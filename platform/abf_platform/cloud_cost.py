# Nothing existing: Seqera Platform only bills, Nextflow's google-batch trace gives machineType and priceModel but no price, and a Google billing budget alerts after the spend; none checks a launch before it is sent, so this is ours.
"""What a run on Google Batch costs in US dollars, what a person has used this month, and the check against the monthly cap.

Sister of su.py: load the rates, price one task, add up a run, add up a month. The rates are data (data/cloud_rates.json), one entry per
region and machine type, each with the page it was read from and the day it was read; an entry without them is treated as absent. Money
is in the cloud's own currency (US dollars) and is never converted. Only the virtual machines are priced (no disk, network or storage),
by the task's own realtime, so the figures are "about" and a little under the bill. When anything needed is missing the answer is None with
the reasons: never a guess, never 0. This module only reads; nothing is stored and nothing is started or stopped.
"""
import datetime
import json
import math
import re
import sqlite3
from pathlib import Path

from . import compute_envs, jobs, status, store, su

CLOUD = "googlebatch-platform"
CURRENCY = "USD"
RATES_PATH = Path(__file__).resolve().parent / "data" / "cloud_rates.json"
MS_PER_HOUR = 3600000.0
NOT_STORED = ("這個 run 的紀錄沒有保存機器型號 (the run record does not keep the machine type)")
NO_HISTORY = ("這個 pipeline 你還沒有成功跑過的雲端紀錄，無法預估 (no earlier cloud run of this pipeline to estimate from)")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}\Z")
_ZONE_LETTER = re.compile(r"-[a-z]\Z")
_MODELS = ("standard", "spot")


