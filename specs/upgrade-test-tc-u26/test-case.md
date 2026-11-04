# 測試案例：TC-U26 改成檢查現在的 want_list（不再拿 merge-base 差異當檢查）

<!--
Written by the verifier (CONTRACT mode). Source: specs/upgrade-test-tc-u26/plan.md (no separate spec.md; the plan is the spec).
Only behaviour the plan states is tested here.
-->

**規格**：`specs/upgrade-test-tc-u26/plan.md`（本任務沒有 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

白話背景：`tests/platform_upgrade_test.sh` 裡的 TC-U26 原本想保護「`tests/hosted_deploy_test.sh` 的 want_list（部署資料夾應有的檔案清單）含 `$D/platform-upgrade.sh`，且原本六項沒少」。它的做法是拿「和 merge-base 的差異」來比，但那一項早已併入 v3，差異是空的，所以在 v3 上必紅。這次改成直接看現在的清單。

**維護者原話**（計畫引用）：「絕不放寬安全網」（`specs/upgrade-agents-reconnect-check/test-case.md:15`，對應 TC-U25、TC-U26、TC-U27）；「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」（2026-10-29 清理掃描）。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：清單少了東西時，新檢查怎麼反應（必須變紅）。
- **不在範圍**：計畫明講這次不做的事；確認真的沒做。

驗證方式說明：「自動」是跑測試腳本就能看到；「手動」是一次性證據（紅輸出、負向證明貼在計畫指定的 ledger）或閱卷者讀 diff，不進 repo、不進 `docs/TESTING.md`（計畫禁止改 `docs/`）。

## User Story 1 — TC-U26 改成檢查現況（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；GREEN（改後）；維護者原話「絕不放寬安全網」 | 功能 | 乾淨的 v3 worktree（HEAD 等於 origin/v3，`tests/hosted_deploy_test.sh` 沒被動過），環境有 Python ≥3.10 加 starlette | 執行 `bash tests/platform_upgrade_test.sh` | 輸出裡 TC-U26 那一行是 ok（不是 FAIL、不是 skip），沒有任何 FAIL 行 | 自動：`tests/platform_upgrade_test.sh` |
| TC-002 | GREEN（改後） | 功能 | 同 TC-001 | 執行 `bash tests/platform_upgrade_test.sh` 看最後一行 | 最後一行是 `all platform_upgrade tests passed`，結束碼 0 | 自動：`tests/platform_upgrade_test.sh` |
| TC-003 | 作法：標籤 | 功能 | 同 TC-001 | 執行腳本，看 TC-U26 那一行的文字 | 該行文字為 `TC-U26 hosted_deploy_test.sh want_list names platform-upgrade.sh and the six originals` | 自動：`tests/platform_upgrade_test.sh`（輸出比對） |
| TC-004 | GREEN（改後）：ok 行數 | 功能 | 取得改前與改後兩次完整輸出 | 數兩次輸出中的 ok 行數 | 改後 ok 行數 ＝ 改前 ok 行數 ＋ 1（改前 TC-U26 是 FAIL，改後是 ok，其餘行不變） | 手動：閱卷者比對 ledger 貼的輸出 |
| TC-005 | 作法：不再依賴 git 歷史（不需要 origin/v3）；完成標準「TC-U26 不再 skip」 | 功能 | 沒有 `origin/v3` 參照的環境（例如淺 clone 或沒抓 origin/v3） | 執行 `bash tests/platform_upgrade_test.sh` | TC-U26 仍然是 ok，不是 skip（TC-U28 照舊在這種環境 skip） | 手動：ledger 證據，或閱卷者在此環境執行 |
| TC-006 | 失敗先行測試：RED（改前） | 功能 | 改動之前、乾淨的 v3 worktree | 執行 `bash tests/platform_upgrade_test.sh` | 輸出含一行 `TC-U26 … FAIL`，末尾 `1 FAILED`；此紅輸出已貼進 ledger（若與計畫推演不符，已回報 developer-agent 而非硬改） | 手動：ledger 證據 |
| TC-007 | 完成標準：全套全綠 | 功能 | 改動完成，在 WSL／Linux 執行 | 執行 `bash tests/run_all.sh` | 全綠（已知環境紅依 dev-plans README「通例：已知環境紅」處理） | 自動：`tests/run_all.sh` |
| TC-008 | 負向證明 1 | 例外 | 在 worktree 內暫時把 `tests/hosted_deploy_test.sh:283` 的 `$D/platform-upgrade.sh` 刪掉 | 執行 `bash tests/platform_upgrade_test.sh` | TC-U26 變紅（FAIL）；之後 `git checkout -- tests/hosted_deploy_test.sh` 還原，且證據已貼 ledger | 手動：ledger 證據 |
| TC-009 | 負向證明 2 | 例外 | 在 worktree 內暫時只把 want_list 裡的 `backup.sh` 刪掉（`platform-upgrade.sh` 保留） | 執行 `bash tests/platform_upgrade_test.sh` | TC-U26 變紅（FAIL）；還原後恢復為 ok，證據已貼 ledger | 手動：ledger 證據 |
| TC-010 | 作法 2：其餘六項沒少 | 例外 | 讀 `tests/platform_upgrade_test.sh` 的新 TC-U26 區塊 | 逐項對照 | 區塊檢查 `want_list=` 那一行含 `$D/platform-upgrade.sh`，且同一行也要求 `Caddyfile.template`、`backup.sh`、`env.example`、`systemd/abf-mcp.service.in`、`systemd/abf-serve.service.in`、`systemd/abf-web.service.in` 六項全在；少任何一項都會走 `bad "TC-U26"` | 手動：閱卷者讀測試碼 |

