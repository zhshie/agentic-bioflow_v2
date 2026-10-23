# Not the Seqera MCP server: it is hosted only and ends in Seqera's cloud; this one reads the local index and the compute environments, offers six read-only tools, and is built on the official Python mcp SDK.
"""MCP server: seven read-only tools, and the tools that ask a person: list_runs, get_run, list_compute_envs, get_compute_env,
list_agents, list_site_files, read_task_log, launch, cancel, resume, relaunch.

The seven read tools carry readOnlyHint, which is only a hint; read-only here means two things:

  - toward runs: this module never writes the run index (status.py opens it read-only);
  - toward the site: list_site_files may put one read-only question (list a folder) in the job queue of
    platform.db and wait for the agent's answer; read_task_log does the same to read the end of one of three log
    files of a failed task. Neither can name a command or a job kind; the platform and the agent each check the path again.

launch and cancel (spec 009c) start nothing by themselves. Each builds what the terminal command builds, writes a pending request
and asks the person (the client's form, else a page they open). They carry no argument that could say yes, and the answer to a call
says plainly whether a job exists. Everything they do is in abf_platform.actions.

resume and relaunch (spec 009e) are the same kind of tool, for a run that failed or was cancelled. Their one argument is the name of the
run: the pipeline, the samples and the parameters are those of its first launch and cannot be said again.
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
    def list_runs(ctx: Context) -> dict:
        return actions.list_runs(index_path, caller=_caller(ctx), platform_path=platform_path)

    @server.tool(name="get_run", annotations=_READ_ONLY,
                 description="One run by its id: status, times, task numbers, task numbers per process, and the "
                             "failed tasks with their exit code and error message (and workdir, the task's folder on the site, "
                             "when Nextflow reported it); a failed run also has failure_reason, "
                             "Nextflow's own words for why it failed, when it gave any. cancel_requested_at is there only when "
                             "a confirmed cancel of the run was sent; it is a fact about the request, not a status.")
    def get_run(ctx: Context, run_id: str) -> dict:
        return actions.get_run(index_path, run_id, caller=_caller(ctx), platform_path=platform_path)

    @server.tool(name="list_compute_envs", annotations=_READ_ONLY,
                 description="List the compute environments: name, type, credential name, status, message, primary, "
                             "dates and config. A credential itself is never stored, only its name.")
    def list_compute_envs(ctx: Context) -> dict:
        return actions.list_compute_envs(platform_path, caller=_caller(ctx))

    @server.tool(name="get_compute_env", annotations=_READ_ONLY,
                 description="One compute environment by its name, with its config.")
    def get_compute_env(ctx: Context, name: str) -> dict:
        return actions.get_compute_env(platform_path, name, caller=_caller(ctx))

    @server.tool(name="list_agents", annotations=_READ_ONLY,
                 description="List the agents that have connected: name, version, online or offline, and the time of "
                             "their last contact. Offline means no contact for three heartbeats.")
    def list_agents(ctx: Context) -> dict:
        return actions.list_agents(platform_path, caller=_caller(ctx))

    @server.tool(name="list_site_files", annotations=_READ_ONLY,
                 description="List one folder on the site through the agent of a compute environment: file names, "
                             "sizes and modification times (these go to the model you chose). The folder must be "
                             "inside the places the agent may read; at most 500 entries are shown and a cut is said "
                             "so. Nothing is written or run.")
    async def list_site_files(ctx: Context, compute_env: str, path: str) -> dict:
        return await actions.list_site_files(platform_path, compute_env, path, caller=_caller(ctx))

    @server.tool(name="read_task_log", annotations=_READ_ONLY,
                 description="Read the end of one log file of a failed task of a run you launched, through the run's agent: "
                             "task is the name get_run shows in failed_tasks, which is err, out or log (.command.err, "
                             ".command.out, .command.log in the task's folder). At most the last 200 lines and 64 KB, and a "
                             "cut is said; the text goes to the model you chose. It is refused when the task has no recorded "
                             "workdir or the agent is offline, and it says which. Nothing is written or run.")
    async def read_task_log(ctx: Context, run_name: str, task: str, which: str) -> dict:
        return await actions.read_task_log(platform_path, index_path, run_name, task, which, caller=_caller(ctx))

    _add_write_tools(server, platform_path, index_path)
    _add_guidance(server)
    return server


def _add_write_tools(server, platform_path, index_path):
    """launch, cancel, resume and relaunch: a pending request and a question to the person; forget: a question to the person.
    Nothing here says yes for anybody."""

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
                                            caller=_caller(ctx), person=actions.person_at(ctx),
                                            remote=_remote(ctx))

    @server.tool(name="cancel", annotations=_STOPS,
                 description="Ask to stop one run that this platform launched. This does NOT stop anything: it writes a request and shows "
                             "the person which Slurm job would be cancelled. The person says yes in their own client's form or on a "
                             "page whose address this returns; you cannot say it for them. After they pressed send, call cancel again "
                             "with the same run_name to get the job number.")
    async def cancel_tool(ctx: Context, run_name: str) -> dict:
        return await actions.request_cancel(platform_path, run_name=run_name, caller=_caller(ctx), person=actions.person_at(ctx),
                                            remote=_remote(ctx))

    @server.tool(name="forget", annotations=_STOPS,
                 description="Ask to delete what was kept of one run you launched: the bundle and the screen text of its requests and "
                             "jobs. This does NOT delete anything by itself: the person is asked in their own client's form, and you "
                             "cannot answer it for them. It cannot be undone, and the run can no longer be resumed or launched again "
                             "as it was; the record of who sent it and when stays. Only for a run that has finished (not running, "
                             "not lost). A client that cannot show a form is told to use the terminal command "
                             "`abf-platform forget RUN`.")
    async def forget_tool(ctx: Context, run_name: str) -> dict:
        return await actions.request_forget(platform_path, index_path, run_name=run_name, caller=_caller(ctx),
                                            person=actions.person_at(ctx))


    @server.tool(name="resume", annotations=_WRITES,
                 description="Ask to resume one run of this platform that failed or was cancelled: the same folder, and Nextflow takes up where "
                             "it stopped and reuses the tasks that finished; the pipeline, samples and parameters are those of the first launch "
                             "and cannot be changed here (a different analysis is a new launch). This does NOT start anything: it writes a "
                             "request and shows the person what would run. The person says yes in their own client's form or on a page whose "
                             "address this returns; you cannot say it for them. It does not start anything until the person says yes. After "
                             "they pressed send, call resume again with the same run_name to get the job number.")
    async def resume_tool(ctx: Context, run_name: str) -> dict:
        return await actions.request_resume(platform_path, run_name=run_name, caller=_caller(ctx), person=actions.person_at(ctx),
                                            remote=_remote(ctx), index_path=index_path)

    @server.tool(name="relaunch", annotations=_WRITES,
                 description="Ask to start one run of this platform that failed or was cancelled again from the start, in a new folder: the same "
                             "pipeline, samples and parameters as the first launch, which cannot be changed here (a different analysis is a "
                             "new launch). This does NOT start anything: it writes a request and shows the person what would run. The person "
                             "says yes in their own client's form or on a page whose address this returns; you cannot say it for them. It "
                             "does not start anything until the person says yes. After they pressed send, call relaunch again with the same "
                             "run_name to get the job number.")
    async def relaunch_tool(ctx: Context, run_name: str) -> dict:
        return await actions.request_relaunch(platform_path, run_name=run_name, caller=_caller(ctx), person=actions.person_at(ctx),
                                              remote=_remote(ctx), index_path=index_path)


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


def _request_scope(ctx):
    """The scope of the HTTP request this very tool call came in with, or None (local stdio, or a client in the same process)."""
    try:
        request = ctx.request_context.request
    except Exception:
        return None
    return getattr(request, "scope", None)


def _caller(ctx):
    """Who is calling this tool: the user of this call's own HTTP request (never one remembered from the request that opened the
    session), or None for local stdio."""
    scope = _request_scope(ctx)
    if scope is not None:
        return scope.get("abf_caller")
    return http_auth.current_caller()


def _remote(ctx):
    """Whether this call came from beyond the platform's machine."""
    scope = _request_scope(ctx)
    if scope is not None:
        return bool(scope.get("abf_remote"))
    return http_auth.current_remote()


