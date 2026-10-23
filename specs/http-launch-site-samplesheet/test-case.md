# 測試案例：HTTP launch 可用環境 readRoots 內的站台檔；MCP launch 加 samplesheet_text

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer. Write every row so that it can be
judged without reading code: what is set up, what the person or the system does,
what must be seen. No internal jargon without a one-line explanation.
Language: 繁體中文; identifiers (TC-, FR-, US) and file paths stay as they are.
-->

**規格**：`specs/http-launch-site-samplesheet/plan.md`（本任務沒有 spec.md；plan 的「目標」「維護者原話」「作法」「不做」就是規格）　**總覽**：`test-case-overview.md`

名詞（每條都用同樣的意思）：

- **A、B**：兩位不同的平台使用者（測試裡的 alice 與 bob）。A 的上傳資料夾是 `<uploads_root>/A`，B 的是 `<uploads_root>/B`。
- **readRoots**：運算環境設定裡「代理可以讀的資料夾清單」。測試環境 `lab-a` 的 readRoots 含 uploads 資料夾與一個共享資料夾 `/data/shared`（測試用暫存目錄）。
- **站台檔**：在跑 pipeline 的站台（例如國網 nano4）上的檔案，平台這台機器上不一定有。
- **路徑格**：samplesheet 裡被當成檔案路徑的格子（`path_columns` 指名的欄、常見欄名的欄、或以 `/` 開頭的格）。
- **用文字送**：MCP `launch` 的新選填參數 `samplesheet_text`，給 CSV 全文；**用路徑送**：舊的 `samplesheet`，給平台機器上 A 的上傳資料夾裡的檔案路徑。
- 「HTTP」＝帶使用者身分的 MCP/HTTP 呼叫；「終端機」＝ `abf-platform launch`；「stdio」＝本機 stdio 的 MCP（兩者都沒有使用者身分）。
- 自動測試檔：新的在 `platform/tests/test_http_site_samplesheet.py`（下稱「新檔」）；其餘是既有檔。

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

## User Story 1 — 站台檔案路徑能從 Claude 送出（優先度 P1）

