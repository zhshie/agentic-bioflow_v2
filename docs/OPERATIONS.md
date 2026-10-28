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

One host name sits in front of all three processes. People and Claude connectors reach that one
name; Caddy (a small web server that handles https) takes the request and sends each path to the
right local port. The processes themselves keep listening on loopback only.
`deploy/Caddyfile.template` is the whole configuration, one file for both set-ups below. It reads
its site address from the variable `ABF_SITE_ADDRESS`, which lives in the env file
(`deploy/env.example` is the template for it).

| Paths | Go to |
|---|---|
| `/trace/*`, `/user-info`, `/agent/hello`, `/agent/poll`, `/agent/result/*` | `serve`, 8787 |
| `/mcp*`, `/.well-known/oauth-protected-resource*` | `mcp --http`, 8788 |
| everything else: the login and consent pages, and the OAuth routes (`/.well-known/oauth-authorization-server`, `/register`, `/authorize`, `/token`, `/revoke`) | `web`, 8789 |

The Nextflow progress reports (`/trace/*`) go through the same address, so a compute node can
post to the public URL (see "Public URL" in section 5).

**A rented server (VPS): Caddy faces the internet and gets the certificate itself.**

1. Point the domain's DNS record at the server and keep ports 80 and 443 open.
2. Install Caddy.
3. Copy `deploy/env.example` to `~/.config/abf-platform/env` and set `ABF_SITE_ADDRESS=<your-domain>`
   and `ABF_PUBLIC_URL=https://<your-domain>`.
4. Give Caddy that file: `caddy run --config deploy/Caddyfile.template --envfile ~/.config/abf-platform/env`,
   or, for a Caddy that runs as a system service, an `EnvironmentFile=` line in its unit that names
   the file. Caddy asks for the certificate and renews it by itself.

**A desktop behind Tailscale Funnel: Funnel provides the https, Caddy only splits the paths.**

1. Use the same env file, but set `ABF_SITE_ADDRESS=http://127.0.0.1:8080`. An address that starts
   with `http://` gets no certificate, and it listens on this machine only.
2. Start Caddy the same way: `caddy run --config deploy/Caddyfile.template --envfile ~/.config/abf-platform/env`.
3. Publish it: `tailscale funnel --bg 8080`. Funnel accepts the public side on port 443, 8443 or
   10000 only, and forwards only to `http://127.0.0.1`; that is why Caddy sits on a local port in
   between. The https address Funnel prints is the value for `ABF_PUBLIC_URL`; restart the three
   services after you set it.

Check either set-up as in "Public URL" (section 5). The whole procedure on a rented server, from
nothing to a working address, is under "Hosting one lab" (section 5).

## 3. Keeping them running

The three processes start at boot and come back after a crash under systemd. This repository
ships one user unit per process in `deploy/systemd/`: `abf-serve.service.in`, `abf-mcp.service.in` and
`abf-web.service.in` (templates: copy them and drop the `.in`). They listen on 127.0.0.1 only, read their settings from
`~/.config/abf-platform/env`, restart five seconds after a failure, and have `<venv>` where the
folder of your virtual environment goes. To install them:

1. Copy the three files to `~/.config/systemd/user/`.
2. Replace `<venv>` in them with the path of your virtual environment, relative to your home
   folder (for `~/abf-venv`, that is `abf-venv`).
3. Run `systemctl --user daemon-reload`, then `systemctl --user enable --now abf-serve abf-mcp abf-web`.
4. Run `loginctl enable-linger <user>` once, so the user units keep running when nobody is
   logged in.

Bearer tokens never go into a unit file; they are issued with the commands in section 5 and
shown once.

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

To back up everything marked Yes, run `deploy/backup.sh <destination-folder>`. It makes a
folder `abf-backup-<UTC time>` there (mode 700, files 600), copies the two databases with
SQLite's own backup so a copy taken while the services run is whole, and leaves out `index.db`.
It sends nothing anywhere and deletes nothing. To restore, stop the three services, put the files
back into the data folder, and start them again; run `abf-platform rebuild` if the index is
wanted fresh.

## 5. Administration from the CLI

All of these run as the operator on the platform host.

