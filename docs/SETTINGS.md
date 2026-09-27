# The settings file

One root, outside the repository, holding everything that identifies a person
or their site. The user chooses where it is; nothing in this repo has an
opinion beyond "somewhere that follows you between machines".

```
<root>/
├── config/
│   ├── env.yaml                  the settings - travels with the root
│   ├── .seqera_token             the token, mode 600
│   └── machines/<machine>.yaml   the few keys that cannot travel
└── projects/<project>/
    ├── rawdata/      staging; scripts/push.sh sends this up
    ├── runs/<run>/results/   brought back by scripts/fetch.sh, read-only
    ├── analysis/     analysis.md, R/Python, figures; what an IDE opens
    └── submission/   the built package
```

**There used to be seven places these files could be**, and the reason was
accretion rather than design: `$LAB_RUNS_DIR/_personal` came first, when the
only deployment ran on the site; the XDG location was added for `reach: ssh`;
and a portable folder was added on top of both rather than replacing either,
with a pointer file of its own. A person who wanted to know where their own
settings were had to be told which of the three applied to them, and the
honest answer depended on which shell they asked from.

T30 replaced all of it with the root above. Two properties follow, and they
are the whole point:

- **The user knows one location.** Not one per `reach`, not one per machine.
- **Setup happens once per person, not once per machine.** A second machine
  runs `scripts/settings.sh --use <root>` and is done - no questions, no
  second onboarding.

## How a machine finds the root

`scripts/settings.sh` resolves it in two steps, most explicit first:

1. `$LAB_SETTINGS_FILE`, if set. It names exactly one file and nothing else is
   searched: a location that could quietly resolve elsewhere would let a read
   and a write land in two different files. This exists for test fixtures and
   one-off calls, not for deployments.
2. The pointer file, `${XDG_CONFIG_HOME:-~/.config}/agentic-bioflow/root` -
   one line, the root's absolute path. `settings.sh --use <root>` writes it.

**One breadcrumb cannot be avoided**, and it is worth being honest about that
rather than claiming "one location" and quietly keeping two: a machine has to
learn where the root is before it can read anything in it. The pointer is that,
and it is never something a user has to know about - written automatically,
one line, and re-created by one command if it is ever lost.

**It is a file, not an environment variable, deliberately.** Every way the
settings file has gone missing between one session and the next was caused by
a variable being **set**, never by the absence of one:

- **A variable exported in one shell's startup file and not another's.** Git
  Bash and WSL on one Windows machine have separate homes and separate startup
  files (PITFALLS 25). `zsh`, the default shell on macOS, does not read
  `~/.bashrc` at all.
- **`LAB_SETTINGS_FILE` pinned to a path that has since moved.** It wins
  outright and searches nowhere else, so the real file can be sitting at the
  root untouched while the report names one absent path. `settings.sh` says so
  when that happens, because it is the one form of this a person can fix in
  one command.
- **A file written under `$LAB_RUNS_DIR/_personal/` on the user's own
  machine.** Measured: the old `set_setting` followed that variable, `mkdir -p`
  made the site-shaped directory locally without complaint, and the next shell
  without the variable could not find what had just been written. T30 removed
  the code path entirely - `LAB_RUNS_DIR` no longer takes part in finding
  settings at all, on any platform, under any `reach`.

`$HOME` is the one thing every shell on every platform agrees about, which is
why the pointer lives there and needs no variable to be found.

## `reach` does not change any of this

