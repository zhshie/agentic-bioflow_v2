# Plan: constitution 4.0.0 — one submission path of our own, behind the user's confirmation

Branch `amend-4.0.0-launch-path`. Tier C: the maintainer approves and merges (Governance).
Written by the developer-agent on 2026-10-11.

## Revision 2 (2026-10-11, after the verifier's contract review): this section overrides the text below where they differ

The contract review had four must-fixes. Each is answered here.

1. **"Exactly one" becomes "at most one"; the check enforces the "at most".**
   - In principle 2, the sentence "There MUST be exactly one submission path of our own: ..." becomes "There MAY be at most one submission path of our own: ...".
   - The amendment record says plainly that none exists when 4.0.0 is merged and that 007b builds it.
   - The check fails when `LAUNCH_ALLOW` holds more than one entry, with the message `LAUNCH  only one submission path is allowed (I.2); found <n>`.
   - The pinned phrase in `platform_direction_docs_test.sh` becomes `There MAY be at most one submission path of our own`.
2. **`platform/abf_station/handlers.py` lines 17 and 162 must leave scan 1's shape by rewriting that file, never through an allow-list or a weaker regex.**
   - The file only runs `command -v` checks and submits nothing. It is in neither `SUBMIT_ALLOW` nor `LAUNCH_ALLOW`.
   - The check ids in `CHECK_ORDER` (`"sbatch"` and the others), their order, the `has_sbatch` field and every user-visible check text stay the same.
   - The executor chooses the smallest rewrite that keeps the literal word from following an opening quote. One example: name the tools once in a single string that does not start with a submit command, then split it.
   - A comment at that place says why: the scan of principle 2 treats a quoted `sbatch` as a command.
   - `CMDS`, `PFX` and the quote rules of the scan stay byte-for-byte the same.
   - Platform pytest stays green.
3. **The version pins that must also change:**
   - `tests/constitution_scope_test.sh`, lines 29 and 31: `**Version**: 4.0.0` and `**Last Amended**: 2026-10-11`. The 2.0.0 and 3.0.0 entry assertions stay.
   - `tests/platform_direction_docs_test.sh`:
     - TC-001 becomes the 4.0.0 version line.
     - TC-059 `CLAUDE.md points at constitution 3.0.0` becomes `constitution 4.0.0`.
     - TC-059 for the README becomes `the truth under constitution 4.0.0`.
   - `CLAUDE.md`, line 11: `3.0.0, principle 2` becomes `4.0.0, principle 2`.
   - `README.md`: `the truth under constitution 3.0.0` becomes `the truth under constitution 4.0.0`.
   - No assertion is removed or loosened.
4. **The confirmation test is bound tightly.**
   - A `LAUNCH_ALLOW` entry is `<file>|<test file>::<test name>|<why>`.
   - `<file>` must be under `platform/abf_platform/` or `platform/abf_station/`. An entry for any other path, `scripts/` included, fails with `LAUNCH  <file>: only platform code may hold the launch path`, and a submission in `scripts/` is never excused by it.
   - `<test file>` must be under `platform/tests/` and must contain a definition of the test: a line matching `^[[:space:]]*(async[[:space:]]+)?def[[:space:]]+<test name>[[:space:]]*\(`. A mention in a comment or a string does not count.
   - Self-tests add entries through `LAUNCH_ALLOW_EXTRA`, which is read only when `NO_RUN_STATE_ROOT` is set. On the real tree that variable is ignored; a self-test proves it.
   - New self-tests, besides the five below:
     - the second entry fails;
     - a test name found only in a comment fails;
     - an entry for `scripts/` fails;
     - `LAUNCH_ALLOW_EXTRA` without `NO_RUN_STATE_ROOT` is ignored;
     - scans 2 and 3 do not read `platform/` (`nohup` in `abf_station/x.py` and `runs.db` in `abf_platform/x.py` both pass).

**Should-fix, also taken.**
- `docs/ROADMAP.md`, the Stage 1 row: add a sentence after the slice 1 sentence: "Slice 2 (007b) launches through the agent, under constitution 4.0.0, behind the user's confirmation."
- 007b must also revise `platform/tests/test_scope.py` TC-071 and `platform/tests/test_station_static.py` TC-084, which forbid submission in platform code under principle 2. They are untouched here, and are recorded as 007b work in the amendment record.
- The check's header keeps "a net, not a proof".

