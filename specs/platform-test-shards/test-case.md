# 測試案例：把平台測試拆成四個 run_all 項目（三份分片＋時鐘）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
編號沿用計畫的 PS- 前綴（裁決二第 3 點）；PS-01…PS-31 與計畫「失敗先行測試」一一對應，PS-32 起是計畫其他段落（作法、完成標準、不做）明寫的事。
PS-11 依「裁決三」第 1 點的範圍；完成標準第 2 條依「裁決三」第 2 點。
-->

**規格**：`specs/platform-test-shards/plan.md`（本任務沒有 spec.md，計畫即規格；維護者原話在計畫「維護者原話」段）　**總覽**：`test-case-overview.md`

白話：以前整份平台測試擠在一個 `run_all.sh` 項目裡，在 GitHub 機器上跑超過 300 秒被判逾時（維護者原話）。這次把它分成四個項目（第 1、2、3 份加時鐘），每個項目遠低於 300 秒，並證明每個平台測試檔恰好被一個項目跑到，沒掉、沒重複。「清單」指 `ABF_PLATFORM_LIST=1` 時腳本印出的「這份要跑哪些檔」。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

「自動」的測試檔寫在 `platform/tests/test_platform_parts.py`（簡稱「parts 測試」）或 `tests/run_all_retry_test.sh`（簡稱「retry 測試」），每條在註解裡寫出自己的編號。

