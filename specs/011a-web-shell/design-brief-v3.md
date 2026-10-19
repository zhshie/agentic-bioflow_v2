# 貼給 Claude Design 的提示（2026-10-18 第三版：完整功能）

> 上傳這些檔（都在 `C:\Users\ACER\Desktop\ui-reference\`）：
> 1. `galaxy-layout-src.zip`（Galaxy 官方原始碼的版面部分）
> 2. `seqera-frontend-map-2026-10-16.md`（Seqera 頁面、導覽、分頁清單）
> 3. 你自己截的 Seqera 畫面：Runs 清單、Run 詳情、Launchpad、Launch 表單（要登入才看得到）
> 4. `G:\我的雲端硬碟\謝馬爾\.playwright-mcp\galaxy-home.png`
>
> 功能來源：ADR 0006／0008／0009 與 `memory/handoff/2026-10-17-platform-features-discussion.md` 的結論。

---

I'm attaching the source of Galaxy's UI (Vue components and styles), a feature map of Seqera Platform, and screenshots. **Reproduce their layout and interaction patterns as faithfully as you can**, adapted to the product below. Where Galaxy and Seqera differ, make variant A (Galaxy-like), B (Seqera-like), and C (a hybrid of your choice). Show the whole product, not just a run list.

**The product:** "agentic-bioflow", a lab web app where a student runs bioinformatics pipelines (Nextflow / nf-core) on an HPC cluster, guided by an AI chat. One user = one login; each user sees only their own data.

**Structure (agreed)**
- **Left column:** Projects (a project = one experiment folder). Under each project: an "Upload data" entry and several **Analyses**. An analysis = one thing from picking a pipeline to downloading results; resuming or re-running the same inputs counts as the Nth run of the same analysis; changing samples or parameters starts a new analysis. **Settings at bottom-left:** compute environments, credentials, secrets, personal settings.
- **Center:** a status board for the selected analysis with **five stages**: Launch → Running → Results → Downstream → Finished. User can swipe/click between stages. A **chat box at the bottom** (platform AI chat). By default the board advances on its own and only stops at (1) the submit confirmation and (2) "do you want downstream analysis?"; downstream can be skipped; a setting turns on step-by-step mode.
- **Right column:** progress bars for all analyses, grouped by stage and color-coded by state; top line shows this month's cost. Cost follows the compute environment (HPC service units "SU" and cloud money shown separately; cloud has a per-user monthly cap).

**Screens to design (clickable)**
1. **Launch stage:** list of all nf-core pipelines with search; the 16S pipeline is marked "Verified" and prefilled; samplesheet picker/preview; parameter form generated from the pipeline schema; compute environment picker; **a summary/confirmation page where the human presses Confirm** (every write action needs it); "Quick launch".
2. **Running stage:** live progress, task counts, logs; failed runs are grouped under "Running"; automatic debugging status ("fixing automatically" / "needs your action"); resume vs. re-run from scratch, both available.
3. **Results stage:** Outputs, Reports (e.g. MultiQC), Run Info, Tasks, Logs, Metrics tabs (like Seqera run detail); download.
4. **Downstream stage:** AI-suggested downstream analysis, results figures, and **Studios**: embedded RStudio or Jupyter shown inside the page (runs on the user's own computer, embedded via iframe), with an "Open Studio" launcher.
5. **Finished stage:** delivery package summary and download.
6. **Upload data:** drag-and-drop for small files (up to ~2 GB), samplesheet creation, a list of what is already uploaded (Datasets, with versions).
7. **Chat:** conversation panel with tool-call steps shown, source citations (PubMed, nf-core docs, SRA), and where the user supplies their own model API key.
8. **Settings:** compute environments (HPC site, cloud), credentials, secrets, personal settings, step-by-step mode, development mode toggle.
9. **Empty states:** a new user with no project, a project with no analysis; each with one clear next step.
10. **Confirmation page** reached by login (name + personal access token, remembered 12 hours).

**Not in the first release (show as greyed "coming later", never hide):** admin/operator panel, multiple roles (teacher/student), Data Explorer, standalone Dashboard page.

**Constraints for the final HTML (I'll reconcile them later; design freely first, but tell me where you used JS)**
- Prefer plain HTML + one CSS file, no external fonts or CDN, no inline styles. Where JavaScript is really needed (chat, live updates, Studio embed), mark it so I can decide.
- Don't use Galaxy's or Seqera's logos, names or brand colors.

**What I dislike in the current version:** a three-column read-only layout with progress bars felt empty and unclear about what to look at first. The first screen must answer "what is running right now, did anything fail, and what do I do next?" at a glance.
