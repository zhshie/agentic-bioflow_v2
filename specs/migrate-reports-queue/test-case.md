# 測試案例：搬舊設定時一併搬 reports/ 佇列（#23）

<!--
Written by the verifier (CONTRACT mode). 來源只有 plan.md（本任務沒有 spec.md，沒有維護者逐字裁示；plan 的「維護者原話」一節是 issue #23 的等價要求）。
所有預期結果都取自 plan 的 T1–T10 與「作法」「不做」「完成標準」，沒有另外發明行為。
-->

**規格**：`specs/migrate-reports-queue/plan.md`（本任務以 plan 代規格）　**總覽**：`test-case-overview.md`

名詞：「回報佇列」＝還沒送出的 off-design 回報，一份一個 `*.report` 檔，放在設定檔旁邊的 `reports/` 資料夾；「舊」＝T30 版面之前（設定檔在 `~/.config/agentic-bioflow/env.yaml` 或 `$LAB_RUNS_DIR/_personal/env.yaml`）；「新」＝`<root>/config/reports/`。

所有「自動」案例都放在新檔 `tests/settings_migrate_reports_test.sh`，每條各自用獨立的暫存 `HOME`、`XDG_CONFIG_HOME`；舊設定檔為 `$HOME/.config/agentic-bioflow/env.yaml`（模式 600，內容 `workspace_id: 1`），根為 `$TMP/root`，除非該列另有說明。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

## User Story 1 — 搬完設定，舊的回報佇列跟著搬走、並說清楚搬了幾份（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | plan 目標；T1 | 功能 | 舊設定檔旁的 `reports/` 有 2 份 `.report` | 跑 `scripts/settings.sh --migrate $TMP/root` | `$TMP/root/config/reports/` 裡有同名的 2 份，內容與舊檔逐位元相同 | 自動：`tests/settings_migrate_reports_test.sh` |
| TC-002 | T2 | 功能 | 同 TC-001，已搬完；`AGENTIC_BIOFLOW_REPORTS_DIR` 不設 | 跑 `bash scripts/report.sh --dir` | 印出 `$TMP/root/config/reports` | 自動 |
| TC-003 | T2 | 功能 | 同 TC-002 | 跑 `bash scripts/report.sh list` | 列出那 2 份回報（開場提醒因此數得到 2 份，不是 0 份） | 自動 |
| TC-004 | T3；plan「複製不移動」 | 功能 | 同 TC-001 | 搬完後看舊位置 | 舊的 `reports/` 資料夾仍在 | 自動 |
| TC-005 | T3；plan「複製不移動」 | 功能 | 同 TC-001 | 搬完後看舊位置 | 舊 `reports/` 裡原本那 2 份檔案都還在，內容沒變 | 自動 |
| TC-006 | T4；作法第 2 點 | 功能 | 同 TC-001 | 搬完後用 `stat -c %a` 看新檔 | 新目錄裡每一份 `.report` 的模式都是 `600` | 自動 |
| TC-007 | T4；作法第 2 點 | 功能 | 同 TC-001 | 搬完後用 `stat -c %a` 看新資料夾 | `$TMP/root/config/reports` 的模式是 `700` | 自動 |
| TC-008 | T5；作法第 3 點 | 功能 | 同 TC-001 | 看 `--migrate` 的輸出 | 含 `2 queued report(s) copied to`（後接新資料夾路徑）；這類訊息只有這一行 | 自動 |
| TC-009 | T5；作法第 4 點 | 功能 | 同 TC-001 | 看輸出裡「Done. 舊檔未動、可在驗證後刪除」那份清單 | 舊的 `reports/` 資料夾路徑列在清單裡 | 自動 |
| TC-010 | T9 | 功能 | 舊設定改放 `$LAB_RUNS_DIR/_personal/env.yaml`，佇列在 `$LAB_RUNS_DIR/_personal/reports/`（2 份 `.report`）；`~/.config` 下沒有舊設定 | 跑 `--migrate $TMP/root` | 與 TC-001 相同：新資料夾有同名 2 份、內容逐位元相同 | 自動 |
| TC-011 | T10 | 功能 | 舊設定檔有 `workspace_id: 1`（及其他鍵） | 跑 `--migrate`，與 base 上同一情境的輸出逐行比對 | 設定鍵搬進 `config/env.yaml` 與 `config/machines/...` 的訊息（`N setting(s) into ...`）和內容不變 | 自動 |
| TC-012 | T10 | 功能 | 舊設定檔旁有 `.seqera_token` | 跑 `--migrate` | token 被複製到 `<root>/config/.seqera_token`，輸出 `token copied to ...` 與 base 逐字相同 | 自動 |
| TC-013 | T10 | 功能 | 舊設定檔含 `local_root: <某路徑>` | 跑 `--migrate` | 輸出 `local_root (<某路徑>) is superseded by the root itself - not carried over` 與 base 逐字相同，該鍵不被搬 | 自動 |
| TC-014 | 專長守則（密鑰不得出現在回應）；T10 | 例外 | 舊設定檔旁有 `.seqera_token`（內容為可辨識的假 token），且舊 `reports/` 有 2 份回報 | 跑 `--migrate`，收集全部輸出 | 輸出裡完全找不到 token 內容；新增的佇列相關輸出也不含 token | 自動 |

