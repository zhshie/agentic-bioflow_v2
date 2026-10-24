# 測試案例：nano4 計算環境範本收進 16S 實跑的四個修正（nano4-ce-fixes）

<!--
Written by the verifier (CONTRACT mode). Source: specs/nano4-ce-fixes/plan.md, including "裁決" and "裁決二". There is no spec.md and the plan's "維護者原話" is the developer-agent's record of the 2026-10-24 nano4 run (ampliseq 2.18.0, r1-r3), not the maintainer's literal words; those four facts are used as inputs and expected results below. No expected behaviour is invented beyond the plan.
IDs use the prefix N4F- so they do not collide with TC-... and N4-... in platform/tests/test_estimate_su.py. The comment of each test names its N4F- ID.
-->

**規格**：`specs/nano4-ce-fixes/plan.md`（沒有 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；確認真的沒做。

名詞：「CE 範本」指 `configs/sites/nchc-nano4-ce.json`（CE ＝ compute environment，計算環境：告訴平台「去哪個節點、載哪些模組、設哪些環境變數」跑 Nextflow）。「站台」指國網 nano4 叢集。`<site_user>` 是範本裡代替真實帳號的佔位字。「映像」指 Singularity 容器映像檔（流程要用的軟體包）。「別名」指同一個映像在不同流程裡被叫成的不同檔名。

四個實測事實（計畫「維護者原話」）：
1. 站台離線且插件目錄沒有 `nf-tower` → CE 的 `NXF_PLUGINS_DIR` 要指到使用者自己的 `/work/<site_user>/abf/nxf-plugins`。
2. `NFCORE_SITE_REFERENCES` 會弄壞 ampliseq → 從 `siteConfigVars` 拿掉，只留 `NFCORE_SITE_CONFIG`。
3. 站台唯讀的 `ref_taxonomy_storage` 沒有 DADA2 silva 138.2 → 只在文件寫參數 `ref_taxonomy_storage: /work/<site_user>/abf/ref_taxonomy_storage`，不進 CE。
4. 站台映像庫有壞檔（存下來的 404 HTML）→ CE 的 `NXF_SINGULARITY_LIBRARYDIR` 指到 `/work/<site_user>/abf/singularity-lib`；文件給建庫指令與辨認壞映像的方法。

