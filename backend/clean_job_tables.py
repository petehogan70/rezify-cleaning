from backend.database_config import Session
from sqlalchemy import text
import logging
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup
from sentry_sdk import capture_exception, capture_message
from backend.tables import deleted_internships_ids_table, deleted_entry_level_ids_table, internships_table, entry_level_table, \
    internships_cleaning_hist_table, entry_level_cleaning_hist_table

"""
clean_job_tables.py contains functions to clean and maintain the jobs database.

Any new functions or updates to how the jobs database is cleaned should be added here.
"""

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set the log level to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def add_deleted_job_ids(deleted_jobs, table, reason):
    """
    Inserts deleted job IDs for internships or entry level, their corresponding date_posted values, and the reason for deletion into the deleted_internship_ids table.

    :param table: Which table to enter it into - either 'internships' or 'entry_level'
    :param deleted_jobs: List of tuples [(job_id, date_posted), ...]
    :param reason: String describing the reason for deletion (applied to all jobs in the batch)
    :return: None
    """
    if not deleted_jobs or not reason:
        return

    if table == 'internships':
        table = deleted_internships_ids_table
    elif table == 'entry_level':
        table = deleted_entry_level_ids_table
    else:
        return

    session = Session
    try:
        session.execute(
            text(f'''
                INSERT INTO {table} (job_id, date_posted, reason)
                VALUES (:job_id, :date_posted, :reason)
            '''),
            [{'job_id': job_id, 'date_posted': str(date_posted), 'reason': reason} for job_id, date_posted in deleted_jobs]
        )
        session.commit()
    except Exception as e:
        session.rollback()
        capture_exception(e)
    finally:
        session.remove()




def deduplicate_jobs_in_db(table):
    """
    Deduplicates jobs in the specified table based on title, company, and location.

    :param table: Which table to deduplicate - either 'internships' or 'entry_level'
    """

    if table == 'internships':
        table = internships_table
        job_type = 'internships'
    elif table == 'entry_level':
        table = entry_level_table
        job_type = 'entry_level'
    else:
        return

    session = Session
    count = 0
    try:
        # First, select duplicate jobs (row number > 1)
        results = session.execute(
            text(f'''
                WITH ranked_jobs AS (
                    SELECT id, date_posted,
                           ROW_NUMBER() OVER (PARTITION BY title, company, location ORDER BY date_posted DESC, id) AS rn
                    FROM {table}
                )
                SELECT id, date_posted
                FROM ranked_jobs
                WHERE rn > 1
            ''')
        ).fetchall()

        deleted_jobs = [(row[0], row[1]) for row in results]

        # Delete those jobs
        if deleted_jobs:
            session.execute(
                text(f'''
                    DELETE FROM {table}
                    WHERE id IN :ids
                '''), {'ids': tuple(job_id for job_id, _ in deleted_jobs)}
            )
            session.commit()

            count = len(deleted_jobs)

            # Log the deletions
            add_deleted_job_ids(deleted_jobs, job_type, "Duplicate")

    except Exception as e:
        session.rollback()
        capture_exception(e)

    finally:
        session.remove()
        return count



def get_recent_ids(table):
    """
    Retrieves up to `max_results` job IDs from the specified table where date_posted is within the last 7 days.
    :param table: Which table to query - either 'internships' or 'entry_level'
    """

    if table == 'internships':
        table = internships_table
    elif table == 'entry_level':
        table = entry_level_table
    else:
        return

    session = Session
    job_ids = []
    try:
        limit_date = datetime.now(timezone.utc) - timedelta(days=7)
        limit_str = limit_date.strftime('%Y-%m-%d')
        max_results = 10000

        results = session.execute(
            text(f'''
                SELECT id FROM {table}
                WHERE date_posted >= :limit
                ORDER BY date_posted DESC
                LIMIT :max_results
            '''),
            {'limit': limit_str, 'max_results': max_results}
        ).fetchall()

        job_ids = [row[0] for row in results]

        if len(job_ids) == 0:
            capture_message("WARNING: 0 jobs found in get_recent_ids()", level="warning")

    except Exception as e:
        capture_exception(e)

    finally:
        session.remove()
        return job_ids


