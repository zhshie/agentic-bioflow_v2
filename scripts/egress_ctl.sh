#!/bin/bash
# Start/stop/inspect the login-node relay.
#
# Not tmux: mirrors agent_ctl.sh's nohup + pid file - a tmux session dies with
# its server, and this needs to survive a closed terminal.
#
# The URL is built from the CURRENT hostname, never a hardcoded one: this site
# has several login nodes (lgn301..lgn304), the head job reaches back by name,
# and a stale name points at a node with no relay running.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"
. "$HERE/require_python.sh"
require_python || exit 1

# The port cannot have a fixed default. It is one process per member on a
# shared login node, so a constant means the second member's channel fails to
# bind and the first member's is what they end up talking to. It also cannot be
# picked fresh on every start: the address is baked into the compute
# environment, so it has to survive a restart. Hence the order below - an
# explicit choice, then the settings file, then whatever was used last, then a
# free port chosen once and written down.
PORT="${NF_RELAY_PORT:-$(setting relay_port)}"

# State must NOT live beside the script. Once this ships as a plugin the script
# sits in a read-only cache directory, and a status check run from there would
# find no pid file and report "not running" for a relay that is up.
STATE_DIR="${NF_RELAY_STATE_DIR:-${LAB_RUNS_DIR:?set LAB_RUNS_DIR to the execution area}/_relay}"
mkdir -p "$STATE_DIR"
STATE="$STATE_DIR/relay.json"
LOG="$STATE_DIR/relay.log"
HOSTNAME_NOW="$(hostname)"

alive() { [ -f "$STATE" ] && kill -0 "$(python3 -c "import json;print(json.load(open('$STATE'))['pid'])" 2>/dev/null)" 2>/dev/null; }

# A channel that is already up owns its port, whatever a freeness test would
# say about it - the test would find the port taken by the very process we are
# asking about and move on, renaming an address the compute environment is
# still using.
if [ -z "$PORT" ] && alive; then
    PORT=$(python3 -c "import json;print(json.load(open('$STATE'))['port'])" 2>/dev/null)
fi
if [ -z "$PORT" ]; then
    PORT=$(python3 - "$STATE" <<'PY'
import json, socket, sys
def free(p):
    with socket.socket() as s:
        try:
            s.bind(("0.0.0.0", p)); return True
        except OSError:
            return False
try:
    prev = json.load(open(sys.argv[1]))["port"]
except Exception:
    prev = None
if prev and free(prev):
    print(prev); raise SystemExit
for p in range(18080, 18180):
    if free(p):
        print(p); raise SystemExit
raise SystemExit("no free port in 18080-18179")
PY
    ) || { echo "could not find a free port" >&2; exit 1; }
fi
URL="http://${HOSTNAME_NOW}:${PORT}"

case "${1:-status}" in
  start)
    # A running relay keeps the domain list it started with: this deployment's
    # extra list (specs/002-relay-allowlist) is read once, at startup. Say so,
    # or a member who just added a domain believes it is in force.
    if alive; then echo "already running: $(python3 -c "import json;print(json.load(open('$STATE'))['url'])") - a changed domain list takes effect only after 'egress_ctl.sh restart'"; exit 0; fi
    # Same anchoring as scripts/agent_ctl.sh (PITFALLS 36): started through
    # `scripts/on_site.sh --script`, this inherits a `mktemp -d` that is gone
    # as soon as the round trip ends. The relay does not spawn shells, so it
    # has no equivalent of the agent's corrupted-output failure - but a
    # long-lived daemon whose cwd is a deleted directory is a trap either way
    # (a core dump has nowhere to go, `lsof`/`/proc` read as "(deleted)", and
    # any future relative path silently resolves nowhere).
    cd "$LAB_RUNS_DIR" 2>/dev/null || cd / || exit 1
    nohup python3 "$HERE/nf_relay.py" "$PORT" >> "$LOG" 2>&1 &
    PID=$!
    python3 - "$PID" "$PORT" "$HOSTNAME_NOW" "$URL" "$STATE" <<'PY'
import json, socket, sys, time
pid, port, host, url, state = sys.argv[1:6]
for _ in range(50):
    try:
        socket.create_connection(("127.0.0.1", int(port)), timeout=1).close()
        break
    except Exception:
        time.sleep(0.1)
else:
    print("ERROR: relay did not bind", file=sys.stderr); sys.exit(1)
