# PITFALLS 條目補四行格式＋PLATFORM.md 846 tier 字樣 progress ledger

## 進度 (executor)
- [x] tests/pitfalls_format_test.sh 先寫、先紅（commit e76efadd "RED: ..."），文件補完後全綠（TC-001..006、010、013、014）。
- [x] docs/PITFALLS.md：檔首 `## How an entry is written` 加 94 組四行（欄位草稿在 fields/，b01..b05）。`grep -nE '^(Symptom|Root cause|Check|Touches):'` 在 v3 原檔 0 筆，無衝突。
- [x] `git diff --numstat origin/v3 -- docs/PITFALLS.md`：492 新增、0 刪除（94x4=376 + 檔首說明）。行尾未動（檔內本來無 CR）。
- [x] docs/PLATFORM.md 846 行：`one tier A PR` -> `one tier C PR`，diff 僅該一行。constitution 6.2.0 只寫 "The development lead merges every pull request after CI is green..."（沒有 A/B/C 字母），無法用它確認 C=自行合併，依維護者原話（backlog 項 4）執行。
- 疑問給 developer-agent：docs/PLATFORM.md 746 行仍為 "*(Tier A: OAuth only adds another way ...)*"，是否也要隨 A／C 對調改，請判斷（本任務未動）。
- tests/run_all.sh 未改；其開頭註解寫 files are every *.sh in this directory, 故 pitfalls_format_test.sh 自動被撿到。
- WSL 裡 constitution_scope_test.sh 若紅＝Windows 建 worktree 的環境問題，以 CI 為準（裁決 4）。
- fields/b05_rest.txt 與 b05.txt 是同一批第 30-58 條的欄位草稿（重複，無法刪除），不影響結果。
