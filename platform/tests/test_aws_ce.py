# Nothing existing: searched Nextflow's awsbatch executor and Seqera's AWS Batch form; neither ships an offline, free preflight, and the official Python package boto3 is barred by TC-085, so the aws command line is faked here.
"""AWS Batch compute environments (aws-ce-type): create, validate, store, and a preflight that the station agent runs on
the platform host. Launching on AWS is a later task (aws-launch); here it is refused in plain words.

Every test uses a fake aws runner and a fake `which`; nothing touches the network. The TC ids refer to
specs/aws-ce-type/test-case.md. No file written here holds a full AWS key id as one literal: the tests build it from pieces.
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

REGION = "eu-west-1"
BUCKET_URL = "s3://lab-bucket/work/"
QUEUE = "lab-queue"
CRED = "aws-lab"
AWS = "awsbatch-platform"
AKID = "AK" + "IA" + "ABCDEFGHIJKLMNOP"      # built in pieces so that no tracked file holds a key-shaped string
CRED_FILE = "[default]\naws_access_key_id = " + AKID + "\naws_secret_access_key = MARKER" + "SECRET0123456789abcdefghij\n"
ACCOUNT = "1234" + "5678" + "9012"
CHECK_NAMES = ["credential_name", "credential_file", "credential_shape", "aws", "identity", "job_queue", "bucket"]
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="permission bits")


@pytest.fixture
def ip(tmp_path, monkeypatch):
    monkeypatch.delenv("ABF_STATION_AWS_CREDENTIALS", raising=False)
    box = Inproc(tmp_path, monkeypatch)
    box.tmp = tmp_path
    box.settings = tmp_path / "deploy" / "config" / "env.yaml"
    box.settings.parent.mkdir(parents=True)
    box.settings.write_text("reach: local\n")
    return box


# ---- helpers ---------------------------------------------------------------------------------------------------------

def good_config(**extra):
    c = {"region": REGION, "workDir": BUCKET_URL, "jobQueue": QUEUE}
    c.update(extra)
    return c


def register_agent(ip, name="a1", age=0):
    from abf_platform import agents, store
    agents.register(ip.state_db, name, "0.1.0", lambda: time.time() - age)
    store.create_token(ip.tokens, kind="agent", agent_name=name)


def fields(name="aws1", config=None, **top):
    f = {"name": name, "platform": AWS, "agent": "a1", "config": good_config() if config is None else config}
    f.update(top)
    return {k: v for k, v in f.items() if v is not None}


def create(ip, name="aws1", config=None, **top):
    from abf_platform import compute_envs
    return compute_envs.create(ip.state_db, fields(name, config, **top))


def refused(ip, config=None, **top):
    from abf_platform import compute_envs
    with pytest.raises(compute_envs.CEError) as e:
        compute_envs.create(ip.state_db, fields("bad", config, **top))
    return str(e.value)


def cred_file(ip, monkeypatch, content=None, mode=0o600, name="aws-credentials"):
    p = ip.tmp / name
    p.write_bytes((CRED_FILE if content is None else content).encode("utf-8") if isinstance(content, (str, type(None))) else content)
    if sys.platform != "win32":
        p.chmod(mode)
    monkeypatch.setenv("ABF_STATION_AWS_CREDENTIALS", str(p))
    return p


class Fake:
    """A fake aws runner that records every call: sts answers the account, batch says ENABLED, s3api says nothing."""

    def __init__(self, replies=None, exc=None):
        self.replies = {"sts": (0, ACCOUNT), "batch": (0, "ENABLED"), "s3api": (0, "")}
        self.replies.update(replies or {})
        self.exc = exc or {}
        self.calls = []

    def __call__(self, argv, env, timeout):
        self.calls.append((list(argv), dict(env), timeout))
        if argv[1] in self.exc:
            raise self.exc[argv[1]]
        return self.replies[argv[1]]


def fake_aws(monkeypatch, runner=None, have=True):
    from abf_station import aws_preflight
    runner = runner or Fake()
    monkeypatch.setattr(aws_preflight, "_run", runner)
    monkeypatch.setattr(aws_preflight.shutil, "which", lambda n: ("/usr/bin/aws" if have else None) if n == "aws" else None)
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


def make_env(ip, cred=CRED, name="aws1", agent="a1", **cfg):
    argv = ["ce", "create", "--name", name, "--platform", AWS, "--config-json", json.dumps(good_config(**cfg))]
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
    e = {"name": "aws1", "platform": AWS, "credentialsId": CRED, "region": REGION, "workDir": "s3://lab-bucket/work",
         "jobQueue": QUEUE}
    e.update(over)
    return e


def direct(cred, runner=None, which=None, stat=None, **env):
    """The station's run_preflight on a flat environment, with the fakes injected."""
    from abf_station import aws_preflight
    return aws_preflight.run_preflight(flat_env(**env), cred_path=cred, runner=runner or Fake(),
                                       which=which or (lambda n: "/usr/bin/aws"), stat=stat or os.stat)


def by_name(res):
    return {c["name"]: (c["status"], c["detail"]) for c in res["checks"]}


# ---- US1: the settings -----------------------------------------------------------------------------------------------

def test_a_valid_aws_batch_environment_is_created_as_creating(ip):
    # TC-001
    ce = create(ip, config=good_config(spot=True, maxvCpus=256))
    assert ce["status"] == "creating" and "waiting for the first preflight" in ce["message"]
    assert ce["config"]["workDir"] == "s3://lab-bucket/work"
    assert ce["config"]["region"] == REGION and ce["config"]["jobQueue"] == QUEUE