**The Safety Net's honesty (TC-045).** The 4.0.0 record says that the Safety Net's scope (sessions where the plugin is in use, guarded by hooks) does not reach the platform's own path, so principle 2 itself carries the confirmation requirement for that path, and no hook guards it.

## Why

On 2026-10-11 the maintainer set the order:

- 「照原本路線」
- 「雲端伺服器（像 Seqera 有 AWS 等）也要一起」
- 「雲端伺服器不限於 AWS，請直接參考 Seqera Platform 的設計」

When asked to begin this amendment, he said 「開始」.

Slice 1 of feature 007 (PR #83, merged 2026-10-11) gave the platform a station agent that reaches the site, but it cannot launch. Launching is the next slice, 007b. Principle 2 as written in 3.0.0 says there MUST be "no submission script of our own". That was right while Seqera Platform launched every run. A self-hosted platform modelled on Seqera has to do what Seqera does: hand the Nextflow head job to the site's scheduler. Seqera does this through its own submit step (`specs/007-station-agent/research.md`, "Where the head job runs": a cluster job in the head queue, for every HPC type). Nextflow has no command that submits its own head job. Nothing maintained that is open source does it for a Slurm site reached through a user's shared SSH connection; Tower Agent is closed and talks only to Seqera.

So principle 2 has to allow exactly one submission path. It must keep its purpose: no second truth about a run, no state machine, no monitoring daemon. The confirmation the Safety Net demands of a launch must hold on this path too.

## What changes

### 1. Principle 2 (`.specify/memory/constitution.md`), the new text

> - **2.** Nextflow's own records (trace, report, log, and the events its `nf-tower` plugin emits)
>   are the truth about a run. While the plugin uses Seqera Platform, Platform shows them; where
>   Platform's display and Nextflow's own records disagree, Nextflow's records win. No file in
>   this repository MAY keep a second copy of a run's state, and there MUST be no state machine
>   and no monitoring daemon beyond the channels its check allow-lists. There MUST be exactly one
>   submission path of our own: the station agent's launch job, which hands the Nextflow head job
>   to the site's own scheduler the way Seqera Platform does, and runs only after the user has
>   seen the full launch command and confirmed it. A file that submits is allow-listed by the
>   check together with the test that refuses an unconfirmed launch; nothing else submits. After
>   the hand-off, everything known about the run comes from Nextflow's records. Where the backend
>   is Seqera, the command layer follows Seqera's nouns (compute environment, then pipelines →
>   datasets → launch, then runs).
>   *Check:* `tests/no_second_run_state_test.sh` (its submission scan covers `scripts/` and
>   `platform/`).

The rationale paragraph under principle I gains one sentence: the one submission path exists because a self-hosted platform must do Seqera's submit step, and only the user's confirmation lets it run.

### 2. The check (`tests/no_second_run_state_test.sh`): stricter, never looser

- **Scan 1 (SUBMISSION) also reads `platform/`.**
  - Python and shell files under `platform/abf_platform/` and `platform/abf_station/` join the code lines that scan 1 sees.
  - Test files under `platform/tests/` are excluded, because the fake site's stand-ins must be called `sbatch`.
  - Scans 2–4 stay on `scripts/` alone. The platform's index and `platform.db` are the index of `docs/adr/0004`, not a run-state store; the rebuild tests of 008 hold that index.
- **A new allow-list, `LAUNCH_ALLOW`.** Its entries take the form `<file>|<test file>::<test name>|<why>`.
  - A file in `platform/` that submits passes only if it is listed there.
  - The named test must exist: the file must exist and contain that test name.
  - That test is the one proving that an unconfirmed launch is refused.
  - A missing test fails with `LAUNCH  <file> submits, but its confirmation test <name> does not exist`. A stale entry fails like the other stale entries.
  - **In this PR the allow-list is empty.** 007b adds the one entry, together with its test.
