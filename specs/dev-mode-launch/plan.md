---
id: dev-mode-launch
title: 「預算內免確認」：使用者在設定頁自設 NCHC nano4 的單次與每月 SU 門檻，門檻內 AI 提出的 launch／resume／relaunch／cancel 直接成立（通道 BUDGET）；雲端花錢永遠要確認（憲法 8.0.0 修正案）
tier: A
kinds: backend
risk: L
lane: L50-dev-mode
branch: feat/dev-mode-launch
base: origin/v3（開工前 fetch，重查所有行號）；必須排在 PR #376（CHAT／憲法 7.0.0）合併之後，見裁決 A
source: 維護者 2026-10-13、2026-11-03、2026-11-07 裁示；10-15 訪談（每次免確認送出列入每日摘要）；ADR 0011（10-23）
serves: M2-DEVMODE（phase 1）；依賴 M1-CHATCONFIRM（PR #376）
rev: 2026-11-07 改寫（取代 11-03 版「平台主機終端機開旗標」設計，見裁決 B）
---

# dev-mode-launch

> A 級（放寬安全網）＋ risk L：必須維護者親口同意憲法文字才能合併；PASS 後多跑一次 Opus 對抗審。

## 裁決
**A. 需要維護者親口同意的憲法文字（白話摘要，供 lead 轉給他看）**

現況：憲法 7.0.0（聊天內核准 CHAT 通道，PR #376）還沒合進 v3，v3 憲法仍是 6.2.0。PR #376 是正式 PR（非 draft）、可合併，7.0.0 條目的 Approval 欄已寫「2026-11-06 維護者說『好』」。卡的是 CI 紅：`shard 4/4` 的 `test_chat_confirm.py::test_tcm_47_no_new_column_no_new_table` 把「基準資料庫結構雜湊」寫死，v3 之後加了新欄位（012a 設定頁的兩個使用者欄位）所以對不上，需要 rebase 後重算；`gitleaks`、`pip-audit` 兩個資安檢查在 v3 自己的跑法上也是紅（pip-audit 是參數用錯，gitleaks 掃到歷史 34 筆），不是這個 PR 造成。本計畫的修正案是 8.0.0，疊在 7.0.0 上，所以 #376 不先合併，本片不能開工合併。

這次要請他逐字同意的白話內容（共五點）：
1. **新增第五種「同意」**：使用者本人事先在自己的設定頁填兩個數字——「單次 SU 上限」「每月 SU 上限」。兩個都填了以後，AI 提出的送出（launch、resume、relaunch）若是在國網 nano4、預估 SU 不超過單次上限、且「本月已用＋這次預估」不超過每月上限，平台就直接排隊，不再等本人逐次按好。平台把這種同意記成 `BUDGET`，記下時間、是誰、當時的預估與兩個上限，每日摘要可以列出來。
2. **沒設定就一律要確認**：兩個數字缺任何一個、預估算不出來（例如這個 pipeline 還沒成功跑過、沒有歷史可估）、本月用量算不出來，都照今天一樣逐次要本人按。
3. **花錢的永遠要確認**：任何雲端（Google Batch 等）的送出，不管數字設多少，都照今天逐次確認。`forget`（刪紀錄）與清工作目錄也永遠要本人。
4. **只有本人能設數字**：數字只能由本人登入後在設定頁（網頁，PAGE 通道）修改；AI、MCP 工具、聊天頁的模型、token 都碰不到。AI 自己不能把上限調高。
5. **要誠實寫進憲法的限制**：這比逐次確認弱——本人是「事先授權一個額度」，額度內 AI 可以自己送；預估可能不準（以歷史為準，不是保證）；自動續跑（Q31，第二片）也算進額度；取消（cancel）因為不花錢，額度兩項都設了就不再逐次問（維護者 10-13「取消直接開放」，產品模式是否也開放仍未決，見「不做」）。這是 MAJOR 修訂（重新定義 I.2 與 Safety Net），版本 8.0.0，並寫明它與 5.0.0／7.0.0 那兩句關於「待確認請求、token、模型的回答不是通道」的關係。
以上不是我能代為同意的；Approval 欄在他用自己的話同意之前，只准寫 `PENDING`，PR 只開 draft（沿用 #376 做法）。

