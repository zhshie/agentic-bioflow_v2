# 續跑可改參數與資源（a：站台與 bundle） progress ledger

- [x] `platform/abf_station/launch.py`：`_head_script` 加 `params_file`／`extra_file`；`render_resume`、`render_resume_bundle` 加 `overrides=None`；
  新增 `MAX_EXTRA_CONFIG`、`RESUME_OPTIONAL`、`_check_extra_config`（封閉行語法）、`_normalize_overrides`；`run_resume`、`_probe`、`_check_folder` 認得新檔。
- [x] `platform/tests/test_resume_edit_params_station.py`：新測試（RED 先、GREEN 後），TC 編號寫在註解。
- 無改動時 `head-N.sh` 與內容包 sha256 與先前逐位元組相同（測試裡寫死黃金文字與黃金雜湊）。
- 正規化後的 `resume.overrides` 省略空的項（空字串、空字典都不放鍵）；`extra_config` 結尾換行收成剛好一個。
- 不需要 migration：沒有碰資料庫；舊的續跑 bundle 沒有 `overrides` 鍵，行為不變。platform 端仍不會送出改動（b 片才接上）。
- 未在國網實測改參數後沿用快取（手動檢查在 d 片的 TESTING.md）。

## git diff --stat
(對 base `014bf9fb95628ccfa262a701625d747361a382f2` 的 git diff --stat，只有三個路徑)

```
  platform/abf_station/launch.py                    | 177 +++++-
 platform/tests/test_resume_edit_params_station.py | 669 ++++++++++++++++++++++
 specs/resume-edit-params-a/ledger.md              |  19 +
 3 files changed, 843 insertions(+), 22 deletions(-)
```

