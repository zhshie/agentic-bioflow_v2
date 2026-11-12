# Nothing existing: tests of the red "site connection is down" bar, the refusal of a new launch while it is down, and the paste-this
# connection line (mcp-site-keepalive-disconnect-ux); the rules are this task's. TC numbers are in the comments.
"""mcp-site-keepalive-disconnect-ux, platform side."""
import json
import os
import re
import sqlite3
import subprocess
import time
from pathlib import Path

import pytest

from helpers import tool_json
from human_harness import World, csrf_of, form_answer
from test_web_board import login, seed

ROOT = Path(__file__).resolve().parents[2]
ZH = ("站台連線已掉：請在執行 agent「%s」那台機器的 WSL 終端機重新登入（貼上開連線指令並輸入 OTP）。"
      "已在跑的分析不受影響；新的分析在恢復前無法送出。")       # lead ruling 2026-11-11: 分析, never the Latin word
EN = ('The site connection is down. On the machine running agent "%s", log in again in its WSL terminal (paste the connect line, '
      'type the one-time code). Runs already going are not affected; new runs cannot be sent until it is back.')
AGENT = "agent-t"


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def set_link(w, agent, link, age=0):
    """What the agent said last: site_link in its facts, as of `age` seconds ago (last_seen_at moves with it)."""
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        facts = json.loads(con.execute("SELECT facts_json FROM agents WHERE name = ?", (agent,)).fetchone()[0] or "{}")
        facts.pop("site_link", None)
        facts.pop("site_link_at", None)
        if link is not None:
            facts["site_link"], facts["site_link_at"] = link, "2026-11-11T10:00:00Z"
        con.execute("UPDATE agents SET facts_json = ?, last_seen_at = ? WHERE name = ?", (json.dumps(facts), time.time() - age, agent))
    con.close()


def add_agent(w, name, owner, link="closed"):
    from abf_platform import agents
    agents.register(w.ip.state_db, name, "0.1.0", time.time, facts={"reach": "ssh"}, owner_user_id=owner.user_id)
    set_link(w, name, link)


def closed(w, user):
    from abf_platform import site_link
    return site_link.closed_agents(w.ip.state_db, None if user is None else user.user_id, time.time())


def page(w, name, path="/", lang="zh"):
    c = login(w, name)
    r = c.get(path + ("&" if "?" in path else "?") + "lang=" + lang)
    assert r.status_code == 200, r.text[:300]
    return r.text


def approve(w, ann, rid):
    from abf_platform import confirm
    return confirm.approve(w.ip.state_db, rid, "PAGE", ann.user_id)


def refused(w, ann, **over):
    from abf_platform import confirm
    rid = w.launch(caller=ann, **over)["id"]
    with pytest.raises(confirm.NotApproved) as e:
        approve(w, ann, rid)
    return rid, e.value


# ---- US1: the list ---------------------------------------------------------------------------------------------------

def test_closed_agents_lists_fresh_closed_only(w):
    # TC-001, TC-002, TC-003, TC-004, TC-005
    ann = w.user("ann")
    add_agent(w, "desktop-gcb", ann, "closed")
    add_agent(w, "desktop", ann, "closed")
    add_agent(w, "op", ann, "open")
    add_agent(w, "unk", ann, "unknown")
    add_agent(w, "stale", ann, "closed")
    set_link(w, "stale", "closed", age=100000)
    add_agent(w, "old", ann, None)
    set_link(w, AGENT, "open")
    assert closed(w, ann) == ["desktop", "desktop-gcb"]


def test_closed_agents_only_own_and_terminal_sees_all(w):
    # TC-006, TC-007
    ann, bob = w.user("ann"), w.user("bob")
    add_agent(w, "bobs", bob, "closed")
    set_link(w, AGENT, "open")
    assert closed(w, ann) == [] and closed(w, bob) == ["bobs"]
    set_link(w, AGENT, "closed")
    assert closed(w, None) == [AGENT, "bobs"]


