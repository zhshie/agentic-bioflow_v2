# Changelog

The v3 line (ADR 0006, 2026-10-15): the platform generation. `main` stays v2 (2.17.x) until v3.0.0.

## 3.0.0-dev (unreleased, branch `v3`)

- Opened 2026-10-15 from `main` at 2.17.0 (commit 42261eb). CI runs on pushes to `v3`.
- commands/*.md moved to skills/<name>/SKILL.md (Agent Skills format); invocation names unchanged.
- Planned, in order: the command files move to `skills/` (Agent Skills format, no content change);
  feature 009 (the action layer, write tools, human-channel confirmation, authorization, prompts
  and skills over MCP); constitution 6.0.0; each skill rewritten to call the platform; the
  harness kits (Claude Code, Codex, Claude Desktop); the web pages; the chat.
- 009b: the action layer (`platform/abf_platform/actions/`): the MCP tools and the terminal launch/cancel call one function per action; behaviour unchanged.
- 009d: **breaking** `mcp --http` needs a personal access token (`Authorization: Bearer <PAT>`, else 401); `abf-platform user add` and `pat new|list|revoke` on the terminal; stdio unchanged. The caller is recorded on launch and cancel confirmations, never a confirmation itself.
