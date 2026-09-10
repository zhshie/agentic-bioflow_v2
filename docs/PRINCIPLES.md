# Principles

`PITFALLS.md` records what went wrong. This file records what decides.

It exists because the reasoning kept evaporating. Design decisions that took a
failed run to reach were re-litigated a week later from memory, and each
re-derivation drifted: a plan whose acceptance criteria were about whether a
variable resolved rather than whether a person succeeded; a proposal to build a
daemon this project had already decided not to build. Reasoning that lives only
in a conversation does not survive the conversation.

**Every invariant below carries a check.** A principle with no check is a
slogan, and slogans lose to whatever seems reasonable in the moment.

---

## A. What this bridge is for

**1. Build only what neither Seqera nor nf-core already does.**

The three things this project rebuilt before checking are in PITFALLS 14: a
biotype warning nf-core already emits, a STAR index calculation the module
already performs, and a samplesheet generator that shipped with the pipeline.
Each was written, then deleted.

*Check:* before adding anything, say out loud what Seqera and nf-core use to do
the same job. Only when you cannot name it does it become ours to write.

**2. Follow Seqera's shape; do not invent a parallel one.**

The commands are Seqera's nouns — compute environment, then
pipelines → datasets → launch, then runs. A user who knows Seqera already knows
this tool, and anything Seqera ships later lands in a slot that already exists.
Platform is the single source of truth for run state; we keep no copy of it.

*Check:* no file in this repo records the state of a run. No submission script,
no state machine, no monitoring daemon.

## B. Who can use it, and where

**3. Anyone can install it.**

No personal paths, no cluster paths, no marketplace coordinates. Every location
derives from a deployment variable — `$LAB_RUNS_DIR` and the deployment's own
settings file. A home directory is not a shared location: on a typical cluster
`/home/<someone>` is mode 700, so a file placed there is invisible to every
other member no matter how the file itself is permissioned.

*Check:* `tests/no_hardcoded_paths.sh`.

**4. One cluster is not the world.**

SLURM, a firewall, POSIX storage — these are *site* properties. A site adapter
supplies them; the core must not assume them. On a cloud compute environment
there is no relay to check and no partition to choose, and nothing outside the
adapter should have to know that.

*Check:* `tests/command_layer_is_site_neutral.sh`. The contract itself, and what
this site supplies for each part of it, is `docs/SITE_ADAPTER.md`.

**5. Portable substance, but never a lowest common denominator.**

Judgment, procedure and site operations live in `docs/` and `scripts/`, which a
person or another model can read and run directly. The host's own capabilities —
hooks, skills, commands — are used fully and **are not given up because another
harness lacks them**. Dropping hooks would drop the safety net; dropping the
skill would leave a tool that exists only when someone types a slash.

This costs nothing here, which is why it holds: the things worth building were
already portable. Pitfalls are markdown, the resource mapping is a Nextflow
config, the relay is Python, site operations are shell. Writing them that way is
better for the primary host too — testable, reusable, and not occupying context.
The host-specific layer is thin glue over portable substance, so a port rewrites
the glue rather than the system.

*Check:* with `hooks/` and `.claude-plugin/` removed, the system still works
from `docs/` and `scripts/` — **degraded, not equivalent**. Usable is the bar.

## C. Whether a person can finish

**6. Any pipeline, no configuration.**

Resource mapping keys off the *composed* request (`task.cpus`, `task.memory`,
`task.time`), never off label names: nf-core labels are partial and stackable,
and a label table goes stale the moment a pipeline adds one. Samplesheet columns
come from the pipeline's `assets/schema_input.json`, parameters from its
`nextflow_schema.json`.

*Check:* a pipeline nobody here has seen runs to completion under `-profile
test` **with no mapping added along the way**.

**7. Nobody should need the maintainer.**

A user must not have to read `PITFALLS.md` or ask whoever built this in order to
keep going. Say what a step will do before doing it. Prove the environment works
on public test data — touching none of their real data — before their first real
run, and do not hand them the command list until that proof passes, or they will
take an unverified environment to real data.

