# 測試案例：自訂 pipeline 匯出成可獨立執行的 zip（動作層）

**規格**：`specs/pipeline-export-zip/plan.md`（此任務沒有獨立的 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

名詞：「pipeline」是使用者在畫布上拖出來的一張分析流程圖，一個 pipeline 有好幾個「版本」。「匯出」是把某一版連同用到的 nf-core 模組檔打包成一個 zip 檔，解開就能執行。「甲、乙」是兩位不同的實驗室使用者。「空跑」指 `nextflow run . -stub-run`，只檢查流程能不能組起來，不真的算資料、不花 SU（叢集運算額度）。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

測試檔：除非另外註明，「自動」指 `platform/tests/test_pipeline_export.py`。

## User Story 1 — 把某一版匯出成可獨立執行的 zip（優先度 P1）

維護者原話（017b）：「actions：`compose_pipeline`、`list_pipelines`、`get_pipeline_version`、`export_pipeline`（zip）。」「done：fastqc→multiqc 圖產出可 `-stub-run` 的 zip。」裁示 5：「匯出 zip」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫·失敗先行測試 1；017b done「fastqc→multiqc 圖產出 zip」 | 功能 | 甲有一個 pipeline：fastqc 節點接 multiqc 節點，存成第 1 版 | 甲匯出這個 pipeline | 回應 `ok` 為 True，`zip` 是一串位元組、能被當成 zip 打開；zip 內有 `main.nf`、`nextflow.config`、`modules.json` 三個檔 | 自動 |
| TC-002 | 計畫·失敗先行測試 1；017b done | 功能 | 同 TC-001 | 甲匯出 | zip 內有 fastqc 與 multiqc 兩個模組各自的 `modules/nf-core/…/main.nf` | 自動 |
| TC-003 | 計畫·介面（filename） | 功能 | 同 TC-001，pipeline 名稱為普通名稱（例如 `qc-demo`） | 甲匯出 | `filename` 恰為 `<名稱>-v1.zip`（例如 `qc-demo-v1.zip`） | 自動 |
| TC-004 | 計畫·做法「重用 render_pipeline 的檔案」 | 功能 | 同 TC-001 | 甲匯出，並用同一版呼叫 `render_pipeline` | zip 內 `main.nf`、`modules.json`、`nextflow.config` 的文字，與 `render_pipeline` 回的同名檔逐字相同 | 自動 |
| TC-005 | 計畫·做法「用 files_for 補模組檔」 | 功能 | 同 TC-001，模組來源用測試替身 | 甲匯出 | `module_sources.files_for` 回的每一個檔都在 zip 內，路徑與文字逐字相同 | 自動 |
| TC-006 | 計畫·介面（files 欄） | 功能 | 同 TC-001 | 甲匯出 | 回應的 `files` 是排序後的路徑清單，且與 zip 內的檔案路徑完全一致（不多不少） | 自動 |
| TC-007 | 計畫·介面（open_inputs 欄） | 功能 | 同 TC-001，fastqc 的輸入沒接線（未填輸入） | 甲匯出，並用同一版呼叫 `render_pipeline` | 回應的 `open_inputs` 與 `render_pipeline` 回的 `open_inputs` 相同 | 自動 |
| TC-008 | 計畫·失敗先行測試 7；017b done「可 -stub-run 的 zip」 | 功能 | 同 TC-001；測試環境裝有 `nextflow`（沒有則本條標 UNVERIFIED，其他條仍須全綠） | 把 zip 解開到一個全新的暫存資料夾，在裡面執行 `nextflow run . -stub-run` | 指令成功結束（結束碼 0）；過程不連叢集、不用平台資料夾 | 自動 |
| TC-009 | 計畫·裁決 2（zip 內附短說明） | 功能 | 同 TC-001，有未填輸入 | 甲匯出 | zip 內多出一份說明檔（不屬於專案三檔、也不屬於模組檔），文字很短，並寫出每一個未填輸入的名稱，讓別人解開就知道哪些要自己填 | 自動 |
| TC-010 | 計畫·失敗先行測試 3（不指定版本取最新版） | 功能 | 甲的 pipeline 有第 1 版與第 2 版，兩版的圖不同 | 甲匯出，不指定版本 | `filename` 是 `<名稱>-v2.zip`，zip 內容對應第 2 版的圖 | 自動 |
| TC-011 | 計畫·失敗先行測試 3（指定舊版） | 功能 | 同 TC-010 | 甲匯出，指定 `version=1` | `filename` 是 `<名稱>-v1.zip`，zip 內 `main.nf` 與 `render_pipeline` 第 1 版相同，而不是第 2 版的內容 | 自動 |
| TC-012 | 計畫·失敗先行測試 2（確定性） | 功能 | 同 TC-001 | 甲對同一版匯出兩次，兩次之間隔開一段時間 | 兩次的 `zip` 位元組完全相同 | 自動 |
| TC-013 | 計畫·做法（排序、固定時間戳、固定壓縮） | 功能 | 同 TC-001 | 甲匯出，逐一檢查 zip 內每個條目 | 條目依路徑排序；每個條目的時間戳都是 1980-01-01；所有條目用同一種壓縮方式 | 自動 |
| TC-014 | 計畫·裁決 3（不要求驗證） | 功能 | 甲的 pipeline 從來沒有驗證過 | 甲匯出 | 匯出成功（`ok` 為 True），沒有因為「還沒驗證」被擋 | 自動 |
| TC-015 | 計畫·裁決 3（有驗證結果就附上） | 功能 | 甲已對這一版做過驗證（`validate_pipeline`） | 甲匯出 | 回應有 `validation` 欄，內容與 `get_validation` 回的這一版結果相同 | 自動 |
| TC-016 | 計畫·裁決 3（不擋） | 功能 | 甲這一版的驗證結果含錯誤（驗證沒通過） | 甲匯出 | 仍然匯出成功，`validation` 欄如實附上那些錯誤 | 自動 |
| TC-017 | 計畫·「不寫檔案到磁碟」 | 功能 | 記下平台資料夾與目前工作資料夾的檔案清單 | 甲匯出（成功） | 匯出前後兩個資料夾的檔案清單相同；zip 只以位元組回傳 | 自動 |
| TC-018 | 計畫·環境「不需 migration：不改資料表」 | 功能 | 記下 pipeline 相關資料表的欄位結構 | 甲匯出（成功） | 匯出後資料表的欄位結構與匯出前完全相同，沒有新增資料表或欄位 | 自動 |

