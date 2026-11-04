# 預檢被拒要讓 AI 與網頁看得到原因與連線指令 progress ledger

- [x] 站台：`rules.Refusal.open_command`、`rules.open_command_in`、`launch._prechecks`、`handlers._refused` 帶出 `open_command`（只在 no-master 時）
- [x] 平台：`jobs.valid_open_command`／`host_of`／`clean_result(host=)`／`take_result` 查 CE hostName；`refusal_of`、`latest_refusal`
- [x] 網頁：`web_board.refusal_block`（確認頁與看板共用）、`web.state_page`、`web.board_page`；STRINGS 新增 `refusal_*` 四個 zh／en 鍵，沒有 `refusal_queued_note`
- [x] 文件：PLATFORM.md、TESTING.md（手動步驟）、CHANGELOG.md
- [ ] 截圖四張（1440／390、zh／en）到 `screens/`：本機無瀏覽器，留給 reviewer，步驟在 TESTING.md

## 做法備註
- 指令取自 connect 檢查 detail 結尾（即 `connect_failure` 逐字放進去的 `_open_command` 結果），沒有改 verdict 形狀。
- `clean_result` 沒有 CE，所以加 `host=` 參數，由 `take_result` 查 `compute_envs.config_json`。
- 憲法與 no-touch 清單內的檔案都沒動；沒有加 `nchc_t3c4`／`u9613010`／`ControlPersist=12h`／`site_login_command`。
- 修了一個自己寫出的退格字元（`\b` 變成 0x08），已改回並查過其他檔案沒有。
