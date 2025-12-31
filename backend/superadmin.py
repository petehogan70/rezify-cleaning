import json
import os
from sentry_sdk import capture_exception
from datetime import datetime, timezone, timedelta, date
from sqlalchemy import text
from collections import Counter
import re

from backend.database_config import Session

from backend.monitoring import get_current_active_users_counts, get_jobs_database_length, get_title_document_count_internships, \
            get_description_document_count_internships, get_theirstack_data, get_recent_search_data

from backend.login import premium_emails, premium_email_endings
from backend.tables import jobs_data_hist_table, users_list_table, admin_list_table, internships_cleaning_hist_table, \
    openai_usage_table, removed_jobs_global_table, searches_table, traffic_history_table, ts_purchases_table

"""
This file contains functions to retrieve and process statistics from the database used for calculations in
the rezify super admin dashboard.
"""

base_dir = os.path.dirname(os.path.abspath(__file__))

# We have get_current_active_users_counts

def get_user_breakdown():
    """
    Returns the total number of rows in the users_list table.

    :return: Integer count or None if an error occurs
    """
    this_session = Session
    try:
        basic_users = 0
        paying_premium_users = 0
        sponsored_premium_users = 0

        result = this_session.execute(text(f"SELECT email, plan FROM {users_list_table} WHERE email NOT LIKE '%sample.student%'")).fetchall()

        total_users = len(result)

        for user in result:
            if user[1] == 'basic':
                basic_users += 1
            else:
                if any(user[0].endswith(ending) for ending in premium_email_endings) or user[0] in premium_emails:
                    sponsored_premium_users += 1
                else:
                    paying_premium_users += 1

        user_breakdown = {'total_users': total_users, 'basic_users': basic_users,
                          'paying_premium_users': paying_premium_users, 'sponsored_premium_users': sponsored_premium_users}


        this_session.remove()
        return user_breakdown
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


def get_user_counts_by_school():
    """
    Returns counts of users grouped by reported_college (school),
    sorted from most common to least common.

    Excludes sample/testing accounts (email LIKE '%sample.student%').
    COALESCEs NULL reported_college to 'unknown'.

    :return: List[{"school": str, "count": int}]
    """
    this_session = Session
    try:
        rows = this_session.execute(text(f"""
            SELECT
                COALESCE(reported_college, 'unknown') AS school,
                COUNT(*) AS cnt
            FROM {users_list_table}
            WHERE email NOT LIKE '%sample.student%'
            GROUP BY COALESCE(reported_college, 'unknown')
            ORDER BY cnt DESC, school ASC
        """)).fetchall()

        return [{"school": school, "count": int(cnt)} for school, cnt in rows][:15]

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return []
    finally:
        this_session.remove()

def get_users_historical_data():
    this_session = Session
    dats = {}

    try:

        rows = this_session.execute(text(f'''
                    SELECT time, users_today, sessions_today, searches_today, admins_today, paying_premium_users, basic_users, sponsored_premium_users, active_users_today
                    FROM {traffic_history_table}
                    ORDER BY time
                ''')).fetchall()

        for time_val, users, sessions, searches, admins, paying_premium, basic, sponsored_premium, active_users_today in rows:
            # time_val may be a datetime or a string; normalize to YYYY-MM-DD
            try:
                date_key = (time_val.date() - timedelta(days=1)).isoformat()  ## Subtract 1 day so it displays it as the previous day data (Since we enter in right when the new day starts)
            except AttributeError as e:
                date_key = str(time_val)[:10]
                capture_exception(e)

            if date_key not in dats:
                dats[date_key] = {
                    'number_of_users': 0,
                    'number_of_active_sessions': 0,
                    'searches_today': 0,
                    'number_of_admins': 0,
                    'paying_premium_users': 0,
                    'basic_users': 0,
                    'sponsored_premium_users': 0,
                    'active_users_today': 0
                }

            dats[date_key]['number_of_users'] += int(users or 0)
            dats[date_key]['number_of_active_sessions'] += int(sessions or 0)
            dats[date_key]['searches_today'] += int(searches or 0)
            dats[date_key]['number_of_admins'] += int(admins or 0)
            dats[date_key]['paying_premium_users'] += int(paying_premium or 0)
            dats[date_key]['basic_users'] += int(basic or 0)
            dats[date_key]['sponsored_premium_users'] += int(sponsored_premium or 0)
            dats[date_key]['active_users_today'] += int(active_users_today or 0)


        return dats

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return {}
    finally:
        this_session.remove()
        return dats

def count_admins():
    """
    Returns the total number of rows in the admin_user_list table.

    :return: Integer count or None if an error occurs
    """
    this_session = Session
    try:
        result = this_session.execute(text(f"SELECT COUNT(*) FROM {admin_list_table} WHERE email NOT LIKE '%sample.admin%' AND email NOT LIKE '%@rezify.ai%'")).scalar()
        this_session.remove()
        return result
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None



def get_super_admin_users_data():
    return {
        'active_users_now': get_current_active_users_counts(),
        'users_breakdown': get_user_breakdown(),
        'users_by_school': get_user_counts_by_school(),
        'admin_count': count_admins(),
        'users_historical': get_users_historical_data()
    }

