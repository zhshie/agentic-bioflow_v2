# 測試案例：平台升級後確認站台代理人重新連上

**規格**：`specs/upgrade-agents-reconnect-check/plan.md`（本件沒有 spec.md，以計畫為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫「不做」或「不准碰」的事；測試確認它真的沒做。

名詞（一句話）：「代理人」＝站台上替使用者跑事的程式；「重連」＝重啟平台後，代理人再向平台打一次招呼，平台記下的「最後聯絡時間」比重啟前一刻晚；「假重啟指令」＝測試用的小腳本，代替真的 `systemctl`，並可讓指定代理人「重連」或「被拒（403）」。所有測試只用暫存資料夾，不碰真的 systemd、網路、站台。

驗證方式一律是 `tests/platform_upgrade_test.sh`（新檔）或下列註明的既有測試檔；每條測試要在註解寫上自己的 TC 編號。

維護者原話與對應：「絕不放寬安全網」→ TC-U25、TC-U26、TC-U27（以及 TC-U7 等待有上限、TC-U3 被拒也抓得到）。「A 級…不改使用者看得到的行為」→ 計畫已定為 B 級（新增操作員腳本），沒有對應測試。2026-10-29 nano4 停擺（重啟後代理人收到 403 沒人發現）是派工說明，不是維護者逐字話，只用來設計 TC-U3 的情境。

