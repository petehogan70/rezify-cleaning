from sentry_sdk import capture_exception

from backend.monitoring import add_traffic_history, count_sessions_data, get_daily_active_sessions
from backend.superadmin import get_user_breakdown, count_admins, get_total_applications, get_total_accepted, \
    get_total_favorites, get_total_messages_generated, get_daily_search_counts, \
    get_daily_homepage_searchtime, get_daily_refresh_addtitle_searchtime, get_daily_parseexp_avg_runtime
from sentry_sdk import capture_exception

from backend.monitoring import add_traffic_history, count_sessions_data, get_daily_active_sessions
from backend.superadmin import get_user_breakdown, count_admins, get_total_applications, get_total_accepted, \
    get_total_favorites, get_total_messages_generated, get_daily_search_counts, \
    get_daily_homepage_searchtime, get_daily_refresh_addtitle_searchtime, get_daily_parseexp_avg_runtime

"""
This script is designed to be run in Heroku Scheduler (every hour) to accumulate jobs from TheirStack API and load them into
our Postgres database and Elasticsearch indexes. It also sends a daily monitoring email with the current state of the
system.

Any new functionality that needs to be ran in the background by a scheduler should be added here.
"""

# RUN python accumulate_jobs.py in heroku scheduler to auto accumulate jobs

if __name__ == "__main__":
    try:

        # Add traffic history data to the database
        user_breakdown = get_user_breakdown()
        search_breakdown = get_daily_search_counts()
        add_traffic_history(user_breakdown['total_users'], count_sessions_data(), search_breakdown['total_searches'],
                            count_admins(), user_breakdown['paying_premium_users'], user_breakdown['basic_users'], user_breakdown['sponsored_premium_users'],
                            get_daily_active_sessions(), search_breakdown['homepage_searches'], search_breakdown['add_title_searches'], search_breakdown['refresh_searches'],
                            get_total_favorites(), get_total_applications(), get_total_messages_generated(), get_total_accepted(), get_daily_parseexp_avg_runtime(),
                            get_daily_homepage_searchtime(), get_daily_refresh_addtitle_searchtime())

    except Exception as e:
        capture_exception(e)
