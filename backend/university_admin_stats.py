import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta
from sentry_sdk import capture_exception, capture_message

from sqlalchemy import text

from backend.database_config import Session, sessions_data_name

from backend.monitoring import get_current_active_users_counts, get_daily_sessions_list

from backend.tables import users_list_table, school_stats_table, traffic_history_table

"""
This file contains functions to retrieve and process statistics from the database used for calculations in
the admin dashboard.
"""

base_dir = os.path.dirname(os.path.abspath(__file__))

def get_active_sessions_by_school(school_name: str):
    """
    Returns the count of distinct user_email values from sessions_data where:
      - The school matches the given school_name (or all if rezifyadmin)
      - user_email is not null
      - session_id is in today_sessions

    :param school_name: The school name string (e.g., 'purdue')
    :return: Integer count of distinct matching user_email values, or None if error
    """
    this_session = Session
    final_length = 0
    try:
        if school_name == "rezifyadmin":
            result = this_session.execute(text(f'''
                SELECT user_email, session_id
                FROM {sessions_data_name}
                WHERE user_email IS NOT NULL
            ''')).fetchall()
        else:
            result = this_session.execute(text(f'''
                SELECT user_email, session_id
                FROM {sessions_data_name}
                WHERE school = :school_name AND user_email IS NOT NULL
            '''), {'school_name': school_name}).fetchall()

        # Keep only emails where the session_id is in today_sessions
        daily_list = get_daily_sessions_list()
        filtered_emails = [row[0] for row in result if row[1] in daily_list]

        # Keep only distinct emails
        distinct_emails = set(filtered_emails)

        # Return the count of unique emails
        final_length = len(distinct_emails)

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
    finally:
        this_session.remove()
        return final_length



def get_user_list_for_school(school: str) -> list:
    """
    Returns a list of non-premium user emails from users_list where reported_college
    matches the given school key or its full_name from school_themes.json.

    :param school: The short school key (e.g., 'purdue')
    :return: List of emails (excluding premium) or empty list if none found
    """
    this_session = Session
    email_list = []

    try:
        # Load school_themes.json
        with open(os.path.join(base_dir, 'school_themes.json'), 'r', encoding='utf-8') as f:
            school_themes = json.load(f)

        school_data = school_themes.get(school, {})
        full_name = school_data.get("full_name", None)

        if school == "rezifyadmin":
            # Query all users since it's rezify admin
            results = this_session.execute(text(f'''
                            SELECT email
                            FROM {users_list_table}
                            WHERE email NOT LIKE '%sample.student%'
                        ''')).fetchall()

        else:
            # Query based on reported_college
            if full_name:
                results = this_session.execute(text(f'''
                    SELECT email
                    FROM {users_list_table}
                    WHERE (reported_college = :short_name OR reported_college = :full_name) AND email NOT LIKE '%sample.student%'
                '''), {
                    'short_name': school,
                    'full_name': full_name
                }).fetchall()
            elif school != "all":
                results = this_session.execute(text(f'''
                    SELECT email
                    FROM {users_list_table}
                    WHERE reported_college = :short_name AND email NOT LIKE '%sample.student%'
                '''), {
                    'short_name': school
                }).fetchall()
            else:
                results = this_session.execute(text(f'''
                    SELECT email
                    FROM {users_list_table}
                    WHERE email NOT LIKE '%sample.student%'
                '''), {
                }).fetchall()

        # Filter out None and premium emails
        email_list = [
            email for (email,) in results
        ]

        if len(email_list) == 0:
            capture_message(f"WARNING: get_user_list_for_school() returned no users for: {school}", level="warning")

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        email_list = []
    finally:
        this_session.remove()
        return email_list


def get_num_users_school(users_list):
    """
    Returns the number of non-premium users from users_list associated with the given school.

    :return: Integer count of matching users
    """
    return len(users_list)


