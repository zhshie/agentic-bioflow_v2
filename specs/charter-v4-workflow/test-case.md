# 測試案例：憲法 6.2.0（合併規則對齊現況）＋ PRODUCT.md／DESIGN.md 補原話

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
Source of truth: specs/charter-v4-workflow/plan.md including its two 「裁決（自動補）」 rounds (later rounds win).
There is no spec.md for this task; the plan's 「作法」 points 0-8, 「維護者原話」 and 「不做」 play the role of FR / out-of-scope.
-->

**規格**：`specs/charter-v4-workflow/plan.md`（本任務無 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，做到了。
- **例外**：出錯或做了不該做的事時系統怎麼反應。本任務只改文件與測試，沒有「執行時出錯」的情況，所以這一類為 0 條；「舊字句不得殘留」「不該動的沒動」放在「功能」或「不在範圍」。
- **不在範圍**：計畫「不做」或「其餘一字不動」的事；測試確認真的沒做。

驗證方式說明：

- 「自動」＝可由 `bash tests/<檔名>.sh` 判定（Git Bash 即可）；憲法條目與 Workflow 那一條跨行，比對前先把換行摺成單一空白（同 TC-E7 的做法）。Workflow 那一條＝從 `- **One change at a time, on a branch.**` 到下一個 `## ` 標題之間的文字。
- 「手動」＝本任務不碰 `commands/`、`skills/`、`hooks/`，所以**不適用** `docs/TESTING.md`（計畫裁決第二輪 2）；步驟寫在該列，證據貼在 `specs/charter-v4-workflow/ledger.md`，閱卷者自己重跑那條指令核對。
- 憲法文字由 developer-agent 預先 commit 在 base 分支 `charter-v4-base`，executor 不得改憲法。因此 TC-005 到 TC-027 在 base 就該是綠的，作為 hunk 的回歸保護；它們若是紅的，是 base 缺陷，退回 developer-agent。

## User Story 1 — 憲法 6.2.0 條文與版本（優先度 P1）

