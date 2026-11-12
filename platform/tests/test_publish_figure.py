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
    assert a["state"] == b["state"] == "refused" and a["reason"].replace(run, "X") == b["reason"].replace("no-such-run", "X")
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


# ---- mcp-publish-figure-gallery (slice 2): pack and delete at the action layer; TC IDs from specs/mcp-publish-figure-gallery/test-case.md ----

def stored(w, ann, run, names=("a.png", "b.png", "c.png")):
    """The figures `names` in the gallery of `run`, put there the way a person does it: proposed, then 送出 pressed."""
    press(w, ann.name, call(w, ann, run, [fig(n, code="# " + n + "\n", params="n=" + n) for n in names])["request_id"])


def index_of(w, ann, run):
    return json.loads((gallery(w, ann, run) / "index.json").read_text())["figures"]


def tree(folder):
    return {p.name: (p.read_bytes(), oct(p.stat().st_mode & 0o777)) for p in sorted(folder.iterdir())}


def pack(w, ann, run, names):
    from abf_platform import actions
    from abf_platform.actions import figures
    return figures.pack_figures(w.ip.index, w.ip.state_db, run, names, caller=ann, clock=w.clock)


def test_pack_figures_whitelist_and_set_semantics(w):
    # TC-023, TC-024, TC-025, TC-026, TC-030, TC-053, TC-062
    ann, bob = w.user("ann"), w.user("bob")
    run = seed(w, "r1", "succeeded", ann)
    stored(w, ann, run)
    before = tree(gallery(w, ann, run))
    got = pack(w, ann, run, ["a.png"])
    assert got["ok"] and got["count"] == 1
    idx = index_of(w, ann, run)
    assert idx["a.png"]["packed"] is True and idx["a.png"]["packed_at"] and not idx["b.png"]["packed"] and not idx["c.png"]["packed"]
    assert pack(w, ann, run, ["b.png"])["ok"]                       # the package is the last selection, not a sum
    idx = index_of(w, ann, run)
    assert [k for k, v in idx.items() if v["packed"]] == ["b.png"] and idx["a.png"]["packed_at"] is None and idx["b.png"]["packed_at"]
    assert pack(w, ann, run, ["c.png", "c.png"])["count"] == 1      # the same name twice is one figure
    assert pack(w, ann, run, [])["ok"] and not any(v["packed"] for v in index_of(w, ann, run).values())
    after = tree(gallery(w, ann, run))
    assert {k: v for k, v in after.items() if k != "index.json"} == {k: v for k, v in before.items() if k != "index.json"}      # only index.json moves
    snap = tree(gallery(w, ann, run))
    for bad in (["a.png", "z.png"], ["../x.png"], ["index.json"], ["a.png.code.txt"], ["x" * 81], ["a\x00.png"], ["a\n.png"], [3],
                ["f%d.png" % i for i in range(31)], "a.png", None):
        got = pack(w, ann, run, bad)
        assert got["ok"] is False and got["reason"] in ("unknown_name", "bad_name", "too_many") and got["message"], bad
        assert tree(gallery(w, ann, run)) == snap, bad              # nothing moves, not even the valid name of a mixed list
    got = pack(w, ann, run, ["a.png", "z.png"])
    assert got["name"] == "z.png" and "z.png" in got["message"]
    mine = pack(w, bob, run, ["a.png"])                             # TC-053: somebody else's run and a missing run answer alike
    gone = pack(w, bob, "no-such-run", ["a.png"])
    assert mine["ok"] is False and mine == gone and mine["found"] is False
    assert tree(gallery(w, ann, run)) == snap


def test_pack_with_no_gallery_changes_nothing(w):
    # TC-008, TC-026
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    assert pack(w, ann, run, []) == {"ok": True, "found": True, "count": 0, "names": []}
    assert not gallery(w, ann, run).exists()


