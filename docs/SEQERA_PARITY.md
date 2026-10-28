# Seqera Platform parity checklist

What one lab uses from Seqera Platform, item by item, and where this project stands. Compiled
2026-10-08 by the development lead from Seqera's public documentation only (ADR 0004:
development never goes through Seqera's Services); the table first appeared in the maintainer's
direction plan, outside this repository. Stages are those of `docs/ROADMAP.md`.

Count: the original count was 84, but one item of section K was counted and never named, so this
table lists 83 named items: A 16, B 11, C 1, D 5, E 9, F 13, G 2, H 7, I 3, J 9, K 7. No item is
invented to fill the gap.

Verdicts:
- **Have**: agentic-bioflow 2.17.0 already does it (through Seqera or on its own).
- **Build**: the platform direction (ADR 0004) needs it. The four items the direction turned from
  "not needed" into "build" are marked ★: Dashboard, the Launchpad schema form, report rendering,
  and the simplified two-role lab.
- **Not needed**: multi-tenant, cloud-only, SaaS operations, or already given by nf-core.
- **Revisit at Stage 4**: depends on cloud compute.

When an item is built, tick it and name the feature that did it.

## A. Launchpad and pipelines (16 items)

| Item | Verdict | Done |
|---|---|---|
| Add / edit a pipeline | Have | |
| Quick launch | Have | |
| Parameter form from the pipeline schema | Build ★ (web, Stage 3) | [ ] |
| Params file | Have | |
| Labels | Not needed | |
| Resource labels | Not needed (revisit at Stage 4) | |
| Secrets | Have | |
| Resume | Have, with edit | parameters and a restricted resource config can be changed on resume (CLI, MCP); compute-environment switch and web form: not done |
| Relaunch | Have | |
| Advanced launch options | Partly have | |
| Output directory | Have | |
| URL-prefilled launch | Not needed | |
| Revision pinning | Have | |
| Pipeline version drafts | Not needed | |
| Actions (triggers) | Not needed | |
| Git integration | Not needed | |

## B. Runs (11 items)

| Item | Verdict | Done |
|---|---|---|
| Run detail tabs | Have; web version Build (Stage 3) | [ ] |
| Task filtering | Have | |
| Metrics charts | Have (Nextflow report) | |
| Logs | Have | |
| Run control | Have | |
| Cancel | Have | |
| Cost estimate | Build, as NCHC SU and cloud money, never converted (Stage 2–3; ADR 0009) | [ ] |
| Reports | Build ★, rendered (Stage 3) | [ ] |
| Dashboard | Build ★ (Stage 3), as the right pane, not a page (ADR 0009) | [ ] |
| Lineage | Not needed | |
| Notifications | Not needed | |

## C. Datasets (1 item)

Datasets: Have.

## D. Data Explorer (5 items)

Not needed (ADR 0009): upload into the person's own storage plus the run's Outputs view replace it.
NCHC had nothing to register (`docs/SITE_ADAPTER.md`). Bucket browsing is revisited
at Stage 4.

## E. Studios (9 items)

