# 連線保活、掉線紅色提示、擋新送出 progress ledger

## 完成項目
- [x] 開連線指令（on_site.sh、reset_master.sh）：`ControlPersist=yes -o ServerAliveInterval=60 -o ServerAliveCountMax=10`，說明文字不再承諾 8h。
- [x] `scripts/keepalive_log.sh` 與 `tests/keepalive_log_test.sh`（24 項）。
- [x] `platform/abf_platform/site_link.py`（closed_agents、down_message、bar_html、SITE_DOWN_AGENTS）；`web.user_of` 每個請求設值；`web_board._frame` 在 devbar 之後畫紅條；`jobs.enqueue_confirmed` 在 launch 的 yes 時擋。
- [x] mcp_server 四個送出工具的 description 加「站台連線掉線時會被擋。」（launch 的原文為此縮了幾個字，才不超過 600 字元上限）。
- [x] 文件：PLATFORM.md、SITE_ADAPTER.md、PITFALLS.md 第 61 條。
- [x] 既有測試改動（皆因本件必然的結果）：`STYLE_SHA256` 與各頁雜湊重釘（test_results_files、test_clean_page、test_web_guided_launch_preview、test_web_resume_edit、test_web_settings_register）；test_refusal_visibility.py:138 白名單加四個檔；test_launch_docs.py:32 由「8 hours」改為「keepalive_log.sh 且無 8 hours」；reset_master_test.sh:32。

## 備註
- 紅條畫面截圖：本環境無瀏覽器，未附；以 HTML 結構與 STYLE 規則的測試代替（test_site_disconnect_ux.py）。
- 模擬的 keepalive log 形狀：`ts=2026-11-11T10:00:00+08:00 machine=host master=open rc=0`；掉線時多一行 `event=closed lasted_min=N last_open=ISO`。
- 若全套有失敗，見最後一次 executor 報告。
