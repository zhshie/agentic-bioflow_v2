# Nothing existing: tests of the agent reading nf-core's own public list of all pipelines and of the action that turns it into a search list; no earlier test knows this list.
"""nfcore-catalogue: the pipeline_files job gets a fifth public file, https://nf-co.re/pipelines.json, and the action layer gets
`nfcore_catalogue` for the guided launch page's "search every nf-core pipeline". Three sections: the agent (CS), the queue and the
cleaning (CQ), the action (CA). Test cases are named in the comments (TC-001 ...). The one place that connects is
`pipeline_files.OPEN`; an autouse guard makes any test that forgets to replace it fail instead of reaching the internet."""
import asyncio
import inspect
import json
import re
import sqlite3
from pathlib import Path

import pytest

from helpers import Clock, PLATFORM_DIR, REPO_ROOT
from test_station_pipeline_files import Net, ctx, job  # noqa: F401  (ctx is a fixture)

from abf_station import handlers, pipeline_files

T0 = 1_800_000_000.0
STATION = PLATFORM_DIR / "abf_station"
FIXTURE = PLATFORM_DIR / "tests" / "fixtures" / "catalogue" / "pipelines-small.json"
URL = "https://nf-co.re/pipelines.json"
NINE = ["preflight", "list_site_files", "launch_nextflow", "cancel_run", "fetch_run_records", "read_task_log", "clean_work", "put_upload",
        "pipeline_files"]
CAT_KEYS = {"state", "checked_at", "count", "error", "reason", "pipelines"}
NOT_FOR_USERS = re.compile(r"Traceback|sqlite|args_json|deadline_at|result_json|SELECT")
NETWORK_REASON = "代理連不到 nf-co.re，請檢查那台機器的網路 (the agent could not reach nf-co.re; check that machine's network)"
ENTRY_KEYS = {"name", "description", "archived", "tags"}


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch):
    def forbidden(url, headers, timeout, limit):
        raise AssertionError("a test reached the real network: %s" % url)
    monkeypatch.setattr(pipeline_files, "OPEN", forbidden)


@pytest.fixture
def net(monkeypatch):
    n = Net()
    monkeypatch.setattr(pipeline_files, "OPEN", n)
    return n


def cat_job(**over):
    args = {"repo": None, "revision": None, "parts": ["catalogue"]}
    args.update(over)
    return {"id": 1, "kind": "pipeline_files", "args": args}


def fixture_data():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def body_of(entries):
    return json.dumps({"remote_workflows": entries}).encode()


def wf(name, **over):
    out = {"name": name, "description": "d " + str(name), "archived": False, "releases": [{"tag_name": "1.0.0"}]}
    out.update(over)
    return out


def read(ctx, net, body, status=200, headers=None):
    net.routes[URL] = (status, headers or {"Content-Type": "application/json"}, body)
    return handlers.handle(cat_job(), ctx)


def part_of(ctx, net, body, **kw):
    state, out = read(ctx, net, body, **kw)
    assert state == "done" and out["ok"] is True, (state, out)
    return out["parts"]["catalogue"]


# ---- the agent (CS) ------------------------------------------------------------------------------------------------

def test_tc001_the_kinds_and_arguments_do_not_change():
    # TC-001
    assert list(handlers.JOB_KINDS) == NINE
    assert handlers.ARG_KEYS["pipeline_files"] == {"repo", "revision", "parts"}


def test_tc002_catalogue_is_the_last_part():
    # TC-002
    from abf_platform import jobs
    assert pipeline_files.PARTS[-1] == "catalogue"
    assert pipeline_files.PARTS[:5] == ("schema", "schema_input", "diagram", "image", "tags")
    assert tuple(jobs.PF_PARTS) == tuple(pipeline_files.PARTS)


def test_tc003_the_fourth_host_is_nf_co_re():
    # TC-003
    assert pipeline_files.allowed(URL) is True
    assert pipeline_files.HOSTS == ("github.com", "raw.githubusercontent.com", "api.github.com", "nf-co.re")


def test_tc004_only_the_exact_host_is_allowed(net):
    # TC-004
    for url in ("http://nf-co.re/pipelines.json", "https://nf-co.re.evil.com/pipelines.json", "https://evil.com/nf-co.re/pipelines.json",
                "https://nf-co.re@evil.com/x", "https://nf-co.re:8443/pipelines.json", "https://www.nf-co.re/pipelines.json"):
        assert pipeline_files.allowed(url) is False, url
    assert net.calls == []


