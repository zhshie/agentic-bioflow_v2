---
id: 017c-validate
title: 驗證畫布上的組合：邊兩端型別對不對、必接的輸入接了沒、參數與名字有沒有問題（只做後端、只做靜態檢查，空跑與 lint 留到站台側另一張票）
tier: B
kinds: backend
lane: L5
base: v3
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 4（017c）；依 017a（PR #172，已合）的 catalogue.py 與 017b（PR #173）的 compose.py、actions/pipelines.py
---

# 017c-validate

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/017c-validate/plan.md`。**只處理本任務**。
> ⚠️ **前置：必須等 PR #173（017b，分支 `feat/017b-compose`）合進 `v3` 之後，才從最新的 `origin/v3` 開分支。** 本任務要改的 `actions/pipelines.py`、要讀的 `compose.py`、要引用的測試與夾具都只存在於 #173。#173 還沒合就開工 → 立刻 BLOCKED，不要自己 cherry-pick。
> 與 017a／017b 同一個原則：**不新增 MCP 工具、不加網頁路由、不碰 `actions/__init__.py`**——對外的名字留到 017e 一次開。
> 與總表（replan 第 157 行）的差異全部列在「裁決」，以「裁決」為準：本任務**只做靜態檢查，不做 `nextflow lint`、`-stub-run`、nf-test，也不加新的 job 種類**。

## 目標
給一張已存下來的組合圖（某個 pipeline 的某個版本），回一份**確定性的發現清單**：每一項是 `{node, channel, code, severity, message}`，message 同時有中文與英文、並說明怎麼改。檢查的是「這張圖接得對不對」：邊兩端的通道型別相不相容、輸入有沒有接、名字會不會撞、現在的目錄還認不認得這張圖。最新一次結果跟著該版本存起來（存在一張新的、第一次使用時才建的表），017d（launch 前擋 error）與 017e（右欄顯示）直接讀。**純函式＋讀寫平台自己的資料庫；不啟動任何程式。**

## 維護者原話（verifier 出題用）
- 「拖模組、連線、填參數、驗證、送去跑、匯出 zip、版本紀錄與分享；不做巢狀子流程。」（10-21 裁示 5）→ 「驗證」是獨立的一步，輸入是已存的版本，輸出是人看得懂的結果；不改圖本身。
- 總表 017c：「done：三閘門結果顯示在版本頁；lint 失敗的版本不能 launch。」→ 本任務交出「結果的資料與規則」（有 error 的版本 `ok` 為 False，供 017d 擋）；版本頁畫面是 017e。
- 總表 017b 失敗先行：「型別不合的邊被拒並點名兩端。」（017b 裁決 2 已移到本任務）→ 型別不合的邊要被回報，並**點名邊的兩端**（來源節點＋輸出通道、目的節點＋輸入編號）。
- 裁示 9：「自訂 pipeline 的空跑驗證不需本人按確認：它只寫到平台自己的 `pipelines/` 目錄、不花 SU」→ 本任務的驗證**同樣不經確認管道**（只寫平台自己的資料庫；理由見裁決 1）。
- 憲章原則 2（`test_scope.py` TC-071）：平台不啟動程式 → `nextflow lint`／`-stub-run` 若要做，只能是站台代理接的 job（裁決 2）。
- 擁有者規則（`docs/PLATFORM.md` 第 440 行起「Whose it is」）：「a caller sees and uses only their own」，別人的與不存在的回一樣的話。

## 範圍：檔案（最終版，只准改這些）
- `platform/abf_platform/validate.py`（新：純函式，不碰資料庫、不碰網路、不 import `store`；只 import `catalogue`、`compose`）
- `platform/abf_platform/actions/pipelines.py`（改：加表 `pipeline_validations` 與兩個函式 `validate_pipeline`、`get_validation`；**不**在 `actions/__init__.py` 匯入）
- `platform/tests/test_validate.py`（新：純函式）
- `platform/tests/test_pipelines_validation.py`（新：儲存、擁有者、過期）
- `platform/tests/test_pipelines_store.py`（改：只改「允許更新的既有斷言」列的兩處）
- `platform/tests/fixtures/validate/`（新：`good_fastqc_multiqc.json`、`bad_edges.json`、`open_inputs_twins.json` 三張圖，各附手算的標準答案 `*.expected.json`）
- `docs/PLATFORM.md`（`## Composed pipelines` 補一段「Validation」；stores 表補一列；見裁決 9）
- `specs/017c-validate/ledger.md`（新，executor 進度帳本）

