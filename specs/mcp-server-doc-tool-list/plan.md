---
id: mcp-server-doc-tool-list
title: mcp_server.py 開頭兩處說明（「六個／七個唯讀工具」與工具名單）改成和實際註冊的十個唯讀工具一致，並加一則防再過期的測試
tier: A
kinds: backend
lane: L22-mcp-doc
branch: test/mcp-server-doc-tool-list
base: origin/v3@bb0e8d6（2026-10-29 量；行號取自此，executor 開工前用 `git show origin/v3:<檔>` 重查，不對以實際內容為準）
source: 2026-10-29 清理掃描（A 級：只改註解與說明字串、加一則測試，不改任何執行邏輯）
---

# mcp-server-doc-tool-list

> 本檔由 developer-agent 的 subagent 寫（2026-10-29），只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。純文字＋測試，不動邏輯。

## 目標
`mcp_server.py` 檔頭的兩處說明互相矛盾，也都落後程式：第 1 行說「六個唯讀工具」，第 2 行說「七個唯讀工具」，程式實際註冊了十個唯讀工具，且名單漏列三個（`list_used_pipelines`、`my_usage`、`run_outputs`），寫入類的 `forget` 也沒列。把說明改成和程式一致，並加一則測試，之後再加工具卻忘了改說明就會紅。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「過期文件與程式矛盾」要附 `file:line` 證據，且要能描述一則現在會紅的測試。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/mcp_server.py`（只改註解與模組說明字串：第 1–5 行；**不動任何可執行行**）
- `platform/tests/test_mcp_server_doc.py`（**新檔**；檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字，說明為何不加進既有檔，例如「現有測試要啟動伺服器並用 SDK 客戶端連線，沒有檢查檔頭說明是否列全已註冊的工具；這則只讀原始碼文字，不需要安裝 mcp」）
- **不准碰**：`guidance.py`（見「不做」）、`actions/`、`web*.py`、`jobs.py`、`store.py`、任何既有測試的既有斷言、`docs/`。

## 作法
### 證據（說明 vs 程式）
- 程式事實：`mcp_server.py` 以 `annotations=_READ_ONLY` 註冊的工具共十個：`list_runs`（第 39 行）、`get_run`（45）、`list_compute_envs`（57）、`get_compute_env`（63）、`list_agents`（68）、`list_site_files`（74）、`list_used_pipelines`（82）、`my_usage`（88）、`run_outputs`（96）、`read_task_log`（104）。`_add_write_tools`（118 行起）再註冊 `launch`（122）、`cancel`（143）、`forget`（152）、`resume`（164）、`relaunch`（177）。總數十五，與 `platform/tests/test_pat.py:383` 的 `len(tools) == 15` 一致。
- 過期說明一：`mcp_server.py:1` 「offers six read-only tools」——六個是 009c 之前的數字（見 `test_mcp.py:57` 註解「was exactly six read-only tools」）。
- 過期說明二：`mcp_server.py:2–3` 「seven read-only tools, and the tools that ask a person: list_runs, get_run, list_compute_envs, get_compute_env, list_agents, list_site_files, read_task_log, launch, cancel, resume, relaunch」——七個名字都對，但漏了 `list_used_pipelines`、`my_usage`、`run_outputs`（讀）與 `forget`（問人）。
- 過期說明三：`mcp_server.py:5` 「The seven read tools carry readOnlyHint」——實際十個。
- 對照：同檔第 7–10 行對 `list_site_files`、`read_task_log` 的描述是對的，不動。

### 決定
- 只改字：第 1 行改成不寫死數字或改成十個；第 2–3 行把十個唯讀工具與五個「問人」工具（含 `forget`）逐一列名；第 5 行的數字改成十。**第 1 行開頭的 `# Not the Seqera MCP server:` 前綴與它的語意（這個伺服器讀本機索引、不是 Seqera 託管的那個）保持不變。**
- 不改任何程式行；用 `git diff` 確認差異只落在 `#` 註解行與 `"""` 說明字串內。
- 站台程式與平台程式的掃描測試會掃禁字：新增文字不得含 `test_scope` 禁用的完整單字（見 `jobs.py:41` 附近的說明；有疑問先跑 `test_scope.py`）。

