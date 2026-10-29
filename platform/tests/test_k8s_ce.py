# Nothing existing: searched Nextflow's k8s executor and Seqera's Kubernetes form; neither ships an offline, free preflight, and the python client package is barred by TC-085, so kubectl is faked here.
"""Kubernetes compute environments (k8s-ce): create, validate, store, and a read-only preflight that the station agent runs
on the platform host. Launching on Kubernetes is a later task (k8s-launch); here it is refused in plain words.

Every test uses a fake kubectl runner and a fake `which`; nothing touches the network or a cluster. The TC ids refer to
specs/k8s-ce/test-case.md. No file written here holds a full login string as one literal: the tests build them from pieces.
"""
import asyncio
import json
import logging
import os
import re
import sqlite3
import sys
import time
from types import SimpleNamespace

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from station_harness import Inproc

CTX = "lab-context"
NS = "lab-ns"
PVC = "lab-pvc"
MOUNT = "/workspace"
WORKDIR = "/workspace/work"
SA = "lab-sa"
CRED = "k8s-lab"
K8S = "k8s-platform"
KTOK = "MARKER" + "KUBETOK" + "A" * 40                        # built in pieces so that no tracked file holds a login-shaped string
KCFG = "apiVersion: v1\nkind: Config\nusers:\n- user:\n    " + "to" + "ken: " + KTOK + "\n"
CHECK_NAMES = ["credential_name", "credential_file", "kubectl", "context", "pvc", "pvc_access", "service_account"]
SNAP_KEYS = {"name", "platform", "credentialsId", "context", "namespace", "storageClaimName", "storageMountPath", "workDir",
             "serviceAccount"}
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="permission bits")


@pytest.fixture
def ip(tmp_path, monkeypatch):
    monkeypatch.delenv("ABF_STATION_KUBECONFIG", raising=False)
    box = Inproc(tmp_path, monkeypatch)
    box.tmp = tmp_path
    box.settings = tmp_path / "deploy" / "config" / "env.yaml"
    box.settings.parent.mkdir(parents=True)
    box.settings.write_text("reach: local\n")
    return box


# ---- helpers ---------------------------------------------------------------------------------------------------------

def good_config(**extra):
    c = {"context": CTX, "namespace": NS, "storageClaimName": PVC, "workDir": WORKDIR}
    c.update(extra)
    return c


def register_agent(ip, name="a1", age=0):
    from abf_platform import agents, store
    agents.register(ip.state_db, name, "0.1.0", lambda: time.time() - age)
    store.create_token(ip.tokens, kind="agent", agent_name=name)


def fields(name="k1", config=None, **top):
    f = {"name": name, "platform": K8S, "agent": "a1", "config": good_config() if config is None else config}
    f.update(top)
    return {k: v for k, v in f.items() if v is not None}


def create(ip, name="k1", config=None, **top):
    from abf_platform import compute_envs
    return compute_envs.create(ip.state_db, fields(name, config, **top))


def refused(ip, config=None, **top):
    from abf_platform import compute_envs
    with pytest.raises(compute_envs.CEError) as e:
        compute_envs.create(ip.state_db, fields("bad", config, **top))
    return str(e.value)


def kube_file(ip, monkeypatch, content=None, mode=0o600, name="kubeconfig"):
    p = ip.tmp / name
    p.write_bytes((KCFG if content is None else content).encode("utf-8") if isinstance(content, (str, type(None))) else content)
    if sys.platform != "win32":
        p.chmod(mode)
    monkeypatch.setenv("ABF_STATION_KUBECONFIG", str(p))
    return p


def kind_of(argv):
    if argv[1] == "config":
        return "contexts"
    if argv[1] == "get" and argv[2] == "serviceaccount":
        return "sa"
    if argv[1] == "get" and argv[2] == "pvc":
        return "modes" if any("accessModes" in a for a in argv) else "phase"
    return "other"


class Fake:
    """A fake kubectl runner that records every call (argv, the environment, the cache folder as it was at that moment)."""

    def __init__(self, replies=None, exc=None):
        self.replies = {"contexts": (0, CTX + "\nother"), "phase": (0, "Bound"), "modes": (0, "ReadWriteMany"),
                        "sa": (0, "serviceaccount/" + SA)}
        self.replies.update(replies or {})
        self.exc = exc or {}
        self.calls = []
        self.dirs = []

    def __call__(self, argv, env, timeout):
        self.calls.append((list(argv), dict(env), timeout))
        d = env.get("KUBECACHEDIR")
        self.dirs.append((d, os.path.isdir(d) if d else False, os.listdir(d) if d and os.path.isdir(d) else None))
        k = kind_of(argv)
        if k in self.exc:
            raise self.exc[k]
        return self.replies[k]

    def kinds(self):
        return [kind_of(a) for a, _, _ in self.calls]


def fake_kubectl(monkeypatch, runner=None, have=True):
    from abf_station import k8s_preflight
    runner = runner or Fake()
    monkeypatch.setattr(k8s_preflight, "_run", runner)
    monkeypatch.setattr(k8s_preflight.shutil, "which", lambda n: ("/usr/bin/kubectl" if have else None) if n == "kubectl" else None)
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


def make_env(ip, cred=CRED, name="k1", agent="a1", **cfg):
    argv = ["ce", "create", "--name", name, "--platform", K8S, "--config-json", json.dumps(good_config(**cfg))]
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
    e = {"name": "k1", "platform": K8S, "credentialsId": CRED, "context": CTX, "namespace": NS, "storageClaimName": PVC,
         "storageMountPath": MOUNT, "workDir": WORKDIR, "serviceAccount": None}
    e.update(over)
    return e


