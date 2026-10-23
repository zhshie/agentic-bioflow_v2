# 測試案例：017c 畫布組合的靜態檢查——型別、未接輸入、重名，結果依版本存起來（純後端）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
這個任務沒有 spec.md；依據是 `plan.md`（含「維護者原話」「作法 A／B／C／D」「夾具與標準答案」「失敗先行測試」「允許更新的既有斷言」「裁決」「裁決二」「專長守則（backend）」）。每條預期結果都出自 plan 明寫的內容，沒有另外發明；plan 與「裁決二」衝突之處一律依裁決二。
-->

**規格**：`specs/017c-validate/plan.md`（沒有 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了（包含「該被抓到的壞圖有被抓到」）。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」。

名詞：「圖」＝畫布上的一張組合（節點＝一個 nf-core 模組，邊＝一個模組的輸出接到另一個模組的輸入）。「發現」＝檢查結果的一項，形狀是 `{node, channel, code, severity, message}`。「error／warning」＝嚴重（讓 `ok` 變 False）／只顯示（不影響 `ok`）。「meta」＝每個通道第一格、名字叫 `meta`／`meta2`… 且型別是 `map` 的那筆（代表樣本資訊）。「通道簽名」＝這個通道是否有 meta，加上其餘記錄的型別類別集合（`file`／`directory`＝path；`string`／`boolean`／`integer`／`float`＝val；`map`＝meta；`list`、缺漏或不認得＝any）。「GRAPH_STALE」＝存下來的圖對不上現在的目錄。「目錄」＝`catalogue.load()` 回的模組清單；「快照」＝提交在 repo 的 `nf-core-modules.json`（sha `5ed90b42e78410e7411e9c6bdfeff33226d6c58e`，2,116 個模組）；「合成目錄」＝測試自己手寫的 3～5 個小模組目錄。「別人的」＝另一位使用者建的組合。除非另標，純函式測試在 `platform/tests/test_validate.py`，儲存與擁有者測試在 `platform/tests/test_pipelines_validation.py`。

## User Story 1 — 發現清單的形狀、順序與可重複（`validate.validate`）（優先度 P1）

維護者原話：「拖模組、連線、填參數、驗證、送去跑……」（裁示 5）→ 「驗證」是獨立一步，輸入是已存的版本，輸出是人看得懂的結果，不改圖本身。總表 017c「有 error 的版本不能 launch」→ 本任務交出 `ok`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 A（回傳形狀）；`test_golden_good_graph_is_ok_with_one_open_input_warning` | 功能 | 真實目錄；fastqc 的 zip 接到 multiqc 輸入 0 的圖（節點 `qc`、`report`），經 `normalize` | `validate(canonical)` | 回傳是物件，鍵恰為 `ok`、`checks`、`catalogue_sha`、`findings`、`open_inputs`；`checks` 等於 `["static"]` | 自動：`test_validate.py` |
| TC-002 | 作法 A（`catalogue_sha`） | 功能 | 同 TC-001 | `validate(canonical)` | `catalogue_sha` 等於快照 sha `5ed90b42e78410e7411e9c6bdfeff33226d6c58e` | 自動 |
| TC-003 | 作法 A（一份發現的形狀） | 功能 | 一張同時有 error 與 warning 的圖（如 TC-091 到 TC-094 用的圖） | `validate` 後逐項看 `findings` | 每一項恰有 `node`、`channel`、`code`、`severity`、`message` 五個鍵；`severity` 只有 `"error"` 或 `"warning"` | 自動 |
| TC-004 | 作法 A（`ok` ＝沒有任何 error） | 功能 | 圖的發現全是 warning（如黃金圖只有一項 OPEN_INPUT） | `validate` | `ok` 為 True | 自動 |
| TC-005 | 作法 A（`ok` ＝沒有任何 error）；完成標準 | 功能 | 圖裡有至少一項 error（如一條 META_MISMATCH 的邊），另有 warning | `validate` | `ok` 為 False | 自動 |
| TC-006 | 作法 A（決定性順序：error 先於 warning） | 功能 | 一張同時有 error 與 warning 的圖 | `validate` | `findings` 裡所有 `severity` 為 `error` 的項都排在任何 `warning` 之前 | 自動：`test_findings_are_in_a_fixed_order_and_repeatable` |
| TC-007 | 作法 A（決定性順序：node、channel、code、message） | 功能 | 一張在同一嚴重度內有多個節點、多個輸入編號發現的圖（如 TC-090 的 twins 圖） | `validate` | 同一嚴重度內，`findings` 等於把同一批發現依 (node 字串序, channel 數值序, code, message) 排序的結果；例：`s1:0, s1:1, s1:2, s2:0, s2:1, s2:2` | 自動 |
| TC-008 | 作法 A（node 空字串在最前、channel 整數先於字串） | 功能 | 排序鍵的程式碼 | 驗收者讀 `validate.py` 的排序鍵 | 鍵的順序是 (severity 順序, node 為空者最前, channel 整數先於字串再依值, code, message)，與 plan 一致。（實際輸出中 null 節點只會與 GRAPH_STALE 同時出現，無法用輸出測，所以讀程式。） | 手動：驗收者讀原始碼 |
| TC-009 | 作法 A（同一張圖永遠逐字相同）；`test_findings_are_in_a_fixed_order_and_repeatable` | 功能 | 同一張圖，把 `nodes`、`edges` 順序打亂成另一份輸入 | 兩份各先 `normalize` 再 `validate`，每份各跑兩次 | 四份 `findings` 逐項相等 | 自動 |
| TC-010 | 裁決 8（決定性：不含時間、不含隨機） | 功能 | 同 TC-001 | `validate` | 回傳裡沒有 `validated_at`、`stale` 鍵；`findings` 的任何項也不含時間 | 自動 |
| TC-011 | 作法 B 訊息格式；`test_every_finding_is_bilingual_and_says_what_to_do` | 功能 | 涵蓋每一種 code 的圖（GRAPH_STALE、META_MISMATCH、TYPE_MISMATCH、PATTERN_MISMATCH、MIXED_SOURCES、OPEN_INPUT、DUPLICATE_PROCESS） | 逐項檢查 `message` | 每一項都含中文字，也含 ASCII 英文的括號段 | 自動 |
| TC-012 | 維護者原話（驗證不改圖本身）；`test_validate_never_mutates_its_input` | 功能 | 一份 `canonical`，先存一份深度複本 | `validate(canonical)` | 呼叫後 `canonical` 與複本深度相等 | 自動 |
| TC-013 | 作法 A（`open_inputs` 與 `compose.render` 同形同排序）；`test_open_inputs_list_matches_compose_render` | 功能 | 一張有多個沒接輸入的圖（如 twins） | 比較 `validate` 回的 `open_inputs` 與 `compose.render` 回的 `open_inputs` | 兩者逐項完全相同（內容與順序） | 自動 |
| TC-014 | 作法 A（`data` 預設 `catalogue.load()`） | 功能 | 同一張圖 | 一次不傳 `data`、一次傳 `catalogue.load()` | 兩次結果完全相同 | 自動 |

