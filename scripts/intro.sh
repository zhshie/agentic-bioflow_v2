#!/bin/bash
# Prints the plugin overview, or one command's opening, or the flow-end
# signal a Stop hook watches for. This script holds no user-visible sentences
# itself - every line it prints comes from a text file under
# scripts/intro/<lang>/. See the plan appendix ("附錄：2.7 的介面規格") for
# the exact contract.
#
#   intro.sh                      full overview: what this is, the five
#                                  commands, the flow diagram, next step
#   intro.sh <command>            that command's opening (five fixed
#                                  sections)
#   intro.sh --end <command>      exactly one line: "flow-end: <command>" -
#                                  the signal a Stop hook uses to know a
#                                  command's flow finished
#   intro.sh --list               the command names that have opening text
#   [--lang zh-TW|en]             overrides the language; default comes from
#                                  the settings key `language`, falling back
#                                  to zh-TW when that key or the settings
#                                  file itself is missing
#
# Unknown command -> usage on stderr, exit 2. Success -> exit 0.
#
# Not settings.sh: intro.sh needs exactly one thing from it (the `language`
# key), and settings.sh already does that job - a second reader of the
# settings file here would be the kind of duplicate this repo's own
# principles rule out. No other file in this repo is a dependency, and this
# one must still work with no settings file at all: a first-time user, with
# nothing set up yet, is exactly who needs the intro.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTRO_DIR="$ROOT/scripts/intro"
SETTINGS="$ROOT/scripts/settings.sh"

# The five commands, in the order they appear everywhere else in this repo
# (README.md, SKILL.md, the plan's own table) - setup before launch before
# runs before downstream before finish.
COMMANDS="setup launch runs downstream finish"

usage() {
    cat >&2 <<'EOF'
usage: intro.sh [--lang zh-TW|en] [<command>]
       intro.sh [--lang zh-TW|en] --end <command>
       intro.sh --list

<command> is one of: setup launch runs downstream finish
EOF
}

is_known_command() {
    local c="$1" k
    for k in $COMMANDS; do
        [ "$c" = "$k" ] && return 0
    done
    return 1
}

# --- parse args --------------------------------------------------------
# --lang can appear anywhere on the line (`intro.sh launch --lang en` and
# `intro.sh --lang en launch` both work), so this scans everything rather
# than only looking at $1.
lang_override=""
positional=()
while [ $# -gt 0 ]; do
    case "$1" in
        --lang)
            if [ $# -lt 2 ]; then usage; exit 2; fi
            lang_override="$2"
            shift 2
            ;;
        *)
            positional+=("$1")
            shift
            ;;
    esac
done

# --- which language ------------------------------------------------------
# --lang wins outright. Otherwise ask settings.sh for `language` - not by
# reading the settings file ourselves, that is settings.sh's one job - and
# fall back to zh-TW silently whenever that comes back empty: no settings
# file, no `language` key in one that exists, or settings.sh itself missing.
resolve_lang() {
    if [ -n "$lang_override" ]; then
        printf '%s\n' "$lang_override"
        return 0
    fi
    local v=""
    if [ -r "$SETTINGS" ]; then
        v="$(bash "$SETTINGS" language 2>/dev/null)"
    fi
    [ -n "$v" ] || v="zh-TW"
    printf '%s\n' "$v"
}

LANG_DIR="$INTRO_DIR/$(resolve_lang)"
# An unrecognised language (a typo in the settings file, or --lang given
# something that is not one of the two directories that exist) falls back
# to zh-TW rather than failing the whole intro.
[ -d "$LANG_DIR" ] || LANG_DIR="$INTRO_DIR/zh-TW"

# --- dispatch --------------------------------------------------------------
case "${positional[0]:-}" in
    "")
        if [ ! -r "$LANG_DIR/overview.txt" ]; then usage; exit 2; fi
        cat "$LANG_DIR/overview.txt"
        ;;
    --list)
        for c in $COMMANDS; do
            printf '%s\n' "$c"
        done
        ;;
    --end)
        cmd="${positional[1]:-}"
        if ! is_known_command "$cmd"; then usage; exit 2; fi
        printf 'flow-end: %s\n' "$cmd"
        ;;
    *)
        cmd="${positional[0]}"
        if ! is_known_command "$cmd"; then usage; exit 2; fi
        if [ ! -r "$LANG_DIR/$cmd.txt" ]; then usage; exit 2; fi
        cat "$LANG_DIR/$cmd.txt"
        ;;
esac
