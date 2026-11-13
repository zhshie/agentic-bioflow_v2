# Not the Seqera MCP server: it is hosted only and ends in Seqera's cloud; this one reads the local index and the compute environments, offers fifteen read-only tools, and is built on the official Python mcp SDK.
"""MCP server: fifteen read-only tools: list_runs, list_compute_envs, get_compute_env, list_agents,
list_site_files, list_used_pipelines, my_usage, run_outputs, read_run_file, read_task_log, and the five canvas reads find_module, describe_module,
list_pipelines, get_pipeline, get_validation; and nine tools that ask a person:
launch, launch_pipeline, cancel, forget, resume, relaunch, publish_figure, pack_figures, delete_figure.

get_run is the one query that is not marked read-only: for a lost run it queues one read of the site (ruling R2). The fifteen read tools carry readOnlyHint, which is only a hint; read-only here means two things:

  - toward runs: this module never writes the run index (status.py opens it read-only);
  - toward the site: list_site_files may put one read-only question (list a folder) in the job queue of
    platform.db and wait for the agent's answer; read_task_log does the same to read the end of one of three log
    files of a failed task; run_outputs(path) lists a folder below results and read_run_file reads one file of a run (text in pages, a binary
    file only as a download address). None of them can name a command or a job kind; the platform and the agent each check the path again.

launch and cancel (spec 009c) start nothing by themselves. Each builds what the terminal command builds, writes a pending request
and asks the person (the client's form, else a page they open, else their own reply in the chat). A second call with the request id and
user_confirmed=true only relays that reply: it is accepted for the same person, the same content and ten minutes (CHAT), and the answer
to a call says plainly whether a job exists. Everything they do is in abf_platform.actions.

resume and relaunch (spec 009e) are the same kind of tool, for a run that failed or was cancelled. relaunch takes only the name of the
run. resume may also carry params (only the keys to change) and extra_config (settings text); the pipeline, revision, samples and
environment are those of the first launch and cannot be said again.
"""
from typing import Annotated, Any

from mcp.server.mcpserver import Context, MCPServer
from mcp_types import ToolAnnotations
from pydantic import Field

import abf_platform.actions.catalogue as catalogue_actions
import abf_platform.actions.pipelines as pipeline_actions

from . import actions, guidance, http_auth

_READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
# get_run: asks no one's yes, but a lost run makes it queue one read of the site and write that job to platform.db (ruling R2), so not read-only
_QUERY = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
_WRITES = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)
_PUBLISH = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)   # publish_figure: same name replaces, so the same call twice leaves the same gallery
_STOPS = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False)
_DELETES = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False)   # delete_figure: the figure and its code and parameters go for good (after a person's yes)
_PACK = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False)   # pack_figures: the result is the set named, so the same call twice leaves the same package


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

    @server.tool(name="get_run", annotations=_QUERY,
                 description="One run by its id: status, times, task numbers, task numbers per process, and the "
                             "failed tasks with their exit code and error message (and workdir, the task's folder on the site, "
                             "when Nextflow reported it); a failed run also has failure_reason, "
                             "Nextflow's own words for why it failed, when it gave any. cancel_requested_at is there only when "
                             "a confirmed cancel of the run was sent; it is a fact about the request, not a status. "
                             "It also has su: the SU the run's finished tasks used and what that costs (an estimate from "
                             "Nextflow's task records; null with the reasons when a record lacks what the formula needs). "
                             "usd_approx in su is a rough conversion at the rate in the settings file. "
                             "A lost run (no word from Nextflow) triggers one read-only site query, to ask the scheduler what became of its head job.")
    def get_run(ctx: Context, run_id: str) -> dict:
        return actions.get_run(index_path, run_id, caller=_caller(ctx), platform_path=platform_path)

    @server.tool(name="list_compute_envs", annotations=_READ_ONLY,
                 description="List the compute environments: name, type, credential name, status, message, primary, "
                             "dates and config. A credential itself is never stored, only its name. Each one also has site_connection "
                             "{state, as_of, agent}: whether its agent last reported the shared connection to the site as open, closed or "
                             "unknown. It is the agent's own report as of as_of (not checked now); open means only the control channel is "
                             "there, it does not promise the next session will not hang.")
    def list_compute_envs(ctx: Context) -> dict:
        return actions.list_compute_envs(platform_path, caller=_caller(ctx))

    @server.tool(name="get_compute_env", annotations=_READ_ONLY,
                 description="One compute environment by its name, with its config.")
    def get_compute_env(ctx: Context, name: str) -> dict:
        return actions.get_compute_env(platform_path, name, caller=_caller(ctx))

    @server.tool(name="list_agents", annotations=_READ_ONLY,
                 description="List the agents that have connected: name, version, online or offline, and the time of "
                             "their last contact. Offline means no contact for three heartbeats. site_link (open, closed or unknown) and "
                             "site_link_at are the agent's own report of the shared connection to the site as of site_link_at, not checked "
                             "now; unknown when it is offline or never said. open means only the control channel is there, it does "
                             "not promise the next session will not hang.")
    def list_agents(ctx: Context) -> dict:
        return actions.list_agents(platform_path, caller=_caller(ctx))

    @server.tool(name="list_site_files", annotations=_READ_ONLY,
                 description="List one folder on the site through the agent of a compute environment: file names, "
                             "sizes and modification times (these go to the model you chose). The folder must be "
                             "inside the places the agent may read; at most 500 entries are shown and a cut is said "
                             "so. Nothing is written or run.")
    async def list_site_files(ctx: Context, compute_env: str, path: str) -> dict:
        return await actions.list_site_files(platform_path, compute_env, path, caller=_caller(ctx))

    @server.tool(name="list_used_pipelines", annotations=_READ_ONLY,
                 description="The pipelines you have run before, newest first (at most 20): one entry per pipeline and revision, "
                             "with the name of its latest run, when it was started and on which compute environment. "
                             "Only your own runs; a run whose content was forgotten is left out.")
    def list_used_pipelines(ctx: Context) -> dict:
        return actions.list_used_pipelines(platform_path, caller=_caller(ctx))
    @server.tool(name="my_usage", annotations=_READ_ONLY,
                 description="What you used in one month (month is YYYY-MM in Taipei time; this month by default): one entry per compute "
                             "environment you sent runs to, each in its own unit (SU for Slurm, US dollars for a cloud environment; "
                             "never converted or added across environments) with up to 50 of its analyses, and the cloud money with "
                             "the monthly cap the administrator set and what is left of it. A figure that cannot be worked out is "
                             "null, never 0. usd_approx is a rough conversion of the SU at the rate in the settings file.")
    def my_usage(ctx: Context, month: str | None = None) -> dict:
        return actions.my_usage(index_path, platform_path, caller=_caller(ctx), month=month)

    @server.tool(name="run_outputs", annotations=_READ_ONLY,
                 description="What one run of yours produced: the files and folders in <run folder>/results on the site, by the run's id. "
                             "Pass path (a folder below results, taken from the enter field of an earlier answer) to look inside it; a path "
                             "that is not valid lists the first level and says bad_path. Each file row carries enter (the path of a folder you "
                             "may open) and download (the path you may give read_run_file). "
                             "It never waits for the site: it answers state loading (a question was queued, ask again in a few seconds), "
                             "ready (files: name, type, size, modified, and listed_at), error (reason) or unavailable (the run was not "
                             "launched from the platform, so there is no output folder on record). Nothing is written or run.")
    def run_outputs(ctx: Context, run_id: str, path: str | None = None) -> dict:
        return actions.run_outputs(index_path, platform_path, run_id, caller=_caller(ctx), subpath=path)

    @server.tool(name="read_run_file", annotations=_READ_ONLY,
                 description="Read-only: read one file of your own run, by run_id and path (below results/, from run_outputs' "
                             "download). Never waits for the site: state is loading (ask again), ready, error (reason), "
                             "unavailable (not launched here, or results not on the site host) or too_large (over 25 MB: "
                             "size and full site path given, nothing read). Text comes back as at most 200,000 characters from "
                             "offset with total_chars and next_offset; the text goes to the model you chose. A binary file "
                             "is not sent: you get name, size and address /run/file?run=<id>&path=<p>. "
                             "An HTML file (.html, .htm) is treated as a binary file.")
    def read_run_file(ctx: Context, run_id: str, path: str, offset: Any = 0) -> dict:
        return actions.read_run_file(index_path, platform_path, run_id, path, caller=_caller(ctx), offset=offset)

    @server.tool(name="read_task_log", annotations=_READ_ONLY,
                 description="Read the end of one log file of a failed task of a run you launched, through the run's agent: "
                             "task is the name get_run shows in failed_tasks, which is err, out or log (.command.err, "
                             ".command.out, .command.log in the task's folder). At most the last 200 lines and 64 KB, and a "
                             "cut is said; the text goes to the model you chose. It is refused when the task has no recorded "
                             "workdir or the agent is offline, and it says which. Nothing is written or run.")
    async def read_task_log(ctx: Context, run_name: str, task: str, which: str) -> dict:
        return await actions.read_task_log(platform_path, index_path, run_name, task, which, caller=_caller(ctx))

    _add_canvas_reads(server, platform_path)
    _add_write_tools(server, platform_path, index_path)
    _add_guidance(server)
    return server


