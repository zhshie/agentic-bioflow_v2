# 測試案例：downstream-method-catalog（認證下游方法目錄＋唯讀 MCP 工具 list_downstream）

狀態：合約已確認（2026-11-17，verifier）

**計畫**：`memory/dev-plans/downstream-method-catalog.md`（含 2026-11-07 lead 裁決與 2026-11-17 lead 代理裁決五點）　**種子檔**：`memory/reference/downstream-catalog-seed-16s.json`、`memory/reference/downstream-catalog-seed-rnaseq.json`

本檔同時是測試案例與總覽；以下「總覽」一節取代 `test-case-overview.md`。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

驗證等級：**【機器可驗】**＝測試或唯讀指令即可判定；**【實機驗】**＝要真實 MCP 客戶端與模型對話才能判定。

下列所有「今天」都是注入的日期，不用真實日期（目錄複審日是 2026-11-07，真實日期過 2027-11-07 後結果會變，見備註 1）。「測試表」＝計畫中列的 `test_dc*`／`test_ld*` 名稱，名稱僅供對應，驗收看斷言內容。

維護者原話對照：

- 「請你去找是否有社群維護對於不同分析既有的繪圖R script或統計分析script。如果沒有，就是使用者跟你討論繪製」→ TC-D02、TC-D17、TC-Q11、TC-Q12（找得到才列已認證的；找不到就空結果、不亂猜）
- 「Q15你問了才列」→ TC-M10、TC-X01、TC-X02、TC-N03
- 同日裁示 1～9 項：1→TC-D01、N06；2→TC-M10；3→TC-Q03；4→TC-Q04～Q09；5→TC-S02～S04；6→TC-M01；7→TC-D03；8→TC-D04～D06、D14；9→TC-D08～D11、D17

