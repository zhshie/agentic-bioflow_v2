# agentic-bioflow Constitution

This constitution is the single source of truth for what this project will and will not do. It
supersedes every other document in the repository. `docs/PRINCIPLES.md` keeps the reasoning and
history behind each rule; where the two disagree, this file wins and the other is corrected.

The rules were extracted from what the repository already enforces, not invented. Each keeps its
original invariant number and names the check that holds it: a principle with no check is a
slogan, and slogans lose to whatever seems reasonable in the moment. The constitution holds only
what is true at every stage of `docs/ROADMAP.md`; principles already agreed but not yet checked
wait in that file's "Principles waiting for a check" and join here by amendment once their check
exists.

## Core Principles

### I. Build Only What Nobody Else Maintains

- **1.** Before anything is added, the change MUST name what Seqera, nf-core, or another
  maintained tool already uses for the same job. Only when nothing can be named is it ours to
  write. Every script under `scripts/` MUST state its answer in its own header:
  `# Not <tool>: <reason>`, or `# Nothing existing: <why>` for thin glue.
  *Check:* `tests/scripts_name_their_alternative.sh`.
- **2.** The execution backend is the single source of truth for run state: Seqera Platform
  where it is used, Nextflow's own records where it is not. No file in this repository MAY keep
  a second copy of a run's state, and there MUST be no submission script of our own, no state
  machine, and no monitoring daemon. Where the backend is Seqera, the command layer follows
  Seqera's nouns (compute environment, then pipelines → datasets → launch, then runs).

*Rationale:* three features were rebuilt here before anyone checked, and each was written and
then deleted (PITFALLS 14). A second copy of run state drifts from the real one; making Seqera
optional means reading Nextflow's own records, not rebuilding Platform (`docs/adr/0001`).

### II. Anyone, Anywhere

- **3.** No personal paths, no cluster paths, no marketplace coordinates. Every location MUST
  derive from a deployment variable (`$LAB_RUNS_DIR`) or the deployment's own settings file.
  A home directory is not a shared location. *Check:* `tests/no_hardcoded_paths.sh`.
- **4.** Scheduler, firewall and storage are site properties, supplied by a site adapter under
  the contract in `docs/SITE_ADAPTER.md`. The command layer MUST NOT name a scheduler, partition,
  queue or relay. A second site adapter MUST NOT be written until a real second site exists.
  *Check:* `tests/command_layer_is_site_neutral.sh`.
- **5.** Judgment, procedure and site operations live in `docs/` and `scripts/`, readable and
  runnable by a person or another model. Whatever AI host runs the tool, its own capabilities
  (hooks, skills, commands or their equivalents) MUST be used fully.
  *Check:* with `hooks/` and `.claude-plugin/` removed, the system still works from `docs/` and
  `scripts/`: degraded, not equivalent, but usable.

*Rationale:* one cluster is not the world, and a lowest common denominator would drop the
safety net along with the hooks that carry it.

### III. A Person Can Finish

- **6.** Any pipeline, no configuration. Resource mapping MUST key off the composed request
  (`task.cpus`, `task.memory`, `task.time`), never off label names. Samplesheet columns MUST come
  from the pipeline's own `assets/schema_input.json` and parameters from its
  `nextflow_schema.json`, never from a per-pipeline file in this repository.
  *Check:* a pipeline nobody here has seen runs to completion under `-profile test` with no
  mapping added; `tests/no_per_pipeline_config.sh`.
- **7.** Nobody should need the maintainer. A user MUST NOT have to read `docs/PITFALLS.md` or
  ask the maintainer to keep going. Each step MUST say what it will do before doing it, and
  onboarding MUST prove the environment on public test data, touching none of the user's data,
  before handing over the command list.
  *Check:* someone completes onboarding with no point where outside knowledge was required.

*Rationale:* nf-core labels are partial and stackable, so a label table goes stale the moment a
pipeline adds one; and an unverified environment taken to real data fails where it costs most.

### IV. Evidence Before Claims

- **8.** Measure or read the source before claiming that something is needed, impossible, or
  general. The result goes in `docs/PITFALLS.md`.
  *Check:* every PITFALLS entry corresponds to a real failure or a real piece of source read.
- **9.** Anything written on a user's behalf MUST point at the file that produced it. A citation
  comes from the run's own files, a user-supplied DOI, or a page actually fetched, never from
  memory. A number comes from a file; a new statistic comes from a script that ran. A gap is
  written visibly into the output. A figure is described by what its data shows, never by how
  it looks. *Check:* `tests/principle_9_test.sh`.
- **10.** Anything outside the design MUST take one path, not an improvised one: say so, record
  it with `scripts/report.sh`, try within the safety net, and offer the report. The procedure is
  written once in `skills/operational/SKILL.md`; which conditions are designed is
  `docs/CONDITIONS.md`, measured by `scripts/detect_conditions.sh`.
  *Check:* `tests/off_design_single_path.sh`, `tests/conditions_matrix_test.sh`,
  `tests/report_test.sh`.

