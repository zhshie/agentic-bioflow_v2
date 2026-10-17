# Nothing existing: the rule that turns a stored row and the clock into running, succeeded, failed or lost; no monitoring tool is wanted here, the answer is worked out when asked.
"""What a run is, at the moment someone asks.

No background program watches the runs. A run is `lost` when its last message is older than
three heartbeats and no complete arrived; that is decided here, at query time, from the row
and the clock handed in (a fake one in the tests). Reading never writes: the database is
opened read-only and is not created if it is missing.
"""
import os
import sqlite3
import time
from pathlib import Path

from . import common

COUNT_FIELDS = ("succeeded", "cached", "failed", "aborted", "running", "pending", "submitted")


def now():
    """Wall clock, plus ABF_PLATFORM_CLOCK_OFFSET seconds (a testing aid, see docs/PLATFORM.md)."""
    return time.time() + float(os.environ.get("ABF_PLATFORM_CLOCK_OFFSET") or 0)


def derive_status(final_status, source, last_message_at, at):
    if final_status:
        return final_status
    if source == "rebuild":
        # Nextflow's records hold no completion for this run, and nobody is sending messages for it.
        return "lost"
    return "lost" if at - last_message_at > common.LOST_AFTER_SECONDS else "running"


def _open_readonly(path):
    path = Path(path)
    if not path.exists():
        return None
    con = sqlite3.connect("%s?mode=ro" % path.resolve().as_uri(), uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def _counts(row, prefix="n_"):
    c = {f: row[prefix + f] for f in COUNT_FIELDS}
    c["total"] = sum(c.values())
    return c


def _view(con, row, at, detail):
    st = derive_status(row["final_status"], row["source"], row["last_message_at"], at)
    tasks = _counts(row)
    view = {
        "id": row["id"],
        "name": row["run_name"],
        "session_id": row["session_id"],
        "status": st,
        "started_at": common.epoch_iso(row["started_at"]),
        "ended_at": common.epoch_iso(row["ended_at"]),
        "tasks": tasks,
    }
    if detail and st == "failed" and "failure_reason" in row.keys() and row["failure_reason"]:
        view["failure_reason"] = row["failure_reason"]   # Nextflow's own words; an index made before follow-up 3 has no column
    if st in ("running", "lost"):
        view["last_message_at"] = common.epoch_iso(row["last_message_at"])
    if detail:
        procs = con.execute("SELECT * FROM processes WHERE run_id = ? ORDER BY name", (row["id"],)).fetchall()
        view["processes"] = [dict(name=p["name"], **_counts(p)) for p in procs]
        failed = con.execute("SELECT name, exit_code, error_message FROM failed_tasks WHERE run_id = ? "
                             "ORDER BY name, exit_code, task_key", (row["id"],)).fetchall()
        view["failed_tasks"] = [{"name": f["name"], "exit_code": f["exit_code"], "error_message": f["error_message"]}
                                for f in failed]
    return view


def list_runs(index_path, at=None, names=None):
    """Every run, newest first; with `names` (a set of run names) only the runs of those names."""
    at = now() if at is None else at
    con = _open_readonly(index_path)
    if con is None:
        return []
    try:
        rows = con.execute("SELECT * FROM runs ORDER BY started_at DESC, rowid DESC").fetchall()
        return [_view(con, r, at, detail=False) for r in rows if names is None or r["run_name"] in names]
    finally:
        con.close()


def get_run(index_path, run_id, at=None):
    at = now() if at is None else at
    con = _open_readonly(index_path)
    if con is None:
        return None
    try:
        row = con.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return _view(con, row, at, detail=True) if row else None
    finally:
        con.close()
