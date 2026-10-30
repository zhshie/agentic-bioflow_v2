# uploads-sweep-tests progress ledger

- [x] 新增 `platform/tests/test_uploads_sweep.py`（7 條測試，涵蓋 TC-001..TC-012），在 v3 上全綠（7 passed）。
- 因 sweep 本身沒壞，沒有程式可「先紅」；紅用突變證明（一次性，已還原）：
  - M1 `startswith(".incoming-")` -> `if True:`：1 failed（test_tc004_to_tc007_other_things_are_never_touched），6 passed。
  - M2 `>` -> `>=`：1 failed（test_tc002_exactly_24h_is_kept），6 passed。
  - M3 判斷整行 -> `if True:`：2 failed（test_tc002_exactly_24h_is_kept、test_tc003_new_folder_is_kept），5 passed。（TC-003 依計畫變紅；TC-002 也紅，因為一律清連 86400 秒的也清。）
  - 還原後：7 passed；`git status` 只有新測試檔，`uploads_web.py` 無改動。
- 特徵化（TC-010/011）：先在 v3 實測，子資料夾使 discard 清不乾淨：夾子留著、其中 .part 已刪，不丟例外。測試註解已寫明是特徵化、非期望行為。
- 裁決 1 記錄：sweep 用資料夾修改時間判斷「舊」；寫入既有檔案不會更新資料夾時間，所以連續超過 24 小時的上傳理論上可能被別的請求清掉。2 GB 上限下實際不會發生；決定不處理，真要處理屬行為變更，另案請維護者裁決。
- `git diff --stat`（程式與測試部分）：只有 `platform/tests/test_uploads_sweep.py`（新增）。
