# 費用規格改寫（純文件）：以運算環境為單位、每月費用提醒額度由使用者自設 progress ledger

- [x] RED：新增 `platform/tests/test_cost_docs_spec.py`（6 條，改文件前為紅）。
- [x] GREEN：DESIGN.md 第 11、12 項；docs/CLOUD.md 全面改寫（標題、額度節、雲端預算節、四種寫法、過渡段放最後）；docs/PLATFORM.md 第 776、889 行、費用頁節首註記、AWS／Azure 標籤列與註記。
- [x] 相關測試綠：test_cost_docs_spec、test_cloud_cost、test_cloud_wire、test_aws_launch、test_azure_launch、test_scope、test_gcb_launch。

## 釘字掃描（git grep，HEAD）
`Reconciled|cloud cap|cloud-cap|Personal|管理者` 在 platform/tests 與 tests 的命中：golden 檔（user add／cloud-cap 指令名，程式沒改所以不變）、test_cli_contract／test_cli_flags／test_cloud_cost 548 之後（指令與程式行為）、test_cloud_cost 407／422（程式拒絕訊息，程式未改）、test_aws_upload／test_azure_upload／test_byte_channel_b（「請管理者安裝／清理」程式訊息）。這些都釘程式輸出或指令名，不釘本任務改的文件字串；沒有「須同批處理」的測試。`請找管理者調整上限` 只在 test_cloud_wire（程式訊息，不動）與新增的釘字測試（斷言不含）。

## 已知殘留（不算失敗，留給費用頁實作片）
- DESIGN.md 第 34 行（Masthead）仍有 "cloud NT$ used / cap"：裁決 2 選 (b)，規格未定義頂欄費用行。費用頁實作片須一併改它。
- PLATFORM.md 第 778、782 行（現行費用頁描述，含 NT$、Reconciled）不動（裁決 3）。
- 程式拒絕訊息仍寫「請找管理者調整上限」，由 cost-reminder-quota 計畫改。
- artifact Version 6 不在 worktree，TC-007 由 verifier 開連結比對。

## diff 範圍
只含 DESIGN.md（第 11、12 項）、docs/CLOUD.md、docs/PLATFORM.md、新測試檔，加 specs/cost-docs-rewrite 的 ledger 與 decisions.tsv。
