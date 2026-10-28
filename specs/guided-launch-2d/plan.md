---
id: guided-launch-2d
title: 引導式送出重排：分析名稱第一、只列已設定好的運算環境、管線與版本一處決定、流程圖直接顯示、拿掉前置檢查
tier: B
kinds: ui
lane: L7-web-redesign
base: v3
after: guided-launch-2c
source: 維護者 10-28 看 PR #240（afd8b9e）四張截圖後的回覆與三題選擇（本 session）
---

# guided-launch-2d

> PR #240（分支 `feat/guided-launch-2`，head afd8b9e）的修正輪。同一個分支、同一支 PR，在 afd8b9e 上繼續 commit，不另開分支或 PR。worktree：`C:/Users/marvi/Desktop/agentic-bioflow/wt/guided-launch-2`。

## 目標
/launch 依維護者的順序重排成六步：分析名稱 → 運算環境 → 管線（含版本與流程圖）→ 樣本表 → 參數 → 確認。前置檢查不再出現在這頁：沒設定好的東西不給選、不准送出，並指向設定頁。版本只在一個地方選。

## 維護者原話（verifier 出題用）
1. 「分析名稱要放在第1個順位，前置檢查一律在設定那邊做好，沒做好就不跑，而且怎麼會確定了pipline版本後面又一個可調版本的地方?」
2. 「流程圖要在使用者決定pipline時直接顯示於正下方不需要額外點選打開」
3. 「剩下順序是: 分析名稱->運算環境(國網or雲端，設定做好才顯示出來)-> 選pipline ->樣本表 ->確認」
4. 選擇題「參數表要放在新順序的哪裡？」→「樣本表之後、確認之前」。
5. 選擇題「版本只出現一次，選完管線後旁邊出現該管線的版本下拉選單，預設最新版；第 1 步前置檢查裡的『版本已指定』整步拿掉。這樣是你要的嗎？」→「對，就這樣」。
6. 選擇題「流程圖直接顯示在頁面上，需要放寬一條網頁安全設定：允許頁面顯示我們自己伺服器上的圖片（外部網站的圖仍然擋）。同意嗎？」→「同意，只放寬自家圖片」。

## 範圍：檔案
- `platform/abf_platform/web_board.py`：`render_launch`、`launch_checks`（移除或改為內部用）、GUIDED 與 /launch 的 `l_*`／`e_*`／`g_*`／`g2_*` 字串、/launch 用到的樣式。
- `platform/abf_platform/web_launch.py`
- `platform/abf_platform/web.py`：`launch_get`、`launch_post`、`launch_page`、`launch_body`，以及 /launch 回應的 CSP（只限 /launch 與其 400 回頁）。
- `platform/abf_platform/actions/__init__.py`：只動 `# ---- release-lookup-job` 區塊內的 `latest_release`（加 `releases` 欄位）。
- `platform/abf_platform/releases.py`：快取多存一個清單（見作法 4）。
- `platform/tests/`：test_web_guided_launch*.py、新檔 test_web_guided_launch_2d.py、受牽動的路由清單／頁面雜湊／release 測試。
- `docs/PLATFORM.md`、`docs/TESTING.md`（Guided launch 節）、`DESIGN.md`（/launch 線框與步驟順序）。
- `specs/guided-launch-2b/ledger.md`：加「2d」節。

## 介面事實（afd8b9e）
- 現在七步：1 前置檢查（`launch_checks` 的 ver／conn／reg／sheet／params 五列）、2 選管線（曾使用／其他 nf-core 兩分頁，管線與版本是兩個文字框）、3 流程圖（連結＋檔名大小，`GET /launch/diagram` 回圖）、4 樣本表、5 參數、6 運算環境、7 確認（摘要＋分析名稱＋送出）。
- 一個 POST 表單、一個送出鍵；管線或版本與 `shown_*` 不同時 303 重載（頁面不准有 script）。
- CSP（web.py:76）：`default-src 'none'; style-src …; form-action 'self'; frame-ancestors 'none'; base-uri 'none'`——沒有 img-src，所以圖片全擋。
- `actions.list_compute_envs` 回每個環境的 `status`（available 才能跑）、`message`、`config.sitePipelines`（站台登記的管線清單，可能沒有）。環境類型：Slurm 可跑；Google Cloud Batch 可建立與檢查。
- `actions.latest_release` 只回最新一版（`revision`）；它背後的 tags 工作拿到的是整份 tag 清單（`releases.parse_ls_remote`），`releases.pick_latest` 只挑最新，快取只存 `revision`。