## US-A — 四份清單：不漏、不重、新檔有歸屬（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| PS-01 | 計畫 PS-01；維護者原話「no file dropped, none twice」 | 功能 | 真實樹 | 分別取 `ABF_PLATFORM_PART` 為 `1`、`2`、`3`、`clock` 的清單，全部檔合併後排序 | 恰好等於 `platform/tests/test_*.py` 全部（以 `tests/` 為前綴），一個不多一個不少 | 自動：parts 測試 |
| PS-02 | 計畫 PS-02 | 功能 | 同 PS-01 | 同 PS-01，取合併清單 | 沒有任何檔出現兩次（不重複數 ＝ 總數） | 自動：parts 測試 |
| PS-03 | 計畫 PS-03 | 功能 | 真實樹 | 取 `ABF_PLATFORM_PART=all` 的清單 | 檔案聯集等於四份的聯集，也等於全部檔 | 自動：parts 測試 |
| PS-04 | 計畫 PS-04 | 功能 | 真實樹 | 取 `ABF_PLATFORM_PART=clock` 的清單；再看第 1、2、3 份的所有分片行 | 時鐘清單恰為「單獨跑 `tests/test_station_e2e.py`，再單獨跑 `tests/test_nextflow_e2e.py`」，順序不變；這兩檔不在第 1、2、3 份的任何一行 | 自動：parts 測試 |
| PS-05 | 計畫 PS-05 | 功能 | 真實樹 | 取第 1、2、3 份清單 | 三份都非空，且每一行的種類都是 `shard`（沒有 `alone`） | 自動：parts 測試 |
| PS-06 | 計畫 PS-06 | 例外 | 真實樹 | 把四份清單裡每個路徑拿去磁碟找 | 每個路徑都是存在的檔；點名的檔被刪或改名時，這條就紅，而不是等到 pytest 才報找不到 | 自動：parts 測試 |
| PS-07 | 計畫 PS-07；作法 2「預設 `1`」 | 功能 | 不設 `ABF_PLATFORM_PART` | 取清單 | 與 `ABF_PLATFORM_PART=1` 的清單完全相同 | 自動：parts 測試 |
| PS-08 | 計畫 PS-08；作法 2 | 例外 | 無 | 分別用 `ABF_PLATFORM_PART=main` 與 `ABF_PLATFORM_PART=4` 執行 `tests/platform_test.sh` | 兩者都退出 1，輸出含 `must be 1, 2, 3, clock or all`（舊值 `main` 不再接受，也不存在第 4 份） | 自動：parts 測試 |
| PS-09 | 計畫 PS-09；裁決 5 | 功能 | 把 `platform/` 複製到暫存目錄（`ABF_PLATFORM_DIR` 指過去），`tests/` 多放 7 個空的 `test_zz_new_<i>.py` | 取第 1、2、3 份清單 | 這 7 個新檔在三份中各恰出現一次；三份各自「其餘檔案」（不在點名清單、也不是時鐘檔者）的數量兩兩相差不超過 1 | 自動：parts 測試 |
| PS-10 | 計畫 PS-10 | 功能 | 真實樹 | 看第 1、2、3 份每個點名的分片行 | 沒有任何一行含時鐘兩檔（防止有人把時鐘檔又寫回分片） | 自動：parts 測試 |
| PS-11 | 計畫 PS-11（依裁決三第 1 點） | 功能 | 真實樹 | 掃 `tests/*.sh` 中「行首（可有空白）是 `export ABF_PLATFORM_PART=` 或 `ABF_PLATFORM_PART=` 的賦值行」所在的檔，排除 `tests/run_all_retry_test.sh` 與 `tests/platform_test.sh`，註解行不算；再讀 `tests/run_all.sh` | 掃到的每個檔，檔名都是 `platform_clock_test.sh` 或符合 `platform_shard_<n>_test.sh`（現在是時鐘與兩支分片腳本）；`run_all.sh` 全文含 `platform_shard_*_test.sh`。日後有人加了新分片腳本卻忘了改隔離規則，這條就紅 | 自動：parts 測試 |
| PS-12 | 計畫 PS-12 | 功能 | 無 | 執行 `bash tests/run_all.sh --list --allow-msys` | 輸出含 `platform_test.sh`、`platform_shard_2_test.sh`、`platform_shard_3_test.sh`、`platform_clock_test.sh`，不含 `run_all.sh`；這四個名字都以 `_test.sh` 結尾 | 自動：parts 測試 |
| PS-32 | 作法 2「其餘檔案不再全進最後一個分片」 | 功能 | 同 PS-09 的暫存目錄，另有真實樹 | 把「不在點名清單、也不是時鐘檔」的 `tests/test_*.py` 以 `LC_ALL=C sort` 排序，第 i 個（從 0 起）看它在哪一份 | 第 i 個檔在第 `(i mod 3)+1` 份，且只在那一份 | 自動：parts 測試 |
| PS-33 | 作法 2「空的 `REST_n` 不印」 | 功能 | 暫存目錄裡刪掉所有「其餘檔案」，只留點名檔、時鐘檔與 1 個新檔 `test_zz_only.py` | 取第 1、2、3 份清單 | 新檔恰出現在一份；另外兩份沒有「檔案清單為空」的 `shard` 行 | 自動：parts 測試 |
| PS-34 | 作法 2「`ABF_PLATFORM_LIST=1` 輸出格式不變」 | 功能 | 真實樹 | 對四個進入點（`platform_test.sh`、兩支分片腳本、時鐘腳本）各取清單 | 每一行都是 `shard: <檔…>` 或 `alone: <檔>`，退出 0，檔名都以 `tests/` 開頭（`test_platform_parts.py` 的解析函式不用改就能讀） | 自動：parts 測試 |
| PS-35 | 作法 2「兩支新腳本與時鐘腳本同一個形狀」 | 功能 | 兩支新腳本 `tests/platform_shard_2_test.sh`、`tests/platform_shard_3_test.sh` | 讀檔，去掉註解與空行 | 各恰三行有效碼：`HERE=…`、`export ABF_PLATFORM_PART=2`（第 3 份是 `=3`）、`exec bash "$HERE/platform_test.sh" "$@"`；檔頭註解說明「不是第二份拷貝，只選份數」；執行 `ABF_PLATFORM_LIST=1` 時，`platform_shard_2_test.sh` 印出的清單等於 `ABF_PLATFORM_PART=2` 的清單，第 3 份同理 | 自動：parts 測試 |
| PS-36 | 作法 2（`main` 不再接受）；作法 5（註解改寫成新結構） | 功能 | 無 | 在 `tests/`、`docs/` 底下（不含 `specs/`）搜 `ABF_PLATFORM_PART=main` | 沒有任何殘留（說明文字不能再把 `main` 當有效值） | 自動：parts 測試 |

## US-B — 四個項目真的跑得到、共用同一份啟動準備（優先度 P1）

