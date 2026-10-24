# 測試案例：續跑可改參數與資源（c 片：說明文字、技能、ADR、對照表）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Source: specs/resume-edit-params-c/plan.md (including 裁決二, which replaces 作法 B(1) and the "get_run" wording).
This task has no spec.md; the plan is the only source. Every expected result below is taken from the plan.
Language: 繁體中文; identifiers (TC-) and file paths stay as they are.
-->

**規格**：`specs/resume-edit-params-c/plan.md`（本任務沒有 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了；也包含「這些原本就必須維持不變」的檢查。
- **例外**：出錯、不該發生的事發生時，系統或文字怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

本片只改「文字」（開場句、兩份技能、ADR、對照表、CHANGELOG），沒有程式邏輯。所以測試是在讀這些文字，並確認它們與 b 片（`resume-edit-params-b`，已合併）做出來的行為一致。

名詞：「開場句」＝ AI 客戶端一連上 MCP 就收到的那段說明（`guidance.routing_instructions()`）；「續跑」＝ `resume`（接著上次停下的地方跑）；「重跑」＝ `relaunch`（從頭再來、換新資料夾）；「六個鍵」＝ `cpus`、`memory`、`time`、`disk`、`maxRetries`、`errorStrategy`。

## User Story 1 — MCP 開場句改成新說法（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 A；測試 1 | 功能 | 修改完成 | 呼叫 `guidance.routing_instructions()` | 內容含逐字新句：`A failed run is relaunched with its name alone; a resume may also carry changed parameters and extra resource settings.` | 自動：`platform/tests/test_resume_edit_params_words.py` |
| TC-002 | 作法 A；測試 1 | 功能 | 同上 | 同上 | 內容不含舊句片段 `resumed or relaunched with its name alone` | 自動：同上 |
| TC-003 | 作法 A；裁決二 3 | 功能 | 同上 | 取 `routing_instructions()` 的 UTF-8 位元組數，並讀 `guidance.MAX_BYTES` | 位元組數 ≤ 2048，且 `MAX_BYTES` 仍等於 2048（上限沒被調高） | 自動：同上 |
| TC-004 | 作法 A「其餘字不動」 | 功能 | 同上 | 檢查 `FIXED_SENTENCE` 的其他句子 | 其他句子都還在、字句不變：`Seven tools of this server are read-only.`、`The tool forget only asks too: it deletes nothing until the person says yes in their own client's form.`、`The complete steps of each command are the MCP prompt of the same name (setup, launch, runs, downstream, finish).`，以及括號「in the terminal, abf-platform launch, cancel, resume and relaunch ask the same way」 | 自動：同上 |
| TC-005 | 作法 A 第二段 | 功能 | 同上 | 執行 `test_keep_submissions.py::test_tc107_…` | 測試通過；`:850` 那行斷言改為檢查新句；`:851`（`deletes nothing until the person says yes`）與 `:852`（長度 ≤ `MAX_BYTES`）原樣不動 | 自動：`platform/tests/test_keep_submissions.py` |
| TC-006 | 範圍：檔案；作法 A | 功能 | 修改完成 | 閱卷者看 `git diff <base>...HEAD -- platform/abf_platform/guidance.py` | 只有 `FIXED_SENTENCE` 那一句的措辭變了；`MAX_BYTES = 2048` 那行與組字、長度檢查程式一個字沒動 | 手動：閱卷者核對 git diff（見總覽疑問 1） |
| TC-007 | 作法 A 末段；必須仍綠 | 功能 | 同上 | 執行 `test_resume_entrypoints.py`（`:60-66` 的 `SENTENCE in routing_instructions()`，與 `:156` 的 TC-138）與 `test_guidance.py` | 全部通過，沒被改動；TC-138 結尾的「用 skills 目錄產生的開場句＝預設產生的開場句」仍成立 | 自動：`platform/tests/test_resume_entrypoints.py`、`platform/tests/test_guidance.py` |
| TC-008 | 不做：不動 routing 表 | 不在範圍 | 同上 | 閱卷者比對 `skills/operational/SKILL.md` 的「The five commands」下的指令表與 routing 段落（`**The user does not have to name a command.**` 那段）在 base 與 HEAD 是否相同 | 表格與該段一個字沒變（只有第 131 行那一段被改） | 手動：閱卷者核對 git diff |

