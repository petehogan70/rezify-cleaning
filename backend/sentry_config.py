import sentry_sdk
import os
from sentry_sdk.integrations.flask import FlaskIntegration

def init_sentry():

    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        integrations=[FlaskIntegration()],
        environment="cleaning",
        send_default_pii=True,
        traces_sample_rate=1.0,
        profile_session_sample_rate=1.0,
        profile_lifecycle="trace",
        enable_logs=True,
    )

