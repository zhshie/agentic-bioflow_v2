---
id: hook-tests-jq
title: 兩個最慢的安全閘測試改用 jq 組輸入與讀答案（每個案例少起 1～2 個 python），不改任何一條案例的判定
tier: A
kinds: backend
lane: L-hook-tests-speed
base: v3（`origin/v3` @ 50f696b；所有行號都是該版本）
source: developer-agent 實測（2026-10-25，WSL Ubuntu、16 核、v3 的 `git archive`，逐檔計時，見「查證結果」）
---

# hook-tests-jq

> A 級（只動測試）：`tests/confirm_cleanup_test.sh` 與 `tests/confirm_launch_test.sh` 是全套件非平台部分最慢的兩個，卻 70% 的時間花在重複起 python。**只換「組輸入、讀答案」的工具，不換、不增、不刪任何案例與判定。** 這兩個檔是安全閘唯一的證明，所以閱卷嚴格：輸出逐行比對 base，並要做突變驗證。**合併前跑 `/code-review`**（不是 hook 改動，但是 hook 的測試；repo `CLAUDE.md`「Calibration failures」的教訓）。

## 目標
讓 `bash tests/run_all.sh` 少花約 1 分鐘（這個檔被跑兩次：本身一次、`confirm_cleanup_behind_heredoc_test.sh` 在大 here-doc 後再整個重跑一次），開發者回饋更快；判定結果與現在完全相同。

### 查證結果（實測，皆 `origin/v3`；WSL，同一台機器背景有別人的測試在跑，數字有雜訊）
- 逐檔計時（我量到 `platform_*` 之前的 70 多個檔，合計約 450 s；最慢者）：`confirm_cleanup_behind_heredoc_test.sh` 116 s、`confirm_cleanup_test.sh` 68 s、`confirm_launch_test.sh` 58 s、`on_site_parallel_test.sh` 31 s，其餘皆 ≤ 21 s。前三者合計 242 s，超過量到總時間的一半。
- 成本在哪：每個案例的 helper 先用 `python3 -c "import json,sys;print(json.dumps(…))"` 把指令包成 JSON（`tests/confirm_cleanup_test.sh:33`），執行 hook，再用第二個 `python3 -c` 讀 `permissionDecision`（:35）。實測單次 python 啟動 31 ms，`jq -cn --arg` 3 ms，hook 本身對平常指令約 28 ms。`^t "` 案例 324 條（`confirm_cleanup_test.sh`），`t`／`idg`／`msys_*` 約 300 條（`confirm_launch_test.sh:64-71, 618-626, 420-449`）。
- 預實驗（沒進 repo）：只把 `confirm_cleanup_test.sh` 的 `t`／`askcheck`／`denycheck`／`tps`／`tc` 的編碼與解碼換成 jq，同一台機器連跑兩次：原版 50.5 s、62.8 s；改版 38.4 s、37.7 s，兩版都 `all passed`。
- jq 已是這些測試的前提：`tests/confirm_cleanup_test.sh` 其他段落與 `tests/run_all.sh` 的 MISSING 檢查都要求 jq；`run_all.sh` 把「jq 輸出尾端 CR」當成可接受的（`probe="${probe%$'\r'}"`），所以 MSYS 下 jq 會多一個 `\r`，解碼後要 `tr -d '\r'`。
- 兩個陷阱（必須用測試鎖住）：(1) 原本解碼用 `o=json.load(sys.stdin)['hookSpecificOutput']`，答案缺這個鍵就丟錯、`got` 為空、案例 FAIL；若改成 `jq '.hookSpecificOutput.permissionDecision // "warn"'`，缺鍵會變成 `warn`，**期望 warn 的案例會假綠**。(2) `json.dumps` 預設把非 ASCII 轉成 `\uXXXX`，jq 輸出原字元；hook 自己用 jq 讀，兩者等價，但要有一條含中文與 `\r`、`"`、反斜線的案例證明。

## 維護者原話（verifier 出題用）
本任務沒有他的逐字裁示；來源是他要求優化測試速度的一貫方向（總計畫「測試要快」）。等價要求：
- 「判定不能變」→ T1、T2。「不能假綠」→ T3、T4。

## 範圍：檔案（只准改這些，共 3 個）
- `tests/confirm_cleanup_test.sh`（只改 helper 內的組輸入／讀答案：行 33、35、93、232、237、242、247、296、298、423、425、782、784、889、892；其餘一律不動）
- `tests/confirm_launch_test.sh`（只改 `t`〔:67〕、`idg`〔:624〕、`askcheck`／`nodecisioncheck`〔:366-389〕、`msys_ask`／`msys_pass`〔:423-449〕、`envp`／`envq` 系〔:792-864〕的組輸入與讀答案）
- `specs/hook-tests-jq/ledger.md`（新，含改前改後計時與兩版輸出比對）

**不准動**：`hooks/**`、`tests/lib/**`、`tests/confirm_cleanup_behind_heredoc_test.sh`、`tests/run_all.sh`、`tests/flow_skills_layout_test.sh`（它把這兩個檔列為「閘門夾具」例外，:63-70，檔名不能變）、`.github/`、任何一條案例的指令字串／期望／標籤。

