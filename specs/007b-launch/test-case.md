# 測試案例：站台代理第二片：送出分析、即時進度、取消（007b）

**規格**：`specs/007b-launch/spec.md`　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，在正常情況下有做到。
- **例外**：出錯、缺東西，或使用者、平台、代理、站台做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事。測試確認它真的沒做，或會明白說「這個不支援」，而不是悄悄亂做。

## 名詞

沿用 007 的名詞（真代理、假站台、假平台、守衛檔、canary、讀取範圍、真平台行程、H）。本片新增或擴充的如下。

- **確認終端**：用 pty 驅動真的 `abf-platform` 命令列的測試工具。它能在問句出現後暫停、再送出一行輸入，並記下完整的畫面位元組。
- **假站台（擴充）**：
  - 假 `sbatch`：記下完整參數，並把收到的腳本檔內容另存一份；預設印出 `Submitted batch job <編號>`；可設成失敗、設成睡很久。
  - 假 `squeue`：讀一份測試寫的工作表（編號、名稱、使用者、工作目錄），支援 `-h -j <編號> -o '%j|%u|%Z'`。
  - 假 `scancel`、假 `curl`：記下參數與標準輸入。
  - 假 `rm`、`rmdir`、`mv`：只記錄呼叫。
  - 假 ssh：記下每一次參數（包含 `-O forward`、`-O cancel`、`-R ...`），能把標準輸入交給遠端指令，並能在第 N 次呼叫斷線。
- **送出呼叫**：假站台紀錄裡出現的 `sbatch` 帶腳本檔、`nextflow` 帶 `run`、或任何 `scancel`。
- **憑證**：確認終端答 `y` 或 `Y` 之後，平台寫下的那一列確認紀錄（編號、內容的 sha256、種類、時間）。
- **內容包（bundle）**：確認畫面列出的全部內容。
  - 包含：環境、專屬資料夾、samplesheet 文字、參數檔文字、設定檔全文、主控工作腳本全文、管線與版本、計費帳號。
  - 不含：token 的值。
- **token canary**：測試發出的 run token 的真實值，事後在各處搜尋。
- **真 Nextflow**：以 `platform/tests/pins.env` 釘住 sha256 的 Nextflow 25.10.4 加 nf-tower 1.17.5（以及 008 原有的 26.04.7 加 1.28.3）。
- **真 relay**：把 `scripts/nf_relay.py` 當子行程啟動，監聽測試用的 port。
- **迴圈位址**：字串 `127.0.0.1`。
- **正規化雜湊**：內容包轉成排序鍵的 JSON 之後的 sha256。
- **實例編號**：平台在 `platform.db` 裡保存的隨機編號，由 `/user-info` 的 401 回應標頭 `X-ABF-Platform` 回報。

所有「自動」案例都由 `tests/platform_test.sh` 一併執行。驗證方式的寫法：

- 「自動：pty」＝確認終端驅動真命令列。
- 「自動：e2e」＝真代理、真平台行程、假站台。
- 「自動：假平台」＝真代理連到測試寫的假平台。
- 「自動：真 Nextflow」＝釘住版本的真 Nextflow 加真 relay 加真平台。
- 「自動」＝單元或靜態掃描。

