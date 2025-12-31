from flask import request, jsonify
from flask_cors import cross_origin
from sentry_sdk import capture_exception

from backend.email_sending import send_feedback_email, send_help_request_email


def form_routes(app):
    @app.route('/api/submit_feedback', methods=['POST'])
    @cross_origin()
    def submit_feedback():
        """
            Will send an email to support@rezify.ai with the contents of the feedback form submitted in the website
        """
        try:
            feedback_form = request.form.to_dict()

            success = send_feedback_email("support@rezify.ai", feedback_form)

            return jsonify({'status': 'success'}) if success else jsonify({'status': 'error'})
        except Exception as e:
            capture_exception(e)
            return jsonify({'status': 'error', 'message': str(e)})


    @app.route('/api/submit_help', methods=['POST'])
    @cross_origin()
    def submit_help():
        """
            Will send an email to support@rezify.ai with the contents of the help form submitted in the website
        """
        try:
            email = request.form['email']
            problem = request.form['problem']

            success = send_help_request_email("support@rezify.ai", email, problem)

            return jsonify({'status': 'success'}) if success else jsonify({'status': 'error'})
        except Exception as e:
            capture_exception(e)
            return jsonify({'status': 'error', 'message': str(e)})