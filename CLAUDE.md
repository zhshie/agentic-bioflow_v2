# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Claude Code plugin (`agentic-bioflow`) that runs Nextflow/nf-core pipelines
through **Seqera Platform** on a firewalled HPC cluster (NCHC Taiwania-3, the
one site adapter that exists). Platform is the execution backend 2.17.0 uses;
the truth about a run underneath it is Nextflow's own records (constitution
6.0.0, principle 2; the planned platform is ADR 0004); this plugin supplies only what Platform cannot
do for a cluster whose compute nodes have no route out: rounding resource
requests up to the site's QOS floor, and proxying egress.

Read `.specify/memory/constitution.md` before changing anything structural —
it is the single statement of what this project will and will not do, each
invariant with the check that holds it, and it outranks every other file here.
`docs/PRINCIPLES.md` keeps the reasoning and history behind each invariant
(same numbers); re-deriving that reasoning from scratch has already produced
wrong answers more than once. Read
`docs/PITFALLS.md` when something breaks, not preemptively — it is a log of
real failures, each with the fix.

## Repository layout

- `skills/` — the five flow skills (`setup`, `launch`, `runs`, `downstream`, `finish`, each a `SKILL.md` in Agent Skills format, exposed as slash commands in Claude Code) and `operational`. Three follow Seqera's own nouns
  (`setup`, `launch`, `runs`): compute environment →
  pipelines/datasets/launch → runs. Two more cover what happens after a run
  finishes: `downstream` from a SUCCEEDED run to accepted figures, and
  `finish` from those to a package that can be sent somewhere. **Both carry
  no pipeline-specific knowledge, which is the condition under which either
  was allowed to exist** — `tests/no_per_pipeline_config.sh` scans them by
  name, so read their own headers before changing them. These are prose
  procedure files read and followed by Claude, not code.
- `skills/operational/SKILL.md` — the same operational knowledge, reachable
  without a slash command ("I want to run RNA-seq" should work identically).
- `scripts/` — the portable substance: site operations as shell/Python, each
  runnable standalone by a person or another model. One script, one job.
- `configs/sites/` — per-site Nextflow config (currently `nchc.config` +
  `nchc-ce.json.in`, the compute-environment template).
- `hooks/` — `confirm_launch.sh` (gates anything that can start a run behind
  an explicit confirmation and surfaces broken preconditions; also asks before
  an identity setting such as `agent_connection` is changed from an existing
  value, or before the agent/relay is started or stopped on the shared login
  node), `confirm_cleanup.sh`
  (guards destructive deletes), `confirm_walkthrough.sh` (refuses a step whose
  prerequisite step left no evidence in the transcript, and, as G7, a params file
  that carries a credential - always, the escape phrase does not lift it),
  `session_start.sh`
  (reports in-flight runs), `plugin_intro.sh` (shows the plugin overview the
  first time the plugin is used in a session - a typed `/agentic-bioflow:`
  command or a loaded plugin skill - not at every session start),
  `guard_plugin_files.sh` (refuses edits to the installed plugin itself; the
  Bash half is best effort), `next_step.sh` (a Stop
  hook: while a command flow is open, a reply that ends without a next step is
  sent back to add one). The three safety nets **refuse when `jq` is missing or
  broken** rather than falling silent — PITFALLS 28.
  `in_use.sh` (sourced by every hook above, not a hook itself) answers "is the
  plugin in use for this call?": every hook asks it first and exits silently
  when the answer is no (Constitution 2.0.0, Safety Net). In use = the session
  has a marker `plugin_intro.sh` wrote, or the folder is inside the deployment,
  or the call itself names a plugin script, `tw` or a Seqera MCP tool; unsure
  counts as in use. A hook change that adds a new early exit must keep that
  order: in-use check first, nothing forked before it (#34).
- `.specify/` — Spec Kit: `memory/constitution.md` (what decides), plus the
  templates and scripts behind the `/speckit-*` commands.
- `docs/` — `PRINCIPLES.md` (why the constitution says what it does),
  `ROADMAP.md` (stages, and principles waiting for a check),
  `POSITIONING.md`, `adr/` (architecture decisions), `PITFALLS.md` (what went wrong),
  `SITE_ADAPTER.md` (the site contract), `SETTINGS.md` (the per-deployment
  settings file schema), `DOWNSTREAM.md` (worked examples of what an outputs
  inventory turns up, measured from a real run), `CONDITIONS.md` (every user
  condition and whether it is supported, blocked or recognised-but-unsupported),
  `LAB_AGENTS.md` (which agent hosts may touch what, and why the limit is the
  site's 2FA rather than WSL), `RECORD_ADAPTER.md` (the record-system contract;
  only `none` exists), `HANDOFF.md`.
- `scripts/detect_conditions.sh` + `scripts/report.sh` — invariant 10: which
  cell of `docs/CONDITIONS.md` this machine is in, and the one off-design
  procedure's record-and-report step (whitelisted fields only; the maintainer
  designs it in instead of filing it).
