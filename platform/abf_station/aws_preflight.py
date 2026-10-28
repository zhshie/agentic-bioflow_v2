# Nothing existing: searched Nextflow's awsbatch executor and Seqera's AWS Batch form; neither ships a check that runs offline and free, and the official Python packages are barred by TC-085, so this calls the aws command line.
"""The preflight of an AWS Batch environment, run by the station agent that sits on the platform host.

Everything here only reads: it reads the credential file, asks who the key is (`aws sts get-caller-identity`), describes one job
queue (`aws batch describe-job-queues`) and heads one bucket (`aws s3api head-bucket`). It creates no Batch job, writes no bucket
and creates no role, so it costs nothing (預檢不計費; it creates no Batch job). The credential file's content is parsed in memory
for key names only and dropped; it never reaches a result, a message or the platform's database.

Where the credential file lives is the agent's own setting: the environment variable ABF_STATION_AWS_CREDENTIALS, else
`<deployment>/_personal/aws-credentials` (the deployment is the folder that holds config/env.yaml). It is an INI file; only its
`[default]` section is used.
"""
import configparser
import os
import shutil
import stat as stat_mod
import sys
import time
from pathlib import Path

from abf_platform import compute_envs      # the same shapes of region, bucket and queue as the platform applies when it stores them

from . import rules, site
from .gcb_preflight import _check, _scrub  # the same scrubbing and result shape as the Google Batch preflight

TYPE = "awsbatch-platform"
CREDENTIALS_ENV = "ABF_STATION_AWS_CREDENTIALS"
DEFAULT_RELATIVE = ("_personal", "aws-credentials")
TIMEOUT_SECONDS = 30
DETAIL_LIMIT = 300
MAX_FILE = 1000000


def credentials_path(settings_file, environ=None):
    """Where this agent looks for the AWS credential file: its own setting, never the platform's."""
    environ = os.environ if environ is None else environ
    given = environ.get(CREDENTIALS_ENV)
    if given:
        return Path(given)
    return Path(settings_file).parent.parent.joinpath(*DEFAULT_RELATIVE)


def clean_environment(ce):
    """The parts of an AWS Batch environment the checks use, each judged again here whatever the platform judged: they reach a
    command line. Anything else in it is ignored."""
    if not isinstance(ce, dict) or ce.get("platform") != TYPE:
        raise rules.Refusal("the environment is not an AWS Batch environment")
    region, work_dir, queue = ce.get("region"), ce.get("workDir"), ce.get("jobQueue")
    if not (isinstance(region, str) and compute_envs._AWS_REGION.match(region)):
        raise rules.Refusal("region is not an AWS region such as eu-west-1 (區域不合規則)")
    bucket = work_dir[5:].partition("/")[0] if isinstance(work_dir, str) and work_dir.startswith("s3://") else ""
    if not (compute_envs._AWS_BUCKET.match(bucket) and ".." not in bucket):
        raise rules.Refusal("workDir is not an s3:// URL with a valid bucket name (workDir 不合規則)")
    if not (isinstance(queue, str) and compute_envs._AWS_QUEUE.match(queue)):
        raise rules.Refusal("jobQueue is not a job queue name (佇列名字不合規則)")
    cred = ce.get("credentialsId")
    if cred is not None and not (isinstance(cred, str) and compute_envs._CRED_NAME.match(cred)):
        raise rules.Refusal("credentialsId is not a credential name (憑證名字不合規則)")
    return {"name": str(ce.get("name"))[:100], "platform": TYPE, "credentialsId": cred, "region": region,
            "workDir": work_dir, "jobQueue": queue}


def _run(argv, env, timeout):
    """(return code, the first 300 characters of the output). Fixed argv, no shell (site.run_fixed). A timeout is raised to the caller."""
    rc, out = site.run_fixed(argv, env, timeout)
    return rc, str(out)[:DETAIL_LIMIT]


def _aws_env(cred_path, region):
    """The environment of one aws call: nothing of the agent's own AWS or ABF variables, the credential file by path only."""
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith("ABF_") and not (k.upper().startswith("AWS_") and k.upper() != "AWS_CA_BUNDLE")}
    env["AWS_SHARED_CREDENTIALS_FILE"] = str(cred_path)
    env["AWS_PROFILE"] = "default"
    env["AWS_CONFIG_FILE"] = os.devnull
    env["AWS_DEFAULT_REGION"] = region
    env["AWS_PAGER"] = ""
    env["AWS_EC2_METADATA_DISABLED"] = "true"
    return env


