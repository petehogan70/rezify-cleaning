# clean_job_tables_testing.py
import json
import os
import re
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from sqlalchemy import text

from backend.database_config import Session

HEROKU_CHROME = "/app/.chrome-for-testing/chrome-linux64/chrome"


def launch_browser(p):
    if os.path.exists(HEROKU_CHROME):
        return p.chromium.launch(
            headless=True,
            executable_path=HEROKU_CHROME,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
    # local dev fallback
    return p.chromium.launch(headless=True)


def get_links(limit=None, source=None):
    """
    Returns a list of final_url strings from internships where final_url is not null.
    """
    session = Session
    links = []
    try:
        if source:
            query = f"""
                SELECT final_url, date_posted
                FROM internships
                WHERE final_url IS NOT NULL AND final_url LIKE '%{source}%'
                ORDER BY RANDOM()
            """
        else:
            query = """
                SELECT final_url, date_posted
                FROM internships
                WHERE final_url IS NOT NULL
                ORDER BY RANDOM()
            """

        params = {}
        if limit is not None:
            query += " LIMIT :limit"
            params["limit"] = int(limit)

        rows = session.execute(text(query), params).fetchall() if params else session.execute(text(query)).fetchall()
        links = [r[0] for r in rows if r and r[0]]

    finally:
        session.remove()

    return links


def get_expired_links(limit=None):
    """
    Returns a list of final_url strings from internships where final_url is not null.
    """
    session = Session
    links = []
    try:
        query = """
            SELECT final_url
            FROM removed_jobs_global
            WHERE final_url IS NOT NULL
            ORDER BY RANDOM()
        """

        params = {}
        if limit is not None:
            query += " LIMIT :limit"
            params["limit"] = int(limit)

        rows = session.execute(text(query), params).fetchall() if params else session.execute(text(query)).fetchall()
        links = [r[0] for r in rows if r and r[0]]

    finally:
        session.remove()

    return links


def extract_recruitics_redirect(url: str) -> str:
    """
    Extracts the destination URL from a Recruitics redirect.
    Falls back to the original URL if not found.
    """
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)

        rx_url = qs.get("rx_url")
        if rx_url and rx_url[0]:
            return unquote(rx_url[0])

        return url
    except Exception:
        return url


