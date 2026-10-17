# The web as three panes around a project's analyses, one role for everyone

Decided by the maintainer on 2026-10-17, in a design interview held by the development lead
after ADR 0008 was merged. It replaces point 1 of ADR 0008 (the page skeleton copied from
Seqera's menu) and postpones ADR 0005 (two roles). Everything else in ADR 0006 and ADR 0008
stands. Only the web's shape is decided here; the platform chat's tool list, the operator's
administration, Studios on NCHC and the numbers of any cloud cap are left to the next round.

## The problem this record answers

ADR 0008 listed the web's pages after Seqera's menu: Launchpad, Runs, run detail, Dashboard,
Datasets, Data Explorer, Credentials, Secrets, Participants, Compute environments, Studios,
Projects. That is a list of places to go. A student running one 16S experiment asks another
question: where is my analysis now, and what do I do next? Seqera answers it across four pages
(Launchpad, Runs, the run's Outputs, Studios); a click-only user has to know the order.

The maintainer's words (2026-10-17):
- 「我希望面板像claude code app一樣，左側是不同project (folder)，下面是data upload (Datasets or
  Data Explorer)與每次新開的數個"對話"(也就是一次run)，中間是狀態版，顯示目前這一個run是在
  launch (Launchpad), running (Runs), results, downstream (R studio, Jupyter), finished (data
  download)的哪個階段，有左右箭頭可以切換狀態檢視。右邊顯示所有run的進度條，按照不同階段做分類。
  Compute environment, Credentials／Secrets等等全都挪到設定 (可以像claude code app連同個人設定放在左下角)」
- 「統一都不要分角色，每個使用者都統一功能，分角色這些以後再做」
- 「Data Explorer不太需要，只要使用者把自己本機的資料上傳」
- 「Cost estimate, Billing／Credits／Quotas不會只有國網的花費啊? 一般的雲端運算平台呢?」
- 「lauch裡面就是nf-core裡面的pipline都可以跑」

## Decision

1. **Three panes, like the Claude Code app.**
   - **Left**: the person's projects (a project is the project folder the plugin already uses:
     raw data, runs, analysis, package; how work is split into projects is the person's choice,
     and one project may hold more than one experiment spec). Under each project: *upload data*
     and its **analyses**. Bottom-left: **settings** (compute environments, credentials,
     secrets, personal settings, the Jev switch of ADR 0007, step-by-step mode).
   - **Middle**: the selected analysis's **stage board**, five stages: launch → running →
     results → downstream → finished. Arrows move the view between stages. A chat box sits at
     the bottom; a person who does not want AI never has to type in it.
   - **Right**: progress bars of every analysis in all of the person's projects, grouped by
     stage, coloured by state (queued, running, succeeded, failed, paused, after Galaxy's
     history). The colours are read from the run index; nothing is stored a second time. Its
     top line is this month's cost, NCHC SU and cloud money on separate lines, never converted
     into each other; clicking it opens the detail. There is no separate Dashboard page.
2. **An analysis** is one piece of work from launch to download. It holds its chat and every run
   made for it: a resume or a relaunch with the same inputs is attempt 2, 3… of the same
   analysis; changing the samples or the parameters starts a new analysis.
3. **The board moves by itself** and stops in two places only: the launch confirmation (ADR 0006's
   gate) and whether to do downstream. Downstream may be skipped: results can go straight to
   finished. Step-by-step mode, in settings, stops at every stage instead.
4. **Each stage**:
   - *launch*: every nf-core pipeline, searchable, recently used first; the 16S pipeline is
     marked verified and comes with its parameters filled in. There is no separate curated list.
   - *running*: a failure shows one plain sentence of cause and two buttons, resume and start
     over. Debugging runs by itself and stops only where the person must act (the 🤖 / ⏸ split
     of `skills/runs/SKILL.md`). With no AI key, the rule-based fixes still run (exit 137 →
     a larger box and resume); anything else shows "needs AI or you" with the error's last lines.
   - *results*: a report made for every run (with the pipeline's MultiQC report), editable, and
     put into the package at *finished*.
   - *downstream*: a Studio, RStudio and Jupyter both. By default it runs on the person's own
     computer, the one running the station agent, and its screen is shown inside the web page.
     When that computer is off the page says so; a menu offers the person's other compute
     environments (NCHC only once its rules are checked; cloud under the monthly cap).
   - *finished*: download the package.
5. **No Data Explorer.** *Upload data* sends files through the station agent into the person's own
   site or cloud storage; the platform keeps no copy (ADR 0004, "data stays local"). The web
   takes small files only, about 2 GB at most; large FASTQ goes from the person's machine through
   the AI and `scripts/push.sh`. Outputs are read in the run's Outputs view; on cloud a link opens
   the provider's own storage page. Datasets record paths and checksums only; a samplesheet is
   stored whole per version and each run records the version it used.
6. **Cost follows the compute environment.** Each run shows one cost in its environment's unit.
   Cloud shows an estimate when the run ends and the billed amount, marked reconciled, once the
   provider's bill arrives. Each person has a monthly cloud cap that stops new runs; its number is
   set when a cloud account is opened. Development mode puts no cap on NCHC SU.
7. **One role.** Every user has the same features and sees only their own runs. ADR 0005's PI and
   member roles, and sharing between users, are postponed, not withdrawn.
8. **First use** has a guided setup on the web (account, token, compute environment), so ADR 0006's
   "setup without AI" holds.
9. **v3.0.0 includes the web**, Studios included, not only the confirmation page and login.

## Considered Options

- **Seqera's page list (ADR 0008, point 1)**: replaced; it shows places, not where one analysis is.
- **One page per stage with a top menu**: rejected by the maintainer in favour of the Claude Code
  app's layout.
- **Data Explorer as a file browser**: rejected; upload plus the Outputs view cover a lab, and
  no NCHC web page for browsing files was found to link to.
- **A Dashboard page**: rejected; the right pane already groups every analysis by state.
- **A curated pipeline list first**: rejected; every nf-core pipeline is listed, 16S is marked.
- **Two roles in v3.0.0 (ADR 0005)**: postponed.
- **Studios on a cloud VM by default**: rejected; it costs money and needs an account.

## Consequences

- ADR 0008 point 1 and ADR 0005 carry a line pointing here.
- `docs/SEQERA_PARITY.md`: Dashboard is the right pane; Data Explorer is not needed; cost and
  billing count cloud money too; Studios are RStudio and Jupyter on the person's computer first;
  the two-role lab is postponed.
- `CONTEXT.md` gains *Analysis* and *Project*.
- `docs/ROADMAP.md` still words Stage 2 and 3 with a dashboard page, the two-role lab (010) and
  "the PI sees it on the web"; tests pin those rows. Rewording them, with their tests, is a
  separate change for the maintainer to approve.
- Studios move into v3.0.0, so the Studios feature comes before the release, not after it.
