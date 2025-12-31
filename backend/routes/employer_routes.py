from datetime import datetime

from flask import render_template, request, redirect, url_for, jsonify, session
from flask_cors import cross_origin

from backend.employer import Employer, employer_login, get_employer_from_email
from backend.session_management import get_param_from_db, save_param_to_db
from backend.database_config import Session


def employer_routes(app):
    """
    This function sets up the routes for the employer-related functionalities in the Rezify application.
    It includes routes for employer registration, login, dashboard, job posting, and job deletion.
    """
    @app.route('/api/employer_register', methods=['GET', 'POST'])
    @cross_origin()
    def employer_register():
        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        if request.method == 'POST':
            try:
                company_name = request.form['company_name']
                email = request.form['email']
                password = request.form['password']
                location = request.form['location']
                description = request.form['description']
                industry = request.form['industry']

                contact_person = request.form['contact_person']
                contact_number = request.form['contact_number']
                contact_email = request.form['contact_email']

                page_link = request.form['page_link']
                linkedin_page = request.form['linkedin_page']
                logo_link = request.form['logo_link']

                employer = Employer(company_name, logo_link, page_link, linkedin_page, industry, description, location,
                                    email, password, contact_person, contact_number, contact_email)
                message = employer.create_new_employer()

                if 'successfully' in message:
                    save_param_to_db('logged_in', True, session_id)
                    save_param_to_db('user_email', email, session_id)
                    save_param_to_db('first_name', company_name, session_id)
                    return redirect(url_for('employer_dashboard'))

                return render_template('employer_registration.html', error_message=message)

            except Exception as e:
                return render_template('employer_registration.html',
                                       error_message='An error occurred during registration, please try again')

        return render_template('employer_registration.html')


    # EMPLOYER LOGIN PAGE
    @app.route('/api/employer_login', methods=['GET', 'POST'])
    @cross_origin()
    def employer_login_page():
        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        if request.method == 'POST':
            try:
                # Get the login credentials entered and try it
                email = request.form['email']
                password = request.form['password']
                success, employer = employer_login(email, password)

                if success:  # If log in worked
                    save_param_to_db('logged_in', True, session_id)
                    save_param_to_db('user_email', employer.email, session_id)

                    return redirect(
                        url_for('employer_dashboard'))  # Redirect to the employer dashboard

                else:  # If the login didn't work
                    return render_template('employer_login.html', error_message='Invalid Credentials')
            except Exception as e:
                return render_template('employer_login.html',
                                       error_message='An error occurred during login, please try again')
        return render_template('employer_login.html')

    # Employer dashboard
    @app.route('/employer_dashboard', methods=['GET', 'POST'])
    @cross_origin()
    def employer_dashboard():
        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        employer_email = get_param_from_db('user_email', session_id)
        if not employer_email:
            return redirect(url_for('employer_login'))

        employer = get_employer_from_email(employer_email)
        job_postings = employer.get_employee_parameter('job_postings')
        return render_template('employer_dashboard.html', employer=employer, job_listings=job_postings)

    # Employer job posting
    @app.route('/api/post_job', methods=['GET', 'POST'])
    @cross_origin()
    def post_job():
        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            requirements = request.form['requirements']
            location = request.form['location']
            pay = request.form['pay']
            url = request.form['url']
            remote = 'remote' in request.form
            visa_sponsorship = 'visa_sponsorship' in request.form

            employer_email = get_param_from_db('user_email', session_id)
            if not employer_email:
                return redirect(url_for('employer_login'))

            this_session = Session
            location_city = location[:location.index(',')]
            location_state = location[-2:]
            description = description + " \n" + requirements
            date = datetime.now().strftime("%Y-%m-%d")
            employer = get_employer_from_email(employer_email)
            result = employer.add_job_posting(title, location_city, location_state, remote, pay, date, url, description)
            this_session.remove()

            return redirect(url_for('employer_dashboard'))

        return render_template('post_job.html')

    # Delete employer job posting
    @app.route('/api/delete_employer_job', methods=['POST'])
    @cross_origin()
    def delete_employer_job():
        session_id = session.get('session_id', None)  # Get the unique session ID from the session
        school = session.get('school', 'rezify')
        if session_id is None:
            # If there is no session id, send back to the beginning and set a new one
            session['session_expired'] = True  # To indicate that the session has expired
            return redirect(url_for('set_session_id', school=school))

        if get_param_from_db('logged_in', session_id):
            user_email = get_param_from_db('user_email', session_id)
            job_id = request.json.get("job_id")
            if job_id:
                employer = get_employer_from_email(user_email)
                employer_jobs = employer.get_employee_parameter('job_postings')
                job = next((job for job in employer_jobs if job['id'] == int(job_id)), None)
                if job:
                    result = employer.delete_job_posting(int(job_id))
                    if result:
                        return jsonify({'status': 'success'})
                    else:
                        return jsonify({'status': 'fail'})
                else:
                    return jsonify({'status': 'fail'})
            return jsonify({'status': 'error', 'message': 'Invalid job data'}), 400
        return jsonify({'status': 'error'}), 401