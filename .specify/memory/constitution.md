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

### I. Build Only What Seqera Cannot or Will Not Do Here

- **1.** Before anything is added, the change MUST name what Seqera, nf-core, or another
  maintained tool already uses for the same job, and then either reuse the open-source piece or
  say why it does not serve a lab here: it cannot reach the site, it needs Seqera's Services, its
  licence forbids the use, or its price does. Only then is it ours to write. Every script under
  `scripts/` MUST state its answer in its own header: `# Not <tool>: <reason>`, or
  `# Nothing existing: <why>` for thin glue.
  *Check:* `tests/scripts_name_their_alternative.sh`.
- **2.** Nextflow's own records (trace, report, log, and the events its `nf-tower` plugin emits)
  are the truth about a run. While the plugin uses Seqera Platform, Platform shows them; where
  Platform's display and Nextflow's own records disagree, Nextflow's records win. No file in
  this repository MAY keep a second copy of a run's state, and there MUST be no submission
  script of our own, no state machine, and no monitoring daemon beyond the channels its check
  allow-lists. Where the backend is Seqera, the
  command layer follows Seqera's nouns (compute environment, then pipelines → datasets → launch,
  then runs).
  *Check:* `tests/no_second_run_state_test.sh`.

*Rationale:* three features were rebuilt here before anyone checked, and each was written and
then deleted (PITFALLS 14). A second copy of run state drifts from the real one. The platform of
`docs/adr/0004` keeps an index of Nextflow's records, never a second truth; that rule joins here
once its rebuild check exists (`docs/ROADMAP.md`, "Principles waiting for a check").

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
  *Check:* `tests/works_without_host_test.sh`: with `hooks/` and `.claude-plugin/` removed, the
  system still works from `docs/` and `scripts/`: degraded, not equivalent, but usable.

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
  *Check:* Procedure P1 in `docs/TESTING.md`: someone completes onboarding with no point where
  outside knowledge was required.

*Rationale:* nf-core labels are partial and stackable, so a label table goes stale the moment a
pipeline adds one; and an unverified environment taken to real data fails where it costs most.

### IV. Evidence Before Claims

- **8.** Measure or read the source before claiming that something is needed, impossible, or
  general. The result goes in `docs/PITFALLS.md`.
  *Check:* Procedure P2 in `docs/TESTING.md`: every PITFALLS entry corresponds to a real failure
  or a real piece of source read.
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

1. **The session has used the plugin.** A prompt named an `agentic-bioflow:` command, with or
   without the leading slash (anywhere in it), a plugin skill was loaded, or the request was
   worded so as to route to the plugin, and `hooks/plugin_intro.sh` left its per-session marker.
   A subagent carries its parent's session id, so it shares the parent's marker.
2. **The session's working folder is inside the deployment**: under the settings root, or under
   `storage_root`.
