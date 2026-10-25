# pipefail-grep-q-sweep progress ledger

- [x] Guard test `tests/no_pipefail_grep_q_test.sh` (RED commit first, GREEN after the sweep).
- [x] Sweep: every `X | grep -q… PATTERN` in a `tests/*.sh` that has `pipefail` became `X | grep …(q removed) PATTERN >/dev/null`.
- [x] No migration needed: only test scripts and this ledger changed; no data or schema is touched.

## TC-002 RED output (before the sweep, RED commit)
`bash tests/no_pipefail_grep_q_test.sh` exited 1; the TC-003 line listed 21 offending files, including
tests/jev_test.sh and tests/platform_direction_docs_test.sh (also constitution_6_test, flow_skills_layout_test,
gate_output_failclosed_test, generate_samplesheet_test, guard_plugin_files_test, hosted_deploy_test,
inventory_outputs_test, no_second_run_state_test, on_site_parallel_test, operations_doc_test, plugin_intro_test,
prepare_launch_test, run_all_retry_test, run_all_test, scripts_name_their_alternative, skill_runs_uses_actions_test,
skills_name_the_v3_launch_path, tune_resources_test, wsl_bridge_test).

## Files changed
Count unit: one `| grep -q…` pipeline stage rewritten (a line with two stages counts two). Total 91 stages on 83 lines
(= the number of `>/dev/null` additions in `git diff`). Changed lines per file (from `git diff --numstat`):

| file | changed lines | single run in WSL (exit) |
|---|---|---|
| constitution_6_test.sh | 3 | 0 |
| flow_skills_layout_test.sh | 1 | 0 |
| gate_output_failclosed_test.sh | 1 | 0 |
| generate_samplesheet_test.sh | 1 | 0 |
| guard_plugin_files_test.sh | 1 (two stages) | 0 |
| hosted_deploy_test.sh | 18 | 0 |
| inventory_outputs_test.sh | 5 | 0 |
| jev_test.sh | 1 | 0 |
| no_second_run_state_test.sh | 1 (string fed to the detector; expected value 1 unchanged) | 0 |
| on_site_parallel_test.sh | 1 | 0 |
| operations_doc_test.sh | 2 | 0 |
| platform_direction_docs_test.sh | 15 (TC-027: 15 before, 0 after) | 0 |
| plugin_intro_test.sh | 3 | 0 |
| prepare_launch_test.sh | 1 | 0 |
| run_all_retry_test.sh | 6 | 0 |
| run_all_test.sh | 1 | 0 |
| scripts_name_their_alternative.sh | 1 | 0 |
| skill_runs_uses_actions_test.sh | 5 | 0 |
| skills_name_the_v3_launch_path.sh | 13 | 0 |
| tune_resources_test.sh | 2 | 0 |
| wsl_bridge_test.sh | 1 | 0 |
| no_pipefail_grep_q_test.sh (new) | - | 0 |

`bash -n` passes on all 21. constitution_scope_test.sh, run_all.sh, quarantine.txt, hooks/, .github/ are untouched.

## Stress (TC-030, TC-031) - DEVIATION from 8 x 200
Method: two separate git clones on WSL ext4 (base = commit before the sweep, after = the sweep), 8 concurrent
workers each running `platform_direction_docs_test.sh` repeatedly, counting non-zero exits. The machine's load
average was about 44, so one run took 10-30 s and 8 x 200 had not finished after 2 hours; it was cut to 8 x 20 = 160
runs per side.
- before the sweep: 2 red of 160 (the false failure reproduced)
- after the sweep: 0 red of 160
An earlier attempt on a `git archive` copy had no .git and failed every run for an unrelated reason; discarded.

## Full suite (TC-037)
(see the final report)
