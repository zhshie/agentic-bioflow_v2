# Nothing existing: tests of the two read actions pipeline_files and latest_release, which turn an agent's answer into what the launch page shows; no earlier test knows them.
"""release-lookup-job, the action layer (A-01 to A-22): `actions.pipeline_files` and `actions.latest_release` are plain functions
that never wait: they queue one job for the caller's agent, say `loading` until it answers, and read the answer with the pure
modules schema.py and releases.py. Test cases are named in the comments (TC-093 ...). A database, a fake clock, and
`jobs.take_result` in place of the agent; no network, no agent process."""
import base64
import inspect
import json
import os
import re
import sqlite3
from pathlib import Path

import pytest

from helpers import Clock, PLATFORM_DIR, REPO_ROOT

T0 = 1_800_000_000.0
SCHEMA_TEXT = (PLATFORM_DIR / "tests" / "fixtures" / "schema" / "ampliseq-2.18.0.nextflow_schema.json").read_text(encoding="utf-8")
INPUT_TEXT = (REPO_ROOT / "tests" / "fixtures" / "schema_input" / "ampliseq-2.18.0.json").read_text(encoding="utf-8")
PNG = b"\x89PNG\r\n\x1a\n" + bytes(range(64))
DIAGRAM = {"status": "ok", "name": "ampliseq_workflow.png", "type": "image/png", "size": 753702}
PARTS3 = ["schema", "schema_input", "diagram"]
NETWORK_REASON = "代理連不到 GitHub，請檢查那台機器的網路 (the agent could not reach GitHub; check that machine's network)"
def Caller(*args):
    from abf_platform import actions
    return actions.Caller(*args)


PF_KEYS = {"state", "pipeline", "revision", "parts", "checked_at", "error", "reason", "schema", "schema_input", "diagram", "image"}
LR_KEYS = {"state", "pipeline", "revision", "source", "checked_at", "why", "error", "releases"}      # guided-launch-2d: every usable release, newest first
PF_ERRORS = {None, "bad_input", "no_agent", "no_answer", "network", "rate_limited", "not_found", "too_large", "bad_response", "refused"}
LR_ERRORS = {None, "bad_input", "no_agent", "no_answer", "network", "rate_limited", "not_found", "no_release", "refused"}
NOT_FOR_USERS = re.compile(r"Traceback|sqlite|args_json|deadline_at|result_json|SELECT")


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
    """alice (user 1) has an online agent and environment; bob (user 2) has his own."""
    add_user_env(db, "a1", "ce1", 1)
    add_user_env(db, "a2", "ce2", 2)
    return db


def alice():
    from abf_platform import actions
    return actions.Caller(1, "alice", "lab")


def bob():
    from abf_platform import actions
    return actions.Caller(2, "bob", "lab")


def tick(db, clock, t):
    """Move the clock and keep the agents looking online."""
    clock.t = t
    sql(db, "UPDATE agents SET last_seen_at = ?", (t,))


def count_jobs(db):
    return sql(db, "SELECT COUNT(*) FROM jobs WHERE kind = 'pipeline_files'")[0][0]


def pf(db, caller=None, pipeline="nf-core/ampliseq", revision="2.18.0", **kw):
    from abf_platform import actions
    caller = alice() if caller is None else caller
    return actions.pipeline_files(db, pipeline, revision, caller=caller, **kw)


def lr(db, caller=None, pipeline="ampliseq", **kw):
    from abf_platform import actions
    caller = alice() if caller is None else caller
    return actions.latest_release(db, pipeline, caller=caller, **kw)


def agent_parts(parts=PARTS3):
    out = {}
    if "schema" in parts:
        out["schema"] = {"status": "ok", "text": SCHEMA_TEXT}
    if "schema_input" in parts:
        out["schema_input"] = {"status": "ok", "text": INPUT_TEXT}
    if "diagram" in parts or "image" in parts:
        out["diagram"] = dict(DIAGRAM)
    if "image" in parts:
        out["image"] = dict(DIAGRAM, data_b64=base64.b64encode(PNG).decode())
    return out


def good(parts=PARTS3, **over):
    p = agent_parts(parts)
    p.update(over)
    return {"ok": True, "repo": "nf-core/ampliseq", "revision": "2.18.0", "parts": p, "message": "read"}


