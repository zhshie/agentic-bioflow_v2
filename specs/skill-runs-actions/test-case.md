# 測試案例：skill-runs-actions（runs skill 改呼叫平台的 MCP 工具，不再用 tw）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
All input comes from the plan in specs/skill-runs-actions/plan.md; no expected behaviour here is invented beyond what the plan, its Rules and the exact tool list in platform/abf_platform/mcp_server.py state.
-->

**規格**：`specs/skill-runs-actions/plan.md`（此功能沒有獨立 spec.md，計畫即規格；來源是 issue #93 第 6 項）　**總覽**：`test-case-overview.md`

**白話背景**：`tw` 是 Seqera 公司的命令列工具，過去 runs skill 靠它查 run 的狀態。v3 平台有自己的 MCP 工具（AI 用的標準介面）：查詢用 `list_runs`、`get_run`，動作用 `cancel`、`resume`、`relaunch`，這三個動作只「請求」，真正按下確認的是人。這次要讓 `skills/runs/SKILL.md` 改叫這些工具。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：缺東西、沒有對應工具、AI 不該做的事時，skill 怎麼說、怎麼停。
- **不在範圍**：計畫明講這次不做的事；測試確認真的沒做。

新測試檔統一叫 `tests/skill_runs_uses_actions_test.sh`（計畫寫「e.g.」，檔名由執行者最後定；下表「自動」若未另註，就是指這支，每條在註解寫上自己的 TC 編號）。

## 區塊 1 — 查狀態改走平台工具（計畫 Goal、Rule 1、Tests 第 1 點）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | Goal；Rule 2；Tests 第 1 點「no `tw ` command invocation」 | 功能 | 改完後的 `skills/runs/SKILL.md` | 在整份檔案找 `tw` 這個獨立的字（`tw runs list`、`tw launch`、`tw runs view …`、反引號裡的 `tw`、程式碼區塊裡以 `tw` 開頭的行都算） | 一個都找不到。唯一例外：某一句明講「這一步 v3 尚未提供」並提到 Seqera 的 `tw` 作為說明，該句不算「叫 AI 去執行」 | 自動：`tests/skill_runs_uses_actions_test.sh` |
| TC-002 | Goal「`list_runs`」；Tests「mentions get_run and list_runs」 | 功能 | 使用者打 `/runs` 沒指定任何 run | 讀「The work board」那一節 | 這一節叫 AI 用 `list_runs` 看目前有哪些 run；節內沒有 `tw`、沒有 `--workspace` 這類 tw 專用旗標 | 自動 |
| TC-003 | Goal「`get_run`（status、task counts、failure_reason）」；Tests「mentions get_run」 | 功能 | 使用者指定了一個 run（id 或名稱） | 讀「With a run named …resolve it and branch on status」那一段 | 這段叫 AI 用 `get_run` 取得該 run 的狀態與 task 數量，再依狀態進入對應分支；整份檔案有出現 `get_run` | 自動 |
| TC-004 | Goal（每個讀 run 狀態的步驟都改）；原文第 115 行 | 功能 | 改完後的檔案 | 讀「## SUBMITTED」那一節 | 原本寫的 `tw runs list shows SUBMITTED` 已改成用平台工具（`list_runs`／`get_run`）讀狀態；`tw launch` 的說法也不見了；節內仍保留 `scripts/on_site.sh --script scripts/why_pending.sh`（站上排程器的問法） | 自動 |
| TC-005 | Goal；原文第 139 行 `tw runs view -i <id> tasks` | 功能 | 改完後的檔案 | 讀「## RUNNING」開頭「per-task progress」那一行 | 看每個 task 進度改用 `get_run`（它回每個 process 的 task 數字與失敗 task）；該行沒有 `tw` | 自動 |
| TC-006 | Goal「`get_run`（…failure_reason）」；原文第 241–242 行 | 功能 | 改完後的檔案 | 讀「## FAILED」中「No refusal lines up」那一條 | 找失敗 task、取失敗原因改用 `get_run`，並提到它的 `failure_reason`（Nextflow 自己寫的失敗原因）；`tw runs view … tasks`、`tw runs view … download --type log` 兩句已改掉或明講 v3 尚未提供；`.command.err`／`.exitcode` 的讀法與「Jev triage」那一段的位置不變 | 自動 |
| TC-007 | Goal；原文第 565 行 `tw runs list` | 功能 | 改完後的檔案 | 讀「## UNKNOWN」那一節 | 「平台回報了本檔沒有分支的狀態」改成指 `list_runs`／`get_run` 回報的狀態；仍寫「照原樣說出回報的狀態字、不猜」；沒有 `tw` | 自動 |
| TC-008 | Rule 2；原文第 345 行 `tw runs view -i <id> params` | 功能 | 改完後的檔案 | 讀「Jev categories」裡 `params` 那一節 | 不再有 `tw runs view … params`。要嘛換成 v3 存在的工具，要嘛這一步仍在、並白話寫「v3 尚未提供」。不得憑空造一個工具名 | 自動 |
| TC-009 | Rule 2；原文第 391–404 行「Reading a measurement」的三條 `tw runs view` | 功能 | 改完後的檔案 | 讀「## Reading a measurement」的程式碼區塊 | 區塊裡不再有 `tw …` 指令。每個量測（metrics、resources-usage、resources-requested）要嘛換成存在的工具，要嘛白話寫「v3 尚未提供」；同節提到的 `pipeline_info/execution_trace_*.txt` 路徑與下面的判讀表（137／85%／30% 等）仍在 | 自動 |
| TC-010 | Goal；Rule 3（只改「怎麼讀狀態」）；原文第 18–32 行 | 功能 | 改完後的檔案 | 讀「## Before anything else」 | 「每個 tw 呼叫都要先 source env.sh、都要帶 `--workspace`」那兩段（只為 tw 而寫）已移除；`scripts/intro.sh runs` 與結尾 `scripts/intro.sh --end runs` 仍在 | 自動 |
| TC-011 | Goal；Rule 1（以平台為準）；原文第 34 行「Seqera Platform is the only source of truth for run state. Start there」 | 功能 | 改完後的檔案 | 找這句與同段 | 不再說「Seqera Platform 是唯一真相、先去那裡看」；改為依 v3 的來源（平台的 MCP 工具）。「再補兩樣平台看不到的：站上排程器在做什麼、站上拒絕送出什麼」的意思保留 | 自動 |
| TC-012 | Rule 1「name only tools that exist on v3」；Tests 第 1 點「every MCP tool name it mentions in backticks exists in mcp_server.py」 | 功能 | `platform/abf_platform/mcp_server.py` 目前註冊的工具：`list_runs`、`get_run`、`list_compute_envs`、`get_compute_env`、`list_agents`、`list_site_files`、`launch`、`cancel`、`resume`、`relaunch` | 取出 SKILL.md 中被當成「MCP 工具」介紹的反引號名稱 | 每一個都在上列十個之中；沒有 `list_pipelines`、`get_task`、`get_logs`、`download_log` 這類不存在的工具名 | 自動 |
| TC-013 | Rule 1「exact tool names and arguments」 | 功能 | 工具的引數：`get_run` 用 `run_id`；`cancel`／`resume`／`relaunch` 只用 `run_name`；`list_site_files` 用 `compute_env` 與 `path` | 讀 SKILL.md 裡每個示範呼叫或說明引數的地方 | 引數名稱與上列一致；沒有替 `resume`／`relaunch`／`cancel` 另加「新參數」或「新資源大小」之類不存在的引數 | 自動 |
| TC-014 | Tests「A test … that fails today」 | 功能 | main 上原本的 `skills/runs/SKILL.md`（18 處 tw） | 驗收者把 main 版 SKILL.md 放進同一支新測試跑 | 新測試對 main 版**失敗**，對改完後的版本**通過**（證明它真的會抓到 tw） | 自動：驗收者在兩個版本各跑一次 |

