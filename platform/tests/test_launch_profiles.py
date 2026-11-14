# Nothing existing: tests of the new `profiles` argument of launch (Config profiles; a launch on a pipeline's own test data); no existing tool covers it.
"""launch-test-profile: `profiles` at the bundle (render_bundle), the pre-use check's profile list, the MCP tool, the screens, resume and relaunch.
Test cases are named in the comments (TC-nnn of specs/launch-test-profile/test-case.md)."""
import copy
import json
import re
import time

import pytest

from helpers import CHAT_ARGS, tool_json
from human_harness import World, form_answer
from profiles_harness import EIGHT, NAMES, args_of, ask, feed, install_eight, profiles_map, tables
from test_launch_bundle import SHEET, inputs, refused, render

BANNED_WORDS = re.compile(r"approve|confirm|confirmed_by|void|yes", re.I)
OVERWRITE_MARK = "// ---- the platform's settings below"


def exec_line(b):
    return [ln for ln in b["files"]["head.sh"].splitlines() if ln.startswith("exec nextflow")][0]


def make_test_bundle(profiles=("test",), **over):
    return render(samplesheet=None, profiles=list(profiles), params={}, **over)


# ======================================================================= the bundle (render_bundle) =============================================

@pytest.mark.parametrize("pipeline,revision", EIGHT)
def test_tc002_tc003_tc005_each_of_the_eight_has_no_sheet_and_no_input(pipeline, revision):
    # TC-002 TC-003 TC-005 TC-010
    b = make_test_bundle(pipeline=pipeline, revision=revision)
    assert b["profiles"] == ["test"] and b["samplesheet"] is None                       # TC-002
    assert sorted(b["files"]) == ["head.sh", "nextflow.config", "params.yaml"]
    assert "input" not in b["files"]["params.yaml"] and "outdir" in b["files"]["params.yaml"]      # TC-003
    assert " -profile test " in exec_line(b)                                            # TC-005


def test_tc004_the_overwrite_block_is_still_appended():
    # TC-004
    plain = render()["files"]["nextflow.config"]
    none = make_test_bundle()["files"]["nextflow.config"]
    assert none == plain and len(plain.splitlines()) > 1


def test_tc006_tc049_the_profile_goes_after_every_c_and_before_tower():
    # TC-006
    line = exec_line(make_test_bundle(profiles=["test", "singularity"]))
    assert line.index("-c nextflow.config") < line.index("-profile test,singularity") < line.index("-with-tower")


def test_tc006_the_site_config_c_stays():
    # TC-006: a pipeline of the site keeps its -c "$NFCORE_SITE_CONFIG" (the golden tests of test_launch_bundle.py pin the rest)
    from test_launch_bundle import site_ce
    ce = site_ce()
    line = exec_line(render(ce=ce, samplesheet=None, profiles=["test"], params={}))
    assert '-c "$NFCORE_SITE_CONFIG"' in line and "-c nextflow.config" in line
    assert line.index('-c "$NFCORE_SITE_CONFIG"') < line.index("-profile test") and line.index("-profile test") > line.index("-c nextflow.config")


@pytest.mark.parametrize("name", ["test_full", "test_hybrid", "test_zzz"])
def test_tc009_test_full_and_test_star_bring_input(name):
    # TC-009
    b = make_test_bundle(profiles=[name])
    assert b["samplesheet"] is None and (" -profile %s " % name) in exec_line(b) and "samplesheet.csv" not in b["files"]


def test_tc014_a_samplesheet_with_a_test_profile_wins():
    # TC-013 TC-014
    b = render(profiles=["test"])
    assert b["samplesheet"] == SHEET and "samplesheet.csv" in b["files"] and "input:" in b["files"]["params.yaml"]
    assert " -profile test " in exec_line(b)


def test_tc016_the_bundle_passes_a_list_on_as_it_is():
    # TC-016
    b = render(samplesheet=None, profiles=["test", "docker"], params={})
    assert " -profile test,docker " in exec_line(b)


def test_tc019_tc020_no_profiles_is_what_it_always_was():
    # TC-019 TC-020 (the golden files themselves are pinned by test_launch_bundle.py, which is untouched)
    plain = render()
    assert "profiles" not in plain and " -profile" not in plain["files"]["head.sh"]
    assert render(profiles=None) == plain and render(profiles=[]) == plain


def test_tc021_no_sheet_and_no_profile_is_still_refused():
    # TC-021
    refused("samplesheet|樣本", samplesheet=None)


def test_tc031_a_profile_that_brings_no_input_needs_a_samplesheet():
    # TC-031
    refused("samplesheet", samplesheet=None, profiles=["docker"])
    assert render(profiles=["docker"])["profiles"] == ["docker"]


@pytest.mark.parametrize("bad", ["", "te st", "test;rm", "-x", "a" * 65, ".x", "$(x)", "a,b", "a\nb", "ü", "a'b", 'a"b', "a|b", "a`b"])
def test_tc032_to_tc037_odd_names_are_refused(bad):
    # TC-032 TC-033 TC-034 TC-037
    refused("profiles", profiles=[bad])


