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

# #44: D3 (the bare-ssh reminder) reads the REAL `uname -s`, and it is MSYS-only.
# Run natively in Git Bash this file's real uname IS MSYS, so every case below
# that is not about D3 (a read-only `ssh h 'grep ...'` that must pass, the
# "NOT on MSYS" case) saw D3 fire. The fix is the fixture, not the hook: from
# here on every hook call in this file sees a platform that is not MSYS unless
# a case puts MSYSBIN (below) in front. On Linux/macOS this changes nothing.
LINUXDIR=$(mktemp -d)
cat > "$LINUXDIR/uname" <<'EOF'
#!/bin/bash
[ "$1" = -s ] && { echo Linux; exit 0; }
exec /usr/bin/uname "$@"
EOF
chmod +x "$LINUXDIR/uname"
export PATH="$LINUXDIR:$PATH"

# Guard for the shim above: a case that is not about D3 must not run on a
# platform the hook reads as MSYS. Red natively in Git Bash before the shim.
printf '%-58s ' "#44 fixture: the default uname -s is not MSYS (D3 is MSYS-only)"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) echo "FAIL: uname -s says $(uname -s); D3 would fire on every bare ssh below"; fails=$((fails+1)) ;;
  *) echo ok ;;
esac

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

# #29: launch shapes that used to pass with no output (red on main 12dda0c).
LW="w$(printf '\x69\x74\x68')_override.sh"            # relaunch_with_override.sh, assembled
RLW="scripts/$(printf '\x72\x65\x6c\x61\x75\x6e\x63\x68')_$LW"
LVERB=$(printf '\x6c\x61\x75\x6e\x63\x68')
t "tw -o json $LVERB x --disable-optimization"       gate "#29 tw global option before the verb"
t "tw --url=https://x.example $LVERB x"              gate "#29 tw --url= before the verb"
t "tw -o json runs $(printf '\x72\x65\x6c\x61\x75\x6e\x63\x68') -i abc" gate "#29 relaunch with a global option"
t "nextflow -bg $(printf '\x72\x75\x6e') main.nf"    gate "#29 nextflow -bg before run"
t "nextflow -c site.config $(printf '\x72\x75\x6e') main.nf" gate "#29 nextflow -c before run"
t "echo '$LAUNCH x' | bash"                          gate "#29 launch piped into a shell"
t "$(printf 'bash -s <<%s\n%s x\nEOF\n' "'EOF'" "$LAUNCH")"            gate "#29 here-doc fed to bash"
t "$(printf 'ssh h bash -s <<%s\n%s x\nEOF\n' "'EOF'" "$LAUNCH")"      gate "#29 here-doc fed to ssh bash"
t "$(printf 'cat <<%s | bash\n%s x\nEOF\n' "'EOF'" "$LAUNCH")"       gate "#29 here-doc piped into bash"
t "bash $RLW --confirm 3xY proc 4 16"                gate "#29 relaunch_with_override --confirm starts a run"
t "bash $RLW --dry-run 3xY proc 4 16"                pass "#29 its --dry-run starts nothing"
t "bash $RLW 3xY proc 4 16"                          pass "#29 without --confirm it only prints the plan"
t "grep -n '$RLW --confirm' docs/x.md"               pass "#29 reading about it is not running it"
t "tw pipelines list"                                pass "#29 other tw verbs stay quiet"
t "tw -o json runs list"                             pass "#29 listing runs with a global option"
t "nextflow log"                                     pass "#29 nextflow log is not a run"

# #29 acceptance round 2 (reviewer's findings on 939576b).
t "echo \$($LAUNCH x)"                                gate "#29b launch inside \$(...)"
t "ls \`$LAUNCH x\`"                                  gate "#29b launch inside backticks"
t "cat <($LAUNCH x)"                                  gate "#29b launch inside <(...)"
t "python3 -c 'import os; os.system(\"$LAUNCH y\")'"  gate "#29b python -c os.system(...)"
t "perl -e 'system(\"$LAUNCH y\")'"                   gate "#29b perl -e system(...)"
t "$(printf 'sudo -u u bash <<%s\n%s x\nEOF\n' "'EOF'" "$LAUNCH")"  gate "#29b here-doc into sudo -u bash"
t "$(printf 'srun bash <<%s\n%s x\nEOF\n' "'EOF'" "$LAUNCH")"       gate "#29b here-doc into srun bash"
t "$(printf 'python3 - <<%s\nimport subprocess\nsubprocess.run([\"tw\", \"%s\", \"x\"])\nEOF\n' "'EOF'" "$LVERB")" gate "#29b python here-doc, argv list"
t "env A=1 nextflow $(printf '\x72\x75\x6e') main.nf" gate "#29b env prefix before nextflow run"
t "sudo -u x $LAUNCH y"                               gate "#29b sudo -u before tw"
t "echo \"\$(tw runs list)\""                        pass "#29b a read-only substitution"
t "\"tw\" $LVERB x"                                   gate "#29b the program itself in quotes"
t "bash -e -c '$LAUNCH x'"                            gate "#29c bash with options before -c"
# #29 round 4: main kept every quoted string when a nested shell was on the
# line; the splitter only re-reads strings given to a known executor, so a
# launch handed on to tmux/su/flock inside ssh stopped gating.
t "ssh h \"cd /work/run && tmux new -d -s nf 'nextflow $(printf '\x72\x75\x6e') nf-core/ampliseq -resume'\"" gate "#29d ssh -> tmux -> nextflow run (main: ask)"
t "ssh h \"su - lab -c '$SB job.sh'\""                gate "#29d ssh -> su -c -> sbatch"
t "ssh h \"flock /tmp/l -c '$SB job.sh'\""            gate "#29d ssh -> flock -c -> sbatch"
t "eval \"tmux new -d '$LAUNCH x'\""                  gate "#29d eval -> tmux -> launch"
t "ssh h 'grep \"$LAUNCH\" notes.md'"                 pass "#29d ssh running a read-only grep of the words"
t "bash <<< '$LAUNCH x'"                              gate "#29c here-string into bash"
t "echo '$LAUNCH x' |& bash"                          gate "#29c |& into bash"
t "echo '$LAUNCH x' | env bash"                       gate "#29c | env bash"
t "T=tw; \$T $LVERB x"                               gate "#29c program in a variable"
t "\"\$TW\" $LVERB x"                                 gate "#29c program in a quoted variable"
t "tw.exe $LVERB x"                                   gate "#29c tw.exe"
t "echo \$(echo \$(echo \$(echo \$(echo \$($LAUNCH x)))))" gate "#29c deeply nested \$(...)"
t "$(printf "grep -c '<<EOF' notes.sh\n%s x" "$LAUNCH")" gate "#29c a quoted <<EOF is not a here-doc"
t "echo \$T $LVERB"                                   pass "#29c echoing a variable next to the word"
t "'/usr/local/bin/nextflow' $(printf '\x72\x75\x6e') main.nf" gate "#29b quoted path to nextflow"
t "git commit -m \"docs: how $LAUNCH works\""         pass "#29b a commit message quoting a launch"
t "grep -rn 'os.system(' scripts/"                    pass "#29b searching for os.system("

