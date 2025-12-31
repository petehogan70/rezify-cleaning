import json
import os
from datetime import datetime, timedelta, timezone

import markdown
import pandas as pd
from flask import request, redirect, url_for, jsonify, session
from flask_cors import cross_origin
from sentry_sdk import capture_exception, capture_message

from backend.jobs import get_jobs, remove_job_rec, sort_job_listings_by_date, \
    filter_by_location, get_job_from_id, add_removed_job_global, get_raw_description, get_job_description
from backend.login import User, get_user_from_email, check_if_job_in, check_user_plan
from backend.monitoring import add_search_data, increment_linkedin_clicks
from backend.session_management import get_param_from_db, save_param_to_db, clear_session, \
    get_colors, is_locked_out

WEBSITE_ENDPOINT = os.getenv("WEBSITE_ENDPOINT", "https://rezify.ai")  # Default to rezify if not set

BASE_DIR = os.path.dirname(__file__)

cities_df = pd.read_csv(os.path.join(BASE_DIR, "..", "uscities.csv")) # Load cities data from CSV file

def results_routes(app):

    @app.route('/api/get_description/<int:job_id>')
    @cross_origin()
    def get_description(job_id):
        """
            Fetches the job description from the database and returns it in HTML format.
            Simply calls the get_job_description function from the jobs.py file.

            Parameters:
            job_id (int): The unique identifier of the job.

            Returns:
            JSON response with the following keys:
            - 'status': 'success' if the description is found, 'fail' if not found, or 'error' if an error occurred.
            - 'html': The job description in HTML format if found, or an error message if not found or an error occurred.
        """
        return get_job_description(job_id)


    @app.route('/api/update_filters')
    @cross_origin()
    def update_filters():
        """
            Updates the user's filter settings based on the provided parameter to update with teh new value

            Returns:
            Redirects to the 'results' page with the updated filter settings.
        """
        try:
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            searches = session.get('searches', 0)
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({"error_message": 'Fail'})

            clear_session(session) # Clear session except for session_id and school

            parameter = request.args.get('parameter')  # Which filter to update
            value = request.args.get('value')  # The value to update the filter with

            success, user = get_user_from_email(get_param_from_db('user_email', session_id))

            if success:
                filters = user.filters

                if parameter == 'filter_box':  # If the 'Apply Filters' button is clicked, update the filters from teh filters box
                    # The value is a JSON string representing the filter box's state
                    value = json.loads(value)

                    filters['type'] = value['type']  # Update the type filter (In-person, Remote, or Both)

                    filters['international_only'] = value['international_only']  # Update the value of the international only filter

                    filters['location'] = value['location']  # Update the location filter (string)

                    filters['radius'] = int(value['radius'])  # Update the radius filter (int)

                    filters['selected_industries'] = value['selected_industries']  # Update the selected industries filter (list)

                elif parameter == 'sort_by':  # Update the sort by filter (Relevance or Date)
                    #if user.plan != "premium":
                    #        return 'Fail'
                    filters['sort_by'] = value

                elif parameter == 'title_filters':  # Update the selected title filters from the top of the page
                    new_title = value  # The selected title (either selected or unselected)

                    if new_title in filters['selected_titles']:  # If the title is already selected, remove it
                        filters['selected_titles'].remove(new_title)
                    else:  # If the title is not selected, add it
                        filters['selected_titles'].append(new_title)

                elif parameter == 'user_filter':  # Update the selected user filter (Applied to, Favorites, or All)
                    if user.plan != "premium":
                            return jsonify({"error_message": 'Fail'})
                    filters['selected_filter'] = value

                elif parameter == 'add_title':  # Add a new job title from the user's custom input
                    if user.plan != "premium":
                            return jsonify({"error_message": 'Fail'})
                    added_title = value

                    job_titles = user.intern_titles  # Get the user's current job titles

                    if added_title not in user.intern_titles:
                        if is_locked_out(session_id):  # If the user is locked out, return to results with error
                            session['load'] = 'first'
                            session['limit_error'] = True
                            session['segments'] = 1
                            return redirect(url_for('results'))


                        # Add the new title to the user's list of job titles
                        job_titles.append(added_title)
                        user.update_user_param('intern_titles', job_titles)

                        # Call the get_jobs function including the new title
                        job_listings, runtimes_dict = get_jobs(job_titles, user.skills, 'add_title')

                        if os.getenv("WEBSITE_ENDPOINT").lower() == "https://rezify.ai":
                            session['searches'] = searches + 1  # Increment searches count
                        if searches > 100:
                            # If the failed exceeds 75, lock the user out for 2 hours
                            save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                            clear_session(session)  # To set searches back to 0
                            session['searches'] = 0

                        # If there was an error getting the jobs, send error email and return the previous results page with
                        # error message
                        if job_listings == 'Error':
                            capture_message('ERROR: Error in get_jobs()', level="error")

                            session['load'] = 'first'
                            session['get_jobs_error'] = True
                            session['segments'] = 1
                            return redirect(url_for('results'))

                        # If the search was from the production site, add to search data
                        if WEBSITE_ENDPOINT.lower() == "https://rezify.ai":
                            total_time = runtimes_dict['Total Time']
                            add_search_data(total_time, 'add_title', user.email, runtimes_dict)

                        user.update_user_param('internships_list', job_listings)  # Update the user's job listings in the database

                        user.update_user_param('last_refresh', datetime.now())

                elif parameter == 'remove_title':  # Remove a job title from the user's list of job titles
                    if user.plan != "premium":
                            return jsonify({"error_message": 'Fail'})
                    # Get the job listings of the user (jobs not in applied_to)
                    applied_job_ids = {job['id'] for job in user.get_user_list('applied_to')}
                    job_listings = [job for job in user.get_user_list('internships_list') if job['id'] not in applied_job_ids]

                    filters = user.filters  # Get the user's current filters
                    removed_title = value  # The search title to be removed

                    if value in user.filters['selected_titles']:  # Remove the title from the selected titles filter
                        filters['selected_titles'].remove(value)
                        user.update_user_param('filters', filters)

                    # Call the remove_job_rec function to remove the jobs of the selected title to removed
                    job_listings = remove_job_rec(job_listings, removed_title)
                    user.update_user_param('internships_list', job_listings)
                    job_titles = user.intern_titles
                    if removed_title in job_titles:
                        job_titles.remove(removed_title)
                    else:
                        capture_message(f'WARNING: trying to remove title: {removed_title} from titles: {user.intern_titles}', level="warning")
                    user.update_user_param('intern_titles', job_titles)

                user.update_user_param('filters', filters)  # Update the user's filters in the database

                return redirect(url_for('results'))

            else:  # If the login failed
                session['session_expired'] = True  # To indicate that the account session has expired
                return jsonify({"error_message": 'Fail'})

        except Exception as e:
            capture_exception(e)
            return jsonify({"error_message": 'Unknown Error'})


    @app.route('/api/results', methods=['GET', 'POST'])
    @cross_origin()
    def results():
        """
            This function handles the results page of the application. It retrieves the user's session ID,
            login refresh status, and user data. If it is the first time loading the results page, it will render the
            entire results page. Otherwise, it will just update the filters and job cards sections of the page.

            Returns:
            render_template: If the page is being loaded for the first time, it renders the results page with the appropriate data.
            jsonify: If the page is being loaded for subsequent segments, it returns JSON data for the job cards and filters.
        """
        try:
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            school = session.get('school', 'rezify')
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return redirect(url_for('set_session_id', school=school))

            login_refresh = session.get('login_refresh', False)  # Will be True if it is an auto refresh after logging in
            change = session.get('change', None)  # If the user elected to change their password
            load = session.get('load', 'reload')  # If the page is being loaded or being reloaded
            resume_error = session.get('resume_error', None)  # If there was an error parsing the resume
            get_jobs_error = session.get('get_jobs_error', None)  # If there was an error in the get_jobs() function
            limit_error = session.get('limit_error', None)  # If the user has exceeded their search limit
            colors = get_colors(session_id)  # Get the colors for the school theme
            clear_session(session)  # Clear session except for session_id and school

            success, user = get_user_from_email(get_param_from_db('user_email', session_id))

            if success:
                check_user_plan(user)
                # Run the jobs from the session id through the filter_jobs function to get the filtered job listings
                jobs, segments, per_segment, total_jobs, distinct_titles, distinct_industries = filter_jobs(session_id)
                if user.plan != "premium" and user.last_refresh == None:
                    user.update_user_param('last_refresh', datetime.now())

                if user.plan != "premium":  # Basic plan limit
                    jobs = jobs[0:25]

                if load == 'first':  # If it is the first time loading the results page, render the entire page

                    if jobs == 'Fail':
                        session['session_expired'] = True
                        return redirect(url_for('set_session_id', school=school))

                    return json.dumps({'should_redirect': True, 'jobs': jobs, 'segments': segments,
                                       'per_segment': per_segment, 'change': change, 'login_refresh': login_refresh,
                                       'total_jobs': total_jobs, 'distinct_titles': distinct_titles, 'limit_error': limit_error,
                                       'distinct_industries': distinct_industries, 'get_jobs_error': get_jobs_error,
                                       'user': user.to_dict(include_school=True) if (type(user) == User) else None,
                                       'resume_error': resume_error, 'colors': colors})
                else:
                    # Just load the filters and job cards sections of the page
                    if jobs == 'Fail':
                        session['session_expired'] = True
                        return jsonify({"error_message": 'Fail'})

                    return json.dumps({'should_redirect': True, 'jobs': jobs, 'segments': segments,
                                       'per_segment': per_segment, 'change': change, 'login_refresh': login_refresh,
                                       'total_jobs': total_jobs, 'distinct_titles': distinct_titles, 'limit_error': limit_error,
                                       'distinct_industries': distinct_industries, 'get_jobs_error': get_jobs_error,
                                       'user': user.to_dict(include_school=True) if (type(user) == User) else None,
                                       'resume_error': resume_error, 'colors': colors})

            else:  # If the login failed, then it means it is coming from the homepage and needs to register
                user = None

                # Get the jobs and the filters
                job_listings = get_param_from_db('jobs_list', session_id)
                filters = get_param_from_db('filters', session_id)

                # if there is a location entered, filter the jobs by their location
                if filters and filters['location'] is not None and filters['location'] != '':
                    location = filters['location']
                    radius = filters['radius']
                    location_city = location[:location.index(',')]
                    location_state = location[location.index(',') + 2:]
                    job_listings = filter_by_location(job_listings, cities_df, location_city, location_state, radius)

                # Limit the job_listings to at most 300 items
                job_listings = job_listings[:300]
                total_jobs = len(job_listings)
                job_listings_segmented = job_listings[0:2]

                # Get the distinct job titles and industries to pass to the front-end
                distinct_titles = list(set(job['job_rec'] for job in job_listings))
                distinct_industries = list(set(
                    job['company_industry'] for job in job_listings if job['company_industry'] is not None))

                # Get the resume info which was parsed
                resume_info = get_param_from_db('resume_info', session_id)

                # if load == 'first':  # Render the entire results page as the first load
                return json.dumps({'should_redirect': True, 'jobs': job_listings_segmented, 'segments': 1,
                                   'per_segment': 2, 'change': None, 'login_refresh': False,
                                   'total_jobs': total_jobs, 'distinct_titles': distinct_titles, 'limit_error': limit_error,
                                   'distinct_industries': distinct_industries, 'get_jobs_error': get_jobs_error,
                                   'user': user.to_dict(include_school=True) if (type(user) == User) else None,
                                   'resume_error': resume_error, 'colors': colors})

        except Exception as e:
            capture_exception(e)
            return jsonify({"error_message": 'Fail'})


    @app.route('/api/load_more')
    @cross_origin()
    def load_more():
        """
            This function handles the loading of more job cards on the results page.

            Returns:
            render_template: A rendered HTML template containing the job cards for the next segment.
        """
        try:
            # Get the jobs listings of the associated session
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({"error_message": 'Fail'})

            segments = int(request.args.get('segments', 1))  # Get the number of segments from the session
            clear_session(session)  # Clear session except for session_id and school

            job_listings = get_param_from_db('jobs_list', session_id)
            total_jobs = len(job_listings)

            success, user = get_user_from_email(get_param_from_db('user_email', session_id))

            if not success:
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({"error_message": 'Fail'})

            if user.plan == "basic":  # Basic plan limit
                return jsonify({"error_message": 'Fail'})

            # Segments the jobs
            per_segment = 25
            job_listings_segmented = job_listings[0:segments * per_segment]

            return json.dumps({'segments': segments, 'per_segment': per_segment,
                               'jobs': job_listings_segmented, 'total_jobs': total_jobs})
        except Exception as e:
            capture_exception(e)
            return jsonify({"error_message": 'Fail'})


    @app.route('/api/refresh_jobs')
    @cross_origin()
    def refresh_jobs():
        """
            This function handles the refreshing of job cards on the results page.

            Returns:
            render_template: The updated job cards section of the results page.
        """
        try:
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            searches = session.get('searches', 0)  # Get the number of searches from the session
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({"error_message": 'Fail'})

            clear_session(session)  # Clear session except for session_id and school

            if is_locked_out(session_id):
                session['load'] = 'reload'
                session['limit_error'] = True
                session['segments'] = 1
                return redirect(url_for('results'))

            success, user = get_user_from_email(get_param_from_db('user_email', session_id))

            if not success:
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({"error_message": 'Fail'})

            if user.plan != "premium" and user.last_refresh is None:
                user.update_user_param('last_refresh', datetime.now())

            next_refresh = user.last_refresh + timedelta(days=7)
            if user.plan != "premium" and (datetime.now() < next_refresh):  # Basic plan limit
                return redirect(url_for('results'))

            intern_titles = user.intern_titles
            skills = user.skills

            # Re-fetch jobs based on existing job recommendations and resume
            job_listings, runtimes_dict = get_jobs(intern_titles, skills, 'refresh_jobs')

            if os.getenv("WEBSITE_ENDPOINT").lower() == "https://rezify.ai":
                session['searches'] = searches + 1  # Increment searches count
            if searches > 100:
                # If the failed exceeds 75, lock the user out for 2 hours
                save_param_to_db('lockout', datetime.now() + timedelta(hours=2), session_id)
                clear_session(session)  # To set searches back to 0
                session['searches'] = 0

            # If there was an error getting the jobs, send a monitoring email and redirect to the results page
            if job_listings == 'Error':
                capture_message('ERROR: Error in get_jobs()', level="error")

                clear_session(session)
                session['segments'] = 1
                session['load'] = 'reload'
                session['get_jobs_error'] = True
                return redirect(url_for('results'))

            # Adding to search data if it comes from live site
            if WEBSITE_ENDPOINT.lower() == "https://rezify.ai":
                total_time = runtimes_dict['Total Time']
                add_search_data(total_time, 'refresh', user.email, runtimes_dict)

            user.update_user_param('internships_list', job_listings)  # Update the user's job listings with the new job listings

            user.update_user_param('last_refresh', datetime.now())

            # Run the jobs from the session id through the filter_jobs function to get the filtered job listings
            job_listings_segmented, segments, per_segment, total_jobs, distinct_titles, distinct_industries = filter_jobs(
                session_id)

            if job_listings_segmented == 'Fail':
                # If the filter_jobs function failed, return 'Fail' because this means the session expired
                session['session_expired'] = True
                return jsonify({"error_message": 'Fail'})

            return json.dumps({'segments': segments, 'per_segment': per_segment,
                               'jobs': job_listings_segmented, 'total_jobs': total_jobs,
                               "user": user.to_dict() if (type(user) == User) else None})
        except Exception as e:
            capture_exception(e)
            return jsonify({"error_message": 'Fail'})



    @app.route('/api/add_favorite', methods=['POST'])
    @cross_origin()
    def add_favorite():
        """
            This function handles the user adding a job to their favorites list (Clicking the star on the job).
            It gets the job ID from the request and either adds it or removes from the user's favorites list.
            (depending on whether it was already in there or not).
            """
        try:
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

            clear_session(session)  # Clear session except for session_id and school

            if get_param_from_db('user_email', session_id) is not None:  # Make sure a user is logged in
                user_email = get_param_from_db('user_email', session_id)  # Get the user email
                job_id = request.json.get("job_id")  # Get the job id from the request

                if job_id:  # If there is a valid job id
                    success, user = get_user_from_email(user_email)  # Get the user from the email

                    if not success:  # If the user-getting failed, the session expired (or they logged out)
                        session['session_expired'] = True  # To indicate that the session has expired
                        return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400


                    job = get_job_from_id(job_id)  # Get the entire job posting from the job id
                    if job is None:  # If the job is none (it is expired), set it to just the id for now
                        job = {'id': job_id}

                    if not check_if_job_in(job, user.get_user_list('favorites')):  # If the job is not in the user's favorites list, add it

                        if 'title' not in job:  # If the job title is None, it means it is expired. Return an error message.
                            return jsonify({'status': 'fail', 'message': 'Job is expired, please refresh jobs'}), 400

                        desc = get_raw_description(
                            job_id)  # Get the raw text description to add to the job - so it can be saved
                        job['description'] = markdown.markdown(desc, extensions=['extra',
                                                                                 'sane_lists'])  # Add the html description to the job

                        result = user.update_list_with_job('favorites', job,
                                                           True)  # Add the job to the user's favorites list

                        if result:  # Success!
                            return jsonify({'status': 'success'})
                        else:  # Failed to add job to the user's favorites list
                            return jsonify({'status': 'fail'})
                    else:  # If the job is already in the user's favorites list, remove it
                        result = user.update_list_with_job('favorites', job,
                                                           False)  # Remove the job from the user's favorites list

                        if result:  # Success!
                            return jsonify({'status': 'success'})
                        else:  # Failed to remove job from the user's favorites list
                            return jsonify({'status': 'fail'})
                return jsonify({'status': 'fail', 'message': 'Invalid job data'}), 400

            session['session_expired'] = True  # To indicate that the session has expired
            return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

        except Exception as e:
            capture_exception(e)
            return jsonify({'status': 'fail', 'message': 'An unknown error occured'}), 400



    @app.route('/api/add_applied_to', methods=['POST'])
    @cross_origin()
    def add_applied_to():
        """
        This function handles the user adding a job to their applied to list (Clicking the checkbox on the job).
        It gets the job ID from the request and either adds it or removes from the user's applied_to list.
        (depending on whether it was already in there or not).
        """

        try:

            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

            clear_session(session)  # Clear session except for session_id and school

            if get_param_from_db('user_email', session_id) is not None:  # Make sure a user is logged in
                user_email = get_param_from_db('user_email', session_id)  # Get the user email
                job_id = request.json.get("job_id")  # Get the job id from the request

                if job_id:  # If there is a valid job id
                    success, user = get_user_from_email(user_email)

                    if not success:  # If the user-getting failed, the session expired (or they logged out)
                        session['session_expired'] = True  # To indicate that the session has expired
                        return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

                    job = get_job_from_id(job_id)  # Get the entire job posting from the job id
                    if job is None:  # If the job is none (it is expired), set it to just the id for now
                        job = {'id': job_id}

                    if not check_if_job_in(job, user.get_user_list('applied_to')):  # If the job is not in the user's applied_to list, add it

                        if 'title' not in job:  # If the job title is None, it means it is expired. Return an error message.
                            return jsonify({'status': 'fail', 'message': 'Job is expired, please refresh jobs'}), 400

                        desc = get_raw_description(
                            job_id)  # Get the raw text description to add to the job - so it can be saved
                        job['description'] = markdown.markdown(desc, extensions=['extra',
                                                                                 'sane_lists'])  # Add the html description to the job

                        job['user_status'] = 'applied'  # Mark the job status as applied

                        result = user.update_list_with_job('applied_to', job, True)  # Add job to the user's applied_to list

                        if result:  # Success!
                            return jsonify({'status': 'success'})
                        else:  # Failed to add job to the user's applied_to list
                            return jsonify({'status': 'fail'})
                    else:  # If the job is already in the user's applied_to list, remove it

                        result = user.update_list_with_job('applied_to', job,
                                                           False)  # Remove job from the user's applied_to list

                        in_accepted = check_if_job_in(job, user.get_user_list(
                            'jobs_accepted'))  # Check if the job is already in jobs_accepted

                        if in_accepted:
                            user.update_list_with_job('jobs_accepted', job,
                                                      False)  # Remove job from jobs_accepted list

                        if result:  # Success!
                            return jsonify({'status': 'success'})
                        else:  # Failed to remove job from the user's applied_to list
                            return jsonify({'status': 'fail'})
                return jsonify({'status': 'error', 'message': 'Invalid job data'}), 400

            session['session_expired'] = True  # To indicate that the session has expired
            return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

        except Exception as e:
            capture_exception(e)
            return jsonify({'status': 'error', 'message': 'An Uknown Error Occured'}), 400

    @app.route('/api/update_applied_status', methods=['POST'])
    @cross_origin()
    def update_applied_status():
        """
        This function handles the user updating the status of a job in their applied to list.
        It gets the job ID and new status from the request and updates the job status in the user's applied_to list.
        """

        try:

            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

            clear_session(session)  # Clear session except for session_id and school

            if get_param_from_db('user_email', session_id) is not None:  # Make sure a user is logged in
                user_email = get_param_from_db('user_email', session_id)  # Get the user email
                job_id = request.json.get("job_id")  # Get the job id from the request
                new_status = request.json.get("status")  # Get the new status for the applied job

                if job_id:  # If there is a valid job id
                    success, user = get_user_from_email(user_email)
                    in_accepted = check_if_job_in(get_job_from_id(job_id), user.get_user_list('jobs_accepted')) # Check if the job is already in jobs_accepted

                    if not success:  # If the user-getting failed, the session expired (or they logged out)
                        session['session_expired'] = True  # To indicate that the session has expired
                        return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

                    user_applied_to = user.get_user_list('applied_to') # Get the user's applied_to list
                    for job in user_applied_to:
                        if job.get('id') == job_id:
                            job['user_status'] = new_status  # Update the job status
                            if new_status == 'accepted':
                                user.update_list_with_job('jobs_accepted', job, True)  # Add job to jobs_accepted list
                            elif new_status != 'accepted' and in_accepted:
                                user.update_list_with_job('jobs_accepted', job, False)  # Remove job from jobs_accepted list if changing the status away from accepted
                            break

                    result = user.update_user_param('applied_to', user_applied_to)  # Update the user's applied_to list with the updated job status

                    if result:  # Success!
                        return jsonify({'status': 'success'})
                    else:  # Failed to update the job status in the user's applied_to list
                        return jsonify({'status': 'fail'})

                else:
                    return jsonify({'status': 'error', 'message': 'Invalid job data'}), 400

        except Exception as e:
            capture_exception(e)
            return jsonify({'status': 'error', 'message': 'An Uknown Error Occured'}), 400

    @app.route('/api/save_notes_to_job', methods=['POST'])
    @cross_origin()
    def save_notes_to_job():
        """
        This function handles the user saving notes to a job in their applied to list.
        It gets the job ID and notes from the request and updates the notes in the user's applied_to list.
        """
        try:

            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

            clear_session(session)  # Clear session except for session_id and school

            if get_param_from_db('user_email', session_id) is not None:  # Make sure a user is logged in
                user_email = get_param_from_db('user_email', session_id)  # Get the user email
                job_id = request.json.get("job_id")  # Get the job id from the request
                notes = request.json.get("notes")  # Get the new status for the applied job

                if job_id:  # If there is a valid job id
                    success, user = get_user_from_email(user_email)

                    if not success:  # If the user-getting failed, the session expired (or they logged out)
                        session['session_expired'] = True  # To indicate that the session has expired
                        return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

                    user_applied_to = user.get_user_list('applied_to')  # Get the user's applied_to list
                    utc_now_string = datetime.now(timezone.utc).isoformat()
                    for job in user_applied_to:
                        if job.get('id') == job_id:
                            job['user_notes'] = notes  # Update the job status
                            job['notes_saved_time'] = utc_now_string
                            break

                    result = user.update_user_param('applied_to',
                                                    user_applied_to)  # Update the user's applied_to list with the updated job status

                    if result:  # Success!
                        return jsonify({'status': 'success', 'notes_saved_time': utc_now_string})
                    else:  # Failed to update the job status in the user's applied_to list
                        return jsonify({'status': 'fail'})

                else:
                    return jsonify({'status': 'error', 'message': 'Invalid job data'}), 400

        except Exception as e:
            capture_exception(e)
            return jsonify({'status': 'error', 'message': 'An Uknown Error Occured'}), 400


    @app.route('/api/remove_job', methods=['POST'])
    @cross_origin()
    def remove_job():
        """
        This function handles the user removing a job from their results (Clicking the 'X' on the job).
        It gets the job ID and reason from the request and either adds it or removes from the user's jobs_list..
        """

        try:
            session_id = session.get('session_id', None)  # Get the unique session ID from the session
            if session_id is None:
                # If there is no session id, send back to the beginning and set a new one
                session['session_expired'] = True  # To indicate that the session has expired
                return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

            clear_session(session)  # Clear session except for session_id and school

            if get_param_from_db('user_email', session_id) is not None:  # Make sure a user is logged in
                user_email = get_param_from_db('user_email', session_id)  # Get the user email
                job_id = request.json.get("job_id")  # Get the job id from the request
                reason = request.json.get("reason")  # Get the reason for removing the job

                if job_id:  # If there is a valid job id
                    success, user = get_user_from_email(user_email)

                    if not success:  # If the user-getting failed, the session expired (or they logged out)
                        session['session_expired'] = True  # To indicate that the session has expired
                        return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

                    job_full = get_job_from_id(job_id)  # Get the entire job posting from the job id
                    if job_full is None:
                        job_full = {'id': job_id}

                    session_jobs = get_param_from_db('jobs_list', session_id)  # Get the jobs list from the session database
                    session_jobs = [job for job in session_jobs if
                                    job.get('id') != job_full.get('id')]  # Remove the job from the session jobs list
                    save_param_to_db('jobs_list', json.dumps(session_jobs),
                                     session_id)  # Save the updated jobs list to the session database

                    user.update_list_with_job('internships_list', job_full, False)  # Remove job from the user's jobs_list

                    job_removed_list_info = {
                        'id': job_id,
                        'reason': reason,
                        'title': job_full.get('title'),
                        'company': job_full.get('company'),
                        'final_url': job_full.get('final_url'),
                        'date_posted': job_full.get('date_posted'),
                        'time_added': datetime.now().isoformat()
                    }

                    result = user.update_list_with_job('removed_jobs', job_removed_list_info,
                                                       True)  # Add job info to the user's removed_jobs list

                    # Function to add the job to the global bad jobs list. Only add it if the reason is expired, duplicate, or scam
                    if reason == 'Expired' or reason == 'Duplicate' or reason == 'Scam':
                        add_removed_job_global(job_removed_list_info)

                    if result:  # Success!
                        return jsonify({'status': 'success'})
                    else:  # Failed to add job to the user's removed_jobs list
                        return jsonify({'status': 'fail'})

                return jsonify({'status': 'error', 'message': 'Invalid job data'}), 400

            session['session_expired'] = True  # To indicate that the session has expired
            return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

        except Exception as e:
            capture_exception(e)
            return jsonify({'status': 'error', 'message': 'An Unknown Error Occurred'}), 400

    @app.route('/api/increment_linkedin_clicks', methods=['POST'])
    @cross_origin()
    def api_increment_linkedin_clicks():
        """
        Increments linkedin_clicks for the most recent traffic_history row.
        """

        try:
            session_id = session.get('session_id', None)

            if session_id is None:
                session['session_expired'] = True
                return jsonify({'status': 'session_fail', 'message': 'Session is expired'}), 400

            clear_session(session)

            # Call the increment function
            updated = increment_linkedin_clicks()

            if updated:
                return jsonify({'status': 'success'}), 200
            else:
                return jsonify({'status': 'fail', 'message': 'Could not update linkedin clicks'}), 500

        except Exception as e:
            capture_exception(e)
            return jsonify({'status': 'error', 'message': 'An Unknown Error Occurred'}), 400


