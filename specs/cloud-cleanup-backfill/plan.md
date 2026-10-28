---
id: cloud-cleanup-backfill
title: 補提清理申請：對「清理功能上線前就成功」或「7 天申請已逾時」的 run，用終端機指令為它的擁有者重新建一張待確認申請（不是網頁按鈕、不刪任何東西）
tier: B
kinds: backend
lane: L-backfill
base: v3（本任務要等 cloud-cleanup-a..f 都合併後才能開；下列「origin/v3 事實」是今天的，「f 片」事實取自 `memory/dev-plans/cloud-cleanup-f.md`，開工第一步要用合併後的 origin/v3 核對一次）
source: cloud-cleanup-f.md 作法 3（「過去已經成功的 run 也不會被提」）、裁決 4（「逾時後不自動重提；是否補重新提出的入口列為給維護者的問題」）、不做（「不補提過去已成功的 run」）；cloud-cleanup.md 裁決 3（終端機路徑預設不做）
---

# cloud-cleanup-backfill

> 本任務補 cloud-cleanup 系列留下的兩個缺口：①清理上線前就 `succeeded` 的 run 永遠不會被提；②申請 7 天沒按就逾時，之後沒有第二次機會。做法是**一個終端機（維護者／管理者）指令**，不是網頁按鈕（維護者的決定；前端 session 不需動）。**指令只「建申請」，刪除仍然要擁有者本人在確認頁按送出，由代理執行**（`cloud-cleanup.md`「為什麼這樣切」第 1、2 點不變）。B 級（後端行為改變、無畫面）：verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
管理者在平台主機上執行 `abf-platform runs offer-cleanup --all`（或指定幾個 run 名），平台對每個符合條件的 run，重用 f 片的 `offer_cleanup` 建一張 `clean_work` 待確認申請；擁有者之後在網頁右欄「待處理」看到通知、點進確認頁按送出才會刪。對使用者的意義：nano4 的 `/work` 配額與 bucket 儲存費上，已經跑完的舊 run 也能收拾，不必等它們被重跑。

### 查證結果
今天（`origin/v3` @ 2385f97）：
- 終端機已有 `runs` 指令群，目前只有 `assign`：`platform/abf_platform/cli.py:636-646`（`rn = sub.add_parser("runs", …)`，`ra = rsub.add_parser("assign", …)`，`ra.set_defaults(func=cmd_runs_assign)`）。`cmd_runs_assign` 在 `cli.py:448-486`，是「只改一欄、只在終端機」的先例；它用 `store.user_by_name(store.default_tokens_path(), name)`（`store.py:805`）解析 `--user`。
- 列 run：`platform/abf_platform/status.py:79` `list_runs(index_path, at=None, names=None)`（每個 view 有 `"status"`，`status.py:55`）、`:104` `find_run(index_path, run_name)`；hand-off 紀錄：`jobs.latest_launch(con, run_name)`（`jobs.py:296`），擁有者的 run 名集合 `jobs.owned_run_names(state_path, user_id)`（`jobs.py:280`）；唯讀開庫 `store.open_readonly`（`store.py:622`）。
- 指令列的守門測試（新指令不得踩到）：`platform/tests/test_launch_platform.py:722-742`（`test_launch_platform.py` 的 TC-061：整棵 parser 的選項與子指令名字集合不得含 `retry confirm yes y force assume-yes no-confirm`；唯一例外 `runs assign --force`）；`platform/tests/test_confirm_page.py:319-333`（TC-G02：任何非測試的 `.py` 不得有 `--yes|--force|--no-confirm|--assume-yes` 或 `ABF_…(DEV|YES|SKIP|NOCONFIRM|AUTO_CONFIRM|ASSUME)`）。
- 終端機測試樣板：`platform/tests/test_owner_gaps.py:331-360`（用 `d.w.ip.run("runs", "assign", "r-old", "--user", "alice")` 回 `(rc, out)`；夾具 `d.add_run(name, user_id)`、`d.add_launch_row` 在 `platform/tests/owner_harness.py:117,131`；`ip.run` 在 `platform/tests/station_harness.py:649`）。
- `ADOPTING = ("serve", "web", "mcp", "ce")`（`cli.py:649`）：`runs` 不在其中，本指令也**不**加進去（不替沒有擁有者的 run 認領）。

