# Feature Specification: 「這台電腦」用自己的隨機 ID 認（machine identity）

**Feature Branch**: `006-machine-identity`

**Created**: 2026-10-02

**Status**: Draft

**Input**: #49，來自 004 的獨立驗收。`scripts/settings.sh` 的 `machine_id()` 是「主機名稱＋`uname -s`」。只屬於這台電腦的設定，存在 `config/machines/<這個名字>.yaml`：`tw_bin`、`site_bridge`、`ssh_control_path`，還有 004 起的 `proof_run`。這個命名會出兩種錯：

- **兩個環境撞名、共用設定**（不安全）：
  - 同一台 PC 的兩個 WSL 發行版，名字都是 `<主機>-Linux`。
  - 重灌後沿用主機名稱的電腦。
  - 撞名後，一台的證明紀錄會替另一台作保。
- **同一個環境改名、設定遺失**（煩人）：Git Bash 的 `uname -s` 含 Windows 組建號，例如 `MINGW64_NT-10.0-26200`。Windows 一更新，名字就變了，`tw_bin` 和證明紀錄都等於消失。

> 名詞見 `CONTEXT.md`。

## Clarifications

### Session 2026-10-02

- Q: 用什麼認「這台電腦」？ → A: 每個環境第一次需要時，產生一個隨機 ID，存在使用者家目錄的設定區（跟現有的根目錄指標 `~/.config/agentic-bioflow/root` 放一起）。主機改名、系統更新都不影響；兩個 WSL 各有自己的家目錄，所以不會撞。舊的設定檔自動搬過去一次。

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 系統更新、改主機名稱不會讓設定消失（Priority: P1）

**Acceptance Scenarios**:

1. **Given** 這個環境已經有 ID 和自己的設定檔，**When** `uname -s` 或主機名稱改變（模擬 Windows 更新），**Then** 仍然讀到同一份設定（`tw_bin`、`proof_run`）。（正常）
2. **Given** 第一次在這個環境寫入只屬於這台的設定，**When** 寫入，**Then** 產生 ID 檔，設定寫進 `machines/<ID>.yaml`。（正常）
3. **Given** 還沒有 ID 檔，**When** 只是讀設定（任何腳本 source `settings.sh`），**Then** 不產生任何檔案；讀取的規則見 US2。（正常）

### User Story 2 — 舊版的設定自動接上（Priority: P1）

**Acceptance Scenarios**:

1. **Given** 舊版留下 `machines/<主機>-<uname -s>.yaml`，而且名字跟現在算出來的完全相同，還沒有 ID 檔，**When** 讀設定，**Then** 讀得到舊檔的值。（正常）
2. **Given** 同上，**When** 第一次寫入只屬於這台的設定，**Then** 產生 ID，把舊檔改名成 `machines/<ID>.yaml`（內容保留），再寫入。（正常）
3. **Given** Git Bash 的舊檔名用的是較早的組建號（例如 `…-MINGW64_NT-10.0-26100.yaml`），現在是 `26200`，**When** 讀設定，**Then** 主機名稱相同、同屬 MINGW64 的舊檔可以接上。有好幾個符合時，取最新修改的那個。（正常）
4. **Given** 舊檔屬於另一個主機名稱，**When** 讀設定，**Then** 不接上。（例外）

### User Story 3 — 兩個環境不再共用身分（Priority: P1）

**Acceptance Scenarios**:

1. **Given** 兩個環境家目錄不同，但主機名稱和系統類型都相同（模擬兩個 WSL），**When** 各自寫入 `proof_run`，**Then** 寫進兩個不同的檔案，`setup_proof.sh --check` 各自只看到自己的。（正常）
2. **Given** ID 檔內容損壞（空白、含不合法字元），**When** 讀或寫，**Then** 不使用它，改產生新的 ID 並說明，絕不寫出路徑外的檔名。（例外）
3. **Given** ID 檔所在的資料夾無法寫入，**When** 寫入只屬於這台的設定，**Then** 失敗並說明原因，不退回舊的主機名稱命名。（例外）

## Requirements *(mandatory)*

- **FR-001**: 這台電腦的身分 MUST 是存在 `${XDG_CONFIG_HOME:-$HOME/.config}/agentic-bioflow/machine-id` 的一個值：可讀前綴（主機名稱，經過淨化）加上隨機尾碼，例如 `laptop-7f3a91c2`。產生方式 MUST 可攜：Git Bash、Linux、macOS 都要有，不依賴 Python。
- **FR-002**: ID 只在第一次寫入只屬於這台的設定時才產生；讀取時絕不產生檔案。
- **FR-003**: 沒有 ID 檔時，讀取 MUST 退回舊命名：先找完全相同的舊檔名；在 MINGW／MSYS／CYGWIN 環境下，再找「同主機名稱、同前綴、組建號不同」的舊檔，取最新的那個。
- **FR-004**: 第一次產生 ID 時，若有 FR-003 找到的舊檔，MUST 把它改名成新檔名（保留內容），而不是另建空檔。
- **FR-005**: ID 檔內容不合法時，MUST 視同沒有 ID 檔。合法字元是 `A-Za-z0-9._-`，長度 1–64。
- **FR-006**: `docs/SETTINGS.md` MUST 說明新的身分規則和搬移行為；`where.sh` 和 `settings.sh --summary` 若有印出機器檔路徑，MUST 跟著正確。

## 不在範圍

1. 整包家目錄被複製到新電腦（例如 Mac 的移轉輔助程式）時，ID 也會被複製過去。這種情況仍會共用身分；004 的「證明必須 7 天內、沒被別台用過」已經縮小了它的影響。
2. 叢集上 `reach: local` 換登入節點：家目錄是共用的，ID 也共用。這是同一個人在同一個叢集，視為同一台。

## Success Criteria

- **SC-001**: 模擬 Windows 更新（`uname -s` 改變）後，這台的設定和證明紀錄仍然有效。
- **SC-002**: 兩個家目錄不同的環境，不會再寫到同一個機器檔。

## Assumptions

- `od` 和 `/dev/urandom` 在 Git Bash、Linux、macOS 上都有。計畫階段要再確認；如果沒有，就用 `$RANDOM` 加上時間組出尾碼。
