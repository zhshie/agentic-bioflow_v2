# 測試案例：憲法 6.2.0 合併規則對齊現況；PRODUCT／DESIGN 補原話（charter-v4-workflow）

**規格**：`specs/charter-v4-workflow/plan.md`（本任務是純文件，計畫即規格；沒有 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。這裡指「沒有維護者的 yes 就不能合併」這類關卡。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

說明：
- 「自動」的案例都放在新檔 `tests/charter_v4_workflow_test.sh`（用 `has`／`lacks`），除非驗證方式欄另外寫了檔名。
- 「手動」的案例**不在 `docs/TESTING.md`**。依憲法，TESTING.md 手動半部只在 `commands/`、`skills/`、`hooks/` 有變更的發行前才跑，本任務都不碰（計畫裁決 3）。這類案例的證據由 executor 貼在 `specs/charter-v4-workflow/ledger.md`，閱卷者逐項對照。
- 憲法文字由 developer-agent 預先 commit 在 `charter-v4-workflow` 的 base（`charter-v4-base`）；executor 不得改憲法。所以憲法內容的自動案例在 base 就該是綠的（作為回歸保護），其中 TC-007、TC-020 要等 developer-agent 依裁決 2 補回「modified or removed requirement」之後才會綠。
- 「Not 行」指 PRODUCT.md 中以 `**Not**:` 開頭的那一行；「子句」指它以分號切開的每一段。

## US1 — 憲法 6.2.0 條目與 Development Workflow 最後一條（優先度 P1）

