# Plan: 007b — launch, live progress and cancel through the station agent

Branch `007b-launch`, from main bd9d42b (constitution 4.0.0). Spec: `spec.md`. Research: `research.md`.

## Revision 2 (2026-10-11, after the verifier's contract review): overrides the body where they differ

The answers are numbered like the review's must-fixes. Where the review asked for a stricter rule as a should-fix, that rule is adopted.

1. **Template location.** `platform/abf_station/launch.py` is the only file that holds the head-script template and the words `sbatch` and `nextflow run`. It is the one `LAUNCH_ALLOW` entry. The CLI imports `render_bundle()` from it to build what it shows, so the text shown is produced by the same function the agent runs. No string splitting to avoid the scan (TC-049).
2. **No lost submissions.**
   - The `launch_nextflow` deadline is 300 s (`ABF_PLATFORM_DEADLINE_LAUNCH`) and covers every site call.
   - Before `sbatch`, the agent refuses if fewer than 60 s remain.
   - For `launch_nextflow` and `cancel_run`, a result that arrives after the deadline is still applied: `slurm_job_id`, `submitted_at` and `cancel_requested_at` are written to `launches`. It is not only stored in `late_result_json`.
   - An expired launch job is never handed out again.
   - When the CLI does not get an answer, it prints: "結果不明：請查國網上的 `<run folder>` 與 Slurm 工作 `nf-<run>`".
3. **Read the records on the site.** A new read-only kind, `fetch_run_records`.
   - **What it reads.** Only from a `run_folder` listed in `launches`: `.nextflow.log*`, `.nextflow/history`, and the trace file named in the log line "trace file:", which must be inside the run folder.
   - **How.**
     - Symlinks are not followed: the agent runs `find -P` and refuses a link.
     - Each file is capped at 20 MB and the reply says "truncated" when cut.
     - Nothing is written on the site.
   - **On the platform.** `abf-platform fetch-records <run>` stores the files under `<platform data>/records/<run>/`, and `rebuild` reads that folder as one more records root.
4. **The run token.**
   - It is created only when the agent **claims** the job: the poll handler makes a run token bound to the run name, stores only its hash, and sends the plain value once in the poll reply. It is never in `args_json`, `platform.db`, or a log.
   - So no token exists before `y`, and `n` leaves none.
   - It is revoked when the run's `complete` event is received, and in any case 14 days after issue.
   - On the site it lives only in `<run folder>/tower.token` (0600). `head.sh` reads it into the head job's own environment: `export TOWER_ACCESS_TOKEN="$(cat tower.token)"`.
     - FR-004 is reworded: "only in a 0600 file and in the head job's process environment; never in the script text, never on a command line, never printed".
     - The file reaches the site over stdin, as described in item 16.
   - **The preflight probe carries no token.** On lgn304 it runs `curl -sS -o - -w '%{http_code}' -x http://<relay>:18080 http://127.0.0.1:<F>/user-info` with no auth.
     - A pass needs a 401 whose header `X-ABF-Platform` equals this platform's instance id, a random id kept in `platform.db`.
     - Each hop has its own message (see 7).
5. **Account and script safety.**
   - **The account.**
     - The agent reports the deployment's `slurm_account` in `hello`; it is not a secret. The platform stores it on the agent row, and the CLI shows it.
     - The agent re-checks the bundle's account against its own settings.
     - `head.sh` exports `SLURM_ACCOUNT`.
     - If `headJobOptions` contains `-A X`, X must equal the account; otherwise the agent adds `-A <account>`.
   - **Allow-lists**, checked on both the CLI and the agent:
     - `headJobOptions` tokens must match `-c N`, `--cpus-per-task=N`, `--mem=N[MG]`, `-t|--time=D-HH:MM:SS|HH:MM:SS`, `-A acct` or `--qos=name`. Any newline, NUL, `--wrap`, `-D`, `--chdir`, `--uid`, `--gid`, `-o` or `-e` is refused.
     - Environment names: `^[A-Z_][A-Z0-9_]*$`. Values may not contain newline or NUL, and they are written to the script body quoted, never to `#SBATCH` lines.
     - Run name: `^[a-z][a-z0-9_-]{0,63}$`.
     - Pipeline: `^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$`.
     - Revision: `^v?\d+(\.\d+){1,3}$` or 40 hex characters. Branch names are refused.
     - `preRunScript` and `postRunScript`: refused in 007b when not empty ("不支援：這一片不執行事前／事後腳本"), never silently skipped.
     - `params.yaml` is produced with a YAML serializer from a dict of strings, numbers and booleans. Keys must match `^[A-Za-z_][A-Za-z0-9_]*$`.
     - `outdir` is always `<run folder>/results`. A user `outdir` is refused.