def test_tc035_tc036_duplicates_and_nine_are_refused():
    # TC-035 TC-036
    refused("profiles.*重複|twice", profiles=["test", "test"])
    refused("profiles.*8", profiles=["p%d" % i for i in range(9)])
    assert len(render(profiles=["p%d" % i for i in range(8)])["profiles"]) == 8
    refused("profiles", profiles="test")
    refused("profiles", profiles=[1])


def test_the_clouds_refuse_profiles_in_the_bundle():
    # TC-051 TC-052 TC-053 TC-054 (bundle level; the MCP level, with the sentence and no writes, is test_non_site_module_and_other_platforms_refuse_profiles)
    from abf_station import launch
    for plat in (launch.GCB, launch.AWS, launch.AZURE, launch.K8S):
        ce = copy.deepcopy(inputs()["ce"])
        ce["platform"] = plat
        with pytest.raises(launch.BundleError, match="profiles"):
            launch.render_bundle(**inputs(ce=ce, profiles=["test"]))


def test_tc028_brings_input_rule():
    from abf_station import launch
    assert [launch.brings_input(n) for n in ("test", "test_full", "test_x", "tests", "testing", "docker", "mytest")] == \
        [True, True, True, False, False, False, False]


# ======================================================================= the pre-use check (station + jobs) =======================================

CONFIG = """manifest {
    name = 'nf-core/ampliseq'
    version = '2.18.0'
}
params { input = null  // profiles { fake { } } in a comment and in a param
}
profiles {
    debug { dumpHashes = true }
    conda { conda.enabled = true }
    // commented { x = 1 }
    docker { docker.enabled = true
        docker.userEmulation = true }
    "test_full" { includeConfig 'conf/test_full.config' }
    test      { includeConfig 'conf/test.config' }
    'weird name' { x = 1 }
}
"""


def test_tc022_the_preflight_reads_the_profile_names(tmp_path, monkeypatch):
    # TC-022: the station reads the installed pipeline's own nextflow.config; the key is "<pipeline> <revision>"
    from test_station_e2e import AMPLI, PF
    pf = PF(tmp_path / "pf", monkeypatch)
    pf.fake.make_site_pipeline("NFCORE_AMPLISEQ_HOME", "2.18.0", config=CONFIG)
    r = pf.result(sitePipelines=[dict(AMPLI)], modules=[], singularityLibraryDir=None) if False else pf.result(**{"sitePipelines": [dict(AMPLI)]})
    assert r["site_profiles"] == {"nf-core/ampliseq 2.18.0": ["debug", "conda", "docker", "test_full", "test"]}
    assert "site_profiles" not in [c["name"] for c in r["checks"]]


def test_tc022_no_block_and_no_site_pipeline_leave_the_old_shape(tmp_path, monkeypatch):
    # TC-022 (the empty case) and TC-030's source: no entries, no key; a config without profiles gives an empty list
    from test_station_e2e import AMPLI, PF
    pf = PF(tmp_path / "pf", monkeypatch)
    assert "site_profiles" not in pf.result()
    pf.fake.make_site_pipeline("NFCORE_AMPLISEQ_HOME", "2.18.0")
    assert pf.result(sitePipelines=[dict(AMPLI)])["site_profiles"] == {"nf-core/ampliseq 2.18.0": []}


def test_tc022_a_launch_gate_preflight_does_not_carry_it(tmp_path, monkeypatch):
    # TC-022: only the check the person asks for reads the lists (inventory); the gate of a launch is exactly as before
    from abf_station import handlers, rules
    from test_station_e2e import AMPLI, PF
    pf = PF(tmp_path / "pf", monkeypatch)
    pf.fake.make_site_pipeline("NFCORE_AMPLISEQ_HOME", "2.18.0", config=CONFIG)
    env = rules.clean_environment(pf.ce(sitePipelines=[dict(AMPLI)]))
    assert "site_profiles" not in handlers.preflight(env, pf.ctx)


def test_tc023_the_profile_lists_survive_the_cleaning_of_jobs(tmp_path, monkeypatch):
    # TC-023
    w = World(tmp_path, monkeypatch)
    w.user("ann")
    install_eight(w)
    feed(w, profiles_map())
    row = w.sql("SELECT result_json FROM jobs WHERE kind = 'preflight' ORDER BY id DESC LIMIT 1")[0][0]
    assert json.loads(row)["site_profiles"] == profiles_map()


def test_tc023_a_hostile_list_is_cleaned_not_stored(tmp_path, monkeypatch):
    # TC-023: a name that is not a plain profile name, or a key that is not "<pipeline> <revision>", is dropped
    w = World(tmp_path, monkeypatch)
    w.user("ann")
    feed(w, {"nf-core/ampliseq 2.18.0": ["test", "bad name", "$(x)", 3], "evil key": ["test"], "nf-core/rnaseq 3.26.0": "test"})
    got = json.loads(w.sql("SELECT result_json FROM jobs WHERE kind = 'preflight' ORDER BY id DESC LIMIT 1")[0][0])["site_profiles"]
    assert got == {"nf-core/ampliseq 2.18.0": ["test"]}


