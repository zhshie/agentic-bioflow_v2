#!/bin/bash
# Read one value from the deployment's settings file.
#
# Not a YAML parser (PyYAML, yq): deliberately reads `key: value` and stops at
# the first `#` - see the note further down about what that rules out.
#
# Everything that identifies a person or a site - the account compute time is
# billed to, the workspace, where the agent's Java lives - belongs in one file
# outside the repository, mode 600. Baking any of it into a script makes the
# script one person's (PRINCIPLES.md, invariant 3), and on a cluster where home
# directories are mode 700 it also makes it unreadable to everyone else.
#
#   setting <key>              value, or empty
#   setting <key> <default>    value, or the default
#   setting <key> --required   value, or exit 1 saying which key is missing
#   settings.sh --summary      what this deployment is configured as and where
#                              that lives. Never the token's value.
#
# Deliberately not a YAML parser: this reads `key: value` and stops at the first
# `#`, which is all the settings file is allowed to be. A settings file that
# needs a real parser has grown into something it should not be.
set -uo pipefail

# How this machine differs from the one these scripts were written on, decided
# in one place (scripts/utils/portable.sh). Sourced here rather than in each
# caller because nearly everything already sources this file.
#
# Fail-closed, and loudly: without it `stat_mode` is simply undefined, so the
# token's permission check would evaluate to nothing and report a
# world-readable token as fine. A missing guard has to be an error, not a
# quieter version of the same output.
_PORTABLE="$(dirname "${BASH_SOURCE[0]}")/utils/portable.sh"
if [ -r "$_PORTABLE" ]; then
    . "$_PORTABLE"
else
    echo "missing $_PORTABLE - this deployment is incomplete." >&2
    return 1 2>/dev/null || exit 1
fi

# --- Where the file is -------------------------------------------------------
# Three places, most explicit first.
#
# `LAB_SETTINGS_FILE`, when set, is the answer outright and nothing else is
# searched: it is what a deployment driven from the user's own machine points
# at, and a value that could quietly resolve somewhere else would let `setting`
# read one file while `set_setting` writes another.
#
# The third place fixes a real failure. The chain used to be the first two, and
# with neither variable set it produced the literal string `/_personal/env.yaml`
# - unreadable, but not an empty string. So every read returned its default in
# silence, the session hook stopped at its readability check, and a machine that
# was fully set up looked exactly like one that had never run setup. A member
# ended up grepping the filesystem for their own config. `$XDG_CONFIG_HOME` is
# where someone would look without being told, and is already this repo's habit
# for a location it has to invent (scripts/fetch.sh).
SETTINGS_CANDIDATES=()
if [ -n "${LAB_SETTINGS_FILE:-}" ]; then
    SETTINGS_CANDIDATES=("$LAB_SETTINGS_FILE")
else
    [ -n "${LAB_RUNS_DIR:-}" ] && SETTINGS_CANDIDATES+=("${LAB_RUNS_DIR%/}/_personal/env.yaml")
    SETTINGS_CANDIDATES+=("${XDG_CONFIG_HOME:-${HOME:-}/.config}/agentic-bioflow/env.yaml")
fi

SETTINGS_FILE=""
SETTINGS_FOUND=0
for _c in "${SETTINGS_CANDIDATES[@]}"; do
    if [ -r "$_c" ]; then SETTINGS_FILE="$_c"; SETTINGS_FOUND=1; break; fi
done
# Finding nothing is not the same as having nowhere to write: setup creates the
# file through `--set`, and the first candidate is where it belongs.
[ -n "$SETTINGS_FILE" ] || SETTINGS_FILE="${SETTINGS_CANDIDATES[0]}"
unset _c

# --- the portable folder (T23) ----------------------------------------------
# `settings.sh --adopt <path>` writes a small pointer file naming a portable
# folder (docs/SETTINGS.md) - deliberately a FILE, never an environment
# variable: this repo's worst settings-file bugs (16j/16k, PITFALLS 25) were
# all caused by a variable set in one shell's startup file and not another's,
# and a file at the one location every shell agrees on ($HOME) has none of
# that problem. Always the XDG location, never LAB_RUNS_DIR-relative: the
# pointer is this MACHINE's own choice of which portable folder it uses, not
# a site-side thing that would belong under LAB_RUNS_DIR/_personal.
#
# Resolution order this gives `setting()` below: pointer file -> portable
# settings (the keys docs/SETTINGS.md marks portable) -> this machine's own
# local settings file (SETTINGS_FILE, above - machine-derived keys, or every
# key at all on a machine that has never adopted anything).
PORTABLE_POINTER="${XDG_CONFIG_HOME:-${HOME:-}/.config}/agentic-bioflow/portable_root"
PORTABLE_ROOT=""
PORTABLE_SETTINGS_FILE=""
# Same precedence as every other override in this file (site_shaped_write_
# refusal, looks_synced_write_refusal): an explicit LAB_SETTINGS_FILE names
# exactly one file and wins outright, so a caller pointing at a specific
# fixture is never quietly joined by whatever pointer file happens to sit at
# this machine's real $HOME - which matters for this repo's own test suite
# as much as for a real deployment.
if [ -z "${LAB_SETTINGS_FILE:-}" ] && [ -r "$PORTABLE_POINTER" ]; then
    PORTABLE_ROOT="$(head -1 "$PORTABLE_POINTER" 2>/dev/null | tr -d '\r\n')"
    if [ -n "$PORTABLE_ROOT" ] && [ -r "${PORTABLE_ROOT%/}/config/env.yaml" ]; then
        PORTABLE_SETTINGS_FILE="${PORTABLE_ROOT%/}/config/env.yaml"
        SETTINGS_FOUND=1
    fi
fi

# The health check: called wherever a caller wants to explain a gap rather
# than silently fall through to the local file's own default. A portable
# folder that cannot be read right now is not the same failure as one never
# adopted, and the two must not read alike - a member watching a cloud folder
# finish syncing needs to hear that, not "run setup".
portable_missing_reason() {
    [ -n "$PORTABLE_ROOT" ] || return 1
    [ -z "$PORTABLE_SETTINGS_FILE" ] || return 1
    echo "This machine points at a portable folder (via $PORTABLE_POINTER):" >&2
    printf '  %s\n' "$PORTABLE_ROOT" >&2
    if [ ! -e "$PORTABLE_ROOT" ]; then
        echo "  which does not exist here yet. A common cause: a cloud-sync folder" >&2
        echo "  that has not finished syncing to this machine - wait for it, or check" >&2
        echo "  the sync client." >&2
    elif [ ! -r "${PORTABLE_ROOT%/}/config/env.yaml" ]; then
        echo "  ${PORTABLE_ROOT%/}/config/env.yaml is missing or unreadable." >&2
    fi
    return 0
}