def serve(db, clock, result, state="done", agent="a1"):
    """The agent takes the oldest job it has and answers it."""
    from abf_platform import jobs
    out = jobs.claim(db, agent, clock)
    assert out is not None and out["kind"] == "pipeline_files"
    code, _ = jobs.take_result(db, agent, out["id"], state, result, clock)
    assert code == 200
    return out["id"]


def network_down(db, clock):
    return serve(db, clock, {"ok": False, "error": "network", "message": "down"}, state="error")


# ---- shape -------------------------------------------------------------------------------------------------------------------

def test_tc093_tc094_two_plain_functions_with_the_agreed_signatures():
    # TC-093, TC-094
    from abf_platform import actions
    for fn in (actions.pipeline_files, actions.latest_release):
        assert inspect.isfunction(fn) and not inspect.iscoroutinefunction(fn)
    sig = inspect.signature(actions.pipeline_files)
    assert list(sig.parameters) == ["platform_path", "pipeline", "revision", "parts", "compute_env", "caller", "enqueue"]
    assert [p.kind.name for p in sig.parameters.values()] == ["POSITIONAL_OR_KEYWORD"] * 3 + ["KEYWORD_ONLY"] * 4
    assert sig.parameters["parts"].default is None and sig.parameters["enqueue"].default is True
    sig = inspect.signature(actions.latest_release)
    assert list(sig.parameters) == ["platform_path", "pipeline", "compute_env", "caller", "enqueue"]
    assert [p.kind.name for p in sig.parameters.values()] == ["POSITIONAL_OR_KEYWORD"] * 2 + ["KEYWORD_ONLY"] * 3


def test_tc095_a_bad_pipeline_name(world):
    # TC-095
    for name in ("", "../x", "a/b/c", None, 123):
        out = pf(world, pipeline=name)
        assert out["state"] == "error" and out["error"] == "bad_input", name
    assert count_jobs(world) == 0


def test_tc096_a_branch_name_is_not_a_revision(world):
    # TC-096
    for revision in ("master", None, "", "3.0.0dev", "main", 5):
        out = pf(world, revision=revision)
        assert out["state"] == "error" and out["error"] == "bad_input", revision
    assert count_jobs(world) == 0


def test_tc097_bad_parts(world):
    # TC-097
    for parts in (["tags"], [], ["x"], ["schema", "schema"], "schema", ["schema", "tags"]):
        out = pf(world, parts=parts)
        assert out["state"] == "error" and out["error"] == "bad_input", parts
    assert count_jobs(world) == 0


def test_tc098_the_failure_shape(world):
    # TC-098
    out = pf(world, pipeline="../x")
    assert set(out) == PF_KEYS and out["state"] == "error"
    assert out["reason"].startswith("pipeline 名稱不合格") and re.search(r"[A-Za-z]{4}", out["reason"])
    assert out["schema"] is out["schema_input"] is out["diagram"] is out["image"] is None
    assert count_jobs(world) == 0


# ---- asking and answering -------------------------------------------------------------------------------------------------------

def test_tc099_tc100_tc101_the_first_call_queues_one_job_and_a_second_does_not(world):
    # TC-099, TC-100, TC-101
    first = pf(world)
    assert first["state"] == "loading" and first["parts"] == PARTS3 and first["checked_at"] is None and first["error"] is None
    assert first["schema"] is first["schema_input"] is first["diagram"] is first["image"] is None
    rows = sql(world, "SELECT * FROM jobs WHERE kind = 'pipeline_files'")
    assert len(rows) == 1 and json.loads(rows[0]["args_json"]) == {"repo": "nf-core/ampliseq", "revision": "2.18.0", "parts": PARTS3}
    assert pf(world)["state"] == "loading" and count_jobs(world) == 1


def test_tc102_a_job_the_agent_has_taken_is_still_loading(world, clock):
    # TC-102
    from abf_platform import jobs
    pf(world)
    assert jobs.claim(world, "a1", clock) is not None
    clock.t = T0 + 30
    assert pf(world)["state"] == "loading" and count_jobs(world) == 1


