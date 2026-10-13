# 測試案例：007b 後續修正 F1–F3（第一次真國網驗收發現）

**規格**：`specs/007b-launch/spec.md`（US2.2、FR-009、SC-004）　**計畫**：`specs/007b-launch/followup-plan.md`　**總覽**：`followup-test-case-overview.md`

類型：**功能**（該做到的事）、**例外**（出錯或不該發生的事怎麼反應）、**不在範圍**（確認沒做）。
名詞沿用 `test-case.md`（假站台、假平台、確認終端、真代理）。新增：

- **活庫形狀的庫**：測試自己在暫存資料夾做出的 `platform.db`。`launches.run_name` 有 UNIQUE，內有一列 `ampliseq-mt-0920-rerun`（`slurm_job_id` 與 `submitted_at` 為空），其代理工作是第 6 號、狀態 `refused`、訊息開頭為「預檢未通過，沒有建立任何東西：connect（No open connection to the site…」。**絕不使用 `~/abf-station-test/`、不使用 port 8787。**
- **對應**：每一列 `launches` 找到自己那一次送出所產生的代理工作的方式。同名有多列時，每列只對到自己的工作。
- 「期限已過」＝工作的 `deadline_at` 早於現在，不論 `state` 欄位是否已被標成 `expired`。

## F1 — 被拒絕的送出要顯示被拒絕與原因

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-F1-01 | 維護者的例子：被代理拒絕要顯示原因 | 功能 | 一列沒有 Slurm 編號的 launch，其代理工作 `refused`，訊息是「預檢未通過，沒有建立任何東西：connect（No open connection to the site…」 | 執行 `abf-platform launches` | 該列的第二行是 `  被代理拒絕：` 加上代理訊息全文。輸出**不含**「未送出：代理沒有回報 Slurm 工作編號」、不含「結果不明」。另用一則**不含**「沒有建立任何東西」字樣的自訂訊息再跑一次，輸出也不得出現平台自己加的「沒有建立任何東西」或「國網上沒有」之類的主張（證明那句話只來自代理）。輸出不含「失敗」「已取消」「跑完」等 run 狀態詞 | 自動：pty＋真平台資料庫 |
| TC-F1-02 | 等代理處理中 | 功能 | 一列沒有 Slurm 編號的 launch，其工作 `queued`，期限未過；另一列的工作 `claimed`，期限未過 | `abf-platform launches` | 兩列各印 `  等代理處理中（工作 <該工作編號>）`，編號是各自的工作編號。不印「結果不明」，也不印「被代理拒絕」 | 自動 |
| TC-F1-03 | 結果真的不明時維持原句 | 例外 | 沒有 Slurm 編號的 launch，分別屬於下列情況：(a) 工作 `expired`；(b) 工作 `queued` 但期限已過、`state` 欄位還沒被改；(c) 工作 `claimed` 但期限已過；(d) 找不到任何對應的工作；(e) 工作 `error`，訊息為「sbatch 沒有成功（結束碼 1）…」且有 `left_on_site` | `abf-platform launches` | (a)(b)(c)(d) 印原本那行「未送出：代理沒有回報 Slurm 工作編號（結果不明時請查國網上的專屬資料夾與 nf-<run>）」，且**不**印「等代理處理中」。(e) 同樣保留該行，並**另外**印出代理的訊息與 `left_on_site`（US2.2：說清楚國網上留下了什麼）。(a)–(e) 都不印「被代理拒絕」 | 自動 |
| TC-F1-04 | 代理訊息要轉義 | 例外 | 拒絕訊息含 ESC `\x1b[31m`、CR、NUL、換行 | `abf-platform launches` | 輸出位元組中沒有 `\x1b`、`\r`、NUL；控制字元以可見方式（`terminal.esc`）顯示；訊息其餘文字照常。`run_folder` 同樣轉義 | 自動 |
| TC-F1-05 | 有 Slurm 編號的列一個字都不變 | 防止退步 | 已送出（有編號）的列：(a) 尚無 Nextflow 事件；(b) 索引裡已有同名 run；(c) 有 `cancel_requested_at` | 在 main 與分支各跑 `launches` | 三種列的輸出逐位元組相同 | 自動：與 main 比對的黃金檔 |
| TC-F1-06 | 同名多列各自對到自己的工作 | 功能 | 同一個 run 名稱有兩列：舊列的工作 `refused`（訊息 A）；新列的工作 `queued` | `abf-platform launches` | 舊列印「被代理拒絕：A」，新列印「等代理處理中（工作 <新工作編號>）」，兩列不會互相借用對方的工作。再換成「舊列 refused（訊息 A）、新列 refused（訊息 B）」，兩列各印各的訊息 | 自動 |
| TC-F1-07 | 活庫上的舊列也要顯示 | 功能 | 活庫形狀的庫（舊列尚無對應欄位），執行升級後 | `abf-platform launches` | `ampliseq-mt-0920-rerun` 那列印「被代理拒絕：預檢未通過，沒有建立任何東西：connect（No open connection to the site…」。這證明舊列有被回填，維護者的真實例子在他的庫上會成立 | 自動 |
| TC-F1-08 | 唯讀指令不改庫 | 例外 | 尚未升級的活庫形狀的庫（檔案只讀備份一份） | `abf-platform launches` | 不崩潰，每列仍印出合理的一行（可以退回「結果不明」，但不得丟例外）。庫檔案位元組在指令前後相同 | 自動 |

