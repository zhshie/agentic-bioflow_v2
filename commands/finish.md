---
description: Assemble a project into a package that can be submitted or sent to a collaborator
argument-hint: [project name or path]
---

Paths below such as `scripts/...` and `docs/...` are this plugin's own files,
never the user's working directory. Installed as a plugin they are under
`${CLAUDE_PLUGIN_ROOT}`; read them straight from the repository otherwise.

This picks up where `downstream` leaves off — after figures exist and the user
has accepted them, not before. It assembles; it does not compose. Every
sentence it produces traces to a file, and where no file can be found the gap
is written into the document rather than smoothed over.

**Invariant 1 check:** the pipelines already write a methods paragraph, and it
already carries their own citation, the workflow framework's, and the
container projects'. That paragraph is not ours to write and this does not
write one. What they leave for the author is a slot for the per-tool
citations — which renders empty, so the tools that did the work go uncited in
a section that otherwise reads as finished. Their own template says as much in
a footnote. **Filling that slot is what this adds**, together with the two
things no upstream project can supply: why the parameters have the values they
have, and what question each figure was drawn to answer.

**Scope:** Methods and Results. There is no Introduction and no Discussion —
those are the authors' scientific judgement and this has no basis for either.
The Discussion heading is left in place with a comment saying so.

## The three rules that decide what may be written

These are not style. Each one is a way this can produce something false.

1. **A citation comes from the run's own files, from a DOI the user supplied,
   or from a page actually fetched — never from memory.** A recalled reference
   may not exist, and a fabricated one is worse than a missing one because
   missing is visible. `scripts/cite.sh` resolves every DOI over the network
   and leaves anything unresolved marked in the bibliography.

2. **Every number traces to a file, and every new statistic to a script.** Not
   estimated, not read off a figure, not recalled. If the write-up needs a test
   nobody has run, it becomes an entry in the plan and a script under
   `analysis/`, and only then a sentence.

3. **A gap is written down.** A tool that cannot be matched to a citation, a
   planned figure that was never produced, a figure no entry claims — all of
   them appear in the output. A document that quietly omits something looks
   finished.

## Steps

1. **Take stock before assembling anything.** Read the project's `analysis.md`
   and list which entries the user accepted. Run
   `scripts/collect_provenance.py <each run's results directory>` and read what
   it found — versions, parameters, and its notes. **Say the notes out loud**:
   they carry things a reader of the finished package would want to know, such
   as a run having been retried.

2. **Assemble.** `scripts/build_package.sh <project-dir>` writes
   `submission/`: provenance, the methods section, the bibliography, the
   manuscript, the figures, and the code that made them. It is idempotent —
   run it again after any change.

3. **Read what it produced, and report every gap it recorded.** Search the
   output for the citation markers and for the comments about figures that do
   not line up with the plan. Put that list in front of the user as a list of
   decisions they have to make, not as a warning at the end of a wall of text.
   A near-miss citation is theirs to confirm: the tool that ran and the entry
   the pipeline lists may or may not be the same thing, and guessing wrong
   cites the wrong paper.

4. **Write the Results prose.** One section per accepted entry, using the
   question that entry says it answers. State what the data shows — which
   samples, which direction, how large — with each number's source at hand.
   Statistical statements are allowed and rule 2 governs them.

5. **Put the plan for the package in front of the user before rendering.**
   What it contains, what is still marked as a gap, and what rendering will
   produce. Wait for them.

6. **Render, where that is possible.** `scripts/build_package.sh --render
   <project-dir>` produces the document in both formats. **The renderer lives
   with the editor, not here** — if this agent is running somewhere other than
   the machine the IDE is on, there is no route to it, and the build stops one
   step short on purpose with everything else already written. Say that
   plainly rather than reporting a failure: the remaining step is one command
   on the other machine.

## What goes in, and what is only pointed at

The package names the pipeline, its revision and its parameters instead of
copying it. That is what makes the work re-runnable without carrying a second
copy that drifts from upstream the moment it is released again — the same
reason nothing here keeps its own list of what a pipeline produces.

Results stay where they are and are referenced by path. They are read-only and
can be re-fetched; a copy inside the project is a second thing to disagree
with the first.

`docs/FINISH.md` carries worked examples from real projects — what the
provenance looked like, which citations matched and which did not. Read it for
a sense of what to expect, never as a substitute for running the tools on the
project in front of you.
