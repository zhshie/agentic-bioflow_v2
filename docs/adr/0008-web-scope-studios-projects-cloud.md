# The web pages after the Seqera page map: Studios, Projects and cloud compute environments

Decided by the maintainer on 2026-10-17, after reading the page-by-page list of what a Seqera
Platform user sees (compiled for reference only; ADR 0004's terms note stands: no Seqera code or
page text is copied, only which features exist). It adds to ADR 0006, section "What the web pages
must do without AI"; nothing in ADR 0006 is withdrawn.

## The problem this record answers

ADR 0006 said what the web pages must *complete* (setup → launch → runs → rendered reports → the
package of the pipeline's outputs) but not which pages exist. Seen against Seqera's own menu, five
steps leave out pages a lab uses every day, and one step, `downstream`, had no path at all
without AI: ADR 0006 sent it to the chat or a harness.

The maintainer's words (2026-10-17): 「照你的建議。但Compute env要有其他雲端伺服器，Studio也要，
不然怎麼做downstream這步? Project做，AI agent不做。」

## Decision

1. **The pages.** The web follows Seqera's page skeleton, cut to one lab with two roles:
   Launchpad (pipeline list, schema form, quick launch, relaunch), Runs (filters, star), a run's
   detail (run info with inputs and configuration, tasks, logs, metrics and report, outputs),
   Dashboard (runs per status, date range, NCHC SU), Datasets (samplesheets with versions),
   Data Explorer (files on a site), Credentials, Secrets, Participants (two roles),
   **Compute environments**, **Studios**, **Projects**. The five steps of ADR 0006 stay the
   done-when: each must be completable on these pages without AI.
2. **Compute environments are not NCHC only.** The page lists, creates and edits every type the
   platform models (`docs/SEQERA_PARITY.md` section F), cloud types included. A type becomes
   *supported* only after a run on a real account; opening an account or spending money is the
   maintainer's call each time, never a test's.
3. **Studios: a person's own workspace for `downstream`.** A Studio is an interactive session
   (RStudio or Jupyter) started on a compute environment, opened from the browser, with the run's
   outputs mounted. It is how a person does `downstream` without AI. It is not a canned analysis:
   the person writes the analysis, so principle 6 is untouched. Where a Studio runs on NCHC
   (Seqera itself refuses Studios on a Slurm compute environment, `docs/SITE_ADAPTER.md`) is open:
   an interactive Slurm job reached through the station agent, or a cloud VM; it is decided in the
   Studios feature's own plan, with the site's rules checked first.
4. **Projects.** A project groups pipelines, datasets and runs, has its own runs list and launch.
   It may map onto the lab's existing project folders; the Projects feature's plan decides.
5. **No AI agents page.** Seqera's own AI agents are not built; the MCP entry and the chat
   (ADR 0006) already let a model act, through the same action layer and the same gates.
6. **One action layer still holds.** Every page added here needs its action and MCP tool first
   (ADR 0006 parity rule): compute environment edit, Studio start/stop, project create/list.

## Considered Options

- **Only the five steps as pages**: rejected; it leaves out pages a lab uses (Dashboard, Datasets,
  Data Explorer) and gives `downstream` no path without AI.
- **Seqera's whole menu**: rejected; organisations, teams, SSO, custom roles, billing, Fusion,
  Wave, Lineage, Actions, Labels and managed identities serve many tenants, not one lab.
- **`downstream` in the chat only (ADR 0006)**: kept as one path, no longer the only one.

## Consequences

- `docs/SEQERA_PARITY.md`: section E (Studios) turns from "Not needed" to Build; section F notes
  the web edits every type; a new section M records Projects (Build) and AI agents (Not needed).
- Features 011–013 (the web) grow; Studios and Projects become features of their own, after 009.
- Cloud compute environments and any Studio on a paid service wait for the maintainer to open and
  cap an account.
