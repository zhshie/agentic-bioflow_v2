# 測試案例：四個名稱檢查的正規式結尾從 `$` 改成 `\Z`（regex-dollar-newline）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Write every row so that it can be
judged without reading code: what is set up, what the person or the system does,
what must be seen. No internal jargon without a one-line explanation.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/regex-dollar-newline/plan.md`（本件沒有 spec.md，計畫即規格；「維護者原話」與「失敗先行測試」「裁決」各條的例子是出題依據）　**總覽**：`test-case-overview.md`

名詞白話：「結尾換行」＝名字最後多一個看不見的換行字元（例如 `"abc\n"`）。舊寫法 `$` 會把它當成合法的 `abc`；新寫法 `\Z` 只認字串真正的結尾，所以會擋掉。「對照組」＝合法的名字，改前改後都必須照常通過。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

測試命名：新測試一律在註解寫 `regex-dollar-newline TC-0xx`（既有測試檔裡已有別的規格用過 `TC-0xx` 編號，不加前綴會撞名，閱卷時找不到）。

## User Story 1 — 管線組裝（compose）擋掉結尾換行（優先度 P1）

入口依計畫裁決 3、4、5：管線名走 `compose.render(canonical, name, version)`；節點 id、參數鍵走 `compose.normalize(graph, data)`；輸出名走手工組出的 canonical 圖直接呼叫 `compose.render`（因為 `normalize` 會先擋「沒有這個輸出通道」，改前就被拒、紅不了）。若 `ext.args\n` 經 `normalize` 也被前一道檢查擋住，同樣改走 `render`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；失敗先行測試「compose」第 2 句；裁決 3 | 例外 | 一個合法的 canonical 圖（來自 `normalize` 的結果） | 呼叫 `compose.render(canonical, "abc\n", 1)` | 被拒（丟出名稱不合法的錯誤）；沒有產出 `main.nf`。**改前會被收下，所以測試改前紅** | 自動：`platform/tests/test_compose.py` |
| TC-002 | 失敗先行測試「compose」第 1 句（節點 id `"a\n"`）；`_ID` | 例外 | 一個圖，其中一個節點的 id 是 `"a\n"`，其餘合法 | 呼叫 `compose.normalize(graph)` | 回報問題（回傳的問題清單非空、不給 canonical 圖），問題訊息指出節點 id 不合法。改前紅 | 自動：`platform/tests/test_compose.py` |
| TC-003 | 裁決 1、4；`_KEY` | 例外 | 一個圖，其中一個節點的參數鍵是 `ext.args\n`，其餘合法 | 呼叫 `compose.normalize(graph)`（若被前一道檢查擋住則改走 `render`） | 回報該參數鍵不能用的問題。改前紅 | 自動：`platform/tests/test_compose.py` |
| TC-004 | 裁決 1、4、5；`_IDENT` | 例外 | 手工組出的 canonical 圖，其中一條邊的輸出通道名是 `"x\n"` | 直接呼叫 `compose.render(canonical, "demo-qc", 1)` | 被拒（丟出「邊指向不存在的節點或不能接線的通道」錯誤）。改前紅 | 自動：`platform/tests/test_compose.py` |
| TC-005 | 目標「合法名字的結果完全不變」；對照組 | 功能 | 一個合法的 canonical 圖 | 用兩個合法管線名呼叫 `compose.render`：`"a"`（最短）與恰好 40 字的 `"a"` 加 39 個 `"b"`（最長合法長度） | 兩個都成功產出檔案。改前改後都綠 | 自動：`platform/tests/test_compose.py` |
| TC-006 | 對照組 | 功能 | 圖中節點 id 為兩個合法值 | 呼叫 `compose.normalize`：id `"a"`（最短）與恰好 32 字的 id（最長合法長度，小寫字母開頭、含數字與底線） | 兩個都被接受，沒有問題 | 自動：`platform/tests/test_compose.py` |
| TC-007 | 對照組 | 功能 | 圖中節點參數鍵為合法值 | 呼叫 `compose.normalize`：參數鍵 `ext.args` 與 `ext.prefix` | 兩個都被接受 | 自動：`platform/tests/test_compose.py` |
| TC-008 | 對照組 | 功能 | 手工組出的 canonical 圖，邊的輸出通道名為合法識別字 | 直接呼叫 `compose.render`：輸出名 `"x"` 與 `"out_1"` | 兩個都被接受、成功產出 | 自動：`platform/tests/test_compose.py` |
| TC-009 | 失敗先行測試「對照組」第二句；完成標準 | 功能 | 既有 golden（`fastqc_multiqc` 範例圖與其手寫的標準輸出） | 用合法管線名渲染該圖 | `main.nf`、`modules.json`、`nextflow.config` 與改前逐位元組相同（既有 `test_fastqc_multiqc_renders_the_golden` 不改且保持綠） | 自動：`platform/tests/test_compose.py` |

## User Story 2 — 建立管線（create_pipeline）擋掉結尾換行（優先度 P1）

入口：`create_pipeline(platform_path, *, name, graph)`，圖用合法圖。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 失敗先行測試「pipelines」；維護者原話第 2 點 | 例外 | 一個合法的圖，資料庫裡還沒有管線 | `create_pipeline(name="abc\n", graph=合法圖)` | 回傳 `ok` 為 False（被拒）。改前紅 | 自動：`platform/tests/test_pipelines_validation.py` |
| TC-011 | 失敗先行測試「pipelines」：「資料庫／儲存沒有新增」 | 例外 | 同 TC-010，先記下管線表與版本表的筆數 | 做完 TC-010 的呼叫後再數 | 兩張表的筆數都沒變（沒有新管線、沒有新版本） | 自動：`platform/tests/test_pipelines_validation.py` |
| TC-012 | 作法「不新增拒絕訊息，走各處既有的拒絕路徑與文字」；維護者原話第 2 點 | 例外 | 同 TC-010 | 分別用 `"abc\n"` 與一個舊版本就會擋的名字（大寫 `"ABC"`）呼叫 `create_pipeline` | 兩次回傳的拒絕訊息文字相同，且仍是既有那句（小寫英文、數字與 -、1 到 40）；沒有新增訊息 | 自動：`platform/tests/test_pipelines_validation.py` |
| TC-013 | 對照組 | 功能 | 同 TC-010 | 分別用 `"abc"` 與恰好 40 字的合法名字（`"a"` 加 39 個 `"b"`）呼叫 `create_pipeline` | 兩個都建立成功（`ok` 為 True） | 自動：`platform/tests/test_pipelines_validation.py` |

## User Story 3 — 登記資料集（register_dataset）擋掉結尾換行（優先度 P1）

入口：`register_dataset(platform_path, *, name, version, samplesheet, files)`，樣本表與檔案用既有測試用的合法組合。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 失敗先行測試「datasets」第 1 句；目標「可以多一個字元超過 64 字上限」 | 例外 | 合法的樣本表與檔案、合法的版本 | `register_dataset(name="a"*64 + "\n", …)` | 被拒（`ok` 為 False）。改前紅 | 自動：`platform/tests/test_datasets.py` |
| TC-021 | 失敗先行測試「datasets」：`"a"*64` 仍被接受 | 功能 | 同 TC-020 | `register_dataset(name="a"*64, …)` | 被接受（`ok` 為 True），最長合法長度不變 | 自動：`platform/tests/test_datasets.py` |
| TC-022 | 裁決 7 | 例外 | 合法的名稱、樣本表與檔案 | `register_dataset(version="v1\n", …)` | 被拒。改前紅 | 自動：`platform/tests/test_datasets.py` |
| TC-023 | 裁決 7 | 功能 | 同 TC-022 | `register_dataset(version="v1", …)` | 仍被收下 | 自動：`platform/tests/test_datasets.py` |
| TC-024 | 作法「不新增拒絕訊息」 | 例外 | 同 TC-020 | 分別用 `"a"*64 + "\n"` 與一個舊版本就會擋的名字（含空白的 `"a b"`）呼叫 | 兩次拒絕訊息文字相同，是既有那句（英數字、. _ -，長度 1 到 64，且不能像憑證）；沒有新增訊息 | 自動：`platform/tests/test_datasets.py` |
| TC-025 | 對照組「每個檢查各舉兩個合法名字」 | 功能 | 同 TC-020 | `register_dataset` 用第二個合法名字（含 `.` `_` `-` 的短名，例如 `"run-1.v2_a"`） | 被接受 | 自動：`platform/tests/test_datasets.py` |

## User Story 4 — 啟動時的 `owner/name` 識別字（build）擋掉結尾換行（優先度 P1）

入口：`abf_launch/build.py` 的 `_param_path`（第 226 行用到 `OWNER_NAME`）。依裁決 6：改後 `_param_path` 會把 `nf-core/rnaseq\n` 當成路徑回傳（不再回 None），真正的拒絕在 `_confine`；要求的是「從外面送進來最後被拒」，不在乎是哪一層拒。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 失敗先行測試「build」第 1 句；裁決 6 | 例外 | 一個啟動請求，其 params 有一個值是 `"nf-core/rnaseq\n"`；使用者自己的上傳資料夾與讀取根目錄照既有測試設定 | 把它送進 `_confine`（或測試能用的、經過 `_param_path` 再到 `_confine` 的最外層入口） | 最後被拒絕（丟出「路徑在允許讀取的範圍之外」那類既有的拒絕），不會被當成合法的 `owner/name` 識別字放行。改前紅（改前 `_param_path` 回 None、被放行） | 自動：`platform/tests/test_name_anchors.py`（或找到合適的既有檔） |
| TC-031 | 失敗先行測試「build」：`"nf-core/rnaseq"` 仍通過 | 功能 | 同 TC-030，params 值是 `"nf-core/rnaseq"` | 呼叫 `_param_path(...)`，並送進 `_confine` | `_param_path` 回 None（當作識別字、不是路徑），`_confine` 沒有拒絕 | 自動：同上 |
| TC-032 | 對照組「每個檢查各舉兩個合法名字」 | 功能 | 同 TC-030，params 值是第二個合法 `owner/name`（例如含 `.` `_` `-` 的 `"my_org.x/pipe-1.0"`） | 呼叫 `_param_path(...)` | 回 None，不被當成路徑 | 自動：同上 |

## User Story 5 — 範圍與記錄守則（優先度 P1）

本節的手動項都是 `git diff origin/v3...HEAD` 檢查（計畫裁決 8：不需要 TESTING.md 步驟，ledger 貼 diff 統計即可）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 完成標準「`git diff --stat` 只含範圍列的檔」 | 不在範圍 | 實作完成 | 看 `git diff --stat origin/v3...HEAD` | 只出現這些檔：`platform/abf_platform/compose.py`、`platform/abf_platform/actions/pipelines.py`、`platform/abf_platform/actions/datasets.py`、`platform/abf_launch/build.py`、`platform/tests/test_compose.py`、`platform/tests/test_pipelines_validation.py`、`platform/tests/test_datasets.py`、（必要時新增的）`platform/tests/test_name_anchors.py`，以及本件 `specs/regex-dollar-newline/` 底下的計畫與 ledger | 手動：`git diff --stat origin/v3...HEAD`（貼進 ledger） |
| TC-041 | 作法「樣式其餘字元一字不改」；完成標準「每個程式檔只動正規式那幾行」 | 不在範圍 | 實作完成 | 逐行看四個程式檔的 diff | 程式檔只改了 7 行：`compose.py` 的 `_ID`、`_NAME`、`_KEY`、`_IDENT`（4 行），`pipelines.py` 的 `_NAME`（1 行），`datasets.py` 的 `_NAME`（1 行），`build.py` 的 `OWNER_NAME`（1 行）；每一行與舊行相比只差結尾 `$` 變 `\Z`，允許字元與長度一字不變 | 手動：`git diff origin/v3...HEAD -- platform/abf_platform platform/abf_launch` |
| TC-042 | 範圍；裁決 2：datasets 的 `_SCHEME`、`_EXT`、`_TAG`、`_NUM`、`_LANE` 不准動 | 不在範圍 | 實作完成 | 看 `datasets.py` 的 diff | 這五個正規式完全沒有出現在 diff 裡；檔名切割行為與改前相同 | 手動：`git diff origin/v3...HEAD -- platform/abf_platform/actions/datasets.py` |
| TC-043 | 作法「不新增拒絕訊息」；「不做」第 1 點「不改拒絕訊息」 | 不在範圍 | 實作完成 | 在上述程式檔的 diff 中找任何新增或修改的拒絕訊息文字 | 沒有；程式檔 diff 只有 TC-041 那 7 行 | 手動：同 TC-041 |
| TC-044 | 範圍「不准碰」清單；完成標準「沒有既有測試被改弱」 | 不在範圍 | 實作完成 | 看 diff 是否碰到 `fetch.py`、`records.py`、`cloud_store.py`、`launch.py`、`mcp_server.py`、`handlers.py`、`rules.py`、`web/`；並看三個既有測試檔的 diff | 上述檔案與目錄完全沒有變動；既有測試檔的 diff 只有新增行，沒有刪除或改動任何既有斷言、沒有新增 skip | 手動：`git diff origin/v3...HEAD` |
| TC-045 | 「不做」第 2 點：不掃全 repo 其他 `$` 結尾的正規式 | 不在範圍 | 實作完成 | 看 diff 有沒有改到範圍列以外的任何正規式（如 `compute_envs.py` 的 `_QUEUE`、`rules.py`） | 沒有；若執行者看到疑似閘門，只寫在 ledger 的「後續」 | 手動：`git diff origin/v3...HEAD`；ledger「後續」 |
| TC-046 | 「不做」第 3 點；專長守則「不需要 migration」 | 不在範圍 | 實作完成 | 看 diff 有沒有資料表結構、欄位、資料內容或 migration 的變動 | 沒有任何結構或資料變動，也沒有新增 migration（計畫已寫明理由：已存的名字都不含換行） | 手動：`git diff origin/v3...HEAD` |
| TC-047 | 範圍「測試」第 29 行規則 | 功能 | 實作完成 | 若新建了 `platform/tests/test_name_anchors.py`，看它的前 40 行 | 前 40 行內有 `# Nothing existing: …`，後面的原因說明至少 15 個字；若沒有新建這個檔，本條視為不適用並在 ledger 寫明 build 的案例放在哪個既有檔 | 手動：看檔頭前 40 行 |
| TC-048 | 失敗先行測試「紅的輸出貼進 ledger」「兩分支比對」 | 功能 | 實作完成 | 在 `origin/v3` 與本分支各跑一次同一份新測試檔，輸出貼進 ledger | `origin/v3` 上：TC-001～004、TC-010、TC-011、TC-020、TC-022、TC-030 紅，其餘對照組（TC-005～009、013、021、023、025、031、032）綠；本分支上全部綠。ledger 有兩邊輸出 | 手動：看 `specs/regex-dollar-newline/ledger.md` |