## User Story 1 — 升級重啟後，逐一確認代理人重新連上，沒連上就點名（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-U1 | 計畫 TC-U1；決定 3、4 | 功能 | 暫存 `platform.db` 裡有 `alpha`、`beta` 兩個代理人，剛聯絡過（在線）；假重啟指令會讓兩個都重連 | 跑升級腳本（用假指令取代 pull、install、重啟） | 結束碼 0；輸出含 `2 agents reconnected` | 自動：`tests/platform_upgrade_test.sh` |
| TC-U2 | 計畫 TC-U2；決定 5；裁決 5 | 例外 | 同上兩個在線代理人（兩個都還在「60 秒內算在線」的窗內）；假重啟只讓 `alpha` 重連；`ABF_UPGRADE_WAIT_SECONDS=3` | 跑升級腳本 | 結束碼 1；「沒有重新連上」那一句點名 `beta`，且那一句不含 `alpha`；整個測試在 15 秒內跑完（重啟前的最後聯絡還在 60 秒窗內，也不能被當成已重連） | 自動：`tests/platform_upgrade_test.sh` |
| TC-U3 | 計畫 TC-U3（本事件重現）；決定 5 | 例外 | `alpha`、`beta` 在線；`beta` 的 token 名字對不上擁有者，假重啟對 `beta` 呼叫 `register` 會被拒（OwnerMismatch，即 403，資料不寫入）；`alpha` 正常重連；`ABF_UPGRADE_WAIT_SECONDS=3` | 跑升級腳本 | 結束碼 1；輸出點名 `beta`，沒有把 `alpha` 當成沒連上 | 自動：`tests/platform_upgrade_test.sh` |
| TC-U4 | 計畫 TC-U4；決定 1；裁決 4 | 功能 | 一個重啟前就離線的代理人 `gamma`（最後聯絡很舊）；另有在線的 `alpha` 且會重連 | 跑升級腳本；`gamma` 不重連 | 結束碼 0；`gamma` 沒被當作失敗點名（只有重啟前在線的才算期望名單） | 自動：`tests/platform_upgrade_test.sh` |
| TC-U5 | 計畫 TC-U5；決定 6；裁決 3 | 功能 | `platform.db` 已建好，但裡面沒有任何代理人 | 跑升級腳本 | 結束碼 0；輸出含「沒有在線代理人可檢查」 | 自動：`tests/platform_upgrade_test.sh` |
| TC-U6 | 計畫 TC-U6；決定 5 | 例外 | 在線代理人 `alpha`；假重啟指令結束碼非 0；`ABF_UPGRADE_WAIT_SECONDS` 設得很長（例如 60） | 跑升級腳本並計時 | 結束碼非 0；3 秒內結束（沒有進入等待） | 自動：`tests/platform_upgrade_test.sh` |
| TC-U7 | 計畫 TC-U7；決定 3 | 例外 | 在線代理人 `alpha`；假重啟指令什麼都不做（無人重連）；`ABF_UPGRADE_WAIT_SECONDS=2` | 跑升級腳本並計時 | 6 秒內結束（不會無限等）；結束碼 1 | 自動：`tests/platform_upgrade_test.sh` |
| TC-U9 | 計畫 TC-U9；專長守則「密鑰不得出現在日誌或回應」 | 例外 | 暫存 `tokens.db` 裡有字串 `SECRET_TOKEN_VALUE`；情境同 TC-U2 | 跑升級腳本，收集標準輸出與標準錯誤 | 輸出完全不含 `SECRET_TOKEN_VALUE` | 自動：`tests/platform_upgrade_test.sh` |
| TC-U10 | 裁決 5（「晚於重啟前一刻」） | 例外 | 剛把 `beta` 註冊完就立刻跑腳本（不等待），假重啟不讓 `beta` 重連；`ABF_UPGRADE_WAIT_SECONDS=3` | 跑升級腳本 | 結束碼 1 且點名 `beta`（剛註冊完、同一秒內的聯絡不能被當成「重啟後的重連」） | 自動：`tests/platform_upgrade_test.sh` |
| TC-U11 | 裁決 7（pull 失敗就停） | 例外 | `ABF_UPGRADE_PULL_CMD` 換成結束碼非 0 的假指令；安裝與重啟的假指令各會留下標記檔 | 跑升級腳本 | 結束碼非 0；安裝與重啟的標記檔都不存在（失敗之後沒有繼續） | 自動：`tests/platform_upgrade_test.sh` |
| TC-U12 | 裁決 7（install 失敗就停） | 例外 | pull 假指令成功、`ABF_UPGRADE_INSTALL_CMD` 假指令結束碼非 0；重啟假指令會留標記檔 | 跑升級腳本 | 結束碼非 0；重啟標記檔不存在（沒重啟） | 自動：`tests/platform_upgrade_test.sh` |
| TC-U13 | 裁決 7（依文件順序）；決定 2 | 功能 | pull、install、重啟三個假指令各把自己的名字附加到同一個紀錄檔；在線代理人會重連 | 跑升級腳本 | 紀錄檔恰為 pull、install、重啟三行，順序如此，各一次；結束碼 0 | 自動：`tests/platform_upgrade_test.sh` |
| TC-U15 | 決定 3（每 2 秒讀一次直到回來） | 功能 | 在線代理人 `alpha`；假重啟指令在背景延遲約 2 秒才讓 `alpha` 重連；`ABF_UPGRADE_POLL_SECONDS=1`、`ABF_UPGRADE_WAIT_SECONDS=10` | 跑升級腳本 | 結束碼 0（等到了，沒有提早判失敗）；輸出含 `1 agents reconnected` 或同義的「全部重連」一行 | 自動：`tests/platform_upgrade_test.sh` |
| TC-U16 | 決定 5；專長守則「錯誤訊息說明原因與處理」 | 例外 | 情境同 TC-U2 | 跑升級腳本，看輸出 | 輸出是白話：說「這些代理人重啟後沒有重新連上」並列名字；含處理提示 `abf-platform agent-token` 與 `docs/TESTING.md`、並提到看代理人的日誌；不含 `Traceback`、`SELECT` | 自動：`tests/platform_upgrade_test.sh` |
| TC-U17 | 作法「參數錯誤結束碼 2」 | 例外 | 重啟假指令會留標記檔 | 跑 `deploy/platform-upgrade.sh --bogus`（未知選項） | 結束碼 2；輸出說明用法；重啟標記檔不存在（沒做任何事） | 自動：`tests/platform_upgrade_test.sh` |
| TC-U18 | 決定 3（`--wait N`） | 功能 | 在線代理人 `alpha`，無人重連；不設環境變數 | 跑升級腳本 `--wait 2` 並計時 | 6 秒內結束；結束碼 1 | 自動：`tests/platform_upgrade_test.sh` |
| TC-U19 | 決定 7（資料夾尋找照 backup.sh） | 功能 | 只設 `ABF_PLATFORM_DB=<暫存>/d/index.db`，`platform.db` 放在同一資料夾 `<暫存>/d/`；不設 `ABF_PLATFORM_STATE` | 跑升級腳本（情境同 TC-U1） | 讀到該資料夾的 `platform.db`；結束碼 0；輸出含 `2 agents reconnected` | 自動：`tests/platform_upgrade_test.sh` |
| TC-U20 | 決定 7（資料夾尋找照 backup.sh） | 功能 | 只設 `XDG_DATA_HOME=<暫存>/x`，`platform.db` 在 `<暫存>/x/abf-platform/`；不設 `ABF_PLATFORM_DB`、`ABF_PLATFORM_STATE` | 跑升級腳本（情境同 TC-U1） | 讀到該 `platform.db`；結束碼 0；輸出含 `2 agents reconnected` | 自動：`tests/platform_upgrade_test.sh` |
| TC-U21 | 「不做」第 5 條（輸出提醒一句先備份） | 功能 | 情境同 TC-U1 | 跑升級腳本，看輸出 | 輸出有一句提醒先備份（含 `backup` 或「備份」） | 自動：`tests/platform_upgrade_test.sh` |
| TC-U22 | 決定 7（只讀 platform.db，不寫不刪） | 功能 | 假重啟指令什麼都不做；腳本跑前記下 `platform.db` 的 agents 表內容與 `tokens.db` 的檔案雜湊 | 跑升級腳本（無人重連，失敗結束） | 跑完後 agents 表每一列（含 `last_seen_at`）與 `tokens.db` 和跑前完全相同 | 自動：`tests/platform_upgrade_test.sh` |
| TC-U23 | 作法「不需要新 API」；專長守則「不得有第二份邏輯」 | 功能 | 腳本檔案（排除註解） | 檢查程式碼 | 讀代理人清單是呼叫既有的 `list_agents`；程式碼不含自己寫的 SQL（`SELECT`、`sqlite3`） | 自動：`tests/platform_upgrade_test.sh` |
| TC-U29 | 「不做」第 2 條（不自動修復） | 不在範圍 | PATH 上放假的 `abf-platform`、`scancel`、`ssh`，被叫到就留紀錄；情境同 TC-U3（`beta` 被拒）；跑前記下 `tokens.db` 雜湊 | 跑升級腳本 | 假指令紀錄為空（沒重發 token、沒碰站台）；`tokens.db` 雜湊不變；結束碼 1 | 自動：`tests/platform_upgrade_test.sh` |
| TC-U31 | 裁決 8（不自動回復舊版本） | 不在範圍 | 情境同 TC-U2；PATH 上放假的 `git`，被叫到就留紀錄；pull 與 install 用環境變數換成假指令 | 跑升級腳本；另檢查程式碼（排除註解） | 假 `git` 沒被叫到；程式碼不含 `git reset`、`git checkout`、`git revert`、`git stash`；結束碼 1 | 自動：`tests/platform_upgrade_test.sh` |
| TC-U32 | 「不做」第 6 條（不通知外部） | 不在範圍 | PATH 上放假的 `curl`、`wget`、`mail`、`sendmail`，被叫到就留紀錄；情境同 TC-U2 | 跑升級腳本 | 假指令紀錄為空；結束碼 1 | 自動：`tests/platform_upgrade_test.sh` |
| TC-U33 | 「不做」第 5 條（不執行 backup.sh） | 不在範圍 | 情境同 TC-U1；備份目的資料夾不存在；假的 `deploy/backup.sh` 呼叫會留紀錄（或檢查程式碼） | 跑升級腳本 | 沒有備份資料夾被建立、`backup.sh` 沒被叫到；程式碼（排除註解）不含 `backup.sh` 的呼叫 | 自動：`tests/platform_upgrade_test.sh` |