**B. 設計改寫（11-07 之後）**：11-03 版是「操作者在平台主機終端機開旗標、託管部署拒絕」。Q21 說免確認的門檻「由使用者在設定頁自己設定」，信任根從操作者改成使用者本人，所以改寫為使用者設定頁的兩個 SU 數字；「終端機旗標」與 `ABF_HOSTED` 標記不再是開啟條件。安全網沒有放寬：預設仍是逐次確認（數字未設＝關），雲端花錢與 forget 的規則不變，11-03 版較寬的「任何環境全部免確認」已刪。
**C. 名稱**：v3 已有 012a 的個人「開發模式」開關（`users.dev_mode`、橫幅「國網運算不限制 SU」，`web_devmode.py`）。它是另一件事，本片**不沿用、不改**，也不讓它授予任何免確認；新通道名定為 `BUDGET`，避免與它混淆。
**D. 第二片（本計畫不做，列於「不做」）**：Q31 自動續跑。v3 沒有任何自動續跑程式（`git grep` 無 auto_resume），需要失敗偵測、每個分析的計數與「需要你處理」通知，是一整片。規則先定案：每個分析最多自動續跑一次；第二次失敗改發「需要你處理」通知；自動續跑算入 SU 門檻（超過就改發通知、不自動送）。維護者選 (c)「一律自動」，我方解讀為「自動，但最多一次」，**待他確認適用範圍**。
**E. Q20（樣本表）**：樣本表由 LLM 產生、貼給使用者確認，那是確認輸入，不算逐次確認 run。本片不實作樣本表產生；只保證「樣本表被確認」與「run 被核准」是兩件事——樣本表確認不會被當成 run 的核准，且 run 的 BUDGET 判斷仍照常執行（TC-L）。
**F. 預設答案（需 lead 回覆，未回覆就照此做）**：
- Q-a 預估 SU 的來源：用同一 pipeline 在同一站台的歷史成功 run 取最大值（仿 `cloud_cost.estimate_launch`）；沒歷史就要確認。這表示第一次跑某 pipeline 一定要按。接受嗎？
- Q-b 是否仍在 `ABF_HOSTED` 部署拒絕 BUDGET：預設**拒絕**（不放寬），標記放 H-1 部署包的 systemd 單元 `Environment=ABF_HOSTED=1`，`hosted_deploy_test.sh` TC-016 一字不改。維護者 11-07 沒提託管，若他要託管也開，再改。
- Q-c 取消（cancel）是否納入額度內免確認：預設納入（兩數字都設才生效）。
- Q-d 數字單位 SU，0–1,000,000，`0`＝什麼都不放行。
**G. 憲法 8.0.0 與誰套用**：仿 #376 流程——executor 依明文例外起草憲法文字（I.2 在 CHAT 之後加第五種「事先額度」的定義與限制；Safety Net 的 launch 規則與 write-tool 規則加例外並把 `test_budget_launch.py`（前綴 `test_bg`）加進 Check 行；`(today …)` 括號原文一字不動；新條目 `### 8.0.0 (<開工當日 date +%F>)` 依 7.0.0 風格六段 Rationale／What changes／Sync Impact Report／Impact on existing deployments／Version（MAJOR）／Approval；檔尾版本行）；更新釘住測試（`PINNED_SN_SHA256` 與版本字串）讓全套綠。Approval 欄寫 `**Approval.** PENDING: 維護者尚未對修正案全文表示同意。合併前必須由維護者親口同意後補上其原話。`，PR 只開 draft、不加 `--auto`、不 merge。不得杜撰引言，不得把 Q2／Q21 的轉述當成對憲法全文的同意。
**H. 先後**：開工前 `git fetch origin`，確認 `origin/v3` 已含 #376（憲法為 7.0.0、`platform/tests/test_chat_confirm.py` 存在）；未含則本片不開工（lead 先處理 #376 的 `test_tcm_47` 與資安檢查）。

## 目標
NCHC 驗收期間每次送出都要本人按確認，維護者成為瓶頸。這一片讓使用者自己在設定頁設「單次」與「每月」SU 上限；額度內 AI 的送出直接成立並記為 `BUDGET`，額度外、沒設定、雲端花錢、forget 一律照今天逐次確認。每一筆 `BUDGET` 可由 CLI 列出供每日摘要。額度沒設時行為與今天逐位元組相同。

## 維護者原話（verifier 出題用）
- 2026-10-13：「設計成在開發階段你可以自由送出，實際產品再改回來。取消直接開放」
- 2026-11-03：「開發模式讓 AI 直接送出是對的」
- 2026-11-07 Q2：「nano4 SU 預算內 AI 送出免逐次確認；雲端花錢的動作永遠要確認」
- 2026-11-07 Q21：「免確認的門檻由使用者在設定頁自己設定（單次與每月 SU），沒設定就一律要確認」
- 2026-11-07 Q20：「樣本表由 LLM 產生、貼給使用者確認」（確認輸入，不算逐次確認 run）
- 2026-11-07 Q31：「失敗處理沿用 10-23／ADR 0011 結論『每個分析最多自動續跑一次，第二次失敗改「需要你處理」通知，自動續跑也算入 SU 門檻』」（維護者選 (c) 一律自動；我方解讀自動但最多一次，待他確認適用範圍；第二片）
- 10-15 訪談：每一次免確認送出，都列在開發者的每日摘要裡。
- 上列 Q 句為 lead 轉述，非錄音逐字；若有原文請 lead 換入。

每句至少一條 TC：預設要確認（TC-A）；兩數字缺一就確認（TC-B）；額度內直接成立（TC-C）；單次或月度超過／算不出來就確認（TC-D）；雲端永遠確認（TC-E）；只有本人在設定頁能改數字（TC-G）；forget 與清目錄仍要本人（TC-F）；擁有者規則（TC-H）；每日摘要列表（TC-J）；樣本表確認不等於 run 核准（TC-L）。第二片的 Q31 另出題。