維護者原話：2026-10-24「以後你都自己合併」；2026-11-03「合併規則同意」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 3 | 功能 | 憲法檔 | 用 `awk '/^### 6\.2\.0 \(2026-11-03\)/{f=1} /^## Governance/{f=0} f'` 抽出 6.2.0 條目 | 抽出的內容非空；標題行以 `### 6.2.0 (2026-11-03): ` 開頭（英文）；它出現在 6.1.0 條目之後、`## Governance` 之前 | 自動 |
| TC-002 | 作法 3 | 功能 | 同上 | 看條目內六個粗體標籤的出現順序 | 依序是 `**Rationale.**`、`**What changes.**`、`**Sync Impact Report.**`、`**Impact on existing deployments.**`、`**Version.**`、`**Approval.**`，各一次，順序不亂 | 自動 |
| TC-003 | 原話 2026-10-24；作法 3 Rationale | 功能 | 同上 | 在條目中找維護者的話 | 逐字含 `「以後你都自己合併」` | 自動 |
| TC-004 | 原話 2026-11-03；作法 3 Rationale | 功能 | 同上 | 在條目中找維護者的話 | 逐字含 `「合併規則同意」` | 自動 |
| TC-005 | 作法 3 Rationale | 功能 | 同上 | 讀 Rationale | 同時提到 `2.1.0`、`2026-10-24`、以及開發分支改到 `v3` 而舊字句仍寫 `main`，說明舊字面與現況不符 | 自動 |
| TC-006 | 作法 3 What changes（誰合併） | 功能 | 同上 | 讀 What changes | 寫明開發主責（`development lead`）在 CI 綠、獨立驗收通過後合併每一個 PR；用的詞是既有的 `development lead`，沒有新創詞 | 自動 |
| TC-007 | 裁決 2；作法 3 What changes | 功能 | 同上 | 讀 What changes | 寫明「需求的修改或刪除」（`modified or removed requirement`）仍須維護者先說好 | 自動 |
| TC-008 | 作法 3 What changes（仍須維護者好） | 功能 | 同上 | 讀 What changes | 寫明 `Amendments`、`releases`、`loosens the Safety Net` 三項仍須維護者用自己的話明確說 yes，之後才由開發主責合併 | 自動 |
| TC-009 | 裁決 2；原話 2026-10-24 | 功能 | 同上 | 讀 What changes | 寫明使用者可見的變更不再等 yes，而是合併後列給維護者（含 `listed for the maintainer`） | 自動 |
| TC-010 | 作法 3 What changes（基底） | 功能 | 同上 | 讀 What changes | 寫明開發基底是 `v3`、`main` 是 v2 線 | 自動 |
| TC-011 | 作法 2、3 What changes（風險分級） | 功能 | 同上 | 讀 What changes | 有一句 v4 風險分級，同句含五個保護路徑：`.github/`、`hooks`、`this constitution`、`plugin.json`、`platform/abf_station/`，並寫明合併前要有「還會影響什麼」的證明與第二次對抗審 | 自動 |
| TC-012 | 作法 3 What changes | 功能 | 同上 | 讀 What changes 結尾 | 明說沒有任何原則或 Safety Net 規則被刪或重新定義（含 `No principle or Safety Net rule is removed or redefined`） | 自動 |
| TC-013 | 作法 3 Sync Impact Report | 功能 | 同上 | 讀 Sync Impact Report | 列出 `PRODUCT.md`、`DESIGN.md`、`tests/constitution_scope_test.sh`、`tests/platform_direction_docs_test.sh` 與新測試 | 自動 |
| TC-014 | 作法 3 Impact；Version | 功能 | 同上 | 讀 Impact 與 Version | Impact 寫明沒有部署影響（`None`）；Version 行含 `**Version.** MINOR`，並說明沒有原則或 Safety Net 規則被刪或重新定義 | 自動 |
| TC-015 | 作法 3 Approval；原話 2026-11-03 | 功能 | 同上 | 讀 Approval | 含 `「合併規則同意」`、日期 `2026-11-03`，並寫明開發主責在 CI 綠且驗收通過後合併這個 PR | 自動 |
| TC-016 | 作法 1（基底）；原話 2026-11-03 | 功能 | 憲法 Development Workflow 最後一條（`One change at a time, on a branch.`） | 讀這一條 | 含 `v3`，並表明 `main` 帶的是 v2 線 | 自動 |
| TC-017 | 作法 1 | 功能 | 同上 | 搜尋舊句 | 不含舊句 `main receives merges only` | 自動 |
| TC-018 | 作法 1；原話 2026-10-24 | 功能 | 同上 | 讀這一條 | 寫明 CI（`.github/workflows/tests.yml`）須綠、獨立驗收須通過，之後由 `development lead` 合併這個 PR | 自動 |
| TC-019 | 作法 1（不得變成維護者不再管任何事） | 例外 | 同上 | 讀這一條：沒有維護者 yes 時 | 憲法修正（`Amendments`）、發行（`releases`）、放寬 Safety Net（`loosens the Safety Net`）三項，寫明須先取得維護者用自己的話說的 yes，之後才由開發主責合併 | 自動 |
| TC-020 | 裁決 2 | 例外 | 同上 | 讀這一條：需求被修改或刪除時 | 含 `modified or removed requirement`，且它與 TC-019 的三項一樣，須維護者先說好才合併 | 自動 |
| TC-021 | 作法 1（保留原分級） | 功能 | 同上 | 讀這一條 | 仍保留 `fixes`、`tests`、`docs`、`refactors`、`only make the Safety Net stricter` 這些分級字樣 | 自動 |
| TC-022 | 裁決 2；原話 2026-10-24 | 功能 | 同上 | 讀這一條 | 使用者可見變更（`what a user sees`）寫成合併後列給維護者，不在須先 yes 的名單裡 | 自動 |
| TC-023 | 作法 2 | 功能 | 同上 | 讀這一條 | 有一句風險分級，同句含五個保護路徑 `.github/`、`hooks`、`this constitution`、`plugin.json`、`platform/abf_station/`，並含「證明還會影響什麼」與第二次對抗審（`adversarial`）；合併「之前」要做 | 自動 |
| TC-024 | 作法 2（同一個 bullet，不新開條） | 功能 | 憲法 Development Workflow 小節 | 數 Workflow 小節內以 `- **` 開頭的條目，與 `origin/v3` 比 | 條數與 `origin/v3` 相同；風險分級那句在 `One change at a time` 這一條之內 | 自動 |

