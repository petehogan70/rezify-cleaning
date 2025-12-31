import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from datetime import timedelta
from itertools import chain
from backend.tables import openai_usage_table
import requests
from dotenv import load_dotenv
from sentry_sdk import capture_exception
from sqlalchemy import text

from backend.database_config import Session

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_DATA_READ_KEY")
OPENAI_USAGE_BASE = "https://api.openai.com/v1/organization/usage"
OPENAI_COSTS_BASE = "https://api.openai.com/v1/organization/costs"


def _unix_range_for_days_back(days_back: int) -> tuple[int, int]:
    """
    Converts days_back to (start_time, end_time) in Unix seconds.
    The start_time is set to the beginning (00:00:00 UTC) of the day
    that is `days_back` days ago, and the end_time is the current time.
    """
    now = datetime.now(timezone.utc)

    # Calculate the date `days_back` days ago and reset to start of that day (UTC)
    start_of_day = (now - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)

    return int(start_of_day.timestamp()), int(now.timestamp())

def _unix_range_for_mins_back(mins_back: int) -> tuple[int, int]:
    """
    Converts days_back to (start_time, end_time) in Unix seconds.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=mins_back)
    return int(start.timestamp()), int(now.timestamp())


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {OPENAI_API_KEY}"}

def get_projects():
    """
    Fetches Project ids and project names.

    :return: Dict of project_id: project_name.
    """
    try:

        final_data = {}
        url = f"https://api.openai.com/v1/organization/projects"
        response = requests.get(url, headers=_auth_headers(), timeout=30)
        data = response.json()['data']
        for dat in data:
            final_data[dat['id']] = dat['name']

        return final_data


    except Exception as e:
        capture_exception(e)
        return {}



def get_openai_completion_usage(days_back: int = 7):
    """
    Fetches OpenAI usage data for the past `days_back` days.

    :param days_back: Number of days back from now.
    :return: Dict of usage data or None if error.
    """
    try:
        start_time, end_time = _unix_range_for_days_back(days_back)
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "bucket_width": "1d",
            "limit": 30,
            "group_by": ["project_id"]
        }

        url = f"{OPENAI_USAGE_BASE}/completions"
        response = requests.get(url, headers=_auth_headers(), params=params, timeout=30)
        final_data = []
        data = response.json()['data']
        projects = get_projects()

        for dat in data:
            date_obj = {'start_date': datetime.fromtimestamp(int(dat['start_time']), timezone.utc).strftime("%Y-%m-%d"),
                        'end_date': datetime.fromtimestamp(int(dat['end_time']), timezone.utc).strftime("%Y-%m-%d")}
            usage_results = {}
            for project in dat['results']:
                project_name = projects[project['project_id']]
                num_requests = project['num_model_requests']
                if project_name == 'Main Search':
                    num_requests = round(float(num_requests / 2), 4)
                elif project_name == 'Message Generation':
                    num_requests = round(float(num_requests / 2), 4)
                usage_results[project_name] = num_requests

            date_obj['usage_results'] = usage_results
            final_data.append(date_obj)

        return final_data

    except Exception as e:
        print(e)
        capture_exception(e)
        return None

def get_openai_embedding_usage(days_back: int = 7):
    """
    Fetches OpenAI usage data for the past `days_back` days.

    :param days_back: Number of days back from now.
    :return: Dict of usage data or None if error.
    """
    try:
        start_time, end_time = _unix_range_for_days_back(days_back)
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "bucket_width": "1d",
            "limit": 30,
            "group_by": ["project_id"]
        }

        url = f"{OPENAI_USAGE_BASE}/embeddings"
        response = requests.get(url, headers=_auth_headers(), params=params, timeout=30)
        final_data = []
        data = response.json()['data']
        projects = get_projects()

        for dat in data:
            date_obj = {'start_date': datetime.fromtimestamp(int(dat['start_time']), timezone.utc).strftime("%Y-%m-%d"),
                        'end_date': datetime.fromtimestamp(int(dat['end_time']), timezone.utc).strftime("%Y-%m-%d")}
            usage_results = {}
            for project in dat['results']:
                project_name = projects[project['project_id']]
                num_requests = project['num_model_requests']
                if project_name == 'Main Search':
                    num_requests = round(float(num_requests / 5), 4)
                elif project_name == 'Add Title':
                    num_requests = round(float(num_requests / 5), 4)
                elif project_name == 'Refresh Jobs':
                    num_requests = round(float(num_requests / 5), 4)
                usage_results[project_name] = num_requests

            date_obj['usage_results'] = usage_results
            final_data.append(date_obj)

        return final_data

    except Exception as e:
        print(e)
        capture_exception(e)
        return None


def merge_openai_usage(
    completions: list[dict],
    embeddings: list[dict],
    ndigits: int = 4
) -> list[dict]:
    """
    Merge usage rows from completions and embeddings by (start_date, end_date).
    For each date bucket, combine project keys. If a project appears in both,
    the value is the average; if it appears in only one, keep that value.

    Parameters:
        completions: output of get_openai_completion_usage(...)
        embeddings:  output of get_openai_embedding_usage(...)
        ndigits:     rounding precision for values (default 4)

    Returns:
        List[dict] shaped like the inputs:
        [
          {
            "start_date": "YYYY-MM-DD",
            "end_date":   "YYYY-MM-DD",
            "usage_results": { "<Project>": float, ... }
          },
          ...
        ]
    """
    # (start_date, end_date) -> project -> [values...]
    buckets: dict[tuple[str, str], dict[str, list[float]]] = {}

    for row in chain(completions or [], embeddings or []):
        key = (row["start_date"], row["end_date"])
        proj_map = buckets.setdefault(key, defaultdict(list))
        for project, value in (row.get("usage_results") or {}).items():
            # ensure numeric, then collect for averaging
            proj_map[project].append(float(value))

    # Build merged list, sorted by start_date/end_date
    merged: list[dict] = []
    for (start_date, end_date) in sorted(buckets.keys()):
        proj_map = buckets[(start_date, end_date)]
        usage_results = {
            project: round(sum(vals) / len(vals), ndigits)
            for project, vals in proj_map.items()
        }
        merged.append({
            "start_date": start_date,
            "end_date": end_date,
            "usage_results": usage_results
        })

    return merged



def get_openai_costs(days_back: int = 2):
    """
    Fetches OpenAI cost data for the past `days_back` days.

    :param days_back: Number of days back from now.
    :return: Dict of cost data or None if error.
    """
    try:
        start_time, end_time = _unix_range_for_days_back(days_back)
        params = {
            "start_time": start_time,
            "end_time": end_time,
            "bucket_width": "1d",
            "limit": 30,
            "group_by": ["project_id"]
        }

        url = f"{OPENAI_COSTS_BASE}"
        response = requests.get(url, headers=_auth_headers(), params=params, timeout=30)
        final_data = []
        data = response.json()['data']
        projects = get_projects()

        for dat in data:
            date_obj = {'start_date': datetime.fromtimestamp(int(dat['start_time']), timezone.utc).strftime("%Y-%m-%d"),
                        'end_date': datetime.fromtimestamp(int(dat['end_time']), timezone.utc).strftime("%Y-%m-%d")}
            cost_results = {}
            for project in dat['results']:
                project_name = projects[project['project_id']]
                project_cost = project['amount']['value']
                cost_results[project_name] = project_cost

            date_obj['cost_results'] = cost_results
            final_data.append(date_obj)

        return final_data

    except Exception as e:
        print(e)
        capture_exception(e)
        return None


def openai_usage_and_costs(
    days_back: int = 1
) -> list[dict]:
    """
    Merge usage and cost data by date. For each date:
      - For every project in usage_results, add "<Project>Usage" = value
      - For every project in cost_results, add "<Project>Cost" = value
    Dates missing in one list are still included.

    Parameters:
        :param days_back: how many days back to go with the data

    Returns:
        [
          {
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
            "results": { "<Project>Usage": float, "<Project>Cost": float, ... }
          },
          ...
        ]
        :param days_back:
    """
    usage_data = merge_openai_usage(get_openai_completion_usage(days_back), get_openai_embedding_usage(days_back))
    cost_data = get_openai_costs(days_back)

    # Combine both lists into a dict keyed by (start_date, end_date)
    combined = defaultdict(lambda: {"usage_results": {}, "cost_results": {}})

    for row in usage_data or []:
        key = (row["start_date"], row["end_date"])
        combined[key]["usage_results"].update(row.get("usage_results", {}))

    for row in cost_data or []:
        key = (row["start_date"], row["end_date"])
        combined[key]["cost_results"].update(row.get("cost_results", {}))

    # Build merged list
    merged = []
    for (start_date, end_date), vals in sorted(combined.items()):
        merged_entry = {"start_date": start_date, "end_date": end_date, "results": {}}

        # Add usage with renamed keys
        for proj, usage_val in vals["usage_results"].items():
            merged_entry["results"][f"{proj} Usage"] = round(float(usage_val), 4)

        # Add cost with renamed keys
        for proj, cost_val in vals["cost_results"].items():
            merged_entry["results"][f"{proj} Cost"] = float(cost_val)

        merged.append(merged_entry)

    return merged


def add_openai_history():
    """
    Adds a new row to the openai_usage table with the current UTC time and today's openai api usage metrics.

    """
    this_session = Session
    try:
        # Ensure the openai_usage table exists
        this_session.execute(text(f'''
            CREATE TABLE IF NOT EXISTS {openai_usage_table} (
                time TIMESTAMP,
                total_cost FLOAT,
                main_search_cost FLOAT,
                main_search_cost_pr FLOAT,
                message_generation_cost FLOAT,
                message_generation_cost_pr FLOAT,
                add_title_cost FLOAT,
                add_title_cost_pr FLOAT,
                refresh_cost FLOAT,
                refresh_cost_pr FLOAT,
                elasticsearch_embeddings_cost FLOAT               
            )
        '''))

        data = openai_usage_and_costs(1)[0]['results']

        main_search_cost = data.get('Main Search Cost', 0)
        main_search_usage = data.get('Main Search Usage', 0)
        if main_search_usage > 0:
            main_search_cost_pr = float(main_search_cost / main_search_usage)
        else:
            main_search_cost_pr = None

        message_generation_cost = data.get('Message Generation Cost', 0)
        message_generation_usage = data.get('Message Generation Usage', 0)
        if message_generation_usage > 0:
            message_generation_cost_pr = float(message_generation_cost / message_generation_usage)
        else:
            message_generation_cost_pr = None

        add_title_cost = data.get('Add Title Cost', 0)
        add_title_usage = data.get('Add Title Usage', 0)
        if add_title_usage > 0:
            add_title_cost_pr = float(add_title_cost / add_title_usage)
        else:
            add_title_cost_pr = None

        refresh_cost = data.get('Refresh Jobs Cost', 0)
        refresh_usage = data.get('Refresh Jobs Usage', 0)
        if refresh_usage > 0:
            refresh_cost_pr = float(refresh_cost / refresh_usage)
        else:
            refresh_cost_pr = None

        elasticsearch_embeddings_cost = data.get('Elasticsearch Embeddings Cost', 0)

        total_cost = round(float(main_search_cost + message_generation_cost + add_title_cost + refresh_cost + elasticsearch_embeddings_cost), 4)


        # Insert a new row with the current metrics
        this_session.execute(text(f'''
            INSERT INTO {openai_usage_table} (time, total_cost, main_search_cost, main_search_cost_pr, message_generation_cost,
                message_generation_cost_pr, add_title_cost, add_title_cost_pr, refresh_cost, refresh_cost_pr,
                elasticsearch_embeddings_cost)
            VALUES (:time, :total_cost, :main_search_cost, :main_search_cost_pr, :message_generation_cost,
                :message_generation_cost_pr, :add_title_cost, :add_title_cost_pr, :refresh_cost, :refresh_cost_pr,
                :elasticsearch_embeddings_cost)
        '''), {
            'time': datetime.now(timezone.utc),
            'total_cost': total_cost,
            'main_search_cost': main_search_cost,
            'main_search_cost_pr': main_search_cost_pr,
            'message_generation_cost': message_generation_cost,
            'message_generation_cost_pr': message_generation_cost_pr,
            'add_title_cost': add_title_cost,
            'add_title_cost_pr': add_title_cost_pr,
            'refresh_cost': refresh_cost,
            'refresh_cost_pr': refresh_cost_pr,
            'elasticsearch_embeddings_cost': elasticsearch_embeddings_cost
        })

        this_session.commit()
        this_session.remove()
        return True
    except Exception as e:
        capture_exception(e)
        this_session.rollback()
        this_session.remove()
        return False



if __name__ == "__main__":
    print('Open ai api file')


