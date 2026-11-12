# Ledger: cli-fetch-publish-figure, slice 1 (studio-connect, fetch-results)

Branch `feat/cli-fetch-publish-figure`, based on `origin/v3` 230baaa4. Slice 2 (`publish-figure`, the third line of the downstream page) is not done and
waits for `mcp-publish-figure`; TC-053 holds (no `publish-figure` anywhere in the code, the parser or the page).

## MCP client, read from the installed package (not from memory)

Installed: `mcp` 2.3.0 (`platform/constraints.txt` pins `mcp==2.3.0`, `httpx2==2.13.1`, `anyio==4.15.1`; the WSL Python used for the focused runs has
httpx2 2.14.0). Functions and attributes that `platform/abf_platform/studio_remote.py` uses:

- `mcp.Client(transport)` as an async context manager (`mcp/client/client.py`): `await client.call_tool(name, arguments)` (returns `CallToolResult`: the
  code reads `.structured_content`, else the first text block as JSON, and `.is_error`) and `await client.list_tools()` (`.tools[].name`).
- `mcp.client.streamable_http.streamable_http_client(url, http_client=...)`: the Streamable HTTP transport; a caller-made client is not closed by it.
- `httpx2.AsyncClient(headers={"Authorization": "Bearer ..."}, event_hooks={"response": [...]}, timeout=httpx2.Timeout(...))` and the exceptions
  `httpx2.TimeoutException`, `ConnectError`, `NetworkError`. The response hook is what records the HTTP status: the transport turns every non-2xx answer
  (401, 403, 502, 503 ...) into the same `MCPError(-32603, "Server returned an error response")` (only a 404 differs), so the status cannot be read
  from the exception. Without the hook a wrong token and a stopped Funnel would look the same.
- `anyio.fail_after(seconds)`: the deadline around one call (open, ask, close). `Client.read_timeout_seconds` is not applied to the `initialize` request
  (checked: a server that never answers kept the open waiting until it closed), so the deadline is ours.
- Why one MCP session per call: a long-lived `Client` has to be entered and left outside any `anyio` deadline, and a task group inside a deadline scope
  that is left earlier raises "Attempted to exit a cancel scope that isn't the current task's current cancel scope" (seen). Each call opens, asks and
  closes inside one `fail_after`; the `httpx2.AsyncClient` (and so the TLS connection) is shared by the calls of one command.
- The client tries `server/discover` first and falls back to `initialize`, so a refused attempt shows two POSTs; TC-043 counts the `initialize` ones.
- Not threads, `while True`, `asyncio.create_task` or `subprocess`: `test_cleanup_confirm` TC-068, `test_scope` TC-071 forbid them in the package
  sources (they are why the session is not kept in a background task).

## What was done, by group of test cases

| Group | Test cases | Where |
|---|---|---|
| studio-connect | TC-001..013 | `studio_remote.py` (`check_server`, `check_token`, `config_path`, `save_config`, `load_config`), `studio_cli.cmd_studio_connect`; tests `test_studio_remote.py` |
| fetch-results | TC-014..032 | `studio_cli.py` (`_fetch`, `_list`, `_read`, `_write`, `_target`); tests `test_studio_cli.py` (fake tool answers in `studio_harness.py`), TC-022/023/029 in `test_studio_remote.py` |
| R code | TC-033..038 | `studio_cli.r_snippet`, `STRINGS`; tests `test_studio_cli.py` |
| connection errors | TC-040..045 | `studio_remote.classify`, `_Session._run`; tests `test_studio_remote.py` (a real `abf-platform mcp --http` with two users and a revoked token, and a loopback stub server for 403, 404, 502, 503, 504, a timeout, a failed TLS handshake) |
| page | TC-048..053 | `web_downstream.py` (`_commands`, `STRINGS`); `test_web_downstream.py` |
| existing tests | TC-070, TC-072, TC-073 | goldens regenerated with `ABF_UPDATE_GOLDEN=1` and the diff read (two lines of the command list, the two commands, the usage line); `test_cli_contract.py` (`MATRIX` +2 leaves, `test_every_leaf_is_in_the_matrix` untouched, the set of names in its last assertion only grew), `test_cleanup_offer.py` (`COMMANDS`), `test_station_envs.py` (the set and the order string), `test_web_downstream.py` (the pinned `jupyter`/`docker` lines now pin the new lines; `:119` and the three wording tests kept and given more assertions) |
| docs | TC-074..076 | `docs/PLATFORM.md`, `docs/OPERATIONS.md`, `docs/TESTING.md`, `CHANGELOG.md`; `test_studio_docs.py` |
| safety net | TC-079..085 | `test_studio_remote.py` |
| manual | TC-039, TC-046, TC-047, TC-055 | steps in `docs/TESTING.md`; not done by the executor (see below) |

