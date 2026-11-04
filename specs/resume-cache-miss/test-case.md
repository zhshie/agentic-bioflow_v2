# 測試案例：續跑不該讓不相關 task 重算（離線測試＋診斷程序）

**規格**：本片沒有 `spec.md`；以 `specs/resume-cache-miss/plan.md` 各節代替 FR 編號（目標、範圍、作法 H1–H5、失敗先行測試、完成標準、不做、裁決）。「對應需求」欄寫的是計畫的節名或 H 編號。　**總覽**：`test-case-overview.md`

維護者原話（plan.md 引用）：backlog 2026-10-25「nano4: resume of r6 with edits re-ran 71/72 tasks (FASTQC hash changed though unrelated). Diagnose with 3 cheap resumes (no edit / param only / config only; each needs maintainer y), then nextflow -dump-hashes diff. Folder /work/u9613010/runs/runs/ampliseq_day5_nano4_r6.」；2026-10-26「都ok」。對應 TC-001～TC-018（離線排除平台端）與 TC-019～TC-030（三次續跑＋hash 比對的診斷程序）。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做。

名詞：「續跑」＝帶著原本的 session id 重新啟動同一個 run，讓 Nextflow 沿用已算好的結果（CACHED）。「head 腳本」＝平台送到叢集去啟動 Nextflow 的那份 `head-<N>.sh`。H1–H5 是計畫列出的五個「平台端可能害快取失效」的假設。測試檔內以註解標明對應的 TC 編號。

## User Story 1 — 離線證明：平台產生的續跑檔案與原送出相比只差該差的東西（優先度 P1）