**Build (ADR 0008, 2026-10-17)**: a Studio is the person's own RStudio or Jupyter session on a
compute environment, opened from the browser with a run's outputs mounted; it is the path for
`downstream` without AI. Seqera refuses Studios on a Slurm compute environment (measured,
`docs/SITE_ADAPTER.md`), so where ours runs on NCHC is decided in the Studios feature's plan. RStudio and Jupyter both, on the person's own computer by default, shown inside the web page
(ADR 0009). Until
then the IDE equivalent stays: Have (the user's own IDE). The other Studios items are not counted
individually.

## F. Compute environments (13 items)

One verdict per type (feature 007, slice 1; identifiers and sources in `specs/007-station-agent/research.md`,
`docs/PLATFORM.md` section 8). **Modelled, needs a real account**: the type can be created and its settings
are stored, its status is `unsupported`, nothing runs for it, and connecting it waits for someone with a real
account (opening one and capping its cost is not done by a test). Pre-flight checks: Have, for Slurm; for Google Cloud Batch the station agent on the platform host runs them (create + check + launch + cancel; resume not yet); for AWS Batch the same agent runs them (create + check + launch + cancel; resume not yet); for Azure Batch the same agent runs them (create + check; launch in azure-launch).
The web page lists, creates and edits every type below, cloud types included (ADR 0008); a type
turns supported only after a run on a real account the maintainer opened.

| Item | Verdict | Done |
|---|---|---|
| Slurm (`slurm-platform`) | Have | [x] feature 007 |
| PBS Pro (`altair-platform`) | Modelled, needs a real account | [ ] |
| IBM Spectrum LSF (`lsf-platform`) | Modelled, needs a real account | [ ] |
| Grid Engine (`uge-platform`) | Modelled, needs a real account | [ ] |
| Moab (`moab-platform`) | Modelled, needs a real account | [ ] |
| AWS Batch (`awsbatch-platform`) | Have (create + check + launch + cancel + upload + clean) | [ ] |
| AWS Cloud, one VM (`awscloud-platform`) | Modelled, needs a real account | [ ] |
| Azure Batch (`azbatch-platform`) | Have (create + check); launch in azure-launch | [ ] |
| Azure Cloud, one VM (`azcloud-platform`) | Modelled, needs a real account | [ ] |
| Google Cloud Batch (`googlebatch-platform`) | Have (create + check + launch + cancel; resume not yet) | [ ] |
| Google Cloud, one VM (`googlecloud-platform`) | Modelled, needs a real account | [ ] |
| Kubernetes (`k8s-platform`) | Modelled, needs a real account | [ ] |
| Amazon EKS (`eks-platform`) | Modelled, needs a real account | [ ] |
| Google GKE (`gke-platform`) | Modelled, needs a real account | [ ] |
| Seqera Compute | Not needed: Seqera's own hosted service, no counterpart outside Seqera | |

## G. Credentials and secrets (2 items)

Credentials: Have. Secrets: Have.

## H. Organisations, workspaces, teams, roles, SSO (7 items)

Not needed. The simplified two-role lab (PI / member, ADR 0005): Build ★ (Stage 2), postponed by ADR 0009: v3 has one role. [ ]

## I. Wave and Fusion (3 items)

Not needed (Wave is AGPL-3.0; Fusion needs a Seqera licence even outside Platform).

## J. AI, MCP, CLI, API (9 items)

| Item | Verdict | Done |
|---|---|---|
| Co-Scientist equivalent | Have (the user's own harness); Build: the platform's own chat with the model the user chooses (Stage 3, feature 014) | [ ] |
| Seqera MCP | Build: our own MCP server (Stage 2) | [ ] |
| nf-core pipeline search | Have | |
| SRA / public data | Have | |
| `tw` CLI | Have; without Seqera, the `nextflow` CLI | |
| Platform API, seqerakit, Tower Agent, Connect | Not needed (the station agent is ours, Stage 1) | |

## K. Other (7 named items; 8 in the original count)

| Item | Verdict | Done |
|---|---|---|
| Resource optimisation | Have (to re-evaluate without Seqera) | |
| Audit log | Not needed | |
| Billing | Build, as NCHC SU and cloud money; a monthly cloud cap per person (ADR 0009) | [ ] |
| Notifications | Not needed | |
| Nextflow version selection | Have | |
| Data privacy | Have | |
| Pricing tiers | Not needed (no paywall is a selling point) | |

## L. Launch, live progress and cancel through the station agent (feature 007b, 3 rows; outside the 83 counted above)

| Item | Verdict | Done |
|---|---|---|
| Launch | Have, from the command line only, behind a terminal question (007b); the web form is Stage 3 | [x] 007b |
| Live progress | Partly have: per-process done, running and failed counts and the failed task's name and reason come from Nextflow's own messages (`get_run`) | [x] 007b |
| Cancel | Have, from the command line, behind the same question (007b) | [x] 007b |

Not built yet, and so not in the rows above: the list of every task, CPU and memory per task, logs and reports, and a queued state (a run that is submitted and has sent nothing says only `已送出，尚未收到 Nextflow 事件`; that is a fact, not a state). Also missing: earlier failed attempts of a task that was retried and then succeeded. `get_run` lists only the last attempt, so a retried task never appears in `failed_tasks`, while its failed count still shows it (seen on NCHC 2026-10-15: FASTQC exit 134, retried, succeeded). Seqera lists every attempt.

## M. Items found in Seqera's page map (ADR 0008, 2026-10-17; outside the 83 counted above)

| Item | Verdict | Done |
|---|---|---|
| Projects (pipelines, datasets and runs grouped, with their own runs list and launch) | Build (may map onto the lab's project folders; decided in its feature plan) | [ ] |
| AI agents (Seqera's own agents run as service accounts) | Not needed: the MCP entry and the chat act through the same action layer and gates (ADR 0006) | |
