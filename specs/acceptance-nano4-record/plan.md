---
id: acceptance-nano4-record
title: 把第一次 nano4 端到端驗收（ampliseq_day5_nano4_r5）記進驗收表
tier: A
kinds: backend
lane: L3
base: v3
---

# acceptance-nano4-record

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/acceptance-nano4-record/plan.md`。**只處理本任務**。純文件、不改程式與測試。前置：`acceptance-nano4` 已在 v3（空白驗收表 `specs/007b-launch/acceptance-nano4.md`、檢查腳本 `tests/docs_nano4_acceptance.sh`）。

## 目標
2026-10-24 在 nano4 跑成了第一次 16S（nf-core/ampliseq 2.18.0）端到端。把這次的實測值照驗收表既有欄位填成一份存檔，之後同事試用或下次回歸時有「第一次成功長什麼樣」可比。沒量到的欄位誠實寫「未記錄」，不補猜。

## 維護者原話（verifier 出題用）
- 「第一里程碑＝16S（nf-core/ampliseq 2.18.0）在 nano4 端到端：Claude Desktop 或網頁 → 不經 Seqera → 啟動 → 結果頁。」（裁示 7，沿用自 `acceptance-nano4`）
- 「每次先估 SU、記帳。」（裁示 3）——本次 wallet 前後沒讀，所以 SU 以 `sacct` 實測值代替並明寫是代替（見作法）。
- 驗收表檔頭規則：「Leave a cell empty if you did not do that step, and say why in 備註. Write real values only; never paste a token.」——本次改為「沒做的格子寫『未記錄』並在備註說明」，這是維護者派工時的明確要求（空格不可，因為空格分不出「沒做」和「忘了填」）。

## 範圍：檔案
- `specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md`（新；依空白表檔頭「copy it to `specs/007b-launch/acceptance-nano4-<date>-<name>.md`」。`<name>` 用角色詞 `maintainer`，不用真實帳號）
- `specs/acceptance-nano4-record/ledger.md`（新；進度帳）

空白表 `specs/007b-launch/acceptance-nano4.md` **不動**（檔頭明寫它「stays blank」）。不碰 `docs/TESTING.md`、`docs/SETTINGS.md`、`scripts/`、`platform/`、`deploy/`、`tests/`。

## 作法
新檔 = 空白表的完整複本（九節標題、表格欄位名一字不改，`tests/docs_nano4_acceptance.sh` 釘住的欄名都要在），只填右欄。填法：

**1. Run**
- 日期 `2026-10-24`。
- 填表人：`developer-agent（依自己的 run 紀錄代填）；啟動確認人 zhshie（2026-10-24 11:14:20 在確認頁按下）`。
- 走哪條路：`未記錄`（紀錄只寫計算環境 `nano4`，沒寫走國網模組還是自裝 Nextflow，不推測）。

**2. Preflight** 十一項（`connect`…`library`）全寫 `未記錄`。備註交代：r4 因共用 ssh 連線過期在 preflight 被拒、什麼都沒建立；r5 沒留逐項輸出。

**3. SU**
- launch 前預估 SU：`未記錄`。
- wallet 前、wallet 後、差額：`未記錄`（wallet 沒讀）。
- 實測改記在備註（見第 9 節），不放進 wallet 欄，免得被誤當成 `wallet` 差額。

**4. Launch**
- run 名稱與 `<rid>`：`ampliseq_day5_nano4_r5`；平台 run id `ae0d52e5e5fe5a98`（填進 `<rid>` 位置並註明是平台 run id；與確認頁網址 `/c/<rid>` 是否同一個值：`未記錄`）。另寫：nf-core/ampliseq 2.18.0、計算環境 `nano4`、由 Claude Desktop 經平台 MCP 連接器送出。
- `head.sh` 全文：`未記錄`。
- `squeue` 輸出：`未記錄（整段輸出）`；僅記 Slurm head 作業 606916 在 partition `ngsconsole`。

**5. Way back** 三格全 `未記錄`。

**6. Trace and result page**
- trace 行數：`未記錄`（`trace.txt` 行數沒數）。補一句事實：平台收到了 Nextflow trace 事件。
- 結果頁截圖檔名：`未記錄`。

**7. Tokens must not leak** 兩格 `未記錄`。

**8. Fallback** 一格 `未記錄`（本次沒做 TC-051n）。

**9. 備註**（逐字用這些事實，不加別的）
- 完成：Nextflow log「Pipeline completed successfully」12:00:31；WorkflowStats succeededCount=71、failedCount=1（一個 task OUT_OF_MEMORY，自動重試後成功）；head 作業 606916 狀態 COMPLETED，耗時 00:46:06。
- SU 實測（代替 wallet 差額）：11:10–12:05 之間共 73 個 Slurm 作業合計 3.288 核心小時（ngs125g 0.800、ngs62g 1.174、ngsconsole 0.768、ngs16g 0.411、ngs8g 0.135），ngs 每核心小時 1 SU，約 3.3 SU；依 repo 站台費率 `nano4.twd_per_su.nstc = 0.1`，約 NT$0.33。量法：`sacct -X` 的 ElapsedRaw × AllocCPUS。
- 結果資料夾內容：barrnap、cutadapt、dada2、fastqc、input、multiqc、overall_summary.tsv、phyloseq、pipeline_info、qiime2、summary_report、treesummarizedexperiment。
- 前史：r1–r3（2026-10-23／24）因四個站台問題失敗，已由 PR #181 修（nf-tower 插件目錄、NFCORE_SITE_REFERENCES、ref_taxonomy_storage、站台 singularity 映像壞）；r4 因共用 ssh 連線過期，在 preflight 被拒、未建立任何東西。
- 未做／未記錄的步驟照上面各節標「未記錄」；第一次驗收只走 Claude Desktop，網頁路徑留 M2。

**不得出現（constitution 原則 3、`tests/no_hardcoded_paths.sh` 的精神）**：站台帳號（國網使用者名）、`/work/<帳號>/…` 路徑、家目錄路徑、任何 token。空白表的「說明」列含 `/work/u9613010` 是範本既有的；**複本不要照抄那一列的路徑**，改寫成「`/work/<site_user>`」（`docs/SETTINGS.md` 也用 `<site_user>` 當代稱）。`zhshie` 是 GitHub 帳號、repo 內多處已出現，可以寫在填表人欄；但 `specs/` 不在 `no_hardcoded_paths.sh` 的掃描範圍內，所以這條靠 verifier 人工查。

## 失敗先行測試
不新增測試檔（範圍不含 `tests/`）。用既有腳本加參數，現在會紅、做完會綠：
- `bash tests/docs_nano4_acceptance.sh docs/TESTING.md specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md`——檔案還不存在時印 `FAIL TC-012: … does not exist` 並非 0 結束；完成後印 `ok`、結束碼 0。這同時證明複本保留了 `wallet`、`squeue`、`X-ABF-Platform` 與十二個欄名。
- 不帶參數的 `bash tests/docs_nano4_acceptance.sh` 仍為 `ok`（空白表沒被動到；`git diff origin/v3 -- specs/007b-launch/acceptance-nano4.md` 為空）。
- 下列文字斷言由 verifier 用 grep 驗（每條一個 TC）：
  - 新檔含 `ampliseq_day5_nano4_r5`、`ae0d52e5e5fe5a98`、`606916`、`3.288`、`71`、`00:46:06`、`12:00:31`。
  - 新檔不含 `u9613010`、不含 `/home/`、不含 `/work/` 後面接非 `<` 的帳號、不含 `token` 的實際值。
  - 新檔**沒有任何空白右欄**（任何表格列最後一格不是空的）；wallet 前／後／差額三格都是 `未記錄`，且 3.288 與 0.33 只出現在備註列，不在 wallet 欄。
  - 新檔不含未在「作法」列出的數字或事實（verifier 逐項比對備註列，多出的算 FAIL）。

## 完成標準（done when）
- 兩個檔（新複本＋ledger）存在，`git diff --name-only origin/v3...HEAD` 只有它們。
- 上列腳本帶參數與不帶參數都 `ok`；全套 `bash tests/run_all.sh` 綠（文件改動不應影響，仍要附結果）。
- verifier PASS；ledger 記每個步驟與紅綠輸出。
- A 級：verifier PASS 後 developer-agent 直接合併，不等維護者看。

## 環境事實
- 本次 run 的事實全部來自 developer-agent 自己 2026-10-24 的 run 紀錄；維護者原話與 executor 手上除此之外沒有別的來源。來源裡沒有的值就是「未記錄」，不得從 Slack、對話或記憶補。
- 空白表六個節的欄名由 `tests/docs_nano4_acceptance.sh` 釘住：`日期`、`走哪條路`、`launch 前預估 SU`、`preflight`、`head.sh`、`trace 行數`、`grep -c token`、`wallet 前`、`wallet 後`、`差額`、`截圖檔名`、`備註`，另有 `wallet`、`squeue`、`X-ABF-Platform`。複本是整份複製，所以自然都在。
- nano4 的 SU 費率：`configs/sites/su_rates.json` 的 `nano4.twd_per_su` ＝ nstc 0.1／academic 0.2／industry 0.37 元每 SU；`ngs*` 分區 factor 1、`big-mem*` factor 7。所以約 3.3 SU × 0.1 ＝ 約 NT$0.33（nstc）。
- 已知小落差（不在本任務範圍，列在待裁決）：`docs/TESTING.md` TC-047n 第 4 點把第三個新檢查叫 `image_library`，空白表叫 `library`。

## 不做
- 不改空白表、不改 `docs/TESTING.md`／`docs/SETTINGS.md`／`scripts/`／`platform/`／`deploy/`／`tests/`。
- 不補任何沒記錄的值（wallet、preflight 逐項、head.sh、squeue 全文、trace 行數、截圖、token grep、fallback）。
- 不推測走哪條路、不推測確認頁 `<rid>` 與平台 run id 是否同一個。
- 不寫站台帳號或叢集路徑。
- 不為這份存檔另外新增測試或腳本。

## 待 developer-agent 裁決
1. 存檔位置：依空白表檔頭規則放 `specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md`（建議）；若你要改放 `specs/acceptance-nano4-record/` 底下，範圍要同步改。
2. 檔頭規則寫「空格留空」，本計畫改成「寫未記錄」。要不要同步改空白表檔頭那句？（動空白表、會碰到 `tests/docs_nano4_acceptance.sh` 的自測，所以本任務不做，另開一件。）
3. `image_library`（TESTING.md）與 `library`（空白表）名字不一致，要不要另開一件對齊。
4. 平台 run id `ae0d52e5e5fe5a98` 填進 `<rid>` 位置是否合適（確認頁網址的 `<rid>` 可能是另一個值）。本計畫的處理：註明「平台 run id」並把兩者是否相同寫成「未記錄」。

## 裁決
（待 developer-agent 填；寫在「專長守則」之前，`build-dev-plans.py` 會重寫其後整段。）

## 裁決二（2026-10-24 developer-agent）
1. 存成 `specs/007b-launch/acceptance-nano4-2026-10-24-maintainer.md`（照空白表的規定複製），空白表不動。
2. 用「未記錄」；空白表表頭不改。
3. preflight 名稱不一致只記進 ledger，另案。
4. run id 欄寫「平台 run id ae0d52e5e5fe5a98」，與確認頁 `/c/<rid>` 是否相同寫「未記錄」。

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
