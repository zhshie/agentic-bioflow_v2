"""Read-only door for the web pages to the refusal record of a launch (refusal-visibility).

The web layer may not import `jobs` (tests/test_web_parity.py TC-H16f), and `actions/__init__.py` is not touched by this slice, so
the two reads the pages need go through here. Nothing is written; every function only forwards to the jobs.py helpers.
"""
from . import jobs


def refusal_of(state_path, job_id):
    return jobs.refusal_of(state_path, job_id)


def latest_refusal(state_path, user_id, now):
    return jobs.latest_refusal(state_path, user_id, now)
