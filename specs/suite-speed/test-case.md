# 測試案例：把平台測試拆成 8 份，每個項目在預設 300 秒內跑完（suite-speed）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
本任務沒有 spec.md；依據是 `specs/suite-speed/plan.md`（含「維護者原話」、「裁決」D1 至 D9）。
編號沿用計畫「失敗先行測試」的 SS-01 至 SS-14，另補 SS-15 起的案例（每條只驗一件事）。
-->

**規格**：`specs/suite-speed/plan.md`（本任務沒有 spec.md）　**總覽**：`test-case-overview.md`

白話說明：「平台測試」是 `platform/tests/test_*.py` 這一大批測試。`tests/run_all.sh` 一次跑一個「項目」（一支 `*_test.sh`），每個項目有 300 秒上限，只拿來抓卡死。以前平台測試拆成「3 份＋時鐘」共四個項目，在忙碌的機器上仍要 370 到 417 秒而被砍掉。這次改成「8 份＋時鐘」共九個項目，每份只放少量檔案；上限不調高。「REST」是沒被點名的其餘檔案，依檔名排序後輪流分到各份。「點名分片」是人工寫死、把特別慢的檔放在一起或獨佔一個 pytest 行程的那幾行。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

驗證方式「自動」＝由 `platform/tests/test_platform_parts.py`、`tests/run_all_retry_test.sh`、`tests/run_all_shard_test.sh` 這三支之一的測試案例執行（測試內以註解標 TC 編號，SS-12 至 SS-14 放在三支任一支即可，裁決 D9）；「手動」＝閱卷者讀 `specs/suite-speed/ledger.md`、`git diff` 或在 WSL 重跑核對（計畫通例與裁決 D9）。

