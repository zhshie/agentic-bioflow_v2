# cloud-burn 2026-11 reports

- UI2: ui_check.py with axe-core, 6 pages x 1440/390 x zh/en. Eight critical axe meta-refresh hits on board and results, plus wording, launch-with-no-compute-environment and 390 px layout issues (11 findings).
- UI3: design report for settings-ce-table-mobile. The 390 px card layout already landed, but the viewport-keyed switch still cuts words mid-letter from about 901 to 1313 px; proposes a container query (4 findings).
- R4: real-process QA walk with verify-abf against a fake station. Most surfaces pass; findings include the Slurm computeQueue not reaching Nextflow, an all-green preflight that still refuses launch, and a set of CLI/MCP wording and validation gaps (16 findings).
# Cloud-burn 2026-11 reports

- AR06 - Adversarial review of platform/abf_station/launch.py - 14 surviving findings; the top one is that a samplesheet cell outside the path-column heuristic (file:// URI, ../ path) passes both read-root locks and every cloud checker.
# Cloud-burn reports, 2026-11

- AR08 - Adversarial review of cloud_cost.py, su.py, web_cost.py: the SU card and cloud cap miscount (default_site pricing, partial sums, in-flight runs at $0, unpriceable tasks dropping a run), 13 surviving findings.
- AR09 - Adversarial review of web.py and web_board.py: exponent-form numbers sent as text, lost-run Resume offers the action layer refuses, SVG served without a sandbox CSP, shared login bucket behind a proxy, 15 surviving findings.
- AR10 - Adversarial review of web_settings.py, web_launch.py, web_upload.py, uploads_web.py, actions/uploads.py: same-name uploads overwrite registered dataset objects, resume-edit refuses its own untouched box, unregistered batches after job prune, 15 surviving findings.
- MU04: Mutation run on platform/abf_platform/cloud_cost.py. 54 mutants, 30 killed, 20 real survivors (mostly the monthly cap check and odd-number pricing), all killed by a proposed new test file.
- MU05: Mutation run on platform/abf_platform/http_auth.py. 59 mutants, 28 real survivors (session table, ContextVar reset, discovery document), all covered by a proposed new test file.
- MU06: Mutation run on platform/abf_station/rules.py (FORBIDDEN unit). 40 mutants, 20 killed, 20 survivors, all killed by 15 proposed unit tests; no change to rules.py needed.
