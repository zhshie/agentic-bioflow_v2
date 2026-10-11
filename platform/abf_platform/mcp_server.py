# Not the Seqera MCP server: it is hosted only and ends in Seqera's cloud; this one reads the local index, offers two read-only tools, and is built on the official Python mcp SDK.
"""Read-only MCP server: list_runs and get_run (specs/008-run-receiver, FR-007).

There is no tool that starts, cancels or deletes anything, and none that writes. Both tools
carry readOnlyHint, which is only a hint; the guarantee is that this module never opens the
index for writing (status.py opens it read-only).
"""
from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations

from . import status

_READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


def build_server(index_path):
    server = MCPServer(
        "abf-platform",
        instructions="Read-only view of Nextflow runs the platform has received. list_runs gives the newest runs "
                     "first; get_run gives one run with its processes and failed tasks.",
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

    return server


def run_stdio(index_path):
    build_server(index_path).run("stdio")


def run_http(index_path, host, port):
    build_server(index_path).run("streamable-http", host=host, port=port)
