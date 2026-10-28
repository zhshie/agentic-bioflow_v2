# 測試案例：preflight-ssh-fold（reach=ssh 時 preflight 把三次站台呼叫併成一次）

**規格**：`specs/preflight-ssh-fold/plan.md`（本任務沒有獨立 spec.md；來源是 issue #13 第 3 項與計畫裡的「裁決」）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## 計數規則（所有「呼叫次數」都照這一條，對應裁決第 7 條）

測試用的假 ssh 每被呼叫一次就在 `ssh.calls` 記一行。**「開 session 的呼叫數」＝ `ssh.calls` 中不含 `-O check` 的行數**（`ssh -O check` 只是問連線還活著沒有，不算開 session，見 `docs/PITFALLS.md` 16e）。測試裡必須明寫這個排除條件。ssh 部署下一次 preflight 的呼叫：`--check-reach` 開 1 個 session（內容是 `true`），改前三件站台檢查各開 1 個（共 4），改後三件合開 1 個（共 2）。

## User Story 1 — reach=ssh：三件站台檢查併成一次呼叫，使用者看到的字一個都不變（優先度 P1）

維護者原話（issue #13 第 3 項）：「Per-check SSH hops don't batch … each is a separate SSH round trip … more hops is also more exposure」「consider a single `on_site.sh --script` call that runs a small composed script doing all of them」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 T1；issue #13 第 3 項「single `on_site.sh --script` call」「more hops is also more exposure」 | 功能 | `reach: ssh`，假 ssh（`ON_SITE_SSH_BIN`），egress／agent／資源契約三項都是好的 | 跑 `scripts/preflight.sh` | 開 session 的呼叫數恰為 2：第 1 次是 `--check-reach`（內容 `true`），第 2 次是同時帶 `preflight_site.sh` 的合併呼叫。同一個測試在 base 上跑出 4（紅燈輸出貼進帳本） | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-002 | 計畫 T2 | 功能 | 同 TC-001 | 跑 `scripts/preflight.sh` | 輸出有 `OK` 開頭的 `egress`、`agent`、`resources` 各一行；結束碼 0 | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-003 | 計畫 T3 | 例外 | `reach: ssh`，只有 egress 壞（旗標檔控制） | 跑 `scripts/preflight.sh` | 有 `FAIL` 開頭的 `egress` 行，內容含 `egress_ctl.sh` 與 ` start`；同時 `agent`、`resources` 仍各有一行 `OK`（前一項壞不擋後面）；結束碼 1 | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-004 | 計畫 T4 | 例外 | `reach: ssh`，只有 agent 壞 | 跑 `scripts/preflight.sh` | 有 `FAIL` 開頭的 `agent` 行，內容含 `not running` 與 `agent_ctl.sh` 與 ` start`；`egress`、`resources` 仍是 `OK`；結束碼 1 | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-005 | 計畫 T5 | 例外 | `reach: ssh`，只有資源契約壞；假契約腳本輸出多行，第一行為已知字串 | 跑 `scripts/preflight.sh` | 有 `FAIL` 開頭的 `resources` 行，且該行文字等於假契約腳本輸出的第一行；`egress`、`agent` 仍是 `OK`；結束碼 1 | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-006 | 計畫 T6 | 例外 | `reach: ssh`，egress 輸出含 `WARNING` 但退出碼 0 | 跑 `scripts/preflight.sh` | 同時有 `OK` 開頭的 `egress` 行**和** `FAIL` 開頭的 `egress-host` 行（內容含 `started somewhere else`）；結束碼 1 | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-007 | 計畫 T7 | 例外 | `reach: ssh`，三項全壞 | 跑 `scripts/preflight.sh` | 三行 `FAIL`（`egress`、`agent`、`resources`），各自是固定文字；結束碼 1；開 session 的呼叫數仍恰為 2 | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-008 | 計畫 T9；既有 `tests/preflight_reach_test.sh` 斷言 | 例外 | `reach: ssh`，假 ssh 對 `-O check` 回 255（連線已斷） | 跑 `scripts/preflight.sh` | 輸出有 `FAIL` 開頭的 `reach` 行；輸出沒有 `egress`、`agent`、`resources` 任何一行；開 session 的呼叫數為 0（整份 `ssh.calls` 只有 1 行，且是那行 `-O check`）；結束碼非 0 | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-009 | 計畫 T10；作法第 3 點；裁決第 5 條 | 例外 | `reach: ssh`，`--check-reach` 通過；合併呼叫的假 ssh 先印一行已知錯誤文字再 exit 255，輸出裡沒有任何分段標記 | 跑 `scripts/preflight.sh` | 三行 `FAIL`：`egress` 與 `agent` 是各自的固定文字，`resources` 那行是整份輸出的第一行（即那行已知錯誤文字）；結束碼 1；開 session 的呼叫數恰為 2（沒有重試，也沒有退回舊的三次呼叫） | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-010 | 計畫 T11；環境事實（`on_site.sh` 對 `egress_ctl.sh` 有特例） | 功能 | 同一個站台狀態（假 egress 狀態固定） | 一次用 `on_site.sh --script scripts/egress_ctl.sh status` 取得 egress 輸出；一次用 `preflight_site.sh` 取得 egress 段原文 | 兩份 egress 輸出逐字相同 | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-011 | 作法第 1 點；裁決第 2 條 | 功能 | 在站台端（本機模擬）直接跑 `scripts/preflight_site.sh`，不帶參數；假的三個兄弟腳本讓第一個失敗、其餘成功 | 跑 `preflight_site.sh` | 依序出現 egress、agent、resources 三段，每段都是 `@@preflight-begin <名>`、原文、`@@preflight-end <名> rc=<退出碼>`，且 rc 與各假腳本實際退出碼一致；第一段失敗後第二、三段照跑；腳本自己 exit 0 | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-012 | 作法第 1 點「標記必須能被本機機械式解析、且不會與腳本輸出內容混淆」 | 功能 | `reach: ssh`；假 egress 的輸出剛好含一行看起來像標記的文字（例如 `@@preflight-end agent rc=1`） | 跑 `scripts/preflight.sh` | `agent` 的判斷仍以真正的 agent 段為準（agent 好就是 `OK`）；`egress` 行完整顯示那行文字；沒有任何一項因為輸出內容而被誤判 | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-013 | 裁決第 2 條「逐字相同」；目標「使用者可見的輸出與結束碼逐字不變」 | 功能 | 同一組假站台狀態，涵蓋 TC-002 至 TC-007 的情境，其中 egress 輸出是多行 | 在 base 與修改後各跑一次 `scripts/preflight.sh`，比較 stdout、stderr、結束碼 | 每個情境的 stdout、stderr、結束碼，base 與修改後逐字相同（`diff` 為空；多行輸出的換行與結尾都一樣）。例外只有 TC-009 那條傳輸失敗路徑 | 自動：`tests/preflight_ssh_fold_test.sh`（帳本貼 base 對照 diff） |
| TC-029 | 作法第 3 點「標記不全」 | 例外 | `reach: ssh`，合併呼叫的輸出只有 egress 段完整、後面被截斷（缺 agent、resources 的標記），exit 255 | 跑 `scripts/preflight.sh` | 照計畫字面：三項都當失敗，各用固定文字（`resources` 取整份輸出第一行）；結束碼 1；開 session 的呼叫數恰為 2 | 自動：`tests/preflight_ssh_fold_test.sh` |

