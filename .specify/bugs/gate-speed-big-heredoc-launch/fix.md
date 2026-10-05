# Fix: gate-speed-big-heredoc-launch (#62, launch gate and in_use.sh)

- **Branch**: `fix/gates-audit2-launch` (RED 6bd5a2f, GREEN 53853d5)
- **Changed**: `hooks/launch_trigger.sh`, `hooks/confirm_launch.sh`, `hooks/in_use.sh`; tests `tests/confirm_launch_test.sh`, `tests/gate_big_input_test.sh` (launch block only)
- **Approach** (no verdict changes; small commands keep the fork-free path of #34):
  - `is_launch_command`: when the segments pass 16 KB, one awk pass keeps only the segments the loop could act on - the loop's own first test, on the same two texts (quote-free, and quotes dropped), plus the too-deep marker. The per-segment prefilter now reads the quote-dropped text as well, which restores `s"b"atch`, `tw l"aun"ch`, `nextflow r"u"n` (lost by the WIP prefilter). The nested-shell regex over the whole command runs once, and only when a segment needs it. A split already made by the allowlist block is reused.
  - `confirm_launch.sh`: D3 filters big segment lists by one awk pass on its own first test (a transport word on the quote-free column). The allowlist block skips, before its word loops, every segment that cannot name the file or the script (no egr/ess/allow, no `$`, not an assignment, no glob next to a `/` and the cwd is not the config or scripts folder) - the same rule as an awk pass for big lists; it substitutes variables only when there are some and the segment has a `$`; `EA_N` is built by `tr` on a big command; `RELAY_OVR` by a regex instead of `${CMD#*...}`; the resident-process and tw launch/relaunch regexes sit behind substring tests.
  - `in_use.sh`: `_abf_has_path` is one regex (`${t#*"$p"}` tried every prefix: quadratic); a text over 8 KB is normalised by one `sed`, run in C.UTF-8 under MSYS/Cygwin (GNU sed there is itself quadratic on one long line in the plain C locale, which is what it gets when LANG is unset: 50-120 s at 300 KB, 0.1-0.4 s in C.UTF-8, measured); the bare-`cd` check is two regexes instead of global replacements.

## Before / after (native Git Bash, Windows 11, 300 KB here-doc, 3 runs each, median; the machine was shared with other agents and a WSL test run, so single runs scatter up to 2x)

Before = 490de98 (WIP), after = 53853d5. `g2b_time.sh`, hook `timeout 60`.

| situation | before | after |
|---|---|---|
| marker, here-doc + `tw launch` (t62 launch) | 9.5 s (ask) | 3.8 s (ask) |
| marker, here-doc + `rm -rf .../results` (t62 rm, launch gate; D3 runs) | 9.0 s | 2.9 s |
| no marker, cwd under storage_root, here-doc + `tw launch` | 35.6 s (ask) | 5.8 s (ask) |
| no marker, here-doc + `cd <storage_root>/p && sbatch` | over 60 s (killed, no answer) | 7.6 s (ask) |
| marker, code-like here-doc (quotes, `[`, `*`, `.tsv`, add/remove) + `tw launch` | over 60 s (killed, no answer) | 3.7 s (ask) |

Of the after time about 1 s is `scripts/settings.sh reach` (a constant of every launch ask, not size-dependent) and 0.5 s each the splitter and reading the command out of jq's output. `abf_in_use` alone, no marker, 300 KB: 9-110 s before, 0.8 s after (line profile).

WSL, `tests/gate_big_input_test.sh` launch block, 30 KB -> 300 KB: marker 0.2 -> 0.8 s, by cwd 0.2 -> 0.8 s, by named path 0.2 -> 1.0 s (was 0.5 -> 30.1 s, TIMEOUT), code-like 0.2 -> 0.8 s.

## Tests

- `tests/confirm_launch_test.sh`: the three quote splices (red on 490de98), and every `t`, identity/egress and D3 case run again behind a 20 KB python here-doc with the same expected answer (134 + 108 + 44 cases, all green; the three splices were red there too). The re-run adds well under a minute in WSL (8 calls at a time); the whole file took 72-149 s depending on load.
- `tests/gate_big_input_test.sh`, launch block: four situations, 30 KB and 300 KB, right verdict, 300 KB under 25 s, and at most 30x the 30 KB time once over 3 s (linear is 10x, quadratic 100x; a big run that fails the ratio is run once more and the faster counts). The named-path case was red (TIMEOUT at 30 s).
- Also green in WSL: `in_use_test.sh`, `in_use_speed_test.sh` (new 325 ms vs baseline 1687 ms for 20 calls), `gate_process_count_test.sh`, `gate_output_failclosed_test.sh`, `confirm_walkthrough_test.sh`, `guard_plugin_files_test.sh`, `constitution_scope_test.sh`.

## Not changed

- `hooks/confirm_cleanup.sh` (other branch). It sources `in_use.sh`, so a delete after a big here-doc in a session without a marker is now decided in under a second there too (it was the same 36 s in WSL).
- `hooks/guard_plugin_files.sh` still greps per segment, but only once a command names the installed plugin's root; not reached by a here-doc that does not.
