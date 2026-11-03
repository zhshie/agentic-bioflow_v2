# 測試案例：mcp-run-file-live-fixes（run_outputs 錯誤答案不再永久沿用；.html 結果檔改給下載連結）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
來源：本任務沒有獨立的 spec.md，計畫（developer-agent 的 mcp-run-file-live-fixes.md）就是規格；
「對應需求」欄用計畫的「作法 N」與「維護者原話 N」「實測現象 Bug N」「不做」「完成標準」編號。
-->

**規格**：計畫 `mcp-run-file-live-fixes.md`（複本 `specs/mcp-run-file-live-fixes/plan.md`）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

共同說明：「30 秒門檻」指 `jobs.LISTING_ERROR_RETRY_SECONDS = 30`；時間一律用 monkeypatch `status.now` 前進，不真等待。「錯誤答案」指 `run_outputs` 回 `state: "error"` 且帶原因。自動測試都放在 `platform/tests/test_mcp_run_file_live_fixes.py`，每條測試在註解寫上它的 TC 編號。

## User Story 1 — run_outputs 的錯誤答案不再永久沿用，連線恢復後重新列出（優先度 P1）

維護者原話（計畫「維護者原話」）：「上限拉到95%，先讓「MCP 讀取／下載結果檔」在國網跑得動」→ 連線過期後重新登入，`run_outputs` 要能回到正常列表；「跟Seqera platform一樣的模式，不要自己定義」→ 錯誤不是永久答案，下一次詢問重新排工作、回 `loading`；網頁與 MCP 走同一個動作，不另寫邏輯。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1（30 秒內照舊）；Bug 1 | 功能 | 一個有啟動紀錄的 run；第一次 `run_outputs` 已排 1 筆列表工作；該工作以 `ok=False`、`site_unreachable` 結束（`state="error"`） | 結束後立刻（未滿 30 秒）再問 `run_outputs`（`relist=False`、`enqueue=True`） | 仍回 `state == "error"`，帶同一個原因與同一個 `listed_at`；列表工作總數仍是 1（沒有排新工作） | 自動：`test_mcp_run_file_live_fixes.py` |
| TC-002 | 作法 1（≥30 秒重排）；維護者原話 2；Bug 1 | 功能 | 同 TC-001 | 把 `status.now` 前進 31 秒後再問 `run_outputs`；接著在新工作還沒結束時再問一次 | 第一次回 `state == "loading"`、`listed_at is None`，列表工作總數變 2；第二次仍回 `loading`，工作總數仍是 2（在途的工作不重複排） | 自動：同上 |
| TC-003 | 維護者原話 1（重新登入後回到正常列表）；作法 1；Bug 1；MCP 路徑 | 功能 | 同 TC-001，但用 MCP 客戶端 `call_tool("run_outputs")` 問 | 依序：問（得 `loading`）→ 工作以 `site_unreachable` 結束 → 立即問（得同一錯誤、1 筆工作）→ 前進 31 秒問（得 `loading`、2 筆）→ 新工作以 `entries=ENTRIES` 結束 → 再問 | 最後一次回 `state == "ready"`、檔案清單等於 `ENTRIES`、`listed_at` 是新工作的結束時間（不是第一次錯誤的 `listed_at`）；前面各步預期同 TC-001／TC-002 | 自動：同上 |
| TC-004 | 作法 1（子路徑）；計畫測試「path=qiime2 子路徑」 | 功能 | 同 TC-003，但問的是 `path="qiime2"` 子路徑 | 子路徑的列表工作以 `site_unreachable` 結束；前進 31 秒後再問同一子路徑 | 回 `loading`；新排的那一筆工作 `args.path` 以 `/results/qiime2` 結尾（不是排頂層）；30 秒內再問仍回舊錯誤、不排 | 自動：同上 |
| TC-005 | 作法 1（所有錯誤種類都適用） | 功能 | 四種最新工作各準備一次：(a) `done` 但 `ok=False` 且 `error="not_found"`；(b) `state="refused"`；(c) `state="expired"`（`finished_at` 空，以 `deadline_at` 計年齡）；(d) `queued` 且已逾 `deadline_at` | 每一種各自把時間前進到距離參考時間（`finished_at`，空則 `deadline_at`）≥ 30 秒後問 `run_outputs` | 每一種都回 `loading`，且各自恰好多排 1 筆新工作；同樣四種在不滿 30 秒時都不排 | 自動：同上 |
| TC-006 | 作法 1（`enqueue=False` 永不排） | 例外 | 一個最新工作為錯誤、且年齡 ≥ 30 秒的 run | 呼叫 `actions.run_outputs(..., enqueue=False)`（完成階段交付清單用的看一眼模式） | 回舊的錯誤答案（含原因）；工作總數不變，沒有任何新工作 | 自動：同上 |
| TC-007 | 作法 1（`JobRefused` 轉錯誤）；專長守則（錯誤訊息） | 例外 | 錯誤工作年齡 ≥ 30 秒；`jobs.enqueue_listing` 被設成丟 `JobRefused`（例如代理離線） | 問 `run_outputs` | 回 `state == "error"`，`reason` 是白話原因（說明發生什麼事、可以怎麼處理）；不丟例外；回應不含堆疊、內部路徑或 SQL | 自動：同上 |
| TC-008 | 作法 2（網頁共用同一動作）；Bug 1（網頁 Outputs 分頁同一個 bug） | 功能 | 登入的擁有者；run 的最新列表工作是錯誤、年齡 31 秒 | (a) `GET /run?...&tab=outputs`；(b) 另一次把 `actions.run_outputs` 換成假函式（沿用 `test_ro09b` 手法）再 `GET` | (a) 頁面顯示「讀取中」，並多排 1 筆列表工作；30 秒內的同樣請求不多排；(b) 頁面照假函式的回答畫，路由處理函式沒有自己的第二份判斷；網頁「重新讀取」連結與 `relist=1` 仍會排新工作 | 自動：同上 |
| TC-009 | 作法 1（擁有者與不存在，回歸）；專長守則（跨使用者） | 例外 | 第二位使用者的 token；一個他人的 run；一個不存在的 run id | 用第二位使用者問他人 run 的 `run_outputs`，再問不存在的 id（都在錯誤年齡 ≥ 30 秒的情況下） | 兩者回同一句「找不到」（`found: False`，不透露 run 是否存在）；列表工作總數都不變 | 自動：同上 |
| TC-010 | 計畫「不做」：成功列表過期；run_file 失敗答案的 10 分鐘沿用 | 不在範圍 | (a) 一個 `ready` 的成功列表，把時間前進很久（例如一天）；(b) `read_run_file` 的檔案讀取失敗後 10 分鐘內再讀同一檔 | (a) 再問 `run_outputs`；(b) 再讀同一檔 | (a) 仍回 `ready`、原本的清單與 `listed_at`，沒有排新工作，`relist=True` 仍照舊排新工作；(b) 仍沿用舊的失敗答案（既有 `test_results_files.py` 的 tc013／tc015 維持綠、斷言未改） | 自動：同上，加既有 `test_results_files.py` |

