# Nothing existing: searched Nextflow's k8s executor and Seqera's Kubernetes form; neither has a free offline preflight, and the Python client package is barred here (TC-085 scan), so this reads with the kubectl CLI, one fixed argv each.
"""The preflight of a Kubernetes compute environment, run by the agent on the platform host.

It is read-only and free (預檢不計費): it asks the cluster whether the context exists in the kubeconfig, whether the storage claim
is bound and shared-writable, and whether the service account exists. It creates, changes and deletes nothing, and starts
nothing. The kubeconfig lives only on this side (its content is never read here, only handed to kubectl); the platform keeps
only a credential name. The file's path reaches kubectl through the environment of that one call, never through argv.
"""
import os
import shutil
import stat as stat_mod
import sys
import tempfile
from pathlib import Path

from abf_platform import compute_envs      # the same shapes of context, namespace, claim and paths as the platform applies

from . import rules, site
from .gcb_preflight import _check, _scrub  # the same scrubbing and result shape as the Google Batch preflight

TYPE = "k8s-platform"
CREDENTIALS_ENV = "ABF_STATION_KUBECONFIG"
DEFAULT_RELATIVE = ("_personal", "kubeconfig")
TIMEOUT_SECONDS = 30
REQUEST_TIMEOUT = "--request-timeout=20s"
DETAIL_LIMIT = 300
MAX_FILE = 1000000
KEEP = ("name", "platform", "credentialsId", "context", "namespace", "storageClaimName", "storageMountPath", "workDir", "serviceAccount")
DEPENDENTS = ("context", "pvc", "pvc_access", "service_account")


def credentials_path(settings_file, environ=None):
    """Where this agent looks for the kubeconfig: its own setting, never the platform's."""
    environ = os.environ if environ is None else environ
    given = environ.get(CREDENTIALS_ENV)
    if given:
        return Path(given)
    return Path(settings_file).parent.parent.joinpath(*DEFAULT_RELATIVE)


def clean_environment(ce):
    """The parts of a Kubernetes environment the checks use, each judged again here whatever the platform judged: they reach a
    command line. Anything else in it is ignored."""
    if not isinstance(ce, dict) or ce.get("platform") != TYPE:
        raise rules.Refusal("the environment is not a Kubernetes environment")
    cred = ce.get("credentialsId")
    if cred is not None and not (isinstance(cred, str) and compute_envs._CRED_NAME.match(cred)):
        raise rules.Refusal("credentialsId is not a credential name (憑證名字不合規則)")
    config = {k: ce.get(k) for k in KEEP[3:] if ce.get(k) not in (None, "")}
    try:
        compute_envs._check_k8s(config, "agent")
    except compute_envs.CEError as e:
        raise rules.Refusal(str(e)[:300])
    out = {"name": str(ce.get("name"))[:100], "platform": TYPE, "credentialsId": cred}
    out.update({k: config.get(k) for k in KEEP[3:]})
    return out


def _run(argv, env, timeout):
    """(return code, the first 300 characters of the output). Fixed argv, no shell (site.run_fixed). A timeout is raised to the caller."""
    rc, out = site.run_fixed(argv, env, timeout)
    return rc, str(out)[:DETAIL_LIMIT]


def _kube_env(cred_path, cache_dir):
    """The environment of one kubectl call: none of the agent's own ABF or kube variables; the kubeconfig travels here, never in argv."""
    e = {k: v for k, v in os.environ.items() if not k.upper().startswith(("ABF_", "KUBE"))}
    e["KUBECONFIG"] = str(cred_path)
    e["KUBECACHEDIR"] = cache_dir
    return e


def _call(runner, argv, cred_path):
    """(return code, output), each call with an empty cache folder of its own that is deleted afterwards."""
    folder = tempfile.mkdtemp(prefix="abf-kube-")
    try:
        return runner(argv, _kube_env(cred_path, folder), TIMEOUT_SECONDS)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def _get(env, what, *tail):
    return (["kubectl", "get", what[0], what[1], "--namespace", env["namespace"], "--context", env["context"], REQUEST_TIMEOUT]
            + list(tail))


def _timed_out():
    return "逾時 (timed out after %d seconds); check the network and try again" % TIMEOUT_SECONDS


