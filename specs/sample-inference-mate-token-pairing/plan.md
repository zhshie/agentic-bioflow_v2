---
id: sample-inference-mate-token-pairing
title: 取樣本名與配對 R1/R2 時，要在「帶副檔名」的檔名上比對，且只在最強的那個 R1/R2 記號處截斷（現在 S1_R1.fastq.gz 配不起來，Patient_1_Tumor 與 Patient_2_Tumor 會被併成同一個樣本 Patient）
tier: A
kinds: backend
lane: L23-sample-inference
branch: test/sample-inference-mate-token-pairing
base: origin/v3@bb0e8d6（2026-10-29 量；行號取自此，executor 開工前用 `git show origin/v3:<檔>` 重查，不對以實際內容為準）
source: 2026-10-29 清理掃描（A 級：把程式修回它自己註解與 docstring 已經寫的規則；合法的 `_R1_001` 命名行為不變，既有 golden 不動）
---

# sample-inference-mate-token-pairing

> 本檔由 developer-agent 的 subagent 寫（2026-10-29），只有計畫、沒有程式。A 級 → verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
`scripts/utils/sample_inference.py` 負責「從檔名推出樣本名、把 R1/R2 兩個檔配成一對」，`generate_samplesheet.py` 用它寫 samplesheet。現在有兩個真實錯誤，都能用小檔名重現：
1. 標準雙端命名 `S1_R1.fastq.gz` + `S1_R2.fastq.gz`（以及 `S1_1.fastq.gz` + `S1_2.fastq.gz`）配不起來，變成兩個各缺一半的樣本，工具會拒寫（不是靜默錯，但合法資料被拒）。
2. 檔名中間有數字或第二個 `_R1`/`_1` 類記號時，樣本名被截太多：`Patient_1_Tumor_R1/R2` 與 `Patient_2_Tumor_R1/R2` 都變成 `Patient`，**兩個真實樣本被併成一個，只留後面那一對，前一對靜默消失**（`match_read_pairs` 的字典覆蓋，見證據）。這會讓 samplesheet 少樣本卻不報錯。
修回程式碼註解本來就寫的規則；對使用者唯一的可見變化是：本來被拒或被併掉的合法資料現在正確處理。

## 維護者原話（verifier 出題用）
- 本次派工指示（2026-10-29 清理掃描）：「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- 檔頭承諾（`sample_inference.py` 第 1–5 行）：從檔名推出樣本名、把屬於同一對的檔配起來。
- `generate_samplesheet.py` 的作法註解（約第 69–81 行）：配不起來就停下來問，不從檔名猜單端（所以本件**不得**放寬 `unpaired` 的停止行為，只是讓該配的配起來）。
- A 級的前提：`_R1_001` 這種現行能配的命名，樣本名、鍵、輸出必須逐位元不變；若發現修正需要改它，停下回報 BLOCKED。

## 範圍：檔案（只准改這些）
- `scripts/utils/sample_inference.py`（只動 `extract_sample_info` 內去副檔名與取樣本名那段；`match_read_pairs`、`_get_sample_key` 非必要不動）
- `tests/sample_inference_test.sh`（**新檔**；檔頭前 40 行內要有 `# Nothing existing: …` 至少 15 個字，例如「現有 generate_samplesheet_test.sh 只用 `_R1_001` 形式的檔名（mkpairs），沒有任何測試直接檢查 `_R1.fastq.gz`、`_1.fastq.gz` 或樣本名含數字時的配對與樣本名，所以另開新檔」）
- **不准碰**：`scripts/generate_samplesheet.py`、`scripts/utils/schema_roles.py`、`scripts/utils/file_discovery.py`、`tests/generate_samplesheet_test.sh` 與 `tests/fixtures/samplesheet_golden/`（golden 必須逐位元不變）、任何其他既有測試的既有斷言。

