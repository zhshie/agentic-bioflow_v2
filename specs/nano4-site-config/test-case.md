# 測試案例：nano4 站台設定檔、CE 範本與三種費率（nano4-site-config）

<!--
Written by the verifier (CONTRACT mode). Source: specs/nano4-site-config/plan.md, including its section "裁決（2026-10-22）", which replaces the older wording of "作法" wherever they differ (environment as objects, no _comment in the CE JSON, twd_per_su, NT$ = SU x twd_per_su, wildcard partitions, return shape).
There is no spec.md; the maintainer's quoted words are in the plan under "維護者原話" and are used as inputs and expected results below.
IDs use the prefix N4- so they do not collide with TC-001 ... TC-C05 already in platform/tests/test_estimate_su.py.
Comment of each test names its N4- ID. Money values are floats: compare with a tolerance of 1e-9, not ==.
-->

**規格**：`specs/nano4-site-config/plan.md`（沒有 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西時，系統怎麼反應。
- **不在範圍**：計畫明講這次不做的事；確認真的沒做。

下面「真費率檔」指 `configs/sites/su_rates.json`；「CE 範本」指 `configs/sites/nchc-nano4-ce.json`（CE ＝ compute environment，計算環境：告訴平台「去哪個節點、用哪個帳號、用哪些模組」跑 Nextflow）。SU 是國網的計算點數；1 核心跑 1 小時在一般分區＝1 SU。

## User Story 1 — 在 nano4 啟動前就能估出「約多少 SU、約多少元」（優先度 P1）

維護者原話：「建 nano4 的計算環境與費率表（國科會 0.1／學術 0.2／企業 0.37 元每核心小時）。」「開發測試可直接用計畫 `mst109178`，每次先估 SU、記帳。」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| N4-01 | 失敗先行測試 `test_tc025b_nano4_rates_price_a_ngs_task_at_0_1_twd_per_core_hour`；維護者原話（0.1／0.2／0.37） | 功能 | 真費率檔；一個 task：分區 `ngs`、1 核、跑 10 小時（realtime＝36,000,000 毫秒） | 用站台 `nano4` 算（`su_of_tasks`） | SU＝10；`twd` 的 nstc＝1.0、academic＝2.0、industry＝3.7；`unknown_reasons` 是空的 | 自動：`platform/tests/test_estimate_su.py` |
| N4-02 | 同上；計畫「測試用 `ngs`、`ngs7G`、`big-mem`」 | 功能 | 真費率檔；一個 task：分區 `ngs7G`、1 核、10 小時 | 用站台 `nano4` 算 | SU＝10；`twd` 為 1.0／2.0／3.7（`ngs7G` 被 `ngs*` 接住，不是「找不到」） | 自動：同上 |
| N4-03 | `test_tc025c_bigmem_factor_7`；裁決 4 | 功能 | 真費率檔；一個 task：分區 `big-mem`、1 核、10 小時 | 用站台 `nano4` 算 | SU＝70；`twd` 為 nstc＝7.0、academic＝14.0、industry＝25.9 | 自動：同上 |
| N4-04 | 裁決 4（NT$＝SU × 費率）；完成標準 | 功能 | 真費率檔；兩個 task：`ngs` 1 核 10 小時、`big-mem` 1 核 10 小時 | 用站台 `nano4` 算 | SU＝80；`twd` 為 8.0／16.0／29.6（兩個 task 的 SU 先加總，再乘費率） | 自動：同上 |
| N4-05 | 裁決 7（回傳形狀）；「作法」站台層級覆寫 | 功能 | 同 N4-01 的 nano4 結果 | 看回傳 | 仍有 `su`、`twd_nstc`、`twd_academic`、`unknown_reasons` 四個鍵；另有 `twd`，且 `twd` 剛好三個鍵 nstc、academic、industry；`twd_nstc` 等於 `twd.nstc`、`twd_academic` 等於 `twd.academic` | 自動：同上 |
| N4-06 | 裁決 7；完成標準「`estimate_su` 對 nano4 run 回 SU 與三種費率」 | 功能 | 一個 run 的 task 紀錄用測試注入（1 核、`big-mem`、10 小時）；真費率檔 | 分別經 `su.run_su(..., site="nano4")` 與 `actions.estimate_su(..., site="nano4", rates=真費率)` 取答案 | 兩邊都回 SU＝70 與 `twd` 7.0／14.0／25.9，兩邊答案相同（動作層真的接到新算法，不是只改了 `su_of_tasks`） | 自動：同上 |
| N4-07 | 「作法」`sites.nano4`；裁決 4 | 功能 | 真費率檔 | 讀 `sites.nano4` | `twd_per_su` 剛好是 nstc 0.1、academic 0.2、industry 0.37 三項；`partitions` 有 `ngs*`＝factor 1 與 `big-mem*`＝factor 7；沒有叫 `twd_per_core_hour` 的鍵 | 自動：同上 |
| N4-08 | 「SU 與費率缺資料就說不知道」的既有原則（su.py 檔頭）；裁決 5 | 例外 | 真費率檔；一個 task：分區 `gpu`（nano4 的鍵 `ngs*`、`big-mem*` 都對不上）、1 核、10 小時 | 用站台 `nano4` 算 | SU 是 None（不是 0，也不是猜的數字）；`unknown_reasons` 裡有一句點名分區 `gpu`；說明文字不含檔案路徑或程式堆疊 | 自動：同上 |

