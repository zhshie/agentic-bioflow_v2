---
id: cli-fetch-publish-figure
title: 使用者電腦上的兩條指令 fetch-results／publish-figure：經平台公開網址以自己的權杖，把 run 的小型結果表拉到本機並給 R 載入碼，把 RStudio 畫好的圖發佈回平台圖庫
tier: B
kinds: backend
risk: L        # 範圍檔案本身不含保護路徑（依 README 規則為 M）；但本案新增「使用者本機保存權杖」與「經公開網址連線」兩個面，建議升 L，理由見「風險說明」
serves: S2-RSTUDIO
lane: L-cli-fetch-publish-figure
branch: feat/cli-fetch-publish-figure
base: v3
depends: mcp-publish-figure
soft-depends: mcp-site-connection-status
source: 維護者 2026-11-05（Studio 跑在自己電腦、平台不執行腳本）；2026-11-07 決定 Q11、Q17；2026-11-07 回答 RStudio 在使用者自己的裝置；ADR 0010 第 41 行；docs/OPERATIONS.md 52-59（Tailscale Funnel）；platform/abf_platform/{cli.py,http_auth.py,mcp_server.py,store.py,web_downstream.py}、platform/abf_launch/cli.py、platform/tests/test_pat.py
---

# cli-fetch-publish-figure

> 2026-11-07 改版：維護者答「在使用者自己的裝置」，RStudio 不在平台所在的桌機。前一版「CLI 在平台所在機器執行、遠端模式列後續項 S2-RSTUDIO-REMOTE」**已作廢**，遠端模式是本件第一版必備。其餘已查證的內容（取檔規則、R 載入碼、下游頁改字、被釘住的測試）保留，凡涉及「直接呼叫 actions／jobs／本機 platform.db」處已改寫。
>
> 依賴：`mcp-publish-figure`（MCP 工具 `publish_figure(run_id, filename, content_base64, code, params, caption)`，圖進私有圖庫、新圖 `packed=false`）。`fetch-results`、`studio-connect`、下游頁改字不依賴它，可先做；`publish-figure` 在該計畫合進 v3 之前不能驗收。軟依賴 `mcp-site-connection-status`：它讓 `list_compute_envs` 附 `site_connection`、讓站台斷線錯誤句註明 agent；本案只「有就印、沒有就不印」，不因它未合併而失敗。兩計畫與本案**檔案零重疊**（本案只加 client 端新檔，不碰 `actions/`、`mcp_server.py`、`jobs.py`、`abf_station/`）。

## 目標
使用者在自己的電腦（RStudio 所在）執行 `abf-platform studio-connect`（一次性，存平台公開網址與自己的個人權杖）、`abf-platform fetch-results <run>`（把該 run 結果資料夾裡的小型表只讀拉到本機資料夾，印出 R 載入碼）、`abf-platform publish-figure <run> <圖檔> [--code 檔] [--params 檔]`（把圖連同程式碼與參數發佈到私有圖庫）。三者都作為 **MCP client**，經平台公開網址（Tailscale Funnel，目前為 `https://desktop-7j5l5bj.tail6bf2f5.ts.net`，MCP 在 `/mcp`）以使用者自己的權杖連線，呼叫與 AI 助手相同的 MCP 工具（即同一個 actions 層）。下游頁的指令區改為這些指令。平台不執行任何腳本。

## 維護者原話（verifier 出題用）
1. 「在R studio介面要能看」→ `fetch-results` 的輸出必須讓使用者在 RStudio 打開即可讀到表：拉回的檔案放在單一本機資料夾，並印出可直接貼進 RStudio console 的 R 載入碼（讀 ASV 表／counts 表）；下游頁的指令區要有這條指令。
2. 維護者 2026-11-05：「Studio（RStudio／Jupyter）跑在使用者自己電腦，平台不執行腳本」→ 兩條指令都不啟動、不執行任何腳本；`fetch-results` 只讀；下游頁不再給 `jupyter lab`／`docker run` 兩行。
3. 維護者 2026-11-07（Q11）：把小型結果表與報告拉到本機資料夾並輸出 R 載入碼，只讀、依 readRoots、單檔上限同 25MB 規則 → 超過 25 MB 的檔案不下載且列出名稱；站台拒絕的路徑原樣顯示拒絕原因。
4. 維護者 2026-11-07（Q17）：圖連同程式碼與參數發佈到平台圖庫，呼叫與 MCP `publish_figure` 相同的 actions 層函式，不走確認頁，圖進私有圖庫、不進交付包 → 不建立任何 `confirmations` 列；圖發佈後不在交付包的勾選集合內。
5. 維護者 2026-10-27 用字裁示：「一樣要注意中文的顯示不能口語」→ 新增中文字串為正式書面語；英文版無中日韓字元。
6. 維護者 2026-11-07，回答「你的 RStudio 主要在哪台電腦」：「在使用者自己的裝置」→ 兩條指令必須能在**不是平台所在機器**的電腦上執行：不讀本機 `platform.db`、不假設與平台同機；只憑公開網址與使用者自己的權杖。