## 作法
- **證據一（去副檔名後才比對，所以帶 `.` 的記號永遠對不上）**：`sample_inference.py` 第 73–78 行先把 `.fastq.gz` 等副檔名剝掉；第 89–91 行再對剝完的字串跑 `R1_PATTERNS + R2_PATTERNS` 並 `re.sub(pattern + r'.*', '', …)`。但第 41–46、50–55 行的樣式中 `_R1[_.]`（8 分，註解「_R1. or _R1_」）、`_1[_.]`（5 分，註解「_1. or _1_」）、`_R1\.f`（6）、`_1\.f`（4）以及 R2 的對應項，都要求記號後面還有 `.` 或 `_`——副檔名已被剝掉，永遠對不上。只有 `_R1_\d{3}`（`_R1_001`）形式能用。
- **證據二（配對鍵取自去副檔名的字串）**：`_get_sample_key`（第 114–123 行）用 `extract_sample_info`，所以 `S1_R1.fastq.gz`／`S1_R2.fastq.gz` 的鍵是 `S1_R1`／`S1_R2`，不同鍵、配不起來。分類（第 144–145 行）卻用完整檔名打分，所以 R1/R2 分得出來，只是鍵不同。
- **證據三（每個樣式依序各砍一次，砍太多）**：第 89–91 行是 for 迴圈，每個樣式都把「記號之後的全部」砍掉，後面的樣式接著砍已經截短的字串。`Sample_1_S1_L001_R1_001.fastq.gz` 與 `Sample_2_S2_L001_R1_001.fastq.gz` 的樣本名都被砍成 `Sample`；`Patient_1_Tumor_R1.fastq.gz` 變 `Patient`；`A_2_x_1.fastq.gz` 變 `A`。
- **證據四（併掉的樣本靜默消失）**：`match_read_pairs` 第 171–172 行對同鍵的第二個 R1 只寫註解「Multiple R1 files for same sample (should not happen)」並覆蓋。實測（origin/v3 抽出後執行）：`match_read_pairs` 輸入 `Patient_1_Tumor_R{1,2}` 與 `Patient_2_Tumor_R{1,2}` 四個檔，只回一個鍵 `Patient`，內容是 Patient_2 那一對。
- **決定（修法，不改介面）**：
  1. 取樣本名時，**在保留副檔名的完整檔名上**比對 R1/R2 樣式（讓 `_R1.f`、`_1.f`、`_R1[_.]` 這些原本寫好的樣式真的有機會命中），剝完記號後再去副檔名。
  2. 把 R1 與 R2 樣式合併後**依分數由高到低**排，**第一個命中的樣式只砍一次就停**（`break`），不再逐個套用。這樣 `Patient_1_Tumor_R1.fastq.gz` 命中 `_R1[_.]`，只砍 `_R1.fastq.gz`，樣本名 `Patient_1_Tumor`。
  3. `S1_R1_001`／`S1_R2_001` 仍得同一個樣本名 `S1`（R1/R2 樣式必須砍在各自記號處，使兩邊結果相同）；`_get_sample_key` 的 lane 後綴規則（非 `L001` 才加）不動。
- 不新增或改任何使用者可見文字；不改 `unpaired` 停止行為與其訊息。

## 失敗先行測試
先寫、在改程式前跑一次，確認紅，紅的輸出貼進 ledger。新檔 `tests/sample_inference_test.sh`，風格同 `tests/generate_samplesheet_test.sh`（`set -uo pipefail`、`t`／`has` 小幫手、結尾 `exit` 依 `fails`），用 `python3 -c` 載入 `scripts` 目錄下的 `utils.sample_inference`（不連網、不碰叢集）。
- `T1_pairs_R1_dot_ext`：`match_read_pairs(["/d/S1_R1.fastq.gz","/d/S1_R2.fastq.gz"])` 恰一個鍵，且 `r1`、`r2` 都不是 None。**現在紅**：兩個鍵 `S1_R1`／`S1_R2`，各缺一半。
- `T2_pairs_digit_mate`：`S1_1.fastq.gz` + `S1_2.fastq.gz` 同上。**現在紅**：鍵 `S1_1`／`S1_2`。
- `T3_distinct_samples_kept`：`Patient_1_Tumor_R{1,2}.fastq.gz` 與 `Patient_2_Tumor_R{1,2}.fastq.gz` 回兩個鍵，各自 `r1`／`r2` 皆在，樣本名分別為 `Patient_1_Tumor`、`Patient_2_Tumor`。**現在紅**：只有一個鍵 `Patient`。
- `T4_illumina_style_names_not_collapsed`：`Sample_1_S1_L001_R{1,2}_001.fastq.gz` 與 `Sample_2_S2_L001_R{1,2}_001.fastq.gz` 回兩個不同鍵（樣本名各自含 `Sample_1`／`Sample_2`）。**現在紅**：兩者同為 `Sample`，只剩一對。（執行者需先在 origin/v3 實跑確認這一項確實紅，若只在 T3 紅則依實測在 ledger 說明並保留 T3。）
- 對照組（必須一直綠，改前改後都綠）：`S1_R1_001.fastq.gz`+`S1_R2_001.fastq.gz` 配成一對、樣本名 `S1`；`S1_L002_R1_001`／`_R2_001` 的鍵為 `S1_L002`；多 lane 同樣本不被併；單獨一個 `S1_R2.fastq.gz` 仍是 `r1` 為 None（由 `generate_samplesheet.py` 警告跳過）；`tests/generate_samplesheet_test.sh` 全綠且 `tests/fixtures/samplesheet_golden/rnaseq.csv` 比對不變。
- 兩分支比對（專案 CLAUDE.md「Calibration failures」：動閘門要在兩個分支跑同一份測試檔比對）：在 `origin/v3` 與本分支各跑 `bash tests/generate_samplesheet_test.sh` 與新檔，貼輸出；再用一批本來就能配的命名（`_R1_001`、含 lane、含 `S1_S1_L001_R1_001`）逐一 `extract_sample_info` 與 `match_read_pairs`，兩分支輸出必須逐位元相同。

