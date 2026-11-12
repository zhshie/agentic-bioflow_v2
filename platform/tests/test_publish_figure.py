# Nothing existing: no earlier test publishes a figure (mcp-publish-figure, slice 1); the tests below build their own run with seed().
"""mcp-publish-figure: publish_figure proposes figures, the person presses 送出 on the confirmation page, and only then are files written.
TC IDs come from specs/mcp-publish-figure/test-case.md."""
import asyncio
import base64
import json
import os
import time

import pytest

from human_harness import World, csrf_of
from test_confirm_page import logged_in
from test_web_board import seed

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def b64(data=PNG):
    return base64.b64encode(data).decode()


def fig(name="a.png", data=PNG, **extra):
    d = {"filename": name, "content_base64": b64(data), "code": "print(1)\n", "params": "k=1"}
    d.update(extra)
    return d


@pytest.fixture
def w(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    world.clock.t = time.time()
    return world


def call(w, caller, run_id, figures, **kw):
    from abf_platform import actions
    return asyncio.run(actions.request_publish_figure(w.ip.state_db, run_id=run_id, figures=figures, caller=caller, clock=w.clock,
                                                      index_path=w.ip.index, **kw))


def gallery(w, caller, run_id):
    from abf_platform import store
    return store.figures_root(w.ip.state_db) / str(caller.user_id) / run_id


def press(w, name, rid):
    c = logged_in(w, name)
    token = csrf_of(c.get("/c/" + rid).text)
    c.token = token
    return c, c.post("/c/" + rid, data={"csrf": token})


def test_proposal_writes_nothing_until_pressed(w):
    # TC-001, TC-002
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig()])
    assert got["state"] == "pending" and got["request_id"] and got["count"] == 1
    assert not gallery(w, ann, run).exists()
    c, r = press(w, "ann", got["request_id"])
    assert r.status_code == 200 and "已存入圖庫 1 張" in r.text
    folder = gallery(w, ann, run)
    assert (folder / "a.png").read_bytes() == PNG and (folder / "a.png.code.txt").read_text() == "print(1)\n"
    idx = json.loads((folder / "index.json").read_text())
    assert idx["figures"]["a.png"]["size"] == len(PNG) and idx["figures"]["a.png"]["type"] == "png"
    again = c.post("/c/" + got["request_id"], data={"csrf": c.token})
    assert "已存入圖庫 1 張" in again.text and len(json.loads((folder / "index.json").read_text())["figures"]) == 1


def test_not_your_run_and_missing_run_get_the_same_answer(w):
    # TC-003, TC-004
    ann, bob = w.user("ann"), w.user("bob")
    run = seed(w, "r1", "succeeded", ann)
    a = call(w, bob, run, [fig()])
    b = call(w, bob, "no-such-run", [fig()])
    assert a["state"] == b["state"] == "refused" and a["reason"] == b["reason"]
    assert w.confirmations() == []


@pytest.mark.parametrize("bad", [
    fig("../x.png"), fig("a/b.png"), fig("a.exe"), fig("a.png", b"not a png"), fig("index.json"),
    fig("a.svg", b"<svg><script>alert(1)</script></svg>"), fig("a.svg", b'<svg><image href="http://x/y.png"/></svg>'),
    fig("a.svg", b'<svg onload="x()"/>'), fig("a.png", caption="x" * 201),
])
def test_bad_figures_refuse_the_whole_call_without_a_request(w, bad):
    # TC-005 .. TC-020
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("ok.png"), bad])
    assert got["state"] == "refused" and w.confirmations() == []


def test_good_svg_and_limits(w):
    # TC-021, TC-022, TC-023
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    assert call(w, ann, run, [fig("a.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1"/></svg>')])["state"] == "pending"
    assert call(w, ann, run, [fig("f%d.png" % i) for i in range(11)])["state"] == "refused"
    assert call(w, ann, run, [fig("A.png"), fig("a.PNG")])["state"] == "refused"
    assert call(w, ann, run, [fig("big.png", PNG + b"\0" * (6 * 1024 * 1024))])["state"] == "refused"


def test_overwrite_is_marked_and_gallery_is_capped(w):
    # TC-024, TC-025
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig()])
    press(w, "ann", got["request_id"])
    second = call(w, ann, run, [fig(code="print(2)\n")])
    assert "覆蓋既有同名圖" in second["summary"]
    folder = gallery(w, ann, run)
    idx = json.loads((folder / "index.json").read_text())
    for i in range(29):
        idx["figures"]["g%d.png" % i] = dict(idx["figures"]["a.png"])
    (folder / "index.json").write_text(json.dumps(idx))
    assert call(w, ann, run, [fig("new.png")])["state"] == "refused"


def test_write_failure_voids_and_leaves_no_half_gallery(w, monkeypatch):
    # TC-026, TC-027
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("a.png"), fig("b.png")])
    real = os.replace
    calls = []

    def boom(a, b):
        calls.append(b)
        if len(calls) == 2:
            raise OSError("disk full /secret/path")
        return real(a, b)
    monkeypatch.setattr(figures.os, "replace", boom)
    c, r = press(w, "ann", got["request_id"])
    assert r.status_code == 500 and "未存入" in r.text and "/secret" not in r.text
    folder = gallery(w, ann, run)
    assert not (folder / "index.json").exists()
    assert not folder.exists() or not [p for p in folder.glob("*") if p.name.startswith(".tmp-")]
    assert w.confirmations()[0]["state"] == "void"


def test_page_shows_everything_and_send_button(w):
    # TC-028, TC-029
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig(caption="圖說")])
    t = logged_in(w, "ann").get("/c/" + got["request_id"]).text
    assert "存入圖庫確認" in t and "送出" in t and "a.png" in t and "print(1)" in t and "<details open>" in t
    assert "style=" not in t


def test_only_the_owner_can_press(w):
    # TC-030
    ann, bob = w.user("ann"), w.user("bob")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig()])
    c = logged_in(w, "bob")
    r = c.post("/c/" + got["request_id"], data={"csrf": "x" * 32})
    assert r.status_code >= 400 and not gallery(w, ann, run).exists()


def test_confirmations_kind_check_and_no_job(w):
    # TC-031
    from abf_platform import confirm
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig()])
    press(w, "ann", got["request_id"])
    assert w.sql("SELECT * FROM jobs WHERE kind = 'publish_figure'") == []
    assert confirm.NO_JOB_KINDS == ("publish_figure",)
    assert w.sql("SELECT kind FROM confirmations")[0]["kind"] == "publish_figure"


def test_list_figures_reads_the_gallery(w):
    # TC-032
    from abf_platform import actions
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    press(w, "ann", call(w, ann, run, [fig()])["request_id"])
    got = actions.list_figures(w.ip.index, w.ip.state_db, run, caller=ann)
    assert got["found"] and "a.png" in str(got["figures"])
