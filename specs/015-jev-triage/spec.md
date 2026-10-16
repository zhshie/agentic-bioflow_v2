# Feature Specification: 分析失敗時，Jev 先幫忙指出是哪一類錯（選配）

**Feature Branch**: `feat/015-jev-triage`

**Created**: 2026-10-16

**Status**: Draft

**Input**: 2026-10-16 維護者看完謝馬爾端的建議書（工作區 `memory/reference/jev-for-abf-suggestions.md`）與使用者操作流程評估，選定「只做除錯」：「只要有價值就設計，若有風險未來考慮變成本地端」「使用者自備」「一致率 ≥ 90%」「只做除錯」「題庫我核可了」。

> 名詞見 `CONTEXT.md`。Jev＝TypeSafe System One，雲端 API，只回機率／N 選 1／分數〔docs.typesafe.ai/api〕。

## 給維護者

1. 分析失敗、而且不是「網路被擋」也不是「記憶體不足（137）」時，現在 AI 要從頭讀那個 task 的整份錯誤訊息自己猜原因。這個功能在那一步之前，先把錯誤訊息最後 200 行交給 Jev，從 8 類裡挑一類；有把握就直接帶到那一類的修法，沒把握就照舊。
2. 預設關。使用者要自己有 TypeSafe 金鑰、自己打開，第一次會被告知「會送出什麼」。關著的時候，一切跟今天一模一樣。
3. Jev 掛掉或沒回應，會明講一句「Jev 未回應，改用原流程」，不會默默跳過。
4. 上線條件：用你核可的 42 題（其中 37 題會真的走到 Jev）測，答對率 ≥ 90% 才在文件寫「建議開啟」。

## 為什麼是這一塊

`skills/runs/SKILL.md` 的 FAILED 段落：先問站台拒絕了什麼（egress），再看 exit 137（記憶體），兩者都不是時落到「Anything else」，由 AI 讀 `.command.err` 自由判斷，沒有長度限制。這是使用者在除錯時等最久、AI 讀最多字的地方。其他候選點（錯誤回報分類、逐樣本 QC、預選、監看）2026-10-16 評估後不做：監看已由 `scripts/task_health.sh` 以規則回一行結論，其餘價值較低。

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 失敗原因被直接指出來（Priority: P1）

**Acceptance Scenarios**:

1. **Given** 使用者已打開 Jev 並設好金鑰，一個 run 失敗、站台沒有拒絕任何連線、task exit code 不是 137，**When** 走 `/runs` 的 FAILED 流程，**Then** 在讀 `.command.err` 之前先呼叫 `scripts/jev.sh triage`，並在回報裡多一行「Jev 判斷：<類別>（信心 <0.xx>）」。（正常）
2. **Given** 同上，Jev 回的信心 ≥ 門檻、類別不是「未知」，**When** 繼續，**Then** AI 直接走那一類的修復說明，只讀 `.command.err` 的最後 200 行，不再整份讀。（正常）
3. **Given** 同上，信心 < 門檻或類別是「未知」，**When** 繼續，**Then** 照今天的「Anything else」流程，回報裡註明「Jev 沒把握，照原流程」。（正常）
4. **Given** Jev 給的類別需要改管線參數或放寬網路邊界才修得好，**When** 繼續，**Then** 跟今天一樣停下來問使用者；Jev 的判斷不讓任何需要使用者同意的事變成自動。（例外）
5. **Given** 站台有拒絕紀錄對得上失敗時間，或 exit code 是 137，或根本沒有 `.command.log`／`.exitcode`，**When** 走 FAILED 流程，**Then** 不呼叫 Jev，照既有規則走。（例外）

### User Story 2 — 沒開、沒金鑰、或 Jev 掛了，都不影響（Priority: P1）

**Acceptance Scenarios**:

