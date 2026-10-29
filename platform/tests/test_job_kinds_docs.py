# Nothing existing: the kind tests (test_byte_channel_a/b) check the list and its order, none checks that the prose in jobs.py and store.py still names every kind and counts them right.
"""job-kinds-stale-docs: the words about the job kinds must keep up with the code. Reads source text and constants only."""
import re
from pathlib import Path

from abf_platform import jobs, store

_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
            "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15}


def test_jobs_module_doc_names_every_job_kind():
    # TC-001, TC-015
    missing = [k for k in jobs.KINDS if "`%s`" % k not in jobs.__doc__]
    assert not missing, "jobs.py opening text does not name: %s" % missing


def test_jobs_module_doc_counts_the_kinds_that_need_a_confirmation():
    # TC-002, TC-003
    assert len(jobs.CONFIRMED) == 3
    assert "those two kinds" not in jobs.__doc__


def test_store_comment_counts_the_job_kinds():
    # TC-009, TC-015
    text = Path(store.__file__).read_text(encoding="utf-8")
    m = re.search(r"exactly (\w+) job kinds", text)
    assert m, "store.py no longer says 'exactly N job kinds'"
    assert _NUMBERS.get(m.group(1).lower()) == len(jobs.KINDS)


def test_store_check_constraint_lists_the_same_kinds_as_jobs():
    # TC-012
    lists = [x for x in re.findall(r"kind\s+IN\s*\(([^)]*)\)", store.STATE_SCHEMA) if "'preflight'" in x]
    assert len(lists) == 1
    assert set(re.findall(r"'(\w+)'", lists[0])) == set(jobs.KINDS)


def test_handlers_and_jobs_agree_on_the_kinds():
    # TC-013
    from abf_station import handlers
    assert set(handlers.JOB_KINDS) == set(jobs.KINDS)
