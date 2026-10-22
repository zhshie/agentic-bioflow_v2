# DESIGN.md: agentic-bioflow web (v1, 2026-10-18)

Copy this file to the repo root. The executor builds only what this file decides; anything it does not decide goes to 要問 (`.claude/dev-profiles/ui.md`).
Reference rendering: `abf-demo-v4.html` (generator `build-v4.js`, same folder). Where this file and the demo differ, this file wins.

## Maintainer's words (verbatim, for test cases)
1. 「進來之後馬上可以看到各個run的狀態與進度 (右側會顯示各個run的進度到哪個步驟)，只有需要使用者決定的才會通知使用者。開啟一個專案、上傳rawdata之後，馬上就看到選pipline的階段，系統直接一個個引導使用者。」
2. 「系統設定先。然後右側有對話框，直接對話系統就會引導使用者快速上手建專案，選pipline條參數等等」
3. 「AI一律先除錯，不是使用者能決定的事情一律直接處理」
4. 「同時跑5-10個」
5. 「做成產品英文版面是必須的」
6. 「Seqera功能太多學習成本高」
7. 「在送出的介面就要有之前abf-v2那些引導的事情，包括選擇pipline (之前設定的 or 新開的)、pipline的流程圖、pipline的參數等等。介面上不要有AI太口語化的回覆，要有制式化的通知呈現 ("樣本表少了 reverseReads 欄，AI 改不了。"這種不行)」
8. 「版面我完全不滿意，請你直接參考 Seqera 以及 Galaxy 的網頁」 (011a rejection)
9. 「不需要Jev "開關"，只要在設定讓使用者可以放金鑰。」
10. CLI terminal in the page: cancelled by the maintainer.
11. 「不需要建議分析，下面那兩張圖也完全不需要。只要讓使用者能操作裡面的R，或是透過AI agent及時修蓋程式碼，然後能看得到圖片產生，最後要能夠打包圖片往下一步」 (downstream)

## Skeleton (ADR 0009, amended 2026-10-18)
- **Masthead** 40px, dark (`--ink` bg): product name left; right: cost meter (two lines: NCHC `SU —`, Cloud `NT$ used / cap`, plus a thin bar; links to the cost page), 中｜EN switch, user name.
- **Left column** 272px: "Now" (home, red count of items awaiting the person) → PROJECTS heading, + New, search → per project a section header with a rule on both sides, then "↑ Upload data", then its analyses (status dot + name + current stage, ellipsis on overflow) → bottom: Settings, Data Explorer and Dashboard in grey with "coming later", Log out.
  - No Seqera-style top-level pages: there is no Launchpad, Runs, Datasets or Studios entry. These live inside stages.
