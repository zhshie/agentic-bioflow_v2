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

## Measurements

Machine: nproc=16 (WSL Ubuntu). Other lanes ran suites at the same time, so load varied from 1.5 to 21; all seconds are under that load and so inflated. The load figures are written next to each run.

Step 0, per file seconds on the base copy: `ABF_PLATFORM_PART=all ABF_PYTEST_ARGS=--durations=0 bash tests/platform_test.sh`, real 9m46s. Load before `14:03:45 load average: 11.44, 4.75, 3.47`, after `14:13:09 load average: 3.16, 5.87, 5.92`. Sum of the 118 files 2908.3 s (inflated about 2.4 times by load); the two clock files ran alone and are about clean (station_e2e 68.1 s, nextflow_e2e 109.8 s). Measured wall about 586 s against the plan's about 580 s: inside 30 percent, so 8 parts stands (D4, D9).

Per file seconds (whole list):

```
135.9 tests/test_owner_binding.py
122.4 tests/test_resume_platform.py
109.8 tests/test_nextflow_e2e.py
108.2 tests/test_station_resume.py
101.6 tests/test_launch_cli.py
98.3 tests/test_station_cancel.py
97.3 tests/test_launch_e2e.py
96.9 tests/test_station_launch.py
77.0 tests/test_keep_submissions.py
72.6 tests/test_confirm_page.py
70.7 tests/test_oauth.py
68.1 tests/test_station_e2e.py
67.7 tests/test_station_channel.py
62.1 tests/test_pat.py
56.6 tests/test_resume_entrypoints.py
56.4 tests/test_owner_gaps.py
52.8 tests/test_oauth_mcp.py
52.3 tests/test_byte_channel_a.py
48.7 tests/test_actions_layer.py
45.1 tests/test_launch_nextflow.py
44.6 tests/test_datasets.py
43.1 tests/test_relay_loopback.py
41.8 tests/test_aws_ce.py
39.7 tests/test_http_site_samplesheet.py
38.7 tests/test_clean_page.py
38.0 tests/test_station_envs.py
37.2 tests/test_oauth_review.py
35.9 tests/test_owner_tokens.py
34.6 tests/test_web_login.py
33.4 tests/test_resume_edit_params_station.py
33.3 tests/test_cleanup_backfill.py
33.1 tests/test_wrapper.py
(the other 86 files take 32.0 s or less each; the full list is kept in the run output, not repeated here)
```

## Assignment (decision D4, D7)

Named files (24, three per part, longest processing time first using the seconds above plus the real load of the round robin rest of each part), rest of the files round robin by sorted name modulo 8:

| Part | Named files |
|---|---|
| 1 | launch_e2e, resume_entrypoints, actions_layer |
| 2 | launch_cli, station_channel, oauth_review |
| 3 | keep_submissions, oauth, aws_ce |
| 4 | resume_platform, owner_gaps, launch_nextflow |
| 5 | station_cancel, pat, clean_page |
| 6 | station_resume, confirm_page, http_site_samplesheet |
| 7 | owner_binding, byte_channel_a, cleanup_backfill |
| 8 | station_launch, oauth_mcp, datasets |
| clock | station_e2e, nextflow_e2e (unchanged, each alone) |

Estimated sums per part 339 to 345 s (ratio 1.02). The first attempt named only 18 files and the rest of part 6 dominated (measured walls 132, 141, 131, 72, 73, 139, 77, 107 s, clock 179 s, all ok, ratio about 1.96); one adjustment added 6 named files. test_launch_nextflow.py has a process of its own (SS-23).

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
