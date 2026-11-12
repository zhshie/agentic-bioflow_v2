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
    # TC-059
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
    # TC-023, TC-025, TC-031, TC-033, TC-034
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("ok.png"), bad])
    assert got["state"] == "refused" and w.confirmations() == []


def test_good_svg_and_limits(w):
    # TC-035, TC-027, TC-023, TC-037
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    assert call(w, ann, run, [fig("a.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1"/></svg>')])["state"] == "pending"
    assert call(w, ann, run, [fig("f%d.png" % i) for i in range(11)])["state"] == "refused"
    assert call(w, ann, run, [fig("A.png"), fig("a.PNG")])["state"] == "refused"
    assert call(w, ann, run, [fig("big.png", PNG + b"\0" * (6 * 1024 * 1024))])["state"] == "refused"


def test_overwrite_is_marked_and_gallery_is_capped(w):
    # TC-014, TC-029
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
    # TC-018, TC-020
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
    # TC-041, TC-043
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig(caption="圖說")])
    t = logged_in(w, "ann").get("/c/" + got["request_id"]).text
    assert "存入圖庫確認" in t and "送出" in t and "a.png" in t and "print(1)" in t and "<details open>" in t
    assert "style=" not in t


def test_only_the_owner_can_press(w):
    # TC-047
    ann, bob = w.user("ann"), w.user("bob")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig()])
    c = logged_in(w, "bob")
    r = c.post("/c/" + got["request_id"], data={"csrf": "x" * 32})
    assert r.status_code >= 400 and not gallery(w, ann, run).exists()


def test_confirmations_kind_check_and_no_job(w):
    # TC-079
    from abf_platform import confirm
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig()])
    press(w, "ann", got["request_id"])
    assert w.sql("SELECT * FROM jobs WHERE kind = 'publish_figure'") == []
    assert confirm.NO_JOB_KINDS == ("publish_figure",)
    assert w.sql("SELECT kind FROM confirmations")[0]["kind"] == "publish_figure"


def test_list_figures_reads_the_gallery(w):
    # TC-061
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
# ==== fix round (ruling F2, F7): the tests the contract names and that were missing or too weak. TC numbers are those of the confirmed contract ====

import hashlib

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
SVG_OK = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1"/></svg>'
INDEX_FIELDS = {"size", "type", "caption", "code_file", "params_file", "created", "packed", "packed_at", "request_id"}


def confirmed_gallery(w, name="ann", run_name="r1", figures=None):
    user = w.user(name)
    run = seed(w, run_name, "succeeded", user)
    press(w, name, call(w, user, run, figures or [fig("a.png"), fig("b.svg", SVG_OK, code="", params="")])["request_id"])
    return user, run


def test_private_and_not_packed_after_confirm(w):
    # TC-011, TC-061
    from abf_platform import actions
    ann, bob = w.user("ann"), w.user("bob")
    run = seed(w, "r1", "succeeded", ann)
    press(w, "ann", call(w, ann, run, [fig("a.png"), fig("b.png")])["request_id"])
    idx = json.loads((gallery(w, ann, run) / "index.json").read_text())
    assert sorted(idx["figures"]) == ["a.png", "b.png"]
    assert all(v["packed"] is False and v["packed_at"] is None for v in idx["figures"].values())
    assert actions.list_figures(w.ip.index, w.ip.state_db, run, caller=ann, packed_only=True)["figures"] == []
    assert len(actions.list_figures(w.ip.index, w.ip.state_db, run, caller=ann)["figures"]) == 2
    theirs = actions.list_figures(w.ip.index, w.ip.state_db, run, caller=bob)
    missing = actions.list_figures(w.ip.index, w.ip.state_db, "no-such-run", caller=bob)
    assert theirs["found"] is False and not theirs.get("figures") and theirs["message"] == missing["message"]


def test_storage_format(w):
    # TC-012
    ann, run = confirmed_gallery(w)
    folder = gallery(w, ann, run)
    assert sorted(p.name for p in folder.iterdir()) == ["a.png", "a.png.code.txt", "a.png.params.txt", "b.svg", "index.json"]
    idx = json.loads((folder / "index.json").read_text())
    assert idx["version"] == 1 and set(idx) == {"version", "figures"}
    a, b = idx["figures"]["a.png"], idx["figures"]["b.svg"]
    assert set(a) == INDEX_FIELDS == set(b)
    assert (a["code_file"], a["params_file"], a["type"], a["size"]) == ("a.png.code.txt", "a.png.params.txt", "png", len(PNG))
    assert (b["code_file"], b["params_file"], b["type"]) == (None, None, "svg")
    assert (folder / "a.png.code.txt").read_text() == "print(1)\n" and (folder / "a.png.params.txt").read_text() == "k=1"


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions only; CI and WSL run it")
def test_permissions_are_private(w):
    # TC-013
    ann, run = confirmed_gallery(w)
    folder = gallery(w, ann, run)
    assert (folder.stat().st_mode & 0o777) == 0o700 and (folder.parent.stat().st_mode & 0o777) == 0o700
    assert all((p.stat().st_mode & 0o777) == 0o600 for p in folder.iterdir())