## User Story 1 — 送出前一定看到完整內容並確認（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | FR-001、FR-009；US1 情境 1；維護者：「終端機問是／否」 | 功能 | 真平台行程；一個可用的 Slurm 環境（假站台，`reach: ssh`，假 ssh）；真代理在線；帳號已設；10 列 samplesheet；確認終端 | 在 pty 執行 `abf-platform launch`（`nf-core/ampliseq`、版本 `2.18.0`、samplesheet、參數）。問句出現後先不回答，檢查畫面與所有資料庫和假站台紀錄。再輸入 `y` | **回答前**，畫面逐項列出：<br>• 管線與版本；<br>• 環境名稱；<br>• 專屬資料夾的完整路徑 `<workDir>/runs/<run>`；<br>• samplesheet 的每一列（10 列，一列不少）；<br>• 每個參數的名稱與值；<br>• 主控佇列與送出選項；<br>• 計費帳號；<br>• `nextflow.config` 全文，與之後將寫到國網的內容逐行相同；<br>• 主控工作腳本全文，包含 `nextflow run ...` 那一行，且與代理之後寫下的 `head.sh` 逐行相同；<br>• 最後一行是 `確定送出？(y/N)`。<br>畫面與資料裡沒有 token 的值。此時 `jobs`、`confirmations` 列數為 0，`tokens.db` 沒有新的 run token，假站台紀錄為空。**輸入 `y` 後**：恰好 1 個 `launch_nextflow` 工作與 1 筆憑證，憑證的 sha256 等於畫面內容的正規化雜湊；代理領走並完成；假站台的 `sbatch` 恰好 1 次 | 自動：pty |
| TC-002 | FR-001；US1 情境 1（`y` 與 `Y`） | 功能 | 同 TC-001；兩個不同的 run 名稱 | 第一個 run 在問句輸入 `y`，第二個 run 在問句輸入 `Y` | 兩個都送出，各有 1 筆憑證、各 1 次 `sbatch`。兩者的行為除 run 名稱外完全相同 | 自動：pty |
| TC-003 | FR-001；US1 情境 2 | 例外 | 同 TC-001，問句已出現 | 分別輸入：`n`、`N`、直接 Enter、`yes`、`YES`、`yy`、`是`、`y x`、`ok`、`1`、`  `（空白） | 每一種都不送出：命令列印出「未送出」，退出碼非零。`jobs`、`confirmations` 列數為 0；`tokens.db` 沒有任何新的 run token；假站台紀錄為空（連預檢以外的站台呼叫都沒有）；沒有建立專屬資料夾 | 自動：pty |
| TC-004 | FR-001；US1 情境 2 | 例外 | 同 TC-001 | 不給終端的各種做法：<br>• `echo y \| abf-platform launch ...`；<br>• `yes \| abf-platform launch ...`；<br>• 標準輸入重導向到 `/dev/null`；<br>• 關閉標準輸入；<br>• 以 `setsid` 啟動（沒有控制終端）；<br>• 加 `--yes`、`-y`、`--force`、`--assume-yes`；<br>• 設環境變數 `ABF_PLATFORM_ASSUME_YES=1`、`ABF_PLATFORM_YES=1`、`CI=true` | 前六類都拒絕送出，訊息說明需要在終端機互動確認，退出碼非零，不寫任何資料，不呼叫站台。最後一類的旗標被命令列解析器拒絕（未知選項），環境變數沒有任何作用。原始碼與說明文字裡找不到可跳過確認的選項、環境變數或文件記載的繞過方法 | 自動：pty |
| TC-005 | FR-001；US1 情境 2 | 例外 | 同 TC-001，問句已出現 | 分別：送 Ctrl-C；送 Ctrl-D（EOF）；直接關閉 pty；殺掉命令列行程 | 都不送出，不留下半套資料：`jobs`、`confirmations` 為 0，沒有有效 token，假站台紀錄為空，命令列不留殘餘行程 | 自動：pty |
| TC-006 | FR-001；US1 情境 1（使用者看到的必須是真的） | 例外 | 同 TC-001 | 1. samplesheet 的樣本名與參數值分別含 NUL、CR、ESC（`\x1b[2J`、`\x1b[8m`）、U+202E、U+2066 到 U+2069。2. 另備含 BEL、TAB、DEL、換行、很長一行的值（不含上述被拒的字元）。擷取畫面到問句為止 | 1. 含 NUL、CR、ESC、bidi 控制字元的，在組內容包時就被拒絕，訊息點名哪個欄位；問句沒有出現，什麼都沒寫。2. 其他控制字元以可見的跳脫形式顯示（例如 `\t`、`\x07`、`\n`）；每個顯示的值都有行前綴，畫面的每一行都以前綴開頭，沒有任何一行能藏在另一個值裡面。畫面的原始位元組裡沒有 ESC（`0x1b`）、CR、NUL 或 bidi 控制字元 | 自動：pty |
| TC-007 | FR-001；US1 情境 4 | 例外 | 假平台能在確認之後改動工作內容；一個合法的 `launch_nextflow` 工作與憑證 | 假平台各做一種改動，再交給真代理：<br>• 參數檔改一個字；<br>• samplesheet 改一列；<br>• 主控腳本改一個字；<br>• 專屬資料夾路徑改一個字；<br>• 管線版本改一位；<br>• 環境改一欄；<br>• 計費帳號改一個字；<br>• 內容包的 sha256 欄位改一位；<br>另以真平台行程直接改 `platform.db` 的 `args_json`（憑證不動）重做一次 | 每一種代理都拒絕，訊息說明內容與確認時不符。假站台的 `sbatch` 為 0 次，專屬資料夾沒有被建立，沒有任何檔案寫入，代理繼續存活 | 自動：假平台 |
| TC-008 | FR-001；US1 情境 3 | 例外 | 假平台 | 依序給 `launch_nextflow` 與 `cancel_run` 工作，但：<br>• 沒有 `confirmation_id`；<br>• `confirmation_id` 為空字串、null、數字、陣列；<br>• 編號查無此筆；<br>• 輪詢回覆沒有附憑證列；<br>• 憑證的 sha256 與內容包不符；<br>• 憑證的種類是 `cancel_run`，卻用在 launch（反之亦然）；<br>• 引數多了未知欄位；<br>• 憑證列已標記為用過 | 全部被代理拒絕（「拒絕」狀態，不是成功，不是崩潰）。假站台紀錄為空，守衛檔雜湊與修改時間不變，沒有資料夾被建立。最後給一個合法的 `preflight`，仍然成功，代理沒有被前面的弄停 | 自動：假平台 |
| TC-009 | FR-001；US1 情境 3、4（重放） | 例外 | 真平台行程；一個已用完的憑證；真代理與假站台；假 `squeue` 讓被取消的工作在 `scancel` 之後仍然列著 | 1. 在平台程式內以同一個 `confirmation_id` 再排第二個工作（直接呼叫 `jobs` 的對外函式，並用 SQL 直接插入）。2. 假平台把同一個合法 `launch_nextflow` 工作先後交給代理兩次。3. 假平台把同一個合法 `cancel_run` 工作先後交給代理兩次 | 1. 第二個被拒絕（程式或資料庫層，例如唯一性衝突），`jobs` 只多一筆。2. 第一次成功，第二次被代理拒絕，`sbatch` 總共 1 次，第一次寫下的檔案雜湊不變。3. 第一次成功，第二次被代理拒絕（代理記得用過的憑證編號，即使工作還列在佇列裡），`scancel` 總共 1 次 | 自動：e2e |
| TC-010 | FR-001；US1 情境 3；SC-002 | 例外 | 真平台行程；一組代理 token、一組 run token | 嘗試所有入口排入 launch 或 cancel：<br>• 以 POST、PUT、DELETE、GET 打 `/launch`、`/cancel`、`/confirm`、`/confirmation`、`/agent/launch`、`/agent/cancel`、`/agent/confirm`、`/jobs`、`/runs/<id>/cancel`，每條路徑分別不帶 token、帶代理 token、帶 run token；<br>• 列出每個 MCP 工具的輸入綱要；<br>• 靜態掃描 `mcp_server.py`、`receiver.py`、`agents.py`；<br>• 直接 SQL 在 `jobs` 插入 `launch_nextflow` 而 `confirmation_id` 為 NULL；<br>• 直接呼叫 `jobs` 模組每一個對外的排入函式，種類指定為 launch 或 cancel | HTTP 全部回 404、405 或 401，沒有新增任何資料列。MCP 仍然恰好六個工具、全是唯讀，輸入欄位沒有 `confirm`、`confirmation`、`yes`、`y`、`launch`、`cancel`、`kind`、`command`。三個模組不匯入、不呼叫排入 launch 或 cancel 的函式。NULL 憑證的插入失敗（資料庫層）。沒有憑證就沒有任何函式能排入這兩種工作 | 自動 |
| TC-011 | FR-001、FR-006；US1 情境 1 | 例外 | 同 TC-001；另備假平台（直接送工作給代理） | 在命令列（與假平台，對代理）嘗試各種不合法的輸入：<br>• run 名稱：`Bad`、`1abc`、`a/b`、`..`、`x;touch c`、`-x`、`a.b`、65 字元、空字串；<br>• 版本：`main`、`master`、`dev`、`HEAD`、`2`、`1.2.3.4.5`、7 位十六進位短 commit、空字串；<br>• 管線：`-hub/x`、`../x`、`./x`、`.hidden/x`、`nf-core/ampliseq --foo`、`nf-core/ampliseq;ls`、含空白、沒有斜線；<br>• samplesheet 路徑：`/etc/passwd`、`/x/../y`、相對路徑、讀取範圍之外的絕對路徑、含 `$(…)` 或空白；<br>• 環境：已停用、尚未支援、無代理、代理離線、非 Slurm | 命令列在問句出現**之前**就拒絕，說明是哪個欄位、為什麼；`jobs`、`confirmations`、token 都沒有新增，假站台紀錄為空。對假平台直接給代理的同樣值，代理再拒絕一次，`sbatch` 為 0 次、沒有資料夾。合法的 `2.18.0`、`v2.18.0`、40 位十六進位 commit、`nf-core/ampliseq`、`a-b_c` 通過 | 自動：pty |

