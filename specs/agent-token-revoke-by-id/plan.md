---
id: agent-token-revoke-by-id
title: 用 id 撤銷「一把」代理 token（agent-token revoke --id N），並能列出 token id（agent-token list）
tier: B
kinds: backend
lane: L36-token-revoke-id
branch: feat/agent-token-revoke-by-id
base: origin/v3（行號取自 origin/v3@835d47e，executor 開工前用 `git show origin/v3:<檔>` 重查）
source: 維護者 2026-10-29 的一句想法（見「維護者原話」）；B 級＝CLI 行為改變、非畫面
---

# agent-token-revoke-by-id

> 只有計畫、沒有程式。B 級 → 需要維護者看過驗收報告再合併。

## 目標
現在撤銷代理 token 只能「按名字全撤」。同名代理換了新 token 之後，舊 token 想關就會連新的一起關。新增「按 id 只撤一把」，並新增能看到 id 的清單指令。按名字撤銷的行為不變。

**每日簡報那一行：** 以前它會「`agent-token revoke <名字>` 把這個名字底下所有還有效的 token 一次全撤，沒辦法只關舊的」，以後改成「可以用 `agent-token list` 看到每把 token 的 id，再用 `agent-token revoke --id N` 只撤那一把，同名的其他 token 照常能用；按名字撤的舊用法完全不變」。

