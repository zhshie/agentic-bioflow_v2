#!/bin/bash
# Feature 005 (#48), FR-007 / SC-003: when the plugin is not in use, a hook call
# must not cost more than it does on main. Every process is expensive under
# Git Bash (#34), and this runs on every shell command in every session that has
# the plugin installed, so the not-in-use path has to be the cheap one.
#
# It runs main's confirm_launch.sh (read out of git, not from this checkout)
# against this checkout's, on one input that is not in use: a session with no
# marker, a folder outside any deployment, the command from the incident (an
# ssh through WSL, which main's D3 branch spends several processes on). Calls
# alternate main/new so machine load lands on both, and the verdict compares
# totals with a 10% margin - never an absolute time, which would only measure
# the machine.
#
# Skipped, with a note and exit 0, when there is nothing to compare against: no
# git, no `main` ref (a shallow CI checkout has none), or a `date` without
# nanoseconds. A skip is not a pass of the speed claim; the first section still
# runs and is what shows the not-in-use path exits early.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0
N=20

command -v jq >/dev/null 2>&1 || { echo "jq is required for this test"; exit 1; }

# A fake `uname -s` saying MSYS, as tests/confirm_launch_test.sh does.
MSYSBIN="$TMP/msysbin"; mkdir -p "$MSYSBIN"
cat > "$MSYSBIN/uname" <<'EOF'
#!/bin/bash
[ "$1" = -s ] && { echo MINGW64_NT-10.0-22631; exit 0; }
exec /usr/bin/uname "$@"
EOF
chmod +x "$MSYSBIN/uname"

mkdir -p "$TMP/home" "$TMP/cfg" "$TMP/elsewhere"
CMD="wsl.exe -e ssh -o ControlPath=/tmp/cm-%C -o BatchMode=yes u@login-node 'scontrol show partition; sacctmgr show qos'"
INPUT=$(jq -nc --arg c "$CMD" --arg d "$TMP/elsewhere" \
  '{session_id:"speed-test", cwd:$d, hook_event_name:"PreToolUse", tool_name:"Bash", tool_input:{command:$c}}')

call() { # call <hooks-dir>  -> stdout of the hook
  printf '%s' "$INPUT" | env -u LAB_SETTINGS_FILE -u CLAUDE_PLUGIN_ROOT -u LAB_RUNS_DIR \
    HOME="$TMP/home" XDG_CONFIG_HOME="$TMP/cfg" AGENTIC_BIOFLOW_STATE_DIR="$TMP/state" \
    PATH="$MSYSBIN:$PATH" bash "$1/confirm_launch.sh" 2>/dev/null
}

echo "== the not-in-use path exits early =="
printf '%-72s ' "this checkout is silent on the not-in-use input"
out=$(call "$ROOT/hooks")
if [ -z "$out" ]; then echo ok; else echo "FAIL: <<${out:0:100}>>"; fails=$((fails+1)); fi

echo
echo "== and it is not slower than main (TC-023) =="
skip() { echo "SKIP: $1 - the speed comparison was not made"; [ "$fails" = 0 ] && { echo "all passed (speed comparison skipped)"; exit 0; } || { echo "$fails failed"; exit 1; }; }

command -v git >/dev/null 2>&1 || skip "git is not available"
git -C "$ROOT" rev-parse --verify -q main >/dev/null 2>&1 || skip "no 'main' ref here (shallow checkout?)"
# The baseline is the hooks as they were BEFORE the scope check existed. Once
# 005 is merged, `main` itself has it and is silent on this input - comparing
# against it would compare the feature with itself (this failed on main's own
# CI right after the merge). So: main if it has no hooks/in_use.sh yet,
# otherwise the parent of the commit that first added that file.
BASE=main
if git -C "$ROOT" cat-file -e main:hooks/in_use.sh 2>/dev/null; then
    added=$(git -C "$ROOT" log --format=%H --diff-filter=A main -- hooks/in_use.sh 2>/dev/null | tail -1)
    [ -n "$added" ] && git -C "$ROOT" rev-parse --verify -q "$added^" >/dev/null 2>&1 \
        || skip "cannot find the hooks from before the scope check (shallow history?)"
    BASE="$added^"
fi
mkdir -p "$TMP/main"
git -C "$ROOT" archive "$BASE" hooks 2>/dev/null | tar -x -C "$TMP/main" 2>/dev/null || skip "could not read the baseline hooks out of git"
[ -r "$TMP/main/hooks/confirm_launch.sh" ] || skip "main has no hooks/confirm_launch.sh"
t0=$(date +%s%N 2>/dev/null)
case "$t0" in ''|*[!0-9]*) skip "date has no nanosecond clock on this machine" ;; esac

# main's hook asks on this input (it is the incident); that is the cost being
# compared against, and it also proves the two versions really differ here.
printf '%-72s ' "main's hook is not silent on it (so the comparison means something)"
mout=$(call "$TMP/main/hooks")
if [ -n "$mout" ]; then echo ok; else echo "FAIL: main was silent too; nothing to compare"; fails=$((fails+1)); fi

call "$TMP/main/hooks" >/dev/null; call "$ROOT/hooks" >/dev/null   # warm both
tm=0; tn=0
for _ in $(seq 1 "$N"); do
  a=$(date +%s%N); call "$TMP/main/hooks" >/dev/null; b=$(date +%s%N)
  call "$ROOT/hooks" >/dev/null; c=$(date +%s%N)
  tm=$((tm + b - a)); tn=$((tn + c - b))
done
printf '%-72s ' "$N calls each, main ${tm}ns total, this checkout ${tn}ns total"
if [ $((tn * 10)) -le $((tm * 11)) ]; then echo "ok (new <= main x 1.1)"; else
  echo "FAIL: this checkout took more than 1.1x main's time"; fails=$((fails+1)); fi

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
