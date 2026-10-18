# Nothing existing: Seqera estimates only cloud cost, not NCHC SU (docs/POSITIONING.md row 32); the formula is issue #119's and the factors and money rates live in configs/sites/su_rates.json.
"""SU (the compute point of the national HPC) used by a run, worked out from its tasks when asked.

SU of a task = cpus x realtime hours x the factor of its partition. The factors and the money rates are data
(configs/sites/su_rates.json), never numbers in this file. When anything needed is missing (a factor, cpus, realtime, the site, the
rates file) the answer is None with the reasons, never a guess and never 0. Nothing is stored: a total is added up from the index
at the moment someone asks.
"""
import json
from pathlib import Path

from . import jobs, status

RATES_PATH = Path(__file__).resolve().parents[2] / "configs" / "sites" / "su_rates.json"
MS_PER_HOUR = 3600000.0       # Nextflow's trace holds realtime in milliseconds (platform/tests/fixtures/payloads)
NOT_STORED = ("這個 run 的紀錄沒有保存每個 task 的 cpus、realtime 與分區 "
              "(the run record does not keep each task's cpus, realtime and partition)")


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


def su_of_tasks(tasks, site, rates):
    """{su, twd_nstc, twd_academic, unknown_reasons} for these tasks (dicts with cpus, realtime in ms, queue)."""
    if not isinstance(rates, dict):
        return _unknown(["費率檔讀不到 (the rates file cannot be read)"])
    partitions = ((rates.get("sites") or {}).get(site) or {}).get("partitions")
    if not isinstance(partitions, dict):
        return _unknown(["找不到站點 %s 的費率 (no rates for site %s)" % (site, site)])
    total, reasons = 0.0, []
    for i, t in enumerate(tasks):
        label = "task %s" % (t.get("name") or t.get("taskId") or i + 1)
        part = t.get("queue")
        factor = (partitions.get(part) or {}).get("factor") if isinstance(partitions.get(part), dict) else None
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
    nstc, academic = rates.get("nstc_twd_per_su"), rates.get("academic_twd_per_su")
    return {"su": total,
            "twd_nstc": total * nstc if _number(nstc) else None,
            "twd_academic": total * academic if _number(academic) else None,
            "unknown_reasons": []}


def run_tasks(index_path, run_name):
    """The per-task facts (cpus, realtime, queue) of a run, or None when the record does not keep them.
    The receiver stores only counts and failed tasks (store.py), so for now this is always None; it is the one place to change
    when the receiver starts keeping the trace."""
    return None


def run_su(index_path, run_name, site, rates, tasks_of=None):
    tasks = (tasks_of or run_tasks)(index_path, run_name)
    if tasks is None:
        return _unknown([NOT_STORED])
    return su_of_tasks(tasks, site, rates)


def month_total(index_path, platform_path, user_id, month, site, rates, tasks_of=None):
    """Total SU of the runs this user launched that started in `month` ('YYYY-MM', UTC), added up now from the index.
    None when any of those runs has an unknown SU (a partial sum would pass for the whole)."""
    names = jobs.owned_run_names(platform_path, user_id)
    total = 0.0
    for r in status.list_runs(index_path, status.now(), names=names):
        started = r.get("started_at")
        if not started or started[:7] != month:
            continue
        su = run_su(index_path, r["name"], site, rates, tasks_of)["su"]
        if su is None:
            return None
        total += su
    return total
