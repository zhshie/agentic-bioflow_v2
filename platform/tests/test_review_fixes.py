# Nothing existing: tests for the review findings of PR #115 (specs/009c-human-channel/ledger.md, "Fix round: code review"); the rules are ours.
"""009c fix round, one test per finding. Findings are numbered as in the review: 2 uploads, 3 login throttle, 4 session binding,
5 audit rows, 6 repeated calls, 7 web origin, 8 signing key, 9 pending cap and pruning, 10 reachable address."""
import asyncio
import json
import sqlite3

import pytest

from human_harness import World, csrf_of, form_answer
from helpers import tool_json
from test_human_channel import _approve_on_the_page


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def update(w, text, args=()):
    con = sqlite3.connect(str(w.ip.state_db))
    con.execute(text, args)
    con.commit()
    con.close()


# ---- finding 5: an audit row keeps that a person said yes ---------------------------------------------------------------------

def test_f5_a_queue_refusal_after_a_yes_keeps_the_channel_and_the_time_on_the_void_row(w):
    ann = w.user("ann")

    async def cb(context, params):
        from mcp_types import ElicitResult
        w.hand_over("run-one", slurm=None)
        return ElicitResult(action="accept", content={"送出": True})

    out = w.launch(caller=ann, answer=cb)
    assert out["sent"] is False and w.jobs() == []
    row = w.confirmations()[0]
    assert row["state"] == "void" and row["void_reason"]
    assert row["channel"] == "ELICITED" and row["confirmed_at"] is not None


def test_f5_the_same_on_the_page(w):
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    c = w.web()
    w.login(c, "ann")
    token = csrf_of(c.get("/c/" + rid).text)
    w.hand_over("run-one", slurm=None)
    c.post("/c/" + rid, data={"csrf": token})
    row = w.confirmations()[0]
    assert row["state"] == "void" and row["channel"] == "PAGE" and row["confirmed_at"] is not None and w.jobs() == []


# ---- finding 6: a repeated call after the agent took the job ---------------------------------------------------------------------

def test_f6_after_the_agent_claimed_the_job_a_repeated_launch_still_returns_it(w):
    ann = w.user("ann")
    first = w.launch(caller=ann)
    _approve_on_the_page(w, "ann", first["id"])
    job_id = w.jobs()[0]["id"]
    update(w, "UPDATE confirmations SET used_at = ?", (w.confirmations()[0]["created_at"] + 1,))
    update(w, "UPDATE jobs SET state = 'claimed'")
    for _ in range(2):
        again = w.launch(caller=ann)
        assert again["sent"] is True and again["job_id"] == job_id
    assert len(w.confirmations()) == 1 and len(w.jobs("launch_nextflow")) == 1


def test_f6_a_confirmed_cancel_is_never_asked_for_twice(w):
    w.hand_over()
    ann, bob = w.user("ann"), w.user("bob")
    first = tool_json(w.call("cancel", {"run_name": "run-one"}, caller=ann, answer=form_answer()))
    assert first["sent"] is True and len(w.jobs("cancel_run")) == 1
    job_id = w.jobs("cancel_run")[0]["id"]
    update(w, "UPDATE confirmations SET used_at = created_at + 1")
    update(w, "UPDATE jobs SET state = 'claimed'")
    for who in (ann, bob):
        again = tool_json(w.call("cancel", {"run_name": "run-one"}, caller=who))
        assert again["sent"] is True and again["job_id"] == job_id
    assert len(w.confirmations()) == 1 and len(w.jobs("cancel_run")) == 1


# ---- finding 9: a cap on open requests, and old rows lose their content -----------------------------------------------------------------

