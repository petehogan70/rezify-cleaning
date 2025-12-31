import json
import random
import re
import string
from datetime import datetime, timedelta

from flask import request, redirect, url_for, jsonify, session
from flask_cors import cross_origin
from sentry_sdk import capture_exception, capture_message

from backend.email_sending import send_verification_email_sendgrid, send_recovery_email_sendgrid, send_verification_email_support, \
    send_password_recovery_email_support
from backend.login import User, user_login, get_user_from_email, delete_account_email, check_if_user_exists, \
    check_if_valid_email, check_user_plan, \
    approved_passwords, premium_emails, edu_bypass_emails
from backend.payment import register_stripe_user, setup_checkout_session, get_stripe_session, handle_stripe_webhook, \
    create_billing_portal_for_user
from backend.session_management import get_param_from_db, save_param_to_db, clear_session, \
    get_colors, is_locked_out, get_school_from_user, delete_session_data, \
    check_if_school_accepts_email
from backend.admin_login import check_if_admin_exists, get_admin_from_email, delete_admin_account


def account_routes(app):

    @app.route('/api/update_profile', methods=['POST'])
    @cross_origin()
    def update_profile():
        """
            Updates the user's profile settings based on form post request

            Returns:
            New json user object
        """

        try:
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({"error_message": 'Fail'})

            clear_session(session) # Clear session except for session_id and school

            success, user = get_user_from_email(get_param_from_db('user_email', session_id))

            if success:
                new_first_name = request.form.get('first_name')
                new_last_name = request.form.get('last_name')
                new_email = request.form.get('email')
                new_reported_college = request.form.get('college')
                if new_first_name and new_first_name != user.first_name:
                    user.update_user_param("first_name", new_first_name)
                if new_last_name and new_last_name != user.last_name:
                    user.update_user_param("last_name", new_last_name)
                if new_email and new_email != user.email:
                    '''
                    Ignore for now, we need to discuss with team
                    '''
                    # user.update_user_param("email", new_email)
                    # save_param_to_db('user_email', user.email, session_id)
                if new_reported_college and new_reported_college != user.reported_college:
                    user.update_user_param("reported_college", new_reported_college)
                return json.dumps({"user": user.to_dict() if (type(user) == User) else None})
            else:  # If the login failed
                session['session_expired'] = True  # To indicate that the account session has expired
                return jsonify({"error_message": 'Fail'})

        except Exception as e:
            capture_exception(e)
            return jsonify({"error_message": 'Fail'})



    @app.route('/api/login', methods=['GET', 'POST'])
    @cross_origin()
    def login():
        """
            This function handles the login page of the application. It attempts to login with the entered in email and
            password. If successful, it redirects to the results page. If not, it returns an error message.
        """

        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        failed_att = session.get('failed_attempts', 0)  # Get the number of failed attempts
        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        colors = get_colors(session_id)  # Get the colors for the school theme

        try:

            clear_session(session) # Clear session except for session_id and school
            session['failed_attempts'] = failed_att

            if is_locked_out(session_id):  # Check if the user is locked out
                return json.dumps({'error_message': 'Limit Exceeded. Try again later.', 'colors': colors})

            if request.method == 'POST':
                try:
                    # Get the login credentials entered and try to login with it
                    email = request.form['email']
                    password = request.form['password']
                    success, user = user_login(email, password)

                    if success:  # If log in worked
                        save_param_to_db('user_email', user.email, session_id)

                        # Set school based on email ending
                        session['school'] = get_school_from_user(user)
                        save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])

                        # Direct the user to the results page with their results
                        session['load'] = 'first'
                        session['login_refresh'] = True
                        return jsonify({'redirect': '/results'})

                    else:  # If the login didn't work, re-render the login page with an error message
                        session['failed_attempts'] = session.get('failed_attempts', 0) + 1  # Increment the failed attempts in the session
                        if session.get('failed_attempts', 0) > 10:
                            # If the failed exceeds 10, lock the user out for 2 hours
                            save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                            clear_session(session)

                        return json.dumps({'error_message': 'Invalid Credentials', 'colors': colors})

                except Exception as e:  # If there is any error, re-render the login page with an error message
                    capture_exception(e)
                    return json.dumps({'error_message': 'An error occurred during login, please try again', 'colors': colors})

            return json.dumps({'colors': colors})

        except Exception as e:
            capture_exception(e)
            json.dumps({'error_message': 'An error occurred, please try again', 'colors': colors})


    @app.route('/api/register', methods=['GET', 'POST'])
    @cross_origin()
    def register():
        """
            This function handles the registration page of the application. It attempts to register a new user with the
            entered in email and password. If successful, it redirects to the results page. If not, it returns an error.
            The approved_email_endings list contains the email endings that are allowed for registration. Should be used
            when we need gto approve any email with a certain ending, such a new school we partner with. Email verification
            is still required for these emails.
            The approved_passwords list contains a list of access passwords that give a user access to the results page
            no matter what email is used. Should be used to send out for testing or giving specific people access. Email
            verification is bypassed for anyone using these passwords.
            The approved_emails list contains a list of emails that are explicitly approved for registration. Should be used
            to give pople with specific emails access to the results page (example: demo accounts):
            Email verification is bypassed for anyone using these emails.
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

        # Get the parsed resume info from the user's current session
        resume_info = get_param_from_db('resume_info', session_id)

        if resume_info is None or resume_info.get('resume_file', None) is None:
            has_resume_entered = False
        else:
            has_resume_entered = True



        if is_locked_out(session_id):  # Check if the user is locked out
            return json.dumps \
                ({'resume_info': resume_info, 'colors': colors, 'error_message' :"Limit Exceeded. Try Again Later."})

        # If the user presses the register button, get the entered in info and try to register
        if request.method == 'POST':

            try:
                # Get the name, email, and password from the register page
                first_name = request.form['first_name']
                last_name = request.form['last_name']
                email = request.form['email']
                password = request.form['password']
                confirm_password = request.form['confirm_password']
                reported_college = request.form.get('college')
                if reported_college is None:
                    reported_college = school

                # Save the first name, last name, and email entered to the resume info. So if there is an error,
                # the user doesn't have to re-enter it
                resume_info['first_name'] = first_name
                resume_info['last_name'] = last_name
                resume_info['email'] = email
                resume_info['reported_college'] = reported_college
                save_param_to_db('resume_info', json.dumps(resume_info), session_id)

                # If the email ending isn't approved, if the email isn't in the approved emails list, and if the password
                # isn't in the approved passwords list.
                # Inform the user that they don't have a valid email and return to the register page

                if school != 'rezify' and not check_if_school_accepts_email(email, school):
                    # If the school is not rezify and the email doesn't match the school's accepted emails, send an error
                    registration_message = (f'You must register with a valid {school} email address while in this domain. '
                                            f'Please leave this schools domain to register with this email.')
                    return json.dumps({'resume_info': resume_info, 'colors': colors, 'error_message': registration_message})


                # If the passwords do not match, return an error message on the register page
                if password != confirm_password:
                    registration_message = 'Passwords do not match'
                    return json.dumps({'resume_info': resume_info, 'colors': colors, 'error_message' :registration_message})

                # If the password doesn't contain an upper case letter
                if not re.search(r'[A-Z]', password):
                    registration_message = 'Password must include at least one uppercase letter.'
                    return json.dumps({'resume_info': resume_info, 'colors': colors, 'error_message' :registration_message})

                # if the password doesn't contain a special character
                if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                    registration_message = 'Password must include at least one special character.'
                    return json.dumps({'resume_info': resume_info, 'colors': colors, 'error_message' :registration_message})

                # If the entered in email and password is valid, continue

                if not check_if_user_exists(email):  # Make sure the email is not already in use

                    # Save the info to the session database to keep track of it for registering
                    resume_info['first_name'] = first_name
                    resume_info['last_name'] = last_name
                    resume_info['password'] = password
                    resume_info['reported_college'] = reported_college
                    save_param_to_db('resume_info', json.dumps(resume_info), session_id)
                    save_param_to_db('user_email', email, session_id)
                    if (".edu" in email
                                  [-4:].lower()) or email in edu_bypass_emails or email in premium_emails or password in approved_passwords:
                        if email in premium_emails or password in approved_passwords:  # SKIP Verification if approved email or password

                            # Get the required info from the database
                            user_email = get_param_from_db('user_email', session_id)
                            resume_info = get_param_from_db('resume_info', session_id)
                            jobs_list = get_param_from_db('jobs_list', session_id)
                            filters = get_param_from_db('filters', session_id)
                            # Load the resume info from the session database, and save what we want into the resume_json user column
                            resume_json = get_param_from_db('resume_info', session_id)
                            resume_dict = json.loads(resume_json) if isinstance(resume_json, str) else resume_json
                            # keep only the keys you want
                            filtered_resume = {
                                k: v for k, v in resume_dict.items()
                                if k in ["experiences", "relevant_coursework"]
                            }
                            # if you want it back as JSON string
                            resume_json = filtered_resume

                            # Create a new user
                            user = User(resume_file=resume_info['resume_file'], email=user_email,
                                        password=resume_info['password'], first_name=resume_info['first_name'],
                                        last_name=resume_info['last_name'],
                                        intern_titles=resume_info['intern_titles'],
                                        skills=resume_info['skills'], time_created=datetime.now(), filters=filters, auth_type="password",
                                        plan="basic", last_refresh=None ,stripe_id=None, stripe_meta=None, reported_college=reported_college, subscription_status=None, resume_json=resume_json)

                            success, registration_message = user.create_new_user(jobs_list)  # Call the function to create a new user

                            resume_info['password'] = None  # Remove the password from the resume info to avoid saving it in the database
                            save_param_to_db('resume_info', json.dumps(resume_info), session_id)  # Save the resume info to the session database

                            if success:  # If the user was created successfully, redirect to the results page


                                # Set school based on email ending
                                session['school'] = get_school_from_user(user)
                                save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])

                                check_user_plan(user)

                                if user.plan == "premium":
                                    if len(get_param_from_db('jobs_list', session_id)) > 0:
                                        # If they jobs list exists, this means they are registering from the results page
                                        session['load'] = 'first'
                                        return json.dumps({'redirect': '/results'})
                                    else:
                                        # If they register from the index page, redirect to the index page
                                        return json.dumps({'redirect': '/index'})

                                if len(get_param_from_db('jobs_list', session_id)) > 0:
                                    # If they jobs list exists, this means they are registering from the results page
                                    session['load'] = 'first'
                                    return json.dumps({'redirect': '/plans?redirect=results'})
                                else:
                                    # If they register from the index page, redirect to the index page
                                    return json.dumps({'redirect': '/plans?redirect=index'})

                        else:
                            # Prompt email verification if a regular user is registering
                            safe_email = email.replace('@', '[@]').replace('.', '[.]')
                            capture_message(f"REGISTRATION STEP 1 ({safe_email}). Registration Successful.", level="info")
                            return jsonify({'redirect': '/verify_email'})
                    else:
                        # If non edu email

                        session['failed_attempts'] = session.get('failed_attempts', 0) + 1  # Increment the failed attempts in the session
                        if session.get('failed_attempts', 0) > 15:
                            # If the failed exceeds 10, lock the user out for 2 hours
                            save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                            clear_session(session)

                        return json.dumps({'resume_info': resume_info, 'colors': colors, 'error_message' :'Please register with your school provided .edu email address.'})

                else:
                    # If the email is already in use, re-render the register page with an error message
                    # Pass the resume info to the register page so no data is lost

                    session['failed_attempts'] = session.get('failed_attempts', 0) + 1  # Increment the failed attempts in the session
                    if session.get('failed_attempts', 0) > 15:
                        # If the failed exceeds 10, lock the user out for 2 hours
                        save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                        clear_session(session)

                    return json.dumps \
                        ({'resume_info': resume_info, 'colors': colors, 'error_message' :'Email is already in use'})

            except Exception as e:
                # If there is any error during registration, re-render the register page with an error message
                # Pass the resume info to the register page so no data is lost
                capture_exception(e)
                return json.dumps({'resume_info': resume_info, 'colors': colors, 'error_message' :'An error occurred during registration, please try again'})

        return json.dumps({'resume_info': resume_info, 'colors': colors, 'school': school, 'has_resume_entered': has_resume_entered})


    @app.route('/api/verify_email', methods=['GET', 'POST'])
    @cross_origin()
    def verify_email():
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
                verification_code = get_param_from_db('code', session_id)  # Get the code saved in the session database to check
                code_expiry = get_param_from_db('code_expiry', session_id)  # Get the code expiry time

                # Verify code with code entered
                if code == verification_code and datetime.now() < code_expiry:

                    # Get the other info from the database necessary for making a user
                    resume_info = get_param_from_db('resume_info', session_id)
                    jobs_list = get_param_from_db('jobs_list', session_id)
                    filters = get_param_from_db('filters', session_id)
                    resume_json = get_param_from_db('resume_info', session_id)
                    resume_dict = json.loads(resume_json) if isinstance(resume_json, str) else resume_json
                    # keep only the keys you want
                    filtered_resume = {
                        k: v for k, v in resume_dict.items()
                        if k in ["experiences", "relevant_coursework"]
                    }
                    # if you want it back as JSON string
                    resume_json = filtered_resume

                    # Create a new user
                    user = User(resume_file=resume_info['resume_file'], email=user_email, password=resume_info['password'], first_name=resume_info['first_name'], last_name=resume_info['last_name'],
                                intern_titles=resume_info['intern_titles'],
                                skills=resume_info['skills'], time_created=datetime.now(), filters=filters, auth_type="password",
                                plan="basic", last_refresh=None ,stripe_id=None, stripe_meta=None, reported_college=resume_info['reported_college'],
                                subscription_status=None, resume_json=resume_json)


                    success, registration_message = user.create_new_user(jobs_list)  # Call the function to create a new user

                    resume_info['password'] = None  # Remove the password from the resume info to avoid saving it in the database
                    save_param_to_db('resume_info', json.dumps(resume_info), session_id)  # Save the resume info to the session database

                    if success:  # If the user was created successfully, redirect to the results page

                        # Set school based on email ending
                        session['school'] = get_school_from_user(user)
                        save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])

                        check_user_plan(user)

                        safe_email = user.email.replace('@', '[@]').replace('.', '[.]')

                        capture_message(f"REGISTRATION STEP 3 ({safe_email}). Verification/Registration complete.")

                        if user.plan == "premium":
                            if len(get_param_from_db('jobs_list', session_id)) > 0:
                                # If they jobs list exists, this means they are registering from the results page
                                session['load'] = 'first'
                                return json.dumps({'redirect': '/results'})
                            else:
                                # If they register from the index page, redirect to the index page
                                return json.dumps({'redirect': '/index'})

                        if len(get_param_from_db('jobs_list', session_id)) > 0:
                            # If they jobs list exists, this means they are registering from the results page
                            session['load'] = 'first'
                            return json.dumps({'redirect': '/plans?redirect=results'})
                        else:
                            # If they register from the index page, redirect to the index page
                            return json.dumps({'redirect': '/plans?redirect=index'})
                    else:
                        # If there was an error creating the user, return an error message on the register page
                        return json.dumps({'verify': True, 'user_email': user_email, 'colors': colors, 'error_message': 'An error occurred during registration, please try again'})

                else:
                    session['failed_attempts'] = session.get('failed_attempts', 0) + 1  # Increment the failed attempts in the session
                    if session.get('failed_attempts', 0) > 10:
                        # If the failed exceeds 10, lock the user out for 2 hours
                        save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                        clear_session(session)


                    # Verification code did not match, re-render the register page with an error message
                    return json.dumps({'verify': True, 'user_email': user_email, 'colors': colors, 'error_message': 'Incorrect or Expired Code'})
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
            return json.dumps({'verify': True, 'user_email': user_email, 'colors': colors, 'error_message': 'An unknown error occurred'})



    @app.route('/api/recover', methods=['GET', 'POST'])
    @cross_origin()
    def recover():
        """
        This function handles the password recovery process (NOT CHANGE PASSWORD RECOVERY). It takes the email of the user and checks if it is valid.
        If valid, it redirects the user to the change password page. If not, it returns an error message.
        """

        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        admin = get_param_from_db('admin', session_id)  # Weather or not the user is an admin
        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        colors = get_colors(session_id)  # Get the colors for the school theme

        try:

            if is_locked_out(session_id):  # If the session is locked, return to page with error
                return json.dumps({'recover': True, 'colors': colors,
                                   'error_message': 'Limit Exceeded. Try Again Later'})


            if request.method == "POST":
                # Get the email entered by the user and see if it is linked to any account
                email = request.form['email']
                if admin:
                    valid_email = check_if_admin_exists(email)
                else:
                    valid_email = check_if_valid_email(email)

                if valid_email:
                    # If the email is valid, send user to the change password page
                    save_param_to_db('user_email', email, session_id)
                    session['recover_page'] = True  # Set the recover page flag to true
                    return json.dumps({'redirect': '/change_password'})
                else:
                    session['failed_attempts'] = session.get('failed_attempts', 0) + 1  # Increment the failed att in the session
                    if session.get('failed_attempts', 0) > 10:
                        # If the failed att exceeds 10, lock the user out for 2 hours
                        save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                        clear_session(session)

                    return json.dumps({'recover': True, 'colors': colors,
                                       'error_message': 'Email not linked to any account'})

            # Load the login page with the recover parameter set to true, so it loads the recover page
            session['recover_page'] = True  # Set the recover page flag to true
            return json.dumps({'redirect': '/change_password'})

        except Exception as e:
            capture_exception(e)
            return json.dumps({'recover': True, 'colors': colors,
                               'error_message': 'An Unknown Error Occurred'})


    @app.route('/api/change_password', methods=['GET', 'POST'])
    @cross_origin()
    def change_password():
        try:
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            school = session.get('school', 'rezify')
            admin = get_param_from_db('admin', session_id)  # Weather or not the user is an admin
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return redirect(url_for('set_session_id', school=school))

            recover_page = session.get('recover_page', False)  # Check if the recover page flag is set
            colors = get_colors(session_id)  # Get the colors for the school theme

            if admin:
                success, user = get_admin_from_email(get_param_from_db('user_email', session_id))
            else:
                success, user = get_user_from_email(get_param_from_db('user_email', session_id))

            if not success:
                session['session_expired'] = True  # To indicate that the session has expired
                return redirect(url_for('set_session_id', school=school))

            if is_locked_out(session_id):  # If the session is locked, return to page with error
                if recover_page or recover_page == 'True':
                    return json.dumps({'error_message': 'Limit Exceeded. Try Again Later.'})
                else:
                    return json.dumps({'error_message': 'Limit Exceeded. Try Again Later.'})



            if request.method == 'POST':  # If the user is submitting the change/recover password form

                req_type = request.form['type']  # Get the type of request (change or recover)

                if req_type == 'recover':  # If the user is trying to recover their password
                    try:
                        code = request.form['code']  # Get the code entered by the user
                        password = request.form['password']  # Get the password entered by the user
                        confirm_password = request.form['confirm_password']
                        official_code = get_param_from_db('code', session_id)  # Get the code saved in the session database to check
                        code_expiry = get_param_from_db('code_expiry', session_id)  # Get the code expiry time

                        # Verify code entered
                        if code == official_code and datetime.now() < code_expiry:
                            # If the verification code matches, change the password to the new password entered.
                            # The '!rezify_verification_code!' is a placeholder for the current_password
                            # Since the user is recovering their password, we don't need to check the old password.
                            # This signals that the user is recovering their password and the verification code is correct.
                            success, message = user.change_password('!rezify_verification_code!', password, confirm_password)

                            if success:
                                # If the password was changed successfully, redirect to the login page to re-login
                                if admin:
                                    return json.dumps({'redirect': '/login?fromRecover=true&type=admin'})
                                else:
                                    return json.dumps({'redirect': '/login?fromRecover=true'})
                            else:
                                # If there was an error changing the password, return an error message
                                return json.dumps({'error_message': message})
                        else:
                            session['failed_attempts'] = session.get('failed_attempts', 0) + 1  # Increment the failed att in the session
                            if session.get('failed_attempts', 0) > 10:
                                # If the failed att exceeds 10, lock the user out for 2 hours
                                save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                                clear_session(session)

                            # If the verification code did not match, re-render the recover page with an error message
                            return json.dumps({'error_message': 'Incorrect or Expired Code'})

                    except Exception as e:
                        capture_exception(e)
                        return json.dumps({'error_message': 'An Unknown Error Occurred'})

                elif req_type == 'change':  # If the user is trying to change their password
                    try:
                        old_password = request.form['old_password']  # Get the old password entered by the user
                        password = request.form['password']  # Get the new password entered by the user
                        confirm_password = request.form['confirm_password']

                        # Change the password if the old password is correct
                        success, message = user.change_password(old_password, password, confirm_password)

                        if success:
                            # If the password was changed successfully, redirect to the results page
                            # The change=True will trigger a success message on the results page
                            if admin:
                                session['change'] = True
                                return json.dumps({'redirect': '/admin'})
                            else:
                                session['load'] = 'first'
                                session['change'] = True
                                return json.dumps({'redirect': '/results'})
                        else:
                            session['failed_attempts'] = session.get('failed_attempts', 0) + 1  # Increment the failed att in the session
                            if session.get('failed_attempts', 0) > 10:
                                # If the failed att exceeds 10, lock the user out for 2 hours
                                save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                                clear_session(session)

                            # If there was an error changing the password, return an error message
                            return json.dumps({'error_message': message})

                    except Exception as e:
                        capture_exception(e)
                        return json.dumps({'error_message': 'An Uknown Error Occurred'})

            else:  # If the user is just loading the page without submitting anything
                user_email = user.email

                if recover_page or recover_page == 'True':  # If the user is trying to recover their forgotten password
                    recovery_code = generate_verification_code()  # Generate a random verification code to send

                    session['code_count'] = session.get('code_count', 0) + 1  # Increment the code count in the session
                    if session.get('code_count', 0) > 10:
                        # If the code count exceeds 10, lock the user out for 2 hours
                        save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                        clear_session(session)

                    # Save the code and the 10 min expiry to the database under the current session so we can check if it matches later
                    save_param_to_db('code', recovery_code, session_id)
                    save_param_to_db('code_expiry', datetime.now() + timedelta(minutes=10), session_id)

                    send_recovery_email_sendgrid(user_email, recovery_code)  # Send the code to the email

                    # Render the recover page with the 'recover' parameter as true so it loads the verification code input
                    return json.dumps({'recover': True, 'user_email': user_email, 'colors': colors})
                else:
                    # Render the recover page without the 'recover' parameter, this means the user is trying to change their password
                    return json.dumps({'recover': False, 'user_email': user_email, 'colors': colors})

        except Exception as e:
            capture_exception(e)
            return json.dumps({'error_message': 'An Unknown Error Occurred'})


    @app.route('/api/logout', methods=['POST'])
    @cross_origin()
    def logout():
        try:
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            admin = get_param_from_db('admin', session_id)  # Weather or not the user is an admin

            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return 'success'

            clear_session(session)  # Clear session except for session_id and school

            email = get_param_from_db('user_email', session_id)

            if admin:
                success, user = get_admin_from_email(email)
            else:
                success, user = get_user_from_email(email)

            if not success:  # If the user-getting failed, the session expired (or they logged out)
                session['session_expired'] = True  # To indicate that the session has expired
                return 'success'

            if admin:
                user.update_admin_param('last_logged_in', None)
            else:
                user.update_user_param('last_logged_in', None)

            delete_session_data(session_id)

            session.clear()  # Fully clear the session data
            return 'success'  # Back to the index page un-logged in

        except Exception as e:
            capture_exception(e)
            return 'fail'


    @app.route('/api/delete_account', methods=['POST'])
    def delete_account():
        """
        This function handles the account deletion process. It takes the session ID from the request and deletes the user.
        It will send them back to the index page un-logged in.
        """
        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        admin = get_param_from_db('admin', session_id)  # Weather or not the user is an admin
        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        clear_session(session)  # Clear session except for session_id and school

        try:
            # Make sure the user is logged in
            user_email = get_param_from_db('user_email', session_id)
            if user_email:
                if admin:
                    success, user = get_admin_from_email(user_email)
                    if success:
                        delete_admin_account(user_email)  # Delete the user associated with this email

                        delete_session_data(session_id)  # Delete the session
                        session.clear()  # Fully clear the session data
                        return 'success'
                    else:
                        return jsonify({"error_message": 'Fail'})  # If no user email found
                else:
                    success, user = get_user_from_email(user_email)
                    if success:
                        if user.subscription_status != "active" or user.email in premium_emails:
                            delete_account_email(user_email)  # Delete the user associated with this email

                            delete_session_data(session_id)  # Delete the session
                            session.clear()  # Fully clear the session data
                            return 'success'
                        else:
                            capture_message("User has active subscription, won't delete account", level="error")
                            return jsonify({"error_message": 'ActiveSubscription'})
                    else:
                        return jsonify({"error_message": 'Fail'})  # If no user email found
            else:
                capture_message("Attempted deletion of account not logged in", level="error")
                session['session_expired'] = True
                return jsonify({"error_message": 'Fail'})  # If no user email found, redirect to set session ID
        except Exception as e:
            capture_exception(e)
            return jsonify({"error_message": 'Fail'})

    @app.route('/api/notify_verification_not_received', methods=['POST'])
    @cross_origin()
    def notify_verification_not_received():
        try:
            user_email = request.json.get('email', None)
            notified_sent = send_verification_email_support(user_email)
            if notified_sent:
                return jsonify({"status": "success"})
            else:
                return jsonify({"status": "fail"})
        except Exception as e:
            capture_exception(e)
            return jsonify({"status": "fail"})

    @app.route('/api/notify_password_recovery_not_received', methods=['POST'])
    @cross_origin()
    def notify_password_recovery_not_received():
        try:
            user_email = request.json.get('email', None)
            notified_sent = send_password_recovery_email_support(user_email)
            if notified_sent:
                return jsonify({"status": "success"})
            else:
                return jsonify({"status": "fail"})
        except Exception as e:
            capture_exception(e)
            return jsonify({"status": "fail"})


    @app.route('/api/payment', methods=['GET', 'POST'])
    @cross_origin()
    def setup_payment():
        try:
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            school = session.get('school', 'rezify')
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return redirect(url_for('set_session_id', school=school))
            if request.method == 'POST':
                success, user = get_user_from_email(get_param_from_db('user_email', session_id))

                if not success:
                    session['session_expired'] = True  # To indicate that the session has expired
                    return jsonify({'client_secret': None})

                if user.plan == "premium":
                    # user already has premium, probably school user
                    return jsonify({'client_secret': None})

                if user.stripe_id is None:
                    register_stripe_user(user)

                stripe_success, client_secret = setup_checkout_session(user)

                if stripe_success:
                    return json.dumps({'client_secret': client_secret})
                else:
                    return json.dumps({'client_secret': None})
            elif request.method == 'GET':
                returnid = request.args.get('return_id')
                if returnid:
                    stripe_session = get_stripe_session(returnid)
                    if stripe_session:
                        return jsonify(status=stripe_session.status, customer_email=stripe_session.customer_details.email)
                    else:
                        return jsonify(status="DNE")
                else:
                    return 'Unused'

        except Exception as e:
            capture_exception(e)
            return 'Error'

    @app.route('/api/stripe_webhook', methods=['POST'])
    @cross_origin()
    def my_webhook_view():
        try:
            success, err_msg = handle_stripe_webhook(request=request)
            if success:
                return "Success", 200
            else:
                capture_message(err_msg, level="error")
                return "Error: " + err_msg, 400
        except Exception as e:
            capture_exception(e)
            return "Error", 400

    @app.route('/api/get_billing', methods=['POST'])
    @cross_origin()
    def get_billing():
        try:
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({"error_message": 'Fail'})

            clear_session(session)  # Clear session except for session_id and school

            success, user = get_user_from_email(get_param_from_db('user_email', session_id))

            if success:
                portal_success, redirect_url = create_billing_portal_for_user(user)
                if portal_success:
                    return json.dumps({"redirect": redirect_url})
                else:
                    return json.dumps({"error_message": redirect_url})
            else:
                return json.dumps({"error_message": "User not found"})
        except Exception as e:
            capture_exception(e)
            return json.dumps({"error_message": "An Unknown Error Occurred"})


## HELPER FUNCTIONS ##
def generate_verification_code():
    """
    Generates a 6-character alphanumeric verification code using
    uppercase letters and digits.
    """
    try:
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choices(characters, k=6))
    except Exception as e:
        capture_exception(e)
        return None
