# Changelog

The v3 line (ADR 0006, 2026-10-15): the platform generation. `main` stays v2 (2.17.x) until v3.0.0.

## 3.0.0-dev (unreleased, branch `v3`)

- Opened 2026-10-15 from `main` at 2.17.0 (commit 42261eb). CI runs on pushes to `v3`.
- commands/*.md moved to skills/<name>/SKILL.md (Agent Skills format); invocation names unchanged.
- Optional, off-by-default Jev triage for FAILED runs (feature 015, ADR 0007): `scripts/jev.sh` names the likely cause category from the last 200 lines of `.command.err`; bring your own key, disclosed on first use, fails open.
- Planned, in order: the command files move to `skills/` (Agent Skills format, no content change);
  feature 009 (the action layer, write tools, human-channel confirmation, authorization, prompts
  and skills over MCP); constitution 6.0.0; each skill rewritten to call the platform; the
  harness kits (Claude Code, Codex, Claude Desktop); the web pages; the chat.
- 009b: the action layer (`platform/abf_platform/actions/`): the MCP tools and the terminal launch/cancel call one function per action; behaviour unchanged.
- 009g: the guidance travels through the MCP URL: routing-table `instructions`, one prompt per flow skill, the six skills as resources, and a copy of `skills/` inside the package.
- 009d: **breaking** `mcp --http` needs a personal access token (`Authorization: Bearer <PAT>`, else 401); `abf-platform user add` and `pat new|list|revoke` on the terminal; stdio unchanged. The caller is recorded on launch and cancel confirmations, never a confirmation itself.
- 009c: **constitution 5.0.0.** A person's yes may come through the terminal, the form of an MCP client, or the new confirmation page (`abf-platform web`, login with a web password set by `abf-platform user passwd` on a real terminal). The MCP server gains `launch` and `cancel`, which only write a pending request and ask the person; nothing is queued without a yes, and the repeated call returns the job that exists. `platform.db` and `tokens.db` are upgraded in place. The terminal commands are unchanged.