def direct(cred, runner=None, which=None, stat=None, **env):
    """The station's run_preflight on a flat environment, with the fakes injected."""
    from abf_station import k8s_preflight
    return k8s_preflight.run_preflight(flat_env(**env), cred_path=cred, runner=runner or Fake(),
                                       which=which or (lambda n: "/usr/bin/kubectl"), stat=stat or os.stat)


def by_name(res):
    return {c["name"]: (c["status"], c["detail"]) for c in res["checks"]}


# ---- US1: the settings -----------------------------------------------------------------------------------------------

def test_a_valid_k8s_environment_is_created_as_creating(ip):
    # TC-001, TC-002, TC-003, TC-004
    ce = create(ip, config=good_config(serviceAccount=SA, workDir="/workspace/work/"))
    assert ce["status"] == "creating" and "waiting for the first preflight" in ce["message"]
    assert ce["config"]["storageMountPath"] == "/workspace"
    assert ce["config"]["workDir"] == WORKDIR
    assert ce["config"]["serviceAccount"] == SA
    assert ce["config"]["context"] == CTX and ce["config"]["namespace"] == NS and ce["config"]["storageClaimName"] == PVC


def test_required_settings_and_agent(ip):
    # TC-005, TC-006, TC-007, TC-008, TC-009, TC-010
    for key in ("context", "namespace", "storageClaimName", "workDir"):
        cfg = good_config()
        del cfg[key]
        assert key in refused(ip, cfg), key
    msg = refused(ip, agent=None)
    assert "需要指定一個站台代理" in msg and "--agent" in msg
    register_agent(ip)
    rc, out = ip.run("ce", "create", "--name", "noagent", "--platform", K8S, "--credentials", CRED,
                     "--config-json", json.dumps(good_config()))
    assert rc != 0 and "agent" in out and ip.rows()["compute_envs"] == []


def test_context_rules(ip):
    # TC-011, TC-012
    eks = "arn:aws:eks:eu-west-1:" + "123456789012" + ":cluster/x"
    for i, good in enumerate((CTX, "gke_proj_zone_name", eks, "user@cluster.local")):
        create(ip, "c%d" % i, good_config(context=good))
    for bad in ("", "a b", "a; b", "-x", "a\nb"):
        assert "context" in refused(ip, good_config(context=bad)), repr(bad)


def test_namespace_and_names_follow_dns_rules(ip):
    # TC-013, TC-014, TC-015, TC-016
    create(ip, "n0", good_config(namespace="lab-ns"))
    for bad in ("Lab", "-a", "a-", "a" * 64, "a_b"):
        assert "namespace" in refused(ip, good_config(namespace=bad)), bad
    for key in ("storageClaimName", "serviceAccount"):
        for i, good in enumerate(("lab-pvc", "a.b-c", "a" * 64, "a" * 253)):
            create(ip, "%s%d" % (key[:3], i), good_config(**{key: good}))
        for bad in ("Lab", "-a", "a-", "a_b", "a" * 254):
            assert key in refused(ip, good_config(**{key: bad})), (key, bad)


def test_workdir_must_be_inside_the_mount(ip):
    # TC-017, TC-018, TC-019, TC-020, TC-021, TC-022, TC-023, TC-024, TC-025
    for i, good in enumerate(("/workspace/work", "/workspace/a/b/")):
        create(ip, "w%d" % i, good_config(workDir=good))
    for bad in ("/workspace", "/data/work", "work", "s3://b/x", "/workspace/../x", "/workspace/a\nb", "/workspace2/work"):
        assert "workDir" in refused(ip, good_config(workDir=bad)), repr(bad)
    ce = create(ip, "m1", good_config(storageMountPath="/mnt/vol", workDir="/mnt/vol/w"))
    assert ce["config"]["storageMountPath"] == "/mnt/vol"
    assert "workDir" in refused(ip, good_config(storageMountPath="/mnt/vol", workDir="/workspace/w"))
    assert "storageMountPath" in refused(ip, good_config(storageMountPath="mnt"))


def test_unknown_keys_are_refused(ip):
    # TC-026, TC-027, TC-139
    for key in ("spot", "maxvCpus", "region", "cluster", "foo", "storageSubPath", "podOptions", "fusion"):
        msg = refused(ip, good_config(**{key: "x"}))
        assert "unknown setting for a Kubernetes environment" in msg and "known:" in msg and "storageClaimName" in msg, key


def test_all_errors_are_listed_at_once_and_values_are_cut(ip):
    # TC-028, TC-029
    msg = refused(ip, good_config(context="x" * 300, namespace="A B", workDir="nope"))
    assert "context" in msg and "namespace" in msg and "workDir" in msg
    assert "x" * 60 in msg and "x" * 61 not in msg


def test_shared_checks_apply(ip):
    # TC-030, TC-031
    assert "nextflowConfig" in refused(ip, good_config(nextflowConfig="x" * 20001))
    assert "environment" in refused(ip, good_config(environment=[{"name": "bad name", "value": "1"}]))


def test_create_without_credentials_is_allowed(ip, monkeypatch):
    # TC-032, TC-033
    ce = create(ip)
    assert ce["status"] == "creating" and ce["credentialsId"] is None
    register_agent(ip)
    kube_file(ip, monkeypatch)
    fake_kubectl(monkeypatch)
    make_env(ip, cred=None, name="k2")
    c = last_checks(serve(ip))
    assert c["credential_name"][0] == "fail"
    assert ip.show("k2")["status"] == "invalid"


# ---- US2: the credential is a name --------------------------------------------------------------------------------------

