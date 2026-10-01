#!/bin/bash
# specs/002-relay-allowlist, independent acceptance M3: the commands say
# "restart the outbound channel" after adding a domain, but egress_ctl.sh had
# no `restart`, and `start` on a running relay only says "already running" -
# so a newly added domain was silently never loaded.
#
# Nothing existing: no test started the relay before; this one does, for real,
# on 127.0.0.1 and a temporary state directory, and stops it again.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
CTL="$ROOT/scripts/egress_ctl.sh"
command -v python3 >/dev/null 2>&1 || { echo "SKIP: no python3 here"; exit 0; }

TMP=$(mktemp -d)
fails=0
export LAB_SETTINGS_FILE="$TMP/env.yaml" NF_RELAY_STATE_DIR="$TMP/state" LAB_RUNS_DIR="$TMP"
printf 'reach: local\n' > "$LAB_SETTINGS_FILE"
export NF_RELAY_PORT="$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')"
cleanup() { bash "$CTL" stop >/dev/null 2>&1; rm -rf "$TMP"; }
trap cleanup EXIT

t() { printf '%-64s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2' in: $3"; fails=$((fails+1)); }; }

NF_RELAY_EXTRA_DOMAINS=first.example.org bash "$CTL" start >/dev/null 2>&1
t "the relay starts" "$?" "0"
has "it loaded the first list" "domains (this deployment): first.example.org" "$(cat "$TMP/state/relay.log" 2>/dev/null)"

out=$(NF_RELAY_EXTRA_DOMAINS=first.example.org,second.example.org bash "$CTL" restart 2>&1)
t "restart is a command and succeeds" "$?" "0"
has "after restart the new list is loaded" \
    "domains (this deployment): first.example.org,second.example.org" "$(tail -n 5 "$TMP/state/relay.log" 2>/dev/null)"
st=$(bash "$CTL" status 2>&1)
has "and it is running" "running pid=" "$st"

out=$(NF_RELAY_EXTRA_DOMAINS=third.example.org bash "$CTL" start 2>&1)
has "start on a running relay says a list change needs restart" "restart" "$out"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
