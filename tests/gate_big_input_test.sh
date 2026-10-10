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
  "$PY" - "$1" "$2" "$3" "$TMP" "${4:-rm}" <<'PY'
import json, sys
f, kb, body, tmp = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
tail = sys.argv[5] if len(sys.argv) > 5 else "rm"
runner = "python3 -"
if body == "code":
    line = lambda i: "v%d = transform(format(x%d, '.2f')).remove_prefix('r')\n" % (i, i)
elif body == "bs":
    # #66: every line holds a backslash, so the dropped-backslash copy is made for each
    line = lambda i: "v%d = s%d.split('\\t')  # a\\.b\n" % (i, i)
elif body == "bspipes":
    runner = "bash"
    line = lambda i: "cat f%d.txt | grep -c a\\.b%d | sort\n" % (i, i)
elif body == "pipes":
    # a shell script fed to bash: every line a pipeline, and `sort` is a word the
    # guard follows for PowerShell pipelines
    runner = "bash"
    line = lambda i: "cat f%d.txt | grep -c x%d | sort\n" % (i, i)
else:
    line = lambda i: "x%d = %d  # filler line\n" % (i, i)
pad = "".join(line(i) for i in range(20000))[: kb * 1024]
pad = pad[: pad.rfind("\n") + 1]
verb = "r\\m" if tail == "rbm" else "rm"
cmd = runner + " <<'EOF'\n" + pad + "EOF\n" + verb + " -rf /work/u/lab_runs/x/results"
assert cmd.count("\nEOF\n") == 1
d = {"session_id": "big-s1", "cwd": tmp + "/work", "hook_event_name": "PreToolUse", "tool_name": "Bash",
     "tool_input": {"command": cmd}}
open(f, "w").write(json.dumps(d))
PY
}
check62() { # check62 <filler|code|pipes|bs|bspipes> [rm|rbm]
  local ms_small k_small ms_big k_big why="" tail="${2:-rm}" lim=20000 verb="rm -rf results"
  # #66 (TC-033): a backslash on every line, then r\m -rf results. On Linux/WSL the
  # 300 KB call must stay within 3 s; native Git Bash keeps the 20 s of #62.
  case "$1" in bs|bspipes) [ "$(uname -s)" = Linux ] && lim=3000 ;; esac
  [ "$tail" = rbm ] && verb='r\m -rf results'
  mk62 "$TMP/c62s.json" 30 "$1" "$tail";  run confirm_cleanup "$TMP/c62s.json"; ms_small=$MS; k_small=$KIND
  mk62 "$TMP/c62b.json" 300 "$1" "$tail"; run confirm_cleanup "$TMP/c62b.json"; ms_big=$MS; k_big=$KIND
  [ "$k_small" = deny ] || why="30 KB verdict $k_small, want deny. "
  [ "$k_big" = deny ]   || why="${why}300 KB verdict $k_big, want deny. "
  [ "$ms_big" -le "$lim" ] || why="${why}300 KB took ${ms_big} ms (limit $lim). "
  if [ "$ms_big" -gt 3000 ] && [ "$ms_big" -gt $((ms_small * 25)) ]; then why="${why}scaling: 30 KB ${ms_small} ms, 300 KB ${ms_big} ms (over 25x). "; fi
  printf '%-62s %6s ms -> %6s ms  ' "#62 300 KB here-doc ($1) then $verb (deletion guard)" "$ms_small" "$ms_big"
  if [ -z "$why" ]; then echo "ok (deny)"; else echo "FAIL: $why"; fails=$((fails+1)); fi
}
echo "== #62: the deletion guard on a 300 KB here-doc =="
check62 filler
check62 code
check62 pipes
# #66 TC-033 / TC-034: backslash on every line; the dropped-backslash copy is made for all of them
check62 bs rbm
check62 bspipes rbm
check62 bs rm
check62 bspipes rm
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

# ---------------------------------------------------------------------------
# #62 (launch gate and hooks/in_use.sh): a big here-doc followed by a launch, in
# every way a session can be in use. Each case runs 30 KB and 300 KB and passes
# when the verdict is right both times, the 300 KB call ends well inside the
# 30 s timeout, and it costs no more than 30x the 30 KB call. Linear is 10x and
# quadratic 100x, so 30x leaves room for a loaded machine; the ratio is only
# judged once the big call takes over 3 s, and a big call that fails it is run
# once more (the faster of the two counts), so one unlucky run does not fail.
#   marker      the session has the in-use marker
#   by-cwd      no marker; the cwd is under storage_root
#   by-path     no marker, cwd elsewhere; the command names a path under
#               storage_root at its very end (hooks/in_use.sh looks for it)
#   code        marker; the here-doc is code-like: quotes, globs, brackets,
#               `.tsv` and the words add/remove on every line
mkdir -p "$TMP/l62/home/.config/agentic-bioflow" "$TMP/l62/abf/config" "$TMP/l62/runs3/p" "$TMP/l62/work" "$TMP/l62/state/in-use"
: > "$TMP/l62/state/in-use/l62-mark"
printf 'storage_root: %s\nreach: local\n' "$TMP/l62/runs3" > "$TMP/l62/abf/config/env.yaml"
printf '%s\n' "$TMP/l62/abf" > "$TMP/l62/home/.config/agentic-bioflow/root"

