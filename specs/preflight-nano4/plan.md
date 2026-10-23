---
id: preflight-nano4
title: preflight 先 module load，並檢查站台 pipeline 版本與唯讀快取
tier: A
kinds: backend
lane: L1
base: v3
---

# preflight-nano4（M1-04）

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/preflight-nano4/plan.md`。**只處理本任務**。2026-10-23 整份重寫（第一版被 verifier 退回五條，見檔尾「上一版退回理由」）。前置 `ce-nano4-keys`（#157）、`launch-site-pipeline`（#162）、`way-back-direct`（#155）都已合進 `v3`。

## 目標
啟動前的自檢（preflight）在 nano4 上要先 `module load` 才找得到 java／nextflow；還要確認站台預裝的 pipeline 真的是 CE 說的版本、唯讀映像庫讀得到。錯了要點名、說下一步，不要等到跑了才失敗。

## 維護者原話（verifier 出題用）
- 「nano4 若週四跑不通 → 先在 `/work/u9613010` 自裝 Nextflow＋插件跑通」（裁示 17）——所以 `modules` 為空時 preflight 不得硬要 `module load`。
- 「試用成功標準＝同事不問我就能跑完一次 16S」（裁示 17）——失敗訊息要能讓非工程師知道下一步。

## 範圍：檔案
- `platform/abf_station/handlers.py`（preflight）
- `platform/abf_station/rules.py`（`clean_environment` 放行 `singularityLibraryDir`）
- `platform/abf_platform/compute_envs.py`（`snapshot` 多帶 `singularityLibraryDir`）
- `platform/tests/station_harness.py`（FakeSite 加假的 `module` 指令與站台 pipeline 目錄）
- `platform/tests/test_station_e2e.py`（新測試）
- `platform/tests/test_station_envs.py`（只更新 `test_tc_ls_23_24_26_snapshot_carries_the_three_keys_and_nothing_more` 的鍵集合）
- `docs/PLATFORM.md`（「### Preflight」表下加三項條件式檢查的說明）
- `specs/preflight-nano4/ledger.md`

## 作法（每條都可寫成會失敗的測試）
1. **三項新檢查是「條件式」的：條件不成立就不出現在結果裡**（不是 `unchecked`）。所以既有環境（三鍵都空、沒有映像庫）的預檢結果與現在**完全相同**：同樣 8 項、同樣判定、`_verdict` 不改、`CHECK_ORDER` 不改，既有 `test_station_e2e.py` 的 `CHECKS` 與 TC-041／042 不動。
2. **`modules`**（`modules` 非空才出現）：探測順序放在 `java` 之前。站台執行 `module load <m1> && module load <m2> …`；成功 → `pass`「loaded: <m1>, <m2>」；任一失敗 → `fail`，訊息點名第一個失敗的模組並說下一步：「cannot load module <m>: check the environment's modules, or empty them and use a self-installed Nextflow (載入不了模組 <m>：請檢查計算環境的 modules，或清空它改用自裝 Nextflow)」。
3. **java／nextflow 探測**：`modules` 非空時，兩條指令前綴同一串 `module load … && `（失敗時 java／nextflow 照樣探測、照樣回報，各自會因找不到而 fail）；`modules` 空時指令與現在逐字相同。
4. **`site_pipeline`**（`sitePipelines` 非空才出現；一個 CE 一項結果，涵蓋所有條目）：對每一條 `{pipeline, revision, module, home}`，站台執行 `module load <module> && test -r "$<home>/main.nf" && grep -E "^\s*version\s*=" "$<home>/nextflow.config"`。判定：
   - 讀不到 `main.nf` 或 module 載入失敗 → `fail`「<pipeline> <revision>: not installed where the module says (站台找不到這個版本)」。
   - 讀到 `manifest.version`，去掉開頭 `v` 後與 `revision`（也去掉開頭 `v`）相等 → 該條通過；不等 → `fail`「<pipeline>: the site has <X>, the environment says <Y> (站台裝的是 X，設定說 Y)」。
   - `revision` 是 40 位十六進位（commit）→ 該條只要 `main.nf` 讀得到就通過，detail 加「commit revision, version not compared」。
   - 全部條目通過 → `pass`，detail 列出 `<pipeline> <revision>`。
5. **`image_library`**（CE 的 `environment` 有 `NXF_SINGULARITY_LIBRARYDIR` 才出現）：`snapshot` 把它的值放進新鍵 `singularityLibraryDir`（其餘環境變數**不**帶給站台）；`rules.clean_environment` 用 `clean_root` 同等規則檢查這個路徑（不要求在 `readRoots` 內）。站台執行 `test -r "<dir>" && test -x "<dir>"`：成功 `pass`；失敗 `fail`「the read-only image library <dir> cannot be read (唯讀映像庫讀不到)」。
6. **連線中斷**：三項新探測都照既有模式——`rc != 0 and lost_connection(res)` 時呼叫 `connection_lost()`，斷線就 `abandon()`（既有行為：只剩 connect fail＋其餘 unchecked）。
7. **順序**：`connect, work_dir, sbatch, squeue, sinfo, [modules], java, nextflow, head_queue, [site_pipeline], [image_library]`。
8. **不需要 migration**：預檢結果原本就存在 `compute_envs` 的 JSON 欄位，沒有新表或欄位（ledger 寫明）。

## 失敗先行測試（`test_station_e2e.py`，FakeSite）
- `test_pf_modules_loaded_before_java_and_nextflow`：CE `modules=["biology/Nextflow/26.10.0"]`，假 module 認得它 → 結果多一項 `modules: pass`，java／nextflow 的實際指令以 `module load biology/Nextflow/26.10.0 && ` 開頭（看 FakeSite 的 calls log）。
- `test_pf_missing_module_is_named_with_the_next_step`：假 module 不認得 → `modules: fail`，detail 含模組名與「self-installed Nextflow」。
- `test_pf_site_pipeline_version_matches` ／ `_mismatch_names_both_versions` ／ `_missing_main_nf` ／ `_v_prefix_is_ignored` ／ `_commit_revision_not_compared`。
- `test_pf_image_library_readable` ／ `_unreadable_names_the_dir`。
- `test_pf_old_environment_unchanged`：三鍵都空、沒有映像庫 → 結果名稱集合仍等於 `CHECKS`（8 項），指令紀錄與 base 逐字相同。
- `test_pf_connection_lost_during_module_probe`：模組探測時斷線 → abandon 行為。
- `test_station_envs.py`：snapshot 有 `singularityLibraryDir`（有設時為該值，沒設時 `None`），且不帶其他環境變數。

FakeSite：在 fakebin 放一支 `module` 執行檔，`module load X` 依 `self.site / "modules.allow"` 的清單決定 exit 0／1 並記進 calls log；`make_site_pipeline(home, version)` 建 `main.nf` 與含 `manifest { version = '…' }` 的 `nextflow.config`，並把 `<home>` 環境變數設給假站台的指令環境。

## 完成標準
nano4 CE 的預檢一次回報 11 項、各有白話下一步；舊環境的預檢結果逐字不變；全套綠。

## 允許更新的既有斷言（寫進 ledger）
- `test_station_envs.py::test_tc_ls_23_24_26…`：snapshot 鍵集合加 `singularityLibraryDir`。除此之外不改任何既有斷言。

## 不做
- 不改 `_verdict`、`CHECK_ORDER`、`apply_preflight`；不改站台啟動（#162 已做）；不在 nano4 實機跑（驗收表 TC-047n 處理）；不檢查映像庫裡有沒有每個映像（只檢查讀得到）。

## 上一版退回理由（2026-10-22，已在本版處理）
1. CE 三鍵到不了站台 → #162 已讓 snapshot 帶三鍵；本版再帶 `singularityLibraryDir`。2. 前置未合併 → 已合併。3. `unchecked` 會被 `_verdict` 算成未通過 → 改成條件式檢查，不出現就不影響。4. 假站台測試位置與 CHECKS 8→11 → 測試放 `test_station_e2e.py`，舊環境仍 8 項，CHECKS 不動。5. LIBRARYDIR 不可讀＝fail 並點名；`v` 前綴忽略；commit revision 不比版本；modules 失敗時 java／nextflow 照探測。

## 裁決（2026-10-23，計畫預檢後）
P2. 範圍加 `docs/TESTING.md`：把 TC-047n 那一步的 `library` 改名 `image_library`（名稱以本計畫為準）。`abf_station/launch.py::snapshot_ce` **不**帶 `singularityLibraryDir`——它只給啟動 bundle 用，不經預檢；映像庫路徑啟動時已由 CE environment 變成環境變數。
P4. 站台端再驗：`rules.clean_environment` 對 `modules`、`sitePipelines[].module` 套用與 `compute_envs._module_problem` 相同的規則（import 重用），`home` 套用 `_var_problem`；不合 → Refusal 點名鍵。站台指令裡模組名一律 `shlex.quote`。`home` 變數在站台沒設（`[ -z "${HOME_VAR:-}" ]`）→ 該條 fail「the site variable <HOME_VAR> is not set (站台沒有設定 <HOME_VAR>)」，與「未安裝」分開。加 `modules=["a;b"]` 被拒的測試。
P5. 版本只從 `manifest { … }` 區塊取：站台指令讀出 `nextflow.config` 全文，由 handlers 在 Python 端解析——找到 `manifest` 開頭的區塊（大括號配對）裡第一個 `version = '…'` 或 `"…"`；區塊外的 `version=` 不採用。加測試：`params { version = '9.9' }` 加 `manifest { version = '2.18.0' }` → 取 2.18.0；沒有 manifest 區塊 → fail「cannot read the pipeline version (讀不出版本)」。
P9. 名稱統一 `image_library`。
P10. 斷線 abandon：`rest_unchecked` 除了 `CHECK_ORDER`，再加上「這個環境適用的條件式檢查」（`modules` 非空→`modules`；`sitePipelines` 非空→`site_pipeline`；有映像庫→`image_library`），讓它們以 `unchecked` 出現。順序由 preflight 內固定的呼叫順序決定（作法 7），`CHECK_ORDER` 不改；加一個依序比對結果名稱清單的測試。
P11. 已知風險（不在本任務修）：真實 nano4 上 `module` 多半是 Lmod 的 shell function，非互動 ssh 與 sbatch 腳本未必有；FakeSite 用執行檔模擬。實機驗收（TC-047n／048n）第一步就要確認，必要時另開任務讓探測與 head.sh 先 `source /etc/profile.d/lmod.sh`（或用 `bash -l`）。

## 專長守則（backend）

### executor

- 每個網頁／API／聊天指令的動作，都呼叫專案唯一共用的動作層（一個動作一個函式）。路由處理函式裡不得有第二份邏輯。
- 每個寫入動作都必須經過專案定義的人工確認管道；沒有確認就不得寫入。
- 擁有者規則：使用者只能看到與修改自己的紀錄。篩選條件放在動作層、依呼叫者身分過濾，不能只靠畫面藏起來。
- 錯誤訊息說明發生了什麼事、使用者該怎麼處理；不露出堆疊、內部路徑或 SQL。
- 密鑰、token、密碼不得出現在日誌或任何回應中。
- 資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫「不需要 migration」的理由。

### verifier

**CONTRACT（出題）必須轉成測試案例（TC）：**
- 對等性 TC：列舉使用者可見的動作清單與動作層函式清單，兩邊一一對應（測試同時列舉兩邊，缺一邊就失敗）。
- 跨使用者 TC：用第二位使用者的 token 讀取、修改第一位的紀錄，必須被拒絕（讀與寫各一條）。
- 確認管道 TC：每個寫入動作，未經確認時不得改變資料。
- 錯誤訊息與日誌 TC：錯誤回應含原因與處理方式；日誌與回應不含密鑰。
- 有資料結構變動時，migration 可套用的 TC。

**ACCEPTANCE（閱卷）必須檢查：**
- **FAIL**：任何不經確認就能到達的寫入路徑；動作層以外出現重複的邏輯（路由處理函式自己實作）；第二位使用者能讀或改第一位的紀錄；對等性測試缺一邊；日誌或回應洩漏密鑰；結構變動沒有 migration 也沒有計畫說明。
- **「需要人看的事」**：錯誤訊息用詞是否夠白話、動作命名是否直覺等主觀問題。
- 報告固定一行：`專長守則檢查：……`（列出做了哪些檢查、結果）。
