# 測試案例：plugin 的 launch／setup skill 標明「tw 流程只適用 v2」（plugin-launch-v2-only，M1-09）

**規格**：`specs/plugin-launch-v2-only/plan.md`（本任務為 docs 類，無 `spec.md`，以計畫為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應。（本任務是純說明文字，沒有此類）
- **不在範圍**：計畫「不做」的事；確認它真的沒做。

名詞（一句話）：**分流段** = 加在 `skills/launch/SKILL.md` 與 `skills/setup/SKILL.md` 開頭的「版本分流」說明，位置在 frontmatter（最上面 `---` 包起來的設定）之後、第一個 `## ` 標題（`## Before anything else`）之前。**`tw`** = Seqera 平台的命令列工具，是 v2 的做法。**MCP `launch`** = v3 平台透過 MCP 提供的「啟動分析」工具（見 `docs/PLATFORM.md`）。

維護者原話（本任務的依據）：

- 「自建平台、不依賴 Seqera；剩下是把還走 Seqera 的送出路徑換掉。」（裁示 2）
- 「v2/main 的 Seqera 路徑支援到 2027」（M1-08 的 README 措辭，供對齊）。

## User Story 1 — 打開 launch／setup skill 就知道 v3 走平台、`tw` 只給 v2（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1：兩個 SKILL.md 開頭加版本分流；失敗先行測試 | 功能 | 完成修改後的 `skills/launch/SKILL.md` | 在分流段裡找 `abf-platform launch` | 分流段內出現字串 `abf-platform launch` | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-002 | 同上 | 功能 | 完成修改後的 `skills/setup/SKILL.md` | 在分流段裡找 `abf-platform launch` | 分流段內出現字串 `abf-platform launch` | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-003 | 作法 1：v3 → `abf-platform launch`／MCP `launch` | 功能 | 同 TC-001 | 在 launch 的分流段找 MCP 的 `launch` 說法 | 分流段同時說明 v3 也可以用 MCP 的 `launch`（字面含 `MCP`） | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-004 | 同上 | 功能 | 同 TC-002 | 在 setup 的分流段找 MCP 的 `launch` 說法 | 分流段同時說明 v3 也可以用 MCP 的 `launch`（字面含 `MCP`） | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-005 | 作法 1：「以下 `tw` 流程只適用 v2」 | 功能 | 同 TC-001 | 讀 launch 的分流段 | 分流段明說「以下 `tw` 流程只適用 v2」的意思：同一段內同時出現 `v2` 與 `tw`，且語意是 `tw` 只給 v2 | 自動：`tests/skills_name_the_v3_launch_path.sh`（字串）；語意由驗收者讀檔 |
| TC-006 | 同上 | 功能 | 同 TC-002 | 讀 setup 的分流段 | 同 TC-005：同一段內同時出現 `v2` 與 `tw`，語意是 `tw` 只給 v2 | 自動：`tests/skills_name_the_v3_launch_path.sh`（字串）；語意由驗收者讀檔 |
| TC-007 | 作法 1：「連到 `docs/PLATFORM.md`」 | 功能 | 同 TC-001 | 讀 launch 的分流段 | 分流段內出現 `docs/PLATFORM.md`，且該檔真的存在 | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-008 | 同上 | 功能 | 同 TC-002 | 讀 setup 的分流段 | 分流段內出現 `docs/PLATFORM.md`，且該檔真的存在 | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-009 | 目標：「一打開就知道」→ 位置在開頭 | 功能 | 同 TC-001 | 比較分流段與 `## Before anything else` 標題的行號 | 分流段在 `## Before anything else` 之前（還沒進入任何 `tw` 操作步驟前就看得到） | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-010 | 同上 | 功能 | 同 TC-002 | 同 TC-009，對 setup | 分流段在 `## Before anything else` 之前 | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-011 | 維護者原話 1（自建平台、不依賴 Seqera） | 功能 | 兩個 SKILL.md 都已修改 | 在每個分流段內，比較 `abf-platform launch` 與第一個 `tw` 出現的先後 | 兩個檔的分流段都是 v3 做法（`abf-platform launch`）先於 `tw`；分流段沒有叫 v3 使用者去跑 `tw` 或依賴 Seqera | 自動：`tests/skills_name_the_v3_launch_path.sh`（先後）；語意由驗收者讀檔 |
| TC-012 | 作法 1／不做：「不刪 v2 內容」 | 不在範圍 | 比對 base 與修改後的兩個 SKILL.md | 看 `git diff <base>...HEAD -- skills/launch/SKILL.md skills/setup/SKILL.md` | 兩檔都只有新增行，沒有任何被刪除或改寫的原有行（v2 的 `tw` 流程原封不動） | 手動：驗收者看 diff |