## US1 — 目錄資料：第一批內容與欄位（P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-D01【機器可驗】 | 作法 1；裁示 1、3；test_dc01 | 功能 | 已有 `platform/abf_platform/data/downstream-methods.json` | 載入並驗 schema | 頂層 `schema` 為 1；每條都有全部鍵（id、pipeline、pipeline_version、method、link、doi、grade、version_pin、license、inputs、non_interactive_plot、singularity、reviewed、notes）；id 為 kebab-case 且不重複；`grade` 只能是 A／B／C；`reviewed` 是合法的 YYYY-MM-DD；`singularity` 只能是 ok／untested／unavailable；`non_interactive_plot` 只能是 true／false／"needs_person"／null（null 為裁決 2 新增，測試表原寫三值，以本條為準） | 自動：`test_downstream_catalog.py` |
| TC-D02【機器可驗】 | 裁示 7、8；裁決 3 | 功能 | 同上 | 讀出全部 id | 共 19 條，id 恰為：ampliseq-summary-report、ampliseq-ancombc、ampliseq-phyloseq、ampliseq-mia-miaviz-oma、ampliseq-ancom-bc、ampliseq-aldex2、ampliseq-microeco、ampliseq-maaslin2、ampliseq-vegan；rnaseq-differentialabundance、rnaseq-deseq2、rnaseq-edger、rnaseq-limma、rnaseq-clusterprofiler、rnaseq-fgsea、rnaseq-tximport、rnaseq-pcaexplorer、rnaseq-isee、rnaseq-debrowser；pipeline 欄只有 ampliseq 與 rnaseq | 自動 |
| TC-D03【機器可驗】 | 裁示 7；test_dc03 | 功能 | 同上 | 讀 ampliseq 條目的宣告等級 | 宣告 A 的恰為 summary_report、ancombc（ampliseq --ancombc）、phyloseq、mia/miaViz（OMA）、ANCOM-BC、ALDEx2 六條；宣告 B 的恰為 microeco、MaAsLin2、vegan 三條；vegan 與 MaAsLin2 維持 B，不得自行改等級；每條 `pipeline_version` 為 "3.1.0" | 自動 |
| TC-D04【機器可驗】 | 裁示 8；裁決 4 | 功能 | 同上 | 讀 rnaseq 條目的宣告等級 | 宣告 A 的恰為 differentialabundance、DESeq2、edgeR、limma、clusterProfiler、fgsea、tximport、pcaExplorer、iSEE 九條；宣告 B 的恰為 DEBrowser 一條；沒有 C | 自動 |
| TC-D05【機器可驗】 | 裁示 8；test_dc03 | 功能 | 同上 | 讀 `non_interactive_plot` 為 "needs_person" 的條目 | 恰為 pcaExplorer、iSEE、DEBrowser 三條，其他 16 條都不是 "needs_person" | 自動 |
| TC-D06【機器可驗】 | 裁示 8；test_dc04 | 功能 | 同上 | 讀 rnaseq-differentialabundance | `singularity == "untested"`；`notes` 含「待實測」；`notes` 說明 nano4 無 docker | 自動 |
| TC-D07【機器可驗】 | 不做：不對 differentialabundance 實測 | 功能 | 同上 | 讀全部條目的 `singularity` | 19 條全是 "untested"，沒有任何 "ok"（沒人實測過，不得宣稱可用） | 自動 |
| TC-D08【機器可驗】 | 裁示 9；作法 1 缺值規則；test_dc02 | 功能 | 同上 | 找 `doi`／`license`／`version_pin`／`pipeline_version` 任一為 null 的條目 | 每一條的 `notes` 含「查不到」 | 自動 |
| TC-D09【機器可驗】 | 裁示 9；test_dc02 後半 | 例外 | 臨時 JSON，一條 `license: null` 但 `notes` 無「查不到」 | 呼叫 schema 驗證 | 丟錯，且訊息點出是哪個 id、哪個欄位 | 自動 |
| TC-D10【機器可驗】 | 裁決 1 | 功能 | 同 D01 | 讀 rnaseq 10 條的 `pipeline_version` 與 `notes` | `pipeline_version` 全為 null（不得填 3.27.0 或 3.26.0 等任何版本號）；每條 `notes` 含「pipeline_version」與「查不到」 | 自動 |
| TC-D11【機器可驗】 | 裁示 9；裁決 4 | 功能 | 同上 | 讀 rnaseq-debrowser | `grade == "B"`；`version_pin` 為 null；`notes` 含「查不到」；`non_interactive_plot == "needs_person"` | 自動 |
| TC-D12【機器可驗】 | 裁決 2 | 功能 | 同上 | 讀 ampliseq 的 phyloseq、mia/miaViz、ANCOM-BC、ALDEx2、microeco、MaAsLin2、vegan 七條 | `non_interactive_plot` 都是 null（不得猜成 true 或 false）；每條 `notes` 含「待驗證」 | 自動 |
| TC-D13【機器可驗】 | 裁決 2；種子檔 headless／interactive | 功能 | 同上 | 讀其餘條目的 `non_interactive_plot` | summary_report 與 rnaseq 的 differentialabundance、DESeq2、edgeR、limma、clusterProfiler、fgsea、tximport 為 true；ampliseq-ancombc 為 false；pcaExplorer、iSEE、DEBrowser 為 "needs_person" | 自動 |
| TC-D14【機器可驗】 | 裁決 4；作法 1 inputs 規則 | 功能 | 同上 | 讀 rnaseq-clusterprofiler 與 rnaseq-fgsea | 兩條 `inputs == []`；`notes` 含「待驗證」；`notes` 後段附有種子檔 input_contract 的文字描述原文（兩條都是「differential results table from a prior DESeq2/edgeR/limma step …」那句） | 自動 |
| TC-D15【機器可驗】 | 作法 1 inputs 規則 | 功能 | 同上 | 掃全部條目的 `inputs` | 凡 `inputs == []` 的條目，`notes` 含「待驗證」；凡非空 `inputs`，每項都有非空字串的 `pipeline_output` 與 `role` | 自動 |
| TC-D16【機器可驗】 | 作法 2 輸入檔契約；裁示 8 | 功能 | 同上 | 讀三條的 `inputs` | summary_report 含 `summary_report/summary_report.html`；differentialabundance 含 `star_salmon/salmon.merged.gene_counts_length_scaled.tsv`（length-scaled counts）；tximport 含 `star_salmon/<SAMPLE>/quant.sf` | 自動 |
| TC-D17【機器可驗】 | 裁決 3、6；憲法第 9 條 | 功能 | 兩份種子檔存在 | 驗收者用唯讀腳本逐條比對（id 對 id；種子 url→link、reviewed_at→reviewed；interactive 為 true 時 non_interactive_plot 為 "needs_person"，否則取 headless；input_contract 的 files 或清單→inputs；pipeline_version：16S 取種子值、rnaseq 為 null） | 19 條的 `link`、`grade`、`version_pin`、`license`、`doi`、`pipeline_version`、`reviewed`（2026-11-07）、`singularity`、`inputs`（clusterProfiler、fgsea 例外）全與種子檔相同，沒有種子檔沒有的值；種子檔的 tximeta 不在 JSON | 自動：驗收時唯讀比對 |
| TC-D18【機器可驗】 | 作法 3 A 級資格檢查 | 例外 | 臨時 JSON，一條 `grade: "A"` 但 `link: ""` | 呼叫 schema 驗證 | 丟錯，訊息點出 id 與「A 級不得沒有連結」之意 | 自動 |
| TC-D19【機器可驗】 | 作法 1；test_dc10 | 功能 | 讀 `platform/pyproject.toml` | 用 `fnmatch` 比對 package-data 的 glob 與 `data/downstream-methods.json` | 有 glob 涵蓋；`pyproject.toml` 本身未被改動 | 自動 |
| TC-D20【機器可驗】 | 範圍：僅 stdlib | 功能 | `downstream_catalog.py`、`actions/downstream.py` | 用 `ast` 列出 import | 全是標準庫（或 abf_platform 內部模組）；資料檔以 `Path(__file__).parent / "data"` 為預設路徑；沒有 socket、urllib、http、requests、yaml | 自動 |

