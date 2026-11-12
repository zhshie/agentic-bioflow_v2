# Nothing existing: the refusal tests of publish_figure, a write tool that joins the human confirmation channels (constitution safety net: "a new write tool joins this rule with its own refusal test before it ships").
"""mcp-publish-figure slice 1: publish_figure writes nothing until the person says yes on one of the channels. TC IDs are from
specs/mcp-publish-figure/test-case.md."""
import asyncio
import base64
import json
import re
import sqlite3
import subprocess
import time
from pathlib import Path

import pytest

from helpers import tool_json
from human_harness import World, csrf_of, form_answer
from test_confirm_page import logged_in
from test_publish_figure import PNG, b64, call, fig, gallery, press
from test_web_board import seed


@pytest.fixture
def w(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    world.clock.t = time.time()
    return world


def mcp_args(run, figures, **extra):
    return dict({"run_id": run, "figures": figures}, **extra)


def rows(w):
    return w.sql("SELECT * FROM confirmations ORDER BY created_at, id")


def no_files(w, ann, run):
    folder = gallery(w, ann, run)
    return not folder.exists() or not any(folder.iterdir())


# ---- US1: nothing is written without a yes -------------------------------------------------------------------------------------------

def test_unconfirmed_publish_writes_nothing(w):
    # TC-001, TC-087
    from abf_platform import actions
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    out = tool_json(w.call("publish_figure", mcp_args(run, [fig()]), caller=ann))
    assert out["state"] == "pending" and out["url"].startswith("/c/") or "/c/" in out["url"]
    assert out["count"] == 1 and len(rows(w)) == 1 and rows(w)[0]["kind"] == "publish_figure" and rows(w)[0]["state"] == "pending"
    assert no_files(w, ann, run)
    assert actions.list_figures(w.ip.index, w.ip.state_db, run, caller=ann)["figures"] == []
    assert w.sql("SELECT * FROM jobs WHERE kind = 'publish_figure'") == []


def test_model_cannot_confirm_itself(w):
    # TC-005, TC-006, TC-007, TC-008, TC-060
    from abf_platform import actions, confirm
    ann, bob = w.user("ann"), w.user("bob")
    run = seed(w, "r1", "succeeded", ann)
    args = mcp_args(run, [fig()])
    assert tool_json(w.call("publish_figure", dict(args, user_confirmed=True), caller=ann))["state"] == "refused"
    assert rows(w) == []
    rid = tool_json(w.call("publish_figure", args, caller=ann))["request_id"]
    # someone else's request id
    assert tool_json(w.call("publish_figure", dict(args, request_id=rid, user_confirmed=True), caller=bob))["state"] == "refused"
    # content changed
    changed = mcp_args(run, [fig(code="print(2)\n")], request_id=rid, user_confirmed=True)
    assert tool_json(w.call("publish_figure", changed, caller=ann))["state"] == "refused"
    # a token or a made-up id
    assert tool_json(w.call("publish_figure", dict(args, request_id="f" * 32, user_confirmed=True), caller=ann))["state"] == "refused"
    # approve through the action layer as bob
    with pytest.raises(confirm.NotApproved):
        actions.approve(w.ip.state_db, rid, confirmed_by=actions.PAGE, caller=bob, clock=w.clock)
    assert rows(w)[0]["state"] == "pending" and no_files(w, ann, run)


def test_no_one_to_press_is_not_a_success(w):
    # TC-009
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    out = tool_json(w.call("publish_figure", mcp_args(run, [fig()]), caller=None))
    assert out["state"] != "ok" and no_files(w, ann, run)
    assert all(r["channel"] != "TERMINAL" for r in rows(w))


@pytest.mark.parametrize("channel", ["ELICITED", "PAGE", "CHAT"])
def test_confirm_through_each_channel_writes_exactly_the_requested_figures(w, channel):
    # TC-002, TC-003, TC-004, TC-079
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    figs = [fig("a.png", caption="圖一"), fig("b.svg", b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="1"/></svg>', params="x=2")]
    args = mcp_args(run, figs)
    if channel == "ELICITED":
        out = tool_json(w.call("publish_figure", args, caller=ann, answer=form_answer()))
        assert out["state"] == "ok"
    elif channel == "PAGE":
        got = call(w, ann, run, figs)
        press(w, "ann", got["request_id"])
    else:
        rid = tool_json(w.call("publish_figure", args, caller=ann))["request_id"]
        out = tool_json(w.call("publish_figure", dict(args, request_id=rid, user_confirmed=True), caller=ann))
        assert out["state"] == "ok"
    folder = gallery(w, ann, run)
    idx = json.loads((folder / "index.json").read_text())
    assert sorted(idx["figures"]) == ["a.png", "b.svg"]
    assert (folder / "a.png").read_bytes() == PNG and idx["figures"]["a.png"]["caption"] == "圖一"
    assert (folder / "b.svg.params.txt").read_text() == "x=2" and idx["figures"]["b.svg"]["packed"] is False
    r = rows(w)
    assert len(r) == 1 and r[0]["state"] == "confirmed" and r[0]["channel"] == channel
    assert w.sql("SELECT * FROM jobs WHERE kind NOT IN ('launch_nextflow', 'cancel_run') AND confirmation_id IS NOT NULL") == []
    from abf_platform import confirm
    assert not [p for p in folder.iterdir() if p.name.startswith(".tmp-")] and confirm.NO_JOB_KINDS == ("publish_figure",)


def test_one_request_covers_the_whole_list(w):
    # TC-010, TC-040
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("a.png"), fig("b.png"), fig("c.png")])
    assert len(rows(w)) == 1
    press(w, "ann", got["request_id"])
    assert sorted(json.loads((gallery(w, ann, run) / "index.json").read_text())["figures"]) == ["a.png", "b.png", "c.png"]
    bad = call(w, ann, run, [fig("ok.png"), fig("bad.png", b"nope")])
    assert bad["state"] == "refused" and "bad.png" in bad["reason"] and "第 2 張" in bad["reason"]
    assert "Traceback" not in bad["reason"] and "/" not in bad["reason"].replace("(", "").split("：")[0]
    assert len(rows(w)) == 1


def test_pending_limit_and_expiry_are_the_existing_ones(w):
    # TC-065, TC-066, TC-067, TC-070
    from abf_platform import actions, confirm
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    first = call(w, ann, run, [fig("f0.png")])
    assert call(w, ann, run, [fig("f0.png")])["request_id"] == first["request_id"] and len(rows(w)) == 1
    for i in range(1, confirm.MAX_OPEN_PENDING):
        assert call(w, ann, run, [fig("f%d.png" % i)])["state"] == "pending"
    over = call(w, ann, run, [fig("over.png")])
    assert over["state"] == "refused" and over["reason"].startswith("未送出") and len(rows(w)) == confirm.MAX_OPEN_PENDING
    w.clock.t += confirm.PENDING_SECONDS + 5
    with pytest.raises(confirm.NotApproved) as e:
        actions.approve(w.ip.state_db, first["request_id"], confirmed_by=actions.PAGE, caller=ann, clock=w.clock)
    assert e.value.status == "expired" and no_files(w, ann, run)


def test_clean_work_does_not_use_the_publish_quota(w):
    # TC-066
    from abf_platform import confirm
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    for i in range(confirm.MAX_OPEN_PENDING):
        confirm.create_pending(w.ip.state_db, "clean_work", None, {"run_name": "x%d" % i, "work": "/w%d" % i}, "s", ann.user_id, clock=w.clock)
    assert call(w, ann, run, [fig()])["state"] == "pending"


def test_expired_or_void_request_never_writes_even_if_retried(w):
    # TC-049, TC-068
    from abf_platform import confirm
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    w.clock.t -= confirm.PENDING_SECONDS + 5       # made long ago by the real clock, so the retries below find it expired
    got = call(w, ann, run, [fig()])
    w.clock.t += confirm.PENDING_SECONDS + 5
    c = logged_in(w, "ann", w.web(clock=w.clock))
    r = c.post("/c/" + got["request_id"], data={"csrf": csrf_of(c.get("/c/" + got["request_id"]).text) or "x" * 32})
    assert r.status_code in (403, 410) and no_files(w, ann, run)
    args = mcp_args(run, [fig()], request_id=got["request_id"], user_confirmed=True)
    assert tool_json(w.call("publish_figure", args, caller=ann))["state"] == "refused" and no_files(w, ann, run)
    w2 = w.sql("SELECT state FROM confirmations")[0]["state"]
    assert w2 in ("pending", "void")


def test_decline_in_form_voids_and_writes_nothing(w):
    # TC-069
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    out = tool_json(w.call("publish_figure", mcp_args(run, [fig()]), caller=ann, answer=form_answer("decline")))
    assert out["state"] != "ok" and no_files(w, ann, run)
    assert all(r["state"] != "confirmed" for r in rows(w))


def test_write_failure_voids_the_request(w, monkeypatch):
    # TC-018, TC-050, TC-095
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("a.png")])

    def boom(*a, **k):
        raise OSError("read-only /secret/dir")
    monkeypatch.setattr(figures.os, "replace", boom)
    c, r = press(w, "ann", got["request_id"])
    assert r.status_code == 500 and "未存入" in r.text and "/secret" not in r.text and "OSError" not in r.text
    row = rows(w)[0]
    assert row["state"] == "void" and row["void_reason"] and "/secret" not in row["void_reason"]
    assert not (gallery(w, ann, run) / "index.json").exists() and not (gallery(w, ann, run) / "a.png").exists()
    assert csrf_of(r.text) is None or c.token not in r.text


