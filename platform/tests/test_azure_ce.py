# Nothing existing: searched Nextflow's azurebatch executor and Seqera's Azure Batch form; neither ships an offline, free preflight, and the official azure Python packages are barred by TC-085, so the az command line is faked here.
"""Azure Batch compute environments (azure-ce-type): create, validate, store, and a preflight that the station agent runs on
the platform host. Launching on Azure is a later task (azure-launch); here it is refused in plain words.

Every test uses a fake az runner and a fake `which`; nothing touches the network. The TC ids refer to
specs/azure-ce-type/test-case.md. No file written here holds a full account key as one literal: the tests build them from pieces.
"""
import asyncio
import json
import os
import re
import sqlite3
import sys
import time
from types import SimpleNamespace

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from station_harness import Inproc

LOC = "westeurope"
BATCH = "labbatch"
STORE = "labstore"
WORKDIR = "az://lab-container/work/"
POOL = "lab-pool"
CRED = "azure-lab"
AZ = "azbatch-platform"
BKEY = "MARKER" + "BATCHKEY" + "A" * 60                      # built in pieces so that no tracked file holds a key-shaped string
SKEY = "MARKER" + "STOREKEY" + "B" * 60
SAS = "sv=2024-01-01&" + "s" + "ig=" + "MARKERSAS" + "C" * 30
CONN = "Account" + "Key=" + BKEY
SHARED = "SharedAccess" + "Signature=" + SAS
CRED_FILE = "[default]\nbatch_account_key = " + BKEY + "\nstorage_account_key = " + SKEY + "\n"
SAS_FILE = "[default]\nbatch_account_key = " + BKEY + "\nstorage_sas_token = " + SAS + "\n"
CHECK_NAMES = ["credential_name", "credential_file", "credential_shape", "az", "pool", "storage"]
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="permission bits")


@pytest.fixture
def ip(tmp_path, monkeypatch):
    monkeypatch.delenv("ABF_STATION_AZURE_CREDENTIALS", raising=False)
    box = Inproc(tmp_path, monkeypatch)
    box.tmp = tmp_path
    box.settings = tmp_path / "deploy" / "config" / "env.yaml"
    box.settings.parent.mkdir(parents=True)
    box.settings.write_text("reach: local\n")
    return box


# ---- helpers ---------------------------------------------------------------------------------------------------------

def good_config(**extra):
    c = {"location": LOC, "batchAccountName": BATCH, "storageAccountName": STORE, "workDir": WORKDIR, "pool": POOL}
    c.update(extra)
    return c


def register_agent(ip, name="a1", age=0):
    from abf_platform import agents, store
    agents.register(ip.state_db, name, "0.1.0", lambda: time.time() - age)
    store.create_token(ip.tokens, kind="agent", agent_name=name)


def fields(name="az1", config=None, **top):
    f = {"name": name, "platform": AZ, "agent": "a1", "config": good_config() if config is None else config}
    f.update(top)
    return {k: v for k, v in f.items() if v is not None}


def create(ip, name="az1", config=None, **top):
    from abf_platform import compute_envs
    return compute_envs.create(ip.state_db, fields(name, config, **top))


def refused(ip, config=None, **top):
    from abf_platform import compute_envs
    with pytest.raises(compute_envs.CEError) as e:
        compute_envs.create(ip.state_db, fields("bad", config, **top))
    return str(e.value)


def cred_file(ip, monkeypatch, content=None, mode=0o600, name="azure-credentials"):
    p = ip.tmp / name
    p.write_bytes((CRED_FILE if content is None else content).encode("utf-8") if isinstance(content, (str, type(None))) else content)
    if sys.platform != "win32":
        p.chmod(mode)
    monkeypatch.setenv("ABF_STATION_AZURE_CREDENTIALS", str(p))
    return p


class Fake:
    """A fake az runner that records every call (argv, the environment, the config folder as it was at that moment)."""

    def __init__(self, replies=None, exc=None):
        self.replies = {"batch": (0, "active"), "storage": (0, "true")}
        self.replies.update(replies or {})
        self.exc = exc or {}
        self.calls = []
        self.dirs = []

    def __call__(self, argv, env, timeout):
        self.calls.append((list(argv), dict(env), timeout))
        d = env.get("AZURE_CONFIG_DIR")
        self.dirs.append((d, os.path.isdir(d) if d else False, os.listdir(d) if d and os.path.isdir(d) else None))
        if argv[1] in self.exc:
            raise self.exc[argv[1]]
        return self.replies[argv[1]]


def fake_az(monkeypatch, runner=None, have=True):
    from abf_station import azure_preflight
    runner = runner or Fake()
    monkeypatch.setattr(azure_preflight, "_run", runner)
    monkeypatch.setattr(azure_preflight.shutil, "which", lambda n: ("/usr/bin/az" if have else None) if n == "az" else None)
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
    from abf_platform import jobs
    real = jobs.wait_for_result

    async def waiting(state, job_id, **kw):
        serve(ip)
        return await real(state, job_id, **kw)
    monkeypatch.setattr(jobs, "wait_for_result", waiting)
    return ip


def make_env(ip, cred=CRED, name="az1", agent="a1", **cfg):
    argv = ["ce", "create", "--name", name, "--platform", AZ, "--config-json", json.dumps(good_config(**cfg))]
    if cred:
        argv += ["--credentials", cred]
    if agent:
        argv += ["--agent", agent]
    rc, out = ip.run(*argv)
    assert rc == 0, out
    return out


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
    e = {"name": "az1", "platform": AZ, "credentialsId": CRED, "location": LOC, "batchAccountName": BATCH,
         "storageAccountName": STORE, "workDir": "az://lab-container/work", "pool": POOL}
    e.update(over)
    return e


def direct(cred, runner=None, which=None, stat=None, **env):
    """The station's run_preflight on a flat environment, with the fakes injected."""
    from abf_station import azure_preflight
    return azure_preflight.run_preflight(flat_env(**env), cred_path=cred, runner=runner or Fake(),
                                         which=which or (lambda n: "/usr/bin/az"), stat=stat or os.stat)


def by_name(res):
    return {c["name"]: (c["status"], c["detail"]) for c in res["checks"]}