def test_listing_is_read_only(w):
    # TC-008
    ann = w.user("ann")
    set_link(w, AGENT, "closed")

    def snap():
        return (w.sql("SELECT count(*) FROM jobs")[0][0], [tuple(r) for r in w.sql("SELECT name, last_seen_at, facts_json FROM agents")])
    before = snap()
    for _ in range(3):
        assert closed(w, ann) == [AGENT]
    assert before == snap()


# ---- US1: the bar ------------------------------------------------------------------------------------------------------

def test_bar_text_zh_and_en(w):
    # TC-009, TC-010, TC-023
    w.user("ann")
    set_link(w, AGENT, "closed")
    zh = page(w, "ann", "/", "zh")
    assert '<div class="linkbar" role="alert"><span aria-hidden="true">✗</span><span>' + ZH % AGENT + "</span></div>" in zh
    assert "WSL" in zh
    bar = re.search(r'<div class="linkbar".*?</div>', zh, re.S).group(0)
    assert "!" not in bar and "！" not in bar
    en = page(w, "ann", "/", "en")
    assert 'class="linkbar"' in en and 'role="alert"' in en
    assert (EN % AGENT).replace('"', "&quot;") in en or (EN % AGENT) in en


@pytest.mark.parametrize("path", ["/", "/launch", "/settings", "/usage", "/upload"])
@pytest.mark.parametrize("lang", ["zh", "en"])
def test_bar_on_every_page(w, path, lang):
    # TC-011, TC-012
    w.user("ann")
    set_link(w, AGENT, "closed")
    c = login(w, "ann")
    r = c.get(path + "?lang=" + lang)
    if r.status_code != 200:
        pytest.skip("no such page: %s" % path)
    assert 'class="linkbar"' in r.text and AGENT in r.text and "WSL" in r.text


def test_bar_on_downstream_page(w):
    # TC-012
    ann = w.user("ann")
    rid = seed(w, "r1", "succeeded", ann)
    set_link(w, AGENT, "closed")
    html = page(w, "ann", "/?run=%s&stage=downstream" % rid, "zh")
    assert 'class="linkbar"' in html


def test_one_bar_per_closed_agent(w):
    # TC-013
    ann = w.user("ann")
    add_agent(w, "desktop", ann)
    set_link(w, AGENT, "closed")
    html = page(w, "ann", "/")
    assert html.count('<div class="linkbar" role="alert">') == 2
    assert "「desktop」" in html and "「%s」" % AGENT in html


@pytest.mark.parametrize("link,age", [("open", 0), ("unknown", 0), ("closed", 100000), (None, 0)])
def test_no_bar_when_not_fresh_closed(w, link, age):
    # TC-014, TC-015, TC-016: no bar, and the page is the same bytes as with the link open
    w.user("ann")
    set_link(w, AGENT, "open")
    def plain(t):
        return re.sub(r'value="[0-9a-f]{64}"', "", t)      # the csrf token differs per login
    base = plain(page(w, "ann", "/"))
    set_link(w, AGENT, link, age=age)
    html = plain(page(w, "ann", "/"))
    assert 'class="linkbar"' not in html and html == base


def test_bar_goes_when_open_again(w):
    # TC-017
    w.user("ann")
    set_link(w, AGENT, "closed")
    assert 'class="linkbar"' in page(w, "ann", "/")
    set_link(w, AGENT, "open")
    assert 'class="linkbar"' not in page(w, "ann", "/")


def test_bar_not_shown_to_other_user_or_logged_out(w):
    # TC-018, TC-019
    w.user("ann"), w.user("bob")
    set_link(w, AGENT, "closed")
    bob = page(w, "bob", "/")
    assert 'class="linkbar"' not in bob and AGENT not in bob
    assert 'class="linkbar"' not in w.web().get("/login").text


def test_bar_escapes_agent_name(w):
    # TC-020
    from abf_platform import site_link
    html = site_link.bar_html(['x"><script>alert(1)</script>'], "zh")
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_bar_has_no_command_template(w):
    # TC-021
    w.user("ann")
    set_link(w, AGENT, "closed")
    assert "ControlPersist" not in page(w, "ann", "/")


