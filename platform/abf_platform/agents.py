# Not Tower Agent: its wire protocol is undocumented and it talks only to Seqera; this is a three-request protocol, documented in docs/PLATFORM.md, that the agent opens outward.
"""The platform's side of the agent protocol: hello, poll, result.

An agent only ever calls the platform; the platform never calls an agent (a poll is a request the agent
keeps open). Whether an agent is online is worked out when someone asks, from its last contact and the
clock: there is no background program watching agents.

  POST /agent/hello          {name, version}  -> {agent, heartbeat_seconds, poll_seconds}; also the beat
  POST /agent/poll           {name}           -> {job: null} after the poll time, or {job: {id, kind, args}}
  POST /agent/result/{id}    {state, result}  -> {accepted, late}

Every request carries an agent token (Authorization: Bearer ...). A run token is refused here, and an
agent token is refused on the trace endpoints.
"""
import asyncio
import json
import re
import time

from starlette.responses import JSONResponse
from starlette.routing import Route

from . import common, jobs, store

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def status_of(last_seen_at, at, offline_after=None):
    limit = common.offline_after_seconds() if offline_after is None else offline_after
    return "online" if at - last_seen_at <= limit else "offline"


def view(row, at, offline_after=None):
    return {"name": row["name"], "version": row["version"], "status": status_of(row["last_seen_at"], at, offline_after),
            "last_contact_at": common.epoch_iso_ms(row["last_seen_at"])}


def list_agents(state_path, at, offline_after=None):
    """All agents that ever said hello, with online or offline as of `at`. Opens the file read-only.
    offline_after (seconds) replaces three heartbeats; a caller that knows the agent's own beat passes it."""
    con = store.open_readonly(state_path)
    if con is None:
        return []
    try:
        return [view(r, at, offline_after) for r in con.execute("SELECT * FROM agents ORDER BY name")]
    finally:
        con.close()


def register(state_path, name, version, clock=time.time):
    """Record that the agent called now; the same name is the same agent, never a second row."""
    now = clock()
    con = store.connect_state(state_path)
    try:
        with con:
            con.execute("INSERT INTO agents (name, version, first_seen_at, last_seen_at) VALUES (?, ?, ?, ?) "
                        "ON CONFLICT(name) DO UPDATE SET version = COALESCE(excluded.version, agents.version), "
                        "last_seen_at = excluded.last_seen_at", (name, version, now, now))
    finally:
        con.close()


def touch(state_path, name, clock):
    now = clock()
    con = store.connect_state(state_path)
    try:
        with con:
            con.execute("UPDATE agents SET last_seen_at = ? WHERE name = ?", (now, name))
    finally:
        con.close()


def make_routes(state_path, tokens_path, clock=time.time):
    store.init_state(state_path)

    def auth(request):
        """The token row of an agent token, else None."""
        row = store.lookup_token(tokens_path, common.token_from_header(request.headers.get("authorization")))
        return row if row and row["kind"] == "agent" else None

    def unauthorized():
        return JSONResponse({"message": "Unauthorized: missing, unknown or revoked agent token"}, status_code=401)

    async def body_of(request):
        raw = await request.body()
        if not raw.strip():
            return {}, None
        try:
            body = json.loads(raw)
        except ValueError:
            return None, JSONResponse({"message": "The request body is not valid JSON"}, status_code=400)
        if not isinstance(body, dict):
            return None, JSONResponse({"message": "The request body must be a JSON object"}, status_code=400)
        return body, None

    def name_for(row, body):
        """The agent's name. A name in the body must be the one the token was made for."""
        claimed = body.get("name")
        if claimed is not None and claimed != row["agent_name"]:
            return None
        return row["agent_name"]

    def wrong_name():
        return JSONResponse({"message": "This token was made for another agent name"}, status_code=403)

    async def hello(request):
        row = auth(request)
        if row is None:
            return unauthorized()
        body, err = await body_of(request)
        if err:
            return err
        name = name_for(row, body)
        if name is None:
            return wrong_name()
        version = body.get("version")
        version = version[:64] if isinstance(version, str) and version else None
        register(state_path, name, version, clock)
        return JSONResponse({"agent": name, "heartbeat_seconds": common.heartbeat_seconds(),
                             "poll_seconds": common.poll_seconds()})

    async def poll(request):
        row = auth(request)
        if row is None:
            return unauthorized()
        body, err = await body_of(request)
        if err:
            return err
        name = name_for(row, body)
        if name is None:
            return wrong_name()
        register(state_path, name, None, clock)
        # an asyncio deadline loop on the real clock: other requests are served while this one waits
        end = time.monotonic() + common.poll_seconds()
        job = jobs.claim(state_path, name, clock)
        while job is None and time.monotonic() < end:
            await asyncio.sleep(min(0.5, max(0.0, end - time.monotonic())))
            if await request.is_disconnected():  # the agent is gone: not a contact, and no job is taken for it
                return JSONResponse({"job": None})
            if auth(request) is None:  # revoked while waiting
                return unauthorized()
            job = jobs.claim(state_path, name, clock)
        touch(state_path, name, clock)
        return JSONResponse({"job": job})

    async def result(request):
        row = auth(request)
        if row is None:
            return unauthorized()
        body, err = await body_of(request)
        if err:
            return err
        name = name_for(row, body)
        if name is None:
            return wrong_name()
        try:
            job_id = int(request.path_params["jid"])
        except ValueError:
            return JSONResponse({"message": "No such job"}, status_code=404)
        register(state_path, name, None, clock)
        code, answer = jobs.take_result(state_path, name, job_id, body.get("state"), body.get("result"), clock)
        return JSONResponse(answer, status_code=code)

    return [
        Route("/agent/hello", hello, methods=["POST"]),
        Route("/agent/poll", poll, methods=["POST"]),
        Route("/agent/result/{jid}", result, methods=["POST"]),
    ]
