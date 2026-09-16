#!/bin/bash
# Tests for the WSL bridge: scripts/utils/wsl_ssh.sh and the branch in
# scripts/on_site.sh that reaches for it.
#
# PITFALLS 16b measured that Git Bash's own ssh cannot open a session over a
# master - MSYS emulates Unix sockets and does not implement the descriptor
# passing a session needs. PITFALLS 16g measured the way around it: calling
# WSL's ssh FROM Git Bash works, 0.55 s, no 2FA, binary stdin and exit codes
# intact. This file is what pins that the code actually takes that path -
# not just that the path was measured once by hand.
#
# A fake `uname` (MINGW64_NT-10.0) stands in for Git Bash; a fake `wsl.exe`
# appends its own argv, one line per argument, to a log file, so an assertion
# can check exactly what crossed the process boundary rather than trusting
# that it did.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
S="$ROOT/scripts/on_site.sh"
SHIM="$ROOT/scripts/utils/wsl_ssh.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

settings() { printf '%s\n' "$@" > "$TMP/env.yaml"; }

t() { # t <label> <got> <want-substring>
  printf '%-58s ' "$1"
  if grep -qF -- "$3" <<<"$2"; then echo ok
  else echo "FAIL: lacks '$3'  <<$2>>"; fails=$((fails+1)); fi
}
tnot() { # tnot <label> <got> <unwanted-substring>
  printf '%-58s ' "$1"
  if grep -qF -- "$3" <<<"$2"; then echo "FAIL: contains '$3'  <<$2>>"; fails=$((fails+1))
  else echo ok; fi
}

# --- fixtures -----------------------------------------------------------
# A "Git Bash" PATH: a fake uname, and (unless a test removes it) a fake
# wsl.exe that logs its argv and always succeeds - a stand-in for a real WSL
# whose master is already up, so tests here never depend on one.
UB="$TMP/msysbin"; mkdir -p "$UB"
printf '#!/bin/sh\necho MINGW64_NT-10.0-22631\n' > "$UB/uname"; chmod +x "$UB/uname"

WSL_LOG="$TMP/wsl.log"
mkwsl() {
  cat > "$UB/wsl.exe" <<EOF
#!/bin/bash
{ echo '--CALL--'; for a in "\$@"; do printf '%s\n' "\$a"; done; } >> "$WSL_LOG"
exit 0
EOF
  chmod +x "$UB/wsl.exe"
}
rmwsl() { rm -f "$UB/wsl.exe"; }

echo "-- (b) the shim itself: every argument crosses to wsl.exe verbatim --"
: > "$WSL_LOG"; mkwsl
PATH="$UB:$PATH" "$SHIM" \
  -o 'ControlPath=~/.ssh/cm-%r-%h-%p' -o 'ServerAliveInterval=60' \
  'me@example.org' 'an arg with spaces' >/dev/null 2>&1
log=$(cat "$WSL_LOG")
t "wsl.exe is called with -e ssh first"          "$log" "$(printf -- '-e\nssh')"
t "the ControlPath option survives as one token" "$log" 'ControlPath=~/.ssh/cm-%r-%h-%p'
t "an argument containing spaces is not split"   "$log" 'an arg with spaces'
t "the host argument is untouched"               "$log" 'me@example.org'
printf '%-58s ' "spaces do not become two log lines"
awk '/^an arg with spaces$/{n++} END{exit !(n==1)}' "$WSL_LOG" \
  && echo ok || { echo "FAIL: not exactly one line"; fails=$((fails+1)); }

echo
echo "-- (a) on_site.sh + MSYS + reach:ssh + a working bridge: \$SSH is the shim --"
: > "$WSL_LOG"; mkwsl
settings 'reach: ssh' 'site_host: me@example.org'
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" PATH="$UB:$PATH" bash "$S" --check-reach 2>&1); rc=$?
printf '%-58s ' "--check-reach succeeds through the bridge"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc=$rc <<$out>>"; fails=$((fails+1)); }
printf '%-58s ' "wsl.exe was actually invoked (proves \$SSH is not plain ssh)"
[ -s "$WSL_LOG" ] && echo ok || { echo "FAIL: wsl.exe log is empty"; fails=$((fails+1)); }
t "the call carries the control-plane check"     "$(cat "$WSL_LOG")" 'check'
t "and names the configured host"                "$(cat "$WSL_LOG")" 'me@example.org'
t "and the ControlPath default is WSL's own unexpanded tilde form, not MSYS's \$HOME" \
  "$(cat "$WSL_LOG")" 'ControlPath=~/.ssh/cm-%r-%h-%p'

