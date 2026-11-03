# Nothing existing: the guard that keeps spoken Chinese out of every page and every Chinese string table (web-wording-sweep); /launch alone was guarded before (test_web_guided_launch_2b.py).
"""web-wording-sweep: the banned-word guard, widened from /launch to every page and every Chinese string table. The test cases are named in the
comments (TC-001 ...); they are in specs/web-wording-sweep/test-case.md. `BANNED`, `BANNED_ALL` and `banned_in` live here and test_web_guided_launch_2b.py imports them.

Rules of the guard (plan, "作法" 2 and 3):
* a Chinese page is read as its visible text: tags, <script>, <style> and the content of <code>, <pre>, <kbd> are taken out, the description cells of the
  pipeline table (`prow`, `scol`, the pipeline's own English) too; the words of title/aria-label/placeholder/alt are added;
* the pages that print `中文 (English)` side by side (log in, /welcome, consent, the confirmation pages' titles) are read only up to the first English
  parenthesis of each element: the English half is not ours to judge;
* a standalone Latin `run` / `runs` is a banned word on a Chinese page (the maintainer's "我的 run"); the names the tests give to runs avoid it, so the rule is
  never switched off for the interface text."""
import ast
import html
import re
import time
from pathlib import Path

import pytest

from helpers import PLATFORM_DIR
from human_harness import csrf_of
from oauth_harness import Rig as OauthRig
from resume_harness import Rig
from test_clean_page import T0, expire, run_and_request
from test_web_actions import act_form, login, rid_of, run_of
from test_web_board import no_cjk, seed

PKG = PLATFORM_DIR / "abf_platform"

BANNED = ["用過", "選好", "寫死", "自己填", "自己調整", "你還沒", "還沒有", "還不能", "這個", "這份", "這條", "這一版", "一下", "弄", "搞", "東西", "喔",
          "啦", "吧", "囉", "蠻", "超"]
NEW_WORDS = ["你", "什麼都", "做不了", "讀不到", "算不出", "被動", "還沒", "這次", "這個月", "我們", "咱", "沒有這個", "在哪裡"]
BANNED_ALL = BANNED + NEW_WORDS
RUN_RE = re.compile(r"(?<![A-Za-z])runs?(?![A-Za-z])")
CJK_RE = re.compile(r"[　-〿㐀-鿿豈-﫿＀-￯]")
ENGLISH_PAREN = re.compile(r"\s*\((?=[A-Za-z])")


def banned_in(text, words=BANNED_ALL, run=True):
    """The banned words found in `text`. With the default list the standalone Latin `run`/`runs` is looked for too (reported as "run")."""
    found = [w for w in words if w in text]
    if run and RUN_RE.search(text):
        found.append("run")
    return found


# ---- reading a page -------------------------------------------------------------------------------------------------------------------

def plain_text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def cleaned(page):
    page = re.sub(r"<(script|style|code|pre|kbd)\b.*?</\1>", " ", page, flags=re.S)
    page = re.sub(r'(<tr class="prow"><td>.*?</td>)<td>.*?</td>', r"\1", page, flags=re.S)
    page = re.sub(r'(<tr class="scol"><td>.*?</td>)<td>.*?</td>', r"\1", page, flags=re.S)
    return page


def attribute_words(page):
    return [html.unescape(a) for a in re.findall(r'\b(?:title|aria-label|placeholder|alt)="([^"]*)"', page)]


def visible(page):
    """The Chinese interface text of a one-language page."""
    page = cleaned(page)
    return plain_text(page) + " " + " ".join(attribute_words(page))


def halves(page):
    """The Chinese half of every element of a `中文 (English)` page: the text of an element up to its first English parenthesis; an element with no
    Chinese in it at all is the English half (or a bare value) and is not read."""
    page = cleaned(page)
    out = []
    for piece in re.split(r"<[^>]+>", page):
        piece = html.unescape(piece).strip()
        if CJK_RE.search(piece):
            out.append(ENGLISH_PAREN.split(piece)[0])
    for a in attribute_words(page):
        out.append(ENGLISH_PAREN.split(a)[0])
    return " ".join(out)


