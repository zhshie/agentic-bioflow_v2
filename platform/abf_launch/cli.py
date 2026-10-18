# Not Seqera's Launchpad form or its command line: they are Seqera's and send the run to Seqera; these commands show the whole analysis on a terminal, ask, and hand it to the agent that sits next to the cluster.
"""abf-platform launch | cancel | forget | launches | fetch-records (feature 007b; forget: keep-submissions).

launch   builds the bundle (abf_station.launch.render_bundle(), the same function the agent runs; the code that
         calls it is build.py, which the MCP tools use too), shows all of it, and
         sends it only after y or Y on the terminal. cancel does the same for one run. Both refuse in the person's
         words, before any question, when a choice cannot be made into a launch.
launches lists the hand-off record: facts only (what was sent, the Slurm number, when a cancel was requested). It
         never says how a run is doing; that is Nextflow's to say (get_run).
fetch-records asks the agent to read Nextflow's own logs of one launch back, for `rebuild`. It only reads.
"""
import asyncio
import json
import os
import sys
import time

from abf_platform import actions, jobs, store
from abf_station import launch as bundle_mod    # BundleError and the one render function live here; build.py calls them (tests/test_launch_static.py reads this line)

from . import build, terminal

QUESTION_LAUNCH = "確定送出？(y/N)"
QUESTION_CANCEL = "確定取消？(y/N)"
QUESTION_FORGET = "確定刪除？(y/N)"
NOT_SENT = "未送出"
GRACE_DEFAULT = 120.0


def _say(text=""):
    print(text, flush=True)


def _err(text):
    print(text, file=sys.stderr, flush=True)


def _state():
    return store.default_platform_path()


# ---- reading what the person gave, the checks before any question and the screens are in abf_launch/build.py (shared with the MCP tools)

read_samplesheet, infer, read_params_file = build.read_samplesheet, build.infer, build.read_params_file
launch_screen = build.launch_screen


def _refuse(text):
    _err("%s: %s" % (NOT_SENT, text))
    return 1


# ---- launch ---------------------------------------------------------------------------------------------------------

def _account(name):
    """(Caller or None, why not): who a launch typed here is for (116). Once any user exists the terminal must name the account
    (--user NAME), because the launch is recorded as that user's and may use only that user's environments. With no user at all
    there is nobody to name and the record stays empty. Whoever has this terminal can name any account: the terminal is the
    administrator's, and the typed y is still theirs to give."""
    tokens = store.default_tokens_path()
    if name is None:
        if store.user_names(tokens):
            return None, ("要用 --user 名字 指明這次送出是誰的（平台上已有使用者）(name the account with --user NAME: "
                          "this platform has users, and a launch is recorded as one of theirs)")
        return None, None
    user = store.user_by_name(tokens, name)
    if user is None:
        return None, "沒有這個帳號：%s (no such account)" % name
    return actions.Caller(user["user_id"], user["name"], user["lab"]), None


def cmd_launch(args):
    state = _state()
    store.assign_orphans(state, store.default_tokens_path())
    caller, why = _account(args.user)
    if why:
        return _refuse(why)
    try:
        ce_name, bundle = build.prepare_launch(
            state, ce=args.ce, pipeline=args.pipeline, revision=args.revision, run_name=args.run_name, samplesheet=args.samplesheet,
            params_file=args.params_file, param_items=args.param, path_columns=args.path_column,
            owner=caller.user_id if caller else None)
    except build.Refusal as e:
        return _refuse(str(e))
    why = terminal.terminal_problem()
    if why:
        return _refuse("要在終端機上互動回答 y 才會送出，這裡不行（%s）。沒有任何旗標或環境變數能代替這個回答 (needs an interactive terminal)" % why)
    if not terminal.ask(launch_screen(bundle, ce_name), QUESTION_LAUNCH):
        _err(NOT_SENT)
        return 1
    try:
        cid, job_id = actions.launch(state, ce_name, bundle, confirmed_by=actions.TERMINAL, caller=caller)
    except jobs.JobRefused as e:
        return _refuse(str(e))
    _say("已交給代理 %s（確認編號 %s）。等代理回報…" % (bundle["agent"], cid[:8]))
    return _report_launch(state, job_id, bundle)


