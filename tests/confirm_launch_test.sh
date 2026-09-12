#!/bin/bash
# Regression tests for hooks/confirm_launch.sh.
#
# The gate decides per segment, splitting on `|` among others, so that
# `cat notes.txt && tw launch ...` still stops. That splitting is also how it
# went wrong: a regex passed to grep contains `|`, and the middle of
#
#     grep -E 'slurm|sbatch|squeue' commands/*.md
#
# became a segment reading exactly like a submission. The gate fired on a
# read-only search, twice in one session. A gate that cries wolf on `grep` is
# a gate people learn to click through, which costs more than it protects.
#
# The fix strips quoted strings before segmenting - but not when a shell is
# asked to re-interpret them, or `bash -c "tw launch ..."` would slip past.
# Both directions are tested below; the second matters more.
#
# The second failure this file exists for is narrower and worse: the gate knew
# only three ways to start a run - `tw launch`, `sbatch`, `nextflow run`. But
#
#     tw runs relaunch -i 344PjpDnrQiz4U
#
# starts a real pipeline run and matched none of them, so the gate stayed
# silent on the one command that costs the most when issued by accident: it
# re-submits work that has already burned an allocation. A gate that covers
# most of the ways to start a run is not a gate; the miss is invisible from
# the inside, because nothing is printed when nothing fires.
#
# Trigger words are assembled from hex so that running this file does not set
# off the gate installed in the caller's own shell.
H="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/hooks/confirm_launch.sh"
LAUNCH="tw $(printf '\x6c\x61\x75\x6e\x63\x68')"
NFRUN="nextflow $(printf '\x72\x75\x6e')"
RELAUNCH="tw runs $(printf '\x72\x65\x6c\x61\x75\x6e\x63\x68')"
SB=$(printf '\x73\x62\x61\x74\x63\x68')
fails=0

t() { # t <command> <expect gate|pass> <label>
  printf '%-56s ' "$3"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" | bash "$H")
  got=pass; [ -n "$out" ] && got=gate
  if [ "$got" = "$2" ]; then echo "ok ($got)"; else
    echo "FAIL: expected $2, got $got"; fails=$((fails+1))
  fi
}

t "grep -E 'slurm|$SB|squeue' commands/*.md"          pass "regex containing the verb, in quotes"
t "grep -rn \"$SB\" docs/"                            pass "regex containing the verb, double quotes"
t "cat launch_notes.md"                               pass "reading a file about launching"
t "$(printf 'cat > g.md <<%s\nrun: %s x\nEOF\n' "'EOF'" "$LAUNCH")" pass "here-doc that mentions launching"
t "$LAUNCH https://github.com/nf-core/rnaseq --disable-optimization" gate "a real launch"
t "cat notes.txt && $LAUNCH x --disable-optimization"  gate "launch inside a compound command"
t "bash -c \"$LAUNCH x --disable-optimization\""       gate "launch hidden in a quoted bash -c"
t "eval \"$LAUNCH x --disable-optimization\""          gate "launch hidden in eval"
t "$NFRUN main.nf"                                    gate "a direct nextflow run"
t "$SB driver.sh"                                     gate "a bare scheduler submission"
t "ssh twnia3 '$LAUNCH x --disable-optimization'"      gate "launch wrapped in ssh"
t "scripts/on_site.sh '$LAUNCH x --disable-optimization'" gate "launch wrapped in on_site.sh"
t "$RELAUNCH -i 344PjpDnrQiz4U"                        gate "a relaunch of an existing run"
t "cat notes.txt && $RELAUNCH -i 344PjpDnrQiz4U"      gate "relaunch inside a compound command"
t "ssh twnia3 '$RELAUNCH -i 344PjpDnrQiz4U'"          gate "relaunch wrapped in ssh"
t "grep -n '$RELAUNCH' notes.md"                      pass "read-only mention of the relaunch verb"
t "grep -rn \"ssh\" docs/"                              pass "read-only search for the word ssh"
t "grep -E 'a|$SB|b' ssh_config.md"                   pass "regex with the verb, filename contains ssh"

# A third failure, found by trying it rather than by it happening: the trigger
# logic now lives in a sourced file, and a sourced file can go missing. When it
# did, `is_launch_command` was command-not-found, 127 satisfied the `|| exit 0`,
# and the gate vanished for EVERY command with nothing printed - the same shape
# as the relaunch miss above, but total. So the load is fail-closed, and this
# case is what keeps it that way.
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/hooks"
cp "$(dirname "$H")/confirm_launch.sh" "$TMP/hooks/"
cp "$(dirname "$H")/strip_heredocs.awk" "$TMP/hooks/" 2>/dev/null
# launch_trigger.sh deliberately NOT copied.

printf '%-56s ' "a missing trigger helper says so instead of going quiet"
out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" \
        "$LAUNCH https://github.com/nf-core/rnaseq" | bash "$TMP/hooks/confirm_launch.sh" 2>/dev/null)
if grep -qF "GATE NOT WORKING" <<<"${out:-<empty>}"; then echo "ok"
else echo "FAIL: gate went silent with its helper missing  <<${out:-<empty>}>>"; fails=$((fails+1)); fi

printf '%-56s ' "and says it about harmless commands too, not just launches"
out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" \
        "ls -la" | bash "$TMP/hooks/confirm_launch.sh" 2>/dev/null)
if grep -qF "GATE NOT WORKING" <<<"${out:-<empty>}"; then echo "ok"
else echo "FAIL: broken gate stayed quiet on a non-launch  <<${out:-<empty>}>>"; fails=$((fails+1)); fi

