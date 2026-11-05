---
id: mcp-chat-confirm-v5
title: MCP 對話確認通道（CHAT）：使用者在對話裡回「送出」，AI 帶 request_id＋user_confirmed 再呼叫一次即可送出，不必開網頁
tier: A
risk: L
kinds: backend
lane: 獨占（碰 confirm.py、actions/__init__.py、mcp_server.py、憲法；不與動這幾檔的車道並行）
branch: feat/mcp-chat-confirm-v5
base: v3（`origin/v3` @ 0b293be，PR #334 合併；查證日 2026-11-04。行號會漂，以符號名為準）
source: 維護者 2026-11-04 對話（見下）；憲法 I.2 與 Safety Net 的「Every write tool…」規則
---

# mcp-chat-confirm

> 本檔由子 agent 起草（2026-11-04）。**第 A 級（修憲）、風險 L**：閱卷要附爆炸半徑證明，PASS 後再跑一次 Opus 對抗審。憲法修正案需維護者用自己的話明確同意才能合併（見「裁決」Q1）。

## 目標
讓只靠 MCP 的 AI agent 也能把 launch／cancel／resume／relaunch 送出：第一次呼叫回「待確認摘要＋request id」，使用者在**對話裡**回覆確認後，AI 帶同一個 id 與 `user_confirmed=true` 再呼叫同一個工具，平台就核准並排隊，通道記為 `CHAT`。表單（ELICITED）與網頁（PAGE）兩條**不動**。對使用者的意義：沒有表單、不想開網頁的 client（Codex、純 Claude Code）也能完整跑完一次送出。

## 維護者原話（verifier 出題用）
- 「ai agent透過MCP使用abf，現在是不能直接送出，一定要跳出網頁確認連結才能送出嗎? 若是，改成只要有得到使用者回復確認送出就好，這樣才能達成全靠MCP也能跑」→ TCM-01、TCM-10（待確認→使用者在對話回覆→AI 再呼叫→排隊，全程沒有開網頁、沒有表單）。
- 「照3.」（選項 3＝新增第三條通道 CHAT，與表單、網頁並存）→ TCM-12（表單與網頁行為不變）、TCM-15（稽核記 CHAT）、憲法 7.0.0 條目。
- 派工時的硬條件（developer-agent 轉述，同為閱卷依據）：內容綁雜湊、10 分鐘逾時、一次性、同一呼叫者、稽核記 CHAT → TCM-04／05／06／07／15。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/confirm.py`（`approve` 加參數與 CHAT 的呼叫者先檢；`find_approved`、`find_attempt` 的通道清單加 `'CHAT'`；兩處 docstring）
- `platform/abf_platform/actions/__init__.py`（新 `CHAT = _Channel("CHAT")`；`_ask` 的 CHAT 分支；`request_launch`、`request_pipeline_launch`、`request_cancel`、`_request_attempt`、`request_resume`、`request_relaunch` 簽章；待確認訊息；模組 docstring 開頭幾行）
- `platform/abf_platform/mcp_server.py`（launch、cancel、resume、relaunch 四個工具的簽章與 description；模組 docstring「They carry no argument that could say yes」）
- `platform/abf_platform/guidance.py`（`FIXED_SENTENCE`，總長 ≤ `MAX_BYTES`＝2048）
- `platform/abf_platform/actions/chat_tools.py`（`tool_specs` 把兩個新參數剝掉；`CHAT_SYSTEM_PROMPT` 不改字）
- `platform/abf_platform/elicit.py`（只改檔頭註解那句反對 `confirm=true` 的話）
- `.specify/memory/constitution.md`（I.2、Safety Net 規則與其 Check 行、新增 7.0.0 條目、檔尾版本行）
- `skills/launch/SKILL.md`、`skills/runs/SKILL.md`、`skills/operational/SKILL.md`（只加 CHAT 一句；釘住的句子不動）
- `docs/PLATFORM.md`（「The confirmation page」節加一段；:436 那句「no argument that could say yes」）、`docs/TESTING.md`（手動步驟）、`CHANGELOG.md`
- 測試（新）：`platform/tests/test_chat_confirm.py`（檔首 40 行內要有 `# Nothing existing: <理由，≥15 字>`，`test_scope.py` TC-070）
- 測試（改，僅依「必須更新的既有斷言」）：見該節的檔案清單；另 `platform/tests/helpers.py` 只准加常數 `CHAT_ARGS = {"request_id", "user_confirmed"}`；`platform/tests/human_harness.py` 只在 `World.choices`／`launch` 不能透傳新鍵時加最小透傳
- `platform/tests/mcp/snapshots/tools.json`（用 `test_mcp_contract_tools.py` 內既有的重生方法，不手改）
- `tests/charter_v4_workflow_test.sh`、`tests/constitution_scope_test.sh`、`tests/platform_direction_docs_test.sh`（只改版本行字串，見該節）
- `specs/mcp-chat-confirm/ledger.md`（新）

**不准動（硬規則）**：`.github/`、`hooks/`、`plugin.json`、`platform/abf_station/`、`platform/abf_platform/web.py` 與 `web_*.py`（網頁 `/c/<id>` 的 PAGE 路徑一字不動）、`jobs.py`、`store.py`（不加欄位）、`CONTEXT.md`、`docs/adr/*`、`docs/PRINCIPLES.md`、`docs/ROADMAP.md`、`constitution_6_test.sh`（除非它因 Check 行變紅，才准加新前綴並在 ledger 說明）。

## 作法
### 一、資料與通道（不需要 migration）
1. `confirmations.channel` 是自由字串，新值 `'CHAT'` 不加欄位、不加表 → **不需要 migration**。稽核＝`channel='CHAT'`＋`confirmed_at`＋`caller_user_id`＋`sha256`（既有欄位）。
2. `actions/__init__.py` 新增單例 `CHAT = _Channel("CHAT")`（與 TERMINAL／ELICITED／PAGE 並列）。**CHAT 不加進 `_require_human`，也不加進公開的 `actions.approve`**（後者只收 ELICITED、PAGE，網頁路由用）。結果：網頁拿不到 CHAT；`forget`／`clean_work` 仍只有表單；`actions.approve(..., confirmed_by=CHAT)` 仍被拒（TCM-12）。
3. 逾時沿用 `PENDING_SECONDS=600`；一次性沿用既有「已核准的列再核准＝already」；同一呼叫者沿用 `caller_user_id`。三者都不放寬。