## F2 — 被拒絕的 run 名稱可以再用，其他情況一律不行

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-F2-01 | 維護者的例子：同名再送一次要成功 | 功能 | 活庫形狀的庫：`ampliseq-mt-0920-rerun` 有一列，其唯一的工作 `refused` | 以相同 run 名稱再 `launch`，答 `y`，假站台回報 Slurm 2231948 | 命令成功（結束碼 0）並印「已送出：Slurm 工作編號 2231948」。`launches` 表有**兩列**同名：舊列原封不動（沒有 Slurm 編號，`confirmed_at` 不變，對應的工作仍是 job 6），新列有 2231948。`launches` 的列數＋1（沒有任何列被刪）。**此案例必須先在改程式前於主線重現失敗或成功，並把實際結果記進執行紀錄** | 自動：真平台＋真代理＋假站台 |
| TC-F2-02 | 已送出的名字不能再用 | 例外 | 先前同名的 launch 有 Slurm 編號（已送出） | 再 `launch` 同名 | 在出現「確定送出？」之前就拒絕：畫面上沒有確認問句、沒有送出內容全文；結束碼非 0；錯誤訊息用中文說明這個名字已送出過、Slurm 編號是 N。`jobs`、`confirmations`、`launches` 的列數不變，沒有發出新的 run token | 自動：pty |
| TC-F2-03 | 還在等的名字不能再用 | 例外 | 先前同名的工作 `queued`（期限未過）；另一個案例是 `claimed`（期限未過） | 再 `launch` 同名 | 同 TC-F2-02 的拒絕方式，訊息說明上一次還在等代理處理 | 自動：pty |
| TC-F2-04 | 結果不明的名字不能再用 | 例外 | 先前同名、沒有 Slurm 編號的 launch，其工作為：(a) `expired`；(b) `error`（sbatch 結果不明）；(c) `queued`／`claimed` 但期限已過；(d) 找不到對應工作；(e) 工作 `expired` 且 `late_result_json` 記著遲到的拒絕 | 再 `launch` 同名 | 全部在問句之前就拒絕；訊息用中文說「結果不明，請先查國網上的專屬資料夾與 nf-<run>」；各表列數不變 | 自動：pty |
| TC-F2-05 | 歷史混合時以最嚴的為準 | 例外 | (a) 兩列同名，一列 refused、一列已送出；(b) 兩列同名，一列 refused、一列結果不明；(c) 兩列同名，都是 refused | 再 `launch` 同名 | (a)(b) 拒絕（只要有任何一列不是「無編號且 refused」就不行）；(c) 通過，成為第三列，三列都留著 | 自動 |
| TC-F2-06 | 編號只寫進自己那一列 | 功能 | 同名兩列：舊 refused，新列剛送出 | 新工作回報 Slurm 編號；另一個案例是舊工作遲到的結果才抵達 | 只有新列得到編號與 `submitted_at`；舊列仍無編號。新列的取消時間也只寫在新列。舊工作的遲到結果不會改到新列 | 自動 |
| TC-F2-07 | 取消、讀回紀錄、送出後的回報找對列 | 功能 | 同名兩列：舊 refused、新列已送出（有編號） | (a) `abf-platform cancel <run>`；(b) `abf-platform fetch-records <run>`；(c) 新列送出當下 `launch` 的結尾回報 | (a) 確認畫面與送給代理的內容用的是**新列**的編號與資料夾；(b) 讀的是新列的資料夾；(c) 印的是新列的編號，而不是舊列。若同名只有 refused 列，`cancel` 拒絕並說沒有 Slurm 工作編號 | 自動 |
| TC-F2-08 | 升級保留每一列 | 功能 | 活庫形狀的庫，含多列（已送出、有取消時間、refused、結果不明），以及非零的 `sqlite_sequence` | 開啟（升級） | 升級前後 `launches` 每一列的 `id`、`run_name`、`slurm_job_id`、`run_folder`、`ce`、`agent`、`confirmed_at`、`submitted_at`、`cancel_requested_at` 逐欄相同，列數相同。`jobs`、`confirmations`、`agents`、`compute_envs`、`meta` 的內容逐列相同。升級後新增的列編號接續舊的最大值，不重複。再開一次不再改動（可重入）。升級後同名可有多列 | 自動 |
| TC-F2-09 | 升級失敗時整個退回 | 例外 | 活庫形狀的庫，用 `_migration_step` 在複製完資料後丟出例外 | 開啟 | 例外往外丟；庫與升級前位元組等價（舊表、舊列都在，沒有留下半成品的新表）；下一次開啟可以正常完成升級 | 自動 |
| TC-F2-10 | 全新庫與升級庫結構相同 | 功能 | 一個全新建立的庫，與一個由舊庫升級而成的庫 | 比對 `launches` 的欄位與順序 | 兩者相同，且都允許同名多列 | 自動 |
| TC-F2-11 | 同時送出同名只會有一個通過 | 例外 | 兩個同名的確認幾乎同時進入 | 兩個都執行 `confirm_launch` | 恰好一個成功，另一個被拒；`jobs` 裡該名字只有一個 `launch_nextflow` 工作在等 | 自動 |
| TC-F2-12 | 再用名字之後代理端的檢查照舊 | 例外 | 名字可再用，但站台上的專屬資料夾已存在（假站台預先放好） | 再 `launch` 並答 `y` | 代理仍拒絕（訊息含「專屬資料夾…已存在，不覆蓋」），`sbatch` 零次，站台上資料夾不被改。該列因 refused，名字之後仍可再用 | 自動：e2e |
| TC-F2-13 | token 不混 | 例外 | 名字重用；舊的那次在被領走後才被拒（run token 已發出） | 新的送出被領走 | 舊 token 已撤銷，新 token 恰好一個有效；舊 token 不能建立 run | 自動 |

