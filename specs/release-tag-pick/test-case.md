# 測試案例：挑選 nf-core 最新正式版本的邏輯（不連網、還沒接線）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Every row can be judged without reading code.
Language: 繁體中文; identifiers (TC-, T#, FR) and file paths stay as they are.
-->

**規格**：`specs/release-tag-pick/plan.md`（本任務沒有獨立 spec.md；計畫含「維護者原話」「失敗先行測試 T1–T22」「完成標準」與兩段裁決；裁決與正文衝突時以後面的裁決為準）　**總覽**：`test-case-overview.md`

說明：

- 「T#」是計畫「失敗先行測試」表裡的編號，方便對照。標「推自作法」的列，輸入是我（出題者）依計畫「作法」的明文規則換了一組例子，預期結果完全來自該規則，沒有新增任何計畫沒說的行為。
- 「tag」指 GitHub 上 pipeline 的版本標籤（例如 `3.0.0`）。「可用」指這個 tag 的形狀能通過平台既有的 `REVISION` 檢查（數字版本，可帶開頭 `v`），可以原樣送去啟動。
- 測試用的時鐘固定為 `1760000000.0`（秒）；快取檔、假的「抓 tag 函式」`fetch` 都在 `tmp_path`（暫存資料夾）裡，不連網、不呼叫 `git`、不啟動任何程式。24 小時 = 86400 秒。
- 預設快取起點：快取檔內容為 `{"nf-core/ampliseq": {"revision": "3.0.0", "checked_at": 1760000000.0}}`，只有標明「快取為空」「快取有 2.18.0」等的列才不同。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、輸入不合格時，系統怎麼反應（拒絕、回舊值、回「沒有」，而且不丟例外）。
- **不在範圍**：計畫明講這次不做的事；檢查它真的沒做。

維護者原話對照：

- 「新專案預設最新版並釘住」→ 回傳的是具體版本號，不是 `latest` 或分支名：TC-016、TC-017、TC-025。
- 「專案記住版本、不自動升、新版只提示」→ 回傳只報告、不含任何「覆蓋專案版本」的欄位；模組不碰專案資料：TC-035、TC-037、TC-059。
- 「Pin an exact pipeline revision, never a branch」→ 分支名與預發行版一律不當最新：TC-010、TC-011、TC-012。

## User Story 1 — 認出 pipeline 名稱、判斷 tag 能不能用、挑出最新版（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | T1；作法 1 | 功能 | 無 | 把 `ampliseq`（沒寫擁有者）交給 `repo_of` | 得到 `nf-core/ampliseq` | 自動：`test_releases.py` T1 |
| TC-002 | T1；作法 1 | 功能 | 無 | 把 `nf-core/ampliseq` 交給 `repo_of` | 原樣得到 `nf-core/ampliseq` | 自動：T1 |
| TC-003 | T1；作法 1 | 功能 | 無 | 把 `lab/own-flow` 交給 `repo_of` | 原樣得到 `lab/own-flow` | 自動：T1 |
| TC-004 | T2；作法 1 | 例外 | 無 | 把空字串 `""` 交給 `repo_of` | 丟 `ValueError`，訊息同時含中文與英文 | 自動：T2 |
| TC-005 | T2；作法 1 | 例外 | 無 | 把 `../x` 交給 `repo_of` | 丟 `ValueError`，訊息同時含中文與英文（不能因為 `..` 湊得出合法字元就放行） | 自動：T2 |
| TC-006 | T2；作法 1 | 例外 | 無 | 把 `a/b/c`（三段）交給 `repo_of` | 丟 `ValueError`，訊息同時含中文與英文 | 自動：T2 |
| TC-007 | T2；作法 1 | 例外 | 無 | 把 `nf core/x`（帶空白）交給 `repo_of` | 丟 `ValueError`，訊息同時含中文與英文 | 自動：T2 |
| TC-008 | T2；作法 1 | 例外 | 無 | 把 `None` 交給 `repo_of` | 丟 `ValueError`（不是 `TypeError`、不是別種錯），訊息同時含中文與英文 | 自動：T2 |
| TC-009 | T3；作法 2 | 功能 | 無 | 把 `3.0.0`、`v2.1`、`1.2.3.4`、`1.0` 各交給 `usable` | 四個都回 True | 自動：T3 |
| TC-010 | T4；作法 2；原話「never a branch」 | 例外 | 無 | 把 `3.0.0dev`、`3.0.0-rc1`（預發行版）各交給 `usable` | 兩個都回 False | 自動：T4 |
| TC-011 | T4；作法 2；原話「never a branch」 | 例外 | 無 | 把 `dev`、`master`（分支名）各交給 `usable` | 兩個都回 False | 自動：T4 |
| TC-012 | T4；作法 2 | 例外 | 無 | 把一個 40 位十六進位 sha（`0123456789abcdef0123456789abcdef01234567`）交給 `usable` | 回 False（sha 能啟動，但不是「最新版本號」） | 自動：T4 |
| TC-013 | T4；作法 2 | 例外 | 無 | 把 `"3.0.0\n"`（尾巴多一個換行）交給 `usable` | 回 False | 自動：T4 |
| TC-014 | T4；作法 2 | 例外 | 無 | 把空字串 `""` 交給 `usable` | 回 False | 自動：T4 |
| TC-015 | T5；作法 3 | 功能 | 無 | `pick_latest(["3.9.0","3.10.0","3.2.1"])` | 回 `"3.10.0"`（不是按字串排序會得到的 `3.9.0`） | 自動：T5 |
| TC-016 | T6；作法 3；原話「預設最新版並釘住」 | 功能 | 無 | `pick_latest(["2.18.0","3.0.0","3.0.0dev","dev"])` | 回 `"3.0.0"`（預發行版與分支名被排除；回的是具體版本號） | 自動：T6 |
| TC-017 | T7；作法 3 | 功能 | 無 | `pick_latest(["v3.0.0","3.0.0"])` | 回 `"3.0.0"`（同一版本，取不帶 `v` 的） | 自動：T7 |
| TC-018 | 推自作法 3（同一版本取不帶 `v` 的，與順序無關） | 功能 | 無 | `pick_latest(["3.0.0","v3.0.0"])`（順序顛倒） | 回 `"3.0.0"` | 自動：test_releases.py（新） |
| TC-019 | T7；作法 3（`3.0 < 3.0.1`） | 功能 | 無 | `pick_latest(["3.0","3.0.1"])` | 回 `"3.0.1"` | 自動：T7 |
| TC-020 | 推自作法 3（「`v` 只在比較時忽略」「回傳原字串」） | 功能 | 無 | `pick_latest(["v2.1","1.0"])` | 回 `"v2.1"`（原字串，開頭的 `v` 保留） | 自動：test_releases.py（新） |
| TC-021 | T8；作法 3 | 例外 | 無 | `pick_latest([])` | 回 `None`，不丟例外 | 自動：T8 |
| TC-022 | T8；作法 3 | 例外 | 無 | `pick_latest(["dev","master"])` | 回 `None`，不丟例外 | 自動：T8 |
| TC-023 | T8；作法 3 | 例外 | 無 | `pick_latest([None, 3, "2.0.0"])` | 回 `"2.0.0"`（非字串元素略過，不丟例外） | 自動：T8 |
| TC-024 | T9；作法 4 | 功能 | 一段 `git ls-remote --tags --refs` 的輸出：兩行正常（`<sha>` 定位符 tab `refs/tags/2.18.0`、`<sha>` tab `refs/tags/3.0.0`）、一行沒有 tab 的壞行、一行只有空白 | 交給 `parse_ls_remote` | 剛好回 `["2.18.0","3.0.0"]`：只有兩個 tag 名稱，壞行與空白行被略過，順序與輸入相同 | 自動：T9 |

## User Story 2 — 一鍵查「現在可預填的最新版」：24 小時快取、來源失敗不丟例外（優先度 P1）

維護者原話：「launch 表單與 MCP 預填＝該 pipeline 最新 release tag；專案記住版本、不自動升、新版只提示」「新專案預設最新版並釘住」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | T10；作法 5；原話「預設最新版並釘住」 | 功能 | 快取檔不存在；`fetch` 回 `["2.18.0","3.0.0"]` | `lookup("nf-core/ampliseq", fetch, cache_path=…)` | `revision` 是 `"3.0.0"`（具體版本號，不是 `latest`），`source` 是 `"fetched"`，`pipeline` 是 `"nf-core/ampliseq"` | 自動：T10 |
| TC-026 | T10 | 功能 | 同 TC-025 | 同上 | `checked_at` 等於這次呼叫時時鐘讀到的值（`1760000000.0`） | 自動：T10 |
| TC-027 | T10 | 功能 | 同 TC-025 | 同上 | `fetch` 剛好被呼叫一次 | 自動：T10 |
| TC-028 | T10；作法 5（快取檔格式） | 功能 | 同 TC-025 | 同上之後讀快取檔 | 檔案存在、是合法 JSON，其中 `nf-core/ampliseq` 一筆為 `revision "3.0.0"`、`checked_at` 為 `1760000000.0` | 自動：T10 |
| TC-029 | T11；作法 5 | 功能 | 已照 TC-025 查過一次；時鐘走了 3600 秒 | 再呼叫一次 `lookup` | `source` 是 `"cache"`，`revision` 仍是 `"3.0.0"` | 自動：T11 |
| TC-030 | T11；作法 5 | 功能 | 同 TC-029 | 同上 | `fetch` 沒有被再呼叫（總共仍只有第一次那一次） | 自動：T11 |
| TC-031 | 推自作法 5（`now - checked_at < ttl` 才新鮮） | 功能 | 同 TC-029，但時鐘走了 86399 秒（差一秒到期） | 再呼叫一次 | `source` 是 `"cache"`，`fetch` 沒有被再呼叫 | 自動：test_releases.py（新） |
| TC-032 | 推自作法 5（`checked_at <= now` 才新鮮；等於算新鮮） | 功能 | 快取的 `checked_at` 剛好等於現在的時鐘 | 呼叫 `lookup` | `source` 是 `"cache"`，`fetch` 沒有被呼叫 | 自動：test_releases.py（新） |
| TC-033 | T12；作法 5（邊界＝過期） | 功能 | 同 TC-029，但時鐘走了剛好 86400 秒 | 再呼叫一次 | 重新呼叫 `fetch`（總共兩次），`source` 是 `"fetched"` | 自動：T12 |
| TC-034 | T13；作法 5（檢查時間在未來＝過期） | 例外 | 快取的 `checked_at` 比現在的時鐘晚（在未來） | 呼叫 `lookup` | 不信快取，重新呼叫 `fetch`，`source` 是 `"fetched"` | 自動：T13 |
| TC-035 | T14；原話「新版只提示」 | 功能 | 快取有 `2.18.0` 且已過期；`fetch` 現在回 `["2.18.0","3.0.0"]` | 呼叫 `lookup` | 回 `revision "3.0.0"`、`source "fetched"` | 自動：T14 |
| TC-036 | T14 | 功能 | 同 TC-035 | 同上之後讀快取檔 | 快取檔裡該 pipeline 已更新為 `3.0.0` | 自動：T14 |
| TC-037 | T14；原話「專案記住版本、不自動升」 | 功能 | 同 TC-035 | 看回傳 dict 有哪些鍵 | 鍵剛好是 `pipeline`、`revision`、`source`、`checked_at`、`why` 五個，沒有任何「覆蓋專案版本」「升級」之類的欄位 | 自動：T14 |
| TC-038 | T15；作法 5 | 例外 | 快取有 `2.18.0` 且已過期；`fetch` 丟 `OSError("network down")` | 呼叫 `lookup` | 不丟例外；`source` 是 `"stale-cache"`，`revision` 是舊值 `"2.18.0"` | 自動：T15 |
| TC-039 | T15；作法 5（`why` 說原因） | 例外 | 同 TC-038 | 同上，看 `why` | `why` 不是空的，且含失敗原因（`network down`） | 自動：T15 |
| TC-040 | T15 | 例外 | 同 TC-038 | 同上之後讀快取檔 | 快取檔內容與呼叫前逐字相同（失敗不改寫快取） | 自動：T15 |
| TC-041 | T16；作法 5 | 例外 | 沒有快取；`fetch` 丟例外 | 呼叫 `lookup` | 不丟例外；`revision` 是 `None`，`source` 是 `"none"` | 自動：T16 |
| TC-042 | T16；作法 5、裁決 3（不做負面快取） | 例外 | 接 TC-041：之後 `fetch` 恢復正常（回 `["3.0.0"]`），時鐘只走了幾秒 | 再呼叫一次 `lookup` | 會再呼叫 `fetch`（失敗沒有被快取），回 `revision "3.0.0"`、`source "fetched"` | 自動：T16 |
| TC-043 | T17；作法 5 | 例外 | 沒有快取；`fetch` 回 `["dev"]`（全是不可用 tag） | 呼叫 `lookup` | `revision` 是 `None`；`why` 含「沒有可用的 release tag」 | 自動：T17 |
| TC-044 | T18；作法 5 | 例外 | 快取檔內容是 `not json`（不是 JSON）；`fetch` 回 `["3.0.0"]` | 呼叫 `lookup` | 當作沒有快取：呼叫 `fetch`、回 `"3.0.0"`；快取檔被改寫成合法 JSON | 自動：T18 |
| TC-045 | T18；作法 5 | 例外 | 快取檔內容是 `[]`（JSON 但不是物件）；`fetch` 回 `["3.0.0"]` | 呼叫 `lookup` | 同 TC-044：呼叫 `fetch`、回 `"3.0.0"`、檔案被改寫成合法 JSON | 自動：T18 |
| TC-046 | T18；作法 5 | 例外 | 快取檔內容是 `{"nf-core/x": 5}`（值型別錯）；`fetch` 回 `["3.0.0"]`；查的是 `nf-core/x` | 呼叫 `lookup` | 同 TC-044：呼叫 `fetch`、回 `"3.0.0"`、檔案被改寫成合法 JSON | 自動：T18 |
| TC-047 | T19；作法 5 | 功能 | 同一個快取檔；先後查 `nf-core/ampliseq` 與 `lab/own-flow`，兩邊 `fetch` 各回不同版本 | 兩次 `lookup` 後讀快取檔 | 同一個檔裡有兩筆，各自對應自己的版本與時間 | 自動：T19 |
| TC-048 | T19 | 功能 | 同 TC-047，且 `nf-core/ampliseq` 的快取仍新鮮 | 查 `lab/own-flow`；再查 `nf-core/ampliseq` | 兩者互不影響：`lab/own-flow` 拿到自己的版本、不是 `nf-core/ampliseq` 的；`nf-core/ampliseq` 仍是 `"cache"` | 自動：T19 |
| TC-049 | T20；作法 5（`cache_path=None`） | 功能 | `cache_path=None`；`tmp_path` 開始是空的 | 呼叫 `lookup`（`fetch` 回 `["3.0.0"]`） | 回 `revision "3.0.0"`；`tmp_path` 前後比對，沒有建立任何檔案 | 自動：T20 |
| TC-050 | T21；作法 5（先寫暫存檔再 `os.replace`） | 例外 | 快取檔已有 `2.18.0` 且已過期；`fetch` 回 `["3.0.0"]`；`os.replace` 被改成會丟錯 | 呼叫 `lookup` | 原快取檔內容與呼叫前逐字相同（不是被寫壞一半） | 自動：T21 |
| TC-051 | T21 | 例外 | 同 TC-050 | 同上之後列出快取檔所在資料夾 | 資料夾裡只有原快取檔，沒有留下 `.tmp` 或任何暫存檔 | 自動：T21 |
| TC-052 | T21；作法 5（永遠回 dict、不丟例外） | 例外 | 同 TC-050 | 同上，看回傳 | 不丟例外，回傳是 dict 且鍵是上述五個 | 自動：T21 |
| TC-053 | 推自作法 5（`fetch(repo)` 收到完整 `owner/name`；回傳 `pipeline` 為完整名稱） | 功能 | 沒有快取；`fetch` 會記下收到的引數並回 `["3.0.0"]` | `lookup("ampliseq", fetch)`（沒寫擁有者） | `fetch` 收到的是 `"nf-core/ampliseq"`；回傳的 `pipeline` 是 `"nf-core/ampliseq"` | 自動：test_releases.py（新） |
| TC-054 | 推自作法 5（永遠回 dict、不丟例外）與作法 1 | 例外 | 無 | `lookup("../x", fetch)`（名稱不合格） | 不丟例外；回傳 dict 且鍵是上述五個；`revision` 是 `None`；`fetch` 沒有被呼叫 | 自動：test_releases.py（新） |
| TC-055 | 專長守則（錯誤訊息不露堆疊）；T15 | 例外 | 同 TC-038 | 同上，看 `why` | `why` 是一句話，不含 `Traceback` 字樣 | 自動：test_releases.py（新） |

## User Story 3 — 不連網、不接線、不越界（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-056 | T22；作法開頭；計畫「不做」第 2 條（不寫真正的抓取） | 不在範圍 | `platform/abf_platform/releases.py` 原始碼 | 掃描整個檔（含註解與訊息） | 不含 `urllib`、`socket`、`subprocess`、`threading`、`requests`、字面 `station`、`ssh`、`nextflow run`，一個都沒有 | 自動：T22 |
| TC-057 | 完成標準；計畫「不做」第 1、2、3 條（不接線、不加 job kind、不動禁碰檔、不新增設定鍵）；計畫「會改斷言的既有測試：無」 | 不在範圍 | 實作完成的分支 | 驗收者執行 `git diff --name-only <base>...HEAD`（再加 `git status --porcelain` 看有無未提交） | 清單只有 `platform/abf_platform/releases.py`、`platform/tests/test_releases.py`、`specs/release-tag-pick/ledger.md` 三個；`actions/__init__.py`、`mcp_server.py`、`web_board.py`、`web.py`、`cli.py`、`store.py`、`abf_station/*`、`abf_launch/*`、`scripts/prepare_launch.sh`、`pyproject.toml`、任何既有測試檔、`spec`／`test-case*.md` 全都不在清單裡 | 手動：驗收者照本列步驟做（計畫範圍不含 `docs/TESTING.md`，故步驟寫在本列） |
| TC-058 | 計畫「不做」第 1 條（不接線：沒有任何地方呼叫新模組） | 不在範圍 | 實作完成的分支 | 驗收者在 `platform/`、`scripts/`、`skills/`、`hooks/` 搜尋 `releases` 被 import 或呼叫的地方（`rg "abf_platform.releases\|from abf_platform import.*releases\|import releases"`） | 除了 `platform/tests/test_releases.py` 之外沒有任何命中；沒有 launch 表單、MCP 工具、`launch_prefill` 用到它 | 手動：同 TC-057 |
| TC-059 | 計畫「不做」第 3 條（不自動升級專案、不新增設定鍵）；裁決 2（不替呼叫端選站台版本）；原話「專案記住版本、不自動升」 | 不在範圍 | `releases.py` 的 import 清單與全文 | 驗收者讀 `releases.py` | 只 import Python 標準函式庫（例如 `json`、`os`、`re`、`time`），不 import 任何 `abf_*` 專案模組；全文沒有讀專案資料、設定檔、`sitePipelines`、站台清單；`lookup` 沒有「站台版本」參數 | 手動：同 TC-057 |
| TC-060 | 完成標準「測試全程不開網路連線、不呼叫 `git`」 | 不在範圍 | `platform/tests/test_releases.py` | 驗收者搜尋該檔有無 `socket`、`urllib`、`requests`、`subprocess`、`os.system`、`git ` 指令呼叫 | 沒有任何一個；所有「抓 tag」都是測試自己寫的假 `fetch` | 手動：同 TC-057 |
| TC-061 | 計畫「不做」第 3 條與第 88 行（不需要 migration，沒有動資料表） | 不在範圍 | 實作完成的分支 | 驗收者看 TC-057 的檔案清單，並搜尋 diff 內有無資料表、migration、`CREATE TABLE`、`ALTER TABLE` | 沒有任何 migration 或資料表改動；快取只是呼叫端指定的獨立 JSON 檔 | 手動：同 TC-057 |
| TC-062 | 計畫「失敗先行測試」末段（executor 先跑一次貼出紅輸出） | 功能 | `specs/release-tag-pick/ledger.md` | 驗收者讀 ledger | 有一段在寫 `releases.py` 之前的紅輸出（T1–T22 因模組不存在而失敗），不是只寫「測試通過」 | 手動：同 TC-057 |

## 憲法與安全網

本任務新增兩個檔，會被既有的「平台不連網」「每個原始檔寫明替代方案」檢查掃到；這些必須仍綠。（下面「`test_scope.py` TC-070」等是那個既有檔裡的編號，與本文件編號無關。）

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-063 | 原則 I（每個原始檔寫明替代方案）；作法 6；計畫 `test_scope.py:76` | 功能 | 新增 `releases.py` 與 `test_releases.py` | 跑 `platform/tests/test_scope.py` 的 TC-070 | 通過：兩個新檔檔首都有 `# Nothing existing: …` 且夠長（≥15 字），不被判 MISSING／SHORT | 自動：`platform/tests/test_scope.py`（既有，必須仍綠） |
| TC-064 | 原則 I；作法 6 | 功能 | `releases.py` 檔首 | 驗收者讀檔首註解 | 說明了「nf-core 的 CLI 與 plugin 的 `prepare_launch.sh` 各自查 tag，平台沒有可重用的函式」這個意思，不是敷衍湊字數 | 手動：同 TC-057 |
| TC-065 | 原則 II（平台進程不開連線）；計畫 `test_scope.py:187` | 功能 | 同上 | 跑 `test_scope.py` 的 TC-061 | 通過：整個 `abf_platform/` 沒有 `ssh`、`station`、`urllib.request`、`import socket` 等被禁字樣（含新檔的註解與訊息） | 自動：`platform/tests/test_scope.py`（既有，必須仍綠） |
| TC-066 | 原則 II；計畫 `test_scope.py:101` | 功能 | 同上 | 跑 `test_scope.py` 的 TC-071 | 通過：沒有 `subprocess`、`threading`、`while True` | 自動：`platform/tests/test_scope.py`（既有，必須仍綠） |
| TC-067 | 計畫 `test_scope.py:144` | 功能 | 同上 | 跑 `test_scope.py` 的 TC-072（路徑形狀） | 通過 | 自動：`platform/tests/test_scope.py`（既有，必須仍綠） |
| TC-068 | 原則 II（沒有第二份執行狀態） | 功能 | 同上 | 跑 `bash tests/no_second_run_state_test.sh`（掃 `platform/` 下所有 .py） | 通過 | 自動：`tests/no_second_run_state_test.sh`（既有，必須仍綠） |
| TC-069 | 原則 V（憑證只在設定檔） | 功能 | 同上 | 跑 `bash tests/credentials_stay_in_settings_test.sh` | 通過 | 自動：`tests/credentials_stay_in_settings_test.sh`（既有，必須仍綠） |
| TC-070 | 完成標準（整個套件綠） | 功能 | 實作完成、已提交 | 在 WSL 跑 `bash tests/run_all.sh` | 全綠，沒有任何既有測試被改、跳過或放寬 | 自動：`tests/run_all.sh`（WSL） |
| TC-071 | 原則 IV（證據先於宣稱：測試必須能紅） | 功能 | `platform/tests/test_releases.py` | 驗收者搜尋 `skip`、`xfail`、`pytest.mark.skip`，並確認 T1–T22 每一項都有對應的測試函式且註解寫明 T 編號 | 沒有被跳過的測試；T1 至 T22 每一項都有測試（共至少 22 個對應） | 手動：同 TC-057 |
