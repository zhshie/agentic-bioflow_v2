# 007b follow-up 1: what the first real launch showed (A-tier, no spec change)

Found during the manual acceptance on NCHC on 2026-10-13 (TC-047). Nothing here changes what the plugin should do;
each item brings the code back to what `spec.md` already says.

## F1. A refused launch is shown as "result unknown"

What happened: the first launch (`ampliseq-mt-0920-rerun`, job 6) was refused by the agent's preflight because the
shared SSH connection had expired. The agent's result says "預檢未通過，沒有建立任何東西". `abf-platform launches`
still printed `未送出：代理沒有回報 Slurm 工作編號（結果不明時請查國網上的專屬資料夾…）`.

Spec: US2.2 — on failure, "回報原因…並說清楚國網上留下了什麼". FR-009 — the record holds facts only.

Wanted: `launches` reads the agent job linked to the launch (`jobs.confirmation_id` = the launch's confirmation) and
prints one of these, in place of the current line, for a launch with no Slurm job number:
- job `refused` → `  被代理拒絕：<the agent's message, escaped with terminal.esc>`. The message already says what was left
  on the site; the platform does not add its own claim.
- job still queued or claimed → `  等代理處理中（工作 <id>）`.
- job `failed`/expired/no job found → keep the current "結果不明…" line (we really do not know).
The lines for launches that have a Slurm number do not change.

## F2. Reusing the name of a refused launch erases the refused launch's record

Correction after the verifier's review: the second try was not actually made with the same name — I (developer-agent)
renamed it to `ampliseq-mt-0920-r2` in advance because I saw the UNIQUE constraint. `jobs.enqueue_confirmed`
(`platform/abf_platform/jobs.py`) already frees the name of a launch that was refused outright, but it does so with
`DELETE FROM launches` before the INSERT, which throws away a fact (FR-009), and no platform test covers it.
The behaviour below is what to keep; the DELETE is the bug.

Wanted: a new launch may reuse a run name only when every earlier launch with that name has no Slurm job number AND
its agent job is `refused`. In every other case (submitted, waiting, unknown result) the name stays taken and the
launch is refused before the terminal question, with the reason. The refused launch's row is kept (it is a fact);
how the table allows two rows with one name is the executor's choice, with a migration for an existing platform.db
(the live one at `~/abf-station-test/state/platform.db` has the UNIQUE constraint and a refused row) that keeps all rows.
The run folder on the site is still checked by the agent's preflight ("專屬資料夾不存在"), which does not change.

## F3. `tests/platform_test.sh` runs at the edge of the 300 s per-test limit

CI run 38252054087 took 298 s against `PER_TEST_TIMEOUT=300` in `tests/run_all.sh`. One slow CI machine turns
green into a false timeout.

Wanted: CI and WSL keep running every platform test, none skipped (SC-004), and the run has clear headroom:
under 200 s on CI, or split into more than one `run_all` entry each well under the limit. Raising the limit alone is
not the fix (the comment in run_all.sh says the limit only catches hangs). Do not change `.github/` (ask-first);
if the only good fix needs a CI change, stop and report.

## Out of scope

Relay extra domains (an operations task, not code); 009; anything in `plugin/` (the plugin is paused).

## Constraints for the executor

- The live acceptance run is using `~/abf-station-test/` in WSL right now, with `abf-platform serve` on
  127.0.0.1:8787 and an agent process. Do not read, write, stop or restart anything there, and do not use port 8787.
  Tests use their own temporary folders and fake site, as today.
- `platform/abf_station/launch.py` is the one entry in LAUNCH_ALLOW; F1–F3 should not need to touch it.
