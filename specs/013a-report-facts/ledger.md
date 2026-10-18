# 013a: report facts template in the delivery package, no AI wording progress ledger

- [x] tests/report_facts_test.sh + build_package_test.sh additions (RED commit): TC-001..021, 030..041, C06
- [x] scripts/report_facts.py (new, stdlib only, deterministic)
- [x] scripts/build_package.sh: calls it, writes report.md + .report.md.sha256, edited report.md kept -> report.facts.md + one stderr line; header list updated
- [x] fix round: scripts/report_facts.py was 100644 in git, so build_package.sh failed with Permission denied on Linux/CI; now 100755, with a test (TC-030) that checks the git mode
