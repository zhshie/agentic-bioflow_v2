# Plan 009d: identity for the MCP server, step one = personal access tokens (HTTP MCP now needs a token)

- **Slug**: 009d-pat-identity
- **Branch**: `feat/009d-pat-identity`, base **`v3`** (never `main`)
- **Created**: 2026-10-16 by the developer-agent
- **Umbrella**: GitHub issue #93 step 4 (spec 009), after 009b (merged #100) and 009g (same lane: both edit `mcp_server.py`; this plan starts from v3 after 009g merged). Decision record: `docs/adr/0006-four-entries-one-action-layer.md` ("Where the platform runs, and who is calling", ~103-119: OAuth 2.1 "with a personal access token for clients without OAuth", identity = user, lab, agent, compute environments).
- **Tier**: B (user-visible: `abf-platform mcp --http` now answers 401 without a token).

## 給維護者

1. 這一步讓平台認得「誰在呼叫」：先建立使用者（姓名、實驗室），再替他發個人存取權杖（PAT）；權杖只在終端機建立與撤銷，只顯示一次。
2. 你用起來的差別：`mcp --http` 現在必須帶 `Authorization: Bearer <PAT>`，否則 401；stdio（本機）不變、不用權杖。
3. 送出與取消仍然只能在終端機按 y；身分只是被記錄下來，不是新的確認方式。角色（010）、OAuth、公開網址都不在這一步。

## Facts (origin/v3 after 009b, 2026-10-16; re-check line numbers after 009g lands)

- `store.py:6` tokens.db holds hashed tokens only, `rebuild` never opens it. `TOKEN_SCHEMA` (66-77) has `kind` ('run'|'agent'); `_hash` = sha256 (399); `_migrate_tokens` (403) adds columns in place; `create_token` (427) returns the plain token once and rejects any kind other than run/agent (434); `lookup_token` (457) ignores revoked/expired and returns `kind`; `revoke_token` (509) by id.
- `cli.py:45-67` `token new`, `agent-token new|revoke` print the token once via `_say`; `cmd_mcp` (234-241) only warns (`_risk_line`) for a non-loopback `--http` host, no auth; subparsers 290-302, `mcp` 330.
- `mcp_server.py:20` `build_server(index_path, platform_path=None)`, six tools are one-line calls into `actions.*`; `run_http` = `build_server(index).run("streamable-http", ...)`, no auth.
- `actions/__init__.py`: `TERMINAL` sentinel, read actions take paths only, `_require_human` runs first in `launch`/`cancel`, keyword `confirmed_by`.
- Pinned guards:
  - `test_mcp.py` tc024 (exactly six read-only tools, banned input names): unchanged.
  - `test_mcp.py` tc025 (streamable HTTP on loopback, no header): breaks by design; only its input changes (send a PAT), see Changes 5.
  - `test_launch_platform.py` TC-010/TC-061: unchanged. 009b's `test_actions_layer.py`: `mcp_server.py` never mentions `launch`, `cancel`, `TERMINAL`, `confirm\b`; only `abf_launch/cli.py` references `actions.launch|cancel|TERMINAL`: unchanged.
  - `test_secrets.py` tc040 canary scan of tokens.db and index.db: a PAT value must never appear; new test follows the same pattern.
  - `test_scope.py` tc070: every new `.py` needs a first-lines `# Not X: <reason>` or `# Nothing existing: ...` header.
  - `platform/pyproject.toml` packages: list any new package.
  - `tests/credentials_stay_in_settings_test.sh`: no script prints a token variable; no tracked file holds a token-shaped value. Fixtures build PATs at runtime.
  - `test_cli.py`, `test_station_envs.py` tokens.db checks stay green.

## Design decisions (developer-agent)

