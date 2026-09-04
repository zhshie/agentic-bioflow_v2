# Where this stands

Written 2026-09-04. `PRINCIPLES.md` says what decides; `PITFALLS.md` says what
has already gone wrong. This file is only what is unfinished.

The plan this follows is `~/.claude/plans/majestic-sparking-prism.md` — read it
for the stage numbering used below.

## What is proven

Six nf-core pipelines have run on NCHC through Seqera Platform with **no
per-pipeline configuration** — rnaseq 3.26.0, ampliseq, fetchngs,
differentialabundance, bacass, funcscan — every one SUCCEEDED. That was the
point of v2: a new pipeline is launched, not configured.

SUCCEEDED there is the workflow status, and two of the six carry an ignored
task failure inside it: ampliseq's `QIIME2_DIVERSITY_ADONIS` and funcscan's
`AMPCOMBI2_PARSETABLES`, both on nf-core's own test data, both swallowed by the
pipeline's own `errorStrategy`. Nothing to fix here — but a reader counting
green ticks in a trace file should know why two of them do not add up.

Since then the engine has been made into something a stranger could install:
eight invariants in `PRINCIPLES.md` each with a check, five of them scripts in
`tests/`; site machinery behind `docs/SITE_ADAPTER.md`; nothing pointing at one
person's directories. It is installed as a plugin from marketplace
`agentic-bioflow-v2`, now **2.0.3**.

## Stage 4 is done

Installed, restarted, and walked as the first user. What that established:

- both hooks fire in plugin form, which had never been tested — the launch gate
  on a real `tw launch`, the deletion guard on a real `rm`. File existence is
  not evidence: `${CLAUDE_PLUGIN_ROOT}` only resolves once installed
- the six tests are green
- the cold-start walk found three bugs, all fixed, all of the same shape: a
  check that reported success without having checked, and a script that refused
  before reading the file holding its answer

Then a fresh session ran it for real, with no slash command, and that closed
two more rows. `/launch` was reached by "I want to run RNA-seq" alone. The
launch gate fired **four times**, once on a `tw launch` buried behind
`export ...; source ...;` and a pipe — the segment-splitting case it used to
miss — with no precondition warnings, which means the hook's own shell had
`LAB_RUNS_DIR` and passed the egress and agent checks. The run
(`sclerotia-d0-ck-vs-syncom`) SUCCEEDED; its `work/` is 59 GB, which is the
number to plan disk around. **No per-user `/work` quota could be established**
— it is NFS, and `quota` reports only `/home`.

The cold-start method is the thing worth keeping. Point `LAB_RUNS_DIR` and
`LAB_SETTINGS_FILE` at an empty area and run the read-only paths — never
`start`, which would raise a second agent against the same connection (3c).
Evidence in `/work/u9613010/lab_runs/_coldstart_s4`, 14K.

**What Stage 4 has not closed:** the verification row that ends it — walking
`/setup` through to a `-profile test` SUCCEEDED. That is a real run and needs
a person to confirm it.

## Stage 6 is done

`check_egress.py` and `preflight.sh` are called from `launch.md`, and the three
command documents have been reviewed with `mattpocock-skills:writing-for-agents`.
The review changed one thing, and it was not a wording problem: **the command
layer typed `tw` without a workspace.** Every script resolves it
(`TOWER_WORKSPACE_ID`, else `workspace_id` from the settings file); the commands
never said to. `tw` then answers from the caller's personal workspace and
returns an *empty list rather than an error*, which is the same reply a
populated workspace gives when you are outside it. `tests/` locks it, and
PITFALLS 3c was corrected against the agent log — see that entry.

The rest of the review found nothing worth changing. Noted so the next reader
does not redo it: the three-line path preamble is duplicated in all three files
because commands load independently, so there is nowhere shared to put it; the
prohibitions that remain (`never a branch`, `never rawdata/`) are hard
guardrails already paired with the positive instruction, which is the form the
skill asks for.

## Stage 5 is done

`nf-core/differentialabundance` 2.0.0 on the D5 salmon counts, CK vs SynCom,
n=3, through `/launch`: run `vzbJ2rDMg3cud`, SUCCEEDED in about four minutes.
Deliverables in `/work/u9613010/lab_runs/diffabundance_sclerotia_d5_20260904`,
25 MB. 8,873 genes tested after filtering, **951 differential** at
`padj < 0.05` and `|log2FC| >= 1` (412 up in SynCom, 539 down). PC1 carries
55.6% and separates the two groups cleanly.

**The batch question is closed, and the answer needed no guessing.** The user
says the three replicates were one batch; the FASTQ headers say all six
libraries are `LH00242:165:22YMKFLT3` **lane 6** with distinct dual indexes —
CK and SynCom were pooled and sequenced side by side. So batch does not
coincide with group, there is no batch variable with variation to model, and
the design is `~ condition` with no `blocking` column. Within-group CV is 0.23
(CK) and 0.24 (SynCom), which is ordinary biological replication, not
technical.

What the run cost in judgement, both recorded in `PITFALLS.md`: the GTF trap
reappeared through different parameters (14, now measured per line type), and
2.0.0 exports volcano PNGs labelled `higher in null` (15, upstream, reproduced
with nf-core's own test data; the HTML report is unaffected).

`preflight.sh` earned its place here: it caught a dead agent **before** the
samplesheet was built, which is the order `launch.md` prescribes.

## The next thing to do

1. **Finish Stage 4**: `/setup` to a `-profile test` SUCCEEDED. The last
   verification row anywhere, and it needs a person.
2. **`configs/sites/nchc.config` as a PR to nf-core/configs.** No Taiwanese
   institutional config exists upstream and this one is structurally
   `nci_gadi`.
3. **Report PITFALLS 15 upstream.** That entry is already a complete
   reproduction report: the wrong expression, the file and line, and the fact
   that nf-core's own test data reproduces it.

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
