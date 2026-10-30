---
id: results-files
title: 結果頁可以點進資料夾、下載單一結果檔（含 MultiQC 報告與總結報告）
tier: B
kinds: ui, backend
lane: L37-results-files
branch: feat/results-files
base: v3
source: 維護者 10-29「確定我能從點選"+新分析"一直到分析完成都能在網頁上操作了嗎?」；developer-agent 10-29 實測 web-test-1 跑完後，結果頁「輸出」只列出 results 第一層，資料夾點不進去，「報告／MultiQC 報告／指標／全部下載」皆「之後開放」；他 10-29 同意「下一件先做看結果和下載」
---

# results-files

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/results-files/plan.md`。**只處理本任務**。

## 目標
同事跑完一次分析，要在網頁上拿到結果，不必登入叢集：在「結果」階段的「輸出」分頁點進任何子資料夾、下載單一檔案（上限 25 MB），並從摘要卡直接下載 MultiQC 報告與總結報告。位元組照 `/launch/diagram` 的既有模式走：平台排一個工作給**登入者自己的站台代理**，代理讀檔回傳，平台把答案交給瀏覽器；平台不對外連線、不開檔讀站台的東西。

## 維護者原話（verifier 出題用）
1. 「確定我能從點選"+新分析"一直到分析完成都能在網頁上操作了嗎?」（10-29）→ 跑完後在網頁上拿得到結果檔。
2. DESIGN.md 畫面 8：「**Results stage**: summary cards; tabs Report … / Outputs / Reports (MultiQC embedded, JS) / Run info / Tasks / Logs / Metrics; Download all.」→ 本任務做 Outputs 的瀏覽與單檔下載、MultiQC 與總結報告的下載；MultiQC 內嵌、Report 編輯、Metrics、Download all 仍是「之後開放」。
3. 「跟Seqera platform一樣的模式，不要自己定義」（10-23 常設）→ Seqera 的 Reports／Outputs 也是逐檔下載。

## 範圍：檔案
- `platform/abf_platform/jobs.py`：新工作種類 `read_run_file`（種類表、期限 60 s、排隊函式 `enqueue_read_run_file`、`clean_result` 分支）。
- `platform/abf_platform/store.py`＋遷移：jobs 表 CHECK 清單加入 `read_run_file`（照 `put_upload`／byte-channel-a 的遷移寫法；舊資料庫可升級、不掉資料）。
- `platform/abf_platform/actions/__init__.py`：只讀 `run_file(...)`（排隊或讀答案，照 `pipeline_files` 的「不等待」模式）；`list_site_files` 的既有呼叫處若需帶子路徑則加可選參數。
- `platform/abf_station/handlers.py`：新種類的處理（作法 2）；`JOB_KINDS` 加入。只准新增函式，不改 preflight 與 listing 既有行為（L32 同時在改 preflight，見裁決 4）。
- `platform/abf_platform/web.py`：`GET /run/file?run=<id>&path=<相對路徑>`（作法 3）；輸出分頁的 `path` 參數。
- `platform/abf_platform/web_board.py`：輸出分頁的資料夾連結、檔案下載連結、麵包屑；摘要卡「MultiQC 報告」「報告」兩格改成下載連結（有檔時）；STRINGS。
- 新測試：`platform/tests/test_results_files.py`、`platform/tests/test_station_read_run_file.py`。
- 被釘住的既有測試（只加不刪、ledger 逐條列）：jobs 種類數量／清單類（`git grep -n "Nine kinds\|KINDS\|JOB_KINDS" platform/tests`）、路由清單類（`test_aws_ce.py`、`test_aws_launch.py`、`test_gcb_ce.py`、`test_gcb_launch.py`、`test_web_parity.py`）、`test_web_running.py`／`test_web_board.py` 中釘「之後開放」的斷言。
- `docs/PLATFORM.md`（新增「下載結果檔」一節，說明位元組怎麼走與上限）、`docs/TESTING.md`（手動：真站台跑完的 run，點進 multiqc、下載 multiqc_report.html，在瀏覽器打開）。

## 作法
1. **工作 `read_run_file`**：參數只有環境名、run 名稱、`path`（相對於該 run 的 `results/`）。平台排隊前判斷：run 是登入者自己的且有送出紀錄（取 `launches.run_folder` 與 `ce`）；`path` 是相對路徑、不含 `..`、不以 `/` 開頭、每段不以 `.` 開頭、總長 ≤ 512；環境是 slurm 或平台主機類型（雲端類型若 results 不在本機則代理回「此環境的結果檔不在站台主機上」）。工作裡帶的是 `run_folder + "/results/" + path` 由**代理端**組，平台只帶三個值。
2. **代理**：重新判斷同樣的規則；完整路徑必須落在環境的 `readRoots` 之內且在 `<run_folder>/results/` 之下（解開符號連結後再判斷）；必須是一般檔案；大小 ≤ 25 MB（26,214,400 位元組），超過＝回 `too_large` 與實際大小，不讀內容。讀取用一次 ssh 呼叫、固定指令（`stat` 取大小、再 `base64` 輸出內容；或沿用既有讀 log 的方式），回傳 `{"status": "ok", "name", "size", "b64"}`；平台收到後驗 base64 解出的長度等於 size。
3. **下載路由** `GET /run/file?run=<id>&path=<p>`：登入；run 必須是自己的（他人與不存在同為 404）；呼叫 `actions.run_file`：
   - 答案已就緒＝回位元組，`Content-Disposition: attachment; filename="<檔名>"`（一律下載、不在本站內開啟——HTML 報告含腳本，不可在平台的網域執行）、`Content-Type: application/octet-stream`、`X-Content-Type-Options: nosniff`、`Cache-Control: private, no-store`。
   - 還在讀＝回一頁「◌ 正在向站台取得檔案，頁面每 15 秒自動更新。」（沿用 /launch 的 15 秒寫法），讀完自動開始下載（下一次 GET 拿到位元組）。
   - `too_large`＝一頁「✕ 檔案大小 <N MB>，超過網頁下載上限 25 MB。請於站台取得：<完整路徑>」＋回輸出分頁的連結。
   - 代理離線／其他錯誤＝一頁說明原因＋「重試」連結。
   - 同一檔案 10 分鐘內重複下載不重排工作（沿用 `latest_*` 的快取讀法）；答案內容保留在 jobs 表，照既有 7 天清理。
4. **輸出分頁**：`?run=<id>&stage=results&tab=outputs&path=<子資料夾>`。資料夾名稱是連結（進入子資料夾，用既有 `list_site_files` 列該路徑）；上方麵包屑「results / multiqc / …」每段可點；檔案列多一欄「下載」：≤ 25 MB 給連結，> 25 MB 顯示「超過 25 MB」。`path` 規則同作法 1；不合法＝回 results 第一層並在上方顯示「✕ 路徑不正確」。
5. **摘要卡**：「MultiQC 報告」＝若輸出第一層有 `multiqc/`，連到 `/run/file?…&path=multiqc/multiqc_report.html`；「報告」＝若有 `summary_report/`，連到 `summary_report/summary_report.html`；檔案不存在時由下載頁回「站台沒有這個檔案」。沒有那個資料夾＝維持「之後開放」字樣改為「此管線沒有產生」。「指標」「全部下載」不變。
6. 只用現有 class 與 DESIGN.md token；不改 STYLE（D13 釘 sha256）；CSP 不變（下載是 attachment，不需 img-src 或 frame）。中英字串皆正式書面語。

## 六項必填檢核（ui 計畫固定段）
1. 確認頁規則：讀檔是唯讀，不經確認頁（與 listing、diagram 相同）。
2. 失敗狀態：路徑不合法、他人 run、run 沒有送出紀錄、檔案不存在、是資料夾、過大、代理離線、站台連不上、雲端環境不支援——各自的句子與所在頁（作法 3、4）。
3. 提示句位置：下載狀態頁的句子在頁首、連結在句子下方；輸出分頁的路徑錯誤句在表格上方。
4. 要改的舊測試：見「範圍：檔案」的清單與 grep；只加不刪。
5. 手機寬度：輸出表格與下載狀態頁 390 px 無橫向捲動（長檔名可換行）。
6. 空狀態：子資料夾是空的＝「此資料夾沒有檔案。」；run 沒有 results＝沿用既有輸出分頁的空狀態句。

## 失敗先行測試
- 站台：合法路徑回 base64 且長度相符；`..`、絕對路徑、隱藏段、符號連結指到 results 外、readRoots 外＝拒絕；資料夾＝拒絕；> 25 MB＝`too_large` 且沒有讀內容（假 site 的呼叫紀錄裡沒有讀內容的指令）；指令字串只含代理自己組出的路徑並經 quote。
- 平台：他人 run＝404 且不排工作；排隊參數只有三個值；遷移：用 base 版建的資料庫升級後可排 `read_run_file`、舊工作列不變；`clean_result` 拒收長度不符的答案。
- 網頁：資料夾連結與麵包屑；下載中頁含 15 秒更新；就緒回 attachment＋nosniff＋no-store；過大頁含站台完整路徑；摘要卡在有 `multiqc/` 時是連結、沒有時是「此管線沒有產生」；`path` 不合法回第一層並顯示錯誤；CSP 與其他頁面逐字不變。

## 完成標準（done when）
上列全綠；整套 `tests/run_all.sh --timeout 900` 綠（背景跑＋等待）；被改的既有斷言在 ledger 逐條列；docs 兩處更新。

## 環境事實
- 10-29 實測 run `web-test-1`（使用者 abf-test、環境 nano4-test、代理 desktop-test）：`<run_folder>`＝`/work/u9613010/runs/runs/web-test-1`，results 第一層 11 個資料夾＋`overall_summary.tsv`（1,292 位元組）；`multiqc/`、`summary_report/` 都有。輸出分頁現行由 `list_site_files` 工作讀（jobs 40、41）。
- 位元組先例：`GET /launch/diagram`（docs/PLATFORM.md :738）——代理回傳、平台交給瀏覽器、帶 nosniff 與限制型 CSP。
- 遷移先例：byte-channel-a 為 `put_upload` 加 CHECK 種類。
- 代理端讀檔先例：`read_task_log`（`abf_station/readlog.py`）。
- 摘要卡：`web_board._results_cards`（約 :597）。

## 不做
- MultiQC 內嵌、Report 編輯與存檔、Metrics、Download all（整包下載）、> 25 MB 的檔、雲端 bucket 上的結果下載、交付包。不改 STYLE 與 CSP；不新增 MCP 工具。

## 裁決
1. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`。
2. `platform/pyproject.toml` executor 不能改；需要就寫進報告退回。
3. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有慣例自訂預期值寫進 TC，不以「計畫未寫」退回；只有「照字面做不出來」或「違反憲法／ADR／安全」才算阻擋。test-case.md 全文必須放進回傳值，條數 ≤ 45。
4. 與 L32（settings-pick-installed，改 handlers.py 的 preflight）、L33／L34／L17（web.py、web_board.py 其他區段）並行：落地前 `git merge origin/v3`，衝突只保留雙方新增，不改對方的字。
5. worktree 用 Windows git 建，WSL 裡 `constitution_scope_test.sh` 紅＝環境問題，以 CI 為準，ledger 註明。
6. 25 MB 上限理由：MultiQC 報告通常數 MB；jobs 表以 base64 存放，過大會拖慢資料庫。上限寫成一個常數，之後可調。

