# Plan: 007-station-agent (slice 1: connection, compute environments, read-only jobs)

## Revision 2 (2026-10-11, after verifier CONTRACT review): supersedes everything below where they conflict

### Constitution Check

- **Principle 1.**
  - Named alternatives:
    - Seqera Tower Agent: its protocol is undocumented and it talks only to Seqera.
    - GitHub Actions runner and Buildkite agent: each is bound to its own service.
    - Celery and RQ: they need a separate broker. A single SQLite table is enough for two read-only job kinds.
    - SSH and site access: `scripts/on_site.sh` is reused, not rewritten.
  - Every new `.py` file carries the header line. The header check (008 TC-070) is extended to cover `abf_station/`.
- **Principle 2.**
  - The agent's poll loop is not a monitoring daemon. It watches no run, reports no run state, and persists nothing.
  - The `jobs` table is not a run state machine. Only `preflight` and `list_site_files` may be stored in it, enforced by a CHECK constraint.
  - Launching, and any job that touches a run, comes in 007b together with a constitution amendment.
- **§II-4.** The 13 unsupported types are stored data only. No type-specific code runs for them, no cloud library or CLI is imported or called, and preflight and listing refuse them at once. That is recording settings, not writing a second site adapter.
- **Principle 3.**
  - Platform files follow 008's location rule.
  - The agent's token file defaults to `<deployment>/config/agent.token`.
  - Read roots come from the deployment's `storage_root` setting plus the CE's work dir and launch dir. No other path is hard-coded.
- **Principle V.**
  - The agent runs in WSL or Linux bash. It is a separate program, not the plugin.
  - Started on native Windows or Git Bash, it refuses and names the missing capability (bash plus WSL), not a folder.
- **Principle VI.** Every failure is named: a skipped folder, an offline agent, a timed-out job, a truncated listing, an unsupported type. Nothing is silent.
- **Safety Net scope.** The agent is a new path that does not pass through any hook. Its only guard is its own allow-list, enforced twice (at enqueue and in the agent), plus TC-060–064. The docs say so.
- **Credentials.**
  - Credentials stay in the agent's deployment config. The platform stores only names.
  - The token file must be 0600. It is refused when it sits on a Windows drive mount (drvfs/9p, read from `/proc/mounts`), because permission bits are not trustworthy there.

### Fixes M1–M8

1. **Storage.** CEs, agents and jobs live in a new `platform.db` next to the index. `rebuild` never opens it, the same as `tokens.db`. `tokens.db` gains `kind` (run or agent) and `agent_name` columns through an explicit migration (`ALTER TABLE` when missing). An old 008 file keeps working and its tokens are `run` (TC-009).
2. **Writers.** The receiver process (`serve`) answers the agent endpoints. The CLI and MCP processes enqueue jobs into `platform.db`; nothing else writes it. `mcp_server.py`'s header is rewritten from "never opens the index for writing" to "never writes the run index; it may enqueue read-only site jobs". `readOnlyHint` means read-only toward the site and toward runs.
3. **Binding.**
   - Each CE has an `agent` field (an agent name). Jobs for a CE go only to that agent.
   - An agent token is minted for one name, and `hello` must present that name (TC-011, TC-018).
   - Polling is atomic, so a job is claimed once (TC-017).
4. **Shell safety.** `on_site.sh` joins its arguments into one string, so "no string shell" is replaced by two locks:
   - The platform validates at create and update time. Work dir and launch dir must be absolute, with no `..` and no shell metacharacters. Queue names must match `^[A-Za-z0-9_.-]+$`.
   - The agent validates again before running.
   - Every argument the agent hands to `on_site.sh` is passed through `shlex.quote` after validation.
   - Canary tests cover this (TC-029, TC-055, TC-062).
5. **How the agent finds things.**
   - `on_site.sh` is located from the agent's own install: the repository root is the parent of `platform/`, set by `--plugin-root` with that as the default. It is never located from the current directory.
   - The deployment's settings are passed to `on_site.sh` as `LAB_SETTINGS_FILE=<deployment>/config/<settings file>`.
   - A `--deployment` with no settings file is refused before polling (TC-083).
   - A new helper in `platform/tests/helpers.py` builds a temporary deployment with `reach: local`, or `reach: ssh` with `ON_SITE_SSH_BIN` pointing at a fake ssh. The "connection not open" case uses `reach: ssh` with a fake ssh whose `-O check` fails (TC-045, TC-046).
   - `ON_SITE_DRY_RUN` is used only for the command-vocabulary test (TC-050).
6. **Busy agent.**
   - While a job runs, a small heartbeat thread in the agent sends a beat every H = 20 s, so a busy agent stays online (TC-023).
   - Each site call runs with `ON_SITE_TIMEOUT=20`.
   - Job deadlines: `preflight` 180 s, `list_site_files` 60 s. A caller waits up to the job's deadline, then gets "the agent did not answer".
   - The job is marked `expired`. It is never handed out afterwards, and a late result is recorded as late and changes nothing (TC-019).
   - The wait and deadline values are configurable for tests and are written in `docs/PLATFORM.md`.
