# Conditions

What this plugin does and does not consider supported, and how a machine's
own place in that matrix gets measured rather than guessed.

`scripts/detect_conditions.sh` is the measurement. It looks only at the
machine it runs on and the deployment's own settings file
(`scripts/settings.sh`) - it never touches the network, and finishes well
under a second, so it is cheap enough to run before every session and before
every command opens (T1 in the "boundary procedure" this implements). It
prints one `key=value` per line:

```
os=linux|macos|msys|other
shell=<basename of $SHELL, or unknown>
interface=cli|vscode|desktop|web|unknown
reach=local|ssh|none|unset
jq=yes|no
hooks=yes|no|unknown
attended=yes|no|unknown
tier=H1|H2|H3
cell=<one of the codes below>
status=supported|blocked|unsupported
may_touch_site=yes|no
message=<one line>
```

`detect_conditions.sh --get <key>` prints just that value. Exit is always 0
except bad usage (an unknown flag, `--get` with no key or an unrecognised
one), which is 2.

`interface` is not a second implementation of interface detection: it is
`status.sh --interface`, the exact corroboration `status.sh`'s own
`claude_surface()` already does (`CLAUDE_CODE_ENTRYPOINT` alone is
unreliable - the same VS Code session has measured `claude-vscode` once and
`cli` later, because the value describes how the Bash subprocess was
started, not which surface the person is looking at; the editor's own
`TERM_PROGRAM`/`VSCODE_GIT_ASKPASS_MAIN` corroborate it). Both scripts share
one function in `scripts/status.sh` so the two answers can never drift apart.

## Evidence levels

Every dimension below is tagged with how sure the plugin actually is:

- **measured** - run and observed on a real instance of that thing.
- **read in code** - not run here, but the behaviour is read from the tool's
  own source or release artifacts (e.g. which `tw` binaries a release ships).
- **inferred** - a reasonable guess from a naming convention or a single
  partial observation, not directly measured. The `interface` dimension as a
  whole is inferred beyond its two measured values (`cli`, and VS Code via
  corroboration): `claude-desktop`/`claude-web` follow the one naming
  pattern actually observed (`claude-<surface>`) and have never been seen on
  a real desktop or web session.

## Decision cells

`detect_conditions.sh` evaluates its inputs in a **fixed priority**, so
exactly one cell wins every time (blocked beats unsupported beats
supported):

| Order | Condition | `cell` | `status` | Message (fixed) |
|---|---|---|---|---|
| 1 | `jq` missing or cannot run | `blocked-no-jq` | blocked | `jq is required here and was not found. Install it: macOS \`brew install jq\`; Debian/Ubuntu or WSL \`sudo apt install jq\`.` |
| 2 | `os=msys` and `reach=ssh` | `blocked-msys-ssh` | blocked | `Git Bash/MSYS cannot hold the shared ssh connection this site needs (PITFALLS 16b). Start Claude Code from a WSL shell instead.` |
| 3 | `tier=H3` and `reach` is `ssh` or `local` | `blocked-h3-site` | blocked | `no plugin hooks: Platform read-only only, see docs/LAB_AGENTS.md` |
| 4 | `reach=none` | `unsupported-cloud-ce` | unsupported | `Seqera-managed cloud compute environment is recognised but not supported by this version. Run scripts/report.sh to let the maintainer know.` |
| 5 | otherwise | `supported` | supported | `This host and configuration are supported.` |

Every cell whose `status` is unsupported (today, only `unsupported-cloud-ce`) has a message that names how to report it
(`scripts/report.sh`), per the plugin-wide rule that nothing outside its
design silently proceeds without a trace.

`tests/conditions_matrix_test.sh` asserts, in both directions, that this set
of `cell` codes is exactly the set `detect_conditions.sh` can print - it
would fail if this table listed one the script cannot reach, or if the
script grew a branch this table does not document.

### `may_touch_site`

