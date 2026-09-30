# Bug Verification: safety-net-bypass

- **Slug**: safety-net-bypass
- **Verified**: 2026-09-30
- **Verdict**: resolved under the maintainer's stopping rule (independent review, round 4: recommend merge)

## Stopping rule (maintainer, 2026-09-29)

Merge when an independent review finds (1) no regression against `main` — nothing `main` denied/asked/gated/warned that the branch now lets through silently (a pure shell comment excepted), and no read-only command `main` passed that the branch now blocks — and (2) no remaining high-severity bypass. Medium/low findings go to a follow-up issue. The gates are heuristics (constitution: defence in depth, not a sandbox) and cannot be proven complete.

## Review history

| Round | Reviewer verdict | What it found |
|---|---|---|
| 1 (939576b) | FAIL | Quotes glued to paths, `/bin/rm`, `\rm`, braces, globs, `$(...)`, perl/python system(), PowerShell `ri`, new false alarm on `grep del` |
| 2 (ec50965) | FAIL | Regression: `srun rm` etc.; long scripts pushed the gates past their timeout under Git Bash (~50 s / ~27 s) — a timed-out hook lets the command run |
| 3 (ee7e247) | FAIL | Regressions: wrapped `find -delete` / `rsync --delete` / `mv`; launches handed on to tmux/su/flock inside ssh |
| 4 (828f99f) | **PASS — recommend merge** | 196 new cases vs `main`: 0 weaker, 0 read-only stricter; no high-severity bypass; slowest gate 1.75 s natively |

Every finding of rounds 1–3 was reproduced, written as a failing test first, then fixed. The two items round 4 left UNVERIFIED were checked by the developer: the 11 round-4 tests are red on ee7e247 (run 2026-09-29 in WSL against that commit's hooks) and `tests/run_all.sh` is 73/73 in WSL.

## Checks

- WSL `tests/run_all.sh`: 73/73.
- Native Git Bash: `confirm_cleanup_test.sh` all passed (200-line here-doc judged in 1 s); `confirm_launch_test.sh` all new cases pass, only the pre-existing D3 "NOT on MSYS" case fails (#30).
- Timing, native Git Bash, branch vs main: cleanup short 1.0 s vs 4.7 s; 150-line heredoc 1.05–1.37 s; launch 1.5–1.75 s. All gate timeouts 30 s.

## Remaining (medium/low, same on main) → follow-up issue

`flock -c` / `su -c` / `tmux` outside a nested shell; PowerShell `cmd /c rd /s /q`; `rsync --remove-source-files`; `mv` then `rm` (see #33); `cat <<EOF | sudo -u x bash` / `| srun bash` / `| python3`; `R -e`; relative targets after `cd …/results`; `perl remove_tree`; `git clean -fdx`; PowerShell `Start-Process nextflow`; `rsync --dry-run --delete` false alarm; `xargs -I{} rm` denies where ask would do.

## Not yet done

Manual half of `docs/TESTING.md` (hooks changed): the maintainer, after updating the installed plugin and restarting Claude Code.
