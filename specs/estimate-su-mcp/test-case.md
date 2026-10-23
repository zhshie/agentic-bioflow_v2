# 測試案例：接收器記下每個 task 的用量，get_run 帶出 SU 與台幣（estimate-su-mcp）

**規格**：`specs/estimate-su-mcp/plan.md`（本任務沒有獨立 spec.md，計畫即規格；含「維護者原話」與「裁決」）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫「不做」那一節明講這次不做的事；測試確認它真的沒做。

名詞：**SU** ＝國網的計算點數（核心數 × 小時 × 分區係數）；**task** ＝流程裡的一個小工作；**接收器** ＝平台上收 Nextflow 進度回報的那一段；**index** ＝平台存 run 紀錄的資料庫檔；**CE** ＝算力環境設定檔（例如 nano4 那份）。「自動」的測試都寫在 `platform/tests/test_su_in_get_run.py`，除非另行註明檔名；每條測試要在註解裡寫出自己的 TC 編號。

「維護者原話」三句的對應：①「SU 要能從平台查到，不是手算」→ TC-010、TC-060；②「約 120 SU」那種估算寫法（數字是估算不是帳單）→ TC-010、TC-011、TC-075；③「不要猜」（缺任何一個 task 的欄位，整個 run 的 SU 是 null 並說原因，不是 0）→ TC-020、TC-023、TC-024、TC-025、TC-026、TC-027、TC-030。

## User Story 1 — 接收器記下每個 task 的用量（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 2；失敗先行測試 1 | 功能 | 一個新 run；接收器收到一次進度回報，task 清單裡 COMPLETED、FAILED、RUNNING、CACHED 各一個，各自帶 cpus、realtime（毫秒）、queue | 接收器處理這次回報 | `task_usage` 表只有 COMPLETED 與 FAILED 那兩列；每列的 name、status、cpus、realtime_ms、queue 與回報裡的值一模一樣；RUNNING、CACHED 沒有列 | 自動：`test_receiver_keeps_cpus_realtime_queue_of_finished_tasks` |
| TC-002 | 作法 2（其他 status 不寫） | 功能 | 回報裡有 SUBMITTED 與 ABORTED 的 task | 接收器處理回報 | 這兩個 task 都沒有在 `task_usage` 出現 | 自動 |
| TC-003 | 作法 2（不寫、也不刪既有列） | 功能 | `task_usage` 已有某 task 的 COMPLETED 列 | 接收器又收到一次回報，同一個 task 這次的 status 是 RUNNING | 原本那一列還在，值沒變 | 自動 |
| TC-004 | 作法 2（upsert 全欄覆寫） | 功能 | 某 task 已有一列（realtime 1,800,000） | 接收器又收到同一個 task（同 taskId、同 attempt）的 COMPLETED 回報，realtime 改成 3,600,000 | 該 task 仍只有一列，realtime_ms 是 3,600,000（不是兩列） | 自動 |
| TC-005 | 作法 2（每個 attempt 各一列）；失敗先行測試 2 | 功能 | 同一個 task 重試過：attempt 1 是 FAILED、attempt 2 是 COMPLETED | 接收器處理這兩筆 | `task_usage` 有兩列，task_key 分別是 `<taskId>:1` 與 `<taskId>:2`，重試沒有把第一次那列刪掉 | 自動：`test_a_retry_keeps_both_attempts` |
| TC-006 | 作法 2（不是數字就存 NULL） | 例外 | 回報裡某個 COMPLETED task 的 cpus 是字串 "abc"、realtime 是 null | 接收器處理回報 | 該 task 仍有一列，cpus 與 realtime_ms 是 NULL（不是 0、不是丟錯） | 自動 |
| TC-007 | 作法 2（queue 非字串存 NULL）；環境事實（本機執行 queue 是 null） | 例外 | 回報裡一個 COMPLETED task 的 queue 是 null，另一個的 queue 是數字 5 | 接收器處理回報 | 兩個 task 都有列，queue 都是 NULL | 自動 |

