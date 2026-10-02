#!/bin/bash
# Feature 005 (#48): when agentic-bioflow is not in use, the plugin is silent.
#
# Every hook asks hooks/in_use.sh "is this plugin in use for this call?" first
# and exits 0 with no output when the answer is no. In use means ANY of:
#   1. this session left a marker (plugin_intro.sh writes one when the plugin is
#      first used: a typed /agentic-bioflow: command, a Skill load, or the
#      natural-language door);
#   2. the session's cwd is under the deployment root or its storage_root;
#   3. the call itself runs a plugin script, `tw`, or a Seqera/Tower MCP tool.
# Unsure (no session id, an unreadable state directory) counts as in use.
#
# An "in use" assertion alone would also pass on the old code, which gates
# everything always. So every in-use case is paired with a control, in the same
# session and cwd, that differs only in the one fact under test; the control is
# the half that fails without the feature.
#
# Test cases: specs/005-plugin-scope/test-case.md (TC numbers in the labels).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
HOOKS="$ROOT/hooks"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0

command -v jq >/dev/null 2>&1 || { echo "jq is required for this test"; exit 1; }

# --- a deployment, and a machine with none ---------------------------------
DEP="$TMP/dep"                       # the deployment root
RUNS="$TMP/runs"                     # storage_root
mkdir -p "$DEP/config" "$DEP/projects/p1" "$RUNS/proj1" "$TMP/elsewhere" "$TMP/home"
printf 'storage_root: %s\nreach: local\n' "$RUNS" > "$DEP/config/env.yaml"
CFG_DEP="$TMP/cfg_dep"; mkdir -p "$CFG_DEP/agentic-bioflow"
printf '%s\n' "$DEP" > "$CFG_DEP/agentic-bioflow/root"
CFG_NONE="$TMP/cfg_none"; mkdir -p "$CFG_NONE"
STATE="$TMP/state"
OUTSIDE="$TMP/elsewhere"

# A fake `uname -s` that says MSYS, the way tests/confirm_launch_test.sh does:
# D3 (the direct-ssh reminder) only runs there.
MSYSBIN="$TMP/msysbin"; mkdir -p "$MSYSBIN"
cat > "$MSYSBIN/uname" <<'EOF'
#!/bin/bash
[ "$1" = -s ] && { echo MINGW64_NT-10.0-22631; exit 0; }
exec /usr/bin/uname "$@"
EOF
chmod +x "$MSYSBIN/uname"

# run <hook> <json> [VAR=val ...]  ->  OUT (stdout), RC, ERR
run() {
  local hook="$1" json="$2"; shift 2
  OUT=$(cd "${RUNCWD:-.}" && printf '%s' "$json" | env -u LAB_SETTINGS_FILE -u CLAUDE_PLUGIN_ROOT -u LAB_RUNS_DIR \
        -u XDG_STATE_HOME -u TOWER_WORKSPACE_ID -u TW_BIN \
        HOME="$TMP/home" XDG_CONFIG_HOME="$CFG_DEP" AGENTIC_BIOFLOW_STATE_DIR="$STATE" \
        SEQERA_TOKEN_FILE=/nonexistent "$@" bash "$HOOKS/$hook" 2>"$TMP/err")
  RC=$?
  ERR=$(cat "$TMP/err" 2>/dev/null)
}

# What the hook said, as one word: silent | ask | deny | block | exit2 | other
verdict() {
  if [ "$RC" = 2 ]; then echo exit2; return; fi
  if [ -z "$OUT" ]; then echo silent; return; fi
  local d
  d=$(jq -r '.hookSpecificOutput.permissionDecision // .decision // empty' <<<"$OUT" 2>/dev/null)
  echo "${d:-other}"
}

check() { # check <label> <expected-verdict-regex> [VAR=val ...]   (uses last run)
  local label="$1" want="$2" got
  got=$(verdict)
  printf '%-72s ' "$label"
  if [[ $got =~ ^($want)$ ]]; then echo "ok ($got)"; else
    echo "FAIL: expected $want, got $got  <<${OUT:0:120}>>"; fails=$((fails+1))
  fi
}

