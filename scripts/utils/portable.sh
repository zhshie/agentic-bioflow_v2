#!/bin/bash
# GNU-ok-file: this is where the GNU spellings live, guarded by a platform test.
#
# Nothing existing: bash itself ships no cross-platform stat/timeout/readlink
# -f shim; this is that shim, kept in the one place described below.
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

# Whether a file is readable only by the person it belongs to - and, when that
# cannot be established, saying so instead of guessing.
#
# Prints "<state> <evidence>": state is private, exposed or unknown, and the
# rest of the line is the phrase callers drop into their own sentences, so the
# finding and the wording for it are derived in one place.
#
# On Unix the mode is the answer. On Windows it is not even evidence. Git Bash
# mounts NTFS without `acl`, so the permission bits it prints are manufactured,
# and PITFALLS 16j measured a file created in the user's own profile - the
# location docs/SETTINGS.md sends everyone to - reading back as 644 while
# nothing but the owner could actually open it. A check that refused on that
# number was protecting against a filesystem it had not looked at. Asking the
# operating system that actually decides is both more accurate and, on exFAT or
# a cloud-drive folder with no ACLs at all, stricter than the mode ever was.
file_privacy() {
    local m
    if [ "$(plat_kind)" = msys ]; then _win_privacy "$1"; return 0; fi
    m="$(stat_mode "$1")"
    case "$m" in
        600) printf 'private mode 600\n' ;;
        "")  printf 'unknown its mode could not be read\n' ;;
        *)   printf 'exposed mode %s, should be 600\n' "$m" ;;
    esac
}

# Being on a file's ACL says nothing about these three. SYSTEM and the local
# Administrators group can read anything on the machine whatever an ACL says,
# so refusing over them would refuse every file on Windows; CREATOR OWNER is an
# inheritance placeholder rather than a person.
_WIN_SIDS_OK='S-1-5-18 S-1-5-32-544 S-1-3-0'

# SIDs, never account names. `icacls` prints localised names - BUILTIN\Administrators
# is VORDEFINIERT\Administratoren on a German install - and a permission check
# that depends on the display language fails open in a country nobody tested it
# in. GetAccessRules with a SecurityIdentifier argument also cannot throw on an
# account that no longer resolves, which Translate() can.
_win_acl_script() {   # <windows-path> -> the PowerShell to run
    local p
    # A single-quoted PowerShell string ends at the first quote, and doubling
    # is how PowerShell escapes one. A Windows path may legally contain it.
    p=$(printf '%s' "$1" | sed "s/'/''/g")
    printf '%s' "\$ErrorActionPreference='Stop';\$p='$p';\$a=Get-Acl -LiteralPath \$p;\
'me='+[Security.Principal.WindowsIdentity]::GetCurrent().User.Value;\
'owner='+\$a.GetOwner([Security.Principal.SecurityIdentifier]).Value;\
\$a.GetAccessRules(\$true,\$true,[Security.Principal.SecurityIdentifier])|\
ForEach-Object{if(\$_.AccessControlType -eq 'Allow'){'ace='+\$_.IdentityReference.Value}}"
}

_win_privacy() {
    local f="$1" wpath out line me="" owner="" aces="" sid
    command -v powershell.exe >/dev/null 2>&1 || {
        printf 'unknown %s\n' "this shell's mode is not how Windows decides, and powershell.exe is not here to ask"
        return 0
    }
    wpath="$(cygpath -w "$f" 2>/dev/null)"
    [ -n "$wpath" ] || wpath="$f"
    # tr -d '\r': a real powershell.exe ends every line with CRLF, and a SID
    # carrying a trailing carriage return matches nothing - which would make
    # every comparison below fail open.
    out="$(powershell.exe -NoProfile -NonInteractive -Command "$(_win_acl_script "$wpath")" 2>/dev/null | tr -d '\r')"
    while IFS= read -r line; do
        case "$line" in
            me=*)    me="${line#me=}" ;;
            owner=*) owner="${line#owner=}" ;;
            ace=*)   aces="$aces ${line#ace=}" ;;
        esac
    done <<EOF
$out
EOF
    # An answer that never arrived is not an empty ACL. Reading it as one would
    # mean "nobody else has access", which is the single wrong answer here that
    # would also be silent.
    if [ -z "$me" ] || [ -z "$aces" ]; then
        printf 'unknown %s\n' "this shell's mode is not how Windows decides, and Windows did not answer"
        return 0
    fi
    for sid in $aces; do
        case " $_WIN_SIDS_OK $me $owner " in
            *" $sid "*) ;;
            *) printf 'exposed Windows also grants access to %s\n' "$sid"; return 0 ;;
        esac
    done
    printf 'private Windows grants it to you alone\n'
}

# Cloud-sync folder name matching. T30 left exactly one response to it: a
# warning. The root (docs/SETTINGS.md) is expected to be a synced folder -
# that is what "follows you between machines" means in practice - so refusing
# one would refuse the design. What the old refusal protected, the token, is
# addressed where the token is defined instead (scripts/settings.sh,
# token_file), by naming the trade rather than pretending it away: a synced
# folder holds mode 600 perfectly normally, and the sync client uploads the
# file to a third party regardless of its permission bits.
#
# Not a complete list, and every caller that reports this says so: any folder
# that syncs anywhere is the same risk, and a list of sync products can never
# be complete.
looks_cloud_synced() {   # looks_cloud_synced <path> -> 0 if it looks synced
    case "$1" in
        *OneDrive*|*Dropbox*|*"Google Drive"*|*GoogleDrive*|*"Library/Mobile Documents"*|*Box*|*Nextcloud*)
            return 0 ;;
    esac
    return 1
}

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

# Which interpreter actually runs, not which name resolves. PITFALLS 20c:
# Git Bash puts a Microsoft Store stub on PATH as `python3` - `command -v
# python3` finds it and lies; running it prints nothing and exits 49. The fix
# is the one 20c already gives - try each candidate for real and keep the
# first one that runs, rather than asking PATH which names exist.
#
# `python3` first because that is the POSIX-side convention and is right
# everywhere but Windows; `python` and `py` are the names an ordinary
# python.org or working Microsoft Store install actually publishes there.
# This cannot and does not try to tell a working install from a broken one by
# any means other than actually running it - which is the whole fix.
#
# Lives here rather than in scripts/require_python.sh: that file solves a
# different problem, this cluster's own `/usr/bin/python3` being a reserved
# RHEL interpreter this account may not run (PITFALLS 16d) - one fixed name,
# a site-specific diagnosis, used only on the site through on_site.sh
# --script. This is the cross-platform "which of several names actually
# works on THIS machine" question, the same class of problem stat_mode() and
# resolve_link() above answer, so it belongs beside them.
PICK_PYTHON_CANDIDATES="python3 python py"
pick_python() {
    local candidate
    for candidate in $PICK_PYTHON_CANDIDATES; do
        if "$candidate" -c 'pass' >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
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
