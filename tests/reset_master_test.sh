#!/bin/bash
# PITFALLS 16e: too many on_site.sh calls on one master hang the next session
# open silently. reset_master.sh is the one-command fix - close the exhausted
# master, print the exact reconnect line. This checks it reads settings the
# same way on_site.sh does and behaves per reach value.
P="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/reset_master.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }

run() { LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/ssh" bash "$P" "$@" 2>&1; }
t() { # t <label> <expect-rc> <expect-substring>
  local label="$1" want_rc="$2" want="$3"
  printf '%-58s ' "$label"
  local out rc; out=$(run); rc=$?
  if [ "$rc" != "$want_rc" ]; then echo "FAIL: rc $rc wanted $want_rc <<$out>>"; fails=$((fails+1)); return; fi
  if [ -n "$want" ] && ! grep -qF -- "$want" <<<"$out"; then echo "FAIL: lacks '$want' <<$out>>"; fails=$((fails+1)); return; fi
  echo ok
}

settings 'reach: local'
t "local says there is nothing to reset"     0 "no ssh master to reset"

settings 'reach: none'
t "none says there is nothing to reach"      0 "nothing to reach"

settings 'reach: ssh'
t "ssh with no site_host is refused"         2 "site_host"

printf '#!/bin/bash\nexit 0\n' > "$TMP/ssh"; chmod +x "$TMP/ssh"
settings 'reach: ssh' 'site_host: me@example.org'
t "ssh closes the master and prints the reconnect line" 0 "ControlPersist=8h me@example.org"

printf '#!/bin/bash\nexit 1\n' > "$TMP/ssh"; chmod +x "$TMP/ssh"
t "a failed -O exit is reported, not swallowed"          0 "nothing to close"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
