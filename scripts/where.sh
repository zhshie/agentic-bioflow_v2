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
# scripts/utils/portable.sh, or `report.sh --dir` - never a second,
# hand-maintained formula. Where a value cannot be checked from this machine
# (a site-side path under `reach: ssh`), this says so rather than guessing.
#
#   where.sh                                     human-readable report, all
#                                                 sections, nothing hidden
#   where.sh --run-paths <project> <run> [--local-root <path>]
#                                                 two `key=path` lines, for
#                                                 another script to parse -
#                                                 see the block below
#   where.sh --project-paths <project> [--local-root <path>]
#                                                 rawdata/runs/analysis/
#                                                 submission on the local
#                                                 side, T29 - see that
#                                                 block further down
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
# already accepts for the local side. Without it this uses the root this
# machine is pointed at, the same way init_workspace.sh does
# (docs/SETTINGS.md), so the two can never point a launch summary and the
# actual fetch destination at two different directories for the same run.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

# --- shared: the run-area layout, one place -------------------------------
# Site: $LAB_RUNS_DIR/<seqera_user>/projects/<project>/runs/<run> - unchanged,
# the site side keeps the <seqera_user> layer (docs/SETTINGS.md: the site is
# one shared Unix account, so this is what tells members apart).
#
# Local: local_project_base()/local_analysis_base() (scripts/settings.sh,
# T29) - the SAME functions scripts/init_workspace.sh calls to actually build
# these directories, so this can never compute a different answer than what
# is really on disk: old layout (<root>/<user>/projects/<project>) for a
# project that already lives there, new layout (no <user> layer) for one that
# does not yet. T30 removed a third case - analysis/submission used to be
# redirected into a separate portable folder, and there is only one root now.
site_run_dir() {   # site_run_dir <project> <run>
    local base user
    base="${LAB_RUNS_DIR:-$(setting storage_root)}"
    user="$(setting seqera_user)"
    [ -n "$base" ] || { echo "no run area known - set storage_root (docs/SETTINGS.md)." >&2; return 1; }
    [ -n "$user" ] || { echo "no seqera_user in the deployment settings - ask the user for it." >&2; return 1; }
    printf '%s\n' "${base%/}/$user/projects/$1/runs/$2"
}

local_fetch_dir() {   # local_fetch_dir <project> <run> [<root-override>]
    local root user base
    root="${3:-${ABF_ROOT:-}}"
    [ -n "$root" ] || { echo "no root on this machine - scripts/settings.sh --use <root>" >&2; return 1; }
    user="$(setting seqera_user)"
    [ -n "$user" ] || { echo "no seqera_user in the deployment settings - ask the user for it." >&2; return 1; }
    base="$(local_project_base "$root" "$user" "$1")"
    printf '%s\n' "$base/runs/$2/results"
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

# T29: commands/downstream.md and commands/finish.md ask HERE for a project's
# local pieces rather than constructing the path themselves - the whole
# reason this exists is that the shape now branches three ways (old layout,
# new layout, portable-redirected analysis/submission) and a command file
# guessing which one applies is exactly how the two would drift.
#
#   where.sh --project-paths <project> [--local-root <path>]
#
# prints, and only:
#   rawdata_dir=<absolute path>
#   runs_dir=<absolute path>
#   analysis_dir=<absolute path>
#   submission_dir=<absolute path>
if [ "${1:-}" = --project-paths ]; then
    shift
    PROJECT="${1:?usage: where.sh --project-paths <project> [--local-root <path>]}"
    shift
    ROOT_OVERRIDE=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --local-root) ROOT_OVERRIDE="${2:?--local-root needs a value}"; shift 2 ;;
            *) echo "unknown option '$1'" >&2; exit 2 ;;
        esac
    done
    ROOT="${ROOT_OVERRIDE:-${ABF_ROOT:-}}"
    [ -n "$ROOT" ] || { echo "no root on this machine - scripts/settings.sh --use <root>" >&2; exit 1; }
    PUSER="$(setting seqera_user)"
    [ -n "$PUSER" ] || { echo "no seqera_user in the deployment settings - ask the user for it." >&2; exit 2; }
    PBASE="$(local_project_base "$ROOT" "$PUSER" "$PROJECT")"
    ABASE="$(local_analysis_base "$ROOT" "$PUSER" "$PROJECT")"
    printf 'rawdata_dir=%s\n' "$PBASE/rawdata"
    printf 'runs_dir=%s\n' "$PBASE/runs"
    printf 'analysis_dir=%s\n' "$ABASE/analysis"
    printf 'submission_dir=%s\n' "$ABASE/submission"
    exit 0
fi

# --- the human-readable report ---------------------------------------------
mark() { [ -e "$1" ] && printf 'exists\n' || printf 'missing\n'; }   # -e: file or dir, whichever is asked for

echo "== root =="
# T30: this section used to print three candidate settings files, one per
# `reach`, because that is how many there were. There is one now, and it does
# not depend on `reach` at all - which is most of why this card got shorter.
printf '  pointer: %-58s [%s]\n' "$ROOT_POINTER" "$(mark "$ROOT_POINTER")"
if [ -n "${ABF_ROOT:-}" ]; then
    printf '  root:    %-58s [%s]\n' "$ABF_ROOT" "$(mark "$ABF_ROOT")"
    printf '  config/env.yaml:           %-41s [%s]\n' "$SETTINGS_FILE" "$(mark "$SETTINGS_FILE")"
    printf '  config/machines/<this>:    %-41s [%s]\n' \
        "${MACHINE_SETTINGS_FILE:-}" "$(mark "${MACHINE_SETTINGS_FILE:-/nonexistent}")"
    printf '  projects/:                 %-41s [%s]\n' "$ABF_ROOT/projects" "$(mark "$ABF_ROOT/projects")"
else
    echo "  no root on this machine yet (scripts/settings.sh --use <root>)"
fi
if [ -n "${LAB_SETTINGS_FILE:-}" ]; then
    printf '  LAB_SETTINGS_FILE overrides the pointer: %-38s [%s]\n' \
        "$LAB_SETTINGS_FILE" "$(mark "$LAB_SETTINGS_FILE")"
fi
# scripts/status.sh parses this exact line (`sed -n 's/^  in use: //p'`) rather
# than calling settings.sh --summary a second time - T22. Keep the spelling.
if [ "$SETTINGS_FOUND" = 1 ]; then
    printf '  in use: %s\n' "$SETTINGS_FILE"
else
    printf '  in use: none - this machine has no root yet\n'
fi
# The pre-T30 locations, reported only when one is actually there - so that a
# machine that never migrated sees why nothing resolves, and a machine that
# did is not shown two paths it no longer uses.
if _old="$(legacy_settings_found 2>/dev/null)"; then
    printf '  pre-T30 settings still on disk: %-35s [exists]\n' "$_old"
    echo "  -> scripts/settings.sh --migrate <root> moves it, once"
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
QUEUE="$(bash "$HERE/report.sh" --dir 2>/dev/null)"
if [ -n "$QUEUE" ]; then
    if [ -d "$QUEUE" ]; then
        n=$(find "$QUEUE" -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d ' ')
        printf '  %-60s [exists, %s queued]\n' "$QUEUE" "$n"
    else
        printf '  %-60s [missing]\n' "$QUEUE"
    fi
else
    echo "  could not be resolved (scripts/report.sh --dir failed)"
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


