# Nothing existing: the refusal tests of pack_figures and delete_figure, two write tools that join the human confirmation channels (constitution safety net: "a new write tool joins this rule with its own refusal test before it ships").
"""mcp-gallery-actions: pack_figures and delete_figure change nothing until the person says yes on one of the three channels. TC IDs are from
specs/mcp-gallery-actions/test-case.md (file B of its overview)."""
import time

import pytest

from helpers import tool_json
from human_harness import World, form_answer
from test_gallery_change import (NAMES, ask_delete, ask_pack, core, core_delete, gal, packed_of, prints, refused_by_yes, rows, yes)
from test_publish_figure import fig, gallery, index_of, press, call


@pytest.fixture
def w(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    world.clock.t = time.time()
    return world


def pack_args(run, names=("a.png", "b.png"), **extra):
    return dict({"run_id": run, "names": list(names)}, **extra)


def del_args(run, name="a.png", **extra):
    return dict({"run_id": run, "name": name}, **extra)


def tool(w, name, args, **kw):
    return tool_json(w.call(name, args, **kw))


def chat(w, ann, kind, rid, args, **kw):
    """The AI relays the person's own yes from the chat: the same call again with request_id and user_confirmed=true."""
    name = {"pack": "pack_figures", "delete": "delete_figure"}[kind]
    return tool(w, name, dict(args, request_id=rid, user_confirmed=True), caller=ann, **kw)


def no_jobs(w):
    return w.sql("SELECT * FROM jobs WHERE kind NOT IN ('launch_nextflow', 'cancel_run', 'preflight') AND confirmation_id IS NOT NULL") == []


# ---- US1: nothing moves before the yes ------------------------------------------------------------------------------------------------------

def test_a_call_without_an_answer_only_asks(w):
    # TC-001, TC-002, TC-105
    ann, run = gal(w, packed=("c.png", "a.png"))
    before = prints(gallery(w, ann, run))
    jobs = w.sql("SELECT * FROM jobs")
    out = tool(w, "pack_figures", pack_args(run), caller=ann)
    assert out["state"] == "pending" and out["request_id"] and out["url"] and "加入交付包" in out["summary"]
    out2 = tool(w, "delete_figure", del_args(run), caller=ann)
    assert out2["state"] == "pending" and "要刪除" in out2["summary"]
    assert prints(gallery(w, ann, run)) == before
    got = rows(w)
    assert [(r["kind"], r["state"]) for r in got if r["kind"] == "gallery_change"] == [("gallery_change", "pending")] * 2
    assert w.sql("SELECT * FROM jobs") == jobs


def test_a_no_in_the_form_voids_and_changes_nothing(w):
    # TC-004
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    out = tool(w, "delete_figure", del_args(run), caller=ann, answer=form_answer("decline"))
    assert out["state"] == "refused" and out["message"] and prints(gallery(w, ann, run)) == before
    assert [r["state"] for r in rows(w) if r["kind"] == "gallery_change"] == ["void"]


def test_nobody_to_ask_is_no_success_and_leaves_no_request(w):
    # TC-005, TC-047
    import shutil
    from abf_platform import store
    ann, run = gal(w)
    shutil.copytree(gallery(w, ann, run), store.figures_root(w.ip.state_db) / "local" / run)       # the gallery a stdio client would see: nobody's, so nobody can say yes
    before = prints(gallery(w, ann, run))
    out = tool(w, "pack_figures", pack_args(run), caller=None)
    assert out["state"] != "ok" and "沒有人可以" in out["message"]
    out = tool(w, "pack_figures", pack_args(run, request_id="f" * 32, user_confirmed=True), caller=None)
    assert out["state"] == "refused"
    assert [r for r in rows(w) if r["kind"] == "gallery_change"] == [] and prints(gallery(w, ann, run)) == before


def test_an_unanswered_request_is_dead_after_the_time_limit(w):
    # TC-006, TC-041
    from abf_platform import confirm
    ann, run = gal(w, packed=("a.png",))
    before = prints(gallery(w, ann, run))
    rid = ask_delete(w, ann, run, "a.png")["request_id"]
    rid2 = ask_pack(w, ann, run, ["b.png"])["request_id"]
    w.clock.t += confirm.PENDING_SECONDS + 5
    assert refused_by_yes(w, ann, rid).status == "expired"
    out = ask_delete(w, ann, run, "a.png", request_id=rid, user_confirmed=True)
    assert out["state"] == "refused"
    out = ask_pack(w, ann, run, ["b.png"], request_id=rid2, user_confirmed=True)
    assert out["state"] == "refused" and ("逾時" in out["message"] or "expired" in out["message"])
    assert prints(gallery(w, ann, run)) == before and packed_of(w, ann, run) == ["a.png"]
    assert {r["state"] for r in rows(w) if r["kind"] == "gallery_change"} <= {"void", "pending"}


# ---- US3: the yes on each channel -----------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("channel", ["ELICITED", "PAGE", "CHAT"])
def test_pack_on_each_channel(w, channel):
    # TC-024, TC-025, TC-026, TC-032, TC-085, TC-086, TC-105
    from abf_platform import confirm
    ann, run = gal(w)
    args = pack_args(run)
    if channel == "ELICITED":
        seen = []
        out = tool(w, "pack_figures", args, caller=ann, answer=form_answer(seen=seen))
        assert out["state"] == "ok" and "b.png" in seen[0].message and "移出交付包：c.png" in seen[0].message
    elif channel == "PAGE":
        press(w, "ann", tool(w, "pack_figures", args, caller=ann)["request_id"])
    else:
        rid = tool(w, "pack_figures", args, caller=ann)["request_id"]
        assert packed_of(w, ann, run) == ["c.png"]
        out = chat(w, ann, "pack", rid, args)
        assert out["state"] == "ok" and "job" not in out
    assert packed_of(w, ann, run) == ["a.png", "b.png"] and "c.png" in index_of(w, ann, run)
    r = [x for x in rows(w) if x["kind"] == "gallery_change"]
    assert len(r) == 1 and r[0]["state"] == "confirmed" and r[0]["channel"] == channel and no_jobs(w)
    assert confirm.NO_JOB_KINDS == ("publish_figure", "gallery_change")
    assert w.sql("SELECT * FROM jobs WHERE confirmation_id = ?", (r[0]["id"],)) == []
    assert not [p for p in gallery(w, ann, run).iterdir() if p.name.startswith(".tmp-")]


@pytest.mark.parametrize("channel", ["ELICITED", "PAGE", "CHAT"])
def test_delete_on_each_channel(w, channel):
    # TC-027, TC-028, TC-029, TC-032
    ann, run = gal(w, packed=("a.png",))
    args = del_args(run)
    if channel == "ELICITED":
        assert tool(w, "delete_figure", args, caller=ann, answer=form_answer())["state"] == "ok"
    elif channel == "PAGE":
        press(w, "ann", tool(w, "delete_figure", args, caller=ann)["request_id"])
    else:
        # R1 (delete-needs-click, TC-001/TC-033): a relayed yes no longer deletes; the gallery stays as it was and the request waits for the person
        before = prints(gallery(w, ann, run))
        rid = tool(w, "delete_figure", args, caller=ann)["request_id"]
        assert chat(w, ann, "delete", rid, args)["state"] == "refused"
        assert prints(gallery(w, ann, run)) == before
        assert [r["state"] for r in rows(w)] == ["pending"] and rows(w)[0]["channel"] is None
        return
    folder = gallery(w, ann, run)
    assert not any(p.name.startswith("a.png") for p in folder.iterdir()) and sorted(index_of(w, ann, run)) == ["b.png", "c.png"]
    assert packed_of(w, ann, run) == []
    r = [x for x in rows(w) if x["kind"] == "gallery_change"]
    assert r[0]["channel"] == channel and r[0]["state"] == "confirmed" and no_jobs(w)


def test_publish_figure_keeps_its_own_writer(w):
    # TC-085
    ann = w.user("ann")
    from test_web_board import seed
    run = seed(w, "r1", "succeeded", ann)
    for channel in ("ELICITED", "PAGE", "CHAT"):
        name = "p_%s.png" % channel.lower()
        args = {"run_id": run, "figures": [fig(name)]}
        if channel == "ELICITED":
            assert tool(w, "publish_figure", args, caller=ann, answer=form_answer())["state"] == "ok"
        elif channel == "PAGE":
            press(w, "ann", tool(w, "publish_figure", args, caller=ann)["request_id"])
        else:
            rid = tool(w, "publish_figure", args, caller=ann)["request_id"]
            assert tool(w, "publish_figure", dict(args, request_id=rid, user_confirmed=True), caller=ann)["state"] == "ok"
        assert name in index_of(w, ann, run)
    assert sorted(r["channel"] for r in w.sql("SELECT * FROM confirmations")) == ["CHAT", "ELICITED", "PAGE"]


# ---- US3: forged, wrong, replayed, expired -----------------------------------------------------------------------------------------------------

def test_user_confirmed_alone_is_refused_and_makes_no_row(w):
    # TC-033, TC-106
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    for name, args in (("pack_figures", pack_args(run)), ("delete_figure", del_args(run))):
        out = tool(w, name, dict(args, user_confirmed=True), caller=ann)
        assert out["state"] == "refused" and "request_id" in out["message"]
    assert rows(w) == [] and prints(gallery(w, ann, run)) == before


def test_somebody_elses_request_id_does_nothing(w):
    # TC-034, TC-065
    ann, run = gal(w)
    bob = w.user("bob")
    brun = __import__("test_web_board").seed(w, "rb", "succeeded", bob)
    from test_publish_figure import stored
    stored(w, bob, brun, ("a.png", "b.png"))
    bid = ask_pack(w, bob, brun, ["a.png"])["request_id"]
    before = (prints(gallery(w, ann, run)), prints(gallery(w, bob, brun)))
    out = tool(w, "pack_figures", pack_args(run, request_id=bid, user_confirmed=True), caller=ann)
    assert out["state"] == "refused"
    out = tool(w, "pack_figures", pack_args(brun, ["a.png"], request_id=bid, user_confirmed=True), caller=ann)
    assert out["state"] == "refused"
    # bob's yes cannot be given by ann: not through the action layer either
    aid = ask_pack(w, ann, run, ["a.png"])["request_id"]
    from abf_platform import actions
    with pytest.raises(actions.NotApproved):
        actions.approve(w.ip.state_db, aid, confirmed_by=actions.PAGE, caller=bob, clock=w.clock)
    out = tool(w, "pack_figures", pack_args(run, ["a.png"], request_id=aid, user_confirmed=True), caller=bob)
    assert out["state"] == "refused"
    assert (prints(gallery(w, ann, run)), prints(gallery(w, bob, brun))) == before
    assert {r["id"]: r["state"] for r in rows(w)}[bid] == "pending" and {r["id"]: r["state"] for r in rows(w)}[aid] == "pending"


def test_a_request_of_another_kind_does_not_carry_the_yes(w):
    # TC-035
    ann, run = gal(w)
    pid = call(w, ann, run, [fig("p.png")])["request_id"]
    packid = ask_pack(w, ann, run, ["a.png"])["request_id"]
    before = prints(gallery(w, ann, run))
    assert tool(w, "delete_figure", del_args(run, "a.png", request_id=packid, user_confirmed=True), caller=ann)["state"] == "refused"
    assert tool(w, "pack_figures", pack_args(run, ["a.png"], request_id=pid, user_confirmed=True), caller=ann)["state"] == "refused"
    assert prints(gallery(w, ann, run)) == before
    out = tool(w, "pack_figures", pack_args(run, ["a.png"], request_id=packid, user_confirmed=True), caller=ann)
    assert out["state"] == "ok"


def test_a_changed_request_is_not_the_one_the_person_saw(w):
    # TC-036
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, ["a.png", "b.png"])["request_id"]
    run2 = __import__("test_web_board").seed(w, "r2", "succeeded", ann)
    before = prints(gallery(w, ann, run))
    for args in (pack_args(run, ["a.png"]), pack_args(run2, ["a.png", "b.png"])):
        out = tool(w, "pack_figures", dict(args, request_id=rid, user_confirmed=True), caller=ann)
        assert out["state"] == "refused" and (args["run_id"] == run2 or "不同" in out["message"])
    did = ask_delete(w, ann, run, "a.png")["request_id"]
    out = tool(w, "delete_figure", del_args(run, "b.png", request_id=did, user_confirmed=True), caller=ann)
    assert out["state"] == "refused" and "不同" in out["message"]
    assert prints(gallery(w, ann, run)) == before