## 範圍：檔案（只准改這些）
**程式（platform）**
- `platform/abf_platform/budget.py`（新）：`limits(tokens_path, user_id)`、`decide(...)`（回「直接成立」或「要確認」與原因）、`is_hosted()`。
- `platform/abf_platform/su.py`：加 `estimate_launch(index_path, platform_path, user_id, pipeline, site, rates)`（歷史最大值；沒歷史回 None 與原因）。不改既有函式。
- `platform/abf_platform/store.py`：`users` 加兩個可為空的 REAL 欄 `auto_su_single`、`auto_su_month`（NULL＝未設），仿 `_migrate_tokens` 補 `step_mode`／`dev_mode` 的迴圈；`confirmations` 加可為空 TEXT 欄 `budget_note`（存當時預估與上限，供摘要），同樣用 `ALTER TABLE` 補欄；新增 `set_user_budget`、`user_budget`（範圍檢查 0–1,000,000，仿 `set_cloud_cap` l.834）。**需要 migration**（見作法 1）。
- `platform/abf_platform/actions/__init__.py`：加 `BUDGET = _Channel("BUDGET")`；`_ask`（launch／cancel／resume／relaunch 共用）與 `_request_attempt` 加預算分支；新增 `get_my_budget`、`set_my_budget`（仿 `get_my_settings`／`set_my_setting` l.1205–1216，`_require_human`，只收 PAGE）。`request_forget`、`forget`、`clean_work`、`_require_human`、公開 `approve` 不改。
- `platform/abf_platform/confirm.py`：`approve` 允許 `BUDGET`（呼叫者必須存在；stdio 無呼叫者不允許）；`find_approved`、`find_attempt` 的 `channel IN (...)` 清單加 `'BUDGET'`（CHAT PR 已加 `'CHAT'`，在其上追加）。
- `platform/abf_platform/cli.py`：新子命令 `auto-send list [--since ISO]`（唯讀）；檔頭 docstring 的子命令清單。
- `platform/abf_platform/web_settings.py`、`web.py`：設定頁個人區加兩個數字欄與「儲存」，新路由 `POST /settings/budget`（CSRF 與 `/settings/personal` 同）；文字放 `web_devmode.py` 的函式內表或同類新檔，**不放** `web_settings.STRINGS`（`test_ce08` 釘它的雜湊）。
- `deploy/` 託管單元檔 `Environment=ABF_HOSTED=1`（依裁決 F Q-b；若 H-1 部署包尚未合併，此項延到它之後並在 ledger 記）。
**測試**
- 新：`platform/tests/test_budget_launch.py`（主要失敗先行測試，檔首 40 行內要有 `# Nothing existing: <理由，≥15 字>`，`test_scope.py` TC-070）。
- 新：`tests/budget_doc_test.sh`（文件與修正案標記）；登進 `tests/run_all.sh`（若以名單列測試）。
- 既有且釘住的，只准加例外案例，**不准刪或放寬既有斷言**：
  - `platform/tests/test_actions_layer.py`：`REFUSED = "no human confirmation channel"`（l.26）；`_hits` 的 AST 掃描（l.83–116）——新的 `BUDGET` 呼叫點要列白名單且只能在 `_ask`／`_request_attempt` 內；`test_tcb04_to_b06_b09_…`（l.325，`BUDGET` 直接餵 `launch`／`cancel` 仍須被拒）、`test_tcb01/02/03/07/08`、`test_srp_k01…`（l.705–722）。
  - `platform/tests/test_human_channel.py`：`test_tch09_nothing_reaches_the_queue_through_the_tools_without_a_person`（l.581，沒設額度時 `w.jobs() == []`）、`test_tca14`（l.243）、`test_tcf10_f11`（schema 禁字，不得新增名為 session／password 的欄位）。
  - `platform/tests/test_confirm_page.py::test_tch09_b_c_…`（l.354）。
  - `platform/tests/test_chat_confirm.py`（PR #376 新檔；合併後才存在）：`test_tcm_47_no_new_column_no_new_table`（寫死基準結構雜湊、確認表欄位、路由清單）與 `BASE_ROUTES`——本片新增欄位與路由時必須**更新基準值並在 ledger 逐條寫明新增了哪一欄、哪一路由**，不得改成只比部分。
  - `platform/tests/test_web_settings_personal.py`（39 處釘 012a 個人區）、`test_web_board.py`、`test_web_wording_sweep.py`、`test_web_v2_skeleton.py`、`test_web_chrome_origin.py`、`test_web_parity.py`（l.176，網頁動作與動作層一一對應）、`test_web_actions.py`、`test_ce08`（釘 `web_settings.STRINGS` 雜湊）、`STYLE_SHA256`（新增 CSS 才改，並只更新預期值）。
  - `platform/tests/test_resume_entrypoints.py`（`test_tc142`、`test_tc144`）、`test_keep_submissions.py`（`test_tc034/037/038`）、`test_owner_binding.py`（l.467）、`test_owner_guard.py`、`test_mcp_server_doc.py`、`test_station_envs.py`（`EXEMPT`、`banned_schema_words`）、`test_resume_edit_params_platform.py`（l.439）、`test_resume_edit_params_words.py`（l.35–38，「does not start anything until the person says yes」「you cannot say it for them」，額度未設時一字不變；本片**不改任何 MCP 工具說明與 `FIXED_SENTENCE`**，通知句只放在請求回傳的 `_queued` 訊息）。
  - `platform/tests/resume_harness.py`、`human_harness.py`、`platform/tests/mcp/snapshots/tools.json`：只准加、不准改；本片不新增 MCP 工具或參數（snapshot 應零 diff）。
  - `tests/no_second_run_state_test.sh`（`LAUNCH_ALLOW` 名單與 28 個自測，只會更嚴不會更鬆；上限存使用者設定，不是執行狀態）、`tests/hosted_deploy_test.sh`（TC-016 env.example 全占位字、TC-017、TC-007：託管標記不放 env.example）、`tests/operations_doc_test.sh`（文件裡每個 `abf-platform <字>` 必須是真的 `sub.add_parser`；`auto-send` 寫進文件前要先有 parser）。
  - 憲法釘住：`tests/constitution_scope_test.sh`（l.40 版本文字、l.292 TC-E5 版本行、TC-E8／E9 條目檢查、`PINNED_SN_SHA256` l.130–151 失敗時印出新指紋）、`tests/platform_direction_docs_test.sh`（l.52–54）、`tests/charter_v4_workflow_test.sh`（l.84）、`tests/constitution_6_test.sh`（TC-045 write-tool 括號 `(today …)` 原文不動、TC-048、RULE2／RULE3）、`tests/constitution_checks_exist_test.sh`（Check 行新前綴 `test_bg`）、`tests/dev_workflow_test.sh`、`CLAUDE.md` 引用版本處。這些依裁決 G 處理。
