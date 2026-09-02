---
description: Prepare or repair this cluster's connection to Seqera Platform (idempotent)
---

Bring the execution environment to a working state. Every step checks before it
acts, so running this twice is harmless — that matters because the two daemons
below do not survive a login-node reboot.

## What this covers

Seqera Platform owns the compute environment, credentials, and Launchpad. This
command drives `tw` to create or update them, plus the two local daemons that
Platform cannot provide for a firewalled cluster.

## Steps

1. **Read the deployment settings** from `$LAB_RUNS_DIR/_personal/env.yaml`
   (`slurm_account`, `storage_root`, `workspace_id`). Ask the user for anything
   missing — never guess these, and never copy them from another member's file
   or from anywhere in this conversation. Write them back with `chmod 600`.
   The Seqera token lives in `_personal/.seqera_token`; **never print it**.

2. **Relay** — `scripts/relay_ctl.sh status`, start if down. The URL is built
   from the *current* hostname; this site has several login nodes and a stale
   name points at a node with no relay.

3. **Tower Agent** — `scripts/agent_ctl.sh status`, start if down. Then
   `scripts/agent_ctl.sh online <any recent runId>`: a live local process is not
   the same as an established connection, and only the connection determines
   whether Platform can show run outputs.

4. **Partition table** — `scripts/check_partitions.sh`. If it reports drift,
   update `configs/nchc.config` before launching anything; a stale box means
   jobs that never schedule.

5. **Compute environment** — check it exists and its proxy variables point at
   the *current* relay host. If the relay moved, update the CE:
   `scripts/relay_ctl.sh env` prints paste-ready values. Both the `both:`-scoped
   proxy variables and the head-only `NXF_OPTS` are required — the JVM does not
   read `https_proxy`.

6. **Launchpad entries** — `tw pipelines list`. For each pipeline the lab uses,
   ensure an entry exists with a pinned revision and `configs/nchc.config`
   attached, so members can launch by name.

## Report

State plainly what was already fine and what had to be started or changed.
If the agent had to be restarted, say so and note that any run whose outputs
looked missing should now be visible.
