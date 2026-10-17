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
# #62: tests/confirm_cleanup_behind_heredoc_test.sh runs this whole file again with
# every judged command placed after a large here-doc (CLEANUP_TEST_PREFIX_FILE),
# which is the path where the guard filters segments before judging them. Each
# case must get the same verdict there.
PFX=""
if [ -n "${CLEANUP_TEST_PREFIX_FILE:-}" ]; then PFX=$(cat "$CLEANUP_TEST_PREFIX_FILE"; echo x); PFX=${PFX%x}; fi
t() { # t <command> <expect pass|warn|deny> <label>
  printf '%-58s ' "$3"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$PFX$1" | bash "$H")
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
echo "== jq present but broken in other ways (jq-broken-cleanup): fail closed, say so =="
# A jq that runs but answers wrongly is the silent failure the probe above exists
# to stop, in a form the probe did not catch. Each shim below is a jq on PATH;
# a delete must be refused (exit 2 naming jq, as with no jq) or paused (ask/deny),
# never let through; an unrelated command still passes.
REALJQ=$(command -v jq)
BJ=$(mktemp -d)
bjshim() { # bjshim <name> <bash body>
  mkdir -p "$BJ/$1"; printf '#!/bin/bash\n%s\n' "$2" > "$BJ/$1/jq"; chmod +x "$BJ/$1/jq"
}
bjshim braces   'echo "{}"'
bjshim garbage  'echo "jq: something odd happened"'
bjshim silent   'exit 0'
bjshim emptycmd 'for a in "$@"; do [ "$a" = -js ] && { printf "Bash\037\037"; exit 0; }; done; exec "'"$REALJQ"'" "$@"'
bjshim cmdfail  'for a in "$@"; do case "$a" in -js|*tool_input.command*) exit 4 ;; esac; done; exec "'"$REALJQ"'" "$@"'
bjshim emitjunk 'for a in "$@"; do [ "$a" = -n ] && { echo "{}"; exit 0; }; done; exec "'"$REALJQ"'" "$@"'
bj() { # bj <shim|nojq> <command> -> BJV: blocked | asked | pass | other
  local p rc o e
  if [ "$1" = nojq ]; then p=$NOJQ_PATH; else p="$BJ/$1:$PATH"; fi
  o=$(python3 -c "import json,sys;print(json.dumps({'tool_name':'Bash','tool_input':{'command':sys.argv[1]}}))" "$2" \
      | PATH="$p" bash "$H" 2>"$BJ/err"); rc=$?
  e=$(cat "$BJ/err")
  BJERR=$e
  if [ "$rc" = 2 ] && [[ $e == *BLOCKED*jq* ]]; then BJV=blocked
  elif [ "$rc" = 0 ] && [[ $o == *'"permissionDecision"'*'"ask"'* || $o == *'"permissionDecision"'*'"deny"'* ]]; then BJV=asked
  elif [ "$rc" = 0 ] && [ -z "$o" ] && [ -z "$e" ]; then BJV=pass
  else BJV="other (rc=$rc out=${o:0:40})"; fi
}
ML=$(printf 'echo start\n%s -rf %s/results' "$D" "$P")
for s in braces garbage silent emptycmd cmdfail emitjunk; do
  printf '%-64s ' "jq that $s: a delete is refused or paused"
  bj "$s" "$D -rf $P/results"
  case "$BJV" in blocked|asked) echo "ok ($BJV)" ;; *) echo "FAIL: $BJV"; fails=$((fails+1)) ;; esac
  printf '%-64s ' "jq that $s: a delete on a later line too"
  bj "$s" "$ML"
  case "$BJV" in blocked|asked) echo "ok ($BJV)" ;; *) echo "FAIL: $BJV"; fails=$((fails+1)) ;; esac
  printf '%-64s ' "jq that $s: an unrelated command still passes"
  bj "$s" "ls -la"
  [ "$BJV" = pass ] && echo ok || { echo "FAIL: $BJV"; fails=$((fails+1)); }
