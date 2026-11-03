---
id: charter-v4-workflow
title: 憲法 6.2.0（MINOR）加上 PRODUCT.md、DESIGN.md 同步，讓文件寫的跟現在開發的方式一致
tier: A
kinds: docs
risk: L
lane: L-charter
branch: docs/charter-v4-workflow
base: origin/v3（開工前 `git fetch` 並重查行號；憲法版本行現為 6.1.0 | Last Amended 2026-10-25）
source: 維護者 2026-11-03「合併規則同意」；2026-10-24「以後你都自己合併」；PRODUCT.md／DESIGN.md 依 10-23、10-27、10-30、11-03 的原話
---

# charter-v4-workflow

> 只有計畫、沒有程式。A 級（憲法修正案）：維護者已於 2026-11-03 用自己的話同意合併規則；PR 開出後，PASS＋CI 綠＋Opus 對抗審通過，developer-agent 才合併。`risk: L`（動憲法，保護路徑）：閱卷多交爆炸半徑證明。

## 目標
讓三份治理文件寫的跟 2026-10-24 以來實際的做法一致：憲法 6.2.0 把「誰合併」「從哪條分支開發」「v4 風險分級」寫進 Development Workflow 與 Governance；PRODUCT.md 改成 nano4、網頁終端機不再是「不做」、加上「參考成熟平台」原則；DESIGN.md 補維護者原話 23–25。對使用者的意義：下一位讀文件的人（或 agent）不會照過時的規則等維護者按「好」才合併一般變更，也不會誤以為網頁終端機被否決。

## 維護者原話（verifier 出題用）
- 2026-10-24：「以後你都自己合併」。
- 2026-11-03：「合併規則同意」。
- 2026-10-23（網頁終端機）：「是中欄有個可以切換主視窗跟終端機的按鈕…」（完整句見 DESIGN.md 原話 19：「是中欄有個可以切換主視窗跟終端機的按鈕。終端機能否直接使用? 我要在AI幫我跑時同時看到終端機的輸入指令變化，但我同時也可以自己打。下游的中欄主視窗是R studio，但切換成終端機就是跑在我的電腦。」）。
- 2026-10-30：「介面還是不好，AWS, Azure介面就不能跟國網一樣，請你去參考Seqera platform的介面，不要都自己腦補」。
- 2026-11-03：「我的意思是介面設計多去參考Seqera, galaxy等」。
- 2026-10-27：「一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」。

每句至少一條測試案例（見「失敗先行測試」）。

## 範圍：檔案（只准改這些）
- `.specify/memory/constitution.md`（**本任務的計畫明文授權改它**，見「作法」第 0 點；只准動列出的四處）
- `PRODUCT.md`
- `DESIGN.md`（只在「Maintainer's words」段尾追加 23–25）
- `tests/constitution_scope_test.sh`（l.40 版本斷言、l.42 Last Amended、l.292 TC-E5 版本行；新增 TC-E9）
- `tests/platform_direction_docs_test.sh`（l.52–54 TC-001 版本行）
- 新檔 `tests/charter_v4_workflow_test.sh`（本任務的新斷言放這裡，免得動既有檔太多）
- 若 CI／`tests/run_all.sh` 以名單跑測試：把新檔登進名單（先 `git grep -n "dev_workflow_test" origin/v3 -- tests/run_all.sh .github` 確認；`.github/` 不准改，若名單在 `.github/` 內就停下來問，不要改）
- **查過、不需要改**（內容不重述被改的句子，也不釘版本）：`docs/PRINCIPLES.md`（只有 6.0.0 的引用；l.352 之後無合併規則句）、`README.md`（只提 6.0.0）、`CLAUDE.md`（l.192「merges follow the decision tiers in the constitution's Development Workflow」仍然成立，不改）、`tests/dev_workflow_test.sh`（只釘 "Test cases before code"、"Independent acceptance"，這兩句不動）、`docs/ROADMAP.md` l.45（歷史列）、`docs/adr/0006`、`docs/adr/0011`（引用 6.1.0 屬歷史）。
- 沒有任何測試對 PRODUCT.md／DESIGN.md 做雜湊。釘 DESIGN.md 的只有 `platform/tests/test_web_guided_launch_2b.py:639`（「## 用字」段詞表）與 `platform/tests/test_web_upload.py:1192`（兩句 upload 段落）；本任務不動那兩段，兩條必須維持綠。
- 沒有任何測試釘 PRODUCT.md 的字句（`git grep -n "Taiwania3" origin/v3 -- tests platform/tests` 為空；`tests/` 內 PRODUCT.md 零命中）。
- **不准碰**：`.github/`、`hooks/`、`plugin.json`、`platform/`、`specs/`、憲法的原則（I–…）與 Safety Net 章節、`docs/PITFALLS.md`、dev-queue.json。

