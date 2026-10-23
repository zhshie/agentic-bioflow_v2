# 測試案例：README 首段、ADR 0008 附註、ROADMAP 改成 10-21 新方向

**規格**：`specs/readme-adr-roadmap/plan.md`（本件沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應。本件是純文件修改，沒有這一類。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

驗證方式的說法：

- **自動**：既有的測試檔，全套綠就代表它還成立，本件不新增任何測試。
- **閱卷**：verifier 用 `git diff v3...HEAD` 對照下面「逐字對照表」，一字不差才算過。這是因為計畫明說「不加新的釘字串測試，免得把待他裁決的措辭釘死」。
- **手動**：看 PR 說明這類不在 repo 檔案裡的東西。

## 逐字對照表（執行者必須照抄，verifier 逐字比對）

以下文字全部取自計畫的「作法」與「裁決」，不是 verifier 自己編的。

**A1　README 標題（取代原第 1 行 `# agentic-bioflow v2`）**

```
# agentic-bioflow
```

**A2　README 新段落第一段（插在原第 3 行 "Run Nextflow/nf-core pipelines through **Seqera Platform**, from Claude Code." 之前）**

```
Run nf-core pipelines on your own HPC account or cloud, from Claude Desktop or a web page, through a platform you host yourself. Nothing goes through Seqera. The first site is NCHC's nano4; Google Batch, AWS Batch and Azure/Kubernetes follow. This is the `v3` branch.
```

**A3　README 新段落第二段（緊接 A2，中間隔一空行）**

```
**v2 (the `main` branch)** is the Claude Code plugin that runs pipelines through Seqera Platform. It takes bug fixes until 2027. The rest of this file describes v2 until v3.0.0 is released.
```

**B1　ADR 0008 附註（緊接在第 3 行 `> Point 1 (the page skeleton) is replaced by ADR 0009 (2026-10-17): …` 之後，一行）**

```
> Note (2026-10-21, `docs/ROADMAP.md`): cloud compute environments open in the order Google Batch, AWS Batch, Azure/Kubernetes; NCHC's nano4 is the main site; Taiwania 3 takes bug fixes only, until 2027. Nothing in the decision below is withdrawn.
```

**C1　ROADMAP 第 1 列 What changes：被取代的原句**

```
007b is built and waits for its manual acceptance on the real cluster (TC-047 to TC-050 in `docs/TESTING.md`).
```

**C2　ROADMAP 第 1 列 What changes：換成的新句**

```
007b is built; its manual acceptance runs on NCHC's nano4 (TC-047n to TC-051n in `docs/TESTING.md`, table `specs/007b-launch/acceptance-nano4.md`); Taiwania 3 takes bug fixes only, until 2027.
```

**C3　ROADMAP 第 1 列 Done when：被取代的片段 → 新片段**

```
改前：the platform's "list rawdata" and "launch ampliseq" both succeed through it
改後：the platform's "list rawdata" and "launch nf-core/ampliseq 2.18.0" on nano4 both succeed through it
```

**C4　ROADMAP 第 3 列 What changes：新增的一句（放在 `016: Studios (…)` 那句之後、格子結尾之前）**

```
017: a drag-and-drop canvas: nf-core modules as blocks, connect, fill parameters, validate, launch, export a zip, versions and sharing inside the lab; no nested subworkflows (017a–e).
```

**C5　ROADMAP 第 3 列 Done when：新增的結尾（接在 `(charging waits on the open questions below)` 之後）**

```
; the trial counts as a success when a colleague completes one 16S run without asking the maintainer anything
```

**C6　ROADMAP 第 4 列 What changes：要刪掉的兩段**

```
刪 1：The station agent also runs on a VM the lab rents; 
刪 2：; TWCC first
```

**C7　ROADMAP 第 4 列 What changes：結尾換成**

```
; the order is Google Batch, then AWS Batch, then Azure/Kubernetes. A cloud user installs no station agent: the platform host runs Nextflow itself, with the cloud account's key in a file on that host and never in the database (an HPC site credential still never reaches the platform)
```

**C8　ROADMAP Open questions 的 TWCC 那條：句首新增**

```
(Dropped from Stage 4 on 2026-10-21; kept for the record.) 
```

## User Story 1 — README 門面改成現在的產品（優先度 P1）

