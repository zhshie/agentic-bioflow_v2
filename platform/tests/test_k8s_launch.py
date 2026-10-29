# Nothing existing: searched Nextflow's official Kubernetes page (kuberun is obsolete), Seqera's `tw launch` and nf-core's `tower launch`; none is a local agent that, after a person's yes, creates the head Pod in the cluster and can stop that one Pod after a second yes, so these tests drive our agent with a fake kubectl (no cluster, no money).
"""Launching and cancelling on Kubernetes (k8s-launch).

The agent on the platform host creates ONE head Pod in the cluster (the bundle travels in a Secret, both fed to `kubectl create -f -`
through stdin) after a person's yes, and later deletes that one Pod after a second yes. Every test replaces `site.run_fixed` with a
fake kubectl: nothing here reaches a cluster, the network or a real program. The TC ids refer to specs/k8s-launch/test-case.md.
No credential-shaped string is written here as one literal: the fake kubeconfig is built from pieces and the run token at run time.
"""
import base64
import copy
import json
import os
import re
import secrets
import shutil
import sqlite3
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from helpers import PLATFORM_DIR, REPO_ROOT
from test_k8s_ce import (CTX, K8S, KCFG, KTOK, MOUNT, NS, PVC, SA, create, good_config, ip, jobs_count,  # noqa: F401
                         register_agent, set_status)

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="permission bits")
TOKEN = "abf_" + secrets.token_hex(16)      # made at run time: a fixed value of this shape in a tracked file fails tests/credentials_stay_in_settings_test.sh
IMAGE = "example/head:test"
PUBLIC = "https://platform.example"
SHEET = [["sample", "fastq_1", "strandedness"], ["s1", MOUNT + "/data/x.fastq.gz", "auto"]]
BILLING = "由你的 Kubernetes 叢集所屬的雲端或機房計費；本系統目前沒有費用預估與上限"
SECRET_KEYS = {"samplesheet.csv", "params.yaml", "nextflow.config", "k8s.config", "head.sh", "tower.token"}
PHASE = "{.status.phase}"


def zce(**over):
    """The snapshot of a fully set Kubernetes environment, as launch.snapshot_ce gives it."""
    c = {"name": "k8s1", "platform": K8S, "context": CTX, "namespace": NS, "storageClaimName": PVC, "storageMountPath": MOUNT,
         "workDir": MOUNT + "/work", "serviceAccount": None, "environment": [], "nextflowConfig": "// the user's own text\nprocess.cpus = 2\n",
         "preRunScript": "", "postRunScript": ""}
    c.update(over)
    return c


class Cluster:
    """A fake kubectl: answers each call of the agent from its own little world and remembers every call."""

    def __init__(self):
        self.calls = []          # (argv, env, stdin)
        self.pods = {}           # name -> phase
        self.secrets = {}
        self.manifests = []      # (kind, parsed manifest)
        self.fail = {}           # key -> (rc, output)
        self.logs = "log line 1\nlog line 2\n"
        self.phase = "Running"

    def kind_of(self, argv):
        a = argv[1:]
        if a[:2] == ["config", "get-contexts"]:
            return "context"
        if a[0] == "get":
            if a[1] == "pvc":
                return "pvc_access" if "accessModes" in a[a.index("-o") + 1] else "pvc"
            if a[1] == "serviceaccount":
                return "serviceaccount"
            jp = a[a.index("-o") + 1] if "-o" in a else None
            return "get_%s" % a[1] + ("_phase" if jp else "")
        if a[0] in ("create", "delete"):
            return "%s_%s" % (a[0], a[1] if a[1] != "-f" else "manifest")
        return a[0]

    def __call__(self, argv, env, timeout, stdin=None):
        self.calls.append((list(argv), dict(env or {}), stdin))
        key = self.kind_of(argv)
        a = argv[1:]
        if key in self.fail:
            return self.fail[key]
        if key == "context":
            return 0, CTX + "\n"
        if key == "pvc":
            return 0, "Bound"
        if key == "pvc_access":
            return 0, "ReadWriteMany"
        if key == "serviceaccount":
            return 0, "serviceaccount/" + a[2]
        if key in ("get_pod", "get_secret"):
            table = self.pods if key == "get_pod" else self.secrets
            return (0, a[2]) if a[2] in table else (1, 'Error from server (NotFound): %ss "%s" not found' % (a[1], a[2]))
        if key == "get_pod_phase":
            return (0, self.phase) if a[2] in self.pods else (1, 'Error from server (NotFound): pods "%s" not found' % a[2])
        if key == "create_manifest":
            doc = json.loads(stdin)
            self.manifests.append((doc["kind"], doc))
            (self.pods if doc["kind"] == "Pod" else self.secrets)[doc["metadata"]["name"]] = doc
            return 0, "%s/%s created" % (doc["kind"].lower(), doc["metadata"]["name"])
        if key == "delete_pod":
            self.pods.pop(a[2], None)
            return 0, 'pod "%s" deleted' % a[2]
        if key == "delete_secret":
            self.secrets.pop(a[2], None)
            return 0, 'secret "%s" deleted' % a[2]
        if key == "logs":
            return 0, self.logs
        raise AssertionError("an unexpected kubectl call: %r" % (argv,))

    def kinds(self):
        return [self.kind_of(c[0]) for c in self.calls]

    def writes(self):
        return [c for c in self.calls if c[0][1] in ("create", "delete")]

    def pod_doc(self):
        return [d for k, d in self.manifests if k == "Pod"][0]

    def secret_doc(self):
        return [d for k, d in self.manifests if k == "Secret"][0]