# ---- US1: the settings -----------------------------------------------------------------------------------------------

def test_a_valid_azure_batch_environment_is_created_as_creating(ip):
    # TC-001
    ce = create(ip, config=good_config(spot=True, maxvCpus=256))
    assert ce["status"] == "creating" and "waiting for the first preflight" in ce["message"]
    assert ce["config"]["workDir"] == "az://lab-container/work"
    assert ce["config"]["location"] == LOC and ce["config"]["pool"] == POOL
    assert ce["config"]["batchAccountName"] == BATCH and ce["config"]["storageAccountName"] == STORE


def test_required_settings_and_agent(ip):
    # TC-002, TC-003, TC-004, TC-005, TC-006, TC-007, TC-008, TC-149
    for key in ("location", "batchAccountName", "storageAccountName", "workDir", "pool"):
        cfg = good_config()
        del cfg[key]
        assert key in refused(ip, cfg)
    msg = refused(ip, agent=None)
    assert "需要指定一個站台代理" in msg and "--agent" in msg
    register_agent(ip)
    rc, out = ip.run("ce", "create", "--name", "noagent", "--platform", AZ, "--credentials", CRED,
                     "--config-json", json.dumps(good_config()))
    assert rc != 0 and "agent" in out and ip.rows()["compute_envs"] == []


def test_a_missing_credential_name_does_not_stop_the_creation(ip):
    # TC-009 (ruling 12)
    ce = create(ip)
    assert ce["status"] == "creating"
    register_agent(ip)
    out = make_env(ip, cred=None, name="az2")
    assert ip.show("az2")["status"] == "creating" and out


def test_location_rules(ip):
    # TC-010, TC-011
    for i, good in enumerate(("westeurope", "japaneast", "eastus2")):
        create(ip, "l%d" % i, good_config(location=good))
    for bad in ("West Europe", "eu-west-1", "", "a; b"):
        msg = refused(ip, good_config(location=bad))
        assert "location" in msg and "westeurope" in msg, bad


def test_account_name_rules(ip):
    # TC-012, TC-013, TC-014
    for key in ("batchAccountName", "storageAccountName"):
        for i, good in enumerate(("labbatch", "ab1")):
            create(ip, "%s%d" % (key[:3], i), good_config(**{key: good}))
        for bad in ("LabBatch", "ab", "a" * 25, "lab-batch", "lab_batch"):
            assert key in refused(ip, good_config(**{key: bad})), (key, bad)


def test_workdir_must_be_an_azure_blob_url_with_a_subfolder(ip):
    # TC-015, TC-016, TC-017, TC-018, TC-019
    assert create(ip, "w1", good_config(workDir="az://lab-container/work/"))["config"]["workDir"] == "az://lab-container/work"
    for bad in ("/data/work", "s3://b/x", "gs://b/x", "az://", "az://lab-container", "az://lab-container/",
                "az://UPPER/x", "az://ab/x", "az://lab-container/../x"):
        assert "workDir" in refused(ip, good_config(workDir=bad)), bad


def test_pool_is_an_id_not_a_path(ip):
    # TC-020, TC-021
    for i, good in enumerate(("lab-pool", "Pool_1")):
        create(ip, "p%d" % i, good_config(pool=good))
    for bad in ("a b", "a/b", "p" * 65, ""):
        assert "pool" in refused(ip, good_config(pool=bad)), bad


def test_spot_and_maxvcpus_rules(ip):
    # TC-022, TC-023, TC-024, TC-025
    assert "spot" in refused(ip, good_config(spot="yes"))
    for bad in (0, 10001, True, "8"):
        assert "maxvCpus" in refused(ip, good_config(maxvCpus=bad)), bad
    assert create(ip, "m1", good_config(maxvCpus=10000))["config"]["maxvCpus"] == 10000
    assert create(ip, "m2", good_config(spot=True))["config"]["spot"] is True
    assert create(ip, "m3", good_config(spot=False))["config"]["spot"] is False


def test_unknown_keys_are_refused_and_old_keys_say_what_to_do(ip):
    # TC-026, TC-027, TC-124, TC-126, TC-127
    for key in ("region", "vmType", "jobQueue", "headQueue", "project", "foo", "currency", "costCap", "allowPoolCreation",
                "autoPoolMode", "servicePrincipalId", "tenantId", "managedIdentity", "virtualNetwork", "customImage", "fileShare"):
        msg = refused(ip, good_config(**{key: "x"}))
        assert "unknown setting for an Azure Batch environment" in msg and "known:" in msg and "pool" in msg, key
        if key in ("region", "vmType"):
            assert "請刪除後重建這個計算環境" in msg, key


def test_all_errors_are_listed_at_once_and_values_are_cut(ip):
    # TC-028, TC-029
    msg = refused(ip, good_config(location="x" * 200, pool="a b", workDir="nope"))
    assert "location" in msg and "pool" in msg and "workDir" in msg
    assert "x" * 60 in msg and "x" * 61 not in msg


def test_shared_checks_apply(ip):
    # TC-030, TC-031
    assert "nextflowConfig" in refused(ip, good_config(nextflowConfig="x" * 20001))
    assert "environment" in refused(ip, good_config(environment=[{"name": "bad name", "value": "1"}]))


# ---- US2: the credential is a name --------------------------------------------------------------------------------------

def test_the_credential_is_only_a_name_at_the_top_level(ip):
    # TC-032
    create(ip, credentialsId=CRED)
    ce = ip.show("az1")
    assert ce["credentialsId"] == CRED
    assert not [k for k in ce["config"] if re.search(r"cred|key|secret|token", k, re.I)]


def test_credentials_id_is_a_name_only(ip):
    # TC-033
    for bad in ("azure lab", "key=abc", BKEY + "=="):
        assert refused(ip, credentialsId=bad), bad


