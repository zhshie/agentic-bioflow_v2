# Not Seqera Platform's compute environments: they live in Seqera's service; this keeps the same model (type, config, credential name) in a small local SQLite table.
"""Compute environments in the Seqera model: a type, a config, and the NAME of a credential.

Slurm is the only type that can run. Google Cloud Batch can be created and checked (by the agent on the platform
host; launching comes later). AWS Batch and Azure Batch are served the same way (create, check, launch and cancel on the platform host). The other 10 types Seqera lists are stored
(their settings, nothing more) with the status `unsupported`: no code runs for them, no cloud
library is imported, and the check and listing refuse them at once. Nothing here holds a
credential: a value that looks like one is refused, and only the credential's name is kept.
"""
import json
import re
import sqlite3
import time

from . import common, store

# platform value (docs.seqera.io, "Available platform values") -> label. the feature's research notes (research.md).
KINDS = {
    "slurm-platform": "Slurm",
    "altair-platform": "PBS Pro",
    "lsf-platform": "IBM Spectrum LSF",
    "uge-platform": "Grid Engine",
    "moab-platform": "Moab",
    "awsbatch-platform": "AWS Batch",
    "awscloud-platform": "AWS Cloud",
    "azbatch-platform": "Azure Batch",
    "azcloud-platform": "Azure Cloud",
    "googlebatch-platform": "Google Cloud Batch",
    "googlecloud-platform": "Google Cloud",
    "k8s-platform": "Kubernetes",
    "eks-platform": "Amazon EKS",
    "gke-platform": "Google GKE",
}
SUPPORTED = "slurm-platform"                                  # the type that runs through an agent on the cluster
GOOGLE_BATCH = "googlebatch-platform"
AWS = "awsbatch-platform"
AZURE = "azbatch-platform"
PLATFORM_HOST_TYPES = (GOOGLE_BATCH, AWS, AZURE)                   # served by the agent that runs on the platform host: checked, launched and cancelled there (gcb-launch, aws-launch, azure-launch)
CHECK_ONLY_TYPES = ()                                            # 新雲端類型先放這裡，只開預檢
CLOUD_JOB_KINDS = {                                           # the job kinds each platform-host type takes; the rest is refused in plain words (the clean kind is split in two pieces: test_cleanup_store allows that word in no other file of this package)
    GOOGLE_BATCH: ("preflight", "launch_nextflow", "cancel_run", "clean_" "work", "put_upload", "pipeline_files"),
    AWS: ("preflight", "launch_nextflow", "cancel_run", "clean_" "work", "put_upload", "pipeline_files"),
    AZURE: ("preflight", "launch_nextflow", "cancel_run", "clean_" "work", "put_upload", "pipeline_files"),
}
CHECKABLE = (SUPPORTED,) + PLATFORM_HOST_TYPES + CHECK_ONLY_TYPES
SEQERA_COMPUTE = ("seqera-compute", "seqeracompute-platform")

CREATING, AVAILABLE, INVALID, UNSUPPORTED, DISABLED = "creating", "available", "invalid", "unsupported", "disabled"

NOT_SUPPORTED_MESSAGE = ("Not supported yet (尚未支援): a real account is needed to test this type before it can run "
                         "anything (需要一個真的帳號實測). Only its settings are stored.")
CREDENTIAL_ADVICE = ("looks like a credential (像憑證). The platform keeps only the NAME of a credential; keep the "
                     "credential itself on the agent side (憑證要放在代理那邊，平台只記名字).")


class CEError(Exception):
    """A request the platform refuses; the text says why and never repeats a rejected value."""


# ---- rules shared by the fields ----------------------------------------------------------

_NAME = re.compile(r"^[A-Za-z0-9_.-]+\Z")
_QUEUE = re.compile(r"^[A-Za-z0-9_.-]+\Z")
_PATH_CHARS = re.compile(r"^[A-Za-z0-9_./@+=:,-]+\Z")
_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}\Z")
_USER = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}\Z")
_CRED_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{0,99}\Z")
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}\Z")
_MODULE = re.compile(r"^[A-Za-z0-9_./+-]+\Z")
_SITE_VAR = re.compile(r"^[A-Z_][A-Z0-9_]*\Z")
_OWNER_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")                 # same rule as abf_launch.build.OWNER_NAME
_REVISION = re.compile(r"^(v?[0-9]+(\.[0-9]+){1,3}|[0-9a-f]{40})\Z")             # same rule as the launch module's REVISION
_SITE_PIPELINE_KEYS = ("pipeline", "revision", "module", "home")
MAX_PATH = 1024


def path_problem(value):
    """None when value is a plain absolute path; else a short code: type, empty, long, chars, dotdot, relative."""
    if not isinstance(value, str):
        return "type"
    if not value:
        return "empty"
    if len(value) > MAX_PATH:
        return "long"
    if not _PATH_CHARS.match(value):
        return "chars"
    if ".." in value.split("/"):
        return "dotdot"
    if not value.startswith("/"):
        return "relative"
    return None


def path_message(label, problem):
    return {
        "type": "%s must be text" % label,
        "empty": "%s is empty" % label,
        "long": "%s is longer than %d characters" % (label, MAX_PATH),
        "chars": "%s contains characters that are not allowed (含不允許的字元); use letters, digits and _ . / @ + = : , - only" % label,
        "dotdot": "%s contains '..' (含 ..), which is not allowed" % label,
        "relative": "%s must be an absolute path starting with / (a relative path is outside the allowed read roots, "
                    "在允許範圍之外)" % label,
    }[problem]


