# Nothing existing: Seqera's platform and Tower Agent have no figure gallery, so nothing there can pack or delete a figure for a person who said "confirm" in a chat.
"""mcp-gallery-actions (gallery slice 3), the action layer: request_pack_figures and request_delete_figure, the write that runs after the person's yes, and what the
person is shown. TC IDs are from specs/mcp-gallery-actions/test-case.md (file A of its overview)."""
import asyncio
import hashlib
import itertools
import json
import re
import threading
import time
from pathlib import Path

import pytest

from human_harness import World
from test_publish_figure import fig, gallery, index_of, press, call, stored, tree
from test_web_board import seed

NAMES = ("a.png", "b.png", "c.png")


@pytest.fixture
def w(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    world.clock.t = time.time()
    return world


def core(w, ann, run, names):
    from abf_platform.actions import figures
    return figures.pack_figures(w.ip.index, w.ip.state_db, run, names, caller=ann, clock=w.clock)


def core_delete(w, ann, run, name):
    from abf_platform.actions import figures
    return figures.delete_figure(w.ip.index, w.ip.state_db, run, name, caller=ann)


def ask_pack(w, who, run, names, **kw):
    from abf_platform import actions
    return asyncio.run(actions.request_pack_figures(w.ip.state_db, run_id=run, names=names, caller=who, clock=w.clock, index_path=w.ip.index, **kw))


def ask_delete(w, who, run, name, **kw):
    from abf_platform import actions
    return asyncio.run(actions.request_delete_figure(w.ip.state_db, run_id=run, name=name, caller=who, clock=w.clock, index_path=w.ip.index, **kw))


def yes(w, who, rid, channel="PAGE"):
    """The person's yes through the action layer, as the confirmation page gives it."""
    from abf_platform import actions
    return actions.approve(w.ip.state_db, rid, confirmed_by=actions.PAGE, caller=who, clock=w.clock)


def refused_by_yes(w, who, rid):
    from abf_platform import actions
    with pytest.raises(actions.NotApproved) as e:
        yes(w, who, rid)
    return e.value


def gal(w, name="ann", run_name="r1", names=NAMES, packed=("c.png",)):
    """Ann, her succeeded run, and a gallery of `names` (a.png has code and params) of which `packed` are in the package."""
    ann = w.user(name)
    run = seed(w, run_name, "succeeded", ann)
    for i in range(0, len(names), 10):                                         # at most 10 figures per publish_figure call
        stored(w, ann, run, names[i:i + 10])
    if packed:
        assert core(w, ann, run, list(packed))["ok"]
    return ann, run


def prints(folder):
    """The fingerprint of a gallery: every file name and the hash of its content."""
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(folder).iterdir())} if Path(folder).exists() else {}


def rows(w):
    """The gallery_change requests only (the figures were put there by publish_figure requests, which are not what these tests count)."""
    return w.sql("SELECT * FROM confirmations WHERE kind = 'gallery_change' ORDER BY created_at, id")


def lines(text, start):
    return [ln for ln in text.splitlines() if ln.startswith(start)]


def packed_of(w, ann, run):
    return sorted(k for k, v in index_of(w, ann, run).items() if v["packed"])


# ---- US1/US2: what is asked and shown; nothing moves before the yes ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [["z.png"], ["a.png", "z.png"], ["../a.png"], ["a/b.png"], ["a\\b.png"], ["a\x00.png"], ["f%d.png" % i for i in range(31)], "a.png", None, [3], {"a.png": 1}])
def test_bad_names_refuse_the_whole_pack_without_a_request(w, bad):
    # TC-007
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    got = ask_pack(w, ann, run, bad)
    assert got["state"] == "refused" and got["message"] and rows(w) == [] and prints(gallery(w, ann, run)) == before
    if isinstance(bad, list) and bad and isinstance(bad[0], str) and bad[0] not in ("a.png",):
        assert "Traceback" not in got["message"]


