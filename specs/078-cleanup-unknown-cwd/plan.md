# Plan 078: a relative delete after a lost working directory asks instead of passing

- **Slug**: 078-cleanup-unknown-cwd
- **Branch**: `fix/078-cleanup-unknown-cwd`, base **`main`** (v2 line: bug fixes and Safety Net tightening only)
- **Created**: 2026-10-16 by the developer-agent
- **Umbrella**: GitHub issue #78 (found by the verifier during #76/#75, 2026-10-10).
- **Tier**: A (tightening the Safety Net; nothing is loosened).

## 給維護者

1. 這個修補讓清理關卡（confirm_cleanup.sh）在「搞不清楚目前在哪個資料夾」時多問你一次，而不是直接放行。
2. 會多問的情況只有四種：`cd -`、單獨一個 `cd`、`popd` 之後、用引號包起來的反斜線路徑，而且後面接的是相對路徑的刪除。
3. 原本會擋（deny）的仍然擋；原本問的仍然問；不會有任何一種變得更寬鬆。

## Facts (origin/main, 2026-10-16)

- `hooks/confirm_cleanup.sh:406-410`: `VCWD` comes from the hook input's `"cwd"` by regex, with no process. A missing or non-absolute cwd leaves `VCWD=""`.
- `:1011`: `cd`/`pushd` with an empty target, `-`, `~*`, `*$*` or a backtick sets `VCWD=""`. `:1014`: a relative cd from an empty `VCWD` stays empty.
- Every relative-target consumer skips judging when `VCWD` is empty: the deletes at `:1521-1525`, find roots at `:1396`, brace lists at `:844`. So the delete passes (the bug).
- `popd` has no handler (falls to `*)` at `:1076`); `VCWD` keeps the value of the last `pushd`/`cd`, so the state is stale. The issue's case `cd results; pushd /tmp; popd; rm -rf x` passes because `VCWD=/tmp`.
- `:1007-1014` reads `SEG` with quotes stripped, so `cd "res\ults"` resolves as `res/ults` and cannot be told from unquoted `res\ults`.
- `:194` is the single jq fast-path call; in_use early exit `:187`; deadline `:919-933` (20 s total, 15 s deferred; `hooks.json` 30 s); candidate cap 8; asks emitted at `:1690` via `abf_emit`.
- Pinned tests that currently expect **pass** for lost-cwd shapes (flipped on purpose here, pass → ask only): `tests/confirm_cleanup_shapes.txt` lines 74-75 and the `popd` pass lines (2, 3, 6-9, 141-150, 157-168 — re-verify each).
- Must stay green and unedited: every deny and ask in `confirm_cleanup_test.sh` (incl. TC-056, the R1 `popd` cases, TC-034/036, the #62 deadline cases); `confirm_cleanup_behind_heredoc_test.sh`; `confirm_cleanup_candidates_timing_test.sh` (branch ≤ main + 8000 ms); `confirm_cleanup_shapes_main.txt`; the `t` cases that send no cwd; `confirm_cleanup_test.sh:496`, TC-041 to 043 and `:855` (variable / `~` / alias targets stay pass in this PR).

## Design decisions (developer-agent)

1. **A new monotone flag `CWD_LOST`**, not a reuse of `VCWD=""` (which also means "no cwd in input" and "cd to `$var`/`~`/alias", pinned as pass). `CWD_LOST` is set only by: `cd`/`pushd` with target `-` or none; `popd` and `pop-location`; a `cd`/`pushd` target that was quoted and contains a backslash.
2. **Additive only.** `VCWD` and `CANDS` unchanged; `CWD_LOST` adds an ask only where the verdict would otherwise be pass. An absolute `cd`/`pushd` clears it. It lasts for the rest of the command.
3. **Where it asks.** Helper `lost_rel <word>`: true when `CWD_LOST=1`, the word is relative, and it has no variable. Called at the three `VCWD` consumers (deletes, find roots, brace lists), adding to `UNRESOLVED` like the existing "cannot verify" entries; `mv`/`move-item` only for E9 source arguments.
4. **Quoted backslash.** The cd handler checks the raw segment once for a quote adjoining a `\` in the target and sets `CWD_LOST`.
5. **Performance.** No new process, no new jq call, `:194` untouched; deadline, cap and budgets untouched. The candidates-timing test is the guard.
6. The new UNRESOLVED entry carries its own text ("working folder unknown after `cd -` / `cd` / `popd`: … confirm"); the `:1690` wording is not edited.

## Changes, in order (red first)

1. In `tests/confirm_cleanup_test.sh`, after TC-043, add four red cases expecting **ask** (cwd `/tmp`, `P` as defined): `cd $P; cd -; rm -rf x`; `cd $P/results; cd; rm -rf x`; `cd $P/results; pushd /tmp; popd; rm -rf x` and `cd $P; popd; rm -rf x`; `cd $P; cd "res\ults"; rm -rf x`. Add green controls: `cd -; rm -rf $P/tmp` stays pass; `cd -; cd $P; rm -rf x` stays pass; one PowerShell `cd -` case. Run → the reds fail; record in the ledger.
2. Implement `CWD_LOST` in `hooks/confirm_cleanup.sh` (initial value, cd arms, new `popd`/`pop-location` arm, `lost_rel` at the three consumers). Reds go green.
3. Flip the shapes lines listed under Facts from pass to ask; change no deny or ask line. The ledger lists each flipped line with the reason ("lost cwd now asks").
4. WSL `bash tests/run_all.sh` (jq 1.7.1) green; `confirm_cleanup_behind_heredoc_test.sh` green; timing test main vs branch ms recorded.
5. **Measure the new asks over `tests/confirm_cleanup_shapes.txt` and `tests/confirm_cleanup_shapes_main.txt` only** (no session transcripts): count lines whose verdict changes from pass to ask; every changed line must be one of the four lost-cwd shapes. Put the count in the ledger.
6. `CHANGELOG.md`: one line under Unreleased. Update `docs/PRINCIPLES.md` only if it describes unknown-cwd as pass.

## Not in this PR

- No change to variable, `~` or alias cwd targets, nor to the "no cwd in the hook input" case (they stay pass; follow-up after measurement).
- No real directory-stack model for `pushd`/`popd`.
- No change to the jq fast path (issue #95 is the next PR in this lane), the deadline, `hooks.json`, `confirm_launch.sh`, or any deny rule.

## Constitution Check

- Safety Net: tightens only (pass → ask for four named shapes; no deny or ask weakened; output path still `abf_emit`).
- Stays inside the 30 s hook timeout and 20 s deadline, no new process.
- Tests red first; flipped pass expectations listed and justified; no deny/ask expectation edited.
- Protected path (`hooks/`): the developer-agent runs `/code-review` on the PR before merge.
