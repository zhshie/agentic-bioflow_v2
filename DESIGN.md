# DESIGN.md: agentic-bioflow web (v2, 2026-10-23; ADR 0011)

Copy this file to the repo root. The executor builds only what this file decides; anything it does not decide goes to 要問 (`.claude/dev-profiles/ui.md`).
Reference rendering: the Artifact canvas 3B2pu4Fo1GfLPYNqjBRAES, version 16, boards V3-failed, V3-running, V3-terminal, V3-downstream-term (approved 2026-10-23: 「對還行」). Where this file and the drafts differ, this file wins. v1 boards (A/B/C, Now) are history.

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
10. CLI terminal in the page: cancelled by the maintainer (10-18). Superseded by 19.
11. 「不需要建議分析，下面那兩張圖也完全不需要。只要讓使用者能操作裡面的R，或是透過AI agent及時修蓋程式碼，然後能看得到圖片產生，最後要能夠打包圖片往下一步」 (downstream)
12. 「狀態只要running, failed, successed就好，failed下面再去分原因，看是要改參數、重跑、續跑，直接告訴使用者要做甚麼，不是讓他們選。"現在"的這個中間畫面有點多餘」 (10-22)
13. 「我說過不要口語的AI，但你給使用者的按鈕都是"用24G續跑"，哪有一個固定的按鈕會這樣寫?」 (10-23)
14. 「能自動續跑的就續跑，自動處理掉問題。」 (10-23)
15. 「先把功能做起來吧，以後再改美觀」 (10-23)
16. 「處置那邊很奇怪，不需要。我希望一個session處裡一條pipline，出問題非用者決定不可的問題了，ai直接告訴使用者要幹嘛。下載、看結果甚麼的點進去看就好了。」 (10-23)
17. 「為甚麼沒看到之前設計過的，pipline裡面要有的launch, run, result等左右視窗?」 (10-23)
18. 「能再加上AI對電腦的即時指令嗎? (例如terminal?) 執行階段是國網or雲端伺服器的CLI，下游是自己電腦的terminal。」 (10-23)
19. 「是中欄有個可以切換主視窗跟終端機的按鈕。終端機能否直接使用? 我要在AI幫我跑時同時看到終端機的輸入指令變化，但我同時也可以自己打。下游的中欄主視窗是R studio，但切換成終端機就是跑在我的電腦。」 (10-23)
20. 「國網連線斷掉時讓我直接在網頁終端機打密碼和一次性驗證碼（OTP）重新連上」 (10-23)
21. 「直接續跑不用確認」 (10-23, resume after a lost site; at most once per analysis, 「好的」)
22. 「分成四類 改成 跟Seqera platform一樣的模式，不要自己定義」 (10-23 20:15)

## Skeleton (ADR 0009 as amended by ADR 0011)
- **Masthead** 40px, dark (`--ink` bg): product name left; right: cost line (NCHC SU, cloud NT$ used / cap; links to the cost page), 中｜EN, user name.
- **Left column** 272px: analyses grouped by project (project name as a small heading), each row = name + state (symbol + text) on line 1, `stage · detail` on line 2 (e.g. `執行 · 18 / 23`, `執行 · 需上傳 R2`, `下游`); the selected row has the accent background and focus outline; "+ 新分析"; bottom: Settings, Data Explorer and Dashboard in grey "之後開放". No "Now" entry; `/` opens the most recent analysis that needs the person, else the most recent one.
- **Middle** (fluid): title row (name, state pill, `pipeline revision · site · started · last update`); the switch **主視窗 | 終端機 · <site>** (in downstream: **主視窗 · RStudio | 終端機 · 本機**); the five-stage bar (送出 → 執行 → 結果 → 下游 → 完成; done ✓ / current / later); the stage's content (main view) or the terminal.
- **Right column** 360px: **this analysis's conversation** — header "這個分析的對話" + name; formal notices in time order; input "問這個分析…" + 傳送. Nothing about other analyses.
- ≤1200px: 232 / fluid / 300. ≤900px: one column, order middle → right → left.

## Tokens (only these; `abf-ds/project/tokens.json`, `components/bundle.css`)
Colours (light/dark): surface #f6f5f2/#15171a · surface-raised #ffffff/#1e2125 · surface-sunken #ecebe6/#101214 · ink #1f2328/#e9e7e2 · ink-muted #575e66/#a2a8b0 · line #d6d3cc/#33373d · line-strong #8f8b82/#646a73 · accent #1c5d8a/#7db8e2 · accent-weak #e2edf5/#1a2c3a · focus #1c5d8a/#9cccf0 · status-{running #0b5aa8, succeeded #1b6837, failed #b0261d, lost #865700} each with a -bg tint (dark values in tokens.json).
Type: system sans stack incl. Noto Sans TC / Microsoft JhengHei; mono ui-monospace stack. Sizes used: 22 (h1), 16–15 (h2/h3), 13 (body UI), 12 (meta). Spacing 4/8/12/16/24. Radius 4/6/pill. No external fonts, no CDN.

