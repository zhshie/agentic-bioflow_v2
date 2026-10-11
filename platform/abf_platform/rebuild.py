# Nothing existing: Nextflow ships no reader that turns .nextflow/history, .nextflow.log and a trace file into a run record; this one does only that.
"""Build the run index again from Nextflow's own records.

Per launch folder it reads
  .nextflow/history      run name, session id, start second, OK / ERR / - (never finished)
  .nextflow.log[.N]      the log of each run: trace file name, end time, the failed task's error text
  the -with-trace file   one row per task attempt

Where the old index and these records disagree, the records win, because the old index is
dropped. The token file is never opened.
"""
import os
import re
import time
from pathlib import Path

from . import common, store

_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
_LOG_TS = re.compile(r"^([A-Z][a-z]{2})-(\d\d) (\d\d):(\d\d):(\d\d)\.\d{3} ")
_STATUS = {"COMPLETED": "succeeded", "CACHED": "cached", "FAILED": "failed", "ABORTED": "aborted"}


class Result:
    def __init__(self):
        self.runs = 0
        self.folders = 0
        self.skipped = []  # (folder, reason)
        self.notes = []


def _log_epoch(line, start):
    """Epoch seconds of a log line (local time; the line has no year, so the run's start gives it)."""
    m = _LOG_TS.match(line or "")
    if not m or m.group(1) not in _MONTHS:
        return None
    year = time.localtime(start).tm_year
    fields = (_MONTHS[m.group(1)], int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), 0, 0, -1)
    t = int(time.mktime((year,) + fields))
    if t < start - 86400:  # the log crossed New Year
        t = int(time.mktime((year + 1,) + fields))
    return t


def _parse_log(path):
    """What one .nextflow.log says about its run. Times stay as text lines until the start is known."""
    info = {"session": None, "run_name": None, "trace": None, "last_line": None, "barrier_line": None, "errors": {}}
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    for ln in lines:
        if info["session"] is None and "Session UUID: " in ln:
            info["session"] = ln.split("Session UUID: ", 1)[1].strip()
        elif info["run_name"] is None and "Run name: " in ln and "nextflow.Session" in ln:
            info["run_name"] = ln.split("Run name: ", 1)[1].strip()
        elif info["trace"] is None and "Workflow started -- trace file: " in ln:
            info["trace"] = ln.split("trace file: ", 1)[1].strip()
        elif info["barrier_line"] is None and "Session await > all barriers passed" in ln:
            info["barrier_line"] = ln
        if _LOG_TS.match(ln):
            info["last_line"] = ln
    text = "\n".join(lines)
    starts = [m.start() for m in re.finditer(r"Error executing process > '", text)]
    for i, s in enumerate(starts):
        found = common.extract_error(text[s:starts[i + 1] if i + 1 < len(starts) else len(text)])
        if found and found[0] not in info["errors"]:
            info["errors"][found[0]] = found[1]
    return info


def _read_trace(path):
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return []
    head = lines[0].split("\t")
    return [dict(zip(head, ln.split("\t"))) for ln in lines[1:] if ln.strip()]


def _empty_counts():
    return {"succeeded": 0, "cached": 0, "failed": 0, "aborted": 0, "running": 0, "pending": 0, "submitted": 0}


def _folder_problem(folder):
    if not folder.exists():
        return "folder does not exist"
    if not folder.is_dir():
        return "not a folder"
    if not os.access(folder, os.R_OK | os.X_OK):
        return "no permission to read it"
    hist = folder / ".nextflow" / "history"
    if not hist.is_file():
        return "no .nextflow/history found (not a Nextflow launch folder)"
    if not os.access(hist, os.R_OK):
        return "no permission to read .nextflow/history"
    return None


def _runs_of_folder(folder, notes):
    logs = {}
    for p in sorted(folder.glob(".nextflow.log*")):
        if p.name == ".nextflow.log" or re.fullmatch(r"\.nextflow\.log\.\d+", p.name):
            logs[p] = p
    parsed = {}
    runs = []
    for line in (folder / ".nextflow" / "history").read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        ts, _duration, name, st, _script, session = parts[:6]
        try:
            start = int(time.mktime(time.strptime(ts, "%Y-%m-%d %H:%M:%S")))
        except ValueError:
            notes.append("%s: unreadable history line skipped" % folder)
            continue
        log = None
        for p in logs:
            if p not in parsed:
                try:
                    parsed[p] = _parse_log(p)
                except OSError:
                    parsed[p] = None
            cand = parsed[p]
            if cand and cand["session"] == session and cand["run_name"] == name:
                log = cand
                break
        runs.append(_build_run(folder, session, name, st, start, log, notes))
    return runs


