# 測試案例：憲法 6.0.0 收尾（constitution-6，第 2 版計畫）

<!--
Written by the verifier (CONTRACT mode). Source: specs/constitution-6/plan.md (no spec.md for this docs task; the plan's numbered parts are the requirements, cited here as 計畫§1 to 計畫§7). The maintainer's own words that apply: 「都沒問題，好」(2026-10-18, approval of the three rules). Language: 繁體中文; identifiers and paths stay as they are.
-->

**規格**：`specs/constitution-6/plan.md`（本任務沒有 spec.md，以計畫各節為需求）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、有人做了不該做的事時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

驗證方式說明：「自動」= 某個 `tests/*.sh` 會在不符時變紅。「手動」= 驗收者用 `git diff` 或讀檔核對（計畫「Out of scope」明定此項由驗收者手動核對；`docs/TESTING.md` 不在本次範圍，不新增步驟）。

## 一、docs/ROADMAP.md「Principles waiting for a check」表（計畫§1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫§1 刪第 1 列 | 功能 | 路線圖的「等待檢查的原則」表 | 在該表找開頭為「The platform's run index is never a second truth」的列 | 找不到這一列（它已成為憲法 I.2） | 自動：`tests/platform_direction_docs_test.sh`（TC-023「run index」改為 nin）；`tests/constitution_6_test.sh`（d） |
| TC-002 | 計畫§1 刪第 2 列 | 功能 | 同上 | 在該表找「Gates live in the platform's action layer」 | 找不到這一列（5.0.0 已把它放在 I.2） | 自動：`tests/platform_direction_docs_test.sh`（TC-023「gates」改為 nin）；`tests/constitution_6_test.sh`（d） |
| TC-003 | 計畫§1 憑證列，原則文字一字不改 | 功能 | 同上 | 找憑證那一列 | 原則欄仍是逐字的「The platform stores metadata only and never holds a site credential; credentials stay on the user's station agent」 | 自動：`tests/platform_direction_docs_test.sh`（第 224、272 行附近既有斷言，不得改動且須通過） |
| TC-004 | 計畫§1 憑證列，檢查欄附註 | 功能 | 同上 | 讀憑證列的「檢查」欄 | 欄位尾端有逐字附註：「*Note (6.0.0): the half 'a credential inside received data is never stored' joined the Safety Net; the API refusing a credential field still has no check.*」 | 自動：`tests/constitution_6_test.sh`（d） |
| TC-005 | 計畫§1 寫入工具列，原則文字一字不改 | 功能 | 同上 | 找寫入工具那一列 | 原則欄仍是逐字的「Every platform write tool (launch, delete, clear `work/`) refuses without the user's confirmation step」 | 自動：`tests/platform_direction_docs_test.sh`（第 273 行附近既有斷言，不得改動且須通過） |
| TC-006 | 計畫§1 寫入工具列，附註 | 功能 | 同上 | 讀寫入工具列的附註 | 原有附註之後多了逐字一句：「*6.0.0 moved launch, cancel, resume, relaunch and forget into the Safety Net; delete and clear `work/` join when they exist with their refusal tests.*」 | 自動：`tests/constitution_6_test.sh`（d） |
| TC-007 | 計畫§1「15 table lines instead of 17」 | 功能 | 刪列之後 | 數該表以 `|` 開頭的行（含表頭與分隔線） | 恰好 15 行（17 減 2） | 自動：`tests/platform_direction_docs_test.sh`（TC-025 與 W0 TC-026） |
| TC-008 | 計畫§1「No other row changes」 | 功能 | 同上 | 檢查其餘列：角色（PI 與 member）、host 只經自帶閘門的工具、owed parity、model-neutral、不得共用帳號、資料留在本地、花錢需確認等 | 這些列都還在，文字與 `origin/v3` 相同；只有 TC-001/002 刪掉的兩列、TC-004/006 加的兩段附註不同 | 自動：`tests/platform_direction_docs_test.sh`（既有 TC-023、W0 TC-023、TC-024、TC-025、TC-027 model-neutral）；驗收者另以 `git diff origin/v3...HEAD -- docs/ROADMAP.md` 核對 |
| TC-009 | 計畫§1 刪列的理由：兩條原則已在憲法 | 功能 | 兩列已刪 | 讀憲法原則 I.2 | I.2 含「The platform's run index is never a second truth」與「refused through the MCP tool and through the web route」（刪掉的不是丟掉，而是搬進憲法） | 自動：`tests/platform_direction_docs_test.sh`（TC-023、TC-006 的反向斷言，見 TC-028、TC-032、TC-034） |

## 二、docs/PRINCIPLES.md（計畫§2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 計畫§2 更正舊句 | 功能 | 原文第 44–46 行附近說「that rule waits for its check in `docs/ROADMAP.md`」 | 讀「Nextflow's own records are the truth about a run」那一段 | 「that rule waits for its check」這句已不存在 | 自動：`tests/constitution_6_test.sh`（e） |
| TC-011 | 計畫§2 更正後內容 | 功能 | 同上 | 讀同一段 | 說明該規則已在憲法 6.0.0 加入（I.2），由 `test_nextflow_e2e.py` 的 `test_tc030` 與 `test_tc031` 把關 | 自動：`tests/constitution_6_test.sh`（e） |
| TC-012 | 計畫§2 加 6.0.0 條目（加入的三條規則） | 功能 | PRINCIPLES.md 已有 5.0.0 的段落（「Who may say yes (constitution 5.0.0…)」）作為格式範本 | 找 6.0.0 條目 | 有條目引用「constitution 6.0.0」，並列出加入的三條：執行索引可由 Nextflow 紀錄重建且以紀錄為準（I.2）、安全網寫入工具規則（launch、cancel、resume、relaunch、forget）、安全網憑證規則（收到的資料裡的憑證不存） | 自動：`tests/constitution_6_test.sh`（e） |
| TC-013 | 計畫§2（哪些測試把關） | 功能 | 同上 | 讀 6.0.0 條目 | 條目指出各規則由哪些測試把關（至少含 `test_tc030`／`test_tc031`、`test_actions_layer.py`、`test_secrets.py` 的名稱） | 自動：`tests/constitution_6_test.sh`（e） |
| TC-014 | 計畫§2（沒加入的與原因，照抄修正案「Not moved」） | 功能 | 同上 | 讀 6.0.0 條目 | 列出沒加入的四件事及原因：「每個入口到同一個動作」與「網頁與工具一對一」等 parity test（011a）；「呼叫平台自己的工具算 session 在用」等 scope test；「外掛的 hooks 變成 action layer 的呼叫者」尚未成真（`hooks/confirm_launch.sh` 仍獨立）；API 拒收憑證欄位沒有檢查 | 自動：`tests/constitution_6_test.sh`（e，檢查含 `011a`、`scope test`、`confirm_launch.sh`） |
| TC-015 | 計畫§2（只更正那一句）；計畫§1（host 列留在路線圖） | 例外 | 路線圖仍留著「host 只經自帶閘門的工具」那列 | 讀 PRINCIPLES.md 第 88 行附近關於該規則的句子 | 該句仍說它「waits in `docs/ROADMAP.md`」（此規則沒搬，不得被誤改）；PRINCIPLES.md 也沒有「always on／every session」之類與安全網範圍矛盾的字句 | 自動：`tests/constitution_scope_test.sh`（逐檔 hasnt 檢查）；驗收者以 `git diff` 核對 |

## 三、README.md 與 CLAUDE.md（計畫§3）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 計畫§3 README | 功能 | README 第 56、58 行附近原寫「constitution 5.0.0」 | 搜尋 README 的版本引用 | 兩處都寫「constitution 6.0.0」，沒有任何「constitution 5.0.0」殘留 | 自動：`tests/platform_direction_docs_test.sh`（TC-059：「Nextflow's own records, the truth under constitution 6.0.0」） |
| TC-017 | 計畫§3 CLAUDE.md | 功能 | CLAUDE.md 第 11 行附近原寫「5.0.0, principle 2」 | 搜尋 CLAUDE.md 的版本引用 | 寫「constitution 6.0.0」，沒有「constitution 5.0.0」殘留 | 自動：`tests/platform_direction_docs_test.sh`（TC-059：CLAUDE.md points at constitution 6.0.0） |
| TC-018 | 計畫§3「No other wording change」；Out of scope 的手動核對 | 不在範圍 | 兩檔都已改完 | 跑 `git diff origin/v3...HEAD -- README.md CLAUDE.md` | 差異只有版本號引用（5.0.0 變 6.0.0），沒有別的字被動 | 手動：驗收者以 git diff 核對（計畫指定） |

## 四、tests/constitution_scope_test.sh（計畫§4）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 計畫§4 第 29 行 | 功能 | 憲法末行為 `**Version**: 6.0.0` | 執行 `bash tests/constitution_scope_test.sh` | 版本檢查比對 `**Version**: 6.0.0`，說明文字列出「2.0.0 之後依序有 …5.0.0 與 6.0.0」，且通過 | 自動：`tests/constitution_scope_test.sh` |
| TC-020 | 計畫§4 第 31 行 | 功能 | 同上 | 同上 | 比對 `**Last Amended**: 2026-10-18`（舊值 2026-10-17 不再被接受），且通過 | 自動：`tests/constitution_scope_test.sh` |
| TC-021 | 計畫§4 第 127 行指紋 | 功能 | 安全網現有最終文字（6.0.0 新增兩條規則） | 以測試自己的方法（取出「## Safety Net」段，`printf '%s\n'`、去掉 `\r`、SHA-256）算指紋，與檔內 `PINNED_SN_SHA256` 比對 | 檔內釘住的值等於新算出的值，驗證者獨立算得 `bb125d3a27489ca5aa08951bf58d0ba547be88c259a006bb1e32907c6c399bd1`；「Safety Net section matches the pinned fingerprint」一列為 ok | 自動：`tests/constitution_scope_test.sh` |
| TC-022 | 計畫§4「issue #71 scratch cases TC-002/TC-007 must pass again」 | 功能 | 指紋已更新 | 執行該測試的 issue #71 區段 | 「TC-002: unchanged, no main: the fingerprint line runs and is ok」與「TC-007: a change outside the Safety Net keeps the fingerprint ok」都通過 | 自動：`tests/constitution_scope_test.sh` |
| TC-023 | 計畫§4（指紋仍能抓到安全網被改） | 例外 | 在 scratch clone 的安全網段多加一句 | 執行該測試 | 「TC-003: Safety Net changed, no main: fails on the fingerprint」與「TC-008」等既有 scratch 案例仍通過（指紋檢查沒有被放鬆） | 自動：`tests/constitution_scope_test.sh` |
| TC-024 | 計畫§4「Write the old and new fingerprint in the ledger」 | 功能 | 指紋已更新 | 讀 `specs/constitution-6/ledger.md` | 記有舊指紋 `fd9129685c1c52a2790926ed8f6d92e186c9ff036bb8d24155837bcbe51de0ae` 與新指紋（等於 TC-021 的值） | 手動：驗收者讀 ledger.md |
| TC-025 | 計畫§4（只列出的三處改動） | 不在範圍 | 比對 `origin/v3` 的該測試檔 | `git diff origin/v3...HEAD -- tests/constitution_scope_test.sh` | 差異只有版本字串／清單、Last Amended 日期、`PINNED_SN_SHA256` 三處；沒有刪除、放寬或跳過任何其他斷言 | 手動：驗收者以 git diff 核對 |

## 五、tests/platform_direction_docs_test.sh（計畫§5）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | 計畫§5 TC-001（第 52–54 行） | 功能 | 憲法末行 | 執行該測試 | 比對整行 `**Version**: 6.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-10-18`，標籤也改為 6.0.0 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-027 | 計畫§5 TC-059（第 382、385 行） | 功能 | CLAUDE.md、README 已改 | 執行該測試 | 兩條斷言都改成引用 constitution 6.0.0 並通過（見 TC-016、TC-017） | 自動：`tests/platform_direction_docs_test.sh` |
| TC-028 | 計畫§5 TC-006 反向（第 82 行）之一 | 功能 | 原斷言：整份憲法不含「run index」 | 執行該測試 | 改為：原則 I.2（`$P1`）含「The platform's run index is never a second truth」，並通過 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-029 | 計畫§5 TC-006 反向之二 | 功能 | 同上 | 同上 | 原則 I.2（`$P1`）含 `test_tc030_rebuild_gives_back_every_field`，並通過 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-030 | 計畫§5 TC-006 反向之三 | 功能 | 同上 | 同上 | 「## Safety Net」段落內任何地方都沒有「run index」（用安全網段而非整份憲法，因為 I.2 與 6.0.0 修正案本來就含這個詞），並通過 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-031 | 計畫§5 TC-023 run index 列（第 271 行）反向 | 功能 | 原斷言：路線圖表含該列 | 執行該測試 | 改為對路線圖表 `$WL` 做 `nin`（不含「The platform's run index is never a second truth」），並通過 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-032 | 計畫§5 TC-023 run index 規則文字 | 功能 | 同上 | 同上 | 另有對 `$P1` 的 `inn`，確認規則文字在憲法原則 I.2，並通過 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-033 | 計畫§5 TC-023 gates 列（第 275 行）反向 | 功能 | 原斷言：表含「Gates live in the platform's action layer…」整列 | 執行該測試 | 改為對 `$WL` 做 `nin`（不含「Gates live in the platform's action layer」），並通過 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-034 | 計畫§5 TC-023 gates 檢查欄（第 276 行）反向 | 功能 | 原斷言：表含「…refused through the MCP tool and through the web route」 | 同上 | 改為：路線圖表不含該句，且 `$P1`（原則 I.2）含「refused through the MCP tool and through the web route」，並通過 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-035 | 計畫§5 W0 TC-027（第 583 行）反向 | 功能 | 原斷言：「other rows untouched (run index)」表含該列 | 同上 | 改為對 `$WL` 做 `nin`（該列已搬進憲法），標籤也相應更新，並通過 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-036 | 計畫§5 TC-025（第 290 行）與 W0 TC-026（第 582 行） | 功能 | 原斷言：17 行 | 同上 | 兩處都改為 15 行，標籤文字一併改（不再寫 17），並通過 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-037 | 計畫§5 第 224、272、273 行保持不變 | 功能 | 憑證列與寫入工具列保留原則文字 | 同上 | 這三處斷言文字與 `origin/v3` 一字不差，且仍通過 | 自動：`tests/platform_direction_docs_test.sh`；驗收者以 git diff 確認這三行沒被動 |
| TC-038 | 計畫§5 開頭「a deleted assertion is always replaced by its inverse」 | 不在範圍 | 比對 `origin/v3` 的該測試檔 | `git diff origin/v3...HEAD -- tests/platform_direction_docs_test.sh` | 每一條被移除的斷言都有對應的反向斷言；除計畫§5 逐條列名的改動外，沒有其他斷言被刪除、放寬、跳過或改期望值 | 手動：驗收者以 git diff 核對 |

## 六、新檔 tests/constitution_6_test.sh（計畫§6）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-039 | 計畫§6(a) 規則一：執行索引（I.2） | 功能 | 憲法 I.2 的新規則 | 執行 `bash tests/constitution_6_test.sh` | 規則文字點名 `test_nextflow_e2e.py`，且 `platform/tests/test_nextflow_e2e.py` 存在；缺任一者測試變紅 | 自動：`tests/constitution_6_test.sh` |
| TC-040 | 計畫§6(a) 規則二：每個寫入工具 | 功能 | 安全網寫入工具規則 | 同上 | 規則點名 `test_actions_layer.py`、`test_human_channel.py`、`test_resume_entrypoints.py`、`test_keep_submissions.py`，四個檔案都存在於 `platform/tests/` | 自動：`tests/constitution_6_test.sh` |
| TC-041 | 計畫§6(a) 規則三：收到的憑證不存 | 功能 | 安全網憑證規則 | 同上 | 規則點名 `test_secrets.py`、`test_nextflow_e2e.py`、`test_human_channel.py`，三個檔案都存在 | 自動：`tests/constitution_6_test.sh` |
| TC-042 | 計畫§6(b) 規則一的測試名稱 | 功能 | 規則一點名的測試 | 同上 | `test_tc030_rebuild_gives_back_every_field` 與 `test_tc031_nextflows_records_win_over_a_damaged_index` 在 `test_nextflow_e2e.py` 中各有 `def` 定義；少一個測試變紅 | 自動：`tests/constitution_6_test.sh` |
| TC-043 | 計畫§6(b) 規則二的測試名稱 | 功能 | 規則二點名的測試 | 同上 | `test_tcb04_`、`test_tcb08_`（`test_actions_layer.py`）；`test_tch09_`、`test_tca14_`（`test_human_channel.py`）；`test_tc142_`、`test_tc144_`（`test_resume_entrypoints.py`）；`test_tc034_`、`test_tc037_`、`test_tc038_`（`test_keep_submissions.py`）各至少有一個 `def <前綴>` | 自動：`tests/constitution_6_test.sh` |
| TC-044 | 計畫§6(b) 規則三的測試名稱 | 功能 | 規則三點名的測試 | 同上 | `test_tc040_`、`test_tc042_`、`test_tc_i03_`（`test_secrets.py`）；`test_tc041_`（`test_nextflow_e2e.py`）；`test_tcf10_f11_`（`test_human_channel.py`）各至少有一個 `def <前綴>` | 自動：`tests/constitution_6_test.sh` |
| TC-045 | 計畫§6(c) 寫入工具名單相符 | 功能 | `platform/abf_platform/mcp_server.py` 註冊的工具中，標註 `_WRITES` 或 `_STOPS` 的有 launch、cancel、forget、resume、relaunch | 執行該測試 | 安全網寫入工具規則列出的工具，與程式註冊的完全相同（恰好這五個，不多不少） | 自動：`tests/constitution_6_test.sh` |
| TC-046 | 計畫§6(c)「a new write tool without a constitution entry fails」 | 例外 | 在 `mcp_server.py` 的副本新增一個標註 `_WRITES` 或 `_STOPS` 的工具，憲法沒有它 | 以副本執行該測試的比對邏輯 | 測試變紅，並指出多出來的工具名 | 自動：`tests/constitution_6_test.sh`（須能對副本演示變紅） |
| TC-047 | 計畫§6(d) 兩列已刪 | 功能 | 路線圖 | 執行該測試 | 路線圖既沒有「The platform's run index is never a second truth」列，也沒有「Gates live in the platform's action layer」列 | 自動：`tests/constitution_6_test.sh` |
| TC-048 | 計畫§6(d) 兩列保留且有 6.0.0 附註 | 功能 | 路線圖 | 同上 | 憑證列與寫入工具列仍在，且各帶 TC-004、TC-006 的 6.0.0 附註 | 自動：`tests/constitution_6_test.sh` |
| TC-049 | 計畫§6(e) PRINCIPLES 有 6.0.0 條目 | 功能 | PRINCIPLES.md | 同上 | 有 6.0.0 條目（引用「constitution 6.0.0」，見 TC-012） | 自動：`tests/constitution_6_test.sh` |
| TC-050 | 計畫§6(e) 不再說規則在等 | 功能 | PRINCIPLES.md | 同上 | 「that rule waits for its check」不存在（見 TC-010） | 自動：`tests/constitution_6_test.sh` |

## 七、整體與範圍（計畫§7 與 Out of scope）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-051 | 計畫§7 `constitution_checks_exist_test.sh` | 功能 | 全部改動完成 | 執行 `bash tests/constitution_checks_exist_test.sh` | 通過（新規則的 `*Check:*` 都點名了存在的檔案） | 自動：`tests/constitution_checks_exist_test.sh` |
| TC-052 | 計畫§7 全套綠燈 | 功能 | 全部改動完成，在 WSL 執行 | `bash tests/run_all.sh` | 全部測試檔通過，包含新增的 `constitution_6_test.sh`（由 run_all 依檔名自動收進） | 自動：`tests/run_all.sh`（WSL）或 CI 結果 |
| TC-053 | 計畫開頭「DO NOT edit the constitution」；Out of scope | 不在範圍 | 憲法在提交 704e514 時是最終文字 | `git diff 704e514 HEAD -- .specify/memory/constitution.md` | 沒有任何差異（憲法在本任務中未被改動） | 手動：驗收者以 git diff 核對 |
| TC-054 | 計畫 Out of scope | 不在範圍 | 比對 `origin/v3` | `git diff origin/v3...HEAD --stat`（扣除憲法已定稿的 85c2fbd、704e514） | 被改的檔案只有 ROADMAP.md、PRINCIPLES.md、README.md、CLAUDE.md、兩個既有測試、新測試、`specs/constitution-6/*`；CHANGELOG.md、platform 程式碼、hooks、`docs/TESTING.md`、其他文件都沒被動 | 手動：驗收者以 git diff 核對 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-055 | Governance：MAJOR 修正案的 Sync Impact Report 所列文件須一併更新 | 功能 | 憲法 6.0.0 修正案列出：`docs/ROADMAP.md`、`docs/PRINCIPLES.md`、`README.md`、`CLAUDE.md`、`tests/constitution_scope_test.sh`、`tests/platform_direction_docs_test.sh` | 逐一確認這六個檔案都有對應改動 | 六個檔案都已更新（TC-001 至 TC-038 分別驗證內容） | 手動：驗收者以 git diff 核對 |
| TC-056 | 安全網既有規則（刪除來源資料、work/ 清理需確認、launch 需確認、憑證留在設定區、範圍定義等）不因新增兩條而被改寫 | 功能 | 安全網新增兩條規則 | 執行 `bash tests/constitution_scope_test.sh` | TC-040 至 TC-044 的 `sn_has` 固定字串檢查全部仍通過（舊規則字句還在），且整段指紋與新釘住值相符 | 自動：`tests/constitution_scope_test.sh` |
