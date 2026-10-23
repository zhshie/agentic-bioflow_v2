# 測試案例：畫布檢查——必填輸入沒接改成錯誤，可省略的仍是警告

**規格**：`specs/open-input-required/plan.md`（本任務沒有 spec.md；維護者無原話，來源是 017c 計畫的待決事項與 PR #178 說明「unconnected inputs are warnings until the catalogue's optional is used to raise required ones to errors」。判定規則以計畫的「裁決二」為準，它取代「目標」裡「只要有一筆 optional false」那句）　**總覽**：`test-case-overview.md`

名詞：「輸入通道」＝一個節點的某個輸入編號，目錄裡可能有好幾筆「輸入記錄」（例如 samtools_sort 的輸入 1 有 meta2、fasta、fai 三筆）；「meta 記錄」＝ type 為 `map` 的那一筆；「非 meta 記錄」＝同一通道裡其餘的記錄；「必填」＝依裁決二：非 meta 記錄中有任一筆 `optional` 明確為 `false`；「入口節點」＝完全沒有進邊的節點；「非入口」＝至少有一條進邊的節點；「真目錄」＝ `platform/abf_platform/data/nf-core-modules.json`；「合成目錄」＝測試自己造的小目錄（沒有寫 optional 欄位，除非該 TC 明說）。TC 編號前綴 `TC-OI`。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 非入口節點上必填的輸入沒接 → 錯誤（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-OI01 | 失敗先行測試 `test_required_open_input_on_a_non_entry_node_is_an_error`；目標 | 功能 | 合成目錄：節點 a 有一個輸出，節點 b 有輸入 0（已由 a 接上）與輸入 1（一筆非 meta 記錄，`optional: false`，沒接線） | 對這張圖做畫布檢查（`validate`） | 有且只有一項 `OPEN_INPUT` 發現，`node` 是 b、`channel` 是 1，`severity` 是 `error`；結果的 `ok` 為 False | 自動：`platform/tests/test_validate.py::test_required_open_input_on_a_non_entry_node_is_an_error` |
| TC-OI02 | 裁決二 5（措辭沿用，只改 severity） | 功能 | 同 TC-OI01 | 讀那項發現的 `message` | 說「少了一個輸入」、含節點 b、輸入號 1、該通道的輸入名；中文與括號內英文並列；請使用者確認是否可省略、不能省略就接線；**不含**入口那句的「入口」 | 自動：`test_validate.py` |
| TC-OI03 | 裁決二 2 的例子「輸入 2（index_format false）→ 必填」；真目錄 | 功能 | 真目錄；圖：fastqc 節點 qc 的 `zip` 接到 samtools_sort 節點 s 的輸入 0（既有測試用的那張圖） | `validate`，看 `OPEN_INPUT` 的發現 | s 的輸入 2（`index_format`）是 `error`；`ok` 為 False | 自動：`test_validate.py` |
| TC-OI04 | 裁決二 2（「有任一筆 false」） | 功能 | 合成目錄：b 有進邊；b 的一個沒接的輸入通道含兩筆非 meta 記錄，一筆 `optional: false`、一筆 `optional: true` | `validate` | 該通道的 `OPEN_INPUT` 是 `error` | 自動：`test_validate.py` |
| TC-OI05 | 裁決二 2（「有任一筆 false」，另一筆沒寫欄位） | 功能 | 合成目錄：b 有進邊；b 的一個沒接的輸入通道含兩筆非 meta 記錄，一筆 `optional: false`、另一筆**沒有** `optional` 欄位 | `validate` | 該通道的 `OPEN_INPUT` 是 `error` | 自動：`test_validate.py` |
| TC-OI06 | 目標（只針對「沒接」） | 功能 | 同 TC-OI01，但 b 的輸入 0 也是必填（`optional: false`）而且已由 a 接上 | `validate` | 輸入 0 沒有任何 `OPEN_INPUT` 發現；仍只有輸入 1 那一項 error | 自動：`test_validate.py` |
| TC-OI07 | 目標（逐通道判定） | 功能 | 合成目錄：b 有進邊；b 的輸入 1、輸入 2 各一筆非 meta 記錄且 `optional: false`，兩者都沒接 | `validate` | 兩項 `OPEN_INPUT`（b 的 1、b 的 2），兩項都是 `error`；`ok` 為 False | 自動：`test_validate.py` |

