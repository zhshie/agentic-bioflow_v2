2026-11-05
# MCP 聊天內核准（CHAT 通道）＋憲法 7.0.0 progress ledger

本任務依明文例外修改憲法（plan 列出的 I.2、Safety Net、Check 行與 7.0.0 條目；舊條目不動）。Approval 欄為 PENDING，待維護者親口同意。

## 開工前檢查
- merge-base 等於 origin/v3；日期 2026-11-05。
- `git grep "could say yes\|cannot say it for them\|FIXED_SENTENCE"` 命中（本分支 HEAD）：docs/PLATFORM.md:436；platform/abf_platform/guidance.py:16,18,104；platform/abf_platform/mcp_server.py:16,221,244,255；platform/tests/test_keep_submissions.py:851；platform/tests/test_resume_edit_params_words.py:38；其餘為 specs/ 舊文件（不改）。
- PITFALLS 再 grep（`confirm|channel|constitution` @ HEAD docs/PITFALLS.md）：36 筆，全是 shell hooks（confirm_cleanup／confirm_walkthrough／confirm_launch）、jq 缺失、舊 constitution 對帳；與 MCP 確認／CHAT 通道無關，無相符項，與 plan 一致。

## 進度
- [ ] RED：platform/tests/test_chat_confirm.py
- [ ] GREEN：confirm.py、actions/__init__.py、mcp_server.py、guidance.py、chat_tools.py、elicit.py 註解
- [ ] 既有測試更新（規則 A～D）與 snapshot
- [ ] 憲法 7.0.0、三支 shell 測試、docs、skills、CHANGELOG
- [ ] 全套測試