6. **Existing tests that change, by name.** Each is narrowed to allow exactly the new thing and nothing else:
   - `test_scope.py` TC-071 and `test_station_static.py` TC-084: forbidden words are allowed only in `abf_station/launch.py`.
   - `test_station_envs.py` TC-084: the help text may contain `launch` and `cancel` only as the two new subcommands.
   - `test_station_envs.py` TC-063: the subcommand list is exactly the old set plus `launch`, `cancel`, `fetch-records` and `launches`.
   - `test_station_platform.py` TC-090:
     - Column names may contain `run` only in `launches.run_name` and `launches.run_folder`.
     - `jobs.kind` is exactly {`preflight`, `list_site_files`, `launch_nextflow`, `cancel_run`, `fetch_run_records`}.
     - `launch` and `rm` still fail.
   - `store.STATE_SCHEMA` gets its CHECK updated (see 8).
7. **Forward lifecycle.**
   - Before a launch the agent runs `on_site.sh --check-forward`. If a forward is up, its port is reused. If not, `--forward` opens one: sshd chooses the port, and it is written to `<deployment>/_personal/forward_port` (0600, written by `on_site.sh`, read by the agent).
   - The agent writes the same port to the site's `<storage_root>/_relay/forward_port` (0600) over stdin. The relay reads that file for each request.
   - A forward is shared by every run while the ControlMaster lives. Two launches use the same port.
   - `abf-station unforward` (manual) runs `--unforward`, which sends `-O cancel` and deletes both files. Nothing automatic.
   - The relay fails closed when the file is missing, unreadable, malformed, or out of range.
   - A relay process started before this rule answers 403 to loopback; the preflight says "請重啟 relay：`bash scripts/egress_ctl.sh restart`" (or the existing restart command).
8. **Migration.** `store.py` migrates an existing `platform.db`. If the `jobs` CHECK lacks the new kinds, it rebuilds the table in one transaction: create the new table, copy the rows, drop the old one, rename. Existing rows are unchanged. Another check is added: `CHECK (kind NOT IN ('launch_nextflow','cancel_run') OR confirmation_id IS NOT NULL)`, and `confirmation_id` is UNIQUE (TC-048).
9. **What a cancel shows (decided by developer-agent, under principle 2).** `get_run` shows what Nextflow reported: after a SIGTERM that is "failed", with Nextflow's own reason. As a fact, `abf-platform launches` lists "取消請求已於 T 送出" from `launches.cancel_requested_at`. The same command also lists "已送出，尚未收到 Nextflow 事件" for runs with `submitted_at` set and no index row (should-fix 17). SC-003 is reworded to match. The maintainer sees this wording in the B-tier review.
10. **An honest confirmation screen.**
    - Every displayed value has its control characters escaped visibly (`\r`, `\x1b`, `‮`, …) and is shown with a line prefix, so no line can hide another. NUL, CR, ESC and bidi controls in samplesheet cells or params are **refused** when the bundle is built.
    - The spec's list gains "主控工作腳本全文".
    - `y` and `Y` both count as yes; spec and plan are unified.

**Should-fixes adopted.**
- **11.** `docs/PLATFORM.md` states the limits of the confirmation:
  - a same-user process that can write `platform.db`, or an AI that drives a pty, can fake a `y`;
  - the human gate is the terminal plus a Claude Code `ask` rule on `abf-platform launch|cancel`.
  The agent also keeps the confirmation ids it has used in memory and refuses a repeat. A replay is also stopped by the run folder already existing.
- **12.** The relay's loopback rule:
  - plain HTTP only, never CONNECT;
  - host exactly `127.0.0.1`;
  - port compared as an ASCII digit string equal to the file's content;
  - path must start with `/trace/` or equal `/user-info`, checked after normalising with no `..` and no `%2e`;
  - one request per connection: the relay closes the connection after the response.
