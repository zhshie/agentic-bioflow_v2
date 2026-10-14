# 007b follow-up 3: small things the NCHC acceptance showed (A-tier, no spec change)

Source: `specs/007b-launch/acceptance-nchc.md` (2026-10-13, TC-047 and TC-048 notes). Each item brings the code back
to what `spec.md` / 008 already promise.

## G1. `get_run` of a failed run does not say why
TC-048: the run was cancelled; `get_run` shows `failed`, 49/50 tasks, 1 pending, and no reason at all. Nextflow's
`complete` message carries `workflow.errorMessage` (and `errorReport`); the receiver (`platform/abf_platform/receiver.py`
`complete`) only uses `errorReport` to fill `failed_tasks`, and a cancel has no failed task.
Wanted: the run keeps Nextflow's own reason (`workflow.errorMessage`, else the first line of `errorReport`), bounded in
length and escaped like every other text shown, and `get_run` shows it for a failed run (nothing for a succeeded one).
Facts only (FR-009): Nextflow's words, not a reason the platform makes up. `rebuild` from the run folder must give the
same field where the log holds it, or leave it empty — say which in the report. A migration for an existing index.db
keeps every row.

## G2. A 401 warning in Nextflow's log after `complete`
TC-048: after the run ended, Nextflow logged one 401 from the platform: the launch's token is revoked inside `complete`
(`store.revoke_token`), and Nextflow sends at least one more message for the same run after it.
Wanted: no 401 for messages Nextflow sends for the same run after its `complete`; those messages change nothing that
`complete` recorded (no status flip, no counts going back). The token still cannot create a new run, cannot touch any
other run, and stops working entirely in the end (a short, fixed grace after `complete`, or a rule "ended: only no-op
for its own run" — executor's choice, written in the report). Find from Nextflow 26.04.7 / nf-tower 1.28.3 source
(already pinned for 008) which message(s) follow `complete`, and cite the line.

## G3. Files in the run folder are wider than the folder
TC-047: `head.sh` is 711 and `slurm-*.out` 644 inside the 700 run folder (nothing leaks, the folder is 700, but the
files should not depend on that). Wanted: every file the launch writes is 600 (`head.sh` 700 if it must be executable),
and Slurm's output file is created 600 — e.g. by running `sbatch` under `umask 077` (Slurm takes the submitter's
umask), or another way the executor shows works with Slurm. The fake site must check the modes.

## Out of scope
- "Report/Timeline file already exists" warnings (TC-048): the CE config does not set report/timeline; the cause needs
  the site log, which developer-agent will read when the SSH connection is back. Not for the executor.
- Relay extra domains (operations); 009 (dev mode, cancel without confirmation); `plugin/`.

## Constraints for the executor
- Do not touch `~/abf-station-test/`, port 8787, or the NCHC site; tests use temp folders and the fake site.
- Do not change `.github/`. `platform/abf_station/launch.py` is in LAUNCH_ALLOW; G3 may touch it only where needed.