## User Story 2 — `scripts/ce_apply.sh` 頂部註解同樣標明（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 作法 2：「`ce_apply.sh` 頂部註解加一行同樣意思」 | 功能 | 修改後的 `scripts/ce_apply.sh` | 讀檔案最前面連續的註解區塊 | 註解區塊內有一行說：這支腳本屬於 v2 的 `tw`／Seqera 流程；v3 用 `abf-platform launch`（同一行或相鄰行含 `v2` 與 `abf-platform launch`） | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-014 | 範圍：「只動頂部註解」 | 功能 | 比對 base 與修改後的 `scripts/ce_apply.sh` | 看 diff | 所有新增行都以 `#` 開頭，沒有刪除或改動任何非註解行；第 1 行仍是 `#!/bin/bash` | 自動：`tests/skills_name_the_v3_launch_path.sh`（第 1 行與新增行為註解）；diff 由驗收者核對 |
| TC-015 | 範圍：「只動頂部註解」（腳本行為不變） | 功能 | 修改後的 `scripts/ce_apply.sh` | 執行 `bash -n scripts/ce_apply.sh`（只檢查語法，不執行腳本） | 沒有語法錯誤 | 自動：`tests/skills_name_the_v3_launch_path.sh` |

## User Story 3 — `docs/MIGRATION.md` 加「從 v2 的 tw 流程到 v3 平台啟動」一節（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 作法 3：加一節 | 功能 | 修改後的 `docs/MIGRATION.md` | 列出所有 `## ` 標題 | 比原本多一個標題，且標題同時點出 v2 的 `tw` 流程與 v3 平台啟動（語言跟隨該文件，不要求逐字中文） | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-017 | 失敗先行測試：MIGRATION.md grep 到 `abf-platform launch` | 功能 | 同 TC-016 | 在新增的那一節內找 `abf-platform launch` | 新增的那一節內出現 `abf-platform launch`（不是只在檔案別處剛好有） | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-018 | 作法 3：「對照表（v2 指令 → v3 做法）」 | 功能 | 同 TC-016 | 看新增那一節 | 節內有一張表，表頭一欄是 v2 的指令、一欄是 v3 的做法，至少一列資料 | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-019 | 作法 3 對照表內容 | 功能 | 同 TC-016 | 看對照表的列 | 有一列是 v2 的 `tw launch` 對到 v3 的 `abf-platform launch`；且表或表旁文字也提到 MCP `launch` | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-020 | 作法 3／不做：不刪既有內容 | 不在範圍 | 比對 base 與修改後的 `docs/MIGRATION.md` | 看 diff | 原有 6 節（含「5. Going back to v2」「6. Not built yet」）都還在，沒有被刪除或改寫的原有行；只新增 | 手動：驗收者看 diff |
| TC-021 | 維護者原話 2（支援到 2027），供對齊 | 功能 | 修改後的 `docs/MIGRATION.md` 與兩個 SKILL.md、`ce_apply.sh` 的新增文字 | 在所有新增文字裡找 v2 支援期限的說法 | 若有寫 v2／Seqera 路徑的支援期限，年份必須是 2027，不得出現別的年份；沒寫期限則此條自然成立 | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-022 | 維護者原話 1（自建平台、不依賴 Seqera） | 功能 | 同 TC-016 | 看對照表的「v3 做法」那一欄 | v3 做法欄沒有任何 `tw` 指令，也沒有要求使用者先有 Seqera 帳號或 token | 自動：`tests/skills_name_the_v3_launch_path.sh`；語意由驗收者讀檔 |

