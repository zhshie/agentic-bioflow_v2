# The settings file

One file, outside the repository, holding everything that identifies a person
or their site: `$LAB_RUNS_DIR/_personal/env.yaml`, mode 600. Nothing in it may
be copied from another member, printed into a conversation, or committed.

`scripts/settings.sh` reads and writes it. It is not a YAML parser — it reads
`key: value` and stops at the first `#`, which is all this file is allowed to
be. A settings file that needs a real parser has grown into something else.

| Key | What it is | Without it |
|---|---|---|
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
