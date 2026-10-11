# Research: 008-run-receiver (2026-10-11)

Constitution principle 1 asks what already exists for the same job, and whether it is reused.

| Item | Finding | Decision | Source |
|---|---|---|---|
| Tower trace API | Five trace endpoints: `POST /trace/create`, `PUT /trace/{id}/begin`, `/progress`, `/heartbeat` and `/complete`, plus an optional `?workspaceId=`. The token comes from `tower.accessToken` or `TOWER_ACCESS_TOKEN`; a JWT or personal access token is sent as Bearer, anything else as Basic `@token:`. `TowerFactory` only rejects an endpoint ending in `/`, and there is no service-info check. `create` doubles as the auth check, and its response must carry `workflowId`. | Write our own thin receiver. The plugin source is the specification. | https://raw.githubusercontent.com/nextflow-io/nextflow/master/plugins/nf-tower/src/main/io/seqera/tower/plugin/TowerClient.groovy , TowerObserver.groovy |
| seqeralabs/nf-tower (CE) | Archived 2025-01-30. MPL-2.0. A full Java backend plus web app that needs SMTP, Docker and a database. | Not used: heavy, unmaintained, and a second language stack. | https://github.com/seqeralabs/nf-tower |
| AugustDev/nf-shard | MIT. Next.js/TypeScript with Postgres and Prisma. Accepts any non-empty token. Last push 2024-09. | Reference only, for payload handling. Not used because it has no auth, is stale, and is TypeScript with Postgres. | https://github.com/AugustDev/nf-shard |
| MCP SDK | Python `mcp` 2.3.0 (Python 3.10+, MIT), supports Streamable HTTP and stdio. TS SDK v2 is also stable. Standalone FastMCP is at 4.1.0. | Official Python `mcp` 2.x. One language across the receiver, the MCP server and the future station agent. | https://pypi.org/pypi/mcp/json |
| Elicitation (human confirmation) | Client support is inconsistent: Claude Code yes, Claude Desktop unconfirmed, Cursor buggy. | Not relied on. Write tools (a later feature) confirm on the platform's own page. | https://modelcontextprotocol.io/specification/draft/client/elicitation |
| Tool annotations | `readOnlyHint` and `destructiveHint` are hints only. | Set them anyway. | MCP spec |
| Existing MCP for Nextflow | Seqera MCP is hosted only, with no repository. wjlim/nf-core_mcp is a community TypeScript server whose licence is unconfirmed. | Neither is used. Seqera's tool list serves as a design reference only, read from public documentation. | https://docs.seqera.io/platform-cloud/seqera-mcp/ |

Not yet extracted, for the executor to read from the pinned Nextflow version's source before coding:

- the exact `TraceRecord` and `progress` field lists;
- the heartbeat interval;
- the literal `Authorization` header.

## Source facts, read by the executor on 2026-10-11 (plan Revision 2, M4 and M5)

### Pinned versions and checksums

Everything below was downloaded once and hashed. `platform/tests/pins.env` holds the same values and `tests/platform_test.sh` verifies them on every run.

| Item | Version | sha256 | Where it comes from |
|---|---|---|---|
| Nextflow launcher script (`nextflow`) | 26.04.7 (latest stable on 2026-10-11, runs on Java 17) | `fc94fec557e3f78c870b0f92d6c6a30b9706c5e589427f31dc2bc6db0cb3d5b7` | https://github.com/nextflow-io/nextflow/releases/download/v26.04.7/nextflow |
| Nextflow distribution jar (`nextflow-26.04.7-dist`) | 26.04.7 | `d1fc6db677dd40d79ff911c7dddad28edec4905707529c5c5001445085dbcf1b` | https://github.com/nextflow-io/nextflow/releases/download/v26.04.7/nextflow-26.04.7-dist |
| `nf-tower` plugin zip | 1.28.3 (the version 26.04.7 bundles) | `1f2fec2f3e480888f82c1e1eee9d0e1bd6dac36be89c46dd6feac0aa3c73fe2b` | https://registry.nextflow.io/api/v1/plugins/nf-tower/1.28.3/download/nf-tower-1.28.3.zip |

- The two Nextflow checksums match the `digest` that the GitHub release API reports for these assets.
- The plugin registry also lists a sha512 for the zip; its first 24 hex characters, `e9e50fe015a991b8741c3133`, match the zip we hashed.
- The run uses `NXF_HOME` in the cache folder. The jar sits in `framework/26.04.7/`, and the plugin zip is unpacked by us into `plugins/nf-tower-1.28.3/`.
- The run sets `NXF_OFFLINE=true`. A real run was made this way and its log shows no registry request and no download, so Nextflow never fetches anything unverified.
- Source read: the `v26.04.7` tag of `nextflow-io/nextflow`, folder `plugins/nf-tower/src/main/io/seqera/tower/plugin/` (called `…/plugin/` below).

