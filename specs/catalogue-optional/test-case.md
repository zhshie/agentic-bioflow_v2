# 測試案例：模組目錄快照記下輸入是否可省略（optional）

**規格**：`specs/catalogue-optional/plan.md`（本任務沒有 spec.md；維護者無原話，來源是 017c 計畫的待決事項「必填輸入目前只能是 warning；要變成錯誤，須另開 A 級任務讓快照帶 optional」）　**總覽**：`test-case-overview.md`

名詞：「輸入記錄」＝快照裡每個模組 `inputs` 清單中的一筆（有 channel、name、type、pattern）；「輸出記錄」＝ `outputs` 清單中的一筆；「攤平」＝ `catalogue.flatten` 把上游 meta.yml 轉成快照格式；「真快照」＝ `platform/abf_platform/data/nf-core-modules.json`。TC 編號前綴 `TC-OP` 是為了不跟 017a 的 TC 編號混淆。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

## User Story 1 — 攤平時保留輸入的 optional（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-OP01 | 失敗先行測試 `test_flatten_keeps_optional_true`；目標 | 功能 | 一份 meta.yml 資料，輸入（新格式：輸入是「清單的清單」）中有一筆寫了 `optional: true` | 對它做攤平 | 攤平後那一筆輸入記錄的 `optional is True` | 自動：`platform/tests/test_catalogue.py::test_flatten_keeps_optional_true` |
| TC-OP02 | `test_flatten_defaults_optional_false`；「meta.yml 沒寫就是 false」 | 功能 | 一份 meta.yml 資料，輸入記錄完全沒有 `optional` 這個欄位 | 對它做攤平 | 那一筆輸入記錄的 `optional is False` | 自動：`test_catalogue.py::test_flatten_defaults_optional_false` |
| TC-OP03 | 「每筆輸入記錄」；快照裡有舊格式模組 | 功能 | 舊格式的 meta.yml（輸入是一層清單，像 `samtools/sort` 那種），其中一筆寫了 `optional: true` | 對它做攤平 | 那一筆 `optional is True`，其他筆為 False | 自動：`test_catalogue.py` |
| TC-OP04 | 目標（逐筆記錄，不是整個模組一個值） | 功能 | 一個模組有三筆輸入，只有第二筆寫 `optional: true` | 攤平 | 三筆的 `optional` 依序為 `[False, True, False]`，不會互相影響 | 自動：`test_catalogue.py` |
| TC-OP05 | 「布林」 | 功能 | 既有的 FASTQC、SAMTOOLS_SORT 兩份測試資料（都沒寫 optional） | 攤平 | 每一筆輸入記錄的 `optional` 型別就是真正的布林值（`is True`／`is False`），不是 `None`、字串或數字 | 自動：`test_catalogue.py` |
| TC-OP06 | 「不改輸出記錄」的對照：輸入記錄其他欄位不動 | 功能 | FASTQC 資料 | 攤平 | 每筆輸入記錄的 channel、name、type、pattern 值，跟加 optional 之前完全一樣（例如 `reads` 在 channel 0、type `file`、pattern `None`） | 自動：`test_catalogue.py` |
| TC-OP07 | 目標：每筆輸入記錄「帶」optional | 功能 | 任一份有輸入的測試資料 | 攤平 | 每筆輸入記錄的欄位集合剛好是 `{channel, name, type, pattern, optional}`，不多不少 | 自動：`test_catalogue.py::test_inputs_new_format_channels`（該測試的欄位集合期望值依 TC-OP10 更新） |
| TC-OP08 | 不做：「不改輸出記錄」 | 不在範圍 | 一份 meta.yml，輸出記錄上也寫了 `optional: true`（新格式與舊格式各一） | 攤平 | 每筆輸出記錄的欄位集合仍然剛好是 `{channel, name, type, pattern}`，沒有 `optional` | 自動：`test_catalogue.py` |
| TC-OP09 | 不做：不改輸出；沿用 017a 結構 | 功能 | 三份測試資料建成的快照 | 檢查頂層與模組的欄位順序 | 頂層仍是 `source, sha, count, modules, errors`；每個模組仍是 `name, path, description, keywords, tools, inputs, outputs`；沒有 `generated_at` | 自動：`test_catalogue.py::test_key_order_and_no_generated_at`（不修改而通過） |
| TC-OP10 | 完成標準「既有 017a 測試照舊通過」；`test_snapshot_of_three_fixtures_equals_the_golden`、`test_inputs_new_format_channels` 的期望值必然隨之更新 | 功能 | 這兩個測試是僅有的、本來就會因輸入記錄多一欄而改變期望的既有測試 | 看 diff：兩個測試的期望值怎麼改 | 只允許「在輸入記錄上加 `optional: False`（GOLDEN）／把欄位集合加上 `optional`」，其餘斷言與期望值一字不動；不得刪掉、跳過或放寬任何斷言；其他既有測試（TC-002 至 TC-024 等）沒有任何修改 | 自動：`test_catalogue.py`；改動範圍由閱卷者讀 diff 確認 |
| TC-OP11 | 沿用 017a 的容錯：奇形怪狀的輸入不致命 | 例外 | meta.yml 的輸入含 `None`、數字、`{"a": None}`，或整段 `input` 是空／null | 攤平 | 不報錯，奇形怪狀的項目照舊被略過（輸入清單為空），其餘模組照常 | 自動：`test_catalogue.py::test_odd_shapes_are_skipped_not_fatal`、`test_missing_or_null_sections_are_empty_lists`（不修改而通過） |
| TC-OP12 | 「沒寫就是 false」的極端情況 | 例外 | 一筆輸入記錄的內容是空的（例如 `{"x": {}}`，連 type、pattern 都沒有） | 攤平 | 不報錯；`type` 與 `pattern` 為 `None`，`optional is False` | 自動：`test_catalogue.py`（可併入 `test_missing_type_and_pattern_are_null`，但原有斷言不得減少） |
| TC-OP13 | 沿用 017a：叢集路徑遮蔽 | 功能 | 輸入的 name、pattern 含看起來像叢集路徑的字串 | 攤平 | 仍被遮成 `<path>/`，跟之前一樣；`optional` 維持布林不受影響 | 自動：`test_catalogue.py::test_cluster_like_paths_are_masked_in_every_string_field`（不修改而通過） |

