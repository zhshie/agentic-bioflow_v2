# Pitfalls

Every entry below cost a failed run or a wrong assumption that had to be walked
back. They are written in the order you are likely to meet them.

## Setting up the agent

**1. The `tw-agent` native binary will not install here.** It needs glibc
2.32/2.34; Taiwania-3's login nodes have 2.28. Use `tw-agent.jar` instead — but
the jar needs **Java 21** (`UnsupportedClassVersionError: class file version
65.0 vs 61.0`) and the cluster only offers 17 and 8. Install a private Temurin
21 and point *only the agent* at it; leave Nextflow's Java alone.

**2. Create the agent credential only while the agent is already running.**
`tw credentials add agent` fails with "The agent is not online" otherwise.

**3. An offline agent makes every run's output look like it does not exist.**
The run itself is unaffected — Nextflow is on the compute nodes and finishes
normally — but Platform serves HPC reports *through* the agent, so the Reports
tab is empty and the API says:

```
GET /workflow/<id>/reports  →  400
{"message":"No online agent. Check that Tower Agent is running at your cluster."}
```

Run `scripts/agent_ctl.sh online <runId>` before concluding that outputs are
missing. The agent is deliberately started with nohup + a pid file rather than
tmux: an earlier tmux-based setup died with its tmux server while the relay,
started the other way, survived — two daemons with two survival mechanisms, and
the one that died was the one Platform needs.

## Reaching the internet

**4. Compute nodes have no route out; everything goes through the login-node
relay, and one missing domain kills the whole run.** There is no published list
to copy — the allowlist was assembled by watching runs fail. Two entries are
worth calling out:

- `nextflow.io` — Nextflow resolves plugins from `registry.nextflow.io` at
  startup. Blocked, it throws
  `java.util.UnknownFormatConversionException: Conversion = '4'`, which is pf4j
  treating the "403" in the response body as a format specifier. The message
  has nothing to do with the cause.
- `galaxyproject.org` — every nf-core Singularity image lives on
  `depot.galaxyproject.org`.

When a run fails for any network-shaped reason, read the relay log *first*:

```bash
grep DENY-DOMAIN "$LAB_RUNS_DIR/_relay/relay.log" | tail -20
```

**5. `tw launch --config` is additive, not a replacement.** Platform uploads the
file and appends `includeConfig 'https://api.cloud.seqera.io/ephemeral/…'`
*after* the compute environment's own config, so it wins on conflicts and you
only need to send the difference. The side effect: the head job fetches that URL
at startup, so `seqera.io` must stay on the allowlist or your config silently
does not apply. `--params-file` works the same way.

## Resources

**6. NCHC's QOS is a floor, and for most partitions the floor equals the
ceiling.** `sacctmgr -nP show qos format=Name,MinTRES,MaxTRESPerJob` shows
`MinTRES == MaxTRESPerJob` — a partition is a fixed-size box. Ask for less than
the box and the job never schedules: it sits at `QOSMinCpuNotSatisfied` or
`QOSMinMemory` while hundreds of CPUs sit idle, with no error anywhere. Platform
keeps reporting the run as RUNNING. Only `scontrol show job <id>` reveals it.

Nextflow provides `resourceLimits` for the ceiling and has no equivalent for the
floor, which is what `configs/nchc.config` supplies.

**7. Map the composed request, never label names.** nf-core labels are partial
and stackable — `process_long` sets only `time`, `process_low_memory` only
`memory`, `process_gpu` neither — and one process may carry two of them. A
label→partition table is also a maintenance trap: rnaseq 3.14 used six labels,
3.26 added `process_low_memory` at **1.GB**, below every partition minimum here.
The config keys off `task.cpus`/`task.memory`/`task.time` instead, so a pipeline
it has never seen still lands in a valid box.

**8. Setting `resourceLimits` too low is as fatal as too high.** Capping memory
at 92 GB turns a 200 GB request into a 92 GB one, which then needs 14 CPUs on
`ngs92G` and strands if it does not have them.

**9. Turn Platform's resource optimization off.** It right-sizes from run
history, which fights fixed-size boxes — a "helpfully" reduced request lands
below the floor and stalls. Use `tw launch --disable-optimization`.

## Launching

**10. `tw launch <short-name>` only resolves pipelines registered in the
workspace.** Otherwise pass the full GitHub URL, or register it first with
`tw pipelines add`.

**11. Nextflow's work directory must be on a filesystem the compute nodes can
see.** A work dir under the login node's `/tmp` produces jobs that fail before
the task script runs, leaving no `.command.log` and no `.exitcode` — only a
bare exit 1 in `sacct`.

## Do not rebuild what nf-core already does

**12.** Before writing a check, read the pipeline's module source. Three checks
were written and then deleted after the fact:

| Check | Already handled by |
|---|---|
| Warn on a GTF with no `gene_biotype` | `WorkflowRnaseq.biotypeInGtf()` warns and skips biotype QC (rnaseq#460) |
| Compute STAR `--genomeSAindexNbases` for a small genome | `modules/nf-core/star/genomegenerate` computes `min(14, log2(len)/2-1)` in its else branch — passing the value in `ext.args` actually *disables* that |
| Build a samplesheet from a FASTQ directory | `bin/fastq_dir_to_samplesheet.py`, for rnaseq. Note it ships **only** with rnaseq; six other pipelines checked have no equivalent |

The one reference check worth keeping is narrower: confirm that whatever
`--gtf_extra_attributes` names actually appears on `exon` lines. The default is
`gene_name`, which many RefSeq GTFs do not carry, and the result is a silently
empty column in the counts matrix rather than an error.
