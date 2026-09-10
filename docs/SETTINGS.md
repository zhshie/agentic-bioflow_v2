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
| `reach` | How the site is reached: `none`, `local` or `ssh`. See SITE_ADAPTER contract 6 | Defaults to `local`, which is right only when this deployment runs on the site |
| `site_host` | `user@host` to log in to. **`reach: ssh` only** | Nothing can reach the site; preflight fails naming this key |
| `site_user` | The site account the work runs under — the user half of `site_host`, said plainly, so a summary can name it. `scripts/preflight.sh` FAILs when the two disagree, because one value written twice drifts silently | Nothing breaks; the summary cannot say whose account this is |
| `seqera_user` | This member's Seqera username — the Username column of `tw runs list`. Where a lab reaches the site through **one shared account**, this is the only thing that tells two members apart; `$USER` is the same for everybody | A run cannot be attributed to the person who launched it |
| `ssh_control_path` | Where the multiplexed master's socket lives. **`reach: ssh` only** | Defaults to `~/.ssh/cm-%r-%h-%p`. It must not contain `:` — illegal in a Windows filename |
| `storage_root` | Where runs live. Exported as `LAB_RUNS_DIR`; every other path derives from it | Nothing works; scripts refuse to guess |
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

<local root>/                      (local side, "local"; default $HOME/agentic-bioflow)
└── <seqera_user>/
    └── projects/<same name as the site>/
        ├── rawdata/        staging; scripts/push.sh sends this up
        ├── runs/<same name as the site>/
        │   └── results/    brought back by scripts/fetch.sh - read-only
        ├── analysis/       analysis.md, R/Python, figures; what an IDE opens
        └── submission/     the built package
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