## User Story 2 — 邊兩端的型別對不對（META_MISMATCH／TYPE_MISMATCH）（優先度 P1）

維護者原話（總表 017b 失敗先行，已移到本任務）：「型別不合的邊被拒並點名兩端。」→ 型別不合的邊要被回報，並點名邊的兩端（來源節點＋輸出通道、目的節點＋輸入編號）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 作法 B3（只比類別集合，不比個數）；`test_tuple_with_more_elements_is_compatible_by_class` | 功能 | 合成目錄：來源輸出是 `[map, file]`（2 筆，如 fastqc zip），目的輸入是 `[map, file, file, file, file, file]`（6 筆，類別集合都是 path） | `validate` | 這條邊沒有 TYPE_MISMATCH 也沒有 META_MISMATCH | 自動 |
| TC-016 | 作法 B2；維護者原話（點名兩端）；`test_type_mismatch_names_both_ends` | 功能 | 合成目錄：來源 `a` 的輸出 `out` 是 `[map, file]`，目的 `b` 的輸入 0 是 `[file]`（沒有 meta），一條邊 `a.out` → `b` 輸入 0 | `validate` | 有一項 `META_MISMATCH`，`severity` 為 error；`node` 是 `b`、`channel` 是 0（目的端）；message 同時含來源 `a.out` 與目的 `b.0`，並說中間需要一個轉換節點 | 自動 |
| TC-017 | 作法 B2（兩端 `has_meta` 不同）；方向相反 | 功能 | 合成目錄：來源輸出是 `[file]`（單一值），目的輸入是 `[map, file]`（tuple） | `validate` | 同樣得到 `META_MISMATCH`（error），目的端為 `node`／`channel` | 自動 |
| TC-018 | 作法 B2（每條邊最多一項型別類發現）；`test_meta_mismatch_is_reported_and_not_also_a_type_mismatch` | 功能 | 一條邊兩端 `has_meta` 不同、類別集合也不相交（如 `[map, file]` → `[string]`） | `validate` | 這條邊只有 `META_MISMATCH` 一項，沒有 `TYPE_MISMATCH` | 自動 |
| TC-019 | 作法 B3；維護者原話（點名兩端）；`test_type_mismatch_names_both_ends` | 功能 | 合成目錄：`a` 的輸出 `[map, file]` 接 `c` 的輸入 0 `[map, string]`（兩端都有 meta，類別 path 對 val 不相交） | `validate` | 有一項 `TYPE_MISMATCH`，error；`node` 是 `c`、`channel` 是 0；message 同時含來源 `a.out` 與目的 `c.0` | 自動 |
| TC-020 | 作法 B3（一邊類別為空、另一邊不空） | 功能 | 合成目錄：來源通道只有 `[map]`（類別集合為空），目的輸入 `[map, file]` | `validate` | 這條邊得到 `TYPE_MISMATCH`（error） | 自動 |
| TC-021 | 作法 B1（`file`、`directory` 同為 path） | 功能 | 合成目錄：來源 `[map, file]`，目的 `[map, directory]` | `validate` | 這條邊沒有 TYPE_MISMATCH、沒有 META_MISMATCH | 自動 |
| TC-022 | 作法 B1（`string`、`boolean`、`integer`、`float` 同為 val） | 功能 | 合成目錄：來源 `[string]`，目的 `[integer]`（另試 boolean、float 的配對） | `validate` | 這些邊都沒有 TYPE_MISMATCH、沒有 META_MISMATCH | 自動 |
| TC-023 | 裁決 7；作法 B1；`test_any_and_unknown_types_are_compatible_with_anything_but_meta_must_still_match` | 功能 | 合成目錄：一端是 `list` 型別（或型別缺漏、或不認得的型別字串），另一端是 `file`、`string` 等非 meta 類別，兩端 `has_meta` 相同 | `validate` | 這些邊都沒有 TYPE_MISMATCH | 自動 |
| TC-024 | 裁決 7（`meta` 是否一致仍強制）；同上測試 | 功能 | 合成目錄：來源 `[map, list]`，目的 `[list]`（沒有 meta） | `validate` | 得到 `META_MISMATCH`（error）；`list` 不能豁免 meta 檢查 | 自動 |
| TC-025 | 作法 B；`test_tc118_still_holds_for_normalize_but_validate_flags_it`；「必須確認仍綠」`test_types_are_not_compared`（TC-118） | 功能 | 真實目錄；圖：fastqc `qc` 的 `html` 接 samtools_sort `s` 的輸入 2（`index_format`，單一字串） | `normalize(graph)` | 仍接受：`canonical` 不是 `None`、沒有 problem（017b 的 TC-118 不變） | 自動 |
| TC-026 | 完成標準；維護者原話（點名兩端）；`test_tc118_still_holds_for_normalize_but_validate_flags_it` | 功能 | 同 TC-025 通過 `normalize` 的 `canonical` | `validate(canonical)` | 有 `META_MISMATCH`（error），`node` 是 `s`、`channel` 是 2；message 同時含 `qc.html` 與 `s.2`；`ok` 為 False | 自動 |

