---
description: Turn a SUCCEEDED run's outputs into figures or further analysis
argument-hint: [run id or path to results]
---

Paths below such as `scripts/...` and `docs/...` are this plugin's own files,
never the user's working directory. Installed as a plugin they are under
`${CLAUDE_PLUGIN_ROOT}`; read them straight from the repository otherwise.

## Before anything else

Run `scripts/intro.sh downstream` and put its five sections in front of the
user before doing anything below. When the accepted analysis has been
recorded (step 6), run `scripts/intro.sh --end downstream`.

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

**Invariant 1 check:** the pipelines already ship their own reports, and on
some, publication-grade figures and an interactive app. **Step 3 lists those
first and nothing already drawn gets drawn again.** What was missing between
"a run finished" and "someone is looking at a figure that answers their
question" was the part no pipeline can supply: which question *this* person
wants answered, from a tree only they can interpret. That is what this adds,
and the code it writes exists only to answer it.

An earlier version of this file delegated the plotting itself to a general
`dataviz` capability the environment was said to provide. Two things were
wrong with that. It is not a file this repository can see, version or test —
so the justification rested on a name that resolves only in some builds. And
its subject is interactive web charts: hover layers, tooltips, dark mode,
filter rows. A static figure at publication resolution is a different craft,
and the parts that do transfer are rules, not machinery:

- one hue, light to dark, for magnitude; two hues with a neutral grey midpoint
  for polarity; **never a rainbow ramp**
- **never two y-axes** — two measures of different scale are two figures
- colours must survive colour-blind vision and greyscale print; identity is
  never carried by colour alone, so a legend and direct labels do the work
- thin marks, recessive axes, labels on the points that matter rather than all
  of them

## Steps

1. **Check the outputs reader is alive** — through the adapter:
   `scripts/on_site.sh --script scripts/agent_ctl.sh online <id>`.
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

2.5. **Ask about the background, before proposing anything.** No field here
   is mandatory — invite the user to describe the study in their own words,
   or hand over papers, prior results, or where this is headed (a
   manuscript, a thesis chapter, an internal report). Whatever they give
   counts, including "nothing" — that is an answer, not a step skipped.

   **Organise and supplement what they hand you; do not just transcribe it.**
   Sort it into research question, experimental design, organism, hypotheses,
   and intended use. Where something is missing, ask about it or mark it
   unknown — never invent it. Where they hand over a paper, **read it**
   before citing anything from it; a title is not a source (`docs/PRINCIPLES.md`,
   invariant 9 applies here just as it does to `finish`).

   Show the organised version back and get their confirmation before writing
   anything down. Then write it into `analysis.md` as a `background` section
   — "the user did not provide one" is a complete entry if that is what
   happened, but the section has to exist and the question has to have been
   put to them in this conversation.

   **Every proposal from step 3 onward cites this section or the inventory
   from step 2** — which one, why, and what the alternative would have been.
   A proposal that cites neither is a guess wearing a recommendation's
   clothes, and the user cannot tell the difference from the outside.

3. **Agree an analysis plan, and write it down.** This is the step the rest
   depends on, and it has two halves.

   **3a. Say what already exists.** The inventory from step 2 lists rendered
   output — reports, figures — by path and size, and some pipelines ship
   publication-grade vector figures ready to use. Put that list in front of
   the user *before* proposing anything. Nothing already drawn should be drawn
   again; that is invariant 1 in its concrete form here.

   **3b. Agree what to compute and what to draw.** Three ways in, and the
   user picks or mixes:

   | | |
   |---|---|
   | **a** | You propose, from the shapes in the inventory and what the experiment is |
   | **b** | The user describes what they want, or hands you a paper whose figures are the model — read it |
   | **c** | Both: your proposal, their corrections |

   Write the agreed result to **`analysis.md`** in the project's `analysis/`
   directory, one entry per item:

   ```
   id            a short name; the script and its output are named after it
   question      what this answers - one sentence, in the experiment's terms
   source        which run, which file, which columns
   method        what to compute or draw
   why           why this and not something else - citing the background
                 section or the inventory, and what the alternative would
                 have been
   status        proposed | accepted | revised | done
   ```

   **`source` names a run and a file; it does not copy them.** Results are
   read-only and re-fetchable, and a second copy inside the project is a
   second thing to drift.

   **This step is gated.** `hooks/confirm_walkthrough.sh` refuses to write any
   analysis or plotting code until `analysis.md` exists beside it *and* a plan
   was put to the user in this conversation *and* they answered. Writing the
   file is not enough on its own — a plan nobody was shown is not a plan
   anybody agreed to, and writing it into a file is the natural move here, so
   that is precisely the hole the gate closes. The user, not you, can stand it
   down by saying 略過計畫.