def _add_canvas_reads(server, platform_path):
    """The five reads of the canvas backend (module catalogue and the caller's own saved pipelines). All logic is in the actions;
    the owner rule is theirs, so each pipeline read passes the caller on."""

    @server.tool(name="find_module", annotations=_READ_ONLY,
                 description="Search the nf-core module catalogue by name, keyword or description (for example fastqc). Returns sha "
                             "(the catalogue snapshot), count and modules, each with name, path, description, inputs and outputs. "
                             "Nothing found gives an empty list and a hint. The catalogue is public; nothing is written.")
    def find_module(ctx: Context, q: str) -> dict:
        return catalogue_actions.find_module(q)

    @server.tool(name="describe_module", annotations=_READ_ONLY,
                 description="One nf-core module by its exact name: found, sha, inputs and outputs with their types. An unknown name "
                             "answers found false and says to use find_module. Nothing is written.")
    def describe_module(ctx: Context, name: str) -> dict:
        return catalogue_actions.describe_module(name)

    @server.tool(name="list_pipelines", annotations=_READ_ONLY,
                 description="Your own saved pipelines: id, name, newest version, number of nodes and dates. Other people's "
                             "pipelines are not shown. Nothing is written.")
    def list_pipelines(ctx: Context) -> dict:
        return pipeline_actions.list_pipelines(platform_path, caller=_caller(ctx))

    @server.tool(name="get_pipeline", annotations=_READ_ONLY,
                 description="One of your saved pipelines by its id, with the graph of a version (the newest when version is not "
                             "given). A pipeline that is not yours answers like one that does not exist. Nothing is written.")
    def get_pipeline(ctx: Context, pipeline_id: int, version: int | None = None) -> dict:
        return pipeline_actions.get_pipeline(platform_path, pipeline_id, version, caller=_caller(ctx))

    @server.tool(name="get_validation", annotations=_READ_ONLY,
                 description="The kept result of the latest check of one version of your pipeline (the newest version when version "
                             "is not given); validation is null when it was never checked, and stale says the module list changed "
                             "since. Nothing is checked again and nothing is written.")
    def get_validation(ctx: Context, pipeline_id: int, version: int | None = None) -> dict:
        return pipeline_actions.get_validation(platform_path, pipeline_id, version, caller=_caller(ctx))


_CHAT_SENTENCE = ("Or, when the person has answered yes in this chat in their own words after you showed them the summary, call it "
                  "again with the same arguments plus request_id (the id this returned) and user_confirmed=true; never set "
                  "user_confirmed before they answer.")
_REQUEST_ID_DOC = "The id of the pending request that the first call returned; only together with user_confirmed=true, after the person answered yes in the chat."
_DELETE_REQUEST_ID_DOC = "Has no effect on delete_figure: a deletion cannot be confirmed in the chat, only by the person on the confirmation page or in their own form."
_DELETE_USER_CONFIRMED_DOC = ("Has no effect on delete_figure: whatever the person said in the chat, a deletion is confirmed only on the confirmation page "
                              "or in their own form; do not set it.")
_USER_CONFIRMED_DOC = "True only after the person themselves answered yes in the chat to this request; never fill it in for them."


