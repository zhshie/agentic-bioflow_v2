# Nothing existing: the MCP door of actions.request_pipeline_launch had no test; no tool joined a saved canvas pipeline to a person's yes.
"""launch-pipeline-mcp: the tool launch_pipeline only asks. Test cases TC-001 ... TC-032 are named in the comments
(specs/launch-pipeline-mcp/test-case.md)."""
import asyncio
import csv
import io
import json
import re
import sqlite3
import subprocess
from pathlib import Path

import pytest

from human_harness import World, csrf_of, form_answer, pending_id_of
from owner_harness import Duo, sql_rows
from helpers import tool_json, tool_text

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "abf_platform"
FIXTURES = HERE / "fixtures" / "compose"
BAD = {"nodes": [{"id": "qc", "module": "fastqc"}, {"id": "s", "module": "samtools_sort"}],
       "edges": [{"from": {"node": "qc", "output": "html"}, "to": {"node": "s", "input": 2}}]}
BANNED = ("approve", "confirm", "confirmed_by", "void", "yes")


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


@pytest.fixture
def d(w):
    return Duo(w)


def qc_graph():
    return json.loads((FIXTURES / "fastqc_multiqc" / "graph.json").read_text(encoding="utf-8"))


def make(d, caller=None, name="demo-qc", graph=None):
    from abf_platform.actions import pipelines
    out = pipelines.create_pipeline(d.state, name=name, graph=graph if graph is not None else qc_graph(), caller=caller or d.a)
    assert out["ok"], out
    return out["pipeline"]["id"]


def sheet(d, caller, n=2):
    area = d.area(caller)
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(("sample", "reads"))
    for i in range(1, n + 1):
        wr.writerow(["s%02d" % i, "%s/rawdata/s%02d_R1.fastq.gz" % (area, i)])
    return buf.getvalue()


def args(d, caller, pid, **over):
    a = {"pipeline_id": pid, "run_name": "run-one", "samplesheet_text": sheet(d, caller), "ce_name": d.w.env_for(caller)}
    a.update(over)
    return a


def lp(d, caller, pid, answer=None, **over):
    _, outs = d.w.mcp([("launch_pipeline", args(d, caller, pid, **over))], caller=caller, answer=answer, raw=True)
    return outs[0]


def count(d, table, where=""):
    try:
        return sql_rows(d.state, "SELECT COUNT(*) AS n FROM %s %s" % (table, where))[0]["n"]
    except sqlite3.OperationalError:
        return 0


def counts(d):
    return tuple(count(d, t) for t in ("jobs", "confirmations", "launches"))


def launch_jobs(d):
    return count(d, "jobs", "WHERE kind = 'launch_nextflow'")


def tools_of(w):
    tools, _ = w.mcp([], caller=None)
    return {t.name: t for t in tools}


def clean(text):
    return "Traceback" not in text and "SELECT " not in text and not re.search(r"[A-Za-z]:\\|/home/|/mnt/", text)


# ---- US1 ----
def test_tool_exists_and_is_a_write_tool(w):
    # TC-001
    a = tools_of(w)["launch_pipeline"].annotations
    assert a.read_only_hint is False and a.destructive_hint is False


def test_asks_only_and_matches_launch_shape(d):
    # TC-002, TC-003
    pid = make(d)
    before = counts(d)
    out = tool_json(lp(d, d.a, pid))
    assert out["sent"] is False and out["state"] == "pending" and "/c/" in out["confirmation_url"]
    assert launch_jobs(d) == 0 and count(d, "launches") == before[2]
    assert counts(d)[1] == before[1] + 1
    ref = d.launch(d.a, run="run-two")
    assert set(ref) == set(out)
    assert out["message"].strip()


def test_parameter_names(w):
    # TC-004, TC-005
    sch = tools_of(w)["launch_pipeline"].input_schema
    assert set(sch["properties"]) == {"pipeline_id", "version", "run_name", "samplesheet", "samplesheet_text", "ce_name", "params"}
    assert set(sch["required"]) == {"pipeline_id", "run_name"}
    assert not [p for p in sch["properties"] if re.search("confirm|approve|yes|void", p, re.I)]


