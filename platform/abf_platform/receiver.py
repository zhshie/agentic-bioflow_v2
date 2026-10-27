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


def _text64(value):
    """A short text the task event named (the machine type, the price model, the zone), cut to 64 characters; NULL when it is not a string."""
    return value[:64] if isinstance(value, str) else None


def create_app(index_path, tokens_path, clock=time.time, platform_path=None):
    store.init_index(index_path)
    platform_path = platform_path or store.default_platform_path(index_path)
    instance = store.instance_id(platform_path)

    def token_row(request):
        """The run token of the request ({'id', 'run_name', ...}), or None. The check comes before anything is read or written."""
        row = store.lookup_token(tokens_path, _token_from_header(request.headers.get("authorization")))
        return row if row and row["kind"] == "run" else None

    def authorize(request):
        row = token_row(request)
        return row["id"] if row else None

    def after_complete(request, rid):
        """True for a message that comes after the `complete` of its own run, from the token that complete ended, inside the
        short grace of store.ENDED_GRACE_SECONDS: the caller answers OK and writes nothing. Anything else is False."""
        row = store.lookup_ended_token(tokens_path, _token_from_header(request.headers.get("authorization")))
        if row is None:
            return False
        con = store.connect_index(index_path)
        try:
            run = con.execute("SELECT token_id, run_name, final_status FROM runs WHERE id = ?", (rid,)).fetchone()
        finally:
            con.close()
        return bool(run and run["final_status"] and run["token_id"] == row["id"] and run["run_name"] == row["run_name"])

    def unauthorized():
        # the header lets a program that probes a port tell this platform from whatever else answers there
        return JSONResponse({"message": "Unauthorized: missing or unknown access token"}, status_code=401,
                            headers={"X-ABF-Platform": instance})

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
        listed = [t for t in (tasks if isinstance(tasks, list) else []) if isinstance(t, dict) and t.get("name")]
        # earlier attempts first: a retry is a new task record (nf-tower 1.17.5 gives it a new task id, and may
        # send no `attempt` at all), so the order decides which attempt is the last word
        listed.sort(key=lambda t: (_int(t.get("attempt"), 0), _int(t.get("taskId"), 0)))
        for t in listed:
            key = "%s:%s" % (t.get("taskId"), t.get("attempt"))
            name = str(t["name"])
            if t.get("status") in ("COMPLETED", "FAILED"):
                # The usage of a finished task, for the SU a run used. One row per attempt, and a retry does not delete the attempt
                # before it (that attempt also spent SU); failed_tasks below is the opposite on purpose: one row per task name.
                queue = t.get("queue")
                con.execute("INSERT INTO task_usage (run_id, task_key, name, status, cpus, realtime_ms, queue, machine_type, price_model, cloud_zone) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                            "ON CONFLICT(run_id, task_key) DO UPDATE SET name = excluded.name, status = excluded.status, "
                            "cpus = excluded.cpus, realtime_ms = excluded.realtime_ms, queue = excluded.queue, "
                            "machine_type = excluded.machine_type, price_model = excluded.price_model, cloud_zone = excluded.cloud_zone",
                            (rid, key, name, t["status"], _int(t.get("cpus"), None), _int(t.get("realtime"), None),
                             queue if isinstance(queue, str) else None, _text64(t.get("machineType")), _text64(t.get("priceModel")),
                             _text64(t.get("cloudZone"))))
            # one row per task name: a later attempt of the same task replaces the earlier one, whatever its outcome
            con.execute("DELETE FROM failed_tasks WHERE run_id = ? AND name = ? AND task_key != ?", (rid, name, key))
            if t.get("status") == "FAILED":
                code = _int(t.get("exit"), None)
                if code is not None and code >= INT_UNSET:
                    code = None
                workdir = t.get("workdir")      # where Nextflow ran the task, when it said; never guessed, so a missing one stays NULL
                workdir = workdir[:store.WORKDIR_MAX_CHARS] if isinstance(workdir, str) and workdir else None
                con.execute("INSERT INTO failed_tasks (run_id, task_key, name, exit_code, workdir) VALUES (?, ?, ?, ?, ?) "
                            "ON CONFLICT(run_id, task_key) DO UPDATE SET name = excluded.name, exit_code = excluded.exit_code, "
                            "workdir = COALESCE(excluded.workdir, failed_tasks.workdir)",
                            (rid, key, name, code, workdir))
            else:
                con.execute("DELETE FROM failed_tasks WHERE run_id = ? AND task_key = ?", (rid, key))

    def locate(con, rid, trow):
        """(row, error response): 404 for an unknown run, 403 for a run of another token, and 403 for a token the platform made
        for one run name when the run has another name."""
        row = con.execute("SELECT id, token_id, run_name FROM runs WHERE id = ?", (rid,)).fetchone()
        if row is None:
            return None, _reply(404, "No such run")
        if row["token_id"] != trow["id"]:
            return None, _reply(403, "This run belongs to another token")
        if trow["run_name"] is not None and trow["run_name"] != row["run_name"]:
            return None, _reply(403, "This token is for another run")
        return row, None

    async def create(request):
        row = token_row(request)
        if row is None:
            return unauthorized()
        tid = row["id"]
        body, err = await json_object(request)
        if err:
            return err
        sid, name = body.get("sessionId"), body.get("runName")
        if not (isinstance(sid, str) and sid and isinstance(name, str) and name):
            return _reply(400, "sessionId and runName are required")
        if row["run_name"] is not None and row["run_name"] != name:
            return _reply(403, "This token is for another run")
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
        trow = token_row(request)
        if trow is None:
            return unauthorized()
        rid = request.path_params["rid"]
        con = store.connect_index(index_path)
        try:
            _, err = locate(con, rid, trow)
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
        trow = token_row(request)
        if trow is None:
            if after_complete(request, request.path_params["rid"]):
                return JSONResponse({"status": "OK"})   # a message after complete: nothing is written
            return unauthorized()
        rid = request.path_params["rid"]
        con = store.connect_index(index_path)
        try:
            _, err = locate(con, rid, trow)
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
        trow = token_row(request)
        if trow is None:
            if after_complete(request, request.path_params["rid"]):
                return JSONResponse({"status": "OK"})   # a second complete of an aborted run: nothing is written
            return unauthorized()
        tid = trow["id"]
        rid = request.path_params["rid"]
        con = store.connect_index(index_path)
        try:
            _, err = locate(con, rid, trow)
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
                succeeded = wf.get("success") is True
                # Nextflow's own words for a failure (never made up here); a run that succeeded has none
                reason = None if succeeded else common.run_failure_reason(wf.get("errorMessage"), wf.get("errorReport"))
                con.execute("UPDATE runs SET last_message_at = ?, final_status = ?, ended_at = ?, exit_status = ?, "
                            "failure_reason = ? WHERE id = ?",
                            (now, "succeeded" if succeeded else "failed",
                             ended if ended is not None else int(now),
                             _int(wf.get("exitStatus"), None), reason, rid))
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
        if trow["run_name"] is not None:
            # a token the platform made for one launch ends with that run; a token of `token new` is not for one run
            store.end_token(tokens_path, trow["id"])
        if succeeded and trow["run_name"] is not None:
            try:
                from . import actions       # here and not at the top: actions imports a great deal that the receiver does not need
                actions.offer_cleanup(platform_path, index_path, trow["run_name"], clock=clock)
            except Exception:
                pass                        # an offer that fails changes nothing about the answer or the record of the run
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