## User Story 2 — 兩份技能與「已知後果」的說法（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 作法 B；測試 2 | 功能 | 修改完成 | 用 `guidance.read_skill` 讀 `operational` 與 `runs` | 兩份都含 `params` 與 `extra_config`，並說明是 `resume` 另可帶的 | 自動：`platform/tests/test_resume_edit_params_words.py` |
| TC-011 | 作法 B；測試 2 | 功能 | 同上 | 檢查兩份技能 | 兩份都含六個允許的鍵：`cpus`、`memory`、`time`、`disk`、`maxRetries`、`errorStrategy`；且這六個鍵與 `abf_station/launch.py` 的 `EXTRA_KEYS` 完全一致（技能說的白名單＝實際白名單） | 自動：同上 |
| TC-012 | 作法 B；測試 2 | 功能 | 同上 | 檢查兩份技能與 `abf_launch/cli.py` 的 `resume` 子指令 | 兩份都含 `--param`、`--params-file`、`--config-file`；`resume` 子指令真的有這三個旗標 | 自動：同上 |
| TC-013 | 作法 B | 功能 | 同上 | 讀兩份技能關於 `relaunch` 的說法 | 明講 `relaunch` 仍只收名稱、不能改參數 | 自動：同上 |
| TC-014 | 作法 B（operational） | 功能 | 同上 | 讀 `operational` 該段 | 說明 `params` 只寫要改的鍵、蓋在第一次送出的參數上、不能刪除任何參數 | 自動：同上 |
| TC-015 | 作法 B；測試 2 | 功能 | 同上 | 讀兩份技能 | 兩份都說：樣本、管線、版本、運算環境要換就是新的 `launch`（含字樣 new `launch`） | 自動：同上 |
| TC-016 | 作法 B（operational） | 功能 | 同上 | 讀 `operational` 該段 | 說明用到被改動的參數或資源的 task 會重跑，其餘沿用（cache） | 自動：同上 |
| TC-017 | 作法 B 末段；測試 2 | 功能 | 同上 | 讀 `operational` | 仍有至少一行同時含 `resume` 與 `relaunch`（TC-138 要找的那行）；`runs` 也是 | 自動：同上，並跑 `test_resume_entrypoints.py` |
| TC-018 | 作法 B(2)(3)；測試 3 | 功能 | 同上 | 讀 `runs` | 不含 `` `relaunch` and `resume` cannot change parameters ``；也不含「The samples and parameters are those of the first launch; changing them is a new `launch`」的舊寫法（改成與 operational 一致） | 自動：同上 |
| TC-019 | 作法 B(2)② | 功能 | 同上 | 讀 `runs` 原第 345 行那一帶 | 寫的是：`relaunch` 不能改參數；`resume` 可帶修正後的 `params`；並保留「改樣本或管線是新分析、用 `launch`」 | 自動：同上 |
| TC-020 | 裁決二 1 | 功能 | 同上 | 讀 `runs` 的「Actions only ask」段 | 有兩句交代：(1) 同一份改動在按「是」之後再呼叫一次，回的是同一個工作編號；(2) 不同的改動，或改動與一般續跑互換，會被「只能對最新的一次」規則拒絕，訊息指出已存在的那一次 | 自動：同上 |
| TC-021 | 作法 B「`:132` 不改」 | 功能 | 同上 | 閱卷者比對 `runs` 的「🤖 marks a step taken alone」那段（resume 算可還原） | 與 base 一個字沒變 | 手動：閱卷者核對 git diff |
| TC-022 | 裁決 3 | 例外 | 同上 | 搜尋兩份技能、ADR 註記、對照表、CHANGELOG 新增的文字 | 沒有任何一句暗示組合流程（composed）或 Google Batch 的續跑可以改參數；CHANGELOG 明講這兩種仍拒絕 | 自動：同上 |
| TC-023 | 必須仍綠；環境事實 | 功能 | 同上 | 執行 `tests/skill_runs_uses_actions_test.sh`、`platform/tests/test_launch_docs.py`、`platform/tests/test_station_docs.py` | 全部通過，包括該 shell 測試的 TC-023（`runs` 沒有任何一行說 relaunch／resume 可改參數或資源而沒帶「cannot／not／never／same／new `launch`」之類的限定）與「舊版 tw-era 夾具必須讓檢查失敗」；`tests/fixtures/runs_skill/SKILL.tw-era.md` 不被改動 | 自動：`tests/skill_runs_uses_actions_test.sh` |
| TC-024 | 不做：不新增 skill、不新增 MCP 工具、不改 `launch` 技能 | 不在範圍 | 同上 | 閱卷者列出 `skills/` 目錄與 MCP 工具清單，並比對 `skills/launch/SKILL.md` | 沒有新的 skill 目錄；工具清單（`mcp_server.py`）不變；`skills/launch/SKILL.md` 沒被改 | 手動：閱卷者核對 git diff |

