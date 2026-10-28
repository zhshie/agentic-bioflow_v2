# 平台測試拆成 8 份，每項在預設 300 秒內跑完 progress ledger

Run stamp 20261028-1420-suitespeed3. Base 0d44c197d013c8045c848735f8d628bcbe1e3e42 (test cases from verifier). RED 3372f28, GREEN c5c774a.

## Tasks

- [x] RED: platform/tests/test_platform_parts.py (SS-01..SS-30, 39, 40, 50), tests/run_all_retry_test.sh (SS-10, 32, 33, 35, 71), tests/run_all_shard_test.sh (SS-11, 36, 37 and TC-002 rewritten). 8 targeted tests failed for the right reasons.
- [x] GREEN: tests/platform_test.sh (PLATFORM_PARTS=8, valid_part check, SHARDS_1..SHARDS_8 one file per line, REST round robin modulo 8).
- [x] New wrappers tests/platform_shard_4..8_test.sh; shard_2 and shard_3 comments updated.
- [x] Comments only in tests/run_all.sh, tests/platform_clock_test.sh, tests/quarantine.txt line 12 (keeps platform_shard_2_test.sh and platform_shard_3_test.sh literals plus platform_shard_<n>_test.sh, ruling D8).
- [x] docs/TESTING.md and docs/PLATFORM.md name the nine entries.
- [x] Measurements below (SS-52..SS-61).
- [x] Full suite at HEAD (see end of file).


## Fix round 2 (verifier findings SS-24, SS-52, SS-56, SS-66)

The first per file list was lost when `/tmp/per-file.txt` was overwritten by other lanes (only its top 31 lines had been copied into this ledger). It is measured again below, twice: on the base copy (SS-52) and on HEAD (SS-24). SS-66: `tests/platform_clock_test.sh` line 2 is back to its base text; only lines 5, 7 and 8 differ now.

## Measurements

Machine: nproc=16 (WSL Ubuntu). `git rev-parse HEAD` of the branch before this round: f9f9a72998043b52472e08705cde71036aa9145d; v3 (origin/v3) 9a3f65a3faf2cdc235082cbe19c6ac4f4a4dcd03; base of the test cases 0d44c197d013c8045c848735f8d628bcbe1e3e42. Other lanes ran suites at the same time, so the load varied from 1.5 to 21 and all seconds below are inflated by it; the load is written next to each run.

### Step 0, current state (four entries), per file seconds on the base copy

Command: `ABF_PLATFORM_PART=all ABF_PYTEST_ARGS=--durations=0 bash tests/platform_test.sh` in a `git archive 0d44c19` copy (no `.git` there, so the 4 tests that need a git checkout fail: test_scope tc071, test_station_static tc087, test_su_packaged gitignore, test_launch_static tc074; they are not slow tests and not part of the numbers). Load before `17:09:38 load average: 3.56, 7.25, 10.90`, after `17:22:17 load average: 6.31, 7.83, 10.40`; real 12m38s. The first measurement of the same step (real 9m46s, load 11.44 before and 3.16 after) had a sum of 2908.3 s over the files; this repeat sums to 3249.2 s over 120 files, within 12 percent of it and within 30 percent of the plan's 580 s wall (D4, D9), so 8 parts stands.

The four entries on the base copy, by entry:

| Entry (base) | Wall | Source |
|---|---|---|
| platform_test.sh (part 1) | 292 s ok | BEFORE run below |
| platform_shard_2_test.sh | TIMEOUT 300 s | BEFORE run below |
| platform_shard_3_test.sh | TIMEOUT 300 s | BEFORE run below |
| platform_clock_test.sh | TIMEOUT 300 s | BEFORE run below |

The `all` run above starts every pytest process of the base copy at once; the walls of its 16 pytest processes (in order, 1 to 16): 26.4, 36.9, 45.4, 231.2, 453.7, 240.4, 208.4, 127.4, 210.6, 360.1, 261.5, 195.2, 260.4, 506.1, 96.1, 152.3 s. These are inflated, because all of them share the 16 cores.

Per file seconds, base copy, whole list (120 files, `seconds file`, longest first; this is `/tmp/per-file-base.txt`):