| Command | What it does |
|---|---|
| `abf-platform token new` | Issue a token and show it once. |
| `abf-platform agent-token new <name> [--user U]` | Issue a token for one agent name and show it once; `--user` makes the agent belong to that user. |
| `abf-platform agent-token revoke <name>` | Revoke every token of an agent name. |
| `abf-platform user add <name> --lab L` | Add a user (name and lab). |
| `abf-platform user passwd <name> [--temporary]` | Set the password a person logs into the confirmation page with (typed at a terminal, 8 to 1000 characters). `--temporary` instead makes a one-time temporary password, shown once at a real terminal and valid for 72 hours; the person must change it at the first web login. |
| `abf-platform pat new --user U` | Issue a personal access token for the MCP server over HTTP and show it once. |
| `abf-platform pat list` | List the tokens (never their values). |
| `abf-platform pat revoke <id>` | Revoke one token by its id. |
| `abf-platform oauth revoke <user>` | End every OAuth login of that user (access and refresh tokens); their personal access tokens stay. |
| `abf-platform ce create`, `update`, `list`, `show` | Store, change, list and show compute environments (Slurm is checked; other types are only stored). |
| `abf-platform ce primary`, `disable`, `enable` | Make an environment primary; disable it (no new job, no longer primary); enable it again. |
| `abf-platform ce preflight <name>` | Ask the environment's agent to check the site, and wait for the answer. |
| `abf-platform rebuild` | Drop the index and build it again from Nextflow's records. |
| `abf-platform runs assign` | Give a run that nobody owns to a user (`--user`; changing an existing owner needs `--force`). |
| `abf-platform runs offer-cleanup` | Offer the owner of a run that succeeded a clean-up request for its work folder (`RUN ...` or `--all`, `--user` to narrow). It only previews unless you add `--apply`; with it only pending requests are written, and nothing is deleted until the owner presses send on the confirmation page. |

### Public URL (progress reports)

When `way_back` is `direct` (see SETTINGS.md), a compute node posts its progress straight to
Platform, so Platform needs an address the cluster can reach. That address must be https: the
reports carry the run's token, and a plain http address would send it in the clear.
Tailscale Funnel is one way to publish such an address; any host name with a certificate in front
of Platform works too. The steps for Funnel are in the maintainer's own notes and are not
repeated here.

To check it from the site, run `curl -i https://<public>/user-info` there. A working address answers
401 (no token was sent) and the response carries the `X-ABF-Platform` header.

### Hosting one lab

（託管一間實驗室）One lab gets one host: one machine runs one copy of the platform for that lab's
people. The program is the same one anybody can install themselves; only the place differs. A host
serves one lab, and nothing here separates one lab's data from another's.

What the host needs: Linux with systemd, Python 3.10 or newer, a domain name pointing at it, and
ports 80 and 443 reachable from the internet (Caddy uses both to get its certificate). Everything
below is in this repository's `deploy/` folder; run the steps in a clone of the repository.

1. As an administrator, make a dedicated user and let its services run without a login:
   `adduser --disabled-password --gecos "" <user>`, then `loginctl enable-linger <user>`.
2. Log in as that user (a real login, so `systemctl --user` works) and install the platform:
   ```sh
   VENV=abf-venv
   python3 -m venv ~/$VENV
   ~/$VENV/bin/pip install ./platform        # run from the clone of this repository
   ```
3. Install the settings and the three units:
   ```sh
   mkdir -p ~/.config/abf-platform ~/.config/systemd/user
   cp deploy/env.example ~/.config/abf-platform/env && chmod 600 ~/.config/abf-platform/env
   ```
   Open `~/.config/abf-platform/env` and replace every `<...>`: `ABF_PUBLIC_URL=https://<your-domain>`,
   `ABF_SITE_ADDRESS=<your-domain>`, and `ABF_PLATFORM_DB=<data-folder>/index.db` (or delete that
   line to use the default folder from section 4).
   Copy each template and drop the `.in` from its name (for example `abf-serve.service.in` becomes `abf-serve.service`), then replace `<venv>` with your virtualenv path:
   ```sh
   for u in serve mcp web; do cp deploy/systemd/abf-$u.service.in ~/.config/systemd/user/abf-$u.service; done
   sed -i "s|<venv>|$VENV|" ~/.config/systemd/user/abf-*.service
   systemctl --user daemon-reload
   systemctl --user enable --now abf-serve abf-mcp abf-web
   systemctl --user status abf-serve abf-mcp abf-web
   ```
   All three should say `active (running)`.
