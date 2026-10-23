# 測試案例：SU 費率檔打包進平台自己的 data/；補強 estimate-su-mcp 的四條鬆測試（su-followups）

**規格**：`specs/su-followups/plan.md`（本任務沒有獨立 spec.md，計畫含「目標」「裁決」「裁決二」「裁決三」，即規格；「裁決二」明寫取代「目標 1」）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應（拒絕、提示、停下、說不知道）。
- **不在範圍**：計畫「不做」那一節明講這次不做的事；測試確認它真的沒做。

名詞：**SU** ＝國網的計算點數；**費率檔** ＝ `configs/sites/su_rates.json`，記每個分區的係數與每 SU 的台幣價；**wheel** ＝ `pip install` 用的安裝包檔（解開就是一個資料夾）；**checkout** ＝直接從 git 倉庫跑、沒有安裝；**`-I` 獨立 Python** ＝加了 `-I` 旗標的 Python，不讀環境變數與目前資料夾，只看測試自己塞進去的路徑，用來證明「只靠安裝包本身就找得到」；**NOT_STORED 那句** ＝「這個 run 的紀錄沒有保存每個 task 的 cpus、realtime 與分區 (the run record does not keep each task's cpus, realtime and partition)」；**RUN_ENDED 那句** ＝「run 還沒結束，SU 等它結束後再算 (the run has not ended)」；**TWO / `_world`** ＝ `platform/tests/test_su_in_get_run.py` 既有的造資料寫法（nano4 站點、兩個成功 task，SU 2.0）。

「自動」的測試：打包相關寫在新檔 `platform/tests/test_su_packaged.py`，其餘寫在 `platform/tests/test_su_in_get_run.py`，除非另行註明；每條測試要在註解裡寫出自己的 TC 編號。計畫的兩個失敗先行測試名稱照用：`test_su_packaged.py::test_rates_found_in_the_wheel_data`（TC-001 至 TC-004）與 `test_checkout_still_uses_repo_configs`（TC-005）。

計畫沒有「維護者原話」（計畫明寫：來源是 PR #171 閱卷的「放水」清單與 #170 ledger 的「欠」），所以沒有逐字範例可對；以下每條都來自計畫的目標、裁決、失敗先行測試與不做。

## User Story 1 — 費率檔跟著安裝包走，裝完照樣讀得到（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標 1；裁決二 3、4（wheel 內有 `abf_platform/data/su_rates.json` 且逐位元相同） | 功能 | 把倉庫（含 `configs/sites/su_rates.json`）複製到暫存夾，用 `pip wheel` 建出 wheel 並解開 | 在解開的資料夾找 `abf_platform/data/su_rates.json` | 檔案存在；內容與倉庫 `configs/sites/su_rates.json` 逐位元相同 | 自動：`test_su_packaged.py::test_rates_found_in_the_wheel_data` |
| TC-002 | 裁決二 3（與 017a 的 `data/*.json` 同一個資料夾；不能把原本的檔蓋掉） | 功能 | 同 TC-001 的 wheel | 找 `abf_platform/data/nf-core-modules.json` | 檔案還在，且與倉庫 `platform/abf_platform/data/nf-core-modules.json` 逐位元相同（新增的複製沒有清掉整個 data 資料夾） | 自動 |
| TC-003 | 失敗先行測試 1（`-I` 獨立 Python 讀得到費率，nano4 的 `twd_per_su` 存在） | 功能 | 同 TC-001 的 wheel 解開夾；先確認從這個資料夾往上兩層找不到任何 `configs/sites/su_rates.json`（否則等於沒隔離，測試要先斷言這點） | 用 `python -I -c ...`，只把解開夾塞進 `sys.path`，匯入 `abf_platform.su` 並呼叫 `load_rates()` | 不報錯；回傳的不是 None；`sites.nano4.twd_per_su` 存在，且與倉庫費率檔裡 nano4 那段相同 | 自動：`test_rates_found_in_the_wheel_data` |
| TC-004 | 裁決三 8（`su.RATES_PATH` ＝實際要讀的那個路徑） | 功能 | 同 TC-003 的獨立 Python | 印出 `su.RATES_PATH` | 等於解開夾裡的 `abf_platform/data/su_rates.json`（不是 repo 路徑） | 自動：`test_rates_found_in_the_wheel_data` |
| TC-005 | 目標 1（沒有 data 檔就退回 repo）；失敗先行測試 2 | 功能 | 直接從這個 checkout 跑；`platform/abf_platform/data/su_rates.json` 不存在（測試先斷言這點） | 用 `-I` 獨立 Python 把 `platform/` 塞進 `sys.path`，匯入 `abf_platform.su`，看 `RATES_PATH` 並呼叫 `load_rates()` | `RATES_PATH` 等於 repo 的 `configs/sites/su_rates.json`；`load_rates()` 不是 None，`sites.nano4.twd_per_su` 存在 | 自動：`test_su_packaged.py::test_checkout_still_uses_repo_configs` |
| TC-006 | 裁決二 3（先讀 `data/`，沒有再退回 repo）；裁決三 8 | 功能 | 暫存夾裡複製一份 `abf_platform` 套件，旁邊放 repo 形狀的 `configs/sites/su_rates.json`（內容 A），同時在套件的 `data/` 放一份內容不同的 `su_rates.json`（內容 B，例如 `default_site` 不同） | 用 `-I` 獨立 Python 匯入該套件的 `abf_platform.su`，看 `RATES_PATH` 與 `load_rates()` | `RATES_PATH` 指向 `data/` 那份；`load_rates()` 回的是內容 B，不是 A | 自動 |
| TC-007 | 裁決三 8（兩處都沒有也不能讓匯入崩掉）；`su.py` 既有「讀不到就回 None」 | 例外 | 暫存夾裡只有 `abf_platform` 套件，沒有 `data/su_rates.json`，往上兩層也沒有 `configs/` | 用 `-I` 獨立 Python 匯入 `abf_platform.su`，呼叫 `load_rates()` | 匯入不出錯；`load_rates()` 回 None | 自動 |
| TC-008 | 裁決三 8（`load_rates()` 只讀 `RATES_PATH`） | 例外 | `data/su_rates.json` 存在（用 TC-006 的暫存夾，或 wheel 解開夾）；把 `su.RATES_PATH` 用 monkeypatch 指到不存在的檔 | 呼叫 `su.load_rates()` | 回 None（沒有偷偷改讀 data 檔或 repo 檔） | 自動 |
| TC-009 | 裁決三 8（既有三條測試一字不改仍綠） | 例外 | `test_su_in_get_run.py` 的 TC-030 那條（`test_unreadable_rates_file_gives_null_site`）、TC-050 那條（`test_suSite_with_unreadable_rates_file`），以及 `test_station_envs.py` 約第 899 行把 `RATES_PATH` 指到不存在檔的那條 | 對照 base 確認這三條的內容沒被改，然後跑 | 三條都通過；斷言與 base 逐字相同（驗收者比對 diff） | 自動：這三條測試；diff 由驗收者確認 |
| TC-010 | 裁決二 4（找不到來源檔時建置失敗，跟 scripts／configs 一樣）；專長守則（錯誤訊息要說原因與處理） | 例外 | 暫存夾裡的 repo 複本缺 `configs/sites/su_rates.json`（`configs/sites/` 其他檔都在，scripts 與 skills 也都在） | 對它跑 `pip wheel` | 建置失敗（結束碼非 0）；輸出點名缺的是 `su_rates.json`，並說要從倉庫的 checkout 建置（與既有兩條「cannot find … build from a checkout of the repository」同樣的講法） | 自動 |
| TC-011 | 裁決二 4 | 例外 | 同 TC-010 | 看輸出資料夾 | 沒有產出任何 `.whl`（不會留下一個缺費率的安裝包） | 自動 |
| TC-012 | 裁決二 3（`.gitignore` 忽略 build 複製出的那份）；憲法第 9 條（數字只有一個來源） | 功能 | 這次變更後的 HEAD | 讀 `.gitignore`；跑 `git ls-files` 找 `su_rates.json`；跑 `git ls-files platform/abf_platform/data` | `.gitignore` 有一行恰好是 `platform/abf_platform/data/su_rates.json`；被 git 追蹤的 `su_rates.json` 只有 `configs/sites/su_rates.json` 一份；`nf-core-modules.json` 仍被追蹤（沒有被萬用字元誤傷） | 自動 |
| TC-013 | 裁決二 2、3、4（`su.py` 全文不得出現 station 字樣，含拆開的寫法） | 功能 | 變更後的 `platform/abf_platform/su.py` | 讀原始文字；用 `ast` 讀出所有字串常數（含 docstring、f-string 的字面部分）；對每一條陳述，把該陳述裡所有字串常數依出現順序接起來 | 原始文字不含 `station`（不分大小寫）；沒有任何字串常數含它；任何一條陳述接起來也不含它 | 自動：`test_su_packaged.py` |
| TC-014 | 裁決二 4（偵測規則要能變紅，否則等於沒查） | 例外 | 測試自己造的幾段小程式碼：`"sta" "tion"`、`"sta" + "tion"`、`"".join(["sta", "tion"])`、`"stat" + "ion"`，以及一段完全無關的程式碼 | 對每一段跑 TC-013 用的同一支檢查函式 | 前四段都被判為違規；無關那段不被判違規 | 自動 |
| TC-015 | 裁決二 2；憲法第 2 條相關的既有檢查（平台原始碼不得提到站台端） | 功能 | `platform/tests/test_scope.py` | 對照 base 確認它一個字沒被改，然後跑其中的 `test_tc061_no_ssh_no_scheduler_no_outgoing_connection_in_the_source` 與 `test_tc070_every_python_source_names_its_alternative` | 兩條都通過；`test_scope.py` 不在這次變更的檔案清單裡 | 自動：`platform/tests/test_scope.py`；diff 由驗收者確認 |
| TC-016 | 計畫範圍（新檔檔首標頭）；憲法第 1 條、第 3 條 | 功能 | 新檔 `platform/tests/test_su_packaged.py` | 讀檔首 40 行；跑 `platform/tests/test_scope.py::test_tc072_no_personal_or_cluster_paths` 與 `tests/no_hardcoded_paths.sh` | 前 40 行內有 `# Nothing existing: <理由，至少 15 個字>`；兩項路徑檢查通過（新測試沒有 `/work/<真實帳號>/` 之類的寫死路徑） | 自動：`platform/tests/test_scope.py`、`tests/no_hardcoded_paths.sh` |
| TC-017 | 裁決二 5（`test_guidance.py` 只限 `_copy_for_build`）；專長守則放水檢查 | 功能 | 既有打包測試：`test_guidance.py` 的 TC-404（wheel 內 skills 與倉庫相同）、TC-409、TC-410，以及 `test_station_packaging.py` 的 sp01、sp02、sp03、sp14、sp15、sp16 | 跑這些測試；對照 base 看 `test_guidance.py` 與 `test_station_packaging.py` 的差異 | 全部通過；若 `test_guidance.py` 有改，只改了 `_copy_for_build`，沒有任何斷言被刪除、放寬或跳過；`test_station_packaging.py` 沒被改 | 自動：這些測試；diff 由驗收者確認 |
| TC-018 | 裁決二 3（package-data 已含 `data/*.json`，pyproject 不用改） | 功能 | `platform/pyproject.toml` | 對照 base；跑 `test_guidance.py` 的 TC-406、TC-407 | `pyproject.toml` 沒被改；兩條通過（package-data 那一行與 packages 清單都沒變） | 自動：`platform/tests/test_guidance.py`；diff 由驗收者確認 |

## User Story 2 — 補強 estimate-su-mcp 閱卷指出的四條鬆測試（優先度 P1）

四條鬆測試指 `test_su_in_get_run.py` 裡原本對應 estimate-su-mcp 的 TC-014（只列工具名、沒真的呼叫）、TC-083（只檢查 TC-020 一種原因）、TC-073（只造一個沒用量列的 run、沒走 `rebuild.py`）、TC-048（直接呼叫 `site_of_run`、沒經 `estimate_su`）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 目標 2：TC-014（真的經 MCP 的 `get_run` 呼叫一次，斷言回傳含 `su`） | 功能 | 用 `_world` 造 nano4、TWO 兩個成功 task 的 run；用 `build_server(db, plat)` 建 MCP 伺服器（in-process，與 `test_actions_layer.py` 的 `asyncio.run(server.call_tool(...))` 同一種呼叫法） | 呼叫 `call_tool("get_run", {"run_id": "id-run-a"})` | 回傳內容含 `su` 這一段，裡面 `su` ≈ 2.0、`twd_nstc` ≈ 0.2、`twd_academic` ≈ 0.4、`twd` ＝ {nstc 0.2、academic 0.4、industry 0.74}、`unknown_reasons` 為空、`site` 是 `nano4`（不能只斷言工具名存在） | 自動：`test_su_in_get_run.py`（取代 `test_mcp_get_run_is_the_same_action`） |
| TC-021 | 目標 2：TC-014；原 TC-014 預期（MCP 與動作層的 `su` 相同） | 功能 | 同 TC-020 | 把 MCP 回傳的 `su` 與直接呼叫 `actions.get_run` 得到的 `su` 比 | 兩者完全相同（浮點用近似比較） | 自動 |
| TC-022 | 目標 2：TC-083（五種 unknown 之一：舊 run 沒有任何用量列，原 TC-020） | 例外 | `_world(usage=(), launch=False)`，已結束、成功數大於 0 | 問 `get_run`，取 `su.unknown_reasons` | 清單不是空的；第一句以 NOT_STORED 那句開頭；每一句都不含：檔案系統路徑（含測試實際使用的暫存夾路徑字串、反斜線或斜線開頭的路徑形狀、`.db`）、SQL 字樣（`SELECT`、`INSERT`、`WHERE`、`sqlite`、`task_usage`、`OperationalError`，不分大小寫）、`Traceback`、`token`、`Bearer`（不分大小寫） | 自動：`test_get_run_su_is_null_with_reason_for_an_old_run`（斷言只准加嚴） |
| TC-023 | 目標 2：TC-083（五種之二：舊 index 沒有 `task_usage` 這張表，原 TC-022） | 例外 | 把 `task_usage` 表 DROP 掉的舊 index | 問 `get_run`，取 `su.unknown_reasons` | 不崩；`su.su` 為 null；清單不是空的；每一句同 TC-022 的「不含」清單；原本「檔案位元組不變、沒有建表」的斷言保留 | 自動：`test_old_index_without_the_table_reads_as_unknown`（斷言只准加嚴） |
| TC-024 | 目標 2：TC-083（五種之三：還在跑的 run，原 TC-025） | 例外 | `status="running"` 且有用量列的 run | 問 `get_run`，取 `su.unknown_reasons` | 恰好等於 `["run 還沒結束，SU 等它結束後再算 (the run has not ended)"]`（逐字寫在測試裡）；且這一句不含 TC-022 的「不含」清單 | 自動：`test_running_run_has_no_su_number`（斷言只准加嚴；`lost` 那個參數也保留） |
| TC-025 | 目標 2：TC-083（五種之四：成功數對不上，原 TC-027） | 例外 | 已結束，`tasks.succeeded` 是 3，只有 2 列 COMPLETED | 問 `get_run`，取 `su.unknown_reasons` | 恰好等於 `["有 1 個成功的 task 沒有用量紀錄 (1 succeeded tasks have no usage record)"]`；這一句不含 TC-022 的「不含」清單 | 自動：`test_missing_usage_rows_make_su_unknown` |
| TC-026 | 目標 2：TC-083（五種之五：費率檔讀不到，原 TC-030） | 例外 | 把 `su.RATES_PATH` 指到暫存夾裡不存在的 `missing.json`；已結束且有用量列的 run | 問 `get_run`，取 `su.unknown_reasons` 與 `site` | `su.su` 為 null、`site` 為 null；原因含「費率檔讀不到」；每一句都不含 `missing.json` 的實際路徑與暫存夾路徑，也不含 TC-022 的其他「不含」項目 | 自動：`test_unreadable_rates_file_gives_null_site`（斷言只准加嚴） |
| TC-027 | 目標 2：TC-083（檢查本身要能變紅） | 例外 | 測試自己造的壞原因字串：含實際暫存夾路徑的一句、含 `SELECT * FROM task_usage` 的一句、含 `Traceback (most recent call last)` 的一句、含 `token abc` 的一句，以及一句乾淨的 | 對每一句跑 TC-022 至 TC-026 共用的那支「不含」檢查函式 | 前四句都被判違規；乾淨那句不被判違規 | 自動 |
| TC-028 | 目標 2：TC-073；裁決三 7（走 `rebuild.py` 重建後問 `get_run`，原因是 NOT_STORED 那句） | 例外 | 造一個最小的 launch 資料夾（歷史紀錄＋log＋`trace.txt`，成功的 task 大於 0，run 已結束），**真的呼叫 `rebuild.rebuild(...)`** 重建 index（不是手工塞 `runs` 列）；先斷言重建出的 run 的 `source` 是 `rebuild`、`tasks.succeeded` 大於 0、`task_usage` 沒有該 run 的任何列 | 問該 run 的 `get_run` | `su.su`、`twd_nstc`、`twd_academic` 都是 null；`unknown_reasons` 恰好等於 `["這個 run 的紀錄沒有保存每個 task 的 cpus、realtime 與分區 (the run record does not keep each task's cpus, realtime and partition)"]`（整句逐字寫在測試裡，不是 import `su.NOT_STORED` 來比） | 自動：`test_a_run_without_usage_rows_stays_unknown` 改寫成走 `rebuild` |
| TC-029 | 裁決三 7（不是「有 N 個成功的 task 沒有用量紀錄」那句） | 例外 | 同 TC-028 | 看同一個 `unknown_reasons` | 不含「沒有用量紀錄」「succeeded tasks have no usage record」字樣 | 自動 |
| TC-030 | 目標 2：TC-048（經 `actions.estimate_su` 走一次 `site_of_run` 的判斷）；原 TC-048（platform.db 不存在 → `taiwania3`） | 功能 | `index.db` 裡有一個已結束的 run，成功 1 個 task：cpus 4、realtime 7,200,000 毫秒、queue `ct56`；`platform_path` 給一個不存在的檔；不帶 caller（本機直接呼叫，與 MCP 本機模式相同——帶 caller 時查不到擁有者會答「找不到」） | 呼叫 `actions.estimate_su(db, "run-a", platform_path=<不存在的檔>)`，不指定 site | 不丟例外；`su` ≈ 8、`twd_nstc` ≈ 0.64（只有 `taiwania3` 認得 `ct56`，nano4 不認得，所以這兩個數字證明站點判成了預設的 `taiwania3`）；沒有 `twd` 鍵 | 自動：取代只呼叫 `su.site_of_run` 的 `test_site_of_run_without_a_platform_db_is_the_default` 的 estimate 部分（原本直接呼叫的斷言保留） |
| TC-031 | 目標 2：TC-048（platform.db 打不開的那一半） | 例外 | 同 TC-030，但 `platform_path` 給一個內容是亂碼、根本不是資料庫的檔 | 呼叫 `actions.estimate_su(...)`，不指定 site | 不丟例外；`su` ≈ 8、`twd_nstc` ≈ 0.64（同 TC-030，證明判成 `taiwania3`） | 自動 |
| TC-032 | 失敗先行測試（四條補強各自先證明「把被測的那一段弄壞會紅」，在 ledger 記下怎麼證明的） | 功能 | `specs/su-followups/ledger.md` | 讀檔，逐條對照 TC-014、TC-083、TC-073、TC-048 四條 | 四條各有一段：弄壞了哪一段（例如：MCP 的 `get_run` 不回 `su`；讓某個 unknown 原因帶出路徑；讓 `rebuild` 路徑改成別句原因；讓 `estimate_su` 不經 `site_of_run`）、弄壞後哪條測試變紅（測試名與失敗訊息）、還原後轉綠；不是只寫「已驗證」三個字 | 手動：驗收者讀 `specs/su-followups/ledger.md` |

## User Story 3 — 計畫明講這次不做的事

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 不做：不改計費公式 | 不在範圍 | 既有 `platform/tests/test_estimate_su.py` 與 `test_su_in_get_run.py` 的 `test_get_run_has_su_for_a_nano4_run`、`test_default_site_run_has_no_twd_key` | 對照 base 確認 `test_estimate_su.py` 一個字沒被改，然後跑 | 全部通過；nano4 的 TWO 仍是 2.0 SU、0.2／0.4／0.74 元；`su_of_tasks`、`_factor_of`、`run_su`、`month_total` 的程式沒有被改（驗收者比對 `su.py` 的 diff：只動 `RATES_PATH` 的決定與說明文字） | 自動：`platform/tests/test_estimate_su.py`；diff 由驗收者確認 |
| TC-041 | 不做：不改 `get_run` 形狀 | 不在範圍 | TC-010／TC-011 那兩個 run（nano4 與預設站點） | 看 `su` 的鍵；跑 `test_actions_layer.py` | `su` 的鍵仍是固定五個，nano4 多一個 `twd`，沒有其他鍵；`test_actions_layer.py` 沒被改且通過（`get_run` 那筆工具說明與 base 相同） | 自動：`test_get_run_has_su_for_a_nano4_run`、`test_default_site_run_has_no_twd_key`、`platform/tests/test_actions_layer.py` |
| TC-042 | 不做：不改 receiver | 不在範圍 | 這次變更的 diff | 看有沒有動 `platform/abf_platform/receiver.py`、`store.py` | 兩個檔都不在 diff 裡；`test_su_in_get_run.py` 裡 TC-001 至 TC-007 的接收器測試與 base 逐字相同且通過 | 手動：驗收者比對 diff，並跑 `test_su_in_get_run.py` |
| TC-043 | 不做：不改 `rebuild.py`（TC-073 只是走它，不改它） | 不在範圍 | 這次變更的 diff | 看有沒有動 `platform/abf_platform/rebuild.py` | 不在 diff 裡；重建不會因此多寫 `task_usage` 列（TC-028 已證明） | 手動：驗收者比對 diff |
| TC-044 | 裁決 1（不需要 migration）；專長守則（資料結構有變動才需要 migration） | 不在範圍 | 這次變更的 diff | 看有沒有動資料表結構（`store.py` 的 `SCHEMA`）、新增 migration 檔 | `store.py` 不在 diff 裡、沒有新增 migration；沒有任何表或欄位變動（只是複製一份費率檔） | 手動：驗收者比對 diff |
| TC-045 | 計畫「範圍：檔案」與裁決二 5 | 不在範圍 | 這次變更對 base 的檔案清單（`git diff --name-only <base>...HEAD`） | 逐檔對照允許清單 | 只出現：`platform/abf_platform/su.py`、`platform/tests/test_su_in_get_run.py`、`platform/tests/test_su_packaged.py`、`platform/setup.py`、`.gitignore`、`platform/tests/test_guidance.py`（若有，只限 `_copy_for_build`）、`specs/su-followups/` 底下的檔；沒有 `compute_envs.py`、`actions/`、`mcp_server.py`、`receiver.py`、`store.py`、`rebuild.py`、`pyproject.toml`、`test_scope.py`、docs、`specs/` 其他任務的檔（含 `specs/estimate-su-mcp/`、`specs/station-packaged-scripts/ledger.md`）；`plan.md` 與 `test-case*.md` 在實作期間沒被改 | 手動：驗收者比對 diff |
| TC-046 | 專長守則放水檢查；工作流程（不准弱化既有測試） | 不在範圍 | `platform/tests/test_su_in_get_run.py` 對 base 的差異 | 逐條比對除了 TC-014、TC-083、TC-073、TC-048 四條以外的測試 | 其他測試逐字相同；四條只有變嚴（斷言變多或變強），沒有任何斷言被刪除、放寬、改成配合新輸出或被 skip；四條原本的斷言仍保留 | 手動：驗收者比對 diff |

## 憲法與安全網

這個變更碰到：憲法第 1 條（新檔檔首標頭）、第 2 條（平台原始碼不提站台端；index 可重建）、第 3 條（不寫死路徑）、第 9 條（數字來自一個檔、不複製進程式）、backend 專長守則（跨使用者、對等性、讀不寫、錯誤訊息與日誌）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 專長守則：跨使用者（讀；本任務沒有新增或改動任何寫入動作，所以「寫」那條不適用） | 例外 | 使用者 A 的已結束 run，有完整用量列；使用者 B 的身分 | B 問 A 的 run 的 `get_run` | 與現在一樣是「找不到」的形狀，沒有 `su` 鍵，看不到 A 的任何數字；`test_another_users_run_has_no_su` 與 base 逐字相同且通過 | 自動：`test_another_users_run_has_no_su` |
| TC-051 | 專長守則：對等性（動作清單與動作層函式清單一一對應） | 功能 | `test_web_parity.py`、`test_actions_layer.py` | 對照 base 確認沒被改，然後跑；並列出 MCP 工具名 | 兩個檔都通過；工具仍恰好是原本的 12 個，沒有新增 `estimate_su` 工具或任何新動作名 | 自動：`platform/tests/test_web_parity.py`、`platform/tests/test_actions_layer.py`、`test_tool_list_unchanged` |
| TC-052 | 專長守則：讀不寫、確認管道（`get_run` 是讀取；沒有新增寫入路徑） | 功能 | `su.py` 對 base 的 diff | 找新增的 `INSERT`、`UPDATE`、`DELETE`、`CREATE TABLE`、檔案寫入、`mkdir` | 沒有；`su.py` 新增的只有決定 `RATES_PATH` 的那幾行（讀檔路徑判斷）與說明文字 | 手動：驗收者比對 diff |
| TC-053 | 憲法第 9 條：數字來自檔案，不寫死 | 功能 | `su.py` 對 base 的 diff | 找新增的費率數字（`0.08`、`0.16`、`0.1`、`0.37` 等）、分區名（`ngs`、`ct56`、`big-mem`）、站點名 | 沒有；程式裡仍沒有任何費率或分區係數，全部來自費率檔 | 手動：驗收者比對 diff |
| TC-054 | 憲法第 3 條：沒有個人或叢集路徑 | 功能 | 這次變更後的 `platform/`（含新測試）與 `setup.py` | 跑 `tests/no_hardcoded_paths.sh` 與 `test_scope.py::test_tc072_no_personal_or_cluster_paths` | 兩項都通過；新增的程式與測試路徑都從 `__file__`、`REPO_ROOT`、`tmp_path` 推導 | 自動：`tests/no_hardcoded_paths.sh`、`platform/tests/test_scope.py` |
| TC-055 | 工作流程規則：完成標準（全套綠） | 功能 | 完成後的 HEAD | 在 WSL 跑全套 `tests/run_all.sh`（不是 Git Bash）；驗收者另查完成記號 `GREEN <HEAD sha>` 與工作樹乾淨 | 全綠，包含新檔 `test_su_packaged.py` 與被加強的四條 | 自動：`tests/run_all.sh` |
