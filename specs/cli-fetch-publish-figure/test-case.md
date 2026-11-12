# 測試案例：cli-fetch-publish-figure

**規格**：`specs/cli-fetch-publish-figure/plan.md`（含 2026-11-12 晚裁決）　**總覽**：`test-case-overview.md`

類型只有三種：功能（做到了）、例外（出錯時怎麼反應）、不在範圍（明講不做，測試確認沒做）。
「對應需求」欄開頭的【片1】【片2】表示交付片；片 1 的驗收不得因片 2 未做而失敗。
「替身」指測試用的假答覆（不連網路）；「真伺服器」指測試自己啟動的 `abf-platform mcp --http`。測試檔：`platform/tests/test_studio_remote.py`（連線與設定）、`platform/tests/test_studio_cli.py`（指令）、`platform/tests/test_web_downstream.py`（下游頁），各案例依序命名其 TC 編號於註解。

## US1 — studio-connect：存下平台網址與自己的權杖（優先度 P1，片1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 【片1】作法 2；原話 6 | 功能 | 一台沒有平台的電腦；`ABF_STUDIO_CONFIG` 指向暫存資料夾；替身伺服器接受該權杖 | 執行 `studio-connect --server https://主機`，權杖用隱藏輸入給；另一次用 `--token-stdin` 給 | 兩次都在設定檔寫入 `{"server": …, "token": …}`；畫面只印網址與「權杖已存入 <路徑>」；沒設 `ABF_STUDIO_CONFIG` 時預設存 `~/.abf/studio.json` | 自動：`test_studio_remote.py` |
| TC-002 | 【片1】作法 2 | 例外 | 無 | 執行 `studio-connect --server https://主機 --token abf_pat_FAKE123` | 指令列沒有 `--token` 旗標：被拒絕、不存檔；stdout／stderr 都不含 `abf_pat_FAKE123`；argparse 的選項清單中沒有 `--token` | 自動：`test_studio_remote.py` |
| TC-003 | 【片1】作法 2（https 檢查） | 例外 | 無 | `--server` 依序給 `http://example.com`、`https://主機/mcp`（有路徑）、`ftp://主機`、`https://`（無主機） | 四者都被拒絕並說明「要 https://主機、不含路徑」；不連線、不存檔；結束碼非 0 | 自動：`test_studio_remote.py` |
| TC-004 | 【片1】作法 2 | 功能 | 無 | `--server http://127.0.0.1:8080` 與 `--server http://localhost:8080` 加 `--no-check` | 兩者都被接受並存檔（唯一允許的 http 例外） | 自動：`test_studio_remote.py` |
| TC-005 | 【片1】作法 2 | 例外 | 設定檔已有舊內容 | 分別用：真伺服器＋錯誤權杖（401）、已關閉的埠，執行 `studio-connect`（不加 `--no-check`） | 兩次都不存檔、舊設定檔位元組不變；結束碼 3；訊息各為 TC-040、TC-041 的句子 | 自動：`test_studio_remote.py` |
| TC-006 | 【片1】作法 2 | 功能 | 沒有網路 | `studio-connect --server https://主機 --no-check` | 不發出任何連線就存檔成功，並印出權杖已存入的句子 | 自動：`test_studio_remote.py` |
| TC-007 | 【片1】作法 2；憲法「憑證只在擁有者可讀之處」 | 功能 | POSIX（Windows 跳過並註明） | 執行 `studio-connect` 後看設定檔與其資料夾；另在寫入中途讓替換失敗 | 檔案權限為 0600、資料夾 0700；寫入失敗時不留下半個檔、舊檔仍完好 | 自動：`test_studio_remote.py` |
| TC-008 | 【片1】作法 2 | 功能 | 設定檔已存在 | 再執行一次 `studio-connect` 給新權杖 | 新內容覆蓋舊的，並印「已覆蓋」 | 自動：`test_studio_remote.py` |
| TC-009 | 【片1】作法 2 | 功能 | 設定檔存了權杖 A；環境變數 `ABF_PAT` 設為權杖 B | 執行 `fetch-results`（替身記錄收到的 Authorization） | 送出的是 B，不是 A | 自動：`test_studio_remote.py` |
| TC-010 | 【片1】作法 6 未設定；原話 6 | 例外 | 沒有設定檔、沒有 `ABF_PAT` | 執行 `fetch-results r1` | 不連線；訊息說先執行 `abf-platform studio-connect --server <平台網址>`；結束碼 2；不建立資料夾 | 自動：`test_studio_remote.py` |
| TC-011 | 【片1】作法 2；作法 6 權限過寬 | 例外 | POSIX；設定檔權限 0644 | 執行 `fetch-results r1` | 拒絕使用，訊息含 `chmod 600 <該檔路徑>`；結束碼 2；不連線 | 自動：`test_studio_remote.py` |
| TC-012 | 【片1】作法 2（Windows）；PITFALLS 權限位元不可信 | 功能 | 模擬 Windows（權限位元不可信） | 執行 `studio-connect` 成功；再用一個權限位元很寬的設定檔執行 `fetch-results` | 成功時印一次提醒：此檔在個人資料夾、勿放進雲端同步資料夾；`fetch-results` 不因權限位元拒用 | 自動：`test_studio_remote.py` |
| TC-013 | 【片1】不做：不新增發權杖方式、不做 OAuth 瀏覽器流程、不做 keyring | 不在範圍 | 無 | 掃描 `studio_cli.py`、`studio_remote.py` 原始碼與執行 `studio-connect --help` | 不含 `webbrowser`、`keyring`、發權杖或 OAuth 的程式；說明文字寫明權杖向管理者索取（`pat new`）；`pyproject.toml` 依賴清單不變 | 自動：`test_studio_remote.py` |

