# Nothing existing: tests of guided-launch-2d (the launch page in six steps: analysis name first, only the compute environments that are set up, pipeline and
# version decided in one place, the workflow diagram shown under the pipeline, no pre-check step); the page, the version list and the CSP of /launch are ours.
"""guided-launch-2d: /launch in six steps, offline. The test cases are named in the comments (TC-001 ...); they are in
specs/guided-launch-2d/test-case.md. The two read actions (`pipeline_files`, `latest_release`) are replaced by the fake of
test_web_guided_launch_2 (so no job is queued and nothing connects out); the compute environments the page sees are replaced where a test needs a
status the rig does not have."""
import base64
import html
import json
import re
import urllib.parse

import pytest

from helpers import REPO_ROOT
from test_pipeline_files_action import (T0, cache_file, db, clock, lr, seed_cache, serve, sql, tags_result, world)  # noqa: F401  (fixtures)
from test_web_actions import area_sheet, form_values, launch_csrf, login, pending
from test_web_board import no_cjk
from test_web_guided_launch import SEL, ready, rig, set_env, steps  # noqa: F401  (rig is a fixture)
from test_web_guided_launch_2 import (A, DIAGRAM, DIAGRAM_URL, NETWORK, PNG, REFRESH, error_files, fk, good_files, good_image, latest,  # noqa: F401
                                      loading_files, plain_text, step)
from test_web_guided_launch_2b import BANNED, banned_in, form_of, hidden_of, main_of, query_of, select_html, selected_of

NEW = "/launch?pipeline=nf-core/ampliseq&src=new"
REL = ["2.18.0", "2.17.0", "2.16.1"]
TITLES_ZH = ["分析名稱", "運算環境", "管線", "樣本表", "參數", "確認"]
S1 = "尚無可用的運算環境，請先至設定頁完成設定。"
S2 = "此管線版本尚未在所選運算環境登記，請洽管理者登記；已登記的管線列於設定頁。"
S3 = "尚無已上傳的樣本表，請先上傳。"
S4 = "正在讀取版本清單…"
S5 = "正在讀取流程圖…"
S6 = "此管線未提供流程圖。"


@pytest.fixture(autouse=True)
def _releases_on_the_fake(request):
    if "fk" in request.fixturenames:      # the fake answers a version list now (the action tests below do not use it)
        request.getfixturevalue("fk").latest = latest(releases=list(REL))


# ---- helpers --------------------------------------------------------------------------------------------------------------------------------

def patch_envs(monkeypatch, change):
    """The environments the page sees: what the platform lists, changed by `change(list of dicts) -> list of dicts`."""
    current = A().list_compute_envs
    real = getattr(current, "real", current)      # a second patch in one test starts from the platform's list again

    def fake(*a, **kw):
        envs = [dict(e, config=dict(e.get("config") or {})) for e in real(*a, **kw)["compute_envs"]]
        return {"compute_envs": change(envs)}
    fake.real = real
    monkeypatch.setattr(A(), "list_compute_envs", fake)


def only_status(status):
    return lambda envs: [dict(e, status=status) for e in envs]


class Launches:
    """request_launch replaced by a recorder (it answers like the real one would for a refusal: no confirmation)."""

    def __init__(self, monkeypatch):
        self.calls = []
        real = A().request_launch

        async def spy(*a, **kw):
            self.calls.append(kw)
            return await real(*a, **kw)
        monkeypatch.setattr(A(), "request_launch", spy)


@pytest.fixture
def spy(monkeypatch):
    return Launches(monkeypatch)


def pairs_of(text):
    return {k: html.unescape(v) for k, v in re.findall(r'<input type="hidden" name="(\w+)" value="([^"]*)"', form_of(text))}


def raw_form(c, **over):
    """A form as the page would send it, without reading the environment or the sheet from the page (the page may have none)."""
    t = c.get("/launch").text
    data = {"csrf": launch_csrf(t), "pipeline": "nf-core/ampliseq", "revision": "2.18.0", "run_name": "web-run", "samplesheet": "samples.csv",
            "ce_name": "lab-a", "params": "", "shown_pipeline": "nf-core/ampliseq", "shown_revision": "2.18.0"}
    data.update(over)
    return data


def titles_of(text):
    return re.findall(r'<span class="gttl">([^<]+)</span>', text)


def lform(text):
    return re.search(r'<form class="lform" method="post" action="/launch">(.*?)</form>', text, re.S).group(1)


def all_pages(rig, fk, lang=""):
    """{state: page} for every state the contract names."""
    ann, c = ready(rig)
    out = {"ready": c.get(SEL + lang).text, "new": c.get(NEW + lang).text, "plain": c.get("/launch" + ("?lang=en" if lang else "")).text}
    fk.files = loading_files()
    out["loading"] = c.get(SEL + lang).text
    fk.files = error_files()
    out["failed"] = c.get(SEL + lang).text
    fk.files = good_files(diagram={"status": "none"})
    out["no diagram"] = c.get(SEL + lang).text
    fk.files = good_files()
    out["blocked"] = c.post("/launch", data=raw_form(c, run_name="", **({"lang": "en"} if lang else {}))).text
    bob = rig.user("bob")
    out["no sheet"] = login(rig, "bob").get(SEL + lang).text
    return out


# ---- US1: six steps -------------------------------------------------------------------------------------------------------------------

def test_tc001_six_steps_in_the_order(rig, fk):
    # TC-001
    _, c = ready(rig)
    t = c.get(SEL).text
    assert sorted(steps(t)) == [1, 2, 3, 4, 5, 6] and len(re.findall(r'<details class="gstep ', main_of(t))) == 6
    assert titles_of(t) == TITLES_ZH
    assert re.findall(r'<summary><span class="gno">(\d)</span>', t) == list("123456")