### 二、工具介面（launch、cancel、resume、relaunch 四個，其他工具不動）
4. 各加兩個選填參數：`request_id: str | None = None`、`user_confirmed: bool = False`。`required` 不變；`forget`、唯讀工具不加。
5. **第一次呼叫（沒有 request_id）**：行為與現在一致（有表單走表單＝ELICITED；否則寫 pending 並回 `confirmation_url`）。回覆**多帶**說明：`id` 即 request id；訊息改為「還沒送出。請把摘要給本人看並問他要不要送出；他在對話裡明確回覆後，用同樣的參數加 `request_id=<id>`、`user_confirmed=true` 再呼叫一次；也可請他打開網址按送出」。刪掉「AI 不能代按」，換成「在本人回覆之前不可自己填 true」。回覆的其他鍵（`sent`、`state`、`summary`、`confirmation_url`、`message`）與型別不變。
6. **確認呼叫（有 `request_id` 且 `user_confirmed=true`）**：工具照常用參數重建 bundle、跑既有檢查（`check_run_name`、`_cloud_check`、擁有者、`launched_by`），然後在 `_ask` 的 `create_pending` **之前**分支：`confirm.approve(path, request_id, "CHAT", caller_id, clock, expected_sha=common.bundle_sha256(bundle), expected_kind=kind)`。成功回 `_queued(...)`。**`user_confirmed=true` 永遠不會建立 pending 再當場核准**：沒有 request_id、request_id 不存在、不是這個人的、種類不符，一律不寫任何列、不排任何 job。
7. `request_id` 給了但 `user_confirmed` 不是 true → 當成第一次呼叫（回待確認），不碰該列。
8. 重複的普通呼叫（沒帶兩個新參數）在 CHAT 核准後，由既有 `find_approved(include_spent=True)`／`find_attempt` 回已存在的 job（所以通道清單要加 CHAT），不開新的問題。
9. stdio（`caller is None`）：CHAT 一律拒（沿用 `approve` 內既有規則「沒有呼叫者且通道不是 ELICITED → not_yours」）。stdio 沒有表單時第一次呼叫就已被拒（`test_tca14_*` 不變）。

### 三、`confirm.approve` 的改動（唯一的核准入口，改動要最小）
10. 簽章加 `expected_sha=None, expected_kind=None`（關鍵字、預設 None＝既有 ELICITED／PAGE 路徑**位元組不變**）。
11. 只在 `channel == "CHAT"` 時啟用新順序：**① not_found → ② 呼叫者不符（含 `caller_user_id is None`）→ not_yours → ③ state=='confirmed' → already（回 job id）→ ④ void → ⑤ expired（列標 void）→ ⑥ `kind != expected_kind` 或 `row.sha256 != expected_sha` → 新狀態 `changed`（**列維持 pending、不作廢、不排 job**，訊息：內容與當初顯示的不同，請重新看摘要）→ ⑦ 既有的存檔完整性檢查 → ⑧ 翻 confirmed＋排隊**。理由：既有順序的 already 在呼叫者檢查之前，別人拿到已核准的 id 會洩漏 job id；CHAT 把呼叫者檢查移到最前面，別人的 id（pending、confirmed、void 皆然）一律只得 not_yours，且回應不含 job id、void 原因。
12. `NotApproved` 的新 status `changed`、`not_yours` 在 `_ask` 都轉成 `_no("未送出：…")`，**不**帶 `job_id`。`changed` 的訊息要告訴 AI「參數變了：請改回原參數，或重新發起一次」。
13. `find_approved`（`c.channel IN ('ELICITED', 'PAGE')`）、`find_attempt` 同一個清單加 `'CHAT'`；`find_cancel` 包 `find_approved`，不另改。`approve` 與模組 docstring 的「ELICITED or PAGE」「one of two ways」改成含 CHAT。
14. 佇列拒絕（SAVEPOINT 回滾）時既有行為不變：列轉 void，`channel='CHAT'` 與 `confirmed_at` 保留，因為使用者確實說過 yes。

### 四、瀏覽器對話（014a）不得拿到新參數
15. `chat_tools.tool_specs()` 目前直接取 MCP 工具的 schema。新參數加進 MCP 後，網頁聊天的模型會看到 `user_confirmed` 並能自填。**`tool_specs` 必須對 `REQUEST_TOOLS` 把 `request_id`、`user_confirmed` 從 properties 剝掉**（`required` 不含它們，故不需改）。`CHAT_SYSTEM_PROMPT`（「你沒有任何工具可以替本人說『是』」）因此仍為真，不改字。殘留風險（見「裁決」Q2）：網頁聊天把模型的參數原樣轉給 HTTP MCP，伺服器分不出是網頁聊天或別的 MCP client 的呼叫；本片靠剝 schema＋稽核擋，不靠伺服器端辨識。

### 五、文字（全部維持英文／中文雙語既有風格）
16. 四個工具的 description：把「you cannot say it for them」前後句子保留（CHAT 仍然不是「AI 代替他說」，是 AI 轉述他的回覆），加一句 CHAT 流程與「只在本人於對話中明確回覆之後才填 `user_confirmed=true`；不確定就再問」。
17. `FIXED_SENTENCE`：保留被測試釘住的子字串（見下），在「in their own client's form or on the page that the answer names」後加「or by answering in the chat (then call the tool again with the request_id and user_confirmed=true, only after they answered)」之類的短句。**總長 ≤ 2048 bytes**：executor 先量現況，不夠就縮短沒被釘的字，不准刪被釘的。
18. `elicit.py` 檔頭那句「Not a prompt inside the tool or a 'confirm=true' argument: the model fills those in itself」改成：表單仍是平台自己問人；CHAT 是另一條通道，明說它的保證較弱。`mcp_server.py` 模組 docstring 同理。