4. As an administrator, install Caddy (from your distribution or from Caddy's own package
   source) and hand it the template and the site address:
   ```sh
   sudo cp deploy/Caddyfile.template /etc/caddy/Caddyfile
   echo 'ABF_SITE_ADDRESS=<your-domain>' | sudo tee /etc/caddy/env
   sudo mkdir -p /etc/systemd/system/caddy.service.d
   printf '[Service]\nEnvironmentFile=/etc/caddy/env\n' | sudo tee /etc/systemd/system/caddy.service.d/env.conf
   sudo systemctl daemon-reload && sudo systemctl restart caddy
   ```
   (Without the packaged service, `caddy run --config deploy/Caddyfile.template --envfile <env file>`
   does the same, as in section 2.)
5. Add the lab's people with the commands in section 5 (`abf-platform user add`, `abf-platform user passwd`).
6. Check from any other computer: `curl -i https://<your-domain>/user-info`. It must answer
   401 (no token was sent) and the response must carry the `X-ABF-Platform` header. If Caddy
   cannot get a certificate, look at `journalctl -u caddy`; the usual causes are DNS that has not
   reached the host yet and a closed port 80 or 443.

**Back it up on a schedule.** The script is `deploy/backup.sh <destination-folder>` (section 4).
It sends nothing anywhere and deletes nothing, so keep the number of old copies down yourself and
move copies off the host. Example only, not shipped as a file: as the service user, `crontab -e`
and add

```
15 3 * * * $HOME/<clone>/deploy/backup.sh $HOME/backups
```

(every night at 03:15; `<clone>` is the folder you cloned the repository into). A systemd timer
that runs the same command works as well.

**Upgrade.** Back up first, then:

```sh
cd ~/<clone> && git pull
~/$VENV/bin/pip install ./platform
systemctl --user restart abf-serve abf-mcp abf-web
```

If `deploy/systemd/` or `deploy/Caddyfile.template` changed in the new version, copy them again as
in steps 3 and 4 and run `systemctl --user daemon-reload` (and restart Caddy) before the restart.

### Google Batch on the platform host

To let people launch on a `googlebatch-platform` environment, the host that runs `abf-station run` (next to `abf-platform serve`) needs: Java 17 or newer, Nextflow, `gcloud` (the Google Cloud CLI), a `storage_root` in `config/env.yaml` (the run folders go to `<storage_root>/_gcb_runs/`), and the service-account key file at `ABF_STATION_GCP_CREDENTIALS` (or `_personal/gcp-sa.json` in the deployment folder), readable by that user only. The host must be Linux or WSL. Everything else is in `docs/PLATFORM.md`, "Launching on Google Batch". Google bills the lab's Google Cloud account for what a launch starts; before a launch the platform checks each person's monthly cloud cap and shows an estimate, or says why it cannot work one out (`docs/CLOUD.md`); it does not stop a run that is already going.

### Datasets in the lab's bucket

For a `googlebatch-platform` environment the input files live in the lab's Google Cloud bucket. The steps, one sentence each:

1. Each person's files go under their own place in the bucket, `gs://<bucket>/uploads/<user>/` (the folder-like part of the bucket address after `gs://<bucket>/`). The bucket is the one in the environment's `workDir`; another bucket is refused.
2. A person puts files there from their own computer with `gcloud storage cp <folder>/* gs://<bucket>/uploads/<user>/rawdata/`. For a single file over 2 GB the platform gives only this same line.
3. Then the person keeps them as a named Dataset: `abf-platform dataset register --name <name> --version <version> --samplesheet <sheet.csv> --file gs://<bucket>/uploads/<user>/rawdata/<file> --user <user> --destination <environment>` (`abf-platform dataset list` and `abf-platform dataset show` read them back). The platform keeps names and places only; it does not open the files.
4. An AI client uses the `launch` tool with its `dataset` argument (and `dataset_version`) instead of a samplesheet.
5. The platform does not grant, and does not check, who may write to the bucket. That is the Google Cloud project owner's job, done on Google's side.
6. Not built yet: a web page or an AI tool that sends a file into the bucket. The platform and the station agent can already write one file into the user's own place (#224, #229), but nothing in the web or the AI calls it, so today use the `gcloud storage cp` line of point 2. When a launch is sent, Google Batch still checks every path cell is in the `workDir` bucket.

## 6. Not built yet

Nothing is listed here at the moment. The proxy and Funnel set-up (section 2) and the systemd
units (section 3) now ship in `deploy/`; running them on a real host is the operator's own
step, and `docs/TESTING.md` says how to check it.
