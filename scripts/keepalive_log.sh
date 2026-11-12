#!/bin/bash
# Nothing existing: no program recorded how long the shared site connection lives; this only records it (mcp-site-keepalive-disconnect-ux).
#
# One call is one reading, and then it ends. A person calls it by hand in the WSL terminal that opened the connection, or a schedule
# that person already has calls it:
#     bash scripts/keepalive_log.sh
# It asks `on_site.sh --check-master` once (the control channel only: no session, no slot, no login, no wait) and appends one line to
# ABF_KEEPALIVE_LOG (default $HOME/.abf/keepalive.log):
#     ts=<ISO8601 with zone> machine=<hostname> master=open|closed|unknown rc=<exit code>
# What the call before this one saw is read back from that log, nothing is kept in memory. When the log last said open and this
# call sees closed it adds
#     ts=... machine=... event=closed lasted_min=<minutes since the first open after the last closed> last_open=<that ISO8601 time>
# and when the log last said closed and this call sees open: `event=reopened`. Read `lasted_min` as the measured lifetime, to within
# the gap between two calls.
# It never opens a connection, never asks for or writes a one-time code or any credential, and changes nothing but its own log.
# Nothing starts it and nothing stays running after it. ABF_KEEPALIVE_ON_SITE names another on_site.sh (tests).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ON_SITE="${ABF_KEEPALIVE_ON_SITE:-$HERE/on_site.sh}"
LOG="${ABF_KEEPALIVE_LOG:-$HOME/.abf/keepalive.log}"
MAX_BYTES=1048576
MACHINE="$(hostname)"

mkdir -p "$(dirname "$LOG")"

stamp() { date -Iseconds; }
put() { # put <fields...>: rotate first when the log is over 1 MB, keeping one old file
  if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt "$MAX_BYTES" ]; then mv -f "$LOG" "$LOG.1"; fi
  printf '%s\n' "ts=$(stamp) machine=$MACHINE $*" >> "$LOG"
}
secs() { # secs <ISO8601 with zone>: seconds since 1970, by arithmetic (parsing a date is spelled differently on GNU and BSD)
  local y m d era yoe doy off=0
  if [[ "$1" =~ ^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(Z|([+-])([0-9]{2}):?([0-9]{2}))$ ]]; then
    y=$((10#${BASH_REMATCH[1]})); m=$((10#${BASH_REMATCH[2]})); d=$((10#${BASH_REMATCH[3]}))
    [ -z "${BASH_REMATCH[8]}" ] || off=$(( ${BASH_REMATCH[8]}1 * (10#${BASH_REMATCH[9]} * 3600 + 10#${BASH_REMATCH[10]} * 60) ))
    [ "$m" -gt 2 ] || y=$((y - 1))
    era=$((y / 400)); yoe=$((y - era * 400)); doy=$(( (153 * ((m + 9) % 12) + 2) / 5 + d - 1 ))
    echo $(( (era * 146097 + yoe * 365 + yoe / 4 - yoe / 100 + doy - 719468) * 86400
             + 10#${BASH_REMATCH[4]} * 3600 + 10#${BASH_REMATCH[5]} * 60 + 10#${BASH_REMATCH[6]} - off ))
  else
    date +%s      # a time this cannot parse counts as now: 0 minutes, never a made-up number
  fi
}

# what the log last said, read before this call writes: "open <time of the first open after the last closed>", "closed", or nothing
last="$(cat "$LOG.1" "$LOG" 2>/dev/null | grep -a ' master=' \
        | awk '/ master=closed /{s="closed"; o=""} / master=open /{if (o == "") o = substr($1, 4); s="open"} END{print s, o}')"
prev="${last%% *}"; open_iso="${last#* }"

bash "$ON_SITE" --check-master >/dev/null 2>&1
rc=$?
case "$rc" in 0) now=open ;; 124) now=unknown ;; *) now=closed ;; esac
put "master=$now rc=$rc"
if [ "$now" = open ] && [ "$prev" = closed ]; then
  put "event=reopened"
elif [ "$now" = closed ] && [ "$prev" = open ]; then
  lasted=$(( ($(date +%s) - $(secs "$open_iso")) / 60 )); [ "$lasted" -ge 0 ] || lasted=0
  put "event=closed lasted_min=$lasted last_open=$open_iso"
fi
exit 0