## User Story 3 — ADR 0009、對照表、CHANGELOG（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 作法 C；裁決二 2；測試 4 | 功能 | 修改完成 | 讀 `docs/adr/0009-web-layout-three-panes.md` | 含逐字一行：`（Amended by the resume-edit-params task, 2026-10: a resume may change some parameters and add resource settings and stays the same analysis; changing the samples, pipeline, revision or compute environment still starts a new analysis.）`；它自成一行，放在第 2 點最後一行（`analysis; changing the samples or the parameters starts a new analysis.`）之後、第 3 點之前 | 自動：`platform/tests/test_resume_edit_params_words.py` |
| TC-031 | 作法 C「其他段落不動」；測試 4 | 功能 | 同上 | 檢查 ADR 其餘內容，並比對 base 與 HEAD | 原句 `changing the samples or the parameters starts a new analysis` 仍在；與 base 相比只多了那一行，沒有任何一行被刪或被改 | 自動：同上（另由閱卷者以 git diff 核對） |
| TC-032 | 作法 C；測試 5 | 功能 | 同上 | 讀 `docs/SEQERA_PARITY.md` | Resume 那一列逐字為 `\| Resume \| Have, with edit \| parameters and a restricted resource config can be changed on resume (CLI, MCP); compute-environment switch and web form: not done \|`，舊列 `\| Resume \| Have \| \|` 不再存在 | 自動：同上 |
| TC-033 | 作法 C | 功能 | 同上 | 檢查對照表其他列 | `\| Relaunch \| Have \| \|` 等其他列與 base 相同，沒被連帶改動 | 自動：同上 |
| TC-034 | 作法 C；測試 5；必須仍綠 | 功能 | 同上 | 數各節標題的項數與星號 | 各節項數仍為 A16 B11 C1 D5 E9 F13 G2 H7 I3 J9 K7、總和 83、句子 `lists 83 named items` 與 `the original count was 84` 仍在、★ 項正好 4 個；`tests/platform_direction_docs_test.sh`、`test_gcb_ce.py:865`、`test_gcb_launch.py:1160` 通過 | 自動：同上，並跑 `tests/platform_direction_docs_test.sh` |
| TC-035 | 作法 C；測試 6 | 功能 | 同上 | 比對 `CHANGELOG.md` 的 `3.0.0-dev` 清單與 base | 只多出一條與 resume 可改參數有關的項目（不是零條、也不是多條） | 自動：同上 |
| TC-036 | 作法 C | 功能 | 同上 | 讀那一條 | 說明 `resume` 可帶 `params` 與 `extra_config`，並列出白名單（六個鍵） | 自動：同上 |
| TC-037 | 作法 C | 功能 | 同上 | 讀那一條 | 說明對組合流程（composed pipeline）與 Google Batch 仍拒絕，且 `relaunch` 不變 | 自動：同上 |
| TC-038 | 作法 C；Done when | 功能 | 同上 | 讀那一條 | 明寫不需要 migration，以及未在國網（NCHC）實測 | 自動：同上 |
| TC-039 | 作法 C；環境事實（只加一條） | 功能 | 同上 | 閱卷者比對 `CHANGELOG.md` 其餘行 | 既有各條原樣保留，一個字沒變 | 手動：閱卷者核對 git diff |