def test_ruling_a_the_latest_profile_list_is_not_cleaned_after_eight_days(tmp_path, monkeypatch):
    # TC-023 ruling A (11-04): the newest done pre-use check of an environment is kept, so a launch after 8 days still sees the profiles
    from abf_platform import jobs
    w = World(tmp_path, monkeypatch)
    w.ann = w.user("ann")
    install_eight(w)
    feed(w, profiles_map())
    later = time.time() + 8 * 86400
    jobs.enqueue_preflight(w.ip.state_db, "lab-a", lambda: later, offline_after=10 ** 9)         # any later job runs the cleaning
    kept = w.sql("SELECT result_json FROM jobs WHERE kind = 'preflight' AND state = 'done'")
    assert len(kept) == 1 and json.loads(kept[0][0])["site_profiles"] == profiles_map()
    out = ask(w, w.ann, ["test"])
    assert out["ok"] is True and out["state"] == "pending", out


def test_ruling_a_an_older_second_check_is_still_cleaned(tmp_path, monkeypatch):
    # TC-023 ruling A: only the newest done check is kept; the older one goes as before
    from abf_platform import jobs
    w = World(tmp_path, monkeypatch)
    w.user("ann")
    feed(w, profiles_map())
    feed(w, profiles_map())
    assert len(w.sql("SELECT id FROM jobs WHERE kind = 'preflight' AND state = 'done'")) >= 2
    jobs.enqueue_preflight(w.ip.state_db, "lab-a", lambda: time.time() + 8 * 86400, offline_after=10 ** 9)
    assert len(w.sql("SELECT id FROM jobs WHERE kind = 'preflight' AND state = 'done'")) == 1


# ======================================================================= the MCP tool =============================================================

@pytest.fixture
def w(tmp_path, monkeypatch):
    world = World(tmp_path, monkeypatch)
    world.ann = world.user("ann")
    install_eight(world)
    feed(world, profiles_map())
    return world


def pending(w, out):
    assert out["ok"] is True and out["state"] == "pending" and out["sent"] is False, out
    return json.loads(w.confirmations()[-1]["bundle_json"]), w.confirmations()[-1]["screen_text"]


def refused_out(w, out, *words):
    assert out["ok"] is False and out["sent"] is False and out["message"].startswith("未送出："), out
    for word in words:
        assert word in out["message"], (word, out["message"])
    return out["message"]


def test_tc001_tc002_tc003_tc004_a_test_launch_without_a_samplesheet_is_proposed(w):
    # TC-001 TC-002 TC-003 TC-004
    out = ask(w, w.ann, ["test"])
    b, _ = pending(w, out)
    assert b["profiles"] == ["test"] and b["samplesheet"] is None
    assert sorted(b["files"]) == ["head.sh", "nextflow.config", "params.yaml"]
    assert "input" not in b["files"]["params.yaml"] and "outdir" in b["files"]["params.yaml"]
    cfg = b["files"]["nextflow.config"]
    assert cfg.count("added by the platform") == 1 and "report.overwrite = true" in cfg and "timeline.overwrite = true" in cfg    # TC-004: the overwrite block, once
    assert w.jobs() == []


def test_tc005_tc006_the_head_line_of_the_proposal(w):
    # TC-005 TC-006
    b, _ = pending(w, ask(w, w.ann, ["test"]))
    line = exec_line(b)
    assert " -profile test " in line and 'NFCORE_SITE_CONFIG' in line
    assert line.index('NFCORE_SITE_CONFIG') < line.index("-profile test") < line.index("-with-tower")
    assert line.index("-c nextflow.config") < line.index("-profile test")


def test_tc007_tc008_the_screen_names_the_profile_and_the_test_data(w):
    # TC-007 TC-008
    out = ask(w, w.ann, ["test"])
    _, screen = pending(w, out)
    for text in (screen, out["summary"]):
        assert "Config profiles: test" in text
        assert "Samplesheet: from the pipeline's test profile" in text


@pytest.mark.parametrize("pipeline,revision", EIGHT)
def test_tc010_all_eight_pipelines_are_proposed_on_their_test_profile(w, pipeline, revision):
    # TC-010
    out = ask(w, w.ann, ["test"], pipeline=pipeline, revision=revision, run="run-" + pipeline.split("/")[1])
    b, _ = pending(w, out)
    assert b["pipeline"] == pipeline and b["revision"] == revision and b["profiles"] == ["test"]


@pytest.mark.parametrize("name", ["test_full", "test_custom"])
def test_tc009_test_full_and_test_star(w, name):
    # TC-009
    b, _ = pending(w, ask(w, w.ann, [name]))
    assert "samplesheet.csv" not in b["files"] and "input" not in b["files"]["params.yaml"]