done
printf '%-64s ' "a refusal for a wrong answer names jq and the fix"
bj braces "$D -rf $P/results"
if [ "$BJV" = blocked ] && [[ $BJERR == *"apt install jq"* ]]; then echo ok; else echo "FAIL: $BJV <<${BJERR:0:80}>>"; fails=$((fails+1)); fi
# A Windows jq.exe ends its lines with CR: the probe must still accept its answer
# (the one-call read is forced off here, so the probe decides).
bjshim crlf 'for a in "$@"; do [ "$a" = -js ] && exit 4; [ "$a" = .abf ] && { "'"$REALJQ"'" "$@" | sed "s/\$/\r/"; exit; }; done; exec "'"$REALJQ"'" "$@"'
printf '%-64s ' "jq that answers the probe with a trailing CR: judged in full"
bj crlf "$D -f /tmp/x.txt"; a=$BJV; bj crlf "$D -rf $P/results"
[ "$a" = pass ] && [ "$BJV" = asked ] && echo ok || { echo "FAIL: harmless $a, results $BJV <<${BJERR:0:60}>>"; fails=$((fails+1)); }
printf '%-64s ' "no jq: a delete on a later line is refused too"
bj nojq "$ML"
[ "$BJV" = blocked ] && echo ok || { echo "FAIL: $BJV"; fails=$((fails+1)); }
printf '%-64s ' "no jq: truncate / unlink are delete-shaped too"
bj nojq "truncate -s 0 $P/results/x.tsv"; a=$BJV; bj nojq "unlink $P/results/x.tsv"
[ "$a" = blocked ] && [ "$BJV" = blocked ] && echo ok || { echo "FAIL: truncate $a, unlink $BJV"; fails=$((fails+1)); }
rm -rf "$BJ"

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
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$PFX$1" | bash "$H")
  first="${out:0:1}"
  if [ "$first" != "{" ]; then
    echo "FAIL: stdout did not start with '{': <<${out:0:60}>>"; fails=$((fails+1)); return
  fi
  decision=$(PYTHONIOENCODING=utf-8 python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out")
  [ "$decision" = ask ] && echo ok || { echo "FAIL: expected permissionDecision=ask, got '$decision'"; fails=$((fails+1)); }
}
denycheck() { # denycheck <command> <label>
  printf '%-58s ' "$2"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$PFX$1" | bash "$H")
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
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_name':'PowerShell','tool_input':{'command':sys.argv[1]}}))" "$PFX$1" | bash "$H")
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
t "srun mv $P/rawdata/a.fastq.gz /tmp/"            ask  "#29d mv behind srun now asks (E9 supersedes the old warn)"
t "$(printf 'srun %s -rf %s/results "x\ny"' "$D" "$P")" deny "#29d a multi-line quoted argument after the target"

# E9 (2026-09-30, maintainer decision): mv was the one delete-adjacent verb
# with no directory-protection rule at all - only the sequencing-file-
# extension heuristic could ever fire on it, which said nothing about
# rawdata/, results/ or analysis/ as such. Every SOURCE (every argument but
# the last) is now judged against those three, the same set rm/find/rsync
# already deny on; the LAST argument is the destination being written into,
# which stays excluded - writing into one of these directories is normal.
t "mv results /tmp/x"                              ask  "#29e mv results/ (bare relative path) elsewhere asks"
t 'mv $P/rawdata/ /scratch/old'                     ask  "#29e mv an unexpanded \$VAR/rawdata/ still asks (literal match)"
t "mv notes.txt results/"                           pass "#29e mv INTO results/ is writing, stays quiet"
t "mv a.txt b.txt"                                  pass "#29e an ordinary mv with nothing protected, stays quiet"
t "ls results && mv x y"                            pass "#29e mv in a compound, nothing protected, stays quiet"
tps "Move-Item results C:\\tmp"                     ask  "#29e PowerShell Move-Item on results/ asks"
# E9, acceptance review: shapes that still moved a protected directory quietly,
# and one read-only command that asked.
t "mv -t /tmp results"                              ask  "#29e mv -t: every argument is a source"
t "mv --target-directory=/tmp analysis"             ask  "#29e mv --target-directory="
t "mv results{,.bak}"                               ask  "#29e brace rename of results/"
t "mv {rawdata,old_rawdata}"                        ask  "#29e brace list with rawdata as the source"
t "rsync -a --remove-source-files results/ /x/"     ask  "#29e rsync --remove-source-files empties the source"
t "rename s/results/old/ results"                   ask  "#29e rename(1) on results/"
t "grep -rn mv results analysis"                    pass "#29e grep for the word mv is not a move"
tps "Move-Item -Destination C:\\tmp -Path results"  ask  "#29e Move-Item with named parameters reversed"
tps "mi results C:\\tmp"                            ask  "#29e PowerShell alias mi"
tps "Rename-Item results old_results"               ask  "#29e Rename-Item on results/"
tps "Get-ChildItem results | Move-Item -Destination C:\\tmp" ask "#29e Move-Item fed by the pipeline"
tps "Move-Item notes.txt -Destination results"      pass "#29e Move-Item INTO results/ stays quiet"

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


echo
echo "== #35: medium/low shapes left after #29 (each with a control) =="
tc() { # tc <cwd> <command> <expect pass|warn|deny|ask> <label> - the hook input also carries the session's cwd
  printf '%-58s ' "$4"
  out=$(python3 -c "import json,sys;print(json.dumps({'cwd':sys.argv[1],'tool_input':{'command':sys.argv[2]}}))" "$1" "$PFX$2" | bash "$H")
  if [ -z "$out" ]; then got=pass; else
    got=$(PYTHONIOENCODING=utf-8 python3 -c "import json,sys;o=json.load(sys.stdin)['hookSpecificOutput'];print(o.get('permissionDecision','warn'))" <<<"$out")
  fi
  if [ "$got" = "$3" ]; then echo "ok ($got)"; else
    echo "FAIL: expected $3, got $got"; fails=$((fails+1))
  fi
}
EXD=$(mktemp -d)   # #112: a folder that exists, for the "absolute cd to a real folder" controls
RD=$(printf '\x72\x64')           # cmd's remove-directory verb, assembled like $D
DL=$(printf '\x64\x65\x6c')       # cmd's delete verb
# A shell run by flock -c / su -c / tmux / screen outside a nested shell
t "flock /tmp/l -c '$D -rf $P/analysis'"           deny "#35 flock -c delete of analysis/"
t "flock /tmp/l -c '$D -rf $P/work'"               ask  "#35 flock -c delete of work/ asks"
t "su - lab -c '$D -rf $P/results'"                deny "#35 su - lab -c delete of results/"
t "su lab -c \"$D -rf $P/results\""                deny "#35 su -c, double-quoted"
t "tmux new -d '$D -rf $P/results'"                deny "#35 tmux new -d delete"
t "tmux new-session -d -s a \"$D -rf $P/rawdata\"" deny "#35 tmux new-session delete"
t "tmux send-keys -t a '$D -rf $P/results' Enter"  deny "#35 tmux send-keys delete"
t "screen -X stuff '$D -rf $P/results'"            deny "#35 screen -X stuff delete"
t "screen -dmS a $D -rf $P/results"                deny "#35 control: screen with the verb as an argument (already denied)"
t "flock /tmp/l -c 'ls $P/results'"                pass "#35 control: flock -c ls"
t "su lab -c 'echo hi'"                            pass "#35 control: su -c echo"
t "tmux new -d 'htop'"                             pass "#35 control: tmux new htop"
t "tmux ls"                                        pass "#35 control: tmux ls"
# cmd /c <verb> under the Bash tool
t "cmd /c $RD /s /q $P/results"                    deny "#35 cmd /c rd /s /q results"
t "cmd.exe /c $DL /q $P/results/x.txt"             deny "#35 cmd.exe /c del under results/"
t "cmd /c \"$RD /s /q $P/analysis\""               deny "#35 cmd /c with the whole command quoted"
t "cmd /c $RD /s /q $P/work"                       ask  "#35 cmd /c rd of work/ asks"
t "cmd.exe /c rmdir /s /q $P/rawdata"              deny "#35 control: cmd.exe /c rmdir (already denied)"
t "cmd /c dir $P/results"                          pass "#35 control: cmd /c dir"
t "cmd /c echo $RD $P/results"                     pass "#35 control: cmd /c echo rd"
# rsync --remove-source-files empties its sources (already asks since #29e/#33)
t "rsync -a --remove-source-files $P/rawdata/ /backup/" ask "#35 control: rsync --remove-source-files from rawdata/ (already asks)"
t "rsync -a --remove-source-files /tmp/x/ /backup/"     pass "#35 control: ...from an unprotected folder"
# a pipe into an executor that has a wrapper with arguments, or python
t "echo '$D -rf $P/results' | sudo -u lab bash"    deny "#35 piped into sudo -u x bash"
t "echo '$D -rf $P/results' | srun bash"           deny "#35 piped into srun bash"
t "echo '$D -rf $P/results' | srun --pty bash"     deny "#35 piped into srun --pty bash"
t "echo '$D -rf $P/results' | ssh h bash"          deny "#35 piped into ssh h bash"
t "echo '$D -rf $P/results' | sudo -E bash -s"     deny "#35 piped into sudo -E bash -s"
t "echo '$D -rf $P/results' | grep bash"           pass "#35 control: piped into grep bash"
t "echo '$D -rf $P/results' | sudo -u lab tee out.txt" pass "#35 control: piped into sudo tee"
t "$(printf 'cat <<%s | sudo -u lab bash\n%s -rf %s/results\nEOF\n' "'EOF'" "$D" "$P")" deny "#35 here-doc piped into sudo -u x bash"
t "$(printf 'cat <<%s | srun bash\n%s -rf %s/results\nEOF\n' "'EOF'" "$D" "$P")"      deny "#35 here-doc piped into srun bash"
t "$(printf 'cat <<%s | python3\nimport shutil\nshutil.rmtree("%s/results")\nEOF\n' "'EOF'" "$P")" ask "#35 here-doc piped into python3"
t "echo 'import shutil; shutil.rmtree(\"$P/results\")' | python3" ask "#35 python code piped into python3"
t "$(printf 'cat > notes.md <<%s\n%s -rf %s/results\nEOF\n' "'EOF'" "$D" "$P")" pass "#35 control: here-doc written to a file"
# R
t "R -e 'unlink(\"$P/results\", recursive=TRUE)'"  ask  "#35 R -e unlink"
t "R --no-save -e 'unlink(\"$P/results\", recursive=TRUE)'" ask "#35 R --no-save -e unlink"
t "R -e 'print(1)'"                                pass "#35 control: R -e print"
t "R --version"                                    pass "#35 control: R --version"
# relative targets, resolved with the hook input's cwd and any cd before them
tc "$P/results" "$D -rf fastqc"                    deny "#35 cwd results/: rm -rf fastqc"
tc "$P/results" "$D -rf ./fastqc"                  deny "#35 cwd results/: rm -rf ./fastqc"
tc "$P/results/sub" "$D -rf ../fastqc"             deny "#35 cwd results/sub: rm -rf ../fastqc"
tc "$P/analysis" "$D -f fig1.png"                  deny "#35 cwd analysis/: rm a file"
tc "$P/rawdata" "$D -f a.fastq.gz"                 deny "#35 cwd rawdata/: rm a file"
tc "$P" "cd results && $D -rf fastqc"              deny "#35 cd results && rm -rf fastqc"
tc "$P" "cd results; $D -rf fastqc"                deny "#35 cd results; rm -rf fastqc"
tc "$P" "(cd results && $D -rf fastqc)"            deny "#35 (cd results && rm ...) in a subshell"
tc "$P" "cd $P/results && $D -rf fastqc"           deny "#35 cd <absolute>/results && rm ..."
tc "$P" "cd \"results\" && $D -rf fastqc"          deny "#35 cd \"results\" quoted"
tc "$P" "cd results && cd sub && $D -rf x"         deny "#35 two cds down into results/sub"
tc "$P/work" "$D -rf fastqc"                       ask  "#35 cwd work/: rm -rf fastqc asks"
tc "$P" "cd work && $D -rf fastqc"                 ask  "#35 cd work && rm -rf fastqc asks"
tc "$P" "$D -rf tmp_x"                             pass "#35 control: rm in an ordinary cwd"
tc "$P/results" "ls"                               pass "#35 control: cwd results/, ls"
tc "$P" "cd results && ls"                         pass "#35 control: cd results && ls"
tc "$P/results" "cd .. && $D -rf tmp_x"            pass "#35 control: cd .. leaves results/"
tc "$P" "cd tmp && $D -rf x"                       pass "#35 control: cd into an unprotected folder"
tc "$P/results" "$D -rf $P/tmp"                    pass "#35 control: an absolute target outside results/"
tc "$P" "cd \$HOME && $D -rf x"                    ask  "#35 cd to a variable: lost cwd now asks (#104)"
# low shapes
t "perl -MFile::Path=remove_tree -e 'remove_tree(\"$P/results\")'" ask "#35 perl remove_tree"
t "perl -MFile::Path=make_path -e 'make_path(\"$P/x\")'" pass "#35 control: perl make_path"
t "git clean -fdx"                                 ask  "#35 git clean -fdx"
t "git clean -fd $P/results"                       deny "#35 git clean -fd of results/"
tc "$P/results" "git clean -fdx"                   deny "#35 git clean -fdx inside results/"
t "git clean -n"                                   pass "#35 control: git clean -n (dry run)"
t "git clean --dry-run -fd"                        pass "#35 control: git clean --dry-run"
t "git status"                                     pass "#35 control: git status"
t "a=($D -rf $P/results); \"\${a[@]}\""            deny "#35 command held in an array"
t "files=(a.txt b.txt); ls \"\${files[@]}\""       pass "#35 control: an array of file names"
t "$D -rf $P/re\\sults"                            deny "#35 backslash inside the name (re\\sults)"
t "$D -rf $P/r\\esults/x"                          deny "#35 backslash, nested (r\\esults/x)"
t "$D -rf $P/re\\ports"                            pass "#35 control: a backslash in an unprotected name"
# false alarms the review listed
t "rsync -av --dry-run --delete $P/results/ bk/"   pass "#35 rsync --dry-run --delete is not a delete"
t "rsync -avn --delete $P/results/ bk/"            pass "#35 rsync -avn --delete is not a delete"
t "rsync -av --dry-run --remove-source-files $P/results/ bk/" pass "#35 rsync --dry-run --remove-source-files"
t "rsync -av --delete /tmp/empty/ $P/results/"     deny "#35 control: the real rsync --delete into results/"
t "xargs -I{} $D -rf {} < dirs.txt"                ask  "#35 xargs -I{} rm: ask, not deny"
t "cat dirs.txt | xargs -I{} $D -rf {}"            ask  "#35 piped xargs -I{} rm: ask, not deny"
t "find $P/results -name '*.tmp' -exec $D -f {} \\;" deny "#35 control: find -exec rm {} under results/"
t "find /tmp/x -name '*.tmp' -exec $D -f {} \\;"   ask  "#35 find -exec rm {} elsewhere: ask, not a bogus root deny"
t "mv -t $P/results a b"                           pass "#35 mv -t results/ a b writes INTO results/"
t "mv --target-directory=$P/results a b"           pass "#35 control: mv --target-directory=results/ a b (already quiet)"
t "mv -t results a b"                              pass "#35 mv -t results a b (relative)"
t "mv -t /tmp $P/results"                          ask  "#35 control: mv -t /tmp results asks (results is a source)"
t "mv -t /tmp results a"                           ask  "#35 control: ...relative"
t "mv x.txt $P/results/{a,b}.txt"                  ask  "#35 control: a brace in the last argument expands to two sources, asks"
tps "Get-ChildItem C:\\lab\\proj\\x | Move-Item -Destination C:\\lab\\proj\\y" pass "#35 pipeline-fed Move-Item, nothing protected"
tps "Get-ChildItem C:\\lab\\proj\\x | Where-Object { \$_.Length -gt 0 } | Move-Item -Destination C:\\lab\\proj\\y" pass "#35 ...with a filter in the pipeline"
tps "gci x | Move-Item -Destination y"            pass "#35 ...relative lister path"
tps "ls | Move-Item -Destination elsewhere"        ask  "#35 control: a lister with no path (may be the cwd): asks"
tps "Get-ChildItem C:\\lab\\proj\\results | Move-Item -Destination C:\\tmp" ask "#35 control: lister names results/: asks"
tps "Get-ChildItem \$dir | Move-Item -Destination C:\\tmp" ask "#35 control: lister path is a variable: asks"
tps "Get-ChildItem C:\\lab\\x | ForEach-Object { \$_.FullName } | Move-Item -Destination C:\\tmp" ask "#35 control: ForEach-Object can rewrite the path: asks"
tps "Move-Item"                                    ask  "#35 control: Move-Item with no source at all asks"

# After independent acceptance (#35): -n belongs to the WRAPPER, not to rsync/git.
# `nice -n 10 rsync --delete` is a real delete; only an n among rsync's (or
# git clean's) own options is a dry run.
t "nice -n 10 rsync -a --delete /tmp/empty/ $P/results/"        deny "#35b nice -n 10 rsync --delete is not a dry run"
t "srun -n 1 rsync -a --delete /tmp/empty/ $P/results/"         deny "#35b srun -n 1 rsync --delete"
t "ssh -n t3 rsync -a --delete /tmp/empty/ $P/results/"         deny "#35b ssh -n host rsync --delete (unquoted)"
t "sudo -n rsync -a --delete /tmp/empty/ $P/results/"           deny "#35b sudo -n rsync --delete"
t "timeout -n 5 rsync -a --delete /tmp/empty/ $P/results/"      deny "#35b timeout -n 5 rsync --delete"
t "ionice -n 7 rsync -a --remove-source-files $P/rawdata/ /backup/" ask "#35b ionice -n 7 rsync --remove-source-files"
t "nice -n 19 rsync --remove-source-files $P/rawdata/ /backup/" ask  "#35b nice -n 19 rsync --remove-source-files"
t "nice -n 10 git clean -fdx $P/results"                        deny "#35b nice -n 10 git clean -fdx of results/"
t "nice -n 10 rsync -avn --delete /tmp/empty/ $P/results/"      pass "#35b control: the wrapper -n AND rsync -n: dry run"
t "nice -n 10 rsync -a --delete -n /tmp/empty/ $P/results/"     pass "#35b control: rsync -n after other options"
t "nice -n 10 rsync -a --dry-run --delete /tmp/empty/ $P/results/" pass "#35b control: --dry-run behind a wrapper"
t "nice -n 10 git clean -n -fd $P/results"                      pass "#35b control: git clean -n behind a wrapper"
# data piped into a runner that has its own script / remote command is data
t "echo '$D -rf $P/results' | python3 count_words.py"           pass "#35b data piped into python3 script.py"
t "echo '$D -rf $P/results' | python3 -u count_words.py"        pass "#35b ...with an option before the script"
t "echo '$D -rf $P/results' | ssh t3 'cat >> notes.md'"         pass "#35b data piped into ssh host 'cmd'"
t "echo '$D -rf $P/results' | python3 -"                        deny "#35b control: | python3 - reads code from stdin"
t "echo '$D -rf $P/results' | python3"                          deny "#35b control: | python3 (no script) reads code"
t "echo '$D -rf $P/results' | python3 -u -"                     deny "#35b control: | python3 -u - reads code"
t "echo '$D -rf $P/results' | bash"                             deny "#35b control: | bash"
t "echo '$D -rf $P/results' | ssh t3"                           deny "#35b control: | ssh host (no remote command)"
t "echo '$D -rf $P/results' | ssh -p 22 t3 bash"                deny "#35b control: | ssh host bash"
t "echo '$D -rf $P/results' | ssh t3 'bash -s'"                 deny "#35b control: | ssh host 'bash -s'"
t "echo '$D -rf $P/results' | ssh t3 python3 -"                 deny "#35b control: | ssh host python3 -"
t "echo '$D -rf $P/results' | ssh t3 python3 x.py"              pass "#35b | ssh host python3 x.py is data"

echo
echo "== SN2: work/ deletes that ran without the confirmation (nextflow-clean-unconfirmed) =="
# `nextflow clean -f` deletes the task directories under work/ of a run - the same
# act as rm -rf work/, so the same ask. Without -f (or with -n) Nextflow deletes
# nothing and the guard stays quiet.
NF=$(printf '\x6e\x65\x78\x74\x66\x6c\x6f\x77')
t "$NF clean -f"                                   ask  "nextflow clean -f asks"
t "$NF clean -f -k last"                           ask  "nextflow clean -f -k last"
t "$NF clean -f -q"                                ask  "nextflow clean -f -q"
t "$NF clean -f happy_euler"                       ask  "nextflow clean -f <run name>"
t "$NF clean -f -but happy_euler"                  ask  "nextflow clean -f -but <run>"
t "$NF clean -force -before happy_euler"           ask  "nextflow clean -force -before <run>"
t "$NF -log /tmp/n.log clean -f"                   ask  "nextflow <global option> clean -f"
t "srun $NF clean -f"                              ask  "nextflow clean -f behind srun"
t "cd $P && $NF clean -f"                          ask  "nextflow clean -f after a cd"
t "$NF clean -n"                                   pass "control: nextflow clean -n (dry run)"
t "$NF clean -n -f"                                pass "control: nextflow clean -n -f (dry run wins)"
t "$NF clean -dry-run"                             pass "control: nextflow clean -dry-run"
t "$NF clean"                                      pass "control: nextflow clean (Nextflow refuses)"
t "$NF clean -but happy_euler"                     pass "control: nextflow clean -but <run>, no -f"
t "$NF log"                                        pass "control: nextflow log"
t "$NF run nf-core/rnaseq -profile clean"          pass "control: a profile named clean"
t "make clean -f Makefile"                         pass "control: make clean -f"
# variable-nextflow-clean: the command word held in a variable
t "N=$NF; \$N clean -f"                            ask  "N=nextflow; \$N clean -f asks"
t "N=$NF; \${N} clean -f"                          ask  "N=nextflow; \${N} clean -f asks"
t "N=$NF; \"\$N\" clean -f"                        ask  "N=nextflow; \"\$N\" clean -f asks"
t "N=$NF; \$N clean -n -f"                         pass "control: \$N clean -n -f (dry run)"
t "N=$NF; \$N log"                                 pass "control: \$N log"
t "N=$NF; \$N clean"                               pass "control: \$N clean, no -f"
# A warning used to end the hook before the work/ ask: these were warns.
t "$D -f $P/work/ab/cdef/x.bam"                    ask  "work/ file with a sequencing name still asks"
t "$D -rf $P/work/*.fastq.gz"                      ask  "work/ glob of sequencing files still asks"
t "$D -rf $P/work && echo x > $P/results/notes.txt" ask "work/ delete beside an overwrite still asks"
printf '%-58s ' "...and the ask keeps the warning's text"
out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$PFX$D -f $P/work/ab/cdef/x.bam" | bash "$H")
if grep -q 'sequencing data' <<<"$out" && grep -q 'Nextflow scratch' <<<"$out"; then echo ok; else
  echo "FAIL: <<${out:0:120}>>"; fails=$((fails+1)); fi

echo
echo "== SN1: delete shapes the guard did not see (sn1-delete-shapes) =="
# Each shape that removes a protected folder (or empties a file in one) must be
# refused, or asked about where the target cannot be seen; each control must not
# change. The verbs are assembled like $D where a gate watching the shell could
# read them.
TAR=$(printf '\x74\x61\x72'); ZIP=$(printf '\x7a\x69\x70'); RCL=$(printf '\x72\x63\x6c\x6f\x6e\x65')
# archive-and-remove
t "$TAR --remove-files -cf /tmp/r.tar $P/results"         deny "tar --remove-files of results/"
t "$TAR -czf /tmp/r.tgz --remove-files -C $P results"     deny "tar --remove-files -C <run> results"
t "$TAR cf /tmp/r.tar $P/rawdata --remove-files"          deny "old-style tar cf ... --remove-files"
t "$TAR --remove-files -cf /tmp/w.tar $P/work"            ask  "tar --remove-files of work/ asks"
t "$TAR --remove-files -cf /tmp/x.tar -T list.txt"        ask  "tar --remove-files -T list: sources unknown"
t "$TAR -cf /tmp/r.tar $P/results"                        pass "control: tar without --remove-files"
t "$TAR --remove-files -cf $P/results/old.tar /tmp/scratch" pass "control: the archive written INTO results/"
t "$ZIP -rm /tmp/r.zip $P/results"                        deny "zip -rm of results/"
t "$ZIP -r -m /tmp/r.zip $P/analysis"                     deny "zip -r -m of analysis/"
t "$ZIP --move /tmp/r.zip $P/rawdata/a.fastq.gz"          deny "zip --move of a rawdata/ file"
t "$ZIP -r /tmp/r.zip $P/results"                         pass "control: zip without -m"
t "$ZIP -rm $P/results/figs.zip /tmp/figs"                pass "control: the zip file written INTO results/"
# rclone
t "$RCL purge $P/results"                                 deny "rclone purge results/"
t "$RCL delete remote:proj/results"                       deny "rclone delete remote:.../results"
t "$RCL deletefile $P/rawdata/a.fastq.gz"                 deny "rclone deletefile in rawdata/"
t "$RCL rmdirs $P/analysis"                               deny "rclone rmdirs analysis/"
t "$RCL sync /tmp/empty $P/results"                       deny "rclone sync INTO results/ (deletes what is not in the source)"
t "$RCL move $P/results remote:backup"                    ask  "rclone move results/ out asks (as mv, E9)"
t "$RCL delete $P/work"                                   ask  "rclone delete work/ asks"
t "$RCL copy $P/results remote:backup"                    pass "control: rclone copy"
t "$RCL sync $P/results remote:backup"                    pass "control: rclone sync FROM results/"
t "$RCL purge remote:scratch"                             pass "control: rclone purge elsewhere"
t "$RCL delete --dry-run $P/results"                      pass "control: rclone delete --dry-run"
t "$RCL ls $P/results"                                    pass "control: rclone ls"
tc "$P/work" "$RCL purge remote:scratch"                  pass "control: a remote path is not under the working folder"
tc "$P/work" "$RCL sync $P/results remote:backup"         pass "control: ...nor is a remote destination"
# deletes written as node / ruby / pathlib code: ask, as python already does
t "node -e \"require('fs').rmSync('$P/results',{recursive:true})\"" ask "node require('fs').rmSync(...)"
t "node -e \"fs.promises.rm('$P/results',{recursive:true})\""       ask "node fs.promises.rm(...)"
t "ruby -e 'require \"fileutils\"; FileUtils.rm_rf(\"$P/results\")'" ask "ruby FileUtils.rm_rf(...)"
t "ruby -e 'FileUtils.rm_r \"$P/results\"'"                          ask "ruby FileUtils.rm_r without parentheses"
t "python3 -c \"import pathlib; pathlib.Path('$P/results/x').unlink()\"" ask "python pathlib .unlink()"
t "node -e \"console.log(1)\""                                       pass "control: node -e console.log"
t "ruby -e 'puts FileUtils.pwd'"                                     pass "control: ruby FileUtils.pwd"
t "$(printf 'python3 - <<%s\nlst = [1, 2]\nlst.remove(1)\nEOF\n' "'EOF'")" pass "control: python list.remove(...)"
# a brace word, as bash expands it
t "$D -rf $P/res{ults,}"                                  deny "brace res{ults,}"
t "$D -rf $P/{tmp,ana{lysis,x}}"                          deny "nested brace naming analysis"
t "$D -rf $P/re{s..s}ults"                                deny "brace sequence re{s..s}ults"
t "$D -rf $P/tmp{1,2}"                                    pass "control: brace naming nothing protected"
t "$D -rf /tmp/{a,b}"                                     pass "control: brace under /tmp"
# case: the same folder on a file system that ignores case
case "${OSTYPE:-}" in msys*|cygwin*|darwin*) CASE_EXP=deny ;; *) CASE_EXP=ask ;; esac
t "$D -rf $P/RESULTS"                                     "$CASE_EXP" "RESULTS: deny where case is ignored, else ask"
t "$D -rf $P/Analysis/x"                                  "$CASE_EXP" "Analysis/x: the same"
t "$D -rf C:/lab/proj/Results"                            deny "a Windows path: case ignored, deny"
t "$D -rf /mnt/c/lab/proj/RawData"                        deny "a WSL path to a Windows drive: deny"
tps 'Remove-Item -Recurse C:\lab\proj\RESULTS'            deny "PowerShell Remove-Item RESULTS"
t "$D -rf $P/Resultsheet.txt"                             pass "control: a name that only starts alike"
t "$D -f C:/Users/me/Documents/Work/old.txt"              pass "control: a Windows folder named Work is not work/"
# links and modes
t "ln -sfn /tmp/x $P/results"                             deny "ln -sfn over results/"
t "ln --force --no-dereference -s /tmp/x $P/rawdata"      deny "ln --force --no-dereference over rawdata"
t "ln -sf /data/orig/s1.fastq.gz $P/rawdata"              pass "control: ln -sf without -n links INTO rawdata/"
t "ln -sfT /tmp/x $P/analysis/"                           deny "ln -sfT over analysis/"
t "ln -sfn /tmp/x $P/work"                                ask  "ln -sfn over work/ asks"
t "ln -sf /data/orig/s1.fastq.gz $P/rawdata/s1.fastq.gz"  pass "control: staging a link inside rawdata/"
t "ln -s /tmp/x $P/results"                               pass "control: ln without -f (fails if it exists)"
t "ln -sf $P/results /tmp/link"                           pass "control: results/ as the link's target"
t "install -d -m 000 $P/results"                          ask  "install -d -m 000 results/ asks"
t "install -d -o nobody $P/_references"                   ask  "install -d -o on _references/ asks"
t "install -d $P/results"                                 pass "control: install -d without a mode (mkdir -p)"
t "install -d -m 755 $P/results/fastqc_extra"             pass "control: install -d -m of a new folder inside"
t "install -m 644 x.R $P/analysis/x.R"                    pass "control: install a file into analysis/"
# a truncation by redirect is truncate -s 0
t ": > $P/rawdata/s1.fastq.gz"                            deny ": > rawdata/<file>"
t "> $P/results/multiqc_report.html"                      deny "> results/<file>"
t "true > $P/analysis/de.tsv"                             deny "true > analysis/<file>"
t "cat /dev/null > $P/results/x.tsv"                      deny "cat /dev/null > results/<file>"
t ": > $P/work/x"                                         ask  ": > work/<file> asks"
tc "$P/rawdata" ": > s1.fastq.gz"                         deny ": > <file> with cwd rawdata/"
t ": > /tmp/x.log"                                        pass "control: : > /tmp/x.log"
t "echo x > $P/results/notes.txt"                         warn "control: writing into results/ is unchanged (warn)"
t ": >> $P/results/x.log"                                 warn "control: an append is not a truncation (warn)"
# a recursive delete from above the protected folders
t "find $P -name '*.fastq.gz' -delete"                    deny "find <run> -name '*.fastq.gz' -delete"
t "find $P -iname '*.BAM' -exec $D {} +"                  deny "find <run> -iname '*.BAM' -exec rm"
tc "$P" "find . -name '*.fq.gz' -delete"                  deny "find . -name '*.fq.gz' -delete in <run>"
t "find $P -delete"                                       deny "find <run> -delete"
t "$D -rf $P"                                             deny "rm -rf <run>"
t "$D -rf /data/me/projects/p1/"                          deny "rm -rf <projects>/<p>"
t "find $P -name '*.log' -delete"                         ask  "find <run> -name '*.log' -delete asks"
t "find /data/proj -name '*.fastq.gz' -delete"            ask  "find <unknown> -name '*.fastq.gz' -delete asks"
t "find $P/work -name '*.bam' -delete"                    ask  "control: find work/ -name '*.bam' asks (SN2)"
t "find /tmp/x -name '*.fastq.gz' -delete"                warn "control: find /tmp/x -name '*.fastq.gz' unchanged (warn)"
t "$D -f $P/tmp.txt"                                      pass "control: rm a file beside the protected folders"
t "$D -rf $P/tmp"                                         pass "control: rm -rf a folder beside them"
t "find $P -maxdepth 1 -name tmp_x"                       pass "control: find without -delete"
# backslash-delete-shapes: a leading backslash only skips an alias; the same
# command runs and gets the same verdict.
t "\\$NF clean -f"                                        ask  "\\nextflow clean -f asks"
t "\\$TAR --remove-files -cf /tmp/r.tar $P/results"       deny "\\tar --remove-files of results/"
t "\\$ZIP -m /tmp/r.zip $P/rawdata"                       deny "\\zip -m of rawdata/"
t "\\$RCL purge $P/results"                               deny "\\rclone purge results/"
t "\\ln -sfn /tmp/x $P/rawdata"                           deny "\\ln -sfn over rawdata/"
t "\\find $P -delete"                                     deny "\\find <run> -delete"
t "\\rsync -a --delete /tmp/empty/ $P/results/"           deny "\\rsync --delete into results/"
t "\\install -d -m 000 $P/results"                        ask  "\\install -d -m 000 results/ asks"
t "\\$TAR -cf /tmp/r.tar $P/results"                      pass "control: \\tar without --remove-files"
t "\\$RCL copy $P/results remote:backup"                  pass "control: \\rclone copy"
# gates-audit2-low: behind a wrapper the command word is srun; behind a large
# here-doc only the filter's trigger regex keeps this segment.
t "srun $TAR --remove-files -cf /tmp/r.tar $P/results"    deny "srun tar --remove-files of results/"

