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

## BLOCKED (executor) - 已由裁決 N 解除：test_catalogue.py:419 正規式改為 tier A|tier C|A-tier|A 級|A級（只此一處）；746 行 Tier A 未動，請 developer-agent 判斷
全套在 d5798a0 之後：136/138，兩個紅：
1. no_pipefail_grep_q_test.sh：已修（我的 tests/pitfalls_format_test.sh 用了 pipefail + `| grep -q`，改成 here-string），單檔綠。
2. platform_shard_5 -> platform/tests/test_catalogue.py::test_platform_doc_has_the_catalogue_section（第 419 行）：
   `assert "PR" in sec and re.search(r"tier A|A-tier|A 級|A級", sec)`，其中 sec 是 PLATFORM.md「## nf-core module catalogue」到「## What the platform stores」之間。
   846 行是該節裡唯一的 "tier A"，依計畫改成 tier C 後此斷言必紅。計畫「被釘住的既有檢查」漏列這支測試，且未授權改它（只准改三個檔）。
   不能改測試也不能回退 PLATFORM.md（TC-014 要求 tier C）。需要 developer-agent 裁決：(a) 授權把 test_catalogue.py:419 的正規式改成 tier C（或 tier A|tier C），或 (b) 本任務不改 846 行。
其餘工作（94 組欄位、檔首說明、TC-001..013）已完成並提交。
