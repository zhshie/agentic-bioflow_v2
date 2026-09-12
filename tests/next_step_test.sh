#!/bin/bash
# Regression tests for hooks/next_step.sh, the Stop hook that enforces U7:
# while a command's flow is active, the model's final message must end with
# a next step.
#
# "Flow active" is read from real tool calls in the transcript - `intro.sh
# <cmd>` opens it, `intro.sh --end <cmd>` closes it - never from the model's
# own claim. This file builds transcripts directly (no shared mktx helper
# with confirm_walkthrough_test.sh - the two files are independent by the
# house style) with one record per Bash tool_use or assistant text block.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
H="$ROOT/hooks/next_step.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

# Build a transcript from a compact spec, one record per argument:
#   w:<cmd>    a Bash tool_use the assistant RAN
#   a:<text>   assistant text (the model's own message)
mktx() {
  local out="$1"; shift
  python3 - "$out" "$@" <<'PY'
import json, sys
out, specs = sys.argv[1], sys.argv[2:]
with open(out, "w") as f:
    for spec in specs:
        kind, _, text = spec.partition(":")
        if kind == "w":
            rec = {"type": "assistant", "message": {"content": [
                   {"type": "tool_use", "name": "Bash", "input": {"command": text}}]}}
        else:
            rec = {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}
        f.write(json.dumps(rec) + "\n")
PY
}

t() { # t <label> <expect block|allow> <stop_hook_active true|false> <transcript-file> [settings-file]
  printf '%-64s ' "$1"
  local out got
  out=$(python3 -c '
import json,sys
print(json.dumps({"stop_hook_active": sys.argv[1]=="true", "transcript_path": sys.argv[2]}))' \
        "$3" "$4" | env -u LAB_SETTINGS_FILE ${5:+LAB_SETTINGS_FILE="$5"} bash "$H" 2>/dev/null)
  if [ -z "$out" ]; then got=allow
  else got=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("decision","?"))' <<<"$out" 2>/dev/null) || got=unparseable
  fi
  if [ "$got" = "$2" ]; then echo "ok ($got)"
  else echo "FAIL: expected $2, got $got  <<${out:-<empty>}>>"; fails=$((fails+1)); fi
}

INTRO_LAUNCH='bash ${CLAUDE_PLUGIN_ROOT}/scripts/intro.sh launch'
INTRO_END_LAUNCH='bash ${CLAUDE_PLUGIN_ROOT}/scripts/intro.sh --end launch'
INTRO_SETUP='bash ${CLAUDE_PLUGIN_ROOT}/scripts/intro.sh setup'

mktx "$TMP/never_used.jsonl"      'a:hello there, nothing to do with this plugin'
mktx "$TMP/no_flow_yet.jsonl"     'a:let me look at setup.md before doing anything'
mktx "$TMP/in_flow_no_next.jsonl" "w:$INTRO_LAUNCH" 'a:Here is the plan for your run.'
mktx "$TMP/in_flow_with_next.jsonl" "w:$INTRO_LAUNCH" 'a:Here is the plan. 下一步: confirm the command and I will submit it.'
mktx "$TMP/ended.jsonl"           "w:$INTRO_LAUNCH" "w:$INTRO_END_LAUNCH" 'a:All done, no next step here.'
mktx "$TMP/switched.jsonl"        "w:$INTRO_SETUP" "w:$INTRO_LAUNCH" 'a:Now configuring the run, no next step.'
mktx "$TMP/reentered.jsonl"       "w:$INTRO_LAUNCH" "w:$INTRO_END_LAUNCH" "w:$INTRO_LAUNCH" 'a:Back in launch, still no next step.'

echo "== outside any flow: never blocks =="
t "a conversation that never touched this plugin"     allow false "$TMP/never_used.jsonl"
t "talk about a command without running intro.sh yet" allow false "$TMP/no_flow_yet.jsonl"

echo "== inside a flow =="
t "flow active, no next step in the final message"    block false "$TMP/in_flow_no_next.jsonl"
t "flow active, next step present - allowed"          allow false "$TMP/in_flow_with_next.jsonl"
t "flow ended with --end - no longer required"        allow false "$TMP/ended.jsonl"
t "moving to a new command resets which flow is open" block false "$TMP/switched.jsonl"
t "re-entering after --end asks again"                block false "$TMP/reentered.jsonl"

echo "== stop_hook_active: always exit clean, never re-block =="
t "stop_hook_active=true overrides everything, even a bare miss" allow true "$TMP/in_flow_no_next.jsonl"

echo "== language: settings file language: en switches the needle =="
printf 'language: en\n' > "$TMP/en.yaml"
mktx "$TMP/in_flow_en_zh_needle.jsonl" "w:$INTRO_LAUNCH" 'a:Plan is ready. 下一步: confirm.'
mktx "$TMP/in_flow_en_en_needle.jsonl" "w:$INTRO_LAUNCH" 'a:Plan is ready. Next step: confirm the launch command.'
t "en: a zh-only next-step marker does not satisfy the en gate" block false "$TMP/in_flow_en_zh_needle.jsonl" "$TMP/en.yaml"
t "en: the English marker satisfies it"                          allow false "$TMP/in_flow_en_en_needle.jsonl" "$TMP/en.yaml"
t "default (no settings file): the zh-TW marker is what is checked" allow false "$TMP/in_flow_with_next.jsonl"

echo "== robustness: unreadable transcript, missing transcript_path - fail OPEN =="
out=$(python3 -c 'import json;print(json.dumps({"stop_hook_active":False,"transcript_path":"/no/such/file"}))' | bash "$H" 2>/dev/null)
printf '%-64s ' "an unreadable transcript never blocks"
[ -z "$out" ] && echo ok || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }

out=$(printf '{"stop_hook_active":false}' | bash "$H" 2>/dev/null)
printf '%-64s ' "no transcript_path at all never blocks"
[ -z "$out" ] && echo ok || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