## Decisions where the plan left room (for the reviewer)

- `cli.py`: the registration line, and also the first line of the module docstring (`abf-platform: serve | web | ...`): `test_cli_usage_doc.py` fails for a
  top-level command that is not in it, and the golden of the top-level help prints it. The test was not loosened.
- The session is async (`open_session()` is an async context manager whose `call_tool(name, args)` is a coroutine), not a blocking `call_tool`; the fakes
  of the tests replace `studio_remote.open_session`. The reason is the list under "MCP client" above.
- Exit code 1 (not 0) when something is left out by a limit (files, levels, 100 MB), a file is above 25 MB, or a path is refused as unsafe: ruling P2
  lists only deliberate skips (extension, `.html`, `kind: binary`) as 0. A sub-folder that cannot be listed is a problem as well.
- The folder is created when the first file is written, not before; the line with the folder is printed after the run is known to exist, so a run that
  is not found prints only the platform's sentence (TC-029 needs the two outputs to be the same).
- With `ABF_PAT` set and no settings file there is no address to use, so it is exit 2 ("not set up"); `ABF_PAT` replaces the token only.
- Messages: Chinese by default, English when `LC_ALL`/`LC_MESSAGES`/`LANG` starts with `en`; one table `STRINGS` in each module (zh and en with the same
  keys, no banned word in zh, no CJK in en).
- The `--token` refusal: argparse would print the whole argument; `studio_cli._no_unknown_options` wraps `parse_known_args` of the two commands and
  names the unknown options only (never a value).
- `anyio` and `httpx2` are imported in `studio_remote.py` (both are dependencies of `mcp` already installed; none was added to `pyproject.toml`).
  `import httpx2` is written as `from httpx2 import ...` because `test_scope` TC-061 bans the text `import httpx`.
- `studio_cli` imports only the constant `RUN_FILE_MAX_BYTES` from `jobs` (`from .jobs import RUN_FILE_MAX_BYTES`); the command already imports `jobs`
  through `cli.py`, and TC-082 shows no database is opened.

## Environment notes

- The WSL Python used for focused runs has the user site-packages under `~/.local`; tests that give a subprocess another `HOME` fail there on
  `origin/v3` as well (`test_cli.py::test_tc035`, `test_station_envs.py::test_tc040`, `::test_nano4_keys_through_a_real_abf_platform_process`: checked
  on an export of `origin/v3` in `/tmp/base`). The full suite uses its own virtual environment.
- Another session loads the machine; `test_station_envs.py::test_tc071`/`test_tc039` failed once under load and pass alone.

## New constants

`studio_cli.py`: `POLL_SECONDS = 2.0`, `DEADLINE_SECONDS = 120.0` (one listing, or one file, may stay `loading`), `MAX_TOTAL_BYTES = 100 * 1024 * 1024`,
`MAX_FILES = 200`, `MAX_DEPTH = 3`, `TABLE_SUFFIXES = (.tsv .csv .txt .md .json)`, `HTML_SUFFIXES = (.html .htm)`, `LIST_LIMIT = 50` (skip lines printed one by one);
`RUN_FILE_MAX_BYTES` is imported from `jobs` (25 MB), not written again. `studio_remote.py`: `CALL_TIMEOUT = 30.0`, `RETRIES = 2`, `RETRY_DELAY = 2.0`,
`MCP_PATH = "/mcp"`, `CONFIG_ENV = "ABF_STUDIO_CONFIG"`, `PAT_ENV = "ABF_PAT"`.