def get_jobs_historical_data():
    this_session = Session
    dats = {}

    try:

        # PART 1: Get job count over time from jobs_data_hist table
        rows = this_session.execute(text(f'''
                    SELECT time, current_internships
                    FROM {jobs_data_hist_table}
                    ORDER BY time
                ''')).fetchall()

        for time_val, current_internships in rows:
            # time_val may be a datetime or a string; normalize to YYYY-MM-DD
            try:
                date_key = (time_val.date() - timedelta(
                    days=1)).isoformat()  ## Subtract 1 day so it displays it as the previous day data (Since we enter in right when the new day starts)
            except AttributeError as e:
                date_key = str(time_val)[:10]
                capture_exception(e)

            if date_key not in dats:
                dats[date_key] = {
                    'internships_total': 0,
                    'link_html_deleted': 0,
                    'age_deleted': 0,
                    'deduplicate_deleted': 0,
                    'deletion_condition_deleted': 0,
                    'linkedin_deleted': 0,
                    'indeed_deleted': 0,
                    'cut_internships': 0,
                    'cut_fulltime': 0,
                }

            dats[date_key]['internships_total'] += int(current_internships or 0)


        # PART 2: Get jobs deleted history by type from jobs_cleaning_hist
        rows = this_session.execute(text(f'''
                            SELECT time, link_html_deleted, age_deleted, deduplicate_deleted, deletion_condition_deleted, linkedin_deleted, indeed_deleted
                            FROM {internships_cleaning_hist_table}
                            ORDER BY time
                        ''')).fetchall()

        for time_val, link_html_deleted, age_deleted, deduplicate_deleted, deletion_condition_deleted, linkedin_deleted, indeed_deleted in rows:
            # time_val may be a datetime or a string; normalize to YYYY-MM-DD
            try:
                date_key = (time_val.date() - timedelta(
                    days=1)).isoformat()  ## Subtract 1 day so it displays it as the previous day data (Since we enter in right when the new day starts)
            except AttributeError as e:
                date_key = str(time_val)[:10]
                capture_exception(e)

            if date_key not in dats:
                dats[date_key] = {
                    'internships_total': 0,
                    'link_html_deleted': 0,
                    'age_deleted': 0,
                    'deduplicate_deleted': 0,
                    'deletion_condition_deleted': 0,
                    'linkedin_deleted': 0,
                    'indeed_deleted': 0,
                    'cut_internships': 0,
                    'cut_fulltime': 0,
                }

            dats[date_key]['link_html_deleted'] += int(link_html_deleted or 0)
            dats[date_key]['age_deleted'] += int(age_deleted or 0)
            dats[date_key]['deduplicate_deleted'] += int(deduplicate_deleted or 0)
            dats[date_key]['deletion_condition_deleted'] += int(deletion_condition_deleted or 0)
            dats[date_key]['linkedin_deleted'] += int(linkedin_deleted or 0)
            dats[date_key]['indeed_deleted'] += int(indeed_deleted or 0)


        # PART 3: Get credits used by type over time from ts_data table
        rows = this_session.execute(text('''
                                    SELECT time, cut_internships, cut_fulltime
                                    FROM ts_data
                                    ORDER BY time
                                ''')).fetchall()

        for time_val, cut_internships, cut_fulltime in rows:
            # time_val may be a datetime or a string; normalize to YYYY-MM-DD
            try:
                date_key = (time_val.date() - timedelta(
                    days=1)).isoformat()  ## Subtract 1 day so it displays it as the previous day data (Since we enter in right when the new day starts)
            except AttributeError as e:
                date_key = str(time_val)[:10]
                capture_exception(e)

            if date_key not in dats:
                dats[date_key] = {
                    'internships_total': 0,
                    'link_html_deleted': 0,
                    'age_deleted': 0,
                    'deduplicate_deleted': 0,
                    'deletion_condition_deleted': 0,
                    'linkedin_deleted': 0,
                    'indeed_deleted': 0,
                    'cut_internships': 0,
                    'cut_fulltime': 0,
                }

            dats[date_key]['cut_internships'] += int(cut_internships or 0)
            dats[date_key]['cut_fulltime'] += int(cut_fulltime or 0)


        return dats

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return {}
    finally:
        this_session.remove()
        return dats



def get_ts_credits_percentage_and_total():
    """
    Returns the percentage and total of Theirstack credits used.

    :return: Dictionary containing the percentage of 'ts_credits_percentage' and integer of 'ts_credits_used'
    """
    try:
        results = {}
        ts_data = get_theirstack_data()

        percentage = 100 * (ts_data['used_api_credits']/ts_data['api_credits'])
        results['ts_credits_percentage'] = round(percentage, 2)

        total = ts_data['used_api_credits']
        results['ts_credits_used'] = total
        return results
    except Exception as e:
        capture_exception(e)
        return None


def get_credits_30day_avg():
    """
    Calculates the average of credits_used_today from ts_data
    over the past 30 days.

    :return: Float average value or None if no data or error occurs
    """
    this_session = Session
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

        result = this_session.execute(text('''
            SELECT AVG(credits_used_today)
            FROM ts_data
            WHERE time >= :cutoff_date
        '''), {'cutoff_date': cutoff_date}).scalar()

        this_session.remove()
        return round(float(result), 2) if result is not None else 0.0

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


