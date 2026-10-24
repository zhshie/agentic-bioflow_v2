# Operating the platform

For the person who runs the platform for a lab (the operator). This describes what exists on
branch v3 today. Anything not built yet is listed in the last section, "Not built yet", and is
not described as working anywhere above it. The reference for the platform itself is
`docs/PLATFORM.md`.

## 1. The processes

The platform is three separate processes. Each is started on its own and restarted on its own;
they are not three functions of one program. They share the databases described in section 4.

| Process | What it does | Default address |
|---|---|---|
| `abf-platform serve` | Receives Nextflow's trace messages and the agents' requests. | 127.0.0.1:8787 |
| `abf-platform mcp --http` | The read-only MCP server (Streamable HTTP; without `--http` it speaks stdio). | 127.0.0.1:8788 |
| `abf-platform web` | The confirmation page where a person presses send. | 127.0.0.1:8789 |

Every default listens on this machine only. `abf-platform web --host` accepts loopback addresses
only (127.0.0.1, ::1, localhost); any other address is refused, so the page reaches other
people only through a proxy in front of it (section 2). `--public-url` tells `web` and `mcp`
the address people actually use (for `web`, an https one makes the cookie Secure).

## 2. One host name in front of all three

The chosen approach (agreed 2026-10-17): one host name in front of all three processes, with
TLS provided by Tailscale Funnel. People and Claude connectors reach that one name; the proxy
sends each path to the right local port. The processes themselves keep listening on loopback.
The actual Funnel and proxy configuration is Not built yet (see section 6); no file in this
repository implements it. Only the flags the processes already have are real: `--public-url`
on `web` and on `mcp`.

## 3. Keeping them running

Use a service manager so the three processes start at boot and come back after a crash. The
following is an example only, not a file this repository ships. With systemd user units, one
unit per process, for instance `~/.config/systemd/user/abf-serve.service`:

```ini
# example only
[Unit]
Description=abf-platform serve

[Service]
ExecStart=%h/<venv>/bin/abf-platform serve
Restart=on-failure

[Install]
WantedBy=default.target
```

Make a second and third unit the same way for `mcp --http` and `web`, then
`systemctl --user enable --now <unit>`. Run `loginctl enable-linger <user>` so user units keep
running when nobody is logged in. Bearer tokens never go into a unit file; they are issued with
the commands in section 5 and shown once.

## 4. What to back up

The platform writes these, all in one data folder. Default folder:
`${XDG_DATA_HOME:-~/.local/share}/abf-platform/`, or the folder of `ABF_PLATFORM_DB` when it is
set.

| File | Holds | Back up? |
|---|---|---|
| `index.db` | The run index. An index, not the truth (the truth is Nextflow's own records). `ABF_PLATFORM_DB` overrides the path. | No. Rebuildable: `abf-platform rebuild` drops it and builds it again from Nextflow's records. |
| `tokens.db` | Hashes of access tokens, the users and their web-password hashes, web sessions, OAuth clients and logins. Next to the index; `ABF_PLATFORM_TOKENS` overrides. | Yes. Cannot be rebuilt. |
| `platform.db` | Compute environments, agents, the queue of jobs, launches, confirmations, the hand-off record. Next to the index; `ABF_PLATFORM_STATE` overrides. | Yes. Cannot be rebuilt. |
| `web_signing.key` | The key that signs the confirmation page's cookies. Made on first start of `web`, owner-only. | Yes. Losing it logs everyone out, nothing more; keep it private. |
| `uploads/` | Samplesheets uploaded for runs, `<uploads>/<user>/`. Next to `platform.db`; `ABF_PLATFORM_UPLOADS` overrides. | Yes, if the uploaded files are not kept elsewhere. |
| `records/` | Nextflow records fetched back from the site, `records/<run name>/`. Next to `platform.db`. `rebuild` reads them. | Yes: they are what a rebuild is made from when the launch folders are gone. |

Never copy tokens or passwords out of these files; they hold hashes, not the secrets.

## 5. Administration from the CLI

All of these run as the operator on the platform host.

| Command | What it does |
|---|---|
| `abf-platform token new` | Issue a token and show it once. |
| `abf-platform agent-token new <name> [--user U]` | Issue a token for one agent name and show it once; `--user` makes the agent belong to that user. |
| `abf-platform agent-token revoke <name>` | Revoke every token of an agent name. |
| `abf-platform user add <name> --lab L` | Add a user (name and lab). |
| `abf-platform user passwd <name>` | Set the password a person logs into the confirmation page with (typed at a terminal, 8 to 1000 characters). |
| `abf-platform pat new --user U` | Issue a personal access token for the MCP server over HTTP and show it once. |
| `abf-platform pat list` | List the tokens (never their values). |
| `abf-platform pat revoke <id>` | Revoke one token by its id. |
| `abf-platform oauth revoke <user>` | End every OAuth login of that user (access and refresh tokens); their personal access tokens stay. |
| `abf-platform ce create`, `update`, `list`, `show` | Store, change, list and show compute environments (Slurm is checked; other types are only stored). |
| `abf-platform ce primary`, `disable`, `enable` | Make an environment primary; disable it (no new job, no longer primary); enable it again. |
| `abf-platform ce preflight <name>` | Ask the environment's agent to check the site, and wait for the answer. |
| `abf-platform rebuild` | Drop the index and build it again from Nextflow's records. |
| `abf-platform runs assign` | Give a run that nobody owns to a user (`--user`; changing an existing owner needs `--force`). |

### Public URL (progress reports)

When `way_back` is `direct` (see SETTINGS.md), a compute node posts its progress straight to
Platform, so Platform needs an address the cluster can reach. That address must be https: the
reports carry the run's token, and a plain http address would send it in the clear.
Tailscale Funnel is one way to publish such an address; any host name with a certificate in front
of Platform works too. The steps for Funnel are in the maintainer's own notes and are not
repeated here.

To check it from the site, run `curl -i https://<public>/user-info` there. A working address answers
401 (no token was sent) and the response carries the `X-ABF-Platform` header.

### Google Batch on the platform host

To let people launch on a `googlebatch-platform` environment, the host that runs `abf-station run` (next to `abf-platform serve`) needs: Java 17 or newer, Nextflow, `gcloud` (the Google Cloud CLI), a `storage_root` in `config/env.yaml` (the run folders go to `<storage_root>/_gcb_runs/`), and the service-account key file at `ABF_STATION_GCP_CREDENTIALS` (or `_personal/gcp-sa.json` in the deployment folder), readable by that user only. The host must be Linux or WSL. Everything else is in `docs/PLATFORM.md`, "Launching on Google Batch". Google bills the lab's Google Cloud account for what a launch starts; the platform has no cost estimate or cap yet.

## 6. Not built yet

- The Tailscale Funnel and proxy configuration for the one host name (section 2). Nothing in
  this repository implements it.
- Service-manager unit files (section 3). The example there is not shipped; no unit file is
  in the repository.