## The settings file (`ls -l`)

From a real run of `studio-connect --no-check` (a made-up value, on the WSL Linux file system, `ABF_STUDIO_CONFIG=/tmp/lsdemo/cfg/studio.json`):

```
drwx------ 2 ... 4096 Nov 12 19:20 /tmp/lsdemo/cfg
-rw------- 1 ... 95 Nov 12 19:20 studio.json
```

## TC-055, the page (`stage=downstream`), by `scripts/dev/ui_check.py --start` through a driver that adds the page

Four screenshots (1440 and 390 wide, zh and en) were taken in `/tmp/ui-shots-downstream` on the WSL side (not in the repository, not on a synced drive).
Chromium and axe ran. Result: 0 critical; one serious, `link-in-text-block` on `p:nth-child(3) > a` (the existing "view outputs" link of the results-folder
line), at 1440 zh, 1440 en and 390 en; moderate 1 on each. **The same rows come out of an export of `origin/v3` run the same way** (so it is not new, and
the repair would touch `STYLE`, which is pinned); the maintainer decides. The page reads as intended in the zh screenshot at 1440: the sentence "平台不執行腳本 ...", the
block with the two commands, the placeholder note, the paste form. Whether the wording is to the maintainer's taste is his to say (TC-055 is manual).
`scripts/dev/ui_check.py` has no `downstream` page; it was not changed (out of scope), the driver only adds one to its tables at run time.

## Not done by the executor (manual, TC-039, TC-046, TC-047)

They need the maintainer's own computer, RStudio and a person to stop Funnel; the steps are in `docs/TESTING.md`. **UNVERIFIED**: the cross-computer run, the R
code in a real RStudio, and the three bad cases on a real link. What was run instead: the real `abf-platform mcp --http` with two users and a revoked token on
loopback (TC-029, TC-040, TC-085) and a loopback stub for the other connection failures. Package install by `pip install ./platform` on another computer
was not tried either.

## `git diff --stat origin/v3...HEAD` (taken before the last edit of this file)

```
 CHANGELOG.md                                       |   1 +
 docs/OPERATIONS.md                                 |  20 +
 docs/PLATFORM.md                                   |  76 +++
 docs/TESTING.md                                    |  21 +
 platform/abf_platform/cli.py                       |   4 +-
 platform/abf_platform/studio_cli.py                | 498 +++++++++++++++++
 platform/abf_platform/studio_remote.py             | 317 +++++++++++
 platform/abf_platform/web_downstream.py            |  26 +-
 platform/tests/__golden__/cli_help_top.txt         |  11 +-
 platform/tests/__golden__/cli_tree.txt             |   2 +
 platform/tests/studio_harness.py                   | 156 ++++++
 platform/tests/test_cleanup_offer.py               |   4 +-
 platform/tests/test_cli_contract.py                |   6 +-
 platform/tests/test_station_envs.py                |   4 +-
 platform/tests/test_studio_cli.py                  | 381 +++++++++++++
 platform/tests/test_studio_docs.py                 |  99 ++++
 platform/tests/test_studio_remote.py               | 602 +++++++++++++++++++++
 platform/tests/test_web_downstream.py              |  35 +-
 specs/cli-fetch-publish-figure/ledger.md           |  ...
 specs/cli-fetch-publish-figure/plan.md, test-case.md, test-case-overview.md: the earlier commits of this branch (not touched by the executor)
```

No line of `jobs.py`, `actions/`, `mcp_server.py`, `http_auth.py`, `store.py`, `web_board.py`, `web.py`, `abf_station/`, `.github/`, `hooks/`, the constitution,
`plugin.json` or the dependencies of `pyproject.toml` is in it (TC-084).