def test_tc103_tc104_tc105_tc106_the_answer_is_read(world, clock):
    # TC-103, TC-104, TC-105, TC-106
    from abf_platform import schema
    pf(world)
    clock.t = T0 + 5
    serve(world, clock, good())
    clock.t = T0 + 9
    out = pf(world)
    assert out["state"] == "ready" and set(out) == PF_KEYS and out["error"] is None and out["reason"] is None
    groups = schema.parameter_groups(schema.load(SCHEMA_TEXT))
    assert len(out["schema"]["groups"]) == 16 and out["schema"]["groups"] == groups
    assert out["schema"]["status"] == "ok" and out["schema"]["required_without_default"] == ["outdir"] == schema.required_without_default(groups)
    assert out["schema_input"] == {"status": "ok", "columns": schema.samplesheet_columns(schema.load(INPUT_TEXT))}
    assert out["diagram"] == DIAGRAM and out["image"] is None
    assert out["checked_at"] == T0 + 5 == sql(world, "SELECT finished_at FROM jobs")[0][0]
    assert out["pipeline"] == "nf-core/ampliseq" and out["revision"] == "2.18.0" and out["parts"] == PARTS3
    json.dumps(out)


def test_tc107_one_missing_file_does_not_block(world, clock):
    # TC-107
    pf(world)
    serve(world, clock, good(schema_input={"status": "not_found", "message": "gone"}))
    out = pf(world)
    assert out["state"] == "ready"
    assert out["schema_input"] == {"status": "not_found", "message": "這個版本沒有 assets/schema_input.json (this revision has no assets/schema_input.json)"}
    assert out["schema"]["status"] == "ok" and out["diagram"] == DIAGRAM


def test_tc108_a_schema_that_is_not_json(world, clock):
    # TC-108
    pf(world)
    serve(world, clock, good(schema={"status": "ok", "text": "not json"}))
    out = pf(world)
    assert out["state"] == "ready" and out["schema"]["status"] == "bad_json" and out["schema"]["message"]
    assert out["schema_input"]["status"] == "ok" and out["diagram"] == DIAGRAM


def test_tc109_when_every_part_failed_it_is_an_error(world, clock):
    # TC-109
    pf(world)
    serve(world, clock, good(schema={"status": "not_found"}, schema_input={"status": "not_found"}, diagram={"status": "not_found"}))
    out = pf(world)
    assert out["state"] == "error" and out["error"] == "not_found" and out["reason"]
    assert out["schema"] is out["schema_input"] is out["diagram"] is out["image"] is None
    assert out["checked_at"] == T0


def test_tc110_mixed_failures_name_the_first_part_in_order(world, clock):
    # TC-110
    pf(world)
    serve(world, clock, good(schema={"status": "rate_limited"}, schema_input={"status": "too_large"}, diagram={"status": "not_found"}))
    out = pf(world)
    assert out["state"] == "error" and out["error"] == "rate_limited" and out["schema"] is None


def test_tc111_tc112_a_total_failure_is_shown_for_a_minute_and_then_asked_again(world, clock):
    # TC-111, TC-112
    pf(world)
    serve(world, clock, good(schema={"status": "not_found"}, schema_input={"status": "not_found"}, diagram={"status": "not_found"}))
    tick(world, clock, T0 + 59)
    assert pf(world)["error"] == "not_found" and count_jobs(world) == 1
    tick(world, clock, T0 + 61)
    out = pf(world)
    assert out["state"] == "loading" and count_jobs(world) == 2


def test_tc113_a_lasting_failure_of_one_part_is_not_asked_again(world, clock):
    # TC-113
    pf(world)
    serve(world, clock, good(schema_input={"status": "not_found"}, schema={"status": "ok", "text": "not json"}))
    first = pf(world)
    assert first["state"] == "ready" and first["schema"]["status"] == "bad_json"
    tick(world, clock, T0 + 3600)
    second = pf(world)
    assert second == first
    assert pf(world)["state"] == "ready" and count_jobs(world) == 1


def test_tc114_tc115_a_part_that_failed_by_chance_is_asked_again_after_a_minute(world, clock):
    # TC-114, TC-115
    pf(world)
    serve(world, clock, good(diagram={"status": "rate_limited"}))
    tick(world, clock, T0 + 30)
    out = pf(world)
    assert out["state"] == "ready" and out["diagram"]["status"] == "rate_limited" and out["schema"]["status"] == "ok"
    assert count_jobs(world) == 1
    tick(world, clock, T0 + 61)
    assert pf(world)["state"] == "loading" and count_jobs(world) == 2