def test_tc005_one_plain_get_of_the_one_address(ctx, net):
    # TC-005
    part_of(ctx, net, FIXTURE.read_bytes())
    assert len(net.calls) == 1
    call = net.calls[0]
    assert call["url"] == URL and call["limit"] == 8000000 and call["headers"]["Accept"] == "application/json"
    assert not ({k.lower() for k in call["headers"]} & {"authorization", "cookie"})


def test_tc006_tc007_tc008_the_cleaned_list(ctx, net):
    # TC-006, TC-007, TC-008
    state, out = read(ctx, net, FIXTURE.read_bytes())
    assert state == "done" and out["ok"] is True and out["repo"] is None and out["revision"] is None
    part = out["parts"]["catalogue"]
    assert part["status"] == "ok" and set(out["parts"]) == {"catalogue"}
    names = [p["name"] for p in part["pipelines"]]
    assert len(names) == 6 and names == sorted(names)
    assert all(set(p) == ENTRY_KEYS for p in part["pipelines"])
    by = {p["name"]: p for p in part["pipelines"]}
    assert by["ampliseq"]["tags"] == ["3.0.0", "2.18.0", "dev"] and by["ampliseq"]["archived"] is False
    assert by["ampliseq"]["description"] == "Amplicon sequencing analysis workflow using DADA2 and QIIME2"
    assert by["abotyper"]["tags"] == ["dev"]
    assert by["exoseq"]["archived"] is True and by["cellpainting"]["description"] == ""


def test_tc009_extra_keys_never_leave_the_agent(ctx, net):
    # TC-009
    text = json.dumps(read(ctx, net, FIXTURE.read_bytes())[1])
    for word in ("stargazers_count", "topics", "html_url", "tag_sha", "published_at", "full_name", "nextflow_version", "aaaaaaaaaaaaaaaaaaaa"):
        assert word not in text, word


def test_tc010_bad_names_are_skipped(ctx, net):
    # TC-010
    part = part_of(ctx, net, body_of([wf("good"), wf("../evil"), wf(5), wf("also-good")]))
    assert [p["name"] for p in part["pipelines"]] == ["also-good", "good"]


def test_tc011_missing_or_odd_fields_get_defaults(ctx, net):
    # TC-011
    a, b, c = wf("a"), wf("b"), wf("c", description=7)
    del a["releases"]
    b["releases"] = "x"
    part = part_of(ctx, net, body_of([a, b, c]))
    by = {p["name"]: p for p in part["pipelines"]}
    assert by["a"]["tags"] == [] and by["b"]["tags"] == [] and by["c"]["description"] == ""


@pytest.mark.parametrize("body", [b'{"remote_workflows": {}}', b"[]", b'"x"', b"\xff\xfe\x00", b'{"remote_workflows": []}',
                                  body_of([wf("../x"), wf(1)]), b"not json"])
def test_tc012_a_bad_whole_is_bad_response(ctx, net, body):
    # TC-012
    part = part_of(ctx, net, body)
    assert part["status"] == "bad_response" and "pipelines" not in part
    assert len(part["message"]) <= 300 and re.search(r"[一-鿿]", part["message"]) and re.search(r"[A-Za-z]{4}", part["message"])


def test_tc013_a_body_over_eight_megabytes_is_too_large(ctx, net):
    # TC-013
    part = part_of(ctx, net, b"x" * 8000001)
    assert part["status"] == "too_large" and "pipelines" not in part
    assert net.calls[0]["limit"] == 8000000


def test_tc014_more_than_a_thousand_entries_is_too_large(ctx, net):
    # TC-014
    part = part_of(ctx, net, body_of([wf("p%04d" % i) for i in range(1001)]))
    assert part["status"] == "too_large" and "pipelines" not in part
    ok = part_of(ctx, net, body_of([wf("p%04d" % i) for i in range(1000)]))
    assert ok["status"] == "ok" and len(ok["pipelines"]) == 1000


@pytest.mark.parametrize("status,headers,want", [(404, {}, "not_found"), (429, {}, "rate_limited"),
                                                 (403, {"X-RateLimit-Remaining": "0"}, "rate_limited"),
                                                 (500, {}, "bad_response"), (301, {"Location": "https://evil.com/x"}, "bad_response")])
def test_tc015_tc016_http_answers(ctx, net, status, headers, want):
    # TC-015, TC-016
    part = part_of(ctx, net, b"", status=status, headers=headers)
    assert part["status"] == want and "pipelines" not in part
    assert net.urls() == [URL]


