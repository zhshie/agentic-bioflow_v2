#!/bin/bash
# T24: `/runs` with no argument becomes a work board - every run this member
# has in flight right now, across every pipeline, each with a short code so
# a follow-up `/runs <code>` never needs the raw Platform run id typed back.
#
# Not `tw runs list` alone: that answers with EVERY run in the workspace,
# every member, every terminal state it ever reached - reading that as "what
# is going on right now" is the same misread PRINCIPLES.md already warns
# about for an empty list (commands/runs.md's own workspace-scoping note).
# This filters to this member's own SUBMITTED/RUNNING rows and adds the two
# things Platform's own listing does not carry: which project a run belongs
# to, and where its outputs land on the site - both read from the run's own
# launch params (`tw runs view --params`), the exact call commands/launch.md
# step 5's route (1) already uses. Nothing here is a second copy of run
# state (`docs/PRINCIPLES.md`, invariant 2): every field is re-asked of
# Platform on every call.
#
# Codes are assigned fresh on every call, never stored: sort the active runs
# by Platform's own run id and number them r1, r2, ... - deterministic, so
# two calls in the same session agree on a code as long as the same runs are
# still active, with no state file this project's invariant 2 already rules
# out.
#
#   runs_board.sh [--workspace <ws>] [--user <seqera_user>] [--no-site-check]
#       prints the board, one line per active run
#   runs_board.sh --resolve <code> [--workspace <ws>] [--user <seqera_user>]
#       prints just that code's run id (for `/runs <code>` to act on) and
#       exits 0, or exits 1 with nothing on stdout if the code matches
#       nothing right now
#
# --no-site-check skips scripts/runs_board_site_probe.sh - useful when reach
# is 'none' (nothing to probe, docs/SITE_ADAPTER.md contract 6) or when the
# caller only wants Platform's own view.
#
# Measured 2026-09-18 against a live `tw -o json runs list` (54 runs, one
# workspace): each entry is `{orgId, orgName, starred, workflow, workspaceId,
# workspaceName}`, and everything this script reads - id, runName,
# projectName, status, submit (ISO 8601, `...Z`), userName - lives under
# `.workflow`. `.labels` is not on the entry without --labels (PITFALLS 30's
# measurement was made with it), so nothing here depends on labels.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

TW="$(setting tw_bin tw)"
WS=""
USER_FILTER=""
RESOLVE=""
SITE_CHECK=1
while [ $# -gt 0 ]; do
    case "$1" in
        --workspace)      WS="${2:?--workspace needs a value}"; shift 2 ;;
        --user)           USER_FILTER="${2:?--user needs a value}"; shift 2 ;;
        --resolve)        RESOLVE="${2:?--resolve needs a code}"; shift 2 ;;
        --no-site-check)  SITE_CHECK=0; shift ;;
        *) echo "usage: runs_board.sh [--workspace <ws>] [--user <seqera_user>] [--resolve <code>] [--no-site-check]" >&2
           exit 2 ;;
    esac
done
[ -n "$WS" ] || WS="$(setting workspace_id --required)" || exit 2
[ -n "$USER_FILTER" ] || USER_FILTER="$(setting seqera_user)"

TOKEN_FILE="${SEQERA_TOKEN_FILE:-$(dirname "$SETTINGS_FILE")/.seqera_token}"
if [ -z "${TOWER_ACCESS_TOKEN:-}" ] && [ -r "$TOKEN_FILE" ]; then
    TOWER_ACCESS_TOKEN="$(cat "$TOKEN_FILE")"
    export TOWER_ACCESS_TOKEN
fi

out=$("$TW" -o json runs list --workspace "$WS" 2>&1) \
    || { echo "ERROR: could not list runs - $out" >&2; exit 2; }

# Active = not yet terminal. SUBMITTED and RUNNING are the two statuses
# commands/runs.md itself still has open branches for; SUCCEEDED, FAILED,
# CANCELLED and any UNKNOWN Platform adds later are already resolved and
# belong to a history view, not a work board.
filter='.workflows[] | select(.workflow.status == "SUBMITTED" or .workflow.status == "RUNNING")'
[ -n "$USER_FILTER" ] && filter="$filter | select(.workflow.userName == \"$USER_FILTER\")"

