# 測試案例：009a 把五個指令檔搬成 Agent Skills 格式

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
這是 chore，沒有 spec.md；依據是 specs/009a-skills-format/plan.md（含 Contract round 1 的覆寫決定）與維護者 2026-10-15 的例子。
-->

**規格**：`specs/009a-skills-format/plan.md`（chore，無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：**SKILL.md**＝Agent Skills 開放格式的檔案（一個資料夾裡放一份 `SKILL.md`），Claude Code、Codex 等工具都讀得懂。**stale-path guard（舊路徑守門測試）**＝`tests/flow_skills_layout_test.sh` 的 (f) 項，掃描各處有沒有還寫著舊的 `commands/<名字>.md`。**手動**欄的「TESTING 新小節」＝`docs/TESTING.md` 新增的「When a release moves the flow files (commands → skills)」。

維護者的例子（2026-10-15 原文）與對應：「指令檔改成 skill」→ TC-001、TC-004；「只加 MCP 網址就能用」（這一步只是前置）→ TC-039；「v2 凍結、v3 平台世代」→ TC-012、TC-013。計畫第 2 點「在 Claude Code 裡你打 `/agentic-bioflow:launch` 的用法和看到的流程完全一樣」→ TC-002、TC-005、TC-006、TC-015。

## User Story 1 — 五個指令檔變成 skill，用法不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 維護者例子「指令檔改成 skill」；決策 1 | 功能 | 搬家完成後的工作樹 | 檢查 `skills/setup`、`skills/launch`、`skills/runs`、`skills/downstream`、`skills/finish` | 五個資料夾裡各有一份 `SKILL.md`，且都不是空檔 | 自動：`tests/flow_skills_layout_test.sh`（a） |
| TC-002 | 決策 1、6(b)；計畫第 2 點 | 功能 | 同上 | 讀五份 `SKILL.md` 開頭的 `name:` | 每份的 `name:` 恰好等於它所在資料夾的名字（所以 Claude Code 裡的呼叫名 `/agentic-bioflow:<名字>` 不變） | 自動：`tests/flow_skills_layout_test.sh`（b） |
| TC-003 | 決策 6(c) | 功能 | 同上 | 讀五份 `SKILL.md` 開頭 | 每份都有 `description:` | 自動：`tests/flow_skills_layout_test.sh`（c） |
| TC-004 | 維護者例子「指令檔改成 skill」；決策 2 | 功能 | 同上 | 檢查專案根目錄有沒有 `commands/` | `commands/` 不存在（否則 Claude Code 會登記兩個 `/agentic-bioflow:launch`） | 自動：`tests/flow_skills_layout_test.sh`（d） |
| TC-005 | 決策 1；計畫第 2 點 | 功能 | 搬家前後的五份檔案 | 逐一比對五份檔案搬家前的 `description:` 與搬家後的 | 五條 `description:` 與搬家前逐字相同 | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-006 | 決策 1 | 功能 | 同上 | 比對 `argument-hint:` 與 `model:` | `finish` 仍是 `model: sonnet`；`launch`、`runs`、`downstream`、`finish` 的 `argument-hint:` 與搬家前相同；`setup` 仍沒有 `argument-hint:` | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-007 | 決策 1、round 1 第 1 點 | 功能 | PR 對 `v3` 的差異 | 執行 `git diff -M --stat` 並看五份檔案的內文差異 | 顯示五個 rename，相似度各 ≥ 95%；內文差異只有「新增 `name:` 一行」與「`commands/<名字>.md` 改成 `skills/<名字>/SKILL.md` 的路徑指標」，沒有別的改動 | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-008 | round 1 第 1 點 | 功能 | 搬家完成 | 搜尋五份 `SKILL.md` 內文有沒有 `commands/(setup\|launch\|runs\|downstream\|finish).md`；看 `launch/SKILL.md` 原本寫 `commands/runs.md` 的那一句 | 一個都不剩；那一句改成指向 `skills/runs/SKILL.md` | 自動：`tests/flow_skills_layout_test.sh`（f） |
| TC-009 | 決策 7 | 功能 | 搬家完成 | 在專案根目錄執行 `claude plugin validate .` | 驗證通過，輸出記在 ledger | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-010 | 決策 9 | 功能 | 搬家完成 | 看 `.claude-plugin/marketplace.json` 的 description | 開頭由「Five commands:」變成「Five skills (slash commands in Claude Code):」，句子其餘部分逐字不變 | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-011 | 決策 10 | 功能 | 搬家完成 | 看 `CHANGELOG.md` 的 Unreleased 區 | 多一行：「commands/*.md moved to skills/<name>/SKILL.md (Agent Skills format); invocation names unchanged.」，且沒有其他無關改動 | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-012 | 維護者例子「v2 凍結、v3 平台世代」；計畫標頭 | 功能 | 這個 PR | 看 PR 的 base 分支 | base 是 `v3`，不是 `main` | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-013 | 維護者例子「v2 凍結」；計畫第 3 點 | 功能 | 這個 PR | 比對 `main` 分支在這個工作前後的 commit | `main` 一個 commit 都沒多；所有改動只在 `feat/009a-skills-format` | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-014 | 決策 6（紅燈在前） | 例外 | 尚未搬家（或把某份 `SKILL.md` 暫時移走） | 跑 `tests/flow_skills_layout_test.sh` | 測試失敗並指出缺哪一份；搬家前 (a)–(e) 皆紅，ledger 有這段紅燈紀錄，搬家後轉綠 | 手動：`docs/TESTING.md` TESTING 新小節（查 ledger 紅綠證據） |
| TC-015 | 計畫第 2 點「打 `/agentic-bioflow:launch` 用法和流程完全一樣」 | 功能 | 重開 Claude Code，從這個分支安裝 plugin | 依序輸入 `/agentic-bioflow:setup`、`launch`、`runs`、`downstream`、`finish` | 五個指令各只出現一次，名字和搬家前一樣；每個打開後看到的第一段流程與搬家前一致 | 手動：`docs/TESTING.md` TESTING 新小節 |

## User Story 2 — 指向舊位置的指標與訊息跟著搬（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 決策 6(e) | 功能 | 搬家完成 | 讀 `skills/operational/SKILL.md` | 它用新路徑 `skills/<名字>/SKILL.md` 點名 setup、launch、runs、downstream、finish 五個 | 自動：`tests/flow_skills_layout_test.sh`（e） |
| TC-017 | 決策 4 | 功能 | 搬家完成 | 讀 `skills/operational/SKILL.md` 的兩處路徑指標 | 出現 `skills/<command>/SKILL.md` 與 `${CLAUDE_PLUGIN_ROOT}/skills/<command>/SKILL.md`，舊的 `commands/<command>.md` 兩種寫法都不見了 | 自動：`tests/skill_names_command_file_test.sh`（:26、:27 已改） |
| TC-018 | 決策 4；round 1 第 3 點 | 功能 | 搬家完成 | 讀 `skills/operational/SKILL.md` 原本寫 `commands/runs.md` 的那句（SUCCEEDED 段） | 改成指向 `skills/runs/SKILL.md` | 自動：`tests/flow_skills_layout_test.sh`（f） |
| TC-019 | round 1 第 2 點；憲法 III.7（印出來的指引要能找到檔案） | 功能 | 搬家完成 | 看 `scripts/init_workspace.sh:139`、`relaunch_with_override.sh:91`、`settings.sh:1005`、`setup_proof.sh:55`、`setup_verify.sh:53,61` 以及 `scripts/` 其他會印出 `commands/<名字>.md` 的 echo／printf 行 | 印出的都是 `skills/<名字>/SKILL.md`，且這些檔案真的存在 | 自動：`tests/flow_skills_layout_test.sh`（f）加（a） |
| TC-020 | round 1 第 2 點 | 功能 | 搬家完成 | 搜尋 `scripts/*` 的註解有沒有 `commands/<名字>.md` | 註解也改成新路徑；只動文字，不動程式邏輯 | 自動：`tests/flow_skills_layout_test.sh`（f） |
| TC-021 | round 1 第 3 點 | 功能 | 搬家完成 | 守門測試掃描 `tests/`、`docs/`、`scripts/`、`skills/`、`CLAUDE.md`、`README.md`，pattern 為 `commands/(setup\|launch\|runs\|downstream\|finish)\.md`，在 `tests/` 另外抓 `$ROOT/commands` | 沒有任何未豁免的舊路徑；測試通過 | 自動：`tests/flow_skills_layout_test.sh`（f） |
| TC-022 | round 1 第 3 點 | 功能 | 搬家完成 | 讀守門測試裡的豁免清單 | 豁免只有：`docs/PITFALLS.md`、`docs/adr/`、`tests/command_layer_is_site_neutral.sh` 的假資料字串、`tests/no_second_run_state_test.sh` 的 `commands/a.md` 假資料、`tests/confirm_launch_test.sh` 的閘門測試字串、守門測試檔本身；每一項旁邊有一行理由；`specs/` 與 `hooks/` 不在掃描範圍 | 手動：`docs/TESTING.md` TESTING 新小節 |

## User Story 3 — 測試與文件跟著搬（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 決策 3 | 功能 | 搬家完成 | 載入 `tests/lib/flow_skills.sh`，印出 `FLOW_SKILLS`，呼叫 `flow_skill_file launch` 與 `flow_skill_files` | `FLOW_SKILLS` 是「setup launch runs downstream finish」；`flow_skill_file launch` 回傳 `$ROOT/skills/launch/SKILL.md`；`flow_skill_files` 依該順序回傳五個路徑 | 自動：`tests/flow_skills_layout_test.sh` |
| TC-024 | 決策 3、round 1 第 4 點 | 功能 | 搬家完成 | 跑 `tests/commands_resolve_their_own_paths.sh`、`tests/commands_scope_tw_to_the_workspace.sh` 及其他走訪五個檔案的測試 | 每個都確實讀到 5 個檔案（測試內有數量斷言），並通過 | 自動：`tests/commands_resolve_their_own_paths.sh`、`tests/commands_scope_tw_to_the_workspace.sh` |
| TC-025 | round 1 第 4 點（不准無聲變綠） | 例外 | 暫時移走其中一份 `SKILL.md` | 跑上述走訪五個檔案的測試 | 測試失敗並說只讀到少於 5 個，不會因為「找不到就略過」而通過 | 自動：`tests/commands_resolve_their_own_paths.sh`、`tests/commands_scope_tw_to_the_workspace.sh` |
| TC-026 | round 1 第 4 點 | 功能 | 搬家完成 | 跑 `tests/site_scripts_via_on_site.sh` | 它從 `skills/<名字>/SKILL.md` 讀檔（原 :32、:46、:59 的路徑與訊息已改），並通過 | 自動：`tests/site_scripts_via_on_site.sh` |
| TC-027 | 決策 5 | 功能 | 搬家完成 | 跑 `tests/skill_portability_test.sh` | 對六份 `skills/*/SKILL.md` 都檢查：`name` 符合 `^[a-z0-9-]+$`、`description` ≤ 1024 字、frontmatter 每行是 `key: value`、每個含 `${CLAUDE_PLUGIN_ROOT}` 的段落也寫了 "otherwise"；全部通過 | 自動：`tests/skill_portability_test.sh` |
| TC-028 | 決策 5 | 功能 | 搬家完成 | 看 `tests/skill_portability_test.sh` 中「標題 `## On a host without these hooks`、層級 `H3`、`LAB_AGENTS`」的斷言 | 這幾條仍只針對 `skills/operational/SKILL.md`，沒有被套到其他五份 | 自動：`tests/skill_portability_test.sh` |
| TC-029 | 計畫「Changes」第 5 步 | 功能 | 搬家完成 | 看只在註解或 echo 文字提到 `commands/` 的測試（build_package_test、collect_provenance_test、confirm_walkthrough_test、on_site_*、positron_run_test、prepare_launch_test、settings_test、site_report_test、where_test、principle_12_test 等） | 文字改成新路徑，沒有邏輯改動；不再有未豁免的舊路徑 | 自動：`tests/flow_skills_layout_test.sh`（f） |
| TC-030 | 計畫「Changes」第 8 步；憲法「Green at every stage」 | 功能 | 搬家完成，WSL 環境 | 執行 `bash tests/run_all.sh` | 全部通過；新增的 `flow_skills_layout_test.sh` 被自動找到並列入 | 自動：`tests/run_all.sh` |
| TC-031 | 驗收通則（測試不得被放鬆） | 功能 | 被計畫列名要改的測試 | 把每個被動到的測試與 `v3` 版本逐一比對 | 只有路徑／文字／走訪檔案來源的改動，沒有刪除、放寬或跳過任何斷言（新增的「讀到 5 個」斷言是變嚴格） | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-032 | 計畫「Changes」第 6 步 | 功能 | 搬家完成 | 看 `CLAUDE.md:26` 的目錄結構那一行 | 內容為「`skills/` — the five flow skills (`setup`, `launch`, `runs`, `downstream`, `finish`, each a `SKILL.md` in Agent Skills format, exposed as slash commands in Claude Code) and `operational`」 | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-033 | 計畫「Changes」第 6 步 | 功能 | 搬家完成 | 看 `docs/TESTING.md` 原 136、161、177 行與 193 行 | 前三處的 `git diff -- … commands/ …` 檢查改成 `skills/`；193 行列出五個新路徑 | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-034 | 計畫 Facts 的文件清單 | 功能 | 搬家完成 | 看 `CLAUDE.md:113-114,163`、`docs/PRINCIPLES.md`、`docs/SETTINGS.md`、`docs/SITE_ADAPTER.md`、`docs/DOWNSTREAM.md`、`docs/FINISH.md`、`docs/LAB_AGENTS.md` | 描述目前結構的地方都用新路徑，沒有 `commands/<名字>.md` | 自動：`tests/flow_skills_layout_test.sh`（f） |
| TC-035 | round 1 第 5 點 | 功能 | 搬家完成 | 打開 `docs/TESTING.md` | 有「When a release moves the flow files (commands → skills)」小節，列出本合約所有「手動」案例要照做的檢查步驟（rename ≥95%、description 與 argument-hint／model 不變、marketplace、CHANGELOG、base 是 v3、main 沒動、validate、豁免清單、scripts／operational／hooks 差異、沒有新增 Codex／MCP 檔案、測試沒被放鬆、五個指令實際可用） | 手動：`docs/TESTING.md` TESTING 新小節 |