def test_tc017_a_broken_connection_is_a_network_error(ctx, net):
    # TC-017
    net.routes[URL] = OSError("down")
    state, out = handlers.handle(cat_job(), ctx)
    assert state == "error" and out["ok"] is False and out["error"] == "network" and isinstance(out["message"], str)
    assert len(net.calls) == 1


def test_tc018_a_spent_budget_asks_nothing(ctx, net, monkeypatch):
    # TC-018
    ticks = iter([0.0, 1000.0, 1000.0, 1000.0])
    monkeypatch.setattr(pipeline_files, "CLOCK", lambda: next(ticks))
    state, out = handlers.handle(cat_job(), ctx)
    assert state == "error" and out["error"] == "network" and net.calls == []


def refused(ctx, net, j):
    state, out = handlers.handle(j, ctx)
    assert state == "refused" and out["ok"] is False and isinstance(out["message"], str), j
    assert net.calls == [], j


def test_tc019_catalogue_takes_no_repo_and_no_revision(ctx, net):
    # TC-019
    refused(ctx, net, job(["catalogue"]))
    refused(ctx, net, job(["catalogue"], repo=None))
    refused(ctx, net, job(["catalogue"], revision=None))


def test_tc020_catalogue_is_read_on_its_own(ctx, net):
    # TC-020
    refused(ctx, net, job(["catalogue", "schema"], repo=None, revision=None))
    refused(ctx, net, job(["catalogue", "tags"], repo=None, revision=None))
    refused(ctx, net, job(["catalogue", "catalogue"], repo=None, revision=None))


def test_tc021_no_repo_is_only_for_catalogue(ctx, net):
    # TC-021
    refused(ctx, net, job(["schema"], repo=None, revision=None))


def test_tc022_the_old_five_parts_never_touch_nf_co_re(ctx, net):
    # TC-022
    from test_station_pipeline_files import all_ok
    all_ok(net)
    state, out = handlers.handle(job(["schema", "schema_input", "diagram", "image", "tags"]), ctx)
    assert state == "done"
    assert len(net.calls) == 5 and not [u for u in net.urls() if "nf-co.re" in u]


def test_tc023_the_address_is_one_constant():
    # TC-023
    text = (STATION / "pipeline_files.py").read_text(encoding="utf-8")
    assert text.count("https://nf-co.re/pipelines.json") == 1
    assert [m for m in re.findall(r"nf-co\.re/(\S*)", text) if not m.startswith("pipelines.json")] == []


def test_tc024_the_guard_stops_a_test_that_forgot_the_stand_in(ctx):
    # TC-024
    with pytest.raises(AssertionError):
        pipeline_files.run_fetch(cat_job(), ctx)


def test_tc025_the_agent_does_not_pick_the_newest(ctx, net):
    # TC-025
    part = part_of(ctx, net, FIXTURE.read_bytes())
    by = {p["name"]: p for p in part["pipelines"]}
    assert by["abotyper"]["tags"] == ["dev"] and all("latest" not in p for p in part["pipelines"])


def test_tc108_tc109_the_reader_stays_read_only_and_alone():
    # TC-108, TC-109
    text = (STATION / "pipeline_files.py").read_text(encoding="utf-8")
    for word in ("open(", ".write(", "os.remove", "shutil", "subprocess", "socket", "ctx.site", "site.call", "Authorization", "sbatch", "rm -rf"):
        assert word not in text, word
    using = sorted(p.name for p in STATION.glob("*.py") if "urllib.request" in p.read_text(encoding="utf-8"))
    assert using == ["agent.py", "pipeline_files.py"]


# ---- the queue and the cleaning (CQ) ---------------------------------------------------------------------------------------

@pytest.fixture
def clock(monkeypatch):
    from abf_platform import status
    c = Clock(T0)
    monkeypatch.setattr(status, "now", c)
    return c


@pytest.fixture
def db(tmp_path, clock):
    from abf_platform import store
    path = tmp_path / "platform.db"
    store.connect_state(path).close()
    return path


def sql(db, text, args=()):
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        with con:
            return con.execute(text, args).fetchall()
    finally:
        con.close()


def add_user_env(db, agent, ce, owner, seen=T0):
    sql(db, "INSERT OR REPLACE INTO agents (name, version, first_seen_at, last_seen_at, owner_user_id) VALUES (?, '0.1', ?, ?, ?)",
        (agent, seen, seen, owner))
    sql(db, "INSERT INTO compute_envs (name, platform, agent, status, config_json, created_at, updated_at, owner_user_id) "
            "VALUES (?, 'slurm-platform', ?, 'available', '{}', 1, 1, ?)", (ce, agent, owner))


