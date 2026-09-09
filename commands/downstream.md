---
description: Turn a SUCCEEDED run's outputs into figures or further analysis
argument-hint: [run id or path to results]
---

Paths below such as `scripts/...` and `docs/...` are this plugin's own files,
never the user's working directory. Installed as a plugin they are under
`${CLAUDE_PLUGIN_ROOT}`; read them straight from the repository otherwise.

This picks up where `runs` leaves off — after a run SUCCEEDED and its outputs
have been delivered, not before. It carries **no pipeline-specific
knowledge**: no tool names, no output filenames, no per-pipeline table
(`tests/no_per_pipeline_config.sh` checks that this stays true). An earlier
plan said flatly that a fourth command must not exist, because v1 died of
exactly the file this would become — a table of "this tool writes this
report" that goes stale on the next upstream release and leaves an uncatalogued
pipeline unusable. The guardrail is what makes writing it anyway safe: this
command learns the way `launch.md` already does, by reading the artifact in
front of it rather than a copy of it. `launch.md` reads a pipeline's own
`assets/schema_input.json` and `nextflow_schema.json`; this reads the results
tree through `scripts/inventory_outputs.py`, which reports each structured
file's shape with no idea which pipeline made it.

**Invariant 1 check:** this command writes no plotting code of its own. The
environment already provides a general `dataviz` skill, and nf-core pipelines
already ship their own reports and, on some, a shinyngs app. What was missing
between "a run finished" and "someone is looking at a figure that answers
their question" was only the hand-off — knowing what the tree holds and in
what shape — and that is all this adds.

## Steps

1. **Check the outputs reader is alive.** `scripts/agent_ctl.sh online <id>`.
   When it is down, every output looks like it was never produced. This is
   the same check `runs.md` makes before delivering anything, repeated here
   because time may have passed since then.

2. **Inventory the results tree.** `scripts/inventory_outputs.py
   <results-dir>`. It reports each structured file's real shape — delimiter,
   column names and row count for a table; top-level keys for JSON or YAML —
   read from the bytes on disk, never from a remembered list of what some tool
   is supposed to write. Pass `--json` when the next step needs to consume the
   report rather than a person reading it. `docs/DOWNSTREAM.md` carries worked
   examples of what this turns up, measured from a real run — read them for a
   sense of what to expect, never as a substitute for running the inventory
   itself.

3. **Ask what question the figures should answer.** The inventory says what
   exists; it says nothing about what the person actually wants shown. Put the
   shapes in front of them and ask — the way `launch.md` step 5 puts a
   pipeline's own parameters in front of the user rather than choosing quietly
   on their behalf.

4. **Hand the inventory to the environment's own `dataviz` skill.** Give it
   the inventory from step 2 and the question from step 3; it writes R or
   Python into `analysis/`. This command does not choose a plotting library or
   write the code itself — that is exactly what the invariant 1 check above
   rules out here, and the skill already does it well.

   Note where an IDE fits: with an agent extension installed, the person's
   editor shows the file changing as it is written and can run it line by
   line against a live session. That is the actual reason the code lands in a
   file under `analysis/` rather than being printed into the conversation.

5. **Run it, and show the figures.**

## Where does the work happen?

- **Default: bring the results back, and plot where the person already is.**
  `scripts/fetch.sh` brings `results/` back, and `analysis/` lives there too —
  because that is where interactive editing happens, and one home beats two
  that drift. Measured on a real run: a normalised count matrix is 973 KB and
  a whole delivery directory is about 25 MB. Nothing is gained by keeping a
  plotting session on the cluster for that.

- **Exception: outputs over `scripts/fetch.sh`'s 500 MB limit.** Then nothing
  moves the other way — the analysis scripts travel to the site via
  `scripts/on_site.sh` instead, and only the finished figures come back.
  **Measured 2026-09-09.** The claim this replaces — that nothing produced
  here had yet been large enough to reach this path — was already false when it
  was written: `rnaseq_sclerotia_d0_20260903/results` is 10.2 GB and
  `rnaseq_sclerotia_d5_20260902/results` is 8.9 GB, both twenty times the
  limit. Nobody had run `du` on them. Marking a path untested is only honest
  while the reason given for not testing it is true, and "no input exists" is a
  claim about the filesystem that takes one command to check.

  Walked end to end against the 10.2 GB tree: `fetch.sh` sized it at 10918 MB
  from the site and refused, `on_site.sh --script inventory_outputs.py` shipped
  this plugin to the site, ran the inventory there, and returned 872 files
  described in text. Nothing moved but the report.

  Two things that walk turned up. `fetch.sh`'s refusal named only `--max-mb`,
  the override that pulls the whole 10.9 GB over a home connection — the exact
  outcome its own header explains the size check exists to prevent. It now
  names this path first. And the command it names had to be written as
  `--script`: `on_site.sh` ships this plugin's own scripts by that flag, and a
  bare path would look for one on the site that is not there.
