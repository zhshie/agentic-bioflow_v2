# Not the Seqera MCP server: it is hosted only and ends in Seqera's cloud; this one reads the local index and the compute environments, offers six read-only tools, and is built on the official Python mcp SDK.
"""MCP server: six read-only tools, and the two tools that ask a person: list_runs, get_run, list_compute_envs, get_compute_env,
list_agents, list_site_files, launch, cancel.

The six read tools carry readOnlyHint, which is only a hint; read-only here means two things:

  - toward runs: this module never writes the run index (status.py opens it read-only);
  - toward the site: list_site_files may put one read-only question (list a folder) in the job queue of
    platform.db and wait for the agent's answer. It cannot name a command or a job kind; the platform and
    the agent each check the path again.

launch and cancel (spec 009c) start nothing by themselves. Each builds what the terminal command builds, writes a pending request
and asks the person (the client's form, else a page they open). They carry no argument that could say yes, and the answer to a call
says plainly whether a job exists. Everything they do is in abf_platform.actions.
"""
from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp_types import ToolAnnotations

from . import actions, guidance, http_auth

_READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
_WRITES = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)
_STOPS = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False)


def build_server(index_path, platform_path=None):
    platform_path = actions.platform_path_for(index_path, platform_path)
    server = MCPServer(
        "abf-platform",
        instructions=guidance.routing_instructions(),
    )

    @server.tool(name="list_runs", annotations=_READ_ONLY,
                 description="List the Nextflow runs the platform knows, newest first, each with its name, status "
                             "(running, succeeded, failed or lost), start time and task numbers.")
    def list_runs() -> dict:
        return actions.list_runs(index_path, caller=_caller())

    @server.tool(name="get_run", annotations=_READ_ONLY,
                 description="One run by its id: status, times, task numbers, task numbers per process, and the "
                             "failed tasks with their exit code and error message; a failed run also has failure_reason, "
                             "Nextflow's own words for why it failed, when it gave any.")
    def get_run(run_id: str) -> dict:
        return actions.get_run(index_path, run_id, caller=_caller())

    @server.tool(name="list_compute_envs", annotations=_READ_ONLY,
                 description="List the compute environments: name, type, credential name, status, message, primary, "
                             "dates and config. A credential itself is never stored, only its name.")
    def list_compute_envs() -> dict:
        return actions.list_compute_envs(platform_path, caller=_caller())

    @server.tool(name="get_compute_env", annotations=_READ_ONLY,
                 description="One compute environment by its name, with its config.")
    def get_compute_env(name: str) -> dict:
        return actions.get_compute_env(platform_path, name, caller=_caller())

    @server.tool(name="list_agents", annotations=_READ_ONLY,
                 description="List the agents that have connected: name, version, online or offline, and the time of "
                             "their last contact. Offline means no contact for three heartbeats.")
    def list_agents() -> dict:
        return actions.list_agents(platform_path, caller=_caller())

    @server.tool(name="list_site_files", annotations=_READ_ONLY,
                 description="List one folder on the site through the agent of a compute environment: file names, "
                             "sizes and modification times (these go to the model you chose). The folder must be "
                             "inside the places the agent may read; at most 500 entries are shown and a cut is said "
                             "so. Nothing is written or run.")
    async def list_site_files(compute_env: str, path: str) -> dict:
        return await actions.list_site_files(platform_path, compute_env, path, caller=_caller())

    _add_write_tools(server, platform_path)
    _add_guidance(server)
    return server


def _add_write_tools(server, platform_path):
    """launch and cancel: a pending request and a question to the person. Nothing here says yes for anybody."""

    @server.tool(name="launch", annotations=_WRITES,
                 description="Ask to launch a Nextflow pipeline on a compute environment. This does NOT start anything: it builds the "
                             "same analysis the terminal command builds, writes a request and shows the person a summary (pipeline, "
                             "samples, where it runs, where the results go). The person says yes in their own client's form or on "
                             "a page whose address this returns; you cannot say it for them. When the answer says sent is false, "
                             "tell the person what to do and, after they have pressed send, call launch again with the same arguments "
                             "to get the job number. samplesheet is the path of a CSV file; params is a flat mapping of pipeline "
                             "parameters.")
    async def launch_tool(ctx: Context, pipeline: str, revision: str, run_name: str, samplesheet: str, ce_name: str | None = None,
                          params: dict[str, Any] | None = None, path_columns: list[str] | None = None) -> dict:
        return await actions.request_launch(platform_path, pipeline=pipeline, revision=revision, run_name=run_name,
                                            samplesheet=samplesheet, ce_name=ce_name, params=params, path_columns=path_columns,
                                            caller=_caller(), person=actions.person_at(ctx))

    @server.tool(name="cancel", annotations=_STOPS,
                 description="Ask to stop one run that this platform launched. This does NOT stop anything: it writes a request and shows "
                             "the person which Slurm job would be cancelled. The person says yes in their own client's form or on a "
                             "page whose address this returns; you cannot say it for them. After they pressed send, call cancel again "
                             "with the same run_name to get the job number.")
    async def cancel_tool(ctx: Context, run_name: str) -> dict:
        return await actions.request_cancel(platform_path, run_name=run_name, caller=_caller(), person=actions.person_at(ctx))


def _whole_file(name):
    return lambda: guidance.read_skill(name)


def _body_of(text):
    return lambda: text


def _add_guidance(server):
    """The skills of skills/ as one prompt per flow and one fixed resource per file (spec 009g). Nothing here takes an argument."""
    for name, doc in guidance.load_skills().items():
        server.resource("skill://%s/SKILL.md" % name, name="skill-" + name, description=doc.description,
                        mime_type="text/markdown")(_whole_file(name))
        if name != "operational":
            server.prompt(name=name, description=doc.description)(_body_of(doc.body_text))


def run_stdio(index_path):
    build_server(index_path).run("stdio")


def _caller():
    """Who is calling this tool: the user of the HTTP request, or None for local stdio."""
    return http_auth.current_caller()


def build_http_app(index_path, tokens_path=None, host="127.0.0.1"):
    """The server's Streamable HTTP app behind the bearer check: no valid personal access token, no answer."""
    app = build_server(index_path).streamable_http_app(host=host)
    return http_auth.BearerAuth(app, http_auth.tokens_path_for(index_path, tokens_path))


def run_http(index_path, host, port):
    import uvicorn

    uvicorn.run(build_http_app(index_path, host=host), host=host, port=port, log_level="info")