測試都在新檔 `platform/tests/test_resume_cache_stability.py`，用既有的 `resume_harness`／`launch_harness` 夾具。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 失敗先行測試 `test_resume_without_edit_reuses_origin_files` | 功能 | 一份原送出的內容包（ampliseq 站台夾具），續跑沒有任何修改 | 呼叫續跑渲染，不帶 overrides | 只回傳 `head-<N>.sh` 一個檔；沒有 `params-<N>.yaml`、沒有 `extra-<N>.config`，原本的 `params.yaml`、`nextflow.config` 不重寫 | 自動：`platform/tests/test_resume_cache_stability.py` |
| TC-002 | 同上；作法「已知事實」第 1 點 | 功能 | 同 TC-001 | 把續跑的 head 與原送出的 head 逐行比對 | 只有 `#SBATCH -J` 那行、`-name`、`-resume <session>` 不同；其餘每一行逐字相同 | 自動：同上 |
| TC-003 | H1；`test_resume_with_param_edit_keeps_unchanged_params_byte_identical` | 功能 | 原送出的 params 含字串、整數、浮點 `1e-05`、布林、含引號與非 ASCII 的字串 | 續跑時只改其中一個鍵 | `params-2.yaml` 與原 `params.yaml` 逐行比對，只有被改的那一行不同 | 自動：同上 |
| TC-004 | H1 | 功能 | 同 TC-003 | 看沒被改的那些行 | 浮點 `1e-05` 的寫法、布林、整數、含引號與非 ASCII 字串的行，與原 `params.yaml` 逐字相同（含引號、排序） | 自動：同上 |
| TC-005 | H2 | 功能 | 同 TC-003，params 含 `input`、`outdir` | 看兩份檔裡 `input`、`outdir` 的字串 | 兩份檔的 `input`、`outdir` 逐字相同，路徑沒有被正規化成另一個樣子 | 自動：同上 |
| TC-006 | `test_resume_params_yaml_matches_origin_render` | 功能 | 一份原送出的內容包，其 `files["params.yaml"]` 是原渲染結果 | 用原內容包的 params 與 run_folder 重新渲染 `params.yaml` | 重新渲染的文字與原內容包的 `params.yaml` 逐字相同（重新渲染不漂移） | 自動：同上 |
| TC-007 | H3；`test_resume_head_differs_only_in_allowed_flags` | 功能 | 續跑同時改 param 並加 extra 設定 | 把續跑 head 末行與原 head 末行各拆成片段，續跑那行先移除 `-name X`、`-resume S`、`-params-file F`、`-c extra-N.config` | 剩下的片段與原 head 末行的片段完全相同（包含 `-c "$NFCORE_SITE_CONFIG"`、`-c nextflow.config`、`-with-tower`） | 自動：同上 |
| TC-008 | H3；允許的斷言變動（`test_resume_edit_params_station.py` l.31、335、449） | 功能 | 既有測試檔，不修改 | 執行 `test_resume_edit_params_station.py` | 原樣全綠：帶修改的 head 行全文與 argv 為 `-params-file params-2.yaml`、`-c extra-2.config`，且 `-c extra-2.config` 排在 `-c nextflow.config` 之後 | 自動：`platform/tests/test_resume_edit_params_station.py` |
| TC-009 | H4；`test_resume_env_and_modules_match_origin` | 功能 | 原送出的 head 有 `module load` 與 `export` 行 | 續跑（有修改與無修改各一種）後，取 `module load`、`export` 行的集合 | 與原 head 的集合相同（模組版本、`NXF_*` 環境與原本一致，不是重新算的） | 自動：`platform/tests/test_resume_cache_stability.py` |
| TC-010 | H5；`test_resume_extra_config_has_no_hash_affecting_keys` | 功能 | 續跑不帶 extra 設定 | 呼叫續跑渲染 | 沒有 `extra-N.config` 這個檔 | 自動：同上 |
| TC-011 | H5 | 功能 | 續跑帶 `process.memory` 的 extra 設定 | 取 `extra-N.config` 的內容 | 內容恰為平台註解行加使用者給的文字，沒有別的 | 自動：同上 |
| TC-012 | H5 | 功能 | 同 TC-011 | 在 `extra-N.config` 裡找 `container`、`env`、`ext` | 平台自己沒有加任何 `container`／`env`／`ext` 相關的鍵（會改變 task 雜湊的鍵） | 自動：同上 |
| TC-013 | `test_resume_unconfirmed_changes_nothing` | 例外 | 一個可續跑的 run；用 `test_resume_platform.py` 的確認管道夾具 | 要求續跑，但本人沒有確認 | 資料庫沒有新 run、沒有新 job；沒有任何東西被送出 | 自動：同上 |
| TC-014 | 作法「結論寫進 ledger」；完成標準 | 功能 | 實作完成 | 看 `specs/resume-cache-miss/ledger.md` | 有 H1–H5 逐條結論表；每條標「已排除（附測試名）」或「平台端成立（附輸出差異）」；測試名在測試檔中真的存在；表中同時記各測試的紅／綠／xfail 狀態 | 手動：`docs/TESTING.md`（新節的審查者檢查項，見 TC-030） |
| TC-015 | 裁決 1 | 功能 | 若某條 H 測試證明平台端缺陷 | 看該測試的標記 | 寫成 `@pytest.mark.xfail(strict=True, reason="H<n>: 平台端缺陷，見 specs/resume-cache-miss/ledger.md")`；整個新測試檔仍然全綠（含 strict xfail）。若沒有任何 H 成立，則測試檔裡不應有 xfail，且 ledger 寫明五條全部已排除 | 自動：`platform/tests/test_resume_cache_stability.py` |
| TC-016 | 裁決 1 | 功能 | 同 TC-015，有 xfail 的情況 | 看有 xfail 的 H 旁邊 | 另有一條「綠」的 characterization 測試把目前差異釘成事實；ledger 貼有紅的原始差異輸出；沒有放寬任何既有斷言。若沒有 xfail，此條記為「不適用」並在 ledger 說明 | 自動：同上 |
| TC-017 | 允許的斷言變動（全列） | 功能 | 既有測試不修改 | 執行 `test_resume_render.py`（golden head scripts）、`test_launch_bundle.py`、`test_resume_edit_params_docs.py`、`test_resume_platform.py`、`test_resume_scope.py`、`test_resume_entrypoints.py`、`test_resume_lineage.py`、`test_station_resume.py`、`test_cleanup_offer.py` | 全部原樣綠；續跑輸出逐位元組不變（golden 夾具 `fixtures/golden_head_scripts.json` 未被改） | 自動：上述各檔（逐檔執行） |
| TC-018 | 範圍「既有測試只准加案例」；完成標準 | 功能 | 實作完成 | 對照 base 看 `git diff` 中被動到的既有測試檔 | 只有 `resume_harness.py` 有「加案例」；沒有刪除、跳過、放寬任何既有斷言，沒有改期望值去配合新輸出；`fixtures/golden_head_scripts.json` 未變 | 手動：`docs/TESTING.md`（新節的審查者檢查項，見 TC-030） |

## User Story 2 — nano4 診斷程序寫進 `docs/TESTING.md`（優先度 P1）

