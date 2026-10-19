# 測試案例：skill-runs-actions（runs skill 改呼叫平台的 MCP 工具，不再用 tw）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
Revision 3 (2026-10-19): the developer-agent reopened the contract again by adding rulings S7 to S12 to plan.md after #138 (read_task_log, workdir per task in get_run, cancel_requested_at) was merged into v3. All TC IDs of revisions 1 and 2 are kept (TC-001 to TC-097). S7 closes the owed items task-folder-path and log-download, which makes TC-089 and TC-091 (written for S3) say the opposite of the plan: both are struck through and replaced by TC-100 to TC-106 and TC-110. TC-090 is reworded (workdir now exists; building a path is still forbidden). TC-006, TC-012, TC-013, TC-023, TC-083 and TC-094 are reworded. Block 8 (TC-100 to TC-112) is new and maps to S7-S11; S12 (grade the whole contract again, TC-023 included) is a grading instruction and is carried by the reworded TC-023 plus the full list.
All input comes from the plan in specs/skill-runs-actions/plan.md; no expected behaviour here is invented beyond what the plan, its Rules and the exact tool list and tool descriptions in platform/abf_platform/mcp_server.py (and docs/PLATFORM.md) state.
-->

**規格**：`specs/skill-runs-actions/plan.md`（此功能沒有獨立 spec.md，計畫即規格；來源是 issue #93 第 6 項；計畫末段「Rulings after acceptance round」S1 至 S6 與「Rulings, 2026-10-19」S7 至 S12 屬計畫的一部分）　**總覽**：`test-case-overview.md`

**白話背景**：`tw` 是 Seqera 公司的命令列工具，過去 runs skill 靠它查 run 的狀態。v3 平台有自己的 MCP 工具（AI 用的標準介面）：查詢用 `list_runs`、`get_run`，讀失敗 task 的 log 用 `read_task_log`，動作用 `cancel`、`resume`、`relaunch`，這三個動作只「請求」，真正按下確認的是人。這次要讓 `skills/runs/SKILL.md` 改叫這些工具。#138 合進 v3 之後，`get_run` 會給每個失敗 task 的資料夾（`workdir`）和「取消請求已送出」的時間（`cancel_requested_at`），所以先前「v3 尚未提供 task 的資料夾路徑」「v3 尚未提供下載 log」兩個待補項目已經不成立。

**基底分支**：下表凡寫「基底分支」，指這個 PR 要併入的分支 `origin/v3`（`git diff origin/v3...HEAD`；驗收時以已含 #138 的最新 `origin/v3` 為準）。這個 PR 的前身（tw 時代的 skill）也就是基底分支上的 `skills/runs/SKILL.md`。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：缺東西、沒有對應工具、AI 不該做的事時，skill 怎麼說、怎麼停。
- **不在範圍**：計畫明講這次不做的事；測試確認真的沒做。

新測試檔統一叫 `tests/skill_runs_uses_actions_test.sh`（下表「自動」若未另註，就是指這支，每條在註解寫上自己的 TC 編號）。

