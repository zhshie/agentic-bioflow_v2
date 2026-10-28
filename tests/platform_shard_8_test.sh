#!/bin/bash
# One of the run_all.sh entries of the platform tests: part 8 of the eight parts of the shards. Not a second copy of
# tests/platform_test.sh: this only picks its part (ABF_PLATFORM_PART=8) and hands over, so the checks of Java and the pinned
# downloads, the CI rule (nothing may be skipped) and the summary line are the same code, and the venv and the downloads in the
# cache are shared with the other entries. The name is fixed by tests/run_all.sh, which refuses to quarantine platform_shard_*_test.sh.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ABF_PLATFORM_PART=8
exec bash "$HERE/platform_test.sh" "$@"