def get_most_recent_purchase():
    """
    Retrieves the most recent purchase from ts_purchases.

    :return: dict with:
             {
                'date': 'MM-DD-YY',
                'credits_purchased': int,
                'amount_spent': float,
                'days_since_purchase': int
             }
             or None if no purchases or error
    """
    this_session = Session
    try:
        result = this_session.execute(text(f'''
            SELECT time, amount_spent, credits_purchased
            FROM {ts_purchases_table}
            ORDER BY time DESC
            LIMIT 1
        ''')).fetchone()

        this_session.remove()

        if not result:
            return None

        time, amount_spent, credits_purchased = result
        now = datetime.now(timezone.utc)

        # Compute days since purchase
        days_since = (now - time).days if time else None

        return {
            'date': time.strftime('%m-%d-%y') if time else None,
            'credits_purchased': int(credits_purchased),
            'amount_spent': float(amount_spent),
            'days_since_purchase': days_since
        }

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


def estimate_next_credit_purchase():
    """
    Estimates when credits will run out based on:
      - current credits remaining (from get_theirstack_data)
      - average daily consumption over the last 30 days (from get_credits_30day_avg)

    :return: dict like:
             {
                 'estimated_runout_date': 'MM-DD-YY',
                 'days_remaining': int
             }
             or None if data is missing or an error occurs
    """
    try:
        ts_data = get_theirstack_data()
        credits_left = ts_data['api_credits'] - ts_data['used_api_credits']
        credit_avg_thirty_days = get_credits_30day_avg()

        # Validate that we have meaningful values
        if not credit_avg_thirty_days or credit_avg_thirty_days <= 0:
            return None

        # Estimate how many days left
        days_remaining = int(credits_left / credit_avg_thirty_days)

        # Calculate estimated date
        runout_date = datetime.now(timezone.utc) + timedelta(days=days_remaining)
        formatted_date = runout_date.strftime('%m-%d-%y')

        return {
            'estimated_next_purchase': formatted_date,
            'days_remaining': days_remaining
        }

    except Exception as e:
        capture_exception(e)
        return None

def get_removed_jobs_list():
    """
    Retrieves list of jobs from removed_jobs_global.

    :return: list of jobs
    """
    this_session = Session
    try:
        results = this_session.execute(text(f'''
            SELECT id, count, reasons, title, company, final_url, date_posted, first_addition
            FROM {removed_jobs_global_table}
            WHERE final_url IS NOT NULL
            ORDER BY first_addition DESC
        ''')).fetchall()

        this_session.remove()

        jobs = []
        for job in results:
            # Set the dictionary representing the job
            job = {
                'id': job[0],
                'count': job[1],
                'reasons': job[2],
                'title': job[3],
                'company': job[4],
                'final_url': job[5],
                'date_posted': job[6]
            }
            jobs.append(job)

        return jobs

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return []


def delete_job_from_removed_list(job_id):
    """
    Delete a job from the database using its ID
    :param job_id: integer of the id of the job to delete
    :return: None
    """
    session = Session
    try:
        # Delete the job with the specified id
        session.execute(
            text(f'DELETE FROM {removed_jobs_global_table} WHERE id = :id'),
            {'id': job_id}
        )

        # Commit the transaction
        session.commit()

    except Exception as e:
        session.rollback()
        capture_exception(e)
    finally:
        session.remove()




def get_super_admin_jobs_data():
    return {
        'internships_in_table': get_jobs_database_length(),
        'internships_title_embeddings': get_title_document_count_internships(),
        'internships_description_embeddings': get_description_document_count_internships(),
        'ts_credits_percentage': get_ts_credits_percentage_and_total(),
        'jobs_historical': get_jobs_historical_data(),
        'thirty_day_credits_avg': get_credits_30day_avg(),
        'latest_purchase': get_most_recent_purchase(),
        'estimated_next_credit_purchase': estimate_next_credit_purchase(),
        'removed_jobs': get_removed_jobs_list()
    }


def get_total_applications():
    """
    Given a list of user emails, returns the total number of applications submitted
    by summing the length of the applied_to list (JSON) for each user.

    :return: Integer total of all applications
    """

    this_session = Session
    try:
        # Query applied_to field for all users in the list
        results = this_session.execute(text(f'''
            SELECT applied_to
            FROM {users_list_table}
            WHERE email NOT LIKE '%sample.student%'
        ''')).fetchall()

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


def get_total_favorites():
    """
    returns the total number of favorites submitted
    by summing the length of the favorites list (JSON) for each user.

    :return: Integer total of all favorites
    """

    this_session = Session
    try:
        # Query favorites field for all users in the list
        results = this_session.execute(text(f'''
            SELECT favorites
            FROM {users_list_table}
            WHERE email NOT LIKE '%sample.student%'
        ''')).fetchall()

        total_favorites = 0
        for row in results:
            favorites = row[0]
            if isinstance(favorites, list):
                total_favorites += len(favorites)
            elif isinstance(favorites, str):
                # if accidentally stored as a stringified JSON
                try:
                    favorites_list = json.loads(favorites)
                    if isinstance(favorites_list, list):
                        total_favorites += len(favorites_list)
                except Exception as e:
                    capture_exception(e)

        return total_favorites

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return 0
    finally:
        this_session.remove()