def test_region_workdir_jobqueue_and_agent_are_required(ip):
    # TC-002, TC-003, TC-004, TC-005, TC-006
    for key in ("region", "workDir", "jobQueue"):
        cfg = good_config()
        del cfg[key]
        assert key in refused(ip, cfg)
    assert "需要指定一個站台代理" in refused(ip, agent=None)
    register_agent(ip)
    rc, out = ip.run("ce", "create", "--name", "noagent", "--platform", AWS, "--credentials", CRED,
                     "--config-json", json.dumps(good_config()))
    assert rc != 0 and "agent" in out and ip.rows()["compute_envs"] == []


def test_region_rules(ip):
    # TC-007, TC-008
    for i, good in enumerate(("eu-west-1", "ap-northeast-1", "us-gov-west-1")):
        create(ip, "r%d" % i, good_config(region=good))
    for bad in ("europe-west2", "EU-WEST-1", "eu-west", ""):
        msg = refused(ip, good_config(region=bad))
        assert "region" in msg and "eu-west-1" in msg, bad


def test_workdir_must_be_an_s3_url(ip):
    # TC-009, TC-010
    assert create(ip, "w1", good_config(workDir="s3://lab-bucket/work/"))["config"]["workDir"] == "s3://lab-bucket/work"
    assert create(ip, "w2", good_config(workDir="s3://lab-bucket"))["config"]["workDir"] == "s3://lab-bucket"
    for bad in ("/data/work", "gs://b/x", "s3://", "s3://UPPER/x", "s3://ab/x", "s3://lab-bucket/../x"):
        assert "workDir" in refused(ip, good_config(workDir=bad)), bad


def test_job_queue_is_a_name_not_an_arn(ip):
    # TC-011, TC-012
    for i, good in enumerate(("lab-queue", "Q_1")):
        create(ip, "q%d" % i, good_config(jobQueue=good))
    for bad in ("arn:aws:batch:eu-west-1:" + ACCOUNT + ":job-queue/q", "a b", "q" * 129):
        assert "jobQueue" in refused(ip, good_config(jobQueue=bad)), bad[:30]


def test_spot_and_maxvcpus_rules(ip):
    # TC-013, TC-014, TC-015, TC-016, TC-021
    assert "spot" in refused(ip, good_config(spot="yes"))
    for bad in (0, 10001, True, "8"):
        assert "maxvCpus" in refused(ip, good_config(maxvCpus=bad)), bad
    assert create(ip, "m1", good_config(maxvCpus=10000))["config"]["maxvCpus"] == 10000
    assert create(ip, "m2", good_config(spot=True))["config"]["spot"] is True
    assert create(ip, "m3", good_config(spot=False))["config"]["spot"] is False


def test_unknown_slurm_and_gcb_keys_are_refused(ip):
    # TC-017, TC-096, TC-098
    for key in ("headQueue", "computeQueue", "hostName", "project", "location", "bootDiskSize", "foo",
                "currency", "costCap", "fargate", "forge"):
        msg = refused(ip, good_config(**{key: "x"}))
        assert "unknown setting for an AWS Batch environment" in msg and "known:" in msg and "jobQueue" in msg, key


def test_all_errors_are_listed_at_once_and_values_are_cut(ip):
    # TC-018, TC-019
    msg = refused(ip, {"region": "x" * 200, "workDir": "nope", "jobQueue": "a b"})
    assert "region" in msg and "workDir" in msg and "jobQueue" in msg
    assert "x" * 60 in msg and "x" * 61 not in msg


def test_shared_checks_apply(ip):
    # TC-020
    assert "nextflowConfig" in refused(ip, good_config(nextflowConfig="x" * 20001))
    assert "environment" in refused(ip, good_config(environment=[{"name": "bad name", "value": "1"}]))


# ---- US2: the credential is a name --------------------------------------------------------------------------------------

def test_the_credential_is_only_a_name_at_the_top_level(ip):
    # TC-022
    create(ip, credentialsId=CRED)
    ce = ip.show("aws1")
    assert ce["credentialsId"] == CRED
    assert not [k for k in ce["config"] if re.search(r"cred|key|secret|token", k, re.I)]


def test_credentials_id_is_a_name_only(ip):
    # TC-023
    for bad in ("aws lab", "key=abc", AKID + "=="):
        assert refused(ip, credentialsId=bad), bad


def test_an_access_key_pasted_anywhere_is_refused_and_not_repeated(ip):
    # TC-024, TC-025
    create(ip, "ok")
    cases = [({"description": AKID}, "description"), ({"config": good_config(nextflowConfig=AKID)}, "nextflowConfig"),
             ({"config": good_config(environment=[{"name": "A", "value": AKID}])}, "environment"),
             ({"config": good_config(workDir="s3://lab-bucket/" + AKID)}, "workDir")]
    for top, where in cases:
        msg = refused(ip, top.pop("config", None), **top)
        assert where in msg and AKID not in msg and AKID[:8] not in msg, where
    assert AKID.encode() not in ip.state_db.read_bytes()


def test_a_secret_key_line_pasted_anywhere_is_refused(ip):
    # TC-026
    assert "preRunScript" in refused(ip, good_config(preRunScript="aws_secret_access_key = x"))