目標：第一次看 repo 的人讀到的是自架平台、從 Claude Desktop 或網頁啟動、不經 Seqera、nano4 是主站；v2 的 Seqera 路徑說明它到 2027 只修 bug。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1（標題） | 功能 | 對照 `v3` 分支的 `README.md` | 讀改完後 `README.md` 的第 1 行 | 第 1 行恰好是對照表 A1 `# agentic-bioflow`，不再有 ` v2`。 | 閱卷 |
| TC-002 | 作法 1（新段落第一段）；M1-08 措辭 | 功能 | 同上 | 讀標題之後的內容 | 標題後（隔一空行）是對照表 A2 的整段，一字不差；它出現在 "Run Nextflow/nf-core pipelines through **Seqera Platform**, from Claude Code." 這句之前。 | 閱卷 |
| TC-003 | 作法 1（新段落第二段） | 功能 | 同上 | 讀 A2 之後的內容 | A2 之後隔一空行是對照表 A3 的整段，一字不差，緊接在舊的 "Run Nextflow/nf-core pipelines through **Seqera Platform**…" 那句之前。 | 閱卷 |
| TC-004 | 作法 1（其餘一字不動）；裁決 3 | 功能 | 同上 | 對 `README.md` 跑 `git diff v3...HEAD` | diff 只有兩種變動：第 1 行標題改掉，以及在舊第 3 行之前插入 A2、A3 兩段（含空行）。舊第 3 行 "Run Nextflow/nf-core pipelines through **Seqera Platform**, from Claude Code." 及其後所有行一字未動，也沒有為它另加任何標示。 | 閱卷 |
| TC-005 | 作法 1（保住被測試釘住的字串） | 功能 | 同上 | 在改完的 `README.md` 搜尋這兩個字串 | `Nextflow's own records, the truth under constitution 6.0.0` 與 `Constitution 2.0.0` 兩者都還在，各自所在的句子沒被改。 | 自動：`tests/constitution_6_test.sh`、`tests/constitution_scope_test.sh`、`tests/platform_direction_docs_test.sh`（TC-059） |
| TC-006 | 維護者原話：M1-08 README 措辭、裁示 2、裁示 3、裁示 4 | 功能 | 同上 | 一位沒看過 repo 的人只讀 README 開頭兩段 | 他能從文字本身讀到五件事：平台是自己架的（"a platform you host yourself"）；從 Claude Desktop 或網頁啟動；不經 Seqera（"Nothing goes through Seqera."）；第一個站是 NCHC 的 nano4，之後依序 Google Batch、AWS Batch、Azure/Kubernetes；`main` 分支的 v2 走 Seqera 路徑，只修 bug 到 2027。對照表 A2、A3 逐字相符即為通過。 | 閱卷 |
| TC-007 | 不做：「不改 README 第一段以後的 v2 說明（v3.0.0 發版時另一件整份重寫）」 | 不在範圍 | 同上 | 對 `README.md` 跑 `git diff v3...HEAD` | 除了標題與新插入的兩段，沒有任何一行被改、刪或新增；舊的 Seqera／Claude Code 說明、安裝、指令、憲法段落全部原樣。 | 閱卷 |

## User Story 2 — ADR 0008 加一行附註（優先度 P1）

目標：ADR 0008 的讀者在標題下就看到「雲端順序、nano4 是主站、台灣杉三只修 bug」，但決策本文一個字不變。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-008 | 作法 2 | 功能 | 對照 `docs/adr/0008-web-scope-studios-projects-cloud.md` | 讀改完後該檔的前幾行 | 第 3 行仍是 `> Point 1 (the page skeleton) is replaced by ADR 0009 (2026-10-17): three panes around a project's analyses.`；緊接其後的新一行是對照表 B1，一字不差（含日期 2026-10-21、順序 Google Batch, AWS Batch, Azure/Kubernetes、"Taiwania 3 takes bug fixes only, until 2027"、"Nothing in the decision below is withdrawn."）。 | 閱卷 |
| TC-009 | 作法 2（決策本文不改） | 功能 | 同上 | 對該檔跑 `git diff v3...HEAD` | diff 只新增 B1 這一行（外加因此造成的行號位移），沒有刪除、沒有改動任何既有行；第 3 行以前與 B1 以後的內容一字未動。 | 閱卷 |
| TC-010 | 不做：「不新增 ADR」 | 不在範圍 | `docs/adr/` 目錄 | 比對 base 與 HEAD 的 `docs/adr/` 檔案清單 | 沒有任何新的 ADR 檔案（例如 0010 號）；除 0008 外，其他 ADR 一字未動。 | 閱卷 |

## User Story 3 — ROADMAP 第 1、3、4 階段與 TWCC 問題改成新方向（優先度 P1）