def get_recent_deleted_ids(table):
    """
    Retrieves up to `max_results` deleted job IDs from the specified deleted job IDs table where date_posted is within the last 7 days.
    :param table: Which deleted job IDs table to query - either 'internships' or 'entry_level'
    """
    if table == 'internships':
        table = deleted_internships_ids_table
    elif table == 'entry_level':
        table = deleted_entry_level_ids_table
    else:
        return

    session = Session
    job_ids = []
    try:
        limit_date = datetime.now(timezone.utc) - timedelta(days=7)
        limit_str = limit_date.strftime('%Y-%m-%d')
        max_results = 5000

        results = session.execute(
            text(f'''
                SELECT job_id FROM {table}
                WHERE date_posted >= :limit
                ORDER BY date_posted DESC
                LIMIT :max_results
            '''),
            {'limit': limit_str, 'max_results': max_results}
        ).fetchall()

        job_ids = [row[0] for row in results]

    except Exception as e:
        capture_exception(e)

    finally:
        session.remove()
        return job_ids



def get_not_ids(table):
    """
    Combines recent job IDs and recent deleted job IDs from the specified table.
    :param table: Which table to query - either 'internships' or 'entry_level'
    """
    try:
        recent_ids = get_recent_ids(table)
        deleted_ids = get_recent_deleted_ids(table)

        combined_ids = recent_ids + deleted_ids
        return combined_ids

    except Exception as e:
        capture_exception(e)
        return []



def clean_linkedin_jobs(table):
    """
    Removes jobs from the database where:
    - The final_url contains 'www.linkedin.com'
    - The job is over a month old OR
    - The 'company_employee_count_range' is None, '1-10', or '11-50' AND the date_posted is over 3 days

    :param table: Which table to clean - either 'internships' or 'entry_level'

    The reason for this is because LinkedIn jobs have been found to expire more quickly than other job postings.
    Especially when the company is small.

    :return: None
    """
    if table == 'internships':
        table = internships_table
    elif table == 'entry_level':
        table = entry_level_table
    else:
        return

    session = Session
    count = 0
    try:
        # Calculate the date 1 month ago and 3 days ago
        one_month_ago = datetime.now() - timedelta(days=30)
        three_days_ago = datetime.now() - timedelta(days=3)

        one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')
        three_days_ago_str = three_days_ago.strftime('%Y-%m-%d')

        # Delete jobs over a month old where final_url contains 'www.linkedin.com'
        l1 = session.execute(
            text(f'''
                DELETE FROM {table}
                WHERE final_url LIKE '%www.linkedin.com%'
                AND date_posted < :one_month_ago
            '''),
            {'one_month_ago': one_month_ago_str}
        )
        c1 = l1.rowcount or 0

        # Delete jobs where company_employee_count_range is None, '1-10', or '11-50' AND date_posted is over 3 days old
        l2 = session.execute(
            text(f'''
                DELETE FROM {table}
                WHERE final_url LIKE '%www.linkedin.com%'
                AND (company_employee_count_range IS NULL
                     OR company_employee_count_range IN ('1-10', '11-50'))
                AND date_posted < :three_days_ago
            '''),
            {'three_days_ago': three_days_ago_str}
        )
        c2 = l2.rowcount or 0

        # Commit the changes
        session.commit()

        count = c1 + c2

    except Exception as e:
        session.rollback()
        capture_exception(e)

    finally:
        session.remove()
        return count


