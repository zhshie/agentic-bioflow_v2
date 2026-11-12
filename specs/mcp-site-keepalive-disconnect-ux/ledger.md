# 連線保活、掉線紅色提示、擋新送出 progress ledger

## 完成項目
- [x] 開連線指令（on_site.sh、reset_master.sh）：`ControlPersist=yes -o ServerAliveInterval=60 -o ServerAliveCountMax=10`，說明文字不再承諾 8h。
- [x] `scripts/keepalive_log.sh` 與 `tests/keepalive_log_test.sh`（24 項）。
- [x] `platform/abf_platform/site_link.py`（closed_agents、down_message、bar_html、SITE_DOWN_AGENTS）；`web.user_of` 每個請求設值；`web_board._frame` 在 devbar 之後畫紅條；`jobs.enqueue_confirmed` 在 launch 的 yes 時擋。
- [x] mcp_server 四個送出工具的 description 加「站台連線掉線時會被擋。」（launch 的原文為此縮了幾個字，才不超過 600 字元上限）。
- [x] 文件：PLATFORM.md、SITE_ADAPTER.md、PITFALLS.md 第 61 條。
- [x] 既有測試改動（皆因本件必然的結果）：`STYLE_SHA256` 與各頁雜湊重釘（test_results_files、test_clean_page、test_web_guided_launch_preview、test_web_resume_edit、test_web_settings_register）；test_refusal_visibility.py:138 白名單加四個檔；test_launch_docs.py:32 由「8 hours」改為「keepalive_log.sh 且無 8 hours」；reset_master_test.sh:32。

- [x] 重跑（2026-11-11 21:30，stamp 20261111-2130-platform-mcp）：沿用既有 commit，補畫面證據與 keepalive 實演，再跑全套。

## 畫面證據（2026-11-12 11:06 重拍，zh 文字已改成「分析」；首次 2026-11-11 21:36，WSL 內 Playwright Chromium＋axe，`scripts/dev/ui_check.py` 的拋棄式平台，假資料）
作法：`ui_check.start_platform` 起一個 /tmp 下的平台，使用者 alice，agent `agent-t` 自報 `site_link=closed`，截 `/`。
截圖放在 repo 之外：`C:/Users/marvi/abf-ui-evidence/mcp-site-keepalive-disconnect-ux/`（同資料夾的 `shoot.py` 是產生它們的一次性腳本，`summary.md` 是 axe 結果）。

| 檔名 | 語言／寬度 | 紅條上看到的字 |
|---|---|---|
| `board-1440-zh.png` | zh／1440 | ✗ 站台連線已掉：請在執行 agent「agent-t」那台機器的 WSL 終端機重新登入（貼上開連線指令並輸入 OTP）。已在跑的分析不受影響；新的分析在恢復前無法送出。 |
| `board-390-zh.png` | zh／390 | 同上（折成三行） |
| `board-1440-en.png` | en／1440 | ✗ The site connection is down. On the machine running agent "agent-t", log in again in its WSL terminal (paste the connect line, type the one-time code). Runs already going are not affected; new runs cannot be sent until it is back. |
| `board-390-en.png` | en／390 | 同上（折行） |
| `board-1440-zh-after-open.png`、`board-1440-en-after-open.png` | agent 回 open 之後 | 沒有紅條 |

- 四個組合量到的值都一樣：`.linkbar` 1 個；底色 `rgb(250, 230, 227)`（`--failed-bg` #fae6e3）；文字 `rgb(176, 38, 29)`（`--failed` #b0261d）；`position: static`（不浮動）；沒有水平捲動（`scrollWidth > clientWidth` 為 false）。紅條在頂列正下方、主版面之前，滿寬。
- **agent 回 open 後紅條消失**：四個組合都把 `site_link` 改成 `open` 再載入 `/`，`.linkbar` 數量為 0。
- axe：四個組合各有 1 個 critical `meta-refresh`（節點 `meta[http-equiv="refresh"]`）與 1 個 moderate；沒有任何一個指到 `.linkbar`。`meta-refresh` 是看板原有的自動重新整理標籤（base 9ae086b2 的 `web_board.py:956` 就有，本件 diff 沒碰；`docs/TESTING.md:1060` 寫明「note it, do not count it」；`docs/reports/cloud-burn-2026-11/UI2.md` 也記錄過同一項）。因此 `ui_check` 的總判定是 FAILED，原因與本件無關；是否算 TC-030 通過由審查者判定。
- impeccable 偵測器（TC-029）沒有跑：本環境找不到該工具，留給審查者實跑。

