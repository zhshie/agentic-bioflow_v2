# 測試案例：確認頁先用白話說（web-confirm-plain）

<!--
Written by the verifier (CONTRACT mode) from the plan only: there is no spec.md for this task. The maintainer's
words are in the plan's first line ("好的按照你的建議"): the page /c/<id> opens with a short plain summary and the
full technical content stays on the page, folded. Every row below comes from a line of plan.md (C1-C5, 不在範圍,
Tests first). Nothing was added that the plan does not state.
-->

**規格**：`specs/web-confirm-plain/plan.md`（本件沒有 spec.md，計畫即依據）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、過期、作廢、不該按的人去按時，頁面怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒變。

名詞：「白話區塊」＝頁面上方那一小塊「這次要決定什麼」的清單（種類、名稱、管線…）。「完整內容」＝今天 `<pre>` 裡整段會被送出的文字。「折疊」＝用 `<details>` 收起來，點開才看到，不用任何程式。

## User Story 1 — 待確認頁一開頭就用白話說這次要決定什麼（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | C1；Tests first 第 1 條（launch） | 功能 | 本人登入；有一筆「送出新分析」待確認申請，內容是 nf-core/ampliseq、環境 lab-a、一份有樣本的 samplesheet | 本人用瀏覽器打開 `/c/<id>`（不帶 lang） | 在「送出」按鈕之前有白話區塊（定義清單），用中文寫出：種類＝送出新分析；run 名稱；管線 `nf-core/ampliseq` 與它的版本；環境 `lab-a`；樣本數＝samplesheet 的資料列數（表頭不算）。每個值都與下方完整內容裡的同一個值一致 | 自動 |
| TC-002 | C1；Tests first 第 1 條（relaunch） | 功能 | 本人有一個失敗的 run；對它要求「重跑」，產生待確認申請 | 本人打開該申請的 `/c/<id>` | 白話區塊寫出：種類＝重跑；**新的** run 名稱（不是舊的）；管線與版本；環境；樣本數；新資料夾（與完整內容的「專屬資料夾」一致） | 自動 |
| TC-003 | C1（resume） | 功能 | 本人有一個失敗的 run；對它要求「續跑」，產生待確認申請 | 本人打開該申請的 `/c/<id>` | 白話區塊寫出：種類＝續跑；run 名稱；管線與版本；環境；樣本數；每個值與完整內容一致 | 自動 |
| TC-004 | C1；Tests first 第 1 條（cancel） | 功能 | 本人有一個已送出的 run；對它要求「取消」，產生待確認申請 | 本人打開該申請的 `/c/<id>` | 白話區塊寫出：種類＝取消；run 名稱（與完整內容一致）。取消申請裡沒有管線、版本、環境、樣本數，所以這四項**不出現** | 自動 |
| TC-005 | C1（「不知道的欄位直接省略，不顯示 `-`」） | 例外 | 同 TC-004 的取消申請，以及 TC-001 的送出申請 | 打開兩個申請的頁面，檢查白話區塊 | 白話區塊裡沒有任何值是 `-`、空白或「未知／N/A」之類的占位字；少了的欄位整行不存在（標籤也不在） | 自動 |
| TC-006 | C1（「在送出按鈕上方」） | 功能 | 同 TC-001 | 檢查頁面 HTML 順序 | 白話區塊出現在 `<button>送出</button>` 之前 | 自動 |
| TC-007 | C1（維護者的意思：「確認頁先用白話說」） | 功能 | 用真瀏覽器、真的待確認申請 | 維護者自己打開確認頁，不往下捲、不點任何東西 | 第一眼看到的是白話區塊：看得出這是什麼種類的請求、叫什麼名字、哪個管線與版本、跑在哪、幾個樣本；沒有 samplesheet 內容、設定檔、指令碼這類技術文字。維護者覺得「這就是我要的」 | 手動：`docs/TESTING.md`（待加入一步） |
| TC-008 | C1（「放 WEB_ONLY、頁面不自己解析、web.py 不 import confirm」） | 功能 | 實作完成 | 跑 `platform/tests/test_web_parity.py` 並閱讀 `platform/abf_platform/web.py` | 白話區塊的資料來自動作層的一個小函式（或既有的結構化欄位），該函式名稱列在 `test_web_parity.py` 的 `WEB_ONLY`，測試通過；`web.py` 沒有 `import confirm`（`FORBIDDEN_IMPORTS` 不變），也沒有在頁面程式裡用正規表示式之類去拆解摘要文字 | 自動 |

