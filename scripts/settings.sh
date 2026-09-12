#!/bin/bash
# Read one value from the deployment's settings file.
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
# shell where on_site.sh still cannot open a session (16b) and where chmod 600
# on the Windows filesystem does not hold, which trades a loud failure for a
# quiet one and drops the token's only protection on the way.
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
    echo "  PITFALLS 16b: on Windows only WSL can hold the site connection, so"
    echo "  start Claude Code from a WSL shell rather than moving the file."
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
    local key="$1" val="$2"
    [ -n "${SETTINGS_FILE:-}" ] || { echo "no settings file location known" >&2; return 1; }
    mkdir -p "$(dirname "$SETTINGS_FILE")"
    [ -e "$SETTINGS_FILE" ] || { : > "$SETTINGS_FILE"; chmod 600 "$SETTINGS_FILE"; }
    python3 - "$SETTINGS_FILE" "$key" "$val" <<'PY'
import re, sys
path, key, val = sys.argv[1:4]
lines = open(path).read().splitlines(keepends=True)
pat = re.compile(rf"^(\s*){re.escape(key)}\s*:")
for i, line in enumerate(lines):
    if pat.match(line):
        # Keep any trailing comment: it usually says why the value matters.
        comment = ""
        body = line.split("#", 1)
        if len(body) == 2:
            comment = "  #" + body[1].rstrip("\n")
        lines[i] = f"{key}: {val}{comment}\n"
        break
else:
    if lines and not lines[-1].endswith("\n"):
        lines.append("\n")
    lines.append(f"{key}: {val}\n")
open(path, "w").writelines(lines)
PY
    chmod 600 "$SETTINGS_FILE"
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
    echo "All of it is saved at $SETTINGS_FILE, mode 600."
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