目標：ROADMAP 反映 10-21 的決定，nano4 主站、雲端順序、畫布、零支援的試用成功標準；三列只改格子內文字。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 作法 3（第 1 列 What changes）；裁示 3；不做清單（Taiwania 3） | 功能 | 對照 `docs/ROADMAP.md` 第 1 列（`\| 1 \| **Station agent** (feature 007)`） | 讀第 1 列的 What changes 格 | 對照表 C1 的舊句已不存在；原處是對照表 C2 的新句，一字不差。新句同時說出：驗收在 nano4 跑、步驟編號 TC-047n 到 TC-051n、驗收表路徑 `specs/007b-launch/acceptance-nano4.md`、台灣杉三只修 bug 到 2027。 | 閱卷 |
| TC-012 | 作法 3（第 1 列 NCHC first 句保留） | 功能 | 同上 | 在第 1 列找這一段 | `station agent + compute environments (Seqera model, all types; NCHC first)` 原樣還在；第 1 列開頭 `\| 1 \| **Station agent** (feature 007) \|` 沒變；除 C1→C2 與 C3 外，該列其餘文字一字未動。 | 自動：`platform/tests/test_station_docs.py::test_tc077`；其餘部分閱卷 |
| TC-013 | 作法 3（第 1 列 Done when）；維護者原話 | 功能 | 同上 | 讀第 1 列的 Done when 格 | 片段已由對照表 C3「改前」換成「改後」，即 `the platform's "list rawdata" and "launch nf-core/ampliseq 2.18.0" on nano4 both succeed through it`；該格其餘部分（含 "The agent runs on the maintainer's laptop;"、"a gate refuses `rm results`; NCHC has answered M6"）不動，格子不是空的。 | 閱卷；非空由 `test_station_docs.py::test_tc077` 與 `tests/platform_direction_docs_test.sh`（TC-022） |
| TC-014 | 作法 3（第 3 列 What changes：017）；裁示 5 | 功能 | 對照第 3 列（`\| 3 \| **Web** (features 011–014, 016)`） | 讀第 3 列 What changes 格的結尾 | 對照表 C4 的 017 句一字不差，位置在 `016: Studios (…)` 那句之後、該格結尾之前；句中有「nf-core modules as blocks」（積木＝nf-core 模組）與「no nested subworkflows」（不做巢狀子流程）。 | 閱卷 |
| TC-015 | 作法 3（014 句與標題保留）；裁示 6（平台內建聊天繼續做） | 功能 | 同上 | 讀第 3 列的開頭與 014 那句 | 列首標題仍恰好是 `\| 3 \| **Web** (features 011–014, 016)`（沒有加 017）；`014: the platform's chat, connecting to the model the user chooses (their own API key or a local model) and calling only the MCP tools of 009` 原樣還在；"matching the actions one to one (parity test)" 在第 3 列仍恰好出現三次。 | 自動：`tests/platform_direction_docs_test.sh`（TC-022 與 4.1.0 TC-018 到 TC-021、W0 TC-014 到 TC-022） |
| TC-016 | 作法 3（第 3 列 Done when）；裁示 17 | 功能 | 同上 | 讀第 3 列 Done when 格的結尾 | 原有整串 `… finished from the web alone; Two members of the trial lab use it for two weeks with fewer than 10 new PITFALLS; the hosted service goes live (charging waits on the open questions below)` 中間沒被插字；對照表 C5 接在 `(charging waits on the open questions below)` 之後、格子的最後，一字不差，開頭的分號不可少。 | 閱卷；原有字串由 `tests/platform_direction_docs_test.sh`（W0 TC-020 兩處）釘住 |
| TC-017 | 維護者原話裁示 17：「同事不問我就能跑完一次 16S（零支援）」 | 功能 | 同上 | 一位同事型讀者讀第 3 列 Done when | 他讀到成功標準是「a colleague completes one 16S run without asking the maintainer anything」，且這句寫在 ROADMAP 第 3 階段 done-when 裡，不是別的地方。 | 閱卷 |
| TC-018 | 作法 3（第 4 列 What changes）；裁決 1；裁示 4 | 功能 | 對照第 4 列（`\| 4 \| **Cloud compute**`） | 讀第 4 列 What changes 格的結尾 | 結尾的 `; TWCC first` 已不存在；原處是對照表 C7，一字不差。讀者能看到：雲端順序 Google Batch → AWS Batch → Azure/Kubernetes；雲端使用者不裝站台代理；平台主機自己跑 Nextflow；雲端帳號金鑰放主機檔案、不進資料庫；HPC 站台憑證仍不進平台。 | 閱卷 |
| TC-019 | 作法 3（第 4 列保留項） | 功能 | 同上 | 在第 4 列找這兩段 | `merged into Stage 1`（含整句 `Merged into Stage 1 as far as modelling goes (merged into Stage 1: the 14 compute environment types are created there, \`docs/SEQERA_PARITY.md\` section F)`）原樣還在；`Nextflow's AWS Batch executor; an estimate and cap before anything is billed` 原樣保留；該列 Done when（`A lab with no NCHC account completes the same 16S`）不動。 | 自動：`platform/tests/test_station_docs.py::test_tc077`（merged into Stage 1）；其餘閱卷 |
| TC-020 | 裁決 1（與裁示 13 矛盾的舊句要刪） | 功能 | 同上 | 在第 4 列搜尋 "The station agent also runs on a VM the lab rents" 與 "TWCC first" | 兩者都已不存在（對照表 C6 的兩段已刪）；同一格裡不會同時出現「代理跑在實驗室租的 VM」與「雲端使用者不裝代理」這兩個互相矛盾的說法。 | 閱卷 |
| TC-021 | 作法 3（Open questions 的 TWCC 條） | 功能 | 對照 `docs/ROADMAP.md` Open questions 中以 `- TWCC: how a lab without an NSTC project pays` 開頭的條目 | 讀該條 | 句首多了對照表 C8（"(Dropped from Stage 4 on 2026-10-21; kept for the record.) "），其後的 `TWCC: how a lab without an NSTC project pays, whether a VM can run Docker and reach the internet, and how long account approval takes.` 一字不動。 | 閱卷 |
| TC-022 | 作法 3 與「失敗先行測試」（不得增減行數、其餘列不動） | 功能 | 對照 base 的 `docs/ROADMAP.md`（128 行） | 比對兩邊行數與每一行 | 總行數仍是 128，不增不減；表格第 1、3、4 三列各仍是單行；第 0、2、5 列與第 90 行、第 98 行（含第 98 行的內容與行號）一字未動；diff 的改動行只落在第 1、3、4 列與 Open questions 的 TWCC 那一條。 | 自動：`platform/tests/test_keep_submissions.py::test_tc063`（行號 98 的釘子）；行數與逐行比對閱卷 |
| TC-023 | 維護者原話裁示 3、4（nano4 主站；四種環境順序）；M1-08 | 功能 | 三份改完的文件 | 對照 README（A2）、ADR 0008（B1）、ROADMAP 第 4 列（C7）的雲端順序與主站說法 | 三處講的是同一件事：主站是 nano4，雲端依序 Google Batch、AWS Batch、Azure/Kubernetes；任何一處都不再寫「TWCC 優先」，也不寫 Seqera 是主路徑。 | 閱卷 |
| TC-024 | 不做清單：「台灣杉三新功能不做（只修 bug 到 2027）」 | 功能 | 同上 | 搜尋 README、ADR 0008、ROADMAP 三份中提到 Taiwania 3 的地方 | 凡提到 Taiwania 3，說法都是「只修 bug，到 2027」（B1 與 C2 各一處）；沒有任何地方把它寫成新功能目標或主站。 | 閱卷 |

