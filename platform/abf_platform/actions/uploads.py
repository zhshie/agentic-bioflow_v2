# Nothing existing: the batch of a web upload (files already on the platform host -> one put_upload job each -> a Dataset once every file is in the bucket) is this platform's own rule (ADR 0010, 10-25 correction); no library knows it, and every step calls a function that already holds its rule.
"""Web uploads (web-upload-page): start one batch of uploads, and read where it stands.

The web page (web_upload.py, uploads_web.py) has only received the bytes into a folder of the platform host and hands over what it got.
Here the files are judged (names, sizes, the samplesheet, the environment, the dataset name), moved to their place in the person's own upload
folder, and queued one by one with jobs.enqueue_put_upload; the agent on the platform host writes each into the person's own prefix of the
bucket and deletes the staged copy once the size in the bucket is the size here. Nothing in this module opens a connection or starts a program.

A batch is a small file `<uploads>/<user>/.batches/<batch>.json` (0600, written whole and renamed into place): the name and version asked for,
the files with their job numbers and places, the samplesheet in the words of the file names, and whether the Dataset is kept. It is not a run
and not a second copy of any job's state: the state of a file is read from the job each time. Only the owner reads it. When every file is
in the bucket the first read by the owner registers the Dataset (register_dataset, with the places the agent reported); a second read
finds the flag and registers nothing.
"""
import csv
import io
import json
import os
import re
import tempfile
import time
from pathlib import Path

from .. import cloud_store, compute_envs, jobs, store
from . import datasets

BATCH = re.compile(r"^[0-9a-f]{32}\Z")
NAME = re.compile(r"^[A-Za-z0-9._-]{1,64}\Z")
FILE_NAME_CHARS = 255


def _fail(error, **more):
    out = {"ok": False, "error": error}
    out.update(more)
    return out


def _bad_name(name):
    return (not isinstance(name, str) or not name or len(name) > FILE_NAME_CHARS or name.startswith(".") or ".." in name
            or "/" in name or "\\" in name or any(ord(c) < 32 or ord(c) == 127 for c in name))


def _area(platform_path, caller):
    from . import caller_area
    return caller_area(platform_path, caller)


def _usable_env(ce):
    """True for an environment the person may send files to: set up, and of a type whose jobs include the upload."""
    return (isinstance(ce, dict) and ce.get("status") == compute_envs.AVAILABLE
            and "put_upload" in compute_envs.CLOUD_JOB_KINDS.get(ce.get("platform"), ()))


# ---- the batch file --------------------------------------------------------------------------------------------------------

def _batches_dir(area):
    return os.path.join(area, ".batches")


def _load(area, batch):
    if not isinstance(batch, str) or not BATCH.match(batch):
        return None
    try:
        with open(os.path.join(_batches_dir(area), batch + ".json"), encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, ValueError):
        return None
    return rec if isinstance(rec, dict) and rec.get("batch") == batch else None


def _save(area, rec):
    folder = _batches_dir(area)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)
        os.chmod(tmp, 0o600)
        os.replace(tmp, os.path.join(folder, rec["batch"] + ".json"))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _all(area):
    try:
        names = sorted(os.listdir(_batches_dir(area)))
    except OSError:
        return []
    out = []
    for n in names:
        if n.endswith(".json") and not n.startswith("."):
            rec = _load(area, n[:-5])
            if rec is not None:
                out.append(rec)
    return out


# ---- how a file stands -----------------------------------------------------------------------------------------------------

def _states(platform_path, rec, now):
    """One dict per file of the batch: name, size, state (queued, sending, done, failed), message (what the agent or the queue said, or None),
    expired (the job ran out of time), url (where it is in the bucket, for a file that is done)."""
    ids = [f["job_id"] for f in rec["files"] if f.get("job_id") is not None]
    found = jobs.upload_jobs(platform_path, ids, now) if ids else {}
    out = []
    for f in rec["files"]:
        item = {"name": f["name"], "size": f.get("size"), "state": "failed", "message": None, "expired": False, "url": None}
        if f.get("error"):
            item["message"] = f["error"]
        else:
            job = found.get(f.get("job_id")) or {"state": "gone", "result": None}
            result = job["result"] or {}
            if job["state"] == "queued":
                item["state"] = "queued"
            elif job["state"] == "claimed":
                item["state"] = "sending"
            elif job["state"] == "done" and result.get("ok"):
                item["state"] = "done"
                path = result.get("path")
                item["url"] = path if isinstance(path, str) and path else f.get("dest")
                if isinstance(result.get("bytes"), int):
                    item["bytes"] = result["bytes"]
            else:
                item["expired"] = job["state"] in ("expired", "gone")
                item["message"] = result.get("message") if isinstance(result.get("message"), str) else None
        out.append(item)
    return out


def _failed(items):
    return any(i["state"] == "failed" for i in items)


# ---- start -----------------------------------------------------------------------------------------------------------------

