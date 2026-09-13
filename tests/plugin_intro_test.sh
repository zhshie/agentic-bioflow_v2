#!/bin/bash
# Regression tests for hooks/plugin_intro.sh.
#
# The overview used to be shown at every session start, in every project,
# whether or not the user ever touched this plugin. It now appears when the
# plugin is actually used - a `/agentic-bioflow:` command typed by the user, or
# the model successfully loading one of the plugin's skills - and once per
# session. Both halves are tested: it must speak then, and be silent otherwise.
#
# The wording of scripts/intro.sh is not under test here, only the wiring: a
# copy of the plugin root with the real hook and a stub intro.sh printing one
# marker. The once-per-session marker lives under AGENTIC_BIOFLOW_STATE_DIR.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0

P="$TMP/plugin"
mkdir -p "$P/hooks" "$P/scripts"
cp "$ROOT/hooks/plugin_intro.sh" "$P/hooks/" 2>/dev/null
cat > "$P/scripts/intro.sh" <<'EOF'
#!/bin/bash
[ $# -eq 0 ] || exit 2
echo "STUB-OVERVIEW-MARKER"
EOF
chmod +x "$P/scripts/intro.sh"
STATE="$TMP/state"

hook() { AGENTIC_BIOFLOW_STATE_DIR="$STATE" bash "$P/hooks/plugin_intro.sh"; }

prompt() { # prompt <session> <text>
  jq -nc --arg s "$1" --arg p "$2" \
    '{session_id:$s, hook_event_name:"UserPromptSubmit", prompt:$p}' | hook
}
skill() { # skill <session> <skill-name> [args]
  jq -nc --arg s "$1" --arg k "$2" --arg a "${3:-}" \
    '{session_id:$s, hook_event_name:"PostToolUse", tool_name:"Skill", tool_input:{skill:$k, args:$a}}' | hook
}

field() { jq -r "$1 // empty" 2>/dev/null; }

expect() { # expect <label> <actual> <needle-or-EMPTY>
  printf '%-60s ' "$1"
  if [ "$3" = EMPTY ]; then
    [ -z "$2" ] && echo ok || { echo "FAIL: expected nothing, got <<$2>>"; fails=$((fails+1)); }
  else
    grep -qF -- "$3" <<<"$2" && echo ok || { echo "FAIL: expected $3 in <<$2>>"; fails=$((fails+1)); }
  fi
}

# --- silent where the plugin is not being used ------------------------------
expect "an ordinary prompt says nothing"          "$(prompt s1 'fix my python script')" EMPTY
expect "mentioning the name mid-sentence says nothing" \
       "$(prompt s1 'what does /agentic-bioflow:setup do?')" EMPTY
expect "another plugin's command says nothing"    "$(prompt s1 '/other-plugin:setup')" EMPTY
expect "another plugin's skill says nothing"      "$(skill s1 'superpowers:brainstorming')" EMPTY
expect "even when its arguments name this plugin" "$(skill s1 'superpowers:brainstorming' 'plan agentic-bioflow:launch')" EMPTY
expect "and none of that used up the session's one showing" \
       "$(prompt s1 '/agentic-bioflow:setup' | field .systemMessage)" STUB-OVERVIEW-MARKER

# --- a typed command --------------------------------------------------------
OUT=$(prompt s2 '/agentic-bioflow:launch rnaseq')
expect "a typed command shows the overview to the user" "$(field .systemMessage <<<"$OUT")" STUB-OVERVIEW-MARKER
expect "and gives it to the model"                      "$(field .hookSpecificOutput.additionalContext <<<"$OUT")" STUB-OVERVIEW-MARKER
expect "declared as UserPromptSubmit"                   "$(field .hookSpecificOutput.hookEventName <<<"$OUT")" UserPromptSubmit
expect "leading whitespace still counts"                "$(prompt s3 '  /agentic-bioflow:runs' | field .systemMessage)" STUB-OVERVIEW-MARKER

# --- once per session -------------------------------------------------------
expect "a second command in the same session says nothing" "$(prompt s2 '/agentic-bioflow:runs')" EMPTY
expect "nor does the skill loading afterwards"             "$(skill s2 'agentic-bioflow:runs')" EMPTY
expect "a different session is shown it again"             "$(prompt s4 '/agentic-bioflow:runs' | field .systemMessage)" STUB-OVERVIEW-MARKER

# --- the model loading a skill (natural-language requests) ------------------
OUT=$(skill s5 'agentic-bioflow:operational')
expect "a loaded plugin skill shows the overview"  "$(field .systemMessage <<<"$OUT")" STUB-OVERVIEW-MARKER
expect "declared as PostToolUse"                   "$(field .hookSpecificOutput.hookEventName <<<"$OUT")" PostToolUse
expect "and only once"                             "$(skill s5 'agentic-bioflow:launch')" EMPTY
expect "a Bash call is not a skill"                "$(jq -nc '{session_id:"s6",hook_event_name:"PostToolUse",tool_name:"Bash",tool_input:{command:"agentic-bioflow:x"}}' | hook)" EMPTY

# --- never costs the user anything ------------------------------------------
printf '%-60s ' "no session_id: still shown, exit 0"
out=$(jq -nc '{hook_event_name:"UserPromptSubmit", prompt:"/agentic-bioflow:setup"}' | hook); rc=$?
[ "$rc" = 0 ] && grep -qF STUB-OVERVIEW-MARKER <<<"$out" && echo ok || { echo "FAIL rc=$rc <<$out>>"; fails=$((fails+1)); }

printf '%-60s ' "a session_id cannot write outside the state dir"
jq -nc '{session_id:"../../escape", hook_event_name:"UserPromptSubmit", prompt:"/agentic-bioflow:setup"}' | hook >/dev/null
[ ! -e "$TMP/escape" ] && [ ! -e "$STATE/../escape" ] && echo ok || { echo "FAIL: marker escaped"; fails=$((fails+1)); }

printf '%-60s ' "unwritable state dir: shown, exit 0"
out=$(jq -nc '{session_id:"s7", hook_event_name:"UserPromptSubmit", prompt:"/agentic-bioflow:setup"}' \
      | AGENTIC_BIOFLOW_STATE_DIR=/proc/nope bash "$P/hooks/plugin_intro.sh"); rc=$?
[ "$rc" = 0 ] && grep -qF STUB-OVERVIEW-MARKER <<<"$out" && echo ok || { echo "FAIL rc=$rc <<$out>>"; fails=$((fails+1)); }

printf '%-60s ' "broken intro.sh: silent, exit 0"
mv "$P/scripts/intro.sh" "$P/scripts/intro.sh.off"
out=$(prompt s8 '/agentic-bioflow:setup'); rc=$?
mv "$P/scripts/intro.sh.off" "$P/scripts/intro.sh"
[ "$rc" = 0 ] && [ -z "$out" ] && echo ok || { echo "FAIL rc=$rc <<$out>>"; fails=$((fails+1)); }
expect "and that failure did not use up the showing" "$(prompt s8 '/agentic-bioflow:setup' | field .systemMessage)" STUB-OVERVIEW-MARKER

printf '%-60s ' "no jq on PATH: silent, exit 0 (not a gate)"
NOJQ="$TMP/nojq"; mkdir -p "$NOJQ"
for t in bash cat mkdir tr sed grep find date rm; do p=$(command -v $t) && ln -s "$p" "$NOJQ/$t"; done
out=$(printf '{"session_id":"s9","prompt":"/agentic-bioflow:setup"}' \
      | env PATH="$NOJQ" AGENTIC_BIOFLOW_STATE_DIR="$STATE" bash "$P/hooks/plugin_intro.sh"); rc=$?
[ "$rc" = 0 ] && [ -z "$out" ] && echo ok || { echo "FAIL rc=$rc <<$out>>"; fails=$((fails+1)); }

# --- wiring -----------------------------------------------------------------
HJ="$ROOT/hooks/hooks.json"
printf '%-60s ' "hooks.json runs it on UserPromptSubmit"
jq -e '.hooks.UserPromptSubmit[]?.hooks[]? | select(.command|test("plugin_intro.sh"))' "$HJ" >/dev/null \
  && echo ok || { echo FAIL; fails=$((fails+1)); }
printf '%-60s ' "and on PostToolUse for Skill"
jq -e '.hooks.PostToolUse[]? | select(.matcher=="Skill") | .hooks[] | select(.command|test("plugin_intro.sh"))' "$HJ" >/dev/null \
  && echo ok || { echo FAIL; fails=$((fails+1)); }
printf '%-60s ' "SessionStart no longer shows the overview"
grep -v '^[[:space:]]*#' "$ROOT/hooks/session_start.sh" | grep -q 'scripts/intro\.sh' && { echo "FAIL: session_start.sh still calls intro.sh"; fails=$((fails+1)); } || echo ok

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
