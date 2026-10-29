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
    # TC-014
    caplog.set_level("DEBUG")
    pid = make(d)
    d.bobs_environment()
    texts = [tool_text(lp(d, d.a, pid)), tool_text(lp(d, d.b, pid, ce_name="b1", samplesheet_text=sheet(d, d.b))),
             tool_text(lp(d, d.a, pid, version=9))]
    token = getattr(d.a, "token", None)
    for t in texts + [caplog.text]:
        assert clean(t)
        if token:
            assert token not in t


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
    assert len(t) == 21 and sum(1 for x in t.values() if x.annotations.read_only_hint) == 15
    for n in ("create_pipeline", "update_pipeline", "export_pipeline", "validate_pipeline"):
        assert n not in t
    doc = (PKG / "mcp_server.py").read_text(encoding="utf-8")
    assert "five tools that ask" not in doc and "launch_pipeline" in doc.split('"""')[1]


def test_no_web_route_for_it(d, w):
    # TC-027
    client = w.web()
    assert w.login(client, "bob").status_code == 303
    assert client.post("/act/launch_pipeline", data={}).status_code in (404, 405)


def test_no_schema_change():
    # TC-032
    out = subprocess.run(["git", "diff", "--stat", "e428661b", "--", "migrations", "abf_platform/store.py", "abf_platform/schema.sql"],
                         cwd=str(HERE.parent), capture_output=True, text=True).stdout
    assert out.strip() == ""


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
