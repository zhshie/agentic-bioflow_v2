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

# Everything below this line is written as one function early, because the two
# things it reports have opposite conditions: the run list needs a working
# deployment, and the shell warning is precisely for the case where finding one
# is impossible.
emit() {
    [ -n "$1" ] || exit 0
    jq -n --arg m "$1" \
      '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $m}}' 2>/dev/null
    exit 0
}

# The shell warning is computed BEFORE settings.sh is sourced, with nothing but
# uname, so it survives a deployment this shell cannot see - which is the exact
# situation it exists to explain. Under Git Bash the settings file, the site
# connection and the Positron bridge are all unreachable (PITFALLS 16b, 20c,
# 25), and only the first of the three is loud enough to notice.
#
# Not restricted to REASON=startup the way the settings path is. A resume
# follows a compaction, which may have carried the first one away, and the
# whole cost of repeating it is two lines.
SHELLWARN=""
case "$(uname -s 2>/dev/null)" in
    MINGW*|MSYS*|CYGWIN*)
        SHELLWARN="Claude's shell here is Git Bash (MSYS). This plugin cannot reach the
cluster from it: MSYS cannot hold the multiplexed ssh connection, so every site
command would ask for a one-time code from your phone (PITFALLS 16b). A setup
done in WSL is also invisible here, because WSL has its own home directory.

Run Claude Code from a WSL shell instead - install it there with
'npm install -g @anthropic-ai/claude-code' and start 'claude' from that shell.
scripts/on_site.sh refuses with the full instructions when it is reached." ;;
esac

. "$ROOT/scripts/settings.sh" 2>/dev/null || emit "$SHELLWARN"

# Speak only where this deployment exists. On a machine that has never run
# setup - an unrelated project, someone else's laptop - there is no settings
# file, and the right behaviour is silence rather than an explanation. The
# shell warning is the exception: on that machine there may well BE a
# deployment, in a home directory this shell cannot open.
[ -n "${SETTINGS_FILE:-}" ] && [ -r "$SETTINGS_FILE" ] || emit "$SHELLWARN"

# There IS a deployment here, so say where it is - once, and only on a real
# startup. Nothing else that reads this file ever names it, which is how a member
# came to be grepping the filesystem for their own config. A resume is the same
# conversation continuing and has already been told.
WHERE=""
[ "$REASON" = startup ] && WHERE="Deployment settings: $SETTINGS_FILE"
[ -n "$SHELLWARN" ] && WHERE="${WHERE:+$WHERE

}$SHELLWARN"

# Every exit below this point goes through emit(), defined above, so the one
# line survives the many perfectly ordinary reasons there is nothing else to
# report: no token in this shell, no tw, an idle workspace.

WS="${TOWER_WORKSPACE_ID:-$(setting workspace_id)}"
TW="${TW_BIN:-$(setting tw_bin)}"
[ -n "$TW" ] || TW="$(command -v tw)"
[ -n "$WS" ] && [ -x "$TW" ] || emit "$WHERE"

# One derivation, shared with preflight and the site scripts (scripts/settings.sh).
TOKEN_FILE="$(token_file)"
if [ -z "${TOWER_ACCESS_TOKEN:-}" ] && [ -r "$TOKEN_FILE" ]; then
    TOWER_ACCESS_TOKEN="$(cat "$TOKEN_FILE")"
    export TOWER_ACCESS_TOKEN
fi
[ -n "${TOWER_ACCESS_TOKEN:-}" ] || emit "$WHERE"

# SUBMITTED is as important as RUNNING: a run that never left the queue looks
# identical to one working hard, and only the site can say which (:runs).
INFLIGHT=$(clocked 8 "$TW" runs list --workspace "$WS" 2>/dev/null \
    | awk -F'|' '
        NR<=2 { next }
        {
          gsub(/^[ \t]+|[ \t]+$/, "", $1); gsub(/^[ \t]+|[ \t]+$/, "", $2)
          gsub(/^[ \t]+|[ \t]+$/, "", $3); gsub(/^[ \t]+|[ \t]+$/, "", $4)
          if ($2 == "RUNNING" || $2 == "SUBMITTED")
              printf "  %s  %s  (%s)  %s\n", $2, $1, $3, $4
        }')
[ -n "$INFLIGHT" ] || emit "$WHERE"

# Only worth saying when there is a run to lose: a dead outputs reader makes a
# finished run look like it produced nothing (PITFALLS 3c).
AGENT=""
if ! clocked 5 bash "$ROOT/scripts/agent_ctl.sh" status >/dev/null 2>&1; then
    AGENT="

The outputs reader is not running, so anything these produce will look missing
until it is restarted (scripts/agent_ctl.sh start, and see PITFALLS 3c)."
fi

MSG="Still in flight on Seqera Platform:

$INFLIGHT
Use :runs to read one. A run sitting at SUBMITTED may never have been
scheduled - the site knows why, Platform does not.$AGENT"

emit "${WHERE:+$WHERE

}$MSG"