class Box:
    """The platform host as the agent sees it: a settings file, a kubeconfig, and fakes for kubectl."""

    def __init__(self, tmp, monkeypatch):
        from abf_station import site
        self.tmp = Path(tmp)
        self.mp = monkeypatch
        self.root = self.tmp / "host"
        self.root.mkdir()
        self.settings = self.root / "deploy" / "config" / "env.yaml"
        self.settings.parent.mkdir(parents=True)
        self.write_settings()
        self.cred = self.root / "kubeconfig-file"
        self.cred.write_text(KCFG)
        if sys.platform != "win32":
            self.cred.chmod(0o600)
        monkeypatch.setenv("ABF_STATION_KUBECONFIG", str(self.cred))
        monkeypatch.setenv("ABF_FOO", "foo")
        monkeypatch.setenv("KUBE_BAR", "bar")
        monkeypatch.setenv("ABF_STATION_GCB_SETTLE_SECONDS", "0")
        self.cluster = Cluster()
        self.started = []
        self.has_kubectl = True
        self.user = "tester"
        monkeypatch.setattr(site, "run_fixed", self.cluster)
        monkeypatch.setattr(site, "start_detached", lambda *a, **k: self.started.append(a))
        monkeypatch.setattr(shutil, "which", lambda name, *a, **k: "/usr/bin/" + name if (name != "kubectl" or self.has_kubectl) else None)
        self.ctx = SimpleNamespace(site=None, settings_file=str(self.settings), platform_url="http://127.0.0.1:8123",
                                   agent_name="a1", instance_id=None, used_confirmations=set(), job_started=time.monotonic())

    def write_settings(self, image=IMAGE, extra=""):
        lines = ["reach: local", "way_back: direct", "platform_public_url: " + PUBLIC]
        if image:
            lines.append("k8s_head_image: " + image)
        self.settings.write_text("\n".join(lines) + "\n" + extra)

    def facts(self, **over):
        f = {"slurm_account": None, "reach": "local", "platform_local": True, "endpoint": "http://127.0.0.1:8123", "forward_file": None,
             "storage_root": None, "way_back": "direct", "platform_public_url": PUBLIC}
        f.update(over)
        return f

    def bundle(self, run="r1", **over):
        from abf_station import launch
        kw = dict(ce=zce(), agent="a1", facts=self.facts(), roots=[], run_name=run, pipeline="nf-core/rnaseq", revision="3.14.0",
                  samplesheet=copy.deepcopy(SHEET), params={"genome": "GRCh38"})
        kw.update(over)
        return launch.render_k8s_bundle(**kw)

    def handle(self, job):
        from abf_station import handlers
        return handlers.handle(job, self.ctx)


@pytest.fixture
def box(tmp_path, monkeypatch):
    return Box(tmp_path, monkeypatch)


def job_of(bundle, cid=None, sha=None, kind="launch_nextflow", conf_kind="launch", token=TOKEN, remaining=300, **extra):
    from abf_platform import common
    cid = cid or secrets.token_hex(16)
    sha = sha or common.bundle_sha256(bundle)
    job = {"kind": kind, "args": {"bundle": bundle, "confirmation_id": cid, "bundle_sha256": sha},
           "confirmation": {"id": cid, "sha256": sha, "kind": conf_kind}, "run_token": token, "remaining": remaining}
    job.update(extra)
    return job


def launch_ok(box, run="r1", **over):
    b = box.bundle(run, **over)
    state, res = box.handle(job_of(b))
    assert state == "done", res
    return b, res


def cancel_bundle(run="r1", **over):
    from abf_station import launch
    b = {"version": 1, "run_name": run, "slurm_job_id": 1, "run_folder": "%s/_k8s_runs/%s" % (MOUNT, run), "agent": "a1", "ce": zce(),
         "pod_name": launch.k8s_pod_name(run)}
    b.update(over)
    return b


def cancel_job(bundle, **kw):
    return job_of(bundle, kind="cancel_run", conf_kind="cancel", **kw)


def config_keys(text):
    out = {}
    for ln in text.splitlines():
        if not ln.strip() or ln.lstrip().startswith("//"):
            continue
        k, eq, v = ln.partition(" = ")
        assert eq, "not a setting line: %r" % ln
        out[k] = v
    return out


