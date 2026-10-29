# Nothing existing: searched Nextflow's google-batch executor and Seqera's Google Batch form; neither ships an offline free preflight and the official Python packages are barred by TC-085, so gcloud is faked here.
"""Google Cloud Batch compute environments (gcb-ce-type, ruling two): create, validate, store, and a preflight that the
station agent runs on the platform host.

Every test uses a fake gcloud runner and a fake `which`; nothing touches the network. The TC ids refer to
specs/gcb-ce-type/test-case.md. No file written here holds a private-key header as one literal: the tests build it from pieces.
"""
import asyncio
import json
import re
import sqlite3
import sys
import time
from types import SimpleNamespace

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from station_harness import Inproc

PROJECT = "lab-project-1"
EMAIL = "runner@lab-project-1.iam.gserviceaccount.com"
BEGIN = "-----" + "BEGIN PRIVATE KEY" + "-----"      # built in pieces so that no tracked file holds a key-shaped line
KEY_TEXT = BEGIN + "\nMARKERPRIVATEBODY0123456789abcdef\n" + "-----END PRIVATE KEY" + "-----\n"
PEM = BEGIN + "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC"
CHECK_NAMES = ["credential_name", "credential_file", "credential_shape", "credential_project", "service_account", "gcloud",
               "batch_api", "bucket"]
GCB = "googlebatch-platform"
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="permission bits")


@pytest.fixture
def ip(tmp_path, monkeypatch):
    monkeypatch.delenv("ABF_STATION_GCP_CREDENTIALS", raising=False)
    box = Inproc(tmp_path, monkeypatch)
    box.tmp = tmp_path
    box.settings = tmp_path / "deploy" / "config" / "env.yaml"
    box.settings.parent.mkdir(parents=True)
    box.settings.write_text("reach: local\n")
    return box


# ---- helpers ---------------------------------------------------------------------------------------------------------

def good_config(**extra):
    c = {"project": PROJECT, "location": "europe-west2", "workDir": "gs://lab-bucket/work/"}
    c.update(extra)
    return c


def register_agent(ip, name="a1", age=0):
    from abf_platform import agents, store
    agents.register(ip.state_db, name, "0.1.0", lambda: time.time() - age)
    store.create_token(ip.tokens, kind="agent", agent_name=name)


def fields(name="gcb1", config=None, **top):
    f = {"name": name, "platform": GCB, "agent": "a1", "config": good_config() if config is None else config}
    f.update(top)
    return {k: v for k, v in f.items() if v is not None}


def create(ip, name="gcb1", config=None, **top):
    from abf_platform import compute_envs
    return compute_envs.create(ip.state_db, fields(name, config, **top))


def refused(ip, config=None, **top):
    from abf_platform import compute_envs
    with pytest.raises(compute_envs.CEError) as e:
        compute_envs.create(ip.state_db, fields("bad", config, **top))
    return str(e.value)


def key_data(**over):
    d = {"type": "service_account", "project_id": PROJECT, "client_email": EMAIL, "private_key": KEY_TEXT}
    d.update(over)
    return {k: v for k, v in d.items() if v is not None}


def key_file(ip, monkeypatch, content=None, mode=0o600, name="gcp-sa.json"):
    p = ip.tmp / name
    data = key_data() if content is None else content
    p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    if sys.platform != "win32":
        p.chmod(mode)
    monkeypatch.setenv("ABF_STATION_GCP_CREDENTIALS", str(p))
    return p


class Fake:
    """A fake gcloud runner that records every call."""

    def __init__(self, rc=0, out="", exc=None):
        self.rc, self.out, self.exc, self.calls = rc, out, exc, []

    def __call__(self, argv, env, timeout):
        self.calls.append((list(argv), dict(env), timeout))
        if self.exc:
            raise self.exc
        return self.rc, self.out


def fake_gcloud(monkeypatch, runner=None, have=True):
    from abf_station import gcb_preflight
    runner = runner or Fake()
    monkeypatch.setattr(gcb_preflight, "_run", runner)
    monkeypatch.setattr(gcb_preflight.shutil, "which", lambda n: ("/usr/bin/gcloud" if have else None) if n == "gcloud" else None)
    return runner


def serve(ip):
    """Play the station agent on the platform host: take every queued job, handle it with the real handler, answer it."""
    from abf_platform import jobs
    from abf_station import handlers
    ctx = SimpleNamespace(settings_file=str(ip.settings))
    answered = []
    while True:
        job = jobs.claim(ip.state_db, "a1", time.time, tokens_path=ip.tokens)
        if job is None:
            return answered
        state, result = handlers.handle(job, ctx)
        code, _ = jobs.take_result(ip.state_db, "a1", job["id"], state, result, time.time, tokens_path=ip.tokens)
        assert code == 200
        answered.append((job["id"], state, result))


@pytest.fixture
def auto_serve(ip, monkeypatch):
    """`ce preflight` waits for the agent's answer: let the agent answer first."""
    from abf_platform import jobs
    real = jobs.wait_for_result

    async def waiting(state, job_id, **kw):
        serve(ip)
        return await real(state, job_id, **kw)
    monkeypatch.setattr(jobs, "wait_for_result", waiting)
    return ip