7. **Preflight is non-destructive.** The work-dir check is `test -d` plus `test -w`. Nothing is created on the site (TC-048).
8. **Named changes to 008 tests.** Only these assertions change. Each becomes stricter or wider in coverage, never weaker (TC-094):
   - `test_mcp.py` exact tool count (TC-024 and TC-025 of 008): two tools become six, each still `readOnlyHint`, and no input field may be named command, cmd, script, kind, shell or args.
   - `test_scope.py` TC-061 word list: only words that platform-side CE code must contain may be dropped, such as `ssh`, `station` and `sbatch` in config field names. A new, stricter scan of `abf_station/` is added.
   - `test_scope.py` TC-070 file set: widened to include `abf_station/`.
   - `test_scope.py` TC-071: stays as it is for `abf_platform`. There is no `while True`, thread or subprocess there; the long-poll is an asyncio deadline loop.

### Should-fix decisions

- **Credential detection.**
  - It runs on `environment[{name,value}]` by the `name` value, and on the full text of `nextflowConfig`, `preRunScript` and `postRunScript`.
  - Patterns: PEM headers, `AKIA`/`ASIA` ids, `aws_secret_access_key`, `export <SECRETNAME>=`, and the platform's own `abf_` tokens.
  - A rejected value is never echoed back.
  - False positives are tested (TC-036, TC-037).
- **Unsupported types.** They have no per-type field schema; only common-field validation and the credential scan apply. The executor reads Seqera's public API docs and records each type's `platform` identifier in `research.md`, and `docs/PLATFORM.md` uses the same identifiers. Seqera Compute is refused with "Seqera's own hosted service, no counterpart".
- **Primary.** Only a CE that is neither `unsupported` nor `disabled` can be made primary (decision 1).
- **Preflight after create.** It runs automatically when the CE's agent is online. Otherwise the CE stays `creating` with the reason (TC-025, TC-026). `abf-platform ce update` exists (TC-038).
- **Read roots.** The roots are the CE's work dir and launch dir plus the deployment's `storage_root`. Prefix checks use path components, not string prefixes (TC-053).
- **Token file.** The default is `<deployment>/config/agent.token`. It must be 0600, and it is refused on drvfs/9p mounts (decision 2). The mount table path (default `/proc/mounts`) can be overridden by `ABF_STATION_MOUNTS_FILE`, documented in `docs/PLATFORM.md`, so tests can stage a 9p/drvfs entry (TC-097); a missing or unreadable mount table fails the check, never skips it.
- **Non-local `http://`.** The agent refuses to start against a non-local `http://` URL; localhost and 127.0.0.1 are allowed (decision 3, TC-021).
- **Disclosure.** `docs/PLATFORM.md` states that listings send file names, sizes and modification times to the platform and to the model the user chose. This is the ROADMAP's "Data stays local" note.
- **Limits.**
  - A listing is capped at 500 entries and says when it is truncated.
  - Job results are pruned after 7 days at enqueue time, never on a read.
- **Long-poll.** It uses `asyncio.sleep`, polls `platform.db` every 0.5 s and does not hold a connection open between polls. The agent's HTTP read timeout is longer than the poll time.
- **No-listen check.** Socket inodes from `/proc/<pid>/fd` are matched against `/proc/net/tcp` and `/proc/net/tcp6` (TC-012).
- **Packaging.** `pyproject.toml` lists the `abf_station` package and the `abf-station` script.
- **Docs.** ROADMAP and SEQERA_PARITY edits keep the strings `tests/platform_direction_docs_test.sh` checks: the `| 4 | **Cloud compute**` row start, the completion column and the "(13 items)" heading. Stage 4 is annotated "merged into Stage 1", not removed.

Tier A: this slice adds a spec. Plugin hooks, scripts, skills and commands are not modified; `scripts/on_site.sh` is called, never edited. Spec: `spec.md`. Research: `research.md`.

## Shape

Everything lives in the existing `platform/` package (008), with the same Python, venv, constraints and test wrapper.

