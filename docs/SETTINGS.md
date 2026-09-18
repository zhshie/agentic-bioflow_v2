# The settings file

One file, outside the repository, holding everything that identifies a person
or their site. Mode 600. Nothing in it may be copied from another member,
printed into a conversation, or committed.

**Where it lives is where the deployment runs, not where the site is.**
`scripts/settings.sh` looks in three places, most explicit first:

1. `$LAB_SETTINGS_FILE`, if set. It wins outright and nothing else is searched:
   a location that could quietly resolve elsewhere would let a read and a write
   land in two different files.
2. `$LAB_RUNS_DIR/_personal/env.yaml` — where it is on a login node.
3. `${XDG_CONFIG_HOME:-~/.config}/agentic-bioflow/env.yaml` — the conventional
   place, and the one a user can find without being told.

The third is there because the chain used to stop at the second: with neither
variable set it produced the string `/_personal/env.yaml`, which is unreadable
but not empty, so every read returned its default and a configured machine was
indistinguishable from one that had never run setup. When none of the three
holds a file, the error names all of them rather than one.

**Which of the three is yours is decided by where the deployment runs, and for
a user's own machine the answer is the third — with no variable set at all.**

| deployment | the file goes | variables needed |
|---|---|---|
| `reach: local` (Claude on the site) | `$LAB_RUNS_DIR/_personal/env.yaml` | `LAB_RUNS_DIR`, which that account needs anyway |
| `reach: ssh` or `none` (Claude on the user's machine) | `${XDG_CONFIG_HOME:-~/.config}/agentic-bioflow/env.yaml` | **none** |

`none` is listed here because `settings.sh` resolves the file the same way for
it as for `ssh` — that logic is correct and tested. It is not a claim that a
`reach: none` deployment is supported end to end: this version recognises the
value but has no onboarding path built for it (`docs/SITE_ADAPTER.md`,
contract 6; `commands/setup.md`).

That second row is not a style preference. Every way this file has gone missing
between one session and the next is caused by a variable being **set**, never by
the absence of one:

- **A variable exported in one shell's startup file and not another's.** Git
  Bash and WSL on one Windows machine have separate homes and separate startup
  files (PITFALLS 25). `zsh`, the default shell on macOS, does not read
  `~/.bashrc` at all.
- **`LAB_SETTINGS_FILE` pinned to a path that has since moved.** It wins
  outright and searches nowhere else, so the real file can be sitting at the
  default untouched while the report names one absent path. `settings.sh` now
  says so when that happens, because it is the one form of this a person can
  fix in one command.
- **The file written under `$LAB_RUNS_DIR/_personal/` on the user's own
  machine.** Measured: `settings.sh --set` follows that variable, `mkdir -p`
  makes the site-shaped directory locally without complaint, and the next shell
  without the variable cannot find what was just written.

The third place needs none of them, because `$HOME` is the one thing every
shell on every platform agrees about. **So on a user's machine, set nothing.**
`settings.sh --set` already writes there when no variable steers it, and
`settings.sh` finds it again in any shell, on any of the three platforms.

Reaching the site over ssh, the file is on the user's own machine, together with
the token beside it — `token_file` in `scripts/settings.sh` derives the token's
path from this file's, so the pair travel together, and `preflight.sh`,
`agent_ctl.sh`, `ce_apply.sh` and the session hook all ask it rather than each
working it out again. The site never needs a copy: the values its scripts want
cross as environment variables on the one round trip that carries them
(`scripts/on_site.sh`).

**`scripts/settings.sh --summary` says which of the three is in use**, and what
this deployment is configured as. It reports the token only as
`present (mode 600)` — its value is never printed, by this or anything else.

`scripts/settings.sh` reads and writes it. It is not a YAML parser — it reads
`key: value` and stops at the first `#`, which is all this file is allowed to
be. A settings file that needs a real parser has grown into something else.

| Key | What it is | Without it |
|---|---|---|
| `reach` | How the site is reached: `none`, `local` or `ssh`. See SITE_ADAPTER contract 6. `none` is recognised, not supported in this version — `setup` reports it and stops rather than onboarding a cloud site | Defaults to `local`, which is right only when this deployment runs on the site |
| `language` | Which language `scripts/intro.sh` writes in: `zh-TW` or `en`. Read as `scripts/settings.sh language`, not by any script parsing the settings file itself — `scripts/intro.sh` asks for exactly this one key and falls back silently the same way an unset key always does | Defaults to `zh-TW`. An unrecognised value falls back to `zh-TW` the same way — never a hard failure over a typo in this key |
| `site_host` | `user@host` to log in to. **`reach: ssh` only** | Nothing can reach the site; preflight fails naming this key |
| `site_user` | The site account the work runs under — the user half of `site_host`, said plainly, so a summary can name it. `scripts/preflight.sh` FAILs when the two disagree, because one value written twice drifts silently | Nothing breaks; the summary cannot say whose account this is |
| `seqera_user` | This member's Seqera username — the Username column of `tw runs list`. Where a lab reaches the site through **one shared account**, this is the only thing that tells two members apart; `$USER` is the same for everybody | A run cannot be attributed to the person who launched it |
| `site_bridge` | On MSYS only: `wsl` or `none` — whether `scripts/on_site.sh` (and `fetch.sh`/`push.sh`) route ssh through `scripts/utils/wsl_ssh.sh`, i.e. `wsl.exe -e ssh` (PITFALLS 16b/16g). Auto-detected (`wsl` if `wsl.exe -e true` succeeds, else `none`) unless set explicitly. Read on every other platform too, but always `none` there — WSL is a Windows-only concept | Nothing breaks on Linux/macOS. On MSYS with no usable `wsl.exe`, `on_site.sh` refuses (`wrong_shell`) rather than trying Git Bash's own ssh, which cannot multiplex at all |
| `ssh_control_path` | Where the multiplexed master's socket lives. **`reach: ssh` only** | Defaults to `~/.ssh/cm-%r-%h-%p`. It must not contain `:` — illegal in a Windows filename. Under the WSL bridge (`site_bridge: wsl`) the default is left as that literal `~/...` string, unexpanded, because the master lives inside WSL and only WSL's own shell can resolve the `~` against the right home — an MSYS-expanded `$HOME/.ssh/...` would name a path on the Windows side that nothing there is listening on |
| `ssh_max_parallel` | How many concurrent sessions `scripts/on_site.sh` opens on one shared master at once, via a lock directory (`mkdir`, not `flock` — not portable to a Mac). **`reach: ssh` only**; this site caps concurrent sessions per connection too (PITFALLS 16e), and several callers sharing one master reach that cap faster than one ever did — see `docs/LAB_AGENTS.md` §6 | Defaults to 4. A caller that cannot get a slot waits until `ON_SITE_TIMEOUT` |
| `storage_root` | Where runs live. Exported as `LAB_RUNS_DIR`; every other path derives from it | Nothing works; scripts refuse to guess |
| `local_root` | The local side's root — the machine-local mirror of `storage_root`, read by `scripts/inspect_sides.sh` and `scripts/init_workspace.sh local`. May point anywhere the member already keeps work: a desktop folder, a cloud-drive sync folder, a Windows path reached from WSL. `init_workspace.sh --root` overrides it outright for one call | Defaults to `$HOME/agentic-bioflow`, same as before this key existed |
| `workspace_id` | The Seqera workspace. **The one value a lab shares** — everything else below is per person | Cannot reach Platform |
| `compute_env` | This member's compute environment name | Cannot launch |
| `slurm_account` | The allocation compute time is billed to | Jobs are refused. There is deliberately **no default**: one would bill somebody else's project |
| `agent_connection` | Identifier for this member's outputs reader. **Must be unique** | Two members sharing one are refused permanently |
| `agent_java` | A Java 21 runtime | The reader will not start |
| `agent_jar` | Seqera's agent | The reader will not start |
| `tw_bin` | Seqera's CLI, if not on `PATH` | Falls back to `PATH` |
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

<local root>/                      (local side, "local"; settings key `local_root`,
                                    default $HOME/agentic-bioflow)
└── projects/<same name as the site>/    (T29: no <seqera_user> layer here -
    ├── rawdata/        staging; scripts/push.sh sends this up      matches the
    └── runs/<same name as the site>/                       portable folder's
        └── results/    brought back by scripts/fetch.sh - read-only  own shape)

<portable_root>/projects/<same name as the site>/    (T23; only once one is
├── analysis/       analysis.md, R/Python, figures; what an IDE opens  adopted)
└── submission/     the built package

    Local side, WITH NO portable folder adopted: analysis/ and submission/
    stay beside rawdata/runs instead, at the same <local root>/projects/
    <project>/ base - never both places at once.

    A project already living at the OLD shape (<local root>/<seqera_user>/
    projects/<project>/...) keeps living there - detected per project, by
    whether that path already exists (docs/SETTINGS.md's own "Migration:
    none", applied to this change too). Only a brand new project, on a
    machine with no old directory for it yet, gets the shape above.
    scripts/where.sh --project-paths <project> resolves all of this in one
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

## Moving a deployment to the user's own machine

`reach: local` -> `reach: ssh` is a move of two files and one added key. The
run area, the token's *contents*, the workspace and the compute environment do
not change; what changes is which machine holds the settings.

1. Copy `_personal/env.yaml` and `_personal/.seqera_token` from the site into
   `${XDG_CONFIG_HOME:-~/.config}/agentic-bioflow/` on the user's machine,
   keeping them together and mode 600. That is where `settings.sh` looks with
   no variable set, so this step is the whole of "make it findable".

   **On Windows, ignore the mode this shell prints.** Git Bash mounts NTFS
   without `acl`, so `chmod 600` there reads back as 644 whatever the file's
   real permissions are (PITFALLS 16j) - a number nothing in Windows wrote and
   nothing consults. What decides is the file's ACL, and a file in your own
   user profile is owner-only by default. `set_setting` asks Windows directly
   and refuses only if the answer names someone else (PITFALLS 16k), so the
   location above is the right one here too; it is a USB stick or a
   cloud-drive folder, which have no ACLs at all, that it will turn down.

2. **Set nothing.** This step used to read "point `LAB_SETTINGS_FILE` at the
   copy", and that instruction is what manufactured the failure it was meant to
   prevent: a variable that lives in one shell's startup file, on a machine
   that may have two shells with two homes. Make sure `LAB_RUNS_DIR` is *not*
   exported here either — on the user's machine it names a path on the site,
   and it would redirect both the read and the write to a local directory
   nothing else knows about.
3. Add `reach: ssh` and `site_host`. Leave `storage_root` as the **site's**
   path: it is where runs live, and that has not moved.
4. Fix the site account's `~/.bashrc` — PITFALLS 16c. Skipping this is the one
   step whose failure wears the site's error message rather than a setup error.
5. `scripts/install_deps.sh --cli-only` on the user's machine. Seqera's CLI
   reaches Platform over HTTPS from wherever Claude runs, so the user's machine
   needs its own copy; `agent_java` and `agent_jar` stay pointing at the site,
   where the outputs reader actually runs.
6. `scripts/preflight.sh`. It asks whether the site can be reached before
   anything else, and prints the line to paste if it cannot.

The copies on the site can then go. Leaving them is not dangerous, but two
settings files for one deployment will disagree eventually, and the one that
loses is whichever the user did not edit.

## The portable folder (T23, Fixes #17)

The procedure above moves a deployment from the site to **one** machine. It
says nothing about a **second** one - a new laptop, say - which used to mean
rerunning the whole of `setup` there too, even though nothing about the
deployment itself had changed. The portable folder is what closes that gap:
build it once, and adopting it on another machine is one command, not a
second onboarding.

```
<portable_root>/
├── config/
│   ├── env.yaml              the portable keys below, and only those
│   └── .seqera_token.enc     the token, encrypted - never the plaintext
└── projects/<project>/
    ├── analysis/
    └── submission/
```

`<portable_root>` is chosen by the member, once, and can be anywhere they
already keep things that follow them between machines - a cloud-sync folder,
an external drive, any path. **There is deliberately no `<seqera_user>`
layer under it**, unlike the site side: a portable folder belongs to one
person by construction, so nothing needs to tell members apart inside it.

**Building it:** `scripts/portable_root.sh init <path>` on a machine that
already has this deployment's settings. It creates the structure, migrates
this machine's **portable keys** into `config/env.yaml` (`reach`,
`seqera_user`, `workspace_id`, `compute_env`, `slurm_account`, `site_host`,
`site_user`, `storage_root`, `email`, `language`, `record_adapter`,
`record_ref`, `agent_connection`), and encrypts the current token into
`config/.seqera_token.enc` given a passphrase. **Machine-derived keys are
left out on purpose** - `site_bridge`, `ssh_control_path`, `tw_bin`,
`local_root`, `agent_java`, `agent_jar` - because they describe *this
machine*, not the person; T27 formalises the full two-column split. Safe to
re-run: it never overwrites a file that is already there, so running it again
on an already-set-up machine is an in-place upgrade, not a rebuild.

**Adopting it on another machine:** `scripts/settings.sh --adopt <path>`.
This writes a small pointer file at
`${XDG_CONFIG_HOME:-~/.config}/agentic-bioflow/portable_root` naming the
absolute path - **never an environment variable**, for the same reason
`LAB_SETTINGS_FILE` is never meant to be exported as a habit (PITFALLS
16j/16k, 25): a variable set in one shell's startup file and not another's is
how this repo's worst settings-file bugs happened, and a file at the one
location every shell already agrees on ($HOME) has none of that problem.

Once adopted, `scripts/settings.sh` resolves a key in this order:

1. the pointer file, to find `<portable_root>`
2. `<portable_root>/config/env.yaml` (the portable keys)
3. this machine's own local settings file (everything else - the
   machine-derived keys, or every key at all on a machine that has never
   adopted anything)