def test_f9_a_caller_has_at_most_ten_open_requests(w):
    ann, bob = w.user("ann"), w.user("bob")
    for i in range(10):
        assert w.launch(caller=ann, run="run-%02d" % i)["sent"] is False
    over = w.launch(caller=ann, run="run-over")
    assert over["ok"] is False and over["sent"] is False and "10" in over["message"]
    assert len([r for r in w.confirmations() if r["caller_user_id"] == ann.user_id]) == 10
    again = w.launch(caller=ann, run="run-03")             # the same content as an open one is that open one, not a new request
    assert again["ok"] is True and again["id"]
    assert w.launch(caller=bob, run="run-over")["ok"] is True


def test_f9_expired_and_void_rows_lose_their_content_after_seven_days(w):
    ann = w.user("ann")
    w.launch(caller=ann, answer=form_answer("decline"), run="run-a")
    old_pending = w.launch(caller=ann, run="run-b")["id"]
    ok = w.launch(caller=ann, answer=form_answer(), run="run-c")
    assert ok["sent"] is True
    day = 86400
    update(w, "UPDATE confirmations SET created_at = created_at - ?, expires_at = expires_at - ? WHERE expires_at IS NOT NULL", (8 * day, 8 * day))
    update(w, "UPDATE confirmations SET created_at = created_at - ? WHERE expires_at IS NULL", (8 * day,))
    fresh = w.launch(caller=ann, run="run-d")["id"]
    rows = {r["id"]: r for r in w.confirmations()}
    for rid in (w.sql("SELECT id FROM confirmations WHERE state = 'void'")[0]["id"], old_pending):
        r = rows[rid]
        assert r["bundle_json"] is None and r["screen_text"] is None
        assert r["sha256"] and r["kind"] == "launch" and r["caller_user_id"] == ann.user_id and r["created_at"] and r["state"]
    assert rows[ok["id"]]["bundle_json"] is not None
    assert rows[fresh]["bundle_json"] is not None


# ---- finding 3: the login throttle and the password limit ----------------------------------------------------------------------------------

def bad(w, c, name, n=1):
    return [w.login(c, name, "wrong-password-xx").status_code for _ in range(n)]


def test_f3_failures_are_counted_per_client_address_too(w):
    from abf_platform import web
    w.user("ann")
    c = w.web()
    codes = [w.login(c, "nobody-%d" % i, "wrong-password-xx").status_code for i in range(web.IP_FAIL_LIMIT)]
    assert set(codes) == {401}
    assert w.login(c, "ann").status_code == 429          # a name never tried, the right password, the same address: still blocked


def test_f3_a_live_counter_is_never_dropped_to_make_room(w, monkeypatch):
    from abf_platform import web
    monkeypatch.setattr(web, "MAX_TRACKED", 3)
    for n in ("n1", "n2", "n3", "fresh"):
        w.user(n)
    c = w.web()
    for n in ("n1", "n2", "n3"):
        assert bad(w, c, n) == [401]
    assert w.login(c, "fresh").status_code == 429        # no room for a new key: refused, nothing evicted
    assert bad(w, c, "n1", 4) == [401, 401, 401, 401]    # n1 still has its first failure: the fifth blocks it
    assert w.login(c, "n1").status_code == 429
    w.clock.t += web.FAIL_WINDOW + 1                     # the windows end; expired keys make room
    assert w.login(c, "fresh").status_code in (200, 303)


def test_f3_the_password_is_hashed_off_the_event_loop(w, monkeypatch):
    from abf_platform import store
    w.user("ann")
    seen = []
    real = store.check_web_password

    def spy(*a, **k):
        try:
            asyncio.get_running_loop()
            seen.append("loop")
        except RuntimeError:
            seen.append("thread")
        return real(*a, **k)

    monkeypatch.setattr(store, "check_web_password", spy)
    assert w.login(w.web(), "ann").status_code in (200, 303)
    assert seen == ["thread"]


def test_f3_the_password_limit_is_the_same_in_passwd_and_login(w):
    from abf_platform import store
    assert store.MAX_PASSWORD_CHARS == 1000
    w.user("ann", password=None)
    with pytest.raises(ValueError, match="1000"):
        store.set_web_password(w.ip.tokens, "ann", "p" * 1001)
    store.set_web_password(w.ip.tokens, "ann", "p" * 1000)
    c = w.web()
    r = w.login(c, "ann", "p" * 1001)                     # never cut down to the first 1000 characters
    assert r.status_code == 401 and "1000" in r.text
    assert w.login(c, "ann", "p" * 1000).status_code in (200, 303)
    assert "1000" in c.get("/login").text