## 區塊 2 — 動作只「請求」，由人確認（計畫 Goal、Tests 第 1 點）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | Goal「each only asks; the person confirms on a human channel」；Tests「wherever it mentions cancel/resume/relaunch it also says a person confirms」 | 功能 | 改完後的檔案 | 找出每一處把 `cancel`、`resume`、`relaunch` 當工具提到的段落（含「## CANCELLED」那一段） | 同一段內都寫明「要由人確認／按送出」（例如原文的「after the person says yes each time」）；沒有任何一處只提工具、不提人確認 | 自動 |
| TC-021 | Goal「never describe the AI as confirming」 | 例外 | 改完後的檔案 | 找所有談「確認／說 yes／送出」的句子 | 這些句子的主詞都是人（使用者）。沒有「AI 確認」「我確認後送出」「AI 回答表單」「AI 替使用者按 yes」這類說法 | 自動 |
| TC-022 | Rule 3；原文第 561 行 | 功能 | 改完後的檔案 | 讀「## CANCELLED」最後一段 | 仍說：失敗或取消的 run 可用名稱續跑（`resume`：同資料夾、接著跑）或原樣重跑（`relaunch`：新資料夾、從頭）；且仍說樣本與參數沿用第一次 launch，要改就是新的 `launch` | 自動 |
| TC-023 | Rule 1（工具的實際能力）；`mcp_server.py` 對 `resume`／`relaunch` 的描述「cannot be changed here」 | 例外 | 改完後的檔案；RUNNING 與 Jev 路由裡有「調高時間／換小一點的盒子再 relaunch」的步驟 | 讀這些步驟 | 沒有任何一句說 `resume` 或 `relaunch` 工具可以改時間、記憶體或參數。要改資源是「新的 launch」，或這一步標明「v3 尚未提供」；`relaunch_with_override.sh` 的處理見 TC-030 | 自動 |
| TC-024 | 憲法「Manual walkthrough」；`docs/TESTING.md`「Resume and relaunch (009e)」第 2 步 | 功能 | `docs/TESTING.md` 該節 | 人讀 `skills/runs/SKILL.md` 的 resume／relaunch／cancel 說法 | 說清楚每個動作都要人點 yes、樣本與參數不能改 | 手動：`docs/TESTING.md`「Resume and relaunch (009e)」第 2 步 |

