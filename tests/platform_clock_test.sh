#!/bin/bash
# The second run_all.sh entry of the platform tests (follow-up 1 of feature 007b, F3): the two test files that check the clock
# closely and so run alone, one after the other, with nothing else running. Not a second copy of tests/platform_test.sh: this
# only picks its part (ABF_PLATFORM_PART=clock) and hands over, so the checks of Java and the pinned downloads, the CI rule
# (nothing may be skipped) and the summary line are the same code. The other test files are tests/platform_test.sh's part.
#
# Why two entries: the whole platform suite in one entry took 298 s of the 300 s limit of run_all.sh on a CI runner, and the
# limit is there to catch a hang, so raising it was not the answer. Each entry now takes about half of that.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ABF_PLATFORM_PART=clock
exec bash "$HERE/platform_test.sh" "$@"
