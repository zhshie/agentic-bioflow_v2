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
  this repository MAY keep a second copy of a run's state, and there MUST be no state machine
  and no monitoring daemon beyond the channels its check allow-lists. There MAY be at most one
  submission path of our own: the station agent's launch job, which hands the Nextflow head job
  to the site's own scheduler the way Seqera Platform does, and runs only after the user has
  seen the full launch command and confirmed it, through a channel a person operates: the
  terminal, the form of the person's MCP client, or the platform's confirmation page as the
  same logged-in user (the three are the only ones; a pending request, a token, or any answer
  the model itself can give is none of them). A form answer is accepted from whatever MCP
  client holds the person's token and declares forms, so a client program an AI controls can
  answer it: the token is what must be kept where an AI cannot read it. Over stdio there is no
  caller, so the same-user check does not apply there; over HTTP and on the page there always
  is one. A file that submits is allow-listed by the
  check together with the test that refuses an unconfirmed launch; nothing else submits. After
  the hand-off, everything known about the run comes from Nextflow's records. Where the backend
  is Seqera, the command layer follows Seqera's nouns (compute environment, then pipelines →
  datasets → launch, then runs).
  *Check:* `tests/no_second_run_state_test.sh` (its submission scan covers `scripts/` and
  `platform/`).
  The channel rule has its own check, run by `tests/run_all.sh`, which runs the platform tests in four parts (`tests/platform_test.sh`, `tests/platform_shard_2_test.sh`, `tests/platform_shard_3_test.sh`, `tests/platform_clock_test.sh`): an unconfirmed launch
  is refused through the MCP tool and through the web route (the platform tests
  `test_tch09_*` of `test_human_channel.py` and `test_tch09_b_c_*` of `test_confirm_page.py`).
  The platform's run index is never a second truth: it MUST be rebuildable from Nextflow's own
  records alone, and where the index and the records disagree, the records win.
  *Check:* run by `tests/run_all.sh` (through its four platform parts): the platform tests
  `test_tc030_rebuild_gives_back_every_field` and
  `test_tc031_nextflows_records_win_over_a_damaged_index` of `test_nextflow_e2e.py`.

*Rationale:* three features were rebuilt here before anyone checked, and each was written and
then deleted (PITFALLS 14). A second copy of run state drifts from the real one. The platform of
`docs/adr/0004` keeps an index of Nextflow's records, never a second truth; that rule joined here in 6.0.0,
when its rebuild check existed. The one
submission path exists because a self-hosted platform must do Seqera's submit step, and only the
user's confirmation lets it run.

### II. Anyone, Anywhere

- **3.** No personal paths, no cluster paths, no marketplace coordinates. Every location MUST
  derive from a deployment variable (`$LAB_RUNS_DIR`) or the deployment's own settings file.
  A home directory is not a shared location. *Check:* `tests/no_hardcoded_paths.sh`.
- **4.** Scheduler, firewall and storage are site properties, supplied by a site adapter under
  the contract in `docs/SITE_ADAPTER.md`. The command layer MUST NOT name a scheduler, partition,
  queue or relay. A second site adapter MUST NOT be written until a real second site exists.
  *Check:* `tests/command_layer_is_site_neutral.sh`.
- **5.** Judgment, procedure and site operations live in `skills/`, `docs/` and `scripts/`,
  readable and runnable by a person or another model. Whatever AI host runs the tool, its own capabilities
  (hooks, skills, commands or their equivalents) MUST be used fully.
  *Check:* `tests/works_without_host_test.sh`: with `hooks/` and `.claude-plugin/` removed, the
  system still works from `skills/`, `docs/` and `scripts/`: degraded, not equivalent, but usable.

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
  (`hooks/confirm_launch.sh` in the Claude Code kit; on the platform, the gate in
  `platform/abf_platform/actions`, which takes a person's yes only from the terminal, the form
  of an MCP client or the confirmation page).
