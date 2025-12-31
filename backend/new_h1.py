import pandas as pd
from sentry_sdk import capture_exception
from backend.tables import internships_table
from backend.database_config import Session
import re
from sqlalchemy import text
from rapidfuzz.distance import JaroWinkler
import os


def description_is_us_only(title: str, description: str) -> bool:
    """
    Replicates your list-of-lists pattern logic:
      - all lists must have >= 1 hit
      - for lists with 1-2 items: case-insensitive
      - for lists with >=3 items: case-sensitive
    """
    try:
        search_terms_lists = [
            ['authoriz', 'citizen'],
            ['work'],
            [' US ', 'United States', ' U.S. ', ' US.', ' US,']
        ]
        explicit_flags = [
            'no visa sponsorship', 'sponsorship not available', 'not willing to sponsor', 'sponsorship unavailable',
            'not provide sponsorship', 'no sponsorship available', 'no sponsorship provided', 'no h1b', 'no sponsorship']
        text_blob = f"{title or ''} {description or ''}"

        # First check explicit negative flags (case-insensitive)
        text_blob_lower = text_blob.lower()
        for flag in explicit_flags:
            if flag.lower() in text_blob_lower:
                return True

        for terms in search_terms_lists:
            list_has_match = False
            for term in terms:
                if len(terms) <= 2:
                    # case-insensitive
                    pattern = re.compile(re.escape(term), re.IGNORECASE)
                else:
                    # case-sensitive
                    pattern = re.compile(re.escape(term))

                if pattern.search(text_blob):
                    list_has_match = True
                    break

            if not list_has_match:
                return False  # one list failed => not US-only

        return True  # all lists matched at least one term

    except Exception as e:
        capture_exception(e)
        return False


def company_matches_h1b(company_name: str, sponsor_buckets) -> bool:
    """
    Apply your H-1B matching logic:
      - Clean legal suffixes
      - If cleaned company < 6 chars: must match an exact token from sponsor name
      - Else require same first 3 chars to consider
      - If cleaned length > 18 and first 12 chars match -> 100%
      - Else if first 6 chars match -> 100%
      - Else Jaro-Winkler similarity; require >= 0.95
    """
    try:
        if not company_name:
            return False

        c_clean = clean_legal_suffix(company_name)
        if not c_clean:
            return False

        # Short-name exact-word rule (< 6 chars)
        if len(c_clean) < 6:
            p3 = c_clean[:3]
            candidates = sponsor_buckets.get(p3, [])
            for sponsor in candidates:
                # Exact token match on cleaned sponsor tokens
                if c_clean in sponsor.split():
                    return True
            return False  # short names must token-match

        # Normal/long names: prefix gating + forced-score rules
        p3 = c_clean[:3]
        p6 = c_clean[:6]
        p12 = c_clean[:12]
        long_name = len(c_clean) > 18

        candidates = sponsor_buckets.get(p3, [])
        for sponsor in candidates:
            # Forced 100% if longer + first 12 match
            if long_name and sponsor.startswith(p12):
                return True
            # Forced 100% if first 6 match
            if sponsor.startswith(p6):
                return True
            # Otherwise Jaro-Winkler
            score = JaroWinkler.similarity(c_clean, sponsor)
            if score >= 0.95:
                return True

        return False

    except Exception as e:
        capture_exception(e)
        return False