def test_bar_sits_before_main_area(w):
    # TC-022
    w.user("ann")
    set_link(w, AGENT, "closed")
    html = page(w, "ann", "/")
    assert html.index('class="linkbar"') < html.index('class="wb"')
    if 'class="devbar"' in html:
        assert html.index('class="devbar"') < html.index('class="linkbar"')


def test_strings_and_style_rules():
    # TC-024, TC-025, TC-026, TC-027
    from abf_platform import web_board
    assert web_board.STRINGS["zh"]["linkbar_down"] == ZH and web_board.STRINGS["en"]["linkbar_down"] == EN
    rule = re.search(r"\.linkbar\{([^}]*)\}", web_board.STYLE).group(1)
    assert "var(--failed-bg)" in rule and "var(--failed)" in rule and "--lost" not in rule
    assert not re.search(r"#[0-9a-fA-F]{3,8}|rgb\(", rule) and "border-left" not in rule and "position" not in rule
    assert "display:flex" in rule and "gap:8px" in rule and "padding:8px 16px" in rule and "font-weight:600" in rule


# ---- US2: the refusal ---------------------------------------------------------------------------------------------------

def test_launch_refused_names_agent_and_wsl(w):
    # TC-033, TC-034, TC-040, TC-046
    from abf_platform import jobs
    ann = w.user("ann")
    set_link(w, AGENT, "closed")
    rid, e = refused(w, ann)
    m = str(e)
    assert e.status == "failed" and m.startswith(jobs.SITE_DOWN) and AGENT in m and "WSL" in m and len(m) <= 300
    assert "連線已掉，請在執行 agent「%s」那台機器的 WSL 終端機重新登入，再重新送出" % AGENT in m
    assert "已在跑的分析不受影響" in m and "runs already going are not affected" in m and "的 run" not in m
    assert w.sql("SELECT state FROM confirmations WHERE id = ?", (rid,))[0][0] == "void"
    assert w.jobs("launch_nextflow") == []
    assert not re.search(r"Traceback|SELECT|/home/|token", m)


def test_longest_agent_name_still_fits():
    # TC-046
    from abf_platform import site_link
    assert len(site_link.down_message("a" * 64)) <= 300


def test_message_survives_first_sentence():
    # TC-035, TC-045
    from abf_platform import jobs, site_link
    msg = site_link.down_message("desktop")
    assert jobs.SITE_DOWN == "No open connection to the site" and msg.startswith(jobs.SITE_DOWN)
    first = jobs._first_sentence(msg)
    assert "desktop" in first and "WSL" in first


def test_mcp_launch_with_yes_shows_whole_sentence(w):
    # TC-036
    ann = w.user("ann")
    set_link(w, AGENT, "closed")
    out = w.launch(caller=ann, answer=form_answer())
    assert out["sent"] is False
    text = json.dumps(out, ensure_ascii=False)
    assert AGENT in text and "WSL" in text, out


def test_web_confirm_page_shows_whole_sentence(w):
    # TC-037
    ann = w.user("ann")
    set_link(w, AGENT, "closed")
    rid = w.launch(caller=ann)["id"]
    c = login(w, "ann")
    r = c.post("/c/" + rid, data={"csrf": csrf_of(c.get("/c/" + rid).text)})
    assert AGENT in r.text and "WSL" in r.text
    assert w.jobs("launch_nextflow") == []


@pytest.mark.parametrize("link", ["open", "unknown", None])
def test_open_and_unknown_do_not_block(w, link):
    # TC-041, TC-042
    ann = w.user("ann")
    set_link(w, AGENT, link)
    rid = w.launch(caller=ann)["id"]
    assert approve(w, ann, rid)[1]


def test_only_the_target_agent_blocks(w):
    # TC-043, TC-044
    ann = w.user("ann")
    add_agent(w, "other-agent", ann, "closed")
    set_link(w, AGENT, "open")
    rid = w.launch(caller=ann)["id"]
    assert approve(w, ann, rid)[1]