tmcp() { # tmcp <tool_name> <expect gate|pass> <label> - an MCP tool, no command field
  printf '%-56s ' "$3"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_name':sys.argv[1],'tool_input':{'pipeline':'nf-core/rnaseq','revision':'3.14.0'}}))" "$1" | bash "$H")
  got=pass; [ -n "$out" ] && got=gate
  [ "$got" = "$2" ] && echo "ok ($got)" || { echo "FAIL: expected $2, got $got"; fails=$((fails+1)); }
}
tmcp "mcp__seqera__$(printf '\x6c\x61\x75\x6e\x63\x68')_pipeline" gate "#29 an MCP tool named for launching"
tmcp "mcp__seqera__$(printf '\x72\x65\x6c\x61\x75\x6e\x63\x68')_run" gate "#29 an MCP tool named for relaunching"
tmcp "mcp__seqera__list_runs"                          pass "#29 an MCP tool that only lists"

# A third failure, found by trying it rather than by it happening: the trigger
# logic now lives in a sourced file, and a sourced file can go missing. When it
# did, `is_launch_command` was command-not-found, 127 satisfied the `|| exit 0`,
# and the gate vanished for EVERY command with nothing printed - the same shape
# as the relaunch miss above, but total. So the load is fail-closed, and this
# case is what keeps it that way.
TMP=$(mktemp -d); trap 'rm -rf "$TMP" "$LINUXDIR"' EXIT
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
Z2TMP=$(mktemp -d); trap 'rm -rf "$Z2TMP" "$TMP" "$LINUXDIR" 2>/dev/null' EXIT

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
# T1: no jq is SCOPED fail-closed (Fixes #15), not a blanket refusal.
#
# PITFALLS 28's blanket "refuse everything until jq exists" was correct
# against the failure it was written for (a launch slipping through
# unnoticed) and wrong about its own cost: a member on this exact path
# stopped using the plugin's safety net altogether and started typing
# commands into a bare PowerShell window instead, which has none of it.
# Unbounded fail-closed had become the thing driving people around the net,
# not through it. So this hook now asks a narrower question with nothing but
# a shell `case` on the raw bytes it received (no jq, no grep -E either - one
# more binary that could be the very thing missing): does the text look like
# it could start a run or reach the site directly. A command that clearly
# cannot is let through exactly as it would be with jq present and nothing
# matching - silent, no extra prompt - and only a real match still blocks.
#
# How jq is hidden without also losing bash: tests/lib/nojq_path.sh.
. "$(dirname "${BASH_SOURCE[0]}")/lib/nojq_path.sh"
NOJQ_PATH=$(nojq_path "$TMP") || { echo "cannot build a PATH without jq"; exit 1; }

nojq() { # nojq <command-string>
    python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" \
        | PATH="$NOJQ_PATH" bash "$H"
}

printf '%-56s ' "(b) no jq + a real launch - still BLOCKED"
out=$(nojq "$LAUNCH x --disable-optimization" 2>"$TMP/nojq_launch_err"); rc=$?
err=$(cat "$TMP/nojq_launch_err" 2>/dev/null)
if [ "$rc" = 2 ] && [ -z "$out" ]; then echo "ok (rc=2, no stdout)"; else
    echo "FAIL: rc=$rc out='$out'"; fails=$((fails+1)); fi

printf '%-56s ' "(a) no jq + an unrelated command - exit 0, no noise"
out=$(nojq "ls -la" 2>"$TMP/nojq_ls_err"); rc=$?
err=$(cat "$TMP/nojq_ls_err" 2>/dev/null)
if [ "$rc" = 0 ] && [ -z "$out" ] && [ -z "$err" ]; then echo "ok (rc=0, silent)"; else
    echo "FAIL: rc=$rc out='$out' err='$err' (should pass through silently - it cannot look launch-shaped)"
    fails=$((fails+1))
fi

printf '%-56s ' "no jq + sbatch, no launch verb - still BLOCKED"
out=$(nojq "$SB driver.sh" 2>"$TMP/nojq_sb_err"); rc=$?
[ "$rc" = 2 ] && [ -z "$out" ] && echo "ok (rc=2)" || { echo "FAIL: rc=$rc out='$out'"; fails=$((fails+1)); }

printf '%-56s ' "no jq + a direct ssh call - still BLOCKED (site-transport shaped)"
out=$(nojq "ssh twnia3 ls" 2>"$TMP/nojq_ssh_err"); rc=$?
[ "$rc" = 2 ] && [ -z "$out" ] && echo "ok (rc=2)" || { echo "FAIL: rc=$rc out='$out'"; fails=$((fails+1)); }

printf '%-56s ' "no jq: BLOCKED case's stderr names the fix, per platform"
out=$(nojq "$LAUNCH x --disable-optimization" 2>"$TMP/nojq_launch_err2"); rc=$?
err=$(cat "$TMP/nojq_launch_err2" 2>/dev/null)
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
# guard exists to stop. Measured: the guard had to probe, not just look. The
# scoping applies here too: a broken jq is judged the same narrow way a
# missing one is.
echo "== a broken jq is judged the same scoped way as a missing one =="
BADDIR=$(mktemp -d)
printf '#!/bin/sh\nexit 127\n' > "$BADDIR/jq"; chmod +x "$BADDIR/jq"

out=$(echo '{"tool_name":"Bash","tool_input":{"command":"'"$LAUNCH"' x --disable-optimization"}}' \
      | env PATH="$BADDIR:$PATH" bash "$H" 2>"$TMP/broken_jq_err")
rc=$?
err=$(cat "$TMP/broken_jq_err" 2>/dev/null)
printf '%-64s ' "refuses a launch-shaped command when jq exists but cannot run"
[ "$rc" = 2 ] && echo ok || { echo "FAIL: exit $rc, wanted 2"; fails=$((fails+1)); }
printf '%-64s ' "and says so instead of failing silently"
case "$err" in *BLOCKED*) echo ok ;; *) echo "FAIL: said '$err'"; fails=$((fails+1)) ;; esac

out=$(echo '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}' \
      | env PATH="$BADDIR:$PATH" bash "$H" 2>"$TMP/broken_jq_ls_err")
rc=$?
printf '%-64s ' "does NOT refuse an unrelated command in the same broken-jq state"
[ "$rc" = 0 ] && [ -z "$out" ] && echo ok || { echo "FAIL: rc=$rc out='$out'"; fails=$((fails+1)); }
rm -rf "$BADDIR"

