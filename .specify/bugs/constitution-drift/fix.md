# Bug Fix: wording drift from the constitution, and small fixes (audit batch E)

- **Slug**: constitution-drift
- **Fixed**: 2026-09-30
- **Assessment**: ./assessment.md
- **Status**: applied

## Summary

Applied all eleven items from the assessment: aligned wording/citations with the constitution
(E1, E2, E5, E6, E7, E8), and changed behaviour on three items with tests written first
(E3, E4, E9, E10). E11 (personal cluster paths in docs/DOWNSTREAM.md, docs/HANDOFF.md) was left
untouched, exactly as the assessment specifies.

## Changes

| File | Change | Notes |
|------|--------|-------|
| `commands/setup.md` | modified | E1: "When a step fails" no longer has an open "you may attempt to fix this step" catch-all; points at `skills/operational/SKILL.md`'s off-design procedure when a step's own branches don't cover the failure |
| `commands/setup.md` | modified | E2: step 3 token path corrected to `<root>/config/.seqera_token` (`scripts/settings.sh`, `token_file`), no longer the fictional `_personal/.seqera_token` |
| `commands/setup.md` | modified | E6: "chmod 600" / "mode 600" wording replaced with the constitution's "readable by the owner only ... measured by reading it back" (two spots: step 3, and the synced-folder paragraph) |
| `commands/setup.md` | modified | E7: synced-folder paragraph now distinguishes a folder synced *inside the user's profile* (fine, owner-only ACLs) from a cloud drive mounted as its own drive letter with no ACLs (refused by `scripts/settings.sh`'s token write) |
| `commands/downstream.md` | modified | E1: added a `## When something here does not go as designed` section pointing at the off-design procedure (previously the file had none at all) |
| `commands/downstream.md` | modified | E8: citation at the background-section paragraph now cites the constitution (invariant 9), `docs/PRINCIPLES.md` named as reasoning only |
| `commands/finish.md` | modified | E1: same `## When something here does not go as designed` section added |
| `docs/PRINCIPLES.md` | modified | E8: invariants 2, 6, 7 reworded so their bold rule statements match the constitution's wording (2: added "Nextflow's own records where it is not"; 6: added "never from a per-pipeline file in this repository"; 7: removed the added "before their first real run" phrasing not in the constitution); invariant 9's title broadened from "every verifiable claim" to "anything written on a user's behalf", matching the constitution's scope |
| `docs/SITE_ADAPTER.md` | modified | E8: citation at line 27 now cites the constitution first, `PRINCIPLES.md` as reasoning |
| `skills/operational/SKILL.md` | modified | E8: opening paragraph now says the constitution decides, `docs/PRINCIPLES.md` keeps reasoning only (was "Read docs/PRINCIPLES.md ... it records what decides") |
| `skills/operational/SKILL.md` | modified | E8: fixed the reference to the nonexistent `scripts/session_start.sh` → `hooks/session_start.sh` |
| `skills/operational/SKILL.md` | modified | E4: off-design procedure's step 4 now names the repository from `.claude-plugin/plugin.json`'s `repository` field instead of the literal `zhshie/agentic-bioflow_v2` |
| `skills/operational/SKILL.md` | modified | E6: safety-net paragraph's "mode 600" replaced with the constitution's "readable by the owner only" wording |
| `skills/operational/SKILL.md` | modified | E5: H3 bullet reworded — "it must not touch the site, submit a run, or delete anything" is now stated as the intended direction, not yet enforced, with the practical instruction to confirm by hand with the user kept |
| `.claude-plugin/plugin.json` | modified | E4: added `"repository": "https://github.com/zhshie/agentic-bioflow_v2"` |
| `scripts/report.sh` | modified | E4: `REPO` is now derived from `plugin.json`'s `repository` field via `repo_from_plugin_json()`, with `REPORT_REPO` as an explicit override; falls back to the old literal only if `plugin.json` lacks the field |
| `scripts/settings.sh` | modified | E3: `set_setting()`'s `unknown` privacy branch now calls a new `warn_unmeasured_privacy()` that prints a visible warning (and how to check by hand: `icacls` on Windows, `ls -l` elsewhere) instead of returning silently; the token is still written, only the silence is fixed |
| `hooks/confirm_cleanup.sh` | modified | E9: every `mv` source (every argument but the last) is now judged against `rawdata/`, `results/` and `analysis/` and asks if any match; the destination (last argument) stays excluded since writing into those directories is normal; also recognises PowerShell's `Move-Item` via `cmdword()`, not only bash's `mv` |
| `hooks/plugin_intro.sh` | modified | E10: `has_topic()` gained the eight specialist Chinese terms the maintainer named (定序/測序/擴增子/轉錄體/轉錄組/樣本表/總體基因體/宏基因組) plus their simplified forms where different; no generic words added, so `has_action()`'s existing 分析 etc. is unchanged |
| `tests/confirm_cleanup_test.sh` | modified | E9 tests (see below); one pre-existing test (`srun mv .../rawdata/... /tmp/`) updated from expecting `warn` to expecting `ask`, since E9 supersedes the old sequencing-file-extension-only heuristic for that exact command |
| `tests/plugin_intro_test.sh` | modified | E10 tests (see below) |
| `tests/settings_test.sh` | modified | E3 tests (see below) |
| `tests/report_test.sh` | modified | E4 tests (see below) |
| `tests/off_design_single_path.sh` | modified | E1: catch-all pattern extended to also match "attempt to fix"-style wording (whitespace/newline-tolerant, since the offending phrase in setup.md was line-wrapped); `setup.md`'s special-case exclusion removed (it is an ordinary fix target in this same change, not "another agent's file" any more); added positive-control assertions that `downstream.md` and `finish.md` now point at the off-design section |