# backslash-inside-delete-word (#66): a backslash in the MIDDLE of a command word
# or option is dropped by the shell, so `r\m` runs the delete. Each case gets the
# verdict of the same command without the backslash (TC-ids from the bug's test-case.md).
RB="${D:0:1}\\${D:1}"; TB="${TAR:0:1}\\${TAR:1}"
t "$RB -rf results"                                       deny "TC-001 r\\m -rf results"
t "$TB --remove-files -cf a.tar results"                  deny "TC-002 t\\ar --remove-files ... results"
t "$TAR --remo\\ve-files -cf a.tar results"               deny "TC-003 tar --remo\\ve-files ... results"
t "nextflow cl\\ean -f"                                   ask  "TC-004 nextflow cl\\ean -f"
t "$RB -rf $P/work"                                       ask  "TC-005 r\\m -rf work asks, as without \\"
t "echo hi; $RB -rf $P/results"                           deny "TC-006 r\\m behind a ;"
t "ssh twnia3 '$RB -rf $P/results'"                       deny "TC-007 r\\m inside ssh"
t "sudo $RB -rf results"                                  deny "TC-008 sudo r\\m"
t "$RB -rf $P/work $P/results"                            deny "TC-009 work and results: the strictest wins"
t "$RB -rf res\\ults"                                     deny "TC-010 two backslashes (r\\m, res\\ults)"
t "$D -rf res\\ults"                                      deny "TC-011 control: a backslash in the argument only"
t "\\$D -rf results"                                      deny "TC-012 control: a leading backslash (#65)"
t "printf 'a\\nb'"                                        pass "TC-013 control: printf 'a\\nb'"
t 'grep -E "a\sb" file'                                   pass "TC-014 control: grep -E regex with \\s"
t "sed 's/a\\/b/c/' f"                                    pass "TC-015 control: sed regex with \\/"
t 'echo C:\Users\x'                                       pass "TC-016 control: a Windows path"
t 'ls C:\work\results'                                    pass "TC-017 control: ls of a Windows results path"
t "echo $RB -rf $P/results"                               deny "TC-018 echo r\\m: as main judges echo without the backslash"
t "$RB -rf $P/re\\ports"                                  pass "TC-019 control: unprotected name, backslashes"
t 'nextflow l\og'                                         pass "TC-020 control: a harmless nextflow subcommand"
t "$RB -rf $P/rawdata"                                    deny "TC-035 r\\m of rawdata/"
t "$RB -rf $P/.nextflow/plugins"                          deny "TC-036 r\\m of .nextflow/plugins/"

