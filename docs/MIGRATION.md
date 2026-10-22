# Moving from v2 to v3

## 1. Who this is for and what changes

You use v2: the Claude Code plugin that runs pipelines through Seqera Platform (`main` is the
v2 line until v3.0.0, `docs/ROADMAP.md`). This page is for you if you now want v3.

- **v2**: the plugin calls `tw` and its own `scripts/`; Seqera Platform is the execution
  backend and holds the list of runs.
- **v3**: the plugin (and Claude Desktop, Codex, the web pages) talks over MCP to the
  self-hosted abf platform, `abf-platform` (ADR 0004, ADR 0006). The platform never contacts
  Seqera Platform; the truth about a run is Nextflow's own records, and the platform's index
  can be thrown away and rebuilt (`docs/PLATFORM.md` section 5). Seqera becomes an optional
  execution backend (ADR 0001, superseded in part by ADR 0004).

What does not change: your settings file and your project folders (`docs/SETTINGS.md`).

## 2. Step by step

1. **Keep your settings file as it is.** Do not rewrite, move or delete `env.yaml`, and
   do not run setup again. Nothing in v3 asks you to rebuild it.
2. **Ask whoever runs the platform for a user and a personal access token (PAT).** On the
   platform's own machine, the operator makes you a user and a token at the terminal:

   ```bash
   abf-platform user add <name> --lab <lab>
   abf-platform pat new --user <name> --label laptop
   ```

   `abf-platform pat new` prints the PAT once (it starts with `abf_pat_`) and keeps only its
   hash; a lost PAT cannot be shown again, the operator issues another. Never paste a PAT into
   a chat with the AI, a file in a git repository or a params file.
3. **Give the platform URL and the PAT to your MCP client, not to the settings file.** Today
   there is no settings key for either (see section 6). The URL and the PAT go into the
   client's own MCP setting, as in `docs/PLATFORM.md` section 4:

   ```bash
   claude mcp add --transport http abf-platform <platform-URL>/mcp --header "Authorization: Bearer <PAT>"
   ```

   Type it in your own terminal so the PAT stays out of the conversation.
4. To retire a PAT: `abf-platform pat list` shows ids (never values), `abf-platform pat revoke <id>`
   stops it from the next request on.

## 3. Seqera fields

The Seqera fields in your settings file are optional in v3. They are not removed and they are
not required: the v3 platform does not read them. The v2 scripts and skills still read them, so
keep them if you use those paths:

- `seqera_user`, `workspace_id`: read by `scripts/settings.sh`, `scripts/where.sh`,
  `scripts/runs_board.sh` and the `setup`, `launch` and `runs` skills.
- `compute_env`: read by `scripts/settings.sh`, `scripts/preflight.sh`, `scripts/ce_apply.sh`.
- `tw_bin` (the `tw` command, one per machine): read by `scripts/env.sh`,
  `scripts/settings.sh`, `scripts/install_deps.sh`.
- `.seqera_token` (next to `env.yaml`, mode 600): read by `scripts/settings.sh` and the scripts
  that call `tw`, such as `scripts/runs_board.sh`.

If you only use the platform's MCP tools, none of these is consulted.

## 4. Existing runs and project folders

- **Project folders carry over untouched.** `projects/<project>/` (rawdata, `runs/<run>/results`,
  analysis, submission) lives under your settings root; the platform does not move or delete it.
- **The platform's list of runs starts empty.** It is built from what Nextflow reports to it
  (`docs/PLATFORM.md` section 3), and nothing is copied from Seqera Platform.
- **Older runs can be added with `rebuild`**: `abf-platform rebuild <launch_folder> ...` reads the
  launch folders you list (`.nextflow/history`, `.nextflow.log`, the trace file), not Seqera. A
  folder without `.nextflow/history` is named and skipped. A run whose log is gone comes back
  with task numbers of zero; a run Nextflow never finished comes back as `lost`.
- `rebuild` drops the index first, so run it before you start new runs, never while one is going
  (a rebuilt run has no token owner and its later messages are refused). It never opens the token
  file, so issued tokens stay valid.

## 5. Going back to v2

v2 is the `main` branch until v3.0.0; v3 is built on the branch `v3` (`docs/ROADMAP.md`).
Because section 2 never touched your settings file, going back is:

1. Remove the platform from your client: `claude mcp remove abf-platform`.
2. Install the plugin from `main` again.
3. Ask the operator to run `abf-platform pat revoke <id>` for your PAT.

Your project folders and Seqera fields are as you left them.

## 6. Not built yet

- **No settings key for the platform URL or the PAT on the plugin side.** Searching
  `scripts/settings.sh`, `docs/SETTINGS.md` and `platform/` finds none; the PAT is only the
  MCP client's header today. This page will name the key when one exists.
- The plugin's own skills still call `tw` and `scripts/` rather than the platform
  (ADR 0006 describes the move; Stage 2 and 3 of `docs/ROADMAP.md`).
- Copying run history out of Seqera Platform: no tool does this; use `rebuild` on launch folders.

## 7. From the v2 `tw` flow to starting on the v3 platform

The plugin's launch and setup skills still describe the v2 flow, which uses `tw` (the Seqera
command line); that flow is for v2 only. On v3 you start an analysis through the platform, with
`abf-platform launch` or the MCP `launch` tool, and you need no Seqera account or access token
for it.

| v2 (`tw` flow) | v3 (platform) |
|---|---|
| `tw launch` | `abf-platform launch`, or ask the AI to call the MCP `launch` tool |
| `tw runs list` | MCP `list_runs` (and `get_run` for one run) |
| `tw runs cancel` | MCP `cancel`, confirmed by a person at the terminal |

See `docs/PLATFORM.md` for the platform commands and the confirmation page.