1. **Given** 設定 `jev.enabled` 未設或為 `false`，**When** 走 FAILED 流程，**Then** `scripts/jev.sh triage` 不送任何網路請求、exit 0，只在標準輸出印一行機器行 `JEV status=disabled ...` 給技能解析；技能文字不把這行展示給使用者，所以使用者看到的 FAILED 回報與沒有這個功能時逐字相同（逐字相同指使用者看到的，不是腳本標準輸出）。（正常）
2. **Given** `jev.enabled=true` 但沒有金鑰，**When** 呼叫，**Then** 印一行「Jev 已開啟但找不到金鑰，改用原流程」，不送請求，流程照舊。（例外）
3. **Given** Jev 逾時（> 10 秒）、回 4xx／5xx、或回傳格式不對，**When** 呼叫，**Then** 429／529 依官方建議退避重試最多 2 次；仍失敗就印「Jev 未回應，改用原流程（原因：<…>）」，流程照舊。（例外）
4. **Given** 主機上缺 `curl` 或 `jq`，**When** 呼叫，**Then** 同樣印出放行訊息並說缺哪一個，不當掉。（例外）
5. **Given** 當天呼叫次數已達上限（預設 500，可設定），**When** 再呼叫，**Then** 不送請求，印「今天的 Jev 次數已用完，改用原流程」。（例外）

### User Story 3 — 使用者知道送了什麼，金鑰不外洩（Priority: P1）

**Acceptance Scenarios**:

1. **Given** 使用者第一次在這台機器上打開 Jev，**When** 第一次呼叫，**Then** 先印出：會送出 `.command.err` 最後 200 行與 exit code 到 `api.typesafe.ai`、內容可能含路徑與樣本名、TypeSafe 只對企業客戶提供不保留資料、如何關閉。（正常）
2. **Given** 金鑰放在環境變數或 settings 目錄，**When** 任何指令執行，**Then** 金鑰不出現在 params、log、trace、report、終端輸出或 repo 檔案裡（沿用 `tests/credentials_stay_in_settings_test.sh` 的做法並擴充）。（例外）
3. **Given** `docs/SETTINGS.md`，**When** 使用者查 Jev，**Then** 看得到：開關名稱、金鑰放哪、送出哪些欄位、每日上限、`JEV_ENDPOINT`（將來可改指本地相容服務）。（正常）

### User Story 4 — 用核可題庫量準度（Priority: P1）

**Acceptance Scenarios**:

1. **Given** `specs/015-jev-triage/labels.json`（42 題，維護者 2026-10-16 核可），**When** 用 `JEV_DRY_RUN` 跑測試，**Then** 不打網路，每題都能走完 `jev.sh triage` 並產出類別與信心（fixture 回應）。（正常）
2. **Given** 有真金鑰，**When** 維護者手動跑驗收腳本，**Then** 只對「會走到 Jev」的題目（排除 exit 137 與站台拒絕的 5 題：T01、T03、T05、T14、T43，共 37 題）計分，產出 `specs/015-jev-triage/replay-report.md`：答對率、各類答對率、信心門檻建議、總 token 與延遲；另驗證那 5 題確實不會呼叫 Jev。（正常，手動）
3. **Given** 答對率 < 90%，**When** 寫報告，**Then** 文件不寫「建議開啟」，報告列出答錯的題號。（例外）

### Edge Cases

