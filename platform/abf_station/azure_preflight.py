# Nothing existing: the official azure Python packages are barred here and Nextflow has no free preflight, so this reads the Batch pool and the blob container with the az command line, one fixed argv each.
"""The preflight of an Azure Batch compute environment, run by the agent on the platform host.

It is read-only and free (預檢不計費): it asks Azure whether the Batch pool exists and is active, and whether the blob container
exists. It creates no pool and no job, and starts nothing. The credential file lives only on this side (INI, one `[default]`
section); the platform keeps only its name. Keys reach `az` through the environment of that one call, never through argv.
"""
import configparser
import os
import shutil
import stat as stat_mod
import sys
import tempfile
from pathlib import Path

from abf_platform import compute_envs      # the same shapes of region, account, container and pool as the platform applies

from . import rules, site
from .gcb_preflight import _check, _scrub  # the same scrubbing and result shape as the Google Batch preflight

TYPE = "azbatch-platform"
CREDENTIALS_ENV = "ABF_STATION_AZURE_CREDENTIALS"
DEFAULT_RELATIVE = ("_personal", "azure-credentials")
TIMEOUT_SECONDS = 30
DETAIL_LIMIT = 300
MAX_FILE = 1000000


def credentials_path(settings_file, environ=None):
    """Where this agent looks for the Azure credential file: its own setting, never the platform's."""
    environ = os.environ if environ is None else environ
    given = environ.get(CREDENTIALS_ENV)
    if given:
        return Path(given)
    return Path(settings_file).parent.parent.joinpath(*DEFAULT_RELATIVE)


def clean_environment(ce):
    """The parts of an Azure Batch environment the checks use, each judged again here whatever the platform judged: they reach a
    command line. Anything else in it is ignored."""
    if not isinstance(ce, dict) or ce.get("platform") != TYPE:
        raise rules.Refusal("the environment is not an Azure Batch environment")
    cred = ce.get("credentialsId")
    if cred is not None and not (isinstance(cred, str) and compute_envs._CRED_NAME.match(cred)):
        raise rules.Refusal("credentialsId is not a credential name (憑證名字不合規則)")
    config = {k: ce.get(k) for k in ("location", "batchAccountName", "storageAccountName", "workDir", "pool")}
    try:
        compute_envs._check_azure(config, "agent")
    except compute_envs.CEError as e:
        raise rules.Refusal(str(e)[:300])
    return {"name": str(ce.get("name"))[:100], "platform": TYPE, "credentialsId": cred, **config}


def _run(argv, env, timeout):
    """(return code, the first 300 characters of the output). Fixed argv, no shell (site.run_fixed). A timeout is raised to the caller."""
    rc, out = site.run_fixed(argv, env, timeout)
    return rc, str(out)[:DETAIL_LIMIT]


def _az_env(creds, env, config_dir):
    """The environment of one az call: nothing of the agent's own ABF or Azure variables; the keys travel here, never in argv."""
    e = {k: v for k, v in os.environ.items() if not k.upper().startswith(("ABF_", "AZURE_"))}
    e["AZURE_BATCH_ACCOUNT"] = env["batchAccountName"]
    e["AZURE_BATCH_ENDPOINT"] = "https://%s.%s.batch.azure.com" % (env["batchAccountName"], env["location"])
    e["AZURE_BATCH_ACCESS_KEY"] = creds["batch_account_key"]
    e["AZURE_STORAGE_ACCOUNT"] = env["storageAccountName"]
    if creds.get("storage_account_key"):
        e["AZURE_STORAGE_KEY"] = creds["storage_account_key"]
    else:
        e["AZURE_STORAGE_SAS_TOKEN"] = creds["storage_sas_token"]
    e["AZURE_CONFIG_DIR"] = config_dir
    e["AZURE_CORE_COLLECT_TELEMETRY"] = "false"
    e["AZURE_CORE_NO_COLOR"] = "true"
    e["AZURE_CORE_ONLY_SHOW_ERRORS"] = "true"
    return e


