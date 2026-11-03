# Nothing existing: no earlier test runs the agent's lint_pipeline job; nf-core's own lint is replaced here by a stand-in.
"""017c2a, the agent side of the optional lint (TC-020 ... TC-042, TC-044, TC-104, TC-105): the agent writes the project into a private
folder, runs one fixed command on its own host and boils the answer down. `lint.WHICH` and `lint.RUN` are the only places that look for
or start a program; every test replaces both, and an autouse guard makes a test that forgets fail instead of starting anything."""
import json
import os
import re
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from abf_station import handlers, lint

STATION = Path(__file__).resolve().parent.parent / "abf_station"
PROJECT = {"main.nf": "workflow {}\n", "conf/base.config": "process {}\n", "modules.json": "{}\n"}
CTX = SimpleNamespace(site=None, settings_file="", platform_url="", agent_name="agent-f", job_started=time.monotonic())


class Stand:
    """Stands in for WHICH and RUN: records every call, can write the JSON file, raise, or return a code."""

    def __init__(self):
        self.found = True
        self.calls = []
        self.doc = None
        self.code = 0
        self.text = ""
        self.boom = None
        self.seen = {}

    def which(self, name):
        return "/usr/bin/nf-core" if self.found else None

    def run(self, argv, env, timeout):
        self.calls.append({"argv": list(argv), "env": dict(env), "timeout": timeout})
        root = argv[argv.index("--dir") + 1]
        files = {}
        for folder, _, names in os.walk(root):
            for name in names:
                with open(os.path.join(folder, name), encoding="utf-8", newline="") as handle:
                    files[os.path.relpath(os.path.join(folder, name), root).replace(os.sep, "/")] = handle.read()
        self.seen = {"root": root, "files": files}
        if self.boom is not None:
            raise self.boom
        if self.doc is not None:
            with open(argv[argv.index("--json") + 1], "w", encoding="utf-8") as handle:
                handle.write(self.doc if isinstance(self.doc, str) else json.dumps(self.doc))
        return self.code, self.text


@pytest.fixture(autouse=True)
def stand(monkeypatch):
    s = Stand()
    monkeypatch.setattr(lint, "WHICH", s.which)
    monkeypatch.setattr(lint, "RUN", s.run)
    return s


def job(project=None, **extra):
    args = {"name": "demo", "version": 1, "project": PROJECT if project is None else project}
    args.update(extra)
    return {"id": 1, "kind": "lint_pipeline", "args": args}


def go(project=None, **extra):
    return handlers.handle(job(project, **extra), CTX)


def doc(passed=5, warned=1, failed=0):
    return {"tests_pass": [["c%d" % i, "ok %d" % i] for i in range(passed)],
            "tests_warned": [["w%d" % i, "warn"] for i in range(warned)], "tests_failed": [["f%d" % i, "bad"] for i in range(failed)],
            "num_tests_pass": passed, "num_tests_warned": warned, "num_tests_failed": failed}


def test_not_installed_is_unavailable(stand):
    # TC-020
    stand.found = False
    state, res = go()
    assert state == "done" and res["ok"] is False and res["status"] == "unavailable" and "不會自動安裝" in res["reason"] and stand.calls == []


def test_passed_and_failed_from_json(stand):
    # TC-021, TC-022
    stand.doc = doc(5, 1, 0)
    state, res = go()
    assert state == "done" and res["status"] == "passed" and res["counts"] == {"passed": 5, "warned": 1, "failed": 0}
    stand.doc = doc(3, 2, 4)
    state, res = go()
    assert res["status"] == "failed" and res["counts"] == {"passed": 3, "warned": 2, "failed": 4} and "f0：bad" in res["report"]


def test_report_has_the_first_fifty(stand):
    # TC-023
    stand.doc = doc(0, 0, 80)
    state, res = go()
    lines = res["report"].splitlines()
    assert len(lines) == 50 and lines[0] == "f0：bad" and all("：" in line for line in lines)


def test_command_is_exact(stand, monkeypatch):
    # TC-024, TC-025, TC-026, TC-027
    stand.doc = doc()
    monkeypatch.setenv("SECRET_FAKE_VAR", "x")
    go()
    call = stand.calls[0]
    argv = call["argv"]
    assert argv[:3] == ["nf-core", "pipelines", "lint"] and argv[3] == "--dir" and argv[5] == "--json" and len(argv) == 7
    assert argv[4] == stand.seen["root"] and not argv[6].startswith(argv[4] + os.sep)
    assert call["timeout"] <= 240
    assert set(call["env"]) <= {"PATH", "HOME", "LANG"}
    for part in argv:
        assert not any(w in part for w in ("sbatch", "srun", "ssh", "nextflow"))