- Every write tool of the platform (today `launch`, `cancel`, `resume`, `relaunch` and `forget`) refuses
  until a person has answered on one of those channels; a token, a pending request or the
  model's own answer is never that answer. A new write tool joins this rule with its own
  refusal test before it ships.
  *Check:* `platform/tests/test_actions_layer.py` (`test_tcb04_*` to `test_tcb08_*`),
  `platform/tests/test_human_channel.py` (`test_tch09_*`, `test_tca14_*`),
  `platform/tests/test_resume_entrypoints.py` (`test_tc142_*`, `test_tc144_*`),
  `platform/tests/test_keep_submissions.py` (`test_tc034_*`, `test_tc037_*`, `test_tc038_*`), run by `tests/run_all.sh` (through its four platform parts).
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
- The platform never stores a credential that reaches it inside what it receives (a run's
  config, command line, environment or secret parameters, or an OAuth exchange): none is
  written to its database or its data folder.
  *Check:* `platform/tests/test_secrets.py` (`test_tc040_*`, `test_tc042_*`, `test_tc_i03_*`),
  `platform/tests/test_nextflow_e2e.py` (`test_tc041_*`), `platform/tests/test_human_channel.py`
  (`test_tcf10_f11_*`), run by `tests/run_all.sh` (through its four platform parts).

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
  dispatches work; it does not write the code. The executor implements one task at a time; the
  independent reviewer writes the test cases and judges the result. Both are generic agents
  defined in the development lead's workspace and shared by every project; this repository gives
  them its facts in the root `CLAUDE.md` section "For the executor and verifier". The maintainer judges outcomes, not code: each spec quotes
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

### 4.0.0 (2026-10-11): one submission path of our own, behind the user's confirmation

**Rationale.** On 2026-10-11 the maintainer set the order for the platform: 「照原本路線」,
「雲端伺服器（像 Seqera 有 AWS 等）也要一起」, and 「雲端伺服器不限於 AWS，請直接參考 Seqera
Platform 的設計」. When asked to begin this amendment he said 「開始」. Principle 2 as written
in 3.0.0 says there MUST be "no submission script of our own". That was right while Seqera
Platform launched every run. A self-hosted platform modelled on Seqera has to do what Seqera
does: hand the Nextflow head job to the site's scheduler through its own submit step (a cluster
job in the head queue). Nextflow has no command that submits its own head job, and nothing
maintained and open source does it for a site reached through a user's shared SSH connection;
Tower Agent is closed and talks only to Seqera. So the ban cannot stand as written, and it is
redefined so that it keeps its purpose: no second truth about a run, no state machine, no
monitoring daemon, and the confirmation the Safety Net demands of a launch.

**What changes.**
- Principle 2 no longer bans a submission script outright. It now says there MAY be at most one
  submission path of our own: the station agent's launch job, run only after the user has seen
  the full launch command and confirmed it. The ban on a second copy of a run's state, on a state
  machine and on a monitoring daemon stands. After the hand-off, everything known about the run
  comes from Nextflow's records. The text names "the site's own scheduler", no single scheduler
  and no single cloud.
- Its check, `tests/no_second_run_state_test.sh`, is stricter, never looser. The submission scan
  also reads `platform/abf_platform` and `platform/abf_station` (not `platform/tests/`, whose
  fake site is called `sbatch`); scans 2 to 4 stay on `scripts/`. A new allow-list,
  `LAUNCH_ALLOW`, takes at most one entry, in platform code only, naming the test that refuses
  an unconfirmed launch; the test must be defined under `platform/tests/`, and a stale entry
  fails. A submission in `scripts/` is never excused by it.
- When this amendment is merged no submission path exists: `LAUNCH_ALLOW` is empty, and the
  launch job (feature 007b) builds the one path, with its entry and its test.
- `platform/abf_station/handlers.py` is rewritten in one place so that no quoted `sbatch`
  stands in the source; it only runs `command -v` checks. Its check ids, their order and every
  text a user sees are unchanged.
- Documents that cite principle 2 follow: `README.md`, `CLAUDE.md`, `docs/ROADMAP.md` and the
  tests that pin the version and the wording.
- The Safety Net is unchanged, word for word. Its launch rule ("shown in full and waits for
  explicit confirmation") already says what is wanted. Its scope (sessions in which the plugin is
  in use, guarded by hooks) does not reach the platform's own path, and no hook guards that
  path. So principle 2 itself carries the confirmation requirement for the platform's launch.
  Moving the gates into the platform's tool layer is still a waiting principle
  (`docs/ROADMAP.md`).
- Work left to 007b: `platform/tests/test_scope.py` TC-071 and
  `platform/tests/test_station_static.py` TC-084 forbid submission in platform code under
  principle 2 as it stood. They are untouched here and 007b revises them.

**Impact on existing deployments.** None. No hook, script, command or skill changes behaviour;
`handlers.py` changes only how two lists are written. The allow-list is empty, so the repository
still has zero submission paths until 007b, and the plugin still launches through Seqera, behind
`hooks/confirm_launch.sh`.

**Version.** MAJOR, under Governance: principle 2 is redefined.
**Approval.** The maintainer approves and merges the pull request that carries this change.

### 4.1.0 (2026-10-15): skills are a home of judgment; the platform has four entries

