import logging
import os
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask, send_from_directory
from flask_cors import CORS, cross_origin
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask import request, jsonify

from backend.sentry_config import init_sentry
from backend.job_cleaningtesting import check_single_link

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
    resources={r"/api/*": {"origins": ["http://127.0.0.1:5000"]}}
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


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    static_file = os.path.join(app.static_folder, path)

    if path != "" and os.path.exists(static_file):
        return send_from_directory(app.static_folder, path)

    return send_from_directory(app.static_folder, "index.html")


@app.route("/check_job", methods=["POST"])
def check_job():
    try:
        data = request.get_json(silent=True) or {}
        final_url = data.get("final_url")

        if not final_url or not isinstance(final_url, str):
            return jsonify({
                "error": "Missing or invalid final_url"
            }), 400

        result = check_single_link(final_url)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({
            "final_url": data.get("final_url") if isinstance(data, dict) else None,
            "decision": "KEEP",
            "reason": f"Server error: {type(e).__name__}: {e}",
            "used": "route_error"
        }), 500

# Main block to run the app
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(port=5000)
