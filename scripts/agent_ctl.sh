#!/bin/bash
# Start/stop/inspect the Seqera Tower Agent on the login node.
#
# Deliberately mirrors egress_ctl.sh: nohup + a pid file, NOT tmux. The agent used
# to live in a tmux session; when that server went away the agent died with it
# while the relay - started this way - survived. Two daemons, two survival
# mechanisms, and the one that died is the one Platform needs to read run outputs.
#
# The agent is what lets Platform fetch reports (MultiQC HTML, counts TSV) off
# this cluster. With it down, /workflow/<id>/reports returns
#   {"message":"No online agent. Check that Tower Agent is running at your cluster."}
# and the run's outputs look absent even though they are on disk.
set -uo pipefail

# State must NOT live beside the script - see the note in egress_ctl.sh.
STATE_DIR="${TW_AGENT_STATE_DIR:-${LAB_RUNS_DIR:?set LAB_RUNS_DIR to the execution area}/_agent}"
mkdir -p "$STATE_DIR"
STATE="$STATE_DIR/agent.json"
LOG="$STATE_DIR/agent.log"

# Nothing here may default to one person's machine. The agent's Java and jar
# have to be somewhere every member can read - a home directory is mode 700 on
# this kind of cluster, so a jar placed there exists for exactly one person -
# and the connection ID must be unique per agent, so it cannot have a default
# at all. See PRINCIPLES.md, invariant 3.
. "$(dirname "${BASH_SOURCE[0]}")/settings.sh"
. "$(dirname "${BASH_SOURCE[0]}")/require_python.sh"
require_python || exit 1
JAVA="${TW_AGENT_JAVA:-$(setting agent_java)}"
JAR="${TW_AGENT_JAR:-$(setting agent_jar)}"
CONN="${TW_AGENT_CONNECTION:-$(setting agent_connection)}"
WORKDIR="${TW_AGENT_WORKDIR:-${LAB_RUNS_DIR}/_work}"
TOKEN_FILE="${SEQERA_TOKEN_FILE:-${LAB_RUNS_DIR}/_personal/.seqera_token}"
API="${SEQERA_API_URL:-https://api.cloud.seqera.io}"

pid_of() { python3 -c "import json;print(json.load(open('$STATE'))['pid'])" 2>/dev/null; }
alive()  { [ -f "$STATE" ] && kill -0 "$(pid_of)" 2>/dev/null; }

case "${1:-status}" in
  start)
    if alive; then echo "already running: pid=$(pid_of)"; exit 0; fi
    # A connection identifier only has to be unique, so generating one is safe
    # in a way that guessing an allocation code is not. Recorded immediately:
    # the compute environment's credential is tied to it, so it must be the
    # same string on the next start.
    if [ -z "$CONN" ]; then
      CONN="${USER}-$(hostname -s)-$(date +%Y%m%d)"
      set_setting agent_connection "$CONN"
      echo "assigned connection id: $CONN"
    fi

    for v in agent_java:JAVA agent_jar:JAR; do
      k="${v%%:*}"; n="${v##*:}"
      [ -n "${!n}" ] || { echo "ERROR: '$k' is not set in the deployment settings." >&2
                          echo "Ask the user for it; do not guess it." >&2; exit 1; }
    done
    for f in "$JAVA" "$JAR" "$TOKEN_FILE"; do
      [ -r "$f" ] || { echo "ERROR: missing or unreadable: $f" >&2
                       echo "If this is somebody else's home directory, that is the bug." >&2
                       exit 1; }
    done
    # An established run area already has this from a prior nextflow run; a
    # fresh one (new member, new storage_root) does not, and the agent refuses
    # to start rather than create it itself.
    mkdir -p "$WORKDIR"
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
  register)
    # Tell Seqera this agent exists. ORDER MATTERS: the agent has to be running
    # already, or this fails with "The agent is not online" (PITFALLS 2) - the
    # server checks for a live connection before it will issue a credential.
    alive || { echo "start the agent first: agent_ctl.sh start" >&2; exit 1; }
    [ -n "$CONN" ] || { echo "no agent_connection recorded; run 'agent_ctl.sh start' first" >&2; exit 1; }
    TW="${TW_BIN:-$(setting tw_bin)}"; [ -n "$TW" ] || TW="$(command -v tw)"
    WS="${TOWER_WORKSPACE_ID:-$(setting workspace_id)}"
    NAME="${2:-$CONN}"
    TOWER_ACCESS_TOKEN="$(cat "$TOKEN_FILE")" \
      "$TW" credentials add agent -n "$NAME" ${WS:+-w "$WS"} \
            --connection-id "$CONN" --work-dir "$WORKDIR" --overwrite || exit 1
    echo "registered '$NAME' for connection '$CONN'"
    echo "Use it when building the compute environment: SEQERA_CREDENTIALS=$NAME"
    ;;
  online)
    # The only check that matters: does Platform consider the agent reachable?
    # A live local process is not the same thing as an established connection.
    TOKEN="$(cat "$TOKEN_FILE")"
    WS="${TOWER_WORKSPACE_ID:-$(setting workspace_id)}"
    [ -n "$WS" ] || { echo "ERROR: no workspace_id in the deployment settings." >&2; exit 1; }
    OUT=$(curl -s -H "Authorization: Bearer $TOKEN" \
      "$API/workflow/${2:?usage: agent_ctl.sh online <runId>}/reports?workspaceId=$WS")
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
  *) echo "usage: agent_ctl.sh {start|stop|status|register [name]|online <runId>}" >&2; exit 2 ;;
esac
