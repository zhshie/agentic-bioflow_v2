#!/bin/bash
# Runs the tests of platform/ (feature 008: run receiver + read-only MCP).
#
# Not a CI job of its own: tests/run_all.sh picks this file up like every other
# *_test.sh, so the platform is checked by the same command as the plugin.
#
# What it does, in order:
#   1. finds Python >= 3.10 and builds a venv under
#      ${XDG_CACHE_HOME:-$HOME/.cache}/abf-platform-venv (python -m venv, else virtualenv)
#   2. installs the pinned dependencies (platform/constraints.txt)
#   3. checks Java >= 17 and downloads the pinned Nextflow launcher, its
#      distribution jar and the nf-tower plugin into
#      ${XDG_CACHE_HOME:-$HOME/.cache}/abf-platform, checking every sha256
#      (platform/tests/pins.env), then unpacks the plugin and runs offline
#   4. runs pytest in platform/ and exits with its exit code
#
# No silent skip (constitution VI). When something the end-to-end tests need is
# missing (Java, a download), then
#   - with CI=true the run FAILS, and
#   - without CI it prints one line "E2E SKIPPED: <reason>" and counts the skipped
#     tests in the summary.
# A sha256 that does not match is a failure in both modes: a file that is there
# but wrong is never an environment gap.
#
# Test hooks (used by platform/tests/test_wrapper.py, not needed otherwise):
#   ABF_PLATFORM_DIR          platform folder to test (default: platform/ of this repo)
#   ABF_PLATFORM_CACHE        download folder (default: <cache>/abf-platform)
#   ABF_PLATFORM_VENV         venv folder (default: <cache>/abf-platform-venv)
#   ABF_PLATFORM_PREFLIGHT_ONLY=1   stop after the checks and downloads, run no pytest
#   ABF_PYTEST_ARGS           extra pytest arguments
#   ABF_PYTEST_TARGETS        what pytest runs, relative to the platform folder (default: tests)
#   ABF_NF_LAUNCHER_URL / ABF_NF_DIST_URL / ABF_NFTOWER_URL and the matching
#   ABF_*_SHA256              override one pin
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
PLATFORM_DIR="${ABF_PLATFORM_DIR:-$ROOT/platform}"
CACHE_BASE="${XDG_CACHE_HOME:-$HOME/.cache}"
CACHE="${ABF_PLATFORM_CACHE:-$CACHE_BASE/abf-platform}"
VENV="${ABF_PLATFORM_VENV:-$CACHE_BASE/abf-platform-venv}"
CI_MODE=0
[ "${CI:-}" = "true" ] && CI_MODE=1

PINS="$PLATFORM_DIR/tests/pins.env"
[ -r "$PINS" ] || PINS="$ROOT/platform/tests/pins.env"
# shellcheck disable=SC1090
. "$PINS" || { echo "FAIL: cannot read $PINS"; exit 1; }
NF_LAUNCHER_URL="${ABF_NF_LAUNCHER_URL:-$NF_LAUNCHER_URL}"
NF_LAUNCHER_SHA256="${ABF_NF_LAUNCHER_SHA256:-$NF_LAUNCHER_SHA256}"
NF_DIST_URL="${ABF_NF_DIST_URL:-$NF_DIST_URL}"
NF_DIST_SHA256="${ABF_NF_DIST_SHA256:-$NF_DIST_SHA256}"
NFTOWER_URL="${ABF_NFTOWER_URL:-$NFTOWER_URL}"
NFTOWER_SHA256="${ABF_NFTOWER_SHA256:-$NFTOWER_SHA256}"

E2E_SKIP_REASON=""

# A problem with the environment (not with the code): fatal on CI, a loud
# skip of the end-to-end tests otherwise.
env_problem() {
    if [ "$CI_MODE" = 1 ]; then
        echo "FAIL (CI=true): $1"
        exit 1
    fi
    [ -n "$E2E_SKIP_REASON" ] || E2E_SKIP_REASON="$1"
    echo "E2E SKIPPED: $1"
}

# A problem that leaves nothing to run at all.
no_python_tests() {
    if [ "$CI_MODE" = 1 ]; then
        echo "FAIL (CI=true): $1"
        exit 1
    fi
    echo "PLATFORM TESTS SKIPPED: $1"
    exit 0
}

hard_fail() { echo "FAIL: $1"; exit 1; }

sha_of() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }

# fetch <url> <dest> <expected sha256>
# Returns 0 when dest is present and verified, 1 when it could not be
# downloaded. A wrong checksum stops the whole run.
fetch() {
    local url="$1" dest="$2" want="$3" got tmp
    mkdir -p "$(dirname "$dest")"
    if [ -f "$dest" ]; then
        got="$(sha_of "$dest")"
        [ "$got" = "$want" ] || hard_fail "sha256 mismatch for $dest (got $got, pinned $want)"
        return 0
    fi
    command -v curl >/dev/null 2>&1 || { env_problem "curl is not installed, cannot download $url"; return 1; }
    tmp="$dest.part.$$"
    if ! curl -fsSL --retry 2 --connect-timeout 20 -o "$tmp" "$url"; then
        rm -f "$tmp"
        env_problem "download failed: $url"
        return 1
    fi
    got="$(sha_of "$tmp")"
    if [ "$got" != "$want" ]; then
        rm -f "$tmp"
        hard_fail "sha256 mismatch for the download of $url (got $got, pinned $want)"
    fi
    mv "$tmp" "$dest"
    return 0
}

# --- 1. Python and the venv ---------------------------------------------------
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PY="$c"
        break
    fi
done
[ -n "$PY" ] || no_python_tests "no Python >= 3.10 on PATH"