## Tests Added or Updated

- `tests/confirm_cleanup_test.sh`: `#29e` block — `mv results /tmp/x` → ask; `mv $P/rawdata/ /scratch/old` (literal, unexpanded) → ask; `mv notes.txt results/` → quiet; `mv a.txt b.txt` → quiet; `ls results && mv x y` → quiet; PowerShell `Move-Item results C:\tmp` → ask. Plus the pre-existing `srun mv .../rawdata/...` case updated to `ask`.
- `tests/plugin_intro_test.sh`: "E10" block — `幫我分析這批定序資料` routes; `幫我分析職涯選項` (generic action, no specialist topic) does not; `定序是什麼` (topic, no action) does not; `帮我分析这批测序数据` (simplified form) routes.
- `tests/settings_test.sh`: two new assertions on the existing MSYS-unknown case and the existing NOSTAT-unknown case, both now expecting `could not confirm ...` plus a by-hand check (`icacls` / `ls -l`) in stderr.
- `tests/report_test.sh`: `.claude-plugin/plugin.json` names the repository; `REPORT_REPO` override changes the no-gh fallback URL; no override still derives the same URL from `plugin.json` (not a stale hardcode).
- `tests/off_design_single_path.sh`: catch-all regex extended; `setup.md` no longer special-cased; new loop asserting `downstream.md` and `finish.md` each point at the off-design section.

## Local Verification

RED before, GREEN after, for every behaviour change (run via WSL per `docs/TESTING.md`; native Git Bash refuses the suite):

- E9 (`tests/confirm_cleanup_test.sh`): RED — 4 failures (the new `#29e` cases plus the updated `srun mv` case). GREEN — `all passed` after the `hooks/confirm_cleanup.sh` change.
- E10 (`tests/plugin_intro_test.sh`): RED — 2 failures (定序+分析 case, simplified 测序 case). GREEN — `all passed` after the `hooks/plugin_intro.sh` change.
- E3 (`tests/settings_test.sh`): RED — 4 failures (the two new assertions on each of the two existing unknown-privacy cases). GREEN — `all passed` after the `scripts/settings.sh` change.
- E4 (`tests/report_test.sh`): RED — 3 failures (plugin.json field missing, override not honoured). GREEN — `all passed` after the `plugin.json` + `scripts/report.sh` change.
- E1 (`tests/off_design_single_path.sh`): RED — `setup.md` failed once the pattern caught "attempt to fix", plus 2 failures for the new downstream.md/finish.md positive controls. GREEN — `all passed` after `commands/setup.md`, `commands/downstream.md`, `commands/finish.md` changes.

Wording-only items (E2, E5, E6, E7, E8) had no test to extend; re-read each changed paragraph in
place and confirmed nothing a user or the model needs was dropped, and ran the structural tests
that touch the same files to confirm no collateral breakage:
`tests/skill_portability_test.sh`, `tests/skill_requires_intro_test.sh`,
`tests/skill_names_command_file_test.sh`, `tests/command_layer_is_record_neutral.sh`,
`tests/command_layer_is_site_neutral.sh`, `tests/principle_9_test.sh`, `tests/principle_12_test.sh`,
`tests/column_output_relay_rule.sh`, `tests/commands_resolve_their_own_paths.sh`,
`tests/no_per_pipeline_config.sh` — all passed.

