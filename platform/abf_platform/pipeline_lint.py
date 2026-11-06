# Nothing existing: nf-core/tools lints a project on the machine that has it; this platform runs no program, so it only queues the lint for an agent of the caller and keeps the answer next to the pipeline's check result.
"""The optional lint of a composed pipeline (feature 017c2a): ask the caller's agent to run `nf-core pipelines lint` on the
project files of one version, and keep what comes back in the version's row of `pipeline_validations`.

The platform queues one `lint_pipeline` job (jobs.enqueue_lint_pipeline) and never waits. The answer is collected the next time the
check result of that version is read (`collect`); there is no background task. The agent runs the lint on its own host, never on
the cluster. Four nullable columns hold it: lint_status, lint_report, lint_job_id and lint_at (`ensure_columns` adds them to a
table made without them; a row with a NULL lint_job_id was never linted)."""
import json
import sqlite3
import time

from . import jobs, pipeline_launch, store

COLUMNS = (("lint_status", "TEXT"), ("lint_report", "TEXT"), ("lint_job_id", "INTEGER"), ("lint_at", "REAL"))

_ERROR_TEXT = ("站台跑 lint 時出錯，沒有結果；請確認代理在線，再驗證一次 "
               "(the agent failed while running the lint and there is no result; check that your agent is online and validate again)")
_REFUSED_TEXT = ("站台拒絕執行這個 lint（專案檔的路徑或大小不合格）"
                 "(the agent refused to run the lint: a path or a size in the project is not acceptable)")
_EXPIRED_TEXT = ("lint 工作逾時，沒有被執行完；請確認代理在線，再驗證一次 "
                 "(the lint job ran out of time before it finished; check that your agent is online and validate again)")
_GONE_TEXT = ("找不到這個 lint 工作了，沒有結果；請再驗證一次 (the lint job is no longer there, so there is no result; validate again)")


def ensure_columns(con):
    """Add the lint columns the table does not have yet. Safe to call again and again; rows already there are not touched."""
    have = {r[1] for r in con.execute("PRAGMA table_info(pipeline_validations)")}
    for name, kind in COLUMNS:
        if name not in have:
            try:
                con.execute("ALTER TABLE pipeline_validations ADD COLUMN %s %s" % (name, kind))
            except sqlite3.OperationalError:       # another process added it first
                pass
    con.commit()


def _refused(message):
    return {"state": "refused", "message": message}


def request(platform_path, pipeline_id, name, version, files, *, compute_env=None, caller=None, clock=time.time):
    """Queue one lint of the project `files` ({path: text}) of this version and mark the version's row `queued`. Returns
    {"state": "queued", "job_id": n} or {"state": "refused", "message": ...}; a refusal changes nothing."""
    size = sum(len(text.encode("utf-8")) for text in files.values())
    if size > pipeline_launch.MAX_BYTES:
        return _refused("專案檔全部共 %d 位元組，超過 lint 的上限 %d；請減少節點 (the project files are %d bytes together, more than the limit of %d; "
                        "use fewer nodes)" % (size, pipeline_launch.MAX_BYTES, size, pipeline_launch.MAX_BYTES))
    if len(files) > pipeline_launch.MAX_FILES:
        return _refused("專案有 %d 個檔案，超過 lint 的上限 %d；請減少節點 (the project has %d files, more than the limit of %d; use fewer nodes)"
                        % (len(files), pipeline_launch.MAX_FILES, len(files), pipeline_launch.MAX_FILES))
    owner = caller.user_id if caller is not None else None
    try:
        job_id = jobs.enqueue_lint_pipeline(platform_path, name, version, dict(files), compute_env=compute_env, clock=clock,
                                            caller_user_id=owner)
    except jobs.JobRefused as e:
        return _refused("沒有排入 lint：%s (the lint was not queued)" % e)
    con = store.connect_state(platform_path)
    try:
        con.execute("UPDATE pipeline_validations SET lint_status = 'queued', lint_report = NULL, lint_job_id = ?, lint_at = ? "
                    "WHERE pipeline_id = ? AND version = ?", (job_id, clock(), pipeline_id, version))
        con.commit()
    except sqlite3.Error:
        con.rollback()
        return _refused("lint 工作已排入，但狀態沒有存成功；請稍後再驗證一次 (the lint was queued but its state was not saved; validate again in a moment)")
    finally:
        con.close()
    return {"state": "queued", "job_id": job_id}


def _report(cleaned):
    counts = cleaned.get("counts") or {}
    lines = []
    if all(k in counts for k in ("passed", "warned", "failed")):
        lines.append("通過 %d／警告 %d／失敗 %d (passed %d / warned %d / failed %d)"
                     % (counts["passed"], counts["warned"], counts["failed"], counts["passed"], counts["warned"], counts["failed"]))
    if cleaned.get("reason"):
        lines.append(cleaned["reason"])
    if cleaned.get("report"):
        lines.append(cleaned["report"])
    return jobs._short("\n".join(lines), jobs.LINT_REPORT_MAX)


def _outcome(job):
    """(status, report, finished_at) of a finished job row, or None while it is still queued or claimed."""
    state = job["state"]
    if state in ("queued", "claimed"):
        return None
    if state == "done":
        try:
            raw = json.loads(job["result_json"]) if job["result_json"] else None
        except ValueError:
            raw = None
        cleaned = jobs.clean_result("lint_pipeline", raw)
        if not isinstance(raw, dict):
            return "error", _ERROR_TEXT, job["finished_at"]
        return cleaned["status"], _report(cleaned), job["finished_at"]
    if state == "refused":
        return "error", _REFUSED_TEXT, job["finished_at"]
    if state == "expired":
        return "expired", _EXPIRED_TEXT, job["finished_at"]
    return "error", _ERROR_TEXT, job["finished_at"]


def collect(con, row):
    """Take the answer of the lint job of this row if it has finished and write it into the four lint columns; the other columns
    are not touched. Does nothing unless the row says `queued`, so a finished lint is never looked up again. The row is not
    changed; the caller reads it again."""
    if row["lint_job_id"] is None or row["lint_status"] != "queued":
        return False
    try:
        job = con.execute("SELECT state, result_json, finished_at FROM jobs WHERE id = ?", (row["lint_job_id"],)).fetchone()
    except sqlite3.Error:
        return False
    if job is None:
        found = ("error", _GONE_TEXT, None)
    else:
        found = _outcome(job)
        if found is None:
            return False
    status, report, finished = found
    con.execute("UPDATE pipeline_validations SET lint_status = ?, lint_report = ?, lint_at = ? "
                "WHERE pipeline_id = ? AND version = ? AND lint_job_id = ? AND lint_status = 'queued'",
                (status, report, finished if finished is not None else time.time(), row["pipeline_id"], row["version"], row["lint_job_id"]))
    con.commit()
    return True


def shown(row):
    """The `lint` key of a version's check result, or None when it was never linted."""
    if row["lint_job_id"] is None:
        return None
    return {"status": row["lint_status"], "report": row["lint_report"] or "", "linted_at": row["lint_at"]}
