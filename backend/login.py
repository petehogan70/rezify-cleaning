import json
import logging
from sqlalchemy import Integer, text
from datetime import datetime
from backend.database_config import Session
import bcrypt
import re
from sentry_sdk import capture_exception
from backend.tables import users_list_table

"""
login.py contains the User class and functions related to user management, and changes to the users_list table.

Any new updates or functions to editing the users_list table should be added here.
"""

# List of premium colleges (domains) that have therr own portal
premium_schools = ['mst', 'umsl']

# List of premium email endings that will automatically give premium to the user - change this to read from school_themes.json
premium_email_endings = ['mst.edu', 'umsystem.edu', 'rezify.ai', 'umsl.edu']

# List of non edu emails that can sign up - but will not automatically give premium
edu_bypass_emails = ['rileycnoggle@gmail.com', 'petehogan70@gmail.com']

# List of email addresses that will automatically give premium to the user (sample accounts, dev/test accounts, etc.)
# This list will also skip email verification
premium_emails = ['sample.student@mst.edu', 'sample.student@purdue.edu', 'sample.student@gatech.edu',
                       'sample.student@stchas.edu', 'sample.student@college.edu', 'peter@rezifyadmin.com',
                       'sample.student@stlcc.edu', 'sample.student@lindenwood.edu', 'sample.student@umsl.edu',
                       'ishan@rezifyadmin.com', 'sample.student@missouri.edu', 'sample.student@upenn.edu',
                       'sample.student@ranken.edu', 'sample.student@maryville.edu', 'sample.student@obu.edu',
                       'sample.student@umsystem.edu', 'sample.student@columbiasc.edu', 'sample.student@slu.edu', 'jbasler722@gmail.com', 'rob.flynn@gmail.com',
                  'brock.killen@arcadianinfra.com', 'bwkillen@yahoo.com', 'sample.student@illinois.edu', 'staceyscheinkman1@gmail.com', 'isaac.porter144@gmail.com', 'lpovenz3@gatech.edu',
                  'mtabachow3@gatech.edu', 'elibkilgore@gmail.com', 'Truncale.mason@gmail.com', 'Solomonnackashica@gmail.com', 'Jkelley80@gatech.edu',
                  'wilwilson928@gmail.com', 'samireneebbert@gmail.com', 'Jeb.d.mcdonald05@gmail.com', 'hspecht@purdue.edu', 'noggler@purdue.edu',
                  'jbritt40@gatech.edu', 'sample.student@salem.edu', 'sample.student@harpercollege.edu', 'sample.student@depauw.edu',
                  'sample.student@gcu.edu']

# List of passwords when creating a new user that will automatically be approved as premium
# This will also skip email verification
approved_passwords = []


