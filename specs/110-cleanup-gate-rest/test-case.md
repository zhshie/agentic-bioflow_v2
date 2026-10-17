# 測試案例：#110 清理閘門補完「不知道目前在哪個資料夾」的剩餘漏洞，並拿掉 #104 帶來的多餘詢問

<!--
Written by the verifier (CONTRACT mode). Source: specs/110-cleanup-gate-rest/plan.md only (this is a fix; there is no spec.md).
"對應需求" cites the plan's own numbering: 設計 N = "Design decisions" item N (1-5 = Part 1 收緊, 6-8 = Part 2 拿掉多餘詢問), 改動 N = "Changes, in order" step N, 事實 = "Facts", 不在範圍 = "Not changed" / "Not in this PR", Tier = the plan's Tier line.
Notation: <run> = the test file's run folder `$P` (/work/u9613010/lab_runs/x); `rm -rf` = the delete verb `$D` (the test file assembles it from hex so its own text never trips a cleanup hook); "問" = the gate stops and asks the person (ask); "擋" = deny; "放行" = pass. "⏎" = a real newline inside the one command.
Unless a row says otherwise the session's current folder is `/tmp` and the command starts with `cd -;` or `cd <run>; cd -;` so the folder is "lost" (the gate cannot say where it is).
Where a row says "main 現況：…", that is what the verifier measured by feeding the same text to the current hooks/confirm_cleanup.sh (WSL, jq 1.7.1) while writing this file. Rows marked 「推導」 are the plan's rule applied to a plain command (the plan gives the rule, not that exact sentence); nothing else is added.
The gate is only run on text; nothing here deletes anything.
-->

**規格**：`specs/110-cleanup-gate-rest/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：這次要做到的事，正常情況下做到了（含「該放行的照樣放行」的對照組）。
- **例外**：出錯、資料夾不明、不該做的事時，系統怎麼反應（問、擋）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

白話背景：閘門在你「cd - 之後不知道自己在哪個資料夾」時，對相對路徑的刪除與覆寫會先問你。#109 補了大部分，這次補剩下兩件事。(1) 還有幾種寫法會讓閘門誤以為「又知道在哪了」而放行：`false && cd /tmp`、換行寫的 if／for、`builtin cd`，以及用 `>|`、`>&檔名`、`tee`、`sort -o`、`cp`、`sed -i`、`dd of=` 覆寫相對檔案。這些要改成問。(2) #109 同時帶來幾種根本沒寫檔、也沒刪東西卻被問的情況：引號裡的 `>`、`awk '$1>3'`、`[[ a > b ]]`、`cd /tmp # 註解 | …`。這些要改回放行。真正會刪或覆寫的照樣問或擋，任何「擋」不得放寬。

