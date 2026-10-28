# 測試案例：擁有者綁定補三個縫（owner-binding，#116）

**規格**：`specs/owner-binding/plan.md`（本任務沒有 spec.md，計畫即規格；「對應需求」欄引用計畫的 US／條號與 issue #116 原文）　**總覽**：`test-case-overview.md`

名詞先講白：
- **擁有者**：一個代理（agent，替某個使用者在叢集上跑事的小程式）或一個計算環境（compute environment，一組可以送件的叢集設定）屬於哪一位使用者。
- **無使用者 token**：發的時候沒指名使用者的代理通行證（token）。
- **無主**：代理或環境在資料庫裡沒有擁有者。
- **「找不到」措辭**：別人的東西對你的回答必須和「根本不存在」一模一樣，不透露存在與否。
- 範例名字沿用計畫：使用者 alice、bob（也就是計畫裡的 A、B），代理 `ag`，環境 `c1`／`c2`。

維護者原話（issue #116，逐字）：
- 「`agents` and `compute_envs` record the owning user; agent tokens are issued for a user.」→ US1
- 「Every action lists and uses only the caller's own agents and compute environments (MCP, HTTP and CLI entries alike).」→ US3、US2 的跨使用者列
- 「Test case first: one user's agents and compute environments are not visible or usable by another user.」→ 每條缺口都有一對「A 看得到／用得到、B 看不到／用不到」
- 「ADR 0009 postponed 010 but kept "each user sees only their own runs" (point 7).」→ B 的回答必須與「不存在」相同
- 「The ownership part of 010 is still needed under one role.」→ 不做角色、不做共享

類型只有三種：**功能**（做到了）、**例外**（出錯或不該做時怎麼反應）、**不在範圍**（計畫明講不做，確認真的沒做）。

