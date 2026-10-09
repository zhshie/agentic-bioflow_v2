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
| Resume | Have | |
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
| Cost estimate | Build, as NCHC SU (Stage 2–3) | [ ] |
| Reports | Build ★, rendered (Stage 3) | [ ] |
| Dashboard | Build ★ (Stage 3) | [ ] |
| Lineage | Not needed | |
| Notifications | Not needed | |

## C. Datasets (1 item)

Datasets: Have.

## D. Data Explorer (5 items)

Not needed: NCHC had nothing to register (`docs/SITE_ADAPTER.md`). Bucket browsing is revisited
at Stage 4.

## E. Studios (9 items)

The IDE equivalent: Have (the user's own IDE). The rest: Not needed (refused on NCHC,
`docs/SITE_ADAPTER.md`).

## F. Compute environments (13 items)

Slurm: Have. Pre-flight checks: Have. The rest: Not needed. AWS Batch and a single rented VM:
Build at Stage 4.

## G. Credentials and secrets (2 items)

Credentials: Have. Secrets: Have.

## H. Organisations, workspaces, teams, roles, SSO (7 items)

Not needed. The simplified two-role lab (PI / member, ADR 0005): Build ★ (Stage 2). [ ]

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
| Billing | Build, as NCHC SU | [ ] |
| Notifications | Not needed | |
| Nextflow version selection | Have | |
| Data privacy | Have | |
| Pricing tiers | Not needed (no paywall is a selling point) | |