@pytest.fixture
def world(db):
    add_user_env(db, "a1", "ce1", 1)
    add_user_env(db, "a2", "ce2", 2)
    return db


def count_jobs(db):
    return sql(db, "SELECT COUNT(*) FROM jobs WHERE kind = 'pipeline_files'")[0][0]


def test_tc026_tc027_no_new_kind_and_no_migration(tmp_path, monkeypatch):
    # TC-026, TC-027
    from abf_platform import jobs, store
    con = store.connect_state(tmp_path / "x.db")
    text = con.execute("SELECT sql FROM sqlite_master WHERE name = 'jobs'").fetchone()[0]
    con.close()
    m = re.search(r"kind TEXT NOT NULL CHECK \(kind IN \(([^)]*)\)\)", text)
    assert re.findall(r"'([a-z_]+)'", m.group(1)) == NINE
    assert list(jobs.KINDS) == NINE
    assert store._jobs_kinds_current(text)
    seen = []
    monkeypatch.setattr(store, "_migration_step", lambda step: seen.append(step))
    store.connect_state(tmp_path / "x.db").close()
    assert seen == []


def test_tc028_no_confirmation_is_needed(world, clock):
    # TC-028
    from abf_platform import jobs
    assert jobs.CONFIRMED == {"launch_nextflow": "launch", "cancel_run": "cancel", "clean_work": "clean_work"}
    jid = jobs.enqueue_pipeline_files(world, None, None, ["catalogue"], clock=clock, caller_user_id=1)
    assert isinstance(jid, int)


def test_tc029_the_good_arguments():
    # TC-029
    from abf_platform import jobs
    assert jobs.pf_arguments(None, None, ["catalogue"]) == (None, None, ["catalogue"])


BAD = [("nf-core/ampliseq", None, ["catalogue"]), (None, "2.18.0", ["catalogue"]), (None, None, ["catalogue", "schema"]),
       (None, None, ["tags", "catalogue"]), (None, None, ["schema"]), (None, None, ["tags"]), (None, None, ["catalogue", "catalogue"])]


@pytest.mark.parametrize("repo,revision,parts", BAD)
def test_tc030_tc031_bad_arguments_are_refused_in_two_languages(repo, revision, parts):
    # TC-030, TC-031
    from abf_platform import jobs
    with pytest.raises(jobs.JobRefused) as e:
        jobs.pf_arguments(repo, revision, parts)
    text = str(e.value)
    assert re.search(r"[一-鿿]", text) and re.search(r"[A-Za-z]{4}", text) and "station" not in text


def test_tc032_tc033_tc034_the_queued_row_and_who_sees_it(world, clock):
    # TC-032, TC-033, TC-034
    from abf_platform import jobs
    jid = jobs.enqueue_pipeline_files(world, None, None, ["catalogue"], clock=clock, caller_user_id=1)
    row = sql(world, "SELECT * FROM jobs WHERE id = ?", (jid,))[0]
    assert row["kind"] == "pipeline_files" and row["confirmation_id"] is None and row["deadline_at"] == T0 + 90
    assert json.loads(row["args_json"]) == {"repo": None, "revision": None, "parts": ["catalogue"]}
    assert jobs.latest_pipeline_files(world, None, None, ["catalogue"], 1)["id"] == jid
    assert jobs.latest_pipeline_files(world, None, None, ["tags"], 1) is None
    assert jobs.latest_pipeline_files(world, "nf-core/ampliseq", None, ["tags"], 1) is None
    assert jobs.latest_pipeline_files(world, None, None, ["catalogue"], 2) is None


def good_entries():
    return [{"name": e["name"], "description": e["description"] or "", "archived": e["archived"],
             "tags": [r["tag_name"] for r in e["releases"]]} for e in fixture_data()["remote_workflows"]]


def cat_result(entries=None, **part):
    p = {"status": "ok", "pipelines": good_entries() if entries is None else entries}
    p.update(part)
    return {"ok": True, "repo": None, "revision": None, "parts": {"catalogue": p}, "message": "read 1 part(s)"}


def clean(result):
    from abf_platform import jobs
    return jobs.clean_result("pipeline_files", result)


def test_tc035_a_good_result_passes_unchanged():
    # TC-035
    out = clean(cat_result())
    assert out["parts"]["catalogue"] == {"status": "ok", "pipelines": good_entries()} and len(good_entries()) == 6
    assert out["revision"] is None and "repo" not in out


