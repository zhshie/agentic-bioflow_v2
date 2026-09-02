#!/bin/bash
# Start/stop/inspect the Seqera Tower Agent on the login node.
#
# Deliberately mirrors relay_ctl.sh: nohup + a pid file, NOT tmux. The agent used
# to live in a tmux session; when that server went away the agent died with it
# while the relay - started this way - survived. Two daemons, two survival
# mechanisms, and the one that died is the one Platform needs to read run outputs.
#
# The agent is what lets Platform fetch reports (MultiQC HTML, counts TSV) off
# this cluster. With it down, /workflow/<id>/reports returns
#   {"message":"No online agent. Check that Tower Agent is running at your cluster."}
# and the run's outputs look absent even though they are on disk.
set -uo pipefail

# State must NOT live beside the script - see the note in relay_ctl.sh.
STATE_DIR="${TW_AGENT_STATE_DIR:-${LAB_RUNS_DIR:?set LAB_RUNS_DIR to the execution area}/_agent}"
mkdir -p "$STATE_DIR"
STATE="$STATE_DIR/agent.json"
LOG="$STATE_DIR/agent.log"

JAVA="${TW_AGENT_JAVA:-/home/u9613010/bin/java/jdk-21.0.12.1+1/bin/java}"
JAR="${TW_AGENT_JAR:-/home/u9613010/bin/tw-agent.jar}"
CONN="${TW_AGENT_CONNECTION:-nchc-lgn-20260902}"
WORKDIR="${TW_AGENT_WORKDIR:-/work/u9613010/lab_runs/_work}"
TOKEN_FILE="${SEQERA_TOKEN_FILE:-/work/u9613010/lab_runs/_personal/.seqera_token}"

pid_of() { python3 -c "import json;print(json.load(open('$STATE'))['pid'])" 2>/dev/null; }
alive()  { [ -f "$STATE" ] && kill -0 "$(pid_of)" 2>/dev/null; }

case "${1:-status}" in
  start)
    if alive; then echo "already running: pid=$(pid_of)"; exit 0; fi
    for f in "$JAVA" "$JAR" "$TOKEN_FILE"; do
      [ -r "$f" ] || { echo "ERROR: missing or unreadable: $f" >&2; exit 1; }
    done
    # The token is passed through the environment only - never on the command
    # line, where `ps` would expose it to every user on the login node.
    TOWER_ACCESS_TOKEN="$(cat "$TOKEN_FILE")" \
      nohup "$JAVA" -jar "$JAR" "$CONN" --work-dir "$WORKDIR" >> "$LOG" 2>&1 &
    PID=$!
    sleep 3
    if ! kill -0 "$PID" 2>/dev/null; then
      echo "ERROR: agent exited immediately; last lines of $LOG:" >&2
      tail -5 "$LOG" >&2; exit 1
    fi
    python3 -c "
import json,time,sys
json.dump({'pid': $PID, 'connection': '$CONN', 'work_dir': '$WORKDIR',
           'host': '$(hostname)',
           'started': time.strftime('%Y-%m-%dT%H:%M:%S%z')}, open('$STATE','w'), indent=2)"
    chmod 600 "$STATE"
    echo "started pid=$PID  connection=$CONN"
    ;;
  stop)
    if alive; then kill "$(pid_of)" && echo "stopped"; else echo "not running"; fi
    rm -f "$STATE"
    ;;
  status)
    if alive; then
      python3 -c "
import json;d=json.load(open('$STATE'))
print(f\"running pid={d['pid']}  connection={d['connection']}  on {d['host']}  since {d['started']}\")"
    else
      echo "not running"; exit 1
    fi
    ;;
  online)
    # The only check that matters: does Platform consider the agent reachable?
    # A live local process is not the same thing as an established connection.
    TOKEN="$(cat "$TOKEN_FILE")"
    OUT=$(curl -s -H "Authorization: Bearer $TOKEN" \
      "https://api.cloud.seqera.io/workflow/${2:?usage: agent_ctl.sh online <runId>}/reports?workspaceId=${TOWER_WORKSPACE_ID:-85879869587002}")
    if grep -q "No online agent" <<<"$OUT"; then
      echo "OFFLINE - Platform cannot reach this cluster; run outputs will look missing"; exit 1
    fi
    python3 -c "
import json,sys
d=json.loads('''$OUT''')
r=d.get('reports',d if isinstance(d,list) else [])
print(f'ONLINE - Platform lists {len(r)} report(s)')
for x in r: print('   ', x.get('display') or x.get('key'))" 2>/dev/null || echo "ONLINE (unparsed response)"
    ;;
  *) echo "usage: agent_ctl.sh {start|stop|status|online <runId>}" >&2; exit 2 ;;
esac
