import time
from datetime import datetime, timezone

from sentry_sdk import capture_exception

from backend.clean_job_tables import get_not_ids
from backend.internships_elasticsearch_config import load_title_embeddings_internships_bulk_from_jobs, delete_orphan_documents_internships, \
    load_description_embeddings_internships_bulk_from_jobs, load_description_embeddings_internships_bulk, \
    load_title_embeddings_internships_bulk, get_title_document_count_internships, get_description_document_count_internships
from backend.jobs import search_jobs, add_jobs_to_db
from backend.login import premium_schools
from backend.monitoring import send_daily_monitoring_email, get_theirstack_data, delete_old_sessions, \
    delete_old_search_entries, get_daily_credits_by_type, clean_ts_tables, \
    get_jobs_database_length, add_TS_data, \
    add_TS_call, add_traffic_history, count_sessions_data, add_jobs_data_hist, get_daily_active_sessions
from backend.session_management import clean_old_session_data
from backend.superadmin import get_user_breakdown, count_admins, get_total_applications, get_total_accepted, \
    get_total_favorites, get_total_messages_generated, get_daily_search_counts, \
    get_daily_homepage_searchtime, get_daily_refresh_addtitle_searchtime, get_daily_parseexp_avg_runtime
from backend.university_admin_stats import update_school_data
from backend.openai_api import add_openai_history

"""
This script is designed to be run in Heroku Scheduler (every hour) to accumulate jobs from TheirStack API and load them into
our Postgres database and Elasticsearch indexes. It also sends a daily monitoring email with the current state of the
system.

Any new functionality that needs to be ran in the background by a scheduler should be added here.
"""

# RUN python accumulate_jobs.py in heroku scheduler to auto accumulate jobs

if __name__ == "__main__":
    try:
        print(f"Jobs (before) count: {get_jobs_database_length()}")

        # Call the search_jobs function to get the new postings from TheirStack API
        jobs = search_jobs(None, get_not_ids('internships'))
        print(f"Number of new jobs found: {len(jobs)}")
        add_TS_call(len(jobs), 'internships')  # Log the number of jobs found in the database

        # Add the new jobs found to the database
        add_jobs_to_db(jobs)

        # Load the title and description embeddings into Elasticsearch of the new jobs
        load_title_embeddings_internships_bulk_from_jobs(jobs)
        load_description_embeddings_internships_bulk_from_jobs(jobs)

        # Delete orphan documents in Elasticsearch indexes, so any document should match a job in the database
        delete_orphan_documents_internships()

        print(f"Jobs count: {get_jobs_database_length()}")
        print(f"Elasticsearch title embedding count: {get_title_document_count_internships()}")
        print(f"Elasticsearch description embedding count: {get_description_document_count_internships()}")

        if datetime.now(timezone.utc).hour == 0:  # Send the monitoring email only once a day at midnight UTC
            delete_old_sessions()  # Delete old sessions from the database
            clean_old_session_data()  # Clean old session data from the sessions_data table
            clean_ts_tables() # Clean old rows from ts tables

            load_description_embeddings_internships_bulk()  # Load missing description embeddings into Elasticsearch
            load_title_embeddings_internships_bulk() # Load missing title embeddings into Elasticsearch

            daily_credits_by_type = get_daily_credits_by_type()

            add_TS_data(get_theirstack_data()['used_api_credits'], daily_credits_by_type['cut_internships'], daily_credits_by_type['cut_fulltime'])  # Add TheirStack data to the database
            add_jobs_data_hist(get_jobs_database_length())

            time.sleep(10)

            # Add traffic history data to the database
            user_breakdown = get_user_breakdown()
            search_breakdown = get_daily_search_counts()
            add_traffic_history(user_breakdown['total_users'], count_sessions_data(), search_breakdown['total_searches'],
                                count_admins(), user_breakdown['paying_premium_users'], user_breakdown['basic_users'], user_breakdown['sponsored_premium_users'],
                                get_daily_active_sessions(), search_breakdown['homepage_searches'], search_breakdown['add_title_searches'], search_breakdown['refresh_searches'],
                                get_total_favorites(), get_total_applications(), get_total_messages_generated(), get_total_accepted(), get_daily_parseexp_avg_runtime(),
                                get_daily_homepage_searchtime(), get_daily_refresh_addtitle_searchtime())

            send_daily_monitoring_email("technology@rezify.ai")
            delete_old_search_entries()

            update_school_data(premium_schools)

        if datetime.now(timezone.utc).hour == 2:
            add_openai_history()

    except Exception as e:
        capture_exception(e)
