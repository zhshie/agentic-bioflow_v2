# Nothing existing: tests of mcp-run-file-live-fixes; specs/mcp-run-file-live-fixes/test-case.md.
"""run_outputs asks again after an error (30 seconds), and .html / .htm result files are binary for read_run_file."""
import json
import pathlib
import sqlite3
import time
import urllib.parse

import pytest

from human_harness import World
from test_mcp_run_file import SECRET, rf, ro, served
from test_results_files import RESULTS, entry, finish_listing, listings, reply_file, world
import test_web_results_outputs as wro

ENTRIES = [entry("qiime2", "dir", 4096), entry("a.tsv")]


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def advance(monkeypatch, seconds):
    from abf_platform import status
    real = time.time
    monkeypatch.setattr(status, "now", lambda: real() + seconds)


def sql_set(w, sql, args=()):
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute(sql, args)
    con.close()


def failed(w, path=RESULTS, message="site_unreachable: please log in again"):
    finish_listing(w, path, ok=False, message=message, error="site_unreachable")


def n_list(w):
    return len(listings(w))


def errored_world(w):
    ann, c, rid = world(w)
    assert ro(w, ann, rid)["state"] == "loading"
    failed(w)
    return ann, c, rid


# ---- US1 ----------------------------------------------------------------------------------------------------------------

def test_tc001_002_inside_30_seconds_same_error_then_requery(w, monkeypatch):
    # TC-001, TC-002
    from abf_platform import jobs
    assert jobs.LISTING_ERROR_RETRY_SECONDS == 30
    ann, c, rid = errored_world(w)
    first = ro(w, ann, rid)
    again = ro(w, ann, rid)
    assert first["state"] == "error" and first["reason"] and again == first and n_list(w) == 1
    advance(monkeypatch, 31)
    got = ro(w, ann, rid)
    assert got["state"] == "loading" and got["listed_at"] is None and n_list(w) == 2
    assert ro(w, ann, rid)["state"] == "loading" and n_list(w) == 2


def test_tc003_mcp_recovers_to_a_ready_listing(w, monkeypatch):
    # TC-003
    ann, c, rid = errored_world(w)
    old = ro(w, ann, rid)["listed_at"]
    advance(monkeypatch, 31)
    assert ro(w, ann, rid)["state"] == "loading" and n_list(w) == 2
    finish_listing(w, RESULTS, ENTRIES)
    got = ro(w, ann, rid)
    assert got["state"] == "ready" and [f["name"] for f in got["files"]] == [e["name"] for e in ENTRIES]
    assert got["listed_at"] and got["listed_at"] != old


def test_tc004_subfolder(w, monkeypatch):
    # TC-004
    ann, c, rid = world(w)
    assert ro(w, ann, rid, "qiime2")["state"] == "loading"
    failed(w, RESULTS + "/qiime2")
    assert ro(w, ann, rid, "qiime2")["state"] == "error" and n_list(w) == 1
    advance(monkeypatch, 31)
    assert ro(w, ann, rid, "qiime2")["state"] == "loading"
    assert n_list(w) == 2 and json.loads(listings(w)[-1]["args_json"])["path"].endswith("/results/qiime2")


@pytest.mark.parametrize("kind", ["done_not_ok", "refused", "expired", "overdue"])
def test_tc005_every_kind_of_error(w, monkeypatch, kind):
    # TC-005
    ann, c, rid = world(w)
    ro(w, ann, rid)
    ref = time.time() - 10
    last = " WHERE id = (SELECT MAX(id) FROM jobs)"
    if kind == "done_not_ok":
        sql_set(w, "UPDATE jobs SET state='done', result_json=?, finished_at=?" + last,
                (json.dumps({"ok": False, "error": "not_found", "message": "no"}), ref))
    elif kind == "refused":
        sql_set(w, "UPDATE jobs SET state='refused', finished_at=?" + last, (ref,))
    elif kind == "expired":
        sql_set(w, "UPDATE jobs SET state='expired', finished_at=NULL, result_json=NULL, deadline_at=?" + last, (ref,))
    else:
        sql_set(w, "UPDATE jobs SET state='queued', finished_at=NULL, deadline_at=?" + last, (ref,))
    assert ro(w, ann, rid)["state"] == "error" and n_list(w) == 1      # about 10 seconds old: nothing new is queued
    advance(monkeypatch, 25)
    assert ro(w, ann, rid)["state"] == "loading" and n_list(w) == 2


def test_tc006_enqueue_false_never_queues(w, monkeypatch):
    # TC-006
    from abf_platform import actions
    ann, c, rid = errored_world(w)
    advance(monkeypatch, 60)
    got = actions.run_outputs(w.ip.index, None, rid, caller=ann, enqueue=False)
    assert got["state"] == "error" and got["reason"] and n_list(w) == 1


def test_tc007_refused_enqueue_is_a_plain_error(w, monkeypatch):
    # TC-007
    from abf_platform import jobs
    ann, c, rid = errored_world(w)
    advance(monkeypatch, 60)

    def boom(*a, **k):
        raise jobs.JobRefused("the agent is offline; check that it is running")
    monkeypatch.setattr(jobs, "enqueue_listing", boom)
    got = ro(w, ann, rid)
    assert got["state"] == "error" and "agent is offline" in got["reason"]
    assert "Traceback" not in json.dumps(got)