def test_tc013_tc014_tc015_a_samplesheet_with_a_test_profile_keeps_the_sheet(w):
    # TC-013 TC-014 TC-015
    out = ask(w, w.ann, ["test"], sheet=w.sheet)
    b, screen = pending(w, out)
    assert "samplesheet.csv" in b["files"] and "input:" in b["files"]["params.yaml"] and b["samplesheet"]
    assert "Config profiles: test" in screen and "from the pipeline's test profile" not in screen and "Samplesheet" in screen


def test_tc016_a_name_on_the_list_goes_through_even_if_it_is_docker(w):
    # TC-016
    b, _ = pending(w, ask(w, w.ann, ["test", "docker"]))
    assert " -profile test,docker " in exec_line(b) and 'NFCORE_SITE_CONFIG' in exec_line(b)


def test_tc018_tc061_without_profiles_a_launch_is_what_it_was(w):
    # TC-018 TC-061
    out = ask(w, w.ann, None, sheet=w.sheet)
    b, screen = pending(w, out)
    assert "profiles" not in b and "samplesheet.csv" in b["files"] and "Config profiles" not in screen


def test_tc021_neither_a_sheet_nor_a_profile_is_refused_as_before(w):
    # TC-021
    before = tables(w)
    out = ask(w, w.ann, None)
    assert out["ok"] is False and out["sent"] is False and tables(w) == before


def test_tc026_tc027_an_unknown_profile_lists_the_ones_there_are_and_writes_nothing(w):
    # TC-026 TC-027
    before = tables(w)
    out = ask(w, w.ann, ["nope"])
    refused_out(w, out, "nope", "test", "test_full")
    assert tables(w) == before


def test_tc028_tc029_no_record_of_profiles_refuses_and_says_to_run_the_check(tmp_path, monkeypatch):
    # TC-028 TC-029
    w = World(tmp_path, monkeypatch)
    ann = w.user("ann")
    install_eight(w)
    before = tables(w)
    out = ask(w, ann, ["test"])
    refused_out(w, out, "檢查")
    assert tables(w) == before


def test_tc030_a_check_from_before_profiles_is_no_record(tmp_path, monkeypatch):
    # TC-030
    w = World(tmp_path, monkeypatch)
    ann = w.user("ann")
    install_eight(w)
    feed(w, None)
    before = tables(w)
    out = ask(w, ann, ["test"])
    refused_out(w, out, "檢查")
    assert tables(w) == before


def test_tc031_a_profile_without_data_needs_a_samplesheet(w):
    # TC-031
    before = tables(w)
    out = ask(w, w.ann, ["docker"])
    refused_out(w, out)
    assert "samplesheet" in out["message"].lower() or "樣本表" in out["message"]
    assert tables(w) == before


@pytest.mark.parametrize("bad", ["", "te st", "test;rm", "-x", "a" * 65])
def test_tc032_to_tc037_bad_names_are_refused_with_nothing_written(w, bad):
    # TC-032 TC-033 TC-034 TC-037
    before = tables(w)
    refused_out(w, ask(w, w.ann, [bad]))
    assert tables(w) == before


def test_tc035_tc036_duplicates_and_nine_names(w):
    # TC-035 TC-036
    before = tables(w)
    refused_out(w, ask(w, w.ann, ["test", "test"]))
    refused_out(w, ask(w, w.ann, ["a%d" % i for i in range(9)]), "8")
    assert tables(w) == before


def test_tc038_two_sheets_are_refused_with_the_old_sentence_before_profiles(w):
    # TC-038
    both = args_of(["test"], w.sheet, samplesheet_text="sample,fastq_1\ns,/x\n")
    out = tool_json(w.call("launch", both, caller=w.ann))
    assert out["ok"] is False and "只能給一個" in out["message"]


def test_tc039_the_refusals_are_plain_sentences(w):
    # TC-039
    for profs in (["nope"], ["docker"], [""], ["test", "test"]):
        msg = ask(w, w.ann, profs)["message"]
        assert msg.startswith("未送出：") and not re.search(r"Traceback|SELECT |\.py|/home/|File \"", msg), msg


def test_tc040_a_proposal_changes_nothing_that_runs(w):
    # TC-040
    out = ask(w, w.ann, ["test"])
    assert out["sent"] is False
    assert w.counts() == (0, 1, 0)
    assert w.sql("SELECT COUNT(*) FROM launches")[0][0] == 0 and w.jobs() == []


def test_tc050_a_pipeline_that_is_not_installed_on_the_site_refuses(w):
    # TC-050
    before = tables(w)
    out = ask(w, w.ann, ["test"], pipeline="nf-core/fetchngs", revision="1.12.0")
    refused_out(w, out)
    assert tables(w) == before