def everything_said(box):
    """All text that went to kubectl: every argv element and every stdin."""
    return "\n".join(" ".join(argv) + "\n" + (stdin or "") for argv, _env, stdin in box.cluster.calls)


# ======================================================================================================================
# US1 - launch after the yes (K8L-RUN, K8L-CONF)
# ======================================================================================================================

def test_launch_creates_the_secret_then_the_pod(box):
    # TC-001, TC-002, TC-003, TC-004, TC-005, TC-008, K8L-RUN-01
    b, res = launch_ok(box)
    assert res["ok"] is True and res["run_name"] == "r1"
    assert res["message"].startswith("已啟動：Pod nf-r1（命名空間 %s）；叢集的運算費用從現在開始計" % NS)
    assert isinstance(res["slurm_job_id"], int) and res["slurm_job_id"] != 0
    assert b["pod_name"] == "nf-r1"
    c = box.cluster
    writes = c.writes()
    assert [w[0][1] for w in writes] == ["create", "create"]
    assert [k for k, _ in c.manifests] == ["Secret", "Pod"]
    for argv, _env, stdin in writes:
        assert argv[argv.index("-f") + 1] == "-" and argv[argv.index("--context") + 1] == CTX and argv[argv.index("--namespace") + 1] == NS
        assert stdin and stdin not in argv and "from-file" not in " ".join(argv) and "from-literal" not in " ".join(argv)
    kinds = c.kinds()
    assert kinds.index("get_pod") < kinds.index("get_secret") < kinds.index("create_manifest")
    assert max(kinds.index(k) for k in ("context", "pvc", "pvc_access")) < kinds.index("get_pod")
    assert kinds[-1] == "get_pod_phase" and "logs" not in kinds
    assert box.started == []                                  # nothing runs on the platform host
    assert not list(box.root.rglob("head.pid")) and not list(box.root.rglob("head.out"))
    _b2, res2 = launch_ok(box, run="r2")
    assert res2["slurm_job_id"] == res["slurm_job_id"]            # a fixed placeholder, the same for every launch
    assert not [p for p in box.tmp.rglob("*") if p.is_file() and p.suffix in (".yaml", ".json") and "kubeconfig" not in p.name
                and p != box.settings]


def test_the_pod_is_one_pod_wired_to_the_environment(box):
    # TC-086, TC-087, TC-088, TC-089, TC-090, K8L-BUNDLE-03
    b, _ = launch_ok(box, ce=zce(serviceAccount=SA))
    pod = box.cluster.pod_doc()
    assert pod["kind"] == "Pod" and pod["metadata"]["name"] == "nf-r1" and pod["metadata"]["namespace"] == NS
    spec = pod["spec"]
    assert spec["restartPolicy"] == "Never" and spec["serviceAccountName"] == SA
    vols = {v["name"]: v for v in spec["volumes"]}
    pvc = [v for v in spec["volumes"] if "persistentVolumeClaim" in v][0]
    assert pvc["persistentVolumeClaim"]["claimName"] == PVC
    secret = [v for v in spec["volumes"] if "secret" in v][0]
    assert secret["secret"]["secretName"] == "nf-r1-bundle" and len(vols) == 2
    assert len(spec["containers"]) == 1
    cont = spec["containers"][0]
    assert cont["image"] == IMAGE
    mounts = {m["name"]: m for m in cont["volumeMounts"]}
    assert mounts[pvc["name"]]["mountPath"] == MOUNT and not mounts[pvc["name"]].get("readOnly")
    assert mounts[secret["name"]]["readOnly"] is True
    script = cont["command"][-1]
    runs = [ln for ln in script.splitlines() if "nextflow run" in ln]
    assert len(runs) == 1 and script.rstrip().splitlines()[-1] == runs[0]
    assert runs[0].lstrip("exec ").startswith("nextflow run nf-core/rnaseq -r 3.14.0 -name r1 -params-file params.yaml")
    assert runs[0].index("-c nextflow.config") < runs[0].index("-c k8s.config") < runs[0].index("-with-tower " + PUBLIC)
    assert "tower.token" in script and "chmod 600" in script and "_k8s_runs/r1" in script


def test_no_service_account_means_no_serviceaccountname(box):
    # TC-082
    b = box.bundle()
    assert "k8s.serviceAccount" not in config_keys(b["files"]["k8s.config"])
    launch_ok(box)
    assert "serviceAccountName" not in box.cluster.pod_doc()["spec"]
    withsa = box.bundle(ce=zce(serviceAccount=SA))
    assert config_keys(withsa["files"]["k8s.config"])["k8s.serviceAccount"] == "'%s'" % SA


