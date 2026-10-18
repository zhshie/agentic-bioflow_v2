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