## US-A — 九份清單：不漏、不重、新檔有歸屬、分片不膨脹（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SS-01 | 失敗先行 SS-01；完成標準 3 | 功能 | 本機有 `platform/tests/test_*.py` 全部檔案 | 用 `ABF_PLATFORM_LIST=1` 分別列出 `ABF_PLATFORM_PART=1` 至 `8` 與 `clock` 九份清單，全部合併 | 合併後排序，恰好等於 `platform/tests/test_*.py` 全部（加 `tests/` 前綴）；同一個檔沒有出現兩次 | 自動：`platform/tests/test_platform_parts.py` |
| SS-02 | 失敗先行 SS-02；作法 1 | 功能 | 同上 | 列出 `ABF_PLATFORM_PART=all` | 結果的檔案集合等於全部測試檔，也等於九份清單的聯集 | 自動：`platform/tests/test_platform_parts.py` |
| SS-15 | 失敗先行 SS-02 | 功能 | 同上 | 分別列出第 1 至 8 份 | 八份各自不是空的，且每一行的種類都是 `shard`（沒有 `alone`） | 自動：`platform/tests/test_platform_parts.py` |
| SS-16 | 失敗先行 SS-02；作法 1.5 | 功能 | 同上 | 列出 `PART=clock`，並檢查第 1 至 8 份 | `PART=clock` 恰為兩行 `alone`，依序是 `tests/test_station_e2e.py`、`tests/test_nextflow_e2e.py`；這兩個檔不在任何一份數字份的任何分片裡 | 自動：`platform/tests/test_platform_parts.py` |
| SS-03 | 失敗先行 SS-03 | 功能 | 同上 | 對九份清單裡的每個路徑檢查磁碟上是否存在 | 每個路徑都存在（檔被刪或改名時這裡先紅，不是等到 pytest 才報找不到） | 自動：`platform/tests/test_platform_parts.py` |
| SS-17 | 失敗先行 SS-03 | 功能 | 沒設 `ABF_PLATFORM_PART` | 列出清單，再列出 `PART=1` 的清單 | 兩者完全相同（預設仍是第 1 份） | 自動：`platform/tests/test_platform_parts.py` |
| SS-04 | 失敗先行 SS-04；作法 1 | 例外 | 把 `ABF_PLATFORM_PART` 設成 `9`、`0`、`main` 其中之一 | 執行 `bash tests/platform_test.sh` | 三種值都退出碼 1，訊息含 `must be 1 to 8, clock or all` | 自動：`platform/tests/test_platform_parts.py` |
| SS-18 | 作法 1（合法值寫法） | 功能 | 讀改完的 `tests/platform_test.sh` | 看合法值檢查 | 上限由變數 `PLATFORM_PARTS=8` 決定，`case` 裡沒有逐一列出 `1\|2\|3\|…\|8`，錯誤訊息的 8 從變數帶入 | 手動：閱卷者讀 diff |
| SS-05 | 失敗先行 SS-05；裁決 D7 | 功能 | 同上 | 對第 1 至 8 份，取出非點名的 REST 分片（那一行） | 每個 REST 分片的檔數 ≤ ceil(REST 檔總數 ÷ 8) + 1；REST 檔總數用當下實際收集到的數量計算，測試裡不寫死 10 或任何總檔數 | 自動：`platform/tests/test_platform_parts.py` |
| SS-19 | 失敗先行 SS-05 | 功能 | 同上 | 數每一份的分片行數（含 REST） | 每份至多 4 行 | 自動：`platform/tests/test_platform_parts.py` |
| SS-20 | 失敗先行 SS-05；作法 1.1 | 功能 | 同上 | 數每個點名分片（非 REST）那一行的檔案數 | 每一行至多 3 個檔 | 自動：`platform/tests/test_platform_parts.py` |
| SS-06 | 失敗先行 SS-06 | 功能 | 把 `platform/` 複製到暫存目錄（`ABF_PLATFORM_DIR`），再多放 16 個空的 `tests/test_zz_new_<i>.py` | 列出第 1 至 8 份 | 這 16 個新檔每份恰好得到其中兩個，且每個新檔只出現在一份裡 | 自動：`platform/tests/test_platform_parts.py` |
| SS-21 | 失敗先行 SS-06；作法 1.3 | 功能 | 同 SS-06 | 數八份各自的 REST 檔數 | 八份的 REST 檔數兩兩相差 ≤ 1 | 自動：`platform/tests/test_platform_parts.py` |
| SS-22 | 作法 1.3；受影響斷言第 1 項（`% 3` 改 `% 8`） | 功能 | 真實的測試目錄 | 把沒被點名、也不在時鐘的檔以 C 語系排序，逐一看它落在哪一份 | 第 i 個（從 0 起算）檔落在第 (i % 8) + 1 份，且只在那一份 | 自動：`platform/tests/test_platform_parts.py` |
| SS-23 | 作法 1.1（`test_launch_nextflow.py` 獨佔） | 功能 | 同上 | 找出含 `tests/test_launch_nextflow.py` 的那一行 | 那一行只有這一個檔（它的 setup 是一次真的 Nextflow 執行，不能再拆，只能獨佔一個 pytest 行程） | 自動：`platform/tests/test_platform_parts.py` |
| SS-24 | 作法 1.1；維護者原話第 3 句 | 功能 | ledger 已貼入作法 0 第 3 點的每檔秒數全文 | 對照 ledger 的每檔秒數與改完的點名分片 | 每檔 ≥ 20 秒者各自獨佔一行；舊的 `test_launch_e2e.py`、`test_station_fakeplatform.py`、`test_station_channel.py` 組合行已拆開；其餘多檔點名行合計都 ≤ 30 秒 | 手動：閱卷者讀 ledger 與 diff |
| SS-25 | 作法 1.2、1.4 | 功能 | ledger 有每份「點名秒數＋REST 估計」表 | 讀表與 diff | 重檔是最長者先分配到目前最輕的一份（同分取編號小者）；每份點名分片 ≤ 3 個；估算最大／最小 ≤ 1.4，做不到時 ledger 寫明只整行搬移過一次，沒有拆行、沒有改輪流規則 | 手動：閱卷者讀 ledger 與 diff |
| SS-27 | 作法 1「介面不變」 | 功能 | 把 `platform/` 複製到暫存目錄，只留點名檔加一個新檔（其餘 REST 檔刪掉） | 逐份列出第 1 至 8 份 | 輸出每行都是 `shard: <檔…>` 或 `alone: <檔>` 且檔名清單不為空；空的 REST 不印；該新檔在八份裡總共只出現一次 | 自動：`platform/tests/test_platform_parts.py` |

