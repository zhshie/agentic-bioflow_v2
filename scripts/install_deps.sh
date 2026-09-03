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
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

: "${LAB_RUNS_DIR:?set LAB_RUNS_DIR to the execution area first}"
DEST="${LAB_RUNS_DIR}/_agent"
BIN="${LAB_RUNS_DIR}/_bin"
JDK_URL='https://api.adoptium.net/v3/binary/latest/21/ga/linux/x64/jdk/hotspot/normal/eclipse'
JAR_URL='https://github.com/seqeralabs/tower-agent/releases/latest/download/tw-agent.jar'
TW_URL='https://github.com/seqeralabs/tower-cli/releases/latest/download/tw-linux-x86_64'

mkdir -p "$DEST" "$BIN" || exit 1
ok() { printf '  ok    %s\n' "$*"; }
did() { printf '  done  %s\n' "$*"; }
bad() { printf '  FAIL  %s\n' "$*" >&2; }

# --- Java 21 ----------------------------------------------------------------
java_ok() { [ -x "${1:-}" ] && "$1" -version 2>&1 | grep -qE '"21\.'; }

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
if [ -r "$JAR" ] && [ "$(stat -c%s "$JAR" 2>/dev/null || echo 0)" -gt 1000000 ]; then
    ok "agent jar already at $JAR"
else
    JAR="$DEST/tw-agent.jar"
    if curl -fsSL -o "$JAR" "$JAR_URL" && [ "$(stat -c%s "$JAR")" -gt 1000000 ]; then
        did "tw-agent.jar -> $JAR"
    else
        bad "could not download tw-agent.jar from $JAR_URL"; exit 1
    fi
fi
set_setting agent_jar "$JAR"

# --- tw CLI -----------------------------------------------------------------
TW="$(setting tw_bin)"
if [ -x "$TW" ] && "$TW" --version >/dev/null 2>&1; then
    ok "tw already at $TW"
elif TW=$(command -v tw 2>/dev/null) && [ -n "$TW" ]; then
    ok "tw already on PATH at $TW"
else
    TW="$BIN/tw"
    if curl -fsSL -o "$TW" "$TW_URL" && chmod +x "$TW" && "$TW" --version >/dev/null 2>&1; then
        did "tw -> $TW"
    else
        bad "could not install tw from $TW_URL"; exit 1
    fi
fi
set_setting tw_bin "$TW"

echo
echo "Recorded in the settings file. Nothing here is on PATH by design - the"
echo "scripts read these paths rather than relying on the shell's environment."