def normalize_path(value):
    """The path without a trailing slash or repeated slashes. Call it only on a path that has no problem."""
    parts = [p for p in value.split("/") if p and p != "."]
    return "/" + "/".join(parts)


# ---- credentials: refused by shape and by name -------------------------------------------------

_VALUE_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"aws_secret_access_key\s*[=:]", re.I),
    re.compile(r"abf_[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bexport\s+[A-Za-z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|KEY)[A-Za-z0-9_]*\s*=", re.I),
    re.compile(r"\b(?:password|passwd|secret|api[_-]?key|access[_-]?key|secret[_-]?key|token)\w*\s*[=:]\s*\S", re.I),
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),                # 014a: a model key typed into the wrong field is refused by name
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"AccountKey\s*=", re.I),                       # an Azure connection string or SAS typed into the wrong field
    re.compile(r"SharedAccessSignature\s*=", re.I),
    re.compile(r"[?&]sig=[A-Za-z0-9%+/=]{16,}"),
]


def looks_like_credential(text):
    return any(p.search(text) for p in _VALUE_PATTERNS)


def credential_findings(obj, where):
    """Field paths (never values) in obj that name a secret or hold something shaped like one."""
    found = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            here = "%s.%s" % (where, key)
            if common.is_secret_name(key):
                found.append(here)
            else:
                found += credential_findings(value, here)
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            if isinstance(value, dict) and "name" in value and "value" in value and common.is_secret_name(value["name"]):
                found.append("%s[%d].name" % (where, i))
            else:
                found += credential_findings(value, "%s[%d]" % (where, i))
    elif isinstance(obj, str):
        if looks_like_credential(obj):
            found.append(where)
    return found


# ---- validation --------------------------------------------------------------------------------

_COMMON_CONFIG = ("workDir", "preRunScript", "postRunScript", "environment", "nextflowConfig")
_SLURM_CONFIG = _COMMON_CONFIG + ("launchDir", "headQueue", "computeQueue", "maxQueueSize", "headJobOptions",
                                  "hostName", "userName", "port", "readRoots",
                                  "modules", "siteConfigVars", "sitePipelines", "suSite")


def _text(config, key, limit):
    v = config.get(key)
    if v is None:
        return
    if not isinstance(v, str):
        raise CEError("%s must be text" % key)
    if len(v) > limit:
        raise CEError("%s is longer than %d characters" % (key, limit))


def _check_environment(config):
    env = config.get("environment")
    if env is None:
        return
    if not isinstance(env, list) or len(env) > 200:
        raise CEError("environment must be a list of {name, value, head, compute}")
    clean = []
    for i, e in enumerate(env):
        if not isinstance(e, dict) or set(e) - {"name", "value", "head", "compute"}:
            raise CEError("environment[%d] must have only name, value, head and compute" % i)
        name, value = e.get("name"), e.get("value", "")
        if not isinstance(name, str) or not _ENV_NAME.match(name):
            raise CEError("environment[%d].name must be a variable name" % i)
        if not isinstance(value, str) or len(value) > 2000:
            raise CEError("environment[%d].value must be text of at most 2000 characters" % i)
        clean.append({"name": name, "value": value, "head": bool(e.get("head", True)),
                      "compute": bool(e.get("compute", False))})
    config["environment"] = clean


def _check_slurm(config):
    unknown = sorted(set(config) - set(_SLURM_CONFIG))
    if unknown:
        raise CEError("unknown setting for a Slurm environment: %s (known: %s)" % (unknown[0], ", ".join(_SLURM_CONFIG)))
    wd = config.get("workDir")
    if wd is None or wd == "":
        raise CEError("workDir is required for a Slurm environment (缺工作資料夾 workDir)")
    p = path_problem(wd)
    if p:
        raise CEError(path_message("workDir", p))
    config["workDir"] = normalize_path(wd)
    if config.get("launchDir") is not None:
        p = path_problem(config["launchDir"])
        if p:
            raise CEError(path_message("launchDir", p))
        config["launchDir"] = normalize_path(config["launchDir"])
    roots = config.get("readRoots")
    if roots is not None:
        if not isinstance(roots, list) or len(roots) > 50:
            raise CEError("readRoots must be a list of absolute paths")
        clean = []
        for r in roots:
            p = path_problem(r)
            if p:
                raise CEError(path_message("readRoots", p))
            clean.append(normalize_path(r))
        config["readRoots"] = clean
    hq = config.get("headQueue")
    if hq is None or hq == "":
        raise CEError("headQueue is required for a Slurm environment (缺主控佇列 headQueue)")
    for key in ("headQueue", "computeQueue"):
        v = config.get(key)
        if v is not None and (not isinstance(v, str) or not _QUEUE.match(v) or ".." in v):
            raise CEError("%s is not a valid queue name: letters, digits, _ . - only (佇列名稱不合法)" % key)
    if config.get("maxQueueSize") is not None:
        v = config["maxQueueSize"]
        if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 100000:
            raise CEError("maxQueueSize must be a whole number from 1 to 100000")
    if config.get("port") is not None:
        v = config["port"]
        if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 65535:
            raise CEError("port must be a whole number from 1 to 65535")
    if config.get("hostName") is not None and (not isinstance(config["hostName"], str) or not _HOST.match(config["hostName"])):
        raise CEError("hostName is not a valid host name")
    if config.get("userName") is not None and (not isinstance(config["userName"], str) or not _USER.match(config["userName"])):
        raise CEError("userName is not a valid user name")
    _text(config, "headJobOptions", 1000)
    _check_site_keys(config)


