---
description: Prepare this cluster to run pipelines through Seqera Platform, or repair it when something broke
---

Paths below such as `scripts/...` and `docs/...` are this plugin's own files,
never the user's working directory. Installed as a plugin they are under
`${CLAUDE_PLUGIN_ROOT}`; read them straight from the repository otherwise.

## Open by saying what this is

Before the first question, say what the user is about to use and what it will
do to their machine. Someone who has just installed a plugin knows neither, and
a setup that starts by demanding a storage path reads as an interrogation.

Cover four things, briefly:

- **What it is.** It runs nf-core pipelines through Seqera Platform. It does not
  schedule work or keep run state itself - Platform does both. What it adds is
  the part Platform cannot reach from outside.
- **What is about to happen.** Find what this machine is missing, connect their
  Seqera account, build a compute environment, and then prove the whole path
  works end to end.
- **What it needs from them.** An account, a workspace, and somewhere large to
  put the work. Nothing else.
- **That none of their own data is touched.** The proof at the end runs on
  public test data.

Then ask the first question. **Do not list the commands yet** - that belongs
after step 9, for the reason given there.

Speak the user's language throughout, and say what a step will do before doing
it. The deployment's CLAUDE.md supplies tone and lab norms; nothing here
assumes them.

## Which situation this is

Telling the two apart is the first thing to do.

Read the deployment settings — `docs/SETTINGS.md` says where they live, which
depends on whether this deployment runs on the site or reaches it — and check
for a saved credential. **Missing → first run**, and the person in front of you
may have nothing at all. **Present → repair**, which is short.

---

## Repair

`scripts/preflight.sh`. It reports each part as OK or FAIL. Fix what failed —
each FAIL line names the script that fixes it — then say plainly what was
already fine and what you restarted. Nothing else.

One FAIL is not yours to fix: if the site cannot be reached, preflight prints a
line for the **user** to paste, because opening that connection needs a one-time
code only they have. Show them that line as printed and wait. Do not compose
your own version of it.

Two things worth stating when they come up, because neither is obvious:

- If the outputs-reader had to be restarted, say so, and note that any run
  whose outputs looked missing should now be visible. They were never gone.
- If the site's outbound channel came back on a different host, the compute
  environment is now pointing at the old one. `scripts/ce_apply.sh` shows the
  difference; `--apply` fixes it.

---

## First run

**Two questions before anything else**, because between them they decide which
of the steps below exist at all. Ask both, in this order, and save the answers
as `reach` in the settings (`docs/SITE_ADAPTER.md`, contract 6).

**What kind of compute will this run on?**

- **A cluster Platform cannot reach into** - the case this site adapter was
  written for. All nine steps apply.
- **A compute environment Platform manages itself** (AWS Batch and the like).
  `reach: none`. **Steps 5 and 6 do not apply**: there is no channel to open and
  no outputs reader to keep alive, because Platform reaches both the storage and
  the compute directly. Walking a user through them anyway asks them to install
  and babysit two processes that solve a problem they do not have.

**On a cluster: are you running here, or on your own machine?** Skip this
question entirely for a Platform-managed environment — there is nowhere else to
be.

- **On the cluster itself** → `reach: local`. Nothing below changes.
- **On their own laptop or desktop** → `reach: ssh`, plus `site_host`. Three
  things then differ, and all three are silent failures if missed:
  - **The settings file and the token live on the user's machine**, not the
    site. `docs/SETTINGS.md` covers the move for a deployment that already has
    them on the site.
  - **`storage_root` stays the site's path.** It is where runs live, and that
    has not moved. In step 1, `LAB_RUNS_DIR` goes into the profile of the
    **site** account, not the user's machine.
  - **The site account's shell profile has to be fixed first** — PITFALLS 16c.
    A command sent to the site lands in a non-interactive shell that reads
    `~/.bashrc` but not `/etc/profile`, so `~/bin` is absent and Seqera's CLI
    reports as missing on an account where it is plainly installed. Check it the
    way the failure appears, not the way the file reads; PITFALLS 16c gives the
    one-line check and the guard that fixes it.

  Nothing here is Windows-specific except the choice of terminal, and that one
  is decided: **WSL**. Two other Windows shells were measured and neither can
  hold the multiplexed connection this depends on (PITFALLS 16b).

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

**The three do not all belong on one machine.** The agent and its Java run
where the results are; Seqera's CLI talks to Platform over HTTPS and belongs
wherever Claude is running. With `reach: ssh` those are two computers, and the
user's machine has no use for a runtime it will never start:

- On the user's machine: `scripts/install_deps.sh --cli-only`.
- On the site: `scripts/on_site.sh --script scripts/install_deps.sh`. It ends
  with a `--- settings ---` block naming what it found. Those paths are on the
  **site**, and the settings file that matters is not — so put each one in with
  `scripts/settings.sh --set <key> <value>`. Skipping this leaves the outputs
  reader unable to start, reporting a missing runtime that is in fact installed.

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