def get_total_accepted():
    """
    returns the total number of jobs accepted
    by summing the length of the accepted list (JSON) for each user.

    :return: Integer total of all jobs_accepted
    """

    this_session = Session
    try:
        # Query accepted field for all users in the list
        results = this_session.execute(text(f'''
            SELECT jobs_accepted
            FROM {users_list_table}
            WHERE email NOT LIKE '%sample.student%'
        ''')).fetchall()

        total_jobs_accepted = 0
        for row in results:
            jobs_accepted = row[0]
            if isinstance(jobs_accepted, list):
                total_jobs_accepted += len(jobs_accepted)
            elif isinstance(jobs_accepted, str):
                # if accidentally stored as a stringified JSON
                try:
                    jobs_accepted_list = json.loads(jobs_accepted)
                    if isinstance(jobs_accepted_list, list):
                        total_jobs_accepted += len(jobs_accepted_list)
                except Exception as e:
                    capture_exception(e)

        return total_jobs_accepted

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return 0
    finally:
        this_session.remove()


def get_total_messages_generated():
    """
    returns the total number of messages_generated
    by summing the length of the accepted list (JSON) for each user.

    :return: Integer total of all messages_generated
    """

    this_session = Session
    try:
        # Query accepted field for all users in the list
        results = this_session.execute(text(f'''
            SELECT messages_generated
            FROM {users_list_table}
            WHERE email NOT LIKE '%sample.student%'
        ''')).fetchall()

        total_messages_generated = 0
        for row in results:
            messages_generated = row[0]
            if isinstance(messages_generated, list):
                total_messages_generated += len(messages_generated)
            elif isinstance(messages_generated, str):
                # if accidentally stored as a stringified JSON
                try:
                    messages_generated_list = json.loads(messages_generated)
                    if isinstance(messages_generated_list, list):
                        total_messages_generated += len(messages_generated_list)
                except Exception as e:
                    capture_exception(e)

        return total_messages_generated

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return 0
    finally:
        this_session.remove()


def get_daily_search_counts():
    """
    Returns counts of searches in the last 24 hours by type, restricted to:
    'homepage', 'refresh', and 'add_title'.

    :return: {
        'homepage_searches': int,
        'refresh_searches': int,
        'add_title_searches': int,
        'total_searches': int
    } or None on error
    """
    this_session = Session
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        row = this_session.execute(text(f"""
            SELECT
                COALESCE(SUM(CASE WHEN type = 'homepage' THEN 1 ELSE 0 END), 0) AS homepage_searches,
                COALESCE(SUM(CASE WHEN type = 'refresh' THEN 1 ELSE 0 END), 0)   AS refresh_searches,
                COALESCE(SUM(CASE WHEN type = 'add_title' THEN 1 ELSE 0 END), 0) AS add_title_searches,
                COALESCE(COUNT(*), 0)                                            AS total_searches
            FROM {searches_table}
            WHERE time_of_search >= :cutoff
              AND type IN ('homepage', 'refresh', 'add_title')
        """), {"cutoff": cutoff}).fetchone()

        # Row is a SQLAlchemy Row; support key or index access.
        if hasattr(row, "_mapping"):
            data = dict(row._mapping)
        else:
            data = {
                "homepage_searches": row[0],
                "refresh_searches": row[1],
                "add_title_searches": row[2],
                "total_searches": row[4],
            }

        # Ensure pure ints
        return {
            "homepage_searches": int(data["homepage_searches"]),
            "refresh_searches": int(data["refresh_searches"]),
            "add_title_searches": int(data["add_title_searches"]),
            "total_searches": int(data["total_searches"]),
        }

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return None
    finally:
        this_session.remove()



def get_daily_homepage_searchtime():
    """
    Computes per-key average runtimes from `runtimes_dict` for rows in `searches`
    where type='homepage' and time_of_search is within the last 24 hours.

    The `runtimes_dict` column contains a JSON/dict like:
      {"job 1": 2.2, "job 2": 3.1, "total": 5.3}

    :return: dict mapping each key to its average (rounded to 3 decimals).
             Example:
             {
               "job 1": 2.033,
               "job 2": 3.412,
               "total": 5.221
             }
             Returns {} if no qualifying rows or no numeric values found.
    """
    this_session = Session
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        rows = this_session.execute(text(f"""
            SELECT runtimes_dict
            FROM {searches_table}
            WHERE type = 'homepage'
              AND time_of_search >= :cutoff
              AND runtimes_dict IS NOT NULL
        """), {"cutoff": cutoff}).fetchall()

        if not rows:
            return {}

        sums = {}   # key -> float sum
        counts = {} # key -> int count

        def to_dict(value):
            # Accept dicts (JSONB/native) or JSON strings
            if value is None:
                return None
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return None
            return None

        for (payload,) in rows:
            d = to_dict(payload)
            if not isinstance(d, dict):
                continue

            for k, v in d.items():
                # Only average numeric values
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    sums[k] = sums.get(k, 0.0) + float(v)
                    counts[k] = counts.get(k, 0) + 1

        if not sums:
            return {}

        averages = {k: round(sums[k] / counts[k], 3) for k in sums.keys()}
        return averages

    except Exception as e:
        capture_exception(e)
        try:
            this_session.rollback()
        except Exception as e:
            capture_exception(e)
            pass
        return {}
    finally:
        try:
            this_session.remove()
        except Exception as e:
            capture_exception(e)
            pass