## US-B — 九個項目真的跑得到，啟動準備共用（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SS-07 | 失敗先行 SS-07；範圍（新增五支） | 功能 | 看 `tests/` 底下的檔 | 列出 `platform_shard_*_test.sh` | 恰好是 `platform_shard_2_test.sh` 至 `platform_shard_8_test.sh` 七支；沒有 `platform_shard_1_test.sh`，沒有 `platform_shard_9_test.sh` | 自動：`platform/tests/test_platform_parts.py` |
| SS-29 | 失敗先行 SS-07；作法 1 | 功能 | 同上 | 讀每支 `platform_shard_<n>_test.sh` 的有效碼（略過註解與空行） | 恰好三行：`HERE=…`、`export ABF_PLATFORM_PART=<n>`（n 與檔名編號一致，且檔內沒有別的編號）、`exec bash "$HERE/platform_test.sh" "$@"`；執行 `ABF_PLATFORM_LIST=1` 時，清單等於 `platform_test.sh` 在 `PART=<n>` 的清單 | 自動：`platform/tests/test_platform_parts.py` |
| SS-08 | 失敗先行 SS-08 | 功能 | 有 Java 與暖快取（沒有 Java 時本機跳過，CI 上不准跳過） | 九個項目各以 `ABF_PYTEST_ARGS="--collect-only -q"` 執行 | 每個項目都退出 0，輸出含 `platform tests: pytest exit 0` | 自動：`platform/tests/test_platform_parts.py` |
| SS-30 | 失敗先行 SS-08；完成標準 3 | 功能 | 同上 | 取各項目實際收集到的測試檔 | 各項目收集到的檔案集合恰好等於它自己的清單；九個項目合起來恰好等於全部測試檔，且沒有重複 | 自動：`platform/tests/test_platform_parts.py` |
| SS-09 | 失敗先行 SS-09 | 例外 | `CI=true`，PATH 裡沒有 Java | 九個項目各執行一次 | 全部退出非 0，輸出含 `FAIL (CI=true)`（CI 上不准默默跳過） | 自動：`platform/tests/test_platform_parts.py` |
| SS-50 | 作法 1「bootstrap 不動」；受影響斷言（`test_ps15_ps16`） | 功能 | 暖快取；第一個項目已做完預檢 | 另一個分片項目（如第 2 份）在 PATH 放一個永遠失敗的假 `curl` 後執行預檢 | 退出 0，沒有出現 `installing platform test dependencies`，假 `curl` 沒被呼叫（後面的項目不再付啟動準備的成本） | 自動：`platform/tests/test_platform_parts.py` |

