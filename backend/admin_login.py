import logging
from backend.tables import admin_list_table
from sentry_sdk import capture_exception
from sqlalchemy import Integer, text
from datetime import datetime
from backend.database_config import Session
import bcrypt
import re

"""
admin_login.py contains the AdminUser class and functions related to user management, and changes to the admin_list table.

Any new updates or functions to editing the admin_list table should be added here.
"""

admin_sample_accounts = ['sample.admin@mst.edu', 'sample.admin@umsl.edu', 'peter.h@rezify.ai']


class AdminUser:
    """
    The AdminUser class represents an admin in the system.
    """

    def __init__(self, email, first_name, last_name, password, time_created, school_abbreviation, school_fullname):
        try:
            self.id = Integer  # id represents the user's unique identifier
            self.email = email # email
            self.first_name = first_name # first name
            self.last_name = last_name # last name
            self.password = password # admin password
            self.last_logged_in = datetime.now()  # Datetime of the last time the user logged in - set to current time at first
            self.time_created = time_created  # Timestamp of when the user was created
            self.school_abbreviation = school_abbreviation # School abbreviation (e.g., 'mit')
            self.school_fullname = school_fullname # Full name of the school (e.g., 'Massachusetts Institute of Technology')
        except Exception as e:
            capture_exception(e)

    def to_dict(self):
        """
        Converts the User object into a serializable dictionary object for json purposes
        :return: dictionary of User object data
        """
        try:
            user_dict = {
                'id': self.id,
                'email': self.email,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'last_logged_in': self.last_logged_in.isoformat() if self.last_logged_in is not None else "",
                'time_created': self.time_created.isoformat() if self.time_created is not None else "",
                'school_abbreviation': self.school_abbreviation,
                'school_fullname': self.school_fullname
            }
            return user_dict
        except Exception as e:
            capture_exception(e)
            return {}

    def create_new_admin(self):
        """
        Creates a new admin in the database. It creates the admin_list table if it doesn't exist yet. It checks if the
        admin already exists by checking the email. If the admin doesn't exist, it adds the admin to the database.
        :return: boolean of success, message
        """
        session = Session
        try:
            # Create the admin table if it doesn't exist
            session.execute(text(f'''
                CREATE TABLE IF NOT EXISTS {admin_list_table}
                (id SERIAL PRIMARY KEY,
                 email TEXT,
                 first_name TEXT,
                 last_name TEXT,
                 password TEXT,
                 last_logged_in TIMESTAMP,
                 time_created TIMESTAMP,
                 school_abbreviation TEXT,
                 school_fullname TEXT
                                 )
            '''))
            session.commit()

            if not check_if_admin_exists(self.email):  # Making sure the admin doesn't exist already
                # Insert the new user into the admin_list table
                result = session.execute(text(f'''
                    INSERT INTO {admin_list_table} (email, first_name, last_name, password, last_logged_in, time_created, school_abbreviation, school_fullname)
                    VALUES (:email, :first_name, :last_name, :password, :last_logged_in, :time_created, :school_abbreviation, :school_fullname)
                    RETURNING id
                '''), {
                    'email': self.email,
                    'first_name': self.first_name,
                    'last_name': self.last_name,
                    'password': hash_password(self.password),
                    'last_logged_in': self.last_logged_in,
                    'time_created': self.time_created,
                    'school_abbreviation': self.school_abbreviation,
                    'school_fullname': self.school_fullname
                })
                self.id = result.fetchone()[0]
                session.commit()

                return True, f"AdminUser with email: {self.email} added successfully"
            else:
                return False, 'Email is already in use'
        except Exception as e:
            session.rollback()
            capture_exception(e)
            return False, 'An error occurred while creating the user, please try again'
        finally:
            session.remove()

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
                        UPDATE {admin_list_table}
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

    def update_admin_param(self, parameter, new_value):
        """
        This function updates a parameter in the database. It takes the parameter name and the new value as arguments.
        Then it updates the parameter in the database.
        :param parameter: string representing the parameter to be updated
        :param new_value: a value representing the new value to be set for the parameter
        :return: boolean representing success
        """
        if parameter == 'email':
            self.email = new_value
        if parameter == 'first_name':
            self.first_name = new_value
        if parameter == 'last_name':
            self.last_name = new_value
        elif parameter == 'last_logged_in':
            self.last_logged_in = new_value
        elif parameter == 'school_abbreviation':
            self.school_abbreviation = new_value
        elif parameter == 'school_fullname':
            self.school_fullname = new_value
        else:
            capture_exception(ValueError(f"Invalid parameter: {parameter}"))
            return False

        session = Session
        # Update the parameter in the database
        try:
            session.execute(text(f'''
                                UPDATE {admin_list_table}
                                SET {parameter} = :new_value
                                WHERE email = :email
                            '''), {'new_value': new_value, 'email': self.email})
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            capture_exception(e)
            return False
        finally:
            session.remove()