## User Story 3 — pattern、混接、沒接的輸入、重名（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-027 | 作法 B4；裁決二 2；`test_pattern_mismatch_is_a_warning_and_does_not_fail_ok` | 功能 | 合成目錄：來源輸出恰一筆檔案類記錄、pattern 為 `*.{bam}`；目的輸入恰一筆檔案類記錄、pattern 為 `*.{vcf}`；類別相容；圖裡沒有別的發現來源 | `validate` | 有一項 `PATTERN_MISMATCH`，`severity` 為 warning；若沒有別的 error 則 `ok` 仍為 True | 自動 |
| TC-028 | 作法 B4（取不出副檔名就不比）；`test_pattern_that_cannot_be_parsed_is_skipped` | 功能 | 兩端各恰一筆檔案類記錄且有 pattern，但其中一個 pattern 取不出副檔名（如 `bai\|csi\|crai` 那類寫法或空殼字串） | `validate` | 沒有 PATTERN_MISMATCH | 自動 |
| TC-029 | 作法 B4；裁決二 2（展開大括號後有交集就不報） | 功能 | 兩端各恰一筆檔案類記錄：`*.{bam,cram}` 對 `*.{bam}` | `validate` | 沒有 PATTERN_MISMATCH | 自動 |
| TC-030 | 裁決二 2（任一端有多筆記錄就整條邊不比） | 功能 | 目的輸入通道有兩筆檔案類記錄且都有 pattern，pattern 與來源完全不相交 | `validate` | 沒有 PATTERN_MISMATCH | 自動 |
| TC-031 | 裁決二 2（任一筆 pattern 為 null 就整條邊不比） | 功能 | 兩端各恰一筆檔案類記錄，但目的端 pattern 為 null | `validate` | 沒有 PATTERN_MISMATCH | 自動 |
| TC-032 | 作法 B5；`test_mixed_sources_on_one_input_are_checked_pairwise` | 功能 | 合成目錄：目的 `d` 的輸入 1 接兩條邊，來源簽名 `has_meta` 不同（一個 `[map, file]`、一個 `[file]`） | `validate` | 有一項 `MIXED_SOURCES`，error；`node` 是 `d`、`channel` 是 1 | 自動 |
| TC-033 | 作法 B5（`classes` 兩兩不相交） | 功能 | 同一輸入通道接兩條邊，來源 `has_meta` 相同但類別集合不相交（path 對 val） | `validate` | 有一項 `MIXED_SOURCES`（error） | 自動 |
| TC-034 | 作法 B5（兩兩檢查） | 功能 | 同一輸入通道接三條邊，其中兩條彼此相容、第三條與其中一條不相容 | `validate` | 有 `MIXED_SOURCES`（error） | 自動 |
| TC-035 | 作法 B5；`test_compatible_sources_mix_without_a_finding` | 功能 | 真實目錄：samtools_sort 的 `s1`、`s2` 的 `bam` 都接 multiqc `report` 輸入 0 | `validate` | 沒有 `MIXED_SOURCES` | 自動 |
| TC-036 | 作法 B6；裁決 3；`test_open_inputs_are_warnings_never_errors_and_entry_nodes_say_so` | 功能 | 圖裡有沒有任何邊接到的輸入通道 | `validate` | 每個沒接輸入的通道得到一項 `OPEN_INPUT`，`severity` 為 warning（絕不是 error）；`node` 是該節點、`channel` 是輸入編號；若沒有別的 error，`ok` 為 True | 自動 |
| TC-037 | 作法 B6（入口節點的寫法） | 功能 | 節點完全沒有進來的邊（如黃金圖的 `qc`） | `validate` | 該節點的 OPEN_INPUT message 說明是「入口」、送出時要由樣本表或參數供應（message 含「入口」） | 自動 |
| TC-038 | 作法 B6（少一個輸入的寫法） | 功能 | 節點有別的進邊，但某個輸入通道沒接（如 multiqc 只用輸入 0 以外的情形，或合成目錄一個有兩個輸入的節點只接一個） | `validate` | 該通道的 OPEN_INPUT message 說「少了一個輸入」並請確認是否可省略；且與 TC-037 的入口寫法不是同一句 | 自動 |
| TC-039 | 作法 B6（message 列該通道的輸入名） | 功能 | samtools_sort 的輸入 1 沒接（輸入名 `meta2`、`fasta`、`fai`） | `validate` | 該項 message 含 `meta2`、`fasta`、`fai` | 自動 |
| TC-040 | 作法 B6（沒有任何邊接到的才算） | 功能 | 黃金圖的 multiqc 輸入 0 已有邊接上 | `validate` | `report`（multiqc）沒有任何 OPEN_INPUT | 自動 |
| TC-041 | 作法 B7；裁決二 4；`test_duplicate_process_names_and_alias_collisions` | 功能 | 合成目錄：兩個不同模組，path 分別為 `a/b` 與 `a_b`（process 名都是 `A_B`），各一個節點 | `validate` | 有 `DUPLICATE_PROCESS`，error；`ok` 為 False | 自動 |
| TC-042 | 裁決二 4（別名撞另一模組的 process 名） | 功能 | 合成目錄：模組 `fastqc` 有兩個節點 id `x`、`y`（別名 `FASTQC_X`、`FASTQC_Y`），再加一個 path 為 `fastqc/x` 的模組（process 名 `FASTQC_X`）的節點 | `validate` | 有 `DUPLICATE_PROCESS`，error；`ok` 為 False | 自動 |
| TC-043 | 作法 B7（沒撞名就不報） | 功能 | 真實目錄 twins 圖：兩個 samtools_sort 節點 `s1`、`s2`（別名 `SAMTOOLS_SORT_S1`、`SAMTOOLS_SORT_S2`）加 multiqc | `validate` | 沒有 `DUPLICATE_PROCESS` | 自動 |

