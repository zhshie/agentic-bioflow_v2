# Fix: cd-target-backslash

- **Branch**: `fix/76-cd-target-backslash`. Design: plan.md "Revision 3" (after two acceptance REJECTs the stack / two-view model was replaced).
- **Changed**: `hooks/confirm_cleanup.sh` (the only file under `hooks/`); `tests/confirm_cleanup_test.sh`; `tests/confirm_cleanup_shapes.txt` (new, 300 shapes for TC-066).

## What changed

- **A set of candidate folders.** `VCWD` stays main's own working folder (the trunk), moved exactly as main moves it. `CANDS` holds the other folders the shell may be in. Every relative target (judge_word, find, the delete / mv source loop) is judged against the trunk and every candidate; findings only add, so the strictest verdict wins. The rclone remote-path branch clears the set and restores it.
- **Only main's own `cd` / `pushd` change the set.** An absolute target clears it; a relative one is followed from every candidate; an unreadable one leaves it alone. `pushd` options (`-n`, `+N`) are handled exactly as main does (the same code).
- **Everything this PR adds can only add a candidate.** The dropped-backslash copy of a `cd` / `pushd` / cmdlet adds the folder the POSIX reading reaches, from the candidates as they stood before the segment it copies (`cd res\ults; cd sub` is judged in `results/sub`). The cmdlets `Set-Location`, `sl`, `chdir`, `Push-Location` (target = first non-option word or `-Path` / `-LiteralPath`, also `-Path:X`; `-`, `$`, `~`, wildcards, `( )` and `@(` add nothing) add their target, in any tool, in any form. `Pop-Location`, `popd` and `dirs` add nothing and remove nothing. The cmdlet segments then go on through the checks main runs on them (no `continue`).
- **Cap.** At most 8 candidates; over that harmless ones go first, then merely guarded, newest kept; protected-looking ones last. The trunk is not in the set, so what main judges is always judged.
- **Lister verdict from a copy may only tighten**: after the copy, `LISTER_OK` is 1 only if the original and the copy both left it 1.
- `CW_HANDLED` gained `set-location|sl|chdir|push-location|pop-location`; the here-doc awk count stays 3.
- Removed from the earlier revisions: the pushd / popd stack, `HIST_DIR`, per-line suspicion and exact-modelling.

## Evidence (WSL, jq 1.7.1; main = c4a7327)

- `tests/confirm_cleanup_shapes.txt`: the verifier's 237 shapes, TC-045..065 and the round-1/2 pushd shapes (300 rows). Expectation = main's measured verdict, except the rows listed below where this fix is stricter. **Rows where main denies or asks and the branch passes: 0.**
- Behind a large here-doc every case gives the same verdict (`confirm_cleanup_behind_heredoc_test.sh`).
- TC-064 (25 chained `sl dN`) and TC-065 (a `results` in the middle of a 25-step chain) finish inside the normal limit (pass, and deny).

## Timing: the candidate checks are deferred

A security review showed that judging every word against up to 32 candidates inside the segment loop made long commands several times slower than main, enough to reach the 20 s deadline on a slow machine (deny became ask). Now the loop judges every word against the trunk (`VCWD`) exactly as main does, and only **records** the extra checks the candidates imply (`defer_rec`: kind, word, flags, and a snapshot id of the candidate list). `defer_run` replays them after the loop while time remains. Replays can only add findings; at its own deadline (`DEFER_DEADLINE`, the same 20 s, lowered only by `ABF_CLEANUP_DEFER_DEADLINE_S`) they stop and the verdict stands as accumulated - never an `ask` for the deferred phase. The loop's own deadline behaviour is unchanged. The cap stays 8 and `join_path` stays; `LISTER_OK` tightening and `CW_HANDLED` are untouched.

Commands: `cd R;` + 40 `Set-Location dN` (T1) or `cd dN\x` (T2) + 50 `rm -f` of five names + `rm -rf R/results`; TC-064 = 25 chained `sl dN` then `rm -rf x`. "Loop only" = `ABF_CLEANUP_DEFER_DEADLINE_S=0`, the cost the deferred design guarantees even when the deferred phase gets no time.

