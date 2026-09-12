#!/bin/bash
# Install the three things this cluster does not provide, into the execution
# area rather than a home directory.
#
# Why each one, so nobody removes them as unnecessary:
#
#   Java 21    tw-agent.jar needs it and the cluster offers 17 and 8. The
#              native tw-agent binary would avoid this, but it needs glibc
#              2.32/2.34 and the login nodes have 2.28 (PITFALLS 1).
#   the jar    Seqera's agent. Without it Platform cannot read anything this
#              cluster produces, and every run's outputs look absent.
#   tw         Seqera's CLI. Not a module here.
#
# Into $LAB_RUNS_DIR, never into ~: /home/<user> is drwx------ on this cluster,
# so anything placed there exists for exactly one person - which is fine until
# it is not, and then the failure is "missing or unreadable" rather than
# anything that names the real problem.
#
# Idempotent. Re-run it after a failed download; it checks what is already good.
#
#   install_deps.sh              all three, into the execution area
#   install_deps.sh --cli-only   just tw, into INSTALL_ROOT (default: beside the
#                                settings file)
#
# The split exists because the three pieces do not all belong on one machine.
# The agent and its Java run where the results are; `tw` talks to Platform over
# HTTPS and so belongs wherever Claude is running. On a deployment driven from
# the user's own machine that is two different computers, and the laptop has no
# use for a JDK it will never start.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

CLI_ONLY=""
[ "${1:-}" = "--cli-only" ] && CLI_ONLY=1

if [ -n "$CLI_ONLY" ]; then
    ROOT="${INSTALL_ROOT:-$(dirname "$SETTINGS_FILE")}"
else
    : "${LAB_RUNS_DIR:?set LAB_RUNS_DIR to the execution area first}"
    ROOT="$LAB_RUNS_DIR"
fi
DEST="${ROOT}/_agent"
BIN="${ROOT}/_bin"
JDK_URL='https://api.adoptium.net/v3/binary/latest/21/ga/linux/x64/jdk/hotspot/normal/eclipse'
JAR_URL='https://github.com/seqeralabs/tower-agent/releases/latest/download/tw-agent.jar'

# `tw` is a CLI binary, not a module, and under `reach: ssh` it runs on the
# USER'S OWN machine - setup.md talks to Platform from wherever Claude is
# running, which for an ssh deployment is the member's laptop, not this
# cluster. Hardcoding tw-linux-x86_64 here meant every Mac member's setup
# downloaded a Linux binary and failed. Measured against tower-cli v0.40.0's
# release: it ships tw-linux-x86_64, tw-osx-arm64, tw-osx-x86_64 and
# tw-windows-x86_64.exe (Windows only reaches this repo through WSL, which
# reports Linux - PITFALLS 16b/16f - so it is not a fourth case here).
# TW_URL always wins when set: the tests rely on that seam, and so does anyone
# on a platform this has not been taught yet.
tw_asset_url() {
    local os arch
    os="$(uname -s 2>/dev/null)"
    arch="$(uname -m 2>/dev/null)"
    case "$os:$arch" in
        Linux:x86_64)  printf '%s\n' "https://github.com/seqeralabs/tower-cli/releases/latest/download/tw-linux-x86_64" ;;
        Darwin:arm64)  printf '%s\n' "https://github.com/seqeralabs/tower-cli/releases/latest/download/tw-osx-arm64" ;;
        Darwin:x86_64) printf '%s\n' "https://github.com/seqeralabs/tower-cli/releases/latest/download/tw-osx-x86_64" ;;
        *)
            printf '  FAIL  no tw release asset known for this platform: uname -s='"'"'%s'"'"', uname -m='"'"'%s'"'"'\n' "$os" "$arch" >&2
            printf '        known combinations: Linux/x86_64, Darwin/arm64, Darwin/x86_64.\n' >&2
            printf '        set TW_URL to the right download for this machine and re-run.\n' >&2
            return 1
            ;;
    esac
}

mkdir -p "$DEST" "$BIN" || exit 1
ok() { printf '  ok    %s\n' "$*"; }
did() { printf '  done  %s\n' "$*"; }
bad() { printf '  FAIL  %s\n' "$*" >&2; }

# --- Java 21 ----------------------------------------------------------------
java_ok() { [ -x "${1:-}" ] && "$1" -version 2>&1 | grep -qE '"21\.'; }

if [ -z "$CLI_ONLY" ]; then
JAVA="$(setting agent_java)"
if java_ok "$JAVA"; then
    ok "Java 21 already at $JAVA"
