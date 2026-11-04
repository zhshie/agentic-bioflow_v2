# 測試案例：送出可選 Config profiles（test 免樣本表）

**規格**：`specs/launch-test-profile/plan.md`（B 級，沒有獨立 spec.md；計畫即規格）　**總覽**：`test-case-overview.md`

名詞：「profile」就是 Nextflow pipeline 自己設定檔裡一組命名的設定；`test` 這個 profile 會讓 pipeline 用內建的測試資料跑。「樣本表」是使用者自己準備的資料清單。「預檢」是在環境頁對 nano4 跑的一次檢查，會記下每個已安裝 pipeline 有哪些 profile 名稱（`site_profiles`）。「head 指令」是最後送去叢集的那一行 nextflow 指令。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

維護者原話（2026-11-03）：「我希望至少做到已經可以透過MCP以及網頁跑nano4上面所有已安裝的pipline (用內建測試Sample)，而不是僅限於ampliconseq跟rnaseq。」本片只做 MCP 與底層；網頁那半依計畫「不做」留給後續片，見 TC-069。

自動測試的主檔：`platform/tests/test_launch_profiles.py`（下稱「新測試檔」）。每條自動測試須在註解寫上它的 TC 編號。

## User Story 1 — 帶 `test` profile、不給樣本表也能提出送出（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；作法「輸入來源」；失敗先行測試 1 | 功能 | 假站台已裝一個 pipeline，其 `nextflow.config` 有 `profiles { test {…} test_full {…} }`；該環境的預檢已記下這兩個名稱 | 透過 MCP `launch` 送出，`profiles=["test"]`，不給樣本表 | 回覆是「已提出」（等本人確認），不是錯誤，也沒有要求補樣本表 | 自動：新測試檔 `test_test_profile_launch_without_samplesheet_is_proposed`（改前須為紅） |
| TC-002 | 作法「輸入來源」 | 功能 | 同 TC-001 | 取出提出的 bundle（送出內容包） | 檔案清單不含 `samplesheet.csv`，只有 `params.yaml`、`nextflow.config`、`head.sh`；bundle 的 `samplesheet` 是空值（None） | 自動：新測試檔 |
| TC-003 | 作法「輸入來源」 | 功能 | 同 TC-001 | 讀 bundle 的 `params.yaml` | 沒有 `input` 這一項，但仍有 `outdir` | 自動：新測試檔 |
| TC-004 | 環境事實「OVERWRITE_BLOCK」 | 功能 | 同 TC-001 | 讀 bundle 附的 `nextflow.config` | 沒有樣本表時，仍附上 OVERWRITE_BLOCK（與有樣本表時相同的那段） | 自動：新測試檔 |
| TC-005 | 作法「head 指令」；失敗先行測試 3 | 功能 | 同 TC-001 | 讀 head 指令最後一行 | 含 ` -profile test` | 自動：新測試檔 `test_head_line_has_profile_and_keeps_site_config` |
| TC-006 | 作法「head 指令」；PITFALLS 54 | 功能 | 同 TC-001 | 讀 head 指令最後一行 | 站台設定 ` -c "$NFCORE_SITE_CONFIG"` 與 ` -c nextflow.config` 都還在；` -profile` 出現在這些 `-c` 之後、`-with-tower` 之前 | 自動：新測試檔 |
| TC-007 | 作法「確認畫面」；失敗先行測試 4 | 功能 | 同 TC-001 | 取本人確認前會看到的畫面文字 | 含一行 `Config profiles: test` | 自動：新測試檔 `test_screen_shows_profiles_and_test_data_line` |
| TC-008 | 作法「確認畫面」 | 功能 | 同 TC-001 | 取確認畫面文字 | 原本的樣本表那一行改為 `Samplesheet: from the pipeline's test profile` | 自動：新測試檔 |
| TC-009 | 作法「輸入來源」；裁決 5 | 功能 | 假站台 pipeline 的 `nextflow.config` 另有 `test_full` 與一個以 `test_` 開頭的 profile（名稱由測試自訂，且已在預檢名單） | 分別用 `profiles=["test_full"]`、`profiles=["test_<自訂>"]`，不給樣本表 | 兩者都「已提出」，且 bundle 都沒有 `samplesheet.csv`、`params.yaml` 沒有 `input` | 自動：新測試檔 |
| TC-010 | 維護者原話（「nano4 上面所有已安裝的 pipeline（用內建測試 Sample）」）；裁決（自動補）5 | 功能 | 新測試檔用 `station_harness.make_site_pipeline` 為八個 pipeline 各做假夾具：ampliseq 2.18.0、rnaseq 3.26.0、sarek 3.9.0、scrnaseq 4.2.0、atacseq 2.1.2、crisprseq 2.3.0、nanoseq 3.1.0、proteinfold 2.0.0（不改 `SITE_CE`）；預檢已記下各自的 profile | 八個 pipeline 各用 `profiles=["test"]`、不給樣本表，各 `launch` 一次 | 八個都回「已提出」，不是只有 ampliseq 與 rnaseq | 自動：新測試檔 |
| TC-011 | 裁決（自動補）2(a)；裁決 1 的驗收步驟 | 功能 | 平台升級合併後，由操作員處理 | 照 `docs/TESTING.md` 新增的「nano4 test profile 驗收」節 (a)：升級後先在環境頁對 nano4 重跑預檢 | 該節存在、步驟具體可照做（含「確認 `site_profiles` 有清單」）；操作員實際確認後結果記進 ledger | 手動：`docs/TESTING.md`「nano4 test profile 驗收」(a) |
| TC-012 | 維護者原話；裁決（自動補）2(b) | 功能 | 同 TC-011 之後 | 照同一節 (b)：對八個 pipeline（ampliseq、rnaseq、sarek、scrnaseq、atacseq、crisprseq、nanoseq、proteinfold）各用 `launch` 帶 `profiles=["test"]`、不給樣本表，本人確認後跑完 | 該節列出八個 pipeline 與具體步驟；操作員用 skill `nano4-acceptance` 每個各跑一次 test run 並記進 ledger；既有段落沒被改動，只新增文字 | 手動：`docs/TESTING.md`「nano4 test profile 驗收」(b) |