def get_total_applications_for_school_users(users_list):
    """
    Given a list of user emails, returns the total number of applications submitted
    by summing the length of the applied_to list (JSON) for each user.

    :param users_list: List of user emails
    :return: Integer total of all applications
    """
    if not users_list:
        return 0

    this_session = Session
    try:
        # Query applied_to field for all users in the list
        results = this_session.execute(text(f'''
            SELECT applied_to
            FROM {users_list_table}
            WHERE email = ANY(:user_emails)
        '''), {'user_emails': users_list}).fetchall()

        total_applications = 0
        for row in results:
            applied_to = row[0]
            if isinstance(applied_to, list):
                total_applications += len(applied_to)
            elif isinstance(applied_to, str):
                # if accidentally stored as a stringified JSON
                try:
                    applied_to_list = json.loads(applied_to)
                    if isinstance(applied_to_list, list):
                        total_applications += len(applied_to_list)
                except Exception as e:
                    capture_exception(e)

        return total_applications

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return 0
    finally:
        this_session.remove()


def get_avg_per_user(num_users: int, total_in_list: int):
    """
    Returns the average number of applications per user.

    :param num_users: Number of users (int)
    :param total_in_list: Total number of jobs in the list (int)
    :return: Float average, rounded to 2 decimals
    """
    if num_users == 0:
        return 0
    return round(total_in_list / num_users, 2)


def get_total_favorites_for_school_users(users_list):
    """
    Sums the total number of jobs saved (favorites) by users in the given list.

    :param users_list: List of user emails
    :return: Integer total number of favorites
    """
    if not users_list:
        return 0

    this_session = Session
    try:
        results = this_session.execute(text(f'''
            SELECT favorites
            FROM {users_list_table}
            WHERE email = ANY(:user_emails)
        '''), {'user_emails': users_list}).fetchall()

        total_favorites = 0
        for row in results:
            favorites = row[0]
            if isinstance(favorites, list):
                total_favorites += len(favorites)
            elif isinstance(favorites, str):
                try:
                    fav_list = json.loads(favorites)
                    if isinstance(fav_list, list):
                        total_favorites += len(fav_list)
                except Exception as e:
                    capture_exception(e)

        return total_favorites

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return 0
    finally:
        this_session.remove()


def get_total_jobs_seen_for_school_users(users_list):
    """
    Sums the total number of jobs seen (jobs_list) by users in the given list.

    :param users_list: List of user emails
    :return: Integer total number of jobs shown
    """
    if not users_list:
        return 0

    this_session = Session
    try:
        results = this_session.execute(text(f'''
            SELECT internships_list
            FROM {users_list_table}
            WHERE email = ANY(:user_emails)
        '''), {'user_emails': users_list}).fetchall()

        total_jobs_seen = 0
        for row in results:
            jobs = row[0]
            if isinstance(jobs, list):
                total_jobs_seen += len(jobs)
            elif isinstance(jobs, str):
                try:
                    job_list = json.loads(jobs)
                    if isinstance(job_list, list):
                        total_jobs_seen += len(job_list)
                except Exception as e:
                    capture_exception(e)

        return total_jobs_seen

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return 0
    finally:
        this_session.remove()


def get_total_jobs_accepted_for_school_users(users_list):
    """
    Sums the total number of jobs accepted by users in the given list.

    :param users_list: List of user emails
    :return: Integer total number of jobs accepted
    """
    if not users_list:
        return 0

    this_session = Session
    try:
        results = this_session.execute(text(f'''
            SELECT jobs_accepted
            FROM {users_list_table}
            WHERE email = ANY(:user_emails)
        '''), {'user_emails': users_list}).fetchall()

        total_accepted = 0
        for row in results:
            accepted = row[0]
            if isinstance(accepted, list):
                total_accepted += len(accepted)
            elif isinstance(accepted, str):
                try:
                    accepted_list = json.loads(accepted)
                    if isinstance(accepted_list, list):
                        total_accepted += len(accepted_list)
                except Exception as e:
                    capture_exception(e)

        return total_accepted

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return 0
    finally:
        this_session.remove()


def get_top_searches(users_list, limit=10):
    """
    Returns the top 10 most common cleaned intern_titles across the given users.
    Removes trailing 'Intern' or 'Internship' from each title.

    :param users_list: List of user emails
    :return: List of dictionaries [{ "term": str, "count": int }]
    """
    if not users_list:
        return []

    this_session = Session
    try:
        # Query intern_titles JSON field
        results = this_session.execute(text(f'''
            SELECT intern_titles
            FROM {users_list_table}
            WHERE email = ANY(:user_emails)
        '''), {'user_emails': users_list}).fetchall()

        title_counter = Counter()

        for row in results:
            titles = row[0]

            if isinstance(titles, str):
                try:
                    titles = json.loads(titles)
                except Exception as e:
                    capture_exception(e)
                    titles = []

            if isinstance(titles, list):
                for title in titles:
                    if isinstance(title, str):
                        # Normalize title: remove trailing 'Intern' or 'Internship'
                        cleaned = re.sub(r'\s*(Intern|Internship)$', '', title, flags=re.IGNORECASE).strip()
                        if cleaned:
                            title_counter[cleaned] += 1

        # Get top 10 most common cleaned terms
        top_terms = title_counter.most_common(limit)
        return [{"term": term, "count": count} for term, count in top_terms]

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return []
    finally:
        this_session.remove()


