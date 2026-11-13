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

### Giving a person the commands for their own computer

A person who works in RStudio on their own computer needs three things from you: a token, the address, and the package. What the commands do is in
docs/PLATFORM.md, "Commands on your own computer".

1. **The token.** On the machine that runs the platform: `abf-platform user add <name> --lab <lab>` once, then `abf-platform pat new --user <name>`. The
   token is shown once; hand it over through a channel that is not a chat room others read, and never put it in a file of this repository. It does not
   expire; `abf-platform pat list` shows the ids and `abf-platform pat revoke <id>` ends one (the person then gets "the token is wrong or revoked" and
   asks you for a new one).
2. **The address.** It is the https address people open: the value of `ABF_PUBLIC_URL` in `~/.config/abf-platform/env`, or the one `tailscale funnel status`
   prints when Funnel is the way in. Give the address alone (the https address people open); the commands add `/mcp` themselves, and an
   address with a path is refused. The person then runs the `studio-connect` command of the package once, with `--server https://<address>`.
3. **The package.** The commands are part of this repository's `platform/` package: on their computer, in a clone of the repository,
   `pip install ./platform` (a virtual environment is advised), which gives them `abf-platform`. The repository is private: ask its owner to give the
   person read access (a collaborator on the repository, or a read-only deploy key) before they clone it. There is no separate download yet.

4. **The link of `publish-figure`.** When a person proposes a figure, the command prints the address of the platform's confirmation page and does not
   open it; the person opens it and presses the button. The platform builds that address from the public address of the confirmation page
   (`abf-platform web --public-url https://<your-domain>`). If it is not set, the link only opens on the machine that runs the platform and
   the person cannot use it from their own computer: set it to the same public address.

On Windows the settings file is `%USERPROFILE%\.abf\studio.json`. It holds the token in clear text, so it must not be in a folder that a cloud-sync
service copies (OneDrive, Dropbox and the like); the command says so once when it stores the file. If the public address does not answer, the person sees
that it does not, with the address: check that the machine, Caddy, `abf-mcp` and Funnel are running (section 3).

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

### Desktop platform in WSL（桌機）

This is for a lab whose platform runs on a Windows desktop, inside WSL (Windows Subsystem for
Linux). The aim: you log in to Windows, do nothing, and a minute or two later the platform is
there; if one of its processes dies, it comes back in a few seconds. It uses the same systemd
user units as "Hosting one lab" above, plus one unit for the site agent (`deploy/systemd/abf-station@.service.in`)
and one small Windows script (`deploy/wsl/keep-wsl-running.ps1`). Run the commands in the Ubuntu
window unless a step says Windows. Steps 2 and 9 may need the administrator password of the Linux side (sudo), and only you
should do them. After each command, what you should see is written next to it; if you see something else, stop there
and do not go on to the next step.

The order matters. Steps 2 to 6 only prepare files and change nothing that is running: the platform keeps working while you do them.
Step 7 restarts WSL, which stops the platform; step 8 starts it again. Everything you need for step 8 is ready before step 7, so the
platform is down for as short a time as possible.

1. **What you need.** Before anything else, in Windows PowerShell run `wsl --version`. If it prints an error, or you are not sure what it
   shows, run `wsl --update` now, before step 2 (an old WSL is otherwise found out only after step 7 has stopped the platform).
   You need WSL 2 with Ubuntu 22.04 or newer (Windows PowerShell: `wsl -l -v` shows
   VERSION 2), a recent WSL from the Microsoft Store (`wsl --update` brings it up to date), and the platform
   already installed in a virtual environment as in "Hosting one lab", step 2.
2. **Turn systemd on (the file only).** WSL starts without systemd unless you ask for it. Open the file with
   `sudo nano /etc/wsl.conf` and make sure it holds these two lines (add them at the end if the file is empty or is not there yet):
   ```
   [boot]
   systemd=true
   ```
   Save (Ctrl+O, Enter, Ctrl+X). It takes effect at the restart in step 7, not before.