def make_env(ip, cred="gcp-lab", name="gcb1", agent="a1", **cfg):
    argv = ["ce", "create", "--name", name, "--platform", GCB, "--config-json", json.dumps(good_config(**cfg))]
    if cred:
        argv += ["--credentials", cred]
    if agent:
        argv += ["--agent", agent]
    rc, out = ip.run(*argv)
    assert rc == 0, out
    return out


def checked_env(ip, **kw):
    """Create the environment and let the agent answer its first preflight. Returns the checks as a dict name -> (status, detail)."""
    make_env(ip, **kw)
    return last_checks(serve(ip))


def last_checks(answered):
    return {c["name"]: (c["status"], c["detail"]) for c in answered[-1][2]["checks"]}


def checks_of(out):
    return {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(r"^\s+(\w+): (pass|fail|unchecked) - (.*)$", out, re.M)}


def jobs_count(ip):
    con = sqlite3.connect(str(ip.state_db))
    try:
        return con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    finally:
        con.close()


def set_status(ip, name, status, ok=1):
    con = sqlite3.connect(str(ip.state_db))
    try:
        with con:
            con.execute("UPDATE compute_envs SET status = ?, checked_ok = ? WHERE name = ?", (status, ok, name))
    finally:
        con.close()


def flat_env(**over):
    e = {"name": "gcb1", "platform": GCB, "credentialsId": "gcp-lab", "project": PROJECT, "location": "europe-west2",
         "workDir": "gs://lab-bucket/work", "serviceAccountEmail": None}
    e.update(over)
    return e


def direct(cred, runner=None, which=None, stat=None, **env):
    """The station's run_preflight on a flat environment, with the fakes injected."""
    import os
    from abf_station import gcb_preflight
    return gcb_preflight.run_preflight(flat_env(**env), cred_path=cred, runner=runner or Fake(),
                                       which=which or (lambda n: "/usr/bin/gcloud"), stat=stat or os.stat)


def by_name(res):
    return {c["name"]: (c["status"], c["detail"]) for c in res["checks"]}


# ---- US1: the settings -----------------------------------------------------------------------------------------------

def test_a_valid_google_batch_environment_is_created_as_creating(ip):
    # TC-001, TC-002, TC-011
    cfg = good_config(spot=True, bootDiskSize="50 GB", bootDiskImage="projects/lab-project-1/global/images/my-image",
                      serviceAccountEmail=EMAIL, network="my-vpc", subnetwork="my-subnet", usePrivateAddress=False,
                      labels={"team": "lab"}, maxvCpus=100)
    ce = create(ip, config=cfg)
    assert ce["status"] == "creating" and "first preflight" in ce["message"]
    assert ce["config"] == dict(cfg, workDir="gs://lab-bucket/work")


def test_project_location_and_workdir_are_required(ip):
    # TC-003, TC-004, TC-005
    for key in ("project", "location", "workDir"):
        cfg = good_config()
        del cfg[key]
        assert key in refused(ip, cfg)


@pytest.mark.parametrize("bad", ["/data/work", "s3://b/x", "gs://", "gs://UPPER/x", "gs://b/../x"])
def test_workdir_must_be_a_gs_url(ip, bad):
    # TC-006
    assert "workDir" in refused(ip, good_config(workDir=bad))


def test_a_good_workdir_is_accepted(ip):
    # TC-007
    assert create(ip, config=good_config(workDir="gs://lab-bucket/work/"))["config"]["workDir"] == "gs://lab-bucket/work"


def test_project_location_and_flag_rules(ip):
    # TC-008, TC-009, TC-010
    for bad in ("Lab-Project", "abcde", "lab-project-"):
        assert "project" in refused(ip, good_config(project=bad)), bad
    assert "location" in refused(ip, good_config(location="Europe_West2"))
    create(ip, "ok1", good_config(location="europe-west2"))
    assert "spot" in refused(ip, good_config(spot="yes"))
    create(ip, "ok2", good_config(spot=True))


def test_boot_disk_size_rules(ip):
    # TC-011, TC-012
    for i, good in enumerate(("50 GB", "50GB")):
        create(ip, "d%d" % i, good_config(bootDiskSize=good))
    for bad in ("0 GB", "2001 GB", "50"):
        assert "bootDiskSize" in refused(ip, good_config(bootDiskSize=bad)), bad


def test_service_account_email_is_a_plain_email_not_a_secret(ip):
    # TC-013, TC-014
    assert create(ip, "e1", good_config(serviceAccountEmail=EMAIL))["config"]["serviceAccountEmail"] == EMAIL
    assert "serviceAccountEmail" in refused(ip, good_config(serviceAccountEmail="not-an-email"))


def test_labels_maxvcpus_and_network_rules(ip):
    # TC-015, TC-016, TC-017, TC-018
    for bad in ({"Team": "x"}, {"team": "a" * 64}, {"k%d" % i: "v" for i in range(65)}, ["a"]):
        assert "labels" in refused(ip, good_config(labels=bad)), bad
    for bad in (0, 10001, "many"):
        assert "maxvCpus" in refused(ip, good_config(maxvCpus=bad)), bad
    create(ip, "m1", good_config(maxvCpus=10000))
    assert create(ip, "m2", good_config(maxvCpus=100))["config"]["maxvCpus"] == 100
    assert "network" in refused(ip, good_config(network="Bad Name"))
    assert "subnetwork" in refused(ip, good_config(subnetwork="has space"))
    create(ip, "n1", good_config(network="default"))
    create(ip, "n2", good_config(network="projects/p1/global/networks/n1"))


