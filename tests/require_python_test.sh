#!/bin/bash
# On this cluster python3 is present, on PATH, and unrunnable: /usr/bin/python3
# is RHEL's reserved interpreter, mode 750 root:root. Every script here that
# uses it got back a bare `Permission denied`, which reads like a broken plugin
# rather than a site that fences its system interpreter (PITFALLS 16d).
#
# The stub below reproduces that exactly - rc 126 and the same one-line message
# - so the guard can be tested without a locked-down interpreter.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
t() { printf '%-58s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2'"; fails=$((fails+1)); }; }

mkpy() { printf '#!/bin/bash\n%s\n' "$1" > "$TMP/python3"; chmod +x "$TMP/python3"; }
ask()  { PATH="$TMP:$PATH" bash -c ". $ROOT/scripts/require_python.sh; require_python" 2>&1; }

mkpy 'exit 0'
printf '%-58s ' "a working python3 passes, and says nothing"
out=$(ask); rc=$?
{ [ "$rc" = 0 ] && [ -z "$out" ]; } && echo ok || { echo "FAIL: rc=$rc out=<<$out>>"; fails=$((fails+1)); }

mkpy 'echo "bash: /usr/bin/python3: Permission denied" >&2; exit 126'
out=$(ask); rc=$?
printf '%-58s ' "a fenced interpreter fails"
[ "$rc" != 0 ] && echo ok || { echo "FAIL: exit 0"; fails=$((fails+1)); }
t "and says it is the site, not this plugin"    "fencing its own system interpreter" "$out"
t "and names the pitfall"                       "16d"                 "$out"
t "and gives the way to a real one"             "module avail python" "$out"
t "and says where the module load line must go" "16c"                 "$out"

# A missing interpreter is a different fault and must not be explained as a
# fence - but the module system is still the answer.
#
# The PATH here has to be built rather than borrowed. /usr/bin/python3 on this
# cluster IS the fenced interpreter, so `PATH=/usr/bin:/bin` is not "no python3"
# - it is 16d itself. What makes the scripts work in an ordinary shell is
# anaconda's python3 sitting earlier on PATH.
mkdir -p "$TMP/nopy" && ln -sf "$(command -v grep)" "$TMP/nopy/grep"
rm -f "$TMP/python3"
out=$(PATH="$TMP/nopy" bash -c ". $ROOT/scripts/require_python.sh; require_python" 2>&1)
printf '%-58s ' "an absent python3 is not explained as a fence"
grep -qF "fencing its own" <<<"$out" && { echo "FAIL"; fails=$((fails+1)); } || echo ok

# The point of the guard is that it fires where the failure actually surfaces.
mkpy 'echo "bash: /usr/bin/python3: Permission denied" >&2; exit 126'
out=$(PATH="$TMP:$PATH" bash "$ROOT/scripts/egress_ctl.sh" status 2>&1)
t "egress_ctl surfaces it instead of a bare denial" "module avail python" "$out"
out=$(PATH="$TMP:$PATH" bash "$ROOT/scripts/agent_ctl.sh" status 2>&1)
t "agent_ctl surfaces it too"                       "module avail python" "$out"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