**不准動**：`store.py`（不加表、不改 `STATE_SCHEMA`、不改 jobs 的 CHECK）、`jobs.py`、`abf_station/*`、`compose.py`、`catalogue.py`、`data/nf-core-modules.json`、`actions/__init__.py`、`mcp_server.py`、`web.py`、`pyproject.toml`、`constraints.txt`。

## 作法

### A. 一份發現的形狀（`validate.py`）
```json
{"node": "report", "channel": 0, "code": "TYPE_MISMATCH", "severity": "error",
 "message": "中文原因與做法 (English reason and what to do)"}
```
- `node`：節點 id；與整張圖有關的（例：環、圖打不開）為 `null`。`channel`：輸入編號（整數）或輸出通道名（字串）；沒有就 `null`。邊的問題以**目的節點與輸入編號**為 `node`／`channel`，**來源端寫進 message**（例：`邊 qc.html → s.2`）。
- `severity`：`"error"`（`ok` 變 False）或 `"warning"`（只顯示）。
- **決定性順序**：`(severity 的順序 error 先於 warning, node 空字串在最前, channel 整數先於字串再依值, code, message)`。同一張圖同一份目錄永遠逐字相同的清單。
- `validate(canonical, data=None) -> {"ok": bool, "checks": ["static"], "catalogue_sha": str, "findings": [...], "open_inputs": [...]}`。`ok` ＝ 沒有任何 error。`checks` 現在固定 `["static"]`，將來站台側的檢查（lint／空跑）往裡加，是加法。`open_inputs` 與 `compose.render` 回的同形、同排序（直接用 `compose` 的函式算，不重寫）。`data` 預設 `catalogue.load()`。

### B. 檢查項目（每項對應一個 `code`）
輸入 `canonical` 是 `compose.normalize` 的輸出（存下來的就是它）。**第一步**：用**現在**的目錄再跑一次 `compose.normalize`；有 problem（模組已不在目錄、sha 不等於現在的快照、通道已消失……）→ 每條 problem 變一項 `GRAPH_STALE`（error，`node=None`，message 就用 problem 原文，已是中英），**其餘檢查不跑**（圖本身對不上目錄，後面的結果沒意義）。

之後依序（全部只讀目錄的 `inputs[]`／`outputs[]` 記錄 `{channel, name, type, pattern}`；**目錄記錄沒有 `meta` 欄位或 `optional` 欄位**，meta 的判斷見 B1）：

1. **通道簽名**。把一個通道（同一個 `channel` 的所有記錄，依目錄順序）化成 `(has_meta, classes)`：
   - 型別類別：`map`→`meta`；`file`、`directory`→`path`；`string`、`boolean`、`integer`、`float`→`val`；`list` 或型別缺漏／不認得→`any`。
   - `has_meta`：該通道**第一筆**記錄的類別是 `meta`（nf-core 慣例：`meta`、`meta2`… 是 `map`，排在 tuple 第一格）。
   - `classes`：其餘記錄的類別集合。
2. **`META_MISMATCH`（error）**：邊兩端 `has_meta` 不同（一邊是 `[meta, 檔案]` 的 tuple、另一邊是單一值）→ 點名兩端並說「中間需要一個轉換節點」。每條邊最多回一項型別類的發現：先 B2，B2 發現了就不再做 B3。
3. **`TYPE_MISMATCH`（error）**：兩端 `has_meta` 相同，但 `classes` 不相交、且兩邊都不含 `any`；或一邊 `classes` 為空、另一邊不空。**嚴格比較「元素個數」會把黃金例子 fastqc `zip`（2 筆）→ multiqc 輸入 0（6 筆：meta＋5 個檔）擋掉，所以只比類別集合，不比個數**（理由見環境事實）。
4. **`PATTERN_MISMATCH`（warning）**：兩端都有 `pattern`，把兩個 pattern 各取出副檔名集合（`{a,b}` 展開、去掉 `*`、`.`、前導 `_`；取不出就不比），集合不相交 → warning（pattern 是文件字串不是保證，故不當 error）。
5. **`MIXED_SOURCES`（error）**：同一個輸入通道接了多條邊（會被渲染成 `.mix()`），而來源通道的簽名彼此不相容（`has_meta` 不同，或 `classes` 兩兩不相交）。
6. **`OPEN_INPUT`（warning）**：沒有任何邊接到的輸入通道（`node`＝節點、`channel`＝編號，message 列該通道的輸入名）。**不是 error**：入口節點（例：fastqc 的 reads）本來就沒有上游，要等 017d 的樣本表對應才填；而目錄**沒有**記錄哪個輸入是 optional（見裁決 3）。message 分兩種寫法：節點完全沒有進來的邊＝「入口，送出時要由樣本表或參數供應」；節點有別的進邊、只有這個通道沒接＝「少了一個輸入，確認是否可省略」。
7. **`DUPLICATE_PROCESS`（error）**：渲染後 process 名或別名撞名。算法完全用 `compose` 現成的 `process_name` 與別名規則（同模組多節點用 `<PROCESS>_<ID大寫>`），檢查：不同模組的 process 名相同、或別名與別的 process 名／別名相同。（目錄現況不重複，故多半是 `s1`／`S1`、`a_b`／`a_B` 這類情形；`id` 規則本身已排除大寫，但別名拼接仍可能撞，測試要覆蓋。）
8. **`PARAM_KEY`、`PARAM_VALUE`（error）**：重跑 `compose` 的參數規則（鍵白名單、字串、長度、控制字元）。正常情況 `normalize` 已擋，這裡是**第二道**（存下來的舊版若遇到之後收緊的規則仍會被抓到）。直接呼叫 `compose` 內的 `_check_params` 的做法不可取（私有函式）；**用 `compose.normalize` 的 problem 文字不夠細**，所以由 `validate.py` 自己依同一份正規式判斷，並由測試鎖住兩邊一致（`test_param_rules_agree_with_normalize`）。

