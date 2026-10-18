# install-doc: docs/INSTALL.md

Source: issue #93 item 7 (harness kits + docs/INSTALL.md). This task is the DOCS part only, A tier. The kit files themselves (root `.mcp.json`, a Codex root plugin.json / mcp.json, a Claude Desktop connector) are a later task; the doc lists them under 'Not built yet' unless a file in the repo already implements them.

## Goal
A new `docs/INSTALL.md` for a lab member: how to connect each first harness to the lab's abf platform. Maintainer decision 2026-10-15 (in #93): users add one MCP URL and nothing else; first harnesses Claude Desktop, Claude Code, Codex.

## Content
1. What you need: the platform's address from the operator, and how you authenticate (OAuth login for Claude Desktop connectors; a personal access token, `abf-platform pat new` run by the operator, for the others). Read platform/abf_platform/oauth.py, http_auth.py, docs/PLATFORM.md, docs/MIGRATION.md, docs/OPERATIONS.md for the real flows; use only what exists.
2. Claude Code: `claude mcp add` with the HTTP URL and the PAT header, exactly as docs/MIGRATION.md / PLATFORM.md already state it; the `ask` permission rule mentioned in #93 only if the repo already ships it, else Not built yet.
3. Claude Desktop: add a custom connector with the URL; OAuth login; what the person sees on first use.
4. Codex: only what is true today; if nothing in the repo supports Codex yet, a one-paragraph 'Not built yet' pointer.
5. Check it works: one read-only tool call (e.g. list_runs) and what a correct empty answer looks like.
6. Not built yet.

## Test (write first)
`tests/install_doc_test.sh`, style of tests/migration_doc_test.sh:
- the six headings;
- every `abf-platform <subcommand>` named exists in platform/abf_platform/cli.py;
- every MCP tool name the doc names in backticks exists as a tool in platform/abf_platform/mcp_server.py;
- every backticked repo path that looks like a file exists;
- the doc contains no literal token value (no string matching `abf_pat_[A-Za-z0-9]{8,}`).

## Out of scope
No code, no kit files, do not edit CHANGELOG.md, docs/PLATFORM.md, docs/MIGRATION.md, docs/TESTING.md, README.