## User Story 2 — 在國網上送出，照 Seqera 的方式（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | FR-001、FR-003、FR-009；US2 情境 1 | 功能 | 真平台行程、真代理、假站台（`reach: ssh`）；確認終端 | 在 pty 完成 TC-001 的送出（答 `y`），等結果 | 假站台紀錄顯示順序：`mkdir -p <workDir>/runs` → 一次站台呼叫（不帶 `-p` 的 `mkdir <專屬資料夾>` 加解開 tar）→ `sbatch` 恰好 1 次。專屬資料夾是 `<CE 工作資料夾>/runs/<run>`，由 CE 設定推出，不是程式裡的字面值。`sbatch` 的呼叫加腳本內容合起來載有：`-D <專屬資料夾>`、`-J nf-<run>`、`--no-requeue`、主控佇列、環境的送出選項、計費帳號。資料夾權限 700；`samplesheet.csv`、`params.yaml`、`nextflow.config`、`tower.token`、`head.sh` 權限都是 600。命令列印出 Slurm 工作編號、run 名稱、專屬資料夾；`launches` 恰有 1 列，欄位與其相符，`submitted_at` 有值 | 自動：e2e |
| TC-013 | FR-003、FR-004；US2 情境 1；維護者：「看看 Seqera 都怎麼做」 | 功能 | 接 TC-012，取得代理寫下的 `head.sh` 與 `nextflow.config`；假的 `nextflow` 會把收到的參數與環境寫進紀錄；另用真 Nextflow 25.10.4 | 1. 在沙盒目錄執行 `head.sh`（假 nextflow）。2. 用真 Nextflow 執行 `nextflow config -c nextflow.config`，一次未設 `SLURM_ACCOUNT`、一次設成部署帳號 | 1. 假 nextflow 收到的參數**逐字**是：`run <管線> -r <版本> -name <run> -params-file params.yaml -c nextflow.config -with-tower <端點>`。工作目錄是專屬資料夾。環境有：`SLURM_ACCOUNT`＝部署設定的帳號、`TOWER_ACCESS_TOKEN`＝`tower.token` 的內容（只在這個行程內）、`NXF_OPTS` 含 proxy 主機與 port 以及空的 `nonProxyHosts`、`NXF_SINGULARITY_CACHEDIR`。沒有 `NXF_LOG_FILE`，沒有 `-log`。腳本檔本體沒有 token 的值，讀取方式是從 `tower.token` 讀。`#SBATCH` 行只有範本允許的那幾種。2. 未設帳號時設定檔如預期報「SLURM_ACCOUNT is not set」；設了之後解析成功 | 自動：真 Nextflow |
| TC-014 | FR-001、FR-003；US2 情境 1（注入） | 例外 | 假站台；一個 canary 檔路徑；真平台、真代理 | 把下列值依序放進各欄位送出（各答 `y`）：<br>• 參數值：`x'; touch <canary>; '`、`$(touch <canary>)`、反引號、`${System.exit(1)}`、換行加第二個鍵、`!!python/object/apply:os.system ["touch <canary>"]`；<br>• 參數名：`a b`、`a;b`、`--x`、`1a`；<br>• samplesheet 儲存格：逗號、雙引號、換行、`$(touch <canary>)`；路徑含空白、單引號、`..`；<br>• 主控選項：`-c 4` 加換行再加指令、`--wrap=touch <canary>`、`-c 4; touch <canary>`、`--chdir=/`、`-D /`、`--uid=0`、`--gid=0`、`-o /x`、`-e /x`；<br>• CE 環境變數：名稱 `X;touch`、`A B`、小寫名稱；值含換行、NUL；值含 `$()`、引號；<br>• 主控佇列：`normal; touch <canary>` | 每一個值要嘛在代理或命令列被拒絕（說明哪個欄位），要嘛被當成**字面內容**原樣寫入且不被執行。canary 檔從未被建立。寫入的 `params.yaml` 用 YAML 解析後與輸入的對應完全相同（值都是字面字串、數字或布林）；`samplesheet.csv` 用 CSV 解析後與輸入的列相同。環境變數的值只出現在腳本本文並且被引用，從不出現在 `#SBATCH` 行。`head.sh` 通過 `bash -n`，每一行 `#SBATCH` 都在範本允許的集合內（`-D`、`-J`、`--no-requeue`、`-p`，以及符合白名單的 `-c`、`--cpus-per-task`、`--mem`、`-t`、`--time`、`-A`、`--qos`），沒有範本以外的行。選項白名單內的合法形式（例如 `-A acct -c 4 --mem=26G -t 4-00:00:00`）通過 | 自動：假平台 |
| TC-015 | FR-001、FR-003；US2 情境 1 | 功能 | 假 ssh 記下每次參數與標準輸入；samplesheet 有 10000 列（超過 1 MB）且含中文樣本名；參數值與一個 samplesheet 儲存格放不同的 canary | 送出（答 `y`） | 寫入專屬資料夾的檔案只用**一次**站台呼叫，內容以 tar 串流走標準輸入。把假 ssh 收到的 tar 解開，`samplesheet.csv`、`params.yaml`、`nextflow.config`、`head.sh` 的位元組雜湊**等於**確認畫面顯示的文字，一個位元組都不差，中文完整。tar 只含這五個固定名稱的檔案，沒有絕對路徑或 `..`。兩個 canary 都不出現在任何一次假 ssh 的參數列、`on_site.sh` 的指令字串、代理的標準輸出與標準錯誤中；只出現在站台上的檔案裡 | 自動：e2e |
| TC-016 | FR-001；US2 情境 1 | 例外 | 假站台上已有同名專屬資料夾，裡面放一個守衛檔；另備兩個同名 run 同時排入的情境 | 1. 送出一個專屬資料夾已存在的 launch。2. 對同一個 run 名稱同時排入兩個 launch（兩個憑證） | 1. 被拒絕，說明資料夾已存在；`sbatch` 為 0 次；資料夾裡原有檔案雜湊與修改時間不變；沒有 `rm`、`mv` 呼叫。2. 恰好一個成功、`sbatch` 共 1 次，另一個被拒絕。`launches` 對 run 名稱有唯一限制，第二列插不進去 | 自動：e2e |
| TC-017 | FR-001；US2 情境 2 | 例外 | 假 ssh 能在第 N 次呼叫斷線（N 取：建 `runs` 上層資料夾前、建專屬資料夾與寫檔當下、`sbatch` 當下）；假 `sbatch` 能回失敗（帳號無效）、回無法解析的輸出（`Submitted batch job abc`）、回編號之後連線斷掉 | 逐一送出（各答 `y`） | 每一種都：<br>• `sbatch` 最多呼叫 1 次，沒有任何重試；<br>• 回報用白話寫出原因，並列出國網上留下了什麼（例如「已建立資料夾 X，檔案可能不完整，尚未送出」）；<br>• 假站台沒有 `rm`、`rmdir`、`mv` 呼叫；<br>• 失敗時 `launches` 的 `submitted_at` 為空。<br>「編號之後斷線」這種結果不明的情形，回報明說「可能已送出，請查專屬資料夾與 `nf-<run>`」，不假裝失敗也不假裝成功 | 自動：e2e |
| TC-018 | FR-009；US2 情境 2（結果不能弄丟） | 例外 | 假 `sbatch` 在被呼叫後睡到工作期限之後才印出編號；另一情境：代理在 `sbatch` 完成後、回報前被 `kill -9`；期限用文件記載的 `ABF_PLATFORM_DEADLINE_LAUNCH` 縮短，預設值為 300 秒 | 送出（答 `y`），等命令列結束 | 睡過期限的情形：`launches` 仍記下 Slurm 編號與 `submitted_at`；命令列顯示已送出與編號，**不是**「代理沒有回應，工作已丟棄」。同樣情形下的 `cancel_run`：`cancel_requested_at` 仍被寫入。被殺的情形：命令列印出「結果不明：請查國網上的 `<專屬資料夾>` 與 Slurm 工作 `nf-<run>`」；該工作不會被再次交給任何代理（`sbatch` 總共 1 次）。預設期限為 300 秒；代理在 `sbatch` 前若發現剩餘不足 60 秒，拒絕而不送出（`sbatch` 為 0 次） | 自動：e2e |
| TC-019 | FR-004；US2 情境 3；Safety Net（憑證） | 例外 | 真平台、真代理、假站台；確認終端；本次發出的 run token 當 canary | 送出（答 `y`），完成後搜尋 canary | canary 只出現在站台的 `tower.token`（權限 600）。**不**出現在：`head.sh`、`nextflow.config`、`params.yaml`、`samplesheet.csv`、任何一次假 ssh 的參數、`on_site.sh` 的指令字串、代理的輸出與紀錄、命令列的輸出、確認畫面、`platform.db` 與 `index.db`（含 `-wal`、`-shm`）的位元組、`jobs.args_json`、`confirmations` 表。`tokens.db` 只有雜湊。站台上除 `tower.token` 外沒有任何檔案權限寬於 600，資料夾為 700。token 只經由輪詢回覆交給代理一次 | 自動：e2e |
| TC-020 | FR-004 | 例外 | 同 TC-019；用 `ABF_PLATFORM_CLOCK_OFFSET` 控制時間 | 1. 在問句答 `n`。2. 答 `y` 後立刻停掉代理，使工作不被領走（工作過期）。3. 正常領走。4. 代理回答「拒絕」或「錯誤」的情形。5. 領走後送出該 run 的 `create`、`progress`，再送出 `complete`，再用同一個 token 呼叫 `/trace/create`。6. 領走後 14 天（時鐘偏移）。7. 成功取消之後、`complete` 之前，用該 token 送該 run 的 `complete`；再送一個新 run 的 `create` | 1 與 2：`tokens.db` 沒有任何新的 run token。3：token 在**領走時**才產生，只存雜湊，綁定該 run 名稱；用它建另一個名稱的 run 被拒。4：該 token 被撤銷。5：`complete` 之後該 token 被拒（401），已存在的 run 資料不受影響。6：14 天後 token 被拒。7：取消**不會**立即撤銷 token（Nextflow 要靠它在收到 SIGTERM 後送出 `complete`）：`complete` 被接受；之後 token 被撤銷，新 run 的 `create` 被拒 | 自動：e2e |
| TC-021 | FR-006；US2 情境 2 | 例外 | 部署設定的帳號為 A；代理在 `hello` 回報帳號 | 1. 帳號未設。2. 環境的送出選項寫 `-A B`（B 不同於 A）。3. 送出選項寫 `-A A`。4. 送出選項沒有 `-A`。5. 確認之後、代理執行之前，把代理的部署設定改成帳號 C。6. 掃描整個 repo 找帳號字面值 | 1 與 2：在問句出現之前就拒絕，訊息分別是「帳號未設定，請用 … 設定」與「帳號與環境選項不一致」並點名 A 與 B，不猜；不建立任何東西。3：正常。4：`head.sh` 的標頭有 `-A A`，且 `SLURM_ACCOUNT` 匯出為 A。5：代理發現內容包的帳號與自己的設定不符，拒絕，`sbatch` 為 0 次。6：帳號值在程式與文件裡都不是字面常數（只出現在測試造的設定檔） | 自動：e2e |
| TC-022 | FR-006；US3 情境 4 | 例外 | 假站台 | 分別造成：<br>• 007 預檢的某一項失敗；<br>• 容器快取資料夾不可寫；<br>• 專屬資料夾已存在；<br>• 帳號未設 | 都在送出前拒絕，每一項訊息點名失敗項目與修法。假站台上沒有建立任何東西，`sbatch` 為 0 次。007 的預檢項目仍然執行 | 自動：e2e |
| TC-023 | FR-005；Assumptions | 功能 | 代理與站台同一台機器（`reach: local`），其他同 TC-012 | 送出 | 送出成功。沒有任何 `-O forward` 或 `--forward` 呼叫。端點直接指向平台，不經 relay。`on_site.sh` 在 `reach: local` 的既有行為不變 | 自動：e2e |
| TC-024 | FR-005、FR-006；Assumptions | 例外 | `reach: ssh`，但代理設定的平台網址不是迴圈位址（例如 HTTPS 的遠端平台） | 送出 | 在問句出現前就拒絕，說明這一片的反向通道要求平台與代理在同一台機器、以及怎麼改。沒有建立任何東西 | 自動：e2e |
| TC-025 | FR-003、FR-006；US2 情境 1（不悄悄略過） | 例外 | 一個 CE 設了非空的 `preRunScript`；另一個設了非空的 `postRunScript`；使用者參數帶 `outdir`；假平台送來同樣內容的 bundle | 各執行一次 `abf-platform launch`；並讓假平台直接把這些內容的工作交給代理 | 命令列在問句之前拒絕，前兩者的訊息是「不支援：這一片不執行事前／事後腳本」，使用者 `outdir` 被拒並說明 `outdir` 固定為專屬資料夾下的 `results`。代理對假平台的同樣內容也拒絕。沒有任何一種被悄悄略過或悄悄執行；`sbatch` 為 0 次。沒有設這些時，`params.yaml` 的 `outdir` 恰為 `<專屬資料夾>/results` | 自動：pty |

