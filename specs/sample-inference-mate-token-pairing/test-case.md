# 測試案例：樣本表推斷——標準 R1/R2 檔名要配成一組、不同樣本不准合併

<!--
Written by the verifier (CONTRACT mode). 沒有 spec.md；依 `specs/sample-inference-mate-token-pairing/plan.md` 的「目標」「失敗先行測試」「裁決（developer-agent，2026-10-29，回 verifier 合約審查）」寫成。
「維護者原話」：A 級＝不改使用者看得到的行為；絕不放寬安全網；合法的 `_R1_001` 命名行為逐位元不變。
-->

**規格**：`specs/sample-inference-mate-token-pairing/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

白話名詞：「配成一組」＝同一個樣本的 R1（正向讀序檔）與 R2（反向讀序檔）被放進同一筆紀錄。「樣本名」＝程式從檔名推出的樣本稱呼。「鍵」＝`match_read_pairs` 回傳字典的索引，一個鍵代表一個樣本（多 lane 時會加 lane 後綴）。

類型只有三種：**功能**（該做到的事做到了）、**例外**（出錯或缺東西時系統怎麼反應）、**不在範圍**（計畫明講不做，測試確認真的沒做）。

測試在 `tests/sample_inference_test.sh`（新檔），以 `match_read_pairs([...])` 與 `extract_sample_info(...)` 直接驗證，輸入只用檔名字串，不連網、不碰叢集。

## 一、標準雙端命名要配成一組（目標 1；優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標 1；T1_pairs_R1_dot_ext | 功能 | 兩個檔名 `/d/S1_R1.fastq.gz`、`/d/S1_R2.fastq.gz` | 呼叫 `match_read_pairs` | 恰好一個鍵；該筆的 r1 是 `S1_R1.fastq.gz`、r2 是 `S1_R2.fastq.gz`（兩者都不是 None）；樣本名 `S1`。改前紅（原本是兩個鍵 `S1_R1`／`S1_R2`，各缺一半） | 自動：`tests/sample_inference_test.sh` |
| TC-002 | 目標 1；T2_pairs_digit_mate | 功能 | 兩個檔名 `/d/S1_1.fastq.gz`、`/d/S1_2.fastq.gz` | 呼叫 `match_read_pairs` | 恰好一個鍵；r1 是 `S1_1.fastq.gz`、r2 是 `S1_2.fastq.gz`；樣本名 `S1`。改前紅（原本鍵為 `S1_1`／`S1_2`） | 自動：`tests/sample_inference_test.sh` |
| TC-003 | 裁決 2 第 2 條（`x.R1.fastq.gz`＋`x.R2.fastq.gz` → 樣本 `x`） | 功能 | 兩個檔名 `/d/x.R1.fastq.gz`、`/d/x.R2.fastq.gz` | 呼叫 `match_read_pairs` | 恰好一個鍵；樣本名 `x`；r1、r2 都在。改前紅（原本是兩個鍵 `x.R1`／`x.R2`） | 自動：`tests/sample_inference_test.sh` |

## 二、不同樣本不准合併、不准有檔案靜默消失（目標 2；優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-004 | 目標 2；T3_distinct_samples_kept | 功能 | 四個檔名 `Patient_1_Tumor_R1.fastq.gz`、`Patient_1_Tumor_R2.fastq.gz`、`Patient_2_Tumor_R1.fastq.gz`、`Patient_2_Tumor_R2.fastq.gz` | 呼叫 `match_read_pairs` | 兩個鍵；樣本名分別是 `Patient_1_Tumor`、`Patient_2_Tumor`；每一筆的 r1、r2 都在且屬於各自的樣本（Patient_1 的筆裡不會是 Patient_2 的檔）。改前紅（原本只有一個鍵 `Patient`，內容是 Patient_2 那一對） | 自動：`tests/sample_inference_test.sh` |
| TC-005 | 裁決 1：`Patient_1_Tumor_1`＋`_2` → 一個樣本 `Patient_1_Tumor` | 功能 | 兩個檔名 `Patient_1_Tumor_1.fastq.gz`、`Patient_1_Tumor_2.fastq.gz` | 呼叫 `match_read_pairs` | 恰好一個鍵、樣本名 `Patient_1_Tumor`；r1 是 `..._1.fastq.gz`、r2 是 `..._2.fastq.gz`（`_2` 那個檔必須被認成 R2，不是 R1）。改前紅 | 自動：`tests/sample_inference_test.sh` |
| TC-006 | 裁決 1：再加 `Patient_2_Tumor_1/_2` → 兩個樣本 | 功能 | 四個檔名 `Patient_1_Tumor_1/_2.fastq.gz`、`Patient_2_Tumor_1/_2.fastq.gz` | 呼叫 `match_read_pairs` | 兩個鍵；樣本名 `Patient_1_Tumor`、`Patient_2_Tumor`；每筆 r1、r2 皆在且屬於各自樣本。改前紅 | 自動：`tests/sample_inference_test.sh` |
| TC-007 | 裁決 1：`A_2_x_1`＋`A_2_x_2` → 一個樣本 `A_2_x` | 功能 | 兩個檔名 `A_2_x_1.fastq.gz`、`A_2_x_2.fastq.gz` | 呼叫 `match_read_pairs` | 恰好一個鍵、樣本名 `A_2_x`；r1、r2 都在。改前紅（原本樣本名被截成 `A`） | 自動：`tests/sample_inference_test.sh` |
| TC-008 | 目標 2；T4_illumina_style_names_not_collapsed | 功能 | 四個檔名 `Sample_1_S1_L001_R1_001.fastq.gz`、`Sample_1_S1_L001_R2_001.fastq.gz`、`Sample_2_S2_L001_R1_001.fastq.gz`、`Sample_2_S2_L001_R2_001.fastq.gz` | 呼叫 `match_read_pairs` | 兩個不同的鍵；兩個樣本名分別含 `Sample_1`、`Sample_2`（不是都叫 `Sample`）；每筆 r1、r2 都在。改前紅（原本兩者同為 `Sample`，只剩一對） | 自動：`tests/sample_inference_test.sh` |
| TC-009 | 目標 2（前一對靜默消失） | 功能 | 把 TC-004、TC-006、TC-008 的輸入檔名各自餵入 | 呼叫 `match_read_pairs`，收集回傳裡所有 r1、r2 路徑 | 輸入的每一個檔都剛好出現在輸出一次；輸出檔數＝輸入檔數（4、4、4），沒有檔被覆蓋掉 | 自動：`tests/sample_inference_test.sh` |

## 三、現行就能配的命名，行為逐位元不變（A 級前提；優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 對照組：`_R1_001` 標準 Illumina 命名 | 功能 | `S1_R1_001.fastq.gz`、`S1_R2_001.fastq.gz` | 呼叫 `match_read_pairs` | 恰好一個鍵 `S1`、樣本名 `S1`、r1、r2 都在。改前改後都綠 | 自動：`tests/sample_inference_test.sh` |
| TC-011 | 對照組：帶 lane 的鍵 | 功能 | `S1_L002_R1_001.fastq.gz`、`S1_L002_R2_001.fastq.gz` | 呼叫 `match_read_pairs` | 恰好一個鍵 `S1_L002`（lane 不是 L001 才加後綴）；樣本名 `S1`；r1、r2 都在。改前改後都綠 | 自動：`tests/sample_inference_test.sh` |
| TC-012 | 對照組：多 lane 同一樣本不被併 | 功能 | `S1_L001_R1_001/R2_001.fastq.gz` 與 `S1_L002_R1_001/R2_001.fastq.gz` 四個檔 | 呼叫 `match_read_pairs` | 兩個鍵（`S1` 與 `S1_L002`），各自 r1、r2 都在、屬於各自 lane 的檔。改前改後都綠 | 自動：`tests/sample_inference_test.sh` |
| TC-013 | 對照組：樣本名本身含 `S1_S1` 的 lane 命名 | 功能 | `S1_S1_L001_R1_001.fastq.gz`、`S1_S1_L001_R2_001.fastq.gz` | 呼叫 `match_read_pairs` 與 `extract_sample_info` | 恰好一個鍵 `S1_S1`、樣本名 `S1_S1`、r1、r2 都在（與 origin/v3 實測相同） | 自動：`tests/sample_inference_test.sh` |
| TC-014 | 對照組：既有樣本表測試全綠 | 功能 | 本分支 | 執行 `bash tests/generate_samplesheet_test.sh` | 全部通過，輸出 `all passed`，沒有被改弱或刪除的斷言 | 自動：`tests/generate_samplesheet_test.sh` |
| TC-015 | 對照組：golden 不動 | 功能 | 本分支與 origin/v3 | 比對 `tests/fixtures/samplesheet_golden/` 內容，且 `generate_samplesheet_test.sh` 中對 `rnaseq.csv` 的比對通過 | 目錄與 origin/v3 逐位元相同（沒有任何 golden 被修改）；`rnaseq.csv` 比對通過 | 自動：`tests/generate_samplesheet_test.sh` |

## 四、安全網：配不起來就停下來問，不從檔名猜（例外；優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | 對照組：單獨一個 R2 仍不補 R1 | 例外 | 只有一個檔 `S1_R2.fastq.gz` | 呼叫 `match_read_pairs` | 該筆 r1 是 None、r2 是這個檔；沒有把它當成單端 R1，也沒有憑空造出 r1 | 自動：`tests/sample_inference_test.sh` |
| TC-017 | 「不做」：不改 `unpaired` 停止行為與訊息 | 例外 | 一個資料夾含 `S1`、`S2`、`S3` 的 `_R1_001`／`_R2_001` 配對與一個孤立的 `S4_R2_001.fastq.gz` | 用 `generate_samplesheet.py` 產樣本表（`generate_samplesheet_test.sh` 約第 69 行起的既有情境） | 行為與停止訊息和 origin/v3 完全相同（既有斷言未改弱、全綠）：仍然停下並警告，不從檔名猜單端、不寫出缺一半的樣本 | 自動：`tests/generate_samplesheet_test.sh` |

## 五、不在範圍（計畫「不做」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-018 | 「不做」第 2 點／裁決 1：同鍵多個 R1 的覆蓋行為不動、不加警告 | 不在範圍 | 兩個會得到相同鍵的 R1 檔：`S1_R1.fastq.gz` 與 `S1_R1.fq.gz`（依序傳入） | 呼叫 `match_read_pairs` | 不丟例外、不印任何新的警告文字；只有一個鍵，r1 是後傳入的那個檔（維持原本的覆蓋行為） | 自動：`tests/sample_inference_test.sh` |
| TC-019 | 「不做」第 3 點：不新增新的命名樣式 | 不在範圍 | 兩個檔 `S1-R1.fastq.gz`、`S1-R2.fastq.gz`（記號前是連字號，不在 `[_.]R?[12]` 內） | 呼叫 `match_read_pairs` | 這兩個檔沒有被配成同一個樣本的一對（不會出現一筆同時有 r1 與 r2 的紀錄）；與 origin/v3 相同，程式沒有為此新增樣式 | 自動：`tests/sample_inference_test.sh` |

## 六、新測試檔本身的要求（計畫「範圍」「失敗先行測試」「完成標準」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 範圍：檔頭 `# Nothing existing: …` | 功能 | 新檔 `tests/sample_inference_test.sh` | 讀檔頭前 40 行 | 有一行以 `# Nothing existing:` 開頭，說明至少 15 個字 | 自動：`tests/dev_workflow_test.sh`（若已涵蓋）或驗收者讀檔 |
| TC-021 | 環境事實：`run_all.sh` 自動收進新檔 | 功能 | 本分支 | 執行 `bash tests/run_all.sh --list` | 清單包含 `sample_inference_test.sh`，不需另外登記 | 自動：`tests/run_all.sh --list` |
| TC-022 | 失敗先行：這些測試要能失敗 | 功能 | 在 origin/v3（未修改的程式）上放入新測試檔 | 執行 `bash tests/sample_inference_test.sh` | TC-001 至 TC-008 的斷言全部失敗（紅）；TC-010 至 TC-013、TC-016、TC-018、TC-019 通過（綠）。證明這些測試不是無論如何都綠 | 自動：驗收時在 origin/v3 與本分支各跑一次同一份測試檔 |
