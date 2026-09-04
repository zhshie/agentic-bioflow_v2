---
description: Check on, debug, or deliver a pipeline run
argument-hint: [run id or name]
---

Paths below such as `scripts/...` and `docs/...` are this plugin's own files,
never the user's working directory. Installed as a plugin they are under
`${CLAUDE_PLUGIN_ROOT}`; read them straight from the repository otherwise.

Pass the workspace on every `tw` call that is scoped to one:
`--workspace $(scripts/settings.sh workspace_id)`. Left off, `tw` answers from
the caller's personal workspace - where the lab's pipelines, runs and compute
environments do not exist - so `pipelines list` and `runs list` come back empty
and the emptiness reads as an answer. Sourcing a shell env file is not enough:
it carries the token, not the workspace.

Seqera Platform is the only source of truth for run state. Start there, then add
the two things Platform cannot see: what the site's scheduler is doing, and what
the site refused to send out. Both are reached through the site adapter
(`docs/SITE_ADAPTER.md`), never by naming a scheduler here.

`tw runs list` if no run was named. Then branch on status.

## RUNNING

`tw runs view -i <id> tasks` for per-task progress.

**A task sitting unstarted is the failure mode to watch for.** Platform keeps
reporting the run as RUNNING and shows no error, so waiting longer looks like
the reasonable response and never is. Ask the site:

```bash
scripts/why_pending.sh
```

It answers the one question that matters — will this *ever* start. A `NEVER`
means the site refuses the request as submitted, which should not happen while
the resource contract is doing its job; `scripts/check_resource_contract.sh`
says whether the contract has drifted from the site.

## FAILED

**Ask what the site refused**, before reading the Nextflow log:

```bash
scripts/egress_ctl.sh denied
```

Two of the four failures during this system's bring-up were an outbound request
the site would not carry, and in both cases the error Platform reported pointed
somewhere else entirely — a blocked plugin registry surfaces as
`UnknownFormatConversionException: Conversion = '4'`, which is a formatting bug
in the code that reads the rejection, not a clue about the cause. If a refusal
lines up with the failure time, that is it: allow the host, restart the channel
(`scripts/egress_ctl.sh stop && scripts/egress_ctl.sh start`), relaunch. Some
refusals are expected and must not be allowed — see PITFALLS 4e and 4e2.

On a site with unrestricted egress this step prints nothing and costs a second.

Otherwise: task status via `tw runs view -i <id> tasks`, then the failing task's
`.command.err` and `.command.log` in its work directory, then
`tw runs view -i <id> download --type log`.

If a task failed with no `.command.log` and no `.exitcode` at all, the work
directory is probably not visible from the compute nodes.

## SUCCEEDED

1. **Check the site can still serve outputs** — `scripts/agent_ctl.sh online <id>`.
   Where Platform reads results through something running on the cluster, that
   something being down makes every output look like it was never produced.
   Never tell the user an output is missing without checking this first.
   Read binary outputs — images, PDFs — from the filesystem regardless: what
   Platform serves for them is corrupt (PITFALLS 3b).

2. **Read the QC, do not just link it.** Report per-sample numbers, and say
   plainly whether any sample should be dropped. Where the pipeline inferred
   something automatically — `strandedness: auto`, an outlier call — report the
   evidence behind it and whether the samples agree.

   MultiQC is the usual place, carrying mapping rate and duplication. A
   pipeline that produces no MultiQC still produces per-sample QC somewhere:
   differentialabundance puts it in DESeq2 size factors, a MAD-correlation
   outlier call and a sample dendrogram, under `other/` and `plots/`. Find what
   this pipeline actually made. **A missing MultiQC is not a QC report of
   none** — it is the same shape of mistake as an empty `tw` listing read as an
   answer.

3. **Deliver.** Name the exact files that matter for the next step (counts
   matrix, QC report) and where the grouping metadata lives.

4. **Offer cleanup of `work/` only**, and only with explicit confirmation.
   Never `rawdata/`, `results/`, `analysis/`, `_references/`, the shared image
   library, or `.nextflow/plugins/`.
