---
id: owner-binding
title: 代理與計算環境綁定擁有者：把 #116 剩下的缺口補齊（沒有使用者的代理 token、沒有擁有者的代理），並加一支防止以後漏掉的守衛測試
tier: B
kinds: backend
lane: L12-owner
branch: feat/owner-binding
base: v3（`origin/v3` @ fdfcc00；查證日 2026-10-28；所有行號與名字都取自該版本）
source: GitHub issue zhshie/agentic-bioflow_v2 #116「v3: bind station agents and compute environments to their owner (one-role model, ADR 0009)」；已合併的 PR #123（spec 116）、PR #125（spec 116b）；`specs/116-owner-binding/{plan,ledger}.md`、`specs/116b-owner-gaps/{plan,ledger}.md`
---

# owner-binding

> 本檔由 developer-agent 的子 agent 起草（2026-10-28），**待 developer-agent 裁決「不確定的地方」後才派工**。
> **先講結論：#116 的主體已經在 v3 上了**（PR #123 與 #125，verifier 74 PASS／0 FAIL）。本任務**只補還漏的三個縫**，不重做擁有者機制。issue 至今仍開著，只是沒人收尾；本任務合併後該 issue 可以關。
> 車道 L12-owner（新車道，只含本任務）。B 級（理由見「環境事實」最後一條）→ verifier 通過＋CI 綠由 developer-agent 自合，並附一段給管理者的搬遷說明。

## 目標
讓「每個代理、每個計算環境都有且只有一個擁有者，別人看不到也用不到」**不再靠管理者記得加 `--user`**：沒指名使用者的代理 token 不能再服務一個已經有擁有者的代理；擁有者已定的環境，它的代理不會因為「還沒被認領」而靜靜地變成誰都用不了；以及加一支守衛測試，以後新增的動作（例如 `aws-launch`）若忘了帶呼叫者就會當場紅。

對使用者的意義：現在若管理者建了「擁有者是 A」的環境，但代理 token 沒指名使用者，A 透過網頁／MCP 送出時只會看到「找不到」，而且沒有任何地方告訴任何人為什麼。這一片讓那種情況要嘛一開始就被擋下、要嘛自動接好。

## 現況：issue 的每一條，v3 上已經有什麼（執行者不要重做）
issue 的三條，逐條對照：
1. 「`agents` and `compute_envs` record the owning user; agent tokens are issued for a user.」
   - 已有：欄位 `compute_envs.owner_user_id`、`agents.owner_user_id`、`launches.user_id`（`store.py` `_add_owner_columns`）；`agent-token new --user`（`cli.py:92` `cmd_agent_token_new`）；`store.create_token` 允許 `kind="agent"` 帶 `user_id`；`store.lookup_token`（:980）回傳 `user_id`；`agents.register(owner_user_id=)`（`agents.py:71`）把空的擁有者填成第一個帶使用者的 token 的使用者，擁有者不同則 `OwnerMismatch` → hello／poll／result 回 403。
   - **缺的**：`--user` 是選填（「A token without a user neither takes nor refuses an owner」，`agents.py:68-69` 與 `specs/116-owner-binding/ledger.md` 的 Question 5）。
2. 「Every action lists and uses only the caller's own agents and compute environments (MCP, HTTP and CLI entries alike).」
   - 已有：`actions/__init__.py` 的 `list_compute_envs`／`get_compute_env`／`list_agents`（:216-229）、`list_runs`／`get_run`／`estimate_su`／`my_usage`／`run_outputs`／`read_task_log`／`forget`／`launch_prefill`／`list_used_pipelines`／`list_site_files` 全帶 `caller`；`jobs._target`（`jobs.py:95-107`）與 `enqueue_confirmed` 在佇列端再擋一次；`build.primary_environment`／`prepare_launch` 只在呼叫者自己的環境裡選；`set_primary` 每個擁有者各一個；`datasets.py:120`、`pipelines.py` 也傳 `owner`。MCP 工具、網頁（`web.py:556,723` 走 `actions.list_compute_envs(caller=…)`）、HTTP 都走同一組動作。終端機 `abf-platform ...` 刻意無呼叫者、看全部（已寫在 `docs/PLATFORM.md` 的「Whose it is (spec 116)」「The honest boundary」）。
   - **缺的**：沒有任何東西保證**以後新增**的動作也記得帶呼叫者。這條是 `aws-launch` 這類即將進來的新程式碼最容易漏的地方。