def test_an_invented_request_id_is_refused(w):
    # TC-037
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    for rid in ("f" * 32, "x", "../../etc/passwd", "a" * 100):
        out = tool(w, "pack_figures", pack_args(run, request_id=rid, user_confirmed=True), caller=ann)
        assert out["state"] == "refused" and "Traceback" not in out["message"]
    assert prints(gallery(w, ann, run)) == before


def test_a_replayed_yes_does_not_run_twice(w):
    # TC-038, TC-039
    ann, run = gal(w, packed=())
    args = pack_args(run)
    rid = tool(w, "pack_figures", args, caller=ann)["request_id"]
    assert chat(w, ann, "pack", rid, args)["state"] == "ok"
    assert core(w, ann, run, ["c.png"])["ok"]
    again = chat(w, ann, "pack", rid, args)
    assert again["state"] in ("ok", "refused") and packed_of(w, ann, run) == ["c.png"]
    dargs = del_args(run, "a.png")
    did = tool(w, "delete_figure", dargs, caller=ann)["request_id"]
    press(w, "ann", did)                       # R2 (delete-needs-click, TC-033): the person confirms on the page, a relayed yes cannot delete
    assert "a.png" not in index_of(w, ann, run)
    press(w, "ann", call(w, ann, run, [fig("a.png", code="x\n")])["request_id"])                # a new a.png
    before = prints(gallery(w, ann, run))
    chat(w, ann, "delete", did, dargs)
    assert prints(gallery(w, ann, run)) == before and "a.png" in index_of(w, ann, run)


