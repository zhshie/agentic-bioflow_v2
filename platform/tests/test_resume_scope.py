# Nothing existing: tests that 009e did what it says it would not do (no web page, no automatic resume, no third kind of confirmation, one file that submits); the limits are ours.
"""009e: what was left out, and the invariants that must not move (constitution I.2, the three channels, the hand-off record as a record).
Test cases are named in the comments (TC-146 ...), see specs/009e-resume-relaunch/test-case.md."""
import ast
import re
import sqlite3
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT

PKG = PLATFORM_DIR


def source_files():
    """The platform's own code: no tests, no packaged copy of the skills."""
    return sorted(p for p in PKG.rglob("*.py") if "tests" not in p.relative_to(PKG).parts and "build" not in p.relative_to(PKG).parts)


def rel(p):
    return p.relative_to(PKG).as_posix()


def code_lines(p):
    """The lines of a file that are not comments."""
    return [ln for ln in p.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#")]


def test_tc146_there_is_no_web_page_no_stage_board_no_button_and_no_list_attempts():
    # TC-146 (011 does these)
    web = (PKG / "abf_platform" / "web.py").read_text(encoding="utf-8")
    assert not re.search(r"resume|relaunch|attempt", web, re.I)
    for p in source_files():
        text = p.read_text(encoding="utf-8")
        assert "list_attempts" not in text, rel(p)
    from abf_platform import web as web_mod
    assert not [n for n in dir(web_mod) if re.search(r"resume|relaunch|attempt", n, re.I)]


def test_tc150_nothing_calls_a_resume_or_a_relaunch_by_itself():
    # TC-150: the only callers are the two doors that ask a person (the MCP tools and the terminal commands), and the code that builds
    callers = {"request_resume", "request_relaunch", "prepare_resume", "prepare_relaunch", "render_resume", "render_resume_bundle"}
    allowed = {"abf_platform/actions/__init__.py", "abf_platform/mcp_server.py", "abf_launch/cli.py", "abf_launch/build.py",
               "abf_station/launch.py"}
    found = set()
    for p in source_files():
        names = {n.attr if isinstance(n, ast.Attribute) else n.id for n in ast.walk(ast.parse(p.read_text(encoding="utf-8")))
                 if isinstance(n, (ast.Attribute, ast.Name))}
        names |= {n.name for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        if names & callers:
            found.add(rel(p))
    assert found <= allowed, found - allowed
    for quiet in ("abf_platform/receiver.py", "abf_platform/jobs.py", "abf_platform/agents.py", "abf_platform/status.py",
                  "abf_platform/rebuild.py", "abf_platform/web.py", "abf_station/agent.py", "abf_station/handlers.py"):
        assert quiet not in found, quiet


def test_tc154_tc161_there_are_still_three_channels_two_kinds_of_confirmation_and_two_kinds_of_job():
    # TC-154, TC-161
    from abf_platform import actions, confirm, jobs, store
    channels = [n for n, v in vars(actions).items() if isinstance(v, actions._Channel)]
    assert sorted(channels) == ["ELICITED", "PAGE", "TERMINAL"]
    text = (PKG / "abf_platform" / "actions" / "__init__.py").read_text(encoding="utf-8")
    assert len(re.findall(r"_Channel\(", text)) == 3          # the three singletons; nothing else is made
    assert confirm.JOB_KIND == {"launch": "launch_nextflow", "cancel": "cancel_run"}
    assert jobs.CONFIRMED == {"launch_nextflow": "launch", "cancel_run": "cancel"}
    assert jobs.KINDS == ("preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records")
    assert store.STATE_SCHEMA.count("kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel'))") == 1


def test_tc161_the_confirmation_table_of_a_new_file_takes_no_third_kind(tmp_path):
    from abf_platform import store
    db = tmp_path / "platform.db"
    store.connect_state(db).close()
    con = sqlite3.connect(str(db))
    for kind in ("resume", "relaunch", "retry", ""):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('i', 's', ?, 1)", (kind,))
    con.close()


def test_tc157_the_words_that_start_nextflow_are_in_one_file_of_the_platform():
    # TC-157
    found = sorted(rel(p) for p in source_files() if re.search(r"nextflow run|-resume", "\n".join(code_lines(p))))
    assert found == ["abf_station/launch.py"], found


def test_tc158_the_one_file_that_submits_is_still_the_only_entry_and_its_refusal_tests_are_in_one_file():
    # TC-158
    script = (REPO_ROOT / "tests" / "no_second_run_state_test.sh").read_text(encoding="utf-8")
    block = script[script.index('LAUNCH_ALLOW="\n') + len('LAUNCH_ALLOW="\n'):]
    entries = [ln for ln in block[:block.index('"\n')].splitlines() if ln.strip()]
    assert len(entries) == 1 and entries[0].startswith(
        "platform/abf_station/launch.py|platform/tests/test_station_launch.py::test_unconfirmed_launch_is_refused|")
    tree = ast.parse((PKG / "tests" / "test_station_launch.py").read_text(encoding="utf-8"))
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert {"test_unconfirmed_launch_is_refused", "test_unconfirmed_resume_is_refused"} <= names


def test_tc159_no_file_but_the_agents_launch_calls_sbatch():
    # TC-159
    for p in source_files():
        if rel(p) == "abf_station/launch.py":
            continue
        assert not re.search(r"\bsbatch\b|\bsrun\b", "\n".join(code_lines(p))), rel(p)


def test_tc160_no_state_of_a_run_is_written_anywhere_after_a_round_of_resumes_and_relaunches(tmp_path, monkeypatch):
    # TC-160
    from resume_harness import Rig
    rig = Rig(tmp_path, monkeypatch)
    rig.first("x")
    rig.attempt("resume", "x")
    rig.attempt("relaunch", "x-a2", status="succeeded")
    for table, in rig.sql("SELECT name FROM sqlite_master WHERE type = 'table'"):
        cols = [r[1] for r in rig.sql("PRAGMA table_info(%s)" % table)]
        if table in ("launches",):
            assert not [c for c in cols if re.search(r"status|state|phase|result|exit|progress|ended|fail|success|resumed|cancel(?!_requested_at)", c)], cols
    dump = ""
    for row in rig.sql("SELECT * FROM launches"):
        dump += " ".join(str(v) for v in tuple(row))
    assert not re.search(r"resumed|failed|cancelled|canceled|succeeded|已續跑|已取消", dump)
    for f in source_files():
        text = "\n".join(code_lines(f))
        assert not re.search(r"['\"](resumed|cancelled|canceled|已取消|已續跑)['\"]", text), rel(f)


def test_tc152_the_clean_up_of_finished_jobs_was_not_made_longer():
    # TC-152 (the behaviour is in test_resume_platform)
    from abf_platform import confirm, jobs
    assert jobs.PRUNE_AFTER_SECONDS == 7 * 86400 and confirm.KEEP_CONTENT_SECONDS == 7 * 86400


def test_tc155_the_token_of_a_run_is_still_for_one_run_name_and_has_no_attempt():
    # TC-155
    text = (PKG / "abf_platform" / "store.py").read_text(encoding="utf-8")
    tokens = text[text.index("CREATE TABLE IF NOT EXISTS tokens"):]
    tokens = tokens[:tokens.index(");")]
    assert "run_name" in tokens and not re.search(r"attempt|parent|resume", tokens)