## User Story 1 — 新發的代理 token 一定要指名使用者，舊的無使用者 token 不能服務已有主人的代理（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 US1-1；issue「agent tokens are issued for a user」 | 例外 | 平台上已有使用者 alice | 管理者執行 `abf-platform agent-token new ag`（沒給 `--user`） | 指令失敗（結束碼不是 0）；輸出含 `--user`；`tokens` 表沒有新增 `kind='agent'` 的列 | 自動：`platform/tests/test_owner_tokens.py::test_agent_token_new_without_user_is_refused_once_a_user_exists` |
| TC-002 | 計畫 US1-1（訊息與結束碼） | 例外 | 同 TC-001 | 同 TC-001 | 結束碼剛好是 1；訊息為 `rejected: say whose agent this is with --user NAME (請用 --user 名字 指定這個代理是誰的)` | 自動：`platform/tests/test_owner_tokens.py` |
| TC-003 | 計畫 US1-1（不印任何像 token 的東西） | 例外 | 同 TC-001 | 同 TC-001 | 輸出沒有任何以 `abf_` 開頭的字串 | 自動：`platform/tests/test_owner_tokens.py` |
| TC-004 | 計畫 US1-1（零使用者照舊允許）；裁決 6 | 功能 | 平台上一個使用者都沒有 | 執行 `abf-platform agent-token new ag`（沒給 `--user`） | 結束碼 0；印出以 `abf_` 開頭的 token | 自動：`platform/tests/test_owner_tokens.py::test_agent_token_new_without_user_is_allowed_when_there_is_no_user` |
| TC-005 | 計畫 US1；`docs/ONBOARDING.md` 的寫法 | 功能 | 有使用者 alice；代理 `ag` 還沒有任何列 | 執行 `abf-platform agent-token new ag --user alice` | 結束碼 0；印出 `abf_` 開頭的 token；`tokens` 表多一筆 `kind='agent'` 且屬於 alice | 自動：`platform/tests/test_owner_tokens.py` |
| TC-006 | 計畫 US1-2 | 例外 | `ag` 已因 alice 的 token hello 過而歸 alice；另有使用者 bob | 執行 `abf-platform agent-token new ag --user bob` | 指令失敗（結束碼不是 0）；`tokens` 表沒有新增列 | 自動：`platform/tests/test_owner_tokens.py::test_agent_token_for_an_agent_owned_by_another_user_is_refused_at_issue` |
| TC-007 | 計畫 US1-2（不透露 A 是誰） | 例外 | 同 TC-006 | 同 TC-006 | 輸出不含 `alice` | 自動：`platform/tests/test_owner_tokens.py` |
| TC-008 | 計畫 US1-2（講白） | 例外 | 同 TC-006 | 同 TC-006 | 輸出明說這個代理屬於另一位使用者（「這個代理屬於另一位使用者」或同義字句） | 自動：`platform/tests/test_owner_tokens.py` |
| TC-009 | 計畫 US1-4 | 例外 | `ag` 歸 alice；用 `create_token(kind="agent", agent_name="ag")`（無使用者，繞過 CLI）做出一支 token | 用該 token 對 `ag` 做 hello | 回 403 | 自動：`platform/tests/test_owner_tokens.py::test_a_token_with_no_user_cannot_serve_an_owned_agent` |
| TC-010 | 計畫 US1-4 | 例外 | 同 TC-009 | 用該 token 做 poll | 回 403 | 自動：`platform/tests/test_owner_tokens.py` |
| TC-011 | 計畫 US1-4 | 例外 | 同 TC-009 | 用該 token 回報 result | 回 403 | 自動：`platform/tests/test_owner_tokens.py` |
| TC-012 | 計畫 US1-4（不洩漏） | 例外 | 同 TC-009，另備「bob 的 token 打 alice 的代理」的 403 | 比較兩個 403 的回應 JSON | 兩者都只有 `message` 一個 key，key 集合相同；訊息為 `This agent belongs to another user` | 自動：`platform/tests/test_owner_tokens.py` |
| TC-013 | 計畫 US1-4 | 例外 | 同 TC-009 | 做完 TC-009～011 後查 `agents` 表 | `ag` 的擁有者仍是 alice | 自動：`platform/tests/test_owner_tokens.py` |
| TC-014 | 計畫 US1-4（舊部署相容） | 功能 | `ag` 無主（先前只被無使用者 token 打過）；一支無使用者 token | 用該 token 對 `ag` 做 hello | 回 200；`ag` 仍無主 | 自動：`platform/tests/test_owner_tokens.py::test_a_token_with_no_user_still_serves_an_agent_nobody_owns` |
| TC-015 | 計畫 US1-4（poll） | 功能 | 同 TC-014 | 用該 token 做 poll | 不回 403（照常服務） | 自動：`platform/tests/test_owner_tokens.py` |
| TC-016 | 計畫 US1-4（result） | 功能 | 同 TC-014 | 用該 token 回報 result | 不回 403（照常服務） | 自動：`platform/tests/test_owner_tokens.py` |
| TC-017 | 計畫 US1-4；現況 hello／poll／result 403（不得放寬） | 例外 | `ag` 歸 alice；bob 有帶使用者的代理 token | 用 bob 的 token 對 `ag` 做 hello | 回 403，訊息 `This agent belongs to another user`；`ag` 仍歸 alice | 自動：`platform/tests/test_owner_binding.py`（既有 tc029／tc030 一類，不得被改） |
| TC-018 | 計畫 US1-3；裁決「不讓 store.create_token 強制 user_id」 | 不在範圍 | 有使用者 alice | 直接呼叫 `store.create_token(kind="agent", agent_name="ag")`（不給 user_id） | 仍然建成功（store 的規則沒變，`test_pat.py` tca12 仍綠） | 自動：`platform/tests/test_pat.py`（tca12，不得被改） |
| TC-019 | 計畫 US1-4（不傷到正常用法） | 功能 | `ag` 歸 alice；alice 有帶使用者的代理 token | 用 alice 的 token 對 `ag` 做 hello | 回 200 | 自動：`platform/tests/test_owner_tokens.py` |
| TC-020 | 計畫 US1-4（既有行為保留） | 功能 | `ag` 無主；alice 有帶使用者的代理 token | 用 alice 的 token 對 `ag` 做 hello | 回 200；`ag` 變成歸 alice | 自動：`platform/tests/test_owner_binding.py`（tc029，不得被改） |

