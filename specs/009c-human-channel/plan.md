# 009c plan draft: a person's "yes" through MCP elicitation or a confirmation page (developer-agent, 2026-10-17)

> Status: draft in the workspace, moves into `specs/009c-human-channel/plan.md` on v3 once #106 (009d) merges.
> Tier C: redefines how I.2's "confirmed it" may be given (MAJOR amendment 5.0.0), the maintainer merges.
> Facts gathered 2026-10-17 by a read-only Explore agent on `feat/009d-pat-identity` (file:line in the session transcript).

## 給維護者
1. 以後不管從 Claude Desktop、Claude Code、Codex 或網頁送出，都會先出現一頁摘要（管線、樣本、跑在哪、結果放哪），你按「送出」才跑。
2. 支援「表單詢問」的 AI 客戶端（Claude Code）直接在對話裡跳是／否表單；不支援的給你一個網址，在瀏覽器登入後按。
3. 只有發起這次送出的本人能按；別人打開同一網址也不能送；AI 不能代按。

## Facts
- Action layer: `actions._require_human(confirmed_by)` accepts only the `TERMINAL` singleton (`actions/__init__.py:90-92`); `launch`/`cancel` then call `confirm.confirm_launch|cancel`, which write one `confirmations` row (`id` token_hex(16), `sha256` of the canonical bundle, `kind`, `caller_user_id`) and enqueue in one transaction (`confirm.py:12-25`).
- Platform check `jobs._check_confirmation` (`jobs.py:179-197`) and station check `abf_station/launch.py:441-462` verify id, kind, unspent, single use, and `sha256 == bundle_sha256`. Neither sees the caller. **These stay as they are.**
- MCP SDK `mcp==2.3.0` (`platform/constraints.txt`) has `Context.elicit` (form) and `Context.elicit_url` (URL mode); server is `MCPServer`; `custom_route` exists.
- `BearerAuth` wraps the whole MCP Starlette app (`http_auth.py`), so a browser page cannot live inside it.
- No HTML route anywhere; the receiver is a separate Starlette app with JSON routes pinned by tce02.
- Tests that pin "no write door" and are **rewritten, not loosened**, in this PR: `test_launch_platform.py:255` TC-010 (no `/confirm` door; mcp_server/receiver/agents never reference confirm/enqueue), `:275` six read-only tools; `test_mcp.py:53` tc024 (six tools, no name matching launch|cancel); `test_actions_layer.py` tca02, tcb04/08/09/10, tcc02, tce01, **tce03 (no "elicit" anywhere)**, tce04 (signature), tce07 (no prompts — already changed by 009g if merged). TC-061 (CLI) and `no_second_run_state_test.sh` LAUNCH_ALLOW are untouched (MCP and page only enqueue; the station agent stays the only submitter).
- Constitution 4.1.0: I.2 (lines 24-37) "runs only after the user has seen the full launch command and confirmed it"; Safety Net line 170 cites `hooks/confirm_launch.sh`; Governance: MAJOR for redefining a principle or Safety Net rule, rationale + breakage assessment + version bump + cited-doc updates in one PR, maintainer merges.

## Design decisions (developer-agent)
1. **Two new confirmation channels, each a distinct singleton** next to `TERMINAL`: `ELICITED` and `PAGE`. `_require_human` accepts exactly these three objects; strings, booleans and None stay refused (tcb04 cases keep their meaning, extended).
2. **Pending confirmation, then a person.** The MCP tools `launch` and `cancel` (write tools, `read_only_hint=False`, `destructive_hint=True` for cancel) build the same screen text the terminal shows (`launch_screen`) and create a *pending* row: bundle hash, kind, `caller_user_id`, `expires_at` (10 min), no job. A pending row is never a confirmation: `_check_confirmation` refuses it until a person flips it.
3. **Form mode (elicitation).** If the client advertises elicitation, the tool calls `ctx.elicit` with the screen text and one boolean field "送出" ; only an `accept` with `true` flips the row (channel `ELICITED`) and enqueues. Decline / cancel / timeout → refused, row expired. The model never sees a way to answer: the answer comes from the client's UI.
4. **URL mode.** Otherwise (or if the person prefers), the tool returns a one-time confirmation URL `/c/<pending id>` and says "open it, then call `launch` again with the same arguments". The page:
   - is served by a **separate small Starlette app** on the same `serve` process (not inside `BearerAuth`), loopback by default like everything else;
   - shows the screen text and a "送出" button;
   - requires the person to be **logged in as the same user** that created the pending row (`caller_user_id`); another user, or nobody, sees "not yours" and nothing changes;
   - POST with a CSRF token flips the row (channel `PAGE`) and enqueues; single use; expires with the row.
   - The repeated MCP call finds the flipped row for the same caller and bundle hash and returns the job id; it never creates a second job.