## 完成標準（done when）
- T1–T3（及實測確認的 T4）改前紅、改後綠；對照組全程綠；`generate_samplesheet_test.sh` 與 golden 不變。
- 整個測試套件全綠（已知環境紅見 dev-plans README「通例：已知環境紅」，只剩那一條視同綠）。
- ledger 記：`git diff --stat` 只含「範圍」列的兩個檔；`extract_sample_info` 以外的函式未動或僅最小必要；沒有既有測試被改弱；兩分支輸出比對貼上。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」：
  - 單檔：`bash tests/sample_inference_test.sh`。`tests/run_all.sh` 以 `tests/*.sh` 自動收進新檔（`run_all.sh` 第 340 行迴圈），不需註冊。
  - 全套：`tests/run_all.sh` 不接受原生 Git Bash，要在 WSL 跑；從 Git Bash 且工作目錄為純 ASCII（例如 `$HOME`）：`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree 路徑> && bash tests/run_all.sh'`。同一個 checkout 不可同時跑兩次。
- **全套測試會超過單次指令 10 分鐘上限**：跑全套（`tests/run_all.sh --timeout 900`）一律用 Bash 的 `run_in_background`，再用 `until grep -qE "passed|FAILED|failed" <輸出檔>; do sleep 30; done` 迴圈（每次 ≤ 9 分鐘）等它結束，讀完結果才結束回合；測試還在背景跑時不准交報告。
- 這台 Windows 的 `python3` 在 Git Bash 可能不是真的 Python；測試在 WSL 跑即可，本機單檔驗證可改用實際的 Python 3.12 路徑。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 讀碼一律 `git -C <repo> show origin/v3:<path>`；實作在 worktree 的 `test/sample-inference-mate-token-pairing` 分支，base 為 `origin/v3`。

## 不做
- 不動 `generate_samplesheet.py` 的 `unpaired`／`two_for_one` 停止行為，不改任何警告或錯誤文字，不從檔名猜單端。
- 不動 `match_read_pairs` 對「同鍵多個 R1」的覆蓋行為（雖然靜默覆蓋本身也不好，見裁決 1）。
- 不改樣式的分數與清單；不新增新的命名樣式（例如 `.R1.`）——那是新功能，不是修回規則（見裁決 2）。
- 不碰 golden、不碰其他既有測試。不需要 migration。

## 裁決
1. **同鍵出現第二個 R1 時，要不要由靜默覆蓋改成警告？** 這會改使用者看得到的輸出，不屬 A 級。**建議：本件不做；修好樣本名截斷後這個情況只剩真的重複檔名，另開一件由使用者決定措辭。**
2. **`x.R1.fastq.gz`（記號前是點）目前也取成 `x.R1`，要不要一併處理？** 現有樣式 `\.R1[_.]` 需要記號後還有字元，同屬證據一那一類。**建議：作法 1 把樣式放到帶副檔名的字串上比對後，這個也會自然命中；executor 若實測不命中，不另加樣式，只在 ledger 記一筆交 developer-agent 決定。**

### developer-agent 確認（2026-10-29）
證據已在 origin/v3 核對：`_1[_.]` 套在去副檔名後的 stem 上，`Patient_1_Tumor_R1` 會被切成 `Patient`，屬實。A 級 bug：修回「一個樣本一組 R1/R2」的原意；既有可配對的命名輸出須逐位元不變。車道名改 L23（L22 已被佔用）。裁決全部照「建議」。

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

## 裁決（developer-agent，2026-10-29，回 verifier 合約審查）
1. **選 (a)：數字式記號且樣本名含數字，本件一併修。** 規則改寫成「只認最後一個記號」，取代「依分數排序、第一個命中就砍」：
   - 先去副檔名（`.fastq.gz`／`.fq.gz`／`.fastq`／`.fq`）與 lane 段（`_L\d{3}`）。
   - 配對記號＝剩下字串**結尾處**的 `[_.]R?[12]`，後面只允許再接一個 `_\d{3}`（例 `_001`），之後就是字串結尾。不在結尾的 `_1_`、`_2_` 一律視為樣本名的一部分。
   - 樣本名＝記號之前的全部字串。因為只看結尾那一個，所以不存在同分、R1／R2 誰先試的問題（回 verifier 第 2 點）。
2. **必須成立的預期結果（請轉成 TC，都要在 origin/v3 先紅）**：
   - `Patient_1_Tumor_1.fastq.gz`＋`Patient_1_Tumor_2.fastq.gz` → 一個樣本 `Patient_1_Tumor`，R1、R2 都在。
   - 再加 `Patient_2_Tumor_1/_2.fastq.gz` → 兩個樣本 `Patient_1_Tumor`、`Patient_2_Tumor`。
   - `A_2_x_1.fastq.gz`＋`A_2_x_2.fastq.gz` → 一個樣本 `A_2_x`。
   - `x.R1.fastq.gz`＋`x.R2.fastq.gz` → 一個樣本 `x`（回 verifier 第 3 點：給出預期結果；若 origin/v3 已經是綠的就當對照組）。
   - 原有可配對的 `_R1_001`、帶 lane 的命名輸出逐位元不變，`generate_samplesheet_test.sh` 與 golden 不改。
3. 車道統一為 L23-sample-inference（回第 4 點）。
4. 沒有 spec.md 照計畫為準，backend 守則不適用的條目不轉 TC（回第 5 點，同意 verifier 判斷）。
