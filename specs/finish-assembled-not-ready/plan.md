---
id: finish-assembled-not-ready
title: build_package.sh 成功時要說「組好了但還不是成品」：印出還有幾處 Results 佔位、Discussion 未寫（issue #12 的第二個建議）
tier: B
kinds: backend
lane: L16-finish-not-ready（只動 scripts/build_package.sh、tests/build_package_test.sh、docs/FINISH.md；不與 fetch／push 任務、platform、web、雲端、hooks、測試切分任何檔相交）
branch: fix/finish-assembled-not-ready
base: v3
source: GitHub issue #12（OPEN）建議的第二點。第一點（拒絕未 accepted 的條目）已由 PR #182 做完；第二點被當時的 TC-G23 明文列為「out of scope」並用測試鎖住「訊息不變」，現在補做
---

# finish-assembled-not-ready

> 本檔由 Explore 子代理草擬（2026-10-28）給 developer-agent 審。A 級：新增一行輸出文字，不改檔案內容、不改 exit code、不改閘門；屬「更嚴的安全網」（讓代理人與人不會把鷹架當成品）。
> **注意**：#93 說 #12 屬 v2（`main`）。v3 分支上它的第一半已進，第二半沒有；本任務只在 `v3` 做。若維護者希望同一修補也落 v2，那是另一個 PR，不在本計畫。

## 目標
`scripts/build_package.sh` 寫完 `submission/manuscript.qmd` 之後，多印一行明講「這是組好的鷹架，不是完成的文件」，並數出 Results 還有幾處 `[GAP: Results for '…' not written yet …]` 等著補文字、Discussion 還沒寫。對使用者／代理人的意義：看到 `wrote submission/manuscript.qmd` 不再被誤認為可交付（issue #12 的第一個失誤：「I treated the first successful `build_package.sh` run as if the deliverable were complete」）。

## 維護者原話（verifier 出題用）
逐字取自 issue #12：
- 「`build_package.sh` printed `wrote submission/manuscript.qmd` after assembling the package — but the Results section it wrote was only placeholders … nothing in the tool's own output distinguishes "assembled, ready" from "assembled, still has N unfilled placeholder(s)."」→ 輸出必須帶出 N；N 與 manuscript.qmd 裡實際的 Results 佔位數一致。
- 「Have the tool's own success message distinguish "assembled" from "ready" — e.g. `wrote submission/manuscript.qmd (4 Results placeholder(s) still need prose — not yet a finished document)` — so an agent (or a person) can't misread a scaffold as a finished deliverable from the printed output alone.」→ 訊息要含 `placeholder(s)`、`still need prose`、`not yet a finished document` 這三組字樣（verifier 可據此斷言）。
- 「rather than silently building around them」（第一個建議，已由 PR #182 完成）→ 本任務不得動拒絕邏輯、`status` 判斷、exit code 2 的訊息。

