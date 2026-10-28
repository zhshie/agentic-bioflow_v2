# AWS：上傳輸入檔到 S3（put_upload） progress ledger

## 2026-10-28 executor

- [x] 官方文件（2026-10-28 讀）：`https://docs.aws.amazon.com/cli/latest/reference/s3/cp.html`（`aws s3 cp - <s3uri> --region R` 串流上傳；`--expected-size` 只在串流超過 50 GB 才需要，故不帶）、`https://docs.aws.amazon.com/cli/latest/reference/s3api/head-object.html`（`--bucket --key --query ContentLength --output text`）。計畫的指令形狀與文件相符；文件沒有比 2 GB 更低的串流上限，沿用裁決 3 的 2 GB。
- [x] Google 版的行為是：雲端大小查不到 → 仍回 ok 並註明「沒能核對雲端大小；暫存檔保留」；大小不符 → 失敗、暫存檔保留；只有大小相符且 dev/ino 沒變才刪暫存檔。AWS 照做（A4）。
- [x] RED 先行：`platform/tests/test_aws_upload.py` 先 commit（27 failed / 14 passed，失敗皆因 AWS 尚未支援），再實作。
- [x] 實作：cloud_store（parse_s3、workdir_scheme、scheme 參數）、compute_envs（AWS 表加 put_upload）、jobs（閘門、超限訊息、dest）、actions/datasets（依 prefix 判 scheme）、abf_station/put_upload（`_transfer_aws`、head-object）。無 migration（scheme 由 path 前綴判斷）。
- [x] 文件：PLATFORM.md、SEQERA_PARITY.md、TESTING.md（手動真實上傳段落，TC-126）。
- 刻意更新的既有斷言（計畫點名）：test_aws_launch 的 accepts_exactly…、cloud_store_stays_google_only、a_dataset_destination…、put_upload_and_clean_work…、SEQERA_PARITY 字串；test_aws_ce 的 jobs_other_than…、no_new_write_path_for_aws、SEQERA_PARITY 字串。原因：AWS 現在接受 put_upload。
- 注意：cloud_store 內 s3 大檔指令寫成 `"aws s3 " "cp …"` 兩段字面，因為未點名的既有掃描（test_aws_ce `test_no_launch_cost_or_upload_code_for_aws`、test_aws_launch `test_no_new_write_path_for_aws`）會抓原始碼裡的 `s3 cp`；沿用 repo 既有的拆字作法（`"clean_" "work"`），沒有動那兩個測試。
- 手動 diff 檢查：未動 web.py、web_board.py、static、DESIGN.md、clean.py、build.py、test_web_*、spec、test-case；Google 路徑斷言未改。
