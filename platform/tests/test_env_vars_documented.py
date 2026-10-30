# Nothing existing: searched platform/tests for ABF_ scans and docs reads; test_cloud_upload_docs, test_job_kinds_docs and test_station_docs pin single sentences, none checks that every ABF_* name the code reads is written in docs/.
"""env-vars-documented: every ABF_* environment variable the platform code reads is named in docs/.
TC ids in the comments. Only reads text files and two constants of jobs.py: no network, no service."""
import re
import sys

from helpers import PLATFORM_DIR, REPO_ROOT

DOCS_DIR = REPO_ROOT / "docs"
SCAN_DIRS = ("abf_platform", "abf_station", "abf_launch")
NAME = re.compile(r"ABF_[A-Z0-9]+(?:_[A-Z0-9]+)*")
# The only name the code has and the docs must not have: a shell variable inside the head script, not a setting.
ALLOWLIST = {"ABF_FORWARD_PORT"}


def _code_names():
    names = set()
    for d in SCAN_DIRS:
        for path in (PLATFORM_DIR / d).rglob("*.py"):
            names |= set(NAME.findall(path.read_text(encoding="utf-8")))
    return names


def _docs_text():
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(DOCS_DIR.glob("*.md")))


def _in(text, name):
    return re.search(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])", text) is not None


def _lines(path):
    return (DOCS_DIR / path).read_text(encoding="utf-8").splitlines()


def test_every_abf_variable_the_code_reads_is_named_in_docs():
    # TC-012, TC-013, TC-016
    docs = _docs_text()
    missing = sorted(n for n in _code_names() - ALLOWLIST if not _in(docs, n))
    assert not missing, "ABF_* names the code reads but docs/ never names: " + ", ".join(missing)


def test_the_allowlist_has_exactly_one_entry():
    # TC-014
    assert ALLOWLIST == {"ABF_FORWARD_PORT"}


def test_the_scan_finds_the_names_it_should():
    # TC-015
    found = _code_names()
    assert {"ABF_PLATFORM_DEADLINE_PREFLIGHT", "ABF_STATION_UPLOADS", "ABF_PLATFORM_DB"} <= found
    assert "ABF_FORWARD_PORT" in found


def test_deadline_table_covers_every_job_kind():
    # TC-001, TC-002, TC-003, TC-009
    sys.path.insert(0, str(PLATFORM_DIR))
    from abf_platform import jobs
    lines = _lines("PLATFORM.md")
    for kind, seconds in jobs.DEADLINE_SECONDS.items():
        env = jobs._DEADLINE_ENV[kind]
        ok = any(_in(ln, env) and re.search(r"(?<![0-9])%d(?![0-9])" % seconds, ln) for ln in lines)
        assert ok, f"docs/PLATFORM.md has no line with {env} and {seconds} (job kind {kind})"


def test_the_two_station_timeouts_are_described_with_unit_and_default():
    # TC-004, TC-005
    lines = _lines("PLATFORM.md")
    put = [ln for ln in lines if _in(ln, "ABF_STATION_PUT_TIMEOUT")]
    assert put and any(re.search(r"(?<![0-9])3600(?![0-9])", ln) and "second" in ln and "put_upload" in ln for ln in put)
    settle = [ln for ln in lines if _in(ln, "ABF_STATION_GCB_SETTLE_SECONDS")]
    assert settle and any(re.search(r"(?<![0-9.])5(?![0-9])", ln) and "second" in ln for ln in settle)
    assert any("Settings that only the tests change" in ln and "ABF_PLATFORM_DEADLINE_PIPELINE_FILES" in ln for ln in lines)


def test_station_uploads_is_explained_where_the_web_upload_is():
    # TC-006, TC-007
    hits = [ln for ln in _lines("OPERATIONS.md") if _in(ln, "ABF_STATION_UPLOADS")]
    assert hits, "docs/OPERATIONS.md never names ABF_STATION_UPLOADS"
    good = [ln for ln in hits if "abf-station" in ln and ("ABF_PLATFORM_UPLOADS" in ln or "uploads_root" in ln)]
    assert good, "no line names ABF_STATION_UPLOADS together with abf-station and the platform's upload folder"
    assert any("這個代理沒有設定上傳資料夾（ABF_STATION_UPLOADS）" in ln for ln in good)
    assert any("/upload" in ln for ln in good)


def test_names_kept_out_of_the_docs():
    # TC-020, TC-024
    for p in DOCS_DIR.glob("*.md"):
        assert "ABF_FORWARD_PORT" not in p.read_text(encoding="utf-8"), p.name
    ops = (DOCS_DIR / "OPERATIONS.md").read_text(encoding="utf-8")
    assert "ABF_STATION_PUT_TIMEOUT" not in ops and "ABF_STATION_GCB_SETTLE_SECONDS" not in ops