def test_the_secret_carries_exactly_the_six_files(box):
    # TC-060, TC-061, TC-063
    b, _ = launch_ok(box)
    sec = box.cluster.secret_doc()
    assert sec["kind"] == "Secret" and sec["metadata"]["name"] == "nf-r1-bundle" and sec["metadata"]["namespace"] == NS
    assert set(sec["data"]) == SECRET_KEYS
    for name in SECRET_KEYS - {"tower.token"}:
        assert base64.b64decode(sec["data"][name]).decode() == b["files"][name], name
    assert base64.b64decode(sec["data"]["tower.token"]).decode() == TOKEN
    assert TOKEN not in json.dumps(b) and TOKEN not in "\n".join(" ".join(c[0]) for c in box.cluster.calls)
    pod_text = json.dumps(box.cluster.pod_doc())
    assert TOKEN not in pod_text and base64.b64encode(TOKEN.encode()).decode() not in pod_text


def test_pending_running_and_succeeded_all_count_as_started(box):
    # TC-009
    for phase in ("Pending", "Running", "Succeeded"):
        box.cluster.pods.clear()
        box.cluster.secrets.clear()
        box.cluster.phase = phase
        box.ctx.used_confirmations.clear()
        state, res = box.handle(job_of(box.bundle()))
        assert state == "done" and res["ok"] is True, (phase, res)


@pytest.mark.parametrize("label", ["no id", "no row", "sha", "kind", "spent"])
def test_unconfirmed_launch_touches_nothing(box, label):
    # TC-010, TC-011, TC-012, TC-013, K8L-CONF-01
    b = box.bundle()
    good = job_of(b)
    bad = {"no id": dict(good, args={"bundle": b, "bundle_sha256": good["args"]["bundle_sha256"]}),
           "no row": {k: v for k, v in good.items() if k != "confirmation"},
           "sha": dict(good, confirmation=dict(good["confirmation"], sha256="0" * 64)),
           "kind": dict(good, confirmation=dict(good["confirmation"], kind="cancel")),
           "spent": dict(good, confirmation=dict(good["confirmation"], used_at=12345.0))}[label]
    state, res = box.handle(bad)
    assert state == "refused", res
    assert box.cluster.calls == []


def test_a_confirmation_is_used_once(box):
    # TC-012
    b = box.bundle()
    job = job_of(b)
    assert box.handle(job)[0] == "done"
    n = len(box.cluster.calls)
    assert box.handle(job)[0] == "refused" and len(box.cluster.calls) == n


def test_launch_refusals_before_any_call(box):
    # TC-016, TC-017, TC-018, TC-019
    b = box.bundle()
    changed = copy.deepcopy(b)
    changed["files"]["k8s.config"] = changed["files"]["k8s.config"].replace(NS, "other-ns")
    for label, job in (("changed", job_of(changed)), ("other agent", job_of(dict(b, agent="a2"))),
                       ("no token", job_of(b, token="")), ("deadline", job_of(b, remaining=1))):
        state, res = box.handle(job)
        assert state == "refused", (label, res)
        assert res.get("message") or res.get("error"), label
        assert box.cluster.calls == [], label


def test_credential_problems_stop_before_any_call(box):
    # TC-020, TC-021, TC-022, K8L-CRED-03
    box.cred.unlink()
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "kubeconfig" in json.dumps(res, ensure_ascii=False) and box.cluster.calls == []
    box.cred.write_text(KCFG)
    if sys.platform != "win32":
        box.cred.chmod(0o644)
        box.ctx.used_confirmations.clear()
        state, res = box.handle(job_of(box.bundle()))
        assert state == "refused" and box.cluster.calls == []
        box.cred.chmod(0o600)
    box.has_kubectl = False
    box.ctx.used_confirmations.clear()
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "kubectl" in json.dumps(res, ensure_ascii=False) and box.cluster.calls == []


@pytest.mark.parametrize("key", ["context", "pvc", "pvc_access", "serviceaccount"])
def test_a_failing_preflight_creates_nothing(box, key):
    # TC-023, K8L-RUN-02
    box.cluster.fail[key] = (1, "boom") if key != "context" else (0, "other-context\n")
    state, res = box.handle(job_of(box.bundle(ce=zce(serviceAccount=SA))))
    assert state == "refused", res
    assert box.cluster.writes() == []


def test_an_existing_pod_is_never_overwritten(box):
    # TC-024, TC-097, K8L-BUNDLE-05
    box.cluster.pods["nf-a-b"] = "Running"
    state, res = box.handle(job_of(box.bundle("a-b")))
    assert state == "refused" and "nf-a-b" in json.dumps(res, ensure_ascii=False) and box.cluster.writes() == []


def test_an_existing_secret_is_never_overwritten(box):
    # TC-025
    box.cluster.secrets["nf-r1-bundle"] = {}
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "nf-r1-bundle" in json.dumps(res, ensure_ascii=False) and box.cluster.writes() == []