def extract_redirect_url_appcast(url, timeout=60):
    """
    Extracts a JS/meta redirect URL from HTML.
    Falls back to url if none found.
    """

    try:

        resp = requests.get(
            url,
            allow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        if not resp.text:
            return url

        # Normalize HTML
        html = unescape(resp.text)

        # --------------------------------------------------
        # 1) Appcast / JS setTimeout navigateTo(...)
        # --------------------------------------------------
        m = re.search(
            r'navigateTo\([^,]+,[^,]+,\s*"([^"]+)"\s*\)',
            html,
            flags=re.IGNORECASE
        )
        if m:
            return m.group(1).strip()

        # --------------------------------------------------
        # 2) window.location.replace("URL") or .href =
        # --------------------------------------------------
        m = re.search(
            r'window\.location(?:\.replace|\.)?\s*\(?\s*["\']([^"\']+)["\']\s*\)?',
            html,
            flags=re.IGNORECASE
        )
        if m:
            return m.group(1).strip()

        # --------------------------------------------------
        # 3) Meta refresh fallback
        # --------------------------------------------------
        m = re.search(
            r'<meta\s+http-equiv=["\']refresh["\']\s+content=["\'][^;]+;\s*url=([^"\']+)["\']',
            html,
            flags=re.IGNORECASE
        )
        if m:
            return m.group(1).strip()

        # No redirect found; return original URL
        return url


    except Exception as e:
        return url


def extract_redirect_url(url, timeout=60):
    """
    Extracts a JS/meta redirect URL from HTML.
    Falls back to url if none found.
    """

    try:

        resp = requests.get(
            url,
            allow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        if not resp.url:
            return url
        else:
            return resp.url

    except Exception as e:
        return url


def is_workday_job_expired(url: str, timeout=60):
    """
    Custom Workday expired detector.

    Returns (expired: string - either "active", "expired", or "unknown", reason: string)
    """

    try:
        # Make the request
        resp = requests.get(
            url,
            allow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        # Search for the postingAvailable flag in the HTML, and return the result accordingly
        if not resp.text:
            return "unknown", "Workday.com custom cleaning: No HTML content"

        m = re.search(
            r'postingAvailable"\s*:\s*(true|false)|postingAvailable\s*:\s*(true|false)',
            resp.text,
            flags=re.IGNORECASE
        )

        if not m:  # Flag not found
            return "unknown", "Workday.com custom cleaning: response tag postingAvailable flag not found"

        if (m.group(1) or m.group(2)).lower() == "true":
            return "active", "Workday.com custom cleaning: response tag postingAvailable=true"
        elif (m.group(1) or m.group(2)).lower() == "false":
            return "expired", "Workday.com custom cleaning: response tag postingAvailable=false"
        else:
            return "unknown", "Workday.com custom cleaning: response tag postingAvailable flag unrecognized"

    except Exception as e:
        return "unknown", f"Error in workday.com custom cleaning: {type(e).__name__}: {e}"


# Greenhouse expired detector
def is_job_expired_greenhouse(url: str, timeout=60):
    """
    Custom Greenhouse expired detector.
    """
    try:
        if 'error=true' in url:
            return 'expired', "Greenhouse link redirected with error=true present"

        resp = requests.get(url, allow_redirects=False, timeout=timeout)

        if 'location' in resp.headers:
            if 'error=true' in resp.headers['location']:
                return 'expired', "Greenhouse.io custom cleaning: link redirected with error=true present"

        return 'active', "Greenhouse.io custom cleaning: link did not redirect with error=true, meaning the job is active"

    except Exception as e:
        return 'unknown', f"Error in greenhouse.io custom cleaning cleaning: {type(e).__name__}: {e}"


# Redirect expired detector
def is_job_expired_redirect(url: str, source: str, timeout=60):
    """
    Custom expired detector for sites that redirect expired jobs. It checks if the final URL after redirects
    is different from the original URL.
    """
    try:
        resp = requests.get(url, allow_redirects=True, timeout=timeout)

        if resp.url != url:
            return 'expired', (f"{source} redirect detected, meaning job is expired. Custom testing indicates that"
                               f" {source} always redirects on expired jobs.")
        else:
            return 'active', f"{source} did not redirect, meaning job is active. Custom testing indicates that {source} always redirects on expired jobs."

    except Exception as e:
        return 'unknown', f"Error in {source} redirect cleaning: {type(e).__name__}: {e}"


def is_ultipro_job_expired(url: str, timeout=60):
    """
    Custom Ultipro expired detector.

    Returns (expired: string - either "active", "expired", or "unknown", reason: string)
    """

    try:
        # Make the request
        resp = requests.get(
            url,
            allow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        if not resp.text:
            return "unknown", "Ultipro.com custom cleaning: No HTML content for Ultipro job"

        # Search for the OpportunityUnavailable flag in the HTML, and return the result accordingly
        if 'Opportunity.OpportunityError.OpportunityUnavailableMessage' in resp.text:
            return "expired", "Ultipro.com custom cleaning: OpportunityUnavailableMessage found in HTML response, indicating expired job"
        else:
            return "active", "Ultipro.com custom cleaning: job active, OpportunityUnavailableMessage not found in HTML response"

    except Exception as e:
        return "unknown", f"Error in Ultipro.com custom cleaning: {type(e).__name__}: {e}"


def is_oracle_job_expired(url: str, timeout_ms: int = 15000):
    """
    Returns (expired: bool, reason: str, time: float).
    Detects Oracle CE "job-expired" via browser console logs.
    """
    start_time = datetime.now(timezone.utc)
    found = {"expired": False, "reason": ""}

    def on_console(msg):
        text = msg.text or ""
        # Console line you saw: "job-expired"
        if "job-expired" in text.lower():
            found["expired"] = True
            found["reason"] = f"console:{text}"

    def on_page_error(err):
        # Sometimes it can show up as an exception; keep it for debugging
        t = str(err)
        if "job-expired" in t.lower():
            found["expired"] = True
            found["reason"] = f"pageerror:{t}"

    try:

        with sync_playwright() as p:
            browser = launch_browser(p)
            context = browser.new_context()
            page = context.new_page()

            page.on("console", on_console)
            page.on("pageerror", on_page_error)

            try:
                # IMPORTANT: don't use networkidle for Oracle CE
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

                # Give JS a moment to run and log
                page.wait_for_timeout(1500)

            except PWTimeoutError:
                # If we already saw "job-expired", it's fine. Otherwise treat as unknown.
                pass
            finally:
                context.close()
                browser.close()

        if found["expired"]:
            end_time = datetime.now(timezone.utc)
            elapsed = (end_time - start_time).total_seconds()
            return 'expired', f"{found.get('reason')}"

        end_time = datetime.now(timezone.utc)
        elapsed = (end_time - start_time).total_seconds()
        return 'active', f"Oraclecloud custom cleaning: job-expired not found in console/pageerror logs, indicating active job"

    except Exception as e:
        err_str = str(e)
        cutoff = err_str.find("Call")
        if cutoff != -1:
            err_str = err_str[:cutoff].strip()

        return "unknown", f"Error in Oracle cleaning: {type(e).__name__}: {err_str}"


def is_job_expired_icims(url: str, timeout=60):
    """
    Custom iCIMS expired detector.
    """
    try:
        resp = requests.get(
            url,
            allow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        if resp.status_code in (404, 410):
            return 'expired', f"iCIMS.com custom cleaning: HTTP {resp.status_code}, meaning job is expired"
        else:
            return 'active', f"iCIMS.com custom cleaning: HTTP {resp.status_code}, meaning job is active"

    except Exception as e:
        return 'unknown', f"Error in iCIMS.com custom cleaning: {type(e).__name__}: {e}"


def is_job_expired_dayforce(url: str, timeout: int = 60):
    """

    """
    try:
        resp = requests.get(
            url,
            allow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        if not resp.text:
            return "unknown", "DayforceHCM jobData not found"
        else:
            html = resp.text

        # 1) Prefer parsing the script tag by id
        soup = BeautifulSoup(html, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        next_json_text = None

        if script and script.string:
            next_json_text = script.string.strip()

        # 2) Fallback: regex search if bs4 didn't find it (some pages compress/minify)
        if not next_json_text:
            m = re.search(
                r'<script[^>]+id="__NEXT_DATA__"[^>]*>\s*(\{.*?\})\s*</script>',
                html,
                flags=re.DOTALL,
            )
            if m:
                next_json_text = m.group(1)

        if not next_json_text:
            return "unknown", "DayforceHCM jobData not found"

        # 3) Parse JSON
        try:
            data = json.loads(next_json_text)
        except Exception:
            return "unknown", "DayforceHCM jobData not found"

        # 4) Pull jobData
        page_props = (data.get("props") or {}).get("pageProps") or {}
        job_data = page_props.get("jobData") or {}

        if not isinstance(job_data, dict) or not job_data:
            # Some Next apps store it inside dehydratedState; optional fallback:
            # Try to find a query that contains "jobPostingId"/"jobTitle"
            dehydrated = (page_props.get("dehydratedState") or {}).get("queries") or []
            for q in dehydrated:
                qdata = (((q or {}).get("state") or {}).get("data") or {})
                if isinstance(qdata, dict) and ("jobTitle" in qdata or "jobPostingId" in qdata):
                    job_data = qdata
                    break

        if not isinstance(job_data, dict) or not job_data:
            return "unknown", "DayforceHCM jobData not found"

        posting_status = job_data.get("postingStatus") or ""
        postingExpiryTimestampUTC = job_data.get("postingExpiryTimestampUTC") or None

        if postingExpiryTimestampUTC:
            posting_expiry = datetime.fromisoformat(postingExpiryTimestampUTC)
            now_utc = datetime.now(timezone.utc)
            if now_utc > posting_expiry:
                return 'expired', "DayforceHCM custom cleaning: postingExpiryTimestampUTC in the past, meaning job is expired"
        else:
            if posting_status != 1:
                return 'expired', "DayforceHCM custom cleaning: postingStatus indicates closed, meaning job is expired"

        return 'active', "DayforceHCM custom cleaning: job active based on postingExpiryTimestampUTC and postingStatus"

    except Exception as e:
        return "unknown", f"Error in DayforceHCM custom cleaning: {type(e).__name__}: {e}"


def is_job_expired_taleo(url: str, timeout: int = 60):
    """
    Taleo job availability detector (request/HTML-based).

    Returns:
      ("active" | "expired" | "unknown", reason)
    """
    try:
        resp = requests.get(
            url,
            allow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        html = resp.text or ""
        if not html.strip():
            return "unknown", "Talea custom cleaning: Empty response body"

        # --- Build a visible-text view (helps catch plain phrases) ---
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        visible_text = soup.get_text(" ", strip=True).lower()

        # --- Quick phrase-based signals (works even if scripts differ) ---
        phrase_signals = [
            "the job is no longer available",
            "job is no longer available",
            "job description you are trying to view is no longer available",
            "the job description you are trying to view is no longer available",
            "notavailable",  # some pages include notAvailablePage / notavailable markers
        ]
        for p in phrase_signals:
            if p in visible_text:
                return "expired", f"Taleo custom cleaning: unavailable phrase found in response: '{p}'"

        # --- Script/JS signals specific to Taleo _ftl object ---
        # Instead of parsing JS fully, we search for robust markers.
        html_lower = html.lower()

        # 1) Interface set differs: unavailable has requisitionUnavailableInterface
        if "requisitionunavailableinterface" in html_lower:
            return "expired", "Taleo custom cleaning: interface indicates requisitionUnavailableInterface - meaning expired job"

        # 2) Available job pages typically have requisitionDescriptionInterface + descRequisition list
        has_desc_interface = "requisitiondescriptioninterface" in html_lower
        has_desc_list = "descrequisition" in html_lower

        # 3) Another strong marker: _ints list includes requisitionUnavailableInterface
        m_ints = re.search(r"_ints\s*:\s*\[(.*?)\]", html_lower, flags=re.DOTALL)
        if m_ints:
            ints_blob = m_ints.group(1)
            if "requisitionunavailableinterface" in ints_blob:
                return "expired", "Taleo custom cleaning: _ints includes requisitionUnavailableInterface - meaning expired job"
            if "requisitiondescriptioninterface" in ints_blob:
                # if it explicitly includes description interface, that's a good sign
                pass

        # If it looks like a real job detail page, call it active.
        if has_desc_interface and has_desc_list:
            return "active", "Taleo custom cleaning: requisitionDescriptionInterface/descRequisition detected- meaning active job"

        # If we can't confidently decide, return unknown
        return "unknown", "Taleo custom cleaning: Could not confidently classify Taleo page"

    except requests.Timeout:
        return "unknown", f"Taleo custom cleaning: request timed out after {timeout}s"
    except Exception as e:
        return "unknown", f"Error in Taleo custom cleaning: {type(e).__name__}: {e}"


# ============================================================
# Playwright expired detector (generic)
# ============================================================

CLOSED_PATTERNS = [
    r"\bno longer available\b",
    r"\bno longer exists\b",
    r"\bno longer posted\b",
    r"\bpage not found\b",
    r"\bwe didn't find any relevant jobs\b",
    r"\bnot available at this time\b",
    r"\bcurrently not available\b",
    r"\bthis job is not available\b",
    r"\bjob is unavailable\b",
    r"\bjob expired\b",
    r"\blooking for has expired\b",
    r"\bjob has expired\b",
    r"\bjob (is )?not found\b",
    r"\bpage missing\b",
    r"\b404 error\b",
    r"\bdoes not exist\b",
    r"\bno longer accepting (applications|candidates)?\b",
    r"\bposition has been filled\b",
    r"\bno longer open\b",
    r"\bposting (is )?closed\b",
    r"\bposting has closed\b",
    r"\brequisition (is )?closed\b",
    r"\bopportunity (is )?no longer available\b",
    r"\bcouldn't find this job\b",
    r"\bcouldn't find the job\b",
    r"\bproblem with the service\b",
    r"\bjob you are looking for may have closed\b",
    r"\bwe couldn’t find that page\b",
    r"\bpage you requested could not be found\b",
    r"\bjob is currently unposted\b",
    r"\bjob is expired\b",
    r"\bjob is closed to new applications\b"
]

REDIRECT_SOURCES = [
    'bamboohr.com'
]


def is_job_expired_playwright(url: str, timeout_ms: int = 60000):
    """
    Generic expired detector using Playwright to render the page and search for closed job patterns.
    """

    try:
        start_time = datetime.now(timezone.utc)
        with sync_playwright() as p:
            browser = launch_browser(p)
            page = browser.new_page()
            # domcontentloaded / networkidle
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)

            text = (page.inner_text("body") or "").lower()

            for pat in CLOSED_PATTERNS:
                if re.search(pat, text):
                    browser.close()
                    end_time = datetime.now(timezone.utc)
                    elapsed = (end_time - start_time).total_seconds()
                    return 'expired', f"Playwright: Job is expired because the following pattern was found: {pat}"

            end_time = datetime.now(timezone.utc)
            elapsed = (end_time - start_time).total_seconds()
            browser.close()
            return 'active', f"Playwright: No closed patterns found, job is active"

    except Exception as e:
        err_str = str(e)
        cutoff = err_str.find("Call")
        if cutoff != -1:
            err_str = err_str[:cutoff].strip()

        return "unknown", f"Error in Playwright cleaning: {type(e).__name__}: {err_str}"


# Sources that say whether or not the job is closed via html text in the request, not needing to use Playwright
REQUEST_TEXT_SOURCES = [
    'smartrecruiters.com',
    'teamworkonline.com'
]


def is_job_expired_request_text(url: str, timeout: int = 60):
    """
    Generic expired detector using request to render the page and search for closed job patterns.
    """

    try:
        start_time = datetime.now(timezone.utc)
        resp = requests.get(
            url,
            allow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        # print(f"REQUEST HTML: {resp.text}")

        soup = BeautifulSoup(resp.text, "html.parser")
        for script in soup(["script", "style"]):
            script.extract()

        visible_text = soup.get_text(" ", strip=True).lower()
        visible_text = re.sub(r"\s+", " ", visible_text)

        # print(f"REQUEST HTML TEXT: {visible_text}")

        for pat in CLOSED_PATTERNS:
            if re.search(pat, visible_text):
                end_time = datetime.now(timezone.utc)
                elapsed = (end_time - start_time).total_seconds()
                return 'expired', (f"The job is deemed expired because the following pattern was found: {pat}. This came "
                                   f"from the HTML request text, playwright was not used.")

        end_time = datetime.now(timezone.utc)
        elapsed = (end_time - start_time).total_seconds()
        return 'active', f"The job is deemed active because no closed patterns were found in the HTML request text, playwright was not used."

    except Exception as e:
        return 'unknown', f"Error in request text cleaning: {type(e).__name__}: {e}"


# ============================================================
# Main testing function
# ============================================================

def check_single_link(final_url, timeout=60):
    """
    Checks a single job link and determines whether it should be
    DELETED or KEPT, using the same logic as job_cleaning_testing.

    Order:
      1) Check sources with known flags (Workday, Greenhouse, BambooHR, etc)
      2) HTTP status check
      3) Playwright fallback

    Returns:
      {
        "final_url": str,
        "decision": "DELETE" | "KEEP",
        "reason": str,
        "used": "workday" | "status_code" | "playwright"
      }
    """

    try:

        result = {
            "final_url": final_url,
            "decision": "KEEP",
            "reason": None,
            "used": None,
        }

        if not final_url or not final_url.strip():
            result["reason"] = "Missing URL"
            result["used"] = "input_validation"
            return result

        url = final_url.strip()

        if 'appcast.io' in url:
            # Extract redirect URL from Appcast wrapper
            url = extract_redirect_url_appcast(url, timeout=timeout)
        elif 'grnh.se' in url:
            # Extract redirect URL from Greenhouse short link
            url = extract_redirect_url(url, timeout=timeout)
        elif 'recruitics.com' in url:
            # Extract redirect URL from Recruitics link
            url = extract_recruitics_redirect(url)

        # --------------------------------------------------
        # STEP 1) Source-specific handling
        # --------------------------------------------------

        # 1: Workday handling
        if 'workdayjobs' in url or 'workdaysite':
            expired, reason = is_workday_job_expired(url, timeout=timeout)
            result["used"] = "workday"

            if expired == 'expired':
                result["decision"] = "DELETE"
                result["reason"] = reason
            elif expired == 'active':
                result["decision"] = "KEEP"
                result["reason"] = reason
            else:
                result["decision"] = "KEEP"
                result["reason"] = reason

            return result

        # 2: Greenhouse handling
        if 'greenhouse.io' in url:
            expired, reason = is_job_expired_greenhouse(url, timeout=timeout)
            result["used"] = "greenhouse"
            result["reason"] = reason

            if expired == 'expired':
                result["decision"] = "DELETE"
            elif expired == 'active':
                result["decision"] = "KEEP"
            else:
                result["decision"] = "KEEP"

            return result

        # 3: Ultipro handling
        if 'ultipro.com' in url:
            expired, reason = is_ultipro_job_expired(url, timeout=timeout)
            result["used"] = "ultipro"
            result["reason"] = reason

            if expired == 'expired':
                result["decision"] = "DELETE"
            elif expired == 'active':
                result["decision"] = "KEEP"
            else:
                result["decision"] = "KEEP"

            return result

        # 4: Oracle Cloud handling
        if 'oraclecloud.com' in url:
            expired, reason = is_oracle_job_expired(url, timeout_ms=int(timeout * 1000))
            result["used"] = "oraclecloud"
            result["reason"] = reason

            if expired == 'expired':
                result["decision"] = "DELETE"
            elif expired == 'active':
                result["decision"] = "KEEP"
            else:
                result["decision"] = "KEEP"

            return result

        # 5: iCIMS handling
        if 'icims.com' in url:
            expired, reason = is_job_expired_icims(url, timeout=timeout)
            result["used"] = "icims status_code"
            result["reason"] = reason

            if expired == 'expired':
                result["decision"] = "DELETE"
            elif expired == 'active':
                result["decision"] = "KEEP"
            else:
                result["decision"] = "KEEP"

            return result

        # 6 : Dayforce handling
        if 'dayforcehcm.com' in url:
            expired, reason = is_job_expired_dayforce(url, timeout=timeout)
            result["used"] = "dayforce"
            result["reason"] = reason

            if expired == 'expired':
                result["decision"] = "DELETE"
            elif expired == 'active':
                result["decision"] = "KEEP"
            else:
                result["decision"] = "KEEP"

            return result

        # 7 : Taleo handling
        if 'taleo.net' in url or 'taleo.com' in url:
            expired, reason = is_job_expired_taleo(url, timeout=timeout)
            result["used"] = "taleo"
            result["reason"] = reason

            if expired == 'expired':
                result["decision"] = "DELETE"
            elif expired == 'active':
                result["decision"] = "KEEP"
            else:
                result["decision"] = "KEEP"

            return result

        # 7: Any source that only redirects on expiry
        for source in REDIRECT_SOURCES:
            if source in url:
                expired, reason = is_job_expired_redirect(url, source, timeout=timeout)
                result["used"] = f"{source}_redirect"
                result["reason"] = reason

                if expired == 'expired':
                    result["decision"] = "DELETE"
                elif expired == 'active':
                    result["decision"] = "KEEP"
                else:
                    result["decision"] = "KEEP"

                return result

        # 8: Any source that only redirects on expiry
        for source in REQUEST_TEXT_SOURCES:
            if source in url:
                expired, reason = is_job_expired_request_text(url)
                result["used"] = f"{source}_request_text"
                result["reason"] = reason

                if expired == 'expired':
                    result["decision"] = "DELETE"
                elif expired == 'active':
                    result["decision"] = "KEEP"
                else:
                    result["decision"] = "KEEP"

                return result

        # --------------------------------------------------
        # 2) Status code handling and redirect url check
        # --------------------------------------------------
        # resp = requests.get(url, allow_redirects=True, timeout=timeout)
        resp = requests.get(
            url,
            allow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "text/html",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        # print(f"RESPONSE HTML: {resp.text}")

        if resp.status_code in (404, 410):
            result["decision"] = "DELETE"
            result["reason"] = f"HTTP {resp.status_code}"
            result["used"] = "status_code"
            return result

        url_string_checks = [
            'position-not-available',
            'jobnotfound',
            'job-not-found',
        ]

        if any(check in resp.url.lower() for check in url_string_checks):
            result["decision"] = "DELETE"
            result["reason"] = f"URL indicates not found: {resp.url}"
            result["used"] = "status_code"
            return result

        # --------------------------------------------------
        # 3) Request text handling - generic pattern search in request without Playwright
        # --------------------------------------------------

        expired, reason = is_job_expired_request_text(url, timeout=timeout)
        if expired == 'expired':
            result["decision"] = "DELETE"
            result["reason"] = reason
            result["used"] = "request_text"
            return result

        # --------------------------------------------------
        # 4) Playwright fallback
        # --------------------------------------------------
        expired, reason = is_job_expired_playwright(url, timeout_ms=int(timeout * 1000))
        result["used"] = "playwright"
        result["reason"] = reason

        if expired == 'expired':
            result["decision"] = "DELETE"
        elif expired == 'active':
            result["decision"] = "KEEP"
        else:
            result["decision"] = "KEEP"

        # print(result)
        return result

    except Exception as e:
        return {
            "final_url": final_url,
            "decision": "KEEP",
            "reason": f"Error in check_single_link: {type(e).__name__}: {e}",
            "used": "error_handling",
        }


def extract_base_domain(url: str) -> str:
    """
    Returns a normalized source domain for grouping job links.

    Examples:
      bloomenergy.wd1.myworkdayjobs.com -> myworkdayjobs.com
      job-boards.greenhouse.io          -> greenhouse.io
      workforcenow.adp.com              -> adp.com
    """
    if not url:
        return "unknown"

    u = url.strip()
    if not u:
        return "unknown"

    if "://" not in u:
        u = "https://" + u

    try:
        host = (urlparse(u).netloc or "").lower()

        host = host.split("@")[-1]  # remove auth
        host = host.split(":")[0]  # remove port

        if host.startswith("www."):
            host = host[4:]

        parts = [p for p in host.split(".") if p]
        if len(parts) >= 2:
            return ".".join(parts[-2:])

        return host or "unknown"

    except Exception:
        return "unknown"


def group_count_by_source(urls, examples_per_source=3):
    """
    Groups job URLs by base domain, prints counts + percentages,
    and returns the structured result.

    :param urls: list[str]
    :param examples_per_source: how many example URLs to print per domain
    :return: dict with totals, counts, percentages, examples
    """
    total = len(urls or [])
    counts = Counter()
    examples = defaultdict(list)

    for url in (urls or []):
        domain = extract_base_domain(url)
        counts[domain] += 1

        if len(examples[domain]) < examples_per_source:
            examples[domain].append(url)

    # sort descending
    counts_sorted = dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))

    percentages = {
        dom: (cnt / total * 100 if total else 0.0)
        for dom, cnt in counts_sorted.items()
    }

    # ---- PRINT RESULTS ----
    print("\n=== Job Source Breakdown ===")
    print(f"Total URLs: {total}\n")

    for domain, count in counts_sorted.items():
        if count > 100:
            pct = percentages[domain]
            print(f"{domain:25s} {count:7d} ({pct:6.2f}%)")

            for ex in examples[domain]:
                print(f"   - {ex}")
            print()

    print("=== End Breakdown ===\n")
    # ------------------------

    return {
        "total": total,
        "counts": counts_sorted,
        "percentages": percentages,
        "examples": dict(examples),
    }


def run_link_checks(
        links,
        timeout=60,
        show_per_link=True,
        show_fail_reasons_top_n=10,
):
    """
    Runs check_single_link() on a list of URLs, prints per-link results as it runs,
    and prints a summary at the end.

    Summary includes:
      - kept vs deleted counts + %
      - used-method counts + %
      - top reasons (optional)
      - elapsed time

    Returns:
      results: list[dict] of the check_single_link outputs
    """
    links = [l for l in (links or []) if l and str(l).strip()]
    total = len(links)

    start_ts = datetime.now(timezone.utc)

    if total == 0:
        print("No links provided.")
        return []

    results = []
    decision_counts = Counter()
    used_counts = Counter()
    reason_counts = Counter()

    print("\n" + "=" * 80)
    print(f"Running job link checks: {total} link(s) | timeout={timeout}s")
    print("=" * 80)

    for i, url in enumerate(links, start=1):
        url = str(url).strip()

        # ---- run check ----
        res = check_single_link(url, timeout=timeout)
        results.append(res)

        decision = (res.get("decision") or "UNKNOWN").upper()
        used = (res.get("used") or "unknown").lower()
        reason = (res.get("reason") or "").strip()

        decision_counts[decision] += 1
        used_counts[used] += 1
        if reason:
            reason_counts[reason] += 1

        # ---- per-link print ----
        if show_per_link:
            # compact, consistent print format
            # Example:
            # [003/250] DELETE | used=playwright      | Pattern found: ...
            #           https://...
            print(f"\n[{i:03d}/{total}] {decision:<6} | used={used:<14} | {reason}")
            print(f"          {url}")

    # ---- summary ----
    elapsed = (datetime.now(timezone.utc) - start_ts).total_seconds()
    kept = decision_counts.get("KEEP", 0)
    deleted = decision_counts.get("DELETE", 0)

    def pct(n):  # safe percentage helper
        return (n / total * 100.0) if total else 0.0

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total:   {total}")
    print(f"KEEP:    {kept:6d} ({pct(kept):6.2f}%)")
    print(f"DELETE:  {deleted:6d} ({pct(deleted):6.2f}%)")
    other = total - kept - deleted
    if other:
        print(f"OTHER:   {other:6d} ({pct(other):6.2f}%)")

    print("\n--- Method Used Breakdown ---")
    for method, cnt in used_counts.most_common():
        print(f"{method:20s} {cnt:6d} ({pct(cnt):6.2f}%)")

    if show_fail_reasons_top_n and reason_counts:
        print(f"\n--- Top Reasons (top {show_fail_reasons_top_n}) ---")
        for reason, cnt in reason_counts.most_common(show_fail_reasons_top_n):
            print(f"{cnt:6d} ({pct(cnt):6.2f}%)  {reason}")

    print(f"\nElapsed: {elapsed:.2f}s")
    print("=" * 80 + "\n")

    return results


print_lock = threading.Lock()


def run_link_checks_parallel(
        links,
        timeout=60,
        show_per_link=True,
        show_fail_reasons_top_n=10,
        max_workers=20,  # tune: 10–50 depending on your machine/network
):
    links = [l for l in (links or []) if l and str(l).strip()]
    total = len(links)
    start_ts = datetime.now(timezone.utc)

    if total == 0:
        print("No links provided.")
        return []

    results = [None] * total
    decision_counts = Counter()
    used_counts = Counter()
    reason_counts = Counter()

    print("\n" + "=" * 80)
    print(f"Running job link checks (PARALLEL): {total} link(s) | timeout={timeout}s | workers={max_workers}")
    print("=" * 80)

    def _do_one(idx, url):
        res = check_single_link(url, timeout=timeout)
        return idx, url, res

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(_do_one, i, str(url).strip()): i
            for i, url in enumerate(links)
        }

        for fut in as_completed(futures):
            idx, url, res = fut.result()
            results[idx] = res  # preserve original ordering

            decision = (res.get("decision") or "UNKNOWN").upper()
            used = (res.get("used") or "unknown").lower()
            reason = (res.get("reason") or "").strip()

            decision_counts[decision] += 1
            used_counts[used] += 1
            if reason:
                reason_counts[reason] += 1

            if show_per_link:
                with print_lock:
                    # idx is 0-based; display 1-based
                    print(f"\n[{idx + 1:03d}/{total}] {decision:<6} | used={used:<14} | {reason}")
                    print(f"          {url}")

    # ---- summary (same as yours) ----
    elapsed = (datetime.now(timezone.utc) - start_ts).total_seconds()
    kept = decision_counts.get("KEEP", 0)
    deleted = decision_counts.get("DELETE", 0)

    def pct(n):
        return (n / total * 100.0) if total else 0.0

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total:   {total}")
    print(f"KEEP:    {kept:6d} ({pct(kept):6.2f}%)")
    print(f"DELETE:  {deleted:6d} ({pct(deleted):6.2f}%)")
    other = total - kept - deleted
    if other:
        print(f"OTHER:   {other:6d} ({pct(other):6.2f}%)")

    print("\n--- Method Used Breakdown ---")
    for method, cnt in used_counts.most_common():
        print(f"{method:20s} {cnt:6d} ({pct(cnt):6.2f}%)")

    if show_fail_reasons_top_n and reason_counts:
        print(f"\n--- Top Reasons (top {show_fail_reasons_top_n}) ---")
        for reason, cnt in reason_counts.most_common(show_fail_reasons_top_n):
            print(f"{cnt:6d} ({pct(cnt):6.2f}%)  {reason}")

    print(f"\nElapsed: {elapsed:.2f}s")
    print("=" * 80 + "\n")

    return results


if __name__ == "__main__":
    # group_count_by_source(get_links(50000))
    '''
        Good: [
            'https://jobs.dayforcehcm.com/en-US/ggg/GenesisGlobalGroupClientCareerSite/jobs/8693',
            'https://jobs.dayforcehcm.com/en-US/watlow/WATLOWCAREERSITE/jobs/16567',
            'https://jobs.dayforcehcm.com/en-US/yss/CANDIDATEPORTAL/jobs/1009'
        ]

        Bad: [
            'https://jobs.dayforcehcm.com/en-US/usga/CANDIDATEPORTAL/jobs/1016',
            'https://jobs.dayforcehcm.com/en-US/atricure/CANDIDATEPORTAL/jobs/10019?src=LinkedIn',
            'https://jobs.dayforcehcm.com/en-US/pca/CANDIDATEPORTAL/jobs/51361?src=LinkedIn'
        ]
    '''
    # url = 'https://wd1.myworkdaysite.com/recruiting/avnet/External/job/Chandler-Arizona-United-States-Of-America/Business-Analyst-Intern_JR-020726?source=LinkedIn'
    # print(check_single_link(url, timeout=20))

    test_links = get_links(limit=500)
    run_link_checks_parallel(test_links, timeout=13, show_per_link=True, show_fail_reasons_top_n=10, max_workers=10)