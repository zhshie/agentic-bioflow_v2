# 測試案例：升級腳本的點名提示指向真的存在的段落；拿掉無條件 ok 的 TC-U27

**規格**：`specs/upgrade-hint-followup/plan.md`（本片只有計畫，沒有 spec.md；計畫即規格）　**總覽**：`test-case-overview.md`

維護者原話與對應：
- 「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」→ TC-H5（提示的其餘部分與結束碼不變）、TC-H6、TC-H7、TC-H8（範圍之外的東西都沒動）。
- 「絕不放寬安全網」→ TC-H11（除 TC-U27 外沒有任何既有斷言被刪或放寬）、TC-H12（真正保護平台的 TC-U28 與 `tests/platform_test.sh` 仍在）。
- PR #281 的目的：「升級後沒連回來的代理人要當場點名，並提示用 `abf-platform agent-token` 修」→ TC-H1、TC-H5。

類型只有三種：功能、例外、不在範圍。標「手動」的列，是閱卷者讀 `git diff` 或在 base 版重跑來核對（`docs/TESTING.md` 沒有對應步驟，這是這類修正片的通例）。

## User Story 1 — 提示指到真的存在、教人重發 token 的段落（優先度 P1）

背景：有代理人升級後沒連回來時，腳本印一句提示。現在提示叫人去看「docs/TESTING.md 的 403 一節」，但那份文件沒有這個名字的段落。計畫決定改成指向 `docs/TESTING.md` 的 `## Owner binding follow-up (owner-binding)` 一節第 2 步（該步驟教人確認 403、`agent-token revoke`、`agent-token new`、換 token 檔、重啟代理人）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H1 | 計畫「決定」：提示改成指向 Owner binding follow-up 一節第 2 步 | 功能 | 兩個代理人 alpha、beta 在升級前在線；重啟後只有 alpha 重新連上，beta 沒回來（等待秒數設成很短） | 跑 `deploy/platform-upgrade.sh`，讀它印出的點名提示 | 提示含完整的 `docs/TESTING.md 的「Owner binding follow-up」一節第 2 步`；不再含「403 一節」 | 自動：`tests/platform_upgrade_test.sh`（新增的測試） |
| TC-H2 | 計畫「目標」：提示裡引用的段落名一定存在於該文件 | 功能 | 同 TC-H1 的提示輸出；`docs/TESTING.md` 在工作區中 | 測試從提示抓出 `docs/TESTING.md 的「…」一節` 引號裡的段落名，到 `docs/TESTING.md` 找以 `## ` 開頭、含這個名字的標題 | 找得到：`## Owner binding follow-up (owner-binding)` 含「Owner binding follow-up」 | 自動：`tests/platform_upgrade_test.sh`（新增的測試） |
| TC-H3 | 計畫「失敗先行測試」：新測試改前必須紅 | 例外 | base 版腳本（提示寫「403 一節」、沒有引號內段落名）；新測試已加入 | 閱卷者在 base 版腳本上跑新測試，並讀 ledger 貼的紅輸出 | 新測試在 base 版是紅的（FAIL），改腳本後轉綠；紅的輸出有貼進 `specs/upgrade-hint-followup/ledger.md` | 手動：閱卷者在 base 版腳本上重跑新測試，對照 ledger |
| TC-H4 | 計畫「失敗先行測試」：現在紅的原因是抓不到引號內段落名 | 例外 | 提示裡沒有 `「…」` 引號段落名（例如 base 版的「403 一節」） | 測試嘗試抓段落名 | 抓到的段落名是空的或在文件找不到時，測試判 FAIL，不會當作通過（測試內有「抓到的名字不是空的」這一道斷言） | 自動：`tests/platform_upgrade_test.sh`（閱卷時讀斷言，並配合 TC-H3 在 base 版確實紅） |
| TC-H5 | 計畫「決定」：其餘字不動；「對照」：既有點名測試維持綠 | 功能 | 同 TC-H1 | 跑整支 `tests/platform_upgrade_test.sh` | 既有的 TC-U2（只點名 beta、結束碼 1）、TC-U9（輸出沒有 token 值）、TC-U16（含「這些代理人重啟後沒有重新連上」、`abf-platform agent-token`、`docs/TESTING.md`、「日誌」，且沒有 Traceback／SELECT）全部維持綠，而且這幾行斷言文字與 base 相同 | 自動：`tests/platform_upgrade_test.sh` |
| TC-H6 | 計畫「範圍」、「不做」：不在 TESTING.md 新增「403」段落、不改標題 | 不在範圍 | 改動完成 | `git diff <base>...HEAD -- docs/TESTING.md` | 沒有任何差異：標題沒改、沒有新增以 403 命名的段落 | 手動：閱卷者讀 git diff |
| TC-H7 | 計畫「範圍：檔案」：只准改兩個檔 | 不在範圍 | 改動完成 | `git diff --stat <base>...HEAD`（排除 `specs/upgrade-hint-followup/` 的計畫與 ledger） | 只有 `deploy/platform-upgrade.sh` 與 `tests/platform_upgrade_test.sh`；`platform/`、其他測試檔、`.github/`、`docs/TESTING.md` 都沒有；腳本只有提示那一句（約第 136 行）有變動 | 手動：閱卷者讀 git diff |
| TC-H8 | 計畫「不做」：不改等待秒數、名單邏輯、結束碼 | 不在範圍 | 改動完成 | 逐行讀 `deploy/platform-upgrade.sh` 的 diff | 變動只在提示文字裡的段落名那一句；等待、輪詢、名單、`exit` 的邏輯一行都沒動 | 手動：閱卷者讀 git diff |