# Command mode, not --check-reach: this is the branch that actually calls
# wrong_shell (on_site.sh, `if [ "$REACH" = ssh ]; then case ... wrong_shell`)
# - --check-reach above exits before ever reaching it, so a working bridge
# proven there alone would not prove this gate lets it through too.
: > "$WSL_LOG"; mkwsl
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" PATH="$UB:$PATH" bash "$S" true 2>&1); rc=$?
printf '%-58s ' "command mode also succeeds through the bridge (not just --check-reach)"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc=$rc <<$out>>"; fails=$((fails+1)); }
tnot "and does not fire wrong_shell despite being MSYS" "$out" "WSL is not available"
t "and the real command reaches wsl.exe"                "$(cat "$WSL_LOG")" 'true'

echo
echo "-- (c) R1: the rsync -e string survives the round trip through the shim --"
: > "$WSL_LOG"; mkwsl
CP='~/.ssh/cm-%r-%h-%p'
PATH="$UB:$PATH" rsync -a -e "$SHIM -o ControlPath=$CP" \
  'nowhere.invalid:/nonexistent/path' "$TMP/dest/" >/dev/null 2>&1
t "rsync's own -e split still hands wsl.exe one ControlPath token" \
  "$(cat "$WSL_LOG")" "ControlPath=$CP"
t "and the remote target rsync built from it is intact" \
  "$(cat "$WSL_LOG")" 'nowhere.invalid'

echo
echo "-- (d) on Linux there is no shim at all, and nothing calls wsl.exe --"
: > "$WSL_LOG"; mkwsl
DECOY_PATH="$TMP/decoybin"; mkdir -p "$DECOY_PATH"; cp "$UB/wsl.exe" "$DECOY_PATH/wsl.exe"
settings 'reach: ssh' 'site_host: me@example.org'
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" \
      PATH="$DECOY_PATH:$PATH" ON_SITE_DRY_RUN=1 bash "$S" true 2>&1)
printf '#!/bin/bash\nexit 0\n' > "$TMP/fake-ssh"; chmod +x "$TMP/fake-ssh"
printf '%-58s ' "on real Linux, wsl.exe on PATH is never touched"
[ ! -s "$WSL_LOG" ] && echo ok || { echo "FAIL: wsl.exe was called <<$(cat "$WSL_LOG")>>"; fails=$((fails+1)); }
t "the dry run still answers normally"           "$out" 'ssh me@example.org'

echo
echo "-- (e) MSYS with no usable wsl.exe: on_site.sh refuses, names WSL --"
: > "$WSL_LOG"; rmwsl   # no wsl.exe at all on PATH
settings 'reach: ssh' 'site_host: me@example.org'
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" PATH="$UB:$PATH" bash "$S" true 2>&1); rc=$?
printf '%-58s ' "refuses with exit 2"
[ "$rc" = 2 ] && echo ok || { echo "FAIL: rc=$rc <<$out>>"; fails=$((fails+1)); }
t "the message names WSL, not just 'the shell'"  "$out" 'WSL'
t "it still says what is refused is the shell, not the folder" "$out" 'not the folder'
tnot "it does not tell the user to relocate their project" "$out" 'move your project'

echo
echo "-- (f) ON_SITE_SSH_BIN still beats the bridge, even when one is available --"
: > "$WSL_LOG"; mkwsl
SSH_MARKER="$TMP/fake-ssh.called"
cat > "$TMP/fake-ssh" <<EOF
#!/bin/bash
: >> "$SSH_MARKER"
exit 0
EOF
chmod +x "$TMP/fake-ssh"
settings 'reach: ssh' 'site_host: me@example.org'
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" ON_SITE_SSH_BIN="$TMP/fake-ssh" \
      PATH="$UB:$PATH" bash "$S" --check-reach 2>&1); rc=$?
printf '%-58s ' "the override still succeeds"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc=$rc <<$out>>"; fails=$((fails+1)); }
printf '%-58s ' "the override binary was the one actually called"
[ -e "$SSH_MARKER" ] && echo ok || { echo "FAIL: ON_SITE_SSH_BIN was not invoked"; fails=$((fails+1)); }
# wsl.exe may still see one harmless call - the `wsl.exe -e true` probe that
# decides whether 'site_bridge' auto-detects to 'wsl' at all, which runs
# before ON_SITE_SSH_BIN is known to matter. What must NOT happen is the shim
# itself running - that always calls `wsl.exe -e ssh ...`, so a logged 'ssh'
# argument is the tell that the override was bypassed rather than honoured.
printf '%-58s ' "the shim's own 'wsl.exe -e ssh' was never invoked"
grep -qxF 'ssh' "$WSL_LOG" \
  && { echo "FAIL: the shim ran despite ON_SITE_SSH_BIN <<$(cat "$WSL_LOG")>>"; fails=$((fails+1)); } \
  || echo ok