def _grace():
    try:
        return max(0.0, float(os.environ.get("ABF_PLATFORM_LAUNCH_GRACE", GRACE_DEFAULT)))
    except ValueError:
        return GRACE_DEFAULT


def _row(state, run_name):
    """The newest row of the hand-off record for a run name (a refused launch leaves its row, and the name can be used again)."""
    con = store.open_readonly(state)
    if con is None:
        return None
    try:
        return jobs.latest_launch(con, run_name)
    finally:
        con.close()


def _row_of_job(state, job_id):
    """The row that this very launch job made."""
    con = store.open_readonly(state)
    if con is None:
        return None
    try:
        return con.execute("SELECT * FROM launches WHERE job_id = ?", (job_id,)).fetchone()
    finally:
        con.close()


def _late_message(state, job_id):
    con = store.open_readonly(state)
    if con is None:
        return None
    try:
        row = con.execute("SELECT late_result_json FROM jobs WHERE id = ?", (job_id,)).fetchone()
    finally:
        con.close()
    if row and row["late_result_json"]:
        return json.loads(row["late_result_json"]).get("result", {}).get("message")
    return None


def _submitted_line(row):
    return "已送出：Slurm 工作編號 %s；run 名稱 %s；專屬資料夾 %s。" % (row["slurm_job_id"], row["run_name"], row["run_folder"])


def _report_launch(state, job_id, bundle):
    run = bundle["run_name"]
    out = asyncio.run(jobs.wait_for_result(state, job_id))
    if out["state"] == "done" and out["ok"]:
        row = _row_of_job(state, job_id)
        _say(_submitted_line(row) + "進度請用 `abf-platform launches` 看送出的事實，Nextflow 起來後用 get_run 看每個 process。")
        return 0
    if out["state"] in ("refused", "error"):
        res = out["result"] or {}
        _err("未完成：%s" % (res.get("message") or out["state"]))
        if res.get("left_on_site"):
            _err("國網上留下：%s" % res["left_on_site"])
        return 1
    # the deadline passed. The agent may still be finishing; its answer is applied to the record whenever it comes.
    end = time.time() + _grace()
    late = None
    while time.time() < end and late is None:     # bounded by the grace time; a person is waiting at the terminal
        row = _row_of_job(state, job_id)
        if row is not None and row["submitted_at"] is not None:
            break
        late = _late_message(state, job_id)
        if late is None:
            time.sleep(0.25)
    row = _row_of_job(state, job_id)
    if row is not None and row["submitted_at"] is not None:
        _say(_submitted_line(row) + "（代理在期限之後才回報；這個編號已記下。）")
        return 0
    if not out.get("claimed"):
        _err("代理沒有領走這個工作，國網上沒有任何改變 (the agent never took the job; nothing was done on the site)")
        return 1
    if late:
        _err("代理回報（已逾期）：%s" % late)
    _err("結果不明：請查國網上的 %s 與 Slurm 工作 nf-%s" % (bundle["run_folder"], run))
    return 1


# ---- cancel ---------------------------------------------------------------------------------------------------------

def cmd_cancel(args):
    state = _state()
    try:
        ce_name, bundle, row = build.prepare_cancel(state, args.run)
    except build.Refusal as e:
        return _refuse(str(e))
    why = terminal.terminal_problem()
    if why:
        return _refuse("要在終端機上互動回答 y 才會取消，這裡不行（%s）(needs an interactive terminal)" % why)
    lines = build.cancel_screen(bundle, row)
    if not terminal.ask(lines, QUESTION_CANCEL):
        _err("未取消")
        return 1
    try:
        cid, job_id = actions.cancel(state, ce_name, bundle, confirmed_by=actions.TERMINAL, caller=None)
    except jobs.JobRefused as e:
        return _refuse(str(e))
    _say("已交給代理 %s（確認編號 %s）。等代理回報…" % (bundle["agent"], cid[:8]))
    out = asyncio.run(jobs.wait_for_result(state, job_id))
    if out["state"] == "done" and out["ok"]:
        _say("取消請求已送出（Slurm 工作 %s）。Nextflow 收到訊號後會收掉它底下的 task；它回報的結局請用 get_run 看。"
             "國網上若還有殘留的 task，請自己查（squeue）。" % bundle["slurm_job_id"])
        return 0
    res = out["result"] or {}
    _err("未取消：%s" % (res.get("message") or out["message"]))
    return 1


