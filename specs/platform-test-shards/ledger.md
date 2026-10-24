# 把平台測試拆成幾支，每支在 CI 上遠低於 300 秒 progress ledger

## 改前量測 (step 0)

量測時的 commit: 89dd60237a636b3edfc3e4396ac29c361e9ef1c9（本分支的計畫／測試案例 commit，程式與 origin/v3 b086b6d 相同）。WSL Ubuntu、16 核、暖快取，從 git archive 解出的副本跑（所以沒有 .git，另有 4 個讀 git 狀態的測試在副本裡紅：test_launch_static::test_tc074、test_scope::test_tc071、test_station_static::test_tc087、test_su_packaged::test_gitignore_and_tracking；它們在真實樹是綠的，不影響牆鐘數字）。

```
time bash tests/platform_test.sh (改前，一個項目): 6m36.530s
time bash tests/platform_clock_test.sh (改前): 2m43.783s

每個分片自己的秒數 (改前, platform_test.sh, 依啟動順序，最後一個是 REST):
8 passed in 12.82s 
11 passed in 20.53s 
6 passed in 96.32s (0:01:36) 
100 passed in 131.75s (0:02:11) 
107 passed in 114.00s (0:01:54) 
265 passed in 124.66s (0:02:04) 
73 passed in 68.30s (0:01:08) 
203 passed in 112.07s (0:01:52) 
170 passed in 135.82s (0:02:15) 
126 passed, 7 warnings in 100.89s (0:01:40) 
186 passed in 146.43s (0:02:26) 
4 failed, 1900 passed in 395.17s (0:06:35) 

前 30 慢測試 (--durations=30, 跨分片合併):
95.19s setup    tests/test_launch_nextflow.py::test_tc026_the_progress_of_a_run_is_seen_changing_and_ends_equal_to_the_trace
24.20s call     tests/test_launch_e2e.py::test_tc018_an_answer_after_the_deadline_is_still_recorded_and_a_killed_agent_leaves_an_honest_message
13.19s call     tests/test_relay_loopback.py::test_tc075_with_no_forward_file_the_relay_answers_exactly_as_it_did_before_feature_007b
9.52s call     tests/test_relay_loopback.py::test_tc080_a_listener_that_took_over_the_forward_port_never_sees_a_run_token[silent]
9.22s call     tests/test_launch_e2e.py::test_tc034_fetch_records_brings_the_logs_back_and_rebuild_puts_a_lost_run_right
8.60s call     tests/test_oauth.py::test_tca04_nothing_else_on_the_mcp_process_answers_without_a_token
6.79s call     tests/test_launch_e2e.py::test_tc040_tc044_a_cancel_stops_the_one_job_and_the_second_try_finds_it_gone
6.18s call     tests/test_wrapper.py::test_tc056_a_wrong_sha256_stops_the_run_in_both_modes
5.04s call     tests/test_oauth.py::test_tca01_a02_the_mcp_process_serves_the_resource_metadata_and_the_401_points_to_it
5.01s call     tests/test_station_envs.py::test_tc039_environments_agents_and_tokens_survive_a_restart_and_a_rebuild
4.96s call     tests/test_oauth.py::test_tcb04_the_two_hundred_and_first_client_is_refused
4.21s call     tests/test_web_running.py::test_r103_r114_limits_and_readonly
3.99s call     tests/test_station_fakeplatform.py::test_tc067_the_token_is_nowhere_in_output_arguments_or_what_a_site_command_sees
3.95s call     tests/test_guidance.py::test_tc404_the_wheel_copy_equals_the_repo_skills
3.80s call     tests/test_station_launch.py::test_tc_ls_12_47_a_terminal_launch_with_the_old_arguments_shows_the_site_start_and_keeps_it_in_the_bundle_only
3.79s call     tests/test_launch_cli.py::test_tc001_the_whole_launch_is_shown_before_the_question_and_nothing_is_written_until_y
3.68s call     tests/test_wrapper_nf2.py::test_tc054_without_the_second_pair_ci_fails_and_a_local_run_skips_loudly
3.64s call     tests/test_owner_binding.py::test_tc043_with_no_users_the_row_stays_null
3.57s call     tests/test_launch_e2e.py::test_tc010_tc061_no_web_page_and_no_mcp_tool_can_launch_or_cancel
3.52s call     tests/test_station_fakeplatform.py::test_tc021_only_a_local_address_may_use_plain_http
3.45s call     tests/test_human_channel.py::test_tca02_a06_the_summary_and_the_bundle_are_the_ones_of_the_terminal
3.41s call     tests/test_owner_binding.py::test_tc027_the_terminal_cancel_asks_for_no_account
3.38s setup    tests/test_su_packaged.py::test_rates_found_in_the_wheel_data
3.34s call     tests/test_launch_cli.py::test_tc040_a_cancel_shows_the_run_the_job_number_and_the_folder_and_asks
3.34s call     tests/test_keep_submissions.py::test_tc162_tc163_tc164_a_terminal_cancel_keeps_its_content
3.33s call     tests/test_launch_followup.py::test_tcf2_05_the_strictest_row_of_the_history_decides[refused-True]
3.33s call     tests/test_launch_cli.py::test_tc002_a_small_y_and_a_capital_Y_both_send[Y\n]
3.32s call     tests/test_station_channel.py::test_tc064_after_the_shared_connection_ends_nothing_rebuilds_the_forward
3.31s call     tests/test_resume_entrypoints.py::test_tc145_y_queues_the_job_through_the_terminal_channel_and_says_what_became_of_it[resume-\u78ba\u5b9a\u7e8c\u8dd1\uff1f
3.31s call     tests/test_oauth_mcp.py::test_tcf08_nothing_reaches_the_queue_without_a_person_whatever_is_held
```

