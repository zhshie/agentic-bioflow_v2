# 測試案例：兩支最慢的安全閘測試改用 jq 編解碼（hook-tests-jq）

<!--
Written by the verifier (CONTRACT mode). Source: specs/hook-tests-jq/plan.md (tier A, 只動測試, 重構).
This task has no maintainer verbatim quotes; plan section "維護者原話" gives the equivalence
requirements: 「判定不能變」→ T1、T2；「不能假綠」→ T3、T4. Plan rulings 2026-10-25 (裁決、裁決二) are applied:
T5 limited to the helpers on the plan's line list; mutation done on a temp copy of tests/ + hooks/;
T6 is a one-time check, no permanent case added; the reason field is not CR-stripped.
-->

**規格**：`specs/hook-tests-jq/plan.md`（A 級，沒有 spec.md；計畫即規格）　**總覽**：`test-case-overview.md`

**名詞（一句話）**
- 「兩個被改的檔」＝`tests/confirm_cleanup_test.sh`（測「刪檔守門員」）與 `tests/confirm_launch_test.sh`（測「送出分析前要先確認的守門員」）。
- 「base」＝計畫寫定時的 `origin/v3`（`50f696b`）；「head」＝做完後的分支。
- 「helper」＝測試檔裡每個案例都會呼叫的小函式（`t`、`askcheck`、`idg`…），它們負責「把指令包成 JSON 餵給守門員」與「讀守門員答的決定」。
- 「突變」＝在**暫存目錄的副本**裡故意把守門員改壞（例如對任何輸入都回 `{}`），確認測試真的會變紅；不動 repo 裡的 hook。
- 「輸入記錄」＝在副本守門員最前面加一行，把它收到的每一筆 stdin 追加存檔，再原樣交給真正的邏輯；用來證明 base 與 head 餵給守門員的東西一模一樣。
- 所有「跑測試」都在 WSL／Linux 進行（`tests/run_all.sh` 拒絕原生 Git Bash）；同一個 checkout 不可同時跑兩份。

類型只有三種：功能、例外、不在範圍。

## User Story 1 — 判定完全不變（優先度 P1）