## User Story 2 — 樣本表並用、多個 profile，且不帶 profiles 時一切照舊（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | 裁決 3 | 功能 | 預檢名單有 `test` | `launch`，`profiles=["test"]`，同時給一份有效樣本表 | 回「已提出」 | 自動：新測試檔 |
| TC-014 | 裁決 3 | 功能 | 同 TC-013 | 讀該 bundle | 檔案清單含 `samplesheet.csv`；`params.yaml` 照舊寫 `input`（樣本表優先） | 自動：新測試檔 |
| TC-015 | 裁決（自動補）4 | 功能 | 同 TC-013 | 取確認畫面文字 | 含原本的樣本表那一行、含 `Config profiles: test`、不含 `from the pipeline's test profile` | 自動：新測試檔 |
| TC-016 | 作法「head 指令」（` -profile a,b`）；裁決 4 | 功能 | 預檢名單同時有 `test` 與 `docker` | `launch`，`profiles=["test","docker"]`，不給樣本表 | head 指令含 ` -profile test,docker`，站台 `-c` 行仍在；平台沒有另外擋掉 `docker`（名單內即放行） | 自動：新測試檔 |
| TC-017 | 作法「MCP 介面」；失敗先行測試 10 | 功能 | 取 MCP 工具清單 | 看 `launch` 的輸入結構 | 有選填參數 `profiles`（字串清單，預設不給）；原有 `samplesheet_text` 等參數仍在 | 自動：新測試檔 `test_profiles_argument_name_not_confirm_like`；`platform/tests/test_http_site_samplesheet.py` |
| TC-018 | 裁決（自動補）1 | 功能 | 預檢結果是舊形狀（沒有 `site_profiles` 欄），或該環境從沒預檢過 | `launch` 不帶 `profiles`、給有效樣本表 | 與改動前完全一樣地「已提出」，不受影響 | 自動：新測試檔 |
| TC-019 | 作法「新 bundle 鍵」；失敗先行測試 8 | 功能 | `platform/tests/fixtures/golden_head_scripts.json` 為改動前版本 | 不帶 `profiles`，用 golden 檔裡的每一組輸入重新渲染 head 指令 | 全部與 golden 逐位元組相同（golden 檔本身沒被改） | 自動：新測試檔 `test_no_profiles_is_byte_identical`；`test_launch_bundle.py`、`test_resume_render.py` |
| TC-020 | 作法「新 bundle 鍵」（沒給或空清單） | 功能 | 有效樣本表 | 分別用「不給 `profiles`」與「`profiles=[]`」渲染 | 兩者渲染出的 `samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh` 逐位元組相同，也與改動前相同 | 自動：新測試檔 |
| TC-021 | 作法「輸入來源」（沒給樣本表的既有行為不變） | 例外 | 不帶 `profiles`（或 `profiles=[]`） | `launch` 不給樣本表也不給 `samplesheet_text` | 仍被拒絕，與改動前同樣的拒絕（不因新功能變成放行） | 自動：新測試檔 |
| TC-022 | 作法「名稱驗證來源」；PITFALLS 14 | 功能 | 假站台 pipeline 的 `nextflow.config` 用真實 nf-core 寫法（含 `profiles { … }` 區塊） | 跑預檢 | 預檢結果有 `site_profiles`，以 `"<pipeline> <revision>"` 為鍵，值是該 pipeline 實際的 profile 名稱（例如含 `test`、`test_full`） | 自動：新測試檔；`test_station_site_inventory.py`、`test_station_launch.py` 既有完整相等比對仍通過 |
| TC-023 | 作法「名稱驗證來源」（jobs.py 清理處） | 功能 | 預檢結果帶 `site_profiles` | 預檢結果存進資料庫、再讀回（經 jobs.py 的清理） | `site_profiles` 沒被清掉，讀回後內容不變 | 自動：新測試檔 |
| TC-024 | 作法「所有讀 samplesheet 的地方」（confirm.py） | 功能 | 一筆已提出、`samplesheet` 為空值的 test-profile 送出 | 本人打開確認頁／表單 | 能正常顯示，不出錯（不再因為沒有樣本表而當掉） | 自動：新測試檔 |
| TC-025 | 作法「agent 端重建比對」 | 功能 | `samplesheet` 為空值、帶 `profiles` 的 bundle | 站台 agent 端重建並與送來的 bundle 比對 | 比對通過、不報錯；重建出的 head 行含 ` -profile test` | 自動：新測試檔；`test_station_launch.py` |

