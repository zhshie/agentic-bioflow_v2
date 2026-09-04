# The site adapter

Seqera Platform runs the pipeline. A *site* is where it runs — this cluster,
some other cluster, or a cloud compute environment. Everything that is true of
one site and false of another belongs here, behind a small interface, so that
the command layer can be written once.

This matters more than it looks. On a cloud compute environment there is no
relay to check, no partition to choose and no agent to keep alive; a command
that asks about any of those is a command that only works in one building.

**The command layer may not name a scheduler, a partition, a queue, or a
relay.** It asks *what it needs to know*; the adapter knows how to find out.

---

## What a site must supply

### 1. A resource contract

A Nextflow config that turns whatever a pipeline asks for into something the
site will actually accept — without the pipeline knowing.

*Why it is not optional:* nf-core pipelines request whatever their labels say,
and a site is free to reject that. The mapping must key off the **composed**
request (`task.cpus`, `task.memory`, `task.time`), never off label names, or a
pipeline the adapter has never seen will not run (`PRINCIPLES.md`, invariant 6).

*A site with no constraints supplies an empty config.* That is a valid adapter.

### 2. Egress, and a record of what was refused

How a compute node reaches the internet, and — if anything is blocked — where a
refusal is written down.

*Why:* pipelines fetch containers and reference data at run time. When that is
blocked, the error that reaches Platform routinely names something else
entirely, so a log that names the actual host is the difference between one
round of diagnosis and several.

*A site with open egress supplies nothing and says so.* The command layer must
treat "this site has no egress restrictions" as a normal answer.

### 3. A way for Platform to read the outputs

*Why:* Platform is not on the cluster. Something has to bridge it to wherever
the results landed, and if that bridge is down every output looks like it was
never produced.

### 4. Storage that the compute nodes can see

The work directory and the results area, plus the fact of whether they are
POSIX or object storage.

### 5. A way to ask why a task has not started

*Why:* a task can sit unstarted indefinitely while Platform reports the run as
RUNNING and nothing anywhere records an error. Somebody has to be able to ask
the site directly.

### 6. A way to be reached

Where this deployment runs, *relative to the site*. Settings key `reach`:

| value | what it means | the site it describes |
|---|---|---|
| `none` | there is no login node; nothing can be run on the site at all | a Platform-managed cloud compute environment |
| `local` | this deployment already runs on the site | a login node with a terminal open on it |
| `ssh` | this deployment runs elsewhere and reaches the site over a **multiplexed** ssh connection | the user's own machine |

*Why this is a contract and not a transport layer:* two of the five contracts
above — egress and the outputs reader — exist **only** because this site's
compute nodes have no route out. A cloud site supplies neither, and has nothing
to be reached on either. As a contract, that site costs nothing and its `reach`
is `none`. As an "ssh layer" threaded through the scripts, it would have to be
unpicked. The command layer must treat *"this site has nothing to reach"* as a
normal answer, exactly as it treats a site with no egress restrictions.

`scripts/on_site.sh` is the only sanctioned implementation. **The command layer
may not call `ssh` itself.** `ON_SITE_DRY_RUN=1` makes it print where a command
would run and what it would be, without running it — which is how all three
values are tested with no host, no network and no site.

*A deployment that runs on the site supplies `local`, which is the default.*

---

## What NCHC Taiwania-3 supplies

| Contract | Implementation | Note |
|---|---|---|
| Resource | `configs/sites/nchc.config` | The unusual part: the QOS enforces a resource **floor**, and for most partitions floor == ceiling, so a partition is a fixed-size box. Nextflow has `resourceLimits` for the ceiling and nothing for the floor |
| Egress | `scripts/nf_relay.py`, `scripts/egress_ctl.sh` | Compute nodes have no route out. A CONNECT proxy runs on the login node with a domain allowlist; refusals go to its log. `scripts/check_egress.py` predicts what a pipeline will need |
| Reports | `scripts/agent_ctl.sh` | Seqera's Tower Agent. **Binary files it serves are corrupt** — see PITFALLS 3b; read images from disk |
| Storage | POSIX, under the deployment's run area | The work directory must be visible from the compute nodes |
| Diagnosis | `scripts/why_pending.sh` | Reports the scheduler's own reason in plain language |
| Reach | `local`, or `ssh` from the user's own machine | **Every connection costs a one-time code.** See below — this shapes the whole laptop-driven topology |
| Drift check | `scripts/check_resource_contract.sh` | The box table is a copy of the cluster's QOS table and can go stale |

