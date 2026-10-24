# 測試案例：重用已登記的 launchpad 管線時，核對它綁的計算環境（issue #8）

**規格**：`specs/launchpad-ce-routing/plan.md`（本任務為 A 級，以計畫＋維護者在 issue #8 的原話為規格；沒有獨立的 `spec.md`）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：查不出、沒設定、沒有 tw 等情況下，系統怎麼反應（警告、不亂說）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

## 名詞（先讀這段）

- **CE（計算環境）**：Seqera 平台上「這個 run 要送去哪裡跑」的設定。同一個工作區裡可以同時有正式環境（例：`nchc-taiwania3`）和新建的隔離環境（例：`agentic-bioflow-v2test`）。
- **登記項目（launchpad 項目）**：用 `tw pipelines add` 登記過的管線，之後可用短名（例：`nf-core-rnaseq-3140`）直接 launch。每個項目綁一個 CE。
- **期望的 CE**：這個部署設定檔裡的 `compute_env`（環境變數 `SEQERA_COMPUTE_ENV` 優先）。
- **摘要**：`scripts/prepare_launch.sh` 印出的那份分段報告，含 `== pipeline ==` 與最後的 `== decisions ==`。`DECIDE:` 是「請使用者決定」，`WARNING:` 是「要注意」，`BLOCKING:` 是「擋住」。

## 共同準備（除非該列另有寫）

- 全部用**假的 `tw`**（測試自己寫的小程式，依參數回罐頭輸出），不碰 Seqera、不需要網路。依 `tests/prepare_launch_test.sh` 的搭法：把真的 `prepare_launch.sh`、`settings.sh`、`utils/*` 複製到暫存 `scripts/`、假的 `preflight.sh`、`--fixture-dir`。
- 設定檔：`workspace_id: ws1`、`compute_env: agentic-bioflow-v2test`；`TOWER_ACCESS_TOKEN` 設成一個看得出來的值；`SEQERA_COMPUTE_ENV` 未設。
- 執行：`--repo nf-core/rnaseq --revision 3.14.0`。
- 假 `tw` 的文字版 `pipelines list` 回含 `nf-core-rnaseq-3140`、`https://github.com/nf-core/rnaseq`、`3.14.0` 的內容（讓既有判斷得出「已登記」）。
- 假 `tw` 的 `-o json pipelines list` 回 `{"pipelines":[{"name":"nf-core-rnaseq-3140","repository":"https://github.com/nf-core/rnaseq","revision":"3.14.0","launch":{"revision":"3.14.0"},"computeEnv":{"name":"<該列指定>"}}]}`。「revision 欄位」指頂層 `revision` 與 `launch.revision` 兩處（兩處放同一個值；說「沒有 revision 欄位」的列兩處都拿掉）。
- 假 `tw` 把每次被呼叫的完整參數記到一個檔，供檢查。

## User Story 1 — 已登記的項目綁在哪個 CE 要看得見，不符就要使用者決定（優先度 P1）