def test_tc002_english_titles(rig, fk):
    # TC-002
    _, c = ready(rig)
    t = c.get(SEL + "&lang=en").text
    titles = titles_of(t)
    assert len(titles) == 6 and len(set(titles)) == 6 and all(x.strip() for x in titles) and all(no_cjk(x) for x in titles)
    assert "Pre-check" not in t and "Pre-check".lower() not in main_of(t).lower()


@pytest.mark.parametrize("lang", ["", "en"])
def test_tc003_no_pre_check_anywhere(rig, fk, lang):
    # TC-003
    for state, page in all_pages(rig, fk, "&lang=en" if lang else "").items():
        assert "前置檢查" not in page and "Pre-check" not in page and 'class="checks"' not in page and "版本已指定" not in page and "Revision pinned" not in page, state


def test_tc003_also_without_environment(rig, fk, monkeypatch):
    # TC-003
    _, c = ready(rig)
    patch_envs(monkeypatch, lambda envs: [])
    for url in (SEL, SEL + "&lang=en"):
        t = c.get(url).text
        assert "前置檢查" not in t and "Pre-check" not in t and 'class="checks"' not in t and "版本已指定" not in t


def test_tc004_numbers_and_state_marks(rig, fk):
    # TC-004
    _, c = ready(rig)
    pages = [(c.get(SEL).text, "zh"), (c.get(SEL + "&lang=en").text, "en"), (c.post("/launch", data=raw_form(c, run_name="")).text, "zh")]
    for t, lang in pages:
        s = steps(t)
        assert list(s) == [1, 2, 3, 4, 5, 6]
        heads = re.findall(r'<span class="gstate">([^<]*)</span>', t)
        want = r"^(✓ 已完成|● 目前|○ 之後)$" if lang == "zh" else r"^(✓ Done|● Current|○ Later)$"
        assert len(heads) == 6 and all(re.match(want, h) for h in heads), heads


def test_tc005_first_step_is_current(rig, fk):
    # TC-005
    _, c = ready(rig)
    t = c.get("/launch").text
    s = steps(t)
    assert s[1]["state"] == "current" and s[1]["open"]
    assert all(s[n]["state"] == "later" for n in (2, 3, 4, 5, 6))


def test_tc006_run_name_is_the_only_input_of_step_one(rig, fk):
    # TC-006
    _, c = ready(rig)
    t = c.get(SEL).text
    assert len(re.findall(r'name="run_name"', t)) == 1
    one = step(t, 1)
    assert 'name="run_name"' in one and 'class="req"' in one and len(re.findall(r"<(?:input|select|textarea)\b", one)) == 1


def test_tc007_one_submit_button_in_the_last_step(rig, fk):
    # TC-007
    _, c = ready(rig)
    t = c.get(SEL).text
    form = lform(main_of(t))
    assert form.count("<button") == 1 and re.findall(r"<button[^>]*>([^<]*)</button>", form) == ["送出（前往確認頁）"]
    assert "<button" in step(t, 6) and re.search(r'<button type="submit"', form)
    assert all("<button" not in step(t, n) for n in (1, 2, 3, 4, 5))


def test_tc008_confirm_step_only_shows(rig, fk):
    # TC-008
    _, c = ready(rig)
    t = c.get(SEL + "&run_name=my-run").text
    six = step(t, 6)
    for name in ("run_name", "pipeline", "revision"):
        assert 'name="%s"' % name not in six
    text = plain_text(six)
    for word in ("my-run", "nf-core/ampliseq", "2.18.0", "samples.csv", "lab-a"):
        assert word in text, word


def test_tc009_samplesheet_then_parameters_then_confirm(rig, fk):
    # TC-009
    _, c = ready(rig)
    t = c.get(SEL).text
    sheet, params, confirm = (t.index('data-step="%d"' % n) for n in (4, 5, 6))
    assert sheet < params < confirm
    assert 'name="samplesheet"' in step(t, 4) and 'name="p.' in step(t, 5) and 'name="params"' in step(t, 5)
    assert 'name="samplesheet"' not in step(t, 5) and 'name="p.' not in step(t, 6)


def test_tc010_run_name_from_the_address(rig, fk):
    # TC-010
    _, c = ready(rig)
    assert re.search(r'name="run_name" value="my-run"', step(c.get(SEL + "&run_name=my-run").text, 1))


# ---- US2: compute environment ---------------------------------------------------------------------------------------------------------

def env_names(text):
    return [html.unescape(x) for x in re.findall(r'<option value="([^"]*)"', select_html(step(text, 2), "ce_name"))]


@pytest.mark.parametrize("bad", ["creating", "invalid", "unsupported", "disabled"])
def test_tc011_only_available_environments(rig, fk, monkeypatch, bad):
    # TC-011
    _, c = ready(rig)

    def change(envs):
        a = dict(envs[0], name="env-ok", status="available")
        b = dict(envs[0], name="env-" + bad, status=bad)
        return [b, a]
    patch_envs(monkeypatch, change)
    t = c.get(SEL).text
    assert env_names(t) == ["env-ok"] and "env-" + bad not in t


def test_tc011_site_and_cloud_alike(rig, fk, monkeypatch):
    # TC-011
    _, c = ready(rig)
    for slurm, cloud in (("available", "creating"), ("creating", "available")):
        def change(envs, slurm=slurm, cloud=cloud):
            return [dict(envs[0], name="slurm-a", platform="slurm-platform", status=slurm),
                    dict(envs[0], name="cloud-a", platform="google-batch", status=cloud)]
        patch_envs(monkeypatch, change)
        assert env_names(c.get(SEL).text) == (["slurm-a"] if slurm == "available" else ["cloud-a"])