需要 Java 與暖快取，同 `test_wrapper.py` 的 `warm` fixture；沒有 Java 時該 fixture 會 skip，CI 上不准 skip 的規則照舊。閱卷以 executor 在 WSL／Linux 貼進 ledger 的實跑輸出為準。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| PS-13 | 計畫 PS-13 | 功能 | 暖快取、有 Java | 四個項目各以 `ABF_PYTEST_ARGS="--collect-only -q"` 執行 | 四個都退出 0，輸出含 `platform tests: pytest exit 0`；每個項目實際收集到的測試檔集合，恰等於它自己的清單 | 自動：parts 測試 |
| PS-14 | 計畫 PS-14；維護者原話「every platform/tests/test_*.py is covered by exactly one shard」 | 功能 | 同 PS-13 | 把 PS-13 四個項目收集到的檔案合併 | 聯集恰等於 `platform/tests/test_*.py` 全部，沒有檔出現在兩個項目（這是「實際跑」層級的覆蓋；PS-01 是清單層級） | 自動：parts 測試 |
| PS-15 | 計畫 PS-15；維護者原話「keep the venv/Nextflow bootstrap shared or cached」 | 功能 | 暖快取 | 連跑兩次預檢（`ABF_PLATFORM_PREFLIGHT_ONLY=2`）：第一次 `platform_test.sh`、第二次 `platform_shard_2_test.sh` | 第二次的輸出不含 `installing platform test dependencies`（沒有重新安裝） | 自動：parts 測試 |
| PS-16 | 計畫 PS-16 | 功能 | 同 PS-15，PATH 最前面放一支會記錄呼叫的假 `curl` | 同 PS-15 的第二次預檢 | 記錄檔是空的（命中快取，沒有重新下載） | 自動：parts 測試 |
| PS-17 | 計畫 PS-17；作法 2（CI 規則照舊） | 例外 | `CI=true`，PATH 裡沒有 Java | 四個項目（`platform_test.sh`、兩支分片腳本、時鐘腳本）各執行一次 | 四個全都退出非 0，輸出含 `FAIL (CI=true)`（CI 上沒有 Java 是失敗，不是跳過） | 自動：parts 測試 |

## US-C — 四個平台項目都不准進隔離名單（優先度 P1）

隔離名單＝`tests/quarantine.txt`，登記後某測試檔失敗時可被放行；平台測試包著整份平台 pytest，登記它等於放過任何平台測試失敗，所以必須拒絕。沙盒＝測試自己造的暫存樹。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| PS-18 | 計畫 PS-18；維護者原話「the new shard names must be rejected the same way」 | 例外 | 沙盒存在 `tests/platform_shard_2_test.sh`，名單第 1 行寫 `tests/platform_shard_2_test.sh #12 <今天+3>` | 執行 `run_all.sh` | 退出 1；訊息含 `quarantine: tests/quarantine.txt:1:` 與 `platform_shard_2_test.sh` | 自動：retry 測試 |
| PS-19 | 計畫 PS-19 | 例外 | 同 PS-18，檔名改 `platform_shard_3_test.sh` | 同 PS-18 | 同 PS-18（退出 1，訊息含行號與 `platform_shard_3_test.sh`） | 自動：retry 測試 |
| PS-20 | 計畫 PS-20（規則是樣式，不是兩個名字） | 例外 | 沙盒內另建一支假想的 `platform_shard_9_test.sh`，名單登記它 | 同 PS-18 | 同樣被拒（退出 1，訊息含行號與檔名） | 自動：retry 測試 |
| PS-44 | 作法 4「訊息沿用第 161 行的句型」 | 例外 | 同 PS-18 | 看被拒的訊息 | 訊息句型為 `<檔名> may not be quarantined: it wraps the platform pytest suite, so quarantining it would let any platform test failure through` | 自動：retry 測試 |
| PS-21 | 計畫 PS-21；作法 4「不用 `platform_*_test.sh`」 | 功能 | 沙盒內建 `platform_storage_doc_test.sh` 與 `platform_direction_docs_test.sh`（只讀文件的檢查），各自登記在名單 | 執行 `run_all.sh` | 退出 0（兩支文件檢查仍可被隔離，沒被誤傷） | 自動：retry 測試 |
| PS-22 | 計畫 PS-22 | 例外 | 沙盒內建 `platform_test.sh`、`platform_clock_test.sh`，各自登記在名單 | 執行 `run_all.sh` | 兩者仍被拒（既有 TC-053、TC-089 原樣綠、不改動） | 自動：retry 測試 |
| PS-23 | 計畫 PS-23 | 功能 | 真實樹 | `bash tests/run_all.sh --check-quarantine` | 退出 0（既有 TC-052 原樣綠） | 自動：retry 測試 |
| PS-24 | 計畫 PS-24；作法 4 末句 | 功能 | 真實樹 | 對 `tests/quarantine.txt` 第 12 行的註解各 `grep -F` 四個名字 | 四個名字都在：`platform_test.sh`、`platform_shard_2_test.sh`、`platform_shard_3_test.sh`、`platform_clock_test.sh`；並說明只有這四支包平台 pytest | 自動：retry 測試 |
| PS-25 | 計畫 PS-25；作法 4（規則依檔名，不依內容） | 不在範圍 | 沙盒內檔名為 `platform_x_test.sh`，內容含 `ABF_PLATFORM_PART=`，登記在名單 | 執行 `run_all.sh` | **不**被拒（退出 0）：隔離規則沒有悄悄變成內容掃描；防呆靠命名規則加 PS-11 | 自動：retry 測試 |

