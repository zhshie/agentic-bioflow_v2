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
`agentic-bioflow-v2`, now **2.0.7**.

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

Walking `/runs` afterwards - rather than reading the results by hand, which is
what closed the launch half - found the defect that made the row worth walking.
Step 2 said to open the MultiQC data files, and differentialabundance produces
no MultiQC; the instruction named one pipeline's artefact as if it were every
pipeline's. The step now asks what QC this pipeline made, and says that a
missing MultiQC is not a QC report of none. That is the fourth member of the
same family as the workspace defect: an absence read as an answer.

## v2.1 has started: step 0 is done

The plan is `~/.claude/plans/curious-doodling-lightning.md`. It moves Claude
Code off the login node and onto the user's own machine, reaching the site over
SSH, because the agent window has to be single: it will also carry lab notes,
Zotero and other tools, and those need browser OAuth that a login node cannot
give (this deployment already hit that with Seqera's own MCP).

**Step 0 shipped as 2.0.5, and it was a real hole.** Both PreToolUse hooks read
the local command string, so `ssh host '<payload>'` hid the payload from them -
a launch sailed through the gate and a delete sailed through the guard, with no
error. Moving to SSH without fixing this would have switched the safety net off
at the exact moment the plugin reached more people.

Also fixed: a read-only grep whose regex contained the delete verb was denied,
because segmenting split on the `|` inside the regex. That fired twice on me -
once while planning, once while committing the fix.

`tests/confirm_cleanup_test.sh` asserted nothing before this: it printed each
result, every label said `(expect deny)`, and no expected value was ever
compared. It asserts now.

**Step 3 shipped as 2.0.6.** The three things a user found missing next to v1 -
an opening that says what the tool is, a picture of the pipeline, and being
asked what to skip - are all back, and none of them is a file here. The diagram
is found by listing the pipeline's `docs/images/` (the four pipelines run here
name it four different ways); the skippable steps come from the schema's own
`*skipping*` group, 19 of them in rnaseq 3.14.0. `tests/no_per_pipeline_config.sh`
guards the trade and was verified red before green.

`setup.md` now forks first on what kind of compute this is: a Platform-managed
environment skips steps 5 and 6, because there is no channel to open and no
outputs reader to keep alive.

**Steps 4 and 5 shipped as 2.0.7.** `:launch` now arms a watch on the run and
on the outputs reader without asking, and a `SessionStart` hook says what is
still in flight at the top of a conversation. Neither is a daemon: the watch
dies with the conversation, the hook runs once and keeps no state, and Platform
stays the only record (invariant 2). The hook's own hazards are handled and
worth knowing before editing it - the SessionStart default timeout is **600
seconds**, so it carries an explicit 15, and **exit 2 blocks the session from
starting**, so it exits 0 on every path. It is silent on a compaction and
wherever no deployment settings file exists.

Step 5 settled two Seqera questions by measurement, in `SITE_ADAPTER.md`:
Studios refuses this compute environment outright (`Studios are not supported
by compute environment ... of type slurm-platform` — nothing was created by the
probe), and Data Explorer requires a cloud `--provider`, so a filesystem site
has nothing to register. Datasets, actions, secrets and labels all work.

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

## A second member has now installed this, from a Windows laptop over SSH

2026-09-05, `reach: ssh`, driven from WSL against `t3-c4.nchc.org.tw`, storage
kept deliberately separate from `/work/u9613010/lab_runs` at
`/work/u9613010/agentic-bioflow-test` so it could not collide with the first
member's environment. Every step of `setup.md` walked end to end, including
both proof runs, and one real analysis after: `nf-core/ampliseq` 2.18.0 against
40 public PacBio full-length 16S samples (NCBI BioProject `PRJNA1099878`), which
SUCCEEDED with results delivered back to the laptop via `fetch.sh`.

**Five real bugs came out of it, all fixed and committed** (`9c7aef7`):
`on_site.sh` dropped `egress_ctl.sh`'s sibling `nf_relay.py` when shipping only
the named script; it also carried the laptop's own `tw_bin` to the site, which
outranked `agent_ctl.sh`'s `command -v tw` fallback and broke registration;
`agent_ctl.sh` never created its own work directory, invisible until now
because the first member's run area already had one; `ce_apply.sh` used
`LAB_RUNS_DIR`-relative paths for its backup file, the token, and the egress
proxy URL, all of which are laptop-local under `reach: ssh` — the proxy URL bug
is the sharp one, since it silently builds a compute environment that points
containers at the laptop's own hostname; and the repo's shell scripts were
committed with CRLF line endings, which breaks them both under WSL and on the
site itself (`.gitattributes` added).

**Four more things were learned but are the site's or Windows's to work around,
not this repo's to fix** — all in `PITFALLS.md`: this cluster's `python3` on
PATH is a locked-down `platform-python` (16d); too many `on_site.sh` calls on
one master hang instead of erroring once sshd's `MaxSessions` is spent (16e);
`tw`'s native binary segfaults under WSL2 without `vsyscall=emulate` in
`.wslconfig` (16f); and a live agent reporting zero Platform reports for a
SUCCEEDED run can be the *pipeline's* `tower.yml` naming a stale path, not this
deployment (3e) — true of both `nf-core/ampliseq` and `nf-core/rnaseq` here.