## User Story 3 — 即時看到每個 task 的進度（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | FR-005、FR-007；US3 情境 1；維護者：「上面應該能即時知道不同 task 的完成度」 | 功能 | 真平台行程；真 relay（`forward_port` 檔指向平台）；真 Nextflow 25.10.4 加 nf-tower 1.17.5；本機執行器的測試流程（≥3 個 process、≥12 個 task，含 `sleep`）；proxy 選項取自**實際生成的 `head.sh`** 的 `NXF_OPTS`；`-with-tower http://127.0.0.1:<F>` | 執行流程；執行期間每秒對 `get_run` 取樣；結束後比對 Nextflow 的 `trace.txt` | 取樣中至少 3 個不同的畫面，各 process 的完成、執行中、失敗數隨時間改變，且曾出現執行中大於 0 的時刻。結束時狀態為成功；每個 process 的完成數等於 `trace.txt` 中該 process 的完成列數；task 總數等於 `trace.txt` 的列數。relay 紀錄有 `OPEN-HTTP 127.0.0.1 <F>`，沒有 DENY；除此之外沒有連到任何其他位址 | 自動：真 Nextflow |
| TC-027 | FR-007；US3 情境 1 | 功能 | 同 TC-026，流程含一個必定失敗（不重試）的 task 與一個第一次失敗、第二次成功的重試 task | 執行並取樣 | 最終狀態為失敗。`failed_tasks` 有那個失敗 task 的名稱，錯誤訊息等於 `.nextflow.log` 裡該 task 的 `Command error:` 內容。重試成功的 task 沒有留在失敗清單，沒有被重複計算。各 process 計數等於 `trace.txt` | 自動：真 Nextflow |
| TC-028 | FR-007 | 功能 | `platform/tests/fixtures/` 內由真 Nextflow 25.10.4 錄下的一整段事件（附錄製腳本）：含成功、失敗加 `errorReport`、快取、重試；以及 008 原有的 1.28.3 事件 | 依序重送給接收端，比對 `get_run` | 1.17.5 的 `create`、`begin`、`progress`、`heartbeat`、`complete` 全部被接受；每個 process 的計數與失敗 task 與預期（由該段的 trace 得出）相符。沒有 `attempt` 欄位時重試 task 不會互相覆蓋。未知欄位被忽略、不被儲存；參數中名稱像秘密的值照 008 規則清除。008 原有的 1.28.3 重送測試**未改動**仍然通過 | 自動 |
| TC-029 | FR-007；US3 情境 2（失聯規則） | 功能 | TC-028 的 1.17.5 錄製檔，需含收到時間，且涵蓋 ≥4 分鐘的執行 | 計算相鄰訊息的最大間隔 | 最大間隔小於 `LOST_AFTER_SECONDS`（180 秒）。若實測 ≥180，這條失敗，迫使計畫決定改規則並點名 008 的失聯測試 | 自動 |
| TC-030 | FR-005 | 功能 | 真 relay，`forward_port` 檔內容為 F；一個監聽 F 的測試伺服器；允許的對等端（本機） | 從允許的對等端經 relay 送：`GET http://127.0.0.1:F/user-info`、`POST http://127.0.0.1:F/trace/create`、`PUT http://127.0.0.1:F/trace/abc/progress`（絕對形式） | relay 把請求轉到 F，回應原樣回來，relay 紀錄有 `OPEN-HTTP`。`forward_port` 檔改成另一個 port F2 後，**不重啟** relay，對 F 的請求被拒絕、對 F2 的放行 | 自動 |
| TC-031 | FR-005；US3 情境 4 | 例外 | 同 TC-030；在 F+1、80、22、18080（relay 自己）、1、65535 各放一個會計算連線數的監聽伺服器 | 逐項送出：<br>• 目的地：`127.0.0.1:<其他 port>`、`localhost:F`、`[::1]:F`、`127.0.0.2:F`、`127.1:F`、`0x7f.0.0.1:F`、`2130706433:F`、`0.0.0.0:F`、`127.0.0.1.:F`、`user@127.0.0.1:F`、`127.0.0.1:F@evil.example`；<br>• 埠號寫法：全形數字、`+F`、前導零、含空白；<br>• `CONNECT 127.0.0.1:F`；<br>• 原始形式 `GET /user-info`（Host 為迴圈位址）；<br>• 非計算節點的對等端；<br>• `forward_port` 檔缺少、空白、非數字、負數、0、>65535、等於 18080、內含二進位垃圾 | 全部被拒絕（403、400、405 或 502），所有計數伺服器的連線數為 0；relay 紀錄記為 DENY。檔案有任何異常時一律拒絕（fail-closed）。非計算節點仍被 `DENY-PEER` 擋掉 | 自動 |
| TC-032 | FR-005（收窄迴圈規則） | 例外 | 同 TC-030；測試伺服器記下收到的請求路徑與連線數 | 1. 經 relay 送 `GET/POST/PUT` 到：`/agent/poll`、`/agent/hello`、`/mcp`、`/`、`/trace`、`/user-info/x`、`/user-infox`、`//agent/poll`、`/trace/../agent/poll`、`/trace/%2e%2e/agent/poll`、`/trace/%2E%2E/agent/poll`、`/agent/poll?x=/trace/`。2. 在**同一條連線**上先送 `/user-info`，再送 `/agent/poll`。3. 送 `/user-info?x=1` | 1. 只有 `/trace/…` 與恰為 `/user-info` 的路徑（查詢字串不算路徑）被轉送，其他全被拒絕，測試伺服器收不到。2. 每條連線只處理一個請求，relay 在回應後關閉連線；第二個請求沒有被送到平台，測試伺服器只見 1 個請求。3. 被轉送 | 自動 |
| TC-033 | FR-005；US3 情境 2 | 例外 | 同 TC-026，執行到一半 | 停掉 relay（並一次試停反向通道）；讓流程跑完；然後把時鐘往後撥 3 分鐘加 | 流程照常結束，退出碼 0，`trace.txt` 完整。接收端沒有崩潰。撥時鐘後 `get_run` 顯示「失聯」，**不是**成功。之後依 TC-034 取回紀錄並 `rebuild`，同一個 run 變成與 trace 一致的結果，來源標為 rebuild | 自動：真 Nextflow |
| TC-034 | FR-011；US3 情境 2 | 功能 | 假站台上有一個由 TC-012 產生的專屬資料夾，裡面放真 Nextflow 錄下的 `.nextflow.log`、`.nextflow.log.1`、`.nextflow/history`、log 裡指名的 trace；`launches` 有該 run；不需要任何確認 | 執行 `abf-platform fetch-records <run>`（代理工作種類 `fetch_run_records`），再執行 `abf-platform rebuild` | 沒有出現確認問句（這是唯讀工作）。取回只用唯讀的站台指令（假站台紀錄裡沒有寫入、`rm`、`mv`、`tar` 解開）。本機 `<平台資料>/records/<run>/` 含 `.nextflow.log*`、`.nextflow/history` 與紀錄裡點名的 trace 檔。`rebuild` 把這個資料夾當作一個紀錄來源，該 run 的狀態與計數等於 trace，覆蓋先前「失聯」的畫面。取回前後國網資料夾的雜湊與修改時間不變。MCP 工具仍恰好六個 | 自動：e2e |
| TC-035 | FR-011；Safety Net | 例外 | 同 TC-034；假站台上有：指向守衛檔的符號連結（例如 `.nextflow.log.2`）、`tower.token`、`params.yaml`、log 裡「trace file:」指向專屬資料夾之外的路徑（例如守衛檔）、超過 20 MB 的紀錄檔、另一個 run 的資料夾 | 嘗試取回：不在 `launches` 的 run；另一個 run 的資料夾；`../` 路徑；符號連結；指向資料夾外的 trace；超大檔；並檢視取回的檔案清單 | 不在 `launches` 的 run、資料夾外的路徑被拒絕。符號連結不被跟隨，回覆說明已拒絕，守衛檔內容沒有被讀出。資料夾外的 trace 被拒絕。超過 20 MB 的檔只取前 20 MB，回覆明說「已截斷」。取回的檔案**只有** `.nextflow.log*`、`.nextflow/history` 與合法的 trace；`tower.token` 與 `params.yaml` 從未被取回。沒有任何寫入 | 自動：e2e |
| TC-036 | FR-009；US3 情境 3 | 功能 | TC-012 已送出、但還沒有送任何 Nextflow 事件的 run；另有一個送出失敗（`submitted_at` 為空）的 launch | 執行 `abf-platform launches`；之後送出該 run 的 `create`；再執行 `abf-platform launches`；再取消並再看一次；最後 `rebuild`（索引被重建）後再看 | 第一次：列出 run 名稱、Slurm 工作編號、專屬資料夾、確認時間，並寫出「已送出，尚未收到 Nextflow 事件」；失敗的那個 launch 不被寫成已送出。收到 `create` 後，該 run 不再顯示這句，改為指向 `get_run`。取消後顯示「取消請求已於 T 送出」。索引重建且沒有該 run 的紀錄時，這句重新出現（它只陳述事實）。全程沒有「執行中」「成功」「失敗」之類的狀態詞出自 `launches`；命令不寫入任何資料庫（資料庫位元組前後相同）；`get_run` 的輸出不因 `launches` 而改變 | 自動 |
| TC-037 | FR-006；US3 情境 4 | 例外 | 假站台、假 relay 行為：<br>(a) 沒有共用連線；<br>(b) 反向通道不存在（登入節點直接連 `127.0.0.1:<F>` 被拒）；<br>(c) relay 沒在跑；<br>(d) relay 在跑但規則沒生效（回 403，模擬舊行程）；<br>(e) 反向通道在、但平台沒回應；<br>(f) 該 port 上是別的程式（回 401 但沒有 `X-ABF-Platform` 或編號不同）；<br>(g) 全部正常 | 各送出一次（各答 `y`） | (a) 到 (f) 都不送出：沒有建資料夾、沒有寫檔、`sbatch` 為 0 次，假站台紀錄只有唯讀呼叫。訊息各自點名是**哪一段**不通，並給出修法：(a) 要使用者在 WSL 開連線的那一行、(b) 反向通道沒開、(c) 要啟動 relay 的命令、(d) 「請重啟 relay」與重啟命令、(e) 要檢查平台是否在跑、(f) 有別的程式佔用這個 port。(b) 與 (e) 的訊息不同。探測不帶任何 token，指令列沒有 token；通過的條件是 401 且標頭 `X-ABF-Platform` 等於這個平台的實例編號。實例編號是隨機的，存在 `platform.db`，重啟平台後不變，兩個不同的平台不同。(g) 通過並送出 | 自動：e2e |
| TC-038 | FR-005 | 功能 | 假 ssh；兩個先後送出的 launch | 送第一個，再送第二個；之後執行 `abf-station unforward`；再跑 `tests/on_site_test.sh` | 每次送出前代理先執行 `on_site.sh --check-forward`。第一次沒有通道時 `--forward` 送出 `-O forward -R 127.0.0.1:0:127.0.0.1:<平台 port>`：綁定位址恰為 `127.0.0.1`，不是 `0.0.0.0` 或 `*`，遠端 port 由 sshd 挑。筆電端 `<部署>/_personal/forward_port`（由 `on_site.sh` 寫，權限 600）與站台端 `<storage_root>/_relay/forward_port`（由代理經標準輸入寫，權限 600）都存著該 port。第二次送出沿用同一個 port，沒有第二次 `-O forward`，兩個 run 的事件都被接受。`abf-station unforward` 送出 `-O cancel` 並刪掉兩邊的檔案；除此之外沒有任何自動取消（run 結束、取消時都沒有）。`on_site.sh` 沒有新增 `nohup`、`setsid`、背景 `&`。`tests/on_site_test.sh` 原樣全綠 | 自動 |
| TC-039 | FR-005；Safety Net | 例外 | 整條鏈（真 relay → 反向通道 → 真平台）；run A、run B 兩個 token | 經 relay 送：不帶 token、亂寫的 token、代理 token、run A 的 token 寫 run B、run A 的 token 以 B 的名稱呼叫 `/trace/create` | 全部被拒（401 或 403），沒有新增任何 run，也沒有改動任何計數 | 自動 |