### 六、憲法 7.0.0（MAJOR；先例 5.0.0、6.0.0 重新定義 I.2／Safety Net 都是 MAJOR）
19. **I.2**：把「三條」改成四條，加入 CHAT 的定義與它的限制（誠實寫：平台看不到對話，CHAT 保證的是「AI 不能核准一個沒有給人看過、內容被改過、過期、已用過、或不是他的申請」，不保證那句 yes 真的出自人；模型自填 `true` 是已知殘留風險，靠雜湊綁定＋10 分鐘＋一次性＋稽核 CHAT 限縮影響）。「AI cannot press for them」改成「AI cannot answer for them; it can only relay the person's own reply on the request id」。
20. **Safety Net**：改「takes a person's yes only from…」那句加入第四條；「a token, a pending request or the model's own answer is never that answer」改為「…the model's own answer is never that answer; a chat reply counts only as the person's own, relayed with the request id and `user_confirmed=true`」。**保留** `(today launch, cancel, resume, relaunch and forget)` 這段原文（`constitution_6_test.sh` TC-045 用 regex `\(today ([^)]*)\)` 解析它，必須恰等於已註冊的寫入工具）。Check 行加新測試前綴 `test_tcm`（在 `test_chat_confirm.py`），其餘前綴全留。
21. **新條目 `### 7.0.0 (<執行當日>)`**，六段依序：**Rationale**（引維護者原話）、**What changes**、**Sync Impact Report**（列受影響檔）、**Impact on existing deployments**（新參數選填、舊 client 不受影響、不需要 migration、tools schema 多兩個選填欄位）、**Version**（`MAJOR`，說明為何不是 MINOR）、**Approval**（引「照3.」，並附維護者對修正案全文的同意——取得方式見 Q1）。**不改**舊條目，包括 5.0.0 那句「A pending request, a token, and anything the model can answer are not a channel」；7.0.0 明寫它對 CHAT 不再適用。
22. 檔尾版本行改為 `**Version**: 7.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: <執行當日>`，三個 shell 測試的精確字串同步改（見下）。

## 失敗先行測試（新檔 `platform/tests/test_chat_confirm.py`，prefix `test_tcm`；用既有夾具 `World`＝`w`，不碰網路；先寫、現在都紅）
以維護者的例子為主線：待確認 →（對話確認）→ 排隊。
- **TCM-01** `launch_pending_then_chat_confirm_then_queued`：`ann=w.user("ann")`；`o1=w.launch(caller=ann)` → `sent False`、`state "pending"`、有 `id`、`w.jobs()==[]`、訊息含 `user_confirmed`；`o2=w.launch(caller=ann, request_id=o1["id"], user_confirmed=True)` → `sent True`、`state "queued"`、`job_id`；`len(w.jobs("launch_nextflow"))==1`。
- **TCM-02** `true_with_no_pending_is_rejected`：(a) 沒 `request_id`、(b) 隨機 32 位 hex 的 id、(c) 空字串／過長字串／非字串 → 都 `ok False`，`w.jobs()==[] and w.confirmations()==[]`（不建任何列）。
- **TCM-03** `request_id_without_true_changes_nothing`：帶 id、`user_confirmed=False` → 回待確認、該列仍 pending、無 job。
- **TCM-04** `changed_content_is_rejected_and_the_row_survives`：o1 用預設參數；第二次改 `params={"depth": 9}`（或換 revision／run）帶 o1 的 id＋true → `ok False`、無 job、該列 `state=='pending'`（**不是** void）；第三次回原參數＋id＋true → 排隊成功。
- **TCM-05** `timeout_is_rejected`：`w.clock.t += 599` 仍可核准（另一個新 pending 驗）；`+= 600` 與 `+= 601` → 被拒、列標 void、原因含 `expired`、無 job。
- **TCM-06** `someone_elses_id_is_rejected`：`bob=w.user("bob")`；bob 拿 ann 的 id＋true → `ok False`、列仍 pending、無 job；ann 之後仍能核准。再測 ann 已核准的 id 與已 void 的 id：bob 的回應 `json.dumps` 後**不含** ann 的 `job_id`、不含 void 原因（洩漏檢查）。
- **TCM-07** `one_time_use`：ann 核准後再送一次同樣的確認呼叫 → 仍是同一個 `job_id`，`len(w.jobs())==1`、`len(w.confirmations())==1`。
- **TCM-08** `plain_repeat_after_chat_yes_returns_the_job`：核准後不帶新參數再呼叫 → 回同一 job，不新增 confirmations 列（驗通道清單含 CHAT）。
- **TCM-09** `stdio_cannot_use_chat`：`caller=None` 帶 id＋true → 被拒、無 job；直接呼叫 `confirm.approve(..., "CHAT", None, ...)` 對 pending 列 → `NotApproved.status=="not_yours"`。
- **TCM-10** `cancel_resume_relaunch_use_the_same_flow`：`w.hand_over()` 後 cancel 走 TCM-01 流程，job kind＝`cancel_run`；resume、relaunch 各一條（失敗 run 用 `test_resume_entrypoints.py` 的既有夾具），resume 的 `params`／`extra_config` 在確認呼叫裡被改 → `changed`。
- **TCM-11** `a_request_of_another_kind_is_rejected`：launch 的 id 拿去給 cancel 帶 true → 被拒、無 job、該列仍 pending。
- **TCM-12** `chat_is_not_a_form_or_page_or_forget_channel`：`actions.approve(..., confirmed_by=actions.CHAT)` 被拒且不寫；`forget` 工具 schema 沒有兩個新參數；`/c/<id>` 的 POST 仍把列標成 `PAGE`；表單 `answer=form_answer()` 仍標 `ELICITED`（既有 tc01、tc_c* 保持綠）。
- **TCM-13** `browser_chat_never_sees_the_chat_arguments`：`chat_tools.tool_specs()` 中 launch／cancel／resume／relaunch 的 properties 不含 `request_id`、`user_confirmed`；全部 spec 文字不吃 `BANNED_WORDS`。
- **TCM-14** `schemas_gain_exactly_two_optional_fields_on_exactly_four_tools`：四個工具的 properties＝舊集合 ∪ `CHAT_ARGS`；`user_confirmed` 是 boolean、預設 False；`request_id` 是 string 或 null；`required` 與舊相同；其餘工具與 `forget` 的 schema 與舊相同。
- **TCM-15** `the_audit_says_chat`：核准後那一列 `channel=='CHAT'`、`confirmed_at` 非空、`caller_user_id==ann.user_id`、`sha256` 等於 bundle 的雜湊；`find_approved` 找得到 CHAT 列、找不到 channel 為其他字串的列（通道清單是白名單）。
- **TCM-16** `queue_refusal_keeps_the_audit`：讓 `jobs.enqueue_confirmed` 拒絕 → 列為 void 且 `channel=='CHAT'`、`confirmed_at` 保留。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
**規則 A（工具 schema／拒絕 yes 欄位的測試）**：允許集合只加 `CHAT_ARGS`，且**只限 launch、cancel、resume、relaunch 四個**；其餘 yes 類名稱（`yes`、`confirm`、`confirmed`、`approve`、`approved`、`送出`、`ok`、`agree`、`force`、`skip`、`accept`、`void`）照舊禁止，`forget` 與唯讀工具照舊零 yes 欄位。regex 型測試（含 `confirm`，會吃到 `user_confirmed`）在比對前先 `props - CHAT_ARGS`，**不准**改 regex 本身。
- `platform/tests/test_resume_edit_params_platform.py:430-442`（resume 恰為 `{"run_name","params","extra_config"}`、relaunch 恰為 `{"run_name"}`、`required==["run_name"]`、denylist）
- `platform/tests/test_resume_entrypoints.py:21,53-57`（`YES_FIELDS`、`required`）
- `platform/tests/test_human_channel.py:154-166`（`test_tca08_*`）
- `platform/tests/test_dataset_launch.py:203-215`（launch 恰為舊集合∪dataset 欄；regex）
- `platform/tests/test_http_site_samplesheet.py:456-460`（`test_tc048_no_argument_can_say_yes`）
- `platform/tests/test_station_launch.py:732-735`（launch 屬性集合）
- `platform/tests/test_launch_platform.py:306-310`、`platform/tests/test_keep_submissions.py:706-709`（`saying_yes`）；`test_keep_submissions.py:478`（forget 屬性，**不改**，只確認仍綠）
- `platform/tests/test_mcp.py:67`、`test_mcp_run_file.py:332`、`mcp/test_mcp_contract_tools.py:226,243`、`mcp/test_mcp_contract_writes.py:196`、`test_actions_layer.py:35-36,220-228`、`test_oauth_mcp.py:332`、`test_pat.py:284`、`test_station_envs.py:410`（執行者逐一看，只有真的紅才改，改法同規則 A）
- `platform/tests/mcp/snapshots/tools.json`：重生，PR 說明列 diff（只應多出四個工具各兩個欄位）。

