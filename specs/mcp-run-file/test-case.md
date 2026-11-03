# 測試案例：MCP 讀取結果檔（mcp-run-file）

**規格**：`specs/mcp-run-file/plan.md`（本任務沒有獨立 spec.md，計畫即規格，維護者原話引在計畫「維護者原話」一節）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

名詞：「假站台」＝測試用的假站台代理與假結果檔夾具（照 `test_results_files.py`、`test_web_results_outputs.py` 的做法）；「jobs 列數」＝平台資料庫 `jobs` 表的列數（`SELECT COUNT(*) FROM jobs`），用來證明「有沒有排工作」；「MCP 客戶端」＝測試用 `call_tool` 呼叫工具；「動作層」＝`actions.*` 函式。除非另寫，自動測試都放在 `platform/tests/test_mcp_run_file.py`，並在測試註解寫明 TC 編號。

維護者原話對照（出題依據）：
- 原話 1「已經能用MCP從頭跑到下游分析跟取得最終分析檔了嗎?」→ TC-004、TC-040
- 原話 2「先讓「MCP 讀取／下載結果檔」在國網跑得動」→ TC-040、TC-041、TC-024
- 原話 3「跟Seqera platform一樣的模式，不要自己定義」→ TC-019、TC-029、TC-030、TC-032、TC-043

## User Story 1 — 在 MCP 逛結果資料夾（run_outputs 加 path）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1；測試「run_outputs(path="qiime2")」 | 功能 | 假站台有一個自己的 run，結果樹有 `qiime2/` 子資料夾且列表已回 | 用 MCP 客戶端呼叫 `run_outputs(run_id, path="qiime2")` | 回 `state: "ready"`、`sub == "qiime2"`；每一列的 `enter`／`download` 都是 `qiime2/…` 開頭的完整相對路徑（不是只有檔名） | 自動 |
| TC-002 | 作法 1；測試「路徑列表工作恰好 1 列」 | 功能 | 同上，但 `qiime2/` 還沒有列過 | 第一次呼叫 `run_outputs(run_id, path="qiime2")`，立刻再呼叫一次 | 第一次回 `state: "loading"` 且不等待；jobs 裡針對 `qiime2` 的列表工作恰好 1 列；第二次呼叫後仍是 1 列 | 自動 |
| TC-003 | 作法 1（不帶 path 與原本相同） | 功能 | 同 TC-001 | 呼叫 `run_outputs(run_id)`（不帶 path） | 回第一層：`sub` 為空、`bad_path` 為 False，內容與動作層 `actions.run_outputs(..., subpath=None)` 相同 | 自動 |
| TC-004 | 維護者原話 1；作法 1 | 功能 | 假站台有 run，第一層有資料夾 `qiime2`、其下有 `qiime2/table.tsv`（文字檔），所有答案都已就緒 | 只用 MCP 客戶端：①`run_outputs(run_id)` 取第一層的 `enter`；②把該 `enter` 原樣當 `path` 再呼叫 `run_outputs`；③把子層的 `download` 原樣當 `path` 呼叫 `read_run_file` | 三步都成功，最後拿到 `kind: "text"` 且 `text` 等於 `qiime2/table.tsv` 的原文；全程沒有用到 MCP 以外的工具，路徑都來自上一步的回答，不是測試自己拼的 | 自動 |
| TC-005 | 作法 1；測試「壞路徑」 | 例外 | 同 TC-001；jobs 列數先記下 | 對 `run_outputs` 分別帶 `../x`、`/etc/passwd`、`a/.hidden/b`、`a//b`、513 個字元的路徑、含控制字元（如 `a\nb`）的路徑 | 每一個都回第一層內容且 `bad_path: True`；jobs 沒有為這些壞路徑新增任何列表工作 | 自動 |
| TC-006 | 作法 1（計畫兩處說法不一，見總覽疑問 1） | 例外 | 同 TC-001；jobs 列數先記下 | 呼叫 `run_outputs(run_id, path="")`（空字串） | 回第一層內容；沒有為空字串另排任何列表工作（jobs 列數與「不帶 path」時相同）。`bad_path` 的值不在此檢查 | 自動 |
| TC-007 | 作法 1、3；測試「MCP 描述提到 path」 | 功能 | MCP 伺服器已建置 | 列出工具，讀 `run_outputs` 的描述與參數 | 參數含可選的 `path`；描述寫明：路徑不正確時列的是第一層並標 `bad_path`；仍是不等待，並提到 `loading`、`ready`、`error`、`unavailable` 四個狀態 | 自動 |
| TC-008 | 作法 4；測試「他人 run」 | 例外 | 兩位使用者 A、B；A 有 run；jobs 列數先記下 | 用 B 的 token 呼叫 `run_outputs(A 的 run_id, path="qiime2")`，再用 A 的 token 呼叫 `run_outputs("不存在的id", path="qiime2")` | 兩者都回 `found: False` 且是同一句話（`_OUTPUTS_NO_RUN`）；jobs 列數前後相同（沒有排工作） | 自動 |

