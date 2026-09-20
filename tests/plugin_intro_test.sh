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
# marker (T3: also a distinct marker for the one flag plugin_intro.sh's own
# natural-language door uses, `--nudge`, so that path is exercised through
# the same stub rather than the real bilingual text - which is its own file's
# job, tests/intro_test.sh and tests/intro_languages_test.sh). The
# once-per-session marker lives under AGENTIC_BIOFLOW_STATE_DIR.
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
case "${1:-}" in
    "") echo "STUB-OVERVIEW-MARKER" ;;
    --banner) echo "STUB-BANNER-MARKER" ;;
    --nudge) echo "STUB-NUDGE-MARKER: load agentic-bioflow:operational" ;;
    *) exit 2 ;;
esac
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
       "$(prompt s1 '/agentic-bioflow:setup' | field .systemMessage)" STUB-BANNER-MARKER

# --- a typed command --------------------------------------------------------
OUT=$(prompt s2 '/agentic-bioflow:launch rnaseq')
expect "a typed command banners the load to the user"  "$(field .systemMessage <<<"$OUT")" STUB-BANNER-MARKER
expect "and gives the overview itself to the model"     "$(field .hookSpecificOutput.additionalContext <<<"$OUT")" STUB-OVERVIEW-MARKER
expect "told to print it first, verbatim, as Markdown"  "$(field .hookSpecificOutput.additionalContext <<<"$OUT")" "verbatim"
expect "declared as UserPromptSubmit"                   "$(field .hookSpecificOutput.hookEventName <<<"$OUT")" UserPromptSubmit
expect "leading whitespace still counts"                "$(prompt s3 '  /agentic-bioflow:runs' | field .systemMessage)" STUB-BANNER-MARKER

# --- once per session -------------------------------------------------------
expect "a second command in the same session says nothing" "$(prompt s2 '/agentic-bioflow:runs')" EMPTY
expect "nor does the skill loading afterwards"             "$(skill s2 'agentic-bioflow:runs')" EMPTY
expect "a different session is shown it again"             "$(prompt s4 '/agentic-bioflow:runs' | field .systemMessage)" STUB-BANNER-MARKER

# --- the model loading a skill (natural-language requests) ------------------
OUT=$(skill s5 'agentic-bioflow:operational')
expect "a loaded plugin skill banners the load"    "$(field .systemMessage <<<"$OUT")" STUB-BANNER-MARKER
expect "and hands the skill path the overview too" "$(field .hookSpecificOutput.additionalContext <<<"$OUT")" STUB-OVERVIEW-MARKER
expect "declared as PostToolUse"                   "$(field .hookSpecificOutput.hookEventName <<<"$OUT")" PostToolUse
expect "and only once"                             "$(skill s5 'agentic-bioflow:launch')" EMPTY
expect "a Bash call is not a skill"                "$(jq -nc '{session_id:"s6",hook_event_name:"PostToolUse",tool_name:"Bash",tool_input:{command:"agentic-bioflow:x"}}' | hook)" EMPTY

# --- PITFALLS 35: systemMessage must stay one line --------------------------
# A GUI surface renders this field one prompt-prefixed row per line, so any
# newline here is 26 rows of "PostToolUse:Skill says:" on the Claude app.
printf '%-60s ' "systemMessage is exactly one line"
lines=$(prompt s20 '/agentic-bioflow:setup' | field .systemMessage | wc -l | tr -d ' ')
[ "$lines" = 1 ] && echo ok || { echo "FAIL: systemMessage has $lines lines"; fails=$((fails+1)); }

printf '%-60s ' "a multi-line banner is still cut to one line"
cat > "$P/scripts/intro_multiline.sh" <<'EOS'
#!/bin/bash
case "${1:-}" in
    "") echo "STUB-OVERVIEW-MARKER" ;;
    --banner) printf 'STUB-BANNER-MARKER\nSECOND-LINE-MARKER\n' ;;
    *) exit 2 ;;
