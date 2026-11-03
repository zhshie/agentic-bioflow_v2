# 測試案例：env-vars-documented（程式讀的每個 ABF_* 環境變數都要寫進 docs/）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Source: specs/env-vars-documented/plan.md (A 級，沒有獨立 spec.md；plan 兼任規格)。
-->

**規格**：`specs/env-vars-documented/plan.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：寫錯、漏掉、有人偷塞時，測試或文件怎麼反應（變紅、拒絕）。
- **不在範圍**：計畫「不做」「不准碰」的事；確認真的沒做。

名詞：「環境變數」＝程式啟動時從作業系統讀的設定名字，例如 `ABF_STATION_UPLOADS`。「代理」＝跑 `abf-station run` 的那個程式，替平台在實驗室機器上做事。「白名單」＝掃描測試允許「程式有、文件沒有」的名字清單，這次只准一個。

維護者原話（計畫「維護者原話」節，逐字）：

- 「A 級：錯誤修正／測試／文件／重構，不改使用者看得到的行為」；「絕不放寬安全網」。
- `docs/PLATFORM.md:871` 現行說法要保持成立：「Settings that only the tests change: `ABF_PLATFORM_DEADLINE_PIPELINE_FILES` (default 90) …」。
- `platform/abf_station/put_upload.py:84` 程式自己的話：「這個代理沒有設定上傳資料夾（ABF_STATION_UPLOADS），請管理者設定」——文件要讓管理者做得到這句話。

新測試檔：`platform/tests/test_env_vars_documented.py`。單檔指令（相對於 `platform/`）：`ABF_PYTEST_TARGETS=tests/test_env_vars_documented.py bash tests/platform_test.sh`。

## User Story 1 — 管理者在 docs/ 找得到每個要設的變數（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「決定（文件）」PLATFORM 表；`jobs.py:29` `read_task_log`＝60 | 功能 | 改完後的 `docs/PLATFORM.md` | 找「Online, offline, and the numbers」表，看含 `ABF_PLATFORM_DEADLINE_READ_TASK_LOG` 的那一行 | 同一行有 `read_task_log`（或其名字）與完整數字 `60` 秒；欄位格式與 `preflight` 列相同 | 自動：`test_env_vars_documented.py::test_deadline_table_covers_every_job_kind`（`read_task_log` 分支） |
| TC-002 | 同上；`jobs.py:30` `clean_work`＝600 | 功能 | 同上 | 看含 `ABF_PLATFORM_DEADLINE_CLEAN` 的那一行 | 同一行有完整數字 `600` 秒，欄位格式同上 | 自動：同上（`clean_work` 分支） |
| TC-003 | 同上；`jobs.py:30` `put_upload`＝3600 | 功能 | 同上 | 看含 `ABF_PLATFORM_DEADLINE_PUT_UPLOAD` 的那一行 | 同一行有完整數字 `3600` 秒，欄位格式同上 | 自動：同上（`put_upload` 分支） |
| TC-004 | 計畫「決定（文件）」第 871 行段落；`put_upload.py:23-24` | 功能 | 同上 | 看 `docs/PLATFORM.md` 「Settings that only the tests change」那一段 | 段落提到 `ABF_STATION_PUT_TIMEOUT`，同一行寫出單位是秒、預設 3600、它覆寫 put_upload 的複製時限；原有的 `ABF_PLATFORM_DEADLINE_PIPELINE_FILES`（90）等字句仍在 | 自動：新檔追加斷言（名字與 3600 同行）；原句保留見 TC-010 |
| TC-005 | 計畫「決定（文件）」第 871 行段落；`gcb_launch.py:28-29,91-95,209` | 功能 | 同上 | 同上 | 段落提到 `ABF_STATION_GCB_SETTLE_SECONDS`，同一行寫出單位是秒、預設 5（完整數字）、head 程序在這幾秒內消失就當作沒起來 | 自動：新檔追加斷言（名字與 5 同行） |
| TC-006 | 計畫「決定（文件）」`OPERATIONS.md:234`；原話「文件要讓管理者做得到這句話」 | 功能 | 改完後的 `docs/OPERATIONS.md` | 找含 `ABF_STATION_UPLOADS` 的那一行 | 同一行還含 `abf-station`，且含 `ABF_PLATFORM_UPLOADS` 或 `uploads_root` 其中之一；位置在「The web page /upload」那一點附近 | 自動：`test_station_uploads_is_explained_where_the_web_upload_is` |
| TC-007 | 計畫「決定（文件）」`OPERATIONS.md:234`；`put_upload.py:84` | 功能 | 同上 | 讀那一行 | 說出沒設 `ABF_STATION_UPLOADS` 時，上傳會被代理拒絕，並引出訊息「這個代理沒有設定上傳資料夾（ABF_STATION_UPLOADS）」 | 自動：新檔追加斷言（該行含這段訊息文字） |
| TC-008 | 計畫「作法」第 41 行、裁決 4（developer-agent 已定案） | 功能 | 改完後的 `docs/OPERATIONS.md` 與 ledger | 閱卷人讀那句話，再讀 ledger 與 `platform/tests/test_byte_channel_b.py` | 若句子寫「必須與平台 `uploads_root` 同一個資料夾」，ledger 要引出兩邊對得上的證據（`test_byte_channel_b.py:76,94-96` 的 `set_uploads` 與 `:195,377,636` 的 `enqueue_put_upload(..., aw.uploads, ...)` 用同一個資料夾，或等價證據）；沒引出就句子必須是較弱的「指向平台暫存上傳檔的資料夾」並在 ledger 說明 | 手動：閱卷人讀 ledger 與該測試檔（本件不新增 TESTING.md 步驟） |
| TC-009 | 計畫「失敗先行測試」`test_deadline_table_covers_every_job_kind`：「防名字有了、數字寫錯」 | 例外 | 把任一 deadline 行的秒數改錯（例如 `put_upload` 列寫 `600`，或只靠 `3600` 裡含有 `60` 的巧合） | 跑 `test_deadline_table_covers_every_job_kind` | 測試變紅並指出是哪個 kind 的秒數不對；比對用完整數字（前後不是數字），子字串碰巧含有不算 | 自動：同上；閱卷人讀斷言確認比對方式 |
| TC-010 | 計畫「完成標準」：docs 差異只有新增行；`PLATFORM.md:871` 要保持成立 | 功能 | 本分支對 `origin/v3` 的 `git diff -- docs/` | 逐行看被刪／被改的行 | 既有句子的字沒有被刪或改（第 871 行段落、第 234 行那一點，只准尾端追加或另起新行）；沒有其他 docs 檔被動 | 手動：閱卷人執行 `git diff origin/v3...HEAD -- docs/` 並檢查沒有被刪的字 |
| TC-011 | 計畫「完成標準」第一條 | 功能 | 本分支 HEAD | 各跑 `test_cloud_upload_docs.py`、`test_job_kinds_docs.py`、`test_station_docs.py`、`test_mcp_server_doc.py`、`test_onboarding_doc.py` | 五個檔全綠（它們讀同幾份文件，沒被新增的句子弄壞） | 自動：各檔 `ABF_PYTEST_TARGETS=tests/<檔名> bash tests/platform_test.sh` |

## User Story 2 — 往後程式新增 ABF_* 變數卻沒寫文件，測試就變紅（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 計畫「失敗先行測試」第 1 條；目標 | 功能 | 本分支（文件已補） | 跑 `test_every_abf_variable_the_code_reads_is_named_in_docs` | 通過：掃 `platform/abf_platform`、`platform/abf_station`、`platform/abf_launch` 下所有 `.py` 取出的每個 `ABF_*` 名字（共 27 個），除白名單外都整串出現在 `docs/*.md` | 自動：`test_env_vars_documented.py::test_every_abf_variable_the_code_reads_is_named_in_docs` |
| TC-013 | 計畫「失敗先行測試」第 1 條與「兩分支比對」 | 例外 | 在 `origin/v3`（改前）放入新測試檔，或 ledger 貼的「改前紅」輸出 | 在 v3 與本分支各跑 `test_env_vars_documented.py` | v3 上第 1、4、5 條紅；失敗訊息列出的缺漏名字正好是 `ABF_PLATFORM_DEADLINE_CLEAN`、`ABF_PLATFORM_DEADLINE_PUT_UPLOAD`、`ABF_PLATFORM_DEADLINE_READ_TASK_LOG`、`ABF_STATION_UPLOADS`、`ABF_STATION_PUT_TIMEOUT`、`ABF_STATION_GCB_SETTLE_SECONDS`，不含 `ABF_FORWARD_PORT`；本分支同一檔全綠 | 手動：閱卷人在兩邊各跑單檔並比對輸出，與 ledger 貼的相符 |
| TC-014 | 計畫「決定（測試）」：白名單「只准這一個」 | 功能 | 本分支 | 跑 `test_the_allowlist_has_exactly_one_entry` | 白名單集合 `== {"ABF_FORWARD_PORT"}`，旁邊有註解說明它是殼層變數、不是設定；沒有萬用字元 | 自動：`test_the_allowlist_has_exactly_one_entry` |
| TC-015 | 計畫「失敗先行測試」第 3 條 | 功能 | 本分支 | 跑 `test_the_scan_finds_the_names_it_should` | 掃描結果至少含 `ABF_PLATFORM_DEADLINE_PREFLIGHT`、`ABF_STATION_UPLOADS`、`ABF_PLATFORM_DB`（掃描不是空的、正則沒寫壞） | 自動：`test_the_scan_finds_the_names_it_should` |
| TC-016 | 計畫「決定（測試）」：「每個名字必須整串出現」「結尾不得是底線」 | 例外 | 假設程式讀 `ABF_STATION_X`，文件只有 `ABF_STATION_X_LONGER`（較長的名字） | 閱卷人讀測試的比對方式 | 只是別的長名字的前段，不算「寫進文件」；測試對文件用邊界比對（名字後面不是字母、數字、底線），所以這種情況會紅 | 自動：`test_every_abf_variable_...`；閱卷人讀斷言確認 |
| TC-017 | 計畫「決定（測試）」：不啟動任何服務、不連網 | 功能 | 新測試檔 | 閱卷人讀檔頭與 import | 只讀文字檔與 `jobs.DEADLINE_SECONDS`、`jobs._DEADLINE_ENV` 常數；沒有啟動伺服器、沒有開網路連線、沒有讀使用者家目錄設定；路徑來自 `from helpers import PLATFORM_DIR, REPO_ROOT` | 自動：整檔在無網路下通過；閱卷人讀 import |
| TC-018 | 計畫「範圍」第 28 行；環境事實分片說明 | 功能 | 新檔放入 `platform/tests/` | 讀新檔第一行；跑 `test_platform_parts.py` | 第一行以 `# Nothing existing: …` 開頭並說明搜過沒有現成測試；`test_platform_parts.py` 仍綠（新檔被分到某一片、沒漏沒重複） | 自動：`ABF_PYTEST_TARGETS=tests/test_platform_parts.py bash tests/platform_test.sh` |
| TC-019 | 計畫「失敗先行測試」首句：先寫、改文件前跑一次確認紅，紅的輸出貼進 ledger | 功能 | `specs/env-vars-documented/ledger.md` | 閱卷人讀 ledger | 有「改前紅」輸出（含六個名字）、「改後綠」輸出，以及兩分支比對 | 手動：閱卷人讀 ledger |

## 不在範圍（計畫「不做」「不准碰」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 計畫「作法」第 38 行：`ABF_FORWARD_PORT`「不寫進文件」 | 不在範圍 | 本分支 | 在 `docs/*.md` 全文找 `ABF_FORWARD_PORT` | 找不到；它只出現在測試白名單的註解與集合裡 | 自動：新檔追加斷言（文件全文不含該名字）；閱卷人另執行 `grep -rn ABF_FORWARD_PORT docs/` 為空 |
| TC-021 | A 級原話「不改使用者看得到的行為」；計畫「範圍：不准碰」「不做」第 1 條 | 不在範圍 | 本分支 | 執行 `git diff --stat origin/v3...HEAD` | 變動檔只有 `docs/PLATFORM.md`、`docs/OPERATIONS.md`、`platform/tests/test_env_vars_documented.py`，外加 `specs/env-vars-documented/` 底下的 plan／ledger；`platform/abf_platform/`、`platform/abf_station/`、`platform/abf_launch/` 一個字都沒動，因此沒有任何 `ABF_*` 名字、預設值、讀取邏輯被改，也沒有資料結構變動（不需要 migration） | 手動：閱卷人執行上述指令與 `git diff origin/v3...HEAD -- platform/abf_platform platform/abf_station platform/abf_launch`（應為空） |
| TC-022 | 計畫「不做」第 2、3 項；裁決 3 | 不在範圍 | 本分支 | 讀新測試掃描的目錄清單；看 docs 差異 | 掃描目錄只有 `platform/abf_platform`、`platform/abf_station`、`platform/abf_launch`；沒掃 `scripts/` 與 `hooks/`；`docs/` 沒有為 `ABF_CACHE_DIR`、`ABF_PIPELINE_FETCHER` 新增任何字 | 手動：閱卷人讀測試與 `git diff` |
| TC-023 | 計畫「不准碰」與「不做」第 4 項 | 不在範圍 | 本分支 | 執行 `git diff --name-only origin/v3...HEAD` | 沒有 `web.py`、`web_board.py`、`web_settings.py`、`compute_envs.py`、`cli.py`、`launch.py`、`deploy/`（含 `deploy/env.example`）、`tests/*.sh`；既有測試檔一個都沒動（既有斷言沒被刪改） | 手動：閱卷人執行上述指令 |
| TC-024 | 計畫裁決 1（developer-agent 已定案）：兩個測試用逾時「不寫進 OPERATIONS」 | 不在範圍 | 本分支 | 在 `docs/OPERATIONS.md` 找 `ABF_STATION_PUT_TIMEOUT`、`ABF_STATION_GCB_SETTLE_SECONDS` | 找不到；這兩個只出現在 `docs/PLATFORM.md` | 自動：新檔追加斷言；閱卷人另執行 grep |
| TC-025 | 計畫「不做」第 1 條：「不把『只有測試會改』的變數升級成正式設定」 | 不在範圍 | 本分支 | 讀 PLATFORM 第 871 行段落中新增的兩個變數的句子 | 語氣仍是「Settings that only the tests change」那一類（測試用、不建議管理者改）；沒有叫管理者去調它們 | 手動：閱卷人讀 `git diff -- docs/PLATFORM.md` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | 維護者原話「絕不放寬安全網」；憲法與 CLAUDE.md「Never edit during implementation」 | 功能 | 本分支 | 執行 `git diff --name-only origin/v3...HEAD` | 沒有 `spec.md`、`test-case.md`、`test-case-overview.md`、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`、`hooks/`；沒有任何閘或安全網被放寬 | 手動：閱卷人執行上述指令 |
| TC-027 | 計畫「完成標準」第二條；完成記號 | 功能 | 本分支 HEAD | 讀 `executor-status` 與 `git rev-parse HEAD` | 為 `GREEN <HEAD sha>`，工作樹乾淨；整個 `platform/tests` 套件在該 HEAD 全綠（已知環境紅除外，見 dev-plans README「通例：已知環境紅」） | 自動：`executor-status` 完成記號（閱卷人不重跑全套） |
| TC-028 | 專長守則（backend）：日誌與回應不含密鑰；錯誤訊息要說明原因與處理方式 | 例外 | 本分支 | 閱卷人讀 `git diff -- docs/` 新增的行 | 新增的文字沒有 token、密碼、金鑰、使用者家目錄或內部絕對路徑；引用的拒絕訊息同時說明原因（沒設資料夾）與處理（請管理者設定 `ABF_STATION_UPLOADS`）。本件不改動作層、寫入路徑、擁有者規則、資料結構，因此專長守則的對等性、跨使用者、確認管道、migration 各條不適用（由 TC-021 證明沒動產品程式碼） | 手動：閱卷人讀 `git diff` |

<!--
Rules for the writer:
- 手動欄：專案 docs/TESTING.md 沒有本件的手動步驟，本件也不准改該檔；每條手動列已寫明閱卷人要執行的指令。
- IDs are never renumbered after approval; a removed case keeps its row, struck through.
-->