**規則 B（釘住句子的測試）**：新句子必須仍含這些子字串：`does not start anything until the person says yes`、`you cannot say it for them`、`(in the terminal, abf-platform launch, cancel, resume and relaunch ask the same way)`、`The tool forget only asks too: it deletes nothing until the person says yes in their own client's form.`、`deletes nothing until the person says yes`、`Each time asks the person and waits for their yes`（operational skill）。
- `platform/tests/test_resume_edit_params_words.py:26-40,60`（NEW／OLD 指令全文常數更新為新 `FIXED_SENTENCE`；`:38` 的必含子字串不動；≤ 2048 不動）
- `platform/tests/test_keep_submissions.py:844-852`（tc107，五個工具名、009e 句、≤ `MAX_BYTES`）
- `platform/tests/test_resume_entrypoints.py:20,61-69`（SENTENCE；tc136 三處：工具 description、`routing_instructions`、`build_server(...).instructions`）
- `platform/tests/test_guidance.py:64-121,262-271`、`test_actions_layer.py` 的 instructions 相等斷言
- `tests/skill_runs_uses_actions_test.sh`（TC-012，runs skill 的反引號限制）、`tests/platform_direction_docs_test.sh`／`tests/platform_storage_doc_test.sh` 對 docs 的釘字：先 grep 再改，改法＝只加句子、不刪被釘句。
- 執行前先跑 `git grep -n "could say yes\|cannot say it for them\|FIXED_SENTENCE" -- platform/tests tests`，把命中全列進 ledger。

**規則 C（閘門測試：改寫成新意義，不是刪）**
- `test_human_channel.py::test_tch09_nothing_reaches_the_queue_through_the_tools_without_a_person`（:581）：保留原迴圈（`ann` 與 `None`、launch 與 cancel、四種 variants，最後 `w.jobs()==[]`），**新增**「帶 `user_confirmed=True` 但沒有 pending／別人的 id／過期的 id 也不排隊」；改名請保留前綴 `test_tch09_`（`constitution_6_test.sh:63` 與 `test_platform_parts.py:370-377`〔SC-29〕靠前綴找）。
- `test_confirm_page.py::test_tch09_b_c_nothing_reaches_the_queue_through_the_web_without_the_owner_pressing`（:354）：不變，確認仍綠（網頁攻擊者仍排不了隊）；`paths` 清單不用加。
- `test_tca14_*`（`test_human_channel.py:243`）、`test_actions_layer.py::test_tcb04_*`／`test_tcb08_*`（:325,359）、`test_resume_entrypoints.py::test_tc142_*`／`test_tc144_*`、`test_keep_submissions.py::test_tc034_*`／`test_tc037_*`／`test_tc038_*`：預期**不變仍綠**；若紅，只准加「CHAT 也被拒」的斷言，不准放寬。`test_tcf10_f11_*` 不相關，不動。
- `tests/constitution_checks_exist_test.sh`、`tests/constitution_6_test.sh`：Check 行加 `test_tcm` 後仍須綠。

**規則 D（版本行 6.2.0 → 7.0.0，只改字串）**
- `tests/charter_v4_workflow_test.sh:84`（精確版本行；:27-31,117 的 6.2.0 條目檢查不動）、`tests/constitution_scope_test.sh:40`（版本文字）與 `:292`（TC-E5 精確版本行；TC-E9 的 6.2.0 條目檢查不動）、`tests/platform_direction_docs_test.sh:52-54`。新字串須與憲法檔尾逐字相同，「Last Amended」用執行當日。
- `tests/dev_workflow_test.sh` 也讀憲法：跑過確認，紅才改。