def test_a_pod_that_cannot_be_created_takes_only_its_own_secret_away(box):
    # TC-026, TC-027, TC-028
    real = box.cluster.__call__
    state_calls = {"n": 0}

    def flaky(argv, env, timeout, stdin=None):
        if argv[1] == "create":
            state_calls["n"] += 1
            if state_calls["n"] == 2:
                box.cluster.calls.append((list(argv), dict(env or {}), stdin))
                return 1, "pods is forbidden"
        return real(argv, env, timeout, stdin)
    from abf_station import site
    box.mp.setattr(site, "run_fixed", flaky)
    state, res = box.handle(job_of(box.bundle()))
    assert state == "error" and "forbidden" in res["message"]
    deletes = [c[0] for c in box.cluster.writes() if c[0][1] == "delete"]
    assert len(deletes) == 1 and deletes[0][:4] == ["kubectl", "delete", "secret", "nf-r1-bundle"]
    assert deletes[0][deletes[0].index("--namespace") + 1] == NS and deletes[0][deletes[0].index("--context") + 1] == CTX
    # the delete fails too: the message names the Secret, nothing is retried
    box.cluster.calls.clear()
    box.cluster.secrets.clear()
    box.ctx.used_confirmations.clear()
    state_calls["n"] = 0
    box.cluster.fail["delete_secret"] = (1, "nope")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "error" and "nf-r1-bundle" in res["message"]
    assert len([c for c in box.cluster.writes() if c[0][1] == "delete"]) == 1


def test_a_secret_that_cannot_be_created_stops_there(box):
    # TC-028
    box.cluster.fail["create_manifest"] = (1, "quota exceeded")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "error" and "quota exceeded" in res["message"]
    assert [c[0][1] for c in box.cluster.writes()] == ["create"]


def test_a_failed_pod_reports_the_log_tail_and_deletes_nothing(box):
    # TC-029, TC-030, TC-031, K8L-RUN-03
    box.cluster.phase = "Failed"
    box.cluster.logs = "image pull failed " + TOKEN + "\n"
    state, res = box.handle(job_of(box.bundle()))
    assert state == "error" and res["ok"] is False and "image pull failed" in res["message"] and TOKEN not in json.dumps(res)
    assert len([k for k in box.cluster.kinds() if k == "logs"]) == 1
    logs = [c[0] for c in box.cluster.calls if c[0][1] == "logs"][0]
    assert logs[:3] == ["kubectl", "logs", "nf-r1"] and "--tail=50" in logs
    assert [c[0][1] for c in box.cluster.writes()] == ["create", "create"]       # nothing deleted


def test_an_unreachable_cluster_is_said_in_plain_words(box):
    # TC-032
    box.cluster.fail["get_pod"] = (1, "Unable to connect to the server: dial tcp: i/o timeout")
    state, res = box.handle(job_of(box.bundle()))
    assert "連不上叢集" in json.dumps(res, ensure_ascii=False) and box.cluster.writes() == []


def test_a_phase_that_cannot_be_read(box):
    # TC-033
    box.cluster.fail["get_pod_phase"] = (1, "connection reset")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "error" and "無法取得 Pod 狀態" in res["message"]
    assert [c[0][1] for c in box.cluster.writes()] == ["create", "create"]


def test_no_head_image_is_a_plain_refusal(box):
    # TC-034
    box.write_settings(image="")
    state, res = box.handle(job_of(box.bundle()))
    assert state == "refused" and "k8s_head_image" in json.dumps(res, ensure_ascii=False) and box.cluster.writes() == []
    code = (PLATFORM_DIR / "abf_station" / "k8s_launch.py").read_text(encoding="utf-8")
    assert not re.search(r"nextflow/nextflow|nextflow:[0-9]|:latest", code)
    box.write_settings(image=IMAGE)
    b = box.bundle()
    assert IMAGE not in json.dumps(b) and "k8s_head_image" not in json.dumps(b)


# ---- credentials ---------------------------------------------------------------------------------------------------

def test_every_call_gets_a_clean_environment_and_the_path_only_there(box):
    # TC-062, TC-064, K8L-CRED-01
    launch_ok(box)
    assert box.cluster.calls
    for argv, env, _stdin in box.cluster.calls:
        assert not [k for k in env if k.upper().startswith("ABF_")], argv
        assert "KUBE_BAR" not in env and env["KUBECONFIG"] == str(box.cred) and env["KUBECACHEDIR"]
        assert not [a for a in argv if str(box.cred) in a or KTOK in a]


def test_no_credential_reaches_argv_manifest_or_answer(box):
    # TC-065, K8L-CRED-02
    for label in ("ok", "failed", "no-pod"):
        box.cluster.pods.clear()
        box.cluster.secrets.clear()
        box.cluster.phase = "Failed" if label == "failed" else "Running"
        box.ctx.used_confirmations.clear()
        state, res = box.handle(job_of(box.bundle()))
        text = everything_said(box) + json.dumps(res, ensure_ascii=False)
        assert KTOK not in text and str(box.cred) not in text, label
    assert KTOK not in json.dumps(box.bundle()) and str(box.cred) not in json.dumps(box.bundle())