def test_tc055_no_parameter_can_say_yes(w):
    # TC-055 (the property names of every tool; the same check as test_http_site_samplesheet's test_tc048)
    tools, _ = w.mcp([])
    launch = [t for t in tools if t.name == "launch"][0]
    props = set(launch.input_schema["properties"])
    assert "profiles" in props
    assert not [p for p in props - CHAT_ARGS if re.search(r"confirm|approve|yes|send|force|skip|accept|送出|void", p)]
    assert launch.input_schema["required"] == ["pipeline", "revision", "run_name"]


def test_tc017_tc056_tc057_profiles_is_an_optional_list_with_a_described_example(w):
    # TC-017 TC-056 TC-057
    tools, _ = w.mcp([])
    launch = [t for t in tools if t.name == "launch"][0]
    props = launch.input_schema["properties"]
    assert "samplesheet_text" in props and "profiles" in props and "profiles" not in launch.input_schema["required"]
    p = props["profiles"]
    assert json.dumps(p).count('"array"') >= 1 and "string" in json.dumps(p)
    assert '["test"]' in p["description"] and not BANNED_WORDS.search(p["description"])
    assert not BANNED_WORDS.search(launch.description.replace("answers", ""))
    assert "description" in props["params"]


def test_tc058_the_description_is_short_and_says_what_to_do(w):
    # TC-058: about 600 characters
    tools, _ = w.mcp([])
    d = [t for t in tools if t.name == "launch"][0].description
    assert len(d) <= 600, len(d)
    for must in ("does NOT start", "resume or relaunch", "same arguments", "profiles", "Or name a dataset of yours (dataset, optionally dataset_version): its samplesheet is used."):
        assert must in d, must


def test_tc059_the_tools_are_the_same(w):
    # TC-059
    tools, _ = w.mcp([])
    assert sorted(t.name for t in tools) == ["cancel", "delete_figure", "describe_module", "find_module", "forget", "get_compute_env", "get_pipeline", "get_run", "get_validation",
                                              "launch", "launch_pipeline", "list_agents", "list_compute_envs", "list_figures", "list_pipelines", "list_runs", "list_site_files",
                                              "list_used_pipelines", "my_usage", "pack_figures", "publish_figure", "read_run_file", "read_task_log", "relaunch", "resume", "run_outputs"]


def test_tc070_launch_pipeline_exists_and_takes_no_profiles(w):
    # TC-070 (ruling B, 11-04): launch_pipeline is there, and neither it nor the action behind it can carry profiles
    import inspect
    from abf_platform import actions
    tools, _ = w.mcp([])
    tool = [t for t in tools if t.name == "launch_pipeline"][0]
    assert "profiles" not in tool.input_schema["properties"]
    assert "profiles" not in inspect.signature(actions.request_pipeline_launch).parameters


def test_tc067_the_pipeline_launch_tool_gets_no_profiles(w):
    # TC-067: the request for a pipeline of the person's own does not take profiles
    from abf_platform import actions
    import inspect
    assert "profiles" not in inspect.signature(actions.request_pipeline_launch).parameters


# ---- the confirmation page and the person's answer ------------------------------------------------------------------------------------------

def test_tc024_the_confirmation_page_shows_a_launch_without_a_samplesheet(w):
    # TC-024
    out = ask(w, w.ann, ["test"])
    client = w.web()
    assert w.login(client, "ann").status_code in (200, 303)
    page = client.get("/c/" + out["id"])
    assert page.status_code == 200, page.text
    assert "Config profiles" in page.text and "test profile" in page.text


def test_tc024_the_summary_never_says_zero_samples(w):
    # TC-024 (fix round: the plain summary at the top of the confirmation page; web.py stays untouched by TC-069, so the
    # profile name is asserted in the facts and in the full page, not as a label in the plain block)
    import re
    from abf_platform import actions
    out = ask(w, w.ann, ["test"])
    facts = actions.request_facts(w.ip.state_db, out["id"])
    assert "samples" not in facts and facts["profiles"] == "test", facts
    client = w.web()
    assert w.login(client, "ann").status_code in (200, 303)
    page = client.get("/c/" + out["id"]).text
    block = re.search(r'<dl class="fields plain">(.*?)</dl>', page, re.S).group(1)
    assert "樣本數" not in block and "<dd>0</dd>" not in block, block
    assert "Config profiles" in page and "test profile" in page   # the full content names them; the plain block has no label for them (web.py untouched)


def test_tc024_the_form_answer_sends_the_test_launch(w):
    # TC-024 TC-001: a client with a form: the person presses send, and the launch job is queued with the same bundle
    out = ask(w, w.ann, ["test"], answer=form_answer())
    assert out["sent"] is True, out
    jobs = w.jobs("launch_nextflow")
    assert len(jobs) == 1
    sent = json.loads(jobs[0]["args_json"])["bundle"]
    assert sent["profiles"] == ["test"] and "samplesheet.csv" not in sent["files"]


# ======================================================================= the agent (station) ======================================================