## US2 — 查詢 `list_downstream(pipeline)` 與有效等級（P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-Q01【機器可驗】 | 完成標準 2；裁示 7 | 功能 | 套件內資料檔；`today=2026-11-17` | `downstream_catalog.list_downstream("ampliseq", today=...)` | 頂層有 `pipeline`、`methods`、`count`、`note`；`count == 9`；前六條有效等級 A、後三條 B；`count == len(methods)` | 自動 |
| TC-Q02【機器可驗】 | 完成標準 2；裁示 8 | 功能 | 同上 | `list_downstream("rnaseq", today=2026-11-17)` | `count == 10`；前九條 A、最後一條（DEBrowser）B；pcaExplorer、iSEE、DEBrowser 都在列，且 `non_interactive_plot == "needs_person"` | 自動 |
| TC-Q03【機器可驗】 | 裁示 3；作法 4 | 功能 | 同上 | 檢查每個回傳項的鍵 | 每項恰有 id、method、link、grade、declared_grade、downgraded、version_pin、license、doi、inputs、non_interactive_plot、singularity、reviewed、notes；pipeline 在頂層（維護者列的 10 類欄位都能取得） | 自動：test_ld02 |
| TC-Q04【機器可驗】 | 裁決 2；test_dc05 | 功能 | 臨時 JSON，一條 A、複審日 2026-01-01 | 以 today=2026-12-31（364 天）與 2027-01-01（365 天）算有效等級 | 兩者都維持 A（恰 365 天不降） | 自動 |
| TC-Q05【機器可驗】 | 裁示 5；裁決 2；test_dc05 | 功能 | 臨時 JSON，A、B、C 各一條，複審日 2026-01-01 | today=2027-01-02（366 天） | A→B、B→C、C→C；三條的 `declared_grade` 仍是原值，`downgraded` 依序為 true、true、false | 自動 |
| TC-Q06【機器可驗】 | 作法 3 | 功能 | 臨時 JSON | 呼叫 `list_downstream` 與有效等級計算前後比對 JSON 檔雜湊 | 檔案內容不變（人工 `grade` 不被改寫） | 自動 |
| TC-Q07【機器可驗】 | 裁示 4；作法 4；test_dc06 | 功能 | 臨時 JSON：A、B、C 各一與一條過期 B（有效 C） | 預設查詢 | 只回 A 與未過期 B；C 與過期變 C 的那條不在內 | 自動 |
| TC-Q08【機器可驗】 | 作法 4 排序；test_dc06 | 功能 | 臨時 JSON：多條 A、B，method 全用同一種大小寫、無歧義（如 alpha、beta、gamma） | 查詢兩次 | A 全在 B 前；同級依 method 字母序；兩次輸出完全相同 | 自動 |
| TC-Q09【機器可驗】 | 作法 3、4 | 功能 | 臨時 JSON：一條過期 A（有效 B）與一條未過期 B | 預設查詢 | 過期 A 以有效等級 B 列出（`grade: "B"`、`declared_grade: "A"`、`downgraded: true`），排在 B 組內 | 自動 |
| TC-Q10【機器可驗】 | 作法 3：today 可注入、預設 `date.today()` | 功能 | 臨時 JSON | 不傳 today 與傳 `date.today()` 各查一次 | 兩者結果相同 | 自動 |
| TC-Q11【機器可驗】 | 維護者「如果沒有，就是使用者跟你討論繪製」；作法 4；test_dc07 | 例外 | 套件資料 | `list_downstream("scrnaseq")` | 不丟錯；回 `{"pipeline": "scrnaseq", "methods": [], "count": 0, "note": "no certified downstream methods for this pipeline"}`（note 字串逐字相同） | 自動 |
| TC-Q12【機器可驗】 | 作法 4「不猜近似」 | 例外 | 套件資料 | `list_downstream("ampliseqq")` | 回空結果，不回 ampliseq 的條目 | 自動 |
| TC-Q13【機器可驗】 | 作法 4；test_dc08 | 例外 | 無 | `list_downstream("")` | 丟 `ValueError` | 自動 |
| TC-Q14【機器可驗】 | 裁示 8；test_dc09 | 功能 | 套件資料 | 查 rnaseq，看 pcaExplorer／iSEE／DEBrowser 三項 | 值原樣為 `"needs_person"`，不被轉成 true 或 false | 自動 |
| TC-Q15【機器可驗】 | 裁示 5；完成標準 4 | 功能 | 套件真實資料；`today=2027-11-09`（距複審日 367 天） | 查 ampliseq | 原 A 六條以有效等級 B 列出（`downgraded: true`）；原 B 三條變 C 不列；`count == 6` | 自動 |
| TC-Q16【機器可驗】 | 範圍：唯讀 | 功能 | 套件資料檔 | 呼叫查詢前後比對資料檔雜湊與目錄內檔案清單 | 完全沒變，沒有新檔 | 自動 |

