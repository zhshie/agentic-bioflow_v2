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
#
# Not on native Windows Git Bash (issue #1). Run there, 23 of 40 files failed,
# every one a known MSYS gap - no multiplexed ssh (PITFALLS 16b), no USER,
# hostname.exe without -s - and the result read like a broken release. The
# plugin itself already refuses that shell and sends the user to WSL
# (session_start.sh, settings.sh, on_site.sh), so the runner says the same
# thing once and stops with exit 3, distinct from a real failure's 1. The
# suite itself needs only a Linux/macOS bash, not Claude Code, so the message
# offers the login node (Remote-SSH) as well as WSL.
# --allow-msys runs anyway, and the verdict then names the gap.
#
# Not without jq or python3 either (issue #70). On a machine with no jq, 22 of 94
# files went red and read like a broken Safety Net; the gates were fine (each
# refuses with exit 2 when jq is missing, PITFALLS 28) - the tests build their
# inputs and read the hook answers with jq. So the runner checks both tools
# before running anything, says so once, and stops with exit 3. The check that
# the gates hold without jq is tests/gates_without_jq_test.sh, which needs no jq
# and is exempt (alone it runs anyway). --allow-missing-tools runs regardless and
# the verdict then names what was missing.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT/scripts/utils/portable.sh" || { echo "cannot read scripts/utils/portable.sh"; exit 1; }

PER_TEST_TIMEOUT=300   # no test measured above ~30s; this only catches a hang
ONLY=""
VERBOSE=0

usage() {
    cat >&2 <<'U'
usage: run_all.sh [--only <substring>] [--timeout <secs>] [--verbose] [--list]
                  [--allow-msys] [--allow-missing-tools]

  --only <substring>   run only test files whose name contains this
  --timeout <secs>     per-test limit (default 300; 0 disables)
  --verbose            print each test's own output as it runs
  --list               list the test files that would run, then stop
  --allow-msys         run on native Windows Git Bash/MSYS anyway (failures
                       there are the known gap in PITFALLS 16b, not a regression)
  --allow-missing-tools  run even though jq or python3 is missing or does not work
                       (the reds are then those tools, not a regression; also
                       skipped for python3 under --allow-msys, PITFALLS 20c)
U
    exit 2
}

LIST=0
ALLOW_MSYS=0
ALLOW_MISSING=0
while [ $# -gt 0 ]; do
    case "$1" in
        --only)    ONLY="${2-}"; [ -n "$ONLY" ] || usage; shift 2 ;;
        --timeout) PER_TEST_TIMEOUT="${2-}"; case "$PER_TEST_TIMEOUT" in ''|*[!0-9]*) usage ;; esac; shift 2 ;;
        --verbose) VERBOSE=1; shift ;;
        --list)    LIST=1; shift ;;
        --allow-msys) ALLOW_MSYS=1; shift ;;
        --allow-missing-tools) ALLOW_MISSING=1; shift ;;
        -h|--help) usage ;;
        *)         echo "unknown option: $1" >&2; usage ;;
    esac
done

ON_MSYS=0
[ "$(plat_kind)" = msys ] && ON_MSYS=1
if [ "$ON_MSYS" = 1 ] && [ "$ALLOW_MSYS" = 0 ] && [ "$LIST" = 0 ]; then
    cat >&2 <<'W'
This shell is native Windows Git Bash (MSYS). The test suite is not run here.

Most of it would fail, and none of those failures would mean the release is
broken: python3 on PATH here is a Microsoft Store stub that exits without
printing (docs/PITFALLS.md 20c), there is no USER variable, and the hostname
has no -s.

The suite only needs a Linux or macOS bash (plus jq and python3) - not Claude
Code. On Windows, either of these works:

  - the cluster's login node, e.g. over VS Code Remote-SSH:
      bash <plugin root>/tests/run_all.sh
  - a WSL shell:
      wsl
      bash <plugin root>/tests/run_all.sh

To run here anyway and see the failures: run_all.sh --allow-msys
W
    exit 3
fi

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