## User Story 2 — 真快照以同一個上游版本重產，且每筆輸入都帶 optional（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-OP20 | `test_snapshot_has_optional_on_every_input_record` | 功能 | 重產後的真快照 | 逐模組逐筆檢查輸入記錄 | 全部（目前約 9417 筆）都有 `optional`，且都是布林；任何一筆缺欄位或不是布林就失敗 | 自動：`test_catalogue.py::test_snapshot_has_optional_on_every_input_record` |
| TC-OP21 | `test_snapshot_marks_known_optional_input` | 功能 | 執行者從上游 5ed90b42 的某個 meta.yml 找到一個明確標 `optional: true` 的輸入，把模組名與輸入名寫進測試 | 查真快照該模組該輸入 | 該筆輸入記錄 `optional is True`；同一模組中沒標 optional 的輸入是 False（至少斷言一筆，證明不是整個模組一律 True） | 自動：`test_catalogue.py::test_snapshot_marks_known_optional_input` |
| TC-OP22 | 目標；使用者可見處是 `describe` | 功能 | 真快照 | 呼叫 `catalogue.describe("fastqc")` | 回傳的每一筆 `inputs` 都帶布林 `optional` | 自動：`test_catalogue.py` |
| TC-OP23 | 「以同一個上游 sha 重產」→ 內容不應多或少模組 | 功能 | 重產後的真快照 | 讀 `count`、`errors` | `count == 2116`、`errors == []`（重產前的快照就是這兩個值；同一個上游版本不該變） | 自動：`test_catalogue.py` |
| TC-OP24 | 「重產」而非手改：差異只有 optional | 功能 | base 分支的真快照與本分支的真快照 | 閱卷者把本分支快照每筆輸入記錄的 `optional` 拿掉後，跟 base 逐項比對 | 完全相同（模組、順序、tools、outputs、errors、sha 全不變） | 手動：閱卷者讀 diff（見總覽「不確定的地方」） |
| TC-OP25 | 完成標準「`test_dumps_matches_file` 類測試在重產後仍成立」 | 功能 | 重產後的真快照 | 讀檔內容跟 `catalogue.dumps(catalogue.load())` 比 | 逐位元相同，結尾剛好一個換行，沒有 `generated_at` | 自動：`test_catalogue.py::test_committed_snapshot_is_what_dumps_writes`（不修改而通過） |
| TC-OP26 | 同上（既有 017a 排序／順序） | 功能 | 真快照 | 檢查模組排序與欄位順序 | 模組依 (name, path) 排序；錯誤依 path 排序；每個模組欄位順序仍是 `name, path, description, keywords, tools, inputs, outputs` | 自動：`test_catalogue.py::test_committed_snapshot_order`（不修改而通過） |
| TC-OP27 | 同上（既有 017a） | 功能 | 真快照 | 找 `versions` 開頭的輸出頻道 | 一個都沒有 | 自動：`test_committed_snapshot_has_no_versions_channels`（不修改而通過） |
| TC-OP28 | 同上（既有 017a，打包大小） | 功能 | 重產後的真快照（檔案因多了欄位而變大） | 看檔案大小 | 仍 ≤ 8 MB | 自動：`test_committed_snapshot_is_the_pinned_upstream`（不修改而通過） |
| TC-OP29 | 不做：「不改輸出記錄」 | 不在範圍 | 真快照 | 逐筆檢查所有模組的輸出記錄 | 每一筆的欄位集合都剛好是 `{channel, name, type, pattern}`，沒有 `optional` | 自動：`test_catalogue.py` |
| TC-OP30 | 不做：「不換上游 sha」 | 不在範圍 | 重產後的真快照 | 讀 `sha` | 仍是 `5ed90b42e78410e7411e9c6bdfeff33226d6c58e` | 自動：`test_catalogue.py::test_committed_snapshot_is_the_pinned_upstream`（不修改而通過） |
| TC-OP31 | 專長守則（backend）：錯誤訊息說明原因與處理方式 | 例外 | 目錄檔不存在，或查詢不存在的模組 | 呼叫 `load(不存在的路徑)`、`describe("nope")`、`describe("")` | 訊息跟變更前一字不差（含中英文、含處理方式「用 search 找相近的名字」），不含 `Traceback` | 自動：`test_catalogue.py::test_missing_catalogue_file_does_not_raise`、`test_describe_unknown_is_a_clean_not_found`（不修改而通過） |
| TC-OP32 | 範圍：`specs/catalogue-optional/ledger.md`；`test_snapshot_marks_known_optional_input` 要求「在 ledger 記出處路徑」 | 功能 | 執行完成 | 閱卷者讀 ledger | ledger 寫明 TC-OP21 用的模組、輸入名，以及它在上游 5ed90b42 的 meta.yml 路徑（`modules/nf-core/<模組>/meta.yml`） | 手動：閱卷者讀 `ledger.md`（見總覽「不確定的地方」） |