def test_tc116_tc117_tc118_the_network_error(world, clock):
    # TC-116, TC-117, TC-118
    pf(world)
    clock.t = T0 + 4
    network_down(world, clock)
    out = pf(world)
    assert out == {"state": "error", "pipeline": "nf-core/ampliseq", "revision": "2.18.0", "parts": PARTS3, "checked_at": T0 + 4,
                   "error": "network", "reason": NETWORK_REASON, "schema": None, "schema_input": None, "diagram": None, "image": None}
    tick(world, clock, T0 + 40)
    assert pf(world)["error"] == "network" and count_jobs(world) == 1
    tick(world, clock, T0 + 65)
    assert pf(world)["state"] == "loading" and count_jobs(world) == 2


def test_tc119_an_old_agent_that_does_not_know_the_kind(world, clock):
    # TC-119
    pf(world)
    serve(world, clock, {"ok": False, "message": "the job kind 'pipeline_files' is not supported (不支援)"}, state="refused")
    out = pf(world)
    assert out["state"] == "error" and out["error"] == "refused" and "abf-station" in out["reason"]


def test_tc120_tc121_nobody_takes_the_job(world, clock):
    # TC-120, TC-121
    pf(world)
    tick(world, clock, T0 + 91)
    out = pf(world)
    assert out["state"] == "error" and out["error"] == "no_answer" and out["reason"] and count_jobs(world) == 1
    tick(world, clock, T0 + 90 + 61)
    assert pf(world)["state"] == "loading" and count_jobs(world) == 2


def test_tc122_tc123_no_agent_online(db):
    # TC-122, TC-123
    out = pf(db)
    assert out["state"] == "error" and out["error"] == "no_agent" and out["reason"] and count_jobs(db) == 0
    out = pf(db, enqueue=False)
    assert out["state"] == "loading" and count_jobs(db) == 0


def test_tc124_tc125_tc126_one_user_never_sees_or_uses_the_others(world, clock):
    # TC-124, TC-125, TC-126
    pf(world)
    serve(world, clock, good())
    assert pf(world)["state"] == "ready"
    out = pf(world, caller=bob())
    assert out["state"] == "loading" and out["schema"] is None
    assert sql(world, "SELECT compute_env FROM jobs ORDER BY id DESC LIMIT 1")[0][0] == "ce2"
    add_user_env(world, "a3", "ce3", 3)
    nobody = pf(world, caller=Caller(4, "carol", "lab"))
    assert nobody["state"] == "error" and nobody["error"] == "no_agent"
    before = count_jobs(world)
    other = pf(world, caller=bob(), revision="2.17.0", compute_env="ce1")
    missing = pf(world, caller=bob(), revision="2.17.0", compute_env="ce-nope")
    assert other["state"] == missing["state"] == "error" and count_jobs(world) == before
    assert other["reason"].replace("ce1", "NAME") == missing["reason"].replace("ce-nope", "NAME")


def test_tc127_tc128_tc129_no_file_cache_and_the_finished_job_is_reused(world, clock, tmp_path):
    # TC-127, TC-128, TC-129
    pf(world)
    names = lambda: {n for n in os.listdir(tmp_path) if not n.startswith("platform.db")}
    before = names()
    serve(world, clock, good())
    pf(world)
    assert names() == before and "release-tags.json" not in names()
    tick(world, clock, T0 + 1000)
    pf(world)
    pf(world)
    assert count_jobs(world) == 1 and names() == before
    sql(world, "DELETE FROM jobs")
    assert pf(world)["state"] == "loading" and count_jobs(world) == 1


def test_tc130_tc131_the_picture_only_when_asked_for(world, clock):
    # TC-130, TC-131
    first = pf(world, parts=("image",))
    assert first["parts"] == ["image"]
    serve(world, clock, good(("image",)))
    out = pf(world, parts=("image",))
    assert out["state"] == "ready" and out["image"] == dict(DIAGRAM, data_b64=base64.b64encode(PNG).decode())
    assert out["diagram"] is None and out["schema"] is None
    pf(world)
    serve(world, clock, good())
    plain = pf(world)
    assert plain["state"] == "ready" and "data_b64" not in json.dumps(plain)