def finish_international(h1b_csv_path: str) -> None:
    """
    Update international_availability for jobs where it is NULL.

    Decision order (highest precedence first):
      1) If description signals US-only requirements -> set FALSE
      2) Else if company matches H1B sponsor list (prefix + Jaro-Winkler rules) -> set TRUE
      3) Else -> set TRUE (fallback, same as your prior behavior)

    :param h1b_csv_path: Path to H-1B CSV (e.g., 'h1_data.csv')
    """
    session = Session

    # Get directory of this file (where this script lives)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Build path to h1b_path folder inside backend
    h1b_path = os.path.join(base_dir, h1b_csv_path)

    try:
        # -----------------------------
        # 1) Build sponsor list (cleaned)
        # -----------------------------
        sponsor_employers_raw = get_unique_employers(h1b_path, sort=False)
        sponsor_employers_cleaned = [clean_legal_suffix(s) for s in sponsor_employers_raw if s]

        # Optional small speedup: bucket sponsors by first 3 chars to limit comparisons
        sponsor_buckets = {}
        for s in sponsor_employers_cleaned:
            if not s:
                continue
            p3 = s[:3]
            sponsor_buckets.setdefault(p3, []).append(s)

        # -----------------------------
        # 2) Fetch jobs to process
        # -----------------------------  WHERE international_availability IS NULL
        jobs = session.execute(text(f'''
            SELECT id, title, description, company
            FROM {internships_table}
            WHERE international_availability IS NULL
        ''')).fetchall()


        # -----------------------------
        # 3) Process each job
        # -----------------------------
        processed = 0
        forced_false = 0
        sponsor_true = 0
        fallback_false = 0

        for job in jobs:
            job_id = job.id
            title = job.title or ""
            desc = job.description or ""
            company = job.company or ""

            try:
                # A) If description indicates US-only, set FALSE (wins)
                if description_is_us_only(title, desc):
                    session.execute(
                        text(f'UPDATE {internships_table} SET international_availability = FALSE WHERE id = :id'),
                        {'id': job_id}
                    )
                    forced_false += 1
                else:
                    # B) Else if company matches H1B sponsors, set TRUE
                    if company_matches_h1b(company, sponsor_buckets):
                        session.execute(
                            text(f'UPDATE {internships_table} SET international_availability = TRUE WHERE id = :id'),
                            {'id': job_id}
                        )
                        sponsor_true += 1
                    else:
                        # C) Else default FALSE
                        session.execute(
                            text(f'UPDATE {internships_table} SET international_availability = FALSE WHERE id = :id'),
                            {'id': job_id}
                        )
                        fallback_false += 1

                session.commit()
                processed += 1

            except Exception as inner_e:
                capture_exception(inner_e)
                session.rollback()

        get_international_availability_counts()

    except Exception as e:
        capture_exception(e)
        session.rollback()

    finally:
        session.remove()



def get_unique_employers(csv_path: str, sort: bool = True) -> list:
    """
    Reads an H-1B LCA CSV file and returns a list of unique employer names.

    :param csv_path: Path to the H-1B CSV file (e.g., 'h1_data.csv')
    :param sort: Whether to return the list sorted alphabetically (default: True)
    :return: List of unique employer names (strings)
    """
    try:
        df = pd.read_csv(csv_path)
        df["EMPLOYER_NAME"] = df["EMPLOYER_NAME"].astype(str).str.strip()
        unique_employers = df["EMPLOYER_NAME"].dropna().unique()
        return sorted(unique_employers) if sort else list(unique_employers)

    except Exception as e:
        capture_exception(e)
        return []


def get_h1b_likely_job_stats(h1b_csv_path: str) -> dict:
    """
    Uses cleaned and similarity-matched employer names from H-1B data to detect likely H-1B sponsor jobs.

    :param h1b_csv_path: Path to h1_data.csv
    :return: Dictionary with stats: % h1b likely, list of companies, job counts
    """
    session = Session()

    try:
        # Step 1: Load sponsor company names and clean them
        sponsor_employers_raw = get_unique_employers(h1b_csv_path, sort=False)
        sponsor_employers_cleaned = [clean_legal_suffix(name) for name in sponsor_employers_raw if name]

        # Step 2: Load job company names
        result = session.execute(text(f"SELECT DISTINCT company FROM {internships_table}"))
        job_companies = [row[0] for row in result.fetchall() if row[0]]

        h1b_likely = []
        all_job_names = []

        long_matches = 0
        short_matches = 0
        lml, sml = [], []

        for company in job_companies:
            company_clean = clean_legal_suffix(company)
            all_job_names.append(company)

            # --- NEW: handle very short names (< 6 chars) with exact token match rule ---
            if len(company_clean) < 6 and company_clean:
                matched_short = False
                for sponsor in sponsor_employers_cleaned:
                    sponsor_tokens = sponsor.split()  # cleaned already -> lowercase, punctuation stripped
                    if company_clean in sponsor_tokens:
                        # direct token match → force 100%
                        h1b_likely.append(company)
                        matched_short = True
                        short_matches += 1
                        sml.append((company, sponsor))
                        break
                if matched_short:
                    continue  # go to next company
                # if no token match, skip further similarity checks for this short name
                continue

            # --- Original logic for normal/long names ---
            prefix_3 = company_clean[:3]
            prefix_6 = company_clean[:6]
            prefix_12 = company_clean[:12]
            long_name = len(sponsor_employers_cleaned) > 25  # your latest threshold

            for sponsor in sponsor_employers_cleaned:
                if not sponsor.startswith(prefix_3):
                    continue

                # Apply prefix-based scoring
                if long_name and sponsor.startswith(prefix_12):
                    score = 1.0
                    long_matches += 1
                    lml.append((company, sponsor))
                elif not long_name and sponsor.startswith(prefix_6):
                    score = 1.0
                    short_matches += 1
                    sml.append((company, sponsor))
                else:
                    score = JaroWinkler.similarity(company_clean, sponsor)

                if score >= 0.95:
                    h1b_likely.append(company)
                    break  # Stop checking once a match is found

        total_jobs = len(all_job_names)
        matched_jobs = len(h1b_likely)
        percentage = (matched_jobs / total_jobs * 100) if total_jobs else 0

        session.close()
        return {
            "percentage_h1b_likely": round(percentage, 2),
            "h1b_likely_companies": sorted(set(h1b_likely)),
            "total_jobs": total_jobs,
            "h1b_likely_jobs": matched_jobs
        }

    except Exception as e:
        capture_exception(e)
        session.rollback()
        session.close()
        return {}