def test_tc012_address_value_of_an_unavailable_environment_is_ignored(rig, fk, monkeypatch):
    # TC-012
    _, c = ready(rig)
    patch_envs(monkeypatch, lambda envs: [dict(envs[0], name="env-b", status="invalid"), dict(envs[0], name="env-a", status="available")])
    t = c.get(SEL + "&ce_name=env-b").text
    assert selected_of(select_html(step(t, 2), "ce_name")) in ("env-a", None) and "env-b" not in t
    assert env_names(t) == ["env-a"]


@pytest.mark.parametrize("make", ["none", "all bad"])
@pytest.mark.parametrize("lang", ["", "&lang=en"])
def test_tc013_no_available_environment(rig, fk, monkeypatch, make, lang):
    # TC-013
    _, c = ready(rig)
    patch_envs(monkeypatch, (lambda envs: []) if make == "none" else only_status("invalid"))
    t = c.get(SEL + lang).text
    two = step(t, 2)
    assert 'name="ce_name"' not in t and "<button" not in lform(main_of(t))
    link = re.search(r'<a href="(/settings[^"]*)"', two)
    assert link and html.unescape(link.group(1)) == ("/settings?lang=en" if lang else "/settings")
    if not lang:
        assert S1 in plain_text(two)
    else:
        assert no_cjk(main_of(t))


@pytest.mark.parametrize("case", ["none", "all bad", "posted unavailable"])
def test_tc014_post_without_an_available_environment(rig, fk, monkeypatch, spy, case):
    # TC-014
    _, c = ready(rig)
    if case == "none":
        patch_envs(monkeypatch, lambda envs: [])
    elif case == "all bad":
        patch_envs(monkeypatch, only_status("invalid"))
    else:
        patch_envs(monkeypatch, lambda envs: [dict(envs[0], name="env-bad", status="invalid"), dict(envs[0], name="lab-a", status="available")])
    data = raw_form(c, ce_name="env-bad") if case == "posted unavailable" else raw_form(c)
    r = c.post("/launch", data=data)
    assert r.status_code == 400 and "運算環境必須是您名下可用的環境。" in r.text and spy.calls == []
    assert steps(r.text)[2]["state"] == "current"


def site_list(*entries):
    return lambda envs: [dict(e, config=dict(e.get("config") or {}, sitePipelines=list(entries))) for e in envs]


AMPLI = {"pipeline": "nf-core/ampliseq", "revision": "2.18.0", "module": "m", "home": "/h"}
OTHER = {"pipeline": "nf-core/rnaseq", "revision": "3.14.0", "module": "m", "home": "/h"}


def test_tc015_unregistered_pair(rig, fk, monkeypatch, spy):
    # TC-015
    _, c = ready(rig)
    patch_envs(monkeypatch, site_list(OTHER))
    t = c.get(SEL).text
    three = step(t, 3)
    assert S2 in plain_text(three) and re.search(r'<a href="/settings"', three)
    r = c.post("/launch", data=raw_form(c))
    assert r.status_code == 400 and spy.calls == [] and "登記" in plain_text(main_of(r.text)) and steps(r.text)[3]["state"] == "current"


def test_tc016_registered_pair_passes(rig, fk, monkeypatch, spy):
    # TC-016
    _, c = ready(rig)
    patch_envs(monkeypatch, site_list(OTHER, AMPLI))
    assert S2 not in plain_text(step(c.get(SEL).text, 3))
    r = c.post("/launch", data=raw_form(c))
    assert r.status_code == 303 and r.headers["location"].startswith("/c/") and len(spy.calls) == 1


@pytest.mark.parametrize("change", ["missing", "empty", "not a list"])
def test_tc017_no_registration_check(rig, fk, monkeypatch, spy, change):
    # TC-017
    _, c = ready(rig)
    if change == "missing":
        patch_envs(monkeypatch, lambda envs: [dict(e, config={k: v for k, v in e["config"].items() if k != "sitePipelines"}) for e in envs])
    elif change == "empty":
        patch_envs(monkeypatch, site_list())
    else:
        patch_envs(monkeypatch, lambda envs: [dict(e, config=dict(e["config"], sitePipelines="x")) for e in envs])
    assert S2 not in plain_text(step(c.get(SEL).text, 3))
    assert c.post("/launch", data=raw_form(c)).status_code == 303 and len(spy.calls) == 1


def test_tc018_the_posted_environment_decides(rig, fk, monkeypatch, spy):
    # TC-018
    _, c = ready(rig)

    def change(envs):
        a = dict(envs[0], name="lab-a", status="available", config=dict(envs[0]["config"], sitePipelines=[AMPLI]))
        b = dict(envs[0], name="lab-b", status="available", config=dict(envs[0]["config"], sitePipelines=[OTHER]))
        return [a, b]
    patch_envs(monkeypatch, change)
    assert env_names(c.get(SEL).text)[0] == "lab-a"
    r = c.post("/launch", data=raw_form(c, ce_name="lab-b"))
    assert r.status_code == 400 and spy.calls == []
    r = c.post("/launch", data=raw_form(c, ce_name="lab-a"))
    assert r.status_code == 303


def test_tc019_no_samplesheet(rig, fk, spy):
    # TC-019
    rig.user("ann")
    c = login(rig, "ann")
    t = c.get(SEL).text
    four = step(t, 4)
    assert S3 in plain_text(four) and "<a href=" in four and "<button" in lform(main_of(t))
    r = c.post("/launch", data=raw_form(c))
    assert r.status_code == 400 and "樣本表必須從已上傳的檔案中選擇。" in r.text and spy.calls == [] and steps(r.text)[4]["state"] == "current"


