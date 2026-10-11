# The run receiver, the read-only MCP server, and the station agent

`platform/` holds a small program, `abf-platform`, that does two things, and a second program, `abf-station` (the station agent, section 6), that lets it ask about a site without ever holding a credential:

1. It **receives** what Nextflow reports about a run. Nextflow's own `nf-tower` plugin sends the start of a run, its progress, a heartbeat once a minute and its end to whatever address you set as `tower.endpoint`. The receiver accepts those messages and keeps a small index of the runs.
2. It **answers questions** about that index to an AI client over MCP (Model Context Protocol), with read-only tools: `list_runs` and `get_run` for runs, `list_compute_envs`, `get_compute_env`, `list_agents` and `list_site_files` for the compute environments and the agent (sections 6 to 8).

It does not start, cancel or delete anything, it has no web pages, and it never contacts Seqera Platform (ADR 0004). Nextflow's own records stay the truth about a run; the index can be thrown away and rebuilt (see "Rebuild the index").

## What you need

- Python 3.10 or newer.
- For the tests only: Java 17 or newer, and a connection that can download the pinned Nextflow once.

```bash
python3 -m venv ~/abf-venv            # or: virtualenv -p python3 ~/abf-venv
~/abf-venv/bin/pip install ./platform # run from the repository root; installs the abf-platform command
```

Without installing, `PYTHONPATH=platform python3 -m abf_platform ...` does the same as `abf-platform ...` everywhere below.

## 1. Start the receiver

```bash
abf-platform serve                  # listens on 127.0.0.1:8787, this machine only
abf-platform serve --port 9000
```

It prints where it listens and where its two files are. Leave it running.

**It listens on `127.0.0.1` unless you say otherwise.** `--host 0.0.0.0` (or any non-local address) makes it reachable from every machine that can reach this one, and the program prints a warning line when you do. Doing so has a real cost: anyone on the network can send it requests and try tokens against it, and the traffic is plain HTTP, tokens included. Do it only behind a firewall or a TLS proxy you control.

## 2. Issue a token

```bash
abf-platform token new
```

The token starts with `abf_` and is shown **once**. The platform keeps only a hash of it, so a lost token cannot be shown again; issue another. A token can only write to the runs it created.

## 3. Point Nextflow at it

Set the token in the environment and pass the address on the command line:

```bash
export TOWER_ACCESS_TOKEN=abf_...          # the token from step 2
nextflow run <pipeline> -with-tower http://127.0.0.1:8787 -with-trace
```

- `-with-trace` is what lets `rebuild` recover the task numbers later; use it for runs you want to be able to rebuild.
- Prefer the environment variable to `tower.accessToken` in a config file: a config file is easy to commit or share by accident. The platform never stores the resolved config, the command line, environment variables or parameters whose names contain `token`, `password`, `secret` or `key`, but your own files and shell history are outside its reach.
- A wrong or missing token makes Nextflow stop before the first task, with an "Unauthorized" message.
- Tested with Nextflow 26.04.7 and `nf-tower` 1.28.3 (`specs/008-run-receiver/research.md`).

What the receiver stores per run: name, session id, start and end time (whole seconds), task numbers (total, succeeded, cached, failed, aborted, running, pending, submitted) overall and per process, the failed tasks with their exit code and error text, and the parameters with secret-looking names blanked. A **cached** task (from `-resume`) is counted on its own, not as succeeded.

Run states:

| State | Meaning |
|---|---|
| `running` | Nextflow has sent something within the last three minutes and has not finished. |
| `succeeded` / `failed` | Nextflow reported the end of the run. |
| `lost` | No message for more than three heartbeats (three minutes) and no end. The run may have been killed. If it was only quiet and then reports its end, it becomes `succeeded` or `failed`. |

Nothing runs in the background to decide this: the state is worked out when you ask.

## 4. Connect Claude Code or Claude Desktop (MCP)

The MCP server reads the same index file the receiver writes, so give it the same location (the default is the same for both).

**Claude Code**, over stdio:

```bash
claude mcp add abf-platform -- abf-platform mcp
# without installing: claude mcp add abf-platform -e PYTHONPATH=platform -- python3 -m abf_platform mcp
```

**Claude Desktop**, in its `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "abf-platform": { "command": "abf-platform", "args": ["mcp"] }
  }
}
```

