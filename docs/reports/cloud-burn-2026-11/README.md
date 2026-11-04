# cloud-burn 2026-11 reports

- UI2: ui_check.py with axe-core, 6 pages x 1440/390 x zh/en. Eight critical axe meta-refresh hits on board and results, plus wording, launch-with-no-compute-environment and 390 px layout issues (11 findings).
- UI3: design report for settings-ce-table-mobile. The 390 px card layout already landed, but the viewport-keyed switch still cuts words mid-letter from about 901 to 1313 px; proposes a container query (4 findings).
- R4: real-process QA walk with verify-abf against a fake station. Most surfaces pass; findings include the Slurm computeQueue not reaching Nextflow, an all-green preflight that still refuses launch, and a set of CLI/MCP wording and validation gaps (16 findings).
