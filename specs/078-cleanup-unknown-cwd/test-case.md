# 測試案例：清理關卡在「搞不清楚目前在哪個資料夾」時多問一次（#78）

<!--
Written by the verifier (CONTRACT mode) after the plan, before any code.
Source: specs/078-cleanup-unknown-cwd/plan.md (no spec.md; this is a bug fix). The "maintainer's examples" are the plan's own examples: the four situations in 「給維護者」 and the red cases in Changes step 1.
-->

**規格**：`specs/078-cleanup-unknown-cwd/plan.md`（修補計畫，無獨立 spec）　**總覽**：`test-case-overview.md`

**這份文件怎麼讀**

- 這個修補讓清理關卡（`hooks/confirm_cleanup.sh`）在「搞不清楚目前在哪個資料夾」時，對後面接的相對路徑刪除多問你一次，而不是直接放行。
- 「問」指關卡的 ask：停下來等你按確認。「擋」指 deny：直接拒絕。「放行」指 pass：什麼都不說。
- 下列指令中，`$P` 指測試用的執行資料夾 `/work/u9613010/lab_runs/x`，工作資料夾（cwd）都是 `/tmp`，`rm` 是刪除指令。「相對路徑」指沒有從 `/` 或磁碟代號開頭的路徑，例如 `x`。
- TC 編號用 `TC-078-NN`，避免和 `tests/confirm_cleanup_test.sh` 裡舊的 `TC-0NN` 標籤撞名。新測試案例的註解要寫出對應的 `TC-078-NN`。
- 新案例都加在 `tests/confirm_cleanup_test.sh` 的 TC-043 之後。PowerShell 的案例也可以放在 `tests/confirm_cleanup_shapes.txt`。
- 「和 main 相同」指在 `main` 與本分支各跑一次，結果逐字相同。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## 區塊 1 — 四種搞不清楚的情況，後面接相對路徑刪除就問（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-078-01 | 給維護者 2（`cd -`）；Changes 1 | 例外 | cwd 為 `/tmp`；`main` 上這條是放行（這就是漏洞） | 關卡收到 `cd $P; cd -; rm -rf x` | 問（ask）。不是放行，也不是擋 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-02 | 給維護者 2（單獨一個 `cd`）；Changes 1 | 例外 | cwd 為 `/tmp` | 關卡收到 `cd $P/results; cd; rm -rf x` | 問（ask）。不是放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-03 | 給維護者 2（`popd` 之後）；Facts 的 issue 案例；Changes 1 | 例外 | cwd 為 `/tmp`；`pushd /tmp` 之後 `popd` 回到哪裡，關卡並不知道 | 關卡收到 `cd $P/results; pushd /tmp; popd; rm -rf x` | 問（ask）。不是放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-04 | 給維護者 2（`popd` 之後）；Changes 1 | 例外 | cwd 為 `/tmp`；沒有任何 `pushd` 卻 `popd` | 關卡收到 `cd $P; popd; rm -rf x` | 問（ask）。不是放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-05 | 給維護者 2（引號包起來的反斜線路徑）；Changes 1 | 例外 | cwd 為 `/tmp`；雙引號裡的 `res\ults` 可能是 Windows 寫法，可能是名字真的帶反斜線，關卡分不出 | 關卡收到 `cd $P; cd "res\ults"; rm -rf x` | 問（ask）。不是放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-06 | Design 1（「quoted and contains a backslash」；單引號也是引號） | 例外 | cwd 為 `/tmp` | 關卡收到 `cd $P; cd 'res\ults'; rm -rf x` | 問（ask） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-07 | Design 1（`cd`／`pushd` 兩者都算） | 例外 | cwd 為 `/tmp` | 關卡收到 `cd $P; pushd "res\ults"; rm -rf x` | 問（ask） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-08 | Design 1（`cd`／`pushd` 沒有目標） | 例外 | cwd 為 `/tmp` | 關卡收到 `cd $P; pushd; rm -rf x` | 問（ask） | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-09 | Changes 1（PowerShell `cd -` 案例）；Changes 3（shapes 第 74 行 pass 改 ask） | 例外 | 工具是 PowerShell，cwd 為 `/tmp` | 關卡收到 `cd $P; cd results; cd -; Remove-Item -Recurse x` | 問（ask）。不是放行 | 自動：`tests/confirm_cleanup_shapes.txt`（經 `tests/confirm_cleanup_test.sh` 讀取）或 `tests/confirm_cleanup_test.sh` |
| TC-078-10 | Changes 3（shapes 第 75 行 pass 改 ask） | 例外 | 工具是 PowerShell，cwd 為 `/tmp` | 關卡收到 `cd $P; cd results; cd; Remove-Item -Recurse x` | 問（ask）。不是放行 | 自動：`tests/confirm_cleanup_shapes.txt` |
| TC-078-11 | Design 1（`popd` 與 `pop-location` 都算） | 例外 | 工具是 PowerShell，cwd 為 `/tmp` | 關卡收到 `cd $P; Push-Location /tmp; Pop-Location; Remove-Item -Recurse x` | 問（ask）。不是放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-12 | Design 2（「It lasts for the rest of the command」） | 例外 | cwd 為 `/tmp` | 關卡收到 `cd $P; cd -; ls; rm -rf x`（`cd -` 與刪除之間隔了一個無關的指令） | 問（ask）。「不知道在哪」的狀態不會被中間的 `ls` 洗掉 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-13 | Design 2（只把 pass 變 ask，不產生新的 deny） | 例外 | cwd 為 `/tmp` | 關卡收到 `cd $P; cd -; rm -rf results`（相對路徑剛好叫 `results`） | 問（ask）。不是擋，也不是放行：關卡不知道目前在哪，不能斷定它刪的是受保護的資料夾 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-14 | Design 6（新增的問法要自己說明原因） | 例外 | 同 TC-078-01 | 取 `cd $P; cd -; rm -rf x` 的詢問原因文字 | 文字說明「working folder unknown」（不知道目前的工作資料夾），並提到 `cd -`／`cd`／`popd`，且是要你確認。文字不能是 `main` 已有的其他原因 | 自動：`tests/confirm_cleanup_test.sh`（比對詢問原因的文字） |

