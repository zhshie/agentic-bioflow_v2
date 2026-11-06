# Nothing existing: tests of the site's "no open connection" refusal reaching the pages (open_command, strict check, both pages); none of this was there before.
"""refusal-visibility: the site's refusal reason and its log-in line reach the confirmation page and the board.
TC numbers are in the comments, see specs/refusal-visibility/test-case.md."""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from abf_station import handlers, launch, rules
from abf_station.site import SiteResult
from human_harness import World, csrf_of

HOST = "nano4.nchc.org.tw"
GOOD = ("ssh -o ControlMaster=auto -o ControlPath=~/.ssh/cm-%r-%h-%p -o ControlPersist=8h -o ServerAliveInterval=60 u@" + HOST + " true")
WSL_GOOD = "wsl.exe -e " + GOOD
OPEN_CMD = "ssh -o ControlMaster=yes -o ControlPath=/tmp/cm-nano4 nano4 true"
NO_MASTER = "on_site: needs-human reason=no-master\n%s\n" % OPEN_CMD
RELOGIN = "Log in once in a WSL terminal first"
DOWN = "No open connection to the site. Log in once in a WSL terminal first (請先在 WSL 終端機登入站台): " + GOOD
ROOT = Path(__file__).resolve().parents[2]
PLATFORM = ROOT / "platform"
CE = {"platform": "slurm-platform", "workDir": "/data/work", "headQueue": "q"}


# ---- the station: one more key in the refusal ----------------------------------------------------------------------------

class ReachSite:
    def __init__(self, err):
        self.err = err

    def call(self, args, input=None, timeout=None):
        if args[0] == "--check-reach":
            return SiteResult(1, b"", self.err)
        return SiteResult(0, b"", "")


def station_refusal(monkeypatch, preflight):
    """What handlers.handle answers for a launch whose preflight fails: the real _prechecks, the real handle, a scripted preflight."""
    env = rules.clean_environment(CE)

    def run_launch(job, ctx, pf):
        launch._prechecks(job, ctx, preflight, env, {"ce": CE}, {"ce": CE})
        raise AssertionError("the preflight should have failed")

    monkeypatch.setattr(launch, "run_launch", run_launch)
    ctx = SimpleNamespace(site=None, settings_file="none.yml", job_started=time.monotonic())
    return handlers.handle({"kind": "launch_nextflow", "args": {}, "remaining": 3600}, ctx)


def reach_preflight(err):
    site = ReachSite(err)
    return lambda env, ctx: handlers.preflight(env, SimpleNamespace(site=site, settings_file="none.yml"))


def test_tcr001_002_no_master_adds_open_command_and_keeps_the_message(monkeypatch):
    # TC-001, TC-002
    state, body = station_refusal(monkeypatch, reach_preflight(NO_MASTER))
    assert state == "refused" and body["ok"] is False
    assert body["open_command"] == OPEN_CMD
    assert RELOGIN in body["message"] and OPEN_CMD in body["message"]


def test_tcr003_no_command_line_means_no_key(monkeypatch):
    # TC-003
    state, body = station_refusal(monkeypatch, reach_preflight("on_site: needs-human reason=no-master\n"))
    assert state == "refused" and "open_command" not in body and body["ok"] is False and RELOGIN in body["message"]


def test_tcr004_sessions_exhausted_has_no_open_command(monkeypatch):
    # TC-004
    err = "on_site: needs-human reason=sessions-exhausted\nssh -O exit -o ControlPath=/tmp/cm-nano4 nano4\n"
    state, body = station_refusal(monkeypatch, reach_preflight(err))
    assert state == "refused" and "open_command" not in body


def test_tcr005_a_java_refusal_has_no_open_command(monkeypatch):
    # TC-005
    verdict = {"ok": False, "checks": [{"name": "java", "status": "fail", "detail": "Java 11 found, 17 needed"}]}
    state, body = station_refusal(monkeypatch, lambda env, ctx: verdict)
    assert state == "refused" and "open_command" not in body and "java" in body["message"]


def _fake_on_site(tmp_path):
    (tmp_path / "fake-ssh").write_text("#!/bin/bash\nexit 255\n")
    (tmp_path / "fake-ssh").chmod(0o755)
    (tmp_path / "env.yaml").write_text("reach: ssh\nsite_host: me@example.org\n")
    env = {"LAB_SETTINGS_FILE": str(tmp_path / "env.yaml"), "ON_SITE_SSH_BIN": str(tmp_path / "fake-ssh"), "PATH": "/usr/bin:/bin"}
    out = subprocess.run(["bash", str(ROOT / "scripts" / "on_site.sh"), "true"], capture_output=True, text=True, env=env, cwd=str(ROOT))
    return out.stdout + out.stderr