def test_the_credential_is_only_a_name(ip):
    # TC-034, TC-035, TC-036
    create(ip, credentialsId=CRED)
    ce = ip.show("k1")
    assert ce["credentialsId"] == CRED
    assert set(ce["config"]) <= {"context", "namespace", "storageClaimName", "storageMountPath", "workDir", "serviceAccount"}
    assert not [k for k in ce["config"] if re.search(r"cred|key|secret|token", k, re.I)]
    # a string that holds KTOK: written as a token assignment (the way it would be pasted from a kubeconfig); refused, and
    # the refusal never repeats it. A bare KTOK is only letters and digits, so it is shaped like a legal name (see ledger).
    for bad in ("k8s lab", "key=abc", "to" + "ken: " + KTOK):
        msg = refused(ip, credentialsId=bad)
        assert msg and KTOK not in msg, bad


def test_a_kubeconfig_pasted_anywhere_is_refused_and_not_repeated(ip):
    # TC-037, TC-038, TC-039, TC-040
    create(ip, "ok")
    cases = [({"description": KCFG}, "description"), ({"config": good_config(nextflowConfig=KCFG)}, "nextflowConfig"),
             ({"config": good_config(environment=[{"name": "A", "value": KCFG}])}, "environment")]
    for top, where in cases:
        msg = refused(ip, top.pop("config", None), **top)
        assert where in msg and KTOK not in msg and "MARKER" not in msg, where
    assert KTOK.encode() not in ip.state_db.read_bytes()


def test_a_key_named_field_is_refused(ip):
    # TC-041
    for key in ("token", "clientKey", "password"):
        msg = refused(ip, good_config(**{key: "x"}))
        assert key in msg and "unknown setting" not in msg, (key, msg)


def test_normal_values_are_not_mistaken_for_secrets(ip):
    # TC-042
    assert create(ip)["status"] == "creating"
    assert create(ip, "d1", description="a context for the lab, token-free")["status"] == "creating"


def test_the_platform_does_not_read_the_kubeconfig(ip, monkeypatch):
    # TC-043, TC-044
    p = ip.settings.parent.parent / "_personal" / "kubeconfig"
    p.parent.mkdir(parents=True)
    p.write_text(KCFG)
    register_agent(ip)
    outs = [make_env(ip), ip.run("ce", "list")[1], ip.run("ce", "show", "k1")[1]]
    assert p.exists()
    assert KTOK.encode() not in ip.state_db.read_bytes()
    for out in outs:
        assert "MARKER" not in out
    for f in (PLATFORM_DIR / "abf_platform").rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert "ABF_STATION_KUBECONFIG" not in text and "_personal" not in text or f.name == "x", f.name


# ---- US3: the preflight on the agent -----------------------------------------------------------------------------------

def test_every_check_is_reported_in_order(ip, monkeypatch):
    # TC-046
    p = kube_file(ip, monkeypatch)
    res = direct(p)
    assert [c["name"] for c in res["checks"]] == CHECK_NAMES and res["ok"] is True
    assert all(set(c) == {"name", "status", "detail"} for c in res["checks"])


def test_a_missing_credential_file_says_where_to_put_it(ip, monkeypatch):
    # TC-047, TC-048
    from abf_station import k8s_preflight
    runner = fake_kubectl(monkeypatch)
    register_agent(ip)
    make_env(ip)
    c = last_checks(serve(ip))
    expected = ip.settings.parent.parent / "_personal" / "kubeconfig"
    assert k8s_preflight.credentials_path(ip.settings) == expected
    assert c["credential_file"][0] == "fail" and str(expected) in c["credential_file"][1] and "chmod 600" in c["credential_file"][1]
    for name in ("context", "pvc", "pvc_access", "service_account"):
        assert c[name][0] == "unchecked", name
    assert ip.show("k1")["status"] == "invalid" and runner.calls == []


def test_the_kubeconfig_location_follows_the_agents_setting(ip, monkeypatch):
    # TC-049, TC-050
    from abf_station import k8s_preflight
    custom = ip.tmp / "x"
    monkeypatch.setenv("ABF_STATION_KUBECONFIG", str(custom))
    assert k8s_preflight.credentials_path(ip.settings) == custom
    monkeypatch.delenv("ABF_STATION_KUBECONFIG")
    assert k8s_preflight.credentials_path(ip.settings) == ip.settings.parent.parent / "_personal" / "kubeconfig"


@posix_only
def test_a_kubeconfig_other_people_can_read_is_refused(ip, monkeypatch):
    # TC-051, TC-052, TC-141
    p = kube_file(ip, monkeypatch, mode=0o644)
    st, detail = by_name(direct(p))["credential_file"]
    assert st == "fail" and "chmod 600" in detail
    p.chmod(0o600)
    assert by_name(direct(p))["credential_file"][0] == "pass"
    p.write_text("this is not yaml: [ {\n")       # the content is never read by the agent
    p.chmod(0o600)
    assert by_name(direct(p))["credential_file"][0] == "pass"


def test_permission_bits_are_not_checked_on_windows(ip, monkeypatch):
    # TC-053 (runs on every OS: the platform check is switched to Windows)
    from abf_station import k8s_preflight
    monkeypatch.setattr(k8s_preflight, "sys", SimpleNamespace(platform="win32"))
    st, detail = by_name(direct(kube_file(ip, monkeypatch, mode=0o644)))["credential_file"]
    assert st == "pass" and "Windows 不檢查權限位" in detail


def test_a_kubeconfig_that_is_a_folder_or_too_big_is_refused(ip, monkeypatch):
    # TC-054, TC-055
    d = ip.tmp / "adir"
    d.mkdir()
    st, detail = by_name(direct(d))["credential_file"]
    assert st == "fail" and "not a regular file" in detail
    runner = Fake()
    big = kube_file(ip, monkeypatch, b"a" * 1000001)
    res = by_name(direct(big, runner=runner))
    assert res["credential_file"][0] != "pass"
    for name in ("context", "pvc", "pvc_access", "service_account"):
        assert res[name][0] == "unchecked", name
    assert runner.calls == []