**文件**：`docs/PLATFORM.md`、`docs/OPERATIONS.md`、`docs/TESTING.md`、`docs/adr/0006-…`（加註）、`CHANGELOG.md`、`skills/launch/SKILL.md`（只加一句，被釘句不動）。
**憲法（見裁決 G）**：`.specify/memory/constitution.md` 只准改 I.2、Safety Net 規則與其 Check 行、新增 8.0.0 條目、檔尾版本行（沿用 #376 的明文例外）。
- **不准碰**：`spec.md`、`test-case*.md`、`docs/ROADMAP.md`、`.github/`、`web_devmode.py` 既有函式與 `users.dev_mode` 語意。

## 作法
1. **資料**。證據：`store._migrate_tokens` 以迴圈補 `step_mode`／`dev_mode` 欄、NULL＝預設；`confirmations.channel` 是無 CHECK 的 TEXT（store.py l.225），`BUDGET` 只是新值。決定：`users` 加 `auto_su_single REAL`、`auto_su_month REAL`；`confirmations` 加 `budget_note TEXT`；全部用 `ALTER TABLE ADD COLUMN`＋「第二個進程先加了也算成功」的同款寫法；舊庫補欄後值為 NULL＝未設＝要確認。測試：舊庫（無新欄）開啟後欄位出現、既有列不變、所有人預設要確認。
2. **只有本人能設數字**。`actions.set_my_budget(tokens_path, single, month, *, confirmed_by=None, caller=None)`：`_require_human` 之後只收 PAGE；`single`／`month` 各為 None（清除）或 0–1,000,000 的數字（bool、NaN、負數、字串拒絕，仿 `set_cloud_cap`）。入口只有 `POST /settings/budget`（登入者本人，擁有者規則：只能改自己）。AST 掃描斷言 `set_my_budget`、`store.set_user_budget` 只被 `web_settings`／`web.py` 的該路由與動作層呼叫；`mcp_server.py`、`chat_tools.py` 內沒有；MCP 工具名單與 `chat_tools.tool_specs()` 沒有含 `budget`／`su`／`limit` 的項目。
3. **決定函式 `budget.decide`**（純函式，傳入已查好的值，便於測）。回「直接成立」只在**全部**成立時：(a) 呼叫者存在且為本人帳號（stdio 無呼叫者→要確認）；(b) 不是 `is_hosted()`；(c) 兩個數字都已設；(d) 種類是 launch、resume、relaunch 且目標 compute env 是 SU 站台（nano4，由 `su.site_of_run`／env 型別判斷），或種類是 cancel；(e) 目標不是雲端環境，且 `cloud_cost` 的雲端檢查路徑不適用（雲端一律要確認，`_cloud_check` 照舊先跑）；(f) `su.estimate_launch` 不是 None 且 ≤ 單次上限；(g) `su.month_total` 不是 None 且 本月用量＋預估 ≤ 每月上限（月界用既有 Asia/Taipei）。任何一項不成立或算不出來，**回「要確認」並照今天走表單／確認頁**，不報錯、不降級。cancel 只要 (a)(b)(c) 與擁有者規則。
4. **動作層分支**。在 `_ask` 與 `_request_attempt` 於 `create_pending` 之後：若 `budget.decide(...)` 成立，**略過表單與確認頁**，直接 `confirm.approve(platform_path, rid, BUDGET.name, caller_id, clock)`，並把預估、兩個上限、本月已用寫進 `budget_note`；回傳與 ELICITED 成立同形的 `_queued` 結果，多帶 `channel: BUDGET` 與一句白話（「在你設定的 SU 額度內，已直接送出。預估 X SU，你的單次上限 Y、本月已用 Z／上限 W」）。`launch()`、`cancel()`、`_require_human` 仍只認 TERMINAL／ELICITED／PAGE（與 CHAT 依 #376 的特例）；`BUDGET` 直接餵它們依舊被拒。`request_forget`、`forget`、`clean_work` 不碰。擁有者規則照舊：`create_pending` 已做，BUDGET 不繞過。
5. **`confirm.approve`**。BUDGET 只在動作層分支內呼叫（爆炸半徑證明的核心）；`caller_user_id is None` 一律 `not_yours`。`find_approved`／`find_attempt` 加 `'BUDGET'`，使重複呼叫回同一個 job。
6. **可見性（每日摘要）**。`abf-platform auto-send list [--since <ISO>]`：列 `channel='BUDGET'` 的每筆，tab 分隔、依時間排序，欄位固定為 `confirmed_at`、呼叫者名稱、種類、run 名稱、確認編號、`budget_note`；沒有則印 `no budget-approved sends`。設定頁顯示目前兩個數字與「未設定＝每次都問你」。**不新增橫幅**（既有 012a 橫幅是另一個旗標）。
7. **託管**。`is_hosted()`＝`bool(os.environ.get("ABF_HOSTED"))`，為真時 `decide` 一律要確認；設定頁註明「此部署不啟用」。
8. **fail-closed**。任何例外（資料庫讀失敗、rates 檔缺、estimate 或 month_total 丟錯）一律當「要確認」，不得變成放行，TC-D 逐項覆蓋。

