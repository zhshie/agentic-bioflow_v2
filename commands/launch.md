---
description: Set up and submit one analysis - pipeline, samplesheet, parameters, launch
argument-hint: [pipeline] [path to input data]
---

Paths below such as `scripts/...` and `docs/...` are this plugin's own files,
never the user's working directory. Installed as a plugin they are under
`${CLAUDE_PLUGIN_ROOT}`; read them straight from the repository otherwise.

Pass the workspace on every `tw` call that is scoped to one:
`--workspace $(scripts/settings.sh workspace_id)`. Left off, `tw` answers from
the caller's personal workspace - where the lab's pipelines, runs and compute
environments do not exist - so `pipelines list` and `runs list` come back empty
and the emptiness reads as an answer. Sourcing a shell env file is not enough:
it carries the token, not the workspace.

Walk the user from "I want to analyse this" to a submitted run, following
Seqera's own sequence: pipeline → dataset → launch.

**This path is the same for every pipeline.** Nothing here is specialised to
rnaseq; the pipeline itself supplies the schema, the samplesheet columns, and
the report list.

## Before anything

`scripts/preflight.sh`. It exits 0 when the site is ready, and prints a FAIL
line naming the script that fixes whatever is not.

**Do not build a samplesheet on top of a FAIL.** The run gets assembled
correctly and then submitted into an environment that cannot carry it - which
is how a dead outputs reader took out a launch once (`docs/PITFALLS.md`).

The launch gate re-checks the two things that can die while you work. This is
the earlier and wider check: it also covers `LAB_RUNS_DIR`, the resource
contract, and whether the compute environment is AVAILABLE - none of which the
gate can see.

## Steps

1. **Choose the pipeline and revision.** Discuss the experiment first. Pin an
   exact revision — never a branch. If the Seqera Co-Scientist is available it
   may suggest better than you can, but it is optional: proceed on your own
   knowledge if it is not.

   With both pinned, `scripts/check_egress.py <repo> <rev>` reads the
   pipeline's own code and reports hosts the site's egress channel would
   refuse. The allowlist is the one thing a new pipeline reliably needs added
   to, and discovering that by watching a run fail costs a queue slot and a
   round of diagnosis. It is heuristic in both directions: it cannot see URLs
   assembled at runtime, and a pipeline only fetches what its parameters
   select, so a host it lists may not be needed. Add the ones that are.

2. **Show what the pipeline does before asking anyone to configure it.**
   Someone who has not seen the workflow cannot say which parts of it they
   want, and will accept every default by default.

   - **The diagram.** List `docs/images/` in the pipeline at that revision,
     pick the workflow figure, and hand the user its raw URL. **Read the
     directory rather than guessing the filename** - the four pipelines run
     here name it four different ways: `nf-core-rnaseq_metro_map_grey.png`,
     `nf-core-differentialabundance_metro_map.png`, `ampliseq_workflow.png`,
     `funcscan_metro_workflow.png`.
   - **The same thing in words.** A terminal renders no image, and that is
     where some of these conversations happen. The README carries a numbered
     list of stages, but the heading above it varies - `## Pipeline summary`
     usually, `## Introduction` in rnaseq 3.14.0 - so read the section rather
     than matching a heading.

   Keep it to what this run will do. The user is choosing, not studying.

3. **Register it** if `tw pipelines list` does not already have it:
   `tw pipelines add --compute-env <ce> --revision <rev> <github-url>`.
   `tw launch <short-name>` only resolves registered pipelines.

4. **Build the samplesheet.**
   - Read `assets/schema_input.json` from the pipeline at that revision to get
     the exact columns and which are required. Do not hardcode them.
   - rnaseq ships `bin/fastq_dir_to_samplesheet.py`; prefer it. No other
     pipeline checked ships an equivalent, so otherwise use
     `scripts/generate_samplesheet.py --columns <from the schema>`.
   - Columns the filenames cannot tell you — `patient`, `lane`, `condition` —
     **ask the user**. Do not infer them.
   - Keep grouping metadata the pipeline does not accept in a separate
     `sample_info.csv` for downstream work.
   - Register it: `tw datasets add`.

5. **Decide parameters, and offer the choices instead of waiting to be asked.**
   Fetch `nextflow_schema.json` at that revision. It is the authority: this
   repo holds no curated list of options for any pipeline, and adding one would
   be the thing v2 exists to avoid.

   Put two things in front of the user unprompted:
   - **What can be skipped or swapped.** The schema already groups them - a
     `*skipping*` group, 19 parameters of it in rnaseq 3.14.0, plus the
     tool-choice parameters carrying an enum, which there are `aligner`,
     `trimmer`, `pseudo_aligner` and `remove_ribo_rna`. Show each with its
     default, and say that "all defaults" is a complete answer.
   - **Anything the schema marks required with no default**, which fails at
     launch rather than before it.

   Write `params.yaml` with a comment explaining any non-default choice.

   If the pipeline reads a GTF, confirm that the attribute a parameter names is
   present on the line type that pipeline actually parses - both halves differ
   per pipeline, and the result of getting it wrong is a silently empty column
   rather than an error. `docs/PITFALLS.md` 14 carries the measured table.
   Leave everything else to the pipeline: it already handles missing biotypes
   and small-genome STAR index sizing.

6. **Check for directives that need a human decision.** Read the pipeline's
   `conf/base.config`. Resource requests need no attention — the site adapter
   turns whatever comes out into something the site accepts. Speak up only for:
   - `accelerator` / GPU — the GPU path is **not yet verified** anywhere here
   - a request larger than the site offers at all (the adapter's config lists
     what it has)

7. **Show the complete command** — every parameter on its own line — and wait
   for an explicit 確認執行. Include `--disable-optimization`.

8. **Launch**, then report the run ID and the Platform URL.

9. **Watch it without asking first.** Arm a background watch on the run's
   status — the harness's `Monitor` where it has one — and report the outcome
   when it lands. Asking permission to watch spends a turn on a question with
   one sensible answer.

   **Watch the outputs reader too, not only the run.** Where the site has one it
   dies on its own — four times in two days here (`docs/PITFALLS.md` 3c) — and
   a run that SUCCEEDS with a dead reader still delivers nothing.

   The watch lives only as long as this conversation, which is the point: no
   daemon and no second copy of run state (`docs/PRINCIPLES.md`, invariant 2).
   What outlives the conversation is the start-of-session check, which asks
   Platform again next time rather than remembering anything.