def test_a_key_named_field_is_refused(ip):
    # TC-027
    for key in ("awsSecretAccessKey", "accessKey", "sessionToken"):
        assert key in refused(ip, good_config(**{key: "x"})), key


def test_the_platform_does_not_read_the_credential_file(ip, monkeypatch):
    # TC-028
    p = cred_file(ip, monkeypatch)
    register_agent(ip)
    outs = [make_env(ip), ip.run("ce", "list")[1], ip.run("ce", "show", "aws1")[1]]
    assert p.exists()
    assert b"MARKERSECRET" not in ip.state_db.read_bytes() and AKID.encode() not in ip.state_db.read_bytes()
    for out in outs:
        assert "MARKERSECRET" not in out and AKID not in out
    for f in (PLATFORM_DIR / "abf_platform").rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert "aws-credentials" not in text and "AWS_CREDENTIALS" not in text, f.name


# ---- US3: the preflight on the agent -----------------------------------------------------------------------------------

def test_every_check_is_reported_with_name_status_and_detail(ip, monkeypatch):
    # TC-029, TC-021
    p = cred_file(ip, monkeypatch)
    res = direct(p)
    assert [c["name"] for c in res["checks"]] == CHECK_NAMES and res["ok"] is True
    assert all(set(c) == {"name", "status", "detail"} for c in res["checks"])


def test_a_missing_credential_name_is_a_failure(ip, monkeypatch):
    # TC-030
    c = by_name(direct(cred_file(ip, monkeypatch), credentialsId=None))
    assert c["credential_name"][0] == "fail" and c["credential_shape"][0] == "unchecked"
    assert "profile" not in c["credential_name"][1].lower()


def test_a_missing_credential_file_says_where_to_put_it(ip, monkeypatch):
    # TC-031, TC-032
    from abf_station import aws_preflight
    runner = fake_aws(monkeypatch)
    register_agent(ip)
    make_env(ip)
    answered = serve(ip)
    c = last_checks(answered)
    expected = ip.settings.parent.parent / "_personal" / "aws-credentials"
    assert aws_preflight.credentials_path(ip.settings) == expected
    assert c["credential_file"][0] == "fail" and str(expected) in c["credential_file"][1] and "chmod 600" in c["credential_file"][1]
    for name in ("credential_shape", "identity", "job_queue", "bucket"):
        assert c[name][0] == "unchecked", name
    assert ip.show("aws1")["status"] == "invalid" and runner.calls == []


def test_the_credential_file_location_follows_the_agents_setting(ip, monkeypatch):
    # TC-033
    from abf_station import aws_preflight
    custom = ip.tmp / "x"
    monkeypatch.setenv("ABF_STATION_AWS_CREDENTIALS", str(custom))
    assert aws_preflight.credentials_path(ip.settings) == custom
    monkeypatch.delenv("ABF_STATION_AWS_CREDENTIALS")
    assert aws_preflight.credentials_path(ip.settings) == ip.settings.parent.parent / "_personal" / "aws-credentials"


@posix_only
def test_a_credential_file_other_people_can_read_is_refused(ip, monkeypatch):
    # TC-034, TC-035
    p = cred_file(ip, monkeypatch, mode=0o644)
    st, detail = by_name(direct(p))["credential_file"]
    assert st == "fail" and "chmod 600" in detail
    p.chmod(0o600)
    assert by_name(direct(p))["credential_file"][0] == "pass"


def test_permission_bits_are_not_checked_on_windows(ip, monkeypatch):
    # TC-036 (runs on every OS: the platform check is switched to Windows)
    from abf_station import aws_preflight
    monkeypatch.setattr(aws_preflight, "sys", SimpleNamespace(platform="win32"))
    st, detail = by_name(direct(cred_file(ip, monkeypatch, mode=0o644)))["credential_file"]
    assert st == "pass" and "Windows 不檢查權限位" in detail


def test_a_credential_file_that_is_a_folder_is_refused(ip):
    # TC-037
    d = ip.tmp / "adir"
    d.mkdir()
    st, detail = by_name(direct(d))["credential_file"]
    assert st == "fail" and "not a regular file" in detail


def test_the_shape_of_the_file_is_judged_without_printing_it(ip, monkeypatch):
    # TC-038, TC-039, TC-040, TC-041, TC-042, TC-043
    results = []
    # (a) the secret key is missing
    p = cred_file(ip, monkeypatch, "[default]\naws_access_key_id = " + AKID + "\n")
    res = direct(p)
    st, detail = by_name(res)["credential_shape"]
    assert st == "fail" and "aws_secret_access_key" in detail
    results.append(res)
    # (b) no [default] section, only another one
    p = cred_file(ip, monkeypatch, "[other]\naws_access_key_id = " + AKID + "\naws_secret_access_key = MARKER" + "SECRET0123456789abcdefghij\n")
    res = direct(p)
    st, detail = by_name(res)["credential_shape"]
    assert st == "fail" and "憑證檔沒有 [default] 區段" in detail and "other" not in detail
    results.append(res)
    # (c) random bytes
    p = cred_file(ip, monkeypatch, bytes(range(256)) * 4)
    res = direct(p)
    assert by_name(res)["credential_shape"][0] == "fail"
    results.append(res)
    # (d) credential_process
    p = cred_file(ip, monkeypatch, CRED_FILE + "credential_process = /bin/x\n")
    res = direct(p)
    st, detail = by_name(res)["credential_shape"]
    assert st == "fail" and "credential_process" in detail
    results.append(res)
    # (e) bigger than 1 MB
    p = cred_file(ip, monkeypatch, CRED_FILE + "# " + "x" * 1100000 + "\n")
    res = direct(p)
    assert by_name(res)["credential_shape"][0] == "fail"
    results.append(res)
    for res in results:
        blob = json.dumps(res)
        assert AKID not in blob and "MARKERSECRET" not in blob and "other" not in blob
    # the environment's message too
    fake_aws(monkeypatch)
    register_agent(ip)
    cred_file(ip, monkeypatch, "[other]\naws_access_key_id = " + AKID + "\n")
    make_env(ip)
    answered = serve(ip)
    msg = ip.show("aws1")["message"]
    assert AKID not in msg and "MARKERSECRET" not in msg and AKID not in json.dumps(answered)
    assert by_name(direct(cred_file(ip, monkeypatch)))["credential_shape"][0] == "pass"