- `scripts/input_checksums.sh` — SHA-256 of a samplesheet's inputs, reusing a
  lab's existing list first; `scripts/record_adapter.sh` — the record-system
  contract's `none` implementation. Every script names the existing tool it is
  not (`tests/scripts_name_their_alternative.sh`).
- `scripts/utils/portable.sh` — one place that knows how this machine differs
  from the one the scripts were written on (BSD vs GNU `stat`, a missing
  `timeout`, `readlink -f`). Sourced through `scripts/settings.sh`, so almost
  everything gets it for free. The two safety-net hooks deliberately do **not**
  source it — a gate that vanishes with a missing helper is worse than one
  never written — and inline their own few lines instead.
- `scripts/intro.sh` + `scripts/intro/<lang>/` — what the user is shown: the
  plugin overview (on first use per session) and each command's own opening (what it does,
  what they decide, what it will not do, what they end up with, what is next).
  The script holds no sentences; the text lives in the language directories,
  picked by the settings key `language` (default `zh-TW`).
- `scripts/status.sh` — the "where you are" card: this machine, both sides of
  the deployment, setup progress, and one concrete next step. It calls
  `preflight.sh`, `settings.sh --summary` and `inspect_sides.sh` rather than
  re-checking anything itself.
- `scripts/inspect_sides.sh` — what exists on the site and what exists on this
  machine, gathered in **one** `on_site.sh` round trip. `setup` decides "new
  install / adopt / repair" from this instead of from a question.
- `scripts/where.sh` — every absolute path this deployment might read or
  write **on this machine**, each marked exists/missing; purely read-only.
  `status.sh` and `setup`'s repair branch reference it instead of re-deriving
  the same paths. `where.sh --run-paths <project> <run>` is the stable
  interface another script (e.g. `prepare_launch.sh`) can query for the
  site-side run directory and the local fetch destination without
  re-deriving the run-area shape a second time. `where.sh --project-paths
  <project>` (T29) is the same idea for `rawdata/`/`runs/`/`analysis/`/
  `submission/` on the local side, whose shape branches two ways (the old
  `<seqera_user>`-layered layout for a project already living there, the
  current one for a new project) - `skills/downstream/SKILL.md` and
  `skills/finish/SKILL.md` ask it rather than constructing a path themselves.
- `scripts/settings.sh --use`/`--migrate`/`--reconstruct` — **T30: one root
  the user names** (`docs/SETTINGS.md`), holding `config/env.yaml`, the
  token, `config/machines/<machine id>.yaml` for the keys that cannot
  travel (the id is this environment's own, kept beside the root pointer -
  006), and `projects/`. `--use <root>` points this machine at it,
  creating it if it is not there yet, so a second machine is one command
  rather than a second onboarding; `--migrate <root>` is the one-time move
  off the pre-T30 locations, which are no longer read; `--reconstruct`
  rebuilds candidate values from Seqera Platform when there is nothing to
  migrate. `scripts/portable_root.sh` and `--adopt` are gone - the root is
  the portable folder, so there is no second concept to keep in step.
