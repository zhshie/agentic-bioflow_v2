---
name: runs
description: Check on, debug, or deliver a pipeline run
argument-hint: [run id or name]
---

Paths below such as `scripts/...` and `docs/...` are this plugin's own files,
never the user's working directory. Installed as a plugin they are under
`${CLAUDE_PLUGIN_ROOT}`; read them straight from the repository otherwise.

`preflight.sh`, `runs_board.sh`, `settings.sh`, `status.sh`, `tune_resources.sh`, `where.sh`
and `why_pending.sh` line their output up with runs of spaces. Relay what they
printed inside a fenced code block: outside one, a GUI surface collapses those
runs and the columns stop meaning anything (PITFALLS 35).

## Before anything else

Run `. scripts/env.sh && scripts/intro.sh runs`. Each Bash tool call is a fresh
shell, so nothing exported here survives into the next one. Put `intro.sh`'s five
sections in front of the user before doing anything below. When this invocation's
diagnosis or delivery has been given, run `scripts/intro.sh --end runs`.

Run state comes from the abf platform's MCP tools: `list_runs` for the runs it
knows (newest first, with status and task numbers), `get_run` (it takes the run's
id) for one run's status, task numbers per process, failed tasks and, for a failed
run, `failure_reason` - Nextflow's own words for why it failed. The platform
reports four statuses: running, succeeded, failed and lost. Then add the two
things the platform cannot see: what the site's scheduler is doing, and what the
site refused to send out. Both are reached through the site adapter
(`docs/SITE_ADAPTER.md`), never by naming a scheduler here.

**Actions only ask.** `cancel`, `resume` and `relaunch` (each takes the run's name,
`run_name`) do not stop or start anything: each writes a request and shows the
person what would happen, and the person says yes on their own channel - a form
in their client or a page whose address the tool returns. You cannot say it for
them. After the person has pressed send, call the same tool again with the same
`run_name` to get the job number. Wherever this file says "relaunch" or "resume",
it means asking this way.

With a run named — an id, a run name, or a code from the board below —
resolve it and branch on status. With nothing named, show the work board
first (below), then branch once the user picks one.

## The work board (`/runs` with nothing named)

Before asking about one run, find out what is actually in flight — a member
running several analyses at once should never have to open several windows
to see them all in one place:

Call `list_runs`. The runs still in flight are the ones whose status is
`running` (a launched run that has not started yet may not be listed at all;
the SUBMITTED section below says how to find it). Show each with its run name,
status, elapsed time and task numbers, and give each a short code (`r1`, `r2`,
...) in the order the tool returned them. The codes are computed fresh on every
call from the platform's own listing, never stored (`docs/PRINCIPLES.md`,
invariant 2), so a later `/runs <code>` is resolved by calling `list_runs`
again and taking the same position, then continuing with that run's id in every
branch below exactly as if the user had named the run outright. `/runs <run id
or name>` skips the board entirely and goes straight to the branch below.

One `list_runs` call covers every run, so the board costs the site nothing.
Asking the site about each run one by one would open one site session per run
(PITFALLS 16e's session cap, `ssh_max_parallel`): ask the site only about the
run the user picked.

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
`You decide`. Layer is never a guess — `why_pending.sh` (below) prints its own
`layer=<value>` alongside its verdict; read it from there rather than
inferring it from the symptom.

## SUBMITTED

Mapping: SUBMITTED = the person confirmed the launch but the run is not in `list_runs` yet; tell them "已送出、還沒開始" and check again later, at most 3 checks, and after the 3rd tell the person where it stands (never wait forever).

A run that has not left the queue looks identical, from the platform's side, to
one working hard: the platform has no "submitted" status, so a launched run that
has not started either is not in `list_runs` yet or shows as `running` with no
task done in `get_run`, and only the site's own scheduler can say which. Ask it
the same way RUNNING does, below:

```bash
scripts/on_site.sh --script scripts/why_pending.sh
```

- **Nothing pending for this account.** 🤖 The submission likely never
  reached the site's scheduler at all — this is a launch-time failure, not a
  queue wait. Look at what the `launch` tool returned, and whether the person pressed send, rather than waiting
  longer for something that is not there.

      Status:          submitted to Platform, but nothing is waiting on the site
      Layer:           scheduler
      I will handle:   report this as a launch failure, not a queue wait
      Next step:       read what the `launch` tool returned and whether the request was sent; the answer is there, not in the queue

- **Something is pending.** Its reason resolves exactly the way RUNNING's own
  table does, below — a SUBMITTED run waiting on a floor it will never clear
  is the same NEVER case, only caught before its first task ran. Follow that
  table and report through the same four lines.

## RUNNING

Mapping: RUNNING = the platform reports `running`.

`get_run` for per-task progress: it returns the task numbers for each process and the failed tasks.

**A task sitting unstarted is the failure mode to watch for.** Platform keeps
reporting the run as RUNNING and shows no error, so waiting longer looks like
the reasonable response and never is. What follows is a decision procedure,
not a checklist — take the first branch that matches and stop there.

**🤖 marks a step taken alone. ⏸ marks one that stops and asks the person.**
One rule decides which mark a step gets, everywhere in this file: **act alone
where there is a measurement or the action is reversible; stop and ask where
the choice would be a guess, or would move a security boundary.** A `resume`
counts as reversible in the sense that matters here — it continues in the same folder, and finished
tasks come back from cache rather than running again; the person says yes to it first.

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

For a run that looks stuck, read `get_run`'s task numbers (tasks submitted but
none started, for a long time) and ask the site the question above: silence
from a status check is not evidence of progress. The one-command check that
joined the two (`scripts/task_health.sh`) is not available on v3 yet (owed: task-health), so do both by hand.