f 片合併後（取自 `cloud-cleanup-f.md`，開工先核對函式名與回傳形狀；對不上就 BLOCKED 回報，不要猜）：
- `actions.offer_cleanup(platform_path, index_path, run_name, *, clock=time.time)`：只對 `succeeded`、有擁有者、有 Slurm／主控程序編號、`work_cleaned_at` 空、`prepare_clean` 通過的 run 建 pending；其他靜靜跳過回 `{"offered": False, "reason": …}`，不丟例外（f 作法 2）。
- b 片：申請 7 天有效、不佔 10 張名額、上限自成一格 50（`cloud-cleanup-b.md` 裁決 5）；`create_pending` 依 sha 重用未逾時的同內容申請，所以重複呼叫不會多建（f 作法 2.4）。

## 維護者原話（verifier 出題用）
- 本任務來自他的指示：「cloud-cleanup-backfill（對清理上線前就成功的 run，手動要求清理）——設計成 CLI／MCP 動作，不是網頁按鈕」（developer-agent 派工單，2026-10-24）→ T1–T4、T14：只有終端機入口、沒有新網頁路由。
- 「**跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪**」（`PLAN-abf-v3-replan-2026-10.md` 裁示 16，第 58 行）→ T5、T6：指令永不刪、永不替人按「是」。
- 「直接 `scancel`，以及刪改叢集端 `rawdata`／`results`／`analysis`，一律擋住」（`CLAUDE.md` §3.4）→ T6：指令不啟動任何程式、不碰路徑。
- 憲法 6.0.0／ADR 0006「每個寫入要本人答應」→ T5（指令之後 `jobs` 表沒有 `clean_work` 工作）。

## 範圍：檔案（8 個以內）
- `platform/abf_platform/cli.py`：`runs` 群加子指令 `offer-cleanup`（`cmd_runs_offer_cleanup`）。
- `platform/abf_platform/actions/__init__.py`：新增 `offer_cleanups(platform_path, index_path, *, run_names=None, user_id=None, dry_run=False, clock=time.time)`；並在 f 片的 `offer_cleanup` 加關鍵字 `dry_run=False`（預設行為位元不變）。
- `platform/tests/test_cleanup_backfill.py`（新；檔首 `# Nothing existing: …` ≥15 字，TC-070）。
- `docs/OPERATIONS.md`：Admin 節（第 5 個 `##`）加一小段指令說明（只能用真的存在的 `abf-platform` 指令名與存在的 repo 路徑，`tests/operations_doc_test.sh` 會查；六個 `##` 標題不增不減）。
- `docs/TESTING.md`：加「cloud-cleanup-backfill」小節（手動驗收）。
- `specs/cloud-cleanup-backfill/ledger.md`。
- **不准動**：`store.py`、`confirm.py`、`jobs.py`、`receiver.py`、`web.py`、`web_board.py`、`mcp_server.py`、`guidance.py`、`actions/chat_tools.py`、`abf_station/*`、`abf_launch/*`、`test_actions_layer.py`、`test_web_parity.py` 的既有斷言（除「必須更新」）、`docs/PLATFORM.md`（別的任務在動）。