本片只寫程序，不連 nano4、不執行續跑。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 範圍 `docs/TESTING.md`；裁決 7 | 功能 | 實作完成 | 開 `docs/TESTING.md` | 新增一節「續跑快取診斷（nano4）」，位置在「Resume and relaunch (009e)」整節第 7 項之後、下一個 `##` 標題之前；既有段落一字未動（diff 只有新增行） | 手動：`docs/TESTING.md` 新節 |
| TC-020 | 作法第 2 階段第 1 步 | 功能 | 同上 | 讀新節第 1 次續跑 | 寫明：對 r6 資料夾「無修改續跑」，預期幾乎全 CACHED；若這一步就大量重算，原因在 session／工作目錄／檔案時間戳（站台或 Nextflow 端），與「修改」無關 | 手動：`docs/TESTING.md` 新節 |
| TC-021 | 作法第 2 階段第 2 步；環境事實 | 功能 | 同上 | 讀新節第 2 次續跑 | 寫明：只改一個「下游才用」的參數，預期只有受影響的 task 重算；並提醒要選下游才用的參數（改上游才用的參數導致下游重算是正常） | 手動：`docs/TESTING.md` 新節 |
| TC-022 | 作法第 2 階段第 3 步 | 功能 | 同上 | 讀新節第 3 次續跑 | 寫明：只加 `extra_config`（例如 `process.memory`），預期全 CACHED（memory 不入雜湊） | 手動：`docs/TESTING.md` 新節 |
| TC-023 | backlog「each needs maintainer y」；作法第 2 階段 | 功能 | 同上 | 讀新節對三次續跑的要求 | 寫明每一次續跑都要維護者本人確認（說 y），操作員不能代答；每次都記下 session id 與 `get_run` 的 CACHED／總數 | 手動：`docs/TESTING.md` 新節 |
| TC-024 | backlog 原文（資料夾）；作法第 2 階段 | 功能 | 同上 | 讀新節的環境說明 | 指明對象是 `/work/u9613010/runs/runs/ampliseq_day5_nano4_r6`，由操作員用 skill `nano4-acceptance` 執行 | 手動：`docs/TESTING.md` 新節 |
| TC-025 | 裁決 5(a) | 功能 | 同上 | 讀新節的第一層（免寫入） | 寫明：三次續跑各自在 r6 資料夾留下 `.nextflow.log`；操作員只用 `grep`／`cp` 在登入節點讀取並複製日誌到別處（例如 `~/r6-diag/`），再餵 `scripts/nf_hash_diff.py`；這一層不啟動 Nextflow，不動 `.nextflow/cache` | 手動：`docs/TESTING.md` 新節 |
| TC-026 | 裁決 5(b) | 功能 | 同上 | 讀新節的第二層（`-dump-hashes`） | 寫明：這是「第四次手動續跑」——複製某次續跑產生的 `head-<N>.sh` 末行、手動加 `-dump-hashes`、在 r6 資料夾啟動；須維護者本人說 y；排在三次平台續跑之後；記錄 session id；給出完整指令；說明修改前後兩份輸出各存放何處 | 手動：`docs/TESTING.md` 新節 |
| TC-027 | 裁決 5（「唯讀」一句作廢） | 例外 | 同上 | 在新節搜尋 `-dump-hashes` 附近的說明 | 明講第二層「不是唯讀」，會寫入 `.nextflow/cache` 與 `.nextflow.log`；全節沒有任何地方把 `-dump-hashes` 步驟說成唯讀或不寫入；並說明平台產生的 head 本身不帶 `-dump-hashes` | 手動：`docs/TESTING.md` 新節 |
| TC-028 | 完成標準「具體指令、每次要記的欄位」 | 功能 | 同上 | 讀新節 | 三次續跑與 `-dump-hashes` 各有可照著打的具體指令；每次要記的欄位有列出 | 手動：`docs/TESTING.md` 新節 |
| TC-029 | 完成標準「判讀表」；裁決 4 | 功能 | 同上 | 讀新節的判讀表 | 有表說明每種結果指向哪裡：第 1 步就大量重算 → 站台／Nextflow 端（與修改無關），本片不猜修法、回報維護者另議；第 2 步重算超出受影響範圍、第 3 步 extra_config 就導致重算 → 如何判讀；並列出 hash 比對第一個不同欄位的分類（輸入檔路徑／大小／mtime、container、script、env）各指向誰 | 手動：`docs/TESTING.md` 新節 |
| TC-030 | 驗證方式要求（手動案例須有步驟）；完成標準 | 功能 | 同上 | 讀新節末尾 | 有一項「審查者檢查」，列出：`git diff --stat` 只含範圍內的檔；`launch.py`、`OVERWRITE_BLOCK`、`relaunch`、`web.py`、`mcp_server.py`、`static/`、`jobs.py` 未改；無 `store.py`／migration 變動；`nf_hash_diff.py` 只用標準函式庫；ledger 的 H1–H5 表與既有測試未被放寬 | 手動：`docs/TESTING.md` 新節 |

