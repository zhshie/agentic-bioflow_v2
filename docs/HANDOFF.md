# Where this stands

Written 2026-09-03. `PRINCIPLES.md` says what decides; `PITFALLS.md` says what
has already gone wrong. This file is only what is unfinished.

The plan this follows is `~/.claude/plans/majestic-sparking-prism.md` — read it
for the stage numbering used below.

## What is proven

Six nf-core pipelines have run on NCHC through Seqera Platform with **no
per-pipeline configuration** — rnaseq 3.26.0, ampliseq, fetchngs,
differentialabundance, bacass, funcscan — every one SUCCEEDED. That was the
point of v2: a new pipeline is launched, not configured.

Since then the engine has been made into something a stranger could install:
eight invariants in `PRINCIPLES.md` each with a check, five of them scripts in
`tests/`; site machinery behind `docs/SITE_ADAPTER.md`; nothing pointing at one
person's directories. It is installed as a plugin from marketplace
`agentic-bioflow-v2`, now **2.0.1**.

## Stage 4 is done

Installed, restarted, and walked as the first user. What that established:

- both hooks fire in plugin form, which had never been tested — the launch gate
  on a real `tw launch`, the deletion guard on a real `rm`. File existence is
  not evidence: `${CLAUDE_PLUGIN_ROOT}` only resolves once installed
- the six tests are green
- the cold-start walk found two bugs, both fixed, both of the same shape: a
  check that reported success without having checked, and a script that refused
  before reading the file holding its answer

The cold-start method is the thing worth keeping. Point `LAB_RUNS_DIR` and
`LAB_SETTINGS_FILE` at an empty area and run the read-only paths — never
`start`, which would raise a second agent against the same connection (3c).
Evidence in `/work/u9613010/lab_runs/_coldstart_s4`, 14K.

**What Stage 4 has not closed:** the verification row that ends it — walking
`/setup` through to a `-profile test` SUCCEEDED. That is a real run and needs
a person to confirm it.

## The next thing to do

1. **Restart Claude Code.** 2.0.1 is installed and not yet live.
2. **Say "I want to run RNA-seq" with no slash command, in a fresh session.**
   This cannot be tested by whoever just read this file — knowing the skill
   exists is exactly what the test is trying to exclude.
3. **Finish Stage 4**: `/setup` to a `-profile test` SUCCEEDED.
4. **Stage 5 — real data end to end.** `rnaseq_sclerotia_d5_20260902` has
   salmon counts and `sample_info.csv`: CK vs SynCom, n=3 per group, one
   timepoint. Run `nf-core/differentialabundance` through `/launch` and
   `/runs`, and ask first whether the three replicates were processed as one
   batch — if group and batch coincide, neither run nor analysis can separate
   them. The test is that no `tw` command is typed by hand. Read plots from
   disk, not Platform (3b).
5. **Stage 6 remainder**: review the three command documents with
   `mattpocock-skills:writing-for-agents`. The other two Stage 6 items —
   `check_egress.py` and `preflight.sh` called from `launch.md` — are done.
6. **`configs/sites/nchc.config` as a PR to nf-core/configs.** No Taiwanese
   institutional config exists upstream and this one is structurally
   `nci_gadi`.

Rollback is one command: `claude plugin install agentic-bioflow@agentic-bioflow`.
v1's repository and marketplace were left untouched for exactly this.

## Known and deliberately not fixed

- `preflight.sh` hardcodes `configs/sites/nchc.config`, and no settings key
  names a site config. Harmless while one site config exists, but "OK
  resources" is then a claim about somebody else's cluster. Fixing it means a
  new settings key, and `docs/SETTINGS.md` and `setup` with it.
- Every binary file Platform serves is corrupt (3b). Not reported to Seqera yet;
  the measurement table in that entry is a complete reproduction report.
- Java, the agent jar and the image cache sit under a `drwx------` home and
  `/work` subtree, so a second member cannot read them. Not a blocker — each
  member installs their own, which is the decided model — but it is why
  `install_deps.sh` puts them in the execution area instead.
- The GPU path has never been run.
- `/work/u9613010/lab_runs/_coldstart` is 362 MB of cold-start test evidence.
  Delete it when it stops being useful.
- A second member has still never installed this. Everything above is one
  person's machine.