3. **The call itself is about the plugin**: it runs one of the plugin's scripts or hooks, runs
   `tw` (or `tw.exe`), names a path under the deployment (in any spelling: `~`, `$HOME`, a
   symlink's other name), or is a Seqera or Tower MCP tool. A write into the installed plugin's own
   directory counts too.

When the plugin is unsure the session counts as in use: the hook input carries no session id, or
the state directory cannot be read, or (once a deployment exists) cannot be written, so that the
marker may have failed to save. Outside a session in use the plugin stays silent: no hook
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
  the owner only; never printed, never in git, never in a params file. The plugin never fills in one
  member's credential from another member's settings: it asks the user for the value.
  It does not detect a settings file a person copied in by hand.
  *Check:* `tests/credentials_stay_in_settings_test.sh` (never in git; never printed by a script;
  never in a params file, for the common shapes, see its header and the G7 note in
  `hooks/confirm_walkthrough.sh`, with `tests/confirm_walkthrough_test.sh`); readable by the owner
  only: `tests/settings_test.sh`, `tests/windows_privacy_test.sh`; never printed (a fixture token
  is never in the output): `tests/inspect_sides_test.sh`, `tests/status_test.sh`. The last
  sentence has no automated check, and does not need one: it states what the code does (a missing
  value is asked for, never guessed or copied; a changed `agent_connection` asks first, see
  `hooks/confirm_launch.sh`), not a detection the plugin performs.

## Development Workflow

- **Features** (new or changed behavior) MUST go through the Spec Kit feature workflow:
  `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → test cases (`合約已確認`) →
  `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement` → `/speckit-converge`. Each spec opens with a User
  Story, and every requirement has Given/When/Then scenarios of three kinds: normal, exception,
  and out of scope. A spec describes the change being made, not a retroactive inventory of
  existing behavior.
- **Bugs** (existing behavior broken) MAY use the Spec Kit bug workflow instead
  (`/speckit-bug-assess` → `/speckit-bug-fix` → `/speckit-bug-test`); the independent reviewer
  (below) reviews the assessment before any fix is made.
- **Roles.** The development lead talks with the maintainer, writes specs and plans, and
  dispatches work; it does not write the code. The executor (`.claude/agents/executor.md`)
  implements one task at a time; the independent reviewer (`.claude/agents/verifier.md`) writes
  the test cases and judges the result. The maintainer judges outcomes, not code: each spec quotes
  his own examples of what he wants, verbatim.
- **Test cases before code.** For a feature, `test-case.md` and `test-case-overview.md` MUST be
  written by the independent reviewer from the spec, the maintainer's examples and the plan, and
  the overview MUST say `合約已確認` (or `已核可`, when the maintainer approved them himself)
  before implementation starts. The author of the code never writes or edits them.
- **Green at every stage.** Implementation runs in stages; each stage ends with
  `bash tests/run_all.sh` fully green and a test for every confirmed scenario. It runs in WSL or on
  Linux; native Git Bash refuses it.
- **Independent acceptance.** Acceptance is judged by a separate read-only reviewer against the
  spec, the confirmed test cases and the diff, never by the author of the change.
- **Manual walkthrough.** Before a release that contains a change to `commands/`, `skills/` or
  `hooks/`, the manual half of `docs/TESTING.md` passes, after restarting the AI host so hooks
  reload.
- **One change at a time, on a branch.** `main` receives merges only; CI
  (`.github/workflows/tests.yml`) MUST be green first, and the independent acceptance MUST pass.
  Who merges follows the decision tiers: the development lead merges fixes, tests, docs,
  refactors and changes that only make the Safety Net stricter; a change in what a user sees, or
  a modified or removed requirement, waits for the maintainer's yes on the result; amendments to
  this constitution, releases, and anything that loosens the Safety Net are the maintainer's.

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
  directory, cannot write to it, or whose host sends no session id keeps the full net.

**Version.** MAJOR, under Governance: the amendment redefines the Safety Net's scope.
**Approval.** Maintainer's choice recorded in `specs/005-plugin-scope/spec.md` (Clarifications,
2026-10-02); merge approval is the maintainer's, on the pull request that carries this change.

### 2.0.1 (2026-10-05): every rule names a Check that exists

**Rationale (#30, `.specify/bugs/constitution-checks`).** The preamble says each principle names the
check that holds it, and a principle with no check is a slogan. A fresh audit against 2.0.0 found
five rules where that was kept in form and not in fact: principles 2, 5, 7 and 8 and the Safety
Net's credentials rule carried either no *Check:* or a sentence describing a check nobody had
written. `tests/constitution_checks_exist_test.sh` now fails when a rule's *Check:* cites no
`tests/` file and no Procedure, or cites one that does not exist.

**What changes.** Only *Check:* lines are added or completed. Principles 2 and 5 and the
credentials rule cite new automated tests; principles 7 and 8 cite Procedure P1 and Procedure P2,
manual procedures written in `docs/TESTING.md` (Half 3), because what they ask (whether a person
got stuck, whether a claim rests on evidence) cannot be measured by a script. No rule changes its
meaning.

**Impact on existing deployments.** The rules' text is unchanged, but one hook behaves
differently. `hooks/confirm_walkthrough.sh` gains a gate, G7: a write to a params file (yaml, yml
or json) that carries a credential is now refused, and neither the walkthrough evidence nor the
user's escape phrase lifts it. The credentials rule already required this and nothing enforced
it. A params file that holds no credential is unaffected. G7 is a net for the common shapes: a
credential-named key with a value of 12 or more characters on the same line, or a token shape. It
does not see a write by `tee`, `sed -i`, a python `open()` or the PowerShell tool, a short value,
a value on the next line or in a block scalar, or a key without such a word in its name. A
parameter genuinely named like a credential and holding a long opaque value is refused too; its
key naming a file, path, name, policy or pattern, or its value being a path, is not. The
credentials rule's last clause is reworded to say what the code does, see the clarification below.

**Clarification (maintainer's decision, same 2.0.1).** The credentials rule used to end with
"never carried over from another member's copy". Nothing enforced that: `scripts/settings.sh
--migrate` has no owner check, and a settings file copied in by hand is not detected. The
maintainer chose to reword the rule to what the code does, not to add a check. It now says the
plugin never fills in a credential from another member's settings (it asks the user) and does not
detect a copied file. No behavior changes; no deployment is affected.

**Version.** PATCH, under Governance: the amendment names checks and changes no meaning.
**Approval.** The maintainer approves and merges the pull request that carries this change.

### 2.1.0 (2026-10-07): the maintainer judges outcomes; an independent reviewer writes the exam

**Rationale.** The maintainer is not a programmer. Under 2.0.1 he was the gate for things he
cannot judge (test cases, technical plans, every merge), and work queued behind him: on
2026-10-04 six PRs waited for his merge. Anthropic's guidance is that verification, not a
person reading code, is what makes autonomous work safe, and that the agent that does the work
must not grade it (code.claude.com/docs/en/best-practices;
anthropic.com/engineering/harness-design-long-running-apps). His decision on 2026-10-07: split
the development role into a lead that talks with him and does not write code, an executor that
implements, and an independent reviewer that writes the test cases from his own examples and
grades the result; he answers only "is this what I wanted". He approved this amendment in his
own words the same day ("同意修憲").

**What changes.**
- Test cases are written by the independent reviewer, after the plan and from his quoted
  examples, and marked `合約已確認`; his own approval (`已核可`) still counts when he gives it.
- The bug assessment is reviewed by the independent reviewer instead of the maintainer.
- The manual walkthrough moves from every merge to every release that contains such changes.
- Merging follows decision tiers (Development Workflow). Amendments, releases and loosening the
  Safety Net stay with the maintainer, as before.

**Impact on existing deployments.** None: this section governs how the repository is developed,
not what the plugin does. The principles, the Safety Net and every check are unchanged. Features
whose overview already says `已核可` stay valid.

**Version.** MINOR, under Governance: no principle or Safety Net rule is removed or redefined;
the Development Workflow is materially changed.

### 3.0.0 (2026-10-08): a self-hosted platform, reached through MCP

**Rationale.** On 2026-10-08 the maintainer changed the project's direction, in his words:
「完全仿照 Seqera MCP 的模式，自建平台，功能延續 Seqera（一間實驗室用得到的全部＋簡化版多人），
由我自己架雲端服務給大家用（像 cloud.seqera.io），對話不自己做——平台只開 MCP，使用者用自己的
harness 接。」 Reviewing this amendment on 2026-10-09 he added the platform's own chat, connecting
to the model the user chooses (「也做聊天介面 可接模型」); it calls the same MCP tools.
`docs/adr/0004` records the decision and supersedes `docs/adr/0001`, which had
ruled out rebuilding Platform; `docs/adr/0005` records the two-role lab. Principle 1 as written
under 2.x forbade the platform outright, since Seqera already maintains one; principle 2 named
"the execution backend" as the truth, which a platform of our own would become. Both are
redefined so that they keep their purpose (do not rebuild what can be reused; never keep a
second truth about a run) without forbidding the direction.

**What changes.**
- Principle I is retitled. Principle 1 still requires naming what Seqera, nf-core or another
  maintained tool does for the same job, and now asks for one of two answers: reuse the
  open-source piece, or say why it does not serve a lab here. Its check is unchanged.
- Principle 2 names Nextflow's own records as the truth about a run, and says they win where
  Seqera Platform's display disagrees. Its prohibitions and its check are unchanged. The
  platform's index of runs is not written in as a rule yet: it is in `docs/ROADMAP.md`, "Principles
  waiting for a check", until its rebuild test exists.
- The Safety Net is unchanged, word for word. "Gates live in the platform's tool layer" is also
  waiting for a check in `docs/ROADMAP.md`. Scope condition 3 names Seqera or Tower MCP tools
  only; whether a call to the platform's own MCP tools counts as in use is decided by the
  amendment that moves a gate there.
- Development and testing toward the platform never go through Seqera's Services, its MCP
  server or `tw` (`docs/adr/0004`).

**Impact on existing deployments.** None. No hook, script, command or skill changes; 2.17.0
behaves exactly as before, and the whole test suite passes with only the documents that quote
these principles updated.

**Version.** MAJOR, under Governance: principles 1 and 2 are redefined.
**Approval.** The maintainer approves and merges the pull request that carries this change.

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

**Version**: 3.0.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-10-08
