#!/bin/bash
# Nothing existing: no tool here counts a member's own in-flight runs
# against a shared connection's session budget - this is a handful of lines
# of jq over what `tw runs list` already returns, compared against the
# `ssh_max_parallel` setting `scripts/on_site.sh` already enforces.
#
# Guardrail 2 (T26): warn before arming one more background watch pushes the
# shared site connection close to PITFALLS.md 16e's session cap
# (`ssh_max_parallel`, default 4). The failure there is a silent hang, not
# an error, so the only real defence is saying something before it happens.
#
# Counts this member's own SUBMITTED/RUNNING runs as a proxy for how many
# background watches (commands/launch.md step 9) are already sharing the
# connection - each run launched there arms exactly one. Approximate on
# purpose: a watch can end early, `/runs` itself makes its own occasional
# call too, and this project keeps no file that would let it count watches
# directly (`docs/PRINCIPLES.md`, invariant 2 - no file here records run
# state, and a watch is not run state either). So this warns a step before
# the cap rather than claiming to compute the exact number of open sessions.
#
#   parallel_watch_check.sh [--workspace <ws>] [--user <seqera_user>]
#
# Prints nothing and exits 0 when there is headroom. Prints one line and
# exits 1 when the count is at or past `ssh_max_parallel - 1` (leaving room
# for at most one more before the cap itself). Exit 2 on a usage/settings
# error.
#
# Not folded only into scripts/runs_board.sh: perf/latency's
# scripts/prepare_launch.sh needs this BEFORE a run is launched, at a point
# where the board's own per-run detail is not wanted yet - just the count
# and the verdict. Once prepare_launch.sh exists it should call
#
#   scripts/parallel_watch_check.sh --workspace <ws> [--user <seqera_user>]
#
# and fold whatever line it prints (if any) into its own pre-launch summary,
# the same way scripts/duplicate_run_check.sh documents itself being called.
# Until prepare_launch.sh exists, commands/launch.md step 9 calls this
# directly, and scripts/runs_board.sh also calls it (see its own header) so
# a growing count shows up wherever a member is actually looking.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

WS=""
USER_FILTER=""
while [ $# -gt 0 ]; do
    case "$1" in
        --workspace) WS="${2:?--workspace needs a value}"; shift 2 ;;
        --user)      USER_FILTER="${2:?--user needs a value}"; shift 2 ;;
        *) echo "usage: parallel_watch_check.sh [--workspace <ws>] [--user <seqera_user>]" >&2
           exit 2 ;;
    esac
done
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
n=$(jq -r "[$filter] | length" <<<"$out" 2>/dev/null)
case "$n" in ''|*[!0-9]*) n=0 ;; esac

MAXP="$(setting ssh_max_parallel 4)"
case "$MAXP" in ''|*[!0-9]*) MAXP=4 ;; esac

if [ "$n" -lt $((MAXP - 1)) ]; then
    exit 0
fi

# Template, not a hardcoded sentence: the text lives in scripts/intro/<lang>/
# the same way scripts/intro.sh's own opening text does, so it stays
# bilingual in one place rather than as a string baked into this script.
LANGK="$(setting language zh-TW)"
TPL_DIR="$HERE/intro/$LANGK"
[ -d "$TPL_DIR" ] || TPL_DIR="$HERE/intro/zh-TW"
msg=$(cat "$TPL_DIR/parallel_watch_warning.txt" 2>/dev/null)
[ -n "$msg" ] || msg="{{N}} runs in flight, close to ssh_max_parallel ({{MAX}})."
line="${msg//\{\{N\}\}/$n}"
line="${line//\{\{MAX\}\}/$MAXP}"
printf '%s\n' "$line"
exit 1