def test_without_the_aws_cli_the_api_checks_are_unchecked_and_nothing_is_run(ip, monkeypatch):
    # TC-044
    p = cred_file(ip, monkeypatch)
    runner = Fake()
    res = direct(p, runner=runner, which=lambda n: None)
    c = by_name(res)
    assert c["aws"][0] == "unchecked"
    for name in ("identity", "job_queue", "bucket"):
        assert c[name][0] == "unchecked"
    assert runner.calls == [] and res["ok"] is False
    runner = fake_aws(monkeypatch, have=False)
    register_agent(ip)
    make_env(ip)
    serve(ip)
    ce = ip.show("aws1")
    assert ce["status"] == "invalid" and "aws" in ce["message"] and "沒裝" in ce["message"] and runner.calls == []


def test_all_checks_passing_makes_the_environment_available(ip, monkeypatch):
    # TC-045, TC-046
    cred_file(ip, monkeypatch)
    fake_aws(monkeypatch)
    register_agent(ip)
    make_env(ip)
    c = last_checks(serve(ip))
    assert list(c) == CHECK_NAMES and all(v[0] == "pass" for v in c.values())
    assert ACCOUNT not in c["identity"][1] and "the key answered" in c["identity"][1]
    ce = ip.show("aws1")
    assert ce["status"] == "available"
    con = sqlite3.connect(str(ip.state_db))
    assert con.execute("SELECT checked_ok FROM compute_envs WHERE name = 'aws1'").fetchone()[0] == 1
    con.close()


def test_a_failing_identity_query_is_reported(ip, monkeypatch):
    # TC-047
    p = cred_file(ip, monkeypatch)
    res = direct(p, runner=Fake({"sts": (255, "InvalidClientTokenId " + "z" * 600 + " " + AKID)}))
    st, detail = by_name(res)["identity"]
    assert st == "fail" and len(detail) <= 300 and AKID not in detail and res["ok"] is False


def test_a_job_queue_that_does_not_exist_or_is_disabled_fails(ip, monkeypatch):
    # TC-048, TC-049
    p = cred_file(ip, monkeypatch)
    st, detail = by_name(direct(p, runner=Fake({"batch": (0, "")})))["job_queue"]
    assert st == "fail" and QUEUE in detail
    assert by_name(direct(p, runner=Fake({"batch": (0, "DISABLED")})))["job_queue"][0] == "fail"


def test_an_api_failure_is_reported_trimmed_and_scrubbed(ip, monkeypatch):
    # TC-050
    p = cred_file(ip, monkeypatch)
    token = "q8Zr" * 10
    noisy = "AccessDenied " + AKID + " " + token + " " + "z" * 1900
    st, detail = by_name(direct(p, runner=Fake({"s3api": (255, noisy)})))["bucket"]
    assert st == "fail" and len(detail) <= 300 and AKID not in detail and token not in detail


def test_a_timeout_fails_that_check_only(ip, monkeypatch):
    # TC-051
    p = cred_file(ip, monkeypatch)
    runner = Fake(exc={"sts": TimeoutError("slow")})
    c = by_name(direct(p, runner=runner))
    assert c["identity"][0] == "fail" and "逾時" in c["identity"][1]
    assert c["job_queue"][0] == "pass" and c["bucket"][0] == "pass"
    assert [a[1] for a, _, _ in runner.calls] == ["sts", "batch", "s3api"]


def test_the_commands_are_read_only(ip, monkeypatch):
    # TC-052, TC-053, TC-102, TC-021
    p = cred_file(ip, monkeypatch)
    runner = Fake()
    direct(p, runner=runner, spot=True, maxvCpus=256)
    assert len(runner.calls) == 3
    for argv, env, timeout in runner.calls:
        assert " ".join(argv[:3]) in ("aws sts get-caller-identity", "aws batch describe-job-queues", "aws s3api head-bucket")
        for word in argv:
            for bad in ("create", "submit", "delete", "put", "cp", "rm", "mb", "terminate", "register", "update", "cancel"):
                assert word != bad and not word.startswith(bad + "-"), (bad, argv)
        assert not [w for w in argv if w in ("sso", "assume-role", "--profile", "describe-compute-environments")]
        assert timeout == 30