## US2 — fetch-results：把結果表拉到自己的電腦（優先度 P1，片1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 【片1】原話 1「在R studio介面要能看」、原話 3；作法 3 | 功能 | 替身結果樹含 `ASV_table.tsv`、`counts.tsv`、`notes.md`、`DATA.TSV`、`report.html`、`x.bam` | 執行 `fetch-results run1`；再執行一次加 `--dir <另一個資料夾>` | 預設放 `~/abf-results/run1/`，且第一行先印其絕對路徑；`ASV_table.tsv`、`counts.tsv`、`notes.md`、`DATA.TSV`（副檔名不分大小寫）都在其中；加 `--dir` 時檔案放該資料夾、預設資料夾沒有被建立 | 自動：`test_studio_cli.py` |
| TC-015 | 【片1】作法 3（深度 3、檔案 200） | 功能 | 替身樹有 4 層深的檔，以及共 201 個符合的檔 | 執行 `fetch-results` | 只用 `run_outputs` 的 `enter`／`download` 路徑逐層走；不取第 4 層以下、不取第 200 個之後；摘要不宣稱已取得全部（細節見總覽疑問 3） | 自動：`test_studio_cli.py` |
| TC-016 | 【片1】作法 3（分頁） | 功能 | 一個檔分三頁（`next_offset` 帶動），內容含 CRLF 與中文 | 執行 `fetch-results` | 本機檔與原文逐位元相同（含 `\r\n`、中文；Windows 下也不被換行轉換改動） | 自動：`test_studio_cli.py` |
| TC-017 | 【片1】作法 3（不等待） | 功能 | 替身先回兩次 `loading` 再回 `ready`（測試把間隔縮短，並斷言設定值為 2 秒） | 執行 `fetch-results` | 重問後取到檔案；結束碼 0 | 自動：`test_studio_cli.py` |
| TC-018 | 【片1】作法 3（期限 120 秒） | 例外 | 替身永遠回 `loading`（期限縮為 0.2 秒；斷言預設為 120 秒） | 執行 `fetch-results` | 期限到就停；印出尚未取得的檔名；結束碼 1；不無限等待 | 自動：`test_studio_cli.py` |
| TC-019 | 【片1】不做：不鏡像整棵樹、不做二進位與 .html 下載；原話 3 | 不在範圍 | 替身樹含 `x.bam`、`y.fastq`、`z.gz`、`p.png`、`report.html`；另有一個白名單副檔名但伺服端回 `kind: binary` 的檔 | 執行 `fetch-results` | 以上檔案都不寫到本機、不呼叫 `read_run_file`（`kind: binary` 者呼叫後也不寫檔）；都列在「略過」並各附原因；`report.html` 附「須用瀏覽器登入平台下載」之意；不下載部分內容 | 自動：`test_studio_cli.py` |
| TC-020 | 【片1】原話 3「超過 25 MB 的檔案不下載且列出名稱」；作法 3 | 例外 | 一個檔 `size = jobs.RUN_FILE_MAX_BYTES + 1`，另一個剛好 `jobs.RUN_FILE_MAX_BYTES` | 執行 `fetch-results` | 前者不呼叫 `read_run_file`、輸出列出檔名與大小；後者照常取得；程式中數字引用該常數，不另寫 26214400 | 自動：`test_studio_cli.py` |
| TC-021 | 【片1】原話 3「站台拒絕的路徑原樣顯示拒絕原因」；作法 3 | 例外 | 替身：某檔回 `error`、`code: refused`、固定原因句；其他檔正常 | 執行 `fetch-results` | 輸出含該原因句（逐字）；其他檔仍取得；結束碼 1；CLI 不自己重判 readRoots | 自動：`test_studio_cli.py` |
| TC-022 | 【片1】作法 6；PITFALLS 58 | 例外 | 替身一：回 `state: error`、`code: refused`、原因文字為 "No open connection to the site. Log in once in a WSL terminal first…"；替身二：`code: bad_path` 或「站台拒絕讀這個檔案」 | 各執行一次 | 兩者訊息不同：前者說「平台可達，但站台連線沒開」，後者說路徑被拒原因；前者不得說「路徑不正確」；兩者結束碼 1 | 自動：`test_studio_remote.py` |
| TC-023 | 【片1】作法 6（站台連線欄位） | 功能 | 替身 `list_compute_envs` 一：該環境含 `site_connection {state, as_of, agent}`；替身二：沒有該欄位 | 在 TC-022 的站台連線沒開情況下各執行一次 | 一：另印 state、as_of、agent；二：不印、也不失敗 | 自動：`test_studio_remote.py` |
| TC-024 | 【片1】作法 3（總量 100 MB） | 例外 | 替身樹累計超過 `MAX_TOTAL_BYTES`（測試可縮小該常數） | 執行 `fetch-results` | 超過即停、列出未取的檔名；結束碼 1；已取的檔完整 | 自動：`test_studio_cli.py` |
| TC-025 | 【片1】作法 3（縱深防禦）；憲法 V | 例外 | 替身樹含路徑 `../evil.tsv`、`a/../../b.tsv`、`/etc/x.tsv`、`.hidden/c.tsv`；目標資料夾內另有一個指向資料夾外的符號連結 | 執行 `fetch-results` | 以上都不寫到目標資料夾之外（resolve 後須在資料夾內）；不跟隨符號連結；含 `..`、絕對路徑、點開頭的各條被略過並列出原因 | 自動：`test_studio_cli.py` |
| TC-026 | 【片1】作法 3 | 功能 | 目標資料夾已有同名檔 | 再執行一次 `fetch-results` | 同名檔被新內容取代，並印「已覆蓋」 | 自動：`test_studio_cli.py` |
| TC-027 | 【片1】作法 3（先寫暫存再替換；整檔讀完才算成功） | 例外 | 同名舊檔存在；替身第二頁回錯誤 | 執行 `fetch-results` | 該檔視為失敗並列出；舊檔內容不變、目的位置沒有半個檔、資料夾內沒留暫存檔；結束碼 1 | 自動：`test_studio_cli.py` |
| TC-028 | 【片1】作法 3（run 不存在） | 例外 | 替身回 `found: False` 與固定訊息 | 執行 `fetch-results nope` | 原樣顯示該訊息；結束碼 1；不建立任何資料夾 | 自動：`test_studio_cli.py` |
| TC-029 | 【片1】專長守則：跨使用者讀；作法 3 | 例外 | 真伺服器；甲的 run；乙的權杖 | 乙執行 `fetch-results <甲的 run>`；再對一個不存在的 run 執行 | 兩次輸出完全相同的一句（與 MCP 相同）；結束碼 1；本機不建立資料夾、沒有任何甲的檔案 | 自動：`test_studio_remote.py` |
| TC-030 | 【片1】作法 3；總覽疑問 2 | 例外 | 替身 `run_outputs` 回 `state: unavailable`（run 沒有結果資料夾紀錄）或 `state: error` 與 reason | 執行 `fetch-results` | 原樣顯示 reason；不寫任何檔；結束碼 1 | 自動：`test_studio_cli.py` |
| TC-031 | 【片1】作法 3（摘要與結束碼） | 功能 | 替身樹含可取的表與一個 `.bam`（刻意略過） | 執行 `fetch-results` | 印「取到 n 個、略過 m 個（含原因）」與資料夾路徑，接著印 R 載入碼區塊；結束碼 0（只有刻意略過時，暫定） | 自動：`test_studio_cli.py` |
| TC-032 | 【片1】作法 3（與 fetch-records 區分） | 功能 | 無 | 執行 `fetch-results --help` | 以一句話說明它拉結果表給自己的電腦，不是 `fetch-records`（抓 Nextflow 日誌）；沒有 `--user` 選項（權杖即身分） | 自動：`test_studio_cli.py` |

