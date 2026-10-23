---
id: http-launch-site-samplesheet
title: HTTP launch 可用環境 readRoots 內的站台檔；MCP launch 加 samplesheet_text
tier: C
kinds: backend
lane: L2-http-launch
base: v3
---

# http-launch-site-samplesheet

> 本檔由 developer-agent（筆電 side session）寫，2026-10-23。**只處理本任務**。PR #166（feat/failure-seqera）也改 `actions/__init__.py`（list_runs／get_run，約 23–110 行）與 `docs/PLATFORM.md`（約 472 行），本任務的段落不重疊；base 用 v3，不疊在 #166 上。

## 目標
使用者從 Claude（HTTP MCP）就能對遠端站台（nano4）送出一個 samplesheet 路徑欄指向站台檔案的 run，不必先把 fastq 上傳到平台機器的 `<uploads_root>/<user>/`。今天這在遠端站台完全做不到：samplesheet 檔在平台機器上讀、路徑格必須在平台機器的上傳資料夾，而 pipeline 在站台上讀檔。

## 維護者原話（verifier 出題用）
- 「同意放寬：HTTP 送出的 samplesheet 路徑可以指向環境 readRoots 內的站台檔案，但落在 uploads 資料夾內的仍只能是自己的；並加 samplesheet_text 參數。照計畫做。」（2026-10-23，經謝馬爾 session 轉述）
- 例子（本次真實使用情境）：nano4 上 `/work/u9613010/abf/projects/microbiome_test/rawdata/Day5_*.fastq.gz` 共 10 個 PacBio fastq，nf-core/ampliseq 2.18.0，`path_columns=["forwardReads"]`，samplesheet 欄位 `sampleID,forwardReads`。lab-agent 用 claude.ai 的 HTTP MCP 送了兩次都被拒：「cannot read the samplesheet as a plain file in your own uploads folder」。

## 範圍：檔案
- `platform/abf_launch/build.py`（`_confine` 的路徑格迴圈；`prepare_launch` 文件字串）
- `platform/abf_platform/actions/__init__.py`（`request_launch`：接 `samplesheet_text`；只動約 400–446 行與 request_launch）
- `platform/abf_platform/mcp_server.py`（`launch` 工具：新增選填參數與說明文字）
- `platform/tests/test_owner_binding.py`、`platform/tests/test_owner_gaps.py`（TC-049 等釘住舊行為的案例改寫；ledger 記舊/新/理由）
- `platform/tests/test_http_site_samplesheet.py`（新）
- 若 parity／guidance 測試要求 MCP 工具與其他入口（網頁 012b、chat tools、guidance 說明）參數一致而變紅：只做讓它們一致所需的最小改動，檔案列進 ledger
- `docs/PLATFORM.md`（約 414、445、451 行三處）
- `specs/http-launch-site-samplesheet/`（plan、test-case、ledger）

## 作法
1. **路徑格規則（HTTP、caller 不是 None）＝ 116b params 的同一條規則**：
   - 一格路徑若落在 `uploads_root` 內（真實路徑 realpath，或字面寫法 `rules.normalize(abspath)`／uploads 的真實路徑，與 params 判法相同）→ 必須在呼叫者自己的資料夾 `area` 內，否則 `area_refusal(area)`（字句不變，不透露別人的資料夾）；通過者照舊記進 `upload_paths`（代理在站台複查，不變）。
   - 其他格 → 必須在環境 readRoots 內。這條現在已由 `inputs_from_environment`／`render_bundle` 檢查（終端機也走這條）；`_confine` 不再對它們多擋。executor 要用測試確認 readRoots 檢查對 HTTP 呼叫者確實生效（readRoots 外的格仍被拒）。
   - 不在 readRoots 內、也不在 uploads 內 → 拒絕（現有字句）。
   - 終端機與 stdio（caller=None）完全不變。
2. **`samplesheet_text`**：MCP `launch` 新增選填 `samplesheet_text: str | None`（CSV 全文）。
   - 與 `samplesheet`（路徑）**恰好給一個**：兩個都給或都沒給 → 拒絕，字句說「samplesheet 與 samplesheet_text 只能給一個」。`samplesheet` 在工具簽章改成選填（預設 None）。
   - 上限 1 MiB（UTF-8 位元組計），超過拒絕；含 NUL 拒絕。
   - 解析用同一個 `parse_samplesheet`（以 `samplesheet_raw=text.encode("utf-8")` 傳入 `prepare_launch`），之後路徑格規則與檔案來源無關，一律照第 1 點。
   - 平台機器上不寫任何檔；bundle 與確認畫面跟用路徑送出時一樣（rows 已在 bundle 裡，被核准的 hash 蓋到）。同樣的 text＋參數重送 → 找到同一個已核准的確認（不重複排隊）。
   - stdio 也接受 `samplesheet_text`（stdio 沒有表單仍照舊拒絕，這條不變）。