def test_tc025_the_agent_rebuilds_and_accepts_a_test_launch(tmp_path):
    # TC-025
    import stat
    from station_harness import FakePlatform, FakeSite
    from test_station_fakeplatform import agent_on, wait_for
    from test_station_launch import ACCT, bundle_for, folder, job_of, run_job
    site = FakeSite(tmp_path / "s", account=ACCT, site_user="tester", destructive_log=True)
    (site.storage / "cache").mkdir()
    fake = FakePlatform()
    try:
        b = bundle_for(site, fake, samplesheet=None, profiles=["test"], params={})
        assert " -profile test " in exec_line(b)
        with agent_on(fake, site, tmp_path, name="agent-f"):
            wait_for(lambda: fake.count("hello"))
            res = run_job(fake, job_of(b))
        assert res["state"] == "done", res
        f = folder(site)
        assert sorted(p.name for p in f.iterdir()) == ["head.sh", "nextflow.config", "params.yaml", "tower.token"]
        assert (f / "head.sh").read_bytes() == b["files"]["head.sh"].encode("utf-8")
        assert " -profile test " in (f / "head.sh").read_text()
        assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in f.iterdir())
    finally:
        fake.stop()


def test_tc025_a_changed_profile_in_the_bundle_is_not_the_confirmed_one(tmp_path):
    # TC-025: the agent rebuilds from the bundle's own fields; a head.sh that does not say the profiles the bundle names is refused
    from station_harness import FakePlatform, FakeSite
    from test_station_fakeplatform import agent_on, wait_for
    from test_station_launch import ACCT, bundle_for, job_of, nothing_happened, run_job
    site = FakeSite(tmp_path / "s", account=ACCT, site_user="tester", destructive_log=True)
    (site.storage / "cache").mkdir()
    fake = FakePlatform()
    try:
        b = bundle_for(site, fake, samplesheet=None, profiles=["test"], params={})
        b["files"]["head.sh"] = b["files"]["head.sh"].replace(" -profile test ", " -profile test,evil ")
        with agent_on(fake, site, tmp_path, name="agent-f"):
            wait_for(lambda: fake.count("hello"))
            assert run_job(fake, job_of(b))["state"] == "refused"
        nothing_happened(site)
    finally:
        fake.stop()


# ======================================================================= resume and relaunch ======================================================

def first_with_profiles(rig, run="run-one"):
    from abf_launch import build
    from abf_platform import actions
    install_eight(rig.w)
    ce, bundle = build.prepare_launch(rig.state, ce="lab-a", pipeline="nf-core/ampliseq", revision="2.18.0", run_name=run, samplesheet=None,
                                      params={}, profiles=["test"])
    _, job_id = actions.launch(rig.state, ce, bundle, confirmed_by=actions.TERMINAL, caller=None)
    rig.hand_over(job_id, run)
    rig.set_run(run, "failed")
    return bundle


@pytest.fixture
def rig(tmp_path, monkeypatch):
    from resume_harness import Rig
    return Rig(tmp_path, monkeypatch)


def test_tc041_tc042_tc046_a_relaunch_reproduces_the_test_launch(rig):
    # TC-041 TC-042 TC-046
    from abf_launch import build
    first = first_with_profiles(rig)
    assert first["profiles"] == ["test"]
    stored = json.loads(rig.w.sql("SELECT bundle_json FROM confirmations ORDER BY created_at DESC LIMIT 1")[0][0]) if rig.w.sql("SELECT 1 FROM confirmations") else first
    assert stored["profiles"] == ["test"]
    import asyncio
    from abf_platform import actions
    ann = rig.w.user("ann")
    out = asyncio.run(actions.request_relaunch(rig.state, run_name="run-one", caller=ann, person=None, remote=False, index_path=rig.index))
    assert out["ok"] is True, out
    row = rig.w.confirmations()[-1]
    b = json.loads(row["bundle_json"])
    assert b["profiles"] == ["test"] and b["samplesheet"] is None and "samplesheet.csv" not in b["files"]
    assert exec_line(b).replace(b["run_name"], "R") == exec_line(first).replace(first["run_name"], "R")
    assert "Config profiles: test" in row["screen_text"] and "Samplesheet: from the pipeline's test profile" in row["screen_text"]   # TC-047 TC-048


def test_tc045_tc047_tc048_a_resume_reproduces_the_test_launch(rig):
    # TC-045 TC-047 TC-048
    import asyncio
    from abf_platform import actions
    first_with_profiles(rig)
    ann = rig.w.user("ann")      # a person who can be sent to the page that asks (the stdio caller of the harness has nobody to ask)
    out = asyncio.run(actions.request_resume(rig.state, run_name="run-one", caller=ann, person=None, remote=False, index_path=rig.index))
    assert out["ok"] is True, out
    row = rig.w.confirmations()[-1]
    b = json.loads(row["bundle_json"])
    assert b["resume"]["origin"]["profiles"] == ["test"]      # the resume bundle keeps the origin verbatim; the head line below is rebuilt from it
    heads = [t for n, t in b["files"].items() if n.startswith("head-")]
    assert heads and " -profile test " in heads[0] and "-resume" in heads[0]
    line = [ln for ln in heads[0].splitlines() if ln.startswith("exec nextflow")][0]
    assert line.index("-c nextflow.config") < line.index("-profile test") < line.index("-with-tower")       # TC-049
    assert "Config profiles: test" in row["screen_text"] and "Samplesheet: from the pipeline's test profile" in row["screen_text"]