def test_without_kubectl_nothing_is_run(ip, monkeypatch):
    # TC-056, TC-057
    p = kube_file(ip, monkeypatch)
    runner = Fake()
    res = direct(p, runner=runner, which=lambda n: None)
    c = by_name(res)
    assert c["kubectl"][0] == "unchecked"
    for name in ("context", "pvc", "pvc_access", "service_account"):
        assert c[name][0] == "unchecked"
    assert runner.calls == [] and res["ok"] is False
    runner = fake_kubectl(monkeypatch, have=False)
    register_agent(ip)
    make_env(ip)
    serve(ip)
    ce = ip.show("k1")
    assert ce["status"] == "invalid" and "kubectl" in ce["message"] and "沒裝" in ce["message"] and runner.calls == []


def test_all_checks_passing_makes_the_environment_available(ip, monkeypatch):
    # TC-058, TC-059
    kube_file(ip, monkeypatch)
    fake_kubectl(monkeypatch)
    register_agent(ip)
    make_env(ip, serviceAccount=SA)
    c = last_checks(serve(ip))
    assert list(c) == CHECK_NAMES and all(v[0] == "pass" for v in c.values())
    assert ip.show("k1")["status"] == "available"


def test_a_context_that_is_not_in_the_file_fails_without_listing_the_others(ip, monkeypatch):
    # TC-060, TC-061, TC-062
    p = kube_file(ip, monkeypatch)
    runner = Fake({"contexts": (0, "prod-cluster\nother")})
    res = direct(p, runner=runner, serviceAccount=SA)
    c = by_name(res)
    assert c["context"][0] == "fail" and CTX in c["context"][1]
    assert "prod-cluster" not in json.dumps(res) and "other" not in c["context"][1]
    for name in ("pvc", "pvc_access", "service_account"):
        assert c[name][0] == "unchecked", name
    assert runner.kinds() == ["contexts"]


def test_a_context_is_matched_as_a_whole_line(ip, monkeypatch):
    # TC-063, TC-064
    p = kube_file(ip, monkeypatch)
    assert by_name(direct(p, runner=Fake({"contexts": (0, CTX + "-2")})))["context"][0] == "fail"
    assert by_name(direct(p, runner=Fake({"contexts": (0, "x\n  " + CTX + "  \ny")})))["context"][0] == "pass"


def test_a_pvc_that_is_missing_or_not_bound_fails(ip, monkeypatch):
    # TC-065, TC-066, TC-067, TC-068
    p = kube_file(ip, monkeypatch)
    runner = Fake({"phase": (1, 'Error from server (NotFound): persistentvolumeclaims "x" not found')})
    c = by_name(direct(p, runner=runner))
    assert c["pvc"][0] == "fail" and PVC in c["pvc"][1] and c["pvc_access"][0] == "unchecked"
    for phase in ("Pending", "Lost"):
        c = by_name(direct(p, runner=Fake({"phase": (0, phase)})))
        assert c["pvc"][0] == "fail" and c["pvc_access"][0] == "unchecked", phase


def test_a_pvc_without_readwritemany_fails_and_says_why(ip, monkeypatch):
    # TC-069, TC-070
    p = kube_file(ip, monkeypatch)
    st, detail = by_name(direct(p, runner=Fake({"modes": (0, "ReadWriteOnce")})))["pvc_access"]
    assert st == "fail" and "ReadWriteMany" in detail
    assert by_name(direct(p, runner=Fake({"modes": (0, "ReadWriteOnce ReadWriteMany")})))["pvc_access"][0] == "pass"


def test_the_service_account_is_checked_only_when_set(ip, monkeypatch):
    # TC-071, TC-072
    p = kube_file(ip, monkeypatch)
    runner = Fake()
    st, detail = by_name(direct(p, runner=runner))["service_account"]
    assert st == "pass" and "未設定，使用命名空間預設帳號" in detail and "sa" not in runner.kinds()
    runner = Fake({"sa": (1, "NotFound")})
    st, detail = by_name(direct(p, runner=runner, serviceAccount=SA))["service_account"]
    assert st == "fail" and SA in detail


def test_an_api_failure_is_reported_trimmed_and_scrubbed(ip, monkeypatch):
    # TC-073, TC-074
    p = kube_file(ip, monkeypatch)
    bearer = "Bearer " + "Zk9v" * 20
    noisy = "Unauthorized " + KTOK + " " + bearer + " " + "z" * 1900
    st, detail = by_name(direct(p, runner=Fake({"phase": (1, noisy)})))["pvc"]
    assert st == "fail" and len(detail) <= 300 and KTOK not in detail and bearer not in detail and "Zk9v" * 20 not in detail


def test_a_timeout_fails_that_check_only(ip, monkeypatch):
    # TC-075, TC-076, TC-077
    p = kube_file(ip, monkeypatch)
    runner = Fake(exc={"phase": TimeoutError("slow")})
    c = by_name(direct(p, runner=runner, serviceAccount=SA))
    assert c["pvc"][0] == "fail" and "逾時" in c["pvc"][1]
    assert c["pvc_access"][0] == "unchecked" and c["service_account"][0] == "pass"
    assert runner.kinds() == ["contexts", "phase", "sa"]
    runner = Fake(exc={"contexts": TimeoutError("slow")})
    c = by_name(direct(p, runner=runner, serviceAccount=SA))
    assert c["context"][0] == "fail" and "逾時" in c["context"][1]
    for name in ("pvc", "pvc_access", "service_account"):
        assert c[name][0] == "unchecked", name
    assert runner.kinds() == ["contexts"]


READ_ONLY_PREFIXES = (["kubectl", "config", "get-contexts"], ["kubectl", "get", "pvc"], ["kubectl", "get", "serviceaccount"])
BARRED_WORDS = ("create", "delete", "apply", "patch", "replace", "edit", "exec", "run", "cp", "scale", "drain", "cordon", "taint",
                "label", "annotate", "attach", "rollout", "logs", "certificate", "auth", "proxy", "can")