def _transport_security(public_url):
    """The DNS-rebinding guard the mcp library would switch on for a loopback host, plus the public address when there is one
    (otherwise a tunnel's host name is refused with 421). None without `public_url`: the library's own default stays."""
    if not public_url:
        return None
    from urllib.parse import urlsplit

    from mcp.server.transport_security import TransportSecuritySettings

    u = urlsplit(public_url)
    hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    origins = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
    if u.hostname:
        netloc = u.netloc.rpartition("@")[2]
        hosts += [u.hostname if ":" not in u.hostname else "[%s]" % u.hostname, netloc]
        origins.append("%s://%s" % (u.scheme, netloc))
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=list(dict.fromkeys(hosts)),
                                     allowed_origins=origins)


def build_http_app(index_path, tokens_path=None, host="127.0.0.1", public_url=None):
    """The server's Streamable HTTP app behind the bearer check: no valid personal access token or OAuth access token, no answer.
    `public_url` is the address people reach this server at; with it the 401 points a connector to the resource metadata (009i)."""
    app = build_server(index_path).streamable_http_app(host=host, transport_security=_transport_security(public_url))
    return http_auth.BearerAuth(app, http_auth.tokens_path_for(index_path, tokens_path),
                                platform_path=actions.platform_path_for(index_path), public_url=public_url)


def run_http(index_path, host, port, public_url=None):
    import uvicorn

    uvicorn.run(build_http_app(index_path, host=host, public_url=public_url), host=host, port=port, log_level="info")