## User Story 2 — 腳本形式、文件入口與既有檢查不被放寬（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-U8 | 計畫 TC-U8；「腳本風格照 backup.sh」 | 功能 | 已新增 `deploy/platform-upgrade.sh` | 靜態檢查 | 檔案存在且可執行；第一行是 `#!/usr/bin/env bash`；`bash -n` 通過；含 `set -euo pipefail`；程式碼（排除註解）不含 `curl`、`wget`、`scp`、`rsync`、`ssh`、`rm `、`scancel`、`DELETE`、`UPDATE`、`INSERT` | 自動：`tests/platform_upgrade_test.sh` |
| TC-U14 | 決定 2；裁決 7（預設指令是文件上那幾行） | 功能 | 腳本檔案 | 檢查沒設環境變數時的預設指令（讀程式碼） | 預設 pull 是 `git pull`；預設 install 是 `pip install ./platform`；預設重啟是 `systemctl --user restart abf-serve abf-mcp abf-web`，三者與 `docs/OPERATIONS.md` Upgrade 段相同 | 自動：`tests/platform_upgrade_test.sh` |
| TC-U24 | 完成標準第 4 條；範圍「docs/OPERATIONS.md」 | 功能 | 已改文件 | 讀 `docs/OPERATIONS.md` 的 Upgrade 段 | 原本三行（`cd ~/<clone> && git pull`、`~/$VENV/bin/pip install ./platform`、`systemctl --user restart abf-serve abf-mcp abf-web`）一字不少、順序不變；段內多一句提到 `deploy/platform-upgrade.sh`；既有 TC-062（文件裡的路徑都存在）仍綠 | 自動：`tests/platform_upgrade_test.sh`、`tests/hosted_deploy_test.sh` |
| TC-U25 | 範圍「hosted_deploy_test.sh」；維護者「絕不放寬安全網」 | 功能 | 已新增 `deploy/platform-upgrade.sh` | 跑 `bash tests/hosted_deploy_test.sh` | 全綠；既有 TC-069 確認 `deploy/` 內恰好是原六個檔加 `platform-upgrade.sh`（共七個），沒有其他多出來的檔 | 自動：`tests/hosted_deploy_test.sh` |
| TC-U26 | 維護者「絕不放寬安全網」；完成標準第 3 條 | 功能 | 本分支與 `origin/v3` 都在 | 比對 `tests/hosted_deploy_test.sh` 兩邊的差異 | 差異只有第 283 行 `want_list` 多一項 `$D/platform-upgrade.sh`；其餘斷言一個字都沒動、沒有跳過（無 git 或無 `origin/v3` 時此條 skip，由閱卷改以 `git diff` 核對） | 自動：`tests/platform_upgrade_test.sh` |
| TC-U27 | 計畫「對照組」 | 功能 | 已完成所有改動 | 跑 `bash tests/platform_test.sh` | 與改動前一樣全綠（平台本身不受影響） | 自動：`tests/platform_test.sh` |
| TC-U28 | 範圍「不准碰 platform/」；「不做」第 1 條（無新 API、CLI 子命令、資料表欄位、migration） | 不在範圍 | 本分支與 `origin/v3` 都在 | 列出 `platform/`、`deploy/backup.sh`、`deploy/systemd/` 的改動 | 沒有任何改動（沒有新 `agents` 子命令、沒有 migration） | 自動：`tests/platform_upgrade_test.sh`（用 `git diff --name-only origin/v3...HEAD`；無 git 或無 `origin/v3` 則 skip，由閱卷核對） |
| TC-U30 | 「不做」第 3 條（不掛進 systemd 或排程） | 不在範圍 | 已新增腳本 | 跑既有 `bash tests/hosted_deploy_test.sh` 的 TC-083；另搜 `deploy/` | `deploy/systemd/` 仍只有三個 `.service.in`；全 repo 沒有新增 `*.service`、`*.timer`；腳本沒有被任何單元或排程檔引用 | 自動：`tests/hosted_deploy_test.sh` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-U34 | 第 11 條（腳本從 `${BASH_SOURCE[0]}` 定位，不靠 `pwd`） | 功能 | 情境同 TC-U1；先 `cd` 到一個不相干的暫存資料夾 | 用腳本的絕對路徑執行 | 結束碼 0；輸出含 `2 agents reconnected`（不受目前所在資料夾影響）；程式碼不用 `pwd` 找檔 | 自動：`tests/platform_upgrade_test.sh` |
| TC-U35 | 第 13 條（不能悄悄失敗） | 例外 | 分別重現下列失敗：代理人沒重連（TC-U2）、被拒（TC-U3）、重啟指令失敗（TC-U6）、pull 失敗（TC-U11）、install 失敗（TC-U12）、未知選項（TC-U17） | 每種跑一次，收集標準輸出與標準錯誤 | 每一種都結束碼非 0，且輸出非空、是白話句子（不是空白退出） | 自動：`tests/platform_upgrade_test.sh` |

<!--
專長守則（backend）對照：動作層單一入口 → TC-U23；寫入需確認 → 腳本不寫入，TC-U22；擁有者規則 → 本腳本是本機操作員終端（owner=None 看全部，同 `list_agents` 既有行為），無跨使用者面，不另出題；錯誤訊息 → TC-U16、TC-U35；密鑰不外洩 → TC-U9；migration → 不需要（TC-U28、TC-U22）。
-->