## User Story 4 — 取消（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | FR-001、FR-008；US4 情境 1；維護者：「這片就要能取消」 | 功能 | 接 TC-012 已送出的 run；假 `squeue` 工作表有該工作（名稱 `nf-<run>`、使用者為站台使用者、工作目錄為專屬資料夾）；確認終端 | 執行 `abf-platform cancel <run>`，在問句出現時檢查，再輸入 `y` | 問句前畫面列出 run 名稱、Slurm 工作編號、專屬資料夾，最後一行 `確定取消？(y/N)`；此時 `confirmations`、`jobs` 沒有新增，假站台沒有 `squeue`／`scancel`。答 `y` 之後：`squeue` 恰好 1 次且參數為 `-h -j <編號> -o '%j\|%u\|%Z'`；`scancel` 恰好 1 次且參數**只有**這個十進位數字；`launches.cancel_requested_at` 有值；輸出寫「取消請求已送出」。`Y` 同樣有效 | 自動：pty |
| TC-041 | FR-001；US4 情境 1 | 例外 | 同 TC-040，問句已出現 | 依 TC-003、TC-004、TC-005 的輸入方式（非 `y`／`Y`、無終端、`--yes` 類旗標與環境變數、Ctrl-C、EOF） | 全部不取消：假站台沒有任何站台呼叫（連 `squeue` 都沒有），沒有新資料列，`cancel_requested_at` 仍為空 | 自動：pty |
| TC-042 | FR-008；US4 情境 2 | 例外 | 假 `squeue` 的各種表：<br>• 該 run 不在 `launches`（只在索引裡）；<br>• `launches.agent` 與環境的代理不同；<br>• 工作已不在佇列（已結束）；<br>• 名稱不是 `nf-<run>`；<br>• 使用者不是 `site_user`；<br>• 工作目錄不是專屬資料夾；<br>• 輸出有兩行；<br>• `squeue` 失敗、連線斷線 | 逐一執行取消並答 `y`（需要時以假平台送工作） | 全部拒絕，`scancel` 為 0 次，訊息點名原因（不是平台自己送出的／不是你的／已結束／名稱不符／目錄不符／查詢失敗）。不重試。別人的同名工作與你的其他工作都沒有被碰 | 自動：e2e |
| TC-043 | FR-001、FR-008；US4 情境 3 | 例外 | 假平台 | 給 `cancel_run` 工作：沒有憑證、憑證 sha256 不符、確認後把工作編號改成工作表裡另一個人的編號、編號為 `123;touch c`、`123 456`、`-u me`、`--name=nf-x`、`0`、負數、極大數、字串型別 | 全部被代理拒絕，`scancel` 為 0 次，不呼叫任何站台指令（參數無效的）或只呼叫唯讀的核對。canary 檔不存在 | 自動：假平台 |
| TC-044 | FR-008 | 例外 | 兩個 run 都在跑；假 `squeue` 同時有別人的工作 | 1. 取消 run A。2. 對 run A 再取消一次。3. 取消 run B | 1. 只有 A 的編號收到 `scancel`。2. 需要再答一次 `y`；因為工作已不在佇列而被拒絕，`scancel` 總數仍為 1。3. 只有 B 的編號收到。全程沒有 `scancel -u`、`--name`、萬用字元 | 自動：e2e |
| TC-045 | FR-009；US4 情境 1；SC-003（顯示什麼） | 功能 | 用真 Nextflow 25.10.4 啟動一個流程，中途送 SIGTERM，錄下它送出的 `complete`；另一情境是完全沒有 `complete` | 1. 重送錄下的事件，再看 `get_run` 與 `abf-platform launches`。2. 取消後什麼事件都不送，時鐘撥到 3 分鐘加 | 1. `get_run` 顯示 Nextflow 回報的結局：失敗，附它自己的原因與退出狀態與各 task 計數，不是成功；`abf-platform launches` 另列「取消請求已於 T 送出」這個事實。2. `get_run` 顯示「失聯」，**不會**自己變成「已取消」。原始碼與輸出中沒有任何地方把 run 的狀態寫成「已取消」，也沒有程式根據 `launches` 推斷狀態 | 自動 |
| TC-046 | FR-001、FR-008 | 例外 | 假平台 | 給 `scancel`、`cancel`、`cancel_run ` 前後有空白、`CANCEL_RUN`、附加 `cmd` 或 `signal` 欄位的工作；最後給一個合法的 `preflight` | 前面全被拒絕（007 的種類比對規則不變），`scancel` 為 0 次；多出的欄位絕不被執行；最後的 `preflight` 仍成功 | 自動：假平台 |