## User Story 3 — 名稱不對或送法不對時，白話拒絕且什麼都不寫（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | 作法「request_launch」；失敗先行測試 2 | 例外 | 預檢名單為 `test`、`test_full` | `launch`，`profiles=["nope"]` | 回覆以 `未送出：` 開頭，並列出該 pipeline 實際有的 profile 名稱（`test`、`test_full`） | 自動：新測試檔 `test_unknown_profile_refused_and_nothing_written` |
| TC-027 | 同上 | 例外 | 同 TC-026，先記下資料庫各表行數與檔案系統狀態 | 同 TC-026 | 資料庫行數與檔案系統都與送出前完全相同 | 自動：新測試檔 |
| TC-028 | 裁決 1 | 例外 | 該環境從沒跑過預檢（沒有紀錄） | `launch`，`profiles=["test"]` | 回覆以 `未送出：` 開頭，並提示先在環境頁跑一次檢查 | 自動：新測試檔 |
| TC-029 | 裁決 1 | 例外 | 同 TC-028，先記下資料庫與檔案系統狀態 | 同 TC-028 | 資料庫行數與檔案系統都沒變 | 自動：新測試檔 |
| TC-030 | 裁決（自動補）1 | 例外 | 預檢結果是舊形狀（沒有 `site_profiles`） | `launch`，`profiles=["test"]` | 拒絕（視為「無清單」），訊息同 TC-028 的提示 | 自動：新測試檔 |
| TC-031 | 作法「輸入來源」；失敗先行測試 7 | 例外 | 預檢名單有 `docker`（非自帶測試資料的 profile） | `launch`，`profiles=["docker"]`，不給樣本表 | 拒絕，說明這個 profile 不自帶資料、需要樣本表 | 自動：新測試檔 `test_non_input_profile_without_samplesheet_refused` |
| TC-032 | 作法「新 bundle 鍵」；失敗先行測試 11 | 例外 | 預檢名單有 `test` | `launch`，`profiles=[""]`（空字串） | 拒絕，`未送出：` 開頭，寫入無變化 | 自動：新測試檔 `test_bad_profile_names_refused` |
| TC-033 | 同上 | 例外 | 同 TC-032 | `profiles=["te st"]`（含空白） | 拒絕，`未送出：` 開頭 | 自動：新測試檔 |
| TC-034 | 同上 | 例外 | 同 TC-032 | `profiles=["test;rm"]`（含 `;`） | 拒絕，`未送出：` 開頭 | 自動：新測試檔 |
| TC-035 | 同上 | 例外 | 預檢名單有 `test` | `profiles=["test","test"]`（重複） | 拒絕，說明有重複 | 自動：新測試檔 |
| TC-036 | 同上（最多 8 個） | 例外 | 預檢名單含九個以上名稱 | `profiles` 給 9 個不同名稱 | 拒絕，說明最多 8 個 | 自動：新測試檔 |
| TC-037 | 作法「新 bundle 鍵」（命名規則 `^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}$`） | 例外 | 同 TC-032 | 分別用開頭是 `-` 的名稱（如 `-x`）與長度 65 的名稱 | 兩者都拒絕，`未送出：` 開頭 | 自動：新測試檔 |
| TC-038 | 裁決（自動補）3 | 例外 | 預檢名單有 `test` | `launch`，同時給 `samplesheet` 與 `samplesheet_text`，並帶 `profiles=["test"]` | 得到與改動前同一句原文：`samplesheet 與 samplesheet_text 只能給一個 …`（此檢查在 profile 判斷之前） | 自動：新測試檔；`test_dataset_launch.py:112` |
| TC-039 | 專長守則（錯誤訊息） | 例外 | 觸發 TC-026、TC-028、TC-031、TC-036 的拒絕 | 讀各拒絕回覆 | 每則說明發生什麼事與下一步該做什麼，用白話；不含堆疊、內部路徑、SQL | 自動：新測試檔 |
| TC-040 | 維護者原則「未確認不改變資料」；失敗先行測試 6 | 例外 | 一筆 test-profile 送出已提出、本人尚未確認；先記下資料庫行數 | 不做任何確認動作（含單獨呼叫工具、拿 token、帶模型自己的回答） | 資料庫沒有新的 run 或 job，行數與提出前相同 | 自動：新測試檔 `test_unconfirmed_test_profile_launch_changes_nothing` |

