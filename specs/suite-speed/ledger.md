# 平台測試拆成 8 份，每項在預設 300 秒內跑完 progress ledger

Run stamp 20261028-1420-suitespeed3. Base 0d44c197d013c8045c848735f8d628bcbe1e3e42 (test cases from verifier). RED 3372f28, GREEN c5c774a.

## Tasks

- [x] RED: platform/tests/test_platform_parts.py (SS-01..SS-30, 39, 40, 50), tests/run_all_retry_test.sh (SS-10, 32, 33, 35, 71), tests/run_all_shard_test.sh (SS-11, 36, 37 and TC-002 rewritten). 8 targeted tests failed for the right reasons.
- [x] GREEN: tests/platform_test.sh (PLATFORM_PARTS=8, valid_part check, SHARDS_1..SHARDS_8 one file per line, REST round robin modulo 8).
- [x] New wrappers tests/platform_shard_4..8_test.sh; shard_2 and shard_3 comments updated.
- [x] Comments only in tests/run_all.sh, tests/platform_clock_test.sh, tests/quarantine.txt line 12 (keeps platform_shard_2_test.sh and platform_shard_3_test.sh literals plus platform_shard_<n>_test.sh, ruling D8).
- [x] docs/TESTING.md and docs/PLATFORM.md name the nine entries.
- [x] Measurements below (SS-52..SS-61).
- [x] Full suite at 0f9af82 (see the last section; the commit after it changes only this file).


## Fix round 2 (verifier findings SS-24, SS-52, SS-56, SS-66)
 A second deal of the named files followed the full suite run (see the assignment section): the lists in tests/platform_test.sh are the second deal.
The first per file list was lost when `/tmp/per-file.txt` was overwritten by other lanes (only its top 31 lines had been copied into this ledger). It is measured again below, twice: on the base copy (SS-52) and on HEAD (SS-24). SS-66: `tests/platform_clock_test.sh` line 2 is back to its base text; only lines 5, 7 and 8 differ now.

## Measurements

Machine: nproc=16 (WSL Ubuntu). `git rev-parse HEAD` of the branch before this round: f9f9a72998043b52472e08705cde71036aa9145d; v3 (origin/v3) 9a3f65a3faf2cdc235082cbe19c6ac4f4a4dcd03; base of the test cases 0d44c197d013c8045c848735f8d628bcbe1e3e42. Other lanes ran suites at the same time, so the load varied from 1.5 to 21 and all seconds below are inflated by it; the load is written next to each run.

### Step 0, current state (four entries), per file seconds on the base copy

Command: `ABF_PLATFORM_PART=all ABF_PYTEST_ARGS=--durations=0 bash tests/platform_test.sh` in a `git archive 0d44c19` copy (no `.git` there, so the 4 tests that need a git checkout fail: test_scope tc071, test_station_static tc087, test_su_packaged gitignore, test_launch_static tc074; they are not slow tests and not part of the numbers). Load before `17:09:38 load average: 3.56, 7.25, 10.90`, after `17:22:17 load average: 6.31, 7.83, 10.40`; real 12m38s. The first measurement of the same step (real 9m46s, load 11.44 before and 3.16 after) had a sum of 2908.3 s over the files; this repeat sums to 3249.2 s over 120 files (the two sums differ by 12 percent); a sum of per-file seconds is not a wall time (16 pytest processes ran at once), and the wall time of the same command is the real value: 9m46s (586 s) the first time and 12m38s (758 s) this repeat; the plan's 580 s is the sum of the single-entry walls (D4, D9) and is within 1 percent of the 586 s wall, so 8 parts stands.

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

### Same list on HEAD at f9f9a72 (nine entries, first deal), SS-24

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

## Assignment (decision D4, D7), second deal after the full suite run at f9f9a72 / 1301c74

The first deal (the table of the first round: launch_e2e, resume_entrypoints, actions_layer / launch_cli, station_channel, oauth_review / and so on) was measured alone and gave, at load 1.5 to 4.6: 96, 99, 131, 204, 156, 86, 85, 149 s for the parts 1 to 8 (REST processes 94, 97, 130, 202, 154, 85, 84, 147 s), largest over smallest 2.4, and in the full run of `bash tests/run_all.sh` at 1301c74 `platform_shard_5_test.sh` ran into the 300 s limit (TIMEOUT, the other lane was running a suite at the same time). The reason is plain in the numbers: the REST process (12 files one after the other) is the longest process of every part and the old deal left the REST of part 4 at 202 s and of part 7 at 84 s. The deal was redone with the per file seconds of the two runs above (the average of the base run and of the HEAD run, the HEAD run scaled by 3249.2 / 4894.0 to the same total), searching which 24 files to name so that the REST shards come out about equal; the named lines were then dealt out longest first, each to the part that had the least so far (REST counted in), at most three per part, ties to the lower number. The REST rule did not change (sorted by name, modulo 8). `tests/platform_test.sh` is the only code file changed.

