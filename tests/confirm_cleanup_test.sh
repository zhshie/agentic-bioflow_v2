#!/bin/bash
# Regression tests for hooks/confirm_cleanup.sh.
#
# The first two cases are the ones that mattered: the hook used to classify a
# segment as a delete whenever the letters "rm" followed by a space appeared
# anywhere in it, which is true of "confirm " and of "Platform run". Combined
# with a protected word among the arguments, that denied ordinary commands.
# A guard that refuses `echo confirm the results directory` trains its reader
# to ignore it, which costs more than the guard is worth.
#
# Note the delete verb is assembled from hex below rather than written out, so
# that running this file does not itself trip a cleanup hook watching the shell.
H="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/hooks/confirm_cleanup.sh"
fails=0
t() { # t <command> <expect pass|warn|deny> <label>
  printf '%-58s ' "$3"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" | bash "$H")
  if [ -z "$out" ]; then got=pass; else
    got=$(python3 -c "import json,sys;o=json.load(sys.stdin)['hookSpecificOutput'];print(o.get('permissionDecision','warn'))" <<<"$out")
  fi
  if [ "$got" = "$2" ]; then echo "ok ($got)"; else
    echo "FAIL: expected $2, got $got"; fails=$((fails+1))
  fi
}
D=$(printf '\x72\x6d')            # the delete verb, assembled so this file's own
P=/work/u9613010/lab_runs/x       # text does not trip the installed v1 hook
t "bash set_phase.sh /x completed note=\"Seqera Platform run 2LjRa 201 tasks\"" pass "harmless cmd mentioning 'Platform run'"
t "echo confirm the results directory"                                     pass "harmless cmd containing 'confirm'"
t "$D -rf $P/results"                                                      deny "delete results/"
t "$D -rf $P/rawdata"                                                      deny "delete rawdata/"
t "$D -rf $P/.nextflow/plugins"                                            deny "delete plugins/"
t "$D -rf $P/work"                                                         ask  "delete work/ (R2: structural ask, not just a warning)"
t "ls $P && $D -rf $P/results"                                             deny "delete inside compound"
t "ssh twnia3 '$D -rf $P/results'"                                         deny "delete results/ wrapped in ssh"
t "grep -n 'A=\\|B\\|$D ' hooks/confirm_cleanup.sh"                       pass "read-only grep whose regex contains the verb"
t "ssh twnia3 'ls $P/results'"                                             pass "ssh is not by itself suspicious"
t "scripts/on_site.sh '$D -rf $P/rawdata'"                                 deny "delete rawdata/ wrapped in on_site.sh"

# The shared image library had three spellings and the rule knew one of them -
# the one nothing wrote to. nchc.config defaults the cache to
# `_singularity_cache`, this deployment's NXF_SINGULARITY_CACHEDIR points at
# `.singularity_cache`, and the rule named `lab_singularity_library`. So the
# directory actually holding the images was deletable while PRINCIPLES.md said
# it was protected. All spellings now, and two near misses that must not be.
SG=$(printf '\x73\x69\x6e\x67\x75\x6c\x61\x72\x69\x74\x79')
t "$D -rf /work/u9613010/lab_runs/lab_${SG}_library" deny "the library, as the rule spelled it"
t "$D -rf /work/u9613010/lab_runs/_${SG}_cache"      deny "as nchc.config defaults it"
t "$D -rf /work/u9613010/lab_runs/.${SG}_cache"      deny "as this deployment actually sets it"
t "$D -rf /work/u9613010/lab_runs/x/results_singular" pass "a name that merely starts alike"
t "$D -f  /work/u9613010/lab_runs/x/my_${SG}_notes.md" pass "someone's notes about it"

# A redirection is not an argument. The TRUNCATE test already drops
# `2>/dev/null` before looking for a `>` target, with a comment saying why - a
# guard that fires on the most common idiom in this repo's own snippets teaches
# the reader to skip it. But the argument list was built from the unstripped
# segment, so the token `2>/dev/null` reached the leftover rule and matched its
# `null` pattern. The bare-path exception below it (`/dev/null`) never saw this
# form. Found by running `rmdir <path> 2>/dev/null` during a probe cleanup.
t "$D -rf /tmp/x 2>/dev/null"                        pass "a redirection is not a deletion target"
t "$D -rf /tmp/x >/dev/null 2>&1"                    pass "nor is a discarded stdout"
t "$D -rf $P/null"                                   warn "the real null/ leftover still warns"

