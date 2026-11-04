---
name: verify-abf
description: "Launch the agentic-bioflow platform (abf_platform web + receiver + MCP, abf_station agent, abf-platform CLI) from an empty folder and drive it like a user: log in on the web page, list compute environments, open /settings, call MCP tools, take screenshots, save evidence. Use when asked to verify, try, demo or reproduce behaviour of the platform in a real process rather than through pytest."
user-invocable: true
disable-model-invocation: false
---

# verify-abf: drive the platform like a user

Every command and output below was run on the Linux cloud VM (Python 3.11, Node 22, Playwright 1.63 with Chromium
under `/opt/pw-browsers`) against `origin/v3`. It uses throwaway data and loopback ports only. No product file is
touched. The pytest harnesses (`platform/tests/*_harness.py`) are the machine check; this skill is the by-hand one.

## Surfaces a user touches

| Surface | Entry | Default port |
|---|---|---|
| Web (login, board `/`, `/settings`, `/usage`, `/launch`, `/upload`, `/c/{id}` confirmation) | `abf-platform web` | 8789 |
| CLI | `abf-platform user|ce|token|pat|agent-token|dataset|launch|cancel|resume|...` | none |
| MCP over HTTP (Bearer personal access token) | `abf-platform mcp --http` (`/mcp`) | 8788 |
| Receiver for Nextflow trace messages | `abf-platform serve` | 8787 (plain 404 on `/`; routes are `/trace/...`, `/user-info`) |
| Station agent (outbound only, no port) | `abf-station run` | none |

`web`, `serve` and `mcp` are three separate processes sharing one data folder. The login page needs only `web`.

## Launch

```bash
# 1. install (once per VM). Run from the repo root. Afterwards delete platform/build and platform/abf_platform.egg-info
#    (pip leaves them as untracked files).
python3 -m venv /tmp/abfv && /tmp/abfv/bin/pip install -q ./platform
rm -rf platform/build platform/abf_platform.egg-info

# 2. one data folder = one instance. ABF_PLATFORM_DB alone moves index.db, tokens.db and platform.db into that folder.
export V=/tmp/abfv/bin ABF_PLATFORM_DB=/tmp/abfx/data/index.db D=/tmp/abfx
rm -rf $D && mkdir -p $D/data $D/evidence

# 3. a user, a web password, a compute environment
$V/abf-platform user add alice --lab lab-x
$V/python -c "from abf_platform import store; store.set_web_password(store.default_tokens_path(),'alice','correct horse battery')"
$V/abf-platform ce create --name lab-a --platform slurm-platform --agent agent-t --work-dir /data/w --launch-dir /data/l --head-queue normal --head-job-options "-A ACCT -c 4"

# 4. the servers, on non-default ports, each in its own session so they outlive the call
(setsid $V/abf-platform serve --port 18787 >$D/serve.log 2>&1 & echo $! >$D/serve.pid)
(setsid $V/abf-platform web   --port 18789 >$D/web.log   2>&1 & echo $! >$D/web.pid)
(setsid $V/abf-platform mcp --http --port 18788 >$D/mcp.log 2>&1 & echo $! >$D/mcp.pid)
```

Ran: `user add` prints `added user alice (lab lab-x); issue a token with: abf-platform pat new --user alice`;
`ce create` prints `compute environment lab-a created (status creating)` followed by
`沒有代理在線，尚未預檢 ... agent agent-t is offline` (expected, no agent yet).

**Why `store.set_web_password` and not `abf-platform user passwd`:** `passwd` (and `--temporary`) refuse anything that is
not a real controlling terminal, by design, so a script cannot type a person's password. For a throwaway data folder
the store call is the same function the pytest `World.user()` uses. Never do this against real data.

**Ready when** (about 3 s after start):
- `$D/web.log` contains `abf-platform confirmation page on http://127.0.0.1:18789` and `Application startup complete`;
- `curl -s -o /dev/null -w "%{http_code}" localhost:18789/login` is `200`;
- `curl -s -o /dev/null -w "%{http_code}" localhost:18788/` is `401` (MCP is up and wants a token);
- `curl -s -o /dev/null -w "%{http_code}" localhost:18787/` is `404` (receiver is up).

**Optional: the station agent.** It needs a deployment folder with `config/env.yaml` (without it: `abf-station will not
start: the deployment folder ... has no settings file`, exit 2). `reach: none` is enough to connect:

```bash
mkdir -p $D/dep/config && printf 'reach: none\n' >$D/dep/config/env.yaml && chmod 600 $D/dep/config/env.yaml
$V/abf-platform agent-token new agent-t --user alice | grep -o 'abf_w[A-Za-z0-9_-]*' >$D/agent.token; chmod 600 $D/agent.token
(setsid $V/abf-station run --platform http://127.0.0.1:18787 --token-file $D/agent.token --deployment $D/dep >$D/station.log 2>&1 & echo $! >$D/station.pid)
# ready: station.log says "abf-station 0.1.0 is connected to http://127.0.0.1:18787 as agent-t"
$V/abf-platform ce preflight lab-a; echo exit=$?
```