## US-D — 上限不變、文件與註解不再過期（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| PS-26 | 計畫 PS-26；作法 5 | 功能 | 真實樹 | 讀 `tests/run_all.sh` 的 `PER_TEST_TIMEOUT` 行 | 值仍是 300（沒調高）；註解含 `only catches a hang`；不含 `~30s` | 自動：parts 測試 |
| PS-40 | 作法 5「不寫任何秒數」；裁決 8 | 功能 | 同 PS-26 | 檢查 `PER_TEST_TIMEOUT` 那行的註解 | 註解沒有任何「數字＋秒」的寫法（如 `30s`、`300 s`、`~30 seconds`），避免再過期 | 自動：parts 測試 |
| PS-27 | 計畫 PS-27 | 功能 | 真實樹 | 讀 `docs/TESTING.md` | 不含 `About 100 seconds`；含四個項目的檔名（`platform_test.sh`、`platform_shard_2_test.sh`、`platform_shard_3_test.sh`、`platform_clock_test.sh`） | 自動：parts 測試 |
| PS-43 | 作法 5（TESTING.md 第 13 行） | 功能 | 同 PS-27 | 讀 `docs/TESTING.md` 第 13 行附近 | 該句改為 `Several minutes, mostly the four platform entries (…)；one verdict and a non-zero exit if anything fails.`，四個檔名在括號內 | 自動：parts 測試 |
| PS-28 | 計畫 PS-28 | 功能 | 同 PS-27 | 讀 `docs/TESTING.md` | 仍含 `default 300`（第 16 行沒被誤刪） | 自動：parts 測試 |
| PS-29 | 計畫 PS-29；作法 5 | 功能 | 同 PS-27 | 讀 `docs/TESTING.md` | 不再有字串 ``The machine part is `tests/platform_test.sh` ``；改成「The machine part is the four platform entries (…)」，其後原句保留 | 自動：parts 測試 |
| PS-30 | 計畫 PS-30 | 功能 | 真實樹 | 讀 `docs/PLATFORM.md` | 含四個項目的檔名；不含 `every test file but two` | 自動：parts 測試 |
| PS-41 | 作法 5（PLATFORM.md 末句） | 功能 | 同 PS-30 | 讀 `docs/PLATFORM.md` 的 Tests 小節 | 指令區是四行（第 1、2、3 份、時鐘）；說明段加了一句，說明 `ABF_PLATFORM_PART=all` 在同一個項目跑全部 | 自動：parts 測試 |
| PS-31 | 計畫 PS-31 | 功能 | 真實樹 | 讀 `tests/platform_test.sh`、`tests/platform_shard_2_test.sh`、`tests/platform_shard_3_test.sh`、`tests/platform_clock_test.sh` | 四個檔的註解都不再出現 `Two run_all.sh entries` 與 `about half` | 自動：parts 測試 |
| PS-42 | 作法 5（TESTING.md 只動指定行） | 不在範圍 | 比對 base 與 HEAD | 看 `docs/TESTING.md` 的 diff | 只改第 13、129、140、169 行；第 16 行與各功能的歷史驗收步驟（第 133、137、159、161、177 行）一個字沒動 | 手動：閱卷者看 diff（通例） |