@pytest.mark.parametrize("bad", [["a.png"], 3, None, "../a.png", "a/b.png", "a\x00.png", "nope.png"])
def test_bad_delete_names_refuse_without_a_request(w, bad):
    # TC-007, TC-098
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    got = ask_delete(w, ann, run, bad)
    assert got["state"] == "refused" and got["message"] and rows(w) == [] and prints(gallery(w, ann, run)) == before


def test_delete_takes_one_figure_only(w):
    # TC-098
    ann, run = gal(w)
    before = prints(gallery(w, ann, run))
    for many in (["a.png", "b.png"], "a.png,b.png", "a.png b.png"):
        got = ask_delete(w, ann, run, many)
        assert got["state"] == "refused" and ("一張" in got["message"] or "one figure" in got["message"]), many
    assert rows(w) == [] and prints(gallery(w, ann, run)) == before


def test_a_pack_screen_says_added_removed_and_that_the_removed_stay(w):
    # TC-009, TC-012
    ann, run = gal(w, names=NAMES + ("d.png",), packed=("c.png", "a.png"))
    got = ask_pack(w, ann, run, ["a.png", "b.png"])
    assert got["state"] == "pending" and got["request_id"] and got["url"]
    text = got["summary"]
    assert lines(text, "加入交付包：") == ["加入交付包：b.png"]                      # a is in the package already: it is not an addition
    assert lines(text, "移出交付包：")[0].startswith("移出交付包：c.png") and "仍留在圖庫" in lines(text, "移出交付包：")[0] and "之後可以再打包" in lines(text, "移出交付包：")[0]
    assert "a.png" in lines(text, "不變（已在交付包內）：")[0] and "d.png" in lines(text, "不變（未打包）：")[0]
    assert lines(text, "打包後交付包：") == ["打包後交付包：2 張（a.png、b.png）"]
    assert packed_of(w, ann, run) == ["a.png", "c.png"]                        # nothing moved


def test_the_first_example_is_the_one_the_maintainer_wrote(w):
    # TC-009
    ann, run = gal(w)
    got = ask_pack(w, ann, run, ["a.png", "b.png"])
    assert lines(got["summary"], "加入交付包：") == ["加入交付包：a.png、b.png"]
    assert lines(got["summary"], "移出交付包：")[0].startswith("移出交付包：c.png（仍留在圖庫")
    assert "2 張" in lines(got["summary"], "打包後交付包：")[0]


def test_clearing_the_package_is_said_loudly_and_asks_once(w):
    # TC-013
    ann, run = gal(w)
    got = ask_pack(w, ann, run, [])
    assert got["state"] == "pending" and "交付包將被清空" in got["summary"] and "c.png" in got["summary"] and "仍留在圖庫" in got["summary"]
    assert len(rows(w)) == 1
    core(w, ann, run, [])
    nothing = ask_pack(w, ann, run, [])                                       # an empty package stays empty: nothing to ask
    assert nothing["state"] == "unchanged" and "沒有需要變更" in nothing["message"] and len(rows(w)) == 1


def test_a_request_with_no_effect_makes_no_row(w):
    # TC-013
    ann, run = gal(w)
    got = ask_pack(w, ann, run, ["c.png"])                                    # c is the whole package already
    assert got["state"] == "unchanged" and got["request_id"] is None and "沒有需要變更" in got["message"] and rows(w) == []
    empty = w.user("zed")
    run2 = seed(w, "r9", "succeeded", empty)
    assert ask_pack(w, empty, run2, [])["state"] == "unchanged" and rows(w) == []