- **Middle**: the selected analysis's five-stage bar (launch → running → results → downstream → finished, done ✓ / current / later) with ← → pager; the stage's content below.
- **Right column** 320px (380px when Chat is open): segmented switch "Progress | Chat" (Chat shows a red unread count).
  - Progress = search, "All analyses · yours only", counts row (▶ ⟳ ! ? ✓), groups per stage as collapsible `<details open>`, each item colour-filled by state: `n: name`, symbol right, second line "state · current process step · done/total", thin progress bar. The selected analysis has a focus outline. Failed analyses sit under Running.
  - Chat = the platform chat (person's own key; tool steps and sources shown; AI replies use the formal field layout: 診斷／依據／處置).
- ≤1200px: 232 / fluid / 288. ≤900px: one column, order middle → right → left; masthead hides the cost meter.

## Tokens (only these; `abf-ds/project/tokens.json`, `components/bundle.css`)
Colours (light/dark): surface #f6f5f2/#15171a · surface-raised #ffffff/#1e2125 · surface-sunken #ecebe6/#101214 · ink #1f2328/#e9e7e2 · ink-muted #575e66/#a2a8b0 · line #d6d3cc/#33373d · line-strong #8f8b82/#646a73 · accent #1c5d8a/#7db8e2 · accent-weak #e2edf5/#1a2c3a · focus #1c5d8a/#9cccf0 · status-{running #0b5aa8, succeeded #1b6837, failed #b0261d, lost #865700} each with a -bg tint (dark values in tokens.json).
Type: system sans stack incl. Noto Sans TC / Microsoft JhengHei; mono ui-monospace stack. Sizes used: 22 (h1), 16–15 (h2/h3), 13 (body UI), 12 (meta). Spacing 4/8/12/16/24. Radius 4/6/pill. No external fonts, no CDN.

## States (coloured square + word; colour never carries meaning alone)
A small coloured square (its own element, colour from the status tokens) followed by the word: Running · Pending · Failed · Done; a status outside these four shows a neutral grey square and the word Unknown. No symbol character stands for a state.

## Formal notices (one component everywhere)
Box with: level pill (coloured square + word: Decision needed / Action needed / Handled automatically / Completed), analysis name (mono), time right; one-line title; a definition list of fields (問題／原因／可選動作, or 步驟／處置／你需要做的事); buttons. No chatty sentences, no error codes in titles. No coloured side stripes (Impeccable side-tab).
Only Decision needed and Action needed notify (Now page + red counts). Automatic handling goes to the "Automatic handling log" table on Now and to the analysis's own notices, never as a notification.

## Screens
1. **Now** (default): "Awaiting you (n)" notices, then "Automatic handling log" table (time, analysis, event, action, status). Examples: input incomplete (R2 missing → upload R2 / switch to single-end); needs AI or you (no key, error last 4 lines, buttons add key / resume / start over); confirm before launch; downstream decision.
2. **First use / Setup** (`#setup`): numbered disclosure steps: account ✓, access token ✓, compute environment (required: environment, site agent status, cluster account), AI key + Jev key (optional, browser only), create first project. Right column becomes a step guide (formal fields).
3. **Project with no analysis**: one next step, "Upload raw data"; after upload the launch stage opens.
4. **Upload data**: drop zone (≤ ~2 GB per file; large FASTQ via the AI and `push.sh`; files go through the site agent to the person's own site or cloud storage, platform keeps no copy); Create samplesheet (auto-pair R1/R2, columns from the chosen pipeline's `schema_input.json`, makes a new version); Uploaded data table with version, used by, checksum, updated.
5. **Launch stage**: guided walk of v2's launch skill, numbered disclosures (done ✓ / current outlined / later):
   1 Pre-checks (revision pinned, schema read, registered, samplesheet draft, directives, site connection; notices such as egress host) ·
   2 Pipeline: tabs "Used before" (pipeline, revision, last used by, when; Select; ⚡ Quick launch = all previous settings → confirmation) and "New pipeline (all nf-core)" (search, cards, Verified tag, 16S prefilled) ·
   3 Workflow diagram (from the pipeline's `docs/images/` at that revision, caption names the file) + stage list from the README, skipped stages struck through ·
   4 Samplesheet (column roles, preview, n/n paired) ·
   5 Parameters: three routes ① reuse a previous run (show tuned-on sample count and size vs this run) ② defaults ③ adjust by group; required-without-default warning; every schema group as a disclosure (count + representative names; table name/type/default/this run); "Stages that will run" ·
   6 Compute environment · 7 Confirm.
6. **Confirmation pages** (every write, ADR 0006): launch (pipeline, samplesheet+version, changed parameters, skipped stages, compute, output path on cluster, copy-back path, estimate, new analysis vs attempt), resume, start over, run downstream. Confirm / Back.
7. **Running stage**: title with Resume / Re-run (both → confirmation), four summary cards (current step, duration, compute, cost), Tasks bar + legend, this analysis's notices, tabs Tasks / Logs / Run info / Configuration / Metrics.
8. **Results stage**: summary cards; tabs Report (generated, editable, saved → goes into the package) / Outputs / Reports (MultiQC embedded, JS) / Run info / Tasks / Logs / Metrics; Download all.
9. **Downstream stage** (maintainer 10-18: 「不需要建議分析，下面那兩張圖也完全不需要。只要讓使用者能操作裡面的R，或是透過AI agent及時修蓋程式碼，然後能看得到圖片產生，最後要能夠打包圖片往下一步」): no AI-suggested analyses and no preset figures. Entry: decision notice "Do downstream analysis?" (open → confirmation page "start RStudio and load results", or skip to finished); title row also has "Skip to finished".
   - The full IDE in the middle column: tabs RStudio / Jupyter (iframe of the agent's localhost, "Open in new tab"); third state "On another computer" as an Action-needed notice. The person works in R directly.
   - AI edits: the person asks in the right-column Chat; the AI edits `analysis/downstream.R` and runs it in the IDE console; each change appears as a "Handled automatically" notice under "AI edits" (lines changed, what ran, file produced).
   - "Figures produced": live list of `analysis/figures/` (JS), newest highlighted, each with an "Include in package" checkbox; button "Package the n selected figures, go to Finished"; the script goes into the package too.
   - Positron is not embedded (no free web build; ELv2 hosting clause).
10. **Finished stage**: delivery package (edited report, tables, MultiQC, figures, methods with versions, samplesheet), provenance, Download.
11. **Cost** (`#cost`, from the masthead meter): cards NCHC SU / Cloud used / cap / remaining; "never converted" line; Action-needed notice when a launch would exceed the cloud cap (use NCHC / wait for reset); per-analysis table with status Running / Reconciled / Estimate, bill pending.
12. **Settings**: compute environments, credentials (token, 12 h), Secrets (AI model key, Jev key optional; browser only), Personal (step-by-step mode, development mode); Operator panel and Roles as dashed "coming later".
13. **Sign-in to confirm** (from an MCP client): name, token, remember 12 h → launch summary.

## Constraints
Single stylesheet, no inline style, no external resources. JS only where marked: live updates, client-side pipeline search, chat send/streaming, drag-and-drop upload, MultiQC embed, Studio iframe. Language by `?lang=en` server-side (the demo's CSS radio is only a mock). Owner rule: each person sees only their own analyses. No Galaxy/Seqera logos, names, brand colours or code (ADR 0004).

## Open
- `/impeccable critique` not yet run on v4 (detect: 1 finding, the Progress|Chat switch inset).
- ADR 0009/0010 amendment needed: chat in right column; Data Explorer/Dashboard greyed; Seqera pages folded into stages; downstream = embedded IDE (RStudio/Jupyter only); no Jev switch.
