# 測試案例：桌機（WSL）上的平台開機自動啟動、當掉自動重啟

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
這個功能目錄沒有 spec.md，計畫 plan.md 是規格；「計畫 §n」指 plan.md 的第 n 小節（1 看守腳本、2 範例檔、3 Windows 安裝腳本、4 文件）。
測試旋鈕（狀態資料夾、間隔、等待秒數、換檔大小）的名字由執行者決定並寫在 abf-supervise.sh 檔頭；
下列案例只說「檔頭記載的旋鈕」，不綁名字。所有自動測試都指向暫存資料夾（HOME 指到暫存），不碰真的平台、不碰使用者家目錄。
-->

**規格**：`specs/platform-autostart/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

自動測試檔：`tests/platform_autostart_test.sh`（一個檔，每條 TC 的標籤用 TC 編號）。「假行程」指測試自己寫的短命 `sh -c` 或會記錄自己被啟動幾次的小腳本。

**維護者的五個例子**（驗收以此為準，下表用他的原話）：

1. 「我把電腦重開機、登入，什麼都不做，過一兩分鐘打開網站，平台是好的。」→ TC-001、TC-013
2. 「平台當掉（我把其中一個行程砍掉），幾秒後它自己回來，其他的沒受影響。」→ TC-020、TC-034
3. 「我想知道現在哪些在跑，下一個指令就看得到。」→ TC-040、TC-047
4. 「它不會同時跑兩份。」→ TC-050、TC-055
5. 「裡面沒有我的權杖。」→ TC-060、TC-073、TC-077

## US1 — 重開機登入後，平台自己起來（例 1；計畫 §1、§3）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 例 1：「我把電腦重開機、登入，什麼都不做，過一兩分鐘打開網站，平台是好的。」（合併前只能驗到「從乾淨環境起得來」）；計畫 §1 | 功能 | 清單檔有三行假行程（各自長時間睡著、啟動時把自己的行程編號寫進一個檔）；用 `env -i` 清空環境，只留 HOME（指暫存）與最基本的 PATH | 執行 `abf-supervise.sh --list <清單>`（模擬登入工作的方式，沒有終端、沒有互動） | 幾秒內三個假行程都在跑；`--status` 三個都顯示「在跑」；沒有要求任何輸入 | 自動：`tests/platform_autostart_test.sh` |
| TC-002 | 計畫 §3：登入時執行、名稱 `abf-platform-autostart` | 功能 | 讀 `deploy/wsl/install-autostart.ps1` | 檢查檔案內容 | 工作名稱是 `abf-platform-autostart`；觸發條件是「使用者登入時」且限定目前使用者；不是開機觸發、不是排程時間 | 自動：`tests/platform_autostart_test.sh`（靜態檢查） |
| TC-003 | 計畫 §3：動作是 `wsl.exe -d <distro> -u <user> --exec <看守腳本路徑>` | 功能 | 同上 | 檢查動作字串的組成；若環境有 `powershell.exe`，另以三個參數（`-Distro` `-User` `-Script`）跑預設模式看實際印出的動作 | 動作程式是 `wsl.exe`；參數依序含 `-d <給的 distro>`、`-u <給的使用者>`、`--exec`、`<給的腳本路徑>`；沒有 `bash -c`、沒有 `sudo`、沒有 `-e` 與 shell 字串拼接 | 自動：`tests/platform_autostart_test.sh` |
| TC-004 | 計畫 §3：預設只印不更動（實跑版）；測試章節「有 powershell.exe 可加跑」 | 功能 | 環境有 `powershell.exe`（WSL 互通）；沒有就整條略過並印出略過原因 | 不加 `-Apply` 跑安裝腳本，之後查 `Get-ScheduledTask -TaskName abf-platform-autostart` | 輸出說明「將要做什麼」（工作名稱、動作、觸發條件）且明說「沒有更動」；排程器裡查不到這個工作；沒有 powershell.exe 時印「略過：原因」而不是假裝通過 | 自動：`tests/platform_autostart_test.sh`（無 powershell.exe 時略過） |
| TC-005 | 計畫 §3：預設不更動，加 `-Apply` 才註冊（靜態版） | 功能 | 讀安裝腳本 | 檢查檔案內容 | 註冊工作的指令只出現在 `-Apply` 成立的分支裡；沒有任何不受 `-Apply` 保護的註冊／移除／停用指令；預設分支只印字 | 自動：`tests/platform_autostart_test.sh` |
| TC-006 | 計畫 §3：`-Apply`、`-Remove`；重複 `-Apply` 結果相同 | 功能 | 讀安裝腳本 | 檢查檔案內容 | 兩個開關都存在；`-Apply` 用「已存在就覆蓋／先移除再註冊」的寫法，重複執行不會產生第二個工作、不會報錯；`-Remove` 只動這個名稱的工作 | 自動：`tests/platform_autostart_test.sh` |
| TC-007 | 計畫 §3：`-Remove` | 例外 | 讀安裝腳本；環境有 powershell.exe 時另跑 | 工作不存在時 `-Remove` | 說「本來就沒有這個工作」，結束碼 0，不是錯誤訊息；有 powershell.exe 時實跑一次確認 | 自動：`tests/platform_autostart_test.sh` |
| TC-008 | 計畫 §3：不需要系統管理員權限；需要時說明白並停手，不自行提權 | 例外 | 讀安裝腳本 | 檢查檔案內容 | 不含 `RunAs`、`-Verb RunAs`、`RunLevel Highest`、`Start-Process` 提權用法；工作以一般權限（Limited）註冊；有一個「權限不足」的處理分支，印出白話一句（說權限不夠、要請誰做什麼）並停手 | 自動：`tests/platform_autostart_test.sh` |
| TC-009 | 計畫 §3：失敗時每分鐘重試、不限時間長度；加 P4（電池、單一實例、視窗隱藏） | 功能 | 讀安裝腳本 | 檢查工作設定 | 失敗重試間隔 1 分鐘；重試次數大；執行時間上限為「不限」（零）；電池供電時也啟動且不因換電池而停；已有一份在跑時忽略新的；視窗隱藏 | 自動：`tests/platform_autostart_test.sh` |
| TC-010 | 計畫 §3；PowerShell 5.1 讀無 BOM 的 UTF-8 會把中文讀成亂碼 | 功能 | 讀安裝腳本的原始位元組 | 檢查檔頭 | 檔案以 UTF-8 BOM 開頭，或整個檔案只有 ASCII；兩者必居其一 | 自動：`tests/platform_autostart_test.sh` |
| TC-011 | 計畫 §1：bash 腳本，在 WSL 裡直接執行 | 功能 | 檢查 git 索引與檔案位元組 | `git ls-files -s deploy/wsl/abf-supervise.sh` 與檔頭 | 索引模式 100755（可執行）；第一行是 bash 的 shebang；檔內沒有 CR 字元（Windows 檢出換行會讓 shebang 失效） | 自動：`tests/platform_autostart_test.sh` |
| TC-012 | 計畫「專長守則」：用到 `flock`、`setsid` 前先檢查存在，缺了要說明白並結束 | 例外 | 用只含必要工具、但缺 `flock`（另一次缺 `setsid`，若腳本有用到）的 PATH 目錄 | 啟動看守腳本 | 印白話一句，說缺哪個工具、下一步怎麼裝，結束碼非 0，沒有啟動任何行程，不是靜默退化成沒鎖的模式 | 自動：`tests/platform_autostart_test.sh` |
| TC-013 | 例 1 原話：「我把電腦重開機、登入，什麼都不做，過一兩分鐘打開網站，平台是好的。」 | 功能 | 合併後、與維護者約好時間；已照文件寫好清單、手動起的六個行程已停掉、已 `-Apply` | 電腦重開機，登入 Windows，什麼都不做，過一兩分鐘打開網站 | 網站能開、平台是好的；`--status` 六個都「在跑」 | 手動：`docs/TESTING.md`「platform-autostart」 |
| TC-014 | 計畫 §3：註冊／移除（實跑） | 功能 | 合併後、與維護者約好時間，一般（非系統管理員）的 PowerShell | 先不加 `-Apply` 看輸出；再 `-Apply`；用工作排程器或 `Get-ScheduledTask` 看；再 `-Apply` 一次；再 `-Remove` | 第一步沒更動；`-Apply` 後出現一個 `abf-platform-autostart`；第二次 `-Apply` 仍只有一個；`-Remove` 後消失；全程沒跳出系統管理員提示 | 手動：`docs/TESTING.md`「platform-autostart」 |
| TC-015 | 計畫 §3：`wsl.exe --exec` 持續占著，WSL 不會因為沒人開視窗而被關掉 | 功能 | 已 `-Apply`，登入後不開任何 WSL 視窗 | 登入十分鐘後執行 `--status`（從 WSL 或 `wsl.exe -d <distro> --exec <腳本> --status`） | 看守腳本仍在跑、各行程仍在跑；螢幕上沒有一直開著的黑色視窗 | 手動：`docs/TESTING.md`「platform-autostart」 |

## US2 — 行程當掉，幾秒後自己回來，其他不受影響（例 2；計畫 §1）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 例 2 原話：「平台當掉（我把其中一個行程砍掉），幾秒後它自己回來，其他的沒受影響。」 | 功能 | 看守腳本管三個假行程 a、b、c（各自記下行程編號與被啟動次數），間隔旋鈕調小 | 對 b 送 `kill -9` | 在「間隔底 + 2 秒」內 b 有新的行程編號且在跑；a、c 的行程編號不變、啟動次數仍是 1 | 自動：`tests/platform_autostart_test.sh` |
| TC-021 | 計畫 §1：「任何一個結束（不論結束碼）就重啟」 | 功能 | 假行程 x 啟動後等 1 秒、乾淨地 `exit 0` | 觀察 | x 被再次啟動（啟動次數 ≥ 2）；supervise.log 記到結束碼 0 | 自動：`tests/platform_autostart_test.sh` |
| TC-022 | 計畫 §1：其他行程不受影響（連環崩潰也不拖累別人） | 功能 | a 是「立刻結束」的假行程（進入長間隔），b 是正常行程 | 等 a 的間隔拉長後，對 b 送 `kill -9` | b 在「間隔底 + 2 秒」內回來，不被 a 的長間隔拖慢；a 的重啟不影響 b 的行程編號 | 自動：`tests/platform_autostart_test.sh` |
| TC-023 | 計畫 §1：看守腳本自己的事件寫 `supervise.log`，每行有時間 | 功能 | 一個會當掉一次的假行程 | 跑完一個「啟動、結束、重啟」之後讀 supervise.log | 有「啟動」「結束碼 N」「重啟」「下次間隔 N 秒」的事件行，每一行開頭有日期時間；行程名字出現在行裡 | 自動：`tests/platform_autostart_test.sh` |
| TC-024 | 計畫 §1：連續快速失敗時加倍，不能空轉燒 CPU | 例外 | 假行程「啟動就立刻結束，永遠如此」，旋鈕：底 0.2 秒、頂 1.6 秒、穩定門檻 1 秒 | 跑 6 秒 | 啟動次數不超過 15 次（空轉的話會是幾百次）且至少 3 次；supervise.log 記到的間隔是 0.2→0.4→0.8→1.6，不遞減 | 自動：`tests/platform_autostart_test.sh` |
| TC-025 | 計畫 §1：上限 60 秒（用旋鈕縮小測） | 例外 | 同 TC-024，跑到加倍超過頂 | 讀 supervise.log 的間隔 | 任何一次間隔都不超過頂（1.6 秒）；達到頂之後維持在頂 | 自動：`tests/platform_autostart_test.sh` |
| TC-026 | 計畫 §1：存活滿 30 秒後歸零 | 功能 | 假行程：第一次跑超過穩定門檻（旋鈕 1 秒）才結束；之後每次立刻結束 | 觀察前兩次重啟的間隔 | 存活夠久那次結束後，下一個間隔回到底（0.2 秒），不是延續先前加倍的值 | 自動：`tests/platform_autostart_test.sh` |
| TC-027 | 計畫 §1：預設第一次 2 秒、加倍、上限 60 秒、穩定 30 秒 | 功能 | 不設任何間隔旋鈕，假行程立刻結束 | 跑約 3.5 秒讀 supervise.log；並檢查腳本檔頭記載的預設值 | 前兩個間隔是 2 秒、4 秒；檔頭記載的預設是底 2、頂 60、穩定 30、等待 10 | 自動：`tests/platform_autostart_test.sh` |
| TC-028 | 憲法 VI「什麼都不要悄悄不見」；計畫 §1 | 例外 | 看守腳本在管 a、b；執行中把 a 的執行檔刪掉（或改成不存在的路徑再讓 a 當掉） | 等 a 重啟 | supervise.log 記到「無法啟動 a」及結束碼（例 127）與下次間隔；a 持續以退避重試，不悄悄消失、不讓整個看守腳本結束；b 不受影響 | 自動：`tests/platform_autostart_test.sh` |
| TC-029 | 計畫 §1：收到 SIGTERM，轉給所有子行程，等最多 10 秒，然後自己結束，不再重啟 | 功能 | 三個守規矩的假行程在跑 | 對看守腳本送 `kill -TERM` | 三個假行程都結束；看守腳本結束碼 0；之後等兩倍間隔，沒有任何行程被重啟；鎖已釋放（另起一份可以成功啟動） | 自動：`tests/platform_autostart_test.sh` |
| TC-030 | 計畫 §1：收到 SIGINT 同上 | 功能 | 同 TC-029 | 對看守腳本送 `kill -INT` | 結果與 TC-029 相同 | 自動：`tests/platform_autostart_test.sh` |
| TC-031 | 計畫 §1：還在的再 SIGKILL | 例外 | 一個假行程設定 `trap '' TERM`（忽略 SIGTERM）後長時間睡著；等待旋鈕設 1 秒 | 對看守腳本送 `kill -TERM` | 在「等待旋鈕 + 3 秒」內看守腳本結束；該假行程已不存在（被 SIGKILL）；之後沒有重啟 | 自動：`tests/platform_autostart_test.sh` |
| TC-032 | 計畫 §1：訊號轉給「所有子行程」；不留孤兒 | 例外 | 假行程是 `sh -c 'sleep 600'`（有孫行程），指令帶一個獨一無二的標記字串 | 對看守腳本送 `kill -TERM` | 以標記字串搜尋，不剩任何行程（孫行程也不在） | 自動：`tests/platform_autostart_test.sh` |
| TC-033 | 計畫 §1：收到訊號後不再重啟（包括正在等間隔時） | 例外 | 立刻結束的假行程，已進入一個較長的間隔等待 | 在等待中對看守腳本送 `kill -TERM` | 看守腳本很快結束（不等完間隔）；結束後啟動次數不再增加 | 自動：`tests/platform_autostart_test.sh` |
| TC-034 | 例 2 原話：「平台當掉（我把其中一個行程砍掉），幾秒後它自己回來，其他的沒受影響。」（真平台） | 功能 | 合併後、與維護者約好時間；六個行程由看守腳本管 | 維護者自己 `kill` 其中一個（例如 web），看網站與 `--status` | 幾秒後 web 自己回來；其他五個行程編號不變；網站正常 | 手動：`docs/TESTING.md`「platform-autostart」 |
| TC-035 | 計畫 §1：每個行程的輸出接到 `log/<名字>.log` | 功能 | 假行程印出一句獨一無二的字串到 stdout，一句到 stderr | 啟動 | 兩句都在 `<狀態資料夾>/log/<名字>.log`；都沒有出現在看守腳本自己的終端輸出 | 自動：`tests/platform_autostart_test.sh` |

## US3 — 想知道現在哪些在跑，下一個指令就看得到（例 3；計畫 §1 `--status`）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 例 3 原話：「我想知道現在哪些在跑，下一個指令就看得到。」 | 功能 | 看守腳本管三個假行程，都在跑 | 另開一個終端執行 `abf-supervise.sh --status`（同一個狀態資料夾） | 每個名字一行，寫明「在跑」、行程編號、上次啟動時間、重啟次數（此時為 0）；結束碼 0 | 自動：`tests/platform_autostart_test.sh` |
| TC-041 | 計畫 §1：重啟次數、行程編號 | 功能 | 同上，對 b 送 `kill -9` 並等它回來 | 再跑 `--status` | b 的重啟次數是 1、行程編號是新的、上次啟動時間更新；a、c 的次數仍是 0 | 自動：`tests/platform_autostart_test.sh` |
| TC-042 | 計畫 §1：「在跑／沒在跑」 | 功能 | 一個正在「退避等待」中的假行程（剛當掉、還沒重啟） | 跑 `--status` | 該名字顯示「沒在跑」，而不是沿用舊的行程編號顯示成在跑；其他名字照實 | 自動：`tests/platform_autostart_test.sh` |
| TC-043 | 計畫 §1：`--status` 不啟動任何東西 | 功能 | 看守腳本在跑 | 連續跑 `--status` 五次 | 每個假行程的行程編號與啟動次數都不變；沒有新行程出現；沒有新的鎖或新的記錄行被寫入 | 自動：`tests/platform_autostart_test.sh` |
| TC-044 | 計畫 §1：看守腳本沒在跑時說明白，結束碼 1 | 例外 | 狀態資料夾存在，但沒有看守腳本在跑 | 跑 `--status` | 印白話一句「看守腳本沒在跑」並說下一步（怎麼手動試跑或看註冊狀態）；結束碼 1；沒有啟動任何行程 | 自動：`tests/platform_autostart_test.sh` |
| TC-045 | 計畫 §1：`--status` 不能被過期的檔案騙 | 例外 | 看守腳本被 `kill -9`（狀態檔還在、行程編號還寫在裡面），子行程也已清掉 | 跑 `--status` | 仍說「看守腳本沒在跑」，結束碼 1；不顯示過期的「在跑」 | 自動：`tests/platform_autostart_test.sh` |
| TC-046 | 計畫 §1：`--status` 不啟動、不留東西 | 例外 | 狀態資料夾根本不存在（全新機器） | 跑 `--status` | 說沒在跑，結束碼 1；沒有建立狀態資料夾、記錄或鎖 | 自動：`tests/platform_autostart_test.sh` |
| TC-047 | 例 3 原話：「我想知道現在哪些在跑，下一個指令就看得到。」（真平台） | 功能 | 合併後、與維護者約好時間；看守腳本管著六個行程 | 維護者照文件打 `--status` | 看到六個名字各自「在跑」，維護者看得懂每一欄；不需要打別的指令 | 手動：`docs/TESTING.md`「platform-autostart」 |

## US4 — 不會同時跑兩份（例 4；計畫 §1 單一實例）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 例 4 原話：「它不會同時跑兩份。」；計畫 §1：第二份印一句話、結束碼 0、不啟動任何東西 | 功能 | 一份看守腳本在跑三個假行程 | 同一個狀態資料夾再啟動第二份 | 第二份印一句白話（說已有一份在跑，可用 `--status` 看）並結束，結束碼 0；沒有新的假行程出現；第一份的假行程行程編號與啟動次數都不變 | 自動：`tests/platform_autostart_test.sh` |
| TC-051 | 計畫 §1：鎖只看狀態資料夾 | 例外 | 第一份在跑；準備另一份不同的清單檔（會啟動不同的假行程） | `--list <另一份清單>` 啟動第二份 | 仍被擋下，結束碼 0；另一份清單的假行程沒有被啟動 | 自動：`tests/platform_autostart_test.sh` |
| TC-052 | 計畫 §1：單一實例 | 功能 | 第一份正常結束（SIGTERM） | 再啟動一份 | 可以啟動，三個假行程再度在跑（鎖已釋放） | 自動：`tests/platform_autostart_test.sh` |
| TC-053 | 計畫 §1：`flock` 會在行程死亡時自動釋放；孤兒子行程另見文件 | 例外 | 第一份被 `kill -9`；手動清掉遺留的假行程 | 再啟動一份 | 新的一份可以啟動（不被過期的鎖卡住） | 自動：`tests/platform_autostart_test.sh` |
| TC-054 | 計畫 §1：單一實例（競爭條件） | 例外 | 乾淨的狀態資料夾 | 同時（同一瞬間）啟動兩份 | 恰好一份啟動行程；另一份說明已有一份在跑，結束碼 0；每個名字的行程只有一個（以標記字串數行程） | 自動：`tests/platform_autostart_test.sh` |
| TC-055 | 例 4 原話：「它不會同時跑兩份。」（真環境） | 功能 | 合併後、與維護者約好時間；登入工作已讓看守腳本在跑 | 維護者在終端手動再執行一次看守腳本 | 它說已經有一份在跑然後結束；`--status` 仍是六個行程、沒有第二組 | 手動：`docs/TESTING.md`「platform-autostart」 |

## US5 — 裡面沒有權杖（例 5；計畫 §1、§2）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 例 5 原話：「裡面沒有我的權杖。」；計畫 §2：沒有任何權杖 | 功能 | `deploy/wsl/processes.example` | 以看守腳本自己的權杖偵測規則，加上倉庫的權杖形狀規則掃它；並確認路徑都是 `<...>` 佔位字 | 沒有任何一行含權杖形狀（`abf_` 開頭長字串、`Bearer `、`-----BEGIN`）；沒有任何真人的路徑、主機名；只有佔位字 | 自動：`tests/platform_autostart_test.sh` |
| TC-061 | 計畫 §2：上面六行的範例 | 功能 | 同上 | 讀範例檔的非註解行 | 剛好六行，名字不重複、都符合 `[a-z0-9-]`；其中是 `abf-platform serve`、`abf-platform web --public-url <…>`、`abf-platform mcp --http --public-url <…>`、三個 `abf-station run --platform http://127.0.0.1:8787 --token-file <…> --deployment <…> --plugin-root <…>`；權杖只以 `--token-file` 的檔案路徑出現 | 自動：`tests/platform_autostart_test.sh` |
| TC-062 | 計畫 §1：`--check` 與範例檔相容 | 功能 | 範例檔複製到暫存、權限設 0600 | 跑 `--check` | 沒有任何「格式錯誤」或「權杖」的訊息；唯一的錯誤是佔位的執行檔不存在（逐行說明） | 自動：`tests/platform_autostart_test.sh` |
| TC-063 | 計畫 §1：行含 `abf_` 開頭長字串就拒絕啟動，請改用 `--token-file` | 例外 | 清單一行：`web abf-platform web --token abf_` 加 30 個英數字（測試在執行時用片段組出，不把整段寫進原始碼） | 啟動看守腳本 | 拒絕，結束碼 2；訊息說第幾行像權杖、請改用 `--token-file`；沒有任何行程被啟動（哨兵檔不存在）；訊息與記錄都沒有印出那串權杖本身 | 自動：`tests/platform_autostart_test.sh` |
| TC-064 | 計畫 §1：`Bearer ` | 例外 | 清單一行含 `Authorization: Bearer ` 加一串字 | 啟動 | 同 TC-063：拒絕、結束碼 2、沒啟動、不回印那串字 | 自動：`tests/platform_autostart_test.sh` |
| TC-065 | 計畫 §1：`-----BEGIN` | 例外 | 清單一行含 `-----BEGIN` 開頭（以片段在執行時組出） | 啟動 | 同 TC-063 | 自動：`tests/platform_autostart_test.sh` |
| TC-066 | 計畫 §1：「任何一行」（含註解行，P13） | 例外 | 權杖樣子的字串只出現在以 `#` 開頭的註解行 | 啟動 | 一樣拒絕，說是第幾行；沒啟動 | 自動：`tests/platform_autostart_test.sh` |
| TC-067 | 計畫 §1：`--check` 也要抓到 | 例外 | 同 TC-063 的清單 | 跑 `--check` | 結束碼 2，逐行說哪一行有問題；不回印那串字 | 自動：`tests/platform_autostart_test.sh` |
| TC-068 | 計畫 §1：不誤擋正常的行 | 功能 | 清單行含 `abf-platform`、`abf-station`、`--token-file /tmp/x/abf_token`、`abf_platform` 這類正常字樣（`abf_` 後面不到 20 個連續字元） | 跑 `--check` 與啟動 | 沒有任何一行被當成權杖；可以正常啟動 | 自動：`tests/platform_autostart_test.sh` |
| TC-069 | 計畫 §1：清單檔群組或其他人可讀寫就拒絕（P10） | 例外 | 同一份有效清單，權限分別設 0666、0664、0660、0640、0644 | 各啟動一次 | 每個都拒絕，結束碼 2；訊息說明檔名、為什麼（它決定以這個帳號執行什麼）、並給出 `chmod 600 <檔案>`；沒有任何行程被啟動 | 自動：`tests/platform_autostart_test.sh` |
| TC-070 | 計畫 §1：正常權限可用 | 功能 | 同一份清單，權限設 0600 與 0400 | 各跑 `--check` | 不因權限被拒 | 自動：`tests/platform_autostart_test.sh` |
| TC-071 | 計畫 §1：`--check` 也看權限 | 例外 | 權限 0666 的有效清單 | 跑 `--check` | 結束碼 2，逐行／逐項說權限太寬；不啟動 | 自動：`tests/platform_autostart_test.sh` |
| TC-072 | 計畫 §1：資料夾 0700、檔案 0600 | 功能 | 全新狀態資料夾，分別在 umask 022 與 000 下啟動，讓一個行程當掉一次並讓記錄換檔一次 | 檢查狀態資料夾內所有東西的權限 | 狀態資料夾與 `log/` 是 0700；`supervise.log`、各行程記錄、換出的舊檔、鎖檔、狀態檔都是 0600；兩種 umask 結果相同 | 自動：`tests/platform_autostart_test.sh` |
| TC-073 | 例 5 原話：「裡面沒有我的權杖。」；計畫 §1：任何輸出與記錄不印出環境變數 | 例外 | 啟動環境放一個假變數 `CANARY_SECRET=<一串獨一無二的字>`；假行程本身不印環境 | 跑完整的一輪：啟動、當掉重啟、`--status`、`--check`、拒絕啟動（壞清單）、SIGTERM 停止 | 這串字沒出現在看守腳本的任何 stdout／stderr、`supervise.log`、任何行程記錄或任何狀態檔裡 | 自動：`tests/platform_autostart_test.sh` |
| TC-074 | 計畫 §1：不印環境變數（靜態） | 功能 | 讀看守腳本 | 檢查內容 | 沒有 `set -x`／`set -o xtrace`、`env`、`printenv`、`export -p`、`declare -p`、`set` 單獨輸出等會傾印環境的用法 | 自動：`tests/platform_autostart_test.sh` |
| TC-075 | 計畫「測試怎麼做」：不碰使用者家目錄；任務要求：狀態資料夾以外不寫東西 | 功能 | HOME 與 TMPDIR 都指到暫存；先記下兩處（狀態資料夾除外）的完整檔案清單、雜湊與修改時間 | 跑完整的一輪（含 `--check`、`--status`、當掉重啟、換檔、停止） | 狀態資料夾以外沒有新增、修改或刪除任何檔案；清單檔本身雜湊與修改時間不變；TMPDIR 沒有殘留 | 自動：`tests/platform_autostart_test.sh` |
| TC-076 | 計畫 §1：拒絕時不留東西 | 例外 | 全新狀態資料夾不存在；清單含權杖或權限太寬 | 啟動（會被拒絕） | 被拒絕後沒有建立狀態資料夾、鎖或記錄 | 自動：`tests/platform_autostart_test.sh` |
| TC-077 | 例 5 原話：「裡面沒有我的權杖。」（真機器） | 功能 | 合併後、與維護者約好時間；已真實跑過一段時間 | 對清單檔與狀態資料夾搜尋權杖形狀字串（不把結果內容貼出來，只看有沒有） | 兩處都沒有權杖形狀的字串；維護者的權杖只在他原本放的 `--token-file` 檔案裡 | 手動：`docs/TESTING.md`「platform-autostart」 |

