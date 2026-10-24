# 測試案例：憲法文字對齊平台測試四段（6.0.2）

<!--
Written by the verifier (CONTRACT mode) from specs/constitution-platform-entries/plan.md.
This task has no spec.md; the plan is the spec, and the maintainer gave no verbatim sentence for this task
(plan "維護者原話"): the examples are the plan's own checks (E1-E7) and the Governance sentences it quotes.
IDs TC-E1 to TC-E7 are the plan's own labels; TC-E8 and up are added to cover every other statement in the plan.
「手動」在本檔指：閱卷者看 `git diff origin/v3...HEAD` 與 ledger 貼的證據（計畫不准動 docs/TESTING.md，所以這些步驟不在那裡）。
-->

**規格**：`specs/constitution-platform-entries/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

背景（一句白話）：憲法有四處寫「這條規則的檢查由 `tests/platform_test.sh` 執行」，但那個檔現在只跑平台測試的第 1 部分。這次只把說明改成實際的四個入口，並記成 6.0.2 版；不改任何規則的意思。

## User Story 1 — 憲法四處的「由誰執行」改成實際的四個入口（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-E1 | 計畫 E1；作法 1 | 功能 | 憲法已改完 | 把 `.specify/memory/constitution.md` 的換行全部攤平成一行，找 ``run by `tests/platform_test.sh` `` 這串字 | 整份憲法（含新增的 6.0.2 條目，也含原本「run by」與檔名被換行隔開的第 195-196 行）都找不到這串字；6.0.2 條目引用舊文時換了寫法 | 自動：`tests/constitution_scope_test.sh`（E1） |
| TC-E2 | 計畫 E2；作法 1 | 功能 | 同上 | 在憲法裡找 `tests/run_all.sh` 與四個檔名 `tests/platform_test.sh`、`tests/platform_shard_2_test.sh`、`tests/platform_shard_3_test.sh`、`tests/platform_clock_test.sh` | `tests/run_all.sh` 出現至少一次，四個檔名各自至少出現一次 | 自動：`tests/constitution_scope_test.sh`（E2） |
| TC-E3 | 計畫 E3；既有保護 | 功能 | 同上 | 檢查 `tests/` 底下上述四個入口檔 | 四個檔都存在而且可執行（憲法點名的檔不是憑空的）。這條現在就綠，是鎖住用的 | 自動：`tests/constitution_scope_test.sh`（E3） |
| TC-E6 | 計畫 E6；作法 2 | 功能 | 憲法已改完 | 直接跑 `bash tests/constitution_6_test.sh` 與 `bash tests/constitution_checks_exist_test.sh` | 兩個都 exit 0：規則 1–3 點名的測試名稱（`test_tc030_*`、`test_tcb04_*`…）仍都在對應的測試檔裡。這條現在就綠，是鎖住用的 | 自動：`tests/constitution_scope_test.sh`（E6，實際執行這兩個檔） |
| TC-E8 | 作法 1（第一次出現） | 功能 | 憲法已改完 | 看原第 46 行那一處（「The channel rule has its own check…」）的新句子 | 句子寫成「run by `tests/run_all.sh` through its four platform entries」並在括號內逐一列出四個檔名全名；原句後面的「an unconfirmed launch is refused through the MCP tool and through the web route…」和 `test_tch09_*`、`test_tch09_b_c_*` 說明一個字不變 | 手動：看 diff（證據貼 ledger） |
| TC-E9 | 作法 1（其餘三處） | 功能 | 憲法已改完 | 逐一看原第 51 行（`test_tc030_…`／`test_tc031_…` 那條 Check）、原第 195-196 行（規則 2 的 Check 清單結尾）、原第 214 行（規則 3 的 Check 結尾）的新句子 | 三處每一處的句子本身都含字串 `tests/run_all.sh`，說明由 `tests/run_all.sh` 的平台入口執行（第一個是 `tests/platform_test.sh`）；沒有任何一處再把 `tests/platform_test.sh` 當成唯一執行者。不能靠 6.0.2 條目那邊出現 `tests/run_all.sh` 來充數 | 手動：看 diff（證據貼 ledger） |
| TC-E10 | 裁決 2 | 功能 | 憲法已改完 | 在上面四處規則文字裡找「第 1／2／3 部分」「part 1／2／3」這類說「某測試在第幾部分」的字 | 四處規則文字只講「四個入口」，沒有任何一處寫死哪個測試在第幾部分（部分的劃分會隨測試增減重排，寫死會再過期）。部分歸屬只允許出現在 6.0.2 的 Rationale | 手動：看 diff |
| TC-E11 | 完成標準第 2 點 | 功能 | 憲法已改完 | 看 `git diff origin/v3...HEAD -- .specify/memory/constitution.md` | 憲法的變動只有三類：上述四處「由誰執行」的措辭、新增的 6.0.2 條目、最後的版本行。沒有任何其他行被改、刪、搬 | 手動：看 diff（證據貼 ledger） |

## User Story 2 — 6.0.2 條目與版本行（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-E4 | 計畫 E4；作法 3 | 功能 | 憲法已改完 | 找標題 `### 6.0.2 (2026-10-24)`，往下看它的小段 | 有這個標題，其後依序出現 `**Rationale`、`**What changes`、`**Sync Impact Report`、`**Impact on existing deployments`、`**Version.** PATCH`、`**Approval` | 自動：`tests/constitution_scope_test.sh`（E4） |
| TC-E5 | 計畫 E5；作法 4 | 功能 | 同上 | 看憲法最後一個非空白行 | 逐字等於 `**Version**: 6.0.2 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-10-24`，而且它是檔案最後一個非空行 | 自動：`tests/constitution_scope_test.sh`（E5） |
| TC-E7 | 計畫 E7；Governance「PATCH for wording that changes no meaning」 | 功能 | 同上 | 看 6.0.2 條目全文 | 條目含 "no rule changes meaning"（版本類別是 PATCH，理由是只改措辭） | 自動：`tests/constitution_scope_test.sh`（E7） |
| TC-E12 | 作法 3 | 功能 | 同上 | 看 6.0.2 條目在檔案中的位置 | 條目緊接在 6.0.1 條目（原第 585-609 行）之後、`## Governance` 之前；標題是 `### 6.0.2 (2026-10-24): the platform checks run through four entries, not one` | 手動：看 diff |
| TC-E13 | 作法 3（Rationale）；查證結果 | 功能 | 同上 | 讀 6.0.2 的 **Rationale** | 說明 #200 把平台測試拆成四個 `run_all.sh` 入口，所以憲法四處與現實不符；並列出實測的歸屬：`test_actions_layer` 在第 1 部分，`test_resume_entrypoints`、`test_secrets` 在第 2 部分，`test_confirm_page`、`test_human_channel`、`test_keep_submissions` 在第 3 部分。閱卷者可用 `ABF_PLATFORM_LIST=1 ABF_PLATFORM_PART=<n> bash tests/platform_test.sh` 重現（只列檔、不執行測試） | 手動：看 diff 並重現列表 |
| TC-E14 | 作法 3（What changes） | 功能 | 同上 | 讀 6.0.2 的 **What changes** | 說明改的是四處措辭，並明講沒有規則、檢查名稱或測試被改 | 手動：看 diff |
| TC-E15 | 作法 3（Sync Impact Report）；Governance「matching update to any document that cites the changed rule」 | 功能 | 同上 | 讀 6.0.2 的 **Sync Impact Report** | 寫出一起更新的是 `tests/constitution_scope_test.sh` 與 `tests/platform_direction_docs_test.sh` 的版本釘子，並說明其他文件（`docs/TESTING.md` 等）本來就已正確 | 手動：看 diff |
| TC-E16 | 作法 3（Impact） | 功能 | 同上 | 讀 6.0.2 的 **Impact on existing deployments** | 寫 None（沒有任何已部署的東西受影響） | 手動：看 diff |
| TC-E17 | 作法 3（Version、Approval） | 功能 | 同上 | 讀 6.0.2 的 **Version.** 與 **Approval.** | **Version.** 寫 PATCH, under Governance: wording changes; no rule changes meaning；**Approval.** 沿用 6.0.1 的句子（"The maintainer approves and merges the pull request that carries this change."） | 手動：看 diff |
| TC-E18 | 環境事實 | 功能 | 同上 | 看 6.0.2 條目的語言與路徑寫法 | 條目是英文；路徑與檔名都用反引號 | 手動：看 diff |
| TC-E19 | 作法 4（Ratified 不動） | 功能 | 同上 | 看版本行與既有檢查 | `**Ratified**: 2026-09-28` 沒變；既有的 "Ratified date is untouched" 檢查維持綠燈 | 自動：`tests/constitution_scope_test.sh`（既有檢查） |