4. **Write one script per entry, named after its id.** One entry, one script,
   one output — so a revision re-runs one thing rather than everything, and a
   figure can be traced back to the line that asked for it.

   **A statistic that appears in the write-up later must be computed by a
   script here.** Not estimated, not read off a plot, not recalled. If a new
   test is needed it becomes an entry in `analysis.md` and a script like any
   other; that is what makes it checkable afterwards.

5. **Run them one at a time, and say what each one shows.** `Rscript`/`python` is the whole answer
   when all that is wanted is the files. It is not the answer when the person
   is sitting in front of the IDE the script was just written into: a batch run
   cannot put anything in the Plots pane, and step 4's reason for writing to a
   file rather than into the conversation was that their editor can run it
   against a live session.

   `scripts/positron_run.py --lang r --file analysis/<script>.R` runs it in the
   console Positron already has open — plots land in the Plots pane, objects
   stay in the Variables pane, and stdout and any error come back here, so a
   failure is legible rather than something to go and look for.

   **One entry at a time, then stop and describe it.** Say what the figure
   shows **from the data** — which samples, what values, which direction —
   never from the picture: the Plots pane is on the user's screen and not
   yours, and describing an image you cannot see is invention. The user then
   says revise or accept. **Revising means editing the script and running it
   again**, never touching the output by hand.

   **This only works where the IDE is.** Everything the tool uses to reach a
   console is local to the machine it runs on. If this agent is running
   somewhere other than the desktop Positron is open on, there is no route to
   it at all, and no console anyone opens there will change that. `--check`
   says which of those two situations it is in — "no Positron is running on
   this machine" is a different sentence from "no console is open in it", and
   the second one used to be printed for both. Which deployment this is meant
   to be is a setup decision, and `docs/DOWNSTREAM.md` names the two.

   **`--check` is the gate, and it now has an exit code.** Non-zero means the
   step cannot proceed: no console, or no `jupyter_client` for the interpreter
   this runs under. Read what it says instead of retrying — the two causes take
   different actions, and neither is fixed by running the command again.

   **A console has to exist first, and this is a gate, not a warning.** The
   tool attaches to a session and will not start one: a runtime appearing
   unasked in someone's IDE, holding a workspace they did not pick, is a worse
   surprise than being told to open it. So run `--check` before anything else,
   and when it reports nothing, stop and put the instructions in front of the
   person rather than falling back to a batch run and calling the step done —
   the whole reason for being on this path is the Plots pane, and a batch run
   does not reach it. `--wait 120` holds the step open instead of sending them
   away to start over, and continues by itself the moment the console appears.

   Pass the script its own flags after `--args`, last on the line:

       scripts/positron_run.py --lang r --file analysis/<script>.R \
           --args --outdir analysis/figures/run2 --min-depth 5000

   Not optional housekeeping. A live console's `commandArgs(trailingOnly =
   TRUE)` is empty, so without `--args` a script runs on its defaults and
   nothing can change them — and two scripts written into one `analysis/` will
   commonly default to the same `figures/`, where running the second live
   silently destroys the first one's output.

   Do not drive the IDE by sending it keystrokes. It was tried on a real
   machine and it is not merely unreliable: the desktop belongs to the person,
   who moves windows while it runs, so the keystrokes land in whatever is in
   front — twice, in a chat window. No amount of focus checking closes that
   race, because the race is with a human being.

6. **Record what was accepted, in `analysis.md`.** Set each entry's `status`
   as the user settles it. That file is the only record of what this analysis
   was for — the scripts say how, and only it says why — and `finish` reads
   the `question` field to caption the figures. Nothing else is written down:
   run status is Platform's to answer, and a second copy would disagree with
   it (`docs/PRINCIPLES.md`, invariant 2).

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