def test_a_delete_screen_says_the_files_and_the_package(w):
    # TC-014, TC-015, TC-016
    ann, run = gal(w, names=("a.png", "b.png", "n.png"), packed=("a.png",))
    plain = {"filename": "n.png", "content_base64": __import__("base64").b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32).decode()}
    press(w, "ann", call(w, ann, run, [plain])["request_id"])                 # replaces n.png with one that has no code and no parameters
    d = ask_delete(w, ann, run, "a.png")
    assert d["state"] == "pending"
    assert lines(d["summary"], "要刪除：") == ["要刪除：a.png"]
    assert "a.png.code.txt" in d["summary"] and "a.png.params.txt" in d["summary"]
    assert lines(d["summary"], "目前在交付包內：")[0].startswith("目前在交付包內：是") and "一併移出交付包" in d["summary"]
    assert "復原" not in d["summary"]
    b = ask_delete(w, ann, run, "b.png")
    assert lines(b["summary"], "目前在交付包內：")[0].startswith("目前在交付包內：否") and "移出交付包" not in b["summary"]
    n = ask_delete(w, ann, run, "n.png")
    assert "code.txt" not in n["summary"] and "params.txt" not in n["summary"] and "n.png" in n["summary"]
    assert prints(gallery(w, ann, run)).keys() >= {"a.png", "a.png.code.txt", "a.png.params.txt"}


def test_the_bundle_is_small_and_holds_no_bytes(w):
    # TC-023
    ann, run = gal(w, names=(), packed=())
    for start in (0, 10, 20):                                                  # at most 10 figures per publish_figure call
        stored(w, ann, run, ["f%d.png" % i for i in range(start, start + 10)])
    ask_pack(w, ann, run, ["f%d.png" % i for i in range(30)])
    ask_delete(w, ann, run, "f3.png")
    got = w.sql("SELECT kind, bundle_json FROM confirmations WHERE kind = 'gallery_change'")
    assert len(got) == 2
    for r in got:
        raw = r["bundle_json"]
        b = json.loads(raw)
        assert b["action"] in ("pack", "delete") and b["run_id"] == run and b["run_name"] == "r1" and "effect" in b
        assert set(b) <= {"action", "run_id", "run_name", "names", "name", "effect", "snapshot"}
        assert "content_base64" not in raw and "print(1)" not in raw and "k=1" not in raw and len(raw) < 20000


def test_the_three_channels_give_the_same_names(w):
    # TC-018
    from abf_platform import actions, confirm
    ann, run = gal(w, names=NAMES + ("d.png",), packed=("c.png",))
    got = ask_pack(w, ann, run, ["a.png", "b.png"])
    zh = got["summary"]
    en = actions.screen_for_page(confirm.facts(w.ip.state_db, got["request_id"]), None, "en")
    names = lambda text: sorted(set(re.findall(r"[a-z]\.png", " ".join(ln for ln in text.splitlines() if ":" in ln or "：" in ln))))
    assert names(zh) == names(en) == ["a.png", "b.png", "c.png", "d.png"]
    stored_text = rows(w)[0]["screen_text"]
    assert stored_text == zh
    d = ask_delete(w, ann, run, "a.png")
    assert "a.png" in actions.screen_for_page(confirm.facts(w.ip.state_db, d["request_id"]), None, "en") and "a.png" in d["summary"]


# ---- US3: the yes writes exactly the requested change, and keeps the figures -----------------------------------------------------------------

def test_pack_after_the_yes_sets_exactly_that_set_and_never_loses_a_figure(w):
    # TC-008, TC-030, TC-031
    from abf_platform import actions
    ann, run = gal(w)
    folder = gallery(w, ann, run)
    base = {k: v for k, v in prints(folder).items() if k != "index.json"}
    for want in (["a.png"], ["b.png", "c.png"], [], ["a.png", "b.png", "c.png"]):
        got = ask_pack(w, ann, run, want)
        if got["state"] == "unchanged":
            continue
        yes(w, ann, got["request_id"])
        assert packed_of(w, ann, run) == sorted(want)
        assert {k: v for k, v in prints(folder).items() if k != "index.json"} == base
    assert core(w, ann, run, ["a.png", "b.png"])["ok"]
    got = ask_pack(w, ann, run, ["a.png", "b.png"])
    assert got["state"] == "unchanged"
    yes(w, ann, ask_pack(w, ann, run, ["c.png"])["request_id"])
    assert [f["name"] for f in actions.list_figures(w.ip.index, w.ip.state_db, run, caller=ann, packed_only=True)["figures"]] == ["c.png"]
    assert (folder / "a.png.code.txt").exists() and (folder / "a.png").exists() and not index_of(w, ann, run)["a.png"]["packed"]