## 作法
0. **憲法怎麼改**：executor **不得**修改憲法。下列 hunk A～D 與版本行由 developer-agent 預先 commit 在 base 分支 `charter-v4-base`（見「裁決」1）；executor 從第 6 點開始做。verifier 用 `git diff origin/v3 -- .specify/memory/constitution.md` 逐 hunk 核對與本段文字一致，多一個 hunk 就判 FAIL。
1. **憲法 hunk A（Development Workflow 最後一條）**：把 "One change at a time, on a branch." 整條重寫成：開發基底是分支 `v3`（`main` 是 v2 線），合併只進 `v3`，不再寫 "`main` receives merges only"；CI（`.github/workflows/tests.yml`）必須綠、獨立驗收必須通過；通過後由開發主責（development lead）合併每一個 PR；但**憲法修正、發行、任何放寬 Safety Net 的變更**，須先取得維護者用自己的話明確說的「好」，才由開發主責合併。保留原有 "fixes, tests, docs, refactors, changes that only make the Safety Net stricter" 的分級意思，不得變成「維護者不再管任何事」。
2. **憲法 hunk B（同一條之後新增一句）**：v4 風險分級——一句話：改到保護路徑（`.github/`、hooks、本憲法、`plugin.json`、`platform/abf_station/`）的變更，合併前須有爆炸半徑證明與第二次對抗審。（寫成同一個 bullet 內的一句，不新開條；不改 Safety Net 任何字。）
3. **憲法 hunk C（新增 `### 6.2.0 (2026-11-03): …`）**：放在 6.1.0 條目之後、`## Governance` 之前；標題用英文，格式同 6.1.0，依序六個粗體標籤（`**Rationale.**`、`**What changes.**`、`**Sync Impact Report.**`、`**Impact on existing deployments.**`、`**Version.**`、`**Approval.**`）。
   - Rationale：引用 2026-10-24「以後你都自己合併」與 2026-11-03「合併規則同意」；寫明 2.1.0 起的字面（一般使用者可見變更等維護者的 yes、只有維護者合併修正案）已與 10-24 以來的做法不符。
   - What changes：四點——誰合併；修正案、發行、放寬 Safety Net 仍須維護者先說好；基底是 `v3`；v4 風險分級一句。明說「沒有任何原則或 Safety Net 規則被刪或重新定義」。
   - Sync Impact Report：列本任務動到的檔（PRODUCT.md、DESIGN.md 原話 23–25、兩個版本釘住測試、新測試）。
   - Impact：無部署影響，只改流程字句。
   - Version：`**Version.** MINOR, under Governance: a rule is materially expanded (who merges, and the protected-path review); no principle or Safety Net rule is removed or redefined.`
   - Approval：`The maintainer approved this change in his own words on 2026-11-03 (「合併規則同意」); the development lead merges the pull request after CI is green and the acceptance passes.`