esac
EOS
cp "$P/scripts/intro.sh" "$P/scripts/intro_single.sh"
cp "$P/scripts/intro_multiline.sh" "$P/scripts/intro.sh"; chmod +x "$P/scripts/intro.sh"
out=$(prompt s21 '/agentic-bioflow:setup' | field .systemMessage)
{ [ "$(wc -l <<<"$out" | tr -d ' ')" = 1 ] && ! grep -qF SECOND-LINE-MARKER <<<"$out"; } \
  && echo ok || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }
cp "$P/scripts/intro_single.sh" "$P/scripts/intro.sh"; chmod +x "$P/scripts/intro.sh"

# --- never costs the user anything ------------------------------------------
printf '%-60s ' "no session_id: still shown, exit 0"
out=$(jq -nc '{hook_event_name:"UserPromptSubmit", prompt:"/agentic-bioflow:setup"}' | hook); rc=$?
[ "$rc" = 0 ] && grep -qF STUB-BANNER-MARKER <<<"$out" && grep -qF STUB-OVERVIEW-MARKER <<<"$out" && echo ok || { echo "FAIL rc=$rc <<$out>>"; fails=$((fails+1)); }

printf '%-60s ' "a session_id cannot write outside the state dir"
jq -nc '{session_id:"../../escape", hook_event_name:"UserPromptSubmit", prompt:"/agentic-bioflow:setup"}' | hook >/dev/null
[ ! -e "$TMP/escape" ] && [ ! -e "$STATE/../escape" ] && echo ok || { echo "FAIL: marker escaped"; fails=$((fails+1)); }

printf '%-60s ' "unwritable state dir: shown, exit 0"
out=$(jq -nc '{session_id:"s7", hook_event_name:"UserPromptSubmit", prompt:"/agentic-bioflow:setup"}' \
      | AGENTIC_BIOFLOW_STATE_DIR=/proc/nope bash "$P/hooks/plugin_intro.sh"); rc=$?
[ "$rc" = 0 ] && grep -qF STUB-BANNER-MARKER <<<"$out" && grep -qF STUB-OVERVIEW-MARKER <<<"$out" && echo ok || { echo "FAIL rc=$rc <<$out>>"; fails=$((fails+1)); }

printf '%-60s ' "broken intro.sh: silent, exit 0"
mv "$P/scripts/intro.sh" "$P/scripts/intro.sh.off"
out=$(prompt s8 '/agentic-bioflow:setup'); rc=$?
mv "$P/scripts/intro.sh.off" "$P/scripts/intro.sh"
[ "$rc" = 0 ] && [ -z "$out" ] && echo ok || { echo "FAIL rc=$rc <<$out>>"; fails=$((fails+1)); }
expect "and that failure did not use up the showing" "$(prompt s8 '/agentic-bioflow:setup' | field .systemMessage)" STUB-BANNER-MARKER

# T3: no jq used to mean total silence, in the one hook that could have said
# so - the safety-net gates (confirm_launch.sh etc.) already run degraded
# without jq, and nothing told anyone that was happening. It now exits 0
# (still never a gate) but SPEAKS UP once per session with a systemMessage,
# via plain printf rather than jq -n - the same reason the gates' own no-jq
# messages avoid jq to report jq's own absence.
NOJQ="$TMP/nojq"; mkdir -p "$NOJQ"
for t in bash cat mkdir tr sed grep find date rm; do p=$(command -v $t) && ln -s "$p" "$NOJQ/$t"; done

printf '%-60s ' "no jq, plugin-relevant prompt: warns (not silent), exit 0"
out=$(printf '{"session_id":"s9","prompt":"/agentic-bioflow:setup"}' \
      | env PATH="$NOJQ" AGENTIC_BIOFLOW_STATE_DIR="$STATE" bash "$P/hooks/plugin_intro.sh"); rc=$?
[ "$rc" = 0 ] && echo "$out" | grep -qF "jq is missing" && echo ok || { echo "FAIL rc=$rc <<$out>>"; fails=$((fails+1)); }

printf '%-60s ' "no jq, same session again: only warns once"
out=$(printf '{"session_id":"s9","prompt":"/agentic-bioflow:runs"}' \
      | env PATH="$NOJQ" AGENTIC_BIOFLOW_STATE_DIR="$STATE" bash "$P/hooks/plugin_intro.sh"); rc=$?
