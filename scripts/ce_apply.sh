#!/bin/bash
# Push the site's resource contract into the Seqera compute environment.
#
# The compute environment stores a COPY of the Nextflow config, not a reference
# to it. Edit configs/sites/*.config and nothing happens until this runs, and
# nothing anywhere reports the divergence - the next run just quietly uses the
# old contract. The same is true of the egress address, which is baked in and
# goes stale whenever the channel comes up somewhere else.
#
# There is no in-place edit: `tw compute-envs update` changes only the name and
# description, so applying a config means import --overwrite, which DELETES and
# recreates the environment under a NEW ID (PITFALLS 13). Anything pointing at
# the old ID - Launchpad entries above all - has to be repointed afterwards.
#
# Because of that, this shows the difference and stops. Pass --apply to commit.
#
#   ce_apply.sh                 what would change
#   ce_apply.sh --apply         change it
#
# Creating an environment from nothing (a new member has none to export) is not
# handled here yet; that belongs with onboarding, which knows the member's
# storage and account.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
TW="${TW_BIN:-tw}"
CE="${SEQERA_COMPUTE_ENV:?set SEQERA_COMPUTE_ENV to the compute environment name}"
WS="${TOWER_WORKSPACE_ID:-}"
CREDS="${SEQERA_CREDENTIALS:-}"
CONFIG="${SITE_CONFIG:-$ROOT/configs/sites/nchc.config}"
STATE_DIR="${CE_STATE_DIR:-${LAB_RUNS_DIR:?set LAB_RUNS_DIR to the execution area}/_agent}"

APPLY=0
[ "${1:-}" = "--apply" ] && APPLY=1

[ -r "$CONFIG" ] || { echo "no site config at $CONFIG" >&2; exit 1; }
mkdir -p "$STATE_DIR"
BACKUP="$STATE_DIR/ce-$(date +%Y%m%d-%H%M%S).json"

# Export first, always. This doubles as the backup and as the base for the new
# definition, so nothing outside the two fields below can drift by accident.
"$TW" compute-envs export -n "$CE" ${WS:+-w "$WS"} "$BACKUP" >/dev/null 2>&1 \
  || { echo "could not export '$CE' - does it exist in this workspace?" >&2; exit 1; }
echo "backed up: $BACKUP"

NEW="$STATE_DIR/ce-pending.json"
python3 - "$BACKUP" "$CONFIG" "$NEW" "$HERE" <<'PY'
import json, subprocess, sys
backup, config, out, here = sys.argv[1:5]
ce = json.load(open(backup))
ce["nextflowConfig"] = open(config).read()

# Refresh whatever the egress channel says its address is now. Only the names
# the adapter itself prints are touched; anything else in the environment is
# left exactly as exported.
try:
    env = subprocess.run(["bash", f"{here}/egress_ctl.sh", "env"],
                         capture_output=True, text=True, timeout=15)
    fresh = dict(l.split("=", 1) for l in env.stdout.splitlines() if "=" in l)
except Exception:
    fresh = {}
for entry in ce.get("environment", []):
    if entry.get("name") in fresh:
        entry["value"] = fresh[entry["name"]]

json.dump(ce, open(out, "w"), indent=2)
PY
[ -f "$NEW" ] || { echo "could not build the new definition" >&2; exit 1; }

# Show only what changed, and show it as config, not as JSON escapes.
python3 - "$BACKUP" "$NEW" <<'PY'
import difflib, json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
changed = False
d = list(difflib.unified_diff(a.get("nextflowConfig", "").splitlines(),
                              b.get("nextflowConfig", "").splitlines(),
                              "compute environment", "site config", lineterm="", n=1))
if d:
    changed = True
    print("\n".join(d))
av = {e["name"]: e["value"] for e in a.get("environment", [])}
bv = {e["name"]: e["value"] for e in b.get("environment", [])}
for k in sorted(set(av) | set(bv)):
    if av.get(k) != bv.get(k):
        changed = True
        print(f"  {k}: {av.get(k)!r} -> {bv.get(k)!r}")
if not changed:
    print("no difference - the compute environment already matches this site")
PY

if [ "$APPLY" != 1 ]; then
    echo
    echo "nothing applied. Re-run with --apply to overwrite '$CE'."
    echo "That deletes and recreates it under a NEW ID; repoint Launchpad entries after."
    exit 0
fi

echo
echo "overwriting '$CE' ..."
"$TW" compute-envs import -n "$CE" ${WS:+-w "$WS"} ${CREDS:+-c "$CREDS"} \
      --overwrite --wait AVAILABLE "$NEW" || exit 1
"$TW" compute-envs view -n "$CE" ${WS:+-w "$WS"} 2>/dev/null \
  | awk -F'|' '$1 ~ /^ *(ID|Status)/ {gsub(/^[ \t]+|[ \t]+$/,"",$1); gsub(/^[ \t]+|[ \t]+$/,"",$2); print $1": "$2}'
