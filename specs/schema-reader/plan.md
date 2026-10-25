---
id: schema-reader
title: 平台自己讀得懂 pipeline 的參數表與樣本表欄位（純解析：nextflow_schema.json 分組參數、schema_input.json 欄位），還不連網、不接線
tier: A
kinds: backend
lane: L-schema
base: v3（`origin/v3` @ 6061925；所有行號都是該版本）
source: developer-agent 讀碼查證（2026-10-25）；總表 012b-2 的「schema 讀取改到平台側 → 新 `platform/abf_platform/schema.py`」（replan 第 146 行）；`guided-launch-1.md` 第 14 行把它留給第二刀
---

# schema-reader

> A 級：新增一個沒人呼叫的純解析模組，輸入是已經讀進來的 JSON 文字／dict。**抓檔案（連 GitHub）不在這裡**：平台進程不准開連線（`test_scope.py:187` TC-061），見裁決 1。第二刀引導式送出（`guided-launch-2`，前端手上）將來直接呼叫這支，不必再寫解析。

## 目標
給一份 pipeline 的 `nextflow_schema.json`，回傳「參數分組表」（依 nf-core 的顯示順序、每個參數的型別／預設／必填／隱藏／選項）；給一份 `assets/schema_input.json`，回傳「樣本表欄位表」。對使用者的意義：引導式送出的第 5 步（參數三路線）與樣本表預覽有可靠的資料來源，而且和 plugin 端 `prepare_launch.sh` 看到的是同一個答案。

## 維護者原話（verifier 出題用）
- 「引導式七步：…參數三路線…；schema 讀取改到平台側」（replan 第 146 行 012b-2）→ T1–T9。
- 「pipeline 的 schema 一律讀釘死版本的原始檔，不快取」（repo `CLAUDE.md` Working conventions：「those are all read live from the pipeline's repo at that revision, never cached here」）→ T20（本模組不存檔、不記憶上次結果）。
- 「規則只放一處」（`scripts/utils/schema_roles.py:19`：樣本欄位角色的判斷只在那裡）→ T18（本模組**不推論** R1／R2／樣本欄角色，只回報欄位的原始屬性）。

## 範圍：檔案（5 個）
- `platform/abf_platform/schema.py`（新）
- `platform/tests/test_schema.py`（新；檔首 `# Nothing existing: …` ≥15 字，`test_scope.py:76` TC-070 檢查）
- `platform/tests/fixtures/schema/ampliseq-2.18.0.nextflow_schema.json`（新；**逐字**複製自 `https://raw.githubusercontent.com/nf-core/ampliseq/2.18.0/nextflow_schema.json`，95,707 位元組，sha256 `0e8f195c88c1a1a07f610ebd74bd88bf6ef00d8f105dfe16e39989d429da516f`，2026-10-25 我下載並核對；executor 只在這一步可連一次公開網址，hash 不符就停下回報 BLOCKED，不得改檔內容）
- `platform/tests/fixtures/schema/old-definitions.json`（新；手寫小檔，用舊式 `definitions` 鍵、一個組、三個參數，供 T7）
- `specs/schema-reader/ledger.md`
- 樣本表欄位的測試**直接讀**既有的 `tests/fixtures/schema_input/*.json`（五份，`tests/fixtures/schema_input/README.md:3`），不複製。
- **不准動**：`scripts/*`（含 `utils/schema_roles.py`、`prepare_launch.sh`）、`actions/*`、`mcp_server.py`、`web*.py`、`cli.py`、`store.py`、`pipeline_launch.py`、`abf_station/*`、`abf_launch/*`、`docs/*`。

## 作法（決定）
只用標準函式庫、不連網、不讀檔（呼叫端給文字或 dict）。原始碼不得出現 `urllib.request`、`socket`、`subprocess`、`threading`、`while True`、字面 `station`、`ssh`、`sbatch`（`test_scope.py:101,187`）。
1. `load(text)` → dict：長度超過 2,000,000 個字元、不是合法 JSON、頂層不是物件 → `ValueError`（中英並陳）。
2. `parameter_groups(schema)` → `list[dict]`，每組：
   `{"id": "input_output_options", "title": "Input/output options", "description": "…", "hidden_count": 0, "params": [ … ]}`；每個參數：
   `{"name": "outdir", "types": ["string"], "description": "…", "help_text": "…" | None, "has_default": False, "default": None, "required": True, "hidden": False, "enum": None, "format": "directory-path" | None, "pattern": None}`。
   - 組來源：`$defs` 優先，其次 `definitions`；兩者都有時 id 相同取 `$defs`。**順序依頂層 `allOf` 裡 `{"$ref": "#/$defs/<id>"}`（或 `#/definitions/<id>`）出現的順序**，指向不存在的 id 者略過；沒被 `allOf` 提到的組接在最後，維持原檔順序。（實測 ampliseq 2.18.0：`$defs` 的第一個鍵是 `asv_post_processing`，但 `allOf` 的第一個是 `input_output_options`。）
   - 頂層另有非空 `properties`（沒有組的小 pipeline）→ 最後多一組 `id: ""`、`title: "Parameters"`。
   - `types`：`type` 是字串 → `[字串]`；是 list → 其中的字串元素（實測 `help` 是 `["boolean","string"]`）；沒有 → `[]`。永遠是 list。
   - `required`：該參數名在**該組**的 `required` list 裡。`has_default`：該參數有 `default` 鍵（值可以是 `false`、`0`、`""`，都算有）；`default` 回原值，沒有就 None。`hidden`：`hidden is True`。`enum`：list 就原樣，否則 None。`format`、`pattern`、`description`、`help_text`：字串就原樣，否則 None（`description` 缺少時用 `""`）。
   - 組的 `title` 缺少時用 id；`hidden_count`＝該組 `hidden` 參數數。組或參數不是物件 → 略過，不丟例外。
   - 不吃 `$ref` 指向外部網址或其他檔的項目；不展開 `anyOf`／`oneOf`。