## User Story 5 — 驗收：ampliseq 跑完（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-047 | US5 情境 1；SC-001；維護者：「ampliseq＋microbiome_test」「跟 9/20 那次一樣」「終端機問是／否」 | 功能 | 真國網；使用者已在 WSL 開好共用連線；relay 在跑；平台與代理在跑；2026-09-20 那次的 `params.yaml`；`docs/TESTING.md`「007b 手動驗收」 | 照 `docs/TESTING.md` 逐步：在終端機執行 `abf-platform launch`（`nf-core/ampliseq`、`2.18.0`、microbiome_test 的 10 個 fastq、引子 27F／1492R、PacBio、SILVA 138.2）；核對確認畫面；答 `y`；送出後先用 `abf-platform launches` 看，Nextflow 起來後在 `get_run` 觀看；等它跑完 | 確認畫面列出 TC-001 的全部項目，參數與 9/20 的 `params.yaml` 逐項比對只有 `outdir` 路徑不同。送出後回報 Slurm 編號與 run 名稱；排隊期間 `launches` 顯示「已送出，尚未收到 Nextflow 事件」。執行中 `get_run` 至少 3 個不同時刻看到各 process 的完成、執行中、失敗數在變。最後顯示成功，task 總數等於站台上該 run 的 `trace.txt` 列數（9/20 那次為 71，作為參考，不是判準）。結果在專屬資料夾的 `results/`。專屬資料夾權限 700，`grep -r` 該 run 的 token 只在 `tower.token`，`.nextflow.log` 與 slurm 輸出沒有 token | 手動：驗收者照 `docs/TESTING.md` |
| TC-048 | US4 情境 1；SC-003；維護者：「這片就要能取消」 | 功能 | 真國網；一個小的測試分析正在跑（有 task 在執行）；記下取消前的 `squeue -u` 全貌 | 執行 `abf-platform cancel <run>`，答 `y`；每 30 秒看一次 `squeue` 與 `get_run`，直到穩定 | 該 run 的主控工作與它底下的 task 在合理時間內都從 `squeue` 消失。你的其他工作與別人的工作都還在（與取消前比對）。`get_run` 顯示 Nextflow 回報的結局（失敗，附它自己的原因），不是成功；`abf-platform launches` 列出「取消請求已於 T 送出」。專屬資料夾與紀錄都還在。若有 task 殘留，驗收者記下，並確認取消的輸出有提醒使用者去查。`complete` 到達後該 run 的 token 失效 | 手動：驗收者照 `docs/TESTING.md` |
| TC-049 | FR-005；US3；Assumptions（sshd 不允許對外綁定） | 功能 | 真國網；共用連線已開；平台在跑 | 照 `docs/TESTING.md`：開反向通道；在登入節點 `ss -ltn` 看綁定位址；從計算節點（經使用者核可的短暫測試工作）用 `curl -x http://<登入節點>:18080 http://127.0.0.1:<F>/user-info`；改打其他 port 與 `/agent/poll`；直接打 `<登入節點>:<F>`；再執行 `abf-station unforward` 後重打；舊 relay 行程（規則生效前啟動）的情形 | 反向通道只綁在 `127.0.0.1`。經 relay 得到平台的 401 與 `X-ABF-Platform` 標頭。其他 port 與 `/agent/poll` 被 relay 拒絕，relay 紀錄有 DENY。直接打 `<登入節點>:<F>` 失敗。`unforward` 後再打失敗。舊 relay 行程時，預檢拒絕並說「請重啟 relay」，重啟後通過。JVM 路徑由 TC-047 的即時進度證明 | 手動：驗收者照 `docs/TESTING.md` |
| TC-050 | SC-001；維護者：「看看 Seqera 都怎麼做，上面應該能即時知道不同 task 的完成度」 | 功能 | TC-047 執行中；9/20 那次在 Seqera 上顯示的 process 清單 | 在執行中用 `get_run` 看，與 9/20 那次 Seqera 上的 process 名稱與計數方式比對 | process 名稱與 9/20 在 Seqera 看到的對得上；每個 process 的完成數隨時間增加；失敗 task 有名稱與原因。驗收者以白話寫下「與 Seqera 相比少了什麼」，並確認 `docs/SEQERA_PARITY.md` 有同樣內容（每個 task 的列表、CPU 與記憶體、日誌與報告、排隊中狀態），沒有隱瞞 | 手動：驗收者與維護者共同判斷 |

