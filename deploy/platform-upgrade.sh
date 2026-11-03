#!/usr/bin/env bash
# Upgrade the platform on this host, then check that every site agent came back
# (docs/OPERATIONS.md, section 4, "Upgrade").
#
# Usage: deploy/platform-upgrade.sh [--wait SECONDS]
#
# Runs, in the order of the manual upgrade: git pull, pip install ./platform, then the restart of
# the three services. Any step that fails stops the script before the next one. Just before the
# restart it notes which agents are online and the time; after the restart it reads the agent list
# (the platform's own list_agents, read-only) every few seconds until each of those agents has
# said hello again (its last contact is later than that time), or the wait is over. Agents that
# did not come back are named and the exit code is 1. It never writes to the databases, never
# repairs an agent, never rolls back, and does not make the backup (do that first).
# Exit codes: 0 all back (or none to check), 1 not all back or a step failed, 2 bad arguments.
#
# Settings (environment): ABF_UPGRADE_WAIT_SECONDS (default 120), ABF_UPGRADE_POLL_SECONDS (2),
# ABF_UPGRADE_PULL_CMD / ABF_UPGRADE_INSTALL_CMD / ABF_UPGRADE_RESTART_CMD replace the three
# commands (the tests use this), ABF_UPGRADE_PYTHON is the python that runs the check (default
# python3; give the platform venv's python if the system one lacks the platform's packages).
# The data folder is found as the services find it: ABF_PLATFORM_STATE, else platform.db next
# to ABF_PLATFORM_DB, else ${XDG_DATA_HOME:-~/.local/share}/abf-platform/.
set -euo pipefail

usage() {
  echo "Usage: deploy/platform-upgrade.sh [--wait SECONDS]" >&2
  echo "  --wait SECONDS  how long to wait for the agents after the restart (default 120)" >&2
}

wait_s=${ABF_UPGRADE_WAIT_SECONDS:-120}
while [ $# -gt 0 ]; do
  case $1 in
    --wait)
      if [ $# -lt 2 ]; then usage; exit 2; fi
      wait_s=$2; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done
case $wait_s in ''|*[!0-9]*) echo "--wait needs a whole number of seconds, got: $wait_s" >&2; usage; exit 2 ;; esac
poll_s=${ABF_UPGRADE_POLL_SECONDS:-2}
case $poll_s in ''|*[!0-9]*) echo "ABF_UPGRADE_POLL_SECONDS needs a whole number, got: $poll_s" >&2; exit 2 ;; esac

here=$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")
root=$(dirname -- "$here")
export PYTHONPATH="$root/platform${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
py=${ABF_UPGRADE_PYTHON:-python3}

if [ -n "${ABF_PLATFORM_DB:-}" ]; then
  data_dir=$(dirname -- "$ABF_PLATFORM_DB")
else
  data_dir=${XDG_DATA_HOME:-$HOME/.local/share}/abf-platform
fi
state=${ABF_PLATFORM_STATE:-$data_dir/platform.db}

pull_cmd=${ABF_UPGRADE_PULL_CMD:-git pull}
install_cmd=${ABF_UPGRADE_INSTALL_CMD:-pip install ./platform}
restart_cmd=${ABF_UPGRADE_RESTART_CMD:-systemctl --user restart abf-serve abf-mcp abf-web}

echo "Reminder: take a backup before you upgrade (docs/OPERATIONS.md, backups). This script does not make one."

step() { # <label> <command>
  echo "Step: $1"
  local rc=0
  (cd -- "$root" && bash -c "$2") || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "Upgrade stopped: the step '$1' failed (exit code $rc). Nothing after it was run. Fix that and run this script again." >&2
    exit 1
  fi
}

# One small python program for both reads; it only calls the platform's list_agents.
agents_py() { # snapshot <state> | missing <state> <t0> <name>...
  "$py" - "$@" <<'PY'
import datetime, sys, time
from abf_platform import agents

mode, state = sys.argv[1], sys.argv[2]
now = time.time()
rows = agents.list_agents(state, now)
if mode == "snapshot":
    print("%.3f" % now)
    for r in rows:
        if r["status"] == "online":
            print(r["name"])
else:
    t0_ms = int(float(sys.argv[3]) * 1000)
    expected = sys.argv[4:]
    back = set()
    for r in rows:
        dt = datetime.datetime.strptime(r["last_contact_at"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=datetime.timezone.utc)
        if int(round(dt.timestamp() * 1000)) > t0_ms:
            back.add(r["name"])
    for n in expected:
        if n not in back:
            print(n)
PY
}

read_failed() {
  echo "Upgrade stopped: could not read the agent list from $state with $py. Set ABF_UPGRADE_PYTHON to the platform's python and check the data folder." >&2
  exit 1
}

step "pull" "$pull_cmd"
step "install" "$install_cmd"

snap=$(agents_py snapshot "$state") || read_failed
t0=$(printf '%s\n' "$snap" | sed -n '1p')
names=()
while IFS= read -r line; do
  if [ -n "$line" ]; then names+=("$line"); fi
done < <(printf '%s\n' "$snap" | sed '1d')

step "restart" "$restart_cmd"

if [ "${#names[@]}" -eq 0 ]; then
  echo "沒有在線代理人可檢查 (no agent was online before the restart, so there is nothing to wait for)."
  exit 0
fi
echo "Waiting up to ${wait_s}s for ${#names[@]} agents to say hello again."

start=$SECONDS
while :; do
  missing=$(agents_py missing "$state" "$t0" "${names[@]}") || read_failed
  if [ -z "$missing" ]; then
    echo "All ${#names[@]} agents reconnected."
    exit 0
  fi
  if [ $((SECONDS - start)) -ge "$wait_s" ]; then break; fi
  sleep "$poll_s"
done

list=$(printf '%s\n' "$missing" | paste -sd, - | sed 's/,/、/g')
sp=" "
echo "這些代理人重啟後沒有重新連上：$list。請檢查它們的 token 和擁有者（abf-platform${sp}agent-token；docs/TESTING.md 的「Owner binding follow-up」一節第 2 步），並看代理人的日誌。" >&2
exit 1