- **13.** The real-Nextflow end-to-end test (TC-024) uses the `NXF_OPTS` taken from the generated `head.sh`.
- **14.** Real nf-tower 1.17.5 recordings are made, with failures and retries. `failed_tasks` keys are robust when `attempt` is missing. The message gap is measured against `LOST_AFTER_SECONDS` (TC-027).
- **15.** Cancel checks `squeue -h -j <id> -o '%j|%u|%Z'`: the name must be `nf-<run>`, the user must be the deployment's `site_user`, and the folder must be the run folder. `scancel` takes exactly one decimal id. The reply says "取消請求已送出".
- **16.** Files are written in one site call: a tar stream over stdin, unpacked with `umask 077; mkdir <run folder> && tar -x -C <run folder>`, after a `mkdir -p <workDir>/runs`. The `mkdir` without `-p` is the existence check. `Site.call` gains `input=`.
- **17.** `docs/SEQERA_PARITY.md` lists what is not built yet: the per-task list, CPU and memory, logs and reports, and a queued state.
- **18.**
  - In `reach: ssh` the platform URL must be loopback, otherwise the launch is refused before the question.
  - `reach: local` opens no forward.
  - `launches.run_name` is UNIQUE.
  - `squeue` is called once per cancel and never anywhere else.

### Revision 2 addendum (second contract round, adopted)

- **a.** A pipeline has two parts, and each must match `^[A-Za-z0-9][A-Za-z0-9_.-]*$`. Neither part may be `.` or `..` (TC-011).
- **b. Stale text in the body.** Where the body below disagrees with Revision 2, Revision 2 holds. Specifically:
  - The Safety Net row: the token is kept in the head job's environment, as item 4 says.
  - §2: a single tar over stdin plus `mkdir` without `-p`, as item 16 says. `shlex.quote` is used only for the values in the script body; `#SBATCH` lines take only allow-listed tokens.
  - §4: the `squeue` format is `'%j|%u|%Z'`.
- **c.** The preflight first connects straight to `127.0.0.1:<F>` on the login node:
  - connection refused means "反向通道沒開";
  - connected but no answer, or a 502 through the relay, means "平台沒有回應".
  The two messages differ (TC-037).
- **d.** When the agent answers `refused` or `error` for a claimed `launch_nextflow`, the platform revokes that job's run token (TC-020).
- **e.** The agent reports `slurm_account` in `hello`, and it is stored on the `agents` row. This does not conflict with the Safety Net rule that personal details live in the deployment's settings area: an account id is not a credential, and the confirmation screen has to show it anyway.
- **f. Task list additions.**
  - The platform instance id: random, stored in `platform.db`, the same after a restart.
  - The `X-ABF-Platform` header on 401 replies.
  - The run token is bound to the run name: a token for A cannot `create` B (TC-039).
- **g.** The relay's path check looks at the path only and ignores the query string. `/agent/poll?x=/trace/` is refused (TC-032).
- **h.** `docs/PLATFORM.md` says that `fetch-records` sends the contents of Nextflow's logs (paths, params) to the platform.

## Tier

**B with a C part.**
- Launch and cancel are new behaviour the user sees: B. The PR is opened and he looks at it before the merge.
- The relay rule in FR-005 widens the egress net by one loopback target: C. The PR description asks about it separately.

## Constitution Check

| Rule | Answer |
|---|---|
| **1** | The alternatives, and why each one does not serve: <br>• Seqera's launcher and Tower Agent are closed and Seqera-only. <br>• Nextflow cannot submit its own head job. <br>• No maintained tool submits a head job through a user's ControlMaster. <br>Our pieces reuse: <br>• `scripts/on_site.sh` for every site command and the forward; <br>• the existing relay; <br>• `configs/sites/nchc.config` and `nchc-ce.json.in`; <br>• Nextflow's own nf-tower for progress; <br>• 008's receiver and rebuild. <br>Every new file gets its `# Not …` / `# Nothing existing:` header. |
| **2 (4.0.0)** | `launch_nextflow` is the single submission path. It is listed in `LAUNCH_ALLOW`, with the test that refuses an unconfirmed launch. <br>• State: run status comes only from nf-tower events or from rebuild of the run folder. The platform keeps a hand-off record (FR-009), never a status. <br>• Daemons: none. The forward is an option of the existing ControlMaster, and the relay already runs. <br>• `cancel_run` calls `scancel` and `squeue` once each. It does not submit, so it is not in `CMDS`, but it is still a write and has its own confirmation (FR-001). |
| **3** | Paths come from the CE config (`workDir`) and from the deployment settings (`slurm_account`, `storage_root`). Nothing is hard-coded. The account is never a literal. |
| **II-4** | Only Slurm. No new site adapter. NCHC specifics (box table, proxy) stay in `configs/sites/`. |
| **V** | WSL or Linux only, as in 007. |
| **VI** | Nothing fails quietly. Every refusal and failure names what is left on the site. A broken channel before launch is a refusal with the fix; one after launch shows as 「失聯」 (lost), and rebuild is offered. |
| **Safety Net** | The launch is shown in full and waits for `y` (it meets the launch rule). Credentials: the run token goes into a 0600 file and is never in the script, never in an environment variable and never printed. No delete of `rawdata/`, `results/` or `analysis/`: the run folder is new, and an existing folder is refused. |
| **Waiting principle** | "Every platform write tool refuses without the user's confirmation step" gets its first two checks here, for launch and cancel. The ROADMAP row is noted; it is not moved into the constitution in this PR. |