## 區塊 1 — 查狀態改走平台工具（計畫 Goal、Rule 1、Tests 第 1 點）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | Goal；Rule 2；Tests 第 1 點「no `tw ` command invocation」 | 功能 | 改完後的 `skills/runs/SKILL.md` | 在整份檔案找 `tw` 這個獨立的字（`tw runs list`、`tw launch`、`tw runs view …`、反引號裡的 `tw`、程式碼區塊裡以 `tw` 開頭的行都算） | 一個都找不到。唯一例外：某一句明講「這一步 v3 尚未提供」並提到 Seqera 的 `tw` 作為說明，該句不算「叫 AI 去執行」 | 自動：`tests/skill_runs_uses_actions_test.sh` |
| TC-002 | Goal「`list_runs`」；Tests「mentions get_run and list_runs」 | 功能 | 使用者打 `/runs` 沒指定任何 run | 讀「The work board」那一節 | 這一節叫 AI 用 `list_runs` 看目前有哪些 run；節內沒有 `tw`、沒有 `--workspace` 這類 tw 專用旗標 | 自動 |
| TC-003 | Goal「`get_run`（status、task counts、failure_reason）」；Tests「mentions get_run」 | 功能 | 使用者指定了一個 run（id 或名稱） | 讀「With a run named …resolve it and branch on status」那一段 | 這段叫 AI 用 `get_run` 取得該 run 的狀態與 task 數量，再依狀態進入對應分支；整份檔案有出現 `get_run` | 自動 |
| TC-004 | Goal（每個讀 run 狀態的步驟都改）；tw 時代原文 `tw runs list shows SUBMITTED` | 功能 | 改完後的檔案 | 讀「## SUBMITTED」那一節 | 原本寫的 `tw runs list shows SUBMITTED` 已改成用平台工具（`list_runs`／`get_run`）讀狀態；`tw launch` 的說法也不見了；節內仍保留 `scripts/on_site.sh --script scripts/why_pending.sh`（站上排程器的問法） | 自動 |
| TC-005 | Goal；tw 時代原文 `tw runs view -i <id> tasks` | 功能 | 改完後的檔案 | 讀「## RUNNING」開頭「per-task progress」那一行 | 看每個 task 進度改用 `get_run`（它回每個 process 的 task 數字與失敗 task）；該行沒有 `tw` | 自動 |
| TC-006 | Goal「`get_run`（…failure_reason）」；S8；tw 時代原文 `tw runs view … tasks`／`… download --type log` | 功能 | 改完後的檔案 | 讀「## FAILED」中「No refusal lines up」那一條 | 找失敗 task、取退出碼與失敗原因用 `get_run`，並提到它的 `failure_reason`（Nextflow 自己寫的失敗原因）；讀該 task 的 `.command.err` 改走 `read_task_log`（細節見 TC-104）；`tw runs view … tasks`、`tw runs view … download --type log` 兩句已改掉；「Jev triage」那一段的位置不變 | 自動 |
| TC-007 | Goal；tw 時代原文「UNKNOWN」節的 `tw runs list` | 功能 | 改完後的檔案 | 讀「## UNKNOWN」那一節 | 「平台回報了本檔沒有分支的狀態」改成指 `list_runs`／`get_run` 回報的狀態；仍寫「照原樣說出回報的狀態字、不猜」；沒有 `tw` | 自動 |
| TC-008 | Rule 2；tw 時代原文 `tw runs view -i <id> params` | 功能 | 改完後的檔案 | 讀「Jev categories」裡 `params` 那一節 | 不再有 `tw runs view … params`。要嘛換成 v3 存在的工具，要嘛這一步仍在、並白話寫「v3 尚未提供」。不得憑空造一個工具名 | 自動 |
| TC-009 | Rule 2；tw 時代原文「Reading a measurement」的三條 `tw runs view` | 功能 | 改完後的檔案 | 讀「## Reading a measurement」 | 沒有 `tw …` 指令。每個量測（metrics、resources-usage、resources-requested）要嘛換成存在的工具，要嘛白話寫「v3 尚未提供」；同節提到的 `pipeline_info/execution_trace_*.txt` 路徑與下面的判讀表（137／85%／30% 等）仍在 | 自動 |
| TC-010 | Goal；Rule 3（只改「怎麼讀狀態」）；tw 時代原文「Before anything else」 | 功能 | 改完後的檔案 | 讀「## Before anything else」 | 「每個 tw 呼叫都要先 source env.sh、都要帶 `--workspace`」那兩段（只為 tw 而寫）已移除；`scripts/intro.sh runs` 與結尾 `scripts/intro.sh --end runs` 仍在 | 自動 |
| TC-011 | Goal；Rule 1（以平台為準）；tw 時代原文「Seqera Platform is the only source of truth for run state. Start there」 | 功能 | 改完後的檔案 | 找這句與同段 | 不再說「Seqera Platform 是唯一真相、先去那裡看」；改為依 v3 的來源（平台的 MCP 工具）。「再補兩樣平台看不到的：站上排程器在做什麼、站上拒絕送出什麼」的意思保留 | 自動 |
| TC-012 | Rule 1「name only tools that exist on v3」；Tests 第 1 點「every MCP tool name it mentions in backticks exists in mcp_server.py」 | 功能 | `platform/abf_platform/mcp_server.py` 目前註冊的十二個工具：`list_runs`、`get_run`、`list_compute_envs`、`get_compute_env`、`list_agents`、`list_site_files`、`read_task_log`、`launch`、`cancel`、`resume`、`relaunch`、`forget` | 取出 SKILL.md 中被當成「MCP 工具」介紹的反引號名稱 | 每一個都在上列十二個之中（測試應直接從 `mcp_server.py` 讀出名單，不寫死）；沒有 `list_pipelines`、`get_task`、`get_logs`、`download_log` 這類不存在的工具名 | 自動 |
| TC-013 | Rule 1「exact tool names and arguments」；S8 | 功能 | 工具的引數：`get_run` 用 `run_id`；`cancel`／`resume`／`relaunch` 只用 `run_name`；`list_site_files` 用 `compute_env` 與 `path`；`read_task_log` 用 `run_name`、`task`、`which` | 讀 SKILL.md 裡每個示範呼叫或說明引數的地方 | 引數名稱與上列一致；沒有替 `resume`／`relaunch`／`cancel` 另加「新參數」或「新資源大小」之類不存在的引數；`read_task_log` 沒有被說成可以讀 `.command.err`、`.command.out`、`.command.log` 以外的檔案 | 自動 |
| TC-014 | Tests「A test … that fails today」 | 功能 | 基底分支上原本的 `skills/runs/SKILL.md`（18 處 tw；改完後也存成 `tests/fixtures/runs_skill/SKILL.tw-era.md` 供測試用） | 驗收者把基底分支版 SKILL.md 放進同一支新測試跑 | 新測試對基底分支版**失敗**，對改完後的版本**通過**（證明它真的會抓到 tw） | 自動：驗收者在兩個版本各跑一次 |

