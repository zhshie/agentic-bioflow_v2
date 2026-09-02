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
# It never denies. A launch the user has thought about is always allowed.
INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)

# Drop here-doc bodies first: a document that MENTIONS `tw launch` is not a
# launch, and the segment scan below would otherwise treat prose as commands.
STRIPPED=$(printf '%s\n' "$CMD" | awk -f "$(dirname "$0")/strip_heredocs.awk" 2>/dev/null)
[ -n "$STRIPPED" ] && CMD="$STRIPPED"

# Decided per segment, never for the whole line: `cat notes.txt && tw launch ...`
# must still hit the gate.
TRIGGER='(^|/)tw[[:space:]]+launch([[:space:]]|$)|nextflow[[:space:]]+run|^[[:space:]]*sbatch([[:space:]]|$)'
READONLY='^[[:space:]]*(cat|less|more|head|tail|grep|rg|wc|chmod|shellcheck|ls|stat|file|diff|cp|vim|nano|echo)([[:space:]]|$)|^[[:space:]]*(bash|sh)[[:space:]]+-n([[:space:]]|$)'

EXECUTES=0
while IFS= read -r S; do
    echo "$S" | grep -qE "$TRIGGER" || continue
    echo "$S" | grep -qE "$READONLY" && continue
    EXECUTES=1; break
done <<< "$(echo "$CMD" | sed -E 's/(\|\||&&|[;&|])/\n/g')"
[ "$EXECUTES" = 1 ] || exit 0

WARN=""
add() { WARN="${WARN}
  - $1"; }

HERE="$(cd "$(dirname "$0")/.." && pwd)"

# Preconditions. Each of these has cost a real run.
#
# Hooks do not always run under a login shell, so an unset LAB_RUNS_DIR means
# "cannot check" - reporting that as "not running" would train the user to
# ignore this section.
if [ -z "${LAB_RUNS_DIR:-}" ]; then
    add "LAB_RUNS_DIR is not set in this shell, so relay and agent state could not be checked"
else
    bash "$HERE/scripts/relay_ctl.sh" status >/dev/null 2>&1 \
      || add "relay is NOT running - compute nodes have no route out and image pulls will fail (scripts/relay_ctl.sh start)"

    bash "$HERE/scripts/agent_ctl.sh" status >/dev/null 2>&1 \
      || add "Tower Agent is NOT running - the run may still execute, but Platform will show no outputs (scripts/agent_ctl.sh start)"
fi

# A relay started on another login node is useless: the head job reaches back by
# hostname, and this site has lgn301..lgn304.
if [ -n "${LAB_RUNS_DIR:-}" ] && bash "$HERE/scripts/relay_ctl.sh" status 2>/dev/null | grep -q WARNING; then
    add "relay was started on a different login node than the one you are on - update the compute environment's proxy variables"
fi

if grep -qE '(^|/)tw[[:space:]]+launch' <<<"$CMD" && ! grep -q -- '--disable-optimization' <<<"$CMD"; then
    add "no --disable-optimization: Platform's resource optimization right-sizes from history, which fights this cluster's fixed-size QOS boxes and can push a request below the floor"
fi

MSG="GATE: this command can start a pipeline run. Show the user the complete command (every parameter, one per line) and wait for an explicit \"確認執行\" before proceeding."
[ -n "$WARN" ] && MSG="${MSG}

Preconditions that are not met:${WARN}

Report these to the user with the command; do not silently launch past them."

jq -n --arg m "$MSG" '{hookSpecificOutput: {hookEventName: "PreToolUse", additionalContext: $m}}'
exit 0