def test_goes_through_the_action_layer_with_this_calls_identity(d, monkeypatch):
    # TC-006
    from abf_platform import actions
    seen = []

    async def fake(platform_path, **kw):
        seen.append(kw)
        return {"ok": True, "sent": False, "state": "pending", "message": "m"}

    monkeypatch.setattr(actions, "request_pipeline_launch", fake)
    lp(d, d.a, 7, version=2)
    assert len(seen) == 1
    kw = seen[0]
    assert kw["pipeline_id"] == 7 and kw["version"] == 2 and kw["run_name"] == "run-one"
    assert kw["caller"] is not None and kw["caller"].user_id == d.a.user_id and "remote" in kw and "person" in kw
    assert "confirmed_by" not in kw


def test_form_declined_sends_nothing(d):
    # TC-007
    pid = make(d)
    out = tool_json(lp(d, d.a, pid, answer=form_answer(action="decline", content=None)))
    assert out["sent"] is False and launch_jobs(d) == 0


def test_form_accepted_queues_a_job(d):
    # TC-008
    pid = make(d)
    out = tool_json(lp(d, d.a, pid, answer=form_answer()))
    assert out["sent"] is True and out["job_id"]
    assert launch_jobs(d) == 1


def test_same_call_after_the_page_yes_returns_the_job(d):
    # TC-009
    from abf_platform import actions
    pid = make(d)
    out = tool_json(lp(d, d.a, pid))
    _, job = actions.approve(d.state, out["id"], confirmed_by=actions.PAGE, caller=d.a)
    again = tool_json(lp(d, d.a, pid))
    assert again["job_id"] == job and again["state"] == "queued"
    assert launch_jobs(d) == 1 and count(d, "confirmations") == 1


# ---- US2 ----
def test_other_user_gets_not_found_and_nothing_is_written(d):
    # TC-010, TC-011
    d.bobs_environment()
    pid = make(d, name="alices-secret-qc")
    before = counts(d)
    other = tool_json(lp(d, d.b, pid, ce_name="b1", samplesheet_text=sheet(d, d.b)))
    ghost = tool_json(lp(d, d.b, 424242, ce_name="b1", samplesheet_text=sheet(d, d.b)))
    assert other["ok"] is False
    assert other["message"].replace(str(pid), "<n>") == ghost["message"].replace("424242", "<n>")
    assert "alices-secret-qc" not in json.dumps(other)
    assert counts(d) == before


def test_missing_version_is_a_plain_error(d):
    # TC-012
    pid = make(d)
    before = counts(d)
    res = lp(d, d.a, pid, version=9)
    out = tool_json(res)
    assert out["ok"] is False and out["message"].startswith("未送出：") and clean(tool_text(res))
    assert counts(d) == before


def test_unvalidated_pipeline_is_a_plain_error(d):
    # TC-013
    pid = make(d, graph=BAD)
    before = counts(d)
    res = lp(d, d.a, pid)
    out = tool_json(res)
    assert out["ok"] is False and out["sent"] is False and out["message"].strip() and clean(tool_text(res))
    assert counts(d) == before


def test_no_secret_in_responses_or_logs(d, caplog):
    # TC-014: real secrets exist (a personal access token for each person, the web password); none may show up. The
    # secrets are first proven real (made in the token store), so the check below can fail.
    from abf_platform import store
    from human_harness import PASSWORD
    caplog.set_level("DEBUG")
    pid = make(d)
    d.bobs_environment()
    secrets_ = [store.create_token(d.w.ip.tokens, kind="pat", user_id=c.user_id, label="tc014") for c in (d.a, d.b)]
    secrets_.append(PASSWORD)
    assert secrets_[0].startswith("abf_pat_") and all(len(x) >= 12 for x in secrets_)
    assert store.lookup_pat(d.w.ip.tokens, secrets_[0]) is not None
    texts = [tool_text(lp(d, d.a, pid)), tool_text(lp(d, d.b, pid, ce_name="b1", samplesheet_text=sheet(d, d.b))),
             tool_text(lp(d, d.a, pid, version=9)), tool_text(lp(d, d.a, 424242))]
    for t in texts + [caplog.text]:
        assert clean(t)
        for secret in secrets_:
            assert secret not in t


# ---- US3 ----
def test_request_tools_has_it():
    # TC-015
    from abf_platform.actions import chat_tools
    assert {"launch", "cancel", "resume", "relaunch", "forget", "launch_pipeline"} <= chat_tools.REQUEST_TOOLS


