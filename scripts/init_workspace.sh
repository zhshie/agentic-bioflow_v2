#!/bin/bash
# T11: give the run area a designed shape.
#
# Measured, not guessed: a real run area was two things at once - probe
# directories from setup rehearsals (_boxtest, _coldstart, _coldstart2,
# _coldstart_s4, _net_probe, _relay_probe, _coscientist_eval, _exttest) sitting
# beside real analyses with no boundary between them, and a second run area
# elsewhere shaped differently again (rawdata/ results/ _work/ at the top,
# instead of per-member). Nothing had ever decided the shape; it accreted.
#
# This script is the shape, made real. It creates either side - never both in
# one call, because they are two different machines - and it is deliberately
# dumb about *how* the site is reached: reach (none/local/ssh, contract 6 in
# docs/SITE_ADAPTER.md) is a command-layer decision, not this script's. Run it
# where you want the directories to appear: directly for reach:local or the
# local side, through scripts/on_site.sh --script for reach:ssh's site side.
#
#   init_workspace.sh site  [--user <seqera_user>] [--run <name>]
#   init_workspace.sh local --user <seqera_user> [--run <name>] [--root <path>]
#
#   --user   the Seqera username (Username column of `tw runs list`). The site
#            is one shared Unix account, so this is what tells members' runs
#            apart - not $USER, which is the same for everyone. May not start
#            with '_': that prefix is reserved for the shared areas below.
#
#            Required on the local side, which has no shared area to fall
#            back to. Optional on the site side, because setup asks for it in
#            a later step than "where the work will live": call this once
#            without --user to lay down _personal/, _references/,
#            lab_singularity_library/ and _system/ (nothing about them needs
#            to know who the member is), and again with --user once Seqera
#            has answered, to add that member's rawdata/ and runs/. Both
#            calls are idempotent, so doing it in two passes costs nothing.
#   --run    also scaffold one run's own subdirectories
#            (runs/<pipeline>_<label>_<YYYYMMDD>/...). Optional: most calls
#            are setup building the standing skeleton, before any run exists.
#   --root   local side only. Default $HOME/agentic-bioflow.
#
# Idempotent: every directory is made with `mkdir -p`, which by construction
# never touches anything already inside an existing one - the same guarantee
# `hooks/confirm_cleanup.sh` polices from the other direction. Run this twice
# and the second run changes nothing.
#
# The names below - rawdata, results, analysis, _references and
# lab_singularity_library - are not this script's invention: they are copied
# verbatim from hooks/confirm_cleanup.sh's HIT_PROTECTED and HIT_SHARED
# blocks, which is the safety net that refuses to delete them. Get one
# spelling wrong here and the skeleton names a directory the net does not
# recognise. (The shared image cache is spelled `lab_singularity_library`
# because that is the hook's literal pattern - an earlier draft of this design
# called it `_singularity_cache`, which the hook does not match. Naming it
# that here would build a "protected" directory the safety net has never heard
# of, so the hook's spelling wins.)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

die() { local rc="$1"; shift; printf '%s\n' "$@" >&2; exit "$rc"; }

SIDE="${1:-}"
case "$SIDE" in
    site|local) shift ;;
    *) die 2 "usage: init_workspace.sh site|local --user <seqera_user> [--run <name>] [--root <path>]" ;;
esac

USER_NAME="" RUN_NAME="" ROOT_ARG=""
while [ $# -gt 0 ]; do
    case "$1" in
        --user) USER_NAME="${2:?--user needs a value}"; shift 2 ;;
        --run)  RUN_NAME="${2:?--run needs a value}"; shift 2 ;;
        --root) ROOT_ARG="${2:?--root needs a value}"; shift 2 ;;
        *) die 2 "unknown option '$1'" ;;
    esac
done

if [ "$SIDE" = local ]; then
    [ -n "$USER_NAME" ] || die 2 "--user is required on the local side." \
        "There is no shared area here to fall back to - everything local is" \
        "under one member's own name. See docs/SETTINGS.md (seqera_user)."
fi
[ -n "$RUN_NAME" ] && [ -z "$USER_NAME" ] \
    && die 2 "--run needs --user - a run belongs to one member's runs/."