def load_rates(path=None):
    """The rates table, or None when the file cannot be read as a JSON object."""
    try:
        with open(path or RATES_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _shown(v):
    return repr(str(v)[:60])


def _unknown(reasons, **extra):
    return dict({"usd": None, "currency": CURRENCY, "unknown_reasons": reasons, "as_of": None}, **extra)


def _entry(rates, region, machine):
    """The rate entry of a machine type in a region, or None when there is none or it lacks its source (https://) or its read date."""
    regions = rates.get("regions") if isinstance(rates, dict) else None
    machines = regions.get(region) if isinstance(regions, dict) else None
    e = machines.get(machine) if isinstance(machines, dict) else None
    if not isinstance(e, dict):
        return None
    source, read_on = e.get("source"), e.get("read_on")
    if not (isinstance(source, str) and source.startswith("https://") and isinstance(read_on, str) and _DATE.match(read_on)):
        return None
    try:
        datetime.datetime.strptime(read_on, "%Y-%m-%d")
    except ValueError:
        return None
    return e


def _region_of(task):
    region = task.get("region")
    if isinstance(region, str) and region:
        return region
    zone = task.get("zone")
    if isinstance(zone, str) and zone:
        return _ZONE_LETTER.sub("", zone)
    return None


def cost_of_tasks(tasks, rates, default_region=None):
    """{usd, currency, unknown_reasons, as_of} for these tasks (dicts with name, realtime_ms, machine_type, price_model and zone or region).
    One task that cannot be priced makes the whole answer None with a reason for each; there is no partial sum. as_of is the oldest read
    date of the rate entries that were used. default_region is the region to use for a task that names none."""
    if not isinstance(rates, dict):
        return _unknown(["價目表讀不到 (the rates file cannot be read)"])
    total, reasons, dates = 0.0, [], []
    for i, t in enumerate(tasks):
        label = "task %s" % (t.get("name") or i + 1)
        missing = []
        rt = t.get("realtime_ms")
        if not _number(rt) or rt < 0:
            missing.append("缺跑多久 (no realtime_ms)")
        machine = t.get("machine_type")
        if not (isinstance(machine, str) and machine):
            missing.append("缺機器型號 (no machine type)")
        model = t.get("price_model")
        if not isinstance(model, str) or not model:
            missing.append("缺計價模式 (no price model)")
        elif model.lower() not in _MODELS:
            missing.append("計價模式 %s 不認得 (price model %s is not known)" % (_shown(model), _shown(model)))
        region = _region_of(t) or default_region
        if not region:
            missing.append("缺區域 (no region or zone)")
        if not missing:
            if region not in (rates.get("regions") or {}):
                missing.append("區域 %s 沒有價目 (no rates for region %s)" % (region, region))
            else:
                e = _entry(rates, region, machine)
                price = e.get(model.lower()) if e else None
                if e is None:
                    missing.append("機器型號 %s 不在價目表 (machine type %s is not in the rates)" % (machine, machine))
                elif not _number(price) or price <= 0:
                    missing.append("機器型號 %s 沒有 %s 價 (machine type %s has no %s price)" % (machine, model.lower(), machine, model.lower()))
        if missing:
            reasons.append("%s: %s" % (label, "; ".join(missing)))
        else:
            total += rt / MS_PER_HOUR * price
            dates.append(e["read_on"])
    if reasons:
        return _unknown(reasons)
    return {"usd": total, "currency": CURRENCY, "unknown_reasons": [], "as_of": min(dates) if dates else None}


def run_tasks_cost(index_path, run_name, rates, default_region=None):
    """cost_of_tasks for the finished tasks (retries and failed ones too, they were paid for) a run kept in the index. Read-only: it never
    creates a table, and an index made before the machine columns gives the NOT_STORED answer."""
    view = status.find_run(index_path, run_name)
    if view is None:
        return _unknown([NOT_STORED])
    con = status._open_readonly(index_path)
    if con is None:
        return _unknown([NOT_STORED])
    try:
        rows = con.execute("SELECT name, status, realtime_ms, machine_type, price_model, cloud_zone FROM task_usage "
                           "WHERE run_id = ? ORDER BY task_key", (view["id"],)).fetchall()
    except sqlite3.OperationalError:
        return _unknown([NOT_STORED])
    finally:
        con.close()
    if not rows:
        return _unknown([NOT_STORED])
    tasks = [{"name": r["name"], "status": r["status"], "realtime_ms": r["realtime_ms"], "machine_type": r["machine_type"],
              "price_model": r["price_model"], "zone": r["cloud_zone"]} for r in rows]
    return cost_of_tasks(tasks, rates, default_region)


def _launch_facts(platform_path, run_name):
    """{cloud, location, pipeline} of a run from its newest row of the hand-off record: whether it went to a Google Batch environment, that
    environment's location, and the pipeline of the content that was confirmed (None when that content is no longer kept). None when the run
    has no row."""
    con = store.open_readonly(platform_path)
    if con is None:
        return None
    try:
        row = jobs.latest_launch(con, run_name)
        if row is None:
            return None
        _, job = jobs.launch_job(con, row, 0)
        content = jobs.launch_content(con, row, job)
        pipeline = content[0].get("pipeline") if content else None
        ce_name = row["ce"]
    except sqlite3.Error:
        return None
    finally:
        con.close()
    ce = compute_envs.get(platform_path, ce_name) if ce_name else None
    config = ce["config"] if ce else {}
    location = config.get("location") if isinstance(config.get("location"), str) else None
    return {"cloud": bool(ce) and ce["platform"] == CLOUD, "location": location,
            "pipeline": pipeline if isinstance(pipeline, str) else None}


def _same_pipeline(a, b):
    def norm(x):
        return x.strip().rstrip("/").lower() if isinstance(x, str) else None
    return norm(a) is not None and norm(a) == norm(b)


def _runs_of(index_path, platform_path, user_id):
    """The runs of this user that went to a Google Batch environment (newest first), each as (run view, launch facts)."""
    out = []
    for r in status.list_runs(index_path, status.now(), names=jobs.owned_run_names(platform_path, user_id)):
        facts = _launch_facts(platform_path, r["name"])
        if facts and facts["cloud"]:
            out.append((r, facts))
    return out


def month_used(index_path, platform_path, user_id, month, rates):
    """{usd, currency, unknown_runs} the user has used on Google Batch in `month` ('YYYY-MM', Taipei time, by start): the runs that started
    then and whose newest launch went to a Google Batch environment, added up now. A run that cannot be priced is counted in unknown_runs
    and left out of usd; it does not make the month unknown."""
    total, unknown = 0.0, 0
    for r, facts in _runs_of(index_path, platform_path, user_id):
        started = r.get("started_at")
        if not started or su._taipei_month(started) != month:
            continue
        usd = run_tasks_cost(index_path, r["name"], rates, facts["location"])["usd"]
        if usd is None:
            unknown += 1
        else:
            total += usd
    return {"usd": total, "currency": CURRENCY, "unknown_runs": unknown}


def estimate_launch(index_path, platform_path, user_id, pipeline, rates):
    """The cost of the user's latest successful Google Batch run of the same pipeline that can be priced, with basis ('run <name>'). No such
    run gives usd None and the reason; nothing is worked out from resource limits."""
    for r, facts in _runs_of(index_path, platform_path, user_id):
        if r["status"] != "succeeded" or not _same_pipeline(facts["pipeline"], pipeline):
            continue
        out = run_tasks_cost(index_path, r["name"], rates, facts["location"])
        if out["usd"] is not None:
            return dict(out, basis="run %s" % r["name"])
    return _unknown([NO_HISTORY], basis=None)


def _money(x):
    return "US$%.2f" % x


NO_CAP = ("管理者還沒有替你設定每月雲端費用上限，所以不能送到雲端；請管理者執行 abf-platform user cloud-cap <名字> <美元> "
          "(no monthly cloud cap is set for you)")


def cap_problem(platform_path, ce_name, bundle, user_id, *, index_path=None, tokens_path=None, rates=None, now=None):
    """None to let a launch go, or the plain sentence that says why a new launch to Google Batch is refused. Only a Google Batch environment
    is looked at: any other kind returns None before the rates, the cap or any database of the index is read. The estimate is from the
    pipeline the bundle names. Refused: no cap set; this month's use is at or over the cap; use plus estimate is over the cap. An estimate
    that cannot be worked out does not refuse a person who still has room."""
    ce = compute_envs.get(platform_path, ce_name) if ce_name else None
    if not ce or ce["platform"] != CLOUD:
        return None
    index_path = index_path or store.default_index_path()
    tokens_path = tokens_path or store.default_tokens_path(index_path)
    cap = store.cloud_cap(tokens_path, user_id)
    if cap is None:
        return NO_CAP
    rates = rates if rates is not None else load_rates()
    at = status.now() if now is None else now
    month = datetime.datetime.fromtimestamp(at, su.TAIPEI).strftime("%Y-%m")
    used = month_used(index_path, platform_path, user_id, month, rates)
    spent = used["usd"]
    floor = used["unknown_runs"]
    used_text = ("至少 %s（另有 %d 個 run 算不出來）" % (_money(spent), floor)) if floor else ("約 %s" % _money(spent))
    left = max(0.0, cap - spent)
    pipeline = bundle.get("pipeline") if isinstance(bundle, dict) else None
    estimate = estimate_launch(index_path, platform_path, user_id, pipeline, rates)["usd"]
    if round(spent, 6) >= round(cap, 6):
        return ("本月雲端費用上限 %s，已用%s，剩 %s，這個月不能再送出新的雲端分析。請找管理者調整上限，或下個月再送出 "
                "(this month's cloud cap is %s, %s used, %s left; no new cloud analysis can be sent this month)"
                % (_money(cap), used_text, _money(left), _money(cap), used_text.replace("約", "about").replace("至少", "at least"),
                   _money(left)))
    if estimate is not None and round(spent + estimate, 6) > round(cap, 6):
        return ("本月雲端費用上限 %s，已用%s，剩約 %s；這次預估約 %s，會超過。請找管理者調整上限，或下個月再送出 "
                "(this month's cloud cap is %s, %s used, about %s left; this launch is estimated at about %s)"
                % (_money(cap), used_text, _money(left), _money(estimate), _money(cap),
                   used_text.replace("約", "about").replace("至少", "at least"), _money(left), _money(estimate)))
    return None