維護者原話：「同意放寬：HTTP 送出的 samplesheet 路徑可以指向環境 readRoots 內的站台檔案，但落在 uploads 資料夾內的仍只能是自己的；並加 samplesheet_text 參數。照計畫做。」真實情境：nano4、nf-core/ampliseq 2.18.0、10 個 PacBio fastq `/work/u9613010/abf/projects/microbiome_test/rawdata/Day5_*.fastq.gz`、欄位 `sampleID,forwardReads`、`path_columns=["forwardReads"]`，之前被拒兩次，訊息是「cannot read the samplesheet as a plain file in your own uploads folder」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 目標；維護者原話；作法 1、2 | 功能 | A 是 HTTP 使用者，擁有環境 `lab-a`；`lab-a` 的 readRoots 含 `/data/shared`（測試用暫存目錄，內有 10 個檔 `Day5_01.fastq.gz`…`Day5_10.fastq.gz`） | A 呼叫 `launch`：pipeline `nf-core/ampliseq`、revision `2.18.0`、`path_columns=["forwardReads"]`，`samplesheet_text` 是表頭 `sampleID,forwardReads` 加 10 列，每列的 forwardReads 是 `/data/shared/.../Day5_NN.fastq.gz`；不給 `samplesheet`，客戶端不能跳表單 | 回覆 ok=true、state=pending、sent=false，並給確認網址；沒有出現「cannot read the samplesheet as a plain file in your own uploads folder」或「必須在你自己的上傳資料夾」之類的拒絕 | 自動：新檔 |
| TC-002 | 作法 1（舊 TC-049 反轉） | 功能 | 同 TC-001 的環境；A 的上傳資料夾裡有一個 CSV，路徑格指向 `/data/shared` 內的檔（在 readRoots 內、不在 A 的資料夾） | A 用路徑送出 `launch`（`samplesheet` 是那個 CSV） | 回覆 ok=true、state=pending；沒有被拒 | 自動：新檔 |
| TC-003 | 作法 2「bundle 與確認畫面跟用路徑送出一樣」；維護者例子 | 功能 | TC-001 的送出 | 看回覆裡的 summary（確認畫面文字） | 畫面列出管線 `nf-core/ampliseq`、版本 `2.18.0`，與 samplesheet 的 10 列資料，每列都看得到 `Day5_NN.fastq.gz` 的站台路徑 | 自動：新檔 |
| TC-004 | 作法 2「平台機器上不寫任何檔」 | 功能 | TC-001 的環境；先記下平台的 uploads 資料夾與平台資料夾裡所有檔案的清單 | A 用文字送出 `launch`（成功與被拒各一次） | 送出前後清單完全相同：平台機器上沒有多出任何檔案或資料夾 | 自動：新檔 |
| TC-005 | 作法 1 | 功能 | A 的 samplesheet 一半的格子在 A 自己的上傳資料夾，一半在 `/data/shared` | A 用文字送出 | 通過到 pending；沒有被拒 | 自動：新檔 |
| TC-006 | 作法 1「通過者照舊記進 upload_paths」；116b | 功能 | 同 TC-005 | A 送出後，讀送出的內容包（bundle）裡的 `upload_paths` | `upload_paths` 只記 A 自己資料夾裡的格子（每格有真實路徑）；`/data/shared` 的格子不在其中；記錄的區域是 A 的資料夾 | 自動：新檔 |
| TC-007 | 作法 2；維護者例子（送得出去） | 功能 | TC-001 的狀態；A 的客戶端能跳表單且答「送出」 | A 用文字送出 `launch` | 回覆 sent=true，有工作編號；佇列裡剛好一個 launch 工作；確認紀錄裡的 bundle 有 10 列樣本 | 自動：新檔 |
| TC-008 | 作法 2「同樣的 text＋參數重送 → 找到同一個已核准的確認」 | 功能 | TC-007 已送出（或 pending 已被本人在網頁按送出） | A 用完全相同的 text 與參數再呼叫一次 `launch` | 回到同一個確認與同一個工作編號；佇列裡仍只有一個工作，沒有第二個確認排隊 | 自動：新檔 |
| TC-009 | 作法 2「被核准的 hash 蓋到 rows」 | 功能 | TC-007 已核准一份 samplesheet_text | A 把 text 裡一個格子（或一個樣本名）改掉，其餘參數不變，再呼叫 `launch` | 不會被當成已核准的那一個：得到新的 pending，沒有工作編號，原本的工作不受影響 | 自動：新檔 |
| TC-010 | 作法 3 | 功能 | A 用文字送出、格子在 readRoots 的 run 已失敗（索引裡是 failed）、環境與代理仍是 A 的 | A 用 HTTP 對該 run 呼叫 `resume`，再另一個失敗 run 呼叫 `relaunch` | 兩個都不因新規則被拒，各得到 pending（續跑沿用第一次的 rows） | 自動：新檔 |

## User Story 2 — 不該放行的形狀仍然被拒（優先度 P1）