## 完成標準（done when）
- 自動：TCM-01～16 綠；全套綠（`tests/run_all.sh`，WSL）；`git diff --name-only` 只含「範圍：檔案」；`.github/`、hooks、`plugin.json`、`platform/abf_station/`、`web*.py` 零 diff；`git diff origin/v3 -- platform/abf_platform/confirm.py` 證明 ELICITED／PAGE 路徑的程式行沒有改（只有加參數與 CHAT 分支）。
- **爆炸半徑證明（閱卷必交）**：(1) 列出所有能呼叫 `confirm.approve` 的位置與各自的 channel 字串，證明 `"CHAT"` 只出現在 `_ask` 的確認分支；(2) 列出所有能把模型參數送進四個工具的入口（stdio、HTTP MCP、PAT、OAuth 連接器、網頁聊天 `/chat`），逐一說明誰能填 `user_confirmed`（結論應為：任何 MCP client 的模型都能填，這是 CHAT 的本質；網頁聊天靠剝 schema，仍可被手工偽造呼叫繞過，見 Q2）；(3) 證明任何入口都無法讓別人的 id 或沒給人看過的 bundle 被核准（TCM-02／04／06／11）。
- 憲法：7.0.0 條目六段依序、`**Version.** MAJOR`、引用「照3.」；`constitution_scope_test.sh`、`constitution_6_test.sh`、`constitution_checks_exist_test.sh`、`charter_v4_workflow_test.sh`、`platform_direction_docs_test.sh`、`dev_workflow_test.sh` 全綠。
- 手動（`docs/TESTING.md` 新增步驟）：用只有 stdio＋HTTP MCP 的 client（不開網頁）對測試平台做一次 launch：看摘要→在對話回「送出」→AI 帶 id 再呼叫→收到工作編號；`confirmations` 表該列 `channel='CHAT'`。
- 文件：`docs/PLATFORM.md`、`CHANGELOG.md`、三個 skill 各加 CHAT 一句。

## 環境事實
- 核准入口只有 `confirm.approve`（`confirm.py`）；`_ask`（`actions/__init__.py`）是表單與 pending 的共同入口；`_finish_launch` 的順序是 `find_approved(include_spent=True)` → `check_run_name` → `_cloud_check` → `_ask`。`create_pending` 對同一人、同內容、剩餘 > `REUSE_MIN_SECONDS`(60) 的 pending 會回舊的 id；每人最多 `MAX_OPEN_PENDING`(10) 個。
- `request_forget` 沒有 pending 列、只收表單（`forget(... confirmed_by=ELICITED ...)`），所以不在本片。`_require_human` 與公開 `actions.approve` 的白名單不含 CHAT，是刻意的。
- `guidance.FIXED_SENTENCE` 上限 `MAX_BYTES=2048`，是 MCP 連線時交給模型的路由說明。
- 夾具：`human_harness.World`（`w.user/launch/call/mcp/hand_over/jobs/confirmations/clock`）；`w.launch(caller=, answer=, **over)` 的 `over` 併進工具參數（`choices` 以 `c.update(over)` 合併，所以 `request_id`、`user_confirmed` 可直接傳）；時間用 `w.clock.t += N`（先例 `test_confirm_page.py:142`）。
- 保護路徑：本任務改 `.specify/memory/constitution.md`（保護路徑）→ risk L、tier A。`docs/` 只動列出的檔；`CONTEXT.md` 與 ADR 有被測試釘字（`platform_direction_docs_test.sh:470,491,504,533`），不動。
- **PITFALLS 已查，無相符項**（`docs/PITFALLS.md` @ origin/v3，2556 行，以 confirm／approve／elicit／channel／mcp_server／guidance／constitution 等關鍵字比對；根目錄無 `PITFALLS.md`、無 `docs/solutions/`）。executor 開工前自己再 grep 一次：`git grep -n -i "confirm\|channel\|FIXED_SENTENCE\|constitution" origin/v3 -- docs/PITFALLS.md`，有新增項要在 ledger 引用。
- 殘留風險（要寫進憲法與 PR）：CHAT 的 yes 由模型轉述，平台看不到對話；模型可以自填 `user_confirmed=true`。限縮：必須先有一個真的 pending（人被告知過的摘要）、同一人、內容雜湊相同、10 分鐘內、一次性、稽核記 CHAT。**不能**阻止「模型在人沒回覆時自己填 true」；這比表單／網頁弱，維護者已選此取捨（「照3.」）。

## 不做
- 不做 `forget`／`clean_work` 的 CHAT（沒有 pending 列、設計是表單限定；若要加是後續片，要另改 `request_forget` 與 `_require_human`）。
- 不改網頁 `/c/<id>` 與 PAGE 的任何行為；不新增 HTTP 路由；不新增 MCP 工具；不加 DB 欄位或表。
- 不改 `.github/`、hooks、`plugin.json`、`platform/abf_station/`、`CONTEXT.md`、`docs/adr/*`、`docs/PRINCIPLES.md`、`docs/ROADMAP.md`。
- 不修舊憲法條目；不放寬任何既有拒絕。
- **建議但需維護者另點頭（本片都不做）**：①每人每日送出上限；②核准前顯示 SU 預估；③client 能顯示表單時拒絕 CHAT（強迫走表單）；④伺服器端標記網頁聊天來源，使其呼叫一律不得帶 `user_confirmed`；⑤`/c/<id>` 頁面顯示「此申請可被 CHAT 核准」並提供「作廢」鈕；⑥CHAT 核准後通知（Slack／信）給使用者；⑦CHAT 核准要求回覆文字原文留存（現在只存旗標，不存對話）；⑧`forget` 納入 CHAT 的評估。

## 裁決（planner 的決定；Q 開頭的是要 developer-agent 回覆的）
1. 新參數名定為 `request_id`、`user_confirmed`（不用 `confirm`／`approve` 等已被 denylist 列名的字）；`user_confirmed` 仍會撞到含 `confirm` 的 regex 測試，故用 `CHAT_ARGS` 做明列例外（規則 A）。
2. hash 不符走新狀態 `changed`，列留 pending（不作廢），讓使用者改回參數可重試；別人的 id 一律 `not_yours` 且不洩 job id。
3. CHAT 不進 `_require_human`、公開 `actions.approve`、`forget`、`clean_work`。
4. 版本定 7.0.0（MAJOR）：重新定義 I.2「三條」與 Safety Net 的「AI 不能」，與 5.0.0／6.0.0 先例一致。
5. 不需要 migration，理由：`confirmations.channel` 是自由字串。
- **Q1（需回覆）**：憲法修正案要維護者用自己的話同意。「照3.」是選方案，不是對修正案全文的同意。要不要在合併前把 I.2／Safety Net／7.0.0 的最終全文給他看並取一句「同意」放進 Approval？（預設：要；沒有他的話，PR 停在 draft。）
- **Q2（需回覆）**：網頁聊天（014a）的呼叫無法在伺服器端與其他 MCP client 區分，剝 schema 擋不住有心人手工偽造呼叫。接受這個殘留風險（建議清單④），還是本片就要加伺服器端標記？（預設：接受，列後續。）
- **Q3（需回覆）**：stdio（`caller is None`）預設**拒絕** CHAT（沒有帳號可綁、稽核無主）。要不要為純本機單人開例外？（預設：不開。）
- **Q4**：`Last Amended` 與 7.0.0 條目日期用執行當日，三個 shell 測試的精確字串跟著改；若合併延到隔日，要再改一次。

