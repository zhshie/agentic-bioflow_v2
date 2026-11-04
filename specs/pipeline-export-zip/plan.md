---
id: pipeline-export-zip
title: 自訂 pipeline 匯出成可獨立執行的 zip（動作層，不含 MCP 與網頁）
tier: A
kinds: backend
lane: L45-pipeline-export
branch: feat/pipeline-export-zip
base: origin/v3@108bfdff（executor 開工前用 `git show origin/v3:<檔>` 重查行號）
source: PLAN-abf-v3-replan-2026-10.md 017b「actions：…`export_pipeline`（zip）」「done：fastqc→multiqc 圖產出可 `-stub-run` 的 zip」＋裁示 5、16
---

# pipeline-export-zip

> 只有計畫、沒有程式。A 級（只加一個動作函式與測試，不改使用者看得到的行為；沒有 MCP 工具、沒有網頁路由）→ verifier 通過＋CI 綠由 developer-agent 自合。

## 目標
017b 的動作清單裡有 `export_pipeline`（zip），v3 上沒做：`actions/pipelines.py` 只有建、改、列、取、`render_pipeline`（回字串檔案）、驗證，沒有打包。這一片補上打包函式：把某個 pipeline 的某一版，連同它用到的 nf-core 模組檔，裝成一個確定性的 zip，解開就能 `nextflow run .`。

## 維護者原話（verifier 出題用）
- 017b：「actions：`compose_pipeline`、`list_pipelines`、`get_pipeline_version`、`export_pipeline`（zip）。」
- 017b：「done：fastqc→multiqc 圖產出可 `-stub-run` 的 zip。」
- 裁示 5：v1 畫布＝「拖模組、連線、填參數、驗證、送去跑、匯出 zip、版本紀錄與分享」。
- 裁示 16：「自訂 pipeline 分享只在實驗室內＋匯出 zip，不做公開庫」。
- 裁示 9：「自訂 pipeline 的空跑驗證（`-stub-run`）不需本人按確認：它只寫到平台自己的 `pipelines/` 目錄、不花 SU」。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/actions/pipelines.py`（加 `export_pipeline`）
- `platform/tests/test_pipelines_store.py`（只改 l.308 附近「七個公開函式」那條：名單加 `export_pipeline`、標題與數字改成八個）
- 新檔 `platform/tests/test_pipeline_export.py`
- **不准碰**：`mcp_server.py`、`web.py`、`web_board.py`、`actions/__init__.py`、`chat_tools.py`、`test_web_parity.py`（本函式不是 `actions` 的公開名稱，不進 parity 四張表；同理 MCP 與網頁出口留給 017e）、`docs/PLATFORM.md`、`store.py`（不需 migration：不改資料表）。

## 作法
- **證據**（origin/v3@108bfdff）：
  - `actions/pipelines.py`：`create_pipeline` l.90、`update_pipeline` l.122、`list_pipelines` l.153、`get_pipeline` l.172、`render_pipeline` l.195（回 `files`＝main.nf／modules.json／nextflow.config 與 `open_inputs`）、`validate_pipeline` l.209、`get_validation` l.234；沒有 `export_pipeline`。
  - `git grep -n zipfile platform/abf_platform` 無結果（資料目錄以外）＝尚無打包程式。
  - 模組檔來源：`module_sources.files_for(paths, sources)`（約 l.108）回 `{"modules/nf-core/<path>/<file>": text}`；模組缺或不支援時丟 `ValueError`。
  - 整個專案文字已有現成組法：`pipeline_launch.build_project`（含 `MAX_BYTES`＝2 MiB、`MAX_FILES`＝2000 兩個上限）。
  - 擁有者規則：`_mine`（l.72）— 他人的 pipeline 當作找不到。
  - `test_pipelines_store.py:308`：「只有七個公開函式」。
- **介面**：`export_pipeline(platform_path, pipeline_id, version=None, *, caller=None, data=None, sources=None)`，回 `{"ok": True, "filename": "<name>-v<N>.zip", "zip": <bytes>, "files": [排序後的路徑], "open_inputs": [...]}`；失敗回 `_no(...)` 同樣的錯誤形狀（點名原因與怎麼辦）。
- **做法**：重用 `render_pipeline` 的檔案，再用 `module_sources.files_for` 補模組檔；兩邊合起來走 `pipeline_launch.build_project` 的同一套上限，不另寫第二份。zip 條目依路徑排序、時間戳固定（例如 1980-01-01）、壓縮方式固定，所以同一版匯出兩次位元組完全相同。
- **不寫檔案到磁碟**：回 bytes，由呼叫端（日後的 MCP／網頁）決定怎麼給使用者。這也避開「寫到平台目錄」的議題。

## 失敗先行測試
`platform/tests/test_pipeline_export.py`，先寫、改程式前跑確認紅，紅的輸出貼進 ledger。
- fastqc→multiqc 兩節點圖匯出：zip 內含 `main.nf`、`nextflow.config`、`modules.json`、兩個模組各自的 `modules/nf-core/…/main.nf`；`filename` 是 `<name>-v1.zip`。**現在紅**（函式不存在）。
- 確定性：同一版匯出兩次，bytes 相同。
- 版本：`version=None` 取最新版；指定 `version=1` 取舊版，內容是舊版的圖。
- 跨使用者：乙匯出甲的 pipeline 回「找不到」，不洩漏是否存在。
- 模組檔缺或不支援（`files_for` 丟 ValueError）：回含模組名與處理方式的錯誤，不留半個 zip。
- 超過 `MAX_BYTES`／`MAX_FILES`：回清楚的錯誤。
- 空跑對照（若 `nextflow` 在環境內）：解開 zip 後 `nextflow run . -stub-run` 通過；沒有 nextflow 時此條標 UNVERIFIED、其他條仍須全綠。
- `test_pipelines_store.py` 的公開函式名單測試更新為八個後綠，且 `hasattr(actions, "export_pipeline")` 仍為 False。

## 完成標準（done when）
- 新測試改前紅、改後綠；全套 `tests/run_all.sh` 全綠（已知環境紅見 dev-plans README「通例：已知環境紅」）。
- ledger 記：`git diff --stat` 只含範圍內三個檔；`test_pipelines_store.py` 只改名單那條；zip 內檔案清單貼進 ledger。

## 環境事實
- 專案根 `CLAUDE.md`「For the executor and verifier」。
- 單檔測試：WSL repo 根目錄 `python -m pytest platform/tests/test_pipeline_export.py`。全套寫法見 `upgrade-hint-followup.md`「環境事實」。
- 不准改：`spec.md`、`test-case*.md`、constitution、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`。

