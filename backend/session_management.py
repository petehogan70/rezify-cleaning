import json
from datetime import datetime
from datetime import timezone
from types import NoneType
from flask_session import Session
from sentry_sdk import capture_exception, capture_message
from sqlalchemy import text
from backend.database_config import Session, sessions_name, sessions_data_name
from backend.login import get_user_from_email, premium_emails, premium_schools
from backend.admin_login import AdminUser, get_admin_from_email
from flask import session
import os

base_dir = os.path.dirname(os.path.abspath(__file__))

try:
    with open(os.path.join(base_dir, 'school_themes.json'), 'r', encoding='utf-8') as f:
        school_themes = json.load(f)
except Exception as e1:
    capture_exception(e1)

try:
    with open(os.path.join(base_dir, 'wuad.json'), 'r', encoding='utf-8') as f:
        wuad_schools = json.load(f)
        wuad_school_names = [school["name"] for school in wuad_schools]
except Exception as e2:
    capture_exception(e2)

try:
    valid_subdomains = list(school_themes.keys())  # List of valid schools - for subdomaining and theme setting
except Exception as e3:
    capture_exception(e3)


def get_colors(session_id):
    try:
        admin = get_param_from_db('admin', session_id)
        if admin:
            success, user = get_admin_from_email(get_param_from_db('user_email', session_id))
            if success:
                return school_themes[user.school_abbreviation]
        else:
            success, user = get_user_from_email(get_param_from_db('user_email', session_id))

        if success:
            if user.plan == "premium":
                return school_themes[session.get('school', 'rezify')]
            else:
                return school_themes['rezify']
        else:
            return school_themes[session.get('school', 'rezify')]
    except Exception as e:
        capture_exception(e)
        return school_themes['rezify']

def is_locked_out(session_id):
    try:
        lockout_time = get_param_from_db('lockout', session_id)  # Get the lockout time from the database

        if lockout_time is None or datetime.now() > lockout_time:  # If there is no lockout time or the lockout time has passed
            save_param_to_db('lockout', None, session_id)  # Clear the lockout time
            return False
        else:
            # If the lockout time is still valid, return True
            email = get_param_from_db('user_email', session_id)
            capture_message(f"INFO: Locked out session. Email: {email}", level="info")
            return True
    except Exception as e:
        capture_exception(e)
        return False


def clear_session(session_obj):
    """
    Clears all keys in the session except for 'session_id' and 'school'.

    Args:
        session_obj (flask.session): The Flask session object.
    """
    try:
        keys_to_keep = {'session_id', 'school', 'searches'}
        keys_to_delete = [key for key in session_obj.keys() if key not in keys_to_keep]

        for key in keys_to_delete:
            session_obj.pop(key, None)
    except Exception as e:
        capture_exception(e)

def get_current_session_id_from_db(session_obj):
    """
    Retrieves the session_id from the SQLAlchemy-backed 'sessions' table
    for the given session object (if it exists).

    :param session_obj: The session object (typically flask.session)
    :return: session_id string or None
    """
    # Use actual session ID — Flask-Session stores it in session.sid, fallback to session['session_id']
    try:
        actual_session_id = getattr(session_obj, 'sid', None)

        return actual_session_id
    except Exception as e:
        capture_exception(e)
        return None


def get_school_from_user(user):
    ''' Determines the school based on the user. '''

    try:
        if isinstance(user, str) or isinstance(user, NoneType):
            return 'rezify'  # If user is a string or none, return default school

        if isinstance(user, AdminUser):
            # If the user is an admin, return their school abbreviation
            return user.school_abbreviation

        # Check direct email ending match with school_themes
        for school_name, settings in school_themes.items():
            if user.email.endswith(settings.get('email_ending', 'notapplicablerezify314.com')):
                if school_name in premium_schools or 'sample.student' in user.email:
                    return school_name

        # If reported_college is in wuad_school_names, perform domain checks
        if user.reported_college in wuad_school_names:
            # Find the school entry in wuad_schools
            school_entry = next((s for s in wuad_schools if s["name"] == user.reported_college), None)
            if school_entry and "domains" in school_entry:
                # For each domain listed for that school
                for domain in school_entry["domains"]:
                    domain = domain[:domain.rfind('.')]  # Remove .edu part
                    # Check if any school_theme matches this domain
                    if domain in valid_subdomains:
                        if check_if_school_accepts_email(user.email, domain):
                            if domain in premium_schools or 'sample.student' in user.email:
                                return domain

        return 'rezify'  # Fallback to default school if no matches found
    except Exception as e:
        capture_exception(e)
        return 'rezify'