## User Story 2 — 不放寬安全網、不動別處（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 作法：看現況、不依賴 git 歷史 | 功能 | 讀改後的 TC-U26 區塊 | 找 `git merge-base`、`git diff`、`origin/v3` | 區塊內不再用 git 歷史（沒有 merge-base、沒有 git diff）；直接讀 `tests/hosted_deploy_test.sh` 以 `want_list=` 開頭的那一行 | 手動：閱卷者讀 diff |
| TC-012 | 不做：不放寬（維護者原話「絕不放寬安全網」） | 不在範圍 | 讀改後的 TC-U26 區塊 | 找無條件 ok、`\|\| true`、降成 skip | 都沒有：TC-U26 不是無條件 ok、沒有 `\|\| true`、不會降成 skip；它的 ok 只在檢查成立時才印（TC-008、TC-009 已證明能變紅） | 手動：閱卷者讀 diff |
| TC-013 | 完成標準：除 TC-U26 區塊外沒有既有斷言被刪或放寬 | 功能 | `git diff <base>...HEAD -- tests/platform_upgrade_test.sh` | 逐行檢視差異 | 變動只有 TC-U26 區塊（舊區塊被換掉並移到外層 `if mb=…` 之前）；TC-U24、TC-U25、TC-U27 等其他斷言一條都沒被刪、沒被改弱 | 手動：閱卷者讀 diff |
| TC-014 | 作法：結構 | 功能 | 讀改後檔案 | 看 TC-U26 區塊的位置 | TC-U26 區塊位於 `if mb=$(git merge-base …)` 之前，不在該 if 內，所以沒有 git 或沒有 origin/v3 時也會執行 | 手動：閱卷者讀 diff |
| TC-015 | 不做：不改 TC-U28 | 不在範圍 | 讀改後檔案 | 看 TC-U28 區塊 | TC-U28 內容與 base 相同，仍留在原本的 `if mb=…` 內（沒有 origin/v3 時照舊 skip） | 手動：閱卷者讀 diff |
| TC-016 | 範圍：只准改 `tests/platform_upgrade_test.sh` | 不在範圍 | `git diff --stat <base>...HEAD` | 看變動檔案清單 | 只有 `tests/platform_upgrade_test.sh`；`deploy/`、`tests/hosted_deploy_test.sh`、`platform/`、`docs/`、`.github/`、`specs/` 下任何檔、`platform-upgrade.sh` 都沒被動（`specs/` 下計畫指定的 ledger 紀錄不算） | 手動：閱卷者看 diff stat |
| TC-017 | 作法：「hosted_deploy_test.sh 全綠」已由 TC-U24/U25/U30 負責，不重複 | 不在範圍 | 讀改後檔案 | 看新 TC-U26 區塊與原約 :222 的 TC-U24/U25/U30 那一行 | 新區塊沒有再次執行 `tests/hosted_deploy_test.sh`；原 TC-U24/U25/U30 那一行維持不變 | 手動：閱卷者讀 diff |