class User:
    """
    The User class represents a user in the system. It contains methods for creating a new user, logging in, and updating
    user information.
    """

    def __init__(self, resume_file, email, password, first_name, last_name, intern_titles, skills,
                 time_created, filters, auth_type, plan, last_refresh, stripe_id, stripe_meta, reported_college, subscription_status, resume_json):
        try:
            self.id = Integer  # id represents the user's unique identifier
            self.resume_file = resume_file  # name of the file of the resume the user is using
            self.email = email
            self.password = password
            self.last_logged_in = datetime.now()  # Datetime of the last time the user logged in - set to current time at first
            self.first_name = first_name
            self.last_name = last_name
            self.intern_titles = intern_titles  # A list of internship titles that the user is searching for
            self.skills = skills  # A list of skills parsed from the user's resume
            self.time_created = time_created  # Timestamp of when the user was created
            self.filters = filters  # A dictionary of filters that the user has set for their job search on the results page
            self.auth_type = auth_type
            self.plan = plan
            self.last_refresh = last_refresh
            self.stripe_id = stripe_id
            self.stripe_meta = stripe_meta
            self.reported_college = reported_college
            self.subscription_status = subscription_status
            self.resume_json = resume_json # A dictionary to hold resume information, if needed
        except Exception as e:
            capture_exception(e)

    def to_dict(self, include_school=False):
        """
        Converts the User object into a serializable dictionary object for json purposes
        :param include_school: If True, includes the user's school information
        :return: dictionary of User object data
        """
        try:
            user_dict = {
                'id': self.id,
                'resume_file': self.resume_file,
                'email': self.email,
                'favorites': self.get_user_list('favorites'),
                'applied_to': self.get_user_list('applied_to'),
                'last_logged_in': self.last_logged_in.isoformat() if self.last_logged_in is not None else "",
                'first_name': self.first_name,
                'last_name': self.last_name,
                'intern_titles': self.intern_titles,
                'skills': self.skills,
                'time_created': self.time_created.isoformat() if self.time_created is not None else "",
                'filters': self.filters,
                'plan': self.plan,
                'last_refresh': self.last_refresh.isoformat() if self.last_refresh is not None else "",
                'reported_college': self.reported_college,
                'removed_jobs': self.get_user_list('removed_jobs'),
                "subscription_status": self.subscription_status,
                "stripe_meta": self.stripe_meta,
                "jobs_accepted": self.get_user_list('jobs_accepted'),
                "messages_generated": self.get_user_list('messages_generated'),
                "resume_json": self.resume_json
            }

            if include_school and self.email:
                # Import here to avoid circular imports
                from backend.session_management import get_school_from_user
                user_dict['school'] = get_school_from_user(self)

            return user_dict
        except Exception as e:
            capture_exception(e)
            return {}

    def create_new_user(self, internships_list):
        """
        Creates a new user in the database. It creates the users_list table if it doesn't exist yet. It checks if the
        user already exists by checking the email. If the user doesn't exist, it adds the user to the database.
        :return: boolean of success, message
        """
        session = Session
        try:
            # Create the users_list table if it doesn't exist
            session.execute(text(f'''
                CREATE TABLE IF NOT EXISTS {users_list_table}
                (id SERIAL PRIMARY KEY,
                 resume_file TEXT,
                 email TEXT,
                 password TEXT,
                 internships_list JSON,
                 favorites JSON,
                 applied_to JSON,
                 last_logged_in TIMESTAMP,
                 device_id TEXT,
                 first_name TEXT,
                 last_name TEXT,
                 intern_titles TEXT[],
                 skills TEXT[],
                 time_created TIMESTAMP,
                 filters JSON,
                 auth_type TEXT,
                 plan TEXT,
                 last_refresh TIMESTAMP,
                 stripe_id TEXT,
                 stripe_meta JSON,
                 reported_college TEXT,
                 removed_jobs JSON,
                 subscription_status TEXT,
                 jobs_accepted JSON,
                 messages_generated JSONB,
                 resume_json JSONB
                                 )
            '''))
            session.commit()

            if not check_if_user_exists(self.email):  # Making sure the user doesn't exist already
                # Insert the new user into the users_list table
                result = session.execute(text(f'''
                    INSERT INTO {users_list_table} (resume_file, email, password, internships_list, favorites, applied_to, last_logged_in, device_id, first_name, last_name, intern_titles, skills, time_created, filters, auth_type, plan, last_refresh, stripe_id, stripe_meta, reported_college, removed_jobs, subscription_status, jobs_accepted, messages_generated, resume_json)
                    VALUES (:resume_file, :email, :password, :internships_list, :favorites, :applied_to, :last_logged_in, :device_id, :first_name, :last_name, :intern_titles, :skills, :time_created, :filters, :auth_type, :plan, :last_refresh, :stripe_id, :stripe_meta, :reported_college, :removed_jobs, :subscription_status, :jobs_accepted, :messages_generated, :resume_json)
                    RETURNING id
                '''), {
                    'resume_file': self.resume_file,
                    'email': self.email,
                    'password': hash_password(self.password),
                    'internships_list': json.dumps(internships_list),
                    'favorites': json.dumps([]),
                    'applied_to': json.dumps([]),
                    'last_logged_in': self.last_logged_in,
                    'device_id': '',
                    'first_name': self.first_name,
                    'last_name': self.last_name,
                    'intern_titles': self.intern_titles,
                    'skills': self.skills,
                    'time_created': self.time_created,
                    'filters': json.dumps(self.filters),
                    'auth_type': self.auth_type,
                    'plan': self.plan,
                    'last_refresh': self.last_refresh,
                    'stripe_id': self.stripe_id,
                    'stripe_meta': json.dumps(self.stripe_meta),
                    'reported_college': self.reported_college,
                    'removed_jobs': json.dumps([]),
                    'subscription_status': self.subscription_status,
                    'jobs_accepted': json.dumps([]),
                    'messages_generated': json.dumps([]),
                    'resume_json': json.dumps(self.resume_json)
                })
                self.id = result.fetchone()[0]
                session.commit()

                return True, f"User with email: {self.email} added successfully"
            else:
                return False, 'Email is already in use'
        except Exception as e:
            capture_exception(e)
            session.rollback()
            return False, 'An error occurred while creating the user, please try again'
        finally:
            session.remove()

    def get_user_list(self, list_name: str):
        """
        Retrieve one of the list-type columns for a user by email.

        Valid list_name values:
          - 'favorites'
          - 'applied_to'
          - 'removed_jobs'
          - 'internships_list'
          - 'jobs_accepted'
          - 'messages_generated'

        Returns a Python list (decoded from JSON if needed), or [] if not found/invalid.
        """
        # Whitelist of valid list columns
        allowed_lists = {
            "favorites",
            "applied_to",
            "removed_jobs",
            "internships_list",
            "jobs_accepted",
            "messages_generated",
        }

        if list_name not in allowed_lists:
            capture_exception(Exception(f"ERROR: user list not allowed: {list_name}"))
            return []

        session = Session
        try:
            row = session.execute(
                text(f"SELECT {list_name} FROM {users_list_table} WHERE email = :email"),
                {"email": self.email},
            ).fetchone()
            session.remove()

            if row is None:
                return []

            value = row[0]

            # If stored as JSON text, decode it
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    # If it isn't valid JSON, just return as-is wrapped in a list
                    return [value]

            # Ensure we always return a list
            if value is None:
                return []
            if isinstance(value, list):
                return value

            # Fallback: wrap non-list in a list
            return [value]

        except Exception as e:
            session.rollback()
            capture_exception(e)
            session.remove()
            return []


    def update_list_with_job(self, which_list, job, add):
        session = Session
        try:
            # Get the target list from the list name entered
            if which_list == 'favorites':
                list_updating = self.get_user_list('favorites')
            elif which_list == 'applied_to':
                list_updating = self.get_user_list('applied_to')
            elif which_list == 'removed_jobs':
                list_updating = self.get_user_list('removed_jobs')
            elif which_list == 'internships_list':
                list_updating = self.get_user_list('internships_list')
            elif which_list == 'jobs_accepted':
                list_updating = self.get_user_list('jobs_accepted')
            elif which_list == 'messages_generated':
                list_updating = self.get_user_list('messages_generated')
            else:
                return False, 'Unknown list'

            # Determine if job is in list
            if which_list != 'removed_jobs':
                job_in_list = check_if_job_in(job, list_updating)
            else:
                job_in_list = False  # Removed jobs are not checked for existence in the list

            if add and not job_in_list:  # Add the job to the list
                list_updating.append(job)
            elif not add and job_in_list:  # Remove the job from the list
                list_updating = [list_job for list_job in list_updating if not (job['id'] == list_job.get('id'))]
            else:
                return False, 'Unknown error'

            # Update the database with the new list in place of the old one
            session.execute(text(f'''
                UPDATE {users_list_table}
                SET {which_list} = :some_value
                WHERE email = :email
            '''), {'some_value': json.dumps(list_updating), 'email': self.email})
            session.commit()
            session.remove()

            action = 'added to' if add else 'removed from'
            return True, f"Successfully {action} the {which_list} list"

        except Exception as e:
            session.rollback()
            capture_exception(e)
            session.remove()
            return False, 'An error occurred, please try again'

    def change_password(self, current_password, new_password, new_password_confirmed):
        """
        This function changes the user's password. It takes the current password, new password, and new password
        confirmed as arguments. It checks if the current password is correct and if the new password and new password
        confirmed are the same. If they are, it updates the password in the database.
        If the current_password entered is !rezify_verification_code!, then it will change the password because this
        that the user recovered their password using a verification code sent by email.
        :param current_password: string representing the current password for the account
        :param new_password: string representing the new password to be set for the account
        :param new_password_confirmed: string representing the new password confirmed (make sure it matches the new password)
        :return: boolean representing success, message
        """

        # Verify that the current password matches the users password
        # Or, if the password is the '!rezify_verification_code!', then allow the change because the user has
        # verified their identity
        try:
            if verify_password(current_password, self.password) or current_password == '!rezify_verification_code!':
                if new_password == new_password_confirmed:  # If the new passwords are the same
                    # Check for at least one uppercase letter
                    if not re.search(r'[A-Z]', new_password):
                        return False, 'Password must include at least one uppercase letter.'

                    # Check for at least one special character
                    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
                        return False, 'Password must include at least one special character.'

                    new_password = hash_password(new_password)  # Hash the new password
                    self.password = new_password  # Update the password in the user object

                    session = Session
                    # Update the password in the database
                    try:
                        session.execute(text(f'''
                            UPDATE {users_list_table}
                            SET password = :new_password
                            WHERE email = :email
                        '''), {'new_password': new_password, 'email': self.email})
                        session.commit()
                        session.remove()
                    except Exception as e:
                        session.rollback()
                        capture_exception(e)
                        session.remove()
                        return False, 'Error occurred'

                    return True, 'Password changed successfully'
                else:
                    return False, 'New passwords do not match'
            else:
                return False, 'Current password is incorrect'

        except Exception as e:
            capture_exception(e)
            return False, 'Error occured'

    def update_user_param(self, parameter, new_value):
        """
        This function updates a parameter in the database. It takes the parameter name and the new value as arguments.
        Then it updates the parameter in the database.
        :param parameter: string representing the parameter to be updated
        :param new_value: a value representing the new value to be set for the parameter
        :return: boolean representing success
        """
        if parameter == 'email':
            self.email = new_value
        elif parameter == 'internships_list':
            new_value = json.dumps(new_value)
        elif parameter == 'applied_to':
            new_value = json.dumps(new_value)
        elif parameter == 'last_logged_in':
            self.last_logged_in = new_value
        elif parameter == 'intern_titles':
            self.intern_titles = new_value
        elif parameter == 'skills':
            self.skills = new_value
        elif parameter == 'filters':
            self.filters = json.dumps(new_value)
            new_value = json.dumps(new_value)
        elif parameter == 'plan':
            self.plan = new_value
        elif parameter == 'stripe_id':
            self.stripe_id = new_value
        elif parameter == 'last_refresh':
            self.last_refresh = new_value
        elif parameter == 'reported_college':
            self.reported_college = new_value
        elif parameter == 'first_name':
            self.first_name = new_value
        elif parameter == 'last_name':
            self.last_name = new_value
        elif parameter == 'email':
            self.email = new_value
        elif parameter == 'subscription_status':
            self.subscription_status = new_value
        elif parameter == 'stripe_meta':
            self.stripe_meta = new_value
        elif parameter == 'resume_json':
            self.resume_json = new_value
        elif parameter == 'resume_file':
            self.resume_file = new_value
        else:
            capture_exception(Exception(f'ERROR: Cannot update user param: {parameter}'))
            return False

        session = Session
        # Update the parameter in the database
        try:
            session.execute(text(f'''
                                UPDATE {users_list_table}
                                SET {parameter} = :new_value
                                WHERE email = :email
                            '''), {'new_value': new_value, 'email': self.email})
            session.commit()
            session.remove()
            return True
        except Exception as e:
            session.rollback()
            capture_exception(e)
            session.remove()
            return False


