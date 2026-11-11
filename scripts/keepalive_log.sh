#!/bin/bash
# Nothing existing: no program recorded how long the shared site connection lives; this loop only records it (mcp-site-keepalive-disconnect-ux).
#
# Run it by hand in the same WSL terminal that opened the connection:
#     nohup bash scripts/keepalive_log.sh >/dev/null 2>&1 &
# Every ABF_KEEPALIVE_INTERVAL seconds (default 600) it asks `on_site.sh --check-master` (the control channel only: no session, no slot,
# no login, no wait) and appends one line to ABF_KEEPALIVE_LOG (default $HOME/.abf/keepalive.log):
#     ts=<ISO8601 with zone> machine=<hostname> master=open|closed|unknown rc=<exit code>
# When the connection is seen going from open to closed it adds
#     ts=... machine=... event=closed lasted_min=<minutes since first seen open> last_open=<ISO8601>
# and when it is seen open again after that: `event=reopened`. Read `lasted_min` as the measured lifetime, to within one interval.
# It never opens a connection, never asks for or writes a one-time code or any credential, and changes nothing but its own log.
# `kill` stops it. Nothing starts it for you. ABF_KEEPALIVE_ONCE=1 runs one round and does not sleep (tests);
# ABF_KEEPALIVE_ROUNDS=<n> runs n rounds (tests); ABF_KEEPALIVE_ON_SITE names another on_site.sh (tests).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ON_SITE="${ABF_KEEPALIVE_ON_SITE:-$HERE/on_site.sh}"
INTERVAL="${ABF_KEEPALIVE_INTERVAL:-600}"
LOG="${ABF_KEEPALIVE_LOG:-$HOME/.abf/keepalive.log}"
MAX_BYTES=1048576
ROUNDS="${ABF_KEEPALIVE_ROUNDS:-0}"
[ "${ABF_KEEPALIVE_ONCE:-0}" = 1 ] && ROUNDS=1
MACHINE="$(hostname)"

mkdir -p "$(dirname "$LOG")"

stamp() { date -Iseconds; }
epoch() { date +%s; }
put() { # put <fields...>: rotate first when the log is over 1 MB, keeping one old file
  if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt "$MAX_BYTES" ]; then mv -f "$LOG" "$LOG.1"; fi
  printf '%s\n' "ts=$(stamp) machine=$MACHINE $*" >> "$LOG"
}

state=""            # open | closed | "" (nothing seen yet)
open_since=0; open_iso=""
done_rounds=0
while :; do
  bash "$ON_SITE" --check-master >/dev/null 2>&1
  rc=$?
  case "$rc" in 0) now=open ;; 124) now=unknown ;; *) now=closed ;; esac
  put "master=$now rc=$rc"
  if [ "$now" = open ] && [ "$state" != open ]; then
    [ "$state" = closed ] && put "event=reopened"
    open_since="$(epoch)"; open_iso="$(stamp)"; state=open
  elif [ "$now" = closed ] && [ "$state" = open ]; then
    put "event=closed lasted_min=$(( ($(epoch) - open_since) / 60 )) last_open=$open_iso"
    state=closed
  elif [ "$now" = closed ] && [ -z "$state" ]; then
    state=closed
  fi
  done_rounds=$((done_rounds + 1))
  [ "$ROUNDS" -gt 0 ] && [ "$done_rounds" -ge "$ROUNDS" ] && break
  sleep "$INTERVAL"
done