def _module_problem(value):
    if not isinstance(value, str):
        return "must be text"
    if value == "":
        return "is empty; use letters, digits and _ . / + - only"
    if not _MODULE.match(value):
        ch = next((c for c in value if not re.match(r"[A-Za-z0-9_./+-]", c)), "?")
        return "不允許 %r (not allowed); use letters, digits and _ . / + - only" % ch
    if ".." in value.split("/"):
        return "不允許 '..' (not allowed); a module name is not a path"
    return None


def _var_problem(value):
    if not isinstance(value, str) or not value or len(value) > 100 or not _SITE_VAR.match(value):
        return ("must be an environment variable name: capital letters, digits and _ only, not starting with a digit "
                "(大寫字母、數字、_)")
    return None


def _check_site_keys(config):
    """modules, siteConfigVars and sitePipelines (ce-nano4-keys): every problem is listed at once, each naming its key.
    A bad value is shown as one character at most, never whole."""
    errors = []
    site = config.get("suSite")
    if site is not None:
        from . import su      # inside the function: su imports jobs, which imports this module
        rates = su.load_rates()
        sites = (rates or {}).get("sites")
        if not isinstance(site, str) or not site:
            errors.append("suSite must be the name of a site in configs/sites/su_rates.json (站點名稱)")
        elif not isinstance(sites, dict):
            errors.append("suSite: 費率檔讀不到，無法確認站點 %s (the rates file cannot be read)" % site[:60])
        elif site not in sites:
            errors.append("suSite: 費率檔沒有站點 %s；可用的有 %s (no such site in configs/sites/su_rates.json)"
                          % (site[:60], ", ".join(sites)))
    for key, check in (("modules", _module_problem), ("siteConfigVars", _var_problem)):
        v = config.get(key)
        if v is None:
            continue
        if not isinstance(v, list) or len(v) > 100:
            errors.append("%s must be a list of text (at most 100)" % key)
            continue
        for i, item in enumerate(v):
            p = check(item)
            if p:
                errors.append("%s[%d]: %s" % (key, i, p))
    sp = config.get("sitePipelines")
    if sp is not None:
        if not isinstance(sp, list) or len(sp) > 100:
            errors.append("sitePipelines must be a list of {pipeline, revision, module, home}")
        else:
            for i, item in enumerate(sp):
                here = "sitePipelines[%d]" % i
                if not isinstance(item, dict) or set(item) != set(_SITE_PIPELINE_KEYS):
                    errors.append("%s must be an object with exactly pipeline, revision, module and home" % here)
                    continue
                if not isinstance(item["pipeline"], str) or not _OWNER_NAME.match(item["pipeline"]):
                    errors.append("%s.pipeline: must be owner/name, e.g. nf-core/ampliseq (letters, digits, _ . -)" % here)
                if not isinstance(item["revision"], str) or not _REVISION.match(item["revision"]):
                    errors.append("%s.revision: must be a release such as 2.18.0 or v2.18.0, or a 40-character commit id; "
                                  "a branch name is not accepted" % here)
                p = _module_problem(item["module"])
                if p:
                    errors.append("%s.module: %s" % (here, p))
                p = _var_problem(item["home"])
                if p:
                    errors.append("%s.home: %s" % (here, p))
    if errors:
        raise CEError("; ".join(errors))


_GCB_CONFIG = _COMMON_CONFIG + ("project", "location", "spot", "bootDiskSize", "bootDiskImage", "serviceAccountEmail",
                                "network", "subnetwork", "usePrivateAddress", "labels", "maxvCpus")
_GCB_PROJECT = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]\Z")
_GCB_LOCATION = re.compile(r"^[a-z]+-[a-z]+[0-9]+\Z")
_GCB_BUCKET = re.compile(r"^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]\Z")
_GCB_DISK = re.compile(r"^([0-9]{1,5}) ?GB\Z")
_GCB_IMAGE = re.compile(r"^[A-Za-z0-9_./:-]+\Z")
_GCB_SA_EMAIL = re.compile(r"^[A-Za-z0-9._-]+@(?:[a-z][a-z0-9-]*\.iam|developer)\.gserviceaccount\.com\Z")
_GCB_NET = re.compile(r"^(?:[a-z](?:[-a-z0-9]*[a-z0-9])?|projects/[a-z0-9-]+/(?:global/networks|regions/[a-z0-9-]+/subnetworks)/"
                      r"[a-z](?:[-a-z0-9]*[a-z0-9])?)\Z")
_GCB_LABEL_KEY = re.compile(r"^[a-z][a-z0-9_-]{0,62}\Z")
_GCB_LABEL_VALUE = re.compile(r"^[a-z0-9_-]{0,63}\Z")


def _shown(v):
    return repr(str(v)[:60])


