# keep-submissions: a submission's content is kept until its owner deletes it

Tier B (a behaviour the maintainer can see changes, and it modifies a rule written in 009c plan item 8).

## The maintainer's words (2026-10-18)

> 送出內容除非使用者刪除不然不刪

The question he answered: "Keep submission contents 7 days or 30 days?" He chose neither: keep until the user deletes them.

## What "submission content" means here

A row in `confirmations` that reached `state = 'confirmed'` keeps `bundle_json` and `screen_text`: what was run and the text the person approved. Today `confirm.create_pending` clears both after `KEEP_CONTENT_SECONDS` (7 days) for `void`, `confirmed` and expired `pending` rows.

## Rulings (developer-agent, technical)

1. Confirmed rows: never cleared by time. Remove them from the prune.
2. Rows that were never submitted (`void`, or `pending` past `expires_at`): still cleared after 7 days. They were never sent, and keeping them forever only grows the database. Rename the constant so its name says this (`KEEP_UNSENT_SECONDS`); the value stays 7 days.
3. A new action `forget_submission(run_name)` clears `bundle_json` and `screen_text` of every confirmed row behind that run. Audit columns (`id`, `sha256`, `kind`, times, `caller_user_id`, `channel`, `state`) stay, so the record that it happened is not lost.
   - Owner only. Not the owner, or no such run, gives the same "not found" answer (#116 rule).
   - Refused while the run is queued or running: say so in Chinese and English.
   - It is irreversible, so it is confirmed through the existing human channels exactly like `cancel`: terminal `abf-platform forget RUN` asks `y`, with no `--yes`; the MCP tool `forget` goes through `_ask` (and the 009i connector rule).
   - The screen says, in plain Chinese: 「刪除後無法復原；這個 run 之後不能再續跑或原樣重跑。紀錄（誰、何時送出）會保留。」
4. Anything that reads a confirmed bundle later (009e resume/relaunch, when it lands) must treat a forgotten bundle as "content deleted by its owner" and refuse with that message, not as a crash. If 009e is not on v3 yet, note the hook point in the ledger; do not pull 009e code in.
5. The web stays read-only (011a); no delete button in this task.
6. Docs: `docs/PLATFORM.md` (retention paragraph and the new action), CHANGELOG.

## Examples (become test cases)

- A launch confirmed 400 days ago: its bundle and screen are still there after a new `create_pending` runs the prune.
- A pending request that expired 8 days ago: cleared. One that expired 6 days ago: kept.
- Owner runs `abf-platform forget R1` on a finished run, answers `y`: bundle and screen are gone, the audit row is still there.
- Another user asks to forget R1: "not found", nothing changes.
- Owner asks to forget a run that is still running: refused, nothing changes.

## Out of scope

Deleting results on the cluster, deleting runs from the run list, any web UI.

## Rulings after contract round 1 (developer-agent, 2026-10-18)

R1. Pins this plan moves, by name (maintainer decision 2026-10-18, "送出內容除非使用者刪除不然不刪"):
   - `platform/tests/test_review_fixes.py` ~line 119 (test_f9_..., second review item 8) and
     `platform/tests/test_review_fixes_2.py` ~line 282 (`test_r8_confirmed_rows_lose_their_content_after_seven_days_too`):
     they asserted that a confirmed row loses its content after 7 days. Invert them: a confirmed row keeps its content at
     any age; void and expired-pending rows still lose it after 7 days. Keep the void/pending half of each test as is.
   - The fixed MCP tool lists in `test_human_channel.py` ~158, `test_guidance.py` ~397, `test_actions_layer.py` ~28 grow by
     exactly one tool, `forget`. Nothing else in those lists changes.
R2. `forget` over MCP: form channel only. When `_ask` would fall back to the page (no form: an HTTP client whose form is not
   trusted, e.g. a connector token with form_ok false) or over stdio, refuse without writing anything and say:
   「這個客戶端無法跳出確認視窗；請在終端機執行 abf-platform forget <run> (this client cannot show a confirmation form; use the
   terminal command)」. No page support, so `confirm.approve` and `JOB_KIND` are not touched. `forget` queues no job: an
   accepted form answer clears the content in the same transaction as the confirmation row (kind `forget`, audit kept).
R3. "Queued or running" is read from existing sources only, never stored (constitution I.2): refuse if any `jobs` row for the
   run is queued or running, or if the run's status as the owner sees it through `actions.get_run` is not final. Use the
   final-status set the code already has; do not invent a new one.
R4. "Deleted means deleted": `forget` also clears the content copy the `jobs` rows of that run keep (whatever column holds the
   queued bundle), keeping their audit columns. Update the PLATFORM.md sentence "the job keeps its own copy of what was
   queued" to say a forget clears that copy too.
R5. Terminal `abf-platform forget RUN`: no owner check, same as `abf-platform cancel` (the terminal is the machine's owner).
   The owner check (#116 rule, same "not found" for not-yours and missing) applies to MCP/HTTP callers.
R6. A run with no confirmed content left (already forgotten): answer 「已經刪除過了 (already deleted)」, change nothing, no
   error. `forget` also clears pending and void rows of that run, and voids any open pending request for it.

## Rulings after contract round 2 (developer-agent, 2026-10-18)

R7 (replaces the source part of R3). `forget` is allowed only when the run's status, as `status.py` gives it, is a stored final
   status: succeeded, failed or aborted. Refused, with nothing changed:
   - `running`;
   - `lost` (it may still be running on the cluster: same reason 009e refuses lost runs);
   - launched but not in the run index yet (`get_run` found:false while a launch job exists): 「這個 run 還在準備中，不能刪除
     (the run is still starting)」;
   - any `jobs` row of the run queued or claimed.
   The name is mapped to the run the same way `request_cancel` already maps a run name to its run; reuse that, no new mapping.
R8 (replaces the confirmation-row part of R2). No new `kind` and no CHECK change: `forget` writes no `confirmations` row. The
   accepted form answer is the confirmation. The audit is two new nullable columns, added through the existing add-columns
   upgrade in `store.py`: `forgotten_at REAL` and `forgotten_by TEXT` (user id, NULL from the terminal), set on every row whose
   content `forget` clears, in `confirmations` and in `jobs`. An old platform.db gains them on open, losing no rows.
R9. The rows of a run:
   - its launch confirmation: `launches.job_id -> jobs.confirmation_id`;
   - its cancel confirmations, and its pending or void launch/cancel requests: the rows whose `bundle_json` names that run_name.
     Over MCP/HTTP, only those whose `caller_user_id` is the caller;
   - its jobs: the launch job and the cancel jobs of that run.
   A terminal-confirmed launch has no content in `confirmations`, so only its job copy is cleared. Rows of other runs are never
   touched.
R10. The cleared job copy is not NULL: `args_json` becomes `{"forgotten": true, "bundle": {"run_name": "<name>"}}`. Only the
   name is kept, so `jobs._apply_handover` (late answer for an expired job) still reads the run name and goes on without a
   crash. Any reader that needs more than the name (009e later, the page) must see `forgotten` and refuse with 「內容已被擁有者
   刪除 (content deleted by its owner)」. Add one test for the late-answer path on a forgotten job.
R11 (clarifies R2). "Over stdio" means stdio with no usable form. stdio with a client form may forget, same as `cancel`.
R12. Record `forget` in the ledger as owed web parity (docs/ROADMAP.md:98): it has no web route yet.
R13. New tests go in `platform/tests/test_keep_submissions.py`; each test names its TC id in a comment.
