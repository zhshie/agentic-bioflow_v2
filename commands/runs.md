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

   **`ONLINE - Platform lists 0 report(s)` is not a verdict on this
   deployment.** Platform fills its Reports tab by matching the pipeline's own
   `tower.yml` against files under `outdir`, and that manifest goes stale
   upstream: nf-core/ampliseq 2.18.0 and rnaseq 3.26.0 both name paths at the
   `outdir` root for files the pipeline publishes into a subdirectory. Every
   file is there and correct; nothing matches, on any deployment, cloud
   included. **Read the pipeline's `tower.yml` at that revision before
   suspecting the agent, the outbound channel or the compute environment** —
   PITFALLS 3e has the measured case. Then deliver from the filesystem, which
   step 3 does anyway, and tell the user the gap is upstream packaging rather
   than a lost result.

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

3. **Deliver, as a table.** Naming a few files in prose was how this was done
   before, and it kept coming out different each time: a path with no purpose
   beside it, or a purpose with no way to open the thing. Four columns, one row
   per output that matters:

   | Column | What goes in it |
   |---|---|
   | Purpose | what the next step actually does with it — not what it contains |
   | Path | relative to `results/` |
   | How to open it | a browser, a spreadsheet, or code on the user's own machine |
   | Warning | known-bad outputs, when there are any |

   Say where the grouping metadata lives, in the same table.

   The last column is not padding. A run can succeed and still produce an
   output that lies: differentialabundance 2.0.0 exports volcano plots labelled
   `higher in null` in both directions while its HTML report has the directions
   right (PITFALLS 15). Delivering that PNG without the warning hands over a
   figure that says the opposite of the result.

   **Read the file, do not just list it.** Whether that needs a copy is the
   site's business, not this command's: `scripts/fetch.sh <path>` prints the
   path to read. Where the deployment runs on the site it prints back what it
   was given and copies nothing; elsewhere it brings the results over first. It
   refuses an oversized path rather than starting a transfer that will not
   finish, so pass it `results/`, never the work directory beside it.

4. **Offer cleanup of `work/` only**, and only with explicit confirmation.
   Never `rawdata/`, `results/`, `analysis/`, `_references/`, the shared image
   library, or `.nextflow/plugins/`.
