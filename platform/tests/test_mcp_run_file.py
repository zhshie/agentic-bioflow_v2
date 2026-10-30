# Nothing existing: tests of mcp-run-file (run_outputs(path) and the read tool read_run_file); specs/mcp-run-file/test-case.md.
"""MCP reads of the results tree: a folder listing below results, and one file in pages of text or a download address."""
import json
import pathlib
import subprocess
import urllib.parse

import pytest

from helpers import tool_json
from test_results_files import (FOLDER, LIMIT, RESULTS, entry, file_jobs, finish_listing, listing_paths, listings, ok_result, reply_file,
                                world)
from human_harness import World

CHARS = 200_000
SECRET = "abf_" + "FAKECREDENTIAL" + "0123456789abcdef"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def rf(w, caller, rid, path, **kw):
    args = {"run_id": rid, "path": path}
    args.update(kw)
    return tool_json(w.call("read_run_file", args, caller=caller))


def ro(w, caller, rid, path=None):
    args = {"run_id": rid}
    if path is not None:
        args["path"] = path
    return tool_json(w.call("run_outputs", args, caller=caller))


def jobs_count(w):
    return w.sql("SELECT COUNT(*) AS n FROM jobs")[0]["n"]


def served(w, ann, rid, path, data):
    """Ask once (loading), let the site answer with `data`, ask again: the ready answer."""
    first = rf(w, ann, rid, path)
    assert first["state"] == "loading"
    reply_file(w, "done", ok_result(data, name=path.rsplit("/", 1)[-1]))
    return rf(w, ann, rid, path)


# ---- run_outputs(path) ----------------------------------------------------------------------------------------------------

def test_tc001_003_run_outputs_path_lists_a_subfolder(w):
    # TC-001, TC-003
    ann, c, rid = world(w)
    top = ro(w, ann, rid)
    finish_listing(w, RESULTS, [entry("qiime2", "dir", 4096), entry("a.tsv")])
    top = ro(w, ann, rid)
    assert top["state"] == "ready" and top["sub"] == "" and top["bad_path"] is False
    from abf_platform import actions
    assert top == json.loads(json.dumps(actions.run_outputs(w.ip.index, None, rid, caller=ann, subpath=None)))
    sub = ro(w, ann, rid, "qiime2")
    assert sub["state"] == "loading"
    finish_listing(w, RESULTS + "/qiime2", [entry("table.tsv"), entry("deep", "dir", 4096)])
    sub = ro(w, ann, rid, "qiime2")
    assert sub["state"] == "ready" and sub["sub"] == "qiime2"
    rows = {f["name"]: f for f in sub["files"]}
    assert rows["table.tsv"]["download"] == "qiime2/table.tsv" and rows["deep"]["enter"] == "qiime2/deep"


def test_tc002_one_listing_job_for_a_path(w):
    # TC-002
    ann, c, rid = world(w)
    first = ro(w, ann, rid, "qiime2")
    assert first["state"] == "loading"
    ro(w, ann, rid, "qiime2")
    assert listing_paths(w) == [RESULTS + "/qiime2"]


def test_tc004_walk_from_the_first_level_to_the_file_text(w):
    # TC-004: only MCP answers feed the next call; the test never spells a path itself after the first listing
    ann, c, rid = world(w)
    body = "id\tcount\na\t1\nb\t2\n"
    ro(w, ann, rid)
    finish_listing(w, RESULTS, [entry("qiime2", "dir", 4096), entry("a.tsv")])
    top = ro(w, ann, rid)
    assert top["state"] == "ready"
    folder = [f for f in top["files"] if f["name"] == "qiime2"][0]
    assert folder["enter"]
    step2 = ro(w, ann, rid, folder["enter"])
    assert step2["state"] == "loading"
    finish_listing(w, RESULTS + "/" + folder["enter"], [entry("table.tsv")])
    step2 = ro(w, ann, rid, folder["enter"])
    assert step2["state"] == "ready" and step2["sub"] == folder["enter"] and step2["bad_path"] is False
    leaf = [f for f in step2["files"] if f["name"] == "table.tsv"][0]
    assert leaf["download"]
    first = rf(w, ann, rid, leaf["download"])
    assert first["state"] == "loading"
    reply_file(w, "done", ok_result(body.encode(), name="table.tsv"))
    got = rf(w, ann, rid, leaf["download"])
    assert got["state"] == "ready" and got["kind"] == "text" and got["text"] == body