## User Story 2 — 不走 ssh 的部署完全不受影響（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 計畫 T8；裁決第 3 條 | 功能 | `reach: local`，`LAB_RUNS_DIR` 已設，假 ssh 在位 | 在 base 與修改後各跑一次 `scripts/preflight.sh` | 修改後 `ssh.calls` 不存在或 0 行；stdout、stderr、結束碼與 base 逐字相同（`diff` 為空，貼進帳本） | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-015 | 完成標準「`REACH=none` 逐字相同」 | 功能 | `reach: none`，假 ssh 在位 | 在 base 與修改後各跑一次 `scripts/preflight.sh` | 沒有 `egress`、`agent`、`resources` 行；開 ssh 的次數為 0；stdout、stderr、結束碼與 base 逐字相同 | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-016 | 「不做：不把 REACH=local 也改成走包裝腳本」；作法第 2 點「local 保持三次獨立呼叫」 | 不在範圍 | `reach: local`，設 `ON_SITE_DRY_RUN=1`（`on_site.sh` 只印它會做什麼，不執行） | 跑 `scripts/preflight.sh` | 輸出裡出現三次各自獨立的呼叫描述（`script egress_ctl.sh status`、`script agent_ctl.sh status`、`script check_resource_contract.sh`）；整份輸出沒有 `preflight_site.sh` | 自動：`tests/preflight_ssh_fold_test.sh` |