## User Story 2 — 沒有舊佇列、或新位置已有同名檔時，不亂動（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | T6；作法第 2 點「不覆蓋」 | 例外 | 舊 `reports/` 有 2 份；新 `config/reports/` 已存在其中 1 份的同名檔，但內容不同 | 跑 `--migrate` | 那份已存在的新檔內容保持原樣、沒有被覆蓋；另一份照常複製過去 | 自動 |
| TC-016 | T6；作法第 3 點 | 例外 | 同 TC-015 | 看輸出 | 含 `1 already there - left alone` | 自動 |
| TC-017 | T7；作法第 3 點 | 例外 | 舊設定檔旁沒有 `reports/` 資料夾 | 跑 `--migrate $TMP/root` | `$TMP/root/config/reports` 沒有被建立 | 自動 |
| TC-018 | T7；作法第 3 點 | 例外 | 同 TC-017 | 看輸出 | 輸出不含 `queued report` 字樣 | 自動 |

## User Story 3 — 這次明講不做的事（優先度 P3）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | T8；作法第 6 點（只複製 `*.report`） | 不在範圍 | 舊 `reports/` 內有 2 份 `.report`，另有 `notes.txt` | 跑 `--migrate` | 新資料夾裡沒有 `notes.txt` | 自動 |
| TC-020 | T8；作法第 6 點 | 不在範圍 | 舊 `reports/` 內有 2 份 `.report`，另有一個子資料夾（內含檔案） | 跑 `--migrate` | 新資料夾裡沒有該子資料夾，也沒有其中的檔案 | 自動 |
| TC-021 | 作法第 5 點；「不做」不搬 XDG state 佇列 | 不在範圍 | 舊設定檔旁沒有 `reports/`，但 `$HOME/.local/state/agentic-bioflow/reports/` 有 `.report` | 跑 `--migrate $TMP/root` | 那些檔案沒有被複製到 `$TMP/root/config/reports/`（該資料夾不存在），XDG 那邊原樣不動 | 自動 |
| TC-022 | 範圍：檔案（只准改 4 個）；「不准動」清單 | 不在範圍 | 實作完成 | verifier 閱卷時跑 `git diff --name-only <base>...HEAD` | 只含 `scripts/settings.sh`、`tests/settings_migrate_reports_test.sh`、`docs/SETTINGS.md`、`specs/migrate-reports-queue/ledger.md`；`platform/**`、`hooks/`、`scripts/report.sh`、`scripts/where.sh`、`.claude-plugin/plugin.json`、`CHANGELOG.md`、憲法零改動 | 手動：verifier 閱卷步驟（見總覽「不確定」第 3 點） |
| TC-023 | 「不做」：不改 `reports_dir()`、不加新的 session 提醒、不刪舊檔、不處理 #23 的七個個別回報 | 不在範圍 | 實作完成 | verifier 閱卷時讀 diff | `settings.sh` 的改動只在 `migrate_legacy` 內、token 區塊之後、「Done.」之前，外加「可刪除清單」多一行；沒有任何 `rm`／刪除舊檔的程式；沒有新增開場提醒；版本號未動 | 手動：verifier 閱卷步驟 |

## 憲法與安全網

<!-- 本變更碰到：安全網「第一次搬移不得丟失唯一一份」的既有原則（settings.sh:898-901）與「測試不得碰真實 ~/.config」（CLAUDE.md Never run）。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 | 完成標準：既有測試不改而綠 | 功能 | 實作完成 | 逐一跑 `bash tests/settings_test.sh`、`tests/report_test.sh`、`tests/where_test.sh`、`tests/session_start_test.sh`、`tests/jev_test.sh`、`tests/machine_identity_test.sh` | 六個全綠，且這些檔案在 diff 中零改動 | 自動：在 WSL 逐檔跑 |
| TC-025 | 完成標準：整套全綠 | 功能 | 實作完成 | 在 WSL 跑 `bash tests/run_all.sh` | 全綠；執行完成後 `executor-status` 為 `GREEN <HEAD sha>` | 自動 |
| TC-026 | 憲法「驗收：不得弱化測試」；plan「會改斷言的既有測試：無」 | 例外 | 實作完成 | verifier 比對 base 與 HEAD 的 `tests/` 與 `docs/SETTINGS.md` | `tests/` 只新增 `tests/settings_migrate_reports_test.sh`，沒有任何既有測試被刪斷言、改預期值或跳過；`docs/SETTINGS.md` 只在 `## Migration` 一節**新增**一句，沒有刪字（`tests/jev_test.sh` TC-053、`tests/machine_identity_test.sh` 讀它找特定字詞） | 手動：verifier 閱卷步驟 |
| TC-027 | CLAUDE.md「Never run：用真實 ~/.config」；完成標準「沒有真的連網或碰真實 ~/.config」 | 例外 | 新測試檔寫好 | verifier 讀 `tests/settings_migrate_reports_test.sh` 的頭部與每個情境 | 每個情境都用 `mktemp -d` 的暫存 `HOME`／`XDG_CONFIG_HOME`；沒有任何指令指向真實 `$HOME`，也沒有網路呼叫 | 手動：verifier 閱卷步驟 |