def check_if_school_accepts_email(email, school):
    """
    Checks if the given email is accepted by the specified school.
    Returns True if the email is accepted, False otherwise.
    """

    try:
        if school not in school_themes:
            return False  # School not found

        # Collect all possible email endings
        email_endings = []
        primary_ending = school_themes[school].get("email_ending")
        alt_endings = school_themes[school].get("alternate_email_endings")

        if primary_ending:
            email_endings.append(primary_ending)
        if alt_endings:
            for alt_ending in alt_endings:
                email_endings.append(alt_ending)

        return any(email.endswith(ending) for ending in email_endings)

    except Exception as e:
        capture_exception(e)
        return False

def check_if_admin_valid(email, school) -> bool:
    """
    Check if an email is a valid admin for a given school.
    """
    try:
        # Check against school's admin_emails list (if present)
        school_data = school_themes.get(school, {})
        school_admins = school_data.get("admin_emails", [])
        if email in school_admins:
            return True

        return False
    except Exception as e:
        capture_exception(e)
        return False

def get_fullname_from_abbreviation(abbreviation):
    """
    Given a school abbreviation (like 'mst'), return its full_name from school_themes.
    Returns None if abbreviation is not found or full_name is missing.
    """
    school_data = school_themes.get(abbreviation)
    if school_data:
        return school_data.get("full_name")

    capture_exception(Exception(f"ERROR: Fullname could not be found from abbreviation: {abbreviation}"))
    return None


def get_abbreviation_from_fullname(full_name):
    """
    Given a school's full name, return its abbreviation key from school_themes.
    Returns None if no match is found.
    """
    for abbr, data in school_themes.items():
        if data.get("full_name") == full_name:
            return abbr

    capture_exception(Exception(f"ERROR: Abbreviation could not be found from full name: {full_name}"))
    return None



def need_domain_change(host, user, user_type='user'):
    try:
        subdomain = host.split('.')[0]  # Get the subdomain from the host
        if subdomain == session.get('school', 'rezify'):
            return False
        else:
            if subdomain in valid_subdomains:  # if the subdomain is in the list of valid subdomains
                if user:  # If the user is logged in
                    if user_type == 'admin':
                        if check_if_admin_valid(user.email, subdomain):
                            # If the user is an admin and their email is valid for the school in the subdomain, set the session school
                            session['school'] = subdomain
                            save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])
                            return False
                        else:
                            # Try to find another premium school the admin is valid for
                            for school in premium_schools:
                                if check_if_admin_valid(user.email, school):
                                    session['school'] = school
                                    save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])
                                    return True

                            # If the user is an admin but their email is not valid for the school in the subdomain, or ANY premium school, set to rezify
                            session['school'] = 'rezify'
                            save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])
                            return True
                    if check_if_school_accepts_email(user.email, subdomain):
                        # If the user's email is accepted by the school in the subdomain, set the session school
                        session['school'] = subdomain
                        save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])
                        return False
                    else:
                        # If the user's email is not accepted by the school in the subdomain, check email against other schools
                        if user.email in premium_emails:
                            # If the email is in the premium emails list, set the session school to the school
                            return False
                        other_school = get_school_from_user(user)
                        if other_school != 'rezify' and other_school in premium_schools:
                            # If the email of the user matches another approved school, set the session school to that school
                            session['school'] = other_school
                            save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])
                            return True
                        else:
                            # If the email does not match any approved school, set the session school to rezify
                            session['school'] = 'rezify'
                            save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])
                            return True
                else:  # Not logged in
                    session['school'] = subdomain
                    save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])
                    return False
            else:  # Subdomain is not valid
                session['school'] = 'rezify'  # Default to rezify
                save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])
                return True

    except Exception as e:
        capture_exception(e)
        return False


