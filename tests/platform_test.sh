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
#   ABF_PLATFORM_PREFLIGHT_ONLY=1   stop after the checks and downloads of the first Nextflow pair, run no pytest
#   ABF_PLATFORM_PREFLIGHT_ONLY=2   the same after the second pair (Nextflow 25.10.4, feature 007b) as well
#   ABF_PYTEST_ARGS           extra pytest arguments
#   ABF_PYTEST_TARGETS        what pytest runs, relative to the platform folder (default: tests)
#   ABF_NF_LAUNCHER_URL / ABF_NF_DIST_URL / ABF_NFTOWER_URL and the matching
#   ABF_*_SHA256              override one pin; ABF_NF2_LAUNCHER_URL / ABF_NF2_DIST_URL / ABF_NFTOWER2_URL (and
#                             the matching ABF_NF2_*_SHA256, ABF_NFTOWER2_SHA256) do the same for the second pair
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
PLATFORM_DIR="${ABF_PLATFORM_DIR:-$ROOT/platform}"
CACHE_BASE="${XDG_CACHE_HOME:-$HOME/.cache}"
CACHE="${ABF_PLATFORM_CACHE:-$CACHE_BASE/abf-platform}"
VENV="${ABF_PLATFORM_VENV:-$CACHE_BASE/abf-platform-venv}"
CI_MODE=0
[ "${CI:-}" = "true" ] && CI_MODE=1

# Which part of the platform tests this run is (see the shards below): 1 (the default) to PLATFORM_PARTS, clock, clock2, or all. run_all.sh has
# one entry for each: this file runs part 1, tests/platform_shard_<n>_test.sh selects part n (n = 2 to 8), tests/platform_clock_test.sh
# selects the clock part (one clock file) and tests/platform_clock_2_test.sh the clock2 part (the other one). "all" runs the numbered
# parts and then clock and clock2, in that order, in one go.
PLATFORM_PARTS=8
PART="${ABF_PLATFORM_PART:-1}"
valid_part=0
case "$PART" in clock|clock2|all) valid_part=1 ;; *[!0-9]*|"") ;; *) [ "$((10#$PART))" -ge 1 ] && [ "$((10#$PART))" -le "$PLATFORM_PARTS" ] && [ "$PART" = "$((10#$PART))" ] && valid_part=1 ;; esac
[ "$valid_part" = 1 ] || { echo "FAIL: ABF_PLATFORM_PART must be 1 to $PLATFORM_PARTS, clock, clock2 or all, not '$PART'"; exit 1; }

# The fixed lists. Some of the slowest files (measured; see specs/suite-speed/ledger.md for which and why) are named here, one line for each, so that each
# is a pytest process of its own; the lines are dealt out to the parts longest first, each to the part that has the least so far
# (the REST shards counted in). Every other test file goes into the REST shard of one of the parts, in turn (sorted by name, the
# first to part 1, the second to part 2, and so on), so a new test file has a part without anyone editing this list. LAST are the
# files that check the clock closely: LAST_1 is the clock part, LAST_2 the clock2 part, and LAST is both of them together (the list
# of files that are already named). Sets SHARDS_1 to SHARDS_8 (one shard per line), LAST_1, LAST_2, LAST and REST_1 to REST_8.
# tests/test_launch_nextflow.py is alone in its line on purpose: its setup is one real Nextflow run and cannot be split.
set_platform_parts() {
    LAST_1="tests/test_station_e2e.py"
    LAST_2="tests/test_nextflow_e2e.py"
    LAST="$LAST_1 $LAST_2"
    SHARDS_1="
tests/test_owner_binding.py
tests/test_oauth_mcp.py
tests/test_resume_edit_params_station.py
"
    SHARDS_2="
tests/test_keep_submissions.py
tests/test_confirm_page.py
tests/test_clean_page.py
"
    SHARDS_3="
tests/test_station_channel.py
tests/test_pat.py
tests/test_web_login.py
"
    SHARDS_4="
tests/test_platform_parts.py
tests/test_http_site_samplesheet.py
tests/test_launch_nextflow.py
"
    SHARDS_5="
tests/test_resume_platform.py
tests/test_launch_e2e.py
tests/test_launch_followup.py
"
    SHARDS_6="
tests/test_station_launch.py
tests/test_resume_entrypoints.py
tests/test_cleanup_offer.py
"
    SHARDS_7="
tests/test_station_resume.py
tests/test_owner_gaps.py
tests/test_relay_loopback.py
"
    SHARDS_8="
tests/test_launch_cli.py
tests/test_oauth.py
tests/test_web_board.py
"
    local listed f k=0 n
    listed=" $(echo $SHARDS_1 $SHARDS_2 $SHARDS_3 $SHARDS_4 $SHARDS_5 $SHARDS_6 $SHARDS_7 $SHARDS_8) $LAST "
    for n in $(seq 1 "$PLATFORM_PARTS"); do eval "REST_$n="; done
    for f in $(ls tests/test_*.py | LC_ALL=C sort); do
        case "$listed" in
            *" $f "*) ;;
            *) n=$((k % PLATFORM_PARTS + 1)); eval "REST_$n=\"\$REST_$n $f\""
               k=$((k + 1)) ;;
        esac
    done
}

