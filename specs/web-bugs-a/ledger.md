# 網頁 bug 一批（#335 #336 #337 #339 #340） progress ledger

## 完成（executor）
- [x] #335 確認頁／404 英文版（web.py：_page 加 lang、view_of、state_page、no_address）
- [x] #336 任務分頁說明句（failed_unlisted／failed_partial）
- [x] #337 succeeded 的選單不給續跑／重跑／取消（quick 連結保留）
- [x] #339 送出／下游階段改灰字「之後開放」
- [x] #340 `*.nf` 無 `/` 的專案名視為無專案
- 新測試 `platform/tests/test_web_bugs_a.py`（18 條）。

## 被改的既有斷言（舊→新與理由）
- `test_clean_page.py` `test_the_expired_and_void_…`：en 迴圈原斷言中文標題與中文逾時句 → 改斷言英文標題／英文逾時句且無中文（#335）；zh 照舊。
- `BASE_CONFIRM` 只動 `-en` 鍵：pending-launch-en fc25714f1456fc99→d6ff72373725bc80；pending-cancel-en 0edb26e927e2795c→4313b8b2ad13e177；void-en 0db16b6921b8cff3→656964c19751b11d；confirmed-launch-en 6a6af64927587198→2c1c58dad9aa688c；confirmed-cancel-en e6b49c99a108279b→c569a78f17dd1e8b。`-zh` 鍵原值。
- `BASE_EXPIRED` 只動 `-en`：expired-launch-en 279bd8ce6698f89c→e33e97220f0e46f9；expired-cancel-en c1a5d02a55fefcfb→cd56f1e532231086。`-zh` 原值。
- `test_web_board.py` `test_tch21_stage_bodies`：launch／downstream 由含 `012b`／`016` → 含 `之後開放`且不含 012b／016；finished 不動。

## 備註
- 截圖（1440／390 × zh／en）：本環境未取得，留給 PR。`scripts/dev/ui_check.py` 不存在。
- failed_partial 說明句：「上表列出 N 個失敗任務，但失敗計數 M；其餘可能已被忽略或重試成功。」

- Plan gap: test_web_resume_edit tc024/tc049 needed a resume form on a succeeded run; they now take the form while failed, then flip to succeeded before posting (same assertions). test_web_bugs_a.py got its test_scope header.
- Plan gap: test_web_status_squares_3 ss02 forbids the word 成功 on a failed run page; the spec-mandated note (TC-030) contains 重試成功, so ss02 now strips that one note first.
- Pre-existing, not ours: test_mcp_launch_pipeline::test_no_schema_change diffs store.py against origin/v3 (store.py untouched here); test_azure_ce missing_credential passes alone, flaky in shard.
- Plan gap: test_web_settings_ce_mobile ce08 hash of web_board.STRINGS re-pinned (new strings failed_unlisted/failed_partial).