| Command | Where | main | branch, loop only | branch, whole |
|---|---|---|---|---|
| T1 | WSL | deny 0.5 s | deny 0.5 s | deny 1.5 s |
| T2 | WSL | deny 0.7 s | deny 0.8 s | deny 1.9 s |
| TC-064 | WSL | pass 0.1 s | pass 0.1 s | pass 0.1 s |
| T1 | native Git Bash | deny 661 ms | deny 790 ms | deny 8477 ms |
| T2 | native Git Bash | deny 2610-2839 ms | deny 2761 ms | deny 11412 ms |
| TC-064 | native Git Bash | pass 143-160 ms | pass 228 ms | pass 263 ms |

The "whole" column on native Git Bash is the deferred phase using time main never spends; it is stopped at the 20 s deadline, so on a machine where main needs 8 s the branch stops replaying at 20 s and returns main's verdict (deny). `tests/confirm_cleanup_candidates_timing_test.sh` asserts that the branch's verdict equals main's (read from commit c4a7327 with `git archive`, skipped when that commit is not in the checkout) for T1, T2 and TC-064, prints both times, and checks that with the deferred phase out of time `cd R; sl results; rm -rf x` gives main's pass (not ask), T2 still gives deny, and the loop's own `ABF_CLEANUP_DEADLINE_S=0` still gives ask. (The "R1" / "R5" shapes named by the reviewer were not defined for this run; T1, T2 and TC-064 are the three measured.)

## Assertions whose expectation changed (named by the contract)

| Case | Before | Now | Why |
|---|---|---|---|
| TC-027 `cd R; Set-Location results; Set-Location ..; Remove-Item -Recurse x` (PowerShell) | pass | deny | contract rev 3: entering results by PowerShell is judged for the rest of the command; main passes this line because it ignores the cmdlet |
| TC-056 `cd R; pushd results; popd; rm -rf x` (and the r0 "plan" copy) | pass | deny | a bare popd adds nothing and removes nothing (main denies) |
| TC-060 `Push-Location results; Pop-Location -PassThru; Remove-Item x` | pass | deny | same |
| plan: `pushd res\ults; popd`, `Push-Location results; Pop-Location` | pass | deny | same rule; stricter than main |