## User Story 4 — resume／relaunch 沿用原本的 profiles（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-041 | 作法「resume／relaunch」；失敗先行測試 5 | 功能 | 一筆用 `profiles=["test"]` 送出的 run | 讀記下來的 bundle | 有 `profiles`，內容是 `["test"]` | 自動：新測試檔 `test_bundle_records_profiles_and_relaunch_resume_reproduce` |
| TC-042 | 同上 | 功能 | 同 TC-041 | `prepare_relaunch` 重建 | 重建後的 head 行與原本相同（含 ` -profile test`） | 自動：新測試檔 |
| TC-043 | 裁決（自動補）1 | 功能 | 一筆舊形狀的 bundle（沒有 `profiles` 鍵） | `prepare_relaunch` 重建 | 把缺少的 `profiles` 當 `[]`，head 行與舊版逐位元組相同 | 自動：新測試檔；`test_resume_platform.py` |
| TC-044 | 裁決（自動補）1 | 功能 | 同 TC-043 | `prepare_resume` 重建 | 同 TC-043：head 行與舊版逐位元組相同 | 自動：新測試檔 |
| TC-045 | 作法「resume／relaunch」 | 功能 | 同 TC-041 | `prepare_resume` 重建 | 重建後的 head 行與原本相同（含 ` -profile test`） | 自動：新測試檔 |
| TC-046 | 作法「所有讀 samplesheet 的地方」 | 功能 | 原送出的 `samplesheet` 為空值（test profile 免樣本表） | `prepare_relaunch` 與 `prepare_resume` 重建 | 兩者都成功，不出錯，重建結果仍沒有 `samplesheet.csv` | 自動：新測試檔 |
| TC-047 | 作法「確認畫面」 | 功能 | 同 TC-041 | 取 resume 畫面與 relaunch 畫面文字 | 兩者都含 `Config profiles: test` | 自動：新測試檔 |
| TC-048 | 作法「確認畫面」 | 功能 | 同 TC-046 | 取 resume 畫面與 relaunch 畫面文字 | 兩者都含 `Samplesheet: from the pipeline's test profile` | 自動：新測試檔 |
| TC-049 | 作法「head 指令」；`render_resume`／`render_resume_bundle` | 功能 | 同 TC-041 | 用 resume 渲染路徑產生 head 指令 | 站台 `-c` 行仍在，` -profile test` 在它們之後、`-with-tower` 之前 | 自動：新測試檔 |