## User Story 3 — 離線小工具 `scripts/nf_hash_diff.py`（優先度 P2）

讀兩份 `.nextflow.log`／hash 輸出，列出第一個不同的欄位。測試名 `test_nf_hash_diff_reports_first_difference`（裁決 3：必做）。測試使用人造輸入。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-031 | `test_nf_hash_diff_reports_first_difference` | 功能 | 兩份人造輸出，只有 `container` 不同 | 執行工具 | 回報第一個不同的欄位是 `container` | 自動：`platform/tests/test_resume_cache_stability.py` |
| TC-032 | 同上 | 功能 | 兩份人造輸出完全相同 | 執行工具 | 回報「無差異」，不虛報任何欄位 | 自動：同上 |
| TC-033 | 作法「找第一個不同欄位」 | 功能 | 兩份人造輸出有兩個欄位不同（例如 `container` 與較後面的另一欄） | 執行工具 | 回報的是兩者中排在輸入前面的那一個（第一個），不是最後一個或全部混在一起 | 自動：同上 |
| TC-034 | 同上「缺欄位不拋堆疊」 | 例外 | 其中一份輸出缺少某個欄位 | 執行工具 | 不出現 Python 堆疊（traceback）；給出可讀的訊息 | 自動：同上 |
| TC-035 | 裁決 5「格式不認得」 | 例外 | 餵進完全不是 hash 日誌的文字 | 執行工具 | 回報「格式不認得」；不出現堆疊 | 自動：同上 |
| TC-036 | 專長守則：錯誤訊息；日誌不含密鑰 | 例外 | 觸發 TC-034、TC-035 的錯誤 | 看輸出文字 | 說明發生了什麼事（哪份檔、缺什麼或認不得）並告訴操作員下一步怎麼做；不露出堆疊、SQL；不含密鑰、token | 自動：同上 |
| TC-037 | 範圍 `nf_hash_diff.py`「純標準函式庫，不連網、不連叢集」；裁決 3 | 功能 | 實作完成 | 讀 `scripts/nf_hash_diff.py` 的 import 與呼叫 | 只用 Python 標準函式庫；沒有網路、ssh、sbatch、nextflow 的呼叫；整檔刪除不影響其他檔（除 TESTING.md 對它的引用） | 手動：`docs/TESTING.md` 新節審查者檢查項（TC-030） |
| TC-038 | 裁決 5「輸入格式以 `.nextflow.log` 實際 hash 行為準」；PITFALLS 第 14 條 | 功能 | 實作完成 | 讀測試用的人造輸入與腳本檔頭註解／ledger | 人造輸入的形狀是照真實 `.nextflow.log` 的 hash 行寫的，並寫明格式依據出處；沒有憑空假設欄位 | 手動：`docs/TESTING.md` 新節審查者檢查項（TC-030） |

## User Story 4 — 範圍與「不做」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-039 | 裁決 2；範圍 `launch.py`「不改」；風險維持 M | 不在範圍 | 實作完成（即使有 H 測試證明平台端缺陷） | `git diff origin/v3...HEAD -- platform/abf_station/launch.py` | 沒有任何變動；缺陷（若有）只以 strict xfail 與 ledger 差異輸出留下，不在本片修 | 手動：`docs/TESTING.md` 新節審查者檢查項（TC-030） |
| TC-040 | 不做第 1 條；PITFALLS 第 50 條 | 不在範圍 | 同上 | 看 diff | `OVERWRITE_BLOCK` 未動；沒有新增 `process.cache = 'lenient'` 或其他站台／Nextflow 快取設定 | 手動：同上 |
| TC-041 | 不做第 2 條 | 不在範圍 | 同上 | 看 diff | `relaunch` 的程式與行為未動 | 手動：同上 |
| TC-042 | 不做第 3 條；範圍「不准碰」 | 不在範圍 | 同上 | 看 diff | `web.py`、`mcp_server.py`、`static/`、`platform/abf_platform/jobs.py` 沒有變動 | 手動：同上 |
| TC-043 | 不做第 4 條；範圍「不准碰」；環境事實「不准改」 | 不在範圍 | 同上 | 看 diff | `docs/PITFALLS.md`、`dev-queue.json`、`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json` 都沒有變動 | 手動：同上 |
| TC-044 | 不做第 5 條 | 不在範圍 | 同上 | 看新增的檔案與程式 | 沒有任何程式路徑會自動在 nano4 發起續跑（沒有 ssh／sbatch／nextflow 呼叫）；三次續跑只寫成文件程序，由維護者確認、操作員手動做 | 手動：同上 |
| TC-045 | 不做第 6 條 | 不在範圍 | 同上 | 看 diff | 雲端（gcb／aws／azure／k8s）的續跑相關程式與測試沒有變動 | 手動：同上 |
| TC-046 | 裁決 7「不需要 migration」；專長守則 migration | 不在範圍 | 同上 | `git diff origin/v3...HEAD` 查 `store.py` 與 migration | 沒有 `store.py` 或 migration 變動（本片不改資料結構或資料內容） | 手動：同上 |
| TC-047 | 範圍「檔案（只准改這些）」；裁決 6；完成標準 | 不在範圍 | 同上 | `git diff --stat origin/v3...HEAD` | 只含：`platform/tests/test_resume_cache_stability.py`、`platform/tests/resume_harness.py`（僅加案例）、`docs/TESTING.md`（僅新節）、`scripts/nf_hash_diff.py`、`specs/resume-cache-miss/ledger.md`；沒有其他檔 | 手動：同上 |

