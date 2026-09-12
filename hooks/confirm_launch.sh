#!/bin/bash
# PreToolUse/Bash: the execution gate for v2.
#
# v1 gated `nextflow run` and consulted a .cli_task.json phase machine to decide
# whether to prompt. v2 has no state machine - Seqera Platform is the only
# source of truth for run state - so this gate does two things instead:
#
#   1. Requires an explicit confirmation before anything that can start a run.
#   2. Reports the preconditions that silently ruin a launch here, while the
#      command is still on screen, rather than 20 minutes into a stalled run.
#
# It never denies a launch it can actually see. It DOES refuse - the one
# exception to the line above - when `jq` itself is missing, deliberately
# fail-closed (PITFALLS 28). Before this check existed, no `jq` meant every
# `jq -r` below silently produced an empty string: CMD came back "", every
# judgement after it went the harmless way, and the whole gate vanished with
# nothing printed. A freshly installed WSL Ubuntu has no `jq`, and neither did
# macOS before 15, so this was not a corner case.
#
# Exit 2 rather than a JSON `deny` decision: building that JSON is itself a
# `jq -n` call, so leaning on jq to report jq's own absence would fail the
# same way it is trying to fix. Exit 2 needs nothing but the shell.
# `command -v jq` would only prove a FILE exists. A jq that cannot run -
# wrong architecture, a missing shared library, or a Windows jq.exe that
# Git Bash finds but cannot execute - passes that check and then fails
# every parse below, which is the exact silent-gate failure this guard
# exists to stop. So ask jq to do its job on the smallest possible input.
if ! printf '{}' | jq -e . >/dev/null 2>&1; then
    cat >&2 <<'EOF'
BLOCKED: jq is missing or cannot run here, so hooks/confirm_launch.sh cannot read what
this command is - and cannot tell a pipeline launch from `ls`. Rather than
silently stop checking (the old, dangerous behaviour), it refuses every Bash
command until jq exists. The same is true of confirm_cleanup.sh and
confirm_walkthrough.sh, which share this requirement.

Install it yourself (this hook will not attempt to), then retry:
  macOS:       brew install jq
  Debian/WSL:  sudo apt install jq
EOF
    exit 2
fi

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)

# "Does this string start a run" is a judgement several hooks need to reach
# identically, so it lives in one sourced file instead of being restated here.
# Sourced relative to $0 the same way strip_heredocs.awk is, so a direct
# `bash hooks/confirm_launch.sh` from a test still finds it.
#
# It is loaded fail-CLOSED, unlike strip_heredocs.awk beside it. That awk fails
# safe by construction: if it dies, STRIPPED is empty, CMD keeps its original
# value, and the judgement below still happens. A missing launch_trigger.sh
# fails the other way - `is_launch_command` becomes command-not-found, 127 is
# non-zero, and `|| exit 0` waves through every command including a real launch.
# The gate would be gone with nothing on screen to say so, which is precisely
# the failure this file exists to prevent. So when the helper cannot be loaded,
# every command is treated as one that might start a run. That is noisy, and
# noisy is the correct behaviour for a safety net that has stopped being able
# to judge.
if ! . "$(dirname "$0")/launch_trigger.sh" 2>/dev/null \
   || ! declare -F is_launch_command >/dev/null 2>&1; then
    jq -n --arg m "GATE NOT WORKING: hooks/launch_trigger.sh could not be loaded, so this command was NOT checked and no other command will be either.

Reinstall or repair the plugin. Until then the launch gate is absent: treat anything that can start a run - tw launch, tw runs relaunch, sbatch, nextflow run - as ungated, and confirm it with the user by hand." \
      '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $m}}'
    exit 0
fi

is_launch_command "$CMD" || exit 0

