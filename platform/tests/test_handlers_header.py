# Nothing existing: the handlers tests check what each job kind does; none checks that the header comment on line 1 still matches JOB_KINDS, so this reads the source text only.
"""Line 1 of abf_station/handlers.py must describe the job kinds as they are (reads text only)."""
import ast
from pathlib import Path

HANDLERS = Path(__file__).resolve().parent.parent / "abf_station" / "handlers.py"
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
         9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen"}


def _first_line():
    return HANDLERS.read_text(encoding="utf-8").splitlines()[0].lower()


def _kind_count():
    tree = ast.parse(HANDLERS.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "JOB_KINDS" for t in node.targets):
            return len(node.value.elts)
    raise AssertionError("JOB_KINDS not found")


def test_first_line_does_not_claim_read_only():
    # TC-001, TC-016
    assert "read-only" not in _first_line()


def test_first_line_does_not_claim_two_handlers():
    # TC-002, TC-016
    line = _first_line()
    assert "two built-in" not in line
    assert "two handler" not in line


def test_first_line_names_the_job_kind_count():
    # TC-003, TC-015: the expected word comes from JOB_KINDS, not written here
    assert WORDS[_kind_count()] in _first_line()


def test_first_line_keeps_its_reason():
    # TC-004
    assert _first_line().startswith("# not ansible modules or celery tasks")


def test_job_kinds_count_is_pinned():
    # TC-005: add or drop a kind and this goes red, a reminder to fix line 1 too
    assert _kind_count() == 9