## User Story 3 — 版本釘子跟著更新，完整測試維持綠燈（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-E20 | 作法 5 | 功能 | 憲法已改完 | 看 `tests/constitution_scope_test.sh` 原第 29 行 | 釘的是 `**Version**: 6.0.2`，標籤文字補上 "6.0.2 came after"，檢查通過 | 自動：`tests/constitution_scope_test.sh` |
| TC-E21 | 作法 5 | 功能 | 同上 | 看 `tests/constitution_scope_test.sh` 原第 31 行 | 釘的是 `**Last Amended**: 2026-10-24`，檢查通過 | 自動：`tests/constitution_scope_test.sh` |
| TC-E22 | 作法 5 | 功能 | 同上 | 看 `tests/platform_direction_docs_test.sh` 原第 52-54 行（含標籤） | 最後一行比對的是 6.0.2 那行版本字串（與 TC-E5 逐字相同），檢查通過 | 自動：`tests/platform_direction_docs_test.sh` |
| TC-E23 | 「會改斷言的既有測試（有意）」 | 功能 | 同上 | 看 `git diff origin/v3...HEAD -- tests/`，對照 base | 既有測試只動了 TC-E20、E21、E22 那三處（版本、日期、標籤）；沒有任何斷言被刪、放寬、跳過；其餘既有測試檔一個字沒改。`constitution_scope_test.sh` 新增的只有 E1–E7 這類新斷言 | 手動：看 diff |
| TC-E24 | 完成標準第 1 點 | 功能 | 同上 | 分別單跑 `bash tests/constitution_scope_test.sh`、`platform_direction_docs_test.sh`、`constitution_6_test.sh`、`constitution_checks_exist_test.sh`、`dev_workflow_test.sh` | 五個都 exit 0；`constitution_scope_test.sh` 的 E1–E7 全綠 | 自動 |
| TC-E25 | 完成標準第 1 點 | 功能 | 同上 | 在 WSL 跑整個 `bash tests/run_all.sh`（worktree 在本機磁碟，不在同步磁碟） | 全綠 | 自動：`tests/run_all.sh` |
| TC-E26 | 失敗先行（計畫「現在」欄） | 例外 | 拿 base（`origin/v3`）版的憲法放進暫存的檔案路徑，用新版 `tests/constitution_scope_test.sh` 去比對 | 閱卷者對 base 憲法跑新增的 E1–E7 | E1、E2、E4、E5、E7 失敗（紅）；E3、E6 通過（綠）。證明這些測試真的會抓到舊文字，不是永遠綠 | 手動：閱卷者重現（結果貼 ledger） |

