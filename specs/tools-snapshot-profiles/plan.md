---
id: tools-snapshot-profiles
title: PR #362（launch 可選 Config profiles）合併後 origin/v3 上 MCP 工具合約測試四支紅，補快照、OVER_LIMIT 與 launch.pipeline 說明
tier: C
kinds: backend
risk: M
lane: L50-tools-snapshot-profiles
branch: fix/tools-snapshot-profiles
dir: specs/tools-snapshot-profiles
base: v3
source: developer-agent 11-05：head-nodefail-detect 的 ledger（specs/head-nodefail-detect/ledger.md 第 27 行）記錄 origin/v3 本身 test_mcp_contract_tools.py 有 4 支紅，與該分支無關；根源是 PR #362（feat(mcp): launch 可選 Config profiles, test 免樣本表）
---

# tools-snapshot-profiles

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/tools-snapshot-profiles/plan.md`。**只處理本任務**。risk M：範圍含 `platform/abf_platform/mcp_server.py`，不含 `.github`、憲法、`platform/abf_station/`。

## 目標
讓 `platform/tests/mcp/test_mcp_contract_tools.py` 在乾淨的 origin/v3 上全綠，**不放寬任何測試**：快照補上 launch 新增的 `profiles` 參數與 `params` 說明；launch 描述已降到 599 字，依測試自己的規則從 `OVER_LIMIT` 刪掉；`launch.pipeline` 補一句白話參數說明。對使用者的意義：合約測試重新能擋下「工具介面被不小心改掉」，而不是在 v3 上長期紅、讓每個分支都背四支假紅。

## 維護者原話（verifier 出題用）
1. 「make these four green without weakening them」（developer-agent 對本任務的指示，11-05）→ 四支測試各自轉綠，且測試檔只准做規則允許的刪減（見「作法」），不得改 `LIMIT`、不得改斷言、不得新增豁免。
2. 「regenerate/repair the snapshot following the file's own regeneration rule」→ 快照用測試檔 `REGEN_CMD` 產生，不手改 JSON。
3. 「remove launch from OVER_LIMIT」→ `OVER_LIMIT` 只刪 `launch` 一行，`get_run`、`run_outputs` 的數字不動。
4. 「add the missing parameter descriptions in the tool definition in platform/abf_platform/mcp_server.py (descriptions in plain English, saying what the param does and when to use it)」→ 說明寫在參數的 `Field(description=...)`，用白話英文，說這個參數做什麼、什麼時候用。
5. 「No other behavior change. Do not touch .github or the constitution.」→ 不改工具名、參數名、型別、預設值、必填、工具描述（description）本文。
6. 「First verify on origin/v3 which of these truly fail」→ 開工第一步先在乾淨的 origin/v3 上跑這個檔，貼證據（見「失敗先行測試」）。

## 範圍：檔案
- `platform/abf_platform/mcp_server.py`：只在 `launch_tool`（約 188～200 行，`_add_write_tools` 內）把 `pipeline: str` 改成 `Annotated[str, Field(description="...")]`。**不動** `@server.tool(... description=...)` 那段文字（一個字都不加：它現在 599 字，加一個字就破 600，且 `test_launch_profiles.py::test_tc058` 逐字釘住）。
- `platform/tests/mcp/snapshots/tools.json`：用 `REGEN_CMD` 重新產生（LF 行尾）。
- `platform/tests/mcp/test_mcp_contract_tools.py`：只刪 `OVER_LIMIT` 裡 `"launch": 968,` 那一行。**不碰其他任何一行**；`UNDESCRIBED_PARAMS` 不用動（`('launch','pipeline')` 本來就不在清單裡，它是新紅，不是舊債）。
- `specs/tools-snapshot-profiles/`（ledger.md、decisions.tsv 等 supervise 產物）。
- 不改：`.github/`、`.specify/memory/constitution.md`、`platform/abf_station/`、`docs/`（沒有文件列出這些常數，見環境事實）。

## 作法
1. **先驗證（不寫碼）**：在乾淨的 origin/v3 worktree 跑 `cd platform && python -m pytest tests/mcp/test_mcp_contract_tools.py -q`（整個檔，WSL 快速指令見倉庫 CLAUDE.md「For the executor and verifier」；單檔 `pytest` 不需要 `run_all.sh`）。預期紅四支：`test_tools_schema_matches_snapshot`、`test_snapshot_is_crlf_insensitive`、`test_over_limit_list_only_shrinks`、`test_every_param_is_described`。**本計畫寫作時沒有執行測試**（planner 不跑測試）；以讀碼推論這四支，executor 必須先實跑確認，若實際紅的集合與此不同，把差異寫進 ledger 並停下來問 developer-agent，不要自行擴大範圍。
2. **launch.pipeline 說明（產品碼）**：`pipeline: Annotated[str, Field(description="...")]`，白話英文，建議文字（可微調，但要含這三件事：是什麼、怎麼寫、何時用）：
   `"The pipeline to run: an nf-core name such as nf-core/rnaseq, or a pipeline the site already has. Use it with revision, which says which release or branch to run."`
   限制：不得含 `approve|confirm|confirmed_by|void|yes`（不分大小寫，`test_launch_profiles.py` 第 16 行 `BANNED_WORDS`，會掃 launch 的描述與 `profiles` 說明；為保險 pipeline 說明也避開）；`test_tc055` 禁止參數名含 confirm／approve／yes／send／force／skip／accept 等，本案不新增參數名。`launch` 的 `required` 仍為 `["pipeline","revision","run_name"]`。
   其餘沒說明的 launch 參數（`revision`、`run_name`、`ce_name`、`path_columns`）屬於 `UNDESCRIBED_PARAMS` 的既有凍結舊債，本片**不補**（補了就得同步刪清單項，且會擴大快照差異；列為後續，見「不做」）。
3. **OVER_LIMIT**：刪 `"launch": 968,` 一行。`test_over_limit_list_only_shrinks` 規則是「清單內的工具必須仍 > 600」，launch 現在 599，所以必須刪；`test_descriptions_within_limit` 對不在清單的工具要求 ≤ 600（`LIMIT = 600`），599 通過。
4. **快照**：產品碼改完後才重新產生（順序不可顛倒，否則 pipeline 說明不在快照裡）：`cd platform && ABF_UPDATE_MCP_SNAPSHOT=1 python -m pytest tests/mcp/test_mcp_contract_tools.py::test_tools_schema_matches_snapshot`，再不帶環境變數整檔重跑確認。快照由 `compare_snapshot` 以 LF、UTF-8、`sort_keys=True, indent=2, ensure_ascii=False` 寫出，不要用編輯器另存。
5. **自查快照差異**：`git diff -- platform/tests/mcp/snapshots/tools.json` 只應出現：launch 的 `params.description`、新增整個 `profiles` 物件（含 description）、`pipeline.description`。其他工具若出現差異（例如 `get_run` 因別條分支改過），代表基準有別的漂移，停下來列在 ledger，不要一併吞進快照。
6. **不要把 `ASPECT_GAPS`／`UNDESCRIBED_PARAMS` 當作這支任務的出口**：若 `test_descriptions_cover_the_six_aspects` 或 `test_every_param_is_described` 出現與 launch 無關的紅，那是另一個問題，回報、不改。

## 失敗先行測試
本任務沒有新測試檔：目標就是讓既有四支轉綠，它們就是失敗先行測試（改前紅、改後綠）。executor 的紅綠證據貼進 ledger：
- 改前（乾淨 origin/v3）：整檔輸出，紅的應是這四支：
  - `test_tools_schema_matches_snapshot`：差異含 launch 的 `profiles`、`params.description`。
  - `test_snapshot_is_crlf_insensitive`：同一份快照與現況不符（它拿快照檔轉 CRLF 後比對 `render_snapshot`）。
  - `test_over_limit_list_only_shrinks`：訊息 `launch is now 599 chars: delete it from OVER_LIMIT`。
  - `test_every_param_is_described`：`[('launch', 'pipeline')]`。
- 改前再證一次「沒削弱」：`git diff origin/v3 -- platform/tests/mcp/test_mcp_contract_tools.py` 只有刪一行。
- 改後：同一個檔全綠（其中 `test_tools_schema_matches_snapshot` 在**不帶** `ABF_UPDATE_MCP_SNAPSHOT` 時綠）。
- 刻意破壞各一次（記進 ledger，然後還原）：①把 pipeline 說明暫時拿掉 → `test_every_param_is_described` 紅；②把 `"launch": 968,` 暫時加回 → `test_over_limit_list_only_shrinks` 紅；③快照改一個字元 → `test_tools_schema_matches_snapshot` 紅。

## 允許的斷言（既有測試）
下列既有測試釘住本案會碰的常數或句子，**只准新增、不刪不放寬**；行號為 origin/v3 的（開工前用 `git -C <repo> grep -n "<字串>" origin/v3 -- platform/tests` 再對一次）：
- `platform/tests/mcp/test_mcp_contract_tools.py`：`LIMIT = 600`（約 121 行）、`OVER_LIMIT`（約 124～128 行，只刪 launch）、`test_over_limit_list_only_shrinks`（約 213～219）、`test_descriptions_within_limit`（約 203～210）、`test_every_param_is_described`（約 237～252）、`test_snapshot_has_only_name_and_input_schema`（約 111～115，快照只准有 `name`、`inputSchema` 兩個頂層鍵，且工具名單等於 `EXPECTED_TOOLS`）、`test_snapshot_missing_or_different_fails_without_overwrite`（約 79～100，REGEN 行為）。
- `platform/tests/test_launch_profiles.py`：第 16 行 `BANNED_WORDS`；`test_tc055`（約 409～417，launch 的 `required == ["pipeline","revision","run_name"]`、無「能代答」的參數名）；`test_tc017_tc056_tc057`（約 420～429，`profiles` 為選填字串陣列、說明含 `["test"]`、`params` 有 description）；`test_tc058`（約 432～438，launch 描述 ≤ 600 且含 `does NOT start`、`resume or relaunch`、`same arguments`、`profiles`、`Or name a dataset of yours (dataset, optionally dataset_version): its samplesheet is used.`）；約 677 行（`profiles` 在 launch 的 properties）。
- `platform/tests/test_dataset_launch.py`：約 207～212（launch 屬性集、`required`、描述含 dataset 那一句）。
- `platform/tests/test_head_nodefail.py`：約 795 行（`get_run` 的描述，TC-046／047；本案不動 get_run）。
- `platform/tests/test_actions_layer.py`：約 36 行 `BASELINE`（讀取工具的描述與 schema 逐字基準，不含 launch；本案不動讀取工具）與約 225 行（排除清單）。
- `platform/tests/test_mcp_launch_pipeline.py`：約 115 行（`launch_pipeline` 的 schema；本案不動）。
- 還有「工具個數／名單」類的測試（`test_launch_profiles.py::test_tc059` 約 441 行起列出全部工具名）——本案不增不減工具，維持綠。
- 其他描述釘住者：`git grep -n "description" origin/v3 -- platform/tests` 已掃過，上面是全部與 launch／MCP 工具描述有關的；若 executor 改完後跑 `platform/tests/` 整套有任何其他測試因為 launch 的 inputSchema 多一個 `description` 而紅，把測試名貼回報告，不要自行改它。

## 完成標準（done when）
- `platform/tests/mcp/test_mcp_contract_tools.py` 全綠（含四支原本紅的）；`platform/tests/test_launch_profiles.py`、`test_dataset_launch.py`、`test_mcp_launch_pipeline.py`、`test_actions_layer.py`、`test_head_nodefail.py` 綠或與 origin/v3 的紅綠一致；`tests/run_all.sh` 於 WSL 全綠（環境紅依 README 通例）。
- `git diff --stat origin/v3...HEAD` 只有：`mcp_server.py`（一處 `pipeline` 註解式改動）、`tools.json`、`test_mcp_contract_tools.py`（-1 行）、`specs/tools-snapshot-profiles/`。
- `git diff origin/v3...HEAD -- platform/abf_platform/mcp_server.py` 只動 `pipeline: str` → `Annotated[str, Field(...)]` 一處；launch 的 `@server.tool` 描述字串零差異（`len == 599` 不變）。
- 快照差異只含「作法 5」列的三處。
- 閱卷附證據（貼進 ledger）：改前四紅的輸出、改後全綠輸出、`git diff --stat`、三個刻意破壞的紅。

## 環境事實
- 快照、REGEN 規則、LIMIT 等都在測試檔頭部（`REGEN_CMD`、`compare_snapshot`、`render_snapshot`）；`docs/TESTING.md` 與 `CLAUDE.md` 沒有提到 `tools.json` 或 `ABF_UPDATE_MCP_SNAPSHOT`（已 grep），所以不需要改文件。
- 快照現況：origin/v3 的 `platform/tests/mcp/snapshots/tools.json` 最後由 `5c2e9955`（Merge origin/v3 into feat/launch-pipeline-mcp）更動；PR #362 沒更新它。launch 的 inputSchema 在快照約 200～273 行。
- launch 在 `platform/abf_platform/mcp_server.py` 約 179～205 行：描述 599 字；`params` 與 `profiles` 已有 `Field(description=...)`，`pipeline`、`revision`、`run_name`、`ce_name`、`path_columns` 沒有。
- 為什麼 `test_every_param_is_described` 現在只多出 `pipeline`：該測試認「schema 有說明」或「工具描述裡出現參數名（整詞）」。launch 描述縮短後不再出現整詞 `pipeline`，所以 `pipeline` 變成新紅；`revision`、`run_name`、`ce_name`、`path_columns` 本來就在凍結清單。
- 測試跑法：WSL 快速指令在倉庫 `CLAUDE.md`「Full suite」那一條（`cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree> && ...'`，從 ASCII 目錄呼叫 wsl）；單檔 pytest 在該指令裡把 `bash tests/run_all.sh` 換成 `cd platform && python -m pytest tests/mcp/test_mcp_contract_tools.py -q`。worktree 必須在本機磁碟，不可在同步碟；一個 checkout 同時只跑一個。
- PITFALLS 已查：`docs/PITFALLS.md`（2556 行）用 mcp／mcp_server／snapshot／tool list／schema／description 查，沒有與本任務（MCP 工具快照、描述長度、參數說明）相符的條目，**PITFALLS 已查，無相符項**。`docs/solutions/` 不存在。
- 同一個分支要避免的撞車：`mcp_server.py` 與 `tools.json` 是別條車道（例如 head-nodefail-giveup 的 get_run 描述、其他新增 launch 參數的任務）也會動的熱檔；落地前 `git merge origin/v3`，快照衝突一律**重新產生**，不要手解 JSON。

