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
# A member who has none yet gets one built from the site's template. After
# that this always works from the live environment, so that nothing outside
# nextflowConfig and the environment variables can drift by accident.
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
CREATING=0
if "$TW" compute-envs export -n "$CE" ${WS:+-w "$WS"} "$BACKUP" >/dev/null 2>&1; then
    echo "backed up: $BACKUP"
else
    # Nothing to export means nothing exists. Build the first one from the
    # site's template rather than making the member assemble JSON by hand.
    CREATING=1
    TEMPLATE="${SITE_CE_TEMPLATE:-$ROOT/configs/sites/nchc-ce.json.in}"
    [ -r "$TEMPLATE" ] || { echo "no compute environment '$CE', and no template at $TEMPLATE" >&2; exit 1; }
    ACCT_T="$(. "$HERE/settings.sh"; setting slurm_account)"
    [ -n "$ACCT_T" ] || { echo "no compute environment '$CE' yet, and no slurm_account in the settings to build one with." >&2
                          echo "Ask the user for the allocation their compute time is billed to." >&2; exit 1; }
    sed -e "s|@WORKDIR@|${LAB_RUNS_DIR}/_work|g" \
        -e "s|@LAUNCHDIR@|${LAB_RUNS_DIR}/_work|g" \
        -e "s|@ACCOUNT@|${ACCT_T}|g" "$TEMPLATE" > "$BACKUP"
    echo "no '$CE' in this workspace - building the first one from $(basename "$TEMPLATE")"
fi

# Values the site config reads from the environment rather than hardcoding.
# The allocation code identifies a person's project, and the image cache is
# large enough that pointing two things at two directories quietly stores
# every container twice - both belong in the settings file, and both have to
# reach the run through the compute environment.
. "$HERE/settings.sh"
ACCT="$(setting slurm_account)"
CACHE="$(setting singularity_cache)"

NEW="$STATE_DIR/ce-pending.json"
python3 - "$BACKUP" "$CONFIG" "$NEW" "$HERE" "$ACCT" "$CACHE" <<'PY'
import json, subprocess, sys
backup, config, out, here, acct, cache = sys.argv[1:7]
ce = json.load(open(backup))
ce["nextflowConfig"] = open(config).read()

def upsert(name, value, head=True, compute=True):
    for entry in ce.setdefault("environment", []):
        if entry.get("name") == name:
            entry["value"] = value
            return
    ce["environment"].append(
        {"name": name, "value": value, "head": head, "compute": compute})

# Whatever the egress channel says its address is now. These are UPSERTED, not
# only refreshed: a compute environment being created has an empty environment
# list, so "update what is already there" silently produced one with no route
# out at all - which fails much later, as a container that will not pull.
# The adapter says where each variable has to apply; NXF_OPTS is head-only
# because it configures the head job's JVM and means nothing on a task node.
try:
    env = subprocess.run(["bash", f"{here}/egress_ctl.sh", "env", "--scoped"],
                         capture_output=True, text=True, timeout=15)
    for line in env.stdout.splitlines():
        scope, _, rest = line.partition(" ")
        name, _, value = rest.partition("=")
        if scope in ("both", "head") and name:
            upsert(name, value, head=True, compute=(scope == "both"))
except Exception:
    pass

# Settings-derived values, added when absent rather than only refreshed: a
# compute environment exported before these existed has no entry to update.
for name, value in (("SLURM_ACCOUNT", acct), ("NXF_SINGULARITY_CACHEDIR", cache)):
    if value:
        upsert(name, value)

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
    if [ "$CREATING" = 1 ]; then
        echo "nothing applied. Re-run with --apply to create '$CE'."
    else
        echo "nothing applied. Re-run with --apply to overwrite '$CE'."
        echo "That deletes and recreates it under a NEW ID; repoint Launchpad entries after."
    fi
    exit 0
fi

echo
[ "$CREATING" = 1 ] && echo "creating '$CE' ..." || echo "overwriting '$CE' ..."
"$TW" compute-envs import -n "$CE" ${WS:+-w "$WS"} ${CREDS:+-c "$CREDS"} \
      --overwrite --wait AVAILABLE "$NEW" || exit 1
"$TW" compute-envs view -n "$CE" ${WS:+-w "$WS"} 2>/dev/null \
  | awk -F'|' '$1 ~ /^ *(ID|Status)/ {gsub(/^[ \t]+|[ \t]+$/,"",$1); gsub(/^[ \t]+|[ \t]+$/,"",$2); print $1": "$2}'