### Heartbeat interval (H)

- `…/plugin/TowerObserver.groovy:60`: `ALIVE_INTERVAL = Duration.of('1 min')`, so H = 60 seconds.
- `…/TowerObserver.groovy:58`: `REQUEST_INTERVAL = 1 sec`.
- `…/TowerObserver.groovy:564-608`, the sender thread:
  - Task events are collected and sent as one `progress` request at most once per second.
  - A `heartbeat` is sent only when there is nothing to send and more than the alive interval has passed since the last message (lines 590-596).
- So a quiet run sends one message a minute. The platform treats a run as lost after 3 H = 180 seconds without any message and without `complete` (FR-006).
- A real heartbeat was recorded: `platform/tests/fixtures/payloads/heartbeat_run.json`.

### Requests, their fields and the response Nextflow needs

- URLs are in `…/TowerClient.groovy:181-214`. All end in an optional `?workspaceId=`.
  - `POST /trace/create`
  - `PUT /trace/{id}/begin`
  - `PUT /trace/{id}/progress`
  - `PUT /trace/{id}/heartbeat`
  - `PUT /trace/{id}/complete`
- Responses, and what a failure does:
  - A non-2xx response to `create` or `begin` raises `AbortRunException` (`TowerClient.groovy:167-179`).
  - A non-2xx response to `progress` also aborts the run (`:141-153`).
  - A non-2xx response to `heartbeat` or `complete` only logs a warning (`:129-139`, `:378-394`).
  - A 401 is turned into the message "Unauthorized Seqera Platform API access" (`:293-296`).
- `create` request, built at `TowerObserver.groovy:222-232`: `sessionId`, `runName`, `projectName`, `repository`, `workflowId` (null unless launched by Platform), `instant`.
  - The response must carry `workflowId`, or the run stops (`TowerObserver.groovy:159-161`).
  - It may carry `watchUrl`, `message` and `metadata`; all are optional (`:162-171`).
- `begin` request, built at `:380-400`: `workflow{...}`, `processNames`, `towerLaunch`, `instant`.
  - `workflow` is `WorkflowMetadata.toMap()` plus `params`, `configText`, `container`, `operationId`, `logFile`, `outFile`.
  - Fields we use: `runName`, `sessionId`, `start`, `projectName`, `nextflow.version`.
  - Fields we never store: `configText`, `commandLine`, `params` values with secret-looking names, `env`, `homeDir`, `userName` (FR-008).
- `progress` request, built at `:515-528`: `tasks[]`, `progress`, `containers`, `instant`.
  - Each task is a `TraceRecord` (`modules/nextflow/src/main/groovy/nextflow/trace/TraceRecord.groovy:65-110`) turned into camelCase (`TowerObserver.groovy:475-505`).
  - Task fields we use: `taskId`, `attempt`, `name`, `process`, `status`, `exit`, `hash`.
  - `exit` is 2147483647 until the task has ended.
  - Only the last state of a task is sent per batch (`:572-578`).
- `progress` object is `WorkflowProgress` (`…/WorkflowProgress.groovy:30-67`): `succeeded`, `failed`, `ignored`, `cached`, `pending`, `submitted`, `running`, `retries`, `aborted`, `loadCpus`, `loadMemory`, `peakRunning`, `peakCpus`, `peakMemory` and `processes[]`.
  - Each `processes[]` entry (`ProgressRecord`) has `index`, `name`, `hash`, `workDir`, `taskName`, `pending`, `submitted`, `running`, `succeeded`, `cached`, `failed`, `aborted`, `stored`, `ignored`, `retries`, `terminated`, `errored` and the load/peak numbers.
- `heartbeat` request, built at `:426-431`: `{progress, instant}`.
- `complete` request, built at `:402-424`: `workflow{...}` with `success`, `exitStatus`, `complete`, `duration`, `errorMessage`, `errorReport`, plus `metrics`, `progress`, `instant`.
  - `errorMessage` is cut to 255 characters by the tower schema (`tower-schema.properties`: `workflow.errorMessage = 255`).
  - `errorReport` is not cut and holds the whole "Error executing process" text.
- Nobody calls `GET /user-info` in an ordinary run of this version (`TowerClient.groovy:489-492` only serves the optional Platform commands). It exists in FR-001 for the other plugin paths.

### The literal Authorization header

- `…/TowerClient.groovy:236-268`, `setupClientAuth`:
  - A token with two dots is sent as `Bearer`.
  - A token that base64-decodes to JSON before its first dot is also sent as `Bearer`.
  - Anything else becomes `config.basicAuth('@token:' + token)` (line 50 defines `TOKEN_PREFIX = '@token:'`, line 267 uses it).