def test_delete_after_the_yes_removes_the_three_files_and_nothing_else(w):
    # TC-027, TC-109
    ann, run = gal(w, packed=("a.png",))
    folder = gallery(w, ann, run)
    (folder.parent / "a.png").write_bytes(b"outside")
    (folder.parent / "a.png.code.txt").write_bytes(b"outside")
    others = {k: v for k, v in prints(folder).items() if not k.startswith("a.png") and k != "index.json"}
    yes(w, ann, ask_delete(w, ann, run, "a.png")["request_id"])
    assert not any(p.name.startswith("a.png") for p in folder.iterdir())
    assert "a.png" not in index_of(w, ann, run) and packed_of(w, ann, run) == []
    assert {k: v for k, v in prints(folder).items() if k != "index.json"} == others
    assert (folder.parent / "a.png").read_bytes() == b"outside" and (folder.parent / "a.png.code.txt").read_bytes() == b"outside"
    assert ask_delete(w, ann, run, "../a.png")["state"] == "refused"


def test_a_path_in_a_name_is_refused_at_the_proposal(w):
    # TC-109
    ann, run = gal(w)
    folder = gallery(w, ann, run)
    idx = json.loads((folder / "index.json").read_text())
    idx["figures"]["../evil.png"] = dict(idx["figures"]["a.png"])
    (folder / "index.json").write_text(json.dumps(idx))
    assert ask_delete(w, ann, run, "../evil.png")["state"] == "refused" and ask_pack(w, ann, run, ["../evil.png"])["state"] == "refused"
    assert rows(w) == []


# ---- US4: the gallery is checked again at the yes, once, under the lock ------------------------------------------------------------------------

def test_a_replaced_figure_counts_as_a_changed_gallery(w):
    # TC-052
    from abf_platform import actions
    ann, run = gal(w, packed=())
    rid = ask_pack(w, ann, run, ["a.png", "b.png"])["request_id"]
    press(w, "ann", call(w, ann, run, [fig("b.png", code="print(2)\n")])["request_id"])      # the same name, new content
    before = prints(gallery(w, ann, run))
    err = refused_by_yes(w, ann, rid)
    assert "圖庫已變動" in str(err) and "重新提出" in str(err)
    assert packed_of(w, ann, run) == [] and prints(gallery(w, ann, run)) == before


def test_a_package_changed_by_hand_makes_both_requests_stale(w):
    # TC-053
    ann, run = gal(w)
    r1 = ask_pack(w, ann, run, ["a.png", "b.png"])["request_id"]
    r2 = ask_delete(w, ann, run, "c.png")["request_id"]
    assert core(w, ann, run, ["a.png"])["ok"]                                  # the package was changed by hand in between
    for rid in (r1, r2):
        assert "圖庫已變動" in str(refused_by_yes(w, ann, rid))
    assert packed_of(w, ann, run) == ["a.png"] and set(index_of(w, ann, run)) == set(NAMES)


def test_a_new_unrelated_figure_makes_the_request_stale(w):
    # TC-054
    ann, run = gal(w, packed=())
    rid = ask_pack(w, ann, run, ["a.png", "b.png"])["request_id"]
    press(w, "ann", call(w, ann, run, [fig("d.png")])["request_id"])
    assert "圖庫已變動" in str(refused_by_yes(w, ann, rid))
    assert packed_of(w, ann, run) == [] and "d.png" in index_of(w, ann, run)


def test_an_untouched_gallery_passes_the_check(w):
    # TC-055
    ann, run = gal(w)
    yes(w, ann, ask_pack(w, ann, run, ["a.png", "b.png"])["request_id"])
    assert packed_of(w, ann, run) == ["a.png", "b.png"]


