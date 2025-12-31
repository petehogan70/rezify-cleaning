import json
import random
import re
import string
from datetime import datetime, timedelta

from flask import request, redirect, url_for, jsonify, session
from flask_cors import cross_origin
from sentry_sdk import capture_exception, capture_message

from backend.email_sending import send_verification_email_sendgrid
from backend.session_management import get_param_from_db, save_param_to_db, clear_session, \
    get_colors, is_locked_out, check_if_admin_valid
from backend.admin_login import admin_user_login, AdminUser, check_if_admin_exists, admin_sample_accounts


def admin_account_routes(app):
    @app.route('/api/admin_login', methods=['GET', 'POST'])
    @cross_origin()
    def admin_login():
        """
            This function handles the admin login process. It takes the email and password from the request,
            checks if they are valid, and if so, logs the user in and redirects them to the admin page.
        """

        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        failed_att = session.get('failed_attempts', 0)  # Get the number of failed attempts

        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        colors = get_colors(session_id)  # Get the colors for the school theme

        clear_session(session)  # Clear session except for session_id and school
        session['failed_attempts'] = failed_att

        if is_locked_out(session_id):  # Check if the user is locked out
            return json.dumps({'error_message': 'Limit Exceeded. Try again later.', 'colors': colors})

        if request.method == 'POST':
            try:
                # Get the login credentials entered and try to login with it
                email = request.form['email']
                password = request.form['password']
                success, user = admin_user_login(email, password)

                if success:  # If log in worked
                    save_param_to_db('user_email', user.email, session_id)
                    save_param_to_db('admin', True, session_id)

                    session['school'] = user.school_abbreviation

                    save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])

                    return jsonify({'redirect': '/admin'})

                else:  # If the login didn't work, re-render the login page with an error message
                    session['failed_attempts'] = session.get('failed_attempts',
                                                             0) + 1  # Increment the failed attempts in the session
                    if session.get('failed_attempts', 0) > 10:
                        # If the failed exceeds 10, lock the user out for 2 hours
                        save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                        clear_session(session)

                    return json.dumps({'error_message': 'Invalid Credentials', 'colors': colors})

            except Exception as e:  # If there is any error, re-render the login page with an error message
                capture_exception(e)
                return json.dumps(
                    {'error_message': 'An error occurred during login, please try again', 'colors': colors})

        return json.dumps({'colors': colors})

    @app.route('/api/admin_register', methods=['GET', 'POST'])
    @cross_origin()
    def admin_register():
        """
            This function handles the registration page for admin users. It attempts to register a new admin user with the
            entered in email and password. If successful, it redirects to the admin page. If not, it returns an error.
            The sample_admin_accounts list contains a list of emails that are explicitly approved for admin registration (without email verification). Should be used
            to give people with specific emails access to the admin page (example: demo accounts).
        """

        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        failed_att = session.get('failed_attempts', 0)  # Get the number of failed attempts
        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        colors = get_colors(session_id)  # Get the colors for the school theme

        clear_session(session)  # Clear session except for session_id and school
        session['failed_attempts'] = failed_att

        registration_info = get_param_from_db('resume_info', session_id)  # Get the registration info from the session database, which is saved under 'resume_info'


        if is_locked_out(session_id):  # Check if the user is locked out
            return json.dumps({'colors': colors, 'error_message': "Limit Exceeded. Try Again Later."})

        # If the user presses the register button, get the entered in info and try to register
        if request.method == 'POST':

            try:
                # Get the name, email, and password from the register page
                first_name = request.form['first_name']
                last_name = request.form['last_name']
                email = request.form['email']
                password = request.form['password']
                confirm_password = request.form['confirm_password']
                school_fullname = request.form.get('college')
                if school_fullname is None:
                    return json.dumps({'colors': colors, 'error_message': "School cannot be empty. Please try again."})

                # Save the first name, last name, and email entered to the resume info. So if there is an error,
                # the user doesn't have to re-enter it
                registration_info = {'first_name': first_name, 'last_name': last_name, 'email': email, 'password': password,
                               'school_fullname': school_fullname}
                save_param_to_db('resume_info', json.dumps(registration_info), session_id)

                # If the passwords do not match, return an error message on the register page
                if password != confirm_password:
                    registration_message = 'Passwords do not match'
                    return json.dumps(
                        {'resume_info': registration_info, 'colors': colors, 'error_message': registration_message})

                # If the password doesn't contain an upper case letter
                if not re.search(r'[A-Z]', password):
                    registration_message = 'Password must include at least one uppercase letter.'
                    return json.dumps(
                        {'resume_info': registration_info, 'colors': colors, 'error_message': registration_message})

                # if the password doesn't contain a special character
                if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                    registration_message = 'Password must include at least one special character.'
                    return json.dumps(
                        {'resume_info': registration_info, 'colors': colors, 'error_message': registration_message})

                # If the entered in email and password is valid, continue

                if not check_if_admin_exists(email):  # Make sure the email is not already in use

                    # Save the email to the session database to keep track of it for registering
                    save_param_to_db('user_email', email, session_id)

                    if email in admin_sample_accounts:  # SKIP Verification if a sample account

                        # Get the required info from the database
                        user_email = get_param_from_db('user_email', session_id)
                        registration_info = get_param_from_db('resume_info', session_id)

                        if not check_if_admin_valid(user_email, school):
                            registration_message = 'Admin registration is not allowed with this email.'
                            return json.dumps(
                                {'resume_info': registration_info, 'colors': colors, 'error_message': registration_message})

                        # Create a new admin user
                        user = AdminUser(email=user_email, first_name=registration_info['first_name'], last_name=registration_info['last_name'],
                                         password=registration_info['password'], time_created=datetime.now(), school_abbreviation=school,
                                         school_fullname=registration_info['school_fullname'])

                        success, registration_message = user.create_new_admin()  # Call the function to create a new admin user

                        registration_info[
                            'password'] = None  # Remove the password from the resume info to avoid saving it in the database
                        save_param_to_db('resume_info', json.dumps(registration_info),
                                         session_id)  # Save the resume info to the session database

                        if success:  # If the user was created successfully, redirect to the admin page

                            save_param_to_db('admin', True, session_id)

                            return jsonify({'redirect': '/admin'})
                        else:  # If there was an error creating the user, return an error message
                            return json.dumps(
                                {'resume_info': registration_info, 'colors': colors, 'error_message': 'An error occurred during registration, please try again'})

                    else:

                        if check_if_admin_valid(email, school):
                            # Prompt email verification if a regular admin user is registering
                            safe_email = email.replace('@', '[@]').replace('.', '[.]')
                            capture_message(f"REGISTRATION STEP 1 ({safe_email}). Registration Successful.", level="info")
                            return jsonify({'redirect': '/verify_email?type=admin'})
                        else:
                            registration_message = 'Admin registration is not allowed with this email.'
                            return json.dumps(
                                {'resume_info': registration_info, 'colors': colors, 'error_message': registration_message})

                else:
                    # If the email is already in use, re-render the register page with an error message
                    # Pass the resume info to the register page so no data is lost

                    session['failed_attempts'] = session.get('failed_attempts',
                                                             0) + 1  # Increment the failed attempts in the session
                    if session.get('failed_attempts', 0) > 15:
                        # If the failed exceeds 10, lock the user out for 2 hours
                        save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                        clear_session(session)

                    return json.dumps \
                        ({'resume_info': registration_info, 'colors': colors, 'error_message': 'Email is already in use'})

            except Exception as e:
                # If there is any error during registration, re-render the register page with an error message
                # Pass the resume info to the register page so no data is lost
                capture_exception(e)
                return json.dumps({'resume_info': registration_info, 'colors': colors,
                                   'error_message': 'An error occurred during registration, please try again'})

        return json.dumps({'resume_info': registration_info, 'colors': colors, 'school': school})


    @app.route('/api/admin_verify_email', methods=['GET', 'POST'])
    @cross_origin()
    def admin_verify_email():
        """
        This function handles the email verification process during user registration. It sends a verification code to the
        user's email and verifies the code entered by the user. If the verification is successful, it creates a new user
        account. If the verification fails, it returns an error message.
        """
        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        colors = get_colors(session_id)  # Get the colors for the school theme

        user_email = get_param_from_db('user_email', session_id)

        try:

            if is_locked_out(session_id):
                # If the user is locked out, show them the error message
                return json.dumps({'verify': True, 'user_email': user_email, 'colors': colors,
                                   'error_message': 'Limit Exceeded. Try Again Later'})

            if request.method == 'POST':  # If the user is submitting the verification code
                code = request.form['code']  # Get the code entered by the user
                verification_code = get_param_from_db('code',
                                                      session_id)  # Get the code saved in the session database to check
                code_expiry = get_param_from_db('code_expiry', session_id)  # Get the code expiry time

                # Verify code with code entered
                if code == verification_code and datetime.now() < code_expiry:

                    # Get the other info from the database necessary for making a user
                    registration_info = get_param_from_db('resume_info', session_id)

                    # Create a new admin user
                    user = AdminUser(email=user_email, first_name=registration_info['first_name'],
                                     last_name=registration_info['last_name'],
                                     password=registration_info['password'], time_created=datetime.now(),
                                     school_abbreviation=school,
                                     school_fullname=registration_info['school_fullname'])

                    success, registration_message = user.create_new_admin()  # Call the function to create a new admin user

                    registration_info[
                        'password'] = None  # Remove the password from the resume info to avoid saving it in the database
                    save_param_to_db('resume_info', json.dumps(registration_info),
                                     session_id)  # Save the resume info to the session database

                    if success:  # If the user was created successfully, redirect to the admin page

                        safe_email = user.email.replace('@', '[@]').replace('.', '[.]')

                        capture_message(f"REGISTRATION STEP 3 ({safe_email}). Verification/Registration complete.")

                        save_param_to_db('admin', True, session_id)

                        return jsonify({'redirect': '/admin'})

                    else:  # If there was an error creating the user, return an error message
                        return json.dumps(
                            {'resume_info': registration_info, 'colors': colors,
                             'error_message': 'An error occurred during registration, please try again'})


                else:
                    session['failed_attempts'] = session.get('failed_attempts',
                                                             0) + 1  # Increment the failed attempts in the session
                    if session.get('failed_attempts', 0) > 10:
                        # If the failed exceeds 10, lock the user out for 2 hours
                        save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                        clear_session(session)

                    # Verification code did not match, re-render the register page with an error message
                    return json.dumps({'verify': True, 'user_email': user_email, 'colors': colors,
                                       'error_message': 'Incorrect or Expired Code'})
            else:

                official_code = generate_verification_code()  # Generate a random verification code to send

                session['code_count'] = session.get('code_count', 0) + 1  # Increment the code count in the session
                if session.get('code_count', 0) > 10:
                    # If the code count exceeds 10, lock the user out for 2 hours
                    save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                    clear_session(session)

                # Save the code and the 10 min expiry to the database under the current session so we can check if it matches later
                save_param_to_db('code', official_code, session_id)
                save_param_to_db('code_expiry', datetime.now() + timedelta(minutes=10), session_id)

                send_verification_email_sendgrid(user_email, official_code)  # Send the code to the email

                # Render the register page with the 'verify' parameter as true so it loads the verification code input
                return json.dumps({'verify': True, 'user_email': user_email, 'colors': colors})

        except Exception as e:
            capture_exception(e)
            return json.dumps({'verify': True, 'user_email': user_email, 'colors': colors,
                               'error_message': 'An Unknown Error Occured'})


## HELPER FUNCTIONS ##
def generate_verification_code():
    """
    Generates a 6-character alphanumeric verification code using
    uppercase letters and digits.
    """
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(characters, k=6))