def test_tc036_only_four_keys_per_entry():
    # TC-036
    entries = good_entries()
    for e in entries:
        e.update(html_url="https://x", topics=["a"], stargazers_count=3, token="T")
    assert clean(cat_result(entries))["parts"]["catalogue"]["pipelines"] == good_entries()


def test_tc037_bad_names_are_dropped():
    # TC-037
    entries = good_entries() + [dict(good_entries()[0], name="../x"), dict(good_entries()[0], name=5)]
    no_name = dict(good_entries()[0])
    del no_name["name"]
    out = clean(cat_result(entries + [no_name]))["parts"]["catalogue"]["pipelines"]
    assert out == good_entries()


def test_tc038_tc039_description_and_archived():
    # TC-038, TC-039
    a, b, c = (dict(good_entries()[0], name=n) for n in ("aa", "bb", "cc"))
    a["description"] = "x" * 401
    b["description"] = 7
    c["archived"] = "yes"
    out = {e["name"]: e for e in clean(cat_result([a, b, c]))["parts"]["catalogue"]["pipelines"]}
    assert out["aa"]["description"] == "x" * 400 and out["bb"]["description"] == "" and out["cc"]["archived"] is False


def test_tc040_tags_are_filtered_and_capped():
    # TC-040
    a, b = dict(good_entries()[0], name="aa"), dict(good_entries()[0], name="bb")
    a["tags"] = ["1.0.0", 5, "../x", None, "dev"]
    b["tags"] = ["%d.0.0" % i for i in range(501)]
    out = {e["name"]: e for e in clean(cat_result([a, b]))["parts"]["catalogue"]["pipelines"]}
    assert out["aa"]["tags"] == ["1.0.0", "dev"] and len(out["bb"]["tags"]) == 500


def test_tc041_only_the_first_thousand_entries():
    # TC-041
    out = clean(cat_result([dict(good_entries()[0], name="p%04d" % i) for i in range(1001)]))["parts"]["catalogue"]["pipelines"]
    assert len(out) == 1000 and out[-1]["name"] == "p0999"


def test_tc042_not_a_list_or_nothing_left_is_bad_response():
    # TC-042
    assert clean(cat_result("x"))["parts"]["catalogue"] == {"status": "bad_response"}
    assert clean(cat_result([{"name": "../x"}]))["parts"]["catalogue"] == {"status": "bad_response"}


def test_tc043_a_failed_part_keeps_status_and_message_only():
    # TC-043
    out = clean(cat_result(None, status="too_large", message="m" * 400))
    part = out["parts"]["catalogue"]
    assert set(part) == {"status", "message"} and part["status"] == "too_large" and len(part["message"]) <= 300
    assert "entries" not in out


def test_tc044_take_result_cleans_and_the_claim_has_no_secrets(world, clock):
    # TC-044
    from abf_platform import jobs
    jid = jobs.enqueue_pipeline_files(world, None, None, ["catalogue"], clock=clock, caller_user_id=1)
    out = jobs.claim(world, "a1", clock)
    assert out["id"] == jid and out["args"] == {"repo": None, "revision": None, "parts": ["catalogue"]}
    assert "confirmation" not in out and "run_token" not in out
    raw = cat_result()
    raw["parts"]["catalogue"]["pipelines"][0]["token"] = "T"
    code, _ = jobs.take_result(world, "a1", jid, "done", raw, clock)
    assert code == 200
    stored = json.loads(sql(world, "SELECT result_json FROM jobs WHERE id = ?", (jid,))[0][0])
    assert stored["parts"]["catalogue"]["pipelines"] == good_entries()


def test_tc045_tc046_the_limits_and_the_name_rules():
    # TC-045, TC-046
    from abf_platform import jobs
    assert jobs.CATALOGUE_CACHE_SECONDS == 86400 and jobs.PF_CATALOGUE_ENTRIES == 1000
    assert jobs.PF_CATALOGUE_TAGS == 500 and jobs.PF_DESCRIPTION_LIMIT == 400
    for good in ("ampliseq", "Ampliseq_2", "a.b"):
        assert jobs.PF_PIPELINE_NAME.match(good), good
    for bad in ("../x", ".", "", "a b", "a/b"):
        assert not jobs.PF_PIPELINE_NAME.match(bad), bad
    assert jobs.PF_TAG_NAME.pattern == pipeline_files._TAG_NAME.pattern