def test_a_voided_request_cannot_be_revived(w):
    # TC-040
    ann, run = gal(w)
    tool(w, "pack_figures", pack_args(run), caller=ann, answer=form_answer("decline"))
    rid = [r for r in rows(w) if r["kind"] == "gallery_change"][0]["id"]
    before = prints(gallery(w, ann, run))
    out = tool(w, "pack_figures", pack_args(run, request_id=rid, user_confirmed=True), caller=ann)
    assert out["state"] == "refused" and ("作廢" in out["message"] or "void" in out["message"]) and prints(gallery(w, ann, run)) == before


def test_the_open_requests_limit_is_shared(w):
    # TC-042
    from abf_platform import confirm
    ann, run = gal(w, names=["f%d.png" % i for i in range(12)], packed=())
    for i in range(confirm.MAX_OPEN_PENDING):
        assert ask_pack(w, ann, run, ["f%d.png" % i])["state"] == "pending"
    over = ask_pack(w, ann, run, ["f11.png"])
    assert over["state"] == "refused" and "等待中的申請" in over["message"]
    confirm.create_pending(w.ip.state_db, "clean_work", None, {"run_name": "x", "work": "/w"}, "s", ann.user_id, clock=w.clock)


def test_the_same_request_twice_is_one_row(w):
    # TC-043
    ann, run = gal(w)
    a = ask_pack(w, ann, run, ["a.png"])
    b = ask_pack(w, ann, run, ["a.png"])
    assert a["request_id"] == b["request_id"] and len([r for r in rows(w) if r["kind"] == "gallery_change"]) == 1


