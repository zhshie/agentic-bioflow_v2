# 測試案例總覽：017c 畫布組合的靜態檢查——型別、未接輸入、重名，結果依版本存起來（純後端）

狀態：合約已確認（2026-10-24，verifier）

**規格**：`specs/017c-validate/plan.md`（沒有 spec.md）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 發現清單的形狀、順序與可重複 | 14 | 0 | 0 | 14 |
| US2 — 邊兩端的型別對不對 | 12 | 0 | 0 | 12 |
| US3 — pattern、混接、沒接的輸入、重名 | 17 | 0 | 0 | 17 |
| US4 — 圖對不上現在的目錄與參數 | 4 | 5 | 0 | 9 |
| US5 — 結果依版本存下來、讀出來、標記過期 | 17 | 1 | 0 | 18 |
| US6 — 擁有者、不經確認、不啟動程式 | 6 | 8 | 0 | 14 |
| US7 — 夾具與標準答案 | 14 | 0 | 0 | 14 |
| US8 — 文件與交付 | 5 | 0 | 0 | 5 |
| US9 — 這次不做的事 | 0 | 0 | 11 | 11 |
| 憲法與安全網 | 5 | 0 | 0 | 5 |
| **合計** | 94 | 14 | 11 | 119 |

自動驗證 111 條、手動驗證 8 條（TC-008 讀排序鍵原始碼、TC-097 讀 ledger 並獨立重推標準答案、TC-099／TC-100 讀 `docs/PLATFORM.md`、TC-102 讀 PR 說明、TC-103 讀 ledger、TC-112／TC-113 讀 diff）。TC-114 也要求驗收者比對既有測試與 base，但列為手動；上面手動數已含它，所以實際手動為 9 條、自動 110 條。

> 更正：手動共 9 條（TC-008、097、099、100、102、103、112、113、114），自動 110 條，合計 119。

## 請你判斷的三件事

1. **每條是不是你要的？** 重點看 US2（型別不合的邊要被抓到並點名兩端，TC-016、TC-019、TC-026、TC-096）與 US3 的 TC-036 到 TC-040（沒接的輸入只是 warning，不是 error，所以黃金圖 `ok` 仍為 True）。
2. **有沒有漏掉的出錯情況？** 想像實驗室成員會怎麼用錯它：驗證別人的組合（US6）、存下的圖在目錄更新後失效（US4、TC-061）。
3. **「不在範圍」對嗎？** 這次不跑 lint／空跑、不開 MCP 工具與網頁、不擋 launch、不在存檔時自動驗證（US9）；這些留到 017c2、017d、017e。

## 覆蓋檢查