## 區塊 2 — 動作只「請求」，由人確認（計畫 Goal、Tests 第 1 點）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | Goal「each only asks; the person confirms on a human channel」；Tests「wherever it mentions cancel/resume/relaunch it also says a person confirms」 | 功能 | 改完後的檔案 | 找出每一處把 `cancel`、`resume`、`relaunch` 當工具提到的段落（含「## CANCELLED」那一段） | 同一段內都寫明「要由人確認／按送出」（例如「after the person says yes each time」）；沒有任何一處只提工具、不提人確認 | 自動 |
| TC-021 | Goal「never describe the AI as confirming」 | 例外 | 改完後的檔案 | 找所有談「確認／說 yes／送出」的句子 | 這些句子的主詞都是人（使用者）。沒有「AI 確認」「我確認後送出」「AI 回答表單」「AI 替使用者按 yes」這類說法 | 自動 |
| TC-022 | Rule 3；tw 時代原文 CANCELLED 最後一段 | 功能 | 改完後的檔案 | 讀「## CANCELLED」最後一段 | 仍說：失敗或取消的 run 可用名稱續跑（`resume`：同資料夾、接著跑）或原樣重跑（`relaunch`：新資料夾、從頭）；且仍說樣本與參數沿用第一次 launch，要改就是新的 `launch` | 自動 |
| TC-023 | Rule 1（工具的實際能力）；S10；S12（本條必須重新評分）；`mcp_server.py` 對 `resume`／`relaunch` 的描述「cannot be changed here」 | 例外 | 改完後的檔案；RUNNING、Jev 路由裡有「調高時間／換小一點的盒子再 relaunch」的步驟，`params` 與 `input` 兩個類別各有「Usual fix」 | 讀這些步驟（含「Reading a measurement」判讀表、walltime 條目、`#### params`、`#### input`；`relaunch` 有沒有加反引號都要看） | 沒有任何一句說 `resume` 或 `relaunch` 工具可以改時間、記憶體、參數或樣本表。要改資源或參數或樣本表是「新的 launch」，或這一步標明「v3 尚未提供」；`params` 類別寫的是「新的分析，用 `launch`，由人確認；`relaunch`／`resume` 不能改參數」；`relaunch_with_override.sh` 的處理見 TC-030 | 自動 |
| TC-024 | 憲法「Manual walkthrough」；`docs/TESTING.md`「Resume and relaunch (009e)」第 2 步 | 功能 | `docs/TESTING.md` 該節 | 人讀 `skills/runs/SKILL.md` 的 resume／relaunch／cancel 說法 | 說清楚每個動作都要人點 yes、樣本與參數不能改 | 手動：`docs/TESTING.md`「Resume and relaunch (009e)」第 2 步 |

## 區塊 3 — 沒有對應的步驟：明講、記帳、不造工具（計畫 Rule 2、S4）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | Rule 2；S4（內部呼叫 `tw` 的腳本：`task_health.sh`、`tune_resources.sh`、`relaunch_with_override.sh`、`runs_board.sh`、`agent_ctl.sh`；用 `grep -n '\btw\b' scripts/<名>.sh` 可見） | 例外 | SKILL.md 仍叫 AI 執行其中任何一支 | 讀每個「叫 AI 執行這支腳本」的地方 | 每一處要嘛已改成平台工具，要嘛在原地白話寫明「這一步 v3 尚未提供」（S4 的字樣；同義英文說法同 TC-031）。不得讓 AI 去跑一支在沒有 tw 的 v3 必定失敗、卻沒標示的腳本。（單純點名的排版提醒段落不算「叫 AI 執行」，見 TC-045） | 自動 |
| TC-031 | Rule 2「keep the step but say plainly it is not available on v3 yet」 | 例外 | SKILL.md 中有標「v3 尚未提供」的步驟 | 讀這些步驟 | 步驟本身還在（沒有被悄悄刪掉）；用白話直接說這一步 v3 還沒有，不是含糊帶過；沒有為它編造工具名 | 自動 |
| TC-032 | Rule 2「list it in the ledger as owed」；S11 | 功能 | `specs/skill-runs-actions/ledger.md` | 比對 SKILL.md 與 ledger | SKILL.md 每一個標「v3 尚未提供」的步驟，ledger 都有一行「待補（owed）」；ledger 沒有 SKILL.md 看不到的待補項（兩邊一一對得上） | 自動 |