def test_delete_figure_removes_files_and_pack_state(w):
    # TC-032, TC-033, TC-035, TC-037, TC-038, TC-053
    from abf_platform.actions import figures
    ann, bob = w.user("ann"), w.user("bob")
    run = seed(w, "r1", "succeeded", ann)
    stored(w, ann, run, ("a.png", "b.png"))
    pack(w, ann, run, ["a.png"])
    folder = gallery(w, ann, run)
    b_files = {n: v for n, v in tree(folder).items() if n.startswith("b.png")}
    b_entry = index_of(w, ann, run)["b.png"]
    assert figures.delete_figure(w.ip.index, w.ip.state_db, run, "a.png", caller=bob)["found"] is False     # not bob's
    assert (folder / "a.png").exists()
    assert figures.delete_figure(w.ip.index, w.ip.state_db, run, "a.png", caller=ann)["ok"]
    assert not (folder / "a.png").exists() and not (folder / "a.png.code.txt").exists() and not (folder / "a.png.params.txt").exists()
    idx = index_of(w, ann, run)
    assert list(idx) == ["b.png"] and idx["b.png"] == b_entry
    assert {n: v for n, v in tree(folder).items() if n.startswith("b.png")} == b_files
    from abf_platform import actions
    assert actions.list_figures(w.ip.index, w.ip.state_db, run, caller=ann, packed_only=True)["figures"] == []
    for bad in ("z.png", "../b.png", "index.json", "b.png.code.txt", "", None):
        got = figures.delete_figure(w.ip.index, w.ip.state_db, run, bad, caller=ann)
        assert got["ok"] is False and got["message"], bad
    assert (folder / "index.json").exists() and (folder / "b.png").exists() and (folder / "b.png.code.txt").exists()
    (folder / "b.png").unlink()                                      # TC-038: the file is already gone, the entry still goes
    assert figures.delete_figure(w.ip.index, w.ip.state_db, run, "b.png", caller=ann)["ok"] and index_of(w, ann, run) == {}


def test_delete_frees_a_place_in_a_full_gallery(w):
    # TC-037
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    stored(w, ann, run, ("g0.png",))
    folder = gallery(w, ann, run)
    idx = json.loads((folder / "index.json").read_text())
    for i in range(1, 30):
        idx["figures"]["g%d.png" % i] = dict(idx["figures"]["g0.png"])
    (folder / "index.json").write_text(json.dumps(idx))
    assert call(w, ann, run, [fig("new.png")])["state"] == "refused"
    assert figures.delete_figure(w.ip.index, w.ip.state_db, run, "g1.png", caller=ann)["ok"]
    assert call(w, ann, run, [fig("new.png")])["state"] == "pending"


def test_pack_resets_on_same_name_overwrite(w):
    # TC-028
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    stored(w, ann, run, ("a.png",))
    assert pack(w, ann, run, ["a.png"])["ok"] and index_of(w, ann, run)["a.png"]["packed"] is True
    press(w, "ann", call(w, ann, run, [fig("a.png", code="print(2)\n")])["request_id"])
    idx = index_of(w, ann, run)
    assert list(idx) == ["a.png"] and idx["a.png"]["packed"] is False and idx["a.png"]["packed_at"] is None


def test_pack_write_failure_keeps_the_old_index(w, monkeypatch):
    # TC-031
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    stored(w, ann, run, ("a.png",))
    snap = tree(gallery(w, ann, run))

    def boom(a, b):
        raise OSError("read-only /secret/path")
    monkeypatch.setattr(figures.os, "replace", boom)
    got = pack(w, ann, run, ["a.png"])
    assert got["ok"] is False and got["reason"] == "write_failed" and "/secret" not in got["message"]
    assert tree(gallery(w, ann, run)) == snap                       # the old index, and no temporary file left behind
    monkeypatch.undo()
    got = figures.delete_figure(w.ip.index, w.ip.state_db, run, "a.png", caller=ann)
    assert got["ok"]
