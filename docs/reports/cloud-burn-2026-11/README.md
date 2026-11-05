# Cloud-burn reports, 2026-11

- AR11 - Adversarial review of compose, catalogue, module sources, pipeline actions and pipeline launch (`platform/abf_platform/`): 10 surviving findings, led by a P1 where a map-only channel is rendered as `[[id: ...]]`.
- AR12 - Adversarial review of `platform/abf_launch/`: 19 surviving findings, two P1 (samplesheet cells escape the path gates; a resume after a relaunch gets a name the agent cannot match).
- AR13 - Adversarial review of `hooks/`: 24 surviving findings, four P1 Safety Net bypasses (glob in a middle path component, here-doc run by `source`/`eval`, MCP launch with a top-level `input`, identity-change gate spellings).
- MU04: Mutation run on platform/abf_platform/cloud_cost.py. 54 mutants, 30 killed, 20 real survivors (mostly the monthly cap check and odd-number pricing), all killed by a proposed new test file.
- MU05: Mutation run on platform/abf_platform/http_auth.py. 59 mutants, 28 real survivors (session table, ContextVar reset, discovery document), all covered by a proposed new test file.
- MU06: Mutation run on platform/abf_station/rules.py (FORBIDDEN unit). 40 mutants, 20 killed, 20 survivors, all killed by 15 proposed unit tests; no change to rules.py needed.
