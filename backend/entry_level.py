import os

import requests
from dotenv import load_dotenv
from sentry_sdk import capture_exception, capture_message

"""
jobs.py is a file containing all functions to make transactions to and from the entry_level table in the database.
It contains functions to search for jobs using the TheirStack API, add jobs to the database, get jobs from the database,
as well as update certain columns of jobs in the database such as location, industry, and international availability.
In addition to this, the logic for the main searching function is also in this file. Including parsing the resume
with our OpenAI API, and the main get_jobs() function that matches search terms and resumes to jobs in the database.

Any new functions or updates to functions referring to getting, adding, or updating jobs in the database should be 
done here.
"""

load_dotenv()


def search_entry_level(revealed, not_ids):
    """
    Search for jobs using the TheirStack API. It searches the TheirStack API with specific criteria, including
    only searching for jobs where 'intern', 'internship', or 'co-op' is in the title, and the job is located in the US.
    It searches for jobs discovered within the past day, in order to get the most recent postings. This is the
    function that is called every hour to load jobs into our database.

    :param revealed: A boolean value indicating whether to search for companies that are revealed or not. Set to 'None'
    for regular searching.
    :param not_ids: A list of job ids to exclude from the search. This is used to prevent from including jobs that we
    have already loaded recently.
    :return: data - which is the list of jobs found.
    """
    try:
        url = "https://api.theirstack.com/v1/jobs/search"
        payload = {
            "order_by": [
                {
                    # Order by the most recent discovered jobs
                    "desc": True,
                    "field": "discovered_at"
                }
            ],
            "page": 0,
            "limit": 15,  # This is the maximum limit it allows us to set
            "include_total_results": True,
            "job_id_not": not_ids,  # Jobs we DON'T want to include in our search, because we have already discovered them
            "company_type": "direct_employer",  # Only search for direct employers - exclude recruiting companies
            "company_name_not": ["WayUp", "RippleMatch", "Lensa", "Jobs via Dice", 'Jobright.ai'],  # Exclude WayUp, RippleMatch, Lensa, and Jobs via Dice
            "job_title_not": ["intern", "internship", "co-op", "Senior", "Staff", "Lead", "Manager","Director", "Head of"],  # Only internships and co-ops,
            "job_title_pattern_or": [
                "(?i)entry[ -]?level",
                "(?i)new grad",
                "(?i)graduate (program|scheme|role)",
                "(?i)junior",
                "(?i)jr"
                "(?i)campus (hire|recruiting|program)",
                "(?i)developmental program",
                "(?i)graduate"
            ],
            "job_description_pattern_is_case_insensitive": True,
            "job_seniority_or": ["mid_level", "staff"],
            "employment_statuses_or": ["full_time", "contract", "other"],
            "property_exists_or": ["final_url"],
            "job_country_code_or": ["US"],  # Only job postins in the US
            "discovered_at_max_age_days": 1,  # 1 for real searching - only jobs discovered in the last day
            "posted_at_max_age_days": 20,  # 20 for real searching - only jobs posted in the last 20 days.
            # ^ The reason why this is 20 is because jobs can be discovered at a later date than when they are posted.
            "revealed_company_data": revealed  # None/True/False
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('THEIRSTACK_API_KEY')}"
        }
        response = requests.post(url, json=payload, headers=headers)  # Request data from TheirStack API

        data = response.json()['data']  # The jobs returned

        if len(data) == 0:
            capture_message("WARNING: 0 jobs found in search_jobs()", level="warning")

        print(len(data))

        return data
    except Exception as e:
        capture_exception(e)
        return []


def search_junior_level(revealed, not_ids):
    """
    Search for jobs using the TheirStack API. It searches the TheirStack API with specific criteria, including
    only searching for jobs where 'intern', 'internship', or 'co-op' is in the title, and the job is located in the US.
    It searches for jobs discovered within the past day, in order to get the most recent postings. This is the
    function that is called every hour to load jobs into our database.

    :param revealed: A boolean value indicating whether to search for companies that are revealed or not. Set to 'None'
    for regular searching.
    :param not_ids: A list of job ids to exclude from the search. This is used to prevent from including jobs that we
    have already loaded recently.
    :return: data - which is the list of jobs found.
    """
    try:
        url = "https://api.theirstack.com/v1/jobs/search"
        payload = {
            "order_by": [
                {
                    # Order by the most recent discovered jobs
                    "desc": True,
                    "field": "discovered_at"
                }
            ],
            "page": 0,
            "limit": 15,  # This is the maximum limit it allows us to set
            "include_total_results": True,
            "job_id_not": not_ids,  # Jobs we DON'T want to include in our search, because we have already discovered them
            "company_type": "direct_employer",  # Only search for direct employers - exclude recruiting companies
            "company_name_not": ["WayUp", "RippleMatch", "Lensa", "Jobs via Dice", 'Jobright.ai'],  # Exclude WayUp, RippleMatch, Lensa, and Jobs via Dice
            "job_title_not": ["intern", "internship", "co-op", "Senior", "Staff", "Lead", "Manager","Director", "Head of"],  # Only internships and co-ops,
            "job_description_pattern_is_case_insensitive": True,
            "job_seniority_or": ["junior"],
            "employment_statuses_or": ["full_time", "contract", "other"],
            "property_exists_or": ["final_url"],
            "job_country_code_or": ["US"],  # Only job postins in the US
            "discovered_at_max_age_days": 2,  # 1 for real searching - only jobs discovered in the last day
            "posted_at_max_age_days": 20,  # 20 for real searching - only jobs posted in the last 20 days.
            # ^ The reason why this is 20 is because jobs can be discovered at a later date than when they are posted.
            "revealed_company_data": revealed  # None/True/False
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('THEIRSTACK_API_KEY')}"
        }
        response = requests.post(url, json=payload, headers=headers)  # Request data from TheirStack API

        data = response.json()['data']  # The jobs returned

        if len(data) == 0:
            capture_message("WARNING: 0 jobs found in search_jobs()", level="warning")

        print(len(data))

        return data
    except Exception as e:
        capture_exception(e)
        return []

if __name__ == "__main__":
    jobs = search_entry_level(None, [])
    for job in jobs:
        print(f"Title: {job['job_title']}, Seniority: {job['seniority']}, Statuses: {job['employment_statuses']}, URL: {job['final_url']}")