訊息格式比照 017b：中文在前、英文放括號、說怎麼改。範例：`邊 qc.html → s.2：輸出是 [meta, 檔案]，輸入 index_format 是單一字串，型別對不上；中間加一個轉換節點，或改接別的通道 (edge qc.html → s.2: the output is [meta, file] but input index_format is a single string; add a conversion node or wire another channel)`。

### C. 儲存（`actions/pipelines.py`）
加在 `_TABLES`（與 017b 同一套 `CREATE TABLE IF NOT EXISTS`，`_table(con)` 會一起建）：
```sql
CREATE TABLE IF NOT EXISTS pipeline_validations (
    pipeline_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    graph_sha256 TEXT NOT NULL,
    catalogue_sha TEXT NOT NULL,
    result_json TEXT NOT NULL,
    validated_at REAL NOT NULL,
    PRIMARY KEY (pipeline_id, version)
);
```
沒有外鍵：`pipeline_versions` 的觸發器只擋該表自己；這張表是「最新結果」可被覆蓋的衍生資料（`INSERT OR REPLACE`），**刻意不放進 `pipeline_versions`**，因為那張表有「不准 UPDATE」的觸發器（017b 裁決 8），而且版本內容本來就該不可變，驗證結果會隨目錄快照更新而改變。讀取一律先經 `_mine`（擁有者過濾），不靠外鍵。

函式（沿用 017b 的簽名慣例；`pipelines.py` 現有 5 個公開函式變 7 個）：
- `validate_pipeline(platform_path, pipeline_id, version=None, *, caller=None, data=None, clock=time.time) -> dict`：`get_pipeline`（別人的與不存在的同一句 `找不到這個組合`）→ `validate.validate(graph, data)` → `INSERT OR REPLACE` 一列 → 回 `{"ok": True, "id", "name", "version", "validation": {<validate 的結果>, "validated_at", "stale": False}}`。注意外層 `ok` 是「這次呼叫成功」，裡面 `validation.ok` 才是「圖有沒有 error」。不寫檔、不排工作、不呼叫 `confirm`。
- `get_validation(platform_path, pipeline_id, version=None, *, caller=None, data=None) -> dict`：只讀。沒驗證過 → `{"ok": True, "validation": None, ...}`；有存 → 回存的結果，並加 `"stale": <目前目錄 sha ≠ 存的 catalogue_sha>`（`stale` 時 UI 應提示重新驗證，**不自動重算**；拿它擋 launch 的 017d 要自己呼叫 `validate_pipeline`，見裁決 5）。找不到與擁有者規則同 `get_pipeline`。
- 這兩個函式與表**不含** `confirm`、`jobs`、`queue`、`subprocess` 等字樣（`test_pipelines_store_has_no_submit_path` 會掃 `pipelines.py` 原始碼；寫註解也別用）。

### D. migration
**不需要 migration。** 理由與 017b 相同：只新增一張全新的表，由 `CREATE TABLE IF NOT EXISTS` 在第一次使用時建立；沒有改任何既有表或欄位（`STATE_SCHEMA`、`jobs` 的 CHECK 都不動）；舊的 `platform.db` 原樣可用。PR 說明要寫：`connect_state()` 之後這張表不一定存在，讀取函式自己先建表（`_table`）。