> 維護者的要求：「判定不能變」。換的只是組輸入、讀答案的工具，每個案例的判定（pass／warn／deny／ask／gate）與印出的字一個都不能變。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 T1；「判定不能變」 | 功能 | base 與 head 各一份乾淨 checkout（WSL），各自 `jq` 可用 | 兩邊各跑 `bash tests/confirm_cleanup_test.sh`，輸出去掉時間後 `diff` | 零差異：每個案例的標籤與 `ok (...)` 行都相同；兩邊結尾都是 `all passed`，exit 0 | 自動：`tests/confirm_cleanup_test.sh`（base／head 輸出對比貼進 ledger） |
| TC-002 | 計畫 T2；「判定不能變」 | 功能 | 同上 | 兩邊各跑 `bash tests/confirm_launch_test.sh`，輸出去掉時間後 `diff` | 零差異；兩邊結尾都是 `all passed` | 自動：`tests/confirm_launch_test.sh` |
| TC-003 | 計畫 T2；環境事實（`$PFX` 前綴要原樣保留） | 功能 | 同上 | 兩邊各跑 `bash tests/confirm_cleanup_behind_heredoc_test.sh`（它會在大 here-doc 後整個重跑 cleanup 測試），輸出對比 | 零差異；兩邊都通過；該檔本身不在 diff 內 | 自動：`tests/confirm_cleanup_behind_heredoc_test.sh` |
| TC-004 | 作法 1（鍵名與 python 版逐一對應）；`$PFX` 前綴 | 功能 | 在 base 與 head 的副本裡，把 `hooks/confirm_cleanup.sh` 最前面加一行「把 stdin 追加存到檔案，再原樣交給原邏輯」；測試照常能跑完 | 兩邊各跑一次 `confirm_cleanup_test.sh`，把記錄檔每一行用 `jq -S -c .` 正規化後逐行比對 | 兩邊筆數相同、順序相同、每一筆正規化後完全相等（含 `tool_name`＝`PowerShell`／`mcp__win__powershell`、`cwd`、`script_block` 這些變體鍵）；不是只比「有檔案」 | 手動：閱卷時執行，指令與輸出貼進 `specs/hook-tests-jq/ledger.md` |
| TC-005 | 作法 1；`tool_name`／`cwd`／`script_block` 變體 | 功能 | 同 TC-004，對象是 `hooks/confirm_launch.sh` | 兩邊各跑 `confirm_launch_test.sh`，同法記錄並正規化比對 | 筆數、順序、每筆內容都相等（含 `idg` 等的 `tool_name:"Bash"`、`tool_input` 內非 `command` 的鍵） | 手動：同上 |
| TC-006 | 完成標準「案例數與 base 相同」 | 功能 | base 與 head | 對兩個檔各數 `grep -c '^t "'`，並數 `tc`／`askcheck`／`denycheck`／`tps`／`idg`／`envp`／`envq`／`msys_*` 等所有案例呼叫行，兩邊比對 | 所有計數與 base 完全相同（cleanup 的 `^t "` 為 324、launch 為 139）；沒有任何案例被刪、跳過、註解掉或放寬；沒有新增永久案例 | 手動：閱卷時執行，輸出貼進 ledger |
| TC-007 | 作法 4；範圍「只改 helper 內組輸入／讀答案」 | 功能 | head 對 base 的 `git diff`（兩個測試檔） | 逐個 hunk 檢查 | 每個改動 hunk 都落在計畫列出的行所屬的 helper 內，且只動編碼／解碼那幾行；`printf` 標籤、`ok (...)`／`FAIL: ...` 文字、`fails` 計數、`PFX`、任何案例的指令字串／期望／標籤一字不變 | 手動：閱卷時讀 diff，結論寫進 ledger |
| TC-008 | 計畫 T5（裁決二第 3 點）；cleanup | 功能 | head 的 `tests/confirm_cleanup_test.sh` | 檢查計畫列出的行（33、35、93、232、237、242、247、296、298、423、425、782、784、889、892）所屬的 helper | 這些 helper 內不再有 `python3 -c`；檔內其餘 `python3 -c` 行（含 `bj()`、被測指令字串如 :327／:353／:643、一次性呼叫）與 base 逐字相同 | 手動：`grep -n 'python3 -c'` 前後對照，貼進 ledger |
| TC-009 | 計畫 T5（裁決二第 3 點）；launch | 功能 | head 的 `tests/confirm_launch_test.sh` | 檢查 `t`〔:67〕、`idg`〔:624〕、`askcheck`／`nodecisioncheck`〔:366-389〕、`msys_ask`／`msys_pass`〔:423-449〕、`envp`／`envq`／`envq_txt`／`envq_order`／`envw`〔:792-864〕 | 這些 helper 內不再有 `python3 -c`；清單以外的 `python3 -c` 行（如 :157、:178、:322 起、:1101）與 :1185-1195 的 here-doc 產生區塊與 base 逐字相同 | 手動：同上 |
| TC-010 | 計畫 T6；陷阱 (2) | 功能 | head 的新編碼寫法 | 一次性：用新編碼處理含中文、`"`、`\`、`\r`、換行、單引號的指令字串；`jq -e .` 解析，並取 `.tool_input.command` 與原字串比對（同字串用 base 的 python 編碼再比正規化結果） | 能被 `jq -e .` 解析；`.tool_input.command` 與原字串逐字相等；與 base 編碼的正規化結果相同 | 手動：一次性，步驟與輸出貼進 ledger（裁決二第 5 點：不新增永久案例） |

## User Story 2 — 不能假綠（優先度 P1）

> 維護者的要求：「不能假綠」。換成 jq 之後，守門員答錯或亂答時，測試必須跟以前一樣變紅。以下全部在**暫存目錄的副本**做（把 `tests/` 與 `hooks/` 整份複製，改副本裡的 hook，跑副本的測試；`H=` 寫死，不能用環境變數覆寫）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 計畫 T3；陷阱 (1) | 例外 | 副本的 `hooks/confirm_cleanup.sh` 改成對任何輸入都只輸出 `{}` | 跑副本的 head 版 `confirm_cleanup_test.sh` | 期望 `warn` 的案例逐條顯示 `FAIL`（不得有任何 `ok (warn)`）；`fails` > 0、結尾 `N failed`、exit 1（缺 `hookSpecificOutput` 不得被當成 `warn`） | 手動：閱卷時執行，輸出貼進 ledger |
| TC-012 | 計畫 T4 | 例外 | 副本 hook 改成永遠不輸出（全部放行） | 跑副本的 head 版 `confirm_cleanup_test.sh` | base 輸出中期望 `deny`／`ask`／`warn` 的案例在這裡全數 `FAIL`（張數等於 base 的該類案例數）；期望 `pass` 的仍 `ok`；結尾 `N failed`、exit 1 | 手動：同上 |
| TC-013 | 計畫作法 2（答案不是 JSON → 值為空 → 案例 FAIL） | 例外 | 副本 hook 改成對任何輸入輸出一行非 JSON 的字（如 `garbage`） | 跑副本的 head 版 `confirm_cleanup_test.sh` | 所有期望非 `pass` 的案例都 `FAIL`（讀不到決定，不得變成 `warn` 或 `ok`）；exit 1 | 手動：同上 |
| TC-014 | 計畫作法 2（有 `hookSpecificOutput` 才給 `warn` 預設）；與 base 行為一致 | 功能 | 副本 hook 改成永遠輸出 `{"hookSpecificOutput":{}}`（有鍵、沒有 `permissionDecision`） | 跑副本的 head 版與 base 版 `confirm_cleanup_test.sh` | 兩邊逐案例結果相同：期望 `warn` 的案例 `ok (warn)`，期望 `deny`／`ask` 的案例 `FAIL`；head 沒有因為嚴格版而讓 `warn` 案例誤紅 | 手動：同上 |
| TC-015 | 計畫 T3／裁決二第 6 點（對 launch 同樣突變） | 例外 | 副本的 `hooks/confirm_launch.sh` 改成永遠不輸出（以副本內能跑的方式複製其依賴） | 跑副本的 head 版 `confirm_launch_test.sh` | 期望 `gate`／`ask` 的案例（`t`、`askcheck`、`msys_ask`、`idg`、`envp`／`envq` 的 `has`）全數 `FAIL`；期望 `pass` 的 `ok`；結尾 `N failed`、exit 1 | 手動：同上 |
| TC-016 | 同上 | 例外 | 副本 launch hook 改成對任何輸入只輸出 `{}` | 跑副本的 head 版 `confirm_launch_test.sh` | `askcheck`／`msys_ask` 的案例都 `FAIL`（開頭是 `{` 但決定為空，不得算 `ask`）；exit 1 | 手動：同上 |
| TC-017 | 同上 | 例外 | 副本 launch hook 改成輸出 `{"hookSpecificOutput":{"permissionDecision":"allow"}}` | 跑副本的 head 版 `confirm_launch_test.sh` | `askcheck`／`msys_ask` 的案例 `FAIL`（決定是 `allow`）；`nodecisioncheck`／`msys_pass` 的案例也 `FAIL`（不該有決定的指令出現了決定）；exit 1 | 手動：同上 |
| TC-018 | 計畫裁決二第 7 點（reason 照樣解碼、不去 `\r`） | 例外 | 副本 launch hook 改成輸出 `permissionDecision:"ask"` 但 `permissionDecisionReason` 不含完整指令（也不含 `on_site.sh`） | 跑副本的 head 版 `confirm_launch_test.sh` | `askcheck` 顯示 `FAIL: reason did not contain the full command`、`msys_ask` 顯示 `FAIL: reason did not name on_site.sh`；證明 reason 的解碼真的讀到欄位 | 手動：同上 |
| TC-019 | T3／T4 的對照組 | 功能 | 把 `tests/` 與 `hooks/` 整份複製到暫存目錄，**不做任何突變** | 在副本跑 head 版 `confirm_cleanup_test.sh` 與 `confirm_launch_test.sh` | 兩個都 `all passed`，exit 0（證明 TC-011 至 TC-018 的紅是突變造成，不是副本沒複製完整） | 自動：`tests/confirm_cleanup_test.sh`、`tests/confirm_launch_test.sh`（在副本內） |
| TC-020 | 計畫作法 2（讀的是 `permissionDecision` 這個欄位本身） | 例外 | 副本 cleanup hook 改成對任何輸入輸出 `{"hookSpecificOutput":{"permissionDecision":"deny"}}` | 跑副本的 head 版 `confirm_cleanup_test.sh` | 期望 `pass`／`warn`／`ask` 的案例都 `FAIL`；只有期望 `deny` 的案例 `ok`；exit 1 | 手動：同上 |

## User Story 3 — 範圍、整套綠、速度證據（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 計畫 T8；範圍（只准改 3 個檔） | 功能 | head 分支 | `git diff --name-only <含計畫的 commit>...HEAD`（不含合約流程加入的 `plan.md`、`test-case*.md`） | 只有 `tests/confirm_cleanup_test.sh`、`tests/confirm_launch_test.sh`、`specs/hook-tests-jq/ledger.md`；`hooks/` 零改動；`spec`／`test-case*.md` 沒被實作者改過 | 手動：指令輸出貼進 ledger |
| TC-022 | 完成標準 | 功能 | WSL，head 乾淨 checkout | 跑整套 `bash tests/run_all.sh`；另單獨跑 `gate_output_failclosed_test.sh`、`gate_process_count_test.sh`、`confirm_cleanup_candidates_timing_test.sh`、`confirm_cleanup_behind_heredoc_test.sh` | 整套綠，這四個檔沒改且各自通過（`jev_test.sh`、`constitution_scope_test.sh`、`platform_direction_docs_test.sh` 只在無 `.git` 的 archive 副本才紅，真 worktree 不應紅） | 自動：`tests/run_all.sh` |
| TC-023 | 計畫 T7 | 功能 | 同一台機器、同樣負載 | `confirm_cleanup_test.sh` 在 base 與 head 各連跑 3 次，記中位數 | ledger 有改前改後 3 次的秒數與中位數；少 ≥ 20% 則記錄，< 10% 則 ledger 有說明原因。**速度不是通過／失敗條件** | 手動：ledger |
| TC-024 | 計畫範圍（ledger 含計時與兩版輸出比對） | 功能 | head | 讀 `specs/hook-tests-jq/ledger.md` | 含：TC-001／002／003 的 base／head 輸出比對結論、TC-004／005 的輸入記錄比對、TC-011 至 TC-020 突變結果、TC-021 指令輸出、TC-023 計時；不是只有標題 | 手動：讀檔 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 計畫「不做」：不平行化案例；作法 5 | 不在範圍 | head 的 diff | 檢查 diff 是否引入 `&`／`wait`／`xargs -P`／`parallel`／背景工作，並比對 TC-001／002 輸出的案例順序 | 沒有任何平行化；案例順序與 base 完全相同 | 手動：讀 diff，結論寫進 ledger |
| TC-026 | 計畫「不做」：不改 `run_all.sh`、不動 `on_site_parallel_test.sh`；不准動清單 | 不在範圍 | head 的 diff | 檢查 `tests/run_all.sh`、`tests/on_site_parallel_test.sh`、`tests/lib/**`、`tests/confirm_cleanup_behind_heredoc_test.sh`、`tests/flow_skills_layout_test.sh`、`.github/` | 全部零改動；`run_all.sh` 沒有 `--jobs`；`flow_skills_layout_test.sh` 照常通過（兩個檔名沒變） | 手動：`git diff --stat` 貼進 ledger；`flow_skills_layout_test.sh` 另自動 |
| TC-027 | 計畫「不做」：不動 hook | 不在範圍 | head 的 diff | `git diff <base>...HEAD -- hooks/` | 輸出為空 | 手動：指令輸出貼進 ledger |
| TC-028 | 計畫作法 3 / 裁決「只改熱路徑 helper」 | 不在範圍 | head 的 diff | 檢查不在計畫行清單內的 python 呼叫：cleanup 的 :119、:167（`bj()`）、:208-219、:261、:403、:599；launch 的 :1185-1195 here-doc 產生區塊 | 這些行與 base 逐字相同，沒有被順手改成 jq | 手動：讀 diff，結論寫進 ledger |
| TC-029 | 計畫「不需要 migration」 | 不在範圍 | head 的 diff | 檢查是否有資料結構、設定檔格式、資料內容或 migration 檔的改動 | 沒有；diff 只含測試檔與 ledger | 手動：讀 diff |

## 憲法與安全網

> 觸及：不變式 13（沒有 jq 時守門員不得悄悄放行也不得悄悄全擋；其 Check 就是這兩個檔的「no jq」段落）；Safety Net 的「刪除保護」與「送出前確認」（這兩個檔就是它們唯一的證明）。後者由 TC-001／002／003（base／head 對比，校準失敗 #1 的做法）與 TC-011 至 TC-020（突變）證明；下面兩條證明不變式 13 的 Check 在換編碼後仍然咬得住。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 不變式 13；Check＝`tests/confirm_cleanup_test.sh` 的 no-jq 段（含 `nojq()`〔:93〕） | 例外 | 副本 cleanup hook 改成「jq 不在時一律悄悄放行（exit 0、無輸出）」 | 跑副本的 head 版 `confirm_cleanup_test.sh` | 「(b) no jq + a real delete - still BLOCKED」與「stderr names the fix」兩條 `FAIL`；同時未突變的 head 版這兩條 `ok (rc=2, no stdout)`；且 `(a) ... exit 0, no noise` 仍要求 stderr 為空（新編碼不得在 `nojq()` 內製造雜訊） | 手動：閱卷時執行，輸出貼進 ledger |
| TC-031 | 不變式 13；Check＝`tests/confirm_launch_test.sh` 的 no-jq 段（約 :1101） | 例外 | 副本 launch hook 改成「jq 不在時悄悄放行」 | 跑副本的 head 版 `confirm_launch_test.sh` | no-jq 段對應案例 `FAIL`；未突變的 head 版同段與 base 相同、`ok` | 手動：同上 |

<!--
Rules followed: every plan check T1-T8 maps (T1→001/003, T2→002/003, T3→011, T4→012/015, T5→008/009,
T6→010, T7→023, T8→021); the 完成標準 maps to 006/022; every 「不做」 item maps to a 不在範圍 row.
IDs are never renumbered after approval.
-->