## States
分析狀態＝色塊＋詞，三種；顏色從不單獨表意 (a small coloured square, then the word: 執行中 Running · 完成 Done · 失敗 Failed). Nothing else. A lost run is Failed until resumed; a cancelled run is Failed with reason "cancelled".

## Formal notices (one component, right column only)
Level line (symbol + text, time right): `! 需要你處理` (notifies) · `⟳ 已自動處理` · `✓ 已完成` (never notify). Then a definition list of fixed fields, then at most one button.
- Failure (Seqera model, the run's `failure` field from PR #166): 步驟 (failed task, process name in mono) · 原因 (`failure_reason` as reported, last lines) · 之後 (the action) · one button = `failure.actions[0]` (續跑 Resume, else 重跑 Re-run) → confirmation page. The other action stays in the run's menu.
- Automatic handling: 診斷 / 依據 / 結果 (e.g. nf-core retry with more memory; the one automatic resume after a lost site).
- Downstream: 項目 / 檔案 / 下一步, button 打包 → confirmation page.
Buttons are fixed verbs only (上傳, 續跑, 重跑, 設定, 日誌, 打包, 傳送); numbers, sizes and file names live in fields, never on a button. No chatty sentences, no error codes in titles, no coloured side stripes. There is no "處置" column anywhere.

## Screens
1. **Home**: no separate page (ADR 0011). `/` opens an analysis as in the Skeleton; the left column is the list.
2. **First use / Setup** (`#setup`): numbered disclosure steps: account ✓, access token ✓, compute environment (required: environment, site agent status, cluster account), AI key + Jev key (optional, browser only), create first project. Right column becomes a step guide (formal fields).
3. **Project with no analysis**: one next step, "Upload raw data"; after upload the launch stage opens.
4. **Upload data**: drop zone (≤ ~2 GB per file; large FASTQ via the AI and `push.sh`; files go through the site agent to the person's own site or cloud storage, platform keeps no copy); Create samplesheet (auto-pair R1/R2, columns from the chosen pipeline's `schema_input.json`, makes a new version); Uploaded data table with version, used by, checksum, updated.
5. **Launch stage**: guided walk, six numbered disclosures (done ✓ / current outlined / later); the order is the maintainer's (guided-launch-2d, 10-28): nothing that is not set up is offered, so there is no pre-check step:
   1 Analysis name (the one required box of the step) ·
   2 Compute environment (only environments whose status is `available`, site or cloud alike; with none: "No compute environment is available. Set one up on the settings page first." and a link to `/settings`, and no send button) ·
   3 Pipeline: tabs "Used before" (pipeline, revision, last used by, when; Select; ⚡ Quick launch = all previous settings → confirmation) and "Other nf-core pipelines" (one pipeline box; once the pipeline is loaded a version drop-down appears beside it, newest first, the newest selected; this is the only place the version can be changed); under the pipeline the workflow diagram itself, shown as an image (no link to open, no file line); a pair the chosen environment does not list as registered says so with a link to `/settings` ·
   4 Samplesheet (column roles, preview, n/n paired; with none uploaded: "No samplesheet has been uploaded. Please upload one first." and a link) ·
   5 Parameters: the first line says whether the parameter table was read (✓ / … / ✗ / ○); then ① reuse a previous run ② every schema group as a disclosure (box holds the default) ③ advanced box ·
   6 Confirm (the summary and the one send button).
6. **Confirmation pages** (every write, ADR 0006): launch (pipeline, samplesheet+version, changed parameters, skipped stages, compute, output path on cluster, copy-back path, estimate, new analysis vs attempt), resume, start over, run downstream. Confirm / Back.
7. **Running stage**: four summary cards (current step, done/total with bar, duration, cost); tabs 步驟 / 日誌 / 執行資訊 / 設定檔; the steps table (state, step name + process in mono, attempt). Resume / Re-run in the run's menu (→ confirmation). Notices go to the right column.
   - **Terminal** (switch in the title area): a shell on the station agent's machine reaching the site through the ssh master (ADR 0011). Header: `user@site · path`, "共用：你＋abf", "abf：僅查看". Lines: time, who (`abf $` look-only commands tagged 查看; `你 $` the person), output; Nextflow or platform happenings as yellow "事件" lines (e.g. nf-core retry, a confirmed resume typed in by the station agent). When the master is gone the shell asks for passphrase and OTP; the person types them there.
8. **Results stage**: summary cards; tabs Report (generated, editable, saved → goes into the package) / Outputs / Reports (MultiQC embedded, JS) / Run info / Tasks / Logs / Metrics; Download all.
9. **Downstream stage** (maintainer 10-18: 「不需要建議分析，下面那兩張圖也完全不需要。只要讓使用者能操作裡面的R，或是透過AI agent及時修蓋程式碼，然後能看得到圖片產生，最後要能夠打包圖片往下一步」): no AI-suggested analyses and no preset figures. Entry: decision notice "Do downstream analysis?" (open → confirmation page "start RStudio and load results", or skip to finished); title row also has "Skip to finished".
   - The full IDE in the middle column: tabs RStudio / Jupyter (iframe of the agent's localhost, "Open in new tab"); third state "On another computer" as an Action-needed notice. The person works in R directly.
   - AI edits: the person asks in the right-column conversation; the AI edits and runs the script in RStudio; each change appears as a notice (項目 / 檔案 / 下一步) and as an "事件" line in the terminal.
   - Terminal · 本機: the person's own computer (station agent under WSL); abf only looks there.
   - "Figures produced": live list of `analysis/figures/` (JS), newest highlighted, each with an "Include in package" checkbox; button "Package the n selected figures, go to Finished"; the script goes into the package too.
   - Positron is not embedded (no free web build; ELv2 hosting clause).
10. **Finished stage**: delivery package (edited report, tables, MultiQC, figures, methods with versions, samplesheet), provenance, Download.
11. **Cost** (`#cost`, from the masthead meter): cards NCHC SU / Cloud used / cap / remaining; "never converted" line; Action-needed notice when a launch would exceed the cloud cap (use NCHC / wait for reset); per-analysis table with status Running / Reconciled / Estimate, bill pending.
12. **Settings**: compute environments, credentials (token, 12 h), Secrets (AI model key, Jev key optional; browser only), Personal (step-by-step mode, development mode); Operator panel and Roles as dashed "coming later".
13. **Sign-in to confirm** (from an MCP client): name, token, remember 12 h → launch summary.

## 用字 (wording of the Chinese interface; guided-launch-2b)

The maintainer, 2026-10-27: 「一樣要注意中文的顯示不能口語(e.g. "選用這個樣本", "用過的")」. Every Chinese sentence of the interface is written language (正式書面語): a statement of fact or a plain request, with no spoken particles, no "you did not yet" phrasing and no pointing words that stand for nothing. The English text is the equivalent formal sentence.

Rules: (1) say what the state is ("尚無使用紀錄。", "尚未上傳樣本表，無法啟動分析。"), not what the person has or has not done; (2) name the thing instead of pointing at it ("此管線", "該次分析", "已上傳的檔案"); (3) one verb for one act: 選用 (take a row of a table), 套用 (apply a version), 送出 (submit), 載入 (load); (4) a required field is marked with the red `*` (`<span class="req" title="必填">*</span>`, English title "Required") and the legend "* 必填" above the table; the word 必填 is not repeated as a label.

Banned strings in the Chinese text of a page (a test reads the main column of `/launch` in every state and fails on any of them; the pipeline's own English descriptions are not checked): 用過、選好、寫死、自己填、自己調整、你還沒、還沒有、還不能、這個、這份、這條、這一版、一下、弄、搞、東西、喔、啦、吧、囉、蠻、超.

Other screens (board, run page, settings, /welcome, the left column) are not yet swept; that is the backlog item `web-wording-sweep`. A new page uses this section from the start.

## Constraints
Single stylesheet, no inline style, no external resources, 15-second refresh. JS only where marked: the terminal page (ttyd), the studio iframe, MultiQC embed, chat send, drag-and-drop upload, client-side pipeline search. Language by `?lang=en` server-side; every screen exists in English. Owner rule: each person sees only their own analyses and terminals. No Galaxy/Seqera logos, names, brand colours or code (ADR 0004).

## Open
- The automatic resume and relayed OTP join the constitution (MAJOR) with the PR that builds them and their tests (ADR 0011, "Consequences").
- Cost line in the masthead and the cost card come from v1; not re-confirmed in the 10-23 round.
- Visual polish is postponed (word 15).
