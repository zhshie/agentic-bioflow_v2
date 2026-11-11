# 連線保活、掉線紅色提示、擋新送出 progress ledger

## 完成項目
- [x] 開連線指令（on_site.sh、reset_master.sh）：`ControlPersist=yes -o ServerAliveInterval=60 -o ServerAliveCountMax=10`，說明文字不再承諾 8h。
- [x] `scripts/keepalive_log.sh` 與 `tests/keepalive_log_test.sh`（24 項）。
- [x] `platform/abf_platform/site_link.py`（closed_agents、down_message、bar_html、SITE_DOWN_AGENTS）；`web.user_of` 每個請求設值；`web_board._frame` 在 devbar 之後畫紅條；`jobs.enqueue_confirmed` 在 launch 的 yes 時擋。
- [x] mcp_server 四個送出工具的 description 加「站台連線掉線時會被擋。」（launch 的原文為此縮了幾個字，才不超過 600 字元上限）。
- [x] 文件：PLATFORM.md、SITE_ADAPTER.md、PITFALLS.md 第 61 條。
- [x] 既有測試改動（皆因本件必然的結果）：`STYLE_SHA256` 與各頁雜湊重釘（test_results_files、test_clean_page、test_web_guided_launch_preview、test_web_resume_edit、test_web_settings_register）；test_refusal_visibility.py:138 白名單加四個檔；test_launch_docs.py:32 由「8 hours」改為「keepalive_log.sh 且無 8 hours」；reset_master_test.sh:32。

- [x] 重跑（2026-11-11 21:30，stamp 20261111-2130-platform-mcp）：沿用既有 commit，補畫面證據與 keepalive 實演，再跑全套。

## 畫面證據（2026-11-11 21:36，WSL 內 Playwright Chromium＋axe，`scripts/dev/ui_check.py` 的拋棄式平台，假資料）
作法：`ui_check.start_platform` 起一個 /tmp 下的平台，使用者 alice，agent `agent-t` 自報 `site_link=closed`，截 `/`。
截圖放在 repo 之外：`C:/Users/marvi/abf-ui-evidence/mcp-site-keepalive-disconnect-ux/`（同資料夾的 `shoot.py` 是產生它們的一次性腳本，`summary.md` 是 axe 結果）。

| 檔名 | 語言／寬度 | 紅條上看到的字 |
|---|---|---|
| `board-1440-zh.png` | zh／1440 | ✗ 站台連線已掉：請在執行 agent「agent-t」那台機器的 WSL 終端機重新登入（貼上開連線指令並輸入 OTP）。已在跑的 run 不受影響；新的 run 在恢復前無法送出。 |
| `board-390-zh.png` | zh／390 | 同上（折成三行） |
| `board-1440-en.png` | en／1440 | ✗ The site connection is down. On the machine running agent "agent-t", log in again in its WSL terminal (paste the connect line, type the one-time code). Runs already going are not affected; new runs cannot be sent until it is back. |
| `board-390-en.png` | en／390 | 同上（折行） |
| `board-1440-zh-after-open.png`、`board-1440-en-after-open.png` | agent 回 open 之後 | 沒有紅條 |

- 四個組合量到的值都一樣：`.linkbar` 1 個；底色 `rgb(250, 230, 227)`（`--failed-bg` #fae6e3）；文字 `rgb(176, 38, 29)`（`--failed` #b0261d）；`position: static`（不浮動）；沒有水平捲動（`scrollWidth > clientWidth` 為 false）。紅條在頂列正下方、主版面之前，滿寬。
- **agent 回 open 後紅條消失**：四個組合都把 `site_link` 改成 `open` 再載入 `/`，`.linkbar` 數量為 0。
- axe：四個組合各有 1 個 critical `meta-refresh`（節點 `meta[http-equiv="refresh"]`）與 1 個 moderate；沒有任何一個指到 `.linkbar`。`meta-refresh` 是看板原有的自動重新整理標籤（base 9ae086b2 的 `web_board.py:956` 就有，本件 diff 沒碰；`docs/TESTING.md:1060` 寫明「note it, do not count it」；`docs/reports/cloud-burn-2026-11/UI2.md` 也記錄過同一項）。因此 `ui_check` 的總判定是 FAILED，原因與本件無關；是否算 TC-030 通過由審查者判定。
- impeccable 偵測器（TC-029）沒有跑：本環境找不到該工具，留給審查者實跑。

## keepalive_log.sh 實演（模擬：假的 `--check-master` 依序回 open、closed、open；`ABF_KEEPALIVE_ROUNDS=3 ABF_KEEPALIVE_INTERVAL=0`）
```
ts=2026-11-11T21:36:57+08:00 machine=DESKTOP-7J5L5BJ master=open rc=0
ts=2026-11-11T21:36:57+08:00 machine=DESKTOP-7J5L5BJ master=closed rc=1
ts=2026-11-11T21:36:57+08:00 machine=DESKTOP-7J5L5BJ event=closed lasted_min=0 last_open=2026-11-11T21:36:57+08:00
ts=2026-11-11T21:36:57+08:00 machine=DESKTOP-7J5L5BJ master=open rc=0
ts=2026-11-11T21:36:57+08:00 machine=DESKTOP-7J5L5BJ event=reopened
```

## git diff --stat（9ae086b2..d5dd2533，不含 specs/）
```
 docs/PITFALLS.md                                   |   8 +
 docs/PLATFORM.md                                   |   6 +-
 docs/SITE_ADAPTER.md                               |   2 +-
 platform/abf_platform/jobs.py                      |   6 +
 platform/abf_platform/mcp_server.py                |  14 +-
 platform/abf_platform/site_link.py                 |  35 ++
 platform/abf_platform/web.py                       |   4 +-
 platform/abf_platform/web_board.py                 |   6 +-
 platform/tests/test_clean_page.py                  |  12 +-
 platform/tests/test_launch_docs.py                 |   2 +-
 platform/tests/test_refusal_visibility.py          |   4 +-
 platform/tests/test_results_files.py               |   2 +-
 platform/tests/test_site_disconnect_ux.py          | 392 +++++++++++++++++++++
 platform/tests/test_web_guided_launch_preview.py   |   2 +-
 platform/tests/test_web_resume_edit.py             |   2 +-
 platform/tests/test_web_settings_register.py       |   2 +-
 scripts/keepalive_log.sh                           |  53 +++
 scripts/on_site.sh                                 |  17 +-
 scripts/reset_master.sh                            |  10 +-
 tests/keepalive_log_test.sh                        |  83 +++++
 tests/reset_master_test.sh                         |   2 +-
```
沒有 `platform/abf_station/`、`.github/`、`hooks/`、`.specify/`、`.claude-plugin/` 的改動；沒有 `CREATE TABLE`／`ALTER TABLE`。

## 備註
- 計畫「允許更新」只點名 `STYLE_SHA256`；另外四個檔（test_clean_page、test_web_guided_launch_preview、test_web_resume_edit、test_web_settings_register）釘的是整頁位元組雜湊，`STYLE` 多一條規則後必然改變，所以一併重釘。`test_launch_docs.py:32` 計畫點名的是 79 行，實際釘住「8 hours」的是 32 行，只改那一句。這兩點請審查者確認。
- 全套結果見最後一次 executor 報告與 `executor-status`。