def test_the_credential_goes_in_the_environment_not_in_argv(ip, monkeypatch):
    # TC-054, TC-055, TC-056
    p = cred_file(ip, monkeypatch)
    for k, v in (("AWS_ACCESS_KEY_ID", "X"), ("AWS_SECRET_ACCESS_KEY", "Y"), ("AWS_SESSION_TOKEN", "Z"), ("ABF_PLATFORM_TOKEN", "T")):
        monkeypatch.setenv(k, v)
    runner = Fake()
    direct(p, runner=runner)
    assert runner.calls
    for argv, env, _ in runner.calls:
        assert env["AWS_SHARED_CREDENTIALS_FILE"] == str(p) and env["AWS_PROFILE"] == "default"
        assert env["AWS_DEFAULT_REGION"] == REGION and env["AWS_CONFIG_FILE"] == os.devnull
        assert env["AWS_EC2_METADATA_DISABLED"] == "true"
        assert str(p) not in " ".join(argv)
        assert not [k for k in env if k.startswith("ABF_")]
        for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
            assert k not in env


def test_the_default_runner_is_a_fixed_argv_without_a_shell(monkeypatch):
    # TC-057
    from abf_station import aws_preflight, site
    seen = {}

    class Done:
        returncode = 3
        stdout = "o" * 900
        stderr = ""

    def fake_run(argv, **kw):
        seen["argv"], seen["kw"] = argv, kw
        return Done()
    monkeypatch.setattr(site.subprocess, "run", fake_run)
    rc, out = aws_preflight._run(["aws", "s3api", "head-bucket"], {"A": "1"}, 30)
    assert rc == 3 and len(out) <= 300
    assert isinstance(seen["argv"], list) and seen["kw"]["shell"] is False and seen["kw"]["timeout"] == 30


def test_the_agent_judges_the_environment_again_before_it_builds_a_command(ip):
    # TC-058, TC-059, TC-060
    from abf_station import aws_preflight, rules
    for bad in ({"region": "x; touch c"}, {"workDir": "s3://b/x"}, {"jobQueue": "q q"}, {"credentialsId": "a b"},
                {"platform": "slurm-platform"}):
        with pytest.raises(rules.Refusal):
            aws_preflight.clean_environment(flat_env(**bad))
    full = flat_env(spot=True, maxvCpus=256, nextflowConfig="process.x = 1")
    assert set(aws_preflight.clean_environment(full)) == {"name", "platform", "credentialsId", "region", "workDir", "jobQueue"}


# ---- US4: wiring and the commands -------------------------------------------------------------------------------------

def test_create_queues_the_first_preflight_for_the_agent(ip):
    # TC-062, TC-063
    register_agent(ip)
    before = jobs_count(ip)
    rc, out = ip.run("ce", "create", "--name", "aws1", "--platform", AWS, "--agent", "a1", "--credentials", CRED, "--region", REGION,
                     "--work-dir", "s3://lab-bucket/work", "--job-queue", QUEUE)
    assert rc == 0 and "preflight queued" in out and jobs_count(ip) == before + 1
    con = sqlite3.connect(str(ip.state_db))
    kind, args = con.execute("SELECT kind, args_json FROM jobs WHERE compute_env = 'aws1'").fetchone()
    con.close()
    assert kind == "preflight"
    # aws-launch added spot and maxvCpus to what an agent is told (the launch needs them)
    assert set(json.loads(args)["ce"]) == {"name", "platform", "credentialsId", "region", "workDir", "jobQueue", "spot", "maxvCpus"}


def test_create_with_the_agent_offline_says_so_and_does_not_pretend(ip):
    # TC-064
    register_agent(ip, age=100000)
    n = jobs_count(ip)
    out = make_env(ip)
    assert "沒有代理在線" in out and ip.show("aws1")["status"] == "creating" and jobs_count(ip) == n


def test_ce_preflight_waits_for_the_agent_and_prints_each_check(ip, auto_serve, monkeypatch):
    # TC-065
    cred_file(ip, monkeypatch)
    fake_aws(monkeypatch)
    register_agent(ip)
    make_env(ip)
    serve(ip)
    rc, out = ip.run("ce", "preflight", "aws1")
    assert rc == 0 and list(checks_of(out)) == CHECK_NAMES and "status: available" in out


def test_cli_flags(ip):
    # TC-066, TC-067, TC-068
    register_agent(ip)
    base = ["ce", "create", "--platform", AWS, "--agent", "a1", "--work-dir", "s3://lab-bucket/work", "--region", REGION,
            "--job-queue", QUEUE]
    assert ip.run(*base, "--name", "f1", "--spot")[0] == 0
    c = ip.show("f1")["config"]
    assert c["region"] == REGION and c["jobQueue"] == QUEUE and c["spot"] is True
    assert ip.run(*base, "--name", "f2", "--no-spot")[0] == 0 and ip.show("f2")["config"]["spot"] is False
    rc, out = ip.run("ce", "create", "--help")
    assert "Google Batch/AWS Batch" in re.sub(r"\s+", "", out).replace("Google Batch", "Google Batch") or "Google Batch／AWS Batch" in out \
        or re.search(r"Google Batch\s*/\s*AWS Batch", out)


def test_slurm_and_google_batch_are_unchanged(ip):
    # TC-069, TC-070
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
    from abf_station import handlers
    assert handlers.gcb_preflight.TYPE == "googlebatch-platform"


# ---- US4: no launching yet ---------------------------------------------------------------------------------------------

def _available_aws(ip, name="aws1", **top):
    register_agent(ip)
    create(ip, name, **top)
    set_status(ip, name, "available")