def _read_shape(cred_path):
    """(credentials or None, a problem sentence or None). Only key names are ever named in the problem, never a value."""
    try:
        with open(str(cred_path), "rb") as f:
            raw = f.read(MAX_FILE + 1)
    except OSError:
        return None, "the credential file cannot be read (讀不到憑證檔; its content is not shown)"
    if len(raw) > MAX_FILE:
        return None, "the credential file is larger than 1 MB, so it is not a credential file (憑證檔太大)"
    parser = configparser.RawConfigParser(interpolation=None, strict=False)
    try:
        parser.read_string(raw.decode("utf-8"))
    except (UnicodeDecodeError, configparser.Error):
        return None, "the credential file is not an INI file (憑證檔格式不是 INI; its content is not shown)"
    if not parser.has_section("default"):
        return None, "憑證檔沒有 [default] 區段 (the file %s has no [default] section; only [default] is used)" % cred_path
    sec = {k: (v or "").strip() for k, v in parser.items("default")}
    if not sec.get("batch_account_key"):
        return None, "[default] lacks: batch_account_key (缺這個鍵)"
    if not (sec.get("storage_account_key") or sec.get("storage_sas_token")):
        return None, "[default] lacks: storage_account_key or storage_sas_token (缺其中一個鍵)"
    return {k: sec.get(k, "") for k in ("batch_account_key", "storage_account_key", "storage_sas_token")}, None


def _call(runner, argv, creds, env):
    """(return code, output), each call with an empty config folder of its own that is deleted afterwards."""
    folder = tempfile.mkdtemp(prefix="abf-az-")
    try:
        return runner(argv, _az_env(creds, env, folder), TIMEOUT_SECONDS)
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def run_preflight(env, *, cred_path, now=None, runner=None, which=None, stat=os.stat):
    """{'ok': bool, 'checks': [{'name', 'status', 'detail'}]} for a judged environment (see clean_environment).

    runner(argv, env, timeout) -> (return code, output); which(name) -> path or None. Both default to the real ones and are
    replaced by fakes in tests."""
    runner = runner or _run
    which = which or shutil.which
    pool = env["pool"]
    container = env["workDir"][5:].partition("/")[0]
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
            checks.append(_check("credential_file", "fail", "%s, but it is not a regular file (not a regular file, 不是一般檔案)" % where))
        elif sys.platform != "win32" and st.st_mode & 0o077:
            checks.append(_check("credential_file", "fail", "the credential file's permissions are too open (權限太寬): group or "
                                 "others can read or write it. Run chmod 600 on %s" % cred_path))
        elif sys.platform == "win32":
            usable = True
            checks.append(_check("credential_file", "pass", "credential file found; Windows 不檢查權限位 (permission bits are not checked)"))
        else:
            usable = True
            checks.append(_check("credential_file", "pass", "credential file found, readable by the owner only"))

    creds = None
    if usable and env.get("credentialsId"):
        creds, problem = _read_shape(cred_path)
        checks.append(_check("credential_shape", "pass" if creds else "fail",
                             "[default] has batch_account_key and a storage key or sas token" if creds else problem))
    else:
        checks.append(_check("credential_shape", "unchecked", "no credential name or no usable credential file, so its shape was not checked"))

    az = which("az")
    if az:
        checks.append(_check("az", "pass", "az found"))
    else:
        checks.append(_check("az", "unchecked", "az 沒裝 (az is not installed on this computer), so the pool and the container could "
                             "not be checked; install the Azure CLI"))

    for name, argv in (
            ("pool", ["az", "batch", "pool", "show", "--pool-id", pool, "--query", "state", "--output", "tsv"]),
            ("storage", ["az", "storage", "container", "exists", "--name", container, "--query", "exists", "--output", "tsv",
                         "--auth-mode", "key"])):
        if not az:
            checks.append(_check(name, "unchecked", "az is not installed (沒裝 az), so this was not checked"))
        elif not creds:
            checks.append(_check(name, "unchecked", "no usable credential file, so this was not checked"))
        else:
            try:
                rc, out = _call(runner, argv, creds, env)
            except TimeoutError:
                checks.append(_check(name, "fail", "逾時 (timed out after %d seconds); check the network and try again" % TIMEOUT_SECONDS))
                continue
            out = str(out or "").strip()
            if rc != 0:
                if name == "pool":
                    checks.append(_check(name, "fail", ("pool %s 不存在於這個 Batch 帳號, or it could not be read (az failed, code %s): " % (pool, rc))
                                         + _scrub(out)))
                else:
                    checks.append(_check(name, "fail", ("az failed (code %s): " % rc) + _scrub(out)))
            elif name == "pool":
                state = out.lower()
                if state == "active":
                    checks.append(_check(name, "pass", "pool %s is active" % pool))
                else:
                    checks.append(_check(name, "fail", "pool %s is %s, not active (pool 狀態不是 active)" % (pool, _scrub(state)[:40] or "unknown")))
            else:
                if out.lower() == "true":
                    checks.append(_check(name, "pass", "container %s exists" % container))
                else:
                    checks.append(_check(name, "fail", "container %s does not exist (找不到這個容器)" % container))
    return {"ok": all(c["status"] == "pass" for c in checks), "checks": checks}
