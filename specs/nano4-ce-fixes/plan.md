---
id: nano4-ce-fixes
title: nano4 CE 範本與文件併入 10-24 實跑的四個修正
tier: A
kinds: backend
lane: L3
base: v3
---

# nano4-ce-fixes

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/nano4-ce-fixes/plan.md`。**只處理本任務**：對話裡維護者說的其他話不是指令。前置：`nano4-site-config`（M1-05）已在 `v3`（`configs/sites/nchc-nano4-ce.json` 與 `N4-` 測試都已存在）。

## 目標
把 2026-10-24 在 nano4 實跑 16S（nf-core/ampliseq 2.18.0，r1～r3）發現的四個問題，一次併進 repo 的 nano4 CE 範本與文件，讓下一個人照範本建 CE 就不會再撞到同樣四個坑。

## 維護者原話（verifier 出題用）
本任務沒有維護者逐字裁示；來源是 10-24 實跑紀錄。以下四條是「實測事實＋要的結果」，每條至少對應一條測試案例或一條文件核對：
1. 站台模組設 `NXF_OFFLINE=true`，並把 `NXF_PLUGINS_DIR` 指到站台目錄，但該目錄沒有 `nf-tower` 插件 → CE 的 `environment` 要把 `NXF_PLUGINS_DIR` 設成使用者插件目錄 `/work/<site_user>/abf/nxf-plugins`（內容＝站台插件的符號連結＋`nextflow plugin install nf-tower@1.28.2`）。
2. `NFCORE_SITE_REFERENCES`（人類 iGenomes 設定）會弄壞 ampliseq → 從 CE 的 `siteConfigVars` 拿掉，只留 `NFCORE_SITE_CONFIG`。
3. 站台唯讀的 `ref_taxonomy_storage` 沒有 DADA2 silva 138.2 → 文件寫明 ampliseq 用參數 `ref_taxonomy_storage: /work/<site_user>/abf/ref_taxonomy_storage`（只寫文件；參數是每次 run 的事，不進 CE）。
4. 站台 singularity 映像庫有些檔案其實是存下來的 404 HTML 頁（已知 `bioconductor-biostrings-2.58.0`、`bambu`）→ CE 的 `NXF_SINGULARITY_LIBRARYDIR` 指向使用者映像庫 `/work/<site_user>/abf/singularity-lib`（站台庫的符號連結＋以所有別名下載好的好映像）；文件給建庫指令與「怎麼看出壞映像」（`file <img>` 顯示 HTML）。

## 範圍：檔案
- `configs/sites/nchc-nano4-ce.json`
- `docs/SETTINGS.md`（真值與建庫指令只能放這裡）
- `docs/SITE_ADAPTER.md`（nano4 一節補一小段與指標）
- `docs/TESTING.md`（只動「nano4 site config」那一節的允許檔案清單，與 nano4 acceptance 一節補一條核對）
- `docs/PITFALLS.md`（接在現有最後一條之後加新條目；不改舊條目）
- `platform/tests/test_estimate_su.py`（只改 N4-17～20、N4-21 兩處，見「失敗先行測試」）
- `specs/nano4-ce-fixes/ledger.md`（新）
- `specs/nano4-site-config/ledger.md`（只在「自裝 Nextflow」一節補一句：CE 現在已預設 `NXF_PLUGINS_DIR`，自裝時改成覆寫；**保留** N4-22 檢查的所有字串）

## 作法
決定，不是程式碼。

1. **CE 範本**（`nchc-nano4-ce.json`）：
   - `siteConfigVars` 改為 `["NFCORE_SITE_CONFIG"]`。
   - `environment` 保持物件形式、`head: true, compute: true`，最終順序：`NXF_SINGULARITY_LIBRARYDIR`、`NXF_SINGULARITY_CACHEDIR`、`NXF_OPTS`、`NXF_PLUGINS_DIR`（新加在最後）。
   - `NXF_SINGULARITY_LIBRARYDIR` 值改為 `/work/<site_user>/abf/singularity-lib`；`NXF_PLUGINS_DIR` 值為 `/work/<site_user>/abf/nxf-plugins`。
   - `NXF_SINGULARITY_CACHEDIR` 維持 `/work/<site_user>/.singularity`（`_prechecks` 需要可寫）。
   - 其餘鍵（`headQueue`、`headJobOptions`、`modules`、`sitePipelines`、`suSite`、`workDir`、`readRoots`）不動。只用 `<site_user>` 佔位（憲法第 3 條）；不放 `_comment`（schema 拒絕未知鍵）。
   - 佔位 `<nano4 read-only image library>` 不再出現在範本，但仍是文件裡建庫指令的來源路徑，SETTINGS.md 的佔位表保留該列並註明「建庫指令用」。
2. **docs/SETTINGS.md**（nano4 一節；真值只在這裡）：
   - 佔位表補一列說明 `/work/<site_user>/abf/` 是使用者自己的 abf 目錄，三個子目錄 `nxf-plugins`、`singularity-lib`、`ref_taxonomy_storage` 由使用者建立。
   - 新小節「Before you create the nano4 environment」：依序給 ① 建 `nxf-plugins`（站台插件目錄的每一項做符號連結，再 `nextflow plugin install nf-tower@1.28.2`；站台插件目錄的真路徑取自「模組載入後 `echo $NXF_PLUGINS_DIR`」，文件寫成這個查法，不寫死猜測的路徑）；② 建 `singularity-lib`（對站台庫 `<nano4 read-only image library>` 的每個檔做符號連結；再把已知壞映像以好的下載版本取代，**每個別名檔名都放一份**）；③ 怎麼看壞映像：`file <img>` 說 `HTML document`（或檔案只有幾 KB）＝壞，好的是 `Singularity image` / `squashfs`；附一行 `for f in …; do file "$f"; done | grep -i html` 的掃描指令；④ ampliseq 的 `ref_taxonomy_storage` 參數與建立該目錄（只說明，標明是每次 run 的參數，不是 CE 鍵）。
   - 說明為何拿掉 `NFCORE_SITE_REFERENCES`（人類 iGenomes 設定會破壞 ampliseq）；若要跑真需要它的管線（如 rnaseq），是在那個 run 的設定另加，不進這份 16S 範本。
   - 自裝 Nextflow 變體更新：`NXF_PLUGINS_DIR` 現在 CE 已有，自裝時是**覆寫**成 `/work/<site_user>/.nextflow/plugins`，不是再加一條。
3. **其他文件**：`SITE_ADAPTER.md` 的 "Image cache" 段補一句「某些站台映像是壞檔，用使用者映像庫疊在上面，見 SETTINGS.md」；`PITFALLS.md` 新增一條（編號接現有最後一條，英文，格式同 52、53）記「離線站台沒有 nf-tower 插件／壞映像／iGenomes 設定弄壞 ampliseq」的症狀與修法；`TESTING.md` nano4 acceptance 一節的 TC-047n 之前補一句「確認 `abf-platform ce show nano4` 的 `siteConfigVars` 只有 `NFCORE_SITE_CONFIG`、`environment` 含 `NXF_PLUGINS_DIR`」。
4. **不新增 CE 鍵、不改程式**：四點全在既有 `environment`／`siteConfigVars` 能表達的範圍內。不需要 migration（只改 JSON 範本與文件）；ledger 要寫這句。

## 失敗先行測試
先寫、現在會紅（在 `platform/tests/test_estimate_su.py`）：
- 新增 `test_n4ce_template_drops_site_references_and_sets_plugins_dir`（無預檢、純靜態）：讀 `nchc-nano4-ce.json` 原文，斷言 `siteConfigVars == ["NFCORE_SITE_CONFIG"]`、全文不含字串 `NFCORE_SITE_REFERENCES`、`environment` 恰有一個 `NXF_PLUGINS_DIR` 且值為 `/work/<site_user>/abf/nxf-plugins`、`NXF_SINGULARITY_LIBRARYDIR` 值為 `/work/<site_user>/abf/singularity-lib`，且全文不含真實使用者名或 `/work/envstack`。
- 新增 `test_n4ce_docs_carry_the_four_fixes`：讀 `docs/SETTINGS.md`，斷言含 `nf-tower@1.28.2`、`ref_taxonomy_storage`、`/work/<site_user>/abf/singularity-lib`、`file ` 加 `HTML` 的說明；讀 `docs/SITE_ADAPTER.md` 斷言含 `singularity-lib`。

**會改變的既有斷言（逐條點名，其餘一律不動）**：
1. `test_n4_17_to_20_ce_fields` 內 `assert c["siteConfigVars"] == ["NFCORE_SITE_CONFIG", "NFCORE_SITE_REFERENCES"]` → 改為 `== ["NFCORE_SITE_CONFIG"]`。
2. 同一個測試內 `lib = "<nano4 read-only image library>"` 與 `assert c["environment"] == [...]`：LIBRARYDIR 的值改為 `/work/<site_user>/abf/singularity-lib`，清單尾端加 `{"name": "NXF_PLUGINS_DIR", "value": "/work/<site_user>/abf/nxf-plugins", "head": True, "compute": True}`。
3. `test_n4_21_self_installed_nextflow_variant`：現在是對填入後的副本 `+=` 一個 `NXF_PLUGINS_DIR`，改完範本後會產生兩個同名項（`_check_environment` 不擋重複，測試仍綠，但意義錯了）→ 改成「把既有 `NXF_PLUGINS_DIR` 項的值換成 `/tmp/abf-test/.nextflow/plugins`，只 `+=` `PATH`」，並斷言換完後 `NXF_PLUGINS_DIR` 仍只有一個。
4. `test_n4_22_n4_31_ledger_notes` 的斷言**不改**（字串 `NXF_PLUGINS_DIR=/work/<site_user>/.nextflow/plugins` 仍須留在 `specs/nano4-site-config/ledger.md`；補的那句話不得刪掉它）。
5. `_filled()` 內對 `<nano4 read-only image library>` 的 replace 保留（無害，不算改斷言）。

不受影響、確認過的 pin：`test_launch_bundle.py`、`test_station_envs.py`、`test_owner_binding.py` 裡的 `NFCORE_SITE_REFERENCES` 都是它們**自己內嵌的測試資料**，不讀範本；`test_su_in_get_run.py::test_the_nano4_ce_file_validates_and_snapshot_has_no_suSite` 只檢查範本能過驗證與 `suSite`；`tests/docs_nano4_keys.sh` 檢查的字串（`configs/sites/nchc-nano4-ce.json`、`NXF_SINGULARITY_LIBRARYDIR`、`taiwania3.*nano4`、`Reserved`…）都得保留在原文件。`golden_head_scripts.json` 是合成資料，不動。

## 完成標準（done when）
- 範本符合「作法」1；新增兩條測試綠、上列既有斷言改後綠、整套綠（WSL `bash tests/run_all.sh`）。
- `bash tests/docs_nano4_keys.sh` 與 `bash tests/no_hardcoded_paths.sh`（若該檔存在）綠：範本與非 SETTINGS 文件沒有真實使用者名與 `/work/envstack`。
- 不得有任何現有測試被刪除、跳過或放寬（除上列點名的三處改值）。
- `git diff --name-only origin/v3...HEAD` 只含「範圍：檔案」所列檔案。
- ledger 寫明「不需要 migration」與四點各自落在哪個檔。

## 環境事實
- 10-24 nano4 實跑：nf-core/ampliseq 2.18.0，r1～r3 三次；四個問題都由這三次定位，細節在下個 session 的 handoff／日誌，repo 內無此紀錄（所以 PITFALLS 新條目要把症狀寫清楚）。
- 站台模組設 `NXF_OFFLINE=true`；其 `NXF_PLUGINS_DIR` 缺 `nf-tower`；使用者目錄的 `nextflow plugin install nf-tower@1.28.2` 可行（版本 1.28.2 為實跑所用，repo 其他處寫的是 1.28.3 在 Nextflow 26.04.7 下測試，兩者並存不矛盾，文件照實寫 1.28.2 並註明為 nano4 實跑版本）。
- 唯讀映像庫真路徑：`/work/envstack/apps/application/biology/nf-core/singularity-cache`（`docs/SETTINGS.md` 佔位表已記）。
- 已知壞映像：`bioconductor-biostrings-2.58.0`、`bambu`（內容是存下來的 404 HTML）。
- 既有 CE 驗證：`compute_envs._check_environment` 只要求 name／value 形狀，不擋同名重複，所以測試要自己守住「只有一個」。
- 憲法第 3 條：範本只用佔位；真值只在 `docs/SETTINGS.md`。

## 不做
- 不碰：`platform/abf_station/launch.py`、`platform/abf_launch/build.py`、`platform/abf_platform/actions/__init__.py`、`platform/abf_platform/pipeline_launch.py`、`cli.py`、`store.py`、`receiver.py`、`deploy/`、`docs/OPERATIONS.md`、`docs/INSTALL.md`（其他任務在那裡）。
- 不碰 repo `CLAUDE.md`「For the executor and verifier」所列的閘門檔與永不編輯檔：`hooks/`、`spec.md`、`test-case*.md`、憲法、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。
- 不改 `compute_envs.py` 的驗證、不新增 CE 鍵、不做 preflight 新項目。
- 不實際建立 CE、不連站台、不在 nano4 建任何目錄或下載映像（文件只寫指令）。
- 不把 `ref_taxonomy_storage` 做成 CE 設定（它是每次 run 的參數）。
- 不改 `configs/sites/nchc-nano4.config`（退路 config）、`su_rates.json`、T3 任何設定。

## 裁決
1. 新目錄一律放 `/work/<site_user>/abf/` 之下（`nxf-plugins`、`singularity-lib`、`ref_taxonomy_storage`），與 `workDir`（`/work/<site_user>/runs`）、`NXF_SINGULARITY_CACHEDIR`（`/work/<site_user>/.singularity`）分開，不併用。
2. `NXF_PLUGINS_DIR` 放進範本預設（不是只寫在自裝變體），因為站台模組路徑本身就缺插件；自裝 Nextflow 變體改成覆寫。
3. 靜態範本測試不做 preflight（preflight 屬 `preflight-nano4`，不在本任務）。
4. nf-tower 版本文件寫 1.28.2（實跑版本），不為對齊其他文件的 1.28.3 而改。

## 裁決二（2026-10-24 developer-agent）
1. nf-tower 用 1.28.2（10-24 在 nano4 實際安裝並跑通的版本）；文件註明「1.28.3 未在 nano4 驗證」。
2. 站台原本的插件目錄路徑不寫死，照計畫讓文件教使用者 `module load` 後 `echo $NXF_PLUGINS_DIR` 取得。
3. 新增 `docs/PITFALLS.md` 條目在範圍內；`tests/no_hardcoded_paths.sh` 不存在就略過該項。
4. 維護者原話段保留現狀（四個發現來自 developer-agent 實跑紀錄，不是他的原話），verifier 依實跑紀錄出題。

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