def test_classify_check_accepts_the_real_list(w):
    # TC-016
    from abf_platform.actions import chat_tools
    chat_tools.classify_check(list(tools_of(w).values()))


def test_chat_spec_has_it_from_the_server(w):
    # TC-017, TC-019
    from abf_platform.actions import chat_tools
    specs = asyncio.run(chat_tools.tool_specs(w.ip.index))
    s = next(x for x in specs if x["name"] == "launch_pipeline")
    t = tools_of(w)["launch_pipeline"]
    assert s["description"] == t.description and s["input_schema"] == t.input_schema
    for x in specs:
        assert not re.search("approve|confirm|void|yes", x["name"], re.I)
        assert not [p for p in x["input_schema"].get("properties", {}) if re.search("approve|confirm|void|yes", p, re.I)]


def test_prompt_mentions_it_without_banned_words():
    # TC-018
    from abf_platform.actions import chat_tools
    p = chat_tools.CHAT_SYSTEM_PROMPT
    assert "launch_pipeline" in p
    for word in BANNED:
        assert word not in p.lower()


def test_classify_check_still_rejects_an_unlisted_tool(w):
    # TC-020
    from abf_platform.actions import chat_tools

    class T:
        name = "wipe_everything"
        annotations = None

    with pytest.raises(ValueError, match="wipe_everything"):
        chat_tools.classify_check(list(tools_of(w).values()) + [T()])


# ---- US4 / out of scope ----
def test_tool_count_and_no_extra_tools(w):
    # TC-021, TC-026
    t = tools_of(w)
    assert len(t) == 23 and sum(1 for x in t.values() if x.annotations.read_only_hint) == 15      # ruling R2: get_run is no longer read-only
    for n in ("create_pipeline", "update_pipeline", "export_pipeline", "validate_pipeline"):
        assert n not in t
    doc = (PKG / "mcp_server.py").read_text(encoding="utf-8")
    assert "five tools that ask" not in doc and "launch_pipeline" in doc.split('"""')[1]


def test_no_web_route_for_it(d, w):
    # TC-027
    client = w.web()
    assert w.login(client, "bob").status_code == 303
    assert client.post("/act/launch_pipeline", data={}).status_code in (404, 405)


SCHEMA_PATHS = ["migrations", "abf_platform/store.py", "abf_platform/schema.sql"]


def schema_diff(cwd, base="origin/v3"):
    # three dots: compare with the merge-base, so only the branch's own changes count
    return subprocess.run(["git", "diff", "--stat", base + "...HEAD", "--"] + SCHEMA_PATHS,
                          cwd=str(cwd), capture_output=True, text=True).stdout


def _git(cwd, *a):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a], cwd=str(cwd), check=True,
                   capture_output=True)


def _repo(tmp_path):
    r = tmp_path / "r"
    (r / "migrations").mkdir(parents=True)
    (r / "abf_platform").mkdir()
    (r / "migrations" / "001.sql").write_text("a\n")
    (r / "abf_platform" / "store.py").write_text("a\n")
    (r / "abf_platform" / "schema.sql").write_text("a\n")
    _git(r, "init", "-q")
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "base")
    return r


def _commit_file(r, rel, text):
    (r / rel).write_text(text)
    _git(r, "add", "-A")
    _git(r, "commit", "-qm", "c " + rel)


def test_schema_pin_ignores_base_advance(tmp_path):
    # TC-001: base moved on after the branch was cut; the branch itself touched nothing
    r = _repo(tmp_path)
    _git(r, "branch", "feature")
    _commit_file(r, "abf_platform/schema.sql", "newer\n")
    _commit_file(r, "abf_platform/store.py", "newer\n")
    _git(r, "update-ref", "refs/remotes/origin/v3", "HEAD")
    _git(r, "checkout", "-q", "feature")
    assert schema_diff(r).strip() == ""
    # the old two-dot form would have flagged it
    old = subprocess.run(["git", "diff", "--stat", "origin/v3", "--"] + SCHEMA_PATHS, cwd=str(r),
                         capture_output=True, text=True).stdout
    assert old.strip() != ""


@pytest.mark.parametrize("rel", ["abf_platform/schema.sql", "abf_platform/store.py", "migrations/002.sql"])
def test_schema_pin_still_catches_branch_change(tmp_path, rel):
    # TC-004 / TC-005 / TC-006: a real change on the branch must still show
    r = _repo(tmp_path)
    _git(r, "update-ref", "refs/remotes/origin/v3", "HEAD")
    _git(r, "checkout", "-qb", "feature")
    _commit_file(r, rel, "changed\n")
    assert rel.split("/")[-1] in schema_diff(r)


