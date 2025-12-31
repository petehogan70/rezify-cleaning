import errno
import json
import os
from datetime import datetime, timedelta
from flask import request, redirect, url_for, session
from flask_cors import cross_origin
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from sentry_sdk import capture_message, capture_exception

from backend.ai_generation import get_parsed_from_resume, get_experiences_from_resume
from backend.email_sending import send_demo_request_confirmation_failed_email_sendgrid, send_demo_request_confirmation_email_sendgrid, \
    send_demo_request_email_sendgrid
from backend.jobs import get_jobs
from backend.login import User, get_user_from_email, check_if_user_exists, \
    check_user_plan
from backend.monitoring import add_search_data
from backend.session_management import get_param_from_db, save_param_to_db, add_session, clear_session, \
    get_current_session_id_from_db, get_colors, is_locked_out, get_school_from_user
from backend.admin_login import check_if_admin_exists, get_admin_from_email

EXECUTOR = ThreadPoolExecutor(max_workers=4)

WEBSITE_ENDPOINT = os.getenv("WEBSITE_ENDPOINT", "https://rezify.ai")  # Default to rezify if not set

def _run_exp_parse_background(resume_path: str, session_id: str, resume_file):
    """
    Fire-and-forget wrapper. Opens its own DB/session context if needed.
    Do NOT use request/session globals in here.
    """
    try:
        exp_success, exp_time = get_experiences_from_resume(resume_path, session_id, resume_file)
        if not exp_success and WEBSITE_ENDPOINT.lower() == "https://rezify.ai":
            # best-effort notification; avoid touching Flask request context here
            email = None
            try:
                ri = get_param_from_db('resume_info', session_id)
                ri = json.loads(ri) if isinstance(ri, str) else (ri or {})
                email = (ri or {}).get('email')
            except Exception as e:
                capture_exception(e)
    except Exception as e:
        capture_exception(e)


