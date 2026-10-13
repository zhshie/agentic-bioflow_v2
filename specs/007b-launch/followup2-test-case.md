# 測試案例：007b 後續修正 2（第一次真國網驗收 TC-049 發現：unforward 說已取消，forward 其實還開著）

**規格**：`specs/007b-launch/spec.md`（FR-005）、`plan.md:61`、`docs/PLATFORM.md:337`　**計畫**：`specs/007b-launch/followup2-plan.md`　**總覽**：`followup2-test-case-overview.md`

類型：**功能**（該做到的事）、**例外**（出錯或不該發生的事怎麼反應）、**防止退步**（和 main 比對）、**不在範圍**（確認沒做）。
名詞沿用 `test-case.md`（假站台、假平台、假 ssh）。新增：

- **維護者的真實觀察**（2026-10-13 21:07，真 OpenSSH 8.9p1、WSL Ubuntu 22.04、站台 lgn304）：
  - 以 `ssh -O forward -R 127.0.0.1:0:127.0.0.1:8787` 開的 forward，sshd 選了 41179。
  - `abf-station unforward` 印「reverse forward cancelled and its records removed」、結束碼 0，但站台上 `ss -ltn` 仍看到 `127.0.0.1:41179 LISTEN`。
  - 用實際 port 取消：`ssh -O cancel -R 127.0.0.1:41179:127.0.0.1:8787` → stderr 兩行「mux_client_forward: forwarding request failed: port not forwarded」與「muxclient: master cancel forward request failed」，**結束碼 0**。
  - 用 port 0 取消：`ssh -O cancel -R 127.0.0.1:0:127.0.0.1:8787` → 結束碼 0，`ss` 裡的 port 消失。
- **仿真假 ssh**：測試用的假 ssh 要照上面的真實行為運作。
  - `-O forward` 時記下收到的 `-R` 規格與配到的 port（規格的 port 欄是 0 就配 41234、41235…，否則用規格自己的 port）。
  - `-O cancel` **只有**規格與某一筆已記錄的規格逐字相同時才成功（靜默、結束碼 0，並把該筆從「聽著的 port」移除）。否則寫出上面那兩行 stderr，結束碼仍是 0。
  - 另提供開關：`cancel_refuse_once`（下一次 cancel 不管規格對不對都被拒絕一次）、`cancel_error`（cancel 以 255 結束並寫 stderr「Control socket connect: No such file or directory」）。
  - 假 ssh 對外的其餘行為（`-O check` 的輸出與 `master_pid`、`fwd_fail`、`ssh_drop_after`、41234 起算）一律不變。
  - 測試用「聽著的 port 清單」（假 ssh 的狀態檔）判斷 forward 是否真的結束，**不是**看 `ssh.log` 有沒有出現 cancel。
- **舊格式紀錄**：目前程式寫的 `forward_state`，只有 `master_pid=` 與 `local_port=` 兩行。
- 「用開啟時的規格取消」＝取消用的 `-R` 與 `--forward` 當初給的 `-R 127.0.0.1:0:127.0.0.1:<本機port>` 逐字相同。

**絕不使用 `~/abf-station-test/`、不使用 port 8787 的真平台、不連國網。** 本檔所說的 8787 只是假站台上 `--forward` 的參數。

