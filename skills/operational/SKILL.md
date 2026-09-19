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

**T5: once which command applies is decided, the first action is
`scripts/intro.sh <command>`** (the plugin root's `scripts/`, i.e.
`"${CLAUDE_PLUGIN_ROOT}/scripts/intro.sh"`, the repository root's
otherwise - there is no `scripts/` beside this SKILL.md, and resolving it
from here was the first failed call of the 2.15.0 Windows launch) — put its five sections in front of the user
before doing anything else, exactly what every `commands/*.md` file's own
"Before anything else" section already requires of a typed slash command.
This skill is the *other* door into the same five commands (PRINCIPLES.md,
"the skill is the heart, because it is the only part that works when the
user never types a slash command"), and a door that skips the opening card
is not the same door: `hooks/next_step.sh` treats loading this skill's
sibling for one of the five commands (`agentic-bioflow:launch`,
`agentic-bioflow:runs`, and so on) as opening that command's flow, and this
skill (`agentic-bioflow:operational`) as the router that becomes one of them
the moment `scripts/intro.sh <command>` actually runs - so the call is not
optional framing, it is what tells the rest of this plugin's safety net a
flow is under way at all. When this command's flow ends, run
`scripts/intro.sh --end <command>` the same way a typed command's own file
says to.

**A project is what holds them together.** Raw data, every run made from it,
the analysis written on those runs, and the package built from the analysis all
live under one project directory. The project folder may live wherever the
member already keeps their work - nothing this plugin needs is bound to that
location. `launch` asks which project a run belongs to before starting it, and
a run whose output lands outside one is refused.

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

## More than one at once

Seqera Platform already runs several pipelines in parallel; nothing about the
site or the workspace limits that. What used to bottleneck was the
conversation — one thread felt like it could hold one run, so a member with
several datasets or several kinds of analysis in mind had to pick which to
mention first and lost track of the others.

**When someone mentions more than one dataset, or more than one kind of
analysis, in the same breath** — "run rnaseq on these two batches" or "do QC
then run sarek on the tumour set" — **do not silently queue them up as one
long `launch` conversation.** Route through `/runs` first: with nothing named
it prints the work board (`scripts/runs_board.sh`) of everything already in
flight for this member, each with a short code, before adding to it. Then
walk into `launch` for the next one — one at a time, since `launch` still
ends in a single explicit confirmation per run
(`hooks/confirm_walkthrough.sh`'s G3) - and mention `/runs` again once it is
submitted, so the user always knows how to see everything at once rather than
having to remember each run separately.

Two guardrails ride along on `launch` itself, both their own callable
scripts rather than improvised inline: `scripts/duplicate_run_check.sh`
flags when the project and samplesheet about to be launched already has an
active run behind it; `scripts/parallel_watch_check.sh` (also folded into
the board) warns before one more background watch gets close to
`ssh_max_parallel` — PITFALLS 16e's session cap is a hang, not an error, so
the only real defence is saying something before it happens.

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

## On Windows

The site is reached only through `scripts/on_site.sh`, never by improvising a
connection of your own — on this platform that script borrows the one piece
its own shell is missing (`docs/PRINCIPLES.md`, invariant 11), and nothing
else about where the session is running changes because of it.

Opening that connection is a human turn, not yours: the one-time code lands
on a phone you cannot read, so wait for the user to supply it rather than
retrying it yourself.

Neither this plugin's own files nor the settings file live in the member's
project folder, so the folder may be anywhere — a desktop folder, a folder a
cloud drive syncs — and none of the above depends on which one it is.

## On a host without these hooks

This file reads the same for every runtime that reaches it — a person in
Claude Code, an unattended agent, or a host with no plugin mechanism at all.
What changes is not this text but whether `hooks/` fires alongside it
(`docs/LAB_AGENTS.md`, section 3, tiers H1/H2/H3):

- **H1** — Claude Code with hooks loaded, a person present. Everything above
  applies as written, and the safety net enforces it structurally.
- **H2** — Claude Code headless or the Agent SDK, this plugin's hooks loaded,
  no human turn in the transcript to point to. The same procedures apply, but
  the launch and destructive-delete gates (`hooks/confirm_walkthrough.sh`,
  `hooks/confirm_cleanup.sh`) deny by default rather than trust that someone
  is watching — an unattended run has nothing to offer them as evidence.
- **H3** — a runtime that reaches these files with no hook mechanism to run
  them at all (Claude Tag, Managed Agents, OpenClaw, Hermes, or similar). It
  may read this skill and `docs/` as documentation, and run read-only
  Platform queries — look up a run, read a report. It must not touch the
  site, submit a run, or delete anything. Prose is not a gate on a host with
  no hooks to turn it into one, and the gate meant to replace it -
  `docs/LAB_AGENTS.md` section 3's view-only credential - **is designed but
  not built**. So on such a host this is a rule someone has to keep, and the
  operator's job is not to hand it a deployment's settings file: that file's
  token is the same full-permission one everyone else uses.

`${CLAUDE_PLUGIN_ROOT}` throughout this file means the installed plugin root;
on a host with no plugin mechanism it means the repository root, read
directly — otherwise every path above resolves nowhere.
