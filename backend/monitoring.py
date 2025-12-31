import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from backend.internships_elasticsearch_config import get_title_document_count_internships, get_description_document_count_internships
from backend.tables import jobs_data_hist_table, users_list_table, searches_table, sessions_table, traffic_history_table, \
    ts_calls_table, ts_data_table, internships_table
from datetime import datetime, timezone
from backend.database_config import Session, sessions_data_name
import os
from dotenv import load_dotenv
from sqlalchemy import text
from datetime import timedelta
import json
from sentry_sdk import capture_exception, capture_message

"""
monitoring.py is a file that contains functions to be used for sending monitoring and status emails to keep owners
updated while not having to manually log in. The purpose is for the IT team to keep an eye on things and notice
if things are going wrong.

Any new updated or functions involving sending monitoring emails should be added here.
"""


load_dotenv()


def get_jobs_database_length():
    """
    Get the number of jobs in the internships table.
    :return: integer representing the number of jobs in the database
    """
    session = Session
    try:
        result = session.execute(text(f'SELECT COUNT(*) FROM {internships_table}')).fetchall()  # Select the number of rows in internships table
        session.remove()
        if result[0][0] == 0:
            capture_message('ERROR: 0 jobs found in database', level="error")

        return result[0][0]

    except Exception as e:
        capture_exception(e)
        session.remove()
        return 0



def get_theirstack_data():
    """
    Getting account data from the TheirStack API

    :return: a dictionary representing requested data from TheirStack account
    """
    try:
        url = "https://api.theirstack.com/v0/billing/credit-balance"

        headers = {
            "Authorization": f"Bearer {os.getenv('THEIRSTACK_API_KEY')}"}

        response = requests.get(url, headers=headers)

        data = response.json()

        return data

    except Exception as e:
        capture_exception(e)
        return {}



def send_daily_monitoring_email(email):
    """
    This function handles the sending of the monitoring email. It sends TheirStack account info, job count in
    heroku postgresql database, document count in elasticsearch indexes, and search data.
    :param email: email address to end the email to
    :return: None
    """

    sender_email = "peter.h@rezify.ai"  # Email to send FROM
    sender_password = os.getenv("SENDER_PASSWORD")  # Password of sender account

    ts_data = get_theirstack_data()  # Get dat a from TheirStack


    # Get search data from the last 24 hours
    search_data = get_recent_search_data(24)

    # Format type distribution
    type_lines = ""
    for search_type, stats in search_data['type_distribution'].items():
        type_lines += f"  - {search_type}: {stats['count']} searches (avg runtime: {stats['average_runtime']}s)\n"

    # Content of the email to send
    subject = "Rezify Monitoring Email"
    body = (
        f"--- Jobs Monitoring ---\n"
        f"Difference in Jobs Today: {get_jobs_difference_today()}\n"
        f"Jobs in Heroku Postgres: {get_jobs_database_length()}\n"
        f"Titles in Elasticsearch: {get_title_document_count_internships()}\n"
        f"Descriptions in Elasticsearch: {get_description_document_count_internships()}\n\n"
        f"--- Credits Monitoring ---\n"
        f"Credits Used Today: {get_credits_used_today()}\n"
        f"Current API TheirStack Credits Used: {ts_data['used_api_credits']}\n"
        f"Current TheirStack Credits Left: {ts_data['api_credits'] - ts_data['used_api_credits']}\n"
        f"Total Credits This Period: {ts_data['api_credits']}\n"
        f"Percentage of Credits Used ({ts_data['used_api_credits']}/{ts_data['api_credits']}) = "
        f"{round(ts_data['used_api_credits'] / ts_data['api_credits'] * 100, 2)}%\n\n"
        f"--- Search Activity (Last 24 Hours) ---\n"
        f"Total Searches: {search_data['total_searches']}\n"
        f"Average Runtime: {search_data['average_runtime']}s\n"
        f"Unique Emails ({search_data['unique_emails_count']}): {', '.join(search_data['unique_emails'])}\n"
        f"Search Distribution by Type:\n{type_lines if type_lines else '  No data available.'}\n"
        f"--- Session Data ---\n"
        f"Logged In Users Active TODAY: {get_daily_active_sessions()}\n"
        f"Total Active Sessions: {count_sessions()}\n"
        f"Total Active Sessions_Data: {count_sessions_data()}\n\n"
        f"--- USERS ---\n"
        f"Total Users: {count_users()}\n"
    )

    msg = MIMEMultipart()
    msg['From'] = sender_email  # Send the email from the sender email
    recipients = [email, "peter.h@rezify.ai", "don.h@rezify.ai", "ishan.d@rezify.ai"]
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Send the email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipients, msg.as_string())
        server.quit()
    except Exception as e:
        capture_exception(e)