## US3 — MCP 工具、問了才列、文件與既有測試同步（P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-M01【機器可驗】 | 裁示 6；作法 5；test_ld01 | 功能 | `build_server` 建好的伺服器 | 列出工具 | 有 `list_downstream`；`read_only_hint is True`；inputSchema 只有必填字串 `pipeline` | 自動：`test_mcp_list_downstream.py` |
| TC-M02【機器可驗】 | test_ld02；完成標準 2 | 功能 | 同上 | 透過 MCP 呼叫 `{"pipeline":"ampliseq"}` | 回傳 `count` 與各項 id 和直接呼叫 `downstream_catalog.list_downstream("ampliseq")` 相同；每項有 TC-Q03 列的鍵（此測試不寫死 A／B 筆數，見備註 1） | 自動 |
| TC-M03【機器可驗】 | 作法 4；專長守則錯誤訊息 | 例外 | 同上 | 透過 MCP 呼叫 `{"pipeline":""}` | 回工具錯誤（isError），形狀與既有 `describe_module` 傳空名稱時相同；訊息說明原因（pipeline 不能是空的）與處理（給 ampliseq 或 rnaseq 等 pipeline 名稱）；不含堆疊、內部路徑 | 自動：另補 `test_mcp_contract_writes.py` 的 ERROR_INPUTS 一筆 |
| TC-M04【機器可驗】 | 專長守則：日誌與回應不含密鑰 | 例外 | 環境放一個測試用假 token 字串 | 呼叫成功與失敗各一次，收集回應與日誌輸出 | 假 token 不出現在任何一處 | 自動 |
| TC-M05【機器可驗】 | 作法 4 | 例外 | 同 M01 | 透過 MCP 呼叫 `{"pipeline":"scrnaseq"}` | 不是工具錯誤；回 `count: 0`、note 同 TC-Q11 | 自動 |
| TC-M06【機器可驗】 | 作法 5；完成標準 3 | 功能 | 同 M01 | 數工具 | 共 23 個、唯讀 16 個；非唯讀工具名單與 base（origin/v3）完全相同（沒新增寫入工具） | 自動 |
| TC-M07【機器可驗】 | 作法 5；test_ld04 | 功能 | 讀 `mcp_server.py` | 用 `ast` 看 `list_downstream` 工具函式 | 本體只有一次對 `downstream_actions.list_downstream` 的呼叫；函式定義在 `build_server` 本體之外（`test_tca13` 維持綠） | 自動 |
| TC-M08【機器可驗】 | 專長守則：對等性；test_ld05 | 功能 | 讀 `actions/downstream.py`、`actions/__init__`、`test_actions_layer.py` | 同時列舉兩邊：MCP 工具名單（含 list_downstream）與動作層函式 | `actions/downstream.py` 有同名 `list_downstream`，只呼叫 `downstream_catalog.list_downstream`，沒有第二份邏輯；`not hasattr(abf_platform.actions, "list_downstream")`；`test_actions_layer.py` 新增獨立的 `DOWNSTREAM_NAMES`（不塞進 `CANVAS_NAMES`），tca02、tce01 對它查 `abf_platform.actions.downstream`；缺任一邊測試就紅；`test_web_parity.py` 不動且綠 | 自動 |
| TC-M09【機器可驗】 | 作法 5；test_ld06 | 功能 | 同 M01 | 讀工具描述與參數描述 | 描述 ≤ 600 字元；`pipeline` 參數有描述；通過 `tests/mcp/test_mcp_contract_tools.py` 的 lint；描述明講五件事：唯讀、只列已認證方法、使用者問了才呼叫、不執行任何分析、C 級不列（驗收者讀描述確認） | 自動 |
| TC-M10【機器可驗】 | 維護者「Q15你問了才列」；裁示 2；作法 4；test_ld03 | 功能 | 目錄的 19 個 method 字串 | 檢查 `server.instructions`、`guidance.routing_instructions()`、`CHAT_SYSTEM_PROMPT` 及 `mcp_server.py` 內其他 prompt／說明常數 | 都不含任何一個 entry 的 method（至少含「ANCOM-BC」「MaAsLin2」「DESeq2」「clusterProfiler」與 19 個完整 method 字串）；目錄內容只在工具被呼叫時回傳 | 自動 |
| TC-M11【機器可驗】 | 範圍：chat_tools；環境事實 | 功能 | `chat_tools.py` | 跑 `test_chat_tools.py` | `list_downstream` 在 `READ_ONLY` 集合內被 `classify_check` 接受；`CHAT_SYSTEM_PROMPT` 若新增一行，只講工具用途、含 `list_downstream` 一詞、不含方法名；若 executor 不改，ledger 有說明理由 | 自動 |
| TC-M12【機器可驗】 | 範圍：snapshot；完成標準 3 | 功能 | `git diff origin/v3 -- platform/tests/mcp/snapshots/tools.json` | 讀差異 | 只新增 `list_downstream` 一筆（name＋inputSchema），其他工具一字未動 | 自動 |
| TC-M13【機器可驗】 | 作法 7；完成標準 6 | 功能 | `mcp_server.py` 檔頭與 docstring | 跑 `test_mcp_server_doc.py` | 第 1 行註解與 docstring 為「sixteen read-only tools」，名單含 `list_downstream`；測試綠 | 自動 |
| TC-M14【機器可驗】 | 作法 7；完成標準 6 | 功能 | `docs/PLATFORM.md`、`tests/platform_storage_doc_test.sh` | 讀文件並跑該 shell 測試與 `test_job_kinds_docs.py` | 439 行為「Twenty-three tools. Sixteen are read-only」且名單含 `list_downstream`；第 6 行「nine read-only tools」原樣；新增一小節講目錄、A／B／C 等級、12 個月降級、問了才列；shell 測試的錨點改為「Twenty-three tools.」且綠；`test_job_kinds_docs.py` 能解析新數字詞 | 自動 |
| TC-M15【機器可驗】 | 計畫「必須同步改的既有測試」 | 功能 | 計畫表列出的既有測試檔 | 逐檔看 `git diff origin/v3`，並跑這些被改的測試檔 | 差異只有計數（22→23、15→16）與名單加 `list_downstream`；沒有刪除或放寬任何其他斷言；`test_mcp_canvas_read.py`、`test_web_parity.py`、`test_k8s_launch.py`、`tests/no_second_run_state_test.sh` 若未改則仍綠；全部綠 | 自動 |
| TC-M16【機器可驗】 | 裁決 5；專長守則 migration | 功能 | 讀 diff | 看 `store.py` 與 migration 目錄，跑 `test_no_schema_change` | 兩者都沒被動；測試綠；不需要 migration | 自動 |
| TC-M17【機器可驗】 | 專長守則：跨使用者 | 功能 | 兩個不同使用者身分各自的 token（PAT） | 各自呼叫 `list_downstream({"pipeline":"ampliseq"})` | 兩人得到完全相同的目錄結果；回傳不含任何使用者、run、路徑資料（目錄是全站共用的唯讀資料，沒有「別人的紀錄」可讀可改） | 自動 |
| TC-M18【機器可驗】 | 專長守則：確認管道、寫入 | 功能 | 一個沒有 `platform.db` 的空平台資料夾 | 呼叫 `list_downstream` | 照常回傳；沒有建立資料庫或任何新檔；沒有產生待確認請求（工具沒有寫入路徑，不需要確認） | 自動 |
| TC-X01【實機驗】 | 維護者「Q15你問了才列」；裁示 2 | 功能 | 真實 MCP 客戶端接上本平台，使用者與模型已在討論一個 ampliseq 結果 | 使用者說「ampliseq 跑完了，有哪些認證過的下游分析方法可以用？」 | 模型呼叫 `list_downstream`，回答把 A 級列在 B 級前；互動式工具對使用者標為「需人操作」；不自己編造方法 | 手動：由 worker 或維護者跑並留紀錄 |
| TC-X02【實機驗】 | 維護者「Q15你問了才列」；裁示 2 | 功能 | 同上，使用者在問 ampliseq 怎麼啟動、參數怎麼設 | 使用者全程沒提下游分析 | 模型不呼叫 `list_downstream`，也不主動列任何下游方法 | 手動：同上 |