def test_recheck_at_the_yes_voids_when_the_gallery_filled_up(w):
    # TC-019
    from abf_platform import confirm
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("new.png")])
    folder = gallery(w, ann, run)
    folder.mkdir(parents=True)
    entry = {"size": 1, "type": "png", "caption": "", "code_file": None, "params_file": None, "created": "t", "packed": False, "packed_at": None, "request_id": "x"}
    (folder / "index.json").write_text(json.dumps({"version": 1, "figures": {"g%d.png" % i: entry for i in range(30)}}))
    press(w, "ann", got["request_id"])
    assert rows(w)[0]["state"] == "void" and not (folder / "new.png").exists()


def test_resend_after_success_asks_again_and_overwrites(w):
    # TC-015
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    first = call(w, ann, run, [fig()])
    press(w, "ann", first["request_id"])
    again = call(w, ann, run, [fig()])
    assert again["state"] == "pending" and again["request_id"] != first["request_id"]
    press(w, "ann", again["request_id"])
    idx = json.loads((gallery(w, ann, run) / "index.json").read_text())
    assert list(idx["figures"]) == ["a.png"] and (gallery(w, ann, run) / "a.png").read_bytes() == PNG


def test_bundle_size_cap_and_message(w):
    # TC-037, TC-038
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)

    def size_of(pad):
        data = PNG + b"\0" * pad
        bundle = {"run_name": "r1", "run_id": run, "figures": [{"name": "a.png", "type": "png", "size": len(data), "sha256": __import__("hashlib").sha256(data).hexdigest(),
                                                                  "caption": "", "code": "", "params": "", "content_base64": b64(data)}]}
        return len(json.dumps(bundle).encode()), data
    # find the padding that makes the serialised bundle exactly 5 MiB (base64 grows in steps of 3 bytes, so tune with the caption-free parts)
    pad = 3 * 1024 * 1024 + 700000
    for _ in range(6):
        n, _ = size_of(pad)
        pad += (figures.MAX_BUNDLE_BYTES - n) * 3 // 4
    n, data = size_of(pad)
    while n > figures.MAX_BUNDLE_BYTES:
        pad -= 1
        n, data = size_of(pad)
    # a payload slightly over the cap is refused with the limit and the current size
    over_n, over = size_of(pad + 3 * 40)
    assert over_n > figures.MAX_BUNDLE_BYTES
    out = call(w, ann, run, [{"filename": "a.png", "content_base64": b64(over)}])
    assert out["state"] == "refused" and "5 MB" in out["reason"] and "MB）" in out["reason"] and "the figures together exceed the 5 MB limit" in out["reason"]
    assert rows(w) == []
    small = call(w, ann, run, [{"filename": "a.png", "content_base64": b64(PNG + b"\0" * 1000)}])
    assert small["state"] == "pending"


