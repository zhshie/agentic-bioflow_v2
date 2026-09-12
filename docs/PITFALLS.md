# Pitfalls

Every entry below cost a failed run or a wrong assumption that had to be walked
back. They are written in the order you are likely to meet them.

## Setting up the agent

**1. The `tw-agent` native binary will not install here.** It needs glibc
2.32/2.34; Taiwania-3's login nodes have 2.28. Use `tw-agent.jar` instead — but
the jar needs **Java 21** (`UnsupportedClassVersionError: class file version
65.0 vs 61.0`) and the cluster only offers 17 and 8. Install a private Temurin
21 and point *only the agent* at it; leave Nextflow's Java alone.

Do not leave either the JDK or the jar in a home directory. `/home/<user>` is
`drwx------` on this cluster, so a second member cannot traverse it no matter
how the files themselves are permissioned - and the same is true of a private
`/work/<user>`. Put them somewhere every member can read and record the paths
in the settings file (`agent_java`, `agent_jar`).

**2. Create the agent credential only while the agent is already running.**
`tw credentials add agent` fails with "The agent is not online" otherwise.

**2b. The generated connection identifier had nothing in it that varied per
person.** `agent_ctl.sh start` assigned `${USER}-$(hostname -s)-$(date
+%Y%m%d)` when the setting was empty, and at this site neither of the first two
discriminates: everyone reaches the cluster through one shared account, and
under `reach: ssh` the hostname is the login node's for whoever is driving. The
date was doing all the work, so two setups on one day - two members, or one
person on a laptop and on the login node - would have been handed the same
string. The workspace shows how close this came: its two `tw-agent`
credentials differ only by work directory, which is not part of the name.

Nothing would have reported it. `start` succeeds on the duplicate - a real
process, real local state - and the collision surfaces later as 3c's permanent
refusal, which reads as an agent that keeps dying. Identifiers now carry four
random bytes, and `start` asks the workspace before committing to one. There is
no `tw agent` command; the credential list is the registry:

```
tw -o json credentials list -w <ws>   →   credentials[].keys.connectionId
```

The query is best-effort - a site with no `tw`, no token or no route out says
so and proceeds on the random tag - because uniqueness comes from the bytes and
the query only confirms it.

**A generated identifier has to be written down on the machine that reads the
settings.** `start` runs on the site; under `reach: ssh` the settings file
driving the next `start` is on the user's machine, and `set_setting` on the
site cannot reach it. This was survivable while the identifier was
date-derived, because regenerating it produced the same string until midnight.
It is not survivable now, and `start` prints the `settings.sh --set
agent_connection <id>` line for exactly that reason.

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

**3b. Every binary file Platform serves through the Tower Agent is corrupt.**
Reports open, images do not. The agent's file transfer deletes every `0xFF`
byte from the stream, and the first `0xFF 0xFF` pair ends the transfer early.
Measured on `nf-core/differentialabundance` output:

| file | on disk | served by Platform | `0xFF` count | first `0xFF 0xFF` |
|---|---|---|---|---|
| `volcano.png` | 31,950 | 31,833 | 117 | none |
| `density.png` | 87,319 | 86,966 | 353 | none |
| `pca3d.png` | 39,857 | **5,172** | 153 | offset 5,190 |
| `deseq2.plots.pdf` | 9,477 | 9,459 | 18 | none |

For the first, second and fourth the served bytes are *exactly* the file with
every `0xFF` removed; for the third they are that same stream cut at the
doubled `0xFF`. Deterministic - refetching returns byte-identical corruption.

Text is unaffected, which is why this hides: a 3.8 MB `multiqc_report.html`
arrives byte-perfect, because valid UTF-8 never contains `0xFF`. So the run
looks fine, MultiQC looks fine, and only the images are broken - subtly, since
a PNG missing 117 scattered bytes still has a valid header and renders as a
partial or mangled picture rather than a clearly failed download.

Until Seqera fixes it, read binary outputs from the filesystem - they are
intact on disk. Platform is reliable for HTML, TSV and logs only.

**3c. The agent dies quietly, and the first thing that tells you is a refused
launch.** Its own log explains it afterwards:

```
INFO - Closed for unknown reason after
INFO - Connecting to Tower
ERROR- There is an active agent for this user and connection ID. Please close it before starting a new one.
```

The session dropped, the agent reconnected, and the server still considered the
old connection live - so the reconnect was rejected and the process exited. No
alert, no state change anywhere Platform shows you.

**The drop itself is routine; being refused on the way back is what kills it.**
Four drops across two days, three of them fatal:

| drop | reconnect | outcome |
|---|---|---|
| 09-03 18:07:01 | +3.3 s | refused, process exited; a manual restart at **+10 min** was accepted |
| 09-03 21:18:50 | +0.7 s | accepted, agent carried on - nothing to do |
| 09-03 22:54:04 | +2.7 s | refused, process exited; a manual restart at **+58 min** was accepted |
| 09-04 08:35:57 | +2.5 s | refused, process exited; a manual restart at **+93 min** was accepted |

This is not a slow decay you can outrun by restarting nightly: the agent that
died on 09-04 had been up **13 minutes**.

So the agent's own retry, seconds later, is the one attempt that reliably
fails. **Wait a few minutes before restarting**, and restart with the *same*
connection ID - the compute environment's credential is tied to that string, so
a fresh ID trades this outage for a broken CE. How long the server holds a dead
session is not established: accepted restarts span 10 to 93 minutes, and every
one of those was a wait somebody happened to take, never a measured floor.

It surfaces two ways, and neither names the agent:

- **A launch is refused** with `No Tower Agent is online for the selected
  compute environment`, which reads like a compute environment problem.
- **A run that already SUCCEEDED goes blank.** Outputs are streamed through the
  agent on request, never stored on Platform, so a delivered run loses its
  Reports tab the moment the agent dies - hours later, with the run still shown
  as SUCCEEDED. The files are untouched on disk (see 3).

The real lesson is to run `scripts/preflight.sh` **before** launching rather
than after a launch is refused - it names this in one line, and `/launch` is
supposed to. When a user says outputs vanished from a finished run, check the
agent again rather than trusting the check from delivery time.

Note that the connection ID has to be unique per agent. Two members sharing one
produces exactly the error above, permanently rather than transiently.

**3d. `npm install -g` on this NFS home breaks the Claude Code CLI you are
running from.** npm moves the existing package aside and deletes it. NFS cannot
unlink a file another process still holds open, so it silly-renames the running
binary to `.nfsXXXXXXXX` and npm's cleanup fails:

```
npm warn cleanup [Error: EBUSY: resource busy or locked, unlink
  '.../@anthropic-ai/.claude-code-CimSOsSF/bin/.nfsa0407ee829f786120008d133']
```

If the install is interrupted anywhere after that move, the package is left
with no `package.json` and no `bin/claude.exe`, while `bin/claude` still points
at the missing file. Observed on 2026-09-04: `claude` became "command not
found" mid-session, `npm ls -g` showed `@anthropic-ai/claude-code@` with an
empty version, and 216 MB sat in a `.nfs` file.

**The session already running survives, because it holds the deleted binary
open — but it cannot be restarted.** Quitting is what makes the damage visible.

**It recurs, and the second time is quieter.** Later the same day the package
directory held an empty `bin/` and nothing else — no `.nfs` file left to
explain it — while `~/.nvm/.../bin/claude` still pointed at the missing
`claude.exe`. Nothing announced this: `command -v claude` simply stopped
answering.

**Check where the session actually came from before treating this as urgent.**
The VS Code extension ships its own binary at
`~/.vscode-server/extensions/anthropic.claude-code-<version>-linux-x64/resources/native-binary/claude`,
and a session started that way neither uses nor needs the npm install. That
binary also runs `claude plugin update` perfectly well, which is the way to
finish a deployment without reinstalling anything mid-session.

Re-running `npm install -g @anthropic-ai/claude-code` fixes it in seconds and
is safe while a session is running; the cleanup warning about the busy `.nfs`
file is expected and harmless. That file is only removable once every process
holding it has exited.

