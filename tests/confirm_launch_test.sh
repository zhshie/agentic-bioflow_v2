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
' "$HJ" 2>/dev/null)
for name in Bash PowerShell pwsh Terminal Exec; do
  printf '%-58s ' "confirm_launch.sh's matcher covers tool_name '$name'"
  jq -en --arg m "$CL_MATCHER" --arg n "$name" '$n | test($m)' 2>/dev/null | grep -qx true \
    && echo ok || { echo FAIL; fails=$((fails+1)); }
done
printf '%-58s ' "...but not an unrelated read-only tool name like 'Read'"
jq -en --arg m "$CL_MATCHER" '"Read" | test($m)' 2>/dev/null | grep -qx true \
  && { echo "FAIL: matched Read"; fails=$((fails+1)); } || echo ok

[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