def test_same_name_overwrites_resets_packed_and_counts_once(w):
    # TC-014
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    press(w, "ann", call(w, ann, run, [fig("a.png"), fig("b.png")])["request_id"])
    folder = gallery(w, ann, run)
    idx = json.loads((folder / "index.json").read_text())
    idx["figures"]["a.png"].update(packed=True, packed_at="2026-01-01T00:00:00Z")
    (folder / "index.json").write_text(json.dumps(idx))
    new = PNG + b"\x07" * 9
    second = call(w, ann, run, [fig("a.png", new)])
    assert "覆蓋" in second["summary"]
    press(w, "ann", second["request_id"])
    idx = json.loads((folder / "index.json").read_text())
    assert (folder / "a.png").read_bytes() == new and idx["figures"]["a.png"]["packed"] is False and idx["figures"]["a.png"]["packed_at"] is None
    assert sorted(idx["figures"]) == ["a.png", "b.png"]


def test_corrupt_index_json_is_empty_gallery_not_crash(w):
    # TC-021
    from abf_platform import actions
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    folder = gallery(w, ann, run)
    folder.mkdir(parents=True)
    for junk in (b"{not json", b'{"version": 2, "figures": {}}', b'{"version": 1, "figures": [1]}', b"\xff\xfe"):
        (folder / "index.json").write_bytes(junk)
        got = actions.list_figures(w.ip.index, w.ip.state_db, run, caller=ann)
        assert got["found"] is True and got["figures"] == [] and got["error"]
        out = call(w, ann, run, [fig("n%d.png" % len(junk))])
        assert out["state"] == "pending" and out["warning"]


def test_figures_root_setting(tmp_path):
    # TC-022
    from abf_platform import store
    db = tmp_path / "x" / "platform.db"
    assert store.figures_root(db, {"ABF_PLATFORM_FIGURES": str(tmp_path / "elsewhere")}) == tmp_path / "elsewhere"
    assert store.figures_root(db, {}) == tmp_path / "x" / "figures"
    assert store.figures_root(db, {"ABF_PLATFORM_FIGURES": ""}) == tmp_path / "x" / "figures"


BAD_NAMES = ["../x.png", "a/b.png", "a\\b.png", ".hidden.png", "x.exe", "x.png.exe", "x.html", "index.json", "a.code.txt", "a.params.txt",
             "", "a" * 77 + ".png", "a b.png", "a\x00b.png"]


@pytest.mark.parametrize("name", BAD_NAMES + ["<same name twice>"])
def test_bad_names_refused(w, name):
    # TC-023
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    figures = [fig("a.png"), fig("a.png")] if name == "<same name twice>" else [fig(name)]
    got = call(w, ann, run, figures)
    assert got["state"] == "refused" and got["reason"] and w.confirmations() == [] and not gallery(w, ann, run).exists()


def test_legal_names_pass(w):
    # TC-024
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    eighty = "a" * 76 + ".png"
    assert len(eighty) == 80
    assert [figures.check_name(n) for n in ("ok-1_a.b.png", "X.PNG", "y.jpeg", eighty)] == ["png", "png", "jpg", "png"]
    got = call(w, ann, run, [fig("ok-1_a.b.png"), fig("X.PNG"), fig("y.jpeg", JPEG), fig(eighty)])
    assert got["state"] == "pending" and got["count"] == 4


@pytest.mark.parametrize("name,data", [("a.jpg", PNG), ("a.png", JPEG), ("a.png", b"just some text"), ("a.jpeg", b"\x89PNG\r\n\x1a\n")])
def test_extension_must_match_magic_bytes(w, name, data):
    # TC-025
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig(name, data)])
    assert got["state"] == "refused" and w.confirmations() == []


def test_three_formats_accepted(w):
    # TC-026, TC-035
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    for name, data in (("a.png", PNG), ("a.jpg", JPEG), ("a.svg", SVG_OK)):
        assert call(w, ann, run, [fig(name, data)])["state"] == "pending", name


