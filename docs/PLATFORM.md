# The run receiver, the read-only MCP server, and the station agent

`platform/` holds a small program, `abf-platform`, that does two things, and a second program, `abf-station` (the station agent, section 6), that lets it ask about a site without ever holding a credential:

1. It **receives** what Nextflow reports about a run. Nextflow's own `nf-tower` plugin sends the start of a run, its progress, a heartbeat once a minute and its end to whatever address you set as `tower.endpoint`. The receiver accepts those messages and keeps a small index of the runs.
2. It **answers questions** about that index to an AI client over MCP (Model Context Protocol), with eight read-only tools: `list_runs` and `get_run` for runs, `run_outputs` for the files a run produced, `read_task_log` for the end of a failed task's log, `list_compute_envs`, `get_compute_env`, `list_agents` and `list_site_files` for the compute environments and the agent (sections 6 to 8). Five more tools, `launch`, `cancel`, `resume`, `relaunch` and `forget`, only ask: they start, stop or delete nothing until a person says yes (section 9, "The confirmation page").

It never deletes a run, a run folder or a result on the site (it only prunes finished job rows after 7 days, and the owner can delete a submission's kept content with `forget`), it starts or cancels a run only after a person's yes, its only web pages are the login, the confirmation page, the read-only board and the settings frame (`abf-platform web`), and it never contacts Seqera Platform (ADR 0004). Nextflow's own records stay the truth about a run; the index can be thrown away and rebuilt (see "Rebuild the index").

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

Use the full path of the command if Desktop cannot find it. Then ask, for example, "what is the state of my latest runs?"; the AI calls `list_runs` (newest first, with name, state, start time and task numbers) and, for one run, `get_run` (adds the per-process numbers, the failed tasks with exit code and error text and, when Nextflow reported it, `workdir` (the task's folder on the site; absent when not reported, and always absent on a run rebuilt from the run folder), `cancel_requested_at` (present only when a confirmed cancel of the run was sent: the same fact `abf-platform launches` prints, never a status), and for a failed run `failure_reason`: Nextflow's own `errorMessage`, else the first line of its `errorReport`, on one line and at most 1000 characters; absent when Nextflow gave none, and absent on a run rebuilt from the run folder, whose log does not hold it; and `su`: the SU the run's finished tasks used and what it costs, an estimate from the task records the receiver keeps (`task_usage`): `su`, `twd_nstc`, `twd_academic`, `unknown_reasons`, `site`, and `twd` (nstc, academic, industry) when the site has money rates per SU. Every number is `null` with the reasons when the run has not ended, when a finished task has no usage record, or when a record lacks cpus, realtime or a partition factor; a run rebuilt from the run folder always is).

**Streamable HTTP**, for a client that wants a URL:

```bash
abf-platform mcp --http                # http://127.0.0.1:8788/mcp, this machine only
```

The same warning as for the receiver applies to `--host`.

**Who is calling: users and personal access tokens (spec 009d).** Over HTTP the platform needs to know who calls. A user (name and lab) is made on the terminal, and gets a personal access token (PAT), which is what the client sends:

```bash
abf-platform user add 王小明 --lab lab-x
abf-platform pat new --user 王小明 --label laptop   # prints abf_pat_... ONCE; only its hash is kept
abf-platform pat list                               # id, user, label, created, revoked; never a value
abf-platform pat revoke <id>                        # refused from the next request on
```

`mcp --http` answers 401 (`WWW-Authenticate: Bearer`) to every request that does not carry `Authorization: Bearer <PAT>` of a live token of a user who is not disabled; with no users yet, every request is 401 and the command says so. Put the PAT in the client's header setting, for example `claude mcp add --transport http abf-platform http://127.0.0.1:8788/mcp --header "Authorization: Bearer <PAT>"`. Local stdio (`abf-platform mcp`) needs no token. Users and PATs are made and revoked only on the terminal (no MCP tool, no web route); the tokens live in tokens.db, so `rebuild` never loses them. A PAT opens only the MCP door (not the receiver, not the agents), and a run or agent token does not open MCP. The caller is only recorded (the confirmation of a launch or cancel stores the user's id when one is given); it is never a confirmation, which stays the terminal's y. Not in this step: OAuth, a public URL or TLS, roles, token expiry.

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

`abf-station` is a small program that runs on **your** side: in WSL, or in a Linux bash on a machine you control (the lab's always-on computer, say). It connects **outward** to the platform and never accepts a connection (the platform never calls it). It does three read-only things, and nothing else:

- `preflight`: check that a compute environment's site can be used (the checks are listed in section 7);
- `list_site_files`: list one folder on the site (names, sizes, modification times);
- `read_task_log`: read the end of one of `.command.err`, `.command.out`, `.command.log` in the task folder of one failed task (`workdir` of `get_run`): read-only, at most the last 200 lines and 64 KB, and a cut is said. The agent reads only inside the places it may read, takes no other file name, and refuses a link. The text goes to the model you chose, like a listing. The tool `read_task_log(run_name, task, which)` is refused, with the reason, when the task has no recorded workdir, the run was not launched from this platform, or the agent is offline.

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
abf-platform ce create --name=gcb1 --platform=googlebatch-platform --agent=host1 --project=lab-project-1 --location=europe-west2 --service-account-email=runner@lab-project-1.iam.gserviceaccount.com --boot-disk-size="50 GB" --spot --config-json='{"workDir":"gs://lab-bucket/work"}' --credentials=gcp-lab
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
| `suSite` | optional name of a site in `configs/sites/su_rates.json` (for example `nano4`); `get_run` uses it to work out the SU of a run launched on this environment. Without it the rates file's `default_site` is used. A name the rates file does not have is refused |

Outside the config an environment also has `name` (1 to 100 characters, unique), `description`, `platform` (the type), `credentialsId` (the **name** of a credential), `agent` (the agent that serves it; with no `--agent` the only agent that has a token is used), `status`, `message`, `primary`, and the dates `dateCreated`, `lastUpdated`, `lastUsed`. The field names follow Seqera's (`specs/007-station-agent/research.md`).

**The platform refuses anything that looks like a credential**: a private key, an `AKIA` or `ASIA` key id, `aws_secret_access_key`, `export TOKEN=...`, one of this platform's own `abf_` tokens, a variable or field named like a secret (`password`, `token`, `secret`, `key`), in any text field or any depth. The refusal names the field, never repeats the value, and says that the credential belongs on the agent's side. Queue names and paths are checked for shell syntax too (a `;`, `$(`, a quote and so on is refused).

### Google Cloud Batch

A `googlebatch-platform` environment is served by **a station agent that runs on the platform host** (`abf-station run`, the one an operator already runs there), and `--agent` must name it. The people who use the cloud install nothing: the platform never starts a program itself (principle 2), so the preflight is a job for that agent, the same kind of job a Slurm environment gets. `ce create` and `ce update` queue it; `ce preflight <name>` queues it and waits for the answer. **It can launch and cancel** (see "Launching on Google Batch" below, with the same question and the same yes as for Slurm). A listing, a record fetch and a task log are refused in plain words (尚未支援), and the automatic choice of an environment never picks it: a launch on it needs its name (`--ce gcb1`), so nothing that costs money is chosen for you.

| Key | Rule |
|---|---|
| `project` | required; the GCP project **ID**, 6 to 30 characters, lower-case letters, digits and `-`, starting with a letter, not ending with `-` (`--project`) |
| `location` | required; a region such as `europe-west2` (`--location`) |
| `workDir` | required; `gs://<bucket>[/<folder>]`, the bucket 3 to 63 characters of lower-case letters, digits and `- _ .`; no `..`; a trailing slash is dropped |
| `spot` | optional true or false (`--spot`, `--no-spot`) |
| `bootDiskSize` | optional, `50 GB` or `50GB`, 1 to 2000 (`--boot-disk-size`) |
| `bootDiskImage` | optional image name, at most 200 characters |
| `serviceAccountEmail` | optional; an e-mail address like `runner@lab-project-1.iam.gserviceaccount.com`, never a key (`--service-account-email`) |
| `network`, `subnetwork` | optional VPC and subnet names, or `projects/...` paths |
| `usePrivateAddress` | optional true or false |
| `labels` | optional object; keys and values at most 63 characters, at most 64 pairs |
| `maxvCpus` | optional whole number 1 to 10000; it takes effect from C-2 as a per-task cpus limit (`process.resourceLimits = [cpus: N]`, one task at most, **not** a total of vCPUs); a total cap belongs to C-3 |
| `preRunScript`, `postRunScript`, `environment`, `nextflowConfig` | the shared checks |

Every problem is listed at once, each naming its key. There is no field for money or currency: cost is not part of this type. Only the **name** of the credential is stored (`--credentials`, the top-level `credentialsId`). The service-account key file lives on the agent's computer, never in `platform.db`, a log or an answer, and the platform never reads it. The agent looks for it at `ABF_STATION_GCP_CREDENTIALS`, or else at `_personal/gcp-sa.json` in its deployment folder (the folder that holds `config/env.yaml`); make it readable by that user only (`chmod 600`). The agent judges `project`, `location` and the bucket again before it builds a command.

| Check | What the agent does |
|---|---|
| `credential_name` | the environment has a credential name |
| `credential_file` | the key file exists, is a regular file and (not on Windows) is not readable by others; when it is missing the message says where to put it |
| `credential_shape` | the file is a service-account key with `client_email` and `private_key` (a Workload Identity file is not supported); only missing key names are ever shown |
| `credential_project` | the `project_id` in the file is the environment's `project` |
| `service_account` | `serviceAccountEmail` has the shape of an address (it need not equal the file's `client_email`); without it the Compute Engine default account is used |
| `gcloud` | `gcloud` is installed (`unchecked`, not `fail`, when it is not) |
| `batch_api` | `gcloud batch jobs list --limit 1` answers |
| `bucket` | `gcloud storage ls gs://<bucket>/` answers |

**預檢不計費 (the preflight costs nothing):** it only reads. It lists Batch jobs and the top of a bucket and reads the key file; it creates no Batch job, writes nothing to a bucket, enables no API and creates no service account. Each `gcloud` call is limited to 30 seconds; a timeout fails that one check. The key file's path is handed to `gcloud` in its environment (`CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE`), never in its arguments, and no `ABF_` variable is passed on. Without `gcloud` on that computer the two API checks are `unchecked` and the environment stays `invalid`, with a message that says so. A record made before this type was checked keeps its status `unsupported`; `ce update` and `ce preflight` apply today's rules to it and say which fields are missing, and a completed one becomes `creating` until its first preflight is answered.

### Launching on Google Batch

The question, the screen and the yes are the ones of a Slurm launch: `abf-launch ... --ce gcb1` (or the web page) builds everything, shows all of it, and sends it only after a person answers y. Nothing is started before that yes. The environment must be named: it is never chosen automatically.

**Who runs what.** The Nextflow head process runs **on the platform host**, started by the station agent that serves the environment. The tasks are run by Batch virtual machines that the head process asks Google for (`process.executor = 'google-batch'`). Progress reaches the platform through `-with-tower` at the address the agent is connected to (normally loopback). The platform itself starts no program.

**What the platform host needs.** Java 17 or newer, Nextflow, and `gcloud`; `storage_root` set in the deployment's settings (the run's own folder is `<storage_root>/_gcb_runs/<run>`); and the service-account key file where the agent looks for it (`ABF_STATION_GCP_CREDENTIALS`, mode 600). The host must be Linux or WSL: the cancel looks at `/proc`. The agent checks Java and Nextflow just before a launch (not in the preflight), and runs the preflight again.

**Money.** 費用：按下 y 之後，這個 run 會在 Google Cloud 專案裡建立 Batch 工作與虛擬機，**由 Google 向實驗室的 Google Cloud 帳號收費**。The platform has no cost estimate and no cap yet (C-3); the actual amount is on Google's invoice. The launch screen says this in its first paragraph, without a number.

**Input data.** Every path cell of the samplesheet must be `gs://<bucket>/<object>` in the **same bucket as `workDir`**. A local path, `http(s)://`, `s3://`, another bucket, or a `..` is refused with a plain sentence. Copying files into the bucket is a later feature (C-6); for now put them there yourself with `gcloud storage cp`. `workDir` must have at least one folder below the bucket (`gs://lab-bucket/work`, not `gs://lab-bucket`): that is Nextflow's rule.

**The files.** Five files are shown and then written to the run's folder (mode 700), with `tower.token`, `head.pid` and `head.out`: `samplesheet.csv`, `params.yaml`, `nextflow.config` (the environment's own text, unchanged), `gcb.config` (made from the environment's fields, read after `nextflow.config` with `-c nextflow.config -c gcb.config`, so it wins) and `head.sh`. The work folder and the results are in the bucket, one prefix per run: `<workDir>/runs/<run>/work` and `<workDir>/runs/<run>/results`.

| Line of `gcb.config` | From |
|---|---|
| `process.executor` | always `'google-batch'` |
| `workDir` | `workDir` and the run name |
| `google.project`, `google.location` | `project`, `location` |
| `google.batch.spot` | `spot`, only when true |
| `google.batch.bootDiskSize` | `bootDiskSize`, written as `50.GB` |
| `google.batch.bootDiskImage` | `bootDiskImage` |
| `google.batch.serviceAccountEmail` | `serviceAccountEmail` (the account the tasks run as) |
| `google.batch.network`, `google.batch.subnetwork` | `network`, `subnetwork`, short names as given |
| `google.batch.usePrivateAddress` | `usePrivateAddress`, only when true |
| `process.resourceLabels` | `labels` and one more, `abf-run=<run name>` |
| `process.resourceLimits` | `maxvCpus`: a per-task limit on cpus, not a total |

**The key.** The key file's path is the agent's own setting. It is given to the head process in its environment (`GOOGLE_APPLICATION_CREDENTIALS`) and nowhere else: not in `head.sh`, not in an argument, not in the bundle, not in an answer or the database. `head.sh` carries a comment saying so.

**Cancel.** After the same kind of yes, the agent checks that the number in `head.pid` is still the head process of this run (its owner, `-name <run>` in its command line, its working folder) and sends **one** `SIGTERM`. Nextflow is expected to cancel the Batch jobs it started when it ends; this is checked by hand once (docs/TESTING.md), so after a cancel look at the Batch page of the Google Cloud Console: a virtual machine that was not cancelled is still billed. The platform deletes nothing in Google Cloud.

**Not yet.** Resume and relaunch of a Google Batch run, reading its Nextflow records back, listing files and reading a task log are refused with 尚未支援. The result field `slurm_job_id` holds the head process number (pid) for a Google Batch run; the table has no other column for it, and no migration was needed.

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

Three more checks are **conditional**: they appear in the answer only when the environment asks for them, so an environment that sets none of the keys below gets exactly the eight checks above, with the same wording as before.

| Check | Appears when | What the agent does on the site | When it fails, the next step |
|---|---|---|---|
| `modules` (placed before `java`) | the environment's `modules` list is not empty | `module load <m1> && module load <m2> ...`; `java` and `nextflow` are then probed with the same `module load ... &&` in front | The message names the first module that would not load. Check the environment's `modules`, or empty the list and use a self-installed Nextflow (an empty list means no `module load` is run at all). |
| `site_pipeline` (after `head_queue`; one result for all entries) | `sitePipelines` is not empty | For each entry: load its module, read `main.nf` under its home variable, and read the `version` of the `manifest { }` block of `nextflow.config`. A leading `v` is ignored. A commit revision (40 hex digits) only needs `main.nf` to be readable. | "not installed where the module says": the module or `main.nf` is not there. "the site variable ... is not set": the module did not define its home variable. "the site has X, the environment says Y": fix the `revision` in the environment, or ask the site to install that version. |
| `image_library` (last) | the environment's `environment` holds `NXF_SINGULARITY_LIBRARYDIR` | `test -r` and `test -x` on that folder (its contents are not listed) | The message names the folder: it is missing or cannot be entered. The folder need not be inside a read root. |

Everything is read-only. If the connection goes away during one of these probes, the preflight ends the usual way: `connect` fails and every other applicable check, these three included, is `unchecked`. These checks need no database change (a preflight answer already lives in the environment's JSON record).

### The MCP tools

Thirteen tools. Eight are read-only (`readOnlyHint`): `list_runs`, `get_run`, `list_compute_envs`, `get_compute_env`, `list_agents`, `list_site_files`, `read_task_log` and `run_outputs`. `list_site_files` and `read_task_log` each put one read-only question in the job queue and wait for the answer; neither can name a command or a kind of job. `run_outputs` (results-outputs) never waits: it shows the newest answer to the question "what is in `<run folder>/results`", or queues that question and says `loading`. The other five, `launch`, `cancel` (spec 009c), `resume`, `relaunch` (spec 009e, see "Resume and relaunch") and `forget` (keep-submissions, see "Forget"), are marked as writing (`cancel` also as destructive) but start and stop nothing by themselves: each builds what the terminal command builds, writes a pending request and asks the person (section 9, "The confirmation page"). They have no argument that could say yes. There is no tool that creates or changes an environment, a user or a password: that is the command line.

## 8. The types

Fourteen types can be created, with Seqera's identifiers (`specs/007-station-agent/research.md` gives the source). **Slurm and Google Cloud Batch can run; the other types can be modelled only** (Google Cloud Batch is served by a station agent on the platform host, see "Google Cloud Batch" above); the other twelve are *modelled*: their settings are stored as given, their status is `unsupported`, and a preflight or a listing is refused at once (no code runs for them, and no cloud library is used) until someone with a real account has tested the type.

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
| `googlebatch-platform` | Google Cloud Batch | Slurm-like confirmed launch and cancel on the platform host (resume: not yet) |
| `googlecloud-platform` | Google Cloud | modelled only |
| `k8s-platform` | Kubernetes | modelled only |
| `eks-platform` | Amazon EKS | modelled only |
| `gke-platform` | Google GKE | modelled only |

Seqera Compute is not a type here: it is Seqera's own hosted service and has no counterpart outside Seqera.

For a modelled type, give the settings as JSON: `abf-platform ce create --name=aws1 --platform=awsbatch-platform --config-json=@settings.json`. Only the shared checks apply (name, credential name, the credential scan); there is no field list.

## 9. Launch and cancel

Feature 007b. The station agent can now start a Nextflow analysis on the cluster and stop it, and Nextflow reports its progress back while it runs. This is the one place in this repository that submits a job of its own (constitution 4.0.0, principle 2), so it is built to do nothing until a person has seen all of it and said yes.

### Launch

```bash
abf-platform launch --ce lab-a --pipeline nf-core/ampliseq --revision 2.18.0 --run-name ampliseq-d5 --samplesheet samples.csv --param pacbio=true --param FW_primer=AGRGTTYGATYMTGGCTCAG
```

- `--revision` is a release tag or a full 40-character commit. A branch name is refused.
- `--samplesheet` is the CSV you wrote, with one row per sample. Columns that hold file paths (by default `fastq_1`, `fastq_2`, `reads`, `file`, `path` and similar; name more with `--path-column`) must hold absolute paths inside the compute environment's work folder, launch folder, `readRoots`, or the deployment's `storage_root`.
- `--param name=value` (repeatable) or `--params-file file` (flat `name: value` lines). `input` and `outdir` are fixed: `outdir` is always `<run folder>/results`.
- The compute environment must be available, its agent online, and the deployment's `slurm_account` set. There is no default account: a default would bill somebody else's project. If the environment's `headJobOptions` carries `-A`, it must be the same account.

**Before anything happens the command shows all of it**: pipeline and version, environment, the run folder, the account, the head queue and its options, every row of the samplesheet, `params.yaml`, `nextflow.config` and the whole of `head.sh` (the script that will be submitted). The `nextflow.config` shown is your compute environment's own text, first and unchanged, and after it a block the platform always adds, with a comment saying so: `report.overwrite = true` and `timeline.overwrite = true`. When a run is cancelled Nextflow writes its report and timeline twice, and without these two settings the second write is refused and the log of the cancelled run holds an ERROR (`Report file already exists`). The block is part of what you see and of the hash you confirm; trace and DAG files are not touched. Every line starts with `| `; every control character in a value is written out (`\t`, `\x1b`, `‮`, `\\`), so no value can hide a line or rewrite the screen. NUL, CR, ESC and bidirectional controls in a samplesheet cell or a parameter are refused, before the question. Then it asks `確定送出？(y/N)`.

**Only y or Y, typed on the terminal the command runs in, sends it.** Anything else, Enter, Ctrl-C, Ctrl-D, a closed terminal, a pipe, a program that has no controlling terminal, does not. There is no flag (`--yes` is an unknown option) and no environment variable that answers for you, and none is documented because none exists.

What `y` does: the platform writes one confirmation row (a random id and the sha256 of exactly what you saw) and one `launch_nextflow` job in a single transaction. The agent, which is the only program that can submit, refuses a launch unless all of this holds: the job carries a confirmation of the right kind whose hash equals the hash of the bundle it received; it has not used that confirmation before; and when it builds the bundle again from the same choices and its own settings (account, storage root, reach) the result is identical to what was confirmed. Then it runs the 007 preflight, checks the container cache is writable, opens the way back (below), creates `<workDir>/runs/<run name>` (an existing folder is refused, nothing is overwritten), writes five files into it in one step (`samplesheet.csv`, `params.yaml`, `nextflow.config`, `head.sh`, and `tower.token`, mode 600, folder mode 700) and calls `sbatch` once, never again. A failure says what is left on the site and leaves it; nothing is deleted. The agent will not submit when fewer than 60 seconds of the job's deadline remain (`ABF_STATION_MIN_REMAINING`).

The deadline of a launch is 300 seconds (`ABF_PLATFORM_DEADLINE_LAUNCH`). If the agent answers after it, the Slurm number is still written to the record, and the command waits up to `ABF_PLATFORM_LAUNCH_GRACE` seconds (default 120) for it; if the agent died, the command says `結果不明：請查國網上的 <run folder> 與 Slurm 工作 nf-<run>`.

### Cancel

```bash
abf-platform cancel ampliseq-d5
```

It shows the run name, the Slurm job number and the run folder and asks `確定取消？(y/N)` in the same way. The agent asks Slurm once (`squeue -h -j <id> -o '%j|%u|%Z'`) and sends one stop to that one number only if the answer is exactly one line with the job name `nf-<run>`, your `site_user`, and the run folder. Nextflow receives the signal and stops its tasks, then reports the end it chose: `get_run` shows that (a stopped run is shown as failed, with Nextflow's own reason), and `abf-platform launches` adds the fact "取消請求已於 T 送出". The platform never writes "cancelled" as a state. Tasks that were already running on the cluster may take a moment to go; check `squeue` yourself.

### Forget (keep-submissions)

```bash
abf-platform forget ampliseq-d5
```

`abf-platform forget RUN` deletes what a launch was sent with; until then it is kept. For each submission the platform keeps the bundle (what was run) and the screen text (what the person approved). A confirmed request keeps both for as long as the owner wants: no clock clears them, whatever the channel was (the terminal's `y`, the client's form or the page; since keep-submissions the confirmation row of a terminal launch holds the bundle and the screen text too, which the 7-day clean-up of finished jobs cannot take away). A resume or a relaunch of a forgotten run is refused (see "Resume and relaunch"). `forget` is how the owner deletes them. It clears the bundle and the screen text of every request behind that run (the launch, its cancels, and any pending or void request that names the run; an open pending one is made void), and the copy each of the run's jobs kept of what was queued (the job's `args_json` becomes `{"forgotten": true, "bundle": {"run_name": "<name>"}}`, so a late answer from the agent is still read). Every row cleared gets `forgotten_at` and `forgotten_by` (the user id, empty from the terminal). The audit record of who sent it and when (`id`, `sha256`, `kind`, times, `caller_user_id`, `channel`, `state`), the run, its results on the cluster and the run list are not touched, and nothing is queued for the agent.

It shows the run name and 「刪除後無法復原；這個 run 之後不能再續跑或原樣重跑。紀錄（誰、何時送出）會保留。」 and asks `確定刪除？(y/N)` as `cancel` does: only a `y` at the terminal, no `--yes`, and no owner check at the terminal. It cannot be undone, so it is refused, with nothing changed, while the run is `running`, `lost` (it may still run on the cluster), not yet in the run index while its launch job is still queued or claimed, or has gone out (finished `done`) and the index does not know the run yet, until the index sees it or 24 hours after the job ended (「這個 run 還在準備中，不能刪除」; the 24 hours are worked out from the job's own end time, nothing is stored; a launch that was refused, failed or expired and never reached the index may be forgotten at once), or while a job of the run is queued or running. A run with nothing left to clear answers 「已經刪除過了 (already deleted)」.

Over MCP the tool `forget` (argument `run_name`) is only for the owner: a run that is not yours answers like one that does not exist, and only your own requests are cleared. It asks in the client's own form with the same text. A client that cannot show a form (stdio without one, or an HTTP client whose form is not trusted, such as a connector token) is told to use `abf-platform forget <run>` in the terminal, and nothing is written. The web has no forget route (the web stays read-only; the parity is owed, see the ledger of keep-submissions).

### Resume and relaunch (spec 009e)

A run that failed, or was cancelled (to Nextflow a cancelled run is a failed one), can be gone on with by its name alone. There are two ways, and both are the same analysis: its second, third ... attempt (ADR 0009). Changing the samples, the parameters, the revision, the pipeline or the environment is a new analysis, and that is `launch`.

```bash
abf-platform resume ampliseq-d5          # the same folder; Nextflow takes up where it stopped and reuses the finished tasks
abf-platform relaunch ampliseq-d5        # a new folder, the same samples and parameters, from the start
```

Over MCP they are the tools `resume` and `relaunch`, each with the one argument `run_name`. Like `launch` and `cancel` they only ask: nothing starts until a person has said yes, in the terminal, in the form of their client, or on the confirmation page. **Every attempt asks again, even the third:** the yes of an earlier attempt is not reused, and the hash of the bundle covers the attempt number, the run it is made from, its Slurm number and the session (so a yes for attempt 2 cannot make attempt 3, and a yes for a resume cannot start a relaunch).

- **Which runs.** A run of this platform, with a Slurm number, that is the newest attempt of its analysis, whose end in Nextflow's own records (the run index; nothing about it is stored here) is `failed`. `succeeded` is refused (`已成功，不需要續跑`), a run that is still going, has sent nothing yet or has been silent for three heartbeats (`lost`) is refused (`還在跑`), and an older attempt is refused with the name of the newer one. The agent and the environment must be the ones of the first launch: when the platform rebuilds the first launch from the facts it has today and the result is not the same, that is a new analysis and the answer says to use `launch`.
- **What a resume is.** Its bundle has no samples or parameters of its own: it carries the first launch's bundle verbatim (`origin`), the new run name (`<root>-a<N>`, cut to 64 characters; for a relaunch the same), the old folder and one new file, `head-<N>.sh`, which is the first head script with `-resume <session id>` and the new `-name`. The session id is read from the run index, and only a UUID is accepted. The screen shows the old run, which attempt this is, the Slurm number, the pipeline, revision and sample count, the sentence `這是續跑：同一個資料夾，沿用已完成的 task；樣本和參數不變` and the exact last line of `head-<N>.sh`, the one that starts Nextflow.
- **What a relaunch is.** `prepare_launch`'s own output for the first launch's pipeline, revision, samples and parameters under the new name, plus a record `relaunch` (`of_run`, `attempt`, `of_sha256`: the hash that was confirmed for the launch that made the old folder). The screen is the one of a launch with the old run, the attempt and the Slurm number in front, and the sentence `這是原樣重跑：全新資料夾，樣本與參數不變`. The agent takes it through the launch path: a new folder, five files, one `sbatch`.
- **What the agent does for a resume.** It checks the confirmation and rebuilds the first launch from its own facts as it does for a launch, and the resume bundle from that (a difference is a refusal), then runs the preflight, the container-cache check and the way back. Then it asks the site **one** question about the folder: it is a real folder, reached through no link; `head-<N>.sh` is not there; `tower.token` is not a link; the first line of `.nextflow/history` that has a session id has the session that was confirmed; the sha256 of `samplesheet.csv`, `params.yaml`, `nextflow.config` and `head.sh` are those of the first launch; and `squeue -h -n nf-<old run> -u <site_user>` shows nothing (the predecessor is not alive). Any other answer is a refusal that names the folder and says nothing was changed. Only then does it write `head-<N>.sh` and a new `tower.token` (mode 600; the token is for the new run name) into the existing folder with one `tar`, and make one `sbatch`. It never overwrites `head.sh` or an input, never deletes, never makes the folder. This is the one place where the agent writes into a folder that exists; it is narrow on purpose.
- **Whose.** Only the owner of the run: anybody else, and a run nobody owns, gets `找不到這個 run (Run not found): <run>`, the same words as a run that does not exist, and no state or Slurm number. At the terminal the account is named with `--user` as for `launch`. All attempts of an analysis have one owner: the queue checks again, with the yes's own user, that the run it is made from is that user's. Over HTTP the real paths of the samples are looked at again when the request is made (a link that now leads out of the user's folder is refused before any question) and recorded in the bundle under `upload_paths`, so the hash covers them, and the agent resolves them once more at job time.
- **The numbers.** `launches` has three more columns, last: `parent_run`, `attempt` and `attempt_kind` (`resume` or `relaunch`; all three are empty on a first launch). They are written with the job in one transaction and record a request and what it was made from, never how it went. Attempt numbers go 2, 3, 4 ... across resumes and relaunches; a job the agent refused does not use up its number; two attempts asked for at the same time cannot both be 2 (the later one is refused with `another attempt was started meanwhile`). `abf-platform launches` prints `attempt N (resume of RUN)` or `attempt N (relaunch of RUN)`.
- **Where the content is read from.** The confirmation of the first launch, which keeps it until the owner forgets the run, whatever the channel (terminal, form or page). Only a row made before the confirmation kept it (a terminal launch of an older version) is read from its launch job, which is cleared 7 days after it finished; only then, and only when that job is gone, is the answer `太久了，這次送出的內容已經清掉，請當成新分析重新送出`.
- **A forgotten run.** When the owner has forgotten the run, or the first launch of its analysis (`abf-platform forget`, above), a resume or a relaunch is refused with 「內容已被擁有者刪除 (content deleted by its owner)」: at the terminal, over MCP, and again when a yes that was given before the forget reaches the queue. Nothing is queued. Somebody else's run still answers "not found", as before.
- **Not yet accepted on NCHC.** That `nextflow run ... -resume <session id> -name <new name>` in the same folder reuses the finished tasks, and that `get_run` of the new run shows them as cached, has been checked with a fake site only. It is a manual check on Taiwania-3 (docs/TESTING.md, "Resume and relaunch (009e)").

### What was handed over

```bash
abf-platform launches
```

Lists, for each launch, the run name, the Slurm job number, the folder and the time you confirmed (and, for a resume or a relaunch, the line `attempt N (resume of RUN)`). A run that was submitted and has sent no event yet says `已送出，尚未收到 Nextflow 事件`; one that has says to look at `get_run`. This is a record of what was done, never a status: it does not say whether a run is running, and it writes nothing.

### Live progress: the way back

The head job runs on a compute node, which cannot reach your machine. The route is: Nextflow on the node, the relay on the login node (`scripts/nf_relay.py`, the one the compute nodes already use for downloads), a reverse forward on your shared ssh connection, the platform on your machine.

- The forward is an option of the connection you opened yourself, made by `scripts/on_site.sh --forward`. The site's sshd chooses its port and binds it to the **loopback** of the login node only, so nothing else on the cluster network can use it except through the relay. The port is recorded in `<deployment>/_personal/forward_port` (mode 600) and, by the agent, in `<storage_root>/_relay/forward_port` on the site, where the relay reads it for every request. One forward serves every run while the connection lives; the head job reads the port from that file when it starts.
- **The relay's rule is narrow and fails closed.** It answers a plain-HTTP request in absolute form to exactly `127.0.0.1:<that port>` and nothing else on loopback; only the paths `/trace/...` and `/user-info` (the query string does not count); never CONNECT; and it closes the connection after the answer, so a second request on the same connection never reaches the platform. A missing, unreadable or malformed port file means no. A relay process started before this rule exists answers 403; the launch then says `請重啟 relay：bash scripts/egress_ctl.sh restart`.
- **The platform and the agent must be on the same machine** (the agent's `--platform` is `http://127.0.0.1:<port>`): the reverse forward ends at the agent's loopback. Otherwise the command refuses before it asks.
- **Before the files are written, every hop is probed** on the login node with no token: first straight to the forward, then through the relay the way the head job will go. A pass is an HTTP 401 whose header `X-ABF-Platform` carries this platform's instance id (a random id kept in `platform.db`, the same after a restart). Each failure names the hop and its fix: no shared connection (open it in WSL), tunnel closed, relay not running, relay out of date, platform not answering, or some other program on that port.
- `abf-station unforward --deployment <root>` cancels the forward and removes both port files. Nothing does that for you: not a run ending, not a cancel. The forward ends with the shared connection (at most 8 hours, `ControlPersist`); a run that is still going then keeps running, its live progress stops and shows `lost` after three minutes of silence, and the records bring it right (below). Nothing rebuilds the forward by itself.

### The run token

Nextflow needs a token to report. The platform makes it **when the agent claims the launch job**, not when you answer y: a launch you decline, or that no agent takes, never has one. The platform keeps only its hash; the plain token travels once, in the agent's poll reply, and lives on the site only in `<run folder>/tower.token` (mode 600) and in the environment of the head job (`export TOWER_ACCESS_TOKEN="$(cat tower.token)"`). It is never in `head.sh`, never on a command line, never printed. It is bound to the run name: it cannot create another run. It is revoked when that run's `complete` message arrives, when the agent refuses or fails the launch, and in any case 14 days after it was made. One narrow exception, for 300 seconds after the `complete`: a message for that same run (a second `complete`, a `progress` or a `heartbeat`; Nextflow can send one after the first, PITFALLS 43) is answered OK and changes nothing, so Nextflow's log has no 401 warning. The token still cannot create or touch any other run, and after the 300 seconds, or after any other revoke, it is refused like any revoked token. **A cancel does not revoke it**, because Nextflow needs it to send its `complete` after the stop. (Seqera's own launcher keeps the token in a mode 755 script; see PITFALLS.)

### Reading Nextflow's records back

```bash
abf-platform fetch-records ampliseq-d5
abf-platform rebuild
```

`fetch-records` asks the agent, read-only, for `.nextflow.log*`, `.nextflow/history` and the trace file that a log names, from that one run folder (never `tower.token`, `params.yaml` or anything else, never through a symbolic link, at most 20 MB each, "truncated" is said). **These records are sent to the platform and stored on this machine under `<platform data>/records/<run>/`; they contain the paths and parameters of the run.** `rebuild` reads that folder as one more launch folder, and the run becomes what Nextflow's records say, whatever the live messages said.

### The confirmation page

*(Spec 009c, constitution 5.0.0.)* A launch or a cancel asked for through MCP is never sent on the model's word. `launch` and `cancel` take the same choices as `abf-platform launch` (pipeline, revision, run name, samplesheet path, environment, params) and `cancel` takes the run name; they build the same bundle and the same summary (pipeline, samples, where it runs, where the results go, and every file that will be written), write it as a **pending request** (a row of `confirmations` with `state = pending`, no job, ten minutes to live) and ask the person:

1. **A client with forms (Claude Code).** The client shows the summary with one yes/no field, 送出. Only an accepted answer whose 送出 is true flips the request and queues the job. Declined, cancelled, empty, wrong content, a client that fails, or no answer in ten minutes: the request is void and nothing is queued.
2. **Any other client (Claude Desktop, Codex).** The answer carries an address, `<base>/c/<id>`, and says: open it, log in as yourself, press 送出, then call the tool again with the same arguments. The repeated call finds the person's yes and returns the job number of the job that exists; it never queues a second one. A changed argument is a different content and gets a new request. Over local stdio, without a form, the tools refuse and say to use the terminal command or HTTP with a token. With a form answer the tool call itself confirms and queues; without one it only writes a pending request. The same-user check applies to the page and to HTTP; stdio has no caller, so it does not apply there.

Over MCP/HTTP the samplesheet file must resolve (symlinks followed) inside `<uploads_root>/<your user name>/`; a relative path means that folder. Or give the CSV itself as `samplesheet_text` (exactly one of the two; at most 1 MiB of UTF-8, not empty, no NUL; it is read from memory and no file is written on the platform machine). The cells of the samplesheet are judged the same way whichever you give (see "Files" below). `uploads_root` is the setting `ABF_PLATFORM_UPLOADS`, by default the `uploads` folder next to `platform.db`. stdio and the terminal read any path as before. One person may have at most 10 open requests; a confirmed request keeps its content until its owner deletes it (`abf-platform forget RUN`, below), whatever the channel it was confirmed through (terminal, form or page); a void or expired pending request loses its content (bundle and summary) after 7 days and keeps its audit columns (the job keeps its own copy of what was queued; `forget` clears that copy too). Over MCP a cancel is only for a run the caller launched themselves through MCP (a run launched at the terminal, or by someone else, is refused with "not launched from this platform"); the terminal `abf-platform cancel` is unchanged. A confirmed cancel is reused only for the caller who got the yes and only while its job is queued or running; after that a new cancel asks again. If the page address is only the loopback one and the caller is on another machine, the answer says so and names `--public-url`.

The page is a small separate program, `abf-platform web` (port 8789 by default). **It binds loopback only**: `--host` may be `127.0.0.1`, `::1` or `localhost`, and any other address is refused at start whatever `--public-url` says, because the program serves plain http and the login cookie must not cross a network in clear text. To let other people open it, put a TLS proxy on the same machine in front of it (for example Tailscale Funnel) and give the proxy's address as `--public-url https://…`: that is the address the answers name and, when it is `https` and not loopback, it makes the cookie `Secure`; a plain-http `--public-url` for a non-loopback name is refused too. It has the routes of the confirmation and the board (`GET /` (the board, 011a), `GET /settings` (011a), `GET|POST /login`, `POST /logout`, `GET|POST /c/<id>`) and, since 009i, the routes of the OAuth login below (see "Claude Desktop's custom connector"), and nothing else. Every page, the consent page included, is made by one function from the one stylesheet, so all carry the same headers; the content-security-policy is `default-src 'none'; style-src 'sha256-<hash of the one stylesheet>'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'` (the consent page alone adds the connector's own origin to `form-action`, for the redirect after Allow or Deny): no script, no `'unsafe-inline'`. Rules:

- **The board (`GET /`, 011a) and the settings frame (`GET /settings`) are read-only** and follow `DESIGN.md` (web design v1). A dark 40 px bar on top: the product name, two plain-text cost lines "SU —" and "雲端 NT$ —" ("—" until 011d; no link, no number, hidden below 900 px), the language switch (two plain links, `?lang=en`; no cookie; only the board pages and the board's 404 are translated, the login, confirmation and consent pages stay Chinese) and the user name. Under it three columns, 272 px / fluid / 320 px (232 / fluid / 288 below 1200 px; one column below 900 px, in the order middle, right, left). Left: "現在", then my runs (status symbol, name, stage), the not-yet-built items (new project, search, upload, data explorer, dashboard) as grey "之後開放" text, 設定 and logout (the only form, with its CSRF token). Middle: with no `?run=`, the Now page, two cards (正在跑 = running runs, 需要注意 = failed and lost runs with the first line of Nextflow's failure text), one line per run linking to the run; with `?run=<id>`, the five-stage board (launch, running, results, downstream, finished) of that run, the stage picked with `?stage=<name>` (anything else falls back to the run's own stage), times in Asia/Taipei as `MM-DD HH:mm`. Right: the progress tab (the chat tab is grey), a counts row (▶ running, ! failed and lost, ✓ succeeded) and my runs as whole-block items grouped 執行中 (running, failed, lost) and 結果 (succeeded), each numbered by start time among my runs. The settings page has six sections, all still "之後開放" (no key can be typed yet). The stage is worked out from the status each time (running, lost and failed are `running`; succeeded is `results`) and never stored. The pages call only `list_runs` and `get_run`, always with the logged-in user as the caller, so a user sees only the runs they launched; a run with no recorded submitter is shown to nobody on the web (the terminal still lists it). Another person's run and a missing id give the same 404 page. Lists show 100 rows and "還有 N 筆". `/` refreshes itself every 15 seconds (a meta tag, no script). Colours, type sizes, spacings and radii are only the tokens of DESIGN.md.

- **Login is a name and a web password, not a token.** The password is set by the person with `abf-platform user passwd <name>`, typed twice on a real terminal (no flag, no file, no variable can stand in for the keyboard), and kept only as a scrypt hash with its own salt in `tokens.db`. A personal access token never logs into the web, and an `Authorization: Bearer` header is never looked at by the page. Five wrong tries in a minute lock that name for the rest of the minute, and 20 from one client address lock that address (if too many names are being tried at once, new tries are refused with 429 rather than forgetting a live count; behind a proxy every visitor has the proxy's address). A password is 8 to 1000 characters, in `user passwd` and at the login alike; a longer one is refused, never cut. A POST from another origin (Origin or Referer) is refused. Hashing runs in a worker thread. The cookie is signed, `HttpOnly`, `SameSite=Strict`, lasts 12 hours, and only the sha256 of its id is stored (`web_sessions`); a new password or a disabled user ends it at once. The signing key is a file in the data folder, owner-only, written whole to a temporary file and linked into place; a key file of fewer than 32 bytes stops the start.
- **Only the person who asked can press.** The page shows the summary only to the user the request was made for; anyone else sees "not yours" and no summary. The button needs the cookie, the same user, and a CSRF token made for this login and this request. A GET never changes anything; a second press does nothing more; an expired or void request cannot be brought back.
- **When the queue refuses after the yes** (the environment went offline, the run name was taken meanwhile), the request becomes void with the reason, nothing is queued, and the person asks the AI again.

The Claude Code kit adds a permission `ask` rule for `mcp__abf-platform__launch`, `mcp__abf-platform__cancel`, `mcp__abf-platform__resume`, `mcp__abf-platform__relaunch` and `mcp__abf-platform__forget` (`extensions/claude-code-kit/settings.json`). That is a second layer. It is not the gate: the gate is the platform's action layer, which refuses without a person's yes whatever a client's settings say.

**The honest boundary.** An AI that can run commands on your own machine can do what you can: type at your terminal, read your browser. The form is accepted from whatever MCP client holds your personal access token and declares forms, over HTTP as well (decided 2026-10-17: kept so that the dialog works over a network), so a client program an AI controls can answer it. Your token is the thing to protect: keep it where an AI cannot read it. An MCP session also belongs to the token that opened it: another token on the same Mcp-Session-Id is refused. The gate stops the AI clients that reach the platform only over MCP, which is what a platform shared by several people has to stop. It does not make a machine you hand to an AI safe from that AI. Likewise a path cell that names a site file in a shared read root is checked when the request is made and again, for the recorded upload paths only, on the site; a link in a shared read root that is pointed at somebody else's upload folder after the yes is not caught by either check (the same as for a read-root path sent from the terminal), so keep the shared read roots to people you trust.

### The limits of the confirmation

The question is a human gate only as far as a human sits at the terminal. A process of your own user that can write `platform.db` can write a confirmation, and a program (an AI included) that opens its own pseudo-terminal (pty) can fake a y: the agent checks the hash and that a confirmation is used once, but it cannot know who typed. The real gate is the terminal plus your Claude Code approval setting: put `abf-platform launch|cancel` on the list of commands that always ask for your approval (a permission `ask` rule), so an assistant cannot run them unseen. The confirmation, the 14-day token and the loopback-only relay rule are layers, not a substitute for that.

### Two more limits that are accepted

- **The agent does not authenticate the platform.** It sends its agent token to the address it was started with and believes what that address answers. Anything that answers `/agent/poll` on the laptop at that address can hand the agent a self-consistent confirmed job: a bundle, a confirmation row whose hash matches it, and a token. The agent checks the bundle against its own settings and the hash against the confirmation, but it cannot know who wrote the confirmation. This is the same-user trust boundary of plan Revision 2 item 11: a process running as you is trusted as much as you are. The human gate is the terminal plus the Claude Code ask rule on `abf-platform launch|cancel`.
- **A process that drives a pty can answer y.** The question reads the terminal it runs in, and a program that opens its own pseudo-terminal is that terminal. Nothing in the code can tell it from a person. Again the same-user trust boundary; again the gate is the terminal plus the Claude Code ask rule on `abf-platform launch|cancel`, so that a launch or a cancel started by an assistant stops and asks you first.

### Whose it is (spec 116)

Every environment, agent, launch and upload folder has an owner, and a caller sees and uses only their own. Over MCP/HTTP and the page that caller is the user of the token or the login; the local terminal and stdio have no caller and see everything, as before.

- **Environments and agents.** `compute_envs.owner_user_id`, `agents.owner_user_id`. `ce create --owner NAME` names the owner; without it the only user is the owner, with no user there is none, with two or more users the flag is required. `ce update --owner NAME` hands one over, and the agent bound to it goes along when it was the old owner's (refused while another environment of the old owner still uses that agent; the agent's token must then be remade with `agent-token new NAME --user NEW`). An agent token made with `agent-token new NAME --user USER` makes the agent that user's: its first hello fills an empty owner, and a token of another user is refused (403) for that name. `ce create|update` refuse an agent that has a different owner. `primary` is per owner.
- **Resume and relaunch.** Only the owner of a run may resume or relaunch it; the same words as a missing run for everybody else; the new attempt keeps the owner (see "Resume and relaunch" above).
- **Launches.** `launches.user_id` is the user whose yes made the launch, written in the same transaction as the job. A run is its owner's when the newest launch record of its name names that user. A run with no launch record, or whose record names nobody, is hidden over HTTP and the page and shown at the terminal and over stdio.
- **The same words.** What belongs to somebody else, or to nobody, answers exactly like what is missing ("not found"), for a read, a launch, a listing and a cancel. Launching or listing through an environment is refused at the queue too, when the confirmation's user is not the owner of the environment and of its agent, so a confirmation made for one cannot be turned on another's. A confirmed cancel is never reused for another user.
- **Files.** Over HTTP the samplesheet file itself must lie, links followed, inside `<uploads_root>/<your name>/`. A path cell of the samplesheet is judged as a path in `params` is (116b): one that lies in `uploads_root` (links and `..` followed) must be a file inside your own folder (the folder itself is not a file), and any other must lie under the environment's read roots, which is the environment owner's to keep (the cell may name a file on the site that this machine does not have). Why: a remote station has no folder per person (009h), so the isolation between people there is the ownership of the environment, not a folder. The cells of `samplesheet_text` follow the same rule. `list_site_files` into another user's folder under `uploads_root` is refused; other paths follow the read roots. The terminal and stdio keep the old roots. A folder per person on a remote station is not made (009h).
- **The terminal names the account.** `abf-platform launch ... --user NAME` records the launch as that user's and may use only that user's environments. Once the platform has any user it is required, and an unknown name is refused before the question. With no user at all it is left out and the record has no user. **The honest boundary: whoever has the shell can name any account** (有終端機的人可以指名任何帳號): the terminal is the administrator's, and the typed y is still the only yes. `abf-platform cancel` names no account.
- **Old data.** A platform.db made before 116 is upgraded in place (three new columns, last; `launches` keeps its order). At the start of `serve`, `mcp`, `web`, any `ce` command and `launch`, when there is exactly one user he adopts every environment, agent and launch that has no owner; with two or more users nothing is adopted and those rows are for the terminal until `ce update --owner` or a new agent token gives them one; with none nothing happens. `ce list` and `launches` print the owner, or "(none: local only)". `rebuild` still never opens platform.db or tokens.db.

#### Closing the gaps of 116 (spec 116b)

- **Paths in `params`.** Over HTTP a `params` value that looks like a path (it contains `/`, starts with `~`, or names an existing file in the caller's folder or under a read root; a `scheme://` address is not a file path) is judged with the same real-path rule as the samplesheet cells, whether the samplesheet came as a file or as `samplesheet_text` (one rule for both, since http-launch-site-samplesheet). A value that points into `uploads_root`, links and `..` followed, must lie inside your own folder; any other must lie under the environment's read roots. The terminal and stdio are unchanged.
- **A run name that is taken.** Names stay unique for everybody (the run folder is shared on the site), but an HTTP caller whose name is held by another user's launch, or by nobody's, is told only `this run name is taken; choose another`: no Slurm number, no state. Your own launch keeps the detailed words, and so does the terminal.
- **Links.** `list_site_files` resolves the path before the upload-folder check, and the agent lists what a link leads to only when that lies inside its read roots. The bundle of an HTTP launch carries `upload_paths`: the real path of every upload-area path as of the request, covered by the approved hash (the screen stays the terminal's). At job time the agent resolves them again on the site and refuses the job, with a plain reason, when one leads elsewhere or outside the recorded folder (a link swapped after the yes). That check only refuses.
- **`abf-platform runs assign RUN_NAME --user USER [--force]`** (terminal only) gives the newest launch row of a run that nobody owns to a user. A row that has an owner needs `--force`, which prints the old and the new owner. An unknown user or run is refused. It writes `launches.user_id` and nothing else.

Not here: roles or sharing inside a lab (010), per-user folders on a remote station (009h).

### Claude Desktop's custom connector (spec 009i, #117)

*(Tier A: OAuth only adds another way to prove who the caller is, like the PAT. It adds no confirmation channel.)* Claude Desktop's custom connector cannot be given a pasted token; it logs in through a browser. So the platform is a minimal OAuth 2.1 authorization server, built from the Python MCP SDK's own handlers (`mcp==2.3.0`: metadata, `/register`, `/authorize`, `/token`, `/revoke`, S256 PKCE, exact redirect match), stored in `tokens.db`:

1. The connector knows only the MCP address. An unauthenticated request gets `401` with `WWW-Authenticate: Bearer resource_metadata="<url>"` (only when `abf-platform mcp --http --public-url https://<address>` is given and the web page was started with its own `--public-url`; otherwise the challenge is a bare `Bearer`, as before). The MCP process serves exactly one thing without a token: that metadata document (`GET /.well-known/oauth-protected-resource/mcp`), which names the web page as the authorization server.
2. The authorization server lives in `abf-platform web`: `GET /.well-known/oauth-authorization-server`, `POST /register`, `GET|POST /authorize`, `POST /token`, `POST /revoke`, and the consent page `GET|POST /consent/<id>`. The issuer is the page's `--public-url` (https, or loopback http for a test on one machine). PKCE is S256 only; one scope, `mcp`.
3. **Registration** (`POST /register`) is open, because it grants nothing without a login and a click. Every client is registered as a public client (no secret kept). Redirect URIs must be https, or http to `localhost`, `127.0.0.1` or `[::1]`, with no credentials or fragment; a list with one bad entry is refused whole. Limits: the body is at most 16 KiB; `client_name` at most 100 characters; at most 5 redirect URIs of at most 512 characters each; `logo_uri`, `client_uri`, `tos_uri` and `policy_uri` are dropped; at most 200 clients that completed a token exchange (`MAX_CLIENTS`; a client that never exchanged a code is forgotten after 24 hours); at most 20 pending consent requests per client and 200 in all (over that `/authorize` answers `temporarily_unavailable`; expired requests are purged at every `/authorize`); at most 10 registrations per client address per hour (`REGISTRATIONS_PER_HOUR`; behind a proxy every visitor has the proxy's address, so the cap is then shared), and a client not used for 30 days is forgotten. The exact redirect URIs Claude Desktop registers are recorded by the manual check in `docs/TESTING.md` ("Claude Desktop custom connector (#117)"); until then the rule above is all that is enforced.
4. **Consent.** `/authorize` stores the request (10 minutes) and sends the browser to `/consent/<id>`. That page asks for the same login as the confirmation page, **name and web password only**: a PAT, an OAuth token or any `Authorization` header never logs in. It shows the connector's name, the host it will return to, and in plain words what it may do: for a connector on the form allow-list (below) that it can read your runs, ask to launch, and show you a 送出 form inside the AI app; for any other connector that each launch or cancel must be confirmed by you on this website. Allow and Deny are POSTs with the CSRF token of this login and this request; a GET never changes anything; a request is decided once. Allow mints a code (5 minutes, single use, kept as a sha256, bound to the client, the redirect, the PKCE challenge and the person who pressed). Deny returns `access_denied`. Consent is not remembered: every `/authorize` asks again.
5. **Tokens.** The access token lasts 1 hour; the refresh token 30 days and is rotated at each use. A refresh token (or a code) used a second time ends every token of that authorization. Both kinds are kept as hashes (`tokens.kind` `oauth_access` / `oauth_refresh`, `label` = the client id). `abf-platform oauth revoke <user>` ends all of one person's OAuth tokens at once (their PATs are untouched; use `pat revoke` for those). A disabled user's tokens stop working at once.
6. **At the MCP door** a PAT is tried first, then an OAuth access token; both give the same caller, so what a person sees and may do is exactly what their PAT would show. Run and agent tokens, refresh tokens, web passwords and cookies are still 401. The receiver and the agent routes know nothing of OAuth.

**The honest boundary.** An AI client that holds an OAuth token acts as that user at the MCP door, exactly as it would with the user's PAT: it is as strong as a PAT, only shorter-lived (1 hour, renewable for 30 days). What it still cannot do is say yes for the person: the consent click writes no confirmation row and queues nothing, `launch` and `cancel` over an OAuth token only make a pending request, and each send or cancel still needs the person's own 送出 (the form of their client, or the confirmation page after logging in with the web password). **The form is offered only to vetted clients.** The client's own form (the `ELICITED` channel) is shown to a PAT, to stdio, and to an OAuth caller whose client's registered redirect URIs all have the host `claude.ai` or a loopback host (`127.0.0.1`, `::1`, `localhost`): the named constant `FORM_REDIRECT_HOSTS` in `oauth.py`. Why: a code is delivered only to a registered redirect, so someone who phishes a consent for a client that redirects to `claude.ai` never receives the code, and a client that registered its own host gets no form, only the pending request and the confirmation URL, so a person has to press 送出 in the browser. Allowing a connector is not agreeing to any analysis. Claude Desktop reaches the platform from the cloud, so an end-to-end trial needs the public https address (009h); until then the flow is tried on one machine with a loopback client (see TESTING.md).

## Action layer

The platform's actions live in one place, `platform/abf_platform/actions/`: one function per action (list runs, get a run, list or get compute environments, list agents, list site files, launch, cancel, resume, relaunch, forget). The MCP tools call these functions and nothing else, and so will the web pages and the chat. A launch or a cancel (and the other writing actions, `resume`, `relaunch` and `forget`) is confirmed through one of three channels, each one object (`TERMINAL`, `ELICITED`, `PAGE`) that `actions.launch` and `actions.cancel` accept as `confirmed_by`: the terminal (`abf-platform launch|cancel` after a `y`), the form of the person's MCP client, and the confirmation page as the same logged-in user. Anything else, a string or a copy of one of them included, is refused with "no human confirmation channel" before a database is opened. The MCP tools `launch` and `cancel` call `request_launch` and `request_cancel`, which only write a pending request and ask; `approve` flips it, for the form or the page, and queues the job in the same transaction.

## Results stage: the output list

The Outputs tab of a succeeded run's results stage lists `<run folder>/results`, where `<run folder>` is the folder recorded by the newest launch of that run (the station always writes the results to `<run folder>/results`). The list comes from the action `run_outputs`, which the web page and the MCP tool of the same name call. It never waits for the site: it looks in the job table for the newest `list_site_files` job of the same compute environment and the same path. An answer already there is shown (`ready`, or `error` with the site's plain sentence); a job still queued or claimed shows as `loading`, or as `error` once its deadline has passed (nobody is waiting to mark it expired); no job at all (never asked, or cleaned up after seven days) queues one and shows `loading`. The page refreshes every 15 seconds to an address without `relist`; only the "Read again" link carries `relist=1`, which queues a new listing. A run that was not launched through the platform has no folder on record and shows `unavailable`. Another person's run answers like a missing one. The list is read-only (no confirmation page, nothing is deleted or downloaded), and no table or migration was added: the file list lives in the result of the job.

## Failed runs

`get_run` and each row of `list_runs` carry a `failure` field: `None` for a run that is not failed or lost, otherwise exactly five keys, taken the way Seqera Platform's run page shows a failed run. Nothing is sorted into causes and nothing is advised.

- `status_seqera`: Seqera's word for the run. `failed` for a failed run; `unknown` for a `lost` run (the platform has had no news and does not know how it ended); `cancelled` when a confirmed cancel of the run was sent (`cancel_requested_at`).
- `failed_tasks`: the failed tasks as the status view gives them (`name`, `exit_code`, `error_message`, `workdir` when reported), in the same order, none cut.
- `failure_reason`: Nextflow's own words, as they are, or `None`.
- `log`: the log reference the view already has, or `None`. This feature reads no log; to read one use `read_task_log`.
- `actions`: `["resume", "relaunch"]`, or only `["relaunch"]` when no task succeeded or was cached (nothing to carry over). They are the Resume and Relaunch entries of Seqera's run menu; the platform names them and sends neither: each still waits for a person's yes (section 9).

A resume here cannot yet change resources or parameters, as Seqera's Resume dialog can; the gap is `resume-edit-params`. No migration: the field is worked out when asked.

## Guidance over the URL

A person who pastes the server's address into Claude gets the "how to use it" along with the tools, with nothing to install. It comes in three forms, all made from the one folder `skills/`:

- **Instructions.** On connecting, the client hands the model the routing table of `skills/operational/SKILL.md` (which command to reach for: "I want to run RNA-seq" is a `launch`) and one fixed sentence: the seven tools are read-only, `launch`, `cancel`, `resume`, `relaunch` and `forget` only ask (nothing happens until the person says yes), and the full steps are the prompts. The text is generated from the file, never typed a second time; if the table is gone the server refuses to start rather than send an empty text.
- **Prompts.** One per flow skill (`setup`, `launch`, `runs`, `downstream`, `finish`), no arguments, holding the whole SKILL.md without its frontmatter. Clients list them as commands; how Claude Desktop shows them is checked by hand (docs/TESTING.md).
- **Skills as resources.** The same six files (the five flows and `operational`) are also served as fixed resources, `skill://<name>/SKILL.md`, type `text/markdown`, one per file, with no path template, so no path can be passed in and anything else is refused. This is the fallback for a client that shows resources but not prompts. The pinned `mcp` SDK (2.3.0) has no Skills extension API, so the resources are plain ones; when the pin moves to an SDK that has one, only the registration changes.

The text exists once, in `skills/`. The build copies that folder into the package as `abf_platform/skills/` (`platform/setup.py`; the copy is not committed), and a test builds a wheel and compares the copy with the folder byte for byte. Nothing here adds a tool, a login or a way to launch.

## nf-core module catalogue

The building blocks of the pipeline canvas are the nf-core modules. A snapshot of all of them is committed at `platform/abf_platform/data/nf-core-modules.json`; `abf_platform/catalogue.py` loads it and offers `search` and `describe`. Nothing in the tool list or the web pages uses it yet.

- Source: `nf-core/modules` at commit `5ed90b42e78410e7411e9c6bdfeff33226d6c58e`, every `modules/nf-core/**/meta.yml`, old and new format, flattened to name, path, description, keywords, tools, inputs and outputs (`versions` channels left out). A meta.yml that cannot be read is listed under `errors`, never fatal.
- Each input record carries a boolean `optional`: `true` only where the meta.yml marks that input `optional: true`, `false` when it says nothing. Output records have no `optional`.
- Regenerate (maintainer only; needs PyYAML in a throwaway environment): `PYTHONPATH=platform python -m abf_platform.catalogue snapshot --modules <nf-core/modules checkout> --sha <sha> --out platform/abf_platform/data/nf-core-modules.json`. The same sha gives a byte-identical file.
- A new snapshot is one tier A PR: the changed file, plus the new sha here and in the test.

## Composed pipelines

A composed pipeline is a graph the canvas will draw: each node is one nf-core module of the catalogue above, each edge joins an output channel of one node to an input channel number of another, and a node may carry the parameters `ext.args`, `ext.args2` to `ext.args9` and `ext.prefix` (one-line text, 1000 characters at most). There are no sub-workflows. `abf_platform/compose.py` has two pure functions: `normalize` checks the shape (known modules, real channels, no loop, no repeated edge, at most 200 nodes, 1000 edges and 256 KiB; every problem is written in Chinese and English) and puts the graph in one fixed order; `render` turns it into the text of three files, `main.nf`, `modules.json` and `nextflow.config`, byte for byte the same for the same graph, name and version. It copies no module and fetches nothing: it only says which module at which commit. An input that no edge reaches is rendered as an empty channel and listed in `open_inputs`; that is not an error here.

`abf_platform/actions/pipelines.py` keeps them: `create_pipeline`, `update_pipeline`, `list_pipelines`, `get_pipeline` and `render_pipeline`. A pipeline belongs to the person who made it (the terminal sees all); what belongs to somebody else answers like what does not exist. Every save adds a numbered version; a version is never changed or removed (the database refuses it). Saving writes only the platform's own `platform.db`: it starts nothing and needs no confirmation. There is no MCP tool and no web page for this yet; they come with spec 017e.

### Validation

`abf_platform/validate.py` checks a saved graph without running anything, and `validate_pipeline` / `get_validation` in `actions/pipelines.py` keep the latest result per version. A finding is `{node, channel, code, severity, message}`; the message is Chinese and English and says what to change. `severity` is `error` or `warning`: the result's `ok` is False when any finding is an error, and warnings are only shown. The codes are `GRAPH_STALE` (the graph no longer fits today's catalogue or its parameter rules; nothing else is checked then), `META_MISMATCH` and `TYPE_MISMATCH` (an edge joins channels that do not fit; the finding names both ends), `MIXED_SOURCES` (one input is fed by sources that cannot be mixed), `DUPLICATE_PROCESS` (two nodes would get one process name) as errors, `OPEN_INPUT` (no edge reaches an input) as an error when the node has an incoming edge and a non-meta record of that input says `optional: false`, and a warning when the input may be left out or the node is an entry node (no incoming edge; the sample sheet or parameters supply it at launch), and `PATTERN_MISMATCH` (the file patterns of an edge share no extension) as a warning. Types are compared by class (file, value, meta), not by count of elements. The check is the same for the same graph and catalogue. `get_validation` marks a stored result `stale` when the catalogue has changed since; it never checks again by itself. Only static checks exist: there is no lint and no trial run yet, and no MCP tool or web page for validation until spec 017e. Nothing is confirmed or queued, and the check writes only `platform.db`. The table `pipeline_validations` is made at first use, like the other two, so a reader makes it before it looks.

## What the platform stores

One row per kind of data. Every period below is a constant in `platform/abf_platform/` or a rule stated elsewhere in this document; where the code has no rule, the row says `no automatic deletion`. Tokens and passwords are kept only as hashes; the cookie is signed.

| What | Where | How long |
|---|---|---|
| Run index: the runs, their processes and failed tasks as Nextflow reported them | `index.db` (`runs`, `processes`, `failed_tasks`) | Rebuildable: `abf-platform rebuild` drops it and builds it again from Nextflow's records (section 5); no automatic deletion. |
| Confirmed submissions: the bundle (what was run) and the screen text (what the person approved), with the audit record of who sent it and when | `platform.db` (`confirmations`) | Until the owner forgets them with `abf-platform forget`; no clock clears a confirmed request. A void or expired request keeps its content 7 days; its audit columns stay. |
| Job rows: the queue between the platform and the agent, with a copy of what was queued | `platform.db` (`jobs`) | 7 days after the job ends. |
| Tokens, users and OAuth: sha256 of access tokens, scrypt hashes of web passwords, the connectors that registered and their logins | `tokens.db` (`tokens`, `users`, `oauth_clients`, `oauth_requests`, `oauth_codes`) | A run token 14 days; an OAuth access token 1 hour and a refresh token 30 days; a connector not used for 30 days is forgotten. Personal access tokens and users: no automatic deletion. |
| Web sessions: sha256 of a browser login's id | `tokens.db` (`web_sessions`) | 12 hours; expired rows are cleared at the next login. |
| Cookie signing key | `web_signing.key` | no automatic deletion. |
| Uploads: samplesheets uploaded for runs | `uploads` folder, one folder per user | no automatic deletion. |
| Fetched records: Nextflow's records read back from the site | `records` folder, one folder per run name | no automatic deletion. |
| Composed pipelines: a name and numbered versions of a graph of nf-core modules, per owner | `platform.db` (`pipelines`, `pipeline_versions`) | no automatic deletion; versions are never changed or removed. |
| Pipeline validations: the latest check result for each saved pipeline version | `platform.db` (`pipeline_validations`) | no automatic deletion; replaced by the next check of the same version. |

**First use.** The platform keeps the bundle and the screen text of every launch you confirm until you delete them, and you can forget a submission at any time with `abf-platform forget`. Showing this sentence to a person the first time, in the web page and in the clients, is not built yet; this document is the only place it is written.

## Where the files are

Nothing is hard-coded; every location can be changed.

| What | Default | Override |
|---|---|---|
| Run index | `${XDG_DATA_HOME:-~/.local/share}/abf-platform/index.db` | `ABF_PLATFORM_DB` |
| Token file | `tokens.db` in the same folder as the index (run tokens and agent tokens; a file made by an earlier version is upgraded in place, and its tokens stay run tokens) | `ABF_PLATFORM_TOKENS` |
| Compute environments, agents, jobs, confirmations, the hand-off record (`launches`) and the platform's instance id | `platform.db` in the same folder as the index. `rebuild` never opens it. A file made by 007 is upgraded in place, in one transaction. | `ABF_PLATFORM_STATE` |
| Nextflow's records read back by `fetch-records` | `records/<run name>/` in the same folder as the index; `rebuild` reads each as a launch folder | (moves with `ABF_PLATFORM_STATE`'s folder) |

The folders are created on first use. The `.gitignore` of this repository keeps `*.db` files out of version control.

`ABF_PLATFORM_CLOCK_OFFSET` (seconds, default 0) shifts the clock the query side uses. It exists so the tests can look at a run "three minutes later"; leave it unset. It also moves the clock by which a run token expires.

Settings that only the tests change: `ABF_PLATFORM_DEADLINE_LAUNCH` (default 300), `ABF_PLATFORM_DEADLINE_CANCEL` (90) and `ABF_PLATFORM_DEADLINE_FETCH` (180) are the deadlines in seconds of the three new job kinds, `ABF_PLATFORM_LAUNCH_GRACE` (120) is how long `abf-platform launch` waits for a late answer, and `ABF_STATION_MIN_REMAINING` (60) is how much of a launch's deadline the agent needs left before it submits.

## What it does not do

No deleting of runs, run folders or results on the site (finished job rows are pruned after 7 days, and the owner can `forget` a submission's kept content), no clean-up of `work/`, no web page but the login, the confirmation page and the read-only board, no roles, and nothing that resumes, retries or relaunches on its own (section 9: a resume or a relaunch is asked for by name and waits for a person's yes each time; the web page and the buttons for them are later, and so is the automatic resume). The agent writes only the new run folder of a confirmed launch, the `head-<N>.sh` and `tower.token` of a confirmed resume, and sends only a confirmed stop; it never removes or moves anything on the site. Compute environments of the thirteen other types are stored and never used. MCP tools that create or change environments, a way to submit from a web page, and TLS in the program itself are later features (009 and after).

## Tests

```bash
bash tests/platform_test.sh        # also run by tests/run_all.sh: every test file but two
bash tests/platform_clock_test.sh  # the other entry of run_all.sh: those two files, which check the clock, run alone
```

It builds a venv in `${XDG_CACHE_HOME:-$HOME/.cache}/abf-platform-venv`, downloads the pinned Nextflow and its `nf-tower` plugin into `${XDG_CACHE_HOME:-$HOME/.cache}/abf-platform` (every file checked against a pinned sha256), and runs `pytest` in `platform/`. The end-to-end tests run the real Nextflow, against a receiver on `127.0.0.1`, with small pipelines from `platform/tests/fixtures/flows/` that need no container.

- With `CI=true`, missing Java or Python, a failed download or a skipped test is a **failure**.
- Without `CI`, the end-to-end tests are skipped with one visible line, `E2E SKIPPED: <reason>`, and the summary counts the skipped tests. A checksum that does not match always stops the run.

The agent's tests (`platform/tests/test_station_*.py`) run in the same command: they start a real platform process and a real agent process against a **fake site**, a temporary deployment whose PATH holds stand-ins for `sbatch`, `sinfo`, `java` and `nextflow` that only log their calls (with a stand-in `ssh` that must never be called). No real cluster and no Seqera service is involved; the real cluster is only exercised by hand (`docs/TESTING.md`).