**3e. A live agent and a real SUCCEEDED run can still show zero reports, for a
reason that has nothing to do with this deployment.** `scripts/agent_ctl.sh
online <runId>` answering `ONLINE - Platform lists 0 report(s)` is not proof
that anything here is broken — check the pipeline's own `tower.yml` before
suspecting the agent or the site adapter. Platform's Reports tab is populated
by matching that manifest's paths against files under `outdir`; nf-core/ampliseq
2.18.0 ships

```yaml
reports:
  multiqc_report.html: ...
  samplesheet.csv: ...
```

naming paths **relative to `outdir` root**, but the pipeline actually publishes
to `outdir/multiqc/multiqc_report.html` — the manifest was not updated when the
output moved into a subdirectory. Every file is on disk, complete and correct
(verified byte-for-byte against the site copy); Platform simply never finds a
match, on any deployment, HPC or cloud. `nf-core/rnaseq` showed the same zero
during this same session, which is what makes "check tower.yml first" worth
doing before spending time on the agent, the relay, or the compute environment.

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

**4b. A CONNECT with no headers used to hang the relay, and only Python
noticed.** `http.client._tunnel()` - which is what `urllib.request.urlopen`
uses, and therefore every nf-core helper script written in Python - sends:

```
CONNECT host:443\r\n\r\n
```

with no headers at all. The relay read the request line, then drained the rest
with "recv until this chunk contains \r\n\r\n". With no headers the only thing
left in the socket is the terminating `\r\n`, which no single chunk can ever
satisfy, so the relay blocked for the full socket timeout and then closed. The
client reported `RemoteDisconnected: Remote end closed connection without
response`, which reads like a fault at the far end.

curl and Singularity always send a `Host:` header, so image pulls never
revealed it. nf-core/fetchngs is the first pipeline here that reaches the
internet from Python, and it failed 100% of the time from the day the relay was
written. `tests/relay_connect_test.py` covers all four shapes, including the
headerless one and a denial.

**4c. The relay's DENY log only means something once parsing succeeds.**
While 4b was live, blocked domains produced `ERROR ... TimeoutError` with no
domain name rather than a `DENY-DOMAIN` line - the request never got as far as
the allowlist check. After fixing 4b, the very first run immediately named
`eutils.ncbi.nlm.nih.gov` as missing. Reading "no DENY lines" as "not a network
problem" is only safe when the relay is known to be parsing correctly.

**5. `tw launch --config` is additive, not a replacement.** Platform uploads the
file and appends `includeConfig 'https://api.cloud.seqera.io/ephemeral/…'`
*after* the compute environment's own config, so it wins on conflicts and you
only need to send the difference. The side effect: the head job fetches that URL
at startup, so `seqera.io` must stay on the allowlist or your config silently
does not apply. `--params-file` works the same way.

**4d. The relay only carries HTTP and HTTPS.** `nf-core/fetchngs` offers
`--download_method aspera`, which moves data over UDP; nothing routed through
an HTTP proxy can carry it. Use the FTP/HTTP download methods here. The same
applies to any tool reaching for a native FTP or UDP transport.

**4e. A denied `169.254.169.254` is expected and harmless.** Several tools
(sra-tools among them) probe the cloud instance-metadata endpoint to work out
whether they are running on AWS. On this cluster that address means nothing and
the relay refuses it, which is the correct outcome - do not add it.

**4e2. A denied `multiqc.info` is expected and harmless.** MultiQC checks for a
newer version of itself on startup and carries on when it cannot. The refusals
appear in the egress log during otherwise healthy runs:

```
13:22:52 DENY-DOMAIN multiqc.info 80 from cpn3859
14:03:45 DENY-DOMAIN api.multiqc.info 443 from cpn3857
```

Do not add it. Allowing it buys nothing and sends outbound telemetry from every
run on the cluster.

**4f. Check the allowlist before launching, not after.**
`scripts/check_egress.py <owner/pipeline> <revision>` reads the pipeline's own
code - `nextflow.config`, `conf/`, `bin/`, `workflows/`, `subworkflows/` and
each module's `main.nf` - and reports hosts the relay would refuse. Config and
`bin/` alone are not enough: funcscan hardcodes the CARD download in
`subworkflows/local/arg.nf`. Documentation is excluded on purpose, because
`meta.yml` and `ro-crate-metadata.json` are nothing but tool homepages and
including them buries three real hosts under forty citations.

**4g. The static check cannot see a URL that lives inside the tool, and that
is what the DENY log is for.** nf-core/bacass passes 4f clean, then fails at
BUSCO: `Cannot reach https://busco-data2.ezlab.org`. That host appears nowhere
in bacass — the download URL is compiled into BUSCO itself. Expect one round of
this for a pipeline whose tools fetch their own reference data; the relay log
names the host on the first failure, which costs one run, not a diagnosis.

## Resources

**6. NCHC's QOS is a floor, and for most partitions the floor equals the
ceiling.** `sacctmgr -nP show qos format=Name,MinTRES,MaxTRESPerJob` shows
`MinTRES == MaxTRESPerJob` — a partition is a fixed-size box. Ask for less than
the box and the job never schedules: it sits at `QOSMinCpuNotSatisfied` or
`QOSMinMemory` while hundreds of CPUs sit idle, with no error anywhere. Platform
keeps reporting the run as RUNNING. Only `scontrol show job <id>` reveals it.

Nextflow provides `resourceLimits` for the ceiling and has no equivalent for the
floor, which is what `configs/sites/nchc.config` supplies.

**6b. The seven `ngs` partitions are one node pool wearing seven labels.** The
box names look like tiers of hardware and are not — the node lists are
byte-identical:

```
$ for p in ngs7G ngs13G ngs26G ngs53G ngs92G ngs186G ngs372G; do
    echo "$p $(sinfo -h -p $p -o '%D') $(sinfo -h -p $p -o '%N')"; done
ngs7G   46 cpn[3851-3852,3857-3900]
ngs13G  46 cpn[3851-3852,3857-3900]
ngs26G  46 cpn[3851-3852,3857-3900]
ngs53G  46 cpn[3851-3852,3857-3900]
ngs92G  46 cpn[3851-3852,3857-3900]
ngs186G 46 cpn[3851-3852,3857-3900]
ngs372G 50 bgm[3001-3004],cpn[3851-3852,3857-3900]

$ sinfo -h -p ngs53G -o '%n %c %m' | head -1
cpn3851 56 384564
```

`ngs7G` through `ngs186G` are the same 46 nodes. `ngs372G` is those 46 plus four
`bgm` nodes — 50. Every node is 56 cores and 384564 MB.

So moving to a smaller partition does **not** move you to different hardware,
and the inference it invites — "the small queue is less busy, I will wait there"
— has the mechanism backwards. A smaller box gets scheduled sooner because more
of them **fit per node**: a 56-core/375 GB node holds 7 jobs at 8c/53G but 28 at
2c/13G. The pool is the same size either way; the request is what changes how
much of it you need free at once.

Two things follow. Shrinking a request is the only lever that makes a queued job
start sooner here, so `scripts/why_pending.sh <jobid>` prints the ladder of
smaller boxes for a job whose `Reason=` is `Resources` or `Priority` — and
prints nothing of the kind for `QOSMin*`, which is entry 6's stranding and gets
worse, not better, if you shrink it. And the ladder itself is read out of
`NCHC_BOXES` in `configs/sites/nchc.config` by `scripts/utils/boxes.sh`, so the
box numbers exist in exactly one place.

**6c. A queued job cannot be resized here; `scontrol update` is refused
outright.** Shrinking a request is the lever entry 6b names, which raises the
obvious follow-up: a job already sitting in the queue does not need its whole
run cancelled and relaunched, it just needs its own request changed. On most
SLURM sites that works and costs nothing — the head job keeps running, the
cache is untouched, nothing re-queues.

Not here. Measured against a held job of the author's own, so ownership and
account were never in question (`UserId=u9613010`, `Account=mst109178`,
slurm 25.11.0):

```
$ sbatch --hold -A MST109178 -p ngs7G -c 1 --mem=7G -t 00:02:00 probe.sh
Submitted batch job 2053079                    # JobState=PENDING

$ scontrol update JobId=2053079 MinMemoryNode=13312
Unspecified error for job 2053079
$ scontrol update JobId=2053079 NumCPUs=2
Unspecified error for job 2053079
$ scontrol update JobId=2053079 Partition=ngs13G
Unspecified error for job 2053079
$ scontrol update JobId=2053079 JobName=renamed_probe
Unspecified error for job 2053079
```