## 作法（決定）
1. 編碼：`python3 -c "…json.dumps({'tool_input':{'command':sys.argv[1]}})" "$X"` → `jq -cn --arg c "$X" '{tool_input:{command:$c}}'`；有 `tool_name`／`cwd`／`script_block` 的變體同理加 `--arg`，鍵名與 python 版逐一對應。
2. 解碼（嚴格版）：`jq -er 'if .hookSpecificOutput then (.hookSpecificOutput.permissionDecision // "warn") else error("no hookSpecificOutput") end' 2>/dev/null <<<"$out" | tr -d '\r'`；`.get(…,'')` 型改成 `// ""`，且保留「答案不是 JSON → 值為空 → 案例 FAIL」的行為。
3. 一次性的、不在迴圈裡的 python 區塊（如 `confirm_launch_test.sh:1185-1195` 產生大 here-doc 輸入）**不改**。
4. 每個 helper 的 `printf` 標籤、`ok (...)`／`FAIL: ...` 文字、`fails` 計數一字不改。
5. 不引入平行執行，不改案例順序。

## 失敗先行測試（這是重構，沒有「現在會紅」的行為；以下是閱卷要用的等價證明，executor 把證據貼進 ledger）
| # | 檢查 | 期望 |
|---|---|---|
| T1 | 在 base 與 head 各跑 `bash tests/confirm_cleanup_test.sh`，輸出去掉時間後 `diff` | 零差異（每個案例的 `ok (...)` 行與標籤都相同），結尾都是 `all passed` |
| T2 | 同上，對 `bash tests/confirm_launch_test.sh` 與 `bash tests/confirm_cleanup_behind_heredoc_test.sh` | 零差異 |
| T3 | **突變一（假綠）**：把 `hooks/confirm_cleanup.sh` 的副本改成對任何輸入輸出 `{}`，用 `H=` 指向副本（暫存目錄，不動 repo）跑 head 版 `confirm_cleanup_test.sh` | 期望 `warn` 的案例也要 FAIL（`fails` > 0、結尾 `N failed`，exit 1） |
| T4 | **突變二（放行）**：副本改成永遠不輸出（全部放行） | 期望 `deny`／`ask` 的案例全數 FAIL |
| T5 | `grep -c 'python3 -c' tests/confirm_cleanup_test.sh` 在 helper 函式內為 0（迴圈熱路徑無 python）；檔內剩下的 `python3 -c` 只出現在被測指令字串裡（如 :327、:353、:643） | 如述 |
| T6 | 一條含中文、`"`、`\`、`\r`、換行、單引號的指令經新編碼後，`jq -e . ` 能解析且 `.tool_input.command` 與原字串逐字相等 | 如述 |
| T7 | 計時：同機器連跑 3 次，`confirm_cleanup_test.sh` 中位數比 base 少 ≥ 20% | 寫進 ledger；**不作為 PASS／FAIL 條件**（機器負載雜訊大），但低於 10% 要在 ledger 說明 |
| T8 | `git diff --name-only` 只含上列 3 個檔，`hooks/` 零改動 | 證據貼進 ledger |

## 完成標準（done when）
- T1–T6、T8 通過；整套 `bash tests/run_all.sh`（WSL）綠；`tests/gate_output_failclosed_test.sh`、`gate_process_count_test.sh`、`confirm_cleanup_candidates_timing_test.sh`、`confirm_cleanup_behind_heredoc_test.sh` 不改而綠。
- 兩個被改的檔，案例數（`grep -c '^t "'` 等）與 base 相同；沒有任何案例被刪、跳過或放寬。

## 環境事實
- 只能在 WSL／Linux 驗證（`run_all.sh` 拒絕原生 Git Bash）；worktree 不可在同步磁碟；同一個 checkout 不可同時跑兩份（暫存互踩）。
- `tests/confirm_cleanup_behind_heredoc_test.sh:45` 會用 `CLEANUP_TEST_PREFIX_FILE` 重跑整個 `confirm_cleanup_test.sh`，所以 `$PFX` 前綴要原樣保留在編碼裡（`"$PFX$1"`）。
- 現況已知兩個環境紅（與本任務無關，別當回歸）：`jev_test.sh`、`constitution_scope_test.sh`、`platform_direction_docs_test.sh` 在沒有 `.git` 的 `git archive` 副本裡會失敗；在真的 worktree 裡不會。

## 不做
- 不平行化案例；不改 `run_all.sh`（沒有 `--jobs`，那是另一個需要裁決的題目：測試之間共用快取與埠）；不動 `on_site_parallel_test.sh`；不動 hook。
- 不需要 migration。

## 裁決
- **解碼用嚴格版（缺鍵即錯）**：換來的速度不能用假綠的風險買；T3 專門釘這點。
- **只改熱路徑 helper**：一次性的 python 區塊省不了多少，卻讓 diff 變大、閱卷變難。
- **兩檔一起做**：同一種改法、同一種驗證；分開做會讓同一個 helper 樣式有兩份寫法。若維護者只要 cleanup 那一檔（省得最多：約 25 s × 2），把 `confirm_launch_test.sh` 與 T2 的後半拿掉。

## 裁決（2026-10-25 06:50，developer-agent）
1. 兩支都做（不只 cleanup）。
2. 合併前 developer-agent 跑 /code-review（安全網的測試）。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