## 夾具與標準答案（developer-agent 準備；executor 原樣放進 `fixtures/validate/`）
**單元測試不依賴真實目錄的細節**：`test_validate.py` 用小型的合成目錄 dict（形狀同 `catalogue.load()`，只放 3～5 個手寫模組，欄位 `name`／`path`／`inputs`／`outputs`），這樣型別規則的每個分支都能精準覆蓋；只有「黃金例」與 TC-118 對照用真實目錄。

- `good_fastqc_multiqc.json`＝017b 的 `fixtures/compose/fastqc_multiqc/graph.json`（fastqc `zip` → multiqc 輸入 0）。預期（真實目錄）：`ok` 為 True、`findings` 恰好一項：`{"node": "qc", "channel": 0, "code": "OPEN_INPUT", "severity": "warning", message: …}`（message 為「入口」那一種）；`open_inputs` ＝ `[{"node": "qc", "input": 0, "names": ["meta", "reads"]}]`。
- `bad_edges.json`（合成目錄）：`a`（輸出 `out`：`[map, file]`）接 `b` 的輸入 0（`[file]`，無 meta）→ `META_MISMATCH`；`a` 接 `c` 的輸入 0（`[map, string]`）→ `TYPE_MISMATCH`；`d` 的輸入 1 同時接 `a.out`（`[map, file]`）與 `e.out`（`[file]`）→ `MIXED_SOURCES`；另有一條 pattern 為 `*.{bam}` 接 `*.{vcf}` 的邊 → `PATTERN_MISMATCH`。標準答案由 developer-agent 手算。
- `open_inputs_twins.json`＝017b `fan_in_and_twins` 的圖：六個 `OPEN_INPUT`（`s1`、`s2` 各通道 0、1、2；`s1`、`s2` 為入口節點）；`multiqc` 輸入 0 已接。順序固定為 `s1:0, s1:1, s1:2, s2:0, s2:1, s2:2`。
- 標準答案不得由程式輸出反推（同 017b）。

## 失敗先行測試（現在都會紅）

**`platform/tests/test_validate.py`**（純函式，不需資料庫）
- `test_golden_good_graph_is_ok_with_one_open_input_warning`：真實目錄下 fastqc→multiqc：`ok` True、findings 如上、`checks == ["static"]`、`catalogue_sha` 等於快照 sha。
- `test_type_mismatch_names_both_ends`：`TYPE_MISMATCH` 的 message 同時含來源 `節點.通道` 與目的 `節點.編號`；`node`／`channel` 是目的端。
- `test_meta_mismatch_is_reported_and_not_also_a_type_mismatch`：同一條邊只出一項型別類發現。
- `test_tuple_with_more_elements_is_compatible_by_class`：fastqc `zip`（2 筆）→ 6 筆的合成輸入，只要類別集合相交就通過（鎖住「不比個數」）。
- `test_any_and_unknown_types_are_compatible_with_anything_but_meta_must_still_match`。
- `test_pattern_mismatch_is_a_warning_and_does_not_fail_ok`；`test_pattern_that_cannot_be_parsed_is_skipped`。
- `test_mixed_sources_on_one_input_are_checked_pairwise`、`test_compatible_sources_mix_without_a_finding`。
- `test_open_inputs_are_warnings_never_errors_and_entry_nodes_say_so`：入口節點與「少一個輸入」的 message 不同；`ok` 仍為 True。
- `test_open_inputs_list_matches_compose_render`：`validate` 回的 `open_inputs` 與 `compose.render` 回的逐項相同。
- `test_stale_graph_stops_after_the_graph_check`：合成目錄移掉一個模組 → 只有 `GRAPH_STALE`（每條 problem 一項、含中英），沒有後面各項。
- `test_duplicate_process_names_and_alias_collisions`：合成目錄兩個模組 path 轉大寫後相同；以及別名撞名。
- `test_param_rules_agree_with_normalize`：用 017b `test_param_keys_and_values_are_restricted` 的同一批壞值，`validate` 與 `normalize` 對「合法／不合法」的判定一致。
- `test_findings_are_in_a_fixed_order_and_repeatable`：同一張圖打亂節點／邊順序先 `normalize` 再 `validate` ×2，清單逐項相等；順序鍵如 A 節。
- `test_every_finding_is_bilingual_and_says_what_to_do`：每項 message 含中文字與 ASCII 英文括號段。
- `test_tc118_still_holds_for_normalize_but_validate_flags_it`：`normalize` 仍接受 fastqc `html` → samtools_sort 輸入 2（017b 的 TC-118 不變）；`validate` 對同一張圖回 `META_MISMATCH`（error），`ok` 為 False。
- `test_validate_module_is_pure`：`validate.py` 原始碼不含 `import store`、`sqlite3`、`urllib`、`requests`、`socket`、`subprocess`、`open(`、`nextflow`、`lint`、`stub`（沒有任何啟動程式的字樣）。
- `test_validate_never_mutates_its_input`：呼叫前後 `canonical` 深度相等。