# --- inputs ----------------------------------------------------------------
bash_in() { # bash_in <sid|""> <cwd> <command> [extra-json]
  jq -nc --arg s "$1" --arg d "$2" --arg c "$3" --argjson x "${4:-{\}}" \
    '(if $s != "" then {session_id:$s} else {} end) + {cwd:$d, hook_event_name:"PreToolUse", tool_name:"Bash", tool_input:{command:$c}} + $x'
}
file_in() { # file_in <sid|""> <cwd> <tool> <path>
  jq -nc --arg s "$1" --arg d "$2" --arg t "$3" --arg p "$4" \
    '(if $s != "" then {session_id:$s} else {} end) + {cwd:$d, hook_event_name:"PreToolUse", tool_name:$t, tool_input:{file_path:$p}}'
}
mark() { mkdir -p "$STATE/in-use"; : > "$STATE/in-use/$1"; }

RM='rm -rf results/'
RMW='rm -rf work/'
LAUNCH='tw launch nf-core/rnaseq --disable-optimization'
RELAUNCH='tw runs relaunch -i abc123'
CASE_CMD="wsl.exe -e ssh -o ControlPath=/tmp/cm-%C -o BatchMode=yes u@login-node 'scontrol show partition; sacctmgr show qos'"

echo "== US1: not in use - every hook is silent =="
# TC-001 (and the exact incident, #48)
run confirm_launch.sh "$(bash_in s-out "$OUTSIDE" "$CASE_CMD")" PATH="$MSYSBIN:$PATH"
check "TC-001 the incident command is not stopped (MSYS, not in use)"  silent
run confirm_launch.sh "$(bash_in s-out "$OUTSIDE" "$CASE_CMD")" XDG_CONFIG_HOME="$CFG_NONE" PATH="$MSYSBIN:$PATH"
check "TC-001 ...same on a machine with no deployment at all"          silent
# TC-002
for c in "ssh u@host 'ls'" "scp a u@host:b" "rsync -a a u@host:b"; do
  run confirm_launch.sh "$(bash_in s-out "$OUTSIDE" "$c")" PATH="$MSYSBIN:$PATH"
  check "TC-002 direct transport not stopped: ${c:0:34}"                silent
done
# TC-003
run confirm_cleanup.sh "$(bash_in s-out "$OUTSIDE" "$RM")"
check "TC-003 deleting results/ is not refused"                         silent
run confirm_cleanup.sh "$(bash_in s-out "$OUTSIDE" "$RMW")"
check "TC-003 clearing work/ is not asked"                              silent
run confirm_launch.sh "$(bash_in s-out "$OUTSIDE" "sbatch x.sh")"
check "TC-003 a direct sbatch is not asked"                             silent
run confirm_launch.sh "$(bash_in s-out "$OUTSIDE" "nextflow run nf-core/rnaseq")"
check "TC-003 a direct nextflow run is not asked"                       silent
# TC-004
: > "$TMP/empty.jsonl"
J=$(jq -nc --arg s s-out --arg d "$OUTSIDE" --arg t "$TMP/empty.jsonl" \
  '{session_id:$s, cwd:$d, transcript_path:$t, tool_name:"Write", tool_input:{file_path:"/r/samplesheet.csv"}}')
run confirm_walkthrough.sh "$J"
check "TC-004 writing a samplesheet is not gated (walkthrough)"         silent
PLUG="$TMP/plugin_root"; mkdir -p "$PLUG/hooks" "$PLUG/scripts"
run guard_plugin_files.sh "$(file_in s-out "$OUTSIDE" Write "$OUTSIDE/notes.txt")" CLAUDE_PLUGIN_ROOT="$PLUG"
check "TC-004 writing an ordinary file is not refused (guard)"          silent
# Naming the plugin's own install directory is condition 3 (the call is about
# the plugin), so the guard that protects that directory still fires - from any
# session, in use or not. This is the one place "not in use" does not mean the
# guard is off, and it is deliberate (fail-safe: the install is overwritten on
# update and edits there are lost).
run guard_plugin_files.sh "$(file_in s-out "$OUTSIDE" Write "$PLUG/hooks/x.sh")" CLAUDE_PLUGIN_ROOT="$PLUG"
check "TC-004 ...but a write into the plugin's own install dir is refused" deny
run guard_plugin_files.sh "$(bash_in s-out "$OUTSIDE" 'echo x > "$CLAUDE_PLUGIN_ROOT/hooks/x.sh"')" CLAUDE_PLUGIN_ROOT="$PLUG"
check "TC-004 ...also when the command spells the root as the variable"  deny
# TC-005
J=$(jq -nc --arg s s-out --arg d "$OUTSIDE" '{session_id:$s, cwd:$d, hook_event_name:"SessionStart"}')
run session_start.sh "$J"
check "TC-005 session start adds nothing (deployment exists, cwd outside)" silent
python3 - "$TMP/flow.jsonl" <<'PY'
import json, sys
with open(sys.argv[1], "w") as f:
    for rec in ({"type": "assistant", "message": {"content": [
                  {"type": "tool_use", "name": "Bash", "input": {"command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/intro.sh launch"}}]}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "Here is the plan."}]}}):
        f.write(json.dumps(rec) + "\n")