echo
echo "-- (g) push.sh duplicates the same bridge - prove its own \$SSH resolves --"
# fetch.sh carries the identical block (mirrored, not shared - see both
# files' own comments on why); push.sh is exercised here because nothing
# upstream of its rsync call already asks the site anything, so this is the
# more direct read of "did \$SSH become the shim inside THIS script", not
# just inside scripts/utils/wsl_ssh.sh in isolation (that is (b)/(c) above).
: > "$WSL_LOG"; mkwsl
PUSH_LOG="$TMP/push-rsync.log"
cat > "$TMP/fake-rsync" <<EOF
#!/bin/bash
printf '%s\n' "\$@" > "$PUSH_LOG"
exit 0
EOF
chmod +x "$TMP/fake-rsync"
mkdir -p "$TMP/pushsrc"; : > "$TMP/pushsrc/a.txt"
settings 'reach: ssh' 'site_host: me@example.org'
out=$(LAB_SETTINGS_FILE="$TMP/env.yaml" PUSH_RSYNC_BIN="$TMP/fake-rsync" \
      PATH="$UB:$PATH" bash "$ROOT/scripts/push.sh" "$TMP/pushsrc" /remote/dest 2>&1); rc=$?
printf '%-58s ' "push.sh itself still succeeds"
[ "$rc" = 0 ] && echo ok || { echo "FAIL: rc=$rc <<$out>>"; fails=$((fails+1)); }
t "its rsync -e names the shim, not plain ssh" \
  "$(cat "$PUSH_LOG" 2>/dev/null)" "$SHIM"
t "and the ControlPath default is WSL's own unexpanded tilde form" \
  "$(cat "$PUSH_LOG" 2>/dev/null)" 'ControlPath=~/.ssh/cm-%r-%h-%p'

echo
echo "-- (h) preflight.sh: rsync on MSYS is named plainly, not left to rsync's own error --"
: > "$TMP/token"; chmod 600 "$TMP/token"; printf 'stub-token\n' > "$TMP/token"
printf '#!/bin/bash\nexit 0\n' > "$TMP/fake-tw"; chmod +x "$TMP/fake-tw"
printf '#!/bin/bash\nexit 0\n' > "$TMP/fake-ssh-ok"; chmod +x "$TMP/fake-ssh-ok"
settings 'reach: ssh' 'site_host: me@example.org' 'storage_root: /work/runs' \
         'workspace_id: 1' 'compute_env: ce'

run_preflight() {
  LAB_SETTINGS_FILE="$TMP/env.yaml" SEQERA_TOKEN_FILE="$TMP/token" \
  ON_SITE_SSH_BIN="$TMP/fake-ssh-ok" TW_BIN="$TMP/fake-tw" PATH="$1" \
  bash "$ROOT/scripts/preflight.sh" 2>&1
}

out=$(run_preflight "$UB:$PATH")
printf '%-58s ' "MSYS with rsync already on PATH reports it OK"
grep -qE '^OK +rsync' <<<"$out" && echo ok || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }

# A minimal PATH with everything preflight.sh needs EXCEPT rsync - the actual
# absence Git Bash ships, rather than trusting a bare "command not found"
# three layers down to explain itself.
NORSYNC="$TMP/norsyncbin"; mkdir -p "$NORSYNC"
for d in /usr/bin /bin; do
  [ -d "$d" ] || continue
  for f in "$d"/*; do
    b="${f##*/}"
    [ "$b" = rsync ] && continue
    [ -e "$NORSYNC/$b" ] || ln -s "$f" "$NORSYNC/$b" 2>/dev/null
  done
done
ln -sf "$UB/uname" "$NORSYNC/uname"   # the MSYS stub wins over the real one
out=$(run_preflight "$NORSYNC")
t "missing rsync on MSYS is FAILed by name"    "$out" "FAIL       rsync"
t "and it says plainly that Git Bash ships none" "$out" "Git Bash ships none"
t "and gives an install route rather than nothing" "$out" "winget"