## 區塊 2 — 其他讀相對路徑的地方也一樣問（優先度 P1）

計畫的 Design 3 說關卡有三個地方會讀相對路徑：刪除目標、`find` 的起點、大括號清單，另有 `mv` 的來源。計畫沒給具體指令，下面的指令是依這條規則寫出來的。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-078-15 | Design 3（find 起點） | 例外 | cwd 為 `/tmp` | 關卡收到 `cd $P; cd -; find . -name x -delete` | 問（ask）。不是放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-16 | Design 3（大括號清單） | 例外 | cwd 為 `/tmp` | 關卡收到 `cd $P; cd -; rm -rf {a,b}` | 問（ask）。不是放行 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-17 | Design 3（`mv` 只管來源） | 例外 | cwd 為 `/tmp` | 關卡收到 `cd $P; cd -; mv x /tmp/y`（來源 `x` 是相對路徑） | 問（ask）。不是放行 | 自動：`tests/confirm_cleanup_test.sh` |

## 區塊 3 — 不該多問的，照舊放行或照舊擋（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-078-18 | Changes 1（綠燈對照）；Design 3（只管相對路徑） | 功能 | cwd 為 `/tmp` | 關卡收到 `cd -; rm -rf $P/tmp`（刪除目標是絕對路徑） | 放行（pass）。不管目前在哪，絕對路徑的判斷不受影響 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-19 | Changes 1（綠燈對照）；Design 2（絕對路徑的 `cd` 會解除） | 功能 | cwd 為 `/tmp` | 關卡收到 `cd -; cd $P; rm -rf x` | 放行（pass）。後面用絕對路徑 `cd` 之後，又知道在哪了 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-20 | Design 2（只加在「原本會放行」的刪除上） | 功能 | cwd 為 `/tmp` | 關卡收到 `cd $P; cd -; ls`（後面沒有任何刪除） | 放行（pass）。單純不知道在哪不會讓所有指令都被問 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-21 | Design 3（`mv` 只管來源，不管目的地） | 功能 | cwd 為 `/tmp` | 關卡收到 `cd $P; cd -; mv /tmp/a x`（只有最後一個目的地是相對路徑） | 放行（pass），結果和 `main` 相同 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-22 | 給維護者 3（原本會擋的仍然擋）；shapes 的 `#35` 既有案例 | 功能 | cwd 為 `$P` | 關卡收到 `cd "results" && rm -rf fastqc`（有引號、沒有反斜線） | 擋（deny），和 `main` 相同 | 自動：`tests/confirm_cleanup_test.sh`（#35 既有案例，不得修改） |
| TC-078-23 | Design 1（只有「有引號」的反斜線才算搞不清楚） | 功能 | cwd 為 `/tmp` | 在 `main` 與本分支各跑一次：`cd $P; cd res\ults; rm -rf x`（反斜線沒有引號）與 shapes 第 10-12 行的沒有引號反斜線案例 | 兩個分支逐字相同：原本擋的還是擋，原本放行的還是放行 | 自動：`tests/confirm_cleanup_shapes.txt`，另由驗收者在兩個分支比對 |