## US3 — R 載入碼：貼進 RStudio 就能讀（優先度 P1，片1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-033 | 【片1】原話 1；作法 4 | 功能 | `r_snippet` 輸入：已取到的 `ASV_table.tsv`、`counts.csv` 與資料夾 | 呼叫 `r_snippet(files, folder)` | `.tsv` 的 ASV 表一行 `read.delim(file.path("<資料夾>", "ASV_table.tsv"), check.names = FALSE, row.names = 1)`；`.csv` 的 counts 表用 `read.csv`；固定輸入得固定字串 | 自動：`test_studio_cli.py` |
| TC-034 | 【片1】作法 4（沒有候選） | 功能 | 取到 7 個表，檔名都不含 ASV／counts 等字 | 呼叫 `r_snippet` | 最多 5 行讀檔，並寫「其餘檔案見資料夾」 | 自動：`test_studio_cli.py` |
| TC-035 | 【片1】作法 4（路徑逸出）；PITFALLS Windows 路徑 | 功能 | 資料夾為 `C:\Users\a b\res`；檔名含 `"` | 呼叫 `r_snippet` | 反斜線轉為 `/`；`"` 與 `\` 被逸出；路徑含空白仍是合法的 R 字串 | 自動：`test_studio_cli.py` |
| TC-036 | 【片1】原話 5「一樣要注意中文的顯示不能口語」；作法 4 | 功能 | 無 | 檢查碼區塊前的說明字串（zh、en） | zh 為「將下列程式碼貼入 RStudio 的 Console」之意且通過 `test_web_wording_sweep.banned_in`；en 同結構、無 CJK 字元；zh／en 鍵相同 | 自動：`test_studio_cli.py` |
| TC-037 | 【片1】作法 4；PITFALLS Jupyter 連線檔旁證 | 例外 | 設定檔存了權杖與主機名 | 取得 `r_snippet` 輸出與整個 `fetch-results` 輸出 | 不含權杖、`token`、`password`、平台主機名、站台名稱；不含固定的 `analysis/figures` 路徑（PITFALLS 1550 旁證） | 自動：`test_studio_cli.py` |
| TC-038 | 【片1】不做：不啟動 RStudio／Jupyter、不執行 R、不偵測本機 R；原話 2 | 不在範圍 | 無 | 掃描 `studio_cli.py` 原始碼；執行 `fetch-results` 時以替身攔截子行程 | 不含 `subprocess`、`Rscript`、`which R`；執行過程沒有任何子行程；R 碼只是印出的文字 | 自動：`test_studio_cli.py` |
| TC-039 | 【片1】原話 1、原話 6 | 功能 | 維護者在自己的電腦（非桌機），RStudio 已裝；有一個成功的 run | 執行 `fetch-results <run>`，把印出的 R 碼貼進 RStudio Console | 表真的讀進來、可在 RStudio 看到內容；步驟寫在 `docs/TESTING.md` | 手動：`docs/TESTING.md` |

## US4 — 連線與錯誤：三條指令共用（優先度 P1，片1；publish-figure 部分屬片2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 【片1】作法 6（401）；片2 的 publish-figure 同此 | 例外 | 真伺服器；(a) 錯誤的權杖 (b) 已 `pat revoke` 的權杖 | 各執行 `fetch-results`（片2 加 `publish-figure`） | 兩者都印「權杖不正確或已被撤銷，向管理者重新索取（`pat new`）再 `studio-connect`」；結束碼 3 | 自動：`test_studio_remote.py` |
| TC-041 | 【片1】作法 6（自己的電腦離線） | 例外 | 設定指向一個已關閉的埠（連線被拒） | 執行 `fetch-results` | 說請確認本機網路、以 `--server` 網址為準；結束碼 3；不顯示堆疊 | 自動：`test_studio_remote.py` |
| TC-042 | 【片1】作法 6（公開網址不可達） | 例外 | 替身依序模擬 HTTP 502、503、504、逾時、TLS 失敗 | 各執行 `fetch-results` | 都印「平台公開網址無回應：平台所在機器可能未開機，或 Tailscale Funnel／MCP 服務未啟動」並列出所用網址；結束碼 3 | 自動：`test_studio_remote.py` |
| TC-043 | 【片1】作法 6（重試與逾時） | 例外 | 替身永遠 503；永遠不回應 | 各執行 `fetch-results` | 重試不超過 2 次、間隔 2 秒；單次呼叫逾時常數為 30 秒；整體在有限時間內結束；結束碼 3 | 自動：`test_studio_remote.py` |
| TC-044 | 【片1】作法 6（階段） | 例外 | 替身回 403；回 404（階段不存在） | 各執行 `fetch-results` | 說「重新執行一次；仍失敗請洽管理者」；結束碼 3 | 自動：`test_studio_remote.py` |
| TC-045 | 【片1】專長守則：錯誤訊息；作法 6 | 例外 | TC-010、TC-011、TC-040 至 TC-044、TC-021 各情況 | 收集每個錯誤的 stdout／stderr | 每則訊息都含「發生什麼」與「怎麼辦」；不含 `Traceback`、`File "`、內部路徑、SQL 字樣；語氣為書面語 | 自動：`test_studio_remote.py` |
| TC-046 | 【片1】完成標準三項負面操作 | 例外 | 維護者的電腦已完成 `studio-connect` | 故意輸入錯權杖；關閉本機網路；請維護者暫停 Funnel 或 MCP 服務；各執行 `fetch-results` | 三種情況各出現不同、看得懂的句子（401 句、離線句、不可達句）；貼入 ledger | 手動：`docs/TESTING.md` |
| TC-047 | 【片1】原話 6「在使用者自己的裝置」；完成標準 | 功能 | 一台不是平台所在的電腦，已 `pip install` 平台套件 | `studio-connect --server https://公開網址` 後對一個成功的 run 執行 `fetch-results` | 表被拉到該電腦；若只有同一台機器可試，須用公開網址而非 127.0.0.1，並在 ledger 標明未驗證跨機 | 手動：`docs/TESTING.md` |