## User Story 4 — 交付給維護者審閱（優先度 P1）

C 級：改的是方向的措辭，由維護者讀過後自己 merge。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 完成標準；計畫抬頭「PR 說明要把三處改動逐段列成『改前／改後』」 | 功能 | PR 已開出 | 維護者打開 PR 說明 | 說明裡有三段：README、ADR 0008、ROADMAP，每段都並列「改前」與「改後」的原文（ROADMAP 一段涵蓋第 1、3、4 列與 Open questions 條目），不用讀 diff 就能判斷好不好。 | 手動：看 PR 說明 |
| TC-026 | 計畫抬頭：「PR 不掛自動合併，由維護者讀過措辭後自己 merge」 | 功能 | 同上 | 看 PR 的合併設定 | PR 沒有啟用自動合併（auto-merge），審閱狀態為待維護者；沒有任何程序在維護者回覆前就把它合進 `v3`。 | 手動：看 PR 頁面 |

## 憲法與安全網

本件觸到的是「文件與測試釘住的字串」這道網：憲法 6.0.0、2.0.0 的引用字串、`docs/ROADMAP.md` 第 90 行那條「平台只存中繼資料、不持有站台憑證」的原則、以及 ROADMAP 第 98 行的行號釘子。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-027 | 計畫「完成標準：全套綠」；「允許更新的既有斷言：無」 | 功能 | 在 WSL 或 Linux 內，於本 worktree | 跑 `bash tests/run_all.sh`（CLAUDE.md 寫明的跑法） | 全套通過，沒有任何既有測試變紅。 | 自動：`tests/run_all.sh` |
| TC-028 | 6.0.0 方向文件釘子（ROADMAP 六個階段列首、014 句、Dropped 句；W0 與 4.1.0 的第 3 列釘子；TC-032、TC-038、TC-059） | 功能 | 同上 | 跑 `bash tests/platform_direction_docs_test.sh` | 全綠；特別是 TC-022（stage 0 到 5 的列首、014 句、`Dropped on 2026-10-08: the old "local page to see progress and results"` 與 `the old "Codex adapter" stage`）、W0 TC-020（done-when 兩段逐字）、TC-059（README 兩個字串）。 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-029 | 站台代理文件釘子 | 功能 | 同上 | 跑 `platform/tests/test_station_docs.py::test_tc077` | 通過：第 1 列開頭與 `NCHC first` 句還在、第 4 列有 `merged into Stage 1`、每一列的 Done when 非空。 | 自動：`platform/tests/test_station_docs.py` |
| TC-030 | 憲法 6.0.0 與 2.0.0 的測試（README 的 `Constitution 2.0.0`、`Nextflow's own records`） | 功能 | 同上 | 跑 `bash tests/constitution_6_test.sh` 與 `bash tests/constitution_scope_test.sh` | 兩者都綠。 | 自動：兩個 `tests/constitution_*` 檔 |
| TC-031 | 行號釘子（`docs/ROADMAP.md:98`） | 功能 | 同上 | 跑 `platform/tests/test_keep_submissions.py::test_tc063` | 通過：第 98 行的列沒有位移（改的三列都在第 98 行之前且行數不變）。 | 自動：`platform/tests/test_keep_submissions.py` |
| TC-032 | ROADMAP 第 90 行原則：平台只存中繼資料、不持有站台憑證（"credentials stay on the user's station agent"）；裁決 2 | 功能 | 對照 base 的 `docs/ROADMAP.md:90` | 比對第 90 行；並讀 TC-018 的 C7 括號句 | 第 90 行一字未動；第 4 列的雲端金鑰說法明確只談「雲端帳號金鑰」，並用括號 `(an HPC site credential still never reaches the platform)` 保住 HPC 站台憑證不進平台的原則，沒有寫出「站台憑證會進平台或資料庫」的說法。 | 閱卷 |
| TC-033 | 計畫「允許更新的既有斷言：無」；弱化測試檢查 | 功能 | base 與 HEAD | 跑 `git diff v3...HEAD -- tests platform/tests` | 輸出為空：沒有任何既有測試或斷言被改、刪、跳過；也沒有改 `tests/fixtures`。 | 閱卷 |
| TC-034 | 計畫「範圍：檔案（最終版，只准改這些）」 | 功能 | 同上 | 跑 `git diff --name-only v3...HEAD` | 變更檔案只有 `README.md`、`docs/adr/0008-web-scope-studios-projects-cloud.md`、`docs/ROADMAP.md`、`specs/readme-adr-roadmap/ledger.md`（`plan.md` 是 base 之後已提交的計畫，不算實作改動）；沒有第五個檔案。 | 閱卷 |
| TC-035 | 計畫「不做：不改憲法、不改 CLAUDE.md、不改 POSITIONING／SEQERA_PARITY」 | 不在範圍 | 同上 | 跑 `git diff v3...HEAD -- .specify/memory/constitution.md CLAUDE.md docs/POSITIONING.md docs/SEQERA_PARITY.md` | 輸出為空，四個檔案都沒動。 | 閱卷 |
| TC-036 | 計畫「不做：不改版號、不寫 CHANGELOG」 | 不在範圍 | 同上 | 跑 `git diff v3...HEAD` 並找 `.claude-plugin/plugin.json`、`CHANGELOG*` | 沒有任何版號變動，沒有新建或修改 CHANGELOG；README 中的 "v3.0.0" 只在 A3 那句出現，不代表改了版號。 | 閱卷 |
| TC-037 | 計畫「失敗先行測試：不加新的釘字串測試」；「不需要 migration」 | 不在範圍 | 同上 | 跑 `git diff --name-status v3...HEAD` | 沒有新增或修改 `tests/`、`platform/tests/` 下任何檔案，也沒有新增 migration 檔；新措辭沒有被任何新測試釘死。 | 閱卷 |
