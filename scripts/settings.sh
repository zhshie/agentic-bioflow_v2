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
    echo "  refuses the filesystem outright if the mode 600 the token needs does"
    echo "  not hold there - settings.sh reads the mode back rather than trusting"
    echo "  that chmod did anything."
    echo "  On at least one machine it does not hold: MSYS maps chmod onto NTFS"
    echo "  ACLs, and 2026-09-16 measured 644 in \$HOME itself (PITFALLS 16j)."
    echo "  If setup refuses here, that is what happened, and the settings file"
    echo "  has to live where 600 holds - which this shell cannot yet read."
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
    local _default=none
    command -v wsl.exe >/dev/null 2>&1 \
        && ( cd "${HOME:-/}" 2>/dev/null || cd / 2>/dev/null || :
             wsl.exe -e true >/dev/null 2>&1 ) \
        && _default=wsl
    # The setting wins over the probe, in both directions: `site_bridge: none`
    # turns a working bridge off, which is what makes the refusal path
    # reachable on a machine that has WSL.
    setting site_bridge "$_default"
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

setting() {
    local key="$1" fallback="${2:-}" val=""
    if [ -r "$SETTINGS_FILE" ]; then
        val=$(sed -n "s/^[[:space:]]*${key}[[:space:]]*:[[:space:]]*//p" "$SETTINGS_FILE" \
              | sed 's/[[:space:]]*#.*$//; s/[[:space:]]*$//' | head -1)
    fi
    if [ -n "$val" ]; then printf '%s\n' "$val"; return 0; fi
    if [ "$fallback" = "--required" ]; then
        if [ "$SETTINGS_FOUND" = 1 ]; then
            echo "missing '$key' in $SETTINGS_FILE." >&2
        else
            echo "missing '$key', and there is no settings file to read it from." >&2
            settings_missing >&2
        fi
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
    local _mode_after; _mode_after="$(stat_mode "$SETTINGS_FILE")"
    case "$_mode_after" in
        600|"") return 0 ;;
    esac
    # Only a file THIS call created is ours to remove. One that already held a
    # member's real settings must stay - deleting it over a permission problem
    # would be a second, worse failure stacked on the first.
    if [ "$created" = 1 ]; then rm -f "$SETTINGS_FILE"; fi
    refuse_unwritable_mode "$SETTINGS_FILE" "$_mode_after"
    return 1
}

# What set_setting() calls when chmod 600 did not hold. Same shape as
# refuse_site_shaped_write() below: name the file, say why, name where it
# works instead.
refuse_unwritable_mode() {
    local file="$1" mode="$2"
    echo "refusing to write settings to $file: this filesystem would not hold mode 600." >&2
    echo "" >&2
    echo "chmod 600 was accepted but the file is still mode $mode. /mnt/c under WSL" >&2
    echo "(without the 'metadata' mount option) and exFAT both do this: the chmod" >&2
    echo "call succeeds and silently changes nothing. A token saved there is" >&2
    echo "effectively public to anyone with access to that filesystem." >&2
    echo "" >&2
    # 16j: on Git Bash the sentence below is a circle. MSYS maps chmod onto
    # NTFS ACLs, and on a member's own laptop, 2026-09-16, the mode came back
    # 644 in $HOME itself - not only on the cloud drive they work in. Naming
    # another directory under the same $HOME there would send them back to the
    # filesystem that just refused them. Say where 600 does hold instead, and
    # say plainly that this shell cannot yet read a settings file that lives
    # there (PITFALLS 25) - a gap this version has not closed is still better
    # information than an instruction that cannot work.
    if [ "$(plat_kind)" = msys ]; then
        echo "This shell is Git Bash/MSYS, where chmod is mapped onto NTFS ACLs and" >&2
        echo "can be accepted without changing anything. Measured on a member's own" >&2
        echo "laptop on 2026-09-16: mode 644 in \$HOME itself, not only on a mapped or" >&2
        echo "cloud drive (PITFALLS 16j). If that is this machine, no other directory" >&2
        echo "under \$HOME here will get past this refusal." >&2
        echo "" >&2
        echo "WSL's own home is on ext4, which holds mode 600 normally, and setup run" >&2
        echo "from a WSL shell writes there. Be warned that this shell cannot read a" >&2
        echo "settings file that lives there (PITFALLS 25): that is a known gap in this" >&2
        echo "version, not something a path in this window can work around." >&2
        return 0
    fi
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
#   0  refuse   1  fine, carry on
looks_synced_write_refusal() {
    local path="$1"
    [ -z "${LAB_SETTINGS_FILE:-}" ] || return 1   # an explicit location wins outright
    case "$path" in
        *OneDrive*|*Dropbox*|*"Google Drive"*|*GoogleDrive*|*"Library/Mobile Documents"*|*Box*|*Nextcloud*)
            return 0 ;;
    esac
    return 1
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
    local f m; f="$(token_file)"
    if [ -r "$f" ]; then
        m="$(stat_mode "$f")"
        case "$m" in
            600) printf 'present (mode 600)  %s\n' "$f" ;;
            "")  printf 'present  %s\n' "$f" ;;
            *)   printf 'present but mode %s, should be 600  %s\n' "$m" "$f" ;;
        esac
    elif [ -e "$f" ]; then
        printf 'present but unreadable  %s\n' "$f"
    else
        printf 'not found - looked beside the settings file\n'
    fi
}

settings_summary() {
    [ "$SETTINGS_FOUND" = 1 ] || { settings_missing >&2; return 1; }
    local r='  %-20s %s\n' host
    host="$(setting site_host)"
    echo "This deployment:"
    echo
    # shellcheck disable=SC2059
    printf "$r" "settings file"       "$SETTINGS_FILE"
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
    local _settings_mode; _settings_mode="$(stat_mode "$SETTINGS_FILE")"
    case "$_settings_mode" in
        600) echo "All of it is saved at $SETTINGS_FILE, mode 600." ;;
        "")  echo "All of it is saved at $SETTINGS_FILE; its mode could not be read." ;;
        *)   echo "All of it is saved at $SETTINGS_FILE, mode $_settings_mode - should be 600." ;;
    esac
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
        *)
            setting "${1:?usage: settings.sh <key> [default|--required] | --summary | --set <key> <value>}" \
                    "${2:-}" ;;
    esac
fi