@pytest.mark.parametrize("key", ["headQueue", "hostName", "foo", "wave", "fusion", "instanceTemplate", "gpu", "usd", "cap", "budgetTWD"])
def test_unknown_slurm_cost_and_future_keys_are_refused(ip, key):
    # TC-019, TC-080, TC-086
    msg = refused(ip, good_config(**{key: "x"}))
    assert "unknown setting for a Google Batch environment: %s (known: " % key in msg, msg
    assert "project" in msg and "labels" in msg
    assert not re.search(r"TWD|USD|cost|currency", msg.split("(known: ")[1], re.I)


def test_all_errors_are_listed_at_once_and_values_are_cut(ip):
    # TC-020, TC-021
    msg = refused(ip, good_config(project="Bad", spot="yes", bootDiskSize="x"))
    assert all(k in msg for k in ("project", "spot", "bootDiskSize"))
    msg = refused(ip, good_config(project="Q" * 200))
    assert "Q" * 60 in msg and "Q" * 61 not in msg


def test_a_google_batch_environment_without_an_agent_is_refused_even_with_one_agent_online(ip):
    # TC-022 (and TC-090: the automatic agent is for Slurm only)
    register_agent(ip)
    msg = refused(ip, agent=None)
    assert "agent" in msg and "代理" in msg
    rc, out = ip.run("ce", "create", "--name", "g9", "--platform", GCB, "--config-json", json.dumps(good_config()))
    assert rc != 0 and "agent" in out and ip.run("ce", "show", "g9")[0] != 0


def test_shared_checks_apply(ip):
    # TC-023
    create(ip, "shared", good_config(nextflowConfig="process.cpus = 2", preRunScript="true", postRunScript="true",
                                     environment=[{"name": "A", "value": "1"}]))
    assert "environment" in refused(ip, good_config(environment=[{"name": "bad name", "value": "1"}]))


# ---- US2: old records ------------------------------------------------------------------------------------------------

def _old_row(ip, name="old", config=None):
    from abf_platform import store
    con = store.connect_state(ip.state_db)
    with con:
        con.execute("INSERT INTO compute_envs (name, platform, status, message, is_primary, config_json, created_at, updated_at) "
                    "VALUES (?, 'googlebatch-platform', 'unsupported', 'Not supported yet', 0, ?, 1, 1)",
                    (name, json.dumps(config or {"workDir": "gs://lab-bucket/work", "location": "europe-west2", "spot": True})))
    con.close()


def test_an_old_google_batch_record_is_still_listed_and_shown(ip):
    # TC-024
    _old_row(ip)
    assert ip.show("old")["status"] == "unsupported" and "old" in ip.run("ce", "list")[1]


def test_an_old_record_must_be_completed_before_an_update_or_a_preflight(ip):
    # TC-025, TC-027
    _old_row(ip)
    register_agent(ip)
    before = ip.show("old")
    rc, out = ip.run("ce", "update", "old", "--description", "x")
    assert rc != 0 and "project" in out and ip.show("old") == before
    n = jobs_count(ip)
    rc, out = ip.run("ce", "preflight", "old")
    assert rc != 0 and "project" in out and jobs_count(ip) == n and ip.show("old")["status"] == "unsupported"


def test_an_old_record_that_is_completed_becomes_creating_and_is_then_checked(ip, monkeypatch):
    # TC-026
    _old_row(ip)
    register_agent(ip)
    key_file(ip, monkeypatch)
    fake_gcloud(monkeypatch)
    rc, out = ip.run("ce", "update", "old", "--project", PROJECT, "--agent", "a1", "--credentials", "gcp-lab")
    assert rc == 0, out
    assert ip.show("old")["status"] == "creating" and "preflight queued" in out
    serve(ip)
    assert ip.show("old")["status"] == "available"


def test_updating_a_disabled_environment_queues_no_preflight(ip):
    # TC-028
    register_agent(ip)
    make_env(ip)
    serve(ip)
    assert ip.run("ce", "disable", "gcb1")[0] == 0
    n = jobs_count(ip)
    rc, out = ip.run("ce", "update", "gcb1", "--location", "europe-west3")
    assert rc == 0 and ip.show("gcb1")["config"]["location"] == "europe-west3" and jobs_count(ip) == n
    rc, out = ip.run("ce", "update", "gcb1", "--project", "Bad")
    assert rc != 0


# ---- US3: credentials ------------------------------------------------------------------------------------------------

def test_the_credential_is_only_a_name_at_the_top_level(ip):
    # TC-029
    ce = create(ip, credentialsId="gcp-lab")
    assert ce["credentialsId"] == "gcp-lab" and "credentialName" not in ce["config"]
    assert "unknown setting" in refused(ip, good_config(credentialName="gcp-lab"))


def test_credentials_id_is_a_name_only(ip):
    # TC-030
    for bad in ("gcp lab", "key=abc", "A" * 60 + "==="):
        assert refused(ip, credentialsId=bad), bad


