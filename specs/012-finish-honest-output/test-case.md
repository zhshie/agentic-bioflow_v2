# 測試案例：finish 打包誠實說明「這是草稿骨架」並列出未接受項目（#12 第 2 部分）

<!--
Written by the verifier (CONTRACT mode). Source: specs/012-finish-honest-output/plan.md (this is a bug fix, so the plan is the only spec; its "給維護者" three sentences are the maintainer's examples).
-->

**規格**：`specs/012-finish-honest-output/plan.md`（修正案，無 spec.md）　**總覽**：`test-case-overview.md`

對應代號：**M1／M2／M3** ＝ 計畫「給維護者」第 1／2／3 句（維護者的原話）；**D1–D7** ＝ 計畫「Design decisions」第 1–7 點；**R3** ＝ 計畫「Round 3 rulings」。

名詞：「骨架」＝ `manuscript.qmd` 裡每個結果段只有一行 `[GAP: Results for '<id>' not written yet …]` 佔位、討論段只有一行 `[GAP: not drafted …]`，要人來寫。「分析計畫」＝ 專案裡的 `analysis/analysis.md`。「N」＝ `manuscript.qmd` 裡 `[GAP: Results for '` 開頭的佔位行數。

測試檔：以下「自動」的案例都寫在 `tests/build_package_test.sh`（計畫第 1 步指定的檔案），每條在註解裡標 TC 編號。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：邊角情況，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 打包完成時，明說這是草稿骨架（優先度 P1）

維護者的話（M1）：「`finish` 組好投稿包時，以前只印『wrote manuscript.qmd』，看起來像完成了；以後會寫明『還有 N 段結果和討論要人來寫，這是草稿骨架』。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | M1；D1；計畫 1(a) | 功能 | 分析計畫有兩個項目（id 為 `richness`、`evenness`），status 都是 `accepted`，專案有一個 run | 執行 `build_package.sh <專案>`（不加 `--render`） | 畫面上有這一整行：`wrote     submission/manuscript.qmd (scaffold: 2 Results section(s) and the Discussion still need prose)`；不再只有光禿禿的 `wrote     submission/manuscript.qmd` | 自動：`tests/build_package_test.sh` |
| TC-002 | D1；D4；計畫 1(b) | 功能 | 分析計畫有四個項目（一個 accepted、一個 proposed、一個 rejected、一個沒有 status），四個都有 id | 執行 build_package.sh | 畫面上的 N 是 4（`scaffold: 4 Results section(s) and the Discussion still need prose`），且 N 等於 `manuscript.qmd` 裡實際寫出的 `[GAP: Results for '` 行數 | 自動：`tests/build_package_test.sh` |
| TC-003 | D4；R3 | 功能 | 分析計畫（表格格式）有兩列有 id、一列有內容但沒有 id | 執行 build_package.sh | N 是 2：沒有 id 的那一列不算在 N 裡（它在 `manuscript.qmd` 裡有自己的 `[GAP: a plan row has no id …]`，且該 GAP 仍然存在） | 自動：`tests/build_package_test.sh` |
| TC-004 | R3（N=0 時） | 功能 | 分析計畫（表格格式，有 `id` 欄）只有一列，內容有寫但 id 欄是空的 | 執行 build_package.sh | 打包成功，畫面上是 `wrote     submission/manuscript.qmd (scaffold: 0 Results section(s) and the Discussion still need prose)`，不是不帶說明的光禿禿一行 | 自動：`tests/build_package_test.sh` |
| TC-005 | D3；計畫 1(d) | 功能 | 同 TC-001 的兩個 accepted 項目 | 執行 build_package.sh，打開寫出的 `submission/README.md` | README 裡有一句含 `scaffold` 與 `2 Results section(s)` 的話，位置在 `## How to reproduce the runs` 這個標題之前 | 自動：`tests/build_package_test.sh` |
| TC-006 | D3；D6；「Not in this PR」寫出哪些檔案不變 | 功能 | 同 TC-001 | 執行 build_package.sh | 與修改前一樣寫出同一批檔案（`provenance.json`、`methods.md`、`manuscript.qmd`、`README.md`、`ro-crate-metadata.json`、`figures/`、`scripts/`，以及該專案本來就會寫的 `references.bib`），一個都沒少、沒多 | 自動：`tests/build_package_test.sh` |

## User Story 2 — 逐項列出「還沒接受」的項目（優先度 P1）

維護者的話（M2）：「分析計畫裡還沒被你接受的項目，現在其實也會被放進結果；以後會逐項列出『這些還沒接受，送出前要接受或拿掉』。」

「未接受」＝ status 去掉前後空白、不分大小寫之後不是 `accepted`（包含 proposed、revised、rejected、空白）。除特別註明外，下列案例用表格格式的分析計畫，id 分別為 `acc`、`prop`、`rej`、`rev`、`none`（none 的 status 欄是空的）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | D2；M2；計畫 1(b) | 功能 | 計畫有一個 `prop`，status 為 `proposed` | 執行 build_package.sh | 畫面上有這一整行：`not accepted prop: status proposed - still in Results; accept it in analysis.md or remove it before submitting` | 自動：`tests/build_package_test.sh` |
| TC-011 | D2；計畫 1(b) | 功能 | 計畫有一個 `rej`，status 為 `rejected` | 執行 build_package.sh | 畫面上有 `not accepted rej: status rejected - still in Results; accept it in analysis.md or remove it before submitting` | 自動：`tests/build_package_test.sh` |
| TC-012 | D2；計畫 1(b) | 功能 | 計畫有一個 `none`，status 欄是空的 | 執行 build_package.sh | 畫面上有 `not accepted none: status (none) - still in Results; accept it in analysis.md or remove it before submitting`（空白顯示成 `(none)`） | 自動：`tests/build_package_test.sh` |
| TC-013 | D2 | 功能 | 計畫有一個 `rev`，status 為 `revised` | 執行 build_package.sh | 畫面上有 `not accepted rev: status revised - still in Results; accept it in analysis.md or remove it before submitting` | 自動：`tests/build_package_test.sh` |
| TC-014 | D2；計畫 1(b) | 功能 | 計畫同時有 `acc`（accepted）、`prop`、`rej`、`none` | 執行 build_package.sh | 有三行 `not accepted`（prop、rej、none），沒有任何一行提到 `acc` | 自動：`tests/build_package_test.sh` |
| TC-015 | D2（After the manuscript line） | 功能 | 同 TC-014 | 執行 build_package.sh，看輸出順序 | 三行 `not accepted` 都出現在 `wrote     submission/manuscript.qmd …` 那一行之後 | 自動：`tests/build_package_test.sh` |
| TC-016 | D2「what the build really does today」；D6；計畫 1(b) | 功能 | 同 TC-014（四個項目，其中三個未接受） | 執行 build_package.sh，讀 `manuscript.qmd` | 結果（Results）裡仍有四個小節，四個 id 各有一行 `[GAP: Results for '<id>' not written yet`；未接受的項目沒有被拿掉 | 自動：`tests/build_package_test.sh` |
| TC-017 | R3；計畫 1(b2) | 功能 | 計畫有兩個項目，status 欄分別寫成 `Accepted`（首字大寫）與 ` accepted `（前後有空格） | 執行 build_package.sh | 兩個都算已接受，畫面上沒有任何 `not accepted` 行 | 自動：`tests/build_package_test.sh` |
| TC-018 | D2；計畫 1(c) | 功能 | 計畫所有項目的 status 都是 `accepted` | 執行 build_package.sh | 畫面上完全沒有 `not accepted` 字樣 | 自動：`tests/build_package_test.sh` |
| TC-019 | R3（status 照寫出來，只去前後空白） | 功能 | 計畫有一個 `cap`，status 欄寫成 ` Proposed `（首字大寫、前後有空格） | 執行 build_package.sh | 該行是 `not accepted cap: status Proposed - still in Results; …`（保留 `Proposed` 的大小寫，空格已去掉） | 自動：`tests/build_package_test.sh` |
| TC-020 | R3（沒有 id 的列不產生 not accepted 行） | 例外 | 表格格式計畫有一列沒有 id、status 為 `proposed`，另有一列 `acc`（accepted） | 執行 build_package.sh | 畫面上沒有任何 `not accepted` 行（沒有 id 的那列不列出，它已有自己的 GAP） | 自動：`tests/build_package_test.sh` |
| TC-021 | R3（舊的區塊格式）；計畫 1 之 older-format 測試 | 功能 | 分析計畫用舊的「標題／項目符號加 `id:`、`question:`、`status:` 各一行」格式（即 `tests/build_package_test.sh` 開頭那種），所有項目 `status: accepted` | 執行 build_package.sh | 畫面上沒有 `not accepted` 行（不會被誤報成 `(none)`），N 等於項目數 | 自動：`tests/build_package_test.sh` |
| TC-022 | R3（舊的區塊格式） | 功能 | 舊區塊格式計畫有一個項目 `id: old1`、`status: proposed` | 執行 build_package.sh | 畫面上有 `not accepted old1: status proposed - still in Results; accept it in analysis.md or remove it before submitting` | 自動：`tests/build_package_test.sh` |

## User Story 3 — 不擋下打包，其餘行為照舊（優先度 P1）

維護者的話（M3）：「不會因此擋下打包（要不要擋，是另一個問題，之後再問你）。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | M3；D6 | 功能 | 同 TC-014（有三個未接受項目） | 執行 build_package.sh | 結束代碼是 0；`manuscript.qmd`、`README.md` 等檔案都有寫出且不是空的 | 自動：`tests/build_package_test.sh` |
| TC-031 | D6；「Not in this PR」零項目即停不變 | 例外 | 分析計畫的內容既不是表格也不是 id/question 區塊（如現有測試那句「We looked at richness …」） | 執行 build_package.sh | 與修改前一樣：結束代碼不是 0、訊息仍含 `matched 0 plan entries` 與 `id/question/source/method/why/status`；畫面上沒有 `scaffold` 字樣、沒有 `not accepted` 行、沒有 `wrote     submission/manuscript.qmd`。現有這三條斷言一字不改 | 自動：`tests/build_package_test.sh` |
| TC-032 | D6（不改結束代碼） | 功能 | 一個正常專案，機器上沒有 quarto | 先不加 `--render` 執行，再加 `--render` 執行 | 前者結束代碼 0 並印出「Not rendered」收尾說明；後者結束代碼 3，行為與現有 `--render` 測試相同 | 自動：`tests/build_package_test.sh` |
| TC-033 | D5 | 功能 | 修改後的 `scripts/build_package.sh` | 檢視約第 26 行與第 164 行的註解與約第 71 行的「沒有分析計畫」錯誤訊息 | 三處都不再說「只有 accepted 才有一節」（`one section per accepted entry`、`One section per figure the plan accepted` 兩句消失），改成說每個被讀到的項目都有一節 | 自動：`tests/build_package_test.sh`（檢查舊說法已不存在；行為本身由 TC-016 證明） |
| TC-034 | 「Not in this PR」分析計畫解析不變；R3（唯一的解析器改動是多回傳 status） | 功能 | 表格格式計畫，欄位順序打亂、含額外欄位、用 `問題` 當欄名；另一份舊區塊格式計畫完全沒有 `status:` 行 | 執行 build_package.sh | 兩份都照舊成功解析：每個 id 各有一節、題目文字成為圖說，與修改前相同；不因為沒有 status 而掉項目或失敗 | 自動：`tests/build_package_test.sh` |
| TC-040 | 「Not in this PR」：不因未接受而拒絕打包 | 不在範圍 | 分析計畫所有項目都是 `proposed` 或 `rejected`，沒有任何 accepted | 執行 build_package.sh | 仍然打包成功（結束代碼 0）、每個項目都在結果裡，每個都被 `not accepted` 列出；沒有任何拒絕或「無法打包」的訊息 | 自動：`tests/build_package_test.sh` |
| TC-041 | 「Not in this PR」：不新增 `confirm_finish.sh` 之類的 hook | 不在範圍 | 修改後的 repo | 檢查 `hooks/` | 沒有新增 `hooks/confirm_finish.sh`，`hooks/hooks.json` 沒有新增與 finish／build_package 有關的項目（驗收時另以 `git diff main...HEAD -- hooks/` 為空確認） | 自動：`tests/build_package_test.sh`（檢查檔案不存在） |
| TC-042 | D7；計畫第 3 步（只改引用舊輸出行的文件） | 不在範圍 | 修改後的 repo | 在 `commands/`、`docs/`、`scripts/intro/*/finish.txt` 找引用舊行 `wrote     submission/manuscript.qmd` 的地方 | 凡有引用的地方，都同時帶新的 `(scaffold:` 說明；沒有引用的文件（目前 `finish.txt`、`commands/finish.md`、`docs/FINISH.md` 都沒有）不被改動 | 自動：`tests/build_package_test.sh` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 憲法第 9 條（缺口要明寫在輸出裡） | 功能 | 兩個 accepted 項目、其中一個沒有圖 | 執行 build_package.sh | `manuscript.qmd` 裡每個結果段的 `[GAP: Results for …]`、沒有圖的 `[GAP: no figure file …]`、討論段的 `[GAP: not drafted …]` 都仍在；新增的說明沒有取代或吞掉任何一個 GAP，`manuscript.qmd` 裡也沒有新增 HTML 註解 | 自動：`tests/principle_9_test.sh`、`tests/package_gaps_test.sh`（原樣通過） |
| TC-051 | 憲法第 1 條（腳本標頭要寫明替代方案） | 功能 | 修改後的 `scripts/build_package.sh` | 跑標頭檢查 | 標頭仍有 `# Not Quarto manuscript/MECA: …`，檢查通過 | 自動：`tests/scripts_name_their_alternative.sh` |
| TC-052 | 憲法第 3 條（不寫死路徑） | 功能 | 修改後的 `scripts/build_package.sh` 與新增的輸出文字 | 跑路徑檢查 | 新增的輸出與註解沒有個人路徑、叢集路徑 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-053 | 安全網（計畫：未動任何 gate） | 功能 | 修改後的 repo | 跑 hook 相關測試，並比對 `hooks/` | `hooks/` 無改動；`tests/confirm_launch_test.sh`、`tests/confirm_cleanup_test.sh`、`tests/confirm_walkthrough_test.sh` 與 `main` 同樣通過 | 自動：這三個測試檔 |
| TC-054 | 開發流程「每階段全綠」；計畫「除舊輸出行斷言外不改既有期望」 | 功能 | 修改後的 repo | 在 WSL 跑 `bash tests/run_all.sh`；比對 `tests/` 在 `main...HEAD` 的差異 | 全綠；既有測試只有「新增」，沒有刪除或放寬的斷言（計畫稱只有逐字斷言舊輸出行的才會改，目前 `main` 上只有 `tests/build_package_test.sh` 那條「不應印出 wrote」的反向斷言，且它不需要改；若改了，ledger 必須逐條列出） | 自動：`tests/run_all.sh` |
