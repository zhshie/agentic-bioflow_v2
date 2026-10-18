# 測試案例：docs/OPERATIONS.md —— 營運者手冊（issue #119 第 4 項）

<!--
Written by the verifier (CONTRACT mode, 2026-10-18) from specs/ops-doc/plan.md and the constitution.
There is no spec.md for this task; the plan is the only source, and it quotes no sentence of the
maintainer's. The plan says "the test cases must come from the examples in the plan", so every case
below is taken from a sentence of the plan. Nothing is invented beyond what the plan states.
Reader: the maintainer, who is not an engineer.
-->

**規格**：`specs/ops-doc/plan.md`（無 spec.md；計畫即來源）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：缺東西、文件寫錯、使用者做了不該做的事時，文件或測試怎麼反應（拒絕、標明「尚未建好」）。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做。

驗證方式說明：「自動」是 `tests/` 底下的測試腳本（含驗收者在暫存複本上竄改文件、確認測試會變紅）。「手動」在這個變更裡是「驗收者逐項讀文件、對照 `platform/abf_platform/` 的原始碼或 `git diff`」，因為計畫的測試只管三件事（標題、指令名、路徑），管不到內容是否屬實；本變更是純文件，不新增 `docs/TESTING.md` 的步驟。

## User Story 1 — 營運者讀一份文件，就知道平台現在怎麼跑、備份什麼、用哪些管理指令（優先度 P1）

