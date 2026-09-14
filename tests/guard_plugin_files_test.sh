#!/bin/bash
# Regression tests for hooks/guard_plugin_files.sh.
#
# Everything here runs against a TEMP directory standing in for
# ${CLAUDE_PLUGIN_ROOT} - never against this session's own real plugin root,
# which has the plugin actually installed under it (see the file's own
# comment about why: a write there during a test run would be a write to the
# plugin actually driving this session).
set -uo pipefail

H="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/hooks/guard_plugin_files.sh"
fails=0

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

ROOT="$TMP/plugin_root"
mkdir -p "$ROOT/hooks" "$ROOT/scripts" "$ROOT/tests"
OTHER="$TMP/repo_checkout"          # a maintainer's own checkout - never guarded
mkdir -p "$OTHER/hooks"
PROJECT="$TMP/user_project"         # an ordinary user project - never guarded
mkdir -p "$PROJECT"

edit_input() { # edit_input <tool> <file_path_field> <path>
  python3 -c '
import json, sys
tool, field, path = sys.argv[1], sys.argv[2], sys.argv[3]
print(json.dumps({"tool_name": tool, "tool_input": {field: path}}))
' "$1" "$2" "$3"
}

bash_input() { # bash_input <command>
  python3 -c '
import json, sys
print(json.dumps({"tool_name": "Bash", "tool_input": {"command": sys.argv[1]}}))
' "$1"
}

decision() { # decision <json-or-empty>
  if [ -z "$1" ]; then echo "allow"; return; fi
  python3 -c '
import json, sys
o = json.load(sys.stdin)["hookSpecificOutput"]
print(o.get("permissionDecision", "allow"))
' <<<"$1" 2>/dev/null
}

t() { # t <label> <expect allow|deny> -- <env assignments...> -- <stdin-json>
  local label="$1" expect="$2"; shift 2
  local -a envs=()
  while [ "$1" != "--" ]; do envs+=("$1"); shift; done
  shift
  local input="$1"
  printf '%-72s ' "$label"
  local out rc
  out=$(env "${envs[@]}" bash "$H" <<<"$input" 2>"$TMP/stderr"); rc=$?
  local got
  if [ "$rc" != 0 ]; then got="exit:$rc"; else got=$(decision "$out"); fi
  if [ "$got" = "$expect" ]; then echo "ok ($got)"; else
    echo "FAIL: expected $expect, got $got"; fails=$((fails + 1))
  fi
}

echo "== CLAUDE_PLUGIN_ROOT unset =="
t "unset root - Write anywhere is allowed" allow \
  -- \
  "$(edit_input Write file_path "$ROOT/hooks/x.sh")"
env -u CLAUDE_PLUGIN_ROOT true  # sanity: the var really is absent by default here

echo
echo "== Write/Edit/MultiEdit/NotebookEdit: positive (denied) and negative (allowed) =="

for tool in Write Edit MultiEdit; do
  t "$tool: existing file inside root - DENY" deny \
    CLAUDE_PLUGIN_ROOT="$ROOT" -- \
    "$(edit_input "$tool" file_path "$ROOT/hooks/confirm_launch.sh")"

  t "$tool: NEW (nonexistent) file inside root - DENY" deny \
    CLAUDE_PLUGIN_ROOT="$ROOT" -- \
    "$(edit_input "$tool" file_path "$ROOT/hooks/brand_new_file.sh")"

  t "$tool: nested new path inside root - DENY" deny \
    CLAUDE_PLUGIN_ROOT="$ROOT" -- \
    "$(edit_input "$tool" file_path "$ROOT/scripts/sub/newer/deep.sh")"

  t "$tool: file in a repo checkout - allow" allow \
    CLAUDE_PLUGIN_ROOT="$ROOT" -- \
    "$(edit_input "$tool" file_path "$OTHER/hooks/confirm_launch.sh")"

  t "$tool: file in an ordinary user project - allow" allow \
    CLAUDE_PLUGIN_ROOT="$ROOT" -- \
    "$(edit_input "$tool" file_path "$PROJECT/analysis.R")"
done

t "NotebookEdit: notebook_path inside root - DENY" deny \
  CLAUDE_PLUGIN_ROOT="$ROOT" -- \
  "$(edit_input NotebookEdit notebook_path "$ROOT/scripts/nb.ipynb")"

t "NotebookEdit: notebook_path outside root - allow" allow \
  CLAUDE_PLUGIN_ROOT="$ROOT" -- \
  "$(edit_input NotebookEdit notebook_path "$PROJECT/nb.ipynb")"