if [ ! -x "$VENV/bin/python" ]; then
    mkdir -p "$(dirname "$VENV")"
    if ! "$PY" -m venv "$VENV" >/dev/null 2>&1; then
        rm -rf "$VENV"
        if command -v virtualenv >/dev/null 2>&1 && virtualenv -p "$PY" "$VENV" >/dev/null 2>&1; then
            :
        else
            rm -rf "$VENV"
            no_python_tests "cannot create a venv at $VENV (python -m venv and virtualenv both failed)"
        fi
    fi
fi
VPY="$VENV/bin/python"

CONSTRAINTS="$PLATFORM_DIR/constraints.txt"
[ -r "$CONSTRAINTS" ] || CONSTRAINTS="$ROOT/platform/constraints.txt"
STAMP="$(sha_of "$CONSTRAINTS")-mcp2-pytest-httpx"
if [ "$(cat "$VENV/.abf-stamp" 2>/dev/null)" != "$STAMP" ]; then
    echo "installing platform test dependencies into $VENV"
    if "$VPY" -m pip install -q -c "$CONSTRAINTS" 'mcp>=2.3,<3' pytest httpx; then
        echo "$STAMP" > "$VENV/.abf-stamp"
    else
        no_python_tests "pip could not install the platform dependencies"
    fi
fi

# --- 2. Java and the pinned Nextflow ------------------------------------------
JAVA_MAJOR=0
if command -v java >/dev/null 2>&1; then
    jv="$(java -version 2>&1 | sed -n '1s/.*version "\([0-9]*\)\.\{0,1\}\([0-9]*\).*/\1 \2/p')"
    set -- $jv
    if [ "${1:-0}" = "1" ]; then JAVA_MAJOR="${2:-0}"; else JAVA_MAJOR="${1:-0}"; fi
fi
if [ "$JAVA_MAJOR" -lt 17 ]; then
    if [ "$JAVA_MAJOR" = 0 ]; then
        env_problem "Java 17 or newer is required for Nextflow but java was not found on PATH"
    else
        env_problem "Java 17 or newer is required for Nextflow, found Java $JAVA_MAJOR"
    fi
fi

NXF_HOME_DIR="$CACHE/nxf-home-$NF_VERSION"
LAUNCHER="$CACHE/downloads/nextflow-$NF_VERSION"
if [ -z "$E2E_SKIP_REASON" ]; then
    DIST="$CACHE/downloads/nextflow-$NF_VERSION-dist"
    ZIP="$CACHE/downloads/nf-tower-$NFTOWER_VERSION.zip"
    ok=1
    fetch "$NF_LAUNCHER_URL" "$LAUNCHER" "$NF_LAUNCHER_SHA256" || ok=0
    if [ "$ok" = 1 ]; then fetch "$NF_DIST_URL" "$DIST" "$NF_DIST_SHA256" || ok=0; fi
    if [ "$ok" = 1 ]; then fetch "$NFTOWER_URL" "$ZIP" "$NFTOWER_SHA256" || ok=0; fi
    if [ "$ok" = 1 ] && [ -z "$E2E_SKIP_REASON" ]; then
        mkdir -p "$NXF_HOME_DIR/framework/$NF_VERSION" "$NXF_HOME_DIR/plugins"
        cp -f "$DIST" "$NXF_HOME_DIR/framework/$NF_VERSION/nextflow-$NF_VERSION-dist"
        PLUGIN_DIR="$NXF_HOME_DIR/plugins/nf-tower-$NFTOWER_VERSION"
        if [ "$(cat "$PLUGIN_DIR/.abf-sha256" 2>/dev/null)" != "$NFTOWER_SHA256" ]; then
            rm -rf "$PLUGIN_DIR"
            "$VPY" -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$ZIP" "$PLUGIN_DIR" \
                || hard_fail "cannot unpack $ZIP"
            echo "$NFTOWER_SHA256" > "$PLUGIN_DIR/.abf-sha256"
        fi
    fi
fi

if [ -n "$E2E_SKIP_REASON" ]; then
    export ABF_E2E_SKIP_REASON="$E2E_SKIP_REASON"
else
    export ABF_NXF_LAUNCHER="$LAUNCHER"
    export ABF_NXF_HOME="$NXF_HOME_DIR"
    export ABF_NXF_VER="$NF_VERSION"
fi

if [ "${ABF_PLATFORM_PREFLIGHT_ONLY:-}" = "1" ]; then
    if [ -n "$E2E_SKIP_REASON" ]; then
        echo "preflight done, end-to-end tests would be skipped"
    else
        echo "preflight OK"
    fi
    exit 0
fi

# --- 3. pytest ------------------------------------------------------------------
LOG="$(mktemp "${TMPDIR:-/tmp}/abf-platform-pytest.XXXXXX")" || exit 1
trap 'rm -f "$LOG"' EXIT
cd "$PLATFORM_DIR" || exit 1
export PYTHONPATH="$PLATFORM_DIR${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
# shellcheck disable=SC2086
"$VPY" -m pytest -rs -p no:cacheprovider ${ABF_PYTEST_TARGETS:-tests} ${ABF_PYTEST_ARGS:-} 2>&1 | tee "$LOG"
rc=${PIPESTATUS[0]}

skipped="$(sed -n 's/.* \([0-9][0-9]*\) skipped.*/\1/p' "$LOG" | tail -1)"
skipped="${skipped:-0}"
echo
if [ -n "$E2E_SKIP_REASON" ]; then
    echo "E2E SKIPPED: $E2E_SKIP_REASON"
fi
echo "platform tests: pytest exit $rc, $skipped skipped"
if [ "$rc" = 0 ] && [ "$CI_MODE" = 1 ] && [ "$skipped" != 0 ]; then
    echo "FAIL (CI=true): $skipped test(s) were skipped, and nothing may be skipped on CI"
    exit 1
fi
exit "$rc"
