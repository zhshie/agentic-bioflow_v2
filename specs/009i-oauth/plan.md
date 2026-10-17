# Plan 009i: minimal OAuth 2.1 so Claude Desktop custom connectors reach the HTTP MCP server (#117)

- **Slug**: 009i-oauth. **Branch**: `feat/009i-oauth`, base **v3**. Implementation starts after #116 (owner binding) merges. The contract can be written now.
- **Tier**: A. OAuth only adds another way to prove who the caller is, like the PAT does. It adds no confirmation channel: I.2 (5.0.0) lists exactly three, the terminal, the form and the page. The slice becomes tier C only if a token, a consent click or a registered client could stand for a person's yes, and the tests below rule that out.
- **Created**: 2026-10-17 by the developer-agent. Facts come from a read-only Plan agent on the #115 head and from the `mcp==2.3.0` wheel. Re-check the line numbers on v3.

## 給維護者
1. Claude Desktop 的「自訂連接器」可以用網頁登入連平台：跳出瀏覽器頁面，你用名字＋網頁密碼登入、按「允許」，之後它以你的身分連線，不必貼權杖。
2. 允許連接器不等於同意送出分析；每次送出、取消仍要你本人按「送出」。授權頁只收網頁密碼，絕不收權杖。
3. Claude Desktop 從雲端連進來，要等平台有公開 https 網址（009h）才能端到端實測；在那之前用本機測試代替。

## Facts
- `http_auth.py`: `BearerAuth` wraps the whole MCP app.
  - It looks up the PAT with `store.lookup_pat` (kind `pat` only).
  - With no match it returns a 401 with a bare `WWW-Authenticate: Bearer`.
  - With a match it puts `Caller(user_id, name, lab)` into `scope["abf_caller"]`, and an MCP session is bound to that user.
- `mcp==2.3.0` ships server-side auth:
  - `mcp/server/auth/provider.py`: the `OAuthAuthorizationServerProvider` protocol (`get_client`, `register_client`, `authorize`, `load_authorization_code`, `exchange_authorization_code`, `load/exchange_refresh_token`, `load_access_token`, `revoke_token`). PKCE is S256 only.
  - `mcp/server/auth/routes.py`: `create_auth_routes` (`/authorize`, `/token`, `/register`, `/revoke`, metadata) and `create_protected_resource_routes`. `validate_issuer_url` requires https except on loopback.
  - `mcpserver/server.py`: passing `auth=` adds the SDK's own `RequireAuthMiddleware`.
- The 009c web app (`web.py`) has the name + web password login, the signed cookie, `web_sessions`, CSRF, the same-origin check and throttling. It binds loopback only, and `--public-url` gives its public base.
- Pins this slice touches:
  - `test_pat.py`: tcf01 (`.well-known/*` gives 404, the bare `Bearer` challenge, no `AuthSettings` in `mcp_server.py`), tcf02 (the `run_http` parameters, no "public" in `mcp --help`), tcb01–b07 (the 401 shape), tcc03/c04.
  - `test_confirm_page.py`: the web app answers 404 for `/oauth/*`.
  - `test_human_channel.py`: tcf10_f11 (the schema ban on session/cookie/password words, with an exact exception list).
- Unchanged pins: `test_receiver.py` and `test_station_envs.py` (no `/oauth/*` on the receiver or the platform).

## Design decisions (developer-agent)
1. **Manual check, written into `docs/TESTING.md`** (new section "Claude Desktop custom connector (#117)"):
   - Add a custom connector pointing at `/mcp`.
   - Record whether it can send a custom `Authorization: Bearer` header, the redirect URI it registers, and the client version.
   - Earlier research says it supports OAuth with dynamic client registration only, so this slice is built. The check fixes the allowed redirect URIs.
2. **Use the SDK's handlers.**
   - One class, `abf_platform/oauth.py::PlatformOAuthProvider`, stores everything in `tokens.db`.
   - `AuthSettings` is not passed to `MCPServer`, so `BearerAuth` stays the one check at the MCP door.