## User Story 2 — 擁有者已定的環境，它的代理不再無主（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 計畫 US2-5（create） | 功能 | `ag` 已被無使用者 token hello 過（有列、無主）；有 alice、bob | `ce create --name c1 --agent ag --owner alice ...` | 成功；`ag` 的擁有者是 alice 的 id | 自動：`platform/tests/test_owner_tokens.py::test_ce_create_with_an_owner_claims_an_agent_nobody_owns` |
| TC-022 | 計畫 US2-5（update） | 功能 | 同 TC-021；環境 c1 已存在 | `ce update` 帶 `--owner alice` | 成功；`ag` 的擁有者是 alice 的 id | 自動：`platform/tests/test_owner_tokens.py::test_ce_update_owner_claims_an_agent_nobody_owns` |
| TC-023 | 計畫 US2-5；issue Scope 2 | 功能 | TC-021 之後 | alice 的 PAT 呼叫 `actions.list_agents` | 清單中看得到 `ag` | 自動：`platform/tests/test_owner_tokens.py` |
| TC-024 | 計畫 US2-5；`jobs._target` 對無主代理 fail-closed | 功能 | TC-021 之後 | alice 對 `ag` 上的環境做確認（`jobs._target`） | 被接受（不再是「找不到」） | 自動：`platform/tests/test_owner_tokens.py` |
| TC-025 | issue「not visible…by another user」 | 例外 | TC-021 之後 | bob 的 PAT 呼叫 `actions.list_agents` | 看不到 `ag`（與 `ag` 不存在時相同） | 自動：`platform/tests/test_owner_tokens.py` |
| TC-026 | issue ADR 0009 point 7 | 例外 | TC-021 之後 | bob 對 alice 的環境做確認（`jobs._target`） | 回「找不到」措辭，與環境不存在時一樣 | 自動：`platform/tests/test_owner_tokens.py` |
| TC-027 | 計畫 US2-5（別人的代理不被搶） | 例外 | `ag` 歸 alice | `ce create ... --agent ag --owner bob` | 被 `_agent_owner_problem` 拒絕，訊息與既有 tc031 完全相同 | 自動：`platform/tests/test_owner_tokens.py::test_ce_create_does_not_claim_an_agent_that_has_an_owner` |
| TC-028 | 計畫 US2-5 | 例外 | 同 TC-027 | 做完 TC-027 後查 `agents` 表 | `ag` 仍歸 alice；沒有環境被建出來 | 自動：`platform/tests/test_owner_tokens.py` |
| TC-029 | 計畫 US2-5（代理還沒 hello） | 功能 | `agents` 表裡沒有 `ag` 的列 | `ce create ... --agent ag --owner alice` | 成功；`agents` 表仍沒有 `ag` 的列（不憑空建代理） | 自動：`platform/tests/test_owner_tokens.py` |
| TC-030 | 計畫 US2-5（等第一個帶使用者的 token） | 功能 | TC-029 之後 | alice 的代理 token 對 `ag` 做 hello | `ag` 歸 alice（既有 `register` 行為） | 自動：`platform/tests/test_owner_tokens.py` |
| TC-031 | 計畫 US2-6（無擁有者的環境不認領） | 功能 | 零使用者；`ag` 無主 | `ce create ... --agent ag`（無擁有者） | 成功；`ag` 仍無主 | 自動：`platform/tests/test_owner_tokens.py::test_ce_create_with_no_owner_does_not_claim` |
| TC-032 | 計畫 US2-6（既有行為不變） | 功能 | TC-031 之後 | `user add` 一位使用者並跑 `assign_orphans` | 該使用者接手無主的環境（既有行為） | 自動：`platform/tests/test_owner_tokens.py` |
| TC-033 | 計畫 US2-5「同一個交易」 | 例外 | `ag` 無主；用 monkeypatch 讓 `compute_envs` 寫環境列時丟例外 | `ce create ... --agent ag --owner alice` | 指令失敗；`ag` 的擁有者仍是 NULL；沒有環境列（不出現「代理已改、環境沒建」） | 自動：`platform/tests/test_owner_tokens.py::test_claiming_is_one_transaction` |
| TC-034 | 計畫 US2-7 | 功能 | 兩位使用者；`ag` 無主；環境 c1、c2 都歸 alice 且都用 `ag` | 跑 `assign_orphans` | `ag` 歸 alice | 自動：`platform/tests/test_owner_tokens.py::test_assign_orphans_gives_an_unowned_agent_to_the_owner_of_its_environments` |
| TC-035 | 計畫 US2-7（冪等） | 功能 | TC-034 之後 | 再跑一次 `assign_orphans` | 結果不變（`ag` 仍歸 alice，沒有別的列被改） | 自動：`platform/tests/test_owner_tokens.py` |
| TC-036 | 計畫 US2-7（多人共用不動） | 例外 | c1 歸 alice、c2 歸 bob，都用 `ag`；`ag` 無主 | 跑 `assign_orphans` | `ag` 仍無主 | 自動：`platform/tests/test_owner_tokens.py::test_assign_orphans_leaves_an_agent_shared_by_two_owners_alone` |
| TC-037 | 計畫 US2-7（沒有環境用它） | 例外 | `ag` 無主；沒有任何環境用 `ag` | 跑 `assign_orphans` | `ag` 仍無主 | 自動：`platform/tests/test_owner_tokens.py::test_assign_orphans_leaves_an_agent_with_no_environment_alone` |
| TC-038 | 計畫 US2-7（環境本身無主） | 例外 | 用 `ag` 的環境沒有擁有者；`ag` 無主 | 跑 `assign_orphans` | `ag` 不動 | 自動：`platform/tests/test_owner_tokens.py::test_assign_orphans_never_gives_an_agent_to_the_owner_of_an_ownerless_environment` |
| TC-039 | 計畫 US2-7（rebuild 不開 platform.db／tokens.db） | 功能 | 一個含無主代理的資料庫 | 跑 `rebuild` | `platform.db` 與 `tokens.db` 的位元組完全不變（沿用 tc065 的做法） | 自動：`platform/tests/test_owner_tokens.py::test_rebuild_still_never_opens_the_platform_or_the_tokens` |
| TC-040 | 計畫 US2-7（`owners_assigned` 語意不變、單人接手保留） | 功能 | 只有一位使用者；有無主的環境、代理與紀錄 | 跑 `assign_orphans` | 該使用者接手全部（既有行為） | 自動：`platform/tests/test_owner_binding.py`（既有案例，不得被改） |
| TC-041 | 計畫 US2-7（原本「兩個以上什麼都不接」保留） | 例外 | 兩位以上使用者；有無主的環境（無擁有者）與紀錄 | 跑 `assign_orphans` | 無主的環境與紀錄仍無主（新增的一步只動「用它的環境全屬同一人」的代理） | 自動：`platform/tests/test_owner_binding.py`（既有案例，不得被改） |
| TC-042 | issue Scope 2；跨使用者（讀） | 例外 | TC-021 之後 | bob 的 PAT 呼叫 `actions.list_compute_envs` | 結果不含 alice 的環境，與不存在時相同 | 自動：`platform/tests/test_owner_tokens.py::test_b_cannot_see_or_use_the_claimed_agent_or_environment` |
| TC-043 | 同上 | 例外 | TC-021 之後 | bob 呼叫 `actions.get_compute_env` 問 alice 的環境 | 回與「環境不存在」相同的結果 | 自動：`platform/tests/test_owner_tokens.py` |
| TC-044 | 同上 | 例外 | TC-021 之後 | bob 呼叫 `actions.list_site_files` 指向 alice 的環境 | 回與「環境不存在」相同的結果 | 自動：`platform/tests/test_owner_tokens.py` |
| TC-045 | 同上 | 例外 | TC-021 之後；alice 有一個在該環境上的 run | bob 呼叫 `actions.run_outputs` 問該 run | 回與「run 不存在」相同的結果 | 自動：`platform/tests/test_owner_tokens.py` |
| TC-046 | 跨使用者（寫／用） | 例外 | TC-021 之後；記下 `jobs` 表列數 | bob 對 alice 的環境走 `enqueue_confirmed` | 被拒（「找不到」措辭）；`jobs` 表列數不變 | 自動：`platform/tests/test_owner_tokens.py` |
| TC-047 | 計畫 US2-7；缺口 3 的「A 看得到」 | 功能 | TC-034 之後 | alice 的 PAT 呼叫 `actions.list_agents` | 看得到 `ag` | 自動：`platform/tests/test_owner_tokens.py` |
| TC-048 | 計畫 US2-7；缺口 3 的「B 看不到」 | 例外 | TC-034 之後 | bob 的 PAT 呼叫 `actions.list_agents` | 看不到 `ag` | 自動：`platform/tests/test_owner_tokens.py` |