3. 「Test case first: one user's agents and compute environments are not visible or usable by another user.」
   - 已有：`platform/tests/test_owner_binding.py`（tc001–tc068＋tc_ls_50/51）、`test_owner_gaps.py`、`test_station_owner.py`、`owner_harness.py`。這條**完全達成，不再加**。
4. 舊資料：`store.assign_orphans`（`store.py:1284`）「只有一個使用者時他接手全部沒有擁有者的列；兩個以上什麼都不接」。
   - **缺的**：兩個以上使用者時，**擁有者已定的環境所用的代理仍可能是無主的**，而 `jobs._target:105-108` 對「代理無主」一律拒絕（fail-closed），所以那個環境對它的擁有者也是死的，且沒有訊息。

## 維護者原話（verifier 出題用）
只引 issue 本文與 ADR 0009 的字句，逐字：
- 「`agents` and `compute_envs` record the owning user; agent tokens are issued for a user.」（issue #116，Scope 第 1 條）→ 新發的代理 token 必須指名使用者；沒指名就不是「issued for a user」。
- 「Every action lists and uses only the caller's own agents and compute environments (MCP, HTTP and CLI entries alike).」（issue #116，Scope 第 2 條）→ 守衛測試要涵蓋 MCP／HTTP／網頁共用的動作層；以後新動作漏帶呼叫者要紅。
- 「Test case first: one user's agents and compute environments are not visible or usable by another user.」（issue #116，Scope 第 3 條）→ 跨使用者案例要先寫、先紅；每條缺口至少一對「A 看得到／用得到、B 看不到／用不到」。
- 「ADR 0009 postponed 010 but kept "each user sees only their own runs" (point 7).」（issue #116 內文）→ 一個使用者的環境與代理，對另一個使用者的回答必須和「不存在」一樣（沿用 116 的「找不到」措辭，不新增能讓人探測存在與否的訊息）。
- 「The ownership part of 010 is still needed under one role.」（issue #116 內文）→ 不做角色、不做實驗室內共享（ADR 0009 postponed 010；見「不做」）。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/agents.py`（只改 `register`:71；`OwnerMismatch` 沿用）
- `platform/abf_platform/compute_envs.py`（只動 `_agent_owner_problem`:586 附近與 `create`:~630／`update`:~655 認領無主代理的那幾行；新增小函式 `_claim_agent`）
- `platform/abf_platform/store.py`（只動 `assign_orphans`:1284：多一步「無主代理由『用它的環境全屬同一個擁有者』時接手」）
- `platform/abf_platform/cli.py`（只動 `cmd_agent_token_new`:92 與 `agent-token new` 的 parser 說明:683-688；**不碰** docstring 第 2 行、`user` 群組、`cmd_ce_*`、`_owner_id`）
- `platform/tests/test_owner_tokens.py`（新；檔首前 40 行要有 `# Nothing existing: <理由，≥15 字>`，`test_scope.py` TC-070）
- `platform/tests/test_owner_guard.py`（新；同上檔首要求）
- `platform/tests/test_owner_binding.py`（**只准**依「必須更新的既有斷言」列的幾處動）
- `platform/tests/station_harness.py:409`、`platform/tests/test_station_envs.py:579`、`platform/tests/test_station_platform.py:139-140`（**僅當**執行者先跑全套時它們因新規則紅才動，**只准**在 `agent-token new` 的呼叫後面加 `--user <名字>`，其餘不動；沒紅就不碰）
- `docs/PLATFORM.md`（「Whose it is (spec 116)」那節 Environments and agents 一條；:147 的範例命令加 `--user`）
- `docs/OPERATIONS.md`（:114 那一列的 `[--user U]` 去掉方括號並改說明）
- `docs/TESTING.md`（新增「Owner binding follow-up (owner-binding)」小節，含管理者搬遷的手動步驟）
- `CHANGELOG.md`
- `specs/owner-binding/ledger.md`（新，executor 進度帳本）