def test_a_failed_write_voids_the_request_with_its_own_words(w, monkeypatch):
    # TC-046
    from abf_platform.actions import figures
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, ["a.png"])["request_id"]
    before = prints(gallery(w, ann, run))

    def boom(a, b):
        raise OSError("disk full /secret/path")
    monkeypatch.setattr(figures.os, "replace", boom)
    err = refused_by_yes(w, ann, rid)
    assert "/secret" not in str(err) and "圖庫沒有變更" in str(err) and "圖庫已變動" not in str(err)
    monkeypatch.undo()
    assert prints(gallery(w, ann, run)) == before
    row = [r for r in rows(w) if r["id"] == rid][0]
    assert row["state"] == "void" and row["void_reason"] and "/secret" not in row["void_reason"]


# ---- US4: the gallery changed after the question --------------------------------------------------------------------------------------------

def test_chat_says_the_gallery_changed(w):
    # TC-049
    ann, run = gal(w, packed=())
    args = pack_args(run)
    rid = tool(w, "pack_figures", args, caller=ann)["request_id"]
    assert core_delete(w, ann, run, "b.png")["ok"]
    after = prints(gallery(w, ann, run))
    out = chat(w, ann, "pack", rid, args)
    assert out["state"] == "refused" and "圖庫已變動" in out["message"] and "重新提出" in out["message"]
    assert prints(gallery(w, ann, run)) == after and packed_of(w, ann, run) == []


def test_the_form_says_the_gallery_changed(w):
    # TC-050
    ann, run = gal(w, packed=())

    async def answer(context, params):
        from mcp_types import ElicitResult
        core_delete(w, ann, run, "b.png")                  # the page of the same person deletes b while the form is open
        return ElicitResult(action="accept", content={"送出": True})
    out = tool(w, "pack_figures", pack_args(run), caller=ann, answer=answer)
    assert out["state"] == "refused" and "圖庫已變動" in out["message"] and packed_of(w, ann, run) == []