## FR 與成功條件

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-051 | FR-001 | 功能 | 一個由 007 建出的 `platform.db`（`jobs.kind` 只收兩種），內有環境、代理、已完成的工作 | 用升級後的平台開啟；排入一個帶憑證的 `launch_nextflow`；另在升級過程中注入錯誤（例如複製資料時失敗） | 舊資料不變（環境、代理、舊工作的列與雜湊相同）。新種類（`launch_nextflow`、`cancel_run`、`fetch_run_records`）能被排入。沒有憑證的 launch 或 cancel 排入仍失敗；`confirmation_id` 有唯一限制。007 的 `preflight`、`list_site_files` 仍可排入。直接塞別的種類（`rm`、`sbatch`、`scancel`、`launch`）仍失敗。升級在一個交易裡完成：中途失敗時舊表完整保留 | 自動 |
| TC-052 | FR-002 | 功能 | `tests/no_second_run_state_test.sh`、`platform/abf_station/launch.py` | 執行該檢查與它的自測；掃描 `platform/` 找字串拼接 | `LAUNCH_ALLOW` 恰有一條，指向 `platform/abf_station/launch.py` 和 `platform/tests/test_station_launch.py::test_unconfirmed_launch_is_refused`，該測試用 AST 找得到。`nextflow run` 與 `sbatch` 字樣在 `platform/` 只出現在這一個檔，命令列從這個檔匯入 `render_bundle()`；畫面上的主控腳本與代理寫下的 `head.sh` 由同一個函式產生。找不到為了躲掃描而拆開字串的寫法（例如 `"next" + "flow run"`）。既有的自測全部仍在且通過。這個測試本身：不給憑證時，斷言假站台紀錄為空、沒有資料夾、沒有資料列 | 自動 |
| TC-053 | FR-002；防止放水 | 例外 | 實作完成的分支 | 驗收者把 `launch.py` 裡「檢查憑證與 sha256」的程式暫時拿掉，執行 `test_unconfirmed_launch_is_refused` 與 TC-007、TC-008、TC-009 | 這四個測試都變紅。還原後回綠。步驟與結果寫入驗收報告 | 手動：驗收者 |
| TC-054 | FR-007 | 功能 | `platform/tests/pins.env`、`tests/platform_test.sh` | 檢視並執行 | 兩組版本（26.04.7＋1.28.3 與 25.10.4＋1.17.5）都釘了 sha256。sha256 不符時整個測試失敗，不是跳過。CI 缺少 25.10.4 時失敗而不是跳過 | 自動 |
| TC-055 | FR-009；原則 2 | 功能 | 一次完整的送出與取消之後 | 讀 `launches` 的欄位與資料 | 欄位恰為：`run_name`（唯一）、`slurm_job_id`、`run_folder`、`ce`、`agent`、`confirmed_at`、`submitted_at`、`cancel_requested_at`（加主鍵）。內容與送出時相符。沒有名稱含 `status`、`state`、`phase`、`result`、`exit`、`progress`、`ended` 的欄位 | 自動 |
| TC-056 | FR-010 | 功能 | PATH 沒有真 `ssh`、`tw`、`sbatch` | 掃描新增測試與執行 | 新測試檔沒有 `skip`、`xfail`、`importorskip`。沒有任何真的 `ssh` 被呼叫，沒有連國網或 Seqera。假站台的 `sbatch`、`squeue`、`scancel`、`curl` 都有紀錄 | 自動 |
| TC-057 | SC-004 | 功能 | WSL 與 CI | 執行 `bash tests/run_all.sh` | 全綠，沒有被跳過的平台測試。007 與 008 既有測試除了 TC-060 列出的之外都不需要改 | 自動 |
| TC-058 | 計畫 §6、Revision 2 項 11 與 17；FR-005 | 功能 | `docs/PLATFORM.md`、`docs/SEQERA_PARITY.md`、`docs/PITFALLS.md`、`docs/ROADMAP.md`、`docs/TESTING.md` | 檢查內容 | `PLATFORM.md` §9 含：確認流程、專屬資料夾、即時進度路線與通道、8 小時上限、平台與代理需同機、`abf-platform launches`、`abf-platform fetch-records`（並揭露紀錄內容會傳到平台）、`abf-station unforward`、`X-ABF-Platform` 標頭、run token 的處理與撤銷時機（含取消不會立即撤銷的原因）、**確認機制的限制**（同一使用者且能寫 `platform.db` 的行程，或自己開 pty 的 AI，可以偽造 `y`；真正的人類閘門是終端機，加上 Claude Code 對 `abf-platform launch\|cancel` 的核可設定）。`SEQERA_PARITY.md` 有送出、進度、取消三列，並誠實列出沒做的：每個 task 的列表、CPU 與記憶體、日誌與報告、排隊中狀態。`PITFALLS.md` 兩則新紀錄。`ROADMAP.md` 標記。`TESTING.md` 有 TC-047、048、049 的具體步驟 | 自動 |
| TC-059 | 回歸 | 功能 | 007 的既有流程（建環境、預檢、列檔、故障情境、關代理） | 執行 007 的 e2e | 危險呼叫紀錄仍為空（沒有 `sbatch` 帶腳本、沒有 `nextflow run`、沒有 `scancel`），守衛檔不變。這些流程的斷言沒有被改動 | 自動：e2e |
| TC-060 | 防止放水 | 功能 | 本 feature 對 `platform/tests/` 與 `tests/` 既有測試檔的 diff | 逐一比對被改動的斷言 | 只有計畫 Revision 2 項 6 逐條點名的斷言被改，並且只改成允許新增的那一項：<br>• `test_scope.py` 的 TC-071 與 `test_station_static.py` 的 TC-084：禁用字樣只在 `abf_station/launch.py` 允許；<br>• `test_station_envs.py` 的 TC-084：說明文字只在兩個新子指令處含 `launch`、`cancel`；<br>• `test_station_envs.py` 的 TC-063：子指令集合恰為舊集合加 `launch`、`cancel`、`fetch-records`、`launches`；<br>• `test_station_platform.py` 的 TC-090：欄位名含 `run` 只允許 `launches.run_name`、`launches.run_folder`；`jobs.kind` 恰為五種；`launch`、`rm` 仍失敗。<br>其餘斷言不變：沒有被刪、變弱、跳過，也沒有把預期值改成配合新輸出。`tests/no_second_run_state_test.sh` 只改 `LAUNCH_ALLOW` 與它的自測 | 手動：驗收者用 git diff |

