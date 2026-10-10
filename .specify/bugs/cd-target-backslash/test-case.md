# 測試案例：清理關卡跟丟「反斜線資料夾名」與「PowerShell 切換指令」（#76、#75）

<!--
Written by the verifier (CONTRACT mode). Bug fix, tier A (the Safety Net gets stricter);
no maintainer example: the ground truth is the "same command without the trick"
column of .specify/bugs/cd-target-backslash/assessment.md, re-measured on main
(WSL, jq 1.7.1) and corrected where noted.
-->

**規格**：`.specify/bugs/cd-target-backslash/assessment.md`（沒有 spec.md，這是缺陷修復）　**總覽**：`test-case-overview.md`

名詞：關卡＝`hooks/confirm_cleanup.sh`，負責在刪除／搬移前擋下或詢問。`R` ＝ `/work/u9613010/lab_runs/x`（一個分析資料夾）。「平常寫法」＝同一條指令拿掉反斜線技巧後，main 上實測的結果。判定：deny＝擋下；ask＝跳確認框；pass＝放行。除非另寫，session 的工作目錄是 `/tmp`。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

所有自動案例都寫在 `tests/confirm_cleanup_test.sh`（以下簡稱「主測試」），並由 `tests/confirm_cleanup_behind_heredoc_test.sh`（以下簡稱「大輸入測試」）在一份很大的 here-doc 後面再跑一遍，兩邊判定必須相同。每個測試的註解要寫出它的 TC 編號。

## User Story 1 — Bash：資料夾名中間夾反斜線，關卡要跟著進去（#76 項 1，優先度 P1）

shell 會把 `res\ults` 的反斜線拿掉，真的進到 results。關卡必須照 `cd results` 的平常寫法判斷。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | assessment 第 1 列；#76 項 1 | 功能 | 工具＝Bash | `cd R; cd res\ults; rm -rf x` | deny（平常寫法 `cd results` 是 deny） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-002 | assessment 第 2 列；#76 項 1 | 功能 | 工具＝Bash | `cd R; cd raw\data; rm -rf x` | deny（平常寫法 deny） | 自動：主測試 |
| TC-003 | assessment 第 3 列；#76 項 1 | 功能 | 工具＝Bash | `cd R; cd wo\rk; rm -rf x` | ask（平常寫法 `cd work` 是 ask，不能變成 deny，也不能放行） | 自動：主測試 |
| TC-004 | assessment 第 4 列；#76 項 1 | 功能 | 工具＝Bash | `pushd R/.nextflow/plug\ins; rm -rf x` | deny（平常寫法 deny） | 自動：主測試 |
| TC-005 | assessment 第 5 列 | 功能 | 工具＝Bash | `cd R/res\ults; rm -rf .` | deny（平常寫法 deny） | 自動：主測試 |
| TC-006 | #76「複本不可更鬆」的延伸：命令字本身夾反斜線 | 功能 | 工具＝Bash | `cd R; c\d results; rm -rf x`（shell 把 `c\d` 當 `cd`） | deny（`cd R; cd results; rm -rf x` 是 deny） | 自動：主測試 |
| TC-007 | 同上 | 功能 | 工具＝Bash | `cd R; pu\shd results; rm -rf x` | deny（平常寫法 deny） | 自動：主測試 |
| TC-008 | 同 TC-001，但刪除方式是 `find` | 功能 | 工具＝Bash | `cd R; cd res\ults; find . -delete` | deny（`cd R; cd results; find . -delete` 是 deny） | 自動：主測試 |
| TC-009 | 同 TC-002，但動作是搬移 | 功能 | 工具＝Bash | `cd R; cd raw\data; mv x y` | ask（`cd R; cd rawdata; mv x y` 是 ask） | 自動：主測試 |
| TC-010 | 不誤擋：往上一層離開 | 功能 | 工具＝Bash | `cd R; cd res\ults; cd ..; rm -rf x` | pass（人其實已回到 R；`cd R; cd results; cd ..; rm -rf x` 是 pass） | 自動：主測試 |
| TC-011 | 不誤擋：無害資料夾 | 功能 | 工具＝Bash | `cd R; cd re\ports; rm -rf x` | pass（`cd R; cd reports; rm -rf x` 是 pass） | 自動：主測試 |
| TC-012 | 不誤擋：無害資料夾，路徑寫在一起 | 功能 | 工具＝Bash | `cd R/re\ports; rm -rf x` | pass（平常寫法 pass） | 自動：主測試 |
| TC-013 | 不誤擋：切去別處 | 功能 | 工具＝Bash | `cd R; cd res\ults; cd /tmp; rm -rf x` | pass（人已在 /tmp） | 自動：主測試 |