def check_if_user_exists(email):
    """
    This function checks if a user exists in the database by checking the email. It returns True if the user exists,
    False otherwise.
    :param email:
    :return:
    """
    session = Session
    try:
        # Query to check if the user exists. True if the user exists, False if not
        result = session.execute(text(f'''
            SELECT EXISTS (
                SELECT 1 
                FROM {users_list_table}
                WHERE email = :email
            )
        '''), {'email': email}).scalar()

        return result
    except Exception as e:
        capture_exception(e)
        session.rollback()
        return False
    finally:
        session.remove()


def check_if_job_in(job, list_to_check):
    """
    This function checks if a job is in a list of jobs. It takes the job information and the list to check as parameters.
    Returns True if the job is in the list, False if not.
    :param job: Job to check
    :param list_to_check: list of jobs to check
    :return:
    """

    try:

        selected_job_id = job['id']

        # Check if the job is in the list
        for job in list_to_check:
            job_id_to_check = job['id']
            if selected_job_id == job_id_to_check:
                return True

        return False

    except Exception as e:
        capture_exception(e)
        return False


def user_login(email, password):
    """
    This function logs in a user. It takes the email, password, and device id as parameters. It uses the email and
    password to attempt to log in to an account. If the login is successful, it returns True and the user object.
    :param email: string representing the email of the user
    :param password: string representing the password of the user
    :return: boolean of success, user object
    """
    session = Session
    try:
        # Query to check if the user exists. True if the user exists, False if not
        result = session.execute(text(f'''
            SELECT id, resume_file, email, password, last_logged_in, first_name, last_name, intern_titles, skills, time_created, filters, auth_type, plan, last_refresh, stripe_id, stripe_meta, reported_college, subscription_status, resume_json
            FROM {users_list_table}
            WHERE email = :email
        '''), {'email': email}).fetchone()

        if result:  # If a user exists with that email, create a user object with the data from the database
            user = User(
                resume_file=result[1],
                email=result[2],
                password=result[3],
                first_name=result[5],
                last_name=result[6],
                intern_titles=result[7],
                skills=result[8],
                time_created=result[9],
                filters=result[10],
                auth_type=result[11],
                plan=result[12],
                last_refresh=result[13],
                stripe_id=result[14],
                stripe_meta=result[15],
                reported_college=result[16],
                subscription_status=result[17],
                resume_json=result[18]
            )

            # Check if the password is correct
            password_check = verify_password(password, result[3])

            # If the password is correct, update the user object with the data from the database and return the user
            if password_check:
                user.id = result[0]
                user.last_logged_in = datetime.now()
                user.update_user_param('last_logged_in', datetime.now())
                check_user_plan(user)
                return True, user
            else:
                return False, "Incorrect password"
        else:
            return False, "Invalid credentials"
    except Exception as e:
        print(e)
        capture_exception(e)
        session.rollback()
        return False, "Error"
    finally:
        session.remove()