def test_other_user_cannot_approve_and_name_is_not_leaked(w):
    # TC-098
    from abf_platform import confirm
    ann, bob = w.user("ann"), w.user("bob")
    set_link(w, AGENT, "closed")
    rid = w.launch(caller=ann)["id"]
    with pytest.raises(confirm.NotApproved) as e:
        approve(w, bob, rid)
    assert e.value.status == "not_yours" and AGENT not in str(e.value)
    assert w.sql("SELECT state FROM confirmations WHERE id = ?", (rid,))[0][0] == "pending"


def test_form_is_made_while_closed(w):
    # TC-084: the question is asked; the refusal only comes at yes
    ann = w.user("ann")
    set_link(w, AGENT, "closed")
    assert w.launch(caller=ann).get("id")


def test_refusal_is_immediate_without_ssh(w, monkeypatch):
    # TC-087
    ann = w.user("ann")
    set_link(w, AGENT, "closed")
    rid = w.launch(caller=ann)["id"]
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: calls.append(a))
    from abf_platform import confirm
    t = time.time()
    with pytest.raises(confirm.NotApproved):
        approve(w, ann, rid)
    assert calls == [] and time.time() - t < 5


# ---- US2, every way in: one gate in jobs.enqueue_confirmed (TC-038, TC-039) ---------------------------------------------------

def _state_counts(w):
    return (len(w.sql("SELECT * FROM jobs WHERE kind = 'launch_nextflow'")),
            len(w.sql("SELECT * FROM confirmations WHERE state = 'void'")), len(w.sql("SELECT * FROM confirmations WHERE state = 'pending'")))


def _closed_and_nothing_sent(w, out, before):
    """The refusal names the agent and the next step; the one new confirmation is void (not pending, not approved); nothing new was queued."""
    text = json.dumps(out, ensure_ascii=False)
    assert out["sent"] is False and "job_id" not in out, out
    assert AGENT in text and "WSL" in text and "重新登入" in text, text
    assert _state_counts(w) == (before[0], before[1] + 1, before[2]), (before, _state_counts(w))


def test_launch_pipeline_refused_when_closed(w):
    # TC-039 (launch_pipeline)
    from test_mcp_launch_pipeline import lp, make
    from owner_harness import Duo
    d = Duo(w)
    set_link(w, AGENT, "closed")
    pid = make(d)
    before = _state_counts(w)
    out = tool_json(lp(d, d.a, pid, answer=form_answer()))
    _closed_and_nothing_sent(w, out, before)


def _failed_first_run(tmp_path, monkeypatch, link):
    """A first launch that failed (so resume and relaunch have something to ask about), then the agent's link set."""
    from resume_harness import Rig
    rig = Rig(tmp_path, monkeypatch)
    rig.first("x")
    set_link(rig.w, AGENT, link)
    return rig


@pytest.mark.parametrize("name", ["resume", "relaunch"])
def test_resume_and_relaunch_refused_when_closed(tmp_path, monkeypatch, name):
    # TC-039 (resume, relaunch)
    rig = _failed_first_run(tmp_path, monkeypatch, "closed")
    w = rig.w
    before = _state_counts(w)
    out = tool_json(w.call(name, {"run_name": "x"}, answer=form_answer()))
    _closed_and_nothing_sent(w, out, before)


@pytest.mark.parametrize("name", ["resume", "relaunch"])
def test_resume_and_relaunch_go_through_when_open(tmp_path, monkeypatch, name):
    # TC-039 control: the same call with the link open is queued, so the refusal above is the gate and nothing else
    rig = _failed_first_run(tmp_path, monkeypatch, "open")
    out = tool_json(rig.w.call(name, {"run_name": "x"}, answer=form_answer()))
    assert out["sent"] is True and out["job_id"], out