## US2 — Governance 與版本行（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 作法 4 | 功能 | 憲法 `## Governance` 段 | 搜尋舊句 | 不含 `Only the maintainer approves and merges it` | 自動 |
| TC-026 | 作法 4 | 功能 | 同上 | 讀修正案那一條 | 寫明維護者須先「明確、用自己的話」同意，之後由 `development lead` 合併這個 PR | 自動 |
| TC-027 | 作法 4（其餘不動的反向檢查） | 功能 | 同上 | 搜尋兩句沒被改的話 | 仍含 `supersedes all other practices` 與 `MUST NOT restate` | 自動 |
| TC-028 | 作法 5 | 功能 | 憲法檔 | 取最後一個非空行 | 完全等於 `**Version**: 6.2.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-11-03` | 自動 |
| TC-029 | 作法 4（其餘 Governance 字句不動） | 功能 | `origin/v3` 與目前分支 | `git diff origin/v3 -- .specify/memory/constitution.md`，只看 `## Governance` 段 | Governance 段只有「Only the maintainer approves …」那一條與版本行被改；`Versioning`、`Every plan's Constitution Check`、`supersedes` 三條逐字未動 | 手動：證據貼 ledger（不適用 TESTING.md） |

## US3 — PRODUCT.md（優先度 P1）

維護者原話：2026-10-23 網頁終端機（DESIGN.md 原話 19：「是中欄有個可以切換主視窗跟終端機的按鈕。終端機能否直接使用? 我要在AI幫我跑時同時看到終端機的輸入指令變化，但我同時也可以自己打。下游的中欄主視窗是R studio，但切換成終端機就是跑在我的電腦。」）；2026-10-30、2026-11-03 介面參考 Seqera／Galaxy。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 作法 6 Who | 功能 | `PRODUCT.md` | 讀 `**Who**` 行 | 含 `NCHC nano4` | 自動 |
| TC-031 | 作法 6 Who | 功能 | 同上 | 搜尋整份檔案 | 不含 `Taiwania3` | 自動 |
| TC-032 | 裁決 1(a)；作法 6 Not | 功能 | 同上 | 把 Not 行以分號切成子句 | 沒有任何「不含 `later`」的子句出現 `web terminal`；舊的獨立項 `a web terminal;` 已消失 | 自動 |
| TC-033 | 原話 2026-10-23；裁決 1(b)；作法 6 Not | 功能 | 同上 | 找 Not 行中含 `web terminal` 的子句 | 恰有一個這樣的子句，且同一子句含 `later`、`constitution amendment`，並與 `roles`、`Data Explorer`、`Dashboard` 在同一個 (later) 清單；沒有另開新段落或新行 | 自動 |
| TC-034 | 裁決 1(c)；計畫「不做」 | 不在範圍 | 同上 | 看含 `web terminal` 的子句 | 沒有「已核可」「approved」之類字樣；只說之後、待它自己的憲法修正案，沒宣告已核可 | 自動 |
| TC-035 | 作法 6 Not（其餘不動） | 功能 | 同上 | 讀 Not 行 | 仍含 `Seqera clone with many top-level pages`、`chatty AI text`、`roles`、`Data Explorer`、`Dashboard` | 自動 |
| TC-036 | 原話 2026-10-30、2026-11-03；作法 6 Principles | 功能 | 同上 | 讀 `**Principles**` 行 | 含 `Seqera Platform` 與 `Galaxy`，寫成介面設計沿用成熟平台的做法、不自創版面 | 自動 |
| TC-037 | 作法 6 Principles | 功能 | 同上 | 讀 `**Principles**` 行 | 同時含 `top-level pages`，表達維持較少的頂層頁面（fewer top-level pages 之意） | 自動 |
| TC-038 | 作法 6 Principles（原有原則不得被刪） | 功能 | 同上 | 讀 `**Principles**` 行 | 原有四項仍在：`ADR 0006`（每個寫入都經人確認）、`works without AI`、`ADR 0004`、`only their own runs` | 自動 |
| TC-039 | 作法 6（其餘不動） | 功能 | `origin/v3` 與目前分支 | `git diff origin/v3 -- PRODUCT.md` | 只有 Who、Not、Principles 三行有變動；`Job`、`Path` 等其他行逐字未動 | 手動：證據貼 ledger（不適用 TESTING.md） |

