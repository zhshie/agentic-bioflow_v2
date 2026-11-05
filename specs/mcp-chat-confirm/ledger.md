2026-11-05
# MCP 聊天內核准（CHAT 通道）＋憲法 7.0.0 progress ledger

本任務依明文例外修改憲法（plan 列出的 I.2、Safety Net、Check 行與 7.0.0 條目；舊條目不動）。Approval 欄為 PENDING，待維護者親口同意。

## 開工前檢查
- merge-base 等於 origin/v3；日期 2026-11-05。
- `git grep "could say yes\|cannot say it for them\|FIXED_SENTENCE"` 命中（本分支 HEAD）：docs/PLATFORM.md:436；platform/abf_platform/guidance.py:16,18,104；platform/abf_platform/mcp_server.py:16,221,244,255；platform/tests/test_keep_submissions.py:851；platform/tests/test_resume_edit_params_words.py:38；其餘為 specs/ 舊文件（不改）。
- PITFALLS 再 grep（`confirm|channel|constitution` @ HEAD docs/PITFALLS.md）：36 筆，全是 shell hooks（confirm_cleanup／confirm_walkthrough／confirm_launch）、jq 缺失、舊 constitution 對帳；與 MCP 確認／CHAT 通道無關，無相符項，與 plan 一致。

## 進度
- [x] RED：platform/tests/test_chat_confirm.py
- [x] GREEN：confirm.py、actions/__init__.py、mcp_server.py、guidance.py、chat_tools.py、elicit.py 註解
- [x] 既有測試更新（規則 A～D）與 snapshot
- [x] 憲法 7.0.0、三支 shell 測試、docs、skills、CHANGELOG
- [x] 全套測試

## 第二次合併 origin/v3 (075b6177) 後
- 合併乾淨無衝突，HEAD 1630efc8。全套 146/150，1 FAIL (platform_upgrade_test TC-U28)，3 逾時 (shard_2/4/6, 300s)。
- TC-U28 以 merge-base 比對 platform/ 是否未動；合併後 merge-base=origin/v3，任何改 platform/ 的分支必紅。計畫未授權改該測試，故卡住。

## 第三次：合併 origin/v3 (b3ec5b32，TC-U28 已刪) 後
- 合併乾淨，HEAD 8ca9459a。修 test_tcm_50（launch 描述不含 confirm 字樣，TC-017 釘住）。鏡像的 origin/v3 過舊，已手動 fetch 更新（環境，非程式碼）。
- 全套 150/150 全綠，在 81983198 跑的（之後只改本 ledger）。