def run_preflight(env, *, cred_path, now=None, runner=None, which=None, stat=os.stat):
    """{'ok': bool, 'checks': [{'name', 'status', 'detail'}]} for a judged environment (see clean_environment).

    runner(argv, env, timeout) -> (return code, output); which(name) -> path or None. Both default to the real ones and are
    replaced by fakes in tests."""
    runner = runner or _run
    which = which or shutil.which
    ctx, claim, sa = env["context"], env["storageClaimName"], env.get("serviceAccount")
    checks = []

    if env.get("credentialsId"):
        checks.append(_check("credential_name", "pass", "credential name: %s" % env["credentialsId"]))
    else:
        checks.append(_check("credential_name", "fail", "give this environment a credential name (給這個環境一個憑證名字): "
                             "--credentials NAME. Only the name is stored; the kubeconfig stays on the agent's computer."))

    usable = False
    where = "the kubeconfig should be at %s" % cred_path
    try:
        st = stat(str(cred_path))
    except OSError:
        checks.append(_check("credential_file", "fail", "no kubeconfig (找不到憑證檔): %s. Put it there and make it readable by "
                             "this user only (chmod 600)." % where))
    else:
        if not stat_mod.S_ISREG(st.st_mode):
            checks.append(_check("credential_file", "fail", "%s, but it is not a regular file (不是一般檔案)" % where))
        elif st.st_size > MAX_FILE:
            checks.append(_check("credential_file", "fail", "the kubeconfig is larger than 1 MB, so it is not a kubeconfig (憑證檔太大)"))
        elif sys.platform != "win32" and st.st_mode & 0o077:
            checks.append(_check("credential_file", "fail", "the kubeconfig's permissions are too open (權限太寬): group or "
                                 "others can read or write it. Run chmod 600 on %s" % cred_path))
        elif sys.platform == "win32":
            usable = True
            checks.append(_check("credential_file", "pass", "kubeconfig found; Windows 不檢查權限位 (permission bits are not checked)"))
        else:
            usable = True
            checks.append(_check("credential_file", "pass", "kubeconfig found, readable by the owner only"))

    kubectl = which("kubectl")
    if kubectl:
        checks.append(_check("kubectl", "pass", "kubectl found"))
    else:
        checks.append(_check("kubectl", "unchecked", "kubectl 沒裝 (kubectl is not installed on this computer), so the cluster could "
                             "not be checked; install it"))

    if not (kubectl and usable):
        for name in DEPENDENTS:
            checks.append(_check(name, "unchecked", "no usable kubeconfig or no kubectl, so this was not checked"))
        return {"ok": False, "checks": checks}

    # context: the name must be a whole line of the list
    ctx_ok = False
    try:
        rc, out = _call(runner, ["kubectl", "config", "get-contexts", "-o", "name"], cred_path)
    except TimeoutError:
        checks.append(_check("context", "fail", _timed_out()))
    else:
        if rc != 0:
            checks.append(_check("context", "fail", ("kubectl failed (code %s): " % rc) + _scrub(str(out or "").strip())))
        elif ctx in [ln.strip() for ln in str(out or "").splitlines()]:
            ctx_ok = True
            checks.append(_check("context", "pass", "context %s is in the kubeconfig" % ctx))
        else:
            checks.append(_check("context", "fail", "context %s 不在這個 kubeconfig 裡 (not in the kubeconfig); check the name" % ctx))
    if not ctx_ok:
        for name in DEPENDENTS[1:]:
            checks.append(_check(name, "unchecked", "the context was not found, so this was not checked"))
        return {"ok": False, "checks": checks}

    pvc_ok = False
    try:
        rc, out = _call(runner, _get(env, ("pvc", claim), "-o", "jsonpath={.status.phase}"), cred_path)
    except TimeoutError:
        checks.append(_check("pvc", "fail", _timed_out()))
    else:
        out = str(out or "").strip()
        if rc != 0:
            checks.append(_check("pvc", "fail", ("claim %s 讀不到 (could not be read, code %s): " % (claim, rc)) + _scrub(out)))
        elif out == "Bound":
            pvc_ok = True
            checks.append(_check("pvc", "pass", "claim %s is Bound" % claim))
        else:
            checks.append(_check("pvc", "fail", "claim %s is %s, not Bound (儲存請求還沒綁定)" % (claim, _scrub(out)[:40] or "unknown")))

    if not pvc_ok:
        checks.append(_check("pvc_access", "unchecked", "the claim is not Bound, so its access modes were not checked"))
    else:
        try:
            rc, out = _call(runner, _get(env, ("pvc", claim), "-o", "jsonpath={.spec.accessModes[*]}"), cred_path)
        except TimeoutError:
            checks.append(_check("pvc_access", "fail", _timed_out()))
        else:
            out = str(out or "").strip()
            if rc != 0:
                checks.append(_check("pvc_access", "fail", ("access modes of %s 讀不到 (code %s): " % (claim, rc)) + _scrub(out)))
            elif "ReadWriteMany" in out.split():
                checks.append(_check("pvc_access", "pass", "claim %s allows ReadWriteMany" % claim))
            else:
                checks.append(_check("pvc_access", "fail", "claim %s needs ReadWriteMany (Nextflow's work folder is shared by several pods); "
                                     "it has: %s" % (claim, _scrub(out)[:80] or "nothing")))

    if not sa:
        checks.append(_check("service_account", "pass", "未設定，使用命名空間預設帳號 (not set: the namespace's default account is used)"))
    else:
        try:
            rc, out = _call(runner, _get(env, ("serviceaccount", sa), "-o", "name"), cred_path)
        except TimeoutError:
            checks.append(_check("service_account", "fail", _timed_out()))
        else:
            if rc != 0:
                checks.append(_check("service_account", "fail", ("service account %s 讀不到 (code %s): " % (sa, rc)) + _scrub(str(out or "").strip())))
            else:
                checks.append(_check("service_account", "pass", "service account %s exists" % sa))
    return {"ok": all(c["status"] == "pass" for c in checks), "checks": checks}