def test_tc107_the_platform_never_names_the_agent_or_connects():
    # TC-107
    for name in ("jobs.py", "store.py"):
        assert "station" not in (PLATFORM_DIR / "abf_platform" / name).read_text(encoding="utf-8"), name


# ---- the action (CA) ------------------------------------------------------------------------------------------------------

def alice():
    from abf_platform import actions
    return actions.Caller(1, "alice", "lab")


def bob():
    from abf_platform import actions
    return actions.Caller(2, "bob", "lab")


def cat(db, caller=None, **kw):
    from abf_platform import actions
    return actions.nfcore_catalogue(db, caller=alice() if caller is None else caller, **kw)


def tick(db, clock, t):
    clock.t = t
    sql(db, "UPDATE agents SET last_seen_at = ?", (t,))


def serve(db, clock, result, state="done", agent="a1"):
    from abf_platform import jobs
    out = jobs.claim(db, agent, clock)
    assert out is not None and out["kind"] == "pipeline_files"
    code, _ = jobs.take_result(db, agent, out["id"], state, result, clock)
    assert code == 200
    return out["id"]


def network_down(db, clock):
    return serve(db, clock, {"ok": False, "error": "network", "message": "down"}, state="error")


LOADING = {"state": "loading", "checked_at": None, "count": None, "error": None, "reason": None, "pipelines": None}


def seen_shape(out):
    assert set(out) == CAT_KEYS
    json.dumps(out)
    if out["state"] == "error":
        assert out["reason"] and not NOT_FOR_USERS.search(out["reason"])
    return out


def test_tc047_the_signature():
    # TC-047
    from abf_platform import actions
    sig = inspect.signature(actions.nfcore_catalogue)
    assert not inspect.iscoroutinefunction(actions.nfcore_catalogue)
    assert list(sig.parameters) == ["platform_path", "compute_env", "caller", "enqueue"]
    assert [p.kind.name for p in sig.parameters.values()] == ["POSITIONAL_OR_KEYWORD"] + ["KEYWORD_ONLY"] * 3
    assert [sig.parameters[n].default for n in ("compute_env", "caller", "enqueue")] == [None, None, True]


def test_tc049_no_mcp_tool(tmp_path):
    # TC-049
    from abf_platform.mcp_server import build_server
    names = {t.name for t in asyncio.run(build_server(str(tmp_path / "index.db")).list_tools())}
    assert names and "nfcore_catalogue" not in names


def test_tc050_tc051_the_first_call_queues_one_job(world):
    # TC-050, TC-051
    assert seen_shape(cat(world)) == LOADING
    rows = sql(world, "SELECT * FROM jobs WHERE kind = 'pipeline_files'")
    assert len(rows) == 1 and json.loads(rows[0]["args_json"]) == {"repo": None, "revision": None, "parts": ["catalogue"]}
    assert cat(world) == LOADING and count_jobs(world) == 1


def ready(world, clock):
    cat(world)
    serve(world, clock, cat_result())
    return seen_shape(cat(world))


def test_tc052_to_tc055_ready_with_every_pipeline(world, clock):
    # TC-052, TC-053, TC-054, TC-055
    out = ready(world, clock)
    assert out["state"] == "ready" and out["count"] == 6 and out["checked_at"] == T0 and out["error"] is None and out["reason"] is None
    names = [p["name"] for p in out["pipelines"]]
    assert names == sorted(names) and all(set(p) == {"name", "repo", "description", "archived", "latest"} for p in out["pipelines"])
    by = {p["name"]: p for p in out["pipelines"]}
    assert by["ampliseq"]["repo"] == "nf-core/ampliseq" and by["ampliseq"]["latest"] == "3.0.0"
    assert by["abotyper"]["latest"] is None and by["exoseq"]["archived"] is True and by["cellpainting"]["description"] == ""
    assert "tags" not in json.dumps(out)


def test_tc056_tc057_the_newest_launchable_tag(world, clock):
    # TC-056, TC-057
    cat(world)
    entries = [{"name": "x1", "description": "", "archived": False, "tags": ["dev", "3.0.0dev", "1.0.0-rc1", "v2.0.0", "2.0.0", "1.9.0"]},
               {"name": "x2", "description": "", "archived": False, "tags": ["dev"]}]
    serve(world, clock, cat_result(entries))
    by = {p["name"]: p for p in cat(world)["pipelines"]}
    assert by["x1"]["latest"] == "2.0.0" and by["x2"]["latest"] is None