## US6 — 清單檔、記錄、文件（計畫 §1、§4）（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | 計畫 §1：每行「名字，空白，要執行的完整指令」；`#` 與空行略過 | 功能 | 清單含註解、空行、行首縮排的空白、一行指令帶引號與含空白的參數（如 `sh -c 'echo a b'`） | 啟動 | 註解與空行被略過；指令的引號與參數按 shell 規則保留（假行程收到的參數與寫的一致）；名字就是第一個字 | 自動：`tests/platform_autostart_test.sh` |
| TC-081 | 計畫 §1：名字只准 `[a-z0-9-]` | 例外 | 名字分別為 `Web`、`my_proc`、`a.b`、`ab c` 之外的怪字元（中文、`/`） | 跑 `--check` 與啟動 | 每個都被拒，結束碼 2，說第幾行、名字哪裡不合法；啟動時沒有任何行程被啟動 | 自動：`tests/platform_autostart_test.sh` |
| TC-082 | 計畫 §1：不可重複 | 例外 | 兩行使用同一個名字 | 跑 `--check` 與啟動 | 都被拒，結束碼 2，說兩行的行號與重複的名字；啟動時沒有任何行程被啟動 | 自動：`tests/platform_autostart_test.sh` |
| TC-083 | 計畫 §1：格式 | 例外 | 一行只有名字沒有指令 | 跑 `--check` | 結束碼 2，說第幾行缺指令 | 自動：`tests/platform_autostart_test.sh` |
| TC-084 | 計畫 §1：`--check` 檢查每個指令的執行檔存不存在 | 例外 | 一行的執行檔路徑不存在；另一行的執行檔存在但不可執行 | 跑 `--check` | 結束碼 2，逐行說執行檔找不到或不可執行；沒有啟動任何東西 | 自動：`tests/platform_autostart_test.sh` |
| TC-085 | 計畫 §1：`--check` 只檢查，不啟動 | 功能 | 一份完全正確的清單 | 跑 `--check` | 結束碼 0；說「清單沒問題」；沒有任何假行程啟動（哨兵檔不存在）；沒有建立狀態資料夾或鎖 | 自動：`tests/platform_autostart_test.sh` |
| TC-086 | 計畫 §1：有錯逐行說哪裡錯 | 例外 | 清單同時有三種錯（壞名字、重複名字、不存在的執行檔） | 跑 `--check` | 結束碼 2；一次把三個錯都列出，每個帶行號；不是只報第一個 | 自動：`tests/platform_autostart_test.sh` |
| TC-087 | 計畫 §1：預設清單位置 `~/.config/abf-platform/processes` | 功能 | HOME 指暫存，清單放在該預設位置（0600） | 不帶 `--list` 啟動 | 讀到預設位置的清單並啟動 | 自動：`tests/platform_autostart_test.sh` |
| TC-088 | 計畫 §1：清單檔不存在或讀不到 | 例外 | `--list` 指向不存在的檔案；另一次沒有 `--list` 且預設位置沒檔 | 啟動與 `--check` | 說白話一句（找不到哪個檔、要怎麼建立、可看 `processes.example`），結束碼 2；不是 shell 的錯誤堆疊；不啟動任何東西 | 自動：`tests/platform_autostart_test.sh` |
| TC-089 | 計畫 §1（空清單，P7） | 例外 | 清單只有註解與空行 | 啟動與 `--check` | 拒絕，結束碼 2，說「沒有可看守的行程」；不空轉 | 自動：`tests/platform_autostart_test.sh` |
| TC-090 | 計畫 §1：記錄超過 10 MB 時換檔，保留一份舊檔 | 功能 | 換檔大小旋鈕調成很小；某行程記錄已超過它，再啟動看守腳本 | 啟動 | 該記錄被換成一份舊檔（例如 `<名字>.log.1`），新的 `<名字>.log` 從空開始；只留這一份舊檔 | 自動：`tests/platform_autostart_test.sh` |
| TC-091 | 計畫 §1：保留一份舊檔 | 功能 | 同上，再讓它超過第二次 | 再啟動／再寫入 | 仍然只有一份舊檔，內容是最近一次換出的；更舊的被丟棄 | 自動：`tests/platform_autostart_test.sh` |
| TC-092 | 計畫 §1；P8：不當掉的行程記錄也不能無限長 | 功能 | 一個假行程持續不斷地寫輸出，總量達換檔大小旋鈕的 3 倍以上，期間不當掉 | 觀察記錄檔 | 現行記錄檔的大小不超過旋鈕 + 一個檢查週期的量；舊檔只有一份；行程編號沒變（沒有為了換檔而重啟它） | 自動：`tests/platform_autostart_test.sh` |
| TC-093 | 計畫 §1：10 MB；`supervise.log` 也適用 | 功能 | 檢查檔頭預設值；`supervise.log` 超過旋鈕 | 檢查並觸發 | 預設換檔大小是 10 MB（10485760 位元組）；`supervise.log` 也被換檔、保留一份舊檔；新檔開頭仍有時間格式的行 | 自動：`tests/platform_autostart_test.sh` |
| TC-094 | 計畫 §1：每行有時間 | 功能 | 跑一輪含重啟與停止 | 讀 `supervise.log` 每一行 | 每一行都以日期時間開頭（同一格式），沒有無時間的行 | 自動：`tests/platform_autostart_test.sh` |
| TC-095 | 計畫「專長守則」：訊息用白話、一句說完發生什麼與下一步 | 功能 | TC-012、TC-044、TC-063、TC-069、TC-082、TC-088 產生的訊息 | 逐條讀 | 每則訊息一句話內說清楚發生什麼，並帶一個下一步（要做什麼、哪個指令）；沒有只有「error」或 shell 原始錯誤 | 自動：`tests/platform_autostart_test.sh` |
| TC-096 | 計畫 §4：`docs/OPERATIONS.md` 新增一節「桌機（WSL）上自動啟動」 | 功能 | 讀 `docs/OPERATIONS.md` | 檢查該節 | 有這一節，並依序涵蓋：前提、寫清單檔、`--check`、手動試跑、註冊、怎麼看狀態與記錄、怎麼停、怎麼移除 | 自動：`tests/platform_autostart_test.sh` |
| TC-097 | 計畫 §4：兩件做不到的事 | 功能 | 同上 | 檢查該節 | 明寫：(1) 國網共用 SSH 連線（要 OTP）不會自動恢復，重開機後要本人重新連線、網站會提示；(2) 從手動啟動換到看守腳本要先停掉手動起的行程，平台會中斷約一分鐘 | 自動：`tests/platform_autostart_test.sh` |
| TC-098 | 計畫 §4；P9：停它要用 SIGTERM，不要 `kill -9` | 功能 | 同上 | 檢查該節 | 明寫停看守腳本的正確方式（SIGTERM／Ctrl-C）與不要用 `kill -9` 的原因；文件提到的每個開關（`--list`、`--check`、`--status`、`-Apply`、`-Remove`）在腳本裡都真的存在，提到的檔名都真的存在 | 自動：`tests/platform_autostart_test.sh` |
| TC-099 | 計畫 §4：CHANGELOG 照慣例加一行 | 功能 | 讀 `CHANGELOG.md` | 檢查 `3.0.0-dev` 那一節 | 有一行提到 platform-autostart 與 `deploy/wsl/`，寫法與同節其他行一致 | 自動：`tests/platform_autostart_test.sh` |