## 作法
1. **六步順序**：① 分析名稱 ② 運算環境 ③ 管線 ④ 樣本表 ⑤ 參數 ⑥ 確認。各步標題與步驟狀態（已完成／目前／之後）沿用現有樣式。送出鍵在 ⑥。
2. **拿掉前置檢查這一步**。原本的五項改成就地處理：
   - 運算環境：② 只列 `status == "available"` 的環境（國網 Slurm 或雲端都一樣，只看狀態）。一個都沒有時，② 顯示「尚無可用的運算環境，請先至設定頁完成設定。」加連到 `/settings` 的連結，並且整頁不顯示送出鍵；POST 也回 400（e_ce）。
   - 站台登記：若選定環境的 `config.sitePipelines` 是非空清單而所選管線＋版本不在其中，③ 顯示「此管線版本尚未在所選運算環境登記，請先至設定頁登記。」＋設定頁連結；POST 回 400。清單不存在或為空時不檢查（同現狀「不需登記」）。
   - 樣本表：沒有任何已上傳樣本表時，④ 顯示「尚無已上傳的樣本表，請先上傳。」＋上傳頁連結（沿用頁面上既有的上傳入口網址）；POST 回 400。
   - 參數表讀取狀態（讀取中／讀不到）顯示在 ⑤ 的開頭，用現有的符號＋文字＋顏色。
   - 「版本已指定」那一列整個不要。
3. **管線與版本一處決定（③）**：
   - 分頁「曾使用的管線」與「其他 nf-core 管線」保留。曾使用分頁的每一列直接帶管線＋版本（現狀）。
   - 其他 nf-core 分頁：只有一個「管線」文字框。管線載入後（303 重載後），旁邊出現「版本」下拉選單，選項是該管線所有可用版本（新到舊），預設最新版；清單還在讀取中時顯示「正在讀取版本清單…」並沿用 15 秒自動重整；讀不到時顯示原因，下拉選單只放快取裡有的版本，沒有就不顯示下拉選單、不准送出（POST 400 e_revision）。
   - 頁面任何其他地方都不再有可以改版本的欄位；⑥ 摘要只顯示。
   - 版本下拉選單的值和 `shown_revision` 不同時，按送出照現行規則 303 重載。
4. **版本清單來源**：`actions.latest_release` 的回傳多一個欄位 `releases`：可用版本（`releases.usable`）由新到舊的 list[str]；`revision` 仍是最新一版。`releases.py` 的快取 entry 多存 `releases`，舊快取沒有這欄時 `releases` 只含 `[revision]`。不新增 MCP 工具、不新增網路連線（仍由站台代理讀 tags）。
5. **流程圖直接顯示（③ 正下方）**：管線與版本都確定、而且代理已讀到圖時，在 ③ 管線欄位正下方顯示 `<img src="/launch/diagram?pipeline=…&revision=…" alt="<管線> <版本> 流程圖">`，寬度 `max-width:100%; height:auto`，不需點開。讀取中顯示「正在讀取流程圖…」；這個管線沒有流程圖時顯示「此管線未提供流程圖。」。拿掉「開啟流程圖」連結與檔名／大小那行。
6. **CSP**：只在 /launch（GET 與 POST 的 400 回頁）的 CSP 加 `img-src 'self'`。其他頁面的 CSP 不變。不加任何外部網址。
7. 用字守門（2b 的禁用詞測試）照舊；新字串用正式書面語，英文版對應。