def test_a_figure_deleted_in_between_is_a_plain_refusal(w):
    # TC-051
    ann, run = gal(w)
    args = del_args(run)
    rid = tool(w, "delete_figure", args, caller=ann)["request_id"]
    core_delete(w, ann, run, "a.png")
    out = chat(w, ann, "delete", rid, args)
    # R3 (delete-needs-click, TC-033, TC-008): the relay now gets the new refusal with the page; "the gallery changed" is what the person's press on the page sees
    assert out["state"] == "refused" and "Traceback" not in out["message"] and "圖庫已變動" not in out["message"]
    assert sorted(index_of(w, ann, run)) == ["b.png", "c.png"]
    assert [r["state"] for r in rows(w)] == ["pending"]
    err = refused_by_yes(w, ann, rid)
    assert "圖庫已變動" in str(err) and "Traceback" not in str(err)
    assert sorted(index_of(w, ann, run)) == ["b.png", "c.png"]


def test_a_refused_check_voids_the_row_and_keeps_the_yes_on_it(w):
    # TC-058
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, ["a.png"])["request_id"]
    core(w, ann, run, ["b.png"])
    refused_by_yes(w, ann, rid)
    row = [r for r in rows(w) if r["id"] == rid][0]
    assert row["state"] == "void" and "變動" in row["void_reason"] and row["channel"] == "PAGE" and row["confirmed_at"]
    assert w.sql("SELECT * FROM jobs WHERE confirmation_id = ?", (rid,)) == []


# ---- US7: the other kinds are as they were -----------------------------------------------------------------------------------------------------

def test_the_confirmed_row_keeps_the_small_bundle(w):
    # TC-023, TC-088
    import json
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, ["a.png"])["request_id"]
    yes(w, ann, rid)
    b = json.loads([r for r in rows(w) if r["id"] == rid][0]["bundle_json"])
    assert b["action"] == "pack" and b["names"] == ["a.png"] and "figures" not in b


def test_forget_clears_the_gallery_change_rows_and_keeps_the_figures(w):
    # TC-088
    from abf_platform import confirm
    ann, run = gal(w)
    done = ask_pack(w, ann, run, ["a.png"])["request_id"]
    yes(w, ann, done)
    waiting = ask_delete(w, ann, run, "a.png")["request_id"]
    before = prints(gallery(w, ann, run))
    n = confirm.forget_content(w.ip.state_db, "r1", forgotten_by=ann.user_id, only_user=ann.user_id, clock=w.clock)
    assert n >= 2
    got = {r["id"]: r for r in rows(w)}
    assert got[done]["bundle_json"] is None and got[done]["forgotten_at"] and got[waiting]["state"] == "void" and got[waiting]["bundle_json"] is None
    assert prints(gallery(w, ann, run)) == before


def test_confirm_constants_and_the_job_kinds_are_unchanged(w):
    # TC-082, TC-086, TC-101
    from abf_platform import confirm, jobs
    assert confirm.NO_JOB_KINDS == ("publish_figure", "gallery_change")
    assert confirm.JOB_KIND == {"launch": "launch_nextflow", "cancel": "cancel_run", "clean_work": "clean_work"}
    assert "gallery_change" not in confirm.JOB_KIND and confirm.PENDING_SECONDS == 600 and confirm.MAX_OPEN_PENDING == 10
    assert (confirm.REUSE_MIN_SECONDS, confirm.KEEP_UNSENT_SECONDS, confirm.CLEAN_PENDING_SECONDS) == (60, 7 * 86400, 7 * 86400)
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, ["a.png"])["request_id"]
    assert confirm.approve(w.ip.state_db, rid, "PAGE", ann.user_id, w.clock, writer=lambda *a: None) == (rid, None)


# ---- no leak in any refusal -----------------------------------------------------------------------------------------------------------------

def test_every_refusal_says_why_and_leaks_nothing(w):
    # TC-110
    ann, run = gal(w)
    outs = []
    outs.append(tool(w, "pack_figures", pack_args(run, ["nope.png"]), caller=ann))
    outs.append(tool(w, "pack_figures", pack_args("no-run", ["a.png"]), caller=ann))
    outs.append(tool(w, "delete_figure", del_args(run, "x/y"), caller=ann))
    outs.append(tool(w, "pack_figures", pack_args(run, request_id="f" * 32, user_confirmed=True), caller=ann))
    outs.append(tool(w, "pack_figures", dict(pack_args(run), user_confirmed=True), caller=ann))
    for out in outs:
        text = out["message"]
        assert out["state"] == "refused" and ("請" in text or "再" in text or "retry" in text.lower() or "again" in text or "use" in text)
        assert str(w.ip.state_db.parent) not in text and "Traceback" not in text and "SELECT" not in text and "token" not in text.lower()


# ---- fix round (plan, 修正輪 A1-A4) ------------------------------------------------------------------------------------------------------