## User Story 4 — 圖對不上現在的目錄（GRAPH_STALE）與參數（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-044 | 作法 B 第一步；`test_stale_graph_stops_after_the_graph_check` | 功能 | 一張有效的 `canonical`，拿一個把其中一個模組移掉的合成目錄當 `data` | `validate(canonical, data)` | 每條 `normalize` 的 problem 變成一項 `GRAPH_STALE`（error），`node` 與 `channel` 都是 `null`；`ok` 為 False | 自動 |
| TC-045 | 作法 B 第一步（sha 不等於現在的快照） | 例外 | 存下的圖節點 sha 是舊值，`data` 的 sha 已不同 | `validate` | 有 `GRAPH_STALE`（error） | 自動 |
| TC-046 | 作法 B 第一步（通道已消失） | 例外 | 存下的圖有一條邊從某模組的輸出通道接出，但 `data` 裡該模組已沒有這個輸出通道 | `validate` | 有 `GRAPH_STALE`（error） | 自動 |
| TC-047 | 作法 A（環等整張圖的問題 `node` 為 null） | 例外 | 圖的邊形成環，或節點接到自己 | `validate` | 有 `GRAPH_STALE`（error），`node` 為 `null` | 自動 |
| TC-048 | 裁決二 1；`test_param_rules_agree_with_normalize` | 例外 | 節點 `qc` 的 params 含 `publishDir` | `validate` | 得到 `GRAPH_STALE`（error），該項 message 同時點名節點 `qc` 與參數 `publishDir` | 自動 |
| TC-049 | 裁決二 1；`test_param_rules_agree_with_normalize`（用 017b `test_param_keys_and_values_are_restricted` 的同一批壞值） | 例外 | 同一批壞值：`ext.args1`、`ext.args10`、值含換行或 `\x07`、值是整數／布林／清單、值超過 1000 字元 | 對每個壞值先 `normalize` 再 `validate`；`normalize` 判不合法的，`validate` 也要判 | 凡 `normalize` 有 problem 的，`validate` 都回 `GRAPH_STALE`（error）且點名節點與參數名 | 自動 |
| TC-050 | 裁決二 1（合法值不被擋） | 功能 | 節點 params 含 `ext.args`、`ext.args2`…`ext.args9`、`ext.prefix`，值都是短字串 | `normalize` 後 `validate` | 沒有 `GRAPH_STALE` | 自動 |
| TC-051 | 作法 B 第一步；裁決 6 | 功能 | 一張圖同時有「目錄對不上」與「本來會產生 OPEN_INPUT／型別問題」的毛病 | `validate` | `findings` 只有 `GRAPH_STALE` 各項，沒有 OPEN_INPUT、META_MISMATCH 等其餘項 | 自動 |
| TC-052 | 作法 B 第一步（message 就用 problem 原文） | 功能 | 同 TC-044 | 比較 `validate` 的 GRAPH_STALE message 與 `normalize` 回的 problem | 每項 message 等於對應的 problem 原文（已是中英並陳） | 自動 |

