# 測試案例：夾在刪除指令名字中間的反斜線（issue #66）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Language: 繁體中文; identifiers and paths stay as they are.
-->

**規格**：`.specify/bugs/backslash-inside-delete-word/assessment.md`（issue #66 為準）　**總覽**：`test-case-overview.md`

名詞：「刪除關卡」＝ `hooks/confirm_cleanup.sh`，在 Claude 要執行刪除指令前攔下它。「deny」＝直接擋；「ask」＝跳出確認框問使用者；「pass」＝不吭聲放行。「run 資料夾」＝一次分析的資料夾，裡面有 `results/`、`work/`。
「同一條拿掉反斜線的指令」＝把指令裡的 `\` 全部刪掉再丟給關卡，得到的判定就是這條應得的判定。
反斜線在 shell 裡放在字母前只是「照字面」，所以 `r\m` 實際執行的就是 `rm`。

類型只有三種：功能、例外、不在範圍。

## 修復 1 — 有 jq：指令名字或選項中間夾反斜線，也要被關卡判到（優先度 P1）

目標一律是該 run 資料夾的 `results/`（測試中用 `/work/u9613010/lab_runs/x/results` 這種絕對路徑，與 `tests/confirm_cleanup_test.sh` 其他案例一致）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | issue #66 指令 1 | 功能 | 有 jq；目標是 run 的 `results/` | 對關卡送 `r\m -rf results` | deny（與 `rm -rf results` 相同；main 上是無聲放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-002 | issue #66 指令 2 | 功能 | 同上 | 送 `t\ar --remove-files -cf a.tar results` | deny（與 `tar --remove-files -cf a.tar results` 相同） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-003 | issue #66 指令 4 | 功能 | 同上 | 送 `tar --remo\ve-files -cf a.tar results`（反斜線在選項中間） | deny | 自動：`tests/confirm_cleanup_test.sh` |
| TC-004 | issue #66 指令 3 | 功能 | 有 jq | 送 `nextflow cl\ean -f` | ask（與 `nextflow clean -f` 相同；main 上是無聲放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-005 | issue 要求「判定同拿掉反斜線的指令」 | 功能 | 目標是 run 的 `work/` | 送 `r\m -rf work` | ask（不是 deny，也不是放行；與 `rm -rf work` 相同） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-006 | 同一行有多個指令 | 功能 | 目標是 run 的 `results/` | 送 `echo hi; r\m -rf results` | deny | 自動：`tests/confirm_cleanup_test.sh` |
| TC-007 | 包在 ssh 裡 | 功能 | 同上 | 送 `ssh twnia3 'r\m -rf <results 路徑>'` | deny（與沒有反斜線的 ssh 版相同） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-008 | 指令前面有 sudo | 功能 | 同上 | 送 `sudo r\m -rf results` | deny（與 `sudo rm -rf results` 相同） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-009 | 「取最嚴格那份」 | 功能 | 同一個指令同時列 `work/` 和 `results/` | 送 `r\m -rf work results`（絕對路徑形式） | deny（不是只問 ask） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-010 | 多個反斜線 | 功能 | 目標是 run 的 `results/` | 送 `r\m -rf res\ults` | deny | 自動：`tests/confirm_cleanup_test.sh` |
| TC-011 | issue「A backslash in an argument is handled」（防退步） | 功能 | 同上 | 送 `rm -rf res\ults` | 仍是 deny | 自動：`tests/confirm_cleanup_test.sh` |
| TC-012 | issue「leading backslash handled, #65」（防退步） | 功能 | 同上 | 送 `\rm -rf results` | 仍是 deny | 自動：`tests/confirm_cleanup_test.sh` |

## 修復 2 — 有 jq：正常指令不能因為多了反斜線處理而被誤問（優先度 P1）

issue 明講要檢查「沒有新增誤問」。以下全部必須是 pass（完全不吭聲）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | issue 對照組 | 功能 | 有 jq | 送 `printf 'a\nb'` | pass | 自動：`tests/confirm_cleanup_test.sh` |
| TC-014 | issue 對照組（grep 正規式） | 功能 | 有 jq | 送 `grep -E "a\sb" file` | pass | 自動：`tests/confirm_cleanup_test.sh` |
| TC-015 | issue 對照組（sed 正規式） | 功能 | 有 jq | 送 `sed 's/a\/b/c/' f` | pass | 自動：`tests/confirm_cleanup_test.sh` |
| TC-016 | issue 對照組（Windows 路徑） | 功能 | 有 jq | 送 `echo C:\Users\x` | pass | 自動：`tests/confirm_cleanup_test.sh` |
| TC-017 | issue 對照組（Windows 路徑指到 results，只是看） | 功能 | 有 jq | 送 `ls C:\work\results` | pass（唯讀，不能問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-018 | 只是印出字，不是刪除 | 功能 | 有 jq | 送 `echo r\m -rf <results 路徑>` | 與 `echo rm -rf <results 路徑>` 在 main 上的判定相同（預期 pass） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-019 | 目標不是受保護資料夾 | 功能 | 有 jq | 送 `r\m -rf <run>/re\ports`（reports 不受保護） | pass（與 `rm -rf <run>/reports` 相同；`tests/confirm_cleanup_test.sh:510` 已有 `rm -rf re\ports` 同類案例） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-020 | 無害的 nextflow 子指令 | 功能 | 有 jq | 送 `nextflow l\og` | pass | 自動：`tests/confirm_cleanup_test.sh` |

## 修復 3 — 沒有 jq：不能無聲放行（憲法第 13 條）（優先度 P1）

沒有 jq 時關卡只看原始文字，疑似刪除就 exit 2 並印 `BLOCKED: jq is missing …`；不是刪除就 exit 0。測試用 `tests/lib/nojq_path.sh` 藏起 jq，並確認真的藏起來。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 計畫第 3 項 | 例外 | 沒有 jq | 送 `r\m -rf results` | exit 2、stderr 有 `BLOCKED` 和 `jq is missing`（main 上是 exit 0，這是真修復） | 自動：`tests/gates_without_jq_test.sh` |
| TC-022 | 計畫第 3 項 | 例外 | 沒有 jq | 送 `tar --remo\ve-files -cf a.tar results` | exit 2、BLOCKED（main 上 exit 0） | 自動：`tests/gates_without_jq_test.sh` |
| TC-023 | 計畫第 3 項 | 例外 | 沒有 jq | 送 `nextflow cl\ean -f` | exit 2、BLOCKED（main 上 exit 0） | 自動：`tests/gates_without_jq_test.sh` |
| TC-024 | 開頭反斜線的備援（#65 只修了有 jq 的路） | 例外 | 沒有 jq | 送 `\rm -rf results` | exit 2、BLOCKED（main 上 exit 0） | 自動：`tests/gates_without_jq_test.sh` |
| TC-025 | 防退步：main 本來就擋 | 例外 | 沒有 jq | 送 `t\ar --remove-files -cf a.tar results` | exit 2、BLOCKED（main 已經擋；不能因修改而放行） | 自動：`tests/gates_without_jq_test.sh` |
| TC-026 | 沒有 jq 的對照組，不能因此多擋 | 功能 | 沒有 jq | 送 `printf 'a\nb'` | exit 0 | 自動：`tests/gates_without_jq_test.sh` |
| TC-027 | 同上 | 功能 | 沒有 jq | 送 `grep -E "a\sb" file` | exit 0 | 自動：`tests/gates_without_jq_test.sh` |
| TC-028 | 同上 | 功能 | 沒有 jq | 送 `sed 's/a\/b/c/' f` | exit 0 | 自動：`tests/gates_without_jq_test.sh` |
| TC-029 | 同上 | 功能 | 沒有 jq | 送 `echo C:\Users\x` | exit 0 | 自動：`tests/gates_without_jq_test.sh` |
| TC-030 | 同上 | 功能 | 沒有 jq | 送 `ls C:\work\results` | exit 0 | 自動：`tests/gates_without_jq_test.sh` |

## 修復 4 — 大輸入（big here-doc）與速度（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | 計畫第 2 項：大輸入路徑也要看到去掉反斜線的版本 | 功能 | 有 jq；一大段 here-doc 之後接 TC-001..TC-012 的指令 | 跑 `tests/confirm_cleanup_behind_heredoc_test.sh`（它會把 `confirm_cleanup_test.sh` 的每一條放到大 here-doc 後面再跑一遍，其中包含 TC-001..TC-020 的新案例） | 所有案例判定與小輸入相同，輸出無 FAIL；新案例確實存在於 `confirm_cleanup_test.sh`（否則此條是空轉） | 自動：`tests/confirm_cleanup_behind_heredoc_test.sh` |
| TC-032 | 不能讓無反斜線的大輸入變慢 | 功能 | 有 jq；大 here-doc 內容沒有任何反斜線 | 跑同一個測試開頭的「awk 次數」檢查 | awk 仍恰好 3 次（去反斜線的額外一次只在有反斜線時才跑） | 自動：`tests/confirm_cleanup_behind_heredoc_test.sh` |
| TC-033 | issue「300 KB 計時約 3 秒內」 | 功能 | 有 jq；300 KB 的 here-doc，**每一行都含反斜線**（例如 `s.split('\t')`），後面接 `r\m -rf results` | 計時送進關卡 | deny；在 Linux/WSL 約 3 秒內；30 KB 到 300 KB 時間成長不超過 25 倍；（參考：main 上無反斜線 300 KB 約 0.3 秒） | 自動：`tests/gate_big_input_test.sh`（需新增含反斜線的檔案內容；現有三種內容都沒有反斜線，測不到新程式碼） |
| TC-034 | 同上，確認正常刪除的判定沒被拖慢或弄壞 | 功能 | 同 TC-033 的 300 KB，後面接普通的 `rm -rf results` | 計時送進關卡 | deny，時間同 TC-033 | 自動：`tests/gate_big_input_test.sh` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-035 | 安全網：永不刪使用者原始資料（`rawdata/`） | 功能 | 有 jq | 送 `r\m -rf <run>/rawdata` | deny | 自動：`tests/confirm_cleanup_test.sh` |
| TC-036 | 安全網：永不刪 `.nextflow/plugins/` | 功能 | 有 jq | 送 `r\m -rf <run>/.nextflow/plugins` | deny | 自動：`tests/confirm_cleanup_test.sh` |
| TC-037 | 不變式 13：安全網做不了事要說出來並指出怎麼修 | 例外 | 沒有 jq | 送 TC-021 的指令，讀 stderr | 說明 jq 缺失，並列出安裝方式（brew／apt／winget） | 自動：`tests/gates_without_jq_test.sh` |
| TC-038 | 安全網只能更嚴、不能放寬（教訓：#29 窄化閘門放過 main 擋的三種寫法） | 功能 | 修復前後各一份程式碼 | 跑 `tests/confirm_cleanup_test.sh`、`tests/confirm_cleanup_behind_heredoc_test.sh`、`tests/gates_without_jq_test.sh`；並把 main 上所有現有案例（含 `\rm`、`\tar`、`re\sults`、PowerShell、ssh）在修改後的程式碼上再跑 | 現有案例一條不少、判定不變（deny 沒變 ask、ask 沒變 pass）；現有斷言沒有被刪、放寬或略過 | 自動：以上三個測試檔 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-039 | 計畫「不在範圍」：其他引號／變數／別名手法（`r''m`、`$'\x72'm`、變數、alias）除非 main 本來就擋 | 不在範圍 | 有 jq | 驗收時對 `r''m -rf results`、`$'\x72'm -rf results` 在 main 與修復後各跑一次 | 兩邊判定相同；測試與程式碼沒有為這些手法新增專用處理 | 手動：`docs/TESTING.md`（驗收者逐條比對 main，需補一段步驟） |
| TC-040 | 計畫「不在範圍」：`confirm_launch.sh`、`confirm_walkthrough.sh`、`guard_plugin_files.sh` 不改 | 不在範圍 | 有 diff | 看 `git diff main...HEAD -- hooks/` | 只有 `hooks/confirm_cleanup.sh` 有改；其餘 hooks 無變動 | 手動：`docs/TESTING.md`（需補一段步驟） |
| TC-041 | 計畫「不在範圍」：issue #71 | 不在範圍 | 有 diff | 看 diff 與測試 | 沒有處理 #71 的內容 | 手動：`docs/TESTING.md`（需補一段步驟） |

<!--
Rules: 編號不重編；一條只測一件事；沒有 jq 的測試不得自己依賴 jq（見 tests/gates_without_jq_test.sh 開頭）。
-->
