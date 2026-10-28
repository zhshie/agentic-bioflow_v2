# fetch.sh／push.sh 把 C:/… 本機路徑轉成 rsync 看得懂的 /c/… progress ledger

- [x] `scripts/fetch.sh`、`scripts/push.sh` 各加 `rsync_local_path()`，rsync 的本機端引數經它轉換（fetch：先轉整條 `$DEST` 再 dirname；push：轉 `$from`）。tar 後備、`--dry-run`、錯誤訊息、exit code 不動。
- [x] `tests/fetch_test.sh`、`tests/push_test.sh` 新增斷言（TC-001..030，只新增不改既有）；MSYS／Cygwin 上整段略過並印 note。
- [ ] 全套測試（WSL）在 HEAD 綠。

## 已知限制
- 根因是從 rsync 的 `host:path` 規則推論出來的，**未在 Windows 重現**（issue #23 只有簽名）。
- WSL 的 `/mnt/c/…` 寫法**未量測、未處理**；只轉成 MSYS 的 `/c/…`。
- UNC（`\server\share`）不處理，原樣輸出。
- 有 `cygpath` 的分支在 CI（Linux）不測。