if [ -n "$USER_NAME" ]; then
    case "$USER_NAME" in
        */*|.|..) die 2 "--user '$USER_NAME' must be a bare name, not a path." ;;
        _*) die 2 "--user '$USER_NAME' starts with '_'." \
                 "That prefix is reserved for the shared areas this script also" \
                 "creates (_personal, _references, _system) and would collide with one." ;;
    esac
fi
if [ -n "$RUN_NAME" ]; then
    case "$RUN_NAME" in
        */*|.|..) die 2 "--run '$RUN_NAME' must be a bare directory name, not a path." ;;
    esac
fi

# mkdir -p is the whole idempotency and non-destructive guarantee: it creates
# what is missing and leaves what already exists - files inside included -
# completely alone.
make() { mkdir -p "$1" || die 1 "could not create '$1'"; }

DIRS=()

if [ "$SIDE" = site ]; then
    BASE="${LAB_RUNS_DIR:-$(setting storage_root)}"
    [ -n "$BASE" ] || die 2 "no run area known." \
        "Set LAB_RUNS_DIR, or 'storage_root' in the deployment settings - this is" \
        "step 1 of setup and everything else derives from it. See docs/SETTINGS.md."
    BASE="${BASE%/}"

    DIRS+=(
        "$BASE/_personal"
        "$BASE/_references"
        "$BASE/lab_singularity_library"
        "$BASE/_system/agent"
        "$BASE/_system/relay"
        "$BASE/_system/coldstart"
    )
    if [ -n "$USER_NAME" ]; then
        DIRS+=("$BASE/$USER_NAME/rawdata" "$BASE/$USER_NAME/runs")
    fi
    if [ -n "$RUN_NAME" ]; then
        RUN_DIR="$BASE/$USER_NAME/runs/$RUN_NAME"
        DIRS+=("$RUN_DIR/logs" "$RUN_DIR/results" "$RUN_DIR/analysis" "$RUN_DIR/work")
    fi
else
    BASE="${ROOT_ARG:-$HOME/agentic-bioflow}"
    BASE="${BASE%/}"

    DIRS+=(
        "$BASE/$USER_NAME/inbox"
        "$BASE/$USER_NAME/runs"
    )
    if [ -n "$RUN_NAME" ]; then
        RUN_DIR="$BASE/$USER_NAME/runs/$RUN_NAME"
        DIRS+=("$RUN_DIR/results" "$RUN_DIR/analysis")
    fi
fi

for d in "${DIRS[@]}"; do make "$d"; done

# _personal/ holds env.yaml and the Seqera token once setup writes them - both
# mode 600, per person. The directory itself is tightened here so nothing
# else on a shared account can even list what is in it before those files
# exist. Idempotent: chmod on an already-700 directory changes nothing.
[ "$SIDE" = site ] && chmod 700 "$BASE/_personal" 2>/dev/null

# --- the tree it made --------------------------------------------------------
# Fixed, not scanned: $BASE is the run area, and on a real deployment it holds
# every other member's rawdata and every past run - `find`-ing it recursively
# would print all of that, not "the tree this call made", and would do it
# every single time this idempotent script is re-run. Print only the shape
# this call is responsible for.
echo "$BASE"
if [ "$SIDE" = site ]; then
    echo "├── _personal/"
    echo "├── _references/"
    echo "├── lab_singularity_library/"
    if [ -n "$USER_NAME" ]; then
        echo "├── _system/"
        echo "│   ├── agent/"
        echo "│   ├── relay/"
        echo "│   └── coldstart/"
    else
        echo "└── _system/"
        echo "    ├── agent/"
        echo "    ├── relay/"
        echo "    └── coldstart/"
    fi
    if [ -n "$USER_NAME" ]; then
        echo "└── $USER_NAME/"
        echo "    ├── rawdata/"
        echo "    └── runs/"
        if [ -n "$RUN_NAME" ]; then
            echo "        └── $RUN_NAME/"
            echo "            ├── logs/"
            echo "            ├── results/"
            echo "            ├── analysis/"
            echo "            └── work/"
        fi
    fi
else
    echo "└── $USER_NAME/"
    echo "    ├── inbox/"
    echo "    └── runs/"
    if [ -n "$RUN_NAME" ]; then
        echo "        └── $RUN_NAME/"
        echo "            ├── results/"
        echo "            └── analysis/"
    fi
fi