## User Story 5 — 結果依版本存下來、讀出來、標記過期（`validate_pipeline`／`get_validation`）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-053 | 作法 C；`test_validate_pipeline_stores_and_get_validation_returns_it` | 功能 | 使用者 A 存了黃金圖（fastqc→multiqc）一個版本 | `validate_pipeline(平台路徑, 編號, caller=A)` | 回 `{"ok": True, "id", "name", "version", "validation": {...}}`；`validation` 含 `validate` 的全部欄位加 `validated_at`，且 `stale` 為 False | 自動：`test_pipelines_validation.py` |
| TC-054 | 作法 C（外層 `ok` 與內層 `validation.ok` 不同義） | 功能 | A 存了一張有 error 的圖（如含 TC-026 的邊） | `validate_pipeline` | 外層 `ok` 為 True（這次呼叫成功），`validation.ok` 為 False（圖有 error） | 自動 |
| TC-055 | 作法 C（`validated_at` 用注入的 `clock`） | 功能 | 傳入固定 `clock`（如回 1234.5） | `validate_pipeline` | `validation.validated_at` 等於 1234.5 | 自動 |
| TC-056 | 作法 C（`get_validation` 回存的結果） | 功能 | 剛 `validate_pipeline` 過 | `get_validation(平台路徑, 編號, caller=A)` | 回的 `validation` 與 `validate_pipeline` 回的是同一份（`findings`、`ok`、`checks`、`catalogue_sha`、`open_inputs`、`validated_at`），`stale` 為 False | 自動 |
| TC-057 | 作法 C；`test_get_validation_before_any_validation_is_none_not_an_error` | 功能 | A 的組合從沒驗證過 | `get_validation` | 回 `{"ok": True, "validation": None, ...}`，不是錯誤、不丟例外 | 自動 |
| TC-058 | 作法 C；`test_revalidating_replaces_the_row_and_keeps_one_row_per_version` | 功能 | 同一版本連續驗證兩次（第二次 `clock` 不同） | 兩次 `validate_pipeline`，查 `pipeline_validations` 表 | 該版本在表裡只有 1 列，且存的是第二次的 `validated_at` | 自動 |
| TC-059 | 作法 C（同上測試後半） | 功能 | A 的組合有版本 1 已驗證；再 `update_pipeline` 存出版本 2 並驗證 | 查表，並讀版本 1 的結果 | 表有 2 列（每版本一列）；版本 1 的結果與驗版本 2 之前逐項相同 | 自動 |
| TC-060 | 作法 C（`version=None` 同 `get_pipeline`） | 功能 | 組合有 2 個版本，只驗證了版本 1 | `get_validation(…, version=None)`；再 `get_validation(…, version=1)` | `version=None` 對應最新版本（版本 2）而回 `validation: None`；指定版本 1 回版本 1 的結果 | 自動 |
| TC-061 | 作法 C；裁決 5；`test_stored_result_is_stale_when_the_catalogue_sha_changes` | 功能 | 已驗證過；之後用 `data=` 傳入一份換了 `sha` 的目錄 | `get_validation(…, data=新目錄)` | `stale` 為 True；`findings`、`ok` 仍是原來存的內容（沒有重算）；表裡存的 `catalogue_sha`、`validated_at` 沒變 | 自動 |
| TC-062 | 作法 C（`stale` ＝目前目錄 sha 不等於存的） | 功能 | 已驗證過，目錄沒換 | `get_validation` | `stale` 為 False | 自動 |
| TC-063 | 作法 C；`test_validation_columns_say_nothing_about_runs` | 功能 | 驗證過一次 | 讀 `pipeline_validations` 的欄位 | 欄位恰為六個：`pipeline_id`、`version`、`graph_sha256`、`catalogue_sha`、`result_json`、`validated_at` | 自動 |
| TC-064 | 作法 C（表裡的 `catalogue_sha` 對得上結果） | 功能 | 驗證過一次 | 讀表中那一列 | `catalogue_sha` 等於存的 `result_json` 裡的 `catalogue_sha`，也等於快照 sha；`graph_sha256` 不是空字串 | 自動 |
| TC-065 | 作法 D；`test_validation_table_is_lazy_and_old_db_works` | 功能 | 一個沒有 `pipeline_validations` 表的舊 `platform.db` | 直接 `get_validation`；然後 `validate_pipeline` | `get_validation` 回 `validation: None` 且不丟例外；之後 `validate_pipeline` 成功 | 自動 |
| TC-066 | 作法 D（不需要 migration）；「必須確認仍綠」`test_old_platform_db_works_without_a_migration` | 功能 | 同 TC-065；以及 017b 既有測試（會 `DROP TABLE pipelines`／`pipeline_versions`） | 檢查 `store.STATE_SCHEMA`；跑既有測試 | `STATE_SCHEMA` 不含 `pipeline_validations`；既有測試不改、仍綠 | 自動 |
| TC-067 | 作法 C（不放進 `pipeline_versions`）；`test_pipeline_versions_stay_append_only` | 功能 | 驗證過一次，記下 `pipeline_versions` 的 `graph_json` | 對 `pipeline_versions` 試 `UPDATE`、`DELETE`；再讀 `graph_json` | `UPDATE`、`DELETE` 仍被擋；`graph_json` 逐位元不變 | 自動 |
| TC-068 | 作法 C（公開函式 5 個變 7 個）；「允許更新的既有斷言」第一處 | 功能 | `actions/pipelines.py` | 列出公開函式；檢查 `abf_platform.actions` 套件 | 公開函式名單依字母序恰為 `create_pipeline`、`get_pipeline`、`get_validation`、`list_pipelines`、`render_pipeline`、`update_pipeline`、`validate_pipeline`；`actions` 套件裡沒有這 7 個名字 | 自動：`test_pipelines_store.py`（既有測試依計畫改名單，其餘邏輯不變） |
| TC-069 | 「允許更新的既有斷言」第二處 | 功能 | `test_pipelines_store.py::test_pipelines_columns_say_nothing_about_runs` | 跑該測試，且比對它與 base 的內容 | 該測試沒有被改，仍綠（只比 `pipelines`、`pipeline_versions` 兩表欄位） | 自動 |
| TC-070 | 作法 C（找不到）；「找不到這個組合」 | 例外 | 不存在的組合編號（如 999999） | `validate_pipeline`；`get_validation` | 都回 `ok` 為 False，訊息含「找不到這個組合」；沒有寫入任何列 | 自動 |

## User Story 6 — 擁有者、不經確認、不啟動程式（優先度 P1）