def test_unsent_content_is_cleared_after_the_keep_time(w):
    # TC-072
    from abf_platform import confirm
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    call(w, ann, run, [fig("a.png")])
    w.clock.t += confirm.KEEP_UNSENT_SECONDS + confirm.PENDING_SECONDS + 10
    confirm.create_pending(w.ip.state_db, "launch", "lab-a", {"x": 1}, "s", ann.user_id, clock=w.clock)     # the existing sweep runs on create
    assert not rows(w)[0]["bundle_json"]


# ---- the confirmation page -----------------------------------------------------------------------------------------------------------

def test_confirm_page_for_publish_figure(w):
    # TC-041 .. TC-048, TC-051, TC-053, TC-054
    ann, bob = w.user("ann"), w.user("bob")
    run = seed(w, "r1", "succeeded", ann)
    first = call(w, ann, run, [fig("a.png")])
    press(w, "ann", first["request_id"])
    code = "".join("line%d\n" % i for i in range(30))
    got = call(w, ann, run, [fig("a.png", caption="<script>alert(1)</script>", code=code + "<script>x</script>\n", params="p=<b>"), fig("b.png")])
    c = logged_in(w, "ann")
    zh = c.get("/c/" + got["request_id"]).text
    assert "存入圖庫確認" in zh and "以下為將存入圖庫的全部內容。確認無誤後，請按「送出」；按下後才會寫入圖庫。" in zh and "送出" in zh
    assert csrf_of(zh) and "a.png" in zh and "b.png" in zh and "覆蓋既有同名圖" in zh and "line19" in zh and "line20" not in zh and "31" in zh
    assert "&lt;script&gt;" in zh and "<script>" not in zh
    assert "<img" not in zh and "data:" not in zh and "style=" not in zh and not re.search(r"(?:src|href)=\"https?://", zh)
    assert re.search(r"<button[^>]*>\s*送出\s*</button>", zh) and re.search(r"<details open><summary>[^<]+</summary>", zh)      # TC-054: the state is in words, see test_confirm_page_states_say_it_in_words
    en = c.get("/c/" + got["request_id"] + "?lang=en").text
    assert "Confirm adding figures" in en and "Send" in en and not re.search(r"[　-鿿＀-￯]", en.split("<body", 1)[1])
    # another person, wrong CSRF
    other = logged_in(w, "bob")
    assert other.post("/c/" + got["request_id"], data={"csrf": csrf_of(zh)}).status_code == 403
    assert c.post("/c/" + got["request_id"], data={"csrf": "wrong"}).status_code == 403
    assert [r for r in rows(w) if r["id"] == got["request_id"]][0]["state"] == "pending"
    done = c.post("/c/" + got["request_id"], data={"csrf": csrf_of(zh)})
    assert done.status_code == 200 and "已存入圖庫 2 張。" in done.text and "工作編號" not in done.text and "href" in done.text
    c2 = logged_in(w, "ann")
    again = call(w, ann, run, [fig("c.png")])
    en_done = c2.post("/c/" + again["request_id"] + "?lang=en", data={"csrf": csrf_of(c2.get("/c/" + again["request_id"] + "?lang=en").text)})
    assert "Added" in en_done.text and "工作編號" not in en_done.text


def test_confirm_page_times_out_with_410(w):
    # TC-048
    from abf_platform import confirm
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig()])
    c = logged_in(w, "ann", w.web(clock=w.clock))
    token = csrf_of(c.get("/c/" + got["request_id"]).text)
    w.clock.t += confirm.PENDING_SECONDS + 5
    r = c.post("/c/" + got["request_id"], data={"csrf": token})
    assert r.status_code == 410 and no_files(w, ann, run)


# ---- the database --------------------------------------------------------------------------------------------------------------------

def _old_db(tmp_path):
    from test_cleanup_store import make_old
    return make_old(tmp_path / "platform.db")


def test_confirmations_check_migration(tmp_path):
    # TC-073, TC-075, TC-076, TC-092
    from abf_platform import store
    import test_cleanup_store as t
    db = tmp_path / "platform.db"
    con = sqlite3.connect(str(db))
    con.executescript(store.SCHEMA if hasattr(store, "SCHEMA") else "")
    con.close()
    con = store.connect_state(db)
    con.close()
    # an older table with only clean_work
    con = sqlite3.connect(str(db))
    con.execute("PRAGMA foreign_keys = OFF")
    old_sql = t.check_of(con, "confirmations").replace(", 'publish_figure'", "")
    assert "publish_figure" not in old_sql
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('c1', 'x', 'clean_work', 1)")
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('c2', 'x', 'launch', 1)")
    con.execute("ALTER TABLE confirmations RENAME TO confirmations_old")
    con.execute(old_sql.replace("confirmations", "confirmations", 1))
    con.execute("INSERT INTO confirmations SELECT * FROM confirmations_old")
    con.execute("DROP TABLE confirmations_old")
    con.commit()
    jobs_sql = t.check_of(con, "jobs")
    before_rows = con.execute("SELECT * FROM confirmations ORDER BY id").fetchall()
    con.close()
    assert "publish_figure" not in t.check_of(sqlite3.connect(str(db)), "confirmations")
    con = store.connect_state(db)
    assert "publish_figure" in t.check_of(con, "confirmations")
    assert [tuple(r) for r in con.execute("SELECT * FROM confirmations ORDER BY id")] == [tuple(r) for r in before_rows]
    assert con.execute("PRAGMA foreign_key_check").fetchall() == [] and t.check_of(con, "jobs") == jobs_sql
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('p', 'x', 'publish_figure', 1)")
    for kind in ("resume", ""):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('q', 'x', ?, 1)", (kind,))
    con.close()


def test_migration_of_the_oldest_database_also_takes_publish_figure(tmp_path):
    # TC-074, TC-077
    from abf_platform import store
    import test_cleanup_store as t
    db = _old_db(tmp_path)
    before = t.rows_of(db, "confirmations")
    con = store.connect_state(db)
    assert "publish_figure" in t.check_of(con, "confirmations")
    assert [tuple(r) for r in con.execute("SELECT * FROM confirmations ORDER BY rowid")][: len(before)] == before
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    con.execute("INSERT INTO confirmations (id, sha256, kind, created_at) VALUES ('p', 'x', 'publish_figure', 1)")
    con.close()