## 範圍：檔案
只准改這些檔：
- `platform/abf_platform/studio_remote.py`（新檔）：**唯一**碰網路與權杖的模組。`load_config()`、`save_config()`、`open_session()`（MCP client，Streamable HTTP，帶 `Authorization: Bearer`）、`call_tool(name, args)`、錯誤分類（見作法 5）。
- `platform/abf_platform/studio_cli.py`（新檔）：`cmd_studio_connect`、`cmd_fetch_results`、`cmd_publish_figure`、`add_commands(sub)`，純函式 `r_snippet(files, folder)`。只經 `studio_remote.call_tool` 取資料。**不放進 `abf_launch/cli.py`**：該檔被多個測試釘住「誰可以用 confirm／actions」（`test_human_channel.py:552`、`test_actions_layer.py:510、561`、`test_resume_scope.py:46`）。
- `platform/abf_platform/cli.py`：只在 `build_parser`（756 行起，於 `launch_cli.add_commands` 呼叫附近，920 行）加一行註冊；不改別的指令。executor 須確認這三條指令走完 `main` 時**不開啟、不建立** `platform.db`／`tokens.db`（遠端電腦上沒有這些檔）。
- `platform/abf_platform/web_downstream.py`：`_commands` 與 `STRINGS` 中指令區相關鍵（`jupyter`、`rstudio`、`placeholder_note`、`copy_note`）改為新指令說明；`HOME_RESULTS`、`RM_FLAG` 兩常數若不再用則刪除（其拼寫是為了躲 `test_scope TC-072`、`test_cleanup_confirm TC-068` 的掃描，刪後須確認那兩個測試仍綠）。**不改** `studio_url`、`_form`、`_answer`、`render_downstream` 簽章（`test_web_downstream.py:268-277` 釘住）。
- `docs/PLATFORM.md`（三條指令、設定檔位置與格式、錯誤與結束碼）、`docs/OPERATIONS.md`（只在 Funnel 段後加一小節：使用者如何向管理者取得 `pat new` 發的權杖、公開網址從哪看）、`docs/TESTING.md`（手動步驟）、`CHANGELOG.md`。
- 新測試：`platform/tests/test_studio_cli.py`、`platform/tests/test_studio_remote.py`。
- 既有測試必須同步改（只增不減，不放寬）：
  - `platform/tests/__golden__/cli_help_top.txt`（第 2、10 行的指令集合、第 34 行附近的說明列）與 `cli_tree.txt`：用既有重生方式更新，executor 先 `git grep -n "cli_help_top" origin/v3 -- platform/tests` 找重生旗標。
  - `platform/tests/test_cli_contract.py`：`MATRIX`（134 行附近）加**三個** `leaf`；`test_every_leaf_is_in_the_matrix`（169 行）不得放寬。
  - `platform/tests/test_cleanup_offer.py:819`（`COMMANDS` 清單）、`platform/tests/test_station_envs.py:430、450`（頂層指令集合與括號內順序字串，順序＝註冊順序）。
  - `platform/tests/test_web_downstream.py:91-92、109、281`：原釘 `jupyter lab --notebook-dir`／`rocker/rstudio`，改釘新指令；`:119`（非成功的 run 不含 `jupyter`）保持；`test_strings_table_parity_and_wording`（252 行）、`test_board_touches_are_minimal`（262 行）、`test_wording_in_command_block`（281 行起「指令區禁用字」）原樣必須綠。
  - `platform/tests/test_launch_docs.py:27、55`：文件測試若掃描 `abf-platform <動詞>` 範例行（只認 `launch|cancel|launches|fetch-records|rebuild`），新指令範例行不得被誤判；executor 讀該測試後只在需要時擴充。
  - `platform/tests/test_cli_usage_doc.py`、`test_cli_flags.py`、`test_cli_snapshots.py`：executor 先 `git grep -n "fetch-records" origin/v3 -- platform/tests` 與讀這三檔，凡是列舉全部指令或旗標者同步（只增不減）。
- 被釘住、**不得改動**：`web_board.py`、`web.py`、`STYLE`／CSS（`CSS_SHA256`）、`jobs.py`、`actions/`（含 `__init__.py`、`figures.py`）、`mcp_server.py`、`http_auth.py`、`store.py`、`platform/abf_station/`、`.github/`、`hooks/`、憲法、`plugin.json`。**伺服端零改動**：若發現非改不可（例如 `/mcp` 路徑需要新旗標），立即停手回報。

## 作法

### 1. 兩種做法比較與選擇：採「CLI 當 MCP client」
| 項目 | A：CLI 當 MCP client（採用） | B：CLI 直接打平台 HTTP 路由 |
|---|---|---|
| 驗證 | `/mcp` 已有 `BearerAuth`（`http_auth.py`），PAT（`abf_pat_…`，`store.create_token(kind="pat")`）與 OAuth 權杖皆可；本案直接重用 | 網頁路由（`/run/file` 等）用**登入 cookie**，沒有 Bearer 檢查；要用 PAT 就得在 `web.py` 新增一套 token 驗證路徑，新增攻擊面 |
| actions 層 | MCP 工具就是 actions 層的薄包裝，Q17 要求「呼叫與 MCP publish_figure 相同的函式」自然成立 | 要新增（或重用）HTTP 路由，路由處理函式易長出第二份邏輯（專長守則禁止） |
| 伺服端改動 | 零 | 至少 `web.py` 新路由＋認證，且與 `mcp-publish-figure`、`web-result-viewer` 同碰 `web.py`（已知衝突區） |
| 能力邊界 | `read_run_file` 只回文字（至多 200,000 字元一頁，`next_offset` 分頁），二進位與 `.html` 不傳，只給網址；需多次往返（25 MB 約 125 頁） | `/run/file` 可整檔下載（含 `.html`、二進位），往返少 |
| 依賴 | `pyproject.toml` 已有 `mcp>=2.3,<3`，其 client 端已隨附，**不新增依賴** | 需 HTTP 客戶端（`httpx` 目前只在 test extra），要新增依賴或用標準庫 |
| 對外介面 | 沿用已公開、已有契約測試的 `/mcp` | 擴大公開網址上的路由 |

選 A 的理由：不動伺服端、不新增認證面、重用已測試的 Bearer 檢查與 actions 層；代價是 `.html` 報告與二進位檔無法經 MCP 取得（見作法 3、待裁決 3）與往返較多。executor 須先讀 `pip show mcp` 版本的 client API（`streamable_http` client 與 `ClientSession`，名稱以已安裝套件為準，**不要憑記憶**），在 ledger 記下實際使用的函式。