def clean_indeed_jobs(table):
    """
    Removes jobs from the database where:
    - The final_url contains 'www.indeed.com'
    - The company_employee_count_range is None, '1-10', or '11-50'
    - The date_posted is over a month old

    :param table: Which table to clean - either 'internships' or 'entry_level'

    The reason for this is because Indeed jobs have been found to expire more quickly than other job postings.
    This removes jobs from indeed after a month.
    """
    if table == 'internships':
        table = internships_table
    elif table == 'entry_level':
        table = entry_level_table
    else:
        return

    count = 0
    session = Session
    try:
        # Calculate the date 1 month ago
        one_month_ago = datetime.now() - timedelta(days=30)
        one_month_ago_str = one_month_ago.strftime('%Y-%m-%d')

        # Delete jobs where the final_url contains 'www.indeed.com' and the date_posted is over a month old, and
        # company_employee_count_range is None, '1-10', or '11-50'
        i1 = session.execute(
            text(f'''
                DELETE FROM {table}
                WHERE final_url LIKE '%www.indeed.com%'
                AND (company_employee_count_range IS NULL
                     OR company_employee_count_range IN ('1-10', '11-50'))
                AND date_posted < :one_month_ago
            '''),
            {'one_month_ago': one_month_ago_str}
        )
        count = i1.rowcount or 0

        # Commit the changes
        session.commit()

    except Exception as e:
        session.rollback()
        capture_exception(e)

    finally:
        session.remove()
        return count


def clean_internships_table():
    """
    This is the main function to clean the internships table. It calls the other functions such as clean_linkedin_jobs,
    and clean_indeed_jobs. It also removes jobs based on certain criteria:
    Removes jobs older than 2 months, jobs where the company is 'WayUp',
    jobs where the company contains 'xxx' (case insensitive),
    or jobs where the final_url contains 'morningimages.in'.
    Removes jobs where the final_url is NULL.
    """
    session = Session
    del_counts = {}
    try:
        # Choose the date to delete jobs
        jobs_limit = datetime.now() - timedelta(days=70)
        jobs_limit_str = jobs_limit.strftime('%Y-%m-%d')

        # Choose the date to delete recent deleted job id entries
        deleted_job_ids_limit = datetime.now() - timedelta(days=8)
        deleted_job_ids_limit_str = deleted_job_ids_limit.strftime('%Y-%m-%d')

        # Remove jobs older than 2 months
        age_del = session.execute(
            text(f'''
                DELETE FROM {internships_table}
                WHERE date_posted < :two_months_ago
            '''),
            {'two_months_ago': jobs_limit_str}
        )
        session.commit()
        age_count = age_del.rowcount or 0

        # Remove deleted job id entries older than 2 months
        test = session.execute(
            text(f'''
                        DELETE FROM {deleted_internships_ids_table}
                        WHERE date_posted < :two_months_ago
                    '''),
            {'two_months_ago': deleted_job_ids_limit_str}
        )
        session.commit()

        # Helper list of conditions to apply with messages for logging
        deletion_conditions = [
            ("company = 'RippleMatch'", "RippleMatch"),
            ("company = 'Jobs via Dice'", "Jobs via Dice"),
            ("LOWER(company) LIKE '%xxx%'", "Company contains 'xxx'"),
            ("final_url LIKE '%lensa.com%'", "lensa.com duplicates"),
            ("company = 'Jobright.ai'", "Jobright.ai"),
            ("final_url IS NULL", "final_url is NULL")
        ]

        deletion_cond_count = 0
        for condition, reason in deletion_conditions:
            try:
                # Step 1: Select matching job IDs and date_posted
                results = session.execute(
                    text(f'''
                        SELECT id, date_posted FROM {internships_table}
                        WHERE {condition}
                    ''')
                ).fetchall()

                deleted_jobs = [(row[0], row[1]) for row in results]

                deletion_cond_count += len(deleted_jobs)

                # Step 2: Delete them
                if deleted_jobs:
                    session.execute(
                        text(f'''
                            DELETE FROM {internships_table}
                            WHERE id IN :ids
                        '''), {'ids': tuple(job_id for job_id, _ in deleted_jobs)}
                    )
                    session.commit()

                    # Step 3: Log deletions
                    add_deleted_job_ids(deleted_jobs, 'internships', reason)

            except Exception as e:
                session.rollback()
                capture_exception(e)

        dedup_count = deduplicate_jobs_in_db('internships')  # Remove duplicates based on title, company, and location
        linkedin_count = clean_linkedin_jobs('internships')  # Cleans LinkedIn jobs based on special LinkedIn criteria
        indeed_count = clean_indeed_jobs('internships')  # Clean Indeed jobs based on special Indeed criteria

        del_counts = {'deduplicate_del_count': dedup_count, 'linkedin_del_count': linkedin_count, 'indeed_del_count': indeed_count,
                'age_del_count': age_count, 'deletion_cond_del_count': deletion_cond_count}

        # Commit the changes
        session.commit()
        logging.debug(
            "Successfully cleaned the internships database")
    except Exception as e:
        session.rollback()
        capture_exception(e)
    finally:
        session.remove()
        return del_counts