# ---- finding 7: same-origin posts, and no plain http beyond this machine ------------------------------------------------------------------------

def test_f7_a_post_from_another_origin_is_refused_on_login_and_on_the_button(w):
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    c = w.web()
    evil = {"Origin": "https://evil.example"}
    r = c.post("/login", data={"name": "ann", "password": "correct horse battery"}, headers=evil)
    assert r.status_code == 403 and "set-cookie" not in r.headers
    assert c.post("/login", data={"name": "ann", "password": "correct horse battery"},
                  headers={"Referer": "https://evil.example/x"}).status_code == 403
    assert w.login(c, "ann").status_code in (200, 303)
    token = csrf_of(c.get("/c/" + rid).text)
    assert c.post("/c/" + rid, data={"csrf": token}, headers=evil).status_code == 403
    assert w.jobs() == [] and w.confirmations()[0]["state"] == "pending"
    same = {"Origin": "http://testserver"}
    assert c.post("/c/" + rid, data={"csrf": token}, headers=same).status_code == 200
    assert len(w.jobs("launch_nextflow")) == 1


def test_f7_the_public_origin_is_accepted_behind_a_proxy(w):
    w.user("ann")
    c = w.web(public_url="https://abf.example")
    r = c.post("/login", data={"name": "ann", "password": "correct horse battery"}, headers={"Origin": "https://abf.example"})
    assert r.status_code in (200, 303)


@pytest.mark.parametrize("args", [["--host", "0.0.0.0"], ["--host", "0.0.0.0", "--public-url", "http://abf.example"],
                                  ["--host", "::"], ["--host", "192.168.1.5", "--public-url", "http://192.168.1.5:8789"]])
def test_f7_f10_the_page_is_not_served_beyond_this_machine_without_an_https_address(w, args):
    from helpers import run_cli
    r = run_cli(["web", "--port", "0"] + args, env=w.data.env(), timeout=30)
    assert r.returncode != 0 and "--public-url" in r.stderr + r.stdout and "https" in r.stderr + r.stdout
    from abf_platform import store
    assert store.get_meta(w.ip.state_db, "web_base_url") is None


# ---- finding 8: the signing key ----------------------------------------------------------------------------------------------------------------

def test_f8_a_short_or_empty_key_file_stops_the_start(w, tmp_path):
    from abf_platform import web
    folder = tmp_path / "keys"
    folder.mkdir()
    for content in (b"", b"\n", b"short", b"x" * 31 + b"\n"):
        (folder / web.KEY_FILE).write_bytes(content)
        with pytest.raises(ValueError, match="32"):
            web._signing_key(folder)


def test_f8_a_new_key_is_written_whole_by_rename_and_kept(w, tmp_path):
    import os
    from abf_platform import web
    folder = tmp_path / "keys2"
    key = web._signing_key(folder)
    assert len(key) >= 32 and web._signing_key(folder) == key
    assert sorted(os.listdir(folder)) == [web.KEY_FILE]          # no temporary file left behind
    if os.name == "posix":
        assert (folder / web.KEY_FILE).stat().st_mode & 0o777 == 0o600