## User Story 4 — 新測試先紅後綠；其他東西不動（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 失敗先行測試：新增 `tests/skills_name_the_v3_launch_path.sh` | 功能 | 修改後的 repo | 執行 `bash tests/skills_name_the_v3_launch_path.sh` | 檔案存在、可執行、結束碼 0；它對三個檔（兩個 SKILL.md 與 `MIGRATION.md`）各自檢查，任何一個缺 `abf-platform launch` 就失敗（不是三個合起來有一個就過），且讀不到檔案時會失敗而不是當成通過 | 自動：`tests/skills_name_the_v3_launch_path.sh` |
| TC-024 | 失敗先行測試：「先寫、現在會紅」 | 功能 | 把新測試放到只有計畫、尚未修改三個檔的 base 狀態 | 對 base 版的三個檔執行這支新測試 | 測試失敗（紅）；修改後才變綠。若在 base 就綠，代表測試沒測到東西 | 自動：驗收者在 base 檔案上跑一次對照 |
| TC-025 | 不做：「不改 plugin 版號」 | 不在範圍 | 比對 base 與 HEAD | 看 `.claude-plugin/plugin.json` 與其他放版號的檔 | `.claude-plugin/plugin.json` 不在 diff 內，版號沒變 | 手動：驗收者看 diff |
| TC-026 | 不做：「不改 `README.md`（M1-08）」 | 不在範圍 | 比對 base 與 HEAD | 看 `git diff --name-only <base>...HEAD` | `README.md` 不在清單內 | 手動：驗收者看 diff |
| TC-027 | 範圍：檔案（只有四個檔） | 不在範圍 | 比對 base 與 HEAD | 看 `git diff --name-only <base>...HEAD` | 變動的檔案只有 `skills/launch/SKILL.md`、`skills/setup/SKILL.md`、`scripts/ce_apply.sh`、`docs/MIGRATION.md`、新測試 `tests/skills_name_the_v3_launch_path.sh`，以及 `specs/plugin-launch-v2-only/` 底下的任務檔；其他 skill（`runs`／`downstream`／`finish`／`operational`）、`hooks/`、`docs/PLATFORM.md`、`docs/ROADMAP.md`、`.github/` 都沒動 | 手動：驗收者看 diff |
| TC-028 | 失敗先行測試：「兩個既有測試仍須過（不得弱化）」 | 功能 | 修改後的 repo | 比對 `tests/command_layer_is_site_neutral.sh` 與 `tests/commands_scope_tw_to_the_workspace.sh` 和 base，並各跑一次 | 兩個檔與 base 完全相同（沒被放寬），且兩個都通過 | 自動：`tests/command_layer_is_site_neutral.sh`、`tests/commands_scope_tw_to_the_workspace.sh` |
| TC-029 | 完成標準：「新舊測試全綠」 | 功能 | 修改後的 repo，WSL 或 Linux | 依 CLAUDE.md 在 WSL 跑 `tests/run_all.sh` | 全部通過，包含新測試；`executor-status` 為 `GREEN <HEAD sha>` | 自動：`tests/run_all.sh` |

## 憲法與安全網

本任務新增的是說明文字，但新文字放進了「被憲法測試掃描的檔案」，所以要證明沒有撞到：

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-C01 | 不變條款 4：指令層不綁定單一叢集（site-neutral） | 功能 | 兩個 SKILL.md 已加入分流段 | 掃描 `skills/` 是否出現排程器／代理等站台專屬字眼（`slurm`、`sbatch`、`squeue`、`proxy`、`relay`、`ssh`、`partition` 等） | 新增的分流段沒有帶進任何這類字眼，`tests/command_layer_is_site_neutral.sh` 通過 | 自動：`tests/command_layer_is_site_neutral.sh` |
| TC-C02 | `tw` 呼叫必須指定 workspace（`tests/commands_scope_tw_to_the_workspace.sh` 守的規則） | 功能 | 兩個 SKILL.md 已加入分流段（段內會提到 `tw`） | 掃描有提到需限定 workspace 的 `tw` 子指令的 flow skill | 新增文字沒有讓任何 flow skill 變成「提了 `tw launch`／`tw runs` 之類卻沒說 workspace 從哪來」；測試通過，且仍讀到 5 個 flow skill | 自動：`tests/commands_scope_tw_to_the_workspace.sh` |
| TC-C03 | 欄位輸出要放在程式碼區塊轉述的規則（PITFALLS 35） | 功能 | 兩個 SKILL.md 已加入分流段 | 檢查每個 SKILL.md 仍保有該規則的敘述 | 規則句子沒被新段落擠掉或改壞，`tests/column_output_relay_rule.sh` 通過 | 自動：`tests/column_output_relay_rule.sh` |