- **The site's scheduler is not answering** (exit 3). 🤖 Report that and wait —
  queued work survives it, and there is nothing to fix at the run's end. A
  scheduler that has gone quiet does not refuse the ordinary status query, it
  makes it wait for tens of seconds, so this and a genuinely busy site look
  identical until something asks.
- **A resource-floor rejection (the pending-reason check above names it;
  the scheduler's own wording is site-specific), or any answer shaped like a
  floor being missed →
  NEVER.** 🤖 The resource contract has drifted from what the site actually
  enforces. Fixing it (`scripts/ce_apply.sh` rewrites the compute environment
  through the old Seqera CLI) is not available on v3 yet (owed: ce-apply), so
  do not run it: say plainly that the contract and the site disagree and that
  the person has to change the compute environment. Never wait longer, since
  this request was never going to start.
- **The time requested exceeds what is allowed → NEVER.** 🤖 Raising the time
  and relaunching is not available on v3 yet (owed: resize-relaunch): the
  `relaunch` tool restarts with the same settings and cannot change the time.
  Say so, and that a changed request is a new `launch`, which the person confirms.
- **The nodes requested are unavailable → NEVER.** ⏸ Whether to keep waiting
  for them or move the request is the person's call, not this command's —
  both are legitimate and neither is reversible the way a relaunch is.
- **Waiting on resources, or on priority.** One more question decides the
  branch: is there a measurement for this process? ("Reading a measurement",
  below, says where that comes from.)
    - **Yes.** Does peak memory × 1.5 still fit inside a smaller box?
        - **Yes.** 🤖 Relaunching into the smaller box is not available on v3 yet (owed: resize-relaunch): `scripts/relaunch_with_override.sh`
          depends on the old Seqera CLI, and the `relaunch` tool cannot change
          the size. The number came from a measurement, so say what it is and
          that a new `launch` is the route; the person confirms that launch.
        - **No.** 🤖 Say plainly that it is already as small as it can go —
          there is no smaller box to relaunch into.
    - **No.** ⏸ Propose a number with the evidence behind it, and wait for a
      reply. A number with no measurement behind it is a guess, and a guess
      that lands low is a second failure, not a faster run.

A job already sitting in the site's scheduler cannot be resized where it
sits — the site refuses that outright, for every field, including a rename
that touches no resource at all (`docs/PITFALLS.md` 6c). So once a number
needs to change, relaunching is the only route there is; it is not a
compromise, and there is nothing to build in its place. On v3 that relaunch is
a `relaunch` request (same settings) or a new `launch` (changed settings), and
in both the person says yes. Either way it starts from the
start in a new folder, so the cost is one more spell in the queue and the
whole run again.

## FAILED

Mapping: FAILED = the platform reports `failed`.

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
    Next step:       once approved — `scripts/egress_allow.sh add <host> --reason "<this run>"`, restart the outbound channel, relaunch

- **A refusal lines up with the failure time.**
    - **It is on the known-harmless list** (`docs/PITFALLS.md` 4e, 4e2). 🤖
      Rule it out and keep looking — this refusal is expected on a healthy
      run and is not the cause here.
    - **It is not on that list.** ⏸ Allowing a host through the outbound
      channel moves a security boundary, and that is not this command's call
      to make alone. Once approved: run
      `scripts/egress_allow.sh add <host> --reason "<the run that needed it>"`
      (the safety net asks the user to confirm it), restart the outbound
      channel, relaunch. This adds the host to this deployment's own list
      only; adding it to the built-in list is the maintainer's change (a
      plugin edit and a release).
