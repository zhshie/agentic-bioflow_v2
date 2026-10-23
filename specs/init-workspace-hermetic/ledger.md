# init-workspace-hermetic progress ledger

- [x] 新案例 `site side ignores the developer's own deployment when testing`：夾具 HOME 含指標、storage_root=/proc/no-such-run-area/work。舊寫法（只 `env -u LAB_RUNS_DIR`）rc 1（mkdir: cannot create directory '/work'）；新 helper `no_deployment`（清 LAB_RUNS_DIR、LAB_SETTINGS_FILE，HOME/XDG 指向空目錄）後 rc 2。原案例也改用該 helper；另加 control 案例固定舊寫法 rc 1。
- 根因補充：開發機 shell 匯出了 LAB_SETTINGS_FILE，光換 HOME 不夠。
