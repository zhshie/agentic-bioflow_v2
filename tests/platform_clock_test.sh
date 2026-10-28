#!/bin/bash
# The fourth run_all.sh entry of the platform tests (follow-up 1 of feature 007b, F3): the two test files that check the clock
# closely and so run alone, one after the other, with nothing else running. Not a second copy of tests/platform_test.sh: this
# only picks its part (ABF_PLATFORM_PART=clock) and hands over, so the checks of Java and the pinned downloads, the CI rule
# (nothing may be skipped) and the summary line are the same code. The other test files are the parts of tests/platform_test.sh (part 1) and tests/platform_shard_<n>_test.sh (parts 2 to 8).
#
# Why separate entries: the whole platform suite in one entry came too near the limit of run_all.sh, and the limit is there to
# catch a hang, so raising it was not the answer. The suite is cut into eight parts and this clock part.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ABF_PLATFORM_PART=clock
exec bash "$HERE/platform_test.sh" "$@"
