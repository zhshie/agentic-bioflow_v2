#!/bin/bash
# Run every test file in this directory and report one verdict.
#
# Why this exists: the release procedure says to run every test file twice -
# once in the repo, once in the deployed copy - which nobody does by hand. A
# release check that is too tedious to perform is a release check that does
# not happen. The files are every *.sh in this directory except run_all.sh,
# found and counted at run time, so no number is written here to go stale; the
# final summary line reports how many ran.
#
# It resolves its own root, so `bash <deployed>/tests/run_all.sh` tests the
# DEPLOYED copy, not this one. The banner prints which root and which version
# it is testing, because a pass means nothing if you tested the wrong
# tree - the exact mistake the deploy step is supposed to catch.
#
# Every test file here signals pass/fail with its exit code, so the verdict
# rests on that and never on parsing their output.
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
                  [--retry-failed-once] [--check-quarantine]

  --only <substring>   run only test files whose name contains this
  --timeout <secs>     per-test limit (default 300; 0 disables)
  --verbose            print each test's own output as it runs
  --list               list the test files that would run, then stop
  --allow-msys         run on native Windows Git Bash/MSYS anyway (failures
                       there are the known gap in PITFALLS 16b, not a regression)
  --allow-missing-tools  run even though jq or python3 is missing or does not work
                       (the reds are then those tools, not a regression; also
                       skipped for python3 under --allow-msys, PITFALLS 20c)
  --retry-failed-once  re-run each failed or timed-out file once; a file that
                       passes the retry is listed as FLAKY and must be registered
                       in tests/quarantine.txt (issue, expiry at most 14 days out),
                       otherwise the run fails. Still-red files fail either way.
  --check-quarantine   only validate tests/quarantine.txt, run no test, then stop
U
    exit 2
}

LIST=0
ALLOW_MSYS=0
ALLOW_MISSING=0
RETRY=0
CHECKQ=0
while [ $# -gt 0 ]; do
    case "$1" in
        --only)    ONLY="${2-}"; [ -n "$ONLY" ] || usage; shift 2 ;;
        --timeout) PER_TEST_TIMEOUT="${2-}"; case "$PER_TEST_TIMEOUT" in ''|*[!0-9]*) usage ;; esac; shift 2 ;;
        --verbose) VERBOSE=1; shift ;;
        --list)    LIST=1; shift ;;
        --allow-msys) ALLOW_MSYS=1; shift ;;
        --allow-missing-tools) ALLOW_MISSING=1; shift ;;
        --retry-failed-once) RETRY=1; shift ;;
        --check-quarantine) CHECKQ=1; shift ;;
        -h|--help) usage ;;
        *)         echo "unknown option: $1" >&2; usage ;;
    esac
done

# ---- quarantine list and retry (only used with --retry-failed-once or
# --check-quarantine; without them nothing below is called) ------------------
# tests/quarantine.txt: blank lines and whole-line # comments are ignored; every
# other line is exactly three columns: tests/<name>.sh <issue> <YYYY-MM-DD>.
# The expiry is judged against the day of the check only (RUN_ALL_TODAY for the
# tests, else the system date): earlier than today = expired, later than today
# plus 14 days = too far out. Day arithmetic is pure bash, no relative-date
# option of date, no python3.
QFILE="$ROOT/tests/quarantine.txt"
QUAR=""

q_parse_date() { # q_parse_date <YYYY-MM-DD>: sets QD (days since 1970-01-01); 1 if not a real date
    local re='^([0-9]{4})-([0-9]{2})-([0-9]{2})$' y m d dim era yoe doy doe
    [[ "$1" =~ $re ]] || return 1
    y=$((10#${BASH_REMATCH[1]})); m=$((10#${BASH_REMATCH[2]})); d=$((10#${BASH_REMATCH[3]}))
    [ "$m" -ge 1 ] && [ "$m" -le 12 ] || return 1
    case "$m" in
        4|6|9|11) dim=30 ;;
        2) if [ $((y % 4)) = 0 ] && { [ $((y % 100)) != 0 ] || [ $((y % 400)) = 0 ]; }; then dim=29; else dim=28; fi ;;
        *) dim=31 ;;
    esac
    [ "$d" -ge 1 ] && [ "$d" -le "$dim" ] || return 1
    [ "$m" -le 2 ] && y=$((y - 1))
    era=$(( (y >= 0 ? y : y - 399) / 400 ))
    yoe=$((y - era * 400))
    doy=$(( (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1 ))
    doe=$((yoe * 365 + yoe / 4 - yoe / 100 + doy))
    QD=$((era * 146097 + doe - 719468))
}