## 失敗先行測試（新檔 `platform/tests/test_web_guided_launch_2d.py`；假代理用 test_web_guided_launch_2.py 的 `Fake`）
verifier 出題時以此為底再補；至少包含：
- K01 步驟順序：/launch 的六個步驟標題依序為 分析名稱、運算環境、管線、樣本表、參數、確認（中文）；英文版對應；頁面沒有「前置檢查」。
- K02 分析名稱在第一步，且是 ① 裡唯一的必填輸入；送出鍵在 ⑥。
- K03 運算環境只列 available：兩個環境一個 available 一個不是，下拉選單只出現 available 那個。
- K04 沒有可用環境：顯示設定頁連結與句子，頁面沒有送出鍵；直接 POST 回 400。
- K05 站台未登記：sitePipelines 有清單但不含所選管線版本 → ③ 出現句子與設定頁連結；POST 400。
- K06 沒有樣本表 → ④ 句子＋上傳連結；POST 400。
- K07 版本只出現一次：管線載入後，整頁只有一個 name="revision" 的可編輯控制項，而且是 `<select>`，選項等於 Fake 的版本清單（新到舊），預設選最新。
- K08 版本清單讀取中 → 「正在讀取版本清單…」＋meta refresh；讀不到且無快取 → 無下拉選單、POST 400。
- K09 `actions.latest_release` 回 `releases`（新到舊、只含 usable tag）；舊快取無 releases 時回 `[revision]`。
- K10 流程圖直接顯示：管線版本已載入且有圖 → ③ 內有 `<img src="/launch/diagram?...">` 且有 alt；頁面沒有「開啟流程圖」字樣；圖在管線欄位之後、④ 之前。
- K11 流程圖讀取中／沒有圖的兩個句子。
- K12 CSP：/launch 的回應標頭含 `img-src 'self'`；另挑一個非 /launch 頁面（例如 `/`）的 CSP 不含 img-src。
- K13 用字守門對新頁面仍全綠。
- K14 手機 390 寬：版面規則不出現橫向捲動（img 有 max-width:100%）。

## 允許改的斷言
- 舊測試中斷言七步順序、前置檢查五列、流程圖連結與檔名大小、版本文字框、CSP 無 img-src（只限 /launch）的，改成新行為；每條在 ledger 寫舊→新與理由。
- 頁面雜湊、路由清單重釘。
其他斷言不准刪或放寬。

## 完成標準
全套測試綠（WSL：清掉 platform 下的 __pycache__ 後 `bash tests/run_all.sh --timeout 900`），K01–K14 都在且通過，ledger 有 2d 節，DESIGN.md 的 /launch 線框改成六步。

## 不做
- 不改設定頁本身（只連過去）。
- 不改其他頁面與側欄字串（留給 web-wording-sweep）。
- 不加 script；不改其他頁面的 CSP。
- 不新增 MCP 工具。

## 裁決
1. 參數表在樣本表之後、確認之前（維護者 10-28 選）。
2. 運算環境「設定做好」＝`status == "available"`；國網與雲端一視同仁。
3. 上傳樣本表的連結：用頁面目前已有的上傳入口網址；若沒有就連 `/`（看板）並在 ledger 記下。
4. （10-28，回應合約）S2 改句為「此管線版本尚未在所選運算環境登記，請洽管理者登記；已登記的管線列於設定頁。」——設定頁目前只能檢視站台登記的管線，不能登記。連結仍指向 `/settings`。
5. （10-28，回應合約）其他 nf-core 分頁：新管線（與 shown_pipeline 不同）而版本空白時，送出 303 重載，不回 400；重載後版本預設最新、shown_revision 設為最新，參數表與流程圖用這一版讀（TC-024、025）。2b TC-023 在 ledger 改舊→新。
6. （10-28，回應合約）③ 顯示流程圖時，③ 的 `<details>` 一律帶 `open`，不論目前是哪一步（TC-040）。
7. （10-28，回應合約）版本下拉出現時，「套用此版本」連結拿掉（TC-032）；「曾使用」分頁只用隱藏欄帶版本（TC-023）。
8. 合約：`specs/guided-launch-2d/test-case.md`＋`test-case-overview.md`（verifier 10-28 確認；S2 句子依裁決 4 改）。測試檔 `platform/tests/test_web_guided_launch_2d.py`。

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