## User Story 2 — 在 Claude Desktop 問 get_run 就看到 SU 與台幣（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 作法 6 範例；失敗先行測試 3；維護者原話①② | 功能 | 算力環境 `suSite: nano4`；一個已結束、屬於呼叫者的 run，成功 2 個 task：（cpus 2、realtime 1,800,000 毫秒、queue `ngs92G`）與（cpus 1、realtime 3,600,000、queue `ngs92G`） | 呼叫者問 `get_run` 該 run | 回答裡 `su` 等於 `{"su": 2.0, "twd_nstc": 0.2, "twd_academic": 0.4, "twd": {"nstc": 0.2, "academic": 0.4, "industry": 0.74}, "unknown_reasons": [], "site": "nano4"}`（浮點用近似比較） | 自動：`test_get_run_has_su_for_a_nano4_run` |
| TC-011 | 作法 6；裁決 4（twd 只在站點有 twd_per_su 才有） | 功能 | 該 run 沒有 `suSite`（用預設站點 taiwania3）；一個已結束的 run，成功 1 個 task：cpus 4、realtime 7,200,000、queue `ct56` | 問 `get_run` | `su` 為 8、`twd_nstc` 為 0.64、`site` 是 `taiwania3`，且 `su` 裡沒有 `twd` 這個鍵 | 自動 |
| TC-012 | 作法 6；裁決 4（五個固定鍵＋一個條件鍵） | 功能 | TC-010 與 TC-011 的兩個 run | 看 `su` 有哪些鍵 | 固定只有 `su`、`twd_nstc`、`twd_academic`、`unknown_reasons`、`site`；`twd` 只出現在 nano4 那個；沒有其他鍵（例如沒有 `found`、沒有 task 清單） | 自動 |
| TC-013 | 作法 2（前一次也花了 SU）；作法 6 | 功能 | 一個已結束的 run：同一個 task 的 attempt 1 是 FAILED（cpus 1、realtime 1,800,000、`ngs92G`），attempt 2 是 COMPLETED（cpus 1、realtime 3,600,000、`ngs92G`），站點 nano4 | 問 `get_run` | `su` 為 1.5（兩次都算），`twd_nstc` 為 0.15，`twd_academic` 為 0.3 | 自動 |
| TC-014 | 計畫「為什麼不是新增工具」（網頁與 MCP 共用同一個動作）；目標（Claude Desktop 看得到） | 功能 | TC-010 的 run | 透過 MCP 的 `get_run` 工具問 | MCP 回傳的 `su` 與直接呼叫動作層 `actions.get_run` 的 `su` 完全相同 | 自動 |
| TC-015 | 作法 4（`estimate_su` 在 `site is None` 時改用 `site_of_run`） | 功能 | TC-010 的 run（CE 是 nano4） | 呼叫 `estimate_su`，不指定 site | 回傳的是 nano4 的結果（su 2.0），不是 taiwania3 的 | 自動 |
| TC-016 | 作法 4（呼叫者明給 site 時照用） | 功能 | 既有 `platform/tests/test_estimate_su.py` | 不改一個字，跑那個檔 | 全部通過 | 自動：`platform/tests/test_estimate_su.py` |
| TC-017 | 作法 7 | 功能 | `mcp_server.py` 的 `get_run` 工具說明 | 讀工具說明 | 說明結尾有這句：`It also has su: the SU the run's finished tasks used and what that costs (an estimate from Nextflow's task records; null with the reasons when a record lacks what the formula needs).`；`test_actions_layer.py` 的 `BASELINE` 裡 `get_run` 那一筆與它逐字相同 | 自動：`platform/tests/test_actions_layer.py` |
| TC-020 | 作法 6 舊 run 範例；失敗先行測試 4；維護者原話③ | 例外 | 一個已結束、成功數大於 0、`task_usage` 完全沒有列的 run，沒有 launch 紀錄 | 問 `get_run` | `su` 是 null（不是 0）、`twd_nstc` 與 `twd_academic` 是 null、`unknown_reasons` 的內容是「這個 run 的紀錄沒有保存每個 task 的 cpus、realtime 與分區 …」、`site` 是 `taiwania3` | 自動：`test_get_run_su_is_null_with_reason_for_an_old_run` |
| TC-021 | 裁決 7 | 例外 | 同 TC-020，但這個 run 有一筆 launch 紀錄，用的 CE 設了 `suSite: nano4` | 問 `get_run` | `su` 仍是 null 並有原因；`site` 是 `nano4`（不是 taiwania3） | 自動 |
| TC-022 | 作法 3；作法 9；失敗先行測試 5 | 例外 | 手工做一份沒有 `task_usage` 這張表的舊 index（唯讀開啟），裡面有一個已結束的 run | 問 `get_run` | 不崩、不報錯；`su.su` 是 null 並有原因 | 自動：`test_old_index_without_the_table_reads_as_unknown` |
| TC-023 | 作法 3（部分有列也回清單，缺欄的判 unknown）；維護者原話③ | 例外 | 一個已結束的 run，兩個 task 都有列，其中一個的 cpus 是 NULL（另一個資料完整） | 問 `get_run` | 整個 run 的 `su`、`twd_nstc`、`twd_academic` 都是 null（不是只加完整那個的部分和）；`unknown_reasons` 指出是哪個 task 缺 cpus | 自動 |
| TC-024 | 作法 3；維護者原話③ | 例外 | 一個已結束的 run，其中一個 task 的 realtime 是 NULL，另一個 task 的 queue 是 NULL（本機執行） | 問 `get_run` | 整個 run 的三個數字都是 null；原因分別說缺 realtime、該分區沒有 SU 係數 | 自動 |
| TC-025 | 裁決 6（還沒結束的 run 不給數字） | 例外 | 一個正在跑（`running`）的 run，已有幾個 COMPLETED task 的列 | 問 `get_run` | `su`、`twd_nstc`、`twd_academic` 都是 null，`unknown_reasons` 恰好等於 `["run 還沒結束，SU 等它結束後再算 (the run has not ended)"]`；不給「到目前為止的合計」 | 自動：`test_running_run_has_no_su_number` |
| TC-026 | 裁決 6 | 例外 | 一個狀態是 `lost`（太久沒回報）的 run，有幾列用量 | 問 `get_run` | 同 TC-025：三個數字 null、原因恰好是同一句 | 自動 |
| TC-027 | 裁決 6（成功數對不上） | 例外 | 一個已結束的 run，`tasks.succeeded` 是 3，但 `task_usage` 只有 2 列 COMPLETED | 問 `get_run` | 三個數字都是 null；原因是「有 1 個成功的 task 沒有用量紀錄 (1 succeeded tasks have no usage record)」（數字是缺的個數） | 自動：`test_missing_usage_rows_make_su_unknown` |
| TC-028 | 作法 6（找不到 run 的回傳形狀不變） | 例外 | 要問的 run id 不存在 | 問 `get_run` | 回傳 `found: false`、`id`、「Run not found: … (找不到這個 run)」，沒有 `su` 鍵 | 自動 |
| TC-029 | 作法 6；失敗先行測試 8；專長守則（跨使用者） | 例外 | 使用者 A 的 run，已結束且有完整用量列；使用者 B 的身分 | B 問 A 的 run 的 `get_run` | 與現在一樣是「找不到」的形狀，沒有 `su` 鍵，看不到任何 A 的數字 | 自動：`test_another_users_run_has_no_su` |
| TC-030 | 裁決 4（費率檔讀不到時 site 是 None） | 例外 | 費率檔讀不到（壞掉或不存在），一個已結束且有用量列的 run | 問 `get_run` | 三個數字 null；`site` 是 null；`unknown_reasons` 說費率檔讀不到；不崩 | 自動 |

