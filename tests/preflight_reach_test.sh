#!/bin/bash
# preflight.sh has to give a different, honest answer for each kind of site.
# Two of its answers are the ones that matter and neither can be produced by
# running it here:
#
#   reach=none  a Platform-managed compute environment. There is no relay, no
#               outputs reader and no scheduler to ask. Reporting those as FAIL
#               would make a perfectly healthy cloud site look broken.
#   reach=ssh   the master connection has died. Every later command would hang
#               on a one-time code prompt that Claude cannot answer, so this has
#               to fail loudly and print the line the user pastes.
#
# The seam is preflight's own line output: `OK|FAIL|SKIP <name> <detail>`.
P="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/preflight.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

: > "$TMP/token"; chmod 600 "$TMP/token"
printf 'stub-token\n' > "$TMP/token"
printf '#!/bin/bash\nexit 0\n' > "$TMP/tw"; chmod +x "$TMP/tw"

settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }
mkssh()    { printf '#!/bin/bash\nexit %s\n' "$1" > "$TMP/ssh"; chmod +x "$TMP/ssh"; }

run() {
  LAB_SETTINGS_FILE="$TMP/env.yaml" SEQERA_TOKEN_FILE="$TMP/token" \
  ON_SITE_SSH_BIN="$TMP/ssh" TW_BIN="$TMP/tw" bash "$P" 2>&1
}

has()    { printf '%-58s ' "$1"; grep -qE "$2" <<<"$3" && echo ok || { echo "FAIL: no line matching /$2/"; fails=$((fails+1)); }; }
hasnot() { printf '%-58s ' "$1"; grep -qE "$2" <<<"$3" && { echo "FAIL: unexpected /$2/"; fails=$((fails+1)); } || echo ok; }

# --- a cloud compute environment: nothing to reach ---------------------------
settings 'reach: none' 'storage_root: s3://bucket/runs' 'workspace_id: 1' 'compute_env: ce'
out=$(run)
has    "none: says the site needs no transport"   '^OK +reach .*none'     "$out"
hasnot "none: does not ask about the relay"       '(^| )egress'           "$out"
hasnot "none: does not ask about the reader"      '(^| )agent'           "$out"
hasnot "none: does not ask a scheduler"           '(^| )resources'        "$out"
has    "none: still checks the compute env"       '(^| )compute-env'      "$out"

# --- an ssh site whose master has died ---------------------------------------
settings 'reach: ssh' 'site_host: me@example.org' 'storage_root: /work/runs' 'workspace_id: 1' 'compute_env: ce'
mkssh 255
out=$(run)
has "dead master fails the reach check"           '^FAIL +reach'          "$out"
has "and prints the line the user pastes"         'ControlMaster=auto'    "$out"
has "and names the host"                          'me@example.org'        "$out"
hasnot "and does not go on to ask the site"       '(^| )egress'           "$out"
printf '%-58s ' "dead master exits non-zero"; run >/dev/null 2>&1 && { echo "FAIL: exit 0"; fails=$((fails+1)); } || echo ok

# --- an ssh site that is reachable -------------------------------------------
mkssh 0
out=$(run)
has "a live master passes the reach check"        '^OK +reach'            "$out"
has "and the site checks then run"                '(^| )egress'           "$out"
has "including the scheduler"                     '(^| )resources'        "$out"

# --- the site this deployment already runs on --------------------------------
settings 'reach: local' 'storage_root: /work/runs' 'workspace_id: 1' 'compute_env: ce'
mkssh 255
out=$(run)
has "local needs no master connection"            '^OK +reach .*local'    "$out"
has "and still asks the site directly"            '(^| )egress'           "$out"

# --- the run area, named for where it actually lives -------------------------
settings 'reach: ssh' 'site_host: me@example.org' 'workspace_id: 1'
mkssh 0
out=$(run)
has "no storage_root names the settings key"      'FAIL +run-area.*storage_root' "$out"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
