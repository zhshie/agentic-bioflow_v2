#!/bin/bash
# The one failure worth a test here is the one that lied. `tw` is a GraalVM
# native image; under WSL2's default `vsyscall=none` it downloads perfectly and
# then takes SIGSEGV the instant it runs (PITFALLS 16f). The old code reported
# that as "could not install tw from <url>", which sends the reader to the
# network - the one thing that was working.
#
# TW_URL is overridable so the test can hand it a local file:// binary that
# dies the way the real one does. No network, no WSL.
I="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/install_deps.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
t() { printf '%-58s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2'"; fails=$((fails+1)); }; }

printf 'workspace_id: 1\n' > "$TMP/env.yaml"
mkdir -p "$TMP/bin"
# A stand-in for a binary the kernel kills on startup. 139 = 128 + SIGSEGV.
printf '#!/bin/bash\nexit 139\n' > "$TMP/segfaulter"; chmod +x "$TMP/segfaulter"

run() { # PATH without tw, so the "already installed" shortcuts cannot fire
  env -i HOME="$TMP" PATH=/usr/bin:/bin LAB_SETTINGS_FILE="$TMP/env.yaml" \
      INSTALL_ROOT="$TMP" TW_URL="file://$TMP/$1" \
      bash "$I" --cli-only 2>&1
}

out=$(run segfaulter); rc=$?
printf '%-58s ' "a binary that dies on a signal is not a download failure"
[ "$rc" != 0 ] && echo ok || { echo "FAIL: exit 0"; fails=$((fails+1)); }
t "the signal number is named"                 "signal 11"        "$out"
t "and the size proves the download was fine"  "bytes, executable" "$out"
t "it points at the kernel, not the network"   "vsyscall"         "$out"
t "and gives the fix verbatim"                 "kernelCommandLine = vsyscall=emulate" "$out"
t "and warns the master drops with the VM"     "wsl --shutdown"   "$out"

# A binary that merely exits non-zero is a different problem and must not be
# told to go and edit .wslconfig.
printf '#!/bin/bash\nexit 3\n' > "$TMP/dud"; chmod +x "$TMP/dud"
out=$(run dud)
printf '%-58s ' "an ordinary non-zero exit is not blamed on vsyscall"
grep -qF vsyscall <<<"$out" && { echo "FAIL: mentions vsyscall"; fails=$((fails+1)); } || echo ok
t "it reports the exit code instead"           "exit 3"           "$out"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
