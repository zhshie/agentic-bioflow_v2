# 測試案例：其他測試腳本裡同一種時好時壞（pipefail＋grep -q）一次掃掉（pipefail-grep-q-sweep）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
本任務沒有 spec.md，依據是 `specs/pipefail-grep-q-sweep/plan.md`；「User Story」在此對應計畫的各段。
-->

**規格**：`specs/pipefail-grep-q-sweep/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

名詞先講白：`pipefail` 是 bash 的一個開關，開了之後「一條用 `|` 接起來的指令」只要任何一段失敗就算整條失敗。`grep -q` 是「找到就立刻結束、不印東西」的 grep。兩個湊在一起，前一段（例如 printf）還在寫字，grep 已經走了，前一段就會收到 Broken pipe 而失敗，於是「字明明在卻判成找不到」。這就是 #231 查出的根因。修法是把 `-q` 拿掉、改把輸出丟進 `/dev/null`，讓 grep 把字讀完。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、不該放行的情況，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

驗證方式：「自動」＝`tests/` 底下的測試檔跑出來；「手動」＝閱卷者看 diff 或看 `specs/pipefail-grep-q-sweep/ledger.md` 裡的證據。本任務的檔案範圍不含 `docs/TESTING.md`，所以手動條目的步驟與證據都放在 ledger.md（同 constitution-scope-flake 的做法）。

「改寫」的標準形式（下面多條會用到）：`X | grep -q… 樣式` 變成 `X | grep …（去掉 q）樣式 >/dev/null`，其他旗標、樣式、比對字串一字不改。

## User Story 1 — 守門測試 `tests/no_pipefail_grep_q_test.sh`，防止再寫回來（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 3；「檔首照慣例寫為什麼」 | 功能 | 守門測試檔已新增 | 閱卷者讀 `tests/no_pipefail_grep_q_test.sh` 的檔首註解 | 檔首用白話寫出：是什麼寫法、為什麼會時好時壞（grep 先走、前一段收到 Broken pipe、pipefail 判整條失敗）、出處 #231 | 手動：閱卷者讀檔；結果記在 ledger.md |
| TC-002 | 失敗先行測試第 1 條 | 功能 | 把守門測試放進尚未掃除的 v3（掃除之前的樹） | 執行 `bash tests/no_pipefail_grep_q_test.sh` | 結束碼不是 0，輸出列出違規的檔名，名單至少包含 `tests/jev_test.sh` 與 `tests/platform_direction_docs_test.sh`；這次紅燈的輸出貼在 ledger.md | 手動：ledger.md 附 RED 的輸出與 commit |
| TC-003 | 作法 3；完成標準第 1 條 | 功能 | 掃除已完成 | 在 `tests/*.sh` 的真實樹上執行守門測試 | 全部通過、結束碼 0 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-004 | 作法 3 自我測試 1；樣式 `grep -q` | 功能 | 暫存檔：開頭 `set -o pipefail`，內有 `printf x \| grep -q x` | 守門測試的檢查函式掃這個暫存檔 | 判為違規（紅），檔名被點出 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-005 | 作法 3；樣式 `grep -qF` | 功能 | 暫存檔：有 pipefail，內有 `printf x \| grep -qF x` | 掃描 | 判為違規 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-006 | 作法 3；樣式 `grep -iq` | 功能 | 暫存檔：有 pipefail，內有 `printf x \| grep -iq x` | 掃描 | 判為違規 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-007 | 作法 3；樣式 `grep -F -q` | 功能 | 暫存檔：有 pipefail，內有 `printf x \| grep -F -q x` | 掃描 | 判為違規 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-008 | 作法 3；樣式 `grep -E -q` | 功能 | 暫存檔：有 pipefail，內有 `printf x \| grep -E -q x` | 掃描 | 判為違規 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-009 | 範圍「旗標含 q」；真實樣本 `tests/hosted_deploy_test.sh:129` 的 `grep -vqE` | 功能 | 暫存檔：有 pipefail，內有 `printf x \| grep -vqE x` | 掃描 | 判為違規（q 不在旗標最前面也要抓到） | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-010 | 範圍「旗標含 q」；真實樣本 `tests/skills_name_the_v3_launch_path.sh:28` 的 `grep -qvx` | 功能 | 暫存檔：有 pipefail，內有 `printf x \| grep -oE x \| grep -qvx y` | 掃描 | 判為違規 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-011 | 範圍；真實樣本 `tests/wsl_bridge_test.sh:282`（`\|` 在續行行首） | 功能 | 暫存檔：有 pipefail，內有一行以 `\| grep -qE "x"` 開頭的續行 | 掃描 | 判為違規 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-012 | 作法 3 自我測試 2 | 功能 | 暫存檔：有 pipefail，內有 `printf x \| grep -F x >/dev/null`（乾淨寫法） | 掃描 | 判為乾淨（綠） | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-013 | 作法 3「凡是檔內有 pipefail 的」 | 功能 | 暫存檔：沒有 pipefail，內有 `printf x \| grep -q x` | 掃描 | 不判違規 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-014 | 作法 2；直接讀檔的寫法不用改 | 功能 | 暫存檔：有 pipefail，內有 `grep -q x "$FILE"`（沒有管線） | 掃描 | 不判違規 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-015 | 作法 2；真實樣本 `tests/no_second_run_state_test.sh:262`（`\|\| grep -qE … <<<"$out"`） | 功能 | 暫存檔：有 pipefail，內有 `[ "$a" = "-" ] \|\| grep -qE x "$f"`（`\|\|` 是「或」，不是管線） | 掃描 | 不判違規 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-016 | 作法 3「`\|` 之後接 grep 且旗標含 q」；真實樣本 `tests/constitution_scope_test.sh:249` | 功能 | 暫存檔：有 pipefail，內有 `a \| grep 'FAIL' >/dev/null && grep -qE x "$f"`（管線後的 grep 沒有 q，q 在 `&&` 後面讀檔） | 掃描 | 不判違規 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-017 | 作法 3「排除它自己」 | 功能 | 守門測試檔本身為了自我測試而含有違規寫法的字樣 | 在真實樹上執行守門測試 | 不因為自己檔內的範例而紅（結果同 TC-003）；掃描清單中沒有它自己 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-018 | 失敗先行測試第 1 條「列出違規檔」 | 例外 | 暫存目錄放一個違規檔、一個乾淨檔 | 守門測試掃這個目錄 | 結束碼不是 0；輸出只點名違規檔，不點名乾淨檔 | 自動：`tests/no_pipefail_grep_q_test.sh` |
| TC-019 | 目標「防止再寫回來」 | 功能 | 守門測試已新增，`tests/run_all.sh` 與 `tests/quarantine.txt` 沒動 | 在 WSL 執行 `bash tests/run_all.sh --list`，看清單 | 清單含 `no_pipefail_grep_q_test.sh`，且它不在 quarantine.txt 裡（所以真的會在每次全套與 CI 裡跑） | 手動：ledger.md 附 `--list` 輸出 |

## User Story 2 — 把其他測試腳本裡的同一種寫法一次改掉（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 作法 1；完成標準第 2 條「比對字串與預期值一個都沒動」 | 功能 | 掃除完成 | 閱卷者對每一個被改的檔跑 `git diff <base>...HEAD`，逐行把新行還原（把 `>/dev/null` 拿掉、把 q 放回旗標）再與舊行比 | 每一行都完全等於舊行：被改動的只有旗標裡的 q 和新增的 `>/dev/null`；樣式、比對字串、`--`、`-e`、預期值一字不差；沒有被刪掉的行、沒有新增的行（只有守門測試與 ledger 是新檔） | 手動：閱卷者逐行比對；結論記在 ledger.md |
| TC-021 | 作法 1「其他旗標一字不改」 | 功能 | 掃除完成 | 看 diff 裡旗標有多個字母的行：`-qF`→`-F`、`-qE`→`-E`、`-qiE`→`-iE`、`-iq`→`-i`、`-vqE`→`-vE`、`-qvx`→`-vx`；只有 `-q` 的（`grep -q .`、`grep -q OK`）→ 整個旗標拿掉 | 只去掉 q 這個字母；剩下的字母順序不變；沒有留下單獨的 `-`；沒有誤刪 `--` | 手動：閱卷者看 diff |
| TC-022 | 作法 1；`>/dev/null` 放的位置 | 功能 | 掃除完成 | 對每一個被改的檔執行 `bash -n <檔>`（只檢查語法、不執行） | 全部語法正確；`>/dev/null` 放在 grep 那段指令的後面、`;`／`&&`／`\|\|`／`)`／行尾 `\`／`then` 之前（例：`tests/wsl_bridge_test.sh` 的續行、`tests/skills_name_the_v3_launch_path.sh:52` 的行尾 `\`），以及放在 `bash -c '…'` 單引號字串裡的（`tests/run_all_retry_test.sh`）也正確 | 手動：閱卷者逐檔 `bash -n`，結果記在 ledger.md |
| TC-023 | 作法 1「`if`／`&&`／`\|\|` 的邏輯不變」 | 功能 | 掃除完成 | 看 diff 裡含 `if`、`&&`、`\|\|`、前面有 `!`（取反）的行（例：`tests/hosted_deploy_test.sh:132`、`tests/run_all_retry_test.sh:367`、`tests/skill_runs_uses_actions_test.sh:131`） | 這些行的 `if`／`&&`／`\|\|`／`!`、then／else 分支與 ok／bad 訊息全都沒動，只有 grep 那段被改寫 | 手動：閱卷者看 diff |
| TC-024 | 作法 2「直接讀檔、沒有管線的不用改」 | 功能 | 掃除完成 | 看 diff，找沒有管線的 `grep -q 樣式 檔案`（例：`tests/hosted_deploy_test.sh:150`、`tests/no_second_run_state_test.sh:262`、`tests/constitution_scope_test.sh` 的 `has()`） | 這些行沒有出現在 diff 裡（沒有被順手改） | 手動：閱卷者看 diff |
| TC-025 | 作法 4；完成標準第 2 條「所有改過的腳本單跑綠」 | 功能 | 掃除完成 | 在 WSL，對每個被改的檔各執行一次 `bash tests/<檔>.sh` | 每一個都結束碼 0、最後是全部通過的那一行；ledger.md 每個檔一列，記結束碼 | 手動：ledger.md 的逐檔表，閱卷者可重跑任一檔 |
| TC-026 | 作法 4「ledger 列出改了哪些檔、各幾處」 | 功能 | 掃除完成 | 閱卷者把 ledger.md 的檔案清單與每檔處數，對照 diff 裡每檔被去掉 q 的 `grep` 個數 | 清單的檔案與 diff 裡被改的測試檔完全一致（不多不少）；每檔處數等於 diff 實際數；ledger 寫明「處」是怎麼算的（同一行兩個 grep 算兩處或一處，要寫明） | 手動：閱卷者數 diff |
| TC-027 | 失敗先行測試第 2 條「例：platform_direction_docs_test.sh，15 處」 | 功能 | 掃除完成 | 數 `tests/platform_direction_docs_test.sh` 裡 `\| grep -q…` 的個數：改前與改後 | 改前 15 處、改後 0 處；ledger.md 記 15 | 手動：閱卷者對 base 與 HEAD 各數一次 |
| TC-028 | 範圍；#231 已修過的 `tests/constitution_scope_test.sh` | 功能 | 掃除完成 | 看該檔的 diff，並執行 `bash tests/constitution_scope_test.sh` | 不是註解的行一行都沒動；既有 `flake TC-014` 仍然通過；整支綠。若只動了第 24 行附近的註解字樣，也可（註解不是斷言） | 自動：`tests/constitution_scope_test.sh`（既有）；diff 由閱卷者看 |
| TC-029 | 範圍；`tests/no_second_run_state_test.sh:238` 的 `case_ "an until/sleep polling loop fails" 1 …` 是餵給偵測器的字串資料，不是真的在跑的管線 | 功能 | 掃除完成 | 執行 `bash tests/no_second_run_state_test.sh`，看該案例 | 案例名稱「an until/sleep polling loop fails」仍在、預期值仍是 1（偵測器要判失敗）、整支綠；不論這一處有沒有被改，都不許案例消失或預期值改變 | 自動：`tests/no_second_run_state_test.sh`（既有） |

## User Story 3 — 壓測證明不再誤判（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 失敗先行測試第 2 條「改前若能重現誤判就貼數字」 | 功能 | 在 WSL，改前（base）的 `tests/platform_direction_docs_test.sh` | 8 份同時、各跑 200 次（共 1600 次），記錄誤判（紅）次數 | ledger.md 貼出：怎麼跑的（8 份是各自獨立的副本還是同一份，要寫明）、總次數、紅的次數。若重現不了，就寫「重現不了」與實際次數，不得省略這一格 | 手動：ledger.md |
| TC-031 | 失敗先行測試第 2 條「改後 0 次」 | 功能 | 在 WSL，改後的同一支檔，同樣條件 | 8 份同時、各跑 200 次（共 1600 次） | 紅 0 次；ledger.md 貼出同一格式的總次數與 0 | 手動：ledger.md |

## User Story 4 — 不在範圍／禁止的事（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 範圍「不准動 `tests/run_all.sh`」；不做「不改 run_all 的 FLAKY 判定」 | 不在範圍 | 實作完成 | `git diff <base>...HEAD -- tests/run_all.sh` | 沒有任何差異 | 手動：閱卷者執行 |
| TC-033 | 維護者原話「Fix the test, or add one line per file to tests/quarantine.txt」→ 一律 Fix the test；範圍「不准動 `tests/quarantine.txt`」 | 不在範圍 | 實作完成 | `git diff <base>...HEAD -- tests/quarantine.txt` | 沒有任何差異（沒有加隔離名單） | 手動：閱卷者執行 |
| TC-034 | 範圍「不准動 `hooks/*`、`.github/*`、憲法、任何非 tests/ 的檔」 | 不在範圍 | 實作完成 | `git diff --name-only <base>...HEAD`，另加未提交的 `git status --porcelain` | 變動的檔只有：`tests/*.sh`（被改的測試）、`tests/no_pipefail_grep_q_test.sh`、`specs/pipefail-grep-q-sweep/` 底下的檔；`hooks/`、`.github/`、`.specify/memory/constitution.md`、`docs/`、`scripts/` 都沒有 | 手動：閱卷者執行 |
| TC-035 | 範圍「`tests/*.sh` 中同時有 pipefail 與管線接 grep -q 的檔：只改那些」 | 不在範圍 | 實作完成；有些測試檔有 `grep -q` 管線但整檔沒有 `pipefail` | 對沒有 `pipefail` 字樣的 `tests/*.sh`（例：`confirm_launch_test.sh`、`package_gaps_test.sh`、`report_facts_test.sh`、`build_package_test.sh`、`reset_master_test.sh`）看 diff | 這些檔沒有任何差異 | 手動：閱卷者執行 |
| TC-036 | 不做「不加重試」；完成標準「不放寬」 | 不在範圍 | 實作完成 | 看整個 diff 有沒有新增重試迴圈、`sleep` 等待、跳過案例（`continue`／`return`／`skip`）、放寬的比對樣式 | 都沒有；被改的行只有 TC-020 說的那兩種改動 | 手動：閱卷者看 diff |

## 憲法與安全網

<!-- 本任務只動測試腳本，但會碰到「全綠才准停」與「不放鬆安全網」兩條。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-037 | Development Workflow：「`bash tests/run_all.sh` fully green」；維護者原話「全綠才准停」 | 功能 | 實作完成、已提交 | 在 WSL 於 worktree 執行 `bash tests/run_all.sh`；閱卷者另查完成記號 `executor-status` | 全套綠、沒有 FLAKY（沒有「第一次紅、重跑綠」）；完成記號是 `GREEN <HEAD sha>` 且工作樹乾淨 | 手動：完成記號＋ledger.md 的全套結果 |
| TC-038 | Safety Net：「loosens the Safety Net 是維護者的決定」→ 改寫不得讓斷言變弱 | 功能 | 掃除完成 | 閱卷者挑 3 處改過的斷言（不同檔、不同旗標形狀），在暫存副本裡把「預期要找到的字串」換成一個肯定不存在的字串，再跑該檔 | 該斷言變紅（失敗）；換回原字串變綠。證明去掉 q 之後，斷言仍會在字串不在時報錯 | 手動：閱卷者在暫存副本操作，結果記在 ledger.md |

## 專長守則（backend）

<!-- 計畫的專長守則條目中，本任務（只動測試腳本、不碰網頁／API／聊天指令）適用的只有兩條。動作層對等性、跨使用者讀寫、人工確認管道、錯誤訊息用詞：不適用，因為沒有任何使用者可見的動作或資料被改。 -->

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-039 | 專長守則：資料結構變動要有 migration 或明寫不需要 | 功能 | 實作完成 | 讀 ledger.md | 明寫「不需要 migration」與理由（只改了測試腳本與 ledger，沒有資料或結構變動） | 手動：閱卷者讀 ledger.md |
| TC-040 | 專長守則：密鑰不得出現在日誌或回應 | 功能 | ledger.md 內貼了壓測與全套的輸出 | 閱卷者搜 ledger.md 與守門測試的輸出，找 token、密碼、金鑰、`~/.config/agentic-bioflow` 的內容 | 都沒有 | 手動：閱卷者搜尋 |