def bad_page(page, both=False):
    return banned_in(halves(page) if both else visible(page))


# ---- the world -----------------------------------------------------------------------------------------------------------------------

@pytest.fixture
def rig(tmp_path, monkeypatch):
    r = Rig(tmp_path, monkeypatch)
    r.w.clock.t = T0
    return r


STAGES = ("launch", "running", "results", "downstream", "finished")
TABS = ("tasks", "logs", "info", "config", "metrics", "outputs")


def board_world(rig):
    """alpha-* runs of ann in the four states a run shows (the names avoid the word `run`, see the header)."""
    ann = rig.user("ann")
    ids = {}
    for st in ("running", "succeeded", "failed", "lost"):
        ids[st] = seed(rig.w, "alpha-" + st, st, ann, counts=dict(succeeded=1, failed=1 if st == "failed" else 0, running=1 if st == "running" else 0),
                       reason="boom" if st == "failed" else None)
    real = run_of(rig, ann, "beta-one", status="failed")
    return ann, ids, real


# ---- US6: the guard itself ------------------------------------------------------------------------------------------------------------

def test_guard_catches_every_new_word():
    # TC-071, TC-072, TC-073, TC-074, TC-075, TC-076
    assert BANNED[:3] == ["用過", "選好", "寫死"] and len(BANNED) == 22 and len(NEW_WORDS) == 13 and BANNED_ALL == BANNED + NEW_WORDS
    for w in BANNED_ALL:
        assert w in banned_in("前%s後" % w), w
        assert w in bad_page('<main><p>前%s後</p></main>' % w), w
    assert banned_in("請於終端機執行指令，會依您的設定處理。") == []
    assert banned_in("您的分析") == [] and "你" in banned_in("你的分析")
    assert banned_in('<p>x</p>') == []
    assert bad_page("<p>請依序完成步驟。</p><code>run</code><pre>run a run</pre><kbd>runs</kbd>") == []
    assert bad_page('<table><tr class="prow"><td>x</td><td>Run this 這個</td></tr></table><table><tr class="scol"><td>c</td><td>東西</td></tr></table>') == []
    for ok in ("running", "prune", "Rerun", "overrun", "trunk"):
        assert banned_in("前 %s 後" % ok) == [], ok
    for bad in ("我的 run", "前 run 後", "runs", "run。", "（run）", "run-a"):
        assert "run" in banned_in(bad), bad
    assert bad_page("<p>請按「送出」。 (Press 這個 the run)</p>", both=True) == []
    assert bad_page("<p>請按這個。 (Press)</p>", both=True) == ["這個"]
    assert bad_page("<p>請按「送出」。</p><p>(a job of this run) 送出</p>", both=True) == []
    assert bad_page('<p title="必填你">x</p>') == ["你"]


def test_2b_still_uses_the_shared_list():
    # TC-079, TC-080
    import test_web_guided_launch_2b as two_b
    assert two_b.BANNED is BANNED and len(two_b.BANNED) == 22
    assert two_b.hits is banned_in
    src = (PLATFORM_DIR / "tests" / "test_web_guided_launch_2b.py").read_text(encoding="utf-8")
    assert '"選用這個樣本" not in page and "用過的" not in page' in src
    assert "assert banned_in(page) == [w], w" in src      # the old guard test keeps its words and its `== [w]` (read the diff)


# ---- US1 / US2: the Chinese string tables -------------------------------------------------------------------------------------------

def tables():
    from abf_platform import web, web_board, web_cost, web_finished, web_settings, web_upload
    return {"web_board.STRINGS": web_board.STRINGS, "web_board.GUIDED": web_board.GUIDED, "web_settings.STRINGS": web_settings.STRINGS,
            "web_cost.STRINGS": web_cost.STRINGS, "web_finished.STRINGS": web_finished.STRINGS, "web_upload.STRINGS": web_upload.STRINGS,
            "web._PLAIN": web._PLAIN}