@pytest.mark.parametrize("lang,want", [("", "/upload"), ("&lang=en", "/upload?lang=en")])
def test_tc020_upload_link_is_the_board(rig, fk, lang, want):
    # TC-020 (web-upload-page ruling 13: the link of step 4 with no samplesheet now goes to the upload page, not to the board)
    rig.user("ann")
    c = login(rig, "ann")
    four = step(c.get(SEL + lang).text, 4)
    assert [html.unescape(h) for h in re.findall(r'<a href="([^"]+)"', four)] == [want]
    if lang:
        assert "Please upload one first." in four and no_cjk(four)


@pytest.mark.parametrize("kind", ["loading", "error", "ready"])
def test_tc021_parameter_read_status_opens_step_five(rig, fk, kind):
    # TC-021
    fk.files = {"loading": loading_files, "error": error_files, "ready": good_files}[kind]()
    _, c = ready(rig)
    five = plain_text(step(c.get(SEL).text, 5))
    mark = {"loading": "… 讀取管線參數表 讀取中", "error": "✗ 讀取管線參數表 代理連不到 GitHub，請檢查那台機器的網路。"}.get(kind)
    if kind == "ready":
        from test_web_guided_launch_2 import sample_counts
        n, m = sample_counts()
        mark = "✓ 讀取管線參數表 讀到 %d 組、%d 個參數" % (n, m)
    assert mark in five and five.index(mark) < five.index("沿用先前分析的參數")


# ---- US3: pipeline and version in one place --------------------------------------------------------------------------------------------

def revision_controls(text):
    return re.findall(r'<(?:input|select|textarea)\b[^>]*name="revision"[^>]*>', text)


def test_tc022_one_version_dropdown_newest_first(rig, fk):
    # TC-022
    _, c = ready(rig)
    t = c.get(NEW).text
    assert len(revision_controls(t)) == 1 and revision_controls(t)[0].startswith("<select")
    sel = select_html(t, "revision")
    assert [x for x in re.findall(r'<option value="([^"]*)"', sel)] == REL and selected_of(sel) == "2.18.0"
    assert not re.search(r'<input [^>]*name="revision"', t)


def test_tc023_used_tab_carries_the_version_hidden(rig, fk):
    # TC-023
    from test_web_guided_launch import launched
    ann, c = ready(rig)
    launched(rig, ann, "run-a")
    t = c.get(SEL + "&src=used").text
    assert re.findall(r'<input type="hidden" name="revision" value="2.18.0">', t) and len(revision_controls(t)) == 1
    assert "<select" not in "".join(revision_controls(t)) and 'name="revision" value="2.18.0" required' not in t
    assert not re.search(r'<input (?!type="hidden")[^>]*name="revision"', t)


def test_tc024_new_pipeline_without_version_loads(rig, fk, spy):
    # TC-024
    _, c = ready(rig)
    for lang in ("", "en"):
        data = raw_form(c, revision="", shown_pipeline="", shown_revision="", src="new", **({"lang": lang} if lang else {}))
        r = c.post("/launch", data=data)
        assert r.status_code == 303
        q = query_of(r)
        assert q["pipeline"] == "nf-core/ampliseq" and q["src"] == "new" and ("lang" in q) == bool(lang) and "revision" not in q
    assert spy.calls == []


def test_tc025_loaded_page_defaults_to_the_newest(rig, fk):
    # TC-025
    _, c = ready(rig)
    t = c.get(NEW).text
    assert selected_of(select_html(t, "revision")) == "2.18.0" and pairs_of(t)["shown_revision"] == "2.18.0"
    assert fk.main_calls() and all(x["revision"] == "2.18.0" for x in fk.pf)


def test_tc026_a_changed_version_only_loads(rig, fk, spy):
    # TC-026
    _, c = ready(rig)
    r = c.post("/launch", data=raw_form(c, revision="2.17.0", src="new"))
    assert r.status_code == 303 and query_of(r)["revision"] == "2.17.0" and spy.calls == []


def test_tc027_a_matching_pair_sends(rig, fk, spy):
    # TC-027
    _, c = ready(rig)
    r = c.post("/launch", data=raw_form(c, src="new"))
    assert r.status_code == 303 and r.headers["location"].startswith("/c/") and len(spy.calls) == 1
    assert spy.calls[0]["pipeline"] == "nf-core/ampliseq" and spy.calls[0]["revision"] == "2.18.0"


def test_tc028_version_list_reading(rig, fk):
    # TC-028
    fk.latest = latest(state="loading")
    _, c = ready(rig)
    t = c.get(NEW).text
    three = plain_text(step(t, 3))
    assert "… " + S4 in three and "<select name=\"revision\"" not in t and revision_controls(t) == [] and REFRESH in t


def test_tc029_version_list_failed(rig, fk, spy):
    # TC-029
    fk.latest = latest(state="error", why="代理連不到 GitHub，請檢查那台機器的網路 (x)", error="network")
    _, c = ready(rig)
    t = c.get(NEW).text
    assert "✗ " in plain_text(step(t, 3)) and revision_controls(t) == []
    r = c.post("/launch", data=raw_form(c, revision="", src="new"))
    assert r.status_code == 400 and "版本為必填" in r.text and spy.calls == []


def test_tc030_stale_cache_list(rig, fk):
    # TC-030
    fk.latest = latest(source="stale-cache", revision="2.17.0", releases=["2.17.0", "2.16.1"], why="x")
    _, c = ready(rig)
    t = c.get(NEW).text
    sel = select_html(t, "revision")
    assert re.findall(r'<option value="([^"]*)"', sel) == ["2.17.0", "2.16.1"] and selected_of(sel) == "2.17.0"
    assert "目前無法連線至 GitHub" in plain_text(step(t, 3))


