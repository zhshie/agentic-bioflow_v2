# 測試案例：schema-reader（平台自己讀得懂參數表與樣本表欄位）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code. 本功能沒有 spec.md，來源是 plan.md；
維護者指示「測試案例必須來自計畫裡的例子，不得另編計畫沒寫的行為」，所以每條都標出對應的計畫位置（T1–T22 是計畫「失敗先行測試」表的編號；「作法 n」是計畫「作法（決定）」的第 n 點）。
-->

**規格**：`specs/schema-reader/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

這個功能是一個「只讀文字、不連網、沒人呼叫」的解析模組：給它 `nextflow_schema.json` 的內容，它回「參數分組表」；給它 `schema_input.json` 的內容，它回「樣本表欄位表」。使用者現在看不到任何畫面，所以下面所有「預期結果」都是函式回傳的內容或檢查結果。

名詞：

- **真檔**＝`platform/tests/fixtures/schema/ampliseq-2.18.0.nextflow_schema.json`（nf-core ampliseq 2.18.0 官方原檔，逐字複製）。
- **組**＝參數分組表裡的一個分組（例如「輸入輸出選項」）；**參數**＝組裡的一個設定項。
- 「小 dict」＝測試自己在程式裡寫的一小段 schema，用來單獨驗證一條規則。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：缺東西、格式不對、壞輸入時的反應（略過或拒絕，不當掉）。
- **不在範圍**：計畫「不做」的事；測試確認它真的沒做。

## User Story 1 — 讀出參數分組表（`parameter_groups`、`required_without_default`）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | T1 | 功能 | 真檔 | 對真檔呼叫 `parameter_groups` | 回傳 16 組 | 自動：`platform/tests/test_schema.py` |
| TC-002 | T1 | 功能 | 真檔 | 同上 | 第一組的 id 是 `input_output_options` | 自動 |
| TC-003 | T1 | 功能 | 真檔 | 同上，看 `asv_post_processing` 在回傳清單的位置 | 它排在第 6 位（從 1 算起），不是檔案裡 `$defs` 的第一個鍵所暗示的第 1 位 | 自動 |
| TC-004 | 作法 2（組的順序） | 功能 | 真檔 | 把回傳各組的 id 依序列出，與真檔頂層 `allOf` 裡 `#/$defs/<id>` 出現的順序比對 | 兩個順序完全一致（16 個都在） | 自動 |
| TC-005 | T2 | 功能 | 真檔 | 把所有組的參數數量加總 | 170 | 自動 |
| TC-006 | T2 | 功能 | 真檔 | 數所有參數中 `hidden` 為 True 的個數 | 19 | 自動 |
| TC-007 | 作法 5；T18 | 功能 | 真檔 | 把 `parameter_groups` 的回傳值丟進 `json.dumps` | 不丟例外 | 自動 |
| TC-008 | T3 | 功能 | 真檔 | 把真檔的分組結果丟給 `required_without_default` | 回傳恰好是 `["outdir"]` | 自動 |
| TC-009 | T4 | 功能 | 真檔 | 取 `generic_options` 組裡名叫 `help` 的參數 | `types == ["boolean","string"]` | 自動 |
| TC-010 | T5 | 功能 | 真檔 | 取 `outdir` 參數 | `format == "directory-path"` | 自動 |
| TC-011 | T5 | 功能 | 真檔 | 同上 | `required` 為 True | 自動 |
| TC-012 | T5；作法 2 | 功能 | 真檔 | 同上 | `has_default` 為 False，且 `default` 為 None | 自動 |
| TC-013 | T6 | 功能 | 真檔 | 取 `asv_post_processing` 組裡的 `decontam_decontaminate_method` | `default == "auto"` | 自動 |
| TC-014 | T6 | 功能 | 真檔 | 同上 | `enum` 的第一項是 `"auto"` | 自動 |
| TC-015 | T6 | 功能 | 真檔 | 同上 | `has_default` 為 True | 自動 |
| TC-016 | T7 | 功能 | `old-definitions.json`（舊式 `definitions` 鍵、一個組、三個參數） | 對它呼叫 `parameter_groups` | 解出恰好一組、該組三個參數 | 自動 |
| TC-017 | T7 | 功能 | 同上 | 逐一檢查三個參數的 `required`、`has_default`、`default` | 每一個都與檔案內容相符：名字在該組 `required` 清單裡才算必填；有 `default` 鍵才算有預設，`default` 是檔案裡的原值 | 自動 |
| TC-018 | T8 | 功能 | 小 dict：同時有 `$defs` 與 `definitions`，兩邊有同一個 id 但內容不同 | 呼叫 `parameter_groups` | 該 id 的內容取自 `$defs` 那份；沒有重複的組 | 自動 |
| TC-019 | T9 | 例外 | 小 dict：`allOf` 裡有一項指向不存在的 id，其餘項正常 | 呼叫 `parameter_groups` | 不丟例外；不存在的 id 被略過；其餘組照常、順序照 `allOf` | 自動 |
| TC-020 | T9 | 例外 | 小 dict：`allOf` 裡有一項 `$ref` 是外部網址（例如 `https://example.org/x.json#/$defs/a`），其餘項正常 | 呼叫 `parameter_groups` | 不丟例外；那一項被略過（不去讀它）；其餘組照常 | 自動 |
| TC-021 | T9 | 例外 | 小 dict：`allOf` 裡有一項不是物件（例如字串 `"x"` 或數字），其餘項正常 | 呼叫 `parameter_groups` | 不丟例外；該項被略過；其餘組照常 | 自動 |
| TC-022 | 作法 2（組或參數不是物件→略過） | 例外 | 小 dict：`$defs` 裡有一個組的值不是物件（例如 `"oops"`），另一個組正常 | 呼叫 `parameter_groups` | 不丟例外；壞的那組不在結果裡；正常的組照常 | 自動 |
| TC-023 | 作法 2（同上） | 例外 | 小 dict：某組的 `properties` 裡有一個參數的值不是物件，其他參數正常 | 呼叫 `parameter_groups` | 不丟例外；壞參數不在結果裡；其他參數照常 | 自動 |
| TC-024 | T10 | 功能 | 小 dict：有組，頂層也有非空 `properties` | 呼叫 `parameter_groups` | 最後多一組：`id == ""`、`title == "Parameters"`，裡面是頂層那些參數；前面的組不變 | 自動 |
| TC-025 | 作法 2（沒有組的小 pipeline） | 功能 | 小 dict：沒有 `$defs`／`definitions`，只有頂層非空 `properties` | 呼叫 `parameter_groups` | 恰好一組，`id == ""`、`title == "Parameters"` | 自動 |
| TC-026 | 作法 2（只有「非空」才多一組） | 功能 | 小 dict：有組，頂層 `properties` 是空物件 | 呼叫 `parameter_groups` | 不多出 `id ""` 的組 | 自動 |
| TC-027 | T11 | 例外 | `{}` | 呼叫 `parameter_groups` | 回傳 `[]` | 自動 |
| TC-028 | T12 | 功能 | 小 dict：三個參數，`default` 分別是 `false`、`0`、`""`，都列在該組 `required` | 呼叫 `parameter_groups`，取 `default` 是 `false` 的那個 | `has_default` 為 True，`default` 是 `False`（原值，不是 None） | 自動 |
| TC-029 | T12 | 功能 | 同上 | 取 `default` 是 `0` 的那個 | `has_default` 為 True，`default` 是 `0` | 自動 |
| TC-030 | T12 | 功能 | 同上 | 取 `default` 是 `""` 的那個 | `has_default` 為 True，`default` 是 `""` | 自動 |
| TC-031 | T12 | 功能 | 同上 | 對結果呼叫 `required_without_default` | 這三個參數的名字都不在回傳裡 | 自動 |
| TC-032 | T13 | 例外 | 小 dict：某組的 `required` 清單含一個該組沒有的參數名 | 呼叫 `parameter_groups` 與 `required_without_default` | 不丟例外；那個名字被略過（不憑空生出參數，也不出現在回傳） | 自動 |
| TC-033 | 作法 2（沒被 allOf 提到的組接在最後） | 功能 | 小 dict：`$defs` 依序有 a、b、c 三組，`allOf` 只提到 c | 呼叫 `parameter_groups` | 組的順序是 c、a、b（被提到的先，沒被提到的接在最後並維持檔案原順序） | 自動 |
| TC-034 | 作法 2（也認 `#/definitions/<id>`） | 功能 | 小 dict：用 `definitions` 鍵，`allOf` 的 `$ref` 寫成 `#/definitions/<id>`，順序與檔案鍵序不同 | 呼叫 `parameter_groups` | 組的順序照 `allOf` | 自動 |
| TC-035 | 作法 2（types） | 功能 | 小 dict：參數 `type` 是字串 `"string"` | 呼叫 `parameter_groups` | `types == ["string"]` | 自動 |
| TC-036 | 作法 2（types） | 例外 | 小 dict：參數完全沒有 `type` | 同上 | `types == []`（是 list，不是 None） | 自動 |
| TC-037 | 作法 2（types） | 例外 | 小 dict：參數 `type` 是 `["string", 5, null]` | 同上 | `types == ["string"]`（非字串元素略過） | 自動 |
| TC-038 | 作法 2（title 缺少） | 例外 | 小 dict：某組沒有 `title` | 同上 | 該組 `title` 等於它的 id | 自動 |
| TC-039 | 作法 2（description 缺少） | 例外 | 小 dict：某參數沒有 `description` | 同上 | 該參數 `description == ""`（不是 None） | 自動 |
| TC-040 | 作法 2（hidden） | 例外 | 小 dict：參數 `hidden` 分別是 `true`、字串 `"true"`、`1`、缺少 | 同上 | 只有布林 true 的那個 `hidden` 為 True；其餘三個為 False | 自動 |
| TC-041 | 作法 2（hidden_count） | 功能 | 小 dict：一組三個參數，其中兩個 `hidden: true` | 同上 | 該組 `hidden_count == 2` | 自動 |
| TC-042 | 作法 2（enum） | 功能 | 小 dict：一個參數 `enum` 是 list、一個參數 `enum` 是字串、一個沒有 | 同上 | 第一個原樣回傳該 list；後兩個 `enum` 是 None | 自動 |
| TC-043 | 作法 2（format／pattern／help_text）；裁決 3 | 例外 | 小 dict：參數的 `format`、`pattern`、`help_text` 值不是字串（例如數字），另一參數三者缺少 | 同上 | 這三欄都是 None；字串時則原樣回傳（含換行與 Markdown 符號不被清理） | 自動 |
| TC-044 | 作法 2（required 只看該組） | 功能 | 小 dict：甲組 `required` 列了名字 `x`，乙組也有一個叫 `x` 的參數但乙組沒有 `required` | 同上 | 甲組的 `x` 必填為 True；乙組的 `x` 必填為 False | 自動 |
| TC-045 | 作法 2（回傳形狀） | 功能 | 真檔 | 檢查任一組與任一參數的鍵 | 組的鍵恰為 `id,title,description,hidden_count,params`；參數的鍵恰為 `name,types,description,help_text,has_default,default,required,hidden,enum,format,pattern`（不多不少） | 自動 |
| TC-046 | 作法 3 | 功能 | 小 dict：兩組，各有必填且無預設的參數（甲組先、乙組後，組內有兩個），另有必填但有預設的參數 | 呼叫 `required_without_default` | 回傳依組順序、組內依檔案順序列出「必填且無預設」的名字，有預設的不在裡面 | 自動 |
| TC-047 | 不做：不解讀 `anyOf`／`oneOf` | 不在範圍 | 小 dict：參數沒有 `type`，只有 `anyOf: [{"type":"string"},{"type":"integer"}]` | 呼叫 `parameter_groups` | 不丟例外；`types == []`（沒有把 `anyOf` 裡的型別展開出來） | 自動 |
| TC-048 | 不做：不做參數值驗證 | 不在範圍 | 小 dict：參數 `type` 是 `integer`，但 `default` 是字串 `"abc"`；另一參數 `default` 不在自己的 `enum` 裡 | 呼叫 `parameter_groups` | 不丟例外；`default` 原樣回傳，沒有被改或被拒絕 | 自動 |