## 區塊 3 — 沒有對應的步驟：明講、記帳、不造工具（計畫 Rule 2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | Rule 2；內部呼叫 `tw` 的腳本（`task_health.sh`、`tune_resources.sh`、`relaunch_with_override.sh`、`runs_board.sh`、`agent_ctl.sh`；用 `grep -n '\btw\b' scripts/<名>.sh` 可見） | 例外 | SKILL.md 仍叫 AI 執行其中任何一支 | 讀每個「叫 AI 執行這支腳本」的地方 | 每一處要嘛已改成平台工具，要嘛在原地白話寫明「這一步 v3 尚未提供」。不得讓 AI 去跑一支在沒有 tw 的 v3 必定失敗、卻沒標示的腳本。（單純點名的排版提醒段落不算「叫 AI 執行」，見 TC-045） | 自動 |
| TC-031 | Rule 2「keep the step but say plainly it is not available on v3 yet」 | 例外 | SKILL.md 中有標「v3 尚未提供」的步驟 | 讀這些步驟 | 步驟本身還在（沒有被悄悄刪掉）；用白話直接說這一步 v3 還沒有，不是含糊帶過；沒有為它編造工具名 | 自動 |
| TC-032 | Rule 2「list it in the ledger as owed」 | 功能 | `specs/skill-runs-actions/ledger.md` | 比對 SKILL.md 與 ledger | SKILL.md 每一個標「v3 尚未提供」的步驟，ledger 都有一行「待補（owed）」；ledger 沒有 SKILL.md 看不到的待補項（兩邊一一對得上） | 自動 |

## 區塊 4 — 結構、觸發、語氣不變，既有測試不退步（計畫 Rule 3、Tests 第 2 點）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | Rule 3「Keep the skill's structure, triggers」 | 功能 | main 與改完後的 SKILL.md | 比對最上方 frontmatter（`name`、`description`、`argument-hint`） | 三行與 main 完全相同（`name: runs`、`description: Check on, debug, or deliver a pipeline run`、`argument-hint: [run id or name]`） | 自動 |
| TC-041 | Rule 3「user-facing tone」 | 功能 | 改完後的檔案 | 執行 `bash tests/runs_report_format_test.sh` | 通過：SUBMITTED、RUNNING、FAILED、SUCCEEDED、CANCELLED、UNKNOWN 六個分支標題都在，且每個都有 `Status:`／`Layer:`／`I will handle:` 或 `You decide:`／`Next step:` 四行 | 自動：`tests/runs_report_format_test.sh` |
| TC-042 | Rule 3；憲法 12 | 功能 | 改完後的檔案 | 找開場與收尾 | 仍有 `scripts/intro.sh runs`（開場）與 `scripts/intro.sh --end runs`（診斷或交付完成後） | 自動 |
| TC-043 | Goal「Steps that read files on the site keep their existing site scripts」 | 功能 | 改完後的檔案 | 找站上的查詢 | `scripts/on_site.sh --script scripts/why_pending.sh`（SUBMITTED 與 RUNNING）與 `scripts/on_site.sh --script scripts/egress_ctl.sh denied`（FAILED，且位置在 Jev 步驟之前）仍在、寫法不變；若改用 `list_site_files`，節內寫明要給 `compute_env` 與 `path` | 自動 |
| TC-044 | Rule 3；Tests 第 2 點 | 功能 | 改完後的檔案 | 執行 `bash tests/jev_test.sh` | 通過：「No refusal lines up」→「137, or killed」→「No `.command.log`」→ `scripts/jev.sh triage --err` →「Anything else」→「On a site with unrestricted egress」的順序不變；`first failing task`、`Jev 判斷：`、各 `####` 類別小節都還在 | 自動：`tests/jev_test.sh` |
| TC-045 | Rule 3；Rule 4 | 功能 | 改完後的檔案 | 執行 `bash tests/column_output_relay_rule.sh` | 通過：「排版輸出要放在 fenced code block、PITFALLS 35」那段仍在，且仍點名所有用空格排版的腳本（`runs_board.sh`、`settings.sh`、`status.sh` 等）。若執行者刪了名字，必須依規則 4 改測試並寫進 ledger | 自動：`tests/column_output_relay_rule.sh` |
| TC-046 | Tests「tests/run_all.sh stays green」 | 功能 | 在 WSL／Linux，或看 CI 結果 | 執行 `bash tests/run_all.sh` | 全綠；總數包含新增的那一支 | 自動：`tests/run_all.sh` |
| TC-047 | Tests「flow_skills_layout_test.sh, skill_portability_test.sh, skill_names_command_file_test.sh, commands_scope_tw_to_the_workspace.sh etc. either stay green or are updated per rule 4」 | 功能 | 改完後的檔案 | 逐支執行這四支（再加 `skill_requires_intro_test.sh`、`commands_resolve_their_own_paths.sh`、`command_layer_is_site_neutral.sh`、`egress_allow_test.sh`、`off_design_single_path.sh`、`works_without_host_test.sh`） | 每一支通過，或依規則 4 有寫在 ledger 的更新理由 | 自動：上列各測試檔 |

