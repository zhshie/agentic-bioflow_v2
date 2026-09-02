# agentic-bioflow v2

Run Nextflow/nf-core pipelines through **Seqera Platform**, from Claude Code.

Platform does the work it is good at — submitting the head job, tracking state,
collecting task metrics, serving reports. This plugin adds only what Platform
cannot do for a firewalled HPC cluster, and three commands that follow Platform's
own object model.

| Command | Seqera equivalent |
|---|---|
| `/agentic-bioflow:setup` | compute environments, credentials, Launchpad |
| `/agentic-bioflow:launch` | pipelines → datasets → launch |
| `/agentic-bioflow:runs` | runs |

## What is actually custom here

**`configs/nchc.config`** — NCHC's QOS enforces a resource *floor*, and for most
partitions the floor equals the ceiling: a partition is a fixed-size box. Ask for
less and the job never schedules, with no error anywhere and Platform still
reporting RUNNING. Nextflow offers `resourceLimits` for the ceiling and nothing
for the floor, so this config rounds each request up to the smallest box that
fits, using dynamic `queue`/`clusterOptions` closures — the same idiom as
`nci_gadi` and `vsc_kul_uhasselt` upstream.

It keys off the **composed** request (`task.cpus`/`task.memory`/`task.time`),
never off label names. nf-core labels are partial and stackable, and a
label→partition table goes stale the moment a pipeline adds one. Because of
this, a pipeline the config has never seen still lands in a valid box, with no
configuration from the user.

**`scripts/nf_relay.py`** — compute nodes have no route out. This is a small
CONNECT proxy on the login node, restricted by reverse-DNS peer check and a
domain allowlist. Its log is the only place a blocked request is visible; the
errors that reach Platform point elsewhere.

**`docs/PITFALLS.md`** — everything that cost a failed run.

Everything else is deliberately not built: no submission script, no run-state
machine, no monitoring daemon, no per-pipeline parameter specs. Platform,
`nextflow_schema.json` and `assets/schema_input.json` already provide them.

## Requirements

- Seqera Platform workspace with a `slurm-platform` compute environment
- `tw` CLI, Java 21 for `tw-agent.jar`, Nextflow
- `LAB_RUNS_DIR` pointing at the execution area on shared storage