**不准動（硬規則）**：
- 網頁介面檔：`platform/abf_platform/web.py`、`web_board.py`、`web_*.py`、`static/*`、`DESIGN.md`、`PRODUCT.md`、`platform/tests/test_web_*`（前端 session 擁有；守衛測試只**讀**這些檔，不改）。若網頁層需要改字或加畫面，一律列進下面「後續任務」，不在本片做。
- `platform/abf_platform/releases.py`。
- `jobs.py`、`launch.py`、`aws_launch.py`、`cloud_cost.py`、`su.py`、`abf_launch/*`、`abf_station/*`（`aws-launch` 車道擁有 `jobs.py`；擁有者檢查本來就在 `jobs._target`，不需改）。
- 閘門檔：`spec.md`、`test-case*.md`、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`.github/`、`platform/pyproject.toml`、`docs/ONBOARDING.md`（`test_onboarding_doc.py:140` 已釘住 `agent-token new <agent-name> --user <name>`，本片只是讓它變成唯一合法寫法）。

## 與正在跑的兩條車道的檔案重疊（給 developer-agent 排序用）
| 車道 | 重疊的檔 | 重疊的位置 | 衝突風險 |
|---|---|---|---|
| `aws-launch`（L2-platform-ce） | `platform/abf_platform/compute_envs.py` | 它改 `PLATFORM_HOST_TYPES`／`CHECK_ONLY_TYPES`、`:450` 分派、`snapshot`:691；本片只動 `_agent_owner_problem`:586 與 `create`/`update` 裡認領代理的幾行 | 低（不同函式，文字上不相鄰）；仍是同一檔，後合併的要 rebase |
| `aws-launch` | `docs/PLATFORM.md`、`docs/TESTING.md` | 它加「Launching on AWS Batch」；本片加「Whose it is」一條與一個 TESTING 小節 | 低（不同小節） |
| `aws-launch` | `jobs.py`、`launch.py`、新 `aws_launch.py` | **本片不碰**。但守衛測試會掃它新增的呼叫（見 `test_owner_guard.py`）；若它在 `abf_launch/build.py` 新增 `is_aws` 之類呼叫 `compute_envs.get(state, ce_name)`（無擁有者），守衛的白名單已含 `is_*` 前綴，不會紅 | 低 |
| `account-welcome-cli`（L11-onboarding） | `platform/abf_platform/cli.py` | 它動第 2 行 docstring、`user` 群組（`cmd_user_welcome`、`cli.py:696-699` 附近）；本片動 `cmd_agent_token_new`:92 與 parser:683-688 | 低到中（同檔不同區塊，沒有同一行；後合併者 rebase） |
| `account-welcome-cli` | `docs/*` | 它明說不動 `PLATFORM.md`／`TESTING.md`／`OPERATIONS.md`；只改 `docs/ONBOARDING.md`（本片不碰） | 無 |

建議順序：`aws-launch` 與 `account-welcome-cli` 先合，本片最後從更新後的 v3 開分支（守衛測試因此一次掃到 aws-launch 的新程式碼，而不是之後才發現）。若 developer-agent 要平行跑，本片可以先做 US1（只動 `agents.py`、`cli.py` 小段、`store.py`），把守衛（US3）留到最後。

