# samplesheet 輸出資料夾不存在時自動建立 progress ledger

- [x] 失敗先行測試 TC-001..022 加進 tests/generate_samplesheet_test.sh（RED commit；base 上 15 條紅）
- [x] scripts/generate_samplesheet.py：寫檔前 makedirs，OSError -> 一行 ERROR: cannot write、exit 2；檔頭結束碼說明加一句
- [x] hooks/ 與其他範圍外檔案零改動（見下方 git diff --name-only）
- git diff --name-only 50f696b..HEAD:
  - scripts/generate_samplesheet.py
  - specs/samplesheet-output-dir/ledger.md
  - specs/samplesheet-output-dir/plan.md
  - specs/samplesheet-output-dir/test-case-overview.md
  - specs/samplesheet-output-dir/test-case.md
  - tests/generate_samplesheet_test.sh
  - hooks/: 0 檔
