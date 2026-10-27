# 三支常誤報的測試改成確定性（confirm_launch 大輸入預算、jev .pyc 掃描、station/launch e2e 時窗與 httpx 逾時） progress ledger

## 進度（executor，2026-10-27）
- [x] 1 confirm_launch_test.sh envbig、[x] 2 jev_test.sh TC-085/075、[x] 3b tc014、[x] 3c httpx timeout、[x] 量測表。證據在 WSL 暫存副本 `~/ef3`（base=HEAD 的複本＋本分支改動）。

## 1. confirm_launch_test.sh（待裁決 1 = A，已核准）
- 取代說明：`relay-warning-hardening` 的「都 < 1 秒」由 flaky-three 裁決 5 取代（絕對值改 `BIG_CEIL_MS=10000`＋比例檢查 <= 40）。
- TC-001 改前紅（舊檔，16 個忙迴圈）：`TC-048 EXTRA_DOMAINS 60 KB FAIL: slow (556 ms)`；`TC-051 … 1 MB FAIL: slow (2335/2192/2135/1908 ms)`；`POL-22 / POL-22b TC-032 FAIL: slow (1711/1793 ms)`，共 7 條 FAIL。
- TC-002 改後（同條件）：rc=0、`all passed`；比例行：`O(n) 1 MB tail / 60 KB tail ok (2069 / 432 ms)`、`spread ok (2076 / 339 ms)`、`PEER tail ok (2147 / 522 ms)`、`PEER spread ok (1819 / 411 ms)`、`TC-032 ok (2151 / 522 ms)`。
- TC-004 連跑：閒置 10/10 綠（1 MB 約 650～1000 ms；比值 4.5～12）；16 忙迴圈 10/10 綠（1 MB 約 2200～2800 ms；比值 4.0～7）。
- 反向強制條件（暫存副本把 `H` 換成包裝腳本，只對 >30 KB 輸入延遲）：(i) 平方延遲：`TC-051 EXTRA_DOMAINS O(n) tail FAIL: ratio 52 > 40 (9205/176 ms)`、`spread FAIL: ratio 78 (9237/117)`、`PEER spread FAIL: ratio 70 (9024/128)`，而 10 s 上限仍過（未出現 slow）；(ii) 固定 sleep 11：10 個 envbig 案例全 `FAIL: slow (11.1～12.2 s)`。
- 機械檢查：envbig 呼叫 15 行、第 4 引數非純數字；`BIG_CEIL_MS` 出現 2 次；`grep -c 'O(n)'` = 5；第 74 行未動；第 596–612 行未動。
- 比原本多擋：平方成本、hook 慢到接近逾時；少擋：絕對 1000 ms（改 10000，裁決 5 核准）。

## 2. jev_test.sh
- 改前紅：`py_compile` 三個 test_web_* 的 .pyc 後，舊檔 `TC-085 … FAIL: got '3', wanted '0'`。
- 改後：同條件 `TC-085 ok`、`TC-075 ok`；N=20（.pyc 一直留著）20/20 綠。
- 正向控制：未追蹤 `platform/zz_probe.py` 含 jev → `FAIL: got 'platform/zz_probe.py ', wanted ''`；刪除後綠。
- 少擋：被 .gitignore 忽略的檔與二進位（非程式碼）。理由：它們不是 `platform/` 的程式碼（.pyc 是編譯產物，不會被提交，也不會跑進產品）；`specs/015-jev-triage/test-case.md:128`（TC-085）要的是「搜尋 `platform/`」裡有沒有 jev 字樣，即搜程式碼，不是搜產物。多擋：未 git add 的新 .py、失敗時列檔名。不改 015 規格字句。

## 3b. tc014
- 暫存副本在 `while` 前插 `time.sleep(3)`：舊寫法 `1 failed`；新寫法 `1 passed`。
- `test_station_e2e.py` 整檔 N=5：85 passed ×5（約 71～74 s）；同時 4 份：4×85 passed（約 86 s）。
- 比原本多擋／少擋：多擋：無（`assert len(seen) >= 3` 與訊息原樣，仍要求至少 3 筆）；少擋：無（只把等待窗上限放寬，斷言一個字沒動，對應維護者「放寬等待上限而不是放寬斷言」；因此沒有任何需要引用的放鬆斷言裁決條文）。