這個故事是「安全閘」：以下每種形狀在改動前都被拒，改動後仍必須被拒；對照基準是 base `origin/v3`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 作法 1「落在 uploads_root 內的仍只能是自己的」 | 例外 | 環境 readRoots 包住 `uploads_root`（含 uploads 資料夾）；B 的資料夾裡有 `y.fq` | A 用文字送出，格子用 readRoots 寫法指到 `<uploads_root>/B/y.fq` | 被拒；沒有 pending、沒有工作 | 自動：新檔 |
| TC-012 | 同上 | 例外 | 同 TC-011；A 的上傳資料夾裡有一個 CSV，格子指到 `<uploads_root>/B/y.fq` | A 用路徑送出 | 被拒；沒有 pending、沒有工作 | 自動：新檔 |
| TC-013 | 116 TC-052；116b 連結規則 | 例外 | 共享資料夾（在 readRoots 內、不在 uploads 內，真的存在於平台這台機器）裡有一個符號連結指向 `<uploads_root>/B` | A 用文字送出，格子走 `/data/shared/link/y.fq` | 被拒（連結解析後落在 B 的資料夾）；沒有 pending | 自動：新檔 |
| TC-014 | 116 TC-052 | 例外 | A 自己的資料夾裡有一個符號連結指向 B 的資料夾 | A 用文字送出，格子走 `<uploads_root>/A/link/y.fq` | 被拒；沒有 pending | 自動：新檔 |
| TC-015 | 作法 1；路徑含 `..` 一律拒絕 | 例外 | 同 TC-011 | A 分別送出兩個格子：`/data/shared/../<uploads 資料夾名>/B/y.fq`，以及 `<uploads_root>/A/../B/y.fq` | 兩個都被拒；沒有 pending | 自動：新檔 |
| TC-016 | 作法 1（字面寫法） | 例外 | 同 TC-011 | A 送出格子用不規則寫法指到 B 的檔：`<uploads_root>//B/./y.fq`、`<uploads_root>/B//y.fq`、結尾多斜線等 | 每一種都被拒；沒有 pending | 自動：新檔 |
| TC-017 | 作法 1 | 例外 | 同 TC-011 | A 送出的格子是 `uploads_root` 本身，以及 B 的資料夾本身（沒有檔名） | 兩個都被拒 | 自動：新檔 |
| TC-018 | 作法 1（以整段路徑比對，不是比字首） | 例外 | `<uploads_root>` 下除了 A 的資料夾，還有名稱以 A 的名字開頭的鄰居資料夾（例如名為 `A` 加一個字母），裡面有檔 | A 用文字送出，格子指到那個鄰居資料夾裡的檔 | 被拒（在 uploads 內但不是 A 自己的資料夾） | 自動：新檔 |
| TC-019 | 作法 1「不在 readRoots、也不在 uploads → 拒絕」 | 例外 | 同 TC-001 | A 用文字送出，格子是 `/etc/passwd` 或 `/elsewhere/x.fq`（不在任何 readRoots，也不在 uploads） | 被拒，訊息說在允許讀取的範圍之外；沒有 pending | 自動：新檔 |
| TC-020 | 同上 | 例外 | 同 TC-001；A 的上傳資料夾裡有 CSV，格子指到 readRoots 之外 | A 用路徑送出 | 被拒，同樣的訊息；沒有 pending | 自動：新檔 |
| TC-021 | 既有行為：相對路徑不是路徑欄的合法值 | 例外 | 同 TC-001 | A 用文字送出，格子是 `rawdata/x.fq`（相對路徑） | 被拒（不是絕對路徑） | 自動：新檔 |
| TC-022 | 作法 1 | 例外 | A 的 samplesheet 有 10 個格子，9 個在 readRoots 內，1 個在 B 的資料夾 | A 用文字送出 | 整個 launch 被拒，沒有 pending；不是「只擋那一格」 | 自動：新檔 |
| TC-023 | 116 TC-051「不透露別人的資料夾」 | 例外 | 同 TC-011；B 的資料夾裡有 `y.fq` | A 送出指到 B 的檔的 launch，看拒絕訊息 | 訊息只提到 A 自己的資料夾；不含 B 的名字、B 資料夾裡的檔名，也不含 A 所給的那條路徑 | 自動：新檔 |
| TC-024 | 不做：samplesheet 檔本身仍須在自己的資料夾 | 例外 | 環境 readRoots 含 `/data/shared`；其中有一個 CSV | A 用路徑送出，`samplesheet` 分別是：`/data/shared/sheet.csv`、B 資料夾裡的 CSV、`<uploads_root>/A/../B/sheet.csv`、A 資料夾裡指向 B 的 CSV 的連結 | 每一種都被拒，維持舊拒絕字句（「samplesheet 必須是你自己上傳資料夾裡的檔案」或「讀不到，或不是你自己上傳資料夾裡的一般檔案」）；放寬只針對 CSV 裡的格子，不是 CSV 檔本身 | 自動：新檔 |