def add_search_data(runtime: float, type: str, email: str, runtimes_dict: dict):
    """
    This function adds a new search entry to the searches table. It adds the time of the search, the runtime, the type
    of search (where the search occured: homepage, refresh, etc), and the email of the user who made the search.
    This is for monitoring purposes and to see how long searches take, and well as for usage reporting.

    :param runtime: float representing the runtime of the search
    :param type: a string representing where the search occured (e.g., homepage, refresh, add_title)
    :param email: the email of the user who made the search
    :param runtimes_dict: dictionary of times for each part of algorithm
    :return:
    """
    this_session = Session
    try:
        # Insert a new search entry into the searches table
        this_session.execute(text(f'''
            INSERT INTO {searches_table} (time_of_search, runtime, type, email, runtimes_dict)
            VALUES (:time_of_search, :runtime, :type, :email, :runtimes_dict)
        '''), {
            'time_of_search': datetime.now(),
            'runtime': runtime,
            'type': type,
            'email': email,
            'runtimes_dict': json.dumps(runtimes_dict or {})
        })
        this_session.commit()
        this_session.remove()
        return True
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return False


def get_recent_search_data(hours: int):
    """
    This function retrieves recent search data from the searches table. It calculates the total number of searches,
    the average runtime, the number of unique emails, and the distribution of search types. It retrieves search data
    from the last 'hours' hours. This is used for monitoring and reporting purposes.

    :param hours: int representing the number of hours to look back for search data

    :return: a dictionary containing the total searches, average runtime, unique emails count, unique emails list,
                and type distribution
    """
    this_session = Session
    try:
        # Get timestamp cutoff
        time_cutoff = datetime.now() - timedelta(hours=hours)

        # Query all search rows within the time cutoff
        results = this_session.execute(text(f'''
            SELECT time_of_search, runtime, type, email
            FROM {searches_table}
            WHERE time_of_search >= :time_cutoff AND type != 'parse_exp'
        '''), {'time_cutoff': time_cutoff}).fetchall()

        this_session.commit()
        this_session.remove()

        if not results:
            # return empty stats if no results
            return {
                'total_searches': 0,
                'average_runtime': 0.0,
                'unique_emails_count': 0,
                'unique_emails': [],
                'type_distribution': {}
            }

        total_runtime = 0.0
        email_set = set()
        type_stats = {}  # {type: {'count': int, 'total_runtime': float}}

        for row in results:
            # Summarize the data and combine them where necessary
            _, runtime, type_val, email = row
            total_runtime += runtime
            if email:
                email_set.add(email)

            if type_val not in type_stats:
                type_stats[type_val] = {'count': 0, 'total_runtime': 0.0}
            type_stats[type_val]['count'] += 1
            type_stats[type_val]['total_runtime'] += runtime

        # Build type distribution with averages for each search type
        type_distribution = {
            t: {
                'count': stats['count'],
                'average_runtime': round(stats['total_runtime'] / stats['count'], 3)
            }
            for t, stats in type_stats.items()
        }

        return {
            # Return the results as a dictionary
            'total_searches': len(results),
            'average_runtime': round(total_runtime / len(results), 3),
            'unique_emails_count': len(email_set),
            'unique_emails': list(email_set),
            'type_distribution': type_distribution
        }

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


def delete_old_search_entries():
    """
    This function deletes old search entries from the searches table. It removes entries that are older than 40 days

    :return: boolean indicating success or failure
    """
    this_session = Session
    try:
        # Set the cutoff time to 40 days ago
        cutoff_time = datetime.now() - timedelta(days=40)

        # Delete old search entries over 40 days old
        this_session.execute(text(f'''
            DELETE FROM {searches_table}
            WHERE time_of_search < :cutoff_time
        '''), {'cutoff_time': cutoff_time})

        this_session.commit()
        this_session.remove()
        return True
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return False