## 憲法與安全網

本片動到的規則：憲法第 3 條（沒有個人／叢集路徑；`scripts/nf_hash_diff.py` 在被掃描範圍內）、第 8 條（先有證據再下結論；由 TC-014、TC-038 證明）、人工確認管道（續跑的 yes）、以及後端專長守則（對等性、跨使用者、確認管道、錯誤訊息與日誌、migration）。本片不新增任何動作或寫入路徑，所以下列對等性與跨使用者 TC 以「既有測試原樣綠」證明沒有被破壞。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-048 | 憲法第 3 條（無硬編碼路徑） | 功能 | 新增 `scripts/nf_hash_diff.py` | 執行 `tests/no_hardcoded_paths.sh` | 輸出 OK；腳本與測試資料沒有 `/work/<人>/`、`/home/<人>/` 之類路徑（TESTING.md 在 `docs/`，不在掃描範圍） | 自動：`tests/no_hardcoded_paths.sh` |
| TC-049 | 確認管道（專長守則：確認管道 TC；Safety Net 人工確認） | 功能 | 既有確認管道測試，不修改 | 執行 `test_resume_platform.py`、`test_resume_entrypoints.py` | 原樣全綠：待確認的請求不排任何工作（`test_tc078_tc079…`）；不是 y 的回答不排任何工作（`test_tc144…`）；與 TC-013 一起證明未確認不改變資料 | 自動：`platform/tests/test_resume_platform.py`、`platform/tests/test_resume_entrypoints.py` |
| TC-050 | 專長守則：對等性 TC | 功能 | 既有測試，不修改 | 執行 `test_resume_entrypoints.py` | 原樣全綠：續跑與重跑的工具清單仍恰為既有的那兩個（`test_tc132…`），本片沒有多出或少掉使用者可見的動作 | 自動：`platform/tests/test_resume_entrypoints.py` |
| TC-051 | 專長守則：跨使用者（讀） | 功能 | 既有測試，不修改 | 執行 `test_resume_entrypoints.py` | 原樣全綠：別人的 run 對第二位使用者回「找不到」（`test_tc100_tc101…`、`test_tc109…`） | 自動：`platform/tests/test_resume_entrypoints.py` |
| TC-052 | 專長守則：跨使用者（寫） | 功能 | 既有測試，不修改 | 執行 `test_resume_edit_params_platform.py`、`test_resume_platform.py` | 原樣全綠：帶修改的續跑仍只限擁有者（`test_an_edited_resume_is_still_owner_only…`）；別的 agent 送的 run 被拒（`test_tc049…`） | 自動：`platform/tests/test_resume_edit_params_platform.py`、`platform/tests/test_resume_platform.py` |
| TC-053 | 專長守則：日誌與回應不含密鑰 | 功能 | 實作完成 | 讀新測試檔、`nf_hash_diff.py`、ledger 貼的輸出、TESTING.md 新節 | 沒有 token、密碼、金鑰；夾具用的都是假值；貼進 ledger 的差異輸出已不含密鑰 | 手動：`docs/TESTING.md` 新節審查者檢查項（TC-030） |
| TC-054 | 完成標準：全套綠 | 功能 | 實作完成 | 在 WSL／Linux 執行 `tests/run_all.sh` | 全綠（含新測試檔的 strict xfail 若有）；已知環境紅除外（見 dev-plans README） | 自動：`tests/run_all.sh` |