**Those four are still not this repo's to fix, but they were this repo's to
explain, and now are.** The distinction is worth keeping: nothing here can
unlock the site's interpreter or reboot WSL's kernel, but every one of them
first appeared as an error blaming the wrong thing, which is a defect in this
repo's output whoever owns the underlying cause.

| Was reported as | Now |
|---|---|
| `Permission denied` from a failed exec (16d) | `scripts/require_python.sh`, sourced by both site scripts, names the fence and points at `module avail python` |
| Nothing at all — a call that hangs forever (16e) | Every `on_site.sh` call carries a clock, and `--check-reach` opens a real session instead of trusting `ssh -O check`, which was passing while the next command sat there |
| `could not install tw from <url>` (16f) | A signal death is told apart from a download failure and answered with the `.wslconfig` fix |
| `0 report(s)`, read as a broken deployment (3e) | `runs.md` sends the reader to the pipeline's own `tower.yml` first |

**Six gaps in the command guidance came out of the same walk**, and they are a
different class again — places where the text said nothing about a situation
the member hit, or asked for a step with nothing to notice when it was skipped.
Three of `launch.md`'s steps (the workflow diagram, the skippable-tools menu,
and the `conf/base.config` read) were skipped in the real walk with no
consequence, so step 7's confirmation now carries one line of evidence from
each: the gate the user must answer is the only place an omission is visible.
`setup.md` grew the third situation it never had — an empty *local* settings
file on a site somebody has already set up — because the second member had to
improvise it, and improvising it wrong means two agents on one
`agent_connection`, which Seqera refuses permanently. And `push.sh` now exists,
because `fetch.sh` only ever brought results back: a user whose own reads have
never left their laptop had no path at all.

## Four more, found by re-reading rather than by failing

A second pass over the same walk turned up four things that did not go wrong
and clearly could. That is a different kind of finding from everything above,
and worth naming as such: none of these cost the walk anything, so none of them
would ever have been written down by waiting.

**The list of files that travel to the site was a list.** `on_site.sh` shipped
the named script plus a hand-written set of its dependencies, and the set had
already been wrong twice — once for the `settings.sh` every site script
sources, once for `nf_relay.py`, which `egress_ctl.sh` execs by path. Both were
fixed by adding a line to the list, which fixes the instance and leaves the
class: a dependency list kept in a different file from the dependency goes
stale in silence, and nothing reminds whoever adds the next script. Measured
before deciding, because "ship everything" is only obviously right if it is
cheap: the whole of `scripts/` plus `configs/` is 120 KB raw against the old
list's 30–40 KB, and **37 KB compressed — fewer bytes on the wire than the
cherry-picked tar it replaces**. So it ships everything, gzipped, and there is
no list. `tests/on_site_test.sh` now reads the payload rather than the
intention; the assertion that `why_pending.sh` is in it, having nothing to do
with `egress_ctl.sh`, is what makes reintroducing a list fail.

**The connection identifier could not be unique, and the reported reason was
not the real one.** It was reported as two members on one login node colliding.
That is not this site's failure: `${USER}` would differ. What does not differ
here is anything else — the cluster is reached through **one shared account**,
and under `reach: ssh` the hostname is the login node's for whoever is driving
— so `${USER}-$(hostname -s)-$(date +%Y%m%d)` reduced to the date, and one
person setting up on two machines on one day got one string. The workspace
shows how close it came: its two `tw-agent` credentials differ only by work
directory, which is not part of the name. The identifier now carries four
random bytes, and `start` asks the workspace before committing — there is no
`tw agent` command, but `tw -o json credentials list` exposes
`keys.connectionId`, which is the registry. PITFALLS 2b.

Fixing it surfaced a second thing that had been hiding behind the date:
**`start` records the identifier on the machine it ran on**, which under
`reach: ssh` is the site and not where the next `start` reads its settings.
Regenerating a date-derived string produced the same answer until midnight, so
this never showed. A random one makes it fatal, so `start` now prints the
`settings.sh --set agent_connection <id>` line, and `setup.md` step 6 says to
run it — the same split step 4 already had for `install_deps.sh`'s paths.

**Every nf-core pipeline requires `--outdir` and no `test` profile sets one.**
The walk spent a full submit-through-Slurm cycle discovering this: the job
queued, reached a node, and died at parameter validation before a task existed.
`setup.md` step 8 now says to pass a scratch `--outdir` under the run area.

**`why_pending.sh` asked the slow question first.** A scheduler controller that
has stopped answering does not make `squeue` fail; it makes it wait tens of
seconds, which is indistinguishable from a busy site. `scontrol ping` answers
either way in about 20 ms and names the controller's state outright, so it now
runs first and exits 3 without going further. `runs.md` sends people to that
script to ask whether a task will *ever* start, and "the site is not answering"
is a real answer to that question and a different one.
