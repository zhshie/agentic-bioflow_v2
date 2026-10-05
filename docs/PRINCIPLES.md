# Principles: reasoning and history

**The rules themselves live in `.specify/memory/constitution.md`** - one statement of each,
with the check that holds it. This file keeps what the constitution leaves out: why each rule
exists and the failures that produced it. Where the two disagree, the constitution wins and this
file is corrected (constitution, Governance). The invariant numbers are the same in both, so a
citation such as "`PRINCIPLES.md`, invariant 2" still finds its reasoning here and its rule
there.

`PITFALLS.md` records what went wrong. This file records why that decided what it did.

It exists because the reasoning kept evaporating. Design decisions that took a
failed run to reach were re-litigated a week later from memory, and each
re-derivation drifted: a plan whose acceptance criteria were about whether a
variable resolved rather than whether a person succeeded; a proposal to build a
daemon this project had already decided not to build. Reasoning that lives only
in a conversation does not survive the conversation.

---

## A. What this bridge is for

**1. Build only what Seqera, nf-core, or any tool someone already maintains
does not already do.**

The three things this project rebuilt before checking are in PITFALLS 14: a
biotype warning nf-core already emits, a STAR index calculation the module
already performs, and a samplesheet generator that shipped with the pipeline.
Each was written, then deleted.

**2. Follow Seqera's shape; do not invent a parallel one.**

The commands are Seqera's nouns — compute environment, then
pipelines → datasets → launch, then runs. A user who knows Seqera already knows
this tool, and anything Seqera ships later lands in a slot that already exists.
The execution backend is the single source of truth for run state — Seqera
Platform where it is used, Nextflow's own records where it is not
(constitution, invariant 2) — and no file here keeps a second copy.

## B. Who can use it, and where

**3. Anyone can install it.**

No personal paths, no cluster paths, no marketplace coordinates. Every location
derives from a deployment variable — `$LAB_RUNS_DIR` and the deployment's own
settings file. A home directory is not a shared location: on a typical cluster
`/home/<someone>` is mode 700, so a file placed there is invisible to every
other member no matter how the file itself is permissioned.

**4. One cluster is not the world.**

SLURM, a firewall, POSIX storage — these are *site* properties. A site adapter
supplies them; the core must not assume them. On a cloud compute environment
there is no relay to check and no partition to choose, and nothing outside the
adapter should have to know that.

**5. Portable substance, but never a lowest common denominator.**

Judgment, procedure and site operations live in `docs/` and `scripts/`, which a
person or another model can read and run directly. The host's own capabilities —
hooks, skills, commands — are used fully, because dropping hooks would drop the
safety net and dropping the skill would leave a tool that exists only when
someone types a slash. The stronger form - a host that lacks the safety net may
query but never launch or delete - is agreed but has no check yet, so it waits
in `docs/ROADMAP.md` ("Principles waiting for a check") rather than in the
constitution.

This costs nothing here, which is why it holds: the things worth building were
already portable. Pitfalls are markdown, the resource mapping is a Nextflow
config, the relay is Python, site operations are shell. Writing them that way is
better for the primary host too — testable, reusable, and not occupying context.
The host-specific layer is thin glue over portable substance, so a port rewrites
the glue rather than the system.

## C. Whether a person can finish

**6. Any pipeline, no configuration.**

Resource mapping keys off the *composed* request (`task.cpus`, `task.memory`,
`task.time`), never off label names: nf-core labels are partial and stackable,
and a label table goes stale the moment a pipeline adds one. Samplesheet columns
come from the pipeline's `assets/schema_input.json`, parameters from its
`nextflow_schema.json` — never from a per-pipeline file in this repository
(constitution, invariant 6), for the same reason: it would go stale the same way.

**7. Nobody should need the maintainer.**

A user must not have to read `PITFALLS.md` or ask whoever built this in order to
keep going. Say what a step will do before doing it. Prove the environment works
on public test data — touching none of their real data — and do not hand them
the command list until that proof passes (constitution, invariant 7): skip
that order and they take an unverified environment to real data instead.

## D. How to work

**8. Measure or read the source before claiming.**

"We need to build X", "Y is impossible", "this generalises" — each of these was
asserted here and each was wrong. The GTF check that nf-core already did. The
missing outputs that were a dead agent. The claim that a compute environment's
config could be edited in place. Verify first; the result goes in `PITFALLS.md`.

**9. Anything written on a user's behalf points at the file that produced it.**

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

*How it is held:* `scripts/cite.sh` resolves every DOI over the network and marks what
it cannot resolve; `scripts/methods_text.py` reports a near-miss as a candidate
rather than citing it; `scripts/build_package.sh` writes a comment for every
planned figure that is missing and every figure nobody planned.
`tests/principle_9_test.sh` asserts those three stay true.

**10. What the design does not cover takes one path, not an improvised one.**

