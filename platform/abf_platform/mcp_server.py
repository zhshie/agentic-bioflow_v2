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

from . import actions, guidance

_READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


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
        return actions.list_runs(index_path)

    @server.tool(name="get_run", annotations=_READ_ONLY,
                 description="One run by its id: status, times, task numbers, task numbers per process, and the "
                             "failed tasks with their exit code and error message; a failed run also has failure_reason, "
                             "Nextflow's own words for why it failed, when it gave any.")
    def get_run(run_id: str) -> dict:
        return actions.get_run(index_path, run_id)

    @server.tool(name="list_compute_envs", annotations=_READ_ONLY,
                 description="List the compute environments: name, type, credential name, status, message, primary, "
                             "dates and config. A credential itself is never stored, only its name.")
    def list_compute_envs() -> dict:
        return actions.list_compute_envs(platform_path)

    @server.tool(name="get_compute_env", annotations=_READ_ONLY,
                 description="One compute environment by its name, with its config.")
    def get_compute_env(name: str) -> dict:
        return actions.get_compute_env(platform_path, name)

    @server.tool(name="list_agents", annotations=_READ_ONLY,
                 description="List the agents that have connected: name, version, online or offline, and the time of "
                             "their last contact. Offline means no contact for three heartbeats.")
    def list_agents() -> dict:
        return actions.list_agents(platform_path)

    @server.tool(name="list_site_files", annotations=_READ_ONLY,
                 description="List one folder on the site through the agent of a compute environment: file names, "
                             "sizes and modification times (these go to the model you chose). The folder must be "
                             "inside the places the agent may read; at most 500 entries are shown and a cut is said "
                             "so. Nothing is written or run.")
    async def list_site_files(compute_env: str, path: str) -> dict:
        return await actions.list_site_files(platform_path, compute_env, path)

    _add_guidance(server)
    return server


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


def run_http(index_path, host, port):
    build_server(index_path).run("streamable-http", host=host, port=port)