PUBLISH_FIGURE_STORE_LINES = {
    "# The confirmation kinds are launch, cancel and clean_work (the person's yes to deleting a run's work folder; kept apart so a",
    "# cancel confirmation cannot stand for it). A platform.db made before clean_work gets this table rebuilt by _migrate_confirmation_kinds.",
    "# The confirmation kinds are launch, cancel, clean_work (the person's yes to deleting a run's work folder; kept apart so a",
    "# cancel confirmation cannot stand for it) and publish_figure (the person's yes to adding figures to a run's private gallery; it queues no job).",
    "# A platform.db made before clean_work or publish_figure gets this table rebuilt by _migrate_confirmation_kinds.",
    "kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel', 'clean_work')),",
    "kind TEXT NOT NULL CHECK (kind IN ('launch', 'cancel', 'clean_work', 'publish_figure')),",
    "def figures_root(platform_path=None, env=None):",
    '"""The platform setting `figures_root`: ABF_PLATFORM_FIGURES, else `figures` next to platform.db. The private figure gallery of a run is',
    '<figures_root>/<user id>/<run id>/."""',
    "env = os.environ if env is None else env",
    'if env.get("ABF_PLATFORM_FIGURES"):',
    'return Path(env["ABF_PLATFORM_FIGURES"])',
    'return Path(platform_path or default_platform_path(None, env)).parent / "figures"',
    """return row is None or "'clean_work'" in row[0]""",
    """return row is None or ("'clean_work'" in row[0] and "'publish_figure'" in row[0])""",
}


def test_no_schema_change():
    # TC-032
    # three-dot compare with origin/v3: a newer local origin/v3 snapshot no longer causes a false red
    # refresh origin/v3 first; if that is impossible, skip with the reason (never pass silently)
    # In a local mirror clone, origin is the worktree whose own origin/v3 is the fresh one (its v3 is stale):
    # that ref exists only there, so try it first; against GitHub it fails and we fetch v3 itself.
    def _fetch(src):
        return subprocess.run(["git", "fetch", "origin", src + ":refs/remotes/origin/v3"], cwd=str(HERE.parent),
                              capture_output=True, text=True, timeout=120)
    f = _fetch("+refs/remotes/origin/v3")
    if f.returncode != 0:
        f = _fetch("v3")
    if f.returncode != 0:
        pytest.skip("cannot fetch origin/v3: " + (f.stderr or f.stdout).strip()[:200])
    # mcp-publish-figure: the one change to the schema paths that is allowed is the new confirmation kind publish_figure in store.py (its CHECK,
    # its migration test and the figures_root setting); every other changed line, in any of the three paths, still fails this test.
    diff = subprocess.run(["git", "diff", "-U0", "origin/v3...HEAD", "--"] + SCHEMA_PATHS, cwd=str(HERE.parent), capture_output=True, text=True).stdout
    changed = [ln[1:].strip() for ln in diff.splitlines() if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
    assert [ln for ln in changed if ln and ln not in PUBLISH_FIGURE_STORE_LINES] == []


# ---- constitution ----
def test_remote_call_without_a_yes_writes_no_job(d, monkeypatch):
    # TC-030
    from abf_platform import http_auth
    monkeypatch.setattr(http_auth, "current_remote", lambda: True)
    pid = make(d)
    out = tool_json(lp(d, d.a, pid))
    assert out["sent"] is False and "/c/" in out["confirmation_url"]
    assert launch_jobs(d) == 0


def test_bob_cannot_press_alices_request(d, w):
    # TC-031
    pid = make(d)
    out = tool_json(lp(d, d.a, pid))
    rid = pending_id_of(out["confirmation_url"])
    client = w.web()
    assert w.login(client, "bob").status_code == 303
    page = client.get("/c/" + rid)
    posted = client.post("/c/" + rid, data={"csrf": csrf_of(page.text) or "x"})
    assert posted.status_code == 403
    assert sql_rows(d.state, "SELECT state FROM confirmations WHERE id = ?", (rid,))[0]["state"] == "pending"
    assert launch_jobs(d) == 0