# What the search covered. An error that names one unreadable path tells the
# reader nothing about where to put a file instead - which is the whole
# difference between "not set up" and "set up somewhere I did not look".
settings_missing() {
    local c
    echo "No settings file. Looked in:"
    for c in "${SETTINGS_CANDIDATES[@]}"; do printf '  %s\n' "$c"; done
    if [ -n "${LAB_SETTINGS_FILE:-}" ]; then
        echo "  (LAB_SETTINGS_FILE names that one, so nowhere else was searched)"
    elif [ -z "${LAB_RUNS_DIR:-}" ]; then
        echo "  (LAB_RUNS_DIR is not set, so no run area was searched)"
    fi
    steered_past_a_real_file
    shell_blind_spot
    # This used to end "...or point LAB_SETTINGS_FILE at an existing one",
    # which recommends the hazard: all three ways this message gets printed
    # wrongly are caused by a variable being set, and the default with no
    # variables at all is already correct on every platform.
    echo "Run setup to create one. With no variables set it writes to"
    printf '  %s\n' "$(xdg_default)"
    echo "which every shell on every platform can find, because it needs none."
    return 0
}

# The conventional place, worked out the same way the candidate list does it.
xdg_default() {
    printf '%s\n' "${XDG_CONFIG_HOME:-${HOME:-}/.config}/agentic-bioflow/env.yaml"
}

# A variable can steer the search away from a file that is sitting right there.
# LAB_SETTINGS_FILE wins outright and searches nowhere else, so a member who
# set it once - to a path that has since moved, or that only exists in another
# shell's home - gets a report listing one absent path while their real
# settings file is untouched at the default. That reads exactly like "never set
# up", and it is the one form of this failure a person can fix in one command.
steered_past_a_real_file() {
    local d; d="$(xdg_default)"
    [ -r "$d" ] || return 0
    # No second condition, deliberately. The default is always in the candidate
    # list unless LAB_SETTINGS_FILE short-circuited it, and a readable
    # candidate means the file was FOUND and this function never runs. So
    # arriving here with a readable file at the default already proves the
    # search was steered - a guard checking that again could never fail, and an
    # assertion that cannot fail is worse than none (PITFALLS 21).
    echo "  BUT a settings file exists at $d"
    echo "  and the search never reached it. Unset LAB_SETTINGS_FILE to use it."
}

# Windows puts two homes on one machine and only one of them is the one setup
# used. Git Bash's $HOME is the Windows profile; a deployment set up in WSL -
# which commands/setup.md requires, because PITFALLS 16b measured that only WSL
# can hold the site connection - sits in a filesystem this shell cannot reach,
# and WSL's ~/.bashrc, where LAB_SETTINGS_FILE is exported, is never read here.
# So the candidate list above is a true answer to the wrong question: every path
# in it is genuinely absent, and the file is genuinely there. Without this note
# "no settings file" is indistinguishable from "never set up", which is exactly
# the confusion the third candidate was added to end - one machine over.
#
# The right move is named here too, because the obvious one is wrong: copying
# the settings file somewhere Git Bash can see it makes --summary green in a
# shell this version still refuses to drive the site from (on_site.sh), and
# where chmod 600 on the Windows filesystem does not hold - trading a loud
# failure for a quiet one and dropping the token's only protection on the way.
#
# uname, not $OSTYPE: bash sets OSTYPE itself at startup, so it cannot be
# substituted from the environment and the branch would be untestable.
shell_blind_spot() {
    case "$(uname -s 2>/dev/null)" in
        MINGW*|MSYS*|CYGWIN*) ;;
        *) return 0 ;;
    esac
    echo "  This shell is Git Bash/MSYS, where HOME is ${HOME:-unset}."
    echo "  A deployment set up in WSL is not visible from here: different home,"
    echo "  different filesystem, and WSL's ~/.bashrc is never read in this shell."
    echo "  'Not found' here does not mean 'not set up'."
    echo "  None of that asks you to move: the project folder you already work"
    echo "  in does not have to move, and neither does this window. The one call"
    echo "  that needs WSL borrows it by itself (PITFALLS 16b, 16g)."
    echo "  Run setup here. It writes a settings file this shell can find, and"
    echo "  refuses outright if the file would not be private to you - settings.sh"
    echo "  reads that back rather than trusting that chmod did anything."
    echo "  The mode this shell prints for a Windows file is manufactured and is"
    echo "  not consulted (PITFALLS 16j): Windows itself is asked who can open the"
    echo "  file, and a refusal here means it named more people than you."
    echo "  A deployment already set up inside WSL stays exactly where it is;"
    echo "  this shell simply cannot read it."
}

# The token file, worked out in one place. preflight.sh, the session hook,
# agent_ctl.sh and ce_apply.sh each used to derive this for themselves, and two
# of them anchored it on the settings file while two anchored it on
# $LAB_RUNS_DIR. With a third place for the settings file to live, those two
# answers start differing for real.
#
# The settings file's directory is the anchor: docs/SETTINGS.md says the pair
# travel together. The other candidate directories are tried after it for the
# one case where they legitimately part - under `reach: ssh` the settings file
# stays on the user's machine and never crosses, but agent_ctl.sh still runs on
# the site and still needs the token left beside the run area there.
token_file() {
    if [ -n "${SEQERA_TOKEN_FILE:-}" ]; then printf '%s\n' "$SEQERA_TOKEN_FILE"; return 0; fi
    local c d first=""
    for c in "$SETTINGS_FILE" "${SETTINGS_CANDIDATES[@]}" \
             "${LAB_RUNS_DIR:+${LAB_RUNS_DIR%/}/_personal/env.yaml}"; do
        [ -n "$c" ] || continue
        d="$(dirname "$c")/.seqera_token"
        [ -n "$first" ] || first="$d"
        if [ -r "$d" ]; then printf '%s\n' "$d"; return 0; fi
    done
    printf '%s\n' "$first"
}