## User Story 4 — 範圍與完成標準（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 範圍：檔案（9 個）；Done when | 功能 | 修改完成 | 閱卷者執行 `git diff <base>...HEAD --stat` | 只出現這 9 個路徑：`platform/abf_platform/guidance.py`、`platform/tests/test_keep_submissions.py`、`skills/operational/SKILL.md`、`skills/runs/SKILL.md`、`docs/adr/0009-web-layout-three-panes.md`、`docs/SEQERA_PARITY.md`、`CHANGELOG.md`、`platform/tests/test_resume_edit_params_words.py`、`specs/resume-edit-params-c/ledger.md`；（plan.md 是計畫給的，不算實作改動） | 手動：閱卷者核對 git diff |
| TC-041 | 不做：`PLATFORM.md`、`TESTING.md`（d 片） | 不在範圍 | 同上 | 閱卷者看 diff | `docs/PLATFORM.md` 與 `docs/TESTING.md` 沒被改 | 手動：閱卷者核對 git diff |
| TC-042 | 不做：不改程式邏輯 | 不在範圍 | 同上 | 閱卷者看 diff | `web.py`、`abf_station/*`、`abf_launch/*`、`mcp_server.py`、`chat_tools.py`、`hooks/*`、`scripts/launch_recheck.sh` 都沒被改；`guidance.py` 除那句字串外沒有邏輯變動 | 手動：閱卷者核對 git diff |
| TC-043 | 範圍：`test_keep_submissions.py` 只准動 `test_tc107_…` | 功能 | 同上 | 閱卷者看該檔 diff | 只有 `:850` 那一行斷言被改；其他測試與同一測試的 `:851`、`:852` 不動；沒有被刪除、放寬、跳過的斷言 | 手動：閱卷者核對 git diff |
| TC-044 | 失敗先行測試（每個先紅） | 功能 | 同上 | 閱卷者確認新檔含 7 個具名測試（開場句、兩份技能、runs 不再說不能改、ADR、對照表 Resume 列＋項數不變、CHANGELOG），並把新測試對 base 的文字跑一次 | 新檔存在、各測試名稱對得上；對 base 的文字至少 Resume 列、開場句、ADR 註記、CHANGELOG 這幾個會失敗（不是永遠綠） | 手動：閱卷者在 base 上跑新測試 |
| TC-045 | Done when（ledger） | 功能 | 同上 | 讀 `specs/resume-edit-params-c/ledger.md` | 貼有 `git diff --stat`，以及 `guidance.py`、`test_keep_submissions.py` 的 `git diff`，內容與實際 diff 一致 | 手動：閱卷者讀檔核對 |
| TC-046 | Done when；完成標記 | 功能 | 同上 | 在 WSL 跑 `tests/run_all.sh`；看 CI | 全套 `platform/tests`、`tests/` shell 測試全綠，CI 綠；執行者的完成標記為 `GREEN <HEAD sha>` 且工作目錄乾淨 | 自動：`tests/run_all.sh` |

## 憲法與安全網

<!-- 本片只改文字，但文字是 AI 客戶端的行為依據；寫入要人說 yes、續跑只在同一個專屬資料夾、原本四個檔不被改，這三條底線（計畫「不變的底線」）不能被文字悄悄改弱。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 底線：任何寫入都要人說 yes（ADR 0006 的 gate） | 功能 | 修改完成 | 讀兩份技能與開場句；跑 `tests/skill_runs_uses_actions_test.sh` 的 TC-020／TC-021 | 帶改動的 `resume` 仍明講「只是詢問、要人在自己的管道說 yes、AI 不能代說」；operational 仍有 `Each time asks the person and waits for their yes`；開場句仍有 `does not start anything until the person says yes ... and you cannot say it for them`；沒有任何一句說改動可以免確認 | 自動：`platform/tests/test_resume_edit_params_words.py`；`tests/skill_runs_uses_actions_test.sh` |
| TC-051 | 底線：續跑只在同一個專屬資料夾；原本四個檔不被改 | 功能 | 同上 | 讀兩份技能與新增的 ADR、對照表、CHANGELOG 文字 | operational 與 runs 仍說 `resume` 在同一個資料夾（same folder）接著跑；沒有任何一句說改動會改寫 `samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh`；改動是「蓋在第一次送出的參數上」 | 自動：同上 |
| TC-052 | 實作期間不准改的檔 | 不在範圍 | 同上 | 閱卷者看 diff | `specs/**/spec.md`、任何 `test-case*.md`、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json` 都沒被改；本合約簽定後也沒被實作者改動 | 手動：閱卷者核對 git diff |
