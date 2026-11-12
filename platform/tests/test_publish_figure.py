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
