# cloud-burn 2026-11 reports

- R1 - platform coverage report and split of the sweep section 6 heuristic list: 146 names checked, 142 are in fact executed; 20 never-run safety gates and refusal branches ranked for new tests, plus 2 minor findings.
- R2 - abf_station fix design (path-rule duplication, F1, F2): root cause, fix, RED tests and measured blast radius for a parity test, a fail-open samplesheet-cell check and a scoped resourceLimits hoist.
- R3 - tests that hard-code a count, list or hash: 12 findings and a migration order for moving them to one source.
# Cloud-burn 2026-11 reports

- MU01 - Mutation run: platform/abf_platform/common.py - 38 hand-made mutants, 13 killed, 25 survived (24 real, 1 equivalent); parse_iso_epoch, extract_error, run_failure_reason and token parsing are barely pinned by tests.
- MU02 - Mutation run: platform/abf_platform/validate.py - 48 hand-made mutants, 42 killed, 6 survived (5 real, 1 equivalent); gaps are mostly in extension-pattern comparison (multi-dot, case, hyphen).
- MU03 - Mutation run: platform/abf_platform/compute_envs.py - 101 hand-made mutants, 54 killed, 47 survived (44 real, 3 equivalent); Slurm limits, cloud workDir shapes and storage bookkeeping are unasserted.
- AR06 - Adversarial review of platform/abf_station/launch.py - 14 surviving findings; the top one is that a samplesheet cell outside the path-column heuristic (file:// URI, ../ path) passes both read-root locks and every cloud checker.
# Cloud-burn reports, 2026-11

- AR08 - Adversarial review of cloud_cost.py, su.py, web_cost.py: the SU card and cloud cap miscount (default_site pricing, partial sums, in-flight runs at $0, unpriceable tasks dropping a run), 13 surviving findings.
- AR09 - Adversarial review of web.py and web_board.py: exponent-form numbers sent as text, lost-run Resume offers the action layer refuses, SVG served without a sandbox CSP, shared login bucket behind a proxy, 15 surviving findings.
- AR10 - Adversarial review of web_settings.py, web_launch.py, web_upload.py, uploads_web.py, actions/uploads.py: same-name uploads overwrite registered dataset objects, resume-edit refuses its own untouched box, unregistered batches after job prune, 15 surviving findings.
- MU04: Mutation run on platform/abf_platform/cloud_cost.py. 54 mutants, 30 killed, 20 real survivors (mostly the monthly cap check and odd-number pricing), all killed by a proposed new test file.
- MU05: Mutation run on platform/abf_platform/http_auth.py. 59 mutants, 28 real survivors (session table, ContextVar reset, discovery document), all covered by a proposed new test file.
- MU06: Mutation run on platform/abf_station/rules.py (FORBIDDEN unit). 40 mutants, 20 killed, 20 survivors, all killed by 15 proposed unit tests; no change to rules.py needed.