def test_tc005_006_bad_paths_list_the_first_level(w):
    # TC-005, TC-006
    ann, c, rid = world(w)
    ro(w, ann, rid)
    finish_listing(w, RESULTS, [entry("qiime2", "dir", 4096)])
    n = jobs_count(w)
    for bad in ("../x", "/etc/passwd", "a/.hidden/b", "a//b", "a" * 513, "a\nb"):
        got = ro(w, ann, rid, bad)
        assert got["bad_path"] is True and got["sub"] == "" and got["state"] == "ready", bad
    assert jobs_count(w) == n
    got = ro(w, ann, rid, "")
    assert got["state"] == "ready" and got["sub"] == "" and jobs_count(w) == n


def test_tc008_029_other_users_run_is_not_found(w):
    # TC-008, TC-029
    from abf_platform import actions
    ann, c, rid = world(w)
    bob = w.user("bob")
    n = jobs_count(w)
    theirs = ro(w, bob, rid, "qiime2")
    assert theirs == ro(w, ann, "nope", "qiime2") and theirs["found"] is False
    mine = rf(w, bob, rid, "a.tsv")
    assert mine == rf(w, ann, "nope", "a.tsv") == theirs
    assert actions.read_run_file(w.ip.index, None, rid, "a.tsv", caller=bob) == theirs
    assert actions.read_run_file(w.ip.index, None, "nope", "a.tsv", caller=ann) == theirs
    assert jobs_count(w) == n


# ---- read_run_file --------------------------------------------------------------------------------------------------------

def test_tc009_a_small_text_file(w):
    # TC-009
    ann, c, rid = world(w)
    body = "id\tcount\na\t1\nb\t2\n"
    got = served(w, ann, rid, "qiime2/table.tsv", body.encode())
    assert got["state"] == "ready" and got["kind"] == "text" and got["name"] == "table.tsv" and got["size"] == len(body)
    assert got["total_chars"] == len(body) and got["offset"] == 0 and got["text"] == body and got["next_offset"] is None
    assert "message" not in got


def test_tc010_011_012_018_pages(w):
    # TC-010, TC-011, TC-012, TC-018
    ann, c, rid = world(w)
    body = ("a" * 399) + "\n"
    body = (body * 1001)[:CHARS * 2 + 17]
    n = jobs_count(w)
    p1 = served(w, ann, rid, "t.tsv", body.encode())
    assert len(p1["text"]) == CHARS and p1["next_offset"] == CHARS and p1["total_chars"] == CHARS * 2 + 17
    assert "offset=200000" in p1["message"]
    p2 = rf(w, ann, rid, "t.tsv", offset=p1["next_offset"])
    assert len(p2["text"]) == CHARS and p2["offset"] == CHARS and p2["next_offset"] == 2 * CHARS and "message" in p2
    p3 = rf(w, ann, rid, "t.tsv", offset=p2["next_offset"])
    assert len(p3["text"]) == 17 and p3["next_offset"] is None and "message" not in p3
    assert p1["text"] + p2["text"] + p3["text"] == body
    assert len(file_jobs(w)) == 1 and jobs_count(w) == n + 1


def test_tc013_014_015_016_edges(w):
    # TC-013, TC-014, TC-015, TC-016
    ann, c, rid = world(w)
    exact = served(w, ann, rid, "x.txt", b"a" * CHARS)
    assert len(exact["text"]) == CHARS and exact["next_offset"] is None and exact["total_chars"] == CHARS
    ten = served(w, ann, rid, "ten.txt", b"0123456789")
    assert ten["state"] == "ready"
    end = rf(w, ann, rid, "ten.txt", offset=10)
    assert end["state"] == "ready" and end["kind"] == "text" and end["text"] == "" and end["next_offset"] is None
    empty = served(w, ann, rid, "empty.txt", b"")
    assert empty["state"] == "ready" and empty["kind"] == "text" and empty["text"] == "" and empty["next_offset"] is None
    over = rf(w, ann, rid, "ten.txt", offset=11)
    assert over["state"] == "error" and over["code"] == "bad_offset" and over["total_chars"] == 10 and "text" not in over
    for bad in (-1, "10", 1.5):
        got = rf(w, ann, rid, "ten.txt", offset=bad)
        assert got["state"] == "error" and got["code"] == "bad_offset" and "text" not in got, bad


def test_tc017_multibyte_pages(w):
    # TC-017
    ann, c, rid = world(w)
    body = ("分μ😀" * 150_000)[:CHARS * 2 + 5]
    data = body.encode("utf-8")
    first = served(w, ann, rid, "m.txt", data)
    pages, got = [], first
    while True:
        pages.append(got["text"])
        assert "�" not in got["text"]
        got["text"].encode("utf-8")
        if got["next_offset"] is None:
            break
        assert len(got["text"]) == CHARS
        got = rf(w, ann, rid, "m.txt", offset=got["next_offset"])
    assert "".join(pages) == body and first["total_chars"] == len(body) < first["size"]