## 區塊 4 — 這次不做的事

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-078-24 | Not in this PR 第 1 條（變數目標維持放行） | 不在範圍 | cwd 為 `/tmp` | 關卡收到 `cd $P; cd $d; rm -rf x` | 放行（pass），結果和 `main` 相同。既有 TC-041 與 `tests/confirm_cleanup_test.sh:496` 不得修改且仍通過 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-25 | Not in this PR 第 1 條（指令展開目標維持放行） | 不在範圍 | cwd 為 `/tmp` | 關卡收到 `cd $P; cd $(printf results); rm -rf x` | 放行（pass），結果和 `main` 相同。既有 TC-042 不得修改且仍通過 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-26 | Not in this PR 第 1 條（別名維持放行） | 不在範圍 | cwd 為 `/tmp` | 關卡收到 `cd $P; alias go=cd; go results; rm -rf x` | 放行（pass），結果和 `main` 相同。既有 TC-043 不得修改且仍通過 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-27 | Not in this PR 第 1 條（`~` 維持放行） | 不在範圍 | cwd 為 `/tmp` | 關卡收到 `cd $P; cd ~; rm -rf x` | 放行（pass），結果和 `main` 相同 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-28 | Not in this PR 第 1 條（輸入裡沒有 cwd 維持放行） | 不在範圍 | 關卡收到的輸入裡沒有 `cwd` 欄位 | 送出相對路徑刪除，例如 `rm -rf x`（不帶 `cd`） | 放行（pass），結果和 `main` 相同。所有「不帶 cwd」的既有 `t` 案例不得修改且仍通過；`confirm_cleanup_test.sh:855` 也一樣 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-29 | Not in this PR 第 2 條（不做真正的目錄堆疊模型） | 不在範圍 | cwd 為 `/tmp` | 關卡收到 `cd $P; pushd results; pushd /tmp; popd; rm -rf x`（真正的堆疊會回到 `results`） | 問（ask）。不是放行（`main` 是放行），也不是擋：關卡沒有堆疊模型，只知道「不確定」 | 自動：`tests/confirm_cleanup_test.sh`（對應 shapes 第 2 行 pass 改 ask） |
| TC-078-30 | Not in this PR 第 3 條（不動 jq 快路徑、期限、`hooks.json`、`confirm_launch.sh`、任何擋的規則） | 不在範圍 | 本分支相對 `main` 的 diff | 看 diff：`hooks/confirm_cleanup.sh` 第 194 行的 jq 呼叫、期限邏輯（`:919-933`）、`hooks/hooks.json`、`hooks/confirm_launch.sh` 沒有被改；沒有任何 deny 規則被新增、刪除或放寬；然後跑 `tests/confirm_launch_test.sh` | 以上都沒被改，`confirm_launch_test.sh` 通過 | 自動：`tests/confirm_launch_test.sh`（diff 範圍由驗收者讀 diff 確認） |