## keepalive_log.sh 實演（模擬：假的 `--check-master` 依序回 open、closed、open；腳本連續呼叫三次，每次自行結束，2026-11-12 11:06）
```
call 1 exit=0
call 2 exit=0
call 3 exit=0
ts=2026-11-12T11:06:34+08:00 machine=DESKTOP-7J5L5BJ master=open rc=0
ts=2026-11-12T11:06:34+08:00 machine=DESKTOP-7J5L5BJ master=closed rc=1
ts=2026-11-12T11:06:34+08:00 machine=DESKTOP-7J5L5BJ event=closed lasted_min=0 last_open=2026-11-12T11:06:34+08:00
ts=2026-11-12T11:06:34+08:00 machine=DESKTOP-7J5L5BJ master=open rc=0
ts=2026-11-12T11:06:34+08:00 machine=DESKTOP-7J5L5BJ event=reopened
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

## 全套結果與卡住的兩點（2026-11-11 重跑）
全套第一次真的跑完是在 dcf3a8e8（前一輪寫的「綠」只跑過相關檔）。失敗的檔：`no_second_run_state_test.sh`、`platform_test.sh`、`platform_shard_2／3／5／6／7／8`。逐項：

已修（在 dcf3a8e8 之後的 commit）：
- [x] `pitfalls_format_test.sh`：條數釘 96→97；第 61 條內文補 `linkbar`、`jobs.enqueue_confirmed`（Touches 的字要出現在內文）。
- [x] launch 的 description：前一輪為了 600 字元上限改掉了三處被別的測試釘住的字（`after they answer`、`Or name a dataset of yours…`）。現在還原這兩處，改成只動兩處沒被釘的字（`After that call`→`Then call`、`a CSV you uploaded`→`an uploaded CSV`），長度剛好 600。`test_launch_profiles`（tc058）、`test_chat_confirm`（tcm_50）、`test_dataset_launch` 已綠。
- [x] 因新增 `.linkbar` 規則與 `linkbar_down` 字串而必然改變的釘值：`test_clean_page.py` 的 `BASE_STYLE`（前一輪打錯一碼，…841→…840，與 `STYLE_SHA256` 前 16 碼一致）；`test_web_nano4_path.py:249` 上傳頁 zh／en 雜湊、`:545` `len(STYLE)` 11742→11872；`test_web_settings_ce_mobile.py` 的 `web_board.STRINGS` 雜湊。
- `test_aws_ce`／`test_azure_ce::test_a_missing_credential_file_says_where_to_put_it` 只在重試那一輪失敗（重試資料夾路徑較長，訊息被截），第一輪是綠的；與本件無關。

**卡住，需要裁決（沒動）：**
1. **不變量 2 的 DAEMON 閘**：`tests/no_second_run_state_test.sh` 掃到 `scripts/keepalive_log.sh:36` 的 `while :; do`，「only the allow-listed channels may (I.2)」。連帶 `test_keep_submissions.py::test_tc090_the_second_state_scan_passes`、`test_resume_edit_params_station.py::test_no_second_copy_of_run_state` 也紅。計畫（裁決 1）要一支常駐記錄迴圈，但沒有點名這支測試，也沒授權在 `DAEMON_ALLOW`（該測試檔 48 行）加一列。這是憲法閘，executor 不自行加白名單，也不改寫迴圈去避開掃描。要的裁決：准許加一列 `scripts/keepalive_log.sh|<理由>`（例如：只記錄站台連線開或關，不保存任何 run 的狀態），或改變 (6) 的做法。
2. **用字閘**：`test_web_wording_sweep.py::test_banned_words_cover_every_zh_string_table` 不准網頁 zh 字串表出現「run」（網頁用「分析」）。計畫 (2) 與 TC-009 逐字規定的 zh 紅條文字有兩個「run」（「已在跑的 run 不受影響；新的 run 在恢復前無法送出」）。兩者不能同時成立；改字要動 TC（executor 不能改），把字串移出 `STRINGS` 則是躲閘。要的裁決：zh 文字改成「分析」（verifier 改 TC-009／010 等），或在該測試為這一鍵開例外。若改字，`test_web_settings_ce_mobile.py` 的 STRINGS 雜湊與 ledger 的畫面證據要跟著重做。

下一步（接手的人）：拿到兩點裁決後照做，跑上面幾支相關檔，再跑一次全套。

## 備註
- 計畫「允許更新」只點名 `STYLE_SHA256`；另外四個檔（test_clean_page、test_web_guided_launch_preview、test_web_resume_edit、test_web_settings_register）釘的是整頁位元組雜湊，`STYLE` 多一條規則後必然改變，所以一併重釘。`test_launch_docs.py:32` 計畫點名的是 79 行，實際釘住「8 hours」的是 32 行，只改那一句。這兩點請審查者確認。
- 全套結果見最後一次 executor 報告與 `executor-status`。

## 2026-11-12 00:50 接手（stamp 20261112-0040-platform-mcp）：卡住，沒動程式
計畫已加「裁決（lead，11-11 深夜）」兩點（keepalive_log.sh 改單次執行；zh 紅條改用「分析」），但 `test-case.md`／`test-case-overview.md` 還是 0c6820fb（11-11 20:04，早於裁決）的版本，與裁決矛盾：
- TC-009（test-case.md:32）仍逐字要求「已在跑的 run 不受影響；新的 run 在恢復前無法送出」。裁決 2 說「verifier 重寫該 TC 的字串，頁面同一句」，新句子還沒寫出來；executor 不猜（雜湊釘值與畫面證據都跟著這一句）。
- TC-068（:111）仍要求預設間隔 600 秒、`ABF_KEEPALIVE_INTERVAL`、ONCE 模式；TC-069（:112）仍要求「以背景執行迴圈」再 kill；TC-073（:121）仍要求 PLATFORM.md 有 `nohup bash scripts/keepalive_log.sh >/dev/null 2>&1 &`。裁決 1 禁止 while／loop／nohup／sleep。
- TC-034（:62）的擋送出訊息也含「已在跑的 run 不受影響」，裁決沒提；請 verifier 一併決定要不要改。

下一步（接手的人，等 verifier 更新 TC 之後）：
1. `scripts/keepalive_log.sh` 改單次：呼叫一次 `--check-master`、追加一行；上一筆是 open 而這次 closed 時再寫 `event=closed lasted_min=…`（從 log 找這一段最早的 open 算），上一筆 closed 而這次 open 寫 `event=reopened`。拿掉 `while`、`sleep`、ROUNDS／INTERVAL。`tests/keepalive_log_test.sh` 改寫成連續呼叫。
2. `site_link.py` 的 zh `linkbar_down` 換成 verifier 給的句子；重釘 `test_web_settings_ce_mobile.py` 的 STRINGS 雜湊與受影響的頁面雜湊；重拍 zh 截圖。
3. PLATFORM.md、PITFALLS 第 61 條的用法改成「由人手動或既有排程呼叫一次」。
4. 相關檔：`--only no_second_run_state`、`--only keepalive`、`--pytest tests/test_web_wording_sweep.py`、`test_site_disconnect_ux.py`、`test_keep_submissions.py`、`test_resume_edit_params_station.py`，再跑一次全套。

## 2026-11-12 11:00 接手（stamp 20261112-1050-platform-mcp）：照 11-11 深夜與 11-12 裁決完成
派工說「既有程式應已符合，只要確認綠」；實際上上一輪卡住時沒動程式（見上一節），所以這一輪照裁決與 f7de2c6a 的新 TC 做完：
- [x] `scripts/keepalive_log.sh` 改成單次執行（TC-064～069）：呼叫一次 `--check-master`、追加一行就結束；上一次看到什麼從 log（含 `.1`）讀回，上一筆 open 這次 closed 寫 `event=closed lasted_min=… last_open=…`（從最後一次 closed 之後的第一筆 open 起算），上一筆 closed 這次 open 寫 `event=reopened`。沒有 while／sleep／nohup，沒有 INTERVAL／ROUNDS／ONCE 旋鈕；沒加進 `DAEMON_ALLOW`。ISO 時間轉秒用 bash 算術（`date -d` 是 GNU 專用，`portable_userland.sh` 不准）。
- [x] `tests/keepalive_log_test.sh` 改寫成連續呼叫（34 項），原有每個 TC 的斷言都保留或換成單次版的等價斷言；新增「分鐘數是從 log 算的」「輪替後狀態仍接得上」「腳本無迴圈字樣」「不在 DAEMON_ALLOW」。
- [x] zh 紅條與擋送出訊息的「run」改「分析」（TC-009、TC-034）：`site_link.py` 兩處；en 不變。
- [x] 釘值：`test_web_settings_ce_mobile.py` 的 zh `STRINGS` 雜湊重釘（只有那一句變了）。頁面雜湊不受影響（沒掉線時不輸出紅條）。
- [x] 文件（TC-073、TC-075）：PLATFORM.md 與 PITFALLS 第 61 條的用法改成「由人手動或既有排程呼叫一次 `bash scripts/keepalive_log.sh`」，沒有 nohup、不說常駐。
- [x] zh／en × 1440／390 截圖重拍、keepalive 實演重跑（見上面兩節）。
- 上一節列的兩個卡點（DAEMON 閘、用字閘）因此都解掉：`no_second_run_state_test.sh`、`test_keep_submissions.py`、`test_resume_edit_params_station.py`、`test_web_wording_sweep.py` 已綠。
- 全套結果見本輪 executor 報告與 `executor-status`。

- 2026-11-12 對照 base：axe `meta-refresh` 在 base 9ae086b2 就存在（web_board.py:956；UI2.md 同一規則同一節點），本件沒碰它；`.linkbar` 無 serious／critical。見 screenshots/summary.md。

## 2026-11-12 修正輪（驗收 REJECT 後，三項）
1. **TC-038／TC-039 測試**（`platform/tests/test_site_disconnect_ux.py`）：新增 `test_launch_pipeline_refused_when_closed`、`test_resume_and_relaunch_refused_when_closed[resume|relaunch]`、`test_terminal_launch_refused_when_closed`（走 PTY 的 `abf-platform launch`，打 y），另加對照 `test_resume_and_relaunch_go_through_when_open`。每條斷言：被擋（`sent` 為 false、無 job_id）、訊息含 agent 名與 `WSL` 與「重新登入」、新增的那一筆 confirmation 是 `void`（不是 pending／approved）、`launch_nextflow` job 數不變。四條路徑都被現有的單一閘擋下，**沒有發現新 bug**，程式碼沒改。
   - 閘門中和實驗：我在本地把 `jobs.py` 的 `== "closed":` 暫時改成 `== "closed" and False:`，四個新測試全部失敗（4 failed），然後 `git checkout` 還原；被中和的版本沒有 commit。
   - 因為閘本來就在，這些測試加進去就是綠的，所以那個 commit 的訊息雖寫 RED:，實際上是「補上缺的測試」，紅燈靠上面的中和實驗證明。
2. **截圖重拍**：用拋棄式平台（temp 資料夾、空閒 port，沒碰 8787/8788/8789 與真資料庫），agent 在線且自報 `site_link=closed`（重拍前 `closed_agents` 列出 `['agent-t']`），board／launch／settings × zh／en × 1440／390 共 12 張，每張都量到一條 `.linkbar`。舊的 12 張（agent 離線、沒有紅條）已被取代；`screenshots/summary.md` 重寫，只寫圖上看得到的。axe：只有 board 上既有的 critical `meta-refresh`（origin/v3 `web_board.py:958`），以及 12 頁都有的 moderate `landmark-unique`（`.side`、`.views`）；沒有任何項目指到 `.linkbar`。
3. **docs/TESTING.md**：新增 TC-032 手動步驟（白話：開哪頁、紅條的字與顏色、什麼情況會出現與不該出現、怎麼讓它消失）。