## User Story 2 — 分區萬用字元規則，且不影響 T3（優先度 P1）

裁決 5：分區的鍵可帶尾端 `*`（前綴比對）；先精確比對，沒有再找「最長的、以 `*` 結尾且前綴相符」的鍵；T3 沒有 `*` 鍵，行為不變。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| N4-09 | 裁決 5「先精確比對」 | 功能 | 手做費率：站台 `testsite` 的分區有 `ngs*`＝1 與 `ngs7G`＝3；一個 task 分區 `ngs7G`、1 核、1 小時 | 算 SU | SU＝3（精確的 `ngs7G` 勝過 `ngs*`） | 自動：同上 |
| N4-10 | 裁決 5「最長的」 | 功能 | 手做費率：分區有 `ngs*`＝1 與 `ngs7*`＝2；一個 task 分區 `ngs7G`、1 核、1 小時 | 算 SU | SU＝2（前綴較長的鍵勝出） | 自動：同上 |
| N4-11 | 裁決 5「T3 沒有 `*` 鍵，行為不變」 | 例外 | 真費率檔；T3 一個 task：分區 `ct56x`（`ct56` 的前綴相同但 T3 沒有萬用字元鍵）、1 核、1 小時 | 用站台 `taiwania3` 算 | SU 是 None，`unknown_reasons` 點名分區 `ct56x`（沒有因為新規則而被偷偷算出數字） | 自動：同上 |
| N4-12 | 裁決 7「沒有 `twd_per_su` 的站台不加 `twd` 鍵」 | 功能 | 真費率檔 T3 的 `ct56` task（4 核 2 小時），以及手做費率的 `testsite` | 兩者各算一次 | T3 結果仍剛好是 `su`、`twd_nstc`、`twd_academic`、`unknown_reasons` 四個鍵，沒有 `twd`，且 SU＝8、`twd_nstc`＝0.64；`testsite` 同樣四個鍵、沒有 `twd` | 自動：同上 |
| N4-13 | 「作法」「沒給 site → 行為同現在」 | 功能 | 真費率檔；用 `actions.estimate_su` 不傳 `site`，task 紀錄用測試注入（`ct56`、1 核、1 小時） | 取答案 | 用預設站台 `taiwania3` 算：SU＝1，沒有 `twd` 鍵；`default_site` 仍是 `taiwania3` | 自動：同上 |
| N4-14 | 「既有 T3 案例全部保留、斷言不改」 | 功能 | `test_estimate_su.py` 內既有的所有測試（如 TC-001…TC-040、E4 兩條） | 跑 `platform/tests/test_estimate_su.py` | 既有測試全部通過，包含 `test_tc023`、`test_tc024`、`test_tc025`、`test_tcc03`、`test_tcc05` | 自動：同上 |
| N4-15 | 「既有 T3 案例全部保留、斷言不改」 | 功能 | 實作完成後的 `git diff` | 看 `platform/tests/test_estimate_su.py` 對 base 的差異 | 只有新增的測試與註解；沒有任何既有斷言被刪、被放寬、被改預期值、被跳過 | 手動：`docs/TESTING.md` 的「nano4 site config」一節 |

