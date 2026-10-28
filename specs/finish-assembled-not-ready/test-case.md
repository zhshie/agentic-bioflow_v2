# 測試案例：build_package.sh 成功時說明「組好了但還不是成品」

**規格**：`specs/finish-assembled-not-ready/plan.md`（本任務沒有獨立 spec.md；依據是計畫與 GitHub issue #12 維護者原話，見計畫「維護者原話」）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：「note 行」＝`build_package.sh` 成功時多印的那一行，開頭是 `note` 加空格。「K」＝note 行裡的數字，代表 Results 還有幾處佔位文字（`manuscript.qmd` 裡以 `[GAP: Results for '` 開頭的行）等著補寫。「wrote 行」＝原本就有的 `wrote     submission/manuscript.qmd` 那行。

所有「自動」案例都寫在 `tests/build_package_test.sh`，沿用檔內 `gate_proj`／`blk` 造專案，指令是 `CITE_CURL=false bash "$S" "$G"`；標準輸出一律用 `out=$(… 2>/dev/null)` 取（不可用只收 stderr 的 `run_gate`）。「兩個條目」＝`richness`、`evenness` 都是 `status: accepted`；「一個條目」＝只有 `richness`。每條測試的註解要寫上它的 TC 編號。

## User Story 1 — 成功訊息要說「組好了，但還不是成品」（優先度 P1）

