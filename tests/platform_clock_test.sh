#!/bin/bash
# A run_all.sh entry of the platform tests (follow-up 1 of feature 007b, F3): the clock part, which is one test file,
# tests/test_station_e2e.py. It checks the clock closely and so runs alone, with nothing else running. The other file that checks the
# clock, tests/test_nextflow_e2e.py, is the entry of its own in tests/platform_clock_2_test.sh. Not a second copy of tests/platform_test.sh: this
# only picks its part (ABF_PLATFORM_PART=clock) and hands over, so the checks of Java and the pinned downloads, the CI rule
# (nothing may be skipped) and the summary line are the same code. The other test files are the parts of tests/platform_test.sh (part 1) and tests/platform_shard_<n>_test.sh (parts 2 to 8).
#
# Why separate entries: the whole platform suite in one entry came too near the limit of run_all.sh, and the limit is there to
# catch a hang, so raising it was not the answer. The suite is cut into eight parts and the two clock parts, one file each.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ABF_PLATFORM_PART=clock
exec bash "$HERE/platform_test.sh" "$@"
