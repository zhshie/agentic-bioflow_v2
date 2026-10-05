#!/bin/bash
# #34, acceptance round: the gates must not get slower than LINEAR in the size of
# what they are handed. A hook that runs past its timeout (hooks.json: 30 s) is
# cancelled and the tool call PROCEEDS, so a large Write (an analysis script, a
# samplesheet) or a large here-doc followed by a delete or a launch must still be
# judged, quickly, with the same verdict as always.
#
# The first version of the speed fix counted separators with ${X//[^x]/} and
# trimmed newlines one character at a time; both are quadratic in bash. On native
# Git Bash a 130 KB input took over 30 s and every hook was cancelled.
#
# Two checks per case, neither a comparison with a fixed machine speed:
#   - absolute: the largest input finishes in well under the timeout;
#   - scaling: 4x the input must not cost more than ~8x the time (linear is 4x,
#     quadratic 16x). Only judged once the run is long enough to mean anything.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
HOOKS="$ROOT/hooks"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0

command -v jq >/dev/null 2>&1 || { echo "jq is required for this test"; exit 1; }
PY=$(command -v python3 || command -v python) || { echo "python is required for this test"; exit 1; }

mkdir -p "$TMP/home" "$TMP/state/in-use" "$TMP/work"
: > "$TMP/state/in-use/big-s1"
for i in $(seq 1 200); do printf '{"type":"user","message":{"content":"hello %s"}}\n' "$i"; done > "$TMP/transcript.jsonl"

now_ms() { if [ -n "${EPOCHREALTIME:-}" ]; then local e=${EPOCHREALTIME/[.,]/}; echo $((e / 1000)); else echo $((SECONDS * 1000)); fi; }

