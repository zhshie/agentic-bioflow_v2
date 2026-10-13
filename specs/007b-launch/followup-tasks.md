# 007b follow-up 1: progress (executor)

Plan: `followup-plan.md`. Test cases: `followup-test-case.md`. Branch `fix/007b-followups`.

## F2 reproduction on the unchanged code (before any code change), 2026-10-13

Setup (TC-F2-01, through the real platform, real agent and fake site; `platform/tests/test_launch_followup_e2e.py`):
the folder `runs/run-reuse` already exists on the fake site, so the agent refuses the first launch ("專屬資料夾…已存在",
sbatch zero times, the folder untouched). The refused launch is row id 1 (no Slurm number, its job `refused`). The folder is
removed, the fake site answers Slurm 2231948, and the same name is launched again, answered `y`.

Result on main code: the second launch succeeds (exit 0, "已送出：Slurm 工作編號 2231948"), but `launches` holds ONE row
for `run-reuse` (id 2, 2231948): the refused row id 1 is gone, because `jobs.enqueue_confirmed` runs
`DELETE FROM launches WHERE id = ?` before the INSERT. The total of `launches` rows did not go up by one. So the maintainer's
case "works" but destroys a fact (FR-009); that DELETE is the bug, as the plan says.
F1 was reproduced in the same run: `abf-platform launches` printed "未送出：代理沒有回報 Slurm 工作編號（結果不明…" for the refused row.

## Items

- [x] F1 `launches` reads the launch's own job (`launches.job_id`) and prints 被代理拒絕 / 等代理處理中 / the old line (+ the agent's message and left_on_site on `error`). `abf_launch/cli.py` `_not_submitted_lines`, `jobs.launch_job`. Tests: TC-F1-01..08 in `platform/tests/test_launch_followup.py`.
- [x] F2 `launches` gets `job_id` and loses UNIQUE(run_name) (`store._migrate_launches`: one transaction, copies ids and the AUTOINCREMENT counter, backfills job_id by created_at == confirmed_at, else the newest unclaimed job of the name); `jobs.name_problem` (strictest row decides) is used by `enqueue_confirmed` (inside the transaction, so two at once let one through) and by `jobs.check_run_name` before the question in `abf-platform launch`; the DELETE is gone; results, cancel, fetch and the closing report find their own / the newest row. Tests: TC-F2-01..13 (`test_launch_followup.py`, `test_launch_followup_e2e.py`).
  Two existing assertions had to change because they said the opposite of F2 (the plan's own change): `test_tc055_launches_holds_the_facts...` (column list gains job_id; run_name no longer UNIQUE, two rows of one name now insert) and `test_a_launch_that_failed...` (two rows of the reused name, not one).
- [x] F3 the platform tests are two `run_all` entries: `tests/platform_test.sh` (the parallel shards, the default `ABF_PLATFORM_PART=main`) and the new `tests/platform_clock_test.sh` (`ABF_PLATFORM_PART=clock`: `test_station_e2e.py` then `test_nextflow_e2e.py`, alone, one after the other; it only sets the part and runs `platform_test.sh`, so the Java / download / CI-skip rules are the same code). `ABF_PLATFORM_PART=all` is the old single run; `ABF_PLATFORM_LIST=1` lists a part's files (used by `platform/tests/test_platform_parts.py`: union = every `test_*.py`, each once). `PER_TEST_TIMEOUT` is untouched (300), `.github/` untouched. In WSL (16 cores) before: one entry 247 s; after: `platform_clock_test.sh` 133 s, `platform_test.sh` 113 s. CI is the only proof (TC-F3-01): the PR text should paste those two lines from the CI log.