@pytest.mark.skipif(shutil.which("bash") is None or sys.platform == "win32", reason="needs bash for on_site.sh")
def test_tcr006_the_command_is_the_line_on_site_prints(tmp_path, monkeypatch):
    # TC-006
    err = _fake_on_site(tmp_path)
    lines = [ln.strip() for ln in err.splitlines() if re.match(r"^\s*(wsl\.exe -e )?ssh\s", ln) and "ControlPath" in ln and " true" in ln]
    assert len(lines) == 1, err
    state, body = station_refusal(monkeypatch, reach_preflight("on_site: needs-human reason=no-master\n" + err))
    assert body["open_command"] == lines[0]


def _sources():
    for p in PLATFORM.rglob("*.py"):
        if "tests" in p.relative_to(PLATFORM).parts or p.name == "test_refusal_visibility.py":
            continue
        yield p, p.read_text(encoding="utf-8", errors="replace")


def _absent(*needles):
    return [(str(p.relative_to(ROOT)), n) for p, text in _sources() for n in needles if n in text]


def test_tcr007_no_command_template_in_the_sources():
    # TC-007
    assert _absent("ControlMaster=yes") == []
    hits = [h for h in _absent("ControlPersist") if h[0] != "platform/abf_platform/jobs.py"]
    assert hits == []


def test_tcr008_the_chat_command_is_not_baked_in():
    # TC-008
    assert _absent("nchc_t3c4", "u9613010", "cm-%r-%h-%p -i") == []


def test_tcr094_nothing_of_the_chat_command_or_site_login_command():
    # TC-094
    assert _absent("site_login_command", "-fN", "ControlPersist=12h", "-i ~/.ssh/") == []


def test_tcr090_091_nothing_of_c2_or_c3():
    # TC-090, TC-091
    assert _absent("site_link") == []
    assert _absent("abf-station connect", "abf-connect://") == []


# ---- the platform: the strict check ---------------------------------------------------------------------------------------

def clean(result, kind="launch_nextflow", host=HOST):
    from abf_platform import jobs
    return jobs.clean_result(kind, dict({"ok": False, "message": "m"}, **result), host=host)


@pytest.mark.parametrize("line", [GOOD, WSL_GOOD, "ssh -o A=b nano4.nchc.org.tw true"])
def test_tcr010_011_019_a_strict_line_is_kept(line):
    # TC-010, TC-011, TC-019
    assert clean({"open_command": line})["open_command"] == line


@pytest.mark.parametrize("bad", [";", "&&", "$(", "`", "\n", "|"])
def test_tcr012_a_shell_trick_drops_the_key(bad):
    # TC-012
    out = clean({"open_command": GOOD.replace("ServerAliveInterval=60", "ServerAliveInterval=60" + bad + "id")})
    assert "open_command" not in out and out["message"] == "m" and out["ok"] is False


def test_tcr013_601_characters_are_dropped():
    # TC-013
    pad = "-o K=" + "a" * (601 - len(GOOD) - 5 - 1)
    line = GOOD.replace(" -o ControlPersist", " " + pad + " -o ControlPersist")
    assert len(line) == 601 and "open_command" not in clean({"open_command": line})
    ok = GOOD.replace(" -o ControlPersist", " -o K=" + "a" * 20 + " -o ControlPersist")
    assert "open_command" in clean({"open_command": ok})


@pytest.mark.parametrize("value", [None, 5, ["x"], {"a": 1}, True])
def test_tcr014_not_a_string_is_dropped(value):
    # TC-014
    assert "open_command" not in clean({"open_command": value})


@pytest.mark.parametrize("kind", ["put_upload", "clean_work", "preflight"])
def test_tcr015_other_kinds_never_keep_it(kind):
    # TC-015
    with_it = clean({"open_command": GOOD}, kind=kind)
    without = clean({}, kind=kind)
    assert with_it == without and "open_command" not in with_it


def test_tcr016_a_foreign_host_is_dropped():
    # TC-016
    out = clean({"open_command": GOOD.replace(HOST, "evil.example.org")})
    assert "open_command" not in out and out["message"] == "m" and out["ok"] is False


