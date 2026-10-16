# 測試案例：scratch-clone-main（測試用暫存副本不得自帶 main 分支）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer.
-->

**規格**：`.specify/bugs/scratch-clone-main/assessment.md`（bug 修補，維護者範例見該檔「維護者的例子（原文）」）　**總覽**：`test-case-overview.md`

白話：有兩支測試要做一個「暫存副本」，並且假設副本裡沒有 main 分支。平常在 PR 上跑時這個假設成立，但 main 合併後 CI 就是在 main 上跑，副本會自動帶出 main，於是那條「確認沒有 main」必敗，main 的 CI 每次都紅。修法是：副本做好後，如果這次不要 main，就先切成「不在任何分支上」再把 main 刪掉。

名詞：
- 「在 main 上跑」＝執行測試的那份檢出（checkout）目前所在的分支就叫 `main`，等同合併後的 CI。可用「複製一份專案到暫存資料夾，再 `git checkout -B main`」重現。
- 「在 PR 上跑」＝所在位置不是 main（例如 PR 的合併參照是「不在任何分支上」，或一般功能分支），等同現在綠的情況。
- 「暫存副本」＝測試內部用 `git clone --depth 1` 做出的臨時複本；「nomain」副本要求沒有 main，「withmain」副本要求有 main。

類型只有三種：

- **功能**：修補說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應。
- **不在範圍**：修補明講這次不做的事；確認真的沒做。

## User Story 1 — 「main 合併完，CI 要綠；不能因為在 main 上跑就紅。」（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 維護者範例 1：「main 合併完，CI 要綠」；Reproduction | 功能 | 把修補後的專案複製到暫存資料夾，`git checkout -B main`，使目前分支就叫 main | 在該處執行 `bash tests/constitution_scope_test.sh` | 結束碼 0，結尾顯示 `all passed`，輸出裡沒有任何 `FAIL` 行；其中「scratch clone really has no main ref」那一行是 ok（修補前同樣情況是這一行 FAIL） | 手動：驗收者依 Reproduction 步驟在暫存檢出執行並記錄 |
| TC-002 | 維護者範例 1；Proposed Remediation 第 2 點（`platform_direction_docs_test.sh` 同樣寫法一起修） | 功能 | 同 TC-001 的「分支就叫 main」暫存檢出 | 執行 `bash tests/platform_direction_docs_test.sh` | 結束碼 0，結尾 `all passed`，沒有任何 `FAIL` 行；其中 nomain 與 withmain 兩種副本的 TC-010、TC-011、TC-012、TC-014 都是 ok | 手動：驗收者在同一暫存檢出執行並記錄 |
| TC-003 | 修法：不要 main 時副本裡不可有 main | 功能 | 來源檢出在 main 上（TC-001 的環境），測試做 nomain 副本 | 測試檢查 nomain 副本是否有 `refs/heads/main` | 副本裡沒有 `refs/heads/main`；測試裡「scratch clone really has no main ref」這條斷言仍然存在、內容不變、結果 ok | 自動：`tests/constitution_scope_test.sh` |
| TC-004 | 修法：「先切成不在任何分支上」 | 功能 | 來源檢出在 main 上，測試做 nomain 副本 | 測試檢查 nomain 副本的 HEAD 狀態 | nomain 副本的 HEAD 是「不在任何分支上」（detached），不是停在某個分支 | 自動：`tests/constitution_scope_test.sh` |
| TC-005 | 修法：要 main 時維持現狀（「keep today's behaviour」） | 功能 | 來源檢出在 main 上，測試做 withmain 副本 | 測試檢查 withmain 副本是否有 `refs/heads/main` | 副本裡有 `refs/heads/main`，且指向副本目前的 HEAD 提交；要 main 的副本沒有被誤刪 | 自動：`tests/constitution_scope_test.sh` |
| TC-006 | Proposed Remediation 第 2 點 | 功能 | 來源檢出在 main 上，`tests/platform_direction_docs_test.sh` 做 nomain 副本 | 測試檢查 nomain 副本是否有 `refs/heads/main` | 副本裡沒有 `refs/heads/main`，且 HEAD 不在任何分支上；withmain 副本有 `refs/heads/main` | 自動：`tests/platform_direction_docs_test.sh` |
| TC-007 | 修法的「如果副本裡有 main 才刪」 | 例外 | 來源檢出不在 main 上（因此 nomain 副本一開始就沒有 main，沒有東西可刪） | 兩支測試各自做 nomain 副本 | 做副本不會因為「找不到 main 可刪」而失敗或印錯誤；副本照常建立，「scratch shallow clone」類斷言是 ok，不出現 `FAIL` | 自動：`tests/constitution_scope_test.sh`、`tests/platform_direction_docs_test.sh` |
| TC-008 | 憲法安全網指紋檢查不得因修補而失靈；維護者範例 1 的反面（綠不能是因為少檢查） | 例外 | 來源檢出在 main 上；nomain 副本裡把憲法 Safety Net 段改一句 | 執行 `bash tests/constitution_scope_test.sh` | 外層仍全部通過；而內層「改動 Safety Net」那些案例（TC-003、TC-004、TC-006、TC-007、TC-008，以輸出裡的 ok 行為準）全部維持 ok，也就是改動確實被抓到、改動 Safety Net 以外的地方確實不被誤報 | 手動：驗收者在 TC-001 的暫存檢出核對輸出中這幾行 |
| TC-009 | 詞彙表檢查不得因修補而失靈 | 例外 | 來源檢出在 main 上；nomain 與 withmain 副本裡 CONTEXT.md 刪掉 `**Run index**` | 執行 `bash tests/platform_direction_docs_test.sh` | 輸出裡 TC-011（nomain）與 TC-012（withmain）都是 ok，也就是被刪的詞確實失敗並點名 `[Run index]`；TC-014（新增詞仍通過）也是 ok | 手動：驗收者在 TC-001 的暫存檢出核對輸出中這幾行 |
| TC-010 | Proposed Remediation「Red first」 | 功能 | 修補提交之前的程式（`git stash` 或切回修補前提交）放在分支叫 main 的暫存檢出 | 執行 `bash tests/constitution_scope_test.sh`，再換成修補後的程式重跑 | 修補前：出現 `scratch clone really has no main ref  FAIL`；修補後：同一行 ok。fix.md 進度紀錄裡有這次修補前的 FAIL 紀錄，不是只寫「已修」 | 手動：驗收者查 `.specify/bugs/scratch-clone-main/fix.md` 並自行重現 |

