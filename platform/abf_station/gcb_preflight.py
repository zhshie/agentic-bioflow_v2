# Nothing existing: searched Nextflow's google-batch executor and Seqera's Google Batch form; neither ships a check that runs offline and free, and the official Python packages are barred by TC-085, so this calls the gcloud command line.
"""The preflight of a Google Cloud Batch environment, run by the station agent that sits on the platform host.

Everything here only reads: it reads the key file, lists Batch jobs (`gcloud batch jobs list`) and lists a bucket's top level
(`gcloud storage ls`). It creates no Batch job, writes no bucket and enables no API, so it costs nothing (預檢不計費). The key file's
content is parsed in memory for four fields and dropped; it never reaches a result, a message or the platform's database.

Where the key file lives is the agent's own setting: the environment variable ABF_STATION_GCP_CREDENTIALS, else
`<deployment>/_personal/gcp-sa.json` (the deployment is the folder that holds config/env.yaml).
"""
import json
import os
import re
import shutil
import stat as stat_mod
import sys
import time
from pathlib import Path

from abf_platform import compute_envs      # the same shapes of project, location and bucket as the platform applies when it stores them

from . import rules, site

TYPE = "googlebatch-platform"
CREDENTIALS_ENV = "ABF_STATION_GCP_CREDENTIALS"
DEFAULT_RELATIVE = ("_personal", "gcp-sa.json")
TIMEOUT_SECONDS = 30
DETAIL_LIMIT = 300

# a whole BEGIN...END block (or BEGIN to the end of the text), then anything shaped like a credential, then any long token
_BLOCK = re.compile(r"-----BEGIN [A-Z0-9 ]*-----.*?(?:-----END [A-Z0-9 ]*-----|\Z)", re.S)
_LONG_TOKEN = re.compile(r"[A-Za-z0-9+/=_-]{32,}")


def credentials_path(settings_file, environ=None):
    """Where this agent looks for the service-account key file: its own setting, never the platform's."""
    environ = os.environ if environ is None else environ
    given = environ.get(CREDENTIALS_ENV)
    if given:
        return Path(given)
    return Path(settings_file).parent.parent.joinpath(*DEFAULT_RELATIVE)


def clean_environment(ce):
    """The parts of a Google Batch environment the checks use, each judged again here whatever the platform judged: they reach a
    command line. Anything else in it is ignored."""
    if not isinstance(ce, dict) or ce.get("platform") != TYPE:
        raise rules.Refusal("the environment is not a Google Batch environment")
    project, location, work_dir = ce.get("project"), ce.get("location"), ce.get("workDir")
    if not (isinstance(project, str) and 6 <= len(project) <= 30 and compute_envs._GCB_PROJECT.match(project)):
        raise rules.Refusal("project is not a GCP project ID (專案 ID 不合規則)")
    if not (isinstance(location, str) and compute_envs._GCB_LOCATION.match(location)):
        raise rules.Refusal("location is not a region such as europe-west2 (區域不合規則)")
    if not (isinstance(work_dir, str) and work_dir.startswith("gs://") and compute_envs._GCB_BUCKET.match(work_dir[5:].partition("/")[0])):
        raise rules.Refusal("workDir is not a gs:// URL with a valid bucket name (workDir 不合規則)")
    email = ce.get("serviceAccountEmail")
    if email is not None and not (isinstance(email, str) and len(email) <= 200 and compute_envs._GCB_SA_EMAIL.match(email)):
        raise rules.Refusal("serviceAccountEmail is not a service-account e-mail address (服務帳號信箱不合規則)")
    cred = ce.get("credentialsId")
    if cred is not None and not (isinstance(cred, str) and compute_envs._CRED_NAME.match(cred)):
        raise rules.Refusal("credentialsId is not a credential name (憑證名字不合規則)")
    return {"name": str(ce.get("name"))[:100], "platform": TYPE, "credentialsId": cred, "project": project, "location": location,
            "workDir": work_dir, "serviceAccountEmail": email}


def _scrub(text):
    text = _BLOCK.sub("[hidden]", str(text))
    for pat in compute_envs._VALUE_PATTERNS:
        text = re.sub("(?:%s)\\S*" % pat.pattern, "[hidden]", text, flags=pat.flags)
    return _LONG_TOKEN.sub("[hidden]", text)


def _run(argv, env, timeout):
    """(return code, the first 300 characters of the output). Fixed argv, no shell (site.run_fixed). A timeout is raised to the caller."""
    rc, out = site.run_fixed(argv, env, timeout)
    return rc, str(out)[:DETAIL_LIMIT]


def _check(name, status, detail):
    return {"name": name, "status": status, "detail": str(detail)[:DETAIL_LIMIT]}


def _gcloud_env(cred_path):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("ABF_") and k != "GOOGLE_APPLICATION_CREDENTIALS"}
    env["CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE"] = str(cred_path)
    env["CLOUDSDK_CORE_DISABLE_PROMPTS"] = "1"
    return env