## US-C — 隔離規則與 CI 分片（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SS-10 | 失敗先行 SS-10；作法 2 | 例外 | 沙盒內有 `platform_shard_8_test.sh`，且 `quarantine.txt` 想把它列入隔離 | 執行隔離檢查 | 退出 1，訊息含 `may not be quarantined` | 自動：`tests/run_all_retry_test.sh` |
| SS-32 | 失敗先行 SS-10；作法 2 | 例外 | 沙盒內造一支 `platform_shard_12_test.sh`，同樣想列入隔離 | 執行隔離檢查 | 退出 1，訊息含 `may not be quarantined`（規則是檔名樣式，不是點名八支） | 自動：`tests/run_all_retry_test.sh` |
| SS-33 | 失敗先行 SS-10 | 功能 | 沙盒內有 `platform_storage_doc_test.sh`、`platform_direction_docs_test.sh`（只讀文件） | 分別想把它們列入隔離 | 兩者仍可隔離，退出 0 | 自動：`tests/run_all_retry_test.sh` |
| SS-34 | 裁決 D8 | 功能 | 改完的 `tests/quarantine.txt` | 跑既有 PS-24（原樣不改） | PS-24 通過：第 12 行仍同時含 `platform_test.sh`、`platform_shard_2_test.sh`、`platform_shard_3_test.sh`、`platform_clock_test.sh` 四個字面 | 自動：`tests/run_all_retry_test.sh` |
| SS-35 | 作法 2；裁決 D8 | 功能 | 同上 | 讀 `tests/quarantine.txt` 第 12 行 | 第 12 行另外明說涵蓋所有 `platform_shard_<n>_test.sh`，且不再出現「four」或「四個」 | 自動：`tests/run_all_retry_test.sh` |
| SS-11 | 失敗先行 SS-11 | 功能 | 沙盒或真實專案目錄 | 執行 `bash tests/run_all.sh --list --allow-msys` | 清單含九個平台包裝檔：`platform_test.sh`、`platform_shard_2_test.sh` 至 `platform_shard_8_test.sh`、`platform_clock_test.sh` | 自動：`tests/run_all_shard_test.sh` |
| SS-36 | 失敗先行 SS-11；受影響斷言第 2 項（TC-002 改寫） | 功能 | 同上 | 對 `--shard 1/4` 至 `4/4` 各數平台包裝檔個數 | 四份的個數兩兩相差 ≤ 1，總和等於 `tests/` 底下實際的平台包裝檔數（九） | 自動：`tests/run_all_shard_test.sh` |
| SS-37 | 失敗先行 SS-11（反例）；受影響斷言第 2 項 | 例外 | 在沙盒造一份把全部包裝檔排在同一份的假清單 | 把新版 TC-002 的判斷套用到假清單 | 新版 TC-002 的判斷判紅（證明新斷言沒有被弱化成永遠為真） | 自動：`tests/run_all_shard_test.sh` |
| SS-49 | 受影響斷言（`run_all_shard_test.sh` 其餘項） | 功能 | 只有 TC-002 被改 | 跑 `bash tests/run_all_shard_test.sh` | TC-001（N=1 至 6 每個檔恰好一次）、TC-003、TC-004、TC-005、TC-006 原樣通過；檔尾印 `ALL OK` | 自動：`tests/run_all_shard_test.sh` |

## US-D — 上限不變、文件與註解不再過期（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SS-12 | 失敗先行 SS-12；維護者原話第 2 句 | 功能 | 改完的 `tests/run_all.sh` | 讀 `PER_TEST_TIMEOUT=` 那一行 | 值仍是 300；同行註解含 `only catches a hang`，不含 `~30s`，且註解裡沒有「數字加秒」的寫法 | 自動：`platform/tests/test_platform_parts.py` |
| SS-39 | 失敗先行 SS-12、SS-13 | 功能 | 同上 | 讀 `run_all.sh` 的使用說明與 `docs/TESTING.md` | 使用說明仍寫 `default 300`；`docs/TESTING.md` 仍含 `default 300` | 自動：`platform/tests/test_platform_parts.py` |
| SS-13 | 失敗先行 SS-13 | 功能 | 改完的文件 | 讀 `docs/TESTING.md` 與 `docs/PLATFORM.md` | 兩份都提到 `platform_shard_`，且 `platform_test.sh`、`platform_clock_test.sh` 也都還在 | 自動：`platform/tests/test_platform_parts.py` |
| SS-40 | 失敗先行 SS-13；作法 3 | 功能 | 同上 | 在兩份文件裡搜尋舊說法 | 找不到 `four platform entries`、`one of four entries`、`The machine part is the four`，也找不到「About 100 seconds」 | 自動：`platform/tests/test_platform_parts.py` |
| SS-14 | 失敗先行 SS-14 | 功能 | 改完的檔 | 讀 `tests/platform_test.sh`、`tests/platform_clock_test.sh` 與每支 `platform_shard_<n>_test.sh` 的註解 | 都不再出現 `Two run_all.sh entries`、`about half`、`four entries` | 自動：`platform/tests/test_platform_parts.py` |
| SS-41 | 作法 3 | 功能 | 看 diff | 對照 `docs/TESTING.md` 第 13、129、140、169 行與 `docs/PLATFORM.md` 第 732 至 735 行 | TESTING.md 四處改成列出 `platform_test.sh`、`platform_shard_<n>_test.sh`（n = 2 至 8）、`platform_clock_test.sh`；PLATFORM.md 的指令清單依序是第 1 份、第 n 份（n = 2…8）、時鐘，註解不寫個數 | 手動：閱卷者讀 diff |
| SS-42 | 範圍：`tests/run_all.sh` | 功能 | 看 diff | 比對 `tests/run_all.sh` 的改動 | 只有第 46 行與第 355 至 361 行的註解有改（不再寫「four」或個數）；第 174 行與第 363、364 行的樣式與其餘邏輯一個字都沒動 | 手動：閱卷者讀 diff |