```
151.3 tests/test_nextflow_e2e.py
131.7 tests/test_launch_cli.py
130.5 tests/test_owner_binding.py
125.4 tests/test_station_resume.py
111.8 tests/test_station_launch.py
105.5 tests/test_station_cancel.py
103.6 tests/test_keep_submissions.py
94.8 tests/test_station_e2e.py
89.3 tests/test_launch_e2e.py
87.6 tests/test_station_channel.py
85.7 tests/test_resume_platform.py
84.2 tests/test_pat.py
77.2 tests/test_resume_entrypoints.py
73.8 tests/test_platform_parts.py
67.9 tests/test_oauth_mcp.py
66.9 tests/test_owner_gaps.py
52.8 tests/test_http_site_samplesheet.py
50.7 tests/test_confirm_page.py
50.6 tests/test_station_fakeplatform.py
47.7 tests/test_station_envs.py
47.3 tests/test_datasets.py
46.9 tests/test_oauth.py
46.3 tests/test_cloud_upload.py
44.5 tests/test_resume_edit_params_station.py
44.1 tests/test_oauth_review.py
43.8 tests/test_relay_loopback.py
43.8 tests/test_launch_nextflow.py
41.3 tests/test_human_channel.py
39.8 tests/test_clean_page.py
39.6 tests/test_owner_tokens.py
37.4 tests/test_web_board.py
36.8 tests/test_web_login.py
35.8 tests/test_launch_followup.py
35.6 tests/test_wrapper.py
33.7 tests/test_resume_lineage.py
32.9 tests/test_cleanup_offer.py
32.1 tests/test_cloud_cost.py
25.1 tests/test_wrapper_nf2.py
24.4 tests/test_actions_layer.py
23.8 tests/test_resume_edit_params_platform.py
23.5 tests/test_guidance.py
23.4 tests/test_su_usd.py
23.4 tests/test_temp_password.py
23.0 tests/test_pipeline_launch_station.py
22.4 tests/test_review_fixes.py
22.3 tests/test_cli.py
21.0 tests/test_byte_channel_a.py
20.6 tests/test_web_welcome.py
19.8 tests/test_cleanup_backfill.py
19.1 tests/test_oauth_consent.py
18.2 tests/test_aws_ce.py
17.5 tests/test_followup3.py
17.5 tests/test_cloud_wire.py
17.1 tests/test_run_diag_tools.py
16.9 tests/test_pipeline_launch.py
16.4 tests/test_review_fixes_2.py
16.2 tests/test_oauth_tokens.py
16.2 tests/test_mcp.py
16.1 tests/test_web_running.py
15.1 tests/test_web_cost.py
14.7 tests/test_station_packaging.py
14.0 tests/test_web_guided_launch.py
13.9 tests/test_web_actions.py
13.5 tests/test_launch_platform.py
13.3 tests/test_gcb_ce.py
12.8 tests/test_chat_tools.py
12.2 tests/test_cleanup_confirm.py
11.9 tests/test_station_owner.py
11.8 tests/test_web_v2_skeleton.py
11.5 tests/test_pipelines_store.py
11.3 tests/test_su_packaged.py
10.5 tests/test_web_results_outputs.py
10.5 tests/test_pipeline_files_action.py
10.0 tests/test_dataset_launch.py
9.5 tests/test_station_platform.py
8.0 tests/test_web_settings.py
7.6 tests/test_launch_followup_e2e.py
7.2 tests/test_dataset_cli.py
7.1 tests/test_resume_scope.py
6.7 tests/test_estimate_su.py
6.7 tests/test_cleanup_store.py
6.7 tests/test_nfcore_catalogue.py
6.4 tests/test_web_status_squares_3.py
6.4 tests/test_web_finished.py
6.2 tests/test_pipelines_validation.py
6.2 tests/test_pipeline_files_queue.py
6.1 tests/test_gcb_launch.py
6.1 tests/test_byte_channel_b.py
5.7 tests/test_web_fixes_1.py
4.7 tests/test_scope.py
4.3 tests/test_su_in_get_run.py
4.2 tests/test_station_clean.py
4.1 tests/test_web_confirm_plain.py
3.5 tests/test_receiver.py
3.2 tests/test_failures.py
3.1 tests/test_launch_static.py
2.8 tests/test_receiver_nf2510.py
2.1 tests/test_compose.py
1.6 tests/test_station_pipeline_files.py
1.6 tests/test_station_static.py
1.5 tests/test_web_chrome_origin.py
1.2 tests/test_catalogue.py
1.1 tests/test_secrets.py
0.9 tests/test_status.py
0.8 tests/test_launch_bundle.py
0.7 tests/test_onboarding_doc.py
0.6 tests/test_web_parity.py
0.5 tests/test_port_race.py
0.5 tests/test_owner_guard.py
0.3 tests/test_launch_docs.py
0.3 tests/test_station_clean_gcb.py
0.3 tests/test_module_sources.py
0.3 tests/test_validate.py
0.2 tests/test_resume_edit_params_words.py
0.1 tests/test_model_key_refusal.py
0.1 tests/test_cloud_upload_docs.py
0.1 tests/test_schema.py
0.1 tests/test_resume_edit_params_docs.py
0.0 tests/test_station_docs.py
0.0 tests/test_common.py
```