def test_a_private_key_pasted_anywhere_is_refused_and_not_repeated(ip):
    # TC-031, TC-032, TC-033
    create(ip, "ok")
    cases = [({"description": KEY_TEXT}, "description"), ({"config": good_config(nextflowConfig=KEY_TEXT)}, "nextflowConfig"),
             ({"config": good_config(environment=[{"name": "A", "value": KEY_TEXT}])}, "environment"),
             ({"config": good_config(labels={"a": KEY_TEXT})}, "labels")]
    for top, where in cases:
        msg = refused(ip, top.pop("config", None), **top)
        assert where in msg and "MARKERPRIVATEBODY" not in msg and "BEGIN" not in msg
    assert b"MARKERPRIVATEBODY" not in ip.state_db.read_bytes()


def test_a_key_named_field_is_refused(ip):
    # TC-034
    for key in ("privateKey", "serviceAccountKey"):
        assert key in refused(ip, good_config(**{key: "x"}))


def test_the_platform_does_not_read_the_key_file_and_nothing_of_it_is_stored(ip, monkeypatch):
    # TC-035
    from abf_platform import store
    marker = "UNIQUEMARKER4711"
    key_file(ip, monkeypatch, key_data(client_email=marker + "@x", private_key=marker, project_id=PROJECT))
    fake_gcloud(monkeypatch)
    register_agent(ip)
    make_env(ip)
    answered = serve(ip)
    assert not hasattr(store, "gcp_credentials_file")
    for f in (PLATFORM_DIR / "abf_platform").rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert "gcp-sa.json" not in text and "gcp_credentials" not in text and "GCP_CREDENTIALS" not in text, f.name
    assert marker.encode() not in ip.state_db.read_bytes() and marker not in json.dumps(answered)
    assert marker not in ip.run("ce", "show", "gcb1")[1]


# ---- US4: the preflight on the agent ----------------------------------------------------------------------------------

def test_every_check_is_reported_with_name_status_and_detail(ip, monkeypatch):
    # TC-040
    p = key_file(ip, monkeypatch)
    res = direct(p)
    assert [c["name"] for c in res["checks"]] == CHECK_NAMES and res["ok"] is True
    assert all(set(c) == {"name", "status", "detail"} for c in res["checks"])


def test_a_missing_credential_name_is_a_failure(ip, monkeypatch):
    # TC-041
    st, detail = by_name(direct(key_file(ip, monkeypatch), credentialsId=None))["credential_name"]
    assert st == "fail" and "憑證名字" in detail


def test_a_missing_key_file_says_where_to_put_it_and_leaves_the_environment_invalid(ip, monkeypatch):
    # TC-042, TC-043, TC-044
    absent = ip.tmp / "absent.json"
    monkeypatch.setenv("ABF_STATION_GCP_CREDENTIALS", str(absent))
    runner = fake_gcloud(monkeypatch)
    register_agent(ip)
    make_env(ip, cred=None)
    answered = serve(ip)
    c = last_checks(answered)
    assert c["credential_name"][0] == "fail"
    assert c["credential_file"][0] == "fail" and str(absent) in c["credential_file"][1] and "chmod 600" in c["credential_file"][1]
    assert c["credential_shape"][0] == "unchecked" and c["credential_project"][0] == "unchecked"
    assert ip.show("gcb1")["status"] == "invalid"
    assert runner.calls == []


@posix_only
def test_a_key_file_other_people_can_read_is_refused(ip, monkeypatch):
    # TC-045, TC-046
    p = key_file(ip, monkeypatch, mode=0o644)
    st, detail = by_name(direct(p))["credential_file"]
    assert st == "fail" and "permission" in detail
    p.chmod(0o600)
    assert by_name(direct(p))["credential_file"][0] == "pass"


def test_permission_bits_are_not_checked_on_windows(ip, monkeypatch):
    # TC-047. Runs on every OS (CI forbids skips): the platform check is switched to Windows, and on POSIX
    # the key file is deliberately world-readable (0644), which must then not be looked at.
    from abf_station import gcb_preflight
    monkeypatch.setattr(gcb_preflight, "sys", SimpleNamespace(platform="win32"))
    st, detail = by_name(direct(key_file(ip, monkeypatch, mode=0o644)))["credential_file"]
    assert st == "pass" and "Windows 不檢查權限位" in detail


def test_a_key_file_that_is_a_folder_is_refused(ip):
    # TC-042 (kind of file)
    d = ip.tmp / "adir"
    d.mkdir()
    assert by_name(direct(d))["credential_file"][0] == "fail"


def test_the_shape_of_the_key_file_is_judged_without_printing_it(ip, monkeypatch):
    # TC-048, TC-049, TC-050
    for drop in ("client_email", "private_key"):
        data = {"type": "service_account", "project_id": "MARK-PID", "client_email": "MARK-EMAIL", "private_key": "MARK-KEY"}
        del data[drop]
        p = key_file(ip, monkeypatch, data)
        res = direct(p)
        st, detail = by_name(res)["credential_shape"]
        assert st == "fail" and drop in detail and "MARK" not in json.dumps(res)
    p = key_file(ip, monkeypatch, {"type": "other", "project_id": "MARK-PID", "client_email": "MARK-E", "private_key": "MARK-K"})
    res = direct(p)
    assert by_name(res)["credential_shape"][0] == "fail" and "MARK" not in json.dumps(res)
    p = key_file(ip, monkeypatch, "{ this is MARK-TEXT not json")
    res = direct(p)
    assert by_name(res)["credential_shape"][0] == "fail" and "MARK" not in json.dumps(res)
    assert by_name(direct(key_file(ip, monkeypatch)))["credential_shape"][0] == "pass"


