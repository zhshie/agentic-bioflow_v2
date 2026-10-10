#!/bin/bash
# The gates must not open when jq is missing (issue #70).
#
# The Safety Net hooks refuse (exit 2, "BLOCKED" on stderr) when jq is missing
# or broken - PITFALLS 28, Constitution 13. This file feeds each gate the shapes
# from #70's table with jq hidden from PATH and checks the answer. It needs NO
# jq itself: every input is built with printf, so it passes on a machine that
# has none (where tests/run_all.sh refuses to run the rest of the suite).
#
# With a real jq on the machine (CI) jq is hidden with tests/lib/nojq_path.sh.
# If it cannot be hidden this file FAILS: running the gates with jq present and
# calling that "no jq" would be a green that proves nothing (TC-012).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HD="$HERE/../hooks"
export MSYS2_ARG_CONV_EXCL='*'
TMP=$(mktemp -d)
trap 'command rm -rf "$TMP"' EXIT
fails=0

. "$HERE/lib/nojq_path.sh"
NOJQ_PATH=$(nojq_path "$TMP") || { echo "FAIL: cannot hide jq from PATH, so this file would test the with-jq path"; exit 1; }
if PATH="$NOJQ_PATH" command -v jq >/dev/null 2>&1; then
    echo "FAIL: jq is still reachable on the test PATH"; exit 1
fi

# A scratch plugin root, so guard_plugin_files has something to guard.
PR="$TMP/plugin-root"; mkdir -p "$PR/hooks"

bash_json()  { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1"; }
write_json() { printf '{"tool_name":"%s","tool_input":{"file_path":"%s","content":"%s"}}' "$1" "$2" "$3"; }

# gate <label> <expect block|pass> <hook> <json>
gate() {
    local label="$1" want="$2" hook="$3" json="$4" out err rc
    printf '%-62s ' "$label"
    out=$(printf '%s' "$json" | PATH="$NOJQ_PATH" CLAUDE_PLUGIN_ROOT="$PR" bash "$HD/$hook" 2>"$TMP/err"); rc=$?
    err=$(cat "$TMP/err")
    if [ "$want" = block ]; then
        if [ "$rc" = 2 ] && [ -z "$out" ] && grep -q 'BLOCKED' <<<"$err" && grep -q 'jq is missing' <<<"$err"; then
            echo "ok (exit 2, BLOCKED)"
        else
            echo "FAIL: expected exit 2 + BLOCKED/jq is missing, got rc=$rc out='$out' err='$err'"; fails=$((fails+1))
        fi
    else
        if [ "$rc" = 0 ]; then echo "ok (exit 0)"; else
            echo "FAIL: expected exit 0, got rc=$rc err='$err'"; fails=$((fails+1)); fi
    fi
}

# TC-001..003  confirm_cleanup.sh
gate "TC-001 cleanup: rm -rf results"                  block confirm_cleanup.sh "$(bash_json 'rm -rf results')"
gate "TC-002 cleanup: ssh u@host rm -rf /work/results" block confirm_cleanup.sh "$(bash_json 'ssh u@host rm -rf /work/results')"
gate "TC-003 cleanup: ls -la has nothing to gate"      pass  confirm_cleanup.sh "$(bash_json 'ls -la')"

# TC-004..007  confirm_launch.sh
gate "TC-004 launch: tw launch nf-core/rnaseq"         block confirm_launch.sh "$(bash_json 'tw launch nf-core/rnaseq')"
gate "TC-005 launch: nextflow run ... -profile slurm"  block confirm_launch.sh "$(bash_json 'nextflow run nf-core/rnaseq -profile slurm')"
gate "TC-006 launch: ssh u@host sbatch job.sh"         block confirm_launch.sh "$(bash_json 'ssh u@host sbatch job.sh')"
gate "TC-007 launch: read-only squeue over ssh"        block confirm_launch.sh "$(bash_json 'ssh -o BatchMode=yes -F jump.cfg u@node01 squeue')"

# TC-008..009  confirm_walkthrough.sh
gate "TC-008 walkthrough: Write token into params.yaml" block confirm_walkthrough.sh "$(write_json Write /r/params.yaml 'tower_access_token: abc123')"
gate "TC-009 walkthrough: echo token >> params.yaml"    block confirm_walkthrough.sh "$(bash_json 'echo tower_access_token: abc123 >> params.yaml')"

# TC-010..011  guard_plugin_files.sh
gate "TC-010 guard: Edit a file under the plugin root"  block guard_plugin_files.sh "$(write_json Edit "$PR/hooks/confirm_launch.sh" 'x')"
gate "TC-011 guard: sed -i a file under the plugin root" block guard_plugin_files.sh "$(bash_json "sed -i 's/a/b/' $PR/hooks/confirm_launch.sh")"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