- `tests/confirm_cleanup_test.sh` run natively in Git Bash (required — it must pass there too):
  all passed, `real 4m52.587s`.
- `hooks/confirm_cleanup.sh` timing, native Git Bash, `rm -rf .../results` and `mv .../results /tmp/x`,
  averaged over several runs: before ~1.2-1.6 s/call, after ~1.0-2.1 s/call (single-call noise on this
  machine is roughly ±0.5-1 s either way; a 5-call average for the `mv` case was 1.31 s before vs.
  0.96 s after). No consistent regression — the new mv-source check is a handful of in-shell `[[ =~ ]]`
  comparisons per segment, no new subprocess.
- `bash tests/run_all.sh` (full suite, WSL): see below.

## Deviations from Assessment

- E1's remediation named only `commands/setup.md`'s catch-all and referred to `commands/downstream.md`
  and `commands/finish.md` as having "failure branches that point nowhere." On inspection neither file
  contained any catch-all phrase at all (matched or not) — they had no failure-handling section
  whatsoever, unlike `launch.md`/`runs.md`/`setup.md`. Read "point nowhere" as "point nowhere because
  there is nothing to point," and added a short `## When something here does not go as designed`
  section to each, mirroring what the other command files already do, rather than editing text that
  did not exist.
- `tests/off_design_single_path.sh`'s existing special-case for `setup.md` ("owned by another agent in
  this wave, read-only from here") was removed rather than kept, since this fix is the one editing
  `setup.md`'s catch-all directly — keeping the special-case would have hidden the exact regression the
  assessment described.

## Follow-ups

- None identified beyond what E11 already excludes.

## Developer review (2026-09-30)

- `commands/setup.md` synced-folder paragraph: removed the example "e.g. Google Drive for Desktop's default location" as the in-profile case. It had no source, and Drive for Desktop's streaming mode mounts its own drive letter (this maintainer's workspace is on `G:`), so it may be the opposite case. The paragraph now says step 3 does not guess: it reads back who can open the token file and refuses when anyone beyond the owner can.
- Reviewed E1's added "When something here does not go as designed" sections in downstream.md/finish.md (deviation accepted: neither file had any failure text), and the E5 rewrite in SKILL.md (the practical instruction and the settings-file warning are kept).

## After independent acceptance (2026-09-30)

The reviewer found no regression against main and failed two items; both fixed test-first, with the E9 gaps it listed:

- **E4**: the maintainer check still compared the login with a literal `zhshie`. It now compares with the owner of `$REPO`; the fallback repository is gone (no `repository` in plugin.json and no `REPORT_REPO` → reports stay queued, said so); SKILL.md no longer names the repository literally. `tests/report_test.sh`: a fork's owner is the maintainer, zhshie is not on a fork (both red before).
- **E1**: `tests/off_design_single_path.sh` matched one literal phrase. It now catches the ordinary variants (try/attempt(s) (to/a) fix, fix it yourself, work around it, figure it out yourself, improvise) and self-tests on planted paragraphs: 5 red with the old pattern, all caught now; a paragraph that points at the off-design section still passes.
- **E9 gaps**: `mv -t` / `--target-directory` (every argument a source), brace lists (`mv results{,.bak}`, `mv {rawdata,old}`), `rsync --remove-source-files`, `rename`, PowerShell `Move-Item` with named parameters in any order, `mi`/`move`/`Rename-Item`/`rni`/`ren` under a PowerShell tool, and a pipeline-fed `Move-Item` → ask. `grep -rn mv results` no longer asks (readers of text are not movers). 11 new cases, red before.
- **E7**: setup.md said the token file is read back and refused; it is the settings file written beside it. Corrected.
- **E8**: three more places in SKILL.md cited PRINCIPLES.md as the authority for a rule; now the constitution.
- **E10**: `宏基因体`/`宏基因體` (mixed forms) added.

Left as found (reviewer: not in scope): the settings summary still prints the token as `present` when its privacy could not be measured; Chinese questions containing 失敗/分析 already routed before this change.

WSL `tests/run_all.sh` 74/74.

## Final (2026-09-30)

Re-review of cad04df passed (zero regressions against main; all E9 shapes ask; E1/E4/E7 fixed). Its timing note - PowerShell Move-Item started one process per argument to lowercase it - fixed in-shell (838 ms natively with six arguments). Three extra asks it noted (mv -t INTO results, a brace destination, any pipeline-fed Move-Item) go to #35.