## User Story 2 — PowerShell 的 Set-Location／sl／Push-Location 要當成 cd（#75，優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | assessment 第 6 列；#75 | 功能 | 工具＝PowerShell | `Set-Location R/results; Remove-Item -Recurse x` | deny（`cd R/results; Remove-Item -Recurse x` 是 deny） | 自動：主測試 |
| TC-015 | assessment 第 7 列；#75 | 功能 | 工具＝PowerShell | `sl R/results; Remove-Item -Recurse x` | deny | 自動：主測試 |
| TC-016 | assessment 第 8 列；#75 | 功能 | 工具＝PowerShell | `Push-Location R/results; Remove-Item -Recurse x` | deny | 自動：主測試 |
| TC-017 | assessment 第 9 列 | 功能 | 工具＝Bash（內容是 PowerShell 寫法） | `Set-Location R/results; rm -rf x` | deny | 自動：主測試 |
| TC-018 | 計畫「含 -Path」 | 功能 | 工具＝PowerShell | `Set-Location -Path R/results; Remove-Item -Recurse x` | deny | 自動：主測試 |
| TC-019 | 計畫「含 -LiteralPath」 | 功能 | 工具＝PowerShell | `Set-Location -LiteralPath R/results; Remove-Item -Recurse x` | deny | 自動：主測試 |
| TC-020 | 計畫「含 -Path」，冒號貼著寫 | 例外 | 工具＝PowerShell | `Set-Location -Path:R/results; Remove-Item -Recurse x` | deny（不能因為讀不到目標就當成未知而放行；main 現在是 pass） | 自動：主測試 |
| TC-021 | 計畫「不分大小寫」 | 例外 | 工具＝PowerShell | `SET-LOCATION R/results; Remove-Item -Recurse x` | deny | 自動：主測試 |
| TC-022 | 計畫 `chdir` | 功能 | 工具＝PowerShell | `cd R; chdir results; Remove-Item -Recurse x` | deny | 自動：主測試 |
| TC-023 | 相對路徑接在 cd 後面 | 功能 | 工具＝PowerShell | `cd R; Set-Location results; Remove-Item -Recurse x` | deny | 自動：主測試 |
| TC-024 | #75 與 #76 合併：PowerShell 切換加反斜線 | 功能 | 工具＝PowerShell | `cd R; Set-Location res\ults; Remove-Item -Recurse x` | deny（平常寫法 deny；關卡保守地沿用 #66 的「反斜線拿掉也判」） | 自動：主測試 |
| TC-025 | 不誤擋：切去無關資料夾 | 功能 | 工具＝PowerShell | `Set-Location /tmp; Remove-Item x` | pass | 自動：主測試 |
| TC-026 | 不誤擋：相對切去無關資料夾 | 功能 | 工具＝PowerShell | `cd R; Set-Location tmp; Remove-Item -Recurse x` | pass | 自動：主測試 |
| TC-027 | Revision 3：PowerShell 指令只增加候選、不移除；進過 results 就一直判 results（過度擋可接受，絕不放鬆） | 例外 | 工具＝PowerShell | `cd R; Set-Location results; Set-Location ..; Remove-Item -Recurse x` | deny（Revision 3 起；原合約是 pass。同一串用 `cd` 寫、且 `cd ..` 離開 results，仍是 pass，見 TC-010） | 自動：主測試 |

## User Story 3 — 反斜線資料夾名接管線搬移（#76 項 2，優先度 P2）