## 作法
### US1：新發的代理 token 一定要指名使用者
1. `abf-platform agent-token new NAME` 不給 `--user`：**平台上已有任何使用者時拒絕**（訊息：`rejected: say whose agent this is with --user NAME (請用 --user 名字 指定這個代理是誰的)`，rc 1，不建 token，不印任何東西像 token）。**平台上一個使用者都沒有時照舊允許**（全新安裝與測試環境不受影響；與 116 的 D7「終端機送出：有使用者就必須 `--user`，沒有使用者就留空」同一條規則）。
2. `--user B` 但代理 `NAME` 已有擁有者 A（`agents` 表有列且 `owner_user_id` 不是 B）→ 發 token 時就拒絕，訊息講白「這個代理屬於另一位使用者」，不透露 A 是誰。理由：現在要等代理 hello 時才 403，管理者白發一支永遠不能用的 token。
3. `store.create_token` 的簽章與其對 `kind="agent"` 的規則**不改**（`user_id` 仍可為 None）——「必須指名」只在 CLI 這一道，避免動 store 的契約與測試（`test_pat.py` tca12 釘住它）。
4. **`agents.register`**：`owner_user_id is None`（沒指名使用者的舊 token）且該代理列的 `owner_user_id` 不是 NULL → 視同 `OwnerMismatch`（回 403，同一句 `This agent belongs to another user`）。沒指名使用者的 token 對**無主**代理仍可 hello／poll／result（舊部署相容，代理維持無主，與現在相同）。
   - 這是「失敗即拒絕」：未知擁有者 → 拒絕。副作用：舊部署裡「已被認領的代理＋一支舊的無使用者 token」會開始被拒；管理者需 `agent-token revoke NAME` 後以 `--user` 重發（見「搬遷」）。

### US2：擁有者已定的環境，它的代理不能是無主的
5. `compute_envs.create` 與 `update` 在 `_agent_owner_problem`（:586）之後，若環境有 `owner_user_id=O` 且 `agents` 表已有該代理的列、且列的 `owner_user_id IS NULL` → **同一個交易裡**把代理的擁有者設為 O（新函式 `_claim_agent(con, agent, owner)`；已有別的擁有者的代理仍照舊被 `_agent_owner_problem` 拒絕）。代理的列還不存在（還沒 hello 過）→ 什麼都不做，等第一個帶使用者的 token hello 時由 `register` 填（既有行為）。
6. `ce create`／`ce update` 若結果是「環境有擁有者、代理的列存在、代理仍無主」不可能再出現（步驟 5 之後）；若**環境無擁有者**（沒有任何使用者時建的），不認領，維持現狀。
7. **搬遷（舊資料）**：`store.assign_orphans` 的「兩個以上使用者什麼都不接」之後，多一步（`len(users) >= 1` 都做，冪等）：對每個 `owner_user_id IS NULL` 的代理，若用它的環境（`compute_envs.agent = 該代理`）**至少一個、且擁有者都不是 NULL 並全相同**，把代理設成那位擁有者。有多個不同擁有者共用一個代理、或沒有任何環境用它的代理 → 不動。不新增欄位、不新增表 → **不需要 schema migration**，但這是一筆資料搬遷（寫在 `docs/TESTING.md`）。`rebuild` 仍然不開 `platform.db`／`tokens.db`（tc065 釘住）。`owners_assigned` 標記的語意不變。

### US3：守衛測試（防止以後漏）
8. `platform/tests/test_owner_guard.py`：用 `ast` 掃**這幾個檔**的所有呼叫：`abf_platform/actions/*.py`、`abf_platform/mcp_server.py`、`abf_platform/web*.py`（只讀）、`abf_platform/pipeline_launch.py`、`abf_launch/build.py`。對下列呼叫，要求有 `owner=`／`caller_user_id=`／`caller=` 關鍵字或對應的位置參數（只檢查**有帶**，不檢查值，因為 `None`＝終端機是合法值）：
   - `compute_envs.get`、`compute_envs.list_all`、`agents.list_agents`
   - `jobs.latest_pipeline_files`、`jobs.enqueue_listing`、`jobs.enqueue_task_log`、`jobs.enqueue_pipeline_files`、`jobs.check_target`
9. **白名單**（具名，每個附一句理由，寫在測試檔頂端）：`abf_launch/build.py` 的 `is_gcb`、`_same_environment`、`prepare_cancel`、`prepare_clean`（它們在已通過擁有者檢查的 run 之後讀環境；擁有者檢查在 `prepare_cancel`/`prepare_clean` 開頭的 `user_id` 比對與緊接的 `target_problem(..., owner)`），以及任何函式名以 `is_` 開頭的 build 輔助函式（`aws-launch` 會加 `is_aws`）。其餘一律不准無擁有者。`abf_platform/cli.py`、`abf_launch/cli.py`（終端機）、`cloud_cost.py`、`su.py`、`abf_station/*` **不掃**（終端機＝無呼叫者是設計；後兩者是已過擁有者檢查的內部查詢）。
10. 守衛本身要有「不是空轉」的證明：測試裡餵一小段合成原始碼（`compute_envs.get(p, name)` 無擁有者）給同一個偵測函式，斷言它被抓到；餵 `compute_envs.get(p, name, owner=1)` 與白名單函式，斷言通過。
11. MCP 對等性：列舉 `mcp_server.build_server(...)` 註冊的全部工具名，與 `actions` 裡有 `caller` 參數的公開函式清單，兩邊的差集必須是**明列的**（`launch`／`cancel` 等走確認管道的動作用 `confirmed_by`，不是 `caller`，列在白名單）；缺一邊就失敗。

