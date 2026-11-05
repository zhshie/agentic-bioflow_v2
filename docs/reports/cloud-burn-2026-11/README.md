# Cloud-burn 2026-11 reports

- MU01 - Mutation run: platform/abf_platform/common.py - 38 hand-made mutants, 13 killed, 25 survived (24 real, 1 equivalent); parse_iso_epoch, extract_error, run_failure_reason and token parsing are barely pinned by tests.
- MU02 - Mutation run: platform/abf_platform/validate.py - 48 hand-made mutants, 42 killed, 6 survived (5 real, 1 equivalent); gaps are mostly in extension-pattern comparison (multi-dot, case, hyphen).
- MU03 - Mutation run: platform/abf_platform/compute_envs.py - 101 hand-made mutants, 54 killed, 47 survived (44 real, 3 equivalent); Slurm limits, cloud workDir shapes and storage bookkeeping are unasserted.
# Cloud-burn reports, 2026-11

- MU04: Mutation run on platform/abf_platform/cloud_cost.py. 54 mutants, 30 killed, 20 real survivors (mostly the monthly cap check and odd-number pricing), all killed by a proposed new test file.
- MU05: Mutation run on platform/abf_platform/http_auth.py. 59 mutants, 28 real survivors (session table, ContextVar reset, discovery document), all covered by a proposed new test file.
- MU06: Mutation run on platform/abf_station/rules.py (FORBIDDEN unit). 40 mutants, 20 killed, 20 survivors, all killed by 15 proposed unit tests; no change to rules.py needed.