def delete_old_sessions():
    """
    Deletes all expired Flask-Session rows from the 'sessions' table where expiry < NOW().
    Also deletes sessions whose stripped session_id (without 'session:' prefix) is not found in sessions_data.
    """
    this_session = Session
    try:
        # Delete all expired sessions
        this_session.execute(text(f'''
            DELETE FROM {searches_table}
            WHERE expiry < NOW()
        '''))

        # Delete sessions whose session_id (without 'session:' prefix) is not in sessions_data
        this_session.execute(text(f'''
            DELETE FROM {sessions_table}
            WHERE substring(session_id from 9) NOT IN (
                SELECT session_id FROM {sessions_data_name}
            )
        '''))

        this_session.commit()
        this_session.remove()
        return True
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return False


def count_sessions():
    """
    Returns the total number of rows in the 'sessions' table.
    """
    this_session = Session
    try:
        result = this_session.execute(text(f"SELECT COUNT(*) FROM {sessions_table}")).scalar()
        this_session.remove()
        return result
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


def count_sessions_data():
    """
    Returns the total number of rows in the 'sessions_data' table.
    """
    this_session = Session
    try:
        result = this_session.execute(text(f"SELECT COUNT(*) FROM {sessions_data_name}")).scalar()
        this_session.remove()
        return result
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


def add_TS_call(credits_consumed: int, call_type: str):
    """
    Adds a new row to the TS_calls table with the current Time timestamp,
    credits consumed, and call type.

    :param credits_consumed: Integer representing how many credits were used
    :param call_type: A string representing the type of call
    :return: Boolean indicating success or failure
    """
    this_session = Session
    try:

        # Ensure the TS_calls table exists
        this_session.execute(text(f'''
            CREATE TABLE IF NOT EXISTS {ts_calls_table} (
                time TIMESTAMP,
                credits_consumed INT,
                type TEXT
            )
        '''))

        # Insert a new row into TS_calls
        this_session.execute(text(f'''
            INSERT INTO {ts_calls_table} (time, credits_consumed, type)
            VALUES (:timestamp, :credits, :call_type)
        '''), {
            'timestamp': datetime.now(timezone.utc),
            'credits': credits_consumed,
            'call_type': call_type
        })

        this_session.commit()
        this_session.remove()
        return True
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return False


def add_TS_data(current_credits_used: int, cut_internships: int, cut_fulltime: int):
    """
    Adds a new row to the ts_data table with the current UTC time, the given credits_used,
    and credits_used_today calculated as the difference from the previous entry's credits_used.
    If the difference is negative or previous value is NULL, defaults appropriately.

    :param cut_fulltime: number of credits used today for fulltime jobs
    :param cut_internships: number of credits used today for internships
    :param current_credits_used: Integer of the current total credits used
    :return: Boolean indicating success or failure
    """
    this_session = Session
    try:
        # Ensure table exists
        this_session.execute(text(f'''
            CREATE TABLE IF NOT EXISTS {ts_data_table} (
                time TIMESTAMP,
                credits_used INT,
                credits_used_today INT,
                cut_internships INT,
                cut_fulltime INT
            )
        '''))

        # Fetch the most recent row
        previous_row = this_session.execute(text(f'''
            SELECT credits_used
            FROM {ts_data_table}
            ORDER BY time DESC
            LIMIT 1
        ''')).fetchone()

        # Calculate credits_used_today
        if previous_row and previous_row[0] is not None:
            diff = current_credits_used - previous_row[0]
            credits_used_today = diff if diff >= 0 else current_credits_used
        else:
            credits_used_today = None

        # Insert new row
        this_session.execute(text(f'''
            INSERT INTO {ts_data_table} (time, credits_used, credits_used_today, cut_internships, cut_fulltime)
            VALUES (:time, :credits_used, :credits_used_today, :cut_internships, :cut_fulltime)
        '''), {
            'time': datetime.now(timezone.utc),
            'credits_used': current_credits_used,
            'credits_used_today': credits_used_today,
            'cut_internships': cut_internships,
            'cut_fulltime': cut_fulltime
        })

        this_session.commit()
        this_session.remove()
        return True
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return False