## User Story 3 — samplesheet_text 參數（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 作法 2「恰好給一個」 | 例外 | A 是 HTTP 使用者 | A 呼叫 `launch`，同時給 `samplesheet` 與 `samplesheet_text` | 被拒，字句含「samplesheet 與 samplesheet_text 只能給一個」；沒有 pending | 自動：新檔 |
| TC-026 | 作法 2 | 例外 | 同上 | A 呼叫 `launch`，兩個都不給 | 被拒，同一句話；沒有 pending | 自動：新檔 |
| TC-027 | 作法 2（空字串不是內容） | 例外 | 同上 | A 只給 `samplesheet_text=""` | 被拒，講清楚要給內容（不得當掉、不得露出錯誤堆疊）；沒有 pending | 自動：新檔 |
| TC-028 | 作法 2「上限 1 MiB」 | 例外 | 同上 | A 給的 `samplesheet_text` 是 1 MiB 加 1 個位元組（UTF-8 計） | 被拒，訊息說太大與上限；沒有 pending | 自動：新檔 |
| TC-029 | 作法 2「超過 1 MiB 拒絕」的邊界 | 功能 | 同上 | A 給的 `samplesheet_text` 剛好 1 MiB（1048576 位元組） | 不因大小被拒（若被拒，原因不是大小） | 自動：新檔 |
| TC-030 | 作法 2「含 NUL 拒絕」 | 例外 | 同上 | A 給的 text 中間有一個 NUL 字元 | 被拒，訊息說含 NUL；沒有 pending | 自動：新檔 |
| TC-031 | 作法 2；錯誤訊息規則 | 例外 | 同上 | A 給的 `samplesheet_text` 不是文字（例如數字或清單） | 被拒，用白話說要給 CSV 文字；沒有錯誤堆疊 | 自動：新檔 |
| TC-032 | 作法 2「同一個 parse_samplesheet」 | 例外 | 同上 | A 用文字送出兩種壞內容：只有表頭沒有資料列、各列欄數不一致 | 兩種都被拒，訊息與把同樣內容寫成檔案、用路徑送出時一字不差；沒有 pending | 自動：新檔 |
| TC-033 | 作法 2「bundle 與確認畫面跟用路徑送出一樣」 | 功能 | 同一份 CSV 內容：一次放在 A 的上傳資料夾用路徑送出，一次用文字送出；其餘參數相同 | 兩個都送出到 pending，比較兩個確認的 bundle 與畫面文字 | 樣本、參數、檔案內容、畫面文字完全相同（run 名稱以外的差別不可有；hash 的差別只能來自 run 名稱等本來就不同的欄位） | 自動：新檔 |
| TC-034 | 作法 2「stdio 也接受 samplesheet_text」 | 功能 | stdio（沒有使用者身分），客戶端能跳表單並答「送出」 | 用 `samplesheet_text` 送出 `launch`，格子在 readRoots | 通過、送出，有工作編號；不受上傳資料夾規則限制（與用路徑送出時一樣） | 自動：新檔 |
| TC-035 | 作法 2「stdio 沒有表單仍照舊拒絕」 | 例外 | stdio，客戶端不能跳表單 | 用 `samplesheet_text` 送出 `launch` | 被拒，說這裡沒有人可以按「送出」，請用終端機指令或帶權杖的 HTTP；沒有 pending、沒有工作 | 自動：新檔 |
| TC-036 | 作法 2「samplesheet 在工具簽章改成選填」；LS-52 改寫 | 功能 | MCP 伺服器的工具清單 | 讀 `launch` 工具的參數結構 | 參數是 `pipeline, revision, run_name, samplesheet, samplesheet_text, ce_name, params, path_columns`；必填只剩 `pipeline, revision, run_name`；`samplesheet` 與 `samplesheet_text` 預設都是空；工具清單仍是原來那 12 個，沒有多也沒有少 | 自動：`platform/tests/test_station_launch.py`（TC-LS-52 改寫，ledger 記舊/新/理由） |