- **No refusal lines up with the failure time.** Read `.command.err` and
  `.exitcode` for the failing task (`get_run` finds it: it lists the failed
  tasks with their exit code and error message, and gives `failure_reason`
  when Nextflow said why). v3 尚未提供 task 的資料夾路徑 - not available on v3 yet (owed: task-folder-path): `get_run` gives no work folder for a failed task, so do not build one; use the error message and `failure_reason` it gives, and ask the person for the folder if they know it. Downloading the log through the platform is not available on v3 yet (owed: log-download); once the person gives the folder, read the file there with `scripts/fetch.sh`.
    - **137, or killed.** 🤖 See "out of memory", below.
    - **No `.command.log` and no `.exitcode` at all.** 🤖 The work directory is
      probably not visible from the compute side — report that; there is
      nothing further to diagnose from here.
    - **Jev triage, only if the user turned it on** (optional, off by default;
      `docs/adr/0007-jev-optional-triage.md`). 🤖 Call it for the first failing task
      that `get_run` lists, once per run, never per task: v3 尚未提供 task 的資料夾路徑 - not available on v3 yet (owed: task-folder-path), so run it only when the person has given the task folder; otherwise skip to "Anything else".


      ```bash
      scripts/jev.sh triage --err <that task's .command.err> --exit <its exit code, or none>
      ```

      The script always exits 0 and prints a machine line first,
      `JEV status=<…> category=<…> confidence=<…> sent_chars=<…>`. That line is
      for you to parse; never show it to the user. (If the script prints a
      notice about what is sent before it, that notice is for the user: pass it
      on in full, it appears once per machine.)
        - **`status=disabled`.** Say nothing about Jev: the report the user sees
          has no Jev wording and no extra line, and is the same as it would be
          without this step. Go on to "Anything else".
        - **`status=ok`, category not `unknown`, confidence at least
          `jev.min_confidence`** (read it with `scripts/settings.sh --jev
          min_confidence`; a confidence equal to it counts as sure). Add one line
          to the report, `Jev 判斷：<category>（信心 0.xx）`, read only the last
          200 lines of `.command.err` (not the whole file), and follow that
          category's route in "Jev categories", below. `memory` goes to "Out of
          memory".
        - **`status=ok`, but the confidence is below the threshold, or the
          category is `unknown`.** Say `Jev 沒把握，照原流程` and go on to
          "Anything else".
        - **`status=no_key`, `failed`, `capped` or `empty`.** Pass on the one
          sentence the script printed after the machine line (it says why Jev
          was skipped and that the original flow follows), then go on to
          "Anything else".

      Jev only points; it decides nothing. Every ⏸ below stays a stop for the
      user's say-so: Jev 的判斷不讓任何需要使用者同意的事變成自動.
    - **Anything else.** This has no branch above — follow
      `skills/operational/SKILL.md`'s "Off-design: when nothing here covers
      it" (T2: a failure with no branch), category `pipeline`, command
      `runs`. 🤖 Attempt the fix inside the safety net once it is recorded.
      ⏸ Stop and ask only if the fix turns out to need a pipeline parameter
      changed — that is a call about the run that was requested, not about
      the site.

On a site with unrestricted egress the first step prints nothing and costs a
second. Two of the four failures during this system's bring-up were an
outbound request the site would not carry, and in both cases the error
Platform reported pointed somewhere else entirely — a blocked request can
surface as `UnknownFormatConversionException: Conversion = '4'`, a formatting
bug in the code that reads the rejection, not a clue about the cause. That is
why the refusal is asked about before the log, not after: reading the log
first sends the diagnosis toward whatever it names, and in this shape of
failure that is never the actual cause.

### Jev categories

Where a confident Jev category leads. Each route says what to look at first, the
usual fix, and when to stop and ask; none of them skips a ⏸ that exists
elsewhere. For Jev, `memory` is the "Out of memory" section below, `unknown` is "Anything else".

#### `walltime`
- **Look first:** the task's `.command.log` and `.exitcode` for a time-limit
  message, and how long the task ran against the time it asked for.
