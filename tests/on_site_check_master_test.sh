#!/bin/bash
# Tests for scripts/on_site.sh --check-master (mcp-site-connection-status): a read-only look at the shared connection.
# It asks the control channel (ssh -O check) and nothing else: no session, no slot, no login, no waiting.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/on_site.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
. "$(dirname "${BASH_SOURCE[0]}")/lib/nowsl_path.sh"
PATH=$(nowsl_path "$TMP") || { echo "cannot build a PATH without wsl.exe"; exit 1; }
fails=0
SLOTS="$TMP/slots"

settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }
# a fake ssh that logs every argument line and answers -O check with $1
mkfake() {
  printf '#!/bin/bash\necho "$*" >> "%s/ssh.log"\ncase "$*" in *"-O check"*) exit %s ;; esac\nexit 0\n' "$TMP" "$1" > "$TMP/fake-ssh"
  chmod +x "$TMP/fake-ssh"; : > "$TMP/ssh.log"
}
run() { LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" ON_SITE_SLOT_DIR="$SLOTS" bash "$S" --check-master 2>&1; }
check() { # check <label> <condition-status>
  printf '%-60s ' "$1"
  if [ "$2" = 0 ]; then echo ok; else echo FAIL; fails=$((fails+1)); fi
}

settings 'reach: ssh' 'site_host: me@example.org'

# TC-026, TC-028: the channel is there -> 0, and only -O check was asked
mkfake 0; out=$(run); rc=$?
check "ssh, master up: exit 0" "$([ "$rc" = 0 ]; echo $?)"
check "ssh, master up: only -O check, no true session" "$(! grep -qw true "$TMP/ssh.log" && grep -q -- '-O check' "$TMP/ssh.log"; echo $?)"
check "ssh, master up: exactly one ssh call" "$([ "$(wc -l < "$TMP/ssh.log")" = 1 ]; echo $?)"

# TC-027, TC-057: no channel -> 1 at once, no login attempt, no instructions that wait
mkfake 255; out=$(run); rc=$?
check "ssh, no master: exit 1" "$([ "$rc" = 1 ]; echo $?)"
check "ssh, no master: only -O check, no true session" "$(! grep -qw true "$TMP/ssh.log" && [ "$(wc -l < "$TMP/ssh.log")" = 1 ]; echo $?)"
check "ssh, no master: nothing opened (no ControlMaster=yes)" "$(! grep -q 'ControlMaster=yes' "$TMP/ssh.log"; echo $?)"

# TC-029: no slot taken (the slot directory is not even made)
check "no slot is taken" "$([ -z "$(ls -A "$SLOTS" 2>/dev/null)" ]; echo $?)"

# TC-030: reach local -> 0 and the fake ssh is never called
settings 'reach: local'
mkfake 255; out=$(run); rc=$?
check "local: exit 0" "$([ "$rc" = 0 ]; echo $?)"
check "local: ssh never called" "$([ ! -s "$TMP/ssh.log" ]; echo $?)"

# reach none -> nothing to check, but never "open": exit 1
settings 'reach: none'
mkfake 0; out=$(run); rc=$?
check "none: exit 1 and ssh never called" "$([ "$rc" = 1 ] && [ ! -s "$TMP/ssh.log" ]; echo $?)"

[ "$fails" = 0 ] && echo "all ok" || { echo "$fails failed"; exit 1; }