## User Story 2 — 失敗與別人的 pipeline（優先度 P1）

維護者原話（裁示 16）：「自訂 pipeline 分享只在實驗室內＋匯出 zip，不做公開庫」。擁有者規則：使用者只能看到與修改自己的紀錄。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 計畫·失敗先行測試 4；專長守則（跨使用者，讀） | 例外 | 甲有一個 pipeline | 乙用自己的身分匯出甲的 pipeline | `ok` 為 False，回「找不到」，沒有 `zip`，也沒有甲的模組或檔名資訊 | 自動 |
| TC-021 | 計畫·失敗先行測試 4「不洩漏是否存在」 | 例外 | 甲有一個 pipeline（編號 A）；另有一個不存在的編號 B | 乙分別匯出 A 與 B | 兩次回應的措辭相同（只差編號本身），乙分辨不出 A 是「存在但不是我的」還是「不存在」 | 自動 |
| TC-022 | 專長守則（跨使用者，寫） | 例外 | 甲有一個 pipeline，並已記下它的各版本與驗證結果 | 乙匯出甲的 pipeline（被拒絕）之後 | 甲的 pipeline、版本與驗證結果完全沒變 | 自動 |
| TC-023 | 計畫·失敗先行測試 5 | 例外 | 甲的 pipeline 用到的某個模組，模組檔找不到（`files_for` 丟 ValueError，原因為模組缺） | 甲匯出 | `ok` 為 False；訊息點名是哪個模組，並說明怎麼處理（例如換模組或請維護者補上） | 自動 |
| TC-024 | 計畫·失敗先行測試 5「不留半個 zip」 | 例外 | 同 TC-023 | 甲匯出 | 回應沒有 `zip`，磁碟上也沒有留下任何 zip 或半成品檔 | 自動 |
| TC-025 | 計畫·失敗先行測試 5 | 例外 | 甲的 pipeline 用到平台不支援的模組（`files_for` 丟 ValueError，原因為不支援） | 甲匯出 | `ok` 為 False；訊息點名模組並說明怎麼處理 | 自動 |
| TC-026 | 計畫·失敗先行測試 5「不留半個 zip」 | 例外 | 同 TC-025 | 甲匯出 | 回應沒有 `zip`，磁碟上沒有留下任何檔 | 自動 |
| TC-027 | 計畫·失敗先行測試 6（MAX_BYTES） | 例外 | 甲的 pipeline 全部檔案合計超過 2 MiB（`pipeline_launch.MAX_BYTES`），可用測試替身的大模組檔造出 | 甲匯出 | `ok` 為 False；訊息講明檔案太大、上限是多少、該怎麼辦（例如減少節點） | 自動 |
| TC-028 | 計畫·失敗先行測試 6（MAX_FILES） | 例外 | 甲的 pipeline 檔案數超過 2000（`pipeline_launch.MAX_FILES`），可用測試替身造出 | 甲匯出 | `ok` 為 False；訊息講明檔案太多、上限是多少、該怎麼辦 | 自動 |
| TC-029 | 計畫·做法「走同一套上限，不另寫第二份」 | 例外 | 把 `pipeline_launch.MAX_BYTES` 調低（或把 `MAX_FILES` 調低）到小於 TC-001 那個小 pipeline 的實際大小（或檔案數） | 甲匯出 TC-001 的 pipeline | 匯出被拒絕，訊息提到上限；把上限還原後同一個 pipeline 又能匯出。證明上限是 `pipeline_launch` 的那一份 | 自動 |
| TC-030 | 計畫·介面（失敗回 `_no(...)` 同樣的錯誤形狀） | 例外 | 甲的 pipeline 只有第 1 版 | 甲匯出，指定 `version=5` | `ok` 為 False，沒有 `zip`；訊息說明沒有這個版本，並告知已有哪些版本 | 自動 |
| TC-031 | 計畫·介面「點名原因與怎麼辦」；專長守則（錯誤訊息） | 例外 | 分別製造：找不到、模組缺、模組不支援、超過大小、超過檔數、沒有此版本 | 逐一匯出 | 每一種失敗的 `message` 都同時說了「發生什麼事」與「該怎麼處理」，且回應格式與其他 pipeline 動作的失敗相同（有 `ok: False` 與 `message`） | 自動 |
| TC-032 | 專長守則（錯誤訊息不露內部） | 例外 | 同 TC-031 的各種失敗 | 逐一匯出 | 任何一則 `message` 都不含堆疊追蹤（Traceback）、平台資料夾的實際路徑、SQL 語句或資料庫錯誤字樣 | 自動 |
| TC-033 | 專長守則（密鑰不得出現） | 例外 | 呼叫者帶有測試用的 token（登入憑證）；開啟日誌擷取 | 分別做一次成功匯出與每一種失敗匯出 | 回應（不含 zip 位元組）與擷取到的日誌文字，都不含那個 token 或任何密碼字樣 | 自動 |
| TC-034 | 計畫·失敗先行測試 6（超限不留半個 zip） | 例外 | 同 TC-027、TC-028 | 甲匯出 | 超過大小或檔數的失敗也沒有 `zip`，磁碟上沒有留下任何檔 | 自動 |