| Module | Job |
|---|---|
| `abf_platform/agents.py` | Platform side of agents. `abf-platform agent-token new <name>` mints a token (stored as a hash in `tokens.db`, kind=agent, revocable with `agent-token revoke`). Endpoints: `POST /agent/hello` (name, version), `POST /agent/poll` (long-poll up to 25 s (asyncio deadline loop, Revision 2), returns at most one job), `POST /agent/result/{job_id}`. Last contact is recorded on every call. Online or offline is derived at query time: offline after 3× the heartbeat interval (heartbeat 20 s, so 60 s). |
| `abf_platform/compute_envs.py` | CE store and validation. Seqera's shared fields plus per-type `config` schemas for all 14 types, with field names following Seqera. Statuses: `creating`, `available`, `invalid`, `unsupported`, `disabled`. One primary at most. A credential-looking value is rejected (FR-005), using the same name rule as 008's `scrub_params` plus value patterns: PEM headers, `AKIA`/`ASIA` keys, `aws_secret_access_key`. CLI: `abf-platform ce create/list/primary/disable/preflight`. |
| `abf_platform/jobs.py` | Job queue table (id, agent, kind, args, state, result, created/finished). Kinds allowed: `preflight`, `list_site_files`. Anything else is refused at enqueue as well as at the agent, so there are two locks. Deadlines per Revision 2 item 6 (preflight 180 s, list 60 s); expired jobs are never handed out. |
| `abf_station/` (new sibling package, same `platform/` folder) | The station agent: `abf-station run --platform URL --token-file F --deployment <root>`. It loops hello → poll → run → result. Backoff is bounded, and on 401 it prints the reason and exits (US1-3). It runs only the built-in handlers. Every site command goes through `scripts/on_site.sh` of the deployment named by `--deployment`; the agent never calls ssh itself. The token file must be 0600 (Windows: ACL, measured the way `scripts/settings.sh` and `tests/windows_privacy_test.sh` do), or the agent refuses to start. |
| `abf_station/handlers.py` | `preflight(ce)` runs every check and reports all of them: reach (`on_site.sh --check-reach`), work dir writable, `sbatch`/`squeue`/`sinfo` present, `java -version` ≥17, `nextflow -version`, head queue present in `sinfo`. `list_site_files(ce, path)` validates the path before calling `on_site.sh` with `ls`/`stat`: it must be under work dir, launch dir or an allowed read root in the CE config, with no `..` and no glob or shell metacharacters. Arguments are validated and `shlex.quote`d before `on_site.sh` (which joins them into one string) — see Revision 2 item 4. |
| `abf_platform/mcp_server.py` | Adds the read-only tools `list_compute_envs`, `get_compute_env`, `list_agents` and `list_site_files`, all `readOnlyHint` true. `list_site_files` enqueues a job and waits for its result. |

Each new `.py` file names its alternative in the header, as principle 1 asks (e.g. "Not Seqera Tower Agent: undocumented protocol, talks only to Seqera").

## Reuse

- `scripts/on_site.sh`: connection, session cap, WSL bridge, timeouts. Its `reach: local` mode, and the `ON_SITE_SSH_BIN`/`ON_SITE_DRY_RUN` seams, are what the tests use.
- `scripts/settings.sh`: the deployment settings that `on_site.sh` reads.
- 008's token store, `status` clock and `scrub` helpers. These are extended, not copied.

## Tests (red first)

- **Unit tests:**
  - token kinds: an agent token cannot post trace events and a run token cannot poll;
  - online/offline status, using a fake clock;
  - CE validation for all 14 types, with every non-Slurm type `unsupported`;
  - credential-looking values rejected, and canary scans of the database bytes;
  - the primary rule;
  - job-kind allow-list at both ends;
  - path validation;
  - 401 makes the agent exit.
- **End-to-end with a fake site:**
  - Run the real agent process against the real receiver, both on 127.0.0.1.
  - The deployment uses `reach: local`, and fake `sbatch`/`squeue`/`sinfo`/`java`/`nextflow` are put first on PATH.
  - Preflight passes; a missing `sinfo` gives `invalid` with every failure listed.
  - `list_site_files` returns real entries of a temp work dir.
  - `rm`, `scancel`, unknown kinds and paths outside the roots are refused.
  - When the agent is killed, it is shown offline after 60 s, checked with the fake clock.
- **Network direction:** the agent process opens no listening socket (checked with `/proc/<pid>/net` or `ss`, plus a static scan for listen/bind in `abf_station`).
- **Manual (`docs/TESTING.md`), on real NCHC:** open the master the old way, start the agent, create the Slurm CE, run preflight, then `list_site_files` on rawdata, then attempt a delete job, which must be refused.
- **Wrapper:** `tests/platform_test.sh` runs everything, and CI rules are unchanged (no skips under `CI=true`).

## Docs

- `docs/PLATFORM.md`: new sections for the agent and for compute environments.
- `docs/SEQERA_PARITY.md` §F: a per-type verdict table (Have / Modelled, needs a real account / Not needed: Seqera Compute).
- `docs/ROADMAP.md` Stage 1: "station agent + compute environments (Seqera model, all types; NCHC first)". Stage 4 is marked "merged into Stage 1".

## Risks

- **`on_site.sh` from Python under WSL vs. Git Bash.** The agent runs in WSL (bash available). Native Windows is out of scope for this slice; say so in the docs.
- **Long-poll through the 008 server.** It holds a request open for up to 25 s. The uvicorn worker model must still serve the trace endpoints at the same time; test this with a concurrent progress post while a poll is held.
- **`on_site.sh` needs a deployment root and settings.** The tests create a temp deployment with `scripts/settings.sh` the way existing tests do (reuse their helper).

## Done when

The contract cases pass, the whole suite is green in WSL and CI with nothing skipped, the verifier ACCEPTs, and the docs are updated. The manual NCHC run waits for the maintainer to open the connection.
