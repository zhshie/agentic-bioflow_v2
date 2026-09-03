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
alert, no state change anywhere Platform shows you. The next launch fails with
`No Tower Agent is online for the selected compute environment`, which reads
like a compute environment problem and is not.

Restarting it is enough; the stale connection has timed out by then. The real
lesson is to run `scripts/preflight.sh` **before** launching rather than after
a launch is refused - it names this in one line, and `/launch` is supposed to.

Note that the connection ID has to be unique per agent. Two members sharing one
produces exactly the error above, permanently rather than transiently.

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

**13. A compute environment's config cannot be edited in place.**
`tw compute-envs update` changes only the name and description. Changing
`nextflowConfig` means `tw compute-envs import --overwrite`, which deletes and
recreates the environment under a new ID — export a backup first. To test a
config change without touching the environment, pass it to `tw launch --config`,
which is appended after the environment's own config.

## Do not rebuild what nf-core already does

**14.** Before writing a check, read the pipeline's module source. Three checks
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
