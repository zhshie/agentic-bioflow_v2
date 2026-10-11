# Research: 007-station-agent (2026-10-11)

Only public documentation was read. No Seqera service, API, MCP or `tw` was called (ADR 0004).
- C = https://docs.seqera.io/platform-cloud/compute-envs/
- N = https://docs.seqera.io/nextflow/

## Seqera Platform compute environments (CE)

There are 15 types (C overview):
- Seqera Compute
- AWS Batch
- Azure Batch
- Google Batch
- AWS Cloud, Azure Cloud, Google Cloud (one VM per run, `local` executor)
- Kubernetes, Amazon EKS, Google GKE (`k8s`)
- Slurm, PBS Pro, LSF, Grid Engine, Moab (one HPC page)

The shared object comes from https://docs.seqera.io/platform-api/info/compute-envs-info. It has these fields:
- `id`, `name` (unique, 1–100 characters), `description`
- `platform` (the type), `credentialsId`
- `status`, `message`, `primary`
- `dateCreated`, `lastUpdated`, `lastUsed`
- `config`, which holds `workDir`, `preRunScript`, `postRunScript`, `environment[{name,value,head,compute}]`, `nextflowConfig`, and the type-specific fields

The status values seen are AVAILABLE, INVALID, CREATING, DELETING and ERRORED. The documentation does not give the full list.

Other behaviour:
- **Primary CE**: one per workspace, and it is the default for a launch.
- **Disabled CE**: blocks new runs. Runs already going are allowed to finish.

| CE type | Nextflow executor | Credentials (Seqera) | Key fields | Where the head job runs |
|---|---|---|---|---|
| Seqera Compute | not stated | Seqera-managed | region, relative work dir, scripts | not stated |
| AWS Batch | awsbatch | AWS keys or role ARN | region, S3 work dir, head and compute queue, Forge options, head CPU and memory | Batch head queue or Fargate |
| AWS Cloud | local | AWS keys or role ARN | S3 work dir, instance type, AMI, VPC | the single EC2 VM |
| Azure Batch | azurebatch | shared keys, Entra service principal, or managed identity | region, az:// work dir, VM type and count or pool, head VM | a separate head pool |
| Azure Cloud | local | Entra service principal | location, container work dir, instance type, VNet | the single VM |
| Google Batch | google-batch | service-account key or Workload Identity Federation | location, gs:// work dir, Spot, head CPU and memory | a Batch job |
| Google Cloud | local | service-account key or Workload Identity Federation | instance type, zone, image, VPC | the single VM |
| Kubernetes | k8s | service-account token or X509 certificate, plus the CA certificate | control-plane URL, namespace, head service account, storage claim, mount path | head pod |
| Amazon EKS | k8s | AWS keys or role | cluster, region, namespace, service accounts, storage | head pod |
| Google GKE | k8s | service-account key | cluster, location, namespace, service accounts, storage | head pod |
| Slurm / PBS Pro / LSF / Grid Engine / Moab | slurm / pbspro / lsf / sge / moab | SSH, managed identity, or Agent | login host, work dir, launch dir, head queue, compute queue, queue size, head-job submit options | a cluster job in the head queue |

## How HPC is reached (C hpc; https://docs.seqera.io/platform-cloud/supported_software/agent/overview)

There are two ways:
- **SSH**: Platform connects to the login node itself.
- **Tower Agent**: a process on the login node opens an outbound, authenticated WebSocket to Platform. It runs commands as the Linux user who started it and needs a personal access token plus a connection ID. Keys and scheduler credentials stay on the cluster. It needs only outbound HTTPS, and sends a heartbeat every 45 s.

Either way, the Nextflow head job runs as a cluster job in the head queue.

## Pre-flight (https://docs.seqera.io/platform-enterprise/compute-envs/preflight-checks)

- **When a CE is created or updated**: a credential that has been deleted or is INVALID gives a 400.
- **Every 12 hours**: cloud credentials are probed through the provider's API, and a CE whose credential is INVALID becomes INVALID.
- **At launch**:
  - CE status
  - credential status
  - Wave (if used)
  - for HPC, whether the agent is online

  All failures are reported together.
- HPC has no credential probe.

## Running each type without Seqera (N executor pages)

