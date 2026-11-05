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

## 修正輪（verifier 退回）
- TC-083：以 ABF_UPDATE_MCP_SNAPSHOT=1 重產 platform/tests/mcp/snapshots/tools.json（加入 request_id、user_confirmed）。
- 描述長度：cancel 610→低於 600；resume、relaunch 改寫為不超過 600（內含 request_id 與 user_confirmed 一句）。tests/mcp 全過（72 passed）。
- TC-026：test_tcm_26 改為 599 秒必須核可並排出 job（offline_after 放寬以免假時鐘造成離線）。
- 注意：tests/platform_test.sh 只列舉 tests/test_*.py，platform/tests/mcp/ 不在全套分片內；已另跑 tests/mcp。

## 修正輪二
- TC-047、TC-054、TC-075：test_chat_confirm.py 改為與 base（ea704065）逐項比對，38 passed。pending 回覆的 summary 欄與表單／頁面同一份畫面，含使用者自己的 samplesheet 路徑（base 行為），路徑檢查排除該欄，token／密碼檢查含全部。
- TC-071：7.0.0 條目需補一條 What changes bullet，寫明 5.0.0 那句 A pending request, a token, and anything the model can answer are not a channel 對 CHAT 不再適用（CHAT 只是人本人的回覆經 request id 轉述；單獨的待確認與 token 仍不是通道；5.0.0 條目不動）。憲法檔的編輯被拒，未寫入，卡住。