## 失敗先行測試
`platform/tests/test_budget_launch.py`，先寫、改程式前先跑出紅，紅的輸出貼進 ledger；夾具用 `human_harness.py` 現成寫法，SU 歷史用 `su` 既有測試夾具造 run 與 task 用量。
- TC-A：新使用者（兩欄 NULL）`request_launch`／`resume`／`relaunch`／`cancel` 全回待確認、`w.jobs()==[]`、與基準位元組相同（同 `test_tch09` 斷言）。
- TC-B：只設單次或只設每月 → 全回待確認。
- TC-C：兩數字都設、歷史估 10 SU、單次上限 20、每月上限 100、本月已用 50 → launch／resume／relaunch 各自直接入列，`confirmations.channel=='BUDGET'`、`confirmed_at` 非空、`caller_user_id` 為呼叫者、`budget_note` 含預估與上限；重複同一請求回同一 job。cancel（兩數字都設）直接成立。
- TC-D：預估 30 > 單次 20 → 待確認；預估 10 但本月已用 95（95＋10＞100）→ 待確認；剛好等於上限 → 成立（邊界）；無歷史（estimate None）→ 待確認；`month_total` 為 None → 待確認；`su` 丟例外、rates 檔缺 → 待確認且不洩堆疊。
- TC-E：目標是雲端環境、兩數字設到 1,000,000 → 仍待確認；雲端額度檢查（`_cloud_check`）行為不變。
- TC-F：兩數字都設時 `request_forget`、`clean_work` 仍待確認、資料不動；`launch(…, BUDGET)`、`cancel(…, BUDGET)`、`forget(…, BUDGET)` 直接呼叫被拒（訊息含 "no human confirmation channel"）。
- TC-G：`set_my_budget` 只在 PAGE 成功；以 ELICITED／TERMINAL／None／模型字串呼叫被拒且不寫；AST 掃描（作法 2）；MCP 工具名單與 `tool_specs()` 不含相關項；乙不能改甲的數字；非法值（負數、bool、NaN、字串、>1,000,000）被拒。
- TC-H：乙對甲的 run 在甲設了額度後 cancel／resume 仍被拒。
- TC-I：額度未設時 MCP 工具說明、`FIXED_SENTENCE`、tools.json snapshot 位元組不變；網頁各頁 HTML（首頁、確認頁、runs 頁、設定頁在未設額度時除新增欄位外）與基準比對。
- TC-J：`auto-send list` 列出 TC-C 每一筆，欄位齊全、`--since` 過濾；取消額度後仍能列歷史；沒有則印指定句。
- TC-K：`ABF_HOSTED=1` 時，數字都設也一律待確認。
- TC-L：樣本表確認（既有輸入確認步驟）不產生 `confirmations` 的 run 核准列；額度內 launch 仍由 `budget.decide` 判定；樣本表確認後額度外的 launch 仍待確認。
- TC-M：舊庫 migration 後新欄存在、既有列與設定不變。
- `tests/budget_doc_test.sh`：文件提到的每個 `abf-platform auto-send …` 是真 parser；修正案含 "never" 雲端與 forget、`PENDING`；憲法版本行與條目標題日期同一字串。