- local VM: `local`
- AWS Batch: `awsbatch` with `queue` and an `s3://` workDir
- Azure Batch: `azurebatch` with an `az://` workDir
- Google Batch: `google-batch` with `google.project`, `google.location` and a `gs://` workDir
- Kubernetes: `k8s` with `k8s.storageClaimName` and `k8s.storageMountPath`
- HPC: `slurm`, `pbspro`, `lsf`, `sge` or `moab`, with `queue` and `clusterOptions`, run from a login node that has the submit command

Seqera Compute has no counterpart outside Seqera.

## Reuse in this repository

- `scripts/on_site.sh` already manages one shared SSH ControlMaster per site. The user opens it once with their one-time code; it uses `ControlPersist=8h`, and its strict rules live in that script.
- The station agent uses `on_site.sh` for every site command. It does not open its own SSH.
- `docs/SITE_ADAPTER.md` is the contract for what a site must supply.

## Decisions

| Item | Decision | Why |
|---|---|---|
| Tower Agent | Not used | Its wire protocol is undocumented, and it talks only to Seqera. We copy its pattern instead: outbound only, a per-agent token, and a heartbeat. |
| Transport | Long-poll HTTPS, not WebSocket | Fewer moving parts for one developer. It is outbound only, like Tower Agent. |
| Seqera Compute | Not needed | It is Seqera's own managed AWS and has no counterpart outside Seqera. |
| Credentials | Kept by the station agent, never by the platform | The 10-08 red line. The platform stores only the name of a credential. |
| Types other than Slurm | Modelled now, enabled one at a time | Constitution §II-4: a second site adapter is written only when a real second site exists. Each type needs a real account first. |

## Compute environment type identifiers (read 2026-10-11, executor)

Only public documentation was read, through `docs.seqera.io` (its `llms-full.txt` text export of the same pages). No Seqera service, API, MCP server or `tw` was called.

- Source A, the platform value table: https://docs.seqera.io/platform-enterprise/enterprise/configuration/overview (section "Compute environments", table "Available platform values").
- Source B, the command names: https://docs.seqera.io/platform-cloud/cli/commands (`tw compute-envs add <type>`).

The API reference page for the compute environment object (https://docs.seqera.io/platform-api/info/compute-envs-info) is drawn in the browser and its text export does not list the allowed values of `platform`. So the value of the `platform` field is taken from source A, the only place the public documentation names a type identifier. If Seqera's API uses another spelling, only this table and `abf_platform/compute_envs.py` change.

| Type | `platform` identifier (source A) | `tw` command (source B) | Slice 1 |
|---|---|---|---|
| Slurm | `slurm-platform` | `slurm` | supported |
| PBS Pro (Altair) | `altair-platform` | `altair` | modelled only |
| IBM Spectrum LSF | `lsf-platform` | `lsf` | modelled only |
| Grid Engine | `uge-platform` | `uge` | modelled only |
| Moab | `moab-platform` | `moab` | modelled only |
| AWS Batch | `awsbatch-platform` | `aws-batch` | modelled only |
| AWS Cloud | `awscloud-platform` | `aws-cloud` | modelled only |
| Azure Batch | `azbatch-platform` | `azure-batch` | modelled only |
| Azure Cloud | `azcloud-platform` | `azure-cloud` | modelled only |
| Google Cloud Batch | `googlebatch-platform` | `google-batch` | modelled only |
| Google Cloud | `googlecloud-platform` | `google-cloud` | modelled only |
| Kubernetes | `k8s-platform` | `k8s` | modelled only |
| Amazon EKS | `eks-platform` | `eks` | modelled only |
| Google GKE | `gke-platform` | `gke` | modelled only |
| Seqera Compute | none in source A | `seqera-compute` | refused: Seqera's own hosted service, no counterpart |

Source A also lists `local-platform` ("evaluation and development only"); it is not one of the 14 and is refused as an unknown type.

The Slurm options in source B give the field names used for the Slurm `config`: `workDir`, `launchDir`, `headQueue`, `computeQueue`, `maxQueueSize`, `headJobOptions`, `hostName`, `userName`, `port`, plus the shared `preRunScript`, `postRunScript`, `nextflowConfig` and `environment`.