## 失敗先行測試
新檔 `platform/tests/test_mcp_server_doc.py`，先寫、改字前跑一次確認紅，紅的輸出貼進 ledger。測試只讀原始碼文字（`ast.parse` 該檔），不 import `mcp`、不連網、不開資料庫。
- `test_module_doc_names_every_registered_tool`：以 `ast` 取所有 `@server.tool(name="…")` 裝飾器的 `name` 常數（含 `_add_write_tools` 內的），得到十五個名字；對每一個，`ast.get_docstring(模組)` 必須含該名字。**現在紅**：缺 `list_used_pipelines`、`my_usage`、`run_outputs`、`forget`。
- `test_module_doc_counts_the_read_only_tools`：從同一棵 AST 數出 `annotations=_READ_ONLY` 的工具數 N（現在是 10）；模組說明字串裡「`<數字詞> read` 開頭的那句」（正則 `\b(six|seven|eight|nine|ten|eleven|twelve)\b read`）轉成整數後必須等於 N。**現在紅**：寫的是 seven。
- `test_first_comment_line_does_not_name_an_old_count`（鬆條件）：檔案第 1 行不得含 `six` 或 `seven`。**現在紅**：含 six。
- 對照組（必須一直綠）：已註冊工具的名字集合 == `{…十五個…}` 寫死在測試裡的清單（先釘住事實，之後加工具會紅，提醒同時改說明）；`test_pat.py:383` 的 `len(tools) == 15` 與既有 `test_mcp.py` 不改、保持綠。
- 手動檢查（記 ledger，verifier 自己重跑）：`git diff -U0 origin/v3 -- platform/abf_platform/mcp_server.py`，逐行確認沒有「不是 `#` 開頭也不在模組 `"""` 內」的變更行；兩分支各 `ast.parse` 後去掉模組 docstring 的 AST 比對相等，輸出貼上。

## 完成標準（done when）
- 前三則新測試改前紅、改後綠；對照組全程綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」，只剩那一條視同綠）。
- ledger 記：`git diff --stat` 只含「範圍」列的兩個檔；`mcp_server.py` 沒有可執行行被改（AST 比對輸出貼上）。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`ABF_PYTEST_TARGETS=tests/test_mcp_server_doc.py bash tests/platform_test.sh`（相對於 `platform/`）。
  - 全套：`tests/run_all.sh` 不接受原生 Git Bash，要在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII（例如 `$HOME`）：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。repo 與 worktree 必須在本機磁碟；同一個 checkout 不可同時跑兩次。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 Bash 的 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束，讀完結果才結束回合；測試還在背景跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 讀碼一律 `git -C <repo> show origin/v3:<path>`；實作在 worktree 的 `test/mcp-server-doc-tool-list` 分支，base 為 `origin/v3`。

## 不做
- 不改任何可執行行、工具名稱、描述字串（`description=` 是使用者與模型看得到的文字）、`annotations`。
- **不改 `guidance.py:16` 的 `FIXED_SENTENCE`**（「Seven tools of this server are read-only」，同樣落後：實際十個）。那句是送給 MCP 客戶端的指示文字，屬使用者看得到的內容，且 spec 009g 與 `MAX_BYTES = 2048` 的長度限制都綁著它，不是 A 級；見裁決 2。
- 不改 `docs/`；不需要 migration。

## 裁決
1. **說明裡寫死數字，還是改成不寫數字？** 寫死數字最容易再過期；但「十個唯讀」對讀者有資訊量。**建議：保留數字，靠 `test_module_doc_counts_the_read_only_tools` 防再過期。**
2. **`guidance.py:16` 的「Seven tools … read-only」要不要一起改？** 它同樣不對（十個），但那是對外指示文字，改它要同步 spec／長度預算／可能的 docs 與測試釘住的原文。**建議：本件不含；由你決定是否另開一件（屬 B 級以上，需看 `test_guidance.py` 與 spec 009g）。**
3. **新測試放新檔還是既有檔？** 既有 MCP 測試都要啟動伺服器，需要安裝 `mcp`；這則只讀文字，放新檔才能在沒有 `mcp` 的環境也跑。**建議：新檔 `test_mcp_server_doc.py`（需 `# Nothing existing:` 檔頭）。**

### developer-agent 確認（2026-10-29）
證據已在 origin/v3 逐行核對屬實；裁決全部照「建議」定案。A 級：只收緊或只改註解，不放寬任何安全網、不改使用者看得到的文字。

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
