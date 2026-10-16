# Nothing existing: the platform's own list of what it can do (read six things, queue a launch or a cancel after a human's yes); no library knows these rules, and this only calls the modules that already hold them.
"""The action layer (spec 009b, ADR 0006): one function per action.

Every entry of the platform (the MCP tools, later the web pages and the chat) calls these functions and nothing else.
The read actions are the bodies the MCP tools had. launch and cancel check who confirmed, then call confirm.py, which
writes the confirmation and the job in one transaction. Until the confirmation page (009c) the only channel is the
terminal: `confirmed_by` must be the object TERMINAL, which only abf_launch/cli.py uses, after terminal.ask answered yes.
Anything else is refused before a database is opened.
"""
import time

from .. import agents, compute_envs, confirm, jobs, status, store


class _Terminal:
    """The one kind of human confirmation there is today: a person typed y at the question on a terminal."""

    def __repr__(self):
        return "<abf_platform.actions.TERMINAL>"


TERMINAL = _Terminal()


def platform_path_for(index_path, platform_path=None):
    return platform_path or store.default_platform_path(index_path)


# ---- read ------------------------------------------------------------------------------------------------------------

def list_runs(index_path):
    return {"runs": status.list_runs(index_path, status.now())}


def get_run(index_path, run_id):
    view = status.get_run(index_path, run_id, status.now())
    if view is None:
        return {"found": False, "id": run_id,
                "message": "Run not found: %s (找不到這個 run)" % run_id}
    return view


def list_compute_envs(platform_path):
    return {"compute_envs": compute_envs.list_all(platform_path)}


def get_compute_env(platform_path, name):
    view = compute_envs.get(platform_path, name)
    if view is None:
        return {"found": False, "name": name,
                "message": "Compute environment not found: %s (找不到這個算力環境)" % name}
    return view


def list_agents(platform_path):
    return {"agents": agents.list_agents(platform_path, status.now())}


async def list_site_files(platform_path, compute_env, path):
    answer = {"compute_env": compute_env, "path": path}
    try:
        job_id = jobs.enqueue_listing(platform_path, compute_env, path, status.now)
    except jobs.JobRefused as e:
        answer.update(ok=False, message=str(e))
        return answer
    out = await jobs.wait_for_result(platform_path, job_id, status.now)
    result = out["result"]
    if out["state"] == "done" and result and result.get("ok"):
        answer.update(result)
        answer["path"] = result.get("path", path)
        return answer
    answer.update(ok=False, message=out["message"])
    if result and result.get("error"):
        answer["error"] = result["error"]
    return answer


# ---- write: only after a human's yes -------------------------------------------------------------------------------------

def _require_human(confirmed_by):
    if confirmed_by is not TERMINAL:
        raise jobs.JobRefused("no human confirmation channel")


def launch(state_path, ce_name, bundle, *, confirmed_by, clock=time.time, deadline_seconds=None, offline_after=None):
    """Queue a launch of exactly `bundle`. Returns (confirmation id, job id)."""
    _require_human(confirmed_by)
    return confirm.confirm_launch(state_path, ce_name, bundle, clock=clock, deadline_seconds=deadline_seconds,
                                  offline_after=offline_after)


def cancel(state_path, ce_name, bundle, *, confirmed_by, clock=time.time, deadline_seconds=None, offline_after=None):
    """Queue a cancel of exactly `bundle`. Returns (confirmation id, job id)."""
    _require_human(confirmed_by)
    return confirm.confirm_cancel(state_path, ce_name, bundle, clock=clock, deadline_seconds=deadline_seconds,
                                  offline_after=offline_after)