# l62_mk <file> <kb> <situation>
l62_mk() {
  "$PY" - "$1" "$2" "$3" "$TMP/l62" <<'PY'
import json, sys
f, kb, sit, base = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
if sit == "code":
    line = lambda i: "df%d = pd.read_csv(\"results/s%d.tsv\", sep='\\t')  # add the [%d] values * 2; remove \"outliers\"\n" % (i, i, i)
else:
    line = lambda i: "x%d = %d  # filler line\n" % (i, i)
pad = "".join(line(i) for i in range(200000))[: kb * 1024]
pad = pad[: pad.rfind("\n") + 1]
verb = "t" + "w launch nf-core/rnaseq -profile test"
if sit == "by-path":
    tail = "cd " + base + "/runs3/p && s" + "batch run.sh"
else:
    tail = verb
sid = {"marker": "l62-mark", "code": "l62-mark"}.get(sit, "l62-" + sit)
cwd = base + "/runs3/p" if sit == "by-cwd" else base + "/work"
ti = {"command": "python3 - <<'EOF'\n" + pad + "EOF\n" + tail}
d = {"session_id": sid, "cwd": cwd, "hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": ti}
open(f, "w").write(json.dumps(d))
PY
}
# l62_run <file>  -> MS, KIND
l62_run() {
  local s e out rc
  s=$(now_ms)
  out=$( ( cd "$TMP/l62/work" && env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR HOME="$TMP/l62/home" XDG_CONFIG_HOME="$TMP/l62/home/.config" \
        AGENTIC_BIOFLOW_STATE_DIR="$TMP/l62/state" CLAUDE_PLUGIN_ROOT="$ROOT" \
        timeout 30 bash "$HOOKS/confirm_launch.sh" < "$1" 2>/dev/null ) )
  rc=$?
  e=$(now_ms); MS=$((e - s))
  KIND=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision // "none"' 2>/dev/null)
  [ "$rc" = 124 ] && KIND=TIMEOUT
  [ -n "$KIND" ] || KIND=none
}
l62_check() { # l62_check <situation> <label>
  local sit="$1" label="$2" ms_small k_small ms_big k_big why=""
  l62_mk "$TMP/l62s.json" 30 "$sit";  l62_run "$TMP/l62s.json"; ms_small=$MS; k_small=$KIND
  l62_mk "$TMP/l62b.json" 300 "$sit"; l62_run "$TMP/l62b.json"; ms_big=$MS; k_big=$KIND
  if [ "$ms_big" -gt 3000 ] && [ "$ms_big" -gt $((ms_small * 30)) ]; then
    l62_run "$TMP/l62b.json"; [ "$MS" -lt "$ms_big" ] && { ms_big=$MS; k_big=$KIND; }
  fi
  [ "$k_small" = ask ] || why="30 KB verdict $k_small, want ask. "
  [ "$k_big" = ask ]   || why="${why}300 KB verdict $k_big, want ask. "
  [ "$ms_big" -le 25000 ] || why="${why}300 KB took ${ms_big} ms (limit 25000). "
  if [ "$ms_big" -gt 3000 ] && [ "$ms_big" -gt $((ms_small * 30)) ]; then why="${why}scaling: 30 KB ${ms_small} ms, 300 KB ${ms_big} ms (over 30x). "; fi
  printf '%-62s %6s ms -> %6s ms  ' "$label" "$ms_small" "$ms_big"
  if [ -z "$why" ]; then echo "ok (ask)"; else echo "FAIL: $why"; fails=$((fails+1)); fi
}
echo
echo "== #62: a big here-doc then a launch, in use four ways (launch gate, 30 KB -> 300 KB) =="
l62_check marker  "#62 marker: here-doc then tw launch"
l62_check by-cwd  "#62 no marker, cwd under storage_root: here-doc then tw launch"
l62_check by-path "#62 no marker, the command names storage_root last"
l62_check code    "#62 marker, code-like here-doc then tw launch"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
