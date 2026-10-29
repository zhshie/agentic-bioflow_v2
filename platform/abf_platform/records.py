# Nothing existing: Nextflow's logs of a run have no home on the machine that runs the platform; this keeps the few files the agent reads back, and refuses every other name.
"""Nextflow's own records of a launch, as the agent read them back from the site (feature 007b, FR-011).

They are kept under `<platform data>/records/<run name>/` in the same shape as a launch folder (`.nextflow.log*`,
`.nextflow/history` and the trace file), so `abf-platform rebuild` reads each of them as one more launch folder.
Only the names Nextflow writes for these records are accepted. The files carry paths and parameters of the run
(see docs/PLATFORM.md): that is why only the fetch command, which the user types, brings them here.
"""
import base64
import binascii
import os
import re
from pathlib import Path

MAX_BYTES = 20 * 1024 * 1024
MAX_FILES = 40
_RUN_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,63}\Z")
_LOG = re.compile(r"^\.nextflow\.log(\.[0-9]{1,3})?\Z")
_TRACE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}\Z")
_NOT_RECORDS = {"tower.token", "params.yaml", "head.sh", "nextflow.config", "samplesheet.csv", "gcb.config", "aws.config", "az" "ure.config"}


def name_ok(name):
    """True for the names of Nextflow's records: its log files, its history, and a trace file named like a plain file."""
    if not isinstance(name, str):
        return False
    if _LOG.match(name) or name == ".nextflow/history":
        return True
    return bool(_TRACE.match(name)) and name not in _NOT_RECORDS and not name.startswith(("slurm-", ".nextflow"))


def store_files(records_dir, run_name, files):
    """Write the accepted files; returns {'files': [{'name', 'size', 'truncated'}], 'refused': [why, ...]}. Nothing is deleted."""
    out = {"files": [], "refused": []}
    if not isinstance(run_name, str) or not _RUN_NAME.match(run_name):
        out["refused"].append("the run name is not one this platform makes")
        return out
    if not isinstance(files, list):
        return out
    folder = Path(records_dir) / run_name
    for item in files[:MAX_FILES]:
        name = item.get("name") if isinstance(item, dict) else None
        if not name_ok(name):
            out["refused"].append("not a record of Nextflow: %r" % str(name)[:60])
            continue
        data = item.get("data")
        try:
            raw = base64.b64decode(data, validate=True) if isinstance(data, str) else None
        except (binascii.Error, ValueError):
            raw = None
        if raw is None:
            out["refused"].append("%s: unreadable content" % name)
            continue
        if len(raw) > MAX_BYTES:
            out["refused"].append("%s: larger than %d bytes" % (name, MAX_BYTES))
            continue
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(folder, 0o700)
        tmp = target.with_name(target.name + ".part")
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        os.replace(str(tmp), str(target))
        out["files"].append({"name": name, "size": len(raw), "truncated": bool(item.get("truncated"))})
    if len(files) > MAX_FILES:
        out["refused"].append("more than %d files" % MAX_FILES)
    return out


def roots(records_dir):
    """The folders under records/ that rebuild reads as launch folders."""
    base = Path(records_dir)
    return sorted(str(p) for p in base.iterdir() if p.is_dir()) if base.is_dir() else []
