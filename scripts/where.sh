#!/bin/bash
# T22: "where is everything" - every absolute path this deployment might read
# or write ON THIS MACHINE, each marked exists/missing. Purely read-only: this
# script changes nothing, ever.
#
# Nothing existing: no script here inventories the LOCAL machine's own paths.
# inspect_sides.sh (D1) answers a fixed yes/no set for one decision ("new
# install / adopt / repair"); this answers "where exactly is each thing" for
# a person debugging a surprising answer, or for another script that needs
# one of these paths without re-deriving the formula a second time - which is
# how docs/SETTINGS.md's own history of drift (two homes, a steered search, a
# settings file and a token that stopped travelling together) kept happening.
#
# Every path below comes from a function this repo already has - settings.sh,
# scripts/utils/portable.sh, or `report.sh --queue-dir` - never a second,
# hand-maintained formula. Where a value cannot be checked from this machine
# (a site-side path under `reach: ssh`), this says so rather than guessing.
#
#   where.sh                                     human-readable report, all
#                                                 sections, nothing hidden
#   where.sh --run-paths <project> <run> [--local-root <path>]
#                                                 two `key=path` lines, for
#                                                 another script to parse -
#                                                 see the block below
#
# --- the --run-paths interface, for scripts/prepare_launch.sh -------------
# perf/latency's scripts/prepare_launch.sh (not on this branch - it does not
# exist here yet) wants two absolute paths in its own launch summary: the
# site-side directory a launch will write results into, and where
# scripts/fetch.sh will bring them back to on THIS machine. Call:
#
#   bash scripts/where.sh --run-paths "$PROJECT" "$RUN_NAME" \
#       [--local-root "$OVERRIDE"]
#
# prints exactly two lines on stdout and nothing else:
#   site_run_dir=<absolute path>
#   local_fetch_dir=<absolute path>
# Errors go to stderr; a missing `seqera_user` or `--project`/`--run` value
# exits 2 before printing anything. Parse with
# `sed -n 's/^site_run_dir=//p'`, the same `key=value` shape
# inspect_sides.sh and egress_ctl.sh status already use.
#
# --local-root is the one-off override scripts/init_workspace.sh's own --root
# already accepts for the local side. Without it this reads the `local_root`
# setting the same way init_workspace.sh does (docs/SETTINGS.md), so the two
# can never point a launch summary and the actual fetch destination at two
# different directories for the same run.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

# --- shared: the run-area layout, one place -------------------------------
# Mirrors scripts/init_workspace.sh exactly (docs/SETTINGS.md, "The shape
# under storage_root"): site is $LAB_RUNS_DIR/<seqera_user>/projects/<project>
# /runs/<run>; local is <local_root>/<seqera_user>/projects/<project>/runs/
# <run>/results. T29 will teach both this function and init_workspace.sh a
# second shape once `portable_root` exists (no <seqera_user> layer locally) -
# not built yet on this branch at this point, so this is the layout every
# deployment has today.
site_run_dir() {   # site_run_dir <project> <run>
    local base user
    base="${LAB_RUNS_DIR:-$(setting storage_root)}"
    user="$(setting seqera_user)"
    [ -n "$base" ] || { echo "no run area known - set storage_root (docs/SETTINGS.md)." >&2; return 1; }
    [ -n "$user" ] || { echo "no seqera_user in the deployment settings - ask the user for it." >&2; return 1; }
    printf '%s\n' "${base%/}/$user/projects/$1/runs/$2"
}

local_fetch_dir() {   # local_fetch_dir <project> <run> [<root-override>]
    local root user
    root="${3:-$(setting local_root "${HOME:-}/agentic-bioflow")}"
    user="$(setting seqera_user)"
    [ -n "$user" ] || { echo "no seqera_user in the deployment settings - ask the user for it." >&2; return 1; }
    printf '%s\n' "${root%/}/$user/projects/$1/runs/$2/results"
}

if [ "${1:-}" = --run-paths ]; then
    shift
    PROJECT="${1:?usage: where.sh --run-paths <project> <run> [--local-root <path>]}"
    RUN="${2:?usage: where.sh --run-paths <project> <run> [--local-root <path>]}"
    shift 2
    ROOT_OVERRIDE=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --local-root) ROOT_OVERRIDE="${2:?--local-root needs a value}"; shift 2 ;;
            *) echo "unknown option '$1'" >&2; exit 2 ;;
        esac
    done
    SRD="$(site_run_dir "$PROJECT" "$RUN")" || exit 2
    LFD="$(local_fetch_dir "$PROJECT" "$RUN" "$ROOT_OVERRIDE")" || exit 2
    printf 'site_run_dir=%s\n' "$SRD"
    printf 'local_fetch_dir=%s\n' "$LFD"
    exit 0
fi

# --- the human-readable report ---------------------------------------------
mark() { [ -e "$1" ] && printf 'exists\n' || printf 'missing\n'; }   # -e: file or dir, whichever is asked for

echo "== settings file (env.yaml) - what each 'reach' resolves to here =="
# The same three candidates docs/SETTINGS.md's table names, computed the same
# way settings.sh's own SETTINGS_CANDIDATES is (this file's own header),
# shown for all three `reach` values regardless of which one is actually
# configured - so a person moving between reach:local and reach:ssh can see
# both answers without changing anything first.
LOCAL_CANDIDATE="${LAB_RUNS_DIR:+${LAB_RUNS_DIR%/}/_personal/env.yaml}"
XDG_CANDIDATE="$(xdg_default)"
if [ -n "$LOCAL_CANDIDATE" ]; then
    printf '  reach: local   %-60s [%s]\n' "$LOCAL_CANDIDATE" "$(mark "$LOCAL_CANDIDATE")"