def _check_gcb(config, agent):
    """A Google Cloud Batch environment: every problem is listed at once, each naming its key; a bad value is shown 60 characters
    at most. It needs an agent (the agent that runs on the platform host). No credential is held here: the key file
    stays on the agent's side and only its name is kept."""
    unknown = sorted(set(config) - set(_GCB_CONFIG))
    if unknown:
        raise CEError("unknown setting for a Google Batch environment: %s (known: %s)" % (unknown[0], ", ".join(_GCB_CONFIG)))
    errors = []
    if not agent:
        errors.append("agent is required: a Google Batch environment is checked by the agent that runs on the platform host, "
                      "so name it with --agent (需要指定一個站台代理，就是平台主機上的那個)")
    for key in ("project", "location", "workDir"):
        if config.get(key) is None or config.get(key) == "":
            errors.append("%s is required for a Google Batch environment (缺 %s)" % (key, key))
    v = config.get("project")
    if v not in (None, "") and not (isinstance(v, str) and 6 <= len(v) <= 30 and _GCB_PROJECT.match(v)):
        errors.append("project must be a GCP project ID: 6 to 30 characters, lower-case letters, digits and -, starting with a "
                      "letter and not ending with - (got %s)" % _shown(v))
    v = config.get("location")
    if v not in (None, "") and not (isinstance(v, str) and _GCB_LOCATION.match(v)):
        errors.append("location must be a region such as europe-west2 (got %s)" % _shown(v))
    v = config.get("workDir")
    if v not in (None, ""):
        problem = None
        if not isinstance(v, str) or not v.startswith("gs://"):
            problem = "workDir must be a gs:// URL such as gs://lab-bucket/work (got %s)" % _shown(v)
        else:
            bucket, _, prefix = v[5:].partition("/")
            if not _GCB_BUCKET.match(bucket):
                problem = ("workDir: the bucket name must be 3 to 63 characters of lower-case letters, digits and - _ . "
                           "(got %s)" % _shown(bucket))
            elif ".." in prefix.split("/") or any(ord(c) < 32 or ord(c) == 127 for c in prefix) or len(v) > MAX_PATH:
                problem = "workDir: the folder part must not contain '..' or control characters, or be longer than %d" % MAX_PATH
            else:
                prefix = prefix.rstrip("/")
                config["workDir"] = "gs://" + bucket + ("/" + prefix if prefix else "")
        if problem:
            errors.append(problem)
    for key in ("spot", "usePrivateAddress"):
        if config.get(key) is not None and not isinstance(config[key], bool):
            errors.append("%s must be true or false" % key)
    v = config.get("bootDiskSize")
    if v is not None:
        m = _GCB_DISK.match(v) if isinstance(v, str) else None
        if not m or not 1 <= int(m.group(1)) <= 2000:
            errors.append("bootDiskSize must be a whole number of GB from 1 to 2000, such as 50 GB (got %s)" % _shown(v))
    v = config.get("bootDiskImage")
    if v is not None and not (isinstance(v, str) and 0 < len(v) <= 200 and _GCB_IMAGE.match(v)):
        errors.append("bootDiskImage must be an image name of at most 200 characters (letters, digits and _ . / : -)")
    v = config.get("serviceAccountEmail")
    if v is not None and not (isinstance(v, str) and len(v) <= 200 and _GCB_SA_EMAIL.match(v)):
        errors.append("serviceAccountEmail must be an e-mail address like name@lab-project-1.iam.gserviceaccount.com "
                      "(an address, never a key) (got %s)" % _shown(v))
    for key in ("network", "subnetwork"):
        v = config.get(key)
        if v is not None and not (isinstance(v, str) and len(v) <= 300 and _GCB_NET.match(v)):
            errors.append("%s must be a VPC or subnet name (lower-case letters, digits, -) or a projects/... path (got %s)"
                          % (key, _shown(v)))
    v = config.get("labels")
    if v is not None:
        if not isinstance(v, dict):
            errors.append("labels must be an object of text pairs")
        elif len(v) > 64:
            errors.append("labels may have at most 64 pairs")
        else:
            for lk, lv in v.items():
                if not (isinstance(lk, str) and _GCB_LABEL_KEY.match(lk)) or not (isinstance(lv, str) and _GCB_LABEL_VALUE.match(lv)):
                    errors.append("labels: a key is lower-case letters, digits, _ - starting with a letter, a value lower-case "
                                  "letters, digits, _ -, each at most 63 characters (bad pair: %s)" % _shown(lk))
                    break
    v = config.get("maxvCpus")
    if v is not None and (isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 10000):
        errors.append("maxvCpus must be a whole number from 1 to 10000")
    if errors:
        raise CEError("; ".join(errors))


_AWS_CONFIG = _COMMON_CONFIG + ("region", "jobQueue", "spot", "maxvCpus")
_AWS_REGION = re.compile(r"^[a-z]{2}(-[a-z]+)+-[0-9]\Z")
_AWS_BUCKET = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]\Z")
_AWS_QUEUE = re.compile(r"^[A-Za-z0-9_-]{1,128}\Z")
_AWS_OLD_KEYS = ("headQueue", "computeQueue")