def test_tc132_every_shape_is_json_and_free_of_inner_words(world, clock):
    # TC-132
    seen = []

    def see(out):
        seen.append(out)
        json.dumps(out)
        return out

    see(pf(world, pipeline="../x"))
    see(pf(world, revision="main"))
    see(pf(world))
    serve(world, clock, good(schema={"status": "ok", "text": "not json"}, schema_input={"status": "too_large"}, diagram={"status": "rate_limited"}))
    see(pf(world))
    sql(world, "DELETE FROM jobs")
    see(pf(world))
    network_down(world, clock)
    see(pf(world))
    tick(world, clock, T0 + 100)
    see(pf(world))
    serve(world, clock, {"ok": False, "message": "x"}, state="refused")
    see(pf(world))
    see(pf(world, caller=Caller(9, "z", "l")))
    see(lr(world))
    see(lr(world, pipeline="../x"))
    for out in seen:
        assert set(out) in (PF_KEYS, LR_KEYS)
        for key in ("reason", "why"):
            if out.get(key):
                assert not NOT_FOR_USERS.search(out[key]), out[key]
        for key in ("schema", "schema_input", "diagram", "image"):
            part = out.get(key)
            if isinstance(part, dict) and part.get("message"):
                assert not NOT_FOR_USERS.search(part["message"])
        if out["state"] == "error":
            assert out.get("reason") or out.get("why")


def test_tc133_the_new_action_code_touches_neither_network_nor_files():
    # TC-133: the new code sits between two marker comments of actions/__init__.py
    text = (PLATFORM_DIR / "abf_platform" / "actions" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r"# ---- release-lookup-job: begin.*?# ---- release-lookup-job: end", text, re.S)
    assert m, "the new code must be kept between the release-lookup-job markers"
    body = m.group(0)
    assert len(body.splitlines()) > 80
    for word in ("urllib", "socket", "subprocess", "open("):
        assert word not in body, word


def test_tc135_no_mcp_tool_for_the_three_actions(tmp_path):
    # TC-135: the tool count is pinned by the older tests (test_actions_layer, test_pat, test_oauth_mcp), which are not changed; here only the two names
    import asyncio
    from abf_platform.mcp_server import build_server
    names = {t.name for t in asyncio.run(build_server(str(tmp_path / "index.db")).list_tools())}
    assert names and not ({"pipeline_files", "latest_release", "nfcore_catalogue"} & names)


def test_tc159_the_catalogue_is_its_own_action(world):
    # TC-159 (flipped by nfcore-catalogue: the maintainer allowed reading nf-co.re on 2026-10-26)
    from abf_platform import actions
    assert callable(actions.nfcore_catalogue)
    assert "catalogue" not in inspect.signature(actions.pipeline_files).parameters
    assert pf(world, parts=["catalogue"])["error"] == "bad_input"


# ---- latest_release ----------------------------------------------------------------------------------------------------------------

TAGS_TEXT = "".join("%040x\trefs/tags/%s\n" % (i + 1, t) for i, t in enumerate(["2.18.0", "3.0.0", "3.0.0dev", "dev"]))


def tags_result(text=TAGS_TEXT):
    return {"ok": True, "repo": "nf-core/ampliseq", "revision": None, "parts": {"tags": {"status": "ok", "text": text}}, "message": "read"}


def cache_file(db):
    return Path(db).parent / "release-tags.json"


def test_tc136_tc137_the_first_call(world):
    # TC-136, TC-137
    out = lr(world)
    assert out["pipeline"] == "nf-core/ampliseq" and out["state"] == "loading" and out["revision"] is None and out["source"] == "none"
    assert set(out) == LR_KEYS and out["error"] is None
    rows = sql(world, "SELECT args_json FROM jobs WHERE kind = 'pipeline_files'")
    assert len(rows) == 1 and json.loads(rows[0][0]) == {"repo": "nf-core/ampliseq", "revision": None, "parts": ["tags"]}
    assert lr(world)["state"] == "loading" and count_jobs(world) == 1


def test_tc138_tc139_tc140_the_newest_plain_version_is_found_and_remembered(world, clock):
    # TC-138, TC-139, TC-140
    lr(world)
    serve(world, clock, tags_result())
    clock.t = T0 + 7
    out = lr(world)
    assert out["state"] == "ready" and out["revision"] == "3.0.0" and out["source"] == "fetched" and out["checked_at"] == T0 + 7
    assert out["error"] is None and out["why"] is None
    assert json.loads(cache_file(world).read_text(encoding="utf-8")) == {"nf-core/ampliseq": {"revision": "3.0.0", "checked_at": T0 + 7, "releases": ["3.0.0", "2.18.0"]}}      # guided-launch-2d: the entry keeps the list
    assert re.match(r"^(v?[0-9]+(\.[0-9]+){1,3}|[0-9a-f]{40})\Z", out["revision"])


