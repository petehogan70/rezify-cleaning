import json
import time
from sentry_sdk import capture_exception, capture_message

from flask import redirect, url_for, session, request, jsonify
from flask_cors import cross_origin

from backend.admin_login import AdminUser, get_admin_from_email, check_if_admin_exists
from backend.session_management import get_param_from_db, clear_session, \
    get_colors
from backend.university_admin_stats import get_admin_data
from backend.login import get_user_from_email
from backend.superadmin import get_super_admin_users_data, get_super_admin_jobs_data, delete_job_from_removed_list, \
    get_super_admin_usage_data, get_super_admin_openai_data
from backend.jobs import delete_job_from_database


def admin_routes(app):
    @app.route('/api/get_admin', methods=['GET'])
    @cross_origin()
    def get_admin():
        """
            Returns admin
        """

        try:

            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            school = session.get('school', 'rezify')
            change = session.get('change')
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return redirect(url_for('set_session_id', school=school))

            session_expired = session.get('session_expired', False)  # Check if the session has expired
            colors = get_colors(session_id)  # Get the colors for the school theme
            clear_session(session)  # Clear session besides session_id and school

            # Get the boolean of whether someone logged in or not. If there is a user email and the user exists, then the user is logged in.
            admin_logged_in = get_param_from_db('admin', session_id) and get_param_from_db('user_email',
                                                                                           session_id) is not None and check_if_admin_exists(
                get_param_from_db('user_email', session_id))

            if admin_logged_in:  # If the user is logged in, get their info
                admin_email = get_param_from_db('user_email', session_id)
                success, admin = get_admin_from_email(admin_email)
            else:
                admin = None

            if session_expired:
                error_message = "Session expired. Please log in again."
            else:
                error_message = None

            senddata = {
                "admin": admin.to_dict() if (type(admin) == AdminUser) else None,
                "colors": colors,
                "school": school,
                "error_message": error_message,
                "change": change
            }

            return json.dumps(senddata)

        except Exception as e:
            capture_exception(e)
            return json.dumps({
                "admin": None,
                "colors": None,
                "school": None,
                "error_message": "An error occurred while processing your request.",
                "change": None
            })

    @app.route('/api/admin', methods=['GET'])
    @cross_origin()
    def admin_stats():
        """
            Returns admin stats
        """

        try:

            start_time = time.time()

            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            school = session.get('school', 'rezify')
            change = session.get('change')
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return redirect(url_for('set_session_id', school=school))

            session_expired = session.get('session_expired', False)  # Check if the session has expired
            colors = get_colors(session_id)  # Get the colors for the school theme
            clear_session(session)  # Clear session besides session_id and school

            # Get the boolean of whether someone logged in or not. If there is a user email and the user exists, then the user is logged in.
            admin_logged_in = get_param_from_db('admin', session_id) and get_param_from_db('user_email', session_id) is not None and check_if_admin_exists(
                get_param_from_db('user_email', session_id))

            if admin_logged_in:  # If the user is logged in, get their info
                admin_email = get_param_from_db('user_email', session_id)
                success, admin = get_admin_from_email(admin_email)
            else:
                admin = None

            if session_expired:
                error_message = "Session expired. Please log in again."
            else:
                error_message = None

            senddata = {
                "admin": admin.to_dict() if (type(admin) == AdminUser) else None,
                "stats": get_admin_data(admin.school_abbreviation) if (type(admin) == AdminUser) else None,
                "colors": colors,
                "school": school,
                "error_message": error_message,
                "change": change
            }

            total_time = time.time() - start_time

            # Log a success
            if admin and senddata.get('error_message') is None:
                capture_message(f"Admin Stats Loading Time: {round(total_time, 2)}, for school: {admin.school_abbreviation}", level="info")

            return json.dumps(senddata)

        except Exception as e:
            capture_exception(e)
            return json.dumps({
                "admin": None,
                "stats": None,
                "colors": None,
                "school": None,
                "error_message": "An error occurred while processing your request.",
                "change": None
            })

    @app.route('/api/get_user_from_admin', methods=['GET', 'POST'])
    @cross_origin()
    def get_user_from_admin():
        """
            Returns necessary user info for admin dashboard in student view
        """
        start_time = time.time()

        data = request.get_json()  # Parse JSON body
        email = data.get("email")

        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        colors = get_colors(session_id)  # Get the colors for the school theme
        clear_session(session)  # Clear session besides session_id and school

        try:

            # Get the boolean of whether someone logged in or not. If there is a user email and the user exists, then the user is logged in.
            admin_logged_in = get_param_from_db('admin', session_id) and get_param_from_db('user_email',
                                                                                           session_id) is not None and check_if_admin_exists(
                get_param_from_db('user_email', session_id))

            if not admin_logged_in:
                return json.dumps({
                    "user": None,
                    "colors": colors,
                    "error_message": "Not logged in as admin."
                })
            else:
                admin_email = get_param_from_db('user_email', session_id)

            success, user = get_user_from_email(email)
            if not success:
                return json.dumps({
                    "user": None,
                    "colors": colors,
                    "error_message": "User Not Found"
                })

            user_dict = user.to_dict()

            nec_fields = ["email", "first_name", "last_name", "favorites", "applied_to"]
            filtered_user = {field: user_dict.get(field) for field in nec_fields}

            total_time = time.time() - start_time

            capture_message(f"Admin Loaded User. Time: {round(total_time, 2)} for school: {admin_email}", level="info")

            return json.dumps({
                "user": filtered_user,
                "colors": colors,
                "error_message": None
            })

        except Exception as e:
            capture_exception(e)
            return json.dumps({
                "user": None,
                "colors": colors,
                "error_message": "Unknown Error"
            })

    @app.route('/api/get_superadmin_users_stats', methods=['GET'])
    @cross_origin()
    def get_superadmin_users_stats():
        """
        Gets the user stats for the rezify super admin dashboard

        :return:
        """

        try:

            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            school = session.get('school', 'rezify')
            change = session.get('change')
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return redirect(url_for('set_session_id', school=school))

            session_expired = session.get('session_expired', False)  # Check if the session has expired
            colors = get_colors(session_id)  # Get the colors for the school theme
            clear_session(session)  # Clear session besides session_id and school

            # Get the boolean of whether someone logged in or not. If there is a user email and the user exists, then the user is logged in.
            admin_logged_in = get_param_from_db('admin', session_id) and get_param_from_db('user_email', session_id) is not None and check_if_admin_exists(
                get_param_from_db('user_email', session_id))

            if admin_logged_in:  # If the user is logged in, get their info
                admin_email = get_param_from_db('user_email', session_id)
                success, admin = get_admin_from_email(admin_email)
                if admin.school_abbreviation != "rezifyadmin":  # If the admin is not a rezify superadmin
                    admin = None
            else:
                admin = None

            if session_expired:
                error_message = "Session expired. Please log in again."
            else:
                error_message = None

            senddata = {
                "admin": admin.to_dict() if (type(admin) == AdminUser) else None,
                "stats": get_super_admin_users_data() if (type(admin) == AdminUser) else None,
                "colors": colors,
                "school": school,
                "error_message": error_message,
                "change": change
            }

            return json.dumps(senddata)

        except Exception as e:
            capture_exception(e)
            return json.dumps({
                "admin": None,
                "stats": None,
                "colors": None,
                "school": None,
                "error_message": "An error occurred while processing your request.",
                "change": None
            })

    @app.route('/api/get_superadmin_jobs_stats', methods=['GET'])
    @cross_origin()
    def get_superadmin_jobs_stats():
        """
        Gets the jobs stats for the rezify super admin dashboard

        :return:
        """

        try:

            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            school = session.get('school', 'rezify')
            change = session.get('change')
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return redirect(url_for('set_session_id', school=school))

            session_expired = session.get('session_expired', False)  # Check if the session has expired
            colors = get_colors(session_id)  # Get the colors for the school theme
            clear_session(session)  # Clear session besides session_id and school

            # Get the boolean of whether someone logged in or not. If there is a user email and the user exists, then the user is logged in.
            admin_logged_in = get_param_from_db('admin', session_id) and get_param_from_db('user_email',
                                                                                           session_id) is not None and check_if_admin_exists(
                get_param_from_db('user_email', session_id))

            if admin_logged_in:  # If the user is logged in, get their info
                admin_email = get_param_from_db('user_email', session_id)
                success, admin = get_admin_from_email(admin_email)
                if admin.school_abbreviation != "rezifyadmin":  # If the admin is not a rezify superadmin
                    admin = None
            else:
                admin = None

            if session_expired:
                error_message = "Session expired. Please log in again."
            else:
                error_message = None

            senddata = {
                "admin": admin.to_dict() if (type(admin) == AdminUser) else None,
                "stats": get_super_admin_jobs_data() if (type(admin) == AdminUser) else None,
                "colors": colors,
                "school": school,
                "error_message": error_message,
                "change": change
            }

            return json.dumps(senddata)

        except Exception as e:
            capture_exception(e)
            return json.dumps({
                "admin": None,
                "stats": None,
                "colors": None,
                "school": None,
                "error_message": "An error occurred while processing your request.",
                "change": None
            })

    @app.route('/api/admin_remove_job', methods=['POST'])
    @cross_origin()
    def admin_remove_job():
        """
        This function handles the admin reviewing a job put in the removed_jobs_global list. When this is triggered,
        the job will be removed from the database and the list
        """

        try:
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

            clear_session(session)  # Clear session except for session_id and school

            job_id = request.json.get("job_id")  # Get the job id from the request

            delete_job_from_removed_list(job_id)
            delete_job_from_database(job_id)

            return jsonify({'status': 'success'})

        except Exception as e:
            capture_exception(e)
            return jsonify({'status': 'error', 'message': 'An Unknown Error Occurred'}), 400

    @app.route('/api/admin_job_good', methods=['POST'])
    @cross_origin()
    def admin_job_good():
        """
        This function handles the admin reviewing a job in the removed_jobs_global list, and determining that it is valid.
        The job will be removed from the list, but not the databse
        """

        try:
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

            clear_session(session)  # Clear session except for session_id and school

            job_id = request.json.get("job_id")  # Get the job id from the request

            delete_job_from_removed_list(job_id)

            return jsonify({'status': 'success'})

        except Exception as e:
            capture_exception(e)
            return jsonify({'status': 'error', 'message': 'An Unknown Error Occurred'}), 400

    @app.route('/api/get_superadmin_usage_stats', methods=['GET'])
    @cross_origin()
    def get_superadmin_usage_stats():
        """
        Gets the usage stats for the rezify super admin dashboard

        :return:
        """

        try:

            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            school = session.get('school', 'rezify')
            change = session.get('change')
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return redirect(url_for('set_session_id', school=school))

            session_expired = session.get('session_expired', False)  # Check if the session has expired
            colors = get_colors(session_id)  # Get the colors for the school theme
            clear_session(session)  # Clear session besides session_id and school

            # Get the boolean of whether someone logged in or not. If there is a user email and the user exists, then the user is logged in.
            admin_logged_in = get_param_from_db('admin', session_id) and get_param_from_db('user_email',
                                                                                           session_id) is not None and check_if_admin_exists(
                get_param_from_db('user_email', session_id))

            if admin_logged_in:  # If the user is logged in, get their info
                admin_email = get_param_from_db('user_email', session_id)
                success, admin = get_admin_from_email(admin_email)
                if admin.school_abbreviation != "rezifyadmin":  # If the admin is not a rezify superadmin
                    admin = None
            else:
                admin = None

            if session_expired:
                error_message = "Session expired. Please log in again."
            else:
                error_message = None

            senddata = {
                "admin": admin.to_dict() if (type(admin) == AdminUser) else None,
                "stats": get_super_admin_usage_data() if (type(admin) == AdminUser) else None,
                "colors": colors,
                "school": school,
                "error_message": error_message,
                "change": change
            }

            return json.dumps(senddata)

        except Exception as e:
            capture_exception(e)
            return json.dumps({
                "admin": None,
                "stats": None,
                "colors": None,
                "school": None,
                "error_message": "An error occurred while processing your request.",
                "change": None
            })

    @app.route('/api/get_superadmin_openai_stats', methods=['GET'])
    @cross_origin()
    def get_superadmin_openai_stats():
        """
        Gets the openai api stats for the rezify super admin dashboard

        :return:
        """

        try:

            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            school = session.get('school', 'rezify')
            change = session.get('change')
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return redirect(url_for('set_session_id', school=school))

            session_expired = session.get('session_expired', False)  # Check if the session has expired
            colors = get_colors(session_id)  # Get the colors for the school theme
            clear_session(session)  # Clear session besides session_id and school

            # Get the boolean of whether someone logged in or not. If there is a user email and the user exists, then the user is logged in.
            admin_logged_in = get_param_from_db('admin', session_id) and get_param_from_db('user_email',
                                                                                           session_id) is not None and check_if_admin_exists(
                get_param_from_db('user_email', session_id))

            if admin_logged_in:  # If the user is logged in, get their info
                admin_email = get_param_from_db('user_email', session_id)
                success, admin = get_admin_from_email(admin_email)
                if admin.school_abbreviation != "rezifyadmin":  # If the admin is not a rezify superadmin
                    admin = None
            else:
                admin = None

            if session_expired:
                error_message = "Session expired. Please log in again."
            else:
                error_message = None

            senddata = {
                "admin": admin.to_dict() if (type(admin) == AdminUser) else None,
                "stats": get_super_admin_openai_data() if (type(admin) == AdminUser) else None,
                "colors": colors,
                "school": school,
                "error_message": error_message,
                "change": change
            }

            return json.dumps(senddata)

        except Exception as e:
            capture_exception(e)
            return json.dumps({
                "admin": None,
                "stats": None,
                "colors": None,
                "school": None,
                "error_message": "An error occurred while processing your request.",
                "change": None
            })