1. **Storage in tokens.db** (not index.db: `rebuild` must never lose identity). New table `users (id, name UNIQUE, lab, created_at, disabled_at)`. Tokens table gets `user_id INTEGER` through `_migrate_tokens` (old files keep working) and a third kind `pat`. `create_token` accepts `kind="pat", user_id=...`; value prefix `abf_pat_` + `secrets.token_urlsafe(32)`, stored as `_hash` only.
2. **A PAT never opens another door.** Test that a PAT is refused on the receiver and agent endpoints and a run/agent token is refused on MCP. New `lookup_pat(tokens_path, token)` returns `{"user_id","name","lab","token_id"}` or None (revoked token or disabled user = None).
3. **Terminal-only management.** `abf-platform user add <name> --lab <lab>`, `pat new --user <name> [--label]`, `pat list` (id, user, label, created, revoked; never a hash or value), `pat revoke <id>`. No MCP tool, no web route, no action for these. A PAT is printed once by `pat new` with the same wording and `_say` as `token new`; nothing else prints or logs it.
4. **HTTP auth as ASGI middleware** in a new module `platform/abf_platform/http_auth.py`, not the SDK's OAuth `AuthSettings` (OAuth is a later slice). `mcp_server.run_http` serves the SDK's streamable HTTP app wrapped by the middleware: missing, malformed or unknown bearer gives 401 with `WWW-Authenticate: Bearer`, body never echoes the token; a valid one sets a `contextvars` caller for the request. 009b's import rule for `mcp_server.py` is extended by exactly one allowed name, `http_auth`; `http_auth` itself may import `store` and `actions.Caller` only (AST test).
5. **`caller`** = frozen `actions.Caller(user_id, name, lab)`; `None` means local stdio/terminal, unauthenticated by design. Read actions gain keyword-only `caller=None` and ignore it. `launch`/`cancel` gain keyword-only `caller=None`; the `confirmed_by` check stays first (order unchanged), then `caller` name/id is recorded on the confirmation row (nullable column, migrated in place). `abf_launch/cli.py` passes `caller=None`.
6. **`--http` on a non-loopback host** keeps the risk line and adds "a token is required"; no flag or env var turns auth off.
7. No users yet: `mcp --http` still starts, every request is 401; `cmd_mcp` prints one line saying so.

## Changes, in order (red first)

1. Facts check: confirm the installed `mcp` SDK exposes the streamable HTTP ASGI app and how to wrap it; note in ledger.
2. Write tests, run, record FAIL:
   - `platform/tests/test_pat.py`: user add / pat new / list / revoke through the CLI; stored value is a hash (canary scan over tokens.db and index.db, PAT built at runtime); printed once (only `pat new` stdout; `pat list`, errors and server output contain none); revoked PAT and disabled user give 401; PAT refused on receiver/agent endpoints, run/agent token refused on MCP; an old tokens.db migrates.
   - HTTP: no header, wrong scheme, garbage, revoked → 401 with `WWW-Authenticate`; valid PAT → six tools, same answers as stdio; stdio needs no token.
   - caller: a spy on a read action sees the user; `launch(..., confirmed_by="yes", caller=u)` still refused and writes nothing; `launch(TERMINAL, caller=u)` queues one job and the confirmation row names the user.
   - AST: `mcp_server.py` imports only `actions` and `http_auth`; `http_auth.py` imports only `store` and `actions`.
3. `store.py`: users table, `user_id`, kind `pat`, `create_user`, `lookup_pat`, `list_pats`, `revoke_pat`.
4. `actions/__init__.py`: `Caller`, `caller=` params; confirmation column.
5. `http_auth.py`, `mcp_server.run_http`; `cli.py` commands and `cmd_mcp` message. Edit `test_mcp.py` tc025 only to create a user, issue a PAT and send the header (ledger lists it as the one pinned test whose input changes; assertions unchanged). Update 009b's import-rule test by the one allowed name only.
6. `docs/PLATFORM.md` (identity, PAT, how to put it in a client), `CHANGELOG.md` line under the 3.0.0-dev section ("breaking: `mcp --http` needs a PAT").
7. `cd platform && python -m pytest -q` green; WSL `bash tests/run_all.sh` green; ledger with red/green evidence.

## Not in this PR

- No OAuth 2.1, no discovery metadata, no public URL or TLS, no roles/PI/lab permissions (010), no per-user compute-environment limits, no token expiry or rotation, no web login (011+).
- No new way to confirm (still TERMINAL), no PAT or user tool in MCP, no edit to TC-010, tc024, TC-061, `LAUNCH_ALLOW`, hooks, constitution, `.github/`.

## Constitution Check

- I.2 single submission path: unchanged; `caller` is only recorded.
- Safety Net credentials rule: PAT shown once, stored hashed, never logged; fixtures build tokens at runtime.
- Loosens nothing; adds one refusal (401). Stdio stays local and unauthenticated by design.