# One derivation of "is the WSL bridge in play", for on_site.sh, fetch.sh,
# push.sh, reset_master.sh and detect_conditions.sh. Those five worked it out
# four separate times when the bridge first landed, and two of the copies
# already disagreed: detect_conditions.sh probed `wsl.exe` alone and never
# read `site_bridge`, so a member who had turned the bridge off was told this
# machine was `supported` while on_site.sh refused every call it made. That is
# exactly the failure token_file() above exists to prevent, one subsystem over
# - and reset_master.sh, which never learned about the bridge at all, was
# telling people to close a master at a path nothing had opened.
#
# A function, never run at source time: the probe costs a process spawn and
# nearly everything in this repo sources this file.
bridge_kind() {   # -> wsl | none
    case "$(uname -s 2>/dev/null)" in
        MINGW*|MSYS*|CYGWIN*) ;;
        # WSL is a Windows-only concept, so there is nothing to detect
        # elsewhere - and a stray `wsl.exe` on some other PATH must never
        # change what these scripts do there.
        *) printf 'none\n'; return 0 ;;
    esac
    # Probed from a directory WSL can map, for the reason
    # scripts/utils/wsl_ssh.sh gives at length: a cloud-drive working directory
    # makes wsl.exe complain before it runs anything. Measured to be only a
    # warning there - but this probe reads an exit code, and a probe whose
    # answer depends on a warning staying a warning would turn "the bridge is
    # missing" into a refusal on a machine where WSL is working fine.
    #
    # The setting wins over the probe, in both directions: `site_bridge: none`
    # turns a working bridge off, which is what makes the refusal path
    # reachable on a machine that has WSL. So it is read FIRST, and the probe
    # only runs when there is no setting to answer with. It used to run on
    # every call regardless and then be overruled - and in the 2.15.0 Windows
    # verification one call spent 312 s inside it.
    #
    # </dev/null and a time limit on the probe for the same reason: wsl.exe
    # reads the stdin it inherits, and from a harness whose stdin is a pipe
    # that can hold it indefinitely. A WSL that has not answered in 20 s -
    # a cold start takes a few - is reported as no bridge, which is what the
    # caller would have to act on anyway.
    local _set _default=none
    _set="$(setting site_bridge "")"
    if [ -n "$_set" ]; then printf '%s\n' "$_set"; return 0; fi
    command -v wsl.exe >/dev/null 2>&1 \
        && ( cd "${HOME:-/}" 2>/dev/null || cd / 2>/dev/null || :
             clocked 20 wsl.exe -e true </dev/null >/dev/null 2>&1 ) \
        && _default=wsl
    printf '%s\n' "$_default"
}

# The ssh binary that goes with that answer. PITFALLS 16b/16g: Git Bash's own
# ssh cannot open a session over a master, WSL's can, and scripts/utils/
# wsl_ssh.sh is that one call - a script rather than a function because both
# `$SSH` and rsync's `-e` need something passable as a command string.
site_ssh_bin() {   # site_ssh_bin <bridge-kind> -> path or 'ssh'
    if [ "${1:-none}" = wsl ]; then
        printf '%s\n' "$(dirname "${BASH_SOURCE[0]}")/utils/wsl_ssh.sh"
    else
        printf 'ssh\n'
    fi
}

# The ControlPath default that goes with it. Under the bridge the master lives
# inside WSL, so the path has to be one WSL's OWN shell expands: left as the
# literal '~/...' it crosses wsl.exe unexpanded and resolves against WSL's
# home, rather than a Windows-shaped $HOME this shell would have expanded
# first. Either way it must not contain ':' - illegal in an NTFS filename,
# which is why the usual '%r@%h:%p' form cannot be used here (PITFALLS 16b).
site_control_path_default() {   # site_control_path_default <bridge-kind>
    if [ "${1:-none}" = wsl ]; then
        printf '%s\n' '~/.ssh/cm-%r-%h-%p'
    else
        printf '%s\n' "${HOME:-}/.ssh/cm-%r-%h-%p"
    fi
}

# --- T29: the local side's project layout -----------------------------------
# One place, so scripts/init_workspace.sh (which builds these directories)
# and scripts/where.sh (which answers "where are they" for commands/
# downstream.md and commands/finish.md) compute the SAME path by
# construction, never by a test asserting two independent formulas happen to
# agree.
#
# Two decisions:
#
# 1. Old layout (<local_root>/<seqera_user>/projects/<project>/...) or new
#    (<local_root>/projects/<project>/..., no <seqera_user> layer - matching
#    the portable folder's own shape, T23/docs/SETTINGS.md) - decided PER
#    PROJECT, by whether the old path already exists on this machine.
#    docs/SETTINGS.md: "Migration: none" - a project already living at the
#    old path keeps living there; only a brand new project gets the new one.
# 2. `analysis/` and `submission/` specifically move into the portable
#    folder instead, once one is adopted (T23) - never `rawdata/`/`runs/`/
#    `results/`, which stay local because raw and re-fetchable data must
#    never ride a cloud sync (docs/SETTINGS.md, T21's cloud_sync_caution).

# local_layout_is_old <root> <user> <project> -> 0 (true) if the OLD,
# <user>-layered path already exists for this project.
local_layout_is_old() {
    [ -n "${2:-}" ] && [ -n "${3:-}" ] && [ -d "${1%/}/$2/projects/$3" ]
}

# The base directory for rawdata/runs (and, with no portable folder,
# analysis/submission too): <root>/<user>/projects/<project> for a project
# that already lives there, <root>/projects/<project> for a new one.
local_project_base() {   # local_project_base <root> <user> <project>
    local root="${1%/}" user="${2:-}" project="${3:-}"
    if local_layout_is_old "$root" "$user" "$project"; then
        printf '%s\n' "$root/$user/projects/$project"
    else
        printf '%s\n' "$root/projects/$project"
    fi
}

# Where analysis/ and submission/ actually live: the portable folder once one
# is adopted (never a <seqera_user> layer there either - T23's own shape), or
# alongside rawdata/runs otherwise, at whichever base local_project_base just
# decided.
local_analysis_base() {   # local_analysis_base <root> <user> <project>
    if [ -n "$PORTABLE_ROOT" ]; then
        printf '%s\n' "${PORTABLE_ROOT%/}/projects/${3:-}"
    else
        local_project_base "$1" "$2" "$3"
    fi
}