## 不做
- 不加 MCP 工具、不加網頁路由、不加下載端點（017e 才做）。
- 不做分享連結（`shared_token`）、不做公開庫（裁示 16）。
- 不在平台主機真的跑 `nextflow`（只在測試環境有 nextflow 時空跑對照）。

## 裁決
1. **回 bytes 還是寫成檔案？** 建議：回 bytes＋`filename`。理由：不碰檔案系統與路徑，日後 MCP 與網頁各自決定怎麼交付。
2. **zip 裡要不要放一份短 README 說明未填的輸入？** 建議：要，兩三行，內容取自 `open_inputs`；理由：別人解開就知道哪些欄位要自己填。
3. **匯出前要不要求驗證通過？** 建議：不要。匯出是拿走成品，不花 SU、不改資料；驗證結果若有就附在回傳的 `validation` 欄位，不擋。

### developer-agent 確認（2026-10-29 22:1x）
證據已抽查（origin/v3 無 find_module／export_pipeline；mcp_server.py 未呼叫 request_pipeline_launch）。上列裁決一律照「建議」定案。

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

### 補充裁決（2026-10-30 02:5x，PR #288 CI 紅）
- CI shard 4 的 `platform_shard_3_test.sh` 兩次都紅：`FAIL (CI=true): 1 test(s) were skipped, and nothing may be skipped on CI`——就是 TC-008 用 `shutil.which("nextflow")` 找不到就 skip。
- **改法（只改 `platform/tests/test_pipeline_export.py` 的 TC-008）**：改用 `platform/tests/conftest.py:30` 的 `e2e_cfg` fixture（包裝腳本下載的固定版 Nextflow），呼叫 `[e2e_cfg["launcher"], "run", ".", "-stub-run"]`，環境照 `platform/tests/test_launch_nextflow.py:66-68` 的寫法：去掉既有 `NXF_*`／`TOWER_*`／`ABF_*`，設 `NXF_HOME`、`NXF_VER`、`NXF_OFFLINE=true`、`NXF_ANSI_LOG=false`、`NXF_DISABLE_CHECK_LATEST=true`。拿掉 `shutil.which` 的 skip。
- 不准改 CI 設定、不准把它加進 quarantine、不准放寬斷言（仍要 returncode 0）。
- 完成標準：本機用 `bash tests/platform_shard_3_test.sh`（走包裝腳本，才有固定版 Nextflow）跑到 TC-008 PASSED 且 0 skipped，輸出貼 ledger；再跑全套。