## 3c. httpx timeout
- 日誌證據，不是強制重現：CI 40099957808 `httpx.ReadTimeout`；venv：`0.28.1 Timeout(timeout=5.0)`。
- 兩檔共 11 處呼叫都帶 `timeout=HTTP_TIMEOUT`（機械檢查 11/11）。
- `test_launch_e2e.py`：本機沒有 pinned Nextflow（`which nextflow` 無），單跑整檔 8 passed + 1 error（`test_tc034`，訊息「need the second pinned Nextflow: run them through tests/platform_test.sh」；base 同樣 8 passed 1 error，與本改動無關）。經 `ABF_PLATFORM_PART=1 bash tests/platform_test.sh`（含該檔）：100 passed，綠。

- 比原本多擋／少擋：多擋：無（每個呼叫的回應斷言原樣）；少擋：無（`timeout=HTTP_TIMEOUT` 只把預設 5 s 的讀取上限放寬，不改任何斷言；逾時仍會丟 `httpx.ReadTimeout` 讓測試紅；因此沒有任何需要引用的放鬆斷言裁決條文）。

## 量測表（完成標準 6；單獨跑，WSL 桌機）
shard 檔名清單由 `ABF_PLATFORM_PART=<n> ABF_PLATFORM_LIST=1 bash tests/platform_test.sh` 列出（檔都在 `platform/tests/`，下表省略前綴 `tests/`）；每列的順序與清單順序相同。

| PART | 總時間 | shard | 檔名清單 | passed / 秒 |
|---|---|---|---|---|
| 1 | 6m04s | 1 | test_wrapper_nf2.py | 8 / 14.9 |
| 1 | | 2 | test_wrapper.py | 11 / 24.2 |
| 1 | | 3 | test_launch_nextflow.py | 6 / 35.5 |
| 1 | | 4 | test_launch_e2e.py、test_station_fakeplatform.py、test_station_channel.py | 100 / 140.3 |
| 1 | | 5 | test_actions_layer.py、test_catalogue.py、test_cleanup_confirm.py、test_cloud_cost.py、test_common.py、test_estimate_su.py、test_gcb_ce.py、test_http_site_samplesheet.py、test_launch_followup_e2e.py、test_mcp.py、test_nfcore_catalogue.py、test_pipeline_files_action.py、test_pipeline_launch_station.py、test_platform_parts.py、test_receiver_nf2510.py、test_resume_edit_params_platform.py、test_review_fixes.py、test_schema.py、test_station_clean.py、test_station_owner.py、test_station_platform.py、test_su_in_get_run.py、test_temp_password.py、test_web_board.py、test_web_cost.py、test_web_guided_launch.py、test_web_running.py、test_web_v2_skeleton.py | 1132 / 361.8 |
| 2 | 3m57s | 1 | test_station_cancel.py、test_launch_cli.py | 121 / 118.9 |
| 2 | | 2 | test_station_launch.py、test_relay_loopback.py、test_station_envs.py | 265 / 119.0 |
| 2 | | 3 | test_station_resume.py | 73 / 60.7 |
| 2 | | 4 | test_resume_platform.py、test_resume_entrypoints.py、test_resume_lineage.py、test_resume_scope.py、test_resume_render.py | 203 / 104.1 |
| 2 | | 5 | test_byte_channel_a.py、test_chat_tools.py、test_cleanup_store.py、test_cloud_upload.py、test_compose.py、test_failures.py、test_gcb_launch.py、test_launch_bundle.py、test_launch_platform.py、test_model_key_refusal.py、test_oauth_review.py、test_pipeline_files_queue.py、test_pipelines_store.py、test_port_race.py、test_releases.py、test_resume_edit_params_station.py、test_review_fixes_2.py、test_scope.py、test_station_clean_gcb.py、test_station_packaging.py、test_station_static.py、test_su_packaged.py、test_validate.py、test_web_chrome_origin.py、test_web_finished.py、test_web_parity.py、test_web_settings.py、test_web_welcome.py | 1212 / 235.4 |
| 3 | 3m25s | 1 | test_owner_binding.py、test_pat.py、test_human_channel.py | 170 / 140.3 |
| 3 | | 2 | test_confirm_page.py、test_owner_gaps.py、test_launch_followup.py、test_web_login.py | 126 / 103.9 |
| 3 | | 3 | test_oauth.py、test_oauth_consent.py、test_oauth_tokens.py、test_oauth_mcp.py、test_keep_submissions.py | 186 / 153.1 |
| 3 | | 4 | test_byte_channel_b.py、test_clean_page.py、test_cli.py、test_cloud_wire.py、test_datasets.py、test_followup3.py、test_guidance.py、test_launch_docs.py、test_launch_static.py、test_module_sources.py、test_onboarding_doc.py、test_pipeline_launch.py、test_pipelines_validation.py、test_receiver.py、test_resume_edit_params_docs.py、test_resume_edit_params_words.py、test_run_diag_tools.py、test_secrets.py、test_station_docs.py、test_station_pipeline_files.py、test_status.py、test_su_usd.py、test_web_actions.py、test_web_confirm_plain.py、test_web_fixes_1.py、test_web_results_outputs.py、test_web_status_squares_3.py | 735 / 203.9 |