*Check:* someone completes onboarding with no point where outside knowledge was
required to continue.

## D. How to work

**8. Measure or read the source before claiming.**

"We need to build X", "Y is impossible", "this generalises" — each of these was
asserted here and each was wrong. The GTF check that nf-core already did. The
missing outputs that were a dead agent. The claim that a compute environment's
config could be edited in place. Verify first; the result goes in `PITFALLS.md`.

*Check:* every entry in `PITFALLS.md` corresponds to a real failure or a real
piece of source that was read.

**9. Every verifiable claim points at the file that produced it.**

Invariant 8 governs what this project asserts about itself. This one governs
what it writes on someone's behalf, and the stakes are different: a wrong line
in a methods section goes out under a researcher's name, and no test run later
can catch it.

Three consequences, and each closes a way to produce something false:

- **A citation comes from the run's own files, from a DOI the user supplied,
  or from a page actually fetched — never from memory.** A recalled reference
  may not exist. A fabricated one is worse than a missing one, because missing
  is visible.
- **A number comes from a file; a new statistic comes from a script that was
  run.** Not estimated, not read off a figure, not recalled.
- **A gap is written into the output.** Where no source can be found, the
  document says so where a reader will see it. A document that quietly omits
  something looks finished.

The same rule covers describing a figure: say what the data shows, never what
the picture looks like. The plot is on the user's screen and not ours.

*Check:* `scripts/cite.sh` resolves every DOI over the network and marks what
it cannot resolve; `scripts/methods_text.py` reports a near-miss as a candidate
rather than citing it; `scripts/build_package.sh` writes a comment for every
planned figure that is missing and every figure nobody planned.
`tests/principle_9_test.sh` asserts those three stay true.

---

## Where each piece belongs

A plugin is not an alternative to a skill or an MCP server — it is the envelope
that holds them. The question is where each piece lives, and three of the
answers are outside this repo.

| Piece | Home | Why |
|---|---|---|
| Resource-floor mapping | **upstream `nf-core/configs`** | 160 institutional configs already live there, installed by nobody. Kept here it helps only us |
| Launchpad entries, datasets, pipeline schemas | **the Seqera workspace** | That is Seqera's data model. This is why there are no per-pipeline spec files here |
| Platform operations | **Seqera's own `tw` and MCP server** | Their MCP already exposes the Platform API. Wrapping it again violates invariant 1 |
| Judgment, safety net, entry points | **this plugin** | What is left once the rest goes where it belongs |

Inside the plugin: the **skill** is the heart, because it is the only part that
works when the user never types a slash command — someone who says "I want to
run RNA-seq" should reach the same tool. **Hooks** are the one thing that
genuinely requires a plugin: a gate must fire whether or not the model chose to
load anything. **Commands** are thin entry points. **Scripts** and **docs** are
the portable substance.

Not an MCP server, for four reasons: Seqera already ships one (invariant 1); the
site operations that remain are five shell scripts on a host that can run shell;
an MCP tool cannot carry procedure or judgment, which is most of the value here;
and a script stays runnable by a person or another model (invariant 5). Between
`tw` and Seqera's MCP, both are Seqera's, so invariant 1 does not decide —
invariant 5 does. Use `tw`; treat the MCP as opportunistic, never a dependency.

---

## The safety net

Not negotiable, and not subject to the reasoning above.

Never delete a user's source data. Never delete `rawdata/`, `results/`,
`analysis/`, a run area's `_references/`, or a shared image cache. Never delete
`.nextflow/plugins/`. Deleting `work/` or `.nextflow/cache/` requires the user's
explicit confirmation. Show a launch command in full and wait for the user to
confirm before running it. Credentials and personal details belong only in the
deployment's own settings area, mode 600 — never printed, never in git, never in
a params file, and never carried over from another member's copy.
