# Where this stands

Written 2026-09-03. `PRINCIPLES.md` says what decides; `PITFALLS.md` says what
has already gone wrong. This file is only what is unfinished.

## What is proven

Six nf-core pipelines have run on NCHC through Seqera Platform with **no
per-pipeline configuration** — rnaseq 3.26.0, ampliseq, fetchngs,
differentialabundance, bacass, funcscan — every one SUCCEEDED. That was the
point of v2: a new pipeline is launched, not configured.

Since then the engine has been made into something a stranger could install:

- the reasoning is in `PRINCIPLES.md` as eight invariants, each with a check,
  and four of those checks are scripts in `tests/`
- site-specific machinery is behind `docs/SITE_ADAPTER.md`; the command layer
  names no scheduler, no egress mechanism, no container runtime
- nothing in `scripts/`, `commands/` or `configs/` points at one person's
  directories any more — they read `_personal/env.yaml` (`docs/SETTINGS.md`)
- `install_deps.sh` fetches Java 21, the agent jar and `tw` from nothing;
  `ce_apply.sh` builds a first compute environment from a site template
- v2 is installed as a plugin, version 2.0.0, from marketplace
  `agentic-bioflow-v2`

## The next thing to do: restart, then walk it

**Claude Code has to restart before v2's hooks and commands take effect.** The
session that installed it is still running v1's hooks. There is a clean way to
tell which is live — run a command containing a quoted regex with `sbatch` in
it, such as `grep -n "slurm|sbatch|squeue" docs/PITFALLS.md`:

- **the launch gate fires** → still v1, whose gate false-positives on quoted
  regexes and whose message mentions `submit_run.sh`
- **nothing happens** → v2

After the restart:

1. `/agentic-bioflow:setup`, `:launch` and `:runs` should exist.
2. The gate must fire on a real `tw launch` — file existence is not evidence,
   because `${CLAUDE_PLUGIN_ROOT}` only resolves once installed.
3. Say something with no slash command at all — "I want to run RNA-seq" —
   and the operational skill should pick it up. This is the thing v2 had no
   answer to until recently.
4. Walk `/agentic-bioflow:setup` as if new. The bar is not that it works; it is
   that every question is answerable **without this conversation's memory**.
   Where it is not, that is the bug.

Rollback is one command: `claude plugin install agentic-bioflow@agentic-bioflow`.
v1's repository and marketplace were left untouched for exactly this.

## Then

- **Real data end to end.** `rnaseq_sclerotia_d5_20260902` has salmon counts and
  `sample_info.csv`: CK vs SynCom, n=3 per group, one timepoint. Run
  `nf-core/differentialabundance` through `/launch` and `/runs`, and ask first
  whether the three replicates were processed as one batch — if group and batch
  coincide, neither run nor analysis can separate them. The test is that no
  `tw` command is typed by hand. Read plots from disk, not Platform (3b).
- **`check_egress.py` and `preflight.sh` into `launch.md`.** Both exist and
  nothing calls them. Skipping preflight is what let a dead agent take out a
  launch this session (3c).
- **`configs/sites/nchc.config` as a PR to nf-core/configs.** No Taiwanese
  institutional config exists upstream and this one is structurally `nci_gadi`.

## Known and deliberately not fixed

- Every binary file Platform serves is corrupt (3b). Not reported to Seqera yet;
  the measurement table in that entry is a complete reproduction report.
- Java, the agent jar and the image cache sit under a `drwx------` home and
  `/work` subtree, so a second member cannot read them. Not a blocker — each
  member installs their own, which is the decided model — but it is why
  `install_deps.sh` puts them in the execution area instead.
- The GPU path has never been run.
- `/work/u9613010/lab_runs/_coldstart` is 362 MB of cold-start test evidence.
  Delete it when it stops being useful.