## User Story 3 — nano4 的 CE 範本（優先度 P1）

維護者原話：「nano4 若週四跑不通 → 先在 `/work/u9613010` 自裝 Nextflow＋插件跑通」，所以範本的 `modules` 必須可留空、`environment` 可加 `PATH`／`NXF_PLUGINS_DIR`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| N4-16 | 失敗先行測試第 3 條；完成標準「CE JSON 通過驗證」 | 功能 | `configs/sites/nchc-nano4-ce.json` 存在，是合法 JSON，頂層是一個物件 | 把它當 `config`、類型 `slurm-platform`，交給 `compute_envs.clean`（`_check_slurm` 那一關） | 通過，沒有丟出 `CEError` | 自動：同上 |
| N4-17 | 「作法」CE JSON 欄位；維護者原話「用計畫 `mst109178`」 | 功能 | 同 N4-16 的檔案 | 讀欄位 | `headQueue`＝`ngsconsole`；`headJobOptions`＝`-A mst109178 -c 1 --mem=8G -t 2-00:00:00`；`workDir`＝`/work/u9613010/runs`；`readRoots`＝`["/work/u9613010"]` | 自動：同上 |
| N4-18 | 「作法」`modules`／`siteConfigVars`／`sitePipelines` | 功能 | 同上 | 讀欄位 | `modules`＝`["biology/Nextflow/26.10.0"]`；`siteConfigVars`＝`["NFCORE_SITE_CONFIG","NFCORE_SITE_REFERENCES"]`；`sitePipelines` 剛好一筆：pipeline `nf-core/ampliseq`、revision `2.18.0`、module `biology/nf-core-ampliseq/2.18.0`、home `NFCORE_AMPLISEQ_HOME` | 自動：同上 |
| N4-19 | 裁決 2（environment 的物件格式） | 功能 | 同上 | 讀 `environment` | 剛好三項，且 `head`、`compute` 皆為 true：`NXF_SINGULARITY_LIBRARYDIR`＝`/work/envstack/apps/application/biology/nf-core/singularity-cache`；`NXF_SINGULARITY_CACHEDIR`＝`/work/u9613010/.singularity`；`NXF_OPTS`＝`-Xms512m -Xmx4g`（可寫快取與唯讀快取分開） | 自動：同上 |
| N4-20 | 裁決 3（CE JSON 不放 `_comment`） | 功能 | 同上 | 看檔案頂層的鍵 | 沒有 `_comment`，也沒有 `compute_envs` 不認得的鍵（頂層的鍵全部在 slurm 設定允許的清單內） | 自動：同上 |
| N4-21 | 維護者原話「自裝 Nextflow」；裁決 3 | 功能 | 把 N4-16 的設定改成退路版：`modules` 設為 `[]`，`environment` 再加兩項（`PATH`＝`/work/u9613010/nextflow/bin:$PATH`、`NXF_PLUGINS_DIR`＝`/work/u9613010/.nextflow/plugins`，`head`、`compute` 皆 true） | 同樣交給 `compute_envs.clean` | 通過，沒有丟出 `CEError`（空的 `modules` 與多出的 `PATH`／`NXF_PLUGINS_DIR` 都被接受） | 自動：同上 |
| N4-22 | 裁決 3「寫在 `specs/nano4-site-config/ledger.md`」 | 功能 | 實作完成後的 `specs/nano4-site-config/ledger.md` | 讀它 | 寫明自裝 Nextflow 時要把 `modules` 清空、`environment` 加 `PATH=/work/u9613010/nextflow/bin:$PATH` 與 `NXF_PLUGINS_DIR=/work/u9613010/.nextflow/plugins`，並註明由 L3 的 `docs/SETTINGS.md` 再抄 | 自動：同上（讀檔案內容比對） |

