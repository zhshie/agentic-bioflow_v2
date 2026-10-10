#!/bin/bash
# #80: a gate hook that times out, crashes or prints something Claude Code cannot
# read is, by Claude Code's default, treated as "carry on": the command runs. The
# official switch is "onFailure": "block" on the hook entry (Claude Code >= 2.1.295).
# So every PreToolUse gate entry in hooks/hooks.json must carry it, and the
# hooks that are not gates (SessionStart, Stop, UserPromptSubmit, PostToolUse)
# must not: a failure there must not block a session or a prompt.
#
# main's shape is pinned below, not read from git history (the lesson of #71:
# a test that needs history breaks on a shallow clone).
#
# Test cases: .specify/bugs/hooks-fail-open-on-timeout/test-case.md
#   TC-001..007.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
J="$ROOT/hooks/hooks.json"
fails=0
command -v jq >/dev/null 2>&1 || { echo "jq is required for this test"; exit 1; }

ok()   { printf '%-78s ok\n' "$1"; }
bad()  { printf '%-78s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }
check() { # check <label> <jq filter that prints true/false>
  local got; got=$(jq -r "$2" "$J" 2>&1)
  if [ "$got" = true ]; then ok "$1"; else bad "$1" "got: ${got:0:120}"; fi
}

BASHM='Bash|.*[Ss]hell.*|.*[Pp]ower[Ss]hell.*|.*[Pp]wsh.*|.*[Tt]erminal.*|.*[Cc]md.*|.*[Ee]xec.*'
WRITEM='Write|Edit|MultiEdit|NotebookEdit'

# entries: PreToolUse as [matcher, script] pairs, in order
pre='[.hooks.PreToolUse[] as $g | $g.hooks[] | {m:$g.matcher, c:(.command|sub("^.*/hooks/";"")), h:.}]'

echo "== TC-007 shape equals main's =="
jq -e . "$J" >/dev/null 2>&1 && ok "TC-007 hooks.json is valid JSON" || bad "TC-007 hooks.json is valid JSON" "jq -e failed"
want=$(jq -nc --arg b "$BASHM" --arg w "$WRITEM" '[
  [$b,"confirm_launch.sh"],[$b,"confirm_cleanup.sh"],
  ["mcp__.*([Ss]eqera|[Tt]ower).*","confirm_launch.sh"],
  [$w,"confirm_launch.sh"],
  [$b,"guard_plugin_files.sh"],
  [$b+"|"+$w,"confirm_walkthrough.sh"],
  [$w,"guard_plugin_files.sh"]]')
check "TC-007 PreToolUse: 7 entries, same matcher and command, same order" \
  "($pre | map([.m,.c])) == $want"
check "TC-007 every entry is a command hook" \
  '[.hooks | to_entries[] | .value[] | .hooks[] | .type] | all(. == "command")'
check "TC-007 other events: same four entries as main" \
  '[.hooks | to_entries[] | select(.key != "PreToolUse") | .key as $k | .value[] | .matcher as $m | .hooks[] | [$k, ($m // ""), (.command|sub("^.*/hooks/";""))]]
   == [["SessionStart","","session_start.sh"],["Stop","","next_step.sh"],["UserPromptSubmit","","plugin_intro.sh"],["PostToolUse","Skill","plugin_intro.sh"]]'
check "TC-007 event set is exactly main's five" \
  '(.hooks | keys) == ["PostToolUse","PreToolUse","SessionStart","Stop","UserPromptSubmit"]'

echo "== TC-001..004 every PreToolUse gate entry blocks on failure =="
for s in confirm_launch.sh confirm_cleanup.sh guard_plugin_files.sh confirm_walkthrough.sh; do
  case $s in
    confirm_launch.sh)       tc=TC-001; n=3 ;;
    confirm_cleanup.sh)      tc=TC-002; n=1 ;;
    guard_plugin_files.sh)   tc=TC-003; n=2 ;;
    confirm_walkthrough.sh)  tc=TC-004; n=1 ;;
  esac
  check "$tc $s: $n entries, each with onFailure block" \
    "$pre | map(select(.c == \"$s\")) | (length == $n) and all(.h.onFailure == \"block\")"
done

echo "== TC-005 the other hooks do not block on failure =="
check "TC-005 no onFailure on SessionStart/Stop/UserPromptSubmit/PostToolUse" \
  '[.hooks | to_entries[] | select(.key != "PreToolUse") | .value[] | .hooks[] | has("onFailure")] | (length == 4) and all(. == false)'

echo "== TC-006 timeouts are kept =="
check "TC-006 every PreToolUse entry still has timeout 30" \
  "$pre | (length == 7) and all(.h.timeout == 30)"

echo
[ "$fails" -eq 0 ] && echo "ALL OK" || { echo "$fails FAILED"; exit 1; }