- **New self-tests**, at the bottom with the others, each proving it can turn red:
  - `sbatch` in a `platform/abf_station/x.py` with no entry fails.
  - The same file listed with a test that does not exist fails.
  - The same file listed with a test that exists passes.
  - `sbatch` in `platform/tests/x.py` passes.
  - A stale `LAUNCH_ALLOW` entry fails.
- The header comment is updated: four scans, scan 1 covering `platform/`, and the new allow-list.

### 3. Documents that cite principle 2 (Governance: same PR)

- `tests/platform_direction_docs_test.sh`, TC-004:
  - The expected phrase `no submission script of our own, no state machine, and no monitoring daemon beyond the channels its check allow-lists` becomes two phrases:
    - `no state machine and no monitoring daemon beyond the channels its check allow-lists`
    - `There MUST be exactly one submission path of our own`
  - Add expectations for `runs only after the user has seen the full launch command and confirmed it` and `everything known about the run comes from Nextflow's records`.
  - Every other TC line stays.
- `README.md`, line 56: "no submission script" becomes "no submission script outside the one confirmed launch path (constitution 4.0.0)". The rest of the sentence stays.
- `hooks/confirm_launch.sh`, line 7: **not touched.** It is a comment about the plugin's v2 path, which still launches through Seqera; it stays true, and hooks are a protected path.
- `docs/PRINCIPLES.md`: if it restates principle 2, correct it to match; if it does not, nothing.
- `CLAUDE.md` (repo root): the same.
- `docs/ROADMAP.md`:
  - In "Principles waiting for a check", the row "Every platform write tool (launch, delete, clear `work/`) refuses without the user's confirmation step" gains a note: *4.0.0 binds the launch path to this check; 007b builds it for launch.* The row stays.
  - 007b (Stage 1) is marked as unblocked by 4.0.0.

### 4. The amendment record and the version

- Add `### 4.0.0 (2026-10-11): one submission path of our own, behind the user's confirmation` under `## Amendments`, after 3.0.0. It has the same parts as 3.0.0:
  - **Rationale**, with his words quoted.
  - **What changes.**
  - **Impact on existing deployments.** None. No hook, script, command or skill changes behaviour. The allow-list is empty, so the repository still has zero submission paths until 007b. The plugin still launches through Seqera behind `hooks/confirm_launch.sh`.
  - **Version.** MAJOR, because principle 2 is redefined.
  - **Approval.** The maintainer approves and merges.
- The footer becomes `**Version**: 4.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-10-11`.
- The Safety Net is unchanged, word for word.
  - Its launch rule ("shown in full and waits for explicit confirmation") already says what we want. Its scope (sessions where the plugin is in use) does not reach the platform's own path, so principle 2 itself carries the confirmation requirement for that path.
  - Moving gates into the platform's tool layer is still a waiting principle.

## Constitution check of this amendment

| Rule | How this amendment meets it |
|---|---|
| Principle 1 | Seqera's submit step and Tower Agent are named; neither serves (closed, Seqera-only); Nextflow has no head-job submit. |
| Principle 2 | It stays a ban on a second truth, a state machine and a daemon. The single submission path is bound to a confirmation test and to Nextflow's records. |
| Principles 3, II-4, V, VI | Not touched. |
| Safety Net | Unchanged. No relaxation: the only new permission requires the confirmation that the Safety Net already demands of a launch. |
| Governance | Rationale, impact, version bump and the documents that cite the rule are all in one PR, and the maintainer merges it. |

## Not in this PR

- The launch job itself (007b).
- The confirmation step's form: a terminal yes/no first, and the web confirmation page in 009.
- Moving the Safety Net's gates into the platform's tool layer.
- The other waiting principles, including the run index rule whose check now exists (008); that one goes in its own amendment PR.

## Verification

- `bash tests/no_second_run_state_test.sh` passes on the branch, and every new self-test case turns red when its condition is removed (mutation).
- `bash tests/platform_direction_docs_test.sh` passes.
- WSL `run_all.sh` is no worse than main: 99/100, with `conditions_matrix` failing on both for an environmental reason. CI shows 100/100.
- verifier ACCEPTANCE against the confirmed test cases; built-in `/code-review` as the security review, since the constitution and a check file are protected paths.