## User Story 3 — 用量算到對的站點（suSite）（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 作法 4；失敗先行測試 3 | 功能 | platform.db 裡該 run 的 launch 紀錄用的 CE 設了 `suSite: nano4` | 呼叫 `su.site_of_run` | 回 `nano4` | 自動 |
| TC-041 | 作法 5 | 功能 | repo 的 `configs/sites/nchc-nano4-ce.json` | 讀檔並用 CE 驗證跑一遍 | 檔裡有 `"suSite": "nano4"`，且驗證通過 | 自動 |
| TC-042 | 作法 4（該 run 最新一筆 launch 的 ce） | 功能 | 同一個 run 有兩筆 launch：舊的用沒設 suSite 的 CE，新的用 `suSite: nano4` 的 CE | 呼叫 `su.site_of_run` | 回 `nano4`（取最新一筆） | 自動 |
| TC-043 | 裁決 2（suSite 不進 snapshot） | 功能 | 一個設了 `suSite: nano4` 的 CE | 取這個 CE 送給站台代理用的 snapshot | snapshot 裡沒有 `suSite` | 自動 |
| TC-044 | 裁決 1（避免循環 import） | 功能 | 全新的 Python 程序 | 依序 `import abf_platform.su`、`import abf_platform.compute_envs`，再驗證一個設了 suSite 的 CE | 不出現 ImportError，驗證正常 | 自動 |
| TC-045 | 作法 4；失敗先行測試 6 | 例外 | CE 沒有設 `suSite` | 呼叫 `su.site_of_run` / 問 `get_run` | `site` 是費率檔的 `default_site`，即 `taiwania3` | 自動：`test_site_falls_back_to_default_without_suSite` |
| TC-046 | 作法 4 | 例外 | 該 run 在 platform.db 沒有任何 launch 紀錄 | 呼叫 `su.site_of_run` | 回 `taiwania3`（`default_site`） | 自動 |
| TC-047 | 作法 4 | 例外 | launch 紀錄裡的 CE 已被刪掉（找不到） | 呼叫 `su.site_of_run` | 回 `taiwania3`，不丟例外 | 自動 |
| TC-048 | 裁決 5 | 例外 | platform.db 檔不存在（或打不開） | 呼叫 `su.site_of_run`（也經 `estimate_su`） | 回 `taiwania3`，不丟例外 | 自動 |
| TC-049 | 作法 5；失敗先行測試 7；專長守則（錯誤訊息） | 例外 | 一個 CE 設 `suSite: "nowhere"` | 驗證這個 CE | 驗證失敗；訊息含 `suSite`、「費率檔沒有站點 nowhere」與可用站點清單（taiwania3、nchc、nano4）及英文 `no such site in configs/sites/su_rates.json` | 自動：`test_suSite_must_name_a_site_in_the_rates_file`；另在 `platform/tests/test_station_envs.py` 加驗證測試 |
| TC-050 | 裁決 1（費率檔讀不到時的訊息） | 例外 | 一個 CE 設了 `suSite: "nano4"`，但費率檔讀不到 | 驗證這個 CE | 驗證失敗；訊息是「suSite: 費率檔讀不到，無法確認站點 nano4 (the rates file cannot be read)」 | 自動：`platform/tests/test_station_envs.py` |
| TC-051 | 作法 5（一次列出全部錯誤的既有寫法） | 例外 | 一個 CE 同時有壞的 `suSite` 與另一個既有的錯誤（例如 workDir 不是文字） | 驗證這個 CE | 一次回報兩個錯誤，不是只報第一個 | 自動：`platform/tests/test_station_envs.py` |

