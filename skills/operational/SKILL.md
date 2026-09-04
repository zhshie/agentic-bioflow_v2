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

## The three commands

Seqera's own object model, in the order a piece of work moves through it.

| Command | When | Seqera equivalent |
|---|---|---|
| `setup` | First time on this cluster, or when something in the environment broke | compute environments, credentials, Launchpad |
| `launch` | A new analysis, from "I have data" to a submitted run | pipelines → datasets → launch |
| `runs` | Checking on, debugging, or delivering a run | runs |

**The user does not have to name a command.** "I want to run RNA-seq" is a
`launch`; "is it done yet" is a `runs`; "nothing works" is usually `setup`.
Read the command file and follow it rather than improvising the sequence.

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

## The safety net

Never delete a user's source data — not `rawdata/`, `results/`, `analysis/`, a
run area's `_references/`, or a shared image cache. Never delete
`.nextflow/plugins/`. Deleting `work/` or `.nextflow/cache/` needs the user's
explicit confirmation. Show a launch command in full and wait for confirmation
before running it. Credentials and personal details live only in the
deployment's settings area, mode 600 — never printed, never in git, never in a
params file, and never taken from another member's copy.