## US4 — 過期檢查腳本 `scripts/check_downstream_catalog.py`（P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-S01【機器可驗】 | 作法 6；完成標準 4；test_dc11 | 功能 | 套件資料；從別的工作目錄用 `sys.executable -I` 執行；`--today 2026-11-17`、不給 `--path` | 執行腳本 | 退出碼 0；預設讀 `platform/abf_platform/data/downstream-methods.json` | 自動：`test_downstream_catalog.py` |
| TC-S02【機器可驗】 | 裁示 5；test_dc11 | 功能 | 臨時 JSON：一條 A、複審日 2026-01-01；`--path`、`--today 2027-01-15`（379 天） | 執行 | 退出碼 1；輸出含該條 id、複審日 `2026-01-01`、天數 379、宣告 A→有效 B | 自動 |
| TC-S03【機器可驗】 | 裁決 2 邊界 | 功能 | 套件資料；`--today 2027-11-07`（恰 365 天） | 執行 | 退出碼 0 | 自動 |
| TC-S04【機器可驗】 | 裁決 2 邊界；完成標準 4 | 功能 | 套件資料；`--today 2027-11-08`（366 天） | 執行 | 退出碼 1；輸出列出 19 條的 id、複審日 2026-11-07、366 | 自動 |
| TC-S05【機器可驗】 | 作法 6 schema 違規 | 例外 | 臨時 JSON 缺一個必填鍵（如沒有 `license`） | 執行 | 退出碼 2；訊息點出 id 與缺的鍵 | 自動 |
| TC-S06【機器可驗】 | 作法 6 | 例外 | 臨時 JSON `grade: "D"` | 執行 | 退出碼 2 | 自動 |
| TC-S07【機器可驗】 | 作法 6 | 例外 | 臨時 JSON `reviewed: "11/07/2026"` | 執行 | 退出碼 2 | 自動 |
| TC-S08【機器可驗】 | 作法 6；裁示 9 | 例外 | 臨時 JSON：`doi: null` 但 `notes` 無「查不到」 | 執行 | 退出碼 2 | 自動 |
| TC-S09【機器可驗】 | 作法 6 | 例外 | 臨時 JSON：兩條 id 相同 | 執行 | 退出碼 2；訊息點出重複的 id | 自動 |
| TC-S10【機器可驗】 | 裁決 2 | 例外 | 臨時 JSON：`non_interactive_plot: null` 但 `notes` 無「待驗證」 | 執行 | 退出碼 2 | 自動：另補一條測試 |
| TC-S11【機器可驗】 | 作法 3 | 例外 | 臨時 JSON：A 級、`link` 為空字串 | 執行 | 退出碼 2 | 自動 |
| TC-S12【機器可驗】 | 作法 6「列出全部違規」 | 例外 | 臨時 JSON：同時有兩種違規（缺鍵與 grade 為 D） | 執行 | 退出碼 2；兩種違規都出現在輸出，不是只報第一個 | 自動 |
| TC-S13【機器可驗】 | 作法 6：只用 stdlib、不寫檔、不連網 | 功能 | 腳本檔；一個臨時工作目錄 | 用 `ast` 看 import；執行前後比對目錄與資料檔雜湊 | import 全是標準庫，沒有 socket、urllib、http、requests；沒有新增或改動任何檔 | 自動 |
| TC-S14【機器可驗】 | 作法 6「變動者」 | 功能 | 臨時 JSON：一條過期 A、一條未過期 A | 執行 | 退出碼 1；輸出只列過期那條，未過期的不被當成變動 | 自動 |

