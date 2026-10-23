---
id: readme-adr-roadmap
title: README 首段、ADR 0008 附註、ROADMAP 改成 10-21 新方向（nano4 主站、雲端順序、畫布）
tier: B
kinds: docs
lane: L3
base: v3
review: maintainer
---

# readme-adr-roadmap（M1-08）

> 本檔由 developer-agent 寫（2026-10-23，筆電）、`/supervise` 複製進 worktree 的 `specs/readme-adr-roadmap/plan.md`。**只處理本任務**。
> **C 級（改方向的文字）**：佇列以 `tier: B`＋`review: maintainer` 送（腳本只認 A／B），PR **不掛自動合併**，由維護者讀過措辭後自己 merge。PR 說明要把三處改動逐段列成「改前／改後」，讓他只回好／不好。

## 目標
v3 分支的門面文件還在講「透過 Seqera、Taiwania 3、TWCC 優先」。把它改成 10-21 定的方向，讓第一次看 repo 的人（含試用同事）讀到的是現在的產品：自架平台、從 Claude Desktop 或網頁啟動、nano4 是主站、雲端順序 Google Batch → AWS → Azure／K8s、要做拖拉畫布。

## 維護者原話（verifier 出題用）
- 「自建平台、不依賴 Seqera」（10-20～21 裁示 2）；「主要 HPC＝nano4」（裁示 3）；「四種計算環境都建：nano4 → Google Batch → AWS Batch → Azure／K8s」（裁示 4）。
- 「拖拉畫布做到 GenXflo 程度再多兩件……不做巢狀子流程。積木＝nf-core 模組」（裁示 5）；「平台內建聊天（014）繼續做最簡版」（裁示 6）。
- 「試用成功標準改成『同事不問我就能跑完一次 16S』（零支援；寫進 ROADMAP 第 3 階段 done-when）」（裁示 17）。
- M1-08 的 README 措辭（總表 `memory/PLAN-abf-v3-replan-2026-10.md` 第 134 行）：「自架平台，從 Claude Desktop 或網頁啟動，不經 Seqera；v2/main 的 Seqera 路徑支援到 2027」。
- Taiwania 3：「台灣杉三新功能不做（只修 bug 到 2027）」（不做清單）。

## 範圍：檔案（最終版，只准改這些）
- `README.md`（只改標題與第一段，見作法 1）
- `docs/adr/0008-web-scope-studios-projects-cloud.md`（只在標題下、既有 `> Point 1 …` 那行之後加一行附註，見作法 2；決策本文不改）
- `docs/ROADMAP.md`（只改第 1、3、4 階段那三列的格子內容，與 Open questions 的 TWCC 一條，見作法 3）
- `specs/readme-adr-roadmap/ledger.md`（新，executor 的進度帳本）

## 作法
1. **README.md**：
   - 第 1 行標題 `# agentic-bioflow v2` 改成 `# agentic-bioflow`。
   - 原第 3 行那句（"Run Nextflow/nf-core pipelines through **Seqera Platform**, from Claude Code."）之前插入新段落（照抄）：
     > Run nf-core pipelines on your own HPC account or cloud, from Claude Desktop or a web page, through a platform you host yourself. Nothing goes through Seqera. The first site is NCHC's nano4; Google Batch, AWS Batch and Azure/Kubernetes follow. This is the `v3` branch.
     >
     > **v2 (the `main` branch)** is the Claude Code plugin that runs pipelines through Seqera Platform. It takes bug fixes until 2027. The rest of this file describes v2 until v3.0.0 is released.
   - 其餘內容一字不動（保住 `Nextflow's own records, the truth under constitution 6.0.0` 與 `Constitution 2.0.0` 兩個被測試釘住的字串）。
2. **ADR 0008 附註**（緊接在第 3 行 `> Point 1 (the page skeleton) is replaced by ADR 0009 (2026-10-17): …` 之後，照抄一行）：
   > Note (2026-10-21, `docs/ROADMAP.md`): cloud compute environments open in the order Google Batch, AWS Batch, Azure/Kubernetes; NCHC's nano4 is the main site; Taiwania 3 takes bug fixes only, until 2027. Nothing in the decision below is withdrawn.