### 文件
12. `docs/PLATFORM.md` 的「Environments and agents」那一條補三句：代理 token 在已有使用者的平台上必須 `--user`；沒指名使用者的舊 token 只能服務無主的代理；`ce create|update --owner` 會把無主的代理一併認領。:147 的範例命令加 `--user alice`。`docs/OPERATIONS.md:114` 那列改成 `abf-platform agent-token new <name> --user U`。`docs/TESTING.md` 新增小節，手動步驟（管理者）：①`abf-platform ce list`／`launches` 看有沒有擁有者是 `(none: local only)` 的代理或環境 ②對舊的無使用者 token 做 `agent-token revoke <name>` 後 `agent-token new <name> --user <名字>` 重發、把新 token 放進代理的 `--token-file` ③重啟 `serve`（讓 `assign_orphans` 跑）④以使用者 A 的 PAT 呼叫 MCP `list_agents`、B 的 PAT 呼叫同一個，確認各只看到自己的。

## 失敗先行測試（現在都會紅；全用既有夾具 `owner_harness.py`、`w`／`d`，不碰網路）
### `platform/tests/test_owner_tokens.py`
- `test_agent_token_new_without_user_is_refused_once_a_user_exists`：`w.user("alice")` 後 `agent-token new ag`（無 `--user`）→ rc≠0、輸出含 `--user`、`tokens` 表沒有新的 `kind='agent'` 列。
- `test_agent_token_new_without_user_is_allowed_when_there_is_no_user`：零使用者時 `agent-token new ag` → rc 0、印出以 `abf_` 開頭的 token（保住全新安裝與舊測試）。
- `test_agent_token_for_an_agent_owned_by_another_user_is_refused_at_issue`：A 的 token 讓 `ag` hello 後歸 A；`agent-token new ag --user bob` → rc≠0、不建 token、輸出**不含** `alice`。
- `test_a_token_with_no_user_cannot_serve_an_owned_agent`：`ag` 已歸 A；用 `create_token(kind="agent", agent_name="ag")`（無使用者，繞過 CLI）做 hello／poll／result → 三者都 403，回應 JSON 只有 `{"message": ...}`，與「別的使用者的 token」那個 403 的 key 集合相同；`agents` 列的擁有者仍是 A。
- `test_a_token_with_no_user_still_serves_an_agent_nobody_owns`：無主代理＋無使用者 token → hello 200、代理仍無主（舊部署相容，對照上一條）。
- `test_ce_create_with_an_owner_claims_an_agent_nobody_owns`：代理 `ag` 先以無使用者 token hello（無主）；`ce create --name c1 --agent ag --owner alice ...` → `_agent_owner(w, "ag")` 為 alice 的 id；A 的 PAT 透過 `actions.list_agents` 看得到 `ag`、`jobs._target` 對 A 的確認接受；B 看不到 `ag`，對 B 的確認回「找不到」措辭。
- `test_ce_update_owner_claims_an_agent_nobody_owns`：同上，走 `ce update --owner`。
- `test_ce_create_does_not_claim_an_agent_that_has_an_owner`：`ag` 歸 A；`ce create ... --agent ag --owner bob` → 仍被 `_agent_owner_problem` 拒絕（訊息與 tc031 相同），代理仍歸 A。
- `test_ce_create_with_no_owner_does_not_claim`：零使用者建環境，不認領；之後 `user add` 一位使用者並 `assign_orphans` → 該使用者接手（既有行為，不變）。
- `test_claiming_is_one_transaction`：`monkeypatch` 讓 `compute_envs` 寫環境列時丟例外 → 代理的擁有者仍是 NULL（不出現「代理已改、環境沒建」）。
- `test_assign_orphans_gives_an_unowned_agent_to_the_owner_of_its_environments`：兩位使用者；`ag` 無主，環境 `c1`、`c2` 都歸 A 且都用 `ag` → 跑 `assign_orphans` 後 `ag` 歸 A；第二次再跑不變（冪等）。
- `test_assign_orphans_leaves_an_agent_shared_by_two_owners_alone`：`c1` 歸 A、`c2` 歸 B 都用 `ag` → `ag` 仍無主。
- `test_assign_orphans_leaves_an_agent_with_no_environment_alone`：沒有環境用 `ag` → 仍無主。
- `test_assign_orphans_never_gives_an_agent_to_the_owner_of_an_ownerless_environment`：環境無擁有者 → 代理不動。
- `test_rebuild_still_never_opens_the_platform_or_the_tokens`：沿用 tc065 的做法，加一個「有無主代理」的資料庫，確認 `rebuild` 後 `platform.db`／`tokens.db` 位元組不變。
- 跨使用者（每條缺口一對）：`test_b_cannot_see_or_use_the_claimed_agent_or_environment`：認領後 B 的 `list_agents`、`list_compute_envs`、`get_compute_env`、`list_site_files`、`run_outputs` 全回與不存在相同的結果；B 的確認在 `enqueue_confirmed` 被拒，`jobs` 表列數不變。
- 錯誤訊息與日誌：`test_refusals_say_what_to_do_and_leak_no_token_or_other_user`：US1 的兩個拒絕訊息含下一步指令（`--user`）、不含 token 片段、不含別人的使用者名。