## 功能

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-U2-01 | 維護者的例子：unforward 真的結束 forward | 功能 | 假站台，`on_site.sh --forward 8787` 已成功（假 ssh 配到 41234，聽著的清單有 41234） | `on_site.sh --unforward` | 結束碼 0；stdout 是「reverse forward cancelled and its records removed」；送給假 ssh 的 `-O cancel` 恰一次且其 `-R` 是 `127.0.0.1:0:127.0.0.1:8787`；**聽著的清單為空**；`forward_port`、`forward_state` 都不存在；之後 `--check-forward` 結束碼 1 | 自動：`test_station_channel.py`（改正後的 `test_tc038_unforward…`） |
| TC-U2-02 | 開 forward 時把取消需要的東西記下來 | 功能 | 假站台 | `on_site.sh --forward 8787` | `forward_state` 仍有 `master_pid=` 與 `local_port=8787` 兩行（舊讀法不壞）；並記有取消所需的規格或旗標（欄位名稱由執行者定，但必須能由它重建 `127.0.0.1:0:127.0.0.1:8787`）；`forward_state` 與 `forward_port` 權限仍為 0600；不含任何 token 或憑證；`--check-forward` 仍印 41234 | 自動 |
| TC-U2-03 | 不同的本機 port 也一樣 | 功能 | 假站台 | `--forward 9100` 後 `--unforward` | 取消用的 `-R` 是 `127.0.0.1:0:127.0.0.1:9100`；聽著的清單為空；紀錄已移除；結束碼 0 | 自動 |
| TC-U2-04 | 端到端：`abf-station unforward` | 功能 | 一次 launch 完成（站台有 `_relay/forward_port` 與 `forward_instance`，假 ssh 聽著 41234） | `python -m abf_station unforward --deployment <root>` | 結束碼 0；輸出含「reverse forward cancelled and its records removed」與「the copy on the site (…) is removed」；聽著的清單為空；本機與站台上的 `forward_port`、`forward_instance` 都不存在 | 自動：`test_tc038_abf_station_unforward…` 加強 |
| TC-U2-05 | 舊格式紀錄仍能取消 | 功能 | `forward_port` 內容 41234、`forward_state` 只有 `master_pid=<目前>` 與 `local_port=8787`（舊程式寫的），假 ssh 的 41234 是用 port 0 規格開的 | `--unforward` | 退回用 port 0 加記錄的本機 port 取消（`-R 127.0.0.1:0:127.0.0.1:8787`）；聽著的清單為空；紀錄移除；結束碼 0 | 自動 |
| TC-U2-06 | 仿真假 ssh 本身重現維護者的觀察 | 功能 | 假站台，forward 已開（41234） | 直接對假 ssh 執行：(a) `-O cancel -R 127.0.0.1:41234:127.0.0.1:8787`；(b) `-O cancel -R 127.0.0.1:0:127.0.0.1:8787` | (a) stderr 恰含「mux_client_forward: forwarding request failed: port not forwarded」與「muxclient: master cancel forward request failed」，結束碼 **0**，41234 仍在聽。(b) 靜默、結束碼 0，41234 不再聽。(c) 在 main 的 `on_site.sh` 上跑 TC-U2-01，**必須失敗**（證明新測試真的能抓到原本的錯）；執行者把 main 上的失敗輸出記進執行紀錄 | 自動＋執行紀錄 |

## 例外

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-U2-10 | 維護者的例子：cancel 被拒絕要講出來 | 例外 | forward 已開（41234，用 port 0 開的），但取消用的規格對不上（把 `forward_state` 的本機 port 改成 9999，重現「用錯規格」） | `--unforward` | 結束碼**非 0**；stderr 白話說明 forward 還開著、並寫出 port 41234（以及怎麼處理）；stdout **不含**「cancelled」「records removed」；`forward_port` 與 `forward_state` **都還在、內容逐位元組不變**；聽著的清單仍有 41234；`--check-forward` 仍印 41234 | 自動 |
| TC-U2-11 | 失敗之後可以重試 | 例外 | 同 TC-U2-10 的起點，改用 `cancel_refuse_once`（紀錄是對的，只有第一次被拒絕） | 連跑兩次 `--unforward` | 第一次：非 0、紀錄保留、forward 仍開。第二次：結束碼 0、聽著的清單為空、紀錄移除 | 自動 |
| TC-U2-12 | `abf-station unforward` 要顯示失敗訊息並以非 0 結束 | 例外 | 一次 launch 完成後，用 `cancel_refuse_once` 讓取消被拒絕 | `python -m abf_station unforward --deployment <root>` | 結束碼**非 0**；輸出（stdout 與 stderr 合併）含 on_site 的失敗訊息與 port 41234、說明 forward 還開著；**不含**「cancelled and its records removed」；本機與**站台上** `_relay/forward_port`、`forward_instance` 都保留（站台上沒有任何 `rm`，看破壞性紀錄）；聽著的清單仍有 41234。再跑一次（不再被拒絕）則成功並清掉所有紀錄 | 自動 |
| TC-U2-13 | 兩個輸出都要看得到 | 例外 | `cmd_unforward` 收到的腳本回應 stdout 與 stderr 都有字（以替身 `Site.call` 回傳） | 呼叫 `cmd_unforward` | stdout 與 stderr 的文字**都**印出，不是「stdout 有字就丟掉 stderr」；回傳值依腳本結束碼（非 0 就非 0） | 自動：單元測試 |
| TC-U2-14 | 共用連線已經不在 | 例外 | forward 已開，之後 `ssh_mode=nomaster` | `--unforward` | 不送 `-O cancel`（沒有連線可送）；紀錄移除；結束碼 0；訊息與 main 相同（forward 已隨連線結束）；不印失敗訊息 | 自動 |
| TC-U2-15 | 連線被換掉過：不能讓紀錄永遠清不掉 | 例外 | forward 在舊連線上開的，之後連線重開（`master_pid` 改成 9999，與 `forward_state` 的不同）；新連線上沒有這個 forward | `--unforward` | 不送會被正當拒絕的 cancel，或送了也不視為失敗；紀錄移除；結束碼 0；訊息說明這個 forward 已隨先前的連線結束。**不得**留下一個永遠取消不掉的紀錄，也不得把「連線換過」當成「還開著」 | 自動 |
| TC-U2-16 | cancel 本身出錯（非 0 結束） | 例外 | 假 ssh 設 `cancel_error`（255＋「Control socket connect…」） | `--unforward` | 結束碼非 0；訊息寫出 port 並說 forward 可能還開著；紀錄保留；stdout 不含「cancelled」 | 自動 |
| TC-U2-17 | 兩行拒絕訊息只出現一行也算失敗 | 例外 | 假 ssh 的拒絕分別只寫 (a) 「mux_client_forward: forwarding request failed: port not forwarded」；(b) 只寫「muxclient: master cancel forward request failed」，結束碼 0 | `--unforward` | 兩種都視為失敗：非 0、紀錄保留、訊息含 port | 自動（參數化） |
| TC-U2-18 | 無關的 stderr 不能誤判成失敗 | 例外 | 取消成功，但假 ssh 同時在 stderr 寫一行無關警告（例如「Warning: Permanently added 'lgn304' (ED25519) to the list of known hosts.」） | `--unforward` | 視為成功：結束碼 0、紀錄移除、stdout 為成功訊息 | 自動 |
| TC-U2-19 | 根本沒有紀錄 | 例外 | 沒有 `forward_port` 也沒有 `forward_state` | `--unforward` | 不送 cancel；結束碼 0；訊息與 main 相同（沒有東西可取消）；不建立任何檔案 | 自動 |
| TC-U2-20 | 紀錄不完整時不謊報 | 例外 | 只有 `forward_port`（41234），`forward_state` 不見了或沒有 `local_port` | `--unforward` | 不宣稱「cancelled」；stderr 說明紀錄不完整、無法確認取消、forward 可能還開著，並寫出 port 41234；`forward_port` 保留；結束碼非 0 | 自動 |