def test_no_marker_of_the_key_file_reaches_any_result(ip, monkeypatch):
    # TC-050
    marker = "ALLFIELDS8842"
    full = {"type": "service_account", "project_id": marker, "client_email": marker + "@x", "private_key": marker}
    fake_gcloud(monkeypatch, Fake(rc=1, out="failed"))
    key_file(ip, monkeypatch, full)
    register_agent(ip)
    make_env(ip)
    answered = serve(ip)
    ce = ip.show("gcb1")
    con = sqlite3.connect(str(ip.state_db))
    stored = " ".join(str(r) for r in con.execute("SELECT result_json FROM jobs"))
    con.close()
    for blob in (json.dumps(answered), json.dumps(ce), stored):
        assert marker not in blob


def test_the_project_in_the_key_file_must_match(ip, monkeypatch):
    # TC-051
    p = key_file(ip, monkeypatch, key_data(project_id="other-project-9"))
    st, detail = by_name(direct(p))["credential_project"]
    assert st == "fail" and "other-project-9" in detail and PROJECT in detail


def test_service_account_check_needs_no_match_with_the_file_email(ip, monkeypatch):
    # TC-052, TC-053
    p = key_file(ip, monkeypatch)
    st, detail = by_name(direct(p))["service_account"]
    assert st == "pass" and "預設帳號" in detail
    assert by_name(direct(p, serviceAccountEmail="other@lab-project-1.iam.gserviceaccount.com"))["service_account"][0] == "pass"


def test_without_gcloud_the_api_checks_are_unchecked_and_nothing_is_run(ip, monkeypatch):
    # TC-054, TC-055, TC-056
    p = key_file(ip, monkeypatch)
    runner = Fake()
    res = direct(p, runner=runner, which=lambda n: None)
    c = by_name(res)
    assert c["gcloud"][0] == "unchecked" and c["batch_api"][0] == "unchecked" and c["bucket"][0] == "unchecked"
    assert runner.calls == [] and res["ok"] is False
    # through the real path: the environment stops at invalid and the message names gcloud
    fake_gcloud(monkeypatch, have=False)
    register_agent(ip)
    make_env(ip)
    serve(ip)
    ce = ip.show("gcb1")
    assert ce["status"] == "invalid" and "gcloud" in ce["message"]


def test_all_checks_passing_makes_the_environment_available(ip, monkeypatch):
    # TC-057
    key_file(ip, monkeypatch)
    fake_gcloud(monkeypatch)
    register_agent(ip)
    c = checked_env(ip)
    assert [k for k in c] == CHECK_NAMES and all(v[0] == "pass" for v in c.values())
    ce = ip.show("gcb1")
    assert ce["status"] == "available" and ce["message"].startswith("preflight passed (預檢通過)")
    con = sqlite3.connect(str(ip.state_db))
    assert con.execute("SELECT checked_ok FROM compute_envs WHERE name = 'gcb1'").fetchone()[0] == 1
    con.close()


def test_an_api_failure_is_reported_and_trimmed(ip, monkeypatch):
    # TC-058, TC-059
    p = key_file(ip, monkeypatch)
    noisy = "permission denied " + "z" * 600 + PEM + "B" * 900 + " AKIA" + "ABCDEFGHIJKLMNOP"
    c = by_name(direct(p, runner=Fake(rc=1, out=noisy)))
    for name in ("batch_api", "bucket"):
        st, detail = c[name]
        assert st == "fail" and len(detail) <= 300
        assert "MIIEvQ" not in detail and "AKIA" not in detail and "BEGIN" not in detail
    fake_gcloud(monkeypatch, Fake(rc=1, out=noisy))
    register_agent(ip)
    make_env(ip)
    serve(ip)
    assert ip.show("gcb1")["status"] == "invalid"


def test_a_timeout_fails_that_check_only(ip, monkeypatch):
    # TC-060
    p = key_file(ip, monkeypatch)

    def slow(argv, env, timeout):
        if argv[1] == "batch":
            raise TimeoutError("slow")
        return 0, ""
    c = by_name(direct(p, runner=slow))
    assert c["batch_api"][0] == "fail" and "逾時" in c["batch_api"][1] and c["bucket"][0] == "pass"


def test_the_commands_are_read_only_and_carry_the_key_in_the_environment(ip, monkeypatch):
    # TC-061, TC-062, TC-063, TC-064, TC-065, TC-066
    p = key_file(ip, monkeypatch)
    monkeypatch.setenv("ABF_PLATFORM_TOKEN", "should-not-leak")
    runner = Fake()
    direct(p, runner=runner)
    lines = [" ".join(a) for a, _, _ in runner.calls]
    assert "gcloud batch jobs list --project lab-project-1 --location europe-west2 --limit 1 --format value(name)" in lines
    assert "gcloud storage ls gs://lab-bucket/ --project lab-project-1" in lines
    assert len(runner.calls) == 2
    for argv, env, timeout in runner.calls:
        assert " ".join(argv[:3]) in ("gcloud batch jobs", "gcloud storage ls")
        assert not set(argv) & {"create", "submit", "delete", "cp", "rm", "mb", "enable"}
        assert env["CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE"] == str(p) and env["CLOUDSDK_CORE_DISABLE_PROMPTS"] == "1"
        assert str(p) not in " ".join(argv)
        assert not [k for k in env if k.startswith("ABF_")]
        assert timeout == 30