Use the full path of the command if Desktop cannot find it. Then ask, for example, "what is the state of my latest runs?"; the AI calls `list_runs` (newest first, with name, state, start time and task numbers) and, for one run, `get_run` (adds the per-process numbers and the failed tasks with exit code and error text).

**Streamable HTTP**, for a client that wants a URL:

```bash
abf-platform mcp --http                # http://127.0.0.1:8788/mcp, this machine only
```

The same warning as for the receiver applies to `--host`.

## 5. Rebuild the index

The index is not the truth; Nextflow's own records are. If the index is lost or wrong, drop it and build it again from the launch folders (the folders you ran `nextflow` in, holding `.nextflow/`, `.nextflow.log` and the trace file):

```bash
abf-platform rebuild /path/to/launch_folder_1 /path/to/launch_folder_2
```

- Only the folders you list are read; runs from other folders are not in the new index. A folder that does not exist, cannot be read or has no `.nextflow/history` is **named with the reason and skipped**, the summary counts the skipped ones, and the exit code is non-zero. If no folder can be read at all, the old index is left alone.
- The run ids, names, session ids, states and task numbers come out the same as before. Start and end times are whole seconds and can differ by one second from what the live messages said, because Nextflow writes them from separate clock readings.
- A run that Nextflow never finished (killed) comes back as `lost`, never as running or succeeded.
- Tokens are kept in a separate file that `rebuild` never opens, so issued tokens stay valid.
- **Do not rebuild while a run is still going.** A rebuilt run has no token owner, so the platform refuses that run's later messages, and Nextflow stops a run whose progress message is refused. Wait until every run has finished, or accept that a still-running run is shown as `lost` and may be stopped.
- Nextflow keeps the logs of only a limited number of past runs per folder. A run whose log or trace file is gone is rebuilt from `.nextflow/history` alone, with a note, and its task numbers are zero.

## 6. The station agent