**Rationale.** On 2026-10-15 the maintainer settled how the platform is reached, in his words:
「只加 MCP 網址就能用」, 「平台純粹靠GUI介面也要能使用」, and 「平台也要有對話介面，若使用者不需要使用claude code等harness介面的話也可以直接對話使用」.
He accepted the scope of the web pages as setup → launch → runs → rendered reports → the package,
with figures from scripts made in the platform's chat or in a harness. He also said 「好，加 v3
分支觸發」: the platform generation is built on a branch `v3`, and its CI trigger is configured on
that branch itself, not in this pull request. `docs/adr/0006` records the decision. Principle
II.5 said that judgment and procedure live in `docs/` and `scripts/`; the guidance for every
harness is going to live in `skills/` (the Agent Skills format), so the sentence is made to name it.

**What changes.**
- Principle II.5 names `skills/` beside `docs/` and `scripts/`. Its check,
  `tests/works_without_host_test.sh`, already packs `skills/`. Nothing else in the principle
  changes.
- The four principles that follow from ADR 0006 (every entry reaches the same action; gates live
  where both the tools and the web pages meet them and a person answers each one; the platform's
  own tools count as in use; the web pages and the tools match one to one) have no check yet. They
  wait in `docs/ROADMAP.md`, "Principles waiting for a check", and join by the MAJOR amendment
  that ships with feature 009. No number is promised for it.
- The Safety Net is unchanged, word for word.

**Impact on existing deployments.** None. No hook, script, command or skill changes; 2.17.0
behaves exactly as before, and only documents and the tests that pin them change.

**Version.** MINOR, under Governance: a principle is expanded; none is removed or redefined.
**Approval.** The maintainer approves and merges the pull request that carries this change.

### 5.0.0 (2026-10-17): a person's yes may come through the terminal, an MCP form or the confirmation page

**Rationale.** Until now "the user confirmed it" meant one thing: `y` typed at the question of
`abf-platform launch`, on a real terminal. The platform is now reached by an MCP client (Claude
Desktop, Claude Code, Codex) that cannot show that question, and a launch asked for there would
either be impossible or be answered by the model itself, which receives "needs confirmation" and
can decide the user agreed (`docs/adr/0006`, "The yes must come from a person"). In his words on
2026-10-17: 「正式上線後：不管用 Claude Desktop、Claude Code、Codex 還是平台網頁，送出前都跳出摘要頁（管線、樣本、跑在哪、結果放哪），我按「送出」才跑；按的必須是我本人、AI 不能代按；別人打開同一連結不能送出。」
He then chose how he logs into the page: a web password of its own, set only at a terminal by
the person (`abf-platform user passwd`), kept only as a scrypt hash; a personal access token
never logs into the web, and an `Authorization: Bearer` header never does either. So principle
I.2 and the Safety Net's launch rule now say which channels count as a person's yes.

**What changes.**
- Principle I.2: "confirmed it" becomes "confirmed it, through a channel a person operates: the
  terminal, the form of the person's MCP client, or the platform's confirmation page as the same
  logged-in user". A pending request, a token, and anything the model can answer are not a
  channel. The action layer takes the channel as one of three objects and refuses anything else
  before it opens a database; a pending request is never a confirmation (`state = confirmed` is
  required by the queue); a request that was declined, expired or refused by the queue is void
  for good.
- What the MCP tools do, exactly: `launch` and `cancel` build the terminal's bundle and screen and
  write a pending request. When the client answers its form with an accepted 送出 = true, that
  same call confirms the request and queues the job (channel ELICITED). Otherwise the call only
  leaves the pending request and names the page, whose button (channel PAGE) is pressed by the
  user who made it, after which a repeated call returns the job. The same-user check (`caller` of
  the request equals the user who pressed) applies to the page and to HTTP; stdio has no caller,
  so it does not apply there, and stdio can say yes only through a form. If the queue refuses
  after a yes, the request is void for good but its row keeps the channel and `confirmed_at`, so
  the audit still shows that a person said yes.
- I.2 gains the check that this amendment exists to hold: an unconfirmed launch is refused
  through the MCP tool *and* through the web route, not only by the action function.
- The Safety Net's launch rule names both its holders: `hooks/confirm_launch.sh` in the Claude
  Code kit (it protects only that host) and the gate of the platform's action layer (it protects
  every entry). The kit's permission `ask` rule for the two write tools is a second layer, never
  the gate.
- The honest boundary, written here and in `docs/PLATFORM.md`: an AI that can run commands on the
  person's own machine can do what the person can, including typing at the person's terminal or
  reading the person's browser. The form is open to any MCP client that holds the person's token
  and declares forms, over HTTP too (the maintainer decided on 2026-10-17 to keep it that way,
  「不好」to dropping it: 維持網路連線也能用對話框按), so a client program an AI controls can
  answer it; the token is the thing to protect. The gate stops the AI clients that reach the platform only over
  MCP, which is what a platform shared by several people has to stop.

