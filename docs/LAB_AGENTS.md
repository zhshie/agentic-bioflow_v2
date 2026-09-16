# Lab AI agents and this plugin

Other AI agents in a lab — a shared assistant on a lab machine, a member's own
agent, something running in a cloud sandbox — will eventually want what this
plugin already does: launch a pipeline, check on a run, read what came out of
it. This document is the decided design for how much of that they get, and
why. It is the settled version of plan section A ("N9：串接 Lab AI agent",
`~/.claude/plans/curious-doodling-lightning.md`); where this document and that
plan differ, this one is newer and wins.

Everything here follows the same rule the rest of this repo follows
(`PRINCIPLES.md`, invariant 8): a claim about this repo cites the file that
proves it, and a claim this track could not measure is labelled **unverified**
rather than asserted. Section 10 collects every one of those in one place.

---

## 1. The constraint is the site's 2FA, not WSL

The question that started this track was whether running on WSL limits what a
lab agent can do. It does not, and the actual constraint is site-shaped, not
shell-shaped: **every ssh connection to NCHC costs an interactive 2FA code
from a person's phone, and public-key auth is refused outright.**

```
one bare round trip = 31.3 s
each trip prompts: 2FA method -> password -> OTP from the user's phone
```

Measured 2026-09-04 against `t3-c4.nchc.org.tw` (`PITFALLS.md` 16). This is
why `scripts/on_site.sh` exists at all: "a multiplexed master connection is
not a speed-up here, it is the only thing that makes the topology possible at
all — Claude cannot supply the code" (`docs/SITE_ADAPTER.md:126-127`), and the
script's own `no_master()` function refuses outright and prints the exact
line for a person to paste (`scripts/on_site.sh:70-81`) — it never attempts
to open one itself, because the code that authenticates it lives on a phone
the agent cannot read.

WSL only enters the picture because of *which shells can hold that master
connection open at all*. Measured across all three Windows shells
(`PITFALLS.md` 16b): PowerShell's OpenSSH cannot multiplex at all
(`getsockname failed: Not a socket`), Git Bash's control plane looks alive but
cannot open a session (`ssh -O check` succeeds, then
`mux_client_request_session: read from master failed: Connection reset by
peer` — MSYS's Unix sockets are emulated and do not implement the
file-descriptor passing a session needs), and only WSL2 actually works,
verified 2026-09-05 across a multi-hour deployment.

**What that does *not* establish, measured 2026-09-15 (`PITFALLS.md` 16g):**
a shell whose own ssh cannot hold a master can still *call* one that can.
`wsl.exe -e ssh` from Git Bash, over a master opened in a WSL window, answered
in 0.55 s with no one-time code and carried binary input and exit codes
intact. So the rule is not "Windows can only reach the site from WSL"; it is
"the master lives in WSL, and this version drives it from there". Native Git
Bash stays refused for a smaller reason — `scripts/on_site.sh` detects it by
`uname -s` and stops in `wrong_shell()` — and that reason is now the rest of
the Linux userland (python3 on PATH is a Microsoft Store stub, 20c; no `jq`;
the test suite does not run there), which makes it 🚧
recognised-but-unsupported in `docs/CONDITIONS.md` rather than ⛔ blocked.
It is still a branch every `on_site.sh` call goes through, not prose.

And even WSL does not remove the 2FA cost, it only makes the *one* master
connection per work session possible: PITFALLS 16e measured that too many
`on_site.sh` calls on one master silently hang rather than error (this site's
sshd caps concurrent sessions per TCP connection at `MaxSessions`, default
10), and PITFALLS 25 measured a second, unrelated failure on the same
Windows laptop — setup ran in WSL, Claude's own Bash tool runs in Git Bash on
the same machine, and the two have separate `$HOME`s, so a settings file that
genuinely exists is genuinely invisible to the shell Claude actually runs in.
Neither of those is a WSL problem to fix; both are consequences of the same
underlying fact — **the connection is a scarce, human-authenticated resource,
and every design decision in this section exists to spend it carefully.**

This holds for a Mac, a Linux box, or a Windows laptop equally: none of them
can supply an OTP on an agent's behalf, so none of them changes the shape of
the constraint. What changes is only whether a given host *can* hold the one
kind of connection that ever gets past it — which is exactly the host table
below.

## 2. Where a lab agent can run

