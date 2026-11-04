# Cloud-burn 2026-11 reports

- MU01 - Mutation run: platform/abf_platform/common.py - 38 hand-made mutants, 13 killed, 25 survived (24 real, 1 equivalent); parse_iso_epoch, extract_error, run_failure_reason and token parsing are barely pinned by tests.
- MU02 - Mutation run: platform/abf_platform/validate.py - 48 hand-made mutants, 42 killed, 6 survived (5 real, 1 equivalent); gaps are mostly in extension-pattern comparison (multi-dot, case, hyphen).
- MU03 - Mutation run: platform/abf_platform/compute_envs.py - 101 hand-made mutants, 54 killed, 47 survived (44 real, 3 equivalent); Slurm limits, cloud workDir shapes and storage bookkeeping are unasserted.