def test_the_default_runner_is_a_fixed_argv_without_a_shell(monkeypatch):
    # TC-067
    from abf_station import gcb_preflight, site
    seen = {}

    class Done:
        returncode = 3
        stdout = "o" * 900
        stderr = ""

    def fake_run(argv, **kw):
        seen["argv"], seen["kw"] = argv, kw
        return Done()
    monkeypatch.setattr(site.subprocess, "run", fake_run)
    rc, out = gcb_preflight._run(["gcloud", "storage", "ls"], {"A": "1"}, 30)
    assert rc == 3 and len(out) <= 300
    assert isinstance(seen["argv"], list) and seen["kw"]["shell"] is False and seen["kw"]["timeout"] == 30


def test_the_key_file_location_is_the_agents_own_setting(ip, monkeypatch):
    # TC-068
    from abf_station import gcb_preflight
    custom = ip.tmp / "elsewhere.json"
    monkeypatch.setenv("ABF_STATION_GCP_CREDENTIALS", str(custom))
    assert gcb_preflight.credentials_path(ip.settings) == custom
    res = gcb_preflight.run_preflight(flat_env(), cred_path=gcb_preflight.credentials_path(ip.settings), runner=Fake(),
                                      which=lambda n: "/x")
    st, detail = by_name(res)["credential_file"]
    assert st == "fail" and str(custom) in detail
    monkeypatch.delenv("ABF_STATION_GCP_CREDENTIALS")
    assert gcb_preflight.credentials_path(ip.settings) == ip.settings.parent.parent / "_personal" / "gcp-sa.json"


def test_a_workload_identity_key_file_is_not_supported(ip, monkeypatch):
    # TC-085
    p = key_file(ip, monkeypatch, {"type": "external_account", "audience": "x", "subject_token_type": "y"})
    st, detail = by_name(direct(p))["credential_shape"]
    assert st == "fail" and "service" in detail.lower()
    fake_gcloud(monkeypatch)
    register_agent(ip)
    make_env(ip)
    serve(ip)
    assert ip.show("gcb1")["status"] == "invalid"


def test_the_agent_judges_the_environment_again_before_it_builds_a_command(ip, monkeypatch):
    # the agent trusts nothing the platform said: a project or bucket that would bend the command line is refused
    from abf_station import handlers
    p = key_file(ip, monkeypatch)
    runner = fake_gcloud(monkeypatch)
    ctx = SimpleNamespace(settings_file=str(ip.settings))
    for bad in ({"project": "x;y"}, {"location": "a b"}, {"workDir": "gs://b/x y"}, {"workDir": "/local"}):
        ce = flat_env(**bad)
        state, result = handlers.handle({"id": 1, "kind": "preflight", "args": {"ce": ce}}, ctx)
        assert state == "refused" and result["ok"] is False, bad
    assert runner.calls == [] and p.exists()


# ---- US4: the commands -----------------------------------------------------------------------------------------------

def test_create_queues_the_first_preflight_for_the_agent(ip, monkeypatch):
    # TC-037
    register_agent(ip)
    before = jobs_count(ip)
    out = make_env(ip)
    assert "preflight queued" in out
    ce = ip.show("gcb1")
    assert ce["status"] == "creating" and ce["agent"] == "a1" and jobs_count(ip) == before + 1
    con = sqlite3.connect(str(ip.state_db))
    assert con.execute("SELECT kind FROM jobs WHERE compute_env = 'gcb1'").fetchone()[0] == "preflight"
    con.close()


def test_create_with_the_agent_offline_says_so_and_does_not_pretend(ip):
    # TC-038
    register_agent(ip, age=100000)
    out = make_env(ip)
    assert "沒有代理在線" in out and ip.show("gcb1")["status"] == "creating"


def test_ce_preflight_waits_for_the_agent_and_prints_each_check(ip, auto_serve, monkeypatch):
    # TC-039
    key_file(ip, monkeypatch)
    fake_gcloud(monkeypatch)
    register_agent(ip)
    make_env(ip)
    serve(ip)
    rc, out = ip.run("ce", "preflight", "gcb1")
    c = checks_of(out)
    assert rc == 0 and list(c) == CHECK_NAMES and "status: available" in out


def test_cli_flags(ip, monkeypatch):
    # TC-001 (the flags of the plan)
    register_agent(ip)
    base = ["ce", "create", "--platform", GCB, "--agent", "a1", "--project", PROJECT, "--location", "europe-west2",
            "--config-json", json.dumps({"workDir": "gs://lab-bucket/work"})]
    assert ip.run(*base, "--name", "f1", "--spot", "--service-account-email", EMAIL, "--boot-disk-size", "50 GB")[0] == 0
    c = ip.show("f1")["config"]
    assert c["project"] == PROJECT and c["location"] == "europe-west2" and c["spot"] is True and c["serviceAccountEmail"] == EMAIL
    assert c["bootDiskSize"] == "50 GB" and c["workDir"] == "gs://lab-bucket/work"
    assert ip.run(*base, "--name", "f2", "--no-spot")[0] == 0 and ip.show("f2")["config"]["spot"] is False