BARRED_TOKENS = ("port-forward", "use-context", "set-context", "set-credentials", "can-i")


def test_the_commands_are_read_only(ip, monkeypatch):
    # TC-078, TC-079, TC-140
    p = kube_file(ip, monkeypatch)
    runner = Fake()
    direct(p, runner=runner, serviceAccount=SA)
    assert runner.kinds() == ["contexts", "phase", "modes", "sa"]
    for argv, env, timeout in runner.calls:
        assert argv[:3] in READ_ONLY_PREFIXES, argv
        words = set()
        for word in argv:
            words.update(re.split(r"[^A-Za-z0-9]+", word.lower()))
            assert word.lower() not in BARRED_TOKENS, argv
        for bad in BARRED_WORDS:
            assert bad not in words, (bad, argv)
        assert timeout == 30


def test_the_kubeconfig_goes_in_the_environment_not_in_argv(ip, monkeypatch):
    # TC-080, TC-081, TC-082, TC-083, TC-084, TC-085
    p = kube_file(ip, monkeypatch)
    for k, v in (("KUBECONFIG", "X"), ("KUBE_FAKE_HOST", "Y"), ("ABF_PLATFORM_TOKEN", "T")):
        monkeypatch.setenv(k, v)
    runner = Fake()
    direct(p, runner=runner, serviceAccount=SA)
    assert len(runner.calls) == 4
    for argv, env, _ in runner.calls:
        assert env["KUBECONFIG"] == str(p) and env["KUBECACHEDIR"]
        assert "KUBE_FAKE_HOST" not in env and "T" not in [v for k, v in env.items() if k.startswith("ABF_")]
        assert not [k for k in env if k.startswith("ABF_")]
        assert "X" not in env.values() and "Y" not in env.values() and "T" not in env.values()
        joined = " ".join(argv)
        assert str(p) not in joined and KTOK not in joined
        if argv[1] == "get":
            assert ("--context %s" % CTX) in joined or ("--context=%s" % CTX) in joined
            assert ("--namespace %s" % NS) in joined or ("--namespace=%s" % NS) in joined
            assert "--request-timeout" in joined
    for d, existed, listing in runner.dirs:       # an empty folder of its own, gone when the check is over
        assert existed and listing == [] and not os.path.exists(d)


def test_the_default_runner_is_a_fixed_argv_without_a_shell(monkeypatch):
    # TC-086
    from abf_station import k8s_preflight, site
    seen = {}

    class Done:
        returncode = 3
        stdout = "o" * 900
        stderr = ""

    def fake_run(argv, **kw):
        seen["argv"], seen["kw"] = argv, kw
        return Done()
    monkeypatch.setattr(site.subprocess, "run", fake_run)
    rc, out = k8s_preflight._run(["kubectl", "get", "pvc", "x"], {"A": "1"}, 30)
    assert rc == 3 and len(out) <= 300
    assert isinstance(seen["argv"], list) and seen["kw"]["shell"] is False and seen["kw"]["timeout"] == 30


def test_the_agent_judges_the_environment_again_before_it_builds_a_command(ip):
    # TC-087, TC-088, TC-089
    from abf_station import k8s_preflight, rules
    for bad in ({"context": "x; touch c"}, {"namespace": "A B"}, {"storageClaimName": "q q"}, {"workDir": "/etc/x"},
                {"credentialsId": "a b"}, {"platform": "slurm-platform"}, {"platform": "azbatch-platform"}):
        with pytest.raises(rules.Refusal):
            k8s_preflight.clean_environment(flat_env(**bad))
    full = flat_env(foo="bar", nextflowConfig="process.x = 1")
    assert set(k8s_preflight.clean_environment(full)) <= SNAP_KEYS
    assert "foo" not in k8s_preflight.clean_environment(full)


def test_no_secret_in_the_result_or_in_the_log(ip, monkeypatch, caplog, capsys):
    # TC-090, TC-091
    p = kube_file(ip, monkeypatch)
    with caplog.at_level(logging.DEBUG):
        res = direct(p)
        res2 = direct(p, runner=Fake({"phase": (1, "denied " + KTOK)}))
    assert KTOK not in json.dumps(res) and KTOK not in json.dumps(res2)
    out = capsys.readouterr()
    assert KTOK not in caplog.text and KTOK not in out.out and KTOK not in out.err


# ---- US4: wiring and the commands -------------------------------------------------------------------------------------

def test_create_queues_the_first_preflight_for_the_agent(ip):
    # TC-092, TC-093, TC-137
    register_agent(ip)
    before = jobs_count(ip)
    rc, out = ip.run("ce", "create", "--name", "k1", "--platform", K8S, "--agent", "a1", "--credentials", CRED, "--context", CTX,
                     "--namespace", NS, "--storage-claim", PVC, "--work-dir", WORKDIR)
    assert rc == 0 and "preflight queued" in out and jobs_count(ip) == before + 1
    con = sqlite3.connect(str(ip.state_db))
    kind, args = con.execute("SELECT kind, args_json FROM jobs WHERE compute_env = 'k1'").fetchone()
    con.close()
    assert kind == "preflight"
    ce = json.loads(args)["ce"]
    assert set(ce) == SNAP_KEYS
    assert not [k for k in ce if re.search(r"cost|price|budget|currency|usd", k, re.I)]


def test_create_with_the_agent_offline_says_so(ip):
    # TC-094
    register_agent(ip, age=100000)
    n = jobs_count(ip)
    out = make_env(ip)
    assert "沒有代理在線" in out and ip.show("k1")["status"] == "creating" and jobs_count(ip) == n