3. **Where the endpoints live.**
   - The authorization server (metadata, `/register`, `/authorize`, `/token`, `/revoke`, the consent page) is mounted in the 009c web app. The issuer is its `--public-url`.
   - The MCP process serves only `/.well-known/oauth-protected-resource`, and `BearerAuth` lets exactly that GET through without a token.
   - `mcp --http --public-url` sets the resource URL, and the 401 becomes `Bearer resource_metadata="<url>"`.
   - The receiver is untouched.
4. **Storage, in `tokens.db`, hashes only.**
   - New tables: `oauth_clients`, `oauth_requests` (10 min) and `oauth_codes` (5 min, single use, bound to client, redirect URI, PKCE challenge and user).
   - Access and refresh tokens reuse `tokens` with new kinds `oauth_access` and `oauth_refresh`, which carry `user_id`, `label` = client_id and `expires_at`.
   - No column uses the banned words, and `EXEMPT` gets no new entry.
5. **Authorization flow.**
   - `authorize()` stores the request and redirects to the consent page.
   - The consent page needs the 009c login: name + web password only. A PAT or a Bearer header never logs in.
   - The page shows the connector name, the redirect host, and "it can read your runs and ask to launch; it cannot send an analysis — you still press 送出 each time", with Allow / Deny.
   - POST needs CSRF. GET never changes anything.
   - Allow mints the code. Deny redirects with `access_denied`.
6. **Tokens.**
   - The access token lasts 1 h. The refresh token lasts 30 days, rotates and can be revoked. These are constants.
   - `BearerAuth` tries the PAT first, then `oauth_access`. Both give the same `Caller`, so the #116 owner filters apply unchanged.
   - A disabled user fails both. `abf-platform oauth revoke USER` revokes.
   - Run and agent tokens still get 401 on MCP.
7. **Dynamic client registration.**
   - Registration is on, because it grants nothing without a login plus consent.
   - Redirect URIs must be https, or loopback. The exact Claude callback is taken from the manual check.
   - Limits: at most 200 clients, a rate cap per address, and unused clients expire after 30 days.
   - Public clients with PKCE are accepted.
8. **The gate is not weakened.**
   - `_require_human`, the three singletons, `confirm.py` and the jobs checks are untouched.
   - An OAuth token is an identity only. It cannot open the web: `/c/<id>` with either kind of Bearer gives the login form.
   - Consent writes no `confirmations` row.
   - `launch`/`cancel` over an OAuth token only make a pending request.
9. **Honest boundary** in `docs/PLATFORM.md`: an AI client holding an OAuth token acts as that user, except for the person's yes. It is as strong as a PAT, only shorter-lived.

## Tests (red first; the verifier writes the cases)
- Metadata and challenge:
  - The MCP process serves the resource metadata.
  - The web app serves the authorization-server metadata with S256 only.
  - The 401 carries `resource_metadata`.
- Registration refuses a redirect that is neither https nor loopback, and refuses once the cap is reached.
- Full flow: register, authorize, log in with name + web password, consent, token, then an MCP call as the right user.
- Refused:
  - a wrong PKCE verifier;
  - a reused code;
  - a code presented by another client or with another redirect;
  - an expired code;
  - a replayed refresh token;
  - Deny, which returns `access_denied` and no code;
  - a consent POST without CSRF;
  - a GET that would mint a code.
- The authorization page never accepts a PAT or a Bearer header as a login. A web password is never accepted at `/token` or on MCP.
- An OAuth token cannot approve a pending request (page or form), and consent creates no confirmation.
- A launch over an OAuth token queues no job until a person says yes.
- A disabled user, or a revoked or expired token, gets 401.
- A PAT keeps working unchanged. An OAuth token and a PAT for the same user see the same data.
- Pins to rewrite, each with old, new and reason in the ledger:
  - tcf01: new metadata and challenge. Assert that `AuthSettings` is not passed to `MCPServer`.
  - tcf02: `public_url` added.
  - `test_confirm_page.py` `/oauth/*`: exactly the listed paths exist, and every other path is still 404.
  - tcb01–b07: the header text.
  - Docs and version pins.

## Not in this PR
- Public https hosting (009h).
- Scopes beyond one.
- OAuth for the receiver or the agent.
- Third-party identity providers.
- Password reset.
- Remembering consent per client.
- Any change to the confirmation channels.