### 2. 權杖怎麼取得與保存
- 取得：權杖由平台管理者在平台那台機器執行 `abf-platform pat new --user <名字>` 發給使用者（既有機制，`cli.py:260`，格式 `abf_pat_…`，永不過期，可 `pat revoke`）。本案**不新增任何發權杖的方式**。
- 使用者本機新指令 `abf-platform studio-connect --server <公開網址>`：權杖以**隱藏輸入**（`getpass`）詢問，或 `--token-stdin` 從標準輸入讀；**不提供 `--token VALUE` 旗標**（會進 shell 歷史與行程列表）。環境變數 `ABF_PAT` 若有則優先於檔案（給無人值守用）。
- 驗證網址：必須 `https://主機`、無路徑；僅 `http://127.0.0.1:埠`／`localhost` 例外（規則同 `cli.py:520-535` 對 `--public-url` 的檢查，複製其判斷，不改該處）。非 https 的遠端網址一律拒絕，因為權杖會走明文。
- 存放：只放使用者本機設定檔 `ABF_STUDIO_CONFIG` 或 `~/.abf/studio.json`（JSON：`{"server": "...", "token": "..."}`）。寫入流程：資料夾 0700；`os.open(tmp, O_WRONLY|O_CREAT|O_EXCL, 0o600)` 寫暫存再 `os.replace`（照 `cli.py:197` 與 `records.py:62`）。讀取時在 POSIX 若 `mode & 0o077` 則**拒用**並說 `chmod 600 <路徑>`（照 `abf_station/cli.py:78`）。Windows 的權限位元不可信（PITFALLS 1182），不拒用，改在文件寫明該檔位於使用者個人資料夾、請勿放進雲端同步資料夾，並在 `studio-connect` 成功時印一次此提醒。
- 不外洩：權杖永不印出（成功訊息只印網址與「權杖已存入 <路徑>」）、不寫進任何 log、不在例外訊息、`--json` 輸出、R 載入碼出現；`studio-connect` 預設先用該權杖連一次 `/mcp`（列工具）確認有效才存檔，`--no-check` 供離線時先存。
- `studio-connect` 重跑覆蓋舊設定並印「已覆蓋」。不做 keyring（不新增依賴）。

### 3. fetch-results `<run>` [`--dir 資料夾`]
沒有 `--user`（權杖即身分）。
- 本機資料夾預設 `~/abf-results/<run>/`（`--dir` 可改）；先印絕對路徑。
- 取檔流程只經 MCP 工具：`run_outputs(run_id, path)` 逐層列結果樹（深度上限 3、檔案數上限 200；檔案列的 `download` 是給 `read_run_file` 的路徑、資料夾列的 `enter` 是下一層的 `path`），再對每個符合的檔呼叫 `read_run_file(run_id, path, offset)`，依 `next_offset` 分頁直到 `None`，頁面串接後以 UTF-8 寫入（逐頁累加，不得在整檔讀完前當作成功）。兩個工具都**不等待**，回 `state=loading` 時 CLI 每 2 秒再問，整體期限預設 120 秒（單檔另計；常數放 `studio_cli` 頂端，測試可縮短）。
- 取哪些檔：副檔名（小寫）在 `.tsv .csv .txt .md .json` 且 `size ≤ jobs.RUN_FILE_MAX_BYTES`（25 MB，**引用常數，不另寫數字**）。`.html` 與二進位（`.gz .bam .fastq .png` 等）不經 MCP 傳送：`.html` 列在「略過」並印工具回的網址說明（需用瀏覽器登入平台下載）；`too_large` 的檔列出名稱與大小、不下載。總量上限 100 MB（`MAX_TOTAL_BYTES`，超過即停並列出未取的檔名）。
- readRoots 與單檔上限由站台代理與 actions 層判斷；CLI **不重做**，只原樣顯示 `refused`／`bad_path`／`too_large` 的原因。
- 寫入本機：每檔先寫暫存檔再 `os.replace`；目的路徑 `resolve()` 後必須在目標資料夾內（結果樹路徑含 `..` 或點開頭部分的情形再做縱深防禦）；同名檔覆蓋並印「已覆蓋」。
- 結束時印摘要：取到 n 個、略過 m 個（含原因）、資料夾路徑，接著印 R 載入碼區塊（作法 4）。
- 結束碼：全部成功 0；有檔失敗或因錯誤略過 1；未設定連線 2；連線或權杖問題 3（見作法 6）。run 不是呼叫者的或不存在：以工具回的 `found: False` 訊息原樣顯示（兩種同一句，與 MCP 相同），結束碼 1，不建立資料夾。

### 4. R 載入碼（內容不變）
純函式 `r_snippet(files, folder)`，輸入已取到的相對路徑與資料夾，輸出字串；不執行 R、不偵測本機 R。
- 依檔名找候選表：ASV 表（檔名含 `ASV`／`feature-table`／`abundance` 且為 `.tsv`）、counts 表（檔名含 `counts` 且為 `.tsv`／`.csv`）。每個候選一行 `read.delim(file.path("<資料夾>", "<相對路徑>"), check.names = FALSE, row.names = 1)`（`.csv` 用 `read.csv`）；資料夾以 R 可吃的正斜線路徑印出（Windows 的 `\` 轉 `/`），路徑中的 `"` 與 `\` 逸出。
- 沒有候選時對每個取到的表印一行 `read.delim`／`read.csv`，上限 5 個，其餘寫「其餘檔案見資料夾」。
- 碼區塊前加一句「將下列程式碼貼入 RStudio 的 Console」，英文同結構；**不含權杖、密碼、站台或平台主機名稱**。說明字串集中成表（zh／en 同鍵），英文無 CJK，中文為正式書面語。