這份文件寫給「替實驗室架平台的人」。它只描述 v3 分支上**現在存在**的東西；還沒蓋好的東西只能出現在最後一節「Not built yet」，不能被寫成已經可用。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「Content」：六個章節；「Test」第 1 點 | 功能 | 實作完成 | 打開 `docs/OPERATIONS.md`，列出所有二級標題（`## `） | 檔案存在；有六個二級標題，順序為：(1) 各個程序 (2) 一個主機名稱＋TLS (3) 保持運作 (4) 備份什麼 (5) 管理指令 (6) `Not built yet`；最後一個標題的文字含 `Not built yet` | 自動：`tests/operations_doc_test.sh` |
| TC-002 | 計畫 Content 1 | 功能 | 同上 | 讀第 1 節 | 三個程序都點名並各用一兩句說明它做什麼：`abf-platform serve`（收 Nextflow 回報與 agent 請求）、MCP 伺服器（`abf-platform mcp --http`）、`abf-platform web`（確認頁）；說法與 `platform/abf_platform/cli.py` 的 help 字串一致 | 手動：驗收者對照 `cli.py` 的 `add_parser("serve"/"mcp"/"web")` |
| TC-003 | 計畫 Content 1：「default bind address/port」 | 功能 | 同上 | 讀第 1 節的預設位址 | 寫出三個預設：`serve` 為 127.0.0.1:8787、`mcp --http` 為 127.0.0.1:8788、`web` 為 127.0.0.1:8789；與 `cli.py` 的 `default=` 一字不差 | 手動：驗收者對照 `cli.py` |
| TC-004 | 計畫 Content 1：「they are separate processes」 | 功能 | 同上 | 讀第 1 節 | 明白寫出這三個是各自獨立的程序（要分別啟動、分別重啟），不是一個程式的三個功能 | 手動：驗收者讀文件 |
| TC-005 | 計畫 Content 1（bind address）；`cli.py` 的 `web --host` 說明 | 例外 | 營運者想把 `web` 直接開到區網 | 讀第 1 節對 `web` 的位址說明 | 文件不得說 `web` 能直接綁非本機位址；若提到 `--host`，只能說明「只接受本機位址（127.0.0.1、::1、localhost），其他位址被拒絕，要靠前面的代理」 | 手動：驗收者對照 `cli.py` 的 `wb.add_argument("--host"...)` 與 `docs/PLATFORM.md` 的對應句 |
| TC-006 | 計畫 Content 2 | 功能 | 同上 | 讀第 2 節 | 把「三個程序前面放同一個主機名稱，TLS 由 Tailscale Funnel 提供」寫成**已選定的做法**，並註明 2026-10-17 議定；不寫成「可考慮」或「選項」 | 手動：驗收者讀文件 |
| TC-007 | 計畫 Content 2：「mark the actual config snippet 'Not built yet' if no file in the repo implements it」 | 例外 | 倉庫裡沒有任何檔案實作 Funnel／代理設定（驗收者以 `grep -ri tailscale` 確認只有 ADR 0010 與 `cli.py` 的說明字串） | 找第 2 節裡的設定片段 | 實際的 Funnel／代理設定片段若出現，必須明標 `Not built yet`，且同樣列在第 6 節；不得有一段沒標示、看起來「複製就能用」的設定。文件可以引用已存在的旗標（如 `abf-platform web --public-url`） | 手動：驗收者讀文件並 grep 倉庫 |
| TC-008 | 計畫 Content 3 | 功能 | 同上 | 讀第 3 節 | 以 systemd 使用者單元（user units）為例說明如何讓三個程序保持運作；每一段範例都清楚標成「範例／example」；文件不宣稱倉庫內附有這些單元檔 | 手動：驗收者讀文件並確認倉庫內無對應檔案 |
| TC-009 | 計畫 Content 4：「Name real file names/paths from the code」 | 功能 | 同上 | 讀第 4 節 | 點名平台的三個資料庫檔：`index.db`、`tokens.db`、`platform.db`；寫出預設位置（`ABF_PLATFORM_DB` 未設時為 `${XDG_DATA_HOME:-~/.local/share}/abf-platform/`，另兩個在其旁）與覆寫用的環境變數 `ABF_PLATFORM_DB`、`ABF_PLATFORM_TOKENS`、`ABF_PLATFORM_STATE`；全部與 `store.py` 一致 | 手動：驗收者對照 `store.py` 的 `default_index_path`／`default_tokens_path`／`default_platform_path` |
| TC-010 | 計畫 Content 4：「the run index is [rebuildable], via `rebuild`」 | 功能 | 同上 | 讀第 4 節對 `index.db` 的說明 | 寫明 `index.db` 可重建、不必備份，重建指令是 `abf-platform rebuild`；並說明重建的來源是 Nextflow 自己的紀錄 | 手動：驗收者對照 `rebuild.py`、`cli.py` 的 `cmd_rebuild` |
| TC-011 | 計畫 Content 4：「tokens, users, OAuth, confirmations...」必須備份 | 功能 | 同上 | 讀第 4 節對 `tokens.db`、`platform.db` 的說明 | 兩個檔都標為「必須備份、無法重建」，並寫出裡面有什麼：`tokens.db`（存取權杖的雜湊、使用者、網頁密碼雜湊、OAuth 登入）、`platform.db`（運算環境、agent、工作佇列、確認紀錄、交接紀錄）；內容與 `store.py`／`oauth.py` 的資料表一致 | 手動：驗收者對照 `store.py` 的 `CREATE TABLE` |
| TC-012 | 計畫 Content 4：「list **every** database/file the platform writes (read store.py, oauth.py, http_auth.py, records.py, rebuild.py)」 | 功能 | 同上 | 比對第 4 節與程式碼實際寫出的檔案 | 除三個資料庫外，另外寫到的也都點名並各自分類為「可重建」或「必須備份」：網頁簽章金鑰 `web_signing.key`（`web.py`，放在資料庫旁）、samplesheet 上傳資料夾 `uploads`（`store.uploads_root`，`ABF_PLATFORM_UPLOADS`）、取回的 Nextflow 紀錄資料夾 `records/`（`records.py`，`rebuild` 會讀它）。驗收者另 grep 這五支原始檔有無其他寫檔點，有則文件也要列 | 手動：驗收者對照 `web.py`、`store.py`、`records.py` |
| TC-013 | 計畫 Content 5：子指令表 | 功能 | 同上 | 讀第 5 節的表 | 表中有這幾組指令各一列或多列：`token`、`agent-token`、`user add`／`user passwd`、`pat new`／`pat list`／`pat revoke`、`oauth revoke`、`ce ...`（`ce` 可概括為一列，但列出的子指令必須真實存在） | 手動：驗收者對照 `cli.py` 的 `add_parser` |
| TC-014 | 計畫 Content 5：「one line each, taken from the argparse help strings」 | 功能 | 同上 | 逐列比對表中說明與 `cli.py` 的 `help=` | 每列一行說明，意思與該指令的 argparse help 相符，沒有誇大或寫錯（例：`pat list` 寫「列出權杖，不顯示值」；`oauth revoke` 寫「結束該使用者所有 OAuth 登入，其個人存取權杖仍在」；`user passwd` 寫「在終端機設定登入確認頁用的密碼」） | 手動：驗收者對照 `cli.py` 第 502–570 行 |
| TC-015 | 計畫 Content 6 與開頭：「anything not built yet is listed in a final 'Not built yet' section」 | 功能 | 同上 | 讀最後一節 | 第 6 節存在且是最後一節，列出尚未建好的項目，至少包含第 2 節的 Funnel／代理設定片段（TC-007）；第 3 節若有 systemd 範例，也在此註明「倉庫未附單元檔」；每項都寫成「尚未建好」，不寫成已可用 | 手動：驗收者讀文件 |
| TC-016 | 計畫開頭：「It describes what exists on branch v3 today, not plans」 | 例外 | 同上 | 通讀第 1 至 5 節，找「還沒做好卻寫成能用」的句子 | 第 1–5 節找不到任何尚未存在的東西被描述成可用（例如倉庫未附的單元檔、未實作的代理設定、尚無指令的功能）；有的話必須搬到第 6 節 | 手動：驗收者通讀並對照原始碼 |

