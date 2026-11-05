# Cloud-burn 2026-11 reports

- AR06 - Adversarial review of platform/abf_station/launch.py - 14 surviving findings; the top one is that a samplesheet cell outside the path-column heuristic (file:// URI, ../ path) passes both read-root locks and every cloud checker.
# Cloud-burn reports, 2026-11

- MU04: Mutation run on platform/abf_platform/cloud_cost.py. 54 mutants, 30 killed, 20 real survivors (mostly the monthly cap check and odd-number pricing), all killed by a proposed new test file.
- MU05: Mutation run on platform/abf_platform/http_auth.py. 59 mutants, 28 real survivors (session table, ContextVar reset, discovery document), all covered by a proposed new test file.
- MU06: Mutation run on platform/abf_station/rules.py (FORBIDDEN unit). 40 mutants, 20 killed, 20 survivors, all killed by 15 proposed unit tests; no change to rules.py needed.
