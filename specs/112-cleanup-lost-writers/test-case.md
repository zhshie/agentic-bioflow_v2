# 測試案例：#112 清理閘門：資料夾「迷路」之後還能放行的寫檔方式

<!--
Written by the verifier (CONTRACT mode). Source: specs/112-cleanup-lost-writers/plan.md only (this is a fix; there is no spec.md). The plan's own examples and its "Contract-review rulings" are the only source of expected behaviour.
"對應需求" cites the plan's own numbering: 改動 N = "Changes" item N (1-8), 裁定 = "Contract-review rulings", 檢查 = "Checks", 不在範圍 = "Not in this PR", 規則 = "Rule (unchanged from #110)".
Notation: <run> = the test file's run folder `$P` (/work/u9613010/lab_runs/x); `rm -rf` = the delete verb `$D` (the test file assembles it from hex so its own text never trips a cleanup hook); "問" = the gate stops and asks the person (ask); "擋" = deny; "放行" = pass. "迷路" = the folder is lost: the command starts with `cd -;` so the gate cannot say where the shell is.
Unless a row says otherwise the session's current folder is `/tmp` and the command starts with `cd -;`.
"main 現況" = what the verifier measured on 2026-10-17 by feeding the same text to the unchanged hooks/confirm_cleanup.sh (WSL, jq 1.7.x, hook input with cwd /tmp). It is only written where it was actually measured.
Rows marked 「推導」 apply the plan's rule to a plain command (the plan gives the rule, not that exact sentence); nothing else is added.
"存在的資料夾" = a folder the test creates with `mktemp -d` (the plan's ruling for item 6).
The gate is only run on text; nothing here deletes or writes anything.
-->

**規格**：`specs/112-cleanup-lost-writers/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：這次要做到的事，正常情況下做到了（含「該放行的照樣放行」的對照組）。
- **例外**：資料夾不明、寫到不明資料夾時，系統怎麼反應（問、擋）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

白話背景：在 `cd -` 之後，閘門不知道自己在哪個資料夾，所以任何「可能寫到相對路徑」的指令都要先問你（#110、#111 已補大部分）。這次補剩下的幾種漏洞：檔名以 `-` 開頭、`--` 之後的檔名、被引號包起來的 `~`、`install`／`ln`／`curl -o`／`wget`／`perl -pi`／`awk -i inplace` 等新寫入者、`>(...)` 裡的指令、`cd` 到不存在的絕對資料夾、被括號／`if`／`for`／`xargs`／`find -exec` 包住的寫入者。規則只會變嚴：原本問或擋的不放寬。

## 群組 A — 以 `-` 開頭的名字是檔名，不是旗標（改動 1，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112-01 | 改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo x > -out` | 問（`-out` 是要建立的檔名；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-02 | 改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; cat a >\| -s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-03 | 改動 1（推導：寫入者的檔案運算元） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; sort -o -s1 x` | 問（`-o` 後面的 `-s1` 是輸出檔名；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-04 | 改動 1 對照組（推導：規則只談相對路徑） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; echo x > /tmp/-out` | 放行（絕對路徑不受「資料夾不明」影響；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 B — `--` 之後不再有選項（改動 2，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112-05 | 改動 2（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; tee -- -a s1` | 問（`--` 之後 `-a` 和 `s1` 都是被寫的檔名；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-06 | 改動 1＋2（推導） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; tee -- -s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-07 | 改動 2（推導：`cp` 的目的地） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; cp -- a -s1` | 問（`--` 之後 `-s1` 是目的檔名；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-08 | 改動 2 對照組（推導） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; tee -- /tmp/s1` | 放行（`--` 之後是絕對路徑；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 C — 被引號包住的 `~` 是名叫 `~` 的相對資料夾（改動 3，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112-09 | 改動 3（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo x > "~/s1"` | 問（引號裡的 `~/s1` 是相對路徑；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-10 | 改動 3（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo x > '~/s1'` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-11 | 改動 3（推導：寫入者的檔案運算元） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; cp a "~/s1"` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-12 | 改動 3 對照組（計畫：「只有沒引號、開頭的 `~` 才是家目錄」） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; echo x > ~/s1` | 放行（沒引號的 `~/` 仍是家目錄；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-13 | 改動 3 對照組 | 功能 | 目前資料夾 `/tmp` | 送 `cd -; cp a ~/s1` | 放行（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 D — 新的寫入者（改動 4＋裁定，優先度 P1）

絕對目標／輸出路徑一律放行；只有目標或輸出路徑是相對時才問（裁定「Absolute targets」）。下列「main 現況」除標示外都是放行。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112-14 | 改動 4（`install`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; install a s1` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-15 | 改動 4＋裁定（絕對目標） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; install a /tmp/s1` | 放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-16 | 改動 4（`ln -sf`，計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; ln -sf a s1` | 問（連結名 `s1` 是相對的） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-17 | 裁定（`ln` 只給一個運算元，連結建在目前資料夾） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; ln -s /tmp/a` | 問（連結會建在不明的目前資料夾） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-18 | 裁定（絕對目標） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; ln -s /tmp/a /tmp/s1` | 放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-19 | 改動 4（`shuf -o`，計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; shuf -o s1 x` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-20 | 裁定（絕對輸出） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; shuf -o /tmp/o x` | 放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-21 | 改動 4（`split`；推導：相對前綴） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; split f p_` | 問（輸出檔 `p_aa…` 寫在相對位置） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-22 | 裁定（絕對輸出） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; split f /tmp/p_` | 放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-23 | 改動 4（`curl -o`，計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; curl -o s1 http://x` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-24 | 改動 4（`curl --output`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; curl --output s1 http://x` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-25 | 改動 4（`curl -O`：用遠端檔名寫進目前資料夾） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; curl -O http://x/f` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-26 | 裁定（絕對輸出） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; curl -o /tmp/s1 http://x` | 放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-27 | 裁定（`curl` 沒有 `-o`／`-O` 只寫到標準輸出） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; curl http://x` | 放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-28 | 改動 4（`wget -O`，計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; wget -O s1 http://x` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-29 | 改動 4（`wget --output-document`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; wget --output-document s1 http://x` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-30 | 改動 4＋裁定（裸 `wget` 寫進目前資料夾） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; wget http://x` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-31 | 裁定（`wget -O -` 寫到標準輸出） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; wget -O - http://x` | 放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-32 | 裁定（絕對輸出） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; wget -O /tmp/o http://x` | 放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-33 | 改動 4（`perl -pi`，計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; perl -pi -e 's/a/b/' s1` | 問（原地修改相對檔） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-34 | 改動 4（`perl -i`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; perl -i -ne 'print' s1` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-35 | 改動 4（`awk -i inplace`，計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; awk -i inplace '{print}' s1` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-36 | 改動 4（`gawk -i inplace`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; gawk -i inplace '{print}' s1` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-37 | 規則對照組（資料夾已知，不迷路） | 功能 | 目前資料夾 `/tmp`（沒有 `cd -`） | 送 `install a s1` | 放行（資料夾已知時，判定與 main 相同） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-38 | 規則對照組（資料夾已知） | 功能 | 目前資料夾 `/tmp`（沒有 `cd -`） | 送 `wget http://x` | 放行 | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 E — 行程替換 `>(...)`／`<(...)`：裡面的指令自己被檢查（改動 5，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112-39 | 改動 5（計畫原例；裁定：必須保持會問） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo x > >(tee s1)` | 問（main 現況：問；紀錄寫「main 問、這裡也問」，不算紅轉綠） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-40 | 改動 5（計畫原例；裁定：必須保持會問） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; cat <(tee s1)` | 問（main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-41 | 改動 5＋2（推導：裡面的指令當獨立指令檢查） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo x > >(tee -- -a s1)` | 問（內層 `tee -- -a s1` 單獨看就會問；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 F — `cd /絕對路徑` 只有在該資料夾真的存在時才解除「迷路」（改動 6，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112-42 | 改動 6；裁定（TC-110-66 由放行翻為問） | 例外 | 目前資料夾 `/tmp`；`/no/such/dir` 不存在 | 送 `cd -; cd /no/such/dir; rm -rf s1` | 問（不存在的資料夾不算回到已知位置；main 現況：放行）；`tests/confirm_cleanup_test.sh` 內 TC-110-66 那一行的期望由 pass 改為 ask | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-43 | 改動 6 對照組 | 功能 | 目前資料夾 `/tmp`；測試用 `mktemp -d` 建一個存在的資料夾 | 送 `cd -; cd <存在的資料夾>; rm -rf s1` | 放行（絕對 cd 到真的資料夾，解除迷路） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-44 | 改動 6（推導：迷路狀態對寫檔也成立） | 例外 | 目前資料夾 `/tmp`；`/no/such/dir` 不存在 | 送 `cd -; cd /no/such/dir; echo x > s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-45 | 改動 6 對照組（推導） | 功能 | 目前資料夾 `/tmp`；測試用 `mktemp -d` 建一個存在的資料夾 | 送 `cd -; cd <存在的資料夾>; echo x > s1` | 放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-46 | 裁定（資料夾已知時，cd 到不存在的絕對路徑不變）；`confirm_cleanup_shapes.txt:237` | 功能 | 目前資料夾 `/tmp` | 送 `cd <run>; cd results; cd /nonexistent; rm -rf x`（形狀檔該列） | 放行（這一列維持 pass；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh`（讀 `tests/confirm_cleanup_shapes.txt`） |
| TC-112-47 | 裁定（TC-078-19、TC-104-19 改寫） | 功能 | — | 看 diff 與 `specs/112-cleanup-lost-writers/ledger.md` | TC-078-19 與 TC-104-19 兩行改成用 `mktemp -d` 的存在資料夾，期望仍是 pass；ledger 對 TC-110-66、TC-078-19、TC-104-19 各寫出「舊期望、新期望、理由」；這三行以外沒有任何既有期望被改 | 手動：`docs/TESTING.md`（核對 ledger 與 `git diff` 的步驟） |

## 群組 G — 被包住的寫入者也要被檢查（改動 7，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112-48 | 改動 7（子 shell；裁定：必須保持會問） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; ( cp a s1 )` | 問（main 現況：問；紀錄寫「main 問、這裡也問」） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-49 | 改動 7（大括號群組，計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; { tee s1; }` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-50 | 改動 7（`if/then/fi`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; if true; then cp a s1; fi` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-51 | 改動 7（`else` 分支） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; if false; then echo; else cp a s1; fi` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-52 | 改動 7（`for ... do ... done`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; for i in 1; do cp a s1; done` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-53 | 改動 7（`while ... do ... done`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; while true; do cp a s1; done` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-54 | 改動 7（`xargs tee`，計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo a \| xargs tee` | 問（`xargs` 會把未知的參數接在後面） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-55 | 裁定（`xargs` 即使字面運算元看起來是絕對路徑也問） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo a \| xargs cp /tmp/a` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-56 | 改動 7（`find -exec`，計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; find . -exec cp a {} \;` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-57 | 改動 7（`find -execdir`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; find . -execdir cp a {} \;` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-58 | 改動 7（`find -ok`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; find . -ok cp a {} \;` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 H — 兩套重新導向掃描合併，重複的原因只印一次（改動 8，優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112-59 | 改動 8 | 功能 | 目前資料夾 `/tmp` | 送 `cd -; echo x > s1`，讀閘門回的原因文字 | 判定仍是問；原因文字裡 "overwrite s1" 只出現 1 次（main 現況：出現 2 次） | 自動：`tests/confirm_cleanup_test.sh`（測試要讀原因文字並計次，不能只看判定） |
| TC-112-60 | 改動 8 | 功能 | 目前資料夾 `/tmp` | 送 `cd -; echo x > s1; echo y > s2`，讀原因文字 | 判定仍是問；"overwrite s1" 與 "overwrite s2" 各出現 1 次（main 現況：各 2 次） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-61 | 改動 8（「合併成一個掃描器」） | 功能 | — | 看 `git diff` 與 `hooks/confirm_cleanup.sh` | 重新導向掃描只剩一個函式；`lost_redirects_blind` 與 `lost_redirects` 不再各自存在並重複呼叫（`hooks/confirm_cleanup.sh` 原 1368–1369 行兩次呼叫變成一次）；原本每一種會問的重新導向寫法仍由既有測試覆蓋 | 手動：`docs/TESTING.md`（讀 diff 的步驟） |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112-62 | 不在範圍：issue #112 第 7 項（大型輸入過濾器的效能） | 不在範圍 | — | 看 `git diff` 與 ledger | 大型輸入過濾器沒有被改動（diff 沒碰它；`tests/confirm_cleanup_candidates_timing_test.sh` 沒被編輯）；ledger 有一句說明「第 7 項維持原樣、已是 fail-closed」 | 手動：`docs/TESTING.md`（讀 diff 與 ledger 的步驟） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-112-63 | 安全網：絕不刪使用者來源資料（TC-078-13 不動） | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>; cd -; rm -rf results` | 擋（維持 deny，不可被放寬成問或放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-64 | 安全網：絕不刪 `results/`（TC-110-71 不動） | 例外 | 目前資料夾 `/tmp` | 送 `rm -rf <run>/results` | 擋 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-65 | 安全網：刪 `work/` 要使用者明確確認 | 例外 | 目前資料夾 `/tmp` | 送 `rm -rf <run>/work` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-112-66 | 計畫「檢查」：只會變嚴，不放寬 | 功能 | — | 跑 `specs/110-cleanup-gate-rest/replay.tsv` 對 main 與本分支，看 ledger | 「問／擋 → 放行」的轉變為 0 條；所有「放行 → 問」的轉變都列在 ledger（每條都屬於本計畫改動 1–8 的某一種寫法） | 手動：`docs/TESTING.md`（比對 replay 結果的步驟） |
| TC-112-67 | 計畫「檢查」；憲法 Development Workflow（測試不得被放鬆） | 功能 | — | 比對 `tests/confirm_cleanup_test.sh`、`tests/confirm_cleanup_shapes.txt`、`tests/confirm_cleanup_shapes_main.txt` 與 main 的 diff | 沒有任何既有斷言被刪、被跳過、被放寬；唯一被改的既有期望是計畫點名的三行（TC-110-66 改問；TC-078-19、TC-104-19 改用存在的資料夾，仍放行）；`confirm_cleanup_shapes.txt:237` 仍是 pass | 手動：`docs/TESTING.md`（讀 diff 的步驟） |
| TC-112-68 | 計畫「檢查」；憲法 Development Workflow（每階段全綠） | 功能 | WSL，jq 1.6 與 1.7.1 各排在 PATH 最前面跑一次 | 跑 `bash tests/run_all.sh` | 全綠，含 `confirm_cleanup_behind_heredoc_test.sh`（同一批案例放在大型 here-doc 之後仍得到同樣判定）、`confirm_cleanup_candidates_timing_test.sh`、`gate_process_count_test.sh`、`jq_versions_test.sh` | 自動：`tests/run_all.sh` |
| TC-112-69 | 憲法第 13 條：安全網做不到時要說（沒有 jq／jq 壞掉） | 例外 | `confirm_cleanup_test.sh` 的「no jq」段落 | 跑 `bash tests/confirm_cleanup_test.sh` | 「no jq」段落全部通過且該段沒被編輯 | 自動：`tests/confirm_cleanup_test.sh` |
