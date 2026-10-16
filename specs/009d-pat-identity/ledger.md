# Ledger: 009d-pat-identity


- [x] 1. SDK fact (checked in the pinned venv): `MCPServer.streamable_http_app(host=...)` returns a Starlette ASGI app; `run("streamable-http")` only builds it and serves it with uvicorn. `mcp_server.build_http_app` wraps that app in `http_auth.BearerAuth` (pure ASGI, lifespan passes through) and `run_http` serves it with uvicorn.
- [x] 2. RED (commit "RED: test_pat.py ..."): `pytest tests/test_pat.py -x` failed at TC-A01 (`user` is not a command, exit 2). Test fix after GREEN began, in `test_pat.py` only: the TC-A11 name regex now matches whole words (the tc024-pinned input `path` contains "pat"), and a header value `Bearer ` (trailing space) is sent over a raw socket because httpx refuses it.
- [x] 3. store.py: `users` table, `user_id`/`label` columns (migrated in place), kind `pat`, `create_user`, `lookup_pat`, `list_pats`, `revoke_pat`, `user_id_of`, `has_users`; confirmations get `caller_user_id` (migrated in place).
- [x] 4. actions: frozen `Caller`, keyword-only `caller=None` on all eight actions; `confirmed_by` check still first; confirm.py records the user id; `abf_launch/cli.py` passes `caller=None`.
- [x] 5. `http_auth.py`, `mcp_server.run_http/build_http_app`, cli `user add`, `pat new|list|revoke`, `cmd_mcp` messages.
- [x] 6. docs/PLATFORM.md section 4, CHANGELOG line.
- Pinned tests whose text changed (three): `test_mcp.py` tc025 (input only: user + PAT + header, assertions unchanged), `test_actions_layer.py` tcc01 (allowed names now `{"actions","http_auth"}`), tce04 (parameter list gains last `caller`, plus one new assertion; `confirmed_by`/`clock` checks untouched). helpers.py: `mcp_http_call` gains optional `token`.
- PASS: `pytest tests/test_pat.py tests/test_actions_layer.py tests/test_mcp.py tests/test_scope.py tests/test_secrets.py tests/test_cli.py tests/test_launch_platform.py` 146 passed.