## User Story 4 — 這一步不做的事（優先度 P3）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-036 | 不在範圍：不改任何 skill 的指示（判斷文字） | 不在範圍 | PR 對 `v3` 的差異 | 看五份 `SKILL.md` 與 `skills/operational/SKILL.md` 的差異 | 只有 `name:` 一行與路徑指標；沒有任何判斷文字、步驟、措辭被改；也沒有把內文改成呼叫平台動作 | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-037 | 不在範圍：不動 `platform/`、`.github/`、`plugin.json` 版本、憲法 | 不在範圍 | PR 對 `v3` 的差異 | 看 `platform/`、`.github/`、`.claude-plugin/plugin.json` 的 diff | 這三處沒有任何改動（`plugin.json` 版本號不變，等於本 PR 不是發版） | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-038 | 不在範圍：不動 `scripts/` 邏輯（round 1 第 2 點只放行字串與註解） | 不在範圍 | PR 對 `v3` 的差異 | 看 `scripts/` 的 diff | 每個被改的行都是 echo／printf 的字串或註解；沒有條件、指令、變數、流程的改動 | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-039 | 維護者例子「只加 MCP 網址就能用」（這步只是前置）；不在範圍：Codex／Desktop 安裝包 | 不在範圍 | PR 對 `v3` 的差異 | 找有沒有新增 Codex 的 `plugin.json`／`mcp.json`、`.mcp.json`、`docs/INSTALL.md` | 一個都沒有；也沒有任何文件宣稱「只加 MCP 網址就能用」已經做到 | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-040 | 不在範圍：不改寫 `## On a host without these hooks` 與 H1–H3 | 不在範圍 | 搬家完成 | 跑 `tests/skill_portability_test.sh`；看 `skills/operational/SKILL.md` 該標題與 H1–H3 文字的 diff | 標題在檔內恰好出現一次且逐字不變，H1–H3 文字沒有改動 | 自動：`tests/skill_portability_test.sh` |
| TC-041 | 不在範圍：不淘汰 `tw` 時代的測試與腳本（第 6 步才做） | 不在範圍 | PR 對 `v3` 的差異 | 看 `commands_scope_tw_to_the_workspace.sh`、`no_second_run_state_test.sh`、`launch_provenance_test.sh`、`prepare_launch_test.sh`、`egress_allow_test.sh`、`runs_report_format_test.sh`、`setup_doc_test.sh` 與 `scripts/` 裡呼叫 `tw` 的 20 支腳本 | 全部還在，沒有被刪除或改成停用；`tw` 相關的斷言沒有被拿掉 | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-042 | 計畫 Facts：`docs/PITFALLS.md` 與 `specs/*` 是歷史，維持原樣；round 1 第 3 點 `docs/adr/` | 不在範圍 | PR 對 `v3` 的差異 | 看 `docs/PITFALLS.md`、`docs/adr/` 與其他功能的 `specs/*` 的 diff | 都沒有被改（本功能自己的 `specs/009a-skills-format/ledger.md` 除外） | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-043 | 計畫「Changes」第 4 步：假資料字串留著 | 不在範圍 | PR 對 `v3` 的差異 | 看 `tests/confirm_launch_test.sh:74`、`tests/command_layer_is_site_neutral.sh` 的合成輸入（約 46–53 行）、`tests/no_second_run_state_test.sh` 的 `commands/a.md` 假資料（約 250–251 行） | 這些字串沒有被改（它們是測試輸入，不是版面路徑） | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-044 | 決策 8 | 不在範圍 | PR 對 `v3` 的差異 | 看 `platform/tests/test_scope.py:65` 與 ledger | 該行 regex 仍含 `commands/`（沒有刪），且 ledger 記了「刻意保留」 | 手動：`docs/TESTING.md` TESTING 新小節 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-045 | II.5：沒有 hooks 與 `.claude-plugin/` 也能用 `skills/`、`docs/`、`scripts/` | 功能 | 搬家完成 | 跑 `tests/works_without_host_test.sh` | 縮減後的目錄（打包清單已去掉 `commands`、保留 `skills`）仍含 `skills/setup/SKILL.md`、`skills/launch/SKILL.md`、`skills/runs/SKILL.md` 且非空；「文件指到的腳本都存在」一項仍通過；整支測試通過 | 自動：`tests/works_without_host_test.sh`（:90、:94 與 tar 清單） |
| TC-046 | II.4：指令層不點名排程器、分區、佇列、中繼站 | 功能 | 搬家完成 | 跑 `tests/command_layer_is_site_neutral.sh` | 讀到的是 `skills/<名字>/SKILL.md` 的五份文字（讀到 5 份，不是 0 份），並通過 | 自動：`tests/command_layer_is_site_neutral.sh` |
| TC-047 | 計畫 Constitution Check：record-neutral 測試跑在同一份文字的新位置 | 功能 | 搬家完成 | 跑 `tests/command_layer_is_record_neutral.sh` | 讀到五份新位置的檔案並通過 | 自動：`tests/command_layer_is_record_neutral.sh` |
| TC-048 | VI.12：有動作意圖的請求要走正式流程並出現 walkthrough | 功能 | 搬家完成 | 跑 `tests/skill_requires_intro_test.sh`（:34 已改） | 對新路徑的五份 skill 仍檢查到「需要先出現介紹」的規則，並通過 | 自動：`tests/skill_requires_intro_test.sh` |
| TC-049 | II.3：不寫死個人路徑、叢集路徑 | 功能 | 搬家完成 | 跑 `tests/no_hardcoded_paths.sh` | 掃描範圍含 `skills/`；因 `commands/` 已不存在而產生的「找不到資料夾」抱怨不會出現；通過 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-050 | I.1：每支腳本標明替代工具 | 功能 | 搬家完成 | 跑 `tests/scripts_name_their_alternative.sh`（:83） | 排除清單去掉 `*commands/*`、保留 `*skills/*`，測試通過 | 自動：`tests/scripts_name_their_alternative.sh` |
| TC-051 | 安全網：hooks 不動（受保護路徑） | 功能 | PR 對 `v3` 的差異 | 看 `hooks/` 的 diff | 沒有任何改動；`hooks/plugin_intro.sh:277` 與 `hooks/confirm_walkthrough.sh:7` 的 `commands/` 註解維持原樣，並列在 ledger 的豁免清單 | 手動：`docs/TESTING.md` TESTING 新小節 |
| TC-052 | 安全網：啟動前要先看到完整指令並確認 | 功能 | 搬家完成 | 跑 `tests/confirm_launch_test.sh`，並確認該檔無改動 | 測試與在 `v3` 上的結果相同（全通過），閘門讀的是要執行的指令，不是 skill 檔位置 | 自動：`tests/confirm_launch_test.sh` |
| TC-053 | 憲法本文不可在這個 PR 修改（含 :209 的 `commands/` 字樣） | 功能 | PR 對 `v3` 的差異 | 看 `.specify/memory/constitution.md` 的 diff | 沒有任何改動 | 手動：`docs/TESTING.md` TESTING 新小節 |

<!--
Rules for the writer:
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