## User Story 4 — 沒被放寬的其他規則（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-037 | 作法 1；不做「不改 params 規則」 | 功能 | 既有 116b 的 params 測試 | 不改任何一行地執行 `test_owner_gaps.py` 的 TC-001..011、TC-049 與 ruling3 各案 | 全部通過（params 的路徑規則一字未變） | 自動：`platform/tests/test_owner_gaps.py` |
| TC-038 | 作法 1 第一點；116b | 例外 | A 用文字送出，格子都合法；`params` 有一個值是 `<uploads_root>/B/a.fq` | A 送出 | 被拒，訊息是 params 那一句（只提 A 自己的資料夾）；格子合法不能讓 params 蒙混 | 自動：新檔 |
| TC-039 | 作法 1「終端機與 stdio 完全不變」；116 TC-053 | 功能 | 路徑格在環境 readRoots 內，不在任何使用者資料夾 | 在終端機（不指名帳號）與 stdio 送出 | 照舊通過；bundle 裡沒有 `upload_paths` | 自動：`test_owner_binding.py`（TC-053 不改） |
| TC-040 | 同上 | 例外 | 路徑格不在任何 readRoots | 在終端機與 stdio 送出 | 照舊被拒，字句與改動前一樣（在允許讀取的範圍之外） | 自動：新檔（與 base 同輸入同輸出） |
| TC-041 | 不做「不改代理端 upload_paths 複查」 | 功能 | 既有代理端複查測試 | 不改地執行 `platform/tests/test_station_owner.py` 與 `test_station_launch.py`、`test_station_envs.py` 中與 upload_paths 有關的案例 | 全部通過；`abf_station/launch.py` 的 `_check_upload_paths` 沒有被改動 | 自動：`platform/tests/test_station_owner.py` |
| TC-042 | 不做；116b「核可後連結被改」 | 例外 | 一個新形狀的 bundle：有站台檔格子，加上 `upload_paths`；其中一筆記錄的真實路徑在 B 的資料夾、或記錄的路徑現在解析到別處 | 代理端收到這個工作 | 代理拒絕，說上傳資料夾裡的路徑在核可後變了（或記錄的真實路徑不在擁有者資料夾），沒有送出 | 自動：`platform/tests/test_station_owner.py` |
| TC-043 | 作法 1；代理端不因站台檔格子而誤拒 | 功能 | 新形狀的 bundle：一部分格子在站台 readRoots（不在 `upload_paths`），一部分在擁有者資料夾（有記錄且真實路徑相符） | 代理端收到這個工作 | 代理端的複查通過（只對記錄的項目向站台確認真實路徑），工作可繼續 | 自動：`platform/tests/test_station_owner.py` |
| TC-044 | 116 D4；作法「不改誰的環境」 | 例外 | B 擁有環境 `b1` 與代理 `agent-b`；A 沒有 | A 用文字送出，`ce_name="b1"` | 被拒，字句與「環境不存在」一樣（找不到）；沒有 pending；文字送出沒有繞過擁有者規則 | 自動：新檔 |
| TC-045 | 116 D4 | 例外 | 有一個沒有擁有者的環境 | A 用文字送出，指向那個環境 | 被拒（找不到／不能用）；沒有 pending | 自動：新檔 |
| TC-046 | 不做「不改既有 116 行為」 | 功能 | 116 的其餘既有測試 | 不改地執行 `test_owner_binding.py` 的 TC-050..053、TC-055..058 | 全部通過；只有 TC-049 對應案例按維護者 10-23 裁示由「拒」改成「過」 | 自動：`platform/tests/test_owner_binding.py` |

