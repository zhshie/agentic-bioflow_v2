---
id: release-tag-pick
title: 「最新版」的判斷邏輯：從一串 tag 挑出可啟動的最新 release，24 小時快取，來源可抽換（先做純邏輯，還不接線）
tier: A
kinds: backend
lane: L-release
base: v3（`origin/v3` @ 6061925；所有行號都是該版本）
source: developer-agent 讀碼查證（2026-10-25）；總表「版本政策」（replan 第 172 行、他 10-21 拷問五「新專案預設最新版並釘住」）；上一位規劃者建議的候選
---

# release-tag-pick

> A 級：新增一個沒人呼叫的純模組（比照 017a「先有函式、還沒有工具」）。接線（launch 表單預填、MCP `launch_prefill` 旁的最新版查詢）要動 `actions/__init__.py`、`mcp_server.py`、`web_board.py`，都在別人手上，列在「不做」與裁決 2。

## 目標
給一組 tag 名稱，算出「這個 pipeline 現在可以預填的最新版」，且保證算出來的值一定能通過 `REVISION` 檢查、能原樣送去啟動。有 24 小時快取、來源失敗時不丟例外。對使用者的意義：新專案預設最新版（仍然寫死成一個版本號），不用自己去查 nf-core 現在到幾版。

## 維護者原話（verifier 出題用）
- 「新專案預設最新版並釘住」（replan 第 28 行摘要；第 58 行 16.）→ T6、T7（回傳具體版本號，不是 `latest`／分支名）。
- 「launch 表單與 MCP 預填＝該 pipeline 最新 release tag；專案記住版本、不自動升、新版只提示」（replan 第 172 行）→ T8（快取）、T14（有新版時只回報不覆蓋，回傳值同時帶 `revision` 與 `checked_at`，由呼叫端決定）。
- 「Pin an exact pipeline revision, never a branch」（repo `CLAUDE.md` Working conventions）→ T3、T4。

## 範圍：檔案（3 個）
- `platform/abf_platform/releases.py`（新）
- `platform/tests/test_releases.py`（新；檔首 `# Nothing existing: …` ≥15 字，`test_scope.py:38,76` TC-070 檢查）
- `specs/release-tag-pick/ledger.md`
- **不准動**：`actions/__init__.py`、`mcp_server.py`、`web_board.py`、`web.py`、`cli.py`、`store.py`、`abf_station/*`、`abf_launch/*`、`scripts/prepare_launch.sh`、`pyproject.toml`（`pyproject.toml:20` 的 `packages` 已含 `abf_platform`，新模組自動打包）。

## 作法（決定）
所有函式只做字串與 JSON 檔運算；**不開連線、不啟動程式**（`test_scope.py:187` TC-061 掃整個 `abf_platform/`，禁 `urllib.request`、`socket`、`ssh`、字面 `station` 等；`:101` TC-071 禁 `subprocess`、`threading`、`while True`。註解與錯誤訊息也不能出現這些字——寫「agent」不要寫那個詞）。
1. `repo_of(pipeline)` → `"owner/name"`：`"nf-core/ampliseq"` 原樣；不含 `/` 的 `"ampliseq"` 補成 `"nf-core/ampliseq"`。格式用與 `abf_launch/build.py:207` 相同的 `^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$`；不合（空、`..`、三段、帶空白）→ `ValueError`，訊息中英並陳（本專案慣例）。
2. `usable(tag)` → bool：tag 形狀為 `^v?[0-9]+(\.[0-9]+){1,3}\Z`（即 `compute_envs.py:63`／`abf_station/launch.py:35` 的 `REVISION` 去掉 40 位 sha 那一支）。`3.0.0dev`、`3.0.0-rc1`、`dev`、`master`、40 位 sha、帶空白或換行 → False。
3. `pick_latest(tags)` → `str | None`：只留 `usable` 的；以數字元組比較（`3.10.0 > 3.9.0`；`3.0 < 3.0.1`；`v` 只在比較時忽略）；同一元組（`v3.0.0` 與 `3.0.0`）取不帶 `v` 的；回傳**原字串**；沒有可用者 → None。非 list／含非字串元素 → 略過該元素，不丟例外。
4. `parse_ls_remote(text)` → `list[str]`：把 `git ls-remote --tags --refs <url>` 的輸出（每行 `<sha>\trefs/tags/<name>`，plugin 現行來源，`scripts/prepare_launch.sh:119-120`）轉成 tag 名稱；壞行略過。這讓第一個真來源可以不經 GitHub API（沒有 60 次／小時的匿名額度，實測 `X-RateLimit-Limit: 60`，2026-10-25）。
5. `lookup(pipeline, fetch, *, cache_path=None, clock=time.time, ttl=86400.0)` → dict，**永遠回 dict、不丟例外**：
   `{"pipeline": "nf-core/ampliseq", "revision": "3.0.0" | None, "source": "fetched" | "cache" | "stale-cache" | "none", "checked_at": float | None, "why": str | None}`。
   - `fetch(repo)` 是呼叫端給的函式，回 tag 名稱的 list；它丟任何例外都視為失敗。
   - 快取檔（`cache_path` 給了才用；JSON：`{"nf-core/ampliseq": {"revision": "3.0.0", "checked_at": 1760000000.0}}`）；`now - checked_at < ttl` 且 `checked_at <= now` 才算新鮮（剛好等於 ttl＝過期；檢查時間在未來＝過期）。新鮮 → `source:"cache"`，不呼叫 `fetch`。
   - 過期或沒有 → 呼叫 `fetch`，`pick_latest`；有結果 → 寫入快取（先寫暫存檔再 `os.replace`，不留半截檔）、`source:"fetched"`。
   - `fetch` 失敗或沒有可用 tag：有舊快取 → 回舊值、`source:"stale-cache"`、`why` 說原因；沒有 → `revision:None, source:"none"`。**失敗不寫進快取**（不做負面快取）。
   - 快取檔壞掉（不是 JSON、不是物件、值型別錯）→ 當作沒有，成功後覆寫成合法內容。`cache_path=None` → 只在這次呼叫內，不碰檔案。