def index_routes(app):
    @app.route('/api')
    @cross_origin()
    def set_session_id():
        """
        This is the first route that a user will go to when they visit the site. It will check to see if the user
        has a valid session (been on the site within the past 5 days).
        If they have a valid session and they were logged in post-search, it will redirect them to the results page.
        If they do not have a valid session, it will set a new session id and redirect them to the index page.
        If they have a valid session and they were not logged in or pre-search, it will redirect them to the index page.
        """

        try:

            session.permanent = True
            session_expired = session.get('session_expired', False)  # See if we came here from an expired session
            clear_session(session)  # Clear everything except session_id and school


            if 'session_id' in session:  # If there is a session id, this means this user has a valid session going
                u_email = get_param_from_db('user_email', session['session_id'])
                admin = get_param_from_db('admin', session['session_id'])

                if admin:

                    if u_email is not None and check_if_admin_exists(u_email):  # If the admin is logged in
                        success, admin_user = get_admin_from_email(get_param_from_db('user_email', session['session_id']))
                        if success:
                            session['school'] = admin_user.school_abbreviation
                            save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])
                            return json.dumps({'redirect_admin': True})
                else:
                    if u_email is not None and check_if_user_exists(u_email):  # If the user is logged in
                        # Set school based on email ending
                        success, user = get_user_from_email(get_param_from_db('user_email', session['session_id']))
                        if success:
                            session['school'] = get_school_from_user(user)
                            save_param_to_db('school', session.get('school', 'rezify'), session['session_id'])

                        if len(u_email) > 0 and len(user.get_user_list('applied_to')) > 0:
                            # If the user is already logged in and has job results, redirect to the results page
                            session['load'] = 'first'  # Set the load to first to load the entire page
                            session['login_refresh'] = True  # Refresh the results page after logging in
                            return redirect(url_for('results'))
                        else:
                            # If the user is already logged in but has no job results, redirect to the index page
                            return redirect(url_for('apiindex'))

            else:  # If there is no session id - meaning this user has not been on site in last 5 days
                unique_id = get_current_session_id_from_db(session)  # Use the cookie session id
                session['session_id'] = unique_id  # Set new session id if there is none at beginning

                session['session_expired'] = session_expired  # Pass the session expired variable to the so we can access it in index()
                return redirect(url_for('apiindex'))

            # If it hasn't returned yet, this means that the user has a valid recent session but either is not logged in
            # or has no job results. Redirect to the index page.


            clear_session(session)
            session['session_expired'] = session_expired  # Pass the session expired variable to the so we can access it in index()
            return redirect(url_for('apiindex'))

        except Exception as e:
            capture_exception(e)
            return redirect(url_for('apiindex'))


    @app.route('/api/index', methods=['GET', 'POST'])
    @cross_origin()
    def apiindex():
        """
            Handles the homepage of the website. If the user hits search, it handles the search and redirects to the
            results route.


            Returns:
            redirect_url(results): If the search is successful, it redirects to the results route.
            or
            render_template (str): The rendered HTML template for the homepage.
        """

        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        searches = session.get('searches', 0)
        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        session_expired = session.get('session_expired', False)  # Check if the session has expired
        colors = get_colors(session_id)  # Get the colors for the school theme
        clear_session(session)  # Clear session besides session_id and school

        try:

            add_session(session_id)  # Calling the add_session function to create a row in the database for the session.

            # Get the boolean of whether someone logged in or not. If there is a user email and the user exists, then the user is logged in.
            logged_in = get_param_from_db('user_email', session_id) is not None and check_if_user_exists(
                get_param_from_db('user_email', session_id))

            if logged_in:  # If the user is logged in, get their info
                email = get_param_from_db('user_email', session_id)
                success, user = get_user_from_email(email)
                check_user_plan(user)
            else:
                user = None

            if request.method == 'POST':  # If the search button is hit

                old_resume_info = get_param_from_db('resume_info', session_id)

                if old_resume_info['resume_file'] is not None and user and user.plan != "premium":
                    senddata = {
                        "user": user.to_dict() if (type(user) == User) else None,
                        "colors": colors,
                        "error_message": "Error: User does not have premium access to perform this"
                    }
                    return json.dumps(senddata)

                # Get the location, save it to 'filters' ------------------------------- LOCATION STUFF
                location = request.form.get('location', '').strip()

                if location == '':  # If the location is empty , set
                    location = None

                filters = get_param_from_db('filters', session_id)
                filters['location'] = location

                if location is not None:
                    # Get the specific location info including city and state
                    location_city = location[:location.index(',')]
                    location_state = location[location.index(',') + 2:]

                    # Get the miles (radius) and save it to 'filters'
                    miles = request.form.get('miles', 50)
                    filters['radius'] = miles
                else:
                    # Set the city and state to None, and set the miles to 50 if the location is empty
                    location_city = None
                    location_state = None
                    miles = 50

                save_param_to_db('filters', json.dumps(filters), session_id)

                # Get the resume and save the resume_info -------------------------------- RESUME STUFF
                resume_file = request.files['resume']  # The resume inputted

                if resume_file:
                    if is_locked_out(session_id):
                        senddata = {
                            "user": user.to_dict(include_school=True) if (type(user) == User) else None,
                            "colors": colors,
                            "error_message": 'Spam Searching Detected. Please wait a few hours and try again.'
                        }
                        return json.dumps(senddata)

                    resume_path = f"/tmp/{resume_file.filename}"

                    # Ensure the directory exists
                    if not os.path.exists(os.path.dirname(resume_path)):
                        try:
                            os.makedirs(os.path.dirname(resume_path))
                        except OSError as exc:
                            if exc.errno != errno.EEXIST:
                                raise

                    resume_file.save(resume_path)

                    resume_info = get_param_from_db('resume_info', session_id)

                    # Calling OpenAI API to parse the resume and save all the info
                    resume_parsed, resume_runtime = get_parsed_from_resume(resume_path)

                    # If there was an error parsing the resume, send error email and return user to index page with error message
                    if resume_parsed == 'Error' and resume_runtime == 0:
                        if WEBSITE_ENDPOINT.lower() == "https://rezify.ai":
                            capture_exception(Exception("ERROR: get_parsed_from_resume() failed"))  # Only send error email if in production

                        senddata = {
                            "user": user.to_dict(include_school=True) if (type(user) == User) else None,
                            "colors": colors,
                            "error_message": "Error with Parsing Resume"
                        }
                        return json.dumps(senddata)

                    # Updating the resume_info parameter with the new parsed resume info, save it to the sessions database
                    resume_info['resume_file'] = resume_file.filename
                    resume_info['intern_titles'] = resume_parsed.get('internships', [])
                    resume_info['first_name'] = resume_parsed.get('first name', '')
                    resume_info['last_name'] = resume_parsed.get('last name', '')
                    resume_info['email'] = resume_parsed.get('email', '')
                    resume_info['skills'] = resume_parsed.get('skills', [])
                    resume_info['reported_college'] = resume_parsed.get('reported_college', '')
                    save_param_to_db('resume_info', json.dumps(resume_info), session_id)

                    resume_info = get_param_from_db('resume_info', session_id)  # Get the updated resume info
                    intern_titles = resume_info.get('intern_titles', [])
                    skills = resume_info.get('skills', [])

                    # We have every thing we need, now search ------------------------------------- SEARCH

                    # Kick off background experience parsing (do NOT wait on it)
                    fut_exp = EXECUTOR.submit(_run_exp_parse_background, resume_path, session_id, resume_file)

                    # Run get_jobs concurrently and wait only for this result
                    fut_jobs = EXECUTOR.submit(get_jobs, intern_titles, skills, 'main')

                    try:
                        job_listings, runtimes_dict = fut_jobs.result(timeout=40)
                        runtimes_dict['Job 0: Parse Resume Time'] = resume_runtime
                        jobs_total_time = runtimes_dict['Total Time']
                        runtimes_dict['Total Time'] = resume_runtime + jobs_total_time
                    except TimeoutError:
                        # Optionally: try to cancel the job future; background exp keeps running
                        fut_jobs.cancel()
                        capture_message("ERROR: Search took too long", level="error")
                        return json.dumps({
                            "user": user.to_dict(include_school=True) if (type(user) == User) else None,
                            "colors": colors,
                            "error_message": "Search took too long. Please try again."
                        })
                    except Exception as e:
                        capture_exception(e)
                        return json.dumps({
                            "user": user.to_dict(include_school=True) if (type(user) == User) else None,
                            "colors": colors,
                            "error_message": "Error loading jobs. Please try again."
                        })

                    if os.getenv("WEBSITE_ENDPOINT").lower() == "https://rezify.ai":
                        session['searches'] = searches + 1  # Increment searches count
                    if searches > 100:
                        # If the failed exceeds 75, lock the user out for 2 hours
                        save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                        clear_session(session)  # To set searches back to 0
                        session['searches'] = 0

                    # If there was an error getting the jobs, send error email and return user to index page with error message
                    if job_listings == 'Error':
                        capture_message("ERROR: Error loading jobs from get_jobs()", level="error")
                        senddata = {
                            "user": user.to_dict(include_school=True) if (type(user) == User) else None,
                            "colors": colors,
                            "error_message": 'Error loading jobs. Please try again.'
                        }
                        return json.dumps(senddata)

                    total_runtime = jobs_total_time + resume_runtime

                    if logged_in:
                        search_email = user.email
                    else:
                        search_email = resume_info.get('email', '')

                    # Adding to search data if it comes from production site
                    if WEBSITE_ENDPOINT.lower() == "https://rezify.ai":
                        safe_email = search_email.replace('@', '[@]').replace('.', '[.]')
                        if total_runtime > 25:
                            capture_message(f"WARNING: Search algorithm took more than 25 seconds for email ({safe_email})", level="warning")
                        elif total_runtime > 30:
                            capture_exception(Exception(f'ERROR: Search algorithm took more than 30 seconds for email ({safe_email})'))
                        add_search_data(total_runtime, 'homepage', search_email, runtimes_dict)


                    if logged_in:
                        # Update the user's job listings if they re-search while logged in
                        user.update_user_param('internships_list', job_listings)
                        user.update_user_param('filters', get_param_from_db('filters', session_id))
                        user.update_user_param('last_refresh', datetime.now())
                        user.update_user_param('resume_file', resume_info.get('resume_file', ''))
                        user.update_user_param('intern_titles', resume_info.get('intern_titles', []))
                        user.update_user_param('skills', resume_info.get('skills', []))

                    # Store the job listings in the session
                    save_param_to_db('jobs_list', json.dumps(job_listings), session_id)

                    # redirect the user to the results page
                    session['segments'] = 1
                    session['load'] = 'first'
                    safe_email = search_email.replace('@', '[@]').replace('.', '[.]')
                    capture_message(f"SEARCH SUCCESS: {len(job_listings)} jobs, {round(total_runtime, 2)} seconds, For email: {safe_email}")
                    return json.dumps({'redirect': '/results'})

            if session_expired:
                error_message = "Session expired. Please log in again."
            else:
                error_message = None

            old_resume_info = get_param_from_db('resume_info', session_id)

            senddata = {
                "user": user.to_dict() if (type(user) == User) else None,
                "should_redirect": (user and user.resume_file is not None),
                "colors": colors,
                "school": school,
                "error_message": error_message
            }
            return json.dumps(senddata)

        except Exception as e:
            capture_exception(e)
            senddata = {
                "colors": colors,
                "school": school,
                "error_message": "An Unknown Error Occured"
            }
            return json.dumps(senddata)



    @app.route('/api/request_demo', methods=['POST'])
    @cross_origin()
    def request_demo():
        try:
            form = request.form
            demo_request_sent = send_demo_request_email_sendgrid(form)
            demo_request_confirmation_sent = False
            if demo_request_sent:
                # Confirm demo request with requester
                demo_request_confirmation_sent = send_demo_request_confirmation_email_sendgrid(form)
                if not demo_request_confirmation_sent:
                    # Notify support if unable to send confirmation email to requester
                    send_demo_request_confirmation_failed_email_sendgrid(form)
            return json.dumps({'demo_request_sent': demo_request_sent, 'demo_request_confirmation_sent': demo_request_confirmation_sent})
        except Exception as e:
            capture_exception(e)