def get_daily_refresh_addtitle_searchtime():
    """
    Computes per-key average runtimes from `runtimes_dict` for rows in `searches`
    where type is either 'refresh' or 'add_title', and time_of_search is within
    the last 24 hours.

    The `runtimes_dict` column contains a JSON/dict like:
      {"job 1": 2.2, "job 2": 3.1, "total": 5.3}

    :return: dict mapping each key to its average runtime (rounded to 3 decimals).
             Example:
             {
               "job 1": 1.953,
               "job 2": 2.721,
               "total": 4.132
             }
             Returns {} if no qualifying rows or numeric values found.
    """
    this_session = Session
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        rows = this_session.execute(text(f"""
            SELECT runtimes_dict
            FROM {searches_table}
            WHERE type IN ('refresh', 'add_title')
              AND time_of_search >= :cutoff
              AND runtimes_dict IS NOT NULL
        """), {"cutoff": cutoff}).fetchall()

        if not rows:
            return {}

        sums = {}
        counts = {}

        def to_dict(value):
            if value is None:
                return None
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return None
            return None

        for (payload,) in rows:
            d = to_dict(payload)
            if not isinstance(d, dict):
                continue
            for k, v in d.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    sums[k] = sums.get(k, 0.0) + float(v)
                    counts[k] = counts.get(k, 0) + 1

        if not sums:
            return {}

        return {k: round(sums[k] / counts[k], 3) for k in sums.keys()}

    except Exception as e:
        capture_exception(e)
        try:
            this_session.rollback()
        except Exception as e:
            capture_exception(e)
            pass
        return {}
    finally:
        try:
            this_session.remove()
        except Exception as e:
            capture_exception(e)
            pass


def get_daily_parseexp_avg_runtime():
    """
    Returns the average runtime (float, rounded to 3 decimals)
    for rows in the `searches` table where:
      - type = 'parse_exp'
      - time_of_search is within the last 24 hours.

    :return: float average runtime or 0.0 if no qualifying rows.
    """
    this_session = Session
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        result = this_session.execute(text(f"""
            SELECT AVG(runtime)
            FROM {searches_table}
            WHERE type = 'parse_exp'
              AND time_of_search >= :cutoff
              AND runtime IS NOT NULL
        """), {"cutoff": cutoff}).fetchone()

        avg_runtime = result[0] if result and result[0] is not None else 0.0
        return round(float(avg_runtime), 3)

    except Exception as e:
        capture_exception(e)
        try:
            this_session.rollback()
        except Exception as e:
            capture_exception(e)
            pass
        return 0.0
    finally:
        try:
            this_session.remove()
        except Exception as e:
            capture_exception(e)
            pass