## User Story 3 — 公開函式名單與出口範圍（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 計畫·範圍；失敗先行測試 8 | 功能 | 改完後的 `test_pipelines_store.py` | 執行該檔的「公開函式名單」那條測試 | 通過；名單恰為 `create_pipeline`、`export_pipeline`、`get_pipeline`、`get_validation`、`list_pipelines`、`render_pipeline`、`update_pipeline`、`validate_pipeline` 八個，測試標題與數字改成「八個」 | 自動：`platform/tests/test_pipelines_store.py` |
| TC-041 | 計畫·失敗先行測試 8；專長守則（對等性） | 功能 | 同上 | 檢查 `abf_platform.actions` | `hasattr(actions, "export_pipeline")` 仍為 False（它不是 `actions` 套件的公開名稱），其餘七個名稱也仍然沒有 | 自動：`platform/tests/test_pipelines_store.py` |
| TC-042 | 計畫·範圍（不進 parity 四張表）；專長守則（對等性 TC） | 功能 | 沒有改動 `test_web_parity.py`、`mcp_server.py`、`web.py` | 執行 `platform/tests/test_web_parity.py` | 通過；使用者看得到的動作清單與動作層函式清單仍一一對應，兩邊都沒有 `export_pipeline` | 自動：`platform/tests/test_web_parity.py` |
| TC-043 | 計畫·範圍（`test_pipelines_store.py` 只改名單那條） | 功能 | 實作完成 | 比對 `test_pipelines_store.py` 與 base 的差異 | 只有「七個公開函式」那條測試被改（名單加 `export_pipeline`、標題與數字改成八個）；沒有其他斷言被刪、放寬或跳過 | 手動：驗收者以 `git diff` 核對（`docs/TESTING.md` 無對應步驟） |
| TC-044 | 計畫·完成標準 | 功能 | 實作完成 | 執行 `git diff --stat <base>...HEAD` | 只含三個檔：`platform/abf_platform/actions/pipelines.py`、`platform/tests/test_pipelines_store.py`、新檔 `platform/tests/test_pipeline_export.py`（外加計畫與 ledger 本身） | 手動：驗收者以 `git diff --stat` 核對（`docs/TESTING.md` 無對應步驟） |
| TC-045 | 計畫·失敗先行測試前言；完成標準 | 功能 | 實作完成 | 讀 ledger | ledger 有「改程式前新測試為紅」的輸出，以及 zip 內檔案清單 | 手動：驗收者讀 ledger（`docs/TESTING.md` 無對應步驟） |
| TC-050 | 計畫·不做 1（不加 MCP 工具）；017e | 不在範圍 | 實作完成 | 在 `mcp_server.py` 與 `chat_tools.py` 內找 `export_pipeline` | 找不到；沒有新的 MCP 工具或聊天指令；這兩個檔相對 base 沒有改動 | 自動（測試檔內讀這兩個檔的文字，並由驗收者 `git diff` 再核對） |
| TC-051 | 計畫·不做 1（不加網頁路由、不加下載端點） | 不在範圍 | 實作完成 | 在 `web.py`、`web_board.py` 內找 `export_pipeline` | 找不到；沒有新的網頁路由或下載端點；這兩個檔相對 base 沒有改動 | 自動（同上） |
| TC-052 | 計畫·不做 2；裁示 16（不做分享連結、不做公開庫） | 不在範圍 | 甲匯出成功一次 | 檢查回應的欄位與資料表 | 回應沒有 `shared_token` 或任何分享連結欄位；沒有新增資料表；匯出結果只以位元組交給呼叫端 | 自動 |
| TC-053 | 計畫·不做 3；裁示 9（不花 SU） | 不在範圍 | 在測試中讓 `subprocess` 與 `os.system` 一被呼叫就失敗 | 甲匯出 | 仍然成功，也就是 `export_pipeline` 本身不啟動 `nextflow` 或任何外部程式 | 自動 |
| TC-054 | 計畫·範圍「不准碰」清單 | 不在範圍 | 實作完成 | 檢查 `actions/__init__.py`、`store.py`、`docs/PLATFORM.md`、`mcp_server.py`、`web.py`、`web_board.py`、`chat_tools.py`、`test_web_parity.py` 相對 base 的差異 | 這些檔都沒有改動；`actions/__init__.py` 與 `store.py` 內沒有 `export_pipeline` | 自動（`actions/__init__.py`、`store.py` 的文字檢查）＋驗收者 `git diff` 核對其餘 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 擁有者規則（使用者只能看到自己的紀錄；他人的當作找不到） | 例外 | 甲有一個有兩版的 pipeline | 乙匯出甲的 pipeline，指定 `version=1`、指定 `version=2`、不指定版本；再對一個不存在的編號做同樣三次 | 六次回應都是同樣措辭的「找不到」，沒有任何一次露出甲有哪些版本或版本數 | 自動 |
| TC-061 | 確認管道（沒有人工確認不得寫入）；裁示 9；資料庫無 migration | 功能 | 記下平台資料庫所有資料表的資料列數（含工作、待確認請求、驗證結果） | 甲成功匯出一次，再失敗匯出一次 | 兩次之後所有資料表的資料列數都與之前相同；匯出沒有寫入任何東西，所以不需要確認 | 自動 |