PY
STOPJ() { jq -nc --arg s "$1" --arg d "$2" --arg t "$TMP/flow.jsonl" \
  '(if $s != "" then {session_id:$s} else {} end) + {cwd:$d, hook_event_name:"Stop", stop_hook_active:false, transcript_path:$t}'; }
run next_step.sh "$(STOPJ s-out "$OUTSIDE")"
check "TC-005 Stop adds no next-step reminder"                          silent
# TC-006: a subagent call carries the parent's session id plus agent fields
run confirm_launch.sh "$(bash_in s-out "$OUTSIDE" "$CASE_CMD" '{"agent_id":"a1","agent_type":"general-purpose"}')" PATH="$MSYSBIN:$PATH"
check "TC-006 a subagent of a not-in-use session is not stopped"        silent
mark s-used
run confirm_launch.sh "$(bash_in s-used "$OUTSIDE" "sbatch x.sh" '{"agent_id":"a1","agent_type":"general-purpose"}')"
check "TC-006 ...but a subagent of a session that used the plugin is"   ask

echo
echo "== US2: in use - the safety net is as before (each paired with a control) =="
# TC-007: the marker comes from plugin_intro.sh itself
P="$TMP/plugin"; mkdir -p "$P/hooks" "$P/scripts"
cp "$HOOKS/plugin_intro.sh" "$P/hooks/"
printf '#!/bin/bash\necho STUB\n' > "$P/scripts/intro.sh"; chmod +x "$P/scripts/intro.sh"
intro() { printf '%s' "$1" | AGENTIC_BIOFLOW_STATE_DIR="$STATE" bash "$P/hooks/plugin_intro.sh" >/dev/null 2>&1; }
intro "$(jq -nc '{session_id:"s-typed", hook_event_name:"UserPromptSubmit", prompt:"/agentic-bioflow:launch rnaseq"}')"
printf '%-72s ' "TC-007 a typed command leaves the in-use marker"
[ -e "$STATE/in-use/s-typed" ] && echo ok || { echo "FAIL: no $STATE/in-use/s-typed"; fails=$((fails+1)); }
run confirm_launch.sh "$(bash_in s-typed "$OUTSIDE" "$LAUNCH")"
check "TC-007 then tw launch asks"                                      ask
printf '%-72s ' "TC-007 ...and the reason shows the full command"
case "$OUT" in *"$LAUNCH"*) echo ok ;; *) echo "FAIL <<${OUT:0:100}>>"; fails=$((fails+1)) ;; esac
run confirm_launch.sh "$(bash_in s-typed "$OUTSIDE" "sbatch x.sh")"
check "TC-007 the marker alone is enough: sbatch (no tw) asks"          ask
run confirm_launch.sh "$(bash_in s-other "$OUTSIDE" "sbatch x.sh")"
check "TC-007 control: another session, same cwd, sbatch is silent"     silent
# TC-008: the marker also comes from loading a plugin skill
intro "$(jq -nc '{session_id:"s-skill", hook_event_name:"PostToolUse", tool_name:"Skill", tool_input:{skill:"agentic-bioflow:launch"}}')"
printf '%-72s ' "TC-008 a plugin skill load leaves the in-use marker"
[ -e "$STATE/in-use/s-skill" ] && echo ok || { echo "FAIL: no $STATE/in-use/s-skill"; fails=$((fails+1)); }
run confirm_cleanup.sh "$(bash_in s-skill "$OUTSIDE" "$RM")"
check "TC-008 after a skill load, deleting results/ is refused"         deny
printf '%-72s ' "TC-008 control: another skill's load leaves no marker"
intro "$(jq -nc '{session_id:"s-skill2", hook_event_name:"PostToolUse", tool_name:"Skill", tool_input:{skill:"superpowers:brainstorming"}}')"
[ ! -e "$STATE/in-use/s-skill2" ] && echo ok || { echo FAIL; fails=$((fails+1)); }
# the natural-language door, and the doors that must stay shut
intro "$(jq -nc '{session_id:"s-nl", hook_event_name:"UserPromptSubmit", prompt:"please run the RNA-seq analysis on these FASTQ files"}')"
printf '%-72s ' "TC-008 a natural-language request for a pipeline leaves the marker"
[ -e "$STATE/in-use/s-nl" ] && echo ok || { echo FAIL; fails=$((fails+1)); }
intro "$(jq -nc '{session_id:"s-chat", hook_event_name:"UserPromptSubmit", prompt:"fix my python script"}')"
printf '%-72s ' "TC-008 control: an ordinary prompt leaves none"
[ ! -e "$STATE/in-use/s-chat" ] && echo ok || { echo FAIL; fails=$((fails+1)); }
# M2 (acceptance): a prompt that names the command anywhere reaches for the
# plugin; the overview needs it first, the marker does not (unsure = in use).
intro "$(jq -nc '{session_id:"s-ment", hook_event_name:"UserPromptSubmit", prompt:"what does /agentic-bioflow:setup do?"}')"
intro "$(jq -nc '{session_id:"s-mid", hook_event_name:"UserPromptSubmit", prompt:"please run the RNA-seq FASTQ with /agentic-bioflow:launch"}')"
printf '%-72s ' "M2 a mid-sentence /agentic-bioflow: mention leaves the marker"
[ -e "$STATE/in-use/s-ment" ] && echo ok || { echo FAIL; fails=$((fails+1)); }
printf '%-72s ' "M2 ...also with a pipeline topic and action in the same prompt"
[ -e "$STATE/in-use/s-mid" ] && echo ok || { echo FAIL; fails=$((fails+1)); }
# a session that was shown the overview before this version existed is in use
mkdir -p "$STATE/intro-shown"; : > "$STATE/intro-shown/s-old"
run confirm_cleanup.sh "$(bash_in s-old "$OUTSIDE" "$RM")"
check "TC-008 a session whose overview was already shown is in use"     deny