def top_companies_applied(users_list, limit=10):
    """
    Returns the top 10 most common companies users have applied to, based on
    the 'applied_to' list in users_list.

    :param users_list: List of user emails
    :return: List of dictionaries [{ "company": str, "count": int }]
    """
    if not users_list:
        return []

    this_session = Session
    try:
        # Query the applied_to field
        results = this_session.execute(text(f'''
            SELECT applied_to
            FROM {users_list_table}
            WHERE email = ANY(:user_emails)
        '''), {'user_emails': users_list}).fetchall()

        company_counter = Counter()
        company_logo_hash = {}

        for row in results:
            applied_to = row[0]

            # Handle stringified JSON
            if isinstance(applied_to, str):
                try:
                    applied_to = json.loads(applied_to)
                except Exception as e:
                    capture_exception(e)
                    applied_to = []

            if isinstance(applied_to, list):
                for job in applied_to:
                    if isinstance(job, dict):
                        company = job.get("company")
                        if company:
                            company_counter[company.strip()] += 1
                            if company.strip() not in company_logo_hash:
                                company_logo_hash[company.strip()] = job.get("company_logo", "")

        top_companies = company_counter.most_common(limit)
        return [{"company": name, "count": count, "company_logo": company_logo_hash[name]} for name, count in
                top_companies]

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return []
    finally:
        this_session.remove()


def top_jobs_applied(users_list):
    """
    Returns the top 10 most common jobs (by job ID) users have applied to.
    Each result includes job ID, company, title, location, and count.

    :param users_list: List of user emails
    :return: List of dictionaries [{ "id", "company", "title", "location", "count" }]
    """
    if not users_list:
        return []

    this_session = Session
    try:
        results = this_session.execute(text(f'''
            SELECT applied_to
            FROM {users_list_table}
            WHERE email = ANY(:user_emails)
        '''), {'user_emails': users_list}).fetchall()

        job_counter = Counter()
        job_metadata = {}

        for row in results:
            applied_to = row[0]

            if isinstance(applied_to, str):
                try:
                    applied_to = json.loads(applied_to)
                except Exception as e:
                    capture_exception(e)
                    applied_to = []

            if isinstance(applied_to, list):
                for job in applied_to:
                    if isinstance(job, dict) and 'id' in job:
                        job_id = str(job['id']).strip()
                        job_counter[job_id] += 1

                        if job_id not in job_metadata:
                            job_metadata[job_id] = {
                                "id": job_id,
                                "company": job.get("company", ""),
                                "title": job.get("title", ""),
                                "location": job.get("location", ""),
                                "company_logo": job.get("company_logo", "")
                            }

        top_jobs = job_counter.most_common(10)

        return [
            {
                **job_metadata[job_id],
                "count": count
            }
            for job_id, count in top_jobs
        ]

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return []
    finally:
        this_session.remove()