echo
echo "== symlinked root: a write reaching root through a symlink is still denied =="
LINK="$TMP/link_to_root"
ln -s "$ROOT" "$LINK"
t "write through a symlink into the root - DENY" deny \
  CLAUDE_PLUGIN_ROOT="$ROOT" -- \
  "$(edit_input Write file_path "$LINK/hooks/via_symlink.sh")"

# The other direction: CLAUDE_PLUGIN_ROOT itself set to a symlink that
# resolves to the real root - a write via the real (unresolved) path must
# still be caught because the guard resolves ROOT physically too.
t "CLAUDE_PLUGIN_ROOT itself a symlink - write via real path still DENY" deny \
  CLAUDE_PLUGIN_ROOT="$LINK" -- \
  "$(edit_input Write file_path "$ROOT/hooks/via_real_path.sh")"

echo
echo "== Bash: reads allowed, writes denied, per verb =="

t "bash <root>/tests/run_all.sh - allow (reading/executing)" allow \
  CLAUDE_PLUGIN_ROOT="$ROOT" -- \
  "$(bash_input "bash $ROOT/tests/run_all.sh")"

t "bash <root>/scripts/x.sh - allow (reading/executing)" allow \
  CLAUDE_PLUGIN_ROOT="$ROOT" -- \
  "$(bash_input "bash $ROOT/scripts/x.sh")"

t "cat <root>/hooks/confirm_launch.sh - allow" allow \
  CLAUDE_PLUGIN_ROOT="$ROOT" -- \
  "$(bash_input "cat $ROOT/hooks/confirm_launch.sh")"

t "grep -n foo <root>/hooks/confirm_launch.sh - allow" allow \
  CLAUDE_PLUGIN_ROOT="$ROOT" -- \
  "$(bash_input "grep -n foo $ROOT/hooks/confirm_launch.sh")"

t "run_all.sh redirected to /dev/null - allow (not a real write)" allow \
  CLAUDE_PLUGIN_ROOT="$ROOT" -- \
  "$(bash_input "bash $ROOT/tests/run_all.sh 2>/dev/null")"

# One case per listed write verb.
t "sed -i on a root file - DENY"    deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "sed -i 's/a/b/' $ROOT/hooks/confirm_launch.sh")"
t "redirect > into root - DENY"     deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "echo hi > $ROOT/hooks/new.sh")"
t "redirect >> into root - DENY"    deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "echo hi >> $ROOT/hooks/new.sh")"
t "tee into root - DENY"            deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "echo hi | tee $ROOT/hooks/new.sh")"
t "cp into root - DENY"             deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "cp /tmp/x $ROOT/hooks/new.sh")"
t "mv into root - DENY"             deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "mv /tmp/x $ROOT/hooks/new.sh")"
t "rm inside root - DENY"           deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "rm $ROOT/hooks/old.sh")"
t "chmod on root file - DENY"       deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "chmod +x $ROOT/hooks/new.sh")"
t "chown on root file - DENY"       deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "chown me $ROOT/hooks/new.sh")"
t "patch inside root - DENY"        deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "patch $ROOT/hooks/new.sh < /tmp/x.diff")"
t "ln into root - DENY"             deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "ln -s /tmp/x $ROOT/hooks/new.sh")"
t "truncate a root file - DENY"     deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "truncate -s 0 $ROOT/hooks/new.sh")"
t "install into root - DENY"        deny CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "install -m 644 /tmp/x $ROOT/hooks/new.sh")"

# Same verbs, but the target has nothing to do with the plugin root - must
# not be denied just because a write verb appears somewhere in the shell.
t "sed -i on an unrelated file - allow"  allow CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "sed -i 's/a/b/' $PROJECT/notes.txt")"
t "rm on an unrelated file - allow"      allow CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "rm $PROJECT/scratch.txt")"
t "cp into a repo checkout - allow"      allow CLAUDE_PLUGIN_ROOT="$ROOT" -- "$(bash_input "cp /tmp/x $OTHER/hooks/new.sh")"