| Host | Needs WSL? | Can reach the cluster? |
|---|---|---|
| A lab's own, always-on Linux box | No | Yes — but a person still has to type the OTP that opens the connection, and it has to be reopened if it drops |
| A member's Windows laptop | Yes — the master must live in WSL and this version drives it from there (Git Bash's own ssh cannot hold it, PITFALLS 16b; it *can* call WSL's, 16g, but that bridge is not built) | Same as above, once in WSL |
| The login node itself (`reach: local`) | No | Yes, and with no 2FA cost at all — but whether NCHC permits a persistent process on the login node is **unverified** (§10, M6) |
| A cloud-hosted agent (Claude Tag, Managed Agents, and similar) | Not relevant | **No** — it cannot reach the lab machine holding the shared connection, and cannot supply an OTP itself |
| Anywhere, using only Seqera Platform (`tw` / Seqera's own MCP) | Not relevant | Does not touch the cluster at all — status, logs, and (per §5) even launching go over HTTPS to Platform |

The last row is its own category, not a degraded version of the others:
nothing about it depends on reaching the site, so it is unaffected by
everything in §1. Call it **Platform-only**.

`docs/CONDITIONS.md` (written alongside this document, in the same release)
is where this becomes a matrix dimension a script can check — "Lab agent
host" joins the existing dimensions there (machine, interface, compute
environment, and so on). This document explains *why* that dimension has the
rows it has; `docs/CONDITIONS.md` is where a script reads it.

## 3. Tiers: what a runtime may do, and how that is enforced

The axis that decides is not "which product" — Claude Tag, a lab's own Linux box,
Managed Agents, OpenClaw, Hermes are all instances of the same two questions:
**does this runtime load this plugin's hooks, and can it reach the shared ssh
connection at all?**

| Tier | Condition | May do | May not do | How that is enforced |
|---|---|---|---|---|
| **H1** — a person, interactively | Claude Code with hooks loaded, a human present | Everything | — | The existing hooks, unchanged |
| **H2** — unattended, with hooks | Claude Code headless or the Agent SDK, this plugin's hooks loaded (**hooks load under `claude -p` — measured 2026-09-14; whether PreToolUse gates then refuse is unverified — §10, M4**), running on a lab Linux box or the login node | Non-destructive, non-submitting cluster operations: `push`, `fetch`, `agent_ctl.sh`/`egress_ctl.sh` start/status, `why_pending.sh`, `task_health.sh`, `preflight.sh`; read-only Platform queries; **preparing** a run (samplesheet, params, the full launch command) for a person to approve | Submitting a run, deleting anything | The existing hooks (§5) plus, planned, a Seqera token with no launch permission (§10, M5) |
| **H3** — shared identity, no hooks | Claude Tag, Managed Agents, OpenClaw, Hermes, Codex, or anything else that reaches this plugin's files without a hook mechanism to run them | Read-only Platform queries: look up a run, read a report | Touch the cluster, submit a run, delete anything | **Structural, not textual — and planned, not built**: the design is to hand this tier a Seqera token with only a view role and no ssh access, so there is no credential to intercept. Nothing provisions such a token today (a deployment has one token, `docs/SETTINGS.md`), and whether a view-role token really cannot launch is unverified (§10, M5) |

H3's enforcement is worth stating plainly because it is the one row that would
not lean on this plugin's own machinery at all: a runtime with no ssh
credential and a view-only Platform token could not touch the cluster no matter
what it is told to do — the thing that would have to exist for the action to
succeed simply would not be there.

**Said in the future tense on purpose.** Today it is a design, not a fence:
no code here creates or scopes a Seqera token by role, `scripts/on_site.sh`
never consults a tier, and a deployment has exactly one token that everyone
shares. Its premise is M5, still unverified. Until both are settled, an H3
runtime that can read a deployment's settings file holds the same token
everyone else does — so do not give one that access and call it safe. This is
the correction
this track makes to the earlier proposal's R6, which had treated the
shared-identity case as an open, text-enforced question (§7, row R6).

## 4. The rule

**A runtime with no plugin hooks loaded never touches the site.** Not
"should not" — this plugin has no other mechanism that could stop it, and
writing the rule down does not by itself enforce it. What enforces it is §3's
H3 row: a runtime in that position is never handed anything that reaches the
cluster in the first place. `docs/CONDITIONS.md` and its
`scripts/detect_conditions.sh` are where this rule becomes a check a script
runs, rather than a sentence someone has to remember.

## 5. Unattended agents prepare; a person launches and deletes

This is not new in this release — it already holds today, and this section
says exactly which files make it hold and how precisely, rather than
repeating it as a slogan.

