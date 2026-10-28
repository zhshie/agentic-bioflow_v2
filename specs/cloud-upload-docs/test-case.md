# 測試案例：雲端上傳與費用的文件更新（cloud-upload-docs）

**規格**：`specs/cloud-upload-docs/plan.md`（本任務沒有獨立 spec.md；需求取自 plan 的「作法」1–5、失敗先行測試 T1–T10、「不做」、「裁決三」）　**總覽**：`test-case-overview.md`

類型只有三種：功能／例外／不在範圍。驗證方式「手動」＝閱卷者（verifier）依本表逐條讀文件或跑 `git diff` 核對，不是請維護者操作。

維護者原話（plan「維護者原話」）：
1. 「雲端上傳＝平台代傳到使用者自己的 bucket、不落地（ADR 0010 規則），大檔給 `gsutil` 指令」→ TC-002、TC-003、TC-008。plan 裁決已定指令一律寫 `gcloud storage cp`，PR 說明提一句。
2. 「使用者用自己的 AI 走 MCP，不用 AI 的人走網頁」→ TC-005。

說明：plan 的 T3 原本斷言 "not built yet"，裁決三改為「平台與站台代理已能把一個檔案寫進使用者自己的前綴，但網頁與 AI 都還沒有入口」。TC-007 以裁決三為準。

## User Story 1 — 管理者讀 OPERATIONS 就知道雲端輸入檔怎麼放、怎麼登記（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 2；T2、T5 | 功能 | 改完的 `docs/OPERATIONS.md` | 找 `### Datasets in the lab's bucket` 標題，並數整份文件的 `## ` 標題 | 有這個 `###` 小節，位在「Google Batch on the platform host」之後；`## ` 標題仍恰好 6 個 | 自動：`platform/tests/test_cloud_upload_docs.py` |
| TC-002 | 作法 2①、5；維護者原話 1 | 功能 | 同上 | 讀新小節第一點 | 寫明檔案放 `gs://<bucket>/uploads/<user>/`（每人自己的位置）；寫明 bucket 就是該環境 `workDir` 的 bucket；"prefix" 第一次出現時用白話解釋成「`gs://<bucket>/` 後面像資料夾的那一段」 | 手動：閱卷者讀 `docs/OPERATIONS.md` 該小節，對照 `cloud_store.py` 前綴規則 |
| TC-003 | 作法 2②；維護者原話 1；T2 | 功能 | 同上 | 讀新小節第二點 | 有 `gcloud storage cp <folder>/* gs://<bucket>/uploads/<user>/rawdata/` 這行指令；寫明單檔超過 2 GB 時平台也只給這行指令 | 自動：`test_cloud_upload_docs.py`（`gcloud storage cp`、`rawdata/`、`2 GB`） |
| TC-004 | 作法 2③；T2、T8 | 功能 | 同上；`abf-platform dataset` 指令群已存在於 `cli.py` | 讀新小節第三點 | 有 `abf-platform dataset register --name … --version … --samplesheet … --file gs://… --user <name> --destination <env>`；文件中每個 `abf-platform dataset <字>` 的 `<字>` 只能是 register／list／show；`--user`、`--destination` 在 `cli.py` 的 `dataset` 群真的存在 | 自動：`test_cloud_upload_docs.py`（T2＋T8，讀 `cli.py` 文字） |
| TC-005 | 作法 2④；維護者原話 2；T4 | 功能 | 同上 | 讀新小節第四點，並看小節內所有反引號詞 | 寫的是 AI 用 `launch` 的 `dataset` 參數；小節內沒有不存在的 MCP 工具名，`register_dataset` 不被當成工具列出 | 自動：`test_cloud_upload_docs.py`（T4） |
| TC-006 | 作法 2⑤；T3 | 功能 | 同上 | 讀新小節第五點 | 明寫平台 "does not grant"（不授予，也不檢查）寫入 bucket 的權限，要由 Google Cloud 專案擁有者在 Google 那邊給 | 自動：`test_cloud_upload_docs.py`（T3 的 "does not grant"） |
| TC-007 | 作法 2⑥；裁決三 1；T3 | 功能 | 同上 | 讀新小節第六點 | 寫的是現況：平台與站台代理已能把一個檔案寫進使用者自己的前綴，但網頁與 AI 都還沒有入口，所以今天請自己用 `gcloud storage cp` 放進前綴；不再寫成「之後的功能」或「byte-channel 尚未合併」。測試斷言的字樣由執行者決定，閱卷者核對它確實承載這個意思 | 自動：`test_cloud_upload_docs.py`（T3 第二句） |
| TC-008 | 維護者原話 1；裁決 2 | 功能 | 三份文件改完 | 在三份文件的新增／改寫文字中找指令 | 上傳指令一律是 `gcloud storage cp`，沒有寫 `gsutil`；PR 說明提一句原話寫 `gsutil`、依裁決改用 `gcloud storage cp` | 手動：閱卷者 `git diff origin/v3...HEAD` 搜 `gsutil`，並讀 PR 說明 |

