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


# =============================================================================
# #45 what the relay will accept as "a specific domain" and what it will connect to
# =============================================================================
PS="NF_RELAY_EXTRA_DOMAINS=co.uk,github.io,nip.io,127.0.0.1.nip.io,localhost.localdomain,printer.local,10.0.0.5.example.com,bbc.co.uk,user.github.io,ok.example.org"
t "#45 a public suffix grants nothing (co.uk)"           "$(ok_for foo.co.uk "$PS")" "False"
t "#45 ...nor github.io itself"                          "$(ok_for github.io "$PS")" "False"
t "#45 a wildcard-DNS service grants nothing (nip.io)"   "$(ok_for 127.0.0.1.nip.io "$PS")" "False"
t "#45 ...nor anything under it"                         "$(ok_for evil.nip.io "$PS")" "False"
t "#45 localhost.localdomain grants nothing"             "$(ok_for localhost.localdomain "$PS")" "False"
t "#45 a .local name grants nothing"                     "$(ok_for printer.local "$PS")" "False"
t "#45 a name with an IP in its labels grants nothing"   "$(ok_for 10.0.0.5.example.com "$PS")" "False"
t "#45 control: a registrable domain under co.uk loads"  "$(ok_for bbc.co.uk "$PS")" "True"
t "#45 control: a user site under github.io loads"       "$(ok_for user.github.io "$PS")" "True"
t "#45 control: an ordinary one still loads"             "$(ok_for ok.example.org "$PS")" "True"
has "#45 a dropped suffix is named at startup"           "dropped 'co.uk'" "$(startup "$PS")"
has "#45 a dropped wildcard-DNS name is named"           "dropped '127.0.0.1.nip.io'" "$(startup "$PS")"
# U+212A (Kelvin sign) lowercases to an ASCII k in Python but not in bash: the two
# validators disagreed. Anything that is not ASCII is dropped now.
KEL="NF_RELAY_EXTRA_DOMAINS=$(printf '\xe2\x84\xaa')ev.example.org"
t "#45 a name with a Kelvin sign grants nothing"         "$(ok_for kev.example.org "$KEL")" "False"
has "#45 ...and is named as dropped"                     "dropped" "$(startup "$KEL")"
# a name over 253 characters
LN="$(for i in 1 2 3 4 5; do printf '%s.' "$(printf 'a%.0s' $(seq 1 55))"; done)org"
t "#45 control: a name over 253 characters is dropped"   "$(ok_for "$LN" "NF_RELAY_EXTRA_DOMAINS=$LN")" "False"
# the startup lines cannot be forged or coloured through the environment
FORGE=$'x.org,bad\nFAKE-LOG-LINE planted'
out="$(startup "NF_RELAY_EXTRA_DOMAINS=$FORGE")"
t "#45 a newline in the list cannot start a log line"    "$(grep -c '^FAKE-LOG-LINE' <<<"$out")" "0"
has "#45 ...the dropped entry is still named"            "dropped" "$out"
out="$(startup "NF_RELAY_EXTRA_NOTE=oops $(printf '\033')[31mred")"
t "#45 an escape character in the note does not reach the log" "$(printf '%s' "$out" | LC_ALL=C grep -c "$(printf '\033')")" "0"
has "#45 ...the rest of the note does"                   "oops" "$out"

# connect_upstream refuses an extra domain that resolves to a non-public address
# (the relay checked neither the resolved address nor the port), and still
# connects for a built-in name and for a public address.
conn() { # conn <host> <resolved-ip> [env...] -> "<connected|refused>"
    local host="$1" ip="$2"; shift 2
    env "NF_RELAY_EXTRA_DOMAINS=lab.example.org,ok.example.org" "$@" bash -c '"$0" - "$1" "$2" "$3" <<'"'"'PY'"'"'
import importlib.util, sys, socket
path, host, ip = sys.argv[1], sys.argv[2], sys.argv[3]; sys.argv = sys.argv[:1]
spec = importlib.util.spec_from_file_location("relay", path)
relay = importlib.util.module_from_spec(spec); spec.loader.exec_module(relay)
tried = []
class S:
    def __init__(self, *a): pass
    def settimeout(self, t): pass
    def connect(self, addr): tried.append(addr)
    def close(self): pass
fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
relay.resolve = lambda h, p: [(fam, socket.SOCK_STREAM, 6, "", (ip, p))]
relay.socket.socket = S
relay.time.sleep = lambda s: None
up, err = relay.connect_upstream(host, 443)
print("connected" if up is not None else "refused")
PY' "$PY" "$RELAY" "$host" "$ip" | tail -n 1   # the relay's own DENY-PRIVATE log line comes first
}
t "#45 an extra domain resolving to 127.0.0.1 is refused"        "$(conn lab.example.org 127.0.0.1)" "refused"
t "#45 ...to 10.1.2.3"                                           "$(conn lab.example.org 10.1.2.3)" "refused"
t "#45 ...to 172.16.4.5"                                         "$(conn lab.example.org 172.16.4.5)" "refused"
t "#45 ...to 192.168.0.9"                                        "$(conn lab.example.org 192.168.0.9)" "refused"
t "#45 ...to the metadata address 169.254.169.254"               "$(conn lab.example.org 169.254.169.254)" "refused"
t "#45 ...to ::1"                                                "$(conn lab.example.org ::1)" "refused"
t "#45 ...to fe80::1"                                            "$(conn lab.example.org fe80::1)" "refused"
t "#45 ...to 0.0.0.0"                                            "$(conn lab.example.org 0.0.0.0)" "refused"
t "#45 control: an extra domain resolving to a public address"   "$(conn lab.example.org 93.184.216.34)" "connected"
t "#45 control: a built-in domain is not subject to the check"   "$(conn quay.io 10.1.2.3)" "connected"
echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