echo
echo "== T1 (c): a non-Bash, execution-shaped tool this file has never named =="
# hooks.json's matcher now reaches tools other than Bash (a PowerShell-shaped
# MCP tool among them). jq works in every case below - the point here is
# whether THIS FILE can read what such a tool was asked to run, not whether
# jq is present.
ps_input() { # ps_input <tool_name> <field> <value>
    python3 -c "import json,sys;print(json.dumps({'tool_name':sys.argv[1],'tool_input':{sys.argv[2]:sys.argv[3]}}))" \
        "$1" "$2" "$3"
}

printf '%-64s ' "a non-Bash tool using tool_input.command - judged exactly as Bash would be"
out=$(ps_input PowerShell command "$LAUNCH x --disable-optimization" | bash "$H")
decision=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out" 2>/dev/null)
[ "$decision" = ask ] && echo "ok (ask)" || { echo "FAIL: expected ask, got '$decision' <<$out>>"; fails=$((fails+1)); }

printf '%-64s ' "same tool, under tool_input.script - also read"
out=$(ps_input PowerShell script "$LAUNCH x --disable-optimization" | bash "$H")
decision=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out" 2>/dev/null)
[ "$decision" = ask ] && echo "ok (ask)" || { echo "FAIL: expected ask, got '$decision' <<$out>>"; fails=$((fails+1)); }

printf '%-64s ' "same tool, under tool_input.powershell - also read"
out=$(ps_input PowerShell powershell "$LAUNCH x --disable-optimization" | bash "$H")
decision=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out" 2>/dev/null)
[ "$decision" = ask ] && echo "ok (ask)" || { echo "FAIL: expected ask, got '$decision' <<$out>>"; fails=$((fails+1)); }

printf '%-64s ' "an unparseable tool (unknown field name) that looks launch-shaped - ask"
UNKNOWN=$(python3 -c "import json,sys;print(json.dumps({'tool_name':'mcp__win__powershell','tool_input':{'script_block':sys.argv[1]}}))" \
            "$LAUNCH x --disable-optimization")
out=$(echo "$UNKNOWN" | bash "$H")
decision=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out" 2>/dev/null)
[ "$decision" = ask ] && echo "ok (ask)" || { echo "FAIL: expected ask, got '$decision' <<$out>>"; fails=$((fails+1)); }

printf '%-64s ' "an unparseable tool with harmless content - allowed, no output"
UNKNOWN=$(python3 -c "import json,sys;print(json.dumps({'tool_name':'mcp__win__powershell','tool_input':{'script_block':sys.argv[1]}}))" \
            "Get-ChildItem")
out=$(echo "$UNKNOWN" | bash "$H")
[ -z "$out" ] && echo "ok (no output at all)" || { echo "FAIL: expected nothing, got <<$out>>"; fails=$((fails+1)); }

echo
echo "== R2: Claude Code itself asks (permissionDecision: ask) =="
# A launch-shaped command must not just add prose to additionalContext - it
# must make Claude Code pause with a structural `ask`, carrying the full
# command (and any unmet preconditions) in permissionDecisionReason. A
# non-launch command must carry no decision field at all: this file never
# turns an existing "allow" into anything else, only adds "ask" where a real
# launch is seen. Every case here also checks the JSON starts with `{` -
# PITFALLS 28's appendix-2 fact 3, stdout noise before the JSON is a silent
# gate no differently than a missing jq.
askcheck() { # askcheck <command> <label>
  printf '%-58s ' "$2"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" | bash "$H")
  first="${out:0:1}"
  if [ "$first" != "{" ]; then
    echo "FAIL: stdout did not start with '{': <<${out:0:60}>>"; fails=$((fails+1)); return
  fi
  decision=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out")
  reason=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecisionReason',''))" <<<"$out")
  if [ "$decision" != ask ]; then
    echo "FAIL: expected permissionDecision=ask, got '$decision'"; fails=$((fails+1)); return
  fi
  case "$reason" in
    *"$1"*) echo ok ;;
    *) echo "FAIL: reason did not contain the full command <<$reason>>"; fails=$((fails+1)) ;;
  esac
}
nodecisioncheck() { # nodecisioncheck <command> <label>
  printf '%-58s ' "$2"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" | bash "$H")
  if [ -z "$out" ]; then echo "ok (no output at all)"; return; fi
  first="${out:0:1}"
  if [ "$first" != "{" ]; then
    echo "FAIL: stdout did not start with '{': <<${out:0:60}>>"; fails=$((fails+1)); return
  fi
  decision=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision','') or '')" <<<"$out")
  if [ -z "$decision" ]; then echo "ok (no decision field)"; else
    echo "FAIL: unexpected permissionDecision '$decision' on a non-launch command"; fails=$((fails+1))
  fi
}

askcheck "$LAUNCH https://github.com/nf-core/rnaseq --disable-optimization" "tw launch: ask, reason has the full command"
askcheck "$RELAUNCH -i 344PjpDnrQiz4U"                                      "tw runs relaunch: ask, reason has the full command"
askcheck "$NFRUN main.nf"                                                   "nextflow run: ask, reason has the full command"
askcheck "$SB driver.sh"                                                    "sbatch: ask, reason has the full command"

nodecisioncheck "tw runs list --workspace 12345"                            "tw runs list: no decision field"
nodecisioncheck "cat launch.md"                                             "cat launch.md: no decision field"

echo
echo "== D3: the transport branch, MSYS only =="
# A fake uname ahead of the real PATH, the same technique
# tests/conditions_matrix_test.sh uses. Only -s is answered; anything else
# falls through to the real uname so this doesn't have to stub every call
# this hook or its subprocesses might make.
MSYSBIN="$TMP/msysbin"; mkdir -p "$MSYSBIN"
cat > "$MSYSBIN/uname" <<'EOF'
#!/bin/bash
[ "$1" = -s ] && { echo MINGW64_NT-10.0-22631; exit 0; }
exec /usr/bin/uname "$@"
EOF
chmod +x "$MSYSBIN/uname"

# askcheck/nodecisioncheck above don't let the PATH be swapped, so D3 gets its
# own pair rather than reusing theirs a second way.
msys_ask() { # msys_ask <command> <label>
  printf '%-58s ' "$2"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" \
        | PATH="$MSYSBIN:$PATH" bash "$H")
  first="${out:0:1}"
  if [ "$first" != "{" ]; then
    echo "FAIL: stdout did not start with '{': <<${out:0:60}>>"; fails=$((fails+1)); return
  fi
  decision=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision',''))" <<<"$out")
  reason=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecisionReason',''))" <<<"$out")
  if [ "$decision" != ask ]; then
    echo "FAIL: expected permissionDecision=ask, got '$decision'"; fails=$((fails+1)); return
  fi
  case "$reason" in
    *on_site.sh*) echo ok ;;
    *) echo "FAIL: reason did not name on_site.sh <<$reason>>"; fails=$((fails+1)) ;;
  esac
}
msys_pass() { # msys_pass <command> <label>
  printf '%-58s ' "$2"
  out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$1" \
        | PATH="$MSYSBIN:$PATH" bash "$H")
  if [ -z "$out" ]; then echo "ok (no output at all)"; return; fi
  first="${out:0:1}"
  if [ "$first" != "{" ]; then
    echo "FAIL: stdout did not start with '{': <<${out:0:60}>>"; fails=$((fails+1)); return
  fi
  decision=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecision','') or '')" <<<"$out")
  if [ -z "$decision" ]; then echo "ok (no decision field)"; else
    echo "FAIL: unexpected permissionDecision '$decision' on a command that should not be flagged"; fails=$((fails+1))
  fi
}

