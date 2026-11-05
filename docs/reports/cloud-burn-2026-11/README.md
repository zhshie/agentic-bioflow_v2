# cloud-burn 2026-11 reports

- R1 - platform coverage report and split of the sweep section 6 heuristic list: 146 names checked, 142 are in fact executed; 20 never-run safety gates and refusal branches ranked for new tests, plus 2 minor findings.
- R2 - abf_station fix design (path-rule duplication, F1, F2): root cause, fix, RED tests and measured blast radius for a parity test, a fail-open samplesheet-cell check and a scoped resourceLimits hoist.
- R3 - tests that hard-code a count, list or hash: 12 findings and a migration order for moving them to one source.
# Cloud-burn reports, 2026-11

- MU04: Mutation run on platform/abf_platform/cloud_cost.py. 54 mutants, 30 killed, 20 real survivors (mostly the monthly cap check and odd-number pricing), all killed by a proposed new test file.
- MU05: Mutation run on platform/abf_platform/http_auth.py. 59 mutants, 28 real survivors (session table, ContextVar reset, discovery document), all covered by a proposed new test file.
- MU06: Mutation run on platform/abf_station/rules.py (FORBIDDEN unit). 40 mutants, 20 killed, 20 survivors, all killed by 15 proposed unit tests; no change to rules.py needed.
