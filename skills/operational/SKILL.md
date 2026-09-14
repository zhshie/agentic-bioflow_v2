---
name: agentic-bioflow-operational
description: How to run a Nextflow/nf-core pipeline through Seqera Platform on a firewalled HPC cluster. Use when the user wants to analyse sequencing data (RNA-seq, amplicon/16S, metagenomics, assembly, variant calling, differential expression), mentions nf-core, Nextflow, Seqera, tw, FASTQ, a samplesheet, GEO/SRA, or asks why a run failed, stalled, or shows no output. Covers which command to reach for, where the truth about a run lives, and where to look first when something breaks.
---

# Running pipelines through Seqera Platform

Identity-neutral: this defines *how the work is done*. Persona, language and
lab-specific norms come from the deployment's own CLAUDE.md, not from here.

**Read `docs/PRINCIPLES.md` before changing anything structural.** It records
what decides — most importantly that we build only what neither Seqera nor
nf-core already does. `docs/PITFALLS.md` records what has already gone wrong;
consult it when something breaks, not preemptively.

When installed as a plugin these are under `${CLAUDE_PLUGIN_ROOT}`; read them
straight from the repository otherwise.

## The five commands

Seqera's own object model, in the order a piece of work moves through it —
plus two that sit outside that model on purpose, covering what happens after a
run finishes.

| Command | When | Seqera equivalent |
|---|---|---|
| `setup` | First time on this cluster, or when something in the environment broke | compute environments, credentials, Launchpad |
| `launch` | A new analysis, from "I have data" to a submitted run | pipelines → datasets → launch |
| `runs` | Checking on, debugging, or delivering a run | runs |
| `downstream` | Turning a SUCCEEDED run's outputs into figures or further analysis | outside Seqera's model — inventories the results tree, agrees an analysis plan, and runs it in a live console |
| `finish` | Turning accepted figures into a package that can be submitted or sent | outside Seqera's model — assembles methods, citations and provenance from what the runs already recorded |

**The user does not have to name a command.** "I want to run RNA-seq" is a
`launch`; "is it done yet" is a `runs`; "nothing works" is usually `setup`;
"make me a plot of this" is a `downstream`; "write this up" or "package this
for submission" is a `finish`. Read the command file and follow it rather than
improvising the sequence.

**A project is what holds them together.** Raw data, every run made from it,
the analysis written on those runs, and the package built from the analysis all
live under one project directory. `launch` asks which project a run belongs to
before starting it, and a run whose output lands outside one is refused.

## Which pipeline

**Any nf-core pipeline works without configuration.** There is no list of
supported pipelines to check and no per-pipeline file to add — the resource
mapping keys off the composed request rather than label names, samplesheet
columns come from the pipeline's `assets/schema_input.json`, parameters and the
skippable steps from its `nextflow_schema.json`, and the workflow diagram from
its `docs/images/`. Everything a user is shown or asked comes from the pipeline
at the pinned revision, which is why none of it goes stale. Pin an exact
revision, never a branch.

Note that `fetchngs` fetches data rather than analysing it. Do not offer it
alongside analyses; it belongs in the conversation about where the raw data is
coming from.

## Where the truth is

Getting this wrong produces confident wrong answers, so it is worth stating.

| Question | Authority |
|---|---|
| Is the run alive, and what stage is it at | **Seqera Platform.** Never a local file — we keep no copy of run state |
| Why is a task not starting | The site's scheduler, via the site adapter. Platform reports the run as RUNNING throughout |
| What did the run produce | **The filesystem.** Platform serves reports through an agent, and binary files arrive corrupt (PITFALLS 3b) — read images and other binaries from disk |
| Which resources a task may ask for | The site adapter, not the pipeline's labels |

## When something breaks

Work outward from the layer most likely to be lying to you.

1. **Is the environment actually up?** If the Platform-side agent is offline,
   every output looks like it was never produced. Never tell the user an output
   is missing without checking this first.
2. **Did something get blocked on the way out?** On a site with restricted
   egress the error that reaches Platform routinely points somewhere else
   entirely — a blocked plugin registry surfaces as a Java formatting
   exception. Check the site's egress log before reading the Nextflow log.
3. **Is a task sitting unstarted?** Ask the site adapter's scheduler why. A
   request below a partition's floor never schedules and never errors.
