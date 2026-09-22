#!/bin/bash
# What "only you can read this" means on Windows, where the number this shell
# prints is not the number the operating system uses.
#
# PITFALLS 16j measured `chmod 600` under C:\Users\<user> reading back as 644 in
# Git Bash, and 2.13.1 took that at face value: it refused to write the settings
# file there at all. That refusal was protecting against the wrong thing. Git
# Bash mounts NTFS without `acl`, so the mode it reports is manufactured - it is
# not a rendering of the file's real permissions and it is not evidence either
# way. What decides who can read a file on Windows is its ACL, and a file in the
# user's own profile is owner-only by default.
#
# So the check asks Windows instead of asking a number Windows never wrote.
# These tests stand in for that machine: a fake `uname` to reach the branch, a
# fake `powershell.exe` that answers with a scripted ACL, and a `stat` that
# reports 644 throughout - because the whole point is that the mode must stop
# deciding the outcome on this platform.
#
# The ACL fixtures use SIDs, not account names, for the reason the code does:
# `icacls` prints localised names (BUILTIN\Administrators is
# VORDEFINIERT\Administratoren on a German install), and a permission check
# that depends on the display language is a check that fails open in a country
# it was never tested in.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
S="$ROOT/scripts/settings.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t() { printf '%-64s ' "$1"; [ "$2" = "$3" ] && echo ok \
      || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
has() { printf '%-64s ' "$1"; case "$3" in *"$2"*) echo ok ;;
        *) echo "FAIL: nothing matching '$2'"; fails=$((fails+1)) ;; esac; }
hasnot() { printf '%-64s ' "$1"; case "$3" in *"$2"*)
        echo "FAIL: found '$2', which must never be printed"; fails=$((fails+1)) ;;
        *) echo ok ;; esac; }

