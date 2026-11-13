# Nothing existing: the refusal tests of publish_figure that replaces a figure of the gallery (replace-needs-click, sibling of delete-needs-click in test_gallery_change_confirm.py).
"""replace-needs-click: a publish_figure request that would replace a figure of the gallery (its bundle `replaces` is not empty) is approved only
on the form or the confirmation page; a relayed yes (request_id + user_confirmed=true) is refused before confirm.approve, read-only. A publish under a
new name is as it was. TC IDs are from specs/replace-needs-click/test-case.md."""
import asyncio
import json
import time

import pytest

from helpers import tool_json
from human_harness import World, form_answer
from test_gallery_change import NAMES, ask_delete, ask_pack, gal, prints
from test_publish_figure import PNG, call, fig, gallery, index_of, press

NEW = PNG + b"N"


@pytest.fixture
def w(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    world.clock.t = time.time()
    return world


def allrows(w):
    return w.sql("SELECT * FROM confirmations ORDER BY created_at, id")


def args(run, figs, **extra):
    return dict({"run_id": run, "figures": figs}, **extra)


def new_a():
    return fig("a.png", NEW, code="new code\n", params="new=1")


def propose(w, ann, run, figs):
    return tool_json(w.call("publish_figure", args(run, figs), caller=ann))


def relay(w, ann, run, figs, rid):
    return tool_json(w.call("publish_figure", args(run, figs, request_id=rid, user_confirmed=True), caller=ann))


def no_jobs(w):
    return w.sql("SELECT * FROM jobs WHERE kind NOT IN ('launch_nextflow', 'cancel_run', 'preflight') AND confirmation_id IS NOT NULL") == []


def state_of(w, rid):
    return [r["state"] for r in allrows(w) if r["id"] == rid]


def setup_pending(w, figs=None):
    ann, run = gal(w, packed=("a.png",))
    figs = figs or [new_a()]
    before = prints(gallery(w, ann, run))
    first = propose(w, ann, run, figs)
    return ann, run, figs, before, first


# ---- US1: a relayed yes cannot replace ------------------------------------------------------------------------------------------------------

def test_rnc_a_relayed_replace_is_refused_with_the_page_and_nothing_is_consumed(w):
    # TC-001, TC-002, TC-003, TC-004
    from test_web_wording_sweep import banned_in
    ann, run, figs, before, first = setup_pending(w)
    rid, url = first["request_id"], first["url"]
    jobs = w.sql("SELECT * FROM jobs")
    n = len(allrows(w))
    out = relay(w, ann, run, figs, rid)
    assert out["state"] == "refused" and out["ok"] is False
    assert prints(gallery(w, ann, run)) == before
    assert url and out["url"] == url and url in out["message"]
    msg = out["message"]
    assert "本次存入會取代圖庫中既有的圖" in msg and "原圖無法復原" in msg and "須由本人在確認頁按下確認" in msg
    assert "cannot be undone" in msg and "confirmation page" in msg
    assert not banned_in(msg.split(" (")[0])
    assert "Traceback" not in msg and "SELECT" not in msg and str(w.ip.state_db.parent) not in msg
    rows = allrows(w)
    assert len(rows) == n
    last = [r for r in rows if r["id"] == rid][0]
    assert last["state"] == "pending" and last["channel"] is None and "content_base64" in last["bundle_json"]
    assert w.sql("SELECT * FROM jobs") == jobs


def test_rnc_the_person_can_still_press_after_the_relay_was_refused(w):
    # TC-005
    ann, run, figs, before, first = setup_pending(w)
    rid = first["request_id"]
    assert relay(w, ann, run, figs, rid)["state"] == "refused"
    press(w, "ann", rid)
    folder = gallery(w, ann, run)
    assert (folder / "a.png").read_bytes() == NEW
    assert (folder / "a.png.code.txt").read_text() == "new code\n" and (folder / "a.png.params.txt").read_text() == "new=1"
    now = prints(folder)
    assert now["b.png"] == before["b.png"] and now["c.png"] == before["c.png"]
    r = [x for x in allrows(w) if x["id"] == rid][0]
    assert r["state"] == "confirmed" and r["channel"] == "PAGE" and no_jobs(w)


def test_rnc_thirty_relays_replace_nothing_and_after_the_time_limit_the_old_refusal_stands(w):
    # TC-006, TC-007
    from abf_platform import confirm
    ann, run, figs, before, first = setup_pending(w)
    rid = first["request_id"]
    n = len(allrows(w))
    for _ in range(30):
        assert relay(w, ann, run, figs, rid)["state"] == "refused"
    assert prints(gallery(w, ann, run)) == before and len(allrows(w)) == n
    assert state_of(w, rid) == ["pending"]
    w.clock.t += confirm.PENDING_SECONDS + 5
    out = call(w, ann, run, figs, request_id=rid, user_confirmed=True)
    assert out["state"] == "refused" and "逾時" in out["message"] and "/c/" not in out["message"] and not out.get("url")
    from test_confirm_page import logged_in
    page = logged_in(w, "ann").get("/c/" + rid)
    assert page.status_code in (409, 410) and "name=\"csrf\"" not in page.text
    assert prints(gallery(w, ann, run)) == before


def test_rnc_the_gallery_changed_meanwhile_is_still_the_new_refusal_and_the_page_says_so(w):
    # TC-008
    from abf_platform.actions import figures
    ann, run, figs, before, first = setup_pending(w)
    rid = first["request_id"]
    figures.delete_figure(w.ip.index, w.ip.state_db, run, "a.png", caller=ann)
    out = relay(w, ann, run, figs, rid)
    assert out["state"] == "refused" and out["url"] == first["url"]          # the request said replaces: the new refusal, and it stays pending
    assert state_of(w, rid) == ["pending"]
    after = prints(gallery(w, ann, run))
    c, r = press(w, "ann", rid)
    assert r.status_code == 409 and "圖庫在申請送出後有變動" in r.text and "Traceback" not in r.text
    assert "a.png" not in prints(gallery(w, ann, run)) and prints(gallery(w, ann, run)) == after


def test_rnc_user_confirmed_alone_points_to_the_page_and_makes_no_row(w):
    # TC-009
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    n = len(allrows(w))
    out = tool_json(w.call("publish_figure", args(run, [new_a()], user_confirmed=True), caller=ann))
    assert out["state"] == "refused" and "確認頁" in out["message"] and "等本人在聊天裡回覆" not in out["message"]
    assert len(allrows(w)) == n and prints(gallery(w, ann, run)) == before


def test_rnc_the_first_answer_names_only_the_page(w):
    # TC-010
    ann, run, figs, before, first = setup_pending(w)
    assert first["state"] == "pending" and first["request_id"] and first["url"] and "覆蓋既有同名圖" in first["summary"]
    m = first["message"]
    assert first["url"] in m and "user_confirmed" not in m and "request_id" not in m and "原圖無法復原" in m
    assert prints(gallery(w, ann, run)) == before


def test_rnc_one_name_that_replaces_makes_the_whole_list_page_only(w):
    # TC-011
    ann, run = gal(w, packed=())
    before = prints(gallery(w, ann, run))
    figs = [fig("new.png", PNG + b"2"), new_a()]
    rid = propose(w, ann, run, figs)["request_id"]
    out = relay(w, ann, run, figs, rid)
    assert out["state"] == "refused" and out["url"]
    assert prints(gallery(w, ann, run)) == before and "new.png" not in index_of(w, ann, run)
    assert state_of(w, rid) == ["pending"]
    press(w, "ann", rid)
    assert sorted(index_of(w, ann, run)) == ["a.png", "b.png", "c.png", "new.png"] and (gallery(w, ann, run) / "a.png").read_bytes() == NEW


# ---- US2: other invalid relays are refused as they were --------------------------------------------------------------------------------------

def test_rnc_the_refusals_of_other_people_and_invented_ids_give_no_page(w):
    # TC-012
    ann, run, figs, before, first = setup_pending(w)
    bob = w.user("bob")
    rid = first["request_id"]
    state = [(r["id"], r["state"], r["channel"]) for r in allrows(w)]
    outs = [tool_json(w.call("publish_figure", args(run, figs, request_id=rid, user_confirmed=True), caller=bob)),
            tool_json(w.call("publish_figure", args(run, figs, request_id=rid, user_confirmed=True), caller=None))]
    for bad in ("f" * 32, "x", "../../etc/passwd", "a" * 100):
        outs.append(relay(w, ann, run, figs, bad))
    for out in outs:
        assert out["state"] == "refused" and not out.get("url") and "/c/" not in out["message"] and "Traceback" not in out["message"]
    assert prints(gallery(w, ann, run)) == before and [(r["id"], r["state"], r["channel"]) for r in allrows(w)] == state


def test_rnc_other_kinds_and_changed_content_give_the_old_refusals(w):
    # TC-013
    ann, run, figs, before, first = setup_pending(w)
    rid = first["request_id"]
    pid = ask_pack(w, ann, run, ["b.png"])["request_id"]
    did = ask_delete(w, ann, run, "b.png")["request_id"]
    state = [(r["id"], r["state"]) for r in allrows(w)]
    outs = [relay(w, ann, run, figs, pid), relay(w, ann, run, figs, did),
            relay(w, ann, run, [fig("a.png", NEW, code="other\n")], rid),
            relay(w, ann, run, [new_a(), fig("b.png", NEW)], rid)]
    for out in outs:
        assert out["state"] == "refused" and not out.get("url") and "/c/" not in out["message"]
    assert prints(gallery(w, ann, run)) == before and [(r["id"], r["state"]) for r in allrows(w)] == state


def test_rnc_an_expired_and_a_voided_request_keep_their_own_refusals(w):
    # TC-014
    from abf_platform import confirm
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    old = propose(w, ann, run, [new_a()])["request_id"]
    w.clock.t += confirm.PENDING_SECONDS + 5
    out = call(w, ann, run, [new_a()], request_id=old, user_confirmed=True)
    assert out["state"] == "refused" and "逾時" in out["message"] and "/c/" not in out["message"] and not out.get("url")
    other = [fig("a.png", NEW, code="x\n")]
    tool_json(w.call("publish_figure", args(run, other), caller=ann, answer=form_answer("decline")))
    voided = [r["id"] for r in allrows(w) if r["state"] == "void" and r["void_reason"] and r["id"] != old][-1]
    out = call(w, ann, run, other, request_id=voided, user_confirmed=True)
    assert out["state"] == "refused" and "作廢" in out["message"] and "/c/" not in out["message"] and not out.get("url")
    assert prints(gallery(w, ann, run)) == before


def test_rnc_a_request_the_person_already_confirmed_is_not_a_new_refusal(w):
    # TC-015
    ann, run, figs, before, first = setup_pending(w)
    rid = first["request_id"]
    press(w, "ann", rid)
    press(w, "ann", call(w, ann, run, [fig("a.png", PNG + b"Z", code="z\n")])["request_id"])
    after = prints(gallery(w, ann, run))
    out = relay(w, ann, run, figs, rid)
    assert out["state"] == "ok" and "已存入圖庫" in out["message"] and not out.get("url")
    assert prints(gallery(w, ann, run)) == after and (gallery(w, ann, run) / "a.png").read_bytes() == PNG + b"Z"


# ---- US3: the person's own press still replaces ----------------------------------------------------------------------------------------------

def test_rnc_the_form_replaces_and_a_no_voids(w):
    # TC-016, TC-017
    ann, run = gal(w, packed=("a.png",))
    out = tool_json(w.call("publish_figure", args(run, [new_a()]), caller=ann, answer=form_answer()))
    assert out["state"] == "ok"
    folder = gallery(w, ann, run)
    assert (folder / "a.png").read_bytes() == NEW and (folder / "a.png.code.txt").read_text() == "new code\n"
    assert index_of(w, ann, run)["a.png"]["packed"] is False and allrows(w)[-1]["channel"] == "ELICITED" and no_jobs(w)
    before = prints(folder)
    out = tool_json(w.call("publish_figure", args(run, [fig("a.png", PNG + b"Q")]), caller=ann, answer=form_answer("decline")))
    assert out["state"] == "refused" and out["message"] and prints(folder) == before
    assert allrows(w)[-1]["state"] == "void"


def test_rnc_nobody_to_ask_is_as_it_was(w):
    # TC-018
    import shutil
    from abf_platform import store
    ann, run = gal(w)
    shutil.copytree(gallery(w, ann, run), store.figures_root(w.ip.state_db) / "local" / run)
    before = prints(gallery(w, ann, run))
    n = len(allrows(w))
    out = tool_json(w.call("publish_figure", args(run, [new_a()]), caller=None))
    assert out["state"] == "refused" and "沒有人可以" in out["message"]
    assert len(allrows(w)) == n and prints(gallery(w, ann, run)) == before


# ---- US4: a new name is as it was ------------------------------------------------------------------------------------------------------------

def test_rnc_a_new_name_is_confirmed_by_a_relayed_yes_as_before(w):
    # TC-019, TC-020
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    figs = [fig("new.png", PNG + b"9")]
    first = propose(w, ann, run, figs)
    assert "user_confirmed=true" in first["message"] and "request_id=%s" % first["request_id"] in first["message"] and "取代" not in first["message"]
    out = relay(w, ann, run, figs, first["request_id"])
    assert out["state"] == "ok"
    assert "new.png" in index_of(w, ann, run) and (gallery(w, ann, run) / "new.png.code.txt").exists()
    r = [x for x in allrows(w) if x["id"] == first["request_id"]][0]
    assert r["state"] == "confirmed" and r["channel"] == "CHAT" and no_jobs(w)
    now = prints(gallery(w, ann, run))
    for n in NAMES:
        assert now[n] == before[n]


# ---- US5: the name did not exist at the request, but does at the yes ------------------------------------------------------------------------

def _two_requests_for_a_new_name(w, name="ann", run_name="r1"):
    ann, run = gal(w, name=name, run_name=run_name, names=("b.png",), packed=())
    x = [fig("new.png", PNG + b"X", code="x\n")]
    y = [fig("new.png", PNG + b"Y", code="y\n")]
    rx = propose(w, ann, run, x)["request_id"]
    ry = propose(w, ann, run, y)["request_id"]
    return ann, run, x, y, rx, ry


def test_rnc_chat_cannot_replace_a_name_that_appeared_after_the_request(w):
    # TC-021
    ann, run, x, y, rx, ry = _two_requests_for_a_new_name(w)
    press(w, "ann", ry)
    before = prints(gallery(w, ann, run))
    out = relay(w, ann, run, x, rx)
    assert out["state"] == "refused" and "沒有接受這次確認" in out["message"] and not out.get("url") and "/c/" not in out["message"]
    assert "Traceback" not in out["message"]
    assert prints(gallery(w, ann, run)) == before and (gallery(w, ann, run) / "new.png").read_bytes() == PNG + b"Y"
    assert state_of(w, rx) == ["void"] and no_jobs(w)


def test_rnc_page_cannot_replace_a_name_that_appeared_after_the_request(w):
    # TC-022 (the page)
    ann, run, x, y, rx, ry = _two_requests_for_a_new_name(w)
    press(w, "ann", ry)
    before = prints(gallery(w, ann, run))
    c, r = press(w, "ann", rx)
    assert r.status_code == 409 and "圖庫在申請送出後有變動" in r.text and prints(gallery(w, ann, run)) == before
    assert state_of(w, rx) == ["void"]


def test_rnc_form_cannot_replace_a_name_that_appeared_after_the_request(w):
    # TC-022 (the form: the gallery gets the name while the form is open)
    ann, run, x, y, rx, ry = _two_requests_for_a_new_name(w)
    inner = form_answer()

    async def cb(context, params):
        press(w, "ann", ry)
        return await inner(context, params)
    out = tool_json(w.call("publish_figure", args(run, [fig("new.png", PNG + b"Z", code="z\n")]), caller=ann, answer=cb))
    assert out["state"] == "refused" and (gallery(w, ann, run) / "new.png").read_bytes() == PNG + b"Y"


def test_rnc_two_relays_for_one_new_name_the_second_replaces_nothing(w):
    # TC-023
    ann, run, x, y, rx, ry = _two_requests_for_a_new_name(w)
    assert relay(w, ann, run, x, rx)["state"] == "ok"
    out = relay(w, ann, run, y, ry)
    assert out["state"] == "refused" and (gallery(w, ann, run) / "new.png").read_bytes() == PNG + b"X"
    assert state_of(w, ry) == ["void"]


# ---- US6: the tool says it as it is -----------------------------------------------------------------------------------------------------------

def test_rnc_the_tool_description_and_parameters_say_a_replace_needs_the_click(w):
    # TC-024, TC-025, TC-026
    from abf_platform import mcp_server
    server = mcp_server.build_server(w.ip.index, w.ip.state_db)
    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    t = tools["publish_figure"]
    assert len(t.description) <= 600 and "user_confirmed" in t.description and "replac" in t.description.lower()
    props = t.input_schema["properties"]
    shared = "True only after the person themselves answered yes in the chat to this request; never fill it in for them."
    for k in ("request_id", "user_confirmed"):
        d = props[k]["description"]
        assert "replac" in d.lower() and "new name" in d.lower() and d != shared
    assert t.input_schema["required"] == ["run_id", "figures"]
    a = t.annotations
    assert (a.read_only_hint, a.destructive_hint, a.idempotent_hint) == (False, True, True)    # gallery-followups TC-009: publish_figure can overwrite a figure, so it is marked destructive
    for other in ("pack_figures", "launch", "cancel", "resume", "relaunch", "forget"):
        assert "replac" not in tools[other].input_schema["properties"].get("user_confirmed", {}).get("description", "").lower()


# ---- no old version is kept; the database holds no chat replace -----------------------------------------------------------------------------

def test_rnc_no_old_version_is_kept_and_no_chat_replace_in_the_database(w):
    # TC-029, TC-034
    ann, run, figs, before, first = setup_pending(w)
    rid = first["request_id"]
    relay(w, ann, run, figs, rid)
    press(w, "ann", rid)
    names = sorted(p.name for p in gallery(w, ann, run).iterdir())
    assert names == ["a.png", "a.png.code.txt", "a.png.params.txt", "b.png", "b.png.code.txt", "b.png.params.txt",
                     "c.png", "c.png.code.txt", "c.png.params.txt", "index.json"]
    for r in allrows(w):
        if r["kind"] == "publish_figure" and json.loads(r["bundle_json"]).get("replaces"):
            assert r["channel"] != "CHAT" and not (r["state"] == "confirmed" and r["channel"] is None)


# ---- B1 (an index that cannot be read) and B2 (a file on disk counts as replaced), from the adversarial review ------------------------------------

DAMAGED = b"{not json"


def damage(w, ann, run):
    (gallery(w, ann, run) / "index.json").write_bytes(DAMAGED)


def test_rnc_b1_a_publish_asked_with_an_unreadable_index_cannot_be_relayed(w):
    # B1' (request time): still accepted as pending with the warning, but click-only
    ann, run = gal(w)
    damage(w, ann, run)
    before = prints(gallery(w, ann, run))
    figs = [fig("a.png", NEW, code="new code\n")]
    first = propose(w, ann, run, figs)
    assert first["state"] == "pending" and first["warning"] and first["warning"] in first["summary"]
    m = first["message"]
    assert first["url"] in m and "user_confirmed" not in m and "request_id" not in m and first["warning"] in m
    n = len(allrows(w))
    for _ in range(3):
        out = relay(w, ann, run, figs, first["request_id"])
        assert out["state"] == "refused" and out["url"] == first["url"] and first["url"] in out["message"]
    assert prints(gallery(w, ann, run)) == before and len(allrows(w)) == n and state_of(w, first["request_id"]) == ["pending"]
    assert (gallery(w, ann, run) / "index.json").read_bytes() == DAMAGED


def test_rnc_b1_the_person_can_still_approve_it_on_the_page_and_in_the_form_and_sees_the_warning(w):
    ann, run = gal(w)
    damage(w, ann, run)
    figs = [fig("n.png", NEW)]
    first = propose(w, ann, run, figs)
    from test_confirm_page import logged_in
    page = logged_in(w, "ann").get("/c/" + first["request_id"] + "?lang=en")
    assert "damaged" in page.text
    press(w, "ann", first["request_id"])
    assert sorted(index_of(w, ann, run)) == ["n.png"] and [r["channel"] for r in allrows(w) if r["id"] == first["request_id"]] == ["PAGE"]
    ann2, run2 = gal(w, name="ann2", run_name="r2")
    damage(w, ann2, run2)
    seen = []
    out = tool_json(w.call("publish_figure", args(run2, figs), caller=ann2, answer=form_answer(seen=seen)))
    assert out["state"] == "ok" and sorted(index_of(w, ann2, run2)) == ["n.png"]
    assert "損毀" in str(seen[0])


def test_rnc_b1_a_relay_at_approval_finds_the_index_unreadable_and_writes_nothing(w):
    ann, run = gal(w)
    figs = [fig("new.png", NEW)]
    first = propose(w, ann, run, figs)            # the index was readable when it was asked
    damage(w, ann, run)
    before = prints(gallery(w, ann, run))
    out = relay(w, ann, run, figs, first["request_id"])
    assert out["state"] == "refused"
    assert prints(gallery(w, ann, run)) == before and not (gallery(w, ann, run) / "new.png").exists()


def test_rnc_b1_a_normal_request_bundle_is_unchanged(w):
    ann, run = gal(w)
    first = propose(w, ann, run, [fig("new.png", NEW)])
    r = [x for x in allrows(w) if x["id"] == first["request_id"]][0]
    assert sorted(json.loads(r["bundle_json"])) == ["figures", "replaces", "replaces_ids", "run_id", "run_name"]


def _disk_only(w, ann, run, *leaves):
    folder = gallery(w, ann, run)
    idx = json.loads((folder / "index.json").read_text())
    idx["figures"].pop("a.png", None)
    (folder / "index.json").write_text(json.dumps(idx))
    for p in folder.iterdir():
        if p.name.startswith("a.png") and p.name not in leaves:
            p.unlink()


@pytest.mark.parametrize("leaves", [("a.png", "a.png.code.txt", "a.png.params.txt"), ("a.png.code.txt",), ("a.png.params.txt",)])
def test_rnc_b2_a_file_on_disk_but_not_in_the_index_counts_as_replaced(w, leaves):
    ann, run = gal(w)
    _disk_only(w, ann, run, *leaves)
    before = prints(gallery(w, ann, run))
    figs = [new_a()]
    first = propose(w, ann, run, figs)
    assert "覆蓋既有同名圖" in first["summary"]
    r = [x for x in allrows(w) if x["id"] == first["request_id"]][0]
    assert json.loads(r["bundle_json"])["replaces"] == ["a.png"]
    out = relay(w, ann, run, figs, first["request_id"])
    assert out["state"] == "refused" and out["url"] == first["url"]
    assert prints(gallery(w, ann, run)) == before and state_of(w, first["request_id"]) == ["pending"]
    press(w, "ann", first["request_id"])          # the person's own click replaces it
    assert (gallery(w, ann, run) / "a.png").read_bytes() == NEW


def test_rnc_b2_a_file_that_appears_on_disk_after_the_request_is_not_overwritten(w):
    ann, run = gal(w)
    figs = [fig("new.png", NEW)]
    first = propose(w, ann, run, figs)
    (gallery(w, ann, run) / "new.png").write_bytes(b"theirs")
    out = relay(w, ann, run, figs, first["request_id"])
    assert out["state"] == "refused" and (gallery(w, ann, run) / "new.png").read_bytes() == b"theirs"
    second = propose(w, ann, run, [fig("new.png", NEW + b"2")])
    assert "覆蓋既有同名圖" in second["summary"]
    first2 = propose(w, ann, run, [fig("other.png", NEW)])
    (gallery(w, ann, run) / "other.png.params.txt").write_text("theirs")
    c, r = press(w, "ann", first2["request_id"])
    assert r.status_code == 409 and (gallery(w, ann, run) / "other.png.params.txt").read_text() == "theirs"