echo
echo "== no jq on PATH: fail closed, exit 2, not silent =="
TMP2=$(mktemp -d)
REAL_JQ=$(command -v jq)
JQDIR=$(dirname "$REAL_JQ")
SHIMDIR="$TMP2/no_jq_bin"
mkdir -p "$SHIMDIR"
for _f in "$JQDIR"/*; do
    _b=$(basename "$_f")
    [ "$_b" = jq ] && continue
    ln -sf "$_f" "$SHIMDIR/$_b" 2>/dev/null
done
NOJQ_PATH=$(printf '%s' "$PATH" | sed "s#${JQDIR}#${SHIMDIR}#")

# The JSON is fully materialised by command substitution BEFORE it is fed to
# the hook (a heredoc, not a live pipe from python): guard_plugin_files.sh
# refuses before ever reading stdin once jq is missing, so a live pipe here
# would race python's write against the hook's early exit and intermittently
# turn a broken pipe into python's own nonzero exit status, which `pipefail`
# would then blame on the wrong command.
INPUT_JSON=$(edit_input Write file_path "$ROOT/hooks/x.sh")
printf '%-72s ' "no jq, root set - a real write is BLOCKED (exit 2), not allowed"
out=$(env CLAUDE_PLUGIN_ROOT="$ROOT" PATH="$NOJQ_PATH" bash "$H" <<<"$INPUT_JSON" 2>"$TMP2/err1")
rc=$?
if [ "$rc" = 2 ] && [ -z "$out" ]; then echo "ok (rc=2, no stdout)"; else
    echo "FAIL: rc=$rc out='$out'"; fails=$((fails + 1))
fi

printf '%-72s ' "no jq, root set - stderr names the fix, per platform"
err=$(cat "$TMP2/err1" 2>/dev/null)
if echo "$err" | grep -qF "brew install jq" && echo "$err" | grep -qF "apt install jq"; then
    echo ok
else
    echo "FAIL: stderr did not name both install commands: <<$err>>"; fails=$((fails + 1))
fi

INPUT_JSON2=$(edit_input Write file_path "$PROJECT/x.R")
printf '%-72s ' "no jq, root UNSET - still allowed (nothing to guard, no jq needed)"
out=$(env -u CLAUDE_PLUGIN_ROOT PATH="$NOJQ_PATH" bash "$H" <<<"$INPUT_JSON2" 2>"$TMP2/err2")
rc=$?
if [ "$rc" = 0 ] && [ -z "$out" ]; then echo "ok"; else
    echo "FAIL: rc=$rc out='$out'"; fails=$((fails + 1))
fi
rm -rf "$TMP2"

echo
echo "== hooks.json wiring =="
HOOKS_JSON="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/hooks/hooks.json"

printf '%-72s ' "hooks.json is valid JSON"
if jq -e . "$HOOKS_JSON" >/dev/null 2>&1; then echo ok; else
    echo "FAIL: hooks.json does not parse"; fails=$((fails + 1))
fi

printf '%-72s ' "a PreToolUse entry runs guard_plugin_files.sh on Write|Edit|MultiEdit|NotebookEdit"
MATCH=$(jq -r '
  .hooks.PreToolUse[]
  | select(.matcher | test("Write") and test("Edit") and test("MultiEdit") and test("NotebookEdit"))
  | select(.hooks[].command | test("guard_plugin_files\\.sh"))
  | .matcher
' "$HOOKS_JSON" 2>/dev/null)
if [ -n "$MATCH" ]; then echo "ok ($MATCH)"; else
    echo "FAIL: no matching PreToolUse entry found"; fails=$((fails + 1))
fi

printf '%-72s ' "a separate PreToolUse entry runs guard_plugin_files.sh on Bash"
BASH_MATCH=$(jq -r '
  .hooks.PreToolUse[]
  | select(.matcher == "Bash")
  | select(.hooks[].command | test("guard_plugin_files\\.sh"))
  | .matcher
' "$HOOKS_JSON" 2>/dev/null)
if [ -n "$BASH_MATCH" ]; then echo "ok"; else
    echo "FAIL: no Bash-matcher entry runs guard_plugin_files.sh"; fails=$((fails + 1))
fi

printf '%-72s ' "guard_plugin_files.sh entries carry timeout 5"
TIMEOUTS=$(jq -r '
  [.hooks.PreToolUse[].hooks[] | select(.command | test("guard_plugin_files\\.sh")) | .timeout]
  | unique | .[]
' "$HOOKS_JSON" 2>/dev/null)
if [ "$TIMEOUTS" = "5" ]; then echo "ok"; else
    echo "FAIL: timeouts found: <<$TIMEOUTS>>"; fails=$((fails + 1))
fi

printf '%-72s ' "the file is executable"
if [ -x "$H" ]; then echo ok; else
    echo "FAIL: hooks/guard_plugin_files.sh is not executable"; fails=$((fails + 1))
fi

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
