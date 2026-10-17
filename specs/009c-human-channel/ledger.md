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

## Executor record (2026-10-17)

### Done
- RED `d6bce90`: the 009c tests (`test_human_channel.py`, `test_web_login.py`, `test_confirm_page.py`, `human_harness.py`) and the rewritten pins below; they failed on the missing modules and actions.
- `e6d4bf2`: the part of launch and cancel before any question moved from `abf_launch/cli.py` to `abf_launch/build.py`, shared with the MCP tools (the plan said "into actions"; `abf_platform` sources may not contain the word `station` (test_scope TC-061), and `build.py` calls `abf_station.launch.render_bundle()`, so it stays in `abf_launch`, which already may import both). `test_launch_cli.py` and `test_launch_static.py` pass unchanged.
- GREEN `0763a8c`: store (columns, `web_sessions`, scrypt password, `meta`), `confirm.py` (pending, approve, void, find_approved, describe), `jobs._check_confirmation` and `claim` require `state = confirmed`, `elicit.py`, `actions` (three channels, `request_launch|request_cancel`, `approve`, ...), the two MCP tools, `web.py` + `abf-platform web` + `abf-platform user passwd`, constitution 5.0.0 and the documents and pins it moves.

### Signatures of the new actions (the plan said they would be listed here)
- `request_launch(platform_path, *, pipeline, revision, run_name, samplesheet, ce_name=None, params=None, path_columns=None, caller=None, person=None, clock=time.time)` (async) and `request_cancel(platform_path, *, run_name, caller=None, person=None, clock=time.time)` (async): return a dict `{ok, sent, state?, id?, job_id?, confirmation_url?, summary?, message}`.
- `approve(platform_path, request_id, *, confirmed_by, caller=None, clock=time.time, deadline_seconds=None, offline_after=None)` -> `(request_id, job_id)`; raises `NotApproved` (a `JobRefused`) with `.status` in `not_found | not_yours | void | expired | already | failed` and `.job_id`.
- `find_approved(platform_path, kind, bundle, *, caller=None, clock=time.time)` -> `{id, job_id}` or None. `describe_request(platform_path, request_id, *, clock=time.time)`. `void_request(platform_path, request_id, reason)`. `person_at(ctx)`.
- `launch` and `cancel` keep their signatures; `confirmed_by` now accepts exactly `TERMINAL`, `ELICITED`, `PAGE`.

### Rewritten pins (old expectation -> new expectation, why). No assertion was deleted, skipped or loosened beyond what the new rule changes.
| Test | Old | New | Why |
|---|---|---|---|
| `test_actions_layer.py::test_tca02` | tools are exactly the six read ones | the six plus `launch`, `cancel` (constant `WRITE_NAMES`) | TC-A08 |
| `test_actions_layer.py::test_tca10` | all tools equal the 6-tool baseline | the six read tools equal the baseline (unchanged byte for byte); `launch` and `cancel` are not in it | the baseline predates them. Not in the plan's list, needed |
| `test_actions_layer.py::test_tce01` | no write tool; no name matching launch/cancel/confirm | exactly the eight; `read_only_hint` true only for the six; no name matching confirm/approve/passwd/login | TC-A08 |
| `test_actions_layer.py::test_tce03` | the word `elicit` (any case) is nowhere in the platform | the lowercase word is in `abf_platform/elicit.py` and in one import line of the action layer only (the channel name `ELICITED` is a different word, case-sensitive scan) | TC-C12 as written cannot hold: some module has to import `elicit.py`, and the channel is called ELICITED |
| `test_mcp.py::test_tc024`, `::test_tc025` | six read-only tools | six read-only plus `launch`, `cancel` (marked writing; no field that says yes) | TC-A08 |
| `test_launch_platform.py` TC-010 (door) | `mcp_server.py`, `receiver.py`, `agents.py` never mention confirm / enqueue / INSERT | the same scan, now also on `web.py` | the page is new code held to the same rule |
| `test_launch_platform.py` TC-010 (six tools) | six read-only tools, none with a launch field | eight; the six as before; the two without any yes field | TC-A08 |
| `test_guidance.py::test_tc501`, `test_launch_e2e.py::test_tc010_tc061`, `test_pat.py` (two tool-name asserts) | six tool names | eight | TC-A08 |
| `test_pat.py::test_tcf03_f04` | `users` columns `id, name, lab, created_at, disabled_at` | plus `password_hash` (still no role) | plan ruling 1; not in the plan's list, needed |
| `test_station_envs.py::test_tc086` | one exemption (index.db, runs, session_id) | the same, as the set `EXEMPT` with the five exact triples of ruling 1 added; the scan is the function `banned_schema_words` so `test_tcf10_f11` can show an extra column is still caught; the 404 checks are untouched | TC-F10, TC-F11 |
| `tests/constitution_scope_test.sh`, `tests/platform_direction_docs_test.sh` | version 4.1.0, Last Amended 2026-10-15, Safety Net fingerprint of 4.1.0 | 5.0.0, 2026-10-17, new fingerprint | the MAJOR amendment; the pins say to update them in the same PR |
| `abf_platform/guidance.py` FIXED_SENTENCE (not a test) | "the six tools are read-only. Launching and cancelling happen only in the terminal" | six read-only; launch and cancel only ask; the person says yes in their client's form or on a page | the old sentence became false. `test_guidance.py` TC-103..105 pass unchanged |

Unchanged on purpose (they still pass as written): `tcb04/08/09/10`, `tcc01/02`, `tce04` (signatures), `tce07`, TC-061, `tcb13`, `tcb18`, `test_launch_cli.py`, `test_launch_static.py`, `test_station_launch.py`.

### Departures and doubts for the developer-agent
1. **The generic rule says not to edit the constitution or `docs/ROADMAP.md`.** The plan (decision 8) and TC-H01..H04 require the 5.0.0 amendment, so I wrote it (version line, I.2 and its check, the Safety Net launch rule, the record with Sync Impact Report). `docs/ROADMAP.md` I did not touch: its waiting-principle row "Gates live in the platform's action layer..." is now partly met and should be struck by whoever may edit it. Remove the constitution part if this was not meant.
2. **TC-E04**: with the same run name and another version the call is refused outright ("run name used already"), because the approved job holds the name; with another name it gets a new pending request. Either way no job and the old yes is not reused. The test covers both.
3. **TC-A15**: a control character in `params` is not refused by the bundle (as at the terminal, TC-006); it is shown spelled out (`\x07`). A control character in the samplesheet is refused before anything is made.
4. **TC-C12**: see the `test_tce03` row.
5. **Web password** must be at least 8 characters (not in the plan); `user passwd` refuses a shorter one.
6. **`create_app(public_url=...)` writes the address into `platform.db` (`meta.web_base_url`)** so the MCP process, a different process, can name it; `abf-platform web` writes the loopback address when none is given. Without `abf-platform web` ever started the answers name `http://127.0.0.1:8789`.
7. `launch` reads the samplesheet from a path on the platform's machine (the plan's "samplesheet path"). Through HTTP that means a remote client can make the platform read any readable CSV/UTF-8 file it names into the summary that only that user sees. Same-user trust boundary as the rest of the plan; flagging it.
8. The skills (`skills/*/SKILL.md`) still describe launching only through the terminal command; rewriting them to use the tools is the "each skill rewritten to call the platform" step of the changelog, not this PR.