## US-E — 既有的檢查仍然通過（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SS-43 | 受影響斷言第 3 項 | 功能 | 新增五支包裝檔之後 | 跑 `bash tests/run_all_count_test.sh` | TC-001（只看 `run_all.sh` 前 20 行）與 TC-004（`--list` 行數等於實際 `*.sh` 數，新增五支自動算進去）都通過 | 自動：`tests/run_all_count_test.sh` |
| SS-44 | 受影響斷言第 4 項 | 功能 | 同上 | 跑 `bash tests/constitution_scope_test.sh` | 通過（憲法裡的四個舊包裝檔名字仍在、檔案存在） | 自動：`tests/constitution_scope_test.sh` |
| SS-45 | 受影響斷言第 5 項 | 功能 | 只新增案例，不動既有斷言 | 跑 `bash tests/run_all_retry_test.sh` | 既有 TC-053、TC-089、PS-18、PS-19、PS-22 原樣通過 | 自動：`tests/run_all_retry_test.sh` |
| SS-46 | 受影響斷言第 6 項 | 功能 | 同上 | 跑 `test_wrapper.py`、`test_wrapper_nf2.py`、`test_scope.py`、`test_launch_static.py` | 全部通過 | 自動：`platform/tests/test_wrapper.py` 等四支 |
| SS-47 | 受影響斷言第 6 項 | 功能 | 看改完的 `tests/platform_test.sh` | 搜尋必須保留的字面與新增註解 | 檔內仍有 `PREFLIGHT_ONLY:-}" = "2"` 與 `${XDG_CACHE_HOME:-$HOME/.cache}`；新增的註解沒有 `/home/<名>/` 這類路徑 | 自動：`platform/tests/test_wrapper_nf2.py` 與 `platform/tests/test_scope.py` |
| SS-48 | 受影響斷言第 7 項 | 功能 | 同上 | 跑 `bash tests/platform_direction_docs_test.sh`、`bash tests/platform_storage_doc_test.sh` | 兩支都通過 | 自動：`tests/platform_direction_docs_test.sh`、`tests/platform_storage_doc_test.sh` |
| SS-51 | 受影響斷言第 1、2 項；閱卷通則（不得弱化既有測試） | 功能 | 看 `platform/tests/test_platform_parts.py`、`tests/run_all_shard_test.sh`、`tests/run_all_retry_test.sh` 與 base 的差異 | 逐處比對 | 被改的只有計畫點名的斷言，且只是把個數（3→8、四個→九個、`% 3`→`% 8`、`PART=4`→`PART=9/0/main`）改掉；沒有被刪、被跳過、被放寬的斷言；`run_all_retry_test.sh` 只新增案例；若動到計畫沒點名的案例（如 `test_ps33`），只限把迴圈範圍從三份擴到八份 | 手動：閱卷者讀 diff |