### developer-agent 回覆（2026-11-04，經追進度 session 轉達）
- Q2：接受殘留風險（列後續）。Q3：stdio 預設拒絕 CHAT，不開例外。Q4：日期用執行當日（2026-11-04）。
- Q1 流程定案（他同意）：做完後把憲法新條文全文給他看，他回「同意」才合併；這是流程同意，不是對條文本身的同意。條文定稿後通知「追進度」session 轉全文給他。
- Q1：憲法全文的「同意」由追進度 session 向維護者取；**PR 只開 draft、不准 `--auto`、不准 merge，等通知**。executor 在憲法 Approval 欄位留待填空並在報告註明。

## 裁決（自動補，2026-11-05）
針對 verifier 退回的七點（planIssues），逐點定案；與前面「作法」衝突時以本節為準。

1. **阻擋一（分支不在 v3）**：worktree `wt/mcp-chat-confirm` 的 HEAD 是 847475ce，與 origin/v3 的共同祖先是舊的 c39f42bf。executor 第一步：把分支重建在目前的 `origin/v3`（查證時為 5b9c8d77，憲法 6.2.0），`git fetch origin` 後 `git rebase origin/v3`（或從 origin/v3 開新分支再換過去）。確認 `.specify/memory/constitution.md` 為 6.2.0，且 `platform/abf_platform/actions/`、`elicit.py`、`guidance.py`、`web*.py`、`human_harness.py` 都在，才開始寫碼。frontmatter 的 base 改讀：`origin/v3`（以開工當下的 HEAD 為準；起草時為 0b293be，驗證時為 5b9c8d77）。測試題不依賴行號，rebase 後 verifier 重新確認即可，題目文字不改。
2. **阻擋二（CLAUDE.md 缺「For the executor and verifier」）**：是第 1 點的後果，origin/v3 的 CLAUDE.md 第 206 行起有這一節；rebase 後自然補上。rebase 前 verifier 不設「合約已確認」是正確的。CLAUDE.md 不在範圍內，executor 不動它。
3. **阻擋三（CLAUDE.md「Never edit during implementation: …the constitution…」與本任務衝突）**：本任務是 tier A 修憲任務，對這一條有明文例外，因為維護者已選定「照3.」（新增 CHAT 通道）並要求憲法 7.0.0；該規則是防一般功能實作時順手改憲法，不是禁止走修憲流程。具體規定：
   - 只准改的憲法段落就是「範圍：檔案」所列（I.2、Safety Net 與其 Check 行、新增 7.0.0 條目、檔尾版本行）；其餘一個字都不准動，舊條目不修。
   - 由 executor 依「作法」第 19～22 點起草憲法文字，不是維護者。草案完成後由 developer-agent 轉「追進度」session 把全文給維護者看。
   - **Approval 欄在維護者用自己的話同意之前**，寫成明確的待填標記：`**Approval.** PENDING: 維護者尚未對修正案全文表示同意（「照3.」只是選方案）。合併前必須由維護者親口同意後補上其原話。` 不得寫「已同意」，不得杜撰引言；「照3.」可引為選方案的依據，不得當成對全文的同意。
   - PR 只開 draft，不加 `--auto`，不 merge；維護者同意後由 developer-agent 補 Approval 原話才轉 ready（對應 TC-102）。
   - executor 報告與 ledger 寫明「本任務依上述例外修改憲法」；verifier 在 ACCEPTANCE 模式檢查 `git diff` 的憲法部分沒有超出上列段落。
4. **非阻擋（Safety Net 括號原文）**：作法第 20 點的引文更正為 v3 原文：(today `launch`, `launch_pipeline`, `cancel`, `resume`, `relaunch` and `forget`)，有反引號、含 `launch_pipeline`。這一段必須與 base 逐字相同（TC-088），不得改成沒有反引號或少了 `launch_pipeline` 的寫法。`constitution_6_test.sh` TC-045 用 regex 解析它，要恰等於已註冊的寫入工具。
5. **非阻擋（日期）**：今天是 2026-11-05，不是先前回覆的 2026-11-04（Q4 的答覆作廢）。規則：executor 開工當天執行一次 `date +%F`，把結果定為唯一的 `<日期>`，記在 ledger 第一行；7.0.0 條目標題、檔尾 `Last Amended`、三個 shell 測試的版本字串必須是同一字串（TC-097、TC-098）。預期為 2026-11-05；若實際開工在別天就用那一天，不跨日改，合併延期也不再改。
6. **非阻擋（手動驗證方式）**：同意。`docs/TESTING.md` 只新增一個端到端手動步驟（TC-056）。其餘手動題（git diff 範圍、憲法文字逐句、爆炸半徑證明）沿用 4.1.0 先例，由驗收者在 ACCEPTANCE 模式檢查並把證據寫進報告，不寫進 TESTING.md。
7. **非阻擋（`user_confirmed=true` 沒有 request_id）**：依作法第 6 點字面：一律拒絕，不建 pending、不寫任何列、不排 job，**也不跳表單**（即使 client 支援表單）。回 `_no("未送出：…")`，訊息請 AI 先不帶 `user_confirmed` 發起申請取得 request id。符合 TC-007，不需改題。表單與待確認只由沒有 `user_confirmed=true` 的第一次呼叫觸發。