def test_count_limits(w):
    # TC-027, TC-028
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    assert call(w, ann, run, [fig("f%d.png" % i) for i in range(11)])["state"] == "refused"
    assert call(w, ann, run, [])["state"] == "refused"
    assert w.confirmations() == []
    assert call(w, ann, run, [fig("f%d.png" % i) for i in range(10)])["state"] == "pending"
    # a full gallery still takes a same-name replacement, and refuses a new name
    folder = gallery(w, ann, run)
    folder.mkdir(parents=True)
    entry = {"size": 1, "type": "png", "caption": "", "code_file": None, "params_file": None, "created": "t", "packed": False, "packed_at": None, "request_id": "x"}
    (folder / "index.json").write_text(json.dumps({"version": 1, "figures": {"g%d.png" % i: entry for i in range(30)}}))
    assert call(w, ann, run, [fig("g3.png")])["state"] == "pending"
    assert call(w, ann, run, [fig("one-more.png")])["state"] == "refused"


@pytest.mark.parametrize("b64text", ["iVBORw0KGgo!!!!", "QUJDRA", "QUJD RA==", "%%%%"])
def test_bad_base64_refused(w, b64text):
    # TC-030
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("ok.png"), {"filename": "b.png", "content_base64": b64text}])
    assert got["state"] == "refused" and "第 2 張" in got["reason"] and "b.png" in got["reason"] and w.confirmations() == []


@pytest.mark.parametrize("field,value,word", [("caption", "x" * 201, "caption"), ("code", "x" * (100 * 1024 + 1), "code"), ("code", "a\x00b", "code"),
                                              ("params", "x" * (10 * 1024 + 1), "params")])
def test_caption_code_params_limits(w, field, value, word):
    # TC-031
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("a.png", **{field: value})])
    assert got["state"] == "refused" and word in got["reason"] and w.confirmations() == []


def test_caption_code_params_boundaries_are_taken(w):
    # TC-032
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("a.png", caption="x" * 200, code="y" * (100 * 1024), params="z" * (10 * 1024))])
    assert got["state"] == "pending"


@pytest.mark.parametrize("svg", [b"<svg><script>x</script></svg>", b"<svg><SCRIPT>x</SCRIPT></svg>", b"<svg><foreignObject/></svg>", b"<!DOCTYPE svg><svg/>",
                                 b'<!DOCTYPE svg [<!ENTITY a "b">]><svg/>', b"<svg><!ENTITY a 'b'></svg>", b'<svg><a href="javascript:x()"/></svg>',
                                 b'<svg onload="x()"/>', b'<svg><rect onclick = "x()"/></svg>', b"<svg><iframe/></svg>", b"<svg><embed/></svg>", b"<svg><object/></svg>",
                                 b'<svg><image href="http://x/y.png"/></svg>', b'<svg><image xlink:href="https://x/y.png"/></svg>', b'<svg><image src="//x/y.png"/></svg>',
                                 b'<svg><rect style="fill:url(http://x/y)"/></svg>'])
def test_svg_with_script_or_event_or_external_ref_refused(w, svg):
    # TC-033, TC-034, TC-086
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("a.svg", svg)])
    assert got["state"] == "refused" and got["reason"] and w.confirmations() == [] and not gallery(w, ann, run).exists()


def test_plain_svg_accepted_and_written_byte_for_byte(w):
    # TC-035, TC-086
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    odd = b'<?xml version="1.0"?>\r\n<svg xmlns="http://www.w3.org/2000/svg">\r\n  <text>&lt;script&gt; as text</text>\r\n</svg>\r\n'
    press(w, "ann", call(w, ann, run, [fig("a.svg", odd)])["request_id"])
    assert (gallery(w, ann, run) / "a.svg").read_bytes() == odd


def test_svg_that_is_not_utf8_refused(w):
    # TC-036
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("a.svg", b"<svg>\xff\xfe</svg>")])
    assert got["state"] == "refused" and w.confirmations() == []


@pytest.mark.parametrize("status", ["running", "failed", "succeeded"])
def test_any_run_state_can_be_proposed_for(w, status):
    # TC-062
    ann = w.user("ann")
    run = seed(w, "r-" + status, status, ann)
    assert call(w, ann, run, [fig()])["state"] == "pending"