## User Story 2 — 測試把關：文件不能點名不存在的指令或檔案（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 計畫 Test：「picked up by tests/run_all.sh like the other *_test.sh」 | 功能 | 實作完成 | 執行 `bash tests/run_all.sh --list` | 輸出清單含 `operations_doc_test.sh`；檔案位於 `tests/`，風格比照 `tests/platform_direction_docs_test.sh`（逐項印 `ok`／`FAIL`，失敗時非零結束） | 自動：`tests/operations_doc_test.sh` |
| TC-018 | 計畫 Test：「write first, must fail before the doc exists」 | 例外 | 在暫存複本中沒有 `docs/OPERATIONS.md` | 執行 `bash tests/operations_doc_test.sh` | 非零結束，並印出至少一行 `FAIL`（指出檔案不存在）；git 歷史中測試的提交早於文件的提交 | 自動：`tests/operations_doc_test.sh`（驗收者在無文件的複本上執行並查提交順序） |
| TC-019 | 計畫 Test | 功能 | 文件完成 | 執行 `bash tests/operations_doc_test.sh` | 零結束，所有項目 `ok`，沒有 `FAIL` | 自動：`tests/operations_doc_test.sh` |
| TC-020 | 計畫 Test 第 1 點：「has the six section headings」 | 例外 | 在暫存複本中刪掉文件的一個二級標題（例如 `Not built yet`） | 執行 `bash tests/operations_doc_test.sh` | 非零結束，`FAIL` 行點名缺的標題 | 自動：`tests/operations_doc_test.sh`（驗收者在暫存複本竄改後執行） |
| TC-021 | 計畫 Test 第 2 點：「every `abf-platform <subcommand>` named in the doc exists」 | 例外 | 在暫存複本的文件裡加一行 `` `abf-platform frobnicate` ``（`cli.py` 沒有這個子指令） | 執行 `bash tests/operations_doc_test.sh` | 非零結束，`FAIL` 行點名 `frobnicate`；文件本來就有的真子指令不受影響 | 自動：`tests/operations_doc_test.sh`（驗收者在暫存複本竄改後執行） |
| TC-022 | 計畫 Test 第 2 點（「parse the add_parser names」） | 功能 | 文件的第 5 節點名了真實存在的各種子指令，包括巢狀的（`pat new`、`oauth revoke`）與 `cli.py` 以迴圈而非字面 `add_parser("...")` 建立的（`ce primary`、`ce disable`、`ce enable`） | 執行測試 | 全部通過，不因為「解析不到字面名稱」而誤判成不存在；測試對每個 `abf-platform` 後的第一個字都以 `cli.py` 的頂層子指令核對 | 自動：`tests/operations_doc_test.sh` |
| TC-023 | 計畫 Test 第 3 點：「every repo path written in backticks … exists」 | 例外 | 在暫存複本的文件裡加一行 `` `docs/NOPE.md` ``（倉庫沒有） | 執行測試 | 非零結束，`FAIL` 行點名 `docs/NOPE.md` | 自動：`tests/operations_doc_test.sh`（驗收者在暫存複本竄改後執行） |
| TC-024 | 計畫 Test 第 3 點（「looks like a repo file」）與 Content 4（要寫真實的執行期路徑） | 功能 | 文件含 `` `platform/abf_platform/cli.py` `` 這類倉庫檔案，也含 `` `~/.local/share/abf-platform/index.db` ``、`` `index.db` ``、`` `web_signing.key` `` 這類執行期位置 | 執行測試 | 以倉庫頂層目錄（`docs/`、`platform/`、`tests/`、`scripts/`、`skills/`、`hooks/`、`specs/`、`configs/`、`extensions/`）開頭且含副檔名的路徑才逐一核對是否存在；以 `~`、`$`、`/` 開頭或沒有斜線的執行期位置不被當成倉庫檔案而誤判失敗 | 自動：`tests/operations_doc_test.sh` |