else
    # An existing 21 anywhere the member can read is fine - no reason to pull
    # 200 MB again just because it is not where this script would have put it.
    FOUND=""
    for c in "$DEST"/jdk-21*/bin/java "$JAVA_HOME/bin/java" "$(command -v java 2>/dev/null)"; do
        java_ok "$c" && { FOUND="$c"; break; }
    done
    if [ -n "$FOUND" ]; then
        JAVA="$FOUND"; ok "found Java 21 at $JAVA"
    else
        echo "  ...  downloading Temurin 21 (about 200 MB, once)"
        TMP="$DEST/.jdk.tar.gz"
        if curl -fsSL -o "$TMP" "$JDK_URL"; then
            tar -xzf "$TMP" -C "$DEST" && rm -f "$TMP"
            JAVA=$(echo "$DEST"/jdk-21*/bin/java)
            java_ok "$JAVA" && did "Java 21 -> $JAVA" || { bad "unpacked but will not run: $JAVA"; exit 1; }
        else
            bad "could not download Temurin 21 from $JDK_URL"
            echo "        The login node needs outbound access for this step." >&2
            exit 1
        fi
    fi
fi
set_setting agent_java "$JAVA"

# --- tw-agent.jar -----------------------------------------------------------
JAR="$(setting agent_jar)"
if [ -r "$JAR" ] && [ "$(stat_size "$JAR" || echo 0)" -gt 1000000 ]; then
    ok "agent jar already at $JAR"
else
    JAR="$DEST/tw-agent.jar"
    if curl -fsSL -o "$JAR" "$JAR_URL" && [ "$(stat_size "$JAR" || echo 0)" -gt 1000000 ]; then
        did "tw-agent.jar -> $JAR"
    else
        bad "could not download tw-agent.jar from $JAR_URL"; exit 1
    fi
fi
set_setting agent_jar "$JAR"
fi

# --- tw CLI -----------------------------------------------------------------
TW="$(setting tw_bin)"
if [ -x "$TW" ] && "$TW" --version >/dev/null 2>&1; then
    ok "tw already at $TW"
elif TW=$(command -v tw 2>/dev/null) && [ -n "$TW" ]; then
    ok "tw already on PATH at $TW"
else
    TW="$BIN/tw"
    if [ -z "${TW_URL:-}" ]; then
        TW_URL="$(tw_asset_url)" || exit 1
    fi
    if ! curl -fsSL -o "$TW" "$TW_URL"; then
        bad "could not download tw from $TW_URL"; exit 1
    fi
    chmod +x "$TW"
    "$TW" --version >/dev/null 2>&1
    rc=$?
    if [ "$rc" = 0 ]; then
        did "tw -> $TW"
    elif [ "$rc" -ge 128 ]; then
        # A shell reports a signal death as 128+n. The download is fine here -
        # correct size, executable ELF - and it dies the moment it runs, which
        # made "could not install tw" point at the network for an afternoon.
        # Under WSL2 the cause is always the same one: tw is a GraalVM native
        # image that calls the legacy vsyscall page, and WSL2 boots
        # vsyscall=none, so the call takes SIGSEGV instead of emulation.
        bad "tw downloaded but died on signal $((rc - 128)) when run."
        printf '%s\n' \
          "" \
          "        The binary is intact ($(wc -c < "$TW") bytes, executable). It is the kernel" \
          "        refusing what it does at startup. On WSL2 this is vsyscall - see" \
          "        PITFALLS 16f. Fix it once, machine-wide, in %UserProfile%\\.wslconfig:" \
          "" \
          "            [wsl2]" \
          "            kernelCommandLine = vsyscall=emulate" \
          "" \
          "        then 'wsl --shutdown' and reopen. That also drops the ssh master," \
          "        so budget a reconnect straight after." \
          "" \
          "        Elsewhere, 'dmesg | tail' names the real reason." >&2
        exit 1
    else
        bad "tw downloaded but 'tw --version' failed (exit $rc) - run it by hand for the reason"; exit 1
    fi
fi
set_setting tw_bin "$TW"

echo
echo "Recorded in the settings file. Nothing here is on PATH by design - the"
echo "scripts read these paths rather than relying on the shell's environment."

# Run on the site from another machine, this script's set_setting calls land in
# a settings file the caller cannot see. Print what was discovered so the
# caller can put it in the one that counts - `settings.sh --set <key> <value>`.
echo
echo "--- settings ---"
[ -n "${JAVA:-}" ] && echo "agent_java: $JAVA"
[ -n "${JAR:-}"  ] && echo "agent_jar: $JAR"
[ -n "${TW:-}"   ] && echo "tw_bin: $TW"
exit 0