4. **Only then** read the failing task's own `.command.err` and `.command.log`.

## Off-design: when nothing here covers it

This project is built to a fixed design, not improvised per session
(`docs/PRINCIPLES.md`, invariant 10) — but a firewalled cluster, a shared
Seqera workspace and every OS a member might carry a laptop in produce
situations this design did not anticipate. There are three:

| | Trigger | Decided by |
|---|---|---|
| **T1 environment** | A cell in `docs/CONDITIONS.md` / `scripts/detect_conditions.sh` is not "supported" | The script measures it — never guessed |
| **T2 failure** | A script's failure or output has no branch in the command file you are following | You. Every command file's catch-all now points here instead of saying "diagnose it fully" |
| **T3 request** | What the user wants has no command for it at all — a non-nf-core pipeline, Snakemake, a GPU run | You, from the request itself |

**One procedure, run every time, in this order:**

1. **Tell the user.** One sentence: "this is outside what the plugin has
   designed for so far: `<category>`. I will try to handle it, and record it
   for the maintainer." Do not present this as a dead end — the next step is
   to keep going, not to stop.

2. **Record it.**

   ```
   scripts/report.sh add --category <env|egress|scheduler|pipeline|data|request|host> \
                          --command <setup|launch|runs|downstream|finish|none> \
                          --step <short-slug> [--script <name>] [--exit <n>] \
                          [--outcome resolved|workaround|unresolved]
   ```

   `report.sh` fills in the plugin version, OS, reach, matrix cell/tier and
   Claude interface itself — nothing here is typed by hand, and nothing here
   is a path, a hostname, or anything else that could identify the user or
   their data. Every field is checked against an enum or a short-slug
   pattern; an invalid value is refused rather than queued
   (`tests/report_test.sh`). Run it once you know the category, even before
   you know the outcome — `add` prints the rest of this procedure back to
   you, so it still reaches you if this file was never loaded this turn.

3. **Attempt it, inside the safety net.** Diagnose and fix like any other
   step in this deployment: read logs, try the site adapter, propose a
   change. What does not change: submitting a run and any destructive delete
   still need the user's explicit confirmation, and **this plugin's own
   files are off limits** — `hooks/guard_plugin_files.sh` refuses a write
   under the plugin root regardless of who is asking. When the attempt
   settles, add `--outcome resolved`, `workaround`, or `unresolved` to the
   report above (a second `report.sh add` with the same `--step` is fine —
   send later dedupes by content, not by call count).

4. **Send, at the end of the task.**

   ```
   scripts/report.sh send [--yes]
   ```

   Without `--yes` it only shows every field of everything queued — nothing
   goes anywhere until the user says so. With `--yes` it checks who is
   asking (`gh api user`, three-second budget):

   - **This is the maintainer's own login.** Nothing is sent. Say so, and
     that the right move is designing this into the plugin directly rather
     than filing it as an issue — same as any other change here, through
     `docs/PRINCIPLES.md` and the usual tests.
   - **Someone else, with `gh` available.** It searches open issues labelled
     `off-design` for this report's signature (category + command + step +
     script + exit, hashed). A match gets a comment, not a new issue; no
     match gets a new one, labelled `off-design`, in `zhshie/agentic-bioflow_v2`.
     Sent reports are removed from the local queue.
   - **No `gh`, not logged in, or the identity check timed out.** It prints
     a prefilled `github.com/.../issues/new?...&labels=off-design` link
     instead of sending anything, and the report stays queued locally.
     `scripts/session_start.sh` reminds the user at the next session start
     that reports are still waiting, so this is never a dead end either —
     just one more step for whoever has a GitHub login.

**Upstream pipeline problems are not this repo's to report.** A stale
`tower.yml` or a pipeline bug belongs to the pipeline's own repository —
tell the user that plainly (`commands/runs.md`'s SUCCEEDED section has the
worked example) and stop; do not route it through `report.sh`.

## The safety net

Never delete a user's source data — not `rawdata/`, `results/`, `analysis/`, a
run area's `_references/`, or a shared image cache. Never delete
`.nextflow/plugins/`. Deleting `work/` or `.nextflow/cache/` needs the user's
explicit confirmation. Show a launch command in full and wait for confirmation
before running it. Credentials and personal details live only in the
deployment's settings area, mode 600 — never printed, never in git, never in a
params file, and never taken from another member's copy.