- `.command.err` 是空的、只有一行、或超過 200 行：送最後 200 行；空的就不呼叫 Jev，類別直接記「未知」走原流程。
- `.command.err` 含非 UTF-8 位元組：轉成合法 UTF-8 再送（官方要求 UTF-8 JSON）。
- 同一個 run 多個 task 失敗：只對 `tw runs view tasks` 找到的第一個失敗 task 呼叫一次。
- 兩台機器同時用：每日上限各算各的（計數在本機，不進 repo）。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `skills/runs/SKILL.md` FAILED 段落的「No refusal lines up」分支中，在「137」與「no .command.log」兩條規則之後、「Anything else」之前，加入呼叫 `scripts/jev.sh triage --err <file> --exit <code>` 的步驟；其他分支不變。`skills/operational/SKILL.md` 的檢查順序同步。
- **FR-002**: 類別固定 8 個：`memory`、`walltime`、`network`、`container`、`input`、`params`、`tool_bug`、`unknown`；每類在 `skills/runs/SKILL.md` 都有一段對應的處理說明（至少寫出：先看什麼、常見修法、何時要問使用者）。
- **FR-003**: `scripts/jev.sh` 是唯一呼叫 Jev 的地方；輸出一行機器可讀結果（類別、信心、狀態 `ok|disabled|no_key|failed|capped`）＋給人看的一行說明。
- **FR-004**: 預設關。開關、金鑰、上限的讀法比照 `scripts/settings.sh` 既有的 token 模式（環境變數優先，其次 settings 目錄檔案）。
- **FR-005**: 失敗一律放行並說出來（憲章 VI-13）；不退回其他 LLM。
- **FR-006**: `JEV_DRY_RUN=<目錄>` 時讀 fixture 回應、不打網路；CI 一律用它。
- **FR-007**: `JEV_ENDPOINT` 可覆寫網址（預設 `https://api.typesafe.ai/v1/systemone`），`model` 用 `jev-latest`。
- **FR-008**: 新增 ADR `docs/adr/0007-*`，記錄推翻 `docs/POSITIONING.md` 原本「❌ Jev」的理由（引用維護者 10-16 原話與官方網址），並把 POSITIONING 那一行改為「選配、預設關、自備金鑰、外送已揭露」。
- **FR-009**: `scripts/jev.sh` 檔頭照憲章 I-1 寫明為何不用現成工具（`tests/scripts_name_their_alternative.sh` 要綠）。
- **FR-010**: 每日上限計數不得成為 run 狀態的第二份副本（`tests/no_second_run_state_test.sh` 要綠），位置寫進 `docs/SETTINGS.md`。
- **FR-011**: `docs/TESTING.md` 人工實測段加入：開／關 Jev 各跑一次失敗 run 的步驟。`.claude-plugin/plugin.json` 不升版（v3 維持 `3.0.0-dev`），改在 `CHANGELOG.md` 的 3.0.0-dev 節下加一行。
- **FR-012**: `jev.min_confidence`（預設 0.80）是「有把握」的門檻：信心低於它、或類別為 `unknown`，走原本的「Anything else」流程；等於門檻算有把握。

### Key Entities

- **分診結果**：類別、信心（0–1）、狀態、送出字數；只印出，不存檔。
- **題庫**：`labels.json` 每題 id、exit code、錯誤訊息尾段、正確類別、來源、是否難題、理由。

## Success Criteria *(mandatory)*

- **SC-001**: 37 題可計分題目，Jev 答對率 ≥ 90%（未達則不建議開啟）。
- **SC-002**: 高信心時，AI 讀進的錯誤訊息字數 ≤ 原本的 200 行上限（報告列前後對比）。
- **SC-003**: 關閉狀態下，FAILED 流程輸出與 main 逐字相同（golden 測試）。
- **SC-004**: WSL 全套測試與 CI 全綠；fixture 涵蓋：高信心、低信心、未知、500、逾時、429 重試後成功、缺 jq、無金鑰、達上限。

## Assumptions

- 題庫 42 題中 39 題為合成、3 題取材 PITFALLS；真實國網樣本之後補（維護者 10-16 同意先開工）。
- 官方未公布價格、速率上限、逾時；10 秒逾時與每日 500 次是我們訂的預設，可改。
- 使用者主機已有 `curl`；`jq` 在 `setup_proof.sh` 已是前置需求。

## Out of Scope

- 錯誤回報分類、逐樣本 QC、管線／欄位預選、監看、hooks 白話檢查、verifier 閱卷前篩。
- 本地模型版本（只留 `JEV_ENDPOINT` 介面）。
- 自動修復：Jev 只指路，修法與需要同意的步驟不變。