echo

# ---------------------------------------------------------------------------
# Z2: the LAB_RUNS_DIR warning must not cry wolf under reach: ssh/none, and
# must not change under reach: local.
Z2TMP=$(mktemp -d); trap 'rm -rf "$Z2TMP" "$TMP" 2>/dev/null' EXIT

mksettings() { # mksettings <file> <reach-value-or-empty>
    [ -n "$2" ] && printf 'reach: %s\n' "$2" > "$1" || : > "$1"
}
mksettings "$Z2TMP/ssh.yaml"   ssh
mksettings "$Z2TMP/none.yaml"  none
mksettings "$Z2TMP/local.yaml" local
mksettings "$Z2TMP/empty.yaml" ""

z2run() { # z2run <settings-file>
    env -u LAB_RUNS_DIR LAB_SETTINGS_FILE="$1" \
        python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" \
                 "$LAUNCH https://github.com/nf-core/rnaseq --disable-optimization" \
        | env -u LAB_RUNS_DIR LAB_SETTINGS_FILE="$1" bash "$H"
}

out=$(z2run "$Z2TMP/ssh.yaml")
printf '%-56s ' "reach: ssh, LAB_RUNS_DIR unset - no false warning"
echo "$out" | grep -qF "LAB_RUNS_DIR is not set" && { echo "FAIL: warning still fired"; fails=$((fails+1)); } || echo ok

out=$(z2run "$Z2TMP/none.yaml")
printf '%-56s ' "reach: none, LAB_RUNS_DIR unset - no false warning"
echo "$out" | grep -qF "LAB_RUNS_DIR is not set" && { echo "FAIL: warning still fired"; fails=$((fails+1)); } || echo ok

out=$(z2run "$Z2TMP/local.yaml")
printf '%-56s ' "reach: local, LAB_RUNS_DIR unset - warning UNCHANGED"
echo "$out" | grep -qF "LAB_RUNS_DIR is not set" && echo ok || { echo "FAIL: warning stopped firing under local"; fails=$((fails+1)); }

out=$(z2run "$Z2TMP/empty.yaml")
printf '%-56s ' "no reach key at all (existing deployments) - defaults local, warns"
echo "$out" | grep -qF "LAB_RUNS_DIR is not set" && echo ok || { echo "FAIL: default-local behaviour changed"; fails=$((fails+1)); }

# ---------------------------------------------------------------------------
# No jq: fail CLOSED (PITFALLS 28), not the old silent pass-through.
#
# Simply dropping jq's directory from PATH is not safe here: on this box jq
# and bash both live in /usr/bin, so removing the directory removes the shell
# the hook needs to even start. Instead, a shim directory gets a symlink to
# every OTHER binary that was in jq's directory, and PATH swaps that one
# directory for the shim - everything else on PATH is untouched.
REAL_JQ=$(command -v jq)
JQDIR=$(dirname "$REAL_JQ")
SHIMDIR="$TMP/no_jq_bin"
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

printf '%-56s ' "no jq: a real launch is BLOCKED, not silently allowed"
out=$(nojq "$LAUNCH x --disable-optimization" 2>"$TMP/nojq_launch_err"); rc=$?
err=$(cat "$TMP/nojq_launch_err" 2>/dev/null)
if [ "$rc" = 2 ] && [ -z "$out" ]; then echo "ok (rc=2, no stdout)"; else
    echo "FAIL: rc=$rc out='$out'"; fails=$((fails+1)); fi

printf '%-56s ' "no jq: an unrelated command is ALSO blocked, not waved through"
out=$(nojq "ls -la" 2>"$TMP/nojq_ls_err"); rc=$?
err=$(cat "$TMP/nojq_ls_err" 2>/dev/null)
if [ "$rc" = 2 ]; then echo "ok (rc=2)"; else
    echo "FAIL: rc=$rc (should refuse even harmless commands - it cannot tell them apart without jq)"
    fails=$((fails+1))
fi

printf '%-56s ' "no jq: stderr names the fix, per platform"
if echo "$err" | grep -qF "brew install jq" && echo "$err" | grep -qF "apt install jq"; then
    echo ok
else
    echo "FAIL: stderr did not name both install commands: <<$err>>"; fails=$((fails+1))
fi

printf '%-56s ' "with jq restored, the same command passes again"
out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "ls -la" | bash "$H")
[ -z "$out" ] && echo ok || { echo "FAIL: expected pass, got <<$out>>"; fails=$((fails+1)); }

echo

# A jq that EXISTS but cannot run - wrong architecture, a missing library, a
# Windows jq.exe on a Git Bash PATH - passed the earlier `command -v` form of
# this guard and then failed every parse, which is the silent-gate failure the
# guard exists to stop. Measured: the guard had to probe, not just look.
echo "== a broken jq is as bad as no jq =="
BADDIR=$(mktemp -d)
printf '#!/bin/sh\nexit 127\n' > "$BADDIR/jq"; chmod +x "$BADDIR/jq"
out=$(echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /x"}}' \
      | env PATH="$BADDIR:$PATH" bash "$H" 2>&1)
rc=$?
rm -rf "$BADDIR"
printf '%-64s ' "refuses when jq exists but cannot run"
[ "$rc" = 2 ] && echo ok || { echo "FAIL: exit $rc, wanted 2"; fails=$((fails+1)); }
printf '%-64s ' "and says so instead of failing silently"
case "$out" in *BLOCKED*) echo ok ;; *) echo "FAIL: said '$out'"; fails=$((fails+1)) ;; esac

[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
