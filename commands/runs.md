---
description: Check on, debug, or deliver a pipeline run
argument-hint: [run id or name]
---

Paths below such as `scripts/...` and `docs/...` are this plugin's own files,
never the user's working directory. Installed as a plugin they are under
`${CLAUDE_PLUGIN_ROOT}`; read them straight from the repository otherwise.

## Before anything else

Run `scripts/intro.sh runs` and put its five sections in front of the user
before doing anything below. When this invocation's diagnosis or delivery has
been given, run `scripts/intro.sh --end runs`.

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

## Reporting format

Every diagnosis or state report below goes to the user in the same four
lines, labelled exactly this way:

    Status:          <one line - what is actually happening>
    Layer:           env | egress | scheduler | pipeline | data
    I will handle:   <what, and why>      (or)   You decide: <the options>
    Next step:       <what happens once this is answered>

The labels above are the shape, not the wording the user sees: write them in
the language `scripts/settings.sh language` reports (`zh-TW` is the default,
where they read 狀態／層別／我會處理／需要你決定／下一步). The rest of this
deployment already speaks that language — `scripts/intro.sh` opens every
session in it — and a report that switches to English mid-conversation reads
as a different tool answering.

**This formalises the 🤖/⏸ distinction used throughout this file, it does not
replace it:** a 🤖 step reports through `I will handle`, a ⏸ step through
`You decide`. Layer is never a guess — `task_health.sh` and `why_pending.sh`
(below) print their own `layer=<value>` alongside their verdict; read it from
there rather than inferring it from the symptom.

## SUBMITTED

A run that has not left the queue looks identical, from Platform's side, to
one working hard — `tw runs list` shows SUBMITTED either way, and only the
site's own scheduler can say which. Ask it the same way RUNNING does, below:

```bash
scripts/on_site.sh --script scripts/why_pending.sh
```

- **Nothing pending for this account.** 🤖 The submission likely never
  reached the site's scheduler at all — this is a launch-time failure, not a
  queue wait. Look at what `tw launch` itself returned rather than waiting
  longer for something that is not there.

      Status:          submitted to Platform, but nothing is waiting on the site
      Layer:           scheduler
      I will handle:   report this as a launch failure, not a queue wait
      Next step:       read what `tw launch` returned; the answer is there, not in the queue

- **Something is pending.** Its reason resolves exactly the way RUNNING's own
  table does, below — a SUBMITTED run waiting on a floor it will never clear
  is the same NEVER case, only caught before its first task ran. Follow that
  table and report through the same four lines.

## RUNNING

`tw runs view -i <id> tasks` for per-task progress.

**A task sitting unstarted is the failure mode to watch for.** Platform keeps
reporting the run as RUNNING and shows no error, so waiting longer looks like
the reasonable response and never is. What follows is a decision procedure,
not a checklist — take the first branch that matches and stop there.

**🤖 marks a step taken alone. ⏸ marks one that stops and asks the person.**
One rule decides which mark a step gets, everywhere in this file: **act alone
where there is a measurement or the action is reversible; stop and ask where
the choice would be a guess, or would move a security boundary.** A relaunch
counts as reversible in the sense that matters here — it resumes, and finished
tasks come back from cache rather than running again.

Ask the site why, through the adapter — the scheduler it asks only exists
there:

```bash
scripts/on_site.sh --script scripts/why_pending.sh
```

Report whichever leaf below matches in the shape above. For instance, when
the scheduler itself is the problem:

    Status:          the scheduler is not answering right now
    Layer:           scheduler
    I will handle:   wait — queued work survives this, there is nothing to fix at the run's end
    Next step:       ask again once it responds; no action needed from you

`scripts/task_health.sh <run-id>` is the tasks-table check plus this same
question, as one command — the background watch armed under launch.md step 9
should already be polling it rather than only `--status`; run it by hand here
for the same reason the watch does: silence from `--status` is not evidence
of progress.

- **The site's scheduler is not answering** (exit 3). 🤖 Report that and wait —
  queued work survives it, and there is nothing to fix at the run's end. A
  scheduler that has gone quiet does not refuse the ordinary status query, it
  makes it wait for tens of seconds, so this and a genuinely busy site look
  identical until something asks.
- **`QOSMin*`, or any answer shaped like a floor being missed → NEVER.** 🤖 The
  resource contract has drifted from what the site actually enforces; fix it
  with `scripts/ce_apply.sh` — never by waiting longer, since this request was
  never going to start.
- **The time requested exceeds what is allowed → NEVER.** 🤖 Raise the time and
  relaunch.
- **The nodes requested are unavailable → NEVER.** ⏸ Whether to keep waiting
  for them or move the request is the person's call, not this command's —
  both are legitimate and neither is reversible the way a relaunch is.