def test_tc031_a_version_outside_the_list_stays(rig, fk):
    # TC-031
    _, c = ready(rig)
    sel = select_html(c.get(NEW + "&revision=2.10.0").text, "revision")
    assert "2.10.0" in re.findall(r'<option value="([^"]*)"', sel) and selected_of(sel) == "2.10.0"


def test_tc032_no_second_place_to_change_the_version(rig, fk):
    # TC-032
    _, c = ready(rig)
    t = c.get(NEW).text
    assert "套用此版本" not in t and "Apply this version" not in t and len(revision_controls(t)) == 1
    assert not re.search(r'name="(?:rev|version|revision_\w+)"', t) and revision_controls(step(t, 6)) == []
    assert "最新版本" not in t


# ---- US4: version list from the action --------------------------------------------------------------------------------------------------

TAGS = "".join("%040x\trefs/tags/%s\n" % (i + 1, t) for i, t in enumerate(
    ["v3.0.0", "2.18.0", "2.17.0", "dev", "master", "2.19.0-rc1", "abc", "2.9.0"]))


def test_tc033_releases_newest_first(world, clock):
    # TC-033
    lr(world)
    serve(world, clock, tags_result(TAGS))
    clock.t = T0 + 7
    out = lr(world)
    assert out["state"] == "ready" and out["releases"] == ["v3.0.0", "2.18.0", "2.17.0", "2.9.0"] and out["revision"] == out["releases"][0]
    assert set(out) == {"state", "pipeline", "revision", "source", "checked_at", "why", "error", "releases"}
    assert all(isinstance(x, str) for x in out["releases"])


def test_tc034_old_cache_and_new_cache(world, clock):
    # TC-034
    seed_cache(world, revision="2.18.0", checked_at=T0 - 100)
    out = lr(world)
    assert out["source"] == "cache" and out["releases"] == ["2.18.0"]
    cache_file(world).unlink()
    lr(world)
    serve(world, clock, tags_result(TAGS))
    first = lr(world)
    entry = json.loads(cache_file(world).read_text(encoding="utf-8"))["nf-core/ampliseq"]
    assert entry["releases"] == first["releases"]
    again = lr(world)
    assert again["source"] == "cache" and again["releases"] == first["releases"]


def test_tc035_stale_loading_error(world, clock):
    # TC-035
    from test_pipeline_files_action import network_down, tick
    cache_file(world).write_text(json.dumps({"nf-core/ampliseq": {"revision": "2.18.0", "checked_at": T0 - 90000, "releases": ["2.18.0", "2.17.0"]}}),
                                 encoding="utf-8")
    out = lr(world)
    assert out["state"] == "loading" and out["releases"] == []
    network_down(world, clock)
    out = lr(world)
    assert out["source"] == "stale-cache" and out["releases"] == ["2.18.0", "2.17.0"] and out["why"]
    cache_file(world).unlink()
    tick(world, clock, T0 + 120)
    out = lr(world)
    assert out["state"] == "loading" and out["releases"] == []
    network_down(world, clock)
    out = lr(world)
    assert out["state"] == "error" and out["releases"] == [] and out["revision"] is None


def test_tc036_an_old_shaped_answer_still_draws(rig, fk):
    # TC-036
    old = latest()
    old.pop("releases", None)
    fk.latest = old
    _, c = ready(rig)
    sel = select_html(c.get(NEW).text, "revision")
    assert re.findall(r'<option value="([^"]*)"', sel) == ["2.18.0"]


# ---- US5: the diagram under the pipeline -------------------------------------------------------------------------------------------------

def test_tc037_the_image_is_there(rig, fk):
    # TC-037
    _, c = ready(rig)
    three = step(c.get(SEL).text, 3)
    m = re.search(r'<img [^>]*>', three)
    assert m
    src = re.search(r'src="([^"]+)"', m.group(0)).group(1)
    assert html.unescape(src) == "/launch/diagram?" + urllib.parse.urlencode([("pipeline", "nf-core/ampliseq"), ("revision", "2.18.0")], safe="/")
    assert 'alt="nf-core/ampliseq 2.18.0 流程圖"' in m.group(0)
    en = re.search(r'<img [^>]*>', step(c.get(SEL + "&lang=en").text, 3)).group(0)
    assert 'alt="nf-core/ampliseq 2.18.0 workflow diagram"' in en


def test_tc038_the_image_is_after_the_pipeline_and_before_the_samples(rig, fk):
    # TC-038
    _, c = ready(rig)
    for url in (SEL, NEW):
        t = c.get(url).text
        three = step(t, 3)
        assert three.index("<img") > three.index('name="pipeline"') and t.index("<img") < t.index('data-step="4"')
        assert "<img" not in step(t, 4)


def test_tc039_no_open_link_and_no_file_line(rig, fk):
    # TC-039
    _, c = ready(rig)
    for lang in ("", "&lang=en"):
        t = c.get(SEL + lang).text
        for gone in ("開啟流程圖", "Open the workflow diagram", 'class="dlink"', "ampliseq_workflow.png", "736 KB", "流程圖檔"):
            assert gone not in t, gone


def test_tc040_step_three_stays_open(rig, fk):
    # TC-040
    _, c = ready(rig)
    t = c.get(SEL + "&run_name=my-run&samplesheet=samples.csv&ce_name=lab-a").text
    s = steps(t)
    assert s[3]["state"] == "done" and s[3]["open"] and "<img" in s[3]["html"]
    assert s[1]["state"] == "done" and s[4]["state"] == "done"      # the current step is a later one; the diagram is still open