## User Story 5 — 確認管道與跨使用者（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-047 | 作法 2「確認畫面一樣」；Constitution I.2 | 功能 | A 的客戶端不能跳表單 | A 用文字送出 `launch` | 回覆 sent=false、state=pending，給確認網址，並叫 A 本人去按「送出」後再用同樣參數呼叫；佇列裡沒有工作、沒有 hand-off 紀錄 | 自動：新檔 |
| TC-048 | Constitution I.2「AI 不能代按」 | 例外 | 看 `launch` 的參數結構（含新的 `samplesheet_text`） | 找有沒有任何參數能表示「已確認／直接送出」 | 沒有這種參數；用 AI 自己的呼叫無法讓 pending 變成工作 | 自動：新檔 |
| TC-049 | 專長守則「跨使用者 寫」 | 例外 | A 用文字送出，有一筆 pending 確認 | B（登入網頁的另一位使用者）按 A 那個確認網址的「送出」 | 被拒；A 的確認仍是 pending，佇列沒有工作 | 自動：新檔 |
| TC-050 | 專長守則「跨使用者 讀」 | 例外 | 同 TC-049 | B 打開 A 那個確認網址、或用 B 的 token 呼叫能讀 A 的確認內容的入口 | 看不到 A 的畫面文字、樣本與路徑；回應與「不存在」一樣 | 自動：新檔 |
| TC-051 | 專長守則「跨使用者 寫」；find_approved 只認呼叫者本人 | 例外 | A 用文字送出並已被核准、有工作編號 | B 用完全相同的 text 與參數呼叫 `launch` | B 得到屬於 B 自己的新 pending；不會回傳 A 的工作編號；A 的工作不變（若環境是 A 的，B 本來就用不了：結果是找不到） | 自動：新檔 |
| TC-052 | 專長守則「錯誤訊息」 | 例外 | TC-011、TC-019、TC-025、TC-028、TC-030 這幾種拒絕 | 逐一看拒絕訊息 | 每則都說發生什麼事、使用者該怎麼辦；沒有堆疊、沒有 SQL、沒有平台機器上的內部路徑（只可出現 A 自己的上傳資料夾路徑） | 自動：新檔 |
| TC-053 | 專長守則「日誌與回應不含密鑰」 | 例外 | A 以帶 token 的 HTTP 呼叫送出 `samplesheet_text`（成功與被拒各一次） | 檢查回覆與測試期間捕捉的日誌輸出 | 沒有 token、密碼或其他密鑰字串出現在回覆或日誌 | 自動：新檔 |

## User Story 6 — 文件、替換掉的舊釘子、對等性（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-054 | 作法 4；完成標準「三處同步，且有 samplesheet_text 的名字」 | 功能 | `docs/PLATFORM.md` | 讀 414、445、451 行附近三處 | 三處都改了：(1) 說 samplesheet 檔仍須在自己資料夾、也可用 `samplesheet_text` 給內容；(2) 路徑格規則改成「落在 uploads 內須是自己的、其餘須在環境 readRoots 內」；(3) params 規則與路徑格同一條；並有一句為什麼（遠端站台沒有每人上傳資料夾，隔離由環境擁有者守）；舊句「每個路徑格都必須在自己資料夾內」已不存在 | 自動：新檔 |
| TC-055 | 完成標準「ledger 列出每個改寫的舊釘子」 | 功能 | `specs/http-launch-site-samplesheet/ledger.md` | 讀 ledger | 列出 `test_owner_binding.py` TC-049 對應案例與 `test_station_launch.py` TC-LS-52，每筆有舊預期、新預期、理由（維護者 2026-10-23 裁示）；沒有其他被悄悄改過的既有測試 | 自動：新檔 |
| TC-056 | 專長守則「對等性」；範圍「parity／guidance」 | 功能 | 既有對等性測試 | 不改地執行 `test_web_parity.py`、`test_chat_tools.py`、`test_guidance.py`、`test_actions_layer.py` | 全部通過（使用者可見的動作清單與動作層函式一一對應，邏輯沒有複製到 mcp_server.py） | 自動：`platform/tests/test_web_parity.py` 等 |
| TC-057 | 專長守則「migration」 | 功能 | 一個全新的平台資料庫，以及用 base 建的對照 | 比較兩者的資料表與欄位 | 沒有任何資料表或欄位的差異；因此不需要 migration | 自動：新檔 |