## User Story 2 — 讀文字檔並分頁（read_run_file）（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-009 | 作法 2「文字檔」 | 功能 | 假站台答 `ready`，檔案 `qiime2/table.tsv` 為幾行 ASCII 的 TSV | 呼叫 `read_run_file(run_id, "qiime2/table.tsv")` | 回 `kind: "text"`、`name == "table.tsv"`、`size` 為位元組數、`total_chars` 為字元數、`offset == 0`、`text` 等於全文、`next_offset is None`；沒有 `message` | 自動 |
| TC-010 | 測試「文字分頁」第一頁；作法 2 | 功能 | 檔案為 200,000×2+17 個 ASCII 字元的 TSV，答案已就緒 | 呼叫 `read_run_file(run_id, path)`（offset 預設 0） | `len(text) == 200000`、`next_offset == 200000`、`total_chars == 400017`；有 `message`，內容指示「下一次帶 offset=200000」 | 自動 |
| TC-011 | 測試「文字分頁」第二頁 | 功能 | 同 TC-010 | 用上一頁的 `next_offset` 當 `offset` 再呼叫 | `len(text) == 200000`、`offset == 200000`、`next_offset == 400000`、有 `message` | 自動 |
| TC-012 | 測試「文字分頁」第三頁與串接 | 功能 | 同 TC-010 | 用第二頁的 `next_offset` 再呼叫 | `len(text) == 17`、`next_offset is None`、沒有「還有內容」的 `message`；三頁 `text` 依序串起來完全等於原文 | 自動 |
| TC-013 | 測試「剛好 200,000 字元」 | 功能 | 檔案剛好 200,000 個 ASCII 字元 | 呼叫 `read_run_file(run_id, path)` | 一頁讀完：`len(text) == 200000`、`next_offset is None`、`total_chars == 200000` | 自動 |
| TC-014 | 作法 2「offset == total_chars」；裁決 8 | 功能 | ①檔案 10 個字元；②空檔（0 位元組） | ①帶 `offset=10`；②帶 `offset=0` | 兩者都是 `state: "ready"`、`kind: "text"`、`text == ""`、`next_offset is None`（空檔不被當成二進位） | 自動 |
| TC-015 | 作法 2、裁決 8 | 例外 | 檔案 10 個字元，答案已就緒 | 帶 `offset=11` | 回 `state: "error"`、`code: "bad_offset"`，並帶出總長（`total_chars == 10`）；沒有 `text` | 自動 |
| TC-016 | 作法 2「offset 不是 ≥ 0 的整數」 | 例外 | 同 TC-015 | 分別帶 `offset=-1`、`offset="10"`、`offset=1.5` | 每一個都回 `state: "error"`、`code: "bad_offset"`，沒有 `text` | 自動 |
| TC-017 | 測試「多位元組」；作法 2「單位是字元」 | 功能 | 檔案全由「分」「μ」「😀」混合組成，字元數大於 200,000 兩頁以上，位元組長度遠大於字元長度；答案已就緒 | 依 `next_offset` 一頁一頁讀完 | `total_chars` 是字元數且小於 `size`；除最後一頁外每頁 `len(text) == 200000`；每頁都能獨立 `encode("utf-8")` 成功；所有頁串起來等於原文；任何一頁都沒有 U+FFFD | 自動 |
| TC-018 | 作法 2「同一檔案分頁讀只排一次工作」 | 功能 | 假站台尚未被問過這個檔；jobs 列數先記下 | 先讀（loading，再讓假站台答），之後連讀第一、二、三頁 | jobs 裡 `read_run_file` 列恰好新增 1 列，三頁都從同一個答案（快取）取得 | 自動 |
| TC-019 | 測試「載入中不阻塞」；維護者原話 3「不等待」 | 功能 | 檔案尚未被問過；把程式裡的睡眠／等待函式換成一碰就失敗的假函式；jobs 列數先記下 | 第一次呼叫 `read_run_file`，立刻再呼叫一次 | 第一次回 `state: "loading"` 與 `message`（含「站台正在讀這個檔案，請幾秒後再問一次」與 "ask again in a few seconds"），沒有觸發假函式（沒有等待），jobs 恰好新增 1 列 `read_run_file`；第二次也回 `loading`，列數不再增加 | 自動 |