## User Story 1 — 照範本建的 CE 不會再撞到四個坑中的三個（CE 範本；優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| N4F-01 | 事實 2；作法 1；失敗先行測試 1 | 功能 | 讀 CE 範本原文 | 看 `siteConfigVars` | 剛好等於 `["NFCORE_SITE_CONFIG"]`，不多不少 | 自動：`platform/tests/test_estimate_su.py::test_n4ce_template_drops_site_references_and_sets_plugins_dir` 與 `test_n4_17_to_20_ce_fields` |
| N4F-02 | 事實 2；失敗先行測試 1 | 功能 | 讀 CE 範本原文 | 在整個檔案文字裡找 `NFCORE_SITE_REFERENCES` | 找不到（不只是清單裡沒有，連別處也沒有） | 自動：同 N4F-01 的新測試 |
| N4F-03 | 事實 1；作法 1；裁決 2 | 功能 | 讀 CE 範本 `environment` | 數名稱叫 `NXF_PLUGINS_DIR` 的項目 | 恰有一個，值是 `/work/<site_user>/abf/nxf-plugins`，`head` 與 `compute` 都是 true | 自動：同 N4F-01 的新測試 |
| N4F-04 | 事實 4；作法 1 | 功能 | 讀 CE 範本 `environment` | 看 `NXF_SINGULARITY_LIBRARYDIR` | 值是 `/work/<site_user>/abf/singularity-lib`，`head` 與 `compute` 都是 true | 自動：同 N4F-01 的新測試與 `test_n4_17_to_20_ce_fields` |
| N4F-05 | 作法 1（最終順序）；會改變的既有斷言 2 | 功能 | 讀 CE 範本 `environment` | 看整份清單與順序 | 剛好四項，順序是 `NXF_SINGULARITY_LIBRARYDIR`、`NXF_SINGULARITY_CACHEDIR`、`NXF_OPTS`、`NXF_PLUGINS_DIR`；每項都是物件形式且 `head: true, compute: true` | 自動：`test_n4_17_to_20_ce_fields` |
| N4F-06 | 作法 1 | 功能 | 讀 CE 範本 | 看 `NXF_SINGULARITY_CACHEDIR` 與 `NXF_OPTS` | `NXF_SINGULARITY_CACHEDIR` 仍是 `/work/<site_user>/.singularity`；`NXF_OPTS` 仍是 `-Xms512m -Xmx4g` | 自動：`test_n4_17_to_20_ce_fields` |
| N4F-07 | 作法 1（其餘鍵不動） | 功能 | 讀 CE 範本 | 看 `headQueue`、`headJobOptions`、`modules`、`sitePipelines`、`suSite`、`workDir`、`readRoots` | 全與改動前相同：`ngsconsole`、`-A mst109178 -c 1 --mem=8G -t 2-00:00:00`、`["biology/Nextflow/26.10.0"]`、ampliseq 2.18.0 那一筆、`nano4`、`/work/<site_user>/runs`、`["/work/<site_user>"]` | 自動：`test_n4_17_to_20_ce_fields` 與 `test_su_in_get_run.py::test_the_nano4_ce_file_validates_and_snapshot_has_no_suSite` |
| N4F-08 | 作法 1；憲法第 3 條；失敗先行測試 1 | 功能 | 讀 CE 範本原文 | 找 `u9613010`、`/work/envstack`、`<nano4 read-only image library>` | 三者都找不到；範本裡路徑只用 `<site_user>` 佔位 | 自動：同 N4F-01 的新測試（真實名與 envstack）；舊佔位不見由 `test_n4_17_to_20_ce_fields` 的完整清單比對守住 |
| N4F-09 | 作法 1；完成標準 | 功能 | 把範本的 `<site_user>` 換成測試帳號後 | 交給 CE 驗證 | 通過驗證；範本沒有 `_comment` 鍵，所有鍵都在 Slurm CE 允許的鍵之內 | 自動：`test_n4_16_ce_passes_validation` 與 `test_n4_17_to_20_ce_fields` |
| N4F-10 | 作法 1；既有斷言 3 | 功能 | 填好佔位的範本副本，模組清空 | 把已有的 `NXF_PLUGINS_DIR` 項的值換成 `/tmp/abf-test/.nextflow/plugins`，只再加一項 `PATH`，交給 CE 驗證 | 通過驗證；換完後 `NXF_PLUGINS_DIR` 仍然只有一個；測試不再用 `+=` 加第二個同名項 | 自動：`test_n4_21_self_installed_nextflow_variant` |
| N4F-11 | 作法 1；既有斷言 4；`specs/nano4-site-config/ledger.md` 範圍 | 功能 | 讀 `specs/nano4-site-config/ledger.md` 的「自裝 Nextflow」一節 | 找舊字串，再找新補的一句 | `modules`、`PATH=/work/<site_user>/nextflow/bin:$PATH`、`NXF_PLUGINS_DIR=/work/<site_user>/.nextflow/plugins`、`docs/SETTINGS.md`、`不需要 migration` 全都還在；另有一句說「CE 現在已預設 `NXF_PLUGINS_DIR`，自裝時改成覆寫」；`test_n4_22_n4_31_ledger_notes` 內容沒被改 | 自動：`test_n4_22_n4_31_ledger_notes`（舊字串）；新補的一句：手動，閱卷人讀該檔 |
| N4F-12 | 環境事實（既有驗證不擋同名重複）；作法 1 | 例外 | 假設範本裡出現第二個 `NXF_PLUGINS_DIR` | 看新測試怎麼判 | 測試會變紅，因為它自己數「恰有一個」，不靠 CE 驗證擋；閱卷人讀測試確認它用的是「數量等於 1」而不是「有就好」 | 自動：同 N4F-01 的新測試 |

