# harness-kits: copy-to-use connection kits for Claude Code and Codex

Source: issue #93 item 7 (code part); docs/INSTALL.md section 6 "Not built yet". Tier A: new files + doc, no change to how the plugin installs or behaves.

## Design decision (developer-agent, 2026-10-18) - read before coding
The handoff asked for a ROOT `.mcp.json` and a ROOT Codex `plugin.json` + `mcp.json`. Do NOT create them:
- This repo root IS the Claude Code plugin root (`.claude-plugin/marketplace.json` has `"source": "."`). Claude Code loads `.mcp.json` at the plugin root as the plugin's own MCP servers (code.claude.com/docs/en/plugins-reference, Standard layout). A root `.mcp.json` would add a placeholder server to EVERY person who installs the plugin.
- Codex: MCP servers are configured in TOML (`~/.codex/config.toml`) with `url` + `bearer_token_env_var` (developers.openai.com/codex/mcp). A root plugin.json/mcp.json would turn the repo into a Codex plugin with a bundled placeholder server, and env-var bearer tokens in a plugin mcp.json are undocumented.
- Claude Desktop: a remote server is added in the app as a custom connector (URL only; OAuth). No file to ship. INSTALL.md section 3 already gives the steps.
So the kits are copy-to-use files under `extensions/`, and the token always comes from an environment variable, never a literal.

## Files to add
1. `extensions/claude-code-kit/mcp.json` (no leading dot):
```json
{
  "mcpServers": {
    "abf-platform": {
      "type": "http",
      "url": "${ABF_PLATFORM_URL}/mcp",
      "headers": { "Authorization": "Bearer ${ABF_PAT}" }
    }
  }
}
```
2. `extensions/codex-kit/config.toml`:
```toml
# Append to ~/.codex/config.toml. Replace the URL; export ABF_PAT in your shell.
[mcp_servers.abf-platform]
url = "https://YOUR-PLATFORM.example/mcp"
bearer_token_env_var = "ABF_PAT"
```
Do NOT touch `extensions/claude-code-kit/settings.json` (PR #133 is changing it) or `.claude-plugin/*`.

## docs/INSTALL.md changes (keep all six `## ` headings and their order; tests/install_doc_test.sh must stay green)
- Section 2 Claude Code: keep the `claude mcp add` line. Add an alternative: copy `extensions/claude-code-kit/mcp.json` to `.mcp.json` in your own project folder (not this repo), set `ABF_PLATFORM_URL` and `ABF_PAT` in your own terminal; Claude Code asks you to approve a project server the first time. Say plainly: if `ABF_PAT` is not set, Claude Code sends the literal text and the platform answers 401.
- Section 4 Codex: replace "Not built yet" with real steps: append `extensions/codex-kit/config.toml` to `~/.codex/config.toml`, replace the URL, `export ABF_PAT=<PAT>` in your own terminal (never in a file kept in git).
- Section 3 Claude Desktop: unchanged except one sentence that there is no file to install; the connector is added in the app.
- Section 6 Not built yet: remove the three kit bullets. Replace with one bullet: a root `.mcp.json` is deliberately not shipped, because the repo root is the plugin root and every plugin install would load it. The heading must remain.

## Test (write first): `tests/harness_kits_test.sh` (style of tests/install_doc_test.sh; uses jq)
- TC-001 claude-code-kit/mcp.json parses; server abf-platform has type http, url contains ${ABF_PLATFORM_URL} and ends with /mcp, headers.Authorization == "Bearer ${ABF_PAT}".
- TC-002 codex-kit/config.toml has [mcp_servers.abf-platform], url ending /mcp, bearer_token_env_var = "ABF_PAT", no `bearer_token =` line, no literal http_headers.
- TC-003 neither kit file contains a literal token (abf_pat_[A-Za-z0-9]{8,}) nor a real host (host is ${ABF_PLATFORM_URL} or ends in .example).
- TC-004 repo root has NO .mcp.json, NO plugin.json, NO mcp.json.
- TC-005 INSTALL.md section 4 (between ## 4. and ## 5.) lacks "Not built yet" and names extensions/codex-kit/config.toml and bearer_token_env_var.
- TC-006 INSTALL.md names extensions/claude-code-kit/mcp.json; section 6 no longer lists a Codex kit or a Claude Desktop connector kit.
- TC-007 negative self-check: env override (KIT_DIR / INSTALL_DOC / ROOT_DIR) pointed at a doctored copy with a literal abf_pat_abcdefgh12 and a root .mcp.json makes the checks fail.

## Out of scope
Do not edit CHANGELOG.md, .claude-plugin/*, extensions/claude-code-kit/settings.json, platform code, docs/PLATFORM.md. No version bump.
