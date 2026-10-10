#!/bin/bash
# #80: with "onFailure": "block" on the gate hooks (hooks/hooks.json), Claude Code
# treats a gate that exits with anything but 0 or 2, prints stdout that is not
# valid hook JSON, or runs past its timeout as a failure and BLOCKS the call. So a
# gate that exited 1 by accident ("unbound variable" under set -u, a failed
# probe) used to be harmless noise and is now a command that cannot run. This
# test feeds the four gates (confirm_launch, confirm_cleanup, guard_plugin_files,
# confirm_walkthrough) ordinary and odd inputs and holds them to the contract:
#   exit 0 or 2; stdout empty or JSON with a valid decision; fast.
# A stub python3 that exits 9009 (the Windows Store stand-in) is first on PATH
# throughout: no gate may depend on python3.
#
# Test cases: .specify/bugs/hooks-fail-open-on-timeout/test-case.md
#   TC-010..015, TC-C02.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
HOOKS="$ROOT/hooks"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0
command -v jq >/dev/null 2>&1 || { echo "jq is required for this test"; exit 1; }

# Build the big inputs before the stub is in front of PATH.
big_cmd() { # 32 KB command: long cd target, long ../-heavy rm target
  local a r
  a=$(head -c 16000 /dev/zero | tr '\0' 'a'); r=$(printf '../%.0s' $(seq 1 4000))
  printf 'cd /tmp/%s; rm -rf %sx' "$a" "$r"
}
harmless_cmd() { # 32 KB, no delete or launch wording
  local i out=""; for i in $(seq 1 1000); do out="$out""echo line-$i-padding-padding-padding;"; done
  printf '%s' "$out"
}

DEP="$TMP/dep"; RUNS="$TMP/runs"; CFG_DEP="$TMP/cfg_dep"
mkdir -p "$DEP/config" "$RUNS/proj1" "$CFG_DEP/agentic-bioflow"
printf 'storage_root: %s\nreach: local\n' "$RUNS" > "$DEP/config/env.yaml"
printf '%s\n' "$DEP" > "$CFG_DEP/agentic-bioflow/root"
XDG_USE="$TMP/cfg_none"; HOME_MODE=set
mkdir -p "$TMP/stub" "$TMP/home" "$TMP/state/in-use" "$TMP/cfg_none" "$TMP/outside" "$TMP/work" "$TMP/plug/hooks" "$TMP/plug/scripts"
printf '#!/bin/sh\nexit 9009\n' > "$TMP/stub/python3"; cp "$TMP/stub/python3" "$TMP/stub/python"
chmod +x "$TMP/stub/python3" "$TMP/stub/python"
: > "$TMP/state/in-use/s-use"
: > "$TMP/transcript.jsonl"

now_ms() { if [ -n "${EPOCHREALTIME:-}" ]; then local e=${EPOCHREALTIME/[.,]/}; echo $((e / 1000)); else echo $((SECONDS * 1000)); fi; }

GATES="confirm_launch confirm_cleanup guard_plugin_files confirm_walkthrough"

# gate <hook> <input-file> <cwd>  -> RC OUT MS
gate() {
  local s e
  s=$(now_ms)
  local homearg="HOME=$TMP/home"; [ "$HOME_MODE" = unset ] && homearg="-u HOME"
  OUT=$( cd "$3" && env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u TOWER_WORKSPACE_ID -u TW_BIN -u OSTYPE $homearg \
      PATH="$TMP/stub:$PATH" XDG_CONFIG_HOME="$XDG_USE" \
      AGENTIC_BIOFLOW_STATE_DIR="$TMP/state" CLAUDE_PLUGIN_ROOT="$TMP/plug" SEQERA_TOKEN_FILE=/nonexistent \
      timeout 30 bash "$HOOKS/$1.sh" < "$2" 2>"$TMP/err" )
  RC=$?
  e=$(now_ms); MS=$((e - s))
}