**Sync Impact Report.** Updated in this pull request, together: `docs/PRINCIPLES.md` (the reasoning
and the history of the change), `docs/adr/0006-four-entries-one-action-layer.md` (the amendment
it promised has landed, and how the three channels work), `docs/PLATFORM.md` (the confirmation
page, `abf-platform web`, `user passwd`, the boundary), `docs/TESTING.md` (the manual checks with a
real client and a real browser), `README.md` and `CLAUDE.md` (the version they cite), `CHANGELOG.md`,
the tests that pin the version and the wording (`tests/constitution_scope_test.sh`,
`tests/platform_direction_docs_test.sh`), and the platform tests whose old expectation was "no tool
writes anything" (listed with old expectation, new expectation and reason in
`specs/009c-human-channel/ledger.md`). `docs/ROADMAP.md` still lists the waiting principle "Gates
live in the platform's action layer…"; the maintainer decides when it is struck.

**Impact on existing deployments.**
- No deployment uses a write over HTTP today (the HTTP MCP server had six read-only tools), so
  nothing that works stops working. The terminal commands behave exactly as before, byte for byte
  (`platform/tests/test_launch_cli.py` passes unchanged).
- The platform's `platform.db` is upgraded in place the first time it is opened: every earlier
  confirmation becomes `confirmed` through `TERMINAL`; no job and no hand-off row changes.
- `tokens.db` gains a `password_hash` column and a `web_sessions` table. Nothing reads them until a
  person sets a web password. `abf-platform serve` and `abf-platform mcp` do not change.
- The MCP server has eight tools instead of six; the two new ones can only write a pending request.
  A deployment that wants the confirmation page starts `abf-platform web` and sets a web password
  for each user; without it, a client that cannot show a form gets an address nobody can log into,
  and nothing is launched.

**Version.** MAJOR, under Governance: a principle (I.2) and a Safety Net rule are redefined.
**Approval.** The maintainer approves and merges the pull request that carries this change.

### 6.0.0 (2026-10-18): three agreed rules join, each with the check that holds it

**Rationale.** `docs/ROADMAP.md` keeps principles that were agreed but had no check yet. On
2026-10-18 an audit of branch `v3` found three whose checks now exist, and the maintainer
approved them, in his words: 「都沒問題，好」. Before, each was a promise in the roadmap;
after, each is a rule here with the test that holds it.

