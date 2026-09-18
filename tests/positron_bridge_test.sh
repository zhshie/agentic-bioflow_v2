#!/bin/bash
# Tests extensions/positron-bridge/src/bridge-core.js - the token check, the
# loopback check, the state-file path on all three OSes, and the image diff
# that summarizes what a run drew.
#
# What this does not, and cannot, test: extension.ts's own wiring to the
# vscode/positron APIs (activate/deactivate, the HTTP server, the actual call
# to positron.runtime.executeCode). Those only exist inside a running
# Positron window, and standing one up here would mean testing a fake instead
# of the real API surface - the same boundary
# tests/positron_run_test.sh draws around scripts/positron_run.py, which
# tests everything up to the socket and no further. That half was checked by
# hand against a live Positron; extensions/positron-bridge/src/extension.ts's
# own comments say what was verified and what a future change must re-check.
#
# No network, no npm install: bridge-core.js is plain Node.js with no
# dependency beyond the runtime itself, so this runs it directly with
# whatever `node` is already on PATH - the same "runs standalone" property
# every other script in this repo has (docs/PRINCIPLES.md, invariant 5).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_JS="$HERE/extensions/positron-bridge/test/bridge-core.test.js"

if ! command -v node >/dev/null 2>&1; then
  echo "SKIP: positron_bridge_test.sh - no node on PATH (extensions/positron-bridge needs Node.js to test or build)"
  exit 0
fi

if [ ! -f "$HERE/extensions/positron-bridge/src/bridge-core.js" ]; then
  echo "FAIL: extensions/positron-bridge/src/bridge-core.js is missing"
  exit 1
fi

node "$TEST_JS"
exit $?