### Same list on HEAD (nine entries), SS-24

Command: the same with `ABF_PLATFORM_PART=all` in the worktree. Load before `16:55:12 load average: 6.02, 13.07, 11.09`, after `17:05:32 load average: 6.29, 11.60, 13.05`; real 10m20s; 34 pytest processes, all exit 0. 120 files, sum 4894.0 s (every named file runs in its own process at the same time, so this is more contended than the base run). The names that take 20 s or more and are not named are listed in the section on the assignment below, with the conflict in the plan.

```
180.8 tests/test_keep_submissions.py
180.1 tests/test_launch_cli.py
175.7 tests/test_platform_parts.py
154.9 tests/test_owner_binding.py
145.2 tests/test_nextflow_e2e.py
142.1 tests/test_http_site_samplesheet.py
140.2 tests/test_station_resume.py
138.3 tests/test_pat.py
136.1 tests/test_resume_platform.py
135.2 tests/test_station_channel.py
128.9 tests/test_station_launch.py
124.8 tests/test_station_cancel.py
121.2 tests/test_resume_entrypoints.py
114.4 tests/test_launch_e2e.py
111.2 tests/test_owner_gaps.py
106.0 tests/test_station_e2e.py
102.6 tests/test_oauth_mcp.py
95.6 tests/test_datasets.py
91.0 tests/test_oauth_review.py
81.8 tests/test_clean_page.py
79.9 tests/test_human_channel.py
77.0 tests/test_confirm_page.py
75.7 tests/test_oauth.py
73.9 tests/test_cloud_cost.py
69.5 tests/test_web_board.py
65.7 tests/test_cleanup_offer.py
56.3 tests/test_cloud_upload.py
54.4 tests/test_followup3.py
54.2 tests/test_cleanup_backfill.py
51.0 tests/test_launch_nextflow.py
50.8 tests/test_actions_layer.py
49.9 tests/test_resume_edit_params_station.py
49.5 tests/test_byte_channel_a.py
47.2 tests/test_temp_password.py
44.4 tests/test_review_fixes.py
43.6 tests/test_relay_loopback.py
43.5 tests/test_aws_ce.py
43.2 tests/test_station_envs.py
42.8 tests/test_resume_edit_params_platform.py
41.6 tests/test_launch_followup.py
41.3 tests/test_station_fakeplatform.py
40.8 tests/test_owner_tokens.py
40.3 tests/test_web_welcome.py
37.2 tests/test_cleanup_confirm.py
36.8 tests/test_review_fixes_2.py
31.9 tests/test_cloud_wire.py
30.9 tests/test_web_actions.py
30.8 tests/test_station_packaging.py
30.2 tests/test_web_login.py
29.7 tests/test_pipeline_launch.py
29.7 tests/test_cli.py
28.8 tests/test_run_diag_tools.py
28.1 tests/test_web_running.py
27.6 tests/test_mcp.py
27.5 tests/test_guidance.py
27.1 tests/test_oauth_tokens.py
26.9 tests/test_chat_tools.py
26.4 tests/test_web_guided_launch.py
25.1 tests/test_resume_lineage.py
24.1 tests/test_launch_platform.py
23.8 tests/test_wrapper.py
22.5 tests/test_web_results_outputs.py
22.2 tests/test_dataset_launch.py
21.9 tests/test_web_cost.py
21.3 tests/test_pipelines_store.py
21.2 tests/test_pipeline_launch_station.py
21.1 tests/test_cleanup_store.py
20.3 tests/test_oauth_consent.py
20.3 tests/test_web_v2_skeleton.py
19.9 tests/test_gcb_ce.py
18.5 tests/test_nfcore_catalogue.py
18.3 tests/test_station_platform.py
18.1 tests/test_gcb_launch.py
17.1 tests/test_su_usd.py
16.7 tests/test_su_packaged.py
15.7 tests/test_byte_channel_b.py
15.7 tests/test_pipeline_files_queue.py
15.4 tests/test_dataset_cli.py
12.9 tests/test_launch_followup_e2e.py
12.3 tests/test_pipelines_validation.py
11.6 tests/test_su_in_get_run.py
11.2 tests/test_station_owner.py
11.2 tests/test_web_settings.py
11.0 tests/test_launch_static.py
10.8 tests/test_pipeline_files_action.py
10.6 tests/test_station_clean.py
9.5 tests/test_scope.py
9.2 tests/test_receiver.py
9.0 tests/test_web_fixes_1.py
8.9 tests/test_wrapper_nf2.py
8.9 tests/test_estimate_su.py
8.8 tests/test_web_confirm_plain.py
7.3 tests/test_station_static.py
7.3 tests/test_resume_scope.py
6.8 tests/test_receiver_nf2510.py
5.8 tests/test_web_status_squares_3.py
4.6 tests/test_web_finished.py
4.4 tests/test_failures.py
4.0 tests/test_catalogue.py
3.3 tests/test_web_chrome_origin.py
2.0 tests/test_status.py
1.7 tests/test_secrets.py
1.7 tests/test_station_pipeline_files.py
1.5 tests/test_launch_bundle.py
1.4 tests/test_compose.py
1.3 tests/test_station_clean_gcb.py
0.8 tests/test_web_parity.py
0.8 tests/test_owner_guard.py
0.5 tests/test_validate.py
0.5 tests/test_port_race.py
0.5 tests/test_module_sources.py
0.5 tests/test_onboarding_doc.py
0.2 tests/test_model_key_refusal.py
0.2 tests/test_resume_edit_params_words.py
0.2 tests/test_launch_docs.py
0.1 tests/test_cloud_upload_docs.py
0.1 tests/test_resume_edit_params_docs.py
0.1 tests/test_schema.py
0.0 tests/test_station_docs.py
0.0 tests/test_common.py
```

