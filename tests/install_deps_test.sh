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


# ---------------------------------------------------------------------------
# Z1: under reach: ssh, `tw` runs on the USER'S OWN machine (setup.md talks to
# Platform from wherever Claude is running), not on the cluster - so hardcoding
# tw-linux-x86_64 here means a Mac member installs a binary that will not run.
# Measured against tower-cli v0.40.0's own release: it ships tw-linux-x86_64,
# tw-osx-arm64, tw-osx-x86_64 and tw-windows-x86_64.exe. This picks the asset
# from `uname -s`/`uname -m` with a fake `uname` on PATH, and asserts the URL
# chosen - a fake `curl` records what it was asked to fetch and touches no
# network, so nothing here is actually downloaded.
UB="$TMP/z1bin"; mkdir -p "$UB"
CURL_LOG="$TMP/curl.log"

mkuname() { # mkuname <uname -s answer> <uname -m answer>
  cat > "$UB/uname" <<EOF
#!/bin/bash
case "\$1" in
  -s) echo "$1" ;;
  -m) echo "$2" ;;
  *)  echo unknown ;;
esac
EOF
  chmod +x "$UB/uname"
}

# Records the URL it was asked for and never touches the network: the file
# named by -o is created as a tiny script that exits 0, so the script's own
# "$TW --version" check afterwards succeeds without a real tw binary existing
# anywhere.
cat > "$UB/curl" <<'EOF'
#!/bin/bash
out="" prev=""
for a in "$@"; do
  [ "$prev" = "-o" ] && out="$a"
  prev="$a"
done
echo "${@: -1}" >> "$CURL_LOG"
if [ -n "$out" ]; then printf '#!/bin/bash\nexit 0\n' > "$out"; chmod +x "$out"; fi
exit 0
EOF
chmod +x "$UB/curl"

z1() { # z1 <uname -s> <uname -m>
  mkuname "$1" "$2"
  : > "$CURL_LOG"
  printf 'workspace_id: 1\n' > "$TMP/z1env.yaml"
  env -i HOME="$TMP" PATH="$UB:/usr/bin:/bin" LAB_SETTINGS_FILE="$TMP/z1env.yaml" \
      INSTALL_ROOT="$TMP/z1install" CURL_LOG="$CURL_LOG" \
      bash "$I" --cli-only >/dev/null 2>&1
  tail -1 "$CURL_LOG"
}

t "Darwin/arm64 picks the osx-arm64 asset" \
  "$(z1 Darwin arm64)" \
  "https://github.com/seqeralabs/tower-cli/releases/latest/download/tw-osx-arm64"

t "Darwin/x86_64 picks the osx-x86_64 asset" \
  "$(z1 Darwin x86_64)" \
  "https://github.com/seqeralabs/tower-cli/releases/latest/download/tw-osx-x86_64"

t "Linux/x86_64 keeps the linux-x86_64 asset" \
  "$(z1 Linux x86_64)" \
  "https://github.com/seqeralabs/tower-cli/releases/latest/download/tw-linux-x86_64"

# An unknown combination must fail loudly, naming what it saw - not fall back
# to silently downloading the Linux binary the whole bug report is about.
mkuname Linux aarch64
: > "$CURL_LOG"
printf 'workspace_id: 1\n' > "$TMP/z1env.yaml"
out=$(env -i HOME="$TMP" PATH="$UB:/usr/bin:/bin" LAB_SETTINGS_FILE="$TMP/z1env.yaml" \
      INSTALL_ROOT="$TMP/z1install" CURL_LOG="$CURL_LOG" \
      bash "$I" --cli-only 2>&1); rc=$?
printf '%-58s ' "an unknown platform is not silently given the Linux binary"
[ ! -s "$CURL_LOG" ] && echo ok || { echo "FAIL: curl was still called: $(cat "$CURL_LOG")"; fails=$((fails+1)); }
printf '%-58s ' "and it exits non-zero"
[ "$rc" != 0 ] && echo ok || { echo "FAIL: exit 0"; fails=$((fails+1)); }
t "and names exactly what uname reported"      "uname -s='Linux', uname -m='aarch64'" "$out"

# TW_URL must still win outright, unknown platform or not - the seam the rest
# of this test file (and CI on an unlisted platform) relies on.
mkuname Linux aarch64
: > "$CURL_LOG"
out=$(env -i HOME="$TMP" PATH="$UB:/usr/bin:/bin" LAB_SETTINGS_FILE="$TMP/z1env.yaml" \
      INSTALL_ROOT="$TMP/z1install" CURL_LOG="$CURL_LOG" TW_URL="file://$TMP/somewhere" \
      bash "$I" --cli-only 2>&1); rc=$?
printf '%-58s ' "TW_URL still overrides platform detection"
[ "$rc" = 0 ] && grep -qF "file://$TMP/somewhere" "$CURL_LOG" \
  && echo ok || { echo "FAIL: rc=$rc log=<<$(cat "$CURL_LOG")>> out=<<$out>>"; fails=$((fails+1)); }

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
