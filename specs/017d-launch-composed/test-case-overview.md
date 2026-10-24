# 測試案例總覽：畫布 017d 組合流程經同一確認流程送出（純後端）

狀態：合約已確認（2026-10-24，verifier）

**規格**：`specs/017d-launch-composed/plan.md`（沒有 spec.md；計畫的「維護者原話」「完成標準」「裁決」「裁決二」「裁決三」就是規格）　**明細**：`test-case.md`

> 依據順序：裁決三 > 裁決二 > 裁決（含 2026-10-24 06:50 的 A 至 E）> 計畫上文。上文與較後的裁決衝突處一律以較後的裁決為準。本次因計畫新增「裁決三」而重開並重新確認合約，編號不重排。

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 送到確認頁，本人按了才有工作 | 9 | 7 | 0 | 16 |
| US2 — 送出前的閘門（現算驗證） | 5 | 4 | 0 | 9 |
| US3 — 擁有者：別人的與不存在的一樣 | 1 | 5 | 0 | 6 |
| US4 — 專案檔怎麼組（build_project） | 19 | 15 | 0 | 34 |
| US5 — 模組檔資料（module_sources） | 12 | 7 | 0 | 19 |
| US6 — 內容包與 head.sh | 12 | 12 | 0 | 24 |
| US7 — 站台側 run_launch | 7 | 9 | 0 | 16 |
| US8 — build.py：保留名稱、續跑拒絕、確認畫面 | 4 | 7 | 0 | 11 |
| US9 — 沒變的東西、資料結構、安全與範圍守門 | 17 | 2 | 0 | 19 |
| US10 — 夾具、文件與交付 | 8 | 0 | 0 | 8 |
| US11 — 這次不做的事 | 0 | 0 | 11 | 11 |
| 憲法與安全網 | 5 | 1 | 0 | 6 |
| **合計** | 99 | 69 | 11 | 179 |

自動驗證 161 條、手動驗證 18 條（TC-108、139、145、146、149、150、154、155、156、157、158、159、160、162、163、164、178、179；手動＝驗收者讀 diff、ledger、PR 說明、文件，或需要 nano4 真機）。

## 請你判斷的三件事

1. **每條是不是你要的？** 重點看三處：TC-017 至 TC-025（有 error 的版本不能送、只有 warning 可以送、驗證現算不信存檔）；TC-043 至 TC-055（樣本表怎麼接到沒接的輸入、一格一個檔）；TC-129、TC-130（組合的 run 不能續跑也不能原樣重跑，話怎麼說）。
2. **有沒有漏掉的出錯情況？** 想像實驗室成員會怎麼用錯它：送別人的組合（US3）、確認後有人改了站台上的檔（TC-114 至 TC-117）、樣本表缺欄或指到不該讀的路徑（TC-047、TC-055）、拿 `abf-composed/…` 假名稱走 nf-core 送出（TC-125 至 TC-127）。
3. **「不在範圍」對嗎？** 不做續跑與重跑、容器檢查、雙端定序一格兩檔、共用專案資料夾、MCP 工具與網頁路由（那是 017e）、lint／空跑／zip（US11）。nano4 真機實跑與舊版代理的拒絕訊息是合併後的手動驗收，不擋這個 PR（TC-108、TC-158）。

## 覆蓋檢查