3. **Write the settings file.** Go to the repository folder and copy `deploy/env.example` to `~/.config/abf-platform/env`, yours only:
   ```sh
   cd <repository-folder>
   mkdir -p ~/.config/systemd/user ~/.config/abf-platform && cp deploy/env.example ~/.config/abf-platform/env && chmod 600 ~/.config/abf-platform/env
   ```
   Open it (`nano ~/.config/abf-platform/env`), read the paragraph marked 重要 right below this step, and then set `ABF_PUBLIC_URL`, the https address people use.
   You should see no error from the commands; the file is yours only (`ls -l ~/.config/abf-platform/env` starts with `-rw-------`).

**重要 — read before you save the file.** The copied file contains two lines that must not stay: delete the `ABF_PLATFORM_DB=...` line and delete the `ABF_SITE_ADDRESS=...` line (the address Caddy listens on; the three services do not use it).
`ABF_PLATFORM_DB` says where the platform keeps its data: its tokens, its state, the uploads and the figures. If the line is left out, the platform
uses the default folder it always used. Put the line back only if your `~/.bashrc` already exports `ABF_PLATFORM_DB`, and then with exactly the same value as there.
You must never invent a new data folder, and do not fill in the `<...>` of that line: a new folder means an empty platform, and then every token, every run, every upload and every figure looks gone.
(They are not gone; they are in the old folder, but the platform is not looking there.) After step 8 you check that your existing runs are on the web page; if they are not, you stop and come back here.

**systemd does not read `~/.bashrc`.** When you started the platform by hand, whatever you had `export`ed in `~/.bashrc`
reached the processes; the services never see any of it. The three services (`abf-platform serve`, `web`, `mcp`)
read only these from the environment, one `NAME=value` per line, no `export`:
`ABF_PUBLIC_URL` (the web page and MCP), and the data locations `ABF_PLATFORM_DB`, `ABF_PLATFORM_TOKENS`,
`ABF_PLATFORM_STATE`, `ABF_PLATFORM_UPLOADS`, `ABF_PLATFORM_FIGURES` (and `XDG_DATA_HOME`, which moves the default data folder).
Go through every `export` line in `~/.bashrc` and compare: if one of the data locations is exported there, copy it into the
env file with the same value, or the services will open a new, empty database in the default folder instead of yours. If none is exported,
leave them out: the default folder is used, as before.

4. **The agent's token and one env file for each agent.**
   - The agent's token: make it with `abf-platform agent-token new <name> --user <user>`; it is shown once, so copy it
     into a file at that moment: a file inside WSL's own home folder (not under `/mnt/c`, a Windows drive, where permission
     bits mean nothing), then `chmod 600` on it. The token never goes into a unit or into any example file. If an agent
     already has a token file from when you started it by hand, use that existing token file as it is: its file name need not
     be the agent's name.
   - Name the agent with letters, digits, underscore and dot only (`lab1`, `site_a`): the name never contains a hyphen (`-`), because the
     unit's own name is built from it. The same `<name>` is used twice and must be identical: in the file
     `~/.config/abf-platform/station-<name>.env` and in the unit instance `abf-station@<name>`.
   - **Several agents.** Each agent is its own service: one `station-<name>.env` for each agent, and one `enable --now` for each.
     Example with two agents, `lab1` for the cluster and `gcb` for Google Batch (two token files, and the deployment folders
     they were using by hand):
     ```sh
     cp deploy/station.env.example ~/.config/abf-platform/station-lab1.env
     cp deploy/station.env.example ~/.config/abf-platform/station-gcb.env
     chmod 600 ~/.config/abf-platform/station-lab1.env ~/.config/abf-platform/station-gcb.env
     ```
     Fill each file in (`nano`): its own token file, its own deployment folder, the plugin folder (the same for both).
     In step 8, write `abf-station@lab1 abf-station@gcb` instead of one `abf-station@<name>`
     (a service that is enabled later is simply one more `systemctl --user enable --now abf-station@<second-name>`).
   - **What an agent's env file must hold.** The unit gives the agent the three paths in `station-<name>.env` and nothing else
     from your terminal. What the agent really needs from the environment:
     `PATH` written out in full (every folder, on one line) so that it finds `ssh` and, for Google Batch, `nextflow`, `gcloud`
     and Java 17 or newer; `JAVA_HOME` if you had exported it; `ABF_STATION_GCP_CREDENTIALS`, the service-account key file (a path), and
     `ABF_STATION_UPLOADS`, the folder where the platform keeps the waiting upload files (the same folder as `ABF_PLATFORM_UPLOADS`
     of the platform, or the `uploads` folder next to `platform.db`) for a Google Batch agent. An AWS, Azure or Kubernetes agent has
     `ABF_STATION_AWS_CREDENTIALS`, `ABF_STATION_AZURE_CREDENTIALS` or `ABF_STATION_KUBECONFIG` in the same place. The site
     connection itself needs none of these: the agent finds the shared connection through the deployment folder.
     Same rule as in step 3: go through every `export` in `~/.bashrc`, and for each one that the agent used, write it as `NAME=value` into
     that agent's `station-<name>.env` (the example file `deploy/station.env.example` shows where). A path to a key file is allowed; a key's contents never are.