## F3 — platform_test.sh 要有餘裕

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-F3-01 | CI 上有餘裕 | 功能 | 修改後的分支推上 CI | 看 `run_all.sh` 的輸出行 | 每個平台測試項目的耗時都在 200 秒以下（原本 `platform_test.sh` 是 298 秒）；或已拆成多個 `run_all` 項目且每項遠低於 300 秒的上限。執行者要在 PR 說明貼出該行與 CI 連結。**這是唯一能證明它的方式：本機不算** | 手動：驗收者看 CI 紀錄 |
| TC-F3-02 | 沒有任何平台測試被跳過或漏掉 | 例外 | 修改前（main）與修改後各收集一次 | 列出 pytest 收集到的測試名稱，並跑 `tests/platform_test.sh` | 修改後收集到的測試名稱集合包含修改前的全部，數量相同或更多（新增 F1／F2 的除外）。輸出的最後一行是「platform tests: pytest exit 0, 0 skipped」。拆成多個項目時，各項目所含檔案的聯集等於全部 `platform/tests/test_*.py`，每個檔案恰好一次 | 自動＋手動：比對 |
| TC-F3-03 | CI 保護仍在 | 例外 | 在 CI 模式（`CI=true`）下，人為讓一個測試被跳過 | 跑 `platform_test.sh`（或拆出的各檔） | 仍以失敗結束，訊息「nothing may be skipped on CI」。缺 Java 或缺下載時 CI 模式仍失敗（沿用 `test_wrapper*.py` 的既有測試且它們仍通過） | 自動 |
| TC-F3-04 | 上限不是靠調高來解決 | 例外 | 看 `tests/run_all.sh` 的 diff | 比對 `PER_TEST_TIMEOUT` | 沒有調高（仍是 300 或更低），其說明註解沒有被弱化 | 手動：驗收者看 diff |
| TC-F3-05 | 對時鐘敏感的檔案仍單獨跑 | 例外 | 檢查分片設定 | 閱讀 `platform_test.sh` 與任何新拆出的檔 | `test_station_e2e.py` 與 `test_nextflow_e2e.py` 仍是「其他分片結束後、單獨、一個接一個」執行 | 手動：驗收者看 diff |
| TC-F3-06 | run_all 列得出來 | 功能 | 修改後 | `bash tests/run_all.sh --list` | 列出所有平台項目，其餘既有項目一個不少；若有新檔，檔名以 `_test.sh` 結尾 | 自動 |