## 作法
1. **指令**：`abf-platform runs offer-cleanup [RUN ...] [--all] [--user NAME] [--list]`。`RUN ...` 與 `--all` 恰給一個（都沒給或都給 → 白話拒絕、exit 1、什麼都不建）。`--user NAME` 是篩選器：與 `--all` 並用時只處理該使用者的 run；與 RUN 並用時，不屬於他的 run 回 skipped。`--list` 只列「會提」的清單、不建任何申請。選項名不得是 TC-061／TC-G02 的禁字。`allow_abbrev=False`（同 `runs assign`）。
2. **動作 `actions.offer_cleanups`**：`run_names=None` ＝ 對 `status.list_runs(index_path)` 裡 `status == "succeeded"` 的每個 run；否則對給的名字（去重、保序）。逐一呼叫 `offer_cleanup(…, dry_run=dry_run)`；`user_id` 給了就先用 hand-off 紀錄的 `user_id` 篩，不符回 `{"offered": False, "reason": "not that user's run"}`。回傳：`{"ok": True, "results": [{"run_name": str, "offered": bool, "reason": str|None, "owner": str|None}], "offered": N, "skipped": M}`；`owner` 是使用者名字（查不到或沒有擁有者為 `None`）。**絕不丟例外**（任何一個 run 出錯只影響它那一行）；不存在的 RUN 名回 `{"run_name": x, "offered": False, "reason": "no such run"}`。
3. **dry_run**：`offer_cleanup(…, dry_run=True)` 做完全相同的資格檢查，但**不呼叫 `create_pending`**；回 `{"offered": False, "would_offer": True|False, "reason": …}`。`dry_run=False` 時回傳形狀與 f 片一字不差（不多 `would_offer` 鍵）。
4. **輸出（每個 run 一行，最後一行總結）**：`<run>: 已提出申請，請 <owner> 登入網頁在確認頁按送出 (offered; <owner> presses send on the confirmation page)` ／ `<run>: 略過：<reason>` ／（`--list`）`<run>: 會提出申請 (would offer)`；總結 `已提出 N 張、略過 M 個 (offered N, skipped M)`。exit 0＝指令跑完（即使全部略過）；exit 1＝輸入錯（沒給 RUN／`--all`、`--user` 不存在、兩者都給）。reason 逐字照 f 片回傳顯示，不翻譯、不改寫；輸出不含路徑堆疊、SQL、權杖。
5. **逾時後重提**：不新增邏輯——f 片的 `offer_cleanup` 在舊申請逾時後會建新的（`create_pending` 只重用未逾時的）。本任務只負責用測試證明（T10）。
6. **永不確認、永不刪**：指令與動作的原始碼不得 import 或呼叫 `confirm.approve`、`jobs.enqueue_*`、`subprocess`、`os.system`；不寫 `work_cleaned_at`。測試用原始碼掃描釘住（T6）。
7. **沒有擁有者的 run**：略過，reason 照 f（`user_id` 為空）。**不**提供 `--as USER` 之類替人認領的旗標（那是 `runs assign` 的事）。
8. **migration**：不需要（沒有動資料表或 JSON 欄位內容；只用 a 片已有的欄位與 b 片已有的申請種類）。