def test_an_account_key_or_sas_pasted_anywhere_is_refused_and_not_repeated(ip):
    # TC-034, TC-035, TC-036, TC-037
    create(ip, "ok")
    for secret in (CONN, SHARED, "x" + SAS):
        cases = [({"description": secret}, "description"), ({"config": good_config(nextflowConfig=secret)}, "nextflowConfig"),
                 ({"config": good_config(environment=[{"name": "A", "value": secret}])}, "environment"),
                 ({"config": good_config(workDir="az://lab-container/" + secret)}, "workDir")]
        for top, where in cases:
            msg = refused(ip, top.pop("config", None), **top)
            assert where in msg and BKEY not in msg and "MARKER" not in msg and "MARKERSAS" not in msg, (secret[:12], where)
    blob = ip.state_db.read_bytes()
    assert BKEY.encode() not in blob and SKEY.encode() not in blob and SAS.encode() not in blob and b"MARKERSAS" not in blob


def test_a_key_named_field_is_refused(ip):
    # TC-038
    for key in ("batchAccountKey", "accountKey", "sasToken", "servicePrincipalSecret"):
        msg = refused(ip, good_config(**{key: "x"}))
        assert key in msg and "像憑證" in msg and "unknown setting" not in msg, (key, msg)


def test_normal_values_are_not_mistaken_for_secrets(ip):
    # TC-039, TC-040
    assert create(ip)["status"] == "creating"
    assert create(ip, "d1", description="a design=1 run, signature of the lab")["status"] == "creating"


def test_the_platform_does_not_read_the_credential_file(ip, monkeypatch):
    # TC-041
    p = cred_file(ip, monkeypatch)
    register_agent(ip)
    outs = [make_env(ip), ip.run("ce", "list")[1], ip.run("ce", "show", "az1")[1]]
    assert p.exists()
    assert BKEY.encode() not in ip.state_db.read_bytes() and SKEY.encode() not in ip.state_db.read_bytes()
    for out in outs:
        assert "MARKER" not in out
    for f in (PLATFORM_DIR / "abf_platform").rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert "azure-credentials" not in text and "AZURE_CREDENTIALS" not in text, f.name


# ---- US3: the preflight on the agent -----------------------------------------------------------------------------------

def test_every_check_is_reported_with_name_status_and_detail(ip, monkeypatch):
    # TC-042
    p = cred_file(ip, monkeypatch)
    res = direct(p)
    assert [c["name"] for c in res["checks"]] == CHECK_NAMES and res["ok"] is True
    assert all(set(c) == {"name", "status", "detail"} for c in res["checks"])


def test_a_missing_credential_name_is_a_failure(ip, monkeypatch):
    # TC-043
    c = by_name(direct(cred_file(ip, monkeypatch), credentialsId=None))
    assert c["credential_name"][0] == "fail" and c["credential_shape"][0] == "unchecked"


def test_a_missing_credential_file_says_where_to_put_it(ip, monkeypatch):
    # TC-044, TC-045
    from abf_station import azure_preflight
    runner = fake_az(monkeypatch)
    register_agent(ip)
    make_env(ip)
    answered = serve(ip)
    c = last_checks(answered)
    expected = ip.settings.parent.parent / "_personal" / "azure-credentials"
    assert azure_preflight.credentials_path(ip.settings) == expected
    assert c["credential_file"][0] == "fail" and str(expected) in c["credential_file"][1] and "chmod 600" in c["credential_file"][1]
    for name in ("credential_shape", "pool", "storage"):
        assert c[name][0] == "unchecked", name
    assert ip.show("az1")["status"] == "invalid" and runner.calls == []


def test_the_credential_file_location_follows_the_agents_setting(ip, monkeypatch):
    # TC-046, TC-047
    from abf_station import azure_preflight
    custom = ip.tmp / "x"
    monkeypatch.setenv("ABF_STATION_AZURE_CREDENTIALS", str(custom))
    assert azure_preflight.credentials_path(ip.settings) == custom
    monkeypatch.delenv("ABF_STATION_AZURE_CREDENTIALS")
    assert azure_preflight.credentials_path(ip.settings) == ip.settings.parent.parent / "_personal" / "azure-credentials"


@posix_only
def test_a_credential_file_other_people_can_read_is_refused(ip, monkeypatch):
    # TC-048, TC-049
    p = cred_file(ip, monkeypatch, mode=0o644)
    st, detail = by_name(direct(p))["credential_file"]
    assert st == "fail" and "chmod 600" in detail
    p.chmod(0o600)
    assert by_name(direct(p))["credential_file"][0] == "pass"


def test_permission_bits_are_not_checked_on_windows(ip, monkeypatch):
    # TC-050 (runs on every OS: the platform check is switched to Windows)
    from abf_station import azure_preflight
    monkeypatch.setattr(azure_preflight, "sys", SimpleNamespace(platform="win32"))
    st, detail = by_name(direct(cred_file(ip, monkeypatch, mode=0o644)))["credential_file"]
    assert st == "pass" and "Windows 不檢查權限位" in detail


def test_a_credential_file_that_is_a_folder_is_refused(ip):
    # TC-051
    d = ip.tmp / "adir"
    d.mkdir()
    st, detail = by_name(direct(d))["credential_file"]
    assert st == "fail" and "not a regular file" in detail