## US4 — DESIGN.md 補維護者原話 23–25（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 原話 2026-10-27；作法 7 | 功能 | `DESIGN.md` | `grep -F` 這一整列 | 存在一列：`23. 「一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」 (10-27)`，含全形引號 「」，標點一字不差 | 自動 |
| TC-041 | 原話 2026-10-30；作法 7 | 功能 | 同上 | `grep -F` 這一整列 | 存在一列：`24. 「介面還是不好，AWS, Azure介面就不能跟國網一樣，請你去參考Seqera platform的介面，不要都自己腦補」 (10-30)` | 自動 |
| TC-042 | 原話 2026-11-03；作法 7 | 功能 | 同上 | `grep -F` 這一整列 | 存在一列：`25. 「我的意思是介面設計多去參考Seqera, galaxy等」 (11-03)` | 自動 |
| TC-043 | 作法 7（位置與格式） | 功能 | 同上 | 看 23、24、25 三列的位置 | 緊接在 `22.` 之後、`## Skeleton` 之前，依序 23、24、25，格式與 18–22 一樣（編號、「原話」、括號日期） | 自動 |
| TC-044 | 作法 7（其餘一字不動）；原話 2026-10-23 | 功能 | 同上 | 比對 12–22 列 | 19 列逐字仍為維護者的終端機原話（`是中欄有個可以切換主視窗跟終端機的按鈕。…切換成終端機就是跑在我的電腦。`）；22 列逐字未變 | 自動 |
| TC-045 | 作法 7 | 功能 | `origin/v3` 與目前分支 | `git diff origin/v3 -- DESIGN.md` | 只有新增行（三列 + 必要的空行），沒有任何 `-` 行 | 手動：證據貼 ledger（不適用 TESTING.md） |
| TC-046 | 計畫範圍：「## 用字」段不動 | 功能 | `platform/tests/test_web_guided_launch_2b.py` | 跑 `test_h11_design_has_the_word_list` | 仍綠 | 自動：`platform/tests/test_web_guided_launch_2b.py` |
| TC-047 | 計畫範圍：upload 段落不動 | 功能 | `platform/tests/test_web_upload.py` | 跑 `test_tc101_design_md_upload_data_paragraph` | 仍綠 | 自動：`platform/tests/test_web_upload.py` |