def _read_key(cred_path):
    """(the parsed key file or None, a problem sentence or None). Only keys are ever named in the problem, never a value."""
    try:
        with open(str(cred_path), encoding="utf-8") as f:
            data = json.loads(f.read(1000000))
    except (OSError, ValueError):
        return None, "the key file cannot be read as JSON (金鑰檔不是合法的 JSON; its content is not shown)"
    if not isinstance(data, dict):
        return None, "the key file is not a JSON object (金鑰檔不是 JSON 物件)"
    if data.get("type") != "service_account":
        return None, ("the key file is not a service-account key: its type is not service_account; only a service-account key file "
                      "is supported (只支援服務帳號金鑰檔)")
    missing = [k for k in ("client_email", "private_key") if k not in data]
    if missing:
        return None, "the key file lacks: %s (金鑰檔缺這些鍵)" % ", ".join(missing)
    return data, None


def run_preflight(env, *, cred_path, now=time.time, runner=None, which=None, stat=os.stat):
    """{'ok': bool, 'checks': [{'name', 'status', 'detail'}]} for a judged environment (see clean_environment).

    runner(argv, env, timeout) -> (return code, output); which(name) -> path or None. Both default to the real ones and are
    replaced by fakes in tests."""
    runner = runner or _run
    which = which or shutil.which
    project, location, work_dir = env["project"], env["location"], env["workDir"]
    checks = []

    if env.get("credentialsId"):
        checks.append(_check("credential_name", "pass", "credential name: %s" % env["credentialsId"]))
    else:
        checks.append(_check("credential_name", "fail", "give this environment a credential name (給這個環境一個憑證名字): "
                             "--credentials NAME. Only the name is stored; the key file stays on the agent's computer."))

    usable, key = False, None
    where = "the key file should be at %s" % cred_path
    try:
        st = stat(str(cred_path))
    except OSError:
        st = None
        checks.append(_check("credential_file", "fail", "no key file (找不到金鑰檔): %s. Put the service-account JSON there and "
                             "make it readable by this user only (chmod 600)." % where))
    else:
        if not stat_mod.S_ISREG(st.st_mode):
            checks.append(_check("credential_file", "fail", "%s, but it is not a regular file (不是一般檔案)" % where))
        elif sys.platform != "win32" and st.st_mode & 0o077:
            checks.append(_check("credential_file", "fail", "the key file's permissions are too open (權限太寬): group or others can "
                                 "read or write it. Run chmod 600 on %s" % cred_path))
        elif sys.platform == "win32":
            usable = True
            checks.append(_check("credential_file", "pass", "key file found; Windows 不檢查權限位 (permission bits are not checked)"))
        else:
            usable = True
            checks.append(_check("credential_file", "pass", "key file found, readable by the owner only"))

    shape_ok = False
    if usable:
        key, problem = _read_key(cred_path)
        shape_ok = problem is None
        checks.append(_check("credential_shape", "pass" if shape_ok else "fail",
                             "service-account key file: type, client_email and private_key are present" if shape_ok else problem))
    else:
        checks.append(_check("credential_shape", "unchecked", "no usable key file, so its shape was not checked"))

    if shape_ok:
        file_project = key.get("project_id")
        if file_project == project:
            checks.append(_check("credential_project", "pass", "the key file belongs to project %s" % project))
        else:
            ok_shape = isinstance(file_project, str) and 6 <= len(file_project) <= 30 and compute_envs._GCB_PROJECT.match(file_project)
            shown = file_project if ok_shape else "(not a project ID)"      # a project ID is not secret; anything else is not echoed
            checks.append(_check("credential_project", "fail", "the key file is for project %s, but this environment's project is "
                                 "%s (專案不一致)" % (shown, project)))
        key = None      # used up: nothing of the file is kept
    else:
        checks.append(_check("credential_project", "unchecked", "the key file was not read, so its project was not compared"))

    email = env.get("serviceAccountEmail")
    checks.append(_check("service_account", "pass", ("jobs run as %s" % email) if email
                         else "no serviceAccountEmail: the Compute Engine default account is used (用 Compute Engine 預設帳號)"))

    gcloud = which("gcloud")
    if gcloud:
        checks.append(_check("gcloud", "pass", "gcloud found"))
    else:
        checks.append(_check("gcloud", "unchecked", "gcloud is not installed on this computer (沒裝 gcloud), so the Batch API and the "
                             "bucket could not be checked; install the Google Cloud CLI"))

    bucket = work_dir[5:].partition("/")[0]
    for name, argv in (
            ("batch_api", ["gcloud", "batch", "jobs", "list", "--project", project, "--location", location,
                           "--limit", "1", "--format", "value(name)"]),
            ("bucket", ["gcloud", "storage", "ls", "gs://%s/" % bucket, "--project", project])):
        if not gcloud:
            checks.append(_check(name, "unchecked", "gcloud is not installed (沒裝 gcloud), so this was not checked"))
        elif not usable:
            checks.append(_check(name, "unchecked", "no usable key file, so this was not checked"))
        else:
            try:
                rc, out = runner(argv, _gcloud_env(cred_path), TIMEOUT_SECONDS)
            except TimeoutError:
                checks.append(_check(name, "fail", "逾時 (timed out after %d seconds); check the network and try again" % TIMEOUT_SECONDS))
                continue
            if rc == 0:
                checks.append(_check(name, "pass", "gcloud answered" + (" (the Batch API is reachable)" if name == "batch_api"
                                                                       else " (the bucket is reachable)")))
            else:
                checks.append(_check(name, "fail", ("gcloud failed (code %s): " % rc) + _scrub(out or "")))
    return {"ok": all(c["status"] == "pass" for c in checks), "checks": checks}