## 憲法與安全網

本件動的是輸入閘門（名稱檢查）。維護者原話：「絕不放寬安全網」。專案 CLAUDE.md 校準失敗第 1 條：修閘門時縮窄了匹配範圍、放過舊版會擋的形狀，所有 TC 都過、只有拿舊形狀在兩個分支都跑才抓得到。所以要求用同一份測試在 `origin/v3` 與本分支各跑一次。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 安全網「絕不放寬」（維護者原話）；校準失敗第 1 條 | 例外 | 舊版（`origin/v3`）就會擋的形狀，用邊界值：41 字的管線名（`create_pipeline`）、大寫 `"ABC"` 管線名、65 字的資料集名（`register_dataset`）、33 字的節點 id（`normalize`） | 同一份測試在 `origin/v3` 與本分支各跑一次 | 這些形狀在兩個分支都被拒；本分支沒有任何一個被放行（只收緊、不放寬） | 自動：放在三個既有測試檔與 `test_name_anchors.py` 內；兩分支輸出貼 ledger |
| TC-051 | 完成標準「整個 `platform/tests` 套件全綠」 | 功能 | 實作完成 | 全套測試（WSL，`tests/run_all.sh`）在 HEAD 跑完，完成記號為 `GREEN <HEAD sha>` 且工作區乾淨 | 全綠（已知環境紅依 dev-plans README「通例：已知環境紅」，須逐條列名） | 自動：完成記號（閱卷時不重跑全套） |
