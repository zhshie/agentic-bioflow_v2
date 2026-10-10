# Fix: backslash-inside-delete-word

- **Branch**: `fix/66-backslash-inside-delete-word` (RED d59c599, GREEN eecf944)
- **Changed**: `hooks/confirm_cleanup.sh`; `tests/confirm_cleanup_test.sh` (end of the SN1 section, TC-001..020, 035, 036), `tests/gates_without_jq_test.sh` (TC-021..030, 037), `tests/gate_big_input_test.sh` (TC-033, 034); `docs/TESTING.md` (steps for TC-039..041).

## What changed

- After the command is split, every segment that holds a backslash is added a second time with its backslashes dropped, all three columns (as written, quote-free, command word), before the large-input filter. The segment as written is still judged; the strictest verdict of the copies stands. Port of `hooks/launch_trigger.sh:135-145`, with one difference: a word that is a Windows drive path (`C:\lab\x`) or a UNC path keeps its backslashes in the copy. Without that, the existing `#35` PowerShell cases (`Move-Item -Destination C:\lab\proj\y`) turned `C:labprojy` and asked; no existing assertion was changed.
- The copy is made by one awk pass that runs only when there is a backslash, so a command without one still costs the same 3 awk runs behind a big here-doc (TC-032).
- No-jq fallback (`looks_delete_shaped`): the raw text is matched as written and once more with backslashes dropped (`looks_delete_text`). The pattern ` nextflow ... clean ` could not match `nextflow clean` (the two spaces overlap), so ` nextflow clean ` was added; without it `nextflow cl\ean -f` (TC-023) stayed open, and so did plain `nextflow clean -f`. `git clean` has the same overlap and was left alone (out of scope).

## Evidence (WSL, jq 1.7.1)

| Command | Before | After |
|---|---|---|
| `r\m -rf results` | pass | deny |
| `t\ar --remove-files -cf a.tar results` | pass | deny |
| `tar --remo\ve-files -cf a.tar results` | pass | deny |
| `nextflow cl\ean -f` | pass | ask |
| `r\m -rf <run>/work` | pass | ask |
| `echo r\m -rf <run>/results` | pass | deny (main denies `echo rm -rf <run>/results` too) |
| no jq: `r\m -rf results` | exit 0 | exit 2 BLOCKED |
| no jq: `tar --remo\ve-files ...` | exit 0 | exit 2 BLOCKED |
| no jq: `nextflow cl\ean -f` | exit 0 | exit 2 BLOCKED |
| no jq: `\rm -rf results` | exit 0 | exit 2 BLOCKED |
| no jq: `t\ar --remove-files ...` | exit 2 | exit 2 |

Controls stay pass: `printf 'a\nb'`, `grep -E "a\sb" file`, `sed 's/a\/b/c/' f`, `echo C:\Users\x`, `ls C:\work\results`, `nextflow l\og`, `r\m -rf <run>/re\ports`. `r''m` and `$'\x72'm` give the same verdict on main and on the branch (TC-039).

## Timing (WSL, 300 KB here-doc, a backslash on every line)

| Body then command | 30 KB | 300 KB |
|---|---|---|
| python lines, `r\m -rf results` | 82 ms | 448 ms |
| bash pipelines, `r\m -rf results` | 93 ms | 541 ms |
| python lines, `rm -rf results` | 79 ms | 438 ms |
| bash pipelines, `rm -rf results` | 92 ms | 535 ms |

The limit for these four is 3 s on Linux/WSL, 20 s elsewhere (#62's).

## RED / GREEN

RED d59c599: 13 failures in `confirm_cleanup_test.sh` (also behind the here-doc), 5 in `gates_without_jq_test.sh`, 2 in `gate_big_input_test.sh`. GREEN eecf944: all three and `confirm_cleanup_behind_heredoc_test.sh` pass.

Full suite in WSL with jq: 94/95. The one failure, `conditions_matrix_test.sh`, fails the same 19 checks on `main` in this WSL: it runs with PATH `/usr/bin:/bin` and this WSL has jq only in `/tmp/jqbin`.

## Review round 1: the copy must not change state

The security review found that the dropped-backslash copy, judged as an extra segment after the original, wrote the loop's cross-segment state. The loop carries two such values, `VCWD` (the folder a `cd`/`pushd` moved to) and `LISTER_OK` (a lister named a known path); everything else it accumulates (`UNRESOLVED`, `HIT_*`) only adds findings, which can only make a verdict stricter.

Fix (general, not a list of command words): the awk pass marks each copy with a fourth field; the loop saves `VCWD`/`LISTER_OK` when a copy starts and puts them back before the next segment. The copy is still judged. RED 176f422, GREEN below.

| Command (cwd a run folder `x`) | main | branch before fix | after fix |
|---|---|---|---|
| `cd <x>/results\old; rm -rf x` | deny | pass | deny |
| `pushd <x>/results\old; rm -rf x` | deny | pass | deny |
| same, session cwd `/tmp` | deny | pass | deny |
| `cd results\old; rm -rf x` | deny | deny | deny |
| `cd .\results; rm -rf *` | deny | deny | deny |
| PowerShell `Get-ChildItem results\old \| Move-Item -Destination x` | ask | pass | ask |
| PowerShell `Get-ChildItem .\results \| Move-Item -Destination x` | ask | pass | ask |
| PowerShell `Get-ChildItem reports \| Move-Item -Destination x` (control) | pass | pass | pass |

The two relative `cd` cases were already deny, because the copy resolved under the original's folder; the absolute-path form is the one that regressed. `Set-Location` is not handled by the hook at all (pass on main and branch), so it has no case.