## User Story 3 — 文件說明 optional 的意思（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-OP40 | 範圍：`docs/PLATFORM.md` 模組目錄一節補一句 optional 的意義 | 功能 | 「## nf-core module catalogue」到「## What the platform stores」之間那一節 | 讀這一節 | 節內出現 `optional` 一詞，並說明：輸入記錄帶布林 `optional`，meta.yml 標了 `optional: true` 才是 true，沒寫就是 false（原文沒有這個詞，改前此斷言會失敗） | 自動：`test_catalogue.py`（擴充 `test_platform_doc_has_the_catalogue_section` 或新增一個測試） |
| TC-OP41 | 完成標準「既有 017a 測試照舊通過」 | 功能 | 同一節 | 既有文件檢查 | 仍含 `5ed90b42…` 整串 sha、`nf-core-modules.json`、`python -m abf_platform.catalogue snapshot`、`PR` 與 tier A 字樣 | 自動：`test_catalogue.py::test_platform_doc_has_the_catalogue_section`（原有斷言不得減少） |

## User Story 4 — 這次不做的事與守則邊界（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-OP50 | 不做：「不改 017c 的 OPEN_INPUT 判定」 | 不在範圍 | 本任務的整個 diff | 看 diff 有沒有碰 `platform/abf_platform/compose.py` 與 `platform/tests/test_compose.py` | 兩個檔案都沒有任何改動 | 手動：閱卷者讀 diff |
| TC-OP51 | 同上；行為面 | 不在範圍 | 目錄裡有「沒接的輸入」，快照多了 optional 之後 | 跑既有的組裝測試 | `test_compose.py` 不修改而全過；沒接的輸入照舊列在 `open_inputs`，不因 `optional` 變成錯誤或被略過 | 自動：`platform/tests/test_compose.py`（不修改而通過） |
| TC-OP52 | 專長守則（backend）：動作層對等／不新增動作 | 不在範圍 | 本任務完成 | 檢查 `mcp_server.py`、`web.py`、`web_board.py`、`actions/*.py` | 都沒有出現 `catalogue`：這次沒新增任何工具、網頁路由或動作，所以沒有第二份邏輯，也沒有新的寫入路徑 | 自動：`test_catalogue.py::test_no_tool_route_or_action_mentions_the_catalogue`（不修改而通過） |
| TC-OP53 | 專長守則（backend）：資料結構變動要有 migration 或說明理由；計畫裁決 1「不需要 migration」 | 不在範圍 | 快照是檔案、不進資料庫 | 檢查 `catalogue.py` 與 diff | `catalogue.py` 不含 `sqlite3`、`abf_platform.store`、`subprocess`、`os.system`；diff 沒有新增或修改任何資料庫 migration／結構檔 | 自動：`test_catalogue.py::test_catalogue_source_stays_in_scope`（不修改而通過）；diff 部分由閱卷者確認 |
| TC-OP54 | 不做：不改公開函式 | 不在範圍 | 本任務完成 | 看 `load`、`search`、`describe` 的參數 | 仍分別是 `[path]`、`[q, data]`、`[name, data]` | 自動：同 TC-OP53 的測試 |
| TC-OP55 | 不做：「不改輸出記錄」，搜尋結果也不多欄 | 不在範圍 | 真快照 | `catalogue.search("fastqc")` | 每筆結果欄位仍剛好是 `name, path, description`，沒有 `optional` | 自動：`test_catalogue.py::test_search_result_keys`（不修改而通過） |
| TC-OP56 | 沿用 017a：執行時不需要 PyYAML | 不在範圍 | 沒有安裝 PyYAML 的環境 | 載入 `catalogue`，呼叫 `load`、`search`、`describe` | 正常運作且 `yaml` 沒被載入；`pyproject.toml`、`constraints.txt` 沒有把 yaml 加成相依 | 自動：`test_catalogue.py::test_catalogue_runs_without_pyyaml`、`test_yaml_is_not_a_dependency`（不修改而通過） |

<!--
專長守則（backend）對照：對等性、跨使用者、確認管道三類 TC 需要「使用者可見動作」「使用者紀錄」「寫入動作」，本任務三者皆無（唯讀的檔案快照，沒有新增動作／路由／寫入），故以 TC-OP52 證明沒有新增任何動作路徑；錯誤訊息／日誌以 TC-OP31 證明不變；migration 以 TC-OP53 證明不需要。
-->