## 區塊 4 — 結構、觸發、語氣不變，既有測試不退步（計畫 Rule 3、Tests 第 2 點）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | Rule 3「Keep the skill's structure, triggers」 | 功能 | 基底分支與改完後的 SKILL.md | 比對最上方 frontmatter（`name`、`description`、`argument-hint`） | 三行與基底分支完全相同（`name: runs`、`description: Check on, debug, or deliver a pipeline run`、`argument-hint: [run id or name]`） | 自動 |
| TC-041 | Rule 3「user-facing tone」；S1「Keep the six branch headings (tests pin them)」 | 功能 | 改完後的檔案 | 執行 `bash tests/runs_report_format_test.sh` | 通過：SUBMITTED、RUNNING、FAILED、SUCCEEDED、CANCELLED、UNKNOWN 六個分支標題都在，且每個都有 `Status:`／`Layer:`／`I will handle:` 或 `You decide:`／`Next step:` 四行 | 自動：`tests/runs_report_format_test.sh` |
| TC-042 | Rule 3；憲法 12 | 功能 | 改完後的檔案 | 找開場與收尾 | 仍有 `scripts/intro.sh runs`（開場）與 `scripts/intro.sh --end runs`（診斷或交付完成後） | 自動 |
| TC-043 | Goal「Steps that read files on the site keep their existing site scripts」 | 功能 | 改完後的檔案 | 找站上的查詢 | `scripts/on_site.sh --script scripts/why_pending.sh`（SUBMITTED 與 RUNNING）與 `scripts/on_site.sh --script scripts/egress_ctl.sh denied`（FAILED，且位置在 Jev 步驟之前）仍在、寫法不變；若改用 `list_site_files`，節內寫明要給 `compute_env` 與 `path` | 自動 |
| TC-044 | Rule 3；Tests 第 2 點；S6 | 功能 | 改完後的檔案 | 執行 `bash tests/jev_test.sh` | 通過：「No refusal lines up」→「137, or killed」→「No `.command.log`」→ `scripts/jev.sh triage --err` →「Anything else」→「On a site with unrestricted egress」的順序不變；`first failing task`、`Jev 判斷：`、各 `####` 類別小節都還在 | 自動：`tests/jev_test.sh` |
| TC-045 | Rule 3；Rule 4；S6 | 功能 | 改完後的檔案 | 執行 `bash tests/column_output_relay_rule.sh` | 通過：「排版輸出要放在 fenced code block、PITFALLS 35」那段仍在，且仍點名所有用空格排版的腳本（`runs_board.sh`、`settings.sh`、`status.sh` 等）。若執行者刪了名字，必須依規則 4 改測試並寫進 ledger | 自動：`tests/column_output_relay_rule.sh` |
| TC-046 | Tests「tests/run_all.sh stays green」 | 功能 | 在 WSL／Linux，或看 CI 結果 | 執行 `bash tests/run_all.sh` | 全綠；總數包含新增的那一支 | 自動：`tests/run_all.sh` |
| TC-047 | Tests「flow_skills_layout_test.sh, skill_portability_test.sh, skill_names_command_file_test.sh, commands_scope_tw_to_the_workspace.sh etc. either stay green or are updated per rule 4」 | 功能 | 改完後的檔案 | 逐支執行這四支（再加 `skill_requires_intro_test.sh`、`commands_resolve_their_own_paths.sh`、`command_layer_is_site_neutral.sh`、`egress_allow_test.sh`、`off_design_single_path.sh`、`works_without_host_test.sh`） | 每一支通過，或依規則 4 有寫在 ledger 的更新理由 | 自動：上列各測試檔 |

## 區塊 5 — 淘汰舊測試的規矩（計畫 Rule 4）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | Rule 4「each retired assertion must be replaced by one that pins the new behaviour, or listed in the ledger with the reason」 | 例外 | `git diff origin/v3...HEAD -- tests/` | 驗收者逐支比對有被動到的測試檔（新增的 `tests/skill_runs_uses_actions_test.sh` 與 `tests/fixtures/runs_skill/` 不算被動到既有測試） | 沒有任何既有斷言被默默刪除、放寬、跳過，或把期望值改成配合新輸出；被拿掉的斷言，要嘛有一條釘住新行為的取代，要嘛 ledger 寫了「不再適用」的理由 | 自動：驗收者對基底分支做 diff |
| TC-051 | Rule 4 | 功能 | `specs/skill-runs-actions/ledger.md` | 讀 ledger | 明講有沒有淘汰任何只釘 tw 時代字句的斷言；有的逐條列出（被拿掉的斷言、取代它的新斷言或不再適用的理由）；沒有就明寫「無」 | 自動 |

## 區塊 6 — 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 不在範圍「Other skills (one PR each, later)」 | 不在範圍 | 這個 PR 的 diff | `git diff origin/v3...HEAD --stat -- skills/` | 只有 `skills/runs/SKILL.md` 有變；`skills/setup`、`skills/launch`、`skills/downstream`、`skills/finish`、`skills/operational` 沒變 | 自動：驗收者對基底分支做 diff |
| TC-061 | 不在範圍「platform/ code」 | 不在範圍 | 同上 | `git diff origin/v3...HEAD --stat -- platform/` | 沒有任何變動（含 S7 至 S11：用 `workdir`、`read_task_log`、`cancel_requested_at` 都是讀 #138 已有的東西，不改平台） | 自動 |
| TC-062 | 不在範圍「hooks/」 | 不在範圍 | 同上 | `git diff origin/v3...HEAD --stat -- hooks/` | 沒有任何變動 | 自動 |
| TC-063 | 不在範圍「CHANGELOG.md is NOT edited」 | 不在範圍 | 同上 | `git diff origin/v3...HEAD --stat -- CHANGELOG.md` | 沒有任何變動 | 自動 |
| TC-064 | 不在範圍「docs/PLATFORM.md not edited」 | 不在範圍 | 同上 | `git diff origin/v3...HEAD --stat -- docs/PLATFORM.md` | 沒有任何變動 | 自動 |
| TC-065 | Rule 4「No other skill or script is changed in this PR; scripts still used by other skills stay」；S4「The scripts are not changed here」 | 不在範圍 | 同上 | `git diff origin/v3...HEAD --stat -- scripts/` | `scripts/` 底下沒有任何檔案被改、刪或新增（`runs_board.sh`、`task_health.sh`、`tune_resources.sh`、`relaunch_with_override.sh`、`agent_ctl.sh`、`fetch.sh` 等都留著、內容不變） | 自動 |

