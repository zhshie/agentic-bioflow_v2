#!/bin/bash
# #34: the gates took 4-5 s per shell call under Windows Git Bash, because every
# external process is expensive there and the gates started dozens of them
# (`cat`, `dirname`, `uname`, `jq` three or four times, `grep`, `printf | awk`
# per stage). A timing test only measures the machine; this one counts what
# costs the time: external programs started per call.
#
# Every external command a hook can reach goes through a logging shim that
# records its name and then runs the real one. The hooks run against a session
# that is in use, with a transcript, on commands that no gate has anything to
# say about (the ordinary case: nearly every call), and the count has to stay
# small. The budget is what the redesign needs, not what it could reach:
#   jq once for the input, at most two awk passes for the segments (strip
#   here-doc bodies, split into commands), nothing else.
#
# The verdicts are not tested here - the gate tests (confirm_*_test.sh,
# in_use_test.sh, ...) hold those, and they pass unchanged.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
HOOKS="$ROOT/hooks"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0

command -v jq >/dev/null 2>&1 || { echo "jq is required for this test"; exit 1; }

# --- shims: one per external program a hook could start ----------------------
SHIMS="$TMP/shims"; mkdir -p "$SHIMS"
LOG="$TMP/procs.log"
for prog in jq awk gawk mawk grep egrep fgrep sed tr cat dirname basename uname sort uniq tail head \
            cut wc date mktemp readlink stat find rm mv cp mkdir chmod env tee xargs seq printf \
            realpath expr id hostname; do
  real=$(command -v "$prog" 2>/dev/null) || continue
  case "$real" in /*) ;; *) continue ;; esac     # a builtin or function: not a process
  printf '#!/bin/bash\necho %s >> "$ABF_PROC_LOG"\nexec %s "$@"\n' "$prog" "$real" > "$SHIMS/$prog"
  chmod +x "$SHIMS/$prog"
done

mkdir -p "$TMP/home" "$TMP/state/in-use" "$TMP/work" "$TMP/plugin/hooks"
: > "$TMP/state/in-use/count-s1"
for i in $(seq 1 200); do printf '{"type":"user","message":{"content":"hello %s"}}\n' "$i"; done > "$TMP/transcript.jsonl"
cp "$HOOKS"/* "$TMP/plugin/hooks/" 2>/dev/null

input() { # input <command>
  jq -nc --arg c "$1" --arg d "$TMP/work" --arg t "$TMP/transcript.jsonl" \
    '{session_id:"count-s1", cwd:$d, transcript_path:$t, hook_event_name:"PreToolUse", tool_name:"Bash", tool_input:{command:$c}}'
}

count() { # count <hook> <command>  -> number of external programs the hook started
  : > "$LOG"
  input "$2" | env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR \
      HOME="$TMP/home" XDG_CONFIG_HOME="$TMP/home/.config" AGENTIC_BIOFLOW_STATE_DIR="$TMP/state" \
      CLAUDE_PLUGIN_ROOT="$ROOT" ABF_PROC_LOG="$LOG" PATH="$SHIMS:$PATH" \
      bash "$HOOKS/$1.sh" >/dev/null 2>&1
  awk 'END {print NR+0}' "$LOG"
}
procs() { # procs <hook> <command>  -> the list, for the failure message
  count "$1" "$2" >/dev/null; tr '\n' ' ' < "$LOG"
}

check() { # check <hook> <budget> <label> <command>
  local n; n=$(count "$1" "$4")
  printf '%-74s ' "$3 [$1: $n, budget $2]"
  if [ "$n" -le "$2" ]; then echo ok; else echo "FAIL: started: $(procs "$1" "$4")"; fails=$((fails+1)); fi
}

echo "== external programs started per call, on commands the gates do not care about =="
for c in 'ls -la' 'git status && git diff --stat | head -20' "grep -rn \"foo\" scripts/ | sort | uniq -c | head -5; for f in a b c; do echo \$f; done" \
         'cat notes.txt' 'echo hello'; do
  check confirm_launch   3 "launch gate: ${c:0:34}" "$c"
  check confirm_cleanup  2 "deletion guard: ${c:0:34}" "$c"
  check confirm_walkthrough 4 "walkthrough gate: ${c:0:34}" "$c"
done
check guard_plugin_files 2 "plugin-file guard: ls -la" 'ls -la'

echo
echo "== a transport command and a deletion cost no more than a few more =="
check confirm_launch  5 "launch gate on a (non-MSYS) ssh" 'ssh h "cd /work/run && squeue -u me | head"'
check confirm_cleanup 5 "deletion guard on rm -rf of work/" 'rm -rf /work/u/lab_runs/x/work'
check confirm_cleanup 5 "deletion guard on a refused rm of results/" 'rm -rf /work/u/lab_runs/x/results/fastqc'
LONGBODY=$(for i in $(seq 1 60); do echo "x$i = [a for a in range($i)]  # line $i"; done)
LONGCMD=$(printf 'python3 - <<%s\n%s\nEOF\n' "'EOF'" "$LONGBODY")
check confirm_launch   3 "launch gate on a 60-line here-doc" "$LONGCMD"
check confirm_cleanup  3 "deletion guard on a 60-line here-doc" "$LONGCMD"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