**`platform/tests/test_pipelines_validation.py`**（雙使用者夾具，仿 `test_pipelines_store.py`）
- `test_validate_pipeline_stores_and_get_validation_returns_it`：同一份結果；`validated_at` 用注入的 `clock`。
- `test_get_validation_before_any_validation_is_none_not_an_error`。
- `test_revalidating_replaces_the_row_and_keeps_one_row_per_version`：同版本驗兩次 → 該表 1 列；新版本另一列；舊版本結果不被動到。
- `test_stored_result_is_stale_when_the_catalogue_sha_changes`：用 `data=` 傳入換了 `sha` 的目錄 → `stale` 為 True，且 `get_validation` 不自動重算。
- `test_other_user_cannot_validate_or_read_a_validation`：B 對 A 的組合 `validate_pipeline`、`get_validation` 都得 not found；`words(別人的訊息) == words(不存在的訊息)`；A 的表仍沒有 B 寫的列。
- `test_terminal_caller_none_sees_everything`。
- `test_validate_makes_no_confirmation_or_job`：前後 `jobs`、`confirmations`、`launches` 列數不變（仿 017b `test_no_confirmation_or_job_is_made`）。
- `test_validation_table_is_lazy_and_old_db_works`：沒有該表的舊庫直接 `get_validation` → `validation: None`、不丟例外；之後 `validate_pipeline` 成功；`STATE_SCHEMA` 不含 `pipeline_validations`。
- `test_pipeline_versions_stay_append_only`：驗證後 `pipeline_versions` 對 `UPDATE`／`DELETE` 仍被擋，且 `graph_json` 逐位元不變。
- `test_validation_columns_say_nothing_about_runs`：欄位恰為上面 SQL 的六個。
- `test_error_messages_hide_internals`：被拒回應與日誌不含 SQL、堆疊、`platform.db` 路徑。
- `test_no_program_is_started_by_validation`：`pipelines.py`、`validate.py` 原始碼不含 `subprocess`、`os.system`、`sbatch`、`nextflow`、`lint`、`stub`（仿 tc078）。

## 允許更新的既有斷言
017b 的測試要動的**只有兩處**，且只准照下面改：
- `platform/tests/test_pipelines_store.py::test_only_five_public_functions_and_none_in_the_actions_package`：期望名單從 5 個改成 7 個（加 `get_validation`、`validate_pipeline`，依字母排序），函式名稱可同步改成 `test_only_seven_…`。其餘邏輯（「不在 `actions` 套件」）不變。
- `platform/tests/test_pipelines_store.py::test_pipelines_columns_say_nothing_about_runs`：**不改**（它只比 `pipelines`、`pipeline_versions` 兩表的欄位，新表的欄位由 `test_validation_columns_say_nothing_about_runs` 鎖）；列在這裡是提醒 executor 跑一次確認仍綠。

**必須確認仍綠、不准改**：
- `platform/tests/test_compose.py::test_types_are_not_compared`（TC-118）：`normalize` 仍不比型別，本任務沒動 `compose.py`。若它變紅，代表有人把型別檢查塞進 `normalize` → 退回去。
- `platform/tests/test_pipelines_store.py::test_old_platform_db_works_without_a_migration`（會 `DROP TABLE pipelines`／`pipeline_versions`）：新表無外鍵，不影響 DROP。
- `test_pipelines_store.py::test_pipelines_store_has_no_submit_path`：新增的程式碼與註解不得含 `confirm`、`jobs`、`queue`、`subprocess`、`os.system`、`sbatch`、`srun`、`qsub`。
- `test_pipelines_store.py::test_the_files_owned_by_other_work_do_not_mention_pipelines`：`store.py` 等不含 `pipeline_versions` 等字，本任務不碰它們。
- `test_http_site_samplesheet.py::test_tc057_no_table_or_column_changed`（`SCHEMA_SHA256`）、`test_web_parity.py`、`test_catalogue.py`、`test_guidance.py`、工具數斷言：不牽動。
- `test_scope.py` TC-070（`validate.py`、兩個新測試檔前 40 行要有 `# Nothing existing: …`，理由 ≥15 字）、TC-071（`abf_platform/**/*.py` 含註解與 docstring 都不得出現 `nextflow run`、`subprocess`、`threading`、`while True` 等；**注意 `validate.py` 的說明文字也別寫 `nextflow run`**）、TC-072（fixtures 底下不得有叢集路徑形狀）、`test_launch_static.py` TC-074（金鑰形狀）。
- `bash tests/platform_storage_doc_test.sh`：stores 表加一列後要跑一次（見裁決 9）。

