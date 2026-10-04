# Fix: gate-speed (#34)

- **Branch**: `fix/34-gate-speed` (merged with `fix/45-relay-followups` at bb9d4bb; the "no behaviour change" baseline is bb9d4bb)
- **Changed**: `hooks/confirm_launch.sh`, `confirm_cleanup.sh`, `confirm_walkthrough.sh`, `guard_plugin_files.sh`, `launch_trigger.sh`; new `tests/gate_process_count_test.sh`, `.specify/bugs/gate-speed/{measure.sh,verdict-diff/}`
- **Approach**: cut the fixed per-call overhead (see assessment, causes 1-8), not the classification:
  one `jq` per hook for all fields (anything unusual - not JSON, object-valued field, two documents, separator in a value - falls back to the old probe + jq-per-field path); stdin by `read`; `$HD` instead of `dirname`; awk fed by here-strings; `strip_heredocs.awk` only when the command has `<<`; in-shell regex instead of one-line greps (newline-aware where `[[:space:]]` would differ from grep); `uname` only when a transport word's letters can occur (a subsequence glob, because the splitter drops quoted text and `s"x"sh` reads as `ssh`); D3 reuses the segments `is_launch_command` already computed; walkthrough searches for an analysis/ target only when the command contains `analysis/` and reads the transcript tail once; guard builds its spellings without a pipeline/`sort` and uses `$OSTYPE` for `uname`.
- **Red -> green**: `tests/gate_process_count_test.sh` failed 21 cases on the baseline (launch 15, cleanup 8, walkthrough 18-19, guard 6 programs per call; commit c44b585) and passes all 22 now.

## Before / after (native Git Bash, Windows 11, in-use session; median of 10 calls; programs started per call)

Before = two runs on c440785 (they scatter by up to 2x on this machine); after = merged result.

| Hook | input | before ms (run 1 / run 2) | before procs | after ms | after procs |
|---|---|---|---|---|---|
| confirm_launch | grep results/ | 1721 / 1701 | 15 | 368 | 2 |
| | multi-segment | 3610 / 2557 | 15 | 487 | 3 |
| | 30-line script | 1558 / 1990 | 15 | 541 | 3 |
| | launch | 1257 / 1709 | 16 | 702 | 4 |
| confirm_cleanup | grep results/ | 673 / 864 | 8 | 357 | 2 |
| | multi-segment | 967 / 758 | 8 | 353 | 2 |
| | 30-line script | 1606 / 751 | 8 | 504 | 3 |
| | launch | 1441 / 776 | 8 | 345 | 2 |
| confirm_walkthrough | grep results/ | 1353 / 1666 | 19 | 474 | 3 |
| | multi-segment | 2908 / 1546 | 19 | 434 | 3 |
| | 30-line script | 2285 / 1629 | 19 | 533 | 4 |
| | launch | 11011 / 2338 | 33 | 1016 | 17 |
| guard_plugin_files | all four | 535-1828 / 753-888 | 6 | 288-309 | 1 |

Under 1 s everywhere except the walkthrough gate on a real launch (1016 ms, 17 programs): that path goes on to read the transcript for evidence (tail, jq, awk) and is the rare, interactive one; the launch hook's own ask runs `scripts/settings.sh` on purpose. Not reduced further here.

## Verdict diff (no behaviour change)

Corpus: every stdin payload the gate tests feed the four hooks (captured from the baseline, 756 unique), 52 harmless everyday commands, and ~95 odd shapes (here-docs, multi-line, quote-assembled words, continuation lines, plugin-root writes, Write/Edit/NotebookEdit/PowerShell/MCP tools, non-string fields, empty/non-JSON/two-document input). Each run through baseline hooks (bb9d4bb) and new hooks (2242613) in 3-4 contexts (in use / not in use / transcript with a slash-command marker / original), exit code + stdout + stderr compared.

**13788 runs, 13788 identical, 0 different** (verdicts present: ~1000 deny, ~850 ask, ~280 context-only, rest silent). The jq-missing paths are not in the corpus (no hook run without jq); the existing tests cover them and pass.

Along the way the diff of the design (not the corpus) caught four places where the first draft would have differed and were fixed before commit: `uname` gated on the literal word (quote-assembled `s"x"sh`), `[[:space:]]` and `^` crossing a newline in bash regex but not in grep (relay-restart and `tw launch` checks), `$(cat)`/`$(jq)` trailing-newline stripping, and the guard's `root_spellings` having to stay a stand-alone printing function (its test lifts it out).

## Tests

All 85 files green in WSL on the merged result (`tests/run_all.sh`, includes the gate tests, in_use, egress, conditions_matrix, portable_userland, gate_process_count). Scripts: `verdict-diff/` (capture.sh, corpus.sh, worker.sh, replay.sh).

- **Not changed**: classification logic, messages, timeouts; `scripts/settings.sh` cost on a launch ask.
