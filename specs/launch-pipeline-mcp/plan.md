---
id: launch-pipeline-mcp
title: 開一個只會「提出」的 MCP 工具 launch_pipeline，送出自訂 pipeline 仍由本人按確認
tier: B
kinds: backend
lane: L44-canvas-mcp
branch: feat/launch-pipeline-mcp
base: origin/v3@108bfdff；排在 canvas-mcp-read 合併之後（兩片都改 mcp_server.py 與同一批工具名單測試），開工前先 rebase 並重查行號
source: PLAN-abf-v3-replan-2026-10.md 017e「MCP 鏡像：… `launch_pipeline`（`_add_write_tools`、`chat_tools.REQUEST_TOOLS`、`confirm.JOB_KIND`）」＋017d 已完成的 `request_pipeline_launch`
---

# launch-pipeline-mcp

> 只有計畫、沒有程式。B 級 backend → verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
`actions.request_pipeline_launch` 已在 v3（017d），但只有程式能叫，使用者的 AI 與聊天都叫不到。這一片補一個只會「提出」的 MCP 工具 `launch_pipeline`，行為與既有 `launch` 工具一模一樣：不會自己啟動任何東西，要本人在自己的表單或確認頁按「好」。

## 維護者原話（verifier 出題用）
- 017e：「MCP 鏡像：… `launch_pipeline`（`_add_write_tools`、`chat_tools.REQUEST_TOOLS`、`confirm.JOB_KIND`）；… parity 表全列。」
- 裁示 1：「使用者用自己的 AI 走 MCP」。
- 裁示 5：v1 畫布＝「拖模組、連線、填參數、驗證、送去跑、匯出 zip、版本紀錄與分享」。
- 10-18 裁示（replan 第 65 行）：「AI 可發起任何送出、頁面跳『確認送出嗎？』本人按」。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/mcp_server.py`（加 `launch_pipeline`，標 `_WRITES`；檔頭 docstring「five asking tools」改成六個）
- `platform/abf_platform/actions/chat_tools.py`（`REQUEST_TOOLS` 加 `launch_pipeline`；提示字串加一行，避開 `BANNED_WORDS`）
- 新檔 `platform/tests/test_mcp_launch_pipeline.py`
- 釘住工具名單的既有測試，只改名單與計數：`test_mcp_server_doc.py`、`test_chat_tools.py`、`test_actions_layer.py`、`test_owner_guard.py`（l.150 對應表）及 `git grep -l '"my_usage"' platform/tests` 其餘檔
- **不准碰**：`web.py`、`web_board.py`、`static/`、`confirm.py` 的確認邏輯、`actions/__init__.py` 的 `request_pipeline_launch`（只呼叫、不改）、`docs/PLATFORM.md`、`pipeline_launch.py`、dev-queue.json。

## 作法
- **證據**（origin/v3@108bfdff）：
  - `actions/__init__.py:1265` `request_pipeline_launch` 已存在；`git grep -n "request_pipeline_launch" platform/abf_platform/mcp_server.py` 無結果＝MCP 摸不到。
  - `test_owner_guard.py:150`：`"request_pipeline_launch": "web launch page"`——現在把它登記成「網頁送出頁」的名字，工具加進來後要改成 MCP 也有出口。
  - `mcp_server.py:123` `launch` 工具與 l.134–143 的 `launch_tool`：`actions.request_launch(… caller=_caller(ctx), person=actions.person_at(ctx), remote=_remote(ctx))`——照這個形狀寫。
  - `chat_tools.py:16` `REQUEST_TOOLS = frozenset({"launch","cancel","resume","relaunch","forget"})`；`classify_check` 對「既非唯讀也不在 REQUEST_TOOLS」的工具丟 ValueError，所以兩處必須同批加。
  - `chat_tools.BANNED_WORDS`（`approve|confirm|confirmed_by|void|yes`）：提示字串與工具說明不可出現。
- **工具介面**：參數只有 `pipeline_id`、`version`（可省）、`compute_env`（可省）與樣本表／參數的欄位，欄位名照 `request_pipeline_launch` 的簽名。**沒有任何參數能表示「已同意」**。
- **回傳**：與 `launch` 相同——一句話告訴 AI「已提出，等本人在表單或頁面按好」，附該去哪裡按。
- **擁有者規則**：由 `request_pipeline_launch` 在動作層處理；工具只負責傳 `caller=_caller(ctx)`。

## 失敗先行測試
`platform/tests/test_mcp_launch_pipeline.py`，先寫、改程式前跑確認紅，紅的輸出貼進 ledger。
- 呼叫 `launch_pipeline`：回「已提出、等本人」，**資料庫沒有新增任何 run／job**（未經本人確認不改變資料）。**現在紅**（工具不存在）。
- 工具簽名沒有名稱含 `confirm`／`approve`／`yes`／`void` 的參數。
- 跨使用者：乙對甲的 `pipeline_id` 呼叫，回「找不到」。
- 對不存在的版本、沒驗證通過的 pipeline：回含原因與處理方式的錯誤，不丟堆疊。
- `/chat/spec` 能啟動：`launch_pipeline` 在 `REQUEST_TOOLS` 內，`classify_check` 不丟 ValueError；聊天提示不含禁字。
- 工具名單的所有釘住測試更新後全綠；asking 工具六個、其餘計數與 docstring 一致。

## 完成標準（done when）
- 新測試改前紅、改後綠；全套 `tests/run_all.sh` 全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含範圍內的檔；既有斷言除工具名單與計數外沒被刪或放寬；`launch_pipeline` 呼叫前後資料庫行數比對貼進 ledger。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」。
- 單檔測試：WSL repo 根目錄 `python -m pytest platform/tests/test_mcp_launch_pipeline.py`。全套寫法見 `upgrade-hint-followup.md`「環境事實」。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不開 `create_pipeline`／`update_pipeline`／`export_pipeline`／`validate_pipeline` 的 MCP 工具。
- 不加網頁路由 `/act/launch_pipeline`（017e 的設計閘之後）。
- 不改確認頁文字、不改 `confirm.JOB_KIND`（`request_pipeline_launch` 已用）。

## 裁決
1. **工具名叫 `launch_pipeline` 嗎？** 建議：是，與 017e 原文、動作名一致。
2. **要不要順便開 `create_pipeline`／`update_pipeline` 的 MCP 工具？** 建議：不要，另案。理由：它們寫入平台自己的紀錄、不經確認，歸類上既不是唯讀也不是「提出」，`classify_check` 會直接丟 ValueError；需要先由維護者或 developer-agent 決定歸類方式（例如新增第三類「平台自寫、不花錢」），不能由這一片順手決定。
3. **聊天助理要不要也能提出 `launch_pipeline`？** 建議：要，加進 `REQUEST_TOOLS`（10-18 裁示「AI 可發起任何送出」）；確認仍在頁面，由本人按。

### developer-agent 確認（2026-10-29 22:1x）
證據已抽查（origin/v3 無 find_module／export_pipeline；mcp_server.py 未呼叫 request_pipeline_launch）。上列裁決一律照「建議」定案。

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

### 補充裁決（developer-agent，2026-10-30 04:3x，回 executor BLOCKED）
1. **docs/PLATFORM.md 開放**：只准在 `tests/platform_storage_doc_test.sh` 要求的五處（answers questions／「Fourteen tools.」計數句／`permission ask rule for`／「The platform's actions live in one place」／「- **Instructions.**」）補上 `launch_pipeline`，計數照實更新；其他段落不動。
2. **kit 的 ask 清單要加**：`extensions/claude-code-kit/settings.json` 的 `permissions.ask` 加 `mcp__abf-platform__launch_pipeline`（這是產品給使用者的設定，不是 Claude 權限；加進去＝收緊）。同步更新 `test_keep_submissions.py:1298`（TC-114）與 `test_resume_entrypoints.py:154` 的釘選清單為六個工具，函式名的 five 可改 six；不准刪斷言。
3. **guidance.py FIXED_SENTENCE**：加上 launch_pipeline，讓 AI 連線說明列出全部提出工具；有釘這句的測試照實更新。
4. **憲法 Safety Net 清單**（`.specify/memory/constitution.md:188` 的 `(today …)`）：加上 `launch_pipeline`。只改這個括號清單，規則文字不動；這是 constitution_6_test TC-045 要求的「清單＝實際註冊的寫入工具」。PRINCIPLES／ROADMAP 若有 TC 要求同步，照測試補最小字。此項屬憲法修正，PR 會等維護者點頭才合（developer-agent 處理，executor 照做即可）。
5. **TC-161 與 test_mcp_canvas_read 的放寬**：追認。理由：本片目的就是在 mcp_server.py 新增 launch_pipeline，舊斷言的禁令與本計畫正面衝突；web.py、web_board.py、handlers.py 的檢查必須原樣保留。
6. 欄位名用 `ce_name`、`run_name` 必填，照 `request_pipeline_launch` 簽名；不需要 migration（沒有資料結構變動）。
7. 完成條件不變：最終 HEAD 上完整跑一次 `tests/run_all.sh`，全綠才寫 GREEN；背景跑時必須等它結束。