def get_jobs_by_company(company_name: str, threshold: int = 90) -> list:
    """
    Returns jobs from internships where the company name matches by Jaro-Winkler similarity,
    with legal suffix cleaning, prefix filtering, and forced 100% match rules based on length.

    :param company_name: Legal company name (e.g. from H-1B records)
    :param threshold: Similarity threshold (0–100)
    :return: List of job dicts
    """
    session = Session()
    try:
        # Step 1: Pull unique company names
        companies_result = session.execute(text(f'SELECT DISTINCT company FROM {internships_table}'))
        all_companies = [row[0] for row in companies_result.fetchall() if row[0]]

        # Step 2: Clean input
        query_clean = clean_legal_suffix(company_name)
        threshold_normalized = threshold / 100

        prefix_3 = query_clean[:3]
        prefix_6 = query_clean[:6]
        prefix_12 = query_clean[:12]
        long_name = len(query_clean) > 18

        matches = []

        total_long_match = 0
        total_short_match = 0

        for candidate in all_companies:
            candidate_clean = clean_legal_suffix(candidate)

            # Must share first 3 characters
            if not candidate_clean.startswith(prefix_3):
                continue

            # Force 100% if first 12 chars match and query is long
            if long_name and candidate_clean.startswith(prefix_12):
                score = 1.0
                total_long_match += 1
            # Force 100% if first 6 chars match and not long
            elif not long_name and candidate_clean.startswith(prefix_6):
                score = 1.0
                total_short_match += 1
            else:
                score = JaroWinkler.similarity(candidate_clean, query_clean)

            if score >= threshold_normalized:
                matches.append((candidate, score))

        if not matches:
            session.close()
            return []

        matches.sort(key=lambda x: -x[1])
        matched_company_names = [match[0] for match in matches]

        # Step 3: Fetch matching jobs
        result = session.execute(text(f'''
            SELECT title, company, date_posted, final_url, international_availability
            FROM {internships_table}
            WHERE company = ANY(:matched_names)
        '''), {'matched_names': matched_company_names})

        jobs = [
            {
                'title': row[0],
                'company': row[1],
                'date_posted': row[2],
                'url': row[3],
                'international': row[4]
            }
            for row in result.fetchall()
        ]

        session.close()

        return jobs

    except Exception as e:
        session.rollback()
        session.close()
        capture_exception(e)
        return []


def clean_legal_suffix(name: str) -> str:
    """
    Removes common legal suffixes from company names for better matching.
    """
    try:
        name = name.lower().strip()

        # Remove common legal suffixes
        suffixes = r'\b(llc|inc\.?|ltd\.?|corp\.?|corporation|limited|co\.?|llp|plc|gmbh|pte\.? ltd\.?|incorporated|s\.a\.)\b'
        cleaned = re.sub(suffixes, '', name, flags=re.IGNORECASE)

        # Remove leftover punctuation and normalize whitespace
        cleaned = re.sub(r'[.,]', '', cleaned)
        return cleaned.strip()

    except Exception as e:
        capture_exception(e)
        return name.lower().strip()


def get_international_availability_counts():
    """
    Returns a dict with counts of TRUE, FALSE, and NULL values
    in the international_availability column of internships table.
    """
    session = Session()
    try:
        result = session.execute(text(f"""
            SELECT 
                CASE 
                    WHEN international_availability IS TRUE THEN 'true'
                    WHEN international_availability IS FALSE THEN 'false'
                    ELSE 'null'
                END as availability_status,
                COUNT(*) as count
            FROM {internships_table}
            GROUP BY availability_status
        """)).fetchall()

        counts = {row[0]: row[1] for row in result}
        print("International availability counts:", counts)
        return counts

    except Exception as e:
        capture_exception(e)
        return {}
    finally:
        session.close()




if __name__ == "__main__":
    # Example usage
    # finish_international('h1_data.csv')
    jobs = get_jobs_by_company('Gresham Smith', threshold=90)
    print(len(jobs))
    for job in jobs:
        print(job)