def test_migration_failure_rolls_back(tmp_path, monkeypatch):
    # TC-074
    from abf_platform import store
    import test_cleanup_store as t
    db = _old_db(tmp_path)
    before = t.rows_of(db, "confirmations")
    monkeypatch.setattr(store, "_migration_step", t._boom_on_copied)
    with pytest.raises(RuntimeError):
        store.connect_state(db)
    chk = sqlite3.connect(str(db))
    assert "publish_figure" not in t.check_of(chk, "confirmations")
    chk.close()
    assert t.rows_of(db, "confirmations") == before


def test_existing_kinds_unchanged(w):
    # TC-078
    from abf_platform import confirm, jobs
    assert confirm.JOB_KIND == {"launch": "launch_nextflow", "cancel": "cancel_run", "clean_work": "clean_work"}
    assert confirm.NO_JOB_KINDS == ("publish_figure",) and jobs.CONFIRMED
    ann = w.user("ann")
    o = w.launch(caller=ann, answer=form_answer())
    assert o["sent"] is True and o["job_id"]
    assert len(w.jobs("launch_nextflow")) == 1


def test_constitution_untouched():
    # TC-089
    from test_mcp_launch_pipeline import fetch_origin_v3
    why = fetch_origin_v3()
    if why:
        pytest.skip(why)
    root = Path(__file__).resolve().parents[2]
    r = subprocess.run(["git", "diff", "origin/v3", "--", ".specify/memory/constitution.md"], cwd=str(root), capture_output=True)
    if r.returncode != 0:
        pytest.skip("no origin/v3 here")
    assert r.stdout == b""


# ==== fix round: F4 (the database does not grow), F5 (a failed overwrite is undone), F6 (the yes re-checks), F2 (missing or weak tests), F3 ====

import hashlib
import os

from test_publish_figure import JPEG, SVG_OK


def stripped(row):
    """The bundle of a row: no image bytes in it, the facts of every figure still there."""
    assert row["bundle_json"] and "content_base64" not in row["bundle_json"]
    figs = json.loads(row["bundle_json"])["figures"]
    assert all({"name", "type", "size", "sha256", "caption"} <= set(f) for f in figs)
    return figs


def test_confirmed_row_keeps_bundle_until_forget(w):
    # TC-071 as the ruling F4 changes it (the lead names this rewrite): confirmed means the bytes are dropped, the metadata stays, the gallery files stay
    from abf_platform import confirm
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig(caption="c1")])
    assert "content_base64" in rows(w)[0]["bundle_json"]          # a pending request holds them: the person is shown, and the write needs them
    press(w, "ann", got["request_id"])
    row = rows(w)[0]
    figs = stripped(row)
    assert figs[0]["name"] == "a.png" and figs[0]["size"] == len(PNG) and figs[0]["sha256"] == hashlib.sha256(PNG).hexdigest() and figs[0]["caption"] == "c1"
    assert row["sha256"] and row["state"] == "confirmed"
    assert (gallery(w, ann, run) / "a.png").read_bytes() == PNG
    confirm.forget_content(w.ip.state_db, "r1")
    assert not rows(w)[0]["bundle_json"] and (gallery(w, ann, run) / "a.png").read_bytes() == PNG


def test_f4_void_and_expired_rows_lose_their_bytes_and_a_failed_write_at_once(w, monkeypatch):
    # ruling F4 (adversarial review 1): a declined, an expired and a failed request must not keep the images
    from abf_platform import confirm
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    tool_json(w.call("publish_figure", mcp_args(run, [fig("v.png")]), caller=ann, answer=form_answer("decline")))
    call(w, ann, run, [fig("e.png")])
    got = call(w, ann, run, [fig("f.png")])
    real = os.replace

    def boom(a, b):
        raise OSError("disk")
    monkeypatch.setattr(figures.os, "replace", boom)
    press(w, "ann", got["request_id"])
    monkeypatch.setattr(figures.os, "replace", real)
    failed = [r for r in rows(w) if r["id"] == got["request_id"]][0]
    assert failed["state"] == "void"
    stripped(failed)                                                 # at once, without waiting for the next request
    w.clock.t += confirm.PENDING_SECONDS + 5
    fresh = call(w, ann, run, [fig("n.png")])                         # the same person's next request sweeps
    for r in rows(w):
        if r["id"] == fresh["request_id"]:
            assert "content_base64" in r["bundle_json"]               # the one that is open keeps them
        else:
            stripped(r)


def test_f4_pending_content_per_person_is_capped_at_twenty_mib(w):
    # ruling F4: a constant of 20 MiB; more than that waiting is refused with the reason
    from abf_platform import confirm
    from abf_platform.actions import figures
    assert figures.MAX_PENDING_BYTES == 20 * 1024 * 1024
    ann, bob = w.user("ann"), w.user("bob")
    run, bob_run = seed(w, "r1", "succeeded", ann), seed(w, "r2", "succeeded", bob)

    def big(i):
        return fig("b%d.png" % i, PNG + bytes([i]) * (3 * 1024 * 1024 + 512 * 1024), code="")
    first = [call(w, ann, run, [big(i)]) for i in range(4)]
    assert [x["state"] for x in first] == ["pending"] * 4
    assert call(w, ann, run, [big(0)])["request_id"] == first[0]["request_id"]           # the same content again is the same request, not more bytes
    over = call(w, ann, run, [big(4)])
    assert over["state"] == "refused" and "20 MB" in over["reason"] and len(rows(w)) == 4
    assert call(w, bob, bob_run, [big(5)])["state"] == "pending"                          # somebody else's waiting requests are not counted
    w.clock.t += confirm.PENDING_SECONDS + 5
    assert call(w, ann, run, [big(4)])["state"] == "pending"                              # the expired ones do not count