## 範圍管控與不在範圍（P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-N01【機器可驗】 | 完成標準 7；範圍：檔案 | 不在範圍 | 完成後的分支 | `git diff --stat origin/v3...HEAD` | 只含計畫「範圍：檔案」所列檔與「必須同步改的既有測試」表所列檔；沒有其他檔 | 自動：驗收讀 diff |
| TC-N02【機器可驗】 | 不做：不預寫下游腳本、不做畫圖執行 | 不在範圍 | 同上 | 看 diff 新增檔 | 沒有 `.R`、`.Rmd`、`.qmd` 檔；沒有任何會讀 pipeline 輸出、畫圖、產生報告的程式；目錄裡每條只是資料 | 自動 |
| TC-N03【機器可驗】 | 不做：不自動推送、不改 SKILL.md；維護者「Q15你問了才列」 | 不在範圍 | 同上 | 看 diff | 任何 `skills/*/SKILL.md` 與 `skills/downstream/` 沒被動；沒有任何自動列目錄的程式路徑 | 自動 |
| TC-N04【機器可驗】 | 不做：不做 C 級列出參數 | 不在範圍 | 同上 | 看 `downstream_catalog.list_downstream` 簽名與工具 inputSchema | Python 函式參數只有 `pipeline`、`today`、`path`；工具 schema 只有 `pipeline`；沒有 include_c 之類參數；透過工具查不到 C 級 | 自動 |
| TC-N05【機器可驗】 | 不做：不做網頁頁面、不做寫入工具 | 不在範圍 | 同上 | 看 diff 與 `test_web_parity.py` | 沒有新增或改動 `web_*.py`、網頁路由；`test_web_parity.py` 綠；寫入工具名單未變（見 TC-M06） | 自動 |
| TC-N06【機器可驗】 | 不做：不做 YAML 版 | 不在範圍 | 同上 | 看 diff | 沒有 `.yaml`／`.yml` 檔；沒有 yaml import；`pyproject.toml` 未改 | 自動 |
| TC-N07【機器可驗】 | 不做：不做排程 | 不在範圍 | 同上 | 看 diff | `.github/` 與任何排程登記檔未被動；腳本不被其他程式自動呼叫 | 自動 |
| TC-N08【機器可驗】 | 不做：不對 differentialabundance 實測 | 不在範圍 | 同上 | 看 JSON 與 ledger | 沒有任何 `singularity: "ok"`；differentialabundance 仍是 "untested"＋「待實測」；ledger 沒有 nano4 實測紀錄 | 自動 |
| TC-N09【機器可驗】 | 不做：不補第一批以外的 pipeline | 不在範圍 | 同上 | 查 `list_downstream("atacseq")` 與 JSON 的 pipeline 欄 | 回空結果與 TC-Q11 的 note；JSON 只有 ampliseq 與 rnaseq | 自動 |
| TC-N10【機器可驗】 | 裁決 3 | 不在範圍 | 同上 | 搜 JSON 內「tximeta」 | 找不到任何 tximeta 條目（也不在 notes 之外的欄位出現）；目錄沒有名單外條目 | 自動 |
| TC-N11【機器可驗】 | 範圍「不碰」 | 不在範圍 | 同上 | 看 diff | `platform/pyproject.toml`、`platform/abf_station/`、`.github/` 完全未動 | 自動 |
| TC-N12【機器可驗】 | 完成標準 7；裁決 3、6 | 功能 | executor 的 ledger | 讀 ledger | 內有：`git diff --stat`；兩次 `git grep` 輸出（動手前、完成前）；每條目的來源網址；「種子檔有 tximeta，依裁決未收」一行；vegan 與 MaAsLin2 等級爭議；每處「轉換補註記」（notes 補的「查不到」「待驗證」）的清單；邊界日規則（大於 365 天才降） | 自動：驗收讀 ledger（路徑由 executor 在報告中指出） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-C01【機器可驗】 | 第 1 條：scripts 要寫明「不是哪個既有工具」 | 功能 | `scripts/check_downstream_catalog.py` | 跑 `bash tests/scripts_name_their_alternative.sh` | 腳本前 40 行有 `# Not <外部工具>: <理由>` 或 `# Nothing existing: <why>`；測試綠 | 自動 |
| TC-C02【機器可驗】 | 第 3 條：不寫死個人／叢集路徑 | 功能 | 新增與改動的檔 | 跑 `bash tests/no_hardcoded_paths.sh`，並搜新檔 | 綠；資料檔、程式、腳本沒有 `C:\Users`、`G:\`、家目錄路徑 | 自動 |
| TC-C03【機器可驗】 | 第 2 條：沒有第二份 run 狀態 | 功能 | 新增程式 | 跑 `bash tests/no_second_run_state_test.sh` | 綠；目錄不是 run 狀態，不寫 `platform.db`、不建狀態機 | 自動 |
| TC-C04【機器可驗】 | 第 6 條：不要每個 pipeline 一份設定 | 功能 | 新增程式與資料 | 跑 `bash tests/no_per_pipeline_config.sh`；搜誰 import `downstream_catalog` | 測試綠；目錄只被 `actions/downstream.py`、`scripts/check_downstream_catalog.py` 與測試用，沒有任何啟動、資源對映、samplesheet 程式讀它（目錄只是讓使用者查的參考，不驅動任何執行） | 自動 |
| TC-C05【機器可驗】 | 安全網（hooks／閘門） | 不在範圍 | 同 N01 | 看 diff | `hooks/` 與安全網相關腳本與測試完全沒被動 | 自動 |

## 總覽

| 區塊 | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 目錄資料（D01～D20） | 18 | 2 | 0 | 20 |
| US2 查詢與有效等級（Q01～Q16） | 13 | 3 | 0 | 16 |
| US3 MCP 工具、問了才列、文件與既有測試（M01～M18、X01、X02） | 17 | 3 | 0 | 20 |
| US4 過期檢查腳本（S01～S14） | 6 | 8 | 0 | 14 |
| 範圍管控與不在範圍（N01～N12） | 1 | 0 | 11 | 12 |
| 憲法與安全網（C01～C05） | 4 | 0 | 1 | 5 |
| **合計** | 59 | 16 | 12 | 87 |

【機器可驗】85 條、【實機驗】2 條（TC-X01、TC-X02）。

覆蓋檢查（逐項數過）：

- 維護者原話 2 句與同日裁示 9 項：全部有對應 TC（見檔首對照）。
- 計畫「失敗先行測試」23 條（test_dc01～dc11、test_ld01～ld06 及 dc 的子項）：全部有對應 TC。
- 計畫「不做」7 項（不預寫腳本、不自動推送、不做 C 級參數與 UI、不做網頁、不做 YAML、不做排程、不做實測、不補其他 pipeline）：N02～N09 各有 TC。
- lead 兩次裁決共 11 點：裁決 1→D08、D10；2→D12、D13、S10；3→N10、N12；4→D14、D04、D05；5→M16；6→D15、N12；邊界日→Q04、Q05、S03、S04。
- 專長守則（backend）：對等性→M08；跨使用者→M17（目錄為共用唯讀資料，無「別人的紀錄」，故以身分無差別＋無資料庫存取證明）、M18；確認管道→M06、M18（沒有寫入路徑）；錯誤訊息與日誌→M03、M04；migration→M16。

## 給維護者的備註

計畫審查結論：計畫無阻擋問題。計畫本文有兩處與後續裁決不一致，以裁決與本檔 TC 為準，executor 不必再問：（a）`test_dc01` 的 `non_interactive_plot` 允許值要加 `null`；（b）計畫第 2 節說 pcaExplorer、iSEE 等級由 executor 決定，裁決 4 已定為 A（DEBrowser 為 B），所以 rnaseq 共 10 條（A 九、B 一），不是「至少 9 條」。

我（撰寫者）不確定、但不影響上面任何一條判定的地方，各一句話請你有空回答：

1. **時間炸彈**：目錄複審日是 2026-11-07，過了 2027-11-07 後，連 MCP 這一層用真實日期查詢時，A 級會變 B、B 級會變 C 而不再列出，這是設計好的行為。所以本檔所有寫死筆數的測試（Q01、Q02、S01、S04）都用注入的今天；MCP 層測試（M02）只比對「與直接呼叫一致」，不寫死 A／B 筆數。executor 若在 MCP 層寫死筆數，兩年內會自己變紅。
2. **標籤誰來翻**：計畫說互動式工具「對外顯示需人操作」、differentialabundance「顯示待實測」，但也說回傳值「原樣帶出」。本檔只要求回傳 `needs_person`、`untested` 原值（TC-Q14、D06）。若你要工具回傳的文字直接帶中文標籤，請告訴我，要加一條 TC。
3. **同級排序大小寫**：計畫只說「method 字母序」，沒說大小寫是否分。TC-Q08 用同一種大小寫的假名稱，避開這個歧義。
4. **A 級空連結規則在哪裡擋**：計畫第 3 節說要擋，但沒說放在載入驗證還是腳本。本檔要求兩處都擋（D18、S11），因為腳本本來就走同一份驗證。
5. **pcaExplorer、iSEE、DEBrowser 的輸入路徑**：種子檔給的是路徑、但角色說明裡寫「相容性未驗證（待驗證）」。裁決 6 說描述一律比照 `inputs: []`，但這三條給的是路徑不是純描述。本檔沒對這三條的 `inputs` 做特定要求（TC-D15 只要求空 list 必須帶「待驗證」、非空每項要有路徑與用途），executor 留路徑或清空都過；你若想統一標準，需另裁。
6. **同時過期又 schema 違規時退出碼**：計畫沒寫優先順序（1 或 2），本檔不檢查這種混合情況。
7. **ledger 路徑**：計畫沒指定 ledger 檔在哪裡，TC-N12 假定 executor 會在報告中指出路徑；找不到就是 UNVERIFIED。
8. **憲法第 6 條的張力**：憲法第 6 條的理由寫明 v1 就是死在「每個 pipeline 一份人工維護的清單」。這個目錄是你 2026-11-07 明確裁示要做的，且只讀、不驅動任何執行（TC-C04 證明沒有啟動路徑讀它），機器檢查 `no_per_pipeline_config.sh` 也不會擋它；但「它會不會像 v1 一樣隨上游改版而過時」要靠 12 個月降級機制擋，這是設計意圖，不是本次要驗的。
9. **等級爭議仍在 lead 手上**：vegan（無同儕審查論文，嚴格算 C）與 MaAsLin2（字面符合 A）依你的名單留 B（TC-D03），ledger 要列出爭議（TC-N12）。
10. **兩條【實機驗】**：TC-X01、X02 要真實 MCP 客戶端與模型對話，機器測試證明不了「模型會不會在你沒問時自己亂列」。這兩條在有人跑並留紀錄前，驗收只能是 UNVERIFIED。