維護者原話（issue #8）：「show (or check) which compute environment it's bound to, and flag it if it doesn't match the CE this session is currently configured for」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫 T1；原話「show which CE it's bound to」 | 功能 | 登記項目綁 `nchc-taiwania3`；設定 compute_env 為 `agentic-bioflow-v2test` | 跑摘要 | `== pipeline ==` 內有一行以 `bound to:` 開頭，且含 `nchc-taiwania3` | 自動：`tests/prepare_launch_ce_test.sh` |
| TC-002 | 計畫 T1；原話「flag it if it doesn't match」 | 功能 | 同 TC-001 | 跑摘要 | `== decisions ==` 內至少有一條 `DECIDE:`，同一行同時出現 `nchc-taiwania3`、`agentic-bioflow-v2test`、`--compute-env`，並含「do NOT launch it by short name」的意思（不要用短名直接 launch） | 自動 |
| TC-003 | 計畫作法 3「`REGISTERED` 原字串不改」；T1 | 功能 | 同 TC-001 | 跑摘要 | `registered:` 那行仍含 `yes, at 3.14.0` | 自動 |
| TC-004 | 計畫裁決一「不符用 DECIDE 不用 BLOCKING」 | 功能 | 同 TC-001 | 跑摘要 | 摘要裡沒有任何一行 `BLOCKING:` 是關於「登記項目綁的 CE」（含 `bound to`） | 自動 |
| TC-005 | 計畫作法 3「置於 `registered:` 之後」 | 功能 | 同 TC-001 | 跑摘要 | `bound to:` 那行緊接在 `registered:` 那行之後，且都在 `== pipeline ==` 段內 | 自動 |
| TC-006 | 計畫 T2；對照組 | 功能 | 登記項目綁 `agentic-bioflow-v2test`（與設定相同） | 跑摘要 | 有 `bound to: agentic-bioflow-v2test` 那行，並含 `matches this deployment's compute_env` | 自動 |
| TC-007 | 計畫 T2「不吵」 | 功能 | 同 TC-006 | 跑摘要 | 含 `bound to` 字樣的 `DECIDE:` 行數為 0、含 `bound to` 字樣的 `WARNING:` 行數為 0 | 自動 |
| TC-008 | 計畫 T4（view 備援） | 功能 | JSON 項目沒有 `computeEnv`、也沒有 `launch.computeEnv`；`tw -o json pipelines view -n nf-core-rnaseq-3140` 回 `{"pipeline":{"launch":{"computeEnv":{"name":"nchc-taiwania3"}}}}` | 跑摘要 | 與 TC-001、TC-002 相同的結果（有 `bound to: nchc-taiwania3`，且有同時提到兩個 CE 與 `--compute-env` 的 `DECIDE:`） | 自動 |
| TC-009 | 計畫作法 1（view 備援也要能判「相符」） | 功能 | 同 TC-008，但 view 回的 CE 是 `agentic-bioflow-v2test` | 跑摘要 | `bound to:` 行含 `matches this deployment's compute_env`；含 `bound to` 的 `DECIDE:`／`WARNING:` 為 0 | 自動 |
| TC-010 | 計畫作法 1「沒有 `computeEnv.name` 就取 `launch.computeEnv.name`」 | 功能 | JSON 項目只有 `launch.computeEnv.name = nchc-taiwania3`（沒有頂層 `computeEnv`） | 跑摘要 | 與 TC-001、TC-002 相同的結果，且不需要呼叫 `pipelines view` | 自動 |
| TC-011 | 計畫作法 1「`view` 結果從 `pipeline.` 底下同兩個位置取」 | 功能 | JSON 項目沒有 CE；view 回 `{"pipeline":{"computeEnv":{"name":"nchc-taiwania3"}}}` | 跑摘要 | 與 TC-001、TC-002 相同的結果 | 自動 |
| TC-012 | 計畫作法 2「`SEQERA_COMPUTE_ENV` 優先，同 `preflight.sh`」 | 功能 | 設定檔 compute_env 為 `agentic-bioflow-v2test`；環境變數 `SEQERA_COMPUTE_ENV=nchc-taiwania3`；登記項目綁 `nchc-taiwania3` | 跑摘要 | 視為相符：`bound to:` 行含 `matches this deployment's compute_env`；含 `bound to` 的 `DECIDE:`／`WARNING:` 為 0 | 自動 |

## User Story 2 — 同一管線有多個登記項目時（優先度 P1）