# The one place a `key: value` line is actually pulled out of a file -
# unchanged from before T23, just factored out so `setting()` can try it
# against two files in order instead of duplicating the sed pipeline.
_read_key() {   # _read_key <file> <key>
    [ -r "$1" ] || return 0
    sed -n "s/^[[:space:]]*${2}[[:space:]]*:[[:space:]]*//p" "$1" \
        | sed 's/[[:space:]]*#.*$//; s/[[:space:]]*$//' | head -1
}

setting() {
    local key="$1" fallback="${2:-}" val=""
    # Portable first (T23): the values a person carries between machines
    # take precedence over whatever a machine-local file happens to also
    # have for the same key - the whole point of adopting is that the
    # portable copy is now the one that is current.
    [ -n "$PORTABLE_SETTINGS_FILE" ] && val="$(_read_key "$PORTABLE_SETTINGS_FILE" "$key")"
    [ -n "$val" ] || val="$(_read_key "$SETTINGS_FILE" "$key")"
    if [ -n "$val" ]; then printf '%s\n' "$val"; return 0; fi
    if [ "$fallback" = "--required" ]; then
        if [ -n "$PORTABLE_SETTINGS_FILE" ]; then
            echo "missing '$key' in $PORTABLE_SETTINGS_FILE or $SETTINGS_FILE." >&2
        elif [ "$SETTINGS_FOUND" = 1 ]; then
            echo "missing '$key' in $SETTINGS_FILE." >&2
        else
            echo "missing '$key', and there is no settings file to read it from." >&2
            settings_missing >&2
        fi
        portable_missing_reason >&2
        echo "Ask the user for it - never guess it, and never copy it from another member." >&2
        return 1
    fi
    printf '%s\n' "$fallback"
}

# Write one value back. Onboarding discovers things - a free port, where the
# agent's Java ended up - and the member should not have to transcribe them.
# Rewrites the key in place if present so comments and order survive; appends
# otherwise. Creates the file mode 600, because everything in it is either
# personal or an access path.
set_setting() {
    local key="$1" val="$2" created=0
    [ -n "${SETTINGS_FILE:-}" ] || { echo "no settings file location known" >&2; return 1; }
    mkdir -p "$(dirname "$SETTINGS_FILE")"
    if [ ! -e "$SETTINGS_FILE" ]; then
        created=1
        : > "$SETTINGS_FILE"
        chmod 600 "$SETTINGS_FILE"
    fi
    # awk, not python3, and ENVIRON rather than `awk -v`. PITFALLS 20c: Git
    # Bash's python3 is a Microsoft Store stub that sits on PATH, prints
    # nothing, and exits 49 - this was the one place in the whole repo that
    # still needed a real python3 to exist, to rewrite a single `key: value`
    # line. awk is POSIX and Git Bash ships it - tests/portable_userland.sh
    # holds this file to POSIX awk, so no gensub, no GNU-only extension.
    # Still not a real YAML parser, for the same reason `setting()` above
    # is not one (see this file's own header): the settings file is only
    # ever `key: value` plus an optional trailing comment, by design.
    #
    # ENVIRON, not `awk -v key=... val=...`: POSIX has awk interpret
    # backslash escapes inside a `-v` assignment the same way it would
    # inside a string literal, so a value with a bare backslash in it - a
    # Windows path typed without forward slashes - would come out mangled.
    # ENVIRON hands awk the same bytes bash already has, untouched.
    local _tmp
    _tmp="$(mktemp "${SETTINGS_FILE}.XXXXXX" 2>/dev/null)" || {
        echo "could not create a temp file beside $SETTINGS_FILE" >&2
        [ "$created" = 1 ] && rm -f "$SETTINGS_FILE"
        return 1
    }
    if ! AWK_KEY="$key" AWK_VAL="$val" awk '
        BEGIN {
            key = ENVIRON["AWK_KEY"]; val = ENVIRON["AWK_VAL"]
            klen = length(key); found = 0
        }
        {
            rest = $0
            sub(/^[ \t]*/, "", rest)
            if (!found && substr(rest, 1, klen) == key) {
                after = substr(rest, klen + 1)
                sub(/^[ \t]*/, "", after)
                if (substr(after, 1, 1) == ":") {
                    found = 1
                    # Keep any trailing comment: it usually says why the
                    # value matters.
                    comment = ""
                    hashpos = index($0, "#")
                    if (hashpos > 0) comment = "  #" substr($0, hashpos + 1)
                    print key ": " val comment
                    next
                }
            }
            print
        }
        END { if (!found) print key ": " val }
    ' "$SETTINGS_FILE" > "$_tmp"
    then
        rm -f "$_tmp"
        [ "$created" = 1 ] && rm -f "$SETTINGS_FILE"
        echo "awk failed to rewrite $SETTINGS_FILE" >&2
        return 1
    fi
    # Content only, not the file itself: `mv` would swap in the temp file's
    # own inode, and mktemp always creates that at mode 600 regardless of
    # umask - which would make the mode-600 check just below pass by
    # accident, on a file that never actually went through the chmod that
    # check exists to verify. Writing into the existing file instead - the
    # same thing the python block's own `open(path, "w")` did - keeps
    # whatever mode the file already had until the explicit chmod decides it.
    cat "$_tmp" > "$SETTINGS_FILE" || {
        rm -f "$_tmp"
        echo "failed to write $SETTINGS_FILE" >&2
        return 1
    }
    rm -f "$_tmp"
    chmod 600 "$SETTINGS_FILE"

    # B1: the chmod above can be *accepted* and change nothing. Measured shape:
    # /mnt/c under WSL without the `metadata` mount option, and exFAT, both take
    # the syscall and silently keep whatever mode the file already had - no
    # error, nothing to catch, and the token that lives beside this file
    # (docs/SETTINGS.md) ends up readable by anyone with access to that
    # filesystem. Reading the mode back is the only way to see that; the chmod
    # returning success proves nothing on its own.
    #
    # An empty stat_mode is a DIFFERENT case, not this one. token_state() (this
    # file, below) already treats "" as "cannot tell" rather than "unsafe" - its
    # own empty-string branch - and a refusal on a machine whose `stat` simply
    # answers differently would be a worse failure than the silent-token bug
    # this exists to catch. So "" carries on here too.
    local _priv _state; _priv="$(file_privacy "$SETTINGS_FILE")"
    _state="${_priv%% *}"
    case "$_state" in
        private|unknown) return 0 ;;
    esac
    # Only a file THIS call created is ours to remove. One that already held a
    # member's real settings must stay - deleting it over a permission problem
    # would be a second, worse failure stacked on the first.
    if [ "$created" = 1 ]; then rm -f "$SETTINGS_FILE"; fi
    refuse_unwritable_mode "$SETTINGS_FILE" "${_priv#* }"
    return 1
}