- 計畫作法 A（發現的形狀與順序）、B（B1 到 B7；B8 已被裁決二取代）、C（儲存與兩個函式）、D（不需要 migration）共 4 節，全部都有測試案例：是（A→TC-001 至 TC-014；B1～B3→TC-015 至 TC-026；B4～B7→TC-027 至 TC-043；GRAPH_STALE 與參數→TC-044 至 TC-052；C→TC-053 至 TC-084；D→TC-065、TC-066、TC-102）
- 維護者原話共 6 句，全部都有測試案例：是（驗證是獨立一步、不改圖→TC-012、TC-067；總表 017c「有 error 不能 launch」→TC-005、TC-054、TC-026；總表 017b「型別不合的邊被拒並點名兩端」→TC-016、019、026、096；裁示 9 不經確認→TC-077；憲章原則 2 不啟動程式→TC-083、084、116；擁有者規則→TC-071 至 TC-076）
- 計畫的 17 條 `test_validate.py` 失敗先行測試與 12 條 `test_pipelines_validation.py` 失敗先行測試，全部都有對應 TC：是（`test_golden_good_graph_is_ok_with_one_open_input_warning`→TC-001、002、087、088；`test_type_mismatch_names_both_ends`→TC-016、019；`test_meta_mismatch_is_reported_and_not_also_a_type_mismatch`→TC-018；`test_tuple_with_more_elements_is_compatible_by_class`→TC-015；`test_any_and_unknown_types_…`→TC-023、024；`test_pattern_…`→TC-027 至 031；`test_mixed_sources_…`、`test_compatible_sources_…`→TC-032 至 035；`test_open_inputs_…`→TC-036 至 040；`test_open_inputs_list_matches_compose_render`→TC-013；`test_stale_graph_…`→TC-044 至 052；`test_duplicate_process_…`→TC-041 至 043；`test_param_rules_agree_with_normalize`→TC-048、049；`test_findings_are_in_a_fixed_order_and_repeatable`→TC-006、007、009；`test_every_finding_is_bilingual_…`→TC-011；`test_tc118_…`→TC-025、026；`test_validate_module_is_pure`→TC-084；`test_validate_never_mutates_its_input`→TC-012；儲存側 12 條→TC-053 至 TC-083）
- 計畫「允許更新的既有斷言」兩處、「必須確認仍綠」各項，全部都有 TC：是（TC-066、068、069、082、101、104 至 108、115 至 119）
- 計畫裁決 11 條＋裁決二 4 條，全部都有 TC：是（裁決 1→TC-077；2→TC-106、102、103；3→TC-036 至 040、108；4→TC-015、021 至 023；5→TC-061、110；6→TC-051；7→TC-023、024；8→TC-010；9→TC-099 至 101；10→TC-115；11 無待確認事項；裁決二 1→TC-048、049、111；2→TC-030、031、087；3→TC-095、097、098；4→TC-041、042）
- 計畫「不做」共 9 條（MCP／網頁／`actions/__init__.py`、不跑 lint 等與不加 job 種類、不改 `compose.py`、不要求 `optional` 欄位與重建快照、不自動驗證、不自動重驗、不做 NO_ENTRY 與 schema 檢查、不做畫面與 launch 擋關與分享），全部都有「不在範圍」測試案例：是（TC-104 至 TC-113；TC-114 另防既有測試被削弱）
- 專長守則（backend）適用項：對等性（使用者可見動作與動作層函式兩邊一一對應）本版沒有使用者可見的動作，改以 TC-068、TC-104、TC-105 證明兩個新函式只在動作層檔案、公開清單恰為七個、沒有被匯出成工具或路由；跨使用者讀與寫各一條→TC-071、TC-072（TC-073 至 075 補同句話與不留痕）；確認管道→裁決 1 判為不適用，以 TC-077、082、083 證明沒有送出路徑也沒有產生工作；錯誤訊息與日誌→TC-079 至 081；migration→TC-065、066、102。
- 夾具三組（`good_fastqc_multiqc`、`bad_edges`、`open_inputs_twins`）與標準答案：是（TC-085 至 TC-098）

## 我（撰寫者）不確定的地方

1. 計畫 B3 字面上「兩邊 classes 都是空集合」也算不相交；這與「一邊空、另一邊不空」的原意不一致。兩邊都空算不算 TYPE_MISMATCH？（沒有出 TC，因為計畫沒寫。）
2. 計畫沒寫 channel 為 null 的發現要排在哪裡；排序 TC 只涵蓋計畫寫明的部分（TC-007、TC-008）。
3. 計畫沒寫 GRAPH_STALE 時 `open_inputs` 是什麼（空清單？），也沒寫存下的圖「打不開」（內容壞掉）時用哪個 code。TC-044 至 052 不檢查這兩點。
4. DUPLICATE_PROCESS 發現的 `node`／`channel` 要填什麼計畫沒寫；TC-041、042 只檢查 code、嚴重度與 `ok`。
5. `graph_sha256` 欄位怎麼算計畫沒寫；TC-064 只要求它不是空字串。
6. 同一條邊若 META_MISMATCH，能不能另外又得到 PATTERN_MISMATCH，計畫沒寫；bad_edges 的完整標準答案由 executor 手推、驗收者獨立重推（TC-095、TC-097）。`bad_edges.json` 的合成目錄放在哪個檔案、`d` 輸入 1 的記錄長相，也由 executor 決定並在 ledger 記錄。
7. 計畫 test_no_program_is_started_by_validation 要求 `pipelines.py` 不含 `nextflow`，但既有的 `render_pipeline` docstring 含小寫 `nextflow.config`。TC-083 把範圍寫成「本任務新增的部分＋整個 validate.py」；改寫該 docstring 或排除它都可，字樣清單不得放寬。
8. 計畫上文（A 節的 PARAM_KEY／PARAM_VALUE、「標準答案由 developer-agent 手算」）已被裁決二取代；本合約一律依裁決二。
9. `docs/TESTING.md` 沒有本任務手動項目的步驟，手動 TC 由驗收者直接讀 ledger、PR 說明、diff 與文件。

## 核可紀錄

（尚未經維護者本人審閱；此為 verifier 依 plan 出題的合約。）
