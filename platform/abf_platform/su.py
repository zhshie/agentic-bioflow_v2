# Nothing existing: Seqera estimates only cloud cost, not NCHC SU (docs/POSITIONING.md row 32); the formula is issue #119's and the factors and money rates live in configs/sites/su_rates.json.
"""SU (the compute point of the national HPC) used by a run, worked out from its tasks when asked.

SU of a task = cpus x realtime hours x the factor of its partition. The factors and the money rates are data
(configs/sites/su_rates.json), never numbers in this file. When anything needed is missing (a factor, cpus, realtime, the site, the
rates file) the answer is None with the reasons, never a guess and never 0. Nothing is stored: a total is added up from the index
at the moment someone asks.
"""
import datetime
import json
import sqlite3
from pathlib import Path

from . import compute_envs, jobs, status, store

def _rates_path():
    """The rates file to read: the copy a wheel carries in this package's data/, else the repository's own file (a checkout)."""
    here = Path(__file__).resolve()
    packed = here.parent / "data" / "su_rates.json"
    if packed.is_file():
        return packed
    up = list(here.parents)
    return (up[2] if len(up) > 2 else here.parent) / "configs" / "sites" / "su_rates.json"


RATES_PATH = _rates_path()
TAIPEI = datetime.timezone(datetime.timedelta(hours=8))   # a month is a calendar month in Asia/Taipei (UTC+8)
MS_PER_HOUR = 3600000.0       # Nextflow's trace holds realtime in milliseconds (platform/tests/fixtures/payloads)
NOT_STORED = ("這個 run 的紀錄沒有保存每個 task 的 cpus、realtime 與分區 "
              "(the run record does not keep each task's cpus, realtime and partition)")
RUN_NOT_ENDED = "run 還沒結束，SU 等它結束後再算 (the run has not ended)"


def load_rates(path=None):
    """The rates table, or None when the file cannot be read as JSON."""
    try:
        with open(path or RATES_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _unknown(reasons):
    return {"su": None, "twd_nstc": None, "twd_academic": None, "unknown_reasons": reasons}


def _factor_of(partitions, part):
    """The factor of a partition: an exact key first, else the longest key ending in '*' whose prefix matches."""
    if not isinstance(part, str):
        return None
    hit = partitions.get(part)
    if not isinstance(hit, dict):
        starred = [k for k in partitions if k.endswith("*") and part.startswith(k[:-1]) and isinstance(partitions[k], dict)]
        hit = partitions[max(starred, key=len)] if starred else None
    return hit.get("factor") if hit else None


def su_of_tasks(tasks, site, rates):
    """{su, twd_nstc, twd_academic, unknown_reasons} for these tasks (dicts with cpus, realtime in ms, queue).
    A site that names twd_per_su also gets twd: {nstc, academic, industry}; its own rates win over the top-level ones."""
    if not isinstance(rates, dict):
        return _unknown(["費率檔讀不到 (the rates file cannot be read)"])
    site_rates = (rates.get("sites") or {}).get(site) or {}
    partitions = site_rates.get("partitions")
    if not isinstance(partitions, dict):
        return _unknown(["找不到站點 %s 的費率 (no rates for site %s)" % (site, site)])
    total, reasons = 0.0, []
    for i, t in enumerate(tasks):
        label = "task %s" % (t.get("name") or t.get("taskId") or i + 1)
        part = t.get("queue")
        factor = _factor_of(partitions, part)
        missing = []
        if not _number(t.get("cpus")):
            missing.append("缺 cpus (no cpus)")
        if not _number(t.get("realtime")):
            missing.append("缺 realtime (no realtime)")
        if not _number(factor):
            missing.append("分區 %s 沒有 SU 係數 (no SU factor for partition %s)" % (part, part))
        if missing:
            reasons.append("%s: %s" % (label, "; ".join(missing)))
        else:
            total += t["cpus"] * (t["realtime"] / MS_PER_HOUR) * factor
    if reasons:
        return _unknown(reasons)
    per_su = site_rates.get("twd_per_su")
    if isinstance(per_su, dict):
        nstc, academic = per_su.get("nstc"), per_su.get("academic")
    else:
        nstc, academic = rates.get("nstc_twd_per_su"), rates.get("academic_twd_per_su")
    out = {"su": total,
           "twd_nstc": total * nstc if _number(nstc) else None,
           "twd_academic": total * academic if _number(academic) else None,
           "unknown_reasons": []}
    if isinstance(per_su, dict):
        industry = per_su.get("industry")
        out["twd"] = {"nstc": out["twd_nstc"], "academic": out["twd_academic"],
                      "industry": total * industry if _number(industry) else None}
    return out


def run_tasks(index_path, run_name):
    """The per-task facts (cpus, realtime, queue) of a run, or None when the record does not keep them.
    From the task_usage table the receiver fills; a run (or an index made before the table) with no rows gives None. Each item also
    carries status (COMPLETED or FAILED) so a caller can count the finished ones. Read-only: it never creates the table."""
    view = status.find_run(index_path, run_name)
    if view is None:
        return None
    con = status._open_readonly(index_path)
    if con is None:
        return None
    try:
        rows = con.execute("SELECT name, status, cpus, realtime_ms, queue FROM task_usage WHERE run_id = ? ORDER BY task_key",
                           (view["id"],)).fetchall()
    except sqlite3.OperationalError:
        return None      # an index made before the table existed
    finally:
        con.close()
    if not rows:
        return None
    return [{"name": r["name"], "status": r["status"], "cpus": r["cpus"], "realtime": r["realtime_ms"], "queue": r["queue"]}
            for r in rows]


def site_of_run(platform_path, run_name, rates):
    """The rates site of a run: the suSite of the compute environment of its newest launch; else the rates file's default_site
    (also when there is no launch, the environment is gone, it names no suSite, or platform.db cannot be read)."""
    default = rates.get("default_site") if isinstance(rates, dict) else None
    try:
        con = store.open_readonly(platform_path)
        if con is None:
            return default
        try:
            row = jobs.latest_launch(con, run_name)
            ce_name = row["ce"] if row is not None else None
        finally:
            con.close()
        ce = compute_envs.get(platform_path, ce_name) if ce_name else None
    except (sqlite3.Error, OSError):
        return default
    site = ce["config"].get("suSite") if ce else None
    return site if isinstance(site, str) and site else default


def run_su(index_path, run_name, site, rates, tasks_of=None):
    tasks = (tasks_of or run_tasks)(index_path, run_name)
    if tasks is None:
        return _unknown([NOT_STORED])
    return su_of_tasks(tasks, site, rates)


def _taipei_month(iso_utc):
    """'YYYY-MM' in Taipei time of an ISO 8601 UTC stamp (status.list_runs gives 'YYYY-MM-DDTHH:MM:SSZ'), or None."""
    try:
        t = datetime.datetime.strptime(iso_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return None
    return t.astimezone(TAIPEI).strftime("%Y-%m")


def month_total(index_path, platform_path, user_id, month, site, rates, tasks_of=None):
    """Total SU of the runs this user launched that started in `month` ('YYYY-MM', Taipei time, by start), added up now from the index.
    None when any of those runs has an unknown SU (a partial sum would pass for the whole)."""
    names = jobs.owned_run_names(platform_path, user_id)
    total = 0.0
    for r in status.list_runs(index_path, status.now(), names=names):
        started = r.get("started_at")
        if not started or _taipei_month(started) != month:
            continue
        su = run_su(index_path, r["name"], site, rates, tasks_of)["su"]
        if su is None:
            return None
        total += su
    return total
