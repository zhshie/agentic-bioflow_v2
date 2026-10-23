# 測試案例：init_workspace_test 的「no run area known」案例不受本機部署設定影響

**規格**：`specs/init-workspace-hermetic/plan.md`（本任務沒有 spec.md；「需求」指 plan 的〈目標〉〈作法〉〈失敗先行測試〉〈完成標準〉〈不做〉，下面以「計畫-目標」等標示）　**總覽**：`test-case-overview.md`

維護者原話：計畫寫明「無原話」。所以下面每個預期結果都只取自計畫的文字，沒有另外發明行為。

白話背景：`tests/init_workspace_test.sh` 有一條測試，要證明「沒告訴程式把資料夾建在哪時，它會明確拒絕（結束碼 2、說 `no run area known`），而不是亂建」。但開發機上有一個真實的「部署指標」，指向一個 `/work/...` 的位置。測試沒隔離，程式就讀到那個位置、嘗試建立 `/work`，失敗變成結束碼 1，測試紅。CI 上沒有這個指標，所以是綠的。這次要讓這條測試在任何機器上結果都一樣。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

「部署設定」在這份文件裡指：一個暫存家目錄裡有 `.config/agentic-bioflow/root` 指標檔，指到一個根目錄；該根目錄的 `config/env.yaml` 寫了 `storage_root: <一個不可寫的路徑>`。夾具（fixture）一律建在測試的暫存目錄下，絕不使用真實的 `~/.config/agentic-bioflow`。

## User Story 1 — 既有案例在任何機器上都得結束碼 2（優先度 P1）

案例名稱：`site side with no run area known fails clearly, not silently`（原第 267-268 行）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫-目標；計畫-作法 2 | 功能 | 乾淨機器：沒有 `LAB_RUNS_DIR`、沒有 `LAB_SETTINGS_FILE`、家目錄裡沒有任何 agentic-bioflow 設定 | 執行 `bash tests/init_workspace_test.sh` | 該案例那一行顯示 `ok`（結束碼 2，輸出含 `no run area known`） | 自動：`tests/init_workspace_test.sh` |
| TC-002 | 計畫-目標；計畫-作法 2 | 功能 | 執行測試的 shell 裡 `HOME` 指向一個暫存家目錄，裡面有「部署設定」（指標檔指到 `storage_root` 為不可寫路徑的根） | 在這個環境下執行 `bash tests/init_workspace_test.sh` | 該案例那一行仍顯示 `ok`，不是 `FAIL: rc 1`，輸出沒有 `cannot create directory` | 自動：`tests/init_workspace_test.sh`（在帶有該 `HOME` 的 shell 內執行） |
| TC-003 | 計畫-作法 2（XDG 路徑） | 功能 | 執行測試的 shell 裡 `XDG_CONFIG_HOME` 指向一個暫存目錄，其下 `agentic-bioflow/root` 指到 `storage_root` 為不可寫路徑的根 | 在這個環境下執行 `bash tests/init_workspace_test.sh` | 該案例那一行仍顯示 `ok` | 自動：`tests/init_workspace_test.sh`（在帶有該變數的 shell 內執行） |
| TC-004 | 計畫-作法 2（「settings.sh 用來找部署設定的變數」） | 功能 | 執行測試的 shell 裡 `LAB_SETTINGS_FILE` 指向一個暫存的 `.../config/env.yaml`，檔內 `storage_root` 為不可寫路徑 | 在這個環境下執行 `bash tests/init_workspace_test.sh` | 該案例那一行仍顯示 `ok` | 自動：`tests/init_workspace_test.sh`（在帶有該變數的 shell 內執行） |
| TC-005 | 計畫-作法 2（`env -u LAB_RUNS_DIR`） | 功能 | 執行測試的 shell 裡 `LAB_RUNS_DIR` 已設為某個暫存目錄 | 在這個環境下執行 `bash tests/init_workspace_test.sh` | 該案例那一行仍顯示 `ok`（它沒有被這個變數悄悄接管；結束碼仍是 2） | 自動：`tests/init_workspace_test.sh`（在帶有該變數的 shell 內執行） |
| TC-006 | 計畫-作法 2（「保留 rc 2 與 "no run area known" 的斷言」） | 功能 | 實作完成後 | 閱讀該案例的寫法 | 案例名稱不變；仍斷言結束碼 2；仍斷言輸出含 `no run area known`；斷言沒有被放寬（沒有改成只看結束碼、沒有改成別的字串） | 自動：`tests/init_workspace_test.sh` |
| TC-007 | 計畫-範圍（只改這一個案例的環境隔離） | 例外 | 實作完成後 | 執行 `bash tests/init_workspace_test.sh`，看「Bad input」那一段其他案例（no side given／unknown side／missing --user／slash in --user／reserved name／--run without --project）和 `none of the refused calls created anything` | 這些案例全部仍是 `ok`，沒被隔離寫法連帶改變；沒有任何一條被刪除、跳過或改弱 | 自動：`tests/init_workspace_test.sh` |