## User Story 4 — 文件與手動驗收照新做法（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 完成標準（手動）；維護者原話①（10-21 裁示） | 功能 | 平台已連到 Claude Desktop；有一個 nano4 上由本平台送出且已結束的 run（例如 `ampliseq-mt-0920-r2`） | 在 Claude Desktop 打「get_run ampliseq-mt-0920-r2」 | 回答裡有 `su` 一整段：SU 數字與三種台幣（nstc、academic、industry）；若算不出就是 `su: null` 加 `unknown_reasons`，不是亂給數字 | 手動：`docs/TESTING.md` TC-048n 第 1 步 |
| TC-061 | 作法 8 | 功能 | `docs/TESTING.md` TC-048n 第 1 步 | 讀這一步 | 改成「在 Claude Desktop 問 `get_run ampliseq-mt-0920-r2`（或最近一次同設定、由本平台送出的 run），把回答裡的 `su` 整段貼進表格；`su` 是 null 就寫 unknown 加 `unknown_reasons`」；「它不是 MCP 工具…在 WSL 用 python -c」那一段與那行 python 指令都已刪掉 | 手動：讀 `docs/TESTING.md`（TC-048n 第 1 步） |
| TC-062 | 範圍；裁決 3 | 功能 | `specs/007b-launch/acceptance-nano4.md` 的「launch 前預估 SU」那一格 | 讀該格，並跑 `bash tests/docs_nano4_acceptance.sh` | 表頭字樣「launch 前預估 SU」還在；括號裡的說明改成「Claude Desktop 問 get_run 前一次同設定 run 的 su」；那支測試不改一個字也通過 | 自動：`tests/docs_nano4_acceptance.sh`（格內說明文字由驗收者讀檔確認） |
| TC-063 | 作法 8 | 功能 | `docs/PLATFORM.md` | 讀 `get_run` 說明處與 CE 鍵表 | `get_run` 說明處有一句說明 `su`；CE 鍵表有 `suSite`（值必須是費率檔裡有的站點） | 手動：驗收者讀 `docs/PLATFORM.md` |
| TC-064 | 範圍（`specs/estimate-su/ledger.md` 第 11、12 行） | 功能 | `specs/estimate-su/ledger.md` 「欠」那兩條（receiver 沒保存 task、MCP 工具） | 讀這兩條 | 兩條都改成已補，並寫出本任務 id `estimate-su-mcp`；其他「欠」不被改動 | 手動：驗收者讀檔 |
| TC-065 | 測試不准動的清單 | 功能 | `tests/platform_storage_doc_test.sh` 第 140-142 行釘住的字樣 | 跑該測試 | 通過；「seven read-only tools」「Twelve tools.」字樣仍在文件裡 | 自動：`tests/platform_storage_doc_test.sh` |