## User Story 2 — 「在 PR 上跑，結果跟現在一樣綠。」（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 維護者範例 2：「在 PR 上跑，結果跟現在一樣綠」 | 功能 | 目前所在分支不是 main（例如 `fix/scratch-clone-detached`，或 detached HEAD） | 執行 `bash tests/constitution_scope_test.sh` | 結束碼 0，`all passed`，沒有 `FAIL` 行；nomain 副本無 main、withmain 副本有 main，與修補前相同 | 自動：`tests/constitution_scope_test.sh` |
| TC-012 | 維護者範例 2 | 功能 | 同 TC-011 的環境 | 執行 `bash tests/platform_direction_docs_test.sh` | 結束碼 0，`all passed`，沒有 `FAIL` 行，TC-010..015 的行與修補前一樣都在且是 ok | 自動：`tests/platform_direction_docs_test.sh` |
| TC-013 | 維護者範例 2；「結果跟現在一樣」不得靠少檢查達成 | 功能 | 在 main（修補前）與修補後分支各執行一次兩支測試，並存下輸出 | 比對兩份輸出的檢查項目名稱（每行行首的文字） | 修補前存在的每一條檢查名稱，修補後都還在且結果是 ok；`constitution_scope_test.sh` 的檢查總數不少於修補前的 101 條（可以多、不可以少） | 手動：驗收者逐行比對兩份輸出 |

## 不在範圍（修補明講不做的事）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 不在範圍：fingerprint 邏輯、`PINNED_SN_SHA256` | 不在範圍 | 修補完成 | `git diff main...HEAD -- tests/constitution_scope_test.sh` | 差異裡沒有改到取出 Safety Net 段的 awk、算指紋的程式、`PINNED_SN_SHA256` 的值，也沒有改到指紋檢查的任何斷言文字；差異只落在 `mkclone` 輔助函式 | 手動：驗收者看 diff |
| TC-015 | 不在範圍：憲法本身 | 不在範圍 | 修補完成 | `git diff main...HEAD -- .specify/memory/constitution.md` | 沒有任何差異 | 手動：驗收者看 diff |
| TC-016 | 不在範圍：CI 設定 | 不在範圍 | 修補完成 | `git diff main...HEAD -- .github` | 沒有任何差異（修的是測試的假設，不是改 CI 讓它不在 main 上跑） | 手動：驗收者看 diff |
| TC-017 | 修補範圍只限兩支測試 | 不在範圍 | 修補完成 | `git diff --stat main...HEAD` | 除了 `.specify/bugs/scratch-clone-main/` 底下的紀錄檔外，只有 `tests/constitution_scope_test.sh` 與 `tests/platform_direction_docs_test.sh` 被改；沒有改到 `hooks/`、`scripts/`、其他 `tests/`、`spec`、`test-case*.md` | 手動：驗收者看 diff |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-018 | 憲法「Safety Net」指紋檢查（`tests/constitution_scope_test.sh` 為其檢查）：修法不得再引入「拿本機 main 比對」或「略過」分支（issue #71 的結論） | 功能 | 修補完成，`mkclone` 已加入刪除 main 的程式 | 執行 `bash tests/constitution_scope_test.sh`（在 main 上與不在 main 上各一次） | 檔內自檢「no comparison against the main ref left in this file」與「no skip branch left in this file」兩行都是 ok（新寫的刪除 main 的程式不得含 `git show main:`、`rev-parse --verify -q main` 或 skipped 字樣） | 自動：`tests/constitution_scope_test.sh` |
| TC-019 | 同上：不得削弱或刪除任何斷言 | 功能 | 修補完成 | `git diff main...HEAD -- tests/constitution_scope_test.sh tests/platform_direction_docs_test.sh`，檢視所有被移除或修改的行 | 被移除／修改的行只出現在 `mkclone` 輔助函式內；沒有任何斷言被刪、被放寬（如把 `FAIL` 條件改鬆）、被加上略過，也沒有任何預期值為了符合新輸出而被改動 | 手動：驗收者看 diff |