Measured: `connect: pass - the site answers`, then `work_dir`, `sbatch`, `squeue`, `sinfo` `fail`, `java`/`nextflow`
`cannot read the ... version`, `head_queue: unchecked`, exit 1. That is correct on a VM with no Slurm; the point is that the
job travelled platform → agent → back. A passing preflight needs a real or faked site (see `platform/tests/station_harness.py`).

**Shutdown:** `for p in station mcp web serve; do [ -f $D/$p.pid ] && kill -TERM $(cat $D/$p.pid); done`. Ran: all four ports
then answer `000` (refused) within 2 s, logs end `Application shutdown complete.`, nothing left to clean in `$D` except files.

## Doctor (read-only)

Run before Drive, and again when something looks wrong. It changes nothing.

```bash
# 1. processes are ours, with the data folder we expect (the port alone proves nothing: any process can hold it)
for n in serve web mcp station; do f=$D/$n.pid; [ -f $f ] || continue; p=$(cat $f)
  [ -d /proc/$p ] && { echo "$n pid $p: $(tr '\0' ' ' </proc/$p/cmdline)"; tr '\0' '\n' </proc/$p/environ | grep ^ABF_PLATFORM_DB; } || echo "$n pid $p: NOT RUNNING"; done
# 2. version matches the checkout (abf-platform has no --version; abf-station does)
$V/python -c "import abf_platform;print(abf_platform.__version__)"; $V/abf-station --version     # both 0.1.0 on v3
git rev-parse --short HEAD; $V/pip show abf-platform | grep -i '^location'                          # installed from this checkout?
# 3. ports answer as ours
for p in 18789/login 18788/ 18787/; do curl -s -m3 -o /dev/null -w "$p %{http_code}\n" localhost:$p; done    # 200 / 401 / 404
# 4. is a port held by a foreign process? (no `ss` on the VM)
awk 'NR>1 && $4=="0A"{print $2}' /proc/net/tcp
```

Measured: `/proc/<pid>/cmdline` printed `/tmp/abfv/bin/python3 /tmp/abfv/bin/abf-platform web --port 18789` and
`ABF_PLATFORM_DB=/tmp/abfx/data/index.db`. The 7-line check ran in under a second. Note: if the install is not editable
(`pip install ./platform` copies), a later edit to `platform/` is not seen until you reinstall; use
`pip install -e ./platform` or `PYTHONPATH=platform python3 -m abf_platform ...` to test live code.

## Drive

All with the cookie jar `$D/jar`. Base URL `B=http://127.0.0.1:18789`.

**Web, with curl** (the login form has no CSRF field; POSTs after login need the `csrf` hidden input of the page):

```bash
B=http://127.0.0.1:18789; cd $D
curl -s -o /dev/null -w "%{http_code}\n" -d "name=alice&password=nope" $B/login                 # 401 wrong name or password
curl -s -o /dev/null -w "%{http_code} -> %{redirect_url}\n" $B/settings                          # 303 -> .../login (not logged in)
curl -s -c jar -o /dev/null -w "%{http_code} -> %{redirect_url}\n" -d "name=alice&password=correct horse battery" $B/login   # 303 -> .../
for p in / /settings /usage /launch /upload; do curl -s -b jar -o evidence/page$(echo $p|tr / _).html -w "$p %{http_code} %{size_download}B\n" $B$p; done
```

