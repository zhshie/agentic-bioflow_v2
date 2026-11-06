# 測試案例：tools-snapshot-profiles（補 #362 漏更新的工具快照與 launch 參數說明）

**規格**：`specs/tools-snapshot-profiles/plan.md`（本任務沒有獨立 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

名詞：「快照」是 `platform/tests/mcp/snapshots/tools.json`，記錄每個 MCP 工具（AI 助理看得到的功能）現在長什麼樣，合約測試拿它比對，擋住「工具介面被不小心改掉」。「base」是 v3 分支（改動前）。「合約測試檔」是 `platform/tests/mcp/test_mcp_contract_tools.py`。

維護者原話（來自計畫「維護者原話」，下列 TC 以這些話當輸入與預期）：
1. 「make these four green without weakening them」
2. 「regenerate/repair the snapshot following the file's own regeneration rule」
3. 「remove launch from OVER_LIMIT」
4. 「add the missing parameter descriptions in the tool definition in platform/abf_platform/mcp_server.py (descriptions in plain English, saying what the param does and when to use it)」
5. 「No other behavior change. Do not touch .github or the constitution.」
6. 「First verify on origin/v3 which of these truly fail」

## User Story 1 — 四支紅測試轉綠，launch.pipeline 有白話說明（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 原話 1「make these four green」；目標；作法 4 | 功能 | 改動完成；環境變數 `ABF_UPDATE_MCP_SNAPSHOT` 沒有設 | 跑 `cd platform && python -m pytest tests/mcp/test_mcp_contract_tools.py::test_tools_schema_matches_snapshot` | 通過：現在的工具介面與快照逐字相同（含 launch 的 `profiles`、`params` 說明、`pipeline` 說明） | 自動：`platform/tests/mcp/test_mcp_contract_tools.py::test_tools_schema_matches_snapshot` |
| TC-002 | 原話 1；失敗先行測試第 2 項 | 功能 | 同 TC-001 | 跑 `test_snapshot_is_crlf_insensitive` | 通過：快照檔改成 Windows 換行（CRLF）後比對仍與現況相同 | 自動：`test_mcp_contract_tools.py::test_snapshot_is_crlf_insensitive` |
| TC-003 | 原話 1、3「remove launch from OVER_LIMIT」；作法 3 | 功能 | 同 TC-001；launch 描述現為 599 字 | 跑 `test_over_limit_list_only_shrinks` | 通過：清單內的工具都仍超過 600 字，不再出現「launch is now 599 chars: delete it from OVER_LIMIT」 | 自動：`test_mcp_contract_tools.py::test_over_limit_list_only_shrinks` |
| TC-004 | 原話 1、4；作法 2 | 功能 | 同 TC-001 | 跑 `test_every_param_is_described` | 通過：沒有任何未說明的參數是新增的，特別是結果不再含 `('launch', 'pipeline')` | 自動：`test_mcp_contract_tools.py::test_every_param_is_described` |
| TC-005 | 目標；完成標準第 1 項 | 功能 | 同 TC-001 | 不帶環境變數，整個合約測試檔跑一遍（`python -m pytest tests/mcp/test_mcp_contract_tools.py -q`） | 全綠、0 失敗；其中 `test_descriptions_within_limit` 也綠（launch 599 ≤ 600，且不在 OVER_LIMIT） | 自動：整個 `test_mcp_contract_tools.py` |
| TC-006 | 原話 4；作法 2「是什麼、怎麼寫、何時用」 | 功能 | 取得 launch 的 `inputSchema.properties.pipeline` | 讀它的 `description` | 有說明且不是空字串；是白話英文；同時講到：這是要跑的流程（例如寫 nf-core 名稱如 `nf-core/rnaseq`，或站上已有的流程）、與 `revision` 搭配、什麼時候用 | 自動：新增或沿用的斷言讀 schema 檢查（驗收者另以快照內容核對） |
| TC-007 | 作法 2 限制；裁決 1 | 功能 | 同 TC-006 | 對 `pipeline` 說明套用禁字規則 `approve｜confirm｜confirmed_by｜void｜yes`（不分大小寫） | 完全不含任何一個禁字 | 自動：驗收者以該規則掃快照中的 `pipeline.description`；並跑 `test_launch_profiles.py`、`test_chat_tools.py` 均綠 |
| TC-008 | 裁決 3「單句不超過約 200 字元」 | 功能 | 同 TC-006 | 量 `pipeline` 說明的字元數 | 不超過約 200 字元，且是一句白話，不是為了湊字數的長文 | 自動：驗收者量快照中的字串 |
| TC-009 | 原話 2「following the file's own regeneration rule」；作法 4 | 功能 | 產品碼已改完，快照已用 `REGEN_CMD`（`ABF_UPDATE_MCP_SNAPSHOT=1 python -m pytest tests/mcp/test_mcp_contract_tools.py::test_tools_schema_matches_snapshot`）產生 | 驗收者在乾淨狀態再跑一次 `REGEN_CMD`，然後看 `git diff -- platform/tests/mcp/snapshots/tools.json` 與上一次提交比較 | 再產生一次檔案沒有任何變化（不是手改出來的）；檔案為 LF 換行、UTF-8、鍵排序、縮排 2 | 自動：驗收者重跑 `REGEN_CMD` 後比對檔案 |
| TC-010 | 作法 5；完成標準第 4 項 | 功能 | 比對 base 與 HEAD 的快照 | `git diff origin/v3...HEAD -- platform/tests/mcp/snapshots/tools.json` | 差異只有三處：launch 的 `params.description`、新增整個 `profiles` 物件（含 description）、`pipeline.description`；其他工具（含 `get_run`、`run_outputs`）零差異 | 自動：驗收者讀 diff |
| TC-011 | 允許的斷言：`test_snapshot_has_only_name_and_input_schema` | 功能 | 快照已重產 | 跑 `test_snapshot_has_only_name_and_input_schema` | 通過：快照每個工具只有 `name`、`inputSchema` 兩個頂層鍵，工具名單等於 `EXPECTED_TOOLS` | 自動：`test_mcp_contract_tools.py::test_snapshot_has_only_name_and_input_schema` |
| TC-012 | 原話 6「First verify on origin/v3 which of these truly fail」；作法 1 | 功能 | 動手前，乾淨的 v3 | 在 v3 跑整個合約測試檔，輸出貼進 ledger | ledger 有這份輸出，且紅的恰好是四支：`test_tools_schema_matches_snapshot`、`test_snapshot_is_crlf_insensitive`、`test_over_limit_list_only_shrinks`、`test_every_param_is_described`（驗收者可在 v3 重跑核對） | 自動：驗收者在 base 重跑同一指令比對 |
| TC-013 | 允許的斷言：`test_snapshot_missing_or_different_fails_without_overwrite` | 例外 | 快照與現況不同、沒設環境變數 | 跑 `test_snapshot_missing_or_different_fails_without_overwrite` | 通過：不一致時測試失敗並提示 REGEN 指令，不會自己覆寫快照（沒有悄悄吞掉差異） | 自動：`test_mcp_contract_tools.py::test_snapshot_missing_or_different_fails_without_overwrite` |
| TC-014 | 失敗先行測試「刻意破壞」①（原話 1：不弱化） | 例外 | 改動完成、全綠 | 暫時把 `pipeline` 的說明拿掉，跑整個合約測試檔，然後還原 | `test_every_param_is_described` 變紅，列出 `('launch', 'pipeline')`；ledger 有這段紅色輸出 | 自動：驗收者重現 |
| TC-015 | 失敗先行測試「刻意破壞」② | 例外 | 改動完成、全綠 | 暫時把 `"launch": 968,` 加回 `OVER_LIMIT`，跑整個合約測試檔，然後還原 | `test_over_limit_list_only_shrinks` 變紅，訊息含 `launch is now 599 chars: delete it from OVER_LIMIT` | 自動：驗收者重現 |
| TC-016 | 失敗先行測試「刻意破壞」③ | 例外 | 改動完成、全綠 | 暫時在快照改一個字元，不帶環境變數跑整個合約測試檔，然後還原 | `test_tools_schema_matches_snapshot` 變紅 | 自動：驗收者重現 |