### 5. publish-figure `<run>` `<圖檔>` [`--code 檔`] [`--params 檔`] [`--caption 文字`]
- 讀本機圖檔；CLI 只先擋「檔案不存在／讀不到」與超過 `figures.MAX_BYTES` 的明顯情形（**引用該常數**；`mcp-publish-figure` 計畫為 5 MB，並限 png／svg／jpg）。`--code`、`--params` 讀為 UTF-8 文字（嚴格解碼，失敗拒絕並說哪個檔）；長度上限引用 `figures` 模組中對應 `code`（計畫為 100 KB）與 `params`（計畫為 10 KB）的常數，**常數名以 `mcp-publish-figure` 實際合併的為準**，不另寫數字；其餘由伺服端動作判斷。
- 呼叫 MCP 工具 `publish_figure(run_id, filename, content_base64, code, params, caption)`；`filename` 取圖檔的檔名。不經確認頁、不呼叫 `confirm`、不建立 `confirmations` 列。
- 成功印：圖名、大小、「已存入私有圖庫」、「不會加入交付包」（依回傳 `state: ok`）。回 `refused` 時印其 `reason`，結束碼 1，不寫任何東西。
- 擁有權：由權杖決定；非自己的 run 與不存在的 run 同一句（工具既有行為）。

### 6. 連線與錯誤分類（`studio_remote` 負責，三條指令共用，訊息說「發生什麼、怎麼辦」，不露堆疊與權杖）
| 情況 | 判斷 | 訊息要點 | 結束碼 |
|---|---|---|---|
| 未設定 | 設定檔不存在且無 `ABF_PAT` | 先執行 `abf-platform studio-connect --server <平台網址>` | 2 |
| 設定檔權限過寬（POSIX） | mode 檢查 | `chmod 600 <路徑>` | 2 |
| 權杖錯誤／已撤銷 | HTTP 401 | 權杖不正確或已被撤銷；向平台管理者重新索取（`pat new`），再 `studio-connect` | 3 |
| 帳號停用／他人連線階段 | 403／404 session | 重新執行一次；仍失敗請洽管理者 | 3 |
| 自己的電腦離線 | DNS 失敗、連線被拒、無網路 | 請先確認本機網路；以 `--server` 的網址為準 | 3 |
| 公開網址不可達 | 逾時、TLS 失敗、HTTP 502／503／504 | 平台公開網址無回應：平台所在機器可能未開機，或 Tailscale Funnel／MCP 服務未啟動；列出所用網址（網址不是祕密）；**不重試超過 2 次**（間隔 2 秒） | 3 |
| 站台連線未開 | 工具 error 文字含 "No open connection to the site"，或 code 為 `site_unreachable`／`agent_offline` | 平台可達，但計算站台（nano4 等）的連線沒開；若 `mcp-site-connection-status` 已合併，額外呼叫一次 `list_compute_envs`，印出對應計算環境的 `site_connection.state`／`as_of`／`agent`（沒有此欄就不印）；錯誤句已含 agent 名者原樣顯示 | 1 |
| 路徑被拒 | `refused`／`bad_path`／`too_large` | 原樣顯示 reason | 1 |
- 照 PITFALLS 58：「站台連線過期」與「路徑被拒」必須是不同訊息，不可全說成「路徑不正確」；各有測試。
- 單次呼叫逾時 30 秒（常數，測試可縮短）；整體不無限重試。

### 7. 下游頁指令區（web_downstream.py）
`_commands(t, lang, run)` 印三行字面指令的 `<pre class="reason">`：首次使用 `abf-platform studio-connect --server <平台網址>`、`abf-platform fetch-results <run id>`、`abf-platform publish-figure <run id> <圖檔>`（run id 用 `run["id"]` 經 `_e` 逸出；`_commands` 為檔內函式，`render_downstream` 簽章不變）。說明句：「平台不執行腳本；請在自己的電腦執行下列指令，結果表會放到該電腦的資料夾，圖發佈後出現在圖庫。」英文同結構。保留既有 `intro` 句（含「不在 NCHC 登入節點啟動」，`test_wording_in_command_block` 只允許該句出現 `nchc`）與貼網址表單。指令區不得出現 `token`、`password`、`nchc`、`ln01`、`sbatch`、`srun`（中文用語是否可寫「個人權杖」由 executor 先跑禁用詞測試確認；不確定就不寫在指令區，改寫在 PLATFORM.md）。頁面是純函式，不知公開網址，故用 `<平台網址>` 占位。

### 8. 平台不執行腳本、不碰本機資料庫
`studio_cli.py` 不 import `subprocess`、`socket`、`urllib`、`requests`、`httpx`；不含 `Rscript`；不 import `store`／`actions`／`jobs`（唯一例外：讀常數 `jobs.RUN_FILE_MAX_BYTES`、`figures.MAX_*`，且只能 `from … import 常數`，executor 確認這兩個 import 不會連帶開資料庫）。`studio_remote.py` 只准 import MCP client 套件與標準庫（`json, os, getpass, pathlib, time`）。測試以原始碼掃描釘住（取代前一版「不得 import http」的掃描）。

### 9. `--json`
`cli.py:974` 對 `abf_launch` 模組回「尚不支援 --json」。新模組不屬 `abf_launch`，會被當成支援 `--json`；executor 確認輸出走 `_say` 同路徑，並在 `--json` 下回與 `launch` 一致的拒絕或正確 JSON 外殼（擇一並測），**任何情況下 JSON 內不得含權杖**。

## 失敗先行測試
`platform/tests/test_studio_remote.py`（設定與連線；一部分用替身 session，一部分用真的 `abf-platform mcp --http`，照 `test_pat.py` 的 `start_cli`、`free_port`、`wait_port`、`pkg_env` 與 `store.create_token(kind="pat")`）：
- `test_config_roundtrip_0600_and_atomic`：存檔後 mode 為 0600、資料夾 0700（POSIX；Windows 跳過並註明）；寫入中途失敗不留半檔。
- `test_config_too_open_is_refused`（POSIX）：0644 → 拒用並含 `chmod 600`。
- `test_env_pat_overrides_file`、`test_missing_config_exit_2_with_next_step`。
- `test_non_https_remote_url_refused_loopback_allowed`、`test_url_with_path_refused`。
- `test_token_never_printed_or_logged`：成功、401、不可達、逾時各路徑的 stdout／stderr／caplog／`--json` 都不含權杖字串；無 `--token` 旗標存在（argparse 檢查）。
- `test_wrong_token_gives_401_message_exit_3`（真伺服器）、`test_revoked_token_same_message`、`test_closed_port_gives_unreachable_message_exit_3`、`test_502_is_reported_as_service_not_running`（替身）。
- `test_site_link_closed_vs_path_refused_are_different_messages`（PITFALLS 58）；`test_site_connection_field_printed_when_present_and_silent_when_absent`。
- `test_studio_connect_checks_token_before_saving`、`test_no_check_saves_offline`。
- `test_new_modules_import_nothing_forbidden`、`test_commands_do_not_create_platform_db`（`ABF_PLATFORM_DB` 指向空資料夾，執行後資料夾仍空）。

