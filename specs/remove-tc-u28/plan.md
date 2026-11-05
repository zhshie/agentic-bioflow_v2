Why: TC-U28 diffs the merge-base with origin/v3 for platform/, so it goes red on every branch that touches platform/ and cannot fail once merged; it is a stale guard.
What: delete only the TC-U28 block (if mb=... else skip ...; fi) from tests/platform_upgrade_test.sh; no other assertion changes.
Maintainer words (2026-11-05): '刪'