## 裁決（2026-11-05 第二輪，developer-agent；與前面衝突以本節為準）
1. **分支**：舊 worktree 分支與 v3 無法乾淨合併，作廢；改用新 id `mcp-chat-confirm-v3`、分支 `feat/mcp-chat-confirm-v3`，直接從 origin/v3 開（以後 PR 取代舊分支）。「裁決（自動補）」第 1 點的 rebase 步驟不再需要；TC 編號與題目沿用。
2. **launch_pipeline**：選 (a)。本任務**不**替 `launch_pipeline` 加 `request_id`／`user_confirmed`，它維持只能走表單／網頁、未經人確認仍拒絕；只動 launch、cancel、resume、relaunch 四個工具（TC-052 恰好四個維持）。
3. **參數改了但 request_id 相同**：先比對內容雜湊，不符就回 `changed`（不得回舊 job 編號）；比對順序＝雜湊檢查在「已 confirmed → already」之前。補一條測試。
4. TC 舊編號對照（TC-007→012、056→064、088→076、097/098→085、102→081/089）以 verifier 重編後的 test-case.md 為準，plan 內舊編號一律照此讀。
5. 爆炸半徑 (1)：能「傳 CHAT 進 `confirm.approve` 去核准」的呼叫端只有 `_ask` 的確認分支；其他出現處是定義或白名單，同意 TC-100 的解讀。

## 裁決（自動補，2026-11-05 第三輪；與前面衝突以本節為準）
針對 verifier 第三次退回的七點（planIssues）逐點定案。維護者不需另外決定任何一點。

1. **阻擋（worktree 分支不在 origin/v3）**：以第二輪裁決 1 為準，且 executor 開工前必須先做到，不是只寫在計畫裡。步驟：在 `wt/mcp-chat-confirm-v3` 把 `feat/mcp-chat-confirm-v3` 重建在目前的 `origin/v3` 之上（`git fetch origin` 後從 origin/v3 開分支，或 rebase），並把 `plan.md`、`specs/mcp-chat-confirm/ledger.md` 帶上去。開工前自我檢查全部成立才可寫碼：`git merge-base HEAD origin/v3` 等於 `origin/v3` 的 HEAD；`.specify/memory/constitution.md` 為 6.2.0；`platform/abf_platform/actions/`、`elicit.py`、`guidance.py`、`platform/tests/human_harness.py` 都存在；根目錄 CLAUDE.md 有「For the executor and verifier」節。通過後由 developer-agent 請 verifier 重新確認，才把合約狀態改成「合約已確認」。在那之前 executor 不動工。TC 題目已按 origin/v3 事實寫好，不重寫。
2. **作法第 11 點與第二輪裁決 3 衝突**：以裁決 3 為準，作法 11 的順序改為：① not_found → ② 呼叫者不符（含 `caller_user_id is None`）→ not_yours → ③ 列已 confirmed：先比 `kind`／`sha256`，不符回 `changed`（列不動，不回 job id），相符才回 already（含 job id）→ ④ void → ⑤ expired（pending 且逾 600 秒；列標 void）→ ⑥ pending 且 `kind`／`sha256` 不符 → `changed`（列維持 pending、不排 job）→ ⑦ 既有存檔完整性檢查 → ⑧ 翻 confirmed 並排隊。雜湊不符與 void／expired 同時成立時，void／expired 優先（作廢或過期的列重試也沒用，回 `changed` 會誤導 AI 去重試）；只有 confirmed 與未逾時的 pending 才做雜湊檢查。固定的兩點不變：呼叫者檢查在 already 與 void 之前；雜湊檢查在 already 之前。其餘訊息規則（作法 12）不變。對應 TC-021、TC-033。
3. **舊 TC 編號**：舊 test-case.md 已作廢。本計畫內出現的舊編號一律依 verifier 的對照改讀新編號：TC-007／012→TC-012、013；TC-052→TC-048；TC-056／064→TC-080；TC-088／076→TC-064、TC-070；TC-097／098／085→TC-068；TC-102／081／089→TC-067、TC-071。executor 以新 test-case.md（TC-001～TC-081）為準。計畫中指「既有測試」的編號不改，也不要與新編號混淆：`constitution_6_test.sh` TC-045、`test_scope.py` TC-070、`skill_runs_uses_actions_test.sh` TC-012。
4. **範圍清單的 `request_pipeline_launch`**：從「範圍：檔案」`actions/__init__.py` 那一行刪掉 `request_pipeline_launch`。依第二輪裁決 2，`launch_pipeline` 不加 `request_id`／`user_confirmed`，其 schema 與行為完全不變（TC-040）；只改 `request_launch`、`request_cancel`、`_request_attempt`、`request_resume`、`request_relaunch` 的簽章。executor 不得照字面替 `request_pipeline_launch` 加參數。
5. **專長守則（backend）要求的額外測試**：納入本任務完成標準。executor 在 `platform/tests/test_chat_confirm.py` 另補測試，函式前綴 `test_tcm`，對應 TC-072～TC-075：對等性（同一動作在 CHAT 與表單／網頁得到相同的排隊結果與稽核欄位）；錯誤訊息與日誌（形狀見第 7 點）；密鑰不外洩（回應與日誌不含 token、密碼、完整路徑）；處理函式不得有第二份邏輯（CHAT 與其他通道共用 `confirm.approve`，`mcp_server.py` 的四個工具不自行核准或排隊）。這些測試與 TCM-01～16 一樣先寫、先紅。
6. **憲法條文的手動驗證**：維持第一輪裁決 6 的取捨，不新增自動測試。TC-063、064、066、067、069、071 由驗收者讀 `git diff` 並把證據寫進報告。`docs/TESTING.md` 只新增一個端到端步驟（TC-080）。根目錄 CLAUDE.md「實作中不得改憲法」由第一輪裁決 3 的明文例外覆蓋；驗收者用 TC-069 檢查憲法 diff 沒有超出「範圍：檔案」所列段落。Approval 欄維持待填標記，PR 只開 draft。
7. **拒絕訊息的用詞**：除 `changed`（作法 12）與沒有 request_id（第一輪裁決 7）已規定內容外，no pending、not_yours、expired、stdio 的訊息一律：以「未送出：」開頭，用一句白話說明原因，再用一句說明下一步（例如「請重新發起申請」）；不含 job_id、堆疊、檔案路徑、SQL。TC-074 只驗形狀。用詞是否夠白話列為 PR 說明的審閱項，由維護者在看 draft PR 時順便看，不擋實作。

## 裁決（自動補，2026-11-05 第四輪；與前面衝突以本節為準）
針對 verifier 第四次退回的七點逐點定案。維護者不需另外決定任何一點。