依計畫「裁決三 5」：先看 repository 符合、且 revision 等於這次要用的項目；沒有 revision 欄位時，寧可多問，不靜默。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 計畫作法 1「挑 `repository` 含 `$REPO` 的項目」 | 功能 | JSON 有兩個項目：`nf-core/rnaseq` 綁 `agentic-bioflow-v2test`；`nf-core/ampliseq` 綁 `nchc-taiwania3` | 跑摘要（`--repo nf-core/rnaseq`） | 視為相符；`bound to:` 行不含 `nchc-taiwania3`；含 `bound to` 的 `DECIDE:`／`WARNING:` 為 0 | 自動 |
| TC-014 | 裁決三 5「要用的版本綁錯 → DECIDE」 | 功能 | 同管線兩個項目：`3.14.0` 綁 `nchc-taiwania3`、`3.10.0` 綁 `agentic-bioflow-v2test`；兩者都有 revision 欄位 | 跑摘要（`--revision 3.14.0`） | 有 `DECIDE:` 同時提到 `nchc-taiwania3`、`agentic-bioflow-v2test`、`--compute-env`；不可因為舊版綁對就判相符 | 自動 |
| TC-015 | 裁決三 5「要用的版本綁對、舊版綁錯 → 相符（有 revision 欄位時）」 | 功能 | 同管線兩個項目：`3.14.0` 綁 `agentic-bioflow-v2test`、`3.10.0` 綁 `nchc-taiwania3`；兩者都有 revision 欄位 | 跑摘要（`--revision 3.14.0`） | 視為相符：`bound to:` 行含 `matches this deployment's compute_env`；含 `bound to` 的 `DECIDE:`／`WARNING:` 為 0 | 自動 |
| TC-016 | 裁決三 5「沒有 revision 欄位時，任一同 repo 項目不符就列出並出 DECIDE」 | 例外 | 同 TC-015 的資料，但兩個項目都拿掉 revision 欄位 | 跑摘要（`--revision 3.14.0`） | 有 `DECIDE:` 提到 `nchc-taiwania3`、`agentic-bioflow-v2test`、`--compute-env`；`bound to:` 行不得宣稱 `matches` | 自動 |
| TC-017 | 裁決三 8「`view` 備援最多呼叫 5 次」 | 例外 | JSON 有 7 個同 repo 項目，都沒有 CE 欄位；假 `tw` 的 `pipelines view` 一律失敗 | 跑摘要，之後讀假 `tw` 的呼叫記錄 | `pipelines view` 被呼叫的次數不超過 5；摘要有 `bound to: unknown` | 自動 |

## User Story 3 — 查不出或沒設定時，不裝作沒事（優先度 P1）

這條守「Nothing Goes Quiet」（憲法第 13 條精神）：說不出綁在哪，就明講並當作不相符。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-018 | 計畫 T3；作法 3「查不出」 | 例外 | JSON 項目沒有任何 CE 欄位，且 `pipelines view` 也失敗 | 跑摘要 | 有 `bound to: unknown` 那行；該行與整份摘要都不宣稱 `matches this deployment's compute_env` | 自動 |
| TC-019 | 計畫 T3「恰 1 條」 | 例外 | 同 TC-018 | 跑摘要 | 含 `bound to` 字樣的 `WARNING:` 恰好 1 條，意思是「查不出綁哪個 CE，在查清楚前當作不相符」（`treat it as NOT matching until checked`） | 自動 |
| TC-020 | 計畫作法 3「JSON 讀不懂」 | 例外 | 假 `tw -o json pipelines list` 回一段不是 JSON 的文字 | 跑摘要 | `bound to: unknown`；恰 1 條含 `bound to` 的 `WARNING:`；摘要沒有 `Traceback` 或其他程式錯誤堆疊；`registered:` 行仍與今天一樣是 `yes, at 3.14.0` | 自動 |
| TC-021 | 計畫作法 3「期望的 CE 沒設定」 | 例外 | 設定檔沒有 `compute_env`（且 `SEQERA_COMPUTE_ENV` 未設）；登記項目綁 `nchc-taiwania3` | 跑摘要 | `bound to:` 行含 `nchc-taiwania3` 與 `no compute_env in the deployment settings, nothing to compare` | 自動 |
| TC-022 | 裁決三 7 的固定措辭 | 例外 | 同 TC-021 | 跑摘要 | `== decisions ==` 內有這一整行：`WARNING: no compute_env is configured, so the bound compute environment cannot be checked.` | 自動 |