## User Story 2 — 拿掉一條不論結果都過關的測試行（優先度 P2）

背景：`tests/platform_upgrade_test.sh` 的 TC-U27 在沒設 `ABF_UPGRADE_SKIP_PLATFORM_TEST` 時直接印 `ok`，沒有檢查任何東西。計畫裁決：刪除，因為真正的保護是 `tests/platform_test.sh` 在全套裡跑。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H9 | 計畫「失敗先行測試」：TC-U27 區塊刪除，ok 數差正好 1 | 功能 | 沒設 `ABF_UPGRADE_SKIP_PLATFORM_TEST`；刪除前後各跑一次整支測試 | 數兩次輸出中結尾是 `ok` 的行 | `tests/platform_upgrade_test.sh` 裡不再有 TC-U27 的 if/else 區塊（含 `skip "TC-U27 …"` 那一支）；扣掉新測試新增的 ok 行之後，刪除前比刪除後正好多 1（ledger 有記數字，閱卷者重算） | 手動：閱卷者對照 ledger 並重跑核算 |
| TC-H10 | 計畫「完成標準」：整支 `tests/platform_upgrade_test.sh` 仍全綠 | 功能 | 改動完成 | `bash tests/platform_upgrade_test.sh` | 輸出最後一行是 `all platform_upgrade tests passed`，沒有 FAIL | 自動：`tests/platform_upgrade_test.sh` |

## 憲法與安全網

本片沒有碰憲法的 hooks 或閘門；對應的是維護者的「絕不放寬安全網」。我沒有指認出本片觸及的具體憲法條號，閱卷時若發現碰到，須回報。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-H11 | 維護者原話「絕不放寬安全網」；計畫「完成標準」：除 TC-U27 外沒有任何既有斷言被刪或放寬 | 功能 | 改動完成 | `git diff <base>...HEAD -- tests/platform_upgrade_test.sh`，逐行比對 | 被刪掉的行只有 TC-U27 那個區塊；其餘改動全是新增的新測試；沒有斷言被改寬、被跳過，或預期值被改成配合新輸出 | 手動：閱卷者讀 git diff |
| TC-H12 | 維護者原話「絕不放寬安全網」；計畫裁決 1：真正的保護是 `platform_test.sh` | 不在範圍 | 改動完成 | 跑 `tests/platform_upgrade_test.sh` 並看 `tests/platform_test.sh` 是否仍在 | TC-U28（`platform/`、`deploy/backup.sh`、`deploy/systemd` 沒被改）仍存在且綠；`tests/platform_test.sh` 沒被刪、沒被改 | 自動：`tests/platform_upgrade_test.sh`（TC-U28） |