def test_the_shape_of_the_file_is_judged_without_printing_it(ip, monkeypatch):
    # TC-052, TC-053, TC-054, TC-055, TC-056, TC-057, TC-058, TC-059
    results = []
    # (a) the batch key is missing
    p = cred_file(ip, monkeypatch, "[default]\nstorage_account_key = " + SKEY + "\n")
    res = direct(p)
    st, detail = by_name(res)["credential_shape"]
    assert st == "fail" and "batch_account_key" in detail
    results.append(res)
    # (b) no [default] section, only another one
    p = cred_file(ip, monkeypatch, "[other]\nbatch_account_key = " + BKEY + "\nstorage_account_key = " + SKEY + "\n")
    res = direct(p)
    st, detail = by_name(res)["credential_shape"]
    assert st == "fail" and "沒有 [default] 區段" in detail and str(p) in detail and "other" not in detail.replace(str(p), "")
    results.append(res)
    # (c) no storage key and no sas token
    p = cred_file(ip, monkeypatch, "[default]\nbatch_account_key = " + BKEY + "\n")
    res = direct(p)
    st, detail = by_name(res)["credential_shape"]
    assert st == "fail" and "storage_account_key" in detail and "storage_sas_token" in detail
    results.append(res)
    # (d) only a sas token is enough
    p = cred_file(ip, monkeypatch, SAS_FILE)
    assert by_name(direct(p))["credential_shape"][0] == "pass"
    # (e) random bytes
    p = cred_file(ip, monkeypatch, bytes(range(256)) * 4)
    res = direct(p)
    assert by_name(res)["credential_shape"][0] == "fail"
    results.append(res)
    # a percent-encoded sas token is not an interpolation
    p = cred_file(ip, monkeypatch, "[default]\nbatch_account_key = " + BKEY + "\nstorage_sas_token = " + SAS + "&se=2030-01-01T00%3A00%3A00Z\n")
    assert by_name(direct(p))["credential_shape"][0] == "pass"
    # bigger than 1 MB
    p = cred_file(ip, monkeypatch, CRED_FILE + "# " + "x" * 1100000 + "\n")
    res = direct(p)
    assert by_name(res)["credential_shape"][0] != "pass"
    results.append(res)
    for res in results:
        blob = json.dumps(res)
        assert "MARKER" not in blob and "other" not in blob.replace(str(p), "")
    # the environment's message too
    fake_az(monkeypatch)
    register_agent(ip)
    cred_file(ip, monkeypatch, "[other]\nbatch_account_key = " + BKEY + "\n")
    make_env(ip)
    answered = serve(ip)
    msg = ip.show("az1")["message"]
    assert "MARKER" not in msg and "MARKER" not in json.dumps(answered)
    assert by_name(direct(cred_file(ip, monkeypatch)))["credential_shape"][0] == "pass"


def test_without_the_az_cli_the_api_checks_are_unchecked_and_nothing_is_run(ip, monkeypatch):
    # TC-060, TC-061
    p = cred_file(ip, monkeypatch)
    runner = Fake()
    res = direct(p, runner=runner, which=lambda n: None)
    c = by_name(res)
    assert c["az"][0] == "unchecked" and "install" in c["az"][1].lower()
    for name in ("pool", "storage"):
        assert c[name][0] == "unchecked"
    assert runner.calls == [] and res["ok"] is False
    runner = fake_az(monkeypatch, have=False)
    register_agent(ip)
    make_env(ip)
    serve(ip)
    ce = ip.show("az1")
    assert ce["status"] == "invalid" and "az" in ce["message"] and "沒裝" in ce["message"] and runner.calls == []


def test_all_checks_passing_makes_the_environment_available(ip, monkeypatch):
    # TC-062
    cred_file(ip, monkeypatch)
    fake_az(monkeypatch)
    register_agent(ip)
    make_env(ip)
    c = last_checks(serve(ip))
    assert list(c) == CHECK_NAMES and all(v[0] == "pass" for v in c.values())
    ce = ip.show("az1")
    assert ce["status"] == "available"
    con = sqlite3.connect(str(ip.state_db))
    assert con.execute("SELECT checked_ok FROM compute_envs WHERE name = 'az1'").fetchone()[0] == 1
    con.close()


def test_a_pool_that_is_missing_or_not_active_fails(ip, monkeypatch):
    # TC-063, TC-064, TC-065, TC-066
    p = cred_file(ip, monkeypatch)
    runner = Fake({"batch": (3, "PoolNotFound the specified pool does not exist")})
    st, detail = by_name(direct(p, runner=runner))["pool"]
    assert st == "fail" and POOL in detail
    assert [a[1] for a, _, _ in runner.calls] == ["batch", "storage"]
    assert by_name(direct(p, runner=Fake({"batch": (0, "deleting")})))["pool"][0] == "fail"
    fake_az(monkeypatch, Fake({"batch": (3, "PoolNotFound")}))
    register_agent(ip)
    make_env(ip)
    serve(ip)
    ce = ip.show("az1")
    assert ce["status"] == "invalid" and "pool" in ce["message"]


def test_a_missing_container_fails(ip, monkeypatch):
    # TC-067
    p = cred_file(ip, monkeypatch)
    st, detail = by_name(direct(p, runner=Fake({"storage": (0, "false")})))["storage"]
    assert st == "fail" and "lab-container" in detail


def test_the_booleans_of_az_are_read_in_either_case(ip, monkeypatch):
    # TC-068
    p = cred_file(ip, monkeypatch)
    assert by_name(direct(p, runner=Fake({"storage": (0, "True")})))["storage"][0] == "pass"
    assert by_name(direct(p, runner=Fake({"storage": (0, "False")})))["storage"][0] == "fail"


def test_an_api_failure_is_reported_trimmed_and_scrubbed(ip, monkeypatch):
    # TC-069, TC-070
    p = cred_file(ip, monkeypatch)
    b64 = ("Zk9v" * 22)
    noisy = "AuthorizationFailure " + CONN + " " + b64 + " " + "z" * 1900
    st, detail = by_name(direct(p, runner=Fake({"storage": (1, noisy)})))["storage"]
    assert st == "fail" and len(detail) <= 300 and CONN not in detail and BKEY not in detail and b64 not in detail


def test_a_timeout_fails_that_check_only(ip, monkeypatch):
    # TC-071, TC-072
    p = cred_file(ip, monkeypatch)
    runner = Fake(exc={"batch": TimeoutError("slow")})
    c = by_name(direct(p, runner=runner))
    assert c["pool"][0] == "fail" and "逾時" in c["pool"][1]
    assert c["storage"][0] == "pass"
    assert [a[1] for a, _, _ in runner.calls] == ["batch", "storage"]


def test_the_commands_are_read_only(ip, monkeypatch):
    # TC-073, TC-074, TC-075
    p = cred_file(ip, monkeypatch)
    runner = Fake()
    direct(p, runner=runner, spot=True, maxvCpus=256)
    assert len(runner.calls) == 2
    for argv, env, timeout in runner.calls:
        assert " ".join(argv[:4]) in ("az batch pool show", "az storage container exists")
        words = set()
        for word in argv:
            words.update(re.split(r"[^A-Za-z0-9]+", word.lower()))
        for bad in ("create", "delete", "resize", "update", "upload", "set", "start", "stop", "login", "autoscale", "job",
                    "task", "copy", "remove", "spot", "maxvcpus"):
            assert bad not in words, (bad, argv)
        assert timeout == 30
        assert not [k for k in env if "SPOT" in k.upper() or "MAXVCPU" in k.upper()]
        assert not [v for k, v in env.items() if v == "login"]


