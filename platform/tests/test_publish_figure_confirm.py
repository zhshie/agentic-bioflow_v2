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


def test_confirmed_row_keeps_bundle_until_forget(w):
    # TC-071, TC-083
    from abf_platform import confirm
    ann = w.user("ann")
    run = seed(w, "r1", "succeeded", ann)
    got = call(w, ann, run, [fig()])
    press(w, "ann", got["request_id"])
    assert rows(w)[0]["bundle_json"] and "content_base64" in rows(w)[0]["bundle_json"]
    confirm.forget_content(w.ip.state_db, "r1")
    assert not rows(w)[0]["bundle_json"]
    assert (gallery(w, ann, run) / "a.png").read_bytes() == PNG


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
    assert "⚠" in zh or "✓" in zh or "!" in zh or "待" in zh
    en = c.get("/c/" + got["request_id"] + "?lang=en").text
    assert "Confirm adding figures" in en and "Send" in en and not re.search(r"[　-鿿＀-￯]", en.split("<body", 1)[1])
    # another person, wrong CSRF
    other = logged_in(w, "bob")
    assert other.post("/c/" + got["request_id"], data={"csrf": csrf_of(zh)}).status_code == 403
    assert c.post("/c/" + got["request_id"], data={"csrf": "wrong"}).status_code == 403
    assert rows(w)[-1]["state"] == "pending"
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


def test_page_headers_and_css_are_unchanged(w):
    # TC-052
    from abf_platform import web
    src = (Path(web.__file__)).read_text(encoding="utf-8")
    base = subprocess.run(["git", "show", "origin/v3:platform/abf_platform/web.py"], capture_output=True, cwd=str(Path(web.__file__).parent), check=False)
    if base.returncode == 0:
        old = base.stdout.decode("utf-8")
        for name in ("_HEADERS", "LAUNCH_HEADERS", "CSS_SHA256"):
            m_old = re.search(r"^%s\s*=.*?(?=^\S)" % name, old, re.M | re.S)
            m_new = re.search(r"^%s\s*=.*?(?=^\S)" % name, src, re.M | re.S)
            assert (m_old and m_old.group(0)) == (m_new and m_new.group(0)), name
        routes = lambda t: sorted(re.findall(r"@app\.route\(\"([^\"]+)\"|Route\(\"([^\"]+)\"", t))
        assert routes(old) == routes(src)


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
    root = Path(__file__).resolve().parents[2]
    r = subprocess.run(["git", "diff", "origin/v3", "--", ".specify/memory/constitution.md"], cwd=str(root), capture_output=True)
    if r.returncode != 0:
        pytest.skip("no origin/v3 here")
    assert r.stdout == b""