## US-F — 量測與完成標準（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SS-52 | 作法 0；完成標準 1、2 | 功能 | `specs/suite-speed/ledger.md` | 讀 ledger 的作法 0 部分 | 有 `nproc`、前後各一次 `uptime`、`git rev-parse HEAD`（與 v3 commit）；現況四個項目各自的牆鐘與分片秒數；每個測試檔秒數全文（`/tmp/per-file.txt`）；改前 `bash tests/run_all.sh --only platform_` 的 `ok  <n>s`／`TIMEOUT` 行 | 手動：閱卷者讀 ledger |
| SS-53 | 完成標準 1；維護者原話第 1、2 句 | 功能 | ledger 貼了改後整套 `bash tests/run_all.sh`（不帶 `--timeout`）的輸出 | 讀輸出 | 輸出裡沒有任何 `TIMEOUT` 行（這是硬條件，與機器負載無關，裁決 D5） | 手動：閱卷者讀 ledger |
| SS-54 | 完成標準 1；裁決 D5 | 功能 | 同上，且貼了當時的 `uptime`、`nproc` | 讀九個平台項目的 `ok  <n>s` | 九個都 ≤ 200 秒；若當時 1 分鐘負載 > 3，只要求數字被記錄、不因超過 200 秒判 FAIL | 手動：閱卷者讀 ledger |
| SS-55 | 完成標準 2；裁決 D5 | 功能 | ledger 有九個項目各自單獨執行的牆鐘，並註明當時負載 | 讀數字 | 八份數字份各自 ≤ 100 秒；負載 ≤ 2 時才算數，量不到乾淨時段時 ledger 寫明負載與原因，不因絕對秒數判 FAIL | 手動：閱卷者讀 ledger |
| SS-56 | 完成標準 2；裁決 D5 | 功能 | 同上 | 用八份數字份的單獨牆鐘算最大 ÷ 最小 | 比值 ≤ 1.5；做不到時 ledger 寫明原因與測得的數字（例如某個 95 秒 setup 的檔獨佔一份） | 手動：閱卷者讀 ledger |
| SS-57 | 完成標準 2；裁決 D1 | 功能 | 同上，含時鐘項目改前改後的單獨牆鐘 | 比對時鐘項目 | 改後不比改前慢超過 10%；若改後在忙碌機器上 > 200 秒，ledger 如實記錄（拆時鐘另開一片，不擋本片） | 手動：閱卷者讀 ledger |
| SS-58 | 完成標準 6 | 功能 | ledger 有改前的行數 | 比較 `bash tests/run_all.sh --list --allow-msys` 的行數 | 改後行數 = 改前行數 + 5 | 手動：閱卷者讀 ledger，並可在 WSL 重跑 |
| SS-59 | 完成標準 4 | 功能 | ledger 貼了輸出 | 讀 `bash tests/run_all.sh --only platform_` 與整套 `bash tests/run_all.sh` 的結果 | 兩趟都全綠（唯一允許的例外是已知環境紅 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 單獨紅，視同綠） | 手動：閱卷者讀 ledger |
| SS-60 | 作法 1「為什麼是 8」；裁決 D4、D9 | 功能 | ledger 有作法 0 的總秒數 | 比對實測總和與計畫預估（約 580 秒） | 差距在 30% 以內，份數維持 8；若差超過 30%，executor 應停下回報 BLOCKED（由 developer-agent 重開合約），不是自行改份數 | 手動：閱卷者讀 ledger |
| SS-61 | 完成標準 5 | 功能 | ledger 貼了 `git diff --stat origin/v3` | 對照計畫「範圍：檔案」 | 動到的檔只有清單內的檔、新增的五支包裝檔與 `specs/suite-speed/ledger.md`；`ABF_PLATFORM_LIST=1` 的輸出裡出現 `test_web_*` 的檔名不算違規 | 手動：閱卷者讀 diff |