# ---- forget ---------------------------------------------------------------------------------------------------------

def cmd_forget(args):
    state = _state()
    index = store.default_index_path()
    code, message = actions.forget_check(state, index, args.run)
    if code == "nothing":
        _say(message)
        return 0
    if code != "ok":
        return _refuse_forget(message)
    why = terminal.terminal_problem()
    if why:
        return _refuse_forget("要在終端機上互動回答 y 才會刪除，這裡不行（%s）(needs an interactive terminal)" % why)
    if not terminal.ask(build.forget_screen(args.run), QUESTION_FORGET):
        _err("未刪除")
        return 1
    out = actions.forget(state, index, args.run, confirmed_by=actions.TERMINAL, caller=None)
    if not out["ok"]:
        return _refuse_forget(out["message"])
    _say(out["message"])
    return 0


def _refuse_forget(text):
    _err("未刪除: %s" % text)
    return 1


def _when(epoch):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epoch))


# ---- launches ---------------------------------------------------------------------------------------------------------

def _agent_result(job):
    try:
        return json.loads(job["result_json"]) if job is not None and job["result_json"] else {}
    except ValueError:
        return {}


def _not_submitted_lines(row, kind, job):
    """What to say of a launch that has no Slurm number: what its own job says, in the agent's words, never the platform's."""
    if kind == "refused":
        message = _agent_result(job).get("message")
        return ["  被代理拒絕：%s" % (terminal.esc(message) if message else "（代理沒有附原因）")]
    if kind == "waiting":
        return ["  等代理處理中（工作 %d）" % job["id"]]
    lines = ["  未送出：代理沒有回報 Slurm 工作編號（結果不明時請查國網上的專屬資料夾與 nf-%s）" % row["run_name"]]
    if job is not None and job["state"] == "error":     # the agent said what went wrong and what it left on the site
        res = _agent_result(job)
        if res.get("message"):
            lines.append("  代理回報：%s" % terminal.esc(res["message"]))
        if res.get("left_on_site"):
            lines.append("  國網上留下：%s" % terminal.esc(res["left_on_site"]))
    return lines


def cmd_launches(args):
    state = _state()
    con = store.open_readonly(state)
    rows = []
    what = {}      # launch row id -> (kind, job row or None) for the rows that have no Slurm number
    if con is not None:
        try:
            rows = con.execute("SELECT * FROM launches ORDER BY id").fetchall()
            now = store._now()
            for r in rows:
                if r["slurm_job_id"] is None:
                    try:
                        what[r["id"]] = jobs.launch_job(con, r, now)
                    except Exception:     # a database not upgraded yet: the row is shown as unknown, never a crash
                        what[r["id"]] = ("unknown", None)
        except Exception:
            rows = []
        finally:
            con.close()
    if not rows:
        _say("還沒有由平台送出的分析 (nothing was launched from this platform)")
        return 0
    index = store.open_readonly(store.default_index_path())
    known = {}
    if index is not None:
        try:
            for r in index.execute("SELECT id, run_name FROM runs"):
                known[r["run_name"]] = r["id"]
        except Exception:
            known = {}
        finally:
            index.close()
    users = store.user_names(store.default_tokens_path())
    for r in rows:
        head = "%s  Slurm %s  %s  確認於 %s" % (r["run_name"], r["slurm_job_id"] if r["slurm_job_id"] is not None else "-",
                                               terminal.esc(r["run_folder"]), _when(r["confirmed_at"]))
        owner = r["user_id"] if "user_id" in r.keys() else None
        if owner is not None or users:          # who sent it (116); a platform with no users at all lists as it always did
            head += "  送出者 %s" % terminal.esc(users.get(owner) or "(none: local only)")
        _say(head)
        if r["submitted_at"] is None:
            for line in _not_submitted_lines(r, *what.get(r["id"], ("unknown", None))):
                _say(line)
        elif r["run_name"] in known:
            _say("  已收到 Nextflow 的事件；請用 get_run 看（run id %s）" % known[r["run_name"]])
        else:
            _say("  已送出，尚未收到 Nextflow 事件（%s 送出）" % _when(r["submitted_at"]))
        if r["cancel_requested_at"] is not None:
            _say("  取消請求已於 %s 送出" % _when(r["cancel_requested_at"]))
    return 0


