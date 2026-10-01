# Fix: walkthrough-quoted-text (#42)

- **Branch**: `fix/42-walkthrough-quoted`
- **Changed**: `hooks/confirm_walkthrough.sh` (G1 samplesheet / G2 params-file selection for Bash), `tests/confirm_walkthrough_test.sh` (12 cases)
- **Approach**: per segment of `hooks/split_segments.awk`, on the command with here-doc bodies stripped. A match outside quotes counts as before. A match that only appears once quotes are dropped counts when the segment runs something: its command word is a shell/python/`tw`/wrapper, or the command word is itself quoted (`"scripts/generate_samplesheet.py" …`); for the params file, also when a real `>` sits outside quotes. A here-doc fed to a runner is judged on the whole command as before. If the splitter cannot load, the old raw judgement is used (a false deny, never a false allow).
- **Red → green**: the 4 false denies from the assessment failed first; two more regressions found by comparing against main (a quoted path that IS the command) were added as tests, seen red, then fixed.
- **Compared with main on 18 shapes**: only `gh pr create --title "tw datasets add …"` and `grep -n "generate_samplesheet.py" …` changed (deny → allow), both intended.
- **Not changed**: G3 (launch, shared with confirm_launch.sh), G4, G5, G6; Write/Edit selection by file path.