def test_jobs_other_than_the_preflight_are_refused_in_plain_words(ip):
    # TC-072, TC-073
    from abf_platform import jobs
    _available_aws(ip)
    before = jobs_count(ip)
    msgs = []
    # aws-launch: launch_nextflow, cancel_run and pipeline_files are taken now; the rest stays refused
    for kind in ("launch_nextflow", "cancel_run", "pipeline_files"):
        jobs.check_target(ip.state_db, "aws1", kind)
    for kind in ("list_site_files",):      # aws-upload: put_upload is taken now; aws-clean: clean_work too
        with pytest.raises(jobs.JobRefused) as e:
            jobs.check_target(ip.state_db, "aws1", kind)
        msgs.append(str(e.value))
    with pytest.raises(jobs.JobRefused) as e:
        jobs.enqueue_listing(ip.state_db, "aws1", "/x")
    msgs.append(str(e.value))
    for msg in msgs:
        assert "尚未支援" in msg and "aws-upload" not in msg and "aws-clean" not in msg and "set one with" not in msg, msg
    assert jobs_count(ip) == before
    jobs.enqueue_preflight(ip.state_db, "aws1")      # the preflight is the one job it takes
    assert jobs_count(ip) == before + 1


def test_launch_is_refused_and_the_environment_is_never_auto_picked(ip):
    # TC-074, TC-075, TC-076, TC-077
    from abf_launch import build
    _available_aws(ip)
    assert build.target_problem(ip.state_db, "aws1", "launch_nextflow") is None      # aws-launch: it can be launched now
    assert build.primary_environment(ip.state_db) is None
    rc, out = ip.run("ce", "primary", "aws1")
    assert rc == 0 and ip.show("aws1")["primary"] is True
    assert build.primary_environment(ip.state_db) is None
    assert ip.create_slurm("s1")[0] == 0
    set_status(ip, "s1", "available")
    con = sqlite3.connect(str(ip.state_db))
    with con:
        con.execute("UPDATE compute_envs SET is_primary = 0")
    con.close()
    assert build.primary_environment(ip.state_db) == "s1"


def test_another_users_aws_environment_is_not_found(ip):
    # TC-078, TC-079
    from abf_platform import compute_envs, jobs
    _available_aws(ip, owner_user_id=1)
    before_env, n = compute_envs.get(ip.state_db, "aws1"), jobs_count(ip)
    assert compute_envs.get(ip.state_db, "aws1", owner=2) is None
    missing = None
    try:
        jobs.enqueue_listing(ip.state_db, "nothing-here", "/x", caller_user_id=2)
    except jobs.JobRefused as e:
        missing = str(e)
    for call in (lambda: jobs.enqueue_listing(ip.state_db, "aws1", "/x", caller_user_id=2),
                 lambda: jobs.check_target(ip.state_db, "aws1", "launch_nextflow", caller_user_id=2)):
        with pytest.raises(jobs.JobRefused) as e:
            call()
        assert "not found" in str(e.value) and "AWS" not in str(e.value)
    assert missing is None or "not found" in missing
    assert compute_envs.get(ip.state_db, "aws1") == before_env and jobs_count(ip) == n


def test_nobody_but_the_local_administrator_can_change_an_aws_environment(ip):
    # TC-080: update and disable are commands of the local administrator only; no tool and no web route reaches them
    from abf_platform import compute_envs, web
    from abf_platform.mcp_server import build_server
    _available_aws(ip, owner_user_id=1)
    before = compute_envs.get(ip.state_db, "aws1")
    names = {t.name for t in asyncio.run(build_server(str(ip.tmp / "index.db")).list_tools())}
    assert not [n for n in names if re.search(r"update|disable|enable|create_compute|set_primary", n)]
    app = web.create_app(ip.tmp / "index.db", ip.tmp / "tokens.db", ip.tmp / "platform.db")
    assert not [r.path for r in app.routes if re.search(r"compute|/ce\b|disable|update", getattr(r, "path", ""), re.I)]
    assert compute_envs.get(ip.state_db, "aws1", owner=2) is None
    assert compute_envs.get(ip.state_db, "aws1") == before


def test_updating_a_disabled_environment_queues_no_preflight(ip):
    # TC-081
    register_agent(ip)
    make_env(ip)
    serve(ip)
    assert ip.run("ce", "disable", "aws1")[0] == 0
    n = jobs_count(ip)
    rc, out = ip.run("ce", "update", "aws1", "--job-queue", "other")
    assert rc == 0 and ip.show("aws1")["config"]["jobQueue"] == "other" and jobs_count(ip) == n


# ---- US5: old records --------------------------------------------------------------------------------------------------

def _old_row(ip, name="old", config=None):
    from abf_platform import store
    cfg = config or {"workDir": "s3://lab-bucket/work", "region": REGION, "headQueue": "head-q", "computeQueue": "comp-q"}
    con = store.connect_state(ip.state_db)
    with con:
        con.execute("INSERT INTO compute_envs (name, platform, status, message, is_primary, config_json, created_at, updated_at) "
                    "VALUES (?, 'awsbatch-platform', 'unsupported', 'Not supported yet', 0, ?, 1, 1)", (name, json.dumps(cfg)))
    con.close()


def test_an_old_aws_record_is_still_listed_and_shown(ip):
    # TC-082
    _old_row(ip)
    assert ip.show("old")["status"] == "unsupported" and "old" in ip.run("ce", "list")[1]


