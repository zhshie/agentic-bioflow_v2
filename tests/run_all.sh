#!/bin/bash
# Run every test file in this directory and report one verdict.
#
# Why this exists: there are 39 test files and the release procedure says to
# run them twice - once in the repo, once in the deployed copy - which nobody
# does by hand 78 times. A release check that is too tedious to perform is a
# release check that does not happen.
#
# It resolves its own root, so `bash <deployed>/tests/run_all.sh` tests the
# DEPLOYED copy, not this one. The banner prints which root and which version
# it is testing, because "39 passed" means nothing if you tested the wrong
# tree - the exact mistake the deploy step is supposed to catch.
#
# Every test file here signals pass/fail with its exit code (verified across
# all 39), so the verdict rests on that and never on parsing their output.
#
# Not in scope: relay_connect_test.py is a manual probe needing a live relay
# and a host argument, so it is not a file this can run. Nothing here touches
# the network, the cluster, or a real settings file - the tests that exercise
# ssh use ON_SITE_DRY_RUN.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT/scripts/utils/portable.sh" || { echo "cannot read scripts/utils/portable.sh"; exit 1; }

PER_TEST_TIMEOUT=300   # no test measured above ~30s; this only catches a hang
ONLY=""
VERBOSE=0

usage() {
    cat >&2 <<'U'
usage: run_all.sh [--only <substring>] [--timeout <secs>] [--verbose] [--list]

  --only <substring>   run only test files whose name contains this
  --timeout <secs>     per-test limit (default 300; 0 disables)
  --verbose            print each test's own output as it runs
  --list               list the test files that would run, then stop
U
    exit 2
}

LIST=0
while [ $# -gt 0 ]; do
    case "$1" in
        --only)    ONLY="${2-}"; [ -n "$ONLY" ] || usage; shift 2 ;;
        --timeout) PER_TEST_TIMEOUT="${2-}"; case "$PER_TEST_TIMEOUT" in ''|*[!0-9]*) usage ;; esac; shift 2 ;;
        --verbose) VERBOSE=1; shift ;;
        --list)    LIST=1; shift ;;
        -h|--help) usage ;;
        *)         echo "unknown option: $1" >&2; usage ;;
    esac
done

FILES=""
for f in "$ROOT"/tests/*.sh; do
    [ -r "$f" ] || continue
    b="$(basename "$f")"
    [ "$b" = "run_all.sh" ] && continue
    [ -n "$ONLY" ] && case "$b" in *"$ONLY"*) ;; *) continue ;; esac
    FILES="$FILES$b
"
done
FILES="${FILES%$'\n'}"
[ -n "$FILES" ] || { echo "no test files matched${ONLY:+ --only $ONLY}" >&2; exit 2; }

if [ "$LIST" = 1 ]; then printf '%s\n' "$FILES"; exit 0; fi

VERSION="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    "$ROOT/.claude-plugin/plugin.json" 2>/dev/null | head -1)"
LOGDIR="$(mktemp -d "${TMPDIR:-/tmp}/bioflow-tests.XXXXXX")" || exit 1

echo "root:    $ROOT"
echo "version: ${VERSION:-unknown}"
echo "logs:    $LOGDIR"
echo

passed=0; failed=0; timedout=0; FAILED_LIST=""
while IFS= read -r b; do
    [ -n "$b" ] || continue
    printf '%-46s ' "$b"
    start=$SECONDS
    if [ "$VERBOSE" = 1 ]; then
        clocked "$PER_TEST_TIMEOUT" bash "$ROOT/tests/$b" 2>&1 | tee "$LOGDIR/$b.log"
        rc=${PIPESTATUS[0]}
        printf '%-46s ' "-> $b"
    else
        clocked "$PER_TEST_TIMEOUT" bash "$ROOT/tests/$b" >"$LOGDIR/$b.log" 2>&1
        rc=$?
    fi
    dur=$((SECONDS - start))
    case "$rc" in
        0)   echo "ok       ${dur}s";      passed=$((passed + 1)) ;;
        124) echo "TIMEOUT  ${dur}s";      timedout=$((timedout + 1)); FAILED_LIST="$FAILED_LIST$b
" ;;
        *)   echo "FAIL     ${dur}s  rc=$rc"; failed=$((failed + 1));  FAILED_LIST="$FAILED_LIST$b
" ;;
    esac
done <<< "$FILES"

echo
total=$((passed + failed + timedout))
if [ -n "$FAILED_LIST" ]; then
    echo "== output of what did not pass =="
    while IFS= read -r b; do
        [ -n "$b" ] || continue
        echo "--- $b ---"
        # The tail, not the whole log: these files print one line per case and
        # the failing ones are at the end, next to the summary.
        tail -25 "$LOGDIR/$b.log"
        echo
    done <<< "$FAILED_LIST"
fi

summary="$passed/$total passed"
[ "$failed"   -gt 0 ] && summary="$summary, $failed failed"
[ "$timedout" -gt 0 ] && summary="$summary, $timedout timed out"
echo "$summary"
[ "$failed" = 0 ] && [ "$timedout" = 0 ] || exit 1
echo "all green"
