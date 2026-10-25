# 網頁上傳檔案到雲端（a：平台端工作種類） progress ledger

- [x] 完成：`put_upload` 新工作種類。store CHECK 加第八種、遷移「已是最新」判斷同時看 `read_task_log`／`clean_work`／`put_upload`；jobs 種類表、`_target`（Google Batch 放行、非 Google Batch 拒、須 `available`）、`_enqueue` 拒絕 put_upload、新入口 `enqueue_put_upload`、`clean_result` 分支；`cloud_store.UPLOAD_LIMIT`。
- [x] 新測試 `platform/tests/test_byte_channel_a.py`（50 條，涵蓋 TC-001～094 的自動案例）；六個既有測試檔只在種類清單末尾補 `put_upload`。

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
