# 測試案例：組合管線驗證的可選 nf-core lint（017c2a-validate-lint）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Write every row so that it can be
judged without reading code: what is set up, what the person or the system does,
what must be seen. No internal jargon without a one-line explanation.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/017c2a-validate-lint/plan.md`（本任務沒有獨立的 spec.md，計畫即規格；「作法 N」指計畫「## 作法」的第 N 條，「追加 N」指計畫「## 裁決」最後一段的第 N 點）　**總覽**：`test-case-overview.md`

維護者沒有針對 lint 說過逐字原話，所以沒有「他的話」可引；下列輸入與預期結果全部來自計畫已寫明的行為。

名詞：「代理」指站台代理（跑在叢集登入節點上、替平台做事的小程式）。「工作」指平台排給代理的一件事。「假的」指測試用的替身，不會真的跑 nf-core、不會連真站台。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

## User Story 1 — 使用者驗證已存的組合時，可以選擇請站台跑 lint（優先度 P1）

平台側。測試檔：`platform/tests/test_pipeline_lint.py`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；作法 1（預設不跑）；`test_lint_off_changes_nothing` | 功能 | 使用者有一個已存的組合版本；記下現在的 jobs 列數與驗證紀錄 | 呼叫驗證，不傳 `lint` | 回傳內容與寫入的資料跟現在（沒有這個功能時）完全一樣；jobs 沒有新增列；回傳沒有 `lint` 鍵；之後讀到的 `validation` 也沒有 `lint` 鍵 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-002 | 作法 1；`test_lint_true_queues_exactly_one_job` | 功能 | 同上；呼叫者名下有一個在線的 Slurm 型環境代理 | 呼叫驗證並傳 `lint=True` | 靜態檢查照舊做並已存下；jobs 恰好多一列 `lint_pipeline`；回傳 `lint` 為 `{"state": "queued", "job_id": 該列的編號}`；驗證紀錄的 `lint_job_id` 等於該列編號、`lint_status` 為 `queued`；外層 `ok` 為 True | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-003 | 作法 2（專案檔與匯出 zip 同一份） | 功能 | 同 TC-002 | 傳 `lint=True` 後，取出工作的參數，並匯出同一版本的 zip | 工作參數含 `name`、`version`、`project`；`project` 的檔名集合與每個檔案內容，跟匯出 zip 裡的完全相同 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-004 | 作法 1（`lint` 必須是 True／False） | 例外 | 同 TC-001 | 分別傳 `lint="yes"`、`lint=1`、`lint=None` | 三次都回 `ok: False` 與一句說明；沒有排任何工作；驗證紀錄沒有被寫入或改動 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-005 | 作法 1（被拒但靜態照存）；`test_no_agent_online_is_a_refusal_not_an_error` | 例外 | 呼叫者沒有任何在線的代理 | 傳 `lint=True` | 回傳 `lint.state` 為 `refused`，`message` 是白話、含「代理」並說明該怎麼處理；外層 `ok` 仍為 True；靜態結果已存；jobs 沒有新增列 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-006 | 作法 6；`test_cloud_environment_is_skipped` | 例外 | 呼叫者只有雲端類（GCB）環境，代理在線 | 傳 `lint=True` | `lint.state` 為 `refused`，沒有排工作 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-007 | 作法 6、2 | 功能 | 呼叫者有一個在線的 GCB 環境，也有一個在線的 Slurm 型環境 | 傳 `lint=True` | 工作排到 Slurm 型環境，不是 GCB | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-008 | 作法 2（`compute_env` 有給＝只試它） | 功能 | 呼叫者名下有兩個在線的 Slurm 型環境 A、B | 傳 `lint=True, compute_env=B` | 工作排到 B | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-009 | 作法 2（只試它） | 例外 | 呼叫者名下環境 A 在線、環境 B 的代理離線 | 傳 `lint=True, compute_env=B` | `lint.state` 為 `refused`、訊息白話；沒有改排到 A；沒有排任何工作 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-010 | 作法 2（沒給＝呼叫者名下可用的）；專長守則：擁有者規則 | 功能 | 呼叫者自己有一個在線 Slurm 型環境；另一位使用者也有一個在線 Slurm 型環境 | 呼叫者傳 `lint=True`，不給 `compute_env` | 工作排到呼叫者自己的環境，絕不排到別人的 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-011 | `test_compute_env_of_somebody_else_is_not_found`；專長守則：跨使用者（寫） | 例外 | 第二位使用者擁有環境 E | 第一位使用者傳 `lint=True, compute_env=E` | 回應與傳一個根本不存在的環境編號時完全相同；沒有排工作；看不出 E 存在 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-012 | `test_someone_elses_pipeline_is_not_found_and_nothing_queued`；專長守則：跨使用者（寫） | 例外 | 第一位使用者有組合 P；第二位使用者有自己的 token | 第二位傳 `lint=True` 驗證 P | 回應與驗證一個不存在的組合時同一句；jobs 與驗證紀錄兩張表都沒有變 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-013 | 專長守則：跨使用者（讀） | 例外 | 第一位使用者的組合 P 已跑過 lint 且有結果；第二位使用者有自己的 token | 第二位呼叫 `get_validation` 讀 P | 回應與讀一個不存在的組合時同一句；看不到任何 lint 狀態或報告 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-014 | 作法 2（總位元組 ≤ `MAX_BYTES`）；`test_too_big_project_is_refused` | 例外 | 把 `MAX_BYTES` 在測試裡調小到組合放不下；代理在線 | 傳 `lint=True` | `lint.state` 為 `refused`，訊息白話、說明原因與處理方式；沒有排工作；靜態結果照存；外層 `ok` 為 True | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-015 | 作法 2（檔數 ≤ `MAX_FILES`） | 例外 | 把 `MAX_FILES` 在測試裡調小到組合的檔案數超過；代理在線 | 傳 `lint=True` | `lint.state` 為 `refused`；沒有排工作 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-016 | 範圍：`jobs.py`；`test_lint_pipeline_cannot_be_queued_by_the_generic_door` | 例外 | 無 | 直接用通用入口 `jobs.enqueue(..., "lint_pipeline", …)` 排工作 | 被拒絕，訊息指向專用入口（`enqueue_lint_pipeline`）；沒有新增 jobs 列 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-017 | 作法 2（工作不需確認）；追加 6；專長守則：確認管道 | 功能 | 代理在線 | 傳 `lint=True`，過程中不經任何確認步驟 | 工作直接排入（唯讀、不花錢）；沒有產生任何待確認的請求；工作內容不含啟動管線 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-018 | 追加 5 | 功能 | 同一版本已送過一次 `lint=True` 且有結果 | 再送一次 `lint=True` | `lint_job_id` 換成新工作的編號、`lint_status` 回到 `queued`、`lint_report` 清空；舊工作之後完成，其結果不會被讀進來 | 自動：`platform/tests/test_pipeline_lint.py` |

## User Story 2 — 站台代理在自己的主機上跑 lint，並誠實回報（優先度 P1）

站台側。測試檔：`platform/tests/test_station_lint.py`（假的 `RUN` 與 `WHICH`；忘了換成假的會讓測試失敗）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 作法 5(b)；`test_not_installed_is_unavailable` | 例外 | 假的 `WHICH` 回 None（找不到 nf-core） | 代理執行 lint 工作 | 工作完成（done），結果 `ok: False`、`status: unavailable`；`reason` 為白話並含「不會自動安裝」；假的 `RUN` 零次被呼叫（沒有安裝、沒有下載） | 自動：`platform/tests/test_station_lint.py` |
| TC-021 | 作法 5(d)；`test_passed_and_failed_from_json` | 功能 | 假的 `RUN` 產生一份「失敗數為 0」的 JSON | 代理執行 lint 工作 | 結果 `status` 為 `passed`，`counts` 的通過／警告／失敗三個數字與 JSON 一致 | 自動：`platform/tests/test_station_lint.py` |
| TC-022 | 作法 5(d) | 功能 | 假的 `RUN` 產生一份有失敗項目的 JSON | 代理執行 lint 工作 | `status` 為 `failed`；`counts` 三個數字正確 | 自動：`platform/tests/test_station_lint.py` |
| TC-023 | 作法 5(d)（前 50 條） | 功能 | JSON 裡有超過 50 條檢查結果 | 代理執行 lint 工作 | `report` 只含前 50 條，每條格式為「檢查名：訊息」 | 自動：`platform/tests/test_station_lint.py` |
| TC-024 | 作法 5(c)；`test_command_is_exact` | 功能 | 假的 `WHICH` 找得到 nf-core | 代理執行 lint 工作並記錄 `RUN` 收到的指令 | 指令恰為 `["nf-core", "pipelines", "lint", "--dir", <暫存資料夾>, "--json", <資料夾外的 json 檔>]` | 自動：`platform/tests/test_station_lint.py` |
| TC-025 | 作法 5(c) | 功能 | 同 TC-024 | 檢查 `RUN` 收到的參數 | `shell` 不是 True；`timeout` 不超過 240 秒 | 自動：`platform/tests/test_station_lint.py` |
| TC-026 | 作法 5(c) | 功能 | 同 TC-024；測試環境變數裡放了額外的假變數 | 檢查 `RUN` 收到的環境 | 環境只有 `PATH`、`HOME`、`LANG` 三個 | 自動：`platform/tests/test_station_lint.py` |
| TC-027 | 作法 5(c)（不經 sbatch／srun／ssh） | 功能 | 同 TC-024 | 檢查指令的每一段 | 不含 `sbatch`、`srun`、`ssh`、`nextflow`；lint 是在代理自己的主機上直接跑 | 自動：`platform/tests/test_station_lint.py` |
| TC-028 | 作法 5(d)；`test_timeout_and_crash_are_errors` | 例外 | 假的 `RUN` 丟出逾時（`TimeoutExpired`） | 代理執行 lint 工作 | `status` 為 `error`；`reason` 是白話；訊息不含堆疊、也不含暫存資料夾路徑 | 自動：`platform/tests/test_station_lint.py` |
| TC-029 | 作法 5(d) | 例外 | 假的 `RUN` 丟出 `OSError`（程式崩潰或無法執行） | 代理執行 lint 工作 | `status` 為 `error`；`reason` 白話；不含堆疊與暫存路徑 | 自動：`platform/tests/test_station_lint.py` |
| TC-030 | 作法 5(d)；追加 3 | 例外 | 假的 `RUN` 回傳碼非 0，且 JSON 檔讀不出來 | 代理執行 lint 工作 | `status` 為 `error`（視同崩潰），不是 `passed`；`reason` 白話；不含堆疊與暫存路徑 | 自動：`platform/tests/test_station_lint.py` |
| TC-031 | 作法 5(d)；追加 3 | 功能 | 假的 `RUN` 回傳碼 0，JSON 檔讀不出來，標準輸出超過 40 行 | 代理執行 lint 工作 | `status` 為 `passed`；`report` 是標準輸出的最後 40 行，且不超過 8000 字元 | 自動：`platform/tests/test_station_lint.py` |
| TC-032 | 作法 5(c)；`test_files_written_and_removed` | 功能 | 工作參數的 `project` 有數個檔案 | 代理執行 lint 工作；在 `RUN` 被呼叫的當下檢查暫存資料夾 | 資料夾裡的檔案內容與 `project` 完全相同；JSON 輸出檔在資料夾之外 | 自動：`platform/tests/test_station_lint.py` |
| TC-033 | 作法 5(e) | 功能 | 同 TC-032 | 代理正常跑完 lint 工作 | 暫存資料夾已不存在 | 自動：`platform/tests/test_station_lint.py` |
| TC-034 | 作法 5(e)（含例外） | 例外 | 假的 `RUN` 丟出例外 | 代理執行 lint 工作 | 離開後暫存資料夾已不存在 | 自動：`platform/tests/test_station_lint.py` |
| TC-035 | 作法 5(a)；`test_bad_paths_are_refused` | 例外 | `project` 內有路徑 `../x` | 代理執行 lint 工作 | 工作被 `refused`；`RUN` 未被呼叫；沒有寫出任何檔案 | 自動：`platform/tests/test_station_lint.py` |
| TC-036 | 作法 5(a) | 例外 | `project` 內有路徑 `/etc/passwd`（開頭是 `/`） | 代理執行 lint 工作 | `refused`；`RUN` 未被呼叫 | 自動：`platform/tests/test_station_lint.py` |
| TC-037 | 作法 5(a) | 例外 | `project` 內有含空字元的路徑 `a\x00b` | 代理執行 lint 工作 | `refused`；`RUN` 未被呼叫 | 自動：`platform/tests/test_station_lint.py` |
| TC-038 | 作法 5(a) | 例外 | `project` 內有長度 513 字元的路徑 | 代理執行 lint 工作 | `refused`；`RUN` 未被呼叫 | 自動：`platform/tests/test_station_lint.py` |
| TC-039 | 作法 5(a)（總量） | 例外 | `project` 的總位元組超過上限 | 代理執行 lint 工作 | `refused`；`RUN` 未被呼叫 | 自動：`platform/tests/test_station_lint.py` |
| TC-040 | 作法 5(a)（檔數） | 例外 | `project` 的檔案數超過上限 | 代理執行 lint 工作 | `refused`；`RUN` 未被呼叫 | 自動：`platform/tests/test_station_lint.py` |
| TC-041 | 範圍：`handlers.py`；`test_handlers_register_the_kind` | 功能 | 無 | 讀代理的工作種類登記 | `JOB_KINDS` 最後一個是 `lint_pipeline`；`ARG_KEYS["lint_pipeline"]` 恰為 `{"name", "version", "project"}`；代理的種類集合與平台 `jobs.KINDS` 的集合相同 | 自動：`platform/tests/test_station_lint.py` |
| TC-042 | 範圍：`handlers.py` | 例外 | 一個 `lint_pipeline` 工作帶了多餘的參數 | 代理處理該工作 | 多餘參數被拒絕，`RUN` 未被呼叫 | 自動：`platform/tests/test_station_lint.py` |
| TC-043 | 範圍：`jobs.py`（期限與環境變數） | 功能 | 無 | 讀 `jobs.DEADLINE_SECONDS` 與環境變數對應表 | `DEADLINE_SECONDS["lint_pipeline"]` 為 300；對應的環境變數名為 `ABF_PLATFORM_DEADLINE_LINT_PIPELINE`，設了之後期限隨之改變；`jobs.KINDS` 共十一種且包含 `lint_pipeline` | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-044 | 作法 4；「端到端（假平台）」 | 功能 | 假平台上排了一個 `lint_pipeline` 工作，假站台備好、`RUN` 回一份有失敗的 JSON | 代理 `run_once` 領工作並回報；之後呼叫 `get_validation` | jobs 該列變成 `done`；`get_validation` 讀得到 `lint` 的狀態與報告，內容與假 JSON 一致 | 自動：`platform/tests/test_station_lint.py` |
| TC-045 | 完成標準：手動 1 | 功能 | 維護者在 nano4 代理主機上 | 照 `docs/TESTING.md` 新一節「組合的 lint (017c2a)」第一步，執行 `nf-core --version` | 看到版本號，確認工具存在；該節步驟具體到可照做 | 手動：`docs/TESTING.md` |
| TC-046 | 完成標準：手動 2 | 功能 | 維護者有一個存好的組合，nano4 代理在線、nf-core 已裝 | 照手動一節，在 Python 呼叫 `validate_pipeline(..., lint=True)`，等站台跑完再 `get_validation` | `lint.status` 為 `passed` 或 `failed` 之一，`report` 有內容（第一行為通過／警告／失敗的數字） | 手動：`docs/TESTING.md` |
| TC-047 | 完成標準：手動 3；作法 5(b) | 例外 | 同 TC-046，但把 `nf-core` 移出 `PATH` | 照手動一節重做一次 | `lint.status` 為 `unavailable`，`report` 說明沒有安裝；沒有任何安裝動作發生 | 手動：`docs/TESTING.md` |

## User Story 3 — 結果存在這個版本的驗證紀錄，之後讀得到（優先度 P1）

平台側，結果在 `get_validation` 讀取時才收（不等待、不開背景程式）。測試檔：`platform/tests/test_pipeline_lint.py`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 作法 4（queued／claimed 維持）；`test_result_is_collected_lazily` | 功能 | 已送出 `lint=True`；工作分別處於「排隊中」與「已被代理領走」 | 兩個狀態下各呼叫一次 `get_validation` | 兩次讀到的 `lint.status` 都是 `queued`；紀錄沒有被改成別的狀態 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-051 | 作法 3、4 | 功能 | 假站台已完成工作，結果為 `failed` 附報告與 counts | 呼叫 `get_validation` | `lint_status`、`lint_report`、`lint_job_id`、`lint_at` 四欄都已寫入；`lint_status` 為 `failed` | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-052 | 作法 4（之後不再查） | 功能 | 結果已被收進紀錄（TC-051 之後） | 再呼叫一次 `get_validation`，並用計數器數 jobs 被查詢的次數 | 第二次讀不再查 jobs；回傳內容與第一次相同 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-053 | 追加 4 | 功能 | 工作完成，counts 為通過 X／警告 Y／失敗 Z | 呼叫 `get_validation` | `lint.report` 第一行是「通過 X／警告 Y／失敗 Z (passed X / warned Y / failed Z)」，數字正確；其後才是逐條訊息 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-054 | 作法 4；`test_each_terminal_state` | 功能 | 工作完成，站台結果為 `passed` | 呼叫 `get_validation` | `lint.status` 為 `passed` | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-055 | 作法 4、5(b) | 功能 | 工作完成，站台結果為 `unavailable`（沒裝 nf-core） | 呼叫 `get_validation` | `lint.status` 為 `unavailable`；`report` 是白話，說明沒有安裝所以沒有執行 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-056 | 作法 4（refused＝error） | 例外 | 工作被站台以 `refused` 結案（例如路徑不合） | 呼叫 `get_validation` | `lint.status` 為 `error`；`report` 是白話原因 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-057 | 作法 4（error＝error） | 例外 | 工作以 `error` 結案（站台崩潰或逾時） | 呼叫 `get_validation` | `lint.status` 為 `error`；`report` 是白話原因，不含堆疊 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-058 | 作法 4（expired） | 例外 | 工作超過期限未被領走或未完成而過期 | 呼叫 `get_validation` | `lint.status` 為 `expired`；`report` 是白話 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-059 | 作法 4（沒跑過就沒有 `lint` 鍵）；待確認 4 | 功能 | 一個從沒傳過 `lint=True` 的版本 | 呼叫 `get_validation` | `validation` 裡沒有 `lint` 這個鍵（不是 `lint: None`）；`validation` 與先前沒有此功能時的內容逐項相等 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-060 | 作法 4（`lint` 鍵的形狀） | 功能 | 一個已有 lint 結果的版本 | 呼叫 `get_validation` | `validation.lint` 恰有 `status`、`report`、`linted_at` 三個鍵 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-061 | 作法 3（INSERT OR REPLACE 不可洗掉 lint）；`test_revalidate_keeps_lint` | 功能 | 版本已有 lint 結果 | 再呼叫一次不帶 `lint` 的驗證 | 靜態結果更新，但 lint 的四欄與回傳的 `lint` 仍在、內容不變 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-062 | 作法 4（report ≤ 8000）；作法 3；`test_clean_result_bounds` | 例外 | 站台回報的 `report` 長 20000 字元 | 收結果後讀 `get_validation` | 存下的 `lint_report`（含第一行計數）不超過 8000 字元 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-063 | 作法 4（counts 0 到 100000 整數） | 例外 | 站台回報的 `counts` 帶字串或負數 | 收結果 | 這些不合法的數字不會原樣留下；不出現錯誤堆疊 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-064 | 作法 4（counts 上限） | 例外 | 站台回報的 `counts` 有數字大於 100000 | 收結果 | 這個超過上限的數字不會原樣留下 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-065 | 作法 4（只留四個鍵） | 例外 | 站台回報的結果帶了 `status`、`reason`、`report`、`counts` 以外的多餘鍵 | 收結果 | 多餘的鍵被丟掉，不進紀錄也不出現在回傳 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-066 | 作法 4（status 五值之一，其他＝error） | 例外 | 站台回報的 `status` 是不在五個合法值內的字串 | 收結果 | `lint.status` 為 `error` | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-067 | 作法 4（reason ≤ 200） | 例外 | 站台回報的 `reason` 長 1000 字元 | 收結果 | 存下並顯示的原因不超過 200 字元 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-068 | 專長守則：錯誤訊息與日誌（不含密鑰） | 例外 | 跑完 TC-005、TC-014、TC-056、TC-057 的情境，並收集所有回應與日誌 | 掃描這些文字 | 不含 token、密鑰、`platform.db`、堆疊、內部路徑或 SQL（沿用既有洩漏掃描） | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-069 | 作法 4（`get_validation` 讀取時會寫） | 功能 | 版本有靜態檢查結果，lint 工作剛完成 | 呼叫 `get_validation` 收結果 | 收結果只改動 lint 的四欄；靜態檢查的結果與其他欄位原樣不變 | 自動：`platform/tests/test_pipeline_lint.py` |

## User Story 4 — 舊資料升級不壞，既有行為不變（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | 作法 3（`ensure_columns`）；`test_old_table_gets_the_columns` | 功能 | 先建一張只有舊六欄的驗證紀錄表並塞一列 | 呼叫 `get_validation` | 表多出 `lint_status`、`lint_report`、`lint_job_id`、`lint_at` 四欄；舊列資料不變；回傳的 `validation` 沒有 `lint` 鍵 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-081 | 作法 3（可重複呼叫） | 功能 | 同 TC-080，已升級過一次 | 再呼叫一次 `get_validation`（共兩次） | 不報錯，欄位不重複，資料不變 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-082 | 環境事實（表被刪會重建）；作法 3 | 功能 | 驗證紀錄表被刪掉 | 呼叫驗證 | 重建出來的表同樣有那四個 lint 欄 | 自動：`platform/tests/test_pipelines_validation.py` |
| TC-083 | 範圍：`store.py`；`test_old_jobs_table_is_migrated` | 功能 | 一張沒有 `lint_pipeline` 種類的舊 `jobs` 表，內有幾列既有工作 | 開啟平台資料庫並排一個 `lint_pipeline` 工作 | 可以排入；既有列與編號完全不變 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-084 | 範圍：`actions/pipelines.py`（抽出 `_project_files`，匯出不變） | 功能 | 一個存好的組合版本 | 匯出 zip | 輸出與改動前逐位元組相同（既有匯出測試不改就通過） | 自動：`platform/tests/test_pipeline_export.py` |
| TC-085 | 作法 1、7（`lint=False` 逐位元相同） | 功能 | 不傳 `lint` | 呼叫驗證 | 靜態檢查的結果與寫入的原本六欄跟改動前完全相同 | 自動：`platform/tests/test_pipelines_validation.py` |
| TC-086 | 被釘住的既有測試 | 功能 | 計畫列的既有測試（工作種類名單與順序、驗證欄位清單、`test_no_program_is_started_by_validation` 等） | 跑這些測試 | 全部通過；改動只限計畫列的那幾處（名單末位加 `lint_pipeline`、欄位清單加四欄名、字單拿掉 `"lint"`），沒有任何斷言被刪弱 | 自動：`platform/tests/test_byte_channel_a.py`、`test_byte_channel_b.py`、`test_nfcore_catalogue.py`、`test_station_clean.py`、`test_station_pipeline_files.py`、`test_pipelines_validation.py`、`test_pipeline_export.py`、`test_mcp_canvas_read.py`、`test_pipeline_launch.py` |
| TC-087 | 範圍：文件與計數 | 功能 | 無 | 跑檢查工作種類說明、檔頭註解、環境變數文件的既有測試 | `jobs.__doc__` 寫 eleven 並點名 `lint_pipeline`；`store.py` 註解寫 exactly eleven job kinds、CHECK 名單、`handlers.py` 第 1 行註解三處一致；`ABF_PLATFORM_DEADLINE_LINT_PIPELINE` 已寫在 `docs/PLATFORM.md` | 自動：`platform/tests/test_job_kinds_docs.py`、`test_handlers_header.py`、`test_env_vars_documented.py`、`test_launch_docs.py` |

## User Story 5 — 這次明講不做的事（不在範圍）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-100 | 不做：lint 失敗不擋 launch；目標段 | 不在範圍 | 一個 `lint_status` 為 `failed` 的版本，靜態檢查通過 | 對它做啟動前的準備（`pipeline_launch.prepare`） | 照舊只看靜態檢查，不因 lint 失敗而被擋；啟動的確認方式沒有改 | 自動：`platform/tests/test_pipeline_launch.py` |
| TC-101 | 不做：MCP／網頁上的 `lint` 參數；版本頁顯示 | 不在範圍 | 無 | 檢查 `mcp_server.py`、`web.py` 的原始碼 | 兩個檔案都不含 `lint` | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-102 | 專長守則：對等性；作法 1（只到動作層） | 不在範圍 | 無 | 同時列舉 MCP 工具名單（含數量）與動作層函式 | MCP 工具名單與數量跟改動前相同，使用者看得到的動作與動作層函式仍一一對應；`validate_pipeline` 的 `lint` 只在動作層 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-103 | 不做：`-stub-run`、nf-test | 不在範圍 | 無 | 掃 `pipeline_lint.py` 與 `actions/pipelines.py` 的原始碼，並跑驗證相關既有測試 | 不含 `subprocess`、`os.system`、`sbatch`、`nextflow`、`stub`；平台沒有任何地方啟動程式；既有 `test_no_program_is_started_by_validation` 只拿掉 `"lint"` 一個字 | 自動：`platform/tests/test_pipeline_lint.py`、`test_pipelines_validation.py` |
| TC-104 | 不做：自動安裝 nf-core tools | 不在範圍 | 無 | 掃 `abf_station/lint.py` 的原始碼 | 不含 `pip`、`conda`、`install`、`urllib`、`requests`（沒有安裝或下載的程式） | 自動：`platform/tests/test_station_lint.py` |
| TC-105 | 裁決 (c)：永不送叢集 | 不在範圍 | 無 | 掃 `abf_station/lint.py` 的原始碼 | 不含 `sbatch`、`srun`、`ssh` | 自動：`platform/tests/test_station_lint.py` |
| TC-106 | 不做：雲端類環境代理跑 lint；作法 6 | 不在範圍 | 無 | 檢查 `CLOUD_JOB_KINDS`，並跑雲端相關既有測試 | `CLOUD_JOB_KINDS` 沒有 `lint_pipeline`；`test_azure_launch.py`、`test_k8s_launch.py`、`test_k8s_ce.py` 不需修改就通過 | 自動：`platform/tests/test_azure_launch.py`、`test_k8s_launch.py`、`test_k8s_ce.py` |
| TC-107 | 不做：通知使用者、背景輪詢 | 不在範圍 | 一個 lint 工作已被假站台完成，但沒有任何人呼叫 `get_validation` | 讓時間過去、做別的平台動作（不含讀這個版本的驗證） | 驗證紀錄的 `lint_status` 仍是 `queued`（沒有背景程式偷偷收結果）；沒有送出任何通知 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-108 | 不做：修剪舊 lint 結果 | 不在範圍 | 多個版本都已有 lint 結果 | 做完其他版本的 lint 與讀取 | 每個版本各自的 lint 結果都還在，沒有被自動刪掉或修剪 | 自動：`platform/tests/test_pipeline_lint.py` |
| TC-109 | 不做：把 lint 放進 `validate()` 的 `checks`；作法 7 | 不在範圍 | 無 | 呼叫 `validate()` | 回傳的 `checks` 仍恰為 `["static"]` | 自動：`platform/tests/test_validate.py` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-120 | 第 1 條 2（唯一的送件路徑是需確認的啟動工作；不得另有第二條送件路徑） | 功能 | 新增 `pipeline_lint.py`、`abf_station/lint.py` 之後 | 跑 `tests/no_second_run_state_test.sh`（掃描範圍含 `platform/`） | 通過：新檔案沒有送件動作，lint 在代理主機直接跑，沒有新增任何送件路徑或常駐程式 | 自動：`tests/no_second_run_state_test.sh` |
| TC-122 | 範圍：`pipeline_lint.py`、`abf_station/lint.py` 檔頭 `# Nothing existing: …`（TC-070）；不啟動程式（TC-071） | 功能 | 兩個新檔案已建立 | 跑 `test_scope.py` | 通過：兩個新檔案的檔頭都寫明 `# Nothing existing: <理由>`，且 `pipeline_lint.py` 不含 `subprocess` | 自動：`platform/tests/test_scope.py` |