def test_f4_replaying_a_finished_confirmed_call_says_done(w):
    # ruling F4 (adversarial review 7): `replaces` changes once the gallery has the name; the replay must still be recognised
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    args = mcp_args(run, [fig("a.png", code="print(2)\n")])      # a name the gallery does not have yet: the screen says nothing is replaced, and after the write the gallery has it
    rid = tool_json(w.call("publish_figure", args, caller=ann))["request_id"]
    confirmed = dict(args, request_id=rid, user_confirmed=True)
    assert tool_json(w.call("publish_figure", confirmed, caller=ann))["state"] == "ok"
    again = tool_json(w.call("publish_figure", confirmed, caller=ann))
    assert again["state"] == "ok" and "已存入圖庫" in again["message"] and "內容" not in again["message"].split("(")[0]
    assert [r["state"] for r in rows(w)] == ["confirmed"]      # the replay asked nothing new
    # a replay with other content is still refused
    assert tool_json(w.call("publish_figure", dict(confirmed, figures=[fig("a.png", code="print(3)\n")]), caller=ann))["state"] == "refused"


@pytest.mark.parametrize("target", ["a.png", "a.png.code.txt", "a.png.params.txt", "index.json"])
def test_f5_a_failed_overwrite_puts_every_old_byte_back(w, monkeypatch, target):
    # ruling F5 (adversarial review 3): the page said nothing was stored while a.png already held the new bytes
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    press(w, "ann", call(w, ann, run, [fig("a.png", code="old code\n", params="old=1"), fig("keep.png")])["request_id"])
    folder = gallery(w, ann, run)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    got = call(w, ann, run, [fig("a.png", PNG + b"\x09" * 5, code="new code\n", params="new=2")])
    real = os.replace

    def boom(src, dst):
        if os.path.basename(dst) == target:
            raise OSError("disk full")
        return real(src, dst)
    monkeypatch.setattr(figures.os, "replace", boom)
    c, r = press(w, "ann", got["request_id"])
    assert r.status_code == 500 and "沒有任何圖被存入" in r.text
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before
    assert [x["state"] for x in rows(w) if x["id"] == got["request_id"]] == ["void"]


def test_f5_a_failed_first_write_leaves_no_folder_content(w, monkeypatch):
    # ruling F5: the same for a gallery that did not exist: nothing is left, index.json included
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("a.png"), fig("b.png")])
    real = os.replace
    monkeypatch.setattr(figures.os, "replace", lambda s, d: (_ for _ in ()).throw(OSError("x")) if d.endswith("index.json") else real(s, d))
    press(w, "ann", got["request_id"])
    assert no_files(w, ann, run)


def test_f6_case_variants_approved_in_turn_only_the_first_lands(w):
    # ruling F6 (adversarial review 4): Fig.png, fig.png, Fig.png asked while the gallery was empty, then approved one after the other
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    one = call(w, ann, run, [fig("Fig.png", PNG + b"1", caption="one", code="")])
    two = call(w, ann, run, [fig("fig.png", PNG + b"2", caption="two", code="")])
    three = call(w, ann, run, [fig("Fig.png", PNG + b"3", caption="three", code="")])
    outcomes = [press(w, "ann", x["request_id"])[1] for x in (one, two, three)]
    assert outcomes[0].status_code == 200 and outcomes[1].status_code == 409 and outcomes[2].status_code == 409
    folder = gallery(w, ann, run)
    idx = json.loads((folder / "index.json").read_text())
    assert sorted(idx["figures"]) == ["Fig.png"] and idx["figures"]["Fig.png"]["caption"] == "one"
    assert (folder / "Fig.png").read_bytes() == PNG + b"1" and sorted(p.name for p in folder.iterdir()) == ["Fig.png", "Fig.png.params.txt", "index.json"]
    assert not (folder / "fig.png").exists()
    states = {x["id"]: x["state"] for x in rows(w)}
    assert [states[x["request_id"]] for x in (one, two, three)] == ["confirmed", "void", "void"]


def test_f6_a_request_that_did_not_say_replaces_does_not_replace(w):
    # ruling F6: the screen of the second request said nothing is replaced; if the gallery got the name meanwhile, nothing is written
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    first = call(w, ann, run, [fig("a.png", PNG + b"1")])
    second = call(w, ann, run, [fig("a.png", PNG + b"2")])
    assert "覆蓋" not in second["summary"]
    press(w, "ann", first["request_id"])
    c, r = press(w, "ann", second["request_id"])
    assert r.status_code == 409 and (gallery(w, ann, run) / "a.png").read_bytes() == PNG + b"1"
    # and a request that said replaces still replaces
    third = call(w, ann, run, [fig("a.png", PNG + b"3")])
    assert "覆蓋" in third["summary"]
    press(w, "ann", third["request_id"])
    assert (gallery(w, ann, run) / "a.png").read_bytes() == PNG + b"3"


# ---- F2 (the contract's cases that were missing or could not fail) ---------------------------------------------------------------------

def test_a_token_is_not_a_yes(w):
    # TC-008: a bearer token, the csrf of the page, the address of the page, a prefix of the id: none of them says yes
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    args = mcp_args(run, [fig()])
    rid = tool_json(w.call("publish_figure", args, caller=ann))["request_id"]
    csrf = csrf_of(logged_in(w, "ann").get("/c/" + rid).text)
    for fake in ("Bearer abf_pat_" + "a" * 20, csrf, "/c/" + rid, rid[:16], rid.upper(), rid + "x"):
        got = tool_json(w.call("publish_figure", dict(args, request_id=fake, user_confirmed=True), caller=ann))
        assert got["state"] == "refused", fake
    try:
        w.call("publish_figure", dict(args, token="abf_pat_" + "b" * 20, user_confirmed=True), caller=ann)
    except Exception:
        pass                                  # an argument that does not exist may be turned down by the schema itself
    assert [r["state"] for r in rows(w)] == ["pending"] and no_files(w, ann, run)


def test_confirmation_channel_is_never_terminal_and_the_form_is_the_only_form(w):
    # TC-009 (second half): the three channels are the ones the page shows
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    tool_json(w.call("publish_figure", mcp_args(run, [fig()]), caller=ann, answer=form_answer()))
    assert [r["channel"] for r in rows(w)] == ["ELICITED"]