- `tests/` — standalone bash/python scripts, one file per invariant or script.
  Each prints ok/FAIL per case, is self-contained, and signals the verdict with
  its exit code. `tests/run_all.sh` runs all of them and is the release check;
  a single file still runs directly with `bash tests/<name>.sh`. T20 (2.18)
  added `.github/workflows/tests.yml`: ubuntu-latest, `jq` installed first,
  then `bash tests/run_all.sh`, on every PR and every push to `main` — CI
  running the same command a contributor runs locally, nothing more.

## Running tests

```bash
bash tests/run_all.sh                    # all 73, ~100s, one verdict + exit code
bash tests/run_all.sh --only confirm_    # just the safety-net gates
bash tests/confirm_launch_test.sh        # one file, full output
```

`run_all.sh` resolves its own root, so `bash <deployed-root>/tests/run_all.sh`
tests the **deployed** copy — that is the post-deploy half of the release check
in `docs/TESTING.md`. It prints the root and version it is testing, because a
green run against the wrong tree is exactly what that step exists to catch.

Two that answer questions the others cannot:

```bash
bash tests/portable_userland.sh    # GNU-only spellings anywhere they can run on a Mac
bash tests/bsd_userland_test.sh    # the same code against a stubbed BSD userland
```

`tests/relay_connect_test.py` is a manual probe, not one of these: it takes a
host and a port and needs a live relay.

Tests that exercise `on_site.sh`/ssh behavior support dry-run env vars
(`ON_SITE_DRY_RUN=1`) so they run with no host, no network, and no real site —
check the test file's header for the specific knobs it uses.

## Architecture: the site adapter

The command layer (`skills/*/SKILL.md`) is written to be **site-neutral** — it may
not name a scheduler, a partition, a queue, or a relay. It asks the adapter
"what does the site need," and a site supplies six contracts (resource
mapping, egress + refusal log, outputs-reading bridge, storage, a way to ask
why a task is stuck, and `reach`: `none`/`local`/`ssh`). Full contract in
`docs/SITE_ADAPTER.md`; `tests/command_layer_is_site_neutral.sh` enforces the
neutrality. NCHC's implementation:

| Contract | Script/config |
|---|---|
| Resource floor | `configs/sites/nchc.config` — keys off composed `task.cpus`/`task.memory`/`task.time`, never label names |
| Egress | `scripts/nf_relay.py` (CONNECT proxy), `scripts/egress_ctl.sh`, `scripts/check_egress.py` |
| Outputs bridge | `scripts/agent_ctl.sh` (Seqera Tower Agent) — binary files it serves are corrupt; read images from disk |
| Diagnosis | `scripts/why_pending.sh`, `scripts/task_health.sh` |
| Reach | `scripts/on_site.sh` — the *only* sanctioned way to run something on the site; the command layer may never call `ssh` directly |
| Drift check | `scripts/check_resource_contract.sh` |

Do not write a second site adapter speculatively — one implementation is what
exists to validate the contract; a second one is real work when there's a real
second site.

## Invariants, safety net, and how changes are made

All three are in `.specify/memory/constitution.md` and are deliberately not
restated here, so that they cannot be restated differently (constitution,
Governance). In short: invariants 1–13 each name their check; the Safety Net
section is non-negotiable within a session in which the plugin is in use, and
outside one the plugin stays silent (Constitution 2.0.0, `hooks/in_use.sh`); every non-typo change goes through the Spec Kit
feature or bug workflow, with test cases written by the independent reviewer
before any code, and merges follow the decision tiers in the constitution's
Development Workflow (2.1.0). Shared vocabulary is `CONTEXT.md`.

