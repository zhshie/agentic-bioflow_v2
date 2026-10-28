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
import sqlite3
import time
from pathlib import Path

from starlette.responses import JSONResponse
from starlette.routing import Route

from . import common, jobs, store

_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")


def status_of(last_seen_at, at, offline_after=None):
    limit = common.offline_after_seconds() if offline_after is None else offline_after
    return "online" if at - last_seen_at <= limit else "offline"


def view(row, at, offline_after=None):
    return {"name": row["name"], "version": row["version"], "status": status_of(row["last_seen_at"], at, offline_after),
            "last_contact_at": common.epoch_iso_ms(row["last_seen_at"])}


def list_agents(state_path, at, offline_after=None, owner=None):
    """All agents that ever said hello, with online or offline as of `at`. Opens the file read-only.
    offline_after (seconds) replaces three heartbeats; a caller that knows the agent's own beat passes it.
    With `owner` (a user id, 116) only that user's own agents; owner=None is the local terminal and sees all."""
    con = store.open_readonly(state_path)
    if con is None:
        return []
    try:
        if owner is None:
            rows = con.execute("SELECT * FROM agents ORDER BY name")
        else:
            rows = con.execute("SELECT * FROM agents WHERE owner_user_id = ? ORDER BY name", (owner,))
        return [view(r, at, offline_after) for r in rows]
    except sqlite3.OperationalError:
        return []      # a platform.db made before 116 that no command has opened yet: nobody owns anything in it
    finally:
        con.close()


clean_facts = common.clean_facts


class OwnerMismatch(Exception):
    """The agent already belongs to another user than the one this token was made for."""


def register(state_path, name, version, clock=time.time, facts=None, owner_user_id=None):
    """Record that the agent called now; the same name is the same agent, never a second row.

    A hello with facts replaces the facts stored for the agent (an account that was unset is then stored as unset);
    a call without facts (a beat of an older agent, a poll) leaves them as they were.

    owner_user_id is the user of the agent token (116). An agent without an owner takes the first one that comes; an agent that has
    another owner is not touched and OwnerMismatch is raised. A token without a user (None) may serve an agent
    nobody owns (an old deployment) but never one that has an owner: an unknown owner is refused (owner-binding)."""
    now = clock()
    facts = clean_facts(facts)
    con = store.connect_state(state_path)
    try:
        with con:
            row = con.execute("SELECT owner_user_id FROM agents WHERE name = ?", (name,)).fetchone()
            if row is not None and row["owner_user_id"] is not None and row["owner_user_id"] != owner_user_id:
                raise OwnerMismatch(name)
            con.execute("INSERT INTO agents (name, version, first_seen_at, last_seen_at) VALUES (?, ?, ?, ?) "
                        "ON CONFLICT(name) DO UPDATE SET version = COALESCE(excluded.version, agents.version), "
                        "last_seen_at = excluded.last_seen_at", (name, version, now, now))
            if owner_user_id is not None:
                con.execute("UPDATE agents SET owner_user_id = ? WHERE name = ? AND owner_user_id IS NULL", (owner_user_id, name))
            if facts is not None:
                con.execute("UPDATE agents SET slurm_account = ?, facts_json = ? WHERE name = ?",
                            (facts["slurm_account"], json.dumps(facts, sort_keys=True), name))
    finally:
        con.close()


def get_facts(state_path, name):
    """The facts an agent reported (see FACT_TEXT, FACT_FLAGS), or None when it never reported any. Read-only."""
    con = store.open_readonly(state_path)
    if con is None:
        return None
    try:
        row = con.execute("SELECT facts_json FROM agents WHERE name = ?", (name,)).fetchone()
    except sqlite3.OperationalError:
        return None
    finally:
        con.close()
    if row is None or not row["facts_json"]:
        return None
    return json.loads(row["facts_json"])


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

    def seen(row, name, version, facts=None):
        """Record the call. None when it was taken; the refusal (403, the shape of wrong_name) when the agent belongs to the user
        of another token (116)."""
        try:
            register(state_path, name, version, clock, facts=facts, owner_user_id=row.get("user_id"))
        except OwnerMismatch:
            return JSONResponse({"message": "This agent belongs to another user"}, status_code=403)
        return None

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
        refused = seen(row, name, version, body.get("facts"))
        if refused is not None:
            return refused
        return JSONResponse({"agent": name, "heartbeat_seconds": common.heartbeat_seconds(),
                             "poll_seconds": common.poll_seconds(), "instance": store.instance_id(state_path)})

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
        refused = seen(row, name, None)
        if refused is not None:
            return refused
        # an asyncio deadline loop on the real clock: other requests are served while this one waits
        end = time.monotonic() + common.poll_seconds()
        job = jobs.claim(state_path, name, clock, tokens_path)
        while job is None and time.monotonic() < end:
            await asyncio.sleep(min(0.5, max(0.0, end - time.monotonic())))
            if await request.is_disconnected():  # the agent is gone: not a contact, and no job is taken for it
                return JSONResponse({"job": None})
            if auth(request) is None:  # revoked while waiting
                return unauthorized()
            job = jobs.claim(state_path, name, clock, tokens_path)
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
        refused = seen(row, name, None)
        if refused is not None:
            return refused
        code, answer = jobs.take_result(state_path, name, job_id, body.get("state"), body.get("result"), clock,
                                        tokens_path=tokens_path, records_dir=Path(state_path).parent / "records")
        return JSONResponse(answer, status_code=code)

    return [
        Route("/agent/hello", hello, methods=["POST"]),
        Route("/agent/poll", poll, methods=["POST"]),
        Route("/agent/result/{jid}", result, methods=["POST"]),
    ]
