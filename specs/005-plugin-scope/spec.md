# Feature Specification: 沒在用 agentic-bioflow 時，plugin 完全安靜（plugin scope）

**Feature Branch**: `005-plugin-scope`

**Created**: 2026-10-02

**Status**: Draft

**Input**: #48。2026-10-02 有一個 general-purpose subagent 為了一個不走 nf-core 的小分析，用下面這行唯讀查詢叢集設定：

```
wsl.exe -e ssh -o ControlPath=... -o BatchMode=yes <user>@<login-node> 'scontrol show partition; sacctmgr show qos'
```

結果被 `hooks/confirm_launch.sh` 以「直連 ssh 會耗一次驗證碼（PITFALLS 16b）」為由攔下來要人確認。自動模式蓋不掉 hook 的「要確認」，所以每次都卡住等人。這裡誤判了兩層：
- ①**範圍**：那個 session 根本沒在用 agentic-bioflow。
- ②**偵測**：經過 WSL 的 ssh 能共用已開的連線，而 `BatchMode=yes` 根本不會跳出輸入提示，兩者都不會耗驗證碼。

維護者的目標原話：「解決非使用 agentic-bioflow 情況下，誤呼叫任何 agentic-bioflow 設定的情況」。

> 名詞見 `CONTEXT.md`。本規格給維護者看，用中文；編號照 Spec Kit 慣例。

## Clarifications

### Session 2026-10-02

- Q: 沒在用 abf 時，要關掉多少？憲法的「安全網」寫明不可放寬，改它需要升主版號的修憲。 → A: **全部關掉**。包含「不准刪 rawdata／results」、「清 work/ 要確認」、「送分析要確認」，沒在用 abf 時都不觸發。這需要修憲到 2.0.0，並在同一張 PR 裡附理由、影響評估、所有引用處的同步修改，由維護者核可並合併。
- Q: 怎樣算「正在用 abf」？ → A: 下列三項任一成立就算。
  - ①這個 session 用過 abf：打過 `/agentic-bioflow:…` 指令、載入過 abf 的 skill，或說了會被導向 abf 的自然語言（plugin_intro 現有的判斷）。
  - ②目前資料夾在部署的設定根目錄、專案區或 run 區（`storage_root`）裡面。
  - ③這行指令本身呼叫了 plugin 的腳本、`tw`，或 Seqera 的 MCP 工具。
- Q: 在用 abf 時，經過 WSL 的 ssh，或加了 `BatchMode=yes` 的 ssh，還要攔嗎？ → A: 不攔，兩者都不會耗驗證碼。其他直連 ssh 照舊提醒。

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 沒在用 abf 的 session 不被打擾（Priority: P1）

在一個沒用過 abf、也不在部署資料夾裡的 session（包括它派出的 subagent），任何指令都不會被 abf 的 hook 攔下、要求確認，也不會被插入 abf 的說明文字。

**Independent Test**：把病例那行指令、一個 `tw launch`、一個 `rm -rf results`，都餵給各 hook，條件是「session 沒有使用紀錄、資料夾在部署外」，全部原樣放行，沒有任何輸出。

**Acceptance Scenarios**:

1. **Given** 沒在用 abf，**When** 執行病例那行 `wsl.exe -e ssh … BatchMode=yes …` 唯讀查詢，**Then** 不攔、沒輸出。（正常）
2. **Given** 沒在用 abf，**When** 執行任何直連 ssh／scp／rsync，**Then** 不攔。（正常）
3. **Given** 沒在用 abf，**When** 執行 `rm -rf results/`、`rm -rf work/`、`sbatch x.sh`、`nextflow run …`，**Then** 都不攔，因為維護者選了「全部關掉」。（正常；風險寫在 Assumptions）
4. **Given** 沒在用 abf，**When** 寫入任何檔案，包括 plugin 安裝目錄以外的檔案，**Then** walkthrough 和 guard 都不攔。（正常）
5. **Given** 沒在用 abf，**When** session 開場、每回合結束，**Then** 不插入 abf 的部署說明，也不插入「下一步」提醒。（正常）

### User Story 2 — 在用 abf 時，安全網照舊（Priority: P1）

只要符合三個條件的任一個，所有既有的關卡就照舊運作：送分析確認、刪資料拒絕、清 work/ 確認、步驟順序、plugin 檔案保護、開場說明、下一步提醒。

**Acceptance Scenarios**:

1. **Given** 這個 session 打過 `/agentic-bioflow:launch`（條件①），**When** 執行 `tw launch …`，**Then** 照舊顯示完整指令並要確認。（正常）
2. **Given** 目前資料夾在部署的 `storage_root` 底下（條件②），session 沒用過 abf，**When** 執行 `rm -rf results/`，**Then** 照舊拒絕。（正常）
3. **Given** session 沒用過 abf，資料夾也在部署外，**When** 指令本身呼叫 plugin 的腳本（例如 `…/scripts/on_site.sh … rm -rf results`）或 `tw launch`（條件③），**Then** 照舊攔。（正常）
4. **Given** 呼叫 Seqera／Tower 的 MCP 工具（條件③），**When** 那是送分析的動作，**Then** 照舊要確認。（正常）
5. **Given** 在用 abf，**When** 執行經過 WSL 的 ssh（`wsl.exe -e ssh …`／`wsl ssh …`）或帶 `-o BatchMode=yes` 的 ssh，**Then** 不跳「會耗驗證碼」的提醒。（正常）
6. **Given** 在用 abf，**When** 執行一般直連 `ssh user@host`，而且不是經過 WSL、也沒有 BatchMode，**Then** 照舊提醒。（例外；不能改壞）

### User Story 3 — 判斷失誤時往安全那邊倒（Priority: P1）

「在不在用」本身判斷不出來時，例如 hook 讀不到 session ID，或狀態資料夾壞了，就當成在用：寧可多攔一次，也不要漏攔。

**Acceptance Scenarios**:

1. **Given** hook 收到的輸入沒有 session ID，**When** 指令符合 abf 的關卡，**Then** 照舊攔。（例外）
2. **Given** 讀不到部署設定（沒有設定檔），而且 session 沒用過 abf、指令也沒呼叫 plugin，**When** 執行任何指令，**Then** 不攔。這台根本沒部署，判斷得出來，不算失誤。（正常）

## Requirements *(mandatory)*

- **FR-001**: 新增一個共用判斷「abf 是否在用」，所有 PreToolUse、SessionStart、Stop hook 一律先問它；不在用就立刻放行，沒有任何輸出。
- **FR-002**: 條件① MUST 由 plugin 自己記錄：`plugin_intro.sh` 判定使用者在用 abf 時，以 session ID 留下記號（沿用現有的每 session 記號機制）。subagent 跟主 session 共用 session ID，視為同一個範圍。
- **FR-003**: 條件② MUST 以部署設定為準：設定根目錄，以及 `storage_root`（在本機時）。沒有設定檔就視為條件②不成立。
- **FR-004**: 條件③ MUST 涵蓋三種指令：呼叫 plugin 自己的腳本或 hook（路徑含 plugin 根目錄，或 `scripts/<plugin 腳本名>`）、`tw`、Seqera／Tower MCP 工具（現有 matcher 已經只對它們觸發）。
- **FR-005**: 判斷不出來時（沒有 session ID、狀態資料夾讀不到但有部署），MUST 當成在用。
- **FR-006**: 在用 abf 時，「直連 ssh 會耗驗證碼」的提醒 MUST 略過兩種指令：經過 WSL 執行的 ssh（指令字是 `wsl`／`wsl.exe`），以及帶 `-o BatchMode=yes` 的 ssh。
- **FR-007**: 判斷 MUST 便宜：不在用的那條路，不得比現在多開一個以上的外部行程（#34：Windows Git Bash 每個 fork 都很貴）。
- **FR-008**: 憲法修到 2.0.0（MAJOR）。安全網的開頭改成「這些規則適用於使用 agentic-bioflow 的 session（定義見…）」。同一張 PR MUST 附理由、對現有部署的影響評估，並同步修改所有引用到的文件：`docs/PRINCIPLES.md`、根 `CLAUDE.md`、`docs/SITE_ADAPTER.md` 等，以及 hook 檔頭的說明。

## 不在範圍

1. 改變 abf 在用時各關卡本身的判斷，FR-006 的 ssh 例外除外。
2. #34 的整體速度問題：本次只保證不在用的那條路更快，不處理在用時的成本。
3. #35 留下的中低風險寫法。

## Success Criteria

- **SC-001**: 病例那行指令，在沒用 abf 的 session 裡不再被攔。
- **SC-002**: 在用 abf 時，現有全部安全網測試照舊通過，沒有比 main 退步。
- **SC-003**: 不在用時，每次 shell 呼叫的 hook 時間不比 main 長（以測試量測）。

## Assumptions

- **風險（維護者已知並選擇）**：沒在用 abf 的 session，資料夾也不在部署裡時，誤刪 results、直接 `sbatch` 都不會被 abf 攔。工作區自己的規則（例如謝馬爾工作區 `CLAUDE.md` 的護欄）不受影響，但那是模型自律，不是 hook。
- Claude Code 的 hook 輸入帶有 `session_id`，subagent 的工具呼叫帶的是主 session 的 ID。這點要在計畫階段以官方文件確認；如果不成立，subagent 會被當成「沒在用」，計畫要改用 `transcript_path` 或其他依據。