def test_bundle_size_limit_to_the_byte(w):
    # TC-037, TC-038: a bundle whose bundle_json is exactly 5 MiB is taken; one byte more is refused with the limit and the size
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    raw = 3 * ((figures.MAX_BUNDLE_BYTES - 60000) // 4)
    data = PNG + b"\0" * (raw - len(PNG))
    probe = call(w, ann, run, [fig("a.png", data, code="", params="")])
    assert probe["state"] == "pending"
    base = len([r for r in rows(w) if r["id"] == probe["request_id"]][0]["bundle_json"].encode())
    pad = figures.MAX_BUNDLE_BYTES - base
    assert 0 < pad < figures.MAX_CODE_BYTES
    exact = call(w, ann, run, [fig("a.png", data, code="x" * pad, params="")])
    assert exact["state"] == "pending"
    assert len([r for r in rows(w) if r["id"] == exact["request_id"]][0]["bundle_json"].encode()) == figures.MAX_BUNDLE_BYTES
    over = call(w, ann, run, [fig("a.png", data, code="x" * (pad + 1), params="")])
    assert over["state"] == "refused" and "5 MB" in over["reason"] and "目前" in over["reason"] and "the figures together exceed the 5 MB limit" in over["reason"]


def test_confirm_page_states_say_it_in_words(w):
    # TC-054: pending, success, expired and failed pages each say their state in words (the same way the pages of the other kinds do: a
    # line of text with the class ok or bad), so that the colour of the class is never the only carrier of it
    from abf_platform import confirm
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)

    def status_lines(html):
        return [re.sub(r"<[^>]+>", "", m.group(2)).strip() for m in re.finditer(r'<p class="(ok|bad)">(.*?)</p>', html, re.S)]
    pending = call(w, ann, run, [fig("p.png")])
    c = logged_in(w, "ann", w.web(clock=w.clock))
    for lang, send in (("", "送出"), ("?lang=en", "Send")):
        page = c.get("/c/" + pending["request_id"] + lang).text
        assert re.search(r"<button[^>]*>\s*%s\s*</button>" % send, page) and re.search(r"<p>[^<]{10,}</p>", page)
    done = c.post("/c/" + pending["request_id"], data={"csrf": csrf_of(c.get("/c/" + pending["request_id"]).text)}).text
    assert any("已存入圖庫 1 張" in s for s in status_lines(done))
    done_en = c.get("/c/" + pending["request_id"] + "?lang=en").text
    assert any(s.startswith("Added 1 figures") for s in status_lines(done_en))
    old = call(w, ann, run, [fig("o.png")])
    csrf = csrf_of(c.get("/c/" + old["request_id"]).text)
    w.clock.t += confirm.PENDING_SECONDS + 5
    gone = c.post("/c/" + old["request_id"], data={"csrf": csrf})
    assert gone.status_code == 410 and any("逾時" in s for s in status_lines(gone.text))
    en_gone = c.get("/c/" + old["request_id"] + "?lang=en").text
    assert any("expired" in s for s in status_lines(en_gone))
    w.clock.t -= confirm.PENDING_SECONDS + 5
    bad = call(w, ann, run, [fig("x.png", PNG + b"x")])
    csrf = csrf_of(c.get("/c/" + bad["request_id"]).text)
    real = figures.os.replace
    figures.os.replace = lambda a, b: (_ for _ in ()).throw(OSError("no"))
    try:
        failed = c.post("/c/" + bad["request_id"], data={"csrf": csrf})
    finally:
        figures.os.replace = real
    assert failed.status_code == 500 and any("未存入" in s for s in status_lines(failed.text))
    en_void = c.get("/c/" + bad["request_id"] + "?lang=en").text
    assert any("voided" in s for s in status_lines(en_void))


def test_page_headers_and_css_are_unchanged(w):
    # TC-052 (a missing origin/v3 is a skip with its reason, never a silent pass)
    from abf_platform import web
    from test_mcp_launch_pipeline import fetch_origin_v3
    why = fetch_origin_v3()
    if why:
        pytest.skip(why)
    try:
        base = subprocess.run(["git", "show", "origin/v3:platform/abf_platform/web.py"], capture_output=True, cwd=str(Path(web.__file__).parent))
    except OSError as e:
        pytest.skip("git is not available here: %s" % e)
    if base.returncode != 0:
        pytest.skip("origin/v3 is not there, so the old web.py cannot be compared: " + base.stderr.decode("utf-8", "replace")[:200])
    old, src = base.stdout.decode("utf-8"), Path(web.__file__).read_text(encoding="utf-8")
    for name in ("_HEADERS", "LAUNCH_HEADERS"):
        pat = r"^%s\s*=.*?(?=^\S)" % name
        m_old, m_new = re.search(pat, old, re.M | re.S), re.search(pat, src, re.M | re.S)
        assert m_old and m_new, name + " is not found, so nothing was compared"
        assert m_old.group(0) == m_new.group(0), name
    routes = lambda t: sorted(re.findall(r"@app\.route\(\"([^\"]+)\"|Route\(\"([^\"]+)\"", t))
    assert routes(src) and sorted(routes(old) + [r for r in (("", "/run/figure"), ("", "/run/figure/delete"), ("", "/run/figures/pack")) if r not in routes(old)]) == routes(src)      # slice 2 (mcp-publish-figure-gallery) adds these three routes; once origin/v3 has them they are in `old` already
    # the stylesheet (and so the sha256 the CSP names) lives in web_board.py: that file is not touched at all
    board = subprocess.run(["git", "diff", "--stat", "origin/v3", "--", "platform/abf_platform/web_board.py"], capture_output=True, cwd=str(Path(web.__file__).parent))
    assert board.returncode == 0 and board.stdout == b""