## 完成標準（done when）
- 新測試改前紅、改後綠；全套 `tests/run_all.sh` 全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：第一行 `date +%F`；開工前檢查（#376 已合）；`git diff --stat` 只含範圍內檔；既有斷言沒被刪或放寬（逐檔貼 diff，`test_tcm_47` 基準值更新逐條說明）；額度未設時 `confirmations`／`jobs` 行數與今天一致的前後比對；`git grep -n "dev_mode"` 證明既有 012a 開關未被改。
- 爆炸半徑證明（risk L）：(1) 所有能到達 `confirm.approve(..., BUDGET.name, ...)` 的呼叫點（應只有 `_ask`、`_request_attempt` 內的預算分支）；(2) 所有能寫 `auto_su_*` 欄的呼叫點（應只有 `POST /settings/budget` 經 `set_my_budget`）；(3) 逐一列出雲端與 forget 不可能走到 BUDGET 的理由與對應 TC；(4) 能影響 `decide` 輸入的外部來源（歷史 run、rates 檔）與其失敗時都回「要確認」。
- 憲法 8.0.0 草案齊備、Approval 為 PENDING、PR 為 draft；憲法 diff 未超出「範圍：檔案」所列段落（驗收者讀 diff，證據寫報告）。**在維護者親口同意前不得合併。**

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」；憲法限制見該節與 #376 裁決 3 的明文例外。
- 單檔測試：WSL repo 根目錄 `python -m pytest platform/tests/test_budget_launch.py`；Shell 測試 `bash tests/<name>.sh`。
- SU 現況：`su.py` 只能事後由任務用量算 SU（`su_of_tasks`、`run_su`、`month_total`，月以 Asia/Taipei），沒有事前預估；`cloud_cost.estimate_launch`（l.218）是雲端美元版的歷史預估，可仿。ROADMAP 現寫「no NCHC SU cap in dev mode」，指 012a 的個人開關，與本片數字上限是兩件事。
- PR #376（`feat/mcp-chat-confirm-v5`，head 7671b877）：28 個提交、非 draft；CI 紅在 shard 4 的 `test_tcm_47`（結構雜湊過期）與兩個資安檢查（v3 也紅）。PITFALLS 已查（`docs/PITFALLS.md` grep confirm／channel／constitution／settings／schema／hosted），僅有 `hooks/confirm_*.sh` 與舊憲法對帳條目，與本片無相符項。`docs/solutions/` 不存在。

## 不做
- 第二片：Q31 自動續跑（失敗偵測、每個分析最多自動續跑一次、第二次失敗改「需要你處理」通知、算入 SU 門檻）。規則見裁決 D；待維護者確認 (c) 的適用範圍後另開計畫。
- Q20 樣本表由 LLM 產生（本片只保證它不被當成 run 核准）。
- 產品模式下取消（cancel）免確認的最終答案：**未決，待維護者回答**（10-13 原話可讀成產品模式也開放；本片只在兩數字都設時開放取消）。
- 雲端（Google Batch 等）任何免確認；`forget`、`clean_work` 的任何免確認路徑。
- 以環境變數、MCP 工具、聊天頁、token 或設定檔設定額度；以終端機旗標開啟（11-03 版設計已作廢）。
- 網頁終端機、OTP 轉送、新橫幅、改 012a 的 `users.dev_mode`。
- 任何 `deploy/` 其他變動；MCP 工具說明與 `FIXED_SENTENCE` 的任何變動。

## 裁決（lead，2026-11-07，回應計畫撰寫者的七點）
1. 預估 SU 來源＝歷史成功 run 取最大值；沒歷史就問（第一次跑某 pipeline 一定要按）——接受。
2. `ABF_HOSTED` 託管部署預設拒絕 `BUDGET`——接受。
3. cancel 在兩數字都設時納入免確認——接受（維護者 10-13「取消直接開放」）；產品模式是否也開放仍待他答。
4. 稽核欄位用 `confirmations.budget_note`（新增可為空欄位，附 migration）——接受。
5. Q31 範圍：自動但最多一次，待維護者確認；第二片處理。
6. Q2／Q21／Q20 引言是 lead 轉述，非錄音逐字；維護者本人確認過這些答案。
7. #376（7.0.0）需先 rebase 並修好 CI（shard 4/4 的 `test_tcm_47`；任務 `chat-confirm-rebase-fix`）並合併，本件才能開工。

## 維護者同意紀錄（2026-11-07，當面回答）
- 憲法 7.0.0（PR #376，CHAT 通道，含「任何 MCP 的 AI 都能自己填 user_confirmed=true、平台分不出是否真人」的誠實限制）：維護者回「同意 7.0.0」。
- 憲法 8.0.0（BUDGET 通道，五點）：維護者回「同意，但4)按照1)」。lead 的解讀：第 4 點（只有本人能設數字）就是第 1 點的方式——兩個數字由本人在登入後的網頁設定頁自己填，AI、MCP、聊天頁模型都碰不到、不能調高；條文照第 1 點寫，不另加其他設定管道。若解讀有誤請維護者更正。
- Approval 欄可寫維護者 2026-11-07 同意（引用上列原話）；PR 流程仍照 A 級：先合 #376，再開 8.0.0 的 PR。