assessment 原本說這項「不會重現」，但那條用的是絕對路徑。issue 寫的相對路徑在 main 上確實是 pass，這幾條要補上。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-028 | #76 項 2 | 功能 | 工具＝PowerShell；工作目錄 `/tmp` | `Get-ChildItem res\ults \| Move-Item -Destination x` | ask（`Get-ChildItem results \| Move-Item -Destination x` 是 ask；main 現在是 pass） | 自動：主測試 |
| TC-029 | #76 項 2，換成 rawdata | 功能 | 工具＝PowerShell；工作目錄 `/tmp` | `Get-ChildItem raw\data \| Move-Item -Destination x` | ask（`rawdata` 寫法是 ask） | 自動：主測試 |
| TC-030 | #76 項 2，session 工作目錄就在 R | 功能 | 工具＝PowerShell；工作目錄＝R | `Get-ChildItem res\ults \| Move-Item -Destination x` | ask | 自動：主測試 |
| TC-031 | #76 項 2，別名 | 功能 | 工具＝PowerShell；工作目錄 `/tmp` | `gci res\ults \| Move-Item -Destination /tmp/y` | ask（`gci results \| Move-Item -Destination /tmp/y` 是 ask） | 自動：主測試 |
| TC-032 | 對照：絕對路徑本來就正確 | 功能 | 工具＝PowerShell | `Get-ChildItem R/res\ults \| Move-Item -Destination /tmp/y` | ask（維持，不可退步） | 自動：主測試 |
| TC-033 | 不誤擋：無害資料夾 | 功能 | 工具＝PowerShell；工作目錄 `/tmp` | `Get-ChildItem re\ports \| Move-Item -Destination x` | pass（`reports` 寫法是 pass） | 自動：主測試 |

## 憲法與安全網

涉及的規則：Safety Net「Never delete a user's source data」與「Deleting work/ requires the user's explicit confirmation」；既有 #66、#74 的案例不得變鬆；#62 大輸入路徑不得漏掉新規則。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | Never delete source data：新增追蹤 Push-Location 不可比 main 鬆 | 例外 | 工具＝PowerShell | `cd R/results; Push-Location /tmp; Pop-Location; Remove-Item -Recurse x`（人其實又回到 results） | deny（main 現在是 deny，改完不可變 pass） | 自動：主測試 |
| TC-035 | 同上：Bash 裡的 `sl` 不是 cd | 例外 | 工具＝Bash | `cd R/results; sl /tmp; rm -rf x`（目錄實際沒動） | deny（main 是 deny，改完不可變 pass） | 自動：主測試 |
| TC-036 | 同上：Pop-Location 不可讓判定變鬆 | 例外 | 工具＝PowerShell | `cd R; cd results; Pop-Location; Remove-Item -Recurse x` | deny（main 是 deny） | 自動：主測試 |
| TC-037 | #66／#74 規則：複本不改變原本的狀態 | 例外 | 工具＝Bash | `cd R/results\old; rm -rf x`，另加 `cd results\old; rm -rf x`（工作目錄 R） | 兩條都 deny（沿用主測試既有 #66 案例，數量與期望值不得改動） | 自動：主測試 |
| TC-038 | 既有案例整體不變鬆 | 例外 | 無 | 跑整份主測試 | 所有既有案例（含 #35、#66 第 1 至 3 輪、#62）判定與修改前完全相同，沒有被刪、被跳過、被放寬 | 自動：主測試 |
| TC-039 | #62 大輸入路徑看得到新的切換指令 | 例外 | 工具＝Bash | 在超過 8 KB 的 here-doc 之後接 `Set-Location R/results; Remove-Item -Recurse x`；另接 `cd R; cd res\ults; rm -rf x` | 兩條都 deny，和不放 here-doc 時一樣 | 自動：`tests/confirm_cleanup_behind_heredoc_test.sh` |
| TC-040 | #62 前置條件不變 | 例外 | 無 | 大輸入測試開頭的 awk 次數檢查 | 仍然是 3 次，且全部案例通過 | 自動：大輸入測試 |

## 憲法與安全網（第二輪驗收退回後釘死：不得比 main 鬆）