## 完成標準（done when）
- 對 017b 黃金圖（fastqc→multiqc）存下後 `validate_pipeline` 得 `validation.ok` 為 True、findings 如夾具；對含 html→`index_format` 那條邊的圖得 `ok` 為 False 且 message 點名兩端。
- 上面所有測試綠；全套 `platform/tests` 綠；`bash tests/platform_storage_doc_test.sh` 綠。
- `git diff --stat` 只含「範圍：檔案」列的路徑；`store.py`、`jobs.py`、`abf_station/`、`compose.py`、`actions/__init__.py` 沒有變動。
- PR 說明寫明：不需要 migration 的理由、新表可能不存在、與總表 017c 的差異（裁決 2、3）、以及「站台側的空跑與 lint 另開一張票」。
- 手動（不在本任務）：對真實模組檔跑 lint／空跑。ledger 記「未驗證」。

## 環境事實
- 目錄記錄形狀（`platform/abf_platform/catalogue.py:15-105`，`_entry`、`_inputs`、`_outputs`、`flatten`）：`inputs[]`＝`{channel: 整數, name, type, pattern}`，`outputs[]`＝`{channel: 輸出名字串, name, type, pattern}`；**沒有 `meta` 欄位、沒有 `optional` 欄位**（`_entry` 只取 `type`、`pattern`）。meta 是名字為 `meta`／`meta2`… 且 `type` 為 `map` 的那一筆，排在該通道第一格（例：`fastqc` 輸入 0＝`[meta(map), reads(file)]`、輸出 `zip`＝`[meta(map), *.zip(file, pattern "*_{fastqc.zip}")]`；`multiqc` 輸入 0＝`[meta(map), multiqc_files, multiqc_config, multiqc_logo, replace_names, sample_names]`，全部 `file`）。
- 目錄快照（`platform/abf_platform/data/nf-core-modules.json`，sha `5ed90b42e78410e7411e9c6bdfeff33226d6c58e`，2116 個模組）所有輸入輸出記錄的 `type` 分布：`file` 10547、`map` 8512、`string` 572、`directory` 519、`boolean` 195、`integer` 164、`list` 90、`float` 47；`pattern` 有值的約 10462 筆。這是為什麼 B1 用「類別」而不是原字串，並把 `list` 當 `any`。
- 為什麼不比元素個數：黃金例 fastqc→multiqc 兩端個數不同（2 對 6），而 `test_compose.py::test_fastqc_multiqc_renders_the_golden` 要求它通過。
- 017b 已有的東西（`origin/feat/017b-compose`，PR #173）：`compose.py` 的 `normalize`（形狀與通道存在檢查）、`process_name`、`render`（回 `open_inputs`）、私有 `_outputs`／`_inputs`／`_order`、`graph_json`；`actions/pipelines.py` 的 `_TABLES`、`_table`、`_mine`、`_latest`、`_no`、`_not_found`、五個公開函式；夾具 `platform/tests/fixtures/compose/*`。ledger「給 017c 的備忘」三條：`-stub-run` 閘門要看 `open_inputs`（本任務把它變成 `OPEN_INPUT` 發現；閘門本身在站台側票）、型別檢查（本任務）、兩張表不在 `STATE_SCHEMA`（本任務沿用）。
- 站台側的現況（決定「動態檢查延後」的證據，`origin/v3`）：`platform/abf_platform/jobs.py:26`（`DEADLINE_SECONDS` 六種 kind）；`platform/abf_station/handlers.py:16-17`（`JOB_KINDS`、`ARG_KEYS`）；`jobs` 表的 `CHECK (kind IN (…六種…))` 在 `store.py:228`，上一次加 kind（`read_task_log`）時要寫 `_migrate_jobs_kinds`（`store.py:386` 起，重建表、複製資料）——所以**加 `validate_pipeline` 這個 kind 是 `store.py` 的 B 級 migration**，不在本任務範圍。`preflight` 的做法：`jobs.enqueue_preflight`（`jobs.py:169`）→ 站台代理領走 → `take_result` 在 `jobs.py:761` 呼叫 `compute_envs.apply_preflight`；結果存回來靠的是代理主動回報，不是平台去連站台。
- 仿的現成做法：`actions/pipelines.py`（`_table`、`_mine`）；測試 `test_pipelines_store.py` 的雙使用者夾具與 `words()` 比較。
- 文件落點：`docs/PLATFORM.md` 的 `## Composed pipelines`（017b 新增）與 `## What the platform stores`。

