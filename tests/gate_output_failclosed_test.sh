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
# (Total absence of jq is covered by the "no jq" sections of
# tests/confirm_launch_test.sh, tests/confirm_cleanup_test.sh and
# tests/confirm_walkthrough_test.sh; a jq that fails on everything or answers
# wrongly, by the jq-broken-gates section below and by the "jq present but
# broken" section of tests/confirm_cleanup_test.sh.)
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

# gate-emit-empty-object: a jq that reads fine but BUILDS the wrong answer. `{}`
# carries no decision (the call proceeds); a verdict without hookSpecificOutput
# is ignored by Claude Code the same way. Each gate must print its fixed ask.
mkdir -p "$TMP/bin_empty" "$TMP/bin_flat"
{
  echo '#!/bin/bash'
  echo "for a in \"\$@\"; do [ \"\$a\" = -n ] && { echo '{}'; exit 0; }; done"
  echo "exec \"$REALJQ\" \"\$@\""
} > "$TMP/bin_empty/jq"
{
  echo '#!/bin/bash'
  echo "for a in \"\$@\"; do [ \"\$a\" = -n ] && { echo '{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"x\",\"additionalContext\":\"x\"}'; exit 0; }; done"
  echo "exec \"$REALJQ\" \"\$@\""
} > "$TMP/bin_flat/jq"
chmod +x "$TMP/bin_empty/jq" "$TMP/bin_flat/jq"
askdeny() { case "$(decision)" in ask|deny) echo 1 ;; *) echo 0 ;; esac; }
for k in empty flat; do
  run confirm_launch "$TMP/launch.json" "$TMP/bin_$k"
  check "jq builds '$k': launch gate still asks" "$([ "$(decision)" = ask ] && echo 1 || echo 0)" "got '$(decision)' rc=$RC out='${OUT:0:80}'"
  run confirm_cleanup "$TMP/rm.json" "$TMP/bin_$k"
  check "jq builds '$k': deletion guard still asks or denies" "$(askdeny)" "got '$(decision)' rc=$RC out='${OUT:0:80}'"
  run confirm_walkthrough "$TMP/w.json" "$TMP/bin_$k"
  check "jq builds '$k': walkthrough gate still asks or denies" "$(askdeny)" "got '$(decision)' rc=$RC out='${OUT:0:80}'"
  run guard_plugin_files "$TMP/g.json" "$TMP/bin_$k"
  check "jq builds '$k': plugin-file guard still asks or denies" "$(askdeny)" "got '$(decision)' rc=$RC out='${OUT:0:80}'"
done

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

