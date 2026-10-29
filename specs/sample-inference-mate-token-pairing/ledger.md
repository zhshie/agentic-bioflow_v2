# 樣本表推斷：標準 R1/R2 檔名要配成一組、不同樣本不准合併 progress ledger

- [x] RED 提交：tests/sample_inference_test.sh 在原程式上 13 項紅（TC-001..009、016、018），對照組 TC-010..013、019、020 綠。
- [x] GREEN：extract_sample_info 只認結尾的 `[_.]R?[12](_\d{3})?`，找不到結尾記號時沿用舊逐樣式作法；match_read_pairs 分類加 `_mate_number`（必要最小改動：否則 `Patient_1_Tumor_2` 會因 `_1_` 被分成 R1）。範圍：sample_inference.py + 新測試檔 + 本 ledger。