def clean_entry_level_table():
    """
    This is the main function to clean the entry_level_jobs table. It calls the other functions such as clean_linkedin_jobs,
    and clean_indeed_jobs. It also removes jobs based on certain criteria:
    Removes jobs older than 2 months, jobs where the company is 'WayUp',
    jobs where the company contains 'xxx' (case insensitive),
    or jobs where the final_url contains 'morningimages.in'.
    Removes jobs where the final_url is NULL.
    """
    session = Session
    del_counts = {}
    try:
        # Choose the date to delete jobs
        jobs_limit = datetime.now() - timedelta(days=70)
        jobs_limit_str = jobs_limit.strftime('%Y-%m-%d')

        # Choose the date to delete recent deleted job id entries
        deleted_job_ids_limit = datetime.now() - timedelta(days=8)
        deleted_job_ids_limit_str = deleted_job_ids_limit.strftime('%Y-%m-%d')

        # Remove jobs older than 2 months
        age_del = session.execute(
            text(f'''
                DELETE FROM {entry_level_table}
                WHERE date_posted < :two_months_ago
            '''),
            {'two_months_ago': jobs_limit_str}
        )
        session.commit()
        age_count = age_del.rowcount or 0

        # Remove deleted job id entries older than 2 months
        test = session.execute(
            text(f'''
                        DELETE FROM {deleted_entry_level_ids_table}
                        WHERE date_posted < :two_months_ago
                    '''),
            {'two_months_ago': deleted_job_ids_limit_str}
        )
        session.commit()

        # Helper list of conditions to apply with messages for logging
        deletion_conditions = [
            ("company = 'RippleMatch'", "RippleMatch"),
            ("company = 'Jobs via Dice'", "Jobs via Dice"),
            ("LOWER(company) LIKE '%xxx%'", "Company contains 'xxx'"),
            ("final_url LIKE '%lensa.com%'", "lensa.com duplicates"),
            ("company = 'Jobright.ai'", "Jobright.ai"),
            ("final_url IS NULL", "final_url is NULL")
        ]

        deletion_cond_count = 0
        for condition, reason in deletion_conditions:
            try:
                # Step 1: Select matching job IDs and date_posted
                results = session.execute(
                    text(f'''
                        SELECT id, date_posted FROM {entry_level_table}
                        WHERE {condition}
                    ''')
                ).fetchall()

                deleted_jobs = [(row[0], row[1]) for row in results]

                deletion_cond_count += len(deleted_jobs)

                # Step 2: Delete them
                if deleted_jobs:
                    session.execute(
                        text(f'''
                            DELETE FROM {entry_level_table}
                            WHERE id IN :ids
                        '''), {'ids': tuple(job_id for job_id, _ in deleted_jobs)}
                    )
                    session.commit()

                    # Step 3: Log deletions
                    add_deleted_job_ids(deleted_jobs, 'entry_level', reason)

            except Exception as e:
                session.rollback()
                capture_exception(e)

        dedup_count = deduplicate_jobs_in_db('entry_level')  # Remove duplicates based on title, company, and location
        linkedin_count = clean_linkedin_jobs('entry_level')  # Cleans LinkedIn jobs based on special LinkedIn criteria
        indeed_count = clean_indeed_jobs('entry_level')  # Clean Indeed jobs based on special Indeed criteria

        del_counts = {'deduplicate_del_count': dedup_count, 'linkedin_del_count': linkedin_count, 'indeed_del_count': indeed_count,
                'age_del_count': age_count, 'deletion_cond_del_count': deletion_cond_count}

        # Commit the changes
        session.commit()
        logging.debug(
            "Successfully cleaned the entry_level database")
    except Exception as e:
        session.rollback()
        capture_exception(e)
    finally:
        session.remove()
        return del_counts