## User Story 2 — 讀出樣本表欄位表（`samplesheet_columns`）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-049 | T15 | 功能 | `tests/fixtures/schema_input/` 下的五份檔（ampliseq-2.18.0、bacass-2.6.1、mag-5.5.0、rnaseq-3.27.0、taxprofiler-2.0.1），測試直接讀既有檔、不複製 | 對每一份呼叫 `samplesheet_columns`，取欄位名稱序列 | 五份都和各檔 `items.properties` 的鍵順序完全一致 | 自動 |
| TC-050 | T15 | 功能 | ampliseq-2.18.0 | 同上 | 前三欄依序是 `sampleID`、`forwardReads`、`reverseReads`（2026-10-25 developer-agent 修正：原值取自無序字典，與真檔不符） | 自動 |
| TC-051 | T16 | 功能 | rnaseq-3.27.0 | 看各欄 `required` | `sample`、`fastq_1`、`strandedness` 為 True | 自動 |
| TC-052 | T16 | 功能 | 同上 | 同上 | 除了上面三欄以外，其餘欄位的 `required` 全部 False | 自動 |
| TC-053 | T16 | 功能 | bacass-2.6.1 | 同上 | 只有 `ID` 的 `required` 為 True，其餘全部 False | 自動 |
| TC-054 | T17 | 功能 | ampliseq-2.18.0（檔內沒有 `items.required`） | 看所有欄位 `required` | 全部 False | 自動 |
| TC-055 | T17 | 功能 | 同上 | 取 `sampleID` | `meta == ["sample"]` | 自動 |
| TC-056 | T17 | 功能 | 同上 | 取 `fastq_1` | `exists` 為 True | 自動 |
| TC-057 | T17 | 功能 | 同上 | 取 `fastq_1` | `format == "file-path"` | 自動 |
| TC-058 | T17 | 功能 | 同上 | 取 `run` | `types == ["string","integer"]` | 自動 |
| TC-059 | 作法 4（欄位鍵） | 功能 | 任一份樣本表 schema | 檢查任一欄位的鍵 | 恰為 `name,types,required,format,pattern,exists,meta,description`（不多不少） | 自動 |
| TC-060 | 作法 4（`exists` 只認 True） | 例外 | 小 dict：欄位 `exists` 分別是 `true`、字串 `"true"`、`1`、缺少 | 呼叫 `samplesheet_columns` | 只有布林 true 的 `exists` 為 True，其餘為 False | 自動 |
| TC-061 | T19 | 功能 | 小 dict：欄位 `meta` 是字串 `"id"` | 同上 | `meta == ["id"]` | 自動 |
| TC-062 | T19 | 例外 | 小 dict：欄位 `meta` 是 `["id", 5]` | 同上 | `meta == ["id"]`（非字串元素略過） | 自動 |
| TC-063 | T19 | 例外 | 小 dict：欄位沒有 `meta` | 同上 | `meta == []` | 自動 |
| TC-064 | 作法 4（沒有 `items.properties` 才用頂層 `properties`） | 功能 | 小 dict：沒有 `items`，只有頂層 `properties`（兩欄） | 同上 | 回傳這兩欄，順序照檔案 | 自動 |
| TC-065 | 作法 4（`items.properties` 優先） | 功能 | 小 dict：`items.properties` 與頂層 `properties` 都有，欄位名不同 | 同上 | 回傳的是 `items.properties` 的欄位，頂層那些不出現 | 自動 |
| TC-066 | T18；作法 5 | 功能 | 五份樣本表 schema | 把 `samplesheet_columns` 對五份的回傳值各丟進 `json.dumps` | 五份都不丟例外 | 自動 |
| TC-067 | T18；不做：不推論欄位角色 | 不在範圍 | 五份樣本表 schema，和 TC-007 的真檔 | 檢查回傳的每個欄位 dict 的鍵 | 沒有任何一個欄位含 `role`、`read1`、`read2`、`sample_column` 這類鍵（角色判斷只在 `scripts/utils/schema_roles.py`）；`parameter_groups` 的回傳也沒有這類鍵 | 自動 |
| TC-068 | 不做：不解讀 `anyOf` | 不在範圍 | mag-5.5.0（檔內 `items.required` 是 `sample`、`group`，另有「幾選一」的 `anyOf`） | 看各欄 `required` | 只有 `sample`、`group` 為 True；`anyOf` 裡提到的欄位（例如 `short_reads_1`）沒有因此變成必填 | 自動 |

