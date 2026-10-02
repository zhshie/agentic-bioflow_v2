# 測試案例：「這台電腦」用自己的隨機 ID 認

**規格**：`specs/006-machine-identity/spec.md`　**總覽**：`test-case-overview.md`

名詞：
- **ID 檔**：`<家目錄設定區>/agentic-bioflow/machine-id`。
- **機器檔**：`<設定根目錄>/config/machines/<名字>.yaml`。
- **舊名字**：舊版的「主機名稱－uname -s」。

測試用假的 HOME 和 XDG_CONFIG_HOME。主機名稱和 `uname -s` 用假的 `uname` 放在 PATH 最前面來模擬。

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-001 | US1-2；FR-001、FR-002 | 功能 | 沒有 ID 檔、沒有舊檔 | `settings.sh --set tw_bin /x/tw` | 產生 ID 檔，內容符合「主機名－8 碼十六進位」；機器檔是 `machines/<ID>.yaml`，裡面有 tw_bin | 自動 |
| TC-002 | US1-1；SC-001 | 功能 | 已有 ID 和機器檔 | 把假 `uname -s` 改成另一個組建號、主機名改掉，再讀 `tw_bin` | 讀到同一個值 | 自動 |
| TC-003 | US1-3；FR-002 | 功能 | 沒有 ID 檔 | 只 source `settings.sh` 並讀設定 | 沒產生 ID 檔，也沒產生任何機器檔 | 自動 |
| TC-004 | US2-1；FR-003 | 功能 | 有舊名字的機器檔（名字跟現在算的完全一樣），沒有 ID 檔 | 讀 `tw_bin` | 讀到舊檔的值 | 自動 |
| TC-005 | US2-2；FR-004 | 功能 | 同 TC-004 | `--set site_bridge wsl` | 舊檔被改名成 `<ID>.yaml`，舊值仍在、新值也在；舊檔名不存在了 | 自動 |
| TC-006 | US2-3；FR-003 | 功能 | 假 `uname -s`＝`MINGW64_NT-10.0-26200`；有舊檔 `…-MINGW64_NT-10.0-26100.yaml` | 讀 `tw_bin` | 接上舊檔 | 自動 |
| TC-007 | US2-3；FR-003 | 功能 | 同上，但有兩個不同組建號的舊檔 | 讀 `tw_bin` | 取最後修改的那個 | 自動 |
| TC-008 | US2-4；FR-003 | 例外 | 舊檔屬於另一個主機名稱 | 讀 `tw_bin` | 讀不到（不接上） | 自動 |
| TC-009 | FR-003 | 例外 | Linux 環境，有同主機名稱但 `uname -s` 不同的舊檔（例如 `-Darwin`） | 讀 `tw_bin` | 不接上（只有 MINGW／MSYS／CYGWIN 容許組建號不同） | 自動 |
| TC-010 | US3-1；SC-002 | 功能 | 兩個不同的 HOME，同一個設定根目錄，同樣的假主機名稱和 `uname -s` | 兩邊各自 `setup_proof.sh --record`（假 tw） | 寫進兩個不同的機器檔；各自 `--check` 只看到自己的 | 自動 |
| TC-011 | US3-2；FR-005 | 例外 | ID 檔內容是空白、`../../etc/x`、超過 64 字元 | 寫入 `tw_bin` | 不用壞的 ID；產生新的合法 ID 並在 stderr 說明；機器檔都在 `machines/` 裡 | 自動 |
| TC-012 | US3-3 | 例外 | ID 檔所在資料夾唯讀，沒有 ID 檔 | `--set tw_bin …` | 非零結束並說明；沒有寫出舊名字的機器檔 | 自動 |
| TC-013 | FR-006 | 功能 | — | 檢查 `docs/SETTINGS.md`；跑 `where.sh`、`settings.sh --summary` | 文件寫明新規則；印出的機器檔路徑是 `<ID>.yaml` | 自動 |
| TC-014 | — | 功能 | — | 全套測試（含 004 的 setup_proof、setup_verify 測試） | 全部通過 | 自動（全套） |
