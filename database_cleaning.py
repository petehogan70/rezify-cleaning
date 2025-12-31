from backend.clean_job_tables import get_jobs_for_cleaning, job_cleaning

"""
This script is to be ran in Heroku Scheduler (daily) to clean the jobs database. It runs the long process that checks
the link of each job and removes the ones that are not valid anymore. 
"""

if __name__ == "__main__":
    # Only check jobs that are older than 7 days, from oldest to newest
    jobs_to_clean = get_jobs_for_cleaning('internships',7, newest=False)

    # Run the cleaning process
    job_cleaning(jobs_to_clean, 'internships')