維護者原話：「a caller sees and uses only their own」（擁有者規則）；裁示 9「……它只寫到平台自己的目錄、不花 SU」→ 驗證不經確認管道；憲章原則 2「平台不啟動程式」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-071 | 擁有者規則（寫）；`test_other_user_cannot_validate_or_read_a_validation` | 例外 | A 存了一個組合；使用者 B 另有身分 | B 呼叫 `validate_pipeline(A 的編號, caller=B)` | 被拒，訊息為「找不到這個組合」；B 沒有看到 A 的任何內容 | 自動 |
| TC-072 | 擁有者規則（讀） | 例外 | A 的組合已驗證過 | B 呼叫 `get_validation(A 的編號, caller=B)` | 被拒（not found），沒有任何 A 的結果內容 | 自動 |
| TC-073 | 擁有者規則（別人的與不存在的同一句話） | 例外 | 同 TC-071；另有一個不存在的編號 | 比較 B 對 A 的組合與對不存在編號呼叫 `validate_pipeline` 的訊息 | 訊息的 `words()` 相同（編號本身除外） | 自動 |
| TC-074 | 擁有者規則（同上，讀取函式） | 例外 | 同 TC-072 | 比較 B 對 A 的組合與對不存在編號呼叫 `get_validation` 的訊息 | 訊息的 `words()` 相同 | 自動 |
| TC-075 | 擁有者規則（B 被拒後不留痕） | 例外 | A 的組合沒有驗證過；B 試圖驗證它被拒 | 查 `pipeline_validations` 表 | 表裡沒有因 B 的呼叫而新增的列 | 自動 |
| TC-076 | 作法 C；`test_terminal_caller_none_sees_everything` | 功能 | A 與 B 各有一個組合 | `caller=None`（終端）對兩人的組合各 `validate_pipeline` 與 `get_validation` | 都成功，看得到每個人的 | 自動 |
| TC-077 | 裁決 1；`test_validate_makes_no_confirmation_or_job` | 功能 | 記下 `jobs`、`confirmations`、`launches` 三表列數 | 呼叫 `validate_pipeline` 與 `get_validation` | 三表列數都沒變；沒有呼叫 `confirm` | 自動 |
| TC-078 | 作法 C（不寫檔、不排工作） | 功能 | 平台資料夾在呼叫前的檔案清單 | 呼叫 `validate_pipeline` 與 `get_validation` | 除了 `platform.db`（及其 SQLite 附屬檔）內容，資料夾裡沒有新增、刪除或改動的檔案 | 自動 |
| TC-079 | 專長守則；`test_error_messages_hide_internals` | 例外 | 觸發被拒回應（不存在的編號、別人的編號） | 讀回應文字與日誌輸出 | 不含 SQL 語句、堆疊追蹤、`platform.db` 路徑 | 自動 |
| TC-080 | 專長守則（日誌與回應不含密鑰） | 例外 | 用帶有 token 的呼叫者身分（B 的 token）觸發被拒與成功兩種回應 | 讀回應文字與日誌輸出 | 不含任何 token／密鑰字串 | 自動 |
| TC-081 | 專長守則（錯誤訊息說原因與怎麼辦） | 例外 | 被拒回應 | 讀訊息 | 訊息說明「找不到這個組合」這個原因，並讓使用者知道要換成自己有的組合編號（中英並陳） | 自動 |
| TC-082 | 作法 C；「必須確認仍綠」`test_pipelines_store_has_no_submit_path` | 功能 | 新增程式碼後的 `actions/pipelines.py` | 跑既有測試（掃原始碼） | 檔內（含註解）沒有 `subprocess`、`os.system`、`sbatch`、`srun`、`qsub`、`confirm`、`jobs`、`queue` 等字樣；測試沒被改弱 | 自動 |
| TC-083 | 憲章原則 2；`test_no_program_is_started_by_validation` | 功能 | `actions/pipelines.py` 中屬於本任務的部分（新表 SQL、`validate_pipeline`、`get_validation`）與整個 `validate.py` | 掃原始碼 | 不含 `subprocess`、`os.system`、`sbatch`、`nextflow`、`lint`、`stub`。（`render_pipeline` 既有 docstring 裡的 `nextflow.config` 不算本任務新增；改寫它或排除它都可，但字樣清單不得放寬。） | 自動 |
| TC-084 | 作法 A／B（純函式）；`test_validate_module_is_pure` | 功能 | `platform/abf_platform/validate.py` | 掃原始碼並看 import 行 | 只 import `catalogue`、`compose`（以及標準函式庫的純運算模組）；不含 `import store`、`sqlite3`、`urllib`、`requests`、`socket`、`subprocess`、`open(`、`nextflow`、`lint`、`stub` | 自動 |

## User Story 7 — 夾具與標準答案（優先度 P1）