def test_the_credential_goes_in_the_environment_not_in_argv(ip, monkeypatch):
    # TC-076, TC-077, TC-078, TC-079, TC-080, TC-081, TC-082, TC-083
    p = cred_file(ip, monkeypatch)
    for k, v in (("AZURE_CLIENT_SECRET", "X"), ("AZURE_STORAGE_KEY", "Y"), ("ABF_PLATFORM_TOKEN", "T")):
        monkeypatch.setenv(k, v)
    runner = Fake()
    direct(p, runner=runner)
    assert len(runner.calls) == 2
    for argv, env, _ in runner.calls:
        assert env["AZURE_BATCH_ACCOUNT"] == BATCH
        assert env["AZURE_BATCH_ENDPOINT"] == "https://labbatch.westeurope.batch.azure.com"
        assert env["AZURE_BATCH_ACCESS_KEY"] == BKEY
        assert env["AZURE_CORE_COLLECT_TELEMETRY"] == "false" and env["AZURE_CORE_NO_COLOR"] == "true"
        assert env["AZURE_CORE_ONLY_SHOW_ERRORS"] == "true"
        for secret in (BKEY, SKEY, SAS, str(p)):
            assert secret not in " ".join(argv)
        assert not [k for k in env if k.startswith("ABF_")]
        assert "AZURE_CLIENT_SECRET" not in env
    storage_env = runner.calls[1][1]
    assert storage_env["AZURE_STORAGE_ACCOUNT"] == STORE and storage_env["AZURE_STORAGE_KEY"] == SKEY
    for d, existed, listing in runner.dirs:       # an empty folder of its own, gone when the check is over
        assert existed and listing == [] and not os.path.exists(d)
    # a sas token instead of a storage key
    runner = Fake()
    direct(cred_file(ip, monkeypatch, SAS_FILE), runner=runner)
    env = runner.calls[1][1]
    assert env["AZURE_STORAGE_SAS_TOKEN"] == SAS and "AZURE_STORAGE_KEY" not in env


def test_the_default_runner_is_a_fixed_argv_without_a_shell(monkeypatch):
    # TC-084
    from abf_station import azure_preflight, site
    seen = {}

    class Done:
        returncode = 3
        stdout = "o" * 900
        stderr = ""

    def fake_run(argv, **kw):
        seen["argv"], seen["kw"] = argv, kw
        return Done()
    monkeypatch.setattr(site.subprocess, "run", fake_run)
    rc, out = azure_preflight._run(["az", "storage", "container", "exists"], {"A": "1"}, 30)
    assert rc == 3 and len(out) <= 300
    assert isinstance(seen["argv"], list) and seen["kw"]["shell"] is False and seen["kw"]["timeout"] == 30


def test_the_agent_judges_the_environment_again_before_it_builds_a_command(ip):
    # TC-085, TC-086, TC-087
    from abf_station import azure_preflight, rules
    for bad in ({"location": "x; touch c"}, {"batchAccountName": "A B"}, {"workDir": "az://lab-container"}, {"pool": "q q"},
                {"credentialsId": "a b"}, {"platform": "slurm-platform"}, {"platform": "awsbatch-platform"}):
        with pytest.raises(rules.Refusal):
            azure_preflight.clean_environment(flat_env(**bad))
    full = flat_env(spot=True, maxvCpus=256, nextflowConfig="process.x = 1")
    assert set(azure_preflight.clean_environment(full)) == {"name", "platform", "credentialsId", "location", "batchAccountName",
                                                            "storageAccountName", "workDir", "pool"}


# ---- US4: wiring and the commands -------------------------------------------------------------------------------------

def test_create_queues_the_first_preflight_for_the_agent(ip):
    # TC-091, TC-092
    register_agent(ip)
    before = jobs_count(ip)
    rc, out = ip.run("ce", "create", "--name", "az1", "--platform", AZ, "--agent", "a1", "--credentials", CRED, "--location", LOC,
                     "--batch-account", BATCH, "--storage-account", STORE, "--work-dir", "az://lab-container/work", "--pool", POOL)
    assert rc == 0 and "preflight queued" in out and jobs_count(ip) == before + 1
    con = sqlite3.connect(str(ip.state_db))
    kind, args = con.execute("SELECT kind, args_json FROM jobs WHERE compute_env = 'az1'").fetchone()
    con.close()
    assert kind == "preflight"
    assert set(json.loads(args)["ce"]) == {"name", "platform", "credentialsId", "location", "batchAccountName",
                                            "storageAccountName", "workDir", "pool"}


def test_create_with_the_agent_offline_says_so_and_does_not_pretend(ip):
    # TC-093
    register_agent(ip, age=100000)
    n = jobs_count(ip)
    out = make_env(ip)
    assert "沒有代理在線" in out and ip.show("az1")["status"] == "creating" and jobs_count(ip) == n


def test_ce_preflight_waits_for_the_agent_and_prints_each_check(ip, auto_serve, monkeypatch):
    # TC-088, TC-094
    cred_file(ip, monkeypatch)
    fake_az(monkeypatch)
    register_agent(ip)
    make_env(ip)
    answered = serve(ip)
    assert [c["name"] for c in answered[-1][2]["checks"]] == CHECK_NAMES
    rc, out = ip.run("ce", "preflight", "az1")
    assert rc == 0 and list(checks_of(out)) == CHECK_NAMES and "status: available" in out


def test_cli_flags(ip):
    # TC-095, TC-096, TC-097, TC-098
    register_agent(ip)
    base = ["ce", "create", "--platform", AZ, "--agent", "a1", "--work-dir", "az://lab-container/work", "--location", LOC,
            "--batch-account", BATCH, "--storage-account", STORE, "--pool", POOL]
    assert ip.run(*base, "--name", "f1", "--spot")[0] == 0
    c = ip.show("f1")["config"]
    assert c["location"] == LOC and c["batchAccountName"] == BATCH and c["storageAccountName"] == STORE
    assert c["pool"] == POOL and c["spot"] is True
    assert ip.run(*base, "--name", "f2", "--no-spot")[0] == 0 and ip.show("f2")["config"]["spot"] is False
    rc, out = ip.run("ce", "create", "--help")
    flat = re.sub(r"\s+", " ", out)
    assert re.search(r"--location \S+ ?Google Batch/Azure Batch: the region", flat) or "Google Batch/Azure Batch: the region" in flat
    assert re.search(r"--spot\s.*?Azure Batch", flat) and re.search(r"--no-spot\s.*?Azure Batch", flat)