`settings.sh --set` still only ever writes to the local file (step 3) - the
portable file is edited only by rebuilding or by hand, never by an ordinary
command that runs on someone's behalf.

**A pointer to a path that is not there right now** - the common case is a
cloud-sync folder that has not finished syncing to this machine yet - is
never read as "never set up": `settings.sh` says explicitly which path it
is pointing at and why it cannot be read, rather than falling through to "no
settings file" the way an absent XDG default would.

**The token never crosses in plaintext.** The first time something on a
newly-adopted machine needs it, `scripts/portable_root.sh decrypt-token`
asks for the passphrase and decrypts `config/.seqera_token.enc` into this
machine's own ACL-protected cache - the same path `token_file()` already
resolves to (`dirname(local settings file)/.seqera_token`), so nothing else
has to change to start using it. Encryption prefers `age`, falls back to
`openssl enc`, and - if neither is on PATH - falls back to building the
portable folder **without** a token at all, explaining that the next machine
will need to get one some other way (setup step 3).

**No portable folder at all - `settings.sh --reconstruct`.** The fallback
for issue #17's actual reported shape: a site whose `_personal/env.yaml` only
ever held what `install_deps.sh`/`agent_ctl.sh` discovered on their own
(`agent_java`, `agent_jar`, `tw_bin`, `agent_connection`) and nothing a person
was ever asked for. This reads `tw info` / `tw workspaces list` / (once a
workspace is confirmed) `tw compute-envs list` and prints each finding as a
**candidate**, never writes anything itself - every value here still has to
be asked for rather than guessed, the same rule as every other key in the
table above. `slurm_account` cannot be read from Platform at all; the site's
own `sacctmgr`/`sshare` are what it takes to confirm.

