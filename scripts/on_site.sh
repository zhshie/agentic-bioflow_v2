#!/bin/bash
# The only sanctioned way to run something on the site.
#
# A site is reached in one of three ways, and which one is a property of the
# site, not of this deployment - see docs/SITE_ADAPTER.md, contract 6:
#
#   none    a Platform-managed compute environment. There is no login node and
#           nothing to reach; asking to run something on it is a caller's bug
#   local   this deployment already runs on the site
#   ssh     this deployment runs on the user's own machine
#
# Writing it as a contract is what keeps the cloud case free. An "ssh layer"
# spread through the scripts would have to be torn out the day a site needs no
# transport at all.
#
#   on_site.sh <command...>              run a command
#   on_site.sh --script <path> [args]    run one of this plugin's own scripts
#   on_site.sh --check-reach             can the site be reached right now?
#
#   ON_SITE_DRY_RUN=1   print where a command would run and what it would be,
#                       and run nothing. This is the seam the tests use, so
#                       they need no ssh host, no network and no site.
#   ON_SITE_SSH_BIN     override the ssh binary (tests)
#   ON_SITE_TIMEOUT     seconds before a call is treated as hung (default 120,
#                       15 for --check-reach). 0 disables the clock, which is
#                       what a long install on the site needs.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
. "$HERE/settings.sh"

SSH="${ON_SITE_SSH_BIN:-ssh}"
REACH="$(setting reach local)"
HOST="$(setting site_host)"
CP="$(setting ssh_control_path "$HOME/.ssh/cm-%r-%h-%p")"
TMO="${ON_SITE_TIMEOUT:-120}"
CHECK_TMO="${ON_SITE_TIMEOUT:-15}"

die() { local rc="$1"; shift; printf '%s\n' "$@" >&2; exit "$rc"; }

MODE=command SCRIPT=""
case "${1:-}" in
  --check-reach) MODE=check;  shift ;;
  --script)      MODE=script; SCRIPT="${2:?--script needs a path}"; shift 2 ;;
esac

case "$REACH" in
  local|ssh) ;;
  none)
    [ "$MODE" = check ] && exit 0   # nothing to reach is a normal answer
    die 2 "reach is 'none': this site has nothing to reach." \
          "A Platform-managed compute environment has no login node, so a" \
          "caller asking to run '$*' on it is asking the wrong question." ;;
  *)
    die 2 "unknown reach value '$REACH' in the deployment settings." \
          "It must be one of: none, local, ssh. See docs/SITE_ADAPTER.md." ;;
esac

if [ "$REACH" = ssh ] && [ -z "$HOST" ]; then
  die 2 "reach is 'ssh' but 'site_host' is not set in the deployment settings." \
        "Set it to the user@host you log in to. See docs/SETTINGS.md."
fi

# The master connection carries the one-time code the user typed at login.
# Claude cannot open one - the code is on their phone - so when it is gone the
# only useful thing to do is print the exact line for them to paste. Silently
# falling through would make every later command hang on an invisible prompt.
master_is_up() { "$SSH" -O check -o ControlPath="$CP" "$HOST" >/dev/null 2>&1; }

no_master() {
  die 2 "no ssh master connection to $HOST." \
        "" \
        "Without one, every command asks for a one-time code - which only you" \
        "can supply. Open it yourself:" \
        "" \
        "    ssh -o ControlMaster=auto -o ControlPath=$CP -o ControlPersist=8h $HOST true" \
        "" \
        "ControlPersist detaches the master into the background as soon as it" \
        "has authenticated, so that command returns immediately and the" \
        "terminal is yours again - closing it does not take the connection" \
        "down. One master lasts the whole work session."
}

# A hang is the failure mode here, not an error. This site caps concurrent
# sessions per TCP connection, and the cap is reached by ordinary use - a
# background watch polling every 90s gets there on its own. Past it, a new
# session request waits forever. `ssh -O check` keeps answering throughout,
# because it is a control-plane ping rather than a session, which is what let
# preflight report OK while the next real command sat there. So every call
# carries a clock, and running out of it means this and not "the site is slow".
sessions_exhausted() {
  die 2 "the site did not answer within ${1}s, and did not fail either." \
        "" \
        "A master that still answers a control-plane ping can refuse to" \
        "open another session: this site caps them per connection, and past" \
        "the cap a session request hangs rather than erroring (PITFALLS 16e)." \
        "" \
        "Close the exhausted master, then have the user open a fresh one:" \
        "" \
        "    ssh -O exit -o ControlPath=$CP $HOST" \
        "" \
        "Raise ON_SITE_TIMEOUT, or set it to 0, only for a call that is" \
        "genuinely long - a download onto the site, say."
}