## US-G — 不在範圍（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SS-62 | 範圍「不准動」車道外與程式碼；完成標準 5 | 不在範圍 | 看 `git diff origin/v3...HEAD` | 檢查這些路徑 | `web*.py`、`platform/abf_platform/web*.py`、`static/`、`DESIGN.md`、`PRODUCT.md`、`platform/tests/test_web_*`、`hooks/*`、`platform/abf_*` 零變動 | 手動：閱卷者讀 diff |
| SS-63 | 「不做」第 1 條；維護者原話第 2 句 | 不在範圍 | 看 diff | 搜尋 `--timeout` 的新增與 `PER_TEST_TIMEOUT` 的改動 | 沒有調高 `PER_TEST_TIMEOUT`，沒有在任何腳本新增 `--timeout`；上限仍只負責抓卡死 | 手動：閱卷者讀 diff |
| SS-64 | 範圍「任何平台測試的內容」；「不做」第 2 條 | 不在範圍 | 看 diff | 檢查 `platform/tests/` 底下 `test_platform_parts.py` 以外的檔 | 零變動：沒有加速、沒有刪、沒有改個別測試，也沒有新增跳過標記 | 手動：閱卷者讀 diff |
| SS-65 | 「不做」第 3 條 | 不在範圍 | 看 diff | 搜尋 `xdist`、依歷史秒數自動切分的外掛，以及依賴檔（如 `platform/constraints.txt`）的變動 | 沒有引入 `pytest-xdist` 或任何切分外掛，沒有新增依賴，也沒有新增要維護的秒數檔 | 手動：閱卷者讀 diff |
| SS-66 | 「不做」第 4 條；裁決 D1 | 不在範圍 | 看 diff | 檢查時鐘相關改動 | 沒有 `platform_clock2` 之類新項目；時鐘只由 `PART=clock` 選到那兩個檔，順序不變（SS-16）；`tests/platform_clock_test.sh` 只改第 5 至 8 行註解 | 手動：閱卷者讀 diff |
| SS-67 | 「不做」第 5 條 | 不在範圍 | 看 diff 新增的行 | 搜尋改過的文件與註解中的秒數寫法 | 新增或改寫的文件與註解裡沒有「數字加秒」的寫法（避免再過期） | 手動：閱卷者讀 diff |
| SS-68 | 作法 1「bootstrap 不動」 | 不在範圍 | 看 diff | 檢查 `tests/platform_test.sh` 的預檢、下載、快取部分，以及新增的檔 | 預檢、下載與快取邏輯沒動，沒有新增快取機制，沒有抽出共用腳本；新增的檔只有五支包裝檔與 ledger | 手動：閱卷者讀 diff |
| SS-69 | 「不做」第 6 條；裁決 D2、D3 | 不在範圍 | 看 diff | 檢查 `.github/`、`.specify/memory/constitution.md`、`spec.md`、`test-case*.md`、`docs/ROADMAP.md`、`.claude-plugin/plugin.json` | 全部零變動（`tests.yml` 第 37 行過期註解與憲法的「四個入口」字面留給 developer-agent 另案處理，本片不碰） | 手動：閱卷者讀 diff |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SS-70 | 原則 I 各條 Check（憲法第 46、51、195、213 行）：點名的檔由平台項目跑到 | 功能 | 真實測試目錄 | 列出 `PART=all`，數憲法點名的七個檔 | `test_actions_layer`、`test_human_channel`、`test_resume_entrypoints`、`test_keep_submissions`、`test_nextflow_e2e`、`test_secrets`、`test_confirm_page` 各恰好出現一次（拆成九個項目後檔沒掉、沒重複） | 自動：`platform/tests/test_platform_parts.py`（既有 PS-46 仍通過） |
| SS-71 | 原則 VI「不默默跳過」與安全網（平台項目的失敗不得被隔離名單放行） | 例外 | 沙盒內逐一造出真實存在的九個平台包裝檔名 | 每個都試著列入隔離 | 九個全部被拒（退出 1，訊息含 `may not be quarantined`），沒有任何一個可被隔離 | 自動：`tests/run_all_retry_test.sh` |

<!--
Rules for the writer:
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