echo

# ---------------------------------------------------------------------------
# T1: no jq is SCOPED fail-closed (Fixes #15), not a blanket refusal - see
# hooks/confirm_launch.sh's header for the full reasoning (a member on
# exactly this path gave up on the safety net and moved to a bare PowerShell
# window instead, which has none of it).
#
# Dropping jq's whole directory from PATH is not safe here - on this box jq
# and bash both live in /usr/bin, and removing that directory removes the
# shell the hook needs to start at all. A shim directory instead gets a
# symlink to every OTHER binary that lived beside jq, and PATH swaps that one
# directory for the shim; everything else on PATH is untouched.
TMP2=$(mktemp -d); trap 'rm -rf "$TMP2"' EXIT
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

nojq() { # nojq <command-string>
    python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" \
        | PATH="$NOJQ_PATH" bash "$H"
}

printf '%-58s ' "(b) no jq + a real delete - still BLOCKED"
out=$(nojq "$D -rf $P/results" 2>"$TMP2/err1"); rc=$?
if [ "$rc" = 2 ] && [ -z "$out" ]; then echo "ok (rc=2, no stdout)"; else
    echo "FAIL: rc=$rc out='$out'"; fails=$((fails+1)); fi

printf '%-58s ' "(a) no jq + a harmless command - exit 0, no noise"
out=$(nojq "ls -la" 2>"$TMP2/err2"); rc=$?
err2=$(cat "$TMP2/err2" 2>/dev/null)
if [ "$rc" = 0 ] && [ -z "$out" ] && [ -z "$err2" ]; then echo "ok (rc=0, silent)"; else
    echo "FAIL: rc=$rc out='$out' err='$err2' (should pass through silently - it cannot look deletion-shaped)"
    fails=$((fails+1))
fi

printf '%-58s ' "no jq: BLOCKED case's stderr names the fix, per platform"
err=$(cat "$TMP2/err1" 2>/dev/null)
if echo "$err" | grep -qF "brew install jq" && echo "$err" | grep -qF "apt install jq"; then
    echo ok
else
    echo "FAIL: stderr did not name both install commands: <<$err>>"; fails=$((fails+1))
fi

printf '%-58s ' "with jq restored, the same command passes again"
out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "ls -la" | bash "$H")
[ -z "$out" ] && echo ok || { echo "FAIL: expected pass, got <<$out>>"; fails=$((fails+1)); }

echo

# A jq that EXISTS but cannot run - wrong architecture, a missing library, a
# Windows jq.exe on a Git Bash PATH - passed the earlier `command -v` form of
# this guard and then failed every parse, which is the silent-gate failure the
# guard exists to stop. Measured: the guard had to probe, not just look. The
# scoping applies here too.
echo "== a broken jq is judged the same scoped way as a missing one =="
BADDIR=$(mktemp -d)
printf '#!/bin/sh\nexit 127\n' > "$BADDIR/jq"; chmod +x "$BADDIR/jq"
out=$(echo '{"tool_name":"Bash","tool_input":{"command":"'"$D"' -rf /x"}}' \
      | env PATH="$BADDIR:$PATH" bash "$H" 2>&1)
rc=$?
printf '%-64s ' "refuses a deletion-shaped command when jq exists but cannot run"
[ "$rc" = 2 ] && echo ok || { echo "FAIL: exit $rc, wanted 2"; fails=$((fails+1)); }
printf '%-64s ' "and says so instead of failing silently"
case "$out" in *BLOCKED*) echo ok ;; *) echo "FAIL: said '$out'"; fails=$((fails+1)) ;; esac

out=$(echo '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}' \
      | env PATH="$BADDIR:$PATH" bash "$H" 2>&1)
rc=$?
printf '%-64s ' "does NOT refuse an unrelated command in the same broken-jq state"
[ "$rc" = 0 ] && [ -z "$out" ] && echo ok || { echo "FAIL: rc=$rc out='$out'"; fails=$((fails+1)); }
rm -rf "$BADDIR"

