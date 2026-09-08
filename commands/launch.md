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

1. **Choose the pipeline and revision.** Discuss the experiment first.

   **Start from what this person has already run**, because the commonest
   analysis is the last one again with new samples, and re-deriving it from
   scratch invites a different revision by accident:

   ```
   tw runs list      --workspace $(scripts/settings.sh workspace_id)
   tw pipelines list --workspace $(scripts/settings.sh workspace_id)
   ```

   The first gives project name and username per run — filter to this member's
   `seqera_user`, since the site is one shared account and everyone's runs are
   in the same list. The second says which are registered, and at which
   revision. **Show both and let them choose**: an earlier pipeline, or a new
   one they have not run here.

   None of this is stored. Platform already holds it, and a second copy would
   disagree with the first eventually (`docs/PRINCIPLES.md`, invariant 2). The
   run directories under the work area are where the *files* are, not the
   record of what ran.

   Pin an exact revision — never a branch. If the Seqera Co-Scientist is
   available it may suggest better than you can, but it is optional: proceed on
   your own knowledge if it is not.

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

   **Every line of this comes out of the repository at that revision** - the
   figure's filename from the `docs/images/` listing, the stages from the
   README's own numbered list. A summary written from memory reads exactly like
   one that was looked up, which is why this step was skipped once with nothing
   to notice: the output looked right. Step 7 asks for the URL and the stage
   list back, so an unread directory shows up there.

3. **Register it, but only if it is not already there at this revision.**
   `tw launch <short-name>` resolves registered pipelines only, so a pipeline
   nobody here has run needs:

   ```
   tw pipelines add --compute-env <ce> --revision <rev> <github-url> \
      --workspace $(scripts/settings.sh workspace_id)
   ```

   **A registration pins a revision.** Step 1's listing already showed which
   entries exist and at which one, so re-running the same pipeline at the same
   revision needs nothing here — skip the step and say you skipped it. Wanting
   a *different* revision is a different entry, not an edit to this one.

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
   - Register it: `tw datasets add`, then `tw datasets url -n <name>
     --workspace <ws>` for the URL. **`--input` takes that URL, not the local
     samplesheet path** - adding a dataset does not tell you where it went, and
     the launch fails later and elsewhere if you pass the path.

   **The reads are on the site; you may not be.** List them with
   `scripts/on_site.sh ls <dir>` rather than reading the directory directly -
   a deployment driven from the user's own machine sees nothing at that path,
   and an empty listing there reads exactly like a directory with no reads in
   it. The paths written *into* the samplesheet are the **site's**, unchanged:
   it is the compute nodes that open those files, not this machine.

   **If the data is not on the site yet, put it there first.** Someone
   analysing their own sequencing has it on the laptop, and no amount of
   samplesheet care fixes a path the compute nodes cannot open. Establish which
   case this is before writing a single row - ask, or list the site directory
   and find nothing:

   - `scripts/push.sh <local-path> <site-path>` moves it and prints the site
     path to write into the samplesheet. Where the deployment already runs on
     the site it prints the path back and copies nothing.
   - Say the size out loud first: it reports one, and uploads are far slower
     than downloads on a home connection. An interrupted transfer resumes, so
     a re-run is cheap; a surprise is not.
   - Put it under the run area (`storage_root`), not a home directory - that is
     where quotas are small and where the compute nodes may not look.

5. **Put the parameters to the user as a choice they answer.**
   Fetch `nextflow_schema.json` at that revision. It is the authority: this
   repo holds no curated list of options for any pipeline, and adding one would
   be the thing v2 exists to avoid.

   **Offer three routes, and let them pick one.** Do not choose on their behalf,
   and do not present only the one you would have chosen:

   | | route | where it comes from |
   |---|---|---|
   | ① | the settings from a previous run | `tw runs view -i <that run> --params --workspace $(scripts/settings.sh workspace_id)` |
   | ② | the pipeline's own defaults | the schema, unchanged |
   | ③ | go through what is adjustable | the groups below |

   For ① also look for a saved resource file under the work area's `tuned/`
   directory, named for this pipeline and revision. **Show the line recording
   what data it was tuned against** — sample count and input size — and let the
   user judge whether this run looks similar. The same numbers on ten times the
   data run out of memory.

   Route ③ is where the rest of this step applies. Put two things in front of
   the user unprompted:
   - **What can be skipped or swapped.** The schema already groups them - a
     `*skipping*` group, 19 parameters of it in rnaseq 3.14.0, plus the
     tool-choice parameters carrying an enum, which there are `aligner`,
     `trimmer`, `pseudo_aligner` and `remove_ribo_rna`. Show each with its
     default, and say that "all defaults" is a complete answer.
   - **Anything the schema marks required with no default**, which fails at
     launch rather than before it.

   **This is a menu the user answers, not a decision to make on their behalf.**
   A gate enforces it: writing `params.yaml` is refused until the schema has
   been read and an answer has come back from them. That gate is not a
   formality — it exists because this step was completed without ever reaching
   a person, and the resulting file was indistinguishable from one they had
   approved.
   The whole reason the step exists is that a pipeline's defaults are chosen
   for a generic dataset and the user's is not. Choosing quietly and writing
   the file produces a `params.yaml` indistinguishable from one they approved -
   which is how this step was satisfied without ever reaching a user. It is
   done when the user has said which, and "all defaults" is a complete answer
   from them; it is not an answer you can give for them.

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

   **Report which of the two you looked for and what you found**, "neither"
   included. A step whose only visible output is silence when it passes is
   indistinguishable from one that never ran, and this one never ran.

7. **Show the complete command** — every parameter on its own line — and wait
   for an explicit 確認執行. Include `--disable-optimization`.

   **Carry the evidence from steps 2, 5 and 6 into this message**, one line
   each, above the command:

   - the workflow figure's URL and the stage list (step 2)
   - what was offered as skippable or swappable, and which the **user** chose
     (step 5)
   - what `conf/base.config` needed a human for, or "nothing" (step 6)

   All three were skipped in a real walk and nothing caught it, because each
   one's output is invisible when it goes missing. Here it is not: this is the
   one message the user must answer, so a line that is absent is absent in
   front of them. Do not reconstruct a line from memory to fill the gap — go
   back and do the step.

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
