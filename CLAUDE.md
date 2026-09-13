# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Claude Code plugin (`agentic-bioflow`) that runs Nextflow/nf-core pipelines
through **Seqera Platform** on a firewalled HPC cluster (NCHC Taiwania-3, the
one site adapter that exists). Platform is the execution backend and the only
source of truth for run state; this plugin supplies only what Platform cannot
do for a cluster whose compute nodes have no route out: rounding resource
requests up to the site's QOS floor, and proxying egress.

Read `docs/PRINCIPLES.md` before changing anything structural — it is short,
each invariant carries a check, and re-deriving the reasoning from scratch has
already produced wrong answers more than once (see its own history). Read
`docs/PITFALLS.md` when something breaks, not preemptively — it is a log of
real failures, each with the fix.

## Repository layout

- `commands/` — the slash commands. Three follow Seqera's own nouns
  (`setup.md`, `launch.md`, `runs.md`): compute environment →
  pipelines/datasets/launch → runs. Two more cover what happens after a run
  finishes: `downstream.md` from a SUCCEEDED run to accepted figures, and
  `finish.md` from those to a package that can be sent somewhere. **Both carry
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
  an explicit confirmation and surfaces broken preconditions), `confirm_cleanup.sh`
  (guards destructive deletes), `confirm_walkthrough.sh` (refuses a step whose
  prerequisite step left no evidence in the transcript), `session_start.sh`
  (reports in-flight runs), `plugin_intro.sh` (shows the plugin overview the
  first time the plugin is used in a session - a typed `/agentic-bioflow:`
  command or a loaded plugin skill - not at every session start), `next_step.sh` (a Stop
  hook: while a command flow is open, a reply that ends without a next step is
  sent back to add one). The three safety nets **refuse when `jq` is missing or
  broken** rather than falling silent — PITFALLS 28.
- `docs/` — `PRINCIPLES.md` (what decides), `PITFALLS.md` (what went wrong),
  `SITE_ADAPTER.md` (the site contract), `SETTINGS.md` (the per-deployment
  settings file schema), `DOWNSTREAM.md` (worked examples of what an outputs
  inventory turns up, measured from a real run), `HANDOFF.md`.
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
- `tests/` — standalone bash/python scripts, one file per invariant or script.
  Each prints ok/FAIL per case, is self-contained, and signals the verdict with
  its exit code. `tests/run_all.sh` runs all of them and is the release check;
  a single file still runs directly with `bash tests/<name>.sh`. No CI exists.

## Running tests

```bash
bash tests/run_all.sh                    # all 40, ~80s, one verdict + exit code
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

The command layer (`commands/*.md`) is written to be **site-neutral** — it may
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

## Key invariants (see `docs/PRINCIPLES.md` for the full list + checks)

- **Build only what neither Seqera nor nf-core already does.** Before adding
  anything, name what Seqera/nf-core already use to do the same job.
- **No file in this repo records run state.** No submission script, state
  machine, or monitoring daemon — Platform is the single source of truth.
- **Anyone can install it.** No hardcoded personal/cluster paths; everything
  derives from `$LAB_RUNS_DIR` and the deployment's settings file
  (`tests/no_hardcoded_paths.sh`).
- **Any pipeline, no configuration.** Resource mapping keys off the composed
  request, never nf-core label names; samplesheet columns come from the
  pipeline's own `assets/schema_input.json`, parameters from its
  `nextflow_schema.json` — never a curated per-pipeline file in this repo
  (`tests/no_per_pipeline_config.sh`).
- **Nobody should need the maintainer.** Onboarding (`setup`) must prove the
  environment on public test data before handing over the command list.
- **Measure or read the source before claiming.** Every `PITFALLS.md` entry
  is a real failure or a real piece of source that was read — not inference.

## Safety net (not negotiable)

Never delete a user's source data — `rawdata/`, `results/`, `analysis/`, a run
area's `_references/`, or a shared image cache. Never delete
`.nextflow/plugins/`. Deleting `work/` or `.nextflow/cache/` requires the
user's explicit confirmation (`hooks/confirm_cleanup.sh` gates this). Always
show a launch command in full and wait for explicit confirmation before
running it (`hooks/confirm_launch.sh` gates this on any `tw launch`/`sbatch`/
`nextflow run`-shaped command). Credentials and personal details belong only
in the deployment's own settings file, mode 600 — never printed, never in git,
never in a params file, never copied from another member's settings.

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
  login node or the user's own machine, depending on `reach`), is mode 600,
  and is never committed.
