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
# The wrong shell.
#
# Git Bash cannot hold a master connection at all (PITFALLS 16b), so under it
# every call here is a guaranteed failure that costs a one-time code from the
# user's phone. The refusal lives in this script rather than in a PreToolUse
# hook on purpose: a hook would have to decide from a command string whether it
# reaches the site, and it would wall off a reach:none deployment that needs no
# ssh at all. Here the subject is not guessed.
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
mt "MSYS + reach:ssh is refused outright"     2 "cannot hold an ssh master" -- true
mt "and the refusal says why, measured"      2 "PITFALLS 16b"              -- true
mt "and gives the move, not just the fault"  2 "WSL"                       -- true
mt "and warns about the Windows exe shortcut" 2 "claude.exe"               -- true
mt "and names the .wslconfig fix first"      2 "vsyscall=emulate"          -- true

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

[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
