from flask import request, jsonify, session
from flask_cors import cross_origin
from sentry_sdk import capture_exception, capture_message
from backend.ai_generation import generate_talking_points, generate_personalized_message
from backend.jobs import get_job_from_id, get_raw_description
from backend.login import get_user_from_email
from backend.session_management import get_param_from_db


def linkedin_messaging_routes(app):
    @app.route('/api/messaging/analyze-talking-points', methods=['POST'])
    @cross_origin()
    def analyze_talking_points():
        """
        Analyzes the user's resume and job description to identify key talking points for outreach messages.
        """
        session_id = session.get('session_id', None)
        if session_id is None:
            return jsonify({'error': 'Session not found'}), 401

        try:
            data = request.get_json()
            job_id = data.get('jobId')

            if not job_id:
                return jsonify({'error': 'Job ID is required'}), 400

            # Get user's resume info from session
            resume_info = get_param_from_db('resume_info', session_id)
            if not resume_info:
                return jsonify({'error': 'Resume information not found'}), 404

            # Get job information from database
            job = get_job_from_id(job_id)
            if not job:
                return jsonify({'error': 'Job not found'}), 404

            # Get job description
            job_description = get_raw_description(job_id)

            success, user = get_user_from_email(get_param_from_db('user_email', session_id))

            if success:
                # Generate talking points using AI
                talking_points = generate_talking_points(user, job, job_description)

                capture_message("Generated Talking Points", level="info")

                return jsonify({
                    'talkingPoints': talking_points,
                    'status': 'success'
                })
            else:
                return jsonify({'error': 'No user found'}), 500

        except Exception as e:
            capture_exception(e)
            return jsonify({'error': 'Internal server error'}), 500


    @app.route('/api/messaging/generate-personalized-draft', methods=['POST'])
    @cross_origin()
    def generate_personalized_draft():
        """
        Generates a personalized outreach message using AI based on selected talking points and message goal.
        """

        session_id = session.get('session_id', None)
        if session_id is None:
            return jsonify({'error': 'Session not found'}), 401

        try:
            data = request.get_json()
            job_id = data.get('jobId')
            selected_talking_points = data.get('selectedTalkingPoints', [])
            message_goal = data.get('messageGoal', '')
            message_length = data.get('messageLength', 'standard')  # brief, standard, detailed

            success, user = get_user_from_email(get_param_from_db('user_email', session_id))


            if not job_id or not selected_talking_points or not message_goal:
                return jsonify({'error': 'Missing required parameters'}), 400

            # Get user's resume info from session
            resume_info = get_param_from_db('resume_info', session_id)
            if not resume_info:
                return jsonify({'error': 'Resume information not found'}), 404

            # Get job information from database
            job = get_job_from_id(job_id)
            if not job:
                return jsonify({'error': 'Job not found'}), 404

            # Get job description
            job_description = get_raw_description(job_id)

            success, user = get_user_from_email(get_param_from_db('user_email', session_id))

            if not success:
                return jsonify({'error': 'No user found'}), 500

            # Generate personalized message using AI
            message = generate_personalized_message(
                user,
                job,
                job_description,
                selected_talking_points,
                message_goal,
                message_length
            )

            if success:
                ## INCLUDE THE JOB ID AND THE MESSAGE
                job = {'id': job_id, 'message': message}
                user.update_list_with_job('messages_generated', job, True)

                capture_message("Generated Personal Draft", level="info")


            return jsonify({
                'message': message,
                'status': 'success'
            })

        except Exception as e:
            capture_exception(e)
            return jsonify({'error': 'Internal server error'}), 500