3. **docs/ROADMAP.md**（三列只改格子內文字；列首的編號與粗體名稱不動）：
   - **第 1 列 What changes**：把 `007b is built and waits for its manual acceptance on the real cluster (TC-047 to TC-050 in \`docs/TESTING.md\`).` 改成 `007b is built; its manual acceptance runs on NCHC's nano4 (TC-047n to TC-051n in \`docs/TESTING.md\`, table \`specs/007b-launch/acceptance-nano4.md\`); Taiwania 3 takes bug fixes only, until 2027.`。**`station agent + compute environments (Seqera model, all types; NCHC first)` 這段原樣保留。**
   - **第 1 列 Done when**：`the platform's "list rawdata" and "launch ampliseq" both succeed through it` 改成 `the platform's "list rawdata" and "launch nf-core/ampliseq 2.18.0" on nano4 both succeed through it`；其餘不動。
   - **第 3 列 What changes**：在 `016: Studios (…)` 那句之後、格子結尾之前加一句：`017: a drag-and-drop canvas: nf-core modules as blocks, connect, fill parameters, validate, launch, export a zip, versions and sharing inside the lab; no nested subworkflows (017a–e).`。`014: the platform's chat, connecting to the model the user chooses …` 那句原樣保留（測試釘住）。標題 `| 3 | **Web** (features 011–014, 016)` **不改**（測試釘住；017 寫在內文）。
   - **第 3 列 Done when**：既有文字一字不動（`… finished from the web alone; Two members of the trial lab use it for two weeks with fewer than 10 new PITFALLS; the hosted service goes live (charging waits on the open questions below)` 整串被 TC-020 兩處釘住，中間不能插字），只在格子**最後**、`(charging waits on the open questions below)` 之後加：`; the trial counts as a success when a colleague completes one 16S run without asking the maintainer anything`。
   - **第 4 列 What changes**：刪掉結尾的 `; TWCC first`，換成 `; the order is Google Batch, then AWS Batch, then Azure/Kubernetes. A cloud user installs no station agent: the platform host runs Nextflow and keeps the cloud credential in a file, never in the database`。`merged into Stage 1` 字樣原樣保留（測試釘住）。
   - **Open questions 的 TWCC 那條**（第 116～117 行）：句首加 `(Dropped from Stage 4 on 2026-10-21; kept for the record.) `，其餘不動。
4. **不需要 migration**（純文件）。

## 失敗先行測試
本件只改文件，沒有新的自動測試（不加新的釘字串測試，免得把待他裁決的措辭釘死）。驗收靠：
- 全套 `bash tests/run_all.sh` 綠——特別是下列既有釘子必須仍然通過：`tests/platform_direction_docs_test.sh` 的 TC-022（六個階段列首、014 句、Dropped 句）、4.1.0 TC-018～021 與 W0 TC-014～022（第 3 列：parity 句恰好三次、014 逐字、done-when 兩段逐字、沒有「web page make/draw/plot」）、TC-032、TC-038、TC-059（README 兩個字串）；`platform/tests/test_station_docs.py::test_tc077`（第 1 列開頭與 `NCHC first` 句、第 4 列 `merged into Stage 1`、每列 Done when 非空）；`tests/constitution_6_test.sh`、`tests/constitution_scope_test.sh`（README 的 `Constitution 2.0.0`）；`platform/tests/test_keep_submissions.py::test_tc063`（不碰 `docs/ROADMAP.md:98` 那一列的行號：本件改的三列都在第 98 行之前，**不得增減行數**——三列都是單行表格列，只改列內文字）。
- verifier 逐條比對作法 1～3 的「照抄」文字是否一字不差。

## 允許更新的既有斷言
- 無。任何既有測試變紅＝改錯了，回頭改文件，不改測試。

## 完成標準（done when）
- 全套綠；PR 說明有三處「改前／改後」對照；維護者讀完回好並自己 merge。

## 環境事實
- `docs/ROADMAP.md` 的 Open questions TWCC 那條在第 116～117 行（`origin/v3` @ e079854）；`test_keep_submissions.py:626` 斷言 ledger 文字含 `docs/ROADMAP.md:98`，所以第 98 行以前不能增減行。
- nano4 驗收表：`specs/007b-launch/acceptance-nano4.md`；TESTING.md 的 nano4 步驟編號 TC-047n～051n（#160 已合併）。

## 不做
- 不改憲法、不改 `CLAUDE.md`、不改 `docs/POSITIONING.md`／`docs/SEQERA_PARITY.md`。
- 不改 README 第一段以後的 v2 說明（v3.0.0 發版時另一件整份重寫）。
- 不改版號、不寫 CHANGELOG。
- 不新增 ADR。

## 裁決（2026-10-23，預檢後）
1. 第 4 列「The station agent also runs on a VM the lab rents;」與新句「A cloud user installs no station agent」矛盾（10-21 裁示 13：雲端用戶不裝代理）→ **把這句刪掉**；作法 3 第 4 列的替換文字改成：刪 `The station agent also runs on a VM the lab rents; ` 與結尾 `; TWCC first`，結尾換成 `; the order is Google Batch, then AWS Batch, then Azure/Kubernetes. A cloud user installs no station agent: the platform host runs Nextflow itself, with the cloud account's key in a file on that host and never in the database (an HPC site credential still never reaches the platform)`。`Nextflow's AWS Batch executor; an estimate and cap before anything is billed` 保留。
2. 雲端憑證與 `docs/ROADMAP.md:90`「never holds a site credential」：「site credential」指 HPC 站台登入憑證，雲端帳號金鑰不在此列（裁示 13）；上面括號那句就是為了把兩者分開，第 90 行不改。
3. README 新段之後的舊第 3 行不另加標示（新段已寫「The rest of this file describes v2 until v3.0.0 is released」）。第 3 列標題不含 017 是刻意的（被測試釘住），維持。

## 專長守則（docs）

（工作區沒有 `.claude/dev-profiles/docs.md`；本任務無專長守則。）
