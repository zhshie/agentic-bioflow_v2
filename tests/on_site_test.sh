#!/bin/bash
# Tests for scripts/on_site.sh, the only sanctioned way to run something on the
# site. It has to be right for three site kinds at once, and two of them - a
# cloud compute environment with nothing to reach, and an ssh site whose master
# connection has died - are states no amount of local testing would produce by
# accident.
#
# Everything below runs through ON_SITE_DRY_RUN=1, which prints where a command
# would run and what it would be, without running it. That is the whole point of
# the seam: these tests need no ssh host, no network, and no site.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/on_site.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }

t() { # t <label> <expect-rc> <expect-substring> -- <args...>
  local label="$1" want_rc="$2" want="$3"; shift 4
  printf '%-56s ' "$label"
  local out rc
  out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_DRY_RUN=1 \
        ON_SITE_SSH_BIN="$TMP/fake-ssh" bash "$S" "$@" 2>&1); rc=$?
  if [ "$rc" != "$want_rc" ]; then
    echo "FAIL: rc $rc, wanted $want_rc  <<$out>>"; fails=$((fails+1)); return
  fi
  if [ -n "$want" ] && ! grep -qF "$want" <<<"$out"; then
    echo "FAIL: output lacks '$want'  <<$out>>"; fails=$((fails+1)); return
  fi
  echo "ok"
}

# A stub ssh whose exit status the tests control, so "is the master up" is a
# state we can set rather than one we have to arrange for real.
mkfake() { printf '#!/bin/bash\nexit %s\n' "$1" > "$TMP/fake-ssh"; chmod +x "$TMP/fake-ssh"; }
mkfake 0

settings 'reach: local'
t "local: says where and what"            0 "local	true"            -- true
t "local: joins its arguments"            0 "local	echo hi there"    -- echo hi there

settings 'reach: ssh' 'site_host: me@example.org'
t "ssh: names the host"                   0 "ssh me@example.org	true" -- true
t "ssh: script mode ships settings.sh"    0 "script egress_ctl.sh"   -- --script scripts/egress_ctl.sh status

# A cloud compute environment has no login node. "Nothing to reach" is a normal
# answer for the site, but a caller that asked anyway has a bug, so say so
# rather than silently running the command on the wrong machine.
settings 'reach: none'
t "none: refuses rather than running here" 2 "nothing to reach"      -- true

settings 'reach: ssh'
t "ssh without site_host names the key"    2 "site_host"             -- true

settings 'reach: banana' 'site_host: me@example.org'
t "an unknown reach value is an error"     2 "banana"                -- true

settings 'workspace_id: 1'
t "no reach key defaults to local"         0 "local	true"            -- true

# The master connection carries the one-time code the user typed. Claude cannot
# open it - the code is on their phone - so the only useful thing to do when it
# is gone is print the exact line for them to paste.
settings 'reach: ssh' 'site_host: me@example.org'
mkfake 0
t "check-reach passes when the master is up" 0 ""                    -- --check-reach
mkfake 255
t "check-reach fails when it is gone"      2 "ControlMaster=auto"    -- --check-reach
t "and names the host to paste it against" 2 "me@example.org"        -- --check-reach

# reach=local must never consult ssh at all: a site the deployment already runs
# on has no master connection, and demanding one would break the site that works
# today.
settings 'reach: local'
mkfake 255
t "local ignores the ssh master entirely"  0 "local	true"            -- true

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
