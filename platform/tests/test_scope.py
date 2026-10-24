# Nothing existing: static checks of platform/ against constitution principles 1, 2, 3 and the 008 scope; the repo's own checks do not scan this folder.
"""Scope and constitution checks for platform/ (feature 008).

The four existing check files (tests/no_hardcoded_paths.sh, tests/scripts_name_their_alternative.sh,
tests/no_second_run_state_test.sh, tests/run_all.sh) stay untouched and do not scan platform/,
so the same rules run here.
"""
import re
import subprocess
import time
from pathlib import Path

from helpers import PLATFORM_DIR, REPO_ROOT

PKG = PLATFORM_DIR / "abf_platform"
STATION = PLATFORM_DIR / "abf_station"


def _sources():
    return sorted(p for p in PKG.rglob("*.py"))


def _header_sources():
    """Feature 007 (plan Revision 2 item 8): the header rule covers the agent package too."""
    return _sources() + sorted(p for p in STATION.rglob("*.py"))


def _all_platform_files():
    out = []
    for p in PLATFORM_DIR.rglob("*"):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".pyc", ".db"):
            out.append(p)
    return sorted(out)


# ---- TC-070: principle 1, every source names the alternative it is not -------------

PATTERN = re.compile(r"^#\s*(Not\s+.+:|Nothing existing:)")
IN_REPO_PHRASES = re.compile(
    r"^(a|an|the)\s+(hook|gate|second|new|copy of|shell function|real .*implementation)|"
    r"^(writing|rewriting|duplicating)\s|^(this|our)\s+(repo|plugin|own)|^\"?(a|an)\s+second", re.I)


def _repo_names():
    names = set()
    for d in ("scripts", "hooks", "tests", "commands", "skills", "docs"):
        for p in (REPO_ROOT / d).rglob("*"):
            if p.is_file() and p.suffix in (".sh", ".py", ".awk", ".md"):
                names.add(p.name)
    return names


def judge(path, repo_names):
    """Same rule as tests/scripts_name_their_alternative.sh; returns a problem string or ''."""
    lines = path.read_text(encoding="utf-8").splitlines()[:40]
    hit = next((ln for ln in lines if PATTERN.match(ln)), None)
    if hit is None:
        return "MISSING %s" % path.name
    reason = hit.split(":", 1)[1].strip()
    if len(reason) < 15:
        return "SHORT %s" % path.name
    if hit.lstrip("# \t").startswith("Nothing existing:"):
        return ""
    x = re.sub(r"^#\s*Not\s+", "", hit)
    x = x.split(":", 1)[0]
    if re.search(r"scripts/|hooks/|tests/|commands/|skills/|docs/", x):
        return "IN-REPO %s" % path.name
    for word in re.split(r"[^A-Za-z0-9_.-]+", x):
        if word.rstrip(".") in repo_names:
            return "IN-REPO %s names %s" % (path.name, word)
    if IN_REPO_PHRASES.search(x):
        return "IN-REPO %s" % path.name
    return ""


def test_tc070_every_python_source_names_its_alternative(tmp_path):
    # TC-070
    names = _repo_names()
    files = _header_sources() + sorted((PLATFORM_DIR / "tests").glob("*.py"))
    assert (PKG / "cli.py") in files, "cli.py must exist and be checked"
    assert (STATION / "agent.py") in files and (STATION / "handlers.py") in files, "abf_station must be checked"
    problems = [judge(f, names) for f in files]
    assert [p for p in problems if p] == []
    # the rule must be able to go red
    bad = tmp_path / "no_header.py"
    bad.write_text("import os\n# just prose, no answer to the question\n")
    assert judge(bad, names).startswith("MISSING")
    short = tmp_path / "short.py"
    short.write_text("# Not tmux: short\n")
    assert judge(short, names).startswith("SHORT")
    inrepo = tmp_path / "inrepo.py"
    inrepo.write_text("# Not status.sh: a second reader would duplicate it, nothing more.\n")
    assert judge(inrepo, names).startswith("IN-REPO")
    ok = tmp_path / "ok.py"
    ok.write_text("# Not nf-shard: no auth, TypeScript with Postgres, stale since 2024-09\n")
    assert judge(ok, names) == ""


# ---- TC-071: principle 2, no second truth, no submission, no daemon --------------