結論: 最慢的是一個「REST」分片（1900 個測試、395 s，所有沒被點名的 80 多個檔擠在一個 pytest 行程），其次是 test_launch_nextflow.py 的一個 setup (95 s)；單一測試最慢 95 s，沒有一個接近 300 s。所以瓶頸是 REST 分片的檔案數，不是某一個測試。依此，REST 改成按檔名輪流分給三份。

## 改後量測

commit 5081b7eb845bd7e330c30c4f49f35f0c680de2ba，同一台機器、暖快取，從 git clone 的副本（有 .git）跑，四個項目依序單獨跑：

```
platform_test.sh: 2m50.497s   (pytest exit code of each shard, in order:  0 0 0 0 0
platform tests: pytest exit 0, 0 skipped)
    shard: 8 passed in 17.09s 
    shard: 11 passed in 11.61s 
    shard: 6 passed in 43.39s 
    shard: 100 passed in 124.36s (0:02:04) 
    shard: 678 passed in 169.47s (0:02:49) 
platform_shard_2_test.sh: 2m2.213s   (pytest exit code of each shard, in order:  0 0 0 0 0
platform tests: pytest exit 0, 0 skipped)
    shard: 107 passed in 85.09s (0:01:25) 
    shard: 265 passed in 114.96s (0:01:54) 
    shard: 73 passed in 53.77s 
    shard: 203 passed in 70.25s (0:01:10) 
    shard: 782 passed in 121.18s (0:02:01) 
platform_shard_3_test.sh: 2m3.463s   (pytest exit code of each shard, in order:  0 0 0 0
platform tests: pytest exit 0, 0 skipped)
    shard: 170 passed in 101.92s (0:01:41) 
    shard: 126 passed, 7 warnings in 68.87s (0:01:08) 
    shard: 186 passed in 112.47s (0:01:52) 
    shard: 461 passed in 122.42s (0:02:02) 
platform_clock_test.sh: 2m43.343s   (pytest exit code of each shard, in order:  0 0
platform tests: pytest exit 0, 0 skipped)
    shard: 85 passed in 64.88s (0:01:04) 
    shard: 23 passed in 97.25s (0:01:37) 

time ABF_PLATFORM_PREFLIGHT_ONLY=2 bash tests/platform_test.sh (暖快取): 0m0.535s  (<= 20 s, 接受)
```

- 第 1 份 170.5 s = 改前 396.5 s 的 43.0%；第 2 份 122.2 s = 30.8%；第 3 份 123.5 s = 31.1%。三份都 <= 45%（PS-52）。
- 三份最大/最小 = 170.5 / 122.2 = 1.40 <= 1.5（PS-54）。第 1 份偏長是因為 test_launch_nextflow.py 與 test_wrapper*.py 都在那份；整行搬移後再平衡的空間不大，不再硬調。
- 時鐘項目：改前 163.8 s、改後 163.3 s，不變（PS-53）。它沒被拆，在 CI 上是否遠低於 300 s 要等合併後的 CI。
- PS-55: 暖預檢 0.5 s <= 20 s。bootstrap 不優化。
- PS-58: bash tests/run_all.sh --list --allow-msys 改前 122 行、改後 124 行（多 2）。

## 受影響的既有斷言 5–10（改後，WSL，程式同 5081b7e）

```
bash tests/run_all_count_test.sh: ok, exit 0
bash tests/run_all_test.sh: all passed, exit 0
bash tests/run_all_retry_test.sh: TC-053 (3 lines) ok, TC-089 (3 lines) ok, PS-18..PS-25 + PS-44 ok, "all run_all_retry cases ok"
pytest test_platform_parts.py test_wrapper.py test_wrapper_nf2.py test_scope.py test_launch_static.py: 56 passed (0 skipped), platform tests: pytest exit 0
```
（test_platform_parts.py 單獨：22 passed，含 test_tcf3_04、test_tcf3_05。）

## diff --stat 89dd602..HEAD（不含 specs/）

範圍內 10 個檔：docs/PLATFORM.md、docs/TESTING.md、platform/tests/test_platform_parts.py、tests/platform_clock_test.sh、tests/platform_shard_2_test.sh（新）、tests/platform_shard_3_test.sh（新）、tests/platform_test.sh、tests/quarantine.txt、tests/run_all.sh、tests/run_all_retry_test.sh。hooks/、.github/、platform/abf_* 無變動。

## 待 developer-agent 裁決

1. .github/workflows/tests.yml 可把 --timeout 900 拿掉（本任務未動 .github/）。
2. CI 上四個項目的實際秒數合併後才知道；時鐘項目沒拆（本機 163 s）。
3. 暖預檢 0.5 s，不需優化 bootstrap。