## User Story 2 — 三處過期句子改成現況（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 作法 1；T1 | 功能 | 改完的 `docs/OPERATIONS.md` | 搜 "no cost estimate or cap yet" 與 `docs/CLOUD.md` | 舊句 "the platform has no cost estimate or cap yet." 消失；全文含 `docs/CLOUD.md` | 自動：`test_cloud_upload_docs.py`（T1） |
| TC-011 | 作法 1；裁決三 4 | 功能 | 同上 | 讀 Google Batch 小節最後一句 | 新句說：送出前平台會查每人每月雲端上限，並給預估費用（或說明為什麼算不出來，因為價目表目前空的）；不會停掉已在跑的 run；指向 `docs/CLOUD.md` | 手動：閱卷者讀 `docs/OPERATIONS.md` 該句，對照 `actions/__init__.py` 的 `_cloud_check` |
| TC-012 | 作法 1；T5 | 功能 | 同上 | 搜 "Java 17"、"Nextflow"、"gcloud"、"storage_root" | 四個詞都還在（`test_gcb_launch.py` 要求前三者）；`## ` 標題恰 6 個 | 自動：`test_cloud_upload_docs.py`（T5）；`test_gcb_launch.py` 既有斷言 |
| TC-013 | 作法 3；T6 | 功能 | 改完的 `docs/PLATFORM.md` | 搜 "Copying files into the bucket is a later feature"；讀 "Input data" 段 | 舊句消失；該段含 `gcloud storage cp` 與 "Datasets in the lab's bucket" | 自動：`test_cloud_upload_docs.py`（T6） |
| TC-014 | 作法 3；裁決三 1 | 功能 | 同上 | 讀 "Input data" 段新句，並以 `git diff` 看該段其餘文字 | 新句寫現況：平台不把檔案複製進 bucket，要用 `gcloud storage cp` 放，之後可登記成 Dataset，並指向 OPERATIONS 新小節；與 TC-007 的意思一致（不說「之後的功能（C-6）」）；該段其餘文字（含「同一個 bucket 作為 `workDir`」「workDir 至少一層資料夾」）逐字未動 | 手動：閱卷者讀 `git diff origin/v3...HEAD -- docs/PLATFORM.md` |

## User Story 3 — TESTING 的雲端手動步驟改成真指令（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 作法 4；T7 | 功能 | 改完的 `docs/TESTING.md` | 讀 `## Datasets in a cloud bucket (cloud-upload)` 的編號步驟段 | 步驟段不再出現 "Python shell"，且含 `abf-platform dataset register` | 自動：`test_cloud_upload_docs.py`（T7；只查步驟段，不查說明段） |
| TC-021 | 作法 4 | 功能 | 同上 | 逐一讀步驟 1–4 | 步驟 1–3 的 `register_dataset(…)` 呼叫都改成 `abf-platform dataset register …`，每步仍有 "Check: …"；步驟 4（超過 2 GB）因沒有指令入口，改寫為「讀 `docs/OPERATIONS.md` 的指令是否與 `cloud_store.big_file_command` 一致」，並註明無入口；步驟 4 沒有留著 `check_web_upload(…)` 呼叫 | 手動：閱卷者讀 `git diff origin/v3...HEAD -- docs/TESTING.md` |
| TC-022 | 裁決三 3 | 功能 | 同上 | 讀該節開頭說明段（原 :615） | 不再說「要等 byte-channel 任務」；改為：端到端（真的把檔案送進 bucket）要等網頁／AI 入口；與 TC-007 一致 | 手動：閱卷者讀該段 |
| TC-023 | 作法 4 | 功能 | 同上 | 看 "The reviewer" 段與步驟 5 | 結尾 "The reviewer" 段與步驟 5 逐字未動；該節以外的 TESTING.md 內容未動 | 手動：閱卷者看 `git diff` 只落在該節 |