**What changes.**
- Principle I.2 gains the rule that the platform's run index can be rebuilt from Nextflow's own
  records and loses to them when they disagree (feature 008's rebuild tests).
- The Safety Net's launch rule is extended to every write tool the platform has today:
  `launch` and `cancel` (as in 5.0.0), and now `resume`, `relaunch` and `forget` (the last
  arrived with keep-submissions, PR #133, and its refusal tests came with it). A write tool added
  later must bring its own refusal test.
- The Safety Net's credentials rule gains the platform's half: a credential that arrives inside
  a run's data or an OAuth exchange is never stored. The wider wording in the roadmap ("the API
  refuses a credential field") has no check and stays there.
- Not moved, and why: "every entry reaches the same action" and "the web pages and the tools
  match one to one" wait for the parity test (011a); "a call to the platform's own tools counts
  as a session in use" waits for a scope test, since `hooks/hooks.json` matches only Seqera and
  Tower tools today; "the plugin's hooks become callers of the action layer" is not true yet,
  because `hooks/confirm_launch.sh` still stands alone. The roadmap row "gates live in the
  platform's action layer" is struck: 5.0.0 already holds it in I.2.

**Sync Impact Report.** Updated together: `docs/ROADMAP.md` (rows struck or narrowed),
`docs/PRINCIPLES.md` (history), `README.md` and `CLAUDE.md` (the version they cite), and the
tests that pin the version (`tests/constitution_scope_test.sh`,
`tests/platform_direction_docs_test.sh`).

**Impact on existing deployments.** None. No hook, script, command, skill or platform code
changes behaviour; every check named here already passes on `v3`.

**Version.** MAJOR, under Governance: Safety Net rules are redefined (made stricter).
**Approval.** The maintainer approves and merges the pull request that carries this change.

### 6.0.1 (2026-10-22): the executor and verifier are generic; this repository gives them facts

**Rationale.** The maintainer runs more than one project, and the executor's and verifier's
rules are the same in all of them; only a project's facts differ. A check on 2026-10-22 also
found that the executor's stop gate, written as a hook in `.claude/agents/executor.md`, never
fired: an executor told to stop without recording a green run stopped. The gate now lives where
it is enforced (a SubagentStop hook in the development lead's workspace, tested to block, and
the reviewer's gate check at acceptance). The maintainer approved this change, in his words:
「憲法修正我同意，開 PR 把 Roles 那句改成新位置、刪掉 repo 裡兩個舊的 executor/verifier 檔」.

**What changes.** The Roles rule no longer names `.claude/agents/executor.md` and
`.claude/agents/verifier.md`; it says the two agents are generic and read this repository's
facts in the root `CLAUDE.md`. The two files are removed. `tests/dev_workflow_test.sh` checks the
facts section and that no repo copy is left; the agents' own shape is checked in the workspace.
The roles, test cases before code, green at every stage and independent acceptance are unchanged.

**Sync Impact Report.** Updated together: `CLAUDE.md` (the roles paragraph and the facts
section), `tests/dev_workflow_test.sh`, and the tests that pin the version
(`tests/constitution_scope_test.sh`, `tests/platform_direction_docs_test.sh`).

**Impact on existing deployments.** None. The plugin never shipped or used these agents; they
serve development only.

**Version.** PATCH, under Governance: wording and file locations change; no rule changes meaning.
**Approval.** The maintainer approves and merges the pull request that carries this change.

### 6.0.2 (2026-10-24): the platform checks run through four entries, not one

**Rationale.** Since pull request #200 the platform tests run in four parts so each stays well
inside the per-test time limit: `tests/platform_test.sh` runs part 1, `tests/platform_shard_2_test.sh`
part 2, `tests/platform_shard_3_test.sh` part 3 and `tests/platform_clock_test.sh` the timing
tests. Four places in this constitution still said one file ran checks that now live in other
parts. Measured on 2026-10-24: `test_actions_layer.py` runs in part 1;
`test_resume_entrypoints.py` and `test_secrets.py` in part 2; `test_human_channel.py`,
`test_keep_submissions.py` and `test_confirm_page.py` in part 3. A reader who ran only the
named file would have skipped the check.

**What changes.** Those four places now say the checks are run by `tests/run_all.sh`, which runs
all four parts. They do not say which part holds which test, so moving a test between parts does
not make this file wrong again. The named tests, what each check proves, and every rule are
unchanged.

**Sync Impact Report.** Updated together: `tests/constitution_scope_test.sh` (new checks that the
four places name the whole suite, and the version pin) and `tests/platform_direction_docs_test.sh`
(the version pin). No other document restates these four sentences.

**Impact on existing deployments.** None. Only the wording of where checks run changes.

**Version.** PATCH, under Governance: wording changes and no rule changes meaning.
**Approval.** The maintainer approves and merges the pull request that carries this change.

### 6.1.0 (2026-10-25): a colleague far from the platform host can get a first web password

**Rationale.** The 5.0.0 amendment recorded the maintainer's choice that the web password of the
confirmation page is "set only at a terminal by the person" (`abf-platform user passwd`). A
colleague who works from another building cannot sit at the platform host, so that colleague
could never log in. On 2026-10-25 the maintainer accepted this recommendation (「照你建議」): the
operator issues a one-time temporary password at the platform host's terminal, sends it to the
person privately, and the person's first web login with it can do nothing but change it to a
password of their own.

**What changes.** The web password is still set only at a real terminal of the platform host,
and is still kept only as a scrypt hash. Besides the person's own password typed there, the
operator may issue a one-time temporary password (`abf-platform user passwd <name> --temporary`).
It expires after 72 hours, it is printed once and never logged, and a session that logged in with
it reaches only the page that changes the password; it cannot see runs or press send. A personal
access token and an `Authorization: Bearer` header still never log into the web. Principle I.2
(which channels count as a person's yes) and every Safety Net rule are unchanged: the yes still
comes from the logged-in person on the confirmation page.

**Sync Impact Report.** Updated together: `docs/PRINCIPLES.md` (the confirmation-page sentence),
`docs/adr/0006-four-entries-one-action-layer.md` (the web password paragraph),
`tests/constitution_scope_test.sh` and `tests/platform_direction_docs_test.sh` (the version
pins and a check that this entry exists). The commands and pages themselves come in the task
`temp-password` and the web task after it; neither merges before this amendment.

**Impact on existing deployments.** None until an operator uses `--temporary`. Existing
passwords and logins are unchanged.

**Version.** MINOR, under Governance: a rule is materially expanded (a second way to get a first
web password); no principle or Safety Net rule is removed or redefined.
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

**Version**: 6.1.0 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-10-25