## 不在範圍

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-F0-01 | 沒碰 `plugin/`、`.github/`、relay 網域 | 不在範圍 | 本分支對 main 的 diff | 檢查 | `plugin/`、`.github/`、`scripts/nf_relay.py`、`scripts/egress_ctl.sh` 沒有改動；沒有新增 relay 網域；沒有 009 的網頁或 MCP 寫入工具 | 手動：驗收者用 git diff |
| TC-F0-02 | 沒改自動重試或重新送出 | 不在範圍 | 同上 | 檢查 | 沒有新增自動重試、resume、重新送出的程式；名字重用仍需人在終端機答 `y` | 手動＋TC-F2-01 |
| TC-F0-03 | 沒碰正在跑的驗收環境 | 不在範圍 | 全部新測試 | 檢查測試程式碼與執行紀錄 | 測試只用暫存資料夾與假站台，不讀寫 `~/abf-station-test/`，不用 port 8787 | 自動：掃描＋手動：看紀錄 |

## 憲法與安全網

| TC | 名稱 | 類型 | Given | When | Then | 驗證 |
|---|---|---|---|---|---|---|
| TC-F0-04 | 原則 2：沒有第二份 run 狀態 | 例外 | 修改後 | 跑 `tests/no_second_run_state_test.sh` | 通過；`LAUNCH_ALLOW` 仍只有 `platform/abf_station/launch.py` 一項，且該檔沒有改動（`git diff` 為空）。`launches` 輸出只含工作事實，沒有 run 狀態詞（見 TC-F1-01） | 自動＋手動 |
| TC-F0-05 | 送出仍必須在終端機答 y | 例外 | 名字可重用的情況 | 用沒有終端機或答 `n` 的方式 | 不送出，三張表列數不變（US1.2 沿用）；重用名字**不**繞過確認 | 自動：pty |
| TC-F0-06 | 沒有放水既有測試 | 例外 | 本分支對 main 的 diff | 比對 `platform/tests/`、`tests/` 既有檔 | 既有斷言沒有被刪、放寬或跳過；只有新增。`spec.md`、`test-case.md`、`test-case-overview.md` 沒有改動 | 手動：驗收者用 git diff |
| TC-F0-07 | 原則 6：不靜默 | 功能 | 任何沒有 Slurm 編號的 launch | `launches` | 每一列都有一行說明（被拒絕／等待中／結果不明），沒有空白或只有 `-` | 自動（TC-F1-01～03 涵蓋） |