def clean_old_session_data():
    """
    Deletes rows from sessions_data_name where the session_id is not present
    in the sessions table (after stripping 'session:' from sessions.session_id).
    """
    this_session = Session

    try:
        query = f'''
            DELETE FROM {sessions_data_name}
            WHERE session_id NOT IN (
                SELECT substring(session_id from 9)
                FROM {sessions_name}
            )
        '''
        this_session.execute(text(query))
        this_session.commit()
        this_session.remove()
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()



def add_session(session_id):
    """
    Function to add a new session to the sessions table. It creates the sessions_data table if it doesn't exist.
    Then it checks if the session_id already exists in the table. If it does, it returns 'Already in table'. If it
    doesn't, it inserts a new row with the session_id and other default values.
    This is called when a user first gets on the website, and a unique session is created for them.

    :param session_id: string representing the random session ID
    :return: None or False
    """
    # clean_old_sessions()  # calls function to delete very old sessions
    this_session = Session
    try:
        # Create the sessions_data table if it doesn't exist
        this_session.execute(text(f'''CREATE TABLE IF NOT EXISTS {sessions_data_name}
                         (id SERIAL PRIMARY KEY,
                          session_id VARCHAR,
                          user_email TEXT,
                          jobs_list JSON,
                          time_added TIMESTAMP,
                          resume_info JSON,
                          filters JSON,
                          code TEXT,
                          code_expiry TIMESTAMP,
                          lockout TIMESTAMP,
                          school TEXT,
                          admin BOOLEAN
                          )'''))

        this_session.commit()

        # Query all session IDs from the sessions_data table
        ids = this_session.execute(text(f'''
                        SELECT session_id
                        FROM {sessions_data_name}
                        ''')).fetchall()
        this_session.commit()
        this_session.remove()
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return False

    ids = [row[0] for row in ids]  # Get a list of session_ids from the result

    if session_id in ids:
        # If the session_id already exists in the table, don't add it, and return 'Already in table'
        return 'Already in table'

    this_session = Session
    try:
        # This means that the session_id does not exist in the table, so we can add it
        # Insert a new row into the sessions_data table with the session_id and other default values
        this_session.execute(text(f'''
                            INSERT INTO {sessions_data_name} (session_id, user_email, jobs_list, time_added, resume_info, filters, code, code_expiry, lockout, school, admin)
                            VALUES (:session_id, :user_email, :jobs_list, :time_added, :resume_info, :filters, :code, :code_expiry, :lockout, :school, :admin)
                            RETURNING id
                        '''), {
            'session_id': session_id,
            'user_email': None,
            'jobs_list': json.dumps([]),
            'time_added': datetime.now(timezone.utc),
            # Blank resume info
            'resume_info': json.dumps({
                'resume_file': None, 'intern_titles': [], 'first_name': None, 'last_name': None, 'email': None,
                'skills': [], 'reported_college': None
            }),
            # Default filters
            'filters': json.dumps(
                {'location': None, 'radius': 50, 'type': 'All', 'international_only': False, 'selected_industries': [],
                 'selected_titles': [], 'selected_filter': 'All', 'sort_by': 'Relevance'}),
            'code': None,
            'code_expiry': None,
            'lockout': None,
            'school': None,
            'admin': False
        })
        this_session.commit()
        this_session.remove()
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return False


def get_session_data(session_id):
    """
    This function retrieves all session data from the sessions_data table based on the session_id.
    This is mainly used for testing and is not used in production.

    :param session_id: unique session ID
    :return: Dictionary of the session data or None if not found
    """
    this_session = Session
    try:
        # Select all columns from the session
        results = this_session.execute(text(f'''
                        SELECT *
                        FROM {sessions_data_name}
                        WHERE session_id = :session_id
                    '''), {
            'session_id': session_id}).fetchall()
        this_session.commit()
        this_session.remove()
        sesh = results[0]

        # Convert the session data to a dictionary and return it
        session_dict = {
            'id': sesh[0], 'session_id': sesh[1], 'user_email': sesh[2], 'jobs_list': sesh[3], 'time_added': sesh[4],
            'resume_info': sesh[5], 'filters': sesh[6], 'code': sesh[7], 'code_expiry': sesh[8], 'lockout': sesh[9],
            'school': sesh[10], 'admin': sesh[11]
        }
        return session_dict
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.commit()
        this_session.remove()
        return None