def test_tc058_an_entry_whose_repo_cannot_be_made_is_skipped(world, clock, monkeypatch):
    # TC-058
    from abf_platform import releases
    real = releases.repo_of

    def picky(name):
        if name == "x":
            raise ValueError("no")
        return real(name)

    monkeypatch.setattr(releases, "repo_of", picky)
    cat(world)
    serve(world, clock, cat_result(good_entries() + [{"name": "x", "description": "", "archived": False, "tags": []}]))
    out = cat(world)
    assert out["state"] == "ready" and out["count"] == 6 and "x" not in [p["name"] for p in out["pipelines"]]


@pytest.mark.parametrize("said", ["too_large", "bad_response", "rate_limited", "not_found"])
def test_tc059_tc063_a_failed_part(world, clock, said):
    # TC-059, TC-063
    cat(world)
    serve(world, clock, {"ok": True, "repo": None, "revision": None, "parts": {"catalogue": {"status": said, "message": "m"}}})
    out = seen_shape(cat(world))
    assert out["state"] == "error" and out["error"] == said and out["pipelines"] is None and out["count"] is None
    assert "nf-co.re" in out["reason"] and "GitHub" not in out["reason"]
    assert re.search(r"[一-鿿]", out["reason"]) and re.search(r"[A-Za-z]{4}", out["reason"])


def test_tc060_tc063_network(world, clock):
    # TC-060, TC-063
    cat(world)
    network_down(world, clock)
    out = seen_shape(cat(world))
    assert out["state"] == "error" and out["error"] == "network" and out["reason"] == NETWORK_REASON and out["checked_at"] == T0
    assert out["pipelines"] is None and out["count"] is None


def test_tc061_refused_says_update_the_agent(world, clock):
    # TC-061
    cat(world)
    serve(world, clock, {"ok": False, "message": "no"}, state="refused")
    out = seen_shape(cat(world))
    assert out["error"] == "refused" and ("更新" in out["reason"] or "update" in out["reason"])


def test_tc062_nobody_took_the_job(world, clock):
    # TC-062
    cat(world)
    tick(world, clock, T0 + 91)
    out = seen_shape(cat(world))
    assert out["state"] == "error" and out["error"] == "no_answer"


def test_tc064_tc065_a_failure_is_shown_for_a_minute(world, clock):
    # TC-064, TC-065
    cat(world)
    network_down(world, clock)
    first = cat(world)
    tick(world, clock, T0 + 30)
    assert cat(world) == first and count_jobs(world) == 1
    tick(world, clock, T0 + 61)
    assert cat(world) == LOADING and count_jobs(world) == 2


def test_tc066_tc067_tc068_the_day_long_reuse(world, clock):
    # TC-066, TC-067, TC-068
    first = ready(world, clock)
    tick(world, clock, T0 + 3600)
    again = cat(world)
    assert again["state"] == "ready" and again["checked_at"] == first["checked_at"] and count_jobs(world) == 1
    tick(world, clock, T0 + 86399)
    assert cat(world)["state"] == "ready" and count_jobs(world) == 1
    tick(world, clock, T0 + 86400)
    assert cat(world) == LOADING and count_jobs(world) == 2
    serve(world, clock, cat_result())
    new = cat(world)
    assert new["state"] == "ready" and new["checked_at"] == T0 + 86400


def test_tc069_tc070_no_old_list_when_the_new_job_fails(world, clock):
    # TC-069, TC-070
    ready(world, clock)
    tick(world, clock, T0 + 86401)
    assert cat(world) == LOADING
    network_down(world, clock)
    out = seen_shape(cat(world))
    assert out["state"] == "error" and out["error"] == "network" and out["pipelines"] is None
    tick(world, clock, T0 + 86401 + 61)
    assert cat(world) == LOADING


def test_tc071_tc072_no_agent(db):
    # TC-071, TC-072
    out = seen_shape(cat(db))
    assert out["state"] == "error" and out["error"] == "no_agent" and "沒有在線的代理" in out["reason"]
    assert count_jobs(db) == 0
    assert cat(db, enqueue=False) == LOADING and count_jobs(db) == 0


def test_tc073_tc074_tc075_each_user_has_their_own(world, clock):
    # TC-073, TC-074, TC-075
    ready(world, clock)
    assert cat(world, caller=bob()) == LOADING and count_jobs(world) == 2
    assert sql(world, "SELECT agent FROM jobs ORDER BY id DESC LIMIT 1")[0][0] == "a2"
    sql(world, "DELETE FROM jobs WHERE id = 2")
    sql(world, "DELETE FROM compute_envs WHERE owner_user_id = 2")
    assert cat(world, caller=bob())["error"] == "no_agent"
    again = cat(world, caller=bob(), compute_env="ce1")
    missing = cat(world, caller=bob(), compute_env="nope")
    assert again["state"] == "error" and again["reason"] == missing["reason"]