## 區塊 7 — 第一輪驗收後的裁示 S1 至 S6（計畫「Rulings after acceptance round」）

### S1：狀態字對應（v3 只回 running、succeeded、failed、lost）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | S1「SUBMITTED = the launch was confirmed but the run is not in `list_runs` yet (say "已送出、還沒開始", check again later)」 | 功能 | 改完後的檔案 | 讀「## SUBMITTED」標題下的對應說明 | 有一行說：SUBMITTED ＝ 送出已被人確認、但 `list_runs` 裡還沒有這個 run；告訴使用者的話是「已送出、還沒開始」（照字面）；並說稍後再查一次 | 自動 |
| TC-081 | S1「never wait forever — after 3 checks tell the person」 | 例外 | 一個送出後一直不在 `list_runs` 的 run | 讀 SUBMITTED 對應說明 | 寫明最多查 3 次；3 次之後就把狀況告訴使用者，不是無限等下去 | 自動 |
| TC-082 | S1「RUNNING = running; FAILED = failed; SUCCEEDED = succeeded」 | 功能 | 改完後的檔案 | 讀「## RUNNING」「## FAILED」「## SUCCEEDED」各自標題下 | 各有一行對應：RUNNING ＝ 平台回 `running`；FAILED ＝ 回 `failed`；SUCCEEDED ＝ 回 `succeeded` | 自動 |
| TC-083 | S1「CANCELLED = failed whose facts say a cancel was sent (Nextflow reports a cancelled run as failed, docs/PLATFORM.md)」；S9 | 功能 | 改完後的檔案 | 讀「## CANCELLED」標題下 | 有一行說：CANCELLED ＝ 狀態是 `failed`、而且已知有送出取消請求（這個事實來自 `get_run` 的 `cancel_requested_at`，見 TC-107）；並說 Nextflow 把被取消的 run 回報成 failed；沒有為了「取消」去編造不存在的工具名（見 TC-012） | 自動 |
| TC-084 | S1「UNKNOWN = lost (three heartbeats silent) or any other value」 | 功能 | 改完後的檔案 | 讀「## UNKNOWN」標題下 | 有一行說：UNKNOWN ＝ `lost`（連續三次心跳沒回應）或任何其他沒列出的值；仍照原樣說出平台回報的字（見 TC-007） | 自動 |
| TC-085 | S1「Keep the six branch headings … put one mapping line under each」 | 功能 | 改完後的檔案 | 數 SUBMITTED、RUNNING、FAILED、SUCCEEDED、CANCELLED、UNKNOWN 六個分支 | 六個標題都在，每個標題下剛好各有一行狀態對應（共六行，不多不少） | 自動 |
| TC-086 | S1（v3 只回四種狀態） | 例外 | 改完後的檔案 | 找所有說「平台回報什麼狀態」的句子 | 沒有任何一句說 `list_runs`／`get_run` 會回 `SUBMITTED` 或 `CANCELLED` 這兩個值，也沒有把 `cancel_requested_at` 說成一種狀態；它們只出現在「這是我們對應出來的分支」或「這是一個事實欄位」的語境裡 | 自動 |

### S2：resume 與 relaunch 的說法不能打架

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-087 | S2「resume = same folder, finished tasks come back from the cache … Correct the RUNNING section's sentence」 | 功能 | 改完後的檔案 | 讀「## RUNNING」開頭「A relaunch counts as reversible …」那一句 | 那一句已改正：說「接著跑、已完成的 task 從快取回來」的是 `resume`（同資料夾），不是 `relaunch` | 自動 |
| TC-088 | S2「relaunch = new folder, from the start」 | 例外 | 改完後的檔案 | 找整份檔案裡每一處談 `resume` 或 `relaunch` 的句子 | 凡談 `relaunch`，都是「新資料夾、從頭」，沒有任何一句說 `relaunch` 會用快取或接著跑；凡談 `resume`，都是「同資料夾、快取」，沒有任何一句說 `resume` 會開新資料夾或從頭 | 自動 |

