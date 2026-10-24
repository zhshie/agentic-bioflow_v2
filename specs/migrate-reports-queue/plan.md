---
id: migrate-reports-queue
title: settings.sh --migrate 一併搬走「待送的 off-design 回報佇列」（現在搬完設定後，舊佇列被默默丟在原地、開場提醒永遠不會響）
tier: A
kinds: backend
lane: L-reports-queue
base: v3（`origin/v3` @ 50f696b；所有行號都是該版本）
source: developer-agent 讀碼查證（2026-10-25）；GitHub issue #23 的「Found while triaging」一段；未實機跑 migrate，但已用測試腳本（見下）預先確認讀碼推論
---

# migrate-reports-queue

> A 級 bug：把行為拉回 `report.sh` 檔頭自己寫的承諾（"queued forever, reminded never" 是它要避免的失敗）。純外掛側 bash，不碰 `platform/`、不碰 `hooks/`。

## 目標
`scripts/settings.sh --migrate <root>` 搬設定、搬 token 之外，也把舊設定檔旁邊的 `reports/*.report` **複製**到新根的 `config/reports/`，並說出搬了幾份。對使用者的意義：升級到 T30 版面的人不會悄悄丟掉已排隊、還沒送出的回報，session 開場的「N off-design report(s) not sent」提醒照常響。

### 查證結果（皆 `origin/v3`）
- 回報佇列放哪：`scripts/report.sh:165-175` `reports_dir()`——設了 `AGENTIC_BIOFLOW_REPORTS_DIR` 用它；找得到設定檔（`SETTINGS_FOUND=1`）時是 `$(dirname "$SETTINGS_FILE")/reports`；否則 `~/.local/state/agentic-bioflow/reports`。T30 之後設定檔在 `<root>/config/env.yaml`，所以佇列在 `<root>/config/reports/`。
- 舊佇列放哪：T30 前的設定檔位置由 `scripts/settings.sh:238-245` `legacy_settings_found` 給出（`$LAB_RUNS_DIR/_personal/env.yaml` 或 `~/.config/agentic-bioflow/env.yaml`），同一個公式 `$(dirname 舊設定檔)/reports` 就是舊佇列（issue #23 實際遇到的正是 `~/.config/agentic-bioflow/reports`）。
- **漏搬處**：`scripts/settings.sh:902-957` `migrate_legacy` 只做三件事：逐鍵 `set_setting`（:925-940）、複製 `.seqera_token`（:943-951）、印「舊檔原封不動」（:954-957）。沒有任何一行碰 `reports/`。
- 開場提醒讀哪：`hooks/session_start.sh:145-148` 呼叫 `report.sh --dir`，數該目錄的 `*.report`——搬完後指向新根，舊佇列不在那裡，數得 0。
- 檔名與格式：`scripts/report.sh:245-263` 檔名 `<epoch>-<pid>-<sig>.report`、模式 600，目錄 700（:245）。
- 現在**沒有任何測試跑過 `--migrate`**：`git grep -n -- "--migrate" tests/` 只有 `tests/settings_test.sh:126`（只驗提示文字）與 `tests/credentials_stay_in_settings_test.sh:32`（註解）。

## 維護者原話（verifier 出題用）
本任務沒有他的逐字裁示；來源是 issue #23 的描述。等價要求：
- 「搬完設定，舊的回報佇列不該被默默丟掉」→ T1、T2、T6。
- 「舊檔不刪、搬移可以證明完成之後才由使用者自己刪」（`settings.sh:898-901` 既有原則：複製不移動）→ T3、T4。

## 範圍：檔案（只准改這些，共 4 個）
- `scripts/settings.sh`（只改 `migrate_legacy` 內，於 token 區塊之後、「Done.」之前加一段；不改其他函式）
- `tests/settings_migrate_reports_test.sh`（新；以 `tests/settings_test.sh` 的頭部為樣板：`mktemp -d`、`HOME`／`XDG_CONFIG_HOME` 指進暫存目錄）
- `docs/SETTINGS.md`（只改 `## Migration` 一節，:536-551，加一句）
- `specs/migrate-reports-queue/ledger.md`（新，executor 進度帳本）

**不准動**：`scripts/report.sh`、`hooks/`、`scripts/where.sh`、`platform/**`、`.claude-plugin/plugin.json`、`CHANGELOG.md`、憲法。

## 作法
1. `migrate_legacy` 在 token 區塊之後：`oldq="$(dirname "$old")/reports"`；`newq="$ABF_ROOT/config/reports"`。
2. 若 `$oldq` 是目錄且內含 `*.report`：`mkdir -p "$newq"; chmod 700 "$newq"`；逐檔 `cp -p`（保留模式）到 `$newq`，**目標已存在就跳過**（不覆蓋）；每檔 `chmod 600`。
3. 輸出恰好一行：`  N queued report(s) copied to <newq>`（N＝實際複製數）；若有跳過再加一行 `  M already there - left alone`。沒有舊佇列時**不印這兩行也不建 `newq`**。
4. 「Done.」之後的「可刪除的舊檔」清單（:954-957）加上 `$oldq`（僅當它存在時）。
5. 不搬 `~/.local/state/agentic-bioflow/reports`（那是「設定還不存在時」的佇列，不屬於 T30 前的版面）。
6. 只複製 `*.report`；其他檔案（子目錄、雜物）不碰。

