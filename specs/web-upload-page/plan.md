---
id: web-upload-page
title: 網頁上傳資料頁（雲端運算環境）：瀏覽器把 FASTQ 與樣本表送進平台暫存，排入既有的上傳工作送進自己的雲端資料夾，全部傳完自動登記成資料集，送出頁第 4 步可直接選
tier: B
kinds: ui, backend
lane: L17-web-upload
base: v3
source: 維護者 10-28「加速進行，這禮拜做完」＋10-27 清單「網頁上傳資料的畫面（後端已經做好，缺畫面）」；ADR 0010 第 109-114 行（10-25 更正：按「上傳」即確認、平台主機可暫存、尺寸核對後刪暫存）；docs/OPERATIONS.md:226-232 第 6 點「Not built yet」；specs/byte-channel-a/plan.md:151,157（cloud-upload-wire）
---

# web-upload-page

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/web-upload-page/plan.md`。**只處理本任務**。
> 與 L8（settings-register-pipeline）同時跑：兩邊都會在 `web.py` 路由清單、`web_board.py` STRINGS 與幾個「路由清單釘死」測試各加幾項。本任務在這些檔只准**新增**行，不改既有行（例外見範圍）；合併衝突一律取兩邊聯集。

## 目標
同事不必打指令：在網頁選一個自己的雲端運算環境（Google Batch／AWS），填資料集名稱與版本，選 FASTQ（每檔 ≤2 GB）和樣本表（可不給，平台依檔名配對 R1/R2 自動產生草稿），按「上傳」。平台把檔案收到自己的暫存夾，排入既有的雲端上傳工作，頁面顯示每個檔的進度；全部傳完且尺寸核對無誤，自動登記成資料集，`/launch` 第 4 步就能選。

## 維護者原話（verifier 出題用）
1. 「加速進行，這禮拜做完"還沒做，要讓同事不問人就能自己用完的部分"」（10-28）
2. DESIGN.md 第 55 行「Upload data」一段（英文原文照抄進測試案例：每檔約 2 GB 上限，更大的檔走 AI／push.sh）
3. ADR 0010 10-25 更正（第 109-114 行）：「按上傳就是確認」，不再另開確認頁；平台主機暫存一份，雲端尺寸核對相符後刪除。
4. 「先把功能做起來吧，以後再改美觀」（10-23）

## 範圍：檔案
- `platform/abf_platform/web_upload.py`（**新檔**：上傳頁與進度頁的渲染、中英字串）
- `platform/abf_platform/uploads_web.py`（**新檔**：串流接收 multipart、寫入 `<uploads>/<user>/`、尺寸上限、暫存檔命名與清理）
- `platform/abf_platform/web.py`（只新增：`GET /upload`、`POST /upload`、`GET /upload/{batch}` 三條與註冊行；`MAX_BODY` 不准改，上傳路由用自己的上限）
- `platform/abf_platform/web_board.py`（只限：把灰色「上傳資料」按鈕改成連到 `/upload`；`/launch` 第 4 步無樣本表時的連結改指向 `/upload`；新增 STRINGS）
- `platform/abf_platform/actions/uploads.py`（**新檔**：批次上傳的動作邏輯，見裁決 13）
- `platform/abf_platform/actions/__init__.py`（只新增兩個轉呼叫 `actions/uploads.py` 的函式，見裁決 13）
- `platform/abf_platform/actions/datasets.py`（只新增一個不寫入的檢查函式 `check_samplesheet`，`register_dataset` 改成共用它但行為不變）
- `platform/abf_platform/jobs.py`（只准加讀取「某批上傳工作狀態」的小函式）
- `platform/pyproject.toml`（只限把已在 constraints.txt 釘住的 `python-multipart` 明列為直接依賴；不得新增其他套件）
- `platform/tests/test_web_upload.py`（新檔）
- 被逐字釘住、必須加項的既有測試（只加不刪，ledger 逐條列）：`test_dataset_cli.py:183`、`test_cleanup_offer.py:815`、`test_confirm_page.py:313`、`test_web_board.py:820`、`test_owner_binding.py:824`、`test_temp_password.py:290`、`test_web_parity.py:16`、灰色按鈕與第 4 步連結相關斷言
- `DESIGN.md`（只限裁決 9 的兩句）
- `docs/OPERATIONS.md`（第 6 點改寫）、`docs/PLATFORM.md`（:382「網頁入口尚未接上」改寫）、`docs/TESTING.md`（新增手動一節：真檔經 Tailscale Funnel 上傳 ≥100 MB 一次）

## 作法
1. **上傳頁 `GET /upload`**：只列 `status == available`、型別允許上傳（GOOGLE_BATCH／AWS，沿用 `jobs.py` 的判斷，不重寫）、屬於自己的環境。一個都沒有 → 一句話＋連到 `/settings`，不顯示表單。表單：運算環境、資料集名稱、版本（規則同 `register_dataset`：`^[A-Za-z0-9._-]{1,64}$`）、FASTQ 檔（`<input type=file multiple>`）、樣本表（選填）。不用 JS（拖放區留給之後）。說明一句：每檔上限 2 GB，更大的檔請改用指令（顯示 `check_web_upload` 給的指令）。國網／Slurm 環境不列，並在頁面說明「國網環境的資料目前請用指令上傳」。
2. **`POST /upload`**：`same_origin` → `user_of` → CSRF（purpose `upload`）。用 `request.stream()` 配 python-multipart 串流解析，邊收邊寫到 `<uploads>/<user>/.incoming-<batch>/`；任何一檔超過 2,000,000,000 位元組立刻中止、刪掉這批暫存、回 413 頁（帶指令）。檔名含 `/`、`\`、`..` 或控制字元一律拒收（不截斷）；重名拒收（見裁決 6）。收完後把檔案移到 `<uploads>/<user>/<名>`（`enqueue_put_upload` 要求的位置），每檔呼叫一次 `enqueue_put_upload`，303 到 `/upload/<batch>`。樣本表 ≤1 MiB（`SAMPLESHEET_LIMIT`），沒給就用 `draft_samplesheet`（`pair_fastq`）產生；配不成對 → 400 頁列出哪些檔配不到，並清掉這批暫存、不排工作。
3. **批次紀錄**：每批存 `{batch, owner, ce, name, version, files:[{name, job_id, dest}], samplesheet}`（存成 `<uploads>/<user>/.batches/<batch>.json`，見裁決 13）。批次只有本人看得到；他人的 batch ＝ 404。
4. **進度頁 `GET /upload/{batch}`**：每檔一列（檔名、大小、狀態：排隊中／傳送中／完成／失敗＋原因），15 秒自動重新整理（沿用既有 meta refresh，不加 JS）。全部完成 → 呼叫 `register_dataset(..., destination=<ce>)`，檔案路徑用工作回報的 `gs://`／`s3://` 位置，樣本表儲存格換成同一組位置；登記成功顯示「已登記，前往送出」連到 `/launch`。本批已登記（批次旗標）＝直接顯示已登記，不重複登記。有任一失敗 → 不登記，顯示失敗原因與「重新上傳」連結。
5. **網頁總看板**：灰色「上傳資料」按鈕變成真的連結；`/launch` 第 4 步無樣本表時連到 `/upload`。
6. 平台本身不開任何對外連線（憲法原則 2）：位元組只寫本機暫存夾，送雲端由既有站台代理工作完成。CSP 不變。

