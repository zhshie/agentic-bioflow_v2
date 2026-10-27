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
- 少擋：被 .gitignore 忽略的檔與二進位（非程式碼）；多擋：未 git add 的新 .py、失敗時列檔名。

## 3b. tc014
- 暫存副本在 `while` 前插 `time.sleep(3)`：舊寫法 `1 failed`；新寫法 `1 passed`。
- `test_station_e2e.py` 整檔 N=5：85 passed ×5（約 71～74 s）；同時 4 份：4×85 passed（約 86 s）。

## 3c. httpx timeout
- 日誌證據，不是強制重現：CI 40099957808 `httpx.ReadTimeout`；venv：`0.28.1 Timeout(timeout=5.0)`。
- 兩檔共 11 處呼叫都帶 `timeout=HTTP_TIMEOUT`（機械檢查 11/11）。
- `test_launch_e2e.py`：本機沒有 pinned Nextflow（`which nextflow` 無），單跑整檔 8 passed + 1 error（`test_tc034`，訊息「need the second pinned Nextflow: run them through tests/platform_test.sh」；base 同樣 8 passed 1 error，與本改動無關）。經 `ABF_PLATFORM_PART=1 bash tests/platform_test.sh`（含該檔）：100 passed，綠。

## 量測表（完成標準 6；單獨跑，WSL 桌機）
| PART | 總時間 | pytest 行程（passed / 秒） |
|---|---|---|
| 1 | 6m04s | 8/14.9、11/24.2、6/35.5、100/140.3、1132/361.8 |
| 2 | 3m57s | 121/118.9、265/119.0、73/60.7、203/104.1、1212/235.4 |
| 3 | 3m25s | 170/140.3、126/103.9、186/153.1、735/203.9 |

## 其他
- 守門測試（全套內含）：no_pipefail_grep_q_test、portable_userland、run_all_count_test、constitution_scope_test、hooks_fail_closed_test、gates_without_jq_test、test_scope::test_tc072 由全套確認。
- `git diff | grep -nE '^\+.*(skip|xfail|flaky|retry|rerun)'` 唯一命中是 ledger 引用的註解 `flaky-three ruling 5`（檔名，非跳過／重試）。
- `git diff --stat` 只有：confirm_launch_test.sh、jev_test.sh、test_station_e2e.py、test_launch_e2e.py（加本 ledger）。
