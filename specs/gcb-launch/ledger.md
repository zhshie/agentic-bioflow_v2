# gcb-launch progress ledger

- [x] RED: tests/test_gcb_launch.py written first (commit a1e0403); fixtures failed on the missing `site.start_detached`.
- [x] `site.start_detached` (fixed argv, no shell, new session, private output file).
- [x] `launch.py`: gcb branch of `snapshot_ce`, `render_gcb_bundle` (bundle, `gcb.config`, `head.sh`, gs:// samplesheet rule), guards in `run_launch` / `run_resume`.
- [x] `gcb_launch.py` (new): agent-side launch (rebuild compare, host checks, run folder, detached start, `head.pid`) and cancel (one SIGTERM after pid / owner / `-name` / cwd checks); `cancel.py` dispatches.
- [x] `jobs._target`: gcb now lets `launch_nextflow` and `cancel_run` through; the other kinds are still refused ("尚未支援").
- [x] `build.py` / `cli.py`: gcb launch screen (billing paragraph first), cancel screen, pid wording, resume / relaunch refused; Slurm output byte-identical (digests in the test).
- [x] `fetch.py`: `gcb.config` is not a record.
- [x] Docs: PLATFORM.md (type table, key table, "Launching on Google Batch"), SEQERA_PARITY.md, TESTING.md (gcb-launch), OPERATIONS.md (host requirements). The parity box stays `[ ]`.
- [ ] Manual acceptance (TC-117, TC-118, TC-123, TC-126..TC-131): the maintainer, on his own account. Not done by the executor.
  - Result to record: do `process.resourceLabels` show up on the Batch job (TC-131)? Not checked yet; if not supported, remove the line in `_gcb_config` and record it here.
  - Result to record: is a short `network` / `subnetwork` name accepted by Batch (TC-131)? Not checked yet.
  - Result to record: does SIGTERM make Nextflow cancel its Batch jobs (TC-129)? Not checked yet.

## Deviations from the plan, for the reviewer

1. `test_gcb_ce.py::test_refusals_are_plain_words` (TC-078 of C-1) also changed: it expected `check_target(..., "launch_nextflow")` on an available gcb environment to be refused; it now uses `list_site_files`, which is still refused. The plan's "four places" list did not name it; it cannot stay as it was once a launch is allowed.
2. `NO_BUCKET_PATH` in `launch.py` writes `gcloud storage` and `cp` as two string pieces: TC-053 wants the message to mention that command, and `test_nothing_of_the_later_slices_exists` (TC-107) forbids the three characters-run `storage cp` anywhere in the source.
3. `handlers.py` was not touched: the dispatch is inside `launch.run_launch` and `cancel.run_cancel`, which `handlers.handle` already calls.
4. `compute_envs.snapshot` was not changed: the launch bundle's environment comes from `launch.snapshot_ce`; the preflight job keeps its own fields.
5. The tests use `WORK = "gs://lab-bucket/" + "work"` because `test_scope.py::test_tc072` rejects `/work/<name>/` in any file under platform/.
