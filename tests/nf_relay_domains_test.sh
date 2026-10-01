#!/bin/bash
# Stage S2 (specs/002-relay-allowlist tasks.md T005, T006): scripts/nf_relay.py
# reads this deployment's own extra domains from NF_RELAY_EXTRA_DOMAINS and
# says out loud, at startup, what it loaded and what it did not.
#
# Nothing existing: there was no unit test of the relay at all (plan.md) - its
# matching was only ever exercised on the real login node. This imports the
# module with the environment set, the way scripts/check_egress.py already
# imports it, and starts no server and opens no socket.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
RELAY="$ROOT/scripts/nf_relay.py"
. "$ROOT/scripts/utils/portable.sh" || { echo "cannot read scripts/utils/portable.sh"; exit 1; }

PY="$(command -v python3 || true)"
[ -n "$PY" ] || { echo "SKIP: no python3 here"; exit 0; }

fails=0
t()   { printf '%-72s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has() { printf '%-72s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: nothing matching '$2' in: $3"; fails=$((fails+1)); }; }
lacks() { printf '%-72s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: '$2' should not be in: $3"; fails=$((fails+1)); } || echo ok; }

# relay <python-expression-lines...> -> stdout of a tiny program that imports
# nf_relay.py (argv emptied: it reads its port from argv at import time) and
# then runs the given lines. The environment is whatever the caller sets.
relay() {
    "$PY" - "$RELAY" "$@" <<'PY'
import importlib.util, sys
path, lines = sys.argv[1], sys.argv[2:]
sys.argv = sys.argv[:1]
spec = importlib.util.spec_from_file_location("relay", path)
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)
for line in lines:
    exec(line)
PY
}

# startup <env assignments...> -> the startup lines the relay would log.
startup() { env "$@" bash -c '"$0" - "$1" <<'"'"'PY'"'"'
import importlib.util, sys
path = sys.argv[1]; sys.argv = sys.argv[:1]
spec = importlib.util.spec_from_file_location("relay", path)
relay = importlib.util.module_from_spec(spec); spec.loader.exec_module(relay)
print("\n".join(relay.startup_lines()))
PY' "$PY" "$RELAY"; }

ok_for() {  # ok_for <host> [env...] -> True/False
    local host="$1"; shift
    env "$@" bash -c '"$0" - "$1" "$2" <<'"'"'PY'"'"'
import importlib.util, sys
path, host = sys.argv[1], sys.argv[2]; sys.argv = sys.argv[:1]
spec = importlib.util.spec_from_file_location("relay", path)
relay = importlib.util.module_from_spec(spec); spec.loader.exec_module(relay)
print(relay.domain_ok(host))
PY' "$PY" "$RELAY" "$host"
}

# =============================================================================
# T005 [TC-002, TC-003] an extra domain passes, an unlisted one does not
# =============================================================================
E="NF_RELAY_EXTRA_DOMAINS=download.example.org,data.lab.test"

t "TC-002 an extra domain passes"               "$(ok_for download.example.org "$E")" "True"
t "TC-002 a subdomain of an extra domain passes" "$(ok_for a.b.download.example.org "$E")" "True"
t "TC-002 matching ignores case and a trailing dot" "$(ok_for DOWNLOAD.Example.ORG. "$E")" "True"
t "TC-003 a domain on neither list is refused"  "$(ok_for elsewhere.example.net "$E")" "False"
t "TC-003 a sibling of an extra domain is refused" "$(ok_for upload.example.org "$E")" "False"
t "TC-003 a label-boundary lookalike is refused" "$(ok_for evildownload.example.org "$E")" "False"
t "TC-003 the parent of an extra domain is refused" "$(ok_for example.org "$E")" "False"
t "built-in domains still pass with an extra list set" "$(ok_for quay.io "$E")" "True"
t "built-in domains pass with no extra list at all"    "$(ok_for quay.io)" "True"
t "with no extra list, an extra domain is refused"     "$(ok_for download.example.org)" "False"

# The relay validates what it is given rather than trusting the carrier:
# NF_RELAY_EXTRA_DOMAINS is an environment variable, and anything that sets
# one can set it to anything. A wildcard or a bare TLD here would open the
# relay to everything below it.
BAD="NF_RELAY_EXTRA_DOMAINS=com,*,10.1.2.3,ok.example.org,a..b"
t "an invalid entry (bare TLD) grants nothing"   "$(ok_for anything.com "$BAD")" "False"
t "an invalid entry (wildcard) grants nothing"   "$(ok_for anything.example.net "$BAD")" "False"
t "an invalid entry (IP) grants nothing"         "$(ok_for 10.1.2.3 "$BAD")" "False"
t "the valid entry beside them still loads"      "$(ok_for ok.example.org "$BAD")" "True"

# =============================================================================
# T005 [TC-004, TC-008, TC-009, TC-023] the startup lines
# =============================================================================
out="$(startup "$E")"
has "TC-004 startup names the built-in group"        "domains (built in): " "$out"
has "TC-004 the built-in group lists a built-in"     "quay.io" "$(grep -F 'domains (built in)' <<<"$out")"
has "TC-004 startup names this deployment's group"   "domains (this deployment): download.example.org,data.lab.test" "$out"
lacks "TC-004 an extra is not listed as built in"    "download.example.org" "$(grep -F 'domains (built in)' <<<"$out")"

out="$(startup "$BAD")"
has "an invalid entry is named at startup"           "dropped 'com'" "$out"
has "every invalid entry is named"                   "dropped '10.1.2.3'" "$out"
has "the valid one is still listed"                  "domains (this deployment): ok.example.org" "$out"

NOTE="NF_RELAY_EXTRA_NOTE=/home/me/config/egress_allow.tsv exists but cannot be read"
out="$(startup "$NOTE")"
has "TC-008/009 with a note and no list: says the list was not loaded" \
    "this deployment's list not loaded: /home/me/config/egress_allow.tsv exists but cannot be read" "$out"
has "TC-008/009 and still starts with the built-in list" "domains (built in): " "$out"

out="$(startup "$E" "NF_RELAY_EXTRA_NOTE=skipping 'x y' - not a valid domain")"
has "TC-023 a partial load says so, with the reason" \
    "this deployment's list only partly loaded: skipping 'x y' - not a valid domain" "$out"
has "TC-023 and lists what did load"                 "domains (this deployment): download.example.org" "$out"

out="$(startup)"
has "no list and no note: says this deployment adds none" "domains (this deployment): (none)" "$out"
lacks "no list and no note: no 'not loaded' alarm"   "not loaded" "$out"

# More than 100 on the carrier is not a state egress_allow.sh can produce, but
# the relay must not trust that: the excess is dropped and named, not loaded.
many="$(for i in $(seq 1 101); do printf 'd%d.example.org,' "$i"; done)"
t "a 101st extra domain is not loaded" "$(ok_for d101.example.org "NF_RELAY_EXTRA_DOMAINS=$many")" "False"
t "the 100th still is"                 "$(ok_for d100.example.org "NF_RELAY_EXTRA_DOMAINS=$many")" "True"
has "the excess is named at startup"   "over the limit of 100" "$(startup "NF_RELAY_EXTRA_DOMAINS=$many")"

# =============================================================================
# T006 [TC-019] the peer restriction is exactly what it was
# =============================================================================
peer() {  # peer <reverse-name> [env...] -> "True <name>" / "False <name>"
    local name="$1"; shift
    env "$@" bash -c '"$0" - "$1" "$2" <<'"'"'PY'"'"'
import importlib.util, sys
path, name = sys.argv[1], sys.argv[2]; sys.argv = sys.argv[:1]
spec = importlib.util.spec_from_file_location("relay", path)
relay = importlib.util.module_from_spec(spec); spec.loader.exec_module(relay)
relay.socket.gethostbyaddr = lambda ip: (name, [], [ip])
ok, n = relay.peer_ok("172.16.0.9")
print(ok, n)
PY' "$PY" "$RELAY" "$name"
}
t "TC-019 the peer prefixes are unchanged" \
  "$(relay 'print(relay.ALLOW_HOST_PREFIXES)')" "('cpn', 'gpn', 'bgm', 'lgn', 'localhost')"
t "TC-019 a compute node may connect"            "$(peer cpn3001.example "$E")" "True cpn3001.example"
t "TC-019 a login node may connect"              "$(peer lgn303.example "$E")" "True lgn303.example"
t "TC-019 another host may not"                  "$(peer laptop.example "$E")" "False laptop.example"
# An extra domain is a destination, never a peer: listing a name must not let
# a host by that name connect.
t "TC-019 an extra domain does not become a peer" \
  "$(peer download.example.org "$E")" "False download.example.org"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