# TC-009 / TC-010: the folder
run confirm_cleanup.sh "$(bash_in s-new "$RUNS/proj1" "$RM")"
check "TC-009 cwd under storage_root: deleting results/ is refused"     deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "$RM")"
check "TC-009 control: same session, cwd elsewhere: silent"             silent
run confirm_cleanup.sh "$(bash_in s-new "$DEP/projects/p1" "$RMW")"
check "TC-010 cwd under the deployment root: clearing work/ asks"       ask
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "$RMW")"
check "TC-010 control: same session, cwd elsewhere: silent"             silent
run confirm_cleanup.sh "$(bash_in s-new "$DEP" "$RM")"
check "TC-010 cwd exactly the deployment root counts"                   deny
run confirm_cleanup.sh "$(bash_in s-new "${DEP}-neighbour" "$RM")"
check "TC-010 control: a sibling folder sharing the name prefix does not" silent
# a Windows-style cwd against a root written the Git Bash way
WDEP="/c/Users/zz/abf-root"; WCFG="$TMP/cfg_win"; mkdir -p "$WCFG/agentic-bioflow"
printf '%s\n' "$WDEP" > "$WCFG/agentic-bioflow/root"
run confirm_cleanup.sh "$(bash_in s-new 'C:\Users\zz\abf-root\projects\p' "$RM")" XDG_CONFIG_HOME="$WCFG"
check "TC-010 a C:\\ style cwd matches a /c/ style root"                 deny
run confirm_cleanup.sh "$(bash_in s-new 'C:\Users\zz\other' "$RM")" XDG_CONFIG_HOME="$WCFG"
check "TC-010 control: another folder on the same drive does not"       silent
# LAB_SETTINGS_FILE names the deployment when set
run confirm_cleanup.sh "$(bash_in s-new "$DEP/projects/p1" "$RM")" XDG_CONFIG_HOME="$CFG_NONE" LAB_SETTINGS_FILE="$DEP/config/env.yaml"
check "TC-010 LAB_SETTINGS_FILE alone also names the deployment"        deny
# the command names a deployment path while the cwd is elsewhere
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "rm -rf $RUNS/proj1/results")"
check "TC-010 a command that names a path under storage_root is in use" deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "rm -rf $OUTSIDE/results")"
check "TC-010 control: the same delete under an unrelated path"         silent