## 失敗先行測試（`platform/tests/test_cleanup_backfill.py`；用 `owner_harness` 夾具與 `ip.run`，假的 `offer_cleanup` 用 monkeypatch）
| # | 情境 | 期望 |
|---|---|---|
| T1 | 3 個 run：兩個 `succeeded`（甲有擁有者、乙有擁有者）、一個 `failed`；`runs offer-cleanup --all` | exit 0；`confirmations` 表多 2 張 `kind='clean_work'` 且 `pending`；輸出 3 行＋總結「已提出 2 張、略過 1 個」，failed 那行含 reason |
| T2 | `runs offer-cleanup 甲` | 只多 1 張；乙沒動 |
| T3 | 沒給 RUN 也沒 `--all`；同時給兩者；`--user nobody` | 各 exit 1、白話訊息、`confirmations` 列數不變 |
| T4 | `--all --user alice` | 只處理 alice 的 run；bob 的不出現在 results 的 offered |
| T5 | 任一情境後 | `jobs` 表 `clean_work` 為 0 列；`launches.work_cleaned_at` 全空；沒有 `destructive.log` 記錄（夾具 `FakeSite(destructive_log=True)`，`test_launch_e2e.py` 樣板） |
| T6 | 原始碼掃描（cli.py 的新函式與 `offer_cleanups`） | 不含 `approve`、`enqueue`、`subprocess`、`os.system`；`TERMINAL`／`PAGE` 通道字樣不新增 |
| T7 | `--list` | 輸出「會提出申請」；`confirmations` 列數不變 |
| T8 | 同一指令連跑兩次 | 第二次不多建（依 sha 重用）；總結顯示 offered 數與第一次相同或 0，但表內不重複 |
| T9 | `offer_cleanup` 被換成回 `{"offered": False, "reason": "quota full"}` 的假貨 | 該行逐字顯示 `quota full`；其他 run 仍處理 |
| T10 | 假時鐘：第一次提出後 8 天，再 `offer_cleanups(…, clock=+8d)` | 舊的已逾時，建 1 張新的（共 2 張 `clean_work` 列，只有 1 張未逾時） |
| T11 | `offer_cleanup` 丟例外（monkeypatch） | `offer_cleanups` 不丟出，該行 `offered=False` 並有 reason；其他 run 繼續 |
| T12 | `offer_cleanup(…, dry_run=True)` | `confirmations` 不增；回 `would_offer` 鍵；`dry_run=False` 的回傳鍵集合與 f 片相同 |
| T13 | 不存在的 RUN 名 | 該行 `no such run`，exit 0 |
| T14 | 整棵 parser 掃一遍（比照 TC-061）／`web.py` 路由表 | 新增的名字只有 `offer-cleanup`、`all`、`list`；網頁路由表與 base 逐字相同 |
| T15 | 沒有擁有者的 run（`add_run(name, None)`） | skipped，reason 為 f 的「沒有擁有者」；沒有建申請 |

**現在會紅**：全部（指令與動作都不存在）。T14 的 parser 部分現在綠，但 `offer-cleanup` 不在其中時其餘紅。
**必須更新的既有斷言**：預計無。executor 動手前跑 `git grep -n "offer_cleanup" -- platform/tests`，若 `test_actions_layer.py`／`test_web_parity.py` 對 `actions` 的公開函式有列舉而新函式讓它變紅，在 PR 說明列出「以前／以後／理由」，只加這一個名字。
**允許新增的名字**：`runs offer-cleanup` 在 TC-061 的集合內不違規；不要動 TC-061 本身。

## 完成標準（done when）
- T1–T15 全綠；`bash tests/run_all.sh`（WSL）綠，特別是 `tests/operations_doc_test.sh`、`test_launch_platform.py`、`test_confirm_page.py`、`test_scope.py`（它的 TC-061／TC-071 掃 `abf_platform/` 原始碼）。
- `git diff --name-only` 只含上列 6 個檔；新增測試 ≤ 30 條；既有測試沒有被刪、跳過或放寬。
- 手動（維護者，nano4 實機，寫進 TESTING.md）：找一個 f 片上線前就成功的 run，執行 `abf-platform runs offer-cleanup <run> --list` → 再不加 `--list` 執行 → 以該 run 擁有者登入網頁，確認頁出現清理申請（文字由 e 片負責）→ 不按，確認 nano4 上 `work` 仍在。

## 環境事實
- 全套測試在 WSL／Linux 跑；worktree 不可在同步磁碟（repo `CLAUDE.md`「For the executor and verifier」）。
- 平台程式碼裡（`abf_platform/`、`abf_launch/`）一律寫「代理／agent」，不得出現 `test_scope.py` 的 TC-061 禁用字（`ssh`、`sbatch`、`scancel`、`tw `、`station`、`socket`…，掃 `abf_platform/` 全部原始碼）；輸出文字也算原始碼。
- 本任務在 f 片之前**沒有可呼叫的 `offer_cleanup`**，所以不能提前開工；`after:` 必須含 `cloud-cleanup-f`。