def test_the_ledger_holds_no_credential(box):
    # TC-066
    ledger = REPO_ROOT / "specs" / "k8s-launch" / "ledger.md"
    text = ledger.read_text(encoding="utf-8") if ledger.exists() else ""
    assert KTOK not in text and str(box.cred) not in text and TOKEN not in text


def test_no_call_changes_the_kubeconfig_or_reaches_wider(box):
    # TC-067, K8L-CRED-04
    launch_ok(box)
    box.handle(cancel_job(cancel_bundle()))
    box.cluster.phase = "Failed"
    box.ctx.used_confirmations.clear()
    box.cluster.pods.clear()
    box.cluster.secrets.clear()
    box.handle(job_of(box.bundle()))
    for argv, _env, _stdin in box.cluster.calls:
        for bad in ("use-context", "--all", "-l", "--selector", "kubeconfig"):
            assert bad not in argv, argv
        assert not [a for a in argv[1:2] if a.startswith("set-")] and "set-context" not in argv
        assert not (argv[1] == "delete" and argv[2] not in ("pod", "secret")), argv


# ---- the bundle ----------------------------------------------------------------------------------------------------

def test_the_k8s_config_holds_only_the_environments_plain_fields(box):
    # TC-080, TC-081, TC-083, TC-084, TC-085, K8L-BUNDLE-01
    b = box.bundle()
    keys = config_keys(b["files"]["k8s.config"])
    assert set(keys) == {"process.executor", "k8s.namespace", "k8s.storageClaimName", "k8s.storageMountPath", "workDir"}
    assert keys["process.executor"] == "'k8s'" and keys["workDir"] == "'%s/work/runs/r1/work'" % MOUNT
    assert box.bundle("r2")["files"]["k8s.config"] != b["files"]["k8s.config"]
    assert CTX not in b["files"]["k8s.config"] and KTOK not in b["files"]["k8s.config"]
    spot = box.bundle(ce=zce(spot=True, maxvCpus=8))["files"]["k8s.config"]
    assert spot == b["files"]["k8s.config"]
    assert "maxvCpus" not in spot and "spot" not in spot


def test_the_bundle_is_free_of_credentials_and_the_image(box):
    # TC-071, K8L-BUNDLE-02
    b = box.bundle()
    text = json.dumps(b)
    assert KTOK not in text and str(box.cred) not in text and IMAGE not in text
    from abf_station import launch
    from abf_platform import compute_envs
    assert launch.K8S == compute_envs.K8S


@pytest.mark.parametrize("run,name", [("r1", "nf-r1"), ("my_run", "nf-my-run"), ("a_b", "nf-a-b"), ("a-b", "nf-a-b")])
def test_pod_names(run, name):
    # TC-094, TC-097, K8L-BUNDLE-05
    from abf_station import launch
    assert launch.k8s_pod_name(run) == name


def test_long_pod_names_are_cut_at_63_without_a_trailing_dash():
    # TC-095, TC-096
    from abf_station import launch
    assert len(launch.k8s_pod_name("r" * 64)) == 63
    run = "a" * 59 + "-bcd"                  # "nf-" + 59 a's = 62 chars, the 63rd is "-"
    name = launch.k8s_pod_name(run)
    assert len(name) <= 63 and not name.endswith("-") and name.startswith("nf-aaa")


@pytest.mark.parametrize("cell", ["/home/x/a.fastq.gz", "s3://b/a.fastq.gz", "gs://b/a.fastq.gz", "az://c/a.fastq.gz"])
def test_samplesheet_paths_must_be_inside_the_claim(box, cell):
    # TC-099, TC-100, TC-101, K8L-BUNDLE-04
    from abf_station import launch
    with pytest.raises(launch.BundleError) as e:
        box.bundle(samplesheet=[SHEET[0], ["s1", cell, "auto"]])
    assert "PVC" in str(e.value) and MOUNT in str(e.value)
    assert box.bundle()["samplesheet"] == SHEET


def test_a_composed_pipeline_is_refused_for_kubernetes(box):
    # TC-140, K8L-BUNDLE-07
    from abf_station import launch
    with pytest.raises(launch.BundleError) as e:
        launch.render_bundle(ce=zce(), agent="a1", facts=box.facts(), roots=[], run_name="r1", pipeline="x/y", revision="1",
                             samplesheet=SHEET, params={}, composed={"pipeline_id": 1, "version": 1, "project": {}})
    assert "Kubernetes" in str(e.value)