def test_a_damaged_index_is_refused_in_one_sentence_and_not_overwritten(w):
    # TC-056
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, ["a.png"])["request_id"]
    path = gallery(w, ann, run) / "index.json"
    path.write_bytes(b"{ not json")
    err = refused_by_yes(w, ann, rid)
    assert "暫時無法讀取" in str(err) and str(path.parent) not in str(err) and "index.json" not in str(err)
    assert path.read_bytes() == b"{ not json" and not [p for p in path.parent.iterdir() if p.name.startswith(".tmp-")]


def test_a_missing_gallery_folder_is_not_found_and_creates_nothing(w):
    # TC-057
    import shutil
    ann, run = gal(w)
    rid = ask_pack(w, ann, run, ["a.png"])["request_id"]
    shutil.rmtree(gallery(w, ann, run))
    err = refused_by_yes(w, ann, rid)
    assert "找不到" in str(err) and not gallery(w, ann, run).exists()
    ann2, run2 = gal(w, name="amy", run_name="r2")
    rid2 = ask_delete(w, ann2, run2, "a.png")["request_id"]
    w.sql("SELECT 1")
    import sqlite3
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE launches SET user_id = ? WHERE run_name = 'r2'", (ann.user_id,))     # the run is somebody else's now
    con.close()
    assert "找不到" in str(refused_by_yes(w, ann2, rid2)) and (gallery(w, ann2, run2) / "a.png").exists()


def test_the_check_and_the_write_are_one_hold_of_the_lock(w, monkeypatch):
    # TC-059
    from abf_platform.actions import figures
    ann, run = gal(w, packed=())
    rid = ask_pack(w, ann, run, ["a.png", "b.png"])["request_id"]
    real = figures._pack_figures
    seen = {}

    def hooked(*a, **k):
        t = threading.Thread(target=lambda: seen.setdefault("web", core_delete(w, ann, run, "b.png")))
        t.start()
        t.join(0.5)
        seen["blocked"] = t.is_alive()          # a web delete cannot slip in between the check and the write
        seen["thread"] = t
        return real(*a, **k)
    monkeypatch.setattr(figures, "_pack_figures", hooked)
    yes(w, ann, rid)
    seen["thread"].join(10)
    assert seen["blocked"] is True and seen["web"]["ok"]
    assert "b.png" not in index_of(w, ann, run) and packed_of(w, ann, run) == ["a.png"] and not (gallery(w, ann, run) / "b.png").exists()


def sound(folder):
    """index.json is valid and agrees with the files: every figure has its image, and no figure's file is there without its entry."""
    idx = json.loads((folder / "index.json").read_text())["figures"]
    on_disk = {p.name for p in folder.iterdir() if not p.name.startswith(".tmp-")} - {"index.json"}
    want = set()
    for k, v in idx.items():
        want.add(k)
        for key in ("code_file", "params_file"):
            if v.get(key):
                want.add(v[key])
    assert on_disk == want and not [p for p in folder.iterdir() if p.name.startswith(".tmp-")]
    return idx


def test_web_and_mcp_interleaved_never_lose_an_update(w):
    # TC-060
    ann, run = gal(w, packed=())
    for _ in range(50):
        folder = gallery(w, ann, run)
        for n in NAMES:                                                          # a fresh start every round: all three there, none packed
            if n not in index_of(w, ann, run):
                stored(w, ann, run, (n,))
        core(w, ann, run, [])
        r1 = ask_pack(w, ann, run, ["b.png"])
        r2 = ask_delete(w, ann, run, "a.png")
        ops = [lambda: core(w, ann, run, ["a.png"]), lambda: core_delete(w, ann, run, "c.png"),
               lambda: yes_or_none(w, ann, r1["request_id"]), lambda: yes_or_none(w, ann, r2["request_id"])]
        threads = [threading.Thread(target=op) for op in ops]
        [t.start() for t in threads]
        [t.join(30) for t in threads]
        idx = sound(folder)
        assert not [n for n in idx if n not in NAMES]


def yes_or_none(w, who, rid):
    from abf_platform import actions
    try:
        return yes(w, who, rid)
    except actions.NotApproved:
        return None


