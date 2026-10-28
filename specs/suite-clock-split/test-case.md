# 測試案例：時鐘測試項目拆成兩個（每項 ≤180 秒）＋更正 suite-speed 帳本一句

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Write every row so that it can be
judged without reading code: what is set up, what the person or the system does,
what must be seen. No internal jargon without a one-line explanation.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/suite-clock-split/plan.md`（A 級任務，沒有 spec.md；計畫與其「裁決」段即規格）　**總覽**：`test-case-overview.md`

編號用計畫的 `SC-` 前綴（避免撞到既有的 `SS-`／`PS-`／`TC-`）。計畫原有 SC-01…SC-09、SC-12…SC-14；SC-10、SC-11 計畫漏編，由本合約補上；SC-15 起是把計畫的完成標準、範圍、「不做」逐條對成案例。

白話名詞：
- **項目**＝`bash tests/run_all.sh` 裡跑的一個 `*.sh` 檔，一次只跑一個、各有 300 秒上限。
- **時鐘項目**＝會盯著心跳（兩秒一次）與重建結束時間的那兩個測試檔，所以必須獨佔機器：`tests/test_station_e2e.py`（舊名 `clock` 項目保留）與 `tests/test_nextflow_e2e.py`（新的 `clock2`）。
- **收集**＝讓 pytest 只列出會跑哪些測試、不真的跑（`--collect-only -q`）。
- **手動**在本任務＝閱卷者照該列寫的指令在 WSL 重跑、或讀 diff／ledger 核對，不是 pytest 能斷言的事。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 拆分前後，跑的測試完全一樣（優先度 P1）

> 對應計畫「目標」：「測試一個都不刪、不跳過、不弱化，整體跑的測試集合前後完全相同」。這是本任務最重要的一組。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SC-01 | 目標；完成標準 3；計畫 SC-01 | 功能 | 改後的程式；沿用 `warm` 夾具（沒有 Java 時本機跳過、CI 上不准跳過） | 以 `ABF_PYTEST_ARGS="--collect-only -q"` 分別執行十個項目（八份數字分片、`clock`、`clock2`），取各自收集到的測試編號 | (a) 同一個測試編號不會出現在兩個項目；(b) 十個項目的聯集，等於對 `platform/tests` 整個目錄一次 `pytest --collect-only -q` 的測試編號集合（同環境同 commit）；(c) 每個項目收集到的檔案集合，恰等於它的 `ABF_PLATFORM_LIST=1` 清單 | 自動：`platform/tests/test_platform_parts.py` |
| SC-02 | 目標；計畫 SC-02 | 功能 | 改後的程式 | 列出 `ABF_PLATFORM_PART=clock` 與 `clock2` 的檔案清單，並與八份數字分片比對 | `clock` ∪ `clock2` 的檔案恰為 `tests/test_station_e2e.py` 與 `tests/test_nextflow_e2e.py` 兩個；它們與八份數字分片的任何一份都不重疊 | 自動：`platform/tests/test_platform_parts.py` |
| SC-15 | 目標；計畫 SC-02 | 功能 | 改後的程式 | 取十份清單（`1`～`8`、`clock`、`clock2`）的檔案聯集並排序；另取 `ABF_PLATFORM_PART=all` 的聯集 | 兩者都恰等於 `platform/tests/test_*.py` 磁碟上全部檔案：沒有檔案掉出所有項目，也沒有檔案出現兩次 | 自動：`platform/tests/test_platform_parts.py` |
| SC-16 | 目標；不做「不動八份數字分片」；計畫 SC-02 | 功能 | 作法 0 已把改前八份清單存進 ledger | 讀 `git diff origin/v3 -- tests/platform_test.sh`，並用 `ABF_PLATFORM_LIST=1` 對 `PART=1`～`8` 各印一次，與 ledger 裡改前的清單比對 | `SHARDS_1`…`SHARDS_8`、`REST_1`…`REST_8` 與輪流分配規則的程式行零變動；八份清單與改前逐字相同 | 手動：閱卷者看 diff 與 ledger，在 WSL 重印清單 |
| SC-03 | 計畫 SC-03 | 功能 | 沒設 `ABF_PLATFORM_PART` | 列出清單，再與 `PART=1` 的清單比 | 兩者相同；清單裡每個路徑在磁碟上都存在 | 自動：`platform/tests/test_platform_parts.py` |
| SC-26 | 完成標準 3 | 功能 | 改前的「前」行數與 sha256 已在 ledger（作法 0 第 2 點） | 改後在同一環境、同一指令（`ABF_PLATFORM_PART=all ABF_PYTEST_ARGS="--collect-only -q" bash tests/platform_test.sh`，取含 `::` 的行排序）算行數與 sha256 | 「後」的行數與 sha256 與 ledger 的「前」完全相同 | 手動：閱卷者在 WSL 重跑並與 ledger 比 |
| SC-11 | 目標；第 6 節「不改但必須仍然通過」；計畫 SC-11（補） | 功能 | 改後的程式 | 執行 `tests/run_all_retry_test.sh` 的 TC-089、PS-22、PS-24；`tests/run_all_count_test.sh`；`tests/constitution_scope_test.sh`；`platform/tests/test_wrapper.py`、`test_wrapper_nf2.py`、`test_scope.py`；`test_platform_parts.py` 裡談 REST 輪流分配、重檔、`ABF_PLATFORM_DIR` 沙盒新增空檔、`PER_TEST_TIMEOUT` 仍是 300 的案例（SS-05、SS-06、SS-12 等） | 全部通過，輸出貼在 ledger；沒有任何一條被刪、被跳過 | 自動：上述各檔 |
| SC-28 | 第 6 節「受影響的既有斷言」；驗收「弱化」檢查 | 功能 | 改後的程式與 `origin/v3` | 逐檔比較 `platform/tests/test_platform_parts.py`、`tests/run_all_shard_test.sh`、`tests/run_all_retry_test.sh` 與 base 的 diff | 只有計畫第 6 節點名的改動：`PARTS` 加 `clock2`、`clock` 清單改成單檔且新增 `clock2` 單檔、訊息子字串改為 `must be 1 to 8, clock, clock2 or all`、新增 `PART=clock3`／`clock_2` 案例、檔名樣式與包裝檔數 9→10、名單加 `platform_clock_2_test.sh`；`run_all_retry_test.sh` 只新增案例與名字；沒有任何斷言被刪除、放寬、跳過，也沒有為配合新輸出而改期望值（「兩個檔不在任何數字份」那段原樣保留；`PART=9`、`0`、`main` 照舊退出 1；TC-002 的反例原樣保留） | 手動：閱卷者看 `git diff origin/v3...HEAD` |

## User Story 2 — 時鐘分成兩個項目，且 run_all.sh 認得新項目（優先度 P1）

> 對應計畫「作法 1」「作法 2」：`clock` 只剩 `test_station_e2e.py`，新的 `clock2` 只有 `test_nextflow_e2e.py`，順序不變、各自獨佔。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SC-04 | 作法 1；計畫 SC-04 | 功能 | 改後的程式 | 列出 `ABF_PLATFORM_PART=clock` 與 `ABF_PLATFORM_PART=clock2` 的清單 | `clock` 恰為一行 `alone: tests/test_station_e2e.py`；`clock2` 恰為一行 `alone: tests/test_nextflow_e2e.py`；兩者都沒有 `shard:` 行；清單格式（`shard: <檔…>`／`alone: <檔>`）與改前相同 | 自動：`platform/tests/test_platform_parts.py` |
| SC-17 | 作法 1；計畫 SC-04 | 功能 | 改後的程式 | 列出 `ABF_PLATFORM_PART=all` 的清單 | `alone` 行依序為 `tests/test_station_e2e.py`、`tests/test_nextflow_e2e.py`，且排在全部 `shard:` 行之後；兩個檔都不在任何 `shard:` 行 | 自動：`platform/tests/test_platform_parts.py` |
| SC-10 | 作法 1「執行迴圈」；環境事實（不准與其他 pytest 行程同時跑）；計畫 SC-10（補） | 功能 | 改後的 `tests/platform_test.sh` | 讀執行迴圈（原第 404～415 行）：`clock`／`clock2` 各自的路徑，以及 `all` 的路徑 | `clock` 與 `clock2` 都不跑數字分片；`clock` 只啟動 `LAST_1`、`clock2` 只啟動 `LAST_2`；`all` 先跑完並等完所有數字分片，再一個檔一個 pytest 行程、啟動後等它結束才啟動下一個；沒有任何路徑讓時鐘檔與別的 pytest 行程同時跑 | 手動：閱卷者讀 `tests/platform_test.sh` 迴圈；SC-01(c) 同時佐證 `clock`／`clock2` 沒夾帶別的檔 |
| SC-18 | 作法 1「新包裝檔」；計畫 SC-05 | 功能 | 改後的程式 | 列出 `tests/` 底下的時鐘包裝檔，讀兩支的內容 | 恰有 `platform_clock_test.sh` 與 `platform_clock_2_test.sh` 兩支；後者內含且只含 `ABF_PLATFORM_PART=clock2` 並 `exec bash "$HERE/platform_test.sh" "$@"`；前者內含且只含 `ABF_PLATFORM_PART=clock` | 自動：`platform/tests/test_platform_parts.py` |
| SC-19 | 作法「範圍」`quarantine.txt`；計畫 SC-06 | 功能 | 改後的程式 | 讀 `tests/quarantine.txt` 第 12 行，並跑 `run_all_retry_test.sh` 的 PS-24 | 第 12 行同時含 `platform_clock_2_test.sh` 與原有字面 `platform_test.sh`、`platform_shard_2_test.sh`、`platform_shard_3_test.sh`、`platform_clock_test.sh`、`platform_shard_<n>_test.sh`；PS-24 仍通過；改的只有這行註解 | 自動：`tests/run_all_retry_test.sh` |
| SC-07 | 作法 2；計畫 SC-07 | 功能 | 改後的程式 | 執行 `bash tests/run_all.sh --list --allow-msys`，再看 `--shard I/4`（I＝1～4）各份 | 清單含十個平台包裝檔：`platform_test.sh`、`platform_shard_2…8_test.sh`、`platform_clock_test.sh`、`platform_clock_2_test.sh`；四份的包裝檔數兩兩相差 ≤ 1 且總和為十 | 自動：`tests/run_all_shard_test.sh` |
| SC-20 | 作法 2；計畫 SC-07 | 功能 | 沙盒裡只留這十個包裝檔加 4 個普通檔 | 執行 `run_all.sh --shard I/4` 的分配 | `platform_clock_2_test.sh` 與其他包裝檔一樣權重 40：任何普通檔都不會先於它被分配 | 自動：`tests/run_all_shard_test.sh` |
| SC-24 | 完成標準 8 | 功能 | 作法 0 已記錄改前 `--list` 行數 | 改後執行 `bash tests/run_all.sh --list --allow-msys \| wc -l` | 行數正好比改前多 1 | 手動：閱卷者在 WSL 重跑並與 ledger 比；`run_all_count_test.sh`（TC-004）另外自動佐證行數等於實際 `*.sh` 數 |
| SC-05 | 作法 1「合法值」；計畫 SC-05 | 例外 | 改後的程式 | 分別以 `ABF_PLATFORM_PART` 設 `9`、`0`、`main`、`clock3`、`clock_2` 執行 `bash tests/platform_test.sh` | 每個都退出 1，訊息含 `FAIL: ABF_PLATFORM_PART must be 1 to 8, clock, clock2 or all, not '<輸入值>'`；而 `1`～`8`、`clock`、`clock2`、`all` 都被接受 | 自動：`platform/tests/test_platform_parts.py` |
| SC-06 | 作法 2；計畫 SC-06 | 例外 | `tests/quarantine.txt`（或沙盒裡的同名檔）列了 `platform_clock_2_test.sh`（以及沙盒內造的同名檔） | 執行 `run_all.sh --retry-failed-once` | 退出 1，訊息含 `may not be quarantined`（寫法對照既有 TC-089）；也就是平台測試失敗不能靠隔離放行，新項目一樣 | 自動：`tests/run_all_retry_test.sh` |
| SC-08 | 計畫 SC-08（沿用 SS-09） | 例外 | `CI=true` 且 PATH 上沒有 Java | 分別執行十個項目 | 十個都退出非 0，輸出含 `FAIL (CI=true)`（CI 上不准跳過的規則沒被新項目繞過） | 自動：`platform/tests/test_platform_parts.py` |

## User Story 3 — 每個項目實測都 ≤ 180 秒（優先度 P1）

> 對應計畫「目標」與完成標準 1、2：時鐘項目原本 205～213 秒、離 300 秒單項上限只剩約 90 秒。維護者（verifier 報告 needs-human 第 2 點）要的是：最慢的一項不再貼近上限。以下全部要在桌機 WSL、循序量測（同一份 checkout 不能同時跑兩次）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SC-21 | 完成標準 1 | 功能 | 桌機 WSL，量測前後記下 `nproc` 與 `/proc/loadavg`；循序執行 | 對十個平台項目各自單獨執行一次（`( time bash tests/<名>.sh )`），並看 `bash tests/run_all.sh` 輸出中十個平台項目的 `ok  <n>s` | 1 分鐘平均負載 ≤ 3 時，十個都 ≤ 180 秒（硬條件）；負載 > 3 時只記錄秒數與負載，硬條件改為「沒有 TIMEOUT 行」；改前改後的行與負載都貼在 ledger | 手動：閱卷者在 WSL 重跑核對 |
| SC-22 | 完成標準 2 | 功能 | 同上 | 單獨量 `platform_clock_test.sh`（`test_station_e2e.py`）與 `platform_clock_2_test.sh`（`test_nextflow_e2e.py`），對照改前 `platform_clock_test.sh` | 兩者各自 ≤ 180 秒；兩者秒數之和不比改前 `platform_clock_test.sh` 多 20% 以上 | 手動：閱卷者在 WSL 重跑核對 |
| SC-23 | 完成標準 1、6 | 功能 | 桌機 WSL，不帶 `--timeout`（預設 300 秒） | 執行完整 `bash tests/run_all.sh`；另執行 `bash tests/run_all.sh --only platform_` | 兩趟都全綠，輸出沒有任何 `TIMEOUT` 行（已知環境紅 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 只剩這一條紅時視同綠） | 手動：以 `GREEN <sha>` 完成記號為完整套件的證據；閱卷者在 WSL 重跑 `--only platform_` |
| SC-27 | 作法 0 第 4 點 | 例外 | 作法 0 量到兩個檔其中任何一個單獨 > 180 秒（乾淨機器） | 執行者在 ledger 記錄量測 | 執行者停止並回報 BLOCKED，不去動檔內容或另想辦法；若沒有發生，ledger 有兩個檔各自單獨秒數（約 68、約 110 的量級）且都 ≤ 180 | 手動：閱卷者讀 ledger 作法 0 的數字 |

## User Story 4 — 兩處文字更正與範圍乾淨（優先度 P2）

> 對應計畫「作法 4」「作法 5」與裁決 4：把 suite-speed 帳本裡拿「各檔秒數總和」當牆鐘比較的一句更正；文件項目清單同步。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SC-12 | 作法 4；裁決 4；計畫 SC-12 | 功能 | 改後的 `specs/suite-speed/ledger.md` | 讀第 26 行那一句；執行 `git diff --stat origin/v3 -- specs/suite-speed/ledger.md` | 不再含 `within 30 percent of the plan's 580 s wall`；含 `586`；同一句明說 3249.2 秒是逐檔秒數加總、不是牆鐘，並以同一次量測的 `real`（9m46s／12m38s）當牆鐘；`(D4, D9)` 與「8 份的結論不變」的意思保留；diff 顯示只改 1 行（`1 insertion, 1 deletion`），其他句子、數字、表格不動 | 手動：閱卷者讀 diff（`grep -c 586`、`grep -c "within 30 percent"`） |
| SC-14 | 作法 5；計畫 SC-14 | 功能 | 改後的程式 | 在 `docs/TESTING.md`、`docs/PLATFORM.md`、`tests/platform_clock_test.sh` 檔頭、`tests/` 與 `docs/` 搜尋 | 兩份文件都提到 `platform_clock_2_test.sh` 並說明「時鐘兩個檔各占一個項目」；`tests/platform_clock_test.sh` 檔頭不再含 `fourth`，並說明它只選 `clock`＝`test_station_e2e.py`、另一個檔在 `platform_clock_2_test.sh`；`tests/` 與 `docs/` 不再含 `four platform entries` | 手動：閱卷者用 `grep -rn` 核對 |
| SC-25 | 完成標準 7；範圍：檔案 | 功能 | 改後的程式 | 執行 `git diff --stat origin/v3` | 變動的檔案只在計畫「範圍：檔案」列出者之內（`tests/platform_test.sh`、`tests/platform_clock_test.sh`、`tests/run_all.sh`、`tests/quarantine.txt`、`tests/run_all_shard_test.sh`、`tests/run_all_retry_test.sh`、`platform/tests/test_platform_parts.py`、`docs/TESTING.md`、`docs/PLATFORM.md`、`specs/suite-speed/ledger.md`），加新增的 `tests/platform_clock_2_test.sh` 與 `specs/suite-clock-split/ledger.md`；`tests/run_all.sh` 只改隔離名單 `case`（原第 174 行）與兩條 awk 樣式（原第 363、364 行，兩行一致）及可能的個數註解 | 手動：閱卷者看 `git diff --stat origin/v3` 與 `tests/run_all.sh` 的 diff |