def _build_run(folder, session, name, hist_status, start, log, notes):
    final = {"OK": "succeeded", "ERR": "failed"}.get(hist_status)
    rows = []
    if log and log["trace"]:
        trace = folder / log["trace"]
        if trace.is_file():
            rows = _read_trace(trace)
        else:
            notes.append("%s: trace file %s of run %s is gone, task numbers are unknown" % (folder, log["trace"], name))
    elif log is None:
        notes.append("%s: no log found for run %s, task numbers are unknown" % (folder, name))
    totals = _empty_counts()
    procs = {}
    failed_by_name = {}
    for r in rows:
        key = _STATUS.get(r.get("status"))
        proc = (r.get("name") or "").split(" ", 1)[0]
        pc = procs.setdefault(proc, _empty_counts())
        if key:
            totals[key] += 1
            pc[key] += 1
        if r.get("status") == "FAILED":
            try:
                code = int(r.get("exit"))
            except (TypeError, ValueError):
                code = None
            failed_by_name[r.get("name")] = ("%s:1" % r.get("task_id"), r.get("name"), code,
                                             (log or {}).get("errors", {}).get(r.get("name")))
        else:
            # the same task ran again and did not fail: the earlier failure is not a failure of the run (as live)
            failed_by_name.pop(r.get("name"), None)
    ended = None
    log = log or {}
    last = _log_epoch(log.get("last_line"), start)
    if final:
        # Nextflow writes this line a few milliseconds before it stamps the end time it sends.
        ended = _log_epoch(log.get("barrier_line"), start) or last or start
        last_message = ended
    else:
        last_message = last or start
    return {
        "id": common.run_id(session, name), "session": session, "name": name, "final": final, "start": start,
        "ended": ended, "last_message": last_message, "totals": totals, "procs": procs, "failed": list(failed_by_name.values()),
    }


def rebuild(folders, index_path, out=print):
    """Drop the index and build it again from the launch folders. Returns a Result."""
    result = Result()
    runs = []
    for f in folders:
        folder = Path(f)
        problem = _folder_problem(folder)
        if problem:
            result.skipped.append((str(f), problem))
            out("skipped %s: %s" % (f, problem))
            continue
        try:
            found = _runs_of_folder(folder, result.notes)
        except OSError as e:
            result.skipped.append((str(f), "cannot read the records: %s" % e))
            out("skipped %s: cannot read the records: %s" % (f, e))
            continue
        result.folders += 1
        runs.extend(found)
    for n in result.notes:
        out("note: " + n)
    if result.folders == 0:
        out("no launch folder could be read; the index was left as it is")
        return result
    store.drop_index_files(index_path)
    con = store.connect_index(index_path)
    try:
        with con:
            for r in runs:
                t = r["totals"]
                con.execute(
                    "INSERT OR REPLACE INTO runs (id, session_id, run_name, token_id, source, final_status, started_at, "
                    "ended_at, last_message_at, n_succeeded, n_cached, n_failed, n_aborted, n_running, n_pending, n_submitted) "
                    "VALUES (?, ?, ?, NULL, 'rebuild', ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0)",
                    (r["id"], r["session"], r["name"], r["final"], r["start"], r["ended"], r["last_message"],
                     t["succeeded"], t["cached"], t["failed"], t["aborted"]))
                con.execute("DELETE FROM processes WHERE run_id = ?", (r["id"],))
                con.execute("DELETE FROM failed_tasks WHERE run_id = ?", (r["id"],))
                for pname, c in r["procs"].items():
                    con.execute("INSERT INTO processes (run_id, name, n_succeeded, n_cached, n_failed, n_aborted) "
                                "VALUES (?, ?, ?, ?, ?, ?)", (r["id"], pname, c["succeeded"], c["cached"], c["failed"], c["aborted"]))
                for key, tname, code, msg in r["failed"]:
                    con.execute("INSERT OR REPLACE INTO failed_tasks (run_id, task_key, name, exit_code, error_message) "
                                "VALUES (?, ?, ?, ?, ?)", (r["id"], key, tname, code, msg))
    finally:
        con.close()
    result.runs = len(runs)
    return result
