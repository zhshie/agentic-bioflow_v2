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
    echo "Run setup to create one, or point LAB_SETTINGS_FILE at an existing one."
    return 0
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
        m="$(stat -c %a "$f" 2>/dev/null)"
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
            set_setting "${2:?usage: settings.sh --set <key> <value>}" \
                        "${3?usage: settings.sh --set <key> <value>}" ;;
        --summary)
            settings_summary ;;
        *)
            setting "${1:?usage: settings.sh <key> [default|--required] | --summary | --set <key> <value>}" \
                    "${2:-}" ;;
    esac
fi