## 防止退步

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-U2-30 | 成功路徑一個字都不變 | 防止退步 | 假站台，forward 已開且取消會成功 | 在 main 與分支各跑 `--unforward` | stdout 逐位元組相同（「reverse forward cancelled and its records removed」）、stderr 為空、結束碼 0 | 自動：與 main 比對 |
| TC-U2-31 | `--forward` 沒變 | 防止退步 | 假站台 | `--forward 8787` | 送出的仍是 `-O forward … -R 127.0.0.1:0:127.0.0.1:8787`（恰一次，不含 `0.0.0.0` 或 `-R *`）；stdout 是 `41234`；`forward_port` 內容與權限同 main；`--forward notaport`、`0`、`70000` 仍被拒絕 | 自動：既有 `test_tc038_forward…` 不改而通過 |
| TC-U2-32 | `--check-forward` 沒變 | 防止退步 | 同既有測試 | 無紀錄、剛開、連線被換、無連線四種 | 結束碼與訊息同 main（1／0 加 41234／1 加「another connection」／2 加「needs-human reason=no-master」）。**用舊格式 `forward_state`（無新欄位）也一樣** | 自動：既有測試不改而通過＋舊格式一例 |
| TC-U2-33 | 每次輪詢不多開 sshd 連線 | 防止退步 | 假站台，記錄所有 ssh 呼叫 | 執行 `--forward`、`--check-forward`，以及一次 launch（含預檢） | 這些呼叫產生的 `ssh.log` 中，`-O check`／`-O forward` 的次數與 main 相同，且**沒有任何新增的非 `-O` ssh 連線**。`--unforward` 最多比 main 多一次非 `-O` 連線（若執行者選擇用站台上 `ss -ltn` 查證），並且那一次只讀 | 自動：與 main 比對 |
| TC-U2-34 | 舊的錯誤斷言要改正、不是刪掉 | 防止退步 | 本分支對 main 的 diff | 檢查 `test_tc038_unforward_cancels_the_forward_and_removes_the_records` | 該測試仍在、名稱仍在；原本斷言 `-R 127.0.0.1:41234:127.0.0.1:8787` 的那一行**被改成**斷言 `127.0.0.1:0:127.0.0.1:8787`（並加上聽著的清單為空）；其餘斷言（紀錄移除、`--check-forward` 結束碼 1、結束碼 0）全留。`test_station_channel.py` 的測試數量不減少，沒有 skip，沒有別的斷言被放寬 | 手動：驗收者看 diff |
| TC-U2-35 | 假 ssh 的其他行為不變 | 防止退步 | 本分支對 main 的 `station_harness.py` diff | 跑 `test_station_channel.py`、`test_station_launch.py`、`test_station_fakeplatform.py` 的全部測試 | 全部維持通過、數量不減；`-O check` 的輸出、`master_pid`、`fwd_fail`（255＋「mux_client_forward: forwarding request failed」）、port 41234 起算、`ssh_drop_after` 計數（tc017 的 9 個參數）都不受影響 | 自動 |

