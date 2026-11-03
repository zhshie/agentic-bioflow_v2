---
id: resume-edit-web
title: 網頁「修改後續跑」：失敗或取消的 run 可在網頁改參數與資源設定再續跑
tier: B
kinds: ui
lane: L33-web-resume-edit
branch: feat/resume-edit-web
base: v3
source: 維護者 10-29「加速進行，這禮拜做完『還沒做，要讓同事不問人就能自己用完的部分』」；續跑改參數的後端 resume-edit-params-a～d 已合併（#195、#201、#205、#208），網頁還沒有入口
---

# resume-edit-web

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/resume-edit-web/plan.md`。**只處理本任務**。

## 目標
run 失敗（例如記憶體不夠）時，同事現在只能在網頁按「續跑」照原樣再跑，要改參數或資源得找人打指令。做一頁「修改後續跑」：列出這個 run 第一次送出時的參數（可改）和一格「額外設定」（例 `process.memory = '16 GB'`），送出後走既有的 `request_resume`，進既有確認頁 `/c/<id>`，確認頁列出每一項改動。

## 維護者原話（verifier 出題用）
1. 「加速進行，這禮拜做完"還沒做，要讓同事不問人就能自己用完的部分"」（10-29）→ 不必找人打指令就能改參數續跑。
2. 「跟Seqera platform一樣的模式，不要自己定義」（10-23 常設）→ 對照 Seqera 的 Resume：沿用原 run 的管線、版本、樣本、環境，只能改參數與設定。
3. 「先把功能做起來吧，以後再改美觀」（10-23）

## 範圍：檔案
- `platform/abf_platform/web.py`：新增 `GET /act/resume/edit?run=<id>`（畫表單）；`POST /act/resume` 多接受兩個可選欄位（作法 2）。
- `platform/abf_platform/web_board.py`：只限 STRINGS 新字串，以及在既有「續跑」按鈕旁加「修改後續跑」連結（`Acts.form` 附近；`_failure_notice` 的按鈕列也加）。
- `platform/abf_platform/web_launch.py`：只准新增函式或給既有函式加**可選**參數（例如 `groups_block` 加唯讀前置值），既有呼叫的輸出逐字不變。
- 新測試檔：`platform/tests/test_web_resume_edit.py`。
- 被逐字釘住、要跟著加項的既有測試：只加不刪、ledger 逐條列（預期：路由清單類測試——`test_aws_ce.py`、`test_aws_launch.py`、`test_gcb_ce.py`、`test_gcb_launch.py` 的路由集合、`test_web_parity.py`；run 頁按鈕相關斷言）。執行前 `git grep -n "/act/" platform/tests` 找全。
- `docs/TESTING.md`：手動一節（真站台：一個失敗 run 改 `process.memory` 續跑，確認頁看到改動，跑完看 `-resume` 同資料夾）。

## 作法
1. **入口**：run 頁與失敗通知卡，凡是出現「續跑」按鈕的地方，旁邊加連結「修改後續跑」→ `GET /act/resume/edit?run=<id>`（GET 只讀，不建請求）。不是自己的 run、或狀態不能續跑＝與既有 `/act/resume` 同樣的拒絕句，回 run 頁。
2. **表單頁**（`GET /act/resume/edit`）：
   - 頁首一行：run 名稱、管線＋版本、環境（唯讀，`dl.fields`）。下方灰字「管線、版本、樣本表與運算環境沿用第一次送出的內容，不能修改。」
   - **參數**：用第一次送出的參數當預填值，畫成與 `/launch` 第 5 步相同的四欄群組表（名稱、說明、類型、值）；說明與類型讀 `actions.pipeline_files`（與 /launch 同一路徑，載入中顯示既有 `reading` 句，不阻擋送出）；讀不到 schema 時退回成「名稱／值」兩欄，只列第一次送出有的參數。
   - **額外設定**：一個 textarea，標籤「額外設定（每行一項，例 process.memory = '16 GB'）」，非必填，上限沿用站台的 `MAX_EXTRA_CONFIG`（平台端以同數字檢查，超過＝400 句子）。
   - 按鈕「送出（前往確認頁）」；「返回」連回 run 頁。
   - POST 帶 CSRF：與既有 `/act/resume` 同一個（`act:<run_id>`）。
3. **送出**（`POST /act/resume`，向下相容）：沒有新欄位＝行為逐字不變。有 `p.<名>` 欄位時，只把**和第一次不同**的值收成 `params`（型別照 schema 轉，沿用 `web_launch.changed_fields`／`merge_params` 的規則）；`extra_config` 去掉首尾空白，空字串＝不帶。兩者都空＝等同一般續跑。呼叫 `actions.request_resume(..., params=..., extra_config=...)` → 303 `/c/<id>`。動作層拒絕＝回表單頁（400），保留所有已填值，表單上方「✕ 未能完成：<原因>」。
4. **確認頁**：沿用既有 `/c/<id>`；若它尚未列出 overrides，補上「改動」區：每個改動的參數一行「名稱：原值 → 新值」，額外設定原文用 `<pre>`。不改確認與送出的邏輯。
5. 只用現有 class 與 DESIGN.md token；不改 STYLE（D13 釘 sha256）；CSP 不變。中英字串皆正式書面語、不含 DESIGN.md「用字」禁用字。

## 六項必填檢核（ui 計畫固定段）
1. 確認頁規則：見作法 4；確認與送出邏輯不動。
2. 失敗狀態：動作層拒絕／run 不存在或不是自己的／不可續跑／額外設定過長／參數型別錯，各自的句子與回到哪一頁（作法 1、3）。
3. 提示句位置：錯誤句在表單最上方、按鈕列之前；唯讀說明在頁首資料下方。
4. 要改的舊測試：見「範圍：檔案」的清單與 grep 指令；只加不刪。
5. 手機寬度：390 px 無橫向捲動；四欄表在窄寬沿用 /launch 第 5 步的既有寫法。
6. 空狀態：第一次送出沒有任何參數＝顯示「第一次送出未指定參數，均使用管線預設值。」並仍可填額外設定；schema 讀不到＝兩欄退回（作法 2）。

## 失敗先行測試
`test_web_resume_edit.py`：失敗 run 的頁面有「修改後續跑」連結；成功或執行中的 run 沒有；GET 表單不寫資料庫、預填第一次的值；只改一個參數 → `request_resume` 收到只有那一個鍵的 params；只填額外設定 → 只帶 extra_config；兩者都空 → 與一般續跑相同；確認頁列出「原值 → 新值」與額外設定原文；跨來源／缺 CSRF＝403；他人 run＝404；過長額外設定＝400 且保留值；動作層拒絕＝400 帶原因；既有 `/act/resume` 無新欄位的行為與輸出逐字不變；390 px 由 TESTING.md 手動（截圖）確認。

## 完成標準（done when）
上列全綠；整套 `tests/run_all.sh --timeout 900` 綠（背景跑＋等待）；改到的既有斷言在 ledger 逐條列理由。

## 環境事實
- 後端：`actions.request_resume(platform_path, *, run_name, params=None, extra_config=None, caller=..., ...)`（`actions/__init__.py:1287`）；`build.edits_of` 算改動；`confirm.py:232` 已認得 `overrides`。
- 站台：`abf_station/launch.py` 的 `MAX_EXTRA_CONFIG`、`_check_extra_config`（resume-edit-params-a）。
- 既有網頁續跑：`web.py` `act_post`（約 :538），按鈕 `web_board.Acts.form`（約 :494），失敗卡 `_failure_notice`（約 :530）。
- 已知後端問題（不在本任務）：10-25 nano4 改參數續跑幾乎全部重算（resume-cache-miss 另案）。

## 不做
- 不改動作層、站台、確認／送出邏輯；不讓人改管線、版本、樣本表、環境；不做重跑（relaunch）的修改頁；不新增 MCP 工具；不改 STYLE 與 CSP。

## 裁決
1. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`。
2. `platform/pyproject.toml` executor 不能改；需要就寫進報告退回。
3. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有畫面慣例自訂預期值寫進 TC，不以「計畫未寫」退回；只有「照字面做不出來」或「違反憲法／ADR／安全」才算阻擋。
4. 與 L32（settings-pick-installed）、L17（web-wording-sweep）同碰 `web.py`／`web_board.py` 的不同區段：落地前 `git merge origin/v3`，衝突只保留雙方新增，不改對方的字。
5. worktree 用 Windows git 建，WSL 裡 `constitution_scope_test.sh` 紅＝環境問題，以 CI 為準，ledger 註明。
6. （2026-11-03）10-29 停在 Build 後 v3 又前進 275 個 commit。**第一步先 `git merge origin/v3`**：已知衝突在 `docs/TESTING.md`、`platform/tests/test_clean_page.py`、`test_cleanup_offer.py`、`test_dataset_cli.py`、`test_owner_binding.py`。照第 4 條處理（兩邊新增都留、不改對方的字；雜湊類測試重算），merge commit 後跑全套，再接著完成原本的 TC。已確認的合約照用，不重出題。

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
