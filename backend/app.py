import logging
import os
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask, send_from_directory
from flask_cors import CORS, cross_origin
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy

from backend.sentry_config import init_sentry

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

# Regular DB config
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQL_DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=5)  # Set session lifetime to 3 days

app.config['SESSION_COOKIE_DOMAIN'] = os.getenv('SERVER_COOKIE_DOMAIN')
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent client-side JS from accessing session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Mitigate CSRF (Lax is good balance for most apps)


# Session config
app.config['SESSION_TYPE'] = 'sqlalchemy'
db = SQLAlchemy(app)
app.config['SESSION_SQLALCHEMY'] = db

Session(app)


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
    app.run(port=5000)