A command file that says "anything else: diagnose it fully" hands the model a
blank cheque, and each member who reaches that line gets a different answer
that nobody will ever see. When a condition, a failure or a request is outside
what is designed here, the model says so, records it with `scripts/report.sh`,
tries within the safety net, and at the end offers the report - one procedure,
written once in `skills/operational/SKILL.md` ("Off-design: when nothing here
covers it"). The maintainer designs it in instead of filing it. Which
conditions count as designed is `docs/CONDITIONS.md`, measured by
`scripts/detect_conditions.sh` rather than guessed.

*How it is held:* `tests/off_design_single_path.sh` (no catch-all in `commands/` that
does not point at that section), `tests/conditions_matrix_test.sh` (every cell
the script can print is in the matrix, and the reverse), `tests/report_test.sh`
(nothing leaves the machine that is not a whitelisted field).

## E. Where a person's own things live

**11. The folder is the user's; the shell is the only thing this plugin
requires — and when the shell is short of exactly one thing, the plugin
borrows that one thing rather than asking the member to move.**

Two reasons for the second half, both concrete. First, 16g measured a working
route through the shell already at hand — `wsl.exe -e ssh` reaching the site
with no shell switch at all — and the code went on refusing the whole shell
anyway; that writes an implementation limit into the product as if it were
the member's problem, which PITFALLS 25 already did once. Second, what is
borrowed has to be exactly the size of the measured gap. Borrowing the one
call that needs WSL moves bytes, exit codes and stderr across (16g measured
all three crossing intact) and no paths at all. Borrowing a whole execution
environment moves the paths too, and then the two sides stop agreeing about
what a path means: `hooks/guard_plugin_files.sh` would be comparing a tool
payload's Windows path against a plugin root that had become a WSL one, and a
safety net that stops matching says nothing while it does it. That failure is
reasoned, not measured — which is the point: it costs nothing to avoid by
borrowing narrowly, and the narrow version needs no such argument.

Opening Claude Code somewhere decides exactly one thing: which shell it
inherits. It does not decide where a member's work may live, and nothing here
needs it to. The plugin's own files resolve under `${CLAUDE_PLUGIN_ROOT}`,
never the working directory — every command file says so in its own header
(`commands/launch.md:6-8`), and `tests/commands_resolve_their_own_paths.sh`
holds it. Every script locates itself from `${BASH_SOURCE[0]}`
(`scripts/on_site.sh:35`, `scripts/preflight.sh:11`), never from `pwd`.
Personal and site paths come from the settings file and `$LAB_RUNS_DIR`, never
baked in (invariant 3). The site side lives under
`$LAB_RUNS_DIR/<seqera_user>/projects/…` and the local side under the root
the member named, anywhere they already keep work (`docs/SETTINGS.md`); `scripts/fetch.sh:33` stages fetched results
under `$XDG_CACHE_HOME`, never the project folder. A member not told this
assumes the opposite, and moves their work to wherever they think the plugin
wants it — which is exactly backwards.

Requiring a shell is not requiring a folder, and the two are not
interchangeable in a refusal, and neither is a *capability*.
`unsupported-msys-no-wsl` refuses over the third: WSL is absent, so the one
call that needs it has nothing to borrow (16g measured that call working
wherever it is present). The other two reasons this cell used to carry were
not worked around but removed — the single place that still needed a real
python3 is awk now (20c), and the jq refusal names an installer that runs on
that machine. What is left is one missing capability, named as such; it must
never be read, or written, as a claim about where the project folder is
allowed to sit. Every place this plugin declines something says which of
the two it is declining.

The one place location genuinely matters is the settings file and the token
beside it, and even there the answer is **measured, not listed**: write the
file, then ask the machine who can read it back. On Unix that is the mode. On
Windows it is not: Git Bash renders a mode for an NTFS file that nobody wrote
and nothing enforces, so the check asks Windows for the file's ACL instead and
refuses only when Windows names someone beyond the owner, SYSTEM and the
Administrators group (PITFALLS 16j/16k). Measuring the wrong thing is not a
milder failure than measuring nothing: for one release this refused to write a
settings file that was in fact owner-only, and told the member to move it to
the directory it was already in. A list of folder names known to be a
cloud-sync root — Dropbox, OneDrive, iCloud Drive — can never be complete, so
it is a reminder, never a guarantee, and the refusal it produces has to admit
that plainly rather than imply coverage it does not have. The gap between "the
check passed" and "this is safe" is exactly where a member would otherwise
lose a token: a synced folder holds mode 600 perfectly well on the machine
that set it, and the loss happens somewhere else entirely — on every other
device that folder syncs to, silently, with no permission bit to read back
and fail.

Invariant 3 is about paths baked into *this repo*; 11 is about where the
*user's* folder may sit, and the answer there is: wherever they already keep
it.

*How it is held:* `tests/path_shapes_test.sh` — runs these scripts from a directory
whose name carries spaces and non-ASCII, the shape a member reaches first, not
a convenient fixture. The privacy read-back and the synced-folder refusal
(reminder, not guarantee) in `tests/settings_test.sh`, and what that read-back
asks on Windows in `tests/windows_privacy_test.sh`. The "the folder stays
put" assertions in `tests/on_site_test.sh`. The borrow-exactly-the-gap rule:
`tests/wsl_bridge_test.sh` (only the transport bridges; no path crosses it),
`tests/conditions_matrix_test.sh` (a bridged shell lands in `supported`, not
in a refusal that reads like a folder problem), and `tests/settings_test.sh`
again (the settings file is not part of what moves).

## F. What must not go quiet

Added 2.16–2.18 (T1/T3/T4/T5), both traced to real failures rather than
reasoned from scratch — invariant 8's own rule applied to this file.

**12. A request that carries action intent must reach the formal flow, and
the user must see its walkthrough — not just get an answer.**

"I want to run the RNA-seq samples and submit them" and "what is RNA-seq"
pass through the same model, and only a procedure exists for one of them.
Before 2.16, the only door into that procedure was typing the plugin's own
name or the model loading its skill directly — a request that plainly wants
something DONE, in plain language, had no path that ever reached
`scripts/intro.sh`, `skills/operational/SKILL.md`, or any gate that assumes
that call already happened. Skipping the walkthrough is not a shortcut to
the same outcome; it is every other invariant in this file going unconsulted
at once, because they are all downstream of a flow that was never opened.

This is narrower than "always load the skill": a pure knowledge question
carries a topic with no action, and answering it directly is correct, not a
gap. What must not happen is action intent (跑/分析/送出/launch/為什麼失敗,
English or Chinese) going straight to an answer with no routing at all.

*How it is held:* `hooks/plugin_intro.sh`'s topic-AND-action match on a
UserPromptSubmit prompt routes a natural-language request with intent
toward `agentic-bioflow:operational`, and leaves a pure knowledge question
alone (`tests/plugin_intro_test.sh`, "T3: natural-language routing").
`skills/operational/SKILL.md` states `scripts/intro.sh <command>` as the
first action once a command is decided, the same requirement every
`commands/*.md` file already carries for a typed slash command
(`tests/skill_requires_intro_test.sh`). `hooks/confirm_walkthrough.sh`'s G6
denies the first gated action inside a command whose opening card was never
shown, whether reached by a typed command or by the skill
(`tests/confirm_walkthrough_test.sh`, the G6 cases). Its G7 is the one gate
that is not about a missing step: it refuses a params file (yaml, yml or json)
that carries a credential, whatever the transcript shows, because the Safety
Net says a credential is never in a params file (G7 cases in the same test).
It is a net for the common shapes; its reach is stated in the hook's header.

**13. When the safety net cannot do its job, it must say so — never quietly
do nothing, and never refuse everything either.**

Two failures at different scales, both real. PITFALLS 28: a missing `jq`
used to make every judgement in the three safety-net hooks silently resolve
to "harmless", and the gate vanished with nothing printed — fixed by
refusing outright. Refusing outright turned out to be its own way of going
quiet: GitHub issue #15, a member who could not get the safety net working
simply stopped using it and started typing commands into a plain PowerShell
window instead, which has none of this plugin's guarantees — and nothing
here knew that had happened either, because the only visible symptom was
"nothing runs", not "the safety net is gone". A degraded safety net that
says nothing, in either direction — silently permissive or silently total —
is indistinguishable from a working one until the moment it matters.

*How it is held:* `hooks/confirm_launch.sh`, `hooks/confirm_cleanup.sh` and
`hooks/confirm_walkthrough.sh` still refuse when `jq` is missing or
broken — scoped to what they cannot rule out from the raw text, not every
command — and name the fix (`tests/confirm_launch_test.sh`,
`tests/confirm_cleanup_test.sh`, `tests/confirm_walkthrough_test.sh`, each
file's "no jq" section). `hooks/plugin_intro.sh` prints one `systemMessage`
warning per session when it finds `jq` missing, rather than exiting silently
the way it used to (`tests/plugin_intro_test.sh`, "no jq ... warns").

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

When to look at this again: only when an agent that is not Claude Code needs
a read-only question answered that neither Seqera's MCP (run state) nor the
lab's record system (experiments, samples) can answer - "every run and output
for this sample", say. "Everyone ships an MCP server" is not that condition.
Which agents may touch what is `docs/LAB_AGENTS.md`.

---

## The safety net

Stated once, in the constitution's "Safety Net (Non-Negotiable)" section, and
not subject to the reasoning above. It is not repeated here so that it cannot
be repeated differently.

What this file does keep is why the net has a scope, since that is history and
not a rule. Until 2.0.0 the net held wherever the plugin was installed, and a
plugin is installed per user, so it fired in every session in every project.
On 2026-10-02 (#48) a subagent doing a small analysis with neither nf-core nor
this plugin was stopped for confirmation on a read-only query of the cluster's
configuration, by a gate written for pipeline runs; and auto mode cannot
override a hook's "ask". The maintainer's answer was to scope the whole net to
sessions in which the plugin is *in use* (Constitution 2.0.0): a marker the
session's own first use of the plugin leaves, a folder inside the deployment,
or a call that itself names the plugin, `tw` or a Seqera tool, with "cannot
tell" counting as in use. The cost, accepted on purpose, is that a session
that is not in use is no longer protected by any hook. The definition is in
the constitution and runs in `hooks/in_use.sh`; this file does not restate it.
