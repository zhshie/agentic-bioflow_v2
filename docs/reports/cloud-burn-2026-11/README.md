# Cloud-burn reports, 2026-11

- AR11 - Adversarial review of compose, catalogue, module sources, pipeline actions and pipeline launch (`platform/abf_platform/`): 10 surviving findings, led by a P1 where a map-only channel is rendered as `[[id: ...]]`.
- AR12 - Adversarial review of `platform/abf_launch/`: 19 surviving findings, two P1 (samplesheet cells escape the path gates; a resume after a relaunch gets a name the agent cannot match).
- AR13 - Adversarial review of `hooks/`: 24 surviving findings, four P1 Safety Net bypasses (glob in a middle path component, here-doc run by `source`/`eval`, MCP launch with a top-level `input`, identity-change gate spellings).