`platform/tests/test_studio_cli.py`（替身 `call_tool`，不連網路）：
- `test_fetch_results_writes_tables_and_prints_r_code`：替身樹含 `ASV_table.tsv`、`counts.tsv`、`notes.md`、`report.html`、`x.bam`。斷言本機有前三個、沒有後兩個；`report.html` 列在略過並含瀏覽器下載說明；輸出含 `read.delim(` 與「Console」。
- `test_fetch_results_pages_by_next_offset_and_keeps_text_exact`：三頁串接後與原文逐位元相同（含 CRLF、中文）。
- `test_fetch_results_skips_too_large_and_lists_it`：`size = RUN_FILE_MAX_BYTES + 1` → 不呼叫 `read_run_file`、輸出含檔名與大小；剛好 `RUN_FILE_MAX_BYTES` → 取。
- `test_fetch_results_site_refusal_is_shown_and_rest_continue`：某檔回 `error/refused`＋reason → 輸出 reason、其他檔照取、結束碼 1。
- `test_fetch_results_polls_loading_then_ready_and_gives_up`：`loading` 兩次後 `ready` → 取到；永遠 `loading` → 期限（測試縮 0.2 秒）後停並印未完成檔名、結束碼 1。
- `test_fetch_results_unknown_or_foreign_run_same_answer`：`found: False` 同一句、不建立資料夾。
- `test_fetch_results_cannot_write_outside_folder`：`../evil.tsv`、`a/../../b.tsv`、點開頭部分 → 不寫任何檔。
- `test_fetch_results_total_cap`：累計超過 100 MB → 停並列出未取檔名。
- `test_r_snippet_pure_and_escaped`：固定輸入回固定字串；`C:\Users\a b\res` 轉正斜線；含 `"` 的檔名逸出；無候選時最多 5 行；不含 `token`／`password`／主機名。
- `test_publish_figure_calls_publish_figure_tool`：替身斷言傳入 `run_id`、`filename`、`content_base64`（解碼等於檔案位元組）、`code`、`params`、`caption`；成功印「私有圖庫」與「不會加入交付包」。
- `test_publish_figure_refusal_prints_reason_exit_1`、`test_publish_figure_missing_file_or_bad_utf8_code_file_refused`（不呼叫工具）。
- `test_publish_figure_end_to_end_private_not_packed`（待 `mcp-publish-figure` 合併後啟用，之前 `skipif` 並註明）：真伺服器發佈一張 PNG 後 `list_figures(packed_only=True)` 為空、`confirmations` 與 `jobs` 兩表列數不變。
- `test_commands_registered_and_help`：`build_parser()` 含三條指令；`--help` 結束碼 0；`allow_abbrev=False`。
- `test_strings_parity_and_wording`：新字串表 zh／en 同鍵、en 無 CJK、zh 通過 `test_web_wording_sweep.banned_in`。

`platform/tests/test_web_downstream.py`（改既有並新增）：
- 改 `test_downstream_succeeded_shows_section_not_placeholder`：中欄含 `abf-platform fetch-results %s`、`abf-platform publish-figure %s`（run id 已逸出）、含「平台不執行腳本」所屬句、含 `studio-connect`；**不含** `jupyter lab`、`docker run`、`rocker/rstudio`、`0.0.0.0`；仍含貼網址表單與 `http://localhost` 提示、仍無 `<iframe|<img|<script`。
- 新增 `test_downstream_commands_escape_run_id`（run id 含 `<`、`"`）；英文版同結構且 `no_cjk`。

## 完成標準（done when）
- 新測試全綠（`publish_figure` 端到端那條在依賴未合併時為 skip 並於 ledger 註明）；「必須同步改」的既有測試綠且只增不減；被釘住的測試未改。
- 整個 `platform/tests` 套件綠（「已知環境紅」`test_tc047_tc051_other_docs_untouched` 視同綠）。
- `git diff --stat` 不含 `jobs.py`、`actions/`、`mcp_server.py`、`http_auth.py`、`store.py`、`web_board.py`、`web.py`、`platform/abf_station/`、`.github/`、`hooks/`、憲法、`plugin.json`。
- **手動走通（必須在非平台機器上做，ledger 附輸出）**：在使用者自己的電腦（不是桌機）安裝套件，`abf-platform studio-connect --server https://desktop-7j5l5bj.tail6bf2f5.ts.net`，對一個 succeeded run 執行 `fetch-results`，在 RStudio Console 貼上印出的程式碼讀到表；用 R 產一張 PNG，執行 `publish-figure <run> fig.png --code plot.R --params params.json`，確認圖在私有圖庫（此步依 `mcp-publish-figure` 已合併）。另做三項負面操作並貼訊息：故意輸入錯權杖（401 句）、關閉本機網路（離線句）、請維護者暫停 Funnel 或 MCP 服務（不可達句）。若無第二台電腦，至少用同一台但**設定檔指向公開網址而非 127.0.0.1**，並在 ledger 標明未能驗證跨機。
- **截圖（B 級）**：`stage=downstream` 頁 1440／390 寬 × zh／en 共 4 張，axe 無 serious／critical；`ui_check.py` 不存在則用 Playwright 經 `with_server.py` 並標 axe UNVERIFIED；截圖不存進 Drive 工作區。
- ledger 貼：`git diff --stat`、`MAX_TOTAL_BYTES`／逾時等新常數、實際使用的 MCP client 函式名與 `mcp` 套件版本、設定檔 `ls -l` 輸出（權限）。