def test_slurm_google_batch_and_aws_batch_are_unchanged(ip):
    # TC-099, TC-100, TC-101
    from abf_platform import compute_envs
    register_agent(ip)
    rc, out = ip.create_slurm("s1")
    assert rc == 0 and "preflight queued" in out
    snap = compute_envs.snapshot(compute_envs.get(ip.state_db, "s1"))
    assert set(snap) == {"name", "platform", "workDir", "launchDir", "headQueue", "computeQueue", "readRoots", "modules",
                         "siteConfigVars", "sitePipelines", "singularityLibraryDir"}
    cfg = {"project": "lab-project-1", "location": "europe-west2", "workDir": "gs://lab-bucket/work"}
    rc, out = ip.run("ce", "create", "--name", "g1", "--platform", "googlebatch-platform", "--agent", "a1", "--config-json", json.dumps(cfg))
    assert rc == 0 and "preflight queued" in out
    snap = compute_envs.snapshot(compute_envs.get(ip.state_db, "g1"))
    assert set(snap) == {"name", "platform", "credentialsId", "project", "location", "workDir", "serviceAccountEmail"}
    cfg = {"region": "eu-west-1", "workDir": "s3://lab-bucket/work", "jobQueue": "lab-queue"}
    rc, out = ip.run("ce", "create", "--name", "aws1", "--platform", "awsbatch-platform", "--agent", "a1", "--config-json", json.dumps(cfg))
    assert rc == 0 and "preflight queued" in out
    snap = compute_envs.snapshot(compute_envs.get(ip.state_db, "aws1"))
    assert set(snap) == {"name", "platform", "credentialsId", "region", "workDir", "jobQueue", "spot", "maxvCpus"}
    from abf_station import handlers
    assert handlers.gcb_preflight.TYPE == "googlebatch-platform" and handlers.aws_preflight.TYPE == "awsbatch-platform"


def test_the_type_constants():
    # TC-102 (the same constants are asserted in test_gcb_ce.py)
    from abf_platform import compute_envs
    assert compute_envs.SUPPORTED == "slurm-platform"
    # azure-launch changed this on purpose: Azure Batch can be launched now, so nothing is check-only any more.
    assert compute_envs.PLATFORM_HOST_TYPES == ("googlebatch-platform", "awsbatch-platform", AZ, "k8s-platform")      # k8s-launch
    assert compute_envs.CHECK_ONLY_TYPES == ()      # k8s-launch: nothing is check-only any more
    assert compute_envs.CHECKABLE == (compute_envs.SUPPORTED, "googlebatch-platform", "awsbatch-platform", AZ, "k8s-platform")


# ---- US4: no launching yet ---------------------------------------------------------------------------------------------

def _available_az(ip, name="az1", **top):
    register_agent(ip)
    create(ip, name, **top)
    set_status(ip, name, "available")


def test_jobs_other_than_the_preflight_are_refused_in_plain_words(ip):
    # TC-103, TC-104, TC-149
    from abf_platform import jobs
    _available_az(ip)
    before = jobs_count(ip)
    msgs = []
    # azure-launch changed this on purpose: launch_nextflow, cancel_run and pipeline_files are taken now.
    # azure-upload changed this on purpose: put_upload is taken now (it is queued only through enqueue_put_upload).
    # azure-clean changed this on purpose: clean_work is taken now.
    for kind in ("list_site_files",):
        with pytest.raises(jobs.JobRefused) as e:
            jobs.check_target(ip.state_db, "az1", kind)
        msgs.append(str(e.value))
    with pytest.raises(jobs.JobRefused) as e:
        jobs.enqueue_listing(ip.state_db, "az1", "/x")
    msgs.append(str(e.value))
    for msg in msgs:
        assert "尚未支援" in msg and "Azure Batch" in msg and "AWS" not in msg, msg
    assert jobs_count(ip) == before
    jobs.enqueue_preflight(ip.state_db, "az1")      # the preflight is the one job it takes
    assert jobs_count(ip) == before + 1


def test_launch_is_refused_and_the_environment_is_never_auto_picked(ip):
    # TC-105, TC-106, TC-107
    from abf_launch import build
    _available_az(ip)
    assert build.target_problem(ip.state_db, "az1", "launch_nextflow") is None      # azure-launch: launch is taken now
    assert build.target_problem(ip.state_db, "az1", "clean_work") is None      # azure-clean: clean is taken now
    assert build.primary_environment(ip.state_db) is None
    assert ip.create_slurm("s1")[0] == 0
    set_status(ip, "s1", "available")
    assert build.primary_environment(ip.state_db) == "s1"


def test_another_users_azure_environment_is_not_found(ip):
    # TC-108, TC-109, TC-110
    from abf_platform import compute_envs, jobs
    _available_az(ip, owner_user_id=1)
    before_env, n = compute_envs.get(ip.state_db, "az1"), jobs_count(ip)
    assert compute_envs.get(ip.state_db, "az1", owner=2) is None
    missing = None
    try:
        jobs.enqueue_listing(ip.state_db, "nothing-here", "/x", caller_user_id=2)
    except jobs.JobRefused as e:
        missing = str(e)
    with pytest.raises(jobs.JobRefused) as e:
        jobs.enqueue_listing(ip.state_db, "az1", "/x", caller_user_id=2)
    assert missing is not None and str(e.value).replace("az1", "X") == missing.replace("nothing-here", "X")
    assert "not found" in str(e.value) and "Azure" not in str(e.value)
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(ip.state_db, "az1", "launch_nextflow", caller_user_id=2)
    assert "not found" in str(e.value)
    assert compute_envs.get(ip.state_db, "az1") == before_env and jobs_count(ip) == n