## User Story 2 — 完整內容還在同一頁，但折疊起來，一個字都沒少（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-009 | C2；Tests first 第 2 條（launch） | 功能 | 同 TC-001 | 取頁面中 `<details>` 裡的 `<pre>`，還原 HTML 跳脫後與該申請存的摘要文字比對 | 兩者逐字相同（包含換行與 samplesheet、params、head.sh 全部內容），沒有少任何資訊 | 自動 |
| TC-010 | C2（cancel） | 功能 | 同 TC-004 | 同 TC-009 | `<details>` 裡的 `<pre>` 與取消申請的摘要逐字相同 | 自動 |
| TC-011 | C2（relaunch） | 功能 | 同 TC-002 | 同 TC-009 | `<details>` 裡的 `<pre>` 與重跑申請的摘要逐字相同 | 自動 |
| TC-012 | C2（resume） | 功能 | 同 TC-003 | 同 TC-009 | `<details>` 裡的 `<pre>` 與續跑申請的摘要逐字相同 | 自動 |
| TC-013 | C2（「折疊」；原則 I.2 完整內容在按送出之前就在頁面上） | 功能 | 同 TC-001 | 檢查 `<details>` 標籤與整頁文字 | `<details>` 沒有 `open` 屬性（預設收起）；完整內容只出現在 `<details>` 裡面，白話區塊與頁面其他地方沒有它的副本；且完整內容就在這一次回應裡，不需要再發任何請求或點到別頁才看得到 | 自動 |
| TC-014 | C2（摘要標題） | 功能 | 同 TC-001，不帶 lang | 讀 `<details>` 裡的 `<summary>` | 文字是「完整內容（技術細節）」 | 自動 |

## User Story 3 — 手機上長路徑不用左右捲（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | C3；Tests first 第 4 條 | 功能 | 實作完成 | 讀頁面唯一的樣式表內 `pre` 的規則 | 該規則同時含 `white-space: pre-wrap`（壓縮寫法 `white-space:pre-wrap`）與 `overflow-wrap: anywhere`（`overflow-wrap:anywhere`） | 自動 |
| TC-016 | C3（「手機 390 px 看得到完整路徑、`<pre>` 內外都沒有橫向捲動」） | 功能 | 一筆資料夾路徑很長的待確認申請；瀏覽器視窗寬 390 px（或手機） | 打開確認頁，展開「完整內容（技術細節）」，也看白話區塊 | 長路徑整條都看得到（換行顯示）；整頁、白話區塊、完整內容區塊都沒有左右捲軸 | 手動：`docs/TESTING.md`（待加入一步） |

## User Story 4 — 送出之後的頁面也是白話在前、完整內容折疊（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | C4 | 功能 | 本人按過「送出」，申請已是 confirmed、有工作編號 | 本人重新打開 `/c/<id>` | 頁面仍說「已送出。工作編號 …」；並有與按之前相同的白話區塊（值一致） | 自動 |
| TC-018 | C4 | 功能 | 同 TC-017 | 檢查同一頁 | 完整內容在 `<details>`（預設收起）裡，與摘要逐字相同；沒有送出按鈕 | 自動 |
| TC-019 | C4（過期頁不變） | 例外 | 申請超過 10 分鐘未按 | 打開 `/c/<id>` | 和改動前一樣：「這個申請已逾時（10 分鐘）。請回到 AI 重新送出。」；沒有白話區塊、沒有 `<details>`、沒有按鈕；狀態碼不變 | 自動 |
| TC-020 | C4（作廢頁不變） | 例外 | 申請已作廢（例如被拒或佇列拒收） | 打開 `/c/<id>` | 和改動前一樣：「這個申請已作廢：<原因>。請回到 AI 重新送出。」，狀態碼 409；沒有白話區塊、沒有 `<details>`、沒有按鈕 | 自動 |

## User Story 5 — 英文版、零 JS、一張樣式表（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | C5；Tests first 第 5 條 | 功能 | 同 TC-001 | 打開 `/c/<id>?lang=en` | 白話區塊的標籤是英文，且不含中文標籤字（管線、版本、環境、樣本數、run 名稱…）；仍有值（如 `nf-core/ampliseq`、`lab-a`） | 自動 |
| TC-022 | C5 | 功能 | 同 TC-001 | 打開 `/c/<id>?lang=en`，讀 `<summary>` | 文字是「Full content (technical)」 | 自動 |
| TC-023 | C5 + 「送出內容不變」 | 功能 | 同 TC-001 | 打開 `?lang=en`，取 `<details>` 裡的 `<pre>` | 仍與摘要逐字相同（不翻譯、不增減），與中文版的 `<pre>` 完全一樣 | 自動 |
| TC-024 | C5（零 JS、沒有 inline style） | 功能 | 待確認頁與已送出頁，各用中文與 `?lang=en` | 檢查四份 HTML | 全部沒有 `<script`、沒有任何 `on…=` 事件屬性、沒有 `style=` 屬性 | 自動 |
| TC-025 | C5（一張樣式表、CSP 雜湊更新） | 功能 | 同 TC-024 | 比對回應標頭 `Content-Security-Policy` 的 `style-src` 與頁面 | 頁面只有一個 `<style>` 元素；標頭 `style-src` 的 `sha256-…` 等於該元素文字的 SHA-256（改了樣式表之後雜湊跟著更新） | 自動 |
| TC-026 | C5（CSP 不放寬） | 功能 | 同 TC-024 | 讀 CSP 標頭 | 仍是 `default-src 'none'`，沒有 `script-src`、沒有 `'unsafe-inline'`，其餘指令（form-action、frame-ancestors、base-uri）與改動前相同 | 自動 |