3. `required_without_default(groups)` → `list[str]`：依組順序、組內依檔案順序，`required` 且 `not has_default` 的參數名。與 `prepare_launch.sh:431-445` 同義（它也是 `pname in req and "default" not in p`）。
4. `samplesheet_columns(schema_input)` → `list[dict]`：欄位來自 `items.properties`，沒有才用頂層 `properties`（與 `schema_roles.py:59-65` 相同規則）；每欄 `{"name", "types", "required", "format", "pattern", "exists", "meta", "description"}`；`required` 取 `items.required`（沒有該鍵＝全部 False；`anyOf` 那種「幾選一」**不解讀**，實測 ampliseq 2.18.0 沒有 `items.required`）；`exists` 是 `exists is True`；`meta` 是 list（字串→單元素 list，非字串元素略過，缺少→`[]`，與 `schema_roles.py:113-118` 一致）；順序依檔案。
5. 全部回傳值只含 str／list／dict／bool／None／數字，`json.dumps` 得過。
6. 模組檔首 `# Nothing existing: …`：`prepare_launch.sh` 用 shell 內嵌 Python 印文字摘要、`schema_roles.py` 只判斷欄位角色，平台沒有結構化資料可用；nf-core 的 CLI 解析 schema 但要整套安裝。

## 失敗先行測試（`test_schema.py`；現在全紅，模組不存在）
| 編號 | 案例 | 預期 |
|---|---|---|
| T1 | 真檔 ampliseq 2.18.0：`parameter_groups` | 16 組；第一組 id `input_output_options`；`$defs` 第一個鍵 `asv_post_processing` 排在 `allOf` 的第 6 位 |
| T2 | 同上，所有組的參數總數 | 170；`hidden` 為 True 的總數 19 |
| T3 | 同上 `required_without_default` | 恰為 `["outdir"]`（`input_output_options` 的 `required` 只有它） |
| T4 | 同上 `help` 參數（在 `generic_options`） | `types == ["boolean","string"]` |
| T5 | 同上 `outdir` | `format == "directory-path"`、`required True`、`has_default False` |
| T6 | 同上 `decontam_decontaminate_method`（`asv_post_processing`） | `default == "auto"`、`enum` 首項 `"auto"`、`has_default True` |
| T7 | `old-definitions.json`（`definitions` 鍵） | 同樣解出一組三個參數；`required` 與 `default` 規則相同 |
| T8 | 同時有 `$defs` 與 `definitions`、同 id | 取 `$defs` 的 |
| T9 | `allOf` 指向不存在的 id、外部網址、非物件項 | 略過、不丟例外；其餘組照常 |
| T10 | 有組也有頂層非空 `properties` | 最後多一個 `id ""` 組 |
| T11 | 沒組沒屬性（`{}`） | `[]` |
| T12 | 參數 `default: false`、`0`、`""` | `has_default True` 且 `default` 原值；這三個不出現在 `required_without_default` |
| T13 | 組的 `required` 含一個不存在的參數名 | 略過，不丟例外 |
| T14 | `load` 吃 2,000,001 字元、`"[]"`、`"not json"`、`"null"` | 各丟 `ValueError`，訊息中英並陳 |
| T15 | 五份 `tests/fixtures/schema_input/*.json` 的 `samplesheet_columns` 名稱序列 | 與各檔 `items.properties` 的鍵序一致（ampliseq 首欄 `fastq_1`、`control`、`fastq_2`…） |
| T16 | rnaseq-3.27.0 的 `required` | `sample`、`fastq_1`、`strandedness` 為 True，其餘 False；bacass 只有 `ID` |
| T17 | ampliseq-2.18.0 | 全部 `required False`；`sampleID.meta == ["sample"]`；`fastq_1.exists True`、`format "file-path"`；`run.types == ["string","integer"]` |
| T18 | 回傳的每個欄位 dict | **不含** `role`、`read1`、`read2`、`sample_column` 之類的鍵（角色判斷只在 `schema_roles.py`）；`json.dumps` 兩個函式的回傳值都通過 |
| T19 | `meta` 是字串 `"id"`、是 `["id", 5]`、缺少 | `["id"]`、`["id"]`、`[]` |
| T20 | 同一個 dict 呼叫兩次、中間改動輸入 | 第二次反映新輸入（無記憶）；原始碼不含 `lru_cache`、`open(`、`write_text` |
| T21 | 原始碼掃描：`schema.py` 不含 `urllib`、`socket`、`subprocess`、`threading`、字面 `station`、`ssh`、`sbatch`、`nextflow run` | 無命中 |
| T22 | 真檔的 sha256 與計畫所寫一致（防止被改動） | 相符 |