## User Story 2 — 下一個人只看文件就能建好使用者插件目錄、映像庫，並知道 ampliseq 的參考參數（文件；優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| N4F-13 | 事實 1；裁決二 1；失敗先行測試 2 | 功能 | 讀 `docs/SETTINGS.md` | 找插件版本 | 含 `nf-tower@1.28.2`，並註明這是 nano4 實跑版本、1.28.3 未在 nano4 驗證 | 自動：`test_n4ce_docs_carry_the_four_fixes`（只查字串 `nf-tower@1.28.2`）；「註明實跑版本與 1.28.3 未驗證」：手動，閱卷人讀 `docs/SETTINGS.md` |
| N4F-14 | 事實 1；作法 2 ① | 功能 | 讀 `docs/SETTINGS.md` 新小節 "Before you create the nano4 environment" | 看第 ① 步 | 指令是：在 `/work/<site_user>/abf/nxf-plugins` 為站台插件目錄的每一項建符號連結，再執行 `nextflow plugin install nf-tower@1.28.2` | 手動：閱卷人讀 `docs/SETTINGS.md` |
| N4F-15 | 作法 2 ①；裁決二 2 | 功能 | 讀同一步 | 看站台插件目錄的真路徑從哪來 | 文件教「載入模組後執行 `echo $NXF_PLUGINS_DIR`」取得；文件沒有寫死一個猜測的站台插件路徑 | 手動：閱卷人讀 `docs/SETTINGS.md` |
| N4F-16 | 事實 4；作法 2 ②；失敗先行測試 2 | 功能 | 讀 `docs/SETTINGS.md` | 找建庫步驟 | 含 `/work/<site_user>/abf/singularity-lib`；指令對站台庫 `<nano4 read-only image library>` 的每個檔建符號連結 | 自動：`test_n4ce_docs_carry_the_four_fixes`（路徑字串）；符號連結指令：手動，閱卷人讀 `docs/SETTINGS.md` |
| N4F-17 | 事實 4；作法 2 ② | 功能 | 讀同一步 | 看壞映像怎麼處理 | 已知壞映像 `bioconductor-biostrings-2.58.0`、`bambu` 要用好的下載版本取代，且每個別名檔名都放一份 | 手動：閱卷人讀 `docs/SETTINGS.md` |
| N4F-18 | 事實 4；作法 2 ③；失敗先行測試 2 | 功能 | 讀 `docs/SETTINGS.md` | 找辨認壞映像的說明 | 說 `file <img>` 顯示 `HTML document`（或檔案只有幾 KB）就是壞；好的顯示 `Singularity image` 或 `squashfs`；`file ` 與 `HTML` 同時出現 | 自動：`test_n4ce_docs_carry_the_four_fixes`（查 `file ` 加 `HTML`）；「好映像長相」：手動 |
| N4F-19 | 作法 2 ③ | 功能 | 讀同一步 | 找掃描指令 | 有一行 `for f in …; do file "$f"; done \| grep -i html` 形式的指令 | 手動：閱卷人讀 `docs/SETTINGS.md` |
| N4F-20 | 事實 3；作法 2 ④；失敗先行測試 2 | 功能 | 讀 `docs/SETTINGS.md` | 找 ampliseq 參考參數 | 含 `ref_taxonomy_storage: /work/<site_user>/abf/ref_taxonomy_storage`，並說明要先建立該目錄、此參數是每次 run 的參數、不是 CE 鍵 | 自動：`test_n4ce_docs_carry_the_four_fixes`（查 `ref_taxonomy_storage`）；「每次 run 的參數、不是 CE 鍵」：手動 |
| N4F-21 | 事實 2；作法 2（說明為何拿掉） | 功能 | 讀 `docs/SETTINGS.md` | 找 `NFCORE_SITE_REFERENCES` 的說明 | 說明人類 iGenomes 設定會破壞 ampliseq，所以拿掉；真需要它的管線（如 rnaseq）在那次 run 的設定另加，不進這份 16S 範本 | 手動：閱卷人讀 `docs/SETTINGS.md` |
| N4F-22 | 作法 2（佔位表）；作法 1 最後一點 | 功能 | 讀 `docs/SETTINGS.md` 佔位表 | 看新增與保留的列 | 新增一列說明 `/work/<site_user>/abf/` 是使用者自己的 abf 目錄，三個子目錄 `nxf-plugins`、`singularity-lib`、`ref_taxonomy_storage` 由使用者建立；`<nano4 read-only image library>` 那列仍在，註明「建庫指令用」 | 手動：閱卷人讀 `docs/SETTINGS.md` |
| N4F-23 | 作法 2（自裝變體）；裁決 2 | 功能 | 讀 `docs/SETTINGS.md` 的自裝 Nextflow 說明 | 看 `NXF_PLUGINS_DIR` 怎麼講 | 寫成「CE 已有，自裝時是覆寫成 `/work/<site_user>/.nextflow/plugins`，不是再加一條」 | 手動：閱卷人讀 `docs/SETTINGS.md` |
| N4F-24 | 作法 2（依序 ①②③④） | 功能 | 讀 `docs/SETTINGS.md` | 看 "Before you create the nano4 environment" 小節 | 標題存在，且依序給 ① 建 `nxf-plugins`、② 建 `singularity-lib`、③ 怎麼看壞映像、④ `ref_taxonomy_storage` | 手動：閱卷人讀 `docs/SETTINGS.md` |
| N4F-25 | 作法 3；失敗先行測試 2 | 功能 | 讀 `docs/SITE_ADAPTER.md` "Image cache" 段 | 看新補的句子 | 含 `singularity-lib`，並說某些站台映像是壞檔、用使用者映像庫疊在上面，指向 `SETTINGS.md`；原有的 `NXF_SINGULARITY_LIBRARYDIR` 與 PITFALLS 52 敘述仍在 | 自動：`test_n4ce_docs_carry_the_four_fixes`（SITE_ADAPTER 含 `singularity-lib`）；指向 SETTINGS：手動 |
| N4F-26 | 作法 3（PITFALLS 格式） | 功能 | 讀 `docs/PITFALLS.md` 最後一條 | 看新條目編號與格式 | 編號是 54（接在現有最後一條 53 之後），英文，標題加日期，格式同 52、53（粗體標題、What was seen、Fix） | 手動：閱卷人讀 `docs/PITFALLS.md` |
| N4F-27 | 作法 3；環境事實（症狀要寫清楚） | 功能 | 讀新條目 | 看內容 | 寫清「離線站台缺 nf-tower 插件」「站台映像庫有壞映像」「iGenomes 設定弄壞 ampliseq」三個症狀與各自修法；症狀要具體到下一個人看得出自己是不是同一個問題 | 手動：閱卷人讀 `docs/PITFALLS.md` |
| N4F-28 | 作法 3（不改舊條目） | 功能 | 比對 base 與 HEAD 的 `docs/PITFALLS.md` | 看 diff | 只有檔尾新增行；52、53 及更早的條目一字未動 | 手動：閱卷人跑 `git diff origin/v3...HEAD -- docs/PITFALLS.md` |
| N4F-29 | 作法 3 | 功能 | 讀 `docs/TESTING.md` nano4 acceptance 一節 | 看 TC-047n 之前 | 補了一句：確認 `abf-platform ce show nano4` 的 `siteConfigVars` 只有 `NFCORE_SITE_CONFIG`、`environment` 含 `NXF_PLUGINS_DIR`；TC-047n 到 TC-051n 與原 TC-047 到 TC-053 仍都在 | 自動：`tests/docs_nano4_acceptance.sh`（五個 ID 仍在）；新補的一句：手動，閱卷人讀 `docs/TESTING.md` |
| N4F-30 | 範圍：檔案（TESTING.md 只動兩處） | 功能 | 比對 base 與 HEAD 的 `docs/TESTING.md` | 看 diff | 只改兩處：「nano4 site config」一節第 1 項的允許檔案清單（把本任務的檔案列進去），以及 N4F-29 的那一句；其他行一字未動 | 手動：閱卷人跑 `git diff origin/v3...HEAD -- docs/TESTING.md` |
| N4F-31 | 憲法第 3 條；完成標準；作法 2 開頭「真值只在這裡」 | 功能 | 看本次 diff 在 SETTINGS.md 以外新增的行 | 找 `u9613010` 與 `/work/envstack` | 本次改動沒有在 `docs/SETTINGS.md` 以外的檔案新增這兩個字串（舊檔裡原有的不算）；真路徑只出現在 `docs/SETTINGS.md` | 手動：閱卷人跑 `git diff origin/v3...HEAD` 並搜尋新增行 |
| N4F-32 | 作法 3 與「不受影響、確認過的 pin」 | 功能 | 跑文件鍵檢查 | 執行 `bash tests/docs_nano4_keys.sh` | 全綠：`configs/sites/nchc-nano4-ce.json`、`NXF_SINGULARITY_LIBRARYDIR`、`taiwania3.*nano4`、`Reserved`、52 與 53 的標題等字串都還在原文件 | 自動：`tests/docs_nano4_keys.sh` |