def test_progress_reporting_needs_an_https_address_the_pod_can_reach(box):
    # TC-115, TC-116, TC-117
    from abf_station import launch
    for facts in (box.facts(way_back=None), box.facts(platform_public_url=None), box.facts(platform_public_url="http://x.example")):
        with pytest.raises(launch.BundleError) as e:
            box.bundle(facts=facts)
        assert "https" in str(e.value) or "公開網址" in str(e.value)
    assert box.bundle()["tower"]["endpoint"] == PUBLIC


def test_resume_and_relaunch_are_refused_for_kubernetes(box):
    # TC-136, TC-137, K8L-BUNDLE-06
    from abf_station import launch, rules
    assert "Kubernetes" in launch.K8S_NO_RESUME and "AWS" not in launch.K8S_NO_RESUME
    b = box.bundle()
    resume = dict(b, resume={"of_run": "r0", "of_slurm_job_id": 1, "session_id": "s", "attempt": 1, "origin": copy.deepcopy(b)})
    with pytest.raises(rules.Refusal) as e:
        launch.run_resume(job_of(resume), box.ctx, None, resume)
    assert "Kubernetes" in str(e.value)


# ---- cancel ----------------------------------------------------------------------------------------------------------

def test_cancel_deletes_the_one_pod(box):
    # TC-122, K8L-CANCEL-01
    box.cluster.pods["nf-r1"] = "Running"
    state, res = box.handle(cancel_job(cancel_bundle()))
    assert state == "done" and res["ok"] is True
    deletes = [c[0] for c in box.cluster.writes()]
    assert deletes == [["kubectl", "delete", "pod", "nf-r1", "--namespace", NS, "--context", CTX, "--wait=false"]]
    assert "task pod" in res["message"] or "task" in res["message"]


def test_cancel_of_a_pod_that_is_gone_is_ok(box):
    # TC-123
    state, res = box.handle(cancel_job(cancel_bundle()))
    assert state == "done" and "已不存在" in res["message"] and box.cluster.writes() == []


def test_cancel_with_an_unreachable_cluster_deletes_nothing(box):
    # TC-124
    box.cluster.fail["get_pod"] = (1, "Unable to connect to the server")
    state, res = box.handle(cancel_job(cancel_bundle()))
    assert "連不上叢集" in json.dumps(res, ensure_ascii=False) and box.cluster.writes() == []


def test_cancel_failure_is_reported_once(box):
    # TC-127, TC-128
    box.cluster.pods["nf-r1"] = "Running"
    box.cluster.fail["delete_pod"] = (1, "forbidden " + TOKEN)
    state, res = box.handle(cancel_job(cancel_bundle()))
    assert state == "error" and "forbidden" in res["message"] and TOKEN not in json.dumps(res)
    assert len(box.cluster.writes()) == 1


@pytest.mark.parametrize("over", [{"pod_name": "other-pod"}, {"ce": zce(namespace="Bad_NS")}])
def test_cancel_with_a_name_or_namespace_that_does_not_fit_sends_nothing(box, over):
    # TC-125, TC-126
    box.cluster.pods["nf-r1"] = "Running"
    state, res = box.handle(cancel_job(cancel_bundle(**over)))
    assert state == "refused" and box.cluster.writes() == []


def test_cancel_for_another_agent_is_refused(box):
    # TC-129
    state, res = box.handle(cancel_job(cancel_bundle(agent="a2")))
    assert state == "refused" and box.cluster.calls == []


def test_other_types_keep_their_cancel_fields():
    # TC-130
    from abf_station import cancel
    assert cancel.KEYS == {"version", "run_name", "slurm_job_id", "run_folder", "agent", "ce"}


# ---- the source rules ------------------------------------------------------------------------------------------------

def test_source_rules():
    # TC-091, TC-070, K8L-CONF-03, K8L-CONF-04, K8L-GATE-03
    code = (PLATFORM_DIR / "abf_station" / "k8s_launch.py").read_text(encoding="utf-8")
    assert "# Nothing existing:" in "\n".join(code.splitlines()[:40])
    assert "nextflow run" not in code and "sbatch" not in code and "subprocess" not in code
    me = Path(__file__).read_text(encoding="utf-8")
    assert "# Nothing existing:" in "\n".join(me.splitlines()[:40])
    for p in (PLATFORM_DIR).rglob("*.py"):
        if "tests" in p.parts:
            continue
        text = p.read_text(encoding="utf-8")
        assert "PLATFORM_HOST_TYPES[" not in text, p
        if p.name != "launch.py" or p.parent.name != "abf_station":
            assert "nextflow run" not in text or p.name in ("launch.py",), p
    pyproject = REPO_ROOT / "pyproject.toml"
    if pyproject.exists():
        assert "kubernetes" not in pyproject.read_text(encoding="utf-8").lower()
    for p in (PLATFORM_DIR / "abf_station").glob("*.py"):
        assert "kubernetes" not in p.read_text(encoding="utf-8"), p


# ======================================================================================================================
# Platform side: gates, screens, cancel preparation, wording
# ======================================================================================================================