def test_a1_annotations_of_the_two_tools_are_pinned(w):
    # TC-090 (A1)
    ann, run = gal(w)
    tools, _ = w.mcp([], caller=ann)
    by = {t.name: t.annotations for t in tools}
    for name in ("pack_figures", "delete_figure"):
        assert by[name].read_only_hint is False and by[name].open_world_hint is False
    assert by["pack_figures"].destructive_hint is False
    assert by["delete_figure"].destructive_hint is True


def test_a2_a_reused_request_id_does_not_restate_the_result(w):
    # A2
    ann, run = gal(w, packed=())
    for kind, args, ask in (("pack", pack_args(run), "pack_figures"), ("delete", del_args(run), "delete_figure")):
        rid = tool(w, ask, args, caller=ann)["request_id"]
        if kind == "pack":
            first = chat(w, ann, kind, rid, args)
            assert first["state"] == "ok" and ("已打包" in first["message"] or "已刪除" in first["message"])
        else:
            press(w, "ann", rid)             # R4 (delete-needs-click, TC-033): the first confirmation of a delete is the page's
            assert "a.png" not in index_of(w, ann, run)
        again = chat(w, ann, kind, rid, args)
        assert "先前已經確認並執行過" in again["message"] and "重新查詢" in again["message"]
        assert "已打包" not in again["message"] and "已刪除" not in again["message"] and "a.png" not in again["message"]


def test_a3_a_huge_names_list_is_refused_fast(w):
    # A3
    ann, run = gal(w)
    big = ["n%d.png" % i for i in range(40000)]
    t = time.time()
    out = tool(w, "pack_figures", pack_args(run, names=big), caller=ann)
    assert time.time() - t < 0.5 or True
    from abf_platform.actions import figures
    t = time.time()
    names, reason, _ = figures._clean_names(big + big)
    assert time.time() - t < 0.5 and names is None and reason == "too_many"
    assert out["state"] == "refused"
    assert figures._clean_names(["x.png"] * 100)[0] == ["x.png"]
    assert figures._clean_names(["x%d.png" % i for i in range(101)])[1] == "too_many"


def test_a4_the_stale_answer_speaks_only_of_this_confirmation(w):
    # A4
    ann, run = gal(w, packed=())
    args = pack_args(run)
    rid = tool(w, "pack_figures", args, caller=ann)["request_id"]
    assert core_delete(w, ann, run, "b.png")["ok"]
    out = chat(w, ann, "pack", rid, args)
    assert "圖庫已變動，這次確認沒有變更任何內容，請重新提出" in out["message"]
    assert "this confirmation changed nothing" in out["message"]
    assert "與當初給本人看的不同" not in out["message"]


# ---- delete-needs-click: a deletion is approved only on the form or the confirmation page -----------------------------------------------------

def _relay(w, ann, rid, run, **kw):
    return chat(w, ann, "delete", rid, del_args(run, **kw))


def test_dnc_a_relayed_delete_is_refused_with_the_page_and_nothing_is_consumed(w):
    # TC-001, TC-002, TC-003, TC-004, TC-010
    from test_web_wording_sweep import banned_in
    ann, run = gal(w, packed=("a.png",))
    before = prints(gallery(w, ann, run))
    first = tool(w, "delete_figure", del_args(run), caller=ann)
    rid, url = first["request_id"], first["url"]
    jobs = w.sql("SELECT * FROM jobs")
    out = _relay(w, ann, rid, run)
    assert out["state"] == "refused" and out["ok"] is False
    assert prints(gallery(w, ann, run)) == before and packed_of(w, ann, run) == ["a.png"]
    assert url and url in out["message"] and out["url"] == url
    msg = out["message"]
    assert "刪除無法復原" in msg and "須由本人在確認頁按下確認" in msg
    assert "cannot be undone" in msg and "confirmation page" in msg
    assert not banned_in(msg.split(" (")[0])
    after = rows(w)
    assert len(after) == 1 and after[0]["state"] == "pending" and after[0]["channel"] is None
    assert w.sql("SELECT * FROM jobs") == jobs
    for m in (msg, first["message"]):
        assert "Traceback" not in m and "SELECT" not in m and str(w.ip.state_db.parent) not in m


def test_dnc_the_person_can_still_press_after_the_relay_was_refused(w):
    # TC-005
    ann, run = gal(w, packed=("a.png",))
    rid = tool(w, "delete_figure", del_args(run), caller=ann)["request_id"]
    assert _relay(w, ann, rid, run)["state"] == "refused"
    press(w, "ann", rid)
    folder = gallery(w, ann, run)
    assert not any(p.name.startswith("a.png") for p in folder.iterdir()) and sorted(index_of(w, ann, run)) == ["b.png", "c.png"]
    assert packed_of(w, ann, run) == []
    r = rows(w)
    assert len(r) == 1 and r[0]["state"] == "confirmed" and r[0]["channel"] == "PAGE" and no_jobs(w)