**Launching.** `hooks/confirm_walkthrough.sh` gates the walkthrough steps
`launch.md` has required for two releases: G1 (samplesheet work requires the
pipeline's diagram was shown), G2 (writing `params.yaml` requires the schema
was read *and the user answered*), and G3 (a launch or relaunch command
requires both, as a backstop). All three `deny()` with
`permissionDecision: "deny"` (`hooks/confirm_walkthrough.sh:87-88`) — this is
a structural block, not advisory text. G2's evidence requirement is a reply
from **the user**, specifically (`ANS` in the script), and a subagent's own
transcript is a separate file that cannot contain a parent conversation's
reply (`hooks/confirm_walkthrough.sh:306-311`, citing PITFALLS 22): "G1/G2/G3
keep denying: their remedy is not starting a run, and an unattended agent
starting one is exactly what they are for" (same comment, verbatim). In
practice this means an unattended run has no real human turn to point to as
evidence, so G2 and its backstop G3 deny by default — not because the hook
asks "is anyone watching", but because the thing it demands as proof does not
exist without a person.

Since 2.9, `hooks/confirm_launch.sh` also returns `permissionDecision: "ask"`
with the full command as the reason, so Claude Code itself asks before a
launch-shaped command runs, on top of the conversational gate it already
added. **What `ask` does when nobody is there to answer — `claude -p`, the
Agent SDK, `bypassPermissions` — is not documented and not measured** (§10,
M4). Do not rely on it for an unattended host; G3 in `confirm_walkthrough.sh`
remains the stop that needs a human turn.

**Deleting.** `hooks/confirm_cleanup.sh` hard-denies `rawdata/`, `results/`,
`analysis/` and `.nextflow/plugins/` unconditionally, with the same
`permissionDecision: "deny"` mechanism (`hooks/confirm_cleanup.sh:87-90`,
the deny calls at `:284`, `:290`) — this holds for any runtime, attended or
not, and needs no human-turn check because it never permits the action at
all. Since 2.9, deleting `work/` or the Nextflow cache returns
`permissionDecision: "ask"` as well (`hooks/confirm_cleanup.sh`), where 2.8
only added advisory text. The same unmeasured question applies: on an
unattended host, whether `ask` becomes a refusal or a pass depends on the
permission mode, which is why an H2 agent is told never to delete (§3) and
why that rule is not yet claimed as structurally enforced.

## 6. Machine-readable signals from `scripts/on_site.sh` (2.9)

Built and tested in 2.9 (`tests/on_site_test.sh`, `tests/on_site_parallel_test.sh`):

- **`on_site: needs-human reason=no-master`** — added to `no_master()`'s
  stderr, alongside the existing message, so a lab agent (H2) can detect the
  need for a human without parsing prose. Same idea for
  `sessions_exhausted()`: `on_site: needs-human reason=sessions-exhausted`.
  Exit code stays 2 in both cases. The plugin still names no chat tool and
  decides nothing about how the lab agent notifies a person — that choice
  stays with whoever operates it.
- **`ssh_max_parallel`** — a new settings key, default 4, that caps how many
  concurrent sessions `scripts/on_site.sh` opens on one master using a lock
  directory (`mkdir`, not `flock` — `flock` is not portable to a Mac). A
  caller that cannot get a slot waits until `ON_SITE_TIMEOUT`. This exists
  because PITFALLS 16e's hang is *easier* to reach with more than one caller
  sharing a master, which several H2 agents doing exactly that would be.

## 7. Review of the integration proposal (R1–R10)

The original proposal document
(`~/.claude/plans/agentic-bioflow-lab-agent-integration.md`) is **not present
on this machine** — confirmed by its absence from
`~/.claude/plans/` and by the lab architecture draft's own note that it could
not find the file either
(`~/.claude/plans/lab-ai-agent-ai-agent-protocol-meeting-proud-pony.md:9`).
The table below is the plan's own review of it against this repo's actual
source (`~/.claude/plans/curious-doodling-lightning.md`, section A3), which is
the decided design this document is required to reflect regardless.