## User Story 2 — 新案例「有部署設定的家目錄」（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-008 | 計畫-失敗先行測試（新案例，斷言 rc 2） | 功能 | 實作完成後 | 執行 `bash tests/init_workspace_test.sh` | 輸出裡有一條名為 `site side ignores the developer's own deployment when testing` 的案例，顯示 `ok`；它在「家目錄含部署指標、`storage_root` 不可寫」的情境下跑 `site --user alice`，結束碼為 2，輸出含 `no run area known` | 自動：`tests/init_workspace_test.sh` |
| TC-009 | 計畫-失敗先行測試（「HOME 指向一個含部署指標、storage_root 為不可寫路徑的暫存家目錄」） | 功能 | 實作完成後 | 閱讀新案例的夾具，並在不做隔離的情況下用同一夾具跑 `site --user alice` | 夾具確實有指標檔、有 `config/env.yaml`、`storage_root` 已設且是「就算以 root 身分也建不出來」的路徑；不做隔離時結果不是結束碼 2。也就是這個案例在隔離被拿掉時會變紅，不是永遠綠 | 自動：`tests/init_workspace_test.sh` |
| TC-010 | 計畫-失敗先行測試（「先證明現況會紅」：舊寫法 rc 1，改後 rc 2） | 功能 | 實作完成後 | 在上述夾具家目錄下用舊寫法（只 `env -u LAB_RUNS_DIR`）跑一次，再用新寫法跑一次 | 舊寫法結束碼為 1（`mkdir: cannot create directory`）；新寫法結束碼為 2。這組對照寫在測試裡或 `specs/init-workspace-hermetic/ledger.md` | 手動：閱卷者讀 `ledger.md`／測試檔，並重跑舊寫法對照 |

## User Story 3 — 完成標準（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 計畫-完成標準（「該檔所有案例綠」） | 功能 | 在 Linux／WSL，家目錄有真實部署設定的開發機 | `bash tests/init_workspace_test.sh` | 結尾沒有任何 `FAIL`，整檔結束碼 0 | 自動：`tests/init_workspace_test.sh` |
| TC-012 | 計畫-完成標準（「全套綠；這次不可以再有那一條紅」） | 功能 | 在 WSL 或 Linux | `tests/run_all.sh` | 全套結束碼 0，沒有任何失敗檔，特別是 `init_workspace_test.sh` 不再紅 | 自動：`tests/run_all.sh` |

## 憲法與安全網

計畫沒有碰憲法的不變量。這裡只放專案「CLAUDE.md」寫明的禁令：不可對真實部署使用 `~/.config/agentic-bioflow`。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 專案 CLAUDE.md「Never run: …uses `~/.config/agentic-bioflow` against a real deployment」；計畫-作法 2 | 例外 | 開發機的真實 `~/.config/agentic-bioflow` 內有部署指標 | 執行 `bash tests/init_workspace_test.sh`（含新案例） | 新案例與被修改的案例，其 `HOME`、`XDG_CONFIG_HOME` 都指向測試暫存目錄之下；真實 `~/.config/agentic-bioflow` 內容在測試前後不變（沒讀、沒寫）；夾具在測試結束時隨暫存目錄一起清掉 | 自動：`tests/init_workspace_test.sh` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 計畫-不做（不改 `init_workspace.sh`、`settings.sh`）；計畫-作法 3 | 不在範圍 | 實作完成 | `git diff <base>...HEAD -- scripts/` | 沒有任何差異；兩支腳本沒有被加入 `storage_root` 的預設值或任何繞過 | 手動：閱卷者以 `git diff` 核對（`docs/TESTING.md` 無對應步驟，屬差異檢查） |
| TC-015 | 計畫-裁決 1（不需要 migration） | 不在範圍 | 實作完成 | `git diff <base>...HEAD --stat` | 沒有新增 migration，也沒有資料結構或資料內容變動 | 手動：閱卷者以 `git diff` 核對 |
| TC-016 | 計畫-範圍：檔案 | 不在範圍 | 實作完成 | `git diff <base>...HEAD --stat`（排除 `plan.md`） | 變動的檔案只有 `tests/init_workspace_test.sh` 與 `specs/init-workspace-hermetic/ledger.md`；沒有改 `spec.md`、`test-case*.md`、憲法、`.github/` 等 | 手動：閱卷者以 `git diff` 核對 |

<!--
Rules for the writer:
- Every acceptance scenario and every FR in spec.md maps to at least one TC. Every
  "out of scope" item in spec.md maps to at least one 不在範圍 TC.
- A TC tests one thing. Two expectations = two rows.
- 驗證方式 is 自動 (a test file under tests/, named once it exists, "自動" until then)
  or 手動 (a step in docs/TESTING.md's manual half). Nothing else.
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