維護者原話：2026-10-24「以後你都自己合併」；2026-11-03「合併規則同意」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 5；失敗先行「版本行」 | 功能 | 憲法已更新 | 取憲法最後一個非空行 | 完全等於 `**Version**: 6.2.0 \| **Ratified**: 2026-09-28 \| **Last Amended**: 2026-11-03`（即 `constitution_scope_test.sh` 的 TC-E5 改釘後） | 自動：`tests/constitution_scope_test.sh`（TC-E5） |
| TC-002 | 作法 5、8 | 功能 | 同上 | 取憲法最後一個非空行，與 `platform_direction_docs_test.sh` 的 TC-001 比對 | 該測試釘的是同一條 6.2.0 版本行；測試名稱／描述也不再說「6.1.0 version line」 | 自動：`tests/platform_direction_docs_test.sh`（TC-001） |
| TC-003 | 作法 8 | 功能 | 同上 | 看 `constitution_scope_test.sh` 的 TC-021 版本斷言 | 斷言字串為 `**Version**: 6.2.0`；描述字串依序寫出 "…6.0.2, 6.1.0 and 6.2.0 came after" | 自動：`tests/constitution_scope_test.sh`（TC-021） |
| TC-004 | 作法 5、8 | 功能 | 同上 | 查憲法的 Last Amended 與 Ratified | 含 `**Last Amended**: 2026-11-03`、`**Ratified**: 2026-09-28`；TC-021 的 Last Amended 斷言改為 2026-11-03 | 自動：`tests/constitution_scope_test.sh`（TC-021） |
| TC-005 | 作法 1（保留原分級） | 功能 | Workflow 最後一條 | 查該條文字 | 仍含 "fixes, tests, docs, refactors" 與 "only make the Safety Net stricter" 的分級意思；不得變成「維護者不再管任何事」 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-006 | 作法 1；原話「合併規則同意」 | 功能 | Workflow 最後一條 | 以不分大小寫（grep -i）查 | 同時含 "amendments"、"releases"、"loosens the Safety Net"，且這三項被寫成須先取得維護者 "explicit yes"、"in his own words"（裁決第二輪 4：句首大寫也算） | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-007 | 作法 1；原話「以後你都自己合併」 | 功能 | Workflow 最後一條 | 查該條文字 | 含 "development lead merges"（通過 CI 與獨立驗收之後由開發主責合併每一個 PR），並含 `.github/workflows/tests.yml`、"CI"、"MUST be green"、"independent acceptance" 的意思 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-008 | 裁決第二輪 3；裁決第一輪 2 | 功能 | Workflow 最後一條 | 查該條文字 | 含 "modified or removed"，且「需求被修改或刪除」與修正案、發行、放寬 Safety Net 並列為須維護者先說好才合併 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-009 | 作法 1 | 功能 | Workflow 最後一條 | 查該條文字 | 含 `v3`，並含 `main` 是 v2 線的意思（現行寫法 "`main` carries the v2 line"） | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-010 | 作法 1 | 功能 | 憲法全文 | 查舊句 | 不含 "`main` receives merges only" | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-011 | 作法 2（hunk B） | 功能 | Workflow 最後一條 | 查風險分級那一句 | **同一句**同時含五個保護路徑：`.github/`、hooks、constitution、`plugin.json`、`platform/abf_station/`；並含「爆炸半徑證明」（proof of what else it can affect）與「第二次對抗審」（adversarial review）的意思；寫在同一個 bullet 內，沒有另開條 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-012 | 作法 4（hunk D） | 功能 | Governance 段（`## Governance` 到版本行之間） | 查舊句 | 不含 "Only the maintainer approves and merges it" | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-013 | 作法 4；失敗先行「其餘不動」 | 功能 | 同上 | 查 Governance 其餘字句 | 仍含 "supersedes all other practices" 與 "MUST NOT restate" | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-014 | 作法 4 | 功能 | 同上 | 查修正案的核可句 | 寫明維護者須先用自己的話明確同意（explicitly、in his own words），之後由 development lead 合併 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-015 | 作法 3（hunk C） | 功能 | 憲法 | 以 `awk '/^### 6\.2\.0 \(2026-11-03\)/{f=1} /^## Governance/{f=0} f'` 抽條目 | 條目存在且非空；標題為 `### 6.2.0 (2026-11-03): …`（英文）；位置在 `### 6.1.0` 條目之後、`## Governance` 之前 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-016 | 作法 3 | 功能 | 同上 | 在條目內找六個標籤 | `**Rationale.**`、`**What changes.**`、`**Sync Impact Report.**`、`**Impact on existing deployments.**`、`**Version.**`、`**Approval.**` 全部出現，且依此順序 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-017 | 原話 2026-10-24；作法 3 Rationale | 功能 | 6.2.0 條目的 Rationale | 逐字比對 | 含 `「以後你都自己合併」`（逐字，含全形引號） | 自動：`tests/constitution_scope_test.sh`（TC-E9） |
| TC-018 | 原話 2026-11-03；作法 3 Rationale | 功能 | 同上 | 逐字比對 | 含 `「合併規則同意」`（逐字，含全形引號） | 自動：`tests/constitution_scope_test.sh`（TC-E9） |
| TC-019 | 作法 3 Rationale | 功能 | 同上 | 查 Rationale | 寫明 2.1.0 起的字面（使用者可見變更等維護者的 yes、只有維護者合併修正案）與 10-24 以來的做法不符（含 "2.1.0"） | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-020 | 作法 3 What changes | 功能 | 6.2.0 條目的 What changes | 查四點 | 依序涵蓋：誰合併（development lead）；修正案、發行、放寬 Safety Net 仍須維護者先說好；基底是 `v3`（`main` 是 v2 線）；保護路徑的爆炸半徑證明＋對抗審 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-021 | 作法 3 What changes | 功能 | 同上 | 查結語 | 明說沒有任何原則或 Safety Net 規則被刪或重新定義（"No principle or Safety Net rule is removed or redefined"） | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-022 | 裁決第一輪 2；第二輪 3 | 功能 | 同上 | 查使用者可見變更與需求變更的說法 | 寫明：使用者可見變更不再等維護者的 yes（合併後列給維護者）；需求的修改或刪除（"modified or removed"）仍等維護者的 yes | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-023 | 作法 3 Sync Impact Report | 功能 | 6.2.0 條目的 Sync Impact Report | 查被列出的檔 | 列出 `PRODUCT.md`、`DESIGN.md`（原話 23 to 25）、兩個釘版本的測試（`tests/constitution_scope_test.sh`、`tests/platform_direction_docs_test.sh`）與新測試 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-024 | 作法 3 Impact | 功能 | 6.2.0 條目的 Impact on existing deployments | 查內容 | 寫明無部署影響（None），只改流程字句 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-025 | 作法 3 Version | 功能 | 6.2.0 條目的 Version | 查內容（換行摺成空白後） | 含 `**Version.** MINOR, under Governance: a rule is materially expanded (who merges, and the protected-path review); no principle or Safety Net rule is removed or redefined.` | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-026 | 作法 3 Approval；原話「合併規則同意」 | 功能 | 6.2.0 條目的 Approval | 查內容（換行摺成空白後） | 含 `The maintainer approved this change in his own words on 2026-11-03 (「合併規則同意」); the development lead merges the pull request after CI is green and the acceptance passes.` | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-027 | 失敗先行 TC-E9 | 功能 | `constitution_scope_test.sh` | 跑該檔 | 新增的 TC-E9 存在並通過：條目存在、六標籤依序、含 `**Version.** MINOR`、含兩句原話逐字；既有 TC-E4、TC-E7、TC-E8 的 awk 仍只抽到 `## Governance` 為止，仍通過 | 自動：`tests/constitution_scope_test.sh`（TC-E9） |

