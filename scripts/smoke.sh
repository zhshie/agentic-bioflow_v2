#!/usr/bin/env bash
# Post-deploy smoke check: read-only probes of a deployed site.
# Not curl: a bare curl cannot check status, redirects, header names in any case and a JSON
# body together, and the same probes must also run under pytest -m smoke.
# Usage: SMOKE_BASE_URL=<address of the site> bash scripts/smoke.sh
# Run it on the desktop host after deploy/platform-upgrade.sh. It never has a
# default address: with SMOKE_BASE_URL unset it checks nothing and exits 2.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -z "${SMOKE_BASE_URL:-}" ] || [ -z "$(printf '%s' "$SMOKE_BASE_URL" | tr -d '[:space:]')" ]; then
  echo "SMOKE_BASE_URL is not set: nothing was checked."
  echo "Usage: SMOKE_BASE_URL=<address of the site> bash scripts/smoke.sh"
  exit 2
fi

PY="${SMOKE_PYTHON:-python3}"
if ! "$PY" -c 'import pytest' >/dev/null 2>&1; then
  echo "pytest is not available for $PY. Install it (pip install pytest) or set SMOKE_PYTHON."
  exit 3
fi

cd "$ROOT" || exit 3
"$PY" -m pytest -o "markers=smoke: read-only checks against a deployed site; need SMOKE_BASE_URL" \
  -m smoke tests/smoke -rs -p no:cacheprovider
rc=$?

if [ "$rc" -ne 0 ]; then
  echo "Smoke checks failed. To go back: restore the data folder from the latest backup (deploy/backup.sh), check out the previous release in the platform checkout, reinstall (pip install ./platform), restart the three services; see docs/OPERATIONS.md section 4 (Upgrade)."
  exit "$rc"
fi
echo "Smoke checks passed."
exit 0