# The shards of the selected part or parts, one line each (no line for an empty REST). Nothing for the clock parts.
selected_shards() {
    local n files rest line
    case "$PART" in clock|clock2) set -- ;; all) set -- $(seq 1 "$PLATFORM_PARTS") ;; *) set -- "$PART" ;; esac
    for n in "$@"; do
        eval "files=\$SHARDS_$n rest=\$REST_$n"
        while IFS= read -r line; do [ -n "$line" ] && echo "$line"; done <<< "$files"
        rest="${rest# }"
        [ -n "$rest" ] && echo "$rest"
    done
    return 0
}

# ABF_PLATFORM_LIST=1: print the test files of this part, one line per shard (or per serial file), and stop. A check, not a run.
if [ "${ABF_PLATFORM_LIST:-}" = "1" ]; then
    cd "$PLATFORM_DIR" || exit 1
    set_platform_parts
    while IFS= read -r files; do [ -n "$files" ] && echo "shard: $files"; done <<< "$(selected_shards)"
    case "$PART" in clock|all) echo "alone: $LAST_1" ;; esac
    case "$PART" in clock2|all) echo "alone: $LAST_2" ;; esac
    exit 0
fi

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

# unpack_zip <zip> <dest>: unzip, else jar (a JDK is required anyway), and only then
# Python's zipfile. Python 3.12 refuses the sha256-verified nf-tower zip ("Overlapped
# entries ... possible zip bomb"), so it must not be the first or only way.
unpack_zip() {
    local zip="$1" dest="$2"
    case "$zip" in /*) ;; *) zip="$PWD/$zip" ;; esac
    rm -rf "$dest"; mkdir -p "$dest"
    if command -v unzip >/dev/null 2>&1 && unzip -q -o "$zip" -d "$dest"; then return 0; fi
    rm -rf "$dest"; mkdir -p "$dest"
    if command -v jar >/dev/null 2>&1 && (cd "$dest" && jar xf "$zip"); then return 0; fi
    rm -rf "$dest"; mkdir -p "$dest"
    "$VPY" -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$zip" "$dest" && return 0
    rm -rf "$dest"
    return 1
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
            unpack_zip "$ZIP" "$PLUGIN_DIR" || hard_fail "cannot unpack $ZIP"
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

# --- 2b. the second pinned Nextflow (feature 007b) -----------------------------
# Nextflow 25.10.4 with nf-tower 1.17.5 is what the cluster runs. It is set up the same way as the
# first pair (every sha256 checked, a mismatch stops the run in both modes, a download that cannot be
# had is fatal on CI) but only after the first pair's preflight exit above, so ABF_PLATFORM_PREFLIGHT_ONLY=1
# keeps meaning "the first pair" and =2 means "both pairs".
NF2_LAUNCHER_URL="${ABF_NF2_LAUNCHER_URL:-$NF2_LAUNCHER_URL}"
NF2_LAUNCHER_SHA256="${ABF_NF2_LAUNCHER_SHA256:-$NF2_LAUNCHER_SHA256}"
NF2_DIST_URL="${ABF_NF2_DIST_URL:-$NF2_DIST_URL}"
NF2_DIST_SHA256="${ABF_NF2_DIST_SHA256:-$NF2_DIST_SHA256}"
NFTOWER2_URL="${ABF_NFTOWER2_URL:-$NFTOWER2_URL}"
NFTOWER2_SHA256="${ABF_NFTOWER2_SHA256:-$NFTOWER2_SHA256}"
NXF2_HOME_DIR="$CACHE/nxf-home-$NF2_VERSION"
LAUNCHER2="$CACHE/downloads/nextflow-$NF2_VERSION"
E2E2_SKIP_REASON=""
if [ -z "$E2E_SKIP_REASON" ]; then
    DIST2="$CACHE/downloads/nextflow-$NF2_VERSION-dist"
    ZIP2="$CACHE/downloads/nf-tower-$NFTOWER2_VERSION.zip"
    ok=1
    before_reason="$E2E_SKIP_REASON"
    fetch "$NF2_LAUNCHER_URL" "$LAUNCHER2" "$NF2_LAUNCHER_SHA256" || ok=0
    if [ "$ok" = 1 ]; then fetch "$NF2_DIST_URL" "$DIST2" "$NF2_DIST_SHA256" || ok=0; fi
    if [ "$ok" = 1 ]; then fetch "$NFTOWER2_URL" "$ZIP2" "$NFTOWER2_SHA256" || ok=0; fi
    if [ "$ok" = 1 ] && [ "$E2E_SKIP_REASON" = "$before_reason" ]; then
        mkdir -p "$NXF2_HOME_DIR/framework/$NF2_VERSION" "$NXF2_HOME_DIR/plugins"
        cp -f "$DIST2" "$NXF2_HOME_DIR/framework/$NF2_VERSION/nextflow-$NF2_VERSION-dist"
        PLUGIN_DIR2="$NXF2_HOME_DIR/plugins/nf-tower-$NFTOWER2_VERSION"
        if [ "$(cat "$PLUGIN_DIR2/.abf-sha256" 2>/dev/null)" != "$NFTOWER2_SHA256" ]; then
            unpack_zip "$ZIP2" "$PLUGIN_DIR2" || hard_fail "cannot unpack $ZIP2"
            echo "$NFTOWER2_SHA256" > "$PLUGIN_DIR2/.abf-sha256"
        fi
    fi
    if [ "$E2E_SKIP_REASON" != "$before_reason" ] || [ "$ok" = 0 ]; then
        # env_problem put the reason in E2E_SKIP_REASON for the first pair's variable; the first pair
        # itself is fine, so the second pair's reason gets its own variable and the first is restored.
        E2E2_SKIP_REASON="${E2E_SKIP_REASON:-no reason recorded}"
        E2E_SKIP_REASON="$before_reason"
    fi
fi
if [ -n "$E2E_SKIP_REASON" ]; then
    E2E2_SKIP_REASON="$E2E_SKIP_REASON"
fi
if [ -n "$E2E2_SKIP_REASON" ]; then
    export ABF_E2E2_SKIP_REASON="$E2E2_SKIP_REASON"
else
    export ABF_NXF2_LAUNCHER="$LAUNCHER2"
    export ABF_NXF2_HOME="$NXF2_HOME_DIR"
    export ABF_NXF2_VER="$NF2_VERSION"
fi

if [ "${ABF_PLATFORM_PREFLIGHT_ONLY:-}" = "2" ]; then
    if [ -n "$E2E2_SKIP_REASON" ]; then
        echo "preflight done, the end-to-end tests of Nextflow $NF2_VERSION would be skipped"
    else
        echo "preflight OK (both pairs)"
    fi
    exit 0
fi

# --- 3. pytest ------------------------------------------------------------------
LOG="$(mktemp "${TMPDIR:-/tmp}/abf-platform-pytest.XXXXXX")" || exit 1
trap 'rm -f "$LOG" "$LOG".[0-9]*' EXIT
cd "$PLATFORM_DIR" || exit 1
export PYTHONPATH="$PLATFORM_DIR${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
if [ -n "${ABF_PYTEST_TARGETS:-}" ] || [ -n "${ABF_PYTEST_SERIAL:-}" ]; then
    # one pytest process: what was asked for (the wrapper's own tests do this to run a single file)
    # shellcheck disable=SC2086
    "$VPY" -m pytest -rsfE -p no:cacheprovider ${ABF_PYTEST_TARGETS:-tests} ${ABF_PYTEST_ARGS:-} 2>&1 | tee "$LOG"
    rc=${PIPESTATUS[0]}
else
    # Several pytest processes at once, by test file. The suite is long (real Nextflow runs, real processes, long polls that
    # wait) and the files do not share state: each makes its own folders and takes its own free ports. The shards are fixed
    # lists, balanced by the time each file took when they were made; every other file goes into a REST shard. Two files
    # check the clock closely (the agent's heartbeats are 2 s apart and a rebuilt end time must be within a second of the live
    # one) and failed on a runner with two cores when other shards were busy, so they run one after the other, alone, once the
    # shards have finished. Output is printed shard by shard at the end.
    #
    # Several run_all.sh entries share this file, so that none of them comes near the per-test limit of run_all.sh (the limit only
    # catches a hang, and one entry for the whole suite was too long for it): this one (ABF_PLATFORM_PART=1, the default) runs part 1,
    # tests/platform_shard_<n>_test.sh (parts 2 to 8) run the others, and tests/platform_clock_test.sh (ABF_PLATFORM_PART=clock) and
    # tests/platform_clock_2_test.sh (ABF_PLATFORM_PART=clock2) run one clock-sensitive file each. run_all.sh runs one entry at a time,
    # so those files still run alone. ABF_PLATFORM_PART=all runs all the parts, as this file once did: the shards, then the clock
    # files one after the other.
    # Every test file is in exactly one part: the files named here, and everything else in a REST shard, turn by turn.
    set_platform_parts
    rc=0
    n=0
    pids=""
    start_shard() {
        n=$((n + 1))
        # A job started with & by a script is started with SIGINT ignored, and every program under it would inherit that: a test
        # that sends the agent SIGINT would find it deaf. So Python puts SIGINT back to its default and then becomes pytest.
        # shellcheck disable=SC2086
        "$VPY" -c 'import os, signal, sys; signal.signal(signal.SIGINT, signal.SIG_DFL); os.execv(sys.executable, [sys.executable, "-m", "pytest"] + sys.argv[1:])'             -rsfE -p no:cacheprovider $1 ${ABF_PYTEST_ARGS:-} > "$LOG.$n" 2>&1 &
        pids="$pids $!"
    }
    shard_rc=""
    if [ "$PART" != "clock" ] && [ "$PART" != "clock2" ]; then
        while IFS= read -r files; do
            [ -n "$files" ] && start_shard "$files"
        done < <(selected_shards)
        for pid in $pids; do wait "$pid"; k=$?; shard_rc="$shard_rc $k"; [ "$k" = 0 ] || rc=1; done
    fi
    clock_files=""
    case "$PART" in clock|all) clock_files="$LAST_1" ;; esac
    case "$PART" in clock2|all) clock_files="$clock_files $LAST_2" ;; esac
    for f in $clock_files; do
        pids=""
        start_shard "$f"
        for pid in $pids; do wait "$pid"; k=$?; shard_rc="$shard_rc $k"; [ "$k" = 0 ] || rc=1; done
    done
    : > "$LOG"
    for i in $(seq 1 "$n"); do
        echo "===== pytest shard $i ====="
        cat "$LOG.$i"
        cat "$LOG.$i" >> "$LOG"
    done
    echo "pytest exit code of each shard, in order: $shard_rc"
fi

skipped=0
for k in $(sed -n 's/.* \([0-9][0-9]*\) skipped.*/\1/p' "$LOG"); do skipped=$((skipped + k)); done
echo
if [ -n "$E2E_SKIP_REASON" ]; then
    echo "E2E SKIPPED: $E2E_SKIP_REASON"
fi
# which tests failed, last, so that a log cut to its tail (tests/run_all.sh prints the last lines only) still names them
failing="$(grep -E '^(FAILED|ERROR) ' "$LOG" | sort -u)"
if [ -n "$failing" ]; then
    echo "failing tests:"
    printf '%s\n' "$failing" | cut -c1-200
fi
echo "platform tests: pytest exit $rc, $skipped skipped"
if [ "$rc" = 0 ] && [ "$CI_MODE" = 1 ] && [ "$skipped" != 0 ]; then
    echo "FAIL (CI=true): $skipped test(s) were skipped, and nothing may be skipped on CI"
    exit 1
fi
exit "$rc"