def test_tc076_no_file_is_kept(world, clock):
    # TC-076
    before = sorted(p.name for p in Path(world).parent.iterdir())
    ready(world, clock)
    after = sorted(p.name for p in Path(world).parent.iterdir())
    assert before == after and "release-tags.json" not in after


def test_tc077_tc078_the_block_in_the_action_layer():
    # TC-077, TC-078
    text = (PLATFORM_DIR / "abf_platform" / "actions" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r"# ---- nfcore-catalogue: begin.*?# ---- nfcore-catalogue: end", text, re.S)
    assert m, "the new code must sit between the nfcore-catalogue markers"
    for word in ("urllib", "socket", "subprocess", "open(", "station", "ssh", "sbatch", "threading", "while True"):
        assert word not in m.group(0), word
    old = re.search(r"# ---- release-lookup-job: begin.*?# ---- release-lookup-job: end", text, re.S)
    assert old and len(old.group(0).splitlines()) > 80
    assert re.findall(r"^def ([A-Za-z][A-Za-z0-9_]*)\(", m.group(0), re.M) == ["nfcore_catalogue"]


def test_tc079_tc080_every_answer_has_the_same_keys_and_clean_reasons(world, clock):
    # TC-079, TC-080
    seen_shape(cat(world))
    network_down(world, clock)
    seen_shape(cat(world))
    seen_shape(cat(world, caller=bob(), compute_env="nope"))
    ready(world, clock)


def test_tc081_pipeline_files_does_not_take_catalogue(world):
    # TC-081
    from abf_platform import actions
    for parts in (["catalogue"], ["schema", "catalogue"]):
        out = actions.pipeline_files(world, "nf-core/ampliseq", "2.18.0", parts=parts, caller=alice())
        assert out["state"] == "error" and out["error"] == "bad_input"
    assert count_jobs(world) == 0


def test_tc082_only_jobs_are_written(world, clock):
    # TC-082
    tables = ("confirmations", "launches", "compute_envs", "agents")

    def counts():
        return [sql(world, "SELECT COUNT(*) FROM %s" % t)[0][0] for t in tables]

    before = counts()
    ready(world, clock)
    assert counts() == before
    assert [r[0] for r in sql(world, "SELECT DISTINCT kind FROM jobs")] == ["pipeline_files"]


def test_tc083_no_query_and_the_whole_list(world, clock):
    # TC-083
    from abf_platform import actions
    names = inspect.signature(actions.nfcore_catalogue).parameters
    assert "query" not in names and "limit" not in names
    assert ready(world, clock)["count"] == 6


# ---- documents ------------------------------------------------------------------------------------------------------------

def test_tc096_the_platform_document_says_it():
    # TC-096
    text = (REPO_ROOT / "docs" / "PLATFORM.md").read_text(encoding="utf-8")
    assert "five kinds of public file" in text and "https://nf-co.re/pipelines.json" in text and "actions.nfcore_catalogue" in text
    assert "`nf-co.re` (one fixed address" in text and "Three actions read public" in text


def test_tc097_the_manual_steps_are_written():
    # TC-097
    text = (REPO_ROOT / "docs" / "TESTING.md").read_text(encoding="utf-8")
    assert "nfcore-catalogue：真的讀一次 nf-co.re (read nf-co.re for real, once)" in text
    assert text.index("release-lookup-job") < text.index("nfcore-catalogue：真的讀一次")


def test_tc100_the_fixture():
    # TC-100
    assert FIXTURE.stat().st_size <= 60 * 1024
    rows = {e["name"]: e for e in fixture_data()["remote_workflows"]}
    assert sorted(rows) == ["abotyper", "airrflow", "ampliseq", "cellpainting", "exoseq", "rnaseq"]
    assert [r["tag_name"] for r in rows["ampliseq"]["releases"]] == ["3.0.0", "2.18.0", "dev"]
    assert [r["tag_name"] for r in rows["abotyper"]["releases"]] == ["dev"]
    assert rows["cellpainting"]["description"] is None and rows["exoseq"]["archived"] is True
    assert all({"html_url", "topics", "stargazers_count"} <= set(e) and "tag_sha" in e["releases"][0] for e in rows.values())