## 失敗先行測試
`test_web_upload.py`：無可用雲端環境＝無表單、有設定頁連結；國網環境不出現在選單；成功上傳兩個成對 FASTQ＝暫存檔在 `<uploads>/<user>/`、排了兩個工作、303 到進度頁；超過上限（測試用可調上限或假大小串流）＝413、暫存清空、沒排工作；檔名含 `../`＝400；缺 CSRF／跨來源＝403、沒寫檔；配不成對＝400 列出檔名；他人 batch＝404；工作全部 ok（測試直接改工作結果）→ 進度頁登記資料集、`list_datasets` 看得到、`/launch` 第 4 步出現它；有一個失敗＝不登記；重整兩次只登記一次；臨時密碼登入者被導到 `/welcome`。

## 完成標準（done when）
上列全綠；整套 `tests/run_all.sh --timeout 900` 綠；釘死測試只加項；ledger 列出批次紀錄存哪、改了哪些釘死斷言。

## 環境事實
- `enqueue_put_upload` 在 `jobs.py:241-262`：只接受雲端環境；暫存檔必須在 `<uploads_dir>/<owner>/<filename>`、1 位元組到 2 GB；工作結果 `{ok, bytes, path: dest, message}`；目的地 `gs://<workDir bucket>/uploads/<owner>/<name>`。
- 站台端 `abf_station/put_upload.py:144-204`：核對雲端尺寸後才刪暫存。
- `register_dataset` 在 `actions/datasets.py:278-374`；帶 `destination` 時路徑必須在該環境 bucket 的 `uploads/<user>/` 之下，且不驗證檔案真的存在——所以必須等工作全部成功才登記。
- Web 是 Starlette；`body_of`（web.py:242-248）切在 `MAX_BODY = 16384`，上傳路由不得走它。python-multipart 0.0.32 已在 `platform/constraints.txt:30`。
- 桌機部署的雲端環境 `gcb1` 是可用的 Google Batch 環境（測試用 fixture，不連真雲端）。