## 不在範圍

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-U2-40 | 沒碰 `plugin/`、`.github/`、relay | 不在範圍 | 本分支對 main 的 diff | 檢查 | `plugin/`、`.github/`、`scripts/nf_relay.py` 沒有改動；沒有新增 relay 網域 | 手動：驗收者用 git diff |
| TC-U2-41 | 沒有做 009、自動重試、自動重開 forward | 不在範圍 | 同上 | 檢查 | 沒有網頁確認頁或 MCP 寫入工具；沒有「失敗就自動重試 cancel」「自動重開 forward」的程式。重試必須由人再執行一次 `abf-station unforward` | 手動＋TC-U2-11 |
| TC-U2-42 | 沒有常駐程式或迴圈 | 不在範圍 | `on_site.sh` 的 007b 區段 | 跑既有 `test_tc038_on_site_gained_no_background_process_and_no_loop` | 仍通過（區段內沒有 `nohup`、`setsid`、`while`、`until`、`sleep`、背景 `&`）。查證若要重試也只能手動再跑一次，不能在腳本內輪詢 | 自動：既有測試不改 |
| TC-U2-43 | 沒有任何東西自動取消 forward | 不在範圍 | 一次 launch 與一次 `cancel` 完成 | 看 `ssh.log` | run 結束或取消時沒有 `-O cancel`（既有 `test_tc038_tc012_…` 的那行斷言仍在） | 自動：既有測試不改 |
| TC-U2-44 | 沒碰正在跑的驗收環境 | 不在範圍 | 全部新測試與執行紀錄 | 檢查 | 只用暫存資料夾與假站台；不讀寫 `~/abf-station-test/`；不用真 port 8787；不連 NCHC | 自動：掃描＋手動：看紀錄 |

## 憲法與安全網

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-U2-50 | 原則 13／VI：失敗不能安靜 | 例外 | 任何 cancel 被拒絕或出錯（TC-U2-10、16、17、20） | `--unforward` 或 `abf-station unforward` | 使用者在終端機上看得到一句白話：forward 還開著、port 是哪個、紀錄還在。不是只有 exit code，也不是只寫進 log | 自動（上述案例涵蓋） |
| TC-U2-51 | 安全網：不刪使用者資料 | 例外 | 站台有 `rawdata/s1.fq`、`results`、`analysis`，破壞性紀錄開啟 | `abf-station unforward`（成功與失敗各一次） | 破壞性紀錄中除了 `_relay/forward_port`、`_relay/forward_instance` 兩個檔案的 `rm -f` 外沒有別的刪除；失敗那次完全沒有 `rm`；`rawdata`、`results`、`analysis`、`cache` 原封不動 | 自動 |
| TC-U2-52 | 安全網：憑證與權限 | 例外 | 新寫入的 `forward_state`／`forward_port` | 檢查內容與權限 | 權限 0600；內容只有 port、pid、規格，沒有 token、帳號、金鑰；沒有任何新檔寫進 git 追蹤範圍 | 自動 |
| TC-U2-53 | 原則 8：實測結果寫進 PITFALLS | 功能 | 本分支的 diff | 讀 `docs/PITFALLS.md` | 有一則新條目：`ssh -O cancel` 比對的是開啟時給的規格（port 0），用實際 port 會被拒絕；被拒絕時結束碼仍是 0、只有 stderr 兩行；日期 2026-10-13、OpenSSH 8.9p1。`docs/PLATFORM.md` 的 unforward 段落如有改，只能是補充「失敗時的樣子」，不能弱化原有句子。`tests/` 中檢查 PITFALLS 對應的程序（TESTING.md P2）仍通過 | 手動：驗收者看 diff |
| TC-U2-54 | 真國網重驗 TC-049 | 功能 | 修好的版本，維護者在 NCHC 上做；**不是執行者做** | 依 `docs/TESTING.md` 步驟：`--forward`、`ss -ltn` 看到 port、`abf-station unforward`、再 `ss -ltn` | `ss -ltn` 上該 port 消失，且 `abf-station unforward` 印的是成功訊息、結束碼 0。再做一次「連線中途被換掉再 unforward」，確認不卡死。結果記進 `docs/TESTING.md` 的驗收紀錄 | 手動：維護者 |