else
    printf '  reach: local   (LAB_RUNS_DIR is not set - this reach has no candidate here)\n'
fi
printf '  reach: ssh     %-60s [%s]\n' "$XDG_CANDIDATE" "$(mark "$XDG_CANDIDATE")"
printf '  reach: none    %-60s [%s] (same file as ssh)\n' "$XDG_CANDIDATE" "$(mark "$XDG_CANDIDATE")"
if [ -n "${LAB_SETTINGS_FILE:-}" ]; then
    printf '  LAB_SETTINGS_FILE overrides all three: %-40s [%s]\n' "$LAB_SETTINGS_FILE" "$(mark "$LAB_SETTINGS_FILE")"
fi
if [ "$SETTINGS_FOUND" = 1 ]; then
    printf '  in use: %s\n' "$SETTINGS_FILE"
else
    printf '  in use: none found - looked in the candidates above\n'
fi
echo

echo "== token =="
printf '  %s\n' "$(token_state)"
echo

echo "== state directory (intro marker, Positron bridge) =="
STATE="${AGENTIC_BIOFLOW_STATE_DIR:-${XDG_STATE_HOME:-${HOME:-}/.local/state}/agentic-bioflow}"
printf '  base:            %-50s [%s]\n' "$STATE" "$(mark "$STATE")"
MARKS="$STATE/intro-shown"
if [ -d "$MARKS" ]; then
    n=$(find "$MARKS" -type f 2>/dev/null | wc -l | tr -d ' ')
    printf '  intro marker dir: %-49s [exists, %s marker(s)]\n' "$MARKS" "$n"
else
    printf '  intro marker dir: %-49s [missing]\n' "$MARKS"
fi
# No script on this branch writes this file yet - a Positron .vsix install
# step is a different branch's own card. Named here as the convention that
# would keep it (same directory, same naming scheme as intro-shown) so a
# future installer has one obvious place, not a claim that anything uses it.
PBRIDGE="$STATE/positron-bridge"
printf '  positron bridge (convention, not yet written by anything on this branch): %-20s [%s]\n' \
    "$PBRIDGE" "$(mark "$PBRIDGE")"
echo

echo "== local_root =="
LR="$(setting local_root "${HOME:-}/agentic-bioflow")"
printf '  %-60s [%s]\n' "$LR" "$(mark "$LR")"
echo

echo "== storage_root (site side) =="
SR="${LAB_RUNS_DIR:-$(setting storage_root)}"
REACH="$(setting reach local)"
if [ -z "$SR" ]; then
    echo "  not set - run setup"
elif [ "$REACH" = local ]; then
    printf '  %-60s [%s]\n' "$SR" "$(mark "$SR")"
else
    # Deliberately no on_site.sh round trip here: where.sh is meant to be
    # cheap enough for another script (prepare_launch.sh) to call on every
    # launch. inspect_sides.sh already owns the "is the site actually
    # reachable" question, at the cost of the round trip it accepts for it.
    printf '  %-60s [site-side; not checked from here - reach: %s]\n' "$SR" "$REACH"
fi
echo

echo "== singularity cache =="
CACHE="$(setting singularity_cache)"
if [ -n "$CACHE" ]; then
    if [ "$REACH" = local ]; then
        printf '  %-60s [%s]\n' "$CACHE" "$(mark "$CACHE")"
    else
        printf '  %-60s [site-side; not checked from here]\n' "$CACHE"
    fi
else
    printf '  not set - falls back to %s/_singularity_cache (site-side default)\n' "${SR:-<storage_root>}"
fi
echo

echo "== off-design reports queue =="
QUEUE="$(bash "$HERE/report.sh" --queue-dir 2>/dev/null)"
if [ -n "$QUEUE" ]; then
    if [ -d "$QUEUE" ]; then
        n=$(find "$QUEUE" -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d ' ')
        printf '  %-60s [exists, %s queued]\n' "$QUEUE" "$n"
    else
        printf '  %-60s [missing]\n' "$QUEUE"
    fi
else
    echo "  could not be resolved (scripts/report.sh --queue-dir failed)"
fi
echo

echo "== ssh control path =="
if [ "$REACH" = ssh ]; then
    BRIDGE="$(bridge_kind)"
    CP="$(setting ssh_control_path "$(site_control_path_default "$BRIDGE")")"
    printf '  %-60s [bridge: %s]\n' "$CP" "$BRIDGE"
    echo "  (a literal socket path cannot be existence-checked the way a file can;"
    echo "   scripts/on_site.sh --check-reach is what actually answers 'is it up'.)"
else
    echo "  n/a - reach: $REACH (ssh_control_path only applies under reach: ssh)"
fi
echo

echo "== portable folder (config/env.yaml, config/.seqera_token.enc, projects/) =="
PORTABLE="$(setting portable_root)"
if [ -n "$PORTABLE" ]; then
    printf '  %-60s [%s]\n' "$PORTABLE" "$(mark "$PORTABLE")"
else
    echo "  not configured"
fi
