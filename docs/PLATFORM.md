# The run receiver and the read-only MCP server

`platform/` holds a small program, `abf-platform`, that does two things:

1. It **receives** what Nextflow reports about a run. Nextflow's own `nf-tower` plugin sends the start of a run, its progress, a heartbeat once a minute and its end to whatever address you set as `tower.endpoint`. The receiver accepts those messages and keeps a small index of the runs.
2. It **answers questions** about that index to an AI client over MCP (Model Context Protocol), with two read-only tools: `list_runs` and `get_run`.

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

## Where the files are

Nothing is hard-coded; every location can be changed.

| What | Default | Override |
|---|---|---|
| Run index | `${XDG_DATA_HOME:-~/.local/share}/abf-platform/index.db` | `ABF_PLATFORM_DB` |
| Token file | `tokens.db` in the same folder as the index | `ABF_PLATFORM_TOKENS` |

The folders are created on first use. The `.gitignore` of this repository keeps `*.db` files out of version control.

`ABF_PLATFORM_CLOCK_OFFSET` (seconds, default 0) shifts the clock the query side uses. It exists so the tests can look at a run "three minutes later"; leave it unset.

## What it does not do

No launching, cancelling or deleting of runs, no clean-up of `work/`, no web pages or login, no roles, no connection to a cluster. Write actions, with a confirmation step, are a later feature.

## Tests

```bash
bash tests/platform_test.sh      # also run by tests/run_all.sh
```

It builds a venv in `${XDG_CACHE_HOME:-$HOME/.cache}/abf-platform-venv`, downloads the pinned Nextflow and its `nf-tower` plugin into `${XDG_CACHE_HOME:-$HOME/.cache}/abf-platform` (every file checked against a pinned sha256), and runs `pytest` in `platform/`. The end-to-end tests run the real Nextflow, against a receiver on `127.0.0.1`, with small pipelines from `platform/tests/fixtures/flows/` that need no container.

- With `CI=true`, missing Java or Python, a failed download or a skipped test is a **failure**.
- Without `CI`, the end-to-end tests are skipped with one visible line, `E2E SKIPPED: <reason>`, and the summary counts the skipped tests. A checksum that does not match always stops the run.