## User Story 2 — 不弱化測試、不改其他行為（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 原話 1「without weakening them」、3；範圍：檔案 | 功能 | 比對 base 與 HEAD | `git diff origin/v3...HEAD -- platform/tests/mcp/test_mcp_contract_tools.py` | 只有刪掉 `"launch": 968,` 這一行：刪 1 行、增 0 行 | 自動：驗收者讀 diff |
| TC-018 | 原話 3；不做第 2 條 | 功能 | 同 TC-017 | 看 `OVER_LIMIT` 剩下的內容 | 只剩 `get_run`（804）與 `run_outputs`（700），數字與原本一字不差 | 自動：驗收者讀檔 |
| TC-019 | 原話 1；作法 3、6 | 功能 | 同 TC-017 | 看合約測試檔除 TC-017 那一行以外的所有內容 | `LIMIT = 600`、`UNDESCRIBED_PARAMS`、`ASPECT_GAPS`、所有斷言與其他測試檔都零差異（沒有放寬、沒有新增豁免） | 自動：驗收者讀 diff |
| TC-020 | 原話 4、5；範圍：mcp_server.py；裁決 2 | 功能 | 比對 base 與 HEAD | `git diff origin/v3...HEAD -- platform/abf_platform/mcp_server.py` | 只動「把 `pipeline: str` 改成 `Annotated[str, Field(description=...)]`」這一處；沒有別的行被改 | 自動：驗收者讀 diff |
| TC-021 | 原話 5「No other behavior change」；範圍：不動工具描述 | 功能 | 同 TC-020 | 比較 launch 的 `@server.tool(... description=...)` 文字，並跑 `test_launch_profiles.py::test_tc058` | 描述文字與 base 零差異，長度仍為 599；`test_tc058` 綠 | 自動：`platform/tests/test_launch_profiles.py::test_tc058` |
| TC-022 | 原話 5；`test_tc055`、`test_tc017_tc056_tc057`、`test_dataset_launch.py` 約 207～212 行 | 功能 | 同 TC-020 | 讀 launch 的 `inputSchema` | 參數名、型別、預設值不變；`required` 仍是 `["pipeline","revision","run_name"]`；`profiles` 仍是選填字串陣列 | 自動：`test_launch_profiles.py::test_tc055`、`test_tc017_tc056_tc057`、`test_dataset_launch.py` |
| TC-023 | 原話 5；`test_tc059` | 功能 | 同 TC-020 | 跑 `test_launch_profiles.py::test_tc059` | 通過：工具名單不增不減 | 自動：`test_launch_profiles.py::test_tc059` |
| TC-024 | 完成標準第 1 項；允許的斷言（含 `test_chat_tools.py`） | 功能 | 改動完成 | 跑 `test_launch_profiles.py`、`test_dataset_launch.py`、`test_mcp_launch_pipeline.py`、`test_actions_layer.py`、`test_head_nodefail.py`、`test_chat_tools.py` | 每個檔都綠，或與 base 的紅綠完全一致（有紅的須在 base 同樣是紅，並貼證據）；沒有因 launch 的 schema 多一個 `description` 而新紅 | 自動：上述各測試檔 |
| TC-025 | 完成標準第 2 項；原話 5 | 功能 | 比對 base 與 HEAD | `git diff --stat origin/v3...HEAD` | 只出現四類路徑：`platform/abf_platform/mcp_server.py`、`platform/tests/mcp/snapshots/tools.json`、`platform/tests/mcp/test_mcp_contract_tools.py`（-1 行）、`specs/tools-snapshot-profiles/` | 自動：驗收者讀 diff stat |
| TC-026 | 完成標準第 1 項；裁決 1 | 功能 | 完成記號 GREEN 與 HEAD 相符 | 在 WSL 跑 `tests/run_all.sh --timeout 900` | 全綠（環境性紅燈只限 README 通例所列） | 自動：`tests/run_all.sh`（executor 的完成記號即此結果） |
| TC-027 | 失敗先行測試「刻意破壞」須還原 | 例外 | TC-014～016 三次暫時破壞做完 | 看最後提交的內容 | 三個破壞都已還原：TC-010、TC-017、TC-020 的差異內容仍成立，沒有留下任何破壞痕跡 | 自動：驗收者讀 HEAD 的 diff |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-028 | 不做第 1 條：不補 `revision`、`run_name`、`ce_name`、`path_columns` 說明，不碰 `UNDESCRIBED_PARAMS`、`ASPECT_GAPS` | 不在範圍 | 比對 base 與 HEAD 的快照與 `mcp_server.py` | 看 launch 這四個參數 | 這四個參數仍沒有 `description`（快照無差異於它們）；`UNDESCRIBED_PARAMS`、`ASPECT_GAPS` 零差異 | 自動：驗收者讀 diff |
| TC-029 | 不做第 2 條：不縮短 `get_run`（804）、`run_outputs`（700） | 不在範圍 | 同 TC-028 | 看這兩個工具的描述與快照條目；跑 `test_head_nodefail.py`（約 795 行 get_run 描述） | 描述與快照條目零差異；`test_head_nodefail.py` 綠 | 自動：驗收者讀 diff；`platform/tests/test_head_nodefail.py` |
| TC-030 | 不做第 5 條與原話 5「Do not touch .github」：不把快照比對接進 CI | 不在範圍 | 比對 base 與 HEAD | `git diff origin/v3...HEAD -- .github` | 零差異，沒有新增任何 CI 步驟 | 自動：驗收者讀 diff |
| TC-031 | 原話 5「Do not touch … the constitution」 | 不在範圍 | 同 TC-030 | `git diff origin/v3...HEAD -- .specify/memory/constitution.md` | 零差異 | 自動：驗收者讀 diff |
| TC-032 | 範圍：不改 `platform/abf_station/` | 不在範圍 | 同 TC-030 | `git diff origin/v3...HEAD -- platform/abf_station` | 零差異 | 自動：驗收者讀 diff |
| TC-033 | 範圍：不改 `docs/`（沒有文件列出這些常數） | 不在範圍 | 同 TC-030 | `git diff origin/v3...HEAD -- docs` | 零差異 | 自動：驗收者讀 diff |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | 核心原則 IV「證據先於宣稱」：綠燈必須是真的，不能靠放寬測試換來 | 功能 | 比對 base 與 HEAD 所有 `platform/tests/` 下的檔案 | 檢查 diff 內有沒有新增 `skip`、`xfail`、放寬的比對、改過的預期值 | 全部 `platform/tests/` 的 diff 只有 TC-017 那一行刪除，沒有新增任何跳過、豁免或改過的預期值；快照的改動由 `REGEN_CMD` 產生（TC-009） | 自動：驗收者讀 diff |
| TC-035 | 憲法 5.0.0「同意（yes）只能由本人在自己的表單或確認頁給，AI 助理不能代答」 | 功能 | 改動完成 | 跑 `test_launch_profiles.py::test_tc055`、`test_tc017_tc056_tc057` 與 `test_chat_tools.py` 的禁字掃描 | 全綠：launch 的參數名沒有能讓 AI 代答的名字（confirm、approve、yes、send、force、skip、accept 等），launch 描述與各參數說明（含新加的 `pipeline` 說明）不含禁字 | 自動：`platform/tests/test_launch_profiles.py`、`platform/tests/test_chat_tools.py` |