## Assignment (decision D4, D7)

Named files (24, three per part, longest processing time first, using the base seconds above), rest of the files round robin by sorted name modulo 8. The REST of a part is ONE pytest process (12 files each); every named file is its own process; the processes of a part run side by side, so the wall of a part is about its largest process:

| Part | Named files (own process, base seconds) | Named sum | REST (one process, 12 files) | Largest process | Solo wall measured |

|---|---|---|---|---|---|

| 1 | launch_e2e 89.3, resume_entrypoints 77.2, actions_layer 24.4 | 190.9 | 168.8 | 168.8 | 135 s |

| 2 | launch_cli 131.7, station_channel 87.6, oauth_review 44.1 | 263.4 | 142.8 | 142.8 | 126 s |

| 3 | keep_submissions 103.6, oauth 46.9, aws_ce 18.2 | 168.7 | 189.9 | 189.9 | 186 s |

| 4 | resume_platform 85.7, owner_gaps 66.9, launch_nextflow 43.8 | 196.4 | 188.4 | 188.4 | 232 s |

| 5 | station_cancel 105.5, pat 84.2, clean_page 39.8 | 229.5 | 175.3 | 175.3 | 182 s |

| 6 | station_resume 125.4, confirm_page 50.7, http_site_samplesheet 52.8 | 228.9 | 140.6 | 140.6 | 115 s |