| # | Proposal | Verdict | Correction, with the file that proves it |
|---|---|---|---|
| R1 | Enable nf-core's `nf-prov` plugin for provenance (RO-Crate/WRROC) | **Adopted, with a correction** | The proposal assumed compute nodes cannot download a plugin and it must be pre-staged. That is wrong: `scripts/nf_relay.py`'s domain allowlist already carries `nextflow.io`, with the comment noting that missing it "makes every run die at plugin resolution" (`scripts/nf_relay.py:23-33`) — plugins resolve through the relay like everything else. Where it is enabled is also a correction: `nf-prov` has nothing to do with *this site*, so it cannot live in `configs/sites/nchc.config` (that file is the resource-floor mapping only — `configs/sites/nchc.config:1-22` — and putting a plugin flag there would violate invariant 4, `PRINCIPLES.md`). It belongs in launch-time configuration instead. **Measured (§10, M1; PITFALLS 32):** it works through the Tower Agent and the relay with nothing pre-staged, writes a valid crate, and carries no checksum or file size. |
| R2 | Seqera labels, one per lab-record entry | **Measure before deciding** | `commands/launch.md` currently has no `tw launch` command line at all, and no labels. A label per record entry risks unbounded label growth on one workspace. **Unverified (§10, M2)**: label creation, any upper bound, and whether `tw runs list` can filter by label. If it cannot, the fallback is a run name carrying the record ID, or the record system storing the run URL instead. |
| R3 | A record-system adapter contract | **Adopted, contract and `none` only** | This document's sibling, `docs/RECORD_ADAPTER.md`, plus `scripts/record_adapter.sh`'s `none` implementation and `tests/command_layer_is_record_neutral.sh`. No real adapter is written — see `docs/RECORD_ADAPTER.md`'s own section on why, which is the same reasoning `docs/SITE_ADAPTER.md` already gives for not writing a second site adapter speculatively. |
| R4 | Compute an input checksum at launch time | **Adopted, changed to "prefer an existing value"** | This repo currently computes no input checksum anywhere (verified by absence — nothing in `scripts/` hashes an input file today). Sequencing files run tens of gigabytes, so hashing on the login node is expensive: prefer whatever checksum a lab's own intake process already recorded; only fall back to computing one through `scripts/on_site.sh` (with `ON_SITE_TIMEOUT=0`, since this is a genuinely long call) when nothing exists. The result is data about the input, not run state, so it is written into the project directory, not tracked as run state (`PRINCIPLES.md`, invariant 2). M1 showed `nf-prov` records no checksum (PITFALLS 32), so this stays: `scripts/input_checksums.sh`. |
| R5 | `finish` produces an `ro-crate-metadata.json` | **Adopted, depends on R1** | `scripts/build_package.sh` currently produces no such file (verified by absence). Every field in it must come from something already on disk, never invented (`PRINCIPLES.md`, invariant 9). |
| R6 | Shared-identity hosts get a read-only role, left as an open, text-enforced question | **Rewritten** | See §3: H2 can reach the cluster (with hooks enforcing what it may do); H3 is refused structurally, by never holding a credential that reaches the cluster, not by an instruction it could ignore. |
| R7 | Do not build an MCP server | **Adopted** | See §8 below — reaffirmed, with the one condition under which this project would reconsider. |
| R8 | A deployer-facing settings interface | **Adopted, with a real gap it closes** | `language` is documented in `CLAUDE.md` but is missing from `docs/SETTINGS.md`'s own key table (verified: `docs/SETTINGS.md`'s table, read in full for this document, has no `language` row). `ssh_max_parallel` and the record-adapter keys (§6, `docs/RECORD_ADAPTER.md`) are the new additions; `docs/SETTINGS.md` itself is edited in a later release by another track of this same round of changes. |
| R9 | A PI gets a workspace role suited to oversight, not execution | **Folded into M5** | Same measurement as H2/H3's token roles (§10). |
| R10 | The skill text should be portable, describing what is and is not possible when hooks are absent | **Adopted** | `skills/operational/SKILL.md`'s frontmatter today carries only `name` and `description`; a test enforces that its body states, per tier, what can and cannot be done without hooks — tying directly to §3 above. |

## 8. "Not an MCP server" — reaffirmed, with a reconsideration trigger

`PRINCIPLES.md`'s "Where each piece belongs" section already gives four
reasons this plugin is not, and does not wrap itself in, an MCP server:
Seqera already ships one; what remains here is five shell scripts on a host
that can already run shell; an MCP tool cannot carry procedure or judgement,
which is most of this plugin's value; and a script stays runnable by a
person or another model, which an MCP tool restricted to whoever has that
server attached does not (`PRINCIPLES.md`, "Where each piece belongs"). This
document adopts that reasoning outright (proposal R7) and does not relitigate
it.