def job_cleaning(jobs, table):
    """
    Deletes jobs from the database where:
    - The job's URL returns a 404, 410, or 301 status code.
    - The job's page contains keywords indicating the listing is expired or unavailable.

    :param jobs: List of job dictionaries to check.
    :param table: Which table to clean - either 'internships' or 'entry_level'

    Logs the reason for each deletion.
    """

    if table == 'internships':
        table = internships_table
        job_type = 'internships'
    elif table == 'entry_level':
        table = entry_level_table
        job_type = 'entry_level'
    else:
        return

    keywords = [
        "not found", "404 error", "page missing", "does not exist", "no longer available",
        "no longer exists", "unavailable", "job expired", "no longer accepting",
        "position has been filled", "no longer open"
    ]

    session = Session

    try:
        link_html_count = 0
        for job in jobs:
            final_url = job.get('final_url')
            job_id = job.get('id')
            title = job.get('title', 'N/A')
            company = job.get('company', 'N/A')

            if not final_url or not job_id:
                continue

            try:
                response = requests.get(final_url, allow_redirects=True, timeout=10)

                if response.status_code in [404, 410, 301]:
                    session.execute(
                        text(f'DELETE FROM {table} WHERE id = :job_id'),
                        {'job_id': job_id}
                    )
                    session.commit()
                    link_html_count += 1
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                for script in soup(["script", "style"]):
                    script.extract()

                visible_text = soup.get_text(separator=" ", strip=True).lower()

                if any(kw in visible_text for kw in keywords):
                    session.execute(
                        text(f'DELETE FROM {table} WHERE id = :job_id'),
                        {'job_id': job_id}
                    )
                    session.commit()
                    link_html_count += 1

            except requests.exceptions.RequestException as req_err:
                capture_exception(req_err)
                continue

        logging.debug("Completed deletion of jobs with broken links or expired listings.")

        if job_type == 'internships':
            del_counts = clean_internships_table()
        elif job_type == 'entry_level':
            del_counts = clean_entry_level_table()
        else:
            del_counts = {}
        del_counts['link_html_del_count'] = link_html_count
        total_count = 0
        for label in del_counts:
            total_count += del_counts[label]

        del_counts['total_del'] = total_count

        final_del_counts = del_counts

        record_jobs_cleaning_hist(final_del_counts, job_type)

    except Exception as e:
        session.rollback()
        capture_exception(e)

    finally:
        session.remove()

