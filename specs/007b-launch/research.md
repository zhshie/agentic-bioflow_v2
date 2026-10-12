# Research: 007b-launch (2026-10-11)

Sources:
- the repository at bd9d42b;
- read-only commands on the NCHC login node lgn304, run through `scripts/on_site.sh`;
- Seqera's public documentation (`docs.seqera.io`).

No Seqera service, MCP or `tw` was called, and nothing was submitted.

## How Seqera launches on Slurm

On the cluster, Seqera generates `_work/nf-<id>.launcher.sh` (run 2tbVWDAaENzn7o, Slurm job 2131533). The script has:
- `#SBATCH -D <launchDir>`, `-J nf-workflow-<id>` and `--no-requeue`, then the head queue (`-p ngs26G`) and the head options (`-A MST109178 -c 4 --mem=26G -t 4-00:00:00`).
- Exports of `NXF_*`, the config written from base64 to `NXF_CONFIG_FILE`, and then:

  ```
  nextflow run https://github.com/nf-core/ampliseq -name <name> -params-file <yaml> -with-tower <endpoint> -r 2.18.0
  ```

  The run is started in the background and waited on.
- Head options come from the compute environment and cannot be changed at launch (docs: [HPC compute environments](https://docs.seqera.io/platform-enterprise/compute-envs/hpc)). In this repository they are in `configs/sites/nchc-ce.json.in`. `-c` and `--mem` must equal the QOS floor.

**Security finding.** Seqera's launcher script is mode 755 and carries the Tower access token as base64 in `NXF_PRERUN_BASE64`. Only the parent folder's mode 700 protects it. We do not copy this pattern: our token goes into a 0600 file (FR-004).

## What a correct ampliseq run on NCHC needs

- **Config**: `configs/sites/nchc.config`:
  - the Slurm executor, with the box table `ngs7G`…`ngs372G` inside `withName:'.*'` (PITFALLS 6);
  - `clusterOptions "-A ${SLURM_ACCOUNT} -p <queue> -c N --mem=XG"`;
  - a `jobName` cleaned of `|`, and `queueSize` 50;
  - Singularity with `autoMounts` and `cacheDir`;
  - the proxy env on head and tasks: `http(s)_proxy=http://lgn304:18080`. The head also needs `NXF_OPTS` with `-Dhttp(s).proxyHost/Port`, because the JVM ignores `https_proxy`.
- **Versions on the cluster**: Java Temurin 17.0.10; Nextflow 25.10.4 (`~/bin/nextflow`); singularity-ce 3.11.1 (the bare binary).
- **Acceptance inputs**, from the 2026-09-20 run (`project/Lab/agentic-bioflow/projects/microbiome_test/runs/ampliseq_sclerotia_d5_noviz_20260920/params.yaml`):
  - Samplesheet `sample,fastq_1`, single-end, with ten rows (`Day5_ASW_{42,43,46,53,55}`, `Day5_SW_{36,46,51,52,55}`) pointing at `rawdata/` on the cluster.
  - `FW_primer AGRGTTYGATYMTGGCTCAG`, `RV_primer RGYTACCTTGTTACGACTT`, `pacbio: true`, `dada_ref_taxonomy: silva=138.2`, `skip_barplot` and `skip_alpha_rarefaction` true. The pipeline is `-r 2.18.0`.
  - The run completed with 71 tasks, 0 failed.
- **Egress**: every host ampliseq needs is already allowed in `scripts/nf_relay.py`.
- **Image cache**: the September cache is `/work/u9613010/lab_runs/.singularity_cache` (5.5 GB, 15 images). The deployment's own `_singularity_cache` is empty.
- **Layout traps for 008 `rebuild`**:
  - Seqera used one shared launch dir and `NXF_LOG_FILE`, so `.nextflow/history` was never written in a per-run place. We use one launch dir per run and set neither `NXF_LOG_FILE` nor `-log`.
  - The trace file is named in the log line "Workflow started -- trace file:". Ampliseq writes its own trace. Other pipelines get `-with-trace`.

## nf-tower on the cluster's Nextflow

Nextflow 25.10.4 loads nf-tower 1.17.5 (log: `Plugins default=[nf-tower@1.17.5]`). In its `TowerClient.groovy`:
- A failure of `create` or `begin`, including a connection failure, aborts the run (:282-289, :374-381).
- A failure of `progress`, `heartbeat` or `complete` only logs a warning (:416, :814, :824).
- `http://` endpoints are accepted (`checkUrl`, :215).

008's payload fixtures come from nf-tower 1.28.3 on Nextflow 26.04.7, so 1.17.5 payloads must be recorded and tested (FR-007).

## The way back to the platform (measured 2026-10-11)

- Compute nodes reach the login node freely: the head job ran on `cpn3863` and used `lgn304:18080`, and `_relay/relay.log` has 2250 "from cpn…" lines.
- **SSH reverse forward.** `ssh -S <ControlPath> -O forward -R 0.0.0.0:28933:127.0.0.1:18787` on the user's ControlMaster was accepted, but sshd bound it to `127.0.0.1:28933` only (`ss -ltn`).
  - A `curl` to `127.0.0.1:28933` on lgn304 reached the laptop.
  - A `curl` to `lgn304:28933` failed.
  - So `GatewayPorts` is off, and compute nodes cannot use the forward directly.
  - The forward was removed with `-O cancel`.
- **The relay** (`scripts/nf_relay.py`, user process on lgn304, `0.0.0.0:18080`) only lets compute nodes in (`ALLOW_HOST_PREFIXES`). It forwards CONNECT and plain HTTP to an allow-listed host. Because it runs on lgn304, it can reach `127.0.0.1:<forward port>`. That is the bridge.

| Option | Verdict |
|---|---|
| Forward on `0.0.0.0` | Not possible: sshd binds loopback only. |
| Relay to a loopback forward | **Chosen.** No new process, because the relay already runs. It needs one narrow allow rule: loopback plus the one forward port. |
| The agent reads the run folder's records on request | Kept as the fallback and the truth after a gap (008 rebuild). It cannot be live, which the maintainer asked for. |
| A head job on the login node | Rejected. The login-node motd says intensive work must go through the scheduler, and there is an idle logout. |
| A receiver daemon on the login node | Rejected by principle 2. |

## NCHC login-node rules (`/etc/motd`)

- Short work only.
- Slurm queries sustained under 30 s for more than 5 minutes count as an attack; continuous queries over 10 minutes are terminated.
- Repeat violation means a one-week suspension.

The platform never polls Slurm. `cancel_run` calls `squeue` once per cancel.

## Cancel today

The plugin cancels only through `tw runs cancel` (`scripts/relaunch_with_override.sh:206,259`).

`scancel` appears in no hook, script or constitution text. Its only mentions are the 007 agent's refusal list (`specs/007-station-agent` TC-060, TC-064) and the workspace's own permission rule for the assistant.

On SIGTERM, Nextflow's head job cancels its tasks and sends `complete`.
