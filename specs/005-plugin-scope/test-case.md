# 測試案例：沒在用 agentic-bioflow 時，plugin 完全安靜

**規格**：`specs/005-plugin-scope/spec.md`　**總覽**：`test-case-overview.md`

類型只有三種：
- **功能**：規格要求的事，在正常情況下做到了。
- **例外**：出錯、缺東西時的反應。
- **不在範圍**：規格明講這次不做的事，確認它真的沒做。

名詞：
- **在用**：三個條件任一成立。
  - ①這個 session 有 abf 使用記號。
  - ②目前資料夾在部署根目錄或 `storage_root` 裡。
  - ③指令本身呼叫 plugin 腳本、`tw` 或 Seqera MCP。
- **不在用**：三個都不成立。
- **病例指令**：`wsl.exe -e ssh -o ControlPath=… -o BatchMode=yes u@login 'scontrol show partition; sacctmgr show qos'`。

測試一律把 JSON 直接餵給各 hook 腳本，用假的 HOME、狀態資料夾和設定檔，照各 hook 現有測試的做法。hook 回「要確認」或「拒絕」都算「攔」。

## User Story 1 — 沒在用 abf 的 session 不被打擾（P1）

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-001 | US1-1；SC-001 | 功能 | 不在用；在 Git Bash（MSYS）環境下 | 病例指令餵給 `confirm_launch.sh` | 不攔、無輸出、exit 0 | 自動 |
| TC-002 | US1-2 | 功能 | 不在用；MSYS | `ssh u@host 'ls'`、`scp a u@host:b`、`rsync -a a u@host:b` | 都不攔 | 自動 |
| TC-003 | US1-3 | 功能 | 不在用 | `rm -rf results/`、`rm -rf work/` 餵給 `confirm_cleanup.sh`；`sbatch x.sh`、`nextflow run nf-core/rnaseq` 餵給 `confirm_launch.sh` | 都不攔、無輸出 | 自動 |
| TC-004 | US1-4 | 功能 | 不在用 | 寫入／編輯一般檔案，餵給 `confirm_walkthrough.sh` 和 `guard_plugin_files.sh` | 都不攔 | 自動 |
| TC-005 | US1-5 | 功能 | 不在用 | 跑 `session_start.sh`、`next_step.sh` | 沒有任何 abf 文字輸出 | 自動 |
| TC-006 | US1；FR-002 | 功能 | 不在用；subagent 的工具呼叫（輸入帶主 session 的 ID，加上 agent 欄位） | 病例指令 | 不攔（同 TC-001） | 自動 |

## User Story 2 — 在用 abf 時，安全網照舊（P1）

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-007 | US2-1；FR-002 | 功能 | 先讓 `plugin_intro.sh` 處理一次 `/agentic-bioflow:launch`（留下記號） | 同一個 session ID，送 `tw launch …` 給 `confirm_launch.sh` | 照舊要確認，並顯示完整指令 | 自動 |
| TC-008 | US2-1；FR-002 | 功能 | 記號由「載入 abf skill」（PostToolUse Skill）留下 | 同 session 的 `rm -rf results/` | 照舊拒絕 | 自動 |
| TC-009 | US2-2；FR-003 | 功能 | 沒有記號；cwd 在設定的 `storage_root` 底下 | `rm -rf results/` | 照舊拒絕 | 自動 |
| TC-010 | US2-2；FR-003 | 功能 | 沒有記號；cwd 在部署設定根目錄底下 | `rm -rf work/` | 照舊要確認 | 自動 |
| TC-011 | US2-3；FR-004 | 功能 | 沒有記號；cwd 在部署外 | `bash /…/<plugin>/scripts/on_site.sh -- rm -rf results` | 照舊拒絕 | 自動 |
| TC-012 | US2-3；FR-004 | 功能 | 同上 | `tw launch …`、`tw runs relaunch …` | 照舊要確認 | 自動 |
| TC-013 | US2-4；FR-004 | 功能 | 同上 | Seqera MCP 送分析的工具呼叫 | 照舊要確認 | 自動 |
| TC-014 | US2-5；FR-006 | 功能 | 在用；MSYS | 病例指令；`wsl ssh u@host ls`；`ssh -o BatchMode=yes u@host ls` | 不跳「會耗驗證碼」提醒 | 自動 |
| TC-015 | US2-6；FR-006 | 例外 | 在用；MSYS | `ssh u@host ls`；`ssh -o BatchMode=no u@host ls`；`echo wsl; ssh u@host ls` | 照舊提醒 | 自動 |
| TC-016 | SC-002 | 功能 | 在用（測試環境預設留下記號） | 既有的全部 hook 測試 | 全部照舊通過 | 自動（全套） |

## User Story 3 — 判斷失誤時往安全那邊倒（P1）

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-017 | US3-1；FR-005 | 例外 | 輸入沒有 session ID；有部署設定；cwd 在部署外 | `rm -rf results/` | 照舊拒絕（當成在用） | 自動 |
| TC-018 | US3-1；FR-005 | 例外 | 有部署設定；狀態資料夾無法讀取 | `tw launch …` 以外的 `rm -rf results/` | 照舊拒絕 | 自動 |
| TC-019 | US3-2 | 功能 | 沒有任何設定檔（沒部署過）；沒有記號；指令沒呼叫 plugin | `rm -rf results/` | 不攔（判斷得出來：不在用） | 自動 |
| TC-020 | US3；FR-002 | 例外 | 記號是另一個 session ID 留下的 | 這個 session 的 `rm -rf results/`，cwd 在部署外 | 不攔（別的 session 用 abf，不代表這個在用） | 自動 |

## 憲法、文件與效能

| 編號 | 對應 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證 |
|---|---|---|---|---|---|---|
| TC-021 | FR-008 | 功能 | — | 讀 `.specify/memory/constitution.md` | 版本 2.0.0；安全網開頭寫明適用範圍與「在用」的定義；修訂紀錄寫明理由 | 自動（文件檢查） |
| TC-022 | FR-008 | 功能 | — | 搜尋 `docs/PRINCIPLES.md`、根 `CLAUDE.md`、`docs/` 裡引用安全網的地方 | 沒有任何一處仍寫「所有 session 一律」之類跟新憲法矛盾的說法 | 自動（文件檢查） |
| TC-023 | FR-007；SC-003 | 功能 | 不在用；MSYS 或 Linux | 同一個指令跑 20 次 `confirm_launch.sh`，分別用 main 版和新版 | 新版平均時間 ≤ main 版 | 自動（量測，容許誤差） |
| TC-024 | 不在範圍 1 | 不在範圍 | 在用 | 既有的 launch／cleanup／walkthrough 判斷測試 | 結果跟 main 完全一樣（同 TC-016） | 自動 |