def get_credits_used_today():
    """
    Retrieves the credits_used_today value from the most recent ts_data entry
    where the time is today (UTC date match).

    :return: Integer value of credits_used_today or None if not found
    """
    this_session = Session
    try:
        today_utc = datetime.now(timezone.utc).date()

        result = this_session.execute(text(f'''
            SELECT credits_used_today
            FROM {ts_data_table}
            WHERE DATE(time) = :today
            ORDER BY time DESC
            LIMIT 1
        '''), {'today': today_utc}).fetchone()

        this_session.commit()
        this_session.remove()

        return result[0] if result else None
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None

def get_daily_credits_by_type():
    """
    Sum credits consumed in ts_calls for the last 23 hours and 30 minutes,
    separated by type ('internships' vs 'fulltime').

    :return: dict like {'cut_internships': <int>, 'cut_fulltime': <int>} or None on error
    """
    this_session = Session
    try:
        since_ts = datetime.now(timezone.utc) - timedelta(hours=23, minutes=30)

        rows = this_session.execute(text(f'''
            SELECT type,
                   COALESCE(SUM(credits_consumed), 0) AS total
            FROM {ts_calls_table}
            WHERE time >= :since_ts
              AND type IN ('internships', 'fulltime')
            GROUP BY type
        '''), {'since_ts': since_ts}).fetchall()

        this_session.commit()
        this_session.remove()

        # Defaults to 0 if a type has no rows in the window
        totals = {'cut_internships': 0, 'cut_fulltime': 0}
        for t, total in rows:
            if t == 'internships':
                totals['cut_internships'] = int(total or 0)
            elif t == 'fulltime':
                totals['cut_fulltime'] = int(total or 0)

        return totals
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


def clean_ts_tables():
    """
    Deletes old time-series data:
      - Removes rows from ts_calls older than 2 months
      - Removes rows from ts_data older than 1 year

    :return: dict with counts of deleted rows, or None if an error occurs
    """
    this_session = Session
    try:
        now = datetime.now(timezone.utc)
        cutoff_calls = now - timedelta(days=60)  # ~2 months
        cutoff_data = now - timedelta(days=365)  # 1 year

        # Delete old rows from ts_calls
        deleted_calls = this_session.execute(text(f'''
            DELETE FROM {ts_calls_table}
            WHERE time < :cutoff_calls
        '''), {'cutoff_calls': cutoff_calls}).rowcount

        # Delete old rows from ts_data
        deleted_data = this_session.execute(text(f'''
            DELETE FROM {ts_data_table}
            WHERE time < :cutoff_data
        '''), {'cutoff_data': cutoff_data}).rowcount

        this_session.commit()
        this_session.remove()

        return {
            'deleted_ts_calls': deleted_calls or 0,
            'deleted_ts_data': deleted_data or 0
        }

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


def add_jobs_data_hist(current_internships: int):
    """
    Adds a new row to the jobs_data_hist table with the current UTC time, the given current_jobs count,
    and the difference from the previous row's current_jobs value.

    :param current_internships: Integer representing the current number of jobs
    :return: Boolean indicating success or failure
    """
    this_session = Session
    try:
        # Ensure the table exists
        this_session.execute(text(f'''
            CREATE TABLE IF NOT EXISTS {jobs_data_hist_table} (
                time TIMESTAMP,
                current_internships INT,
                internships_diff_yesterday INT
            )
        '''))

        # Self clean old data over 1 year
        this_session.execute(
            text(f"DELETE FROM {jobs_data_hist_table} WHERE time < NOW() - INTERVAL '1 year'")
        )

        # Get the most recent current_jobs value
        previous_row = this_session.execute(text(f'''
            SELECT current_internships
            FROM {jobs_data_hist_table}
            ORDER BY time DESC
            LIMIT 1
        ''')).fetchone()

        # Compute difference
        if previous_row and previous_row[0] is not None:
            difference = current_internships - previous_row[0]
        else:
            difference = None

        # Insert new row
        this_session.execute(text(f'''
            INSERT INTO {jobs_data_hist_table} (time, current_internships, internships_diff_yesterday)
            VALUES (:time, :current_internships, :internships_difference)
        '''), {
            'time': datetime.now(timezone.utc),
            'current_internships': current_internships,
            'internships_difference': difference
        })

        this_session.commit()
        this_session.remove()
        return True
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return False