5. **Put the unit files in place.** Copy the four templates and drop the `.in`; for the agent unit the file keeps the `@` in its name (`abf-station@.service`).
   First find the name of your venv folder (the virtual environment of "Hosting one lab", a folder directly under your home folder). Find it with
   `ls -d ~/*/bin/abf-platform`: it prints a line such as `/home/<you>/<venv-folder>/bin/abf-platform`, and the venv folder is the name between your home folder and `/bin`
   (if the platform is running by hand, `pgrep -af 'abf-(platform|station) (serve|web|mcp|run)'` shows the same path at the start of the line). Write that name in place of `<your-venv-folder>`:
   ```sh
   cd <repository-folder>
   for u in serve web mcp; do cp deploy/systemd/abf-$u.service.in ~/.config/systemd/user/abf-$u.service; done
   cp deploy/systemd/abf-station@.service.in ~/.config/systemd/user/abf-station@.service
   sed -i "s|<venv>|<your-venv-folder>|" ~/.config/systemd/user/abf-*.service
   ```
   Check: `grep -c '<venv>' ~/.config/systemd/user/abf-*.service` prints a `:0` count for each of the four files. Nothing is started yet.
6. **Save how the platform runs now.** While your hand-started processes are still running, write down their full command lines and the settings they were given
   (the file is readable by you only; do not paste it anywhere, it may name key files):
   ```sh
   ( umask 077; pgrep -af 'abf-(platform|station) (serve|web|mcp|run)' > ~/abf-before-switch.txt; for p in $(pgrep -f 'abf-(platform|station) (serve|web|mcp|run)'); do echo "== $p" >> ~/abf-before-switch.txt; tr '\0' '\n' < /proc/$p/environ | grep -E '^(ABF_|PATH=|JAVA_HOME=|XDG_)' >> ~/abf-before-switch.txt; done ); cat ~/abf-before-switch.txt
   ```
   Compare it with what the services will do: they use the ports 8787 (serve), 8788 (mcp) and 8789 (web), and `--public-url ${ABF_PUBLIC_URL}`.
   If you started them with another port or another flag, change the unit files in `~/.config/systemd/user/` now, before step 7. Also check that every `ABF_`, `PATH`, `JAVA_HOME` and `XDG_` value
   in the file is in the env file of step 3 or of step 4. For each `abf-station run` line, check that its `--token-file` and `--deployment` values equal the ones in that agent's `station-<name>.env`
   (these are command-line flags in the saved file, not environment variables). If the file is empty, nothing was running by hand: go on.
7. **Restart WSL. The platform is down from here.** In Windows PowerShell run `wsl --shutdown`, wait a few seconds, and start Ubuntu once more from the Start menu (or the WSL terminal you normally use).
   **This stops everything inside WSL**: every process you started there, the platform if it is running, and the
   shared SSH connection to the National Center (國網). After the restart you must connect again yourself and type the OTP
   (see "Opening the National Center connection again" below); nothing does that for you. The platform is stopped from this step until step 8 has finished: a few minutes, depending on how fast you type the commands.
   Check that it worked: `ps -p 1 -o comm=` must print `systemd` (before this step it prints `init`). If it prints `init`, go back to step 2; if the step 2 line is not accepted, run `wsl --update` in Windows PowerShell.
   If you want the platform back now, follow "Going back to starting by hand" below.