def test_slurm_still_queues_a_job_for_its_agent(ip):
    # TC-088, TC-090
    register_agent(ip)
    rc, out = ip.create_slurm("s1")
    assert rc == 0 and "preflight queued" in out and ip.show("s1")["agent"] == "a1"
    con = sqlite3.connect(str(ip.state_db))
    assert con.execute("SELECT kind FROM jobs WHERE compute_env = 's1'").fetchone()[0] == "preflight"
    con.close()


# ---- US5: no launching yet --------------------------------------------------------------------------------------------

def _available_gcb(ip, name="gcb1", **top):
    register_agent(ip)
    create(ip, name, **top)
    set_status(ip, name, "available")


def test_agent_jobs_other_than_the_preflight_are_refused_in_plain_words(ip):
    # TC-070, TC-071
    from abf_platform import jobs
    _available_gcb(ip)
    before = jobs_count(ip)
    with pytest.raises(jobs.JobRefused) as e:
        jobs.enqueue_listing(ip.state_db, "gcb1", "/x")
    msgs = [str(e.value)]
    for kind in ("list_site_files", "fetch_run_records", "read_task_log"):
        with pytest.raises(jobs.JobRefused) as e:
            jobs.check_target(ip.state_db, "gcb1", kind)
        msgs.append(str(e.value))
    for msg in msgs:
        assert "尚未支援" in msg and "C-2" not in msg and "set an agent" not in msg and "has no agent" not in msg
    for kind in ("launch_nextflow", "cancel_run"):      # gcb-launch (C-2): these two are let through now
        jobs.check_target(ip.state_db, "gcb1", kind)
    assert jobs_count(ip) == before
    jobs.enqueue_preflight(ip.state_db, "gcb1")      # the preflight is the one job it takes
    assert jobs_count(ip) == before + 1