## 憲法與安全網

這個修補動的是安全網的「刪除前要確認」（`hooks/confirm_cleanup.sh`）。安全網規則不得放寬，也不得讓測試變弱。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-078-31 | 安全網：只能收緊（給維護者 3）；開發流程：不得動既有 deny／ask 的預期 | 功能 | 本分支與 `main` | 比對 `tests/confirm_cleanup_test.sh`：既有的每一條 deny、ask 預期（含 TC-056、R1 的 `popd` 案例、TC-034、TC-036、#62 期限案例）；再跑該檔 | 這些行逐字沒有被修改；該檔全部通過 | 自動：`tests/confirm_cleanup_test.sh` |
| TC-078-32 | 安全網：只能收緊 | 功能 | 本分支與 `main` | 跑 `tests/confirm_cleanup_shapes_main.txt` 對應的測試，並比對該檔相對 `main` 的 diff | 該檔沒有被修改；每一行的判斷都和 `main` 相同 | 自動：`tests/confirm_cleanup_candidates_timing_test.sh`（它同時讀 shapes 與 shapes_main） |
| TC-078-33 | 安全網：只能收緊（給維護者 3：不會有任何一種變得更寬鬆） | 功能 | 本分支與 `main` | 對 `tests/confirm_cleanup_shapes.txt` 與 `tests/confirm_cleanup_shapes_main.txt` 的每一行，在兩個分支各取一次判斷（不含任何 session 紀錄），算出判斷有變動的行 | 有變動的行全部是「pass 改 ask」，數量等於 ledger 上記的數字；每一條變動的行都含四種情況之一（`cd -`、單獨 `cd`、`popd`／`pop-location`、引號包起來的反斜線路徑；不帶目標的 `pushd` 算單獨 `cd` 那一種）。沒有任何 deny 變成 ask 或 pass，也沒有任何 ask 變成 pass。ledger 逐行列出，每行註明原因「lost cwd now asks」 | 自動：`tests/confirm_cleanup_shapes.txt`（兩分支比對，數量由驗收者重算） |
| TC-078-34 | 安全網：#62 大型 here-doc 路徑不得有例外 | 功能 | 新增案例已在 `tests/confirm_cleanup_test.sh` | 跑 `tests/confirm_cleanup_behind_heredoc_test.sh`（它把該檔的每個案例放在大型 here-doc 之後再跑一次） | 全部通過。TC-078-01 到 17 在 here-doc 之後也得到同樣的判斷 | 自動：`tests/confirm_cleanup_behind_heredoc_test.sh` |
| TC-078-35 | 憲法 13 與 Safety Net：關卡不得拖慢到逾時被取消（30 秒逾時，20 秒期限） | 功能 | 本分支與 `main` | 跑 `tests/confirm_cleanup_candidates_timing_test.sh` | 通過：本分支耗時不超過 `main` 加 8000 毫秒。兩個分支的毫秒數記進 ledger | 自動：`tests/confirm_cleanup_candidates_timing_test.sh` |
| TC-078-36 | 開發流程：每階段全綠 | 功能 | 在 WSL，jq 1.7.1 | 跑 `bash tests/run_all.sh` | 全部通過，沒有被跳過的案例 | 自動：`tests/run_all.sh`（CI 結果亦可佐證） |