def _check_aws(config, agent):
    """An AWS Batch environment: every problem is listed at once, each naming its key; a bad value is shown 60 characters at most.
    It needs an agent (the one on the platform host). No credential is held here: the credential file stays on the agent's side
    and only its name is kept."""
    unknown = sorted(set(config) - set(_AWS_CONFIG))
    if unknown:
        msg = "unknown setting for an AWS Batch environment: %s (known: %s)" % (", ".join(str(k)[:60] for k in unknown), ", ".join(_AWS_CONFIG))
        if any(k in _AWS_OLD_KEYS for k in unknown):
            msg += ". 這是舊版的設定，請刪除後重建這個計算環境 (delete this environment and create it again)"
        raise CEError(msg)
    errors = []
    if not agent:
        errors.append("agent is required: an AWS Batch environment is checked by the agent that runs on the platform host, "
                      "so name it with --agent (需要指定一個站台代理，就是平台主機上的那個)")
    for key in ("region", "workDir", "jobQueue"):
        if config.get(key) is None or config.get(key) == "":
            errors.append("%s is required for an AWS Batch environment (缺 %s)%s" % (key, key, ", such as eu-west-1" if key == "region" else ""))
    v = config.get("region")
    if v not in (None, "") and not (isinstance(v, str) and _AWS_REGION.match(v)):
        errors.append("region must be an AWS region such as eu-west-1 (got %s)" % _shown(v))
    v = config.get("workDir")
    if v not in (None, ""):
        problem = None
        if not isinstance(v, str) or not v.startswith("s3://"):
            problem = "workDir must be an s3:// URL such as s3://lab-bucket/work (got %s)" % _shown(v)
        else:
            bucket, _, prefix = v[5:].partition("/")
            if not _AWS_BUCKET.match(bucket) or ".." in bucket:
                problem = ("workDir: the bucket name must be 3 to 63 characters of lower-case letters, digits, - and . "
                           "(got %s)" % _shown(bucket))
            elif ".." in prefix.split("/") or any(ord(c) < 32 or ord(c) == 127 for c in prefix) or len(v) > MAX_PATH:
                problem = "workDir: the folder part must not contain '..' or control characters, or be longer than %d" % MAX_PATH
            else:
                prefix = prefix.rstrip("/")
                config["workDir"] = "s3://" + bucket + ("/" + prefix if prefix else "")
        if problem:
            errors.append(problem)
    v = config.get("jobQueue")
    if v not in (None, "") and not (isinstance(v, str) and _AWS_QUEUE.match(v)):
        errors.append("jobQueue must be the queue's name (letters, digits, - and _, at most 128), not an ARN (got %s)" % _shown(v))
    if config.get("spot") is not None and not isinstance(config["spot"], bool):
        errors.append("spot must be true or false")
    v = config.get("maxvCpus")
    if v is not None and (isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 10000):
        errors.append("maxvCpus must be a whole number from 1 to 10000")
    if errors:
        raise CEError("; ".join(errors))


_AZURE_CONFIG = _COMMON_CONFIG + ("location", "batchAccountName", "storageAccountName", "workDir", "pool", "spot", "maxvCpus")
_AZURE_LOCATION = re.compile(r"^[a-z][a-z0-9]{2,39}\Z")
_AZURE_ACCOUNT = re.compile(r"^[a-z0-9]{3,24}\Z")
_AZURE_CONTAINER = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]\Z")
_AZURE_POOL = re.compile(r"^[A-Za-z0-9_-]{1,64}\Z")
_AZURE_OLD_KEYS = ("region", "vmType")


def _check_azure(config, agent):
    """An Azure Batch environment: every problem is listed at once, each naming its key; a bad value is shown 60 characters at most.
    It needs an agent (the one on the platform host). No credential is held here: the credential file stays on the agent's side
    and only its name is kept. The pool must already exist (the preflight only reads; nothing here creates one)."""
    unknown = sorted(set(config) - set(_AZURE_CONFIG))
    if unknown:
        msg = "unknown setting for an Azure Batch environment: %s (known: %s)" % (", ".join(str(k)[:60] for k in unknown), ", ".join(_AZURE_CONFIG))
        if any(k in _AZURE_OLD_KEYS for k in unknown):
            msg += ". 這是舊版的設定，請刪除後重建這個計算環境 (delete this environment and create it again)"
        raise CEError(msg)
    errors = []
    if not agent:
        errors.append("agent is required: an Azure Batch environment is checked by the agent that runs on the platform host, "
                      "so name it with --agent (需要指定一個站台代理，就是平台主機上的那個)")
    for key in ("location", "batchAccountName", "storageAccountName", "workDir", "pool"):
        if config.get(key) is None or config.get(key) == "":
            errors.append("%s is required for an Azure Batch environment (缺 %s)%s" % (key, key, ", such as westeurope" if key == "location" else ""))
    v = config.get("location")
    if v not in (None, "") and not (isinstance(v, str) and _AZURE_LOCATION.match(v)):
        errors.append("location must be an Azure region name in lower case without spaces, such as westeurope (got %s)" % _shown(v))
    for key in ("batchAccountName", "storageAccountName"):
        v = config.get(key)
        if v not in (None, "") and not (isinstance(v, str) and _AZURE_ACCOUNT.match(v)):
            errors.append("%s must be 3 to 24 lower-case letters and digits (got %s)" % (key, _shown(v)))
    v = config.get("workDir")
    if v not in (None, ""):
        problem = None
        if not isinstance(v, str) or not v.startswith("az://"):
            problem = "workDir must be an az:// URL with a folder, such as az://lab-container/work (got %s)" % _shown(v)
        else:
            container, _, sub = v[5:].partition("/")
            if not _AZURE_CONTAINER.match(container) or "--" in container:
                problem = ("workDir: the container name must be 3 to 63 characters of lower-case letters, digits and -, "
                           "starting and ending with a letter or digit (got %s)" % _shown(container))
            elif not sub.strip("/"):
                problem = "workDir needs a folder after the container, such as az://lab-container/work (got %s)" % _shown(v)
            elif ".." in sub.split("/") or any(ord(c) < 32 or ord(c) == 127 for c in sub) or len(v) > MAX_PATH:
                problem = "workDir: the folder part must not contain '..' or control characters, or be longer than %d" % MAX_PATH
            else:
                config["workDir"] = "az://" + container + "/" + sub.rstrip("/")
        if problem:
            errors.append(problem)
    v = config.get("pool")
    if v not in (None, "") and not (isinstance(v, str) and _AZURE_POOL.match(v)):
        errors.append("pool must be the pool's id (letters, digits, - and _, at most 64; the pool must already exist) (got %s)" % _shown(v))
    if config.get("spot") is not None and not isinstance(config["spot"], bool):
        errors.append("spot must be true or false")
    v = config.get("maxvCpus")
    if v is not None and (isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 10000):
        errors.append("maxvCpus must be a whole number from 1 to 10000")
    if errors:
        raise CEError("; ".join(errors))