## User Story 3 — 守衛測試：以後新動作忘了帶呼叫者會當場紅（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-049 | 計畫 US3-8；issue Scope 2 | 功能 | 現在的程式碼 | 守衛掃 `abf_platform/actions/*.py`、`mcp_server.py`、`web*.py`、`pipeline_launch.py`、`abf_launch/build.py` 的呼叫 | 白名單外沒有任何缺擁有者參數的呼叫（綠） | 自動：`platform/tests/test_owner_guard.py::test_every_read_and_queue_call_in_the_action_layer_names_its_caller` |
| TC-050 | 計畫 US3-8（掃描範圍） | 功能 | 同 TC-049 | 檢查守衛實際掃了哪些檔 | 清單恰好涵蓋上述五組檔案（`web*.py` 只讀） | 自動：`platform/tests/test_owner_guard.py` |
| TC-051 | 計畫 US3-10（不是空轉） | 功能 | 一小段合成原始碼：`compute_envs.get(p, name)`（沒帶擁有者） | 餵給守衛的偵測函式 | 被抓到 | 自動：`platform/tests/test_owner_guard.py::test_the_scanner_catches_a_call_without_an_owner` |
| TC-052 | 計畫 US3-8（八種呼叫） | 功能 | 八段合成原始碼，各是 `compute_envs.get`、`compute_envs.list_all`、`agents.list_agents`、`jobs.latest_pipeline_files`、`jobs.enqueue_listing`、`jobs.enqueue_task_log`、`jobs.enqueue_pipeline_files`、`jobs.check_target` 之一且不帶擁有者 | 逐段餵給偵測函式 | 八段都被抓到 | 自動：`platform/tests/test_owner_guard.py` |
| TC-053 | 計畫 US3-10 | 功能 | 合成原始碼 `compute_envs.get(p, name, owner=1)` | 餵給偵測函式 | 通過（不被抓） | 自動：`platform/tests/test_owner_guard.py::test_the_scanner_lets_the_named_exceptions_through` |
| TC-054 | 計畫 US3-8（位置參數） | 功能 | 合成原始碼寫成現有程式的樣子：`compute_envs.get(state, ce_name, owner)` 與 `jobs.latest_pipeline_files(platform_path, repo, revision, asked, caller_id)` | 餵給偵測函式 | 兩者都通過 | 自動：`platform/tests/test_owner_guard.py` |
| TC-055 | 計畫 US3-9（白名單） | 功能 | 合成原始碼：`is_gcb`、`_same_environment`、`prepare_cancel`、`prepare_clean`、`is_aws` 這幾個函式內有不帶擁有者的 `compute_envs.get(state, x)` | 餵給偵測函式 | 全部通過 | 自動：`platform/tests/test_owner_guard.py::test_the_scanner_lets_the_named_exceptions_through` |
| TC-056 | 計畫 US3-9（「其餘一律不准」） | 例外 | 合成原始碼：名為 `prepare_something_else`（不在白名單、不以 `is_` 開頭）的函式內有 `compute_envs.get(state, x)` | 餵給偵測函式 | 被抓到 | 自動：`platform/tests/test_owner_guard.py` |
| TC-057 | 計畫 US3-9（白名單不腐爛） | 例外 | 白名單的具名函式（`is_gcb`、`_same_environment`、`prepare_cancel`、`prepare_clean`） | 檢查每個名字是否真的存在於 `abf_launch/build.py` | 每個都存在；任何一個不存在測試就失敗 | 自動：`platform/tests/test_owner_guard.py::test_the_allow_list_has_no_dead_names` |
| TC-058 | 計畫 US3-11；專長守則「對等性」 | 功能 | `mcp_server.build_server(...)` 註冊的全部工具；`actions` 中帶 `caller` 的公開函式 | 測試同時列舉兩邊（工具名與動作名之間用明列的對應表） | 兩邊差集全由明列的名單組成，每一項有理由 | 自動：`platform/tests/test_owner_guard.py::test_every_mcp_tool_has_an_action_and_every_caller_action_has_a_tool` |
| TC-059 | 計畫 US3-11「缺一邊就失敗」 | 例外 | 在測試內模擬：多一個沒有對應動作的工具，或多一個沒列入名單的帶 `caller` 動作 | 跑同一個對等性比對 | 比對失敗（不是悄悄通過） | 自動：`platform/tests/test_owner_guard.py` |
| TC-060 | 計畫 範圍：新測試檔首要求；`test_scope.py` TC-070 | 功能 | 新增的 `test_owner_tokens.py`、`test_owner_guard.py` | 看每個檔的前 40 行 | 各有一行 `# Nothing existing: <理由，至少 15 字>`；`test_scope.py` 綠 | 自動：`platform/tests/test_scope.py` |
| TC-061 | 計畫 US3-9（不掃的檔） | 不在範圍 | 守衛的掃描清單 | 檢查清單是否含 `abf_platform/cli.py`、`abf_launch/cli.py`、`cloud_cost.py`、`su.py`、`abf_station/*` | 都不在清單內（終端機無呼叫者是設計） | 自動：`platform/tests/test_owner_guard.py` |
| TC-062 | 計畫 US3-8／裁決：web 檔只讀 | 不在範圍 | 守衛測試檔 | 檢查守衛讀 `web*.py` 的方式 | 只以唯讀方式讀取（`Path.read_text` 或 `open(..., "r")`），沒有任何寫入 | 自動：`platform/tests/test_owner_guard.py::test_the_web_files_are_only_read` |