def test_tc019_loading_never_waits(w, monkeypatch):
    # TC-019
    import asyncio
    import time

    def boom(*a, **k):
        raise AssertionError("waited")
    monkeypatch.setattr(time, "sleep", boom)
    monkeypatch.setattr(asyncio, "sleep", boom)
    ann, c, rid = world(w)
    n = jobs_count(w)
    first = rf(w, ann, rid, "t.tsv")
    assert first["state"] == "loading" and "站台正在讀這個檔案，請幾秒後再問一次" in first["message"] and "ask again in a few seconds" in first["message"]
    assert jobs_count(w) == n + 1 and len(file_jobs(w)) == 1
    assert rf(w, ann, rid, "t.tsv")["state"] == "loading" and jobs_count(w) == n + 1


@pytest.mark.parametrize("data", [b"a\x00b\n", b"\x1f\x8b\x08\x00\xff\xfe", b"\x89PNG\r\n\x1a\n\xff"])
def test_tc020_021_028_binary_files_give_no_bytes(w, data):
    # TC-020, TC-021, TC-028
    ann, c, rid = world(w)
    got = served(w, ann, rid, "plots/a.png", data)
    assert got["kind"] == "binary" and got["name"] == "a.png" and got["size"] == len(data) and got["download_url"]
    assert got["note"] == "這是二進位檔，內容不經由 MCP 傳給模型 (binary file; its bytes are not sent through MCP)"
    again = rf(w, ann, rid, "plots/a.png", offset=5)
    assert again["kind"] == "binary"
    for answer in (got, again):
        assert not {"text", "b64", "data", "range", "image", "html"} & set(answer)
        assert "\x00" not in json.dumps(answer) and "PNG" not in json.dumps(answer)


def test_tc022_download_url(w):
    # TC-022
    from abf_platform import store
    ann, c, rid = world(w)
    path = "qiime2/表 a.qza"
    served(w, ann, rid, path, b"\x00\x01")
    q = "/run/file?run=%s&path=%s" % (rid, urllib.parse.quote(path, safe="/"))
    default = rf(w, ann, rid, path)["download_url"]
    from abf_platform.actions import DEFAULT_WEB_BASE
    assert default == DEFAULT_WEB_BASE + q
    store.set_meta(w.ip.state_db, "web_base_url", "https://abf.example.org/")
    assert rf(w, ann, rid, path)["download_url"] == "https://abf.example.org" + q


def test_tc023_too_large(w):
    # TC-023
    ann, c, rid = world(w)
    assert rf(w, ann, rid, "big/table.tsv")["state"] == "loading"
    reply_file(w, "error", {"ok": False, "error": "too_large", "size": LIMIT + 1})
    got = rf(w, ann, rid, "big/table.tsv")
    assert got["state"] == "too_large" and got["size"] == 26214401 and got["max_bytes"] == 26214400
    assert got["site_path"] == FOLDER + "/results/big/table.tsv"
    assert not {"text", "b64", "data"} & set(got)


def test_tc024_cloud_environment(w):
    # TC-024
    from abf_platform import jobs
    ann, c, rid = world(w)
    w.sql("SELECT 1")
    import sqlite3
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET platform = 'awsbatch-platform' WHERE name = 'lab-a'")
    con.close()
    n = jobs_count(w)
    got = rf(w, ann, rid, "a.tsv")
    assert got["state"] == "unavailable" and got["code"] == "not_on_site" and got["message"] == jobs.RUN_FILE_NOT_ON_SITE
    assert jobs_count(w) == n


def test_tc025_no_launch(w):
    # TC-025
    ann, c, rid = world(w, folder="")      # the launch record names no folder
    n = jobs_count(w)
    got = rf(w, ann, rid, "a.tsv")
    assert got["state"] == "unavailable" and got["code"] == "no_launch" and got["message"] and jobs_count(w) == n


def test_tc026_034_every_error_code_has_a_plain_reason(w, monkeypatch, caplog):
    # TC-026, TC-034
    from abf_platform import actions
    caplog.set_level(0)
    ann, c, rid = world(w)
    seen = []
    for code in ("agent_offline", "refused", "no_answer", "not_found", "not_a_file", "site_unreachable", "changed", "bad_answer", "failed"):
        monkeypatch.setattr(actions, "run_file", lambda *a, _c=code, **k: {"found": True, "state": "error", "code": _c, "reason": None, "name": "x",
                                                                            "size": None, "site_path": "/s/x", "max_bytes": LIMIT})
        got = rf(w, ann, rid, "a.tsv")
        assert got["state"] == "error" and got["code"] == code and got["reason"].strip(), code
        seen.append(json.dumps(got))
    monkeypatch.undo()
    # a real failed read with a planted secret and a stack in the site's message
    assert rf(w, ann, rid, "f.tsv")["state"] == "loading"
    reply_file(w, "error", {"ok": False, "error": "failed", "message": "Traceback (most recent call last): token=%s" % SECRET})
    seen.append(json.dumps(rf(w, ann, rid, "f.tsv")))
    seen.append(json.dumps(rf(w, ann, rid, "../x")))
    bob = w.user("bob")
    seen.append(json.dumps(rf(w, bob, rid, "a.tsv")))
    text = "\n".join(seen)
    assert SECRET not in text and "Traceback" not in text and "SELECT" not in text
    assert SECRET not in caplog.text


