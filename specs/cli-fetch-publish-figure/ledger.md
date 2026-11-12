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

## A pinned test touched that the plan did not name

`platform/tests/test_launch_static.py::test_nothing_else_in_the_new_code_sleeps_or_waits_in_a_loop` bars `asyncio.sleep(` in new code except a list of files. The plan requires
polling every 2 seconds and a 2 second retry wait, so `studio_cli.py` and `studio_remote.py` were added to that list (one line, a loosening by two names): the reviewer should
decide. Also: identifiers `site_link` renamed `site_state` (`test_refusal_visibility` TC-090 allow-lists the files that may say `site_link`); the address regex ends in `\Z`
(`tests/regex_end_anchor_test.sh`); `docs/OPERATIONS.md` does not write `abf-platform studio-connect` or `.ts.net` (`operations_doc_test.sh`, `hosted_deploy_test.sh`).

## Correction round 1 (after acceptance REJECT; the lead's rulings R1 to R12 in `plan.md`)

**Correction of an untrue statement.** The first report said that three shards of the full suite "only timed out". A timeout is not a pass: those shards did not
give a verdict, and one of the tests that ran in the suite, `test_no_duplicate_defs.py`, failed every time in 4 seconds (`studio_cli._say` was a copy of
`cli.py._say`). A shard that times out is reported as timed out, then run again alone and its own verdict is reported next to it.

| R | what changed | test |
|---|---|---|
| R1 | `_say` removed from `studio_cli.py`; `cliout.say` is called directly (no allow-list entry) | `test_no_duplicate_defs.py` (failed before, passes now) |
| R2 | `test_launch_static.py`: `studio_cli.py` and `studio_remote.py` are no longer exempt by name from the sleep scan; `PINNED_SLEEPS` pins the function that calls `asyncio.sleep` in each file and the count (1 each) | `test_the_user_side_commands_sleep_only_where_and_as_often_as_pinned` |
| R3 | `test_scope.py`: `NETWORK_CLIENT_EXEMPT` names `studio_remote.py` with its reason; an AST scan bans httpx, httpx2 and the MCP client in every other package file, `import x` and `from x import y` | `test_tc061_only_the_named_file_imports_an_http_or_mcp_client` (the scan is first tried on planted source). The imports in `studio_remote.py` stay plain `from httpx2 import ...` / `from mcp import Client` statements inside the functions that use them (lazy, so the other commands do not load the MCP package) |
| R4 | `MAX_PAGES = 200`; an empty page that names a next offset is refused; `COMMAND_DEADLINE_SECONDS = 900.0` around the whole command (what was written stays, the rest is listed as not fetched) | `test_r4_*` (3) |
| R5 | `MAX_DIRS = 100` folders listed; the rest is counted, said, exit 1 | `test_r5_*` |
| R6 | the total counts the bytes read; a negative listed size counts as 0 | `test_r6_*` |
| R7 | the single-file limit counts UTF-8 bytes | `test_r7_*` |
| R8 | `download` must equal the folder plus `name`, and `name` has no `/`; the suffix check is on that one name | `test_r8_*` |
| R9 | `MAX_NAME_BYTES = 255` per path part; a name or text that cannot be encoded, and a listing that is not a list of objects, are one-sentence refusals with exit 1 (no stack) | `test_r9_*` (4 cases) |
| R10 | `studio_remote.clean_text` (C0, C1, format, separator and surrogate characters become `?`) is applied to every word of the platform or of a file name that is printed (all `_t`/`tr` arguments and the reason texts); a name with such a character is never written (`_unsafe` now covers `\x7f-\x9f`) | `test_r10_*` |
| R11 | a table the platform calls binary: exit 1; the same `download` twice: fetched once, said, not a problem; two that differ only in case: the second is not fetched and is a problem (exit 1; my reading, the ruling says only "once and said") | `test_r11_*` |
| R12 | `trust_env` is off when the address is a loopback one, so no `HTTP_PROXY` gets the Bearer token | `test_r12_*` |

