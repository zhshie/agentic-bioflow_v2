#!/bin/bash
# Nothing existing: neither `tw` nor Platform's own web UI cross-references a
# run's own params against a samplesheet about to be launched - this is a
# few lines of jq and text matching over what `tw runs list`/`tw runs view
# --params` already return.
#
# Guardrail 1 (T26): before a launch goes out, say when it looks like the
# same project/samplesheet pair already has a run in flight - not to block
# it (that call belongs to the user, like every other launch decision in
# this repo), only to surface it before they spend a queue slot finding out
# by hand.
#
# Written as its own callable piece, not inline in commands/launch.md,
# because this same check is where perf/latency's scripts/prepare_launch.sh
# is meant to fold it in. Once that script exists, its pre-launch summary
# should call
#
#   scripts/duplicate_run_check.sh --project <p> --samplesheet <path> \
#       --workspace <ws> [--user <seqera_user>]
#
# and append this call's own stdout (if any, one line per match) to
# whatever it is already showing before the confirm-and-launch step - the
# same "show everything, then wait for confirmation" shape
# commands/launch.md step 7 already uses. Until prepare_launch.sh exists,
# commands/launch.md step 4 calls this directly, right after the
# samplesheet is built and registered.
#
# Heuristic, not a state machine: this repo keeps no record of what
# samplesheet a run used (`docs/PRINCIPLES.md`, invariant 2 - no file here
# records run state), so "the same samplesheet" is judged from what
# Platform already has on the run - the project (from its own `--outdir`,
# the convention `docs/SETTINGS.md` defines) and the dataset name
# `tw runs view --params` reports for `input`, compared against the
# candidate samplesheet's own basename. A rename on either side defeats
# this; that is a known limit of reading a name rather than keeping a copy,
# not a bug to fix here - PRINCIPLES.md invariant 2 is exactly why no copy
# is kept.
#
#   duplicate_run_check.sh --project <name> --samplesheet <path>
#                           [--workspace <ws>] [--user <seqera_user>]
#
# Exit 0, nothing on stdout: no active run looks like a match.
# Exit 1, one line per match on stdout: at least one does.
# Exit 2: usage or settings error.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

PROJECT="" SHEET="" WS="" USER_FILTER=""
while [ $# -gt 0 ]; do
    case "$1" in
        --project)     PROJECT="${2:?--project needs a value}"; shift 2 ;;
        --samplesheet) SHEET="${2:?--samplesheet needs a value}"; shift 2 ;;
        --workspace)   WS="${2:?--workspace needs a value}"; shift 2 ;;
        --user)        USER_FILTER="${2:?--user needs a value}"; shift 2 ;;
        *) echo "usage: duplicate_run_check.sh --project <name> --samplesheet <path> [--workspace <ws>] [--user <seqera_user>]" >&2
           exit 2 ;;
    esac
done
if [ -z "$PROJECT" ] || [ -z "$SHEET" ]; then
    echo "usage: duplicate_run_check.sh --project <name> --samplesheet <path> [--workspace <ws>] [--user <seqera_user>]" >&2
    exit 2
fi
[ -n "$WS" ] || WS="$(setting workspace_id --required)" || exit 2
[ -n "$USER_FILTER" ] || USER_FILTER="$(setting seqera_user)"

TW="$(setting tw_bin tw)"
TOKEN_FILE="${SEQERA_TOKEN_FILE:-$(dirname "$SETTINGS_FILE")/.seqera_token}"
if [ -z "${TOWER_ACCESS_TOKEN:-}" ] && [ -r "$TOKEN_FILE" ]; then
    TOWER_ACCESS_TOKEN="$(cat "$TOKEN_FILE")"
    export TOWER_ACCESS_TOKEN
fi

out=$("$TW" -o json runs list --workspace "$WS" 2>&1) \
    || { echo "ERROR: could not list runs - $out" >&2; exit 2; }

filter='.workflows[] | select(.workflow.status == "SUBMITTED" or .workflow.status == "RUNNING")'
[ -n "$USER_FILTER" ] && filter="$filter | select(.workflow.userName == \"$USER_FILTER\")"
rows=$(jq -r "$filter | [.workflow.id, .workflow.runName, .workflow.status] | @tsv" <<<"$out" 2>/dev/null)
[ -n "$rows" ] || exit 0

sheet_base=$(basename -- "$SHEET")
sheet_stem="${sheet_base%.*}"

# Template, not a hardcoded sentence - see scripts/parallel_watch_check.sh's
# own comment on why this text lives in scripts/intro/<lang>/ instead.
LANGK="$(setting language zh-TW)"
TPL_DIR="$HERE/intro/$LANGK"
[ -d "$TPL_DIR" ] || TPL_DIR="$HERE/intro/zh-TW"
TPL=$(cat "$TPL_DIR/duplicate_run_warning.txt" 2>/dev/null)
[ -n "$TPL" ] || TPL="DUPLICATE-LIKE: run {{ID}} ({{NAME}}, {{STATUS}}) in project {{PROJECT}} already looks like this samplesheet."

found=0
while IFS=$'\t' read -r id runname status; do
    [ -n "$id" ] || continue
    params=$("$TW" runs view -i "$id" --workspace "$WS" --params 2>/dev/null)
    outdir=$(sed -n 's/^outdir:[[:space:]]*//p' <<<"$params" | head -1 | sed -e "s/^['\"]//" -e "s/['\"]\$//")
    [ -n "$outdir" ] || continue

    # docs/SETTINGS.md's own shape: .../<project>/runs/<run-dir>/results
    proj=$(sed -E 's#/runs/[^/]+/results/?$##' <<<"$outdir")
    proj="${proj##*/}"
    [ "$proj" = "$PROJECT" ] || continue

    input=$(sed -n 's/^input:[[:space:]]*//p' <<<"$params" | head -1 | sed -e "s/^['\"]//" -e "s/['\"]\$//")
    [ -n "$input" ] || continue
    input_slug="${input%%\?*}"
    input_slug="${input_slug%/}"
    input_slug="${input_slug##*/}"
    input_stem="${input_slug%.*}"

    if [ "$input_stem" = "$sheet_stem" ] || [ "$input_slug" = "$sheet_base" ]; then
        found=1
        line="${TPL//\{\{ID\}\}/$id}"
        line="${line//\{\{NAME\}\}/$runname}"
        line="${line//\{\{STATUS\}\}/$status}"
        line="${line//\{\{PROJECT\}\}/$PROJECT}"
        printf '%s\n' "$line"
    fi
done <<< "$rows"

[ "$found" = 0 ] && exit 0
exit 1