## 風險說明（為何建議 L）
README 規則只看檔案路徑，本案範圍不含保護路徑，機械推定為 M。建議升 L 的理由：(1) 新增「使用者本機保存長效權杖」，PAT 永不過期且權限等同該使用者全部 MCP 能力（含 `launch` 類詢問工具與讀取自己的結果）；外洩面包括設定檔權限、shell 歷史、log、Windows 權限位元不可信；(2) 新增經公開網址的明文以外連線路徑，需正確處理 https 檢查與錯誤分類；(3) 本案無法以單機測試完全證明跨機行為。爆炸半徑證明（L 要求）：伺服端零改動，故障面限於使用者本機的三條指令與一個設定檔；權杖可 `pat revoke`。lead 若認為 M 即可，把 frontmatter 的 `risk` 改回 M 並同步佇列任務物件。

## 環境事實
- `/mcp` 的驗證：`http_auth.BearerAuth` 接受 `abf_pat_…` 與 OAuth 存取權杖，401 時回 `WWW-Authenticate: Bearer`，階段 id 綁使用者（他人用同階段得 403，未知階段 404）。網頁路由（`web.py`）用 cookie，不接受 PAT。
- PAT 由 `abf-platform pat new --user NAME` 發行（`cli.py:260`），`store.create_token(kind="pat")`，格式 `abf_pat_` + 43 字元；`test_pat.py` 是該機制的測試。
- `run_outputs`、`read_run_file`（`mcp_server.py:107、118`）皆不等待，回 `state` 為 `loading|ready|error|unavailable|too_large`。`read_run_file`：文字至多 200,000 字元一頁（`READ_CHARS`），以字元計的 `offset`／`next_offset`；二進位與 `.html` 不傳，只給名稱、大小、網址 `/run/file?run=&path=`；超過 25 MB 回 `too_large` 與大小。`run_file_path_problem`（`jobs.py:577`）拒絕絕對路徑、`..`、點開頭部分、控制字元；雲端與 K8s 環境回 `not_on_site`。
- `jobs.RUN_FILE_MAX_BYTES = 26214400`（`jobs.py:51`）；readRoots 在 `compute_envs.py:219` 驗證、在 `abf_station/rules.py:109-165` 判斷。CLI 不重做。
- `fetch-records`（`abf_launch/cli.py:423`）抓 Nextflow 日誌供 `rebuild`，存 `platform.db 旁/records/<run>`，與本案無關；`fetch-results` 說明各寫一句區分。
- 部署：Tailscale Funnel 在 `docs/OPERATIONS.md:52-59`（`tailscale funnel --bg 8080`，Caddy 分路徑，MCP 在 `/mcp`）。公開網址由使用者在 `studio-connect` 提供，**程式碼內不寫死任何主機名**（文件範例可寫）。
- `web_downstream.py` 現況：`_commands` 印 `jupyter lab --notebook-dir …` 與 `docker run … rocker/rstudio`，另有貼網址表單；純函式，不碰資料庫、檔案、網路（`test_web_downstream.py:252-257` 掃 import）。
- 指令註冊：`cli.py:build_parser` 756 行起；`launch_cli.add_commands` 在 920 行；`--json` 在 974 行。
- 測試釘住指令集合的位置：`__golden__/cli_help_top.txt`、`cli_tree.txt`、`test_cleanup_offer.py:819`、`test_station_envs.py:430/450`、`test_cli_contract.py:134/169`。
- 依賴的合併順序：`mcp-publish-figure` 會把工具數 22→23 並改 `test_pat.py:384`、`test_mcp_contract_tools.py` 等；本案不碰這些，無衝突。`mcp-site-connection-status` 動 `actions/__init__.py`、`mcp_server.py` 說明文字、`abf_station/`；本案不碰。三案只在文件檔（`docs/PLATFORM.md`、`CHANGELOG.md`）可能 merge 衝突，落地前 `git merge origin/v3`。
- PITFALLS 已查（`docs/PITFALLS.md`；`docs/solutions/` 不存在）。相符項：
  - 「58. A failed first ssh step was read as bad input」（Check：`test_station_realpath_down.py`；症狀：站台連線過期時 `read_run_file` 誤答路徑被拒）→ 作法 6 把 `site_unreachable`／`agent_offline` 與 `refused`／`bad_path` 分開，測試覆蓋。
  - 「兩支腳本預設寫同一個 `analysis/figures`，後跑的蓋掉前一個」（PITFALLS 1550、1569-1572；Touches: `analysis/figures`）→ `publish-figure` 同名覆蓋由伺服端動作決定；R 載入碼與說明不得假設固定的 `analysis/figures` 路徑。
  - 「MSYS mounts NTFS without `acl`. The permission bits it reports are a fiction」（docs/PITFALLS.md 約 1182 行，標題 executor 開檔確認）→ Windows 使用者電腦上不能以 0600 檢查當作保護；作法 2 的處理與文件說明。
  - Jupyter 連線檔含 HMAC key 的條目（PITFALLS 1375、1629）只作旁證：指令區與 R 載入碼不得放權杖或金鑰（測試已列入）。
  - 其餘條目（ssh 多工、WSL、nf-core 圖網址等）與本案無關。