## US-E — 既有的檢查與必須保留的字面（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| PS-37 | 作法 3「必須保留的字面」 | 功能 | 改完後的 `tests/platform_test.sh` | 讀全文 | 仍含 `PREFLIGHT_ONLY:-}" = "2"` 與 `${XDG_CACHE_HOME:-$HOME/.cache}`；新增的註解不含 `/home/<名>/` 這類路徑；`test_wrapper_nf2.py` 與 `test_scope.py` 照原樣綠 | 自動：`platform/tests/test_wrapper_nf2.py`、`platform/tests/test_scope.py`（既有） |
| PS-38 | 受影響的既有斷言 5–10 | 功能 | 改完後 | 跑：parts 測試的 `test_tcf3_05`、`test_tcf3_04`；`tests/run_all_count_test.sh`；retry 測試的 TC-053、TC-089；`test_wrapper.py`、`test_launch_static.py`；`tests/run_all_test.sh` | 全綠，且這些既有斷言沒被放寬、刪除或改期望值（retry 測試只新增 PS- 案例，不動既有斷言） | 自動：上述既有檔案 |
| PS-39 | 範圍「不准動」；作法 5 | 不在範圍 | 比對 base 與 HEAD | 看 `tests/run_all.sh` 的 diff | 第 1–20 行一個字沒動；除第 46 行註解與第 160–161 行隔離規則外沒有其他變動 | 手動：閱卷者看 diff（通例） |

## US-F — 量測與完成標準（優先度 P1）

「帳本」＝`specs/platform-test-shards/ledger.md`。以下由閱卷者讀帳本，並在 WSL／Linux 自己重跑核對（裁決三第 4 點、計畫通例）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| PS-50 | 完成標準 1；作法 0；維護者原話「measure the slowest platform test files/tests」 | 功能 | 改任何檔之前 | 帳本內找「改前」記錄 | 有：前 30 慢測試、每個分片自己的秒數、`time bash tests/platform_test.sh` 與 `time bash tests/platform_clock_test.sh` 的牆鐘時間，並註明量測時的 `v3` commit | 手動：閱卷者核對帳本（通例） |
| PS-51 | 完成標準 1；作法 3 | 功能 | 改完後，WSL／Linux、暖快取 | 帳本內找「改後」記錄 | 有：四個項目各自 `time` 的牆鐘時間，以及 `time ABF_PLATFORM_PREFLIGHT_ONLY=2 bash tests/platform_test.sh` 的秒數 | 手動：閱卷者核對帳本並重跑 |
| PS-52 | 完成標準 2（依裁決三第 2 點） | 功能 | 同 PS-51 | 比對帳本中三份各自的牆鐘與改前 `platform_test.sh` 牆鐘 | 第 1、2、3 份每一份都 ≤ 改前 `platform_test.sh` 牆鐘的 45% | 手動：閱卷者核對帳本並重跑 |
| PS-53 | 完成標準 2（依裁決三第 2 點） | 功能 | 同 PS-51 | 比對時鐘項目改前與改後的牆鐘 | 時鐘項目不比改前慢超過 10% | 手動：閱卷者核對帳本並重跑 |
| PS-54 | 作法 2「調整規則」；完成標準 2 | 功能 | 同 PS-51 | 算三份牆鐘的最大／最小 | ≤ 1.5；做不到時，帳本寫明原因與測得的數字（不再硬調） | 手動：閱卷者核對帳本 |
| PS-55 | 作法 3 | 功能 | 同 PS-51 | 看暖預檢秒數 | ≤ 20 秒就接受；超過則帳本只記錄、不優化，並列入「待 developer-agent 裁決」第 3 項 | 手動：閱卷者核對帳本 |
| PS-56 | 完成標準 4 | 功能 | 改完後 | 帳本內找「受影響的既有斷言」第 5–10 項 | 每一項都貼出綠的輸出 | 手動：閱卷者核對帳本並重跑 |
| PS-58 | 完成標準 6 | 功能 | WSL／Linux 或加 `--allow-msys` | 比對改前改後的 `bash tests/run_all.sh --list --allow-msys` 行數 | 改後比改前剛好多 2 行（兩支新分片腳本） | 手動：閱卷者核對帳本並重跑 |
| PS-59 | 完成標準 3 | 功能 | 改完後，WSL／Linux | `bash tests/run_all.sh --only platform`，再跑 `bash tests/run_all.sh` | 兩者全綠；四個平台項目都出現在輸出且通過；沒有 `E2E SKIPPED` 行 | 手動：閱卷者在 WSL 重跑並核對帳本 |

