# 測試案例：#104 清理閘門補完「不知道目前在哪個資料夾」這一類漏洞

<!--
Written by the verifier (CONTRACT mode). Source: specs/104-cleanup-cwd-rest/plan.md only (this is a fix; there is no spec.md).
"對應需求" cites the plan's own numbering: 設計 N = "Design decisions" item N, 改動 N = "Changes, in order" step N, 事實 = "Facts" flipped lines, 不在範圍 = "Not in this PR".
Every command below is the plan's own example, or the plan's rule applied to a plain command, or a pinned existing line named in "Facts".
Notation: <run> = the test file's run folder `$P`; `rm -rf` = the delete verb `$D`; "問" = the gate stops and asks the person (ask); "擋" = deny; "放行" = pass.
The gate is only run on text; nothing here deletes anything.
-->

**規格**：`specs/104-cleanup-cwd-rest/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：這次要做到的事，正常情況下做到了（含「該放行的照樣放行」的對照組）。
- **例外**：出錯、資料夾不明、不該做的事時，系統怎麼反應（問、擋）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

白話背景：#78 讓「`cd -`、單獨 `cd`、`popd` 之後再刪相對路徑的檔」會先問你。這次把同一類剩下的洞補完：只要閘門「說不出現在在哪個資料夾」，之後對相對路徑的刪除、移動、覆寫就要問；只有「一定成功、一定在主 shell、去到明確絕對路徑」的 cd 才算重新知道位置。只有「原本放行」的會變成「問」，原本擋的、問的不變。

## 群組 A — 去不明的地方（`~/x`、`$變數`、`$(...)`）之後相對刪除要問（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104-01 | 設計 1；改動 1 | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>/rawdata; cd ~/x; rm -rf s1` | 問（閘門不知道 `~/x` 是哪裡，相對的 `s1` 不能放行） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-02 | 設計 1；改動 1 | 例外 | 目前資料夾 `/tmp` | 送 `cd $HOME/rawdata; rm -rf s1` | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-03 | 設計 1；改動 1 | 例外 | 目前資料夾 `/tmp` | 送 `cd $(echo /tmp); rm -rf s1` | 問（`$(...)` 的結果閘門算不出來） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-04 | 事實（TC-041 與 TC-078-24 是同一句）；設計 1 | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>; cd $d; rm -rf x` | 問（原本放行，這次刻意改成問；測試標籤理由寫 "lost cwd now asks (#104)"） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-05 | 事實（TC-042）；設計 1 | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>; cd $(printf results); rm -rf x` | 問（原本放行，刻意改成問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-06 | 事實（TC-078-27）；設計 1 | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>; cd ~; rm -rf x` | 問（原本放行，刻意改成問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-07 | 事實（`:496` #35 對照）；設計 1 | 例外 | 目前資料夾 `<run>` | 送 `cd $HOME && rm -rf x` | 問（原本放行，刻意改成問） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-08 | 事實（`confirm_cleanup_shapes.txt:32`）；設計 1；改動 4 | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>/results; cd ~; rm -rf x`（形狀檔該列） | 問（形狀檔該列的期望值由 pass 改為 ask） | 自動：`tests/confirm_cleanup_test.sh`（讀 `tests/confirm_cleanup_shapes.txt`） |
| TC-104-09 | 設計 4；改動 1 | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>/rawdata; cd -; rm -rf ~s1`（`~s1` 是「某使用者 s1」式寫法，不是家目錄） | 問（`~` 以外的 `~word` 在資料夾不明時當相對路徑） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-10 | 設計 4 | 功能 | 目前資料夾 `/tmp` | 送 `cd <run>; cd -; rm -rf ~/x` | 放行（`~` 與 `~/...` 仍視為明確的家目錄路徑，不算相對） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 B — 只有「無條件、主 shell、絕對路徑」的 cd 才算重新知道位置（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104-11 | 設計 2；改動 1 | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>/rawdata; cd -; (cd /tmp); rm -rf s1` | 問（括號裡的 cd 只動子 shell，不算回到已知位置） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-12 | 設計 2；改動 1 | 例外 | 目前資料夾 `/tmp` | 送 `cd -; cd /tmp & rm -rf s1` | 問（放背景的 cd 不算） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-13 | 設計 2；改動 1 | 例外 | 目前資料夾 `/tmp` | 送 `cd -; true \|\| cd /tmp; rm -rf s1` | 問（`\|\|` 右邊的 cd 不一定執行，不算） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-14 | 設計 2（「不在 if/while/case 裡」） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; if true; then cd /tmp; fi; rm -rf s1` | 問（條件式裡的 cd 不算；閘門若沒追蹤條件脈絡，安全預設是不解除） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-15 | 設計 2（「目標不是變數」） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; cd $d; rm -rf s1` | 問（目標是變數，不能當作已知位置） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-16 | 設計 2；改動 1 對照組 | 功能 | 目前資料夾 `/tmp` | 送 `cd -; cd /tmp; rm -rf s1` | 放行（單獨、無條件的絕對 cd 解除「位置不明」） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-17 | 設計 2；改動 1 對照組 | 功能 | 目前資料夾 `/tmp` | 送 `cd -; cd /tmp && rm -rf s1` | 放行（`&&` 後面只在 cd 成功後才執行，算解除） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-18 | 設計 2（「`{ cd /abs; }` 也解除」） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; { cd /tmp; }; rm -rf s1` | 放行（大括號群組在主 shell 執行，算解除） | 自動：`tests/confirm_cleanup_test.sh` <br>Note: brace half superseded by the 2026-10-17 ruling (plan Design 2). |
| TC-104-19 | 事實（TC-078-19 不動） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; cd <run>; rm -rf x` | 放行（#78 既有行為不變） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-20 | 改動 1 對照組；事實（TC-078-18 不動） | 功能 | 目前資料夾 `/tmp` | 送 `cd ~; rm -rf /tmp/s1`；以及 `cd -; rm -rf <run>/tmp` | 兩句都放行（刪的是絕對路徑，不受「位置不明」影響） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-21 | 事實（TC-078-13 不動）；憲法 | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>; cd -; rm -rf results` | 擋（維持 deny，不可被放寬成問） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 C — 資料夾不明時，用 `>` 覆寫相對檔案也要問（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104-22 | 設計 3；改動 1 | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>/rawdata; cd -; : > s1` | 問（`: > s1` 會清空 `s1`，位置不明） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-23 | 設計 3 | 例外 | 目前資料夾 `/tmp` | 送 `cd -; echo hi > s1` | 問（任何寫入者的相對 `>` 都算） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-24 | 設計 3（「同一組 UNRESOLVED 措辭」） | 例外 | 目前資料夾 `/tmp` | 送 `cd -; : > s1`，讀閘門回的原因文字 | 原因文字含 "working folder unknown"（與 TC-078-14 同一家族措辭） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-25 | 設計 3；改動 1 對照組 | 功能 | 目前資料夾 `/tmp`（位置已知） | 送 `echo hi > s1` | 放行（位置已知時，相對 `>` 的判定與 main 相同） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-26 | 設計 3（「只在 lost_rel 時才問」） | 功能 | 目前資料夾 `/tmp` | 送 `cd -; echo hi > /tmp/s1` | 放行（絕對路徑目標不受位置不明影響，判定與今天相同） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-27 | 事實（TC-078-20 不動） | 功能 | 目前資料夾 `/tmp` | 送 `cd <run>; cd -; ls` | 放行（沒刪、沒移、沒寫，就不問） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 D — PowerShell 的位置指令與「引號裡的反斜線」只看 cd 目標（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104-28 | 設計 5；改動 1 | 例外 | 工具是 PowerShell | 送 `cd <run>; sl -; Remove-Item -Recurse x` | 問（`sl -` 回到上一個資料夾，位置不明） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-29 | 設計 5 | 例外 | 工具是 PowerShell | 送 `cd <run>; sl; Remove-Item -Recurse x` | 問（單獨 `sl` 位置不明） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-30 | 設計 5 | 例外 | 工具是 PowerShell | 送 `cd <run>; Set-Location; Remove-Item -Recurse x` | 問（單獨 `Set-Location` 位置不明） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-31 | 設計 5 | 例外 | 工具是 PowerShell | 送 `cd <run>; Set-Location 'tm\p'; Remove-Item -Recurse x`（目標是引號裡含反斜線） | 問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-32 | 設計 5（「Bash 下 `sl` 不是內建指令」） | 功能 | 工具是 Bash，目前資料夾 `/tmp` | 送 `cd <run>; sl -; rm -rf x` | 放行（Bash 下 `sl` 什麼都不改，位置仍是 `<run>`） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-33 | 設計 5；改動 1 對照組（維持 main 的行為） | 功能 | 目前資料夾 `<run>` | 送 `cd tmp; echo "a\b"; rm -rf x` | 放行（之後某個無關的引號反斜線不會讓位置變成不明） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-34 | 設計 5（只測 cd 目標後，原本抓得到的仍抓得到）；事實（TC-078-05..07 mech 行不動） | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>; cd "tm\p"; rm -rf x`、`cd <run>; cd 'tm\p'; rm -rf x`、`cd <run>; pushd "tm\p"; rm -rf x` | 三句都問 | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 E — popd 與 find（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104-35 | 設計 6（popd 保留舊 `VCWD`，由設計 3 補洞）；事實（TC-078-04） | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>; popd; rm -rf x` | 問（不變） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-36 | 設計 6；事實（TC-078-03） | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>/results; pushd /tmp; popd; rm -rf x` | 問（不變） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-37 | 設計 7；改動 1（對照：main 已會問） | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>; cd -; find . -exec mv {} /tmp/y \;` | 問（main 已問，之後仍問；設計 7 今天不翻轉任何形狀） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-38 | 設計 7；事實（TC-078-15） | 例外 | 目前資料夾 `/tmp` | 送 `cd <run>; cd -; find . -name x -delete` | 問（不變） | 自動：`tests/confirm_cleanup_test.sh` |