# What set_setting() calls when chmod 600 did not hold. Same shape as
# refuse_site_shaped_write() below: name the file, say why, name where it
# works instead.
refuse_unwritable_mode() {
    local file="$1" why="$2"
    echo "refusing to write settings to $file: it would not be private to you." >&2
    echo "" >&2
    # 16k: this used to be one paragraph about chmod, because the mode was the
    # only thing it ever looked at. On Windows the mode is not what decides,
    # and saying "chmod 600 was accepted but..." there would be describing a
    # call whose result was never consulted.
    if [ "$(plat_kind)" = msys ]; then
        echo "$why." >&2
        echo "" >&2
        echo "The permission bits Git Bash prints here are manufactured, and this" >&2
        echo "check did not use them: it asked Windows itself who can open the file," >&2
        echo "and Windows named someone beyond you, SYSTEM and the Administrators" >&2
        echo "group. No chmod in this shell can change that answer." >&2
        echo "" >&2
        echo "A file in your own user profile is owner-only by default, which is" >&2
        echo "where this belongs:" >&2
        printf '  %s\n' "$(xdg_default)" >&2
        echo "A drive with no ACLs at all - a USB stick, or a cloud-drive folder -" >&2
        echo "answers this way about every file on it, and is no place for a token." >&2
        return 0
    fi
    echo "chmod 600 was accepted but the file is still $why. /mnt/c under WSL" >&2
    echo "(without the 'metadata' mount option) and exFAT both do this: the chmod" >&2
    echo "call succeeds and silently changes nothing. A token saved there is" >&2
    echo "effectively public to anyone with access to that filesystem." >&2
    echo "" >&2
    echo "Use a location under \$HOME instead, for example" >&2
    printf '  %s\n' "$(xdg_default)" >&2
    echo "which every filesystem this deployment is designed for can hold at mode 600." >&2
}

# D5: `reach: ssh` means this deployment runs on the user's own machine, not
# the site - so `$LAB_RUNS_DIR`, a site path, has no business being exported
# here at all. Measured, not guessed (docs/SETTINGS.md): when it leaks in
# anyway - a stray export left from following the site's own onboarding, say -
# it is the FIRST candidate `set_setting` would write to, nothing at that path
# exists yet, so the search finds nothing anywhere and falls back to writing
# there regardless. The result is a settings file sitting in a directory
# shaped like the site, on this machine, that the next shell - with the
# variable gone again - can never find.
#
# The value being written can settle the question on its own, without relying
# on whatever SETTINGS_FILE happens to already resolve to - which, in exactly
# this failure, is the one thing that cannot be trusted: `--set reach ssh`
# itself is the write this has to catch, before any file saying so exists.
#
#   0  refuse   1  fine, carry on
site_shaped_write_refusal() {
    local key="$1" val="$2" effective_reach
    [ -z "${LAB_SETTINGS_FILE:-}" ] || return 1   # an explicit location wins outright
    [ -n "${LAB_RUNS_DIR:-}" ] || return 1        # nothing here to be steered by
    effective_reach="$(setting reach local)"
    [ "$key" = reach ] && effective_reach="$val"
    [ "$effective_reach" = ssh ] || return 1
    return 0
}

refuse_site_shaped_write() {
    local key="$1"
    echo "refusing to write '$key' here: reach is ssh, so this is the user's own" >&2
    echo "machine, but LAB_RUNS_DIR is set (to '${LAB_RUNS_DIR:-}')." >&2
    echo "" >&2
    echo "On the user's own machine nothing should be set. The settings file" >&2
    echo "belongs at" >&2
    printf '  %s\n' "$(xdg_default)" >&2
    echo "which every shell finds with no variable at all. LAB_RUNS_DIR names a" >&2
    echo "path on the site; left exported here it would make this write land in" >&2
    echo "a directory shaped like the site, but local, which the next shell -" >&2
    echo "with the variable gone again - cannot find (docs/SETTINGS.md)." >&2
    echo "" >&2
    echo "Unset LAB_RUNS_DIR and run this again." >&2
}

# B3: a synced folder is a risk mode 600 cannot catch. The filesystem holds
# 600 there perfectly normally - the check above and set_setting's read-back
# both see nothing wrong - and the sync client uploads the file to a third
# party regardless of its permission bits. Only the path's *name* can hint at
# this; nothing about the file itself does.
#
# Same shape and precedence as site_shaped_write_refusal() above: an explicit
# LAB_SETTINGS_FILE wins outright, because a member who named the location
# chose it.
#
# The name-matching itself is looks_cloud_synced() (scripts/utils/portable.sh)
# - shared with the softer, non-refusing warning T21 added for `local_root`
# and `portable_root`, which are allowed to be synced folders. This function
# is the settings-file-specific decision built on top of that shared match.
#
#   0  refuse   1  fine, carry on
looks_synced_write_refusal() {
    local path="$1"
    [ -z "${LAB_SETTINGS_FILE:-}" ] || return 1   # an explicit location wins outright
    looks_cloud_synced "$path"
}

refuse_synced_write() {
    local path="$1"
    echo "refusing to write settings to $path: the path looks like it is inside a" >&2
    echo "synced folder (OneDrive, Dropbox, Google Drive, iCloud's Library/Mobile" >&2
    echo "Documents, Box, Nextcloud, ...)." >&2
    echo "" >&2
    echo "Those are the names this check recognises, not a complete list - any folder" >&2
    echo "that syncs anywhere is the same risk, and a list of sync products can never" >&2
    echo "be complete. Mode 600 there is perfectly normal and does not help: the sync" >&2
    echo "client uploads the file to a third party regardless of its permission bits," >&2
    echo "and the token in it would go with it." >&2
    echo "" >&2
    echo "Use a location outside any synced folder instead, for example" >&2
    printf '  %s\n' "$(xdg_default)" >&2
    echo "" >&2
    echo "To use this path anyway, set LAB_SETTINGS_FILE to it explicitly - naming the" >&2
    echo "location outright is treated as a deliberate choice." >&2
}