def test_timeout_and_crash_are_errors(stand):
    # TC-028, TC-029
    class TimeoutExpired(Exception):
        pass
    for boom in (TimeoutError("late"), TimeoutExpired("late"), OSError("no exec")):
        stand.boom = boom
        state, res = go()
        assert state == "done" and res["status"] == "error" and res["reason"]
        assert "Traceback" not in res["reason"] and stand.seen["root"] not in res["reason"] and "abf-lint-" not in res["reason"]


def test_failing_code_without_json_is_error(stand):
    # TC-030
    stand.code = 2
    state, res = go()
    assert res["status"] == "error" and res["reason"] and stand.seen["root"] not in res["reason"] and "Traceback" not in res["reason"]


def test_zero_code_without_json_is_the_tail(stand):
    # TC-031
    stand.text = "\n".join("line %d" % i for i in range(100)) + "\n"
    state, res = go()
    lines = res["report"].splitlines()
    assert res["status"] == "passed" and len(lines) == 40 and lines[-1] == "line 99" and lines[0] == "line 60" and len(res["report"]) <= 8000


def test_files_written_and_removed(stand):
    # TC-032, TC-033, TC-034
    stand.doc = doc()
    go()
    assert stand.seen["files"] == PROJECT and not os.path.exists(stand.seen["root"])
    stand.boom = OSError("x")
    go()
    assert not os.path.exists(stand.seen["root"])


@pytest.mark.parametrize("project", [
    {"../x": "a"}, {"/etc/passwd": "a"}, {"a\x00b": "a"}, {"d" * 513: "a"}, {"a/./b": "a"}, {"a\\b": "a"}, {"": "a"}])
def test_bad_paths_are_refused(stand, project):
    # TC-035, TC-036, TC-037, TC-038
    state, res = go(project)
    assert state == "refused" and stand.calls == [] and stand.seen == {}


def test_too_big_or_too_many_are_refused(stand):
    # TC-039, TC-040
    state, res = go({"a": "x" * (lint.MAX_BYTES + 1)})
    assert state == "refused" and stand.calls == []
    state, res = go({"f%d" % i: "" for i in range(lint.MAX_FILES + 1)})
    assert state == "refused" and stand.calls == []


def test_handlers_register_the_kind():
    # TC-041
    from abf_platform import jobs
    assert handlers.JOB_KINDS[-1] == "lint_pipeline" and handlers.ARG_KEYS["lint_pipeline"] == {"name", "version", "project"}
    assert set(handlers.JOB_KINDS) == set(jobs.KINDS)


def test_extra_argument_is_refused(stand):
    # TC-042
    state, res = go(extra="x")
    assert state == "refused" and stand.calls == []


def test_end_to_end_with_the_platform(tmp_path, monkeypatch, stand):
    # TC-044
    from human_harness import World
    from owner_harness import Duo, sql_rows
    from test_pipelines_validation import make, pid_of, pl
    from abf_platform import jobs
    d = Duo(World(tmp_path, monkeypatch))
    pid = pid_of(make(d, d.a))
    r = pl().validate_pipeline(d.state, pid, caller=d.a, lint=True)
    claimed = jobs.claim(d.state, "agent-t", time.time)
    while claimed["kind"] != "lint_pipeline":
        claimed = jobs.claim(d.state, "agent-t", time.time)
    assert claimed["id"] == r["lint"]["job_id"] and claimed["kind"] == "lint_pipeline"
    stand.doc = doc(3, 0, 2)
    state, result = handlers.handle(claimed, CTX)
    code, _ = jobs.take_result(d.state, "agent-t", claimed["id"], state, result, time.time)
    assert code == 200 and sql_rows(d.state, "SELECT state FROM jobs WHERE id = ?", (claimed["id"],))[0]["state"] == "done"
    got = pl().get_validation(d.state, pid, caller=d.a)["validation"]["lint"]
    assert got["status"] == "failed" and got["report"].splitlines()[0] == "通過 3／警告 0／失敗 2 (passed 3 / warned 0 / failed 2)"
    assert "f0：bad" in got["report"]


def test_no_install_or_download_in_the_source():
    # TC-104
    code = (STATION / "lint.py").read_text(encoding="utf-8")
    for word in ("pip", "conda", "install", "urllib", "requests"):
        assert not re.search(r"(?<![A-Za-z_])%s(?![A-Za-z_])" % word, code), word


def test_never_sent_to_the_cluster():
    # TC-105
    code = (STATION / "lint.py").read_text(encoding="utf-8")
    for word in ("sbatch", "srun", "ssh"):
        assert not re.search(word, code), word