## 維護者原話（verifier 出題用）
- 唯一來源：任務構想一句話（2026-10-29）：「revoke one agent token by id instead of every token of a name; from 2026-10-29: an old desktop token (id 1) was left live because revoking by name would also kill the new token.」
- 沒有其他維護者原話。以下由這句話導出的案例各至少一條測試：①可以只撤一把（id）②同名的另一把照常能用 ③撤掉的那把之後被拒 ④舊的按名字撤銷不變。其餘（`list` 指令、錯誤訊息、不印密鑰）是 developer-agent 依專案規則補的，標在 `## 裁決`。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/store.py`（新增兩個函式：`list_agent_tokens`、`revoke_agent_token`；不動 `revoke_agent_tokens`）
- `platform/abf_platform/cli.py`（新增 `cmd_agent_token_list`、改 `cmd_agent_token_revoke` 接受 `--id`；改 `asub` 子指令；檔頭 docstring 第 2 行的指令清單順手補 `list`）
- `docs/OPERATIONS.md`（第 114–115 行的指令表加兩列／改一列）
- `docs/PLATFORM.md`（第 189 行「To take an agent away」後補一句 `--id`）
- `platform/tests/test_agent_token_revoke_id.py`（新檔）
- **不准碰**：`platform/abf_platform/agents.py`、`receiver.py`、`actions/`（含 `__init__.py`）、`mcp_server.py`、`web*.py`、任何既有測試的既有斷言、`rebuild`、`ce`、`pat`、`oauth` 相關程式。

## 作法
- **證據**（origin/v3@835d47e）：
  - 現有撤銷：`platform/abf_platform/cli.py:296-299` `cmd_agent_token_revoke` 呼叫 `store.revoke_agent_tokens(path, args.name)`，印 `revoked %d token(s) of agent %s; ...`，沒撤到任何一把就回傳 1。指令定義 `cli.py:737-739`（`ar = asub.add_parser("revoke", help="revoke every token of an agent name")`，位置參數 `name`）。
  - 現有 store：`store.py:1061-1072` `revoke_agent_tokens`：`UPDATE tokens SET revoked_at = ? WHERE kind = 'agent' AND agent_name = ? AND revoked_at IS NULL`。
  - 資料表 `tokens` 已有 `id INTEGER PRIMARY KEY AUTOINCREMENT`、`kind`、`agent_name`、`revoked_at`、`user_id`（`store.py:85-99`）——**id 早就有，不需要新欄位**。
  - 拒絕舊 token 的現成機制：`store.py:980-990` `lookup_token` 只認 `revoked_at IS NULL`；代理端 `agents.py:127-130` 對這種 token 回 401「Unauthorized: missing, unknown or revoked agent token」。所以只要寫入 `revoked_at`，之後必被拒，不必改接收端。
  - 現成的「按 id 撤一把」範本：PAT 的 `store.py:962-972` `revoke_pat`（限定 `kind = 'pat'`，回傳撤了幾把）與 `cli.py:277-283` `cmd_pat_revoke`（`rejected: no live personal access token with id %s`）；列表範本 `store.py:949-957` `list_pats`、`cli.py:266-274` `cmd_pat_list`（不印值、不印雜湊）。**照這兩組做，語法與用詞跟 `pat` 一致。**
  - 通用的 `store.py:1033` `revoke_token(id)` 不限 kind，**不要用**——會讓 `--id` 誤撤 run token 或 PAT。
- **共用動作層的現況**（重要，見裁決 1）：token／user 的建立與撤銷**刻意**不在 `actions/`、MCP、網頁路由裡，只在終端機 CLI：`platform/tests/test_pat.py:277-288`（TC-A11）斷言 `dir(actions)` 沒有任何含 `user|pat|token` 的名字，且 MCP 工具與路由都沒有。本計畫維持這條界線：邏輯全放 `store.py`（一個動作一個函式），`cli.py` 只是薄薄的呼叫端。
- **擁有者規則**：現有 `revoke`（按名字）與 `pat revoke` 都是**操作者在終端機**執行，沒有「呼叫者身分」，也沒有「只能撤自己的」檢查；能執行指令＝能碰 `tokens.db`＝管理員。**`--id` 沿用這個規則，不新增檢查**（見裁決 2）。
- **決定（介面）**：
  - `abf-platform agent-token list [NAME]`：每把 agent token 一行：`id N  agent NAME  user USER|-  created YYYY-MM-DD HH:MM  revoked|not revoked`（格式仿 `pat list`，`cli.py:269-271`）。`NAME` 給了就只列該名字。沒有任何一把時印 `no agent tokens`（有給 NAME 則 `no agent tokens for NAME`），回傳 0。只列 `kind = 'agent'`，依 id 排序；`user` 用 `LEFT JOIN users` 取名字（舊 token 沒有 user → 印 `-`）。**不印 token 值、不印雜湊。**
  - `abf-platform agent-token revoke NAME`：**完全不變**（含輸出文字與回傳碼）。
  - `abf-platform agent-token revoke --id N`：`N` 是整數。成功印 `revoked agent token N (agent NAME); it is refused from its next request, other tokens of this agent are untouched`，回 0。找不到、不是 agent token、或早已撤銷 → 印到 stderr：`rejected: no live agent token with id N (沒有這個有效的代理 token); list them with: abf-platform agent-token list`，回 1，不改任何資料。
  - `NAME` 與 `--id` **二選一、必須剛好一個**：兩個都給或都沒給 → `rejected: give either an agent name or --id N, not both and not neither (請給代理名字或 --id，二選一)`，回 1，不改資料。實作上 `name` 改 `nargs="?"`、`--id` `type=int`，在 `cmd_agent_token_revoke` 內檢查（`argparse` 的互斥群組吃不下「位置參數可省略」的訊息格式）。
  - 錯誤輸出一律走 `_err`（現有 helper，`cli.py` 內 `pat revoke` 就是這樣用），不露堆疊、路徑、SQL。
- **決定（store）**：
  - `list_agent_tokens(tokens_path, name=None)` → `[{"id","agent_name","user","created_at","revoked_at"}]`；檔案不存在回 `[]`（仿 `revoke_agent_tokens` 開頭）。
  - `revoke_agent_token(tokens_path, token_id_)` → 回傳 `{"agent_name": ...}`（撤到了）或 `None`（沒有此有效 agent token）。一個 `UPDATE ... WHERE id = ? AND kind = 'agent' AND revoked_at IS NULL`，再依 `rowcount` 查名字（供訊息用）；檔案不存在回 `None`。
- **決定（文件）**：`docs/OPERATIONS.md` 加 `agent-token list [name]` 一列，`revoke` 那列改成 `agent-token revoke <name>` / `agent-token revoke --id N`；`docs/PLATFORM.md:189` 補「只關舊的那把：先 `agent-token list` 看 id，再 `agent-token revoke --id N`」。`test_onboarding_doc.py:14-20` 會檢查文件裡的 `abf-platform agent-token <子指令>` 都在 `cli.py` 有定義，所以 `list` 一定要在 `asub.add_parser("list"` 出現。

## 失敗先行測試
全放新檔 `platform/tests/test_agent_token_revoke_id.py`（檔頭第一行照專案慣例寫 `# Nothing existing: ...` 說明為何新檔）。風格仿 `test_pat.py`：`run_cli([...], env=pkg_env(ABF_PLATFORM_DB=tmp_path/"data"/"index.db"))`、`store.create_token(...)`、`sqlite3` 直接查 `tokens.db`。先寫、改程式前跑一次確認紅，紅的輸出貼進 ledger.md。**以下全部「現在紅」**（除標「對照」者）。
1. `test_list_shows_id_name_user_and_state_but_never_the_token_value` — 建兩把同名 `ag`（一把有 user alice、一把沒有），撤其中一把後 `agent-token list`：每把一行含 `id N`、`agent ag`、舊的那把 user 印 `-`、有 `revoked` / `not revoked`；stdout 與 stderr 不含任一 token 值、不含其 sha256。
2. `test_list_with_a_name_shows_only_that_agent_and_never_a_run_or_pat_token` — 另建 `other` 的 agent token、一把 run token、一把 PAT；`list ag` 只出現 `ag` 的行；`list`（無名）出現 `ag` 與 `other`、不出現 run／PAT 的 id。
3. `test_list_with_no_agent_tokens_says_so_and_exits_0` — 空的 `tokens.db` 與不存在的 `tokens.db` 都印 `no agent tokens`、回 0。
4. `test_revoke_by_id_revokes_only_that_token_and_the_same_name_keeps_working` — 同名 `ag` 兩把（id 1 舊、id 2 新）；`revoke --id 1` 回 0；`store.lookup_token` 對舊值回 `None`、對新值仍回 `{"agent_name": "ag", ...}`；`tokens.db` 裡 id 1 的 `revoked_at` 非空、id 2 為空。
5. `test_a_token_revoked_by_id_is_refused_by_the_receiver_but_the_other_is_not` — 用 `receiver.create_app(index, tokens)` 的 `TestClient`（寫法照 `test_owner_tokens.py` 的 `_client`／`_hello`）：撤 id 1 後，`POST /agent/hello` 帶舊 token → 401、帶新 token → 200。
6. `test_revoke_by_id_prints_what_happened_and_what_is_left_and_never_the_secret` — 成功輸出含 `revoked agent token 1`、`agent ag`、`other tokens of this agent are untouched`；stdout／stderr 不含 token 值與雜湊。
7. `test_revoke_by_id_of_an_unknown_id_is_rejected_with_the_next_step_and_changes_nothing` — `--id 999` 回 1、stderr 含 `rejected` 與 `agent-token list`、無堆疊（不含 `Traceback`）、`tokens.db` 的 `revoked_at` 全沒變（比對前後整張表）。
8. `test_revoke_by_id_will_not_touch_a_run_token_or_a_pat_or_an_already_revoked_one` — 對 run token 的 id、PAT 的 id、已撤銷的 agent id 各跑一次 `--id`：都回 1、都不改資料（PAT 仍能 `lookup_pat`、run token 仍能 `lookup_token`）。
9. `test_revoke_needs_exactly_one_of_name_or_id` — `revoke`（都沒給）、`revoke ag --id 1`（都給）都回 1、stderr 含 `either an agent name or --id`、不改資料；`revoke --id abc` 由 argparse 拒絕（回 2）、不改資料。
10. `test_revoke_by_name_still_revokes_every_live_token_of_the_name_and_prints_the_same_line`（對照，必須一直綠）— 三把 `ag`、一把 `other`；`revoke ag` 回 0、stdout 恰為 `revoked 3 token(s) of agent ag; the agent is refused from its next request`；`other` 不受影響；`revoke nobody` 仍回 1 並印 `revoked 0 token(s) of agent nobody; ...`。
11. `test_the_cli_is_a_thin_caller_of_the_store` — 用 `ast` 讀 `cli.py`，斷言 `cmd_agent_token_list`／`cmd_agent_token_revoke` 內沒有 `sqlite3`／`execute(`／`SELECT`／`UPDATE`，且呼叫 `store.list_agent_tokens`／`store.revoke_agent_token`；同時斷言 `dir(actions)` 沒有 token 相關名字（TC-A11 的界線沒被破壞）。
12. `test_the_docs_name_the_new_commands` — `docs/OPERATIONS.md` 含 `agent-token list` 與 `agent-token revoke --id`；`docs/PLATFORM.md` 含 `agent-token revoke --id`。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」）：在 `origin/v3` 與本分支各跑第 10 條與 `test_pat.py`、`test_onboarding_doc.py`、`test_station_e2e.py::test_tc006_a_revoked_token_stops_the_agent_with_the_reason`，貼輸出；`revoke NAME` 的輸出必須逐字相同。

## 完成標準（done when）
- 上列新測試改前紅（第 10 條除外）、改後全綠。
- 整個 `platform/tests` 套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- `abf-platform agent-token revoke ag`（按名字）的輸出、回傳碼、效果與 origin/v3 逐字相同（兩分支比對貼進 ledger）。
- `--id` 只撤到 `kind='agent'` 且尚有效的那一把；其他同名 token、run token、PAT 都不受影響。
- ledger 記：`git diff --stat` 只含「範圍」列的檔；沒有既有測試被改弱；沒有 migration 檔；所有輸出沒有 token 值。
- 閱卷「需要人看的事」：`rejected: ...` 與 `revoked agent token N ...` 兩句的用詞是否夠白話。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`bash tests/<name>.sh`（Git Bash 多數可跑）；pytest 單檔：`ABF_PYTEST_TARGETS=tests/test_agent_token_revoke_id.py bash tests/platform_test.sh`（相對於 `platform/`）。
  - 全套：`tests/run_all.sh` 拒絕原生 Git Bash，要在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。repo 與 worktree 要在本機磁碟，不可在同步雲碟上；同一個 checkout 不可同時跑兩次。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束；測試還在背景跑時不准交報告。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 不准跑：碰站台或 HPC 的東西、用 `~/.config/agentic-bioflow` 打真實部署。測試一律用 `tmp_path` 的 `ABF_PLATFORM_DB`。
- 現有測試的依賴（不要弄壞）：`test_pat.py` TC-A06／A11、`test_onboarding_doc.py` 的 `check_subcommands`（文件裡每個 `abf-platform agent-token X` 都要在 `cli.py` 有 `asub.add_parser("X"`）、`test_station_e2e.py` TC-006、`test_cleanup_offer.py:818` 的頂層指令清單（只含頂層，`agent-token` 底下加子指令不影響）。

## 不做
- 不改 `revoke_agent_tokens`（按名字）、`lookup_token`、接收端、代理端；不改 `revoke_token`（通用版）。
- 不做 `agent-token revoke` 的「撤銷前確認」提示（現有 `revoke` 與 `pat revoke` 都沒有，保持一致；理由見裁決 3）。
- 不加 MCP 工具、網頁路由、`actions/` 函式；token 管理仍只在終端機。
- 不做「只撤舊的、自動挑最舊的一把」之類的聰明模式。
- 不給 `pat list` 加 agent token；不加 `--all` / `--json` 旗標。
- 不新增欄位、不改 `tokens.db` 結構。

## 遷移說明（migration）
**不需要 migration。** 沒有新增欄位或資料表：`tokens.id`、`kind`、`agent_name`、`revoked_at`、`user_id` 都已存在（`store.py:85-99`）；`--id` 只是新增讀取與一個條件式 `UPDATE`，既有資料不改、舊資料庫直接可用。

## 裁決
1. **「共用動作層」放哪？** 專案現況是 token 管理刻意不在 `actions/`（`test_pat.py` TC-A11 鎖住），專長守則的「動作層」在這裡對應 `store.py` 的函式。**建議：新邏輯放 `store.py`（兩個新函式），`cli.py` 只呼叫；不往 `actions/` 加東西，並用測試 11 鎖住「CLI 薄」與「actions 沒有 token 名字」。** 若維護者其實想讓代理 token 能在網頁／MCP 管理，那是另一件事，另開。
2. **擁有者規則怎麼辦？** 現有 `revoke`（按名字）與 `pat revoke` 都是操作者在終端機，沒有「呼叫者是誰」，所以沒有「只能撤自己的」可以照抄。**建議：`--id` 沿用「能下指令＝管理員」，不加擁有者檢查；`list` 會顯示 user 欄，方便操作者核對是誰的。** 跨使用者的 TC（專長守則）因此不適用，閱卷時請在報告寫明「此指令無呼叫者身分，沿用現有規則」。
3. **要不要撤銷前確認？** 專長守則說寫入動作要經過人工確認管道；但此指令本身就是操作者在終端機手打（類似 `pat revoke <id>` 不確認），且撤銷可由 `agent-token new` 重發補救。**建議：不加確認提示，與 `revoke NAME`、`pat revoke` 一致。** 閱卷者若認為仍須確認，請標「需要人看的事」而不是 FAIL。
4. **指令語法：`revoke --id N` 還是 `revoke-id N`？** **建議：`revoke --id N`**（維護者構想與任務描述都這樣寫，且 `revoke` 已存在）。代價是 `name` 變成可省略的位置參數、要自己檢查「二選一」（作法已寫）。
5. **要不要同時加 `list`？** 專案裡原本沒有任何方式能看到 agent token 的 id（`pat list` 只列 PAT；已核對 `cli.py` 與 `store.py` 沒有 agent 版）。沒有 id 就用不了 `--id`。**建議：加，且只列 agent token、不印值與雜湊。**
6. **`--id` 對 run token／PAT 的 id 怎麼處理？** **建議：拒絕並回 1（`no live agent token with id N`），不撤、不洩漏它其實是別種 token**（避免用此指令誤關進行中的 run）。
7. **已撤銷的 id 再撤一次？** **建議：回 1 並印同一句 `no live agent token`**（與 `pat revoke` 一致，不是「冪等成功」）。
8. **舊 token 的 `user` 欄顯示？** 沒有 user 的舊 token 印 `-`（`pat list` 的 label 用法一樣）。這正是維護者遇到的「舊桌機 token」情形，清單要看得出來。

### developer-agent 確認（2026-10-29）
裁決 1–8 全部照建議定案。補一條：裁決 2「沒有擁有者規則」維持現狀（token 管理只在伺服器終端機、操作者專用），backend 守則的跨使用者 TC 不適用，verifier 報告要寫明理由，不算 FAIL。B 級非畫面，verifier 通過＋CI 綠由 developer-agent 自合。

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