8. **Check nothing is left, then enable and start.** First do the check in "Switching from starting by hand" below: two copies fight for the same port. Then:
   ```sh
   systemctl --user daemon-reload
   systemctl --user enable --now abf-serve abf-web abf-mcp abf-station@<name>
   ```
   You should see lines like `Created symlink ...` and no error. If it says `Failed to connect to bus`, systemd is not on for you: go back to step 2 and step 7. If you want the platform back now, follow "Going back to starting by hand" below.
   Then `systemctl --user is-active abf-serve abf-web abf-mcp abf-station@<name>` must print `active` four times (the agent waits for the site connection, which is opened below).
   **Checkpoint.** Open the platform's web page: your existing runs must be listed there, the ones you had before; otherwise stop here (an empty page, or no runs): do not go on and do not make anything new; go back to step 3
   and the paragraph marked 重要 (the data location is almost always the cause; nothing was deleted). Open the National Center connection again (below) after the checkpoint.
9. **Keep it running with nobody at a terminal.** Run `loginctl enable-linger $USER` once. If it asks for a password, run
   `sudo loginctl enable-linger $USER`. This lets your services run without a terminal window open. It does
   not keep WSL itself open: that is the job of the Windows task in step 10. The two do different jobs and you need both.
10. **Make Windows keep WSL open.** From the repository folder in Ubuntu, show what the script would do (it changes nothing):
   ```sh
   cd <repository-folder>
   powershell.exe -ExecutionPolicy Bypass -File "$(wslpath -w deploy/wsl/keep-wsl-running.ps1)"
   ```
   It prints the task it would make. Then add `-Apply` at the end to register the
   task `abf-wsl-keepalive`: when you log in to Windows it starts `powershell.exe -NoProfile -WindowStyle Hidden`, and that
   starts `wsl.exe` and keeps WSL open. A window may flash for a moment at logon. If a window stays, minimise it, do not close it
   (closing it lets WSL stop), and report it. The task runs with your
   normal rights and asks for no administrator password; add `-Distro <name>` if the Linux you use is not the default one. **It does
   not start while nobody is logged in to Windows**, that is, when you are not logged in to Windows nothing runs: after a reboot, the platform is up only once you have logged in.
   If your computer's policy forbids `-ExecutionPolicy Bypass` (the command stops with a message about running scripts),
   copy `deploy/wsl/keep-wsl-running.ps1` to a Windows folder and right-click it, then choose "Run with PowerShell"
   (that runs the print-only mode; to apply, ask the person who looks after the computer, or report it).
11. **Look at what is running.** One command lists all four services: `systemctl --user status 'abf-*'`. Each should say
   `active (running)` in green. When one does not, read its last lines: `journalctl --user -u abf-web -n 50`.
   An agent that refuses to start (a wrong path, a token file that is not safe) stops in `failed` and does not retry
   every few seconds; the reason is one line `abf-station will not start: ...` in `journalctl --user -u 'abf-station@<name>'`, because under systemd there is no terminal to show it.
   - Stop: `systemctl --user stop abf-serve abf-web abf-mcp abf-station@<name>`
   - Restart: `systemctl --user restart abf-serve abf-web abf-mcp abf-station@<name>`
   - Remove: `systemctl --user disable --now abf-serve abf-web abf-mcp abf-station@<name>`, then delete the files in
     `~/.config/systemd/user/` and run `systemctl --user daemon-reload`. To remove the Windows task, run the script from step 10 with `-Remove`.