def get_user_from_email(email):
    """
    This function gets a user object from the database by their email.
    :param email: string representing the email of the user
    :return: boolean of success, user object
    """
    session = Session
    # Query to get the user from the database by their email
    try:
        result = session.execute(text(f'''
                SELECT id, resume_file, email, password, last_logged_in, first_name, last_name, intern_titles, skills, time_created, filters, auth_type, plan, last_refresh, stripe_id, stripe_meta, reported_college, subscription_status, resume_json
                FROM {users_list_table}
                WHERE email = :email
            '''), {'email': email}).fetchone()

        if result:  # If a user exists with that email, create a user object with the data from the database
            user = User(
                resume_file=result[1],
                email=result[2],
                password=result[3],
                first_name=result[5],
                last_name=result[6],
                intern_titles=result[7],
                skills=result[8],
                time_created=result[9],
                filters=result[10],
                auth_type=result[11],
                plan=result[12],
                last_refresh=result[13],
                stripe_id=result[14],
                stripe_meta=result[15],
                reported_college=result[16],
                subscription_status=result[17],
                resume_json=result[18]
            )
            user.id = result[0]
            user.last_logged_in = result[4]

            # return True and the user object
            return True, user
        else:
            return False, "No user found for that email"

    except Exception as e:
        capture_exception(e)
        session.rollback()
        return False, "Error"
    finally:
        session.remove()