## 不在範圍

計畫的「Out of scope」：不改程式碼；不改 `CHANGELOG.md`、`docs/PLATFORM.md`、`ROADMAP.md`（另一條線在改 PLATFORM.md）；不加新相依。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 計畫 Out of scope：「No code changes」 | 不在範圍 | 實作完成 | `git diff --stat main...HEAD`（含未提交的 `git diff`） | 變更的檔案只有 `docs/OPERATIONS.md`、`tests/operations_doc_test.sh` 與 `specs/ops-doc/` 底下的檔案；`platform/`、`scripts/`、`hooks/`、`skills/`、`commands/` 底下沒有任何變更 | 手動：驗收者執行 `git diff --stat` |
| TC-026 | 計畫 Out of scope：不改 CHANGELOG.md、docs/PLATFORM.md、ROADMAP.md | 不在範圍 | 同上 | `git diff --stat main...HEAD -- CHANGELOG.md docs/PLATFORM.md docs/ROADMAP.md` | 三個檔案都沒有任何差異 | 手動：驗收者執行 `git diff` |
| TC-027 | 計畫 Out of scope：「No new dependencies」 | 不在範圍 | 同上 | 檢查 `platform/pyproject.toml`、`platform/constraints.txt`、`platform/setup.py` 的差異，並看新測試用到的工具 | 三個檔案無差異；新測試只用 `tests/` 其他測試已在用的 bash、grep、awk、sed 等，沒有新增安裝需求 | 手動：驗收者執行 `git diff` 並讀測試檔 |
| TC-028 | 計畫 Content 2、3 與 Out of scope（純文件） | 不在範圍 | 同上 | 檢查差異是否新增 Funnel／代理設定檔或 systemd 單元檔（`*.service`、`*.timer`、含 `tailscale` 的設定檔） | 沒有新增任何這類檔案；它們只以「範例」或「Not built yet」出現在文件裡，沒有被悄悄實作 | 手動：驗收者執行 `git diff --stat` 並 grep |

## 憲法與安全網

這份文件只是說明，不改行為，但它講到三件憲法管的事：執行索引的地位、憑證、路徑。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-029 | 原則 I.2（Nextflow 自己的紀錄才是真相；不存第二份執行狀態） | 功能 | 文件完成 | 讀第 4 節對 `index.db` 與「重建」的描述 | 把 `index.db` 稱為「索引」，真相是 Nextflow 的紀錄；不稱它為執行狀態的來源，也不建議把它當作需保存的資料；與 `store.py` 檔頭「It is an index, not the truth」一致 | 手動：驗收者讀文件對照 `store.py:4` 與 `.specify/memory/constitution.md` 原則 2 |
| TC-030 | 安全網「憑證」條：憑證不得被印出、不進 git | 功能 | 文件完成 | 搜尋文件裡的權杖、密碼、passphrase | 沒有任何真實權杖或密碼；範例只用佔位符（如 `abf_...`、`<token>`）；提到權杖時說明「只顯示一次，平台只存雜湊」，且網頁登入密碼只在終端機設定 | 手動：驗收者 grep 文件，對照 `docs/PLATFORM.md` 第 2 節 |
| TC-031 | 原則 II.3（不寫個人路徑、叢集路徑） | 功能 | 文件完成 | 以 `tests/no_hardcoded_paths.sh` 的樣式 `(/home\|/work\|/scratch\|/staging\|/lustre)/[A-Za-z][A-Za-z0-9_.-]*/` 搜尋 `docs/OPERATIONS.md` | 無任何命中（該測試本身不掃 `docs/`，故由驗收者手動掃）；systemd 範例用 `%h` 或 `<尖括號佔位符>`，不寫某人的家目錄 | 手動：驗收者執行 grep |
| TC-032 | 開發流程「每階段 `bash tests/run_all.sh` 全綠」 | 功能 | 實作完成 | 在 WSL／Linux 或看 CI 結果：`bash tests/run_all.sh` | 全部通過，含新的 `operations_doc_test.sh`；既有釘住文件字句的測試（如 `tests/platform_direction_docs_test.sh`）不因新檔而失敗 | 自動：`tests/run_all.sh`（CI 結果或 WSL） |