Per-member, not shared: the egress proxy, the agent and its credential, and
therefore the compute environment too, because the compute environment embeds
the proxy address and the work directory.

### What this site needs in the deployment settings

Beyond `storage_root` and `workspace_id`, which every site needs:
`slurm_account` — the allocation compute time is billed to. Without it nothing
can be submitted.

### What `reach: ssh` costs at this site

Public-key authentication is refused: every ssh connection asks for a password
and then a code from the user's phone, and one bare round trip was measured at
**31 s**. So a multiplexed master connection is not a speed-up here, it is the
only thing that makes the topology possible at all — Claude cannot supply the
code. With a master up, five nested calls cost **0.65 s** together.

Two consequences the command layer has to respect:

- **Claude never opens the master.** `on_site.sh` prints the exact line for the
  user to paste and stops. `preflight.sh` asks first, before any check that
  would otherwise hang on an invisible prompt.
- **One master lasts a work session, and dies with the terminal.** It is a
  process on the user's machine, so closing the window (or WSL shutting the VM
  down) ends it. `ControlPersist` governs idle time, not survival.

The site account's `~/.bashrc` also has to be fixed before any of this works —
see PITFALLS 16c, which is where `ssh host 'tw ...'` reports a missing command
on an account where `tw` is installed.

### What this site needs baked into the compute environment

`scripts/egress_ctl.sh env` prints all of it. Two groups, both required:

- the `both:`-scoped `https_proxy` / `HTTPS_PROXY` / `http_proxy` / `HTTP_PROXY`
- a head-job-only `NXF_OPTS` carrying `-Dhttps.proxyHost` and friends

Both, because **the JVM does not read `https_proxy`**. Setting only the
environment variables leaves Nextflow itself — which is the JVM — with no route
out, while every task it launches has one.

The address is a hostname and a port on a login node. It changes whenever the
channel comes up somewhere else, and a compute environment still holding the
old one fails in a way that looks like the network, not like configuration.

---

## What Platform offers that this site cannot use

Two of Seqera's features are unavailable here, and neither is a configuration
gap that effort would close. Both need Platform to reach the site's storage or
its compute directly, which is the thing this whole adapter exists to work
around. Recorded so nobody spends an afternoon finding out again.

**Studios.** Measured, not inferred:

```console
$ tw studios add --compute-env <this site's CE> --template <any> --name probe
ERROR: Studios are not supported by compute environment with id
'...' of type slurm-platform
```

Seqera's own documentation gives the supported list as AWS Cloud, Azure Cloud,
Google Cloud, and AWS Batch without Fargate. Nothing was created by the probe.

**Data Explorer.** `tw data-links add` requires `--provider`, and it accepts
only `aws`, `azure` or `google`. There is no POSIX option, so a filesystem site
has nothing to register. This costs less than it sounds: on a site like this the
pipeline's inputs are already filesystem paths, which is what Data Explorer
would exist to produce.

Note what is *not* lost with them. **How to see a run's outputs is a separate
question and it works**: Platform's own categorised output listing (through the
outputs reader), the pipeline's HTML report, and the file list `:runs` names.
What a filesystem site does without is a persistent index *across* runs — and
building one here would mean keeping a record of runs, which is what invariant 2
forbids.

**Working, and independent of the compute environment:** datasets, pipelines,
runs, labels, secrets, actions, teams and participants. Verified against this
workspace. One oddity worth knowing: `tw actions list --workspace <id>` answers
"Actions for <user>", so actions appear not to be workspace-scoped the way the
rest are.

---

## Verifying a change to the environment

Two different questions, and using the slow answer for the fast question wastes
three quarters of an hour.

**Did my config reach the run?** Launch `nextflow-io/hello`. Four trivial tasks,
about a minute, no containers. It proves the compute environment carries the
config, that the scheduler accepts what the resource contract produces, that the
account is set, and - because its tasks are tagged `(1)`, `(2)` - that job names
come out sanitised. Use this after every `ce_apply.sh --apply`.

**Is the site actually able to run work?** Launch a real pipeline with
`-profile test`. Slower, and worth it: only this exercises container pulls,
reference downloads through the egress channel, and Platform's ability to read
the outputs back. This is the proof run at the end of onboarding, and it must
touch none of the user's own data.

The first question is the one asked most often, and it was being answered with
the second - a 45-minute funcscan run to look at a job name.

---

## Adding a site

Do not write a second adapter speculatively. The contract above was derived
from one real site, and a contract with one implementation is a guess about the
second (`PRINCIPLES.md`, invariant 8). Write it when there is a real site to
run on, and expect the contract to change when you do — that is the point of
having written it down.