def model(order, snap):
    """What the gallery should be after the four operations in this order: the web ones always apply, an approval applies only while the gallery is as it was asked."""
    state = {"a.png": False, "b.png": False, "c.png": True}
    for op in order:
        if op == "web_pack_a":
            state = {k: k == "a.png" for k in state}
        elif op == "web_delete_c":
            state.pop("c.png", None)
        elif op == "mcp_pack_b" and state == snap:
            state = {k: k == "b.png" for k in state}
        elif op == "mcp_delete_a" and state == snap:
            state.pop("a.png", None)
    return state


def test_all_24_orders_of_four_operations_equal_the_sequential_result(w):
    # TC-061
    ann, run = gal(w)
    folder = gallery(w, ann, run)
    original = {p.name: p.read_bytes() for p in folder.iterdir()}
    start = {"a.png": False, "b.png": False, "c.png": True}
    for order in itertools.permutations(("web_pack_a", "web_delete_c", "mcp_pack_b", "mcp_delete_a")):
        for p in list(folder.iterdir()):
            p.unlink()
        for n, data in original.items():
            (folder / n).write_bytes(data)
        r1 = ask_pack(w, ann, run, ["b.png"])["request_id"]
        r2 = ask_delete(w, ann, run, "a.png")["request_id"]
        for op in order:
            {"web_pack_a": lambda: core(w, ann, run, ["a.png"]), "web_delete_c": lambda: core_delete(w, ann, run, "c.png"),
             "mcp_pack_b": lambda: yes_or_none(w, ann, r1), "mcp_delete_a": lambda: yes_or_none(w, ann, r2)}[op]()
        got = {k: v["packed"] for k, v in sound(folder).items()}
        assert got == model(order, start), order


def test_a_publish_and_a_change_approved_at_once_lose_nothing(w):
    # TC-062
    ann, run = gal(w, packed=())
    for i in range(10):
        pub = call(w, ann, run, [fig("p%d.png" % i)])["request_id"]
        chg = ask_pack(w, ann, run, ["a.png"] if i % 2 == 0 else ["b.png"])["request_id"]
        ts = [threading.Thread(target=lambda: yes_or_none(w, ann, pub)), threading.Thread(target=lambda: yes_or_none(w, ann, chg))]
        [t.start() for t in ts]
        [t.join(30) for t in ts]
        idx = sound(gallery(w, ann, run))
        assert "p%d.png" % i in idx
        core(w, ann, run, [])


# ---- US5: owners ---------------------------------------------------------------------------------------------------------------------------

def test_someone_elses_run_and_a_missing_run_get_one_answer(w):
    # TC-063, TC-064
    ann, run = gal(w)
    bob = w.user("bob")
    before = prints(gallery(w, ann, run))
    a = ask_pack(w, bob, run, ["a.png"])
    b = ask_pack(w, bob, "no-such-run", ["a.png"])
    assert a["state"] == b["state"] == "refused" and a["message"].replace(run, "X") == b["message"].replace("no-such-run", "X")
    c = ask_delete(w, bob, run, "a.png")
    d = ask_delete(w, bob, "no-such-run", "a.png")
    assert c["message"].replace(run, "X") == d["message"].replace("no-such-run", "X") and "a.png" not in c["message"]
    assert rows(w) == [] and prints(gallery(w, ann, run)) == before


def test_a_run_that_is_not_finished_can_still_be_asked_about(w):
    # TC-067
    ann = w.user("ann")
    run = seed(w, "r1", "running", ann)
    stored(w, ann, run, ("a.png", "b.png"))
    got = ask_pack(w, ann, run, ["a.png"])
    assert got["state"] == "pending"
    yes(w, ann, got["request_id"])
    assert packed_of(w, ann, run) == ["a.png"]


# ---- US6: one core, no second copy ----------------------------------------------------------------------------------------------------------