## 群組 A — 這些寫法的 cd 不再讓閘門「重新知道位置」（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-110-01 | 設計 1；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>; cd -; false && cd /tmp; rm -rf s1` | 問（`&&` 前面還有別的指令，cd 不一定執行；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-02 | 設計 1；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; [ -d x ] && cd /tmp; rm -rf s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-03 | 設計 2；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送（多行）`cd -⏎if true⏎then⏎cd /tmp⏎fi⏎rm -rf s1` | 問（`if` 在 cd 之前出現；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-04 | 設計 2；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送（多行）`cd -⏎for i in; do⏎cd /tmp⏎done⏎rm -rf s1` | 問（`for` 在 cd 之前出現；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-05 | 設計 2（推導：`while`） | 例外 | 目前資料夾 `/tmp` | 送（多行）`cd -⏎while true; do⏎cd /tmp⏎done⏎rm -rf s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-06 | 設計 2（推導：`until`） | 例外 | 目前資料夾 `/tmp` | 送（多行）`cd -⏎until false; do⏎cd /tmp⏎done⏎rm -rf s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-07 | 設計 2（推導：`case`） | 例外 | 目前資料夾 `/tmp` | 送（多行）`cd -⏎case x in x)⏎cd /tmp⏎;;⏎esac⏎rm -rf s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-08 | 設計 2（推導：`select`） | 例外 | 目前資料夾 `/tmp` | 送（多行）`cd -⏎select i in a; do⏎cd /tmp⏎done⏎rm -rf s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-09 | 設計 2（推導：`()`） | 例外 | 目前資料夾 `/tmp` | 送（多行）`cd -⏎(⏎cd /tmp⏎)⏎rm -rf s1` | 問（括號在 cd 之前出現；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-10 | 設計 2（推導：函式定義） | 例外 | 目前資料夾 `/tmp` | 送（多行）`cd -⏎f() {⏎cd /tmp⏎}⏎rm -rf s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-11 | 設計 2（推導：`{`） | 例外 | 目前資料夾 `/tmp` | 送（多行）`cd -⏎{⏎cd /tmp⏎}⏎rm -rf s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-12 | 設計 2（推導：here-doc `<<`） | 例外 | 目前資料夾 `/tmp` | 送（多行）`cd -⏎cat <<EOF⏎x⏎EOF⏎cd /tmp⏎rm -rf s1` | 問（here-doc 在 cd 之前出現；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-13 | 設計 3；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; builtin cd /tmp; rm -rf s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-14 | 設計 3（推導：`command cd`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; command cd /tmp; rm -rf s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-15 | 設計 3（推導：`VAR=x cd`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; X=1 cd /tmp; rm -rf s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-16 | 設計 1、2 對照組（TC-104-16 不動） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; cd /tmp; rm -rf s1` | 放行（單獨、無條件的絕對 cd 仍解除「位置不明」） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-17 | 設計 1 對照組（TC-104-17 不動） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; cd /tmp && rm -rf s1` | 放行（cd 自己開頭一個指令，`&&` 在它後面，仍解除） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-18 | 設計 1 對照組（計畫對照組） | 功能 | 目前資料夾 `/tmp` | 送 `cd /tmp && rm -rf s1` | 放行（`cd /abs && rm …` cd 在前，仍放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-19 | 設計 2 對照組（推導：只有關鍵字／括號出現在 cd「之前」才算） | 功能 | 目前資料夾 `/tmp` | 送（多行）`cd -⏎cd /tmp⏎rm -rf s1`（沒有任何 if／for／括號／here-doc） | 放行（單純換行不讓 cd 失效；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-20 | 設計 2 對照組（計畫文字「appears before the cd」） | 功能 | 目前資料夾 `/tmp` | 送（多行）`cd -⏎cd /tmp⏎if true; then echo; fi⏎rm -rf s1`（if 在 cd 之後） | 放行（main 現況：放行，這次不得變成問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-21 | 事實（TC-104-18 大括號半邊已被 2026-10-17 裁定取代）；改動 4 | 例外 | 目前資料夾 `/tmp` | 送 `cd -; { cd /tmp; }; rm -rf s1` | 問（不變；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 B — 資料夾不明時，更多種「用 `>` 寫進相對檔案」的寫法也要問（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-110-22 | 設計 4；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; ls >\| s1`（強制覆寫） | 問（原因文字與 TC-104-24 同一家族：含 "working folder unknown"；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-23 | 設計 4；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; ls >&s1`（`>&` 後面接檔名） | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-24 | 設計 4（計畫文字 `>& file`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; ls >& s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-25 | 設計 4；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo x > "$F"` | 問（目標用變數寫，位置不明時一律問；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-26 | 設計 4（推導：`$(…)`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo x > $(mktemp)` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-27 | 設計 4（推導：反引號） | 例外 | 目前資料夾 `/tmp` | 送 ``cd -; echo x > `mktemp` `` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-28 | 設計 4（計畫文字：`>&` 後面是檔名，不是數字） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; ls 2>&1` | 放行（`2>&1` 是把輸出併到另一個通道，沒有寫檔；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-29 | 設計 4（同上） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; ls >&2` | 放行（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-30 | 改動 1 對照組（計畫對照組） | 功能 | 目前資料夾 `/tmp`（位置已知，沒有 cd -） | 送 `ls > s1` | 放行（位置已知時相對 `>` 與 main 相同） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-31 | 設計 4（計畫文字「when the folder is lost」才一律問） | 功能 | 目前資料夾 `/tmp`（位置已知） | 送 `cd /tmp; echo x > "$F"` | 放行（位置已知時不因 `$` 而問；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 C — 資料夾不明時，更多種「寫進相對檔案」的指令也要問（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-110-32 | 設計 5；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo x \| tee s1` | 問（`tee` 不加 `-a` 會覆寫 s1；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-33 | 設計 5；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; sort -o s1 s1` | 問（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-34 | 設計 5；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; cp /tmp/a s1` | 問（目的地是相對路徑；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-35 | 設計 5；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; sed -i s/a/b/ s1` | 問（`-i` 原地改檔；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-36 | 設計 5；改動 1（計畫原例） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; dd if=/dev/zero of=s1 count=1` | 問（`of=` 是寫入目標；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-37 | 改動 1 對照組（計畫對照組：`tee -a` 與今天相同） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; echo x \| tee -a s1` | 與 main 相同＝放行（`-a` 是附加不是覆寫，計畫明說不改；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-38 | 設計 5（推導：位置已知時不受影響） | 功能 | 目前資料夾 `/tmp`（位置已知） | 送 `cd /tmp; echo x \| tee s1` | 放行（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-39 | 設計 5（計畫文字「cp … DEST (destination)」：只看目的地） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; cp s1 /tmp/b`（來源相對、目的地絕對） | 放行（只是讀 s1；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-40 | 設計 5（推導：絕對目標不受位置不明影響，同 TC-104-26） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; echo x \| tee /tmp/s1` | 放行（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-41 | 設計 5（推導：`sort` 沒有 `-o` 不是寫檔） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; sort s1` | 放行（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-42 | 設計 5（推導：`sed` 沒有 `-i` 不是改檔） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; sed s/a/b/ s1` | 放行（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-43 | 設計 5（推導：`dd of=` 指向絕對路徑） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; dd if=s1 of=/tmp/o` | 放行（main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 D — #109 帶來的多餘詢問改回放行；真的會寫檔／刪檔的照問（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-110-44 | 設計 6；改動 1（計畫原例） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; echo "x>y"` | 放行（引號裡的 `>` 只是文字；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-45 | 設計 6；改動 1（計畫原例） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; awk '$1>3' /tmp/f` | 放行（`$1>3` 是 awk 的比較，不是寫檔；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-46 | 設計 7；改動 1（計畫原例） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; [[ a > b ]]` | 放行（`[[ ]]` 裡的 `>` 是字串比較；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-47 | 設計 7（計畫文字 `[ a \> b ]`） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; [ a \> b ]` | 放行（main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-48 | 設計 6；改動 1（計畫原例） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; git log --format='a->b'` | 放行（main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-49 | 設計 8；改動 1（計畫原例，補上「位置不明」才是真的紅轉綠） | 功能 | 目前資料夾 `/tmp` | 送（多行）`cd -; cd /tmp # a \| b⏎rm -rf s1` | 放行（`#` 後面是註解，`\|` 不算；與一般 `cd /tmp` 同樣解除；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-50 | 設計 8；改動 1（計畫原句，目前資料夾已知） | 功能 | 目前資料夾 `/tmp`（位置已知） | 送（多行）`cd /tmp # a \| b⏎rm -rf s1` | 放行（對照組；注意 main 現況也是放行，所以這句本身紅不了，見總覽疑問 2） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-51 | 設計 8；改動 1（計畫原例） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; cd /tmp; echo "a&b"; rm -rf s1` | 放行（引號裡的 `&` 是文字，cd 仍解除；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-52 | Tier／設計 6（拿掉詢問不得讓刪除過關） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo "x>y"; rm -rf s1` | 問（前半句是文字，但後半句是位置不明下的相對刪除；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-53 | Tier／設計 6（引號裡有 `>` 但真的有一個重新導向） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo "a>b" > s1` | 問（真的 `> s1` 照問；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-54 | Tier／設計 6（目標被引號包住仍是目標） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo x > "s1"` | 問（目標在雙引號裡不能因此被當成文字；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-55 | Tier／設計 6（同上，單引號） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo x > 's1'` | 問（main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-56 | Tier／設計 7（比較式不得掩護後面真的重新導向） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; [[ a > b ]]; echo x > s1` | 問（`echo x > s1` 是真的寫檔；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-57 | Tier／設計 6（awk 的 `>` 是文字，但行尾真的有 `> s1`） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; awk '$1>3' /tmp/f > s1` | 問（main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-58 | Tier／設計 8（忽略註解與引號，不等於忽略真的 `&`）；TC-104-12 不動 | 例外 | 目前資料夾 `/tmp` | 送 `cd -; cd /tmp & rm -rf s1` | 問（放背景的 cd 不算；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-59 | Tier／設計 8；TC-104-13 不動 | 例外 | 目前資料夾 `/tmp` | 送 `cd -; true \|\| cd /tmp; rm -rf s1` | 問（真的 `\|\|` 右邊的 cd 不算；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 E — 計畫明講這次不做的事（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-110-60 | 不在範圍：`cd "$dir"` 仍算位置不明（#104 刻意） | 不在範圍 | 目前資料夾 `/tmp` | 送 `cd <run>; cd "$dir"; rm -rf s1` | 問（沒有被放寬；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-61 | 不在範圍：`cd $(…)` 仍算位置不明 | 不在範圍 | 目前資料夾 `/tmp` | 送 `cd $(echo /tmp); rm -rf s1`（TC-104-03） | 問（不變） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-62 | 不在範圍：經變數的相對刪除維持現況 | 不在範圍 | 目前資料夾 `/tmp` | 送 `d=s1; rm -rf $d` | 與 main 相同＝問（本次沒有改它；main 現況：問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-63 | 不在範圍：壓縮工具已知缺口 | 不在範圍 | 目前資料夾 `/tmp` | 送 `cd <run>; cd -; tar --remove-files -czf a.tgz s1` | 與 main 相同＝放行（沒有偷做新解析；TC-104-42a） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-64 | 不在範圍：同上 | 不在範圍 | 目前資料夾 `/tmp` | 送 `cd <run>; cd -; zip -m a.zip s1` | 與 main 相同＝放行（TC-104-42b） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-65 | 不在範圍：同上 | 不在範圍 | 目前資料夾 `/tmp` | 送 `cd <run>; cd -; rclone move s1 remote:x` | 與 main 相同＝放行（TC-104-42c） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-66 | 不在範圍：不檢查 cd 的目標存不存在 | 不在範圍 | 目前資料夾 `/tmp` | 送 `cd -; cd /no/such/dir; rm -rf s1` | 與 main 相同＝放行（計畫明說這是已知缺口，閘門不開行程測試存在；main 現況：放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-67 | 不在範圍：沒有別名模型 | 不在範圍 | 目前資料夾 `/tmp` | 送 `cd <run>; alias go=cd; go results; rm -rf x`（TC-104-41） | 仍放行（沒有悄悄做別名） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-68 | 不在範圍：不動期限、jq 快速路徑、其他 hook、任何擋的規則、不新增行程 | 不在範圍 | 實作完成 | 看 `git diff main...HEAD --stat` 與 `hooks/` 的差異 | `hooks/` 底下只有 `confirm_cleanup.sh` 有改；20 秒期限、jq 快速路徑、`confirm_launch.sh`、`hooks.json` 的程式碼段落沒出現在差異裡；差異裡沒有任何新的 deny 規則被刪除或放寬 | 手動：`docs/TESTING.md`（需補此步驟，見總覽疑問 1） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-110-69 | 安全網：永不刪 `results/`（TC-104-21 不動） | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>; cd -; rm -rf results` | 擋（維持 deny，不可被放寬成問或放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-70 | 安全網：忽略註解不得放寬「擋」（設計 8） | 例外 | 目前資料夾 `/tmp` | 送（多行）`cd -; cd /tmp # a \| b⏎rm -rf results` | 擋（main 現況：擋） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-71 | 安全網：永不刪 `results/` | 例外 | 目前資料夾 `/tmp` | 送 `rm -rf <run>/results` | 擋（不變） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-110-72 | 安全網／Tier：與 #104 之前的 main（`94a1c30`）比，沒有任何「原本問或擋、現在放行」 | 功能 | 實作完成 | 把 `tests/confirm_cleanup_test.sh` 的所有輸入與兩份形狀檔（`confirm_cleanup_shapes.txt`、`confirm_cleanup_shapes_main.txt`）分別送進 `94a1c30` 的 hook、現在的 `origin/main` 的 hook、分支的 hook，三邊逐句比判定 | 相對 `94a1c30`：問變放行 0 句、擋被放寬 0 句；結果表寫進 `specs/110-cleanup-gate-rest/ledger.md` | 手動：`docs/TESTING.md`（需補此步驟，見總覽疑問 1） |
| TC-110-73 | 安全網／Tier：與現在的 main 比，只允許兩種變動 | 功能 | 實作完成 | 同上，分支對現在的 `origin/main` | 只有兩種變動：放行變問（Part 1）；問變放行只限「既不刪也不覆寫」的輸入（Part 2：引號或註解裡的字元、比較式、`awk` 比較），每一句逐條列在 ledger；任何會刪或覆寫、main 本來問的句子變放行 0 句；擋被放寬 0 句 | 手動：`docs/TESTING.md`（需補此步驟，見總覽疑問 1） |
| TC-110-74 | 改動 1「先紅後綠」 | 功能 | 實作完成 | 讀 `specs/110-cleanup-gate-rest/ledger.md` 與 git 歷史 | 有一個先寫測試的 commit，Part 1 新案例（TC-110-01…15、22…27、32…36）在修正前確實失敗；Part 2 案例（TC-110-44…49、51）在修正前確實失敗，並如實記下 TC-110-50 在 main 本來就放行 | 手動：`docs/TESTING.md`（需補此步驟，見總覽疑問 1） |
| TC-110-75 | 改動 1／TC-104-39 同類：形狀檔跟著加列 | 功能 | 實作完成 | 看 `tests/confirm_cleanup_shapes.txt` | 本檔 Part 1 與 Part 2 的新輸入各有一列，期望值與本檔一致；既有列的期望值一個都沒改 | 自動：`tests/confirm_cleanup_test.sh`（逐列讀形狀檔） |
| TC-110-76 | 改動 4 | 功能 | 實作完成 | 讀 `specs/104-cleanup-cwd-rest/test-case.md` 的 TC-104-18 那一列 | 該列只多一句註記「brace half superseded by the 2026-10-17 ruling (plan Design 2)」，該列與其他列的任何預期結果都沒被改 | 手動：`docs/TESTING.md`（需補此步驟，見總覽疑問 1） |
| TC-110-77 | 驗收規則：不得放水 | 功能 | 實作完成 | 比對 `git diff main...HEAD -- tests/`，並確認 `specs/110-cleanup-gate-rest/plan.md`、本檔與總覽沒被實作者改動 | `tests/` 底下既有案例沒有被刪、被跳過、被放寬或被改期望值（只有新增與計畫列名的標籤文字）；本檔與總覽與合約確認時一字不差 | 手動：`docs/TESTING.md`（需補此步驟，見總覽疑問 1） |
| TC-110-78 | 安全網：藏在大段 here-doc 後面也守得住（#62） | 功能 | 實作完成 | 跑 `bash tests/confirm_cleanup_behind_heredoc_test.sh`（它把整份 `confirm_cleanup_test.sh` 放在大段 here-doc 後重跑） | 全綠、檔案未被編輯；本檔新案例在 here-doc 之後得到與單獨跑相同的判定 | 自動：`tests/confirm_cleanup_behind_heredoc_test.sh` |
| TC-110-79 | 憲法：不新增行程 | 功能 | 實作完成 | 跑 `bash tests/gate_process_count_test.sh` | 全綠、檔案未被編輯（閘門沒有多開任何程序） | 自動：`tests/gate_process_count_test.sh` |
| TC-110-80 | 憲法：20 秒期限、30 秒 hook 逾時不動（#62） | 功能 | 實作完成 | 跑 `bash tests/confirm_cleanup_candidates_timing_test.sh` | 全綠、檔案未被編輯；分支與 main 的毫秒數記在 ledger | 自動：`tests/confirm_cleanup_candidates_timing_test.sh` |
| TC-110-81 | 改動 5；憲法 13 | 功能 | 實作完成 | 在 WSL 跑 `bash tests/run_all.sh`，分別把 jq 1.6 與 jq 1.7.1 放在 PATH 最前面各跑一次 | 兩次都全綠 | 自動：`tests/run_all.sh` |
| TC-110-82 | 憲法 13：沒有 jq 時不悄悄放行 | 功能 | 實作完成 | 跑 `bash tests/confirm_cleanup_test.sh` 的「no jq」段落 | 該段全綠且沒被改動；新增的判斷沒有讓「jq 壞掉時」的放行／詢問結果變寬 | 自動：`tests/confirm_cleanup_test.sh` |

<!--
Rules for the writer:
- Every design decision (1-8) and every change step (1-5) in plan.md maps to at least one TC; every "Not changed" / "Not in this PR" item maps to a 不在範圍 TC.
- A TC tests one thing. Two expectations = two rows.
- 驗證方式 is 自動 (a test file under tests/) or 手動 (a step in docs/TESTING.md's manual half). Nothing else.
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