## User Story 5 — 計畫明講這次不做的事

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 不做：不新增 MCP 工具；失敗先行測試 9 | 不在範圍 | MCP 伺服器 | 列出工具名 | 恰好是原本的 12 個，與 `test_estimate_su.py::test_tc029` 同一組；沒有 `estimate_su` 工具；`test_pat.py`、`test_oauth_mcp.py` 的工具數斷言不動且通過 | 自動：`test_tool_list_unchanged` |
| TC-071 | 不做：不加網頁路由或畫面 | 不在範圍 | 網頁伺服器的路由 | 跑 `test_estimate_su.py`（TC-030 沒有 su 網頁路由）與 `test_web_parity.py`（OWED 只准變短） | 都不改一個字也通過；沒有新的網頁路由；`site_of_run` 在 `su.py`，不是公開動作 | 自動：`platform/tests/test_estimate_su.py`、`platform/tests/test_web_parity.py` |
| TC-072 | 不做：不改 `list_runs` | 不在範圍 | 有已結束且有用量列的 run | 呼叫 `list_runs` | 每一列都沒有 `su` 鍵，形狀與現在相同 | 自動 |
| TC-073 | 不做：不改 `rebuild.py` | 不在範圍 | 用 `rebuild.py` 從 `trace.txt` 重建出一個 run | 問 `get_run` | `su` 為 null 並有原因（重建的 run 沒有 task 用量列，照舊回 unknown）；`rebuild.py` 沒被改 | 自動 |
| TC-074 | 不做：不做月總計的畫面、`month_total` 不改 | 不在範圍 | 既有月總計測試 | 跑 `test_estimate_su.py` | 不改一個字也通過；`month_total` 的行為與現在相同 | 自動：`platform/tests/test_estimate_su.py` |
| TC-075 | 不做：不做雲端費用；維護者原話②（估算，不是帳單） | 不在範圍 | TC-010 的 `get_run` 回答 | 看 `su` 的內容 | 沒有任何雲端費用欄位，沒有 `bill`、`cloud` 之類的鍵；只有 TC-012 列的鍵 | 自動 |