- **Usual fix:** the task needed more time than it requested; a larger time
  request for that process is a changed request, so a new `launch` (through
  `skills/launch/SKILL.md`) - changing it by relaunch is not available on v3 yet (owed: resize-relaunch).
- **Ask the user** before a new `launch` with more time: that is a different request than the
  one they made. 🤖 Reading the log and measuring is yours.

#### `network`
- **Look first:** which host the task tried to reach (the last lines of
  `.command.err`), then run the refusal check at the top of this section for
  that time window.
- **Usual fix:** a host the site refuses is allowed only by the user's decision;
  a transient download failure usually just needs a relaunch.
- ⏸ **Ask the user** before allowing any host: that moves a security boundary
  (`scripts/egress_allow.sh add <host> --reason "<the run that needed it>"`, as
  in the refusal branch above). Retrying a plain download failure is yours.

#### `container`
- **Look first:** the image name and tag in the error, whether the pull, the
  conversion or the start failed, and whether the same image started for an
  earlier task of this run.
- **Usual fix:** a wrong or retired tag is a pipeline-version question; a pull
  that failed once usually works on relaunch; a full scratch area needs the
  user to free space.
- **Ask the user** before changing the pipeline version or deleting anything
  to free space. 🤖 Retrying the pull is yours.

#### `input`
- **Look first:** the file named in the error: does it exist where the task
  looked, is it empty or truncated, does its header match what the process
  expects (`scripts/input_checksums.sh` compares it with what was recorded at
  launch).
- **Usual fix:** regenerate or re-stage the input, or correct the samplesheet
  row, then relaunch.
- **Ask the user** before replacing any input file: it is their data. 🤖
  Reading and comparing it is yours.

#### `params`
- **Look first:** the option the error names, against the params file this run
  was launched with. Reading a run's parameters back from the platform is not available on v3 yet (owed: run-params); use the params file the launch was
  built from.
- **Usual fix:** correct or remove that option. That is a new analysis: ask through `launch` with the corrected parameters, and the person confirms it. `relaunch` and `resume` cannot change parameters.
- ⏸ **Ask the user** before changing any pipeline parameter: that is a call
  about the run that was requested, not about the site.

#### `tool_bug`
- **Look first:** the tool's name and version in the error, and whether the
  same tool worked on other samples in this run.
- **Usual fix:** a crash on valid input is not something to fix from here;
  report it with the tool, version and the last lines, and check that tool's
  issue tracker for a fixed version.
- **Ask the user** before relaunching with a different tool or pipeline
  version. This route ends in a report, not a repair: follow
  `skills/operational/SKILL.md`'s "Off-design: when nothing here covers it" if
  nothing known matches.

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
  🤖 A relaunch with a floor above what the retry reached is not available on v3 yet (owed: resize-relaunch); a `relaunch` request would repeat the same
  size. Asking for the same size again is not a smaller request, it is the same
  failure repeated, so say that and offer a new `launch`, which the person
  confirms.

The old wording here claimed the opposite: that a doubled request lands
between two boxes and strands, and that a genuine out-of-memory failure needs
a box moved up by hand. Neither was true, and both cost more than they saved —
they told the reader to distrust a recovery that works, and to go do by hand
the thing already happening automatically. Do not reintroduce either claim.

## Reading a measurement

Both branches above turn on whether a measurement exists for a process. This
is where it comes from — verified, not assumed:

Reading per-process memory use and per-task requested and used resources
(the percentage of the box used, peak RSS) through the platform is not available on v3 yet (owed: measurements): `get_run` carries task numbers and
failures, not what a task used.

The numbers exist on the filesystem:
`pipeline_info/execution_trace_*.txt` is a TSV despite its extension, and
carries `peak_rss` and `peak_vmem` per task. This is the measurement to use on v3.

| signal | meaning | action |
|---|---|---|
| 137 / killed, retry succeeded | recovered by itself | 🤖 report the box it needed |
| 137 / killed, retry also died | one tier was not enough | 🤖 report the box the retry reached; a larger one is a new `launch` the person confirms |
| ≥ 85% of the box, task failed | died against its own ceiling | 🤖 report it; a larger box is a new `launch` the person confirms |
| ≤ 30% and waiting on resources | badly over-allocated | 🤖 down to the box fitting peak RSS × 1.5 |
| 30–85% | reasonable | 🤖 leave it; the wait is a real queue, not a sizing problem |
| no measurement at all | nothing to reason from | ⏸ propose and wait |

## SUCCEEDED

Mapping: SUCCEEDED = the platform reports `succeeded`.