**現在會紅**：T1–T22 全部。executor 先跑一次貼紅輸出，再下載 fixture（見範圍）。

**會改斷言的既有測試：無。** 新檔會被這些既有檢查掃到、必須仍綠：`test_scope.py:76`（TC-070 檔首）、`:101`（TC-071）、`:144`（TC-072：fixture 內不得有 `/home/<名>/` 形狀；我已核對真檔 0 命中）、`:187`（TC-061）；`tests/no_second_run_state_test.sh`。

## 完成標準（done when）
- T1–T22 全綠；`bash tests/run_all.sh`（WSL）綠。
- `git diff --name-only` 只含上列 5 個檔（含 ledger）；`scripts/` 零改動（兩份讀 schema 的程式並存，裁決 2）。
- 兩個 fixture 之外沒有新增大檔（真檔 ≤ 100 KB）。

## 環境事實
- v3 的平台目前**完全不讀** `nextflow_schema.json`；只有 plugin 端 `scripts/prepare_launch.sh:419-446` 用內嵌 Python 印文字摘要（`definitions` 或 `$defs`，`:431`）。`guided-launch-1.md` 第 14 行與「不做」節明寫第一刀不連 GitHub、不讀 schema。
- 平台進程不准開連線：`test_scope.py:187` 禁 `urllib.request`、`socket`；`cloud_store.py:1` 檔首也這樣寫。所以抓 `nextflow_schema.json` 要走別的路（裁決 1）。
- 實測真檔（ampliseq 2.18.0，2026-10-25）：頂層鍵 `description,title,$id,allOf,$schema,type,$defs`；16 組；`allOf` 順序與 `$defs` 鍵序不同；只有 `input_output_options` 有 `required`（`["outdir"]`）；`input` 參數沒有被標必填。rnaseq 3.27.0 同樣用 `$defs`。
- 倉庫既有的 `tests/fixtures/schema_input/` 是 `assets/schema_input.json`，沒有任何 `nextflow_schema.json` 的真檔，所以本任務新增一份。

## 不做
- 不連網、不快取、不接線（不加動作層函式、MCP 工具、網頁路由、CLI；`guided-launch-2` 和動作層各有人）。
- 不推論樣本表欄位角色（R1／R2／樣本欄）；不解讀 `anyOf`／`oneOf`；不做參數值驗證（那是 `nf-core pipelines schema validate` 的事，PITFALLS 29）。
- 不新增設定鍵；**不需要 migration**：沒有動資料表或 JSON 欄位內容。

## 裁決
1. **誰去抓檔案（待維護者／developer-agent）**：與 `release-tag-pick` 裁決 1 同一個問題——平台進程被 TC-061 禁止連線。選項：(a) 站台 agent 新增唯讀 job kind 讀取公開 raw 檔（改 `handlers.py`，`after: cloud-cleanup-c`；agent 目前只回答三種站台唯讀問題，要他點頭）；(b) 由使用者的 AI／瀏覽器取得文字後經動作層傳入；(c) 放寬 TC-061 給單一檔案（動憲法級檢查，C 級）。**預設 (a)**，另開任務；本模組不受影響，因為輸入是文字。
2. **兩份解析並存**：`prepare_launch.sh` 的 shell 內嵌 Python 與本模組做的是同一件事。為保「同一個答案」，T3 釘住 `required_without_default` 與 shell 版同義；是否讓 plugin 改呼叫本模組（`scripts/` 不能 import 平台套件）暫不處理——預設兩邊各自維護，PITFALLS 若出現不一致再合併。
3. **欄位文字不做清理**：`description`／`help_text` 原樣回傳（可能含換行與 Markdown）；網頁層本來就逐字跳脫（`web_board.py` 既有做法，`DESIGN.md` 不外連資源）。預設如此；若維護者要截長度，由顯示層處理。

## 裁決（2026-10-25 00:40，developer-agent）
1. 同 release-tag-pick：解析器只吃文字，不連網；抓檔留給 `release-lookup-job`。
2. fixture 的 sha256 不符就 BLOCKED。

## 裁決二（2026-10-25 04:40，executor BLOCKED 後）
3. 合約 TC-050 已由 developer-agent 改成真檔順序 `sampleID`、`forwardReads`、`reverseReads`（原值出題錯誤）。executor 把 test_schema.py 的 TC-050 期望值改成這個順序、重跑全套；其餘不動。
4. 計畫裡「`$defs` 第一個鍵是 asv_post_processing」作廢，以 allOf 順序為準（TC-003／TC-004）。

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