## 不在範圍 — 計畫明講這次不做的事（優先度 P1）

> 對應計畫「不做」「不准動（硬規則）」與裁決 2、3。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SC-09 | 不做第 1 條；計畫 SC-09（沿用 SS-12） | 不在範圍 | 改後的程式 | 讀 `run_all.sh` 的使用說明與 `PER_TEST_TIMEOUT` 的預設；查 diff 有無新增 `--timeout` | `PER_TEST_TIMEOUT` 仍是 300，使用說明仍寫 `default 300`；沒有偷調上限，沒有新增 `--timeout` | 自動：`platform/tests/test_platform_parts.py` |
| SC-13 | 不做第 5 條；裁決 2（覆寫作法 3、完成標準 5）；計畫 SC-13 | 不在範圍 | 改後的程式 | 執行 `git diff origin/v3 -- .github/` 與 `git diff --stat origin/v3 -- .github/` | 輸出完全為空：`.github/` 底下零變動，連註解也沒碰（過期的 `tests.yml` 第 36～38 行註解由 developer-agent 另案處理，本片不改） | 手動：閱卷者執行上述指令 |
| SC-30 | 不做第 6 條；「不准動」第 1、2 點 | 不在範圍 | 改後的程式 | 執行 `git diff --stat origin/v3` 並搜尋這些路徑：`web*.py`、`platform/abf_platform/web*.py`、`static/`、`DESIGN.md`、`PRODUCT.md`、`platform/tests/test_web_*`、`.specify/memory/constitution.md`、`hooks/*`、`platform/abf_*`、`.claude-plugin/plugin.json`、`docs/ROADMAP.md`、`platform/tests/` 內除 `test_platform_parts.py` 以外的檔 | 以上全部零變動（憲法裡「四個入口」過期字面不改） | 手動：閱卷者看 `git diff --stat origin/v3` |
| SC-31 | 不做第 2、4 條；「不准動」第 4 點 | 不在範圍 | 改後的程式 | 查 diff：有無刪除、`skip`／`xfail` 標記、改動任何平台測試的內容；查有無引入 `pytest-xdist` 或按歷史秒數切分的外掛 | 沒有；本片只搬「哪個檔在哪個項目」；SC-01、SC-26 同時證明測試集合沒少 | 手動：閱卷者讀 diff 並 `grep -rn xdist` |
| SC-32 | 不做第 3 條 | 不在範圍 | 改後的程式 | 讀 `tests/platform_test.sh` 的 `PLATFORM_PARTS` 與時鐘兩項目的檔數 | `PLATFORM_PARTS=8` 不變；沒有新增數字分片、沒有把一個檔拆更細；時鐘兩項目各只含一個檔 | 手動：閱卷者讀 diff（與 SC-16 互相印證） |
| SC-33 | 不做第 7 條；作法 5 | 不在範圍 | 改後的程式 | 讀本片新增或改寫的註解與文件文字（`tests/platform_test.sh`、`tests/platform_clock_test.sh`、`tests/platform_clock_2_test.sh`、`tests/quarantine.txt` 第 12 行、`docs/TESTING.md`、`docs/PLATFORM.md`），並搜尋 `/home/<名>/` 一類路徑，以及 `PREFLIGHT_ONLY:-}" = "2"` 與 `${XDG_CACHE_HOME:-$HOME/.cache}` 兩個字面 | 新寫的文字裡沒有秒數、沒有項目個數；沒有 `/home/<名>/` 路徑；兩個必須保留的字面仍在（`test_scope.py`、`test_wrapper*.py` 讀全文） | 手動：閱卷者讀 diff；`test_scope.py`、`test_wrapper*.py` 自動佐證路徑與字面 |

## 憲法與安全網

<!-- 觸及的憲法條目：第 2 條（通道規則與「從 Nextflow 紀錄重建」兩項檢查，憲法 .specify/memory/constitution.md 第 46～52 行，皆由 run_all.sh 的平台項目執行）。「平台測試失敗不能靠隔離放行」的保護在 SC-06、SC-19。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| SC-29 | 第 2 條（檢查由 `tests/run_all.sh` 的平台項目執行）；目標「測試一個都不刪」 | 功能 | 改後的程式；沿用 SC-01 的收集 | 在十個項目收集到的測試編號聯集裡，找憲法點名的測試：`test_human_channel.py` 的 `test_tch09_*`、`test_confirm_page.py` 的 `test_tch09_b_c_*`、`test_tc030_rebuild_gives_back_every_field` | 每一個都至少出現在其中一個項目（拆分後它們仍會被 `run_all.sh` 跑到，不會掉出所有項目） | 自動：`platform/tests/test_platform_parts.py` |