## User Story 4 — 沒變的行為，以及 tw 的呼叫方式（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 計畫作法 1「文字版 list 行為不變，只在登記為 yes 之後才多問」 | 功能 | 文字版 `pipelines list` 沒有這個 repo／版本（例：只有別的管線） | 跑摘要 | `registered:` 行是 `no - ...tw pipelines add...`；仍有原本的 `DECIDE: register the pipeline before launch`；沒有含 `bound to` 的 `DECIDE:`／`WARNING:` | 自動 |
| TC-024 | 計畫 T6（回歸） | 例外 | `TW_BIN=/does/not/exist` | 跑摘要 | `registered: unknown ...`；含 `could not check whether the pipeline is already registered` 的 `WARNING:` 恰 1 條；沒有任何含 `bound to` 的 `WARNING:`（沒有 tw 就沒得比） | 自動 |
| TC-025 | 計畫「環境事實」tw 呼叫慣例；作法 1 | 功能 | 登記項目有 CE 欄位；另設一個沒 CE 欄位的情境以觸發 view | 跑摘要，讀假 `tw` 的呼叫記錄 | 讀 CE 的呼叫帶 `-o json pipelines list` 與 `--workspace ws1`；`pipelines view` 呼叫帶 `-n <項目名>` 與 `--workspace ws1`（不帶 workspace 會悄悄查到個人空間） | 自動 |
| TC-026 | 計畫「不做」：不自動改寫、重新登記或刪除使用者的項目；不替使用者選 CE | 不在範圍 | 任一不符情境（例：TC-001） | 跑摘要，讀假 `tw` 的呼叫記錄 | 被呼叫的 `tw` 子命令只有 `pipelines list` 與 `pipelines view`；沒有 `pipelines add`／`update`／`delete`／`launch` | 自動 |
| TC-027 | 專長守則（密鑰不得出現在回應；錯誤訊息說明原因與處理方式、不露堆疊） | 例外 | 使用一個看得出來的 token 值，跑 TC-001、TC-018、TC-020 三個情境 | 跑摘要，並看假 `tw` 的呼叫記錄 | 摘要與呼叫記錄的參數裡都沒有出現 token 值；WARNING／DECIDE 的句子寫明發生什麼事與下一步（例：用 `--compute-env` 重新登記或改用 GitHub URL），不含 `Traceback` 或內部檔案路徑 | 自動 |

## User Story 5 — skill 文字不再叫人「已登記就跳過」（優先度 P2）

維護者原話：「`launch.md` step 1 says to prefer an existing registered entry ('re-running the same pipeline at the same revision needs nothing here — skip the step'), which is right for revision-pinning but says nothing about compute-environment binding.」「launched via the full GitHub URL + explicit `--revision` + explicit `--compute-env`」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-028 | 計畫 T5（步驟 3） | 功能 | 檔案 `skills/launch/SKILL.md` | 取「Register it…」那一步（步驟 3）的文字 | 該段含 `bound to` | 自動 |
| TC-029 | 計畫 T5（步驟 7）；原話「explicit --compute-env」 | 功能 | 同上 | 取步驟 7（launch 指令說明）的文字 | 該段含 `--compute-env "$(scripts/settings.sh compute_env)"` | 自動 |
| TC-030 | 計畫作法 4「只有 registered: yes 且 bound to 為 matches 時才跳過登記；否則照 decisions 處理」 | 功能 | 同上 | 閱卷者讀步驟 3 全段 | 白話看得懂：只有「已登記」加「綁定相符」兩者都成立才可跳過登記；不相符或查不出時不可跳過，要照摘要的 decisions 處理；舊句「同版本就跳過」沒有剩下無條件的版本 | 手動：閱卷者讀檔，記錄寫在 `specs/launchpad-ce-routing/ledger.md` |
| TC-031 | 計畫作法 4「不靠登記項目預設的 CE」 | 功能 | 同上 | 閱卷者讀步驟 7 | 明確寫出 launch 一律帶 `--compute-env`，不靠登記項目預設的 CE | 手動：同上 |

## User Story 6 — 用真實 tw 輸出核對欄位位置（優先度 P2）