## US5 — 測試檔與交付範圍（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-048 | 失敗先行測試 | 功能 | 目前分支 | 看 `tests/charter_v4_workflow_test.sh` 並執行 | 檔案存在；風格同 `dev_workflow_test.sh`（用 `has`／`lacks`）；執行全綠；TC-001 到 TC-044 的自動斷言在裡面都找得到 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-049 | 失敗先行測試 TC-E9 | 功能 | `tests/constitution_scope_test.sh` | 看 TC-E9 並執行此檔 | 有 TC-E9：抽出 6.2.0 條目、六標籤依序、含 `**Version.** MINOR`、含兩句原話；全檔綠 | 自動：`tests/constitution_scope_test.sh` |
| TC-050 | 作法 8 | 功能 | 同上 | 看 l.40 附近 | 斷言改為 `'**Version**: 6.2.0'`，描述字串含 `6.0.2, 6.1.0 and 6.2.0 came after` | 自動：`tests/constitution_scope_test.sh` |
| TC-051 | 作法 8 | 功能 | 同上 | 看 l.42 附近 | `Last Amended` 斷言為 `2026-11-03` | 自動：`tests/constitution_scope_test.sh` |
| TC-052 | 作法 8 | 功能 | 同上 | 看 TC-E5（約 l.292）的版本行 | 釘的版本行是 6.2.0 那一行（`Last Amended: 2026-11-03`） | 自動：`tests/constitution_scope_test.sh` |
| TC-053 | 作法 8 | 功能 | `tests/platform_direction_docs_test.sh` | 看 TC-001（約 l.52–54） | 釘的是 6.2.0 的完整版本行，描述字串也改成 6.2.0 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-054 | 作法 8；完成標準（不放寬、不刪斷言） | 功能 | 兩個既有測試檔，與 `origin/v3` 比 | `git diff origin/v3 -- tests/` 逐個既有檔檢查 | 既有斷言除兩處版本釘住（6.1.0→6.2.0、2026-10-25→2026-11-03）與一句描述字串外，沒有被刪、跳過或放寬；`dev_workflow_test.sh` 完全沒動 | 手動：證據貼 ledger（不適用 TESTING.md） |
| TC-055 | 失敗先行測試（既有測試） | 功能 | 目前分支 | 執行 `bash tests/constitution_scope_test.sh` | 全綠（含 TC-E4、E7、E8 不受新條目影響） | 自動：`tests/constitution_scope_test.sh` |
| TC-056 | 同上 | 功能 | 同上 | 執行 `bash tests/platform_direction_docs_test.sh` | 全綠 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-057 | 同上 | 功能 | 同上 | 執行 `bash tests/dev_workflow_test.sh` | 全綠（`Test cases before code`、`Independent acceptance` 兩句仍在） | 自動：`tests/dev_workflow_test.sh` |
| TC-058 | 同上 | 功能 | 同上 | 執行 `bash tests/constitution_6_test.sh` | 全綠 | 自動：`tests/constitution_6_test.sh` |
| TC-059 | 同上 | 功能 | 同上 | 執行 `bash tests/constitution_checks_exist_test.sh` | 全綠 | 自動：`tests/constitution_checks_exist_test.sh` |
| TC-060 | 裁決 4（先紅）| 功能 | ledger | 看 ledger 的改前輸出 | 貼有紅的輸出：版本行釘住（TC-E5、platform_direction TC-001 的 6.2.0 釘值）與 PRODUCT.md／DESIGN.md 斷言，在改文件前確實是紅，改後綠 | 手動：證據貼 ledger（不適用 TESTING.md） |
| TC-061 | 裁決 4 | 功能 | ledger | 看 ledger 說明 | 說明 TC-E9 與憲法內容斷言在 base 即綠，作為 hunk 的回歸保護（不假裝改前紅） | 手動：證據貼 ledger（不適用 TESTING.md） |
| TC-062 | 完成標準；範圍 | 功能 | 目前分支 | `git diff --stat origin/v3...HEAD` | 檔案只在範圍內：`.specify/memory/constitution.md`（僅 developer-agent 的 base commit）、`PRODUCT.md`、`DESIGN.md`、`tests/constitution_scope_test.sh`、`tests/platform_direction_docs_test.sh`、`tests/charter_v4_workflow_test.sh`，加 `specs/charter-v4-workflow/` 下的 ledger（`plan.md`、`test-case*.md` 不得被實作期間修改） | 手動：證據貼 ledger（不適用 TESTING.md） |
| TC-063 | 完成標準 risk L | 功能 | 閱卷報告與 ledger | 看爆炸半徑證明與對抗審 | 有逐 hunk 說明沒碰原則與 Safety Net 的證明（指令與輸出）；PASS 後有 Opus 對抗審紀錄 | 手動：證據貼 ledger（不適用 TESTING.md） |
| TC-064 | 完成標準（合併前）；裁決 2 | 功能 | PR | 看 PR 描述 | 引用維護者原話「合併規則同意」，並點出一件事：需求的修改或刪除仍等維護者 yes（這是收緊），讓維護者確認他同意的規則就是這一版 | 手動：PR 描述（合併前由 developer-agent 確認；不適用 TESTING.md） |