# TC-011 / TC-012 / TC-013: the command itself
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "bash $ROOT/scripts/on_site.sh 'rm -rf results'")"
check "TC-011 a command running the plugin's script (by path): refused" deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "bash scripts/on_site.sh 'rm -rf results'")"
check "TC-011 ...by scripts/<its name>"                                 deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "$RM && bash scripts/on_site.sh ls")"
check "TC-011 a delete beside a call to scripts/on_site.sh: refused"    deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "$RM && bash scripts/not_a_plugin_script.sh ls")"
check "TC-011 control: ...beside a script the plugin does not have"     silent
# round 2: a bare script name with the session's cwd inside the plugin itself
# (main refused this; stripping cwd from the text had lost it)
run confirm_cleanup.sh "$(bash_in s-new "$ROOT/scripts" "bash on_site.sh 'rm -rf results'")"
check "TC-011 cwd inside the plugin's scripts/, bare on_site.sh: refused" deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "bash on_site.sh 'rm -rf results'")"
check "TC-011 control: the same bare call from outside the plugin"      silent
run confirm_launch.sh "$(bash_in s-new "$OUTSIDE" "$LAUNCH")"
check "TC-012 tw launch asks without any marker or deployment"          ask
run confirm_launch.sh "$(bash_in s-new "$OUTSIDE" "$RELAUNCH")"
check "TC-012 tw runs relaunch asks"                                    ask
run confirm_launch.sh "$(bash_in s-new "$OUTSIDE" "cd $TMP && $LAUNCH")"
check "TC-012 tw behind a cd && asks"                                   ask
run confirm_launch.sh "$(bash_in s-new "$OUTSIDE" "twine upload dist/*")"
check "TC-012 control: a command that merely starts with tw is silent"  silent
MCPJ=$(jq -nc --arg s s-new --arg d "$OUTSIDE" '{session_id:$s, cwd:$d, hook_event_name:"PreToolUse", tool_name:"mcp__seqera__launch_pipeline", tool_input:{pipeline:"nf-core/rnaseq"}}')
run confirm_launch.sh "$MCPJ"
check "TC-013 a Seqera MCP launch asks without any marker"              ask

echo
echo "== US3: when unsure, in use =="
# TC-017
run confirm_cleanup.sh "$(bash_in "" "$OUTSIDE" "$RM")"
check "TC-017 no session id: deleting results/ is refused"              deny
run confirm_cleanup.sh "$(bash_in "" "$OUTSIDE" "$RM")" XDG_CONFIG_HOME="$CFG_NONE"
check "TC-017 ...even with no deployment at all"                        deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "$RM")"
check "TC-017 control: with a session id it is silent"                  silent
# TC-018: a state directory that cannot be read
BADSTATE="$TMP/state_is_a_file"; : > "$BADSTATE"
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "$RM")" AGENTIC_BIOFLOW_STATE_DIR="$BADSTATE"
check "TC-018 a state path that is not a directory: refused"            deny
if [ "$(id -u)" != 0 ]; then
  LOCKED="$TMP/state_locked"; mkdir -p "$LOCKED"; chmod 000 "$LOCKED"
  run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "$RM")" AGENTIC_BIOFLOW_STATE_DIR="$LOCKED"
  check "TC-018 a state directory that cannot be read: refused"         deny
  chmod 755 "$LOCKED"
fi
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "$RM")" AGENTIC_BIOFLOW_STATE_DIR="$TMP/state_not_created_yet"
check "TC-018 control: a state directory that does not exist yet: silent" silent
# TC-019: nothing deployed, nothing used
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "$RM")" XDG_CONFIG_HOME="$CFG_NONE"
check "TC-019 no settings anywhere: silent (the answer is known)"       silent
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "$RM")" XDG_CONFIG_HOME="$CFG_NONE" LAB_SETTINGS_FILE="$TMP/no/such/env.yaml"
check "TC-019 LAB_SETTINGS_FILE pointing at nothing: silent"            silent
# TC-020: a marker belongs to its own session
mark s-A
run confirm_cleanup.sh "$(bash_in s-A "$OUTSIDE" "$RM")"
check "TC-020 the session that left the marker is in use"               deny
run confirm_cleanup.sh "$(bash_in s-B "$OUTSIDE" "$RM")"
check "TC-020 another session is not"                                   silent
# a session id cannot name a file outside the state directory
run confirm_cleanup.sh "$(bash_in '../../../etc/passwd' "$OUTSIDE" "$RM")"
check "TC-020 a path-shaped session id is reduced, not followed"        silent

echo
echo "== acceptance findings (each case has a control that differs in one fact) =="
# H1: tw spelled tw.exe
for c in 'tw.exe launch nf-core/rnaseq' '/home/u/.local/bin/tw.exe launch x' 'C:\tools\tw.exe launch x' 'cd /x && tw.exe runs relaunch -i a'; do
  run confirm_launch.sh "$(bash_in s-new "$OUTSIDE" "$c")"
  check "H1 tw.exe is tw: ${c:0:40}" ask
done
run confirm_launch.sh "$(bash_in s-new "$OUTSIDE" "twine.exe upload x; sbatch.exe y")"
check "H1 control: twine.exe is not tw" silent

# H2: symlinks, both directions, for the root and for storage_root
REAL="$TMP/real"; mkdir -p "$REAL/dep2/config" "$REAL/dep2/projects/p" "$REAL/runsx/p" "$REAL/other"
ln -s "$REAL/dep2" "$TMP/linkdep"; ln -s "$REAL/runsx" "$TMP/linkruns"; ln -s "$DEP" "$TMP/deplink"
printf 'storage_root: %s\n' "$TMP/linkruns" > "$REAL/dep2/config/env.yaml"
CFG2="$TMP/cfg2"; mkdir -p "$CFG2/agentic-bioflow"; printf '%s\n' "$TMP/linkdep" > "$CFG2/agentic-bioflow/root"
run confirm_cleanup.sh "$(bash_in s-new "$REAL/dep2/projects/p" "$RM")" XDG_CONFIG_HOME="$CFG2"
check "H2 root named by a link, cwd physical: refused"                  deny
run confirm_cleanup.sh "$(bash_in s-new "$REAL/runsx/p" "$RM")" XDG_CONFIG_HOME="$CFG2"
check "H2 storage_root named by a link, cwd physical: refused"          deny
run confirm_cleanup.sh "$(bash_in s-new "$REAL/other" "$RM")" XDG_CONFIG_HOME="$CFG2"
check "H2 control: another physical folder is silent"                   silent
run confirm_cleanup.sh "$(bash_in s-new "$TMP/deplink/projects/p1" "$RM")"
check "H2 root physical, cwd through a link: refused"                   deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "rm -rf $REAL/runsx/p/results")" XDG_CONFIG_HOME="$CFG2"
check "H2 a command naming the physical form of a linked storage_root"  deny

# M1: a state directory that cannot take the marker
if [ "$(id -u)" != 0 ]; then
  RO="$TMP/state_ro"; mkdir -p "$RO"; chmod 555 "$RO"
  run confirm_cleanup.sh "$(bash_in s-ro "$OUTSIDE" "$RM")" AGENTIC_BIOFLOW_STATE_DIR="$RO"
  check "M1 deployment exists, state dir not writable: in use (refused)" deny
  run confirm_cleanup.sh "$(bash_in s-ro "$OUTSIDE" "$RM")" AGENTIC_BIOFLOW_STATE_DIR="$RO" XDG_CONFIG_HOME="$CFG_NONE"
  check "M1 control: ...but with no deployment at all, silent"          silent
  chmod 755 "$RO"
fi
S5="$TMP/state5"; mkdir -p "$S5"; : > "$S5/in-use"
run confirm_cleanup.sh "$(bash_in s-f "$OUTSIDE" "$RM")" AGENTIC_BIOFLOW_STATE_DIR="$S5"
check "M1 state/in-use is a file (marker cannot be written): in use"    deny

# M4: a symlinked CLAUDE_PLUGIN_ROOT, a write to its physical path
PREAL="$TMP/plugin_real"; mkdir -p "$PREAL/hooks" "$PREAL/scripts"; ln -s "$PREAL" "$TMP/plugin_link"
run guard_plugin_files.sh "$(file_in s-out "$OUTSIDE" Write "$PREAL/hooks/x.sh")" CLAUDE_PLUGIN_ROOT="$TMP/plugin_link"
check "M4 write to the physical path of a symlinked plugin root: refused" deny
run guard_plugin_files.sh "$(file_in s-out "$OUTSIDE" Write "$TMP/plugin_link/hooks/x.sh")" CLAUDE_PLUGIN_ROOT="$PREAL"
check "M4 ...and the reverse (root physical, write through the link)"   deny
run guard_plugin_files.sh "$(file_in s-out "$OUTSIDE" Write "$OUTSIDE/notes.txt")" CLAUDE_PLUGIN_ROOT="$TMP/plugin_link"
check "M4 control: an unrelated file is silent"                         silent

# LOW: ~ and $HOME spellings, relative LAB_SETTINGS_FILE, utils scripts
mkdir -p "$TMP/home/runs3/p"; DEP3="$TMP/dep3"; mkdir -p "$DEP3/config"
printf 'storage_root: ~/runs3\n' > "$DEP3/config/env.yaml"
CFG3="$TMP/cfg3"; mkdir -p "$CFG3/agentic-bioflow"; printf '%s\n' "$DEP3" > "$CFG3/agentic-bioflow/root"
run confirm_cleanup.sh "$(bash_in s-new "$TMP/home/runs3/p" "$RM")" XDG_CONFIG_HOME="$CFG3"
check "LOW storage_root written ~/runs3 in env.yaml, cwd under it"      deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "rm -rf ~/runs3/p/results")" XDG_CONFIG_HOME="$CFG3"
check "LOW a command spelling it ~/runs3/..."                           deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" 'rm -rf $HOME/runs3/p/results')" XDG_CONFIG_HOME="$CFG3"
check "LOW a command spelling it \$HOME/runs3/..."                      deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" 'rm -rf ${HOME}/runs3/p/results')" XDG_CONFIG_HOME="$CFG3"
check "LOW a command spelling it \${HOME}/runs3/..."                    deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" 'rm -rf ~/elsewhere/results')" XDG_CONFIG_HOME="$CFG3"
check "LOW control: ~/elsewhere is silent"                              silent
RUNCWD="$DEP" run confirm_cleanup.sh "$(bash_in s-new "$DEP/projects/p1" "$RM")" XDG_CONFIG_HOME="$CFG_NONE" LAB_SETTINGS_FILE=config/env.yaml
check "LOW a relative LAB_SETTINGS_FILE is read against the hook's cwd" deny
RUNCWD="$OUTSIDE" run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "$RM")" XDG_CONFIG_HOME="$CFG_NONE" LAB_SETTINGS_FILE=config/env.yaml
check "LOW control: the same relative path with no file there: silent"  silent
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "bash scripts/utils/schema_roles.py; $RM")"
check "LOW a scripts/utils/*.py call counts as the plugin's script"     deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "bash scripts/utils/not_ours.py; $RM")"
check "LOW control: scripts/utils/ name the plugin does not have"       silent

# #53: shapes of the same path the text check did not read. Each has a control
# that differs in one fact (the folder it names is not a root).
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" 'cd "$HOME"/runs3 && rm -rf results')" XDG_CONFIG_HOME="$CFG3"
check "#53 a quoted \"\$HOME\"/runs3 names the root"                     deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" 'cd "${HOME}"/runs3/p && rm -rf results')" XDG_CONFIG_HOME="$CFG3"
check "#53 a quoted \"\${HOME}\"/runs3/p names the root"                  deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" "cd '$TMP/home/runs3' && rm -rf results")" XDG_CONFIG_HOME="$CFG3"
check "#53 control: a single-quoted absolute path already names the root" deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" 'cd "$HOME"/elsewhere && rm -rf results')" XDG_CONFIG_HOME="$CFG3"
check "#53 control: a quoted \"\$HOME\"/elsewhere is silent"              silent
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" 'cd && cd runs3 && rm -rf results')" XDG_CONFIG_HOME="$CFG3"
check "#53 a bare cd, then a relative path, with a root under home"     deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" 'cd ~ && cd runs3 && rm -rf results')" XDG_CONFIG_HOME="$CFG3"
check "#53 cd ~ then a relative path, with a root under home"           deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" 'cd $HOME && cd runs3 && rm -rf results')" XDG_CONFIG_HOME="$CFG3"
check "#53 cd \$HOME then a relative path, with a root under home"       deny
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" 'cd && cd runs3 && rm -rf results')"
check "#53 control: the same call, no root under home (deployment elsewhere)" silent
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" 'cd /tmp && cd runs3 && rm -rf results')" XDG_CONFIG_HOME="$CFG3"
check "#53 control: cd to another folder, not home: silent"             silent
run confirm_cleanup.sh "$(bash_in s-new "$OUTSIDE" 'echo cdrom && rm -rf results')" XDG_CONFIG_HOME="$CFG3"
check "#53 control: a word that merely starts with cd: silent"          silent
# the same, from a prompt: naming the command without the leading slash
intro "$(jq -nc '{session_id:"s-noslash", hook_event_name:"UserPromptSubmit", prompt:"run it with agentic-bioflow:launch please"}')"
printf '%-72s ' "#53 a prompt naming agentic-bioflow:launch without a slash marks"
[ -e "$STATE/in-use/s-noslash" ] && echo ok || { echo FAIL; fails=$((fails+1)); }
intro "$(jq -nc '{session_id:"s-plain", hook_event_name:"UserPromptSubmit", prompt:"my agentic-bioflow notes are in a folder"}')"
printf '%-72s ' "#53 control: the plugin's name without a colon marks nothing"
[ ! -e "$STATE/in-use/s-plain" ] && echo ok || { echo FAIL; fails=$((fails+1)); }

# session id: the top-level one, by both readers
intro "$(jq -nc '{session_id:"realsid", hook_event_name:"PostToolUse", tool_name:"Skill", tool_input:{skill:"agentic-bioflow:launch"}, tool_response:{session_id:"othersid"}}')"
printf '%-72s ' "LOW plugin_intro marks the top-level session id, not a nested one"
{ [ -e "$STATE/in-use/realsid" ] && [ ! -e "$STATE/in-use/othersid" ]; } && echo ok || { echo "FAIL: $(ls "$STATE/in-use" | tr '\n' ' ')"; fails=$((fails+1)); }

# condition 2 on its own: the call names nothing, only the cwd does
run confirm_cleanup.sh "$(bash_in s-new "$RUNS/proj1" "$RM")"
check "cond 2 alone: cwd under storage_root, call names nothing"        deny

echo
echo "== the other hooks read the same answer (in use = as before) =="
J=$(jq -nc --arg s s-used --arg d "$OUTSIDE" --arg t "$TMP/empty.jsonl" \
  '{session_id:$s, cwd:$d, transcript_path:$t, tool_name:"Write", tool_input:{file_path:"/r/samplesheet.csv"}}')
run confirm_walkthrough.sh "$J"
check "walkthrough: a samplesheet write in a used session is gated"     deny
run guard_plugin_files.sh "$(file_in s-used "$OUTSIDE" Write "$PLUG/hooks/x.sh")" CLAUDE_PLUGIN_ROOT="$PLUG"
check "guard: a plugin-file write in a used session is refused"         deny
run next_step.sh "$(STOPJ s-used "$OUTSIDE")"
check "next_step: an open flow in a used session still blocks"          block
run next_step.sh "$(STOPJ "" "$OUTSIDE")"
check "next_step: no session id still blocks"                           block
J=$(jq -nc --arg s s-used --arg d "$OUTSIDE" '{session_id:$s, cwd:$d, hook_event_name:"SessionStart"}')
run session_start.sh "$J"
printf '%-72s ' "session_start: a used session (resumed) still gets the deployment line"
case "$OUT" in *"Deployment settings:"*) echo ok ;; *) echo "FAIL <<${OUT:0:100}>>"; fails=$((fails+1)) ;; esac
J=$(jq -nc --arg s s-fresh --arg d "$DEP/projects/p1" '{session_id:$s, cwd:$d, hook_event_name:"SessionStart"}')
run session_start.sh "$J"
printf '%-72s ' "session_start: a fresh session inside the deployment gets it too"
case "$OUT" in *"Deployment settings:"*) echo ok ;; *) echo "FAIL <<${OUT:0:100}>>"; fails=$((fails+1)) ;; esac

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
