# 013a: report facts template in the delivery package, no AI wording progress ledger

- [x] tests/report_facts_test.sh + build_package_test.sh additions (RED commit): TC-001..021, 030..041, C06
- [x] scripts/report_facts.py (new, stdlib only, deterministic)
- [x] scripts/build_package.sh: calls it, writes report.md + .report.md.sha256, edited report.md kept -> report.facts.md + one stderr line; header list updated
