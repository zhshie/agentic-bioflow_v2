#!/bin/bash
# A run_all.sh entry of the platform tests: the clock2 part, which is one test file, tests/test_nextflow_e2e.py. It checks the clock
# closely (a rebuilt end time must be within a second of the live one) and so runs alone, with nothing else running. The other clock
# file is the entry in tests/platform_clock_test.sh. Not a second copy of tests/platform_test.sh: this only picks its part
# (ABF_PLATFORM_PART=clock2) and hands over, so the checks of Java and the pinned downloads, the CI rule (nothing may be skipped)
# and the summary line are the same code. The file name is fixed by the patterns in tests/run_all.sh that refuse to quarantine
# a platform entry and that weigh it as a heavy one when the suite is split into jobs.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ABF_PLATFORM_PART=clock2
exec bash "$HERE/platform_test.sh" "$@"