## Design

### 1. Confirmation (FR-001, US1)

The new CLI commands are `abf-platform launch` and `abf-platform cancel`.

**Launch**
1. `launch` builds the full **launch bundle**:
   - CE;
   - run name;
   - run folder = `<workDir>/runs/<run-name>`;
   - samplesheet text, `params.yaml` text and `nextflow.config` text (CE `nextflowConfig` + site config + proxy);
   - head script text;
   - pipeline;
   - revision, which must be a tag or a commit and never a branch.
2. It prints every part of the bundle in full.
3. It asks `確定送出？(y/N)` on the **controlling terminal**. If stdin is not a tty it refuses, and only `y` / `Y` counts as yes.
4. On yes, it writes in one transaction:
   - a `confirmations` row: `id` = random 128-bit, `sha256` of the canonical bundle JSON, `kind`, `created_at`, `used_at` NULL;
   - the job, whose args are `{bundle, confirmation_id, bundle_sha256}`.

**Who can create a confirmation**
- No HTTP route and no MCP tool can create a confirmation or queue a `launch_nextflow` or `cancel_run` job. Tests check both.
- Queuing through `jobs._enqueue` with those kinds requires a confirmation row.

**What the agent checks before it writes anything**
- `bundle_sha256 == sha256(canonical(bundle))`;
- the job carries a `confirmation_id`;
- the platform's `/agent/poll` reply includes the confirmation row, and its sha256 matches;
- the confirmation is used once: `poll` marks it used when the job is claimed.

A mismatch or a missing value is a refusal, and `sbatch` is never called.

**Cancel** works the same way. Its bundle is `{run_name, slurm_job_id, run_folder, agent}`.

### 2. Launch on the site (FR-002/003/004, US2)

New agent module `platform/abf_station/launch.py`. It is the one `LAUNCH_ALLOW` entry, and its test is `platform/tests/test_station_launch.py::test_unconfirmed_launch_is_refused`.

The handler, in order:
1. Re-validates every path with `rules.py`: the run folder must be inside `workDir`, and the absolute paths in the samplesheet must be inside the allowed read roots.
2. `test -e <run folder>`. If the folder exists, the job is refused.
3. `mkdir -m 700 <run folder>`.
4. Writes each file through `on_site.sh` with stdin, as `umask 077; cat > <file>`. The content goes over stdin, never on a command line. Files written: `samplesheet.csv`, `params.yaml`, `nextflow.config`, `tower.token` (0600) and `head.sh`.
5. `sbatch <run folder>/head.sh`, exactly once.
6. Parses `Submitted batch job N`.

`head.sh`:
- header: `#SBATCH -D <run folder> -J nf-<run> --no-requeue -p <headQueue>`, then `headJobOptions`;
- exports: `export TOWER_ACCESS_TOKEN=$(cat tower.token)`, the proxy variables, `NXF_OPTS`, and `NXF_SINGULARITY_CACHEDIR` from the CE config (`environment`);
- then: `nextflow run <pipeline> -r <rev> -name <run> -params-file params.yaml -c nextflow.config -with-tower <endpoint>`;
- no `NXF_LOG_FILE`, no `-log`, and `-with-trace` only when the pipeline does not write its own trace.

Every value in `head.sh` is quoted with `shlex.quote`.

The run token is issued per launch, as a run token (008 kind), and its hash is stored. The token reaches the site only inside `tower.token`.

After `sbatch`, the agent returns `{slurm_job_id, run_name, run_folder}`. The platform stores this as the hand-off record (a new `launches` table: `run_name`, `slurm_job_id`, `run_folder`, `ce`, `agent`, `confirmed_at`, `submitted_at`, `cancel_requested_at`) and nothing about status.

Failure after `mkdir` reports exactly which files exist and leaves them in place. The user decides; the agent never deletes.

### 3. Live progress path (FR-005/006/007, US3)

The endpoint is `http://127.0.0.1:<F>`, as seen from lgn304. Nextflow on the compute node reaches it through the relay. The head job's JVM uses `-Dhttp.proxyHost=<login host> -Dhttp.proxyPort=18080 -Dhttp.nonProxyHosts=` (empty, so loopback is proxied too), and the relay forwards plain HTTP to `127.0.0.1:<F>`, which is the reverse forward to the platform.