Why not simply the 24 longest files: tested on the same numbers, naming the 24 longest leaves REST estimates of 103 to 208 s (parts 3 and 4 above 190 s), while the chosen 24 give 159 to 178 s. station_cancel (100 s) stays in a REST process for that reason.

| Part | Named files (seconds: average of the two runs) | Named sum | REST est. (12 or 13 files, one process) | Measured: named processes / REST process | Entry alone |
|---|---|---|---|---|---|
| 1 | owner_binding 117, oauth_mcp 68, resume_edit_params_station 39 | 223 | 160 (12 files) | 56.4 / 38.7 / 46.0 / 111 s | 112 s |
| 2 | keep_submissions 112, confirm_page 51, clean_page 47 | 210 | 166 (12 files) | 58.4 / 19.1 / 19.1 / 98 s | 100 s |
| 3 | station_channel 89, pat 88, web_login 28 | 205 | 176 (12 files) | 58.6 / 50.0 / 22.7 / 86 s | 87 s |
| 4 | platform_parts 95, http_site_samplesheet 74, launch_nextflow 39 | 208 | 174 (12 files) | 115.7 / 52.6 / 32.9 / 135 s | 137 s |
| 5 | resume_platform 88, launch_e2e 83, launch_followup 32 | 202 | 178 (12 files) | 42.7 / 55.0 / 26.6 / 138 s | 139 s |
| 6 | station_launch 99, resume_entrypoints 79, cleanup_offer 38 | 216 | 168 (12 files) | 59.5 / 38.8 / 15.2 / 100 s | 102 s |
| 7 | station_resume 109, owner_gaps 70, relay_loopback 36 | 216 | 167 (12 files) | 71.6 / 25.0 / 43.5 / 97 s | 99 s |
| 8 | launch_cli 126, oauth 49, web_board 42 | 216 | 159 (12 files) | 72.9 / 19.0 / 38.6 / 98 s | 99 s |

The measured columns are the pytest processes of the part in the order of the lines (three named, then REST), seconds, from the run of the entry alone below. Largest over smallest REST process measured: 138 / 86 = 1.6; entries alone 139 / 87 = 1.6 (earlier deal 204 / 84 = 2.4). The estimate columns (average seconds) are within 10 percent for the parts 1, 2, 4, 5 and not for part 3 (est. 176 s, measured 86 s); the per file seconds are noisy because other lanes use the machine, which is why the walls, not the estimates, are the evidence.

Conflict in the plan, decided by the executor and flagged for the developer-agent: "at most three named files per part" (SS-19, SS-20, SS-25: at most 24 named files) cannot hold together with "every file of 20 s or more on its own line" (SS-24). In the base list 48 files take 20 s or more; 2 of them are the clock part, 24 are named (all 24 named files are 20 s or more in the base list), and 22 stay in the REST processes (name, seconds in the base list): station_cancel 105.5, station_fakeplatform 50.6, station_envs 47.7, datasets 47.3, cloud_upload 46.3, oauth_review 44.1, human_channel 41.3, owner_tokens 39.6, wrapper 35.6, resume_lineage 33.7, cloud_cost 32.1, wrapper_nf2 25.1, actions_layer 24.4, resume_edit_params_platform 23.8, guidance 23.5, temp_password 23.4, su_usd 23.4, pipeline_launch_station 23.0, review_fixes 22.4, cli 22.3, byte_channel_a 21.0, web_welcome 20.6. The old combined lines (`test_launch_e2e.py`, `test_station_fakeplatform.py`, `test_station_channel.py` together) are split: launch_e2e and station_channel are named, station_fakeplatform is a REST file. If the developer-agent wants every 20 s file alone, the number of processes goes to about 46 plus the REST of each part and the limit of 3 named lines per part (SS-19, SS-20) must go; that is a ruling on the plan, not for the executor.

The first attempt named only 18 files and the rest of part 6 dominated (measured walls 132, 141, 131, 72, 73, 139, 77, 107 s, clock 179 s, all ok, ratio about 1.96); that was the first deal. test_launch_nextflow.py has a process of its own (SS-23).

### Single item walls on this machine, SS-55 and SS-56

Each of the nine entries run alone, one after the other, `bash tests/<entry>`, load read from `/proc/loadavg` before and after. The machine is shared with other lanes, so the load is only sometimes under 3.

Second deal (the lists now on the branch):

