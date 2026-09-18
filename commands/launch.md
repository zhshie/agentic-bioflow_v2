---
description: Set up and submit one analysis - pipeline, samplesheet, parameters, launch
argument-hint: [pipeline] [path to input data]
---

Paths below such as `scripts/...` and `docs/...` are this plugin's own files,
never the user's working directory. Installed as a plugin they are under
`${CLAUDE_PLUGIN_ROOT}`; read them straight from the repository otherwise.

## Before anything else

Run `. scripts/env.sh && scripts/intro.sh launch` — sourcing `env.sh` first
sets `PATH` and `TOWER_ACCESS_TOKEN` from this deployment's own settings, in
the same call rather than a separate round trip before every later `tw` call
(`scripts/env.sh`'s own header). Put `intro.sh`'s five sections in front of
the user before doing anything below. When the run has been launched and its
watch armed (step 9), run `scripts/intro.sh --end launch`.

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

`scripts/preflight.sh` used to run here on its own. It is now folded into
`scripts/prepare_launch.sh` (step 0 below), which runs it as one of the four
things it merges into a single call - GitHub issue #13's own accounting is
why: each of those used to be a separate tool call, and a separate tool call
is a separate model round trip. Its `== preflight ==` section is exactly
what `preflight.sh` alone used to print.

**Do not build a samplesheet on top of a `BLOCKING:` line from step 0.** The
run gets assembled correctly and then submitted into an environment that
cannot carry it - which is how a dead outputs reader took out a launch once
(`docs/PITFALLS.md`).

The launch gate (`hooks/confirm_launch.sh`) re-checks the two things that can
die while you work. Step 0 is the earlier and wider check: it also covers
`LAB_RUNS_DIR`, the resource contract, and whether the compute environment is
AVAILABLE - none of which the gate can see.

## Steps

0. **Gather the no-judgement parts in one call, then ask everyone what needs a
   person, in one question.** Steps 1, 4, 5 and 6 in an earlier version of
   this file were a long, sequential chain of `tw`/schema/samplesheet/
   preflight calls - each one its own tool call and therefore its own full
   model round trip, 20-40 of them across a whole launch walk (GitHub issue
   #13). `scripts/prepare_launch.sh` runs the parts of that chain which need
   no judgement - revision lookup, a schema fetch, the registration check, a
   samplesheet draft, the directive check, and `preflight.sh` - together, and
   never stops at the first problem: it runs everything and reports every
   blocking and warning-level issue at once.

   **First, a short conversation to name a candidate pipeline** - this part
   cannot be skipped ahead of, because nothing can look up a schema for a
   pipeline nobody has named yet. Start from what this person has already
   run, because the commonest analysis is the last one again with new
   samples:

   ```
   tw runs list      --workspace $(scripts/settings.sh workspace_id)
   tw pipelines list --workspace $(scripts/settings.sh workspace_id)
   ```

   The first gives project name and username per run — filter to this
   member's `seqera_user`, since the site is one shared account and
   everyone's runs are in the same list. The second says which pipelines are
   registered, and at which revision. **Show both and let them choose**: an
   earlier pipeline, or a new one they have not run here. None of this is
   stored — Platform already holds it (`docs/PRINCIPLES.md`, invariant 2).
   Also list existing projects, the same way step 0 of an earlier version of
   this file did, for the question below:

   ```
   ls $(scripts/settings.sh storage_root)/$(scripts/settings.sh seqera_user)/projects/
   ```

   **Then run it once:**

   ```
   scripts/prepare_launch.sh --repo <owner/name> --revision <rev, if pinned> \
       --input <local directory of reads, if reachable from here> \
       --workspace $(scripts/settings.sh workspace_id)
   ```

   **Show its summary to the user exactly as printed** — do not summarise it
   from memory or reformat it; its `== decisions ==` section is what the
   question below is built from. When `--revision` was left out, the
   `== pipeline ==` section names the one it resolved to (the newest tag) and
   flags it as needing confirmation, never launched on silently.

   **Extension point for other branches (read `scripts/prepare_launch.sh`'s
   own header for the full contract):** the summary is an ordered list of
   `== <name> ==` sections and is designed to grow. A site-side run directory
   and local fetch destination land as a new `paths` section; a "this looks
   like it duplicates an in-flight run" hint feeds the same `== decisions ==`
   rollup every other check already writes into.

   **Then put every decision to the user in one `AskUserQuestion` call**,
   covering what three separate steps used to ask one at a time:

   - **Project** — from the listing above: reuse one, or start a new one.
     Do not choose for them, and do not invent a name.
   - **Pipeline and revision** — confirm what was just resolved/looked up, or
     name a different one. A `DECIDE:` line in the summary asking to confirm
     an auto-resolved revision belongs here.
   - **Parameters — which of the three routes (step 5), not the values yet.**
     Someone who has not seen the workflow cannot say which parts of it they
     want to adjust (step 2's own reasoning), and step 2 has not run yet at
     this point - so this asks only which route (① reuse a previous run's
     settings, ② the pipeline's defaults, ③ go through what is adjustable),
     and names anything the summary's `== parameters ==` section already
     flagged (required with no default, a GPU directive) as something route
     ③ - or a direct answer now, if the user would rather settle it here -
     will need to cover. **The detailed values for route ③ are filled in at
     step 5, after step 2's diagram**, never before it.

   "All defaults" and "reuse the previous project" are complete answers; they
   are not answers this step can give on their behalf (the same rule step 5
   states at length below, for the same reason).

   **The run's `--outdir` goes inside the chosen project**, at
   `<project>/runs/<pipeline>_<label>_<YYYYMMDD>/results`:

   ```
   scripts/init_workspace.sh site --user <seqera_user> --project <project> --run <name>
   ```

   A run pointed anywhere else is in no project, and
   `hooks/confirm_walkthrough.sh` refuses it at the point the parameters are
   written rather than after the run has started. Older run areas are flat
   and are **left exactly where they are** — the new shape applies to new
   work, and nothing is moved.

1. **Pipeline and revision — confirmed in step 0.** Pin an exact revision —
   never a branch. If the Seqera Co-Scientist is available it may suggest
   better than you can, but it is optional: proceed on your own knowledge if
   it is not.

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

   **This step's output must be the final text of this turn.** Show the
   diagram URL and the stage list, then end the turn there and wait for the
   user's reply before doing anything else — no tool call in the same turn.
   `hooks/confirm_walkthrough.sh`'s gate (G1) reads only the text an assistant
   turn actually sent; text that is followed by a tool call in that same turn
   may never reach the transcript it reads, and a diagram shown that way has
   been denied as if nobody had shown it (`docs/PITFALLS.md` 33).

3. **Register it, but only if it is not already there at this revision.**
   `tw launch <short-name>` resolves registered pipelines only, so a pipeline
   nobody here has run needs:

   ```
   tw pipelines add --compute-env <ce> --revision <rev> <github-url> \
      --workspace $(scripts/settings.sh workspace_id)
   ```

   **A registration pins a revision.** Step 0's `== pipeline ==` section
   already said whether this one is registered at this revision, so
   re-running the same pipeline at the same revision needs nothing here —
   skip the step and say you skipped it. Wanting a *different* revision is a
   different entry, not an edit to this one.

   **If `tw pipelines add` fails**, this has no branch below it — follow
   `skills/operational/SKILL.md`'s off-design procedure (T2), category
   `pipeline`, command `launch`, step naming this one. Report the error
   plainly, then attempt what a measured cause suggests (a revision that does
   not exist, a compute environment name typed wrong) before falling back to
   asking the user.

4. **Build the samplesheet, starting from step 0's draft.**

   **If the source is a public accession — SRA, ENA, GEO/GSM — rather than
   reads already in hand, this step does not start from `schema_input.json`
   at all.** Run nf-core/fetchngs first, at its own pinned revision, the same
   way any pipeline here is registered and launched (steps 1–3, once, for it):
   it downloads the reads and writes its own samplesheet, already shaped for
   whatever analysis pipeline consumes it next. **That samplesheet is the
   input to this pipeline** — fetchngs already did this step's job on data it
   fetched itself, and building a second samplesheet from the files it wrote
   would be redoing work nf-core already did (`docs/PRINCIPLES.md`, invariant
   1). Once fetchngs SUCCEEDS, come back here with its output samplesheet as
   the `--input` for the pipeline this command was started for, and continue
   below only for data that is not coming from an accession.

   - Step 0's `== samplesheet ==` section already carries a draft — the
     columns read from `assets/schema_input.json` at that revision (never
     hardcoded here) and a row count with sample rows, built the same way
     rnaseq's own `bin/fastq_dir_to_samplesheet.py` or
     `scripts/generate_samplesheet.py --columns <from the schema>` would.
     When it says the draft was skipped (no `--input` given, or the
     directory was not readable from here), build it now with whichever of
     those two the pipeline ships.
   - Columns the filenames cannot tell you — `patient`, `lane`, `condition` —
     **ask the user**. Do not infer them.
   - Keep grouping metadata the pipeline does not accept in a separate
     `sample_info.csv` for downstream work.
   - Register it: `tw datasets add`, then `tw datasets url -n <name>
     --workspace <ws>` for the URL. **`--input` takes that URL, not the local
     samplesheet path** - adding a dataset does not tell you where it went, and
     the launch fails later and elsewhere if you pass the path.

     **If `tw datasets add` fails**, this has no branch below it either —
     follow the same off-design procedure, category `data`, command `launch`,
     step naming this one. The commonest measured cause is a samplesheet that
     does not parse as the format `tw` expects; read the error before
     assuming anything about the pipeline's own schema.

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

5. **Put the parameters to the user as a choice they answer.** Step 0 already
   fetched `nextflow_schema.json` at that revision (its `== parameters ==`
   section) and asked which of the three routes below the user wants; this
   step is where route ③'s actual values get chosen, now that step 2 has
   shown the workflow - and where routes ① and ② get written down. The
   schema is the authority either way: this repo holds no curated list of
   options for any pipeline, and adding one would be the thing v2 exists to
   avoid.

   **Where the `nf-core` CLI is on `PATH`, use it to build route ③'s group
   list** rather than improvising one over the raw schema:

   ```
   nf-core pipelines create-params-file <repo> -r <rev> -o <tmp>/params.yaml --no-prompts
   ```

   It writes a commented YAML covering every group the schema defines, each
   parameter's type/default/description as a comment above it — the tool
   decides the format, the model only fills in values and uncomments what the
   user chose. It is optional, never a dependency: where the CLI is absent
   (nothing here installs it), read `nextflow_schema.json` directly as
   described below instead — both read the same schema, so the group list and
   the required-with-no-default parameters are the same either way. Measured
   working on this deployment's login node: `docs/PITFALLS.md` 29.

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

   Route ③ is where the rest of this step applies. Put the **whole** schema in
   front of the user, not a subset picked for them:

   - **Every group the schema defines**, one line each — the group's title,
     how many parameters it holds, and two or three representative ones by
     name. `nextflow_schema.json`'s own grouping (`definitions` or `$defs`,
     depending on schema draft) is the source — the CLI's generated file's
     `## ===` group headers are the same list, read off the same schema, when
     one was generated — so read it rather than deciding which groups are
     worth mentioning. A `*skipping*` group (19 parameters of it in rnaseq
     3.14.0) and the tool-choice parameters carrying an enum — `aligner`,
     `trimmer`, `pseudo_aligner`, `remove_ribo_rna` there — are groups this
     list includes, not a special case shown instead of it.
   - **Let the user drill into any group** for its full parameter list — name,
     type, default, description — rather than judging in advance which ones
     they would want to see. Someone shown only a summary cannot adjust what
     the summary left out, and knowing what is adjustable is the whole point
     of this route.
   - **Anything the schema marks required with no default**, which fails at
     launch rather than before it — surfaced regardless of which groups they
     chose to open.

   **Once they have answered, show it back**: which stages will actually run
   given what was skipped or swapped, so the consequence of their choices is
   in front of them, not just the raw values, before `params.yaml` is written.

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

   Write `params.yaml` with a comment explaining any non-default choice — the
   CLI's generated file already carries one comment block per parameter, so
   where it exists, edit values into it rather than starting over.

   If the pipeline reads a GTF, confirm that the attribute a parameter names is
   present on the line type that pipeline actually parses - both halves differ
   per pipeline, and the result of getting it wrong is a silently empty column
   rather than an error. `docs/PITFALLS.md` 14 carries the measured table.
   Leave everything else to the pipeline: it already handles missing biotypes
   and small-genome STAR index sizing.

6. **Check for directives that need a human decision — already read in step
   0's `== parameters ==` section.** It already read the pipeline's
   `conf/base.config` and says plainly whether it found an `accelerator` (GPU)
   directive. Resource requests otherwise need no attention — the site
   adapter turns whatever comes out into something the site accepts.
   - `accelerator` / GPU — the GPU path is **not yet verified** anywhere
     here. Say so to the user (T3 request — no command here covers a GPU
     run), and record it: `skills/operational/SKILL.md`'s off-design
     procedure, category `request`, command `launch`, step naming the
     pipeline's GPU directive. Continuing is the user's call, not a silent
     default - it is one of the items step 0's `AskUserQuestion` already put
     to them if the summary flagged it.
   - a request larger than the site offers at all (the adapter's config lists
     what it has)

   **Report which of the two step 0 looked for and what it found**, "neither"
   included. A step whose only visible output is silence when it passes is
   indistinguishable from one that never ran, and this one never ran.

7. **Show the complete command** — every parameter on its own line — and wait
   for an explicit 確認執行. Include `--disable-optimization`.

   **Provenance is on by default.** Before assembling the command, write
   `<run>/provenance.config` into the run directory step 0 already created:

   ```
   plugins { id 'nf-prov@1.7.0' }
   prov {
     enabled = true
     formats {
       wrroc {
         file = '<absolute outdir>/pipeline_info/ro-crate-metadata.json'
         overwrite = true
       }
     }
   }
   ```

   `<absolute outdir>` is this run's own `--outdir`, written out in full, not
   relative — the plugin needs a real path to write to. Pass the file with
   `--config <run>/provenance.config` in the command you show below.

   State these plainly before asking the user to decide anything, all
   measured rather than assumed (`docs/PITFALLS.md` 32):

   - **Needs Nextflow 25.10 or later.** Check this run's Nextflow version
     matches Platform's default before relying on this; if this run pins an
     older `NXF_VER`, say so and drop provenance for this run rather than
     launching a config the plugin cannot satisfy.
   - **It records no checksums, and no file sizes.** Nothing here duplicates
     `scripts/input_checksums.sh` — the crate is evidence of what ran, not
     proof of file integrity.
   - **`agent` and `license` come out null unless configured, and that is the
     default this command uses.** Do not put the user's name or email into
     the config, here or anywhere else — the crate can leave the lab, and
     whatever is in it travels with every copy. Naming an `agent`, an
     `organization`, or a `license` in `prov.formats.wrroc` is the user's own
     choice to make, never a default set on their behalf.
   - **The user may decline provenance for this run.** Ask. A "no" means no
     `provenance.config` and no `--config` for it — nothing else about the
     launch changes.

   If the plugin fails to resolve when the run starts, that has no branch
   here — follow `skills/operational/SKILL.md`'s off-design procedure,
   category `egress`, command `launch`, step naming this one.

   **If another `--config` is already going into this launch, do not pass
   two.** Checked on this login node (`tw launch --help`, tw 0.40.0):
   `--config` takes one file — unlike `--profile` and `--labels`, its help
   text carries no `[,<config>...]` repeat form. What a second `--config` does
   was not tested, so do not find out on a real run. Merge the provenance block into
   whichever file is already going in, rather than passing both.

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

   Add a fourth line for the same reason: whether provenance is on for this
   run, and if not, that the user declined it — a silent default is exactly
   what the facts above exist to prevent.

8. **Launch**, then report the run ID and the Platform URL.

   **If `tw launch` itself fails** — rejected before a run ID ever exists —
   this has no branch here. Say so plainly, then follow
   `skills/operational/SKILL.md`'s off-design procedure (T2), category
   `pipeline`, command `launch`, step naming this one, before attempting a
   fix. Do not relaunch blind: read what `tw` printed first, the same way
   `commands/runs.md`'s SUBMITTED section reads it for a run that reached
   Platform but never reached the queue.

9. **Watch it without asking first.** Arm a background watch on the run's
   status — the harness's `Monitor` where it has one — and report the outcome
   when it lands. Asking permission to watch spends a turn on a question with
   one sensible answer.

   **Poll `scripts/task_health.sh <run-id>`, not just `--status`.** Platform
   reports RUNNING for the entire time one task sits unstarted (runs.md's
   RUNNING section), and a watch that only checks aggregate status is blind
   to exactly that failure mode — it stays quiet through a stuck task and
   only the terminal states ever get reported. `task_health.sh` is the
   `tw runs view tasks` + `why_pending.sh` combination as one command: it
   reports `OK: <n> running, <n> queued` on ordinary progress, or
   `STUCK: <reason>` the moment nothing is running while something queues,
   with the site's own answer already attached. Escalate `STUCK` the same
   way a terminal state would be — the user should not have to ask for a
   debug pass a second run in a row.

   **Watch the outputs reader too, not only the run.** Where the site has one it
   dies on its own — four times in two days here (`docs/PITFALLS.md` 3c) — and
   a run that SUCCEEDS with a dead reader still delivers nothing.

   The watch lives only as long as this conversation, which is the point: no
   daemon and no second copy of run state (`docs/PRINCIPLES.md`, invariant 2).
   What outlives the conversation is the start-of-session check, which asks
   Platform again next time rather than remembering anything.
