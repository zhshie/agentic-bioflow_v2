#!/bin/bash
# Invariant 13 / Safety Net 3: a gate that cannot BUILD its own verdict must not
# fall silent. Every gate builds its answer with `jq -n --arg ...`; the OS limits
# argv (about 32 KB on Windows, 128 KiB per argument on Linux) and jq can fail for
# other reasons too. A hook that prints nothing and exits 0 lets the call proceed,
# so the launch / delete / write the gate had just recognised goes through.
#
# Two properties, for every gate that can pause or refuse a call:
#   1. a verdict whose text is far larger than the argv limit is still delivered,
#      and the displayed text is bounded (with a marker for what was left out);
#   2. if jq reads the input fine but cannot build the answer, a fixed minimal
#      `ask` is printed instead of nothing.
# (Total absence of jq, and a jq that fails on everything, are covered by
# tests/gate_jq_failing_test.sh.)
#
# The delete verb and the launch verb are assembled from hex so this file's own
# text does not trip a gate watching the shell.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
HOOKS="$ROOT/hooks"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0
command -v jq >/dev/null 2>&1 || { echo "jq is required for this test"; exit 1; }
PY=$(command -v python3 || command -v python) || { echo "python is required for this test"; exit 1; }
REALJQ=$(command -v jq)

D=$(printf '\x72\x6d')
TW=$(printf '\x74\x77')
mkdir -p "$TMP/home" "$TMP/state/in-use" "$TMP/work/analysis" "$TMP/bin"
: > "$TMP/state/in-use/fc-s1"
for i in $(seq 1 50); do printf '{"type":"user","message":{"content":"hello %s"}}\n' "$i"; done > "$TMP/transcript.jsonl"

# A jq that reads fine but cannot build output (anything started with -n fails).
{
  echo '#!/bin/bash'
  echo 'for a in "$@"; do [ "$a" = -n ] && exit 5; done'
  echo "exec \"$REALJQ\" \"\$@\""
} > "$TMP/bin/jq"
chmod +x "$TMP/bin/jq"

# mk <file> <tool> <command | file_path::content-kb>
mk() {
  "$PY" - "$1" "$2" "$3" "$TMP" <<'PY'
import json, sys
f, tool, spec, tmp = sys.argv[1:5]
if tool == "Write":
    ti = {"file_path": tmp + "/work/analysis/de.R", "content": "x <- 1\n" * 40}
else:
    ti = {"command": spec.replace("@BIG@", "echo " + "y" * 70000)}
d = {"session_id": "fc-s1", "cwd": tmp + "/work", "transcript_path": tmp + "/transcript.jsonl",
     "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti}
open(f, "w").write(json.dumps(d))
PY
}

# run <hook> <input> [path-prefix]  -> OUT, RC
run() {
  OUT=$( ( cd "$TMP/work" && env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR HOME="$TMP/home" XDG_CONFIG_HOME="$TMP/home/.config" \
        AGENTIC_BIOFLOW_STATE_DIR="$TMP/state" CLAUDE_PLUGIN_ROOT="$ROOT" PATH="${3:+$3:}$PATH" \
        timeout 60 bash "$HOOKS/$1.sh" < "$2" 2>/dev/null ) )
  RC=$?
}
decision() { printf '%s' "$OUT" | jq -r '.hookSpecificOutput.permissionDecision // "none"' 2>/dev/null || echo unparsable; }

check() { # check <label> <ok?> <detail>
  printf '%-78s ' "$1"
  if [ "$2" = 1 ]; then echo ok; else echo "FAIL: $3"; fails=$((fails+1)); fi
}

echo "== jq reads the input but cannot build the answer: a minimal ask, never silence =="
mk "$TMP/launch.json" Bash "$TW launch nf-core/rnaseq -profile test"
run confirm_launch "$TMP/launch.json" "$TMP/bin"
check "launch gate: ask when its message cannot be built" "$([ "$(decision)" = ask ] && echo 1 || echo 0)" "got '$(decision)' rc=$RC out='${OUT:0:80}'"

mk "$TMP/rm.json" Bash "$D -rf /work/u/lab_runs/x/results"
run confirm_cleanup "$TMP/rm.json" "$TMP/bin"
check "deletion guard: ask-or-deny when its message cannot be built" "$([ "$(decision)" = ask ] || [ "$(decision)" = deny ] && echo 1 || echo 0)" "got '$(decision)' rc=$RC"

mk "$TMP/w.json" Write x
run confirm_walkthrough "$TMP/w.json" "$TMP/bin"
check "walkthrough gate: ask-or-deny when its message cannot be built" "$([ "$(decision)" = ask ] || [ "$(decision)" = deny ] && echo 1 || echo 0)" "got '$(decision)' rc=$RC"

mk "$TMP/g.json" Bash "sed -i 's/a/b/' $ROOT/hooks/confirm_launch.sh"
run guard_plugin_files "$TMP/g.json" "$TMP/bin"
check "plugin-file guard: ask-or-deny when its message cannot be built" "$([ "$(decision)" = ask ] || [ "$(decision)" = deny ] && echo 1 || echo 0)" "got '$(decision)' rc=$RC"

echo
echo "== a verdict whose text is huge is still delivered, and the display is bounded =="
BIG=@BIG@
mk "$TMP/biglaunch.json" Bash "$BIG; $TW launch nf-core/rnaseq -profile test"
run confirm_launch "$TMP/biglaunch.json"
check "launch gate: a 70 KB command line still asks" "$([ "$(decision)" = ask ] && echo 1 || echo 0)" "got '$(decision)' rc=$RC"
LEN=${#OUT}
check "launch gate: ...with a bounded message that says what was left out" \
  "$([ "$LEN" -lt 40000 ] && printf '%s' "$OUT" | grep -q 'left out of this display' && echo 1 || echo 0)" "length $LEN"

mk "$TMP/bigrm.json" Bash "$BIG; $D -rf /work/u/lab_runs/x/results"
run confirm_cleanup "$TMP/bigrm.json"
check "deletion guard: a 70 KB command line still denies" "$([ "$(decision)" = deny ] && echo 1 || echo 0)" "got '$(decision)' rc=$RC"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
