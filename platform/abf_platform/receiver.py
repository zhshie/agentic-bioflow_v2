# Not nf-shard: it accepts any non-empty token and keeps its data in Postgres; this receiver checks tokens it issued itself and keeps a small SQLite index.
"""The receiver: the five requests Nextflow's nf-tower plugin sends, plus GET /user-info, plus the three
requests of the agents (agents.py).

The plugin source is the specification (specs/008-run-receiver/research.md). Anything the
plugin sends that is not listed there is ignored, never stored, and never an error.
"""
import json
import time

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import agents, common, store

INT_UNSET = 2147483647  # Nextflow's 'no exit code yet'
COUNT_FIELDS = ("succeeded", "cached", "failed", "aborted", "running", "pending", "submitted")


def _reply(status_code, message, **extra):
    return JSONResponse(dict(message=message, **extra), status_code=status_code)


_token_from_header = common.token_from_header


def _int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def create_app(index_path, tokens_path, clock=time.time, platform_path=None):
    store.init_index(index_path)
    platform_path = platform_path or store.default_platform_path(index_path)

    def authorize(request):
        """Token id, or None. The check comes before anything is read or written."""
        return store.token_id(tokens_path, _token_from_header(request.headers.get("authorization")))

    def unauthorized():
        return _reply(401, "Unauthorized: missing or unknown access token")

    async def json_object(request):
        raw = await request.body()
        if not raw.strip():
            return None, _reply(400, "Empty request body")
        try:
            body = json.loads(raw)
        except ValueError:
            return None, _reply(400, "The request body is not valid JSON")
        if not isinstance(body, dict):
            return None, _reply(400, "The request body must be a JSON object")
        return body, None

    def apply_progress(con, rid, progress, tasks):
        if isinstance(progress, dict):
            sets = ", ".join("n_%s = ?" % f for f in COUNT_FIELDS)
            con.execute("UPDATE runs SET %s WHERE id = ?" % sets,
                        [_int(progress.get(f)) for f in COUNT_FIELDS] + [rid])
            procs = progress.get("processes")
            if isinstance(procs, list):
                con.execute("DELETE FROM processes WHERE run_id = ?", (rid,))
                for p in procs:
                    if isinstance(p, dict) and p.get("name"):
                        cols = ", ".join("n_%s" % f for f in COUNT_FIELDS)
                        con.execute("INSERT OR REPLACE INTO processes (run_id, name, %s) VALUES (?, ?, %s)"
                                    % (cols, ", ".join("?" * len(COUNT_FIELDS))),
                                    [rid, str(p["name"])] + [_int(p.get(f)) for f in COUNT_FIELDS])
        for t in tasks if isinstance(tasks, list) else []:
            if not isinstance(t, dict) or not t.get("name"):
                continue
            key = "%s:%s" % (t.get("taskId"), t.get("attempt"))
            if t.get("status") == "FAILED":
                code = _int(t.get("exit"), None)
                if code is not None and code >= INT_UNSET:
                    code = None
                con.execute("INSERT INTO failed_tasks (run_id, task_key, name, exit_code) VALUES (?, ?, ?, ?) "
                            "ON CONFLICT(run_id, task_key) DO UPDATE SET name = excluded.name, exit_code = excluded.exit_code",
                            (rid, key, str(t["name"]), code))
            else:
                con.execute("DELETE FROM failed_tasks WHERE run_id = ? AND task_key = ?", (rid, key))

    def locate(con, rid, tid):
        """(row, error response): 404 for an unknown run, 403 for a run of another token."""
        row = con.execute("SELECT id, token_id FROM runs WHERE id = ?", (rid,)).fetchone()
        if row is None:
            return None, _reply(404, "No such run")
        if row["token_id"] != tid:
            return None, _reply(403, "This run belongs to another token")
        return row, None

    async def create(request):
        tid = authorize(request)
        if tid is None:
            return unauthorized()
        body, err = await json_object(request)
        if err:
            return err
        sid, name = body.get("sessionId"), body.get("runName")
        if not (isinstance(sid, str) and sid and isinstance(name, str) and name):
            return _reply(400, "sessionId and runName are required")
        rid = common.run_id(sid, name)
        now = clock()
        con = store.connect_index(index_path)
        try:
            with con:
                row = con.execute("SELECT token_id FROM runs WHERE id = ?", (rid,)).fetchone()
                if row is None:
                    con.execute("INSERT INTO runs (id, session_id, run_name, token_id, source, started_at, "
                                "last_message_at, project_name) VALUES (?, ?, ?, ?, 'live', ?, ?, ?)",
                                (rid, sid, name, tid, int(now), now,
                                 body.get("projectName") if isinstance(body.get("projectName"), str) else None))
                elif row["token_id"] != tid:
                    return _reply(403, "This run belongs to another token")
                else:
                    con.execute("UPDATE runs SET last_message_at = ? WHERE id = ?", (now, rid))
        finally:
            con.close()
        return JSONResponse({"workflowId": rid})

    async def begin(request):
        tid = authorize(request)
        if tid is None:
            return unauthorized()
        rid = request.path_params["rid"]
        con = store.connect_index(index_path)
        try:
            _, err = locate(con, rid, tid)
            if err:
                return err
            body, err = await json_object(request)
            if err:
                return err
            wf = body.get("workflow")
            if not isinstance(wf, dict):
                return _reply(400, "workflow is required")
            params = wf.get("params")
            nf = wf.get("nextflow") if isinstance(wf.get("nextflow"), dict) else {}
            with con:
                start = common.parse_iso_epoch(wf.get("start"))
                if start is not None:
                    con.execute("UPDATE runs SET started_at = ? WHERE id = ?", (start, rid))
                con.execute("UPDATE runs SET last_message_at = ?, nextflow_version = ?, params_json = ?, "
                            "project_name = COALESCE(?, project_name) WHERE id = ?",
                            (clock(), nf.get("version") if isinstance(nf.get("version"), str) else None,
                             json.dumps(common.scrub_params(params)) if isinstance(params, dict) else None,
                             wf.get("projectName") if isinstance(wf.get("projectName"), str) else None, rid))
        finally:
            con.close()
        return JSONResponse({"status": "OK", "workflowId": rid})

    async def progress_like(request):
        """progress and heartbeat: the counters Nextflow keeps, and the tasks that changed."""
        tid = authorize(request)
        if tid is None:
            return unauthorized()
        rid = request.path_params["rid"]
        con = store.connect_index(index_path)
        try:
            _, err = locate(con, rid, tid)
            if err:
                return err
            body, err = await json_object(request)
            if err:
                return err
            with con:
                con.execute("UPDATE runs SET last_message_at = ? WHERE id = ?", (clock(), rid))
                apply_progress(con, rid, body.get("progress"), body.get("tasks"))
        finally:
            con.close()
        return JSONResponse({"status": "OK"})

    async def complete(request):
        tid = authorize(request)
        if tid is None:
            return unauthorized()
        rid = request.path_params["rid"]
        con = store.connect_index(index_path)
        try:
            _, err = locate(con, rid, tid)
            if err:
                return err
            body, err = await json_object(request)
            if err:
                return err
            wf = body.get("workflow")
            if not isinstance(wf, dict):
                return _reply(400, "workflow is required")
            now = clock()
            ended = common.parse_iso_epoch(wf.get("complete"))
            with con:
                con.execute("UPDATE runs SET last_message_at = ?, final_status = ?, ended_at = ?, exit_status = ? "
                            "WHERE id = ?",
                            (now, "succeeded" if wf.get("success") is True else "failed",
                             ended if ended is not None else int(now),
                             _int(wf.get("exitStatus"), None), rid))
                start = common.parse_iso_epoch(wf.get("start"))
                if start is not None:
                    con.execute("UPDATE runs SET started_at = ? WHERE id = ?", (start, rid))
                apply_progress(con, rid, body.get("progress"), None)
                found = common.extract_error(wf.get("errorReport"))
                if found:
                    name, message = found
                    cur = con.execute("UPDATE failed_tasks SET error_message = ? WHERE run_id = ? AND name = ?",
                                      (message, rid, name))
                    if cur.rowcount == 0:
                        con.execute("INSERT OR IGNORE INTO failed_tasks (run_id, task_key, name, error_message) "
                                    "VALUES (?, ?, ?, ?)", (rid, "report:" + name, name, message))
        finally:
            con.close()
        return JSONResponse({"status": "OK"})

    async def user_info(request):
        if authorize(request) is None:
            return unauthorized()
        return JSONResponse({"user": {"id": 1, "userName": "abf-platform"}})

    routes = [
        Route("/trace/create", create, methods=["POST"]),
        Route("/trace/{rid}/begin", begin, methods=["PUT"]),
        Route("/trace/{rid}/progress", progress_like, methods=["PUT"]),
        Route("/trace/{rid}/heartbeat", progress_like, methods=["PUT"]),
        Route("/trace/{rid}/complete", complete, methods=["PUT"]),
        Route("/user-info", user_info, methods=["GET"]),
    ] + agents.make_routes(platform_path, tokens_path, clock)
    return Starlette(routes=routes)