def _tidy(folder):
    """Remove the staging folder and what is in it (files only; best effort)."""
    try:
        for entry in os.scandir(folder):
            try:
                os.unlink(entry.path)
            except OSError:
                pass
        os.rmdir(folder)
    except OSError:
        pass


def start_upload_batch(platform_path, tokens_path, caller, *, batch, ce_name, name, version, files, samplesheet, incoming, clock=time.time):
    """Judge what the web page received and, when all is well, queue one upload per file. `files` is [{name, tmp, size}] (the staged copies are
    in the folder `incoming`, which is removed whatever the answer), `samplesheet` the bytes of the file the person chose or None. Returns
    {ok: True, batch} or {ok: False, error, ...}; before any job is queued an error leaves nothing behind (the staged copies are removed)."""
    try:
        return _start(platform_path, tokens_path, caller, batch, ce_name, name, version, files, samplesheet, incoming, clock)
    finally:
        _tidy(incoming)


def _start(platform_path, tokens_path, caller, batch, ce_name, name, version, files, samplesheet, incoming, clock):
    if caller is None or not isinstance(batch, str) or not BATCH.match(batch):
        return _fail("request")
    try:
        area = _area(platform_path, caller)
    except Exception:
        return _fail("request")
    if os.path.realpath(str(incoming)) != os.path.join(area, ".incoming-" + batch):
        return _fail("request")
    name = name.strip() if isinstance(name, str) else ""
    version = version.strip() if isinstance(version, str) else ""
    fields = {}
    for key, value in (("name", name), ("version", version)):
        if not value:
            fields[key] = "required"
        elif not NAME.match(value) or compute_envs.looks_like_credential(value):
            fields[key] = "invalid"
    if fields:
        return _fail("fields", fields=fields)
    if not files:
        return _fail("no_files")
    ce = compute_envs.get(platform_path, ce_name, owner=caller.user_id) if isinstance(ce_name, str) else None
    if not _usable_env(ce):
        return _fail("env")
    if datasets.get_dataset(platform_path, name, version, caller=caller)["found"]:
        return _fail("already_registered")
    names = [f["name"] for f in files]
    bad = [n for n in names if _bad_name(n)]
    if bad:
        return _fail("bad_name", names=bad)
    seen, twice = set(), []
    for n in names:
        if n in seen and n not in twice:
            twice.append(n)
        seen.add(n)
    if twice:
        return _fail("dup_in_batch", names=twice)
    empty = [f["name"] for f in files if not f["size"] or f["size"] < 1]
    if empty:
        return _fail("empty_file", names=empty)
    large = [f["name"] for f in files if f["size"] > cloud_store.UPLOAD_LIMIT]
    if large:
        return _fail("too_big", names=large)
    now = clock()
    replaced = []
    taken = []
    for n in names:
        if os.path.lexists(os.path.join(area, n)):
            old = _reusable(platform_path, area, n, now)
            if old is None:
                taken.append(n)
            elif all(old["batch"] != r["batch"] for r in replaced):
                replaced.append(old)
    if taken:
        return _fail("in_use", names=taken)
    if samplesheet is not None:
        try:
            sheet = samplesheet.decode("utf-8-sig")
        except UnicodeDecodeError:
            return _fail("sheet", message="樣本表不是 UTF-8 文字 (the samplesheet is not UTF-8 text)")
        checked = datasets.check_samplesheet(sheet, set(names))
        if not checked["ok"]:
            return _fail("sheet", message=checked["message"])
    else:
        paired = datasets.pair_fastq(names)
        if paired["unpaired"]:
            return _fail("unpaired", unpaired=paired["unpaired"])
        sheet = paired["csv"]
    try:
        jobs.check_target(platform_path, ce_name, "put_upload", clock=clock, caller_user_id=caller.user_id)
        scheme = cloud_store.workdir_scheme(ce)
        dests = {n: cloud_store.object_url(ce, caller.name, n, scheme) for n in names}
    except (jobs.JobRefused, cloud_store.CloudPathError) as e:
        return _fail("refused", message=str(e))
    moved = []
    try:
        for f in files:
            final = os.path.join(area, f["name"])
            if os.path.lexists(final):
                os.unlink(final)
            os.replace(str(f["tmp"]), final)
            moved.append(final)
    except OSError:
        for p in moved:
            try:
                os.unlink(p)
            except OSError:
                pass
        return _fail("disk")
    uploads_dir = store.uploads_root(platform_path)
    entries, refused = [], None
    for f in files:
        entry = {"name": f["name"], "size": f["size"], "dest": dests[f["name"]], "job_id": None}
        if refused is None:
            try:
                entry["job_id"] = jobs.enqueue_put_upload(platform_path, tokens_path, ce_name, caller.name, f["name"], uploads_dir, caller.user_id,
                                                          clock=clock)
            except jobs.JobRefused as e:
                refused = str(e)
        if entry["job_id"] is None:
            entry["error"] = refused
            try:
                os.unlink(os.path.join(area, f["name"]))
            except OSError:
                pass
        entries.append(entry)
    if all(e["job_id"] is None for e in entries):
        return _fail("refused", message=refused)
    rec = {"batch": batch, "owner": caller.name, "ce": ce_name, "name": name, "version": version, "files": entries, "samplesheet": sheet,
           "registered": False, "superseded": False, "created_at": now}
    _save(area, rec)
    for old in replaced:
        old["superseded"] = True
        _save(area, old)
    return {"ok": True, "batch": batch}