## 待裁決
（前一版沒有獨立的「## 裁決」段，只有「## 待裁決」；本版保留該段並改寫如下。）
1. ~~程式碼與參數如何保存~~ 已解：`mcp-publish-figure` 現行版本已含 `code`、`params` 兩欄，且新圖預設 `packed=false`（不進交付包）。本案只需確認該計畫合併時欄位名與上限常數未變。
2. ~~「本機」是哪一台；遠端列為後續~~ **已作廢，遠端模式列入本件**：維護者 11-07 答「在使用者自己的裝置」，三條指令在使用者電腦執行，經公開網址以自己的權杖連線，選「CLI 當 MCP client」（作法 1）。`S2-RSTUDIO-REMOTE` 後續項取消。
3. `.html` 報告（如 MultiQC）與二進位檔經 MCP 無法取得（`read_run_file` 視為二進位）。第一版先列為「略過，請用瀏覽器下載」。若維護者要求 `.html` 也要拉到本機資料夾，需新增伺服端能力（另案，會動 `mcp_server.py`／`web.py`）。
4. 使用者電腦如何取得 `abf-platform` 指令（目前套件在 `platform/` 之下，`pip install` 的對外發行路徑未查到）：本案假設使用者能 `pip install` 本 repo 的 platform 套件；若要提供獨立的輕量 client 套件，另案。
5. 風險等級 L 或 M（見「風險說明」）。
6. 取檔副檔名白名單、總量 100 MB、檔案數 200、單頁往返逾時 30 秒是否合適。
7. 指令名稱 `fetch-results`、`publish-figure`、`studio-connect` 是否採用。

## 不做
- 不啟動 RStudio／Jupyter、不執行 R 或 Python、不偵測使用者本機 R。
- 不改伺服端：不新增 jobs 種類、站台協定、資料表、HTTP 路由、認證路徑；不改 `jobs.py`、`actions/`、`mcp_server.py`、`http_auth.py`、`web_board.py`、`web.py`。
- 不新增依賴（不加 `httpx` 為正式依賴、不加 keyring）。
- 不新增發權杖的方式（沿用 `pat new`）；不做 OAuth 瀏覽器登入流程。
- 不做整個結果樹的鏡像、不做二進位與 `.html` 下載、不做大檔分段續傳。
- 不做交付包打包、不做「發佈後勾選進交付包」、不做刪圖（皆屬 `mcp-publish-figure` 的後續切片）。
- 不做 `--json` 完整外殼（只要求不崩潰、不外洩、行為明確）。
- 不改貼網址表單與 `studio_url` 規則。

## 裁決（lead，2026-11-07，回應修補後的待裁決 3–7）
1. 風險維持 **L**（新增本機長效權杖與公開網址連線）；佇列登記為 L，PASS 後跑對抗審，通過前不掛自動合併。
2. `.html` 報告經 MCP 取不到，第一版略過（RStudio 用途以結果表為主）；要拉 HTML 另案新增伺服端能力，不在本件。
3. 安裝路徑：第一版假設使用者能 `pip install` 本 repo 的 `platform/` 套件；executor 在 `docs/` 寫明安裝與 `studio-connect` 步驟並在 ledger 記錄實際安裝驗證。repo 為私有，須寫清楚如何取得存取權；不新增對外發行管道。
4. 副檔名白名單、總量 100 MB、檔案數 200、單次逾時 30 秒——接受為暫定值。
5. 指令名稱 `studio-connect`、`fetch-results`、`publish-figure`——接受。
6. 計畫 35 KB 超過 25 KB 上限：接受此一次（遠端模式不可拆）；executor 只需讀「範圍」「作法」「失敗先行測試」「完成標準」與「裁決」。
7. 完成標準「必須在非桌機的電腦上手動走通並做三項負面操作」維持——使用者的 RStudio 在自己的電腦。

## 裁決（lead，2026-11-12 晚，維護者回「同意」；本段優先於上文任何相反的字句）

1. **發佈圖要經本人確認（取代「維護者原話 4」與作法 5 中「不走確認頁、不建立 confirmations 列」的字句）。** 維護者 2026-11-12 對 `mcp-publish-figure` 選 B：未經本人確認不得寫入；同日對本件回「同意」：「RStudio 發佈圖時，要你點一次確認連結」。因此 `publish-figure`：
   - 呼叫的是 `mcp-publish-figure` 合併後的工具形狀 `publish_figure(run_id, figures=[{filename, content_base64, code?, params?, caption?}])`，一次一張圖。**CLI 永不傳 `user_confirmed`，也不傳 `request_id`**（測試以替身斷言這兩個鍵不在引數內，並以原始碼掃描釘住 `user_confirmed` 字樣不出現在 `studio_cli.py`／`studio_remote.py`）。
   - 工具回「待確認」時：印圖名、大小、「尚未存入；請本人在瀏覽器開啟下列連結並按送出」與工具回的確認連結（原樣，不自行組網址），結束碼 0。不輪詢、不等待、不代按。訊息不得說「已存入」。
   - 工具回拒絕（大小、型別、圖庫已滿、非自己的 run 等）時：原樣印 reason，結束碼 1。
   - 訊息仍須含「不會加入交付包」之意（圖進私有圖庫，打包由本人在網頁勾選）。
   - 上限常數引用 `figures.MAX_BUNDLE_BYTES`、`MAX_CODE_BYTES`、`MAX_PARAMS_BYTES`、`MAX_CAPTION_CHARS`（以合併版為準）。
   - 「失敗先行測試」中 `test_publish_figure_calls_publish_figure_tool` 改為斷言 `figures` 清單的單一項目與上述訊息；`test_publish_figure_end_to_end_private_not_packed` 改為：發佈後 `confirmations` 多一列待確認、圖庫仍空；經確認頁核准後圖庫才有該圖且 `packed_only=True` 為空。
2. **分兩片交付：**
   - 第 1 片（現在就做，不依賴任何未合併的東西）：`studio_remote.py`、`studio-connect`、`fetch-results`、R 載入碼、下游頁指令區中 `studio-connect` 與 `fetch-results` 兩行、文件、相關既有測試同步。下游頁此片**不印** `publish-figure` 那一行，也不註冊 `publish-figure` 指令。
   - 第 2 片（`mcp-publish-figure` 合進 v3 之後）：`publish-figure` 指令、下游頁第三行、其測試與文件。
   verifier 出題時每條案例標明屬第 1 片或第 2 片；第 1 片的驗收不得因第 2 片未做而 FAIL。