- 計畫作法 A（模組檔來源）、B（專案檔）、C（內容包）、D（head.sh）、E（站台）、F（平台入口）、G（不需要 migration）共 7 節，全部都有測試案例：是（A→US5、TC-081、TC-083；B→US4；C→TC-085 至 TC-108；D→TC-092 至 TC-097、TC-106；E→US7；F→US1 至 US3；G→TC-137 至 TC-139）
- 維護者原話共 7 句，全部都有測試案例：是（「送去跑」是一等動作、done 鏈「launch→/c/<rid>→站台跑起」→TC-001、TC-015；「送前驗證、有 error 不能送」→TC-017 至 TC-025；借國網零件自己啟動、不走 nfcore-submit→TC-092 至 TC-095、TC-163；每個寫入要本人答應、不自動送出→TC-002、TC-123、TC-166、TC-172；啟動字樣只在 `launch.py`→TC-143、TC-148、TC-173；擁有者規則→TC-026 至 TC-031；「不做巢狀子流程」→TC-061、TC-168）
- 計畫 `test_module_sources.py` 8 條、`test_pipeline_launch.py` 約 38 條、`test_launch_bundle.py` 6 條、`test_pipeline_launch_station.py` 9 條失敗先行測試，全部都有對應 TC：是（`test_snapshot_is_byte_identical…`→TC-066、067；`…keeps_only_main_templates_and_resources`→TC-068；`…marks_bin_dirs…`→TC-069 至 073；`test_sources_sha_equals…`→TC-075；`test_load_refuses…`→TC-074；`test_every_catalogue_module…`→TC-076、081；`test_fastqc_and_multiqc…`→TC-077；`test_files_for_names…`→TC-078、079；`…no_network_or_program_words`→TC-082；`test_golden_project…`→TC-032、034、035；`…deterministic…`→TC-033；`…open_input_lines…`→TC-035、036；缺欄、同名共用、同名異型→TC-047 至 051；不支援型別→TC-045、046；不安全欄名、使用者文字不進 Groovy→TC-052、053；`…path_columns…read_roots`→TC-054、055；`…publish_block…`→TC-056；`…size_and_file_count_limits`→TC-058、059；閘門四條→TC-017 至 025；擁有者→TC-026 至 028；版本→TC-007、008；`…nothing_is_queued_without_a_yes`→TC-002、003；`…asking_again…`→TC-004；`…same_pending_request_and_page…`→TC-005、006；`…bundle_shape…`→TC-089、090；`…byte_identical_to_before`→TC-136；`…hash_covers_the_project`→TC-105；`…reserved_owner…`→TC-125 至 128；`…resume_and_relaunch…`→TC-129、130；畫面兩條→TC-131 至 135；`…opens_no_socket`→TC-140；`…no_table_or_column_changed`→TC-137；`…hide_internals`→TC-141；`…no_program_or_run_words`→TC-143、144；`test_launch_bundle` 6 條→TC-092 至 097、098 至 104、106；站台 9 條→TC-109 至 124）
- 計畫「允許更新的既有斷言」（`test_pipelines_store.py` 禁用字一處、golden 只加 `composed`、兩個測試檔只新增）與裁決三-1 補核可的兩處（`test_web_parity.py` INTERNAL 多一個名字、`test_guidance.py` package-data 字串多一個 glob）與「必須確認仍綠」各項，全部都有 TC：是（TC-096、145、146、147、148、152、178、179）
- 計畫完成標準 6 條與 PR 說明項目：是（TC-015、017、026、152、150、160；手動項 TC-158、159）
- 裁決三 6 點：全部都有測試案例：是（1→TC-150、178、179；2→TC-081；3→TC-055；4→TC-061、159；5→TC-108、158、160；6→TC-153）
- 計畫「不做」共 11 條（MCP／網頁／handlers、續跑與重跑、容器檢查、lint／stub-run／nf-test／zip、launches 欄位與表與 job 種類、自動送出、list 型別與 bin/ 與子流程、配對式一格兩檔、共用專案資料夾與 sha 略過、`project_tar`、不做離線真 Nextflow 測試）：全部都有「不在範圍」測試案例：是（TC-161 至 TC-171；真 Nextflow 離線測試依裁決二-3 不做，對應 TC-158 的手動步驟與 TC-092 至 TC-095 的文字斷言）
- 專長守則（backend）適用項：對等性——本任務沒有新增使用者可見的動作（不加 MCP 工具、不加網頁路由），所以以 TC-014（兩個送出函式共用 `_finish_launch`）、TC-161 與 TC-178（工具清單、路由清單、parity 表只多登記動作層函式 `request_pipeline_launch` 一個內部名字）證明兩邊一一對應沒有被破壞，017e 才開對外名字；跨使用者讀與寫各一條→TC-026（讀）、TC-028 與 TC-031（寫）；確認管道→TC-002、003、123、172；錯誤訊息與日誌（含密鑰不外洩）→TC-063、064、141、142；migration→TC-137、138、139。
- 夾具與標準答案（黃金圖＋手算標準答案＋`unsupported/`）：是（TC-032、153、154、155）