def update_school_data(school_list):
    """
    Updates the school_stats table for each school in the list:
    - Adds the row if missing
    - Appends a new daily snapshot (date, metrics)
    - Updates top_searches, top_companies_applied, top_jobs_applied, users_list
    - Keeps snapshots sorted (most recent first)
    - Deletes snapshots older than 1 year
    """
    this_session = Session
    today = datetime.now().strftime("%Y-%m-%d")

    try:

        for school_key in school_list:
            # Resolve school name

            # Check if the school row already exists
            result = this_session.execute(text(f'''
                SELECT id, data_snapshots FROM {school_stats_table} WHERE school = :school
            '''), {'school': school_key}).fetchone()

            # Get list of user emails
            users_list = get_user_list_for_school(school_key)
            user_count = len(users_list)

            # Calculate metrics
            total_apps = get_total_applications_for_school_users(users_list)
            total_favs = get_total_favorites_for_school_users(users_list)
            total_accepted = get_total_jobs_accepted_for_school_users(users_list)
            active_sessions = get_active_sessions_by_school(school_key)

            # Create snapshot
            snapshot_entry = {
                "date": today,
                "number_of_users": user_count,
                "total_applications": total_apps,
                "total_favorites": total_favs,
                "total_accepted": total_accepted,
                "number_of_active_sessions": active_sessions
            }

            # Create or update school row
            if result:
                row_id, snapshots_json = result

                # Load, update, and prune snapshots
                snapshots = snapshots_json if isinstance(snapshots_json, list) else json.loads(snapshots_json)
                snapshots = [snap for snap in snapshots if snap.get("date") != today]
                snapshots.append(snapshot_entry)

                # Remove any older than 365 days
                one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
                snapshots = [snap for snap in snapshots if snap["date"] >= one_year_ago]

                # Sort descending by date
                snapshots.sort(key=lambda x: x["date"], reverse=True)

                # Update row
                this_session.execute(text(f'''
                    UPDATE {school_stats_table}
                    SET 
                        data_snapshots = :snapshots,
                        top_searches = :top_searches,
                        top_companies_applied = :top_companies,
                        top_jobs_applied = :top_jobs,
                        users_list = :users_list
                    WHERE id = :row_id
                '''), {
                    'snapshots': json.dumps(snapshots),
                    'top_searches': json.dumps(get_top_searches(users_list)),
                    'top_companies': json.dumps(top_companies_applied(users_list)),
                    'top_jobs': json.dumps(top_jobs_applied(users_list)),
                    'users_list': users_list,
                    'row_id': row_id
                })

            else:
                # Create new row with initial snapshot
                this_session.execute(text(f'''
                    INSERT INTO {school_stats_table} (
                        school, created_at, data_snapshots,
                        top_searches, top_companies_applied, top_jobs_applied, users_list
                    ) VALUES (
                        :school, :created_at, :snapshots,
                        :top_searches, :top_companies, :top_jobs, :users_list
                    )
                '''), {
                    'school': school_key,
                    'created_at': datetime.now(),
                    'snapshots': json.dumps([snapshot_entry]),
                    'top_searches': json.dumps(get_top_searches(users_list)),
                    'top_companies': json.dumps(top_companies_applied(users_list)),
                    'top_jobs': json.dumps(top_jobs_applied(users_list)),
                    'users_list': users_list
                })

            this_session.commit()

        return True

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return False
    finally:
        this_session.remove()


def get_admin_data(school):
    try:
        users_list = get_user_list_for_school(school)
        return {
            "active_sessions": get_active_sessions_by_school(school),
            "num_users": get_num_users_school(users_list),
            "total_applications": get_total_applications_for_school_users(users_list),
            "total_favorites": get_total_favorites_for_school_users(users_list),
            "total_jobs_seen": get_total_jobs_seen_for_school_users(users_list),
            "total_accepted": get_total_jobs_accepted_for_school_users(users_list),
            "top_searches": get_top_searches(users_list),
            "top_companies_applied": top_companies_applied(users_list),
            "top_jobs_applied": top_jobs_applied(users_list),
            "historical": get_historical_data(school),
            "users_list": users_list,
            "active_users_now": get_current_active_users_counts()
        }
    except Exception as e:
        capture_exception(e)
        return {}