## User Story 3 — 二進位、太大與讀不到的檔案（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 作法 2「非文字檔」；裁決 7 | 功能 | 假站台答 `ready`，檔案內容含 `\x00`（但其餘可解成 UTF-8） | 呼叫 `read_run_file` | 回 `kind: "binary"`、有 `name`、`size`、`download_url`，`note` 為「這是二進位檔，內容不經由 MCP 傳給模型 (binary file; its bytes are not sent through MCP)」；回應裡**沒有** `text`、`b64`、`data`，也找不到原位元組 | 自動 |
| TC-021 | 測試「二進位」；裁決 7 | 功能 | 檔案是 gzip 開頭位元組 `\x1f\x8b…`（不合法 UTF-8） | 呼叫 `read_run_file` | 同 TC-020：`kind: "binary"`，沒有 `text`／`b64`／原位元組 | 自動 |
| TC-022 | 作法 2「download_url」；裁決 9 | 功能 | 二進位檔 `qiime2/表 a.qza`；設定了 `web_base_url="https://abf.example.org/"`（尾端有 `/`）；另一個情境未設定 | 呼叫 `read_run_file(run_id, "qiime2/表 a.qza")` | 設定時：`download_url` 以 `https://abf.example.org`（尾端 `/` 已去掉，不出現 `//run`）開頭，接著 `/run/file?run=<id>&path=`，後面的 path 已做 URL 編碼；未設定時以 `DEFAULT_WEB_BASE` 開頭，其餘相同 | 自動 |
| TC-023 | 計畫「不做」：> 25 MB 的檔；作法 2「too_large」 | 不在範圍 | 站台答 `too_large` 與 `size = 26214401`；run 資料夾為 `<run_folder>` | 呼叫 `read_run_file(run_id, "big/table.tsv")` | 回 `state: "too_large"`、`size == 26214401`、`site_path == "<run_folder>/results/big/table.tsv"`、`max_bytes == 26214400`；沒有 `text`／`b64`／位元組，也沒有假裝讀到內容 | 自動 |
| TC-024 | 計畫「不做」：雲端 CE 的讀取；維護者原話 2 | 不在範圍 | 該 run 的環境是雲端（結果不在站台主機）；jobs 列數先記下 | 呼叫 `read_run_file` | 回 `state: "unavailable"`、`code: "not_on_site"`，`message` 與 results-files 的拒絕句是同一個常數（`jobs.RUN_FILE_NOT_ON_SITE`，逐字相等）；沒有排工作 | 自動 |
| TC-025 | 作法 2「unavailable / no_launch」 | 例外 | run 不是從平台送出（沒有送出紀錄） | 呼叫 `read_run_file` | 回 `state: "unavailable"`、`code: "no_launch"`，附白話說明；沒有排工作 | 自動 |
| TC-026 | 作法 2「error」錯誤碼 | 例外 | 假站台依序讓同一個流程回 `agent_offline`、`refused`、`no_answer`、`not_found`、`not_a_file`、`site_unreachable`、`changed`、`bad_answer`、`failed` | 每種各呼叫 `read_run_file` 一次 | 每一種都回 `state: "error"`、`code` 等於該碼，且有非空的白話 `reason`；`reason` 不含堆疊（Traceback）、SQL，也不含站台路徑以外的內部路徑 | 自動 |
| TC-027 | 作法 2「bad_path」；測試「壞路徑」 | 例外 | 自己的 run；jobs 列數先記下 | 對 `read_run_file` 分別帶 `../x`、`/etc/passwd`、`a/.hidden/b`、空字串、`a//b`、513 個字元、含控制字元的路徑 | 每一個都回 `state: "error"`、`code: "bad_path"`；在排工作之前就拒絕：jobs 列數不變 | 自動 |
| TC-028 | 計畫「不做」：MCP 內嵌圖片；不支援以位元組 range 取二進位檔 | 不在範圍 | 檔案為 PNG（開頭 `\x89PNG`，不合法 UTF-8），答案已就緒 | ①呼叫 `read_run_file(run_id, "plots/a.png")`；②同一檔再帶 `offset=5` 呼叫 | 兩次都回 `kind: "binary"` 加名稱、大小、說明與網址；沒有圖片內容、沒有位元組、沒有任何位元組範圍欄位；回應也沒有內嵌 MultiQC／圖片的欄位 | 自動 |