def delete_account_email(email):
    """
    This function deletes a user from the database by their email.
    :param email: string representing the email of the user
    :return: boolean of success
    """
    session = Session
    try:
        # Delete the row of the users_list table associated with the email
        session.execute(text(f'''
            DELETE FROM {users_list_table}
            WHERE email = :email
        '''), {'email': email})
        session.commit()
        session.remove()
        return True
    except Exception as e:
        session.rollback()
        capture_exception(e)
        session.remove()
        return False


def delete_all_users():
    """
    This function deletes all users from the database. It is used for testing purposes only - for if you are trying to
    clean the database for some reason.

    :return: boolean of success, message
    """
    session = Session
    try:
        # Delete all rows from the users_list table
        session.execute(text(f'DELETE FROM {users_list_table}'))
        session.commit()
        logging.debug("All users deleted successfully")
        session.remove()
        return True, "All users deleted successfully"
    except Exception as e:
        session.rollback()
        capture_exception(e)
        session.remove()
        return False, "Error"



def check_if_valid_email(email):
    """
    This function checks if an email exists in the users database. It returns True if the email exists, False otherwise.
    :param email: string representing the email to check
    :return: boolean
    """
    session = Session

    try:

        # Select the count of rows where the email matches
        result = session.execute(text(f"SELECT COUNT(*) FROM {users_list_table} WHERE email = :email"), {'email': email}).scalar()
        session.commit()
        session.remove()

        exists = result > 0  # If the count is greater than 0, the email exists

        return exists

    except Exception as e:
        session.remove()
        capture_exception(e)
        return False



