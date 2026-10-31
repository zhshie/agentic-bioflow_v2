# ledger: slurm-url-cells
- [x] RED: platform/tests/test_slurm_url_cells.py (tests 1-7 of the plan)
- [x] GREEN: launch.py is_web_cell + _check_samplesheet branch (Slurm only; credential check kept); build.py _confine skips web cells. The agent does not re-judge cells at job time (it checks the bundle hash and the upload_paths record only), so nothing else needed.
- [x] docs/PLATFORM.md line 731: one sentence.
- [ ] full suite (see below)