## US-G — 不在範圍：這次不做的事確實沒做（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| PS-57 | 完成標準 5；範圍「不准動」；不做第 2 點 | 不在範圍 | 比對 base（`b086b6d`）與 HEAD | `git diff --stat` | 變動的檔只有計畫「範圍：檔案」列的 10 個，加上 `specs/platform-test-shards/ledger.md`；`hooks/*`、`.github/*`、`platform/abf_*`、`platform/tests/` 底下除 `test_platform_parts.py` 以外的檔，都沒有任何變動（平台測試內容沒改） | 手動：閱卷者看 diff（通例） |
| PS-60 | 不做第 1 點；作法 5 末句；裁決二第 1 點 | 不在範圍 | 同 PS-57 | 看 `.github/workflows/tests.yml` 的 diff | 沒有變動（`--timeout 900` 仍在；拿掉它是合併後 developer-agent 的事） | 手動：閱卷者看 diff（通例） |
| PS-61 | 不做第 6 點；裁決 2 | 不在範圍 | 改完後的 `tests/` | 列出 `tests/platform_shard_*_test.sh` | 恰兩支（`_2_`、`_3_`），沒有第 4 份，也沒有 `platform_shard_4_test.sh` | 自動：parts 測試 |
| PS-62 | 不做第 3 點 | 不在範圍 | 同 PS-57 | 看 diff 中 `tests/platform_test.sh` 與依賴檔 | 沒有引入 `pytest-xdist` 或其他平行化外掛（沒有 `xdist`、沒有 pytest 的 `-n` 參數）；平行仍是「每個分片一個 pytest 行程」 | 手動：閱卷者看 diff（通例） |
| PS-63 | 不做第 4 點；作法 3 | 不在範圍 | 同 PS-57 | 看 diff 的新增檔與 `tests/platform_test.sh` | `tests/` 的新增檔只有兩支分片腳本，沒有抽出共用 bootstrap 腳本；沒有新增快取機制（venv 與下載仍在 `platform_test.sh` 自己的 `CACHE`／`VENV` 路徑） | 手動：閱卷者看 diff（通例） |

## 憲法與安全網

拆分後，憲法裡寫「由 `tests/platform_test.sh` 跑」的檢查，有些檔改由別的項目跑（裁決三第 3 點：憲法本任務不改，另案修條文）；隔離名單屬於「失敗不得被放行」的防線。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| PS-46 | 憲法 I 各條 Check、憑證條 Check 所點名的平台測試檔（`test_actions_layer.py`、`test_human_channel.py`、`test_resume_entrypoints.py`、`test_keep_submissions.py`、`test_nextflow_e2e.py`、`test_secrets.py`，加上 `test_confirm_page.py`） | 功能 | 真實樹 | 取 `ABF_PLATFORM_PART=all` 的清單，找憲法點名的每個平台測試檔 | 每個檔都出現在清單裡，且恰一次（檢查沒有因為拆分而掉出所有項目） | 自動：parts 測試 |
| PS-47 | 開發流程「不得動憲法」；裁決三第 3 點 | 不在範圍 | 比對 base 與 HEAD | `git diff -- .specify/memory/constitution.md` | 為空（憲法一字未改；文字不精確之處另案處理） | 手動：閱卷者看 diff（通例） |
