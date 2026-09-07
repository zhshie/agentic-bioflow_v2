#!/bin/bash
# Recover from PITFALLS.md 16e: too many on_site.sh calls on one master hit
# this site's sshd session cap (MaxSessions, default 10) and the next session
# request hangs - no error, no timeout of its own. `ssh -O check` still
# succeeds throughout (it is a control-plane ping, not a session), which is
# what makes the hang confusing rather than obviously broken.
#
# The fix is not to open a session and wait longer; it is to close the
# exhausted master so the user can open a fresh one. This script is that one
# command, in place of hand-reconstructing the ControlPath and host each time.
#
#   reset_master.sh
#
#   ON_SITE_SSH_BIN   override the ssh binary (tests)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

SSH="${ON_SITE_SSH_BIN:-ssh}"
REACH="$(setting reach local)"
HOST="$(setting site_host)"
CP="$(setting ssh_control_path "$HOME/.ssh/cm-%r-%h-%p")"

die() { local rc="$1"; shift; printf '%s\n' "$@" >&2; exit "$rc"; }

case "$REACH" in
  local) echo "reach is 'local' - there is no ssh master to reset."; exit 0 ;;
  none)  echo "reach is 'none' - this site has nothing to reach over ssh."; exit 0 ;;
  ssh)   [ -n "$HOST" ] || die 2 "reach is 'ssh' but 'site_host' is not set - see docs/SETTINGS.md." ;;
  *)     die 2 "unknown reach value '$REACH' - must be none, local or ssh." ;;
esac

"$SSH" -O exit -o ControlPath="$CP" "$HOST" 2>&1
rc=$?

# `-O exit` fails when there was nothing to close - not this script's problem
# to solve, just something to say plainly rather than reporting a bare
# nonzero exit as if the reset itself went wrong.
[ "$rc" != 0 ] && echo "(no master was open - nothing to close)"

cat <<EOF

Open a fresh one:

    ssh -o ControlMaster=auto -o ControlPath=$CP -o ControlPersist=8h $HOST true

ControlPersist detaches the master into the background as soon as it has
authenticated, so that command returns immediately and the terminal is yours
again - closing it does not take the connection down. One master lasts the
whole work session, until PITFALLS 16e's session cap is hit again.
EOF