*Rationale:* each of "we need to build X", "Y is impossible" and "this generalises" was asserted
here and was wrong; and a wrong line in a methods section goes out under a researcher's name.

### V. The User's Folder, the User's Shell

- **11.** The plugin requires a shell, never a folder. When the shell lacks exactly one
  capability, the plugin MUST borrow exactly that capability (for example `wsl.exe -e ssh`)
  rather than ask the user to move, and MUST NOT borrow more than the measured gap. Plugin files
  resolve under `${CLAUDE_PLUGIN_ROOT}`; scripts locate themselves from `${BASH_SOURCE[0]}`,
  never from `pwd`. Every refusal MUST say whether it declines a shell, a folder, or a
  capability. Settings privacy MUST be measured by reading it back (mode on Unix, ACL on
  Windows), never assumed; a list of cloud-sync folder names is a reminder, never a guarantee.
  *Check:* `tests/path_shapes_test.sh`, `tests/settings_test.sh`,
  `tests/windows_privacy_test.sh`, `tests/on_site_test.sh`, `tests/wsl_bridge_test.sh`,
  `tests/conditions_matrix_test.sh`.

*Rationale:* a member not told where their work may live moves it to wherever they think the
plugin wants it, which is exactly backwards; and borrowing a whole environment instead of one
call makes the safety net compare paths from two different worlds.

### VI. Nothing Goes Quiet

- **12.** A request that carries action intent MUST reach the formal flow and show its
  walkthrough. A pure knowledge question MAY be answered directly.
  *Check:* `tests/plugin_intro_test.sh` (T3), `tests/skill_requires_intro_test.sh`,
  `tests/confirm_walkthrough_test.sh` (G6).