4. **憲法 hunk D（Governance 那句）**：把 "Only the maintainer approves and merges it." 改成：維護者須先用自己的話明確同意，之後由開發主責合併這個 PR。其餘 Governance 字句不動。
5. **版本行**（檔案最後一個非空行，須完全一致）：`**Version**: 6.2.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-11-03`。
6. **PRODUCT.md**：
   - **Who**：`NCHC Taiwania3` → `NCHC nano4`；句尾加括號出處不必，環境事實段有。
   - **Not**：刪掉 "a web terminal;"，其餘（Seqera clone with many top-level pages、chatty AI text、roles、Data Explorer、Dashboard）不動。
   - 新增一句「later, after its constitution amendment」：網頁終端機（維護者 2026-10-23 要求）排在之後，待它自己的憲法修正案——放在 **Not** 的 "(later)" 清單裡，與 roles／Data Explorer／Dashboard 同處，不另開段。
   - **Principles** 加一條：介面設計沿用成熟平台（Seqera Platform、Galaxy）的做法，不自創版面；同時維持較少的頂層頁面。
7. **DESIGN.md**：在 `22.` 之後、`## Skeleton` 之前追加三列，編號 23、24、25，原話逐字（含全形引號 「」，不改標點）：
   - `23. 「一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」 (10-27)`
   - `24. 「介面還是不好，AWS, Azure介面就不能跟國網一樣，請你去參考Seqera platform的介面，不要都自己腦補」 (10-30)`
   - `25. 「我的意思是介面設計多去參考Seqera, galaxy等」 (11-03)`
   格式比照 18–22（編號、原話、括號日期）。其餘一字不動。
8. **測試**：只改兩個版本釘住（6.1.0→6.2.0、2026-10-25→2026-11-03）；`constitution_scope_test.sh` l.40 描述字串補上 6.1.0 與 6.2.0 的順序（"…6.0.2, 6.1.0 and 6.2.0 came after"），斷言改 `'**Version**: 6.2.0'`。不放寬、不刪其他斷言。

## 失敗先行測試
新檔 `tests/charter_v4_workflow_test.sh`（風格同 `dev_workflow_test.sh` 的 `has`／`lacks`），先寫、改文件前跑確認紅，紅的輸出貼進 ledger；另在 `constitution_scope_test.sh` 加 TC-E9。
- TC-E9（scope test）：以 `awk '/^### 6\.2\.0 \(2026-11-03\)/{f=1} /^## Governance/{f=0} f'` 抽出條目；存在；六個標籤依序出現；含 `**Version.** MINOR`；含「以後你都自己合併」與「合併規則同意」兩句原話（verbatim）。**現在紅**。
- 版本行：最後非空行等於 6.2.0 那一行（TC-E5、platform_direction TC-001 改釘後**現在紅**）。
- 憲法 Workflow 最後一條：含 `v3` 與「`main` 是 v2 線」之意；**不含** "`main` receives merges only"；含 "development lead merges" 之意與 "amendments" "releases" "loosens the Safety Net" 三項仍須維護者明確的 yes。（原話 2026-10-24、11-03 各一條 verbatim 比對在 6.2.0 條目。）
- 憲法含 v4 風險分級那一句，且同句含五個保護路徑：`.github/`、hooks、constitution、`plugin.json`、`platform/abf_station/`。
- 憲法 Governance 不再含 "Only the maintainer approves and merges it"，但仍含 "supersedes all other practices"、"MUST NOT restate"（其餘不動的反向檢查）。
- Safety Net 與原則不變：`git diff origin/v3 -- .specify/memory/constitution.md` 的 `-` 行只落在 hunk A、D 與版本行（手動案例，證據貼 ledger，見 README 通例）。
- PRODUCT.md：不含 "Taiwania3"；含 "nano4"；**Not** 行不含 "web terminal"；含「later」＋ constitution amendment 之意；Principles 含 "Seqera Platform" 與 "Galaxy" 與「fewer top-level pages」之意。
- DESIGN.md：含 `23.`、`24.`、`25.` 三列，且原話字串逐字存在（逐一 `grep -F`）；`22.` 列、「## 用字」段不變；`test_h11_design_has_the_word_list`、`test_tc101_design_md_upload_data_paragraph` 仍綠。
- 既有測試：`bash tests/constitution_scope_test.sh`、`platform_direction_docs_test.sh`、`dev_workflow_test.sh`、`constitution_6_test.sh`、`constitution_checks_exist_test.sh` 全綠（TC-E4 與 TC-E8 的 awk 都抽到 `## Governance` 為止，新增 6.2.0 條目不影響它們；TC-E7 查 6.0.2 條目不受影響）。

