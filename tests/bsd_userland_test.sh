#!/bin/bash
# The macOS half of v2.6, run against a userland that behaves like BSD's.
#
# This is a SIMULATION, and the honest limit is stated here rather than in a
# release note: a stub `stat` that refuses -c catches a wrong flag, and it
# cannot catch a difference nobody thought to stub. It has never run on a real
# Mac. What it does prove is that each fix works when the GNU spelling is
# unavailable, which is the thing that was previously assumed.
#
# bash 3.2 is not simulated at all - this machine has no such bash. The one
# bash-4 construct (`local -A` in tune_resources.sh) was removed rather than
# guarded, and tests/portable_userland.sh is what keeps it gone.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
t() { printf '%-58s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }
ok() { printf '%-58s ' "$1"; [ "$2" = 0 ] && echo ok || { echo "FAIL: rc $2"; fails=$((fails+1)); }; }

# --- a BSD userland ---------------------------------------------------------
# Only the two tools whose divergence is measured. Shadowing grep or sed would
# hide the interpreter this harness needs (PITFALLS 16d), and the code no
# longer calls their GNU-only forms anyway.
BIN="$TMP/bsdbin"; mkdir -p "$BIN"
cat > "$BIN/stat" <<'S'
#!/bin/bash
# BSD stat: -f <format> <file>. There is no -c at all.
[ "${1:-}" = "-c" ] && { echo "stat: illegal option -- c" >&2; exit 1; }
[ "${1:-}" = "-f" ] || { echo "stat: usage" >&2; exit 1; }
python3 - "$2" "$3" <<'P'
import os, sys
fmt, path = sys.argv[1], sys.argv[2]
try: st = os.stat(path)
except OSError: sys.exit(1)
print({"%Lp": oct(st.st_mode & 0o777)[2:], "%z": st.st_size}.get(fmt, ""))
P
S
cat > "$BIN/readlink" <<'S'
#!/bin/bash
# BSD readlink before macOS 12.3: no -f.
[ "${1:-}" = "-f" ] && { echo "readlink: illegal option -- f" >&2; exit 1; }
/usr/bin/readlink "$@"
S
chmod +x "$BIN/stat" "$BIN/readlink"

# CLOCKED_BIN="" is portable.sh's own seam for "this machine has no timeout".
# Emptying PATH instead would take the interpreter the harness runs on with it.
bsd() { env PATH="$BIN:$PATH" CLOCKED_BIN="" "$@"; }

t "the stub really does refuse GNU stat" \
  "$(bsd bash -c 'stat -c %a '"$ROOT"'/README.md >/dev/null 2>&1; echo $?')" "1"

# --- the helpers ------------------------------------------------------------
P="$ROOT/scripts/utils/portable.sh"
chmod 600 "$TMP/probe" 2>/dev/null; : > "$TMP/probe"; chmod 600 "$TMP/probe"
t "stat_mode answers on a BSD stat"  "$(bsd bash -c ". '$P'; stat_mode '$TMP/probe'")" "600"
printf '0123456789' > "$TMP/ten"
t "stat_size answers on a BSD stat"  "$(bsd bash -c ". '$P'; stat_size '$TMP/ten'")"  "10"
t "and a missing file is still empty" "$(bsd bash -c ". '$P'; stat_mode '$TMP/nope'")" ""

ln -s "$TMP/ten" "$TMP/link"
t "resolve_link follows a link without readlink -f" \
  "$(bsd bash -c ". '$P'; resolve_link '$TMP/link'")" "$TMP/ten"

# --- clocked, with no timeout binary anywhere -------------------------------
out=$(bsd bash -c ". '$P'; clocked 5 echo hello"); ok "clocked runs a fast command" $? ""
t  "and its output is intact"  "$out"  "hello"
bsd bash -c ". '$P'; clocked 5 sh -c 'exit 7'"
t  "and its exit code survives"  "$?"  "7"

start=$(date +%s)
bsd bash -c ". '$P'; clocked 1 sleep 20"; rc=$?
elapsed=$(( $(date +%s) - start ))
t "a hung command is actually killed"  "$rc"  "124"
printf '%-58s ' "and within the budget, not after it"
[ "$elapsed" -lt 6 ] && echo "ok (${elapsed}s)" \
  || { echo "FAIL: took ${elapsed}s"; fails=$((fails+1)); }

# The watchdog must not hold the pipe of a command substitution open: that bug
# makes every timed call take exactly its full timeout, silently.
start=$(date +%s)
out=$(bsd bash -c ". '$P'; clocked 20 echo quick")
elapsed=$(( $(date +%s) - start ))
printf '%-58s ' "a captured fast command does not wait out the timer"
[ "$elapsed" -lt 5 ] && echo "ok (${elapsed}s)" \
  || { echo "FAIL: took ${elapsed}s for a command that echoes"; fails=$((fails+1)); }

# --- end to end: the silent failure this began with -------------------------
# A token the whole machine can read has to be called out. Under a BSD stat the
# check used to evaluate to nothing at all and report the token as fine.
H="$TMP/home"; mkdir -p "$H/.config/agentic-bioflow"
cat > "$H/.config/agentic-bioflow/env.yaml" <<'Y'
reach: local
seqera_user: someone
workspace_id: 1
Y
chmod 600 "$H/.config/agentic-bioflow/env.yaml"
echo secret > "$H/.config/agentic-bioflow/.seqera_token"
chmod 644 "$H/.config/agentic-bioflow/.seqera_token"
out=$(env -u LAB_SETTINGS_FILE -u LAB_RUNS_DIR -u SEQERA_TOKEN_FILE \
      PATH="$BIN:$PATH" CLOCKED_BIN="" HOME="$H" \
      XDG_CONFIG_HOME="$H/.config" bash "$ROOT/scripts/settings.sh" --summary 2>&1)
printf '%-58s ' "a world-readable token is still called out"
grep -q "mode 644" <<<"$out" && echo ok \
  || { echo "FAIL: <<$out>>"; fails=$((fails+1)); }
printf '%-58s ' "and its value is still never printed"
grep -q "secret" <<<"$out" && { echo "FAIL: token leaked"; fails=$((fails+1)); } || echo ok

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
