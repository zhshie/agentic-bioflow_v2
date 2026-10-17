# Ledger 009c-human-channel

- 2026-10-17 plan moved in by the developer-agent; login option 1 decided by the maintainer.
- 2026-10-17 contract round 1 blocked (an AI holding the PAT could log into the web); the maintainer then chose a separate web password set only at a terminal (plan "round 2").
- 2026-10-17 contract round 2: **合約已確認** (verifier). test-case.md (117 cases) and test-case-overview.md saved verbatim from the verifier's report.

## Developer-agent rulings on the verifier's round-2 notes (binding for implementation)
1. **Database of `password_hash`**: the `users` table lives in **tokens.db** (`store.py:80`, `TOKEN_SCHEMA`), so `password_hash` is a column of `tokens.db` / `users`. `web_sessions` also lives in **tokens.db** (next to `users`, so a disabled user or a password change is one transaction). tc086's exceptions are exact triples: (tokens.db, users, password_hash) and (tokens.db, web_sessions, id_hash|user_id|created_at|expires_at). The plan's "platform.db only" is superseded by this line.
2. **Routes of the web app (complete set, TC-G04)**: `GET /login`, `POST /login`, `POST /logout`, `GET /c/{id}`, `POST /c/{id}`. Nothing else; every other path is 404. A not-logged-in visitor of `/c/{id}` gets the login page with a `next` back to that page.
3. **Rate limit**: as the verifier wrote (TC-B16/B17): per name, 5 failures within 60 s block that name for the rest of the window, even with the right password; other names unaffected.
4. **Platform web as a submission entry** (overview doubt 1): accepted as written — 011–013 add submission pages later and must go through the same pending → person → confirm path; this PR only adds the confirmation page.
5. **Disabled users** (doubt 2): cannot log in, and an existing cookie stops working at the next request (TC-B25).
6. **What others see** (doubt 5): a visitor who is not the requester (or not logged in) sees **no summary content** — only "not yours" / the login page (stricter than TC-D04/D05 require; add assertions that the summary text is absent).
7. **Password change** (doubt 6): `user passwd` deletes that user's `web_sessions` rows in the same transaction, so existing browser logins end at once; add a test.