def test_nothing_written_outside_figures_root(w, tmp_path):
    # TC-063, TC-084
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    before = {str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")}
    schema_before = [tuple(r) for r in w.sql("SELECT type, name, tbl_name FROM sqlite_master ORDER BY name")]
    for bad in BAD_NAMES:
        assert call(w, ann, run, [fig(bad)])["state"] == "refused"
    assert not gallery(w, ann, run).exists()          # TC-084: nothing is there before anyone sends anything
    press(w, "ann", call(w, ann, run, [fig("good.png")])["request_id"])
    folder = gallery(w, ann, run)
    inside = folder.relative_to(tmp_path)
    parents = {str(p) for p in inside.parents}
    new = {str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")} - before
    stray = [p for p in new if not (p == str(inside) or p.startswith(str(inside) + os.sep) or p in parents or "platform.db" in p or "index.db" in p or "web_signing.key" in p)]    # the web login makes its signing key, whoever asks
    assert stray == [], stray
    assert sorted(p.name for p in folder.iterdir()) == ["good.png", "good.png.code.txt", "good.png.params.txt", "index.json"]     # TC-084: only what was sent
    assert [tuple(r) for r in w.sql("SELECT type, name, tbl_name FROM sqlite_master ORDER BY name")] == schema_before


def test_no_recommendation_text(w):
    # TC-084
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    tools, _ = w.mcp([])
    desc = [t.description for t in tools if t.name == "publish_figure"][0]
    got = call(w, ann, run, [fig()])
    text = desc + got["summary"] + got["message"]
    assert not any(word in text for word in ("推薦", "建議的分析", "recommend", "suggested analysis"))


# ---- F7: what a caption and the other texts may hold ----------------------------------------------------------------------------------

@pytest.mark.parametrize("bad", ["a\nb", "a\rb", "a\r\nb", "a\x00b", "a\x1bb", "a\x7fb", "a\tb", "a b", "a b", "a\x85b"])
def test_f7_caption_with_a_line_break_or_control_character_is_refused(w, bad):
    # ruling F7 (adversarial review 5): a caption could forge lines of the confirmation screen
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("a.png", caption=bad)])
    assert got["state"] == "refused" and "caption" in got["reason"] and w.confirmations() == []


@pytest.mark.parametrize("field", ["caption", "code", "params"])
def test_f7_a_lone_surrogate_is_refused_at_the_request(w, field):
    # ruling F7 (adversarial review 6): it passed the size check and failed later in an encode
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("a.png", **{field: "x\ud800y"})])
    assert got["state"] == "refused" and field in got["reason"] and w.confirmations() == [] and "Traceback" not in got["reason"]


def test_f7_the_screen_shows_twelve_characters_of_each_sha256(w):
    # ruling F7
    from abf_platform import actions
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    other = PNG + b"\x01" * 7
    got = call(w, ann, run, [fig("a.png"), fig("b.png", other)])
    for data in (PNG, other):
        assert hashlib.sha256(data).hexdigest()[:12] in got["summary"]
    figs = [{"name": "a.png", "type": "png", "size": 1, "sha256": hashlib.sha256(PNG).hexdigest(), "caption": "", "code": "", "params": ""}]
    assert hashlib.sha256(PNG).hexdigest()[:12] in actions.screen_for_page({"run_name": "r1", "figures": figs}, [], "en")


def test_index_updates_do_not_lose_each_other(w, monkeypatch):
    # ruling G1 (lead, 2026-11-13): pack, delete and the confirmed write each read index.json and replace it whole; they hold one lock of the
    # gallery folder from the read to the replace. Real threads: a delete and a confirmed write are started in the middle of a pack.
    import threading
    from abf_platform import store
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    stored(w, ann, run, ("a.png", "b.png"))
    rid = call(w, ann, run, [fig("new.png")])["request_id"]
    bundle = json.loads(w.sql("SELECT bundle_json FROM confirmations WHERE id = ?", (rid,))[0]["bundle_json"])
    real_read, packer, errors = figures.read_index, [], []

    def read_then_let_the_others_try(folder):
        got = real_read(folder)
        if threading.current_thread() is packer[0]:
            for t in others:
                t.start()
            for t in others:
                t.join(1.5)         # without the lock both finish here, between the read and the write of the pack
        return got

    def guard(fn):
        def run_it():
            try:
                fn()
            except BaseException as e:          # noqa: BLE001 - reported below, never lost in a thread
                errors.append(repr(e))
        return run_it

    others = [threading.Thread(target=guard(lambda: figures.delete_figure(w.ip.index, w.ip.state_db, run, "a.png", caller=ann))),
              threading.Thread(target=guard(lambda: figures.write_confirmed(w.ip.state_db, ann.user_id, bundle, rid, time.time())))]
    monkeypatch.setattr(figures, "read_index", read_then_let_the_others_try)
    main = threading.Thread(target=guard(lambda: pack(w, ann, run, ["a.png"])))
    packer.append(main)
    main.start()
    main.join(20)
    for t in others:
        t.join(20)
    assert not errors, errors
    folder = gallery(w, ann, run)
    listed = sorted(real_read(str(folder))[0])
    on_disk = sorted(p.name for p in folder.iterdir() if p.suffix in (".png",))
    assert listed == on_disk == ["b.png", "new.png"], (listed, on_disk)
