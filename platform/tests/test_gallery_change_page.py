# Nothing existing: the confirmation page of a pack or a delete of gallery figures; the page and its words are ours.
"""mcp-gallery-actions: the page /c/<request> for a gallery_change request, in Chinese and in English. TC IDs are from
specs/mcp-gallery-actions/test-case.md (file C of its overview)."""
import re
import time

import pytest

from human_harness import World, csrf_of
from test_confirm_page import logged_in
from test_gallery_change import ask_delete, ask_pack, core, core_delete, gal, packed_of, prints, rows
from test_publish_figure import gallery, index_of

CJK = re.compile(r"[　-〿぀-ヿ㐀-鿿＀-￯]")


@pytest.fixture
def w(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    world.clock.t = time.time()
    return world


def page(w, name, rid, lang="", client=None):
    c = client or logged_in(w, name, w.web(clock=w.clock))
    r = c.get("/c/" + rid + ("?lang=" + lang if lang else ""))
    return c, r


def body(r):
    return r.text.split("<body", 1)[1] if "<body" in r.text else r.text


def post(c, rid, lang="", token=None):
    r = c.get("/c/" + rid + ("?lang=" + lang if lang else ""))
    return c.post("/c/" + rid + ("?lang=" + lang if lang else ""), data={"csrf": token or csrf_of(r.text)})


def test_opening_the_page_changes_nothing(w):
    # TC-003
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, ["a.png", "b.png"])["request_id"]
    before = prints(gallery(w, ann, run))
    c, r = page(w, "ann", rid)
    assert r.status_code == 200 and "a.png" in r.text and prints(gallery(w, ann, run)) == before
    assert [x["state"] for x in rows(w)] == ["pending"]


def test_the_pack_page_in_chinese(w):
    # TC-010, TC-020
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, ["a.png", "b.png"])["request_id"]
    c, r = page(w, "ann", rid)
    t = r.text
    assert "打包確認" in t and "加入交付包：a.png、b.png" in t and "移出交付包：c.png" in t and "仍留在圖庫" in t and "之後可以再打包" in t
    assert re.search(r"<button[^>]*>\s*送出\s*</button>", t) and csrf_of(t) and 'method="post"' in t
    assert "工作編號" not in t and "送出新分析" not in t and "style=" not in t and "<script" not in t


def test_the_pack_page_in_english_has_no_cjk(w):
    # TC-011
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, ["a.png", "b.png"])["request_id"]
    c, r = page(w, "ann", rid, "en")
    t = body(r)
    assert "Added to the package: a.png, b.png" in t and "Removed from the package: c.png" in t
    assert "stays in the gallery and can be packed again later" in t and not CJK.search(t)
    assert re.search(r"<button[^>]*>\s*Send\s*</button>", t) and "Confirm the delivery package" in t


def test_the_delete_page_in_both_languages(w):
    # TC-014, TC-017, TC-020
    ann, run = gal(w, packed=("a.png",))
    rid = ask_delete(w, ann, run, "a.png")["request_id"]
    c, r = page(w, "ann", rid)
    t = r.text
    assert "刪除確認" in t and "要刪除：a.png" in t and "a.png.code.txt" in t and "a.png.params.txt" in t and "目前在交付包內：是" in t
    assert re.search(r"<button[^>]*>\s*確認刪除\s*</button>", t) and "工作編號" not in t and "復原" not in t
    c, r = page(w, "ann", rid, "en", client=c)
    t = body(r)
    assert "Will delete a.png, its code file a.png.code.txt and its parameter file a.png.params.txt" in t
    assert "a.png is currently in the delivery package" in t and not CJK.search(t)
    assert re.search(r"<button[^>]*>\s*Confirm delete\s*</button>", t) and "Confirm deleting a figure" in t


def test_clearing_the_package_has_its_own_line_on_the_page(w):
    # TC-013
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, [])["request_id"]
    c, r = page(w, "ann", rid)
    assert "交付包將被清空" in r.text
    c, r = page(w, "ann", rid, "en", client=c)
    assert "The delivery package will be emptied" in r.text and "stay in the gallery" in r.text