6. 模組檔首 `# Nothing existing: …`（說明：nf-core 的 CLI 與 plugin 的 `prepare_launch.sh` 各自查 tag，平台沒有可重用的函式）。

## 失敗先行測試（`test_releases.py`；全部現在會紅，因為模組不存在）
| 編號 | 案例 | 預期 |
|---|---|---|
| T1 | `repo_of("ampliseq")`、`repo_of("nf-core/ampliseq")`、`repo_of("lab/own-flow")` | `nf-core/ampliseq`、同、`lab/own-flow` |
| T2 | `repo_of` 吃 `""`、`"../x"`、`"a/b/c"`、`"nf core/x"`、`None` | 各丟 `ValueError`，訊息含中文與英文 |
| T3 | `usable` 吃 `"3.0.0"`、`"v2.1"`、`"1.2.3.4"`、`"1.0"` | 全 True |
| T4 | `usable` 吃 `"3.0.0dev"`、`"3.0.0-rc1"`、`"dev"`、`"master"`、40 位 sha、`"3.0.0\n"`、`""` | 全 False |
| T5 | `pick_latest(["3.9.0","3.10.0","3.2.1"])` | `"3.10.0"`（不是字串排序的 `3.9.0`） |
| T6 | `pick_latest(["2.18.0","3.0.0","3.0.0dev","dev"])` | `"3.0.0"`（pre-release 與分支名被排除） |
| T7 | `pick_latest(["v3.0.0","3.0.0"])`、`pick_latest(["3.0","3.0.1"])` | `"3.0.0"`、`"3.0.1"` |
| T8 | `pick_latest([])`、`pick_latest(["dev","master"])`、`pick_latest([None, 3, "2.0.0"])` | `None`、`None`、`"2.0.0"` |
| T9 | `parse_ls_remote` 吃兩行正常輸出＋一行無 tab＋一行空白 | 只回兩個 tag 名稱，順序保留 |
| T10 | `lookup` 快取為空、`fetch` 回 `["2.18.0","3.0.0"]` | `revision "3.0.0"`、`source "fetched"`、`checked_at == clock()`、`fetch` 被呼叫一次、快取檔存在且是合法 JSON |
| T11 | 同上再呼叫一次（時間過了 3600 秒） | `source "cache"`，`fetch` 沒有再被呼叫 |
| T12 | 時間過了剛好 86400 秒 | 重新 `fetch`（邊界＝過期） |
| T13 | 快取的 `checked_at` 在未來 | 重新 `fetch` |
| T14 | 快取有 `2.18.0`，`fetch` 現在回 `3.0.0` 且已過期 | 回 `3.0.0`；快取檔更新；**回傳不含任何「覆蓋專案版本」的欄位**（只有上述五個鍵） |
| T15 | 過期、`fetch` 丟 `OSError` | `source "stale-cache"`、`revision` 是舊值、`why` 非空；快取檔內容未變 |
| T16 | 沒有快取、`fetch` 丟例外 | `revision None`、`source "none"`、不丟例外；之後 `fetch` 恢復，下一次呼叫就會再試（失敗沒被快取） |
| T17 | `fetch` 回全是不可用 tag（`["dev"]`） | `revision None`、`why` 點名「沒有可用的 release tag」 |
| T18 | 快取檔內容是 `not json`、`[]`、`{"nf-core/x": 5}` 各一次 | 都當作沒有、`fetch` 被呼叫、檔案被改寫成合法 JSON |
| T19 | 兩個 pipeline 各自快取 | 互不影響；同一檔存兩筆 |
| T20 | `cache_path=None` | 不建立任何檔案（用 `tmp_path` 前後比對） |
| T21 | 寫入中途失敗（讓 `os.replace` 丟錯） | 原快取檔內容不變、沒有留下 `.tmp` 檔 |
| T22 | 原始碼掃描：`releases.py` 不含 `urllib`、`socket`、`subprocess`、`threading`、`requests`、字面 `station`、`ssh`、`nextflow run` | 無命中 |