def test_f8_two_starts_at_once_end_with_one_key(w, tmp_path):
    import threading
    from abf_platform import web
    folder = tmp_path / "keys3"
    got = []
    ts = [threading.Thread(target=lambda: got.append(web._signing_key(folder))) for _ in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(got) == 8 and len(set(got)) == 1


# ---- finding 2: over HTTP the samplesheet must be inside the caller's own upload folder ------------------------------------------------------------------

CANARY_ROW = "CANARY-secret-row-5c1e"


def area_of(w, name):
    return w.ip.state_db.parent / "uploads" / name


def put_sheet(w, name, rel="s.csv", text=None):
    import shutil
    dest = area_of(w, name) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if text is None:
        shutil.copy(str(w.sheet), str(dest))
    else:
        dest.write_text(text, encoding="utf-8")
    return dest


def ask(w, caller, sheet, **over):
    _, outs = w.mcp([("launch", w.choices(samplesheet=str(sheet), **over))], caller=caller, raw=True)
    return tool_json(outs[0])


def test_f2_a_sheet_inside_the_callers_own_area_is_accepted_and_a_relative_path_means_that_area(w):
    ann = w.user("ann")
    inside = put_sheet(w, "ann")
    assert ask(w, ann, inside)["ok"] is True
    assert ask(w, ann, "s.csv", run="run-rel")["ok"] is True


def test_f2_a_sheet_outside_the_area_is_refused_without_echoing_paths_or_content(w, tmp_path):
    ann = w.user("ann")
    put_sheet(w, "ann")
    secret = tmp_path / "private" / "secret.csv"
    secret.parent.mkdir()
    secret.write_text("sample,fastq_1\n%s,/data/storage/rawdata/a.fastq.gz\n" % CANARY_ROW, encoding="utf-8")
    other = put_sheet(w, "bob", text="sample,fastq_1\n%s,/x.fq\n" % CANARY_ROW) if w.user("bob") else None
    for path in (secret, other, "../bob/s.csv", str(area_of(w, "ann")) + "/../bob/s.csv", "/etc/passwd"):
        out = ask(w, ann, path)
        text = json.dumps(out, ensure_ascii=False)
        assert out["ok"] is False and out["sent"] is False and "上傳" in out["message"], out
        assert CANARY_ROW not in text and str(secret) not in text and "private" not in text and "root:" not in text
        assert str(area_of(w, "bob")) not in text
    assert w.confirmations() == []


def test_f2_a_symlink_cannot_leave_the_area(w, tmp_path):
    import os
    ann = w.user("ann")
    secret = tmp_path / "elsewhere.csv"
    secret.write_text("sample,fastq_1\n%s,/data/storage/rawdata/a.fastq.gz\n" % CANARY_ROW, encoding="utf-8")
    area_of(w, "ann").mkdir(parents=True)
    try:
        os.symlink(str(secret), str(area_of(w, "ann") / "link.csv"))
        os.symlink(str(tmp_path), str(area_of(w, "ann") / "dir"))
    except (OSError, NotImplementedError):
        pytest.skip("no symlinks here")
    for p in ("link.csv", "dir/elsewhere.csv"):
        out = ask(w, ann, p)
        assert out["ok"] is False and CANARY_ROW not in json.dumps(out, ensure_ascii=False)
        assert "elsewhere" not in out["message"]


def test_f2_stdio_keeps_reading_any_path_and_the_root_is_a_setting(w, tmp_path, monkeypatch):
    out = tool_json(w.call("launch", w.choices(), caller=None, answer=form_answer()))      # stdio: today's behaviour
    assert out["sent"] is True
    ann = w.user("ann")
    assert ask(w, ann, w.sheet, run="run-x")["ok"] is False                                 # the default root is <data dir>/uploads
    monkeypatch.setenv("ABF_PLATFORM_UPLOADS", str(tmp_path))                               # the setting moves the root
    (tmp_path / "ann").mkdir()
    (tmp_path / "ann" / "s.csv").write_bytes(w.sheet.read_bytes())
    assert ask(w, ann, "s.csv", run="run-y")["ok"] is True


# ---- finding 4: an MCP session belongs to the token that opened it ---------------------------------------------------------------------------------

def _pat(w, user):
    from abf_platform import store
    return store.create_token(w.ip.tokens, kind="pat", user_id=user.user_id)


def _rpc(url, token, body, session=None):
    import httpx
    h = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    if token:
        h["Authorization"] = "Bearer " + token
    if session:
        h["Mcp-Session-Id"] = session
        h["Mcp-Protocol-Version"] = "2025-06-18"
    return httpx.post(url, json=body, headers=h, timeout=15)


INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}
LIST = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}