7. `store.py` 的新函式放在 jobs 區段，不放在權杖區段（約 :950-1072，L36 agent-token-revoke-by-id 正在那裡加函式），讓兩邊分開合併。

## 專長守則（ui）

### executor

- 先讀專案根目錄的 `PRODUCT.md`（給誰用、要解決什麼）與 `DESIGN.md`（版面線框、tokens、每個畫面與狀態、維護者的原話例子）。讀不到就 BLOCKED，不自己發明設計。
- 只准用 `DESIGN.md` 定義的 tokens（色彩、字型、字級、間距、圓角）與版面。不新增任何視覺決策：不自創顏色、字型、間距數值，不順手「美化」。
- `DESIGN.md` 沒決定的事，一律寫進報告的「卡住的原因／要問的問題」，不猜。
- `DESIGN.md` 列出的每個畫面、每個狀態都必須做出來，包含空狀態、載入中、錯誤、失敗。少一個就不算完成。
- 遵守計畫寫明的前端限制（例如 CSP、禁用 inline style、不載外部資源、只在允許處使用 JS）。限制與設計衝突時停下來問，不自行取捨。
- 狀態絕不只靠顏色：一律「符號＋文字＋顏色」三者並用。
- 手機寬度可用（不橫向捲動、點擊目標夠大），鍵盤操作時焦點外框可見。
- 介面文字用使用者視角的白話，不露出內部術語、錯誤代碼或程式名詞；錯誤訊息說發生什麼事與下一步。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- `DESIGN.md` 的每個畫面、每個狀態都至少對應 1 個 TC（含空、載入、錯誤、失敗）。
- 維護者的原話例子逐字對應到 TC。
- 計畫列的前端限制各對應 TC（例如頁面不得含 inline style、不得請求外部網址、CSP 標頭存在）。
- 狀態表達 TC：每個狀態輸出的 HTML 同時含符號、文字，不得只靠 class 顏色。

**ACCEPTANCE（閱卷）必須檢查：**
- 把每個有改動的頁面渲染成 HTML 檔（用專案的 test client，或計畫指名的 fixture）。做不到就標 UNVERIFIED，並寫明需要什麼才能驗。
- 對渲染出的 HTML 跑 Impeccable 偵測器（唯讀）：`sh "G:/我的雲端硬碟/謝馬爾/.claude/skills/impeccable/scripts/impeccable" detect <file.html>`。
- **FAIL**：違反 `DESIGN.md` 的 tokens／畫面／狀態；違反計畫寫明的前端限制；狀態只靠顏色；缺少 DESIGN.md 列出的畫面或狀態。
- **「需要人看的事」**：偵測器的其他發現（對比、常見字型、AI 範本味等）與品味問題。這些不判 FAIL。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
- 注意：「看起來好不好」的最終判斷屬於維護者，靠 developer-agent 附在 PR 的截圖（B 級）決定，verifier 不替他下結論。

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