## User Story 2 — .html／.htm 結果檔改給下載連結，不灌進模型（優先度 P1）

維護者原話：「MultiQC 報告不能把模型的 context 塞滿」；「`.html` 與其他二進位檔一樣給網頁下載網址」。實測：`multiqc/multiqc_report.html` 2,549,231 位元組被當文字回成 13 頁。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 作法 3；Bug 2；維護者原話 2 | 功能 | 站台代理回 UTF-8 的 HTML 位元組；逐一用檔名 `multiqc/multiqc_report.html`、`a.HTML`、`b.htm`、`x/y.Htm` | 呼叫 `read_run_file`（`state` 為 `ready`） | 每個都回 `found: True`、`state: "ready"`、`kind == "binary"`、`name`、`size == len(data)`、`note` 逐字等於「這是網頁檔（HTML），內容不經由 MCP 傳給模型 (HTML file; its bytes are not sent through MCP)」、`download_url` 以設定的 `web_base_url` 開頭並含 `/run/file?run=<id>&path=` 與 urlencode 過的路徑 | 自動：同上 |
| TC-012 | 作法 3（不回內容）；維護者原話 1（context 不被塞滿） | 功能 | 同 TC-011，HTML 內含 `<script>` | 讀一次；再帶 `offset=5` 讀一次 | 回應沒有 `text`、`total_chars`、`next_offset`、`b64`、`data`；`json.dumps(answer)` 不含該 HTML 內容（例如 `<script>`）；帶 `offset=5` 仍是 `binary`（offset 不生效） | 自動：同上 |
| TC-013 | 作法 3（大檔）；Bug 2 實測數字 | 功能 | (a) 2,549,231 位元組的 HTML；(b) 超過 25 MB 的 HTML | 各讀一次 | (a) 回 `binary`，不是 13 頁、沒有 `total_chars`；(b) 仍回既有的 `too_large`（既有分支優先），不變成 binary | 自動：同上 |
| TC-014 | 作法 3（文字檔判斷不變） | 功能 | 檔名 `.tsv`、`.csv`、`.txt`、`.json`、`.yml`、`.md`、`.log`、`a.html.txt`、`html`（無副檔名）、`my.htmlx`，內容皆為 UTF-8 文字；另有一個超過 200,000 字元的文字檔 | 逐一 `read_run_file` | 全部仍回 `kind == "text"`；超長文字檔仍照 200,000 字元分頁（`next_offset` 照舊）；既有 `_READ_BINARY` 的 `.png` 等二進位案例（`test_tc020_021_028`）一字不變 | 自動：同上，加既有 `test_mcp_run_file.py` |
| TC-015 | 計畫「不做」：`.svg`、`.xml`、`.pdf` 其他類型分類；站台端副檔名判斷 | 不在範圍 | UTF-8 的 `.svg`、`.xml` 檔 | `read_run_file` | 仍依既有規則（整檔嚴格 UTF-8 且無 NUL）回 `kind == "text"`，沒有被新規則改成 binary；`.html` 判斷只在平台動作層（站台代理與其 25 MB 上限未改） | 自動：同上 |
| TC-016 | 作法 4；作法 1（不改 run_outputs 描述） | 功能 | MCP 工具清單 | 讀 `read_run_file` 與 `run_outputs` 的工具描述 | `read_run_file` 描述新增一句，含 `.html`、「treated as a binary file」意思，且仍含 "the text goes to the model you chose"、"200,000"、"next_offset"、"/run/file" 及既有 `test_mcp_run_file.py` :320–335 的全部子字串；`run_outputs` 描述與 `test_actions_layer.BASELINE` 逐字相同；工具總數不變 | 自動：同上，加既有 `test_mcp_run_file.py`、`test_actions_layer.py` |
| TC-017 | 作法 5（SKILL.md 只加新行）；完成標準（docs 更新） | 功能 | `skills/downstream/SKILL.md`、凍結基準 `platform/tests/fixtures/downstream_SKILL_v3_baseline.md`；`docs/PLATFORM.md` | 比對 SKILL.md 與基準；讀 `downstream` 提示詞；讀 PLATFORM.md | 基準的每一舊行依序都仍在 SKILL.md（`test_tc036_037` 綠）；新增行含 `.html` 的說明（給網頁下載網址，與二進位檔一樣）；新增行不含 multiqc、qiime2、slurm、nano4、ampliseq；PLATFORM.md 的 MCP 一節提到 `.html` 與「錯誤約 30 秒後重查」 | 自動：同上，加既有 `test_mcp_run_file.py`、`tests/no_per_pipeline_config.sh` |
| TC-018 | 完成標準（手動步驟）；維護者原話 1、2；Bug 1、Bug 2 | 功能 | 維護者在 nano4 上的 run `ampliseq_day5_nano4_r5`（`ae0d52e5e5fe5a98`）；`docs/TESTING.md` 有新小節「重新登入後 run_outputs 重查 (mcp-run-file-live-fixes)」 | 照小節四步：(1) 讓 ControlMaster 過期，`run_outputs(run_id)` 得到重新登入的 `error`；(2) 重新登入、等 30 秒後再問：回 `loading`，幾秒後再問回 `ready`（網頁 Outputs 分頁同樣）；(3) `read_run_file(run_id, "multiqc/multiqc_report.html")`；(4) `read_run_file` 讀 `multiqc/multiqc_data/multiqc_general_stats.txt` | (1) 得到要重新登入的錯誤；(2) 不再永遠回同一個舊錯誤，回到正常列表；(3) 回名稱、大小、說明與 `/run/file?...` 網址，沒有 HTML 內文；(4) 仍得到文字內容。四步在 TESTING.md 寫得夠具體可照做，且同節第 4 點「MCP reads a result file」加了 `.html` 例子 | 手動：`docs/TESTING.md`（mcp-run-file-live-fixes 小節） |