# T21: local_root and (from T23) portable_root are ALLOWED to be a synced
# folder - unlike the settings file above, this only warns. A portable_root
# is explicitly designed to often be one (docs/SETTINGS.md: "can be a cloud
# sync folder, an external drive, any path"), so refusing it the way
# refuse_synced_write() refuses the settings file would refuse the design
# itself. What still has to be said: large files sync slowly and burn quota,
# and the *decrypted* token and the Positron bridge connection file must never
# live here even though the encrypted token (T23: config/.seqera_token.enc)
# is fine to.
#
# Printed to stderr so a caller whose stdout is parsed or shown verbatim
# (init_workspace.sh prints the tree it built on stdout) is never polluted by
# it - the same split every other diagnostic in this file already keeps.
cloud_sync_caution() {   # cloud_sync_caution <path> <setting-key>
    local path="$1" key="$2"
    looks_cloud_synced "$path" || return 0
    echo "note: '$key' ($path) looks like it is inside a synced folder (OneDrive," >&2
    echo "Dropbox, Google Drive, iCloud's Library/Mobile Documents, Box, Nextcloud," >&2
    echo "...) - not a complete list, any folder that syncs anywhere is the same risk." >&2
    echo "That's fine for $key itself, but:" >&2
    echo "  - large files (rawdata, results, container images) sync slowly and will" >&2
    echo "    eat the sync quota - keep those out of it." >&2
    echo "  - the decrypted Seqera token and the Positron bridge connection file must" >&2
    echo "    NEVER be written here (docs/SETTINGS.md)." >&2
    return 0
}

