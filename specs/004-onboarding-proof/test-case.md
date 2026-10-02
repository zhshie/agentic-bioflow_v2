# 測試案例：新電腦、第二位成員也要先用公開資料驗證

**規格**：`specs/004-onboarding-proof/spec.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，在正常情況下做到了。
- **例外**：出錯、缺東西，或使用者做了不該做的事時，系統的反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

名詞：
- **證明紀錄**：這台電腦自己的設定檔（`config/machines/<這台>.yaml`）裡記下的「哪個公開測試 run 在哪天成功」。
- **合格的 run**：在 Platform 上狀態 `SUCCEEDED`、管線是 `nf-core/demo`、送出者是這個人的 run。

測試一律用假的 `preflight.sh` 和假的 `tw`（照 `tests/setup_verify_only_test.sh`、`tests/runs_board_test.sh` 既有做法），不連真的叢集和 Platform。

## User Story 1 — 沒證明過的電腦拿不到指令清單（P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | US1 情境 1；FR-003 | 功能 | preflight 通過；這台有證明紀錄 | `setup_verify.sh` | exit 0，說「已經設定好」，並印出證明的 run ID 與日期 | 自動 |
| TC-002 | US1 情境 2；FR-003 | 例外 | preflight 通過；這台沒有證明紀錄 | `setup_verify.sh` | exit 3；**不**說「已經設定好」；說明這台還沒用公開測試資料證明過，指向第 8 步 | 自動 |
| TC-003 | US1 情境 3；FR-001 | 例外 | 同一個設定根目錄；另一台電腦（另一個 machines 檔）有證明紀錄，這台沒有 | `setup_verify.sh` | exit 3，別台的紀錄不算 | 自動 |
| TC-004 | US1 情境 4；FR-002、FR-001 | 功能 | 假 `tw` 回一筆 `SUCCEEDED`、`nf-core/demo`、送出者等於 `seqera_user` 的 run | `setup_proof.sh --record <id>` | exit 0；紀錄寫進這台的 machines 檔、**不**寫進 `env.yaml`；印出記下的 run ID 與日期；之後 `--check` exit 0 | 自動 |
| TC-005 | US1 情境 5；FR-002 | 例外 | 那筆 run 狀態是 `FAILED`（另測 `RUNNING`、`CANCELLED`） | `--record <id>` | 非零結束、不寫入，訊息說狀態不是成功 | 自動 |
| TC-006 | US1 情境 5；FR-002 | 例外 | 那筆 run 是 `nextflow-io/hello`（或其他管線） | `--record <id>` | 非零結束、不寫入，訊息說要的是 `nf-core/demo` | 自動 |
| TC-007 | US1 情境 5；FR-002 | 例外 | 那筆 run 的送出者是別人 | `--record <id>` | 非零結束、不寫入，訊息說不是這個人送的 | 自動 |
| TC-008 | US1 情境 5；FR-002 | 例外 | Platform 上沒有這個 run ID | `--record <id>` | 非零結束、不寫入，訊息說找不到 | 自動 |
| TC-009 | US1 情境 6；FR-004 | 例外 | 假 `tw` 失敗（非零結束），或回的不是看得懂的 JSON | `--record <id>` | 非零結束、不寫入，說明無法確認；**不**當成通過 | 自動 |
| TC-010 | US1 情境 7；FR-007 | 功能 | 沒有設定檔；或 preflight 失敗 | `setup_verify.sh` | 跟現在一樣：exit 1，訊息不變（現有測試照舊通過） | 自動 |
| TC-011 | FR-002 | 例外 | 不帶參數、帶未知參數、`--record` 沒給 ID | `setup_proof.sh` | exit 2，印出用法，不寫入 | 自動 |
| TC-017 | FR-002（驗收後加） | 例外 | 那筆 run 是 7 天以前送的 | `--record <id>` | 非零結束、不寫入，說明 run 太舊、請在這台重跑第 8 步 | 自動 |
| TC-018 | FR-002（驗收後加）；US1 情境 3 | 例外 | 那個 run ID 已經記在同一設定根目錄下另一台電腦的紀錄裡 | `--record <id>` | 非零結束、不寫入，點名是哪一台 | 自動 |

## User Story 2 — setup 的說明照新規則走（P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | US2 情境 1；FR-005 | 功能 | `commands/setup.md` | 讀 T27 那段 | 寫明 exit 3＝直接做第 8 步再第 9、10 步，不重做第 1–7 步 | 自動（文件檢查） |
| TC-013 | US2 情境 2；FR-005 | 功能 | `commands/setup.md` | 讀 Repair 那段 | 寫明 Repair 結束前跑 `setup_proof.sh --check`，沒有紀錄就做第 8 步 | 自動（文件檢查） |
| TC-014 | US2 情境 3；FR-005 | 功能 | `commands/setup.md` | 讀第 8、9 步 | 第 8 步以 `setup_proof.sh --record <run-id>` 作結；第 9 步寫明只在記錄成功後才介紹指令 | 自動（文件檢查） |

## 憲法與安全網

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | FR-006；憲法第 3 條 | 功能 | 新的設定值 | 檢查 `docs/SETTINGS.md` 與 `tests/no_hardcoded_paths.sh` | 文件記載新設定值屬於這台電腦；沒有寫死的路徑 | 自動 |
| TC-016 | 不在範圍 1 | 不在範圍 | 這台沒有證明紀錄 | 跑送出前的總覽（`prepare_launch.sh`）／launch 的關卡 | 行為跟現在一樣，不因為沒有證明而擋下（全套測試照舊通過） | 自動（全套測試） |