def test_nobody_but_the_local_administrator_can_change_an_azure_environment(ip):
    # TC-110: update and disable are commands of the local administrator only; no tool and no web route reaches them
    from abf_platform import compute_envs, web
    from abf_platform.mcp_server import build_server
    _available_az(ip, owner_user_id=1)
    before = compute_envs.get(ip.state_db, "az1")
    names = {t.name for t in asyncio.run(build_server(str(ip.tmp / "index.db")).list_tools())}
    assert not [n for n in names if re.search(r"update|disable|enable|create_compute|set_primary", n)]
    app = web.create_app(ip.tmp / "index.db", ip.tmp / "tokens.db", ip.tmp / "platform.db")
    assert not [r.path for r in app.routes if re.search(r"compute|/ce\b|disable|update", getattr(r, "path", ""), re.I)]
    assert compute_envs.get(ip.state_db, "az1", owner=2) is None
    assert compute_envs.get(ip.state_db, "az1") == before


def test_updating_a_disabled_environment_queues_no_preflight(ip):
    # TC-111
    register_agent(ip)
    make_env(ip)
    serve(ip)
    assert ip.run("ce", "disable", "az1")[0] == 0
    n = jobs_count(ip)
    rc, out = ip.run("ce", "update", "az1", "--pool", "other")
    assert rc == 0 and ip.show("az1")["config"]["pool"] == "other" and jobs_count(ip) == n


# ---- US5: old records --------------------------------------------------------------------------------------------------

OLD = {"workDir": "az://lab-container/work", "region": LOC, "vmType": "Standard_D4s_v3"}


def _old_row(ip, name="old", config=None):
    from abf_platform import store
    con = store.connect_state(ip.state_db)
    with con:
        con.execute("INSERT INTO compute_envs (name, platform, status, message, is_primary, config_json, created_at, updated_at) "
                    "VALUES (?, 'azbatch-platform', 'unsupported', 'Not supported yet', 0, ?, 1, 1)", (name, json.dumps(config or OLD)))
    con.close()


def test_an_old_azure_record_is_still_listed_and_shown(ip):
    # TC-112
    _old_row(ip)
    assert ip.show("old")["status"] == "unsupported" and "old" in ip.run("ce", "list")[1]


def test_an_old_record_is_refused_with_the_next_step(ip):
    # TC-113, TC-114, TC-149
    _old_row(ip)
    register_agent(ip)
    before = ip.show("old")
    n = jobs_count(ip)
    rc, out = ip.run("ce", "preflight", "old")
    assert rc != 0 and re.search(r"region|vmType", out) and "請刪除後重建這個計算環境" in out and jobs_count(ip) == n
    assert ip.show("old")["status"] == "unsupported"
    rc, out = ip.run("ce", "update", "old", "--agent", "a1", "--pool", POOL)
    assert rc != 0 and re.search(r"region|vmType", out) and "請刪除後重建這個計算環境" in out and ip.show("old") == before


# ---- US6: docs ---------------------------------------------------------------------------------------------------------

def doc(name):
    return (REPO_ROOT / "docs" / name).read_text(encoding="utf-8")


def test_docs_list_every_azure_key_and_check():
    # TC-115, TC-116, TC-117, TC-118, TC-119, TC-120, TC-121, TC-122
    d = doc("PLATFORM.md")
    for key in ("location", "batchAccountName", "storageAccountName", "workDir", "pool", "spot", "maxvCpus") + tuple(CHECK_NAMES):
        assert "`%s`" % key in d, key
    section = d[d.index("Azure Batch"):]
    for word in ("ABF_STATION_AZURE_CREDENTIALS", "_personal/azure-credentials", "[default]", "batch_account_key",
                 "storage_account_key", "storage_sas_token", "預檢不計費", "creates no pool"):
        assert word in d, word
    assert re.search(r"`azbatch-platform` \| Azure Batch \| checked, launched and cleaned on the platform host \(resume: not yet\)", d)
    assert "Slurm, Google Cloud Batch, AWS Batch, Azure Batch and Kubernetes can run; the other nine types can be modelled only" in d and "the other eleven" not in d
    assert re.search(r"user subscription[^\n]*(not supported|本片不支援)", section, re.I) or "user subscription 模式的 Batch 帳號本片不支援" in section
    assert "lowPriority" in section and "az" in section and re.search(r"operator|營運者", section)
    par = doc("SEQERA_PARITY.md")
    row = [ln for ln in par.splitlines() if "`azbatch-platform`" in ln][0]
    assert "Have (create + check + launch + cancel + upload + clean)" in row and row.rstrip().endswith("[ ] |")
    assert "Azure Batch" in par[par.index("## F. Compute environments"):][:1500]
    t = doc("TESTING.md")
    assert "Azure Batch environment (azure-ce-type)" in t
    small = t[t.index("Azure Batch environment (azure-ce-type)"):]
    for word in ("azure-ce-type", "預檢不計費", "git diff", "TC-089", "TC-090", "TC-131", "TC-132"):
        assert word in small, word
    for text in (d, par, t):
        assert "Account" + "Key=" not in text and "sig" + "=" not in text
        assert not re.search(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text, re.I)
        for bad in re.findall(r"az://([A-Za-z0-9.<>-]+)", text):
            assert bad in ("lab-container", "<container>", "container") or bad.startswith("<"), bad


# ---- US7: out of scope and the other types ---------------------------------------------------------------------------

def _sources():
    return list((PLATFORM_DIR / "abf_platform").rglob("*.py")) + list((PLATFORM_DIR / "abf_station").rglob("*.py"))


def test_no_delete_no_azcopy_no_pool_creation_for_azure():
    # TC-123, TC-125, TC-126 (azure-upload: the upload command itself is allowed now; delete, azcopy and pool creation stay barred)
    for f in _sources():
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"az batch job|az batch task|storage blob delete|azcopy|batch pool create|"
                             r"batch pool delete|batch pool resize|storage container create", text), f.name
    assert "-with-tower" not in (PLATFORM_DIR / "abf_station" / "azure_preflight.py").read_text(encoding="utf-8")