## 文件與搬遷（管理者看得到的部分）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-063 | 計畫 12 | 功能 | 更新後的 `docs/PLATFORM.md` | 讀「Whose it is (spec 116)」裡 Environments and agents 那一條 | 寫明：已有使用者的平台上，代理 token 必須帶 `--user` | 手動：閱卷者讀文件 |
| TC-064 | 計畫 12 | 功能 | 同上 | 同上 | 寫明：沒指名使用者的舊 token 只能服務無主的代理 | 手動：閱卷者讀文件 |
| TC-065 | 計畫 12 | 功能 | 同上 | 同上 | 寫明：`ce create|update --owner` 會把無主的代理一併認領 | 手動：閱卷者讀文件 |
| TC-066 | 計畫 12（:147 範例） | 功能 | 同上 | 讀 `agent-token new` 的範例命令 | 範例已加 `--user alice` | 手動：閱卷者讀文件 |
| TC-067 | 計畫 12（OPERATIONS） | 功能 | 更新後的 `docs/OPERATIONS.md` | 讀 agent-token 那一列 | 寫成 `abf-platform agent-token new <name> --user U`（沒有方括號） | 手動：閱卷者讀文件 |
| TC-068 | 計畫 12（TESTING 小節） | 功能 | 更新後的 `docs/TESTING.md` | 找「Owner binding follow-up (owner-binding)」小節 | 存在，且依序列出管理者四步：①`ce list`／`launches` 找擁有者是 `(none: local only)` 的代理或環境 ②對舊的無使用者 token `agent-token revoke <name>` 後 `agent-token new <name> --user <名字>` 重發，新 token 放進代理的 `--token-file` ③重啟 `serve`（讓 `assign_orphans` 跑）④以 A、B 各自的 PAT 呼叫 MCP `list_agents`，確認各只看到自己的 | 手動：閱卷者讀文件 |
| TC-069 | 計畫「完成標準」（文件） | 功能 | 更新後的 `CHANGELOG.md` | 讀最新一條 | 有一條說明這片的行為變化（舊的無使用者 token 對已有主人的代理會被拒；`ce --owner` 認領無主代理） | 手動：閱卷者讀文件 |
| TC-070 | 計畫「完成標準」手動：A 與 B 各自只看得到自己的 | 功能 | 已有 alice、bob 兩位使用者的測試平台；舊的無使用者代理 token 已依 TESTING 小節重發 | alice 的 PAT 呼叫 MCP `list_agents`、`get_compute_env` | 只看到自己的代理與環境 | 手動：`docs/TESTING.md`「Owner binding follow-up」第 ④ 步 |
| TC-071 | 計畫「完成標準」手動：彼此的 get_compute_env 回相同的「找不到」 | 例外 | 同 TC-070 | bob 的 PAT 呼叫 `get_compute_env` 問 alice 的環境名 | 回的「找不到」與問一個根本不存在的環境名時一模一樣 | 手動：`docs/TESTING.md`「Owner binding follow-up」第 ④ 步 |
| TC-072 | 計畫 US1-4、搬遷說明 | 功能 | 測試平台上 `ag` 已歸 alice，仍留一支舊的無使用者 token | 先確認舊 token 被擋（403），再 `agent-token revoke ag`、`agent-token new ag --user alice`，換上新 token | 新 token 能 hello；`ag` 仍歸 alice | 手動：`docs/TESTING.md`「Owner binding follow-up」第 ② 步 |