## 不在範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-061 | 不在範圍 1 | 不在範圍 | 真平台、MCP、命令列 | 列出 MCP 工具與輸入綱要；請求 `GET /`、`/login`、`/confirm`、`/confirmation`、任何確認頁；查看命令列的子指令 | MCP 仍恰好六個唯讀工具，沒有 launch、cancel、confirm、fetch。沒有網頁（404）。送出與取消只能從 `abf-platform` 命令列做 | 自動 |
| TC-062 | 不在範圍 2 | 不在範圍 | 假站台 | 檢查 `head.sh` 與命令列；讓 `sbatch` 失敗後再送一次同名 run；查命令列選項 | `head.sh` 沒有 `-resume`。命令列沒有 resume、retry、relaunch 之類的子指令或選項。`sbatch` 失敗後沒有自動重試（TC-017）。同名 run 因資料夾已存在而被拒（TC-016） | 自動 |
| TC-063 | 不在範圍 3 | 不在範圍 | 一個「尚未支援」的 AWS Batch 環境；PATH 裡有會記錄的假 `aws`、`kubectl` | 對它執行 `abf-platform launch` | 在問句之前就拒絕，說「尚未支援」。假命令沒有被呼叫，沒有建任何東西 | 自動 |
| TC-064 | 不在範圍 4 | 不在範圍 | 真 Nextflow 流程執行到一半，之後讓假 ssh 的共用連線結束 | 觀察 | 沒有任何程式重新建立反向通道，沒有保活迴圈、重連或排程（`tests/no_second_run_state_test.sh` 的 daemon 掃描通過，`on_site.sh` 沒有新增迴圈）。流程照跑，`get_run` 顯示「失聯」。文件寫明 8 小時上限 | 自動 |
| TC-065 | 不在範圍 5 | 不在範圍 | 沒有共用連線 | 執行 `abf-platform launch` 並答 `y` | 代理不嘗試自己登入或要 OTP；回報照 007 的說法請使用者在 WSL 終端機開連線，並印出那一行指令。007 的 TC-070 靜態掃描（沒有 `getpass`、`pexpect`、`paramiko`、OTP）仍通過 | 自動 |

## 憲法與安全網

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-066 | 原則 1 | 功能 | 本 feature 新增的檔案；`tests/scripts_name_their_alternative.sh` | 執行該檢查並檢視新檔 | 每個新檔開頭有 `# Not …` 或 `# Nothing existing: …`。該檢查原樣通過 | 自動 |
| TC-067 | 原則 2（沒有第二份真相） | 功能 | `launches`、`confirmations` 表；`status.py`、`rebuild.py`、`receiver.py`、`mcp_server.py` | 靜態掃描；對同一份索引在 `launches` 放入奇怪值前後各呼叫 `get_run` | 上述四個模組不開啟 `platform.db` 的這兩張表（receiver 只為實例編號與 token 綁定讀取指定欄位）。`get_run` 的輸出在 `launches` 內容改變前後逐位元相同。`rebuild` 不開啟 `platform.db` | 自動 |
| TC-068 | 原則 2（沒有常駐、不輪詢） | 功能 | `scripts/`、`platform/`；假站台 | 執行 `tests/no_second_run_state_test.sh`；跑一段 5 分鐘（假時鐘）的進度流程 | 檢查通過，沒有新增 `nohup`、`setsid`、`while true`、sleep 迴圈。`launch.py` 沒有 `while`、執行緒。整段進度期間假站台的 `squeue`、`sacct` 為 0 次；`squeue` 只在每次取消時出現一次 | 自動 |
| TC-069 | 原則 3 | 功能 | `platform/`、`docs/PLATFORM.md`、`tests/platform_test.sh` | 用 `tests/no_hardcoded_paths.sh` 相同的正規式掃描；掃描帳號字面值 | 沒有命中，且 `launch.py` 確實被掃到。計費帳號沒有字面值寫在程式裡 | 自動 |
| TC-070 | II-4 | 功能 | `commands/`、`skills/`、`platform/abf_*/` | 執行 `tests/command_layer_is_site_neutral.sh`；掃描 `ngs`、`lgn`、`nchc`、`taiwania`、`18080` | 檢查通過。這些字樣不在 `platform/abf_*/` 的程式裡；登入節點名稱與 relay port 來自部署設定。`commands/`、`skills/` 沒有改動 | 自動 |
| TC-071 | V | 功能 | Git Bash | 在原生 Git Bash 執行代理與送出 | 如 007：拒絕並說明這是缺 WSL 的能力，不是 shell 或資料夾的問題 | 自動 |
| TC-072 | Safety Net：送出要完整顯示並等確認 | 功能 | `hooks/`、`tests/confirm_launch_test.sh` 等 | 在 main 與分支各執行 hook 的測試 | 結果完全相同，`hooks/` 沒有改動。代理是繞過 hook 的新路徑，由 TC-001 到 TC-011 把關 | 自動 |
| TC-073 | Safety Net：不刪使用者資料 | 功能 | 假站台有守衛檔；假 `rm`、`rmdir`、`mv` | 跑所有送出、取消與取回的流程（包含所有失敗情境） | 守衛檔雜湊與修改時間不變。代理從不呼叫 `rm`、`rmdir`、`mv`；失敗時留在站台上的東西由使用者決定。沒有任何程式碼刪除 `rawdata/`、`results/`、`analysis/` | 自動：e2e |
| TC-074 | Safety Net：憑證 | 功能 | `tests/credentials_stay_in_settings_test.sh` | 執行；掃描 git 追蹤的檔案 | 原樣通過。沒有 token 或帳號被提交到 git。計費帳號只來自部署設定 | 自動 |
| TC-075 | 防止退步（relay） | 功能 | main（bd9d42b）版 `nf_relay.py` 錄下的黃金檔：固定的 30 個請求（允許網域、拒絕網域、CONNECT 允許與拒絕、IP 字面值、非計算節點、額外網域解析成私有位址）及其回應；`tests/nf_relay_domains_test.sh`、`tests/relay_connect_test.py`、`tests/egress_allow_test.sh`、`tests/on_site_test.sh` | 在 `forward_port` 檔不存在時，把同樣的 30 個請求送給分支版 relay，並在兩個分支各跑上述測試 | 30 個請求的回應與黃金檔逐一相同。四個既有測試在兩邊的結果相同 | 自動 |
| TC-076 | 治理：既有檢查檔 | 功能 | 本 feature 的完整 diff | 檢查 `tests/` 既有檢查檔、`hooks/`、`skills/`、`commands/`、`scripts/` 的改動 | 只有：`tests/no_second_run_state_test.sh`（`LAUNCH_ALLOW` 與自測）、`scripts/on_site.sh`（只新增 `--forward`、`--unforward`、`--check-forward`，既有行為不變）、`scripts/nf_relay.py`（只新增迴圈位址規則）、以及計畫點名的。`hooks/`、`skills/`、`commands/` 無改動 | 手動：驗收者用 git diff |
| TC-077 | 治理：憲法與 PR | 功能 | `.specify/memory/constitution.md`；PR 說明 | 比對與閱讀 | 憲法 4.0.0 沒有改動。PR 說明把「relay 多放行一個迴圈目的地」單獨拿出來問維護者，並附上與 main 比較的結果 | 手動：驗收者閱讀 |