def record_jobs_cleaning_hist(final_del_counts: dict, table):
    """
    Insert a single history row into jobs_cleaning_hist using values from final_del_counts.

    :param final_del_counts: Dictionary with deletion counts.
    :param table: Which table to log for - either 'internships' or 'entry_level'

    Maps:
      - time -> NOW() (DB timestamp at insert time)
      - total_deleted -> final_del_counts['total_del']
      - link_html_deleted -> final_del_counts['link_html_del_count']
      - age_deleted -> final_del_counts['age_del_count'] (defaults to 0 if missing)
      - and so on
    """

    if table == 'internships':
        table = internships_cleaning_hist_table
    elif table == 'entry_level':
        table = entry_level_cleaning_hist_table
    else:
        return

    this_session = Session
    try:
        # DELETE rows older than 1 year
        # --------------------------------------------
        this_session.execute(
            text(f"DELETE FROM {table} WHERE time < NOW() - INTERVAL '1 year'")
        )

        this_session.commit()

        # Pull values with safe defaults
        total_deleted = int(final_del_counts.get('total_del', 0))
        link_html_deleted = int(final_del_counts.get('link_html_del_count', 0))
        age_deleted = int(final_del_counts.get('age_del_count', 0))
        deduplicate_deleted = int(final_del_counts.get('deduplicate_del_count', 0))
        deletion_condition_deleted = int(final_del_counts.get('deletion_cond_del_count', 0))
        linkedin_deleted = int(final_del_counts.get('linkedin_del_count', 0))
        indeed_deleted = int(final_del_counts.get('indeed_del_count', 0))

        this_session.execute(
            text(f"""
                INSERT INTO {table} (time, total_deleted, link_html_deleted, age_deleted, deduplicate_deleted, deletion_condition_deleted, linkedin_deleted, indeed_deleted)
                VALUES (NOW(), :total_deleted, :link_html_deleted, :age_deleted, :deduplicate_deleted, :deletion_condition_deleted, :linkedin_deleted, :indeed_deleted)
            """),
            {
                'total_deleted': total_deleted,
                'link_html_deleted': link_html_deleted,
                'age_deleted': age_deleted,
                'deduplicate_deleted': deduplicate_deleted,
                'deletion_condition_deleted': deletion_condition_deleted,
                'linkedin_deleted': linkedin_deleted,
                'indeed_deleted': indeed_deleted
            }
        )
        this_session.commit()

    except Exception as e:
        this_session.rollback()
        capture_exception(e)

    finally:
        this_session.remove()