- **13.** When the safety net cannot do its job, it MUST say so: never silently permissive, and
  never silently refusing everything. With `jq` missing or broken, the gates refuse what they
  cannot rule out from the raw text and name the fix. (In a session where the plugin is not in
  use there is no job to do, and it stays silent: see the Safety Net's scope.)
  *Check:* the "no jq" sections of `tests/confirm_launch_test.sh`,
  `tests/confirm_cleanup_test.sh`, `tests/confirm_walkthrough_test.sh`,
  `tests/plugin_intro_test.sh`.

*Rationale:* a degraded safety net that says nothing, in either direction, is indistinguishable
from a working one until the moment it matters (PITFALLS 28, issue #15).

## Safety Net (Non-Negotiable)

**Scope.** The rules below govern a session in which agentic-bioflow is *in use*. A session is in
use when any one of these holds:

1. **The session has used the plugin.** The user typed an `/agentic-bioflow:` command, a plugin
   skill was loaded, or the request was worded so as to route to the plugin, and
   `hooks/plugin_intro.sh` left its per-session marker. A subagent carries its parent's session
   id, so it shares the parent's marker.
2. **The session's working folder is inside the deployment**: under the settings root, or under
   `storage_root`.
3. **The call itself is about the plugin**: it runs one of the plugin's scripts or hooks, runs
   `tw`, names a path under the deployment, or is a Seqera or Tower MCP tool.

When the plugin is unsure (the hook input carries no session id, or the state directory cannot
be read) the session counts as in use. Outside a session in use the plugin stays silent: no hook
gates, reminds or prints anything. The definition lives in `hooks/in_use.sh`.
*Check:* `tests/in_use_test.sh`, `tests/in_use_speed_test.sh`, `tests/constitution_scope_test.sh`.

The rules that follow apply in a session in use, and are unchanged from 1.0.0.

These rules are not subject to the principles above, MUST NOT be relaxed by any feature spec or
plan, and change only by a MAJOR amendment of this constitution.

- Never delete a user's source data: `rawdata/`, `results/`, `analysis/`, a run area's
  `_references/`, or a shared image cache. Never delete `.nextflow/plugins/`.
- Deleting `work/` or `.nextflow/cache/` requires the user's explicit confirmation
  (`hooks/confirm_cleanup.sh`).
- A launch command is shown in full and waits for explicit confirmation before it runs
  (`hooks/confirm_launch.sh`).
- Credentials and personal details live only in the deployment's own settings area, readable by
  the owner only; never printed, never in git, never in a params file, and never carried over
  from another member's copy.

## Development Workflow

- **Features** (new or changed behavior) MUST go through the Spec Kit feature workflow:
  `/speckit-specify` → `/speckit-clarify` → test cases → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-analyze` → `/speckit-implement` → `/speckit-converge`. Each spec opens with a User
  Story, and every requirement has Given/When/Then scenarios of three kinds: normal, exception,
  and out of scope. A spec describes the change being made, not a retroactive inventory of
  existing behavior.
- **Bugs** (existing behavior broken) MAY use the Spec Kit bug workflow instead
  (`/speckit-bug-assess` → `/speckit-bug-fix` → `/speckit-bug-test`); the maintainer reviews the
  assessment before any fix is made.
- **Test cases before design.** For a feature, `test-case.md` and `test-case-overview.md` MUST be
  written after clarify and approved by the maintainer before `/speckit-plan` runs. The plan MUST
  cite the spec, the approved test cases, and this constitution.
- **Green at every stage.** Implementation runs in stages; each stage ends with
  `bash tests/run_all.sh` fully green and a test for every approved scenario. It runs in WSL or on
  Linux; native Git Bash refuses it.
- **Independent acceptance.** Acceptance is judged by a separate read-only reviewer against the
  spec, the approved test cases and the diff, never by the author of the change.
- **Manual walkthrough.** A change touching `commands/`, `skills/` or `hooks/` also passes the
  manual half of `docs/TESTING.md`, after restarting the AI host so hooks reload.
- **One change at a time, on a branch.** `main` receives merges only; CI
  (`.github/workflows/tests.yml`) MUST be green first, and only the maintainer merges.

## Amendments

### 2.0.0 (2026-10-02): the Safety Net applies to sessions in which the plugin is in use

**Rationale (#48).** On 2026-10-02 a general-purpose subagent was doing a small analysis that used
neither nf-core nor this plugin. It ran one read-only query of the cluster's configuration through
`wsl.exe -e ssh -o BatchMode=yes ...`. `hooks/confirm_launch.sh` stopped it for confirmation,
because a direct ssh costs a one-time code (PITFALLS 16b). Auto mode cannot override a hook's
"ask", so every such call waited for a person. The hook was wrong twice. About scope: the session
was not using agentic-bioflow at all. About detection: ssh through WSL shares an open connection
and `BatchMode=yes` never prompts, so neither costs a code. The detection half is fixed in the
hook (the D3 exceptions). The scope half cannot be fixed under 1.0.0, which wrote the Safety Net
as holding wherever the plugin is installed. A plugin is installed per user, so its hooks fired in
every session in every project. The maintainer's goal, in his words: stop anything agentic-bioflow
configured from being invoked by a session that is not using agentic-bioflow. In the clarification
of feature 005 he chose to switch the whole net off outside use, not only the ssh reminder:
deleting `rawdata/` or `results/`, clearing `work/`, and confirming a launch included.

**What changes.** The Safety Net gains a scope: it governs a session in which the plugin is in
use, defined by three conditions plus a rule that unsure counts as in use. The four rules
themselves are unchanged. The hooks carry the scope: each asks `hooks/in_use.sh` first and exits
silently when the answer is no.

**Impact on existing deployments.**
- A session that is not in use is no longer protected by any hook. That is a session with no
  plugin marker, working outside the deployment folders, running no plugin script and no `tw`.
  In it, `rm -rf results/`, a direct `sbatch` or `nextflow run`, and a direct ssh are no longer
  stopped. This is the cost the maintainer accepted. Whatever a workspace says in its own
  instructions is then the only protection, and that is the model's discipline, not a hook.
- In a session in use, nothing changes: every gate, refusal, confirmation and reminder fires as
  before, and the whole existing test suite passes unchanged.
- The one reminder whose rule changed in use is the direct-ssh one: ssh run through WSL, or with
  `-o BatchMode=yes`, no longer asks, because neither can cost a code.
- Writing into the installed plugin's own directory is still refused from any session, because
  naming the plugin's own path is itself a reason to count as in use.
- The session-start context (the deployment line and the Git Bash note) no longer appears in a
  folder outside the deployment. The overview still appears the first time the plugin is used.
- Credentials and personal details (the fourth rule) are a rule about files, not a hook, and are
  unchanged.
- When in doubt the hooks treat the session as in use, so a deployment that loses its state
  directory or whose host sends no session id keeps the full net.

**Version.** MAJOR, under Governance: the amendment redefines the Safety Net's scope.
**Approval.** Maintainer's choice recorded in `specs/005-plugin-scope/spec.md` (Clarifications,
2026-10-02); merge approval is the maintainer's, on the pull request that carries this change.

## Governance

- This constitution supersedes all other practices and documents in this repository.
  `docs/PRINCIPLES.md` (reasoning and history) and the root `CLAUDE.md` (runtime guidance for
  agents) MUST NOT restate a rule differently from this file; when they do, they are corrected.
- An amendment requires, in one PR: the rationale for the change, an assessment of what it
  breaks for existing deployments, the version bump, and the matching update to any document
  that cites the changed rule. Only the maintainer approves and merges it.
- Versioning: MAJOR for removing or redefining a principle or any Safety Net rule; MINOR for a
  new principle or materially expanded rule; PATCH for wording that changes no meaning.
- Every plan's Constitution Check, every `/speckit-analyze`, and every acceptance review MUST
  check the principles and the Safety Net. A violation needs a written justification in the plan,
  or the change stops.

**Version**: 2.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-10-02