## 範圍與不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-073 | 計畫「不需要 schema migration」；專長守則（結構變動） | 不在範圍 | 本任務的 diff | 看 `store.py`、`agents.py`、`compute_envs.py` 的變更 | 沒有新欄位、沒有新表（無 `ALTER TABLE`／`CREATE TABLE` 新增）；文件把搬遷寫成資料搬遷（`assign_orphans` 新一步），不是 schema 變動 | 手動：閱卷者看 `git diff` |
| TC-074 | 計畫「不做」：不改 `hello` 回傳 | 不在範圍 | 有效的代理 token（歸屬正確） | 對代理做 hello | 回傳內容的 key 與修改前相同（既有 receiver／station 測試仍綠） | 自動：`platform/tests/test_receiver*.py`、`platform/tests/test_station_owner.py`（既有，不得被改） |
| TC-075 | 計畫「不做」：不改終端機看全部 | 不在範圍 | 兩位使用者各有環境 | 終端機執行 `ce list`、`ce show`、`launches` | 仍列出所有擁有者的環境與紀錄（無呼叫者） | 自動：`platform/tests/test_owner_binding.py`（既有案例，不得被改） |
| TC-076 | 計畫「不做」：不新增 MCP 工具 | 不在範圍 | `build_server(...)` | 列出註冊的工具名 | 與修改前同一組，沒有新增或刪除 | 自動：`platform/tests/test_owner_guard.py`（TC-058 的列舉）與 `platform/tests/test_mcp*.py` 既有案例 |
| TC-077 | 計畫「不做」「不准動」：不改網頁、不新增網頁路由 | 不在範圍 | 本任務的 diff | `git diff --name-only <base>...HEAD` | 不含 `platform/abf_platform/web*.py`、`static/*`、`DESIGN.md`、`PRODUCT.md`、`platform/tests/test_web_*` | 手動：閱卷者看 `git diff` |
| TC-078 | 計畫「範圍：檔案」 | 不在範圍 | 本任務的 diff | `git diff --name-only <base>...HEAD` | 只含計畫「範圍：檔案」列出的檔（`station_harness.py`、`test_station_envs.py`、`test_station_platform.py` 僅在先紅時才出現） | 手動：閱卷者看 `git diff` |
| TC-079 | 計畫「不准動」 | 不在範圍 | 本任務的 diff | 同上 | 不含 `jobs.py`、`launch.py`、`aws_launch.py`、`cloud_cost.py`、`su.py`、`releases.py`、`abf_launch/*`（`build.py` 除外只讀）、`abf_station/*`、`spec.md`、`test-case*.md`、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`.github/`、`platform/pyproject.toml`、`docs/ONBOARDING.md` | 手動：閱卷者看 `git diff` |
| TC-080 | 計畫「必須更新的既有斷言」：預期 0 條；「沒有任何一條既有拒絕被放寬」 | 不在範圍 | 本任務的 diff 與 base 比較 | 比對 `test_owner_binding.py` 與其他既有測試 | 沒有斷言被刪、被放寬、被跳過；`test_pat.py` tca12、tcd14、`test_onboarding_doc.py:140` 未被改 | 手動：閱卷者看 `git diff` |
| TC-081 | 計畫「完成標準」與「作法」：station 三處 | 不在範圍 | 同上 | 看 `station_harness.py`、`test_station_envs.py`、`test_station_platform.py` 的 diff（若有） | 只在 `agent-token new` 呼叫後加 `--user <名字>`，斷言一字不動；沒因新規則變紅就不該出現在 diff | 手動：閱卷者看 `git diff` |