def test_the_other_types_stay_unsupported(ip):
    # TC-130
    from abf_platform import compute_envs
    from test_station_envs import UNSUPPORTED
    assert len(UNSUPPORTED) == 9 and AZ not in UNSUPPORTED
    for pid in ("awscloud-platform", "azcloud-platform", "eks-platform", "gke-platform"):
        assert pid in UNSUPPORTED
    for pid, cfg in UNSUPPORTED.items():
        ce = compute_envs.create(ip.state_db, {"name": "x-" + pid, "platform": pid, "config": cfg})
        assert ce["status"] == "unsupported" and "Not supported" in ce["message"], pid


def test_no_cloud_library_is_imported():
    # TC-128
    text = (PLATFORM_DIR / "abf_station" / "azure_preflight.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(boto3|botocore|azure|google|requests)\b", text, re.M)
    toml = (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")
    assert "azure-" not in toml and "boto3" not in toml and "botocore" not in toml


def test_tool_list_unchanged_and_no_new_web_route(tmp_path):
    # TC-129
    from abf_platform import web
    from abf_platform.mcp_server import build_server
    names = {t.name for t in asyncio.run(build_server(str(tmp_path / "index.db")).list_tools())}
    assert names == {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "list_used_pipelines", "read_task_log",
                     "run_outputs", "my_usage", "find_module", "describe_module", "list_pipelines", "get_pipeline", "get_validation", "launch", "cancel", "resume", "relaunch", "forget"}
    app = web.create_app(tmp_path / "index.db", tmp_path / "tokens.db", tmp_path / "platform.db")
    assert not [r.path for r in app.routes if re.search(r"azure|azbatch|blob", getattr(r, "path", ""), re.I)]


def test_the_platform_package_starts_no_program():
    # TC-143
    for f in (PLATFORM_DIR / "abf_platform").rglob("*.py"):
        assert "subprocess" not in f.read_text(encoding="utf-8"), f.name


# ---- the safety net: words, secrets, data shape ----------------------------------------------------------------------

def test_no_new_write_path_for_azure(ip):
    # TC-148
    from abf_platform import jobs
    _available_az(ip)
    for kind in ("list_site_files",):      # azure-clean: clean_work is taken now too; the kinds that azure-launch and azure-upload open are not refused any more
        with pytest.raises(jobs.JobRefused):
            jobs.check_target(ip.state_db, "az1", kind)


def test_every_refusal_says_what_to_do_and_hides_internals(ip, monkeypatch):
    # TC-149, TC-150
    from abf_platform import jobs
    _available_az(ip, "avail")
    msgs = {}
    msgs["agent"] = refused(ip, agent=None)
    assert "--agent" in msgs["agent"]
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(ip.state_db, "avail", "list_site_files")
    msgs["launch"] = str(e.value)
    assert "尚未支援" in msgs["launch"] and "azure-clean" not in msgs["launch"]
    _old_row(ip)
    rc, out = ip.run("ce", "preflight", "old")
    msgs["old"] = out
    assert "請刪除後重建" in out
    runner = fake_az(monkeypatch)
    res = direct(ip.tmp / "nowhere")
    assert "chmod 600" in by_name(res)["credential_file"][1]       # the one message that may name a path
    res2 = direct(cred_file(ip, monkeypatch), which=lambda n: None)
    assert "install" in by_name(res2)["az"][1].lower() or "安裝" in by_name(res2)["az"][1]
    for name, m in msgs.items():
        assert not re.search(r"Traceback|SELECT |INSERT |sqlite", m) and str(ip.tmp) not in m, name
    assert runner.calls == []


def test_no_secret_reaches_the_database_the_jobs_or_the_outputs(ip, monkeypatch):
    # TC-151
    p = cred_file(ip, monkeypatch)
    outs = []
    runner = fake_az(monkeypatch)
    register_agent(ip)
    outs.append(make_env(ip))
    answered = serve(ip)
    outs.append(ip.run("ce", "show", "az1")[1])
    runner.replies["storage"] = (1, "AuthorizationFailure")
    outs.append(ip.run("ce", "update", "az1", "--pool", "lab-pool2")[1])
    answered += serve(ip)
    outs.append(ip.run("ce", "show", "az1")[1])
    con = sqlite3.connect(str(ip.state_db))
    stored = " ".join(str(r) for r in con.execute("SELECT args_json, result_json FROM jobs"))
    con.close()
    blobs = outs + [json.dumps(answered), stored, ip.state_db.read_bytes().decode("latin-1")]
    for blob in blobs:
        for secret in (BKEY, SKEY, "MARKER"):
            assert secret not in blob, secret
    assert p.exists()


def test_no_migration_is_needed(ip):
    # TC-152
    create(ip)
    _old_row(ip)
    con = sqlite3.connect(str(ip.state_db))
    cols = [r[1] for r in con.execute("PRAGMA table_info(compute_envs)")]
    tables = sorted(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'"))
    con.close()
    assert cols == ["id", "name", "description", "platform", "credentials_id", "agent", "status", "message", "is_primary",
                    "checked_ok", "config_json", "created_at", "updated_at", "last_used_at", "owner_user_id"]
    assert tables == ["agents", "compute_envs", "confirmations", "jobs", "launches", "meta", "sqlite_sequence"]
    assert ip.show("old")["status"] == "unsupported"
    assert not [p for p in (PLATFORM_DIR / "abf_platform").rglob("*migration*")]


def test_max_memory_gb_rules(ip):
    # TC-001 TC-002 TC-003 TC-004 TC-005 TC-006 TC-007 TC-008 (maxMemoryGB: one task's memory ceiling, whole GB 1..10000)
    for bad in (0, 10001, True, "8", 1.5):
        assert "maxMemoryGB must be a whole number from 1 to 10000" in refused(ip, good_config(maxMemoryGB=bad)), bad
    assert create(ip, "mm1", good_config(maxMemoryGB=10000))["config"]["maxMemoryGB"] == 10000
    assert create(ip, "mm2", good_config(maxMemoryGB=1))["config"]["maxMemoryGB"] == 1
    assert "maxMemoryGB" not in create(ip, "mm3", good_config())["config"]      # an old environment: unset means unset, no default is filled in


def test_no_other_new_limit_keys_are_taken(ip):
    # TC-061 (no total, no disk, no time limit)
    for key in ("maxDiskGB", "maxTime", "maxTotalMemoryGB"):
        assert "unknown setting" in refused(ip, good_config(**{key: 5})), key