## 失敗先行測試（`tests/settings_migrate_reports_test.sh`）
每條用獨立暫存 `HOME`、`XDG_CONFIG_HOME`；舊設定檔 `$HOME/.config/agentic-bioflow/env.yaml`（模式 600，內容 `workspace_id: 1`）；根 `$TMP/root`。
| # | 情境 | 期望 | 現在 |
|---|---|---|---|
| T1 | 舊 `reports/` 有 2 份 `.report`，跑 `--migrate $TMP/root` | `$TMP/root/config/reports/` 有同名 2 份、內容逐位元相同 | 紅 |
| T2 | 搬完後 `AGENTIC_BIOFLOW_REPORTS_DIR` 不設，`bash scripts/report.sh --dir` | 印出 `$TMP/root/config/reports`，且 `report.sh list` 列出 2 份 | 紅 |
| T3 | 搬完後舊 `reports/` 與其 2 份檔仍在 | 都在 | 綠（鎖住不刪） |
| T4 | 新檔模式 600、新目錄模式 700 | `stat -c %a` 如述 | 紅 |
| T5 | 輸出含 `2 queued report(s) copied to` 與舊目錄路徑列在「可刪除」清單 | 字串存在 | 紅 |
| T6 | 新目錄已有同名檔（內容不同） | 不覆蓋、輸出含 `1 already there - left alone` | 紅 |
| T7 | 舊 `reports/` 不存在 | `$TMP/root/config/reports` 不被建立；輸出不含 `queued report` | 綠（鎖住） |
| T8 | 舊 `reports/` 內有 `notes.txt` 與子目錄 | 不被複製 | 綠（鎖住） |
| T9 | 舊設定在 `$LAB_RUNS_DIR/_personal/env.yaml`、佇列在 `_personal/reports/` | 同 T1 | 紅 |
| T10 | 既有 `--migrate` 行為：設定鍵、token 複製、`local_root` 略過的訊息不變 | 逐字相同 | 綠（鎖住） |

**現在會紅**：T1、T2、T4、T5、T6、T9。executor 先跑並貼出紅的輸出再動手；T1 若在 base 上是綠的，停下回報 BLOCKED。

**會改斷言的既有測試：無。** 已核對：`tests/settings_test.sh:126` 只比對 `--migrate <root>` 提示字樣；`tests/report_test.sh` 全程用 `AGENTIC_BIOFLOW_REPORTS_DIR`，不經 migrate；`tests/where_test.sh:118-123` 只比對 `report.sh --dir` 的路徑；`tests/jev_test.sh:496-498`（TC-053）與 `tests/machine_identity_test.sh:252` 讀 `docs/SETTINGS.md` 找特定字詞——本任務只**加**一句，不刪字。

## 完成標準（done when）
- T1–T10 全綠；`bash tests/settings_test.sh`、`tests/report_test.sh`、`tests/where_test.sh`、`tests/session_start_test.sh`、`tests/jev_test.sh`、`tests/machine_identity_test.sh` 不改而綠；整套 `bash tests/run_all.sh`（WSL）綠。
- `git diff --name-only` 只含上列 4 個檔；`hooks/`、`report.sh` 零改動（證據貼進 ledger）。
- 新增測試 ≤ 12 條；沒有真的連網或碰真實 `~/.config`（測試全程 `HOME` 指暫存）。

## 環境事實
- 全套測試只能在 WSL／Linux 跑（`tests/run_all.sh` 拒絕原生 Git Bash）；worktree 不可在同步磁碟。單檔 `bash tests/<name>.sh` 多數可在 Git Bash 跑，但本檔用 `stat -c`，以 WSL 為準。
- `tests/run_all.sh --list` 的數量由 `tests/run_all_count_test.sh:19-21` 即時比對，新增一個測試檔不需改任何清單。

## 不做
- 不改 `report.sh` 的 `reports_dir()`；不加「自動偵測舊佇列並提示」的新 session 提醒。
- 不搬 XDG state 佇列；不刪舊檔；不處理 issue #23 列的七個個別回報。
- **不需要 migration**（無資料表／JSON 欄位）；不改版本號。

## 裁決
- **複製不移動**：沿用 `settings.sh:898-901` 的原則（搬移未證明前不刪唯一一份）。
- **只認「舊設定檔旁邊」的 `reports/`**：與舊 `reports_dir()` 公式一致；XDG state 佇列是另一個版面，若真有人遇到，另開任務。
- **目標同名就跳過**：檔名含 epoch＋pid＋簽章，同名幾乎必為同一份；不覆蓋比覆蓋安全。

## 裁決（2026-10-25 06:50，developer-agent）
1. `~/.local/state` 底下設定前的佇列不搬：接受。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