### S3：（已被 S7、S8 取代）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| ~~TC-089~~ | ~~S3「say plainly "v3 尚未提供 task 的資料夾路徑"」~~ 已被 S7 取代：S7 要求這句話在兩處都移除。由 TC-100 至 TC-103 取代 | — | — | — | 本條作廢，保留編號 | — |
| TC-090 | S3「Do not invent a path」；S7（現在 `get_run` 有 `workdir`） | 例外 | 改完後的檔案 | 找所有教 AI「怎麼找到失敗 task 的資料夾」的句子 | 資料夾只能取自 `get_run` 的 `workdir` 這一個欄位（它在 `mcp_server.py` 的 `get_run` 說明裡存在）；沒有任何一句叫 AI 取別的不存在的欄位（如 `work_dir`、`path`）、也沒有教 AI 從 hash 自行拼出 `work/xx/yyyy` 路徑；沒有為此編造新工具名 | 自動 |
| ~~TC-091~~ | ~~S3「list it in the ledger as owed (task 資料夾路徑)」~~ 已被 S11 取代：task-folder-path 已結案、不能再留在待補清單。由 TC-110 取代 | — | — | — | 本條作廢，保留編號 | — |

### S4：內部還用 tw 的腳本

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-092 | S4「steps that call scripts which use `tw` internally … stay, each marked "v3 尚未提供" and listed as owed. The scripts are not changed here」 | 例外 | 改完後的 SKILL.md 與 ledger | 對 `task_health.sh`、`tune_resources.sh`、`relaunch_with_override.sh`、`runs_board.sh`、`agent_ctl.sh` 逐支，找 SKILL.md 有沒有叫 AI 執行它 | 凡 SKILL.md 還叫 AI 執行其中某支，該步驟就在原地標「v3 尚未提供」，且 ledger 有對應的 owed 行；沒有任何一支在 SKILL.md 裡是「叫 AI 執行、卻沒標也沒記帳」。（已改用平台工具取代的步驟不必標；腳本本身不得被改，見 TC-065） | 自動 |

### S5：手動步驟

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-093 | S5「Add one manual step to docs/TESTING.md under the runs/009e section」 | 功能 | 改完後的 `docs/TESTING.md` | 找「Resume and relaunch (009e)」那一節（或其下的 runs 區段）新增的那一步 | 有新增剛好一步，寫明：在測試用平台上，依新的 `skills/runs/SKILL.md` 問 AI 關於一個失敗的 run 與一個執行中的 run；並寫出通過條件（用 `list_runs`／`get_run`、完全沒有 `tw`、每個 cancel／resume／relaunch 都等人說 yes） | 自動：檢查該步驟存在且含這幾點 |
| TC-094 | S5「check it uses list_runs/get_run, never `tw`」；S7、S8 | 功能 | 一個測試用平台，其中有一個失敗的 run（失敗 task 有 `workdir`）和一個執行中的 run；依新 skill 讓 AI 回答 | 分別問 AI「這個失敗的 run 怎麼了」「那個執行中的 run 進度如何」 | AI 呼叫的是 `list_runs`／`get_run`；失敗 task 的 log 用 `read_task_log` 讀；整段過程沒有出現 `tw` 指令；對於 v3 仍沒有的東西（例如 run 當初的 params）AI 明說「v3 尚未提供」而不是亂猜 | 手動：`docs/TESTING.md` 新增的 S5 步驟 |
| TC-095 | S5「every cancel/resume/relaunch waits for the person's yes」 | 功能 | 同上 | 對失敗的 run 說「幫我續跑」「重跑」，對執行中的 run 說「取消它」 | AI 每一次都只送出請求，並請人到自己的管道（表單或確認頁）按 yes；在人說 yes 之前什麼都沒開始；AI 沒有說「我已幫你確認」 | 手動：`docs/TESTING.md` 新增的 S5 步驟 |
| TC-097 | S5「Add **one** manual step」；Out of scope（docs/PLATFORM.md 等不動） | 不在範圍 | 這個 PR 的 diff | `git diff origin/v3...HEAD -- docs/TESTING.md` | 只有新增那一步的行；既有的步驟沒有被改或刪 | 自動：驗收者對基底分支做 diff |

### S6：既有測試的錨點

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-096 | S6「Keep tests/column_output_relay_rule.sh and tests/jev_test.sh anchors green; if a pinned name is removed, update that test per rule 4 and log it in the ledger」 | 功能 | 基底分支與改完後的 `tests/column_output_relay_rule.sh`、`tests/jev_test.sh` | 兩支各跑一次；再 `git diff origin/v3...HEAD` 這兩個檔 | 兩支都通過；而且兩個檔要嘛完全沒被改，要嘛每個被改的斷言都在 ledger 有「舊斷言、新斷言、理由」（沒有放寬、沒有跳過） | 自動：兩支測試檔，加驗收者對基底分支做 diff |

## 區塊 8 — #138 合併後的裁示 S7 至 S11（計畫「Rulings, 2026-10-19」；S12 見檔頭說明與 TC-023）