## US5 — 下游頁指令區（優先度 P2，片1 兩行、片2 第三行）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-048 | 【片1】原話 1、原話 2；作法 7 | 功能 | 一個成功的 run，頁面 zh 與 en | 渲染下游頁 | 指令區（`<pre class="reason">`）有 `abf-platform studio-connect --server <平台網址>` 與 `abf-platform fetch-results <run id>`；並有「平台不執行腳本；請在自己的電腦執行下列指令…」之意的說明句（en 同結構、無 CJK）；既有「不在 NCHC 登入節點啟動」的 intro 句保留 | 自動：`test_web_downstream.py` |
| TC-049 | 【片1】原話 2；不做 | 不在範圍 | 同上 | 渲染下游頁 | 不含 `jupyter lab`、`docker run`、`rocker/rstudio`、`0.0.0.0`；`HOME_RESULTS`、`RM_FLAG` 若已刪，`test_scope` TC-072 與 `test_cleanup_confirm` TC-068 仍綠 | 自動：`test_web_downstream.py` |
| TC-050 | 【片1】作法 7（禁用字） | 例外 | 同上 | 取指令區文字（zh、en） | 不含 `token`、`password`、`AKIA`、`sk-`、`nchc`、`ln01`、`sbatch`、`srun`；`test_wording_in_command_block` 以新釘住內容通過 | 自動：`test_web_downstream.py` |
| TC-051 | 【片1】作法 7（逸出） | 例外 | run id 含 `<` 與 `"` | 渲染下游頁（zh、en） | 指令行中 run id 被逸出，頁面不含未逸出的 `<`、`"` 造成的標籤 | 自動：`test_web_downstream.py` |
| TC-052 | 【片1】作法 7；不做：不改貼網址表單 | 功能 | 一個未成功的 run；一個成功的 run | 渲染兩頁 | 未成功者不含任何新指令也不含 `jupyter`；成功者仍有貼網址表單與 `http://localhost` 提示、仍無 `<iframe`、`<img`、`<script`；`studio_url`、`_form`、`_answer`、`render_downstream` 簽章不變 | 自動：`test_web_downstream.py` |
| TC-053 | 【片1】裁決 2「第 1 片不印 publish-figure 也不註冊」 | 不在範圍 | 第 1 片完成時 | 渲染下游頁；執行 `abf-platform --help` | 頁面不含 `publish-figure`；頂層指令不含 `publish-figure`；片 2 合入後此案例由 TC-054、TC-070 取代 | 自動：`test_web_downstream.py`、`test_cli_contract.py` |
| TC-054 | 【片2】裁決 2；作法 7 | 功能 | 一個成功的 run，zh 與 en | 渲染下游頁 | 多出第三行 `abf-platform publish-figure <run id> <圖檔>`，run id 同樣被逸出；其餘行與 TC-048 同 | 自動：`test_web_downstream.py` |
| TC-055 | 【片1】B 級截圖 | 功能 | 一個成功的 run | `stage=downstream` 頁以 1440／390 寬、zh／en 各截圖；跑 axe | 共 4 張，無 serious／critical；頁面文字白話易懂（請維護者看是否合意） | 手動：`docs/TESTING.md` |