def test_tc043_tc044_an_old_bundle_without_profiles_rebuilds_as_before(tmp_path):
    # TC-043 TC-044: a bundle from before `profiles` existed reads it as none
    from abf_station import launch
    from station_harness import FakePlatform, FakeSite
    from resume_harness import SESSION, relaunch_bundle, resume_bundle
    from test_station_launch import ACCT
    site = FakeSite(tmp_path / "s", account=ACCT, site_user="tester")
    fake = FakePlatform()
    try:
        origin, rb = resume_bundle(site, fake)
        assert "profiles" not in origin and " -profile" not in "".join(rb["files"].values())
        again = launch.render_resume_bundle(origin=dict(origin), run_name="run-a-a2", attempt=2, session_id=SESSION, of_run="run-a", of_slurm_job_id=4242)
        assert again == rb
    finally:
        fake.stop()


def test_tc043_the_old_relaunch_path_renders_the_same_bytes(rig):
    # TC-043: a first launch without profiles, relaunched: no profile in anything
    import asyncio
    from abf_platform import actions
    rig.first()
    ann = rig.w.user("ann")
    out = asyncio.run(actions.request_relaunch(rig.state, run_name="run-one", caller=ann, person=None, remote=False, index_path=rig.index))
    assert out["ok"] is True, out
    b = json.loads(rig.w.confirmations()[-1]["bundle_json"])
    assert "profiles" not in b and " -profile" not in b["files"]["head.sh"] and "samplesheet.csv" in b["files"]
    assert "Config profiles" not in rig.w.confirmations()[-1]["screen_text"]



# ======================================================================= added in the fix round ====================================================

def sbatch_calls(script):
    """Real calls to sbatch (a line that runs it), not the #SBATCH directive lines."""
    return [ln for ln in script.splitlines() if re.search(r"\bsbatch\b", ln) and not ln.startswith("#")]


def test_tc077_umask_stays_before_the_only_sbatch_with_profiles():
    # TC-077: the head script of a test-profile launch (the local way and the site's way): umask 077 comes first, one nextflow run
    from test_launch_bundle import site_ce
    for over in ({}, {"ce": site_ce()}):
        h = render(samplesheet=None, profiles=["test"], params={}, **over)["files"]["head.sh"]
        lines = h.splitlines()
        assert lines.count("umask 077") == 1
        calls = sbatch_calls(h)
        assert len(calls) <= 1, calls
        if calls:
            assert lines.index("umask 077") < lines.index(calls[0])
        assert lines.index("umask 077") < [i for i, ln in enumerate(lines) if ln.startswith("exec nextflow")][0]
        assert h.count("nextflow run") == 1


def test_tc078_a_site_pipeline_with_profiles_gets_no_r_and_nothing_else_changes():
    # TC-078: PITFALLS 52/53: a local-path (site home) pipeline must not get -r because of -profile; everything but -profile is as before
    from test_launch_bundle import site_ce
    ce = site_ce()
    plain = render(ce=ce, profiles=[])["files"]["head.sh"]
    with_p = render(ce=ce, profiles=["test"])["files"]["head.sh"]
    assert " -r " not in with_p and '"$NFCORE_AMPLISEQ_HOME"' in with_p
    assert with_p.replace(" -profile test", "") == plain
    assert with_p.splitlines()[:-1] == plain.splitlines()[:-1]          # every line before the exec line: modules, umask, image cache


def test_tc068_resume_and_relaunch_tools_have_no_profiles(w):
    # TC-068
    tools, _ = w.mcp([])
    by = {t.name: t for t in tools}
    for name in ("resume", "relaunch"):
        assert "profiles" not in json.dumps(by[name].input_schema), name
    assert "profiles" in by["launch"].input_schema["properties"]


def test_tc069_the_web_launch_page_has_no_test_data_option(w):
    # TC-069: this slice is MCP and below; the web page (a later slice, web-launch-test-profile) is not touched
    import inspect
    from abf_platform import web, web_board, web_launch
    client = w.web()
    assert w.login(client, "ann").status_code in (200, 303)
    for url in ("/launch", "/launch?pipeline=nf-core/ampliseq&revision=2.18.0"):
        page = client.get(url)
        assert page.status_code == 200
        assert "Use the pipeline's test data" not in page.text and "profile test" not in page.text
    for mod in (web, web_board, web_launch):
        assert "(profile test)" not in inspect.getsource(mod)
    # The git-diff half of TC-069 only held while launch-test-profile was the branch under test; once merged, later PRs legitimately change web.py (012b-2), so only the source/page asserts above remain.