def test_an_old_record_must_be_deleted_and_rebuilt(ip):
    # TC-083, TC-084, TC-085
    _old_row(ip)
    _old_row(ip, "old2", {"workDir": "s3://lab-bucket/work", "region": REGION, "jobQueue": QUEUE, "computeQueue": "comp-q"})
    register_agent(ip)
    before = ip.show("old")
    n = jobs_count(ip)
    rc, out = ip.run("ce", "preflight", "old")
    assert rc != 0 and "headQueue" in out and "請刪除後重建這個計算環境" in out and jobs_count(ip) == n
    rc, out = ip.run("ce", "preflight", "old2")
    assert rc != 0 and "computeQueue" in out and "請刪除後重建這個計算環境" in out
    rc, out = ip.run("ce", "update", "old", "--agent", "a1", "--job-queue", QUEUE)
    assert rc != 0 and "headQueue" in out and "請刪除後重建這個計算環境" in out and ip.show("old") == before


def test_an_old_record_that_is_completed_becomes_creating(ip):
    # TC-086
    _old_row(ip, config={"workDir": "s3://lab-bucket/work", "region": REGION})
    register_agent(ip)
    rc, out = ip.run("ce", "update", "old", "--agent", "a1", "--credentials", CRED, "--job-queue", QUEUE)
    assert rc == 0, out
    assert ip.show("old")["status"] == "creating" and "preflight queued" in out and jobs_count(ip) == 1


# ---- US7: out of scope and the other types ---------------------------------------------------------------------------

def test_no_launch_cost_or_upload_code_for_aws():
    # TC-095, TC-097, TC-098
    for f in list((PLATFORM_DIR / "abf_platform").rglob("*.py")) + list((PLATFORM_DIR / "abf_station").rglob("*.py")):
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"batch submit-job|s3 cp|s3 sync|s3 rm|s3api create-bucket|batch create-|iam create-", text), f.name
    assert "-with-tower" not in (PLATFORM_DIR / "abf_station" / "aws_preflight.py").read_text(encoding="utf-8")


def test_the_other_types_stay_unsupported(ip):
    # TC-100
    from abf_platform import compute_envs
    from test_station_envs import UNSUPPORTED
    assert len(UNSUPPORTED) == 9 and AWS not in UNSUPPORTED
    for pid in ("awscloud-platform", "eks-platform", "azcloud-platform"):
        assert pid in UNSUPPORTED
    for pid, cfg in UNSUPPORTED.items():
        ce = compute_envs.create(ip.state_db, {"name": "x-" + pid, "platform": pid, "config": cfg})
        assert ce["status"] == "unsupported" and "Not supported" in ce["message"], pid