def test_launch_is_allowed_but_the_environment_is_never_auto_picked(ip):
    # TC-072, TC-073, TC-074
    from abf_launch import build
    _available_gcb(ip)
    assert build.target_problem(ip.state_db, "gcb1", "launch_nextflow") is None
    assert build.primary_environment(ip.state_db) is None
    rc, out = ip.run("ce", "primary", "gcb1")
    assert rc == 0 and ip.show("gcb1")["primary"] is True
    assert build.primary_environment(ip.state_db) is None
    assert ip.create_slurm("s1")[0] == 0
    set_status(ip, "s1", "available")
    con = sqlite3.connect(str(ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET is_primary = 0")
    con.close()
    assert build.primary_environment(ip.state_db) == "s1"


def test_another_users_google_batch_environment_is_not_found(ip):
    # TC-075, TC-076
    from abf_platform import compute_envs, jobs
    _available_gcb(ip, owner_user_id=1)
    before_env, n = compute_envs.get(ip.state_db, "gcb1"), jobs_count(ip)
    assert compute_envs.get(ip.state_db, "gcb1", owner=2) is None
    for call in (lambda: jobs.enqueue_listing(ip.state_db, "gcb1", "/x", caller_user_id=2),
                 lambda: jobs.check_target(ip.state_db, "gcb1", "launch_nextflow", caller_user_id=2)):
        with pytest.raises(jobs.JobRefused) as e:
            call()
        assert "not found" in str(e.value) and "Google" not in str(e.value)
    assert compute_envs.get(ip.state_db, "gcb1") == before_env and jobs_count(ip) == n


def test_tool_list_unchanged_and_no_new_web_route(tmp_path):
    # TC-077, TC-081
    from abf_platform import web
    from abf_platform.mcp_server import build_server
    names = {t.name for t in asyncio.run(build_server(str(tmp_path / "index.db")).list_tools())}
    assert names == {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "list_used_pipelines", "read_task_log",
                     "run_outputs", "my_usage", "launch", "cancel", "resume", "relaunch", "forget"}
    app = web.create_app(tmp_path / "index.db", tmp_path / "tokens.db", tmp_path / "platform.db")
    assert not [r.path for r in app.routes if re.search(r"gcb|google|batch|gcp", getattr(r, "path", ""), re.I)]
    for f in ("agents.py", "common.py", "mcp_server.py", "web.py"):
        assert not re.search(r"gcp|google", (PLATFORM_DIR / "abf_platform" / f).read_text(encoding="utf-8"), re.I)


def test_refusals_are_plain_words(ip):
    # TC-078
    from abf_platform import jobs
    msgs = [refused(ip, good_config(project="Bad")), refused(ip, good_config(workDir="/x")), refused(ip, agent=None),
            refused(ip, good_config(foo=1))]
    _available_gcb(ip, "avail")
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(ip.state_db, "avail", "list_site_files")
    msgs.append(str(e.value))
    for m in msgs:
        assert not re.search(r"Traceback|SELECT |INSERT |sqlite", m) and str(ip.tmp) not in m, m


# ---- US6: out of scope -----------------------------------------------------------------------------------------------

def test_nothing_of_the_later_slices_exists():
    # TC-079, TC-080, TC-084
    names = {p.name for p in PLATFORM_DIR.rglob("*.py")} | {p.name for p in (REPO_ROOT / "configs").rglob("*")}
    assert not names & {"rates.json"}      # cloud_cost.py is C-3's (cloud-cost); our price list is cloud_rates.json, a different name
    for f in list((PLATFORM_DIR / "abf_platform").rglob("*.py")) + list((PLATFORM_DIR / "abf_station").rglob("*.py")):
        text = f.read_text(encoding="utf-8")
        if f.name == "clean.py" and f.parent.name == "abf_station":      # cloud-cleanup-d: the one place that may hold the removing words
            assert not any(word in text for word in ("buckets create", "services enable", "service-accounts create")), f.name
            continue
        assert not re.search(r"buckets create|services enable|service-accounts create|storage rm", text), f.name
    assert "-with-tower" not in (PLATFORM_DIR / "abf_station" / "gcb_preflight.py").read_text(encoding="utf-8")


def test_the_other_types_stay_unsupported(ip):
    # TC-082
    from abf_platform import compute_envs
    from test_station_envs import UNSUPPORTED
    assert len(UNSUPPORTED) == 9
    for pid, cfg in UNSUPPORTED.items():
        ce = compute_envs.create(ip.state_db, {"name": "x-" + pid, "platform": pid, "config": cfg})
        assert ce["status"] == "unsupported", pid


def test_no_cloud_library_is_imported():
    # TC-083
    text = (PLATFORM_DIR / "abf_station" / "gcb_preflight.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(google|boto3|azure|requests)\b", text, re.M)
    assert "google-cloud" not in (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")
    for f in list((PLATFORM_DIR / "abf_platform").rglob("*.py")) + list((PLATFORM_DIR / "abf_station").rglob("*.py")):
        assert not re.search(r"^\s*(import|from)\s+(google|boto3|azure)\b", f.read_text(encoding="utf-8"), re.M), f.name


def test_no_migration_is_needed(ip):
    # TC-087
    create(ip)
    con = sqlite3.connect(str(ip.state_db))
    cols = [r[1] for r in con.execute("PRAGMA table_info(compute_envs)")]
    tables = sorted(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'"))
    con.close()
    assert cols == ["id", "name", "description", "platform", "credentials_id", "agent", "status", "message", "is_primary",
                    "checked_ok", "config_json", "created_at", "updated_at", "last_used_at", "owner_user_id"]
    assert tables == ["agents", "compute_envs", "confirmations", "jobs", "launches", "meta", "sqlite_sequence"]


# ---- US7: constants and docs -----------------------------------------------------------------------------------------

def test_the_type_constants():
    # TC-089
    from abf_platform import compute_envs
    assert compute_envs.SUPPORTED == "slurm-platform"
    # aws-launch changed this on purpose: before, PLATFORM_HOST_TYPES == (GCB,) and CHECK_ONLY_TYPES == ("awsbatch-platform",);
    # now AWS can be launched too, so it is a platform-host type and nothing is check-only any more.
    assert compute_envs.PLATFORM_HOST_TYPES == (GCB, "awsbatch-platform", "azbatch-platform")      # azure-launch
    # azure-ce-type changed this on purpose: Azure Batch is created and checked but not launched, so it is the one check-only type.
    assert compute_envs.CHECK_ONLY_TYPES == ("k8s-platform",)      # k8s-ce
    assert compute_envs.CHECKABLE == (compute_envs.SUPPORTED, GCB, "awsbatch-platform", "azbatch-platform", "k8s-platform")


def doc(name):
    return (REPO_ROOT / "docs" / name).read_text(encoding="utf-8")


def test_docs_list_every_gcb_key_and_check():
    # TC-096, TC-097, TC-098, TC-099, TC-100, TC-101
    d = doc("PLATFORM.md")
    assert re.search(r"`googlebatch-platform` \| Google Cloud Batch \| Slurm-like confirmed launch and cancel on the platform host "
                     r"\(resume: not yet\)", d)
    # aws-launch changed this sentence on purpose (plan A9 d): AWS Batch can run now
    assert "Slurm, Google Cloud Batch, AWS Batch and Azure Batch can run; Kubernetes can be created and checked on the platform host (launch: not yet); the other nine types can be modelled only" in d
    for key in ("project", "location", "workDir", "spot", "bootDiskSize", "bootDiskImage", "serviceAccountEmail", "network",
                "subnetwork", "usePrivateAddress", "labels", "maxvCpus") + tuple(CHECK_NAMES):
        assert "`%s`" % key in d, key
    assert "takes effect from C-2" in d and "ABF_STATION_GCP_CREDENTIALS" in d and "_personal/gcp-sa.json" in d
    assert "預檢不計費" in d and "creates no Batch job" in d
    par = doc("SEQERA_PARITY.md")
    row = [ln for ln in par.splitlines() if "`googlebatch-platform`" in ln][0]
    assert "Have (create + check + launch + cancel; resume not yet)" in row and row.rstrip().endswith("[ ] |")
    assert "a type turns supported only after a run on a real account" in par.replace("\n", " ")
    for text in (d, par, doc("TESTING.md")):
        assert not re.findall(r"[a-z0-9-]+@(?!lab-project-1)[a-z0-9-]+\.iam\.gserviceaccount\.com", text)
    t = doc("TESTING.md")
    assert "gcb-ce-type" in t and "預檢不計費" in t and "git diff" in t