echo
echo "-- (i) install_deps.sh: tw on MSYS is named plainly, not folded into 'unknown platform' --"
printf 'workspace_id: 1\n' > "$TMP/idenv.yaml"
out=$(env -i HOME="$TMP" PATH="$UB:/usr/bin:/bin" LAB_SETTINGS_FILE="$TMP/idenv.yaml" \
      INSTALL_ROOT="$TMP/idinstall" bash "$ROOT/scripts/install_deps.sh" --cli-only 2>&1); rc=$?
printf '%-58s ' "install_deps.sh --cli-only fails cleanly, not silently"
[ "$rc" != 0 ] && echo ok || { echo "FAIL: exit 0 <<$out>>"; fails=$((fails+1)); }
t "it names the gap as unmeasured (R4), a real answer"    "$out" "unmeasured"
t "and gives the Windows asset to fetch by hand"           "$out" "tw-windows-x86_64.exe"
tnot "it does not fall back to the generic unknown-platform text" \
  "$out" "known combinations"

# --- (k) the shim does not hand wsl.exe a directory it cannot map -----------
# Measured on the member's machine, 2026-09-16: started from a cloud-drive path
# (`G:\...`, non-ASCII too), wsl.exe printed a path-translation warning and
# started somewhere else. It only warned - but every call to the site would
# have carried that line, and the bridge probe in settings.sh reads an exit
# code. The shim moves to a mappable directory first; this is what pins it.
odd="$TMP/雲端 drive (1)"
mkdir -p "$odd"
log="$TMP/cwd.log"
cat > "$UB/wsl.exe" <<EOF
#!/bin/bash
pwd > "$log"
exit 0
EOF
chmod +x "$UB/wsl.exe"
( cd "$odd" && env PATH="$UB:/usr/bin:/bin" HOME="$TMP" bash "$SHIM" host true ) >/dev/null 2>&1
printf '%-58s ' "shim does not run wsl.exe from the caller's own cwd"
if [ "$(cat "$log" 2>/dev/null)" = "$odd" ]; then
  echo "FAIL: inherited <<$odd>>"; fails=$((fails+1))
else
  echo ok
fi
printf '%-58s ' "and lands in a directory that exists"
[ -d "$(cat "$log" 2>/dev/null)" ] && echo ok \
  || { echo "FAIL: <<$(cat "$log" 2>/dev/null)>>"; fails=$((fails+1)); }

# --- (j) one derivation, not five ------------------------------------------
# on_site.sh, fetch.sh, push.sh, reset_master.sh and detect_conditions.sh all
# need the same answer, and when the bridge first landed each of them worked
# it out for itself. Two of the copies had already drifted: detect_conditions.sh
# probed `wsl.exe` alone and never read `site_bridge`, so a member who had
# turned the bridge off was told this machine was `supported` while every call
# on_site.sh made was refused; reset_master.sh never learned about the bridge
# at all and went on closing a master at a Windows-shaped path nothing had
# opened - silently, while on_site.sh printed that very command as the fix.
# scripts/settings.sh is the one place now (bridge_kind(), site_ssh_bin(),
# site_control_path_default()), the same way token_file() in that file is the
# one place the token is derived. This is what stops a sixth copy appearing.
printf '%-58s ' "only settings.sh decides whether the bridge is in play"
# Comment lines stripped first: naming the key in prose is how these files
# explain themselves, and only a line that RUNS the derivation counts - the
# same crude-but-explicit shape tests/site_scripts_via_on_site.sh uses.
stray=""
for f in "$ROOT"/scripts/*.sh "$ROOT"/scripts/utils/*.sh "$ROOT"/hooks/*.sh; do
  case "$f" in */settings.sh|*/wsl_ssh.sh) continue ;; esac
  # `message=` lines are dropped for the same reason comments are: quoting the
  # probe so the member knows what was tried is the REPORT of the one
  # derivation, not a second one.
  if sed 's/^[[:space:]]*#.*$//' "$f" | grep -v 'message=' \
     | grep -qE "wsl\.exe -e true|setting site_bridge"; then
    stray="$stray $f"
  fi
done
if [ -n "$stray" ]; then
  echo "FAIL: derived again outside settings.sh:"; printf '  %s\n' $stray
  fails=$((fails+1))
else
  echo ok
fi

printf '%-58s ' "and nothing hardcodes the control-path default beside it"
stray=$(grep -rln 'cm-%r-%h-%p' "$ROOT/scripts" "$ROOT/hooks" 2>/dev/null \
        | grep -v '/settings\.sh$')
if [ -n "$stray" ]; then
  echo "FAIL: control-path default restated in:"; printf '  %s\n' $stray
  fails=$((fails+1))
else
  echo ok
fi

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