def test_both_paths_call_the_same_core(w, monkeypatch):
    # TC-068
    from abf_platform.actions import figures
    ann, run = gal(w)
    calls = []
    for name in ("pack_figures", "delete_figure"):
        real = getattr(figures, name)
        monkeypatch.setattr(figures, name, lambda *a, _r=real, _n=name, **k: (calls.append(_n), _r(*a, **k))[1])
    yes(w, ann, ask_pack(w, ann, run, ["a.png"])["request_id"])
    yes(w, ann, ask_delete(w, ann, run, "b.png")["request_id"])
    assert calls == ["pack_figures", "delete_figure"]
    import ast
    src = (Path(figures.__file__)).read_text(encoding="utf-8")
    fn = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name == "write_gallery_change")
    body = ast.get_source_segment(src, fn)
    for banned in ("index.json", "os.replace", "os.unlink", "open(", "_write_index", "json.dump("):
        assert banned not in body, banned


def test_mcp_and_web_leave_the_same_bytes(w):
    # TC-069, TC-070
    import shutil
    ann, run1 = gal(w)
    run2 = seed(w, "r2", "succeeded", ann)
    shutil.copytree(gallery(w, ann, run1), gallery(w, ann, run2))
    core(w, ann, run1, ["a.png", "b.png"])
    yes(w, ann, ask_pack(w, ann, run2, ["a.png", "b.png"])["request_id"])
    assert tree(gallery(w, ann, run1)) == tree(gallery(w, ann, run2))
    core_delete(w, ann, run1, "a.png")
    yes(w, ann, ask_delete(w, ann, run2, "a.png")["request_id"])
    assert tree(gallery(w, ann, run1)) == tree(gallery(w, ann, run2))
    assert not any(p.name.startswith("a.png") for p in gallery(w, ann, run2).iterdir())


def test_the_tool_handlers_hold_no_gallery_logic():
    # TC-071
    import ast
    src = (Path(__file__).resolve().parent.parent / "abf_platform" / "mcp_server.py").read_text(encoding="utf-8")
    mine = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.AsyncFunctionDef) and n.name in ("pack_figures_tool", "delete_figure_tool")]
    assert len(mine) == 2
    for fn in mine:
        text = ast.get_source_segment(src, fn)
        assert ("request_pack_figures" in text) or ("request_delete_figure" in text)
        for banned in ("index.json", "os.unlink", "os.replace", "open(", "figures."):
            assert banned not in text


def test_the_tool_descriptions_say_the_three_things(w):
    # TC-091
    tools, _ = w.mcp([])
    by = {t.name: t for t in tools}
    pack, dele = by["pack_figures"], by["delete_figure"]
    assert list(pack.input_schema["properties"]) == ["run_id", "names", "request_id", "user_confirmed"]
    assert list(dele.input_schema["properties"]) == ["run_id", "name", "request_id", "user_confirmed"]
    assert pack.input_schema["required"] == ["run_id", "names"] and dele.input_schema["required"] == ["run_id", "name"]
    for t in (pack, dele):
        assert "user_confirmed" in t.description and "only after" in t.description and len(t.description) < 1200
    assert "exactly this set" in pack.description and "stay in the gallery" in pack.description and "not deleted" in pack.description
    assert "one figure" in dele.description.lower() and "cannot be undone" not in dele.description.lower()


def test_no_undo_and_no_content_parameter_exists(w):
    # TC-099, TC-104
    from abf_platform import actions
    tools, _ = w.mcp([])
    assert not [t.name for t in tools if re.search(r"undelete|restore|undo|復原", t.name)]
    assert not [n for n in dir(actions) if re.search(r"undelete|restore|undo", n)]
    app = w.web()
    assert not [r.path for r in app.app.routes if re.search(r"undelete|restore|undo", getattr(r, "path", ""))]
    for t in tools:
        props = set(t.input_schema.get("properties", {}))
        if t.name in ("pack_figures", "delete_figure"):
            assert not props & {"content_base64", "figures", "code", "params", "caption", "filename"}
        if props & {"content_base64", "figures"}:
            assert t.name == "publish_figure"