# backslash-inside-delete-word (#66), security review round 1: the dropped-backslash
# copy of a segment must never change what a later segment is judged against (the
# folder a `cd` moved to, whether a lister named a known path). Each case gets
# main's verdict (measured on main before the fix).
tc "$P" "cd $P/results\old; $D -rf x"                    deny "#66 cd <results>\old, then a delete in it"
tc "/tmp" "cd $P/results\old; $D -rf x"                  deny "#66 ...from another working folder"
tc "$P" "pushd $P/results\old; $D -rf x"                 deny "#66 pushd <results>\old, then a delete in it"
tc "$P" "cd results\old; $D -rf x"                       deny "#66 cd results\old (relative), then a delete"
tc "$P" "cd .\results; $D -rf *"                         deny "#66 cd .\results, then a delete"
tps 'Get-ChildItem results\old | Move-Item -Destination x'   ask "#66 lister of results\old feeding Move-Item"
tps 'Get-ChildItem .\results | Move-Item -Destination x'     ask "#66 lister of .\results feeding Move-Item"
tps 'Get-ChildItem reports | Move-Item -Destination x'       pass "#66 control: lister of an unprotected folder"

# #66 review round 2: only a real drive path (C:\ or C:/) or UNC path keeps its backslashes
# in the dropped-backslash copy; `C:res\ults` is a relative word and is judged with the
# backslash dropped too. Main's verdict for each is pass (the hook reads `X:` words as
# drive paths); the cases pin that the narrowing makes nothing looser than main.
tc "$P" "$D -rf C:res\ults"                              pass "#66 r2 C:res\ults: no looser than main"
tc "$P" "$D -rf a:res\ults"                              pass "#66 r2 a:res\ults: no looser than main"
tc "$P" "$D -rf C:\res\ults"                            pass "#66 r2 C:\res\ults: a drive path, as main"

# #66 review round 3: `X:/` is not a backslash path - the shell does not turn it into
# anything - so a word that starts with it gets the dropped-backslash copy too. Each
# gets the verdict of the same command without the backslash (main: pass for the mv
# cases, which is looser; the first four were already judged, kept as controls).
tc "$P" "C:/Program/Git/usr/bin/r\\m -rf results"          deny "#66 r3 C:/.../r\\m -rf results"
tc "$P" "$D -rf C:/lab/proj/res\\ults"                     deny "#66 r3 rm -rf C:/lab/proj/res\\ults"
tc "$P" "rsync -a --delete src/ n:/data/proj/res\\ults/"   deny "#66 r3 rsync --delete to n:/data/proj/res\\ults/"
tc "$P" "$D -rf C:/lab/proj/raw\\data"                     deny "#66 r3 rm -rf C:/lab/proj/raw\\data"
tc "$P" "mv s:/p/raw\\data x"                              ask  "#66 r3 mv s:/p/raw\\data x"
tc "$P" "mv s:/p/res\\ults x"                              ask  "#66 r3 mv s:/p/res\\ults x"
tc "$P" "mv C:/lab/proj/raw\\data x"                       ask  "#66 r3 mv C:/lab/proj/raw\\data x"