最長的一支 shard 是 PART 1 的第 5 支（361.8 s）；三個 PART 單跑各 3～6 分鐘，與 CI 單跑的 111～196 s 同量級。

## 3a／3d／待裁決 3：逾時與容量（TC-040、TC-042）
- **3a（TC-040）**：CI 的 `platform_test.sh TIMEOUT 300s`（6 次）全部發生在 PR #200 合併（2026-10-24T14:00:14Z）之前；#200 已把平台測試拆成四個項目，拆分後最近一次綠的 v3 四支分別 163／111／176／196 s。已被拆分修掉，本任務沒有再做任何事。
- **3d**：本機 900 秒 TIMEOUT（4 次）與 573～893 秒險綠，屬「兩套全套並跑的容量問題」（每支平台項目各開 4～5 個 pytest 行程再各起 Nextflow JVM；同一套在 CI 單跑 163 s，上表單跑也只要 3～6 分鐘），不是任何一條測試寫錯，測試檔修不掉。點名的是 platform 四支包裝檔（`tests/platform_test.sh`、`tests/platform_shard_2_test.sh`、`tests/platform_shard_3_test.sh`、`tests/platform_clock_test.sh`），它們本身沒有問題，**不得隔離**。
- **結論交 developer-agent**（待裁決 3）：看上面量測表後決定 (A) 放寬工作區 `abf-fast-suite.sh` 的 `--timeout 900`、(B) 在 `platform_test.sh` 加預設不變的同時 shard 數限制、(C) 全套改成每件只跑一次背景跑。本任務沒有修，也沒有隔離（`tests/quarantine.txt` 未動）。

## 不需要 migration（TC-061）
不需要 migration：只改測試檔（`tests/confirm_launch_test.sh`、`tests/jev_test.sh`、`platform/tests/test_station_e2e.py`、`platform/tests/test_launch_e2e.py`）。沒有任何資料庫結構、資料內容或 `platform/abf_platform/` 底下的檔被改。

## 其他
- 守門測試（全套內含）：no_pipefail_grep_q_test、portable_userland、run_all_count_test、constitution_scope_test、hooks_fail_closed_test、gates_without_jq_test、test_scope::test_tc072 由全套確認。
- `git diff | grep -nE '^\+.*(skip|xfail|flaky|retry|rerun)'` 唯一命中是 ledger 引用的註解 `flaky-three ruling 5`（檔名，非跳過／重試）。
- `git diff --stat` 只有：confirm_launch_test.sh、jev_test.sh、test_station_e2e.py、test_launch_e2e.py（加本 ledger）。