def get_usage_historical_data():
    this_session = Session
    dats = {}

    try:

        rows = this_session.execute(text(f'''
                    SELECT time, homepage_searches, add_title_searches, refresh_searches, parse_exp_searchtime, total_favorites, total_applications, total_li_messages, total_accepted, homepage_searchtime, add_refresh_searchtime, linkedin_clicks
                    FROM {traffic_history_table}
                    ORDER BY time
                ''')).fetchall()

        for time_val, homepage_searches, add_title_searches, refresh_searches, parse_exp_searchtime, total_favorites, total_applications, total_li_messages, total_accepted, homepage_searchtime, add_refresh_searchtime, linkedin_clicks in rows:
            # time_val may be a datetime or a string; normalize to YYYY-MM-DD
            try:
                date_key = (time_val.date() - timedelta(
                    days=1)).isoformat()  ## Subtract 1 day so it displays it as the previous day data (Since we enter in right when the new day starts)
            except AttributeError as e:
                date_key = str(time_val)[:10]
                capture_exception(e)

            if date_key not in dats:
                dats[date_key] = {
                    'homepage_searches': 0,
                    'add_title_searches': 0,
                    'refresh_searches': 0,
                    'parse_exp_searchtime': 0,
                    'total_favorites': 0,
                    'total_applications': 0,
                    'total_li_messages': 0,
                    'total_accepted': 0,
                    'linkedin_clicks': 0
                }

            dats[date_key]['homepage_searches'] += int(homepage_searches or 0)

            if 'Job 0: Parse Resume Time' in homepage_searchtime:
                dats[date_key]['h_job_0_parse_resume'] = homepage_searchtime['Job 0: Parse Resume Time']
            if 'Job 1: Generate Embeddings Time' in homepage_searchtime:
                dats[date_key]['h_job_1_gen_embeddings'] = homepage_searchtime['Job 1: Generate Embeddings Time']
            if 'Job 2: KNN Title Searching Time' in homepage_searchtime:
                dats[date_key]['h_job_2_knn_title'] = homepage_searchtime['Job 2: KNN Title Searching Time']
            if 'Job 3: KNN Description Search Time' in homepage_searchtime:
                dats[date_key]['h_job_3_knn_description'] = homepage_searchtime['Job 3: KNN Description Search Time']
            if 'Job 4: Combine IDs and get jobs' in homepage_searchtime:
                dats[date_key]['h_job_4_get_jobs'] = homepage_searchtime['Job 4: Combine IDs and get jobs']
            if 'Job 5: Final Computation and Sort' in homepage_searchtime:
                dats[date_key]['h_job_5_compute_sort'] = homepage_searchtime['Job 5: Final Computation and Sort']
            if 'Total Time' in homepage_searchtime:
                dats[date_key]['total_homepage_time'] = homepage_searchtime['Total Time']

            if 'Job 1: Generate Embeddings Time' in add_refresh_searchtime:
                dats[date_key]['ar_job_1_gen_embeddings'] = add_refresh_searchtime['Job 1: Generate Embeddings Time']
            if 'Job 2: KNN Title Searching Time' in add_refresh_searchtime:
                dats[date_key]['ar_job_2_knn_title'] = add_refresh_searchtime['Job 2: KNN Title Searching Time']
            if 'Job 3: KNN Description Search Time' in add_refresh_searchtime:
                dats[date_key]['ar_job_3_knn_description'] = add_refresh_searchtime['Job 3: KNN Description Search Time']
            if 'Job 4: Combine IDs and get jobs' in add_refresh_searchtime:
                dats[date_key]['ar_job_4_get_jobs'] = add_refresh_searchtime['Job 4: Combine IDs and get jobs']
            if 'Job 5: Final Computation and Sort' in add_refresh_searchtime:
                dats[date_key]['ar_job_5_compute_sort'] = add_refresh_searchtime['Job 5: Final Computation and Sort']
            if 'Total Time' in add_refresh_searchtime:
                dats[date_key]['total_add_refresh_time'] = add_refresh_searchtime['Total Time']

            dats[date_key]['add_title_searches'] += int(add_title_searches or 0)
            dats[date_key]['refresh_searches'] += int(refresh_searches or 0)
            if parse_exp_searchtime <= 0:
                dats[date_key].pop('parse_exp_searchtime')
            else:
                dats[date_key]['parse_exp_searchtime'] += float(parse_exp_searchtime or 0)
            dats[date_key]['total_favorites'] += int(total_favorites or 0)
            dats[date_key]['total_applications'] += int(total_applications or 0)
            dats[date_key]['total_li_messages'] += int(total_li_messages or 0)
            dats[date_key]['total_accepted'] += int(total_accepted or 0)
            dats[date_key]['linkedin_clicks'] += int(linkedin_clicks or 0)

        return dats

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return {}
    finally:
        this_session.remove()
        return dats


def get_top_searches(limit=10):
    """
    Returns the top 10 most common cleaned intern_titles across users.
    Removes trailing 'Intern' or 'Internship' from each title.

    :return: List of dictionaries [{ "term": str, "count": int }]
    """


    this_session = Session
    try:
        # Query intern_titles JSON field
        results = this_session.execute(text(f'''
            SELECT intern_titles
            FROM {users_list_table}
            WHERE email NOT LIKE '%sample.student%'
        ''')).fetchall()

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


def top_companies_applied(limit=10):
    """
    Returns the top 10 most common companies users have applied to, based on
    the 'applied_to' list in users_list.

    :return: List of dictionaries [{ "company": str, "count": int }]
    """

    this_session = Session
    try:
        # Query the applied_to field
        results = this_session.execute(text(f'''
            SELECT applied_to
            FROM {users_list_table}
            WHERE email NOT LIKE '%sample.student%'
        ''')).fetchall()

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


def top_jobs_applied(limit=10):
    """
    Returns the top 10 most common jobs (by job ID) users have applied to.
    Each result includes job ID, company, title, location, and count.

    :return: List of dictionaries [{ "id", "company", "title", "location", "count" }]
    """

    this_session = Session
    try:
        results = this_session.execute(text(f'''
            SELECT applied_to
            FROM {users_list_table}
            WHERE email NOT LIKE '%sample.student%'
        ''')).fetchall()

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

        top_jobs = job_counter.most_common(limit)

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


def get_top_users(limit=20):
    """
    Returns the top users by overall usage score across favorites, applied_to, and messages_generated.
    Score = len(favorites) + len(applied_to) + len(messages_generated)

    :return: List of dictionaries sorted by score DESC, limited by `limit`.
             Each item: {
                 "User": "First Last (email)",
                 "total_usage_score": int,
                 "favorites_count": int,
                 "applied_to_count": int,
                 "messages_generated_count": int
             }
    """
    this_session = Session
    try:
        results = this_session.execute(text(f'''
            SELECT first_name, last_name, email, favorites, applied_to, messages_generated
            FROM {users_list_table}
            WHERE email NOT LIKE '%sample.student%'
        ''')).fetchall()

        def to_list(value):
            if value is None:
                return []
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    return parsed if isinstance(parsed, list) else []
                except Exception as e:
                    capture_exception(e)
                    return []
            return []

        users_usage = []

        for first_name, last_name, email, favorites, applied_to, messages_generated in results:
            fav_list = to_list(favorites)
            applied_list = to_list(applied_to)
            msgs_list = to_list(messages_generated)

            fav_count = len(fav_list)
            applied_count = len(applied_list)
            msgs_count = len(msgs_list)

            total_score = fav_count + applied_count + msgs_count

            display_name = f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()
            if display_name:
                display_name = f"{display_name} ({email})"
            else:
                display_name = f"{email}"

            users_usage.append({
                "User": display_name,
                "total_usage_score": total_score,
                "favorites_count": fav_count,
                "applied_to_count": applied_count,
                "messages_generated_count": msgs_count,
            })

        users_usage.sort(key=lambda x: x["total_usage_score"], reverse=True)
        return users_usage[:limit]

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return []
    finally:
        this_session.remove()