## User Story 4 — 國網模組缺席時的退路 config `nchc-nano4.config`（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| N4-23 | 「作法」`process.executor='slurm'` | 功能 | `configs/sites/nchc-nano4.config` 存在 | 讀內容 | 設定了 `process.executor`（或 `process { executor = ... }`）為 `slurm` | 自動：同上（文字比對；無法在此執行 Nextflow） |
| N4-24 | 「作法」`resourceLimits` | 功能 | 同上 | 讀內容 | 有 `resourceLimits`，且寫明 cpus、memory、time 三個上限 | 自動：同上 |
| N4-25 | 「作法」`singularity{enabled=true; autoMounts=true}` | 功能 | 同上 | 讀內容 | `singularity` 區塊裡 `enabled` 為 true、`autoMounts` 為 true | 自動：同上 |
| N4-26 | 「作法」`process.queue` 以 ngs 分區為準、可由 `SLURM_PARTITION` 覆寫 | 功能 | 同上 | 讀內容 | `process.queue` 的值引用環境變數 `SLURM_PARTITION`，且沒設時的預設值是 ngs 開頭的分區名 | 自動：同上 |
| N4-27 | 「作法」`clusterOptions="-A ${SLURM_ACCOUNT}"` | 功能 | 同上 | 讀內容 | `clusterOptions` 等於 `-A ${SLURM_ACCOUNT}`（帳號由環境變數帶入，檔案裡沒有寫死帳號） | 自動：同上 |
| N4-28 | 「作法」「不抄 Taiwania-3 的 box 表」 | 不在範圍 | 同上 | 讀內容並與 `configs/sites/nchc.config` 比較 | 沒有 `NCHC_BOXES`、`nchcBox`、`maxHours` 這類 box 表與挑箱函式 | 自動：同上 |

## User Story 5 — 出處與核對步驟有留下（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| N4-29 | 裁決 6（既有 `test_tc024`：每個非 null 係數都要在 ledger 找得到出處） | 功能 | `specs/estimate-su/ledger.md` | 讀它，並跑 `test_tc024` | 內文有 `ngs*`、`big-mem*` 兩個分區係數與出處：創進一號費率網址 `https://iservice.nchc.org.tw/nchc_service/nchc_service_qa.php?target=54`、`lions.nchc.org.tw/ngs.jsp`，以及倍率推導 0.56／0.08＝7；`test_tc024` 不改斷言且通過 | 自動：同上 |
| N4-30 | 裁決 8（手動核對項） | 功能 | `docs/TESTING.md` | 找「nano4 site config」一節 | 該節存在，寫有 `git diff --name-only origin/v3...HEAD` 的核對步驟與要看什麼，照著做得出 N4-15、N4-32、N4-33 的結論 | 手動：`docs/TESTING.md` |
| N4-31 | 後端專長守則「資料結構或資料內容有變動，必須附 migration，或在計畫裡明寫不需要的理由」 | 功能 | `specs/nano4-site-config/ledger.md` | 讀它 | 明寫「不需要 migration」與理由（只改 JSON 設定檔與 `su.py`，沒動資料庫表） | 手動：`docs/TESTING.md` 的「nano4 site config」一節 |

## User Story 6 — 不在範圍（計畫「不做」與裁決 7、8）