- So the real header is `Authorization: Basic base64("@token:" + token)`: user name `@token`, password = the token.
- The recorded request carried `Basic QHRva2VuOmNhcHR1cmV0b2tlbjEyMw==`, which decodes to `@token:capturetoken123`.
- Platform tokens are `abf_` plus 43 URL-safe characters, with no dot, so Nextflow always sends them as Basic. The receiver also accepts `Bearer <token>`.
- Other request headers (`TowerClient.groovy:348-373`): `User-Agent: Nextflow/<version>`, `Traceparent`, `Content-Type: application/json; charset=utf-8`.

### Recorded payloads

- `platform/tests/fixtures/payloads/`, one file per scenario; the header of each file names both versions and what was replaced:
  - `ok_run.json`
  - `ok_resume.json`
  - `fail_run.json`
  - `slow_run.json`
  - `heartbeat_run.json`
- They were recorded from real Nextflow 26.04.7 runs of the fixture pipelines against a throwaway capture server on 127.0.0.1. Nothing left the machine.
- The recording replaced the OS user name, host name, home, launch and checkout paths, and every `/work/` path segment, so that the files carry no personal path.

### What Nextflow leaves in a launch folder (used by `rebuild`)

- `.nextflow/history`: one tab-separated line per run, in this order:
  - start time `YYYY-MM-DD HH:MM:SS` (local time)
  - duration
  - run name
  - status: `OK`, `ERR`, or `-` when the run never finished
  - script hash
  - session ID
  - the command line (never stored)
- The start second is close to, but not always the same as, the whole-second part of `workflow.start` in the `begin` payload (see "Time resolution" below).
- `.nextflow.log`, `.nextflow.log.1`, …: Nextflow rotates one log per run.
  - Line prefix `Oct-11 11:04:02.315`: no year, local time.
  - `Session UUID: <id>` and `Run name: <name>` identify the run (`nextflow.Session` DEBUG lines).
  - `TraceFileObserver - Workflow started -- trace file: <name>` names the trace file.
  - A finished run ends with `Execution complete -- Goodbye`.
  - A process failure is logged as `Error executing process > '<task>'` followed by the same text as `errorReport`.
- `-with-trace` file `trace-<date>-<n>.txt`: tab-separated, header `task_id hash native_id name status exit submit duration realtime …`. One row per task attempt; a `-resume` run has `CACHED` rows.

### Counting rule

It is applied identically to live events and to a rebuild.

- total = number of trace rows.
- succeeded = rows with status `COMPLETED`.
- cached = rows with status `CACHED`. They are shown on their own and are not counted in succeeded.
- failed = rows with status `FAILED`.
- aborted = rows with status `ABORTED`.
- A retried task counts once per attempt row, exactly as the trace has it.
- Live, the same numbers come from the `progress` object of the latest `progress`, `heartbeat` or `complete` request. Its counters are cumulative, and a retry shows up in `failed`. total is the sum of succeeded, cached, failed, aborted, running, submitted and pending.
- Per process, the same counters are taken from `processes[]`. In a rebuild the process of a trace row is its task name up to the first space (process names have no space).

### Failed-task message: one extractor for the live path and the rebuild

- Both sources contain Nextflow's own text: `workflow.errorReport` in the `complete` request, and the `Error executing process > '<task>'` block in `.nextflow.log`.
- One function (`abf_platform.common.extract_error`) reads such text and returns the task name and the lines of its `Command error:` section, up to the blank line before `Work dir:`, with the indentation removed. If the section is missing, it returns the `Caused by:` line instead.
- Only the process that ended the run carries a message, in both paths.

### Time resolution and the places where the two paths can differ

- Start and end times are stored in whole seconds (UTC, shown as ISO 8601 with `Z`).
- Neither time has one source that both paths can read, because Nextflow samples its clock several times and writes each sample in a different place:
  - Start. The live path takes `workflow.start` from the `begin` request. The rebuild takes the start second of `.nextflow/history`. In a real run, `workflow.start` was 11:04:02.315, the log line `Run name:` was 11:04:02.058 and the history second was 11:04:02. These samples are a few hundred milliseconds apart, so when a run starts close to a second boundary the two seconds differ by one.
  - End. The live path takes `workflow.complete` from the `complete` request. The rebuild takes the log line `Session await > all barriers passed`, which sits 4 to 6 ms away from that stamp (before it in a successful run, after it in a failed one). Again, near a second boundary the two seconds can differ by one.
- TC-030 and TC-031 therefore compare the start and end times with a tolerance of one second, and every other field exactly. This is a limit of what Nextflow records. The platform cannot remove it, short of storing times at a coarser resolution than seconds.
- For a run with no completion record, the rebuild keeps the time of the last timestamped log line as its last message.

### Run id

`workflowId` is the first 16 hex characters of sha256(`sessionId` + "/" + `runName`), computed by `abf_platform.common.run_id`. `create` returns it, and `rebuild` derives the same value from the session ID and run name in `.nextflow/history`.