## User Story 2 — PRODUCT.md 對齊現況（優先度 P1）

維護者原話：2026-10-23 網頁終端機（完整句見 DESIGN.md 原話 19）；2026-10-30「…請你去參考Seqera platform的介面，不要都自己腦補」；2026-11-03「我的意思是介面設計多去參考Seqera, galaxy等」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 作法 6 Not；裁決第二輪 1(a) | 功能 | PRODUCT.md 的 **Not** 行 | 檢查 **Not** 行「(later) 清單之前」的部分 | 不含舊項 "a web terminal;"，也不含 "web terminal;"；其餘項目仍在：Seqera clone with many top-level pages、chatty AI text、roles、Data Explorer、Dashboard | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-031 | 作法 6 later；原話 2026-10-23（網頁終端機）；裁決第二輪 1(b)、5 | 功能 | 同上 | 找 **Not** 行中出現 "web terminal" 的子句 | 該子句與 roles、Data Explorer、Dashboard 同在 "(later)" 清單，並同時含 "later" 與 "constitution amendment" 的意思（網頁終端機排在之後，待它自己的憲法修正案）；不檢查日期；沒有另開 Later 段或新行 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-032 | 不做「不宣告已核可」；裁決第二輪 1(c) | 不在範圍 | 同上 | 在 **Not** 行查核可類字樣 | 不含「已核可」、「核可」、"approved" 類字樣（網頁終端機沒有被宣告為已核可） | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-033 | 作法 6 Who；環境事實 | 功能 | PRODUCT.md 全文 | 搜尋 "Taiwania3" | 全檔零命中 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-034 | 作法 6 Who | 功能 | **Who** 行 | 查內容 | 含 `NCHC nano4`；**Who** 行其餘（16S first、capped cloud account、Not bioinformaticians、English layout required 等）不變；句尾沒有新增括號出處 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-035 | 作法 6 Principles；原話 2026-10-30、2026-11-03 | 功能 | **Principles** 行 | 查內容 | 新增一條：含 "Seqera Platform" 與 "Galaxy"（介面設計沿用成熟平台做法、不自創版面），並含 "fewer top-level pages" 的意思 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-036 | 作法 6 Principles | 功能 | 同上 | 查原有四條 | 仍含 ADR 0006 的人工確認、the web works without AI、ADR 0004 資料留在本地或雲端、each person sees only their own runs | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-037 | 作法 6「其餘」 | 不在範圍 | PRODUCT.md 已改 | `git diff origin/v3 -- PRODUCT.md` | 只有 **Who**、**Not**、**Principles** 三行有變；**Job**、**Path**、標題一字未動；沒有新增段落 | 手動：指令貼 ledger（不適用 TESTING.md） |

