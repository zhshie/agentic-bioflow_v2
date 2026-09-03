---
description: Set up and submit one analysis - pipeline, samplesheet, parameters, launch
argument-hint: [pipeline] [path to input data]
---

Paths below such as `scripts/...` and `docs/...` are this plugin's own files,
never the user's working directory. Installed as a plugin they are under
`${CLAUDE_PLUGIN_ROOT}`; read them straight from the repository otherwise.

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

2. **Register it** if `tw pipelines list` does not already have it:
   `tw pipelines add --compute-env <ce> --revision <rev> <github-url>`.
   `tw launch <short-name>` only resolves registered pipelines.

3. **Build the samplesheet.**
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

4. **Decide parameters.** Fetch `nextflow_schema.json` at that revision and work
   through it with the user. Write `params.yaml` with a comment explaining any
   non-default choice.

   If the pipeline takes a `--gtf`, check that whatever `gtf_extra_attributes`
   names actually appears on `exon` lines — the default `gene_name` is absent
   from many RefSeq GTFs and the result is a silently empty column, not an
   error. Leave everything else to the pipeline: it already handles missing
   biotypes and small-genome STAR index sizing (see `docs/PITFALLS.md`).

5. **Check for directives that need a human decision.** Read the pipeline's
   `conf/base.config`. Resource requests need no attention — the site adapter
   turns whatever comes out into something the site accepts. Speak up only for:
   - `accelerator` / GPU — the GPU path is **not yet verified** anywhere here
   - a request larger than the site offers at all (the adapter's config lists
     what it has)

6. **Show the complete command** — every parameter on its own line — and wait
   for an explicit 確認執行. Include `--disable-optimization`.

7. **Launch**, then report the run ID and the Platform URL.
