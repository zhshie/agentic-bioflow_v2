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

1. **Read the deployment settings** from `$LAB_RUNS_DIR/_personal/env.yaml`:
   `storage_root` and `workspace_id`, plus whatever the site itself needs — on a
   scheduled cluster that includes the account the compute time is billed to
   (`docs/SITE_ADAPTER.md` lists what this site requires). Ask the user for
   anything missing — never guess these, and never copy them from another
   member's file or from anywhere in this conversation. Write them back with
   `chmod 600`. The Seqera token lives in `_personal/.seqera_token`;
   **never print it**.

2. **Egress** — `scripts/egress_ctl.sh status`, start if down. Where a site
   routes outbound traffic through a particular host, that address is baked
   into the compute environment, so a channel that came up somewhere else
   leaves the compute environment pointing at nothing (step 5).

3. **Tower Agent** — `scripts/agent_ctl.sh status`, start if down. Then
   `scripts/agent_ctl.sh online <any recent runId>`: a live local process is not
   the same as an established connection, and only the connection determines
   whether Platform can show run outputs.

4. **Resource contract** — `scripts/check_resource_contract.sh`. If it reports
   drift, fix the site adapter's config before launching anything: a contract
   that no longer matches the site produces jobs the site silently refuses.

5. **Compute environment** — check it exists, and that whatever the site needs
   baked into it still matches reality. `scripts/egress_ctl.sh env` prints the
   current values; **every one of them is required**, for reasons that belong to
   the site, not here (`docs/SITE_ADAPTER.md`).

6. **Launchpad entries** — `tw pipelines list`. For each pipeline the lab uses,
   ensure an entry exists with a pinned revision, so members can launch by name.
   The resource contract rides on the compute environment, not on the entry.

## Report

State plainly what was already fine and what had to be started or changed.
If the agent had to be restarted, say so and note that any run whose outputs
looked missing should now be visible.