## 不做
- 不加 MCP 工具、不加網頁路由、不改 `actions/__init__.py`、`mcp_server.py`、`web.py`（017e）。對外名字（總表的 `validate_pipeline` 工具）與 parity 表留給它。
- **不跑 `nextflow lint`、`nf-core pipelines lint`、`-stub-run`、nf-test**；不加 job 種類、不碰 `jobs.py`／`store.py`／`abf_station/`（裁決 2）。
- 不改 `compose.py`：`normalize` 仍不比型別（TC-118 不變）。
- 不要求目錄新增 `optional` 欄位、不重建快照（那是 A 級 PR，裁決 3 的後續選項）。
- 不在 `create_pipeline`／`update_pipeline` 裡自動驗證（存檔行為不變；要不要「存檔即驗證」是 017e 的產品決定）。
- 不自動重驗過期結果、不排程重驗。
- 不做 `NO_ENTRY` 之類目前不可能發生的檢查；不做 `nextflow_schema.json` 的檢查（017b 也沒生它）。
- 不做畫面、不做 launch 的擋關（017d 讀 `validation.ok`）、不做分享。

## 裁決（預設照本檔，不改方向；與上文衝突時以本段為準）
1. **驗證不經確認管道。** 它只寫平台自己的資料庫、不碰站台、不花 SU、不送出；與 017b 裁決 1、總表裁示 9 同理。仍須有測試證明沒有產生 `jobs`／`confirmations`／`launches` 列（`test_validate_makes_no_confirmation_or_job`）。
2. **動態檢查（lint／`-stub-run`／nf-test）本任務不做，延後到站台側的另一張票（建議 id `017c2-validate-run`，排在 017d 之後）。** 理由，都有出處：①憲章原則 2 與 `test_scope.py` TC-071 禁止平台啟動程式——**連總表寫的「lint 在平台主機（`nf-core pipelines lint --json`）」也違反**，所以 lint 也只能走站台 job，總表這一句要在 spec 更正；②走站台就要新 job kind，而 `jobs` 表的 CHECK 只收六種（`store.py:228`），要重建表的 migration（`store.py:386` 的前例），這屬於 `store.py` 的變動、與本任務「不碰 store」衝突；③`-stub-run` 要有完整的專案目錄（`main.nf`＋所有模組檔）才跑得起來，而 017b 沒有抓模組檔、也沒有打包（`project_tar` 是 017d 的產物）；④沒有模組檔的情況下 `-stub-run` 一定失敗，結果沒有資訊量。**建議的順序：017c（本任務，靜態）→ 017d（打包＋送出）→ 017c2（job kind＋migration＋站台 handler，重用 017d 的 `project_tar`）。** 結果欄位已預留：`checks` 清單與 `validation_json` 同形，之後加 `"lint"`、`"stub_run"` 是加法。
3. **「必接的輸入」本版做成 warning，不做成 error。** 原因：目錄沒有 optional 欄位（`catalogue.py:34` 的 `_entry` 只留 `type`／`pattern`），無法分辨哪個輸入可省略；而且入口節點（例如 fastqc 的 reads）本來就沒有上游，若當 error 則任何圖都過不了。擋與不擋交給 017d：它在送出時用樣本表把入口輸入填起來，仍未填的才擋。**若維護者要「真的必接」**：另開 A 級票，讓 `scripts/snapshot_modules.py` 把 meta.yml 的 `optional: true` 帶進 `inputs[]`，再把 `OPEN_INPUT` 對非 optional 且非入口的通道升為 error（是加法）。
4. **型別比較的粒度＝「類別集合＋是否有 meta」，不是逐元素。** 見環境事實（不比個數）。代價：`file`→`file` 但實際副檔名不對的邊只會得到 `PATTERN_MISMATCH` warning。這是刻意的保守：nf-core 的 `type`／`pattern` 是文件欄位、不是型別系統，做嚴格會誤殺黃金例。
5. **驗證結果存在新表 `pipeline_validations`，每個版本只留最新一列（可覆蓋）。** 不放進 `pipeline_versions`（有 append-only 觸發器，且驗證結果會隨目錄快照改變），也不放 `jobs`。`stale` 只是標記，**不自動重算**；017d 擋 launch 時應直接呼叫 `validate_pipeline`（確定性、毫秒級、不花錢），不要信任可能過期的存檔。存檔的價值在於 017e 顯示「上次驗證結果」與歷史版本頁。
6. **`GRAPH_STALE` 後停止其他檢查。** 圖與現在的目錄對不上時，後面的型別結果沒意義；使用者先修圖。
7. **`any` 規則**：`list` 與缺漏／不認得的型別一律視為可與任何非 meta 類別相接，避免對目錄資料的不完整誤殺；`meta` 是否一致仍強制。
8. **決定性**：發現清單只依圖與目錄內容，不含時間、不含隨機；`validated_at`、`stale` 是存取層加的欄位，不在 `validate()` 的輸出裡。
9. **文件**：`docs/PLATFORM.md` 在 `## Composed pipelines` 補一小節 `### Validation`（發現的形狀、error／warning 的區別、`ok` 的意義、**目前只有靜態檢查，沒有 lint 或空跑**、沒有 MCP 工具或網頁，017e 才開），並在 stores 表加一列：`Pipeline validations: the latest check result for each saved pipeline version | platform.db (pipeline_validations) | replaced by the next check of the same version; never deleted.` 加完跑 `bash tests/platform_storage_doc_test.sh`；若因格式紅燈，只調整該列寫法，不改測試。
10. **檔首標頭**（TC-070）：`validate.py`、`test_validate.py`、`test_pipelines_validation.py` 前 40 行要有 `# Nothing existing: …`。範例：`# Nothing existing: nf-core publishes module metadata but no checker for a canvas graph; nf-core/tools lint needs a checked-out project and starts programs, which the platform host must not do.`
11. **待維護者確認：無。**（裁決 2 的「動態檢查延後並拆票」改變了總表 017c 的範圍與其「done」句的一半——「lint 失敗的版本不能 launch」要等 017c2；這是排程變動，不是方向變動，developer-agent 在派工單與 PLAN 上同步更新即可。）