def test_ce_preflight_prints_each_check(ip, auto_serve, monkeypatch):
    # TC-095
    kube_file(ip, monkeypatch)
    fake_kubectl(monkeypatch)
    register_agent(ip)
    make_env(ip)
    serve(ip)
    rc, out = ip.run("ce", "preflight", "k1")
    assert rc == 0 and list(checks_of(out)) == CHECK_NAMES and "status: available" in out


def test_cli_flags(ip):
    # TC-096, TC-097
    register_agent(ip)
    rc, out = ip.run("ce", "create", "--name", "f1", "--platform", K8S, "--agent", "a1", "--work-dir", "/mnt/vol/w", "--context", CTX,
                     "--namespace", NS, "--storage-claim", PVC, "--storage-mount-path", "/mnt/vol", "--service-account", SA)
    assert rc == 0, out
    c = ip.show("f1")["config"]
    assert (c["context"], c["namespace"], c["storageClaimName"], c["storageMountPath"], c["serviceAccount"]) == (CTX, NS, PVC, "/mnt/vol", SA)
    rc, out = ip.run("ce", "create", "--help")
    flat = re.sub(r"\s+", " ", out)
    for flag in ("--context", "--namespace", "--storage-claim", "--storage-mount-path", "--service-account"):
        assert flag in flat, flag
    from abf_platform import cli

    def walk(parser):
        for x in parser._actions:
            yield x
            if isinstance(getattr(x, "choices", None), dict):
                for child in x.choices.values():
                    yield from walk(child)
    ce_actions = list(walk(cli.build_parser()))
    k8s_flags = {"--context", "--namespace", "--storage-claim", "--storage-mount-path", "--service-account"}
    helps = [x.help or "" for x in ce_actions if set(x.option_strings) & k8s_flags]
    assert helps and not [h for h in helps if re.search(r"\b(launch|submit|cancel)\b", h, re.I)]


def test_the_agent_checks_a_k8s_job_with_the_k8s_preflight(ip, monkeypatch):
    # TC-098
    from abf_station import rules
    kube_file(ip, monkeypatch)
    fake_kubectl(monkeypatch)

    def never(*a, **k):
        raise AssertionError("the Slurm path was taken for a Kubernetes environment")
    monkeypatch.setattr(rules, "clean_environment", never)
    register_agent(ip)
    make_env(ip)
    answered = serve(ip)
    assert answered and answered[-1][1] == "done" and list(last_checks(answered)) == CHECK_NAMES


def test_other_types_are_unchanged(ip):
    # TC-099, TC-100
    from abf_platform import compute_envs
    register_agent(ip)
    rc, out = ip.create_slurm("s1")
    assert rc == 0 and "preflight queued" in out
    snap = compute_envs.snapshot(compute_envs.get(ip.state_db, "s1"))
    assert set(snap) == {"name", "platform", "workDir", "launchDir", "headQueue", "computeQueue", "readRoots", "modules",
                         "siteConfigVars", "sitePipelines", "singularityLibraryDir"}
    cfg = {"project": "lab-project-1", "location": "europe-west2", "workDir": "gs://lab-bucket/work"}
    assert ip.run("ce", "create", "--name", "g1", "--platform", "googlebatch-platform", "--agent", "a1", "--config-json", json.dumps(cfg))[0] == 0
    assert set(compute_envs.snapshot(compute_envs.get(ip.state_db, "g1"))) == {
        "name", "platform", "credentialsId", "project", "location", "workDir", "serviceAccountEmail"}
    cfg = {"region": "eu-west-1", "workDir": "s3://lab-bucket/work", "jobQueue": "lab-queue"}
    assert ip.run("ce", "create", "--name", "aws1", "--platform", "awsbatch-platform", "--agent", "a1", "--config-json", json.dumps(cfg))[0] == 0
    assert set(compute_envs.snapshot(compute_envs.get(ip.state_db, "aws1"))) == {
        "name", "platform", "credentialsId", "region", "workDir", "jobQueue", "spot", "maxvCpus"}
    cfg = {"location": "westeurope", "batchAccountName": "labbatch", "storageAccountName": "labstore",
           "workDir": "az://lab-container/work", "pool": "lab-pool"}
    assert ip.run("ce", "create", "--name", "az1", "--platform", "azbatch-platform", "--agent", "a1", "--config-json", json.dumps(cfg))[0] == 0
    assert set(compute_envs.snapshot(compute_envs.get(ip.state_db, "az1"))) == {
        "name", "platform", "credentialsId", "location", "batchAccountName", "storageAccountName", "workDir", "pool"}
    assert compute_envs.PLATFORM_HOST_TYPES == ("googlebatch-platform", "awsbatch-platform", "azbatch-platform")
    assert K8S not in compute_envs.CLOUD_JOB_KINDS and len(compute_envs.CLOUD_JOB_KINDS) == 3
    assert compute_envs.CHECK_ONLY_TYPES == (K8S,)


def _available_k8s(ip, name="k1", **top):
    register_agent(ip)
    create(ip, name, **top)
    set_status(ip, name, "available")


def test_jobs_other_than_the_preflight_are_refused_in_plain_words(ip):
    # TC-101, TC-102, TC-103, TC-104, TC-136
    from abf_platform import jobs
    _available_k8s(ip)
    before = jobs_count(ip)
    msgs = []
    for kind in ("launch_nextflow", "cancel_run", "clean_" "work", "put_upload", "list_site_files", "pipeline_files"):
        with pytest.raises(jobs.JobRefused) as e:
            jobs.check_target(ip.state_db, "k1", kind)
        msgs.append(str(e.value))
    with pytest.raises(jobs.JobRefused) as e:
        jobs.enqueue_listing(ip.state_db, "k1", "/x")
    msgs.append(str(e.value))
    assert len(msgs) == 7
    for msg in msgs:
        assert "Kubernetes" in msg and "尚未支援送出" in msg and "k8s-launch" in msg, msg
        assert "Azure" not in msg and "AWS" not in msg and "Google" not in msg, msg
    assert jobs_count(ip) == before
    jobs.enqueue_preflight(ip.state_db, "k1")      # the preflight is the one job it takes
    assert jobs_count(ip) == before + 1


