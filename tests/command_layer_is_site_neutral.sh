#!/bin/bash
# Invariant 4: one cluster is not the world.
#
# The command layer says what needs to be found out; the site adapter knows how
# to find it out. A command that runs `squeue` or greps a proxy log is a command
# that only works in one building - on a cloud compute environment there is no
# scheduler to ask and no proxy to have refused anything.
#
# This is a vocabulary check, which is crude but catches the thing that actually
# happens: someone pastes a working diagnostic inline because it is right there
# in their terminal. If a term below genuinely belongs in the command layer,
# that is a design decision worth arguing for - see docs/SITE_ADAPTER.md.
#
# hooks/ is deliberately NOT scanned. The safety net is allowed to be broader
# than the abstraction: the launch gate triggers on `sbatch` because a run
# started that way still needs confirming, and the deletion guard names the
# directories this deployment must never lose. Both are correct, and both would
# fail this check.
#
# skills/ IS scanned, alongside commands/: skills/operational/SKILL.md is the
# same operational knowledge reachable without a slash command
# (CLAUDE.md, "Repository layout"), so it is bound by the same neutrality this
# check exists to hold commands/*.md to.
#
# The term list and the `reach: ssh` exemption live in tests/lib/site_terms.sh,
# shared with tests/launch_provenance_test.sh so the two cannot drift apart
# (bug: false-green-tests, item 1).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
. "$HERE/lib/site_terms.sh"

raw=$(site_terms_grep "$ROOT/commands" "$ROOT/skills" 2>&1)
rc=$?
if [ "$rc" -ge 2 ]; then
    printf '%s\n' "$raw"
    echo
    echo "FAIL: the site-term scan itself errored (grep exit $rc) - a broken scan is not a clean pass."
    exit 1
fi

hits=$(printf '%s\n' "$raw" | site_terms_allow | sed "s|^$ROOT/||" | grep -v '^$')

if [ -n "$hits" ]; then
    printf '%s\n' "$hits"
    echo
    echo "FAIL: the command layer names site machinery. Move it behind the adapter."
    exit 1
fi
echo "OK: commands/ and skills/ name no scheduler, no egress mechanism, no container runtime"