# jq and python3 must compute, not just exist (issue #70; same probe the hooks
# use for jq, trailing CR allowed). Skipped when the only file selected is the
# one that needs neither. --allow-msys skips python3: the Store stub there is the
# known MSYS gap (PITFALLS 20c); jq is still checked.
MISSING=""
if [ "$FILES" != "gates_without_jq_test.sh" ]; then
    probe=$(jq -c .a <<<'{"a":[1]}' 2>/dev/null); [ "${probe%$'\r'}" = '[1]' ] || MISSING="jq"
    if [ "$ALLOW_MSYS" = 0 ]; then
        probe=$(python3 -c 'print(1)' 2>/dev/null); [ "${probe%$'\r'}" = 1 ] || MISSING="${MISSING:+$MISSING and }python3"
    fi
fi
if [ -n "$MISSING" ] && [ "$ALLOW_MISSING" = 0 ]; then
    echo "The test suite is not run here: $MISSING is missing or does not work." >&2
    case "$MISSING" in *jq*) cat >&2 <<'W'

Most test files build their inputs and read the hooks' answers with jq, so
without it they go red for that reason alone, which reads like a broken Safety
Net. It is not one: the gates still refuse when jq is missing (exit 2, "BLOCKED";
PITFALLS 28). To check exactly that, run the one test that needs no jq:

  bash tests/gates_without_jq_test.sh

Install jq to run the whole suite:
  Debian/Ubuntu:  sudo apt install jq
  macOS:          brew install jq
W
    ;; esac
    case "$MISSING" in *python3*) cat >&2 <<'W'

python3 must print when run (a Microsoft Store stub that exits silently does
not count; docs/PITFALLS.md 20c). Install python3, then run this again.
W
    ;; esac
    echo >&2
    echo "To run anyway and see the reds: run_all.sh --allow-missing-tools" >&2
    exit 3
fi

VERSION="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    "$ROOT/.claude-plugin/plugin.json" 2>/dev/null | head -1)"
LOGDIR="$(mktemp -d "${TMPDIR:-/tmp}/bioflow-tests.XXXXXX")" || exit 1

echo "root:    $ROOT"
echo "version: ${VERSION:-unknown}"
echo "logs:    $LOGDIR"
echo

passed=0; failed=0; timedout=0; FAILED_LIST=""
# </dev/null on every test below: this loop reads its file list from stdin,
# and a test that reads stdin - or a child that does, as Windows' py.exe
# launcher did under Git Bash in the 2.15.0 verification - swallowed the rest
# of the list. The run then stopped after 5 of 70 files and printed a summary
# that looked complete. The count check after the loop catches any other way
# that can happen.
while IFS= read -r b; do
    [ -n "$b" ] || continue
    printf '%-46s ' "$b"
    start=$SECONDS
    if [ "$VERBOSE" = 1 ]; then
        clocked "$PER_TEST_TIMEOUT" bash "$ROOT/tests/$b" </dev/null 2>&1 | tee "$LOGDIR/$b.log"
        rc=${PIPESTATUS[0]}
        printf '%-46s ' "-> $b"
    else
        clocked "$PER_TEST_TIMEOUT" bash "$ROOT/tests/$b" </dev/null >"$LOGDIR/$b.log" 2>&1
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
expected=$(grep -c . <<<"$FILES")
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
[ "$total" != "$expected" ] && summary="$summary - INCOMPLETE: only $total of $expected test files ran"
if [ -n "$MISSING" ]; then
    summary="$summary - run with --allow-missing-tools, $MISSING missing"
fi
[ "$failed"   -gt 0 ] && summary="$summary, $failed failed"
[ "$timedout" -gt 0 ] && summary="$summary, $timedout timed out"
echo "$summary"
# Pass or fail, a count from this shell is not the release verdict.
if [ "$ON_MSYS" = 1 ]; then
    echo "note: run on Git Bash/MSYS with --allow-msys - failures here are the known"
    echo "      MSYS gap (docs/PITFALLS.md 20c), not a regression. Rerun on Linux/WSL for a verdict."
fi
[ "$failed" = 0 ] && [ "$timedout" = 0 ] && [ "$total" = "$expected" ] || exit 1
echo "all green"