def test_launch_is_refused_and_the_environment_is_never_auto_picked(ip):
    # TC-106, TC-107, TC-108
    from abf_launch import build
    _available_k8s(ip)
    problem = build.target_problem(ip.state_db, "k1", "launch_nextflow")
    assert problem and isinstance(problem, str)
    assert build.primary_environment(ip.state_db) is None
    assert ip.create_slurm("s1")[0] == 0
    set_status(ip, "s1", "available")
    assert build.primary_environment(ip.state_db) == "s1"


def test_another_users_k8s_environment_is_not_found(ip):
    # TC-109, TC-110
    from abf_platform import compute_envs, jobs
    _available_k8s(ip, owner_user_id=1)
    before_env, n = compute_envs.get(ip.state_db, "k1"), jobs_count(ip)
    assert compute_envs.get(ip.state_db, "k1", owner=2) is None
    missing = None
    try:
        jobs.check_target(ip.state_db, "nothing-here", "preflight", caller_user_id=2)
    except jobs.JobRefused as e:
        missing = str(e)
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(ip.state_db, "k1", "preflight", caller_user_id=2)
    assert missing is not None and str(e.value).replace("k1", "X") == missing.replace("nothing-here", "X")
    assert "Kubernetes" not in str(e.value)
    assert compute_envs.get(ip.state_db, "k1") == before_env and jobs_count(ip) == n


def test_updating_a_disabled_environment_queues_no_preflight(ip):
    # TC-111
    register_agent(ip)
    make_env(ip)
    serve(ip)
    assert ip.run("ce", "disable", "k1")[0] == 0
    n = jobs_count(ip)
    rc, out = ip.run("ce", "update", "k1", "--namespace", "other-ns")
    assert rc == 0 and ip.show("k1")["config"]["namespace"] == "other-ns" and jobs_count(ip) == n


# ---- US5: old records --------------------------------------------------------------------------------------------------

OLD = {"workDir": "/mnt/work", "namespace": "nf", "storageClaimName": "pvc-work", "storageMountPath": "/mnt"}


def _old_row(ip, name="old", config=None):
    from abf_platform import store
    con = store.connect_state(ip.state_db)
    with con:
        con.execute("INSERT INTO compute_envs (name, platform, status, message, is_primary, config_json, created_at, updated_at) "
                    "VALUES (?, 'k8s-platform', 'unsupported', 'Not supported yet', 0, ?, 1, 1)", (name, json.dumps(config or OLD)))
    con.close()


def test_an_old_k8s_record_asks_for_the_missing_context(ip):
    # TC-112, TC-113, TC-114, TC-115, TC-116
    _old_row(ip)
    register_agent(ip)
    assert ip.show("old")["status"] == "unsupported" and "old" in ip.run("ce", "list")[1]
    before, n = ip.show("old"), jobs_count(ip)
    rc, out = ip.run("ce", "preflight", "old")
    assert rc != 0 and "context" in out and jobs_count(ip) == n
    assert not re.search(r"unknown setting[^\n]*(namespace|storageClaimName|storageMountPath|workDir)", out)
    rc, out = ip.run("ce", "update", "old", "--agent", "a1")
    assert rc != 0 and "context" in out and ip.show("old") == before
    assert not re.search(r"unknown setting[^\n]*(namespace|storageClaimName|storageMountPath|workDir)", out)
    rc, out = ip.run("ce", "update", "old", "--agent", "a1", "--context", CTX)
    assert rc == 0, out
    assert ip.show("old")["status"] == "creating"


# ---- US6: docs ---------------------------------------------------------------------------------------------------------

def doc(name):
    return (REPO_ROOT / "docs" / name).read_text(encoding="utf-8")


NEW_SENTENCE = ("Slurm, Google Cloud Batch, AWS Batch and Azure Batch can run; Kubernetes can be created and checked on the platform "
                "host (launch: not yet); the other nine types can be modelled only")


def test_docs_list_every_k8s_key_and_check():
    # TC-117 .. TC-130
    d = doc("PLATFORM.md")
    for key in ("context", "namespace", "storageClaimName", "storageMountPath", "workDir", "serviceAccount") + tuple(CHECK_NAMES):
        assert "`%s`" % key in d, key
    section = d[d.index("### Kubernetes"):]
    section = section[:section.index("\n## ")] if "\n## " in section else section
    for word in ("ABF_STATION_KUBECONFIG", "_personal/kubeconfig", "chmod 600", "預檢不計費", "kubectl", "ReadWriteMany"):
        assert word in section, word
    assert re.search(r"operator|營運者", section) and re.search(r"exec", section) and re.search(r"trusted|信任", section)
    assert re.search(r"already exist|事先|beforehand|in advance", section)
    assert re.search(r"`k8s-platform` \| Kubernetes \| checked on the platform host \(launch: not yet\)", d)
    assert d.count(NEW_SENTENCE) >= 2 and "the other ten" not in d
    assert "Fourteen types can be created" in d
    par = doc("SEQERA_PARITY.md")
    row = [ln for ln in par.splitlines() if "`k8s-platform`" in ln][0]
    assert "Have (create + check); launch not yet" in row and row.rstrip().endswith("[ ] |")
    pre = par[par.index("Pre-flight checks:"):].split("\n")[0]
    assert "for Google Cloud Batch the station agent on the platform host runs them" in pre
    assert "for AWS Batch the same agent runs them" in pre and "for Azure Batch the same agent runs them" in pre
    assert pre.rstrip(". ").endswith("; for Kubernetes the same agent runs the read-only checks (create + check; launch not yet)")
    assert "## F. Compute environments (13 items)" in par
    t = doc("TESTING.md")
    assert "Kubernetes environment (k8s-ce)" in t
    small = t[t.index("Kubernetes environment (k8s-ce)"):]
    nxt = small.find("\n## ", 5)
    small = small[:nxt] if nxt > 0 else small
    for word in ("k8s-ce", "預檢不計費", "git diff", "TC-045", "TC-157", "TC-158", "TC-166", "KUBECACHEDIR", "accessModes",
                 "get-contexts", "回報"):
        assert word in small, word
    for text in (d, par, t):
        assert not re.search(r"eyJ[A-Za-z0-9_-]{10,}", text)
        assert not re.search(r"https?://[^\s)]*(azmk8s|eks\.amazonaws|container\.googleapis)", text)
        assert not re.search(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:6443\b", text)


# ---- US7: out of scope and the other types ---------------------------------------------------------------------------

def _sources():
    return list((PLATFORM_DIR / "abf_platform").rglob("*.py")) + list((PLATFORM_DIR / "abf_station").rglob("*.py"))


def test_no_launch_or_write_code_for_k8s():
    # TC-131
    for f in _sources():
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"kuberun|kubectl apply|kubectl create|kubectl delete", text), f.name
    assert "-with-tower" not in (PLATFORM_DIR / "abf_station" / "k8s_preflight.py").read_text(encoding="utf-8")