### `platform/tests/test_owner_guard.py`
- `test_every_read_and_queue_call_in_the_action_layer_names_its_caller`：掃第 8 條列的檔，沒有白名單外的無擁有者呼叫。
- `test_the_scanner_catches_a_call_without_an_owner`：合成原始碼，抓得到（第 10 條）。
- `test_the_scanner_lets_the_named_exceptions_through`：合成原始碼，`is_aws`、`is_gcb` 通過。
- `test_the_allow_list_has_no_dead_names`：白名單裡的每個函式名在 `build.py` 都真的存在（防止白名單腐爛）。
- `test_every_mcp_tool_has_an_action_and_every_caller_action_has_a_tool`：第 11 條的對等性；兩邊同時列舉。
- `test_the_web_files_are_only_read`：守衛只 `open(..., "r")`，且 `git diff --name-only` 不含 `web*.py`／`static/`（以 `Path.read_text` 的使用與本任務範圍檢查為準；實際的 diff 範圍由閱卷者看，見 README 通例）。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
- **預期 0 條必須改的斷言**：新規則只在「已有使用者」或「代理已有擁有者」時收緊；`test_owner_binding.py` 的 tc028（無使用者的 `create_token` 與 `--user` 兩種都用 `create_token`／帶 `--user` 的 CLI）、tc029、tc030（舊 token 先對無主代理 hello，之後兩個帶使用者的 token）都應仍綠。
- **執行者實作前先在 WSL 跑全套（`bash tests/run_all.sh`），把所有因新規則變紅的測試列在 ledger。** 可能的紅：`station_harness.py:409`、`test_station_envs.py:579`、`test_station_platform.py:139-140`（在已有使用者的平台上跑 `agent-token new <name>` 無 `--user`）。處理方式只有一種：在該呼叫加 `--user <該測試已建立的使用者>`，斷言一字不動，PR 說明記「設定更新，非斷言放寬」。超出此列（尤其是要改斷言內容、或要放寬任何拒絕）→ 回報 BLOCKED，不要自己改。
- 確認**不會**變紅、不准改：`test_pat.py` tca12（`create_token` 規則未動）、tcd14（工具本體不動）、`test_onboarding_doc.py:140`（文件已寫 `--user`）、`test_receiver*.py`（用無使用者 token 對無主代理，行為不變）、`test_station_owner.py`。