# --- T23: settings.sh --adopt <path> ----------------------------------------
# Points THIS machine at an existing portable folder by writing the pointer
# file PORTABLE_POINTER (above) resolves. Never builds the folder itself -
# scripts/portable_root.sh init does that, on the machine that first sets one
# up; a machine adopting one someone else already built has nothing to build,
# only to point at.
adopt_portable_root() {   # adopt_portable_root <path>
    local path="$1"
    case "$path" in
        /*) ;;
        *) echo "the portable folder location must be an absolute path, not '$path'." >&2
           return 2 ;;
    esac
    path="${path%/}"

    # The health check, up front: catch a mistyped or not-yet-synced path
    # before pointing anything at it, rather than after the next ordinary
    # `setting` call fails somewhere else with no context at all.
    if [ ! -e "$path" ]; then
        echo "refusing to adopt $path: it does not exist on this machine." >&2
        echo "A common cause: a cloud-sync folder that has not finished syncing here" >&2
        echo "yet. Wait for it to appear (check the sync client), then try again." >&2
        return 1
    fi
    if [ ! -r "$path/config/env.yaml" ]; then
        echo "refusing to adopt $path: $path/config/env.yaml is missing or unreadable." >&2
        echo "The folder exists but does not look like one 'scripts/portable_root.sh" >&2
        echo "init' built - or it has not finished syncing yet. Build it there first," >&2
        echo "on the machine that already has this deployment's settings, or wait." >&2
        return 1
    fi

    local pointer_dir="${XDG_CONFIG_HOME:-${HOME:-}/.config}/agentic-bioflow"
    mkdir -p "$pointer_dir" || { echo "could not create $pointer_dir" >&2; return 1; }
    local pointer="$pointer_dir/portable_root" stamp
    stamp="$(date +%Y%m%d%H%M%S 2>/dev/null || echo now)"

    # Back up whatever this machine already had before pointing it anywhere
    # else. Adopting must never be the thing that loses a machine's own
    # settings, even a partial or stale one - the same care set_setting()
    # already takes with a settings file it did not itself just create.
    if [ -e "$SETTINGS_FILE" ]; then
        cp -p "$SETTINGS_FILE" "${SETTINGS_FILE}.pre-adopt.$stamp" 2>/dev/null \
            && echo "backed up this machine's settings to ${SETTINGS_FILE}.pre-adopt.$stamp"
    fi
    [ -e "$pointer" ] && cp -p "$pointer" "${pointer}.pre-adopt.$stamp" 2>/dev/null

    printf '%s\n' "$path" > "$pointer" || { echo "could not write $pointer" >&2; return 1; }
    chmod 600 "$pointer"
    echo "adopted $path"
    echo "settings now resolve: $pointer -> $path/config/env.yaml -> $SETTINGS_FILE"
    echo "(portable keys from the first of those two that has them; everything else -"
    echo "site_bridge, ssh_control_path, tw_bin, local_root, agent_java/agent_jar -"
    echo "still comes from this machine's own file, docs/SETTINGS.md.)"
}

# --- T23: settings.sh --reconstruct -----------------------------------------
# The fallback for issue #17's actual reported shape: no portable folder, and
# the site's own _personal/env.yaml only ever held agent_java/agent_jar/
# tw_bin/agent_connection - the values scripts/install_deps.sh and
# scripts/agent_ctl.sh discover on their own, never the ones a person has to
# be asked for. Everything Platform can answer is read back here as a
# CANDIDATE only; nothing is written automatically (docs/SETTINGS.md: "must
# be asked for rather than guessed") - confirm each with
# `scripts/settings.sh --set <key> <value>`.
#
# tw's exact table output was not measured against a real `tw` binary on this
# machine (none installed here, no network to fetch one - PRINCIPLES.md
# invariant 8: measure or read the source before claiming). Parsing here
# indexes columns by their header text rather than a fixed position, and
# falls back to printing the raw table when it cannot find what it is looking
# for - a degraded answer, never a silently wrong one.
_reconstruct_tw_bin() {
    local t; t="${TW_BIN:-$(setting tw_bin)}"
    [ -n "$t" ] || t="tw"
    command -v "$t" >/dev/null 2>&1 && printf '%s\n' "$t"
}

# Index-by-header-name table reader for tw's `|`-delimited list output (the
# one shape actually confirmed in this repo: scripts/preflight.sh parses
# `tw compute-envs view` the same way). <label> is what each candidate line
# is printed as.
_table_candidates() {   # _table_candidates <table-text> <label>
    local text="$1" label="$2" header
    header=$(grep -F '|' <<<"$text" | grep -iE '(^| )id( |\|)' | head -1)
    if [ -z "$header" ]; then
        echo "  (could not find an 'Id' column in this table - read it yourself:)"
        sed 's/^/  | /' <<<"$text"
        return 0
    fi
    local idx nidx
    idx=$(awk -F'|' -v h="$header" 'BEGIN{
        n=split(h,a,"|")
        for(i=1;i<=n;i++){g=a[i]; gsub(/^[ \t]+|[ \t]+$/,"",g); if (tolower(g)=="id"){print i; exit}}
    }')
    nidx=$(awk -F'|' -v h="$header" 'BEGIN{
        n=split(h,a,"|")
        for(i=1;i<=n;i++){g=a[i]; gsub(/^[ \t]+|[ \t]+$/,"",g); if (tolower(g)=="name"){print i; exit}}
    }')
    [ -n "$idx" ] || { echo "  (no 'Id' column - read the raw table yourself:)"; sed 's/^/  | /' <<<"$text"; return 0; }
    awk -F'|' -v idx="$idx" -v nidx="${nidx:-0}" -v label="$label" -v hdr="$header" '
        $0 == hdr { next }
        /^[[:space:]|:+=-]+$/ { next }
        NF >= idx {
            id=$idx; gsub(/^[ \t]+|[ \t]+$/,"",id)
            if (id == "" || tolower(id) == "id") next
            name=""
            if (nidx > 0 && NF >= nidx) { name=$nidx; gsub(/^[ \t]+|[ \t]+$/,"",name) }
            print "  candidate " label ": " id (name != "" ? " (" name ")" : "")
        }' <<<"$text"
}

reconstruct_settings() {
    local tw; tw="$(_reconstruct_tw_bin)"
    if [ -z "$tw" ]; then
        echo "no working 'tw' found (the tw_bin setting, or on PATH) - cannot" >&2
        echo "reconstruct anything. Install it first: scripts/install_deps.sh --cli-only." >&2
        return 1
    fi

    local tokf; tokf="$(token_file)"
    if [ -z "${TOWER_ACCESS_TOKEN:-}" ] && [ -r "$tokf" ]; then
        TOWER_ACCESS_TOKEN="$(cat "$tokf")"; export TOWER_ACCESS_TOKEN
    fi
    if [ -z "${TOWER_ACCESS_TOKEN:-}" ]; then
        echo "no Seqera token available (checked $tokf and \$TOWER_ACCESS_TOKEN) -" >&2
        echo "reconstruction needs one to ask Platform anything at all. See" >&2
        echo "docs/SETTINGS.md / commands/setup.md step 3 for how to get one." >&2
        return 1
    fi

    echo "Reconstructing from Seqera Platform - every line below is a CANDIDATE."
    echo "Confirm each one with the user, then save it yourself:"
    echo "  scripts/settings.sh --set <key> <value>"
    echo "Nothing here is written automatically."
    echo

    local info user_line
    info="$("$tw" info 2>&1)"
    user_line=$(grep -iE 'user' <<<"$info" | head -1)
    echo "-- seqera_user, from '$tw info' --"
    if [ -n "$user_line" ]; then
        # The label/value separator was not measured (no real `tw` here to
        # check against - see this function's own header comment): a ':' or
        # '|' on the line is trusted as that separator when present, and
        # otherwise this falls back to the LAST whitespace-separated field,
        # which is right for a two-column "label   value" layout too.
        local cand
        case "$user_line" in
            *:*|*'|'*)
                cand="${user_line}"
                cand="${cand##*:}"
                cand="${cand##*|}" ;;
            *)
                cand="${user_line##* }" ;;
        esac
        cand="$(sed 's/^[[:space:]]*//;s/[[:space:]]*$//' <<<"$cand")"
        echo "  candidate seqera_user: $cand"
        echo "  (from the line: $user_line)"
    else
        echo "  (no line mentioning a user - read the raw output yourself:)"
        sed 's/^/  | /' <<<"$info"
    fi
    echo

    echo "-- workspace_id, from '$tw workspaces list' --"
    _table_candidates "$("$tw" workspaces list 2>&1)" workspace_id
    echo

    echo "-- compute_env --"
    echo "  needs a confirmed workspace_id first, so this is not run automatically:"
    echo "    $tw compute-envs list -w <the workspace_id you just confirmed>"
    echo "  confirm against the Name column, which is what the 'compute_env' setting"
    echo "  actually stores (docs/SETTINGS.md)."
    echo

    echo "-- slurm_account --"
    echo "  cannot be read from Platform at all - it is the site's own allocation,"
    echo "  never Seqera's. On the site, ask the user to check:"
    echo "    sacctmgr show associations user=\$USER format=account"
    echo "    sshare -U -u \$USER"
    echo "  and confirm which one this deployment should bill to. There is"
    echo "  deliberately no default here (docs/SETTINGS.md) - never guess it, and"
    echo "  never copy it from another member."
}

# Which startup file an export has to go into, and the line to put there.
#
# Writing `~/.bashrc` unconditionally is wrong the moment the shell is not
# bash: zsh - the default on macOS since Catalina - never reads it, so the
# export vanishes with no error and the next terminal looks unconfigured. That
# is PITFALLS 25's symptom reached by a different road, on a machine with only
# one home directory and therefore no clue to follow.
#
# $SHELL, not $0 and not the parent process: the question is what a NEW
# terminal will start and therefore what will read a startup file, and this
# script may well be running under a bash the user never chose.
#
# The line is generated rather than left to the caller because the file and the
# syntax have to agree - fish takes `set -gx`, and an `export` written into
# config.fish is a syntax error at every future shell start.
profile_file() {
    case "$(basename "${SHELL:-sh}")" in
        zsh)  printf '%s\n' "${ZDOTDIR:-$HOME}/.zshrc" ;;
        bash) printf '%s\n' "$HOME/.bashrc" ;;
        fish) printf '%s\n' "$HOME/.config/fish/config.fish" ;;
        ksh)  printf '%s\n' "$HOME/.kshrc" ;;
        csh|tcsh) printf '%s\n' "$HOME/.cshrc" ;;
        # sh, dash, ash, mksh and anything unrecognised: ~/.profile with POSIX
        # `export` is the answer that is right for all of them. The two shells
        # it would be wrong for - fish and csh - are the two named above,
        # because a wrong answer here is silent in both directions: the file is
        # never read, or the line is a syntax error at every future shell start.
        *)    printf '%s\n' "$HOME/.profile" ;;
    esac
}