# cd-target-backslash (#76, #75): the shell drops the backslash of `cd res\ults` and enters
# results/, and PowerShell's Set-Location / sl / chdir / Push-Location change directory too.
# Each case gets the verdict of the same command without the trick (measured on main).
# tcp <tool> <cwd> <command> <expect> <label>: the hook input carries the tool name and the cwd.
tcp() {
  printf '%-58s ' "$5"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_name':sys.argv[1],'cwd':sys.argv[2],'tool_input':{'command':sys.argv[3]}}))" "$1" "$2" "$PFX$3" | bash "$H")
  if [ -z "$out" ]; then got=pass; else
    got=$(PYTHONIOENCODING=utf-8 python3 -c "import json,sys;o=json.load(sys.stdin)['hookSpecificOutput'];print(o.get('permissionDecision','warn'))" <<<"$out" 2>/dev/null)
  fi
  [ "$got" = "$4" ] && echo "ok ($got)" || { echo "FAIL: expected $4, got $got"; fails=$((fails+1)); }
}
# US1: Bash
tc "/tmp" "cd $P; cd res\ults; $D -rf x"                 deny "TC-001 cd res\ults, then a delete"
tc "/tmp" "cd $P; cd raw\data; $D -rf x"                 deny "TC-002 cd raw\data, then a delete"
tc "/tmp" "cd $P; cd wo\rk; $D -rf x"                    ask  "TC-003 cd wo\rk, then a delete (work asks)"
tc "/tmp" "pushd $P/.nextflow/plug\ins; $D -rf x"        deny "TC-004 pushd .nextflow/plug\ins, then a delete"
tc "/tmp" "cd $P/res\ults; $D -rf ."                     deny "TC-005 cd <run>/res\ults, then rm -rf ."
tc "/tmp" "cd $P; c\d results; $D -rf x"                 deny "TC-006 c\d results (backslash in the command word)"
tc "/tmp" "cd $P; pu\shd results; $D -rf x"              deny "TC-007 pu\shd results"
tc "/tmp" "cd $P; cd res\ults; find . -delete"           deny "TC-008 cd res\ults, then find -delete"
tc "/tmp" "cd $P; cd raw\data; mv x y"                   ask  "TC-009 cd raw\data, then mv"
tc "/tmp" "cd $P; cd res\ults; cd ..; $D -rf x"          pass "TC-010 cd res\ults; cd ..: back in the run folder"
tc "/tmp" "cd $P; cd re\ports; $D -rf x"                 pass "TC-011 control: cd re\ports"
tc "/tmp" "cd $P/re\ports; $D -rf x"                     pass "TC-012 control: cd <run>/re\ports"
tc "/tmp" "cd $P; cd res\ults; cd /tmp; $D -rf x"        pass "TC-013 cd res\ults; cd /tmp"
# US2: PowerShell location cmdlets
tps "Set-Location $P/results; Remove-Item -Recurse x"            deny "TC-014 PowerShell Set-Location results"
tps "sl $P/results; Remove-Item -Recurse x"                      deny "TC-015 PowerShell sl results"
tps "Push-Location $P/results; Remove-Item -Recurse x"           deny "TC-016 PowerShell Push-Location results"
tc "/tmp" "Set-Location $P/results; $D -rf x"                    deny "TC-017 Set-Location results, text run by Bash"
tps "Set-Location -Path $P/results; Remove-Item -Recurse x"      deny "TC-018 Set-Location -Path results"
tps "Set-Location -LiteralPath $P/results; Remove-Item -Recurse x" deny "TC-019 Set-Location -LiteralPath results"
tps "Set-Location -Path:$P/results; Remove-Item -Recurse x"      deny "TC-020 Set-Location -Path:results (colon form)"
tps "SET-LOCATION $P/results; Remove-Item -Recurse x"            deny "TC-021 SET-LOCATION (any case)"
tps "cd $P; chdir results; Remove-Item -Recurse x"               deny "TC-022 chdir results"
tps "cd $P; Set-Location results; Remove-Item -Recurse x"        deny "TC-023 cd <run>; Set-Location results"
tps "cd $P; Set-Location res\ults; Remove-Item -Recurse x"       deny "TC-024 Set-Location res\ults"
tps "Set-Location /tmp; Remove-Item x"                           pass "TC-025 control: Set-Location /tmp"
tps "cd $P; Set-Location tmp; Remove-Item -Recurse x"            pass "TC-026 control: Set-Location tmp"
tps "cd $P; Set-Location results; Set-Location ..; Remove-Item -Recurse x" deny "TC-027 Set-Location results; Set-Location .."
# US3: a lister of a backslash folder feeding Move-Item
tcp PowerShell "/tmp" 'Get-ChildItem res\ults | Move-Item -Destination x'     ask  "TC-028 Get-ChildItem res\ults | Move-Item"
tcp PowerShell "/tmp" 'Get-ChildItem raw\data | Move-Item -Destination x'      ask  "TC-029 Get-ChildItem raw\data | Move-Item"
tcp PowerShell "$P" 'Get-ChildItem res\ults | Move-Item -Destination x'        ask  "TC-030 ...from the run folder"
tcp PowerShell "/tmp" 'gci res\ults | Move-Item -Destination /tmp/y'           ask  "TC-031 gci res\ults | Move-Item"
tcp PowerShell "/tmp" "Get-ChildItem $P/res\\ults | Move-Item -Destination /tmp/y" ask "TC-032 absolute path, as before"
tcp PowerShell "/tmp" 'Get-ChildItem re\ports | Move-Item -Destination x'      pass "TC-033 control: re\ports"
# Constitution and safety net
tps "cd $P/results; Push-Location /tmp; Pop-Location; Remove-Item -Recurse x"  deny "TC-034 Push-Location /tmp; Pop-Location: back in results"
tc "/tmp" "cd $P/results; sl /tmp; $D -rf x"                    deny "TC-035 Bash: sl is not a built-in, the folder did not move"
tps "cd $P; cd results; Pop-Location; Remove-Item -Recurse x"  deny "TC-036 Pop-Location with an empty stack changes nothing"
# TC-037 and TC-038: the #66 round 1-3 cases above, unchanged.
# TC-039 and TC-040: tests/confirm_cleanup_behind_heredoc_test.sh runs every case here behind a large here-doc.
# Out of scope: main's behaviour is pinned
tc "/tmp" "cd $P; cd \$d; $D -rf x"                              ask  "TC-041 cd d: lost cwd now asks (#104)"
tc "/tmp" "cd $P; cd \$(printf results); $D -rf x"               ask  "TC-042 cd command-substitution: lost cwd now asks (#104)"
tc "/tmp" "cd $P; alias go=cd; go results; $D -rf x"             pass "TC-043 an alias stays unknown"
# #78: the working folder is lost (cd -, bare cd, popd, quoted backslash): a relative delete asks
tc "/tmp" "cd $P; cd -; $D -rf x"                                ask  "TC-078-01 cd -; relative delete asks"
tc "/tmp" "cd $P/results; cd; $D -rf x"                          ask  "TC-078-02 bare cd asks"
tc "/tmp" "cd $P/results; pushd /tmp; popd; $D -rf x"            ask  "TC-078-03 pushd /tmp; popd asks"
tc "/tmp" "cd $P; popd; $D -rf x"                                ask  "TC-078-04 popd with no pushd asks"
tc "/tmp" "cd $P; cd \"res\ults\"; $D -rf x"                    deny "TC-078-05 cd \"res\ults\" asks: main already denies (candidate results/), stays deny"
tc "/tmp" "cd $P; cd 'res\ults'; $D -rf x"                      deny "TC-078-06 cd 'res\ults' asks: main already denies (candidate results/), stays deny"
tc "/tmp" "cd $P; pushd \"res\ults\"; $D -rf x"                 deny "TC-078-07 pushd \"res\ults\" asks: main already denies (candidate results/), stays deny"
tc "/tmp" "cd $P; pushd; $D -rf x"                               ask  "TC-078-08 bare pushd asks"
tps "cd $P; cd results; cd -; Remove-Item -Recurse x"            ask  "TC-078-09 PowerShell cd - asks"
tps "cd $P; cd results; cd; Remove-Item -Recurse x"              ask  "TC-078-10 PowerShell bare cd asks"
tps "cd $P; Push-Location /tmp; Pop-Location; Remove-Item -Recurse x" ask "TC-078-11 Pop-Location asks"
tc "/tmp" "cd $P; cd -; ls; $D -rf x"                            ask  "TC-078-12 lost state survives an unrelated command"
tc "/tmp" "cd $P; cd -; $D -rf results"                          deny "TC-078-13 lost cwd: relative results stays deny (never loosened to ask)"
tc "/tmp" "cd $P; cd -; find . -name x -delete"                  ask  "TC-078-15 lost cwd: find root asks"
tc "/tmp" "cd $P; cd -; $D -rf {a,b}"                            ask  "TC-078-16 lost cwd: brace list asks"
tc "/tmp" "cd $P; cd -; mv x /tmp/y"                             ask  "TC-078-17 lost cwd: mv source asks"
tc "/tmp" "cd -; $D -rf $P/tmp"                                  pass "TC-078-18 control: absolute target still passes"
tc "/tmp" "cd -; cd $EXD; $D -rf x"                              pass "TC-078-19 control: absolute cd clears the loss (#112: to a folder that exists)"
tc "/tmp" "cd $P; cd -; ls"                                      pass "TC-078-20 control: no delete, no ask"
tc "/tmp" "cd $P; cd -; mv /tmp/a x"                             pass "TC-078-21 control: mv destination only"
tc "/tmp" "cd $P; cd \$d; $D -rf x"                              ask  "TC-078-24 lost cwd now asks (#104)"
tc "/tmp" "cd $P; cd ~; $D -rf x"                                ask  "TC-078-27 lost cwd now asks (#104)"
tc "/tmp" "cd $P; pushd results; pushd /tmp; popd; $D -rf x"     ask  "TC-078-29 no stack model: ask"
tc "/tmp" "cd $P; cd \"tm\p\"; $D -rf x"                        ask  "TC-078-05 mech: cd \"tm\p\" (no protected candidate) asks"
tc "/tmp" "cd $P; cd 'tm\p'; $D -rf x"                          ask  "TC-078-06 mech: cd 'tm\p' asks"
tc "/tmp" "cd $P; pushd \"tm\p\"; $D -rf x"                     ask  "TC-078-07 mech: pushd \"tm\p\" asks"
out78=$(python3 -c "import json,sys;print(json.dumps({'cwd':'/tmp','tool_input':{'command':sys.argv[1]}}))" "$PFX""cd $P; cd -; $D -rf x" | bash "$H")
printf '%-58s ' "TC-078-14 reason says working folder unknown"
if [[ $out78 == *"working folder unknown"* ]] && [[ $out78 == *"popd"* ]]; then echo "ok"; else echo "FAIL: reason text"; fails=$((fails+1)); fi
# #104: the rest of the unknown-working-folder class. Each ask below passed on main.
tc "/tmp" "cd $P/rawdata; cd ~/x; $D -rf s1"                     ask  "TC-104-01 cd ~/x; relative delete asks"
tc "/tmp" "cd \$HOME/rawdata; $D -rf s1"                         ask  "TC-104-02 cd \$HOME/rawdata asks"
tc "/tmp" "cd \$(echo /tmp); $D -rf s1"                          ask  "TC-104-03 cd \$(...) asks"
tc "/tmp" "cd $P; cd \$d; $D -rf x"                              ask  "TC-104-04 cd \$d asks (lost cwd now asks #104)"
tc "/tmp" "cd $P; cd \$(printf results); $D -rf x"               ask  "TC-104-05 cd \$(...) asks (lost cwd now asks #104)"
tc "/tmp" "cd $P; cd ~; $D -rf x"                                ask  "TC-104-06 cd ~ asks (lost cwd now asks #104)"
tc "$P" "cd \$HOME && $D -rf x"                                  ask  "TC-104-07 cd \$HOME && rm asks (lost cwd now asks #104)"
tc "/tmp" "cd $P/rawdata; cd -; $D -rf ~s1"                      ask  "TC-104-09 ~s1 is relative when the folder is lost"
tc "/tmp" "cd $P; cd -; $D -rf ~/x"                              pass "TC-104-10 control: ~/x stays a known path"
tc "/tmp" "cd $P/rawdata; cd -; (cd /tmp); $D -rf s1"            ask  "TC-104-11 cd inside ( ) does not clear"
tc "/tmp" "cd -; cd /tmp & $D -rf s1"                            ask  "TC-104-12 backgrounded cd does not clear"
tc "/tmp" "cd -; true || cd /tmp; $D -rf s1"                     ask  "TC-104-13 cd after || does not clear"
tc "/tmp" "cd -; if true; then cd /tmp; fi; $D -rf s1"           ask  "TC-104-14 cd inside if does not clear"
tc "/tmp" "cd -; cd \$d; $D -rf s1"                              ask  "TC-104-15 variable target does not clear"
tc "/tmp" "cd -; cd /tmp; $D -rf s1"                             pass "TC-104-16 control: plain absolute cd clears"
tc "/tmp" "cd -; cd /tmp && $D -rf s1"                           pass "TC-104-17 control: absolute cd && clears"
# Ruling 2026-10-17 (supersedes TC-104-18 brace half): a cd inside { } never clears; main asked here.
tc "/tmp" "cd -; { cd /tmp; }; $D -rf s1"                        ask  "TC-104-18 { cd /abs; } does not clear (ruling: main asked)"
tc "/tmp" "cd -; false && { cd /tmp; }; $D -rf s1"               ask  "TC-104-18b false && { cd /abs; } does not clear"
tc "/tmp" "cd -; cd $EXD; $D -rf x"                              pass "TC-104-19 control: absolute cd clears (as TC-078-19; #112: to a folder that exists)"
tc "/tmp" "cd ~; $D -rf /tmp/s1"                                 pass "TC-104-20a control: absolute target after cd ~"
tc "/tmp" "cd -; $D -rf $P/tmp"                                  pass "TC-104-20b control: absolute target after cd -"
tc "/tmp" "cd $P; cd -; $D -rf results"                          deny "TC-104-21 results stays deny"
tc "/tmp" "cd $P/rawdata; cd -; : > s1"                          ask  "TC-104-22 lost cwd: : > s1 asks"
tc "/tmp" "cd -; echo hi > s1"                                   ask  "TC-104-23 lost cwd: echo hi > s1 asks"
out104=$(python3 -c "import json,sys;print(json.dumps({'cwd':'/tmp','tool_input':{'command':sys.argv[1]}}))" "$PFX""cd -; : > s1" | bash "$H")
printf '%-58s ' "TC-104-24 reason says working folder unknown"
if [[ $out104 == *"working folder unknown"* ]]; then echo "ok"; else echo "FAIL: reason text"; fails=$((fails+1)); fi
tc "/tmp" "echo hi > s1"                                         pass "TC-104-25 control: known folder, relative > as main"
tc "/tmp" "cd -; echo hi > /tmp/s1"                              pass "TC-104-26 control: absolute > target"
tc "/tmp" "cd $P; cd -; ls"                                      pass "TC-104-27 control: nothing written, no ask"
tps "cd $P; sl -; Remove-Item -Recurse x"                        ask  "TC-104-28 PowerShell sl - asks"
tps "cd $P; sl; Remove-Item -Recurse x"                          ask  "TC-104-29 PowerShell bare sl asks"
tps "cd $P; Set-Location; Remove-Item -Recurse x"                ask  "TC-104-30 PowerShell bare Set-Location asks"
tps "cd $P; Set-Location 'tm\\p'; Remove-Item -Recurse x"        ask  "TC-104-31 PowerShell quoted backslash target asks"
tc "/tmp" "cd $P; sl -; $D -rf x"                                pass "TC-104-32 Bash: sl is not a built-in"
tc "$P" "cd tmp; echo \"a\\b\"; $D -rf x"                        pass "TC-104-33 control: later quoted backslash is not the cd target"
tc "/tmp" "cd $P; cd \"tm\\p\"; $D -rf x"                        ask  "TC-104-34a quoted backslash target asks"
tc "/tmp" "cd $P; cd 'tm\\p'; $D -rf x"                          ask  "TC-104-34b single-quoted backslash target asks"
tc "/tmp" "cd $P; pushd \"tm\\p\"; $D -rf x"                     ask  "TC-104-34c pushd quoted backslash target asks"
tc "/tmp" "cd $P; popd; $D -rf x"                                ask  "TC-104-35 popd asks"
tc "/tmp" "cd $P/results; pushd /tmp; popd; $D -rf x"            ask  "TC-104-36 pushd /tmp; popd asks"
tc "/tmp" "cd $P; cd -; find . -exec mv {} /tmp/y \\;"           ask  "TC-104-37 find -exec mv asks"
tc "/tmp" "cd $P; cd -; find . -name x -delete"                  ask  "TC-104-38 find -delete asks"
tc "/tmp" "cd $P; alias go=cd; go results; $D -rf x"             pass "TC-104-41 alias stays pass (no alias model)"
tc "/tmp" "cd $P; cd -; tar --remove-files -czf a.tgz s1"        pass "TC-104-42a known gap: tar --remove-files"
tc "/tmp" "cd $P; cd -; zip -m a.zip s1"                         pass "TC-104-42b known gap: zip -m"
tc "/tmp" "cd $P; cd -; rclone move s1 remote:x"                 pass "TC-104-42c known gap: rclone move"
tc "/tmp" "cd $P; pushd results; popd; $D -rf x"                 deny "TC-104-44a pushd results; popd stays deny"
tc "/tmp" "cd $P; pushd results; pushd /tmp; popd; $D -rf x"     ask  "TC-104-44b no stack model: ask"
# #110: the remaining ways a lost folder was cleared or bypassed (Part 1, tighten) and the
# asks #109 added for commands that neither delete nor overwrite (Part 2, loosen back).
NL=$'\n'
tc "/tmp" "cd $P; cd -; false && cd /tmp; $D -rf s1"                 ask  "TC-110-01 false && cd does not clear"
tc "/tmp" "cd -; [ -d x ] && cd /tmp; $D -rf s1"                     ask  "TC-110-02 test && cd does not clear"
tc "/tmp" "cd -${NL}if true${NL}then${NL}cd /tmp${NL}fi${NL}$D -rf s1" ask "TC-110-03 multi-line if does not clear"
tc "/tmp" "cd -${NL}for i in; do${NL}cd /tmp${NL}done${NL}$D -rf s1" ask "TC-110-04 multi-line for does not clear"
tc "/tmp" "cd -${NL}while true; do${NL}cd /tmp${NL}done${NL}$D -rf s1" ask "TC-110-05 multi-line while"
tc "/tmp" "cd -${NL}until false; do${NL}cd /tmp${NL}done${NL}$D -rf s1" ask "TC-110-06 multi-line until"
tc "/tmp" "cd -${NL}case x in x)${NL}cd /tmp${NL};;${NL}esac${NL}$D -rf s1" ask "TC-110-07 multi-line case"
tc "/tmp" "cd -${NL}select i in a; do${NL}cd /tmp${NL}done${NL}$D -rf s1" ask "TC-110-08 multi-line select"
tc "/tmp" "cd -${NL}(${NL}cd /tmp${NL})${NL}$D -rf s1"               ask  "TC-110-09 multi-line ( )"
tc "/tmp" "cd -${NL}f() {${NL}cd /tmp${NL}}${NL}$D -rf s1"           ask  "TC-110-10 multi-line function"
tc "/tmp" "cd -${NL}{${NL}cd /tmp${NL}}${NL}$D -rf s1"               ask  "TC-110-11 multi-line { }"
tc "/tmp" "cd -${NL}cat <<EOF${NL}x${NL}EOF${NL}cd /tmp${NL}$D -rf s1" ask "TC-110-12 here-doc before the cd"
tc "/tmp" "cd -; builtin cd /tmp; $D -rf s1"                         ask  "TC-110-13 builtin cd does not clear"
tc "/tmp" "cd -; command cd /tmp; $D -rf s1"                         ask  "TC-110-14 command cd does not clear"
tc "/tmp" "cd -; X=1 cd /tmp; $D -rf s1"                             ask  "TC-110-15 VAR=x cd does not clear"
tc "/tmp" "cd -; cd /tmp; $D -rf s1"                                 pass "TC-110-16 control: plain absolute cd clears"
tc "/tmp" "cd -; cd /tmp && $D -rf s1"                               pass "TC-110-17 control: cd first then && clears"
tc "/tmp" "cd /tmp && $D -rf s1"                                     pass "TC-110-18 control: cd /abs && rm"
tc "/tmp" "cd -${NL}cd /tmp${NL}$D -rf s1"                           pass "TC-110-19 control: plain newlines clear"
tc "/tmp" "cd -${NL}cd /tmp${NL}if true; then echo; fi${NL}$D -rf s1" pass "TC-110-20 control: if after the cd"
tc "/tmp" "cd -; { cd /tmp; }; $D -rf s1"                            ask  "TC-110-21 { cd; } still asks"
tc "/tmp" "cd -; ls >| s1"                                           ask  "TC-110-22 >| overwrite"
tc "/tmp" "cd -; ls >&s1"                                            ask  "TC-110-23 >&file"
tc "/tmp" "cd -; ls >& s1"                                           ask  "TC-110-24 >& file"
tc "/tmp" "cd -; echo x > \"\$F\""                                   ask  "TC-110-25 > \"\$F\""
tc "/tmp" "cd -; echo x > \$(mktemp)"                                ask  "TC-110-26 > \$(...)"
tc "/tmp" 'cd -; echo x > `mktemp`'                                  ask  "TC-110-27 > backticks"
tc "/tmp" "cd -; ls 2>&1"                                            pass "TC-110-28 control: 2>&1"
tc "/tmp" "cd -; ls >&2"                                             pass "TC-110-29 control: >&2"
tc "/tmp" "ls > s1"                                                  pass "TC-110-30 control: known folder"
tc "/tmp" "cd /tmp; echo x > \"\$F\""                                pass "TC-110-31 control: known folder, \$ target"
tc "/tmp" "cd -; echo x | tee s1"                                    ask  "TC-110-32 tee FILE"
tc "/tmp" "cd -; sort -o s1 s1"                                      ask  "TC-110-33 sort -o"
tc "/tmp" "cd -; cp /tmp/a s1"                                       ask  "TC-110-34 cp dest"
tc "/tmp" "cd -; sed -i s/a/b/ s1"                                   ask  "TC-110-35 sed -i"
tc "/tmp" "cd -; dd if=/dev/zero of=s1 count=1"                      ask  "TC-110-36 dd of="
tc "/tmp" "cd -; echo x | tee -a s1"                                 pass "TC-110-37 control: tee -a as today"
tc "/tmp" "cd /tmp; echo x | tee s1"                                 pass "TC-110-38 control: known folder tee"
tc "/tmp" "cd -; cp s1 /tmp/b"                                       pass "TC-110-39 control: cp relative source only"
tc "/tmp" "cd -; echo x | tee /tmp/s1"                               pass "TC-110-40 control: tee absolute"
tc "/tmp" "cd -; sort s1"                                            pass "TC-110-41 control: sort without -o"
tc "/tmp" "cd -; sed s/a/b/ s1"                                      pass "TC-110-42 control: sed without -i"
tc "/tmp" "cd -; dd if=s1 of=/tmp/o"                                 pass "TC-110-43 control: dd of= absolute"
tc "/tmp" "cd -; echo \"x>y\""                                       ask  "TC-110-44 quoted > is text - Part 2 dropped 2026-10-17 (review on #111): ask as main"
tc "/tmp" "cd -; awk '\$1>3' /tmp/f"                                 ask  "TC-110-45 awk comparison (ruling 2026-10-17: awk can write, asks; accepted cost)"
tc "/tmp" "cd -; [[ a > b ]]"                                        ask  "TC-110-46 [[ a > b ]] - Part 2 dropped 2026-10-17 (review on #111): ask as main"
tc "/tmp" "cd -; [ a \> b ]"                                        ask  "TC-110-47 [ a \> b ] - Part 2 dropped 2026-10-17 (review on #111): ask as main"
tc "/tmp" "cd -; git log --format='a->b'"                            ask  "TC-110-48 git is not text-only (ruling 2026-10-17 round 3: expectation superseded to ask)"
tc "/tmp" "cd -; cd /tmp # a | b${NL}$D -rf s1"                      ask  "TC-110-49 comment after cd - Part 2 dropped 2026-10-17 (review on #111): ask as main"
tc "/tmp" "cd /tmp # a | b${NL}$D -rf s1"                            pass "TC-110-50 control: comment, known folder"
tc "/tmp" "cd -; cd /tmp; echo \"a&b\"; $D -rf s1"                   ask  "TC-110-51 quoted & is text - Part 2 dropped 2026-10-17 (review on #111): ask as main"
tc "/tmp" "cd -; echo \"x>y\"; $D -rf s1"                            ask  "TC-110-52 quoted > then relative delete"
tc "/tmp" "cd -; echo \"a>b\" > s1"                                  ask  "TC-110-53 real redirect after quoted >"
tc "/tmp" "cd -; echo x > \"s1\""                                    ask  "TC-110-54 quoted target"
tc "/tmp" "cd -; echo x > 's1'"                                      ask  "TC-110-55 single-quoted target"
tc "/tmp" "cd -; [[ a > b ]]; echo x > s1"                           ask  "TC-110-56 comparison then real redirect"
tc "/tmp" "cd -; awk '\$1>3' /tmp/f > s1"                            ask  "TC-110-57 awk then real redirect"
tc "/tmp" "cd -; cd /tmp & $D -rf s1"                                ask  "TC-110-58 backgrounded cd"
tc "/tmp" "cd -; true || cd /tmp; $D -rf s1"                         ask  "TC-110-59 || cd"
tc "/tmp" "cd $P; cd \"\$dir\"; $D -rf s1"                           ask  "TC-110-60 cd \"\$dir\" still lost"
tc "/tmp" "d=s1; $D -rf \$d"                                         ask  "TC-110-62 variable relative delete as today"
tc "/tmp" "cd -; cd /no/such/dir; $D -rf s1"                         ask  "TC-110-66 (#112 flips pass to ask) cd to a missing folder keeps the loss"
tc "/tmp" "cd -; cd /tmp # a | b${NL}$D -rf results"                 deny "TC-110-70 comment cd then results"
tc "/tmp" "$D -rf $P/results"                                        deny "TC-110-71 results stays deny"
# Fix round 3 (acceptance round 2): git and rg are not text-only; continuation lines; &>
tc "/tmp" "cd -; git -c alias.x='!echo y > s1' x"                     ask  "TC-110-73 git alias writes"
tc "/tmp" "cd -; git rebase -x 'echo hi > s1' HEAD~1"                ask  "TC-110-73 git rebase -x writes"
tc "/tmp" "cd -; git -c core.pager='cat > s1' log"                   ask  "TC-110-73 git core.pager writes"
tc "/tmp" "cd -; rg --pre 'sh -c \"cat > s1\"' x"                    ask  "TC-110-73 rg --pre writes"
tc "/tmp" "cd -${NL}false &&${NL}cd /tmp${NL}$D -rf s1"              ask  "TC-110-73 cd after a line ending in &&"
tc "/tmp" "cd -${NL}false ||${NL}cd /tmp${NL}$D -rf s1"              ask  "TC-110-73 cd after a line ending in ||"
tc "/tmp" "cd -${NL}foo |${NL}cd /tmp${NL}$D -rf s1"                 ask  "TC-110-73 cd after a line ending in |"
tc "/tmp" "cd -; echo x &> s1"                                       ask  "TC-110-73 &> relative target"
tc "/tmp" "cd -; echo x &>> s1"                                      ask  "TC-110-73 &>> relative target"
tc "/tmp" "cd -${NL}cd /tmp${NL}$D -rf s1"                           pass "TC-110-73 control: plain cd line clears"
tc "/tmp" "cd -; echo x &> /tmp/s1"                                  pass "TC-110-73 control: &> absolute target"
tc "/tmp" "cd -; echo x 2>&1"                                        pass "TC-110-73 control: 2>&1"
# Round 3 (review on #111): Part 2 dropped; writer targets with $ / substitutions; attached sed scripts; sort abbreviations; <>
tc "/tmp" "cd -; echo \"echo hi > f\" | bash"                         ask  "TC-110-73 quoted > piped to a shell"
tcp PowerShell "/tmp" 'Pop-Location; echo hi \> out.txt'            ask  "TC-110-73 PowerShell \> is a redirect"
tc "/tmp" "cd -; sed -i -es/a/b/ s1"                                 ask  "TC-110-73 sed -i with -es/a/b/"
tc "/tmp" "cd -; sed -i -nes/a/b/ s1"                                ask  "TC-110-73 sed -i with -nes/a/b/"
tc "/tmp" "cd -; sed -ni -es/a/b/ s1"                                ask  "TC-110-73 sed -ni cluster"
tc "/tmp" "cd -; echo x | tee \$F"                                   ask  "TC-110-73 tee \$F"
tc "/tmp" "cd -; cp a \$F"                                           ask  "TC-110-73 cp a \$F"
tc "/tmp" "cd -; sort -o \"\$F\" x"                                  ask  "TC-110-73 sort -o \"\$F\""
tc "/tmp" "cd -; dd if=a of=\$(x)"                                   ask  "TC-110-73 dd of=\$(x)"
tc "/tmp" "cd -; sort --out=s1 x"                                    ask  "TC-110-73 sort --out="
tc "/tmp" "cd -; sort --o=s1 x"                                      ask  "TC-110-73 sort --o="
tc "/tmp" "cd -; sort --out s1 x"                                    ask  "TC-110-73 sort --out FILE"
tc "/tmp" "cd -; echo x 1<> s1"                                      ask  "TC-110-73 <> read-write redirect"
tc "/tmp" "cd -; sort -o /tmp/s1 x"                                  pass "TC-110-73 control: sort -o absolute"
tc "/tmp" "cd -; echo x | tee /tmp/\$F"                              pass "TC-110-73 control: tee absolute with \$"
# #112: writers that still passed after a lost folder
tc "/tmp" "cd -; echo x > -out"                                      ask  "TC-112-01 > -out is a file name"
tc "/tmp" "cd -; cat a >| -s1"                                       ask  "TC-112-02 >| -s1"
tc "/tmp" "cd -; sort -o -s1 x"                                      ask  "TC-112-03 sort -o -s1"
tc "/tmp" "cd -; echo x > /tmp/-out"                                 pass "TC-112-04 control: absolute -out"
tc "/tmp" "cd -; tee -- -a s1"                                       ask  "TC-112-05 tee -- -a s1"
tc "/tmp" "cd -; tee -- -s1"                                         ask  "TC-112-06 tee -- -s1"
tc "/tmp" "cd -; cp -- a -s1"                                        ask  "TC-112-07 cp -- a -s1"
tc "/tmp" "cd -; tee -- /tmp/s1"                                     pass "TC-112-08 control: tee -- absolute"
tc "/tmp" "cd -; echo x > \"~/s1\""                                  ask  "TC-112-09 quoted ~ redirect"
tc "/tmp" "cd -; echo x > '~/s1'"                                    ask  "TC-112-10 single-quoted ~ redirect"
tc "/tmp" "cd -; cp a \"~/s1\""                                      ask  "TC-112-11 cp a quoted ~"
tc "/tmp" "cd -; echo x > ~/s1"                                      pass "TC-112-12 control: unquoted ~/"
tc "/tmp" "cd -; cp a ~/s1"                                          pass "TC-112-13 control: cp unquoted ~/"
tc "/tmp" "cd -; install a s1"                                       ask  "TC-112-14 install"
tc "/tmp" "cd -; install a /tmp/s1"                                  pass "TC-112-15 control: install absolute"
tc "/tmp" "cd -; ln -sf a s1"                                        ask  "TC-112-16 ln -sf a s1"
tc "/tmp" "cd -; ln -s /tmp/a"                                       ask  "TC-112-17 ln one operand"
tc "/tmp" "cd -; ln -s /tmp/a /tmp/s1"                               pass "TC-112-18 control: ln absolute"
tc "/tmp" "cd -; shuf -o s1 x"                                       ask  "TC-112-19 shuf -o"
tc "/tmp" "cd -; shuf -o /tmp/o x"                                   pass "TC-112-20 control: shuf -o absolute"
tc "/tmp" "cd -; split f p_"                                         ask  "TC-112-21 split"
tc "/tmp" "cd -; split f /tmp/p_"                                    pass "TC-112-22 control: split absolute"
tc "/tmp" "cd -; curl -o s1 http://x"                                ask  "TC-112-23 curl -o"
tc "/tmp" "cd -; curl --output s1 http://x"                          ask  "TC-112-24 curl --output"
tc "/tmp" "cd -; curl -O http://x/f"                                 ask  "TC-112-25 curl -O"
tc "/tmp" "cd -; curl -o /tmp/s1 http://x"                           pass "TC-112-26 control: curl -o absolute"
tc "/tmp" "cd -; curl http://x"                                      pass "TC-112-27 control: curl to stdout"
tc "/tmp" "cd -; wget -O s1 http://x"                                ask  "TC-112-28 wget -O"
tc "/tmp" "cd -; wget --output-document s1 http://x"                 ask  "TC-112-29 wget --output-document"
tc "/tmp" "cd -; wget http://x"                                      ask  "TC-112-30 bare wget"
tc "/tmp" "cd -; wget -O - http://x"                                 pass "TC-112-31 control: wget -O -"
tc "/tmp" "cd -; wget -O /tmp/o http://x"                            pass "TC-112-32 control: wget -O absolute"
tc "/tmp" "cd -; perl -pi -e 's/a/b/' s1"                            ask  "TC-112-33 perl -pi"
tc "/tmp" "cd -; perl -i -ne 'print' s1"                             ask  "TC-112-34 perl -i"
tc "/tmp" "cd -; awk -i inplace '{print}' s1"                        ask  "TC-112-35 awk -i inplace"
tc "/tmp" "cd -; gawk -i inplace '{print}' s1"                       ask  "TC-112-36 gawk -i inplace"
tc "/tmp" "install a s1"                                             pass "TC-112-37 control: install, known folder"
tc "/tmp" "wget http://x"                                            pass "TC-112-38 control: wget, known folder"
tc "/tmp" "cd -; echo x > >(tee s1)"                                 ask  "TC-112-39 >(tee s1) (ask on main too)"
tc "/tmp" "cd -; cat <(tee s1)"                                      ask  "TC-112-40 <(tee s1) (ask on main too)"
tc "/tmp" "cd -; echo x > >(tee -- -a s1)"                           ask  "TC-112-41 >(tee -- -a s1)"
tc "/tmp" "cd -; cd /no/such/dir; $D -rf s1"                         ask  "TC-112-42 cd to a missing folder, delete"
tc "/tmp" "cd -; cd $EXD; $D -rf s1"                                 pass "TC-112-43 cd to a folder that exists, delete"
tc "/tmp" "cd -; cd /no/such/dir; echo x > s1"                       ask  "TC-112-44 cd to a missing folder, write"
tc "/tmp" "cd -; cd $EXD; echo x > s1"                               pass "TC-112-45 cd to a folder that exists, write"
tc "/tmp" "cd -; ( cp a s1 )"                                        ask  "TC-112-48 subshell (ask on main too)"
tc "/tmp" "cd -; { tee s1; }"                                        ask  "TC-112-49 brace group"
tc "/tmp" "cd -; if true; then cp a s1; fi"                          ask  "TC-112-50 if/then"
tc "/tmp" "cd -; if false; then echo; else cp a s1; fi"              ask  "TC-112-51 else"
tc "/tmp" "cd -; for i in 1; do cp a s1; done"                       ask  "TC-112-52 for"
tc "/tmp" "cd -; while true; do cp a s1; done"                       ask  "TC-112-53 while"
tc "/tmp" "cd -; echo a | xargs tee"                                 ask  "TC-112-54 xargs tee"
tc "/tmp" "cd -; echo a | xargs cp /tmp/a"                           ask  "TC-112-55 xargs cp absolute"
tc "/tmp" "cd -; find . -exec cp a {} \\;"                           ask  "TC-112-56 find -exec"
tc "/tmp" "cd -; find . -execdir cp a {} \\;"                        ask  "TC-112-57 find -execdir"
tc "/tmp" "cd -; find . -ok cp a {} \\;"                             ask  "TC-112-58 find -ok"
# fix round (TC-112-66): a wrapper word in front of a writer must not hide it.
# Main's cmdword skips these; lost_writers must too.
tc "/tmp" "cd -; nohup cp a s1"                                       ask  "TC-112-66w nohup cp"
tc "/tmp" "cd -; env cp a s1"                                         ask  "TC-112-66w env cp"
tc "/tmp" "cd -; command cp a s1"                                     ask  "TC-112-66w command cp"
tc "/tmp" "cd -; sudo cp a s1"                                        ask  "TC-112-66w sudo cp"
tc "/tmp" "cd -; nice cp a s1"                                        ask  "TC-112-66w nice cp"
tc "/tmp" "cd -; timeout 5 cp a s1"                                   ask  "TC-112-66w timeout cp"
tc "/tmp" "cd -; exec tee s1"                                         ask  "TC-112-66w exec tee"
tc "/tmp" "cd -; sudo tee s1"                                         ask  "TC-112-66w sudo tee"
tc "/tmp" "cd -; env tee s1"                                          ask  "TC-112-66w env tee"
tc "/tmp" "cd -; nohup tee s1"                                        ask  "TC-112-66w nohup tee"
tc "/tmp" "cd -; stdbuf -oL tee s1"                                   ask  "TC-112-66w stdbuf tee"
tc "/tmp" "cd -; builtin cp a s1"                                     ask  "TC-112-66w builtin cp"
tc "/tmp" "cd -; time nohup cp a s1"                                  ask  "TC-112-66w time nohup cp"
tc "/tmp" "cd -; echo a | nohup tee s1"                               ask  "TC-112-66w pipe nohup tee"
tc "/tmp" "cd -; sudo -u x cp a s1"                                   ask  "TC-112-66w sudo -u x cp"
tc "/tmp" "cd -; sudo nice -n 5 timeout 5 cp a s1"                    ask  "TC-112-66w chained wrappers"
tc "/tmp" "cd -; timeout -k 1 5 cp a s1"                              ask  "TC-112-66w timeout -k"
tc "/tmp" "cd -; sudo cp a /tmp/s1"                                   pass "TC-112-66w sudo cp absolute passes"
tc "/tmp" "cd -; nohup xargs tee s1"                                  ask  "TC-112-66w nohup xargs"
tc "/tmp" "cd -; sudo -n cp a s1"                                     ask  "TC-112-66w sudo -n cp"
tc "/tmp" "cd -; sudo -n tee s1"                                      ask  "TC-112-66w sudo -n tee"
tc "/tmp" "cd -; env -i tee s1"                                       ask  "TC-112-66w env -i tee"
# fix round 2 (TC-112-66): a backslash-escaped file name is a relative name (not an option,
# not the home folder, not empty); main asks for all of these after a lost folder.
tc "/tmp" "cd -; cp a \\-x"                                           ask  "TC-112-66e cp a \\-x"
tc "/tmp" "cd -; tee \\-x"                                            ask  "TC-112-66e tee \\-x"
tc "/tmp" "cd -; sed -i p \\-x"                                       ask  "TC-112-66e sed -i p \\-x"
tc "/tmp" "cd -; dd of=\\~ if=a"                                      ask  "TC-112-66e dd of=\\~"
tc "/tmp" "cd -; sed -i p \\~"                                        ask  "TC-112-66e sed -i p \\~"
tc "/tmp" "cd -; cp --target-directory=\\~ a"                         ask  "TC-112-66e cp --target-directory=\\~"
tc "/tmp" "cd -; cp a \\"                                             ask  "TC-112-66e cp a trailing backslash"
tc "/tmp" "cd -; tee \\"                                              ask  "TC-112-66e tee trailing backslash"
tc "/tmp" "cd -; sed -i p \\"                                         ask  "TC-112-66e sed -i p trailing backslash"
tc "/tmp" "cd -; sort -o \\"                                          ask  "TC-112-66e sort -o trailing backslash"
tc "/tmp" "cd -; dd of=\\"                                            ask  "TC-112-66e dd of= trailing backslash"
tc "/tmp" "cd -; cp a \\ "                                            ask  "TC-112-66e cp a escaped space"
rs() { # rs <command> -> OUT: the reason text of the gate
  OUT=$(python3 -c "import json,sys;print(json.dumps({'cwd':'/tmp','tool_input':{'command':sys.argv[1]}}))" "$PFX$1" | bash "$H")
  OUT=$(PYTHONIOENCODING=utf-8 python3 -c "import json,sys;print(json.load(sys.stdin)['hookSpecificOutput'].get('permissionDecisionReason',''))" <<<"$OUT")
}
cnt() { grep -o "$1" <<<"$OUT" | wc -l; }
printf '%-58s ' "TC-112-59 reason printed once"
rs "cd -; echo x > s1"; [ "$(cnt 'overwrite s1')" = 1 ] && echo "ok" || { echo "FAIL: overwrite s1 x$(cnt 'overwrite s1')"; fails=$((fails+1)); }
printf '%-58s ' "TC-112-60 two reasons once each"
rs "cd -; echo x > s1; echo y > s2"; [ "$(cnt 'overwrite s1')" = 1 ] && [ "$(cnt 'overwrite s2')" = 1 ] && echo "ok" || { echo "FAIL: s1 x$(cnt 'overwrite s1') s2 x$(cnt 'overwrite s2')"; fails=$((fails+1)); }
tc "/tmp" "cd $P; cd -; $D -rf results"                              deny "TC-112-63 results stays deny after lost folder"
tc "/tmp" "$D -rf $P/results"                                        deny "TC-112-64 results stays deny"
tc "/tmp" "$D -rf $P/work"                                           ask  "TC-112-65 work/ asks"
# Plan items beyond the TCs: the directory stack and the two views
tc "/tmp" "cd $P; pushd results; popd; $D -rf x"                 deny "TC-056 pushd results; popd: judged as main does (Rev 3)"
tc "/tmp" "cd $P; pushd res\ults; popd; $D -rf x"                deny "plan: pushd res-ults; popd keeps results (Rev 3, stricter than main)"
tc "/tmp" "cd $P; pushd /tmp; popd; pushd res\ults; $D -rf x"    deny "plan: a stack entry does not leak into the next pushd"
tps "cd $P; Push-Location results; Pop-Location; Remove-Item -Recurse x" deny "plan: Push-Location results; Pop-Location keeps results (Rev 3)"
tc "/tmp" "cd $P; Push-Location results; $D -rf x"               deny "plan: Bash Push-Location results is judged"
tps "cd $P/results; Set-Location \$d; Remove-Item -Recurse x"    deny "plan: an unreadable Set-Location target keeps the old folder"
tcp PowerShell "$P" 'Get-ChildItem reports | Move-Item -Destination x'         pass "plan: control: lister of reports, from the run folder"