## 不在範圍（計畫「不做」段）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-058 | 不做：上傳工具（ROADMAP 012） | 不在範圍 | MCP 伺服器的工具清單 | 列出工具與 `launch` 的參數 | 沒有新增任何上傳／寫檔工具；`samplesheet_text` 只被讀進記憶體；平台上傳資料夾沒有因它多出檔案 | 自動：新檔 |
| TC-059 | 不做：代理去站台讀 samplesheet | 不在範圍 | 用文字送出 `launch`，尚未按送出 | 查工作佇列 | 在核可前佇列沒有任何工作（沒有為了讀 samplesheet 或檢查站台檔而排的 `list`／讀檔工作）；格子是否存在不在平台檢查 | 自動：新檔 |
| TC-060 | 不做：遠端站台每人資料夾（009h） | 不在範圍 | 一個遠端站台的環境 | A 用文字送出 launch | 沒有在站台建立任何每人資料夾，也沒有排任何建資料夾的工作（沿用 116 TC-058 的斷言） | 自動：`test_owner_binding.py`（TC-058 不改）與新檔 |
| TC-061 | 不做：角色與共享（010） | 不在範圍 | 同一個 lab 的 A 與 B | B 嘗試用 A 的 text、A 的確認、A 的環境 | 同 lab 也不共享：全部被拒或找不到；沒有任何「共享」旗標或角色出現 | 自動：新檔（並重跑 `test_owner_binding.py` TC-013） |
| TC-062 | 不做：不改誰可以按「送出」、resume/relaunch 不加參數 | 不在範圍 | MCP 工具清單 | 看 `resume` 與 `relaunch` 的參數結構 | 兩者仍只有 `run_name`；沒有 `samplesheet_text`，也沒有可改樣本、參數的欄位 | 自動：`platform/tests/test_resume_entrypoints.py`（不改） |

## 憲法與安全網

<!-- 本任務動到：憲法原則 I.2（要經過人按「送出」才會跑）與 116 的擁有者規則（每個人只用自己的東西）。這是安全閘的放寬，依 CLAUDE.md 校準失敗 1：要重跑 base 拒絕的形狀，確認除了維護者准許的那一種，沒有其他形狀被放過。 -->

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| CS-01 | 原則 I.2：未經確認不得送出，MCP 路徑 | 例外 | 一般客戶端、A 用文字送出 | 不經任何「送出」，連呼叫 `launch` 三次（同樣參數） | 每次都是 pending 或「已有 pending」；hand-off 紀錄與工作佇列始終是 0 筆；只有本人按了送出，才會有工作 | 自動：新檔 |
| CS-02 | 原則 I.2：網頁路由也不得未經確認就送出 | 功能 | 登入的 A，網頁表單 POST /launch；路徑格在 readRoots 內 | 送出表單 | 只得到確認頁（303 到 /c/<id>），沒有工作；網頁表單仍只能選自己上傳資料夾裡的檔；既有網頁測試不改而通過 | 自動：`platform/tests/test_web_actions.py` 與新檔 |
| CS-03 | 原則 I.2 與 116；校準失敗 1：被放寬的只有維護者准許的那一種 | 例外 | 同一組輸入各在 base 與改動後執行：TC-011..TC-024 的每一種形狀、TC-038、116 的 params 形狀（B 的資料夾、連結、`..`、`~`、readRoots 之外） | 比較兩邊的結果 | 每一種在兩邊都被拒；唯一不同的形狀是「路徑格在 readRoots 內、不在 uploads 內」，從拒變成過；同一輸入被拒時，拒絕的字句也不得比 base 洩漏更多（沒有 B 的名字、路徑） | 自動：新檔（形狀清單寫死在測試裡，各自斷言被拒） |