## User Story 6 — 不在範圍：送出的內容與流程完全不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-027 | 不在範圍「approve flow」；Tests first 第 1 條（表單仍帶 CSRF 送出） | 不在範圍 | 同 TC-001 | 檢查表單；用本人 session 帶正確 csrf 送出 | 表單仍是 `POST /c/<id>`、有隱藏欄位 `csrf`、按鈕寫「送出」；按下後恰好排進一個工作，頁面說工作編號 | 自動 |
| TC-028 | 不在範圍「CSRF」 | 不在範圍 | 同 TC-001 | 送出時 csrf 缺漏或錯誤 | 回 403、什麼都沒送出、沒有排工作；本人隨後仍可正確送出 | 自動 |
| TC-029 | 不在範圍「owner rules」（新的白話區塊不能多洩漏資料） | 不在範圍 | ann 的待確認申請；bob 已登入；另有未登入者 | bob 打開 ann 的 `/c/<id>`；未登入者也打開 | bob 得到 403「不是你的申請」，頁面上沒有 ann 的 run 名稱、管線、環境、樣本數，也沒有白話區塊；未登入者只看到登入表單，沒有白話區塊或按鈕 | 自動 |
| TC-030 | 不在範圍「changing what is sent」 | 不在範圍 | 同一組固定輸入，分別在 `main` 與本分支建立申請 | 比較兩邊申請的摘要文字與內容雜湊（sha256），並按送出 | 摘要與雜湊逐字相同；排進佇列的工作內容與 `main` 相同 | 自動 |
| TC-031 | 不在範圍「other pages」 | 不在範圍 | 看板、登入、啟動表單、設定、授權同意頁 | 比較本分支與 `main` 的 HTML 主體（共用樣式表本身改變不算） | 這些頁的內容與結構沒有變；`test_web_board.py`、`test_web_login.py`、`test_web_actions.py`、`test_web_running.py` 不改就通過 | 自動 |
| TC-032 | 不在範圍（沒有新路由、沒有新的請求種類） | 不在範圍 | 實作完成 | 跑「網頁只有這些路由」的測試 | `test_tcg04_g05_g06_*` 不改就通過：沒有新增路由；`/c/` 上沒有為「刪除保留內容」新增頁面（該動作仍只走終端機或 MCP 表單） | 自動 |
| TC-033 | Tests first 第 6 條（既有確認頁測試不動，只有 ledger 列出的字串替換） | 不在範圍 | 實作完成 | 比對 `platform/tests/` 對 `main` 的差異，對照 `specs/web-confirm-plain/ledger.md` | 既有測試的斷言沒有被刪、放寬或跳過；凡是改過的斷言都在 ledger 逐條寫明「舊的、新的、為什麼」，且僅限字串替換；`spec`／`test-case*.md` 沒被改 | 手動：`docs/TESTING.md`（待加入一步） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | 原則 I.2（未確認的送出一律被擋；人按了才跑）與 Safety Net「寫入工具必須有人確認」 | 例外 | 一筆待確認申請，沒有人按 | 不經本人按鈕，直接走網頁路徑或 MCP 想讓它送出 | 仍被拒、沒有工作；`test_tch09_b_c_*`（`test_confirm_page.py`）不改就通過 | 自動 |
| TC-035 | Safety Net「權杖、待確認申請或模型自己的回答都不算人的 yes」 | 例外 | 只有權杖（Bearer）沒有網頁登入的 AI | 對 `/c/<id>` 送出 | 仍按不了（`test_tcd17_*` 不改就通過）；新增的白話區塊沒有因此讓它多看到內容 | 自動 |

<!--
Rules for the writer:
- Every item of the plan (C1-C5, 不在範圍, Tests first) maps to at least one TC. Every "out of scope" item has a 不在範圍 TC.
- A TC tests one thing.
- IDs are never renumbered after approval.
-->