## User Story 4 — 交付方式：C 級，由維護者核可（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-E27 | 範圍；裁決 3 與 2026-10-25 裁決；Governance「Only the maintainer approves and merges it」 | 功能 | 實作完成 | 看 PR | 已開 PR，沒有自合、沒有掛自動合併；說明裡有以前／以後文字對照、實測表（各測試落在第幾部分）、並寫明等維護者核可 | 手動：看 PR 與 ledger |
| TC-E28 | 完成標準第 2 點 | 功能 | 實作完成 | 看 `specs/constitution-platform-entries/ledger.md` | 貼了 `git diff --stat origin/v3...HEAD` 與憲法 diff 的證據，足以讓人確認 TC-E11、TC-E31 | 手動：看 ledger |

## 不在範圍（計畫「不做」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-E29 | 不做：不改任何規則的意思 | 不在範圍 | 憲法已改完 | 看憲法 diff，除了四處「由誰執行」措辭、6.0.2 條目、版本行以外的任何規則文字 | 規則本文一個字沒變（MUST／MUST NOT 等語句、規則 1–3 的敘述都相同） | 手動：看 diff |
| TC-E30 | 不做：不改檢查名稱、不新增或刪除測試 | 不在範圍 | 同上 | 比對四處規則文字的測試名稱（`test_tch09_*`、`test_tch09_b_c_*`、`test_tc030_…`、`test_tc031_…`、`test_tcb04_*` 到 `test_tcb08_*`、`test_tca14_*`、`test_tc142_*`、`test_tc144_*`、`test_tc034_*`、`test_tc037_*`、`test_tc038_*`、`test_tc040_*`、`test_tc042_*`、`test_tc_i03_*`、`test_tc041_*`、`test_tcf10_f11_*`）；看 diff 有無新增或刪除的測試檔 | 名稱與 base 逐字相同；`platform/`、`tests/platform_*test.sh` 沒有任何增刪改，沒有測試檔被新增或刪除（只在 `constitution_scope_test.sh` 內加 E1–E7 斷言） | 手動：看 diff |
| TC-E31 | 範圍：檔案；不准動清單；不做：不動 `docs/TESTING.md` | 不在範圍 | 實作完成 | 跑 `git diff --stat origin/v3...HEAD` | 變動檔只有 `.specify/memory/constitution.md`、`tests/constitution_scope_test.sh`、`tests/platform_direction_docs_test.sh`、`specs/constitution-platform-entries/ledger.md`（外加計畫自己已在 base 之上的 `plan.md`／合約檔，若尚未進 base）；`docs/*`（含 `docs/TESTING.md`）、`CLAUDE.md`、`README.md`、`tests/platform_*test.sh`、`tests/run_all.sh`、`platform/` 都沒出現 | 手動：看 diff stat |
| TC-E32 | 不做：不處理 `README.md`／`docs/PRINCIPLES.md` 的 6.0.0 引用 | 不在範圍 | 同上 | 看這兩個檔與 `CLAUDE.md` 原第 211 行 | `README.md`、`docs/PRINCIPLES.md` 的 6.0.0 引用沒被改；`CLAUDE.md` 該處仍寫 "constitution 6.0.1"（那是「那條規則何時出現」，不是現行版本） | 手動：看 diff |
| TC-E33 | 不做：不需要 migration | 不在範圍 | 同上 | 看 diff 有無資料表、JSON 內容或遷移腳本的變動 | 沒有任何 migration、資料表或 JSON 內容改變 | 手動：看 diff stat |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-E34 | Governance：修正要在同一個 PR 帶齊理由、衝擊評估、版本升級、相符文件更新 | 功能 | 實作完成 | 看這個 PR 的 diff | 同一個 PR 內同時有：6.0.2 的 Rationale、Impact on existing deployments（None）、版本行升到 6.0.2、兩個釘版本的測試同步更新；版本升級是 PATCH（6.0.1 到 6.0.2），不是 MINOR 或 MAJOR | 手動：看 diff |
| TC-E35 | Safety Net 區段與不變量 1–13 | 功能 | 憲法已改完 | 看憲法 diff 在 `## Safety Net` 區段內的變動；再確認不變量 1–13 每條仍點名自己的檢查 | Safety Net 區段沒有任何變動；不變量 1–13 仍各自點名檢查，被點名的檢查仍存在（對應 TC-E6） | 手動：看 diff；TC-E6 自動 |