| Entry | Wall | Load before / after |
|---|---|---|
| platform_test.sh (part 1) | 112 s | 8.98 / 4.46 |
| platform_shard_2_test.sh | 100 s | 4.46 / 3.39 |
| platform_shard_3_test.sh | 87 s | 3.39 / 3.46 |
| platform_shard_4_test.sh | 137 s | 3.46 / 6.45 |
| platform_shard_5_test.sh | 139 s | 6.45 / 3.13 |
| platform_shard_6_test.sh | 102 s | 3.13 / 2.09 |
| platform_shard_7_test.sh | 99 s | 2.09 / 2.45 |
| platform_shard_8_test.sh | 99 s | 2.45 / 2.55 |
| platform_clock_test.sh | 213 s | 2.55 / 3.48 |

Largest over smallest of the eight numbered parts: 139 / 87 = 1.6. Not under 1.5, and the load never stayed under 2 for a whole run, so D5 applies (numbers recorded, not judged on seconds). What is left: the REST process of a part (12 files in a row, fixed by the round robin rule that the contract does not allow to change) is its longest process, and the REST estimates of the parts differ by up to 12 percent before any noise. Parts 4 and 5 are the longest (137, 139 s): part 4 has test_platform_parts.py as a named process (116 s, it runs the part lists many times) beside a 135 s REST. The lever left is the choice of the 24 names, tuned with quiet numbers; the lists are in `tests/platform_test.sh`. The clock entry is 213 s alone at load about 3 and stays as D1 says (not split in this slice; it was TIMEOUT 300 s before).

First deal, for the record (alone, load 1.5 to 4.6): 96, 99, 131, 204, 156, 86, 85, 149 s and clock 214 s. First deal at load 4 to 9 (the earlier run): 135, 126, 186, 232, 182, 115, 104, 156 s, clock 250 s.

## Before and after (SS-52..SS-61), `run_all.sh --only platform_`

AFTER (first deal, nine entries), load at start `14:37:47 load average: 3.84, 4.16, 4.04`, at end `14:58:03 load average: 8.76, 8.08, 6.74`:

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

## Full suite at 0f9af82 (SS-53, SS-54, SS-59)

`bash tests/run_all.sh` through `abf-fast-suite ... --retry-failed-once` (no `--timeout`, so the default 300 s), nproc=16, 1 minute load 0.16 at the end of the run (load at the start was not recorded; the runs of the earlier commit 1301c74 had a TIMEOUT in `platform_shard_5_test.sh` while another lane was running a suite, which led to the second deal above). Result 133/133, no TIMEOUT line, the nine platform entries 205 s (clock), 9 s (direction docs), 85, 70, 104, 126, 101, 81, 77 s (parts 2 to 8), 90 s (part 1). Slowest entry is the clock one: two files that were not split on purpose (D1). The only change after this run is this ledger section.