def test_tc008_web_outputs_tab_uses_the_same_action(w, monkeypatch):
    # TC-008
    ann, c, rid = wro.world(w)
    c.get(wro.url(rid))
    wro.finish(w, wro.listings(w)[0]["id"], ok=False, message="site_unreachable", state="error", error="site_unreachable")
    assert "無法讀取" in wro.mid(c.get(wro.url(rid)).text) and len(wro.listings(w)) == 1
    advance(monkeypatch, 31)
    t = wro.mid(c.get(wro.url(rid)).text)
    assert "讀取中" in t and len(wro.listings(w)) == 2
    c.get(wro.url(rid))
    assert len(wro.listings(w)) == 2
    from abf_platform import actions
    fake = {"state": "ready", "path": "/x/results", "compute_env": "lab-a", "listed_at": 1_000_000.0, "reason": None,
            "files": [{"name": "only-this.txt", "type": "file", "size": 5, "modified": "2026-10-20T08:00:00Z"}]}
    monkeypatch.setattr(actions, "run_outputs", lambda *a, **k: fake)
    assert "only-this.txt" in c.get(wro.url(rid)).text


def test_tc009_other_users_and_missing_runs(w, monkeypatch):
    # TC-009
    ann, c, rid = errored_world(w)
    bob = w.user("bob")
    advance(monkeypatch, 60)
    a, b = ro(w, bob, rid), ro(w, bob, "0" * 16)
    assert a["found"] is False and a == b and n_list(w) == 1


def test_tc010_out_of_scope_ready_never_expires(w, monkeypatch):
    # TC-010
    ann, c, rid = world(w)
    ro(w, ann, rid)
    finish_listing(w, RESULTS, ENTRIES)
    before = ro(w, ann, rid)
    advance(monkeypatch, 86400)
    after = ro(w, ann, rid)
    assert after["state"] == "ready" and after["files"] == before["files"] and after["listed_at"] == before["listed_at"] and n_list(w) == 1


def test_tc019_no_secret_in_the_retry_path(w, monkeypatch, caplog, capsys):
    # TC-019
    ann, c, rid = world(w)
    ro(w, ann, rid)
    failed(w, message="login failed token=%s\nTraceback (most recent call last):\nSELECT * FROM jobs" % SECRET)
    seen = [ro(w, ann, rid)]
    advance(monkeypatch, 31)
    seen.append(ro(w, ann, rid))
    out = json.dumps(seen) + caplog.text + capsys.readouterr().out
    assert SECRET not in out and "Traceback" not in out and "SELECT" not in out
    assert seen[0]["reason"]


# ---- US2 ----------------------------------------------------------------------------------------------------------------

NOTE = "這是網頁檔（HTML），內容不經由 MCP 傳給模型 (HTML file; its bytes are not sent through MCP)"
HTML = "<html><script>alert(1)</script> héllo</html>\n".encode("utf-8")


@pytest.mark.parametrize("name", ["multiqc/multiqc_report.html", "a.HTML", "b.htm", "x/y.Htm"])
def test_tc011_012_html_is_binary(w, name):
    # TC-011, TC-012
    ann, c, rid = world(w)
    got = served(w, ann, rid, name, HTML)
    assert got["found"] is True and got["state"] == "ready" and got["kind"] == "binary" and got["size"] == len(HTML)
    assert got["name"] == name.rsplit("/", 1)[-1] and got["note"] == NOTE
    assert "/run/file?run=%s&path=%s" % (rid, urllib.parse.quote(name, safe="/")) in got["download_url"]
    for k in ("text", "total_chars", "next_offset", "b64", "data"):
        assert k not in got
    assert "<script>" not in json.dumps(got)
    again = rf(w, ann, rid, name, offset=5)
    assert again["kind"] == "binary" and "text" not in again


def test_tc013_big_html(w):
    # TC-013
    ann, c, rid = world(w)
    got = served(w, ann, rid, "multiqc/multiqc_report.html", b"<html>" + b"x" * (2_549_231 - 6))
    assert got["kind"] == "binary" and "total_chars" not in got and got["size"] == 2_549_231
    first = rf(w, ann, rid, "big.html")
    assert first["state"] == "loading"
    reply_file(w, "done", {"ok": False, "status": "error", "error": "too_large", "name": "big.html", "size": 26214401, "message": "too large"})
    assert rf(w, ann, rid, "big.html")["state"] == "too_large"


@pytest.mark.parametrize("name", ["a.tsv", "a.csv", "a.txt", "a.json", "a.yml", "a.md", "a.log", "a.html.txt", "html", "my.htmlx", "p.svg", "p.xml"])
def test_tc014_015_text_is_still_text(w, name):
    # TC-014, TC-015
    ann, c, rid = world(w)
    got = served(w, ann, rid, name, b"<html>plain</html>\n")
    assert got["kind"] == "text" and got["text"] == "<html>plain</html>\n"


def test_tc016_017_descriptions_and_docs():
    # TC-016, TC-017
    root = pathlib.Path(__file__).resolve().parents[2]
    desc = (root / "platform/abf_platform/mcp_server.py").read_text(encoding="utf-8")
    assert "An HTML file (.html, .htm) is treated as a binary file" in desc
    skill = (root / "skills/downstream/SKILL.md").read_text(encoding="utf-8")
    assert "`.html`, `.htm`" in skill
    plat = (root / "docs/PLATFORM.md").read_text(encoding="utf-8")
    assert ".html" in plat and "30 seconds" in plat
    testing = (root / "docs/TESTING.md").read_text(encoding="utf-8")
    assert "mcp-run-file-live-fixes" in testing and "ampliseq_day5_nano4_r5" in testing