Independent of which cell won above, and with exactly two triggers (plan
section A2's structural rule: **no hooks means no cluster, full stop**):

- `no` when `tier=H3` (no plugin hooks - Claude Tag, Managed Agents,
  OpenClaw, Hermes, Codex and similar share-identity runtimes with no way to
  gate a launch or a delete).
- `no` when `os=msys` and `reach=ssh` (Git Bash cannot hold the shared ssh
  connection this site needs, PITFALLS 16b - a Windows desktop app or Git
  Bash terminal reaching for the cluster the same way).
- `yes` otherwise. Notably **not** triggered by `jq` being missing: that
  blocks the whole session (PITFALLS 28's safety nets fail closed without
  it), which is a different and broader question than whether this *host* is
  structurally allowed near the site at all.

An H3 host with no settings file at all (`reach=unset`) lands on the
`supported` cell - nothing else about it is wrong - but `may_touch_site`
still reads `no`, because the tier alone decides that field.

## The matrix

The plan's own condition matrix (section 二 "條件矩陣"), with a **Lab agent
host** dimension and the **H1-H3 tiers** (plan section A2) added. Each row
names a status, its evidence level, and - where `detect_conditions.sh` can
actually classify it - which decision cell it maps to. Several dimensions
(which IDE, which pipeline request, where the data lives) are not things
`detect_conditions.sh` measures at all; those rows carry no cell code.

### Where Claude itself runs

| Host | Status | Evidence | Cell |
|---|---|---|---|
| NCHC login node | ✅ supported | measured | `supported` |
| macOS | ✅ supported | measured only in a simulated BSD userland | `supported` |
| Windows + WSL | ✅ supported | measured by a second lab member | `supported` |
| Windows, Git Bash/PowerShell reaching the cluster | ⛔ blocked | measured, blocked since v2.6 | `blocked-msys-ssh` |
| Linux desktop | ✅ supported | inferred | `supported` |

### Claude interface

| Interface | Status | Evidence | Cell |
|---|---|---|---|
| CLI | ✅ supported | measured | — |
| VS Code (extension) | ✅ supported | measured | — |
| VS Code Remote-SSH to the login node | ✅ supported | measured (this is that session) | — |
| Windows desktop app, reaching the cluster | ⛔ blocked | inferred - its Bash tool is believed to run through Git Bash, not yet measured | `blocked-msys-ssh` (once measured) |
| claude.ai/code web, cloud sandboxes | 🚧 unsupported | inferred - cannot take a 2FA code, and is not the lab's own machine | `unsupported-cloud-ce` when `reach=none`, otherwise not reachable by this script |

`interface` itself is read as **inferred** evidence as a whole (see
"Evidence levels" above): only `cli` and VS Code are actually measured
values.

### Compute environment

| Environment | Status | Evidence | Cell |
|---|---|---|---|
| NCHC Taiwania-3 | ✅ supported | measured | `supported` |
| Seqera-managed cloud compute environment | 🚧 unsupported (downgraded from "supported" - see below) | read in code | `unsupported-cloud-ce` |
| Another institution's HPC | 🚧 unsupported | read in code (no second site adapter exists, `docs/SITE_ADAPTER.md`) | `unsupported-cloud-ce` when `reach=none`, otherwise not reachable by this script |
| A member's own VM or workstation | 🚧 unsupported | read in code | as above |

**`reach: none` downgrade.** Earlier documentation described `reach: none`
as supported; it has never actually been exercised end to end. This version
recognises it, explains that it is not supported yet, and points at
`scripts/report.sh` - it does not pretend to work. The already-written
refusal paths and their tests are correct and unchanged; only the
documentation and `setup`'s own claims changed, from "supported" to
"recognised, not supported this version, reported".

### Downstream analysis IDE

| IDE | Status | Evidence | Cell |
|---|---|---|---|
| Positron | ✅ supported | measured | — |
| RStudio, VS Code, Jupyter | 🚧 unsupported | read in code (`downstream.md` step 5 is a dead end for these today) | — (not something `detect_conditions.sh` measures; caught by the off-design procedure at the point of use) |

### Accounts

| Account | Status | Evidence | Cell |
|---|---|---|---|
| NCHC account | required; missing → ⛔ blocked | measured | — |
| Seqera account + workspace | required; `setup` already handles this | measured | — |
| GitHub account + `gh` | optional; missing → report stays local, reminded at session start | measured | — |

### Tools on the machine Claude runs on

| Tool | Status | Evidence | Cell |
|---|---|---|---|
| `jq` | required; missing → ⛔ blocked | measured | `blocked-no-jq` |
| `ssh` with ControlMaster support (`reach: ssh`) | required for that reach | measured | (folds into `blocked-msys-ssh` when the shell cannot hold it) |
| `quarto` (used by `finish`) | required for that command | read in code | — |
| Positron (used by `downstream`) | optional, has its own "not here" branch | measured | — |

### Who is using it

| Identity | Status | Evidence | Cell |
|---|---|---|---|
| Maintainer (`gh api user` → `zhshie`) | design-it-in mode, not a report | measured | — |
| First member on this cluster | ✅ supported | measured | — |
| A later member, cluster already set up | ✅ supported (`setup`'s third case) | measured | — |
| The same person, a second machine | ✅ supported | measured | — |

### Request type

| Request | Status | Evidence | Cell |
|---|---|---|---|
| An official nf-core release | ✅ supported | measured | — |
| An nf-core dev branch | ⛔ blocked | read in code (revisions must be pinned) | — |
| A non-nf-core Nextflow pipeline | 🚧 unsupported | read in code | — |
| Snakemake or another workflow system | 🚧 unsupported | read in code | — |
| GPU-requiring pipelines | 🚧 unsupported | read in code (`launch.md` already flags this as unverified) | — |

### Where the data is

| Location | Status | Evidence | Cell |
|---|---|---|---|
| Already on the cluster | ✅ supported | measured | — |
| On the laptop → `push.sh` | ✅ supported | measured | — |
| Public SRA/GEO → fetchngs | ✅ supported | measured | — |
| A cloud bucket (`s3://` etc.) | 🚧 unsupported | read in code | — |

### Lab agent host (plan section A)

Who or what is driving this plugin, mapped onto A2's H1-H3 tiers:

| Host | Tier | Status | Evidence | Cell |
|---|---|---|---|---|
| A person, interactively, in Claude Code | H1 | ✅ full access | measured | `supported` |
| Headless Claude Code / Agent SDK with this plugin loaded, unattended, on the lab's always-on Linux box or the login node | H2 | ✅ read-only cluster ops + preparing (not submitting or deleting) runs | plan-level design, hooks reused as-is; whether hooks actually load under `claude -p`/the Agent SDK is unmeasured (plan's M4) | `supported`, `may_touch_site=yes`, but structurally still gated by G1-G3 (unattended never answers a confirmation) |
| Claude Tag, Managed Agents, OpenClaw, Hermes, Codex or similar - shared identity, no plugin hooks | H3 | ⛔ Platform read-only only; never touches the cluster | structural - no ssh, no launch-capable token, regardless of what it asks for | `blocked-h3-site` when it has `reach` at all; `may_touch_site=no` always |

H2/H3 are not distinguished by *product name* - only by two measurable
facts: does this runtime load the plugin's hooks, and can it reach the
shared ssh connection at all. A runtime that cannot say whether it has hooks
must say so explicitly (`AGENTIC_BIOFLOW_HOST_HOOKS=no`); left unset outside
Claude Code, `hooks` reads `unknown` and `tier` defaults to `H1` rather than
guessing H3, because this script only ever reports what it measured - the
actual enforcement for H2/H3 is a Seqera token scoped without launch rights
(plan A2), never this script's own say-so.