3. 風險維持 L；合併前對抗審照舊。「在非桌機的電腦手動走通」維持為完成標準，由維護者在自己的電腦親手試。
4. 其餘（取檔規則、權杖保存、錯誤分類、被釘住不得改的檔、不做清單）不變。

## 裁決（lead，2026-11-12 深夜，回應 verifier 出題時的 P1 至 P10；與 test-case.md 的暫定寫法一致）

1. （P1）`.html` 依副檔名略過，**不**為了取網址去呼叫 `read_run_file`；訊息只說「須用瀏覽器登入平台下載」，不印網址。作法 3 中「印工具回的網址說明」一句作廢。
2. （P2）只有刻意略過（非白名單副檔名、`.html`、伺服端回 `kind: binary`）時結束碼 0；`run_outputs` 回 `unavailable`／`error`、任一檔取檔失敗、逾期、超過總量上限時結束碼 1。
3. （P3）深度 3、檔案數 200 由 CLI 自己擋；超出時摘要必須說還有未列出的檔，不得宣稱全部取得。
4. （P4）`studio_cli` 只准 `from abf_platform.jobs import RUN_FILE_MAX_BYTES` 這種常數 import，且 import 後不得開任何資料庫（TC-082 證明）。第 1 片不得 import `figures`。若 import `jobs` 會連帶開資料庫或 import 被禁的模組而無法滿足 TC-082／TC-083，executor 停手回報，不自行改 `jobs.py`。
5. （P6）站台連線沒開的判斷看原因文字（"No open connection to the site"）與 code `site_unreachable`／`agent_offline`，不能只看 `code == refused`。
6. （P7）確認連結的網址是平台設定的事（`web --public-url`），CLI 原樣印、不提示、不改寫；第 2 片驗收時由 TC-069 實機確認。
7. （P8）第 2 片：CLI 不印工具回的整段 `message`，只印自己的句子與 `url`。
8. （TC-002）`--token` 不存在；argparse 拒絕時的錯誤輸出不得含使用者打的值，接受自訂錯誤處理。
9. （P10）新指令的 `--help` 文字不得含 launch、submit、cancel 三個字（`test_station_envs.py` tc084）。
10. 行號偏差（P9）以 origin/v3 實際內容為準。

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

## 裁決（lead，2026-11-12 驗收後，第 1 片修正輪）

驗收結論為不通過（`studio_cli.py` 重複定義 `_say`，`tests/test_no_duplicate_defs.py` 必然失敗；ledger 寫成「shard 逾時」不實）。對抗審另有 9 項。以下為裁決，executor 照此修正，每項先寫會失敗的測試。

認可（不需改行為）：
- 單檔超過上限、路徑不安全、被上限截斷：結束碼 1。
- 設了 `ABF_PAT` 但沒有設定檔：結束碼 2。
- `studio_remote.py` 可 import `anyio`、`httpx2`（皆為 `mcp` 的相依，不新增相依，不改 `pyproject.toml`）。每次呼叫一個 MCP session 的 async 寫法認可。

必須修：
- R1 去掉 `studio_cli.py` 的重複 `_say`（用既有的輸出函式），不得用加白名單解決。更正 ledger 的不實說法。
- R2 `test_launch_static` 的例外改窄：不得整檔豁免，改成釘住每檔 `asyncio.sleep` 的次數（照同檔旁邊 abf_launch 的作法）。
- R3 `test_scope` TC-061：不得靠 import 拼字繞過。把 `studio_remote.py` 以檔名明列為例外並寫明原因，其餘檔案禁止 `httpx`、`httpx2` 與 mcp client 的 import（兩種拼字都要擋）。`studio_remote.py` 用一般寫法 import。
- R4 整個 `fetch-results` 要有一個總時限；`read_run_file` 回空頁卻給 `next_offset` 要拒絕；每檔頁數要有上限。
- R5 列目錄的次數要有上限（目錄數上限，超出要告知且結束碼 1）。
- R6 總量上限以實際讀到的位元組計；列表給的負數大小當 0。
- R7 單檔上限以 UTF-8 位元組計，不以字元計。
- R8 副檔名檢查要套在實際寫入的檔名（`download`）上，且 `download` 必須等於所在目錄加 `name`，不符則拒絕。
- R9 怪檔名（過長、孤立代理字元）、列表格式不對（列不是物件）：不得當掉印堆疊，要當成拒絕並給一句話，結束碼 1。
- R10 印到終端的所有伺服器來源文字（檔名、`reason`）要去掉控制字元（含 `\x80-\x9f`）；含這類字元的檔名不寫入。
- R11 平台說是 binary 的 `.tsv`／`.csv` 等表格檔：算問題，結束碼 1。同一個 `download` 出現兩次（含只差大小寫）：只抓一次並告知。
- R12 `http://` 迴路位址不走環境變數的 proxy。

不在本輪：Windows 上設定檔 ACL、`x.tsv:ads`／`con.tsv` 類檔名（目標是 RStudio 容器，另案）。

## 裁決（lead，2026-11-13，第 2 片驗收 ACCEPT 之後）

- `studio_cli.py` 的 `from .actions.figures import MAX_*`：接受（verifier 實測在乾淨環境載入不產生任何檔案、不開資料庫；TC-083 的放行範圍只限 `studio_cli`、`actions.figures`、`MAX_` 開頭的名稱）。executor 當時應先停手回報再做，這一點記錄在此。之後若要讓使用者端指令完全不載入動作層，另案把上限搬到只含常數的模組。
- 連線逾時的自動重試可能讓同一張圖被提出兩次；兩次都只是等本人確認的申請，不會重複寫入。記錄為已知行為。
- `cli.py` 的說明文字少列 `--params`、`--caption`：列入後續小修。