## User Story 4 — 擁有者、只讀、不等待與工具註冊（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 作法 4；維護者原話 3「他人 run 與不存在同一句」 | 例外 | 兩位使用者 A、B；A 有 run；jobs 列數先記下 | 用 B 的 token 對 A 的 run 呼叫 `read_run_file`；再用 A 的 token 對不存在的 id 呼叫；兩邊（MCP 客戶端與動作層）各做一次 | 兩者都回 `found: False`，且是與 `run_outputs` 同一句；jobs 列數前後相同 | 自動 |
| TC-030 | 作法 3；測試「對等與註冊」 | 功能 | MCP 伺服器已建置 | 列出工具；列出 `READ_NAMES` 與動作層函式；跑 AST 檢查（沿用 `test_tca13`）；讀 `test_web_parity.py` 的 `WEB_ROUTES` | 工具名單含 `read_run_file` 且標唯讀（`read_only_hint`）；存在同名 `actions.read_run_file`；工具函式本體只有一個呼叫進 actions；`WEB_ROUTES["read_run_file"]` 為 `GET /run/file?run=<id>&path=<p> (the download; results-files)`；`_READ_ONLY` 工具數為 16 | 自動 |
| TC-031 | 作法 3；測試「描述」 | 功能 | 同 TC-030 | 讀 `read_run_file` 的工具描述 | 描述含 "the text goes to the model you chose"、"200,000"、"next_offset"、"/run/file"、"25 MB"；並寫到只讀且只限自己的 run、不等待與 loading／ready／error／unavailable／too_large（帶大小與完整站台路徑）、二進位只回名稱大小說明與網址、`path` 是 `results/` 之下相對路徑且由 `run_outputs` 取得 | 自動 |
| TC-032 | 作法 4「工具不帶任何可說『是』或選工作種類的參數」；維護者原話 3 | 功能 | 同 TC-030 | 讀 `read_run_file` 的參數結構 | 參數恰好是 `run_id`、`path`、`offset`（`offset` 預設 0）；沒有 confirm／yes／kind／retry 之類參數；呼叫後 jobs 裡新增的工作種類只可能是 `read_run_file` | 自動 |
| TC-033 | 測試「透過 MCP 客戶端 call_tool 與 actions.* 兩邊各驗」 | 功能 | 一個就緒的文字檔與一個二進位檔 | 各用 MCP 客戶端與 `actions.read_run_file` 呼叫一次 | 兩邊的內容欄位（`kind`、`name`、`size`、`text`、`next_offset`、`download_url`）相同 | 自動 |
| TC-034 | 專長守則：錯誤訊息與日誌不含密鑰；作法 2「全部輸出先過 json.dumps」 | 例外 | 在 TC-009 到 TC-029 的情境中，帶一個可辨認的假 token／密鑰；收集所有回應與日誌 | 對每一種回答（loading／ready 文字／ready 二進位／too_large／unavailable／error／found False）做 `json.dumps`，並用既有洩漏掃描夾具掃回應與日誌 | 每一種都能序列化；回應與日誌都不含 token 或密鑰；也不含站台路徑以外的內部路徑 | 自動 |
| TC-035 | 計畫「不做」：寫到使用者電腦、zip／整包下載、RStudio／Jupyter | 不在範圍 | MCP 伺服器已建置 | 列出全部工具，與本任務前的工具名單比對 | 唯一新增的工具是 `read_run_file`（工具總數 20→21）；沒有任何寫檔、打包、zip、studio 的工具或參數；`read_run_file` 與 `run_outputs` 沒有「存到本機」的路徑參數 | 自動 |

