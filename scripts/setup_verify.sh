#!/bin/bash
# T27: the "setup once is enough" contract's own check. `:setup` runs this
# FIRST, before treating a machine as needing repair or first-run at all -
# so a machine that is already fully configured hears that in seconds,
# instead of being walked into the repair flow's ten checks for a machine
# that needs none of them.
#
# Not scripts/preflight.sh alone, and not a copy of it: preflight already
# answers "is everything ready for :launch to gate on" - a different
# question from "does :setup itself have anything left to do here" - and a
# settings file that is entirely absent has to be its own fast, cheap
# answer before preflight is asked anything: several of preflight's own
# checks throw for the wrong reason (an empty token file path, an empty
# compute-env name) rather than reporting cleanly when there was never a
# settings file to read in the first place. This checks that first, then
# defers everything else to preflight.sh rather than re-implementing any of
# its checks (docs mirrors scripts/status.sh's own rule for the same reason).
#
#   setup_verify.sh          prints a verdict; exit 0 = already fully set up,
#                             nothing for :setup to do. Any other exit code =
#                             :setup should continue into repair or first-run.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/settings.sh"

if [ "$SETTINGS_FOUND" != 1 ]; then
    echo "No settings file yet on this machine - this is a first run, not a repair."
    root_missing_reason
    exit 1
fi

PF_OUT=$(bash "$HERE/preflight.sh" 2>&1); PF_RC=$?
if [ "$PF_RC" = 0 ]; then
    echo "This machine is already set up. No need to run setup again."
    echo
    printf '%s\n' "$PF_OUT"
    exit 0
fi

echo "Settings exist, but preflight found something still missing - continuing"
echo "into repair rather than first-run (commands/setup.md's 'Present -> repair')."
echo
printf '%s\n' "$PF_OUT"
exit 1