## Constitution Check
- I.2: no channel is added, so this stays tier A.
- Safety Net: refusals are only added. The authorization page accepts only the 009c web password.
- V/VI: hashes only. The `test_secrets` canary is extended to OAuth tokens.
- Governance: no amendment. Update `docs/PLATFORM.md`, `docs/TESTING.md` and CHANGELOG.

## Contract rulings (2026-10-17, developer-agent, on the verifier's open points)
1. Without `--public-url`, the 401 stays a bare `Bearer`, and the PAT works (TC-A05 as written).
2. A reused authorization code also revokes every token issued from that code (RFC 6749 §4.1.2). Add this as an assertion in TC-D03.
3. `abf-platform oauth revoke USER` revokes only OAuth tokens. PATs use `pat revoke` (TC-E05 as written).
4. A disabled user's refresh token is refused as well (TC-D10 confirmed).
5. The resource-metadata path is the SDK default. Its URL is stored and read the same way as `web_base_url`.
6. The registration rate cap is 10 per address per hour, a named constant documented in `docs/PLATFORM.md`.
7. The cookie stays `SameSite=Strict`. A second login prompt after a cross-site redirect is accepted, because security comes before convenience.
8. Consent is not bound to an initiator, which is standard OAuth. The consent page shows the client name and the redirect host. TC-C05 is the human check.

## Ruling after acceptance round 1 (2026-10-18, developer-agent): option (a)
- Pins to rewrite also include `test_owner_binding.py::test_tc068` (the web route set, the `cli.py` no-`oauth` scan, now an exact allow-list; the `http_auth.py` store-call set) and `test_station_envs.py::test_tc063` / `test_tc084` (the top-level subcommand set and `--help` string gain `oauth`). Each is a necessary consequence of design 3, design 6 and TC-E05. Each stays an exact set: nothing is widened beyond the new names. The ledger entries already present are accepted.
- Contract amendment, same date:
  - TC-G05's "test_station_envs.py unchanged" is narrowed to "tc086 unchanged".
  - TC-G06's allowed list adds the three pins above.
- `openid`, `saml` and `ldap` stay banned in `cli.py`.

## Ruling after the #126 code review (2026-10-18, developer-agent). Fix in this PR, each with a red test first
1. **The form channel (ELICITED) for OAuth tokens.**
   - `Caller` carries how the caller was proven: `auth="pat" | "oauth"`, plus for OAuth the client's redirect hosts.
   - `_ask` offers the form only to:
     - a PAT caller, as today (the maintainer's 009c decision);
     - stdio;
     - an OAuth caller whose client's registered redirect URIs all have host `claude.ai` or are loopback (127.0.0.1, ::1, localhost). The allow-list is a named constant in `oauth.py`, documented in `docs/PLATFORM.md`.
   - Every other OAuth caller gets the PAGE path only: a pending request plus the confirmation URL, so the person presses 送出 in the browser.
   - **Why this holds:** a code is only ever delivered to a registered redirect URI. An attacker who phishes a consent for a client whose redirect is claude.ai never receives the code. A client whose redirect is the attacker's own host never gets the form.
   - Tests:
     - an attacker-registered client (https://evil.example/cb) with an auto-accepting form gets `pending` and no job;
     - a claude.ai-redirect client and a loopback client get the form;
     - a PAT is unchanged.
2. **Consent text is truthful.** For allow-listed clients the page says the connector can show you a 送出 form inside the AI app. For other clients it says each launch or cancel must be confirmed on this website. Remove the absolute claim.
3. **Registration and authorize abuse.**
   - Cap the request body at 16 KiB. Cap metadata fields: `client_name` 100 characters, at most 5 `redirect_uris` of at most 512 characters each, and drop `logo_uri`, `client_uri`, `tos_uri` and `policy_uri`.
   - Count `MAX_CLIENTS` only over clients that completed at least one token exchange. Purge clients that never exchanged after 24 h.
   - Cap pending `oauth_requests` at 20 per client and 200 in total. Over the cap, the answer is refused. Purge expired requests on every `/authorize`.
   - Tests cover each cap.
4. The `docs/PLATFORM.md` honest-boundary paragraph names the allow-list and its reason.