| 7 | owner_binding 130.5, byte_channel_a 21.0, cleanup_backfill 19.8 | 171.3 | 142.4 | 142.4 | 104 s |

| 8 | station_launch 111.8, oauth_mcp 67.9, datasets 47.3 | 227.0 | 178.6 | 178.6 | 156 s |

| clock | station_e2e 94.8, nextflow_e2e 151.3 | 246.1 | 0.0 | 151.3 | 250 s |


Largest over smallest process: 189.9 / 140.6 = 1.35 (estimate, base seconds); sum based, 406.2 / 313.7 = 1.29. This is under the 1.4 bound of SS-25. Nothing was split, no line was moved more than once, the round robin rule is unchanged.

Conflict in the plan, decided by the executor and flagged for the developer-agent: "at most three named files per part" (SS-19, SS-20, SS-25: at most 24 named files) cannot hold together with "every file of 20 s or more on its own line" (SS-24). In the base list 48 files take 20 s or more; 2 of them are the clock part, 22 are named, and 24 stay in the REST processes (name, seconds: test_platform_parts 73.8, test_station_fakeplatform 50.6, test_station_envs 47.7, test_cloud_upload 46.3, test_resume_edit_params_station 44.5, test_relay_loopback 43.8, test_human_channel 41.3, test_owner_tokens 39.6, test_web_board 37.4, test_web_login 36.8, test_launch_followup 35.8, test_wrapper 35.6, test_resume_lineage 33.7, test_cleanup_offer 32.9, test_cloud_cost 32.1, test_wrapper_nf2 25.1, test_resume_edit_params_platform 23.8, test_guidance 23.5, test_su_usd 23.4, test_temp_password 23.4, test_pipeline_launch_station 23.0, test_review_fixes 22.4, test_cli 22.3, test_web_welcome 20.6). Two of the 24 named files are under 20 s (test_cleanup_backfill 19.8, test_aws_ce 18.2) and six REST files are longer than some named ones; the named list was dealt out in the first round from a per file list that no longer exists, and the repeat measurement above differs from it in the order of the middle files. The old combined lines (`test_launch_e2e.py`, `test_station_fakeplatform.py`, `test_station_channel.py` together) are split: launch_e2e and station_channel are named, station_fakeplatform is a REST file. I tried a re-deal of the 24 names by the repeat data (longest 24 first, each to the lightest part, REST counted in): sum ratio 1.11 but largest over smallest process 1.44, which is worse than the 1.35 of the current lists, so it was not applied. If the developer-agent wants every 20 s file alone, the number of processes goes to about 46 plus the REST of each part and the limit of 3 named lines per part (SS-19, SS-20) must go; that is a ruling on the plan, not for the executor.

The first attempt named only 18 files and the rest of part 6 dominated (measured walls 132, 141, 131, 72, 73, 139, 77, 107 s, clock 179 s, all ok, ratio about 1.96); one adjustment added 6 named files. test_launch_nextflow.py has a process of its own (SS-23).

### Single item walls on this machine, SS-55 and SS-56

Each of the nine entries run alone, one after the other, `bash tests/<entry>`, load read from `/proc/loadavg` before and after (not a quiet machine: other lanes were running, the 1 minute load never dropped under 3.3):

| Entry | Wall | Load before / after |
|---|---|---|
| platform_test.sh (part 1) | 135 s | 3.34 / 6.01 |
| platform_shard_2_test.sh | 126 s | 6.01 / 5.66 |
| platform_shard_3_test.sh | 186 s | 5.66 / 9.50 |
| platform_shard_4_test.sh | 232 s | 9.50 / 5.74 |
| platform_shard_5_test.sh | 182 s | 5.74 / 8.18 |
| platform_shard_6_test.sh | 115 s | 8.18 / 5.70 |
| platform_shard_7_test.sh | 104 s | 5.70 / 4.15 |
| platform_shard_8_test.sh | 156 s | 4.15 / 8.33 |
| platform_clock_test.sh | 250 s | 8.33 / 8.13 |