def get_super_admin_usage_data():
    return {
        'day_search_data': get_recent_search_data(24),
        'total_favorites': get_total_favorites(),
        'total_applied': get_total_applications(),
        'total_messages_generated': get_total_messages_generated(),
        'total_accepted': get_total_accepted(),
        'usage_historical': get_usage_historical_data(),
        'top_searches': get_top_searches(),
        'top_companies_applied': top_companies_applied(),
        'top_jobs_applied': top_jobs_applied(),
        'top_users': get_top_users()
    }


# --- 30-day daily total spend average (averages per *calendar day*) ---
def get_30d_daily_total_spend_average():
    """
    Average daily total spend over the last 30 days.
    Computes per-day totals first, then averages those daily totals.
    Returns: float or None
    """
    this_session = Session
    try:
        result = this_session.execute(text(f"""
            WITH per_day AS (
                SELECT DATE(time) AS d, SUM(total_cost) AS day_total
                FROM {openai_usage_table}
                WHERE time >= NOW() - INTERVAL '30 days'
                GROUP BY 1
            )
            SELECT AVG(day_total) AS avg_daily_total
            FROM per_day
        """)).scalar()
        this_session.remove()
        return float(result) if result is not None else None
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


# --- YTD total spend ---
def get_ytd_total_spend():
    """
    Total spend from Jan 1 of the current year (UTC) through now.
    Returns: float or None
    """
    this_session = Session
    try:
        result = this_session.execute(text(f"""
            SELECT SUM(total_cost)
            FROM {openai_usage_table}
            WHERE time >= DATE_TRUNC('year', NOW())
              AND time < NOW()
        """)).scalar()
        this_session.remove()
        return float(result) if result is not None else None
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


# --- MTD total spend ---
def get_mtd_total_spend():
    """
    Total spend from the first day of the current month (UTC) through now.
    Returns: float or None
    """
    this_session = Session
    try:
        result = this_session.execute(text(f"""
            SELECT SUM(total_cost)
            FROM {openai_usage_table}
            WHERE time >= DATE_TRUNC('month', NOW())
              AND time < NOW()
        """)).scalar()
        this_session.remove()
        return float(result) if result is not None else None
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


# --- Last month total spend (None if no rows last month) ---
def get_last_month_total_spend():
    """
    Total spend for the previous calendar month (UTC).
    If there are no rows in that interval, returns None.
    Returns: float or None
    """
    this_session = Session
    try:
        result = this_session.execute(text(f"""
            SELECT SUM(total_cost)
            FROM {openai_usage_table}
            WHERE time >= DATE_TRUNC('month', NOW()) - INTERVAL '1 month'
              AND time <  DATE_TRUNC('month', NOW())
        """)).scalar()
        this_session.remove()
        # If no rows existed, SUM will be NULL -> return None (as requested)
        return float(result) if result is not None else None
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


# --- 30-day spend breakdown (sum by category over last 30 days) ---
def get_30d_spend_breakdown():
    """
    Sum of each cost category over the last 30 days.
    Returns: dict with keys:
      main_search_cost, message_generation_cost, add_title_cost, refresh_cost, elasticsearch_embeddings_cost
    """
    this_session = Session
    try:
        row = this_session.execute(text(f"""
            SELECT
              COALESCE(SUM(main_search_cost), 0)                AS main_search_cost,
              COALESCE(SUM(message_generation_cost), 0)         AS message_generation_cost,
              COALESCE(SUM(add_title_cost), 0)                  AS add_title_cost,
              COALESCE(SUM(refresh_cost), 0)                    AS refresh_cost,
              COALESCE(SUM(elasticsearch_embeddings_cost), 0)   AS elasticsearch_embeddings_cost
            FROM {openai_usage_table}
            WHERE time >= NOW() - INTERVAL '30 days'
        """)).mappings().one()
        this_session.remove()
        return {
            'main_search_cost': float(row['main_search_cost']),
            'message_generation_cost': float(row['message_generation_cost']),
            'add_title_cost': float(row['add_title_cost']),
            'refresh_cost': float(row['refresh_cost']),
            'elasticsearch_embeddings_cost': float(row['elasticsearch_embeddings_cost']),
        }
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return {
            'main_search_cost': 0.0,
            'message_generation_cost': 0.0,
            'add_title_cost': 0.0,
            'refresh_cost': 0.0,
            'elasticsearch_embeddings_cost': 0.0,
        }