| deployment | settings live | variables needed |
|---|---|---|
| `reach: local` (Claude on the site) | `<root>/config/env.yaml` | none |
| `reach: ssh` (Claude on the user's machine) | `<root>/config/env.yaml` | none |
| `reach: none` | `<root>/config/env.yaml` | none |

Under `reach: ssh` the root is on the user's own machine and the site never
needs a copy: the values its scripts want cross as environment variables on
the one round trip that carries them (`scripts/on_site.sh`). Under
`reach: local` the root is a directory on the site that the user picked. Same
mechanism either way, which is why there is no longer a table row explaining
which case someone is in.

`storage_root` is the one thing that stays on the site regardless - it is
where runs actually execute, and compute nodes have to be able to read it.
That is the only other location this deployment has, and it is not a place
anybody keeps settings.

## The keys that cannot travel

`tw_bin`, `site_bridge` and `ssh_control_path` describe *this machine*, so
they live in `<root>/config/machines/<machine>.yaml` instead of
`config/env.yaml`. Two machines sharing one root each get their own file;
neither can clobber the other's `tw`.

The machine id is `<hostname>-<uname -s>`, sanitised for use as a filename.
Hostname alone is not enough: Git Bash and WSL on one Windows box are two
environments with separate homes, separate PATHs and a different `tw`
(PITFALLS 25), and they report the same hostname.

**Every key in that file is discovered, never asked for** - `tw_bin` by
`scripts/install_deps.sh`, `site_bridge` by probing for `wsl.exe`,
`ssh_control_path` from its own default. So the machines/ directory is not
something a user has to know exists, and nothing is lost if it is deleted.

`agent_java` and `agent_jar` are deliberately **not** on that list: under both
`reach: local` and `reach: ssh` they are paths on the **site**, identical no
matter which machine is asking. Treating them as machine-local was the old
layout's mistake - it made a second machine re-run `install_deps.sh` to
rediscover values that had not changed.

`scripts/settings.sh` reads and writes all of this. It is not a YAML parser -
it reads `key: value` and stops at the first `#`, which is all these files are
allowed to be. A settings file that needs a real parser has grown into
something else.

| Key | What it is | Without it |
|---|---|---|
| `reach` | How the site is reached: `none`, `local` or `ssh`. See SITE_ADAPTER contract 6. `none` is recognised, not supported in this version — `setup` reports it and stops rather than onboarding a cloud site | Defaults to `local`, which is right only when this deployment runs on the site |
| `language` | Which language `scripts/intro.sh` writes in: `zh-TW` or `en`. Read as `scripts/settings.sh language`, not by any script parsing the settings file itself — `scripts/intro.sh` asks for exactly this one key and falls back silently the same way an unset key always does | Defaults to `zh-TW`. An unrecognised value falls back to `zh-TW` the same way — never a hard failure over a typo in this key |
| `site_host` | `user@host` to log in to. **`reach: ssh` only** | Nothing can reach the site; preflight fails naming this key |
| `site_user` | The site account the work runs under — the user half of `site_host`, said plainly, so a summary can name it. `scripts/preflight.sh` FAILs when the two disagree, because one value written twice drifts silently | Nothing breaks; the summary cannot say whose account this is |
| `seqera_user` | This member's Seqera username — the Username column of `tw runs list`. Where a lab reaches the site through **one shared account**, this is the only thing that tells two members apart; `$USER` is the same for everybody | A run cannot be attributed to the person who launched it |
| `site_bridge` | **Machine file.** On MSYS only: `wsl` or `none` — whether `scripts/on_site.sh` (and `fetch.sh`/`push.sh`) route ssh through `scripts/utils/wsl_ssh.sh`, i.e. `wsl.exe -e ssh` (PITFALLS 16b/16g). Auto-detected (`wsl` if `wsl.exe -e true` succeeds, else `none`) unless set explicitly. Read on every other platform too, but always `none` there — WSL is a Windows-only concept | Nothing breaks on Linux/macOS. On MSYS with no usable `wsl.exe`, `on_site.sh` refuses (`wrong_shell`) rather than trying Git Bash's own ssh, which cannot multiplex at all |
| `ssh_control_path` | **Machine file.** Where the multiplexed master's socket lives. **`reach: ssh` only** | Defaults to `~/.ssh/cm-%r-%h-%p`. It must not contain `:` — illegal in a Windows filename. Under the WSL bridge (`site_bridge: wsl`) the default is left as that literal `~/...` string, unexpanded, because the master lives inside WSL and only WSL's own shell can resolve the `~` against the right home — an MSYS-expanded `$HOME/.ssh/...` would name a path on the Windows side that nothing there is listening on |
| `ssh_max_parallel` | How many concurrent sessions `scripts/on_site.sh` opens on one shared master at once, via a lock directory (`mkdir`, not `flock` — not portable to a Mac). **`reach: ssh` only**; this site caps concurrent sessions per connection too (PITFALLS 16e), and several callers sharing one master reach that cap faster than one ever did — see `docs/LAB_AGENTS.md` §6 | Defaults to 4. A caller that cannot get a slot waits until `ON_SITE_TIMEOUT` |
| `storage_root` | Where runs live **on the site**. Exported as `LAB_RUNS_DIR` for the site's own scripts; since T30 it takes no part in finding the settings file | Nothing runs; scripts refuse to guess |
| ~~`local_root`~~ | **Removed in T30.** The root *is* the local side, and this machine's copy of that answer is the pointer file, not a key. It used to default to `$HOME/agentic-bioflow` - a path that cannot travel, chosen silently for somebody who was never asked. `settings.sh --migrate` reports it and drops it | n/a |
| `workspace_id` | The Seqera workspace. **The one value a lab shares** — everything else below is per person | Cannot reach Platform |
| `compute_env` | This member's compute environment name | Cannot launch |
| `slurm_account` | The allocation compute time is billed to | Jobs are refused. There is deliberately **no default**: one would bill somebody else's project |
| `agent_connection` | Identifier for this member's outputs reader. **Must be unique** — never another member's or a shared lab credential's. Changing an existing value makes `hooks/confirm_launch.sh` ask the user first | Two members sharing one are refused permanently |
| `agent_java` | A Java 21 runtime | The reader will not start |
| `agent_jar` | Seqera's agent | The reader will not start |
| `tw_bin` | Seqera's CLI, if not on `PATH`. **Machine file** | Falls back to `PATH` |
| `singularity_cache` | Where container images are kept | Falls back to one under the run area, and images are pulled again |
| `relay_port` | Pins the outbound channel's port | One is chosen and remembered; pin it only if you must |
| `email` | Where run notifications go | No notification once the conversation ends |
| `record_adapter` | Which record adapter is in use — `none`, or a future adapter's name. `docs/RECORD_ADAPTER.md` is the contract; only `none` is implemented in this version | Defaults to `none` — every deployment is valid with nothing set |
| `record_ref` | The convention this deployment uses for a reference passed to the record adapter's `resolve`/`attach` — a sample ID, an experiment ID, opaque to the command layer and meaningful only to whichever adapter is configured | Nothing breaks; there is simply nothing to resolve against, which is `none`'s normal case |

## What a lab agent's persona layer may set

`language`, `ssh_max_parallel` and `record_adapter`/`record_ref` are settings
like every other row above — read the same way, by the same script, subject
to the same "ask the user, never guess, never copy from another member" rule.
They are listed separately here only because they are the ones a lab's own
persona layer is most likely to reach for.

**Persona, tone and lab-specific norms come only from the deployer's own
CLAUDE.md — never from this repo.** `skills/operational/SKILL.md` says this
outright in its own opening line: it defines *how the work is done*, not who
is doing it or in what voice. This repo has no mechanism for a lab identity
beyond the settings keys in the table above; anything else a lab wants to
customise — the language notifications are written in, greeting text, which
languages are supported at all beyond `zh-TW`/`en` — is a CLAUDE.md concern,
layered on top of this plugin, never a fork of it.

`scripts/install_deps.sh` fills in `agent_java`, `agent_jar` and `tw_bin`;
`scripts/egress_ctl.sh` remembers the port it chose. The rest come from the
user, and **must be asked for rather than guessed** — an allocation code or a
workspace copied from someone else fails in ways that look like a bug.

## The shape under `storage_root`

`storage_root` used to mean "put things somewhere in here" and nothing more
specific than that. In practice that meant probe directories from setup
rehearsals sitting beside real analyses with no boundary between them, and a
second run area elsewhere shaped differently again - `rawdata/`, `results/`
and a work directory all at the top level, instead of per member. Nobody had
designed the shape; it had accreted.

`scripts/init_workspace.sh` is the shape, made concrete. It builds two
distinct sides - never both from one call, because they are two different
machines - and never touches anything already inside a directory it creates,
so running it again is always safe:

```
$LAB_RUNS_DIR/                     (site side, "site")
├── _personal/            env.yaml and the token, mode 600, per person
├── _references/          shared reference data
├── _singularity_cache/   shared container images
├── _system/               where this deployment's own machinery keeps its
│   ├── agent/              state - agent/relay/coldstart, so a probe from a
│   ├── relay/               setup rehearsal has somewhere to go that is not
│   └── coldstart/           the top level
└── <seqera_user>/         one member's workspace - the site is one shared
    └── projects/           Unix account, so the Seqera username is what
        └── <project>/       tells members apart, not $USER
            ├── rawdata/    what the compute nodes read
            └── runs/
                └── <pipeline>_<label>_<YYYYMMDD>/
                    ├── logs/
                    ├── results/  --outdir points here
                    └── work/     the only deletable one, on confirmation

<root>/                            (local side, "local" - the user's own root)
├── config/                        settings, token, this machine's own keys
└── projects/<same name as the site>/   (no <seqera_user> layer here: the
    ├── rawdata/      staging; scripts/push.sh sends this up    root belongs
    ├── runs/<same name as the site>/                           to one person
    │   └── results/  brought back by scripts/fetch.sh, read-only  already)
    ├── analysis/     analysis.md, R/Python, figures; what an IDE opens
    └── submission/   the built package

    T30: all four are siblings. analysis/ and submission/ used to be
    redirected into a separate portable folder while rawdata/ and runs/
    stayed behind in another root - two roots that had to be kept in step by
    hand, and the source of the "which half am I looking at" question this
    release exists to end.

    A project already living at the OLD shape (<root>/<seqera_user>/
    projects/<project>/...) keeps living there - detected per project, by
    whether that path already exists ("Migration", below). Only a brand new
    project, on a machine with no old directory for it yet, gets the shape
    above. scripts/where.sh --project-paths <project> resolves this in one
    place; scripts/init_workspace.sh and every command file ask it rather
    than constructing a path by hand (T29).
```

**The project is the unit everything is collected under**: the raw data that
feeds it, every run made from that data, the analysis written on those runs,
and the package built from the analysis. Runs used to sit directly under a
member and analysis directly under a run, which made two ordinary things
awkward - one batch of reads feeding several runs, and one write-up drawing on
several runs.

Project and run directories share their names across the two sides, so the
halves line up by eye. `results/` is a re-fetchable read-only copy rather than
a second source of truth. `rawdata/` appears on both sides and is not a second
home either: the site's is what the compute nodes read, the local one is the
staging area `push.sh` sends from. `analysis/` exists **only locally** -
interactive editing happens where the IDE is. This project has been bitten
twice by two copies of one truth being allowed to disagree; do not reintroduce
a third.

**`submission/` is a sibling of `analysis/`, not a child.** Deleting or moving
anything under `analysis/` is a hard deny in `hooks/confirm_cleanup.sh`, and a
built package has to be throwable-away and rebuildable. `analysis/` is source;
`submission/` is what was built from it.

**The directory names are not this design's to choose freely.** Each one has
to satisfy two readers, and satisfying only one is the failure in PITFALLS 17:

| reader | file | what it wants |
|---|---|---|
| the net that refuses to delete it | `hooks/confirm_cleanup.sh` | the name matches its pattern |
| the thing that writes into it | `configs/sites/nchc.config` | the name is where it puts files |

The image cache was called `lab_singularity_library` here for a while, because
that was the hook's only literal pattern and a name it did not know would have
been an unguarded directory. PITFALLS 17 fixed the hook to match the shape
instead — `lab_singularity_library`, `_singularity_cache`, `.singularity_cache`
and a bare `singularity` all qualify — which retired that constraint without
retiring the name it had forced. The skeleton kept building a directory that
was guarded, agreed with every comment about it, and that nothing would ever
put an image into: `nchc.config` writes to `_singularity_cache`. It is now
spelled the way the config spells it, and `tests/init_workspace_test.sh` reads
that spelling out of the config rather than trusting this page.

**Migration: none.** Existing runs stay exactly where they are;
`scripts/init_workspace.sh` never moves, renames or deletes anything. The
skeleton applies going forward, to what gets created from here on - not
retroactively to what already exists.

Setup asks two questions that decide what gets built (`commands/setup.md`,
"Two more questions, before step 1"): where the source data already is
(input is not really a choice - it has to end up on the site, because compute
nodes are what read it, so `scripts/push.sh` moves it there when it starts on
someone's own computer) and where downstream analysis should happen (a real
choice; local is the default, and is small - a normalised count matrix is
about 973 KB, a whole delivery directory about 25 MB - so "the site, because
it might be large" is rarely the right call).

## Keys this version does not read

`nextflow_path`, `hpc_profile`, `driver_queue`. They belong to v1, which is
still installable as a fallback and does read them. Leave them where they are:
deleting them costs the rollback path and saves three lines.

## A second machine

One command:

```
scripts/settings.sh --use <root>
```

That is the whole of it. `--use` points this machine at the root, creating the
root if it is not there yet - the folder's existence answers "is this a first
machine or a second one", so the user never has to. Nothing is typed in twice,
and nothing is copied by hand.

If the root is on a synced folder that has not finished syncing to this
machine yet, `--use` says so rather than creating an empty one beside it, and
every later error distinguishes "pointed at a root that is not here yet" from
"never pointed at a root" - the first is "wait", the second is "run setup".

## The token

`<root>/config/.seqera_token`, plaintext, mode 600.

**The root is expected to be a synced folder, so the sync client holds a copy
of the token.** That is a real exposure and this file will not pretend
otherwise. It was weighed against keeping the token encrypted with a
passphrase, which is what T23 did: that bought secrecy at the cost of a
second, machine-local location for the decrypted copy, and a password typed on
every new machine - which is exactly the "setup once" property this layout
exists to deliver. A Seqera personal access token is revocable from the
Platform UI in one click, which is what makes this the cheaper side of the
trade.

Two consequences worth stating rather than discovering:

- **On Windows, mode 600 is advisory.** The ACL is what decides, and
  `scripts/settings.sh` asks Windows directly rather than trusting the bits
  Git Bash prints (PITFALLS: the Windows privacy check).
- **A root shared with anyone else shares the token.** The root belongs to one
  person. Two members get two roots; they share `workspace_id` and the
  allocation, and nothing else.

`scripts/init_workspace.sh` and `settings.sh --use` warn when the root looks
like a synced folder - they never refuse, because refusing would refuse the
design. The warning says the two things above and adds that large files
(rawdata, results, container images) do not belong there: they live on the
site, and the root holds only what an IDE opens.

## Migration

T30 cut over rather than carrying two layouts indefinitely. The pre-T30
locations - `$LAB_RUNS_DIR/_personal/env.yaml` and
`${XDG_CONFIG_HOME:-~/.config}/agentic-bioflow/env.yaml` - are **not read**.

They are still *looked at*, but only so that somebody who already ran setup is
told the one command they need instead of "run setup again":

```
scripts/settings.sh --migrate <root>
```

It creates the root, copies every key across (splitting the machine keys into
`config/machines/<machine>.yaml`), copies the token, and points this machine
at the result. `local_root` is reported and dropped - the root supersedes it.

**It copies; it never moves.** The old files are left exactly where they were,
and the command says where they are. A migration that deletes the only copy of
somebody's credentials before the new location has been proven is not a
migration. Run `scripts/preflight.sh`, and delete them only after it passes.

**Projects keep their shape.** A project directory already at the old
`<root>/<seqera_user>/projects/<project>/` layout keeps living there, detected
per project rather than by a machine-wide switch. Only a brand new project
gets the current shape.


## The "setup once is enough" contract (T27)

Every key in the table near the top of this file belongs to exactly one of
two layers, and which layer decides what has to happen on a new machine:

| Layer | Keys | Where it lives | On a new machine |
|---|---|---|---|
| **Travels** | everything not in the row below - `reach`, `seqera_user`, `workspace_id`, `compute_env`, `slurm_account`, `site_host`, `site_user`, `storage_root`, `email`, `language`, `record_adapter`, `record_ref`, `agent_connection`, `agent_java`, `agent_jar`, `singularity_cache`, `relay_port` | `<root>/config/env.yaml` | Comes with the root. Typed in exactly once, ever |
| **This machine** | `tw_bin`, `site_bridge`, `ssh_control_path` | `<root>/config/machines/<machine>.yaml`, inside the same root | Discovered automatically - never copied, never asked for |

**"Re-derived automatically" is not a manual step someone has to remember.**
Each one already has a script whose job is finding it out fresh on whatever
machine it runs on, and every one of them already runs as an ordinary part of
`setup`/`preflight` regardless of whether a portable folder is involved:

- `site_bridge` — `bridge_kind()` (`scripts/settings.sh`) probes `wsl.exe` on
  this machine at read time; nothing to set.
- `ssh_control_path` — `site_control_path_default()` computes it from
  `site_bridge`, same call.
- `tw_bin` — `scripts/install_deps.sh --cli-only` on this machine (setup
  step 4's `reach: ssh` branch) installs Seqera's CLI here and records where.

`agent_java` and `agent_jar` moved **out** of this row in T30. They name paths
on the **site**, identical from every machine, so treating them as
machine-local made a second machine re-run `install_deps.sh` to rediscover
values that had not changed. They travel with the root now.

`local_root` is gone entirely - see its row in the key table.

**Verify-only, before anything else.** `setup` runs `scripts/setup_verify.sh`
as its very first act (before deciding repair vs first-run vs adopt):
settings complete and `preflight.sh` green → report that in seconds and stop,
never walking a working machine through checks it does not need. Anything
else → continue into whichever of repair/first-run/adopt actually applies.

### New machine: the three steps that cannot be skipped

Everything above is what the root removes. What is left is real, and this
says so plainly rather than implying the root makes setup disappear entirely -
three things are per-machine no matter what, because none of them is a *value*
that could travel in a settings file at all:

1. **Local tools.** `jq`, `curl`, Seqera's CLI, WSL on Windows (PITFALLS
   16b/16f) - whatever is missing from *this* machine's own PATH. A settings
   key cannot install a binary.
2. **The first connection to the site.** The site accepts no saved
   credential, only a one-time code typed by a human once per session
   (PITFALLS 16h). No root, key, or token can stand in for this - it is the
   one step that is genuinely, deliberately unautomatable.
3. **Positron's bridge**, if this member uses it for downstream analysis - a
   separate install on this machine, unrelated to anything in a settings file
   (a different branch's own card; not built here).

Three steps, not ten: this is the entire gap between `--use <root>` and
"fully working", and nothing above pretends otherwise.

### Open question: `agent_connection` across two machines at once

**Not measured, and this file says so rather than guessing.** The outputs
reader (`scripts/agent_ctl.sh`) runs on the site and is identified by
`agent_connection`, which travels with the root (table above) - so pointing a
second machine at the same root gives both machines the same value by
design. What happens if that member has **both machines open at once**, each
independently calling `scripts/on_site.sh --script scripts/agent_ctl.sh` -
whether the second `start`/`register` bumps the first's session, whether
Platform simply serves both, or whether something fails in a way that reads
like a different bug entirely - has never been tried. Until it is measured
(PRINCIPLES.md invariant 8), treat two machines sharing one `agent_connection`
as **untested**, not as "known to work" or "known to fail" - and if it comes
up, that is the moment to measure it and turn this paragraph into a fact.

T30 makes this more likely to come up, not less: one root on a synced folder
is precisely the arrangement that puts two machines on one `agent_connection`.
Nothing here has changed that it is unmeasured.
