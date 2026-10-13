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

- [ ] F1 launches shows refused / waiting
- [ ] F2 name reuse keeps the row (table migration, name check before the question)
- [ ] F3 platform_test.sh headroom