WARN=""
add() { WARN="${WARN}
  - $1"; }

HERE="$(cd "$(dirname "$0")/.." && pwd)"

# Z2: whether an unset LAB_RUNS_DIR is a FAULT depends on `reach`. v2.6 settled
# that under `ssh`/`none` this variable must NOT be set in the user's own
# shell - the site is a different machine entirely - so under those two
# reaches this warning used to fire on every single launch command,
# unconditionally, reporting as broken a thing that was working exactly as
# designed. A warning that always fires teaches the reader to skip the whole
# section (the same argument every other message in this file already makes).
#
# Reading `reach` means reading the settings file, which is settings.sh's job
# alone - PITFALLS already recorded that a second copy of that search logic
# drifts out of sync (on_site.sh once carried a hand-written list of another
# script's dependencies, twice gone stale). The "no helper" rule beside this
# file's siblings (confirm_cleanup.sh, confirm_walkthrough.sh) exists to stop
# a gate vanishing SILENTLY the moment a sourced file goes missing. Invoking
# settings.sh as a SUBPROCESS rather than sourcing it sidesteps that risk a
# different way: if the call fails for any reason at all - settings.sh
# missing, its own portable.sh missing, no settings file anywhere - the
# command substitution below comes back empty and REACH falls back to
# "local", which is exactly TODAY'S unconditional behaviour and the same
# default settings.sh/on_site.sh already use for this same key. So the worst
# this lookup can do is leave the gate exactly as noisy as it already is; it
# can never make it vanish the way a bare `. helper.sh || true` would. That is
# why this one line is a subprocess call rather than the `.` this repo
# forbids for its two stricter siblings.
#
# Under ssh/none the fix is silence, not a substitute check: on_site.sh can
# answer this, but only at the cost of a round trip that runs up to 31s
# without an already-shared connection (measured) against this hook's own
# 10s timeout - and a PreToolUse hook that times out does not block, it lets
# the tool call through with NOTHING shown, on no predictable schedule. A
# launch command that reliably prints nothing extra is a better outcome than
# one that unpredictably times out trying to be helpful. :launch's own
# background watcher and :runs already cover this once the run actually
# starts.
REACH="$(bash "$HERE/scripts/settings.sh" reach local 2>/dev/null)"
[ -n "$REACH" ] || REACH=local

# Preconditions. Each of these has cost a real run.
#
# Hooks do not always run under a login shell, so an unset LAB_RUNS_DIR means
# "cannot check" - reporting that as "not running" would train the user to
# ignore this section.
if [ -z "${LAB_RUNS_DIR:-}" ]; then
    case "$REACH" in
        ssh|none) ;;   # expected here (v2.6) - not a fault, see above
        *) add "LAB_RUNS_DIR is not set in this shell, so the site's readiness could not be checked" ;;
    esac
else
    bash "$HERE/scripts/egress_ctl.sh" status >/dev/null 2>&1 \
      || add "the site's egress channel is DOWN - container pulls and reference downloads will fail (scripts/egress_ctl.sh start)"

    bash "$HERE/scripts/agent_ctl.sh" status >/dev/null 2>&1 \
      || add "Tower Agent is NOT running - the run may still execute, but Platform will show no outputs (scripts/agent_ctl.sh start)"
fi

# Where a site's egress channel is tied to a specific host, a channel that came
# up elsewhere is useless: the head job reaches back by the address baked into
# the compute environment. The adapter reports this as a WARNING.
if [ -n "${LAB_RUNS_DIR:-}" ] && bash "$HERE/scripts/egress_ctl.sh" status 2>/dev/null | grep -q WARNING; then
    add "the egress channel is up somewhere other than where the compute environment expects it - see scripts/egress_ctl.sh env"
fi

if grep -qE '(^|/)tw[[:space:]]+launch' <<<"$CMD" && ! grep -q -- '--disable-optimization' <<<"$CMD"; then
    add "no --disable-optimization: Platform right-sizes from run history, which fights a site whose accepted sizes are fixed - a helpfully reduced request can land below what the site will take"
fi

# The same check cannot be made of a relaunch: `tw runs relaunch` has no
# --disable-optimization flag at all (`tw runs relaunch --help`), because it
# reuses whatever the original launch stored. Saying nothing would read as
# "checked, and fine", and warning that the flag is absent would send the user
# to a flag that does not exist - so state which of the two it is. It is not a
# precondition the user can meet, so it does not go in the WARN list.
NOTE=""
if grep -qE '(^|/)tw[[:space:]]+runs[[:space:]]+relaunch' <<<"$CMD"; then
    NOTE="This is a relaunch, so the --disable-optimization question cannot be answered from the command line: the flag does not exist on \`tw runs relaunch\`, and the setting is inherited from the original launch. Check it in the Platform launch form before confirming."
fi

MSG="GATE: this command can start a pipeline run. Show the user the complete command (every parameter, one per line) and wait for an explicit \"確認執行\" before proceeding."
[ -n "$NOTE" ] && MSG="${MSG}

${NOTE}"
[ -n "$WARN" ] && MSG="${MSG}

Preconditions that are not met:${WARN}

Report these to the user with the command; do not silently launch past them."

jq -n --arg m "$MSG" '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $m}}'
exit 0