def ann_proposes_and_bob_exists(w):
    bob = w.user("bob")
    out = ask(w, w.ann, ["test"])
    assert out["ok"] is True and out["state"] == "pending"
    return bob, out["id"]


def test_tc073_another_person_cannot_read_a_test_profile_request(w):
    # TC-073: the request has no samplesheet (confirm.py's new branch); bob's own login sees nothing of it
    bob, rid = ann_proposes_and_bob_exists(w)
    c = w.web()
    assert w.login(c, "bob").status_code in (200, 303)
    page = c.get("/c/" + rid)
    assert "非您的申請" in page.text and 'name="csrf"' not in page.text
    for leak in ("nf-core/ampliseq", "run-one", "Config profiles", "test profile", "outdir"):
        assert leak not in page.text, leak


def test_tc074_another_person_cannot_confirm_a_test_profile_request(w):
    # TC-074
    from human_harness import csrf_of
    bob, rid = ann_proposes_and_bob_exists(w)
    c = w.web()
    assert w.login(c, "bob").status_code in (200, 303)       # (the first web login makes the signing key, so the snapshot is taken after it)
    before = (tables(w), [dict(r) for r in w.confirmations()])
    for data in ({}, {"csrf": "x"}):
        assert c.post("/c/" + rid, data=data).status_code == 403
    assert w.jobs() == [] and tables(w) == before[0]
    assert [dict(r) for r in w.confirmations()] == before[1]
    assert [r["state"] for r in w.confirmations() if r["id"] == rid] == ["pending"]
    a = w.web()                                   # the owner can still press, and exactly one job is queued
    assert w.login(a, "ann").status_code in (200, 303)
    assert a.post("/c/" + rid, data={"csrf": csrf_of(a.get("/c/" + rid).text)}).status_code == 200
    assert len(w.jobs("launch_nextflow")) == 1


def test_tc072_a_proposal_calls_no_write_or_send_function(w, monkeypatch):
    # TC-072: one launch call without any answer; the functions that queue a job or approve are counted and must be zero
    from abf_platform import actions, confirm, jobs
    calls = []
    for mod, name in ((actions, "launch"), (jobs, "enqueue_launch"), (confirm, "approve")):
        monkeypatch.setattr(mod, name, lambda *a, _n=name, **k: calls.append(_n))
    out = ask(w, w.ann, ["test"])
    assert out["sent"] is False and out["state"] == "pending"
    assert calls == [] and w.jobs() == [] and w.sql("SELECT COUNT(*) FROM launches")[0][0] == 0


def test_tc076_no_secret_reaches_the_params_file_the_refusals_or_the_log(w, monkeypatch, caplog):
    # TC-076: canaries in the process environment; none is in params.yaml, a refusal, a screen, the log, or any file under the data folder
    from pathlib import Path
    canaries = {"NXF_TOWER_TOKEN": "CANARY_tower_a1", "API_TOKEN": "CANARY_api_b2", "AWS_SECRET_ACCESS_KEY": "CANARY_aws_c3", "GITHUB_TOKEN": "CANARY_gh_d4"}
    for k, v in canaries.items():
        monkeypatch.setenv(k, v)
    caplog.set_level(0)
    out = ask(w, w.ann, ["test"])
    b, screen = pending(w, out)
    refusals = [ask(w, w.ann, ["nope"], run="run-two"), ask(w, w.ann, [], run="run-three")]
    assert all(r["ok"] is False for r in refusals)
    texts = [b["files"]["params.yaml"], screen, json.dumps(out), json.dumps(refusals), caplog.text]
    root = Path(w.ip.state_db).parent
    texts += [p.read_bytes().decode("latin-1") for p in root.rglob("*") if p.is_file() and not p.name.endswith(("-wal", "-shm"))]
    for v in canaries.values():
        assert not [i for i, t in enumerate(texts) if v in t], v
    assert set(re.findall(r"^([A-Za-z_]+):", b["files"]["params.yaml"], re.M)) <= {"outdir", "input"}


@pytest.mark.parametrize("which", ["GCB", "AWS", "AZURE", "K8S"])
def test_non_site_module_and_other_platforms_refuse_profiles(w, which):
    # TC-051 TC-052 TC-053 TC-054: through the MCP launch on a cloud environment: a plain "未送出：" sentence, and nothing written
    import sqlite3
    from abf_station import launch
    con = sqlite3.connect(str(w.ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET platform = ? WHERE name = 'lab-a'", (getattr(launch, which),))
    con.close()
    before = tables(w)
    out = ask(w, w.ann, ["test"])
    msg = refused_out(w, out, "profiles: 這種環境還不支援 Config profiles")
    assert not re.search(r"Traceback|SELECT |\.py|/home/|File \"", msg), msg
    assert tables(w) == before and w.jobs() == [] and w.confirmations() == []