3. `resume`／`relaunch` 沿用第一次的 rows（`samplesheet_rows`），行為不變；加一條測試：用 `samplesheet_text` 送出、格子在 readRoots 的 run，HTTP resume 不因新規則被拒。
4. `docs/PLATFORM.md`：414 行（samplesheet 只能在上傳資料夾 → 或用 `samplesheet_text` 給內容）、445 行（路徑格規則改寫成第 1 點）、451 行（params 規則與路徑格同一條），並寫一句為什麼（遠端站台沒有每人上傳資料夾；隔離由環境擁有者守）。

## 失敗先行測試
新檔 `platform/tests/test_http_site_samplesheet.py`，沿用 `owner_harness`：
- HTTP 使用者 A，環境 readRoots 含 `/data/shared`（tmp 目錄），`samplesheet_text` 的格子指向 readRoots 內檔 → 通過到確認（pending），不被拒。現在紅（參數不存在）。
- 同上但用 `samplesheet` 路徑（在 A 的上傳資料夾內），格子在 readRoots → 通過。現在紅（TC-049 行為）。
- readRoots 包住 `uploads_root`；A 的格子用 readRoots 寫法指到 `<uploads_root>/B/y.fq` → 拒絕，字句只提 A 的資料夾。
- 格子不在 readRoots、也不在 uploads → 拒絕。
- 兩個都給／都沒給 → 拒絕；超過 1 MiB、含 NUL → 拒絕。
- 同樣 `samplesheet_text` 兩次 → 第二次回同一個確認，不排第二個工作。
- 終端機／stdio 現有行為的測試不改就綠。
- 改寫 `test_owner_binding.py` 的 TC-049 對應案例（舊：拒絕 → 新：通過），ledger 寫舊預期、新預期、理由（維護者 10-23 裁示）。

## 完成標準（done when）
- 上面測試全綠；`tests/run_all.sh`（WSL）與 platform 的 pytest 全綠在 HEAD。
- `docs/PLATFORM.md` 三處同步，且有 `samplesheet_text` 的名字。
- ledger 列出每個改寫的舊釘子。
- PR 標題標「[C 級，維護者已同意放寬，等他 merge]」。

## 環境事實
- 平台在另一台主機；samplesheet 現在在平台主機上讀（`read_confined_samplesheet`）。遠端站台的檔案平台主機上沒有，`os.path.realpath` 對不存在的路徑只做字面解析。
- 隔離：116 D4 環境與代理都有擁有者，建 bundle 時與排隊時各查一次；B 用不了 A 的環境。
- 116 TC-057：HTTP 下 `list_site_files` 已可列 readRoots 內的檔；116b：params 路徑已可指向 readRoots。

## 不做
- 上傳工具（ROADMAP 012）、代理去站台讀 samplesheet、遠端站台每人資料夾（009h）、角色與共享（010）。
- 不改誰可以按「送出」；不改終端機與 stdio 的規則；不改代理端 `upload_paths` 複查。

## 裁決
（developer-agent，2026-10-23，回應 verifier CONTRACT 審查的六點）
1. **範圍加兩個檔**：`platform/tests/test_station_launch.py`（TC-LS-52 改寫成 TC-036 的參數集合與必填，ledger 記舊/新/理由）；`platform/tests/owner_harness.py`（只准讓 `Duo.launch` 可以不帶 `samplesheet`、改帶 `samplesheet_text`，屬測試輔助的設定改動，不改任何既有斷言）。`actions.confined_samplesheet`、`read_confined_samplesheet` 的名字與用途不動（`test_review_fixes_2.py:212` 與 `test_web_parity.py` 的 INTERNAL 依賴它們）。
2. **不需要 migration**：沒有任何資料表或欄位改動；bundle 形狀不變，只是路徑格的檢查規則變（TC-057）。
3. **路徑格剛好等於自己的資料夾本身（目錄、沒有檔名）→ 拒絕**，維持舊規則（`real == area` 不算在內）。路徑格要指一個檔；這是比 params 更嚴的一格，刻意保留。
4. **核可後，共享 readRoot 裡的連結被改指向別人的上傳資料夾**：本次不擋（計畫明寫不改代理端複查）；這跟今天終端機送出的 readRoots 路徑一樣。`docs/PLATFORM.md` 的「honest boundary」加一句寫明這個殘餘風險；PR 的「需要人看」列給維護者。
5. **空字串 `samplesheet_text` → 拒絕**（TC-027），說要給 CSV 內容。
6. **網頁表單（POST /launch）不加 `samplesheet_text`**：網頁仍只選自己上傳資料夾的檔；路徑格新規則在 `build._confine`，網頁同樣適用（TC-002、CS-02）。

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