維護者的完成標準：「對 017b 黃金圖存下後 `validate_pipeline` 得 `validation.ok` 為 True、findings 如夾具；對含 html→`index_format` 那條邊的圖得 `ok` 為 False 且 message 點名兩端。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-085 | 範圍：檔案；夾具 | 功能 | `platform/tests/fixtures/validate/` | 列出檔案 | 有 `good_fastqc_multiqc.json`、`bad_edges.json`、`open_inputs_twins.json` 三張圖，且各有 `*.expected.json` | 自動 |
| TC-086 | 夾具（`good_fastqc_multiqc.json` ＝ 017b 的圖） | 功能 | `fixtures/validate/good_fastqc_multiqc.json` 與 `fixtures/compose/fastqc_multiqc/graph.json` | 比對內容 | 兩者的圖內容相同 | 自動 |
| TC-087 | 夾具；`test_golden_good_graph_is_ok_with_one_open_input_warning` | 功能 | 真實目錄；黃金圖 | `validate` | `ok` 為 True；`findings` 恰好一項：`{"node": "qc", "channel": 0, "code": "OPEN_INPUT", "severity": "warning", message: …}`，message 是「入口」那一種；其中沒有 PATTERN_MISMATCH（multiqc 端有 null pattern） | 自動 |
| TC-088 | 夾具（黃金圖的 `open_inputs`） | 功能 | 同 TC-087 | 讀 `open_inputs` | 等於 `[{"node": "qc", "input": 0, "names": ["meta", "reads"]}]` | 自動 |
| TC-089 | 完成標準第一句 | 功能 | A 把黃金圖存成組合 | `validate_pipeline` | `validation.ok` 為 True，`validation.findings` 與 `good_fastqc_multiqc.expected.json` 相同 | 自動 |
| TC-090 | 夾具 `open_inputs_twins.json`（017b `fan_in_and_twins` 的圖） | 功能 | 真實目錄；twins 圖（`s1`、`s2` 兩個 samtools_sort 加 multiqc `report`） | `validate` | `findings` 恰為六項 OPEN_INPUT（warning），順序固定為 `s1:0, s1:1, s1:2, s2:0, s2:1, s2:2`，都是入口寫法；`report` 輸入 0 沒有 OPEN_INPUT；沒有其他發現；`ok` 為 True | 自動 |
| TC-091 | 夾具 `bad_edges.json`（`a`→`b`） | 功能 | 合成目錄：`a` 的輸出 `out` 是 `[map, file]`，接 `b` 的輸入 0（`[file]`，無 meta） | `validate` | 有 `META_MISMATCH`（error），`node` 為 `b`、`channel` 為 0 | 自動 |
| TC-092 | 夾具 `bad_edges.json`（`a`→`c`） | 功能 | 同圖：`a` 接 `c` 的輸入 0（`[map, string]`） | `validate` | 有 `TYPE_MISMATCH`（error），`node` 為 `c`、`channel` 為 0 | 自動 |
| TC-093 | 夾具 `bad_edges.json`（`d` 輸入 1） | 功能 | 同圖：`d` 的輸入 1 同時接 `a.out`（`[map, file]`）與 `e.out`（`[file]`） | `validate` | 有 `MIXED_SOURCES`（error），`node` 為 `d`、`channel` 為 1 | 自動 |
| TC-094 | 夾具 `bad_edges.json`（pattern 邊） | 功能 | 同圖：有一條 pattern 為 `*.{bam}` 接 `*.{vcf}` 的邊（類別相容） | `validate` | 有 `PATTERN_MISMATCH`（warning），並指在該邊的目的端 | 自動 |
| TC-095 | 夾具標準答案；裁決二 3 | 功能 | 同圖整張 | `validate`，與 `bad_edges.expected.json` 比對 | `ok` 為 False；`findings` 與 expected 逐項、逐字、同順序相同 | 自動 |
| TC-096 | 完成標準第二句；維護者原話（點名兩端） | 功能 | A 把含 fastqc `qc.html` → samtools_sort `s` 輸入 2 的圖存成組合 | `validate_pipeline` | `validation.ok` 為 False；有 `META_MISMATCH`，message 同時含 `qc.html` 與 `s.2` | 自動 |
| TC-097 | 裁決二 3（標準答案手推，不得由程式輸出回填） | 功能 | 三份 `*.expected.json` 與 `specs/017c-validate/ledger.md` | 驗收者讀 ledger，並獨立重推 | ledger 逐項寫出每條邊、每個 finding 為何出現（含 bad_edges 的 `d` 輸入 1 兩條進邊各自比對）；驗收者重推的結果與 expected 相同 | 手動：驗收者讀 ledger 並重推 |
| TC-098 | 裁決二 3（每條邊各自比對） | 功能 | `bad_edges` 的 `d` 輸入 1 兩條進邊 | `validate`，看 `d` 輸入 1 的發現 | 每條進邊各自對 `d` 輸入 1 的記錄做型別比對（各自可能產生 META_MISMATCH 或 TYPE_MISMATCH），另外因多來源而有 `MIXED_SOURCES`；各項點名各自的來源 | 自動 |

## User Story 8 — 文件與交付（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-099 | 裁決 9（`### Validation`） | 功能 | `docs/PLATFORM.md` 的 `## Composed pipelines` | 驗收者讀該節 | 有 `### Validation` 小節，說明：發現的形狀、error 與 warning 的區別、`ok` 的意義、目前只有靜態檢查而沒有 lint 或空跑、沒有 MCP 工具或網頁（017e 才開） | 手動：驗收者讀文件 |
| TC-100 | 裁決 9（stores 表加一列） | 功能 | `docs/PLATFORM.md` 的 `## What the platform stores` 表 | 驗收者讀該表 | 新增一列：`Pipeline validations: the latest check result for each saved pipeline version`，位置 `platform.db (pipeline_validations)`，並說「replaced by the next check of the same version; never deleted」 | 手動：驗收者讀文件 |
| TC-101 | 裁決 9 | 功能 | 文件加完 | 跑 `bash tests/platform_storage_doc_test.sh` | 綠；測試檔沒有被改（紅燈時只准調整該列寫法） | 自動：`tests/platform_storage_doc_test.sh` |
| TC-102 | 完成標準（PR 說明） | 功能 | PR 說明 | 驗收者讀 PR 說明 | 寫明：不需要 migration 的理由、新表可能不存在（讀取函式自己先建表）、與總表 017c 的差異（裁決 2、3）、站台側的空跑與 lint 另開一張票 | 手動：驗收者讀 PR 說明 |
| TC-103 | 完成標準（手動項） | 功能 | `specs/017c-validate/ledger.md` | 驗收者讀 ledger | 對真實模組檔跑 lint／空跑一項記為「未驗證」 | 手動：驗收者讀 ledger |