# ---------------------------------------------------------------------------
# jq-broken-gates: a jq that is present but broken - it fails on everything, or
# it answers 0 with something that is not the answer (`{}`, or text) - must not
# turn the launch gate, the walkthrough gate, the plugin-file guard or the
# overview hook silently permissive (invariant 13). Each must do what it does
# with no jq at all: refuse what it guards from the raw text and name the fix
# (the gates: exit 2, BLOCKED and the install line on stderr; plugin_intro.sh:
# the jq warning, and the in-use marker), and stay quiet on a call it does not
# guard. A `{}` answer is the dangerous one: it parses as an empty verdict.
BJ="$TMP/badjq"; mkdir -p "$BJ/fail" "$BJ/empty" "$BJ/text" "$TMP/fakeplugin/hooks"
printf '#!/bin/sh\ncat >/dev/null 2>&1\nexit 3\n' > "$BJ/fail/jq"
printf '#!/bin/sh\ncat >/dev/null 2>&1\necho "{}"\n' > "$BJ/empty/jq"
printf '#!/bin/sh\ncat >/dev/null 2>&1\necho "Segmentation fault (core dumped)"\n' > "$BJ/text/jq"
chmod +x "$BJ"/*/jq
BJ_LAUNCH=$(jq -nc --arg c "$TW launch nf-core/rnaseq -profile test" '{tool_name:"Bash", tool_input:{command:$c}}')
BJ_LS='{"tool_name":"Bash","tool_input":{"command":"ls -la"}}'
BJ_SS=$(jq -nc --arg t "$TMP/transcript.jsonl" '{tool_name:"Write", transcript_path:$t, tool_input:{file_path:"/r/samplesheet.csv", content:"sample,fastq_1\n"}}')
BJ_NOTES=$(jq -nc --arg t "$TMP/transcript.jsonl" '{tool_name:"Write", transcript_path:$t, tool_input:{file_path:"/r/notes.txt", content:"x\n"}}')
BJ_GUARD=$(jq -nc --arg p "$TMP/fakeplugin/hooks/x.sh" '{tool_name:"Write", tool_input:{file_path:$p, content:"x"}}')
BJ_OTHER=$(jq -nc --arg p "$TMP/work/x.txt" '{tool_name:"Write", tool_input:{file_path:$p, content:"x"}}')
bj_run() { # bj_run <kind> <hook> <json>  -> BJ_OUT BJ_ERR BJ_RC (no session id: in use)
  BJ_OUT=$(printf '%s' "$3" | env -u LAB_SETTINGS_FILE PATH="$BJ/$1:$PATH" CLAUDE_PLUGIN_ROOT="$TMP/fakeplugin" \
           AGENTIC_BIOFLOW_STATE_DIR="$TMP/bjstate" HOME="$TMP/home" timeout 60 bash "$HOOKS/$2.sh" 2>"$TMP/bj_err")
  BJ_RC=$?; BJ_ERR=$(cat "$TMP/bj_err" 2>/dev/null)
}
bj_refuses() { # bj_refuses <label>: exit 2, BLOCKED and the install line on stderr, nothing on stdout
  printf '%-78s ' "$1"
  if [ "$BJ_RC" = 2 ] && [ -z "$BJ_OUT" ] && [[ $BJ_ERR == *BLOCKED* ]] && [[ $BJ_ERR == *'install jq'* || $BJ_ERR == *'jqlang.jq'* ]]; then echo ok
  else echo "FAIL: rc=$BJ_RC out='${BJ_OUT:0:60}' err='${BJ_ERR:0:80}'"; fails=$((fails+1)); fi
}
bj_quiet() { # bj_quiet <label>: exit 0, nothing at all
  printf '%-78s ' "$1"
  if [ "$BJ_RC" = 0 ] && [ -z "$BJ_OUT" ] && [ -z "$BJ_ERR" ]; then echo ok
  else echo "FAIL: rc=$BJ_RC out='${BJ_OUT:0:60}' err='${BJ_ERR:0:80}'"; fails=$((fails+1)); fi
}
echo
echo "== jq-broken-gates: jq present but failing, or answering wrongly =="
for k in fail empty text; do
  bj_run "$k" confirm_launch "$BJ_LAUNCH";      bj_refuses "jq '$k': launch gate refuses tw launch, names the fix"
  bj_run "$k" confirm_launch "$BJ_LS";          bj_quiet   "jq '$k': launch gate stays quiet on ls"
  bj_run "$k" confirm_walkthrough "$BJ_SS";     bj_refuses "jq '$k': walkthrough gate refuses a samplesheet write, names the fix"
  bj_run "$k" confirm_walkthrough "$BJ_NOTES";  bj_quiet   "jq '$k': walkthrough gate stays quiet on notes.txt"
  bj_run "$k" guard_plugin_files "$BJ_GUARD";   bj_refuses "jq '$k': plugin-file guard refuses a write into the plugin"
  bj_run "$k" guard_plugin_files "$BJ_OTHER";   bj_quiet   "jq '$k': plugin-file guard stays quiet elsewhere"
  bj_run "$k" plugin_intro "$(jq -nc --arg s "bj-$k" '{session_id:$s, hook_event_name:"UserPromptSubmit", prompt:"/agentic-bioflow:setup"}')"
  printf '%-78s ' "jq '$k': plugin_intro.sh warns that jq is broken, and marks the session"
  if [ "$BJ_RC" = 0 ] && [[ $BJ_OUT == *'jq is missing or cannot run'* ]] && printf '%s' "$BJ_OUT" | jq -e .systemMessage >/dev/null 2>&1 \
     && [ -e "$TMP/bjstate/in-use/bj-$k" ]; then echo ok
  else echo "FAIL: rc=$BJ_RC out='${BJ_OUT:0:80}'"; fails=$((fails+1)); fi
done

# jq-broken-later-line: in the raw input a line break is the two characters
# `\n`, which glued the next line's first word to an `n` (`ntw`). A launch on
# line 2 must be refused like one on line 1, with every kind of broken jq.
mkdir -p "$BJ/missing"; printf '#!/bin/sh\nexit 127\n' > "$BJ/missing/jq"; chmod +x "$BJ/missing/jq"
BJ_LAUNCH2=$(jq -nc --arg c "$(printf 'echo ok\n%s launch nf-core/rnaseq -profile test' "$TW")" '{tool_name:"Bash", tool_input:{command:$c}}')
BJ_LS2=$(jq -nc --arg c "$(printf 'echo ok\nls -la')" '{tool_name:"Bash", tool_input:{command:$c}}')
for k in missing fail empty text; do
  bj_run "$k" confirm_launch "$BJ_LAUNCH2";      bj_refuses "jq '$k': launch gate refuses tw launch on line 2"
  bj_run "$k" confirm_launch "$BJ_LS2";          bj_quiet   "jq '$k': launch gate stays quiet on ls on line 2"
  bj_run "$k" confirm_walkthrough "$BJ_LAUNCH2"; bj_refuses "jq '$k': walkthrough gate refuses tw launch on line 2"
  bj_run "$k" confirm_walkthrough "$BJ_LS2";     bj_quiet   "jq '$k': walkthrough gate stays quiet on ls on line 2"
done

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