## 不做
- 不補 `revision`、`run_name`、`ce_name`、`path_columns` 的參數說明，不碰 `UNDESCRIBED_PARAMS`、`ASPECT_GAPS`：這些是 mcp-contract-tests 的凍結舊債，另案、每補一個要同步刪清單項。
- 不縮短 `get_run`（804）、`run_outputs`（700）的描述，不調整 `OVER_LIMIT` 的數字。
- 不改 launch 的工具描述文字、工具名、參數名、型別、預設、必填；不改行為。
- 不改 `.github/`、憲法、`platform/abf_station/`、`docs/`。
- 不把快照比對接進 CI（原 mcp-contract-tests 計畫列為後續切片）。
- 這次紅的根因（PR #362 合併時沒跑 `tests/mcp/`）是流程問題，不在本片處理；可在 PR 說明提一句，由維護者決定要不要加 CI 步驟。

## 裁決
1. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`；單檔先跑（見環境事實）。
2. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有慣例自訂預期值，不以「計畫未寫」退回；test-case.md 全文放進回傳值。
3. `pipeline` 說明的實際英文可由 executor 微調，但必須：白話、說明做什麼與何時用、不含 `BANNED_WORDS`、單句不超過約 200 字元。不要為了湊字數去動工具描述。
4. 若改前實跑發現四支紅的集合與計畫不同（多或少），先把輸出貼進 ledger 並回報 developer-agent，不要自行決定範圍。

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

## 裁決（2026-11-06 凌晨，developer-agent）
TC-U28 已由維護者核可刪除並合併（PR #369，他 11-05 回「刪」）。前一輪卡在 TC-U28 的紅燈解除。開工第一步：`git fetch origin && git merge origin/v3`（衝突時兩邊意圖都保留，工具數／唯讀數斷言照合併後總數重算，絕不弱化）；然後跑全套直到乾淨全綠，才寫 GREEN。逾時的 shard 只重跑逾時那片一次。不需要改任何測試來迴避 TC-U28（它已不存在）。