def test_check_jobs_for_expiry(jobs):
    """
    Test function to simulate checking jobs for expiration.
    Prints KEEP or REMOVE along with the reason, job's posted date, title, company, and job link as it processes.
    """

    keywords = [
        "not found", "404 error", "page missing", "does not exist", "no longer available", "no longer exists"
        "unavailable", "job expired", "no longer accepting", "position has been filled", "no longer open"
    ]

    for job in jobs:
        final_url = job.get('final_url')
        job_id = job.get('id')
        job_date = job.get('date_posted', 'N/A')
        title = job.get('title', 'N/A')
        company = job.get('company', 'N/A')

        if not final_url or not job_id:
            print(f"[{job_date}] JOB ID: {job_id} | TITLE: {title} | COMPANY: {company} | DECISION: KEEP | REASON: Missing URL or ID | LINK: {final_url}")
            continue

        try:
            response = requests.get(final_url, allow_redirects=True, timeout=10)

            if response.status_code in [404, 410, 301]:
                print(f"[{job_date}] JOB ID: {job_id} | TITLE: {title} | COMPANY: {company} | DECISION: REMOVE | REASON: HTTP {response.status_code} response | LINK: {final_url}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.extract()

            visible_text = soup.get_text(separator=" ", strip=True).lower()

            if any(kw in visible_text for kw in keywords):
                print(f"[{job_date}] JOB ID: {job_id} | TITLE: {title} | COMPANY: {company} | DECISION: REMOVE | REASON: Expired or unavailable keywords found on page | LINK: {final_url}")
            else:
                print(f"[{job_date}] JOB ID: {job_id} | TITLE: {title} | COMPANY: {company} | DECISION: KEEP | REASON: Page accessible, no expiration keywords detected | LINK: {final_url}")

        except requests.exceptions.RequestException as req_err:
            print(f"[{job_date}] JOB ID: {job_id} | TITLE: {title} | COMPANY: {company} | DECISION: KEEP | REASON: Request failed: {req_err} | LINK: {final_url}")


def get_jobs_for_expiry_check_test(table, limit=100, newest=True, url_filter=None):
    """
    Retrieve jobs with only the required fields for expiry checking, including job title and company.
    Optionally filters jobs based on a substring match within the final_url.

    :param table: Which table to query - either 'internships' or 'entry_level'
    :param limit: Maximum number of jobs to return (int).
    :param newest: If True, order by newest first; if False, oldest first (boolean).
    :param url_filter: Optional substring to filter jobs by final_url (e.g., 'linkedin.com').
    :return: List of job dictionaries with id, final_url, date_posted, title, and company.
    """

    if table == 'internships':
        table = internships_table
    elif table == 'entry_level':
        table = entry_level_table
    else:
        return

    session = Session
    jobs = []

    order = 'DESC' if newest else 'ASC'

    try:
        base_query = f'''
            SELECT id, final_url, date_posted, title, company
            FROM {table}
        '''

        if url_filter:
            base_query += " WHERE final_url LIKE :url_filter"

        base_query += f" ORDER BY date_posted {order} LIMIT :limit"

        query = text(base_query)

        params = {'limit': limit}
        if url_filter:
            params['url_filter'] = f"%{url_filter}%"

        results = session.execute(query, params).fetchall()

        for job in results:
            jobs.append({
                'id': job[0],
                'final_url': job[1],
                'date_posted': job[2],
                'title': job[3],
                'company': job[4]
            })

    except Exception as e:
        logging.error(f"Error retrieving jobs for expiry check: {e}")

    finally:
        session.remove()

    return jobs


def get_jobs_for_cleaning(table, min_age_days=7, limit=30000, newest=True, url_filter=None):
    """
    Retrieve jobs that are at least 'min_age_days' old, with optional URL filtering.

    This version calculates the cutoff date in Python and passes it into the SQL,
    similar to your deletion logic.

    :param table: Which table to query - either 'internships' or 'entry_level'
    :param min_age_days: Minimum age of jobs in days (int).
    :param limit: Maximum number of jobs to return (int).
    :param newest: If True, order by newest first; if False, oldest first (boolean).
    :param url_filter: Optional substring to filter jobs by final_url (e.g., 'linkedin.com').
    :return: List of job dictionaries with id, final_url, date_posted, title, and company.
    """
    if table == 'internships':
        table = internships_table
        job_type = 'internships'
    elif table == 'entry_level':
        table = entry_level_table
        job_type = 'entry_level'
    else:
        return

    session = Session
    jobs = []

    order = 'DESC' if newest else 'ASC'

    # Calculate cutoff date in Python
    cutoff_date = datetime.now() - timedelta(days=min_age_days)
    cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')

    try:
        base_query = f'''
            SELECT id, final_url, date_posted, title, company
            FROM {table}
            WHERE date_posted <= :cutoff_date
        '''

        if url_filter:
            base_query += " AND final_url LIKE :url_filter"

        base_query += f" ORDER BY date_posted {order} LIMIT :limit"

        query = text(base_query)

        params = {
            'cutoff_date': cutoff_date_str,
            'limit': limit
        }
        if url_filter:
            params['url_filter'] = f"%{url_filter}%"

        results = session.execute(query, params).fetchall()

        for job in results:
            jobs.append({
                'id': job[0],
                'final_url': job[1],
                'date_posted': job[2],
                'title': job[3],
                'company': job[4]
            })

    except Exception as e:
        capture_exception(e)
        return []

    finally:
        session.remove()

    if len(jobs) == 0:
        capture_message("WARNING: 0 jobs found in get_jobs_for_cleaning()", level="warning")
    return jobs




if __name__ == "__main__":
    jobs = get_jobs_for_cleaning(40, limit=1, newest=False)
    # job_cleaning(jobs)