計畫「環境事實」：沒有可核對的真實 `tw -o json pipelines list/view` 輸出樣本，作法對欄位位置是「兩處都試」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-032 | 計畫裁決二 3、裁決三 6（手動驗收用真的 tw 0.40 核對，結果記進 ledger） | 功能 | 有人能在登入的環境跑真的 `tw` 0.40 並貼出 `tw -o json pipelines list` 與 `pipelines view` 的輸出 | 把真實輸出餵給 `prepare_launch.sh`，看 `bound to:` 行 | 對一個已知綁定的項目，`bound to:` 顯示它真正綁的 CE 名，而不是 `unknown`；欄位實際位置記進 ledger。**本條判 UNVERIFIED 時不擋合併**（裁決三 6） | 手動：`specs/launchpad-ce-routing/ledger.md` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-033 | 第 8 條（PITFALLS 每條對應真實失敗；計畫作法 5） | 功能 | 檔案 `docs/PITFALLS.md` | 看這次的 diff | 只在檔尾新增一條；標題含 `2026-10-24` 與 `issue #8`（或 `#8`）；內容有症狀、原因、修法；既有條目一字未動 | 手動：`docs/TESTING.md` 的 P2 |
| TC-034 | 安全網（`hooks/` 不動；計畫完成標準） | 不在範圍 | 分支與 base `origin/v3` | `git diff --stat origin/v3 -- hooks` | 輸出為空 | 手動：閱卷者執行並貼輸出 |
| TC-035 | 安全網（閘門在 base 與分支行為相同；repo 校準失敗案例 1、2） | 不在範圍 | 同上 | 在 base 與分支各跑一次 `bash tests/confirm_launch_test.sh` | 兩邊輸出相同 | 手動：閱卷者執行並比對 |
| TC-036 | 全套測試（計畫完成標準） | 功能 | WSL 或 Linux，本機磁碟 | 跑 `tests/run_all.sh` | 全綠，其中包含新的 `tests/prepare_launch_ce_test.sh`、既有 `tests/prepare_launch_test.sh`、`tests/skills_name_the_v3_launch_path.sh` | 自動：`tests/run_all.sh` |
| TC-037 | 計畫「會改斷言的既有測試：無」 | 功能 | 同上 | 比對這次 diff 中所有動到的 `tests/` 檔 | 只有新增 `tests/prepare_launch_ce_test.sh`；既有測試檔沒有被刪斷言、放寬、跳過或改期望值 | 手動：閱卷者比對 diff |
| TC-038 | 計畫「範圍：檔案」與「不准動」清單；「不做」：不改 `platform/**`、`preflight.sh`、不新增設定鍵、不同步 main | 不在範圍 | 同上 | `git diff --name-only origin/v3...HEAD` | 檔案只在範圍清單內（`scripts/prepare_launch.sh`、`skills/launch/SKILL.md`、`tests/prepare_launch_ce_test.sh`、`docs/PITFALLS.md`、`specs/launchpad-ce-routing/ledger.md`，外加規劃階段已提交的 `specs/launchpad-ce-routing/` 檔）；不准動清單零命中（`platform/**`、`deploy/`、`configs/sites/*`、`scripts/nf_relay.py`、`scripts/egress_ctl.sh`、`scripts/on_site.sh`、`scripts/build_package.sh`、`docs/OPERATIONS.md`、`docs/INSTALL.md`、`docs/SETTINGS.md`、`docs/SITE_ADAPTER.md`、`docs/TESTING.md`、`scripts/preflight.sh`） | 手動：閱卷者執行並貼輸出 |
| TC-039 | 計畫完成標準「沒有任何真的 tw／Seqera 呼叫，沒網路也綠」 | 功能 | 新測試檔 | 閱卷者讀 `tests/prepare_launch_ce_test.sh` 的 `TW_BIN` 設定與執行輸出 | 每個情境的 `TW_BIN` 都指向假 `tw` 或不存在的路徑；沒有任何地方呼叫 PATH 上的真 `tw`、curl 或連網 | 手動：閱卷者讀檔 |
| TC-040 | repo CLAUDE.md「Never edit during implementation」 | 不在範圍 | 同上 | 看 diff | `spec.md`、`test-case*.md`、憲法、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json` 沒有任何改動 | 手動：閱卷者執行並貼輸出 |
| TC-041 | 計畫「失敗先行測試」 | 功能 | 實作前 | 執行者在動 `scripts/prepare_launch.sh` 與 skill 前先跑新測試 | `ledger.md` 貼有紅的輸出：TC-001 至 TC-005、TC-008、TC-028、TC-029 等在舊程式下失敗；TC-024 在舊程式下就是綠（鎖住不退步） | 手動：閱卷者讀 `specs/launchpad-ce-routing/ledger.md` |

<!--
Rules for the writer:
- 驗證方式 is 自動 or 手動 only. Manual steps for this task live in specs/launchpad-ce-routing/ledger.md, because docs/TESTING.md is on the plan's do-not-touch list.
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
