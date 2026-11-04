# 假 Slurm 指令與 SU 測試夾具 progress ledger

## 狀態
- [x] `platform/tests/fake_slurm.py`、`test_fake_slurm_shim.py`（TC-001..011、021）、`test_su_job_states.py`（TC-012..020、025）完成。
- 新增的狀態表：`fake_slurm.STATES`（COMPLETED 0:0、FAILED 1:0、TIMEOUT 0:0、OUT_OF_MEMORY 0:125、NODE_FAIL 1:0、CANCELLED 0:15；`CANCELLED by 1234` 一例；`FAILED_NO_TRACE`）。欄位順序為假設，未經 nano4 實測。
- 已被測試釘住的既有行為：`su.py` 只看 task 的 cpus、realtime、queue，完全不看 status，也不呼叫 sacct。
- SU 費率未確認（UNCONFIRMED，1 SU = 1 core-hour 為推論）；費率只來自 `configs/sites/su_rates.json`。
- 假指令只證明我們自己的解析，不證明真 Slurm 行為（PITFALLS 第 42 條）。
- 狀態檔命名用 `rows_<id>`／`alive_<id>`／`fail_sacct`／`fail_sbatch`／`invalid_squeue`，不重用 head-nodefail 分支的 `state/sacct_<id>`。
- WSL 裡 `constitution_scope_test.sh` 紅＝環境問題，以 CI 為準。
