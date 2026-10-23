# Nothing existing: the agent's own allow-list of paths, queue names and read roots; it is a second lock on purpose, written separately from the platform's so one mistake cannot open both.
"""What the agent accepts, judged again here whatever the platform already judged.

A path must be absolute, made of plain characters only, free of '..', and inside one of the places the
agent may read: the environment's work folder and launch folder, the read roots named in its settings, and
the deployment's storage_root. Nothing else is listed.
"""
import re

from abf_platform import compute_envs      # the same rules for a module name and a site variable as the platform applies when it stores them

MAX_PATH = 1024
_PATH_CHARS = re.compile(r"^[A-Za-z0-9_./@+=:,-]+\Z")
_QUEUE = re.compile(r"^[A-Za-z0-9_.-]+\Z")

SLURM = "slurm-platform"


class Refusal(Exception):
    """The agent will not do this; the text goes back to the platform as the reason."""


def path_problem(value):
    """None for a plain absolute path, else: type, empty, long, chars, dotdot, relative."""
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


def path_reason(label, problem):
    return {
        "type": "%s must be text" % label,
        "empty": "%s is empty" % label,
        "long": "%s is longer than %d characters" % (label, MAX_PATH),
        "chars": "%s contains characters that are not allowed (含不允許的字元)" % label,
        "dotdot": "%s contains '..' (含 ..)" % label,
        "relative": "%s is not an absolute path, so it is outside the allowed read roots (在允許範圍之外)" % label,
    }[problem]


def normalize(value):
    return "/" + "/".join(p for p in value.split("/") if p and p != ".")


def components(value):
    return [p for p in value.split("/") if p and p != "."]


def inside(path, roots):
    """True when path is a root or lies below one; compared by whole path components, never by prefix text."""
    want = components(path)
    for root in roots:
        r = components(root)
        if want[:len(r)] == r:
            return True
    return False


def clean_path(value, label="path"):
    problem = path_problem(value)
    if problem:
        raise Refusal(path_reason(label, problem))
    return normalize(value)


def clean_root(value, label):
    """A path that may be a read root: it must not be the top of the file system."""
    path = clean_path(value, label)
    if path == "/":
        raise Refusal("%s cannot be the top of the file system" % label)
    return path


def clean_queue(value, label):
    if not isinstance(value, str) or not _QUEUE.match(value):
        raise Refusal("%s is not a valid queue name (letters, digits, _ . - only)" % label)
    return value


def clean_environment(ce):
    """The parts of an environment the agent uses, each judged. Anything else in it is ignored."""
    if not isinstance(ce, dict):
        raise Refusal("the environment is missing from the job")
    if ce.get("platform") != SLURM:
        raise Refusal("only a Slurm environment can run jobs; this type is not supported (不支援)")
    out = {"workDir": clean_root(ce.get("workDir"), "workDir"), "launchDir": None, "readRoots": [],
           "headQueue": clean_queue(ce.get("headQueue"), "headQueue"), "computeQueue": None}
    if ce.get("launchDir") is not None:
        out["launchDir"] = clean_root(ce["launchDir"], "launchDir")
    if ce.get("computeQueue") is not None:
        out["computeQueue"] = clean_queue(ce["computeQueue"], "computeQueue")
    roots = ce.get("readRoots")
    if roots is not None:
        if not isinstance(roots, list) or len(roots) > 50:
            raise Refusal("readRoots must be a list of paths")
        out["readRoots"] = [clean_root(r, "readRoots") for r in roots]
    for key in ("modules", "siteConfigVars"):      # names only, never commands; launch.py judges them again when it builds the script
        v = ce.get(key)
        if v is not None and (not isinstance(v, list) or len(v) > 100 or not all(isinstance(i, str) for i in v)):
            raise Refusal("%s must be a list of text" % key)
        out[key] = list(v or [])
    sp = ce.get("sitePipelines")
    if sp is not None and (not isinstance(sp, list) or len(sp) > 100 or not all(
            isinstance(i, dict) and set(i) == {"pipeline", "revision", "module", "home"}
            and all(isinstance(x, str) for x in i.values()) for i in sp)):
        raise Refusal("sitePipelines must be a list of {pipeline, revision, module, home}")
    out["sitePipelines"] = [dict(i) for i in (sp or [])]
    for i, name in enumerate(out["modules"]):      # these reach a shell command on the site in preflight: judged again here
        problem = compute_envs._module_problem(name)
        if problem:
            raise Refusal("內容不合規則：modules[%d] %s" % (i, problem))
    for i, item in enumerate(out["sitePipelines"]):
        problem = compute_envs._module_problem(item["module"])
        if problem:
            raise Refusal("內容不合規則：sitePipelines[%d].module %s" % (i, problem))
        problem = compute_envs._var_problem(item["home"])
        if problem:
            raise Refusal("內容不合規則：sitePipelines[%d].home %s" % (i, problem))
    out["singularityLibraryDir"] = None
    if ce.get("singularityLibraryDir") is not None:
        out["singularityLibraryDir"] = clean_root(ce["singularityLibraryDir"], "singularityLibraryDir")
    return out


def read_setting(settings_file, key):
    """One `key: value` line of the deployment's settings file, read the way scripts/settings.sh reads it."""
    try:
        with open(settings_file, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r"^\s*%s\s*:\s*(.*)$" % re.escape(key), line)
                if m:
                    return re.sub(r"\s*#.*$", "", m.group(1)).strip()
    except OSError:
        return ""
    return ""


def allowed_roots(env, settings_file):
    roots = [env["workDir"]]
    if env["launchDir"]:
        roots.append(env["launchDir"])
    roots += env["readRoots"]
    storage = read_setting(settings_file, "storage_root")
    if storage and path_problem(storage) is None and normalize(storage) != "/":
        roots.append(normalize(storage))
    return roots