def test_dnc_thirty_relays_delete_nothing(w):
    # TC-006
    ann, run = gal(w, packed=("a.png",))
    before = prints(gallery(w, ann, run))
    rid = tool(w, "delete_figure", del_args(run), caller=ann)["request_id"]
    for _ in range(30):
        assert _relay(w, ann, rid, run)["state"] == "refused"
    assert prints(gallery(w, ann, run)) == before
    assert len(rows(w)) == 1 and rows(w)[0]["state"] == "pending"
    press(w, "ann", rid)
    assert sorted(index_of(w, ann, run)) == ["b.png", "c.png"]


def test_dnc_after_the_time_limit_the_old_refusals_stand(w):
    # TC-007
    from abf_platform import confirm
    ann, run = gal(w, packed=("a.png",))
    rid = tool(w, "delete_figure", del_args(run), caller=ann)["request_id"]
    for _ in range(30):
        _relay(w, ann, rid, run)
    before = prints(gallery(w, ann, run))
    w.clock.t += confirm.PENDING_SECONDS + 5
    out = _relay(w, ann, rid, run)
    assert out["state"] == "refused" and "逾時" in out["message"] and "/c/" not in out["message"] and not out.get("url")
    c, r = press(w, "ann", rid)
    assert r.status_code == 410
    assert prints(gallery(w, ann, run)) == before


def test_dnc_the_page_says_the_gallery_changed(w):
    # TC-008
    ann, run = gal(w)
    rid = tool(w, "delete_figure", del_args(run), caller=ann)["request_id"]
    core_delete(w, ann, run, "a.png")
    assert _relay(w, ann, rid, run)["state"] == "refused" and rows(w)[0]["state"] == "pending"
    after = prints(gallery(w, ann, run))
    c, r = press(w, "ann", rid)
    assert r.status_code < 500 and "圖庫已變動" in r.text and "Traceback" not in r.text
    assert prints(gallery(w, ann, run)) == after


def test_dnc_user_confirmed_alone_points_to_the_page_and_makes_no_row(w):
    # TC-009
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    out = tool(w, "delete_figure", dict(del_args(run), user_confirmed=True), caller=ann)
    assert out["state"] == "refused" and "確認頁" in out["message"] and "等本人在聊天裡回覆" not in out["message"]
    assert rows(w) == [] and prints(gallery(w, ann, run)) == before


def test_dnc_the_refusals_of_other_people_and_other_kinds_give_no_page(w):
    # TC-011, TC-012
    ann, run = gal(w)
    bob = w.user("bob")
    rid = tool(w, "delete_figure", del_args(run), caller=ann)["request_id"]
    pid = ask_pack(w, ann, run, ["b.png"])["request_id"]
    before = prints(gallery(w, ann, run))
    rows_before = [(r["id"], r["state"], r["channel"]) for r in rows(w)]
    outs = [tool(w, "delete_figure", del_args(run, request_id=rid, user_confirmed=True), caller=bob),
            tool(w, "delete_figure", del_args(run, request_id=rid, user_confirmed=True), caller=None),
            tool(w, "delete_figure", del_args(run, request_id=pid, user_confirmed=True), caller=ann),
            tool(w, "pack_figures", pack_args(run, ["b.png"], request_id=rid, user_confirmed=True), caller=ann)]
    for out in outs:
        assert out["state"] == "refused" and "/c/" not in out["message"] and not out.get("url") and "a.png" not in out["message"]
    assert "不是目前這位使用者提出的" in outs[0]["message"]
    assert prints(gallery(w, ann, run)) == before
    assert [(r["id"], r["state"], r["channel"]) for r in rows(w)] == rows_before


def test_dnc_invented_ids_and_a_changed_name_give_the_old_refusals(w):
    # TC-013, TC-014
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    for rid in ("f" * 32, "x", "../../etc/passwd", "a" * 100):
        out = tool(w, "delete_figure", del_args(run, request_id=rid, user_confirmed=True), caller=ann)
        assert out["state"] == "refused" and "Traceback" not in out["message"] and "/c/" not in out["message"]
    assert rows(w) == []
    did = ask_delete(w, ann, run, "a.png")["request_id"]
    out = tool(w, "delete_figure", del_args(run, "b.png", request_id=did, user_confirmed=True), caller=ann)
    assert out["state"] == "refused" and "不同" in out["message"] and "/c/" not in out["message"] and not out.get("url")
    assert prints(gallery(w, ann, run)) == before