**Cloud-sync folders are allowed here, unlike the settings file itself.** A
`portable_root` is explicitly expected to often be one - that is the point of
it. `scripts/init_workspace.sh` and `scripts/portable_root.sh` warn (not
refuse) when `local_root` or `portable_root` looks like one: large files sync
slowly and burn quota, and the decrypted token and the Positron bridge
connection file must never live there, even though the encrypted token is
fine to.

## The "setup once is enough" contract (T27)

Every key in the table near the top of this file belongs to exactly one of
two layers, and which layer decides what has to happen on a new machine:

| Layer | Keys | Where it lives | On a new machine |
|---|---|---|---|
| **Portable** | `reach`, `seqera_user`, `workspace_id`, `compute_env`, `slurm_account`, `site_host`, `site_user`, `storage_root`, `email`, `language`, `record_adapter`, `record_ref`, `agent_connection` | `<portable_root>/config/env.yaml`, once adopted (T23) | Carried across by `settings.sh --adopt` - typed in exactly once, ever, on the machine that first built the portable folder |
| **Machine-derived** | `site_bridge`, `ssh_control_path`, `tw_bin`, `local_root`, `agent_java`, `agent_jar` | This machine's own local settings file, always | Re-derived automatically after `--adopt` - never copied, never asked for a second time either |

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
- `local_root` — asked once, on this machine, the same question T21 added to
  `setup`'s step ②. Not portable by design: where a person keeps their work
  is a per-machine choice, not a per-person one - a desktop with a big disk
  and a laptop with a small one legitimately answer differently.