## 憲法與安全網

本片不動 `hooks/`、安全網、確認管道；下列各列是它會碰到的規則：憲法 13 條各自的檢查不能被弄壞、後端專長守則（擁有者規則、錯誤訊息、確認管道、不洩漏密鑰）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-082 | 專長守則：錯誤訊息說明該怎麼做 | 例外 | TC-001 與 TC-006 的情境 | 看兩個拒絕訊息 | 都含下一步的指令字樣（`--user`） | 自動：`platform/tests/test_owner_tokens.py::test_refusals_say_what_to_do_and_leak_no_token_or_other_user` |
| TC-083 | 專長守則：密鑰不得出現在回應 | 例外 | 同上 | 看兩個拒絕訊息 | 不含任何 token 片段（`abf_` 字串） | 自動：`platform/tests/test_owner_tokens.py::test_refusals_say_what_to_do_and_leak_no_token_or_other_user` |
| TC-084 | 專長守則／issue ADR 0009 point 7：不洩漏他人 | 例外 | 同上 | 看兩個拒絕訊息 | 不含別人的使用者名 | 自動：`platform/tests/test_owner_tokens.py::test_refusals_say_what_to_do_and_leak_no_token_or_other_user` |
| TC-085 | 專長守則：回應不含密鑰與他人資訊 | 例外 | TC-009～011 的 403 | 看 403 回應內容 | 只有 `{"message": "This agent belongs to another user"}`，不含任何 token 或使用者名 | 自動：`platform/tests/test_owner_tokens.py` |
| TC-086 | 專長守則「確認管道」；計畫「不改任何確認管道」 | 例外 | TC-021 之後；alice 的請求尚未被人確認 | alice 在環境上提出送件／取消請求但不確認；記下 `jobs` 表列數 | 沒有確認就不改資料（`jobs` 表列數不變）；確認的方式與修改前相同 | 自動：`platform/tests/test_owner_binding.py`、`platform/tests/test_owner_tokens.py` |
| TC-087 | 憲法 1–13 各自的 check；完成標準「全套綠」 | 功能 | 完成記號 `GREEN <HEAD sha>` 且工作區乾淨 | 在 WSL 跑 `tests/run_all.sh`（由 executor 的完成閘門保證；閱卷者只核對記號） | 全套綠，沒有因本片變紅的既有測試 | 自動：`tests/run_all.sh`（閘門記號） |
