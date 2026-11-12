# MCP publish_figure：私有圖庫、勾選打包 progress ledger

## 進度（執行者，stamp 20261112-1900-L-mcp-publish-figure-r2）
- [x] 切片 1 全部：`publish_figure` 走確認通道（ELICITED／PAGE／CHAT 共用 `_ask`），確認後才寫 `figures_root/<user>/<run_id>/`；新種類 `publish_figure`（`confirm.NO_JOB_KINDS`，不建 job）；遷移 `_migrate_confirmation_kinds`。
- 本輪補的：`platform/tests/test_publish_figure_confirm.py`（確認通道拒絕與遷移測試）；英文確認頁用 facts 重建英文畫面（`screen_for_page`，bundle 多 `replaces`）；`test_web_parity.py` 登記三個新公開名（只增不減，OWED 不變）。
- 既有測試被改動（皆同步新種類／新工具）：`test_cleanup_store.py`（kinds 迴圈與 declared_kinds 多 publish_figure）、`test_web_parity.py`（INTERNAL／WEB_ONLY 增名）、`test_chat_tools.py`（REQUESTS 還原為原六個，聊天不提供 publish_figure）、各 mcp 合約與 tools.json、aws/azure/gcb/k8s 等的工具清單釘住。
- L 級證明：(a) 範圍見 `git diff --stat`（platform/ 與 docs，沒碰 spec／憲法／.github／plugin.json／ROADMAP）；(b) confirm.py 只加 approve 的 writer 分支與 facts 欄位；(c) 遷移：舊表資料列前後相同、`PRAGMA foreign_key_check` 為空、jobs 的 CHECK 不變（test_confirmations_check_migration、test_migration_of_the_oldest_database…）；(d) `confirmations.kind` 的讀寫處由 test_cleanup_store／test_confirm_page 覆蓋；(e) 失敗時回滾（test_migration_failure_rolls_back）。
- 新常數：MAX_FIGURES_PER_CALL=10、MAX_PER_RUN=30、MAX_BUNDLE_BYTES=5 MiB、NO_JOB_KINDS。`index.json` 版本 1，欄位 size／type／caption／code_file／params_file／created／packed／packed_at／request_id。
- 人工項（TC-057／058／098，截圖）：執行者未跑，UNVERIFIED。
- 要問維護者：憲法清單是否列入 publish_figure；刪圖是否另需確認；base64 保留到 forget 為止是否可接受。
