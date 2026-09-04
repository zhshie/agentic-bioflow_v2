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

Re-running `npm install -g @anthropic-ai/claude-code` fixes it in seconds and
is safe while a session is running; the cleanup warning about the busy `.nfs`
file is expected and harmless. That file is only removable once every process
holding it has exited.

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
| WSL2 | expected to work — real AF_UNIX with `SCM_RIGHTS`. **Not yet verified** | — |

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