## User Story 3 — DESIGN.md 補維護者原話 23–25（優先度 P1）

維護者原話：2026-10-27「一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」；2026-10-30「介面還是不好，AWS, Azure介面就不能跟國網一樣，請你去參考Seqera platform的介面，不要都自己腦補」；2026-11-03「我的意思是介面設計多去參考Seqera, galaxy等」；2026-10-23 網頁終端機完整句（原話 19）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-038 | 作法 7；原話 2026-10-27 | 功能 | DESIGN.md「Maintainer's words」段 | `grep -F` 整行 | 存在這一行，逐字（含全形引號、半形括號與引號）：`23. 「一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」 (10-27)` | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-039 | 作法 7；原話 2026-10-30 | 功能 | 同上 | `grep -F` 整行 | 存在：`24. 「介面還是不好，AWS, Azure介面就不能跟國網一樣，請你去參考Seqera platform的介面，不要都自己腦補」 (10-30)` | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-040 | 作法 7；原話 2026-11-03 | 功能 | 同上 | `grep -F` 整行 | 存在：`25. 「我的意思是介面設計多去參考Seqera, galaxy等」 (11-03)` | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-041 | 作法 7 | 功能 | 同上 | 看行的順序 | 依序為 `22.`、`23.`、`24.`、`25.`，之後才是 `## Skeleton`；三列格式比照 18–22（編號、原話、括號日期） | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-042 | 原話 2026-10-23（網頁終端機）；作法 7「其餘一字不動」 | 不在範圍 | 同上 | `grep -F` 原話 19 | 這句仍逐字存在：`19. 「是中欄有個可以切換主視窗跟終端機的按鈕。終端機能否直接使用? 我要在AI幫我跑時同時看到終端機的輸入指令變化，但我同時也可以自己打。下游的中欄主視窗是R studio，但切換成終端機就是跑在我的電腦。」 (10-23)` | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-043 | 作法 7 | 不在範圍 | 同上 | `grep -F` 第 22 列 | `22. 「分成四類 改成 跟Seqera platform一樣的模式，不要自己定義」 (10-23 20:15)` 仍逐字存在 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-044 | 範圍「DESIGN.md 釘住處」；原話 2026-10-27（中文不口語） | 不在範圍 | 「## 用字」段 | 跑 `platform/tests/test_web_guided_launch_2b.py` 的 `test_h11_design_has_the_word_list` | 通過（用字詞表沒被動到） | 自動：`platform/tests/test_web_guided_launch_2b.py::test_h11_design_has_the_word_list` |
| TC-045 | 範圍「DESIGN.md 釘住處」 | 不在範圍 | upload 段 | 跑 `platform/tests/test_web_upload.py` 的 `test_tc101_design_md_upload_data_paragraph` | 通過（兩句 upload 段落沒被動到） | 自動：`platform/tests/test_web_upload.py::test_tc101_design_md_upload_data_paragraph` |
| TC-046 | 作法 7 | 不在範圍 | DESIGN.md 已改 | `git diff origin/v3 -- DESIGN.md` | 只有 3 行新增（23、24、25），0 行刪除、0 行修改 | 手動：指令貼 ledger（不適用 TESTING.md） |

