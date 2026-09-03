# Where this stands

Written 2026-09-03. Read `PITFALLS.md` first — this file only covers what is
unfinished.

## What is proven

Six nf-core pipelines have run on NCHC through Seqera Platform with **no
per-pipeline configuration**: rnaseq 3.26.0, ampliseq, fetchngs,
differentialabundance, bacass, funcscan — every one SUCCEEDED. That was the
point of v2 — a new pipeline is launched, not configured — and it now has
evidence rather than an argument.

The box mapping in `configs/nchc.config` placed tasks in five different
partitions across those runs (ngs7G through ngs92G) without ever being told
what a label means. Two site-wide problems surfaced from the last two
pipelines and were both fixed in that same file, blind to which pipeline hit
them:

- `executor.jobName` sanitises the SLURM job name (funcscan tags a task
  `sample|model`; NCHC's sbatch rejects `|`).
- `ezlab.org` on the relay allowlist (BUSCO's download host is compiled into
  the tool, so no static scan could have found it — see PITFALLS 4g).

## The one open decision

**`executor.jobName` is not yet in the compute environment.** The last two runs
carried it with `tw launch --config /work/u9613010/lab_runs/_exttest/jobname.config`,
which is additive and left the environment untouched. Every launch needs that
flag until this is resolved.

Folding it in permanently means `tw compute-envs import --overwrite`, which
**deletes and recreates the environment under a new ID** (PITFALLS 13) — the
Launchpad entries pointing at the old ID have to be repointed afterwards. It
needs the user's explicit approval; an earlier attempt was refused by the tool
classifier and was not worked around.

Everything is staged for it:

| | |
|---|---|
| backup of the current CE | `/work/u9613010/lab_runs/_agent/ce-v2-backup-1013.json` |
| the replacement, with `jobName` folded in | `$CLAUDE_JOB_DIR/tmp/ce-v2-new.json` — **regenerate this**, the job dir is deleted with the job |
| the additive stopgap | `/work/u9613010/lab_runs/_exttest/jobname.config` |

## Still to do

- Wire `scripts/check_egress.py` into `commands/launch.md` as a pre-flight
  step. The script exists and works; nothing calls it yet.
- Review `commands/{setup,launch,runs}.md` (173 lines) against
  `mattpocock-skills:writing-for-agents`.
- M4, unstarted: downstream DESeq2/R; submit `configs/nchc.config` as a PR to
  nf-core/configs (no Taiwanese institutional config exists upstream, and this
  one is structurally the same as `nci_gadi`); repoint `HX816Lab/Xiao-He`
  marketplace.json at v2; a watchdog for the relay and the agent, which are two
  long-lived processes on a login node that reboots.

## Report the agent corruption upstream

PITFALLS 3b is a data-integrity bug in Seqera's own product: every binary file
the Tower Agent serves has its `0xFF` bytes deleted, and a doubled `0xFF` ends
the transfer. It is silent — text reports arrive perfect. The measurement table
in that entry is a complete reproduction report and has not been sent to Seqera.