## User Story 5 — downstream 提示詞與文件（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-036 | 作法 5；測試「downstream 提示詞內文含 read_run_file 與 run_outputs」 | 功能 | 取得 `downstream` MCP 提示詞內文（等於 `skills/downstream/SKILL.md`） | 讀內文 | 含 `read_run_file` 與 `run_outputs`，並寫明：用 `run_outputs(run_id)` 看第一層、用 `enter` 給的子路徑逐層進入；文字檔一次最多 200,000 字元、被截斷依 `next_offset` 續讀；`loading` 就幾秒後再問同一個呼叫；`too_large` 或二進位檔給使用者網頁下載網址、不假裝讀到；內容會送到使用者選定的模型，先對使用者說一句；沒有終端機時 ≤ 25 MB 的表格靠 MCP 取得，更大的照原本站台端流程 | 自動 |
| TC-037 | 作法 5「加法」；憲法 6 | 功能 | 取得 SKILL.md 的新舊兩版 | 比對新舊版；跑 `tests/no_per_pipeline_config.sh` 與 `test_guidance` | 舊版每一行（`fetch.sh`、`inventory_outputs.py` 的終端機路線）原文都還在，只有新增；新增的句子不含特定管線或工具字樣（如 multiqc、qiime2）、不含排程器或站台名稱；兩個檢查都綠；`platform/abf_platform/skills/` 若為建置產物則未被追蹤 | 自動：`tests/no_per_pipeline_config.sh`、`platform/tests/test_guidance.py` |
| TC-038 | 計畫「被釘住的既有測試（只准加不准刪）」 | 功能 | 計畫列出的既有測試檔 | 跑這些測試檔，並比對它們與 base 的差異 | 全綠；與 base 相比只有計畫允許的改動（名單加入 `read_run_file`、數量 20→21、15→16、`NUMBERS` 加 `"sixteen": 16`、原本拿 16 當負面案例的改拿 17、`BASELINE` 的 `run_outputs` 換新 schema）；沒有被刪除、放鬆或跳過的斷言；`test_su_usd.py` 與 `test_pat.py:752` 已跑過並在 ledger 說明 | 自動：計畫所列各測試檔 |
| TC-039 | 計畫範圍「`docs/PLATFORM.md`、`docs/TESTING.md`」 | 功能 | 兩份文件 | 讀文件 | `docs/PLATFORM.md` MCP 一節含 `read_run_file` 與 `run_outputs(path)`，工具數量與唯讀清單與程式一致（16 個唯讀）；`docs/TESTING.md` 末尾有「MCP 讀結果檔 (mcp-run-file)」一節，含計畫的 5 個手動步驟，每步寫得出要做什麼、看到什麼才算通過 | 手動：`docs/TESTING.md` |

## User Story 6 — 在國網（nano4）真實跑一次（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 維護者原話 1、2；計畫手動步驟 (1)(2)(3) | 功能 | 維護者的 Claude Desktop 已連上平台；nano4 的 run `ampliseq_day5_nano4_r5`（已成功）；站台代理在線 | ①`run_outputs(run_id)`；②`run_outputs(run_id, path="qiime2")`，必要時再往下一層；③`read_run_file` 讀一個 feature table（TSV）與 `multiqc/multiqc_data/multiqc_general_stats.txt`（第一次若回 loading，幾秒後再問同一個呼叫） | 看到第一層與子資料夾的檔案列；讀到表頭與資料列；檔案大於一頁時帶 `next_offset`，續讀成功 | 手動：`docs/TESTING.md`「MCP 讀結果檔 (mcp-run-file)」 |
| TC-041 | 維護者原話 2；計畫手動步驟 (4) | 功能 | 同 TC-040；挑一個 `.qza` 之類的二進位檔（`.html` 是合法 UTF-8 文字，依規則會被當文字檔讀，不用它測二進位） | 對該檔呼叫 `read_run_file` | 得到說明與 `/run/file?...` 網址，而不是亂碼；網址在瀏覽器登入平台後可下載 | 手動：`docs/TESTING.md` |
| TC-042 | 計畫手動步驟 (5)；維護者原話 3 | 例外 | 另一個帳號的 token | 對同一個 run 呼叫 `read_run_file` 與 `run_outputs(path=…)` | 得到「找不到」，與 run 不存在時同一句；沒有任何檔案內容或檔名洩漏 | 手動：`docs/TESTING.md` |

## 憲法與安全網

本任務觸及：原則 I（第 1、2 條：不新增送出路徑、不留第二份 run 狀態）、原則 II（第 3 條：不寫死路徑）。第 4、6 條（站台中立、不寫特定管線）由 TC-037 證明。第 9 條（不假裝讀到）由 TC-020、TC-023、TC-036 證明。本任務不碰 `hooks/`，安全網（Safety Net）各條不受影響。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-043 | 第 1、2 條；計畫「不做」：改站台代理、jobs 種類、遷移、web 路由、STYLE、CSP | 不在範圍 | 本任務前後的程式 | 比對 jobs 允許的工作種類集合，並看 `git diff <base>...HEAD` 動到的檔案 | 工作種類集合與 base 完全相同（沒有新種類）；沒有任何新的送出（launch）路徑；沒有動 `abf_station/`、`jobs.py`、`store.py`、遷移檔、`web.py`、STYLE、CSP；`tests/no_second_run_state_test.sh` 綠 | 自動：`tests/no_second_run_state_test.sh`；驗收時由 verifier 讀 diff |
| TC-044 | 第 3 條 | 功能 | 本任務新增或修改的所有檔案 | 跑 `tests/no_hardcoded_paths.sh`，並搜尋新增內容 | 沒有個人路徑、叢集路徑（如 `/work/<帳號>`、`/home/…`、`C:\Users\…`）；站台路徑只由 run 的 `run_folder` 組出，不寫在程式或文件範例裡 | 自動：`tests/no_hardcoded_paths.sh` |