def test_responses_and_logs_carry_no_secret_path_or_trace(w, monkeypatch, caplog, capsys):
    # TC-095: a refusal, an expiry and a failed write; what the person and the log are told holds no token, csrf, password, path, stack or SQL
    from abf_platform import confirm, store
    from abf_platform.actions import figures
    caplog.set_level(0)
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    texts = [call(w, ann, run, [fig("../x.png")])["reason"]]
    c = logged_in(w, "ann", w.web(clock=w.clock))
    csrfs = []
    expiring = call(w, ann, run, [fig("e.png")])
    csrfs.append(csrf_of(c.get("/c/" + expiring["request_id"]).text))
    w.clock.t += confirm.PENDING_SECONDS + 5
    texts.append(c.post("/c/" + expiring["request_id"], data={"csrf": csrfs[-1]}).text)
    w.clock.t -= confirm.PENDING_SECONDS + 5
    bad = call(w, ann, run, [fig("w.png", PNG + b"w")])
    csrfs.append(csrf_of(c.get("/c/" + bad["request_id"]).text))
    monkeypatch.setattr(figures.os, "replace", lambda a, b: (_ for _ in ()).throw(OSError("/secret/place failed")))
    texts.append(c.post("/c/" + bad["request_id"], data={"csrf": csrfs[-1]}).text)
    texts.append([r for r in rows(w) if r["id"] == bad["request_id"]][0]["void_reason"] or "")
    everything = "\n".join(texts) + caplog.text + capsys.readouterr().out + capsys.readouterr().err
    root = str(store.figures_root(w.ip.state_db))
    for secret in [x for x in csrfs if x] + ["correct horse battery", root, "/secret", "Traceback", "OSError", "sqlite", "SELECT ", "INSERT "]:
        assert secret not in everything, secret


def test_documents_describe_the_tool(w):
    # TC-096
    repo = Path(__file__).resolve().parents[2]
    platform_md = (repo / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    testing_md = (repo / "docs" / "TESTING.md").read_text(encoding="utf-8")
    changelog = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "Twenty-three tools" in platform_md and "publish_figure" in platform_md and "NO_JOB_KINDS" in platform_md and "index.json" in platform_md
    i = platform_md.index("`publish_figure` (mcp-publish-figure, slice 1)")
    para = platform_md[i:i + 4000].split("\n", 1)[0]
    assert "confirmation" in para or "presses 送出" in para
    assert "confirmed" in para and "dropped" in para            # F4: what the row keeps now
    j = testing_md.index("publish_figure")
    steps = testing_md[j:j + 4000]
    assert "<script" in steps and "送出" in steps and ("10 分鐘" in steps or "10 minutes" in steps)      # F8: not pressing for ten minutes writes nothing
    assert "mcp-publish-figure" in changelog


def test_migration_run_twice_gives_the_same_result(tmp_path):
    # F3 (ruling): opening a migrated database again changes nothing
    from abf_platform import store
    import test_cleanup_store as t
    db = _old_db(tmp_path)
    con = store.connect_state(db)
    con.close()
    first = sqlite3.connect(str(db))
    schema_1 = first.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name").fetchall()
    data_1 = {n: first.execute("SELECT * FROM %s" % n).fetchall() for n in ("confirmations", "jobs")}
    first.close()
    con = store.connect_state(db)
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    con.close()
    second = sqlite3.connect(str(db))
    assert second.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name").fetchall() == schema_1
    assert {n: second.execute("SELECT * FROM %s" % n).fetchall() for n in ("confirmations", "jobs")} == data_1
    assert "publish_figure" in t.check_of(second, "confirmations")
    second.close()


# ---- hardening round (lead ruling N1 to N6, 2026-11-13; the second adversarial review) ---------------------------------------------------

@pytest.mark.parametrize("field", ["code", "params"])
@pytest.mark.parametrize("bad", ["\x1b[1A\x1b[2K[1] harmless.png", "\x08\x08[2] evil.png", "\x1b[2J\x1b[H", "a‮b", "a​b", "﻿a",
                                 "a b", "a b", "a\x85b", "a\rb", "a\x7fb"])
def test_n1_code_and_params_refuse_control_and_format_characters(w, field, bad):
    # N1: ESC, backspace, bidi, zero width and the other line separators forged lines of the screen
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("a.png", **{field: bad})])
    assert got["state"] == "refused" and field in got["reason"] and w.confirmations() == []


@pytest.mark.parametrize("bad", ["a‮b", "a​b", "﻿a", "a⁦b"])
def test_n1_caption_refuses_format_characters(w, bad):
    # N1
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig("a.png", caption=bad)])
    assert got["state"] == "refused" and "caption" in got["reason"] and w.confirmations() == []


def test_n1_newline_and_tab_stay_legal_in_code_and_params(w):
    # N1: only the other control characters go
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    assert call(w, ann, run, [fig("a.png", code="a\n\tb\n", params="k=1\n\tj=2")])["state"] == "pending"


def test_n1_long_runs_of_spaces_are_collapsed_on_every_screen_but_not_in_the_file(w):
    # N1: display only; what is stored is what was sent
    from abf_platform import actions
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    pad = " " * 300
    code = "x = 1" + pad + "[2] other.png\n" + " " * 8 + "ok\n"
    got = call(w, ann, run, [fig("a.png", caption="c" + " " * 150 + "d", code=code, params="k" + pad + "= 1")])
    assert got["state"] == "pending" and " " * 9 not in got["summary"] and "[2] other.png" in got["summary"]
    assert " " * 8 + "ok" in got["summary"]                                              # a run of 8 is left alone
    assert " " * 9 not in w.confirmations()[0]["screen_text"]
    bundle = json.loads(w.confirmations()[0]["bundle_json"])
    assert bundle["figures"][0]["code"] == code                                          # the stored content is not altered
    en = actions.screen_for_page(bundle, [], "en")
    assert " " * 9 not in en
    press(w, "ann", got["request_id"])
    assert (gallery(w, ann, run) / "a.png.code.txt").read_text() == code


def test_n2_a_lone_surrogate_in_filename_or_run_id_is_refused_up_front(w):
    # N2: the refusal itself must be encodable (MCP turns an unencodable answer into a generic tool error)
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    for args in ((run, [fig("\ud800.png")]), ("\ud800", [fig()]), (run, [fig("a\udfff.png")])):
        got = call(w, ann, *args)
        assert got["state"] == "refused" and w.confirmations() == []
        json.dumps(got).encode("utf-8")
        got["message"].encode("utf-8")
        got["reason"].encode("utf-8")


def test_n2_an_echoed_bad_name_is_cut_and_has_no_control_characters(w):
    # N2: 3 kB of name with newlines was echoed whole
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    evil = "x\n[2] forged line\x1b[2J" * 150
    for name in (evil, evil + ".png", "a‮" * 100 + ".exe"):
        got = call(w, ann, run, [fig(name)])
        assert got["state"] == "refused" and len(got["reason"]) < 700, got["reason"][:200]
        assert not any(ch in got["reason"] for ch in "\n\r\x1b‮")
    got = call(w, ann, "r\n" + "z" * 400, [fig()])
    assert got["state"] == "refused" and "\n" not in got["reason"] and len(got["reason"]) < 400