- `agent_java` / `agent_jar` — these name a path **on the site**, not on this
  machine at all, so "re-derive" here means "stay pointed at the site's own
  values", which the site's own `_personal/env.yaml` already has from
  whenever it was first set up. A newly-adopting laptop never needs these -
  the outputs reader they name runs on the site, reached through
  `scripts/on_site.sh`, never here.

**Verify-only, before anything else.** `setup` runs `scripts/setup_verify.sh`
as its very first act (before deciding repair vs first-run vs adopt):
settings complete and `preflight.sh` green → report that in seconds and stop,
never walking a working machine through checks it does not need. Anything
else → continue into whichever of repair/first-run/adopt actually applies.

### New machine: the three steps that cannot be skipped

Everything above is what a portable folder removes. What is left is real,
and this says so plainly rather than implying a portable folder makes setup
disappear entirely - three things are per-machine no matter what, because
none of them is a *value* that could travel in a settings file at all:

1. **Local tools.** `jq`, `curl`, Seqera's CLI, WSL on Windows (PITFALLS
   16b/16f) - whatever is missing from *this* machine's own PATH. A settings
   key cannot install a binary.
2. **The first connection to the site.** The site accepts no saved
   credential, only a one-time code typed by a human once per session
   (PITFALLS 16h). No portable folder, key, or token can stand in for this -
   it is the one step that is genuinely, deliberately unautomatable.
3. **Positron's bridge**, if this member uses it for downstream analysis - a
   separate install on this machine, unrelated to anything in a settings file
   (a different branch's own card; not built here).

Three steps, not ten: this is the entire gap between "adopted a portable
folder" and "fully working", and nothing above pretends otherwise.

### Open question: `agent_connection` across two machines at once

**Not measured, and this file says so rather than guessing.** The outputs
reader (`scripts/agent_ctl.sh`) runs on the site and is identified by
`agent_connection`, which is portable (table above) - so adopting the same
portable folder on a second machine gives both machines the same value by
design. What happens if that member has **both machines open at once**, each
independently calling `scripts/on_site.sh --script scripts/agent_ctl.sh` -
whether the second `start`/`register` bumps the first's session, whether
Platform simply serves both, or whether something fails in a way that reads
like a different bug entirely - has never been tried. Until it is measured
(PRINCIPLES.md invariant 8), treat two machines sharing one `agent_connection`
as **untested**, not as "known to work" or "known to fail" - and if it comes
up, that is the moment to measure it and turn this paragraph into a fact.