## 裁決二（2026-10-24 04:35，developer-agent，回應 verifier 出題退回；與上文衝突以本段為準）
1. **選 (b)**：刪掉 `PARAM_KEY`／`PARAM_VALUE` 兩個 code。參數規則只有一套（`compose.normalize` 的 `_check_params`），參數壞掉一律是 `GRAPH_STALE`（訊息帶出 normalize 的 problem 原文，點名節點與參數名）。`test_param_rules_agree_with_normalize` 改成：壞參數 → `GRAPH_STALE` 且 finding 點名節點與參數名。
2. **PATTERN_MISMATCH 的聚合規則**：只在「來源輸出通道恰好一筆檔案類記錄且有 pattern」**而且**「目的輸入通道恰好一筆檔案類記錄且有 pattern」時才比；任一端有多筆記錄、或任一筆 pattern 為 null，就整條邊不比 pattern。比的方法＝兩個 pattern 各自展開大括號後的副檔名集合有沒有交集，沒有交集才給 warning。照此規則，黃金例（fastqc zip → multiqc 輸入 0，multiqc 端 6 筆含 null）與 twins 都不出 PATTERN_MISMATCH。
3. **標準答案檔**：`fixtures/validate/*.expected.json` 由 executor 依本計畫的規則**手推**寫出，推導過程逐項寫進 ledger（每條邊、每個 finding 為什麼出現），不得用 `validate` 的輸出回填；verifier 閱卷時獨立重推（同 017b 的做法）。bad_edges 的 `d` 輸入 1 兩條進邊：每條邊各自對 `d` 輸入 1 的記錄做型別比對，各自可能產生 META_MISMATCH／TYPE_MISMATCH，另外因多來源產生 MIXED_SOURCES（若規則成立）。
4. DUPLICATE_PROCESS 的舉例改為可達情形：兩個不同模組的 path 轉大寫、`/` 換 `_` 後相同；或同模組多節點的別名 `<PROCESS>_<ID大寫>` 等於另一模組的 process 名（例：模組 `fastqc` 兩節點 id `x`、`y`，加上 path 為 `fastqc/x` 的模組）。原文 `s1`／`S1` 的例子作廢。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