## 群組 F — 形狀檔與量測（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104-39 | 改動 4 | 功能 | 實作完成 | 看 `tests/confirm_cleanup_shapes.txt` | 群組 A、B、C、D 的每個新形狀（TC-104-01、02、03、09、11、12、13、15、22、23、28 等）都有一列，期望值與本檔一致；既有列只有「第 32 列 pass→ask」被改，其餘不動 | 自動：`tests/confirm_cleanup_test.sh`（逐列讀形狀檔） |
| TC-104-40 | 改動 6 | 功能 | 實作完成 | 用分支與 main 各跑一次 `confirm_cleanup_shapes.txt` 與 `confirm_cleanup_shapes_main.txt`（不用對話紀錄） | 每一列「pass 變 ask」都屬於本計畫列的那幾類形狀；數量記在 `specs/104-cleanup-cwd-rest/ledger.md` | 手動：`docs/TESTING.md`（需補此步驟，見總覽疑問 1） |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104-41 | 不在範圍：別名 | 不在範圍 | 目前資料夾 `/tmp` | 送 `cd <run>; alias go=cd; go results; rm -rf x` | 仍放行（TC-043 不動；沒有別名模型，沒有悄悄做） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-42 | 不在範圍：不新增壓縮／同步工具的解析 | 不在範圍 | 目前資料夾 `/tmp` | 送 `cd <run>; cd -; tar --remove-files -czf a.tgz s1`（另 `zip -m`、`rclone` 各一句同形） | 仍放行（與 main 相同，沒有偷做新解析） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-43 | 不在範圍：已知缺口要寫下來 | 不在範圍 | 實作完成 | 讀 `specs/104-cleanup-cwd-rest/ledger.md` | 明列 `tar --remove-files`、`zip -m`、`rclone` 相對來源為「已知缺口，留待後續 issue」 | 手動：`docs/TESTING.md`（需補此步驟，見總覽疑問 1） |
| TC-104-44 | 不在範圍：不做目錄堆疊模型 | 不在範圍 | 目前資料夾 `/tmp` | 送 `cd <run>; pushd results; popd; rm -rf x`（TC-056）與 `cd <run>; pushd results; pushd /tmp; popd; rm -rf x`（TC-078-29） | 前者仍擋、後者仍問（沒有追蹤堆疊內容） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-45 | 不在範圍：不動 `confirm_launch.sh`、`hooks.json`、jq 快速路徑、期限、任何擋的規則 | 不在範圍 | 實作完成 | 看 `git diff main...HEAD --stat` | 這些檔案與函式沒有出現在差異裡（`hooks/` 底下只有 `confirm_cleanup.sh`；期限與 jq 快速路徑的程式碼段落未改） | 手動：`docs/TESTING.md`（需補此步驟，見總覽疑問 1） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-104-46 | 安全網：只收緊不放寬 | 功能 | 實作完成 | 跑 `bash tests/confirm_cleanup_test.sh` | 所有既有的「擋」與「問」判定全部不變；唯一被改的「放行」是 TC-104-04、05、06、07、08 這五處（含 TC-078-24、TC-078-27），標籤理由為 "lost cwd now asks (#104)" | 自動：`tests/confirm_cleanup_test.sh` |
| TC-104-47 | 安全網：藏在大段 here-doc 後面也守得住 | 功能 | 實作完成 | 跑 `bash tests/confirm_cleanup_behind_heredoc_test.sh` | 全綠、檔案未被編輯 | 自動：`tests/confirm_cleanup_behind_heredoc_test.sh` |
| TC-104-48 | 憲法：不新增行程 | 功能 | 實作完成 | 跑 `bash tests/gate_process_count_test.sh` | 全綠、檔案未被編輯（閘門沒有多開任何程序） | 自動：`tests/gate_process_count_test.sh` |
| TC-104-49 | 憲法：20 秒期限、30 秒 hook 逾時不動 | 功能 | 實作完成 | 跑 `bash tests/confirm_cleanup_candidates_timing_test.sh` | 全綠、檔案未被編輯；分支與 main 的毫秒數記在 ledger | 自動：`tests/confirm_cleanup_candidates_timing_test.sh` |
| TC-104-50 | 憲法：jq 1.6 與 1.7.1 都過 | 功能 | WSL，兩個版本的 jq 各放在 PATH 最前面 | 各跑 `bash tests/run_all.sh`，及 `bash tests/jq_versions_test.sh` | 兩種版本全綠 | 自動：`tests/jq_versions_test.sh`、`tests/run_all.sh` |
| TC-104-51 | 安全網：沒有任何 main 擋或問、分支卻放行的形狀 | 功能 | 實作完成 | 用 `confirm_cleanup_shapes_main.txt`（main 的實測判定）與 `confirm_cleanup_shapes.txt` 對照分支判定 | main 擋／問、分支放行的列數 = 0；數量記在 ledger | 手動：`docs/TESTING.md`（需補此步驟，見總覽疑問 1） |
| TC-104-52 | 計畫「必須保持綠且不編輯」 | 功能 | 實作完成 | 比對 `main` 與分支的 `tests/`：`confirm_cleanup_shapes_main.txt`、`confirm_cleanup_behind_heredoc_test.sh`、`confirm_cleanup_candidates_timing_test.sh`、`gate_process_count_test.sh`、`jq_versions_test.sh` | 全部與 main 位元組相同；`confirm_cleanup_test.sh` 與形狀檔只出現 TC-104-04、05、06、07、08 那五處期望值改動，其餘 TC-078-* 不動；沒有任何「擋」或「問」被刪、被跳過或被放寬 | 手動：`docs/TESTING.md`（需補此步驟，見總覽疑問 1） |
| TC-104-53 | 計畫「先紅後綠」 | 功能 | 實作完成 | 讀 `specs/104-cleanup-cwd-rest/ledger.md` | 記有「實作前新增的案例（群組 A、B、C、D 的『問』）確實失敗」的紀錄，並說明設計 7 今天沒有翻轉任何形狀 | 手動：`docs/TESTING.md`（需補此步驟，見總覽疑問 1） |

<!--
Rules followed:
- IDs are never renumbered after approval.
- 驗證方式 自動 rows name the test file; the executor puts the TC ID in a comment on each test line.
-->
