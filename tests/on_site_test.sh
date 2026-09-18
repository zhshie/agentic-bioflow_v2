#!/bin/bash
# Tests for scripts/on_site.sh, the only sanctioned way to run something on the
# site. It has to be right for three site kinds at once, and two of them - a
# cloud compute environment with nothing to reach, and an ssh site whose master
# connection has died - are states no amount of local testing would produce by
# accident.
#
# Everything below runs through ON_SITE_DRY_RUN=1, which prints where a command
# would run and what it would be, without running it. That is the whole point of
# the seam: these tests need no ssh host, no network, and no site.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/on_site.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }

t() { # t <label> <expect-rc> <expect-substring> -- <args...>
  local label="$1" want_rc="$2" want="$3"; shift 4
  printf '%-56s ' "$label"
  local out rc
  out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_DRY_RUN=1 \
        ON_SITE_SSH_BIN="$TMP/fake-ssh" bash "$S" "$@" 2>&1); rc=$?
  if [ "$rc" != "$want_rc" ]; then
    echo "FAIL: rc $rc, wanted $want_rc  <<$out>>"; fails=$((fails+1)); return
  fi
  if [ -n "$want" ] && ! grep -qF -- "$want" <<<"$out"; then
    echo "FAIL: output lacks '$want'  <<$out>>"; fails=$((fails+1)); return
  fi
  echo "ok"
}

# A stub ssh whose exit status the tests control, so "is the master up" is a
# state we can set rather than one we have to arrange for real.
mkfake() { printf '#!/bin/bash\nexit %s\n' "$1" > "$TMP/fake-ssh"; chmod +x "$TMP/fake-ssh"; }
mkfake 0

settings 'reach: local'
t "local: says where and what"            0 "local	true"            -- true
t "local: joins its arguments"            0 "local	echo hi there"    -- echo hi there

settings 'reach: ssh' 'site_host: me@example.org'
t "ssh: names the host"                   0 "ssh me@example.org	true" -- true
t "ssh: script mode ships settings.sh"    0 "script egress_ctl.sh"   -- --script scripts/egress_ctl.sh status

# T9: scripts/site_report.sh bundles agent/resources/provenance/inventory into
# one call, so a caller that used to make two or three `on_site.sh --script`
# round trips (commands/downstream.md's step 1 + step 2's >500MB branch) now
# makes one. It travels through --script exactly like any other script here -
# nothing special about how on_site.sh routes it.
t "ssh: site_report.sh is a valid --script target" 0 "script site_report.sh" \
  -- --script scripts/site_report.sh /some/results --run-id abc123

# A cloud compute environment has no login node. "Nothing to reach" is a normal
# answer for the site, but a caller that asked anyway has a bug, so say so
# rather than silently running the command on the wrong machine.
settings 'reach: none'
t "none: refuses rather than running here" 2 "nothing to reach"      -- true

settings 'reach: ssh'
t "ssh without site_host names the key"    2 "site_host"             -- true

settings 'reach: banana' 'site_host: me@example.org'
t "an unknown reach value is an error"     2 "banana"                -- true

settings 'workspace_id: 1'
t "no reach key defaults to local"         0 "local	true"            -- true

# The master connection carries the one-time code the user typed. Claude cannot
# open it - the code is on their phone - so the only useful thing to do when it
# is gone is print the exact line for them to paste.
settings 'reach: ssh' 'site_host: me@example.org'
mkfake 0
t "check-reach passes when the master is up" 0 ""                    -- --check-reach
mkfake 255
t "check-reach fails when it is gone"      2 "ControlMaster=auto"    -- --check-reach
t "and names the host to paste it against" 2 "me@example.org"        -- --check-reach