def check_if_admin_exists(email):
    """
    This function checks if an admin exists in the database by checking the email. It returns True if the user exists,
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
                FROM {admin_list_table}
                WHERE email = :email
            )
        '''), {'email': email}).scalar()
        return result
    except Exception as e:
        session.rollback()
        capture_exception(e)
        return False
    finally:
        session.remove()

def admin_user_login(email, password):
    """
    This function logs in a admin. It takes the email, password, and device id as parameters. It uses the email and
    password to attempt to log in to an account. If the login is successful, it returns True and the user object.
    :param email: string representing the email of the admin
    :param password: string representing the password of the admin
    :return: boolean of success, user object
    """
    session = Session
    try:
        # Query to check if the user exists. True if the user exists, False if not
        result = session.execute(text(f'''
            SELECT id, email, first_name, last_name, password, last_logged_in, time_created, school_abbreviation, school_fullname
            FROM {admin_list_table}
            WHERE email = :email
        '''), {'email': email}).fetchone()

        if result:  # If a user exists with that email, create a user object with the data from the database
            admin = AdminUser(
                email=result[1],
                first_name=result[2],
                last_name=result[3],
                password=result[4],
                time_created=result[6],
                school_abbreviation=result[7],
                school_fullname=result[8]
            )

            # Check if the password is correct
            password_check = verify_password(password, result[4])

            # If the password is correct, update the user object with the data from the database and return the user
            if password_check:
                admin.id = result[0]
                admin.last_logged_in = datetime.now()
                admin.update_admin_param('last_logged_in', datetime.now())
                return True, admin
            else:
                return False, "Incorrect password"
        else:
            return False, "Invalid credentials"
    except Exception as e:
        capture_exception(e)
        session.rollback()
        return False, "Error"
    finally:
        session.remove()


def get_admin_from_email(email):
    """
    This function gets a adminuser object from the database by their email.
    :param email: string representing the email of the admin
    :return: boolean of success, adm in object
    """
    session = Session
    # Query to get the user from the database by their email
    try:
        result = session.execute(text(f'''
                SELECT id, email, first_name, last_name, password, last_logged_in, time_created, school_abbreviation, school_fullname
                FROM {admin_list_table}
                WHERE email = :email
            '''), {'email': email}).fetchone()

        if result:  # If a user exists with that email, create a user object with the data from the database
            admin = AdminUser(
                email=result[1],
                first_name=result[2],
                last_name=result[3],
                password=result[4],
                time_created=result[6],
                school_abbreviation=result[7],
                school_fullname=result[8]
            )
            admin.id = result[0]
            admin.last_logged_in = result[5]

            # return True and the user object
            return True, admin
        else:
            return False, "No admin found for that email"

    except Exception as e:
        capture_exception(e)
        session.rollback()
        return False, "Error"
    finally:
        session.remove()


def delete_admin_account(email):
    """
    This function deletes a admin from the database by their email.
    :param email: string representing the email of the admin
    :return: boolean of success
    """
    session = Session
    try:
        # Delete the row of the admin table associated with the email
        session.execute(text(f'''
            DELETE FROM {admin_list_table}
            WHERE email = :email
        '''), {'email': email})
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        capture_exception(e)
        return False
    finally:
        session.remove()


def delete_all_admins():
    """
    This function deletes all admins from the database. It is used for testing purposes only - for if you are trying to
    clean the database for some reason.

    :return: boolean of success, message
    """
    session = Session
    try:
        # Delete all rows from the admin table
        session.execute(text(f'DELETE FROM {admin_list_table}'))
        session.commit()
        logging.debug("All admins deleted successfully")
        session.remove()
        return True, "All admins deleted successfully"
    except Exception as e:
        session.rollback()
        capture_exception(e)
        session.remove()
        return False, "Error"


def get_admins_from_database():
    """
    This function gets all admins from the database.
    :return: list of users
    """
    session = Session
    # Get all users from the database
    results = session.execute(text(f'SELECT * FROM {admin_list_table}')).fetchall()
    session.commit()
    users = []
    for result in results:
        user = {
            'id': result[0],
            'email': result[1],
            'first_name': result[2],
            'last_name': result[3],
            'last_logged_in': result[5],
            'time_created': result[6],
            'school_abbreviation': result[7],
            'school_fullname': result[8]
        }
        users.append(user)
    return users




def hash_password(password: str) -> str:
    """Hashes a password using bcrypt and returns the hashed version as a string."""
    salt = bcrypt.gensalt()  # Generate a salt
    hashed_password = bcrypt.hashpw(password.encode(), salt)  # Hash password
    return hashed_password.decode()  # Convert bytes to string for storage


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a given password against the stored hashed password."""
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

if __name__ == "__main__":
    # For testing purposes only
    logging.basicConfig(level=logging.DEBUG)

    # delete_all_admins()