def flat(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from flat(v)
    elif isinstance(value, (list, tuple, set)):
        for v in value:
            yield from flat(v)


def test_banned_words_cover_every_zh_string_table():
    # TC-003, TC-006, TC-007, TC-040, TC-082
    bad = []
    for name, table in tables().items():
        for key, value in table["zh"].items():
            for s in flat(value):
                hit = banned_in(s)
                if hit:
                    bad.append((name, key, hit, s[:40]))
    assert bad == [], "%d values are spoken Chinese: %s" % (len(bad), bad)


def test_upload_page_spoken_sentences_are_formal():
    # TC-040 (ruling 15a): the sentences the banned list cannot catch; the page says 尚無／未／為空／返回, never 沒有／是空的／回到
    from abf_platform import web_upload
    spoken = ["沒有可用", "是空的", "沒有收下", "沒有排入", "請回到", "沒有選樣本表", "沒有在時限", "沒有成功", "沒有傳成功", "沒有登記"]
    bad = [(k, w) for k, v in web_upload.STRINGS["zh"].items() for w in spoken if w in v]
    assert bad == []
    assert "請回到 AI" not in (PKG / "web.py").read_text(encoding="utf-8")


def zh_tables_in(source, stem):
    """The names of the module-level dicts that hold a Chinese value in `source` (the text of one web*.py), as "stem.NAME"."""
    found = set()
    for node in ast.parse(source).body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if not isinstance(getattr(node, "value", None), ast.Dict):
            continue
        has_cjk = any(isinstance(n, ast.Constant) and isinstance(n.value, str) and CJK_RE.search(n.value) for n in ast.walk(node.value))
        for t in targets:
            if has_cjk and isinstance(t, ast.Name):
                found.add("%s.%s" % (stem, t.id))
    return found


def scan_web_sources(sources):
    """`sources` is {stem: source text}; the set of Chinese tables found in all of them."""
    found = set()
    for stem, source in sources.items():
        found |= zh_tables_in(source, stem)
    return found


def test_every_zh_table_is_covered():
    # TC-077, TC-078
    real = {path.stem: path.read_text(encoding="utf-8") for path in sorted(PKG.glob("web*.py"))}
    found = scan_web_sources(real)
    assert found == set(tables()), (found ^ set(tables()))
    assert len(found) == 7
    # TC-078: a fake module with one more dictionary that holds Chinese shows up as one more table, so the comparison above would turn red
    fake = dict(real, web_fake='NEW_STRINGS = {"zh": {"hello": "你好"}, "en": {"hello": "hi"}}\nPLAIN = {"a": "b"}\n')
    more = scan_web_sources(fake)
    assert more - found == {"web_fake.NEW_STRINGS"}
    assert more != set(tables())
    # a table of Latin text only, and a Chinese value that is not in a dictionary, are not tables
    assert scan_web_sources({"web_x": 'EN = {"a": "b"}\nTEXT = "你好"\n'}) == set()


def test_embedded_chinese_of_web_py_is_formal():
    # TC-006, TC-022 .. TC-035, TC-038, TC-039 (the sentences that sit in the code of web.py, not in a table: every branch, also those a page test cannot reach)
    path = PKG / "web.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) \
                and isinstance(getattr(n.body[0], "value", None), ast.Constant):
            docstrings.add(id(n.body[0].value))
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings and CJK_RE.search(n.value):
            text = re.sub(r"<(code|pre|kbd)\b.*?</\1>", " ", n.value, flags=re.S)
            half = ENGLISH_PAREN.split(plain_text(text))[0]
            if banned_in(half):
                bad.append((n.lineno, banned_in(half), half[:40]))
    assert bad == [], bad


def test_the_plan_table_values():
    # TC-008, TC-009, TC-010 .. TC-019
    from abf_platform import web, web_board, web_cost, web_finished, web_settings
    want_board = {
        "mine": "我的分析", "none_yet": "尚無分析紀錄。", "no_analyses": "尚無分析", "this_analysis": "本分析的對話", "ask_here": "詢問本分析",
        "c_open": "開啟確認頁", "c_content_text": "該次分析已成功；其中間檔（work）可清理，結果不受影響。",
        "c_next_text": "請開啟確認頁，核對將刪除的資料夾後再決定。", "r_site": "站台無回應", "row_site": "執行 · 站台無回應",
        "not_reached": "該次分析尚未進行至此階段。", "not_found_title": "找不到該次分析", "not_found_body": "無此分析，或該分析不屬於您。",
        "quick": "沿用設定重新分析", "no_notices": "目前無通知", "no_failed_tasks": "無失敗任務", "r_none": "未送出任何內容。",
        "r_generic": "目前無法執行此操作。", "r_form": "表單驗證碼不符或已失效，未送出任何內容。請重新整理頁面後再操作。",
        "o_failed": "無法讀取", "o_none": "無輸出資料夾紀錄", "o_empty": "此資料夾為空",
        "level_action": "待處理", "row_stopped": "執行 · 已取消", "r_stopped": "已取消"}
    for k, v in want_board.items():
        assert web_board.STRINGS["zh"][k] == v, k
    assert web_board.STRINGS["zh"]["quick"] == web_board.GUIDED["zh"]["g_quick"]
    s = web_settings.STRINGS["zh"]
    assert s["key_note"] == "金鑰僅儲存於您的瀏覽器，不會傳送至平台。" and s["token_hint"] == "請於終端機執行 abf-platform token new 建立。"
    assert s["check_cmd"] == "請以指令確認" and "尚無運算環境。" in (s.get("ce_none"), s.get("no_ce"))
    c = web_cost.STRINGS["zh"]
    assert c["th_where"] == "執行位置" and c["empty"] == "— 本月尚無分析" and c["bad_month"] == "月份格式不符，已顯示本月。"
    assert c["no_reason"] == "無法計算" and c["unknown_runs"] == "另有 %d 個分析無法計算" and c["note"].endswith("數字依執行紀錄估算，略低於實際帳單。")
    assert c["usd_note"] == "SU 以 %s 匯率概算為美元，並非帳單金額。" and c["action"] == "待處理：本月雲端額度已用盡"
    f = web_finished.STRINGS["zh"]
    assert (f["params"], f["defaults"], f["gone_note"], f["foreign"], f["no_multiqc"], f["no_files"]) == (
        "已變更的參數", "全部採預設值", "該次送出的內容已不保留。", "此分析並非經由平台送出，無來源紀錄。", "該次未產生", "無檔案")
    assert web._PLAIN["zh"]["run"] == "分析名稱"


# ---- US5: the board and the run page -------------------------------------------------------------------------------------------------

def test_board_empty_state_is_formal(rig):
    # TC-001, TC-002, TC-003, TC-005
    rig.user("ann")
    t = login(rig, "ann").get("/").text
    text = visible(t)
    assert "我的分析" in text and "尚無分析紀錄。" in text and "尚無分析" in text
    for old in ("我的 run", "還沒有 run。", "還沒有分析"):
        assert old not in text, old
    assert bad_page(t) == []


def test_board_with_runs_has_no_banned_word(rig):
    # TC-004, TC-005, TC-049, TC-081
    ann, ids, real = board_world(rig)
    c = login(rig, "ann")
    for url in ["/"] + ["/?run=" + i for i in list(ids.values()) + [real]]:
        t = c.get(url).text
        for side in ("left", "middle", "right"):
            part = t.split('data-pane="%s"' % side)[1].split("data-pane=")[0]
            assert banned_in(visible(part)) == [], (url, side)
        for old in ("選用這個樣本", "用過的", "我的 run", "還沒有 run。"):
            assert old not in visible(t), old


def test_run_page_every_stage_and_tab(rig):
    # TC-004, TC-009, TC-013, TC-050, TC-051, TC-052
    ann, ids, real = board_world(rig)
    c = login(rig, "ann")
    for rid in list(ids.values()) + [real]:
        for stage in STAGES:
            assert bad_page(c.get("/?run=%s&stage=%s" % (rid, stage)).text) == [], (rid, stage)
        for tab in TABS:
            assert bad_page(c.get("/?run=%s&stage=running&tab=%s" % (rid, tab)).text) == [], (rid, tab)
            assert bad_page(c.get("/?run=%s&stage=results&tab=%s" % (rid, tab)).text) == [], (rid, tab)
    t = c.get("/?run=no-such-run").text
    assert bad_page(t) == [] and "找不到該次分析" in t
    other = rig.user("bob")
    seed(rig.w, "gamma-one", "succeeded", other)
    t = c.get("/?run=id-gamma-one").text
    assert bad_page(t) == []


def test_clean_notice_and_cleanup_pages_are_formal(rig):
    # TC-011, TC-028, TC-031, TC-044, TC-049, TC-062, TC-063
    ann = rig.user("ann")
    rid = run_and_request(rig.w, ann, name="alpha-one")
    c = login(rig, "ann")
    board = c.get("/?run=id-alpha-one").text
    assert "開啟確認頁" in board and "該次分析已成功；其中間檔（work）可清理，結果不受影響。" in board
    assert "請開啟確認頁，核對將刪除的資料夾後再決定。" in board and bad_page(board) == []
    page = c.get("/c/" + rid).text
    assert "以下為將被刪除的全部內容。確認無誤後，請按「確認刪除」；按下後才會排入佇列。" in visible(page) and bad_page(page, both=True) == []
    done = c.post("/c/" + rid, data={"csrf": csrf_of(page)})
    assert "代理將清理該次分析的中間檔，結果不受影響。" in done.text and bad_page(done.text, both=True) == []
    assert bad_page(c.get("/c/" + rid).text, both=True) == []


def test_welcome_login_consent_confirm_pages(rig):
    # TC-022 .. TC-039, TC-062 .. TC-067, TC-099
    w = rig.w
    ann = rig.user("ann")
    bob = rig.user("bob")
    seen = []

    def see(response):
        seen.append(response.text)
        assert bad_page(response.text, both=True) == [], (response.status_code, bad_page(response.text, both=True), response.text[:200])
        return response

    # the login page, also with its error lines
    anon = w.web()
    t = see(anon.get("/login")).text
    assert "請以您的姓名與" in visible(t) and "你" not in halves(t)
    see(anon.post("/login", data={"name": "ann", "password": "wrong-password-ZQ9"}, headers={"origin": "http://testserver"}))
    see(anon.post("/login", data={"name": "ann", "password": "x" * 5000}, headers={"origin": "http://testserver"}))
    see(anon.post("/login", data={"name": "ann", "password": "x"}, headers={"origin": "http://evil.example"}))
    for _ in range(12):
        r = anon.post("/login", data={"name": "ann", "password": "wrong-password-ZQ9"}, headers={"origin": "http://testserver"})
    see(r)
    # /welcome
    from test_web_welcome import HDR, NEW, issue, send, temp_login
    c, temp, resp = temp_login(w, "bob")
    t = see(c.get("/welcome")).text
    assert "目前使用的是管理者提供的臨時密碼，效期 72 小時，僅可用於設定個人密碼。設定完成後，請改以新密碼登入。" in halves(t)
    see(send(w, c, temp, confirm="different-pass-ZQ4"))
    see(send(w, c, temp, new="x" * 5000, confirm="x" * 5000))
    see(send(w, c, temp, csrf="bad-token"))
    see(send(w, c, temp, headers={"origin": "http://evil.example"}))
    see(send(w, c, "wrong-old-ZQ5"))
    # the confirmation pages
    mine = login(rig, "ann")
    rid = rig.w.launch(caller=ann, run_name="alpha-one")["id"]
    page = see(mine.get("/c/" + rid)).text
    assert "以下為將被送出的全部內容。確認無誤後，請按「送出」；按下後才會排入佇列。" in visible(page)
    see(mine.get("/c/" + "0" * 32))
    see(mine.get("/c/not-an-id"))
    see(mine.post("/c/" + rid, data={"csrf": "bad"}))
    see(mine.post("/c/" + rid, data={"csrf": csrf_of(page)}, headers={"origin": "http://evil.example"}))
    rig.user("cleo")
    theirs = see(login(rig, "cleo").get("/c/" + rid))
    assert "該申請並非由您送出，無法在此檢視或操作。" in visible(theirs.text) or "該申請並非由您送出" in halves(theirs.text)
    see(mine.post("/c/" + rid, data={"csrf": csrf_of(page)}))
    see(mine.post("/c/" + rid, data={"csrf": csrf_of(page)}))
    again = rig.w.launch(caller=ann, run_name="alpha-two")["id"]
    from abf_platform import actions
    actions.void_request(rig.w.ip.state_db, again, "test")
    see(mine.get("/c/" + again))
    more = rig.w.launch(caller=ann, run_name="alpha-three")["id"]
    expire(rig.w, more)
    see(mine.get("/c/" + more))
    # cancel
    going = run_of(rig, ann, "alpha-go", status=None)
    fields = act_form(mine.get("/?run=" + going).text, "cancel", going)
    cancel = rid_of(mine.post("/act/cancel", data=fields))
    see(mine.get("/c/" + cancel))
    assert "以下為將被取消的全部內容。" in visible(mine.get("/c/" + cancel).text)
    # a clean request that expired
    old = run_and_request(rig.w, ann, name="alpha-old")
    expire(rig.w, old)
    see(mine.get("/c/" + old))
    # the temporary-password session on a normal page, and a log-in with nothing
    see(c.get("/"))


def consent_pages(w):
    rig = OauthRig(w)
    w.user("ann")
    out = []
    redirect = "https://claude.ai/api/mcp/auth_callback"
    for uri in (None, redirect):
        cid = rig.new_client(redirect_uris=[uri] if uri else None)
        path, verifier, cid = rig.start(client_id=cid, redirect=uri or "https://claude.example/cb")
        anon = rig.another()
        out.append(("login", anon.get(path)))
        rig.log_in("ann")
        out.append(("page", rig.c.get(path)))
        out.append(("bad csrf", rig.c.post(path, data={"csrf": "bad", "decision": "allow"}, headers={"origin": rig.base})))
        token = csrf_of(rig.c.get(path).text)
        out.append(("no decision", rig.c.post(path, data={"csrf": token}, headers={"origin": rig.base})))
        out.append(("deny", rig.c.post(path, data={"csrf": token, "decision": "deny"}, headers={"origin": rig.base})))
        out.append(("again", rig.c.get(path)))
    out.append(("unknown", rig.c.get("/consent/" + "0" * 32)))
    out.append(("unnamed", rig.c.get(rig.start(client_id=rig.new_client(client_name=None))[0])))
    return out


def test_consent_pages(rig):
    # TC-032, TC-033, TC-034, TC-035, TC-064 .. TC-067
    pages = consent_pages(rig.w)
    for name, r in pages:
        assert bad_page(r.text, both=True) == [], (name, r.status_code, bad_page(r.text, both=True))
    text = " ".join(halves(r.text) for n, r in pages if n == "page")
    assert "要求連線至本平台，並以" in text and "您的身分" in text and "連線完成後將導回：" in text and "若不認得該網站，請按「拒絕」。" in text
    assert "允許後，該連接器可讀取您的分析紀錄，並可請求送出分析" in text and "不能代您送出" in text and "於本網站的確認頁按「送出」" in text
    assert "(未命名 unnamed)" in " ".join(r.text for n, r in pages if n == "unnamed")
    assert "該申請已處理完畢。請返回連接器重新開始。" in " ".join(halves(r.text) for n, r in pages if n == "again")


def test_refusal_lines_on_the_board(rig):
    # TC-014, TC-044, TC-069, TC-100
    from abf_platform import confirm, jobs, web_board
    ann = rig.user("ann")
    rig.user("bob")
    failed = run_of(rig, ann, "alpha-f", status="failed")
    going = run_of(rig, ann, "alpha-g", status=None)
    done = run_of(rig, ann, "alpha-d", status="succeeded")
    c = login(rig, "ann")
    flashes = []
    for verb, rid in (("resume", done), ("cancel", failed), ("cancel", done), ("resume", going), ("relaunch", going), ("resume", "id-no-such")):
        fields = act_form(c.get("/?run=" + rid).text, verb, rid) if rid != "id-no-such" else None
        if fields is None:
            fields = dict(act_form(c.get("/?run=" + failed).text, "resume", failed) or {}, run=rid)
        r = c.post("/act/" + verb, data=fields)
        if r.status_code != 303:
            flashes.append(r.text)
    bob = login(rig, "bob")
    fields = act_form(c.get("/?run=" + failed).text, "resume", failed)
    if fields:
        flashes.append(bob.post("/act/resume", data=fields).text)
        flashes.append(bob.post("/act/resume", data=dict(fields, csrf="bad")).text)
    for text in flashes:
        assert bad_page(text) == [], bad_page(text)
    # the sentence of the action layer that the board shows when a folder still has a job (confirm.py)
    msg = "該次分析仍有工作在排隊或進行中，無法刪除 (a job of this run is still queued or running)"
    line = web_board.plain_reason(msg, "zh") + " " + web_board.STRINGS["zh"]["r_none"]
    assert banned_in(line) == [] and "仍有工作在排隊或進行中" in line and "未送出任何內容。" in line
    src = (PKG / "confirm.py").read_text(encoding="utf-8")
    assert "該次分析仍有工作在排隊或進行中，無法刪除 (a job of this run is still queued or running)" in src and "這個 run 還有工作" not in src
    assert "還有工作在排隊" not in src
    assert jobs.JobRefused and confirm


# ---- US4 / US5: usage, settings, finished, upload ----------------------------------------------------------------------------------------

def test_cost_settings_finished_pages(tmp_path, monkeypatch):
    # TC-037, TC-041, TC-042, TC-053 .. TC-061
    import json
    from abf_platform import cloud_cost
    from human_harness import World
    import test_web_cost as cost
    rates = tmp_path / "cloud_rates.json"
    rates.write_text(json.dumps(cost.CLOUD_RATES), encoding="utf-8")
    monkeypatch.setattr(cloud_cost, "RATES_PATH", rates)
    w = World(tmp_path, monkeypatch)
    ann = w.user("ann")
    empty = login_of(w, "ann").get("/usage").text
    assert "— 本月尚無分析" in visible(empty) and bad_page(empty) == []
    bad = login_of(w, "ann").get("/usage?month=2026-13").text
    assert "月份格式不符，已顯示本月。" in visible(bad) and bad_page(bad) == []
    assert bad_page(login_of(w, "ann").get("/usage?month=2099-01").text) == []
    cost.seed(w, "cl-ok", ann, "cloud", hours=6)
    cost.seed(w, "cl-x1", ann, "cloud", tasks=[dict(realtime_ms=cost.H, machine_type="m-unknown")])
    cost.seed(w, "nc-a", ann, "nchc", hours=2)
    cost.seed(w, "nc-b", ann, "nchc", status="failed", hours=1)
    cost.seed(w, "nc-c", ann, None, hours=1)
    cost.cap(w, ann, 1.0)
    t = login_of(w, "ann").get("/usage").text
    assert "執行位置" in visible(t) and "無法計算" in visible(t) and "另有 1 個分析無法計算" in visible(t) and bad_page(t) == []
    cost.cap(w, ann, 0.01)
    assert bad_page(login_of(w, "ann").get("/usage").text) == []
    # settings: with environments, without, and an environment that cannot be used
    s = login_of(w, "ann").get("/settings").text
    assert bad_page(s) == []
    import test_web_settings as st
    st.sql(w, "UPDATE compute_envs SET status = 'invalid'")
    assert bad_page(login_of(w, "ann").get("/settings").text) == []
    st.sql(w, "DELETE FROM compute_envs")
    s = login_of(w, "ann").get("/settings").text
    assert "尚無運算環境。" in visible(s) and bad_page(s) == []


def login_of(w, name):
    c = w.web()
    assert w.login(c, name).status_code == 303
    return c


def test_settings_forms_refusals_are_formal(tmp_path, monkeypatch):
    # TC-037
    from human_harness import World
    w = World(tmp_path, monkeypatch)
    w.user("ann")
    c = login_of(w, "ann")
    for url, data in (("/settings/pipelines", {"csrf": "bad"}), ("/settings/pipelines/confirm", {"csrf": "bad"})):
        r = c.post(url, data=data, headers={"origin": "http://testserver"})
        assert bad_page(r.text) == [], (url, bad_page(r.text))
        r = c.post(url, data=data, headers={"origin": "http://evil.example"})
        assert bad_page(r.text, both=True) == [], url


def test_finished_pages(tmp_path, monkeypatch):
    # TC-018, TC-060, TC-061
    from human_harness import World
    import test_web_finished as fin
    w = World(tmp_path, monkeypatch)
    ann, c, rid = fin.world(w, "alpha-done")
    t = c.get(fin.url(rid)).text
    assert bad_page(t) == []
    fin.forget(w, "alpha-done")
    t = c.get(fin.url(rid)).text
    assert "該次送出的內容已不保留。" in visible(t) and bad_page(t) == []
    w2 = World(tmp_path / "foreign", monkeypatch)
    ann2, c2, rid2 = fin.world(w2, "alpha-foreign", kept=False)
    t = c2.get(fin.url(rid2)).text
    assert bad_page(t) == []


def test_upload_pages(tmp_path, monkeypatch):
    # TC-040, TC-006 (the upload page: form, refusals, progress, failure, done)
    import test_web_upload as tu
    up = tu.Up(tmp_path, monkeypatch)
    c = up.client()
    pages = [c.get("/upload").text, c.get("/upload?lang=en").text]
    for files in (((tu.R1, b""), (tu.R2, b"C")), (("../x_R1.fastq.gz", b"A"),), ((tu.R1, b"A"), (tu.R1, b"A")), ((tu.R1, b"A"), ("b_R1.fastq.gz", b"A")), ()):
        pages.append(up.post(c, files=files).text)
    pages.append(up.post(c, name="").text)
    pages.append(up.post(c, sheet="not,a\nsheet").text)
    batch = up.ok(c)
    pages.append(c.get("/upload/" + batch).text)
    first, second = [j["id"] for j in up.jobs()]
    up.finish(first, ok=False, message="cloud size differs")
    up.expire(second)
    pages.append(c.get("/upload/" + batch).text)
    pages.append(c.get("/upload/no-such-batch").text)
    del pages[1]      # the English page is read for CJK in test_english_pages_have_no_cjk_everywhere
    for text in pages:
        assert bad_page(text) == [], bad_page(text)
    b2 = up.ok(c, version="v2")
    for j in up.jobs()[2:]:
        up.finish(j["id"])
    assert bad_page(c.get("/upload/" + b2).text) == []
    # the page with no usable environment
    d = tu.Up(tmp_path / "second", monkeypatch)
    from abf_platform import compute_envs
    tu.sql_exec(d.state, "DELETE FROM compute_envs")
    assert bad_page(d.client().get("/upload").text) == []


def test_english_pages_have_no_cjk_everywhere(rig):
    # TC-070
    ann, ids, real = board_world(rig)
    c = login(rig, "ann")
    urls = ["/?lang=en"] + ["/?run=%s&lang=en" % i for i in list(ids.values()) + [real]]
    for rid in [real, ids["failed"]]:
        urls += ["/?run=%s&stage=%s&lang=en" % (rid, s) for s in STAGES]
        urls += ["/?run=%s&stage=running&tab=%s&lang=en" % (rid, t) for t in TABS]
    urls += ["/usage?lang=en", "/usage?month=2099-01&lang=en", "/usage?month=2026-13&lang=en", "/settings?lang=en", "/upload?lang=en", "/launch?lang=en"]
    for u in urls:
        r = c.get(u)
        assert no_cjk(r.text), u
    run_and_request(rig.w, ann, name="alpha-one")
    assert no_cjk(c.get("/?run=id-alpha-one&lang=en").text)
