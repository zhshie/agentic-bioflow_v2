#!/bin/bash
# Measure the four gates the way #34 describes the problem: wall time per call
# and external processes per call, on inputs a session in use actually sends.
#
#   bash measure.sh [hooks-dir] [calls-per-case]
#
# Run it natively (Windows: Git Bash, not WSL) - the whole point is the cost of
# starting a process there. Wall time is a median of N calls; the process count
# is machine-independent and comes from a separate run with logging shims on
# PATH (the shims themselves cost time, so they never share a run with the clock).
set -uo pipefail
HOOKS="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../hooks" && pwd)}"
N="${2:-10}"
ROOT="$(cd "$HOOKS/.." && pwd)"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT

mkdir -p "$TMP/home" "$TMP/state/in-use" "$TMP/work" "$TMP/shims"
: > "$TMP/state/in-use/count-s1"
for i in $(seq 1 200); do printf '{"type":"user","message":{"content":"hello %s"}}\n' "$i"; done > "$TMP/transcript.jsonl"

# --- the inputs --------------------------------------------------------------
declare -a NAMES CMDS
add() { NAMES+=("$1"); CMDS+=("$2"); }
add "grep results/" 'grep -rn x results/'
add "multi-segment" 'cd src && git status --short | head -20; ls -la docs/ | wc -l; echo done > /dev/null'
SCRIPT=$(for i in $(seq 1 30); do echo "x$i = [a for a in range($i)]  # line $i"; done)
add "30-line script" "$(printf 'python3 - <<%s\n%s\nEOF' "'EOF'" "$SCRIPT")"
add "launch" 'tw launch nf-core/rnaseq --profile test'

input() {
  jq -nc --arg c "$1" --arg d "$TMP/work" --arg t "$TMP/transcript.jsonl" \
    '{session_id:"count-s1", cwd:$d, transcript_path:$t, hook_event_name:"PreToolUse", tool_name:"Bash", tool_input:{command:$c}}'
}
run_hook() { # run_hook <hook> <json> [extra PATH]
  printf '%s' "$2" | env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR \
    HOME="$TMP/home" XDG_CONFIG_HOME="$TMP/home/.config" AGENTIC_BIOFLOW_STATE_DIR="$TMP/state" \
    CLAUDE_PLUGIN_ROOT="$ROOT" ABF_PROC_LOG="$TMP/procs.log" PATH="${3:+$3:}$PATH" \
    bash "$HOOKS/$1.sh" >/dev/null 2>&1
}
now_ms() { date +%s%3N; }

for prog in jq awk gawk mawk grep egrep fgrep sed tr cat dirname basename uname sort uniq tail head \
            cut wc date mktemp readlink stat find rm mv cp mkdir chmod env tee xargs seq \
            realpath expr id hostname; do
  real=$(command -v "$prog" 2>/dev/null) || continue
  case "$real" in /*) ;; *) continue ;; esac
  printf '#!/bin/bash\necho %s >> "$ABF_PROC_LOG"\nexec %s "$@"\n' "$prog" "$real" > "$TMP/shims/$prog"
  chmod +x "$TMP/shims/$prog"
done

printf '%-22s %-17s %9s %6s\n' "hook" "input" "median_ms" "procs"
for hook in confirm_launch confirm_cleanup confirm_walkthrough guard_plugin_files; do
  for k in "${!NAMES[@]}"; do
    J=$(input "${CMDS[$k]}")
    ts=()
    for _ in $(seq 1 "$N"); do
      a=$(now_ms); run_hook "$hook" "$J"; b=$(now_ms); ts+=($((b - a)))
    done
    med=$(printf '%s\n' "${ts[@]}" | sort -n | sed -n "$(( (N + 1) / 2 ))p")
    : > "$TMP/procs.log"; run_hook "$hook" "$J" "$TMP/shims"
    printf '%-22s %-17s %9s %6s\n' "$hook" "${NAMES[$k]}" "$med" "$(awk 'END{print NR+0}' "$TMP/procs.log")"
  done
done
