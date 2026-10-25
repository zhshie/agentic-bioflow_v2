# 網頁上傳檔案到雲端（a：平台端工作種類） progress ledger

- [x] 完成：`put_upload` 新工作種類。store CHECK 加第八種、遷移「已是最新」判斷同時看 `read_task_log`／`clean_work`／`put_upload`；jobs 種類表、`_target`（Google Batch 放行、非 Google Batch 拒、須 `available`）、`_enqueue` 拒絕 put_upload、新入口 `enqueue_put_upload`、`clean_result` 分支；`cloud_store.UPLOAD_LIMIT`。
- [x] 新測試 `platform/tests/test_byte_channel_a.py`（50 條，涵蓋 TC-001～094 的自動案例）；六個既有測試檔只在種類清單末尾補 `put_upload`。

- [x] 計畫漏列的第 11 個檔：`platform/tests/test_http_site_samplesheet.py` 的 `SCHEMA_SHA256`（整份資料庫結構的雜湊，TC-057）。jobs CHECK 清單多一項必然改變雜湊；只換這一個常數（舊值 `0b6aad18e811…`、新值 `bb8b185e8eef…`），與 cloud-cleanup-b 加 clean_work 時同做法（commit 35b7888）。請 verifier 在 TC-097／098 把它視為必要的連帶更新。

## 手動案例的證據（base = 2c1d13c）

`git diff --name-only 2c1d13c`（TC-087/088/092/095/097）：

```
platform/abf_platform/cloud_store.py
platform/abf_platform/jobs.py
platform/abf_platform/store.py
platform/tests/test_byte_channel_a.py
platform/tests/test_cleanup_confirm.py
platform/tests/test_cleanup_store.py
platform/tests/test_cloud_cost.py
platform/tests/test_launch_platform.py
platform/tests/test_resume_scope.py
platform/tests/test_station_platform.py
specs/byte-channel-a/*（計畫、測試案例、本檔）
```

`git diff --stat 2c1d13c -- platform`：cloud_store.py +3；jobs.py +82；store.py +10；test_byte_channel_a.py +510（新）；其餘六個測試檔各 1～2 行（種類清單末尾補 put_upload）。

- TC-083：jobs.py 新增（`+`）行含小寫 `station` 的行數＝0。
- TC-086：jobs.py／store.py／cloud_store.py 中 `private_key` 出現次數＝0。
- TC-096：`pyproject.toml`、`constraints.txt` 無差異。

## 修正回合（verifier 退回 TC-059、TC-076）
- TC-059：`test_tc059_*` 改為收齊 TC-037～057 的每一種拒絕（使用者編號三種、他人的名字／環境／不存在的環境、四種環境狀態、離線代理、八種壞檔名、檔案不存在／資料夾／符號連結／realpath 跑出資料夾／空檔案／超過上限、Slurm 環境，共 24 則以上），逐則斷言：有內容、有白話（中文或括號英文說明）、不含上傳資料夾路徑、SQL、堆疊追蹤。
- TC-076：`test_tc076_tc077_*` 補一段：Slurm 環境、狀態 unavailable，對 `launch_nextflow` 做 `check_target`，斷言拒絕訊息含 "run an analysis"。已手動把 jobs.py 的該字改掉確認此測試會紅，之後還原。
- 只改測試檔，程式碼未動。
