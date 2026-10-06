# Fix: gate-speed-big-heredoc (#62)

- **Branch**: `fix/gates-audit2`. RED c3a519d / GREEN 935328a (filter, deadline); 9c3d3f5 (8 KB threshold); RED c2c00c9 / GREEN ab64fec (pipelines); RED 63064d8 / GREEN e1c54b0 (many targets).
- **Changed**: `hooks/confirm_cleanup.sh`; **`hooks/split_segments.awk` and `hooks/strip_heredocs.awk`** (shared with the launch and walkthrough gates: `pipes_into_runner` and the backtick scan only, meaning-preserving); new `tests/confirm_cleanup_behind_heredoc_test.sh`; `tests/confirm_cleanup_test.sh`; a separate #62 block in `tests/gate_big_input_test.sh`.

## What changed

- **Large-input filter.** Over 8 KB of segments, one awk pass keeps a segment when its command word is one the loop handles (`CW_HANDLED`) or its quote-free text matches `RE_TRIGGER`, the union of the loop's own trigger regexes (the same `RE_*` variables, handed to awk unchanged through the environment). PowerShell listers and pipeline filters (`sort`, `ls`, `where`, ...) are held back and kept only before a kept segment, since they matter only to a Move-Item they feed. Each run of dropped segments becomes one `__skipped__` line, which ends a lister pipeline as any command does. If awk fails, the unfiltered list is used (slow, never silent). This replaces the stem list of 490de98, which kept every line of real code (`format`, `transform`, `remove_prefix` each contain a stem) and dropped the shapes added later on this branch.
- **The filter's correctness is tested, not trusted.** `tests/confirm_cleanup_behind_heredoc_test.sh` runs every case of `tests/confirm_cleanup_test.sh` again behind a 34 KB here-doc of code lines, after proving the prefix takes the filtered path (three awk runs instead of two). Each rule added later on this branch (nextflow clean, tar, zip, rclone, ln, install, truncation by redirect) went through it, its trigger added in the same commit.
- **No program or here-string per segment or per target**: `is_dry_run`, the target split and `norm_path` split without a here-string; a target is resolved through `readlink` only when a component of it is a symbolic link here (`has_link`, builtin `[ -L ]`). Bisecting at 100 KB, `is_dry_run`'s here-string alone cost 22 s; MSYS bash also slows down 18-30x per operation once it holds a few large strings, which is why a per-line loop over a large input cannot be made cheap there and the filter is needed.
- **The shared splitter is linear**: `pipes_into_runner` splits once on the pipes instead of copying the rest of the string at every pipe; the backtick scan walks forward instead of copying the rest at every backtick. Old and new `split_segments.awk` / `strip_heredocs.awk` give identical output on all 904 commands of the verdict-diff corpus plus pipe and backtick shapes.
- **A deadline of the hook's own (invariant 13).** Past 20 s (`SECONDS`, no process), checked per segment and per target, the guard stops and asks, saying it could not finish checking in time, instead of being cancelled at hooks.json's 30 s with the call let through. A deny already found still wins. `ABF_CLEANUP_DEADLINE_S` can only lower it (the tests use 0).

## Before / after (native Git Bash, Windows 11, this machine; 3 runs, median; other agents were running, single runs scatter up to 3x)

`python3 - <<'EOF'` + N KB + `EOF` + `rm -rf …/results` (C:\Users\ACER\abf_audit2\t62.sh / gen62.py, pointed at the tree):

| tree | 30 KB | 300 KB filler | 300 KB code lines | 300 KB, no delete after it |
|---|---|---|---|---|
| c018c15 (before) | 1.6 s | 69.7 s (44-81; one earlier run 116 s) | - | 47 s (1 run) |
| 490de98 (WIP stems) | 0.8 s | 6.1 s (3.5-16) | 63.4 s (53-83) | 15 s (1 run) |
| after (e1c54b0) | 0.45 s | 1.65 s (1.3-1.7) | 1.4 s | 1.35 s |

Other large shapes, after: `bash <<'EOF'` + 300 KB of `cat f | grep x | sort` + delete: 1.6 s (100 KB was 62 s, of which 39 s in `split_segments.awk`); one 300 KB line (quoted or bare words) then a delete: 1.2-2.9 s; `rm -f` of 500 relative names: 2.0-2.5 s (66 s before, same on c018c15); 2000 names: ~18-20 s, and past 20 s the guard asks (before: not finished in 120 s, i.e. cut off and let through). All verdicts as expected (deny for the deletes of results/).

WSL, `tests/gate_big_input_test.sh` #62 block: see the final suite run in the branch report (all within the 20 s bound and the 25x ratio).

## Tests

- RED: the deadline case and the behind-here-doc proof (c3a519d); the "pipes" body (c2c00c9: 300 KB cancelled at 30 s in WSL); the 200-target `rm -f` (63064d8: 200 readlink runs). The filler and code 30 KB vs 300 KB cases were green in WSL already and stay as regression guards (deny, within 20 s, at most 25x the time for 10x the input, judged only past 3 s).
- GREEN: all of them, plus `gate_process_count_test.sh` (a 60-line here-doc stays at 3 programs; the filter starts at 8 KB of segments), `gate_output_failclosed_test.sh`, `confirm_launch_test.sh`, `confirm_walkthrough_test.sh`, `bsd_userland_test.sh`, `in_use_test.sh`, and two link cases in `confirm_cleanup_test.sh` (a delete through a link into `_references/` still denies; a mutation of `has_link` to "never a link" fails both).
- **Not changed**: the other three gates (another branch owns them); jq's own time on 300 KB (0.1-1 s, linear).