第二輪驗收發現：分支在某些寫法上 main 擋、分支放。Revision 3 的規則是「本 PR 新增的一切只能增加候選、不能移除」，所以下列每一條的預期＝main 的實測判定（TC-045、TC-046 比 main 更嚴；TC-062 是 Revision 3 接受的過度擋）。`R` 與前綴 `cd R; pushd results` 如上；除非另寫，工作目錄 `/tmp`。`⏎` 表示指令裡真的換行。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-045 | Never delete source data：反斜線切進去之後的相對 cd 也要跟（#76 本意；Rev3 的「取代候選集」不能只對主幹解析） | 功能 | 工具＝Bash | `cd R; cd res\ults; cd sub; rm -rf x` | deny（平常寫法 `cd R; cd results; cd sub; rm -rf x` 是 deny；main 是 pass；`cd R; cd re\ports; cd sub; rm -rf x` 仍是 pass） | 自動：主測試 |
| TC-046 | 同上：PowerShell 切進去之後的相對 cd | 功能 | 工具＝PowerShell | `cd R; Set-Location results; cd sub; Remove-Item -Recurse x` | deny（比 main 的 pass 嚴；理由同 TC-045） | 自動：主測試 |
| TC-047 | 案例 A1：Bash 裡 Set-Location 不是內建，來回切不得讓真實位置掉出候選 | 例外 | 工具＝Bash | `cd R; Set-Location results; Set-Location R; cd ..; rm -rf x` | deny（main 是 deny；現行分支是 pass，這是退步） | 自動：主測試 |
| TC-048 | 案例 A2 | 例外 | 工具＝Bash | `cd R; sl results; sl R; cd ..; rm -rf x` | deny（main deny） | 自動：主測試 |
| TC-049 | 案例 A3 | 例外 | 工具＝Bash | `cd R; sl results; sl /tmp; cd ..; rm -rf x` | deny（main deny） | 自動：主測試 |
| TC-050 | 案例 A4 | 例外 | 工具＝Bash | `cd R; sl results; sl ..; cd ..; rm -rf x` | deny（main deny） | 自動：主測試 |
| TC-051 | 案例 A5：不認得的選項 | 例外 | 工具＝PowerShell | `cd R; sl results; sl -Foo R; cd ..; Remove-Item -Recurse x` | deny（main deny） | 自動：主測試 |
| TC-052 | 案例 B：條件寫在別行的 popd 不算「一定執行」（Bash，前綴 `cd R; pushd results`，換行後接 `rm -rf x`） | 例外 | 工具＝Bash | 六種寫法各一條：`if false; then⏎ popd⏎fi`、`false &&⏎ popd`、`while false; do⏎ popd⏎done`、`case a in b)⏎ popd ;;⏎esac`、`{ false; } && {⏎ popd⏎}`、`foo() {⏎ popd⏎}` | 六條都 deny（main 六條都 deny） | 自動：主測試 |
| TC-053 | 案例 B：子殼裡的 popd 不影響本 shell | 例外 | 工具＝Bash | `cd R; pushd results⏎bash -c 'popd'⏎rm -rf x` | deny（main deny） | 自動：主測試 |
| TC-054 | 案例 B：PowerShell 多行條件 | 例外 | 工具＝PowerShell | 前綴 `cd R; pushd results⏎`，接 `if ($false) {⏎ Pop-Location⏎}⏎Remove-Item -Recurse x`；另一條把 if 換成 `foreach ($i in @()) {⏎ Pop-Location⏎}` | 兩條都 deny（main 都是 deny；同寫在單行的版本本來也是 deny） | 自動：主測試 |
| TC-055 | 第一輪形狀：popd 帶參數或堆疊被動過，不能當成回到原處（工作目錄 R） | 例外 | 工具＝Bash | `pushd results; popd -n; rm -rf x`；`pushd /tmp; pushd results; popd +1; rm -rf x`；`pushd results; dirs -c; popd; rm -rf x` | 三條都 deny（main 都是 deny） | 自動：主測試 |
| TC-056 | 第一輪形狀：單純 `popd` 也維持 main 的判定（Rev3 起不再「回到 pushd 的資料夾」） | 例外 | 工具＝Bash | `cd R; pushd results; popd; rm -rf x`；另一條 `cd R; pushd results; popd; popd; rm -rf x` | 兩條都 deny（main deny；原計畫曾寫成 pass，已作廢） | 自動：主測試 |
| TC-057 | 第一輪形狀：PowerShell 讀不懂或不可預測的目標，不得讓判定變鬆（工作目錄 `R/results`） | 例外 | 工具＝PowerShell | `Push-Location -StackName a /tmp; Push-Location -StackName b /var; Pop-Location -StackName a; Remove-Item x`；`sl /tmp; sl -; Remove-Item x`；`Push-Location /tmp; Push-Location -; Remove-Item x`；`sl ../res*; Remove-Item x`；`sl ..; sl -Path (Join-Path $PWD results); Remove-Item x`；`sl ..; sl @("results"); Remove-Item x` | 六條都 deny（main 都是 deny） | 自動：主測試 |
| TC-058 | 第一輪形狀：單行裡「可能沒執行」的 popd（工作目錄 R，前綴 `pushd results;`，後接 `rm -rf x`） | 例外 | 工具＝Bash | `false && popd`、`exit 0 \|\| popd`、`popd \| cat`、`(popd)`、`echo a \| popd`、`popd &`、`command popd` 各一條 | 七條都 deny（main 都是 deny） | 自動：主測試 |
| TC-059 | 第一輪形狀：不認得的選項（工作目錄 `R/results`） | 例外 | 工具＝PowerShell | `sl -Foo /tmp; Remove-Item x`；`sl /tmp -WhatIf; Remove-Item x`；`false && sl /tmp; Remove-Item x`；`sl /tmp; Pop-Location -Foo; Remove-Item x` | 四條都 deny（main 都是 deny） | 自動：主測試 |
| TC-060 | 對照：原先 r1 寫成「放行」的 control，Rev3 起維持 main | 例外 | 工具＝PowerShell；工作目錄 R | `Push-Location results; Pop-Location -PassThru; Remove-Item x` | deny（main deny；r1 曾期望 pass，已作廢） | 自動：主測試 |
| TC-061 | 對照：無害的 PowerShell 切換不得被誤擋 | 功能 | 工具＝PowerShell；工作目錄 R | `sl -PassThru /tmp; Remove-Item x` | pass（main pass） | 自動：主測試 |
| TC-062 | Rev3 接受的過度擋，釘住以免被悄悄改回去 | 例外 | 工具＝PowerShell | `Set-Location R/results; Set-Location /tmp; Remove-Item x` | deny（main 是 pass；進過 results 就一直判 results，與 TC-027 同理） | 自動：主測試 |
| TC-063 | rclone 遠端路徑不看本機候選：整組候選要清空再還原（不得多出新的擋或問） | 例外 | 工具＝Bash | `cd R; sl results; rclone delete remote:x`；另一條 `cd R; cd res\ults; rclone delete remote:x` | 兩條都 pass（main 對 `cd R/results; rclone delete remote:x` 是 pass，兩條都與之相同） | 自動：主測試 |
| TC-064 | 候選集合不爆炸：鏈很長也要在時限內完成 | 例外 | 工具＝Bash；工作目錄 R | `sl d1; sl d2; …; sl d25; rm -rf x`（25 個互不相同的相對目標） | 在關卡現有的時限內完成，沒有走 #62 逾時路徑；判定為 pass，或更嚴的 ask／deny 並附說明，不可卡住或報錯（main 是 pass） | 自動：主測試 |
| TC-065 | 候選集合設上限時，受保護的候選不能被丟掉 | 例外 | 工具＝Bash；工作目錄 R | `sl d1; sl d2; …; sl d12; sl results; sl e1; …; sl e12; rm -rf x` | deny（含 `sl results` 的候選要保留；上限只能丟無害的，主幹永遠留著） | 自動：主測試 |
| TC-066 | 整體對照：沒有任何形狀比 main 鬆 | 例外 | 無 | 把第二輪的 237 個形狀（`C:\Users\marvi\rv_all.txt`）加上 TC-045..065 的所有形狀，把 main（c4a7327）的判定當期望值寫進主測試；驗收時 verifier 再用 main 的 hook 重跑一遍 | 「main deny／ask、分支 pass」的列數＝0（接受名單為空）。不得出現期望值比對應 main 判定更鬆的斷言，r0／r1 測試裡「回到原夾所以放行」這類期望值都要改成 deny。「main pass、分支更嚴」的列允許，但要逐列列在 fix.md | 自動：主測試＋verifier 驗收重跑 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | plan「不做：變數的目錄切換」 | 不在範圍 | 工具＝Bash | `cd R; cd $d; rm -rf x` | pass（維持 main 行為：變數看不出，視為未知；沒有悄悄新增解析變數的功能） | 自動：主測試 |
| TC-042 | plan「不做：`$(...)`」 | 不在範圍 | 工具＝Bash | `cd R; cd $(printf results); rm -rf x` | pass（同上，維持 main 行為） | 自動：主測試 |
| TC-043 | plan「不做：別名」 | 不在範圍 | 工具＝Bash | `cd R; alias go=cd; go results; rm -rf x` | pass（同上，維持 main 行為） | 自動：主測試 |
| TC-044 | plan「不做：其他 hook」 | 不在範圍 | 無 | 跑 `tests/guard_plugin_files_test.sh`，其中有 `Set-Location ~/plugin_root; Remove-Item hooks/x.sh` 一條 | 全部通過，該條仍是 deny；且 diff 中 `hooks/` 底下只有 `confirm_cleanup.sh` 被改 | 自動：`tests/guard_plugin_files_test.sh` |