msys_ask  "ssh twnia3 ls"                              "bare ssh on MSYS: ask, names on_site.sh"
msys_ask  "scp file.txt twnia3:/tmp/"                  "bare scp on MSYS: ask"
msys_ask  "rsync -av ./data/ twnia3:/work/"            "bare rsync on MSYS: ask"
msys_ask  "sftp twnia3"                                "bare sftp on MSYS: ask"
msys_ask  "cat notes.txt && ssh twnia3 ls"             "ssh inside a compound command on MSYS: ask"

msys_pass "scripts/on_site.sh 'ls -la'"                "already routed through on_site.sh: not flagged"
msys_pass "scripts/on_site.sh ls"                      "on_site.sh without a quoted payload: not flagged"
# The one case that actually exercises the ONSITE_RE exclusion rather than
# just relying on "on_site.sh" never matching TRANSPORT_RE in the first
# place: here the bare word "ssh" is itself an unquoted argument to
# on_site.sh, in the same segment. Without the exclusion this would ask.
msys_pass "scripts/on_site.sh ssh"                     "bare 'ssh' as on_site.sh's own argument: not flagged"
msys_pass "grep -rn \"ssh\" docs/"                     "read-only mention of ssh, quoted, on MSYS: not flagged"
msys_pass "cat ssh_notes.md"                           "a filename containing ssh, not the command word: not flagged"

# Feature 005 (#48), FR-006: two shapes of ssh that cannot cost a one-time code,
# so the reminder does not apply to them. Through WSL (command word wsl or
# wsl.exe) the connection can share one that is already open (PITFALLS 16g);
# with -o BatchMode=yes ssh never prompts, it fails instead. These run with no
# session id, i.e. "in use" (hooks/in_use.sh), so they exercise D3 itself.
msys_pass "wsl.exe -e ssh -o ControlPath=/tmp/cm-%C -o BatchMode=yes u@login 'scontrol show partition; sacctmgr show qos'" "FR-006 the incident command (wsl.exe, BatchMode): not flagged"
msys_pass "wsl ssh u@host ls"                          "FR-006 ssh through wsl: not flagged"
msys_pass "/c/Windows/System32/wsl.exe -e ssh u@host ls" "FR-006 ssh through wsl.exe by path: not flagged"
msys_pass "C:\Windows\System32\wsl.exe -e ssh u@host ls" "FR-006 ssh through wsl.exe by a Windows path: not flagged"
msys_pass "ssh -o BatchMode=yes u@host ls"             "FR-006 ssh -o BatchMode=yes: not flagged"
msys_pass "ssh -oBatchMode=yes u@host ls"              "FR-006 ssh -oBatchMode=yes (glued): not flagged"
msys_pass "ssh -o \"BatchMode=yes\" u@host ls"         "FR-006 ssh -o \"BatchMode=yes\" (quoted): not flagged"
msys_pass "scp -o BatchMode=yes a u@host:b"            "FR-006 scp -o BatchMode=yes: not flagged"
# ...and what must keep asking (TC-015)
msys_ask  "ssh u@host ls"                              "FR-006 control: plain ssh still asks"
msys_ask  "ssh -o BatchMode=no u@host ls"              "FR-006 control: BatchMode=no still asks"
msys_ask  "ssh -o BatchMode=yesplease u@host ls"       "FR-006 control: a value that merely starts with yes still asks"
msys_ask  "ssh -o BatchMode=no -o BatchMode=yes u@host ls" "FR-006 control: a second, conflicting BatchMode still asks"
msys_ask  "echo wsl; ssh u@host ls"                    "FR-006 control: wsl as an earlier segment does not excuse the ssh"
msys_ask  "echo wsl && ssh u@host ls"                  "FR-006 control: ...also with &&"
msys_ask  "echo BatchMode=yes; ssh u@host ls"          "FR-006 control: BatchMode=yes in another segment does not excuse it"
msys_ask  "ssh -o BatchMode=yes u@host ls; scp a u@host:b" "FR-006 control: the exception is per segment (the scp asks)"
msys_ask  "ssh u@host 'echo -o BatchMode=yes'"         "FR-006 control: the words inside a quoted payload do not count"
msys_ask  "wsl.exe -e true; ssh u@host ls"             "FR-006 control: wsl.exe in its own segment does not excuse the next"
# Acceptance findings (M3): the option must be ssh's own, before the destination,
# and nothing that can still prompt (a jump host) may ride along. Unsure asks.
msys_ask  "ssh u@login \"ssh -o 'BatchMode=yes' node01 squeue\"" "M3a BatchMode inside the remote command does not excuse the outer ssh"
msys_ask  "ssh u@login 'ssh -o \"BatchMode=yes\" node01 squeue'" "M3a ...same with the quotes the other way round"
msys_ask  "ssh -o BatchMode=yes -J u@login u@node01 squeue"  "M3b a jump host (-J) can still prompt: asks"
msys_ask  "ssh -o BatchMode=yes -oProxyJump=u@login u@node01 squeue" "M3b ProxyJump option: asks"
msys_ask  "ssh -o BatchMode=yes -o ProxyCommand='ssh u@login -W %h:%p' u@node01 squeue" "M3b ProxyCommand: asks"
# #53: a config file named on the command line can carry a ProxyJump too.
msys_ask  "ssh -o BatchMode=yes -F jump.cfg u@node01 squeue" "#53 -F cfg (may hold a ProxyJump): asks"
msys_ask  "ssh -o BatchMode=yes -Fjump.cfg u@node01 squeue"  "#53 -Fcfg glued: asks"
msys_ask  "scp -o BatchMode=yes -F jump.cfg a u@node01:b"    "#53 scp -F cfg: asks"
msys_pass "ssh -o BatchMode=yes -i /k u@node01 squeue"       "#53 control: the same call without -F: not flagged"
msys_ask  "ssh u@login squeue -o BatchMode=yes"        "M3c BatchMode after the destination belongs to the remote command: asks"
msys_ask  "rsync -av a u@host:b -o BatchMode=yes"      "M3c rsync -o is not ssh's option: asks"
msys_ask  "rsync -e 'ssh -o BatchMode=yes' a u@host:b" "M3c rsync -e carries its own ssh: asks"
msys_ask  "ssh -o 'BatchMode yes' u@host ls"           "M3 the space spelling is not understood: asks"
msys_pass "ssh -p 22 -o BatchMode=yes u@host ls"       "M3 an option with its argument before BatchMode: not flagged"
msys_pass "ssh -v -o BatchMode=yes -i /k u@host ls"    "M3 flags around it: not flagged"
msys_ask  "ssh -p 22 u@host -o BatchMode=yes ls"       "M3c destination first: asks"