# Review round 1: a directory change moves both views only when the gate can model it
# exactly; anything else keeps the old folder in one view (never drops it). Main's verdict for each is deny.
tcp Bash "$P" "pushd results; popd -n; $D -rf x"                                deny "R1 popd -n does not move"
tcp Bash "$P" "pushd /tmp; pushd results; popd +1; $D -rf x"                    deny "R1 popd +1 does not move to the top"
tcp Bash "$P" "pushd results; dirs -c; popd; $D -rf x"                          deny "R1 dirs -c empties the stack, popd fails"
tcp PowerShell "$P/results" "Push-Location -StackName a /tmp; Push-Location -StackName b /var; Pop-Location -StackName a; Remove-Item x" deny "R1 named stacks"
tcp PowerShell "$P/results" 'sl /tmp; sl -; Remove-Item x'                      deny "R1 sl - goes back"
tcp PowerShell "$P/results" 'Push-Location /tmp; Push-Location -; Remove-Item x' deny "R1 Push-Location - goes back"
tcp PowerShell "$P/results" 'sl ../res*; Remove-Item x'                         deny "R1 a wildcard target"
tcp PowerShell "$P/results" 'sl ..; sl -Path (Join-Path $PWD results); Remove-Item x' deny "R1 an evaluated target"
tcp PowerShell "$P/results" 'sl ..; sl @("results"); Remove-Item x'             deny "R1 an array target"
tcp Bash "$P" "pushd results; popd; $D -rf x"                                   deny "TC-056 a bare popd is judged as main does"
tcp PowerShell "/tmp" 'sl $d; Remove-Item x'                                    pass "R1 control: an unknown target from a harmless folder"
# Review round 1, verifier additions: the new handlers (popd, Pop-Location, the PowerShell
# location cmdlets) must not drop the old folder when they may not run or may not touch this shell.
tcp Bash "$P" "pushd results; false && popd; $D -rf x"                          deny "R1 false && popd"
tcp Bash "$P" "pushd results; exit 0 || popd; $D -rf x"                         deny "R1 exit 0 || popd"
tcp Bash "$P" "pushd results; popd | cat; $D -rf x"                             deny "R1 popd | cat"
tcp Bash "$P" "pushd results; (popd); $D -rf x"                                 deny "R1 (popd)"
tcp Bash "$P" "pushd results; echo a | popd; $D -rf x"                          deny "R1 echo a | popd"
tcp Bash "$P" "pushd results; popd & $D -rf x"                                  deny "R1 popd &"
tcp Bash "$P" "pushd results; command popd; $D -rf x"                           deny "R1 command popd"
tcp PowerShell "$P/results" 'sl -Foo /tmp; Remove-Item x'                       deny "R1 an unknown option on Set-Location"
tcp PowerShell "$P/results" 'sl /tmp -WhatIf; Remove-Item x'                    deny "R1 Set-Location -WhatIf"
tcp PowerShell "$P/results" 'sl /tmp; Pop-Location -Foo; Remove-Item x'         deny "R1 Pop-Location with an unknown option"
tcp PowerShell "$P" 'Push-Location results; Pop-Location -PassThru; Remove-Item x' deny "TC-060 Pop-Location -PassThru is judged as main does"
tcp PowerShell "$P" 'sl -PassThru /tmp; Remove-Item x'                          pass "R1 control: -PassThru is harmless"
tcp PowerShell "$P/results" 'false && sl /tmp; Remove-Item x'                   deny "R1 sl after &&"