def get_jobs_difference_today():
    """
    Retrieves the most recent difference_from_yesterday value from jobs_data_hist
    where the time is today (UTC date match).

    :return: Integer value of difference_from_yesterday or None if not found
    """
    this_session = Session
    try:
        today_utc = datetime.now(timezone.utc).date()

        result = this_session.execute(text(f'''
            SELECT internships_diff_yesterday
            FROM {jobs_data_hist_table}
            WHERE DATE(time) = :today
            ORDER BY time DESC
            LIMIT 1
        '''), {'today': today_utc}).fetchone()

        this_session.commit()
        this_session.remove()

        return result[0] if result else None
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


def add_traffic_history(users_today: int, sessions_today: int, searches_today: int, admins_today: int, paying_premium_users: int,
                        basic_users: int, sponsored_premium_users: int, active_users_today, homepage_searches,
                    add_title_searches, refresh_searches, total_favorites, total_applications, total_li_messages,
                    total_accepted, parse_exp_searchtime, homepage_searchtime, add_refresh_searchtime):
    """
    Adds a new row to the traffic_history table with the current UTC time and today's traffic metrics.

    :param users_today: Number of unique users today
    :param sessions_today: Number of sessions today
    :param searches_today: Number of searches today
    :param admins_today: Number of admins today
    :param paying_premium_users: number of current paying premium users
    :param basic_users: Number of users on the basic plan
    :param sponsored_premium_users: Number of users on premium plan from sponsorship (school or us)
    :param active_users_today: active logged in users today
    :param homepage_searches: searches from the homepage today
    :param add_title_searches: searches from add_title today
    :param refresh_searches: refresh searches today
    :param total_favorites: total number of marked favorites
    :param total_applications: total number of jobs marked as applied to
    :param total_li_messages: total messages generated
    :param total_accepted: total jobs marked as accepted
    :param parse_exp_searchtime: average runtime of the experience parsing today
    :param homepage_searchtime: average runtime of homepage searching today, broken into parts
    :param add_refresh_searchtime: average runtime of refresh/add_title searching today, broken into parts
    :return: Boolean indicating success or failure
    """
    this_session = Session
    try:
        # Ensure the traffic_history table exists
        this_session.execute(text(f'''
            CREATE TABLE IF NOT EXISTS {traffic_history_table} (
                time TIMESTAMP,
                users_today INT,
                sessions_today INT,
                searches_today INT,
                admins_today INT,
                paying_premium_users INT,
                basic_users INT,
                sponsored_premium_users INT,
                active_users_today INT,
                homepage_searches INT,
                add_title_searches INT,
                refresh_searches INT,
                total_favorites INT,
                total_applications INT,
                total_li_messages INT,
                total_accepted INT,
                parse_exp_searchtime DOUBLE PRECISION,
                homepage_searchtime JSONB,
                add_refresh_searchtime JSONB,
                linkedin_clicks INT
            )
        '''))

        # Insert a new row with the current metrics
        this_session.execute(text(f'''
            INSERT INTO {traffic_history_table} (time, users_today, sessions_today, searches_today, admins_today, paying_premium_users, basic_users, 
                sponsored_premium_users, active_users_today, homepage_searches, add_title_searches, refresh_searches, total_favorites,
                total_applications, total_li_messages, total_accepted, parse_exp_searchtime, homepage_searchtime, add_refresh_searchtime, linkedin_clicks)
            VALUES (:time, :users, :sessions, :searches, :admins_today, :paying_premium_users, :basic_users, :sponsored_premium_users,
                :active_users_today, :homepage_searches, :add_title_searches, :refresh_searches, :total_favorites,
                :total_applications, :total_li_messages, :total_accepted, :parse_exp_searchtime, :homepage_searchtime, :add_refresh_searchtime, :linkedin_clicks)
        '''), {
            'time': datetime.now(timezone.utc),
            'users': users_today,
            'sessions': sessions_today,
            'searches': searches_today,
            'admins_today': admins_today,
            'paying_premium_users': paying_premium_users,
            'basic_users': basic_users,
            'sponsored_premium_users': sponsored_premium_users,
            'active_users_today': active_users_today,
            'homepage_searches': homepage_searches,
            'add_title_searches': add_title_searches,
            'refresh_searches': refresh_searches,
            'total_favorites': total_favorites,
            'total_applications': total_applications,
            'total_li_messages': total_li_messages,
            'total_accepted': total_accepted,
            'parse_exp_searchtime': parse_exp_searchtime,
            'homepage_searchtime': json.dumps(homepage_searchtime or {}),
            'add_refresh_searchtime': json.dumps(add_refresh_searchtime or {}),
            'linkedin_clicks': 0
        })

        this_session.commit()
        this_session.remove()
        return True
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return False