printf '%-58s ' "the same bare ssh call, but NOT on MSYS: not flagged (D3 is MSYS-only)"
out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "ssh twnia3 ls" | bash "$H")
if [ -z "$out" ]; then echo "ok (no output at all)"; else
  echo "FAIL: D3 fired off MSYS <<$out>>"; fails=$((fails+1))
fi

# A launch-shaped ssh call on MSYS must still behave exactly as before: the
# existing launch gate (is_launch_command sees "tw launch" in the payload)
# wins, not the new transport branch - same decision, same reason shape as
# the non-MSYS "launch wrapped in ssh" case near the top of this file.
printf '%-58s ' "launch wrapped in ssh, on MSYS: still the launch gate, not the transport one"
out=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" \
        "ssh twnia3 '$LAUNCH x --disable-optimization'" | PATH="$MSYSBIN:$PATH" bash "$H")
reason=$(python3 -c "import json,sys;print(json.load(sys.stdin).get('hookSpecificOutput',{}).get('permissionDecisionReason',''))" <<<"$out" 2>/dev/null)
case "$reason" in
  *"$LAUNCH"*) echo "ok" ;;
  *) echo "FAIL: reason lost the launch command <<$reason>>"; fails=$((fails+1)) ;;
esac
printf '%-58s ' "...and that reason does not carry the D3 wording"
case "$reason" in
  *"PITFALLS 16b"*) echo "FAIL: transport wording leaked into the launch ask"; fails=$((fails+1)) ;;
  *) echo ok ;;
esac

echo
echo "== D1: all four hooks' jq fail-closed message names the Windows install line =="
# Same no-jq PATH already built above (NOJQ_PATH), reused rather than a
# second shim directory - the point is these four files share one
# requirement, so a change to one line in one file that missed the others
# should turn exactly this loop red, in every file it missed.
#
# T1 changed what triggers the message for three of the four: guard_plugin_files.sh
# still refuses every call once CLAUDE_PLUGIN_ROOT is set and jq is broken (out
# of this card's scope - see hooks/guard_plugin_files.sh), so '{}' alone still
# reaches its message. The other three now only speak up for a payload that
# LOOKS like something they guard - '{}' matches none of their scoped
# patterns and would now exit silently, which is the correct new behaviour,
# not a case this loop should call a failure. So each gets a payload shaped
# for what it actually watches.
HOOKS_DIR="$(dirname "$H")"
# A subdirectory of the already-trapped $TMP, not a second mktemp with its own
# EXIT trap - a second `trap ... EXIT` here would silently REPLACE the one set
# earlier in this file (for $Z2TMP and $TMP itself), leaking both on exit.
GPR_TMP="$TMP/fake_plugin_root"; mkdir -p "$GPR_TMP"
D1_LAUNCH=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$LAUNCH x --disable-optimization")
D1_DELETE='{"tool_input":{"command":"rm -rf results/"}}'
D1_WRITE='{"tool_input":{"file_path":"/r/samplesheet.csv"}}'
declare -A D1_PAYLOAD=(
  [confirm_launch.sh]="$D1_LAUNCH"
  [confirm_cleanup.sh]="$D1_DELETE"
  [confirm_walkthrough.sh]="$D1_WRITE"
  # Must name the plugin root: without jq the guard now lets through any
  # call that does not (issue #15), so '{}' would never reach the message.
  [guard_plugin_files.sh]="{\"tool_input\":{\"file_path\":\"$GPR_TMP/hooks/x.sh\"}}"
)
for hf in confirm_launch.sh confirm_cleanup.sh confirm_walkthrough.sh guard_plugin_files.sh; do
  printf '%-58s ' "$hf: fail-closed message names winget"
  out=$(echo "${D1_PAYLOAD[$hf]}" | PATH="$NOJQ_PATH" CLAUDE_PLUGIN_ROOT="$GPR_TMP" bash "$HOOKS_DIR/$hf" 2>&1 1>/dev/null)
  if echo "$out" | grep -qF "winget install jqlang.jq"; then echo ok; else
    echo "FAIL: no Windows install line in $hf: <<$out>>"; fails=$((fails+1))
  fi
done