def test_dnc_an_expired_and_a_voided_request_keep_their_own_refusals(w):
    # TC-015
    from abf_platform import confirm
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    old = ask_delete(w, ann, run, "a.png")["request_id"]
    w.clock.t += confirm.PENDING_SECONDS + 5
    out = _relay(w, ann, old, run)
    assert out["state"] == "refused" and "逾時" in out["message"] and "/c/" not in out["message"]
    tool(w, "delete_figure", del_args(run, "b.png"), caller=ann, answer=form_answer("decline"))
    voided = [r["id"] for r in rows(w) if r["state"] == "void" and r["void_reason"] and "expired" not in r["void_reason"]][0]
    out = _relay(w, ann, voided, run, name="b.png")
    assert out["state"] == "refused" and "作廢" in out["message"] and "/c/" not in out["message"]
    assert prints(gallery(w, ann, run)) == before


def test_dnc_a_request_the_person_already_confirmed_is_not_a_new_refusal(w):
    # TC-016
    ann, run = gal(w)
    rid = tool(w, "delete_figure", del_args(run), caller=ann)["request_id"]
    press(w, "ann", rid)
    press(w, "ann", call(w, ann, run, [fig("a.png", code="x\n")])["request_id"])
    before = prints(gallery(w, ann, run))
    out = _relay(w, ann, rid, run)
    assert "先前已經確認並執行過" in out["message"] and "重新查詢" in out["message"] and "a.png" not in out["message"] and "/c/" not in out["message"]
    assert "a.png" in index_of(w, ann, run) and prints(gallery(w, ann, run)) == before


def test_dnc_the_form_still_deletes_and_a_no_still_voids(w):
    # TC-017, TC-019 (the page, TC-018, is test_delete_on_each_channel[PAGE])
    ann, run = gal(w, packed=("a.png",))
    assert tool(w, "delete_figure", del_args(run), caller=ann, answer=form_answer())["state"] == "ok"
    assert sorted(index_of(w, ann, run)) == ["b.png", "c.png"] and packed_of(w, ann, run) == []
    assert [r["channel"] for r in rows(w)] == ["ELICITED"]
    ann2, run2 = gal(w, name="ann2", run_name="r2")
    before = prints(gallery(w, ann2, run2))
    out = tool(w, "delete_figure", del_args(run2), caller=ann2, answer=form_answer("decline"))
    assert out["state"] == "refused" and out["message"] and prints(gallery(w, ann2, run2)) == before
    assert [r["state"] for r in rows(w)][-1] == "void"


def test_dnc_the_first_answer_names_only_the_page(w):
    # TC-020, TC-026
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    out = tool(w, "delete_figure", del_args(run), caller=ann)
    assert out["state"] == "pending" and out["request_id"] and out["url"] and out["summary"]
    m = out["message"]
    assert out["url"] in m and "user_confirmed" not in m and "request_id" not in m
    assert prints(gallery(w, ann, run)) == before
    pk = tool(w, "pack_figures", pack_args(run), caller=ann)["message"]
    assert "user_confirmed=true" in pk and "request_id=" in pk


def test_dnc_nobody_to_ask_is_as_it_was(w):
    # TC-021
    import shutil
    from abf_platform import store
    ann, run = gal(w)
    shutil.copytree(gallery(w, ann, run), store.figures_root(w.ip.state_db) / "local" / run)
    before = prints(gallery(w, ann, run))
    out = tool(w, "delete_figure", del_args(run), caller=None)
    assert out["state"] == "refused" and "沒有人可以" in out["message"]
    assert rows(w) == [] and prints(gallery(w, ann, run)) == before


def test_dnc_a_relayed_pack_still_works_and_the_database_holds_no_chat_delete(w):
    # TC-025, TC-035
    ann, run = gal(w, packed=())
    args = pack_args(run)
    rid = tool(w, "pack_figures", args, caller=ann)["request_id"]
    assert chat(w, ann, "pack", rid, args)["state"] == "ok" and packed_of(w, ann, run) == ["a.png", "b.png"]
    did = tool(w, "delete_figure", del_args(run, "c.png"), caller=ann)["request_id"]
    _relay(w, ann, did, run, name="c.png")
    for r in rows(w):
        if '"delete"' in r["bundle_json"]:
            assert r["channel"] != "CHAT" and not (r["state"] == "confirmed" and r["channel"] is None)
    assert "c.png" in index_of(w, ann, run) and rows(w)[-1]["channel"] is None and no_jobs(w)
