import logging
import os
from datetime import datetime, timedelta

import markdown
from dotenv import load_dotenv
from flask import Flask, request, redirect, send_from_directory, session
from flask_cors import CORS, cross_origin
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from sentry_sdk import capture_exception

from backend.login import get_user_from_email
from backend.admin_login import get_admin_from_email
from backend.payment import restart_stripe_transactions
from backend.session_management import get_param_from_db, need_domain_change
from backend.sentry_config import init_sentry

# Import all routes
from backend.routes.account_routes import account_routes
# from backend.routes.employer_routes import employer_routes
from backend.routes.index_routes import index_routes
from backend.routes.linkedin_messaging_routes import linkedin_messaging_routes
from backend.routes.results_routes import results_routes
from backend.routes.admin_routes import admin_routes
from backend.routes.admin_account_routes import admin_account_routes
from backend.routes.form_routes import form_routes


"""
rezify.py is the main file of the Rezify application. It contains the main Flask app and all the routes for the 
application.

Any new routes for the application should be added here.
"""

load_dotenv()  # Load environment variables from.env file


# Setup logging
logging.basicConfig(level=logging.WARNING)

init_sentry()

# logging.getLogger("werkzeug").setLevel(logging.WARNING)      # or WARNING
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sentry_sdk").setLevel(logging.WARNING)

# Initialize Flask app
app = Flask(__name__, static_folder="../frontend/build", static_url_path="")
CORS(
    app,
    supports_credentials=True,
    resources={r"/api/*": {"origins": ["http://rezify.local:3000"]}}
)
app.secret_key = os.environ.get('SECRET_KEY')

# Use routes from the 'routes' directory
account_routes(app)
index_routes(app)
linkedin_messaging_routes(app)
results_routes(app)
admin_routes(app)
admin_account_routes(app)
form_routes(app)
# employer_routes(app) - Not used yet


# Get website endpoint with fallback (moved up for early use)
WEBSITE_ENDPOINT = os.getenv("WEBSITE_ENDPOINT", "http://localhost:5000")

if WEBSITE_ENDPOINT == "https://rezify.ai":
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sentry_sdk").setLevel(logging.WARNING)

# Regular DB config
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQL_DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=5)  # Set session lifetime to 3 days
if 'https://' in WEBSITE_ENDPOINT.lower():
    app.config['SESSION_COOKIE_SECURE'] = True  # Ensure cookies are only sent over HTTPS

if WEBSITE_ENDPOINT.lower() == 'http://rezify.local:5000':
    app.config['SERVER_NAME'] = WEBSITE_ENDPOINT[WEBSITE_ENDPOINT.find('://') + 3:]

app.config['SESSION_COOKIE_DOMAIN'] = os.getenv('SERVER_COOKIE_DOMAIN')
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent client-side JS from accessing session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Mitigate CSRF (Lax is good balance for most apps)


# Session config
app.config['SESSION_TYPE'] = 'sqlalchemy'
db = SQLAlchemy(app)
app.config['SESSION_SQLALCHEMY'] = db

Session(app)


@app.before_request
def check_domain():
    """
    Checks the domain of the request and redirects to the appropriate domain if necessary. This is used to make sure
    logged-in users are on their school's domain, or the main Rezify domain if they are not logged in. It also checks
    any non-valid domains and redirects them to the main Rezify domain.
    :return: redirect to the appropriate domain if necessary, otherwise does nothing.
    """
    # Skip domain checking for local development
    if 'rezify.local' in request.host.lower():
        return

    try:
        
        host = request.host.lower()

        session_id = session.get('session_id')

        is_admin = get_param_from_db('admin', session_id)
        if is_admin:
            success, user = get_admin_from_email(get_param_from_db('user_email', session_id))
            if not success:
                user = None
        else:
            success, user = get_user_from_email(get_param_from_db('user_email', session_id))
            if not success:
                user = None

        if session_id:
            if is_admin:
                needs_to_change = need_domain_change(host, user, user_type='admin')
            else:
                needs_to_change = need_domain_change(host, user)
        else:
            needs_to_change = False

        if needs_to_change:
            if session.get('school') is None or session.get('school') == 'rezify':
                domain = WEBSITE_ENDPOINT
            else:
                starting_point = WEBSITE_ENDPOINT.find('://')
                domain = WEBSITE_ENDPOINT[:starting_point + 3] + session.get('school') + '.' + WEBSITE_ENDPOINT[starting_point + 3:]

            return redirect(domain)

    except Exception as e:
        capture_exception(e)



@app.route('/static/<path:filename>')
def serve_static(filename):
    """
        Serves static files from the 'static' directory.
    """
    return send_from_directory(app.static_folder + '/static', filename)

@app.route('/vpat')
def vpat():
    """
        Route to the VPAT statment in the Rezify_VPAT.pdf file in the static directory.
    """
    return send_from_directory(app.static_folder + '/static', 'Rezify_VPAT.pdf')


@app.route('/privacynotice')
def privacynotice():
    """
        Route to the privacy notice in the Rezify_Security.pdf file in the static directory.
    """
    return send_from_directory(app.static_folder + '/static', 'Rezify_Security.pdf')


# Route to our favicon
@app.route('/favicon.ico')
def favicon():
    """
        Route to the favicon in the favicon.ico file in the static directory.
    """
    return send_from_directory(app.static_folder + '/static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')



@app.template_filter('format_date')
def format_date(value):
    """
    Converts a date string from 'YYYY-MM-DD' format to 'MM-DD-YYYY' format for better viewing
    """

    return datetime.strptime(value, '%Y-%m-%d').strftime('%m-%d-%Y')


@app.template_filter('markdown_to_clean')
def markdown_to_clean(description):
    """
    Converts a markdown description to HTML format for better viewing
    """
    return markdown.markdown(description, extensions=['extra', 'sane_lists'])

@app.route('/')
@app.route('/<first>')
@app.route('/<first>/<path:rest>')
@cross_origin()
def frontendindex(first="", rest=""):
    return send_from_directory(app.static_folder, 'index.html')

# Main block to run the app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    restart_stripe_transactions()
    app.run(port=5000)