No assertion that was in the repository before this PR was changed (#35, #62, #66 rounds 1-3 included).

## Remaining differences from main: only stricter

81 shapes are stricter than main (13 pass to ask, 68 pass to deny); the rest are equal. The cause is always the bug itself (a directory change main does not follow) or the accepted over-judging of a folder the command entered. Listed: main verdict to branch verdict, tool, cwd, command (`@P` = /work/u9613010/lab_runs/x, `@D` = the delete verb).

| Main to branch | Tool | cwd | Command |
|---|---|---|---|
| pass to deny | Bash | /tmp | `cd @P; pushd res\ults; popd; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; pushd res\ults; popd; popd; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; Push-Location results; Pop-Location; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; Push-Location -StackName s results; Pop-Location -StackName s; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; Set-Location /tmp; Set-Location @P/results; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; Set-Location results; Set-Location /tmp; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; Set-Location results; Set-Location ..; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; cd results; cd ..; Set-Location results; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; cd res\ults; sl /tmp; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; cd res\ults; cd ../..; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; cd res\ults/sub; cd ..; @D -rf x` |
| pass to ask | Bash | /tmp | `cd @P/wo\rk; @D -rf x` |
| pass to deny | PowerShell | /tmp | `cd @P; Push-Location results; Pop-Location; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Push-Location results; popd; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Push-Location results; Push-Location /tmp; Pop-Location; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Push-Location results; Push-Location /tmp; Pop-Location; Pop-Location; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Push-Location results; Pop-Location; Pop-Location; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Push-Location results; Pop-Location; Pop-Location; Pop-Location; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `Push-Location @P; Push-Location results; Pop-Location; Pop-Location; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location results; Set-Location ~; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location results; Set-Location; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location results; Set-Location -; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location res\ults; Set-Location /tmp; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location res\ults; Set-Location ..; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; cd res\ults; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location -Path results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location -LiteralPath results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location -PassThru results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location -Path:results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location -Path: results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location -Pa results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location -lit results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location .\results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location ./results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location -StackName s results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Push-Location -StackName s results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; sl -Path results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; chdir -Path results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location results\old; Remove-Item -Recurse x` |
| pass to deny | PowerShell | @P | `Set-Location results; Remove-Item -Recurse x` |
| pass to deny | PowerShell | @P | `Set-Location ..; Remove-Item -Recurse x` |
| pass to ask | PowerShell | @P | `Get-ChildItem res\ults | Move-Item -Destination x` |
| pass to ask | PowerShell | /tmp | `cd @P; Get-ChildItem res\ults | Move-Item -Destination x` |
| pass to ask | PowerShell | /tmp | `cd @P; gci res\ults | Move-Item -Destination x` |
| pass to ask | PowerShell | /tmp | `cd @P; Get-ChildItem res\ults | where Name -like a | Move-Item -Destination x` |
| pass to ask | PowerShell | /tmp | `cd @P; Get-ChildItem res\ults | Select-Object -First 1 | Move-Item -Destination x` |
| pass to ask | PowerShell | /tmp | `cd @P; Get-ChildItem reports; Get-ChildItem res\ults | Move-Item -Destination x` |
| pass to ask | PowerShell | /tmp | `cd @P; Get-ChildItem -Path res\ults | Move-Item -Destination x` |
| pass to ask | PowerShell | /tmp | `cd @P; Get-ChildItem -LiteralPath res\ults | Move-Item -Destination x` |
| pass to ask | PowerShell | /tmp | `cd @P; ls raw\data | mi -Destination x` |
| pass to ask | PowerShell | /tmp | `cd @P; dir res\ults | Move-Item -Destination x` |
| pass to ask | PowerShell | /tmp | `cd @P; gi res\ults | Move-Item -Destination x` |
| pass to ask | Bash | /tmp | `cd @P; Get-ChildItem res\ults | Move-Item -Destination x` |
| pass to deny | Bash | /tmp | `cd @P; cd res\ults && @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; cd res\ults || @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P && (cd res\ults; @D -rf x)` |
| pass to deny | Bash | /tmp | `cd @P; pushd res\ults; popd -n; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; pushd res\ults; dirs -c; popd; @D -rf x` |
| pass to deny | PowerShell | /tmp | `cd @P; Push-Location results; Pop-Location -StackName s; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Push-Location -StackName s results; Pop-Location; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Push-Location -StackName s results; Pop-Location -StackName s; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Push-Location results; Push-Location -StackName s /tmp; Pop-Location; Remove-Item -Recurse x` |
| pass to deny | PowerShell | /tmp | `cd @P; Push-Location results; Push-Location -StackName s /tmp; Pop-Location -StackName s; Remove-Item -Recurse x` |
| pass to deny | Bash | /tmp | `cd @P; Set-Location results; Set-Location @P; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; Set-Location results; Pop-Location; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; Set-Location results; popd; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; Push-Location results; popd; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; pushd res\ults; Set-Location ..; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; cd res\ults; Set-Location ..; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; cd res\ults; Push-Location @P; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; c\d results; popd; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; c\d res\ults; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; pu\shd results; po\pd; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; pu\shd results; pu\shd /tmp; po\pd; @D -rf x` |
| pass to deny | Bash | /tmp | `cd @P; cd res\ults; cd sub; @D -rf x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location results; cd sub; Remove-Item -Recurse x` |
| pass to deny | PowerShell | @P | `Push-Location results; Pop-Location -PassThru; Remove-Item x` |
| pass to deny | PowerShell | /tmp | `Set-Location @P/results; Set-Location /tmp; Remove-Item x` |
| pass to deny | PowerShell | /tmp | `cd @P; Set-Location results; Set-Location ..; Remove-Item -Recurse x` |
| pass to deny | Bash | @P | `sl d1; sl d2; sl d3; sl d4; sl d5; sl d6; sl d7; sl d8; sl d9; sl d10; sl d11; sl d12; sl results; sl e1; sl e2; sl e3; sl e4; sl e5; sl e6; sl e7; sl e8; sl e9; sl e10; sl e11; sl e12; @D -rf x` |