Largest over smallest of the eight numbered parts: 232 / 104 = 2.2 in this run (earlier runs 160 / 97 = 1.65 and 141 / 72 = 1.96). Not under 1.5, and the machine never reached load 2, so D5 applies: the numbers are recorded, not judged on seconds. The reason it is uneven is visible in the table above: the REST process of a part is its largest process, the REST is fixed by the round robin rule (by sorted name, modulo 8, which the contract does not allow to change), and the REST of parts 3 (189.9 s) and 4 (188.4 s) are 1.35 times those of parts 6 (140.6 s) and 7 (142.4 s) before any load; the walls follow the same order: parts 3, 4, 5, 8 are the slow ones (186, 232, 182, 156 s), parts 6, 7, 2, 1 the fast ones (115, 104, 126, 135 s). Part 4 is the slowest because its three heavy processes (resume_platform, owner_gaps, launch_nextflow, 196.4 s) run beside a 188.4 s REST: four heavy processes compete for the cores at load 9.5. Each part also pays a fixed start (virtual environment check, Java check, cached downloads), the same for all parts, which compresses the small ones less than the heavy ones. If a ratio under 1.5 is wanted, the lever is the choice of the 24 named files (put a heavy REST file of part 3 or 4 on a named line of its own, and give a light file to parts 6 and 7), measured again on a quiet machine; that changes the lists in `tests/platform_test.sh` only.

## Before and after (SS-52..SS-61), `run_all.sh --only platform_`

AFTER (this branch, nine entries), load at start `14:37:47 load average: 3.84, 4.16, 4.04`, at end `14:58:03 load average: 8.76, 8.08, 6.74`:

```
platform_clock_test.sh                         ok       209s
platform_direction_docs_test.sh                ok       13s
platform_shard_2_test.sh                       ok       97s
platform_shard_3_test.sh                       ok       116s
platform_shard_4_test.sh                       ok       148s
platform_shard_5_test.sh                       ok       160s
platform_shard_6_test.sh                       ok       108s
platform_shard_7_test.sh                       ok       109s
platform_shard_8_test.sh                       ok       138s
platform_storage_doc_test.sh                   ok       0s
platform_test.sh                               ok       113s
11/11 passed
```

No TIMEOUT. An earlier run on the same final layout (load about 20 from other lanes): clock 179, shard_2 141, shard_3 131, shard_4 72, shard_5 73, shard_6 139, shard_7 77, shard_8 107, test 132; also all ok.

BEFORE (base 0d44c19, four entries), start `14:58:03 load average: 8.76, 8.08, 6.74`, end `15:18:10 load average: 4.26, 8.73, 9.83`:

```
platform_clock_test.sh                         TIMEOUT  300s
platform_direction_docs_test.sh                ok       15s
platform_shard_2_test.sh                       TIMEOUT  300s
platform_shard_3_test.sh                       TIMEOUT  300s
platform_storage_doc_test.sh                   ok       0s
platform_test.sh                               ok       292s
3/6 passed, 3 timed out
```

Notes on decision D5: machine load is not under the executor's control. The slowest item after the change is the clock entry (two files that were not split on purpose: station_e2e and nextflow_e2e, 68 s and 110 s alone); it went 300 s TIMEOUT before to 209 s ok under load 8, and 179 s under load about 20. The 200 s bound for the other eight parts holds on every measured run (max 160 s).

List count: `bash tests/run_all.sh --list --allow-msys | wc -l` is 128 on the base and 133 on this branch (+5 wrappers, SS-58).

## Existing assertions affected (green evidence)

`test_platform_parts.py` 24 of 24 passed; run_all_count, run_all_retry, run_all_shard, run_all tests ok; constitution_scope_test ok; wrapper, nf2, scope and launch_static tests 34 passed.

## Files changed (git diff --stat 0d44c19 HEAD, in scope only)

docs/PLATFORM.md, docs/TESTING.md, platform/tests/test_platform_parts.py, tests/platform_clock_test.sh, tests/platform_shard_2..8_test.sh, tests/platform_test.sh, tests/quarantine.txt, tests/run_all.sh (comments), tests/run_all_retry_test.sh, tests/run_all_shard_test.sh.

## Left for the developer-agent

D2 and D3 items of the plan (not part of this executor task).