def test_tc141_the_cache_answers_for_a_day_without_a_job(world, clock):
    # TC-141
    lr(world)
    serve(world, clock, tags_result())
    lr(world)
    tick(world, clock, T0 + 3600)
    out = lr(world)
    assert out["state"] == "ready" and out["source"] == "cache" and out["revision"] == "3.0.0" and count_jobs(world) == 1


def test_tc142_exactly_a_day_later_the_cache_is_over(world, clock):
    # TC-142
    lr(world)
    serve(world, clock, tags_result())
    lr(world)
    tick(world, clock, T0 + 86400)
    out = lr(world)
    assert out["state"] == "loading" and count_jobs(world) == 2


def seed_cache(db, revision="2.18.0", checked_at=T0 - 90000):
    cache_file(db).write_text(json.dumps({"nf-core/ampliseq": {"revision": revision, "checked_at": checked_at}}), encoding="utf-8")


def test_tc143_tc144_an_old_answer_is_better_than_none_when_the_agent_fails(world, clock):
    # TC-143, TC-144
    seed_cache(world)
    before = cache_file(world).read_bytes()
    assert lr(world)["state"] == "loading"
    network_down(world, clock)
    out = lr(world)
    assert out["state"] == "ready" and out["revision"] == "2.18.0" and out["source"] == "stale-cache" and out["why"]
    assert cache_file(world).read_bytes() == before


def test_tc145_tc146_without_any_answer_the_error_is_shown_and_asked_again_later(world, clock):
    # TC-145, TC-146
    lr(world)
    network_down(world, clock)
    out = lr(world)
    assert out["state"] == "error" and out["error"] == "network" and out["revision"] is None and out["source"] == "none" and out["why"]
    assert not cache_file(world).exists()
    tick(world, clock, T0 + 61)
    assert lr(world)["state"] == "loading" and count_jobs(world) == 2
    serve(world, clock, tags_result())
    assert lr(world)["revision"] == "3.0.0"


def test_tc147_tc148_no_usable_tag(world, clock):
    # TC-147, TC-148
    lr(world)
    serve(world, clock, tags_result("%040x\trefs/tags/dev\n%040x\trefs/tags/3.0.0dev\n" % (1, 2)))
    out = lr(world)
    assert out["state"] == "error" and out["error"] == "no_release" and "沒有可用的 release tag" in out["why"]
    assert out["revision"] is None and not cache_file(world).exists()


def test_tc149_a_bad_name_for_the_newest_release(world):
    # TC-149
    out = lr(world, pipeline="../x")
    assert out["state"] == "error" and out["error"] == "bad_input" and out["pipeline"] == "../x" and out["why"]
    assert count_jobs(world) == 0
    assert lr(world, pipeline=None)["pipeline"] is None


def test_tc150_no_agent_and_no_cache(db):
    # TC-150
    out = lr(db)
    assert out["state"] == "error" and out["error"] == "no_agent" and count_jobs(db) == 0


def test_tc151_the_keys_are_always_there(world, clock):
    # TC-151
    shapes = [lr(world)]
    serve(world, clock, tags_result())
    shapes.append(lr(world))
    shapes.append(lr(world, pipeline="../x"))
    for out in shapes:
        assert set(out) == LR_KEYS and out["error"] in LR_ERRORS and out["state"] in ("loading", "ready", "error")
        json.dumps(out)


def test_tc180_the_two_actions_write_only_jobs(world, clock):
    # TC-180
    before = {t: sql(world, "SELECT COUNT(*) FROM %s" % t)[0][0] for t in ("confirmations", "launches", "compute_envs", "agents")}
    pf(world)
    lr(world)
    assert {t: sql(world, "SELECT COUNT(*) FROM %s" % t)[0][0] for t in before} == before
    assert sql(world, "SELECT DISTINCT kind FROM jobs")[0][0] == "pipeline_files" and count_jobs(world) == 2