def get_historical_data(school):
    this_session = Session
    dats = {}

    try:

        if school == 'rezifyadmin' or school == 'all':
            rows = this_session.execute(text(f'''
                        SELECT time, users_today, sessions_today, searches_today
                        FROM {traffic_history_table}
                        ORDER BY time
                    ''')).fetchall()

            for time_val, users, sessions, searches in rows:
                # time_val may be a datetime or a string; normalize to YYYY-MM-DD
                try:
                    date_key = (time_val.date() - timedelta(
                        days=1)).isoformat()  ## Subtract 1 day so it displays it as the previous day data (Since we enter in right when the new day starts)
                except AttributeError as e:
                    date_key = str(time_val)[:10]
                    capture_exception(e)

                if date_key not in dats:
                    dats[date_key] = {
                        'number_of_users': 0,
                        'number_of_active_sessions': 0,
                        'searches_today': 0
                    }

                dats[date_key]['number_of_users'] += int(users or 0)
                dats[date_key]['number_of_active_sessions'] += int(sessions or 0)
                dats[date_key]['searches_today'] += int(searches or 0)

            return dats
        else:
            result = this_session.execute(text(f'''
                    SELECT id, data_snapshots FROM {school_stats_table} WHERE school = :school
                '''), {'school': school}).fetchall()
        for (id, data_snaps) in result:
            for data_snap in data_snaps:
                if data_snap['date'] in dats:
                    dats[data_snap['date']] += data_snap['number_of_active_sessions']
                    dats[data_snap['date']] = {
                        'number_of_active_sessions': dats[data_snap['date']]['number_of_active_sessions'] + data_snap[
                            'number_of_active_sessions'],
                        'number_of_users': dats[data_snap['date']]['number_of_users'] + data_snap['number_of_users'],
                        'total_accepted': dats[data_snap['date']]['total_accepted'] + data_snap['total_accepted'],
                        'total_applications': dats[data_snap['date']]['total_applications'] + data_snap['total_applications'],
                        'total_favorites': dats[data_snap['date']]['total_favorites'] + data_snap['total_favorites']
                    }
                else:
                    dats[data_snap['date']] = {
                        'number_of_active_sessions': data_snap['number_of_active_sessions'],
                        'number_of_users': data_snap['number_of_users'],
                        'total_accepted': data_snap['total_accepted'],
                        'total_applications': data_snap['total_applications'],
                        'total_favorites': data_snap['total_favorites']
                    }

        return dats

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return {}
    finally:
        this_session.remove()
        return dats

def delete_snapshots_before_date(school: str, cutoff_date: str):
    """
    Delete snapshot entries from school_stats.data_snapshots that are strictly BEFORE cutoff_date,
    for the given school.

    :param school: short key for the school (e.g., "mst")
    :param cutoff_date: string in 'YYYY-MM-DD' format
    :return: dict summary with counts and whether an update occurred
    """
    this_session = Session

    # Validate cutoff_date early
    try:
        cutoff_dt = datetime.strptime(cutoff_date, "%Y-%m-%d").date()
    except ValueError:
        return {
            "ok": False,
            "error": "Invalid cutoff_date format; expected 'YYYY-MM-DD'.",
            "school": school,
            "cutoff_date": cutoff_date
        }

    try:
        # Fetch the row for this school
        row = this_session.execute(text(f'''
            SELECT id, data_snapshots
            FROM {school_stats_table}
            WHERE school = :school
        '''), {'school': school}).fetchone()

        if not row:
            this_session.remove()
            return {
                "ok": True,
                "updated": False,
                "school": school,
                "cutoff_date": cutoff_date,
                "reason": "No row found for school."
            }

        row_id, snapshots_json = row

        # Ensure we have a Python list of dicts
        if snapshots_json is None:
            snapshots = []
        elif isinstance(snapshots_json, list):
            snapshots = snapshots_json
        else:
            # stored as JSON string
            try:
                snapshots = json.loads(snapshots_json)
                if not isinstance(snapshots, list):
                    snapshots = []
            except Exception as e:
                snapshots = []

        original_count = len(snapshots)

        # Filter: keep entries with date >= cutoff_date
        filtered = []
        removed = 0
        for snap in snapshots:
            snap_date_str = (snap or {}).get("date")
            try:
                snap_dt = datetime.strptime(snap_date_str, "%Y-%m-%d").date() if snap_date_str else None
            except Exception:
                # If date is malformed, treat as very old so it's removed
                snap_dt = None

            if snap_dt is not None and snap_dt >= cutoff_dt:
                filtered.append(snap)
            else:
                removed += 1

        updated = removed > 0

        if updated:
            # Persist back to DB (as JSON text for consistency with existing code)
            this_session.execute(text('''
                UPDATE school_stats
                SET data_snapshots = :snapshots
                WHERE id = :row_id
            '''), {
                'snapshots': json.dumps(filtered),
                'row_id': row_id
            })
            this_session.commit()
        this_session.remove()

        return {
            "ok": True,
            "updated": updated,
            "school": school,
            "cutoff_date": cutoff_date,
            "original_count": original_count,
            "removed_count": removed,
            "remaining_count": len(filtered)
        }

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return {
            "ok": False,
            "error": str(e),
            "school": school,
            "cutoff_date": cutoff_date
        }



if __name__ == "__main__":
    # users_list = get_user_list_for_school('rezifyadmin')
    print(get_admin_data('umsl'))