5. **Browser login** (needed for 4): see the open question below. Whatever is chosen stores only hashes server side.
6. **stdio has no caller.** Over stdio (local Claude Code) the write tools use form mode only; without elicitation they refuse with "use the terminal command or HTTP with a token". The terminal path (`abf-launch`) is unchanged.
7. **The station agent is unchanged**: it still checks hash, kind, unspent, single use. Who confirmed is recorded in the row (`channel`, `caller_user_id`, `confirmed_at`), not trusted by the agent.
8. **Constitution 5.0.0 (MAJOR)**: I.2 "confirmed it" becomes "confirmed it through a channel a person operates: the terminal, an MCP elicitation form, or the platform's confirmation page as the same logged-in user"; new check: "an unconfirmed launch is refused through the MCP tool *and* through the web route" (ADR 0006). Safety Net line 170 names both the hook (Claude Code kit) and the action layer gate. Sync impact report, breakage assessment (existing deployments: none use HTTP writes today).
9. **Claude Code kit**: a permission `ask` rule for `mcp__abf-platform__launch|cancel` as a second layer (ADR 0006); not the gate.

## Tests (red first; the verifier writes the cases)
- Refused through the MCP tool: no elicitation and no page approval; elicitation declined / cancelled / `false`; a pending row approved by another user; an expired row; a replayed row; a changed bundle after approval (hash mismatch).
- Refused through the web route: not logged in; logged in as another user; missing / wrong CSRF; GET never changes anything; second POST.
- Accepted: elicitation `true` → exactly one job; page approval then repeated call → exactly one job, same id on a third call.
- Terminal path unchanged (tcb13/tcb18 green).
- Rewritten pins listed above, each with the old expectation, the new one and the reason in the ledger; no deny made weaker than the new rule.

## Not in this PR
- Resume / relaunch (009e), dev mode (009f), public HTTPS (009h), the other web pages (011–013).

## Decided 2026-10-17: option 1 (他：「都依照你的建議處理」) — log in once with name + PAT, signed cookie 12 h, `web_sessions` table (hash only); tc086's session ban gets exactly that one exception.

## Open question for the maintainer (C, one question) — answered above
How you log into the confirmation page in a browser:
- **(recommended) Log in once with your username + personal token, the browser remembers you for 12 hours** (a signed cookie; only its hash is stored). This is also the login the later web pages use. It undoes 009d's new "no session/cookie" ban in tc086 for exactly one `web_sessions` table.
- Paste your personal token every time you confirm (no cookie, but clumsy on a phone).

## Decided 2026-10-17 (round 2): web password set only at a terminal
The maintainer first chose the token login above; after the contract review showed an AI holding the PAT could log in and approve, he answered 「好的」 to: a separate web password, set with `abf-platform user passwd` (needs a real TTY, typed by the person), kept only as a slow hash (scrypt) in the users table; the web login takes name + this password, never a PAT; `Authorization: Bearer` never logs into the web (TC-B14). Cookie 12 h. Honest boundary written into the constitution and `docs/PLATFORM.md`: an AI that can run commands on the person's own machine can do what the person can; the gate stops AI clients that reach the platform only over MCP.

Technical rulings by the developer-agent on the contract review's points 2-5:
- Pending confirmations live in the `confirmations` table with added columns `state` (pending / confirmed / void), `channel`, `confirmed_at`, `expires_at`, `ce_name`, `bundle_json`; `_check_confirmation` additionally requires `state = confirmed` (a tightening); existing rows are upgraded as confirmed / TERMINAL.
- The pending row keeps the full bundle and `ce_name` so the page can enqueue.
- MCP `launch` takes the same choices the terminal command takes (pipeline, revision, samplesheet path, params, ce_name, run name); the bundle and screen builder move from `abf_launch` into `actions` (shared, output unchanged). Elicitation lives in one module `abf_platform/elicit.py`; new actions `request_launch`, `request_cancel`, `approve`, `find_approved`, signatures listed in the ledger; `launch` / `cancel` signatures unchanged.
- The page is a separate Starlette app served by `abf-platform web` (own process, loopback, own port; `--public-url` sets the base the MCP answer names). The receiver's ROUTES_V3 is unchanged.
- Enqueue failure after approval: the row goes void with the reason; the person retries from the AI (new pending). Signing key kept in the platform data dir (mode 600). Cookie HttpOnly, SameSite=Strict, Secure when not loopback. Login failures limited to 5 per minute per name.
- tc086's single exception: table `web_sessions` (`id_hash`, `user_id`, `created_at`, `expires_at`) and the users table's `password_hash` column, in platform.db only. (Superseded by ledger ruling 1: both live in tokens.db.)

## Ruling after acceptance round 3 (2026-10-17, developer-agent)
- The rewritten pins beyond the list at "Facts" are **accepted** as recorded in `ledger.md` (the "Rewritten pins" table and its notes): `test_pat.py` tca11, tcb08_b09, tcb10, tcf03_f04; `test_guidance.py` tc501; `test_launch_e2e.py` tc010_tc061; `test_station_envs.py` tc071, tc063, tc084; `test_actions_layer.py` tca10; the version and Safety Net fingerprint pins in `tests/constitution_scope_test.sh` and `tests/platform_direction_docs_test.sh`. Each is a necessary consequence of six tools becoming eight, the new `web` subcommand, the `password_hash` column, or the 5.0.0 amendment; the verifier read every diff and found no assertion deleted, skipped or loosened.
- `docs/ROADMAP.md`'s waiting row "Gates live in the platform's action layer…" is updated in W0 (ADR 0009 follow-through), not here.
- Known limit recorded for the maintainer: the MCP `launch` samplesheet is a path on the platform machine; before the platform is reachable by other people (009h public URL), the path must be confined to the caller's own area. Follow-up issue, not this PR.