## US7 — 不在範圍（計畫「不做什麼」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-110 | 計畫「不做什麼」1：不開 WSL 的 systemd、不寫 `/etc/wsl.conf`、不用 sudo | 不在範圍 | 讀新增的三個檔與文件新節 | 搜尋 | 沒有 `sudo`、`/etc/wsl.conf`、`systemctl`、`systemd=true`、對 `/etc` 的寫入；文件說明有 systemd 的主機請用 `deploy/systemd/` | 自動：`tests/platform_autostart_test.sh` |
| TC-111 | 計畫「不做什麼」2：不改 `deploy/systemd/` | 不在範圍 | 與基底分支 `origin/v3` 比較 | `git diff origin/v3...HEAD -- deploy/systemd` | 沒有任何差異 | 自動：`tests/platform_autostart_test.sh` |
| TC-112 | 計畫風險 M：只加 `deploy/` 新檔、文件與測試；不動 `platform/`、`hooks/`、`.github/`、憲法、`plugin.json` | 不在範圍 | 同上 | `git diff --name-only origin/v3...HEAD` | 改動的檔案只在：`deploy/wsl/`、`docs/OPERATIONS.md`、`docs/TESTING.md`、`CHANGELOG.md`、`specs/platform-autostart/`、`tests/platform_autostart_test.sh`、`tests/hosted_deploy_test.sh`（只加清單項，見 TC-123）；`platform/`、`hooks/`、`.github/`、`.specify/memory/constitution.md`、`plugin.json` 都沒動 | 自動：`tests/platform_autostart_test.sh` |
| TC-113 | 計畫「不做什麼」3：這個 PR 不對維護者的桌機做任何更動（倉庫面） | 不在範圍 | 檢視 diff | 找真實的清單檔、真實權杖路徑、註冊動作 | 倉庫裡只有 `processes.example`，沒有名為 `processes` 的真清單；沒有任何腳本或測試在 PR 內被自動執行去註冊工作；安裝腳本預設是只印字（TC-005） | 自動：`tests/platform_autostart_test.sh` |
| TC-114 | 計畫「不做什麼」3（桌機面） | 不在範圍 | 合併前、PR 還沒跟維護者約時間 | 維護者在桌機查有沒有 `abf-platform-autostart` 工作、六個手動行程是否仍照舊 | 沒有這個工作；他手動起的六個行程沒被動過 | 手動：`docs/TESTING.md`「platform-autostart」 |
| TC-115 | 計畫「不做什麼」4：不處理 Tailscale Funnel | 不在範圍 | 讀新增的三個檔 | 搜尋 | 沒有任何 `tailscale`／`funnel` 的呼叫（文件可以說明「這個不歸它管」） | 自動：`tests/platform_autostart_test.sh` |
| TC-116 | 計畫 §4：國網共用 SSH 連線不會自動恢復 | 不在範圍 | 讀新增的三個檔 | 搜尋 | 看守腳本與安裝腳本都沒有呼叫 `ssh`、`on_site.sh`、任何需要 OTP 的連線；文件明說這件事要本人做（TC-097） | 自動：`tests/platform_autostart_test.sh` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-120 | 原則 I.1：寫明它不是什麼；計畫 §1「腳本開頭照本 repo 的慣例」 | 功能 | 讀 `abf-supervise.sh` 與 `install-autostart.ps1` 前 40 行 | 檢查 | 各有一行 `# Not <外部工具>: <至少 15 字的理由>`（看守腳本寫 systemd；有 systemd 的主機請用 `deploy/systemd/`；安裝腳本寫工作排程器現成的圖形介面／NSSM 之類外部工具）；工具名不是本倉庫的檔案 | 自動：`tests/platform_autostart_test.sh` |
| TC-121 | 原則 I.2：不另存 run 的狀態、不做監控 run 的常駐程式；P1 | 功能 | 讀看守腳本與它寫出的狀態檔 | 搜尋、並實跑一輪看狀態資料夾內容 | 看守腳本不呼叫 `tw`、`nextflow`、`abf-platform` 的 run 相關指令，不讀 trace、報告或平台資料庫；狀態檔只有名字、行程編號、時間、次數、結束碼；`tests/no_second_run_state_test.sh` 仍綠 | 自動：`tests/platform_autostart_test.sh`；`tests/no_second_run_state_test.sh` |
| TC-122 | 安全網：權杖不進被追蹤的檔；`credentials_stay_in_settings_test.sh` | 功能 | 本功能新增的檔案與測試 | 跑 `bash tests/credentials_stay_in_settings_test.sh` | 綠；新測試裡種的假權杖是在執行時用片段組成，不需要加進 `FIXTURE_ALLOW`（若加了，須在計畫點名並說明理由） | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-123 | 驗收規則：改既有測試須由計畫點名；`hosted_deploy_test.sh` 的 TC-069 與 TC-075 至 TC-077 | 功能 | 計畫已補上 F1 一行 | 跑 `bash tests/hosted_deploy_test.sh`，並看它對 origin/v3 的 diff | 全綠；diff 只有 TC-069 的預期清單多了 `deploy/wsl/` 三個檔，沒有其他斷言被刪、放寬或略過；新檔不觸發 TC-075 至 TC-077 的掃描 | 自動：`tests/hosted_deploy_test.sh` |
| TC-124 | 可攜性與既有守門測試 | 功能 | 本功能新增的檔案與測試 | 跑 `portable_userland.sh`、`no_hardcoded_paths.sh`、`shell_helper_dupes_test.sh`、`scripts_name_their_alternative.sh` | 全綠；新測試沒有多出被 `shell_helper_dupes` 抓到的重複 helper，沒有需要新增基準線項目 | 自動：上述各檔 |
| TC-125 | 原則 VI：什麼都不要悄悄不見 | 例外 | 狀態資料夾無法寫入（唯讀或權限不足） | 啟動看守腳本 | 說白話一句（哪個資料夾寫不進去、下一步），結束碼 2；不是在「沒有記錄」的情況下默默跑起行程 | 自動：`tests/platform_autostart_test.sh` |
| TC-126 | 計畫「測試怎麼做」：全套綠；新測試被 `run_all.sh` 收進去 | 功能 | 本功能完成 | `bash tests/run_all.sh --list`；全套在 WSL 或 CI 上跑 | 清單裡有 `platform_autostart_test.sh`；全套綠；沒有檔案因為新增而變紅 | 自動：`tests/run_all.sh`（WSL 或 CI） |
