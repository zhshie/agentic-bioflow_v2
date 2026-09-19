#!/bin/bash
# Nothing existing: this is glue over four scripts this plugin already ships
# (agent_ctl.sh, check_resource_contract.sh, collect_provenance.py,
# inventory_outputs.py), run together so a caller pays for one `on_site.sh`
# session instead of two or three. No outside tool bundles "is Platform's
# outputs reader for this run still up, does the site's resource floor still
# match SLURM, what can this run prove about itself, what is actually in its
# results tree" as one call, because no outside tool knows about this site's
# own scripts to begin with.
#
# One `on_site.sh` round trip for the checks that commonly run back-to-back
# once a run has SUCCEEDED: is the outputs reader still up, does this site's
# resource-floor config still match SLURM, what can the run prove about
# itself, and what does the results tree actually contain.
#
# Every check here already exists and keeps working standalone. This only
# saves the round trips. GitHub issue #13's own accounting is why it matters: under
# `reach: ssh` every `on_site.sh` call is a real ssh session, and this site's
# sshd caps how many a single connection may carry at once (PITFALLS 16e) -
# so `commands/downstream.md`'s step 1 (agent) and step 2's own >500MB branch
# (inventory, plus provenance to learn the run's pipeline+revision before
# fetching its `docs/output.md`) used to cost two or three of those in a row.
# `scripts/on_site.sh --script scripts/site_report.sh` now costs one.
#
#   site_report.sh <results-dir> [--run-id <id>] [--workspace <ws>]
#
# Prints one `== <name> ==` section per check, always in this order, and
# never stops at the first failure - T10's own rule applies here too: a
# caller reading a bundled report wants every problem in one pass, not just
# the first one it happened to hit. `agent`/`resources`/`provenance` skip
# gracefully when they are missing what they need (no --run-id, sacctmgr not
# on this host) rather than failing the whole call over one section.
#
# Exit status is 1 only for the two checks that mean "this deployment itself
# is broken right now" - agent offline, resource-contract drift - the same
# two preflight.sh already gates a launch on. `provenance` and `inventory`
# report their own gaps inline (docs/PRINCIPLES.md invariant 9: a missing
# versions file or an empty results tree is a note in the section, never a
# reason to fail the whole call) and never affect the exit code.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RESULTS=""
RUN_ID=""
WORKSPACE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --run-id)    RUN_ID="${2:?usage: --run-id <id>}"; shift 2 ;;
        --workspace) WORKSPACE="${2:?usage: --workspace <id>}"; shift 2 ;;
        --)          shift; break ;;
        -*)          echo "unknown option: $1" >&2; exit 2 ;;
        *)
            if [ -z "$RESULTS" ]; then RESULTS="$1"
            else echo "unexpected argument: $1" >&2; exit 2; fi
            shift ;;
    esac
done
[ -n "$RESULTS" ] || {
    echo "usage: site_report.sh <results-dir> [--run-id <id>] [--workspace <ws>]" >&2
    exit 2
}

fail=0

echo "== agent =="
if [ -n "$RUN_ID" ]; then
    "$HERE/agent_ctl.sh" online "$RUN_ID" || fail=1
else
    echo "skipped - no --run-id given, so there is no run to ask Platform about"
fi
echo

echo "== resources =="
"$HERE/check_resource_contract.sh" || fail=1
echo

echo "== provenance =="
if [ -d "$RESULTS" ]; then
    if [ -n "$RUN_ID" ]; then
        "$HERE/collect_provenance.py" --brief --run-id "$RUN_ID" \
            ${WORKSPACE:+--workspace "$WORKSPACE"} "$RESULTS"
    else
        "$HERE/collect_provenance.py" --brief "$RESULTS"
    fi
else
    echo "skipped - $RESULTS does not exist here"
fi
echo

echo "== inventory =="
if [ -d "$RESULTS" ]; then
    "$HERE/inventory_outputs.py" "$RESULTS"
else
    echo "skipped - $RESULTS does not exist here"
fi

exit $fail