def available_k8s(ip, name="k1"):
    register_agent(ip)
    create(ip, name)
    set_status(ip, name, "available")


def test_the_type_tables():
    # TC-049, TC-050, TC-051, K8L-GATE-03
    from abf_platform import compute_envs as ce
    assert ce.PLATFORM_HOST_TYPES == (ce.GOOGLE_BATCH, ce.AWS, ce.AZURE, ce.K8S)
    assert ce.CHECK_ONLY_TYPES == ()
    assert set(ce.CLOUD_JOB_KINDS[ce.K8S]) == {"preflight", "launch_nextflow", "cancel_run", "pipeline_files"} and len(ce.CLOUD_JOB_KINDS[ce.K8S]) == 4
    assert ce.K8S in ce.CHECKABLE


def test_the_four_kinds_pass_and_the_rest_say_not_yet(ip):
    # TC-035..TC-044, TC-056, K8L-GATE-01, K8L-GATE-05
    from abf_platform import jobs
    available_k8s(ip)
    for kind in ("launch_nextflow", "cancel_run", "preflight", "pipeline_files"):
        jobs.check_target(ip.state_db, "k1", kind)
    before = jobs_count(ip)
    words = {"clean_work": "尚未支援清理"}
    for kind in ("clean_" "work", "put_upload", "list_site_files", "fetch_run_records", "read_task_log"):
        with pytest.raises(jobs.JobRefused) as e:
            jobs.check_target(ip.state_db, "k1", kind)
        msg = str(e.value)
        assert "Kubernetes" in msg and "尚未支援" in msg, msg
        assert words.get(kind, "尚未支援") in msg
        for other in ("AWS", "Google Batch", "Azure", "k8s-launch", "尚未支援送出"):
            assert other not in msg, msg
    assert jobs_count(ip) == before
    jobs.enqueue_preflight(ip.state_db, "k1")
    assert jobs_count(ip) == before + 1


def test_cloud_paths_still_do_not_resolve_for_kubernetes(ip):
    # TC-054, K8L-GATE-04
    from abf_platform import cloud_store, compute_envs
    available_k8s(ip)
    view = compute_envs.get(ip.state_db, "k1")
    with pytest.raises(cloud_store.CloudPathError):
        cloud_store.workdir_scheme(view)


def test_prepare_launch_screen_and_cancel_for_kubernetes(ip, box, tmp_path):
    # TC-007, TC-102..TC-107, TC-117..TC-121, K8L-SCREEN-01, K8L-CANCEL-02
    from abf_launch import build, terminal
    from abf_platform import agents, jobs
    register_agent(ip)
    agents.register(ip.state_db, "a1", "0.1.0", time.time, facts=box.facts())
    create(ip, "k8s1")
    set_status(ip, "k8s1", "available")
    sheet = tmp_path / "samples.csv"
    sheet.write_text("\n".join(",".join(r) for r in SHEET) + "\n")
    n = jobs_count(ip)
    ce_name, bundle = build.prepare_launch(ip.state_db, ce="k8s1", pipeline="nf-core/rnaseq", revision="3.14.0", run_name="r1",
                                           samplesheet=str(sheet), params={"genome": "GRCh38"}, owner=None)
    assert jobs_count(ip) == n and bundle["pod_name"] == "nf-r1" and bundle["ce"]["platform"] == K8S
    screen = "\n".join(build.launch_screen(bundle, ce_name))
    first = build.launch_screen(bundle, ce_name)[1]
    assert BILLING in first and build.K8S_COST == BILLING
    for bad in ("NT$", "USD", "$", TOKEN, IMAGE):
        assert bad not in screen
    for want in (CTX, NS, PVC, "nf-r1", "/workspace/_k8s_runs/r1/", "k8s.config", "nextflow.config", "params.yaml", "nextflow run"):
        assert want in screen, want
    with pytest.raises(build.Refusal):
        build.prepare_cancel(ip.state_db, "never-launched")


def test_resume_wording_and_cli_lines():
    # TC-112, TC-113, TC-114, K8L-SCREEN-03
    from abf_launch import build, cli
    from abf_platform import compute_envs
    assert hasattr(build, "is_k8s")
    row = {"slurm_job_id": 1, "run_name": "r1", "run_folder": "/workspace/_k8s_runs/r1"}
    bundle = {"run_name": "r1", "pod_name": "nf-r1", "ce": {"platform": compute_envs.K8S, "namespace": NS}}
    line = cli._submitted_line(row, compute_envs.K8S, bundle)
    assert line.startswith("已啟動：Pod nf-r1（命名空間 %s）；叢集的運算費用從現在開始計" % NS) and "Slurm 工作編號" not in line
    assert cli._submitted_line(row) == "已送出：Slurm 工作編號 1；run 名稱 r1；專屬資料夾 /workspace/_k8s_runs/r1。"