def test_f4_a_session_id_is_no_use_with_another_persons_token(w):
    from test_pat import _Served
    ann, bob = w.user("ann"), w.user("bob")
    pa, pb = _pat(w, ann), _pat(w, bob)
    with _Served(w.ip.index, w.ip.tokens) as s:
        opened = _rpc(s.url, pa, INIT)
        sid = opened.headers["mcp-session-id"]
        assert _rpc(s.url, pa, LIST, sid).status_code == 200                       # the owner
        assert _rpc(s.url, pb, LIST, sid).status_code in (401, 403)                # another valid token on ann's session
        assert _rpc(s.url, None, LIST, sid).status_code == 401                     # no token
        assert _rpc(s.url, pa, LIST, "0" * 32).status_code in (403, 404)           # a session this server never opened for anybody
        assert _rpc(s.url, pa, LIST, sid).status_code == 200                       # and the owner is not hurt by any of it


def test_f4_each_call_names_the_caller_of_that_request(w):
    from helpers import mcp_http_call
    from test_pat import _Served
    ann, bob = w.user("ann"), w.user("bob")
    pa, pb = _pat(w, ann), _pat(w, bob)
    with _Served(w.ip.index, w.ip.tokens) as s:
        for tok, who, run in ((pa, ann, "run-a"), (pb, bob, "run-b"), (pa, ann, "run-c")):
            _, outs = mcp_http_call(s.url, [("launch", w.in_area(who, w.choices(run=run)))], token=tok)
            assert tool_json(outs[0])["ok"] is True
    owners = {r["id"]: r["caller_user_id"] for r in w.confirmations()}
    assert sorted(owners.values()) == sorted([ann.user_id, bob.user_id, ann.user_id])


def test_f4_the_tools_read_the_caller_from_the_request_not_from_a_variable_of_the_session():
    import inspect
    from abf_platform import mcp_server
    src = inspect.getsource(mcp_server)
    assert "request_context" in src and "abf_caller" in src


# ---- finding 10: say when the confirmation address cannot be opened from where the caller is --------------------------------------------------------------

def test_f10_a_remote_caller_with_only_a_loopback_page_is_told_how_to_fix_it(w, monkeypatch):
    from abf_platform import http_auth
    ann = w.user("ann")
    monkeypatch.setattr(http_auth, "current_remote", lambda: True, raising=False)
    out = w.launch(caller=ann)
    assert out["sent"] is False and "127.0.0.1" in out["confirmation_url"]
    msg = out["message"]
    assert "--public-url" in msg and "https://" in msg and "只有" in msg           # only reachable on the platform machine
    # with a reachable address stored, there is nothing to warn about
    from abf_platform import store
    store.set_meta(w.ip.state_db, "web_base_url", "https://abf.example")
    out = w.launch(caller=ann, run="run-two")
    assert out["confirmation_url"].startswith("https://abf.example/c/") and "--public-url" not in out["message"]


def test_f10_a_caller_on_this_machine_gets_no_warning(w):
    out = w.launch(caller=w.user("ann"))
    assert "--public-url" not in out["message"]


def test_f10_remote_means_a_peer_or_a_host_name_beyond_loopback():
    from abf_platform import http_auth
    def scope(client, host):
        return {"client": client, "headers": [(b"host", host)]}
    assert http_auth.is_remote(scope(("127.0.0.1", 5), b"127.0.0.1:8788")) is False
    assert http_auth.is_remote(scope(("::1", 5), b"localhost:8788")) is False
    assert http_auth.is_remote(scope(("10.0.0.7", 5), b"10.0.0.2:8788")) is True
    assert http_auth.is_remote(scope(("127.0.0.1", 5), b"abf.example")) is True          # a proxy on this machine in front
