# Not the Seqera MCP server: it is hosted only and ends in Seqera's cloud; this one reads the local index and the compute environments, offers six read-only tools, and is built on the official Python mcp SDK.
"""Read-only MCP server: list_runs, get_run, list_compute_envs, get_compute_env, list_agents, list_site_files.

There is no tool that starts, cancels or deletes anything, and none that writes a run or a compute
environment. All tools carry readOnlyHint, which is only a hint; read-only here means two things:

  - toward runs: this module never writes the run index (status.py opens it read-only);
  - toward the site: list_site_files may put one read-only question (list a folder) in the job queue of
    platform.db and wait for the agent's answer. It cannot name a command or a job kind; the platform and
    the agent each check the path again.
"""
from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations

from . import agents, compute_envs, jobs, status, store

_READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


def build_server(index_path, platform_path=None):
    platform_path = platform_path or store.default_platform_path(index_path)
    server = MCPServer(
        "abf-platform",
        instructions="Read-only view of Nextflow runs, compute environments and agents. list_runs gives the newest "
                     "runs first; get_run gives one run with its processes and failed tasks. list_compute_envs and "
                     "get_compute_env show the compute environments; list_agents shows whether each agent is online; "
                     "list_site_files lists one folder on the site through an agent (names, sizes and modification "
                     "times, which go to the model you chose).",
    )

    @server.tool(name="list_runs", annotations=_READ_ONLY,
                 description="List the Nextflow runs the platform knows, newest first, each with its name, status "
                             "(running, succeeded, failed or lost), start time and task numbers.")
    def list_runs() -> dict:
        return {"runs": status.list_runs(index_path, status.now())}

    @server.tool(name="get_run", annotations=_READ_ONLY,
                 description="One run by its id: status, times, task numbers, task numbers per process, and the "
                             "failed tasks with their exit code and error message.")
    def get_run(run_id: str) -> dict:
        view = status.get_run(index_path, run_id, status.now())
        if view is None:
            return {"found": False, "id": run_id,
                    "message": "Run not found: %s (找不到這個 run)" % run_id}
        return view

    @server.tool(name="list_compute_envs", annotations=_READ_ONLY,
                 description="List the compute environments: name, type, credential name, status, message, primary, "
                             "dates and config. A credential itself is never stored, only its name.")
    def list_compute_envs() -> dict:
        return {"compute_envs": compute_envs.list_all(platform_path)}

    @server.tool(name="get_compute_env", annotations=_READ_ONLY,
                 description="One compute environment by its name, with its config.")
    def get_compute_env(name: str) -> dict:
        view = compute_envs.get(platform_path, name)
        if view is None:
            return {"found": False, "name": name,
                    "message": "Compute environment not found: %s (找不到這個算力環境)" % name}
        return view

    @server.tool(name="list_agents", annotations=_READ_ONLY,
                 description="List the agents that have connected: name, version, online or offline, and the time of "
                             "their last contact. Offline means no contact for three heartbeats.")
    def list_agents() -> dict:
        return {"agents": agents.list_agents(platform_path, status.now())}

    @server.tool(name="list_site_files", annotations=_READ_ONLY,
                 description="List one folder on the site through the agent of a compute environment: file names, "
                             "sizes and modification times (these go to the model you chose). The folder must be "
                             "inside the places the agent may read; at most 500 entries are shown and a cut is said "
                             "so. Nothing is written or run.")
    async def list_site_files(compute_env: str, path: str) -> dict:
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

    return server


def run_stdio(index_path):
    build_server(index_path).run("stdio")


def run_http(index_path, host, port):
    build_server(index_path).run("streamable-http", host=host, port=port)
