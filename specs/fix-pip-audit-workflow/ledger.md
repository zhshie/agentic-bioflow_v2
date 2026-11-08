# 修 security.yml 的 pip-audit 紅燈（專案目錄模式不接受 --no-deps） progress ledger

- 完成：security.yml 專案行改為 `pip-audit ./platform $IGNORES`（3c512fca），新增測試（71f14dc5）。CI run 連結待 push 後由 lander 補（TC-005 手動）。
