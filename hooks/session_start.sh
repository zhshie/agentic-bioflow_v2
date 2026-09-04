#!/bin/bash
# SessionStart: say what is still in flight, once, at the top of a conversation.
#
# Why this exists at all: the machine running Claude Code sleeps, and the login
# node does not. A Monitor armed by :launch dies with its session. So "what
# happened to the run I started last night" has no answer unless something asks
# at the start of the next conversation.
#
# It is NOT a monitoring daemon (PRINCIPLES.md, invariant 2). It runs once per
# conversation, keeps no state, and asks Platform - which remains the only
# record of a run. Nothing here is written down.
#
# It must never cost the user anything:
#   - exit 0 always. Exit 2 blocks the session from starting at all.
#   - every external call is wrapped in a timeout. The hook default is 600s,
#     which would hang a conversation for ten minutes on one stuck request.
#   - silence is the correct output everywhere this deployment is not set up.
set -uo pipefail
exec 2>/dev/null

INPUT=$(cat)

# A compaction, a /clear or a fork is the same conversation continuing.
# Repeating the same runs there is noise, not news.
REASON=$(jq -r '.session_start_reason // "startup"' <<<"$INPUT" 2>/dev/null) || REASON=startup
case "$REASON" in startup|resume) ;; *) exit 0 ;; esac

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
. "$ROOT/scripts/settings.sh" 2>/dev/null || exit 0

# Speak only where this deployment exists. On a machine that has never run
# setup - an unrelated project, someone else's laptop - there is no settings
# file, and the right behaviour is silence rather than an explanation.
[ -n "${SETTINGS_FILE:-}" ] && [ -r "$SETTINGS_FILE" ] || exit 0

WS="${TOWER_WORKSPACE_ID:-$(setting workspace_id)}"
TW="${TW_BIN:-$(setting tw_bin)}"
[ -n "$TW" ] || TW="$(command -v tw)"
[ -n "$WS" ] && [ -x "$TW" ] || exit 0

TOKEN_FILE="${SEQERA_TOKEN_FILE:-$(dirname "$SETTINGS_FILE")/.seqera_token}"
if [ -z "${TOWER_ACCESS_TOKEN:-}" ] && [ -r "$TOKEN_FILE" ]; then
    TOWER_ACCESS_TOKEN="$(cat "$TOKEN_FILE")"
    export TOWER_ACCESS_TOKEN
fi
[ -n "${TOWER_ACCESS_TOKEN:-}" ] || exit 0

# SUBMITTED is as important as RUNNING: a run that never left the queue looks
# identical to one working hard, and only the site can say which (:runs).
INFLIGHT=$(timeout 8 "$TW" runs list --workspace "$WS" 2>/dev/null \
    | awk -F'|' '
        NR<=2 { next }
        {
          gsub(/^[ \t]+|[ \t]+$/, "", $1); gsub(/^[ \t]+|[ \t]+$/, "", $2)
          gsub(/^[ \t]+|[ \t]+$/, "", $3); gsub(/^[ \t]+|[ \t]+$/, "", $4)
          if ($2 == "RUNNING" || $2 == "SUBMITTED")
              printf "  %s  %s  (%s)  %s\n", $2, $1, $3, $4
        }')
[ -n "$INFLIGHT" ] || exit 0

# Only worth saying when there is a run to lose: a dead outputs reader makes a
# finished run look like it produced nothing (PITFALLS 3c).
AGENT=""
if ! timeout 5 bash "$ROOT/scripts/agent_ctl.sh" status >/dev/null 2>&1; then
    AGENT="

The outputs reader is not running, so anything these produce will look missing
until it is restarted (scripts/agent_ctl.sh start, and see PITFALLS 3c)."
fi

MSG="Still in flight on Seqera Platform:

$INFLIGHT
Use :runs to read one. A run sitting at SUBMITTED may never have been
scheduled - the site knows why, Platform does not.$AGENT"

jq -n --arg m "$MSG" \
  '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $m}}' 2>/dev/null
exit 0