## 不做
- 不做網頁按鈕、不做 MCP 工具（MCP 工具會讓 `test_mcp.py`、`test_pat.py:383`、`test_oauth_mcp.py:329` 等十幾個釘著工具清單的測試連動，且 AI 不該能替人「要求清理」，見 `cloud-cleanup.md` 裁決 3）。
- 不自動、不排程、不在 `serve` 啟動時補提（平台沒有常駐程式，憲法原則 2）。
- 不改申請有效期、不改 50 張上限、不替沒有擁有者的 run 認領、不刪任何東西、不動 Google Batch／Slurm 代理端。

## 裁決
1. **只做終端機，不做 MCP 工具**：理由見「不做」第一條。若維護者要 AI 也能問「哪些 run 可以清」，另開唯讀任務（只列、不建）。
2. **`dry_run` 加在 f 片的 `offer_cleanup` 而不是在本任務重算資格**：重算會有第二份「什麼算可提」的邏輯，日後兩份不同步。
3. **`--user` 是篩選器不是身分**：終端機是管理者的（`abf_launch/cli.py:62-76` `_account` 的註解同一立場）；申請的擁有者永遠是 hand-off 紀錄的 `user_id`。
4. **問維護者（不擋工）**：是否希望指令預設 `--list`（要明說 `--apply` 才建）？預設選「直接建、`--list` 預覽」，因為建申請無害（不按就什麼都不刪）。

## 裁決（2026-10-25，developer-agent）
1. 只做終端機指令，不做 MCP 工具與網頁按鈕：接受。
2. 預設**只預覽**（等同 `--list`）；要真的建立確認請求必須加 `--yes`。`--all` 不加 `--yes` 一律只預覽。刪除仍要擁有者在確認頁按「是」。
3. 開工前核對 cloud-cleanup-f 合併後 `offer_cleanup` 的簽名；不同就 BLOCKED。

## 裁決（2026-10-27，developer-agent；派工前預檢 plan-collision-check 的結果，優先於上面兩段裁決）
4. **不用 `--yes`，改用 `--apply`**：`platform/tests/test_confirm_page.py` TC-G02 禁止任何非測試 `.py` 出現 `--yes`，`test_launch_platform.py` TC-061 禁止 parser 有 `yes`／`y`／`confirm`／`force` 等名字。所以：預設只預覽；要真的建申請必須加 `--apply`（`--all` 不加 `--apply` 一律只預覽）。上面「裁決（2026-10-25）」第 2 條的 `--yes` 一律讀成 `--apply`。
5. **`offer_cleanup` 加 `dry_run` 會撞簽名釘**：`platform/tests/test_cleanup_offer.py` 第 393 行 `assert list(inspect.signature(actions.offer_cleanup).parameters) == ["platform_path", "index_path", "run_name", "clock"]`。准許把這一條（只這一條）更新成在結尾加 `"dry_run"`，列入「必須更新的既有斷言」，PR 說明寫「以前／以後／理由：backfill 預覽要重用同一份資格判斷」。`dry_run` 必須是關鍵字參數、預設 False、預設行為位元不變。
6. **`actions` 模組的 docstring 不准提 `offer_cleanup`**：同檔第 394 行 `assert "offer_cleanup" not in actions.__doc__`。`offer_cleanups` 的說明寫在函式自己的 docstring，不要改 `actions/__init__.py` 最上面的模組說明。
7. **`offer_cleanups` 是新的公開函式，要登記到 `test_web_parity.py` 的 `INTERNAL` 表**（跟 f 片 `offer_cleanup` 的做法一樣：只有終端機用、沒有網頁路由也沒有 MCP 工具）。只加這一個名字，不動其他表、不放寬任何檢查；列入「必須更新的既有斷言」。
8. 不准動 `receiver.py`（`test_cleanup_offer.py` 第 579 行數 `complete()` 裡 `offer_cleanup` 恰好一次）。

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