@pytest.mark.parametrize("bad", ["../x", "/etc/passwd", "a/.hidden/b", "", "a//b", "a" * 513, "a\nb"])
def test_tc027_bad_paths_are_refused_before_queueing(w, bad):
    # TC-027
    ann, c, rid = world(w)
    n = jobs_count(w)
    got = rf(w, ann, rid, bad)
    assert got["state"] == "error" and got["code"] == "bad_path" and jobs_count(w) == n


# ---- registration, description, parity, scope ------------------------------------------------------------------------------

def tools_of(w):
    tools, _ = w.mcp([])
    return {t.name: t for t in tools}, tools


def test_tc007_030_031_032_035_tool_registration(w):
    # TC-007, TC-030, TC-031, TC-032, TC-035
    by, tools = tools_of(w)
    assert len(tools) == 21 and "read_run_file" in by and by["read_run_file"].annotations.read_only_hint is True
    assert sum(1 for t in tools if t.annotations and t.annotations.read_only_hint) == 16
    d = by["read_run_file"].description
    for s in ("the text goes to the model you chose", "200,000", "next_offset", "/run/file", "25 MB", "loading", "ready", "error", "unavailable",
              "too_large", "site path", "results/", "run_outputs", "Read-only", "your own"):
        assert s in d, s
    props = by["read_run_file"].input_schema["properties"]
    assert sorted(props) == ["offset", "path", "run_id"] and props["offset"].get("default") == 0
    assert "path" in by["run_outputs"].input_schema["properties"] and "run_id" in by["run_outputs"].input_schema["required"]
    o = by["run_outputs"].description
    assert "bad_path" in o and "never waits" in o and all(s in o for s in ("loading", "ready", "error", "unavailable"))
    for name in ("run_outputs", "read_run_file"):
        assert not {"confirm", "yes", "kind", "retry", "save", "target", "dest"} & set(by[name].input_schema["properties"])
    from abf_platform import actions
    assert callable(actions.read_run_file)


def test_tc032_only_read_jobs_are_queued(w):
    # TC-032
    ann, c, rid = world(w)
    before = {r["id"] for r in w.sql("SELECT id FROM jobs")}
    rf(w, ann, rid, "a.tsv")
    kinds = {r["kind"] for r in w.sql("SELECT id, kind FROM jobs") if r["id"] not in before}
    assert kinds == {"read_run_file"}


def test_tc033_tool_and_action_agree(w):
    # TC-033
    from abf_platform import actions
    ann, c, rid = world(w)
    served(w, ann, rid, "t.tsv", b"x\ty\n")
    served(w, ann, rid, "b.qza", b"\x00\x01")
    for path in ("t.tsv", "b.qza"):
        a = json.loads(json.dumps(actions.read_run_file(w.ip.index, None, rid, path, caller=ann)))
        assert a == rf(w, ann, rid, path)


ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_tc036_037_downstream_prompt_is_extended_not_changed():
    # TC-036, TC-037
    new = (ROOT / "skills" / "downstream" / "SKILL.md").read_text(encoding="utf-8")
    for s in ("read_run_file", "run_outputs", "enter", "200,000", "next_offset", "loading", "too_large", "download", "25 MB", "model the person chose"):
        assert s in " ".join(new.split()), s
    # Frozen from skills/downstream/SKILL.md at v3 commit 861ef5ae (identical at the
    # merge-base with this branch): CI checkouts are shallow, so origin/v3 cannot be
    # read there, and this test must never skip.
    old = (pathlib.Path(__file__).parent / "fixtures" / "downstream_SKILL_v3_baseline.md").read_bytes()
    old_lines = old.decode("utf-8").replace("\r\n", "\n").splitlines()
    new_lines = new.replace("\r\n", "\n").splitlines()
    it = iter(new_lines)
    assert all(line in it for line in old_lines), "an old line was changed or removed"
    added = " ".join(set(new_lines) - set(old_lines)).lower()
    for word in ("multiqc", "qiime2", "slurm", "nano4", "ampliseq"):
        assert word not in added, word