## 裁決（自動補，2026-11-10）
針對 verifier 對本計畫提出的五點，逐點定案（以下蓋過前文任何不一致處）：
1. **Approval 欄唯一內容＝`PENDING`**。「維護者同意紀錄」最後一條「Approval 欄可寫維護者 2026-11-07 同意」作廢。Approval 欄只寫裁決 G 的 PENDING 句；PR 只開 draft、不合併；不得引用「同意，但4)按照1)」當作對憲法全文的同意。TC-076 與 `tests/budget_doc_test.sh` 的預期結果因此唯一：Approval 含 `PENDING`、不含任何維護者引言、PR 為 draft、未合併。
2. **同意紀錄的效力**。「同意，但4)按照1)」後半句只是 lead 的解讀，未經維護者本人確認，不視為對 8.0.0 全文的同意。維護者之後若在合併前親口確認（用他自己的話），才由 lead 或維護者本人補寫 Approval，並以另一次提交完成，不屬於本片 executor 的工作。TC-076 只驗「無杜撰引言、draft、未合併」，不驗「Approval 引用他的話」。
3. **待釐清的四點**：
   - (a) **0 不放行**：`decide` 要求兩個上限都 > 0（`0`＝什麼都不放行，裁決 F Q-d）；上限為 0 時，不論預估是多少（含 0）一律要確認。TC-D 加一條：單次上限 0＋預估 0 -> 待確認；每月上限 0 同。邊界「預估剛好等於上限」仍成立，但僅限上限 > 0。
   - (b) **cancel 不放行雲端 run**：cancel 照作法 3 只需 (a)(b)(c)，另加：目標 run 所在的 compute env 為雲端時，cancel 也要確認（fail-closed，取較嚴者；與 Q2「雲端的動作永遠要確認」一致，且不與 10-13「取消直接開放」衝突，因為 nano4 的取消仍開放）。無法判斷 run 所在環境時當作要確認。TC-E 加一條；TC-C 的 cancel 案例限 nano4 run。
   - (c) **`su.month_total` 是該使用者本人本月用量**：已查 `su.py` l.189，以 `jobs.owned_run_names(platform_path, user_id)` 只加總該使用者擁有的 run，不是全站。上限因此是每人各自的額度；計畫文字「本月已用」一律指本人。
   - (d) **託管部署**：維持裁決 F Q-b 與 lead 裁決 2 的預設（`ABF_HOSTED` 為真則拒絕 BUDGET）。若維護者在 NCHC 以 `ABF_HOSTED=1` 部署，此功能在該處不會生效，設定頁已註明「此部署不啟用」。這是已接受的預設，不阻擋開工；維護者若要託管也開，另開修正。
4. **`deploy/` 託管單元檔**：已查 worktree，`deploy/systemd/` 只有 `abf-mcp.service.in`、`abf-serve.service.in`、`abf-web.service.in`，`deploy/`、`tests/` 內都沒有 `ABF_HOSTED`，即 H-1 部署包尚未合併。決定：本片**不改 `deploy/`**，範圍表該項視為延後並在 ledger 記一行。TC-085 改為：`deploy/` 下若已存在含 `ABF_HOSTED` 的單元檔，才驗其值為 1；`env.example` 無論如何不得含 `ABF_HOSTED`；沒有單元檔則該項略過並註明。`budget.is_hosted()` 與 TC-K 仍照舊（用環境變數測）。
5. **沒有 spec.md**：本片以本 plan.md 的裁決、TC-A..M 與「維護者原話」為合約依據。Q2／Q20／Q21／Q31 引言是 lead 轉述、非錄音逐字，TC 以該轉述文字為輸入；若 lead 日後換入原文，只替換引言，不改 TC 結構。

## 裁決（dev-resolver，2026-11-11）
- 動作：`needs-lead`（交 lead 裁決；resolver 不改判、不重派）。
- 證據一（失敗輸出，ledger 第三輪）：全套 151/152，唯一紅是 `platform_shard_5_test.sh` 內的 `platform/tests/test_mcp_launch_pipeline.py::test_no_schema_change`（1 failed, 1031 passed，重試後仍紅）。
- 證據二（測試原文，`platform/tests/test_mcp_launch_pipeline.py:283-289`、`:341-355`）：`SCHEMA_PATHS = ["migrations", "abf_platform/store.py", "abf_platform/schema.sql"]`，結尾 `assert schema_diff(HERE.parent).strip() == ""`，即本分支對 `origin/v3` 的三點比較在這些檔案上必須零差異。
- 證據三（計畫原文，「範圍：檔案」）：「`platform/abf_platform/store.py`：`users` 加兩個可為空的 REAL 欄 `auto_su_single`、`auto_su_month`…`confirmations` 加可為空 TEXT 欄 `budget_note`…**需要 migration**」。worktree 實測 `git diff --stat origin/v3...HEAD` 在 `SCHEMA_PATHS` 上只有 `store.py | 62 +`（三個欄位的補欄與 `set_user_budget`／`user_budget`），所以這條紅是計畫要求的變更必然造成的，不是環境或流程問題，`retry` 不會變綠。
- 為什麼不是 `fix-contract-regrade-push`：這條不是本任務 verifier 出的題（本任務 `test-case.md` 的 TC-032 是「cancel 不放行雲端 run」，同號不同案）；它是另一個功能留下的結構守門測試，檔案不在計畫「只准改這些」清單內，也沒有可「只加項目」的釘住集合，要過只能改判斷邏輯，裁決 14 明文「不得改測試的判斷邏輯」。放寬守門測試不在 resolver 權限內。
- 為什麼不是 `unverified-operator`：機器側不是全綠，而且還沒有 verifier 驗收報告（本輪停在 executor，8 個本機 commit 未推）。
- 需要 lead 定的事（二選一，或另訂）：(a) 明文核可該測試對本分支的最小修改方式並指定誰改、由獨立 verifier 重閱；(b) 明文接受這一條在合併前為紅（三點比較，合併後自然歸零），並說明 CI 與草稿 PR 如何處理。另 ledger 記有一項未決：憲法 diff 含 Development Workflow 一條，與 TC-081 的範圍不符，「需裁決或改題」，請一併裁。
- 下一輪必須做的：等 lead 的裁決寫進本檔後才重派；重派後先推送既有 8 個 commit（同一分支、不 force、PR 維持草稿），不重做已綠的部分，不動憲法與三條憲法釘住測試。

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