profile_export() {
    local name="${1:?usage: --profile-export <NAME> <VALUE>}" val="${2?}"
    case "$(basename "${SHELL:-sh}")" in
        fish)     printf 'set -gx %s %s\n' "$name" "$val" ;;
        csh|tcsh) printf 'setenv %s "%s"\n' "$name" "$val" ;;
        *)        printf 'export %s="%s"\n' "$name" "$val" ;;
    esac
}

# `settings.sh --summary` - one screen answering "what am I configured as", and
# above all *where that answer lives*. Nothing else in this repo ever names the
# file it just read, which is how a member came to be grepping the filesystem
# for it.
#
# The token's value is never part of this. Setup's own rule for it is "never
# printed, never in git, never in a params file", and a convenience command that
# leaked it would be a worse bug than the one this fixes. Only two things about
# it are anybody's business here: whether it is there, and whether its mode
# still keeps it to one person.
token_state() {
    local f p; f="$(token_file)"
    if [ -r "$f" ]; then
        p="$(file_privacy "$f")"
        case "${p%% *}" in
            private) printf 'present (%s)  %s\n' "${p#* }" "$f" ;;
            unknown) printf 'present  %s\n' "$f" ;;
            *)       printf 'present but %s  %s\n' "${p#* }" "$f" ;;
        esac
    elif [ -e "$f" ]; then
        printf 'present but unreadable  %s\n' "$f"
    elif [ -n "$PORTABLE_ROOT" ] && [ -r "${PORTABLE_ROOT%/}/config/.seqera_token.enc" ]; then
        # T23: distinguish "never had one" from "have one, just not decrypted
        # here yet" - the second is a one-command fix, not a trip back to
        # setup step 3.
        printf 'not decrypted yet - run scripts/portable_root.sh decrypt-token\n'
    else
        printf 'not found - looked beside the settings file\n'
    fi
}

settings_summary() {
    [ "$SETTINGS_FOUND" = 1 ] || { settings_missing >&2; portable_missing_reason >&2; return 1; }
    local r='  %-20s %s\n' host
    host="$(setting site_host)"
    echo "This deployment:"
    echo
    # shellcheck disable=SC2059
    if [ -n "$PORTABLE_SETTINGS_FILE" ]; then
        printf "$r" "portable folder"     "$PORTABLE_ROOT"
        printf "$r" "portable settings"   "$PORTABLE_SETTINGS_FILE"
        printf "$r" "machine settings"    "$SETTINGS_FILE"
    else
        printf "$r" "settings file"       "$SETTINGS_FILE"
    fi
    printf "$r" "site account"        "$(setting site_user 'not set')"
    printf "$r" "site"                "$(setting reach local)${host:+ - $host}"
    printf "$r" "seqera account"      "$(setting seqera_user 'not set')"
    printf "$r" "workspace"           "$(setting workspace_id 'not set')"
    printf "$r" "run area"            "$(setting storage_root "${LAB_RUNS_DIR:-not set}")"
    printf "$r" "compute environment" "$(setting compute_env 'not set')"
    printf "$r" "agent connection"    "$(setting agent_connection 'not set')"
    printf "$r" "token"               "$(token_state)"
    echo
    # B2: this used to assert "mode 600" outright. token_state() above already
    # reads the mode back and reports what it actually is rather than what it
    # should be - the two halves of one file were inconsistent. Same call,
    # same three-way read here, so a filesystem that cannot hold 600 (B1) is
    # not contradicted two lines later by a sentence that was never checked.
    local _sp; _sp="$(file_privacy "$SETTINGS_FILE")"
    if [ -n "$PORTABLE_SETTINGS_FILE" ]; then
        # T23: not "all of it" any more - the portable keys above came from
        # $PORTABLE_SETTINGS_FILE, which this repeats what --adopt already
        # printed rather than re-checking its privacy a second time here.
        echo "The portable keys above come from $PORTABLE_SETTINGS_FILE."
        case "${_sp%% *}" in
            private) echo "Everything else is saved at $SETTINGS_FILE, ${_sp#* }." ;;
            unknown) echo "Everything else is saved at $SETTINGS_FILE; ${_sp#* }." ;;
            *)       echo "Everything else is saved at $SETTINGS_FILE, ${_sp#* }." ;;
        esac
    else
        case "${_sp%% *}" in
            private) echo "All of it is saved at $SETTINGS_FILE, ${_sp#* }." ;;
            unknown) echo "All of it is saved at $SETTINGS_FILE; ${_sp#* }." ;;
            *)       echo "All of it is saved at $SETTINGS_FILE, ${_sp#* }." ;;
        esac
    fi
    echo "Every command here finds it there; none of this has to be entered again."
}

# Allow `settings.sh <key> [default]` and `settings.sh --set <key> <value>` as
# well as sourcing it. The writing form is for the case where the discovery
# happened somewhere else: a script run on the site knows where it put things,
# but its own set_setting can only reach the settings file it can see, which on
# a deployment driven from the user's machine is not the one that counts.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    case "${1:-}" in
        --set)
            _k="${2:?usage: settings.sh --set <key> <value>}"
            _v="${3?usage: settings.sh --set <key> <value>}"
            if site_shaped_write_refusal "$_k" "$_v"; then
                refuse_site_shaped_write "$_k"; exit 2
            fi
            if looks_synced_write_refusal "$SETTINGS_FILE"; then
                refuse_synced_write "$SETTINGS_FILE"; exit 2
            fi
            set_setting "$_k" "$_v" ;;
        --summary)
            settings_summary ;;
        --profile-file)
            profile_file ;;
        --profile-export)
            profile_export "${2:?usage: settings.sh --profile-export <NAME> <VALUE>}" \
                           "${3?usage: settings.sh --profile-export <NAME> <VALUE>}" ;;
        --adopt)
            adopt_portable_root "${2:?usage: settings.sh --adopt <path>}" ;;
        --reconstruct)
            reconstruct_settings ;;
        *)
            setting "${1:?usage: settings.sh <key> [default|--required] | --summary | --set <key> <value>}" \
                    "${2:-}" ;;
    esac
fi