## User Story 4 — 守門測試與交付（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-037 | 範圍：檔案；完成標準 | 功能 | 新增 `platform/tests/test_cloud_upload_docs.py` | 讀檔首與測試數量 | 檔首有 `# Nothing existing: …` 且說明 ≥15 字；測試 ≤15 條；只讀 `REPO_ROOT/docs/…` 與 `cli.py`／`mcp_server.py` 文字，不連網、不需 Google 帳號；每條測試註明對應 T 或 TC 編號；T1–T9 都有對應斷言，且斷言不弱於 plan 表所列 | 手動：閱卷者讀測試檔 |
| TC-038 | 完成標準 | 功能 | PR 說明 | 讀 PR 說明 | 列出三處（OPERATIONS 費用句、PLATFORM Input data 句、TESTING 手動步驟）的「以前／以後」文字與理由，並提 `gsutil`→`gcloud storage cp` | 手動：閱卷者讀 PR 說明 |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 範圍「不准動」；「不做」；T10 | 不在範圍 | 完成後的分支 | `git diff --stat origin/v3...HEAD -- docs/CLOUD.md docs/INSTALL.md` 與 `git diff origin/v3...HEAD -- platform/abf_station/launch.py` | `docs/CLOUD.md`、`docs/INSTALL.md` 沒有差異；`launch.py` 的 `NO_BUCKET_PATH`（含 "C-6"）沒有差異；證據貼進 `specs/cloud-upload-docs/ledger.md` | 手動：閱卷者自己跑 diff，並核對 ledger 有貼 |
| TC-031 | 完成標準；裁決三 5 | 不在範圍 | 同上 | `git diff --name-only origin/v3...HEAD` | 只有 `docs/OPERATIONS.md`、`docs/PLATFORM.md`、`docs/TESTING.md`、`platform/tests/test_cloud_upload_docs.py`、`specs/cloud-upload-docs/ledger.md`（外加 plan／test-case 等本任務目錄下已提交的規格檔）；沒有任何程式碼檔被改 | 手動：閱卷者跑 `git diff --stat origin/v3...HEAD` |
| TC-032 | 作法 2⑤；T9 | 不在範圍 | 三份文件改完 | 掃三份文件 | 不含 `@…iam.gserviceaccount.com`（`lab-project-1` 例外）、不含 `abf_pat_` 後接 8 個以上英數字的字串、不含 `BEGIN PRIVATE KEY`；TESTING.md 既有的 "private_key" 搜尋提示保留 | 自動：`test_cloud_upload_docs.py`（T9） |
| TC-033 | 「不做」第 1 條；裁決 1 | 不在範圍 | 同上 | 讀新增文字 | 沒有寫 IAM 細節（角色名稱、前綴範圍的權限條件、如何在 Google 設權限）；只說平台不授予也不檢查，那是 Google Cloud 專案擁有者的事 | 手動：閱卷者讀新增段落 |
| TC-034 | 「不做」第 3 條 | 不在範圍 | 同上 | 讀 diff | 沒有動價目表或填入任何價格數字；費用句只說「預估，或說明為何算不出」 | 手動：閱卷者讀 diff，確認無金額 |
| TC-035 | 「不做」第 2、4 條 | 不在範圍 | 同上 | `git diff --name-status origin/v3...HEAD` | 沒有新增文件檔（除本任務目錄與新測試檔）；沒有資料表或 JSON 內容改動，沒有 migration | 手動：閱卷者跑 `git diff --name-status` |
| TC-036 | 「會改斷言的既有測試：無」 | 不在範圍 | 完成後的分支 | `git diff origin/v3...HEAD -- platform/tests tests`，並跑 `bash tests/operations_doc_test.sh`、`tests/install_doc_test.sh`、`tests/testing_web_doc_test.sh` 與 `test_gcb_launch.py`、`test_gcb_ce.py`、`test_actions_layer.py`、`test_cloud_cost.py` 內與文件相關的測試 | 既有測試檔沒有任何差異（只多一個新檔）；上述測試全綠，沒有被改弱、跳過或放寬 | 自動：`tests/operations_doc_test.sh`、`tests/install_doc_test.sh`、`tests/testing_web_doc_test.sh`、`platform/tests/test_gcb_launch.py:1146-1170`、`test_gcb_ce.py:854-880`、`test_actions_layer.py:600-606`、`test_cloud_cost.py:772-790` |

## 憲法與安全網

本任務只改文件，但新增的是「做不做得到」的事實陳述，觸及第 8 條（Evidence Before Claims：讀過原始碼才能宣稱）。不碰安全網的閘門。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 原則 IV 第 8 條（先讀來源再下結論） | 功能 | 三份文件改完 | 逐句對照新增文字與原始碼：前綴規則 `cloud_store.py:67-72`、單檔上限 `datasets.py:22`（2_000_000_000 位元組，十進位）、大檔指令 `cloud_store.py:92-95`、`cli.py` 的 `dataset` 群選項、費用上限 `actions/__init__.py` `_cloud_check`、byte-channel 現況（非測試碼是否有人呼叫 `enqueue_put_upload(`） | 每個事實都與程式一致；沒有文件說了程式做不到的事；若 byte-channel 已有網頁或 AI 入口，文件須照現況寫並回報 | 手動：閱卷者逐條對照，附 `path:line` |
| TC-041 | Development Workflow（完成記號） | 功能 | 完成後的分支 | 讀 `executor-status`，比對 HEAD | 內容為 `GREEN <HEAD sha>`，工作樹乾淨；WSL `bash tests/run_all.sh` 綠 | 自動：`tests/run_all.sh`（閘門記號） |