## 完成標準（done when）
- 自動：上面所有新測試綠；全套綠（WSL 跑 `tests/run_all.sh`）；`git diff --name-only` 只含「範圍：檔案」列出的檔；沒有任何一條既有拒絕被放寬；沒有新增 MCP 工具或網頁路由。
- 手動（管理者，`docs/TESTING.md` 新小節的四步，跑在一個已有兩位使用者的測試平台上）：舊的無使用者代理 token 重發之後，A 與 B 各自只看得到自己的代理與環境，彼此的 `get_compute_env` 回相同的「找不到」。
- 文件：`docs/PLATFORM.md`、`docs/OPERATIONS.md`、`docs/TESTING.md`、`CHANGELOG.md` 依上面更新。
- 完成後 issue #116 可關；PR 說明連結 #123、#125 並說明本片只補縫。

## 環境事實
- #116 的實作歷史：`git log origin/v3 --grep=owner`——`6a71b9f`（plan）、`d9f35d5`（RED）、`40fe50c`（GREEN）、`28702b4`／`7c4816b`（`ce update --owner` 要把代理一起交給新擁有者的修正）、`a9f6481`（PR #123 合併）、`f84975c`…`04af0df`（116b，PR #125 合併）。之後的功能（017b `actions/pipelines.py` 每個擁有者各自存放、009e resume／relaunch 的擁有者鏈、keep-submissions 的 `forget`）都已經沿用同一條規則。
- 擁有者規則的唯一實作位置：`compute_envs.get/list_all(owner=)`（:541、:558）、`agents.list_agents(owner=)`（`agents.py:40`）、`jobs._target`（`jobs.py:95-107`：環境擁有者不是呼叫者，或環境的代理有列且擁有者不是呼叫者 → 與「不存在」相同的 `_not_found`）、`jobs.owned_run_names`（:425）、`actions._caller_id`。
- `jobs._target` 的「代理無主＝拒絕」是設計（116 ledger Question 4：「the queue refuses a caller on an agent whose owner is not that caller, empty included」）；本片不放寬它，而是讓代理不再無主。
- `agents.register` 的目前語意只在 `agents.py:66-69` 的 docstring 與 `test_owner_binding.py::tc030`；`store.lookup_token`（`store.py:980`）只在 `kind='agent'` 時回 `user_id`。
- `docs/PLATFORM.md` 「Whose it is (spec 116)」第 561 行起；`docs/OPERATIONS.md:114` 現在寫「`agent-token new <name> [--user U]`」；`docs/ONBOARDING.md:64` 已寫 `--user <name>`。
- 沒有新資料欄位、沒有新表（**不需要 schema migration**），但有一筆**資料搬遷**：`assign_orphans` 的新一步（US2-7），在 `serve`／`mcp`／`web`／`ce`／`launch` 啟動時自動跑，冪等。
- **為什麼 B 級（不是 A）**：A 級＝只收緊、使用者看不出差別。這一片有兩處使用者或管理者看得到不同：①舊部署裡「無使用者 token＋已被認領的代理」會開始 403，管理者要重發 token；②擁有者已定但代理無主的環境，擁有者從此能用（之前是靜默的「找不到」）。沒有任何拒絕被放寬，沒有新的確認管道。

## 不做
- 不做角色、實驗室內共享、多人共用一個環境（ADR 0009 postponed 010；「The ownership part of 010 is still needed under one role」只要求一人一份）。
- 不做遠端站台的每人資料夾（009h）、OAuth（009i，已合併，不動）。
- 不改任何確認管道（誰能說 yes）；擁有者檢查是收窄可及範圍，不是確認。
- 不讓 `store.create_token` 強制 `user_id`（只在 CLI 強制；store 契約與 `test_pat.py` 不動）。
- 不新增 MCP 工具、網頁路由或畫面；不改 `hello` 回傳；不改 `web*.py`／`static/*`。
- 不改終端機的「看全部」行為（`ce list`、`ce show`、`launches` 仍無呼叫者）。
- 不替 `aws-launch` 預先改 `jobs.py`；守衛測試只掃，不改它的程式。