# N9-1/N9-3: on_site.sh with no dry-run flag, so the no_master() path in
# command mode actually runs (dry run never calls master_is_up at all - see
# the parallel-slot tests for that seam). A lab agent (docs/LAB_AGENTS.md,
# tier H2) has nobody to answer an OTP prompt, so this exit must be
# greppable without parsing prose.
no_master_run() { LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" bash "$S" true 2>&1; }
nmr() { # nmr <label> <want-substring>
  printf '%-56s ' "$1"
  local out; out=$(no_master_run)
  grep -qF -- "$2" <<<"$out" && echo ok || { echo "FAIL: lacks '$2'  <<$out>>"; fails=$((fails+1)); }
}
nmr "N9-1: no-master carries the machine-readable line" \
    "on_site: needs-human reason=no-master host=me@example.org"
nmr "N9-1: no-master keeps the existing human message too" \
    "no ssh master connection to me@example.org"
nmr "N9-3: no-master's command carries ServerAliveInterval=60" \
    "ServerAliveInterval=60"

# reach=local must never consult ssh at all: a site the deployment already runs
# on has no master connection, and demanding one would break the site that works
# today.
settings 'reach: local'
mkfake 255
t "local ignores the ssh master entirely"  0 "local	true"            -- true

# --- a master that is up but cannot open another session ---------------------
# PITFALLS 16e: this site's sshd caps sessions per TCP connection, and the cap
# is reached by ordinary use - a background watch polling every 90s plus a long
# diagnostic session. The next session-open does not fail, it *hangs*, forever.
# `ssh -O check` keeps answering because it is a control-plane ping, which is
# exactly what made preflight say OK while the next command sat there. So the
# check has to open a real session, and every call needs a clock on it.
mkhang() {   # -O check succeeds; anything that opens a session hangs
  printf '#!/bin/bash\nfor a in "$@"; do [ "$a" = check ] && exit 0; done\nsleep 30\n' \
    > "$TMP/fake-ssh"; chmod +x "$TMP/fake-ssh"
}

settings 'reach: ssh' 'site_host: me@example.org'
mkhang
tt() { # like t(), but without the dry run - these cases must really execute
  local label="$1" want_rc="$2" want="$3"; shift 4
  printf '%-56s ' "$label"
  local out rc
  out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" \
        ON_SITE_TIMEOUT=1 bash "$S" "$@" 2>&1); rc=$?
  if [ "$rc" != "$want_rc" ]; then echo "FAIL: rc $rc wanted $want_rc <<$out>>"; fails=$((fails+1)); return; fi
  if [ -n "$want" ] && ! grep -qF -- "$want" <<<"$out"; then echo "FAIL: lacks '$want' <<$out>>"; fails=$((fails+1)); return; fi
  echo ok
}
tt "check-reach opens a real session, not just -O check" 2 "session"      -- --check-reach
tt "and says how to recover the master"                  2 "ssh -O exit"  -- --check-reach
tt "a hung command surfaces as an error, not a wait"     2 "session"      -- true

# The recovery line has to be complete enough to paste: a ControlPath the user
# has to reconstruct is a line they will get wrong.
tt "and the recovery line carries the ControlPath"       2 "ControlPath"  -- true

# N9-1: the same machine-readable trailer for the other "needs a human" exit.
tt "N9-1: sessions-exhausted carries the machine-readable line" 2 \
   "on_site: needs-human reason=sessions-exhausted host=me@example.org" -- true

# ControlPersist detaches the master into the background once it has
# authenticated. Telling the user to keep a terminal open is false, and it
# taught one to believe closing it had broken something.
settings 'reach: ssh' 'site_host: me@example.org'
mkfake 255
printf '%-56s ' "no-master text does not demand an open terminal"
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" bash "$S" true 2>&1)
if grep -qiF "leave that terminal open" <<<"$out"; then
  echo "FAIL: still says to leave the terminal open"; fails=$((fails+1))
else echo ok; fi

# --- what actually travels in script mode ------------------------------------
# The named script alone is never enough: site scripts source settings.sh and
# require_python.sh, and egress_ctl.sh execs nf_relay.py by path. That last one
# used to be shipped by a hand-written special case in on_site.sh - a list of
# one script's dependencies, kept in a different file from the dependency, with
# nothing to remind the next author to add theirs. This test is what would have
# caught it, because it reads the payload rather than the intention. The
# presence of why_pending.sh, which egress_ctl.sh has no relationship to at
# all, is the assertion that nothing is being cherry-picked.
settings 'reach: ssh' 'site_host: me@example.org'
PAYLOAD="$TMP/payload.tgz"; export PAYLOAD
cat > "$TMP/fake-ssh" <<'EOF'
#!/bin/bash
for a in "$@"; do [ "$a" = check ] && exit 0; done
cat > "$PAYLOAD"
EOF
chmod +x "$TMP/fake-ssh"
LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" \
  bash "$S" --script scripts/egress_ctl.sh status >/dev/null 2>&1
listing=$(tar -tzf "$PAYLOAD" 2>/dev/null)

for want in scripts/settings.sh scripts/require_python.sh scripts/egress_ctl.sh \
            scripts/nf_relay.py scripts/why_pending.sh configs/; do
  printf '%-56s ' "payload carries $want"
  if grep -q "^$want" <<<"$listing"; then echo ok
  else echo "FAIL: not in the payload"; fails=$((fails+1)); fi
done

# Compiled Python is build output; .gitignore says so, and a site that unpacks
# a stale .pyc next to a newer .py gets to run the old one.
printf '%-56s ' "payload leaves build output behind"
if grep -q '__pycache__\|\.pyc$' <<<"$listing"; then
  echo "FAIL: build output is travelling"; fails=$((fails+1))
else echo ok; fi

echo

# ---------------------------------------------------------------------------
# The wrong shell - now a narrower case than it used to be.
#
# Git Bash used to be refused unconditionally, and 16g changed why that stood:
# its own ssh cannot hold a master (16b), but calling WSL's ssh from it does
# work - measured, 0.55 s, no 2FA prompt (scripts/utils/wsl_ssh.sh is that
# call). So this version routes through the bridge when one is there
# (tests/wsl_bridge_test.sh covers that path) and refuses only when it is
# not: no `wsl.exe` on PATH, which is exactly this section's fixture - a fake
# `uname` alone, deliberately with no fake `wsl.exe` beside it. What remains
# on top, once WSL exists, is the rest of a Linux userland: python3 is a
# Store stub (20c), jq is absent by default, and the suite does not run here.
#
# The refusal lives in this script rather than in a PreToolUse hook on purpose:
# a hook would have to decide from a command string whether it reaches the
# site, and it would wall off a reach:none deployment that needs no ssh at all.
# Here the subject is not guessed.
UB="$TMP/msysbin"; mkdir -p "$UB"
printf '#!/bin/sh\necho MINGW64_NT-10.0-22631\n' > "$UB/uname"; chmod +x "$UB/uname"

msys() { # msys <expect-rc> -- <args...>
  local want="$1"; shift 2
  LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" \
    PATH="$UB:$PATH" bash "$S" "$@" 2>&1
}
mt() { # mt <label> <expect-rc> <expect-substring> -- <args...>
  local label="$1" want_rc="$2" want="$3"; shift 4
  printf '%-56s ' "$label"
  local out rc; out=$(msys "$want_rc" -- "$@"); rc=$?
  if [ "$rc" != "$want_rc" ]; then
    echo "FAIL: rc $rc, wanted $want_rc  <<$out>>"; fails=$((fails+1)); return; fi
  if [ -n "$want" ] && ! grep -qF -- "$want" <<<"$out"; then
    echo "FAIL: output lacks '$want'  <<$out>>"; fails=$((fails+1)); return; fi
  echo ok
}

settings 'reach: ssh' 'site_host: u@h'
mkfake 0                       # the master answers -O check, as it really does
mt "MSYS + reach:ssh, no bridge, is refused"   2 "WSL is not available here" -- true
mt "and names the shell's own ssh limit"      2 "PITFALLS 16b"             -- true
mt "and that the bridge itself was measured"  2 "PITFALLS 16g"             -- true
mt "and says the bridge exists, just unreached" 2 "wsl_ssh.sh"             -- true
mt "and gives the move, not just the fault"   2 "wsl --install"            -- true
mt "and keeps the member in the window they have" 2 "THIS window"          -- true
mt "and names the .wslconfig fix first"       2 "vsyscall=emulate"         -- true
mt "and offers the off-design report"         2 "report.sh"                -- true

# 2.13 removed a reason rather than working around it: set_setting() is awk
# now, so python3's Store stub (20c) no longer blocks anything here, and a
# refusal that still named it would send the member off installing Python to
# fix something that is not broken. This is the assertion that stops it coming
# back - the same shape as the "not the folder" one below, and for the same
# reason: a stale reason in a refusal is worse than no reason, because it is
# actionable and wrong.
printf '%-56s ' "and no longer blames python3, which was fixed"
out=$(msys 2 -- true)
grep -qF "python3" <<<"$out" \
  && { echo "FAIL: still names python3 <<$out>>"; fails=$((fails+1)); } || echo ok

# The mistake 2.12 named and 2.13 finished correcting: the refusal used to
# read as though the project folder had to move into WSL. The first assertion
# is 2.12's, unchanged - it is the one invariant 11 cites.
mt "and says what is refused is the shell, not the folder" 2 "not the folder" -- true

# The other two changed subject, because what they described stopped being
# true. 2.12 pinned a pasteable `cd /mnt/c/...` - the way back to your own
# folder AFTER moving into WSL. There is no move now, so offering that line
# would put the idea of working inside WSL back into the one message whose
# job is to remove it. What replaces it is the stronger statement: nothing
# here sends the member anywhere.
printf '%-56s ' "and never tells the member to work somewhere else"
out=$(msys 2 -- true)
if grep -qE 'cd /mnt/c|from a WSL shell|Start Claude Code' <<<"$out"; then
  echo "FAIL: still relocates the member <<$out>>"; fails=$((fails+1))
else
  echo ok
fi

# And 2.12's "settings and token stay off the Windows filesystem" was a
# prediction this release cannot make any more: the scripts run in MSYS now,
# so the settings file lands in the Windows home unless the mode-600 read-back
# refuses that filesystem. Stating a location here would be guessing at
# something settings.sh measures - so the refusal points at the measurement
# instead, and this pins that it does.
mt "and points at the check, not a guessed location"   2 "reads the result back" -- true

# 16g measured the opposite of what this refusal used to assert. It may say
# this shell is unsupported; it may not say the site is out of reach from here.
printf '%-56s ' "it no longer claims the site is unreachable"
out=$(msys 2 -- true); grep -qF "cannot hold an ssh master connection" <<<"$out" \
  && { echo "FAIL: repeats the retracted claim"; fails=$((fails+1)); } || echo ok

# A master that answers -O check is exactly the state 16b describes, so a
# refusal that only fires when the master looks down would never fire at all.
printf '%-56s ' "it fires even though the master answers -O check"
out=$(msys 2 -- true); grep -qF "no ssh master connection" <<<"$out" \
  && { echo "FAIL: reported a missing master instead"; fails=$((fails+1)); } || echo ok

# Three things it must NOT touch.
settings 'reach: local'
mt "reach:local under MSYS is none of its business" 0 "" -- true
settings 'reach: none'
mt "reach:none under MSYS needs no ssh at all"      2 "nothing to reach" -- true
printf '%-56s ' "and is not told about shells it does not use"
out=$(msys 2 -- true); grep -qF "Git Bash" <<<"$out" \
  && { echo "FAIL: walled off a cloud deployment"; fails=$((fails+1)); } || echo ok
settings 'reach: ssh' 'site_host: u@h'
printf '%-56s ' "a dry run still answers under MSYS"
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_DRY_RUN=1 \
      ON_SITE_SSH_BIN="$TMP/fake-ssh" PATH="$UB:$PATH" bash "$S" true 2>&1)