@pytest.mark.parametrize("host", [None, ""])
def test_tcr017_018_no_host_on_record_drops_it(host):
    # TC-017, TC-018
    out = clean({"open_command": GOOD}, host=host)
    assert "open_command" not in out and out["message"] == "m"


def test_tcr020_the_other_fields_are_cleaned_as_before():
    # TC-020
    fields = {"slurm_job_id": 7, "run_name": "r", "run_folder": "/f", "left_on_site": "x", "message": "y" * 3000}
    base = clean(fields)
    with_good = clean(dict(fields, open_command=GOOD))
    with_bad = clean(dict(fields, open_command="x; y"))
    assert {k: v for k, v in with_good.items() if k != "open_command"} == base == with_bad
    assert len(base["message"]) == 2000


# ---- the pages -------------------------------------------------------------------------------------------------------------

@pytest.fixture
def w(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    world.sql("SELECT 1")
    import sqlite3
    con = sqlite3.connect(str(world.ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET config_json = json_set(config_json, '$.hostName', ?)", (HOST,))
    con.close()
    return world


def logged_in(w, name):
    c = w.web()
    assert w.login(c, name).status_code in (200, 303)
    return c


def queue(w, caller, client=None, **over):
    """A launch the person has pressed: returns (confirmation id, job id)."""
    rid = w.launch(caller=caller, **over)["id"]
    c = client or logged_in(w, caller.name)
    page = c.get("/c/" + rid)
    assert c.post("/c/" + rid, data={"csrf": csrf_of(page.text)}).status_code == 200
    return rid, [j for j in w.jobs("launch_nextflow") if j["confirmation_id"] == rid][0]["id"]


def settle(w, job_id, state="refused", message=DOWN, open_command=GOOD, agent=None, finished=None, raw=None):
    import sqlite3
    result = raw if raw is not None else {"ok": False, "message": message}
    if raw is None and open_command is not None:
        result["open_command"] = open_command
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE jobs SET state = ?, result_json = ?, finished_at = ? WHERE id = ?",
                    (state, json.dumps(result), w.clock() if finished is None else finished, job_id))
        if agent is not None:
            con.execute("UPDATE jobs SET agent = ? WHERE id = ?", (agent, job_id))
    con.close()


def refused_page(w, name="ann", **kw):
    ann = w.user(name)
    rid, job = queue(w, ann)
    settle(w, job, **kw)
    return ann, rid, job, logged_in(w, name)


def block_of(html):
    m = re.search(r'<section id="refusal">.*?</section>', html, re.S)
    return m.group(0) if m else None


def test_tcr021_to_026_the_confirm_page_shows_reason_and_command(w):
    # TC-021, TC-022, TC-023, TC-024, TC-025, TC-026, TC-027
    ann, rid, job, c = refused_page(w, agent="agent-1")
    zh = c.get("/c/" + rid).text
    assert re.search(r"<pre>\s*%s\s*</pre>" % re.escape(GOOD), zh)
    for want in ("站台連線沒開，工作沒有送出", "平台主機 agent-1", "WSL 終端機", "passphrase", "OTP", "重新呼叫 launch"):
        assert want in zh, want
    en = c.get("/c/" + rid + "?lang=en").text
    for want in ("The connection to the site is not open; nothing was submitted.", "station host agent-1",
                 "paste this line into a WSL terminal, enter your passphrase and OTP, then call launch again"):
        assert want in en, want
    assert re.search(r"<pre>\s*%s\s*</pre>" % re.escape(GOOD), en)
    for page in (zh, en):
        assert "已送出" not in page and 'class="ok"' not in page


def test_tcr028_without_an_agent_the_environment_name_is_shown(w):
    # TC-028
    ann, rid, job, c = refused_page(w, agent="")
    assert "平台主機 lab-a" in c.get("/c/" + rid).text


def test_tcr029_the_page_shows_the_line_the_site_sent_through_the_platform(w):
    # TC-029, TC-010 (through the real answer path)
    from abf_platform import jobs
    ann = w.user("ann")
    rid, job = queue(w, ann)
    row = w.sql("SELECT agent FROM jobs WHERE id = ?", (job,))[0]
    claimed = jobs.claim(w.ip.state_db, row["agent"], w.clock, tokens_path=w.ip.tokens)
    assert claimed is not None
    line = "ssh -o ControlMaster=auto -o ControlPath=/tmp/x-y -o ServerAliveInterval=60 me@" + HOST + " true"
    jobs.take_result(w.ip.state_db, row["agent"], job, "refused", {"ok": False, "message": DOWN, "open_command": line}, w.clock)
    kept = json.loads(w.sql("SELECT result_json FROM jobs WHERE id = ?", (job,))[0][0])
    assert kept["open_command"] == line
    assert re.search(r"<pre>\s*%s\s*</pre>" % re.escape(line), logged_in(w, "ann").get("/c/" + rid).text)
    # a line for another host does not get through the platform
    rid2, job2 = queue(w, ann, run="run-two")
    jobs.claim(w.ip.state_db, row["agent"], w.clock, tokens_path=w.ip.tokens)
    jobs.take_result(w.ip.state_db, row["agent"], job2, "refused", {"ok": False, "message": DOWN, "open_command": line.replace(HOST, "evil.example.org")}, w.clock)
    assert "open_command" not in json.loads(w.sql("SELECT result_json FROM jobs WHERE id = ?", (job2,))[0][0])


def test_tcr030_down_without_a_command_gives_the_hint_only(w):
    # TC-030
    ann, rid, job, c = refused_page(w, open_command=None, message="No open connection to the site. Log in once in a WSL terminal first")
    page = c.get("/c/" + rid).text
    assert "請查看站台主機的終端機提示" in page and "<pre>" not in block_of(page) and "ssh " not in block_of(page)


@pytest.mark.parametrize("message", ["預檢未通過，沒有建立任何東西：java（Java 11 found; need 17）",
                                     "The site did not answer in time: its sessions are used up (站台工作階段用盡). Close the stuck connection: ssh -O exit -o ControlPath=/x h"])
def test_tcr031_032_other_reasons_have_one_sentence_and_no_login_line(w, message):
    # TC-031, TC-032
    ann, rid, job, c = refused_page(w, message=message, open_command=None)
    page = c.get("/c/" + rid).text
    blk = block_of(page)
    assert blk and "<pre>" not in blk and "ssh " not in page and "已送出" not in page and "Close the stuck" not in page


def test_tcr033_034_035_error_state_first_sentence_and_clean_text(w):
    # TC-033, TC-034, TC-035
    ann, rid, job, c = refused_page(w, state="error", message="First reason. " + "x" * 400, open_command=None)
    blk = block_of(c.get("/c/" + rid).text)
    assert "First reason." in blk and "xxxxxxxxxx" not in blk and "已送出" not in blk and "<pre>" not in blk
    for bad in ("Traceback (most recent call last): boom", "SELECT * FROM users", "key sk-abcdefghijklmnopqrstuvwxyz0123456789ABCD"):
        settle(w, job, state="error", message=bad, open_command=None)
        text = c.get("/c/" + rid).text
        assert "Traceback" not in text and "SELECT *" not in text and "sk-abcdef" not in text and block_of(text)


def test_tcr036_to_039_queued_claimed_done_and_no_job_keep_their_words(w):
    # TC-036, TC-037, TC-038, TC-039
    ann = w.user("ann")
    rid, job = queue(w, ann)
    c = logged_in(w, "ann")
    for state in ("queued", "claimed", "done"):
        settle(w, job, state=state, message="fine", open_command=None)
        import sqlite3
        con = sqlite3.connect(str(w.ip.state_db))
        with con:
            con.execute("UPDATE jobs SET state = ? WHERE id = ?", (state, job))
        con.close()
        page = c.get("/c/" + rid).text
        assert '<p class="ok">已送出。工作編號 %d。</p>' % job in page and "已排入佇列" not in page and 'id="refusal"' not in page
    rid2 = w.launch(caller=ann, run="run-two")["id"]
    assert "已送出" not in c.get("/c/" + rid2).text


def test_tcr040_pressing_send_answers_as_before(w):
    # TC-040
    ann = w.user("ann")
    rid = w.launch(caller=ann)["id"]
    c = logged_in(w, "ann")
    r = c.post("/c/" + rid, data={"csrf": csrf_of(c.get("/c/" + rid).text)})
    assert r.status_code == 200 and "已送出。工作編號" in r.text and 'id="refusal"' not in r.text


def test_tcr041_042_text_is_escaped_and_a_bad_stored_line_is_not_shown(w):
    # TC-041, TC-042
    ann, rid, job, c = refused_page(w, message="<script>alert(1)</script> bad.", open_command=None)
    assert "<script>alert(1)" not in c.get("/c/" + rid).text
    for bad in ("ssh -o A=b <script>alert(1)</script> " + HOST + " true", GOOD + "; rm -rf /"):
        settle(w, job, message=DOWN, open_command=bad)
        page = c.get("/c/" + rid).text
        assert "<script>alert(1)" not in page and "rm -rf" not in page and "<pre>" not in block_of(page)


def test_tcr043_the_command_sits_only_in_pre_without_forms_or_links(w):
    # TC-043, TC-067, TC-069, TC-089
    ann, rid, job, c = refused_page(w)
    blk = block_of(c.get("/c/" + rid).text)
    assert blk.count(GOOD) == 1 and re.search(r"<pre>\s*%s\s*</pre>" % re.escape(GOOD), blk)
    for forbidden in ("<form", "<button", "<input", "<a ", "href", "<script", " on", "style=", "clipboard", "copy", "iframe"):
        assert forbidden not in blk, forbidden
    assert "沒有送出" in blk


def test_tcr044_045_another_person_gets_nothing(w):
    # TC-044, TC-045
    ann, rid, job, c = refused_page(w)
    w.user("bob")
    b = logged_in(w, "bob")
    r = b.get("/c/" + rid)
    assert r.status_code == 403 and GOOD not in r.text and "No open connection" not in r.text
    pending = w.launch(caller=ann, run="run-two")["id"]
    before = w.sql("SELECT * FROM jobs")
    page = logged_in(w, "ann").get("/c/" + pending)
    assert b.post("/c/" + pending, data={"csrf": csrf_of(page.text)}).status_code in (400, 403)
    assert w.sql("SELECT * FROM jobs") == before


def test_tcr046_looking_changes_nothing(w):
    # TC-046, TC-081
    ann, rid, job, c = refused_page(w)
    tables = ["confirmations", "jobs", "launches", "compute_envs", "agents"]
    snap = lambda: [[tuple(r) for r in w.sql("SELECT * FROM " + t)] for t in tables]
    before = snap()
    for _ in range(3):
        assert c.get("/c/" + rid).status_code == 200 and c.get("/").status_code == 200
    assert snap() == before


# ---- the board -------------------------------------------------------------------------------------------------------------

def test_tcr048_049_the_board_shows_the_same_block(w):
    # TC-048, TC-049
    ann, rid, job, c = refused_page(w, agent="agent-1")
    zh, en = c.get("/").text, c.get("/?lang=en").text
    assert block_of(zh) == block_of(c.get("/c/" + rid).text)
    assert "station host agent-1" in block_of(en) and re.search(r"<pre>\s*%s\s*</pre>" % re.escape(GOOD), block_of(en))


def test_tcr050_one_block_the_latest(w):
    # TC-050
    ann = w.user("ann")
    _, first = queue(w, ann)
    settle(w, first, open_command=GOOD.replace("u@", "first@"), finished=w.clock() - 100)
    _, second = queue(w, ann, run="run-two")
    settle(w, second, open_command=GOOD.replace("u@", "second@"))
    page = logged_in(w, "ann").get("/").text
    assert page.count('id="refusal"') == 1 and "second@" in page and "first@" not in page


def test_tcr051_another_person_sees_no_block(w):
    # TC-051
    refused_page(w)
    w.user("bob")
    page = logged_in(w, "bob").get("/").text
    assert 'id="refusal"' not in page and GOOD not in page


def test_tcr052_053_older_than_an_hour_is_gone(w):
    # TC-052, TC-053
    ann, rid, job, c = refused_page(w, finished=w.clock() - 59 * 60)
    assert 'id="refusal"' in c.get("/").text
    settle(w, job, finished=w.clock() - 3601)
    assert 'id="refusal"' not in c.get("/").text


def test_tcr054_055_058_a_later_launch_hides_it_and_other_jobs_do_not(w):
    # TC-054, TC-055, TC-058
    ann = w.user("ann")
    c = logged_in(w, "ann")
    plain = c.get("/").text
    assert 'id="refusal"' not in plain
    _, job = queue(w, ann)
    settle(w, job)
    assert 'id="refusal"' in c.get("/").text
    from abf_platform import jobs
    import sqlite3
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("INSERT INTO jobs (agent, compute_env, kind, args_json, state, created_at, deadline_at) VALUES "
                    "('a', 'lab-a', 'list_site_files', '{}', 'done', ?, ?)", (w.clock() + 5, w.clock() + 500))
    con.close()
    assert 'id="refusal"' in c.get("/").text
    _, later = queue(w, ann, run="run-two")
    assert 'id="refusal"' not in c.get("/").text


def test_tcr056_057_board_other_reasons(w):
    # TC-056, TC-057
    ann, rid, job, c = refused_page(w, message="預檢未通過，沒有建立任何東西：java（Java 11 found）", open_command=None)
    blk = block_of(c.get("/").text)
    assert blk and "<pre>" not in blk and "ssh " not in blk
    settle(w, job, message="No open connection to the site. Log in", open_command=None)
    blk = block_of(c.get("/").text)
    assert "<pre>" not in blk and "請查看站台主機的終端機提示" in blk


def test_tcr059_the_new_keys_match():
    # TC-059, TC-093
    from abf_platform import web_board
    new = {k for k in web_board.STRINGS["zh"] if k.startswith("refusal_")}
    assert new and new == {k for k in web_board.STRINGS["en"] if k.startswith("refusal_")}
    assert "refusal_queued_note" not in web_board.STRINGS["zh"] and "refusal_queued_note" not in web_board.STRINGS["en"]


def test_tcr061_refusal_of_answers_only_for_refused_and_error(w):
    # TC-061
    from abf_platform import jobs
    ann = w.user("ann")
    _, job = queue(w, ann)
    for state in ("queued", "claimed", "done"):
        import sqlite3
        con = sqlite3.connect(str(w.ip.state_db))
        with con:
            con.execute("UPDATE jobs SET state = ? WHERE id = ?", (state, job))
        con.close()
        assert jobs.refusal_of(w.ip.state_db, job) is None
    settle(w, job)
    got = jobs.refusal_of(w.ip.state_db, job)
    assert got["state"] == "refused" and got["open_command"] == GOOD and got["host"] and got["reason"].startswith("No open connection")
    settle(w, job, state="error", message="boom.", open_command=None)
    got = jobs.refusal_of(w.ip.state_db, job)
    assert got["state"] == "error" and got["open_command"] is None
    assert jobs.refusal_of(w.ip.state_db, 99999) is None


# ---- the pages' limits -----------------------------------------------------------------------------------------------------

def test_tcr066_074_088_095_the_pages_stay_plain(w):
    # TC-066, TC-074, TC-088, TC-095
    ann, rid, job, c = refused_page(w)
    for url in ("/c/" + rid, "/"):
        r = c.get(url)
        text = r.text
        assert "content-security-policy" in {k.lower() for k in r.headers}
        blk = block_of(text)
        assert "style=" not in blk and "http://" not in blk and "https://" not in blk
        assert 'type="password"' not in text and "幫我連線" not in text and "connect for me" not in text.lower()
        assert not re.search(r'<input[^>]*name="[^"]*(password|otp|code)', text, re.I)
        assert "abf-connect://" not in text and "<iframe" not in text and "setInterval" not in blk and 'http-equiv="refresh"' not in blk


def test_tcr073_no_route_connects_for_the_user(w):
    # TC-073
    paths = [getattr(r, "path", "") for r in w.web().app.routes]
    assert paths and not [p for p in paths if re.search(r"connect|ssh|login-site", p)]


def test_tcr072_no_tool_takes_a_secret(w):
    # TC-072
    tools, _ = w.mcp([])
    names = [p for t in tools for p in (t.input_schema or {}).get("properties", {})]
    assert names and not [n for n in names if re.search(r"password|passwd|otp|one.?time|verification|secret", n, re.I)]
    assert "get_request_status" not in [t.name for t in tools]


def test_tcr075_087_a_password_and_code_in_a_post_go_nowhere(w):
    # TC-075, TC-087
    ann, rid, job, c = refused_page(w)
    r = c.post("/c/" + rid, data={"csrf": "x", "password": "x", "otp": "123456"})
    assert "123456" not in r.text
    for table in ("confirmations", "jobs", "launches"):
        assert "123456" not in json.dumps([list(map(str, row)) for row in w.sql("SELECT * FROM " + table)])
    assert "123456" not in json.dumps([list(map(str, row)) for row in w.sql("SELECT * FROM sqlite_master")])


def test_tcr092_launch_answer_has_no_last_refusal(w):
    # TC-092
    ann, rid, job, c = refused_page(w)
    out = w.launch(caller=ann, run="run-three")
    assert "last_refusal" not in out and "state" not in out or out.get("state") != "refused"