## 憲法與安全網

本任務只多排一筆既有種類的 `list_site_files` 讀取工作，並改 `.html` 的分類；可能碰到的條目：原則 I 第 2 條（不得保有第二份 run 狀態、無新狀態機）、原則 II 第 4 條與原則 III 第 6 條（SKILL 新行不點名排程器、流程或管線；見 TC-017）、安全網「憑證不得出現在輸出」與「寫入類工具需人工確認」。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 安全網：憑證不得印出或留在回應／日誌；專長守則（錯誤訊息與日誌不含密鑰） | 例外 | 沿用既有洩漏掃描夾具；run 的最新工作是含一個假 token／密鑰字串的錯誤，且年齡 ≥ 30 秒 | 走完重查路徑：30 秒內問、31 秒後問、`JobRefused` 時問（網頁與 MCP 各一次），並讀 HTML 的 `read_run_file` | 所有回應與日誌都不含該假 token、密鑰、堆疊或 SQL；錯誤訊息仍說明原因 | 自動：同上 |
| TC-020 | 原則 I 第 2 條（無第二份 run 狀態）；安全網寫入工具規則（不新增寫入工具）；專長守則（動作層唯一、migration） | 功能 | 完成後的 diff 與既有被釘住的測試 | 檢查 `git diff --stat` 與以下既有測試 | 沒有新增工具（`test_pat.py:384` 的 21 不變、`test_results_files.test_tc039_no_new_mcp_tool`、`test_mcp_server_doc.py`、`test_actions_layer.py` 綠）；沒有新工作種類、資料表或 migration；`web*.py`、`abf_station/`、`store.py`、`run_file()` 無改動；`jobs.py` 只多一個 `LISTING_ERROR_RETRY_SECONDS = 30`（緊鄰 `RUN_FILE_CACHE_SECONDS`）；`mcp_server.py` 只在 `read_run_file` 描述加一句；計畫列出的既有測試（`test_ro05*`、`test_ro07`、`test_ro09*`、`test_ro10`、`test_ro12`、`test_ro14`、`test_results_files.py` tc005／tc006／tc013／tc015／tc036_045、`test_mcp_run_file.py` 各條、`test_web_parity.py`、`test_owner_guard.py`、`test_owner_tokens.py`）斷言語意未被刪改、全綠 | 自動：既有測試；diff 由驗收者讀 |