echo
echo "== T1: hooks.json's matcher reaches non-Bash execution tools too =="
HJ="$HOOKS_DIR/hooks.json"
CL_MATCHER=$(jq -r '
  .hooks.PreToolUse[]
  | select(.hooks[].command | test("confirm_launch\\.sh"))
  | .matcher
' "$HJ" 2>/dev/null | tr -d '\r' | paste -s -d '|' -)
for name in Bash PowerShell pwsh Terminal Exec "mcp__seqera__$(printf '\x6c\x61\x75\x6e\x63\x68')_pipeline" mcp__claude_ai_Seqera__run_workflow; do
  printf '%-58s ' "confirm_launch.sh's matcher covers tool_name '$name'"
  jq -en --arg m "$CL_MATCHER" --arg n "$name" '$n | test($m)' 2>/dev/null | grep -qx true \
    && echo ok || { echo FAIL; fails=$((fails+1)); }
done
printf '%-58s ' "...but not an unrelated read-only tool name like 'Read'"
jq -en --arg m "$CL_MATCHER" '"Read" | test($m)' 2>/dev/null | grep -qx true \
  && { echo "FAIL: matched Read"; fails=$((fails+1)); } || echo ok
# #29: MCP tools reach the launch gate only when they are Seqera's/Tower's;
# every other MCP call (search, GitHub, Gmail) must not pay for it, and the
# deletion guard - which scans raw payloads for words like "find" - must not
# see MCP calls at all, or it would pause ordinary searches.
printf '%-58s ' "#29 ...nor an unrelated MCP tool (mcp__github__search_code)"
jq -en --arg m "$CL_MATCHER" '"mcp__github__search_code" | test($m)' 2>/dev/null | grep -qx true \
  && { echo "FAIL: matched"; fails=$((fails+1)); } || echo ok
# #29: a PreToolUse hook that runs past its timeout is cancelled and the tool
# call PROCEEDS (code.claude.com/docs/en/hooks-guide, "timeout"). The deletion
# guard measured 4.4-4.8 s on a Windows laptop against a 5 s limit, so under
# load the gate vanished with nothing printed. Every safety gate gets >= 30 s.
for g in confirm_launch.sh confirm_cleanup.sh confirm_walkthrough.sh guard_plugin_files.sh; do
  printf '%-58s ' "#29 every $g entry has timeout >= 30s"
  low=$(jq -r --arg g "$g" '[.hooks.PreToolUse[].hooks[] | select(.command | endswith($g)) | .timeout // 600] | map(select(. < 30)) | length' "$HJ" 2>/dev/null | tr -d '\r')
  [ "$low" = 0 ] && echo ok || { echo "FAIL: $low entries under 30s"; fails=$((fails+1)); }
done
CC_MATCHER=$(jq -r '.hooks.PreToolUse[] | select(.hooks[].command | test("confirm_cleanup\\.sh")) | .matcher' "$HJ" 2>/dev/null | tr -d '\r' | paste -s -d '|' -)
printf '%-58s ' "#29 confirm_cleanup.sh does not see Seqera MCP calls"
jq -en --arg m "$CC_MATCHER" '"mcp__seqera__list_runs" | test($m)' 2>/dev/null | grep -qx true \
  && { echo "FAIL: matched"; fails=$((fails+1)); } || echo ok


# Identity and shared-process gate (2.15.0 Windows verification: the model
# swapped agent_connection to a shared lab credential's id and started an
# agent under it on the login node, asking nobody).
printf 'agent_connection: me-lgn-1\nworkspace_id: 42\n' > "$TMP/id_env.yaml"; chmod 600 "$TMP/id_env.yaml"
idg() { # idg <label> <expect ask|allow> <command>
  local j o got
  j=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$3")
  o=$(LAB_SETTINGS_FILE="$TMP/id_env.yaml" bash "$H" <<<"$j" 2>/dev/null)
  got=allow; grep -q '"permissionDecision": *"ask"' <<<"$o" && got=ask
  printf '%-58s ' "$1"
  [ "$got" = "$2" ] && echo ok || { echo "FAIL: expected $2, got $got"; fails=$((fails+1)); }
}
idg "changing an existing agent_connection asks"           ask   'bash scripts/settings.sh --set agent_connection nchc-lgn-20260902'
idg "...and the ask shows the old and new value"           ask   'bash scripts/settings.sh --set agent_connection other'
j=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' 'bash scripts/settings.sh --set agent_connection other')
o=$(LAB_SETTINGS_FILE="$TMP/id_env.yaml" bash "$H" <<<"$j" 2>/dev/null)
printf '%-58s ' "   (from: me-lgn-1 / to: other in the reason)"
grep -q 'from: me-lgn-1' <<<"$o" && grep -q 'to:   other' <<<"$o" && echo ok || { echo "FAIL <<$o>>"; fails=$((fails+1)); }
idg "setting it to the value it already has does not ask"  allow 'bash scripts/settings.sh --set agent_connection me-lgn-1'
idg "filling an empty identity key (first setup) does not" allow 'bash scripts/settings.sh --set compute_env ce-new'
idg "set_setting in a sourced shell is caught too"         ask   '. scripts/settings.sh && set_setting workspace_id 99'
idg "starting the agent asks"                              ask   'bash scripts/agent_ctl.sh start'
idg "...also when wrapped in on_site.sh"                   ask   'scripts/on_site.sh "bash scripts/agent_ctl.sh restart"'
idg "stopping the egress relay asks"                       ask   'bash scripts/egress_ctl.sh stop'
idg "agent status does not ask"                            allow 'scripts/on_site.sh "bash scripts/agent_ctl.sh status"'
idg "reading a setting does not ask"                       allow 'bash scripts/settings.sh agent_connection'

# Feature 002 (TC-007, TC-016): adding or removing a domain on this
# deployment's own relay allowlist moves a security boundary on the shared
# login node, so the harness asks - the model does not decide.
idg "egress_allow add asks"                                ask   'bash scripts/egress_allow.sh add x.org --reason r'
idg "egress_allow remove asks"                             ask   'bash scripts/egress_allow.sh remove x.org'
idg "egress_allow list does not ask"                       allow 'bash scripts/egress_allow.sh list'
idg "egress_allow domains does not ask"                    allow 'bash scripts/egress_allow.sh domains'
idg "...wrapped in on_site.sh it asks"                     ask   "scripts/on_site.sh 'bash scripts/egress_allow.sh add x.org --reason r'"
idg "...an absolute plugin path asks"                      ask   'bash /some/plugin/scripts/egress_allow.sh add x.org --reason r'
idg "...a ./ path asks"                                    ask   './scripts/egress_allow.sh add x.org --reason r'
idg "...inside a compound command asks"                    ask   'cd /tmp && bash scripts/egress_allow.sh remove x.org'
# Developer review of S3: quoting or indirection must not slip past. Quoting a
# domain is ordinary, and the quote-free column blanks a quoted word, so the
# gate asks on ANY run of the script unless the operation is plainly list or
# domains.
idg "...a quoted operation still asks"                     ask   'bash scripts/egress_allow.sh "add" x.org --reason r'
idg "...a single-quoted remove still asks"                 ask   "bash scripts/egress_allow.sh 'remove' x.org"
idg "...a quoted domain on remove still asks"              ask   'bash scripts/egress_allow.sh remove "x.org"'
idg "...an operation in a variable still asks"             ask   'op=add; bash scripts/egress_allow.sh $op x.org --reason r'
idg "...a bare run with no operation asks"                 ask   'bash scripts/egress_allow.sh'
idg "a quoted list does not ask"                           allow 'bash scripts/egress_allow.sh "list"'
idg "naming it inside echo's quotes does not ask"          allow 'echo "egress_allow.sh add x.org"'
idg "naming it in a commit message does not ask"           allow 'git commit -F msg.txt -m "docs: egress_allow.sh add x.org"'
j=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' 'bash scripts/egress_allow.sh add x.org --reason "needs a conda mirror"')
o=$(LAB_SETTINGS_FILE="$TMP/id_env.yaml" bash "$H" <<<"$j" 2>/dev/null)
printf '%-58s ' "   (ask names the domain, the reason, the boundary)"
grep -q 'x\.org' <<<"$o" && grep -q 'needs a conda mirror' <<<"$o" && grep -qi 'security boundary' <<<"$o" && grep -qi 'shared login node' <<<"$o" && echo ok || { echo "FAIL <<$o>>"; fails=$((fails+1)); }

# Independent acceptance of 002, H1: a quoted script path - the natural form
# for an installed plugin, "${CLAUDE_PLUGIN_ROOT}/scripts/..." - vanished from
# the quote-free column and nothing asked. Same for the relay start on main.
idg "...a quoted plugin-root path asks"                    ask   'bash "$CLAUDE_PLUGIN_ROOT/scripts/egress_allow.sh" add x.org --reason r'
idg "...a single-quoted path asks"                         ask   "bash 'scripts/egress_allow.sh' add x.org --reason r"
idg "...a redirect glued to the name asks"                 ask   'bash scripts/egress_allow.sh>/dev/null add x.org --reason r'
idg "...a 'list' planted in a prefix variable still asks"  ask   'X="egress_allow.sh list" bash scripts/egress_allow.sh add x.org --reason r'
idg "...a 'list' planted in the reason still asks"         ask   'bash scripts/egress_allow.sh add x.org --reason "egress_allow.sh list"'
idg "a quoted plugin-root path to list does not ask"       allow 'bash "$CLAUDE_PLUGIN_ROOT/scripts/egress_allow.sh" list'
idg "a relay start through a quoted path asks"             ask   'bash "${CLAUDE_PLUGIN_ROOT}/scripts/egress_ctl.sh" start'
idg "...and through on_site --script with a quoted path"   ask   'scripts/on_site.sh --script "${CLAUDE_PLUGIN_ROOT}/scripts/egress_ctl.sh" start'
idg "a quoted relay verb still asks (re-verify M-B)"       ask   'scripts/on_site.sh --script scripts/egress_ctl.sh "start"'
idg "a single-quoted stop still asks"                      ask   "bash scripts/egress_ctl.sh 'stop'"
idg "relay status stays quiet"                             allow 'bash scripts/egress_ctl.sh status'

# Independent acceptance of 002, H2: the allowlist file can be written without
# egress_allow.sh (an editor, a redirect). A domain only takes effect when the
# relay (re)starts, and that asks - so that ask must SHOW what this deployment
# will carry, or the user approves a restart blind.
mkdir -p "$TMP/ea"; printf 'agent_connection: me-lgn-1\n' > "$TMP/ea/env.yaml"; chmod 600 "$TMP/ea/env.yaml"
printf 'planted.example.org\n' > "$TMP/ea/egress_allow.tsv"
for verb in start restart; do
    j=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "scripts/on_site.sh --script scripts/egress_ctl.sh $verb")
    o=$(SEQERA_TOKEN_FILE= LAB_SETTINGS_FILE="$TMP/ea/env.yaml" bash "$H" <<<"$j" 2>/dev/null)
    printf '%-58s ' "relay $verb ask shows the extra domains it will carry"
    grep -q 'planted\.example\.org' <<<"$o" && echo ok || { echo "FAIL <<$o>>"; fails=$((fails+1)); }