grep -qF "ssh u@h" <<<"$out" && echo ok \
  || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }

# And on this machine, which is Linux, it must stay silent.
printf '%-56s ' "on Linux nothing about shells is printed"
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" bash "$S" true 2>&1)
grep -qF "Git Bash" <<<"$out" \
  && { echo "FAIL: fired on Linux <<$out>>"; fails=$((fails+1)); } || echo ok

# --- N9-2: local/none never touch the slot machinery at all ------------------
# A control path under $TMP, so this never looks anywhere near a real ~/.ssh.
CPTEST="$TMP/cm-test"
settings 'reach: local' "ssh_control_path: $CPTEST"
mkfake 0
LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" \
  bash "$S" true >/dev/null 2>&1
printf '%-56s ' "N9-2: local mode creates no slots directory"
[ -d "${CPTEST}.slots" ] \
  && { echo "FAIL: ${CPTEST}.slots exists"; fails=$((fails+1)); } || echo ok

rm -rf "${CPTEST}.slots"
settings 'reach: none' "ssh_control_path: $CPTEST"
LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" \
  bash "$S" --check-reach >/dev/null 2>&1
printf '%-56s ' "N9-2: reach:none creates no slots directory either"
[ -d "${CPTEST}.slots" ] \
  && { echo "FAIL: ${CPTEST}.slots exists"; fails=$((fails+1)); } || echo ok

echo
echo "See tests/on_site_parallel_test.sh for N9-2's concurrency, staleness," \
     "timeout and release-on-signal coverage."

[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