維護者原話（issue #12）：「`build_package.sh` printed `wrote submission/manuscript.qmd` after assembling the package — but the Results section it wrote was only placeholders … nothing in the tool's own output distinguishes "assembled, ready" from "assembled, still has N unfilled placeholder(s)."」與「Have the tool's own success message distinguish "assembled" from "ready" — e.g. `wrote submission/manuscript.qmd (4 Results placeholder(s) still need prose — not yet a finished document)` — so an agent (or a person) can't misread a scaffold as a finished deliverable from the printed output alone.」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-N01 | 計畫「失敗先行測試」1；原話「`placeholder(s)`、`still need prose`、`not yet a finished document`」 | 功能 | 兩個條目都是 accepted | 跑 `build_package.sh`，只看標準輸出 | 標準輸出同時含 `placeholder(s)`、`still need prose`、`not yet a finished document` 三組字樣 | 自動：`tests/build_package_test.sh` |
| TC-N02 | 作法 1（note 行全文） | 功能 | 兩個條目都是 accepted | 同上 | 標準輸出有一整行，內容逐字等於 `note      manuscript.qmd is assembled, not finished: 2 Results placeholder(s) still need prose, and the Discussion is not drafted - not yet a finished document`（`note` 後面是 6 個空格，與同區 `wrote     ` 對齊） | 自動 |
| TC-N03 | 作法 1「Discussion 那句永遠印」 | 功能 | 一個條目 accepted | 同上 | note 行含 `the Discussion is not drafted`（Discussion 未寫這件事不因 K 的大小而消失） | 自動 |
| TC-N04 | 原話「輸出必須帶出 N」；失敗先行測試 2；D2 | 功能 | 兩個條目 accepted，跑完後 `submission/manuscript.qmd` 已存在 | 以 `sed -E 's/.*: ([0-9]+) Results.*/\1/'` 從 note 行取出 K，再對 `submission/manuscript.qmd` 數 `grep -c "^\[GAP: Results for '"` | 兩個數字相等（K 是檔案內容數出來的，不是另外推算的） | 自動 |
| TC-N05 | 失敗先行測試 2（兩個條目） | 功能 | 兩個條目 accepted | 同 TC-N04 | K 等於 `2` | 自動 |
| TC-N06 | 失敗先行測試 2（一個條目） | 功能 | 只有一個條目 accepted | 同 TC-N04 | K 等於 `1` | 自動 |
| TC-N07 | 作法 1「以 `[GAP: Results for '` 開頭的行數」；環境事實「Discussion 前面有 `*`」 | 功能 | 兩個條目 accepted、`analysis/figures/` 沒有任何圖（所以檔裡另有 `[GAP: no figure file starting with …` 和 Discussion 的 GAP 行，`[GAP:` 總行數大於 2） | 跑腳本，取 K | K 仍是 `2`：只算 Results 佔位，不把「找不到圖檔」或 Discussion 的 GAP 算進去 | 自動 |
| TC-N08 | 失敗先行測試 3；作法 1「wrote 行一個字都不改」 | 功能 | 兩個條目 accepted | 跑腳本，取標準輸出 | 輸出含 `wrote     submission/manuscript.qmd`（以 `grep -qF` 固定字串比對），且該行獨立成行（整行就等於這串，後面沒有附加文字） | 自動 |
| TC-N09 | 作法 3「挑緊接 manuscript.qmd 那行」 | 功能 | 兩個條目 accepted | 跑腳本，取標準輸出，找到 wrote manuscript.qmd 那行 | 下一行就是 note 行；且 note 行出現在 `package_crate.py` 的輸出之前（在 wrote 區塊內） | 自動 |
| TC-N10 | 失敗先行測試 4；作法 2 | 功能 | 兩個條目 accepted | 跑腳本並丟掉 stderr（`2>/dev/null`） | note 行仍然在輸出裡（它走標準輸出） | 自動 |
| TC-N11 | 失敗先行測試 4；作法 2 | 功能 | 兩個條目 accepted | 跑腳本，只收 stderr（`2>&1 >/dev/null`） | stderr 內容不含 note 行（含 `not yet a finished document` 就算失敗） | 自動 |
| TC-N12 | 失敗先行測試 6；D2 | 功能 | 已組好一次（兩個條目），不重新跑腳本；用 `sed` 把 `manuscript.qmd` 裡 `richness` 的 `[GAP: Results for 'richness' …]` 那行改寫成普通句子 | 對改過的檔案數 `grep -c "^\[GAP: Results for '"` | 得到 `1`（鎖定「K 數的是檔案現在的內容」這個定義；此條測的是數法，不是腳本覆寫行為） | 自動 |
| TC-N13 | 失敗先行測試 7；計畫作法 4（反轉 TC-G23） | 功能 | 沿用原 TC-G06a 情境：一個 accepted、一個 done 的專案 | 跑腳本，取標準輸出 | 成功訊息含 `placeholder(s)`、`still need prose`、`not yet a finished document`（原本是斷言「不得出現」，現在反過來；註解改成指向本計畫，不再寫「out of scope」） | 自動 |
| TC-N14 | 作法 5 | 功能 | 打開 `docs/FINISH.md` | 找「Only accepted entries are packaged (issue #12)」小節之後 | 緊接著有一節標題為「The success message says assembled, not ready (issue #12)」，用兩三句說明：那一行長什麼樣、K 怎麼算（數 `manuscript.qmd` 裡 Results 佔位行） | 手動：閱卷者讀 `docs/FINISH.md` 並以 `git diff origin/v3...HEAD -- docs/FINISH.md` 核對 |
| TC-N15 | 作法 5 的「注意」 | 功能 | 同 TC-N14 | 讀新小節 | 文字寫的是「重新組裝時，數字反映 `manuscript.qmd` 當下的內容」；沒有寫成腳本會監看補寫進度、也沒有寫「補完後這行會自動消失」 | 手動：同 TC-N14 |
| TC-N16 | 原話第 3 條（拒絕邏輯不動）；失敗先行測試 5 | 例外 | 一個條目的 `status: proposed` | 跑腳本，分別收標準輸出與 stderr | 結束碼 `2`；標準輸出與 stderr 都不含 `not yet a finished document`；也沒有任何 note 行；拒絕訊息與沒改前一樣 | 自動 |
| TC-N17 | D2、作法 1 的 K=0 防呆 | 例外 | 讓腳本算出的 K 為 0 的情況（正常輸入不會發生，因為每個條目必有一行；測試需自己造，例如用只對該 `grep -c` 回報 0 的替身指令） | 跑到寫完 manuscript 的那一步 | 只印出一行 note，內容逐字等於 `note      manuscript.qmd is assembled, not finished: the Discussion is not drafted - not yet a finished document`；不得出現「0 Results placeholder(s)」，也不得多出一行單獨的 `0` 或重複的 note 行 | 自動（若造不出 K=0，執行者須在 ledger 說明，閱卷時此條列待確認） |
| TC-N18 | 原話第 3 條；計畫完成標準 | 例外 | 在改完的分支上 | 跑 `bash tests/build_package_test.sh` | 除 TC-G23（已反轉）外，既有斷言（TC-G01..G28、TC-038、TC-040 等）全部維持綠，拒絕訊息逐行未變 | 自動 |
| TC-N19 | 計畫「不做」第 2 條 | 不在範圍 | 兩個條目 accepted，Results 仍是佔位 | 跑腳本，看結束碼 | 結束碼仍是 `0`（有佔位待補是正常流程，不算失敗） | 自動 |
| TC-N20 | 計畫「不做」第 3 條 | 不在範圍 | 兩個條目 accepted | 跑腳本，讀 `submission/manuscript.qmd` | 檔案內不含 note 行的任何字（無 `not yet a finished document`、`assembled, not finished`）；Discussion 區仍是 `*[GAP: not drafted …`；閱卷者再用 base 版與新版各組同一專案，兩份 `manuscript.qmd` 逐位元相同 | 自動（檔內不含新字）＋手動（閱卷者以 base／HEAD 各跑一次，`cmp` 比對 manuscript.qmd） |
| TC-N21 | 計畫完成標準第 2 條；「不做」第 1 條；作法 3 | 不在範圍 | 在改完的分支上 | 閱卷者執行 `git diff -U0 origin/v3...HEAD -- scripts/build_package.sh` | 只新增 note 行相關的行；`mode == "check"` 拒絕區塊、`status` 判斷、各條 `wrote` 行、exit code、`--render` 路徑與 `RENDER=0` 的說明文字都沒有被改動或刪除 | 手動：閱卷者逐行讀上述 diff |
| TC-N22 | 計畫完成標準第 3 條；作法 4 | 不在範圍 | 在改完的分支上 | 閱卷者執行 `git diff origin/v3...HEAD -- tests/build_package_test.sh` | 只有新增的測試段落，加上 TC-G23 那 3–4 行的反轉；沒有其他既有斷言被刪除、放寬、跳過或改期望值；ledger 與 PR 描述有明講 TC-G23 被反轉 | 手動：閱卷者讀上述 diff 與 `specs/finish-assembled-not-ready/ledger.md` |
| TC-N23 | 計畫完成標準第 4 條；「範圍：檔案」「禁止碰」 | 不在範圍 | 在改完的分支上 | 閱卷者執行 `git diff --name-only origin/v3...HEAD` | 只出現 `scripts/build_package.sh`、`tests/build_package_test.sh`、`docs/FINISH.md`、`specs/finish-assembled-not-ready/` 底下的檔案；`skills/finish/SKILL.md`、`tests/package_gaps_test.sh`、`hooks/`、`platform/**`、`.github/`、憲法、`docs/ROADMAP.md` 都不在其中 | 手動：閱卷者執行上述指令 |
| TC-N24 | 計畫「不做」第 4 條 | 不在範圍 | 在改完的分支上 | 搜尋 `scripts/build_package.sh` 與 `docs/FINISH.md` 的新增內容 | 沒有任何「補完後自動重算」「監看」的程式或文字承諾；note 行只在腳本被執行時印一次 | 手動：閱卷者讀 `git diff origin/v3...HEAD -- scripts/build_package.sh docs/FINISH.md` |

## 憲法與安全網

第 9 條（`.specify/memory/constitution.md` 第 104–108 行：「A gap is written visibly into the output」，檢查是 `tests/principle_9_test.sh`）：這次改動就是在加強「缺口要看得見」，但不能因此弄丟或藏起原有的缺口行。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-N25 | 第 9 條：缺口寫在輸出裡看得見 | 功能 | 兩個條目 accepted，跑完腳本 | 讀 `submission/manuscript.qmd`，並跑 `bash tests/principle_9_test.sh` | 檔內仍有每個條目的 `[GAP: Results for '…' not written yet …` 可見文字（不是 HTML 註解）和 Discussion 的 `[GAP: not drafted`；`principle_9_test.sh` 維持全綠（含「manuscript 沒有程式碼區塊」那條，新行不得帶入 ` ```{ `） | 自動：`tests/principle_9_test.sh`、`tests/build_package_test.sh` |
| TC-N26 | 第 9 條：缺口檢查原樣綠 | 功能 | 在改完的分支上 | 跑 `bash tests/package_gaps_test.sh` 與 `bash tests/package_crate_test.sh` | 兩檔都原樣全綠，且這兩個檔案沒有被修改（`package_gaps_test.sh` 在禁止碰清單內） | 自動：`tests/package_gaps_test.sh`、`tests/package_crate_test.sh` |