# TC-066 (revision 3): every shape of the verifier's 237-shape list plus TC-045..065, with the
# verdict c4a7327 gives it as the expectation (a row where this fix is stricter than main
# carries the stricter verdict and is listed in .specify/bugs/cd-target-backslash/fix.md).
# File format: tool|cwd|expected|command ; @P = the run folder, @D = the delete verb,
# the character U+23CE = a line break in the command.
while IFS='|' read -r s_tool s_cwd s_exp s_cmd; do
  [ -n "$s_tool" ] || continue
  s_cmd=${s_cmd//⏎/$'\n'}; s_cmd=${s_cmd//@P/$P}; s_cmd=${s_cmd//@D/$D}; s_cwd=${s_cwd//@P/$P}
  tcp "$s_tool" "$s_cwd" "$s_cmd" "$s_exp" "TC-066 $s_tool $(printf '%s' "${s_cmd:0:44}" | tr '\n' ' ')"
done < "$(dirname "${BASH_SOURCE[0]}")/confirm_cleanup_shapes.txt"

echo
echo "== #62: a guard that cannot finish in time asks, instead of being cancelled =="
# hooks.json gives the hook 30 s; a hook cancelled there lets the call PROCEED.
# Past its own deadline (20 s; ABF_CLEANUP_DEADLINE_S can only lower it, for
# this test) the guard stops judging and asks, saying why (invariant 13).
dl() { # dl <deadline> <command> -> OUT, GOT
  OUT=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$PFX$2" \
        | ABF_CLEANUP_DEADLINE_S="$1" bash "$H")
  if [ -z "$OUT" ]; then GOT=pass; else
    GOT=$(PYTHONIOENCODING=utf-8 python3 -c "import json,sys;o=json.load(sys.stdin)['hookSpecificOutput'];print(o.get('permissionDecision','warn'))" <<<"$OUT")
  fi
}
printf '%-58s ' "#62 deadline reached: asks, even for an ordinary delete"
dl 0 "$D -rf /tmp/x"
if [ "$GOT" = ask ] && grep -q 'in time' <<<"$OUT"; then echo "ok (ask)"; else
  echo "FAIL: expected an ask that says it ran out of time, got $GOT <<${OUT:0:80}>>"; fails=$((fails+1)); fi
printf '%-58s ' "#62 control: the same delete with the default deadline"
dl "" "$D -rf /tmp/x"; [ "$GOT" = pass ] && echo "ok (pass)" || { echo "FAIL: got $GOT"; fails=$((fails+1)); }
# #62: a target is resolved through `readlink` only when a component of it is a
# link here (it cost a program per target); a delete through a link into the
# shared references must still be judged by where it lands.
LK=$(mktemp -d)
mkdir -p "$LK/lab/_references/genome" "$LK/run/other"
ln -s "$LK/lab/_references" "$LK/run/references"
t "$D -rf $LK/run/references/*"                   deny "#62 a delete through a link into _references/"
tc "$LK/run" "$D -rf references/genome"           deny "#62 ...relative, from the working folder"
t "$D -rf $LK/run/other"                          pass "#62 control: a real folder beside the link"
rm -rf "$LK"
printf '%-58s ' "#62 control: a deadline that is not a number is ignored"
dl "soon" "$D -rf /tmp/x"; [ "$GOT" = pass ] && echo "ok (pass)" || { echo "FAIL: got $GOT"; fails=$((fails+1)); }

rmdir "$EXD" 2>/dev/null
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
