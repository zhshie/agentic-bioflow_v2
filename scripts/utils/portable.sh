#!/bin/bash
# GNU-ok-file: this is where the GNU spellings live, guarded by a platform test.
#
# One place that knows how this machine differs from the one the scripts were
# written on. macOS ships a BSD userland and bash 3.2; Git Bash ships MSYS.
# Nine call sites had each answered that question for themselves - by not
# asking it - and four of the resulting failures were silent: a token whose
# mode was never checked, a session hook that reported nothing in flight, a
# delete guard that stopped resolving symlinks, an upload that displayed 0 B.
#
# Source it, do not exec it. Callers that are safety nets must NOT source it:
# a gate that disappears when a helper is missing is worse than one that was
# never written (the launch_trigger.sh lesson), so hooks/confirm_cleanup.sh
# inlines its own three lines instead.
#
# tests/portable_userland.sh forbids these spellings everywhere else, which is
# what stops the tenth call site from being discovered by whoever installs on a
# Mac next.

# linux | macos | msys | other. uname, not $OSTYPE: bash sets OSTYPE itself at
# startup, so it cannot be substituted from the environment and every branch
# below would be untestable.
plat_kind() {
    case "$(uname -s 2>/dev/null)" in
        Linux*)               printf 'linux\n' ;;
        Darwin*)              printf 'macos\n' ;;
        MINGW*|MSYS*|CYGWIN*) printf 'msys\n' ;;
        *)                    printf 'other\n' ;;
    esac
}

# The file's permission bits (octal) and size (bytes), or empty plus a non-zero
# return when neither spelling answers.
#
# The BSD form is NOT simply a fallback to run when the GNU one fails. Measured
# on this machine: `stat -f %Lp <an existing file>` under GNU coreutils means
# --file-system, ignores the format, and prints a five-line block-count report
# - so an unguarded `||` chain would hand a caller that as the permission bits
# the moment the GNU form failed for any reason. It exits non-zero while doing
# it, which is what the `&&` below rests on; the digit test is the second lock,
# because "it returned zero" and "it answered the question asked" are not the
# same claim.
_stat_pick() {   # _stat_pick <gnu-fmt> <bsd-fmt> <file>
    local v
    v=$(stat -c "$1" "$3" 2>/dev/null) && case "$v" in
        ''|*[!0-9]*) ;; *) printf '%s\n' "$v"; return 0 ;;
    esac
    v=$(stat -f "$2" "$3" 2>/dev/null) && case "$v" in
        ''|*[!0-9]*) ;; *) printf '%s\n' "$v"; return 0 ;;
    esac
    return 1
}
stat_mode() { _stat_pick %a %Lp "$1"; }
stat_size() { _stat_pick %s %z  "$1"; }

# A whole tree's size in bytes. `du -sb` is GNU-only; `du -sk` is POSIX and
# every platform has it, and kilobytes are finer than any caller here needs -
# the two readers compare against a megabyte limit and print a human size.
dir_bytes() {
    local kb; kb=$(du -sk "$1" 2>/dev/null | awk 'NR==1{print $1}')
    [ -n "$kb" ] || { printf '0\n'; return 1; }
    printf '%s\n' "$((kb * 1024))"
}

# The path with every symlink resolved, or empty when it cannot be resolved.
# BSD readlink had no -f until macOS 12.3, and returning the input unchanged
# would be worse than returning nothing: a delete guard that judges by the
# destination would then judge the link's own name and pass.
resolve_link() {
    readlink -f "$1" 2>/dev/null && return 0
    # BSD: walk it with the shell. cd resolves every directory component, and
    # readlink without -f resolves the last one, one hop at a time.
    local p="$1" n=0 d b
    while [ -L "$p" ] && [ "$n" -lt 40 ]; do
        d=$(dirname "$p"); b=$(readlink "$p") || return 1
        case "$b" in /*) p="$b" ;; *) p="$d/$b" ;; esac
        n=$((n + 1))
    done
    d=$(cd "$(dirname "$p")" 2>/dev/null && pwd -P) || return 1
    printf '%s\n' "${d%/}/$(basename "$p")"
}

# Run a command under a time limit. `timeout` is GNU coreutils and is simply
# not on a stock macOS; Homebrew installs it as `gtimeout`. With neither, a
# shell watchdog - because the alternative is no limit at all, and the two
# callers that matter are a session hook that would hang a conversation and an
# ssh call against a master that may never answer.
CLOCKED_BIN="${CLOCKED_BIN-$(command -v timeout || command -v gtimeout || true)}"
clocked() {
    local secs="$1"; shift
    [ "$secs" = 0 ] && { "$@"; return $?; }
    if [ -n "$CLOCKED_BIN" ]; then "$CLOCKED_BIN" "$secs" "$@"; return $?; fi

    "$@" &
    local pid=$! rc=0
    # >/dev/null or the watchdog holds the pipe of any $(clocked ...) for the
    # whole timeout, making every timed call take exactly `secs`.
    ( sleep "$secs"; kill -TERM "$pid" 2>/dev/null ) >/dev/null 2>&1 &
    local wd=$!
    # 2>/dev/null: when the watchdog kills the child, the shell announces
    # "Terminated" on its own stderr. `timeout` prints nothing, and a caller
    # should not be able to tell which of the two ran.
    wait "$pid" 2>/dev/null; rc=$?
    # Still alive means it never fired, so the command finished on its own.
    # Gone means it fired: answer 124, the code `timeout` uses, so callers do
    # not have to know which of the two ran.
    if kill -0 "$wd" 2>/dev/null; then kill -TERM "$wd" 2>/dev/null
    else rc=124; fi
    wait "$wd" 2>/dev/null
    return "$rc"
}