The one condition worth naming, because §3 is new since that section was
written: **the H3 case is the only host this repo now describes that cannot
run a script at all** — it has no ssh, and by definition no hooks to invoke
one. Everything invariant 5 says in favour of a script over an MCP tool
("runnable by a person or another model") assumes a caller that can run
something; H3 cannot, structurally, by design (§3). If a lab's H3 host ever
needed more than the read-only Platform queries it already gets directly from
Seqera's own MCP server, a narrow MCP surface confined to that same read-only
scope would be the only mechanism left that could enforce it structurally the
way §3 already enforces everything else in this document. That is a
reconsideration trigger, not a plan: nothing in this release proposes
building it, and H3's current read-only access already goes through Seqera's
own MCP or Platform API directly, not through anything this repo would add.

## 9. What we will not do

Agreed outright (plan section A3: "提案 D 節...全部同意" — proposal section
D, adopted in full):

- **No sample-registration system.** That is the lab architecture draft's own
  "登記層" (`~/.claude/plans/lab-ai-agent-ai-agent-protocol-meeting-proud-pony.md`),
  a separate piece of infrastructure this plugin does not own or depend on.
- **No self-authored RO-Crate.** R1/R5 above use `nf-prov`'s own output
  instead of building a crate format from scratch — the same "build only what
  neither Seqera nor nf-core already does" invariant this repo already lives
  by (`PRINCIPLES.md`, invariant 1).
- **No agent-to-agent (A2A) protocol.** Nothing here defines a wire protocol
  for one agent to call another; every host in §2's table reaches this
  plugin the same way any Claude Code session does — by running its scripts
  or reading its docs.
- **No continuous run-state syncing.** This repo keeps no copy of a run's
  state in any file (`PRINCIPLES.md`, invariant 2, "no file in this repo
  records run state"). A lab agent that wants to know a run's status asks
  Platform, the same way this plugin's own commands do.

## 10. Unverified — the open measurements (M1–M6)

None of these are assumed true anywhere in this document; each is cited above
at the point it matters. Anything here is a claim this track could not check
from source alone (`PRINCIPLES.md`, invariant 8).

| # | What | How it would be measured | Needs a person present |
|---|---|---|---|
| M1 | nf-prov Workflow Run RO-Crate on this site | **Measured 2026-09-14** (PITFALLS 32): plugin downloads through the relay, `tw launch --config` reaches the head job through the Tower Agent, a valid crate is written to `<outdir>/pipeline_info/`; it records **no checksums or sizes**, and `agent`/`license` must be configured | Yes (done) |
| M2 | Do Seqera labels have a practical upper bound, and can `tw runs list` filter by them? | Create one test label on the workspace via `tw labels`, then delete it | No |
| M3 | Does the shared ssh master survive a closed terminal, and for how long does it survive idling? `docs/SITE_ADAPTER.md:135` ("dies with the terminal") and `scripts/on_site.sh:77-81` ("closing it does not take the connection down... One master lasts the whole work session") currently contradict each other | Open one master connection (needs a real OTP), then observe from outside | **Yes** |
| M4 | Do this plugin's hooks load under `claude -p` or the Agent SDK, and do G1–G3 and `ask` refuse there? | **Partly measured 2026-09-14:** `claude -p` with a blocking UserPromptSubmit hook (no model call) - the installed plugin's `plugin_intro.sh` ran and wrote its per-session marker, so plugin hooks load under `-p`. Still unmeasured: whether PreToolUse `deny`/`ask` refuse there (needs a real tool call), and the Agent SDK | No |
| M5 | Do Seqera workspace roles (View, Launch, and so on) behave as this design assumes — specifically, is a View-role token unable to launch? | `tw participants` and Seqera's own documentation; no actual launch attempted. Settling it means issuing one view-role token in Seqera's own UI and trying a launch with it — **no cluster OTP is involved**, which makes this the cheapest open measurement here, and §3 leans on it | Yes, to issue the token |
| M6 | Does NCHC permit automated access under a shared account, and a persistent process on a login node at all? | Only the user can ask NCHC this directly | **Yes** |

A measurement that does not hold does not get implemented around — the
correct response is to record why it failed and not build the feature it was
checking, the same standard `PRINCIPLES.md` invariant 8 already sets for
everything else in this repo.

---

## See also

- `docs/SITE_ADAPTER.md` — the sibling contract this document borrows `reach`
  and its whole shape from.
- `docs/RECORD_ADAPTER.md` — the contract this document's R3 review points at.
- `docs/CONDITIONS.md` — where §2's host dimension and §4's rule become a
  matrix a script can check, alongside every other dimension a deployment can
  vary along (written alongside this document, by a separate track of the
  same release).
- `hooks/confirm_walkthrough.sh`, `hooks/confirm_cleanup.sh`,
  `hooks/confirm_launch.sh` — cited throughout §5 for exactly what each one
  enforces today, and what is only prose today.