## US6 — publish-figure：發佈圖要本人點確認（優先度 P2，片2）

依 2026-11-12 裁決，取代原話 4 的「不走確認頁」。維護者原話：「RStudio 發佈圖時，要你點一次確認連結」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-056 | 【片2】裁決 1；作法 5 | 功能 | 替身 `call_tool`；本機有 `fig.png`（含已知位元組）、`plot.R`、`params.json` | 執行 `publish-figure run1 fig.png --code plot.R --params params.json --caption 圖說` | 呼叫 `publish_figure(run_id="run1", figures=[一個項目])`；該項目的 `filename` 為 `fig.png`、`content_base64` 解碼等於檔案位元組、`code`、`params`、`caption` 與檔案內容一致；一次只一張圖 | 自動：`test_studio_cli.py` |
| TC-057 | 【片2】裁決 1「CLI 永不傳 user_confirmed，也不傳 request_id」 | 例外 | 替身回覆的文字教人「帶 request_id 與 user_confirmed=true 再呼叫」 | 執行 `publish-figure`；並掃描 `studio_cli.py`、`studio_remote.py` 原始碼 | 替身收到的引數裡沒有 `user_confirmed`、`request_id` 兩個鍵；兩個原始檔不含 `user_confirmed` 字樣 | 自動：`test_studio_cli.py` |
| TC-058 | 【片2】裁決 1「待確認」；維護者「要你點一次確認連結」 | 功能 | 替身回 `state: pending` 與 `url` | 執行 `publish-figure` | 印圖名、大小、「尚未存入；請本人在瀏覽器開啟下列連結並按送出」，及工具回的連結（逐字，不自行組網址）；結束碼 0 | 自動：`test_studio_cli.py` |
| TC-059 | 【片2】裁決 1「不輪詢、不等待、不代按；不得說已存入」 | 例外 | 同上 | 執行 `publish-figure` 並計算呼叫次數與耗時 | 恰好呼叫一次 `publish_figure`；立即結束；輸出不含「已存入」 | 自動：`test_studio_cli.py` |
| TC-060 | 【片2】裁決 1；憲法安全網（AI 不得替人說 yes）；總覽 P8 | 例外 | 替身回的 `message` 含 `request_id=` 與 `user_confirmed=true` 的聊天通道說明 | 執行 `publish-figure` | 輸出不含 `user_confirmed`、`request_id=` 等教人代按的句子；只印本 CLI 自己的句子與 `url` | 自動：`test_studio_cli.py` |
| TC-061 | 【片2】裁決 1「訊息仍須含不會加入交付包之意」 | 功能 | 替身回 `pending` | 執行 `publish-figure` | 輸出含「不會加入交付包」之意（圖進私有圖庫，打包由本人在網頁勾選） | 自動：`test_studio_cli.py` |
| TC-062 | 【片2】裁決 1（拒絕）；作法 5 | 例外 | 替身回 `state: refused` 與 `reason`（例：大小、型別、圖庫已滿、檔名不合規則） | 執行 `publish-figure` | 逐字印出 `reason`；結束碼 1；不寫任何東西 | 自動：`test_studio_cli.py` |
| TC-063 | 【片2】專長守則：跨使用者寫；作法 5 擁有權 | 例外 | 真伺服器；甲的 run；乙的權杖 | 乙對甲的 run 執行 `publish-figure`；再對不存在的 run 執行 | 兩次輸出同一句、結束碼 1；`confirmations` 表沒有新增任何列、圖庫沒有任何圖 | 自動：`test_studio_remote.py` |
| TC-064 | 【片2】作法 5（本機先擋、上限引用常數）；裁決 1 常數 | 例外 | (a) 圖檔不存在或讀不到 (b) 圖檔超過 `figures.MAX_BUNDLE_BYTES` (c) `--code` 非 UTF-8 (d) 超過 `MAX_CODE_BYTES`／`MAX_PARAMS_BYTES`／`MAX_CAPTION_CHARS` | 各執行 `publish-figure` | 都被本機拒絕（說明是哪個檔或哪個欄位）、不呼叫工具、結束碼非 0；原始碼用常數名，不寫 5 MB、100 KB、10 KB、200 這些字面數字 | 自動：`test_studio_cli.py` |
| TC-065 | 【片2】裁決 1（端到端：待確認時不寫入） | 功能 | 真伺服器（需 `mcp-publish-figure` 已合併，之前 skip 並於 ledger 註明）；一張 PNG | 執行 `publish-figure` | `confirmations` 多一列待確認；`list_figures` 仍為空；`jobs` 表列數不變 | 自動：`test_studio_cli.py` |
| TC-066 | 【片2】裁決 1；專長守則：確認管道 | 功能 | 接 TC-065 的待確認請求 | 同一使用者經確認頁核准 | 此後圖庫才有該圖；`list_figures(packed_only=True)` 為空 | 自動：`test_studio_cli.py` |
| TC-067 | 【片2】裁決 1「不代按」 | 例外 | 替身記錄所有網路呼叫；掃描原始碼 | 執行 `publish-figure`，替身回 `pending` 與 `url` | CLI 不對該 `url` 發任何請求、不開瀏覽器（原始碼不含 `webbrowser`） | 自動：`test_studio_cli.py` |
| TC-068 | 【片2】不做：不做交付包打包、不做發佈後勾選、不做刪圖 | 不在範圍 | 無 | 執行 `publish-figure --help`；掃描 `studio_cli.py` 呼叫過的工具名 | 沒有打包、勾選、刪除相關選項；CLI 呼叫過的工具只有 `publish_figure`（不呼叫 `confirm` 之類） | 自動：`test_studio_cli.py` |
| TC-069 | 【片2】維護者「RStudio 發佈圖時，要你點一次確認連結」 | 功能 | 維護者在自己的電腦；用 R 產一張 PNG | 執行 `publish-figure <run> fig.png --code plot.R --params params.json`，在自己的電腦開啟印出的連結並按送出 | 連結在這台電腦上打得開（不是 127.0.0.1）；按送出前圖庫沒有該圖，按送出後私有圖庫有、交付包沒有 | 手動：`docs/TESTING.md` |