done
rm -f "$TMP/ea/egress_allow.tsv"
o=$(SEQERA_TOKEN_FILE= LAB_SETTINGS_FILE="$TMP/ea/env.yaml" bash "$H" <<<"$j" 2>/dev/null)
printf '%-58s ' "relay restart ask says when it carries none"
grep -qi 'no extra domains' <<<"$o" && echo ok || { echo "FAIL <<$o>>"; fails=$((fails+1)); }

echo
echo "== #35: launch shapes the splitter did not read outside a nested shell =="
t "flock /tmp/l -c '$SB job.sh'"                       gate "#35 flock -c sbatch (no nested shell)"
t "su - lab -c '$SB job.sh'"                           gate "#35 su - lab -c sbatch"
t "su lab -c \"$NFRUN nf-core/ampliseq\""              gate "#35 su -c nextflow run"
t "tmux new -d '$NFRUN nf-core/ampliseq -resume'"      gate "#35 tmux new -d nextflow run"
t "tmux new-session -d -s a '$SB j.sh'"                gate "#35 tmux new-session sbatch"
t "tmux send-keys -t a '$LAUNCH x' Enter"              gate "#35 tmux send-keys tw launch"
t "screen -X stuff '$SB j.sh'"                         gate "#35 screen -X stuff sbatch"
t "flock /tmp/l -c 'ls'"                               pass "#35 control: flock -c ls"
t "su lab -c 'echo hi'"                                pass "#35 control: su -c echo"
t "tmux new -d 'htop'"                                 pass "#35 control: tmux new htop"
t "tmux ls"                                            pass "#35 control: tmux ls"
t "echo '$LAUNCH x' | sudo -u lab bash"                gate "#35 piped into sudo -u x bash"
t "echo '$SB x.sh' | srun bash"                        gate "#35 piped into srun bash"
t "echo '$SB x.sh' | srun --pty bash"                  gate "#35 piped into srun --pty bash"
t "echo '$SB x.sh' | sudo -E bash -s"                  gate "#35 piped into sudo -E bash -s"
t "echo '$SB x.sh' | grep bash"                        pass "#35 control: piped into grep bash"
t "echo '$SB x.sh' | sudo -u lab tee out.txt"          pass "#35 control: piped into sudo tee"
t "$(printf 'cat <<%s | srun bash\n%s x.sh\nEOF\n' "'EOF'" "$SB")" gate "#35 here-doc piped into srun bash"
t "$(printf 'cat <<%s | sudo -u lab bash\n%s x\nEOF\n' "'EOF'" "$LAUNCH")" gate "#35 here-doc piped into sudo -u bash"
t "Start-Process nextflow -ArgumentList 'run x'"        gate "#35 PowerShell Start-Process nextflow run"
t "Start-Process -FilePath nextflow -ArgumentList 'run','x'" gate "#35 Start-Process -FilePath, comma list"
t "Start-Process $SB -ArgumentList 'x.sh'"             gate "#35 control: Start-Process sbatch (already gated)"
t "Start-Process tw -ArgumentList 'launch','x'"        gate "#35 Start-Process tw launch"
t "Start-Process notepad -ArgumentList 'x.txt'"        pass "#35 control: Start-Process notepad"
t "Start-Process nextflow -ArgumentList '-version'"    pass "#35 control: Start-Process nextflow -version"
t "a=($LAUNCH x); \"\${a[@]}\""                        gate "#35 control: command held in an array (already gated)"
t "files=(a.txt b.txt); ls \"\${files[@]}\""           pass "#35 control: an array of file names"