**現在會紅**：T1–T22 全部（模組不存在）。executor 先跑一次貼出紅輸出。

**會改斷言的既有測試：無。** 會掃到新檔、必須仍綠的既有檢查：`test_scope.py:76`（TC-070 檔首）、`:101`（TC-071）、`:144`（TC-072 路徑形狀）、`:187`（TC-061）；`tests/no_second_run_state_test.sh`（掃 `platform/` 下所有 .py）；`tests/credentials_stay_in_settings_test.sh`。

## 完成標準（done when）
- T1–T22 全綠；整個 `bash tests/run_all.sh`（WSL）綠。
- `git diff --name-only` 只含上列 3 個檔；既有檔零改動。
- 測試全程不開網路連線、不呼叫 `git`。

## 環境事實
- 現況：v3 的平台沒有任何「最新版」查詢；`launch_prefill`（`actions/__init__.py:191`）是「同一個人先前那一次 run 的內容」，不是版本查詢；網頁表單 `l_revision` 標「必填，要寫死」（`web_board.py:57,62`）。
- plugin 現行來源：`scripts/prepare_launch.sh:119-120` 用 `git ls-remote --tags --refs … | sort -V | tail -1`，PITFALLS 29 記其與 nf-core CLI 同源。它會把 `3.0.0dev` 之類排進來；本模組用 `usable` 擋掉。
- **實測（2026-10-25，我的機器）**：`GET api.github.com/repos/nf-core/ampliseq/releases/latest` 回 `3.0.0`（非 pre-release）；但 nano4 的站台 pipeline 清單只有 `2.18.0`（`configs/sites/nchc-nano4-ce.json`）。見裁決 2。
- 平台進程不准開連線（`test_scope.py:187` TC-061；`cloud_store.py:1` 檔首也這樣寫），所以**真的去抓 tag 不在這個任務**。

## 不做
- 不接線：不改 `request_launch`／`launch_prefill`／MCP 工具／網頁表單／`web_board.py`（前端與動作層各有人）。
- 不寫真正的抓取（`git ls-remote` 或 GitHub API）；不加 job kind（要動 `handlers.py`，排在 `cloud-cleanup-c` 之後）。
- 不自動升級任何已存在的專案；不新增設定鍵；不加 migration（**不需要 migration**：沒有動資料表，快取是呼叫端指定的獨立 JSON 檔）。

## 裁決
1. **真來源放哪裡（待維護者／developer-agent）**：平台進程被 TC-061 禁止開連線（那是憲法原則 2 的檢查）。三條路：(a) 站台 agent 新增唯讀 job kind `latest_release`（`git ls-remote`，改 `handlers.py`，`after: cloud-cleanup-c`，agent 的唯讀白名單要放寬，需他點頭）；(b) 修改 TC-061 允許一個專屬檔——動憲法級檢查，C 級；(c) 由使用者的 AI／瀏覽器查，平台只收結果（`fetch` 換成使用者端傳入）。**預設採 (a)**，另開 `release-lookup-job`。本任務與三者都相容，因為 `fetch` 是參數。
2. **站台有裝的版本優先於「最新」**：nano4 的 `sitePipelines` 只有 ampliseq `2.18.0`，最新卻是 `3.0.0`；預填成 `3.0.0` 會退回 `owner/name -r` 路線（M1-02 的退路），失去國網本地模組的好處。接線任務要決定：CE 的 `sitePipelines` 命中該 pipeline 時，預填用站台版本、只「提示有新版」。**預設採此做法**；本任務只回傳最新版，不替呼叫端選。
3. **失敗不做負面快取**（預設）：GitHub 匿名額度 60 次／小時，但本模組一個 pipeline 一天最多成功查一次；失敗每次重試的成本由接線處決定要不要加退避。
4. **tag 形狀**：只接受 `REVISION` 能通過的數字版本；nf-core 偶有的 `1.0dev` 類 tag 一律不當「最新」。

## 裁決（2026-10-25 00:40，developer-agent）
1. 模組保持純函式、`fetch` 當參數；真正去 GitHub 抓由後續任務 `release-lookup-job`（新的唯讀站台工作種類，after cloud-cleanup-c）做，不放寬 TC-061。
2. 之後接線時優先用站台已有的版本，「最新版」只當提示；本片只做挑選邏輯。

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