# --- the machine we are pretending to be ------------------------------------
BIN="$TMP/bin"; mkdir -p "$BIN"
printf '#!/bin/sh\necho MINGW64_NT-10.0-22631\n' > "$BIN/uname"
# The manufactured mode. Everything below runs with this in force, so any
# assertion that passes because of the mode rather than the ACL is a test that
# is not testing what it says.
printf '#!/bin/sh\necho 644\n' > "$BIN/stat"
cat > "$BIN/cygpath" <<'C'
#!/bin/sh
printf 'C:\\fake\\%s\n' "$(basename "$2")"
C
cat > "$BIN/powershell.exe" <<'P'
#!/bin/sh
# Records what it was asked, answers with whatever fixture is in force.
[ -n "${PS_ARGV:-}" ] && printf '%s\n' "$@" > "$PS_ARGV"
[ -n "${PS_RC:-}" ] && [ "$PS_RC" != 0 ] && exit "$PS_RC"
[ -r "${PS_FIXTURE:-/nonexistent}" ] && cat "$PS_FIXTURE"
exit 0
P
chmod +x "$BIN"/*

ME=S-1-5-21-111-222-333-1001
# Windows line endings throughout, because that is what a real powershell.exe
# emits. A carriage return left on the end of a SID stops it matching the
# well-known ones, and the clean fixture below would then be read as exposed -
# which is why the CR is in the fixture that has to come out clean.
CLEAN="$TMP/acl_clean"
printf 'me=%s\r\nowner=%s\r\nace=%s\r\nace=S-1-5-18\r\nace=S-1-5-32-544\r\n' \
    "$ME" "$ME" "$ME" > "$CLEAN"
OPEN="$TMP/acl_open"
printf 'me=%s\r\nowner=%s\r\nace=%s\r\nace=S-1-5-18\r\nace=S-1-1-0\r\n' \
    "$ME" "$ME" "$ME" > "$OPEN"

win() { PATH="$BIN:$PATH" PS_FIXTURE="${FIX:-$CLEAN}" "$@"; }

# --- 1. the ordinary Windows case: the mode lies, the ACL is fine -----------
F1="$TMP/clean/env.yaml"
out=$(FIX="$CLEAN" win env LAB_SETTINGS_FILE="$F1" bash "$S" --set workspace_id 7 2>&1); rc=$?
t "a clean ACL is written, though this shell reports mode 644" "$rc" "0"
printf '%-64s ' "...and the value really landed in the file"
grep -qF 'workspace_id: 7' "$F1" 2>/dev/null && echo ok \
  || { echo "FAIL: not written <<$out>>"; fails=$((fails+1)); }
hasnot "...and nothing is said about a mode Windows never wrote" "644" "$out"

# --- 2. an ACL that lets someone else in ------------------------------------
F2="$TMP/open/env.yaml"
out=$(FIX="$OPEN" win env LAB_SETTINGS_FILE="$F2" bash "$S" --set workspace_id 7 2>&1); rc=$?
t "an ACL granting a third party is refused" "$rc" "1"
has "...and names who Windows is letting in"   "S-1-1-0" "$out"
# T30: a private location is now named as a ROOT to point at, not a file
# path to copy to - the fix is one command, and the advice has to be that
# command or a reader will hand-place a file the pointer does not know about.
has "...and says where a private location is"  "--use " "$out"
hasnot "...and does not blame the manufactured mode" "mode 644" "$out"
printf '%-64s ' "...and the file this call created is not left behind"
[ ! -e "$F2" ] && echo ok || { echo "FAIL: $F2 still exists"; fails=$((fails+1)); }

# --- 3. Windows cannot be asked ---------------------------------------------
# 'cannot tell' is not 'unsafe'. The same rule the empty-stat case already
# follows on every other platform: a check that refuses whenever it fails to
# run is a check people route around.
NOPS="$TMP/nops"; mkdir -p "$NOPS"
cp "$BIN/uname" "$BIN/stat" "$BIN/cygpath" "$NOPS/"
F3="$TMP/nops_out/env.yaml"
out=$(PATH="$NOPS:/usr/bin:/bin" LAB_SETTINGS_FILE="$F3" bash "$S" --set workspace_id 7 2>&1); rc=$?
t "no powershell.exe: let through, not refused" "$rc" "0"

F4="$TMP/psfail/env.yaml"
out=$(FIX="$CLEAN" PS_RC=1 win env LAB_SETTINGS_FILE="$F4" bash "$S" --set workspace_id 7 2>&1); rc=$?
t "powershell.exe that fails: let through, not refused" "$rc" "0"

F5="$TMP/psempty/env.yaml"
out=$(FIX=/nonexistent win env LAB_SETTINGS_FILE="$F5" bash "$S" --set workspace_id 7 2>&1); rc=$?
t "powershell.exe that answers nothing: not read as 'clean'" "$rc" "0"
# An empty answer must not be mistaken for an empty ACL, which would look like
# 'nobody else has access' and pass. It is the one failure mode that would be
# both silent and wrong; --summary is where it becomes visible.
out=$(FIX=/nonexistent win env LAB_SETTINGS_FILE="$F5" bash "$S" --summary 2>&1)
hasnot "...and --summary never claims it is private on no answer" "you alone" "$out"

# --- 4. what Windows was actually asked -------------------------------------
ARGV="$TMP/argv"
F6="$TMP/argv_out/env.yaml"
FIX="$CLEAN" PS_ARGV="$ARGV" win env PS_ARGV="$ARGV" LAB_SETTINGS_FILE="$F6" \
    bash "$S" --set workspace_id 7 >/dev/null 2>&1
argv="$(cat "$ARGV" 2>/dev/null)"
has "Windows is asked about a Windows-shaped path" "C:\\fake"    "$argv"
has "...with no profile loaded, so a member's profile cannot answer" "-NoProfile" "$argv"
has "...and non-interactively, so it can never sit waiting for input" "-NonInteractive" "$argv"

# --- 5. the summary and the token report the same finding -------------------
F7="$TMP/report/env.yaml"; mkdir -p "$(dirname "$F7")"
printf 'workspace_id: 1\n' > "$F7"
# A real-looking secret, not an empty file: an assertion that the token's value
# never appears is worth nothing if the value is the empty string (PITFALLS 21).
SECRET='eyJ0aWQiOjEyMzQ1fS5OT1RBUkVBTFRPS0VO'
printf '%s\n' "$SECRET" > "$(dirname "$F7")/.seqera_token"
out=$(FIX="$CLEAN" win env LAB_SETTINGS_FILE="$F7" bash "$S" --summary 2>&1)
has    "--summary says Windows vouched for it"      "you alone"  "$out"
hasnot "...and never prints a mode on this platform" "mode 644"  "$out"
out=$(FIX="$OPEN" win env LAB_SETTINGS_FILE="$F7" bash "$S" --summary 2>&1)
has    "an exposed token is reported as exposed"    "S-1-1-0"    "$out"
hasnot "...and the token's value is still never printed" "$SECRET" "$out"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