# `timeout` returns 124 when it fires; everything else is the command's own.
clocked() {
  local secs="$1"; shift
  [ "$secs" = 0 ] && { "$@"; return $?; }
  timeout "$secs" "$@"
}

if [ "$MODE" = check ]; then
  [ "$REACH" = local ] && exit 0
  master_is_up || no_master
  # Not enough on its own - see sessions_exhausted. Prove a session opens.
  clocked "$CHECK_TMO" "$SSH" -o ControlPath="$CP" "$HOST" true >/dev/null 2>&1
  rc=$?
  [ "$rc" = 124 ] && sessions_exhausted "$CHECK_TMO"
  exit "$rc"
fi

# What would happen, for the dry-run seam and for the error messages.
where() { [ "$REACH" = local ] && echo local || echo "ssh $HOST"; }
what()  {
  [ "$MODE" = script ] && printf 'script %s %s' "$(basename "$SCRIPT")" "$*" \
                       || printf '%s' "$*"
}

if [ -n "${ON_SITE_DRY_RUN:-}" ]; then
  printf '%s\t%s\n' "$(where)" "$(what "$@")"
  exit 0
fi

[ "$REACH" = ssh ] && { master_is_up || no_master; }

if [ "$MODE" = command ]; then
  [ "$REACH" = local ] && exec bash -c "$*"
  clocked "$TMO" "$SSH" -o ControlPath="$CP" "$HOST" "$*"
  rc=$?
  [ "$rc" = 124 ] && sessions_exhausted "$TMO"
  exit "$rc"
fi

# --- script mode -------------------------------------------------------------
# The script travels; it is never installed on the site. A copy left behind
# drifts from the plugin the moment either is updated, and the drift is silent.
NAME="$(basename "$SCRIPT")"
[ -r "$HERE/$NAME" ] || die 2 "--script takes one of this plugin's own scripts;" \
                              "'$NAME' is not in $HERE."
[ "$REACH" = local ] && exec bash "$HERE/$NAME" "$@"

# Settings stay on this machine. What crosses is the handful of values the site
# scripts already accept as environment overrides - which is why none of them
# needs the settings file on the far end.
envs=""
carry() { [ -n "$2" ] && envs+="$1=$(printf '%q' "$2") "; return 0; }
carry LAB_RUNS_DIR        "$(setting storage_root)"
carry NF_RELAY_PORT       "$(setting relay_port)"
carry TW_AGENT_JAVA       "$(setting agent_java)"
carry TW_AGENT_JAR        "$(setting agent_jar)"
carry TW_AGENT_CONNECTION "$(setting agent_connection)"
carry TOWER_WORKSPACE_ID  "$(setting workspace_id)"
# TW_BIN is deliberately not carried: 'tw_bin' in the local settings file names
# where tw lives on THIS machine, and a site script (agent_ctl.sh register, in
# particular) needs the site's own tw. Carrying it made a laptop path win over
# the remote script's own `command -v tw` fallback, so registration failed
# naming a path that only exists on the laptop.

args=""; for a in "$@"; do args+="$(printf '%q' "$a") "; done

# What travels: settings.sh, because the site scripts source it, configs/,
# because check_resource_contract.sh reads the site config it is checking, and
# any sibling file the named script execs by path rather than sourcing (only
# egress_ctl.sh has one today: it execs nf_relay.py, which a "ship just the
# named script" rule silently drops - the relay then fails to bind, and the
# error names a /tmp path instead of the real cause). About 30 KB, so one
# round trip carries the lot at the measured 131 ms rather than three times
# that.
extra=""
[ "$NAME" = egress_ctl.sh ] && extra="scripts/nf_relay.py"
tar -c -C "$ROOT" scripts/settings.sh scripts/require_python.sh "scripts/$NAME" $extra configs \
  | clocked "$TMO" "$SSH" -o ControlPath="$CP" "$HOST" \
      "d=\$(mktemp -d) && tar -x -C \"\$d\" && cd \"\$d\" && $envs bash scripts/$NAME $args; rc=\$?; cd /; \\rm -rf -- \"\$d\"; exit \$rc"
rc=$?
[ "$rc" = 124 ] && sessions_exhausted "$TMO"
exit "$rc"