# --- 30-day averages for all *_cost_pr columns ---
def get_30d_avg_cost_pr():
    """
    Average of the *_cost_pr columns over the last 30 days.
    (AVG ignores NULLs; if a column is entirely NULL, the result will be None.)
    Returns: dict with keys:
      main_search_cost_pr, message_generation_cost_pr, add_title_cost_pr, refresh_cost_pr
    """
    this_session = Session
    try:
        row = this_session.execute(text(f"""
            SELECT
              AVG(main_search_cost_pr)        AS main_search_cost_pr,
              AVG(message_generation_cost_pr) AS message_generation_cost_pr,
              AVG(add_title_cost_pr)          AS add_title_cost_pr,
              AVG(refresh_cost_pr)            AS refresh_cost_pr,
              AVG(elasticsearch_embeddings_cost) AS elasticsearch_embeddings_cost
            FROM {openai_usage_table}
            WHERE time >= NOW() - INTERVAL '30 days'
        """)).mappings().one()
        this_session.remove()
        # Keep None if there's no data for a metric in the window
        return {
            'main_search_cost_pr': float(row['main_search_cost_pr']) if row['main_search_cost_pr'] is not None else None,
            'message_generation_cost_pr': float(row['message_generation_cost_pr']) if row['message_generation_cost_pr'] is not None else None,
            'add_title_cost_pr': float(row['add_title_cost_pr']) if row['add_title_cost_pr'] is not None else None,
            'refresh_cost_pr': float(row['refresh_cost_pr']) if row['refresh_cost_pr'] is not None else None,
            'elasticsearch_embeddings_cost_per_day': float(row['elasticsearch_embeddings_cost']) if row['elasticsearch_embeddings_cost'] is not None else None,
        }
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return {
            'main_search_cost_pr': None,
            'message_generation_cost_pr': None,
            'add_title_cost_pr': None,
            'refresh_cost_pr': None,
            'elasticsearch_embeddings_cost_per_day': None
        }

def get_openai_historical_data():
    this_session = Session
    dats = {}

    try:

        rows = this_session.execute(text(f'''
                    SELECT time, total_cost, main_search_cost, main_search_cost_pr, message_generation_cost, message_generation_cost_pr,
                        add_title_cost, add_title_cost_pr, refresh_cost, refresh_cost_pr, elasticsearch_embeddings_cost
                    FROM {openai_usage_table}
                    ORDER BY time
                ''')).fetchall()

        for time_val, total_cost, main_search_cost, main_search_cost_pr, message_generation_cost, message_generation_cost_pr, add_title_cost, add_title_cost_pr, refresh_cost, refresh_cost_pr, elasticsearch_embeddings_cost in rows:
            # Normalize time_val → always get a `date` object
            if isinstance(time_val, datetime):
                actual_date = time_val.date()
            elif isinstance(time_val, date):
                actual_date = time_val
            else:
                # Fallback for string or weird values
                try:
                    actual_date = datetime.fromisoformat(str(time_val)).date()
                except Exception as e:
                    capture_exception(e)
                    actual_date = datetime.now(timezone.utc).date()

            # Subtract 1 day
            date_key = (actual_date - timedelta(days=1)).isoformat()


            if date_key not in dats:
                dats[date_key] = {
                    'total_cost': 0,
                    'main_search_cost': 0,
                    'message_generation_cost': 0,
                    'add_title_cost': 0,
                    'refresh_cost': 0,
                    'elasticsearch_embeddings_cost': 0
                }

            dats[date_key]['total_cost'] += float(total_cost or 0)
            dats[date_key]['main_search_cost'] += float(main_search_cost or 0)
            dats[date_key]['message_generation_cost'] += float(message_generation_cost or 0)
            dats[date_key]['add_title_cost'] += float(add_title_cost or 0)
            dats[date_key]['refresh_cost'] += float(refresh_cost or 0)
            dats[date_key]['elasticsearch_embeddings_cost'] += float(elasticsearch_embeddings_cost or 0)
            if main_search_cost_pr:
                dats[date_key]['main_search_cost_pr'] = float(main_search_cost_pr or 0)
            if message_generation_cost_pr:
                dats[date_key]['message_generation_cost_pr'] = float(message_generation_cost_pr or 0)
            if add_title_cost_pr:
                dats[date_key]['add_title_cost_pr'] = float(add_title_cost_pr or 0)
            if refresh_cost_pr:
                dats[date_key]['refresh_cost_pr'] = float(refresh_cost_pr or 0)


        return dats

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return {}
    finally:
        this_session.remove()
        return dats


def get_super_admin_openai_data():
    return {
        'thirtyd_total_avg_spend': get_30d_daily_total_spend_average(),
        'ytd_total_spend': get_ytd_total_spend(),
        'mtd_total_spend': get_mtd_total_spend(),
        'last_month_total_spend': get_last_month_total_spend(),
        'thirtyd_spend_breakdown': get_30d_spend_breakdown(),
        'thirtyd_cost_prs': get_30d_avg_cost_pr(),
        'openai_historical': get_openai_historical_data()
    }



if __name__ == "__main__":
    # users_list = get_user_list_for_school('rezifyadmin')
    dates = get_openai_historical_data()
    for dat in dates:
        print(dat)
        print(dates[dat])
        print('-----------')
