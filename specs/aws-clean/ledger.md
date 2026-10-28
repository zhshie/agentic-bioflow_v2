# AWS：跑完清理 S3 work 前綴（clean_work） progress ledger

## 官方文件（先讀來源，2026-10-28 實際抓取）
- `aws s3 ls`：https://docs.aws.amazon.com/cli/latest/reference/s3/ls.html。用到旗標：`--recursive`、`--region`（全域）。輸出每行 `YYYY-MM-DD HH:MM:SS <size> <key>`，key 是 bucket 相對路徑；會自動分頁（`--page-size` 預設 1000）；前綴下沒有物件時什麼都不印（實務上結束碼 1、輸出空）。
- `aws s3 rm`：https://docs.aws.amazon.com/cli/latest/reference/s3/rm.html。用到旗標：`--recursive`、`--region`（全域）。可用旗標還有 `--dryrun --quiet --include --exclude --only-show-errors --page-size`，本任務一個都不用。輸出 `delete: s3://...` 每個物件一行。
- `aws s3api list-objects-v2`：https://docs.aws.amazon.com/cli/latest/reference/s3api/list-objects-v2.html。旗標有 `--prefix`、`--max-items`、`--page-size`、`--starting-token`、`--no-paginate`。本任務不用它（改用 `s3 ls --recursive`，同樣自動分頁，不帶 `--max-items`，符合 E6）。
- 計畫的指令形狀（E6、E8）與上面三頁一致，沒有不符之處。
- 假 bucket 的列舉輸出照 `s3 ls` 官方頁的行格式寫（`test_station_clean_aws.py` 檔頭附網址）。

## 紀錄
- RED：兩個新測試檔與 E2 指定的既有斷言先寫，跑過確認因為功能還沒做而紅（AWS 放行表沒有 clean_work、代理仍回「尚未支援」、畫面與文件還沒改）。
- E12 真實輸出格式（真的 `aws s3 ls`／`rm` 印出什麼）：UNVERIFIED(needs human)，只照官方文件寫了假輸出，沒有碰真的 AWS。
- GREEN：compute_envs（AWS 放行 clean_work）、jobs（AWS 其餘類型的通用「尚未支援」句）、build（clean_work_path、prepare_clean、clean_screen 的 AWS 分支，結尾斜線與 S3 一句）、clean.py（`_clean_aws`：列舉一次、`rm` 一次、不重試）、PLATFORM／SEQERA_PARITY／TESTING 三份文件。
- 我自己新測試的兩處期望值更正（不是既有測試）：子資料夾 workDir 時 `work/runs/r1/work/q` 也在該前綴下所以會被刪；head 還在跑時 ps 那一次呼叫是允許的（zero=False）。
- 手動差異檢查：既有測試只動 E2 清單內的斷言（test_aws_upload／launch／ce）；`rm` 字樣只在 clean.py；沒碰 test_station_clean_gcb、test_cleanup_confirm、test_byte_channel_b、web 系列、DESIGN.md、handlers.py。
- 卡住：既有 `test_station_clean.py::test_tc073_the_source_reaches_the_site_only_through_ctx_site_call` 釘死「run_fixed 只能出現在 `_clean_gcb` 與 `_head_gone`」；`_clean_aws` 照計畫要呼叫 `host.run_fixed`，所以它變紅。這個測試不在 E2 清單，依規則不改，需要裁決（把集合加上 `_clean_aws`，一行）。
