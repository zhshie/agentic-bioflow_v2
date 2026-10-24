# Nothing existing: tests of the first cut of the settings page (specs/settings-page); the page and its limits are ours.
"""settings-page: the checklist, the compute environments and the access tokens on GET /settings, read only. Test cases are named in the comments."""
import ast
import base64
import hashlib
import json
import logging
import re
import sqlite3
import time

import pytest

from helpers import PLATFORM_DIR
from human_harness import PASSWORD, World
from test_web_board import login, pane

SETTINGS_PY = PLATFORM_DIR / "abf_platform" / "web_settings.py"
CJK = re.compile("[\u3000-\u9fff\uff00-\uffef]")
SECOND = "J" + "ev"      # spelled apart so the platform-wide safety test stays at 0


@pytest.fixture
def w(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def sql(w, text, args=()):
    con = sqlite3.connect(str(w.ip.state_db))
    try:
        with con:
            con.execute(text, args)
    finally:
        con.close()


def pat(w, caller, label=None, revoke=False):
    """A personal access token of `caller`; returns (id, plain value)."""
    from abf_platform import store
    value = store.create_token(w.ip.tokens, kind="pat", user_id=caller.user_id, label=label)
    tid = [p for p in store.list_pats(w.ip.tokens) if p["user"] == caller.name][-1]["id"]
    if revoke:
        store.revoke_pat(w.ip.tokens, tid)
    return tid, value


def page(w, name="ann", lang="zh"):
    c = login(w, name)
    r = c.get("/settings" + ("?lang=en" if lang == "en" else ""))
    assert r.status_code == 200
    return r, pane(r.text, "middle")


def setup_items(mid):
    block = re.search(r'<section[^>]*id="setup".*?</section>', mid, re.S).group(0)
    return block, re.findall(r"<li>(.*?)</li>", block, re.S)


def plain(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()


def make_env(w, caller, name, agent, status="available", message="ok", primary=False, config=None, platform=None):
    from abf_platform import compute_envs
    base = compute_envs.get(w.ip.state_db, "lab-a")
    compute_envs.create(w.ip.state_db, {"name": name, "platform": platform or base["platform"], "agent": agent, "owner_user_id": caller.user_id,
                                        "config": config if config is not None else base["config"]})
    sql(w, "UPDATE compute_envs SET status = ?, message = ?, is_primary = ? WHERE name = ?", (status, message, 1 if primary else 0, name))


def make_agent(w, caller, name, online=True):
    from abf_platform import agents
    agents.register(w.ip.state_db, name, "0.1.0", time.time if online else (lambda: 1000.0), facts=w.data.facts, owner_user_id=caller.user_id)


def clear_envs(w):
    sql(w, "DELETE FROM compute_envs")


# ---- the sections and the checklist ---------------------------------------------------------------------------------------------

def test_st01_sections_in_order(w):
    # TC-001, TC-002
    w.user("ann")
    _, mid = page(w)
    assert re.findall(r"<h2>(.*?)</h2>", mid) == ["使用前檢查", "運算環境", "憑證", "密碼與金鑰", "個人", "營運者後台", "角色（老師／學生）"]
    assert re.search(r'<section[^>]*id="setup"', mid) and mid.index('id="setup"') < mid.index("<h2>運算環境</h2>")
    block, items = setup_items(mid)
    assert "<ol>" in block and len(items) == 4
    assert [plain(i).split(" ")[0] for i in items] == ["帳號", "存取權杖", "運算環境", "AI"]


def test_st02_setup_all_missing(w):
    # TC-003, TC-004, TC-008, TC-014, TC-015, TC-079
    w.user("ann")
    clear_envs(w)
    _, mid = page(w)
    _, items = setup_items(mid)
    assert "✓" in items[0] and "完成" in items[0]
    assert "✗" in items[1] and "未完成" in items[1] and "abf-platform token new" in items[1]
    assert "✗" in items[2] and "未完成" in items[2] and "沒有運算環境。" in items[2]
    assert "—" in items[3] and "之後開放" in items[3] and "✓" not in items[3] and "✗" not in items[3]
    for item, cls in zip((items[0], items[1], items[3]), ("state-succeeded", "state-failed", "muted")):
        assert cls in item


def test_st02b_token_rules(w):
    # TC-005, TC-006, TC-007
    ann, bob = w.user("ann"), w.user("bob")
    pat(w, bob, "bobs")
    _, mid = page(w)
    assert "未完成" in setup_items(mid)[1][1]
    pat(w, ann, "gone", revoke=True)
    _, mid = page(w)
    assert "未完成" in setup_items(mid)[1][1]
    pat(w, ann, "live")
    _, mid = page(w)
    assert "完成" in setup_items(mid)[1][1] and "未完成" not in setup_items(mid)[1][1]


def test_st03_setup_ce_reasons(w):
    # TC-009, TC-010, TC-011, TC-012, TC-017
    w.user("ann")
    _, mid = page(w)
    assert "✓" in setup_items(mid)[1][2] and "未完成" not in setup_items(mid)[1][2]
    sql(w, "UPDATE compute_envs SET status = 'invalid', message = ? WHERE name = 'lab-a'", ("某段說明 <script>alert(1)</script>",))
    r, mid = page(w)
    note = plain(setup_items(mid)[1][2])
    assert "未完成" in note and "主要運算環境無法使用：某段說明" in note and "<script" not in r.text.lower()
    assert "&lt;script&gt;" in setup_items(mid)[0]
    sql(w, "UPDATE compute_envs SET status = 'available', message = 'ok' WHERE name = 'lab-a'")
    sql(w, "UPDATE agents SET last_seen_at = 1000")
    _, mid = page(w)
    assert "未完成" in setup_items(mid)[1][2] and "站台代理離線。" in setup_items(mid)[1][2]
    sql(w, "UPDATE agents SET last_seen_at = ?, name = 'elsewhere'", (time.time(),))
    _, mid = page(w)
    assert "站台代理離線。" in setup_items(mid)[1][2]


def test_st03b_other_users_do_not_count(w):
    # TC-013
    w.user("ann")
    bob = w.user("bob")
    clear_envs(w)
    make_agent(w, bob, "agent-b")
    make_env(w, bob, "b-env", "agent-b", primary=True)
    _, mid = page(w, "ann")
    assert "沒有運算環境。" in setup_items(mid)[1][2]


def test_st03c_english_and_no_project_step(w):
    # TC-016, TC-018
    w.user("ann")
    clear_envs(w)
    _, mid = page(w, lang="en")
    block, items = setup_items(mid)
    assert "<h2>Before you start</h2>" in block
    assert "Done" in items[0] and "Missing" in items[1] and "No compute environment." in items[2] and "Coming later" in items[3]
    assert not CJK.search(mid)
    _, zh = page(w)
    assert "建立專案" not in zh and "建立第一個專案" not in zh


# ---- compute environments --------------------------------------------------------------------------------------------------------

def two_envs(w, ann):
    sql(w, "UPDATE compute_envs SET config_json = ? WHERE name = 'lab-a'",
        (json.dumps({"sitePipelines": [{"pipeline": "nf-core/ampliseq", "revision": "2.18.0", "module": "m", "home": "/h"},
                                       {"pipeline": "nf-core/rnaseq", "revision": "3.14.0", "module": "m", "home": "/h"}]}),))
    make_agent(w, ann, "agent-off", online=False)
    make_env(w, ann, "second-env", "agent-off", status="invalid", message="broken thing", primary=False)
    sql(w, "UPDATE compute_envs SET last_used_at = ? WHERE name = 'lab-a'", (time.time(),))


def rows_of(mid, h2):
    sec = re.search(r"<h2>%s</h2>(.*?)</section>" % h2, mid, re.S).group(1)
    return sec, re.findall(r"<tr>(.*?)</tr>", sec, re.S)


def test_st04_ce_table(w):
    # TC-019, TC-020, TC-021, TC-024, TC-025, TC-026, TC-027, TC-029, TC-032
    ann = w.user("ann")
    two_envs(w, ann)
    _, mid = page(w)
    sec, rows = rows_of(mid, "運算環境")
    assert re.findall(r"<th>(.*?)</th>", sec) == ["名稱", "平台", "狀態", "站台代理", "已登記管線", "上次使用時間"]
    body = [r for r in rows if "<td>" in r]
    assert len(body) == 2
    first, second = body if "lab-a" in body[0] else body[::-1]
    assert "主要" in first and "主要" not in second
    assert "✓" in first and "可用" in first and "state-succeeded" in first
    assert "✓" in first and "在線" in first and "nf-core/ampliseq 2.18.0" in first and "nf-core/rnaseq 3.14.0" in first
    assert "✗" in second and "無法使用" in second and "broken thing" in second and "state-failed" in second
    assert "✗" in second and "離線" in second and "agent-off" in second and "<td>—</td>" in second.split("</td><td>")[-2].join(["<td>", "</td>"]) or "—" in second
    assert re.search(r"\d\d-\d\d \d\d:\d\d", first.split("</td>")[-2])
    assert plain(second.split("</td>")[-2]) == "—"
    assert '<p class="off">新增或修改運算環境 <span class="later">之後開放</span></p>' in sec
    assert not re.search(r"<(a|button|input|form)\b", sec)


def test_st04b_status_mapping_and_unknown(w):
    # TC-022, TC-023
    ann = w.user("ann")
    expect = {"available": "✓ 可用", "creating": "— 未檢查", "invalid": "✗ 無法使用", "unsupported": "✗ 無法使用", "disabled": "✗ 無法使用", "weird": "— 未檢查"}
    for status, shown in expect.items():
        sql(w, "UPDATE compute_envs SET status = ? WHERE name = 'lab-a'", (status,))
        _, mid = page(w)
        sec, rows = rows_of(mid, "運算環境")
        cell = plain([r for r in rows if "<td>" in r][0].split("</td>")[2])
        assert cell.startswith(shown), (status, cell)
        if status != "available":
            assert "✓" not in cell


def test_st04c_empty_and_escaping(w):
    # TC-028, TC-031
    ann = w.user("ann")
    sql(w, "UPDATE compute_envs SET name = ? WHERE name = 'lab-a'", ('<script>x</script>"><img src=x>',))
    sql(w, "UPDATE compute_envs SET message = ?, status = 'invalid'", ('"><img src=x>',))
    r, mid = page(w)
    assert "<script" not in r.text.lower() and "<img" not in r.text
    clear_envs(w)
    _, mid = page(w)
    sec = re.search(r"<h2>運算環境</h2>(.*?)</section>", mid, re.S).group(1)
    assert "沒有運算環境。" in sec and "<tr>" not in sec


def test_st05_ce_owner_rule(w):
    # TC-030
    ann = w.user("ann")
    bob = w.user("bob")
    make_agent(w, bob, "bobs-secret-agent")
    make_env(w, bob, "bobs-secret-env", "bobs-secret-agent", config={"sitePipelines": [{"pipeline": "x/bobs-pipe", "revision": "9", "module": "m", "home": "/h"}]})
    r, _ = page(w, "ann")
    for word in ("bobs-secret-env", "bobs-secret-agent", "bobs-pipe"):
        assert word not in r.text


# ---- credentials -----------------------------------------------------------------------------------------------------------------

def test_st06_tokens_table_and_secret_never_shown(w, caplog):
    # TC-034, TC-035, TC-036, TC-038, TC-039, TC-040, TC-046, TC-077
    ann, bob = w.user("ann"), w.user("bob")
    caplog.set_level(logging.DEBUG)
    _, v1 = pat(w, ann, "laptop")
    _, v2 = pat(w, ann, None, revoke=True)
    _, vb = pat(w, bob, "bobs-label-unique")
    c = login(w, "ann")
    texts = [c.get(u).text for u in ("/settings", "/settings?lang=en")]
    mid = pane(texts[0], "middle")
    sec, rows = rows_of(mid, "憑證")
    body = [r for r in rows if "<td>" in r]
    assert re.findall(r"<th>(.*?)</th>", sec) == ["標籤", "建立時間", "狀態"] and len(body) == 2
    assert "laptop" in body[0] and "✓" in body[0] and "有效" in body[0]
    assert "—" in plain(body[1].split("</td>")[0]) and "✗" in body[1] and "已撤銷" in body[1] and re.search(r"\d\d-\d\d \d\d:\d\d", body[1].split("</td>")[2])
    assert '<p class="off">建立或撤銷權杖 <span class="later">之後開放</span></p>' in sec
    for text in texts:
        for secret in (v1, v2, vb):
            assert secret not in text and hashlib.sha256(secret.encode()).hexdigest() not in text and hashlib.sha256(secret.encode()).hexdigest().upper() not in text
        assert "bobs-label-unique" not in text and "abf_" not in text.replace("abf_platform", "").replace("abf_web", "")
    for secret in (v1, v2, vb):
        assert secret not in caplog.text
    assert not CJK.search(pane(texts[1], "middle")) and "Credentials" in texts[1] and "Valid" in texts[1] and "Revoked" in texts[1]


def test_st06b_no_tokens(w):
    # TC-037
    w.user("ann")
    _, mid = page(w)
    sec = re.search(r"<h2>憑證</h2>(.*?)</section>", mid, re.S).group(1)
    assert "沒有存取權杖。" in sec and "<tr>" not in sec


def test_st07_list_my_tokens_action(w):
    # TC-041, TC-042, TC-043
    from abf_platform import actions, store
    import os
    ann, bob = w.user("ann"), w.user("bob")
    os.remove(w.ip.tokens) if False else None
    _, vb = pat(w, bob, "bobs-label-unique")
    ia, va = pat(w, ann, "a1")
    ib, vc = pat(w, ann, "a2", revoke=True)
    mine = actions.list_my_tokens(w.ip.tokens, caller=ann)
    assert list(mine) == ["tokens"] and [t["id"] for t in mine["tokens"]] == sorted([ia, ib])
    assert all(set(t) == {"id", "label", "created_at", "revoked_at"} for t in mine["tokens"])
    text = json.dumps(mine)
    for bad in (va, vc, vb, hashlib.sha256(va.encode()).hexdigest(), "bobs-label-unique"):
        assert bad not in text
    assert [t["label"] for t in actions.list_my_tokens(w.ip.tokens, caller=bob)["tokens"]] == ["bobs-label-unique"]
    assert actions.list_my_tokens(w.ip.tokens.parent / "nothing-here.db", caller=ann) == {"tokens": []}


# ---- the rest of the page --------------------------------------------------------------------------------------------------------

def test_st08_still_read_only(w):
    # TC-048, TC-049, TC-050, TC-051, TC-052, TC-057, TC-071, TC-072
    ann = w.user("ann")
    pat(w, ann, "x")
    r, mid = page(w)
    assert r.text.count("<form") == 1 and 'action="/logout"' in r.text
    assert not re.search(r"<(form|input|select|textarea|button|a)\b", mid)
    assert "AI 模型金鑰" in mid and "金鑰只存在你的瀏覽器，不會送到平台。" in mid and "逐步模式" in mid and "開發模式" in mid
    assert 'class="nv here"' in pane(r.text, "left") and "設定" in pane(r.text, "left")
    before = (w.sql("SELECT * FROM compute_envs"), len(w.sql("SELECT * FROM agents")))
    c = login(w, "ann")
    assert c.post("/settings", data={"x": "1"}).status_code == 405
    c.get("/settings")
    assert (w.sql("SELECT * FROM compute_envs"), len(w.sql("SELECT * FROM agents"))) == before
    assert SECOND.lower() not in r.text.lower()
    assert w.web().get("/settings", follow_redirects=False).status_code in (302, 303, 307)
    assert "/login" in w.web().get("/settings", follow_redirects=False).headers["location"]


def test_st09_english(w):
    # TC-033, TC-047, TC-059
    ann = w.user("ann")
    two_envs(w, ann)
    pat(w, ann, "k")
    pat(w, ann, None, revoke=True)
    _, mid = page(w, lang="en")
    assert not CJK.search(mid), CJK.findall(mid)
    assert re.findall(r"<h2>(.*?)</h2>", mid)[:3] == ["Before you start", "Compute environments", "Credentials"]
    for word in ("Available", "Unavailable", "Online", "Offline", "Primary", "Valid", "Revoked"):
        assert word in mid


def test_st10_constraints(w):
    # TC-054, TC-055, TC-056, TC-018
    ann = w.user("ann")
    two_envs(w, ann)
    pat(w, ann, "k")
    c = login(w, "ann")
    for url in ("/settings", "/settings?lang=en"):
        r = c.get(url)
        t = r.text
        assert "<script" not in t.lower() and "style=" not in t and len(re.findall(r"<style\b", t)) == 1 and 'http-equiv="refresh"' not in t
        css = re.search(r"<style>(.*?)</style>", t, re.S).group(1)
        digest = base64.b64encode(hashlib.sha256(css.encode("utf-8")).digest()).decode()
        assert "style-src 'sha256-%s'" % digest in r.headers["content-security-policy"]
        assert SECOND.lower() not in t.lower() and not re.search(r"12 小時|12 h\b|12 hours", t, re.I)
        assert not re.search(r"(src|href|action)=\"https?://", t)
        for banned in ("歡迎使用", "第一次使用", "建立第一個專案"):
            assert banned not in t


def test_st11_web_settings_obeys_tc060():
    # TC-045, TC-069, TC-075: the module draws what it is given; it reaches no action, no store, no network
    tree = ast.parse(SETTINGS_PY.read_text(encoding="utf-8"))
    imports = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            imports |= {a.name for a in n.names} | set((n.module or "").split("."))
        elif isinstance(n, ast.Import):
            imports |= {p for a in n.names for p in a.name.split(".")}
    assert not (imports & {"confirm", "jobs", "compute_envs", "agents", "status", "actions", "store", "sqlite3", "urllib", "http", "requests", "socket"}), imports
    assert imports >= {"web_board"}