The fourth one is the one that settles it. Renaming a job touches no resource,
no partition and no QOS, and it is refused with the same message — so this is
not a policy about resizing, it is that an ordinary user cannot `scontrol
update` their own job at all. The message says "Unspecified error" rather than
naming a permission, which is why guessing from the first three attempts alone
would have been wrong: they look exactly like a QOS rule about resources.

So a request that needs changing needs the run relaunched. `tw runs relaunch`
defaults to resuming, and the finished tasks come back from cache — three runs
of one bacass analysis shared a single Session ID and the last of them reported
8 of 9 tasks `CACHED` — so the cost is one more spell in the queue, not the
pipeline over again. That is the only route, and there is no point writing a
wrapper for the other one.

**6d. A retry DOES escalate here, and the config used to say it did not.**
Entry 6c leaves relaunching as the only way to change a request. That is true
for a *queued* job, and it made the neighbouring question urgent: when a task
dies of memory, does anything recover on its own, or does a person have to
intervene every time?

It recovers on its own, and it always did. nf-core's `conf/base.config`
multiplies every label by `task.attempt` — bacass 2.6.1 and rnaseq 3.14.0 both
do — and `configs/sites/nchc.config` sets only `queue` and `clusterOptions`,
never `memory` or `cpus`, so that escalation reaches the scheduler untouched.
Measured with a probe that failed four tasks on purpose with 137, the status an
OOM kill reports:

```
$ sacct --format=JobID,JobName,Partition,ReqCPUS,ReqMem,State,ExitCode -X
   2053143  nf-sayHello__3_  ngs13G  2  13G  FAILED     137:0     <- attempt 1
   2053144  nf-sayHello__1_  ngs13G  2  13G  FAILED     137:0
   2053152  nf-sayHello__1_  ngs26G  4  26G  COMPLETED    0:0     <- attempt 2
   2053155  nf-sayHello__3_  ngs26G  4  26G  COMPLETED    0:0
```

Attempt 2 asked for double and landed in the next box up, with `-c 4 --mem=26G`
derived for it. Nothing stranded.

**What makes this worth an entry is what the config asserted instead.** Its
comment said a doubled request "lands it between two boxes, and the retry would
strand exactly the way the original request did", and that "a genuine OOM needs
its label moved up a tier by hand". Both false. `nchcBox` rounds **up** to the
smallest box that fits, so doubling cannot land between boxes; `resourceLimits`
caps the top. The claim reads like it predates `resourceLimits`.

A wrong comment about a safety property is worse than no comment, because it is
believed and it points the wrong way: it tells whoever reads it to go and do by
hand the thing that is already happening, and to distrust a recovery that
works. It has been corrected in place, with the measurement beside it.

The site config still adds no multiplier of its own — not because escalation is
bad, but because the pipeline already supplies one and a second would compound
with it.

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

**17. The shared image library had three names, and the safety net guarded the
one nothing used.** `PRINCIPLES.md` lists the shared image cache among the
things that are never deleted, and `hooks/confirm_cleanup.sh` implemented that
by matching `lab_singularity_library`. Meanwhile:

```
$ grep cacheDir configs/sites/nchc.config
    cacheDir = System.getenv('NXF_SINGULARITY_CACHEDIR') ?: "${...}/_singularity_cache"
$ echo $NXF_SINGULARITY_CACHEDIR
/work/u9613010/lab_runs/.singularity_cache
$ ls -d /work/u9613010/lab_runs/lab_singularity_library
ls: cannot access ...: No such file or directory
```

Three spellings, and the protected one does not exist on disk. Every image this
site has pulled lives under the third, which the rule did not match — so the
directory whose loss costs the whole lab hours of re-pulling was deletable, and
the principle saying otherwise was true only on paper.

Nothing had gone wrong yet, which is the point: a guard on a path nothing writes
to fails silently and stays quiet until the day it matters. It was found by
building the run-area skeleton and asking which name to create, not by losing
anything.

The rule now matches the shape rather than one literal — `lab_singularity_library`,
`_singularity_cache`, `.singularity_cache` and a bare `singularity` directory —
while still allowing near misses like `results_singular`. The general lesson is
narrower than "keep names in sync": **a protective rule and the thing it protects
must be checked against each other, because divergence between them produces no
error at all.**

## Launching

**10. `tw launch <short-name>` only resolves pipelines registered in the
workspace.** Otherwise pass the full GitHub URL, or register it first with
`tw pipelines add`.

**11. Nextflow's work directory must be on a filesystem the compute nodes can
see.** A work dir under the login node's `/tmp` produces jobs that fail before
the task script runs, leaving no `.command.log` and no `.exitcode` — only a
bare exit 1 in `sacct`.

**12. NCHC's sbatch rejects a job name containing `|`, and a task tag can put
one there.** nf-core/funcscan tags fARGene tasks `<sample>|<hmm model>`;
Nextflow's default job name is `nf-` + `task.name` with only spaces replaced,
so every submission died at once:

```
sbatch: error: ERROR: Job name contains an invalid character '|'.
ERROR ~ Error executing process >
        'NFCORE_FUNCSCAN:FUNCSCAN:ARG:FARGENE (sample_1|class_a)'
```

Nothing reaches the task script, so there is no `.command.err` to read — the
message is in the head job log only. `configs/sites/nchc.config` now sets
`executor.jobName` to a sanitised name, which fixes it for any pipeline rather
than for this tag.

**13. A compute environment's config cannot be edited in place, and it holds a
copy, not a reference.**
`tw compute-envs update` changes only the name and description. Changing
`nextflowConfig` means `tw compute-envs import --overwrite`, which deletes and
recreates the environment under a new ID — export a backup first, and repoint
anything holding the old ID.

Because the stored config is a **copy**, editing `configs/sites/*.config`
changes nothing until it is pushed, and nothing reports the divergence: the next
run quietly uses the old contract. `scripts/ce_apply.sh` exports, shows the
difference and stops; `--apply` commits. Verify with `nextflow-io/hello` rather
than a real pipeline — see `docs/SITE_ADAPTER.md`.

To test a config change *without* touching the environment, pass it to
`tw launch --config`, which is appended after the environment's own config.

## Do not rebuild what nf-core already does

**14.** Before writing a check, read the pipeline's module source. Three checks
were written and then deleted after the fact:

| Check | Already handled by |
|---|---|
| Warn on a GTF with no `gene_biotype` | `WorkflowRnaseq.biotypeInGtf()` warns and skips biotype QC (rnaseq#460) |
| Compute STAR `--genomeSAindexNbases` for a small genome | `modules/nf-core/star/genomegenerate` computes `min(14, log2(len)/2-1)` in its else branch — passing the value in `ext.args` actually *disables* that |
| Build a samplesheet from a FASTQ directory | `bin/fastq_dir_to_samplesheet.py`, for rnaseq. Note it ships **only** with rnaseq; six other pipelines checked have no equivalent |

The one reference check worth keeping is narrower, and it is not rnaseq's:
**an attribute a parameter names has to exist on the line type that pipeline
actually parses**, and both halves move per pipeline. One RefSeq GTF
(*S. sclerotiorum* 1980, 14,714 genes) counted across its line types:

| attribute | `gene` | `transcript` | `exon` |
|---|---|---|---|
| `gene_id` | 14,714 | 14,714 | 40,668 |
| `locus_tag` | 14,714 | 14,714 | 40,668 |
| `gene_biotype` | 14,714 | **0** | **0** |
| `gene_name` | **0** | **0** | **0** |

Two pipelines, two different ways to walk into it:

- **rnaseq** `--gtf_extra_attributes` reads `exon` lines and defaults to
  `gene_name`. Absent, so the counts matrix gets a silently empty column.
- **differentialabundance** `--features_metadata_cols` defaults to
  `gene_id,gene_name,gene_biotype` while `--features_gtf_feature_type` reads
  `transcript` lines - where two of those three are absent. Pointing it at
  `gene` recovers `gene_biotype`; nothing recovers `gene_name`, so
  `--features_name_col` also has to name something the file carries
  (`locus_tag`), or every feature label in the report comes out blank.

Neither raises an error. Both produce a report that renders, with the column
empty. Count the attribute on the line type before trusting the default.

**15. differentialabundance 2.0.0's standalone volcano PNG labels both
directions `higher in null`.** `conf/modules.config` builds PLOT_DIFFERENTIAL's
arguments from `meta.params.reference` and `meta.params.target` - paramset-level
params that do not exist - rather than the contrast's own reference and target,
so the module is invoked with `--reference_level "null" --treatment_level
"null"`. Reproduced with nf-core's own test dataset, so it is not caused by the
contrasts file's format: a CSV (`id,variable,reference,target`) and the YAML
`comparison:` form both hit it.

Nothing about the analysis is wrong - the contrast parses correctly, and DESeq2
gets the right direction (checked against normalised counts: a `log2FC` of
+5.89 was 9-25 in the reference group and 888-1183 in the target). **The HTML
report is also correct**, saying `higher in CK` / `higher in SynCom`. Only the
exported PNGs under `plots/differential/` carry the null labels, so deliver the
report and treat those PNGs as unlabelled for direction.

## Driving the site from a laptop

**16. Every SSH connection to this site costs an interactive 2FA, so an agent
cannot open one — connection multiplexing is not an optimisation, it is the
only thing that makes the laptop-driven topology possible.** Measured
2026-09-04 against `t3-c4.nchc.org.tw`:

```
one bare round trip = 31.3 s
each trip prompts: 2FA method -> password -> OTP from the user's phone
```

Public-key auth is not accepted: `~/.ssh/authorized_keys` has four entries and
the server still forces keyboard-interactive 2FA. Almost all of those 31 s is a
human typing, not network latency, so the useful threshold is not "how many
seconds" but "does a session multiplex" — without it, `preflight.sh`'s five
nested script calls are five OTP prompts, and the OTP lives on a phone the
agent cannot read. That is not slow, it is unusable.

**16b. On Windows, only WSL can multiplex.** All three shells were measured;
the two native ones fail for different reasons, and the second failure is the
subtle one:

| shell | result | evidence |
|---|---|---|
| PowerShell (Win32-OpenSSH) | multiplexing unsupported outright | `getsockname failed: Not a socket` |
| Git Bash (MSYS2 OpenSSH) | control plane works, sessions do not | `Master running (pid=…)` from `ssh -O check`, then `mux_client_request_session: read from master failed: Connection reset by peer` |
| WSL2 | **Verified 2026-09-05.** Real AF_UNIX with `SCM_RIGHTS`; a master opened once with `ControlPersist=8h` carries every `on_site.sh` session for the rest of the work session | many successful sessions across a multi-hour deployment |

Read the Git Bash pair together: the master process is alive and the socket
carries control commands, so the setup looks correct. What fails is the next
step, where the master passes the new session's file descriptors to the client
process over the Unix socket. `-O check` needs no fd-passing; opening a session
does, and MSYS2's Unix sockets are emulated and do not implement it. No ssh
option changes this. Two further Git Bash traps on the way in: `ControlPath`
must not contain `:` (illegal in an NTFS filename — the usual `%r@%h:%p` cannot
work), and `ssh -M -f` fails to survive backgrounding under MSYS2's fork
emulation, which looks like the same mux error and sends you chasing the wrong
cause.

**16c. A `reach=ssh` deployment has to fix the site account's `~/.bashrc`, and
for two separate reasons — one costs seconds, the other loses the binaries
entirely.** `ssh host <cmd>` lands in a *non-interactive* shell. Bash detects
its stdin is a network connection and reads `~/.bashrc`; sshd does **not** read
`/etc/profile`. Both halves of that sentence bite:

| | before | after |
|---|---|---|
| `source ~/.bashrc` in a non-interactive shell | 3.65 s | 0.001 s |
| `tw` on PATH there | **MISSING** | `~/bin/tw` |
| `nextflow` on PATH there | **MISSING** | `~/bin/nextflow` |

The cost was one line: `conda shell.bash hook` spawns Python from NFS and takes
**3.3 s** on its own (nvm 0.45 s, sdkman and mamba 0.08 s each). `preflight.sh`
makes five nested calls, so a laptop-driven preflight was paying ~16 s for
tooling no remote command uses.

The missing binaries are the sharper trap, because they fail with the *site's*
error rather than a setup error: `~/bin` reaches PATH only through
`/etc/profile`, which a remote command never reads, so `ssh host 'tw runs list'`
reports a missing command on an account where `tw` is plainly installed and
works when logged in.

One thing that looks interactive-only and is not: **anything installed with
`npm -g` lives under the node version nvm selected**, so leaving nvm entirely
below the guard takes Claude Code's own CLI off PATH in every non-interactive
shell. Put that one directory above the guard and leave nvm's 0.45 s
initialisation below it — the cheap half of what nvm does is an `ls`:

```bash
_node_bin=$(ls -1d "$HOME"/.nvm/versions/node/*/bin 2>/dev/null | sort -V | tail -1)
[ -n "$_node_bin" ] && export PATH="$_node_bin:$PATH"
```

The fix is one guard, with the ordering doing all the work — anything the far
end of an ssh call needs goes **above** it:

```bash
export PATH="$HOME/bin:$HOME/.local/bin:$PATH"   # and JAVA_HOME, LAB_RUNS_DIR,
                                                  # the singularity cache vars
case $- in
    *i*) ;;
      *) return ;;
esac
# conda / nvm / sdkman / mamba initialisation below here
```

Check it the way the failure appears, not the way the file reads:

```bash
env -i HOME="$HOME" PATH=/usr/bin:/bin bash -c \
  'time (source ~/.bashrc); command -v tw nextflow'
```

**16d. On this cluster, `python3` on PATH is a lockdown, not a stub.**
`/usr/bin/python3` symlinks to `/usr/libexec/platform-python3.6`, mode `750`
`root:root` — RHEL's own reserved interpreter, not meant for general use.
Every script here that shells out to `python3` (`egress_ctl.sh`'s port search,
`agent_ctl.sh`'s JSON state) fails with a plain `Permission denied`, which
reads like a broken install rather than a deliberate fence. The site provides
a real one through the module system — `module load python/3.12.2` here — and
it has to go in `~/.bashrc` **above** the interactive-only guard (16c), the
same place and for the same reason as `tw`/`nextflow`: a `ssh host <cmd>`
session never reads the guard's far side.

**16e. Too many `on_site.sh` calls on one master silently hang, not error.**
This site's sshd caps concurrent sessions per TCP connection (`MaxSessions`,
default 10). Once a master is carrying that many — easy to reach with a
background `Monitor` polling every 60–90s, or simply a long work session with
many diagnostic calls — the next session-open request just sits, forever, with
no error and no timeout of its own. `ssh -O check` still succeeds (it is a
control-plane ping, not a session), which is what makes this confusing:
`preflight.sh`'s reach line says OK while the very next real command hangs.

The fix is not to open a session and wait longer; it is to close the exhausted
master and have the user open a fresh one:

```bash
ssh -O exit -o ControlPath=<path> <host>
```

`scripts/reset_master.sh` does this from the settings file instead of
hand-reconstructing the ControlPath and host each time, and prints the exact
reconnect line straight after.

If one specific session is visibly hung, kill only that ssh process — killing
the whole invoking shell (or the wrong process) can take the master down with
it, undoing the one thing ControlPersist was for. Wrap `on_site.sh` calls in a
local `timeout` so a hang is caught in seconds, not minutes; a bare `on_site.sh
--check-reach` passing is not evidence that the next real command will not
hang.

**16f. On Windows, `tw`'s native binary segfaults under WSL2 unless the kernel
allows `vsyscall`.** GraalVM native-image binaries built against older glibc
sometimes call the legacy vsyscall page (`gettimeofday` and friends) instead of
the vDSO; WSL2's kernel ships `vsyscall=none` by default, and the call takes
SIGSEGV instead of emulation. `dmesg` names it exactly:

```
tw[1046] vsyscall attempted with vsyscall=none ip:ffffffffff600800 ...
tw[1046]: segfault at ffffffffff600800 ip ffffffffff600800 ...
```

The install itself looks fine — `install_deps.sh --cli-only` downloads a
legitimate, correctly-sized, executable ELF binary; it just dies on `tw
--version`. Fix once, machine-wide, in `%UserProfile%\.wslconfig`:

```
[wsl2]
kernelCommandLine = vsyscall=emulate
```

then `wsl --shutdown` and reopen — which also drops the master connection
(16b's "leave that terminal open" does not survive a `--shutdown`), so budget
a reconnect right after.

**18. A gate that reads the conversation must separate what the model typed
from what the user saw — twice this was got wrong, and both times the fix's own
design conversation was what exposed it.** `hooks/confirm_walkthrough.sh` denies
a step when the transcript shows the step it depends on never happened. Its
evidence for "the workflow diagram was shown" went through three forms:

| form | satisfied by |
|---|---|
| the string `docs/images/` appears | the design conversation, which discussed it |
| a `docs/images/` **URL** appears in an assistant record | the heredoc that wrote the gate's own test fixtures |
| a `docs/images/` URL appears in an assistant **text** block | showing it |

The second form looks tight and is not. A transcript record is not one thing:
an assistant turn carries `text` blocks, `thinking` blocks and `tool_use`
blocks, and the flattening treated them alike. So this satisfied the gate —

```
cat > tests/confirm_walkthrough_test.sh <<'T'
DIAG='here is the workflow: https://raw.../docs/images/nf-core-bacass_metro_map.png'
T
```

— a URL typed into a command, inside a file, that nobody ever read. Splitting
the flatten to one line per content block, and requiring the URL in a `text`
block, is the whole fix: `text` is what reaches the terminal, and step 2 asks
for the raw URL to be put in front of the user precisely because a terminal
renders no image.

The schema half is deliberately not the same rule, because the schema has to be
*read*, not displayed — so a `tool_use` counts there, but only when the command
actually fetches (`curl|wget|WebFetch`). Naming a URL inside a file being
written is the same nothing in both halves.

Two general points. **A permission gate whose evidence is a conversation can be
satisfied by the conversation that builds the gate**, and that conversation is
the one place its author will not look. Both holes were found by running the
gate against a real transcript rather than fixtures — fixtures contain what
their author thought of. And **"assistant said X" is not one predicate**: the
question is almost always whether the user *saw* X, whether the model *did* X,
or merely whether it *thought* X, and those live in different blocks of the
same record.

**18b. The third instance, and the part that cannot be closed.** The fix in 18
was verified against a real transcript and passed. Then the report explaining
the fix — prose, to the user, containing the example URL — put a
`docs/images/` URL into an assistant `text` block, and the gate opened again.
That is not a fourth bug to fix. It is the shape of the whole class:

> **A gate whose evidence is a conversation is satisfied by a conversation
> about the gate**, and no pattern separates the two, because explaining a
> thing and doing it leave the same marks.

The right response is to state the threat model rather than tighten the regex
again. This gate defends against **an analysis session that skips step 2** —
an agent going straight to parameters, which is what actually happened and what
`launch.md` had failed to prevent twice. It does **not** defend against a
session *developing this plugin*, and it is not asked to. A real analysis
transcript contains no `nf-core/*/docs/images/` URLs unless someone put them
there on purpose, which is the step.

What the third instance did expose was a real hole, and it is not about blocks
at all: **the evidence never checked which pipeline it was evidence of.**
A conversation that showed rnaseq's figure and then switched to bacass — the
normal way this cluster is used, several pipelines per session — kept the gate
open with a diagram of something else. So when the command names a repo
(`nf-core/<name>`, or a github.com URL; a Launchpad entry names nothing and
leaves the check off), the figure URL must contain that repo. An abbreviated
URL fails it too, correctly: `https://raw.../docs/images/x.png` is not a URL
anyone can open.

The general form is worth more than either fix: **evidence has a subject, and a
rule that checks the predicate without checking the subject answers a question
nobody asked.** "A diagram was shown" is not "this pipeline was shown."

**19. A reason for not checking something is itself a claim, and it expires
without a sound.** One afternoon spent running the tools against the live
cluster and the real filesystem, instead of against their fixtures, turned up
five defects. Every one of them had a comment or a document sitting next to it
asserting the opposite, and four of the five were written by someone who was
right at the time.

| what was written down | what was true on 2026-09-09 |
|---|---|
| `downstream.md`: the >500 MB path is untested because nothing produced here is that large | two results trees at 10.2 GB and 8.9 GB, twenty times the limit, days old. `du` answers this in one command |
| `init_workspace.sh`: the image cache must be spelled `lab_singularity_library`, because the hook matches nothing else | true when written; PITFALLS 17 fixed the hook to match four spellings and retired the constraint without retiring the name. The skeleton kept building an empty directory `nchc.config` never writes to |
| `why_pending.sh`: the reason table covers what a job pends on | the live queue held ten shapes to its five. 102 of 353 pending jobs hit the fallback, which returned an empty string — the job's fields with no verdict under them, which reads as "examined, found fine" |
| `why_pending.sh`: the ladder tells you which box to shrink into | it never looked at the job's partition. Against a real `ct224` job it named an `ngs` box and offered six below — a different node pool, different floors, none of it measured. Same defect as 18b, one file over |
| `fetch.sh`: the size check exists so a laptop is not asked to pull a work directory over a home connection (its own header) | its refusal named only `--max-mb`, the override that does exactly that, and never named the on-site path `docs/DOWNSTREAM.md` had already specified |

Two of these are the *same* shape as failures this file already records, which
is the part worth keeping. The ladder answering for the wrong partition family
is 18b — evidence with an unchecked subject. The image cache is 17 — a guard
and the thing it guards, drifting apart in silence — except that this time the
drift was *created by the fix*: correcting the hook made the skeleton's name
wrong, and the comment explaining why that name was odd is precisely what
stopped the next reader from questioning it.

The lesson is not "re-read your comments". It is narrower and testable:

- **An untested marker has an excuse attached, and the excuse is usually a
  measurement.** "No input is large enough" is a statement about a filesystem.
  Re-run it before trusting it; it costs one command and it was false here.
- **A justification that names another file's behaviour is a dependency, and
  nothing links them.** When the hook changed, nothing pointed at the script
  that had been written around its old shape. The fix is not vigilance — it is
  to pin the value to the file it comes from, the way
  `tests/init_workspace_test.sh` now reads the cache name out of
  `nchc.config` rather than restating it.
- **A fallback branch that returns nothing is not a default; it is a hole with
  a verdict-shaped gap where the answer goes.** Name what you do not know.

And the reason all five surfaced at once: fixtures contain only what their
author thought of. Every one of these tools passed its whole suite before and
after. What they had never been given was the site.

## Driving the IDE from a terminal

**20. Positron's R kernel writes a registration stub, not a connection file,
and the missing ports are one HTTP GET away — "R cannot be driven the way
Python can" was a conclusion drawn from a file listing.** Measured 2026-09-09
against Positron 2026.04.0, ark 0.1.249, kcserver 0.1.64.

`positron-python` runs a classic ipykernel, so `%TEMP%/connection_python-*.json`
is a complete Jupyter connection file and any client can read it and attach.
`positron-r` writes only `registration_r-*.json`:

```json
{ "transport": "tcp", "signature_scheme": "hmac-sha256",
  "ip": "127.0.0.1", "key": "<hmac key>", "registration_port": 59087 }
```

No shell, iopub, stdin, control or hb port. The obvious reading — the R kernel
negotiates its ports privately, so only Positron can talk to it — is wrong, and
it cost a long detour into GUI automation before anyone read the supervisor's
own API docs. The ports are not private, just not written to that file: ark
binds them and the supervisor hands them out.

`positron-supervisor/dist/kcclient/docs/DefaultApi.md` lists `connectionInfo`,
and `ConnectionInfo.md` gives its shape — all five ports, the key, the
transport. Confirmed live, read-only:

```
GET /sessions/r-5d08f5e6/connection_info
{"control_port":59092,"shell_port":59088,"stdin_port":59091,"hb_port":59090,
 "iopub_port":59089,"signature_scheme":"hmac-sha256","key":"<same key>", ...}
```

The key matches the stub's. Only the ports were ever missing. `netstat` had
already shown ark holding 59088-59092 — the evidence was on the machine before
the workaround was attempted. `scripts/positron_run.py` does this, and works
for R and Python by the same path.

The transferable part: **a file that lacks a field is evidence about the file,
not about the system.** Ask what else publishes it before concluding it is
unavailable.

**20b. `sys.frame(1)$ofile` is not where `source()` keeps the path — it depends
on who called `source()`, and Positron's console adds a frame.** Measured
2026-09-09 with a probe run through both paths.

An R script that wants to find its own directory typically tries
`commandArgs()`'s `--file=`, then `sys.frame(1)$ofile`, then `getwd()`. Under
`Rscript` the first branch answers. Sourced in Positron's console:

```
commandArgs --file= : (none)
sys.frame(1)$ofile  : (NULL)
getwd()             : c:/Users/ACER/Desktop/agentic-bioflow
  frame 2 has ofile: .../analysis/probe_paths.R
```

`ofile` is on frame 2. So the middle branch silently returns NULL and the
script falls through to `getwd()` — which is the *workspace root*, not the
script's directory. Anything built from it is then one level off, and the
failure surfaces far away as a missing input file, naming a path that looks
almost right. Scan the frames for `ofile` instead of betting on a depth.

This is the same shape as 18b: evidence with an unchecked subject. `ofile`
existed, the frame index was assumed.

**20c. Two Windows-specific traps that both present as "the thing is not
there" while it plainly is.** Measured 2026-09-09.

Git Bash cannot open a Windows named pipe. `open(r"\\.\pipe\kallichore-22256")`
raises `FileNotFoundError` under MSYS, which rewrites the path on the way to
`open()`, and succeeds under native `python.exe`. Anything talking to the
supervisor must run outside the MSYS shell.

And `python3` is on PATH in Git Bash as an App Execution Alias pointing at a
Microsoft Store stub. `command -v python3` finds it; running it exits 49 having
printed nothing. A test harness that picks its interpreter with `command -v`
reports every case as an identical unexplained failure. Pick one by running it:

```bash
for candidate in python3 python py; do
    if "$candidate" -c 'pass' >/dev/null 2>&1; then PY="$candidate"; break; fi
done
```

**20d. Do not drive the IDE with synthetic keystrokes.** Attempted 2026-09-09,
twice, before the API above was found. Both times the keys landed in the wrong
application — once navigating a chat client — because the desktop belongs to a
person who moves windows while the automation runs. The second attempt added
`AttachThreadInput` + `SetForegroundWindow` with the foreground window verified
before *and* after sending, and still missed: verification and delivery cannot
be made atomic, and the race is against a human being, not a scheduler. There
is no hardening that fixes this class. Use the kernel protocol, which does not
care what has focus.

**20e. kcserver sends its HTTP headers lowercase, so matching the RFC's
capitalisation silently disables a branch.** Found 2026-09-09 by an
adversarial re-read of `scripts/positron_run.py`, then confirmed by dumping
the header block of a live `GET /sessions` (headers only — the body carries
`initial_env`):

```
HTTP/1.1 200 OK
x-span-id: 0e045b31-...
content-type: application/json
connection: close
content-length: 18630
```

The response reader tested `b"Transfer-Encoding: chunked" in head`, which this
server can never send. The bug was invisible because `/sessions` answers with
`content-length`, so the chunked branch was never needed; a response that did
arrive chunked would have reached `json.loads` with its chunk-size lines still
in it, and the failure mode is not an error — `find_sessions` swallows a bad
response as a stale supervisor, so the console just stops existing and the tool
says "no R console is open" about a console that is open. Header names are
case-insensitive by RFC 9110; match them that way. `content-length` is now
honoured too, rather than trusting "everything that arrived before EOF".

The reason this survived 22 passing tests is worth more than the bug: every one
of those tests entered through the fixture seam, which returns a parsed object
and never runs the wire code at all. Parsing is now its own function
(`_parse_response`) so a test can reach it without a socket, and that test also
asserts a non-200 error message withholds the response body.

**20f. `ark` sends an iopub error whose `traceback` is an empty list.**
Measured 2026-09-09: `stop("deliberate failure")` in the live console produced
an `error` message with nothing in `traceback`, so `"\n".join(traceback)`
printed one blank line — exit code correct, terminal silent, reason visible
only to someone looking at the IDE. That is precisely the blindness this tool
exists to remove. `ename`/`evalue` carry it, and `error_text()` now falls back
to them.

Two related things checked at the same time, both fine as they stood: the
authoritative failure signal is the shell channel's `execute_reply`, not iopub,
so it is now read as well and can only escalate a run to failed, never
downgrade one; and workspace matching now asks the filesystem
(`os.path.samefile`, walking up from the child) instead of comparing strings.
Positron reports its working directory with a lowercase drive letter —
`c:\Users\ACER\...` — and macOS and Windows are both case-insensitive, so
`--workspace C:\Users\...` against `c:\Users\...` is the same directory spelt
two ways. `os.path.commonpath` would call that a mismatch and report no console.

Still untested against a real supervisor: the `socket` (macOS/Linux) and `tcp`
branches. Only `named-pipe` has ever run for real. The specific risk worth
knowing on macOS is `AF_UNIX`'s 104-byte `sun_path` limit against a
`/var/folders/...` `$TMPDIR`; if it is hit, `POSITRON_SUPERVISOR_CONNECTION_FILE`
does not help, because the length is in the socket path, not the config path.

**20g. A live console's `commandArgs(trailingOnly = TRUE)` is empty, so a
script's own flags are reachable from `Rscript` and not from the IDE.**
Measured 2026-09-09 against the live R console: it returns `character(0)`,
while `interactive()` is `TRUE` and the device is `.ark.graphics.device`. The
consequence is not cosmetic. `analysis/` here holds two scripts that both
default to `analysis/figures`, so running one live overwrote the other's
output and there was no flag available to prevent it — the batch path had
`--outdir` and the live path had nothing.

`--args` closes it, differently per language because the languages differ.
IPython's `%run file a b` already forwards to `sys.argv`, so Python needs no
help. R has no argument mechanism in `source()` at all, so the generated code
defines `commandArgs` in the global environment for the duration of the call —
which works because R resolves the name up the environment chain and reaches
globalenv before base — and restores it with `on.exit`, so a script that stops
with an error does not leave the console rigged for everything typed
afterwards. Verified both ways live: `--min-depth 5000` changed which samples
were dropped, `--outdir` moved the output, and `identical(commandArgs,
base::commandArgs)` was `TRUE` afterwards.

Argparse detail worth keeping: `--args` is `nargs=REMAINDER`, so it has to be
last on the command line. Anything after it belongs to the script, including
flags this tool has of its own.

**20h. The one manual step is a gate, and a refusal has to be instructions.**
This tool will not open a console — starting a runtime unasked in someone's
IDE, in a workspace they did not choose, is a worse surprise than being asked
to open one. That is only defensible if stopping is actionable, so the refusal
names the window, the session picker, and the two commands worth knowing
(`--check`, `--wait`), and a test asserts those phrases stay in it. `--wait N`
is the alternative to sending someone away to start over: it holds, polls, and
continues by itself when the console appears. It deliberately does not cover a
console that exists but is busy — that is a different problem with a different
answer, and exit 3 says so rather than waiting out someone else's long job.

**20i. Every one of those transports is local-only, and "no console is open"
was said about the wrong machine.** Measured 2026-09-10 on `lgn304`.

Kallichore is reached over a named pipe, a Unix socket, or a loopback port, and
the supervisor files are found by globbing this machine's temp directory. All
three are local by construction. So when the agent runs on a cluster login node
and Positron runs on the person's own desktop — which is the topology this
session was actually in — `--check` printed `no Positron sessions found` and a
run printed the 20h refusal: *bring up the Positron window, open the session
picker*. Both sentences are true about `lgn304` and useless about the machine
the person is sitting at, where the console may well already be open. Following
the instructions cannot help, and `--wait 120` would have waited out the clock
for something that could never appear on that host.

**This is 18b again — evidence has a subject.** The empty list means "no
session *here*", and it was reported as "no session". Four states were being
collapsed into one message; they now get their own, because they take opposite
advice:

| what `survey()` sees | what it means |
|---|---|
| no supervisor file at all | no Positron on this machine — say so, and name the boundary |
| files, none answering | a Positron that has since quit; start it again |
| answering, no console of that language | 20h's refusal, which is correct *here* |
| a console, wrong workspace | already handled: name what was found |

The general lesson is the cheap one: **a tool that can only work under a
precondition should be able to say the precondition is unmet.** This one's
precondition — the agent and the IDE share a machine — was never written down
anywhere, in the script or in `commands/downstream.md`, and so was never
checked. `docs/DOWNSTREAM.md` now names the two deployments it splits.

**20j. The library the whole protocol rides on was imported at the last
possible moment, and `--check` passed without it.** Same review, same file.
`jupyter_client` is imported inside `execute()` — after a session is found and
after `connection_file()` has written that session's HMAC key to disk. On this
cluster it is not installed at all, so the documented sequence was: `--check`
says everything is fine, exit 0; the run then dies on a raw `ModuleNotFoundError`
traceback, out of a tool that weighs every other line it prints.

`commands/downstream.md` uses `--check` as a gate. **A gate that passes when the
run cannot possibly work is 21's shape** — a green assertion nothing can make
fail. It now imports the library rather than locating it (a wheel built for
another interpreter is findable and not importable), reports it, and the run
refuses before writing the key file. `--check` returns non-zero for either
missing precondition, because a gate whose only signal is prose is not a gate —
the same lesson the launch hooks are built on.

The test for it could not be left to the machine: this cluster has no
`jupyter_client` and a laptop generally has one, so the same case would pass on
one and fail on the other for reasons unrelated to the code. The suite supplies
both — a stub that imports and a stub that raises — and `$JC` picks. The present
case is what keeps the absent one honest: it proves the check can also pass, by
getting far enough to fail on the next thing instead.

**21. A negative assertion can be true for a reason unrelated to what it
guards.** `positron_run.py` narrows every `/sessions` record to a field
whitelist at parse time, because that response carries each kernel's whole
`initial_env` — on the machine it was written on, a live GitHub PAT and several
API keys. All 35 of its cases also grepped the rendered output for a fixture
credential, and the change that shipped it said so: "every test asserts a
fixture credential never reaches the output."

True, and worth nothing. Deleting the whitelist outright — `session =
dict(raw)`, every dropped field restored — left all 35 passing. `report()`
prints six named fields, so the credential could not reach stdout with or
without it. The assertion was measuring the print sites, and the whitelist
exists for the print sites *that do not exist yet*: the whole argument for
narrowing once at parse rather than at each render is that a render added later
cannot leak what was never carried. Nothing tested that property, so removing
it was free.

The test now asserts on the parsed object — `initial_env` and `argv` absent,
the credential absent from its `repr` — and fails under exactly that mutation.

Two other things in the same review had the identical shape, which is why this
gets its own entry rather than a footnote:

- The invocation `commands/downstream.md` tells a person to type
  (`scripts/positron_run.py --lang r --file …`) was tested by nothing: every
  case ran `"$PY" "$S"` instead. The file shipped mode 644 with
  `#!/usr/bin/env python3` — a bare-path run dies on the mode, and past it, on
  the Store alias that 20c documents in the same change. The tool knew the
  trap and the instruction walked into it.
- Fixing that, the first `git stash` round-trip reverted the index mode to
  100644 while the working copy stayed `+x`. The new bare-path case still
  passed, because it runs the file off the filesystem, and git is what
  distributes it. There is now an assertion on `git ls-files -s`.

**The general form: when a test cannot fail, find out what would have to be
true for it to fail, and check that thing is reachable.** A mutation is the
cheapest way to ask — break the property on purpose and see whether anything
notices. All three of these took one edit each to expose, and all three had
been green from the day they were written.

**22. A subagent's transcript is a separate file, every record marked — so the
gate's dangerous branch does not exist.** Measured 2026-09-10 against this
session's own history.

`/downstream` hands work to another agent, and that agent's write would meet
the walkthrough gate. Which conversation does the gate then read? Two answers
needed opposite code, and one of them was a trap: if a subagent's records were
interleaved into the parent's transcript, the gate would need
`select(.isSidechain | not)` or a subagent's own chatter would satisfy both
halves — the parent's prompt to it arrives shaped exactly like a human turn,
which is entry 18's injected-turn hole in new clothes. **Blind-adding that
filter under the other answer is worse**: it would match nothing and deny every
write a subagent makes.

The answer is neither. Subagent transcripts live in their own directory beside
the session file:

```
projects/<project>/<session-id>.jsonl          7261 records, isSidechain absent
projects/<project>/<session-id>/subagents/
    agent-<id>.jsonl   x17                     every record isSidechain: true
```

Seventeen of them, 34 to 256 records, **100% `true`**; the parent has the field
on nothing. So there is no interleaving, the contamination case is impossible,
and `.isSidechain // false` is a clean discriminator.

**What the gate does with that:** nothing on the parent path, and on a
sidechain transcript it **warns instead of denying**. Not because the check is
weak there but because the remedy is unavailable — a denial is defensible only
while it is a detour, and a subagent cannot put the missing step in front of a
user and try again. Denying it would be a wall.

**The measurement also made the remaining unknown stop mattering.** Whether the
hook inside a subagent receives its own transcript or the parent's was never
settled, and now need not be: if it gets the parent's, the gate works normally
and correctly; if it gets its own, the discriminator fires and it warns. Both
are safe, so the probe closed the question rather than answering it. **That is
the cheaper shape of answer, and it is worth looking for before building the
apparatus to decide.**

**23. The escape phrase stood down every gate, including one written months
later.** Found while adding G4, 2026-09-10, by a test that expected a denial.

`hooks/confirm_walkthrough.sh` re-reads the whole conversation on every call,
and `[ "$ESC" = 1 ] && allow` meant that a user who said the escape phrase once
had disabled the gate for the rest of the session — every gate, including ones
about steps that had not happened yet. Say it in the morning to skip a pipeline
walkthrough you have seen a hundred times, and the analysis-plan gate is
silently off that afternoon, hours and several subjects later.

Nothing about the first phrase expressed consent to the second thing. **A
blanket escape is a claim about steps the person has not been asked about**,
and it grows every time a gate is added — the newest gate inherits permission
granted before it existed.

Two phrases now, one per concern, and `allow` was replaced by clearing only the
gates the phrase is about. The test that pins it is the pairing, not either
half: `略過計畫` stands G4 down, and `略過導覽` **must not**. Mutating the
second back to the old blanket `allow` fails exactly that one case.

The same shape is worth watching for wherever a session-wide "yes" is read
fresh on every call: the question it answered was asked once, and the answer
does not know what it is being applied to.

**24. The guard against citing an error page rejected every real answer
instead.** Found 2026-09-10 by running `scripts/cite.sh` against the live
resolver rather than a fixture.

DOI content negotiation returns BibTeX, and a resolver that has never heard of
the DOI returns prose with the same 200. So the new entry was checked for the
`@` sigil before being cached — sound, and inverted in practice: the service
answers with **a leading space** before the `@`, so an anchored `case "$body"
in @*)` matched nothing that was real. Every DOI came back
`CITATION NEEDED`, including two that resolve by hand.

What makes this worth an entry is where it would have gone. The failure was
not a crash: it produced a bibliography of markers, in a tool whose whole
purpose is that a missing citation stays visible. **The output looked exactly
like the honest failure mode it was built to produce.** A `.bib` full of gaps
reads as "the resolver was down", and nothing in it says the guard is
backwards.

A fixture would not have caught it — a hand-written one starts with `@`,
because that is what the format looks like when you type it out. The live
service is the only thing that knows about the space. Same lesson as entry 19,
one layer down: it is not enough to test the failure path, the *shape of real
input* has to come from the real source at least once.

The test now carries both — a stub that answers with prose (must not be
cached) and a stub that answers with a leading space (must be). Removing the
trim fails only the second.

**25. Setup ran in one shell and Claude runs in another, on the same machine.**
Measured 2026-09-10, on the Windows laptop.

`commands/setup.md` already decides the Windows terminal — **WSL**, because
16b measured that neither native shell can hold the multiplexed connection.
The member did exactly that. But Claude Code's Bash tool on Windows is Git
Bash (MSYS), and that instruction speaks to the person doing setup, not to the
tool. Nothing joins the two ends:

| | WSL, where setup ran | Git Bash, where Claude runs |
|---|---|---|
| `$HOME` | `/home/<user>` | `/c/Users/<user>` |
| `LAB_SETTINGS_FILE` | exported from `~/.bashrc` | that file is never read here |
| the settings file itself | present | in a filesystem this shell cannot reach |

So every candidate path `settings.sh` reports is truthfully absent while the
settings file is truthfully there. The search report added in T10 — the fix
for "a machine that was set up looks like one that never was" — is correct and
useless here: it answers *where did I look* on a machine where the question is
*which home am I in*. **The same defect, one machine over, and the fix for the
first form does not touch the second.**

Two things make this worth an entry rather than a shrug.

**The visible symptom is the cheap half.** Git Bash is a shell this repo has
already measured and rejected twice, for two unrelated subsystems: 16b (no
fd-passing over MSYS's emulated Unix sockets, so `on_site.sh` cannot open a
session) and 20c (no Windows named pipes, so nothing can reach Positron's
supervisor). A missing settings file is the one failure loud enough to notice.
The other two are a 2FA prompt per call, and a step that reports nothing found.

**The obvious fix is the wrong one.** Copying `env.yaml` to somewhere Git Bash
can see makes `--summary` green in a shell where `on_site.sh` still cannot
open a session — a loud failure traded for a quiet one — and `chmod 600` on the
Windows filesystem does not hold, so the token loses the only protection it has.
The fix is to move the shell, not the file: start Claude Code from WSL.

`settings.sh` now says so when it finds nothing under MSYS. It detects with
`uname -s` rather than `$OSTYPE`: bash sets `OSTYPE` itself at startup, so it
cannot be substituted from the environment and the branch would have no test.
Three assertions in `tests/settings_test.sh`, one negative — a hint that fires
on Linux too teaches the reader to skip the block it is printed in.

**26. Nine GNU-only spellings, four of them silent, and the fix that mattered
was the check rather than the nine edits.** Measured 2026-09-11, prompted by
"this has to work on Mac and Windows too".

macOS ships a BSD userland and bash 3.2. A sweep of `scripts/` and `hooks/`
turned up fourteen call sites that would behave differently or not run at all,
and the split that matters is not GNU-vs-BSD but loud-vs-silent:

| | on a Mac |
|---|---|
| `stat -c %a` in `settings.sh` | **silent** - the token's mode is never checked, so a world-readable token reports as fine |
| `timeout` in `session_start.sh` | **silent** - no runs are ever reported in flight |
| `readlink -f` in `confirm_cleanup.sh` | **silent** - the delete guard stops resolving symlinks, and the shared image library loses its only protection |
| `du -sb` in `push.sh` | **silent** - a 40 GB upload displays as 0 B at the confirmation |
| `stat -c%s` in `install_deps.sh` | loud, and wrong: a successful download reports "could not download" and aborts |
| `timeout` in `on_site.sh` | loud: every call to the site dies |
| `local -A` in `tune_resources.sh` | loud: bash 3.2 cannot parse the file at all |

The nine edits are not the fix; `tests/portable_userland.sh` is. Nine edits
leave the tenth to be found by whoever installs on a Mac next, and four of
these would never announce themselves at all. The check greps the whole tree
for the known-divergent spellings, with two explicit escape hatches
(`# GNU-ok:` on a line, `# GNU-ok-file:` for a file that only ever runs on the
Linux site).

**It earned its keep on the first run.** A careful hand-grep had found nine;
the check found fourteen. One of the five extras was `clocked()` in
`on_site.sh` — `timeout "$secs" "$@"`, missed because the eye was looking for
`timeout` followed by a digit. That one is the wrapper the other four timeout
sites were about to be routed through.

**A fallback chain is not automatically safe, and this one was not.** The
obvious shape is `stat -c %a "$f" || stat -f %Lp "$f"`. Measured here: under
GNU coreutils `-f` means `--file-system`, ignores the format, and prints a
five-line block-count report while exiting non-zero. So an unguarded `||` hands
the caller that block of text as the permission bits the moment the first form
fails for any reason. The guard is two locks: take the second form's output
only if the command succeeded, and only if it is digits — because "it exited
zero" and "it answered the question I asked" are different claims.

Not simulated: bash 3.2, which this machine does not have. The one bash-4
construct was removed rather than guarded, and the static check is what keeps
it gone. `tests/bsd_userland_test.sh` runs the rest against a stub `stat` that
refuses `-c` and a stub `readlink` that refuses `-f`, which catches a wrong
flag and cannot catch a difference nobody thought to stub. **It has never run
on a real Mac, and the release note says so.**

**27. The reason was true, and it was true about something else.** Measured
2026-09-11.

`commands/setup.md` decided where a value should be written:

> Write it to `~/.bashrc` as `LAB_RUNS_DIR` — not to any tool's own settings,
> which reach neither the user's own terminal nor the compute nodes.

Correct, for `LAB_RUNS_DIR`: the site account's non-interactive shells need it,
and so does a person typing commands by hand. But the same reasoning then
governed **where the settings file lives**, and that value has exactly one
reader — this plugin's own scripts. The site does not need it (under
`reach: ssh` the file never crosses), and neither do the compute nodes. So a
constraint that applied to one value silently set policy for another, and the
policy it set was "this must be found through a shell variable".

Three failures follow from that, and they print the same sentence:

- Git Bash and WSL on one Windows machine have separate homes and separate
  startup files, so the export exists and this shell cannot see it (25).
- `zsh`, the default shell on macOS, never reads `~/.bashrc` at all.
- `settings.sh --set` follows `LAB_RUNS_DIR` when it is set, so on a user's own
  machine it writes into a local directory shaped like the site's — findable
  only from a shell that still has the variable. Measured directly.

**The code was already right.** With no variable set at all, `--set` writes to
`${XDG_CONFIG_HOME:-$HOME/.config}/agentic-bioflow/env.yaml` and a fresh shell
with an empty environment reads it straight back — measured. The failure was
manufactured entirely by an instruction telling people to set a variable, and
by an error message whose closing line recommended setting one.

Two general points. **A reason can be correct and still be misapplied one value
over, and nothing about it looks wrong at the new site** — it reads as
considered, which is exactly what stops the next reader from questioning it.
And **when the default is already portable, every configuration mechanism added
on top of it can only subtract**: `$HOME` is the one thing every shell on every
platform agrees about, and each variable layered over it is another way for two
shells to disagree.

---

**28. Three gates could vanish silently, and none of the three ways was a bug
in the gate's own logic.** Found by reading the hooks while planning 2.7, then
measured one by one.

Every safety-net hook reads its input with `jq`. When `jq` is absent the parse
yields an empty string, `CMD` is empty, and each hook takes its own "nothing to
judge here" path and exits 0. The deletion guard, the launch confirmation and
the walkthrough gates all disappear **with nothing printed**. A freshly
installed WSL Ubuntu has no `jq`; neither did macOS before 15. Under
`reach: ssh` these hooks run on the user's own machine, and `setup` step 2
checked for `jq` **on the cluster**, which is the other computer.

They now refuse: `exit 2`, with the one command the user must run themselves.
`exit 2` and not a `deny` decision, because building that JSON is itself a
`jq -n` call — leaning on jq to report jq's absence fails the same way.

Two more, from the same reading:

- **`command -v jq` proves a file exists, not that it runs.** A broken binary —
  wrong architecture, a missing library, a Windows `jq.exe` that Git Bash finds
  and cannot execute — passes that check and then fails every parse, which is
  exactly the silent-gate failure the guard was added to stop. Found by
  accident: a deliberately broken stub written to *test* the guard walked
  straight through it. The guard now asks jq to parse `{}` and checks the
  result.
- **A PreToolUse hook that times out does not block.** The documentation is
  explicit: the call continues through the normal permission flow, so a stalled
  hook is not a gate. Ours carry 5–10 second timeouts, so a slow machine, a
  cold filesystem or a large transcript can switch the safety net off with no
  message. Not fixed here; the mitigation is to keep every hook's work local
  and cheap, and never to add a network call to one.

And one that would have bitten the next author: **exit code 1 is a
non-blocking error** — the action proceeds. Only `exit 2` blocks. A gate
written with `exit 1` looks correct in review and enforces nothing.