## User Story 4 — 測試：新測試、版本釘住與既有測試（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-047 | 失敗先行測試；裁決第一輪 5 | 功能 | 全部改完 | `bash tests/charter_v4_workflow_test.sh` | 全部 ok、結束碼 0；風格同 `dev_workflow_test.sh`（`has`／`lacks`）；涵蓋 TC-005 到 TC-043 中標為該檔的每一條斷言 | 自動：`tests/charter_v4_workflow_test.sh` |
| TC-048 | 完成標準；裁決第一輪 4 | 功能 | ledger | 看 ledger 的紅燈紀錄 | 有「改文件前」的紅輸出：版本行釘住（TC-E5、platform_direction TC-001 的 6.2.0 釘值）與 PRODUCT.md／DESIGN.md 斷言為紅；改後為綠。憲法內容斷言與 TC-E9 在 base 即綠，ledger 說明這是 hunk 的回歸保護 | 手動：ledger 貼輸出（不適用 TESTING.md） |
| TC-049 | 範圍「若 CI／run_all 以名單跑測試」 | 功能 | 新測試檔已建 | `git grep -n "dev_workflow_test" -- tests/run_all.sh .github`；跑 `tests/run_all.sh`（WSL）看清單 | 新測試會被 `run_all.sh` 跑到（以名單跑則已登入名單）；`.github/` 沒被改（若名單在 `.github/` 內，executor 應停下來問而非改） | 手動：指令與輸出貼 ledger |
| TC-050 | 作法 8「不放寬、不刪其他斷言」 | 不在範圍 | 兩個既有測試檔 | `git diff origin/v3 -- tests/constitution_scope_test.sh tests/platform_direction_docs_test.sh`（再與 base 逐行比對） | 變動只有：版本字串 6.1.0→6.2.0、日期 2026-10-25→2026-11-03、TC-021 描述字串、TC-E9 新增、platform_direction TC-001 名稱；沒有刪除、略過或放寬任何其他斷言 | 手動：diff 貼 ledger |
| TC-051 | 失敗先行「既有測試」 | 功能 | 全部改完 | `bash tests/constitution_scope_test.sh` | 全綠（含 TC-021、TC-E4、TC-E5、TC-E7、TC-E8、TC-E9） | 自動：`tests/constitution_scope_test.sh` |
| TC-052 | 失敗先行「既有測試」 | 功能 | 同上 | `bash tests/platform_direction_docs_test.sh` | 全綠 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-053 | 失敗先行「既有測試」 | 功能 | 同上 | `bash tests/dev_workflow_test.sh` | 全綠（只釘 "Test cases before code"、"Independent acceptance"，這兩句沒被動到） | 自動：`tests/dev_workflow_test.sh` |
| TC-057 | 完成標準 | 功能 | HEAD 乾淨 | 看 `executor-status` 與全套結果 | `tests/run_all.sh` 全綠（WSL；已知環境紅須在 ledger 說明）；完成記號為 `GREEN <HEAD sha>` | 手動：閱卷閘門檢查＋ledger |

## 憲法與安全網

動到的憲法段落只有 Development Workflow 最後一條、Amendments 新條目、Governance 一句與版本行。以下確認沒有碰到原則（I–…）、Invariants 與其 Check、Safety Net，且憲法引用的檢查仍存在。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-028 | Governance／Development Workflow；作法 0 | 功能 | 分支已改完 | `git diff origin/v3 -- .specify/memory/constitution.md`，逐 hunk 對照計畫作法 1–5（以裁決補回的新版 hunk A 與 hunk C 為準） | 只有 A（Workflow 最後一條）、B（同一 bullet 的風險分級一句）、C（6.2.0 條目）、D（Governance 一句）與版本行五處；每處文字與計畫一致；多一個 hunk 即不通過 | 手動：diff 貼 ledger（不適用 TESTING.md） |
| TC-029 | 「Never edit during implementation」；裁決 1 | 不在範圍 | executor 的提交 | `git diff charter-v4-base...HEAD -- .specify/memory/constitution.md`（base 為 developer-agent 預先 commit 的分支） | 無輸出：executor 的提交沒有任何憲法改動 | 手動：指令貼 ledger |
| TC-054 | 各 Invariant 的 Check | 功能 | 全部改完 | `bash tests/constitution_6_test.sh` | 全綠 | 自動：`tests/constitution_6_test.sh` |
| TC-055 | 各 Invariant 的 Check 仍指到存在的檔案 | 功能 | 同上 | `bash tests/constitution_checks_exist_test.sh` | 全綠（無 NO CHECK、DANGLING、SENTENCE） | 自動：`tests/constitution_checks_exist_test.sh` |
| TC-056 | 原則 I–…、Invariants、Safety Net；計畫「不做」第 1 條 | 不在範圍 | 分支已改完 | 在 `git diff origin/v3 -- .specify/memory/constitution.md` 中查 `-` 行與各 hunk 落點 | `-` 行只落在 hunk A、hunk D 與版本行；原則、Invariants 與 Check、Safety Net 章節沒有任何 hunk | 手動：diff 貼 ledger（計畫指定的手動案例） |