## HELPER FUNCTIONS ##
def filter_jobs(session_id, segments=1, per_segment=25):
    """
        Filters and returns job listings based on user preferences and filters.

        Parameters:
        session_id (str): The unique identifier for the user's session.
        segments (int, optional): The number of segments of jobs to be shown. Default is 1.
        per_segment (int, optional): The number of job listings per segment. Default is 25.

        Returns:
        job_listings_segmented (list): The segmented job listings based on user preferences and filters.
        segments (int): The number of segments to be shown.
        per_segment (int): The number of job listings per segment.
        total_jobs (int): The total number of job listings.
        distinct_titles (set): The distinct job titles based on user's search titles.
        distinct_industries (set): The distinct job industries based on user's search titles.
    """

    try:

        # Getting the user of the current session and getting their filters
        success, user = get_user_from_email(get_param_from_db('user_email', session_id))

        if not success:  # If the user is not found, it means the session has expired
            capture_exception(Exception('ERROR: Error in filter_jobs()'))
            return 'Fail', None, None, None, None, None

        filters = user.filters

        # If no selected filter is provided, default to 'All' (Discover page)
        if filters['selected_filter'] is None:
            filters['selected_filter'] = 'All'
            user.update_user_param('filters', filters)

        # Get the user again after updating the filter
        success, user = get_user_from_email(get_param_from_db('user_email', session_id))
        if success:
            filters = user.filters

            # Getting the user job listings and showing which category they select to see (All/Favorites/Applied_to)
            job_listings = user.get_user_list('internships_list')
            distinct_titles = []
            distinct_industries = []

            if filters['selected_filter'] == 'Favorites':  # If the favorites filter is selected
                job_listings = [job for job in user.get_user_list('favorites')]

            elif filters['selected_filter'] == 'Applied_to':  # If the applied to filter is selected
                job_listings = [job for job in user.get_user_list('applied_to')]

            elif filters['selected_filter'] == 'All':  # If the all filter is selected (Discover page)
                # Get the user's jobs that aren't in applied_to
                applied_job_ids = {job['id'] for job in user.get_user_list('applied_to')}  # Create a set of applied job IDs
                job_listings = [job for job in job_listings if job['id'] not in applied_job_ids]

                # You Can only apply certain filters when on the 'All' (Discover page)

                intern_titles = user.intern_titles

                # 'type' is the type of work. Can either be Remote/In-person/All.

                if filters['type'] == 'Remote':  # If the remote filter is selected
                    job_listings = [job for job in job_listings if job['remote']]

                elif filters['type'] == 'In-person':  # If the in-person filter is selected
                    job_listings = [job for job in job_listings if not job['remote']]

                # if 'international_only' is true, get only the jobs that have 'international_availability' set to True
                if filters['international_only']:
                    job_listings = [job for job in job_listings if job['international_availability']]

                # if there is a location entered, filter the jobs by their location
                if filters.get('location') is not None and filters.get('location') != '':
                    location = filters['location']
                    radius = filters['radius']
                    if ',' not in location:
                        capture_message(f'WARNING: , not found in location: {location}', level="warning")
                    location_city = location[:location.index(',')]
                    location_state = location[location.index(',') + 2:]

                    # Call the filter_by_location function to filter the jobs by location, using information above
                    job_listings = filter_by_location(job_listings, cities_df, location_city, location_state, radius)

                # Apply sorting - 'Relevance' is the default, so only sort if date is selected
                if filters['sort_by'] == 'Date':
                    job_listings = sort_job_listings_by_date(job_listings)

                # If any of the title buttons are clicked, only get the job listings that have their filter selected
                if len(filters['selected_titles']) > 0:
                    job_listings = [job for job in job_listings if job['job_rec'] in filters['selected_titles']]

                # Get the distinct job titles and industries to pass to the front-end
                distinct_titles =list(set(title for title in intern_titles))
                distinct_industries = list(set(
                    job['company_industry'] for job in job_listings if job['company_industry'] is not None))

                # If any of the industry buttons are clicked, only get the job listings that have their filter selected
                if len(filters['selected_industries']) > 0:
                    job_listings = [job for job in job_listings if
                                    job['company_industry'] in filters['selected_industries']]

            # Limit the job_listings to at most 300 jobs
            job_listings = job_listings[:300]
            total_jobs = len(job_listings)

            # Save the updated user's job listings in the session database
            save_param_to_db('jobs_list', json.dumps(job_listings), session_id)
            job_listings_segmented = job_listings[0:segments * per_segment]  # Send the jobs by segments

            if user.last_refresh is None:
                user.update_user_param("last_refresh", datetime.now())

            if total_jobs == 0:
                capture_message('WARNING: Jobs length 0 after filtering', level="warning")

            return job_listings_segmented, segments, per_segment, total_jobs, distinct_titles, distinct_industries

        else:
            # If the user is not found, it means the session has expired
            capture_exception(Exception('ERROR: Error in filter_jobs()'))
            return 'Fail', None, None, None, None, None

    except Exception as e:
        capture_exception(e)
        return 'Fail', None, None, None, None, None