- **Waiting on resources, or on priority.** One more question decides the
  branch: is there a measurement for this process? ("Reading a measurement",
  below, says where that comes from.)
    - **Yes.** Does peak memory × 1.5 still fit inside a smaller box?
        - **Yes.** 🤖 `scripts/relaunch_with_override.sh` — the number came from
          a measurement, not a guess, so this proceeds without asking first.
        - **No.** 🤖 Say plainly that it is already as small as it can go —
          there is no smaller box to relaunch into.
    - **No.** ⏸ Propose a number with the evidence behind it, and wait for a
      reply. A number with no measurement behind it is a guess, and a guess
      that lands low is a second failure, not a faster run.

A job already sitting in the site's scheduler cannot be resized where it
sits — the site refuses that outright, for every field, including a rename
that touches no resource at all (`docs/PITFALLS.md` 6c). So once a number
needs to change, relaunching is the only route there is; it is not a
compromise, and there is nothing to build in its place. The cost is one more
spell in the queue, not the run over again.

## FAILED

**Ask what the site refused, before reading the Nextflow log** — through the
adapter, since the refusal log lives wherever the outbound channel runs:

```bash
scripts/on_site.sh --script scripts/egress_ctl.sh denied
```

Report whichever leaf below matches in the shape defined above. For instance,
when a refusal is the cause:

    Status:          the run failed; an outbound request was refused at the failure time
    Layer:           egress
    You decide:      allow <host> through the outbound channel, or leave it blocked
    Next step:       once approved — allow it, restart the outbound channel, relaunch

- **A refusal lines up with the failure time.**
    - **It is on the known-harmless list** (`docs/PITFALLS.md` 4e, 4e2). 🤖
      Rule it out and keep looking — this refusal is expected on a healthy
      run and is not the cause here.
    - **It is not on that list.** ⏸ Allowing a host through the outbound
      channel moves a security boundary, and that is not this command's call
      to make alone. Once approved: allow it, restart the outbound channel,
      relaunch.
- **No refusal lines up with the failure time.** Read `.command.err` and
  `.exitcode` for the failing task (`tw runs view -i <id> tasks` finds it;
  `tw runs view -i <id> download --type log` if the log itself is needed).
    - **137, or killed.** 🤖 See "out of memory", below.
    - **No `.command.log` and no `.exitcode` at all.** 🤖 The work directory is
      probably not visible from the compute side — report that; there is
      nothing further to diagnose from here.
    - **Anything else.** 🤖 Diagnose it fully. ⏸ Stop and ask only if the fix
      turns out to need a pipeline parameter changed — that is a call about
      the run that was requested, not about the site.

On a site with unrestricted egress the first step prints nothing and costs a
second. Two of the four failures during this system's bring-up were an
outbound request the site would not carry, and in both cases the error
Platform reported pointed somewhere else entirely — a blocked request can
surface as `UnknownFormatConversionException: Conversion = '4'`, a formatting
bug in the code that reads the rejection, not a clue about the cause. That is
why the refusal is asked about before the log, not after: reading the log
first sends the diagnosis toward whatever it names, and in this shape of
failure that is never the actual cause.

### Out of memory

This was just measured, and it corrects a belief this file used to state as
fact. This site's own resource contract adds no multiplier of its own on a
retry — the pipeline's own defaults already multiply every request by the
attempt number, and doubling it again here would compound the two together.
So **a task that dies of memory is retried automatically at double, in the
next box up**, with no config change needed:

```
attempt 1   smaller box   FAILED      137:0
attempt 2   next box up   COMPLETED     0:0
```

(measured; `docs/PITFALLS.md` 6d has the full record)

- **The retry already succeeded.** 🤖 Nothing to do. Say the run recovered by
  itself, and name the box it needed — that tells the next launch where to
  start, rather than where this one started.
- **The retry also died** (this site allows one retry, and it is now spent).
  🤖 `scripts/relaunch_with_override.sh` with a floor above what the retry
  reached. Asking for the same size again is not a smaller request, it is the
  same failure repeated.

The old wording here claimed the opposite: that a doubled request lands
between two boxes and strands, and that a genuine out-of-memory failure needs
a box moved up by hand. Neither was true, and both cost more than they saved —
they told the reader to distrust a recovery that works, and to go do by hand
the thing already happening automatically. Do not reintroduce either claim.

## Reading a measurement

Both branches above turn on whether a measurement exists for a process. This
is where it comes from — verified, not assumed:

```
tw runs view -i <id> -w <ws> metrics
  → per process: RSS, virtual memory, and the PERCENTAGE of the box used
    PICARD_MARKDUPLICATES | 19GB 34GB 54%
    QUALIMAP_RNASEQ       |  6GB 33GB 16%
    SAMTOOLS_INDEX        | 13MB 210MB  0%
tw runs view -i <id> -w <ws> task -t <n> --resources-usage
tw runs view -i <id> -w <ws> task -t <n> --resources-requested
```

The same numbers exist a second way, on the filesystem:
`pipeline_info/execution_trace_*.txt` is a TSV despite its extension, and
carries `peak_rss` and `peak_vmem` per task. These are two views of one thing —
prefer whichever is actually available.

| signal | meaning | action |
|---|---|---|
| 137 / killed, retry succeeded | recovered by itself | 🤖 report the box it needed |
| 137 / killed, retry also died | one tier was not enough | 🤖 relaunch above what the retry reached |
| ≥ 85% of the box, task failed | died against its own ceiling | 🤖 relaunch one tier up |
| ≤ 30% and waiting on resources | badly over-allocated | 🤖 down to the box fitting peak RSS × 1.5 |
| 30–85% | reasonable | 🤖 leave it; the wait is a real queue, not a sizing problem |
| no measurement at all | nothing to reason from | ⏸ propose and wait |

## SUCCEEDED

1. **Check the site can still serve outputs** — through the adapter:
   `scripts/on_site.sh --script scripts/agent_ctl.sh online <id>`.
   Where Platform reads results through something running on the cluster, that
   something being down makes every output look like it was never produced.
   Never tell the user an output is missing without checking this first.
   Read binary outputs — images, PDFs — from the filesystem regardless: what
   Platform serves for them is corrupt (PITFALLS 3b).

   If the reader is down, report it in the same shape as every other
   diagnosis in this file:

       Status:          the outputs reader is not running
       Layer:           env
       I will handle:   restart it and re-check before saying anything is missing
       Next step:       once it is back, this run's outputs will be visible again

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

4. **Offer to tune the box sizes**, now that this run has real measurements
   behind it:

   ```bash
   scripts/tune_resources.sh <run-id>
   ```

   Invariant 1 is answered unusually strongly by this one script. Platform
   already ships a resource optimiser, and this deployment must keep it off
   (`tw launch --disable-optimization`, `docs/PITFALLS.md` 9) — it right-sizes
   from run history, which is exactly wrong on a site where the acceptable
   sizes are a handful of fixed boxes rather than a range: a "helpfully"
   reduced request lands below a box's floor and never schedules at all.
   Platform's optimiser does not know the boxes exist. This is the one that
   does, and until now nothing did.

   Show the table it prints — only a process a full tier oversized appears
   with a suggested move; the rest are shown unchanged, so the reader can see
   that everything was actually checked rather than wondering what was left
   out. ⏸ **Ask whether to save it.** Saving is configuration, no different
   from a parameters file, so it does not touch run state — that stays only on
   Platform (PRINCIPLES.md, invariant 2). Only on a yes:

   ```bash
   scripts/tune_resources.sh --config --samples <n> --input-size <size> <run-id>
   ```

   and save what it prints as `<run area>/tuned/<pipeline>@<revision>.config`.
   It refuses to print anything without both numbers: the same sizing on
   materially more data is an out-of-memory failure, not a faster run
   (`docs/PITFALLS.md` 6d), so the file has to say what it was tuned against.
   Keep that line visible wherever a later launch offers this file back as
   "reuse the previous settings" — it is the difference between a shortcut and
   a trap.

5. **Offer cleanup of `work/` only**, and only with explicit confirmation.
   Never `rawdata/`, `results/`, `analysis/`, `_references/`, the shared image
   library, or `.nextflow/plugins/`.

## CANCELLED

Platform did not do this on its own — someone asked to, from `tw` or the web
UI, and this command did not do it either unless it just relaunched something
by hand. Establish which before touching anything: a cancellation can land
before, during, or after a task started, and treating it as a mistake without
asking is a decision that was never this command's to make.

    Status:          cancelled — not a failure, and not something this invocation started
    Layer:           pipeline
    You decide:      relaunch it, or leave it cancelled
    Next step:       say the word and it relaunches the same way any other run does

## UNKNOWN

`tw runs list` can report a status this file has no branch for — Platform
adding a status this adapter has not been updated to cover. Say exactly what
Platform reported and stop there rather than guessing what it implies; NEVER
and "waiting" are both claims this file makes only where a rule above already
covers the reason.

    Status:          Platform reports a status not covered above — say it verbatim
    Layer:           env
    You decide:      what to do next — this file has no rule for this status
    Next step:       tell the maintainer which status this was, so a branch can be added here
