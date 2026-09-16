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

# The overview of the plugin is NOT shown here any more. It used to open every
# conversation in every project; it now appears the first time the plugin is
# actually used in a session (hooks/plugin_intro.sh).

# 10,000-character cap on hook output: past it Claude Code writes the output to
# a file and shows a preview instead.
cap10k() {
    local s="$1"
    if [ "${#s}" -gt 9000 ]; then
        printf '%s\n\n[truncated]' "${s:0:9000}"
    else
        printf '%s' "$s"
    fi
}

# Everything below this line is written as one function early, because the two
# things it reports have opposite conditions: the run list needs a working
# deployment, and the shell warning is precisely for the case where finding one
# is impossible. With nothing to say, it says nothing.
emit() {
    local ctx="${1:-}"
    [ -n "$ctx" ] || exit 0
    ctx=$(cap10k "$ctx")
    jq -n --arg c "$ctx" \
      '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $c}}' 2>/dev/null
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
        SHELLWARN="Claude's shell here is Git Bash (MSYS), which this version does
not support. python3 on PATH here is a Microsoft Store stub (PITFALLS 20c), a
default install carries no jq, and the test suite does not run here. This shell's own
ssh also cannot hold the multiplexed connection the site needs (PITFALLS 16b),
though calling WSL's ssh from here was measured to work (PITFALLS 16g) - this
version does not use it. A setup done in WSL is invisible here as well, because
WSL has its own home directory.

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

# 2.8: which cell of docs/CONDITIONS.md this machine is in - said only when it
# is not `supported`, so the ordinary start stays as quiet as before. Local
# measurement only (detect_conditions.sh never touches the network), inside a
# 3s clock because the budget below is already mostly spent.
COND=$(clocked 3 bash "$ROOT/scripts/detect_conditions.sh" 2>/dev/null)
CSTATUS=$(printf '%s\n' "$COND" | sed -n 's/^status=//p')
if [ -n "$CSTATUS" ] && [ "$CSTATUS" != supported ]; then
    CCELL=$(printf '%s\n' "$COND" | sed -n 's/^cell=//p')
    CMSG=$(printf '%s\n' "$COND" | sed -n 's/^message=//p')
    WHERE="${WHERE:+$WHERE

}Condition: $CCELL ($CSTATUS) - $CMSG"
fi

# 2.8: off-design reports still queued (scripts/report.sh). Every start and
# every resume, for the same reason as SHELLWARN: a compaction may have taken
# the first reminder. Read only - this hook keeps no state and writes nothing.
RQ="${AGENTIC_BIOFLOW_REPORTS_DIR:-$(dirname "$SETTINGS_FILE")/reports}"
NREP=0
for r in "$RQ"/*.report; do [ -e "$r" ] && NREP=$((NREP + 1)); done
[ "$NREP" -gt 0 ] && WHERE="${WHERE:+$WHERE

}$NREP off-design report(s) not sent - 'scripts/report.sh send' shows exactly what would go out before anything is sent."

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
#
# R5 (2.9): this used to `awk -F'|'` the human-readable table (`tw runs list`),
# reading fields by COLUMN POSITION ($1 id, $2 status, $3 project, $4 run
# name). That table has no contract - it is meant for a person's eyes, and
# nothing stops a future `tw` release reordering or renaming a column, which
# would silently misattribute status to the wrong run rather than fail loudly.
# `tw -o json runs list` is the machine-readable form this hook already
# requires `jq` for elsewhere, so field NAMES are read instead of column
# INDEXES. Measured on this login node (tw 0.40.0, real workspace, `tw -o json
# runs list --workspace <ws>`), not inferred from docs: the response is
# `{"workflows":[{"workflow":{"id":..., "status":..., "projectName":...,
# "runName":..., ...}}, ...]}` - each entry nests its fields one level under
# "workflow". The `?`/`// []`/`// ""` guards below are for an empty or
# briefly-malformed response (mid-deploy, a workspace with zero runs), not for
# a shape that has ever actually been seen different from this.
INFLIGHT=$(clocked 8 "$TW" -o json runs list --workspace "$WS" 2>/dev/null \
    | jq -r '
        (.workflows // [])[]? | .workflow |
        select(.status == "RUNNING" or .status == "SUBMITTED") |
        "  " + .status + "  " + .id + "  (" + (.projectName // "") + ")  " + (.runName // "")
      ' 2>/dev/null)
[ -n "$INFLIGHT" ] || emit "$WHERE"

# Z3: this check runs on THIS machine, so it only means something when this
# machine IS the site (reach: local). Under ssh/none, Claude runs on the
# user's own laptop; agent_ctl.sh would be probing a process that was never
# meant to run there, and it always reports "not running" - reporting that as
# a fault taught the reader to ignore it, exactly like Z2. `setting` is
# already in scope: settings.sh was sourced above (or this hook has already
# exited through `emit`), so this is not a second lookup mechanism, just the
# existing one asked one more question.
#
# No network call is added to make this work under ssh: the 15s budget is
# already ~13s spent by the `clocked` calls above, and `runs` already covers
# this once a run is actually being watched.
#
# Only worth saying when there is a run to lose: a dead outputs reader makes a
# finished run look like it produced nothing (PITFALLS 3c).
AGENT=""
REACH="$(setting reach local)"
if [ "$REACH" = local ] && ! clocked 5 bash "$ROOT/scripts/agent_ctl.sh" status >/dev/null 2>&1; then
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