def hash_password(password: str) -> str:
    """Hashes a password using bcrypt and returns the hashed version as a string."""
    salt = bcrypt.gensalt()  # Generate a salt
    hashed_password = bcrypt.hashpw(password.encode(), salt)  # Hash password
    return hashed_password.decode()  # Convert bytes to string for storage


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a given password against the stored hashed password."""
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

def check_user_plan(user: User):
    """Check if user is premium via approved emails"""
    try:
        if user.plan is None or len(user.plan) == 0: #A user already registered pre-limitations
            if user.plan != "premium":
                user.update_user_param("plan", "premium")
            return

        if any(user.email.endswith(ending) for ending in premium_email_endings) or user.email in premium_emails:
            if user.plan != "premium":
                user.update_user_param("plan", "premium")
            return
        elif user.subscription_status == "active":
            if user.plan != "premium":
                user.update_user_param("plan", "premium")
            return
        else:
            if user.plan != "basic":
                user.update_user_param("plan", "basic")
            return
    except Exception as e:
        capture_exception(e)
        return

def update_user_plan(user: User, new_plan: str):
    return user.update_user_param("plan", new_plan)

def get_user_from_stripe_id(stripe_id):
    """
    This function gets a user object from the database by their stripe id.
    :param stripe_id: string representing the stripe id of the user
    :return: boolean of success, user object
    """
    session = Session
    # Query to get the user from the database by their email
    try:
        result = session.execute(text(f'''
                SELECT id, resume_file, email, password, last_logged_in, first_name, last_name, intern_titles, skills, time_created, filters, auth_type, plan, last_refresh, stripe_id, stripe_meta, reported_college, subscription_status, resume_json
                FROM {users_list_table}
                WHERE stripe_id = :stripe_id
            '''), {'stripe_id': stripe_id}).fetchone()
        session.remove()
    except Exception as e:
        session.rollback()
        capture_exception(e)
        session.remove()
        result = False

    if result:  # If a user exists with that email, create a user object with the data from the database
        user = User(
            resume_file=result[1],
            email=result[2],
            password=result[3],
            first_name=result[5],
            last_name=result[6],
            intern_titles=result[7],
            skills=result[8],
            time_created=result[9],
            filters=result[10],
            auth_type=result[11],
            plan=result[12],
            last_refresh=result[13],
            stripe_id=result[14],
            stripe_meta=result[15],
            reported_college=result[16],
            subscription_status=result[17],
            resume_json=result[18]
        )
        user.id = result[0]
        user.last_logged_in = result[4]


        # return True and the user object
        return True, user
    else:
        return False, "No user found for that stripe id"

def get_user_param(email: str, parameter: str):
    """
    Return the value of a single column for the user with the given email.
    If the parameter is not a valid column in users_list, return None.

    :param email: user's email
    :param parameter: column name to fetch
    :return: value or None
    """
    # Whitelist of allowed columns (kept in sync with users_list schema)
    allowed_columns = {
        "id", "resume_file", "email", "password", "internships_list", "favorites", "applied_to", "last_logged_in",
        "device_id", "first_name", "last_name", "intern_titles", "skills", "time_created", "filters",
        "auth_type", "plan", "last_refresh", "stripe_id", "stripe_meta", "reported_college",
        "removed_jobs", "subscription_status", "jobs_accepted", "messages_generated", "resume_json"
    }

    if parameter not in allowed_columns:
        capture_exception(Exception(f'ERROR: user param not allowed: {parameter}'))
        return None  # invalid/unknown column

    session = Session
    try:
        row = session.execute(
            text(f"SELECT {parameter} FROM {users_list_table} WHERE email = :email"),
            {"email": email},
        ).fetchone()
        # No commit needed for a SELECT; mirror existing pattern for cleanup
        session.remove()
        return row[0] if row is not None else None
    except Exception as e:
        session.rollback()
        capture_exception(e)
        session.remove()
        return None