## User Story 3 — 只改該改的，既有的東西不退步（完成標準與不做；優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| N4F-33 | 完成標準 1 | 功能 | 完成後的分支，在 WSL | 跑整套測試 | 全綠 | 自動：`tests/run_all.sh`（WSL） |
| N4F-34 | 完成標準 2 | 功能 | 完成後的分支 | 跑 `bash tests/no_hardcoded_paths.sh` | 全綠（該檔存在，故不可略過） | 自動：`tests/no_hardcoded_paths.sh` |
| N4F-35 | 失敗先行測試 | 功能 | 兩條新測試與 base 的 CE 範本 | 閱卷人把新測試對照 base 範本 | `test_n4ce_template_drops_site_references_and_sets_plugins_dir` 與 `test_n4ce_docs_carry_the_four_fixes` 都存在；對 base 範本會紅（base 有 `NFCORE_SITE_REFERENCES`、沒有 `NXF_PLUGINS_DIR`），改完才綠 | 自動：`platform/tests/test_estimate_su.py` |
| N4F-36 | 完成標準 3；「會改變的既有斷言」1–3 | 功能 | 比對 base 與 HEAD 的 `platform/tests/test_estimate_su.py` | 逐行看 diff | 被改的既有斷言只有計畫點名的三處：(1) N4-17～20 的 `siteConfigVars` 改為 `["NFCORE_SITE_CONFIG"]`；(2) `environment` 清單的 LIBRARYDIR 值與尾端加 `NXF_PLUGINS_DIR` 一項；(3) N4-21 改成換值而非再加一項並斷言只有一個。沒有任何測試被刪、跳過或放寬 | 手動：閱卷人跑 `git diff origin/v3...HEAD -- platform/tests/test_estimate_su.py` |
| N4F-37 | 既有斷言 4；既有斷言 5 | 功能 | 比對 base 與 HEAD 的測試檔 | 看 `test_n4_22_n4_31_ledger_notes` 與 `_filled()` | `test_n4_22_n4_31_ledger_notes` 一字未動；`_filled()` 內對 `<nano4 read-only image library>` 的 replace 仍保留 | 自動：`test_n4_22_n4_31_ledger_notes` 綠；一字未動：手動看 diff |
| N4F-38 | 完成標準 4；範圍：檔案 | 功能 | 完成後的分支 | 跑 `git diff --name-only origin/v3...HEAD` | 只含：`configs/sites/nchc-nano4-ce.json`、`docs/SETTINGS.md`、`docs/SITE_ADAPTER.md`、`docs/TESTING.md`、`docs/PITFALLS.md`、`platform/tests/test_estimate_su.py`、`specs/nano4-ce-fixes/ledger.md`、`specs/nano4-site-config/ledger.md`；加上計畫與測試案例檔（`specs/nano4-ce-fixes/plan.md`、`test-case.md`、`test-case-overview.md`，由流程放入） | 手動：`docs/TESTING.md`「nano4 site config」一節第 1 項 |
| N4F-39 | 不做：不改驗證、不新增 CE 鍵、不改程式；作法 4 | 不在範圍 | 比對 base 與 HEAD | 看 `platform/abf_platform/compute_envs.py` 與 `_SLURM_CONFIG` | 完全沒有變動；沒有新增 CE 鍵；沒有新增 preflight 項目；除測試檔外沒有任何 `.py` 或 `.sh` 被改 | 手動：閱卷人跑 `git diff --stat origin/v3...HEAD` |
| N4F-40 | 不做（不碰的檔案） | 不在範圍 | 比對 base 與 HEAD | 看這些檔：`platform/abf_station/launch.py`、`platform/abf_launch/build.py`、`platform/abf_platform/actions/__init__.py`、`platform/abf_platform/pipeline_launch.py`、`cli.py`、`store.py`、`receiver.py`、`deploy/`、`docs/OPERATIONS.md`、`docs/INSTALL.md` | 全部沒有變動 | 手動：閱卷人跑 `git diff --name-only origin/v3...HEAD` 比對 |
| N4F-41 | 不做（閘門檔與永不編輯檔） | 不在範圍 | 比對 base 與 HEAD | 看 `hooks/`、任何 `spec.md`、既有的 `test-case*.md`、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json` | 全部沒有變動；也沒有在實作期間改動 `specs/nano4-ce-fixes/test-case.md` 與 `test-case-overview.md` | 手動：閱卷人跑 `git diff --name-only origin/v3...HEAD` 並比對提交紀錄 |
| N4F-42 | 不做（退路 config、費率、T3） | 不在範圍 | 比對 base 與 HEAD | 看 `configs/sites/nchc-nano4.config`、`configs/sites/su_rates.json`、`configs/sites/nchc.config`、`configs/sites/nchc-ce.json.in` | 全部沒有變動 | 自動：`test_n4_23_to_28_fallback_config`、`test_n4_32_t3_untouched`（仍綠）；沒有被改：手動看 diff |
| N4F-43 | 不做：不把 `ref_taxonomy_storage` 做成 CE 設定；事實 3 | 不在範圍 | 讀 CE 範本原文 | 找 `ref_taxonomy_storage` | 範本裡找不到；這個參數只出現在文件 | 手動：閱卷人搜尋 `configs/sites/nchc-nano4-ce.json` |
| N4F-44 | 不做：不實際建立 CE、不連站台、不在 nano4 建目錄或下載映像 | 不在範圍 | 看本次所有新增內容 | 找可執行的腳本、站台連線、建立 CE 的紀錄 | 都沒有；`abf-platform ce create` 沒有被執行或記錄；建庫與建目錄的指令只以文字寫在 `docs/SETTINGS.md` | 手動：閱卷人讀 diff（除測試檔外無程式碼，文件只含指令文字） |
| N4F-45 | 作法 4；專長守則（資料結構變動要有 migration 或明寫不需要） | 功能 | 讀 `specs/nano4-ce-fixes/ledger.md` | 找 migration 的說法 | 明寫「不需要 migration」，理由是只改 JSON 範本與文件，沒有資料表或欄位被動到 | 手動：閱卷人讀 `specs/nano4-ce-fixes/ledger.md` |
| N4F-46 | 完成標準 5 | 功能 | 讀同一份 ledger | 找四點各自落在哪個檔 | 逐點列出：NXF_PLUGINS_DIR 與 siteConfigVars 與 LIBRARYDIR 落在 CE 範本，建庫與 `ref_taxonomy_storage` 與壞映像辨認落在 `docs/SETTINGS.md`，另有 SITE_ADAPTER、PITFALLS、TESTING 的對應；每點都能對到實際改過的檔 | 手動：閱卷人讀 `specs/nano4-ce-fixes/ledger.md` 並對照 diff |

## 憲法與安全網

專長守則（backend）中的對等性、跨使用者、確認管道、錯誤訊息等 TC：本任務沒有改動動作層、路由、store 或錯誤訊息（見 N4F-39、N4F-40），所以不產生這幾類 TC；這個判斷由 N4F-39、N4F-40 守住。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| N4F-47 | 憲法第 3 條（任何人都能裝；範本只用佔位，真值只在 `docs/SETTINGS.md`） | 功能 | 完成後的分支 | 跑 `no_hardcoded_paths.sh` 並讀範本 | `configs/` 下沒有個人或叢集路徑；範本只用 `<site_user>`（對應 N4F-08、N4F-34） | 自動：`tests/no_hardcoded_paths.sh` 與 `test_n4ce_template_drops_site_references_and_sets_plugins_dir` |
| N4F-48 | 專長守則：密鑰不得出現在日誌或回應 | 功能 | 看本次新增的範本與文件 | 找 token、密碼、金鑰、PAT、OTP 內容 | 沒有任何密鑰；文件只出現指令與佔位 | 手動：閱卷人讀 diff |