### S7：task 資料夾路徑改取自 `get_run` 的 `workdir`

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-100 | S7「Remove the "v3 尚未提供 task 的資料夾路徑" wording at both places (around l.235 and l.242)」 | 功能 | 改完後的檔案 | 在整份 SKILL.md 搜「v3 尚未提供 task 的資料夾路徑」「task-folder-path」「gives no work folder」這類句子 | 一處都找不到（FAILED 的「No refusal lines up」與「Jev triage」兩處都已改掉）；兩個步驟本身都還在 | 自動 |
| TC-101 | S7「the skill takes the task folder from `get_run`'s `workdir`; the per-run check runs whenever `workdir` is present」 | 功能 | 改完後的檔案；`get_run` 回的失敗 task 帶有 `workdir` | 讀 FAILED 的「No refusal lines up」那一條 | 寫明失敗 task 的資料夾取自 `get_run` 的 `workdir`，有 `workdir` 就照做（讀 log 見 TC-104），不再要求人先提供資料夾 | 自動 |
| TC-102 | S7「(Jev triage) the per-run check runs whenever `workdir` is present」 | 功能 | 改完後的檔案；使用者已開啟 Jev triage | 讀「Jev triage, only if the user turned it on」那一條 | 仍是「只在使用者開啟時、對 `get_run` 列出的第一個失敗 task、每個 run 一次、不是每個 task 一次」；執行條件是該 task 有 `workdir`，不再是「人給了資料夾才跑」；`tests/jev_test.sh` 的順序與錨點不變（見 TC-044） | 自動 |
| TC-103 | S7「only falls back to asking the person when `get_run` has no `workdir` for that task (say so in one plain sentence)」 | 例外 | 改完後的檔案；`get_run` 對某個失敗 task 沒有 `workdir`（Nextflow 沒回報，或是從 run 資料夾重建的 run） | 讀 FAILED 兩處（「No refusal lines up」與 Jev triage）中沒有 `workdir` 的情況 | 用一句白話寫明：這個 task 的 `get_run` 沒有 `workdir` 時才改問人資料夾在哪；沒有從 hash 拼路徑（見 TC-090）；這句話不含「v3 尚未提供」字樣（因為不再是待補項目） | 自動 |

### S8：失敗 task 的 log 改用 `read_task_log`

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104 | S8「the skill reads the failed task's log with `read_task_log` (`which` = err first, then out/log if err is empty)」 | 功能 | 改完後的檔案 | 讀 FAILED 讀 log 的那一步 | 叫 AI 用 `read_task_log`（引數 `run_name`、`task`、`which`）；`which` 先用 `err`，`err` 是空的才改讀 `out` 或 `log`；「task」取自 `get_run` 的失敗 task 名稱；工具名在 `mcp_server.py` 中存在（見 TC-012） | 自動 |
| TC-105 | S8「not with `scripts/fetch.sh`」 | 功能 | 改完後的檔案 | 找 FAILED 一節裡讀失敗 task log 的地方；另找整份檔案裡還有沒有「log-download」待補標記 | 讀失敗 task 的 log 不再叫 AI 用 `scripts/fetch.sh`，也沒有「下載 log 這一步 v3 尚未提供」「owed: log-download」的說法。（`fetch.sh` 在 SUCCEEDED 交付結果時的用法與本條無關，不得被誤傷、仍在） | 自動 |
| TC-106 | S8「Keep the refusals of `read_task_log` (no workdir, not launched from this platform, agent offline) as plain one-line fall-backs」 | 例外 | 改完後的檔案；`read_task_log` 被拒 | 讀 `read_task_log` 那一步之後的說明 | 三種拒絕（task 沒有記錄的 workdir、run 不是從這個平台發起的、agent 離線）各有一行白話的退路，每行只一句；沒有一種被漏掉；退路裡沒有叫 AI 改去跑 `scripts/fetch.sh` 或編造路徑 | 自動 |

### S9：取消請求的事實

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-107 | S9「when a run has `cancel_requested_at`, the skill says a cancel was already asked for (with the time, Asia/Taipei)」 | 功能 | 改完後的檔案；`get_run` 回的 run 帶 `cancel_requested_at` | 讀 CANCELLED 一節與其他談到取消的地方 | 檔案明講 `cancel_requested_at` 這個欄位名（它在 `mcp_server.py` 的 `get_run` 說明裡存在）；有該欄位時，skill 要 AI 告訴使用者「已經請求過取消」，並附上那個時間，時區用 Asia/Taipei；它被當作事實，不是狀態（見 TC-086） | 自動 |
| TC-108 | S9「and does not offer another `cancel`」 | 例外 | 改完後的檔案；同上 | 找每一處會叫 AI 提議 `cancel` 的地方（例如 CANCELLED 一節末段「To stop a run that is still going, call `cancel`…」與 RUNNING 一節） | 同一處寫明：該 run 有 `cancel_requested_at` 時不再提議 `cancel`；沒有該欄位的執行中 run 仍可提議 `cancel`，且仍寫明由人確認（TC-020 不退步） | 自動 |

