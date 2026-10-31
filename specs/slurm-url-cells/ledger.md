# ledger: slurm-url-cells
- [x] RED: platform/tests/test_slurm_url_cells.py (tests 1-7 of the plan)
- [x] GREEN: launch.py is_web_cell + _check_samplesheet branch (Slurm only; credential check kept); build.py _confine skips web cells. The agent does not re-judge cells at job time (it checks the bundle hash and the upload_paths record only), so nothing else needed.
- [x] docs/PLATFORM.md line 731: one sentence.
- [ ] full suite (see below)

## Full suite (WSL, run_all.sh --timeout 900, at the GREEN commit): 130/136, 6 red, all environment
The worktree was created by Windows git; inside WSL `git` answers "not a git repository", so these fail for that reason only:
constitution_scope_test.sh, jev_test.sh (not examined), platform_direction_docs_test.sh (scratch clone), and the four pytest
shards' git-dependent tests: test_launch_static::test_tc074, test_scope::test_tc071, test_station_static::test_tc087, test_su_packaged::test_gitignore_and_tracking.
No failure touches Slurm launch or samplesheet code. CI decides.