echo
echo "== #45: egress_allow gate obfuscations, writes to its file, relay env prefix, false alarms =="
# M1: spellings of the script's name that did not contain the name as written
idg "#45 a glob for the extension"                         ask   'bash scripts/egress_allow.* add x.org --reason r'
idg "#45 a ? in the name"                                  ask   'bash scripts/egress_allo?.sh add x.org --reason r'
idg "#45 a backslash in the name"                          ask   'bash scripts/egress_allow\.sh add x.org --reason r'
idg "#45 a bracket in the name"                            ask   'bash scripts/egress_allow.s[h] add x.org --reason r'
idg "#45 a * in the stem"                                  ask   'bash scripts/e*_allow.sh remove x.org'
idg "#45 an empty-string splice in the name"               ask   'bash scripts/egress_""allow.sh add x.org --reason r'
idg "#45 a quote splice in the name"                       ask   "bash scripts/egress_al'low'.sh add x.org --reason r"
idg "#45 the name held in a variable set earlier"          ask   'a=egress_allow; bash scripts/$a.sh add x.org --reason r'
idg "#45 ...with the operation in a variable too"          ask   'a=egress_allow; b=add; bash scripts/$a.sh $b x.org --reason r'
idg "#45 a variable that is not set in the command"        ask   'bash "scripts/$a.sh" add x.org --reason r'
idg "#45 run directly, with a ? in the name"               ask   'scripts/egress_allo?.sh add x.org --reason r'
idg "#45 control: a globbed name with list does not ask"   allow 'bash scripts/egress_allo?.sh list'
idg "#45 control: ls of the scripts does not ask"          allow 'ls scripts/egress_*'
idg "#45 control: git add with a glob does not ask"        allow 'git add -A scripts/*.sh'
idg "#45 control: another script with add does not ask"    allow 'bash scripts/other.sh add x.org'
idg "#45 control: a variable script with list does not"    allow 'bash scripts/$a.sh list'
idg "#45 control: echoing the glob does not ask"           allow 'echo bash scripts/egress_allo?.sh add x.org'
# M2: direct writes to the file the script manages
idg "#45 a >> redirect into egress_allow.tsv"              ask   'echo x.org >> /home/u/cfg/egress_allow.tsv'
idg "#45 a > redirect into it"                             ask   'echo x.org > /home/u/cfg/egress_allow.tsv'
idg "#45 a quoted redirect target"                         ask   'echo x.org >> "/home/u/cfg/egress_allow.tsv"'
idg "#45 tee -a into it"                                   ask   "printf 'x.org\n' | tee -a cfg/egress_allow.tsv"
idg "#45 cp over it"                                       ask   'cp new.tsv cfg/egress_allow.tsv'
idg "#45 sed -i on it"                                     ask   "sed -i 's/a/b/' cfg/egress_allow.tsv"
idg "#45 a glob that names it"                             ask   'echo x.org >> cfg/egress_allo?.tsv'
idg "#45 an editor opened on it"                           ask   'vim cfg/egress_allow.tsv'
idg "#45 control: cat of it does not ask"                  allow 'cat cfg/egress_allow.tsv'
idg "#45 control: grep of it does not ask"                 allow 'grep -n x.org cfg/egress_allow.tsv'
idg "#45 control: ls -l of it does not ask"                allow 'ls -l cfg/egress_allow.tsv'
idg "#45 control: wc -l of it does not ask"                allow 'wc -l cfg/egress_allow.tsv'
idg "#45 control: diff against it does not ask"            allow 'diff a.tsv cfg/egress_allow.tsv'
idg "#45 control: its name in an echo's quotes, written elsewhere" allow 'echo "see egress_allow.tsv" >> notes.md'
idw() { # idw <label> <expect ask|allow> <tool> <file_path>  - a Write/Edit tool call
  local j o got
  j=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":sys.argv[1],"tool_input":{"file_path":sys.argv[2],"content":"x"}}))' "$3" "$4")
  o=$(LAB_SETTINGS_FILE="$TMP/id_env.yaml" bash "$H" <<<"$j" 2>/dev/null)
  got=allow; grep -q '"permissionDecision": *"ask"' <<<"$o" && got=ask
  printf '%-58s ' "$1"
  [ "$got" = "$2" ] && echo ok || { echo "FAIL: expected $2, got $got"; fails=$((fails+1)); }
}
idw "#45 Write to egress_allow.tsv asks"                   ask   Write '/home/u/cfg/egress_allow.tsv'
idw "#45 Edit of egress_allow.tsv asks"                    ask   Edit  '/home/u/cfg/egress_allow.tsv'
idw "#45 a Windows path asks"                              ask   Write 'C:\Users\u\cfg\egress_allow.tsv'
idw "#45 control: Write to another file does not ask"      allow Write '/home/u/cfg/notes.md'
idw "#45 control: a file that only starts alike"           allow Write '/home/u/cfg/egress_allow.tsv.bak'
printf '%-58s ' "#45 hooks.json sends Write/Edit calls to confirm_launch.sh"
CL_MATCHER=$(jq -r '.hooks.PreToolUse[] | select(.hooks[].command | test("confirm_launch\\.sh")) | .matcher' "$HOOKS_DIR/hooks.json" 2>/dev/null | tr -d '\r' | paste -s -d '|' -)
jq -en --arg m "$CL_MATCHER" '"Write" | test("^(" + $m + ")$")' 2>/dev/null | grep -qx true && echo ok || { echo "FAIL: matcher <<$CL_MATCHER>>"; fails=$((fails+1)); }
printf '%-58s ' "#45 control: ...and a plain Read still does not"
jq -en --arg m "$CL_MATCHER" '"Read" | test("^(" + $m + ")$")' 2>/dev/null | grep -qx true && { echo "FAIL"; fails=$((fails+1)); } || echo ok
# M3: an environment prefix on a direct relay start
envp() { # envp <label> <expect has|lacks> <command>: does the ask say the command overrides the list?
  local j o got
  j=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]}}))' "$3")
  o=$(LAB_SETTINGS_FILE="$TMP/id_env.yaml" bash "$H" <<<"$j" 2>/dev/null)
  got=lacks; grep -qF "overrides this deployment's list" <<<"$o" && got=has
  printf '%-58s ' "$1"
  [ "$got" = "$2" ] && echo ok || { echo "FAIL: expected $2, got $got <<${o:0:80}>>"; fails=$((fails+1)); }
}
envp "#45 an env prefix on a relay start is named in the ask"  has   'NF_RELAY_EXTRA_DOMAINS=evil.org bash scripts/egress_ctl.sh start'
envp "#45 ...through env"                                      has   'env NF_RELAY_EXTRA_DOMAINS=evil.org bash scripts/egress_ctl.sh restart'
envp "#45 ...through export"                                   has   'export NF_RELAY_EXTRA_DOMAINS=evil.org; bash scripts/egress_ctl.sh start'
envp "#45 control: a plain relay start does not say it"        lacks 'bash scripts/egress_ctl.sh start'
# LOW: false alarms on reading the script, and sourcing it with no operation
idg "#45 cat of the script does not ask"          allow 'cat scripts/egress_allow.sh'
idg "#45 less of the script does not ask"                  allow 'less scripts/egress_allow.sh'
idg "#45 grep -n add on the script does not ask"           allow 'grep -n add scripts/egress_allow.sh'
idg "#45 bash -n on the script does not ask"               allow 'bash -n scripts/egress_allow.sh'
idg "#45 git diff -- the script does not ask"              allow 'git diff -- scripts/egress_allow.sh'
idg "#45 sourcing it with no operation does not ask"       allow 'source "scripts/egress_allow.sh"'
idg "#45 control: sourcing it with add still asks"         ask   'source scripts/egress_allow.sh add x.org --reason r'
idg "#45 control: a bare run with no operation still asks" ask   'bash scripts/egress_allow.sh'
idg "#45 control: add after a reader segment still asks"   ask   'cat scripts/egress_allow.sh; bash scripts/egress_allow.sh add x.org --reason r'

[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