def _check_other(config):
    """A type that is only modelled: no field schema, only the common checks."""
    for key, value in config.items():
        if not isinstance(key, str) or not key or len(key) > 100:
            raise CEError("a setting name must be 1 to 100 characters")
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            raise CEError("setting %s cannot be stored" % key)
    if len(json.dumps(config)) > 100000:
        raise CEError("the settings are too large")


def clean(fields):
    """Validate a whole record; returns {'name', 'description', 'platform', 'credentials_id', 'agent', 'config'}."""
    name = fields.get("name")
    if not isinstance(name, str) or not 1 <= len(name) <= 100:
        raise CEError("the name must be 1 to 100 characters (名字長度 1 到 100)")
    if not _NAME.match(name):
        raise CEError("the name may use letters, digits, _ . - only")
    platform = fields.get("platform")
    if platform in SEQERA_COMPUTE:
        raise CEError("Seqera Compute is Seqera's own hosted service and has no counterpart here (沒有對應), so it is "
                      "not a type you can create. Types: %s" % ", ".join(KINDS))
    if platform not in KINDS:
        raise CEError("unknown type %r. Types: %s" % (str(platform)[:60], ", ".join(KINDS)))
    desc = fields.get("description")
    if desc is not None and (not isinstance(desc, str) or len(desc) > 1000):
        raise CEError("description must be text of at most 1000 characters")
    cred = fields.get("credentialsId")
    if cred is not None and (not isinstance(cred, str) or not _CRED_NAME.match(cred)):
        raise CEError("credentialsId is the NAME of a credential (letters, digits, _ . : @ -), never the credential itself")
    agent = fields.get("agent")
    if agent is not None and (not isinstance(agent, str) or not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z", agent)):
        raise CEError("agent must be an agent name (letters, digits, _ . -)")
    config = fields.get("config")
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise CEError("config must be an object")
    config = json.loads(json.dumps(config))
    # first of all, before any rule that could repeat a value in its message
    bad = [b.lstrip(".") for b in credential_findings({"description": desc, "credentialsId": cred, "config": config}, "")]
    if bad:
        raise CEError("%s %s" % (bad[0], CREDENTIAL_ADVICE))
    for key in ("preRunScript", "postRunScript", "nextflowConfig"):
        _text(config, key, 20000)
    if config.get("workDir") is not None and not isinstance(config.get("workDir"), str):
        raise CEError("workDir must be text")
    _check_environment(config)
    if platform == SUPPORTED:
        _check_slurm(config)
    elif platform == GOOGLE_BATCH:
        _check_gcb(config, agent)
    elif platform == AWS:
        _check_aws(config, agent)
    elif platform == AZURE:
        _check_azure(config, agent)
    else:
        _check_other(config)
    owner = fields.get("owner_user_id")
    if owner is not None and (isinstance(owner, bool) or not isinstance(owner, int)):
        raise CEError("the owner must be a user id")
    return {"name": name, "description": desc, "platform": platform, "credentials_id": cred, "agent": agent,
            "config": config, "owner_user_id": owner}


# ---- storage -------------------------------------------------------------------------------------

def view(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "platform": row["platform"],
        "credentialsId": row["credentials_id"],
        "agent": row["agent"],
        "status": row["status"],
        "message": row["message"],
        "primary": bool(row["is_primary"]),
        "dateCreated": common.epoch_iso_ms(row["created_at"]),
        "lastUpdated": common.epoch_iso_ms(row["updated_at"]),
        "lastUsed": common.epoch_iso_ms(row["last_used_at"]),
        "config": json.loads(row["config_json"]),
    }


def get(state_path, name, owner=None):
    """The environment as a dict, or None. Opens the file read-only. With `owner` (a user id, 116) only that user's own environment
    is found: one that belongs to somebody else or to nobody is None, as a missing one is. owner=None is the local terminal."""
    con = store.open_readonly(state_path)
    if con is None:
        return None
    try:
        row = con.execute("SELECT * FROM compute_envs WHERE name = ?", (name,)).fetchone()
        if row is not None and owner is not None and row["owner_user_id"] != owner:
            row = None
        return view(row) if row else None
    except sqlite3.OperationalError:
        return None      # a platform.db made before 116 that no command has opened yet: nobody owns anything in it
    finally:
        con.close()


def list_all(state_path, owner=None):
    """Every environment; with `owner` (116) only that user's own."""
    con = store.open_readonly(state_path)
    if con is None:
        return []
    try:
        if owner is None:
            return [view(r) for r in con.execute("SELECT * FROM compute_envs ORDER BY id")]
        return [view(r) for r in con.execute("SELECT * FROM compute_envs WHERE owner_user_id = ? ORDER BY id", (owner,))]
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()


def owners(state_path):
    """{environment name: owner user id or None}, for the terminal commands that print who an environment belongs to."""
    con = store.open_readonly(state_path)
    if con is None:
        return {}
    try:
        return {r["name"]: r["owner_user_id"] for r in con.execute("SELECT name, owner_user_id FROM compute_envs")}
    except sqlite3.OperationalError:
        return {}
    finally:
        con.close()


def _agent_owner_problem(con, agent, owner):
    """The sentence that refuses an agent that is somebody else's, or None. An agent that has not said hello, or has no owner yet,
    is free; an agent with another owner is not."""
    if not agent:
        return None
    row = con.execute("SELECT owner_user_id FROM agents WHERE name = ?", (agent,)).fetchone()
    if row is not None and row["owner_user_id"] is not None and row["owner_user_id"] != owner:
        return "agent %s belongs to somebody else, so this environment cannot use it (這個代理是別人的，不能綁)" % agent[:64]
    return None


def _claim_agent(con, agent, owner):
    """An environment that has an owner takes the agent it uses when that agent has said hello and nobody owns it, so the owner can use
    what they were given (owner-binding). An agent that never said hello is left for its first token with a user. Runs inside the
    caller's transaction."""
    if owner is None or not agent:
        return
    con.execute("UPDATE agents SET owner_user_id = ? WHERE name = ? AND owner_user_id IS NULL", (owner, agent))


def _hand_agent_along(con, name, old_agent, new_agent, old_owner, new_owner):
    """`ce update --owner` on an environment whose agent (unchanged) belongs to the old owner gives that agent to the new owner too,
    so the new owner can use what they were given (116). An agent has one owner: if another environment of the old owner still
    uses it, the hand-over is refused and nothing changes. Runs inside the caller's transaction."""
    if new_owner is None or new_owner == old_owner or not new_agent or new_agent != old_agent:
        return
    row = con.execute("SELECT owner_user_id FROM agents WHERE name = ?", (new_agent,)).fetchone()
    if row is None or row["owner_user_id"] is None or row["owner_user_id"] != old_owner:
        return
    others = [r["name"] for r in con.execute(
        "SELECT name FROM compute_envs WHERE agent = ? AND name != ? AND owner_user_id IS ? ORDER BY name",
        (new_agent, name, old_owner))]
    if others:
        listed = ", ".join(others)[:200]
        raise CEError("agent %s also serves %s of the current owner, so it cannot move with this environment; move or rebind those first "
                      "(這個代理還在服務原擁有者的環境 %s，不能一起轉移)" % (new_agent[:64], listed, listed))
    con.execute("UPDATE agents SET owner_user_id = ? WHERE name = ?", (new_owner, new_agent))


def _row(con, name):
    row = con.execute("SELECT * FROM compute_envs WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise CEError("compute environment %r not found (找不到)" % name[:100])
    return row


def create(state_path, fields, clock=time.time):
    rec = clean(fields)
    supported = rec["platform"] in CHECKABLE
    status = CREATING if supported else UNSUPPORTED
    message = ("waiting for the first preflight (等待第一次預檢)" if supported else NOT_SUPPORTED_MESSAGE)
    now = clock()
    con = store.connect_state(state_path)
    try:
        with con:
            problem = _agent_owner_problem(con, rec["agent"], rec["owner_user_id"])
            if problem:
                raise CEError(problem)
            _claim_agent(con, rec["agent"], rec["owner_user_id"])
            try:
                con.execute(
                    "INSERT INTO compute_envs (name, description, platform, credentials_id, agent, status, message, "
                    "is_primary, config_json, created_at, updated_at, owner_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)",
                    (rec["name"], rec["description"], rec["platform"], rec["credentials_id"], rec["agent"], status,
                     message, json.dumps(rec["config"], sort_keys=True), now, now, rec["owner_user_id"]))
            except sqlite3.IntegrityError:
                raise CEError("a compute environment named %r already exists (名字重複)" % rec["name"])
        return view(_row(con, rec["name"]))
    finally:
        con.close()


def update(state_path, name, fields, clock=time.time):
    """Change the given top-level fields and config keys; the result must pass every rule again."""
    con = store.connect_state(state_path)
    try:
        with con:
            row = _row(con, name)
            cur = view(row)
            merged = {"name": cur["name"], "description": cur["description"], "platform": cur["platform"],
                      "credentialsId": cur["credentialsId"], "agent": cur["agent"], "config": dict(cur["config"]),
                      "owner_user_id": row["owner_user_id"]}
            for key in ("description", "credentialsId", "agent", "owner_user_id"):
                if key in fields:
                    merged[key] = fields[key]
            for key, value in (fields.get("config") or {}).items():
                merged["config"][key] = value
            rec = clean(merged)
            _hand_agent_along(con, name, cur["agent"], rec["agent"], row["owner_user_id"], rec["owner_user_id"])
            problem = _agent_owner_problem(con, rec["agent"], rec["owner_user_id"])
            if problem:
                raise CEError(problem)
            _claim_agent(con, rec["agent"], rec["owner_user_id"])
            # an environment that changes hands stops being the primary one of its old owner
            con.execute("UPDATE compute_envs SET description = ?, credentials_id = ?, agent = ?, config_json = ?, "
                        "updated_at = ?, is_primary = CASE WHEN owner_user_id IS ? THEN is_primary ELSE 0 END, owner_user_id = ? "
                        "WHERE name = ?",
                        (rec["description"], rec["credentials_id"], rec["agent"],
                         json.dumps(rec["config"], sort_keys=True), clock(), rec["owner_user_id"], rec["owner_user_id"], name))
            if row["status"] == UNSUPPORTED and rec["platform"] in CHECKABLE:
                # a record made before the type was checked, now complete under today's rules: it waits for its first preflight
                con.execute("UPDATE compute_envs SET status = ?, message = ?, checked_ok = 0 WHERE name = ?",
                            (CREATING, "waiting for the first preflight (等待第一次預檢)", name))
        return view(_row(con, name))
    finally:
        con.close()


def set_primary(state_path, name, clock=time.time):
    con = store.connect_state(state_path)
    try:
        with con:
            row = _row(con, name)
            if row["status"] == UNSUPPORTED:
                raise CEError("an unsupported environment cannot be primary (尚未支援的環境不能當主要): %s" % name)
            if row["status"] == DISABLED:
                raise CEError("a disabled environment cannot be primary (已停用的環境不能當主要): %s" % name)
            # primary is per owner (116): making one environment primary leaves the primary of every other owner as it is
            con.execute("UPDATE compute_envs SET is_primary = 0 WHERE is_primary = 1 AND name != ? AND owner_user_id IS ?",
                        (name, row["owner_user_id"]))
            con.execute("UPDATE compute_envs SET is_primary = 1, updated_at = ? WHERE name = ?", (clock(), name))
        return view(_row(con, name))
    finally:
        con.close()


def disable(state_path, name, clock=time.time):
    con = store.connect_state(state_path)
    try:
        with con:
            _row(con, name)
            con.execute("UPDATE compute_envs SET status = ?, message = ?, is_primary = 0, updated_at = ? WHERE name = ?",
                        (DISABLED, "disabled (已停用): no new job is accepted", clock(), name))
        return view(_row(con, name))
    finally:
        con.close()


def enable(state_path, name, clock=time.time):
    con = store.connect_state(state_path)
    try:
        with con:
            row = _row(con, name)
            if row["status"] != DISABLED:
                raise CEError("%s is not disabled" % name)
            if row["checked_ok"] == 1:
                status, message = AVAILABLE, "enabled again; the last preflight had passed (重新啟用)"
            else:
                status, message = CREATING, "enabled again; waiting for a preflight (重新啟用，等待預檢)"
            con.execute("UPDATE compute_envs SET status = ?, message = ?, updated_at = ? WHERE name = ?",
                        (status, message, clock(), name))
        return view(_row(con, name))
    finally:
        con.close()


def set_message(state_path, name, message, only_status=None, clock=time.time):
    """Change the message only (the status stays). With only_status the message is written only while the
    environment still has that status, so a verdict that arrived in between is never overwritten."""
    con = store.connect_state(state_path)
    try:
        with con:
            sql = "UPDATE compute_envs SET message = ?, updated_at = ? WHERE name = ?"
            args = [message, clock(), name]
            if only_status:
                sql += " AND status = ?"
                args.append(only_status)
            con.execute(sql, args)
    finally:
        con.close()


def snapshot(row_or_view):
    """What an agent is told about an environment: only what a job needs, never anything else."""
    v = row_or_view if "config" in row_or_view else view(row_or_view)
    c = v["config"]
    if v["platform"] == GOOGLE_BATCH:             # the agent on the platform host needs the settings of its checks, and the credential's name
        return {"name": v["name"], "platform": v["platform"], "credentialsId": v["credentialsId"],
                "project": c.get("project"), "location": c.get("location"), "workDir": c.get("workDir"),
                "serviceAccountEmail": c.get("serviceAccountEmail")}
    if v["platform"] == AWS:
        return {"name": v["name"], "platform": v["platform"], "credentialsId": v["credentialsId"],
                "region": c.get("region"), "workDir": c.get("workDir"), "jobQueue": c.get("jobQueue"),
                "spot": c.get("spot"), "maxvCpus": c.get("maxvCpus")}
    if v["platform"] == AZURE:
        return {"name": v["name"], "platform": v["platform"], "credentialsId": v["credentialsId"],
                "location": c.get("location"), "batchAccountName": c.get("batchAccountName"),
                "storageAccountName": c.get("storageAccountName"), "workDir": c.get("workDir"), "pool": c.get("pool")}
    library = next((e.get("value") for e in (c.get("environment") or []) if isinstance(e, dict)
                    and e.get("name") == "NXF_SINGULARITY_LIBRARYDIR"), None)      # the one variable a preflight needs; no other is carried
    return {"name": v["name"], "platform": v["platform"], "workDir": c.get("workDir"), "launchDir": c.get("launchDir"),
            "headQueue": c.get("headQueue"), "computeQueue": c.get("computeQueue"),
            "readRoots": list(c.get("readRoots") or []), "modules": list(c.get("modules") or []),
            "siteConfigVars": list(c.get("siteConfigVars") or []),
            "sitePipelines": [dict(p) for p in (c.get("sitePipelines") or [])],
            "singularityLibraryDir": library if isinstance(library, str) and library else None}


def verdict_message(ok, checks):
    if ok:
        return "preflight passed (預檢通過): " + ", ".join(c["name"] for c in checks)
    bad = ["%s: %s" % (c["name"], c["detail"]) for c in checks if c["status"] != "pass"]
    return "preflight failed (預檢未通過): " + "; ".join(bad)


def apply_preflight(con, name, ok, checks, now):
    """Record an agent's verdict on the environment, inside the caller's transaction."""
    row = con.execute("SELECT status FROM compute_envs WHERE name = ?", (name,)).fetchone()
    if row is None or row["status"] in (DISABLED, UNSUPPORTED):
        return
    con.execute("UPDATE compute_envs SET status = ?, message = ?, checked_ok = ?, updated_at = ? WHERE name = ?",
                (AVAILABLE if ok else INVALID, verdict_message(ok, checks), 1 if ok else 0, now, name))