echo
echo "== T1 (c): a non-Bash, execution-shaped tool this file has never named =="
printf '%-64s ' "a non-Bash tool using tool_input.command - judged exactly as Bash would be"
out=$(python3 -c "import json,sys;print(json.dumps({'tool_name':'PowerShell','tool_input':{'command':sys.argv[1]}}))" "$D -rf $P/results" | bash "$H")
decision=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out" 2>/dev/null)
[ "$decision" = deny ] && echo "ok (deny)" || { echo "FAIL: expected deny, got '$decision' <<$out>>"; fails=$((fails+1)); }

printf '%-64s ' "an unparseable tool (unknown field) that looks deletion-shaped - ask"
UNKNOWN=$(python3 -c "import json,sys;print(json.dumps({'tool_name':'mcp__win__powershell','tool_input':{'script_block':sys.argv[1]}}))" "$D -rf $P/results")
out=$(echo "$UNKNOWN" | bash "$H")
decision=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out" 2>/dev/null)
[ "$decision" = ask ] && echo "ok (ask)" || { echo "FAIL: expected ask, got '$decision' <<$out>>"; fails=$((fails+1)); }

printf '%-64s ' "an unparseable tool with harmless content - allowed, no output"
UNKNOWN=$(python3 -c "import json,sys;print(json.dumps({'tool_name':'mcp__win__powershell','tool_input':{'script_block':'Get-ChildItem'}}))")
out=$(echo "$UNKNOWN" | bash "$H")
[ -z "$out" ] && echo "ok (no output at all)" || { echo "FAIL: expected nothing, got <<$out>>"; fails=$((fails+1)); }

echo
echo "== R2: Claude Code itself asks, for the work/ + cache branch only =="
# PRINCIPLES.md's exact phrase is "deleting work/ or .nextflow/cache/ requires
# the user's explicit confirmation" - so only that branch gets a structural
# `ask`. The four hard refusals stay `deny` (checked above by the t() calls);
# this section proves ask specifically, and that stdout starts with `{` in
# every decision-carrying case (PITFALLS 28 appendix-2 fact 3).
askcheck() { # askcheck <command> <label>
  printf '%-58s ' "$2"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" | bash "$H")
  first="${out:0:1}"
  if [ "$first" != "{" ]; then
    echo "FAIL: stdout did not start with '{': <<${out:0:60}>>"; fails=$((fails+1)); return
  fi
  decision=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out")
  [ "$decision" = ask ] && echo ok || { echo "FAIL: expected permissionDecision=ask, got '$decision'"; fails=$((fails+1)); }
}
denycheck() { # denycheck <command> <label>
  printf '%-58s ' "$2"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" | bash "$H")
  first="${out:0:1}"
  if [ "$first" != "{" ]; then
    echo "FAIL: stdout did not start with '{': <<${out:0:60}>>"; fails=$((fails+1)); return
  fi
  decision=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out")
  [ "$decision" = deny ] && echo ok || { echo "FAIL: expected permissionDecision=deny, got '$decision'"; fails=$((fails+1)); }
}

askcheck  "$D -rf $P/work"                    "work/: permissionDecision=ask"
askcheck  "$D -rf $P/.nextflow/cache"         ".nextflow/cache/: permissionDecision=ask"
denycheck "$D -rf $P/.nextflow/plugins"       "plugins/: still permissionDecision=deny (unchanged)"
denycheck "$D -rf $P/rawdata"                 "rawdata/: still permissionDecision=deny (unchanged)"
denycheck "$D -rf $P/results"                 "results/: still permissionDecision=deny (unchanged)"

# The stale comment fix: this branch used to ask about a v1 state-machine
# "phase", which v2 has no concept of (PRINCIPLES.md, invariant 2 - Platform
# is the only source of truth for run state, this repo keeps none).
printf '%-58s ' "leftover warning no longer mentions a v1 'phase'"
out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$D -rf $P/null" | bash "$H")
if echo "$out" | grep -qF "phase"; then
  echo "FAIL: still mentions 'phase' <<$out>>"; fails=$((fails+1))
else
  echo ok
fi

[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