def test_tc041_diagram_reading(rig, fk):
    # TC-041
    _, c = ready(rig)
    fk.image = good_image(state="loading", image=None)
    t = c.get(SEL).text
    assert "… " + S5 in plain_text(step(t, 3)) and "<img" not in t and REFRESH in t
    fk.image = good_image()
    fk.files = loading_files()
    t = c.get(SEL).text
    assert "… " + S5 in plain_text(step(t, 3)) and "<img" not in t and REFRESH in t


def test_tc042_no_diagram(rig, fk):
    # TC-042
    fk.files = good_files(diagram={"status": "none"})
    _, c = ready(rig)
    t = c.get(SEL).text
    assert S6 in plain_text(step(t, 3)) and "<img" not in t and steps(t)[3]["state"] == "done" and REFRESH not in t


@pytest.mark.parametrize("which", ["files", "diagram", "image"])
def test_tc043_diagram_failures(rig, fk, which):
    # TC-043
    if which == "files":
        fk.files = error_files()
    elif which == "diagram":
        fk.files = good_files(diagram={"status": "not_found", "message": "GitHub 上找不到流程圖 (the diagram was not found)"})
    else:
        fk.image = good_image(image={"status": "too_large", "message": "檔案太大，沒有讀 (the files are too large to read)"})
    _, c = ready(rig)
    t = c.get(SEL).text
    assert "✗ " in plain_text(step(t, 3)) and "<img" not in t and 'name="samplesheet"' in t


def test_tc044_nothing_before_a_pipeline_is_chosen(rig, fk):
    # TC-044
    _, c = ready(rig)
    for url in ("/launch", "/launch?src=new", "/launch?pipeline=nf-core/ampliseq&src=used"):
        t = c.get(url).text
        assert "<img" not in t and "/launch/diagram" not in t, url


def test_tc045_the_diagram_route_is_as_before(rig, fk):
    # TC-045
    _, c = ready(rig)
    r = c.get("/launch/diagram?pipeline=nf-core/ampliseq&revision=2.18.0")
    assert r.status_code == 200 and r.content == PNG and r.headers["content-type"] == "image/png"
    assert rig.w.web().get("/launch/diagram?pipeline=a&revision=b").status_code == 303


def test_tc046_image_uses_a_class(rig, fk):
    # TC-046
    from abf_platform import web_board
    _, c = ready(rig)
    t = c.get(SEL).text
    tag = re.search(r"<img [^>]*>", t).group(0)
    cls = re.search(r'class="([^"]+)"', tag).group(1)
    assert "style=" not in tag
    body = re.search(r"\.%s\{([^}]*)\}" % re.escape(cls.split()[0]), web_board.STYLE).group(1)
    assert "max-width:100%" in body and "height:auto" in body


# ---- US6: the image allowance of /launch only -------------------------------------------------------------------------------------------

BASE_CSP = "default-src 'none'; style-src %s; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"


def base_csp():
    from abf_platform import web_board
    return BASE_CSP % web_board.style_source()


def csp_ok(csp):
    assert "img-src 'self'" in csp
    assert csp.replace("img-src 'self'; ", "").replace(" img-src 'self'", "") == base_csp()


@pytest.mark.parametrize("url", [SEL, SEL + "&lang=en", NEW, "/launch"])
def test_tc047_launch_csp(rig, fk, url):
    # TC-047
    _, c = ready(rig)
    csp_ok(c.get(url).headers["content-security-policy"])


def test_tc048_blocked_post_csp(rig, fk):
    # TC-048
    _, c = ready(rig)
    r = c.post("/launch", data=raw_form(c, run_name=""))
    assert r.status_code == 400
    csp_ok(r.headers["content-security-policy"])


def test_tc049_other_pages_are_as_before(rig, fk):
    # TC-049
    from test_web_actions import run_of
    ann, c = ready(rig)
    rid = run_of(rig, ann)
    urls = ["/", "/settings", "/usage", "/c/" + rid, "/launch/diagram?pipeline=nf-core/ampliseq&revision=2.18.0"]
    for url in urls:
        r = c.get(url)
        if r.status_code == 404:
            continue
        csp = r.headers.get("content-security-policy", "")
        assert "img-src" not in csp, url
        if "/launch/diagram" not in url:
            assert csp == base_csp(), url
    login_page = rig.w.web().get("/login")
    assert "img-src" not in login_page.headers.get("content-security-policy", "")
    svg = b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"
    fk.image = good_image(image=dict(DIAGRAM, name="x.svg", type="image/svg+xml", data_b64=base64.b64encode(svg).decode()))
    assert "img-src" not in c.get(urls[-1]).headers["content-security-policy"]


def test_tc050_no_outside_address(rig, fk):
    # TC-050
    _, c = ready(rig)
    for url in (SEL, SEL + "&lang=en", NEW, "/launch"):
        r = c.get(url)
        csp = r.headers["content-security-policy"]
        assert not re.search(r"https?:|\*|data:", csp), csp
        for src in re.findall(r'\bsrc="([^"]*)"', r.text):
            assert src.startswith("/") and not src.startswith("//"), src


# ---- US7: words, states, limits ---------------------------------------------------------------------------------------------------------

def test_tc051_no_banned_word(rig, fk, monkeypatch):
    # TC-051
    pages = all_pages(rig, fk)
    for state, page in pages.items():
        assert banned_in(page) == [], state