Existing tests changed, each by the ruling that names it: `test_studio_cli.py::test_tc019_*` now expects exit 1 (R11: the `.tsv` that the platform calls binary is a
problem; it expected 0); `test_tc073_*` accepts lines added to `plan.md` after the first acceptance (the lead's rulings) and still demands no change to
`test-case.md` and `test-case-overview.md`; `studio_harness.FakeSite.size_of` no longer raises for text that cannot be encoded. New file:
`platform/tests/test_studio_cli_hardening.py`.

---

# Slice 2 (publish-figure, the third line of the downstream page)

Branch `fable/cli-publish-figure`, stacked on `fable/mcp-publish-figure` (pull request 393, not merged yet): `publish_figure` is in the tree it is based on.
The first section above is slice 1 and is left as it was; TC-053 ("no publish-figure yet") held for slice 1 and is the one expectation slice 2 flips.

## What was done, by group of test cases

| Group | Test cases | Where |
|---|---|---|
| the command | TC-056, TC-057, TC-058, TC-059, TC-060, TC-061, TC-062 | `studio_cli.py` (`cmd_publish_figure`, `_publish`, `_figure_item`, `_read_local`, `_read_text`, `_caption_problem`); tests `test_studio_publish.py` |
| local limits | TC-064 | the constants `MAX_BUNDLE_BYTES`, `MAX_CODE_BYTES`, `MAX_PARAMS_BYTES`, `MAX_CAPTION_CHARS` imported from `actions/figures.py` (see the import below) |
| no yes from the command | TC-057, TC-060, TC-067, TC-068 | the arguments sent are `run_id` and `figures` (one item) only; the source holds neither `user_confirmed` nor the request id key, nor `webbrowser`; only the tool `publish_figure` is called |
| real server | TC-063, TC-065, TC-066 (and TC-040, TC-079, TC-081, TC-082 for this command) | `test_studio_publish.py`, with the real `abf-platform mcp --http` fixture of `test_studio_remote.py` (two users, a revoked token); TC-066 presses the page's button through `actions.approve(..., confirmed_by=PAGE)` as the same user, the call the page makes |
| page | TC-054 | `web_downstream._commands` (third line `abf-platform publish-figure <run id> <圖檔>`, `<image file>` in English); `test_web_downstream.py` |
| existing tests | TC-071, TC-072 | see "Existing tests touched" |
| docs | TC-077 | `docs/PLATFORM.md` ("publish-figure"), `docs/OPERATIONS.md` (the link of `publish-figure`, `--public-url`), `docs/TESTING.md` (TC-069), `CHANGELOG.md`; `test_studio_docs.py` |
| manual | TC-069 | steps in `docs/TESTING.md`; **UNVERIFIED**: not done by the executor (needs the maintainer's own computer, RStudio and a public confirmation address) |

## The one import that was a judgement

The ruling allows `from abf_platform.jobs import RUN_FILE_MAX_BYTES` and nothing that opens a database. The limits of the gallery are in `actions/figures.py`, and
importing from it runs `actions/__init__.py` first, which imports the server's action layer (`store`, `confirm`, `jobs`, `starlette` and the rest). Measured
before using it: with `ABF_PLATFORM_DB` pointing at an empty folder, `from abf_platform.actions.figures import MAX_BUNDLE_BYTES` and `from abf_platform.jobs
import RUN_FILE_MAX_BYTES` leave the folder empty (nothing is opened or created at import). It does load more code on the user's computer (and `starlette`, which
`mcp` brings anyway). TC-083 of the test cases names the exception ("片2 加 figures.MAX_*"), so `test_studio_remote.py::test_tc083_*` now allows exactly one new
form: in `studio_cli.py` only, `from .actions.figures import MAX_*` (every name starts with `MAX_`), and keeps `store`, `actions` for any other use, in
`studio_remote.py` for any use. TC-082 (the command opens no database) runs for `publish-figure` too. If the lead would rather not load the action layer on the
user's computer, the alternative is a small constants module on the server side, which is a server change this task may not make.

## Not copied from the server, said here

The filename rules (the regex, 80 characters, the type by extension), the content checks (PNG and JPEG header, the SVG deny list), the number of figures in the
gallery (`MAX_PER_RUN`) and the per-person pending limit are judged by the platform only; the command prints the platform's reason. Copying them would be a
second copy of a rule that can drift. Checked on the computer: that the figure is a regular file within `MAX_BUNDLE_BYTES` (counted in bytes, and again after
base64), that code and params are strict UTF-8 without NUL within their limits in bytes, that the caption is one line (no `Cc`, `Zl`, `Zp`) within its limit in
characters and can be encoded, and that the file name can be encoded (a lone surrogate from the command line is refused as a sentence, not a stack).

## Existing tests touched, and how

By addition, except the flips the plan and the lead named:

- `test_studio_cli.py::test_tc053_*` (slice 1 pinned "no publish-figure yet"): flipped to "registered, and the source calls `publish_figure`" (renamed
  `test_tc053_flipped_by_slice_two_...`). The test is kept, its direction is turned.
- `test_web_downstream.py` (the page): the `publish-figure not in` assertions at the two places that pinned the slice 1 page flipped to `in` with the exact line;
  `len(blocks.splitlines()) == 2` became `== 3`; `test_downstream_commands_escape_run_id` also checks the third line; the non-succeeded run now also has no
  `publish-figure`.
- `test_studio_remote.py`: TC-083 allow-list (above); TC-085 expects `publish_figure` in the set of tools the source calls; the `server` fixture yields two more
  keys (`plat`, `alice_id`).
- `test_studio_docs.py`: the slice 1 assertion "`publish-figure` is not in the guide" flipped; the example-line regex also takes `publish-figure`; TC-077 added.
- Command lists, by addition of the third name in registration order: `test_cli_contract.py` (`MATRIX` third leaf, and the set assertion), `test_cleanup_offer.py`
  (`COMMANDS`, in sorted place), `test_station_envs.py` (two places). `test_every_leaf_is_in_the_matrix` is untouched.
- Goldens `cli_help_top.txt` and `cli_tree.txt`: regenerated with `ABF_UPDATE_GOLDEN=1` and the diff read: only the command name in two lists, the usage line, one
  help row and one tree row for `publish-figure`.
- `studio_harness.py`: `FakeSite.publish_figure` and the tool name in `tool_names`.
- Not touched: `test_launch_static.py` (`PINNED_SLEEPS`: `publish-figure` adds no sleep), `test_scope.py`, the slice 1 hardening tests.

## Not done by the executor

TC-069 (manual). The full suite was not run here (the machine is heavily loaded); the verdict is the CI of the pull request.

## An observation that is not this slice's (and was not changed)

Run in one process, a test that uses the module-scoped `server` fixture of `test_studio_remote.py` and then `test_station_envs.py::test_tc071_*` (or `tc039`)
fails with `io.UnsupportedOperation: fileno` (`sys.stderr` is handed to a subprocess by the MCP stdio client). It does the same on the base commit of this
branch (`056caee5`, checked in a separate worktree), so it is not caused by slice 2. The CI shards do not put them together (`ABF_PLATFORM_LIST=1`: `test_station_envs.py`
is in another shard than `test_studio_remote.py`, and `test_studio_publish.py`, which also uses that fixture, has no file after it in its shard that starts the MCP stdio
client). If the shards are ever rebalanced it can show up; the cause was not looked for.
