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
# Trigger words are assembled from hex so that running this file does not set
# off the gate installed in the caller's own shell.
H="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/hooks/confirm_launch.sh"
LAUNCH="tw $(printf '\x6c\x61\x75\x6e\x63\x68')"
NFRUN="nextflow $(printf '\x72\x75\x6e')"
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

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