### S10：samplesheet 改了就是新的 launch

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-109 | S10「"correct the samplesheet row, then relaunch" contradicts S1 … a corrected samplesheet means a **new launch** (the launch skill / `launch`), not `relaunch`; `relaunch` is only for re-running the same inputs」 | 功能 | 改完後的檔案 | 讀 `#### input` 類別的「Usual fix」，並找整份檔案還有沒有「改 samplesheet 後 relaunch」的說法 | `input` 的修法寫成：修正過的 samplesheet 是一次新的 launch（用 launch skill／`launch`，由人確認），不是 `relaunch`；`relaunch` 只用在輸入完全不變的重跑；整份檔案沒有任何一句說改了 samplesheet、參數或輸入檔再用 `relaunch`／`resume` | 自動 |

### S11：待補清單與被取代的舊測試

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-110 | S11「The ledger's owed list drops task-folder-path and log-download (6 items remain)」 | 功能 | `specs/skill-runs-actions/ledger.md` 與 SKILL.md | 數 ledger 的 `owed:` 行，並與 SKILL.md 的 `(owed: …)` 標記比對 | ledger 的 owed 剛好 6 項：task-health、resize-relaunch、run-params、measurements、tune-resources、ce-apply；沒有 task-folder-path、沒有 log-download 這兩項（歷史說明文字可以提到它們已結案，但不能再以 owed 項目出現）；SKILL.md 的 owed 標記與這 6 項一一對得上（同 TC-032），也沒有 task-folder-path、log-download 標記 | 自動 |
| TC-111 | S11 / Rule 4（S7、S8 讓 S3 時代的測試斷言不再適用） | 例外 | `tests/skill_runs_uses_actions_test.sh` 與 ledger；該測試原本有釘「v3 尚未提供 task 的資料夾路徑」「task-folder-path」「log-download」的斷言（TC-089、TC-091 的自動版） | 驗收者比對測試檔在本 PR 內的變動與 ledger | 這些舊斷言沒有被默默刪除或放寬：每一條被拿掉的，要嘛有一條釘住新行為的斷言取代（TC-100 至 TC-106、TC-110 的內容），要嘛 ledger 的 Retired tests 逐條列出「舊斷言、取代它的新斷言、為什麼不再適用」。對基底分支（tw 時代）版本，新測試仍然失敗（TC-014 不退步） | 自動：驗收者對基底分支做 diff |

### S7 至 S11 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112 | S11「The other "not available on v3 yet" items stay as they are」 | 不在範圍 | 改完後的檔案與 ledger | 找 task-health、resize-relaunch、run-params、measurements、tune-resources、ce-apply 這 6 個待補標記 | 6 個標記的位置與「v3 尚未提供」的說法都還在，沒有被趁這次順手結案，也沒有為其中任何一項編造新工具名或改腳本（TC-065） | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 第 2 條：不得另存一份 run 狀態、不得有第二條送出路徑 | 功能 | 改完後的 SKILL.md | 執行 `bash tests/no_second_run_state_test.sh`，並讀 SKILL.md 有無新增「把 run 狀態存成檔／快取」的指示（含：把 `read_task_log` 讀到的 log 文字存成檔，是否被寫成保存 run 狀態） | 測試通過；SKILL.md 只叫 AI 向平台讀狀態，沒有叫它寫檔保存 run 狀態（S1 的「查 3 次」是重新向平台讀，不是存檔）；唯一的送出方式是 `resume`／`relaunch`／`launch` 這種「請求後由人確認」的工具，沒有 `tw launch`、`sbatch` 等直接送出 | 自動：`tests/no_second_run_state_test.sh` |
| TC-071 | 第 5 條：沒有 hooks、沒有 `.claude-plugin/` 時仍可用 | 功能 | 改完後的檔案 | 執行 `bash tests/works_without_host_test.sh` | 通過，`skills/runs/SKILL.md` 仍在被檢查的必要檔案裡 | 自動：`tests/works_without_host_test.sh` |
| TC-072 | 第 12 條：行動意圖必須走正式流程並先出示說明 | 功能 | 改完後的檔案 | 執行 `bash tests/skill_requires_intro_test.sh` 與 `bash tests/next_step_test.sh` | 兩支通過（對 runs 的開場／收尾呼叫字串不變） | 自動：`tests/skill_requires_intro_test.sh`、`tests/next_step_test.sh` |
| TC-073 | 安全網「Every write tool of the platform … refuses until a person has answered」（`launch`、`cancel`、`resume`、`relaunch`、`forget`） | 例外 | 改完後的檔案（S9、S10 新增了「不再提議 cancel」「新的 launch」兩種說法） | 讀 S9、S10 新增的句子與其他所有談 `launch`／`cancel`／`resume`／`relaunch` 的句子 | 凡提到這些寫入工具，都寫明由人確認；沒有一句把 `launch` 或 `cancel` 說成 AI 可以自己確認或自己送出；沒有任何一句叫 AI 在人說 yes 之前宣告已經開始或已經停止 | 自動：`tests/skill_runs_uses_actions_test.sh`（與 TC-020、TC-021 同掃） |
