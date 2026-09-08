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

## Keys this version does not read

`nextflow_path`, `hpc_profile`, `driver_queue`. They belong to v1, which is
still installable as a fallback and does read them. Leave them where they are:
deleting them costs the rollback path and saves three lines.

## Moving a deployment to the user's own machine

`reach: local` -> `reach: ssh` is a move of two files and one added key. The
run area, the token's *contents*, the workspace and the compute environment do
not change; what changes is which machine holds the settings.

1. Copy `_personal/env.yaml` and `_personal/.seqera_token` from the site to the
   user's machine, keeping them together and mode 600.
2. Point `LAB_SETTINGS_FILE` at the copy.
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