quarantine_check() { # fills QUAR; prints one stderr line per problem; returns 1 if any
    local today todayn lineno=0 bad=0 line nf fpath fissue fdate seen=" " base
    local re_issue1='^#[0-9]+$' re_issue2='^https://github\.com/[^/]+/[^/]+/issues/[0-9]+$'
    local re_path='^tests/[A-Za-z0-9._-]+\.sh$' re_skip='^[[:space:]]*(#|$)'
    local -a f
    QUAR=""
    [ -f "$QFILE" ] || return 0
    today="${RUN_ALL_TODAY:-$(date +%F)}"
    if ! q_parse_date "$today"; then
        echo "quarantine: today's date '$today' is not YYYY-MM-DD" >&2
        return 1
    fi
    todayn=$QD
    while IFS= read -r line || [ -n "$line" ]; do
        lineno=$((lineno + 1))
        line="${line%$'\r'}"
        [[ "$line" =~ $re_skip ]] && continue
        read -r -a f <<<"$line"
        nf=${#f[@]}
        if [ "$nf" != 3 ]; then
            echo "quarantine: tests/quarantine.txt:$lineno: expected 3 columns (tests/<name>.sh <issue> <YYYY-MM-DD>), found $nf" >&2
            bad=1; continue
        fi
        fpath="${f[0]}"; fissue="${f[1]}"; fdate="${f[2]}"
        base="${fpath#tests/}"
        if ! [[ "$fpath" =~ $re_path ]]; then
            echo "quarantine: tests/quarantine.txt:$lineno: '$fpath' must look like tests/<name>.sh" >&2; bad=1; continue
        elif [ ! -f "$ROOT/$fpath" ]; then
            echo "quarantine: tests/quarantine.txt:$lineno: '$fpath' does not exist (typo? an entry for a missing file protects nothing)" >&2; bad=1; continue
        elif [ "$base" = "platform_test.sh" ]; then
            echo "quarantine: tests/quarantine.txt:$lineno: platform_test.sh may not be quarantined: it wraps the whole platform suite, so quarantining it would let any platform test failure through" >&2; bad=1; continue
        elif [ "$base" = "run_all.sh" ]; then
            echo "quarantine: tests/quarantine.txt:$lineno: run_all.sh is not a test file" >&2; bad=1; continue
        fi
        case "$seen" in *" $fpath "*)
            echo "quarantine: tests/quarantine.txt:$lineno: '$fpath' is listed twice" >&2; bad=1; continue ;; esac
        seen="$seen$fpath "
        if ! [[ "$fissue" =~ $re_issue1 || "$fissue" =~ $re_issue2 ]]; then
            echo "quarantine: tests/quarantine.txt:$lineno: issue '$fissue' must be #<number> or https://github.com/<owner>/<repo>/issues/<number>" >&2; bad=1; continue
        fi
        if ! q_parse_date "$fdate"; then
            echo "quarantine: tests/quarantine.txt:$lineno: expiry '$fdate' is not a real YYYY-MM-DD date" >&2; bad=1; continue
        fi
        if [ "$QD" -lt "$todayn" ]; then
            echo "quarantine: tests/quarantine.txt:$lineno: '$fpath' expired on $fdate (today is $today): fix the test or renew the entry with a new date" >&2; bad=1; continue
        elif [ "$QD" -gt $((todayn + 14)) ]; then
            echo "quarantine: tests/quarantine.txt:$lineno: expiry $fdate is more than 14 days after today ($today); the limit is 14 days" >&2; bad=1; continue
        fi
        QUAR="$QUAR$fpath $fissue $fdate
"
    done < "$QFILE"
    [ "$bad" = 0 ]
}

q_find() { # q_find <name>: sets QI to "<issue> <date>" if the file is on the list
    local l
    QI=""
    while IFS= read -r l; do
        case "$l" in "tests/$1 "*) QI="${l#* }"; return 0 ;; esac
    done <<< "$QUAR"
    return 1
}

# Replaces the final verdict when --retry-failed-once is given. Re-runs only the
# files that failed or timed out in the first round, once, in the first-round
# order; the first-round counts are not touched. Always exits.
retry_and_conclude() {
    local b rc n passed2="" failed2="" unq="" nflaky=0 issue date
    # A round that did not run every file cannot be rescued by a retry.
    [ "$total" = "$expected" ] || exit 1
    [ -n "$FAILED_LIST" ] || { echo "all green"; exit 0; }
    n=$(grep -c . <<<"$FAILED_LIST")
    echo
    echo "== retry: re-running $n file(s) once =="
    while IFS= read -r b; do
        [ -n "$b" ] || continue
        printf 'retry %s ... ' "$b"
        clocked "$PER_TEST_TIMEOUT" bash "$ROOT/tests/$b" </dev/null >"$LOGDIR/$b.retry.log" 2>&1
        rc=$?
        case "$rc" in
            0)   echo ok;      passed2="$passed2$b
" ;;
            124) echo TIMEOUT; failed2="$failed2$b
" ;;
            *)   echo FAIL;    failed2="$failed2$b
" ;;
        esac
    done <<< "$FAILED_LIST"
    echo
    if [ -n "$failed2" ]; then
        echo "== FAILED twice =="
        while IFS= read -r b; do
            [ -n "$b" ] || continue
            echo "FAILED $b"
            tail -25 "$LOGDIR/$b.retry.log"
            echo
        done <<< "$failed2"
    fi
    if [ -n "$passed2" ]; then
        echo "== FLAKY (failed the first run, passed the retry) =="
        while IFS= read -r b; do
            [ -n "$b" ] || continue
            nflaky=$((nflaky + 1))
            if q_find "$b"; then
                issue="${QI% *}"; date="${QI##* }"
                echo "FLAKY $b  quarantined $issue until $date"
            else
                echo "FLAKY $b  NOT in tests/quarantine.txt"
                unq="$unq${unq:+ }$b"
            fi
        done <<< "$passed2"
        echo
    fi
    if [ -n "$unq" ]; then
        echo "FLAKY not quarantined: $unq. Fix the test, or add one line per file to tests/quarantine.txt: tests/<name>.sh <issue> <YYYY-MM-DD> (at most 14 days out)." >&2
    fi
    [ -z "$failed2" ] && [ -z "$unq" ] || exit 1
    echo "green after retry: $nflaky quarantined flaky file(s)"
    exit 0
}

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

# Before any test starts, so an expired entry turns the run red even when
# nothing else failed.
if [ "$RETRY" = 1 ] || [ "$CHECKQ" = 1 ]; then
    quarantine_check || exit 1
    if [ "$CHECKQ" = 1 ]; then echo "tests/quarantine.txt ok"; exit 0; fi
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
if [ "$RETRY" = 0 ]; then
[ "$failed" = 0 ] && [ "$timedout" = 0 ] && [ "$total" = "$expected" ] || exit 1
else retry_and_conclude; fi
echo "all green"
