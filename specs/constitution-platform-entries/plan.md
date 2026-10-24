---
id: constitution-platform-entries
title: 憲法的「平台測試由 tests/platform_test.sh 執行」改成實際的四個入口（只改措辭，6.0.2 PATCH）
tier: C
kinds: docs
lane: L-const
base: v3（`origin/v3` @ 2385f97；所有行號都是該版本）
source: developer-agent 讀碼查證（2026-10-24）。病灶來自 #200 platform-test-shards：平台測試拆成四個 run_all.sh 入口後，憲法四處仍寫單一檔名。
---

# constitution-platform-entries

> 憲法修正一律由維護者核可並按 merge（`constitution.md:611-621` Governance；6.0.1 的先例是附他的原話）。所以本任務是 **C 級**：executor 照做、開 PR，但不自合。**不改任何規則的意思，只改「由誰執行」的檔名說明**（PATCH，`constitution.md:620`）。

## 目標
憲法四處說某些檢查「run by `tests/platform_test.sh`」，但 #200 之後那個檔只跑平台測試的第 1 部分；規則 2 點名的 `test_human_channel.py`、`test_keep_submissions.py` 等在第 3 部分（`platform_shard_3_test.sh`）。改成「由 `tests/run_all.sh` 的四個平台入口執行」，讓憲法的檢查說明與現實一致，並以 6.0.2 記錄。對使用者的意義：照憲法去找「這條規則的檢查在哪跑」不會找錯檔、更不會誤以為單跑 `platform_test.sh` 就涵蓋憲法點名的全部測試。

### 查證結果（皆 `origin/v3`）
- 憲法四處：`.specify/memory/constitution.md:46`（"The channel rule has its own check, run by `tests/platform_test.sh`:"）、`:51`（"*Check:* run by `tests/platform_test.sh`: the platform tests"）、`:195-196`（"run by" 換行 "`tests/platform_test.sh`."）、`:214`（"run by `tests/platform_test.sh`."）。
- 現實：`tests/platform_test.sh:46-57` 的註解說平台測試分成「part 1（本檔）、`platform_shard_2_test.sh`、`platform_shard_3_test.sh`、`platform_clock_test.sh`」四個入口；`docs/TESTING.md:13` 與 `:129`、`:140`、`:169` 已改成列四個入口。憲法是唯一漏掉的主文件。
- 實測各規則點名的測試落在哪一部分（對解壓的 `origin/v3` 跑 `ABF_PLATFORM_LIST=1 ABF_PLATFORM_PART=<n> bash tests/platform_test.sh`）：`test_actions_layer` 在第 1 部分；`test_resume_entrypoints`、`test_secrets` 在第 2 部分；`test_confirm_page`、`test_human_channel`、`test_keep_submissions` 在第 3 部分。所以「只跑 `platform_test.sh`」確實漏掉憲法規則 2、3 的大半檢查。
- 既有保護：`platform/tests/test_platform_parts.py:204-210`（PS-46）已證明這些檔每個都恰好被執行一次；`tests/run_all.sh:167` 不准隔離這四個入口。本任務不碰它們。
- 釘著版本與日期的測試：`tests/constitution_scope_test.sh:29`（`**Version**: 6.0.1`）、`:31`（`**Last Amended**: 2026-10-22`）；`tests/platform_direction_docs_test.sh:52-54`（最後一行逐字等於 6.0.1 那行）。

## 維護者原話（verifier 出題用）
沒有他針對這件事的逐字裁示；依據是憲法自己的規則與 6.0.1 的先例：
- 「憲法修正我同意，開 PR 把 Roles 那句改成新位置……」（`constitution.md` 6.0.1 Rationale，:585-596；整個條目 :585-609）→ 修正走 PR、由他核可；本任務的 PR 說明要附他核可的位置，沒有就停在 PR 等他回。
- 憲法 Governance：「An amendment requires, in one PR: the rationale for the change, an assessment of what it breaks for existing deployments, the version bump, and the matching update to any document that cites the changed rule.」→ T3、T4。
- 憲法 Governance：「PATCH for wording that changes no meaning.」→ T6。

## 範圍：檔案
- `.specify/memory/constitution.md`
- `tests/constitution_scope_test.sh`
- `tests/platform_direction_docs_test.sh`
- `specs/constitution-platform-entries/ledger.md`
- **不准動**：`docs/*`（TESTING.md 已正確）、`CLAUDE.md`（:211 的 "constitution 6.0.1" 是「那條規則何時出現」，不是現行版本）、`README.md`、`tests/platform_*test.sh`、`tests/run_all.sh`、`platform/`。