[ "$rc" = 0 ] && [ -z "$out" ] && echo ok || { echo "FAIL rc=$rc <<$out>>"; fails=$((fails+1)); }

printf '%-60s ' "no jq, a DIFFERENT session: warns again"
out=$(printf '{"session_id":"s10","prompt":"/agentic-bioflow:setup"}' \
      | env PATH="$NOJQ" AGENTIC_BIOFLOW_STATE_DIR="$STATE" bash "$P/hooks/plugin_intro.sh"); rc=$?
[ "$rc" = 0 ] && echo "$out" | grep -qF "jq is missing" && echo ok || { echo "FAIL rc=$rc <<$out>>"; fails=$((fails+1)); }

printf '%-60s ' "no jq, a prompt with nothing to do with this plugin: still silent"
out=$(printf '{"session_id":"s11","prompt":"fix my python script"}' \
      | env PATH="$NOJQ" AGENTIC_BIOFLOW_STATE_DIR="$STATE" bash "$P/hooks/plugin_intro.sh"); rc=$?
[ "$rc" = 0 ] && [ -z "$out" ] && echo ok || { echo "FAIL rc=$rc <<$out>>"; fails=$((fails+1)); }

echo
echo "== T3: natural-language routing (no literal 'agentic-bioflow:' anywhere) =="
# Two conditions, both required: a pipeline TOPIC and an ACTION verb. Either
# alone must not fire - a pure knowledge question ("what is RNA-seq") is left
# for the model to answer directly, not routed through the operational skill.
expect "topic + action (zh): nudges with additionalContext" \
       "$(prompt nl1 '幫我跑 RNA-seq 的分析' | field .hookSpecificOutput.additionalContext)" "agentic-bioflow:operational"
expect "and NOT as systemMessage - this is a quiet hint, not a banner" \
       "$(prompt nl1 '幫我跑 RNA-seq 的分析' | field .systemMessage)" EMPTY
expect "declared as UserPromptSubmit" \
       "$(prompt nl2 '幫我跑 RNA-seq 的分析' | field .hookSpecificOutput.hookEventName)" UserPromptSubmit
expect "topic + action (en): nudges too" \
       "$(prompt nl3 'please launch the nf-core rnaseq run')" "agentic-bioflow:operational"
expect "pure knowledge question, topic with no action: says nothing" \
       "$(prompt nl4 'RNAseq 是什麼？')" EMPTY
expect "action with no topic at all: says nothing" \
       "$(prompt nl5 '幫我跑一下這個腳本')" EMPTY
expect "why-did-it-fail phrasing (topic + action) nudges" \
       "$(prompt nl6 '這個 Seqera run 為什麼失敗了')" "agentic-bioflow:operational"
expect "the same nudge, once per session" \
       "$(prompt nl1 '再跑一次 RNA-seq')" EMPTY
expect "a different session is nudged again" \
       "$(prompt nl7 'launch the FASTQ samplesheet run')" "agentic-bioflow:operational"
expect "the LITERAL door still wins over the NL one for the same prompt shape" \
       "$(prompt nl8 '/agentic-bioflow:launch RNA-seq' | field .systemMessage)" STUB-BANNER-MARKER

echo
echo "== T3: the topic vocabulary stays pinned to SKILL.md's own trigger words =="
# PITFALLS 19: a justification that names another file's behaviour is a
# dependency, and nothing links them unless something checks it. This does
# not enforce the whole list stays identical - that would make the two files
# one file with extra steps - only that a handful of SKILL.md's own named
# triggers still appear somewhere in this hook's regex, so a future SKILL.md
# rewrite that drops "nf-core" or "FASTQ" turns this test red rather than
# leaving the hook quietly answering for words the skill no longer claims.
SKILL_MD="$ROOT/skills/operational/SKILL.md"
HOOK_SRC="$P/hooks/plugin_intro.sh"
for w in RNA-seq nf-core FASTQ samplesheet Seqera; do
  printf '%-60s ' "SKILL.md's '$w' is still in plugin_intro.sh's topic list"
  grep -qF -- "$w" "$SKILL_MD" && grep -qF -- "$w" "$HOOK_SRC" && echo ok || { echo FAIL; fails=$((fails+1)); }
done

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