def _break_replaces(figures, monkeypatch, fail_from, also_restore):
    real = figures.os.replace
    calls = []

    def boom(a, b):
        calls.append(b)
        if len(calls) >= fail_from and (also_restore or len(calls) == fail_from):
            raise OSError("disk full /secret/path")
        return real(a, b)
    monkeypatch.setattr(figures.os, "replace", boom)


def test_n3_when_the_restore_fails_too_the_answer_does_not_say_nothing_was_stored(w, monkeypatch):
    # N3: the gallery then holds new bytes with the old index; the person must be told it may be inconsistent
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    press(w, "ann", call(w, ann, run, [fig("a.png", PNG + b"1", code="")])["request_id"])
    second = call(w, ann, run, [fig("a.png", PNG + b"2", code="")])
    _break_replaces(figures, monkeypatch, 2, True)
    c, r = press(w, "ann", second["request_id"])
    assert "沒有任何圖被存入" not in r.text and "inconsistent" in r.text and "/secret" not in r.text
    assert not [p for p in gallery(w, ann, run).iterdir() if p.name.startswith(".tmp-")]


def test_n3_a_failed_write_that_restores_fine_still_says_nothing_was_stored(w, monkeypatch):
    # N3: the plain F5 case keeps its words
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    press(w, "ann", call(w, ann, run, [fig("a.png", PNG + b"1", code="")])["request_id"])
    second = call(w, ann, run, [fig("a.png", PNG + b"2", code="")])
    _break_replaces(figures, monkeypatch, 2, False)
    c, r = press(w, "ann", second["request_id"])
    assert "inconsistent" not in r.text and (gallery(w, ann, run) / "a.png").read_bytes() == PNG + b"1"


def test_n3_leftover_temporary_files_are_removed_before_the_next_write(w):
    # N3: a kill between two replaces leaves .tmp-* files; the next write into that gallery (confirm, pack, delete) clears them
    from abf_platform.actions import figures
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    press(w, "ann", call(w, ann, run, [fig("a.png")])["request_id"])
    folder = gallery(w, ann, run)
    for step in ("confirm", "pack", "delete"):
        (folder / ".tmp-deadbeef-0001").write_bytes(b"x")
        (folder / ".tmp-idx-0002").write_bytes(b"y")
        if step == "confirm":
            press(w, "ann", call(w, ann, run, [fig("b.png")])["request_id"])
        elif step == "pack":
            assert figures.pack_figures(w.ip.index, w.ip.state_db, run, ["a.png"], caller=ann)["ok"]
        else:
            assert figures.delete_figure(w.ip.index, w.ip.state_db, run, "b.png", caller=ann)["ok"]
        assert not [p for p in folder.iterdir() if p.name.startswith(".tmp-")], step
    assert (folder / "a.png").exists()


def test_n4_a_request_shown_against_an_older_figure_does_not_overwrite_a_newer_one(w):
    # N4: R2 said "replaces a.png" (v1); R3 replaced it with v3 first; R2's yes must not silently bury v3
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    press(w, "ann", call(w, ann, run, [fig("a.png", PNG + b"1", code="")])["request_id"])
    r2 = call(w, ann, run, [fig("a.png", PNG + b"2", code="")])
    r3 = call(w, ann, run, [fig("a.png", PNG + b"3", code="")])
    assert "覆蓋" in r2["summary"] and "覆蓋" in r3["summary"]
    assert press(w, "ann", r3["request_id"])[1].status_code == 200
    c, r = press(w, "ann", r2["request_id"])
    assert r.status_code == 409 and (gallery(w, ann, run) / "a.png").read_bytes() == PNG + b"3"
    assert {x["id"]: x["state"] for x in rows(w)}[r2["request_id"]] == "void"


def test_n4_the_same_request_still_replaces_when_the_gallery_did_not_move(w):
    # N4: the identity check does not get in the way of the ordinary replace, nor of a repeated call
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    press(w, "ann", call(w, ann, run, [fig("a.png", PNG + b"1", code="")])["request_id"])
    r2 = call(w, ann, run, [fig("a.png", PNG + b"2", code="")])
    assert call(w, ann, run, [fig("a.png", PNG + b"2", code="")])["request_id"] == r2["request_id"]
    assert press(w, "ann", r2["request_id"])[1].status_code == 200
    assert (gallery(w, ann, run) / "a.png").read_bytes() == PNG + b"2"


def test_n5_only_true_is_a_yes_at_the_action_layer(w):
    # N5: user_confirmed=1 (truthy, not True) skipped the pending-bytes cap and made a pending row
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)

    def big(i):
        return fig("b%d.png" % i, PNG + bytes([i]) * (3 * 1024 * 1024 + 512 * 1024), code="")
    for i in range(4):
        assert call(w, ann, run, [big(i)])["state"] == "pending"
    for truthy in (1, "yes", "true", [1]):
        got = call(w, ann, run, [big(4)], request_id="x", user_confirmed=truthy)
        assert got["state"] == "refused" and "20 MB" in got["reason"], truthy
    assert len(rows(w)) == 4 and no_files(w, ann, run)


def test_n6_the_stored_request_of_another_person_is_not_read(w, monkeypatch):
    # N6: facts() was read for any request id; nothing leaked, but the read must come after the owner check
    from abf_platform import confirm
    ann, bob = w.user("ann"), w.user("bob")
    run, bob_run = seed(w, "r1", "succeeded", ann), seed(w, "r2", "succeeded", bob)
    mine = call(w, ann, run, [fig("a.png")])
    seen = []
    real = confirm.facts
    monkeypatch.setattr(confirm, "facts", lambda p, rid: (seen.append(rid), real(p, rid))[1])
    got = call(w, bob, bob_run, [fig("a.png")], request_id=mine["request_id"], user_confirmed=True)
    assert got["state"] == "refused" and mine["request_id"] not in seen
    assert [r["state"] for r in rows(w)] == ["pending"]
