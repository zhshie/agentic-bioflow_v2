---
description: Prepare this cluster to run pipelines through Seqera Platform, or repair it when something broke
---

Paths below such as `scripts/...` and `docs/...` are this plugin's own files,
never the user's working directory. Installed as a plugin they are under
`${CLAUDE_PLUGIN_ROOT}`; read them straight from the repository otherwise.

Two situations, and telling them apart is the first thing to do.

Read `$LAB_RUNS_DIR/_personal/env.yaml` (every key is described in
`docs/SETTINGS.md`) and check for a saved credential.
**Missing, or `LAB_RUNS_DIR` is not set → first run**, and the person in front
of you may have nothing at all. **Present → repair**, which is short.

Speak the user's language, and say what a step will do before doing it. The
deployment's CLAUDE.md supplies tone and lab norms; nothing here assumes them.

---

## Repair

`scripts/preflight.sh`. It reports each part as OK or FAIL. Fix what failed —
each FAIL line names the script that fixes it — then say plainly what was
already fine and what you restarted. Nothing else.

Two things worth stating when they come up, because neither is obvious:

- If the outputs-reader had to be restarted, say so, and note that any run
  whose outputs looked missing should now be visible. They were never gone.
- If the site's outbound channel came back on a different host, the compute
  environment is now pointing at the old one. `scripts/ce_apply.sh` shows the
  difference; `--apply` fixes it.

---

## First run

Nine steps, and **the order is forced** — each one blocks the next. Doing them
out of order strands the user somewhere that reports nothing useful.

**1. Where the work will live.** Everything derives from this, so it is first.
Ask for a location that is large (a single run's intermediates can exceed
100 GB), outside any code checkout, and visible from the machines that will do
the work. A home directory is usually the wrong answer: quotas there are small
and container images will fill it.

Write it to `~/.bashrc` as `LAB_RUNS_DIR` — not to any tool's own settings,
which reach neither the user's own terminal nor the compute nodes. Save it as
`storage_root` in the settings file too.

**2. What must already exist.** Check for `nextflow`, `git`, `jq`, `curl` and
the container runtime. **Report what is missing; do not install it** — these
are the cluster's to provide, usually through its module system, and guessing
at that is how a setup script becomes site-specific.

**3. Seqera.** This is the part that has no local shortcut, so point at it
plainly rather than wrapping it:

- an account at seqera.io, and a workspace — **if someone gave the user a
  workspace ID, this is where it goes**; otherwise they create their own
- a personal access token, saved to `_personal/.seqera_token`, `chmod 600`,
  **never printed, never in git, never in a params file**
- `tw info` to confirm the token works

Save `workspace_id`. Mention that a free plan limits concurrent runs and how
much history is kept, so a busy lab notices before it surprises them.

**4. The pieces this cluster does not ship.** `scripts/install_deps.sh`.
It downloads a Java runtime, Seqera's agent, and Seqera's CLI into the
execution area and records the paths. Tell the user it fetches a few hundred
megabytes once. It is safe to re-run.

**5. The outbound channel.** `scripts/egress_ctl.sh start`. On a site whose
compute nodes cannot reach the internet this is what carries container pulls
and reference downloads; where they can, the adapter says so and this is
quick. It picks its own port, so several members on one machine do not collide.

**6. The outputs reader, then its credential — in that order.**
`scripts/agent_ctl.sh start`, then `scripts/agent_ctl.sh register`.
**Registering first fails**: Seqera will not issue a credential for something
it cannot see. `start` assigns a connection identifier if there is none and
records it; it has to stay the same afterwards, because the credential is tied
to it, and two people sharing one are refused permanently rather than
intermittently. `register` prints the credential name to use in the next step.

**7. The compute environment.** `scripts/ce_apply.sh`. With none present it
builds the first one from the site's template; it always shows what it will do
and stops, so read that out before passing `--apply`.

**8. Prove it, without touching their data.** Two runs, and they answer
different questions — `docs/SITE_ADAPTER.md` explains why both:

- `nextflow-io/hello` — about a minute. Proves the configuration reached the
  run and the site accepted the job.
- any nf-core pipeline with `-profile test` — slower, and the only thing that
  proves containers can be fetched, reference data can be downloaded, and
  Platform can read the results back.

Say explicitly that this uses public test data and touches nothing of theirs.

**9. Only now, say what they can do.** Introduce `launch` and `runs`.
**Not before step 8 passes** — someone handed a command list will use it, and
an unverified environment is how real data meets a broken setup.

---

## When a step fails

Say which step, what the failure means, and what to do — then stop. Do not
continue past a failed step: everything after it depends on it, and the errors
it produces will describe the wrong problem.