def test_no_cloud_library_is_imported_and_no_forbidden_word_in_the_agent_package():
    # TC-132
    text = (PLATFORM_DIR / "abf_station" / "k8s_preflight.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(kubernetes|boto3|botocore|azure|google|requests)\b", text, re.M)
    for f in (PLATFORM_DIR / "abf_station").rglob("*.py"):
        assert not re.search(r"kubernetes", f.read_text(encoding="utf-8")), f.name
    assert "kubernetes" not in (PLATFORM_DIR / "pyproject.toml").read_text(encoding="utf-8")


def test_the_platform_package_starts_no_program():
    # TC-133
    for f in (PLATFORM_DIR / "abf_platform").rglob("*.py"):
        text = f.read_text(encoding="utf-8")
        assert "subprocess" not in text and "kubectl" not in text, f.name


def test_only_site_py_starts_programs():
    # TC-134
    text = (PLATFORM_DIR / "abf_station" / "k8s_preflight.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+subprocess\b", text, re.M) and "site.run_fixed" in text


def test_tool_list_unchanged_and_no_new_web_route(tmp_path):
    # TC-135
    from abf_platform import web
    from abf_platform.mcp_server import build_server
    names = {t.name for t in asyncio.run(build_server(str(tmp_path / "index.db")).list_tools())}
    assert names == {"list_runs", "get_run", "list_compute_envs", "get_compute_env", "list_agents", "list_site_files", "list_used_pipelines", "read_task_log",
                     "run_outputs", "my_usage", "launch", "cancel", "resume", "relaunch", "forget"}
    app = web.create_app(tmp_path / "index.db", tmp_path / "tokens.db", tmp_path / "platform.db")
    assert not [r.path for r in app.routes if re.search(r"k8s|kube", getattr(r, "path", ""), re.I)]


def test_the_five_other_types_stay_unsupported(ip):
    # TC-138
    from abf_platform import compute_envs, jobs
    from test_station_envs import UNSUPPORTED
    register_agent(ip)
    cfgs = dict(UNSUPPORTED)
    assert K8S not in cfgs and len(cfgs) == 9
    for pid, cfg in cfgs.items():
        ce = compute_envs.create(ip.state_db, {"name": "x-" + pid, "platform": pid, "config": cfg})
        assert ce["status"] == "unsupported" and "Not supported" in ce["message"], pid
        with pytest.raises(jobs.JobRefused):
            jobs.enqueue_preflight(ip.state_db, "x-" + pid)
    assert {"eks-platform", "gke-platform", "awscloud-platform", "azcloud-platform", "googlecloud-platform"} <= set(cfgs)


def test_no_schema_change(ip):
    # TC-142
    create(ip)
    _old_row(ip)
    con = sqlite3.connect(str(ip.state_db))
    cols = [r[1] for r in con.execute("PRAGMA table_info(compute_envs)")]
    tables = sorted(r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'"))
    con.close()
    assert cols == ["id", "name", "description", "platform", "credentials_id", "agent", "status", "message", "is_primary",
                    "checked_ok", "config_json", "created_at", "updated_at", "last_used_at", "owner_user_id"]
    assert tables == ["agents", "compute_envs", "confirmations", "jobs", "launches", "meta", "sqlite_sequence"]
    assert not [p for p in (PLATFORM_DIR / "abf_platform").rglob("*migration*")]


def test_messages_say_what_to_do_and_leak_nothing_internal(ip, monkeypatch):
    # TC-165
    from abf_platform import jobs
    _available_k8s(ip, "avail")
    msgs = {"agent": refused(ip, agent=None), "context": refused(ip, good_config(context="a b"))}
    assert "--agent" in msgs["agent"]
    with pytest.raises(jobs.JobRefused) as e:
        jobs.check_target(ip.state_db, "avail", "launch_nextflow")
    msgs["launch"] = str(e.value)
    assert "k8s-launch" in msgs["launch"]
    _old_row(ip)
    rc, out = ip.run("ce", "preflight", "old")
    msgs["old"] = out
    assert "context" in out
    runner = fake_kubectl(monkeypatch)
    res = direct(ip.tmp / "nowhere")
    assert "chmod 600" in by_name(res)["credential_file"][1]       # the one message that may name a path
    for name, m in msgs.items():
        assert not re.search(r"Traceback|SELECT |INSERT |sqlite", m) and str(ip.tmp) not in m, name
    assert runner.calls == []