**`scripts/on_site.sh`** gains `--forward <local port>` and `--unforward`.
- It runs `ssh -S <ControlPath> -O forward -R 127.0.0.1:0:127.0.0.1:<local port>` and prints the remote port that sshd chose.
- The port is written to `<deployment>/_personal/forward_port`, mode 600.
- `--check-forward` reports whether the forward is up.
- Behaviour stays the same for `reach: local`, where the platform and the site share a host.

**`scripts/nf_relay.py`** gains one rule.
- A plain-HTTP request to `127.0.0.1:<port>` is allowed only when `<port>` equals the integer in the deployment's `_relay/forward_port` file, which the agent writes on the site with mode 600.
- No other loopback target and no CONNECT to loopback are allowed.
- **This widens the egress net (C).** The PR asks the maintainer.

**Preflight for launch** (inside `launch_nextflow`, before step 3 of section 2): the agent runs, on the login node, `curl` through the relay to `http://127.0.0.1:<F>/user-info` with the run token. It must get a 200 from *this* platform. If it does not, the launch is refused and the reply says which hop failed: forward, relay rule or platform.

**FR-007.**
- Record real nf-tower 1.17.5 payloads: pin Nextflow 25.10.4 with nf-tower 1.17.5 by sha256 in `tests/platform_test.sh`, the same way 008 did.
- Add receiver tests that `create`, `begin`, `progress` and `complete` from 1.17.5 are accepted, and that per-process counts and failed tasks appear in `get_run`.
- Fix the receiver if a field differs.

### 4. Cancel (FR-008, US4)

The `cancel_run` handler:
1. Re-reads the `launches` row the bundle names.
2. Runs `squeue -h -j <id> -o '%j %u'` once. The name must equal `nf-<run>` and the user must equal `site_user`. Anything else is a refusal.
3. Runs `scancel <id>` once.

No other `scancel` exists anywhere. The 007 refusal tests for `scancel` as a **kind** stay: the kind `scancel` is still refused, and only `cancel_run` with a confirmation can cancel.

### 5. Tests and checks

- `tests/no_second_run_state_test.sh`: one `LAUNCH_ALLOW` entry for `platform/abf_station/launch.py`.
- `platform/tests/test_scope.py` TC-071 and `test_station_static.py` TC-084 (4.0.0 record): they forbid `sbatch` and `subprocess` in platform code. Narrow them so they allow exactly the `LAUNCH_ALLOW` file, and only `sbatch` through `on_site.sh` (no `shell=True`, no `os.system`). Every other file stays forbidden.
- New test files: `test_station_launch.py`, `test_station_cancel.py`, `test_receiver_nf2510.py`, and a fake site that logs `sbatch`, `squeue`, `scancel` and `curl`.
- The confirmation tests drive the CLI through a pty: no tty, `n`, Enter, `y`, a tampered bundle, a replayed confirmation, and a forged job pushed by a fake platform.
- Manual (`docs/TESTING.md`):
  - US5 acceptance on NCHC with the 2026-09-20 settings;
  - SC-003, cancel a small test run;
  - one forward and relay probe.

### 6. Docs

- `docs/PLATFORM.md` §9 Launch and cancel, covering the confirmation, the run folder, live progress, the channel and the 8-hour limit.
- `docs/SEQERA_PARITY.md`: launch, progress and cancel rows.
- `docs/ROADMAP.md` Stage 1: 007b done when merged.
- `docs/PITFALLS.md`: two entries, "GatewayPorts off on NCHC: reverse forward is loopback-only (measured 2026-10-11)" and "Seqera launcher scripts hold the token in a 755 file".

## Tasks (executor, in order)

1. Record the nf-tower 1.17.5 fixtures; receiver tests. RED, then GREEN.
2. The confirmations and launches tables; the CLI `launch` and `cancel` with the tty confirmation; the enqueue guard. RED, then GREEN.
3. Agent `launch.py` and `cancel_run`; the fake site. RED, then GREEN.
4. `on_site.sh --forward/--unforward/--check-forward`; the `nf_relay.py` loopback rule with tests; the launch preflight probe. RED, then GREEN.
5. Check updates (`LAUNCH_ALLOW`, TC-071, TC-084), docs and the full suite.

## Not in this plan

- Web confirmation and MCP write tools (009).
- Resume and retry.
- Cloud launch.
- Keeping the forward alive past ControlPersist.
- NCHC M6.