def test_the_yes_on_the_page_writes_and_the_success_page_says_what_was_done(w):
    # TC-025, TC-028, TC-021, TC-045
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, ["a.png", "b.png"])["request_id"]
    c = logged_in(w, "ann", w.web(clock=w.clock))
    token = csrf_of(c.get("/c/" + rid).text)
    done = post(c, rid, token=token)
    assert done.status_code == 200 and packed_of(w, ann, run) == ["a.png", "b.png"]
    assert "交付包現有 2 張：a.png、b.png" in done.text and "工作編號" not in done.text and "href=" in done.text
    after = prints(gallery(w, ann, run))
    again = post(c, rid, token=token)
    assert again.status_code == 200 and "交付包現有 2 張" in again.text and prints(gallery(w, ann, run)) == after
    did = ask_delete(w, ann, run, "a.png")["request_id"]
    en = post(c, did, "en")
    assert "Deleted a.png" in en.text and "工作編號" not in en.text and not CJK.search(body(en))
    assert "a.png" not in index_of(w, ann, run) and [r["channel"] for r in rows(w)] == ["PAGE", "PAGE"]
    p = ask_pack(w, ann, run, ["b.png", "c.png"])["request_id"]
    en = post(c, p, "en")
    assert "The delivery package now holds 2 figures: b.png, c.png" in en.text


def test_expired_void_and_stale_pages_each_have_their_own_sentence(w):
    # TC-022, TC-048
    from abf_platform import confirm
    ann, run = gal(w)
    r_old = ask_pack(w, ann, run, ["a.png"])["request_id"]
    r_stale = ask_pack(w, ann, run, ["b.png"])["request_id"]
    c = logged_in(w, "ann", w.web(clock=w.clock))
    tok = csrf_of(c.get("/c/" + r_stale).text)
    assert core_delete(w, ann, run, "c.png")["ok"]                          # the gallery changes after the question
    st = c.post("/c/" + r_stale, data={"csrf": tok})
    assert st.status_code == 409 and "圖庫已變動" in st.text and "重新提出" in st.text and "工作編號" not in st.text
    assert packed_of(w, ann, run) == []
    gone = c.get("/c/" + r_stale)
    assert gone.status_code == 409 and "None" not in gone.text and "工作編號" not in gone.text
    w.clock.t += confirm.PENDING_SECONDS + 5
    exp = c.get("/c/" + r_old)
    assert exp.status_code == 410 and "逾時" in exp.text and "工作編號" not in exp.text and "None" not in exp.text
    en = c.get("/c/" + r_old + "?lang=en")
    assert "expired" in en.text and not CJK.search(body(en))
    r_new = ask_pack(w, ann, run, ["a.png"])["request_id"]
    c2 = logged_in(w, "ann", w.web(clock=w.clock))
    token = csrf_of(c2.get("/c/" + r_new).text)
    w.clock.t += confirm.PENDING_SECONDS + 5
    assert c2.post("/c/" + r_new, data={"csrf": token}).status_code == 410


def test_the_page_guards_hold(w):
    # TC-044
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, ["a.png"])["request_id"]
    before = prints(gallery(w, ann, run))
    anon = w.web(clock=w.clock)
    r = anon.post("/c/" + rid, data={"csrf": "x"})
    assert r.status_code in (200, 303, 401) and "交付包現有" not in r.text
    c = logged_in(w, "ann", w.web(clock=w.clock))
    assert c.post("/c/" + rid, data={"csrf": "wrong"}).status_code == 403
    assert c.post("/c/" + rid, data={}).status_code == 403
    assert c.post("/c/" + rid, data={"csrf": csrf_of(c.get("/c/" + rid).text)}, headers={"Origin": "https://evil.example"}).status_code in (400, 403)
    assert prints(gallery(w, ann, run)) == before and rows(w)[0]["state"] == "pending"


def test_somebody_else_sees_a_403_without_the_names(w):
    # TC-065, TC-066
    ann, run = gal(w)
    bob = w.user("bob")
    rid = ask_pack(w, ann, run, ["a.png", "b.png"])["request_id"]
    before = prints(gallery(w, ann, run))
    c = logged_in(w, "bob", w.web(clock=w.clock))
    r = c.get("/c/" + rid)
    assert r.status_code == 403 and "a.png" not in r.text and "交付包" not in body(r).replace("非您的申請", "")
    p = c.post("/c/" + rid, data={"csrf": "x" * 32})
    assert p.status_code == 403 and prints(gallery(w, ann, run)) == before and rows(w)[0]["state"] == "pending"


def test_text_is_escaped_in_the_page(w):
    # TC-010
    ann, run = gal(w)
    folder = gallery(w, ann, run)
    import json
    idx = json.loads((folder / "index.json").read_text())
    idx["figures"]["x<b>.png"] = dict(idx["figures"]["a.png"])
    (folder / "index.json").write_text(json.dumps(idx))
    assert ask_pack(w, ann, run, ["x<b>.png"])["state"] == "refused"            # a name with markup is not a name of this gallery