## US7 — 文件與既有測試同步（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 【片1】範圍「既有測試必須同步改」 | 功能 | 片 1 完成 | 跑 `test_cli_snapshots`（金檔 `cli_help_top.txt`、`cli_tree.txt`）、`test_cli_contract`（`MATRIX` 多兩個 `leaf`）、`test_cleanup_offer`（`COMMANDS`）、`test_station_envs`（頂層集合與括號內順序字串）、`test_cli_usage_doc`、`test_cli_flags` | 全綠；清單與金檔含 `studio-connect`、`fetch-results`，順序＝註冊順序；`test_every_leaf_is_in_the_matrix` 沒有放寬；金檔不是以 `ABF_UPDATE_GOLDEN=1` 蓋過了事 | 自動：既有測試 |
| TC-071 | 【片2】同上 | 功能 | 片 2 完成 | 同 TC-070 | 另含 `publish-figure`（`MATRIX` 第三個 `leaf`、金檔、清單） | 自動：既有測試 |
| TC-072 | 【片1】既有測試 `test_tc084` 的字詞掃描 | 例外 | 無 | 跑 `test_station_envs.py` 的 tc084（掃全部 `--help` 文字不得出現 launch、submit、cancel 字） | 新指令的說明文字不含這些字，測試仍綠（片 2 的 `publish-figure` 說明同） | 自動：`test_station_envs.py` |
| TC-073 | 【片1】範圍「只增不減，不放寬」 | 例外 | 無 | 對本次動到的每個既有測試檔比對 `origin/v3`：`test_web_downstream.py`、`test_cli_contract.py`、`test_cleanup_offer.py`、`test_station_envs.py`、`test_launch_docs.py`、金檔 | 只有計畫點名的釘住內容被改成新指令；沒有被移除、放寬、跳過的斷言；`test_strings_table_parity_and_wording`、`test_board_touches_are_minimal`、`test_wording_in_command_block`、`:119` 的非成功 run 斷言仍在；`spec.md`／`plan.md` 與 `test-case*.md` 在實作期間沒有被改 | 自動：`test_studio_cli.py` 加審查者比對 |
| TC-074 | 【片1】範圍「docs」；完成標準 | 功能 | 無 | 讀 `docs/PLATFORM.md`、`CHANGELOG.md` | `PLATFORM.md` 寫了兩條指令（片1）、設定檔位置與格式、錯誤與結束碼（0／1／2／3）；`CHANGELOG.md` 有條目；範例行能被 `build_parser` 解析、不被 `test_launch_docs` 誤判；文件範例的權杖是明顯的假值 | 自動：`test_launch_docs.py` 與新增文件測試 |
| TC-075 | 【片1】裁決 3「安裝路徑」 | 功能 | 無 | 讀 `docs/OPERATIONS.md` Funnel 段後的新小節與安裝說明 | 寫明：如何向管理者取得 `pat new` 發的權杖、公開網址從哪看、如何 `pip install` 本 repo 的 platform 套件、私有 repo 如何取得存取權、Windows 設定檔勿放雲端同步資料夾 | 自動：新增文件測試 |
| TC-076 | 【片1】完成標準手動走通 | 功能 | 無 | 讀 `docs/TESTING.md` 新增的手動步驟 | 有跨機走通（TC-047）與三項負面操作（TC-046）與 R 碼貼入（TC-039）的具體步驟，可照做；ledger 欄位（`git diff --stat`、新常數、`mcp` 版本與使用的 client 函式名、設定檔 `ls -l`）有列 | 自動：新增文件測試 |
| TC-077 | 【片2】裁決 2 | 功能 | 片 2 完成 | 讀 `docs/PLATFORM.md`、`docs/TESTING.md` | 寫了 `publish-figure`、確認連結由本人點、圖進私有圖庫不進交付包；手動步驟含 TC-069 | 自動：新增文件測試 |
| TC-078 | 【片1】原話 5；作法 4、7 | 例外 | 無 | 檢查新增的 zh／en 字串表（`studio_cli`、`studio_remote`、下游頁新鍵） | zh／en 鍵相同；en 無 CJK；zh 通過 `test_web_wording_sweep.banned_in`；zh 為正式書面語（不口語） | 自動：`test_studio_cli.py`、`test_web_downstream.py` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-079 | 【片1】憲法 I 憑證只在設定處、不印出；安全網「憑證」 | 功能 | 一個有明顯特徵的假權杖 | 成功執行 `studio-connect`、`fetch-results`（片2 加 `publish-figure`），收 stdout、stderr、logging | 全都不含該權杖字串；R 載入碼也不含 | 自動：`test_studio_remote.py` |
| TC-080 | 同上 | 例外 | 同上 | 在 401、不可達、逾時、站台連線沒開各情況執行，並加 `--debug` | stdout、stderr、caplog 與例外訊息都不含權杖；`--debug` 只記選項名稱、不記值 | 自動：`test_studio_remote.py` |
| TC-081 | 【片1】作法 9；不做：不做完整 --json 外殼 | 例外 | 同上 | 各指令加 `--json` 執行（成功與失敗） | 不崩潰；行為明確（回與 `launch` 一致的拒絕，或正確的 JSON）；任何 JSON 都不含權杖 | 自動：`test_studio_remote.py` |
| TC-082 | 【片1】作法 1、原話 6（不讀本機資料庫） | 例外 | `ABF_PLATFORM_DB` 指向空資料夾 | 執行 `studio-connect --no-check`、`fetch-results`（替身）；（片2 加 `publish-figure`） | 該資料夾仍為空：沒有建立 `platform.db`、`tokens.db`、`index.db` | 自動：`test_studio_remote.py` |
| TC-083 | 【片1】憲法 I.2（`tests/no_second_run_state_test.sh` 的送出掃描）；作法 8 | 例外 | 無 | 掃描 `studio_cli.py`、`studio_remote.py` 原始碼；跑 `tests/no_second_run_state_test.sh` | 不 import `subprocess`、`socket`、`urllib`、`requests`、`httpx`、`store`、`actions`；唯一例外是 `from … import 常數`（`jobs.RUN_FILE_MAX_BYTES`，片2 加 `figures.MAX_*`），且 import 後沒有開資料庫（TC-082 證明）；`studio_remote` 只用 MCP client 套件與標準庫；送出掃描仍綠（片 1 不得 import 尚不存在的 `figures`） | 自動：`test_studio_remote.py` |
| TC-084 | 【片1】範圍「伺服端零改動、被釘住不得改」；專長守則 migration | 例外 | 無 | 看 `git diff --stat origin/v3...HEAD` | 不含 `jobs.py`、`actions/`、`mcp_server.py`、`http_auth.py`、`store.py`、`web_board.py`、`web.py`、`platform/abf_station/`、`.github/`、`hooks/`、憲法、`plugin.json`、`pyproject.toml` 的依賴區段；不動資料結構，故不需 migration | 自動：審查者比對 |
| TC-085 | 【片1】專長守則：對等性 | 功能 | 無 | 列舉 CLI 原始碼呼叫的 MCP 工具名，與伺服端 `list_tools` 結果比對 | 片 1 只用 `run_outputs`、`read_run_file`、`list_compute_envs`（站台連線欄位，可選）與列工具（驗證權杖）；片 2 另加 `publish_figure`；每個都真實存在於伺服端；CLI 沒有自己實作擁有者過濾或 readRoots 判斷 | 自動：`test_studio_remote.py` |