def test_tc051_new_states_have_no_banned_word(rig, fk, monkeypatch):
    # TC-051
    ann, c = ready(rig)
    seen = {}
    patch_envs(monkeypatch, lambda envs: [])
    seen["no env"] = c.get(SEL).text
    patch_envs(monkeypatch, site_list(OTHER))
    seen["unregistered"] = c.get(SEL).text
    patch_envs(monkeypatch, lambda envs: envs)
    fk.latest = latest(state="loading")
    seen["versions loading"] = c.get(NEW).text
    fk.latest = latest(state="error", why="x (y)", error="network")
    seen["versions failed"] = c.get(NEW).text
    fk.latest = latest(releases=list(REL))
    fk.image = good_image(state="loading", image=None)
    seen["diagram loading"] = c.get(SEL).text
    fk.image = good_image()
    fk.files = good_files(diagram={"status": "none"})
    seen["no diagram"] = c.get(SEL).text
    fk.files = good_files()
    seen["used tab"] = c.get(SEL + "&src=used").text
    for state, page in seen.items():
        assert banned_in(page) == [], state


def test_tc052_the_six_sentences_verbatim(rig, fk, monkeypatch):
    # TC-052
    ann, c = ready(rig)
    patch_envs(monkeypatch, lambda envs: [])
    assert S1 in plain_text(step(c.get(SEL).text, 2))
    patch_envs(monkeypatch, site_list(OTHER))
    assert S2 in plain_text(step(c.get(SEL).text, 3))
    patch_envs(monkeypatch, lambda envs: envs)
    rig.user("bob")
    assert S3 in plain_text(step(login(rig, "bob").get(SEL).text, 4))
    fk.latest = latest(state="loading")
    assert S4 in plain_text(step(c.get(NEW).text, 3))
    fk.latest = latest(releases=list(REL))
    fk.image = good_image(state="loading", image=None)
    assert S5 in plain_text(step(c.get(SEL).text, 3))
    fk.image = good_image()
    fk.files = good_files(diagram={"status": "none"})
    assert S6 in plain_text(step(c.get(SEL).text, 3))


def test_tc053_english_for_every_new_state(rig, fk, monkeypatch):
    # TC-053
    ann, c = ready(rig)
    pages = []
    patch_envs(monkeypatch, lambda envs: [])
    pages.append(c.get(SEL + "&lang=en").text)
    patch_envs(monkeypatch, site_list(OTHER))
    pages.append(c.get(SEL + "&lang=en").text)
    patch_envs(monkeypatch, lambda envs: envs)
    for lat in (latest(state="loading"), latest(state="error", why="x (y)", error="network"), latest(source="stale-cache", releases=list(REL))):
        fk.latest = lat
        pages.append(c.get(NEW + "&lang=en").text)
    fk.latest = latest(releases=list(REL))
    for image in (good_image(state="loading", image=None), good_image(image={"status": "too_large", "message": "x (y)"})):
        fk.image = image
        pages.append(c.get(SEL + "&lang=en").text)
    fk.image = good_image()
    fk.files = good_files(diagram={"status": "none"})
    pages.append(c.get(SEL + "&lang=en").text)
    rig.user("bob")
    pages.append(login(rig, "bob").get(SEL + "&lang=en").text)
    for page in pages:
        assert no_cjk(main_of(page))


def test_tc054_every_state_has_a_symbol_and_words(rig, fk, monkeypatch):
    # TC-054
    ann, c = ready(rig)
    seen = []
    patch_envs(monkeypatch, lambda envs: [])
    seen.append((step(c.get(SEL).text, 2), S1, None))
    patch_envs(monkeypatch, site_list(OTHER))
    seen.append((step(c.get(SEL).text, 3), S2, None))
    patch_envs(monkeypatch, lambda envs: envs)
    fk.latest = latest(state="loading")
    seen.append((step(c.get(NEW).text, 3), S4, "…"))
    fk.latest = latest(state="error", why="x (y)", error="network")
    seen.append((step(c.get(NEW).text, 3), "x", "✗"))
    fk.latest = latest(releases=list(REL))
    fk.image = good_image(state="loading", image=None)
    seen.append((step(c.get(SEL).text, 3), S5, "…"))
    fk.image = good_image(image={"status": "too_large", "message": "檔案太大，沒有讀 (y)"})
    seen.append((step(c.get(SEL).text, 3), "檔案太大", "✗"))
    fk.image = good_image()
    fk.files = good_files(diagram={"status": "none"})
    seen.append((step(c.get(SEL).text, 3), S6, None))
    rig.user("bob")
    seen.append((step(login(rig, "bob").get(SEL).text, 4), S3, None))
    for part, sentence, sym in seen:
        line = next(m for m in re.findall(r"<p[^>]*>(.*?)</p>", part, re.S) if sentence in plain_text(m))
        text = plain_text(line)
        assert any(s in text for s in "✓✗…○—●"), text
        assert sym is None or sym in text


@pytest.mark.parametrize("lang", ["", "&lang=en"])
def test_tc055_no_script_no_style_attribute(rig, fk, lang):
    # TC-055
    for state, page in all_pages(rig, fk, lang).items():
        assert "<script" not in page and " style=" not in page and len(re.findall(r"<style\b", page)) == 1 and "<link" not in page, state


def test_tc056_phone_rules():
    # TC-056
    from abf_platform import web_board
    rules = dict((sel.strip(), body) for sel, body in re.findall(r"([^{}]*\bgdia\b[^{}]*)\{([^}]*)\}", web_board.STYLE))
    assert rules and all("max-width:100%" in b and "height:auto" in b for b in rules.values())
    for sel, body in re.findall(r"([^{}]*(?:gdia|gstep|gbody)[^{}]*)\{([^}]*)\}", web_board.STYLE):
        assert not re.search(r"(?<!max-)(?<!min-)width:\s*[4-9]\d\dpx|(?<!max-)(?<!min-)width:\s*\d{4,}px", body), (sel, body)
        assert "overflow-x" not in body


