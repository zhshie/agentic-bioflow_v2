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
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

TERMS='slurm|sbatch|squeue|scontrol|sacctmgr|qos|partition|relay|proxy|singularity|module load'

hits=$(grep -rInE "$TERMS" "$ROOT/commands" 2>/dev/null | sed "s|^$ROOT/||") || true

if [ -n "$hits" ]; then
    printf '%s\n' "$hits"
    echo
    echo "FAIL: the command layer names site machinery. Move it behind the adapter."
    exit 1
fi
echo "OK: commands/ names no scheduler, no egress mechanism, no container runtime"