rows=$(jq -r "$filter | [.workflow.id, .workflow.runName, .workflow.projectName, .workflow.status, .workflow.submit] | @tsv" <<<"$out" 2>/dev/null)

if [ -z "$rows" ]; then
    if [ -n "$RESOLVE" ]; then echo "no active run matches code '$RESOLVE'" >&2; exit 1; fi
    echo "nothing in flight for ${USER_FILTER:-this workspace} right now."
    exit 0
fi

now_ms=$(( $(date +%s) * 1000 ))

# LC_ALL=C: run ids are opaque alphanumeric strings, not numbers - a locale
# collation could reorder them between two calls in the same session, which
# would reassign codes out from under a user mid-conversation.
sorted=$(LC_ALL=C sort -t "$(printf '\t')" -k1,1 <<<"$rows")

declare -a IDS=() CODES=()
n=0
while IFS=$'\t' read -r id runname pipeline status submit; do
    n=$((n+1))
    code="r$n"

    if [ -n "$RESOLVE" ]; then
        if [ "$RESOLVE" = "$code" ]; then printf '%s\n' "$id"; exit 0; fi
        continue
    fi

    # Elapsed, from Platform's own submit timestamp (epoch ms) - never a
    # locally kept clock, which invariant 2 already rules out as a second
    # copy of run state.
    elapsed="?"
    case "$submit" in
        ''|null) elapsed="?" ;;
        *[!0-9]*) elapsed="?" ;;
        *)
            d=$(( (now_ms - submit) / 1000 ))
            [ "$d" -lt 0 ] && d=0
            elapsed="$((d/3600))h$(((d%3600)/60))m"
            ;;
    esac

    # Project and site path both come from this run's own launch params -
    # never re-derived from a guess at the run name, which nothing here
    # controls (launch.md never passes `--name`).
    params=$("$TW" runs view -i "$id" --workspace "$WS" --params 2>/dev/null)
    outdir=$(sed -n 's/^outdir:[[:space:]]*//p' <<<"$params" | head -1 | sed -e "s/^['\"]//" -e "s/['\"]\$//")
    project="?"
    if [ -n "$outdir" ]; then
        # docs/SETTINGS.md's own shape: .../<project>/runs/<run-dir>/results
        project=$(sed -E 's#/runs/[^/]+/results/?$##' <<<"$outdir")
        project="${project##*/}"
        [ -n "$project" ] || project="?"
    fi

    printf '%-4s %-28s %-24s %-10s %-8s %-16s %s\n' \
        "$code" "$runname" "$pipeline" "$status" "$elapsed" "$project" "${outdir:-?}"
    IDS+=("$id"); CODES+=("$code")
done <<< "$sorted"

if [ -n "$RESOLVE" ]; then
    echo "no active run matches code '$RESOLVE'" >&2
    exit 1
fi

# The site-side stuck check: ONE round trip for every run just listed, not
# one per run - see scripts/runs_board_site_probe.sh's own header for why
# that distinction is the whole point of this file existing.
if [ "$SITE_CHECK" = 1 ] && [ "${#IDS[@]}" -gt 0 ]; then
    probe=$(bash "$HERE/runs_board_site_probe.sh" "$WS" "${IDS[@]}" 2>/dev/null)
    if [ -n "$probe" ] && grep -q 'STUCK' <<<"$probe"; then
        echo
        echo "site-side check (one round trip for all of the above):"
        while IFS=' ' read -r rid rest; do
            [ -n "$rid" ] || continue
            for i in "${!IDS[@]}"; do
                if [ "${IDS[$i]}" = "$rid" ]; then
                    printf '%s (%s): %s\n' "${CODES[$i]}" "$rid" "$rest"
                fi
            done
        done < <(grep 'STUCK' <<<"$probe")
    fi
fi

# Guardrail 2 (T26): the board is where a growing count is actually seen, so
# it is folded in here too. scripts/parallel_watch_check.sh stays the
# standalone form prepare_launch.sh calls BEFORE one more run is launched.
warn=$(bash "$HERE/parallel_watch_check.sh" --workspace "$WS" ${USER_FILTER:+--user "$USER_FILTER"} 2>/dev/null)
if [ -n "$warn" ]; then
    echo
    printf '%s\n' "$warn"
fi