## User Story 2 — 可省略的輸入沒接仍是警告（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-OI10 | 失敗先行測試 `test_optional_open_input_stays_a_warning`；目標 | 功能 | 同 TC-OI01 的圖，但 b 輸入 1 的所有記錄都是 `optional: true`；圖中沒有別的 error | `validate` | 輸入 1 的 `OPEN_INPUT` 是 `warning`；`ok` 為 True | 自動：`platform/tests/test_validate.py::test_optional_open_input_stays_a_warning` |
| TC-OI11 | 裁決二 2 的例子「samtools_sort 輸入 1（meta2 false、fasta true、fai true）→ 非 meta 都 true → warning」；真目錄 | 功能 | 同 TC-OI03 的圖 | `validate`，看 s 的輸入 1 | s 的輸入 1 是 `warning`（同一次檢查裡輸入 2 是 error）；message 是「少了一個輸入」的寫法，含 meta2、fasta、fai | 自動：`test_validate.py` |
| TC-OI12 | 裁決二 2（通道只有 meta 記錄 → 不算必填） | 功能 | 合成目錄：b 有進邊；b 的一個沒接的輸入通道只有一筆 meta 記錄（type `map`），且寫了 `optional: false` | `validate` | 該通道的 `OPEN_INPUT` 是 `warning` | 自動：`test_validate.py` |
| TC-OI13 | 裁決二 2、3（沒有 optional 欄位 ＝ 不算必填） | 功能 | 合成目錄（輸入記錄完全沒有 `optional` 欄位）：b 有進邊，b 的輸入 1 沒接 | `validate` | 輸入 1 的 `OPEN_INPUT` 是 `warning`；`ok` 為 True | 自動：`test_validate.py` |
| TC-OI14 | 裁決二 2（meta 記錄不算，即使它是 false） | 功能 | 合成目錄：b 有進邊；b 的一個沒接的輸入通道有一筆 meta 記錄 `optional: false`，加一筆非 meta 記錄 `optional: true` | `validate` | 該通道的 `OPEN_INPUT` 是 `warning` | 自動：`test_validate.py` |

## User Story 3 — 入口節點的必填輸入仍是警告（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-OI20 | 失敗先行測試 `test_entry_node_required_input_is_still_a_warning`；目標 | 功能 | 合成目錄：節點 a 沒有任何進邊，它的輸入 0 是一筆非 meta 記錄 `optional: false`，沒接 | `validate` | 輸入 0 的 `OPEN_INPUT` 是 `warning`；沒有 error 時 `ok` 為 True | 自動：`platform/tests/test_validate.py::test_entry_node_required_input_is_still_a_warning` |
| TC-OI21 | 目標（「訊息照舊說送出時要由樣本表或參數供應」） | 功能 | 同 TC-OI20 | 讀那項發現的 `message` | 文字與改動前完全相同：含「這個節點是入口，送出時要由樣本表或參數供應」與英文括號段；**不含**「少了一個輸入」 | 自動：`test_validate.py` |
| TC-OI22 | 失敗先行測試 `test_real_catalogue_golden_still_ok` | 功能 | 真目錄；017c 的黃金圖（fastqc → multiqc） | `validate` | `ok` 為 True；發現恰好一項：`qc`、輸入 0、`OPEN_INPUT`、`warning`、入口寫法；與 `good_fastqc_multiqc.expected.json` 相同 | 自動：`platform/tests/test_validate.py::test_real_catalogue_golden_still_ok` |
| TC-OI23 | 目標（入口節點的必填輸入）；twins 夾具 | 功能 | 真目錄；`open_inputs_twins.json`（兩個 samtools_sort 入口 s1、s2 接到 multiqc）；其中 index_format 是必填 | `validate` | 六項 `OPEN_INPUT` 全是 `warning`、都是入口寫法，順序 s1:0、s1:1、s1:2、s2:0、s2:1、s2:2；`ok` 為 True；與 `open_inputs_twins.expected.json` 逐字相同 | 自動：`test_validate.py::test_open_inputs_list_matches_compose_render`（不修改而通過） |
| TC-OI24 | 目標（入口與非入口在同一張圖裡各自判定） | 功能 | 合成目錄：節點 a 是入口，輸出接到 b 的輸入 0；a 與 b 各有一個沒接的必填輸入 | `validate` | a 那項是 `warning`（入口寫法），b 那項是 `error`（少了一個輸入寫法）；`ok` 為 False | 自動：`test_validate.py` |

