#!/bin/bash
# Start/stop/inspect the login-node relay.
#
# The URL is built from the CURRENT hostname, never a hardcoded one: this site
# has several login nodes (lgn301..lgn304), the head job reaches back by name,
# and a stale name points at a node with no relay running.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${NF_RELAY_PORT:-18080}"

# State must NOT live beside the script. Once this ships as a plugin the script
# sits in a read-only cache directory, and a status check run from there would
# find no pid file and report "not running" for a relay that is up.
STATE_DIR="${NF_RELAY_STATE_DIR:-${LAB_RUNS_DIR:?set LAB_RUNS_DIR to the execution area}/_relay}"
mkdir -p "$STATE_DIR"
STATE="$STATE_DIR/relay.json"
LOG="$STATE_DIR/relay.log"
HOSTNAME_NOW="$(hostname)"
URL="http://${HOSTNAME_NOW}:${PORT}"

alive() { [ -f "$STATE" ] && kill -0 "$(python3 -c "import json;print(json.load(open('$STATE'))['pid'])" 2>/dev/null)" 2>/dev/null; }

case "${1:-status}" in
  start)
    if alive; then echo "already running: $(python3 -c "import json;print(json.load(open('$STATE'))['url'])")"; exit 0; fi
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
  stop)
    if alive; then
      kill "$(python3 -c "import json;print(json.load(open('$STATE'))['pid'])")" && echo "stopped"
    else echo "not running"; fi
    rm -f "$STATE"
    ;;
  status)
    if alive; then
      python3 -c "import json;d=json.load(open('$STATE'));print(f\"running pid={d['pid']}  {d['url']}  since {d['started']}\")"
      # A relay started on a different login node is useless to us now.
      REC=$(python3 -c "import json;print(json.load(open('$STATE'))['host'])")
      [ "$REC" = "$HOSTNAME_NOW" ] || echo "WARNING: relay was started on '$REC' but you are on '$HOSTNAME_NOW'."
    else echo "not running"; exit 1; fi
    ;;
  url) echo "$URL" ;;
  denied)
    # What did this site refuse? The command layer asks this without knowing
    # that the answer comes from a CONNECT proxy's log - see
    # docs/SITE_ADAPTER.md. A site with unrestricted egress prints nothing.
    if [ -f "$LOG" ]; then
      out=$(grep DENY-DOMAIN "$LOG" | tail -"${2:-20}")
      [ -n "$out" ] && printf '%s\n' "$out" || echo "nothing refused"
    else
      echo "no egress log at $LOG"
    fi
    ;;
  env)
    # Paste-ready values for the compute environment. JVM does not read
    # https_proxy, so NXF_OPTS is required alongside it.
    cat <<EOF
https_proxy=$URL
HTTPS_PROXY=$URL
http_proxy=$URL
HTTP_PROXY=$URL
NXF_OPTS=-Dhttps.proxyHost=${HOSTNAME_NOW} -Dhttps.proxyPort=${PORT} -Dhttp.proxyHost=${HOSTNAME_NOW} -Dhttp.proxyPort=${PORT}
EOF
    ;;
  *) echo "usage: egress_ctl.sh {start|stop|status|url|env|denied [n]}" >&2; exit 2 ;;
esac