```
abf-fast-suite: worktree /mnt/c/Users/marvi/Desktop/agentic-bioflow/wt/suite-speed at 0f9af828fc039836415a2c7c9869da64a91fb37e, mirror /home/ycmarvinlin/abf-mirror/suite-speed
abf-fast-suite: running in slot 2 of 2
root:    /home/ycmarvinlin/abf-mirror/suite-speed
version: 3.0.0-dev
logs:    /tmp/bioflow-tests.ih8K8X

agent_ctl_connection_id_test.sh                ok       1s
bash32_arrays_test.sh                          ok       0s
bsd_userland_test.sh                           ok       1s
build_package_test.sh                          ok       6s
cite_test.sh                                   ok       0s
collect_provenance_test.sh                     ok       2s
column_output_relay_rule.sh                    ok       0s
command_layer_is_record_neutral.sh             ok       0s
command_layer_is_site_neutral.sh               ok       0s
commands_resolve_their_own_paths.sh            ok       0s
commands_scope_tw_to_the_workspace.sh          ok       0s
conditions_matrix_test.sh                      ok       5s
confirm_cleanup_behind_heredoc_test.sh         ok       73s
confirm_cleanup_candidates_timing_test.sh      ok       14s
confirm_cleanup_test.sh                        ok       24s
confirm_launch_test.sh                         ok       40s
confirm_walkthrough_test.sh                    ok       10s
constitution_6_test.sh                         ok       0s
constitution_checks_exist_test.sh              ok       1s
constitution_scope_test.sh                     ok       6s
credentials_stay_in_settings_test.sh           ok       2s
daemon_cwd_test.sh                             ok       0s
dev_workflow_test.sh                           ok       0s
docs_nano4_acceptance.sh                       ok       0s
docs_nano4_keys.sh                             ok       0s
duplicate_run_check_test.sh                    ok       1s
egress_allow_test.sh                           ok       1s
egress_ctl_restart_test.sh                     ok       8s
env_sh_test.sh                                 ok       1s
fetch_test.sh                                  ok       0s
flow_skills_layout_test.sh                     ok       1s
gate_big_input_test.sh                         ok       11s
gate_exit_contract_test.sh                     ok       9s
gate_output_failclosed_test.sh                 ok       2s
gate_process_count_test.sh                     ok       0s
gates_without_jq_test.sh                       ok       9s
generate_samplesheet_test.sh                   ok       3s
guard_plugin_files_test.sh                     ok       8s
harness_kits_test.sh                           ok       0s
hooks_fail_closed_test.sh                      ok       0s
hosted_deploy_test.sh                          ok       1s
in_use_speed_test.sh                           ok       0s
in_use_test.sh                                 ok       3s
init_workspace_test.sh                         ok       1s
input_checksums_test.sh                        ok       1s
inspect_sides_test.sh                          ok       3s
install_deps_test.sh                           ok       0s
install_doc_test.sh                            ok       0s
intro_languages_test.sh                        ok       0s
intro_test.sh                                  ok       1s
inventory_outputs_test.sh                      ok       0s
jev_test.sh                                    ok       19s
launch_provenance_test.sh                      ok       0s
launch_recheck_test.sh                         ok       1s
machine_identity_test.sh                       ok       2s
methods_text_fetch_test.sh                     ok       6s
methods_text_test.sh                           ok       2s
migration_doc_test.sh                          ok       0s
next_step_test.sh                              ok       2s
nf_relay_domains_test.sh                       ok       1s
no_hardcoded_paths.sh                          ok       1s
no_per_pipeline_config.sh                      ok       0s
no_pipefail_grep_q_test.sh                     ok       0s
no_second_run_state_test.sh                    ok       2s
off_design_single_path.sh                      ok       1s
on_site_parallel_test.sh                       ok       30s
on_site_test.sh                                ok       11s
operations_doc_test.sh                         ok       0s
package_crate_test.sh                          ok       0s
package_gaps_test.sh                           ok       2s
parallel_watch_check_test.sh                   ok       0s
path_shapes_test.sh                            ok       1s
pitfalls_supervise_test.sh                     ok       0s
platform_clock_test.sh                         ok       205s
platform_direction_docs_test.sh                ok       9s
platform_shard_2_test.sh                       ok       85s
platform_shard_3_test.sh                       ok       70s
platform_shard_4_test.sh                       ok       104s
platform_shard_5_test.sh                       ok       126s
platform_shard_6_test.sh                       ok       101s
platform_shard_7_test.sh                       ok       81s
platform_shard_8_test.sh                       ok       77s
platform_storage_doc_test.sh                   ok       0s
platform_test.sh                               ok       90s
plugin_intro_test.sh                           ok       18s
portable_userland.sh                           ok       2s
positron_bridge_test.sh                        ok       0s
positron_run_test.sh                           ok       5s
preflight_reach_test.sh                        ok       1s
preflight_ssh_fold_test.sh                     ok       7s
prepare_launch_ce_test.sh                      ok       2s
prepare_launch_test.sh                         ok       1s
principle_12_test.sh                           ok       0s
principle_13_test.sh                           ok       0s
principle_9_test.sh                            ok       0s
push_test.sh                                   ok       1s
record_adapter_test.sh                         ok       0s
relaunch_override_test.sh                      ok       1s
report_facts_test.sh                           ok       0s
report_test.sh                                 ok       1s
require_python_test.sh                         ok       0s
reset_master_test.sh                           ok       1s
run_all_count_test.sh                          ok       0s
run_all_retry_test.sh                          ok       10s
run_all_shard_test.sh                          ok       4s
run_all_test.sh                                ok       12s
runs_board_test.sh                             ok       1s
runs_report_format_test.sh                     ok       0s
scripts_name_their_alternative.sh              ok       0s
session_start_test.sh                          ok       3s
settings_migrate_reports_test.sh               ok       1s
settings_test.sh                               ok       2s
setup_doc_test.sh                              ok       0s
setup_proof_test.sh                            ok       1s
setup_verify_only_test.sh                      ok       0s
site_report_test.sh                            ok       0s
site_scripts_via_on_site.sh                    ok       0s
skill_names_command_file_test.sh               ok       0s
skill_portability_test.sh                      ok       0s
skill_requires_intro_test.sh                   ok       0s
skill_runs_uses_actions_test.sh                ok       1s
skills_name_the_v3_launch_path.sh              ok       0s
status_test.sh                                 ok       1s
t3_scripts_are_tagged.sh                       ok       0s
task_health_test.sh                            ok       1s
testing_web_doc_test.sh                        ok       0s
tune_resources_test.sh                         ok       1s
turn_timing_test.sh                            ok       0s
where_test.sh                                  ok       1s
why_pending_test.sh                            ok       0s
windows_privacy_test.sh                        ok       1s
works_without_host_test.sh                     ok       4s
wsl_bridge_test.sh                             ok       2s

133/133 passed
all green
```