`abf-station` is a small program that runs on **your** side: in WSL, or in a Linux bash on a machine you control (the lab's always-on computer, say). It connects **outward** to the platform and never accepts a connection (the platform never calls it). It does two read-only things, and nothing else:

- `preflight`: check that a compute environment's site can be used (the checks are listed in section 7);
- `list_site_files`: list one folder on the site (names, sizes, modification times).

Every command it sends to the site goes through `scripts/on_site.sh`, the one sanctioned way to reach the site, and so through the shared connection **you** opened with your one-time code. The agent never opens a connection of its own and never asks for a password or code.

It does **not** launch, cancel, delete, move or write anything, and it has no job kind for any of them. The agent is a new path that passes through none of the plugin's hooks, so its only guard is its own allow-list, enforced twice: the platform checks a request when it is queued, and the agent checks it again before it runs anything. A job it does not know is refused with a reason, never guessed at.

It runs in **WSL or Linux bash only**. Started on native Windows or in Git Bash it stops at once and says that the missing capability is WSL (`wsl --install`).

### Start it

```bash
abf-platform serve                                   # 1. the platform, as before
abf-platform agent-token new my-laptop               # 2. a token for one agent name, shown once
```

3. Put the token in a file that only you can read, **inside WSL's own home** (not on a Windows drive such as `/mnt/c`):

```bash
mkdir -p ~/.config/abf && cat > ~/.config/abf/agent.token   # paste the token, then Ctrl-D
chmod 600 ~/.config/abf/agent.token
```

The agent refuses to start when the file is missing or empty, when anyone but you can read it (it says `chmod 600 <the file>`), or when the file lives on a `drvfs` or `9p` mount, which is how WSL shows a Windows drive, because permission bits cannot be trusted there. The mount table it reads is `/proc/mounts`; `ABF_STATION_MOUNTS_FILE` names another table (the tests use it to stage a Windows mount). A mount table that cannot be read is a refusal, not a pass.

4. Open the connection to the site **the old way**, once, in a real WSL terminal (the one-time code is typed there). If no connection is open, `on_site.sh` prints the exact line to paste; it looks like this:

```bash
bash scripts/on_site.sh --check-reach
#   ssh -o ControlMaster=auto -o ControlPath=<path> -o ControlPersist=8h -o ServerAliveInterval=60 <user@host> true
```

Run that printed line yourself; `ControlPersist=8h` keeps the connection for the day. Then start the agent:

```bash
abf-station run --platform http://127.0.0.1:8787 --token-file ~/.config/abf/agent.token --deployment <your root>
```

`--deployment` is the root that holds `config/env.yaml` (docs/SETTINGS.md); the agent passes that file to `on_site.sh` as `LAB_SETTINGS_FILE`, and refuses to start, naming the folder, when it is not there. `--name` is the agent name the token was made for (it defaults to what the token says). `--plugin-root` names the plugin folder that holds `scripts/on_site.sh`; by default it is the one this install came from, never the current folder.

Ask `list_agents` over MCP: the agent shows as `online`, with its name, version and last contact.

**Plain `http://` is only for the same machine.** Use HTTPS for every platform address except `localhost` and `127.0.0.1`: the agent refuses a plain `http://` address anywhere else, because the token would travel in clear text. `abf-platform serve` itself speaks plain HTTP, so put a TLS proxy in front of it before any other machine connects.

### What it tells you

| Message or exit code | Meaning |
|---|---|
| `abf-station will not start: ...` (exit 2) | A check failed before any request: shell, URL, token file or deployment. The line says which. |
| `cannot reach the platform at <URL> ...` | The platform is not up. The agent tries again after 2, 4, 8, 16 and then 30 seconds. |
| `abf-station stopped: the platform rejected the token` (exit 3) | The token is wrong or was revoked. It does not retry. |
| exit 143 or 130 | Stopped by SIGTERM or Ctrl-C. A held poll does not delay it. |

Every site command is also printed as a `site: ...` line, so you can see what the agent asked the site to do. The token is never printed, and never appears on its command line (only the token **file** path does).

To take an agent away: `abf-platform agent-token revoke my-laptop`. Its next request is refused with 401, and it stops.

### Online, offline, and the numbers

| What | Value | Setting (for tests) |
|---|---|---|
| Heartbeat | the agent says hello every 20 seconds while a job runs; a poll also counts as contact | `ABF_AGENT_HEARTBEAT_SECONDS` |
| Poll | a request the agent keeps open for up to 25 seconds, answered at once when a job arrives | `ABF_AGENT_POLL_SECONDS` |
| Offline | no contact for 3 heartbeats (60 seconds) | follows the heartbeat setting |
| Job deadline, `preflight` | 180 seconds | `ABF_PLATFORM_DEADLINE_PREFLIGHT` |
| Job deadline, `list_site_files` | 60 seconds | `ABF_PLATFORM_DEADLINE_LIST_SITE_FILES` |
| One site call | 20 seconds (`ON_SITE_TIMEOUT`, unless you already set it) | `ON_SITE_TIMEOUT` |

Online or offline is worked out when someone asks, from the last contact and the clock; nothing runs in the background to decide it. A busy agent keeps sending its heartbeat, so a long preflight does not make it look offline. The platform's settings (`ABF_AGENT_*`, `ABF_PLATFORM_DEADLINE_*`) must be given to the processes that read them: the receiver, the command line and the MCP server all use the heartbeat setting.

A caller waits at most the job's deadline. When the agent does not answer, the answer is "the agent did not answer", with the agent's name and the job kind. The job is then marked `expired`: it is never handed out afterwards, and an answer that arrives late is kept apart and changes nothing. If the agent is already offline, the answer is "agent offline" at once and nothing is queued.

### What a listing reveals

**Listing a folder sends the file names, sizes and modification times to the platform and to the model you chose** (the AI client that called `list_site_files`). File names can be sensitive; do not list a folder whose names you would not show that model. Nothing else about a file is read. A listing shows at most 500 entries and says when it was cut (`truncated`, with the total and the number shown).

What may be listed: the environment's work folder and launch folder, the extra `readRoots` of its config, and the deployment's `storage_root`. A path must be absolute, made of letters, digits and `_ . / @ + = : , -` only, and free of `..`. Anything else (`/etc`, a sibling folder that merely starts with the same letters, a path with a space, `*`, `~`, a quote or a newline) is refused with the reason, and nothing runs. The agent hands every value to `on_site.sh` quoted. A symbolic link inside a read root is listed as a link; it is not followed to decide what is allowed.

The platform keeps no credential. The agent's credentials are its token file and your connection to the site; both stay on your side.

## 7. Compute environments

A compute environment is Seqera's idea, kept the same way: a **type**, a **config**, and the **name** of a credential (never the credential). The platform stores them in `platform.db` and shows them over MCP; the command line creates and changes them.

```bash
abf-platform ce create --name=nchc --platform=slurm-platform --agent=my-laptop --host-name=login.example --work-dir=/lab/work --launch-dir=/lab/launch --head-queue=normal --compute-queue=dev --max-queue-size=50 --credentials=nchc-ssh --env=NXF_OPTS=-Xmx2g --pre-run=true
abf-platform ce list
abf-platform ce show nchc
abf-platform ce update nchc --work-dir=/lab/work2
abf-platform ce preflight nchc
abf-platform ce primary nchc
abf-platform ce disable nchc
abf-platform ce enable nchc
```

For a long value that starts with `--`, use the `=` form (`--head-job-options=--time=02:00:00`). `--env` is `NAME=VALUE` for the head job, `compute:NAME=VALUE` for the compute jobs or `both:NAME=VALUE` for both, the way Seqera's own command line writes it.

### The Slurm config

| Field | Meaning |
|---|---|
| `workDir` | required; absolute path where Nextflow works on the site |
| `launchDir` | optional absolute path; where Nextflow is started |
| `headQueue` | required; the queue of the Nextflow head job (letters, digits, `_ . -`) |
| `computeQueue` | optional; the queue of the tasks (same characters) |
| `maxQueueSize` | optional whole number, how many jobs Nextflow may queue at once |
| `headJobOptions` | optional text appended to the head job's submit options |
| `hostName`, `userName`, `port` | optional login node details (the credential itself is not here) |
| `preRunScript`, `postRunScript` | optional scripts; text only, the platform never runs them |
| `environment` | list of `{name, value, head, compute}` |
| `nextflowConfig` | optional Nextflow configuration text |
| `readRoots` | optional extra absolute paths the agent may list (`--read-root`) |

Outside the config an environment also has `name` (1 to 100 characters, unique), `description`, `platform` (the type), `credentialsId` (the **name** of a credential), `agent` (the agent that serves it; with no `--agent` the only agent that has a token is used), `status`, `message`, `primary`, and the dates `dateCreated`, `lastUpdated`, `lastUsed`. The field names follow Seqera's (`specs/007-station-agent/research.md`).

**The platform refuses anything that looks like a credential**: a private key, an `AKIA` or `ASIA` key id, `aws_secret_access_key`, `export TOKEN=...`, one of this platform's own `abf_` tokens, a variable or field named like a secret (`password`, `token`, `secret`, `key`), in any text field or any depth. The refusal names the field, never repeats the value, and says that the credential belongs on the agent's side. Queue names and paths are checked for shell syntax too (a `;`, `$(`, a quote and so on is refused).

### Status

| Status | Meaning |
|---|---|
| `creating` | made, not yet checked. With an agent online a preflight is queued by itself; with none, the message says `沒有代理在線，尚未預檢 (no agent online, not checked yet)` and the status stays. |
| `available` | the last preflight passed every check |
| `invalid` | the last preflight failed; the message names **every** failed or unchecked item |
| `unsupported` | a modelled type (below). Stored, never run. |
| `disabled` | switched off: no job is accepted and it is not primary. `enable` brings it back. |

Exactly one environment can be `primary` (the default for a launch, later). `ce primary` refuses an `unsupported` or a `disabled` environment; disabling the primary one clears the mark.

### Preflight

`ce preflight <name>` asks the environment's agent for the checks below and waits for the answer (up to the job deadline). Each is `pass`, `fail` or `unchecked`; the environment is `available` only when all pass.

| Check | What the agent does on the site |
|---|---|
| `connect` | `scripts/on_site.sh --check-reach`. If no connection is open, the check fails and says to log in once in a WSL terminal, with the line `on_site.sh` prints; the other checks are `unchecked`. If the site's sessions are used up it says so, in the words of `on_site.sh`. |
| `work_dir` | `test -d` and `test -w` on the work folder. **Nothing is created on the site.** |
| `sbatch`, `squeue`, `sinfo` | `command -v` for each. Nothing is submitted. |
| `java` | `java -version`; 17 or newer passes; a version it cannot read fails |
| `nextflow` | `nextflow -version`; the version it read is shown |
| `head_queue` | `sinfo -h -o %P` lists the head queue (`unchecked` when `sinfo` is missing) |

What goes back is the agent's own short wording (300 characters at most per check), never the site's raw output.

### The MCP tools

Six tools, all read-only (`readOnlyHint`): `list_runs`, `get_run`, `list_compute_envs`, `get_compute_env`, `list_agents` and `list_site_files`. `list_site_files` puts one read-only question in the job queue and waits for the answer; it cannot name a command or a kind of job. There is no tool that creates or changes an environment: that is the command line for now.

## 8. The types

Fourteen types can be created, with Seqera's identifiers (`specs/007-station-agent/research.md` gives the source). **Only Slurm is supported in this slice**; the other thirteen are *modelled*: their settings are stored as given, their status is `unsupported`, and a preflight or a listing is refused at once (no code runs for them, and no cloud library is used) until someone with a real account has tested the type.

| Identifier | Type | Supported |
|---|---|---|
| `slurm-platform` | Slurm | yes |
| `altair-platform` | PBS Pro | modelled only |
| `lsf-platform` | IBM Spectrum LSF | modelled only |
| `uge-platform` | Grid Engine | modelled only |
| `moab-platform` | Moab | modelled only |
| `awsbatch-platform` | AWS Batch | modelled only |
| `awscloud-platform` | AWS Cloud | modelled only |
| `azbatch-platform` | Azure Batch | modelled only |
| `azcloud-platform` | Azure Cloud | modelled only |
| `googlebatch-platform` | Google Cloud Batch | modelled only |
| `googlecloud-platform` | Google Cloud | modelled only |
| `k8s-platform` | Kubernetes | modelled only |
| `eks-platform` | Amazon EKS | modelled only |
| `gke-platform` | Google GKE | modelled only |

Seqera Compute is not a type here: it is Seqera's own hosted service and has no counterpart outside Seqera.

For a modelled type, give the settings as JSON: `abf-platform ce create --name=aws1 --platform=awsbatch-platform --config-json=@settings.json`. Only the shared checks apply (name, credential name, the credential scan); there is no field list.

## Where the files are

Nothing is hard-coded; every location can be changed.

| What | Default | Override |
|---|---|---|
| Run index | `${XDG_DATA_HOME:-~/.local/share}/abf-platform/index.db` | `ABF_PLATFORM_DB` |
| Token file | `tokens.db` in the same folder as the index (run tokens and agent tokens; a file made by an earlier version is upgraded in place, and its tokens stay run tokens) | `ABF_PLATFORM_TOKENS` |
| Compute environments, agents and jobs | `platform.db` in the same folder as the index. `rebuild` never opens it. | `ABF_PLATFORM_STATE` |

The folders are created on first use. The `.gitignore` of this repository keeps `*.db` files out of version control.

`ABF_PLATFORM_CLOCK_OFFSET` (seconds, default 0) shifts the clock the query side uses. It exists so the tests can look at a run "three minutes later"; leave it unset.

## What it does not do

No launching, cancelling or deleting of runs, no clean-up of `work/`, no web pages or login, no roles. The agent only answers two read-only questions (check a site, list a folder); it submits nothing, writes nothing and runs no command a platform sends it. Compute environments of the thirteen other types are stored and never used. Launching, with a confirmation step, is a later feature (007b), and MCP tools that create or change environments are a later one (009).

## Tests

```bash
bash tests/platform_test.sh      # also run by tests/run_all.sh
```

It builds a venv in `${XDG_CACHE_HOME:-$HOME/.cache}/abf-platform-venv`, downloads the pinned Nextflow and its `nf-tower` plugin into `${XDG_CACHE_HOME:-$HOME/.cache}/abf-platform` (every file checked against a pinned sha256), and runs `pytest` in `platform/`. The end-to-end tests run the real Nextflow, against a receiver on `127.0.0.1`, with small pipelines from `platform/tests/fixtures/flows/` that need no container.

- With `CI=true`, missing Java or Python, a failed download or a skipped test is a **failure**.
- Without `CI`, the end-to-end tests are skipped with one visible line, `E2E SKIPPED: <reason>`, and the summary counts the skipped tests. A checksum that does not match always stops the run.

The agent's tests (`platform/tests/test_station_*.py`) run in the same command: they start a real platform process and a real agent process against a **fake site**, a temporary deployment whose PATH holds stand-ins for `sbatch`, `sinfo`, `java` and `nextflow` that only log their calls (with a stand-in `ssh` that must never be called). No real cluster and no Seqera service is involved; the real cluster is only exercised by hand (`docs/TESTING.md`).
