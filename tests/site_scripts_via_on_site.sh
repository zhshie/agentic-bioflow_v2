#!/bin/bash
# Z4: a command file that names a site-only script must route it through
# scripts/on_site.sh - see docs/SITE_ADAPTER.md, contract 6 ("on_site.sh is
# the only sanctioned implementation. The command layer may not call ssh
# itself").
#
# why_pending.sh needs the site's own scheduler tools; egress_ctl.sh and
# agent_ctl.sh both abort on ${LAB_RUNS_DIR:?} before doing anything, because
# neither variable nor state directory exists on a laptop under `reach: ssh`
# (docs/SETTINGS.md: on the user's own machine, set nothing). Read bare, all
# three fail on the machine Claude's shell is actually running on -
# why_pending.sh exits 2, the other two abort before their first line of real
# work. check_resource_contract.sh is the same shape of script and is listed
# for the same reason, even though nothing in commands/ names it today.
#
# Crude, like the other vocabulary checks here: a bare `scripts/<name>` is
# what actually happened (runs.md:43, :90, :183; downstream.md:50; setup.md
# :278, :284 before this commit), so the check is "does the same line that
# names the script also name on_site.sh". A prose mention with no `scripts/`
# path in front of it - e.g. "the `why_pending.sh` combination" in launch.md,
# describing task_health.sh's own internals rather than instructing anyone to
# run it - is deliberately not flagged: task_health.sh already routes through
# on_site.sh itself (scripts/task_health.sh does this), so nothing here
# depends on the command layer routing it a second time.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

SITE_ONLY='why_pending|egress_ctl|agent_ctl|check_resource_contract'

fail=0
hits=$(grep -rnE "scripts/($SITE_ONLY)\.(sh|py)" "$ROOT/commands" 2>/dev/null) || true

if [ -n "$hits" ]; then
    while IFS= read -r hit; do
        [ -n "$hit" ] || continue
        if grep -q 'on_site\.sh' <<<"$hit"; then
            echo "ok: $(sed "s|^$ROOT/||" <<<"$hit")"
        else
            echo "FAIL: $(sed "s|^$ROOT/||" <<<"$hit")"
            echo "  names a site-only script with no on_site.sh on the same line"
            fail=1
        fi
    done <<<"$hits"
else
    echo "FAIL: no site-only script is named in commands/ at all - this test has nothing to check."
    echo "  (expected at least why_pending.sh, egress_ctl.sh and agent_ctl.sh to appear)"
    fail=1
fi

if [ "$fail" = 1 ]; then
    echo
    echo "FAIL: a site-only script is called where the site cannot be reached."
    exit 1
fi
echo "OK: every site-only script named in commands/ is routed through scripts/on_site.sh"