def test_terminal_launch_refused_when_closed(tmp_path, monkeypatch):
    # TC-038: abf-platform launch, the person types y
    from launch_harness import LaunchData
    from station_harness import Inproc
    from test_launch_cli import ask
    data = LaunchData(Inproc(tmp_path / "ip", monkeypatch), facts={"site_link": "closed", "site_link_at": "2026-11-11T10:00:00Z"})
    rc, screen = ask(data, tmp_path, "y\n")
    assert rc != 0 and data.agent in screen and "WSL" in screen and "重新登入" in screen, screen
    assert (data.count("jobs"), data.count("launches")) == (0, 0)
    assert data.run_tokens() == 0


# ---- US3 --------------------------------------------------------------------------------------------------------------

def test_running_run_and_cancel_unaffected_when_closed(w):
    # TC-047, TC-049
    ann = w.user("ann")
    w.hand_over(by=ann)
    set_link(w, AGENT, "closed")
    out = tool_json(w.call("cancel", {"run_name": "run-one"}, caller=ann, answer=form_answer()))
    assert out.get("sent") is True, out
    assert w.sql("SELECT slurm_job_id FROM launches WHERE run_name = 'run-one'")[0][0] == 4242


def test_launch_goes_through_after_reopen(w):
    # TC-052
    ann = w.user("ann")
    set_link(w, AGENT, "closed")
    refused(w, ann)
    set_link(w, AGENT, "open")
    rid = w.launch(caller=ann)["id"]
    assert approve(w, ann, rid)[1]


# ---- US4: the line -----------------------------------------------------------------------------------------------------

def _printed_line(tmp_path):
    env = tmp_path / "env.yaml"
    env.write_text("reach: ssh\nsite_host: me@example.org\nssh_control_path: %s/cm\n" % tmp_path)
    fake = tmp_path / "fake-ssh"
    fake.write_text("#!/bin/bash\nexit 255\n")
    fake.chmod(0o755)
    e = dict(os.environ, LAB_SETTINGS_FILE=str(env), ON_SITE_SSH_BIN=str(fake))
    p = subprocess.run(["bash", str(ROOT / "scripts" / "on_site.sh"), "true"], capture_output=True, text=True, env=e)
    return [ln.strip() for ln in (p.stdout + p.stderr).splitlines() if "ControlMaster=auto" in ln]


def test_open_command_from_on_site_is_valid_and_keepalive(tmp_path):
    # TC-053, TC-054
    from abf_platform import jobs
    lines = _printed_line(tmp_path)
    assert lines
    line = lines[0]
    assert "ControlPersist=yes" in line and "ServerAliveInterval=60" in line and "ServerAliveCountMax=10" in line and "8h" not in line
    assert jobs.valid_open_command(line, "example.org") is not None


def test_scripts_do_not_promise_survival():
    # TC-056, TC-060
    for name in ("on_site.sh", "reset_master.sh"):
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "ControlPersist=8h" not in text and "keepalive_log.sh" in text
        assert not re.search(r"never drops|guarantee|永不|不會掉|保證", text, re.I)


def test_docs_follow_the_new_line():
    # TC-073, TC-074, TC-075
    plat = (ROOT / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    assert "bash scripts/keepalive_log.sh" in plat and "ControlPersist=yes" in plat
    assert "ControlPersist=8h keeps the connection for the day" not in plat and "at most 8 hours" not in plat
    # lead ruling 2026-11-11: one call, one check; a person or an existing schedule calls it, nothing stays resident
    assert not [ln for ln in plat.splitlines() if "keepalive_log" in ln and re.search(r"nohup|daemon|in the background|常駐", ln)]
    assert "8h" not in (ROOT / "docs" / "SITE_ADAPTER.md").read_text(encoding="utf-8")
    pit = (ROOT / "docs" / "PITFALLS.md").read_text(encoding="utf-8")
    entry = pit[pit.index("**61."):]
    for key in ("Symptom:", "Root cause:", "Check:", "Touches:", "keepalive_log.sh", "event=closed lasted_min"):
        assert key in entry
    assert "nohup" not in entry