計畫「不做」：不改站台程式、不實際建立 CE、不改 T3 任何設定；裁決 7：`actions.estimate_su` 不改簽名。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| N4-32 | 「不改 T3 任何設定」 | 不在範圍 | 真費率檔 | 讀 T3 與 `nchc` 站台、頂層費率 | `default_site`＝`taiwania3`；頂層 `nstc_twd_per_su`＝0.08、`academic_twd_per_su`＝0.08、`industry_twd_per_su`＝0.16；T3 的 `ct56`…`ct8k` 係數仍是 1、`ct2k-amd` 仍是 null；`nchc` 站台七個 `ngs…` 分區仍全是 null | 自動：同上 |
| N4-33 | 「不改 T3 任何設定」 | 不在範圍 | 實作完成後的 `git diff` | 看 `configs/sites/nchc.config`、`configs/sites/nchc-ce.json.in`，以及 `su_rates.json` 中 `taiwania3`／`nchc` 兩段與頂層費率 | `nchc.config`、`nchc-ce.json.in` 完全沒有被改；`su_rates.json` 只新增 `sites.nano4`，既有那幾段一個字都沒動 | 手動：`docs/TESTING.md` 的「nano4 site config」一節 |
| N4-34 | 「不改站台程式、不實際建立 CE」 | 不在範圍 | 實作完成後 `git diff --name-only origin/v3...HEAD` | 列出被改的檔案 | 只有：`configs/sites/nchc-nano4.config`、`configs/sites/nchc-nano4-ce.json`、`configs/sites/su_rates.json`、`platform/abf_platform/su.py`、`platform/tests/test_estimate_su.py`、`specs/estimate-su/ledger.md`、`specs/nano4-site-config/ledger.md`、`docs/TESTING.md`，以及本任務的 `test-case*.md`／`plan.md`；沒有 `compute_envs.py`、`actions`、站台腳本；也沒有任何「已建立 CE」的資料或紀錄 | 手動：`docs/TESTING.md` 的「nano4 site config」一節 |
| N4-35 | 裁決 7「`actions.estimate_su` 不改簽名」 | 不在範圍 | `actions.estimate_su` | 檢查它的參數 | 參數仍是 `(index_path, run_name, *, caller, platform_path, site, rates, tasks_of)`，沒有新增或改名 | 自動：同上 |

## 憲法與安全網

這次會碰到的條文：原則 I-1（每支程式檔頭要說明為何自己寫）、原則 IV-9（數字來自檔案，不來自記憶或程式碼）、原則 I-2（不存第二份 run 狀態）、以及後端專長守則（擁有者規則、密鑰、資料結構）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| N4-C1 | 原則 IV-9：費率與分區係數是資料，不是程式裡的數字 | 功能 | `platform/abf_platform/su.py` 改完 | 在 `su.py` 全文找 `0.08`、`0.24`、`0.1`、`0.2`、`0.37` 這些費率數字，以及 `ngs\d`、`big-mem`、`taiwania`、`slurm`、`sbatch`、`squeue` | 一個都沒有（既有 `test_tcc03`、`test_tcc05` 通過；萬用字元比對的程式不寫死分區名） | 自動：同上 |
| N4-C2 | 原則 I-1：檔頭說明 | 功能 | `su.py` 改完 | 看前 40 行 | 仍有 `# Nothing existing:` 或 `# Not …:` 開頭的說明行（既有 `test_tcc04` 通過） | 自動：同上 |
| N4-C3 | 原則 I-2：不存第二份狀態 | 功能 | 用站台 `nano4` 呼叫過 `estimate_su` 之後 | 比對資料庫的表與欄位 | 與呼叫前完全相同，沒有新表、新欄位（既有 `test_tcc02` 通過） | 自動：同上 |
| N4-C4 | 專長守則「密鑰、token、密碼不得出現」 | 功能 | CE 範本 | 對整份設定跑 `compute_envs.credential_findings` | 回傳空清單；檔案裡沒有金鑰、token、密碼樣式的值（`mst109178` 是計畫代號，不是憑證） | 自動：同上 |
| N4-C5 | 專長守則「擁有者規則」：只能看自己的 run | 例外 | 兩位使用者，run-a 屬於使用者 1；測試注入 nano4 的 task 紀錄 | 使用者 2 用 `actions.estimate_su(..., site="nano4")` 查 run-a；再查一個不存在的 run | 兩個答案一樣：「找不到這個 run」，不含 SU 與 `twd`；使用者 1 自己查則得到 SU 與 `twd` | 自動：同上 |

<!--
Rules for the writer:
- 專長守則（backend）對照：對等性 TC → N4-35（動作層簽名不變，既有 parity 測試照舊）；跨使用者 TC → N4-C5；確認管道 TC → 本任務沒有新增寫入動作（只讀費率檔、不改資料），所以沒有對應 TC；錯誤訊息與日誌 → N4-08、N4-C4；migration → N4-31、N4-C3。
- 維護者三句原話對照：第 1 句 → N4-01、N4-03、N4-07；第 2 句 → N4-17、N4-01；第 3 句（裁示 17）→ N4-21、N4-22。
-->