json.dump({"pid": int(pid), "port": int(port), "host": host, "url": url,
           "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, open(state, "w"), indent=2)
print(f"started pid={pid}  {url}")
PY
    chmod 600 "$STATE"
    ;;
  restart)
    # stop, then start: what the commands mean by "restart the outbound
    # channel" after a domain is added (independent acceptance of 002, M3).
    # Same port - the address is baked into the compute environment. $PORT is
    # the running relay's own port by now (resolved above); `stop` deletes the
    # state file that remembers it, so it is passed on explicitly, or `start`
    # would take the lowest free port instead (002 re-verification, M-C).
    NF_RELAY_PORT="$PORT" bash "$HERE/egress_ctl.sh" stop || exit $?
    NF_RELAY_PORT="$PORT" exec bash "$HERE/egress_ctl.sh" start
    ;;
  stop)
    if alive; then
      OLD_PID="$(python3 -c "import json;print(json.load(open('$STATE'))['pid'])")"
      kill "$OLD_PID" && echo "stopped"
      # Wait for it to let go of the port, or a restart's start races it.
      for _ in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$OLD_PID" 2>/dev/null || break; sleep 0.5; done
    else echo "not running"; fi
    rm -f "$STATE"
    ;;
  status)
    if alive; then
      python3 -c "import json;d=json.load(open('$STATE'));print(f\"running pid={d['pid']}  {d['url']}  since {d['started']}\")"
      # A relay started on a different login node is useless to us now.
      REC=$(python3 -c "import json;print(json.load(open('$STATE'))['host'])")
      [ "$REC" = "$HOSTNAME_NOW" ] || echo "WARNING: relay was started on '$REC' but you are on '$HOSTNAME_NOW'."
      # What the running relay loaded of this deployment's own list, from the
      # startup lines it logged - and, out loud, when it did not load (#45,
      # spec 002 TC-023). A list that failed to load must not look like a
      # deployment that never added any.
      if [ -f "$LOG" ]; then
        START_LN=$(grep -n 'nf-relay on ' "$LOG" | tail -1 | cut -d: -f1)
        [ -n "$START_LN" ] && tail -n +"$START_LN" "$LOG" | grep 'this deployment' \
          | sed -E 's/^[0-9]{2}:[0-9]{2}:[0-9]{2} +//' | head -8 || true
      fi
    else echo "not running"; exit 1; fi
    ;;
  url) echo "$URL" ;;
  denied)
    # What did this site refuse? The command layer asks this without knowing
    # that the answer comes from a CONNECT proxy's log - see
    # docs/SITE_ADAPTER.md. A site with unrestricted egress prints nothing.
    if [ -f "$LOG" ]; then
      out=$(grep -E 'DENY-(DOMAIN|PRIVATE)' "$LOG" | tail -"${2:-20}")
      [ -n "$out" ] && printf '%s\n' "$out" || echo "nothing refused"
    else
      echo "no egress log at $LOG"
    fi
    ;;
  env)
    # Paste-ready values for the compute environment. JVM does not read
    # https_proxy, so NXF_OPTS is required alongside it.
    #
    # `env --scoped` prefixes each line with where the variable has to apply.
    # That is the adapter's knowledge, not the caller's: NXF_OPTS configures
    # the head job's JVM and means nothing on a compute node, while the proxy
    # variables are needed in both places. ce_apply.sh reads this form.
    if [ "${2:-}" = "--scoped" ]; then
      cat <<EOF
both https_proxy=$URL
both HTTPS_PROXY=$URL
both http_proxy=$URL
both HTTP_PROXY=$URL
head NXF_OPTS=-Dhttps.proxyHost=${HOSTNAME_NOW} -Dhttps.proxyPort=${PORT} -Dhttp.proxyHost=${HOSTNAME_NOW} -Dhttp.proxyPort=${PORT}
EOF
      exit 0
    fi
    cat <<EOF
https_proxy=$URL
HTTPS_PROXY=$URL
http_proxy=$URL
HTTP_PROXY=$URL
NXF_OPTS=-Dhttps.proxyHost=${HOSTNAME_NOW} -Dhttps.proxyPort=${PORT} -Dhttp.proxyHost=${HOSTNAME_NOW} -Dhttp.proxyPort=${PORT}
EOF
    ;;
  *) echo "usage: egress_ctl.sh {start|stop|restart|status|url|env [--scoped]|denied [n]}" >&2; exit 2 ;;
esac