## User Story 5 — 範圍與流程（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-058 | 範圍；不做「開發模式啟動」 | 不在範圍 | 分支已改完 | `git diff --stat origin/v3` | 檔案只有範圍內的：`.specify/memory/constitution.md`、`PRODUCT.md`、`DESIGN.md`、`tests/constitution_scope_test.sh`、`tests/platform_direction_docs_test.sh`、`tests/charter_v4_workflow_test.sh`、`specs/charter-v4-workflow/` 下的計畫與 ledger（以及 run_all 名單若在範圍內檔案）；沒有任何開發模式啟動（dev-mode launch）相關的檔案 | 手動：輸出貼 ledger |
| TC-059 | 不做「不改 CLAUDE.md、PRINCIPLES、README、ROADMAP、.github、plugin.json、hooks」；範圍「不准碰」 | 不在範圍 | 同上 | 同一份 `git diff --stat` 查下列路徑 | 以下皆無變動：`CLAUDE.md`、`docs/PRINCIPLES.md`、`README.md`、`docs/ROADMAP.md`、`docs/TESTING.md`、`docs/PITFALLS.md`、`dev-queue.json`、`.github/`、`hooks/`、`plugin.json`（`.claude-plugin/plugin.json`）、`platform/` | 手動：輸出貼 ledger |
| TC-060 | 不做「10-23 網頁終端機、自動續跑、OTP 憲法修正案」 | 不在範圍 | 憲法 diff | 在憲法 diff 的 `+` 行搜尋 | 沒有新增網頁終端機、自動續跑（resume 不用確認）、OTP／一次性驗證碼的核可或規則；6.2.0 條目對網頁終端機只有 Sync Impact Report 那句「later, after its own amendment」的描述，沒有宣告已核可 | 手動：指令貼 ledger |
| TC-061 | 完成標準（risk L 爆炸半徑） | 功能 | 全部改完 | `git grep -n` 搜尋重述被改兩句（合併規則、`main` 接收合併）的其他檔 | 沒有其他檔重述這兩句而未同步（`docs/PRINCIPLES.md`、`README.md`、`CLAUDE.md` l.192、`docs/adr/0006`、`docs/adr/0011` 等查過不需改）；指令與輸出貼 ledger，閱卷者自跑核對 | 手動：指令與輸出貼 ledger |
| TC-062 | 完成標準「合併前」；原話「合併規則同意」 | 功能 | PR 已開 | 看 PR 描述 | 引用維護者 2026-11-03 原話「合併規則同意」，並點名 Workflow 那條中「修改或刪除需求仍須維護者先說好」這一句，請維護者確認該話所指的規則涵蓋它 | 手動：PR 描述（developer-agent 合併前確認） |
| TC-063 | 完成標準；risk L | 功能 | 閱卷通過後 | 看 ledger／閱卷紀錄 | 有 Opus 對抗審的結果（沒有已證實的發現，或發現已處理）；閱卷有爆炸半徑證明（憲法 diff 逐 hunk 說明沒碰原則與 Safety Net） | 手動：ledger 與閱卷紀錄 |