## 裁決（lead，2026-11-11，憲法草案已出、33 條釘住測試待更新）
13. **憲法 8.0.0 草案已由 lead 委派起草並推上本分支**（commit 5894113f，草稿 PR #386）。你不得再改 `.specify/memory/constitution.md`、`tests/budget_doc_test.sh`、三個憲法釘住測試與 `PINNED_SN_SHA256`；不得開新 PR（#386 已存在，直接推同一分支）；不得 ready-for-review、不得掛自動合併、不得合併——憲法修正案要維護者親口說好。
14. **33 條失敗的釘住測試（約 25 檔：test_cleanup_store、test_cli_snapshots、test_web_board、test_k8s_launch 等）核可更新基準**：它們釘死「不得有新欄位／路由／指令」，而本任務合法新增了三個預算欄位、`POST /settings/budget`、`auto-send` 指令。**只准把這些新增項目加進各釘住集合（並依需要重算摘要值）**；不得刪除任何既有項目、不得放寬或刪除任何斷言、不得改測試的判斷邏輯。更新前先逐條讀失敗訊息，確認每條失敗都是「新增項目不在釘住集合內」；若有任何一條失敗不是這個原因，停下回報，不要硬改。
15. 目標：`tests/run_all.sh` 在 WSL 乾淨 clone 上全綠；全綠後 commit、推送同一分支（不 force），PR 維持草稿。回報要附整套測試實際數字。
16. 若有被 hook 擋寫的檔（`tests/*.sh` 閘門檔），不要繞過：BLOCKED 並列出檔名與需要的最小修改，lead 處理。
17. **補充（lead，憲法已批准）**：維護者已核可 8.0.0（commit 0c61c766 已把批准寫進憲法）。請把下列過時文字同步為「已核可」：`docs/PLATFORM.md`、`docs/PRINCIPLES.md` 的「a draft until the maintainer approves it」、`CHANGELOG.md` 的「draft … not yet approved」、`docs/TESTING.md` 的 TC-078（Approval 不再是 PENDING）。只改這幾處的措辭，不得動憲法本文、`tests/budget_doc_test.sh` 與釘住值；若有測試釘著這些舊字串，先看是否是「PENDING／draft」這類狀態字，只更新該狀態字，不放寬斷言。
## 裁決（lead，2026-11-11，回應第二次退回：TC-057 措辭與設計規範衝突）
18. **頁面文字遵守 DESIGN.md／web-wording-sweep 的禁用字表（含「你」），不開例外。** TC-057 與 plan 的措辭 lead 已改並推送（commit 794166e4）：未設定時顯示「未設定＝每次都需確認」。請把 `platform/abf_platform/web_devmode.py` 的 `bg_unset` 改成同一句「未設定＝每次都需確認」（只改這個字串；英文表若有對應句同步，語意不變），並確認整個 devmode 頁面的中文字串都不含禁用字（執行 `test_web_wording_sweep`）。這不算放寬任何斷言。
19. 第二輪起請**分批小步**：先把 33 條釘住基準的更新做完並提交推送（每個檔一個 commit 也可以），再跑 `tests/run_all.sh`；上輪在 75 個回合用完前沒推送——請每改完一批就 commit＋push（同一分支，不 force），避免交接時沒有成果。
20. 裁決 13–17 全部維持。
21. **裁決（lead，11-11 下午）：TC-032 schema-diff 測試（test_mcp_launch_pipeline.py 約 341–355）允許且只允許新增三個預算欄位。** 憲法 8.0.0 已由維護者核可並要求加這三欄，所以那條測試必須把這三欄加進它比對的基準集合；不得刪除既有欄位、不得放寬斷言邏輯（裁決 14 仍有效，這條是它的明確例外＝只加不減）。先把 8 個本地 commit 推上同一分支（不 force），再做這個修改。若還有其他失敗，列出測試名與原因回報。