## 作法
1. 四處改寫（不改規則本文，只換「執行者」說明）。第一次出現（:46）寫全：「run by `tests/run_all.sh` through its four platform entries (`tests/platform_test.sh`, `tests/platform_shard_2_test.sh`, `tests/platform_shard_3_test.sh`, `tests/platform_clock_test.sh`)」；:51、:195-196、:214 寫「run by the platform entries of `tests/run_all.sh` (the first is `tests/platform_test.sh`; see the rule on the run index above)」之類的短句，**但每一處都必須含 `tests/run_all.sh` 這個字串**，且不得再出現 "run by `tests/platform_test.sh`"（含換行後）。
2. 每條規則點名的測試名稱（`test_tc030_*`、`test_tcb04_*`…）一個字都不動；`tests/constitution_6_test.sh` 的 `defined` 檢查靠它們。
3. 在 6.0.1 條目（:585-609）之後、`## Governance`（:611）之前新增 `### 6.0.2 (2026-10-24): the platform checks run through four entries, not one`，仿 6.0.1 的五個小段：**Rationale**（#200 拆分；憲法四處與現實不符，列出實測各測試落在哪一部分）、**What changes**（四處措辭；沒有規則、檢查名稱或測試被改）、**Sync Impact Report**（寫：`tests/constitution_scope_test.sh`、`tests/platform_direction_docs_test.sh` 的版本釘子；其他文件已正確）、**Impact on existing deployments**（None）、**Version.** PATCH, under Governance: wording changes; no rule changes meaning. 與 **Approval.**（沿用 6.0.1 的句子）。
4. 版本行（:625）改為 `**Version**: 6.0.2 | **Ratified**: 2026-09-28 | **Last Amended**: 2026-10-24`（Ratified 不動）。
5. 兩個既有測試的釘子改成 6.0.2 與 2026-10-24；`constitution_scope_test.sh:29` 的標籤文字補上 "6.0.2 came after"。

## 失敗先行測試
新增在 `tests/constitution_scope_test.sh`（用該檔既有的 `has <label> <file> <fixed string>`（:19）；要攤平換行時自己用 `tr "
" " "`；`$C` 是憲法路徑）。標籤 TC-E1…；**現在紅**的是 E1–E5、E7。
| # | 斷言 | 現在 |
|---|---|---|
| E1 | 憲法攤平成一行後，不含 "run by `tests/platform_test.sh`" | 紅（四處） |
| E2 | 憲法含 `tests/run_all.sh`，且含四個入口檔名各至少一次 | 紅 |
| E3 | 上述四個檔名在 `tests/` 都存在且可執行 | 綠（鎖住） |
| E4 | 有 `### 6.0.2 (2026-10-24)` 標題，其後依序含 `**Rationale`、`**What changes`、`**Sync Impact Report`、`**Impact on existing deployments`、`**Version.** PATCH`、`**Approval` | 紅 |
| E5 | 版本行逐字為 `**Version**: 6.0.2 \| **Ratified**: 2026-09-28 \| **Last Amended**: 2026-10-24`，且是最後一個非空行 | 紅 |
| E6 | 規則 1–3 點名的測試名稱仍在（直接跑 `bash tests/constitution_6_test.sh` 與 `bash tests/constitution_checks_exist_test.sh`，皆 exit 0） | 綠（鎖住） |
| E7 | 6.0.2 條目含 "no rule changes meaning" | 紅 |

**會改斷言的既有測試（有意）**：`tests/constitution_scope_test.sh:29`、`:31`，`tests/platform_direction_docs_test.sh:52-54`（含其標籤）。其餘既有測試全部不准改。

## 完成標準（done when）
- E1–E7 全綠；整個 `bash tests/run_all.sh`（WSL）綠；`bash tests/constitution_scope_test.sh`、`platform_direction_docs_test.sh`、`constitution_6_test.sh`、`constitution_checks_exist_test.sh`、`dev_workflow_test.sh` 單跑皆綠。
- `git diff --stat origin/v3...HEAD` 只含上列 4 個檔；憲法 diff 除了那四處措辭、新 6.0.2 條目、版本行之外沒有其他變動（閱卷者看 diff 確認，證據貼 ledger，見 `dev-plans/README.md` 通例）。
- PR 說明附：以前／以後文字對照、實測表（各測試落在第幾部分）、等維護者核可。

## 環境事實
- 全套測試要在 WSL／Linux 跑；worktree 不可在同步磁碟（repo `CLAUDE.md`「For the executor and verifier」）。
- 憲法是英文檔；新條目用英文。路徑與檔名用反引號。
- `ABF_PLATFORM_LIST=1` 只列檔、不執行測試，可安全重現「各測試落在哪一部分」。

## 不做
- 不改任何規則的意思、不改檢查名稱、不新增或刪除測試、不動 `docs/TESTING.md`。
- 不處理 `README.md`／`docs/PRINCIPLES.md` 的 6.0.0 引用（那些是「該規則何時進憲法」，不是現行版本）。
- 不需要 migration（沒有資料表或 JSON 內容改變）。

## 裁決
1. **為什麼是 PATCH 不是不改版**：憲法 Governance 規定任何修正都要版本行與日期；措辭修正是 PATCH（6.0.1 先例）。
2. **為什麼寫「四個入口」而不是列每個測試檔所在的部分**：部分的劃分是「按耗時平衡的固定清單」（`tests/platform_test.sh:52-55`），會隨測試增減重排；憲法若寫死會再過期。入口檔名四個是穩定的（`test_platform_parts.py:200-201` 釘著）。
3. **C 級**：憲法修正只有維護者核可（Governance）。若他說「措辭修正不用我看」，改 B 級由 developer-agent 自合，內容不變。

## 裁決（2026-10-25，developer-agent）
1. 改憲法＝C 級：照 repo Governance 由他 merge；我開 PR、不掛自動合併，列進每日清單「請看成品」。只改文字（6.0.2 PATCH），不改任何原則。

## 專長守則（docs）

（工作區沒有 `.claude/dev-profiles/docs.md`；本任務無專長守則。）
