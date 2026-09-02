---
description: Check on, debug, or deliver a pipeline run
argument-hint: [run id or name]
---

Seqera Platform is the only source of truth for run state. Start there, then add
the two things Platform cannot see: this cluster's scheduler, and the relay log.

`tw runs list` if no run was named. Then branch on status.

## RUNNING

`tw runs view -i <id> tasks` for per-task progress.

**A task sitting in `SUBMITTED` is the failure mode to watch for.** Platform
keeps reporting the run as RUNNING and shows no error. Confirm and explain it:

```bash
squeue -u "$USER" -h -o "%i %R" | grep -E "QOSMin|QOSMax"
scontrol show job <jobid> | grep -E "Reason|ReqTRES"
```

`QOSMinCpuNotSatisfied` / `QOSMinMemory` means the request fell below the
partition's floor and the job will never start, however long you wait. With
`configs/nchc.config` in place this should not happen; if it does, the config's
box table has drifted from the cluster — run `scripts/check_partitions.sh`.

## FAILED

**Read the relay log first**, before the Nextflow log:

```bash
grep DENY-DOMAIN "$LAB_RUNS_DIR/_relay/relay.log" | tail -20
```

Two of the four failures during this system's bring-up were a missing domain in
the allowlist, and in both cases the error Platform reported pointed somewhere
else entirely — a blocked `nextflow.io` surfaces as
`UnknownFormatConversionException: Conversion = '4'`. If a DENY lines up with
the failure time, that is the cause: add the domain, restart the relay, and
relaunch.

Otherwise: task status via `tw runs view -i <id> tasks`, then the failing task's
`.command.err` and `.command.log` in its work directory, then
`tw runs view -i <id> download --type log`.

If a task failed with no `.command.log` and no `.exitcode` at all, the work
directory is probably not visible from the compute nodes.

## SUCCEEDED

1. **Check the agent is online first** — `scripts/agent_ctl.sh online <id>`.
   Platform serves this cluster's outputs through the agent; with it down the
   Reports tab is empty and the outputs look like they were never produced.
   Never tell the user an output is missing without checking this.

2. **Read the QC, do not just link it.** Open the MultiQC data files and report
   per-sample numbers: mapping rate, duplication, and — where the pipeline
   inferred something automatically, such as `strandedness: auto` — the evidence
   behind the inference and whether samples agree. Say plainly whether any
   sample should be dropped.

3. **Deliver.** Name the exact files that matter for the next step (counts
   matrix, MultiQC report) and where the grouping metadata lives.

4. **Offer cleanup of `work/` only**, and only with explicit confirmation.
   Never `rawdata/`, `results/`, `analysis/`, `_references/`, the shared image
   library, or `.nextflow/plugins/`.