def _read_shape(cred_path):
    """A problem sentence or None. Only key names are ever named in the problem, never a value."""
    try:
        with open(str(cred_path), "rb") as f:
            raw = f.read(MAX_FILE + 1)
    except OSError:
        return "the credential file cannot be read (讀不到憑證檔; its content is not shown)"
    if len(raw) > MAX_FILE:
        return "the credential file is larger than 1 MB, so it is not a credential file (憑證檔太大)"
    parser = configparser.RawConfigParser(interpolation=None, strict=False)
    try:
        parser.read_string(raw.decode("utf-8"))
    except (UnicodeDecodeError, configparser.Error):
        return "the credential file is not an INI file (憑證檔格式不是 INI; its content is not shown)"
    if not parser.has_section("default"):
        return "憑證檔沒有 [default] 區段 (the file %s has no [default] section; only [default] is used)" % cred_path
    keys = set(parser.options("default"))
    if "credential_process" in keys:
        return "[default] has credential_process, which runs a program; it is not allowed (不允許 credential_process)"
    missing = [k for k in ("aws_access_key_id", "aws_secret_access_key") if k not in keys]
    if missing:
        return "[default] lacks: %s (缺這些鍵)" % ", ".join(missing)
    return None


def run_preflight(env, *, cred_path, now=time.time, runner=None, which=None, stat=os.stat):
    """{'ok': bool, 'checks': [{'name', 'status', 'detail'}]} for a judged environment (see clean_environment).

    runner(argv, env, timeout) -> (return code, output); which(name) -> path or None. Both default to the real ones and are
    replaced by fakes in tests."""
    runner = runner or _run
    which = which or shutil.which
    region, work_dir, queue = env["region"], env["workDir"], env["jobQueue"]
    checks = []

    if env.get("credentialsId"):
        checks.append(_check("credential_name", "pass", "credential name: %s" % env["credentialsId"]))
    else:
        checks.append(_check("credential_name", "fail", "give this environment a credential name (給這個環境一個憑證名字): "
                             "--credentials NAME. Only the name is stored; the credential file stays on the agent's computer."))

    usable = False
    where = "the credential file should be at %s" % cred_path
    try:
        st = stat(str(cred_path))
    except OSError:
        checks.append(_check("credential_file", "fail", "no credential file (找不到憑證檔): %s. Put the [default] credentials there "
                             "and make it readable by this user only (chmod 600)." % where))
    else:
        if not stat_mod.S_ISREG(st.st_mode):
            checks.append(_check("credential_file", "fail", "%s, but it is not a regular file (不是一般檔案)" % where))
        elif sys.platform != "win32" and st.st_mode & 0o077:
            checks.append(_check("credential_file", "fail", "the credential file's permissions are too open (權限太寬): group or "
                                 "others can read or write it. Run chmod 600 on %s" % cred_path))
        elif sys.platform == "win32":
            usable = True
            checks.append(_check("credential_file", "pass", "credential file found; Windows 不檢查權限位 (permission bits are not checked)"))
        else:
            usable = True
            checks.append(_check("credential_file", "pass", "credential file found, readable by the owner only"))

    shape_ok = False
    if usable and env.get("credentialsId"):
        problem = _read_shape(cred_path)
        shape_ok = problem is None
        checks.append(_check("credential_shape", "pass" if shape_ok else "fail",
                             "[default] has aws_access_key_id and aws_secret_access_key" if shape_ok else problem))
    else:
        checks.append(_check("credential_shape", "unchecked", "no credential name or no usable credential file, so its shape was not checked"))

    aws = which("aws")
    if aws:
        checks.append(_check("aws", "pass", "aws found"))
    else:
        checks.append(_check("aws", "unchecked", "aws is not installed on this computer (沒裝 aws), so the key, the job queue and the "
                             "bucket could not be checked; install the AWS CLI"))

    bucket = work_dir[5:].partition("/")[0]
    for name, argv in (
            ("identity", ["aws", "sts", "get-caller-identity", "--region", region, "--query", "Account", "--output", "text"]),
            ("job_queue", ["aws", "batch", "describe-job-queues", "--job-queues", queue, "--region", region,
                           "--query", "jobQueues[].state", "--output", "text"]),
            ("bucket", ["aws", "s3api", "head-bucket", "--bucket", bucket, "--region", region])):
        if not aws:
            checks.append(_check(name, "unchecked", "aws is not installed (沒裝 aws), so this was not checked"))
        elif not (usable and shape_ok):
            checks.append(_check(name, "unchecked", "no usable credential file, so this was not checked"))
        else:
            try:
                rc, out = runner(argv, _aws_env(cred_path, region), TIMEOUT_SECONDS)
            except TimeoutError:
                checks.append(_check(name, "fail", "逾時 (timed out after %d seconds); check the network and try again" % TIMEOUT_SECONDS))
                continue
            if rc != 0:
                checks.append(_check(name, "fail", ("aws failed (code %s): " % rc) + _scrub(out or "")))
            elif name == "identity":
                checks.append(_check(name, "pass", "the key answered"))
            elif name == "job_queue":
                state = str(out or "").strip()
                if state == "ENABLED":
                    checks.append(_check(name, "pass", "job queue %s is ENABLED" % queue))
                elif not state:
                    checks.append(_check(name, "fail", "job queue %s was not found in %s (找不到這個佇列)" % (queue, region)))
                else:
                    checks.append(_check(name, "fail", "job queue %s is %s, not ENABLED (佇列未啟用)" % (queue, _scrub(state)[:40])))
            else:
                checks.append(_check(name, "pass", "the bucket is reachable"))
    return {"ok": all(c["status"] == "pass" for c in checks), "checks": checks}