## User Story 4 — 既有檢查與固定答案不退步（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-OI30 | 裁決二 3（`bad_edges.expected.json` 預期不必改） | 功能 | `bad_edges.json`（合成目錄，沒有 optional 欄位） | `validate`，與 `bad_edges.expected.json` 比對 | 與期望檔逐字相同：d 的輸入 0 的 `OPEN_INPUT` 仍是 `warning`；其餘四項發現不變；該期望檔在 diff 中未被修改（若被修改，須符合 TC-OI41） | 自動：`test_validate.py::test_fixtures_and_hand_derived_answers`（不修改而通過） |
| TC-OI31 | 裁決二 4（允許更新既有測試，改名並改成新規則） | 功能 | 實作完成後的 `test_validate.py` | 閱卷者讀 diff：舊的 `test_open_inputs_are_warnings_never_errors_and_entry_nodes_say_so` | 該測試已改名；新內容斷言「非入口＋必填 → error；可省略、入口 → warning」；舊的「全部都是 warning」斷言只在這個測試被改成新規則，沒有被刪成更弱的斷言 | 手動：閱卷者讀 diff |
| TC-OI32 | 裁決二 4（其他既有斷言不動） | 功能 | 實作完成後的 `test_validate.py` | 閱卷者逐項比對 diff 與 base | 除 TC-OI31 的測試、`mod()` 輔助函式、與新增的測試之外，沒有任何既有斷言被刪除、放寬、跳過或改期望值 | 手動：閱卷者讀 diff |
| TC-OI33 | 裁決二 4（`mod()` 可加 optional 參數，預設不帶欄位） | 功能 | 實作完成後的 `test_validate.py` | 閱卷者讀 `mod()` | 不傳 optional 參數時，產生的輸入記錄沒有 `optional` 欄位（讓所有既有的合成目錄測試維持原狀） | 手動：閱卷者讀 diff |
| TC-OI34 | 「不改其他 code 的規則」 | 功能 | 既有各測試 | 跑 `test_validate.py` 的 code 與 severity 相關測試 | 仍只有七種 code（沒有新 code）；`GRAPH_STALE`、`META_MISMATCH`、`TYPE_MISMATCH`、`MIXED_SOURCES`、`DUPLICATE_PROCESS` 仍是 error，`PATTERN_MISMATCH` 仍是 warning | 自動：`test_validate.py::test_only_the_seven_codes_appear`、`test_pattern_mismatch_is_a_warning_and_does_not_fail_ok` 等（不修改而通過） |
| TC-OI35 | 既有「純函式」守則 | 功能 | `validate.py` 改動後 | 跑純度測試 | 檔案只 import `re` 與 `from . import catalogue, compose`；不含 `sqlite3`、`urllib`、`subprocess`、`open(`、`lint`、`stub` 等字樣 | 自動：`test_validate.py::test_validate_module_is_pure`（不修改而通過） |
| TC-OI36 | 既有「固定順序、重複相同、不改輸入」 | 功能 | 既有測試用的圖 | 跑順序與不改輸入的測試 | 同一張圖兩次結果相同、與輸入順序無關；error 排在 warning 之前的排序規則不變；傳入的圖沒有被修改 | 自動：`test_validate.py::test_findings_are_in_a_fixed_order_and_repeatable`、`test_validate_never_mutates_its_input`（不修改而通過） |
| TC-OI37 | 「不改儲存格式」；完成標準「全套綠」 | 功能 | 資料庫儲存驗證結果的既有測試 | 跑 `platform/tests/test_pipelines_validation.py` 與全套 | 全部通過且該檔未被修改：結果仍照原樣存入、取回，`ok` 為 False 的結果也一樣存取 | 自動：`platform/tests/test_pipelines_validation.py`、`tests/run_all.sh`（見 CLAUDE.md） |

## User Story 5 — 文件與紀錄（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-OI40 | 範圍：`docs/PLATFORM.md`（Validation 小節一句） | 功能 | 實作完成後的 `docs/PLATFORM.md` | 閱卷者讀 Validation 小節 | 原本「`OPEN_INPUT`（…the catalogue does not say which inputs are optional, so this is never an error）」已改寫：說明非入口節點上必填的輸入沒接是 error，可省略的或入口節點的是 warning；`OPEN_INPUT` 不再被列為「永遠不是 error」；其餘句子沒被動 | 手動：閱卷者讀 diff |
| TC-OI41 | 失敗先行測試末條；範圍：`ledger.md` | 功能 | 實作完成後的 `specs/open-input-required/ledger.md` 與 `platform/tests/fixtures/validate/*.expected.json` 的 diff | 閱卷者對照 | 每一個被改的 expected 檔，ledger 都有一段手推（哪個節點、哪個通道、哪筆記錄 optional 是什麼、所以為什麼變成 error）；沒有任何 expected 檔被改時，ledger 明寫「沒有」；expected 檔不是用程式輸出回填 | 手動：閱卷者讀 diff 與 ledger |

