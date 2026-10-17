# 009i: minimal OAuth 2.1 for Claude Desktop custom connectors (#117) progress ledger

Tests: `platform/tests/test_oauth.py` (A, B), `test_oauth_consent.py` (C), `test_oauth_tokens.py` (D), `test_oauth_mcp.py` (E, F, H, I03, I04),
`test_secrets.py` (I03), helpers in `oauth_harness.py`. Code: `platform/abf_platform/oauth.py` (new), `web.py`, `http_auth.py`, `mcp_server.py`, `cli.py`, `store.py`.

## Tasks

- [x] US1 discovery (TC-A01..A07): `http_auth.BearerAuth` serves the SDK's protected-resource metadata for that one GET and names it in the 401; `mcp --http --public-url`; the authorization-server metadata comes from the SDK's `build_metadata` in the web app (public client only: `token_endpoint_auth_methods_supported` is `["none"]`).
- [x] US2 registration (TC-B01..B08): `oauth.PlatformOAuthProvider.register_client` (https or loopback redirects, 200 clients, 30 days idle) and `oauth.RegisterRateCap` (10 per address per hour, a named constant).
- [x] US3 consent (TC-C01..C17): `web.py` `/consent/{rid}`; `oauth.PlatformOAuthProvider.consent_decide` takes the write lock first so two presses make one code.
- [x] US4 tokens (TC-D01..D14): code and refresh token single use; rotation.
- [x] US5 MCP door (TC-E01..E11), US6 gate (TC-F01..F08), out of scope (TC-H01..H07), secrets (TC-I03, I04).
- [x] Docs (TC-I05..I07): `docs/PLATFORM.md` ("Claude Desktop's custom connector"), `docs/TESTING.md` ("Claude Desktop custom connector (#117)"), `CHANGELOG.md`.
- [ ] Manual, for the verifier and the maintainer: TC-C05 wording, TC-F09, TC-G06, TC-I01, TC-I05, TC-I06, TC-I07, TC-I09, and Claude Desktop end to end (waits for 009h).

## Choices not written in the plan (for the reviewer)

- **Client secrets are not kept.** The SDK's registration handler mints a secret before the provider is asked. `register_client` turns every client into a public one (`token_endpoint_auth_method` `none`, no secret) in the stored record and in the answer, so no client secret is ever in `tokens.db` (hashes-only rule). PKCE protects the code.
- **Reuse ends the family.** Beyond ruling 2 (a reused code revokes the tokens made from it), a refresh token used again after it was rotated or revoked revokes every token of that authorization (OAuth 2.1 refresh-token reuse rule). `tokens.grant_id` (new column, migrated) ties them; asserted in TC-D08.
- **A client in use is not idle.** `oauth_clients.last_used_at` is touched at `/authorize` and at every code or refresh exchange, so a connector that keeps refreshing is never forgotten after 30 days (found while writing TC-D09).
- **The MCP public address is not stored in platform.db.** Ruling 5 said its URL is "stored and read the same way as `web_base_url`". Only the web page's address is stored (it already was, as `web_base_url`, and the MCP process reads it); the MCP process's own public address is a start argument held by `BearerAuth`, because nothing else reads it.
- **Consent CSP.** The consent page's `form-action` lists the connector's redirect origin as well as `'self'`, because browsers apply `form-action` to the redirect that follows the form post; without it Allow would be blocked in the browser.
- **Registrations are counted per socket address, in memory** (a restart forgives). Behind a TLS proxy every visitor shares the proxy's address; written in `docs/PLATFORM.md`.

## Pins rewritten (old, new, reason)

Planned (named in the plan):