Measured: `/ 200 12883B`, `/settings 200 16883B`, `/usage 200 13553B`, `/launch 200 16343B`, `/upload 200 12976B`.
The pages are inline-styled; strip `<style>…</style>` before reading. Selectors that exist in the settings page:
`a.nv[href="/settings"]`, `main h1` (`設定`), `table.ce tbody tr` (one row per compute environment: name, platform,
status, agent, registered pipelines, last used), `form[action="/logout"] button`, header `.who` (the user name),
`.switch a[href="/settings?lang=en"]` for English. The "before you use" card (`#setup`) lists 帳號 ✓, 存取權杖 (—, "run
abf-platform token new"), 運算環境 ✗ with the agent-offline message, AI 金鑰 (later). The compute-environment row of
`lab-a` reads `lab-a slurm-platform — 未檢查 agent-t — —` before an agent connects.

**CLI:** `$V/abf-platform ce list` → `lab-a  slurm-platform  creating  agent-t  owner alice`;
`$V/abf-platform ce show lab-a` → JSON (`status`, `primary: false`, `config.workDir` …);
`$V/abf-platform launches` → `還沒有由平台送出的分析 (nothing was launched from this platform)`.

**MCP over HTTP** (Streamable HTTP; needs a personal access token and the three-step handshake):

```bash
TOK=$($V/abf-platform pat new --user alice --label verify | grep -o 'abf_pat_[A-Za-z0-9_-]*')
H=(-H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream')
SID=$(curl -s -i localhost:18788/mcp "${H[@]}" -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"verify","version":"0"}}}' | awk 'tolower($1)=="mcp-session-id:"{print $2}' | tr -d '\r')
curl -s localhost:18788/mcp "${H[@]}" -H "mcp-session-id: $SID" -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'      # 202
curl -s localhost:18788/mcp "${H[@]}" -H "mcp-session-id: $SID" -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_compute_envs","arguments":{}}}'
```

Measured: initialize → 200 with `serverInfo.name = abf-platform` (version is empty) and the command table in
`instructions`; the call returns `"compute_envs":[{"id":1,"name":"lab-a","platform":"slurm-platform","agent":"agent-t","status":"creating",...}]`,
`isError:false`. Without the token: `401 {"error":"unauthorized", ...}`. The launch/cancel/resume tools only ask; a person
presses send on `/c/{id}` (the confirmation page), so an AI cannot complete a launch through MCP alone.

**Browser with screenshots** (Playwright is preinstalled for Node; use the global module, do not install):

```js
// NODE_PATH=$(npm root -g) node shot.js http://127.0.0.1:18789 alice "correct horse battery" $D/evidence
const { chromium } = require('playwright');
(async () => { const [base,user,pw,out] = process.argv.slice(2);
  const b = await chromium.launch(); const p = await b.newPage({viewport:{width:1280,height:800}});
  await p.goto(base+'/login'); await p.fill('input[name=name]',user); await p.fill('input[name=password]',pw);
  await p.click('button[type=submit]'); await p.waitForURL(base+'/');
  await p.click('a.nv[href="/settings"]'); await p.waitForURL('**/settings');
  console.log(await p.textContent('main h1'), (await p.textContent('table.ce tbody tr')).slice(0,120));
  await p.screenshot({path: out+'/settings.png', fullPage:true});
  await p.click('form[action="/logout"] button'); await p.waitForURL('**/login'); await b.close(); })();
```

Measured output: `設定 lab-aslurm-platform— 未檢查agent-t——`; `settings.png` 153 KB; logout lands on `/login`. Python Playwright
is not installed in the system Python; use Node.

## Evidence

Write under `$D/evidence/` (it is inside the throwaway folder; copy what matters out before Cleanup, e.g. to the
session scratchpad or the PR). Names: `<surface>_<what>.<ext>`, with these used above: `page_settings.html`,
`page_launch.html`, `settings.png`, plus `serve.log`, `web.log`, `mcp.log`, `station.log` in `$D`. Record for each step the
command, the HTTP status or exit code, and the first lines of output. HTTP status and exit code are the verdict;
a screenshot is for a human to look at, never the only proof. Exit codes seen: `abf-platform` OK 0, `ce preflight` failing 1,
port already in use 3, `abf-station` refusing to start 2.

## Isolation

- Instance identity = data folder (`ABF_PLATFORM_DB`; `ABF_PLATFORM_STATE` and `ABF_PLATFORM_TOKENS` default to the same folder) + ports.
  Ran two instances side by side: second web on `--port 28789` with `ABF_PLATFORM_DB=/tmp/abfy/index.db` answered `/login` 200
  while the first ran, and `ce list` in it showed none of the first instance's environments. So: yes, they coexist
  if both the folder and every port differ.
- Same port twice is refused cleanly: `[Errno 98] ... address already in use`, exit 3, the running instance is unaffected.
- Never run without `ABF_PLATFORM_DB` set: the default is `~/.local/share/abf-platform/` (or `$XDG_DATA_HOME`).
- Bind loopback only (the default). `--host 0.0.0.0` prints a warning and exposes plain HTTP.
- Pick ports in a range you control (18xxx / 28xxx); the defaults 8787-8789 may be taken by a developer's own instance.

## Cleanup

```bash
for p in station mcp web serve; do [ -f $D/$p.pid ] && kill -TERM $(cat $D/$p.pid); done; sleep 2
# confirm nothing answers, then remove only what this run made
for p in 18787 18788 18789; do curl -s -m2 -o /dev/null -w "$p %{http_code}\n" localhost:$p/login; done   # 000 each
rm -rf /tmp/abfx /tmp/abfy        # after copying evidence out. Check the path first; never rm a data folder you did not create.
rm -rf platform/build platform/abf_platform.egg-info; git status --short                                   # must be clean
```

## Known gaps

- **Not done:** a real site. Preflight fails on `work_dir`/`sbatch`/`sinfo`/`java`/`nextflow` here; `launch` through to a
  submitted run, the `/c/{id}` confirmation press, resume, clean-up and result download were not driven. They need a
  site, or the fake site of `platform/tests/station_harness.py` (the pytest suite covers them).
- `abf-platform user passwd` cannot be scripted (terminal only, by design); this skill sets the password through `store`.
- `abf-platform` has no `--version`; use the Python import.
- Token for Nextflow (`abf-platform token new`), the `/c/{id}` page, `/upload` actions, OAuth and `rebuild` were not exercised.
- Pages are Chinese-first; English via `?lang=en` was not checked.
- Platform has no `/health` route: readiness is the three status codes above.