# ---- fetch-records -------------------------------------------------------------------------------------------------------

def cmd_fetch_records(args):
    state = _state()
    try:
        job_id = jobs.enqueue_fetch(state, args.run)
    except jobs.JobRefused as e:
        return _refuse(str(e))
    _say("已請代理讀回 %s 的 Nextflow 紀錄（唯讀）。注意：紀錄內含執行的路徑與參數，會存到這台機器的 %s" % (
        args.run, store.default_platform_path().parent / "records" / args.run))
    out = asyncio.run(jobs.wait_for_result(state, job_id))
    res = out["result"] or {}
    if out["state"] == "done" and out["ok"]:
        for f in res.get("files", []):
            _say("  %s  %d bytes%s" % (f["name"], f["size"], "  （已截斷：只取前 20 MB）" if f["truncated"] else ""))
        for why in res.get("refused", []):
            _say("  拒絕：%s" % why)
        _say("已存下 %d 個檔。接著執行 `abf-platform rebuild`，索引就以這些紀錄為準補齊。" % len(res.get("files", [])))
        return 0
    _err("未完成：%s" % (res.get("message") or out["message"]))
    return 1


# ---- the parsers ------------------------------------------------------------------------------------------------------

def add_commands(sub):
    s = sub.add_parser("launch", allow_abbrev=False,
                       help="show a whole analysis, ask on the terminal, and hand it to the agent",
                       description="Build everything that will be written and run on the site, show all of it, and send it "
                                   "only after you answer y on this terminal. Nothing can answer for you.")
    s.add_argument("--ce", help="the compute environment (default: the primary one)")
    s.add_argument("--pipeline", required=True, help="owner/name, e.g. nf-core/ampliseq")
    s.add_argument("--revision", required=True, help="a tag (2.18.0) or a full 40-character commit; never a branch")
    s.add_argument("--run-name", required=True, help="lower-case letters, digits, _ and -")
    s.add_argument("--samplesheet", required=True, help="the CSV file with one row per sample")
    s.add_argument("--param", action="append", help="name=value, repeatable")
    s.add_argument("--params-file", help="a flat file of name: value lines")
    s.add_argument("--path-column", action="append", help="a samplesheet column that holds file paths, repeatable")
    s.add_argument("--user", help="the account this is sent as: the person it is for; required once the platform has users "
                                  "(whoever has this terminal can name any account)")
    s.set_defaults(func=cmd_launch)

    c = sub.add_parser("cancel", allow_abbrev=False, help="stop one analysis of this platform, after the same kind of question",
                       description="Send a stop to the one Slurm job this platform started for the run, after you answer y.")
    c.add_argument("run", help="the run name")
    c.set_defaults(func=cmd_cancel)

    fg = sub.add_parser("forget", allow_abbrev=False, help="delete the content a finished run was sent with, after the same kind of question",
                        description="Clear the bundle and the screen text kept for one run (the record of who sent it and when stays), "
                                    "after you answer y. It cannot be undone.")
    fg.add_argument("run", help="the run name")
    fg.set_defaults(func=cmd_forget)

    ls = sub.add_parser("launches", allow_abbrev=False, help="list what was handed to agents: facts only, never a run's state",
                        description="The hand-off record: run, Slurm job number, folder, time, and whether a stop was requested.")
    ls.set_defaults(func=cmd_launches)

    f = sub.add_parser("fetch-records", allow_abbrev=False, help="read Nextflow's own logs of one run back (read only)",
                       description="Ask the agent to read .nextflow.log*, .nextflow/history and the trace of one run back from the "
                                   "site; `rebuild` then fills the index from them.")
    f.add_argument("run", help="the run name")
    f.set_defaults(func=cmd_fetch_records)