12. **RStudio in the downstream page (optional, `studio-embed`).** For a personal computer only. It makes the downstream page of a succeeded run show
   RStudio inside the page; the platform does not start it, stop it or connect to it (your browser, on this computer, does), and the
   page is as it was when you skip this step. 任何能登入這台電腦的人與這台電腦上的任何程式都連得到它，所以只適合個人電腦；不得把這個埠對外公開。
   (Anyone who can log in to this computer and any program on it can reach it, with no password: personal computers only, and never open this port to a network.)
   On the computer that also runs the platform this is a shell of the platform's owner: through it a person or program reads the analyses of every platform user, the platform databases, the token files, the signing key and the agent token, and with those can send analyses to the site and spend its compute allowance. Other Windows users can reach it too (WSL hands loopback ports to Windows).
   **`ABF_STUDIO_URL` is a setting of the whole deployment, so it is for every user's downstream page:** each person's page frames the port on *their own* computer and asks them to allow local network access, and a person who has no RStudio there sees a blank frame. Set it only for a deployment with one user; do not set it on a deployment with several users (a setting for each user is later work). Allowing local network access is a permission given to the platform's address, which is safe only because the platform page runs no script.
   1. **Install RStudio Server yourself.** It is Posit's program under the AGPL licence; this project does not ship it, does not change it and
      does not install it (ADR 0010, Decided 4). Get the Ubuntu package from Posit's download page and install it: `sudo apt install ./rstudio-server-<version>-amd64.deb`.
   2. **Before you start the unit, disable the system service the package starts.** The package enables and starts `rstudio-server`, a system
      service that runs as root and listens on port 8787, the port `abf-serve` uses, so it must be stopped before the unit below starts. Run `sudo systemctl disable --now rstudio-server`;
      `systemctl is-active rstudio-server` must print `inactive`.
   3. **Name the address.** In `~/.config/abf-platform/env` add the line `ABF_STUDIO_URL=http://127.0.0.1:8790` (copy it from `deploy/env.example`; the
      port is not 8787 to 8789, which are the platform's own, and it is written here only: the unit reads its port from this line). Then
      `systemctl --user restart abf-web`. A value that is not `http://127.0.0.1:<port>` or `http://localhost:<port>` stops `abf-web` with one
      line that names `ABF_STUDIO_URL` (`journalctl --user -u abf-web -n 20`).
   4. **Install and start the unit** (it runs as you, not as root, and listens on `127.0.0.1` only):
      copy `deploy/systemd/abf-rstudio.service.in` to `~/.config/systemd/user/abf-rstudio.service` (the name without `.in`), run `systemctl --user daemon-reload`, then
      `systemctl --user enable --now abf-rstudio`.
   5. **Look.** `systemctl --user status abf-rstudio` says `active (running)`. `ss -ltn` shows `127.0.0.1:8790`, and no line for port 8790 that begins with
      anything but `127.0.0.1`. Open the downstream page of a succeeded run: the first time, the browser asks whether to allow this site to reach devices on the local network; press Allow (it is needed: with Refuse, or in a browser that does not support it, the frame stays blank). Then RStudio is in the middle of the page. If the frame is blank, press "Open RStudio in a new tab" on the page.
      Run the `studio-connect` command once on this computer (the first of the terminal commands on the page), and make sure RStudio can find `abf-platform`
      (its folder in the `PATH` RStudio sees), so the two lines on the page work in the Console.
   - Stop: `systemctl --user stop abf-rstudio`. Restart: `systemctl --user restart abf-rstudio`.
   - Remove: `systemctl --user disable --now abf-rstudio`, delete `~/.config/systemd/user/abf-rstudio.service`, run `systemctl --user daemon-reload`, and take the
     `ABF_STUDIO_URL` line out of the env file (then `systemctl --user restart abf-web`). The package itself is removed with `sudo apt remove rstudio-server`.

**Switching from starting by hand.** Your hand-started platform is a set of detached processes (`abf-platform serve`, `web`, `mcp`,
and one `abf-station run` for each agent): closing the terminal does nothing to them. Step 7's `wsl --shutdown` already stopped
them all, so after it there should be none left. Before you run step 8's `enable --now`, check, in the Ubuntu window:
```sh
pgrep -af 'abf-(platform|station) (serve|web|mcp|run)'
```
It prints nothing when none is left: go on. If it prints lines, something you started by hand is still running (started again, or by a
login script). Each line starts with a process number. Only for the process numbers that are listed, and only for those, run `kill <process number>`
(several numbers may follow one `kill`), then run the `pgrep` line again and make sure it prints nothing. Do not stop things by a name pattern: that also catches an editor
open on the env file, a `tail` of a log, and the services themselves. Otherwise the hand-started processes hold the ports, the services cannot start, and you may end up with two copies.
Expect the platform to be unreachable for a few minutes, from step 7 until step 8 is done.

**Going back to starting by hand.** In the Ubuntu window: stop and remove the four services,
`systemctl --user disable --now abf-serve abf-web abf-mcp abf-station@<name>` (every agent you enabled), then remove the unit files with
`rm ~/.config/systemd/user/abf-serve.service ~/.config/systemd/user/abf-web.service ~/.config/systemd/user/abf-mcp.service ~/.config/systemd/user/abf-station@.service`
and `systemctl --user daemon-reload`. Take the two lines `[boot]` and `systemd=true` out of `/etc/wsl.conf` (`sudo nano /etc/wsl.conf`),
then in Windows PowerShell run `wsl --shutdown` and open Ubuntu again. Start the platform the way you did before: `abf-platform serve` as in
`docs/PLATFORM.md` section 1, the agent as in section 6 of the same file; for `web` and `mcp` use the command lines you saved in step 6 (`~/abf-before-switch.txt`), and see section 9 ("The confirmation page") of the same file for
`abf-platform web` and section 4 for `abf-platform mcp`. Also remove the Windows task, otherwise
WSL still opens at every logon: run the script from step 10 with `-Remove`.

**Opening the National Center connection again.** After `wsl --shutdown` or a reboot the shared SSH connection to the site is gone, and the agent
waits. Open it yourself, in three steps, in the same terminal window where you normally work with the site (the place of the deployment's settings reaches your commands through your `~/.bashrc`;
a window that does not read it would look in the wrong place):
1. `cd <plugin-folder>` (the plugin folder, the same one as `ABF_STATION_PLUGIN_ROOT` in the agent's env file).
2. `scripts/on_site.sh --check-reach`. When the connection is missing it prints one line, the `ssh ...` command to open it: paste exactly that line, and type the OTP yourself
   (only you have the one-time code; nothing in this setup can). If the connection is already open it prints no such line.
3. `scripts/on_site.sh --check-master; echo $?` must print `0` (open); `1` means not open: do step 2 again.

The agent looks at the connection again about every 25 seconds by itself, so it picks the connection up without a restart. Within a minute, look at the site connection of that agent on the web page: it should turn to open
(you check this by eye; nothing here checks it for you).

**What this does not do.** The connection to the National Center does not come back by itself: after a reboot or `wsl --shutdown`,
you connect again and type the OTP; the agent waits for it. Tailscale Funnel is not handled here: it is set up as in
"Hosting one lab" and nothing in these steps starts or restarts it. If a computer is off or nobody is logged in to Windows, the platform is not running.

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
| `figures/` | The private figure galleries made with `publish_figure`, `<figures>/<user id>/<run id>/` (the figures, their code and parameters, and an `index.json`). Next to `platform.db`; `ABF_PLATFORM_FIGURES` overrides. | Yes: they are not kept anywhere else. |
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
| `abf-platform agent-token new <name> --user U` | Issue a token for one agent name and show it once; `--user` makes the agent belong to that user (required once the platform has a user). |
| `abf-platform agent-token list [name]` | List the agent tokens with their ids, user and whether each is revoked (never the token itself). |
| `abf-platform agent-token revoke <name>` / `abf-platform agent-token revoke --id N` | Revoke every token of an agent name, or only the one token with that id (the same name's other tokens keep working). |
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

Or run `deploy/platform-upgrade.sh`: it does the same three steps, then waits (120 seconds by default; `--wait N` changes it) for every agent that was online before the restart to say hello again, names the ones that did not, and exits with 1.

If `deploy/systemd/` or `deploy/Caddyfile.template` changed in the new version, copy them again as
in steps 3 and 4 and run `systemctl --user daemon-reload` (and restart Caddy) before the restart.

### Google Batch on the platform host

To let people launch on an `awsbatch-platform` environment, the same host needs Java 17 or newer, Nextflow, the aws CLI (the AWS command line), a `storage_root` (the run folders go to `<storage_root>/_aws_runs/`) and the credential file at `ABF_STATION_AWS_CREDENTIALS` (or `_personal/aws-credentials`), readable by that user only; see `docs/PLATFORM.md`, "Launching on AWS Batch". AWS bills the lab's AWS account for what a launch starts, and the platform has no estimate or limit for it yet: set a budget alert in AWS.

To let people launch on an `azbatch-platform` environment, the same host needs Java 17 or newer, Nextflow, the az CLI (the Azure command line), a `storage_root` (the run folders go to `<storage_root>/_azure_runs/`) and the credential file at `ABF_STATION_AZURE_CREDENTIALS` (or `_personal/azure-credentials`), readable by that user only; see `docs/PLATFORM.md`, "Launching on Azure Batch". The pool must already exist. Azure bills the lab's Azure account for what a launch starts, and the platform has no estimate or limit for it yet: set a budget alert in Azure.

To let people launch on a `k8s-platform` environment, the platform host needs the `kubectl` command line, and the agent needs `ABF_STATION_KUBECONFIG` pointing at a kubeconfig file (the kubeconfig never leaves the agent's computer). Set the station setting `k8s_head_image` (required, no default): the image the head Pod runs, with Nextflow in it. `platform_public_url` must be an `https://` address the cluster can reach. The head Pod's service account needs a Role in the namespace that allows create, get, list, watch and delete on pods (and get, list on pods/log, and get on persistentvolumeclaims). The cluster's own cloud or data centre bills; the platform has no estimate. No migration is needed.

To let people launch on a `googlebatch-platform` environment, the host that runs `abf-station run` (next to `abf-platform serve`) needs: Java 17 or newer, Nextflow, `gcloud` (the Google Cloud CLI), a `storage_root` in `config/env.yaml` (the run folders go to `<storage_root>/_gcb_runs/`), and the service-account key file at `ABF_STATION_GCP_CREDENTIALS` (or `_personal/gcp-sa.json` in the deployment folder), readable by that user only. The host must be Linux or WSL. Everything else is in `docs/PLATFORM.md`, "Launching on Google Batch". Google bills the lab's Google Cloud account for what a launch starts; before a launch the platform checks each person's monthly cloud cap and shows an estimate, or says why it cannot work one out (`docs/CLOUD.md`); it does not stop a run that is already going.

### Datasets in the lab's bucket

For a `googlebatch-platform` environment the input files live in the lab's Google Cloud bucket. The steps, one sentence each:

1. Each person's files go under their own place in the bucket, `gs://<bucket>/uploads/<user>/` (the folder-like part of the bucket address after `gs://<bucket>/`). The bucket is the one in the environment's `workDir`; another bucket is refused.
2. A person puts files there from their own computer with `gcloud storage cp <folder>/* gs://<bucket>/uploads/<user>/rawdata/`. For a single file over 2 GB the platform gives only this same line.
3. Then the person keeps them as a named Dataset: `abf-platform dataset register --name <name> --version <version> --samplesheet <sheet.csv> --file gs://<bucket>/uploads/<user>/rawdata/<file> --user <user> --destination <environment>` (`abf-platform dataset list` and `abf-platform dataset show` read them back). The platform keeps names and places only; it does not open the files.
4. An AI client uses the `launch` tool with its `dataset` argument (and `dataset_version`) instead of a samplesheet.
5. The platform does not grant, and does not check, who may write to the bucket. That is the Google Cloud project owner's job, done on Google's side.
6. The web page /upload sends files up to 2 GB into the bucket: choose the environment, name and version the dataset, choose the FASTQ files (and a samplesheet, or let the R1/R2 pairs make one) and press Upload. Each file waits on the platform host until the agent has copied it and the size in the bucket is the same, then it is removed. When every file is in, the dataset is registered by itself and is one of the choices at step 4 of the launch page. A file over 2 GB still takes the `gcloud storage cp` line of point 2, and an AI tool that sends a file is not built. When a launch is sent, Google Batch still checks every path cell is in the `workDir` bucket. For the /upload page to work, the agent that runs `abf-station run` must have `ABF_STATION_UPLOADS` set to the absolute path of the folder where the platform keeps the waiting files (`uploads_root`: `ABF_PLATFORM_UPLOADS`, else the `uploads` folder next to `platform.db`); without it the agent refuses every upload with "這個代理沒有設定上傳資料夾（ABF_STATION_UPLOADS）", which asks the administrator to set it.

## 6. Not built yet

Nothing is listed here at the moment. The proxy and Funnel set-up (section 2) and the systemd
units (section 3) now ship in `deploy/`; running them on a real host is the operator's own
step, and `docs/TESTING.md` says how to check it.