## 完成標準（done when）
- 新測試與 TC-E9 改前紅、改後綠；`tests/run_all.sh` 全綠（WSL；已知環境紅見 README 通例）。
- ledger 記：`git diff --stat` 只含範圍內的檔；憲法 diff 只有 A、B、C、D 與版本行；既有斷言除兩處版本釘住與一句描述字串外沒被刪或放寬。
- `risk: L`：閱卷附爆炸半徑證明——憲法 diff 逐 hunk 說明沒碰原則與 Safety Net；`git grep -n` 證明沒有其他檔重述被改的兩句（合併規則）而沒同步；PASS 後再跑一次 Opus 對抗審。
- 合併前：developer-agent 確認維護者 11-03 的「合併規則同意」就是這一版文字所指的規則（PR 描述引用原話）。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」；單檔測試 `bash tests/<name>.sh`（Git Bash 多數可跑），全套在 WSL。
- 版本釘住在兩處（`tests/constitution_scope_test.sh` l.40／l.42／l.292，`tests/platform_direction_docs_test.sh` l.52），其他 tests、docs 都不釘；`docs/PRINCIPLES.md`、`README.md` 只提 6.0.0。
- 2026-10-20 決定：nano4 取代 Taiwania3（PRODUCT.md 唯一出現處在 **Who** 行）。
- 網頁終端機：DESIGN.md 原話 10 寫「cancelled (10-18)，由 19 取代」；ADR 0011 已記錄翻案；它自己的憲法修正案（10-23 的終端機／自動續跑／OTP）是另案，不在本任務。
- 憲法用語：開發主責＝the development lead（既有字句），不要新創詞。

## 不做
- 不改任何原則（I–…）或 Safety Net 的字，不改憲法 Invariants 與其 Check。
- 不做開發模式啟動（dev-mode launch）。
- 不做 10-23 的網頁終端機、自動續跑、OTP 憲法修正案（另案；PRODUCT.md 只改成「之後，待它自己的修正案」，不宣告已核可）。
- 不改 `CLAUDE.md`、`docs/PRINCIPLES.md`、`README.md`、`docs/ROADMAP.md`（查過沒有重述）。
- 不改 `.github/`、`plugin.json`、`hooks/`。

## 裁決
1. **誰套用憲法文字？（2026-11-03 developer-agent 裁決）** executor 不准碰憲法（`pretool_executor_write_guard.py` 對 constitution.md 無例外，6.0.2 前例）。developer-agent 在派工前把「作法」列的四個憲法 hunk 與版本行 commit 在分支 `charter-v4-base`（從 origin/v3 開），supervise 以它為 base；executor 只做 PRODUCT.md、DESIGN.md 與測試，**不得修改** `.specify/memory/constitution.md`。verifier 閱卷時逐 hunk 核對憲法 diff 與本計畫文字一致，不一致判 FAIL 交回 developer-agent。PR 開往 `v3`（含 developer-agent 那個 commit，單一 PR）。
2. **v4 風險分級那一句放哪？** 建議：同一個 Workflow bullet 內，不另開條，免得「新原則」觸發 MAJOR／MINOR 之爭；版本仍為 MINOR（規則實質擴大）。
3. **PRODUCT.md「later」寫在 Not 內還是新增 Later 行？** 建議：寫在 Not 行的 later 清單（roles、Data Explorer、Dashboard 同處），少一個新段落。

## 專長守則（docs）

（工作區沒有 `.claude/dev-profiles/docs.md`；本任務無專長守則。）