def increment_linkedin_clicks():
    """
    Increments the linkedin_clicks column by 1 for the most recent
    row in the traffic_history table (ordered by time DESC).

    :return: Boolean indicating success or failure
    """
    this_session = Session
    try:
        # Increment linkedin_clicks for the most recent row
        this_session.execute(text(f'''
            UPDATE {traffic_history_table} th
            SET linkedin_clicks = COALESCE(th.linkedin_clicks, 0) + 1
            FROM (
                SELECT time
                FROM {traffic_history_table}
                ORDER BY time DESC
                LIMIT 1
            ) latest
            WHERE th.time = latest.time
        '''))

        this_session.commit()
        this_session.remove()
        return True
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return False



def count_users():
    """
    Returns the total number of rows in the users_list table.

    :return: Integer count or None if an error occurs
    """
    this_session = Session
    try:
        result = this_session.execute(text(f"SELECT COUNT(*) FROM {users_list_table} WHERE email NOT LIKE '%sample.student%'")).scalar()
        this_session.remove()
        return result
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


def get_current_active_users_counts():
    """
    Returns the count of distinct user_email values from sessions_data where:
      - session_id is in today_sessions

    :return: Integer count of distinct matching user_email values, or None if error
    """
    this_session = Session
    try:
        result = this_session.execute(text(f'''
            SELECT user_email, session_id
            FROM {sessions_data_name}
        ''')).fetchall()


        this_session.remove()

        thirty_min_list = get_30min_sessions_list()

        # Keep only emails where the session_id is in today_sessions
        logged_in_sessions = [row[0] for row in result if row[1] in thirty_min_list and row[0] is not None]

        unlogged_in_sessions = [row for row in result if row[1] in thirty_min_list and row[0] is None]

        # Keep only distinct emails
        distinct_logged_in = set(logged_in_sessions)

        # Return the count of unique emails
        return {'logged_in': len(distinct_logged_in), 'unlogged_in': len(unlogged_in_sessions)}

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None


def get_30min_sessions_list():
    """
    Retrieves session_id and expiry from the sessions table
    where expiry is at least 4 days, 23 hours, and 30 minutes in the future from the current time.

    :return: List of session_id strings or None if an error occurs
    """
    this_session = Session
    try:
        query = text(f"""
            SELECT session_id
            FROM {sessions_table}
            WHERE expiry >= (NOW() + INTERVAL '4 days 23 hours 30 minutes')
        """)
        result = this_session.execute(query).fetchall()
        this_session.remove()

        session_id_list = [
            session_id.split("session:")[1] if "session:" in session_id else session_id
            for (session_id,) in result
        ]

        return session_id_list
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return None

def get_daily_sessions_list():
    """
    Retrieves session_id and expiry from the sessions table
    where expiry is at least 4 days in the future from the current time.

    :return: List of tuples session ids or None if an error occurs
    """
    this_session = Session
    session_id_list = []
    try:
        query = text(f"""
            SELECT session_id
            FROM {sessions_table}
            WHERE expiry >= (NOW() + INTERVAL '4 days')
        """)
        result = this_session.execute(query).fetchall()
        this_session.remove()

        session_id_list = [
            session_id.split("session:")[1] if "session:" in session_id else session_id
            for (session_id,) in result
        ]

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
    finally:
        this_session.remove()
        return session_id_list


def get_daily_active_sessions():
    """
    Returns the count of distinct user_email values from sessions_data where:
      - user_email is not null
      - session_id is in today_sessions

    :return: Integer count of distinct matching user_email values, or None if error
    """
    this_session = Session
    final_length = 0
    try:
        result = this_session.execute(text(f'''
            SELECT user_email, session_id
            FROM {sessions_data_name}
            WHERE user_email IS NOT NULL
        ''')).fetchall()
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



if __name__ == "__main__":
    # send_daily_monitoring_email("technology@rezify.ai")
    print(get_recent_search_data(24))
    increment_linkedin_clicks()