| Test | Old | New | Reason |
|---|---|---|---|
| `test_pat.py::test_tcf01` (renamed `..._only_with_a_public_url`) | no `.well-known` pages, bare `Bearer`, no `AuthSettings` | the whole old check stays for a server started without `--public-url`; added: with `--public-url` the 401 names the resource metadata, that GET is 200, the authorization-server page is still 404 on the MCP process; the source check `AuthSettings not in mcp_server.py` stays | 009i adds the metadata and challenge |
| `test_pat.py::test_tcf02` | `mcp --help` has no `public`; `run_http` has `index_path, host, port` | `ssl|cert|tls` still absent, `public` appears only as `--public-url`; `run_http` has `index_path, host, port, public_url` | the one new option |
| `test_confirm_page.py::test_tcg04_g05_g06` | the web app has exactly five routes | exactly those five plus the consent page (GET, POST) and the SDK's five (`/.well-known/oauth-authorization-server`, `/authorize`, `/token`, `/register`, `/revoke`); the 404 list (`/oauth/token`, `/oauth/authorize`, and the rest) is unchanged and still passes | the plan's `/oauth/*` item |
| `test_pat.py` tcb01..tcb07 | | **unchanged**: a server started without `--public-url` keeps the bare `Bearer` challenge (ruling 1), so no header text had to change | |

Not named in the plan, forced by it (the reviewer should look at these three):

| Test | Old | New | Reason |
|---|---|---|---|
| `test_owner_binding.py::test_tc068_no_new_way_to_log_in` | routes of the web app are `/login`, `/logout`, `/c/{rid}`; no word `oauth` in `cli.py`; `http_auth.py` uses `store.lookup_pat` and `default_tokens_path` only | routes are those plus the consent page and the five SDK paths (exact set); `cli.py` has no `openid|saml|ldap` and the only `oauth` words are the `oauth revoke` command's; `http_auth.py` also uses `store.lookup_oauth_access` and `store.get_meta` (exact set) | the plan puts the authorization server in the web app, adds `oauth revoke`, and reads OAuth tokens in `BearerAuth` |
| `test_station_envs.py::test_tc063` | top-level subcommands `serve, token, agent-token, ce, mcp, rebuild, launch, cancel, fetch-records, launches, user, pat, web` | the same plus `oauth` | `abf-platform oauth revoke USER` is in the plan (design 6, TC-E05) |
| `test_station_envs.py::test_tc084` | the subcommand list string in `--help` | the same with `oauth` after `pat` | same |

Nothing deleted, skipped or loosened; `test_receiver.py`, `test_human_channel.py::test_tcf10_f11` (EXEMPT list), `test_pat.py` tcc03/tcc04 and tcd12 (module imports of `http_auth.py` stay `store`, `actions`; of `mcp_server.py` stay `actions`, `guidance`, `http_auth`) are untouched and pass.

## Order of work (honest note)

The discovery and registration tests were committed red first. The provider, the consent routes and the token endpoint were then written in one go, so the consent, token and door tests passed when first run and have no separate red commit.

## Test infrastructure

- `tests/platform_test.sh`: the four new OAuth test files are one more shard in the fixed list (`SHARDS`). Without it they fell into the last shard (`REST`, one serial pytest) and `platform_test.sh` passed the 300 s limit of `run_all.sh`. No test was changed by this.

## Fix round after acceptance round 2

- `test_oauth_mcp.py::test_tci03_i04...`: added assertions (nothing removed). The replayed-code error body and the `/revoke` body are now checked for every secret of the flow (TC-I04 "responses"). The first two bodies (token, refresh) carry tokens to the client by design and are not checked.
- `test_oauth_mcp.py::test_tch07_no_new_channel`: the source scan was nearly always true. It now asserts that no `actions/*.py`, `confirm.py` or `jobs.py` contains the word oauth at all (stricter, not looser).
- TC-G06 (the contract was amended by the developer-agent after round 1): not fixable in code. The three pins in the section above stay as they are; whether the amendment is accepted, or the verifier re-issues G05/G06, is a ruling for the developer-agent and verifier. The executor did not touch `test-case*.md` in this round.

## Merge of origin/v3 (116b `runs`)

- Conflicts in CHANGELOG.md, docs/PLATFORM.md, platform/tests/test_station_envs.py resolved as the union; no assertion loosened or removed.
- CHANGELOG: the 116b entry and the 009i entry both kept. PLATFORM.md: "Closing the gaps of 116" (116b) kept, then "Claude Desktop's custom connector" (009i); one "Not here" line.
- tc063: subcommand set now contains both `runs` and `oauth`. tc084: help string is `{serve,web,token,agent-token,user,pat,oauth,ce,mcp,rebuild,runs,launch,cancel,launches,fetch-records}` (the order cli.py registers them).