def save_param_to_db(parameter, new_value, session_id):
    """
    This function updates a specific parameter in the sessions_data table based on the session_id. When a specific parameter
    needs to be updated for a session, this function is called.

    :param parameter: a string of the parameter to be updated (e.g., 'user_email', 'jobs_list', etc.)
    :param new_value: the new value to be set for the parameter
    :param session_id: unique session ID so it knows which session to update

    :return: boolean indicating success or failure
    """
    # Ensure the parameter is a valid column name
    valid_parameters = {'session_id', 'user_email', 'jobs_list', 'time_added', 'resume_info', 'filters', 'code', 'code_expiry', 'lockout', 'school', 'admin'}

    if parameter not in valid_parameters:
        capture_exception(ValueError(f"Invalid parameter: {parameter}"))
        return None

    this_session = Session
    try:
        # Update the specified parameter in the sessions_data table
        this_session.execute(text(f'''
                    UPDATE {sessions_data_name}
                    SET {parameter} = :new_value
                    WHERE session_id = :session_id
                '''), {'new_value': new_value, 'session_id': session_id})

        this_session.commit()
        return True
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return False
    finally:
        this_session.remove()


def get_param_from_db(parameter, session_id) -> text:
    """
    This function retrieves a specific parameter from the sessions_data table based on the session_id. Any time data
    is being retrieved from the database, this function is called.

    :param parameter: a string of the parameter to be retrieved (e.g., 'user_email', 'jobs_list', etc.)
    :param session_id: unique session ID so it knows which session to get the parameter from

    :return: the value of the parameter or None if not found
    """

    # Part 1: Ensure the parameter is a valid column name
    valid_parameters = {
        'session_id', 'user_email', 'jobs_list', 'time_added',
        'resume_info', 'filters', 'code', 'code_expiry',
        'lockout', 'school', 'admin'
    }

    if parameter not in valid_parameters:
        capture_exception(ValueError(f"Invalid parameter: {parameter}"))
        return None

    # Part 2: Query the database for the parameter value

    this_session = Session

    try:
        # Select the specified parameter from the sessions_data table
        result = this_session.execute(text(f'''
                    SELECT {parameter}
                    FROM {sessions_data_name}
                    WHERE session_id = :session_id
                '''), {'session_id': session_id}).fetchone()


        if result:
            # return the value of the parameter
            return result[0]
        else:
            return None

    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return None
    finally:
        this_session.remove()


def delete_session_data(session_id):
    """
    This function deletes a session from the sessions_data table based on the session_id.

    :param session_id: unique session ID so it knows which session to delete

    :return: boolean indicating success or failure
    """
    this_session = Session

    try:
        # Delete the session matching the given session_id
        this_session.execute(text(f'''
                        DELETE FROM {sessions_data_name}
                        WHERE session_id = :session_id
                    '''), {'session_id': session_id})

        this_session.commit()
        return True
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        return False
    finally:
        this_session.remove()

def delete_session(session_id):
    """
    This function deletes a session from the sessions_data table based on the session_id.

    :param session_id: unique session ID so it knows which session to delete

    :return: boolean indicating success or failure
    """
    this_session = Session

    session_id = f'session:{session_id}'  # Add the 'session:' prefix to the session_id

    try:
        # Delete the session matching the given session_id
        this_session.execute(text(f'''
                        DELETE FROM {sessions_name}
                        WHERE session_id = :session_id
                    '''), {'session_id': session_id})

        this_session.commit()
        this_session.remove()
        return True
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.commit()
        this_session.remove()
        return False