The roles and gates: the read-only `verifier` agent (generic, in the developer-agent's
workspace; see "For the executor and verifier") writes `test-case.md` + `test-case-overview.md`
after the plan (CONTRACT mode, following `.claude/skills/test-cases/`) and marks
them `合約已確認`; implementation does not start while the overview says
`狀態：草稿`. The `executor` agent (generic, same place) implements one
task test-first and cannot stop until the full suite is green at HEAD or it
reports BLOCKED. After implementing, acceptance is the `verifier` again
(ACCEPTANCE mode), in a fresh context - never the author's own review.
`tests/dev_workflow_test.sh` keeps this repository's half (the facts below, no stale agent
copy); the agents' own shape is checked in the workspace.

## For the executor and verifier

Since 2026-10-22 the maintainer's developer-agent dispatches **generic** `executor` and
`verifier` agents that live in its own workspace and serve every project; they read this
section first, and its facts override their defaults. This repository keeps no copy of either agent
(constitution 6.0.1). The stop gate ("green at HEAD or BLOCKED") is enforced by a
SubagentStop hook and by the verifier's gate check, not by agent frontmatter, which never fired.

- **Rules document**: `.specify/memory/constitution.md` (invariants 1–13 with their checks, the
  Safety Net, the Development Workflow and decision tiers).
- **Where things are**: features `specs/<###-feature>/` (`spec.md`, `plan.md`, `test-case.md`,
  `test-case-overview.md`, `tasks.md`); bugs `.specify/bugs/<slug>/` (`assessment.md`, fix
  record). Test-case templates `.specify/templates/test-case-template.md` and
  `test-case-overview-template.md`; how a test case is written `.claude/skills/test-cases/SKILL.md`.
  Manual steps `docs/TESTING.md`. Pitfalls `docs/PITFALLS.md`. Web design `DESIGN.md`, `PRODUCT.md`.
- **One test file**: `bash tests/<name>.sh` (works in Git Bash for most files).
- **Full suite**: `tests/run_all.sh` refuses native Git Bash; run it in WSL or Linux. From Git Bash
  on Windows, from an ASCII working directory such as `$HOME` (calling `wsl.exe` from a non-ASCII
  directory fails with "Failed to translate"; `--cd` was unreliable):
  `cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<path to the worktree> && bash tests/run_all.sh'`.
  The repo and worktrees must be on a local disk, never a synced drive. Two runs on one checkout at
  once corrupt each other's temporary copies.
- **Never edit during implementation**: `spec.md`, `test-case*.md`, the constitution,
  `docs/ROADMAP.md`, `.github/`, `.claude-plugin/plugin.json`.
- **Never run**: anything that reaches the site or HPC, launches a pipeline, deletes user data, or
  uses `~/.config/agentic-bioflow` against a real deployment.
- **Calibration failures** (real regressions the reviewer caught here; compare with the base, not
  only with the TCs):
  1. A safety-gate fix narrowed what a gate matched, and three shapes the base stopped were let
     through. Every TC passed; only re-running the old shapes against both branches showed it
     (#29, 2026-09-30).
  2. An exemption meant for one part of a compound command let the whole line through (#37).
  3. A packaging fix dropped two figures the base produced and lost the run notes (#39).
  For a change to `hooks/` or a gate, run that gate's test file on both branches and compare.

## Working conventions specific to this repo

- Every `tw` call that is workspace-scoped needs `--workspace
  $(scripts/settings.sh workspace_id)` — left off, `tw` silently answers from
  the caller's personal (empty) workspace instead of erroring.
- `tw launch` calls need `--disable-optimization` — Platform's automatic
  resource right-sizing fights a site whose accepted sizes are fixed floors.
- Paths like `scripts/...` and `docs/...` referenced from command files are
  this plugin's own files. Installed as a plugin they resolve under
  `${CLAUDE_PLUGIN_ROOT}`; read them straight from the repo otherwise.
- Pin an exact pipeline revision, never a branch, when launching or reading a
  pipeline's schema/README/diagrams — those are all read live from the
  pipeline's repo at that revision, never cached here.
- The settings file (`docs/SETTINGS.md`) lives outside this repo (on the
  login node or the user's own machine, depending on `reach`), is readable by
  the owner only — measured by reading it back, never assumed (mode on Unix,
  ACL on Windows) — and is never committed.