## User Story 3 — 載入文字、不連網、不留記憶（`load` 與模組本身）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-069 | 作法 1 | 功能 | 一段合法 JSON 文字，頂層是物件（例如真檔內容） | 呼叫 `load(text)` | 回傳 dict，內容等於 `json.loads` 的結果 | 自動 |
| TC-070 | T14 | 例外 | 一段 2,000,001 個字元的文字 | 呼叫 `load` | 丟 `ValueError`（即使內容是合法 JSON 也拒絕） | 自動 |
| TC-071 | T14 | 例外 | 文字 `"[]"`（合法 JSON 但頂層不是物件） | 呼叫 `load` | 丟 `ValueError` | 自動 |
| TC-072 | T14 | 例外 | 文字 `"not json"` | 呼叫 `load` | 丟 `ValueError` | 自動 |
| TC-073 | T14 | 例外 | 文字 `"null"` | 呼叫 `load` | 丟 `ValueError` | 自動 |
| TC-074 | T14（中英並陳）；專長守則（錯誤訊息） | 例外 | 上面四種壞輸入各一份 | 呼叫 `load`，讀例外訊息 | 四則訊息各自同時含中文字與英文字母（中英並陳），且說明問題是哪一種（過長／不是 JSON／頂層不是物件）；不露出堆疊或內部路徑 | 自動 |
| TC-075 | 作法 1（「超過」2,000,000 才拒絕） | 功能 | 一段剛好 2,000,000 個字元的合法 JSON 物件文字（以空白補長） | 呼叫 `load` | 不丟例外，回傳 dict | 自動 |
| TC-076 | T20 | 不在範圍 | 一個 dict | 呼叫 `parameter_groups` 一次；改動同一個 dict（例如新增一個參數）；再呼叫一次 | 第二次的結果反映改動後的內容（沒有記憶上次結果）；對 `samplesheet_columns` 同樣成立 | 自動 |
| TC-077 | T20 | 不在範圍 | `platform/abf_platform/schema.py` 原始碼 | 掃描原始碼文字 | 不含 `lru_cache`、`open(`、`write_text` | 自動 |
| TC-078 | T21 | 不在範圍 | 同上 | 掃描原始碼文字 | 不含 `urllib`、`socket`、`subprocess`、`threading`、字面 `station`、`ssh`、`sbatch`、`nextflow run`，也沒有 `while True`（作法的禁用清單） | 自動 |
| TC-079 | T22 | 功能 | 真檔 | 計算檔案 sha256 | 等於 `0e8f195c88c1a1a07f610ebd74bd88bf6ef00d8f105dfe16e39989d429da516f`（防止被改動） | 自動 |
| TC-080 | 範圍（fixture 大小）；完成標準 | 功能 | 真檔與 `old-definitions.json` | 看檔案大小 | 真檔 95,707 位元組（不超過 100 KB）；`old-definitions.json` 是手寫小檔；兩檔之外沒有新增大檔 | 自動 |
| TC-081 | 不做：不接線 | 不在範圍 | 本任務的程式碼差異 | 閱卷者看 `git diff --name-only <base>...HEAD` 並搜尋整個 `platform/`、`scripts/` | 沒有任何動作層函式、MCP 工具、網頁路由、CLI 子命令呼叫新模組（除 `test_schema.py` 外沒有檔案 import `abf_platform.schema`） | 閱卷：核對 diff（計畫禁止動 `docs/*`，無法新增 `docs/TESTING.md` 手動步驟） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-082 | 原則 I（1：先說明不用現成工具的理由；檢查 TC-070） | 功能 | 新增的 `platform/abf_platform/schema.py` 與 `platform/tests/test_schema.py` | 跑既有的 `platform/tests/test_scope.py` 的 TC-070 | 兩個檔案檔首都有 `# Nothing existing:` 並附 ≥15 字的理由，檢查為綠；`schema.py` 的理由提到 `prepare_launch.sh` 只印文字摘要、`schema_roles.py` 只判斷角色、nf-core CLI 要整套安裝 | 自動：`platform/tests/test_scope.py` |
| TC-083 | 原則 I（2：平台進程不開連線；檢查 TC-061） | 功能 | 同上 | 跑 `test_scope.py` 的 TC-061 | 綠（新原始碼沒有 ssh／sbatch／station／urllib.request／socket 等） | 自動：`platform/tests/test_scope.py` |
| TC-084 | 原則 I（2：不送出、不常駐；檢查 TC-071） | 功能 | 同上 | 跑 `test_scope.py` 的 TC-071 | 綠（沒有 `nextflow run`、常駐迴圈、被提交的資料庫） | 自動：`platform/tests/test_scope.py` |
| TC-085 | 原則 II（3：不寫死個人／叢集路徑；檢查 TC-072） | 功能 | 兩個新 fixture 與新程式 | 跑 `test_scope.py` 的 TC-072 | 綠（真檔與 `old-definitions.json` 內沒有 `/home/<名>/` 這類路徑形狀） | 自動：`platform/tests/test_scope.py` |
| TC-086 | 原則 I（2：不另存一份執行狀態） | 功能 | 完成後的 worktree | 跑 `bash tests/no_second_run_state_test.sh` | 綠 | 自動：`tests/no_second_run_state_test.sh` |
| TC-087 | 完成標準（全套綠） | 功能 | 完成後的 worktree | 在 WSL 跑 `bash tests/run_all.sh` | 全綠 | 自動：`tests/run_all.sh`（WSL） |
| TC-088 | 完成標準（改動範圍） | 功能 | 完成後的 worktree | 閱卷者看 `git diff --name-only <base>...HEAD` | 除 `specs/schema-reader/` 下的計畫與測試案例文件外，只有計畫列的 5 個檔：`schema.py`、`test_schema.py`、兩個 fixture、`specs/schema-reader/ledger.md`；沒有其他檔案 | 閱卷：核對 diff |
| TC-089 | 完成標準；範圍「不准動」 | 不在範圍 | 同上 | 看 diff 是否碰到 `scripts/*`（含 `utils/schema_roles.py`、`prepare_launch.sh`）、`actions/*`、`mcp_server.py`、`web*.py`、`cli.py`、`store.py`、`pipeline_launch.py`、`abf_station/*`、`abf_launch/*`、`docs/*` | 這些路徑零改動 | 閱卷：核對 diff |
| TC-090 | 計畫「會改斷言的既有測試：無」 | 不在範圍 | 同上 | 比對 diff 中既有測試檔（`test_scope.py` 等） | 既有測試檔沒有被修改（沒有放寬、跳過或改期望值） | 閱卷：核對 diff |
| TC-091 | 計畫「不需要 migration」 | 不在範圍 | 同上 | 看 diff 是否含資料表或 JSON 欄位內容的改動、migration 檔 | 沒有；也沒有新增設定鍵 | 閱卷：核對 diff |

<!--
Rules for the writer:
- 每條計畫例子 T1–T22 都至少對到一條 TC；對照見 test-case-overview.md「覆蓋檢查」。
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