## User Story 5 — 其他來源與平台遇到 profiles 時明白說不支援（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-050 | 作法「範圍收斂」；裁決 2 | 不在範圍 | 一個 GitHub 遠端 pipeline（不是站台模組）；先記下資料庫與檔案系統狀態 | `launch`，帶 `profiles=["test"]` | 回覆以 `未送出：` 開頭，白話說明目前只支援站台已安裝的 pipeline；沒有寫入任何東西 | 自動：新測試檔 `test_non_site_module_and_other_platforms_refuse_profiles` |
| TC-051 | 同上 | 不在範圍 | 目標環境是 gcb | `launch` 帶非空 `profiles` | `未送出：`，白話說明不支援，無寫入 | 自動：新測試檔 |
| TC-052 | 同上 | 不在範圍 | 目標環境是 aws | 同上 | `未送出：`，無寫入 | 自動：新測試檔 |
| TC-053 | 同上 | 不在範圍 | 目標環境是 azure | 同上 | `未送出：`，無寫入 | 自動：新測試檔 |
| TC-054 | 同上 | 不在範圍 | 目標環境是 k8s | 同上 | `未送出：`，無寫入 | 自動：新測試檔 |

## User Story 6 — MCP `launch` 工具介面合乎規矩，既有行為不變（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-055 | 作法「MCP 介面」；`test_tc048` | 功能 | 取 `launch` 全部參數名稱 | 逐一檢查 | 沒有任何參數名含 confirm／approve／yes／send／force／skip／accept／送出；因此沒有任何參數能表示「已同意」 | 自動：新測試檔；`test_http_site_samplesheet.py` test_tc048 |
| TC-056 | 作法（說明字串避開 `BANNED_WORDS`） | 功能 | 取 `launch` 工具與 `profiles` 參數的說明字串 | 對照 `BANNED_WORDS` | 一個禁字都沒有 | 自動：新測試檔；`test_mcp_server_doc.py` |
| TC-057 | 專長守則（mcp）：每個參數都有說明 | 功能 | 取 `launch` 的輸入結構 | 逐個參數看說明 | `profiles` 有說明文字，含格式與範例（例如 `["test"]`）；其他參數說明仍在 | 自動：新測試檔 |
| TC-058 | 專長守則（mcp）：description 要求 | 功能 | 取 `launch` 的 description | 檢查內容與長度 | 說明做什麼、何時用、何時不要用、回傳什麼、下一步；總長不超過約 600 字元 | 自動：`test_mcp_server_doc.py`、新測試檔 |
| TC-059 | 專長守則（mcp）：工具清單；範圍「不新增工具」 | 功能 | 取 MCP 工具名單與唯讀標記 | 與改動前比對 | 工具名稱與唯讀標記不變，沒有新增或刪除工具 | 自動：`test_human_channel.py`、`test_mcp_server_doc.py` |
| TC-060 | 專長守則（mcp）：HTTP 傳輸 | 功能 | 經 HTTP 傳輸連上平台的 MCP | `launch`，`profiles=["test"]`，不給樣本表 | 得到與行程內連線相同的「已提出」結果 | 自動：`test_http_site_samplesheet.py` 加案例（環境做不到則須標明需要什麼） |
| TC-061 | 範圍（既有行為不變） | 功能 | 預檢名單有 `test` | 經 MCP `launch` 不帶 `profiles`，用 `samplesheet_text` 提出 | 與改動前相同地「已提出」，bundle 含 `samplesheet.csv` | 自動：`test_http_site_samplesheet.py`、`test_launch_bundle.py:103` |
| TC-062 | 專長守則：雲端渲染不得改變 | 功能 | aws 環境、不帶 `profiles` | 照既有測試渲染 | 輸出與改動前相同，`files` 含 `samplesheet.csv` | 自動：`test_aws_launch.py` |
| TC-063 | 同上 | 功能 | azure 環境、不帶 `profiles` | 同上 | 輸出與改動前相同 | 自動：`test_azure_launch.py` |
| TC-064 | 同上 | 功能 | gcb 環境、不帶 `profiles` | 同上 | 輸出與改動前相同 | 自動：`test_gcb_launch.py` |
| TC-065 | 同上 | 功能 | k8s 環境、不帶 `profiles` | 同上 | 輸出與改動前相同 | 自動：`test_k8s_launch.py` |
| TC-066 | 同上 | 功能 | 雲端傳輸線格式 | 照既有測試 | 輸出與改動前相同 | 自動：`test_cloud_wire.py` |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-067 | 裁決（自動補）6；「不做」 | 不在範圍 | 取 `request_pipeline_launch` 的函式簽名 | 用 `inspect.signature` 檢查 | 簽名沒有 `profiles` 參數（沒替它新增，所以不可能生效） | 自動：新測試檔 |
| TC-068 | 「不做」：`resume`／`relaunch` 工具改 profiles | 不在範圍 | 取 MCP 的 `resume` 與 `relaunch` 工具輸入結構 | 逐一檢查 | 兩者都沒有 `profiles` 參數 | 自動：新測試檔 |
| TC-069 | 「不做」：網頁步驟 4 的測試資料選項（後續片 `web-launch-test-profile`） | 不在範圍 | 網頁送出流程的樣本表步驟 | 讀頁面內容，並確認 `web.py`、`web_board.py`、`static/` 沒被修改 | 沒有「Use the pipeline's test data (profile test)」選項；這片沒動網頁 | 自動：新測試檔（頁面檢查）；閱卷時另查 `git diff --stat` 不含這些檔 |
| TC-070 | 「不做」：`launch_pipeline` 與組合 pipeline 的 profiles | 不在範圍 | 取 MCP 工具名單 | 找 `launch_pipeline` | 沒有這個工具，也沒有組合 pipeline 的 profiles 路徑 | 自動：新測試檔；`test_pipeline_launch.py` |
| TC-071 | 「不做」：讓使用者移除站台或基礎設施 profile、站台設定 | 不在範圍 | 預檢名單有 `test`、`docker` | 用各種 `profiles` 組合（`["test"]`、`["test","docker"]`）渲染 | head 指令永遠保留站台 ` -c "$NFCORE_SITE_CONFIG"` 與 ` -c nextflow.config`；使用者的 profile 只能附加；平台層沒有 docker／conda／singularity 黑名單 | 自動：新測試檔 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-072 | 安全網「每個寫入工具未經人答覆即拒絕」；不變條款 I.2（確認管道）；專長守則（mcp）寫入工具零副作用 | 例外 | 預檢名單有 `test` | 只呼叫一次 MCP `launch`（`profiles=["test"]`），不做任何確認；後端的寫入／送出函式以 mock 計次 | 寫入與送出函式呼叫次數為 0；資料庫行數不變 | 自動：新測試檔；`test_human_channel.py` test_tch09_*、`test_actions_layer.py` test_tcb04_* 至 test_tcb08_* |
| TC-073 | 專長守則（backend）：擁有者規則（讀） | 例外 | 使用者 A 已提出一筆 test-profile 送出 | 用使用者 B 的 token 去讀 A 這筆 | 被拒絕或看不到 | 自動：新測試檔；`test_owner_guard.py` |
| TC-074 | 專長守則（backend）：擁有者規則（改） | 例外 | 同 TC-073 | 用使用者 B 的 token 去確認或修改 A 這筆 | 被拒絕，A 的紀錄不變 | 自動：新測試檔；`test_owner_guard.py` |
| TC-075 | 專長守則（backend）：對等性 | 功能 | 列舉使用者可見的動作清單與動作層函式清單 | 兩邊對照（測試同時列舉兩邊） | 一一對應；`launch` 仍走動作層的 `request_launch`，沒有在路由處理函式裡另做一份邏輯 | 自動：`test_actions_layer.py`、`test_chat_tools.py` |
| TC-076 | 安全網「憑證不進 params 檔」「平台不存憑證」 | 功能 | 一筆 test-profile 送出，環境帶有 token 之類的測試用機密 | 讀 bundle 的 `params.yaml`、各拒絕回覆、日誌 | 都不含任何機密；`params.yaml` 只有 `outdir`（與可能的 `input`）等原本就有的項目 | 自動：新測試檔；`test_secrets.py` |
| TC-077 | 計畫環境事實：`umask 077` 在唯一的 `sbatch` 前 | 功能 | 帶 `profiles=["test"]` 渲染 head 指令 | 讀 `head.sh` | `umask 077` 仍在唯一那一次 `sbatch` 呼叫之前；只有一次 `sbatch` | 自動：新測試檔；`test_launch_bundle.py` |
| TC-078 | 計畫環境事實：PITFALLS 52／53（唯讀映像快取與本地路徑不可加 `-r`） | 功能 | 帶 `profiles=["test"]` 渲染 head 指令（含本地路徑 pipeline） | 讀 head 行 | 沒有因加了 `-profile` 而多出 `-r`，映像快取相關處與改動前相同 | 自動：新測試檔；`test_launch_bundle.py:575`、594、598 |
| TC-079 | 專長守則（backend）：資料結構變動；計畫「不需要 migration」 | 功能 | 資料庫有舊紀錄（bundle 無 `profiles`、預檢結果無 `site_profiles`） | 不新增任何 migration、不改資料表欄位，直接讀舊紀錄並做 TC-018、TC-043、TC-044 的動作 | 全部正常；`git diff` 沒有新的 migration 檔或資料表欄位 | 自動：新測試檔；閱卷時查 diff |
| TC-080 | 不變條款 6（任何 pipeline、不做逐 pipeline 設定） | 功能 | 本片改完 | 執行 `tests/no_per_pipeline_config.sh` | 通過；平台程式碼裡沒有逐 pipeline 的 profile 對照表（八個 pipeline 名只出現在測試夾具） | 自動：`tests/no_per_pipeline_config.sh` |
| TC-081 | 不變條款 3（不寫死路徑） | 功能 | 本片改完（含 `docs/TESTING.md` 新增節） | 執行 `tests/no_hardcoded_paths.sh` | 通過 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-082 | 不變條款 2（唯一的送出路徑、不留第二份 run 狀態） | 功能 | 本片改完 | 執行 `tests/no_second_run_state_test.sh` | 通過；沒有新增會送出的檔案，也沒有新的 run 狀態副本 | 自動：`tests/no_second_run_state_test.sh` |
| TC-083 | 不變條款 2 的確認管道檢查 | 功能 | 本片改完 | 跑 `test_human_channel.py` 的 `test_tch09_*` 與 `test_confirm_page.py` 的 `test_tch09_b_c_*` | 全部通過：未確認的 launch 經 MCP 工具與網頁路由都被拒絕 | 自動：`platform/tests/test_human_channel.py`、`platform/tests/test_confirm_page.py` |