## User Story 9 — 這次不做的事

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104 | 不做：不加 MCP 工具 | 不在範圍 | `mcp_server.py`、`actions/__init__.py` | 跑工具數斷言與 `test_web_parity.py`；看 diff | 兩檔沒有任何變動；工具清單與對等表和 base 相同；`validate_pipeline`／`get_validation` 沒有被匯出成工具 | 自動 |
| TC-105 | 不做：不加網頁路由 | 不在範圍 | `web.py` | 看 diff；跑 `test_web_parity.py` | `web.py` 沒有變動，沒有新路由 | 自動 |
| TC-106 | 裁決 2：不跑 lint／`-stub-run`／nf-test，不加 job 種類 | 不在範圍 | `jobs.py`、`store.py`、`abf_station/*` | 看 diff；跑 `test_http_site_samplesheet.py::test_tc057_no_table_or_column_changed`（`SCHEMA_SHA256`）；看 `validate` 回傳的 `checks` | 這些檔沒有變動；`SCHEMA_SHA256` 測試仍綠（`jobs` 的 CHECK、`STATE_SCHEMA` 不動）；`checks` 恆為 `["static"]` | 自動 |
| TC-107 | 不做：不改 `compose.py`，`normalize` 仍不比型別 | 不在範圍 | `compose.py` | 看 diff；跑 `test_compose.py::test_types_are_not_compared` | `compose.py` 沒有變動；該測試未被改、仍綠 | 自動 |
| TC-108 | 不做：不要求目錄新增 `optional` 欄位、不重建快照 | 不在範圍 | `catalogue.py`、`data/nf-core-modules.json` | 看 diff；跑 `test_catalogue.py` | 兩者沒有變動；目錄記錄仍無 `optional` 欄位；沒接的輸入只給 warning 不給 error（見 TC-036） | 自動 |
| TC-109 | 不做：存檔時不自動驗證 | 不在範圍 | A 剛 `create_pipeline`，再 `update_pipeline` | 查 `pipeline_validations` 表 | 表裡沒有任何列（存檔行為不變） | 自動 |
| TC-110 | 不做：不自動重驗過期結果、不排程 | 不在範圍 | 已驗證過，之後用換了 sha 的目錄呼叫 `get_validation`（見 TC-061） | 查表前後 | `get_validation` 沒有寫入、沒有重算；表裡該列（含 `validated_at`、`result_json`）逐位元不變 | 自動 |
| TC-111 | 不做：不做 `NO_ENTRY`、`nextflow_schema.json` 檢查；裁決二 1（刪掉 PARAM_KEY／PARAM_VALUE） | 不在範圍 | 本檔所有夾具與壞圖（含壞參數、壞型別、環） | 收集所有 `validate` 回傳的 `code` | 全部 `code` 只落在 `GRAPH_STALE`、`META_MISMATCH`、`TYPE_MISMATCH`、`PATTERN_MISMATCH`、`MIXED_SOURCES`、`OPEN_INPUT`、`DUPLICATE_PROCESS` 七種；沒有 `NO_ENTRY`、`PARAM_KEY`、`PARAM_VALUE` | 自動 |
| TC-112 | 不做：不做畫面、不做 launch 的擋關、不做分享 | 不在範圍 | 本任務的 diff | 驗收者讀 diff | 沒有任何程式讀取 `validation.ok` 去擋 launch；沒有畫面、分享相關改動；`validate_pipeline`／`get_validation` 只在 `pipelines.py` 內定義與測試中被呼叫 | 手動：驗收者讀 diff |
| TC-113 | 範圍：檔案（最終版，只准改這些）；不准動清單 | 不在範圍 | `git diff --stat <base>...HEAD` | 驗收者讀 diff | 只含 `validate.py`、`actions/pipelines.py`、兩個新測試檔、`test_pipelines_store.py`、`fixtures/validate/`、`docs/PLATFORM.md`、`specs/017c-validate/ledger.md`；`store.py`、`jobs.py`、`abf_station/`、`compose.py`、`catalogue.py`、`data/nf-core-modules.json`、`actions/__init__.py`、`mcp_server.py`、`web.py`、`pyproject.toml`、`constraints.txt` 沒有變動 | 手動：驗收者讀 diff |
| TC-114 | 「允許更新的既有斷言」（只有那一處可改） | 不在範圍 | 既有測試檔與 base 比較 | 驗收者比對 diff | 既有測試只有 `test_pipelines_store.py` 的「五個公開函式」那一條改成七個（名稱可同步改）；沒有其他既有斷言被移除、放寬、跳過；`spec`／`test-case*.md` 沒被改 | 手動：驗收者比對 diff |

## 憲法與安全網

本任務新增檔案、新增一張表、新增純函式，但明確不啟動程式、不碰站台與叢集。可能碰到的條目：原則 1（新增東西要說明現有工具為何不夠）、原則 2（平台不啟動程式）、原則 3（沒有個人路徑與叢集路徑）、憑證形狀檢查。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-115 | 原則 1；裁決 10；`test_scope.py` TC-070 | 功能 | 新檔 `validate.py`、`test_validate.py`、`test_pipelines_validation.py` | 跑 `test_scope.py` | 三個檔前 40 行都有 `# Nothing existing: …`，理由 15 字以上；測試綠 | 自動：`test_scope.py` |
| TC-116 | 原則 2；`test_scope.py` TC-071 | 功能 | `abf_platform/**/*.py`（含 `validate.py` 的註解與 docstring） | 跑 `test_scope.py` | 不出現 `nextflow run`、`subprocess`、`threading`、`while True` 等；測試綠 | 自動：`test_scope.py` |
| TC-117 | 原則 3；`test_scope.py` TC-072 | 功能 | `fixtures/validate/` 底下所有檔案 | 跑 `test_scope.py` | 沒有叢集路徑形狀、沒有個人路徑；測試綠 | 自動：`test_scope.py` |
| TC-118 | 憑證形狀檢查；`test_launch_static.py` TC-074 | 功能 | 新增的程式與夾具 | 跑 `test_launch_static.py` | 沒有金鑰形狀的字串；測試綠 | 自動：`test_launch_static.py` |
| TC-119 | 完成標準（全套綠） | 功能 | 實作完成 | 跑 `platform/tests` 全套（含 `test_http_site_samplesheet.py`、`test_web_parity.py`、`test_catalogue.py`、`test_guidance.py` 與工具數斷言） | 全套綠；這些既有測試沒有被改動來配合新輸出 | 自動 |