1. **Check the site can still serve outputs** — through the adapter:
   `list_agents` (name, online or offline, last contact).
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

   **But check the manifest actually reached Platform before blaming the
   pipeline.** The two look identical from the Reports tab and have opposite
   causes. `<workDir>/nf-<runId>-reports.tsv` is what Nextflow wrote and what
   Platform reads back through the agent:

   - **The file has rows** and Platform still shows nothing → the manifest is
     not getting across intact. PITFALLS 36: an agent whose own working
     directory has been deleted prefixes a `shell-init: ... getcwd` line to
     every answer, so Platform parses shell noise as the TSV header and
     reports the file as empty. `readlink /proc/<agent pid>/cwd` settles it in
     one command — a `(deleted)` suffix is the whole diagnosis. Everything
     else looks healthy, including `AVAILABLE` and live heartbeats.
   - **The file has only its header row** → nothing matched, and the
     `tower.yml` paragraph above applies.

   Runs that finished while the agent was in that state stay blank even after
   it is fixed: Platform caches the manifest at completion and never asks
   again. Say so rather than restarting anything twice.

2. **Read the QC, do not just link it.** Report per-sample numbers, and say
   plainly whether any sample should be dropped. Where the pipeline inferred
   something automatically — `strandedness: auto`, an outlier call — report the
   evidence behind it and whether the samples agree.

   MultiQC is the usual place, carrying mapping rate and duplication. A
   pipeline that produces no MultiQC still produces per-sample QC somewhere:
   differentialabundance puts it in DESeq2 size factors, a MAD-correlation
   outlier call and a sample dendrogram, under `other/` and `plots/`. Find what
   this pipeline actually made. **A missing MultiQC is not a QC report of
   none** — it is the same shape of mistake as an empty listing read as an
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

4. **Offer to tune the box sizes** - this is not available on v3 yet (owed: tune-resources):
   `scripts/tune_resources.sh` read its measurements through the old Seqera CLI.
   Say so, and leave the step out of the delivery until it is back. The
   reasoning stays for when it returns: Platform's own resource optimiser must
   stay off (`docs/PITFALLS.md` 9) - it right-sizes from run history, which is
   exactly wrong on a site where the acceptable sizes are a handful of fixed
   boxes rather than a range. A tuned file has to say what it was tuned against
   (how many samples, how big an input): the same sizing on materially more
   data is an out-of-memory failure, not a faster run (`docs/PITFALLS.md` 6d).
   Keep that line visible wherever a later launch offers such a file back as
   "reuse the previous settings".

5. **Offer cleanup of `work/` only**, and only with explicit confirmation.
   Never `rawdata/`, `results/`, `analysis/`, `_references/`, the shared image
   library, or `.nextflow/plugins/`.

## CANCELLED

Mapping: CANCELLED = `failed` whose facts say a cancel request was sent (Nextflow reports a cancelled run as failed, `docs/PLATFORM.md`).

Platform did not do this on its own — someone asked to, from the platform or
the site, and this command did not do it either unless it just relaunched something
by hand. Establish which before touching anything: a cancellation can land
before, during, or after a task started, and treating it as a mistake without
asking is a decision that was never this command's to make.

    Status:          cancelled — not a failure, and not something this invocation started
    Layer:           pipeline
    You decide:      relaunch it, or leave it cancelled
    Next step:       say the word and it relaunches the same way any other run does

To stop a run that is still going, call `cancel` with its name: it only asks, and the person confirms it on their own channel. A failed or cancelled run that the platform launched can be continued by its name alone, after the person says yes each time. `resume` (or `abf-platform resume RUN`) takes up where Nextflow stopped, in the same folder, and finished tasks come back from the cache. `relaunch` (or `abf-platform relaunch RUN`) starts the run again from the start in a new folder. The samples and parameters are those of the first launch; changing them is a new `launch`.

## UNKNOWN

Mapping: UNKNOWN = `lost` (three heartbeats silent) or any other value this file does not list.

`list_runs` and `get_run` can report a status this file has no branch for - `lost`, or
a status the platform adds that this file has not been updated to cover. Say exactly what
Platform reported and stop there rather than guessing what it implies; NEVER
and "waiting" are both claims this file makes only where a rule above already
covers the reason.

    Status:          Platform reports a status not covered above — say it verbatim
    Layer:           env
    You decide:      what to do next — this file has no rule for this status
    Next step:       tell the maintainer which status this was, so a branch can be added here