## 後續任務（不在本片，交給對應車道／session）
1. 網頁層（前端 session）：目前代理被拒時網頁只顯示「找不到」；可在設定頁加「這個環境的代理還沒有擁有者」的提示（資料來自 `ce list` 同款的擁有者欄位，需要一個新的唯讀動作，不是本片）。
2. 是否把 `agent-token new` 的「必須 `--user`」下放到 `store.create_token`（改 `test_pat.py` tca12）——等舊部署都重發完 token 後再議。
3. `aws-launch` 合併後，確認它新增的動作是否要補進守衛的呼叫清單（若它新增 `enqueue_*` 之類）。

## 不確定的地方（待 developer-agent 裁決；括號內是我的預設）
1. **issue 要不要直接關**：#116 的主體早在 #123／#125 合併，issue 仍開著。（預設：本片只補縫，合併後關 issue，PR 說明寫清楚；若你認為連這三個縫都不值得做，可以直接關 issue、本計畫作廢。）
2. **US1-4 是否過嚴**：沒指名使用者的舊 token 對**已有擁有者**的代理一律 403，會讓舊部署需要重發 token。替代：只在 hello 時印警告、不拒絕（較寬，與 116 當時「optional」的決定一致，但留下「無使用者 token 可冒充已擁有的代理」的洞）。（預設：拒絕，理由＝原則「unknown owner means refuse」，且 token 本來就綁死代理名字，冒充面不大、重發成本低。）
3. **US2 認領是自動還是只警告**：`ce create|update --owner O` 時自動把無主代理設成 O。替代：只在輸出印警告「這個環境的代理無主，擁有者無法透過網頁使用，請重發 token」，不改資料。（預設：自動認領；管理者在終端機明說 `--owner` 就是這個意思，且同一交易、可還原。）
4. **搬遷步驟（US2-7）要不要進 `assign_orphans`**：它在每次啟動都跑，會讓舊部署的行為悄悄改變。替代：做成一個明確的終端機指令 `abf-platform agent adopt`（要加 parser，多動 `cli.py`，與 `account-welcome-cli` 的重疊面變大）。（預設：進 `assign_orphans`，因為 116 的搬遷本來就在那裡，且只在「用它的環境都屬同一人」時才動，沒有歧義。）
5. **守衛測試的範圍**：只掃動作層與 build.py，不掃 `cloud_cost.py`／`su.py`（它們在已通過擁有者檢查的 run 之後讀環境）。若你要更嚴，可把它們也納入並白名單具名；代價是 `aws-launch` 動它們時可能紅。（預設：不掃。）
6. **終端機 `agent-token new` 在零使用者平台上仍允許不指名**（沿 116 D7）。替代：永遠必須。（預設：沿用零使用者允許，否則全新安裝要先 `user add` 才能發代理 token，會動到 `docs/INSTALL.md` 的順序，而它有 `install_doc_test.sh` 釘住。）
7. **verifier 的對等性案例（US3-11）的工具清單**：`launch`／`cancel`／`resume`／`relaunch`／`forget` 走確認管道（`confirmed_by`），我把它們放進白名單而不要求 `caller`；請確認這個分法正確。（預設：如此。）

## 裁決


1. 要做三個縫；issue #116 合併後**不由執行者關**，關 issue 由 developer-agent 問維護者。
2. 沒指名使用者的舊 token 對已有擁有者的代理一律拒絕（403）。理由：unknown owner means refuse。合併時 developer-agent 會把「舊 token 需重發」寫進每日清單。
3. `ce create|update --owner O` 在同一交易裡自動認領無主代理。
4. 搬遷放進 `store.assign_orphans`，不新增 `agent adopt` 指令。
5. 守衛測試不掃 `cloud_cost.py`、`su.py`。
6. 零使用者的平台上，`agent-token new` 仍允許不指名使用者（沿 116 D7；不動 INSTALL.md）。
7. launch／cancel／resume／relaunch／forget 走確認管道，列入守衛白名單、不要求 `caller`。
8. 一律以符號名（函式名、測試名）定位，不依賴行號；`cli.py` 與 account-welcome-cli、`compute_envs.py` 與 aws-launch 有重疊，衝突由 developer-agent 在 PR 階段解，執行者不必處理別的分支。
9. B 級，verifier 通過＋CI 綠由 developer-agent 自行合併。

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
