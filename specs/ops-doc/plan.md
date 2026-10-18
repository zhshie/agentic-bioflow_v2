# ops-doc: docs/OPERATIONS.md

Source: issue #119 item 'Operations' (2026-10-17 architecture review). Docs only, A tier.

## Goal
A new `docs/OPERATIONS.md` for the person who runs the platform for a lab (the operator). It describes what exists on branch v3 today, not plans; anything not built yet is listed in a final 'Not built yet' section, never described as working.

## Content (each a section)
1. The processes: `abf-platform serve`, the MCP server, `abf-platform web` (read `platform/abf_platform/cli.py`, `mcp_server.py`, `web.py`, `docs/PLATFORM.md`) - what each does, its default bind address/port, and that they are separate processes.
2. One host name in front of all three, TLS through Tailscale Funnel (agreed 2026-10-17). Write it as the chosen approach; mark the actual config snippet 'Not built yet' if no file in the repo implements it.
3. Keeping them running: a service manager (systemd user units as the example). Only examples, clearly labelled examples.
4. What to back up: list every database/file the platform writes (read `store.py`, `oauth.py`, `http_auth.py`, `records.py`, `rebuild.py`); for each say whether it is rebuildable (the run index is, via `rebuild`) or must be backed up (tokens, users, OAuth, confirmations...). Name real file names/paths from the code.
5. Operator administration from the CLI: a table of the real subcommands (`token`, `agent-token`, `user add/passwd`, `pat new/list/revoke`, `oauth revoke`, `ce ...`) with one line each, taken from the argparse help strings.
6. Not built yet.

## Test (write first, must fail before the doc exists)
`tests/operations_doc_test.sh` (picked up by tests/run_all.sh like the other *_test.sh; follow the style of an existing docs test such as tests/platform_direction_docs_test.sh):
- the file exists and has the six section headings;
- every `abf-platform <subcommand>` named in the doc exists in `platform/abf_platform/cli.py` (parse the add_parser names) - so the doc cannot name a command that does not exist;
- every repo path written in backticks that looks like a repo file (contains '/' and an extension) exists.

## Out of scope
No code changes. Do not edit CHANGELOG.md, docs/PLATFORM.md or ROADMAP.md (another lane edits PLATFORM.md). No new dependencies.
