import sentry_sdk
import os
from sentry_sdk.integrations.flask import FlaskIntegration
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from.env file

if os.getenv('WEBSITE_ENDPOINT') == "https://rezify.ai":
    environment = "production"
else:
    environment = "development"

def init_sentry():

    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[FlaskIntegration()],
        environment=environment,
        send_default_pii=True,
        traces_sample_rate=1.0,
        profile_session_sample_rate=1.0,
        profile_lifecycle="trace",
        enable_logs=True,
    )