## User Story 6 — 這次不做的事（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-OI50 | 裁決 1（不需要 migration） | 不在範圍 | 本任務的 diff | 閱卷者看 diff | 沒有新增或修改任何 migration 檔、沒有改資料表欄位或 `pipeline_validations` 的建表；計畫中「不需要 migration」的理由仍在 | 手動：閱卷者讀 diff |
| TC-OI51 | 不做：「不改其他 code 的規則」 | 不在範圍 | `validate.py` 的 diff | 閱卷者讀 diff | 只動 `OPEN_INPUT` 的判定（`_unwired` 及其用到的輔助）；`_edge_findings`、`_mixed`、`_same_names`、陳舊檢查等其他 code 的邏輯沒有改動 | 手動：閱卷者讀 diff |
| TC-OI52 | 不做：「不改儲存格式」 | 不在範圍 | 黃金圖與壞圖的結果 | 檢查結果的欄位 | 結果的鍵仍恰為 `catalogue_sha`、`checks`、`findings`、`ok`、`open_inputs`；每項發現的鍵仍恰為 `node`、`channel`、`code`、`severity`、`message`；`open_inputs` 的內容仍列出所有沒接的通道（包含可省略的與入口的） | 自動：`test_validate.py::test_golden_good_graph_is_ok_with_one_open_input_warning`、`test_finding_shape_and_ok_follow_the_severity`（不修改而通過） |
| TC-OI53 | 不做：「不改 017b」；範圍外的檔案 | 不在範圍 | 本任務的整個 diff | 閱卷者列出被改的檔案 | `platform/abf_platform/compose.py`、`platform/tests/test_compose.py`、`platform/abf_platform/actions/`、`platform/abf_platform/catalogue.py`、`platform/abf_platform/data/nf-core-modules.json` 都沒有任何改動 | 手動：閱卷者讀 diff |
| TC-OI54 | 範圍：檔案清單 | 不在範圍 | 本任務的整個 diff | 閱卷者列出被改的檔案 | 被改的檔案只限計畫「範圍：檔案」所列五項（`validate.py`、`test_validate.py`、`fixtures/validate/*.expected.json`、`docs/PLATFORM.md`、`ledger.md`）；沒有改 `spec.md`、`plan.md`、`test-case*.md`；沒有新增新的 code 或新的對外動作 | 手動：閱卷者讀 diff |

## 專長守則（backend）

本任務只改一個純函式的判定，不新增任何動作、不碰權限與資料表；下列各條證明守則所說的事沒有被破壞。

| 編號 | 守則條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-OI60 | 對等性：使用者可見動作與動作層函式一一對應 | 不在範圍 | 本任務的 diff | 閱卷者看 diff 與動作對等性的既有測試 | 沒有新增或改動任何網頁路由、MCP 工具、聊天指令或動作層函式（`actions/`、`web.py`、`mcp_server.py` 都沒改）；既有的對等性測試不修改而通過 | 手動：閱卷者讀 diff；全套綠 |
| TC-OI61 | 跨使用者：讀與寫各被拒絕 | 功能 | 第二位使用者的身分；第一位使用者存了一個圖與它的驗證結果 | 第二位使用者取得或重驗第一位的圖 | 仍然回「找不到」（與不存在的圖相同的回答），不洩漏有這個圖 | 自動：`platform/tests/test_pipelines_validation.py::test_not_found_and_other_users`（不修改而通過） |
| TC-OI62 | 確認管道：寫入動作未經確認不得改資料 | 功能 | 一個已存的圖 | 做驗證 | 驗證不產生確認單、不排任何工作，只寫平台自己的資料庫；行為與改動前相同 | 自動：`test_pipelines_validation.py::test_validate_makes_no_confirmation_or_job`（不修改而通過） |
| TC-OI63 | 錯誤訊息與日誌：說明發生什麼事、該怎麼處理；不露堆疊、內部路徑、SQL、密鑰 | 例外 | 一項新的 error 級 `OPEN_INPUT` 發現（如 TC-OI01 的圖） | 檢查它的 `message` 與整份結果 | 含中文與括號內英文；說出「哪個節點的哪個輸入沒接」與「確認能否省略，不能省略就接線」；文字中沒有 Traceback、檔案路徑、SQL 或金鑰字樣 | 自動：`test_validate.py`（新測試，或把 error 級 OPEN_INPUT 納入 `test_every_finding_is_bilingual_and_says_what_to_do` 的檢查範圍） |
