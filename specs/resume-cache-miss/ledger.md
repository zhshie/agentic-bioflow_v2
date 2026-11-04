# 續跑不該讓不相關 task 重算：離線測試＋診斷程序 progress ledger

## 狀態（executor，2026-11-04）

- [x] `scripts/nf_hash_diff.py`（純標準函式庫；欄位名稱是依型別／值猜的，Nextflow 本身不命名；輸入形狀依 TaskProcessor 的 `cache hash ... entries:` 區塊，尚未用真實 nano4 日誌核對，操作員第一次跑時若回「格式不認得」就是這裡要修）
- [x] `platform/tests/test_resume_cache_stability.py`（12 個測試）
- [x] `docs/TESTING.md` 新節「續跑快取診斷（nano4）」，插在 Resume and relaunch (009e) 節之後
- 沒有改 `launch.py`、`resume_harness.py`、任何既有測試；沒有 xfail（五條假設都被排除）。TC-016 不適用。

## H1–H5 結論

| H | 結論 | 測試（`test_resume_cache_stability.py`） | 狀態 |
|---|---|---|---|
| H1 未改的鍵逐字相同（含 `1e-05`、引號、非 ASCII、布林、排序） | 已排除 | `test_resume_with_param_edit_keeps_unchanged_params_byte_identical`、`test_resume_params_yaml_matches_origin_render` | 綠 |
| H2 `input`／`outdir` 字串相同 | 已排除 | `test_resume_with_param_edit_keeps_unchanged_params_byte_identical` | 綠 |
| H3 head 行只差 `-name`／`-resume`／`-params-file`／`-c extra-N.config` | 已排除 | `test_resume_head_differs_only_in_allowed_flags`、`test_resume_without_edit_reuses_origin_files` | 綠 |
| H4 `module load`／`export` 行與原送出相同 | 已排除 | `test_resume_env_and_modules_match_origin`（4 種 overrides） | 綠 |
| H5 `extra-N.config` 平台只加註解行 | 已排除 | `test_resume_extra_config_has_no_hash_affecting_keys` | 綠 |

其他：`test_resume_unconfirmed_changes_nothing`（綠）、`test_nf_hash_diff_reports_first_difference`、`test_nf_hash_diff_missing_field_and_unknown_format_say_what_and_what_next`（綠）。

## 工作紀錄的誠實說明

測試是在工具與測試一起寫完後才第一次跑，因此沒有獨立的 RED commit；所有 H 測試第一次跑就綠，所以沒有紅的差異輸出可貼。結論：平台端沒有造成 71/72 重算的證據，下一步是操作員照 TESTING.md 新節在 nano4 診斷。
