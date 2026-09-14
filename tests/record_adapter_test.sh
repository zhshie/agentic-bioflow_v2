#!/bin/bash
# scripts/record_adapter.sh - the record adapter's only shipped implementation
# (docs/RECORD_ADAPTER.md). `none` must do nothing and keep no state
# (PRINCIPLES.md, invariant 2), and an unimplemented adapter value must refuse
# rather than silently behave like `none`.
#
# Mirrors tests/preflight_reach_test.sh's shape: a settings file in a temp
# dir, LAB_SETTINGS_FILE pointed at it, has()/hasnot() over captured output.
set -uo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/record_adapter.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }

run() { LAB_SETTINGS_FILE="$TMP/env.yaml" bash "$R" "$@" 2>&1; }
rc()  { LAB_SETTINGS_FILE="$TMP/env.yaml" bash "$R" "$@" >/dev/null 2>&1; echo $?; }

has()    { printf '%-58s ' "$1"; grep -qE "$2" <<<"$3" && echo ok || { echo "FAIL: no line matching /$2/ in: $3"; fails=$((fails+1)); }; }
hasnot() { printf '%-58s ' "$1"; grep -qE "$2" <<<"$3" && { echo "FAIL: unexpected /$2/ in: $3"; fails=$((fails+1)); } || echo ok; }
eq()     { printf '%-58s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }

# --- adapter none, the default with no settings file at all ------------------
rm -f "$TMP/env.yaml"

out=$(run resolve sample-42)
has "resolve with no settings file defaults to none" '^record=none$' "$out"
eq  "resolve exits 0"                                 "$(rc resolve sample-42)" "0"

out=$(run attach sample-42 /work/u9613010/runs/x/results/report.html)
has "attach prints where the artefact stays"          '^kept=/work/u9613010/runs/x/results/report\.html$' "$out"
eq  "attach exits 0"                                   "$(rc attach sample-42 /some/path)" "0"

out=$(run lookup-by-checksum abc123)
has "lookup-by-checksum answers found=no"              '^found=no$' "$out"
eq  "lookup-by-checksum exits 0"                        "$(rc lookup-by-checksum abc123)" "0"

# --- adapter none explicitly set in settings ----------------------------------
settings 'record_adapter: none'
eq "explicit none: resolve still record=none" "$(run resolve x)" "record=none"

# --- attach does not touch the filesystem: no file at that path is created ---
DEST="$TMP/would-not-exist/artefact.txt"
run attach ref-1 "$DEST" >/dev/null
eq "attach creates nothing at the given path" "$([ -e "$DEST" ] && echo exists || echo absent)" "absent"

# --- an unimplemented adapter value refuses, rather than acting like none ----
settings 'record_adapter: elabftw'
out=$(run resolve sample-42)
has "unimplemented adapter names itself"        'adapter elabftw is not implemented' "$out"
eq  "unimplemented adapter exits 2"              "$(rc resolve sample-42)" "2"
hasnot "unimplemented adapter never says record=none" '^record=none$' "$out"

# --- RECORD_ADAPTER env var, used when settings.sh cannot be reached ---------
rm -f "$TMP/env.yaml"
out=$(LAB_SETTINGS_FILE="$TMP/does-not-exist/env.yaml" RECORD_ADAPTER=none bash "$R" resolve x 2>&1)
has "RECORD_ADAPTER env var is honoured" '^record=none$' "$out"

out=$(LAB_SETTINGS_FILE="$TMP/does-not-exist/env.yaml" RECORD_ADAPTER=elabftw bash "$R" resolve x 2>&1)
has "RECORD_ADAPTER env var also gates unimplemented adapters" 'adapter elabftw is not implemented' "$out"

# --- bad usage: exit 2, not a crash, and no adapter dispatch happens ---------
settings 'record_adapter: none'
eq "no subcommand at all"                "$(rc)" "2"
eq "unknown subcommand"                  "$(rc frobnicate x)" "2"
eq "resolve with no ref"                 "$(rc resolve)" "2"
eq "attach with no path"                 "$(rc attach sample-42)" "2"
eq "attach with no ref at all"           "$(rc attach)" "2"
eq "lookup-by-checksum with no sum"      "$(rc lookup-by-checksum)" "2"

# --- no network: nothing here may shell out to curl/wget/ssh -----------------
NET=$(grep -nE '\b(curl|wget|ssh|scp|nc[[:space:]])\b' "$R" | grep -v '^[0-9]*:#')
printf '%-58s ' "no network call anywhere in the script"
[ -z "$NET" ] && echo ok || { echo "FAIL: $NET"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