# valid_out: stdout is empty or a JSON hook answer Claude Code accepts: a
# hookSpecificOutput with a valid permissionDecision, or with additionalContext
# only (what confirm_walkthrough prints for a step it lets through), or a
# top-level decision of approve/block.
valid_out() {
  [ -z "$OUT" ] && return 0
  jq -e '(.hookSpecificOutput // null) as $h
         | if $h != null then
             (($h.permissionDecision // "") as $p
              | if $p != "" then ($p|IN("allow","ask","deny","defer"))
                else (($h.additionalContext // "") | type == "string" and length > 0) end)
           else ((.decision // "") | IN("approve","block")) end' <<<"$OUT" >/dev/null 2>&1
}

verify() { # verify <label> <hook> <maxms> <require-silent 0|1>   (uses last gate run)
  local label="$1" hook="$2" max="$3" silent="$4" why=""
  case $RC in 0|2) ;; *) why="exit $RC" ;; esac
  valid_out || why="$why stdout not valid hook JSON: ${OUT:0:80}"
  [ "$MS" -le "$max" ] || why="$why took ${MS}ms (> ${max}ms)"
  if [ "$silent" = 1 ]; then { [ "$RC" = 0 ] && [ -z "$OUT" ]; } || why="$why not silent (rc=$RC)"; fi
  if [ -z "$why" ]; then printf '%-78s ok\n' "$label [$hook]"; else
    printf '%-78s FAIL:%s\n' "$label [$hook]" "$why"; fails=$((fails+1)); fi
}

# --- inputs ----------------------------------------------------------------
mkin() { # mkin <name> <jq program> [jq args...]
  local n="$1" prog="$2"; shift 2
  jq -nc "$@" "$prog" > "$TMP/in_$n.json"
}
A=(--arg c "$TMP/work" --arg t "$TMP/transcript.jsonl")
mkin ls    '{session_id:"s-use",cwd:$c,transcript_path:$t,hook_event_name:"PreToolUse",tool_name:"Bash",tool_input:{command:"ls"}}' "${A[@]}"
mkin gitst '{session_id:"s-use",cwd:$c,transcript_path:$t,tool_name:"Bash",tool_input:{command:"git status"}}' "${A[@]}"
mkin cat   '{session_id:"s-use",cwd:$c,transcript_path:$t,tool_name:"Bash",tool_input:{command:"cat notes.txt"}}' "${A[@]}"
mkin echo  '{session_id:"s-use",cwd:$c,transcript_path:$t,tool_name:"Bash",tool_input:{command:"echo hi"}}' "${A[@]}"
mkin write '{session_id:"s-use",cwd:$c,transcript_path:$t,tool_name:"Write",tool_input:{file_path:($c+"/notes.txt"),content:"hello\n"}}' "${A[@]}"
mkin edit  '{session_id:"s-use",cwd:$c,transcript_path:$t,tool_name:"Edit",tool_input:{file_path:($c+"/notes.txt"),old_string:"a",new_string:"b"}}' "${A[@]}"
mkin mcp   '{session_id:"s-use",cwd:$c,transcript_path:$t,tool_name:"mcp__other__lookup",tool_input:{q:"x"}}' "${A[@]}"
ORDINARY="ls gitst cat echo write edit mcp"

printf '' > "$TMP/in_empty.json"
printf '{}' > "$TMP/in_obj.json"
printf '{"session_id":"s-use","cwd":"%s","tool_name":"Bash"}' "$TMP/work" > "$TMP/in_noti.json"
printf '{"cwd":"%s","tool_name":"Bash","tool_input":{"command":"ls"}}' "$TMP/work" > "$TMP/in_nosid.json"
printf '{"cwd":"%s","tool_name":"Write","tool_input":{"file_path":"/x/y","content":"z"}}' "$TMP/work" > "$TMP/in_nosid_w.json"
printf 'this is not json at all <<<' > "$TMP/in_text.json"
printf '{"session_id":"s-use","cwd":"%s","tool_name":"Bash","tool_input":42}' "$TMP/work" > "$TMP/in_num.json"
printf '{"session_id":"s-use","tool_name":"Bash","tool_input":{"command":"ls"}}' > "$TMP/in_nocwd.json"
printf '{"session_id":"s-use","tool_name":"Bash","tool_input":null}' > "$TMP/in_tinull.json"
printf '{"session_id":"s-use","tool_name":"Bash","tool_input":[1,2]}' > "$TMP/in_tiarr.json"
printf '{"session_id":"s-use","tool_name":"Bash","tool_input":{"command":42}}' > "$TMP/in_cmdnum.json"
printf '{"session_id":"s-use","tool_name":"Write","tool_input":{"file_path":null,"content":null}}' > "$TMP/in_wnull.json"
printf '{"session_id":"s-use","tool_input":{"command":"ls"}}' > "$TMP/in_notool.json"
printf '{"session_id":7,"cwd":"%s","tool_name":"Bash","tool_input":{"command":"ls"}}' "$TMP/work" > "$TMP/in_sidnum.json"
printf '{"session_id":"s-use","cwd":"/nonexistent/dir","tool_name":"Bash","tool_input":{"command":"ls"}}' > "$TMP/in_badcwd.json"
printf '{"session_id":"s-use","transcript_path":"/nonexistent","tool_name":"Write","tool_input":{"file_path":"/a/b","content":"x"}}' > "$TMP/in_badtr.json"
printf '[1,2]' > "$TMP/in_arr.json"
printf 'null' > "$TMP/in_null.json"
ODD="empty obj noti nosid nosid_w text num nocwd tinull tiarr cmdnum wnull notool sidnum badcwd badtr arr null"

echo "== TC-010/011/C02 ordinary calls, in use, python3 stub in front =="
for g in $GATES; do for n in $ORDINARY; do
  gate "$g" "$TMP/in_$n.json" "$TMP/work"; verify "TC-010/011/C02 $n" "$g" 10000 0
done; done

echo "== TC-012/013 odd inputs =="
for g in $GATES; do for n in $ODD; do
  gate "$g" "$TMP/in_$n.json" "$TMP/work"; verify "TC-012/013 $n" "$g" 10000 0
done; done

echo "== TC-014 not in use: a 32 KB command is answered quickly and silently =="
big_cmd > "$TMP/big_cmd.txt"; harmless_cmd > "$TMP/harm_cmd.txt"
echo "   (32 KB inputs: $(wc -c < "$TMP/big_cmd.txt") and $(wc -c < "$TMP/harm_cmd.txt") bytes)"
B=(--arg c "$TMP/outside" --arg t "$TMP/transcript.jsonl")
mkin out_big '{session_id:"s-out",cwd:$c,transcript_path:$t,tool_name:"Bash",tool_input:{command:$x}}' "${B[@]}" --rawfile x "$TMP/big_cmd.txt"
mkin out_ord '{session_id:"s-out",cwd:$c,transcript_path:$t,tool_name:"Bash",tool_input:{command:"ls"}}' "${B[@]}"
for g in $GATES; do
  gate "$g" "$TMP/in_out_ord.json" "$TMP/outside"; verify "TC-014 not in use: ls is silent" "$g" 5000 1
  gate "$g" "$TMP/in_out_big.json" "$TMP/outside"; verify "TC-014 not in use: 32 KB rm/cd command is silent" "$g" 5000 1
done

echo "== TC-015 in use: 1 MB Write and a 32 KB harmless command finish in 10 s =="
head -c 1048576 /dev/zero | tr '\0' 'x' | fold -w 100 > "$TMP/mb.txt"
mkin mb   '{session_id:"s-use",cwd:$c,transcript_path:$t,tool_name:"Write",tool_input:{file_path:($c+"/big.txt"),content:$x}}' "${A[@]}" --rawfile x "$TMP/mb.txt"
mkin harm '{session_id:"s-use",cwd:$c,transcript_path:$t,tool_name:"Bash",tool_input:{command:$x}}' "${A[@]}" --rawfile x "$TMP/harm_cmd.txt"
for g in $GATES; do
  gate "$g" "$TMP/in_mb.json" "$TMP/work"; verify "TC-015 1 MB Write" "$g" 10000 0
  gate "$g" "$TMP/in_harm.json" "$TMP/work"; verify "TC-015 32 KB harmless command" "$g" 10000 0
done

echo "== TC-010/012 again through a real deployment lookup, HOME and OSTYPE unset =="
# A deployment exists (XDG_CONFIG_HOME points at a root file), so hooks/in_use.sh
# runs its base/cwd comparison loops. An empty-array expansion there is fatal on
# bash 3.2 under set -u. Modes: deployment+HOME set, deployment+HOME unset,
# no deployment+HOME unset. The session's cwd is outside the deployment, inside it,
# and unreadable.
for mode in "dep set" "dep unset" "none unset"; do
  set -- $mode
  if [ "$1" = dep ]; then XDG_USE="$CFG_DEP"; else XDG_USE="$TMP/cfg_none"; fi
  HOME_MODE=$2
  for n in $ORDINARY; do
    jq -c --arg c "$RUNS/proj1" '.cwd = $c' "$TMP/in_$n.json" > "$TMP/in_${n}_inside.json"
    jq -c --arg c "$TMP/outside" '.cwd = $c | .session_id = "s-other"' "$TMP/in_$n.json" > "$TMP/in_${n}_outside.json"
  done
  for g in $GATES; do
    for n in $ORDINARY; do
      gate "$g" "$TMP/in_$n.json" "$TMP/work"; verify "TC-010 [$mode] $n" "$g" 10000 0
      gate "$g" "$TMP/in_${n}_inside.json" "$RUNS/proj1"; verify "TC-010 [$mode] $n, cwd inside deployment" "$g" 10000 0
      gate "$g" "$TMP/in_${n}_outside.json" "$TMP/outside"; verify "TC-010 [$mode] $n, cwd outside" "$g" 10000 0
    done
    for n in $ODD; do
      gate "$g" "$TMP/in_$n.json" "$TMP/work"; verify "TC-012 [$mode] $n" "$g" 10000 0
    done
  done
done
XDG_USE="$TMP/cfg_none"; HOME_MODE=set

echo
[ "$fails" -eq 0 ] && echo "ALL OK" || { echo "$fails FAILED"; exit 1; }