## 憲法與安全網

本任務修改憲法（保護路徑，risk L），下列案例證明沒有碰原則與 Safety Net。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-065 | Development Workflow；Amendments；Governance；版本行 | 功能 | `origin/v3` 與目前分支 | `git diff origin/v3 -- .specify/memory/constitution.md`，逐 hunk 對照計畫「作法」與裁決 2 | 只有 hunk A（Workflow 最後一條）、B（風險分級那句，在同一 bullet 內）、C（6.2.0 條目）、D（Governance 一句）與版本行；多一個 hunk 就是 FAIL；`-` 行只落在 A、D 與版本行 | 手動：證據貼 ledger（不適用 TESTING.md） |
| TC-066 | 原則 I–…；Safety Net；Invariants 與其 Check | 功能 | 同上 | 看憲法 diff 的位置 | 沒有任何 hunk 落在原則、Safety Net、Invariants 及其 Check 的行範圍內 | 手動：證據貼 ledger（不適用 TESTING.md） |
| TC-067 | Workflow：憲法在實作期間不得被 executor 改 | 功能 | `charter-v4-base` 與 HEAD | `git diff charter-v4-base...HEAD -- .specify/memory/constitution.md` | 空（executor 沒有碰憲法） | 手動：證據貼 ledger（不適用 TESTING.md） |
| TC-068 | Governance：其他文件不得重述得不一樣 | 功能 | 目前分支 | `git grep -n "receives merges only\|approves and merges it" -- . ':!specs'` | 沒有任何命中，即沒有其他檔還重述被改掉的兩句合併規則而沒同步 | 手動：證據貼 ledger（不適用 TESTING.md） |

## US6 — 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-069 | 計畫「不做」：不做 10-23 網頁終端機、自動續跑、OTP 憲法修正案 | 不在範圍 | 憲法檔 | 在 6.2.0 條目與整份憲法的新增行中找這三件事 | 6.2.0 條目不含 `OTP`；沒有為網頁終端機、自動續跑新增原則或條目（那是另案） | 自動 |
| TC-070 | 計畫「不做」：不改 `.github/`、`plugin.json`、`hooks/`；不准碰 `platform/`、`docs/PITFALLS.md`、dev-queue.json | 不在範圍 | 目前分支 | `git diff --stat origin/v3...HEAD` | 沒有任何檔落在 `.github/`、`.claude-plugin/plugin.json`、`hooks/`、`platform/`、`docs/PITFALLS.md`、`dev-queue.json` | 手動：證據貼 ledger（不適用 TESTING.md） |
| TC-071 | 計畫「不做」：不改 `CLAUDE.md`、`docs/PRINCIPLES.md`、`README.md`、`docs/ROADMAP.md`；不改 TESTING.md | 不在範圍 | 目前分支 | `git diff --stat origin/v3...HEAD` | 這幾個檔與 `docs/TESTING.md` 都沒有出現在變更清單 | 手動：證據貼 ledger（不適用 TESTING.md） |
| TC-072 | 計畫「不做」：不做開發模式啟動（dev-mode launch） | 不在範圍 | 目前分支 | `git diff --stat origin/v3...HEAD` | 變更清單沒有 `commands/`、`skills/`、`scripts/` 底下的檔，也沒有任何啟動開發模式的新程式或新文件 | 手動：證據貼 ledger（不適用 TESTING.md） |