def test_tc071_no_submission_no_resident_loop_no_committed_database():
    # TC-071
    forbidden = [
        (r"nextflow\s+run", "submits a run"),
        (r"\bsbatch\b|\bsrun\b|\bqsub\b|\bbsub\b", "submits a job"),
        (r"while\s+True|while\s+1\b", "resident loop"),
        (r"\bthreading\b|\bThread\(|\bmultiprocessing\b|\bsched\b|\bapscheduler\b|\bnohup\b|\bsetsid\b|\bcrontab\b",
         "background work"),
        (r"\bsubprocess\b|\bos\.system\b|\bos\.fork\b|\bPopen\b", "starts other programs"),
    ]
    hits = []
    for f in _sources():
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for pat, why in forbidden:
                if re.search(pat, line):
                    hits.append("%s:%d %s: %s" % (f.name, n, why, line.strip()))
    assert hits == []
    ls = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True)
    assert ls.returncode == 0 and ls.stdout.split(), "git ls-files gave nothing (rc=%s): %s" % (ls.returncode, ls.stderr)
    dbs = [p for p in ls.stdout.split() if re.search(r"\.(db|sqlite|sqlite3)$|-wal$|-shm$|-journal$", p)]
    status = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True).stdout.splitlines()[:20]
    assert dbs == [], "database files are committed: %s\ngit status --porcelain (first 20 lines):\n%s" % (dbs, "\n".join(status))
    # a SQLite side file lives only while a connection is open: look again until none is left, for at most 15 seconds
    # (a file that stays is still a failure when the time is up)
    deadline = time.time() + 15
    while True:
        on_disk = [p for p in _all_platform_files() if re.search(r"\.(sqlite|sqlite3)$|-wal$|-shm$|-journal$", p.name)]
        if not on_disk or time.time() >= deadline:
            break
        time.sleep(0.3)
    assert on_disk == [], "database files on disk in platform/: %s" % [p.relative_to(PLATFORM_DIR).as_posix() for p in on_disk]


def test_gitignore_keeps_databases_and_the_venv_out_of_the_repo():
    # plan Revision 2, repo hygiene
    text = (REPO_ROOT / ".gitignore").read_text()
    for entry in ("*.db", "*.db-wal", "*.db-shm", "*.db-journal"):
        assert entry in text.splitlines(), entry
    assert "abf-platform-venv" in text


# ---- TC-072: principle 3, no hard-coded paths ---------------------------------------

def test_tc072_no_personal_or_cluster_paths():
    # TC-072: same expression as tests/no_hardcoded_paths.sh, on platform/ (tests and fixtures too)
    pat = re.compile(r"(/home|/work|/scratch|/staging|/lustre)/[A-Za-z][A-Za-z0-9_.-]*/")
    targets = [p for p in _all_platform_files() if p.suffix != ".pyc"]
    targets += [REPO_ROOT / "docs" / "PLATFORM.md", REPO_ROOT / "tests" / "platform_test.sh"]
    hits = []
    for f in targets:
        if not f.exists():
            hits.append("missing file %s" % f)
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if pat.search(line):
                hits.append("%s:%d" % (f.relative_to(REPO_ROOT), n))
    assert hits == []
    wrapper = (REPO_ROOT / "tests" / "platform_test.sh").read_text()
    assert "${XDG_CACHE_HOME:-$HOME/.cache}" in wrapper


# ---- TC-051 / TC-061: nothing from Seqera's services, nothing outside the machine ---------

SEQERA = ["cloud." + "seqera.io", "api.cloud." + "seqera.io", "tower" + ".nf"]


def test_tc051_no_seqera_service_address_and_no_tw_call():
    # TC-051 (static half; the e2e half asserts the endpoint is local and PATH has no tw)
    targets = [p for p in _all_platform_files() if p.suffix not in (".pyc", ".zip")]
    targets.append(REPO_ROOT / "docs" / "PLATFORM.md")
    targets.append(REPO_ROOT / "tests" / "platform_test.sh")
    hits = []
    for f in targets:
        if not f.exists():
            hits.append("missing file %s" % f)
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for s in SEQERA:
            if s in text:
                hits.append("%s mentions %s" % (f.name, s))
        for n, line in enumerate(text.splitlines(), 1):
            if re.search(r"(^|[\s;&|`(])tw\s+(runs|launch|info|pipelines|compute-envs|datasets)\b", line):
                hits.append("%s:%d calls tw" % (f.name, n))
    assert hits == []


def test_tc061_no_ssh_no_scheduler_no_outgoing_connection_in_the_source():
    # TC-061
    forbidden = [r"\bssh\b", r"\bsbatch\b", r"\bscancel\b", r"\btw\s", r"station", r"\bsite agent\b",
                 r"import requests", r"urllib\.request", r"import httpx", r"smtplib", r"\bimport socket\b",
                 r"\bsocket\.", r"\bparamiko\b"]
    hits = []
    for f in _sources():
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for pat in forbidden:
                if re.search(pat, line):
                    hits.append("%s:%d %s" % (f.name, n, line.strip()))
    assert hits == []