## 區塊 5 — 淘汰舊測試的規矩（計畫 Rule 4）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | Rule 4「each retired assertion must be replaced by one that pins the new behaviour, or listed in the ledger with the reason」 | 例外 | `git diff main -- tests/` | 驗收者逐支比對有被動到的測試檔 | 沒有任何斷言被默默刪除、放寬、跳過，或把期望值改成配合新輸出；被拿掉的斷言，要嘛有一條釘住新行為的取代，要嘛 ledger 寫了「不再適用」的理由 | 自動：驗收者對 main 做 diff |
| TC-051 | Rule 4 | 功能 | `specs/skill-runs-actions/ledger.md` | 讀 ledger | 明講有沒有淘汰任何只釘 tw 時代字句的斷言；有的逐條列出（被拿掉的斷言、取代它的新斷言或不再適用的理由）；沒有就明寫「無」 | 自動 |

## 區塊 6 — 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 不在範圍「Other skills (one PR each, later)」 | 不在範圍 | 這個 PR 的 diff | `git diff main --stat -- skills/` | 只有 `skills/runs/SKILL.md` 有變；`skills/setup`、`skills/launch`、`skills/downstream`、`skills/finish`、`skills/operational` 沒變 | 自動：驗收者對 main 做 diff |
| TC-061 | 不在範圍「platform/ code」 | 不在範圍 | 同上 | `git diff main --stat -- platform/` | 沒有任何變動 | 自動 |
| TC-062 | 不在範圍「hooks/」 | 不在範圍 | 同上 | `git diff main --stat -- hooks/` | 沒有任何變動 | 自動 |
| TC-063 | 不在範圍「CHANGELOG.md is NOT edited」 | 不在範圍 | 同上 | `git diff main --stat -- CHANGELOG.md` | 沒有任何變動 | 自動 |
| TC-064 | 不在範圍「docs/PLATFORM.md not edited」 | 不在範圍 | 同上 | `git diff main --stat -- docs/PLATFORM.md` | 沒有任何變動 | 自動 |
| TC-065 | Rule 4「No other skill or script is changed in this PR; scripts still used by other skills stay」 | 不在範圍 | 同上 | `git diff main --stat -- scripts/` | `scripts/` 底下沒有任何檔案被改、刪或新增（`runs_board.sh`、`task_health.sh`、`tune_resources.sh` 等都留著） | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 第 2 條：不得另存一份 run 狀態、不得有第二條送出路徑 | 功能 | 改完後的 SKILL.md | 執行 `bash tests/no_second_run_state_test.sh`，並讀 SKILL.md 有無新增「把 run 狀態存成檔／快取」的指示 | 測試通過；SKILL.md 只叫 AI 向平台讀狀態，沒有叫它寫檔保存 run 狀態；唯一的送出方式是 `resume`／`relaunch` 這種「請求後由人確認」的工具，沒有 `tw launch`、`sbatch` 等直接送出 | 自動：`tests/no_second_run_state_test.sh` |
| TC-071 | 第 5 條：沒有 hooks、沒有 `.claude-plugin/` 時仍可用 | 功能 | 改完後的檔案 | 執行 `bash tests/works_without_host_test.sh` | 通過，`skills/runs/SKILL.md` 仍在被檢查的必要檔案裡 | 自動：`tests/works_without_host_test.sh` |
| TC-072 | 第 12 條：行動意圖必須走正式流程並先出示說明 | 功能 | 改完後的檔案 | 執行 `bash tests/skill_requires_intro_test.sh` 與 `bash tests/next_step_test.sh` | 兩支通過（對 runs 的開場／收尾呼叫字串不變） | 自動：`tests/skill_requires_intro_test.sh`、`tests/next_step_test.sh` |