def _add_write_tools(server, platform_path, index_path):
    """launch, cancel, resume and relaunch: a pending request and a question to the person (and, with the request id and the person's
    own reply from the chat, the answer); forget: a question to the person. Nothing here says yes for anybody."""

    @server.tool(name="launch", annotations=_WRITES,
                 description="Ask to launch a Nextflow run on a compute environment (to continue a failed run: resume or "
                             "relaunch). This does NOT start anything: it returns a summary (sent false), a page address. The person "
                             "answers in their form, on that page or in the chat; you cannot answer for them. Then call "
                             "launch again with the same arguments (plus request_id and the flag, after they answer). Samples: samplesheet "
                             "(an uploaded CSV) or samplesheet_text (the CSV, at most 1 MiB). "
                             "Or name a dataset of yours (dataset, optionally dataset_version): its samplesheet is used. "
                             "Or none, with profiles such as [\"test\"]. 站台連線掉線時會被擋。")
    async def launch_tool(ctx: Context, pipeline: Annotated[str, Field(description="The pipeline to run: an nf-core name such as nf-core/rnaseq, or a pipeline the site already has. Use it with revision, which says which release or branch to run.")], revision: str, run_name: str, samplesheet: str | None = None,
                          samplesheet_text: str | None = None, ce_name: str | None = None,
                          params: Annotated[dict[str, Any] | None, Field(description="A flat mapping of pipeline parameters, e.g. {\"genome\": \"GRCh38\"}.")] = None,
                          path_columns: list[str] | None = None,
                          dataset: str | None = None, dataset_version: str | None = None,
                          profiles: Annotated[list[str] | None, Field(description="The pipeline's own Config profiles, e.g. [\"test\"]. "
                                                                      "With test, test_full or test_* no samplesheet is needed: the pipeline runs on its own test data "
                                                                      "(a pipeline installed on the site, Slurm only).")] = None,
                          request_id: Annotated[str | None, Field(description=_REQUEST_ID_DOC)] = None,
                          user_confirmed: Annotated[bool, Field(description=_USER_CONFIRMED_DOC)] = False) -> dict:
        return await actions.request_launch(platform_path, pipeline=pipeline, revision=revision, run_name=run_name,
                                            samplesheet=samplesheet, samplesheet_text=samplesheet_text, ce_name=ce_name, params=params,
                                            path_columns=path_columns, dataset=dataset, dataset_version=dataset_version, profiles=profiles,
                                            caller=_caller(ctx), person=actions.person_at(ctx),
                                            remote=_remote(ctx), request_id=request_id, user_confirmed=user_confirmed)

    @server.tool(name="launch_pipeline", annotations=_WRITES,
                 description="Ask to launch one of the person's own saved canvas pipelines: pipeline_id, version (newest when none), "
                             "run_name, optional ce_name and params (flat mapping). Samplesheet in one way only: samplesheet (path of "
                             "your uploaded CSV) or samplesheet_text (the CSV, at most 1 MiB). This does NOT start anything: it checks "
                             "the pipeline again, writes a request and returns a summary; you cannot say yes for the person. When "
                             "the answer says sent is false, tell them what to do, then call launch_pipeline again with the same "
                             "arguments to get the job number. 站台連線掉線時會被擋。")
    async def launch_pipeline_tool(ctx: Context, pipeline_id: int, run_name: str, version: int | None = None,
                                   samplesheet: str | None = None, samplesheet_text: str | None = None, ce_name: str | None = None,
                                   params: dict[str, Any] | None = None) -> dict:
        return await actions.request_pipeline_launch(platform_path, pipeline_id=pipeline_id, version=version, run_name=run_name,
                                                     samplesheet=samplesheet, samplesheet_text=samplesheet_text, ce_name=ce_name,
                                                     params=params, caller=_caller(ctx), person=actions.person_at(ctx),
                                                     remote=_remote(ctx))

    @server.tool(name="cancel", annotations=_STOPS,
                 description="Ask to stop one run that this platform launched. This does NOT stop anything: it writes a request and shows "
                             "the person which Slurm job would be cancelled. The person says yes in their own client's form or on the "
                             "page this returns; you cannot say it for them. After they pressed send, call cancel again "
                             "with the same run_name to get the job number. " + _CHAT_SENTENCE)
    async def cancel_tool(ctx: Context, run_name: str,
                          request_id: Annotated[str | None, Field(description=_REQUEST_ID_DOC)] = None,
                          user_confirmed: Annotated[bool, Field(description=_USER_CONFIRMED_DOC)] = False) -> dict:
        return await actions.request_cancel(platform_path, run_name=run_name, caller=_caller(ctx), person=actions.person_at(ctx),
                                            remote=_remote(ctx), request_id=request_id, user_confirmed=user_confirmed)

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
                 description="Ask to resume one failed or cancelled run in the same folder; finished tasks are reused. Optional params "
                             "(only keys to change) and extra_config (resource settings, e.g. "
                             "`process.memory = '16 GB'`); pipeline, version, samples and environment stay (to change them, "
                             "make a new launch). This only writes a request; it does not start anything until the person says "
                             "yes, in their own form or on the page this returns; you cannot say it for them. Then call resume again "
                             "with the same run_name for the job number, or, after they answered in this chat, with request_id and "
                             "user_confirmed=true. 站台連線掉線時會被擋。")
    async def resume_tool(ctx: Context, run_name: str, params: dict | None = None, extra_config: str | None = None,
                          request_id: Annotated[str | None, Field(description=_REQUEST_ID_DOC)] = None,
                          user_confirmed: Annotated[bool, Field(description=_USER_CONFIRMED_DOC)] = False) -> dict:
        return await actions.request_resume(platform_path, run_name=run_name, params=params, extra_config=extra_config,
                                            caller=_caller(ctx), person=actions.person_at(ctx), remote=_remote(ctx), index_path=index_path,
                                            request_id=request_id, user_confirmed=user_confirmed)

    @server.tool(name="relaunch", annotations=_WRITES,
                 description="Ask to start one failed or cancelled run again from the start, in a new folder: the same pipeline, samples and "
                             "parameters as the first launch, which cannot be changed here (a different analysis is a new launch). This "
                             "only writes a request and shows what would run; it does not start anything until the person says yes, in "
                             "their own form or on the page this returns; you cannot say it for them. Then call relaunch again with the "
                             "same run_name for the job number, or, after they answered in this chat, with request_id and "
                             "user_confirmed=true (never before they answer). 站台連線掉線時會被擋。")
    async def relaunch_tool(ctx: Context, run_name: str,
                            request_id: Annotated[str | None, Field(description=_REQUEST_ID_DOC)] = None,
                            user_confirmed: Annotated[bool, Field(description=_USER_CONFIRMED_DOC)] = False) -> dict:
        return await actions.request_relaunch(platform_path, run_name=run_name, caller=_caller(ctx), person=actions.person_at(ctx),
                                              remote=_remote(ctx), index_path=index_path, request_id=request_id,
                                              user_confirmed=user_confirmed)

    @server.tool(name="publish_figure", annotations=_PUBLISH,
                 description="Propose figures for the private gallery of one of your own runs (run_id). Each of figures has filename (letters, digits, "
                             ". _ -; png, svg, jpg or jpeg), content_base64, optional code, params (plain text) and caption (200 characters at "
                             "most). 10 per call, 5 MB together, 30 per run; same name replaces. Nothing is written until "
                             "the person says yes on the page this returns; you cannot say it for them: only after they answered in this chat "
                             "call again with request_id and user_confirmed=true. Not in the delivery package. SVG with scripts or "
                             "external links is refused.")
    async def publish_figure_tool(ctx: Context, run_id: str, figures: list[dict],
                                  request_id: Annotated[str | None, Field(description=_REQUEST_ID_DOC)] = None,
                                  user_confirmed: Annotated[bool, Field(description=_USER_CONFIRMED_DOC)] = False) -> dict:
        return await actions.request_publish_figure(platform_path, run_id=run_id, figures=figures, caller=_caller(ctx),
                                                    person=actions.person_at(ctx), remote=_remote(ctx), index_path=index_path,
                                                    request_id=request_id, user_confirmed=user_confirmed)

    @server.tool(name="pack_figures", annotations=_PACK,
                 description="Propose which figures of one of your own runs (run_id) are in the delivery package: names is the whole set to put in it, "
                             "exactly this set. Figures you do not list leave the package but stay in the gallery, they are not deleted and can be "
                             "packed again later; an empty list empties the package. Nothing changes until the person says yes on the page this "
                             "returns or in their own form; you cannot say it for them: only after they answered in this chat call again with "
                             "request_id and user_confirmed=true (never before they answer). If the gallery changed after the question, the "
                             "answer is refused and you propose again.")
    async def pack_figures_tool(ctx: Context, run_id: str, names: list[str],
                                request_id: Annotated[str | None, Field(description=_REQUEST_ID_DOC)] = None,
                                user_confirmed: Annotated[bool, Field(description=_USER_CONFIRMED_DOC)] = False) -> dict:
        return await actions.request_pack_figures(platform_path, run_id=run_id, names=names, caller=_caller(ctx), person=actions.person_at(ctx),
                                                  remote=_remote(ctx), index_path=index_path, request_id=request_id, user_confirmed=user_confirmed)

    @server.tool(name="delete_figure", annotations=_DELETES,
                 description="Propose deleting one figure (name, one figure at a time) of one of your own runs (run_id), together with its code and "
                             "parameter files; it also leaves the delivery package. The deletion is final. Nothing is deleted until the person says "
                             "yes on the confirmation page this returns or in their own form; you cannot say it for them, and an answer in this chat does "
                             "not count: request_id and user_confirmed have no effect on this tool, so ask the person to open the page and press confirm. "
                             "If the gallery changed after the question, the answer is refused and you propose again.")
    async def delete_figure_tool(ctx: Context, run_id: str, name: str,
                                 request_id: Annotated[str | None, Field(description=_DELETE_REQUEST_ID_DOC)] = None,
                                 user_confirmed: Annotated[bool, Field(description=_DELETE_USER_CONFIRMED_DOC)] = False) -> dict:
        return await actions.request_delete_figure(platform_path, run_id=run_id, name=name, caller=_caller(ctx), person=actions.person_at(ctx),
                                                   remote=_remote(ctx), index_path=index_path, request_id=request_id, user_confirmed=user_confirmed)


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
