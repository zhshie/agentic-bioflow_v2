# Fix: cd-target-backslash

- **Branch**: `fix/76-cd-target-backslash` (RED a1094f5, GREEN see `git log`)
- **Changed**: `hooks/confirm_cleanup.sh` (the only file under `hooks/`); `tests/confirm_cleanup_test.sh` (end of the #66 section: TC-001..036, 041..043 and seven plan cases). `tests/confirm_cleanup_behind_heredoc_test.sh` is unchanged and runs every one of them again behind a large here-doc (TC-039); its awk count stays 3 (TC-040).

## What changed

- **Two candidate folders.** `VCWD_B` sits next to `VCWD`. Every relative target is judged against `VCWD` and, when `VCWD_B` differs, against `VCWD_B` too; findings only add, so the stricter verdict wins. All three resolution sites do it: `judge_word`, `find`, and the delete / `mv` source loop. The rclone remote-path branch saves, clears and restores `VCWD_B` as well.
- **Copies update `VCWD_B` only.** A dropped-backslash copy (#74) starts from the `VCWD_B` the segment before it had and leaves its result there; `VCWD` and the stack still go back to what the original left (#74's rule). That is how `cd res\ults` leaves `VCWD=<run>/res/ults` and `VCWD_B=<run>/results`, and `c\d results` (whose original is not a `cd`) moves `VCWD_B`.
- **Location cmdlets.** `Set-Location`, `sl`, `chdir`, `Push-Location`, `Pop-Location` (any case), target = first non-option word or `-Path` / `-LiteralPath` (also `-Path:X`; `-StackName` takes a word). Under the PowerShell tool they move both views like `cd` / `pushd` / `popd`. Under Bash they are not built-ins: Set-Location / sl / chdir / Push-Location move `VCWD_B` only, so the old folder is judged beside the new one. An unreadable target (`$d`, `~`, none) leaves the folder where it was; `cd` / `pushd` keep main's "unknown".
- **Real stack.** `pushd` / `Push-Location` push, `popd` / `Pop-Location` pop, per view. A pop with an empty stack changes nothing, as on main (issue #78).
- **Lister verdict may only tighten.** After the copy, `LISTER_OK` is 1 only if the original and the copy both left it 1. `Get-ChildItem res\ults | Move-Item ...` now asks like `Get-ChildItem results | ...`.
- `CW_HANDLED` gained `popd|set-location|sl|chdir|push-location|pop-location`.

## Evidence (WSL, jq 1.7.1; session cwd /tmp, R = /work/u9613010/lab_runs/x)

Every row that changes. All other TC rows (TC-010..013, 025..027, 032..038, 040..044) give the same verdict on main and on the branch.

| TC | Command | Tool | main | branch |
|---|---|---|---|---|
| TC-001 | `cd R; cd res\ults; rm -rf x` | Bash | pass | deny |
| TC-002 | `cd R; cd raw\data; rm -rf x` | Bash | pass | deny |
| TC-003 | `cd R; cd wo\rk; rm -rf x` | Bash | pass | ask |
| TC-004 | `pushd R/.nextflow/plug\ins; rm -rf x` | Bash | pass | deny |
| TC-005 | `cd R/res\ults; rm -rf .` | Bash | pass | deny |
| TC-006 | `cd R; c\d results; rm -rf x` | Bash | pass | deny |
| TC-007 | `cd R; pu\shd results; rm -rf x` | Bash | pass | deny |
| TC-008 | `cd R; cd res\ults; find . -delete` | Bash | pass | deny |
| TC-009 | `cd R; cd raw\data; mv x y` | Bash | pass | ask |
| TC-014 | `Set-Location R/results; Remove-Item -Recurse x` | PowerShell | pass | deny |
| TC-015 | `sl R/results; Remove-Item -Recurse x` | PowerShell | pass | deny |
| TC-016 | `Push-Location R/results; Remove-Item -Recurse x` | PowerShell | pass | deny |
| TC-017 | `Set-Location R/results; rm -rf x` | Bash | pass | deny |
| TC-018 | `Set-Location -Path R/results; Remove-Item -Recurse x` | PowerShell | pass | deny |
| TC-019 | `Set-Location -LiteralPath R/results; ...` | PowerShell | pass | deny |
| TC-020 | `Set-Location -Path:R/results; ...` | PowerShell | pass | deny |
| TC-021 | `SET-LOCATION R/results; ...` | PowerShell | pass | deny |
| TC-022 | `cd R; chdir results; ...` | PowerShell | pass | deny |
| TC-023 | `cd R; Set-Location results; ...` | PowerShell | pass | deny |
| TC-024 | `cd R; Set-Location res\ults; ...` | PowerShell | pass | deny |
| TC-028 | `Get-ChildItem res\ults \| Move-Item -Destination x` | PowerShell | pass | ask |
| TC-029 | `Get-ChildItem raw\data \| Move-Item -Destination x` | PowerShell | pass | ask |
| TC-030 | same as TC-028, session cwd R | PowerShell | pass | ask |
| TC-031 | `gci res\ults \| Move-Item -Destination /tmp/y` | PowerShell | pass | ask |
| plan | `cd R; pushd results; popd; rm -rf x` | Bash | deny (popd ignored) | pass |
| plan | `cd R; pushd /tmp; popd; pushd res\ults; rm -rf x` | Bash | pass | deny |
| plan | `cd R; Push-Location results; rm -rf x` | Bash | pass | deny |

Intended differences from main (the branch passes, main denies or asks): see "Remaining intended differences" under Review round 1.

Controls pinned as unchanged: TC-010 `cd res\ults; cd ..` pass, TC-011/012 `re\ports` pass, TC-013 `cd /tmp` pass, TC-033 `Get-ChildItem re\ports | Move-Item` pass, TC-032 absolute lister ask, TC-034..036 deny, TC-041..043 (variable, `$(...)`, alias) pass as on main.

## RED / GREEN

RED a1094f5: the 27 new cases listed above fail. GREEN: all of `confirm_cleanup_test.sh` (also behind the here-doc), `guard_plugin_files_test.sh` and the rest pass; see the PR for the full-suite result.

## Review round 1

The security review found cases that main denies and the first GREEN (r0, 5a08db8) passed. One general rule replaces patching them one by one: **a directory change moves both views only when the gate can model it exactly** - a plain `cd` / `pushd` / `Set-Location` / `Push-Location` to a literal path (no `* ? [ ( ) @(`, no `$`, backtick or `~`, not `-`, no `-StackName`), or a bare `popd` / `Pop-Location` while the gate's own stack is whole (no `dirs` and no uncertain pop or named stack earlier). Anything else - and every cmdlet run under Bash - keeps the more protected of the two views as it was in `VCWD` and puts the possible new folder in `VCWD_B`; when the new folder cannot be read it is the most protected folder this command has been in (`HIST_DIR`, seeded with the session cwd). The old folder is never dropped. `cd` / `pushd` to an unreadable target still clear both views, as on main.

| Command (R = /work/u9613010/lab_runs/x) | Tool | cwd | main | r0 | r1 |
|---|---|---|---|---|---|
| `pushd results; popd -n; rm -rf x` | Bash | R | deny | pass | deny |
| `pushd /tmp; pushd results; popd +1; rm -rf x` | Bash | R | deny | pass | deny |
| `pushd results; dirs -c; popd; rm -rf x` | Bash | R | deny | pass | deny |
| `Push-Location -StackName a /tmp; Push-Location -StackName b /var; Pop-Location -StackName a; Remove-Item x` | PowerShell | R/results | deny | pass | deny |
| `sl /tmp; sl -; Remove-Item x` | PowerShell | R/results | deny | pass | deny |
| `Push-Location /tmp; Push-Location -; Remove-Item x` | PowerShell | R/results | deny | pass | deny |
| `sl ../res*; Remove-Item x` | PowerShell | R/results | deny | pass | deny |
| `sl ..; sl -Path (Join-Path $PWD results); Remove-Item x` | PowerShell | R/results | deny | pass | deny |
| `sl ..; sl @("results"); Remove-Item x` | PowerShell | R/results | deny | pass | deny |
| `cd R; cd res\ults; sl /tmp; rm -rf x` (the old known limit) | Bash | /tmp | pass | pass | deny |
| `pushd results; popd; rm -rf x` (bare popd, whole stack) | Bash | R | deny | pass | pass |
| `sl $d; Remove-Item x` (control) | PowerShell | /tmp | pass | pass | pass |

The `popd` row is the one deliberate difference from main (see above). A target that does not exist (`sl /nonexistent`) still moves the view, as main's `cd /nonexistent` does; accepted, unchanged. The 44 contract cases and the seven extra cases pass unchanged. `dirs` was added to `CW_HANDLED` so the large-input filter keeps it; the here-doc awk count stays 3.

### Verifier additions (same round)

The new handlers (popd, Pop-Location, Set-Location, sl, chdir, Push-Location) are not modelled as a move when the segment may not run or may not touch this shell: its command line has `&`, `|`, a parenthesis or a backtick (after `&&` / `||`, in a pipe, in `( )`, backgrounded), it is wrapped (`command popd`), or the cmdlet has an option other than `-Path`, `-LiteralPath`, `-StackName`, `-PassThru` (`-Foo`, `-WhatIf`). Then the old folder is kept in one view and the possible new one goes to the other. `cd` and `pushd` are not changed (main's `false && cd /tmp` imprecision stays).

| Command (R = /work/u9613010/lab_runs/x) | Tool | cwd | main | r0 | r1 |
|---|---|---|---|---|---|
| `pushd results; false && popd; rm -rf x` | Bash | R | deny | pass | deny |
| `pushd results; exit 0 \|\| popd; rm -rf x` | Bash | R | deny | pass | deny |
| `pushd results; popd \| cat; rm -rf x` | Bash | R | deny | pass | deny |
| `pushd results; (popd); rm -rf x` | Bash | R | deny | pass | deny |
| `pushd results; echo a \| popd; rm -rf x` | Bash | R | deny | pass | deny |
| `pushd results; popd & rm -rf x` | Bash | R | deny | pass | deny |
| `pushd results; command popd; rm -rf x` | Bash | R | deny | pass | deny |
| `sl -Foo /tmp; Remove-Item x` | PowerShell | R/results | deny | pass | deny |
| `sl /tmp -WhatIf; Remove-Item x` | PowerShell | R/results | deny | pass | deny |
| `false && sl /tmp; Remove-Item x` | PowerShell | R/results | deny | pass | deny |
| `sl /tmp; Pop-Location -Foo; Remove-Item x` | PowerShell | R/results | deny | deny | deny |
| `Push-Location results; Pop-Location -PassThru; Remove-Item x` (control) | PowerShell | R | deny | deny | pass |
| `sl -PassThru /tmp; Remove-Item x` (control) | PowerShell | R | pass | pass | pass |

### Remaining intended differences from main (branch passes, main denies or asks)

- A bare `popd` / `Pop-Location` with a stack the gate kept whole really returns to the pushed folder (main never popped).
- PowerShell moves that really leave a protected folder, under the PowerShell tool: `sl /tmp`, `Push-Location /tmp`, `Set-Location -Path ..`, `Set-Location -StackName s ..` (maintainer's developer-agent ruling in the overview, TC-025..027).
- Under the Bash tool `Set-Location` / `sl` / `chdir` / `Push-Location` are not built-ins; they only add a second candidate and never drop the old folder, so nothing passes here that main denies.
- A target that does not exist (`sl /nonexistent`) moves the view, the same class as main's `cd /nonexistent`.
- Main's own `cd` imprecision (`false && cd /tmp`, a nonexistent target) is unchanged.
