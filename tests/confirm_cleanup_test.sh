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
# Git Bash rewrites /bin/... arguments into Windows paths when it starts a
# native python; the hook never sees that rewrite (it reads JSON on stdin), so
# the test must not either.
export MSYS2_ARG_CONV_EXCL='*'
# The hook's own hookSpecificOutput carries Chinese text ("確認刪除" etc, see
# hooks/confirm_cleanup.sh). Every python3 -c that decodes that JSON back off
# stdin gets PYTHONIOENCODING=utf-8 (bug: false-green-tests, item 4) - under
# Windows Git Bash's default code page, python3 otherwise raises
# JSONDecodeError on that stdin, which read as this hook having failed, not as
# a test-harness encoding gap.
fails=0
t() { # t <command> <expect pass|warn|deny> <label>
  printf '%-58s ' "$3"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" | bash "$H")
  if [ -z "$out" ]; then got=pass; else
    got=$(PYTHONIOENCODING=utf-8 python3 -c "import json,sys;o=json.load(sys.stdin)['hookSpecificOutput'];print(o.get('permissionDecision','warn'))" <<<"$out")
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
# How jq is hidden without also losing bash: tests/lib/nojq_path.sh.
TMP2=$(mktemp -d); trap 'rm -rf "$TMP2"' EXIT
. "$(dirname "${BASH_SOURCE[0]}")/lib/nojq_path.sh"
NOJQ_PATH=$(nojq_path "$TMP2") || { echo "cannot build a PATH without jq"; exit 1; }

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
decision=$(PYTHONIOENCODING=utf-8 python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out" 2>/dev/null)
[ "$decision" = deny ] && echo "ok (deny)" || { echo "FAIL: expected deny, got '$decision' <<$out>>"; fails=$((fails+1)); }

printf '%-64s ' "an unparseable tool (unknown field) that looks deletion-shaped - ask"
UNKNOWN=$(python3 -c "import json,sys;print(json.dumps({'tool_name':'mcp__win__powershell','tool_input':{'script_block':sys.argv[1]}}))" "$D -rf $P/results")
out=$(echo "$UNKNOWN" | bash "$H")
decision=$(PYTHONIOENCODING=utf-8 python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out" 2>/dev/null)
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
  decision=$(PYTHONIOENCODING=utf-8 python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out")
  [ "$decision" = ask ] && echo ok || { echo "FAIL: expected permissionDecision=ask, got '$decision'"; fails=$((fails+1)); }
}
denycheck() { # denycheck <command> <label>
  printf '%-58s ' "$2"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" | bash "$H")
  first="${out:0:1}"
  if [ "$first" != "{" ]; then
    echo "FAIL: stdout did not start with '{': <<${out:0:60}>>"; fails=$((fails+1)); return
  fi
  decision=$(PYTHONIOENCODING=utf-8 python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out")
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

echo
echo "== #29: shapes that used to pass with no output at all =="
# Every case below printed nothing and exited 0 on main 12dda0c: the gate
# threw away quoted text and here-doc bodies to avoid false alarms, and a
# real delete can sit in either. Written before the fix, red on main.
t "$D -rf \"$P/results\""                         deny "#29 double-quoted protected target"
t "$D -rf '$P/results'"                           deny "#29 single-quoted protected target"
t "$D -rf \"$P/my dir/analysis\""                 deny "#29 quoted target containing a space"
t "$D -rf \"$P/work\""                            ask  "#29 quoted work/ still asks"
t "$D -rf \"\$RUN_DIR/results\""                  deny "#29 variable target still judged by its literal part"
t "$D -rf \"\$RUN_DIR/tmp_x\""                    ask  "#29 variable target pauses (ask), not a warning"
t "$(printf 'cat <<%s | bash
%s -rf %s/results
EOF
' "'EOF'" "$D" "$P")" deny "#29 here-doc piped into bash"
t "bash -c \"$D -rf $P/results\""                  deny "#29 delete inside a quoted bash -c"
t "echo '$D -rf $P/results' | sh"                   deny "#29 delete piped into sh"
t "echo \"to clean up, $D -rf the work dir\""      pass "#29 quoted prose mentioning the verb"
t "$D -rf \$RESULTS"                              ask  "#29 bare variable target pauses too"
t "echo $P/results | xargs $D -rf"                ask  "#29 xargs delete: target unknown here, pause"
t "$(printf 'ssh h bash -s <<%s\n%s -rf %s/results\nEOF\n' "'EOF'" "$D" "$P")" deny "#29 here-doc fed to ssh bash"
t "$(printf 'bash <<%s\n%s -rf %s/rawdata\nEOF\n' "'EOF'" "$D" "$P")"          deny "#29 here-doc fed to bash"
t "$(printf 'cat > notes.md <<%s\n%s -rf %s/results\nEOF\n' "'EOF'" "$D" "$P")" pass "#29 here-doc written to a file is prose"
t "$(printf 'python3 - <<%s\nimport shutil\nshutil.rmtree(\"%s/results\")\nEOF\n' "'EOF'" "$P")" ask "#29 python here-doc that deletes a tree"
t "grep -rn 'shutil.rmtree' scripts/"             pass "#29 searching for rmtree is not deleting"

tps() { # tps <powershell command> <expect> <label> - through the PowerShell tool
  printf '%-58s ' "$3"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_name':'PowerShell','tool_input':{'command':sys.argv[1]}}))" "$1" | bash "$H")
  if [ -z "$out" ]; then got=pass; else
    got=$(PYTHONIOENCODING=utf-8 python3 -c "import json,sys;o=json.load(sys.stdin)['hookSpecificOutput'];print(o.get('permissionDecision','warn'))" <<<"$out" 2>/dev/null)
  fi
  [ "$got" = "$2" ] && echo "ok ($got)" || { echo "FAIL: expected $2, got $got"; fails=$((fails+1)); }
}
tps "Remove-Item -Recurse -Force $P/results"      deny "#29 PowerShell Remove-Item on results/"
tps 'Remove-Item -Recurse C:\lab\proj\rawdata'    deny "#29 PowerShell, backslash path"
tps 'rd /s /q C:\lab\proj\analysis'               deny "#29 cmd-style rd /s"
tps "Remove-Item -Recurse $P/work"                ask  "#29 PowerShell on work/ asks"
tps 'Get-ChildItem C:\lab\proj\results'           pass "#29 listing results/ is harmless"

echo
echo "== #29 acceptance round 2: bypasses and false alarms the reviewer found =="
# All reproduced by the independent reviewer on the first fix (939576b):
# the upper block passed silently, the lower block was a new false alarm.
t "/bin/$D -rf $P/results"                        deny "#29b the verb with a path"
t "\\$D -rf $P/results"                           deny "#29b the verb escaped to skip an alias"
t "\"/bin/$D\" -rf $P/results"                    deny "#29b the verb itself in quotes"
t "command $D -rf $P/results"                     deny "#29b command <verb>"
t "sudo -u bob $D -rf $P/results"                 deny "#29b sudo with an option"
t "$D -r -f '$P/rawdata'/"                        deny "#29b quote glued to a trailing slash"
t "$D -rf '$P/'results"                           deny "#29b quote closed before the last component"
t "$D -rf $P/res\"ults\""                         deny "#29b quotes inside the name"
t "$D -rf $P/{results,work}"                      deny "#29b brace expansion naming results"
t "env X=\"'\" $D -rf $P/results Y\"'\""           deny "#29b stray quotes around the verb"
t "find $P/results -exec $D -rf {} +"             deny "#29b find -exec <verb>"
t "unlink $P/results/multiqc.html"                deny "#29b unlink"
t "truncate -s 0 $P/results/counts.tsv"           deny "#29b truncate"
t "echo \$($D -rf $P/results)"                    deny "#29b the verb inside \$(...)"
t "perl -e 'system(\"$D -rf $P/results\")'"       deny "#29b perl -e system(...)"
t "python3 -c \"import os; os.system('$D -rf $P/results')\"" deny "#29b python -c os.system(...)"
t "$(printf 'timeout 60 bash <<%s\n%s -rf %s/results\nEOF\n' "'EOF'" "$D" "$P")"  deny "#29b here-doc into timeout bash"
t "$(printf 'sudo -u bob bash <<%s\n%s -rf %s/results\nEOF\n' "'EOF'" "$D" "$P")" deny "#29b here-doc into sudo -u bash"
t "\$(which $D) -rf $P/results"                   ask  "#29b command word is a substitution"
t "R=$D; \$R -rf $P/results"                      ask  "#29b command word is a variable"
t "$D -rf $P/res*"                                ask  "#29b a glob that can match results/"
t "$D -f /tmp/foo*"                               pass "#29b a glob that cannot"
tps "ri -r C:\\lab\\proj\\results"                deny "#29b PowerShell alias ri"
tps "powershell -Command \"Remove-Item -Recurse $P/results\"" deny "#29b powershell -Command payload"
tps "gci C:\\lab\\proj\\results | Remove-Item -Recurse -Force" ask "#29b Remove-Item fed by the pipeline"
tps "[System.IO.Directory]::Delete('C:\\lab\\proj\\results', \$true)" ask "#29b .NET Delete call"
echo
echo "== #29 acceptance round 3 =="
t "srun $D -rf $P/results"                        deny "#29c srun wrapper (a regression in round 2)"
t "singularity exec x.sif $D -rf $P/results"      deny "#29c singularity exec wrapper"
t "parallel $D -rf ::: $P/results"                deny "#29c GNU parallel"
t "flock /tmp/l $D -rf $P/results"                deny "#29c flock wrapper"
t "doas $D -rf $P/results"                        deny "#29c doas"
t "ionice -c3 $D -rf $P/results"                  deny "#29c ionice"
t "bash -e -c '$D -rf $P/results'"                deny "#29c bash with options before -c"
t "bash --norc -c '$D -rf $P/results'"            deny "#29c bash --norc -c"
t "bash <<< '$D -rf $P/results'"                  deny "#29c here-string into bash"
t "echo '$D -rf $P/results' |& bash"              deny "#29c |& into bash"
t "echo '$D -rf $P/results' | env bash"           deny "#29c | env bash"
t "bash <(echo '$D -rf $P/results')"              deny "#29c process substitution read by bash"
t "python3 -u -c \"import shutil; shutil.rmtree('$P/results')\"" ask "#29c python with options before -c"
t "python3 -c \"from shutil import rmtree; rmtree('$P/results')\"" ask "#29c bare rmtree(...)"
t "perl -MFile::Path -e 'rmtree(\"$P/results\")'" ask  "#29c perl rmtree"
t "echo \$(echo \$(echo \$(echo \$(echo \$(echo \$($D -rf $P/results))))))" deny "#29c deeply nested \$(...)"
t "$(printf "grep -c '<<EOF' notes.sh\n%s -rf %s/results" "$D" "$P")" deny "#29c a quoted <<EOF is not a here-doc"
t "$(printf 'python3 - <<%s\nresults = 1\ndel results\nEOF\n' "'EOF'")" pass "#29c python 'del results' under Bash"

# #29 round 4: regressions against main found by the third review.
t "srun find $P/results -mindepth 1 -delete"       deny "#29d find -delete behind srun (main: deny)"
t "ionice -c3 find $P/results -delete"             deny "#29d find -delete behind ionice"
t "singularity exec x.sif find $P/analysis -type f -delete" deny "#29d find -delete behind singularity exec"
t "srun rsync -a --delete /tmp/empty/ $P/results/" deny "#29d rsync --delete behind srun (main: deny)"
t "ionice -c3 rsync -a --delete /tmp/empty/ $P/rawdata/" deny "#29d rsync --delete behind ionice"
t "srun mv $P/rawdata/a.fastq.gz /tmp/"            warn "#29d mv behind srun still warns (main: warn)"
t "$(printf 'srun %s -rf %s/results "x\ny"' "$D" "$P")" deny "#29d a multi-line quoted argument after the target"

# #29 round 3: a gate past its timeout (30 s) is cancelled and the command
# runs. Round 2 took ~50 s on a 120-line script under Git Bash. A 200-line
# script must be judged well inside the limit, on every platform we test.
LONGBODY=$(for i in $(seq 1 200); do echo "x$i = [a for a in range($i)]  # line $i"; done)
LONGCMD=$(printf 'python3 - <<%s\n%s\n%s -rf %s/results\nEOF\n' "'EOF'" "$LONGBODY" "$D" "$P")
printf '%-58s ' "#29c a 200-line here-doc is judged in under 15 s"
t0=$(date +%s)
out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$LONGCMD" | bash "$H")
t1=$(date +%s)
if [ $((t1 - t0)) -lt 15 ] && grep -q '"deny"' <<<"$out"; then echo "ok ($((t1 - t0)) s, deny)"; else
  echo "FAIL: $((t1 - t0)) s, output <<${out:0:60}>>"; fails=$((fails+1)); fi

t "grep -rn del $P/results/"                      pass "#29b grep for 'del' is not a delete"
t "grep -i RD $P/analysis/de.tsv"                 pass "#29b grep for 'RD' is not a delete"
t "grep -n 'os.remove(' scripts/x.py"             pass "#29b searching for a delete call"
t "grep -rn \"unlink(\" scripts/"                 pass "#29b searching for unlink("
t "git commit -m \"use shutil.rmtree( on work\""  pass "#29b a commit message naming a call"
t "$(printf 'python3 - <<%s\n# %s the old results/ by hand\nprint(1)\nEOF\n' "'EOF'" "$D")" pass "#29b a comment in a python here-doc"
t "ls -la $P/results && cat $P/results/x.html"    pass "#29b reading results/"
t "jq '.a | .b' $P/results/x.json"                pass "#29b jq filter with a pipe"
t "awk '{a=1; b=2}' $P/results/x.tsv"             pass "#29b awk program with a semicolon"

[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