1. **阻擋（指定的 worktree 不在 origin/v3）**：不改計畫內容，改正交付對象。實測：`wt/mcp-chat-confirm` 與 `wt/mcp-chat-confirm-v3` 都停在舊祖先 c39f42bf（憲法 4.1.0、沒有 `actions/`），兩者作廢，verifier 與 executor 都不得使用。可用的是 `wt/mcp-chat-confirm-v4`（分支 `feat/mcp-chat-confirm-v4`）：憲法 6.2.0、有 `actions/`、CLAUDE.md 有「For the executor and verifier」節，其祖先 5b9c8d77 是目前 origin/v3（cbc47b40）的祖先，但落後幾個提交。因此 executor 開工前先 `git fetch origin && git rebase origin/v3`，使 `git merge-base HEAD origin/v3` 等於 `origin/v3` 的 HEAD；再做第三輪裁決 1 的四項開工前自我檢查。developer-agent 請 verifier 改讀 `-v4`（rebase 後）重新確認，通過前不設「合約已確認」。第二、三輪裁決寫的 `-v3` 一律改讀 `-v4`。
2. **計畫文字更正（以本節為準）**：①「範圍：檔案」`actions/__init__.py` 那行的 `request_pipeline_launch` 視為已刪，依第三輪裁決 4，`launch_pipeline` 與 `request_pipeline_launch` 一個參數都不加（TC-040）。②「作法」第 11 點的核准順序作廢，唯一有效順序是第三輪裁決 2 的八步：not_found、not_yours、confirmed 先比雜湊（不符 changed，相符 already）、void、expired、pending 雜湊不符 changed、存檔完整性、翻 confirmed 並排隊。void／expired 優先於 changed；呼叫者檢查在 already 與 void 之前；雜湊檢查在 already 之前。
3. **TC 編號對照**：確認 verifier 的重編（TC-001～081）為準；072 對等性、073 密鑰與日誌、074 錯誤訊息形狀、075 無第二份邏輯。第三輪裁決 5 與「專長守則」列的順序只是內容清單，不綁編號順序。
4. **憲法 Approval 只有占位**：維持第一輪裁決 3 與 Q1 的既定做法，不新增決定。Approval 欄寫 PENDING，PR 只開 draft，維護者看全文後以自己的話同意才補原話並轉 ready（TC-067、TC-071）；「實作中不得改憲法」的例外由維護者看 draft PR 時順便確認。這是既有流程，不需再問。
5. **沒有 spec.md**：確認只用 plan.md；維護者原話兩句與 developer-agent 轉述的硬條件已全部對到 TC，不另補 spec。
6. **日期是變數**：確認 TC-068 只要求同一字串一致。開工當天執行一次 `date +%F` 定案（第一輪裁決 5），不鎖死某一天、不跨日改。
7. **其餘**：七點皆非維護者產品決定，needsHuman 為否。

## 裁決（自動補，2026-11-05 第五輪；與前面衝突以本節為準）
針對 verifier 第五次退回的五點逐點定案。實測：`wt/mcp-chat-confirm` HEAD 77b2d783，merge-base c39f42bf，憲法 4.1.0，作廢；`wt/mcp-chat-confirm-v4`（分支 `feat/mcp-chat-confirm-v4`）憲法 6.2.0、有 `actions/`、`elicit.py`、`guidance.py`、`web*.py`，base 是 5b9c8d77，落後本機已知的 origin/v3 共 45 個提交。

1. **阻擋（worktree 作廢）**：本次工作流指到 `wt/mcp-chat-confirm` 是交付對象錯，不是計畫錯。唯一可用路徑是 `C:/Users/marvi/Desktop/agentic-bioflow/wt/mcp-chat-confirm-v4`。developer-agent 把 verifier 的 CONTRACT 路徑改成它；verifier 不得讀 `wt/mcp-chat-confirm`、`-v3`。為使 `git merge-base HEAD origin/v3` 等於 `origin/v3` 的 HEAD，開工前先 `git fetch origin && git rebase origin/v3`（v4 目前仍落後），再做第三輪裁決 1 的四項自我檢查，通過後 verifier 才設「合約已確認」。
2. **阻擋（流程，缺 CLAUDE.md 節）**：v4 的 CLAUDE.md 第 206 行起有「For the executor and verifier」。verifier 在 v4 讀該節，取得 test-case 範本、單檔與全套測試指令、禁止指令與 calibration failures，把自訂格式的 test-case.md 依範本重排；題目內容（TC-001～081）不改。CLAUDE.md 不在範圍內，不動。
3. **非阻擋（多輪裁決疊加）**：不在本檔逐處改寫前文，以免與已完成的 TC 對照錯位；executor 讀法固定：作法第 11 點、範圍清單的 `request_pipeline_launch`、frontmatter 的 `base`、舊 TC 編號，一律以第三、四輪裁決為準（八步順序、不改 `launch_pipeline`、base 讀 `origin/v3` 開工當下 HEAD、TC-001～081）。developer-agent 於 rebase 後若要把這三處就地改成最終版，只准改文字不改語意；這是整理，不需維護者決定。
4. **非阻擋（憲法與爆炸半徑手動驗證）**：沿用第一輪裁決 6、第三輪裁決 6：TC-063、064、066、067、069、070、071 與 TC-081 由驗收者讀 `git diff` 判斷，證據寫進報告，不新增自動測試。
5. **待維護者（Approval PENDING）**：沿用第一輪裁決 3、Q1 與第四輪裁決 4：Approval 欄寫 PENDING 占位，PR 只開 draft，不加 `--auto`、不 merge；維護者看全文後以自己的話同意，才補原話並轉 ready。它擋合併不擋合約，不需新決定。needsHuman 為否。

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

## 裁決（2026-11-06 凌晨，developer-agent）
TC-U28 已由維護者核可刪除並合併（PR #369，他 11-05 回「刪」）。前一輪卡在 TC-U28 的紅燈解除。開工第一步：`git fetch origin && git merge origin/v3`（衝突時兩邊意圖都保留，工具數／唯讀數斷言照合併後總數重算，絕不弱化）；然後跑全套直到乾淨全綠，才寫 GREEN。逾時的 shard 只重跑逾時那片一次。不需要改任何測試來迴避 TC-U28（它已不存在）。