## 範圍：檔案（只准改這些）
- `scripts/build_package.sh`
- `tests/build_package_test.sh`（新增斷言段落；**唯一允許改動既有斷言的地方是 TC-G23**，見作法 4；其餘既有斷言原樣）
- `docs/FINISH.md`（「Only accepted entries are packaged (issue #12)」小節後加一小節，說明成功訊息的新行）
- `specs/finish-assembled-not-ready/ledger.md`（新，executor 進度帳本）

**禁止碰**：`hooks/`、`skills/finish/SKILL.md`（它已教代理人「搜尋每個 `[GAP: ...]` 並回報」，行為不變，不順手改）、`tests/package_gaps_test.sh`、`scripts/package_crate.py`、`scripts/collect_provenance.py`、`platform/**`、`.github/`、`tests/platform_shard_*`、`tests/platform_test.sh`、`tests/run_all.sh`、`tests/quarantine.txt`、`*aws*`／`*azure*`／`build.py`／`compute_envs.py`、`.specify/memory/constitution.md`。

## 作法
1. 在 `scripts/build_package.sh` 印出 `wrote     submission/manuscript.qmd`（第 434 行附近）**緊接著**多印一行（`wrote     submission/manuscript.qmd` 這行本身**一個字都不改**，因為 TC-G06a 與別的測試用 `grep -qF` 認它）：
   ```
   note      manuscript.qmd is assembled, not finished: K Results placeholder(s) still need prose, and the Discussion is not drafted - not yet a finished document
   ```
   - `K` ＝ `manuscript.qmd` 中以 `[GAP: Results for '` 開頭的行數（每個計畫條目產生一行，見檔內 `print("[GAP: Results for '%s' not written yet …`）。用 `grep -c` 對寫好的 `$QMD` 數，不要另算一份（單一事實來源＝檔案內容，條目被 `emitted` 之類邏輯略過時也不會對不上）。
   - 若 `K` 為 0（理論上不會，因每個條目必有一行；防呆用）：改印 `note      manuscript.qmd is assembled, not finished: the Discussion is not drafted - not yet a finished document`，仍含 `not yet a finished document`。
   - Discussion 那句永遠印（`manuscript.qmd` 的 Discussion 區固定是 `[GAP: not drafted …`）。
2. 這行走**標準輸出**（與同區其他 `wrote` 行一致），不是 stderr。
3. `--render` 路徑、`RENDER=0` 的說明文字、後續流程完全不動；新行在 `wrote …/README.md` 之前或之後皆可，但必須在 `package_crate.py` 之前印（讓它出現在 `wrote` 區塊內）；挑緊接 `manuscript.qmd` 那行。
4. **TC-G23 的處理**：`tests/build_package_test.sh` 第 402–404 行現在斷言「新字樣不得出現」（`TC-G23 success message unchanged`，註解寫「the issue's second suggestion is out of scope」）。本任務正是做那個 out-of-scope 的建議，所以 TC-G23 必須**反轉**：改成斷言成功訊息**含** `placeholder(s)`、`still need prose`、`not yet a finished document`，並把註解改成指向本計畫。這是本任務唯一對既有斷言的改動，要在 ledger 與 PR 描述裡明講；閱卷者用 `git diff` 確認其他既有斷言未動。
5. `docs/FINISH.md`：加小節「The success message says assembled, not ready (issue #12)」，兩三句：說明那行、`K` 的算法、以及「出現這行表示還有文字要寫；全部補完後這行才會消失」——**注意**：目前的程式不會因為使用者補完文字而重新印（腳本只在組裝時跑）；文件只能寫「重新組裝時，數字反映 `manuscript.qmd` 當下的內容」，不得寫成腳本會監看補寫進度。

## 失敗先行測試
都在 `tests/build_package_test.sh`，沿用檔內 `gate_proj`／`blk`（見 `# TC-G06a/b` 段）建專案，`CITE_CURL=false bash "$S" "$G"`。現在全紅（輸出沒有新行）。

1. `TC-N01 success output says assembled, not finished`：兩個 accepted 條目（`richness`、`evenness`）→ rc 0，stdout 含 `still need prose`、`placeholder(s)`、`not yet a finished document`。
2. `TC-N02 K equals the placeholders in the file`：同上情境，stdout 的 `K`（從 `note` 行以 `sed -E 's/.*: ([0-9]+) Results.*/\1/'` 取出）等於 `grep -c "^\[GAP: Results for '" submission/manuscript.qmd`，且在兩條目情境為 `2`、一條目情境為 `1`。
3. `TC-N03 the wrote line is byte-for-byte unchanged`：stdout 仍含 `wrote     submission/manuscript.qmd`（`grep -qF`，與 TC-G06a 同字串），且該行**獨立成行**（整行等於這串）。
4. `TC-N04 the note goes to stdout, not stderr`：`2>/dev/null` 時 note 行仍在；`2>&1 >/dev/null` 時不含 note 行。
5. `TC-N05 a refused build prints no note`：有 `status: proposed` 的條目 → rc 2、stdout 與 stderr 皆不含 `not yet a finished document`（拒絕路徑不變；既有 TC-G01.. 系列原樣綠）。
6. `TC-N06 note count follows the file`：先組一次（2 個條目），把 `manuscript.qmd` 其中一個 `[GAP: Results for 'richness' …]` 行以 `sed` 改寫成普通句子，**不重新跑腳本**，驗證 `grep -c` 的算法得 `1`（鎖定「數的是檔案內容」這個定義；實際重跑腳本會覆蓋該檔，所以此案例測的是 `K` 的數法，不測腳本覆寫行為）。
7. `TC-G23`（反轉後）：成功訊息含上述三組字樣。

## 完成標準（done when）
- 新測試與反轉後的 TC-G23 綠；`bash tests/build_package_test.sh` 其餘既有斷言綠；`bash tests/package_gaps_test.sh`、`tests/package_crate_test.sh` 原樣綠；全套（WSL 內 `bash tests/run_all.sh`）綠。
- `git diff -U0 origin/v3...HEAD -- scripts/build_package.sh` 只新增 `note` 行相關的行；拒絕邏輯（`mode == "check"` 區塊）、`wrote` 各行、exit code 無變動。
- `git diff origin/v3...HEAD -- tests/build_package_test.sh` 只有新增段落，加上 TC-G23 那 3–4 行的反轉。
- `git diff --name-only origin/v3...HEAD` 只出現「範圍」列的檔案。

## 環境事實
- `scripts/build_package.sh`（origin/v3）：Results 佔位由內嵌 Python（`PLAN_PY`，results 模式）印出，格式 `[GAP: Results for '%s' not written yet - say what it shows, from the data; every number must trace to a file or to a script in scripts/]`；Discussion 固定寫入 `*[GAP: not drafted - the discussion is the authors' scientific` 開頭（前面有 `*`，所以 `grep -c "^\[GAP: Results for '"` 不會把它算進 K）。`echo "wrote     submission/manuscript.qmd"` 在 `{ … } > "$QMD"` 群組之後。`$QMD="$OUT/manuscript.qmd"`。
- 閘門（PR #182，commit 84e4e06／測試 69092c2）：`mode == "check"` 只放行 `accepted`／`done`，其餘 exit 2；訊息文字被 `tests/build_package_test.sh` TC-G* 系列逐行鎖住，不要碰。
- `skills/finish/SKILL.md` 第 123–148 行已要求代理人「Search the output for … every `[GAP: ...]` line」並向使用者回報；新行是給只看腳本輸出就誤判的人／代理人，與該段不衝突。
- `docs/FINISH.md` 第 132 行起是「Only accepted entries are packaged (issue #12)」小節。
- 測試輔助：`tests/build_package_test.sh` 第 330 行 `run_gate()`（`2>&1 >/dev/null`，只收 stderr，**不適用**於檢查 stdout，新測試要自己 `out=$(… 2>/dev/null)`，仿第 397 行）；`gate_proj <name>` 與 `blk <id> <status>` 造 `analysis/analysis.md`。
- repo CLAUDE.md「For the executor and verifier」：一個測試檔用 `bash tests/<name>.sh`；全套須在 WSL／Linux；不得改 `spec.md`、`test-case*.md`、憲法、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`；不得連站台或 HPC。
- 已知環境紅：見 `dev-plans/README.md` 通例（`test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 單獨紅視同綠）。

## 不做
- 不改閘門、不改 `status` 判斷、不改任何 exit code。
- 不把 `K > 0` 當失敗（代理人還要補文字是正常流程，exit code 維持 0）。
- 不在 `manuscript.qmd` 本身加任何字（檔案內容逐位元不變）。
- 不做「補完後自動重算」或監看；不改 `skills/finish/SKILL.md`。
- 不處理 issue #12 的其他部分（第一個建議已完成）。

## 待裁決選項（developer-agent 填入下方「裁決」）
1. 訊息用英文（與腳本其他輸出一致）：＿＿＿（預設：英文）。
2. 反轉 TC-G23 而不是另開新測試：＿＿＿（預設：反轉，因為兩者斷言互斥，並存必有一紅）。
3. 是否同一修補也要落 v2（`main`，#93 說 #12 屬 v2）：＿＿＿（預設：本計畫只做 v3，v2 另議）。

## 裁決
- **D0（2026-10-28 14:55，developer-agent）**：級別改 **B（網頁外）**——成功訊息多一行 `note`，是使用者看得到的行為改變；verifier 通過＋CI 綠由 developer-agent 自合，事後在每日清單寫「以前／以後」。
- **D1**：三項照預設——①訊息用英文；②反轉 TC-G23（兩條斷言互斥，不能並存），PR 說明逐條寫以前／以後／理由；③只做 v3，v2（main）不動。
- **D2**：K 必須從實際寫出的 manuscript 算（`grep -c "^\[GAP: Results for '"`），不准另外推算；K=0 時也要印出且語意正確（不得說「0 處」卻仍稱未完成的佔位）——訊息仍須說 Discussion 未寫。

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