## 憲法與安全網

這個變更碰到：憲法第 9 條（數字要來自檔案、缺口要明寫）、developer 專長守則（backend：對等性、跨使用者、唯讀不寫入、錯誤訊息、migration）、工作流程規則（新檔檔首標頭、不准弱化既有測試）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | 第 9 條：數字來自檔案，不是寫死 | 功能 | TC-010 的 run | 把某個 task 的 realtime_ms 改掉再問一次 `get_run` | `su` 跟著算出新數字（可由 cpus × 小時 × 係數 手算對上），不是固定值 | 自動 |
| TC-081 | 專長守則：對等性（動作清單與動作層函式清單一一對應） | 功能 | `test_web_parity.py` | 不改一個字，跑它 | 通過；沒有新的公開動作名；網頁與 MCP 的 `get_run` 走同一個動作層函式 | 自動：`platform/tests/test_web_parity.py` |
| TC-082 | 專長守則：確認管道／讀不寫（`get_run` 是讀取，不改資料） | 功能 | 一份沒有 `task_usage` 表的舊 index 檔 | 問 `get_run`，之後比對檔案 | 檔案內容沒變，沒有在唯讀路徑建表；`su`／`status` 只讀 | 自動 |
| TC-083 | 專長守則：錯誤訊息與日誌 | 例外 | TC-020、TC-022、TC-025、TC-027、TC-030 的各種 unknown 回答 | 檢查每個 `unknown_reasons` 的字串 | 說明發生什麼事；不含檔案系統路徑、SQL、堆疊，也不含 token／密鑰 | 自動 |
| TC-084 | 專長守則：migration（計畫寫「不需要 migration」，要驗證理由成立）；作法 9 | 功能 | 一份已有 run 與 task 計數、但沒有 `task_usage` 表的既有 index | 接收器（`store.connect`）開啟它，再開一次 | 第一次開啟後有 `task_usage` 表，既有的 run／計數／failed_tasks 內容不變；第二次開啟不出錯 | 自動 |
| TC-085 | 工作流程規則：新檔檔首與路徑 | 功能 | 新增的 `.py` 檔（含 `test_su_in_get_run.py`）與新增文件 | 跑 `platform/tests/test_scope.py` 與 `tests/no_hardcoded_paths.sh` | 新 `.py` 檔前 40 行內有 `# Nothing existing: <理由，≥15 字>`；新測試與文件沒有 `/work/<真實帳號>/` 形式的路徑（用 `<site_user>`） | 自動：`platform/tests/test_scope.py`、`tests/no_hardcoded_paths.sh` |
| TC-086 | 工作流程規則：不准弱化既有測試 | 功能 | 這次變更對既有測試檔的差異 | 對照 base 比較 | `test_actions_layer.py` 只有 `BASELINE` 裡 `get_run` 的 description 一筆改變；`test_station_envs.py` 只多了 suSite 的測試、既有斷言不動；`test_estimate_su.py`、`test_pat.py`、`test_oauth_mcp.py`、`test_web_parity.py` 不動 | 自動：全套測試＋驗收者比對 diff |
| TC-087 | 工作流程規則：完成標準 | 功能 | 完成後的 HEAD | 在 WSL 跑全套 `tests/run_all.sh` | 全綠（含上面九個失敗先行測試加兩個新增測試） | 自動：`tests/run_all.sh` |