## User Story 3 — 範圍、守門與紀錄（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 「不做：不併 `--check-reach`」；查證結果第 4 點 | 不在範圍 | `reach: ssh`，三項全綠 | 跑 `scripts/preflight.sh`，看 `ssh.calls` 的順序與內容 | `--check-reach` 仍是獨立的第一次開 session 呼叫（內容 `true`），合併呼叫是另一次、排在它後面；兩者不在同一次呼叫裡 | 自動：`tests/preflight_ssh_fold_test.sh` |
| TC-018 | 範圍：檔案；「不准動」清單；「不新增設定鍵」 | 不在範圍 | 實作完成後 | 閱卷者跑 `git diff --name-only <base>...HEAD` 並檢視 `scripts/preflight.sh` 的差異 | 變動的檔案只有：`scripts/preflight_site.sh`、`scripts/preflight.sh`（只動原 `:110-123` 的站台區塊）、`tests/preflight_ssh_fold_test.sh`、`docs/PITFALLS.md`、`specs/preflight-ssh-fold/ledger.md`；「不准動」清單（`on_site.sh`、`site_report.sh`、`egress_ctl.sh`、`agent_ctl.sh`、`check_resource_contract.sh`、其他測試、`hooks/`、`skills/`、`platform/**`、其他 `docs/`）零命中；沒有新增設定鍵 | 手動：閱卷者以 `git diff` 核對 |
| TC-019 | 完成標準第 2 條；T12 | 不在範圍 | 實作完成後 | 跑 `git diff --stat <base>... -- tests/preflight_reach_test.sh tests/on_site_test.sh tests/site_report_test.sh tests/credentials_stay_in_settings_test.sh tests/no_second_run_state_test.sh` | 輸出為空（這五支既有測試零修改，沒有放寬斷言、沒有改預期值） | 手動：閱卷者以 `git diff` 核對 |
| TC-020 | 完成標準第 1 條；T12 | 功能 | 實作完成，在 WSL／Linux | 跑 `tests/preflight_ssh_fold_test.sh`（T1–T12 對應的全部案例）與 `tests/run_all.sh` | 新測試全綠；整個 `tests/run_all.sh` 全綠（含上列五支既有測試） | 自動：`tests/run_all.sh` |
| TC-021 | 範圍：`docs/PITFALLS.md` 檔尾新增一條；作法第 3、4 點 | 功能 | 實作完成 | 閱卷者讀 `docs/PITFALLS.md` 檔尾 | 有一條新條目，寫明：為什麼 ssh 下三件事併成一次、分段標記的格式、傳輸失敗時的行為（三項都報失敗、不重試），以及 `ON_SITE_TIMEOUT` 對這次呼叫是「三件事合計一個時鐘」 | 手動：閱卷者讀檔核對 |
| TC-022 | 失敗先行測試末段；範圍：`ledger.md` | 功能 | 實作完成 | 閱卷者讀 `specs/preflight-ssh-fold/ledger.md` | 帳本記有：假 ssh 的搭法選擇（解 tar 或直接 cd）、在 base 跑新測試的紅綠分佈（TC-001、TC-007、TC-009、TC-010 紅，TC-002 至 TC-006、TC-008、TC-014 綠）、TC-013／TC-014／TC-015 的 base 對照 diff | 手動：閱卷者讀檔核對 |
| TC-023 | 完成標準「沒有真的 ssh／tw／Seqera 呼叫」 | 不在範圍 | 實作完成 | 閱卷者讀新測試與其設定 | 新測試的 ssh 一律走 `ON_SITE_SSH_BIN` 假檔、`tw` 一律走 `TW_BIN` 假檔，不碰 `~/.config/agentic-bioflow` 的真實部署，也沒有任何對真實站台或 Seqera 的連線 | 手動：閱卷者讀測試核對 |
| TC-024 | 完成標準「手動驗收（記帳本，不擋合併）」 | 功能 | 一個真的 ssh 部署（例如國網 Taiwania） | 維護者或指定人員在真 ssh 部署跑 `scripts/preflight.sh` | 輸出與改前逐字相同，且站台開 session 少 2 次；結果記進 `ledger.md`（不擋合併） | 手動：記入帳本 |

## 憲法與安全網

本任務改動站台呼叫（`scripts/preflight.sh`、新增站台端腳本），觸及下列條款；安全網（hooks、閘門）不在改動範圍內，不另列。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 第 3 條（不寫死路徑） | 功能 | 實作完成 | 跑 `bash tests/no_hardcoded_paths.sh` | 通過；新腳本與新測試沒有個人路徑或叢集路徑 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-026 | 第 4 條（指令層不點名排程器／佇列／中繼） | 功能 | 實作完成 | 跑 `bash tests/command_layer_is_site_neutral.sh` | 通過 | 自動：`tests/command_layer_is_site_neutral.sh` |
| TC-027 | 第 8 條（先量測再宣稱，結果進 PITFALLS） | 功能 | 實作完成 | 閱卷者比對 `docs/PITFALLS.md` 新條目與帳本 | 新條目的每項說法（兩種呼叫下 egress 輸出相同、開 session 次數 4 變 2）都對得上帳本或測試裡實際量到的結果，沒有未量測的斷言 | 手動：閱卷者讀檔核對 |
| TC-028 | 第 11 條（腳本自己從 `${BASH_SOURCE[0]}` 找位置，不靠 `pwd`） | 功能 | `preflight_site.sh` 與三個兄弟腳本在站台端被解到一個暫存目錄 | 從別的工作目錄執行 `preflight_site.sh`，並跑 `bash tests/on_site_test.sh` | 三段照常跑完、標記齊全；`tests/on_site_test.sh` 仍全綠 | 自動：`tests/preflight_ssh_fold_test.sh`、`tests/on_site_test.sh` |