## 我（撰寫者）不確定的地方

1. 計畫上文說 `pipeline_launch.py` 不得含 `compose` 子字串，裁決二-1 說只有 `actions/__init__.py` 受限。我依裁決二（TC-144）。這條不改變要檢查什麼。
2. 計畫作法 D 的 head.sh 與真 Nextflow 離線測試，已被裁決二-2、-3 取代；我依裁決二（TC-092 至 TC-095）。TC-092 的 `<run_folder>` 以夾具實際值代入，golden 檔由實作者依夾具產生並由 TC-096 鎖住。
3. 拒絕假名稱的話，上文含 `launch_pipeline`，裁決二-5 改成「組合流程只能從畫布送出（畫布送出介面尚未開放）」；我依裁決二（TC-128）。
4. 「含 `include {` 或 `workflow `」是字樣比對，可能誤中真實模組的註解；只有 fastqc 與 multiqc 被要求不誤中（TC-062），其餘被擋的數量只要求 ledger 記下（TC-159，裁決三-4）。
5. 計畫沒寫「樣本表裡有 `reads` 以外多餘的欄」要怎麼處理，沒有 TC。
6. 計畫沒寫專案檔數剛好等於 2,000 或大小剛好等於 2 MiB 算過還是不過（只寫「≤」為允許）；TC-058、059、100 至 102 以「剛好等於上限允許、多一個就拒絕」為準。
7. TC-174 假設既有的 launch 確認畫面會顯示 `head.sh`（計畫在畫面一節以「與 head.sh 同樣處理控制字元」暗示）；若既有畫面不顯示，TC-174 內已註明改為只驗專案檔。

（已解決、從舊版移除：舊第 4 點「有沒有使用者自給的 path_columns」→裁決三-3 答：沒有；舊第 5 點 `UNSUPPORTED_MODULE` 放哪裡→裁決三-4 答：錯誤物件屬性或訊息文字二擇一；舊第 7 點夾具不在 worktree→裁決三-6 要求必須在分支上，TC-153 驗。）

## 核可紀錄

（尚未經維護者本人審閱；此為 verifier 依 plan 出題的合約。）

### 重開紀錄（2026-10-24，因計畫新增「裁決三」）

- 改寫的列：TC-013（不再指定訊息字面，改為與 `request_launch` 一致）、TC-055（裁決三-3：沒有使用者自給的 path_columns）、TC-061（裁決三-4）、TC-081（裁決三-2：資料檔接受進 repo，數字改以目錄模組數與 8 MiB 上限驗；ledger 內容移到 TC-159）、TC-083（package-data 對應 test_guidance）、TC-092（不再寫死 run_folder 路徑，改 `<run_folder>` 代入）、TC-096（不寫死既有鍵名）、TC-108 與 TC-158（裁決三-5：合併後手動驗收，不擋本 PR）、TC-146／147／150（裁決三-1：兩個測試檔的許可修改與範圍）、TC-153（裁決三-6）、TC-159、TC-160、TC-161、TC-169（只驗計畫寫明的「一個欄一個檔」，不推測拒絕的原因）；憲法條目改用不變條款編號（1、2、3、4、6）。
- 新增：TC-178（`test_web_parity.py` 只多一個名字）、TC-179（`test_guidance.py` 只多一個 glob 字串）。
- 總數由 177 變 179（功能 97→99）；自動 161 條不變、手動 16→18 條。