# ---- US8: send and errors ---------------------------------------------------------------------------------------------------------------

def test_tc059_missing_name(rig, fk, spy):
    # TC-059
    _, c = ready(rig)
    r = c.post("/launch", data=raw_form(c, run_name=""))
    assert r.status_code == 400 and "分析名稱為必填。" in r.text and steps(r.text)[1]["state"] == "current" and spy.calls == []


def test_tc060_current_step_follows_the_problem(rig, fk, monkeypatch, spy):
    # TC-060
    _, c = ready(rig)
    r = c.post("/launch", data=raw_form(c, ce_name="nope"))
    assert r.status_code == 400 and steps(r.text)[2]["state"] == "current"
    r = c.post("/launch", data=raw_form(c, revision="", shown_pipeline="nf-core/ampliseq", shown_revision=""))
    assert r.status_code == 400 and steps(r.text)[3]["state"] == "current"
    r = c.post("/launch", data=raw_form(c, samplesheet="nope.csv"))
    assert r.status_code == 400 and steps(r.text)[4]["state"] == "current"
    r = c.post("/launch", data=raw_form(c, params="a b c"))
    assert r.status_code == 400 and steps(r.text)[5]["state"] == "current"
    assert spy.calls == []

    async def refuse(*a, **kw):
        return {"ok": False, "message": "x (拒絕)"}
    monkeypatch.setattr(A(), "request_launch", refuse)
    r = c.post("/launch", data=raw_form(c))
    assert r.status_code == 400 and steps(r.text)[6]["state"] == "current"


def test_tc061_loading_comes_before_the_name_error(rig, fk, spy):
    # TC-061
    _, c = ready(rig)
    r = c.post("/launch", data=raw_form(c, run_name="", pipeline="nf-core/rnaseq", revision="3.14.0", shown_pipeline="nf-core/ampliseq"))
    assert r.status_code == 303 and spy.calls == []


def test_tc062_only_the_confirmation_queues(rig, fk, spy):
    # TC-062
    _, c = ready(rig)
    before = pending(rig)
    assert c.post("/launch", data=raw_form(c, revision="", shown_revision="", shown_pipeline="", src="new")).status_code == 303
    assert c.post("/launch", data=raw_form(c, run_name="")).status_code == 400
    assert spy.calls == [] and pending(rig) == before
    bad = raw_form(c)
    bad["csrf"] = "x" * 20
    assert c.post("/launch", data=bad).status_code == 403 and spy.calls == []
    r = c.post("/launch", data=raw_form(c))
    assert r.status_code == 303 and r.headers["location"].startswith("/c/") and len(spy.calls) == 1 and pending(rig) == before + 1


def test_tc063_everything_is_in_one_form(rig, fk):
    # TC-063
    _, c = ready(rig)
    t = c.get(NEW).text
    form = lform(main_of(t))
    for name in ("pipeline", "revision", "run_name", "ce_name", "samplesheet", "params_from", "params"):
        assert 'name="%s"' % name in form, name
    assert 'name="p.' in form and 'method="get"' not in t


def test_tc073_the_maintainers_order(rig, fk, spy):
    # TC-073
    _, c = ready(rig)
    t = c.get("/launch").text
    assert titles_of(t)[0] == "分析名稱" and steps(t)[1]["state"] == "current" and 'name="run_name"' in step(t, 1)
    data = raw_form(c, run_name="my-run", pipeline="ampliseq", revision="", shown_pipeline="", shown_revision="", src="new", ce_name="lab-a")
    r = c.post("/launch", data=data)
    assert r.status_code == 303
    page = c.get(r.headers["location"]).text
    assert selected_of(select_html(page, "revision")) == "2.18.0" and "<img" in step(page, 3)
    assert page.index("<img") < page.index('name="samplesheet"') < page.index('name="params"')
    hid = pairs_of(page)
    assert re.search(r'name="run_name" value="my-run"', page)
    sent = dict(raw_form(c), run_name="my-run", pipeline=hid["shown_pipeline"], revision=hid["shown_revision"], shown_pipeline=hid["shown_pipeline"],
                shown_revision=hid["shown_revision"], ce_name="lab-a", samplesheet="samples.csv", src="new")
    r = c.post("/launch", data=sent)
    assert r.status_code == 303 and r.headers["location"].startswith("/c/") and len(spy.calls) == 1
    call = spy.calls[0]
    assert (call["run_name"], call["ce_name"], call["pipeline"], call["revision"], call["samplesheet"]) == (
        "my-run", "lab-a", "nf-core/ampliseq", "2.18.0", "samples.csv")


# ---- out of scope -----------------------------------------------------------------------------------------------------------------------

def test_tc067_search_all_stays_closed(rig, fk):
    # TC-067
    _, c = ready(rig)
    t = c.get(NEW).text
    assert "搜尋全部 nf-core（尚未開放）" in plain_text(step(t, 3)) and 'type="search"' not in t


def test_tc066_nothing_connects_out(rig, fk):
    # TC-066 (the fk fixture blocks socket.connect; the whole file runs under it)
    import socket
    with pytest.raises(AssertionError):
        socket.socket().connect(("127.0.0.1", 9))
    _, c = ready(rig)
    assert "<script" not in c.get(NEW).text


def test_tc068_no_outside_picture_and_no_copy(rig, fk):
    # TC-068
    _, c = ready(rig)
    r = c.get(SEL)
    assert "img-src 'self'" in r.headers["content-security-policy"] and "http" not in r.headers["content-security-policy"]
    assert not re.findall(r'\bsrc="(?!/launch/diagram\?)[^"]*"', r.text)