## 不做
- 國網／Slurm 的網頁上傳（站台沒有對應工作，另案）。
- 拖放、斷點續傳、2 GB 以上的檔。
- AI／MCP 上傳工具。
- 不改 `register_dataset`、`enqueue_put_upload`、站台代理的行為。

## 裁決
1. 不另開確認頁：ADR 0010 10-25 更正已定「按上傳就是確認」。
2. 與 L8 同時跑造成的合併衝突（路由清單、STRINGS、釘死測試清單）一律取兩邊聯集，不算越界。

3. （10-28 合約退回後）**名稱＋版本已存在就在上傳時拒收**：`POST /upload` 先查 `get_dataset(owner, name, version)`，存在＝400「此名稱與版本已登記，請換一個版本。」（en: "This name and version are already registered. Use another version."），不寫檔、不排工作。批次紀錄自帶 `registered` 旗標；進度頁只依本批的旗標顯示「已登記」，不依名稱判斷。
4. **排工作前先把能驗的都驗完**：樣本表欄位（`sample`、`fastq_1`）、每個路徑儲存格都對得上本批檔名、不含網址或像憑證的值——照 `register_dataset` 的同一套規則（可抽出共用的檢查函式，`register_dataset` 行為不變）。驗不過＝400 列出原因，清暫存、不排工作。全部上傳成功後 `register_dataset` 若仍回 `ok:false`：進度頁顯示它回的原因，列出已在雲端的檔案位置（`gs://…`），說明「檔案仍在你的雲端資料夾，可換一個版本重新上傳」，不自動刪雲端檔。
5. **排工作全有或全無（盡力）**：排任何一個工作前，先對每個檔做 `enqueue_put_upload` 會做的前置檢查（環境可用、型別、大小 1 位元組～2 GB）。若仍在排到一半時被拒：已排的工作照傳，批次標為失敗，未排的暫存檔刪除，進度頁標出哪個檔被拒及原因，不登記。
6. 檔名含 `/` 或 `\` 一律拒收（不做 basename 截斷）；同批重名與 uploads 夾已有同名檔都拒收。
7. 進度頁狀態對應：queued＝排隊中、claimed＝傳送中、done 且 ok＝完成、done 且非 ok 或 expired＝失敗（附工作回的 message）。
8. 任何在排工作之前的拒收（大小、檔名、樣本表過大、配不成對、名稱已存在、樣本表驗不過）都清掉這批暫存。
9. **範圍確認**：DESIGN.md「Upload data」的拖放區、依 `schema_input.json` 建樣本表、「已上傳資料」表格本次不做；`DESIGN.md` 加入範圍，只在該段末加一行「10-28 第一刀：表單上傳＋進度頁；拖放、依 schema 建表、已上傳資料表格留待後續」。「平台不留副本」依 ADR 0010 10-25 更正改為「暫存於平台主機、雲端尺寸核對後刪除」，同段改一句。
10. 進度頁 GET 在「本人、本批全部成功、尚未登記」時登記資料集，是刻意選擇（沒有另一個按鈕要按）。
11. 「平台不開對外連線」的出處改為 `docs/PLATFORM.md`（:323、:382）與 `actions/datasets.py` 模組說明，不是憲法原則 2。
12. `docs/TESTING.md` 新節同時寫：≥100 MB 真檔經 Tailscale Funnel 上傳一次、390 px 寬無橫捲、鍵盤 Tab 焦點外框、中英各看一次。

13. （10-28 第三次合約退回後）**分層與釘死測試逐條處理**：
   - 網頁只呼叫 `actions/__init__.py` 新增的 `start_upload_batch(...)` 與 `upload_batch_status(...)`（再加 `register_upload_batch` 若需要），三者只轉呼叫新檔 `actions/uploads.py`。`web.py`、`web_board.py`、`web_upload.py`、`uploads_web.py`、`actions/__init__.py` 都不得出現 `register_dataset`／`draft_samplesheet`／`check_web_upload`／`pair_fastq`／`actions.datasets`／`get_dataset` 新字樣——`test_datasets.py:470` 附近的 `test_tc064` 因此**不改**（若 executor 發現仍須改，停下回報，不得自改）。`actions/uploads.py` 才可呼叫 datasets 與 `jobs.enqueue_put_upload`。
   - `test_aws_upload.py:727`（只有 jobs.py 呼叫 `enqueue_put_upload`）：期望清單改為 `["actions/uploads.py", "jobs.py"]`，其餘不動。
   - `test_aws_upload.py:751`（PLATFORM.md 含「網頁入口尚未接上」）：改成斷言 PLATFORM.md 該處含新句「網頁上傳頁（/upload）會把檔案暫存於平台主機後排入此工作」，且不再含舊句。
   - `test_cloud_upload_docs.py:42`（OPERATIONS.md 第 6 點含 "Not built yet"…）：改成斷言第 6 點含 "The web page /upload sends files up to 2 GB into the bucket" 且不再含 "Not built yet"。
   - `test_aws_upload.py:665` 與 `test_datasets.py:441`（datasets.py 函式清單恰六個）：清單加上 `check_samplesheet`，成為七個。
   - `test_aws_upload.py:660`（資料表雜湊與 `_migrate` 清單）：**不改**——批次紀錄不進資料庫，存成 `<uploads>/<user>/.batches/<batch>.json`（0600，寫入用暫存檔＋rename），所以不需要 migration。
   - `test_web_board.py:316`（`test_tcs21_s22_left_grey_and_settings`）：「↑ 上傳資料」改為連到 `/upload` 的連結（中英皆然），其餘斷言（設定連結等）不動。
14. 進度頁每檔狀態的符號＋文字：`○ 排隊中`／"○ Queued"、`◐ 傳送中`／"◐ Sending"、`✓ 完成`／"✓ Done"、`✕ 失敗`／"✕ Failed"；不只靠顏色。維護者看截圖時可改。
15. 空欄位：沒選任何 FASTQ＝400「請選擇至少一個 FASTQ 檔。」／"Choose at least one FASTQ file."；名稱或版本空白＝400 該欄「此欄為必填。」／"This field is required."；皆不寫檔、不排工作。
16. DESIGN.md 用字禁用清單只檢查本任務頁面自己寫的句子；引用 `jobs.py`／站台回傳的訊息原文照登。

17. （10-28 第四次合約退回後）**「/upload 必須不存在」的既有斷言**：`test_confirm_page.py:315`、`test_web_board.py:1184`（`test_tn04_other_paths_stay_missing`）把 `/upload` 從「必須 404」清單拿掉，改成斷言它存在（未登入時與 `/launch` 同樣轉到登入）；`test_web_actions.py:505-506`（`test_tc051_tc056_nothing_out_of_scope_exists`）正規表達式移除 `upload|`，另加一行斷言含 upload 的路由恰為 `/upload` 與 `/upload/{batch}`。理由：路由現在依維護者 10-28 要求存在；其餘清單與字詞不動。ledger 逐條列。
18. **重新上傳**：uploads 夾已有同名檔時，若該檔屬於本人一個「已失敗」的批次，允許覆蓋（先刪舊暫存、舊批次紀錄標記 superseded）；屬於進行中或已登記的批次＝拒收「此檔名正在上傳或已使用，請改檔名。」／"This file name is in use by another upload; rename the file."
19. 未登入者 `POST /upload`＝與 `POST /launch` 未登入時的反應相同。
20. 國網說明句只在使用者有 Slurm 類環境時顯示。
21. 大檔指令：表單下方對每個列出的雲端環境各顯示一行該環境的大檔指令（內容同 `cloud_store.big_file_command`，以 `<檔名>` 佔位）。
22. **合約規則**：計畫範圍內未明寫的細節由 verifier 依專長守則與既有畫面慣例自行決定預期值並寫進 TC，不再以「計畫未寫」退回；只有「照計畫字面無法實作」或「與憲法／ADR 衝突」才算阻擋。

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