def _reusable(platform_path, area, filename, now):
    """The batch record that holds a file name already in the person's upload folder, when that batch has failed and its job for this very file is
    over: the new upload may take the name over (the record is then marked superseded). None when the name is in use: it belongs to a batch that is
    still running or was registered, or to no batch at all."""
    owner = None
    for rec in _all(area):
        if rec.get("superseded"):
            continue
        if any(f["name"] == filename for f in rec["files"]):
            owner = rec
    if owner is None or owner.get("registered"):
        return None
    items = _states(platform_path, owner, now)
    if not _failed(items):
        return None
    mine = next(i for i in items if i["name"] == filename)
    if mine["state"] in ("queued", "sending"):
        return None
    return owner


# ---- read, and register once every file is in ------------------------------------------------------------------------------

def _with_places(sheet, places):
    rows = list(csv.reader(io.StringIO(sheet)))
    if not rows:
        return sheet
    header = [h.strip() for h in rows[0]]
    columns = [header.index(c) for c in ("fastq_1", "fastq_2") if c in header]
    for row in rows[1:]:
        for i in columns:
            if i < len(row) and row[i].strip() in places:
                row[i] = places[row[i].strip()]
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue()


def _register(platform_path, caller, rec, items, text):
    places = {i["name"]: i["url"] for i in items}
    sizes = {i["name"]: i.get("bytes", i.get("size")) for i in items}
    return datasets.register_dataset(
        platform_path, name=rec["name"], version=rec["version"], samplesheet=text,
        files=[{"path": places[n], "size_bytes": sizes[n]} if isinstance(sizes[n], int) and sizes[n] >= 0 else {"path": places[n]} for n in places],
        caller=caller, destination=rec["ce"])


def _keep_sheet(area, rec, text):
    """The registered samplesheet as a file `<upload folder>/datasets/<name>/<version>.csv`: the launch page chooses its samplesheet among the
    files of the person's upload folder, so this is what makes the new dataset a choice at step 4. Best effort: the dataset is kept either way."""
    folder = os.path.join(area, "datasets", rec["name"])
    try:
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=folder)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, os.path.join(folder, rec["version"] + ".csv"))
    except OSError:
        pass


def upload_batch_status(platform_path, caller, batch, *, clock=time.time):
    """Where one batch of the caller stands, or {ok: False, found: False} (a batch of somebody else answers like one that does not exist).
    Reading it registers the Dataset when every file is in the bucket and nothing registered it yet (the person has no button to press).
    status: running, failed, registered, or register_failed (every file is in, the Dataset was refused: `message`, and `places`)."""
    if caller is None:
        return {"ok": False, "found": False}
    try:
        area = _area(platform_path, caller)
    except Exception:
        return {"ok": False, "found": False}
    rec = _load(area, batch)
    if rec is None or rec.get("owner") != caller.name:
        return {"ok": False, "found": False}
    now = clock()
    items = _states(platform_path, rec, now)
    out = {"ok": True, "found": True, "batch": batch, "name": rec["name"], "version": rec["version"], "ce": rec["ce"], "files": items,
           "superseded": bool(rec.get("superseded"))}
    if rec.get("registered"):
        return dict(out, status="registered")
    if _failed(items):
        return dict(out, status="failed")
    if not all(i["state"] == "done" for i in items):
        return dict(out, status="running")
    text = _with_places(rec["samplesheet"], {i["name"]: i["url"] for i in items})
    answer = _register(platform_path, caller, rec, items, text)
    places = [i["url"] for i in items]
    if not answer.get("ok"):
        # a read of the same page at the same moment may have kept this very dataset a moment ago: then the flag is the truth, and so is a dataset
        # of this name and version that holds exactly these places and this sheet (nothing else is taken for ours)
        rec = _load(area, batch) or rec
        kept = datasets.get_dataset(platform_path, rec["name"], rec["version"], caller=caller)
        ours = kept.get("found") and kept["samplesheet"] == text and [f["path"] for f in kept["files"]] == places
        if not (rec.get("registered") or ours):
            return dict(out, status="register_failed", message=answer.get("message"), places=places)
    if not rec.get("registered"):
        rec["registered"] = True
        _save(area, rec)
        _keep_sheet(area, rec, text)
    return dict(out, status="registered")