def test_no_cloud_library_is_imported():
    # TC-101
    text = (PLATFORM_DIR / "abf_station" / "aws_preflight.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(boto3|botocore|azure|google|requests)\b", text, re.M)
    toml = (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")
    assert "boto3" not in toml and "botocore" not in toml


def test_tool_list_unchanged_and_no_new_web_route(tmp_path):
    # TC-099
    from abf_platform import web
    from abf_platform.mcp_server import build_server
    names = {t.name for t in asyncio.run(build_server(str(tmp_path / "index.db")).list_tools())}
    assert names == {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "list_used_pipelines", "read_task_log",
                     "run_outputs", "my_usage", "launch", "cancel", "resume", "relaunch", "forget"}
    app = web.create_app(tmp_path / "index.db", tmp_path / "tokens.db", tmp_path / "platform.db")
    assert not [r.path for r in app.routes if re.search(r"aws|s3|batch", getattr(r, "path", ""), re.I) and r.path not in {"/upload", "/upload/{batch}"}]      # web-upload-page: only the two routes this task registered are exempt (ruling 25)


def test_the_platform_package_starts_no_program():
    # TC-105
    for f in (PLATFORM_DIR / "abf_platform").rglob("*.py"):
        assert "subprocess" not in f.read_text(encoding="utf-8"), f.name


def test_no_new_write_path_for_aws(ip):
    # TC-110
    from abf_platform import jobs
    _available_aws(ip)
    for kind in ("launch_nextflow", "cancel_run"):      # aws-launch: the two writes that are built, each behind a confirmation
        jobs.check_target(ip.state_db, "aws1", kind)
    jobs.check_target(ip.state_db, "aws1", "put_upload")      # aws-upload: allowed; its only exit is site.start_fed / site.run_fixed
    jobs.check_target(ip.state_db, "aws1", "clean_work")      # aws-clean: allowed; its only exit is site.run_fixed in the agent
    with pytest.raises(jobs.JobRefused):
        jobs.check_target(ip.state_db, "aws1", "list_site_files")


# ---- the safety net: words, secrets, data shape ----------------------------------------------------------------------

def test_every_refusal_says_what_to_do_and_hides_internals(ip, monkeypatch):
    # TC-111, TC-112
    from abf_platform import jobs
    _available_aws(ip, "avail")
    msgs = {}
    msgs["agent"] = refused(ip, agent=None)
    assert "--agent" in msgs["agent"]
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(ip.state_db, "avail", "list_site_files")
    msgs["launch"] = str(e.value)
    assert "尚未支援" in msgs["launch"] and "aws-clean" not in msgs["launch"]
    _old_row(ip)
    rc, out = ip.run("ce", "preflight", "old")
    msgs["old"] = out
    assert "請刪除後重建" in out
    runner = fake_aws(monkeypatch)
    res = direct(ip.tmp / "nowhere")
    assert "chmod 600" in by_name(res)["credential_file"][1]       # the one message that may name a path
    res2 = direct(cred_file(ip, monkeypatch), which=lambda n: None)
    assert "install" in by_name(res2)["aws"][1].lower() or "安裝" in by_name(res2)["aws"][1]
    for name, m in msgs.items():
        assert not re.search(r"Traceback|SELECT |INSERT |sqlite", m) and str(ip.tmp) not in m, name
    assert runner.calls == []


def test_no_secret_reaches_the_database_the_jobs_or_the_outputs(ip, monkeypatch):
    # TC-113
    p = cred_file(ip, monkeypatch)
    outs = []
    runner = fake_aws(monkeypatch)
    register_agent(ip)
    outs.append(make_env(ip))
    answered = serve(ip)
    outs.append(ip.run("ce", "show", "aws1")[1])
    runner.replies["s3api"] = (255, "AccessDenied")
    outs.append(ip.run("ce", "update", "aws1", "--job-queue", "lab-queue2")[1])
    answered += serve(ip)
    outs.append(ip.run("ce", "show", "aws1")[1])
    con = sqlite3.connect(str(ip.state_db))
    stored = " ".join(str(r) for r in con.execute("SELECT args_json, result_json FROM jobs"))
    con.close()
    blobs = outs + [json.dumps(answered), stored, ip.state_db.read_bytes().decode("latin-1")]
    for blob in blobs:
        for secret in (AKID, "MARKERSECRET", ACCOUNT):
            assert secret not in blob, secret
    assert p.exists()


def test_no_migration_is_needed(ip):
    # TC-114
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


# ---- constants and docs ----------------------------------------------------------------------------------------------

def test_the_type_constants():
    # TC-071 (the same constants are asserted in test_gcb_ce.py)
    from abf_platform import compute_envs
    assert compute_envs.SUPPORTED == "slurm-platform"
    # aws-launch changed this on purpose: before, PLATFORM_HOST_TYPES == ("googlebatch-platform",) and CHECK_ONLY_TYPES == (AWS,)
    assert compute_envs.PLATFORM_HOST_TYPES == ("googlebatch-platform", AWS, "azbatch-platform")      # azure-launch
    # azure-ce-type changed this on purpose: Azure Batch is the one check-only type now.
    assert compute_envs.CHECK_ONLY_TYPES == ("k8s-platform",)      # k8s-ce
    assert compute_envs.CHECKABLE == (compute_envs.SUPPORTED, "googlebatch-platform", AWS, "azbatch-platform", "k8s-platform")


def doc(name):
    return (REPO_ROOT / "docs" / name).read_text(encoding="utf-8")


def test_docs_list_every_aws_key_and_check():
    # TC-087, TC-088, TC-089, TC-090, TC-091, TC-092, TC-094
    d = doc("PLATFORM.md")
    for key in ("region", "workDir", "jobQueue", "spot", "maxvCpus") + tuple(CHECK_NAMES):
        assert "`%s`" % key in d, key
    assert "ABF_STATION_AWS_CREDENTIALS" in d and "_personal/aws-credentials" in d
    assert "預檢不計費" in d and "creates no Batch job" in d
    # aws-launch changed these statements on purpose (plan A9 d): AWS Batch can be launched now
    assert re.search(r"`awsbatch-platform` \| AWS Batch \| checked and launched on the platform host \(upload, clean, resume: not yet\)", d)
    assert "Slurm, Google Cloud Batch, AWS Batch and Azure Batch can run; Kubernetes can be created and checked on the platform host (launch: not yet); the other nine types can be modelled only" in d
    assert "[default]" in d and not re.search(r"credentialsId[^.\n]*profile (name|名)", d)
    assert "headQueue" in d and "computeQueue" in d and "請刪除後重建" in d
    par = doc("SEQERA_PARITY.md")
    row = [ln for ln in par.splitlines() if "`awsbatch-platform`" in ln][0]
    assert "Have (create + check + launch + cancel + upload + clean)" in row and row.rstrip().endswith("[ ] |")
    t = doc("TESTING.md")
    assert "aws-ce-type" in t and "預檢不計費" in t and "git diff" in t
    for text in (d, par, t):
        assert not re.search(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", text)
        assert not [m for m in re.findall(r"\b\d{12}\b", text) if m != ACCOUNT]
        for bad in re.findall(r"s3://([A-Za-z0-9.-]+)", text):
            assert bad in ("lab-bucket", "<bucket>", "bucket"), bad


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


def test_slurm_takes_no_max_memory_gb_and_the_agent_snapshot_is_unchanged(ip):
    # TC-060, TC-062, TC-069
    from abf_platform import compute_envs
    with pytest.raises(compute_envs.CEError) as e:
        compute_envs.create(ip.state_db, {"name": "s9", "platform": "slurm-platform", "agent": "a1",
                                          "config": {"workDir": "/x/work", "maxMemoryGB": 8}})
    assert "unknown setting for a Slurm environment" in str(e.value) and "Traceback" not in str(e.value)
    create(ip, "snap1", good_config(maxMemoryGB=6))
    snap = compute_envs.snapshot(compute_envs.get(ip.state_db, "snap1"))
    assert set(snap) == {"name", "platform", "credentialsId", "region", "workDir", "jobQueue", "spot", "maxvCpus"}