# mk <file> <kind> <kb>
mk() {
  "$PY" - "$1" "$2" "$3" "$TMP" <<'PY'
import json, sys
f, kind, kb, tmp = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
pad = "".join("x%d = %d  # filler line\n" % (i, i) for i in range(200000))[: kb * 1024]
# End on a whole line: cut mid-line, "EOF" would be glued to the last filler line, the
# here-doc would never end, and the delete / launch would sit INSIDE its body.
pad = pad[: pad.rfind("\n") + 1]
if kind == "launch":  ti = {"command": "python3 - <<'EOF'\n" + pad + "EOF\ntw launch nf-core/rnaseq -profile test"}
elif kind == "rm":    ti = {"command": "python3 - <<'EOF'\n" + pad + "EOF\nrm -rf /work/u/lab_runs/x/results"}
elif kind == "write": ti = {"file_path": tmp + "/work/analysis/de.R", "content": pad}
if kind != "write":
    assert ti["command"].count("\nEOF\n") == 1, "the here-doc must end on its own line"
tool = "Write" if kind == "write" else "Bash"
d = {"session_id": "big-s1", "cwd": tmp + "/work", "transcript_path": tmp + "/transcript.jsonl",
     "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti}
open(f, "w").write(json.dumps(d))
PY
}

# run <hook> <file>  -> sets MS and KIND
run() {
  local s e out rc
  s=$(now_ms)
  out=$( ( cd "$TMP/work" && env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR HOME="$TMP/home" XDG_CONFIG_HOME="$TMP/home/.config" \
        AGENTIC_BIOFLOW_STATE_DIR="$TMP/state" CLAUDE_PLUGIN_ROOT="$ROOT" \
        timeout 30 bash "$HOOKS/$1.sh" < "$2" 2>/dev/null ) )
  rc=$?
  e=$(now_ms); MS=$((e - s))
  KIND=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision // (if .hookSpecificOutput.additionalContext then "ctx" else "none" end)' 2>/dev/null)
  [ "$rc" = 124 ] && KIND="TIMEOUT"
  [ -n "$KIND" ] || KIND=none
}

# check <label> <hook> <kind of input> <expected verdict, or - for any> <small KB> <big KB>
check() {
  local label="$1" hook="$2" kind="$3" want="$4" sk="$5" bk="$6" ms_small ms_big
  mk "$TMP/small.json" "$kind" "$sk";  run "$hook" "$TMP/small.json"; ms_small=$MS; local k_small=$KIND
  mk "$TMP/big.json" "$kind" "$bk";    run "$hook" "$TMP/big.json";   ms_big=$MS;   local k_big=$KIND
  local why=""
  if [ "$want" != - ]; then
    [ "$k_small" = "$want" ] || why="${sk} KB verdict $k_small, want $want. "
    [ "$k_big" = "$want" ]   || why="${why}${bk} KB verdict $k_big, want $want. "
  fi
  [ "$k_big" != TIMEOUT ] || why="${why}${bk} KB hook was cancelled at 30 s. "
  [ "$ms_big" -le 15000 ]  || why="${why}${bk} KB took ${ms_big} ms (limit 15000). "
  if [ "$ms_big" -gt 4000 ] && [ "$ms_big" -gt $((ms_small * 8)) ]; then why="${why}scaling: ${sk} KB ${ms_small} ms, ${bk} KB ${ms_big} ms (over 8x). "; fi
  printf '%-62s %6s ms -> %6s ms  ' "$label" "$ms_small" "$ms_big"
  if [ -z "$why" ]; then echo "ok ($want)"; else echo "FAIL: $why"; fails=$((fails+1)); fi
}

# --- #62, deletion guard: a 300 KB python here-doc, then a delete of results/ -----
# On native Git Bash this took 23-116 s before #62, past the 30 s timeout (and a
# cancelled hook lets the delete proceed). Three bodies: filler lines; code lines
# full of delete-like letters (format, transform, remove_prefix) that a filter keyed
# on substrings would keep; and a shell script of pipelines fed to bash (the shared
# splitter once copied the rest of the string at every pipe: 39 s for 100 KB on Git
# Bash). Judged: deny at both sizes; 300 KB within 20 s; and 10x
# the input costing at most 25x the time once the run is long enough to measure
# (linear is 10x, quadratic 100x), so a slow machine does not fail it.
mk62() { # mk62 <file> <kb> <filler|code>
  "$PY" - "$1" "$2" "$3" "$TMP" <<'PY'
import json, sys
f, kb, body, tmp = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
runner = "python3 -"
if body == "code":
    line = lambda i: "v%d = transform(format(x%d, '.2f')).remove_prefix('r')\n" % (i, i)
elif body == "pipes":
    # a shell script fed to bash: every line a pipeline, and `sort` is a word the
    # guard follows for PowerShell pipelines
    runner = "bash"
    line = lambda i: "cat f%d.txt | grep -c x%d | sort\n" % (i, i)
else:
    line = lambda i: "x%d = %d  # filler line\n" % (i, i)
pad = "".join(line(i) for i in range(20000))[: kb * 1024]
pad = pad[: pad.rfind("\n") + 1]
cmd = runner + " <<'EOF'\n" + pad + "EOF\nrm -rf /work/u/lab_runs/x/results"
assert cmd.count("\nEOF\n") == 1
d = {"session_id": "big-s1", "cwd": tmp + "/work", "hook_event_name": "PreToolUse", "tool_name": "Bash",
     "tool_input": {"command": cmd}}
open(f, "w").write(json.dumps(d))
PY
}
check62() { # check62 <filler|code|pipes>
  local ms_small k_small ms_big k_big why=""
  mk62 "$TMP/c62s.json" 30 "$1";  run confirm_cleanup "$TMP/c62s.json"; ms_small=$MS; k_small=$KIND
  mk62 "$TMP/c62b.json" 300 "$1"; run confirm_cleanup "$TMP/c62b.json"; ms_big=$MS; k_big=$KIND
  [ "$k_small" = deny ] || why="30 KB verdict $k_small, want deny. "
  [ "$k_big" = deny ]   || why="${why}300 KB verdict $k_big, want deny. "
  [ "$ms_big" -le 20000 ] || why="${why}300 KB took ${ms_big} ms (limit 20000). "
  if [ "$ms_big" -gt 3000 ] && [ "$ms_big" -gt $((ms_small * 25)) ]; then why="${why}scaling: 30 KB ${ms_small} ms, 300 KB ${ms_big} ms (over 25x). "; fi
  printf '%-62s %6s ms -> %6s ms  ' "#62 300 KB here-doc ($1) then rm -rf results (deletion guard)" "$ms_small" "$ms_big"
  if [ -z "$why" ]; then echo "ok (deny)"; else echo "FAIL: $why"; fails=$((fails+1)); fi
}
echo "== #62: the deletion guard on a 300 KB here-doc =="
check62 filler
check62 code
check62 pipes
# A delete with many targets: each relative one, in a folder that exists here, was
# resolved through `readlink -f`, one program per target - 130 ms each on Git Bash
# (500 targets: 66 s, past the timeout). The programs started must not grow with
# the targets.
mkdir -p "$TMP/proj" "$TMP/shim62"
printf '#!/bin/bash\necho x >> "%s/rl62.log"\nexec %s "$@"\n' "$TMP" "$(command -v readlink)" > "$TMP/shim62/readlink"
chmod +x "$TMP/shim62/readlink"
"$PY" - "$TMP/many62.json" 200 "$TMP" <<'PY'
import json, sys
f, n, tmp = sys.argv[1], int(sys.argv[2]), sys.argv[3]
cmd = "rm -f " + " ".join("old_%d.tmp" % i for i in range(n))
d = {"session_id": "big-s1", "cwd": tmp + "/proj", "hook_event_name": "PreToolUse", "tool_name": "Bash",
     "tool_input": {"command": cmd}}
open(f, "w").write(json.dumps(d))
PY
: > "$TMP/rl62.log"
out62=$( ( cd "$TMP/proj" && env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR HOME="$TMP/home" XDG_CONFIG_HOME="$TMP/home/.config" \
      AGENTIC_BIOFLOW_STATE_DIR="$TMP/state" CLAUDE_PLUGIN_ROOT="$ROOT" PATH="$TMP/shim62:$PATH" \
      timeout 60 bash "$HOOKS/confirm_cleanup.sh" < "$TMP/many62.json" 2>/dev/null ) )
n62=$(awk 'END {print NR+0}' "$TMP/rl62.log")
printf '%-80s ' "#62 rm -f of 200 relative targets: readlink started $n62 times (at most 4)"
if [ "$n62" -le 4 ] && [ -z "$out62" ]; then echo ok; else echo "FAIL: output <<${out62:0:60}>>"; fails=$((fails+1)); fi
echo

echo "== large inputs: still judged, same verdict, linear time =="
check "Write of a 300 KB analysis script (walkthrough gate)"  confirm_walkthrough write  deny 75 300
check "Write of a 300 KB analysis script (launch gate)"       confirm_launch       write  none 75 300
check "Write of a 300 KB analysis script (plugin-file guard)" guard_plugin_files   write  none 75 300
check "128 KB here-doc then rm -rf results (deletion guard)"  confirm_cleanup      rm     deny 32 128
check "128 KB here-doc then rm -rf results (launch gate)"     confirm_launch       rm     none 32 128
check "128 KB here-doc then tw launch (launch gate)"          confirm_launch       launch ask  32 128
check "128 KB here-doc then tw launch (walkthrough gate)"     confirm_walkthrough  launch deny 32 128
check "128 KB here-doc then tw launch (deletion guard)"       confirm_cleanup      launch none 32 128

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
