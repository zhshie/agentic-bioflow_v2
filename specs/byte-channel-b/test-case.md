# 測試案例：位元組通道（下）——代理把上傳的檔串流寫進使用者自己的雲端前綴、核對大小後刪暫存（byte-channel-b）

**規格**：`specs/byte-channel-b/plan.md`（本片沒有 spec.md，以 plan.md 與其兩段裁決為唯一來源，裁決二第 9 條已接受）　**總覽**：`test-case-overview.md`

名詞先講白：
- **代理**：跑在平台主機上、替使用者執行工作的小程式（`abf-station run`）。
- **工作 / put_upload**：平台交給代理的一張「把這個檔傳上雲端」的單子，單子上只寫參照（誰的檔、檔名、大小、要放哪），不帶檔案內容。
- **暫存檔**：使用者在網頁按上傳後，檔案先放在平台主機 `uploads/<擁有者>/` 的那一份。
- **前綴**：雲端 bucket 裡 `gs://<bucket>/uploads/<擁有者>/` 這個「資料夾」位置。代理只准寫進這裡。
- **假 gcloud**：測試用的假替身，不連網；記下收到什麼，照劇本回答。
- **canary**：測試故意塞進檔案內容與金鑰檔的獨特暗號，用來確認它不會漏到任何輸出。
- **posix 專用**：只能在 Linux／WSL 跑的案例（符號連結、真管道）。Linux CI 上必須實跑、不得被跳過；Windows 本機可跳過。

維護者原話（本合約的最終依據，案例直接用它）：
- 派工指令（2026-10-24）：「代理串流讀檔，不記位元組、不記金鑰；結果回報寫了幾個位元組與 gs:// 路徑；只准寫 `gs://<workDir bucket>/uploads/<owner>/`，代理側要再檢查一次；測試用假 gcloud（不連網）與現有站台測試工具」。
- 裁決回覆（2026-10-25）：「1.會慢半天就不用 2.照你建議」＝①不加額外確認（使用者在已登入頁面按上傳就是那一次確認）；②允許先暫存在平台主機，傳完且雲端大小與本機相同就刪本機那份，不符或失敗就保留。
- ADR 0010 Decided 2：代理的第一個寫入；路徑白名單＝只讀 `uploads/<擁有者>/` 之下；大小上限 2 GB。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、被竄改、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下、保留）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

驗證方式：「自動」＝`platform/tests/test_byte_channel_b.py`（每個測試在註解寫它的 TC 編號與計畫內的 BB 編號）或名稱已列的既有測試檔；「手動」＝照計畫「通例」，由 executor 把 `git diff --stat`、`git diff --name-only` 與相關 diff 貼進 `specs/byte-channel-b/ledger.md`，verifier 自己重跑核對。

## User Story 1 — 代理認得 put_upload，把檔案串流傳到使用者自己的前綴（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | BB-01；計畫 C | 功能 | 代理程式碼載入 | 看代理認得的工作種類清單 `JOB_KINDS` | 清單最後一項是 `put_upload`；原有六種不變、順序不變 | 自動 |
| TC-002 | BB-01；計畫 C | 功能 | 平台側 `jobs.enqueue_put_upload` 排出一張工作 | 比對該工作的鍵集合與代理的 `ARG_KEYS["put_upload"]` | 兩邊逐字相同，都是 `ce`、`owner`、`name`、`size`、`dest` 五個（測試從平台排出的工作讀鍵，不重抄） | 自動 |
| TC-003 | BB-02 | 例外 | 一張 put_upload 工作，五個鍵齊全再多帶一個 `path` | 交給代理處理 | 被拒絕（refused），訊息含「不支援」或 `not supported`；gcloud 一個字節都沒啟動 | 自動 |
| TC-004 | BB-02 | 例外 | 一張 put_upload 工作，少帶其中一個鍵 | 交給代理處理 | 被拒絕（refused），訊息白話說缺東西；gcloud 沒啟動 | 自動 |
| TC-005 | BB-03；裁決二 6 | 例外 | 一張種類是不認得的工作 | 交給代理處理 | 被拒絕；訊息把 `JOB_KINDS` 的每一種都列出來、其中含 `put_upload`（不釘個數，讀清單來比） | 自動 |
| TC-006 | BB-04；派工指令；裁決二 5 | 功能 | Google Batch 環境，workDir `gs://lab-bucket/work`、project `lab-project-1`；擁有者 alice；`uploads/alice/reads.fq` 為 3 MiB + 17 位元組的隨機內容；工作 size＝3145745、dest＝`gs://lab-bucket/uploads/alice/reads.fq`；假 gcloud 的 cp 成功，雲端大小回 3145745 | 代理處理這張工作 | 狀態 done；結果 `ok` 為真、`bytes`＝3145745、`path`＝`gs://lab-bucket/uploads/alice/reads.fq`、訊息為「已上傳 gs://lab-bucket/uploads/alice/reads.fq（3145745 位元組）；平台主機上的暫存檔已刪除」（BB-04 原文寫於裁決二之前，多出的 message 以裁決二 5 為準） | 自動 |
| TC-007 | BB-04；派工指令「串流讀檔」 | 功能 | 同 TC-006 | 把假 gcloud 收到的每一塊位元組依序串起來，與原檔比對 | 逐位元組相同；送完後 stdin 已關閉（`closed` 為真）；沒有被殺（`killed` 為假） | 自動 |
| TC-008 | BB-05；計畫 B-4 | 功能 | 同 TC-006 | 看代理啟動 gcloud 時交出的命令 | 命令剛好是清單 `["gcloud","storage","cp","-",dest,"--project","lab-project-1"]`（是清單，不是一整串字，沒有 shell） | 自動 |
| TC-009 | BB-05；憑證規則 | 功能 | 同 TC-006，金鑰檔路徑經 `ABF_STATION_GCP_CREDENTIALS` 設定，環境裡另外放了 `ABF_` 開頭的變數與 `GOOGLE_APPLICATION_CREDENTIALS` | 看代理交給 gcloud 的環境變數 | 有 `CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE` 且指向該金鑰檔；沒有任何 `ABF_` 開頭的變數；沒有 `GOOGLE_APPLICATION_CREDENTIALS` | 自動 |
| TC-010 | BB-05；計畫 B-4 | 功能 | 同 TC-009 | 檢查傳給 gcloud 的所有命令（cp 與之後的 describe） | 金鑰檔路徑字串不在任何一條命令清單裡 | 自動 |
| TC-011 | BB-06 | 功能 | 一個 40 MiB 的重複內容檔，size 吻合 | 代理處理；記下假 gcloud 每次 `write` 收到的長度 | 每一塊都 ≤ 1 MiB（1,048,576 位元組） | 自動 |
| TC-012 | BB-06；派工指令「不落地」 | 功能 | 同 TC-011 | 處理期間量記憶體峰值（tracemalloc） | 峰值遠小於檔案大小，例如小於 8 MiB（證明沒有一次讀整個檔） | 自動 |
| TC-013 | BB-07（裁決二之後的解讀） | 功能 | 同一個名字的檔；第一次成功後本機檔會被刪，所以第二次之前先把同內容檔放回 `uploads/alice/` | 連續傳兩次 | 兩次都是 done；兩次的命令都沒有 `--no-clobber`（同名物件會被覆寫） | 自動 |
| TC-014 | BB-24（posix 專用） | 功能 | `tmp_path/bin` 放在 PATH 最前面，裡面有一支假 gcloud 腳本：把命令寫到 `argv.txt`、把 stdin 用 `cat > received.bin` 收下、`exit 0`；一個 5 MiB 隨機檔 | 用真的 `site.start_fed` 管道處理這張工作 | `received.bin` 與原檔位元組完全相同 | 自動 |
| TC-015 | BB-24（posix 專用） | 功能 | 同 TC-014 | 讀 `argv.txt` 與結果 | `argv.txt` 逐行就是 TC-008 的那份清單；結果 `bytes`＝5242880 | 自動 |
| TC-016 | BB-25（posix 專用）；裁決二 | 例外 | 假 gcloud 讀了 1 KiB 就 `exit 1`，並在 stderr 印一行 | 代理處理一個較大的檔 | 整個測試在 20 秒內結束（沒有卡死）；結果 `ok` 為假；沒有任何 `BrokenPipeError` 以未處理例外的形式洩漏出去 | 自動 |
| TC-017 | BB-26（posix 專用） | 例外 | 假 gcloud 睡 60 秒、完全不讀 stdin；代理的逾時被縮成 1 秒（測試用的參數或 `ABF_STATION_` 開頭的環境變數） | 代理處理 | 子程序被殺掉（`poll()` 或 `pgrep` 證明已結束）；結果 `ok` 為假且訊息含「逾時」 | 自動 |
| TC-018 | BB-27（posix 專用） | 功能 | 假 gcloud 在 stderr 灌 1 MiB 文字後 `exit 0`（驗證 stderr 走暫存檔、不會塞住管道） | 代理處理 | 成功（cp 這一步不卡住）；結果訊息不含那段文字 | 自動 |
| TC-019 | BB-18 上限邊界 | 功能 | size＝2_000_000_000（剛好上限）；用注入的假 fstat 與假讀取器回等長的零，不造 2 GB 檔；假 gcloud 吞資料、雲端大小回 2000000000 | 代理處理 | 通過大小檢查；假讀取器被讀約 1,908 次（2×10^9 ÷ 1 MiB 進位）；結果成功、`bytes`＝2000000000 | 自動 |
| TC-020 | BB-31 | 功能 | 平台側用 `jobs.enqueue_put_upload` 排工作（alice 的可用環境、`FakePlatform` 或 `Inproc`） | `claim` → 代理 `handlers.handle` → `take_result` → `wait_for_result` | 回 `{"ok": True, "result": {"bytes": …, "path": "gs://lab-bucket/uploads/alice/…", …}}`；假 gcloud 收到的位元組與原檔相同 | 自動 |

## User Story 2 — 傳完核對雲端大小，相符才刪暫存檔（優先度 P1；維護者「2.照你建議」）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-021 | 裁決二 3 | 功能 | cp 成功 | 看 cp 之後代理又啟動的那一條命令與其限制 | 命令剛好是清單 `["gcloud","storage","objects","describe",dest,"--project",<project>,"--format=value(size)"]`；逾時上限 60 秒；環境變數與 cp 是同一份（沒有 `ABF_` 開頭、沒有 `GOOGLE_APPLICATION_CREDENTIALS`、有 `CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE`）；金鑰路徑不在命令裡 | 自動 |
| TC-022 | 裁決二 3 | 功能 | cp 成功；describe 回 `  3145745\n`（前後有空白與換行的純數字） | 代理處理 | 視為取得大小 3145745（去頭尾空白後是純十進位數字即可），走「相符就刪」那條 | 自動 |
| TC-023 | 裁決二 4、5；維護者 2 | 功能 | cp 成功；雲端大小＝開檔時檔案大小＝串流寫出的位元組數 | 代理處理 | 本機 `uploads/<擁有者>/<檔名>` 已不存在；結果 `ok` 為真，訊息含「平台主機上的暫存檔已刪除」 | 自動 |
| TC-024 | 裁決二 4；Safety Net 第 1 條 | 功能 | `uploads/alice/` 下除了要傳的檔，還有 `other.fq`；另有 `uploads/bob/x.fq` | 同 TC-023 傳完 | 只有被傳的那一個檔被刪；`other.fq`、`bob/x.fq` 內容與修改時間不變；`uploads/alice/` 資料夾本身仍在（即使變空） | 自動 |
| TC-025 | 裁決二 5 | 例外 | cp 成功，但雲端大小回的數字與本機檔大小不同 | 代理處理 | 結果 `ok` 為假；訊息為「雲端物件大小與本機不符，暫存檔保留，請重新上傳」；本機檔仍在、位元組不變 | 自動 |
| TC-026 | 裁決二 3、5 | 例外 | cp 成功，但 describe 回傳碼非 0 | 代理處理 | 結果 `ok` 為真；訊息為「已上傳 <dest>（N 位元組），但沒能核對雲端大小；暫存檔保留」；本機檔仍在 | 自動 |
| TC-027 | 裁決二 3、5 | 例外 | cp 成功，但 describe 逾時（拋 `TimeoutError`） | 代理處理 | 同 TC-026：`ok` 為真、訊息含「沒能核對雲端大小；暫存檔保留」；本機檔仍在 | 自動 |
| TC-028 | 裁決二 3 | 例外 | cp 成功；describe 輸出不是純十進位數字，逐一試：空字串、`abc`、`3145745 bytes`、`-5`、`1e6` | 代理處理 | 每一種都算「取不到」：同 TC-026 的結果與訊息；本機檔仍在 | 自動 |
| TC-029 | 裁決二 4 | 例外 | cp 與核對都成功，但在刪除之前，該路徑上的檔被換成另一個新檔（不同的檔案身分） | 代理處理 | 不刪；結果 `ok` 為真，訊息為「已上傳 <dest>（N 位元組）；暫存檔沒刪掉，請管理者清理」；那個新檔完好無損 | 自動 |
| TC-030 | 裁決二 4（posix 專用） | 例外 | cp 與核對成功，但刪除之前該路徑被換成指向資料夾外某檔的符號連結 | 代理處理 | 連結和它指向的檔都沒被刪；結果同 TC-029（`ok` 為真、「沒刪掉，請管理者清理」） | 自動 |
| TC-031 | 裁決二 5（posix 專用） | 例外 | cp 與核對成功，但刪除會失敗（例如擁有者資料夾唯讀） | 代理處理 | 不丟出例外；結果 `ok` 為真，訊息為「…暫存檔沒刪掉，請管理者清理」 | 自動 |
| TC-032 | 裁決二 5 | 例外 | gcloud cp 回傳碼非 0 | 代理處理 | 結果 `ok` 為假；不再執行 describe；本機檔仍在、位元組與修改時間不變 | 自動 |
| TC-033 | BB-19 | 例外 | 傳到一半，檔案被截短或加長（假 gcloud 的 `write` 內偷改檔案，或假讀取器多回一塊／少回一塊） | 代理處理 | 狀態 error、`ok` 為假；假 gcloud 被殺（`killed` 為真）；`bytes` 是已餵出的數目；不跑 describe；本機檔保留 | 自動 |
| TC-034 | BB-23 | 例外 | 假 gcloud 等待結束時丟 `TimeoutError` | 代理處理 | 狀態 error、訊息含「逾時」；假 gcloud 被殺；本機檔保留 | 自動 |
| TC-035 | 裁決 6 | 例外 | 傳輸中途被中止（例如 TC-033 或 TC-034 的情況） | 看結果訊息 | 訊息白話說已中止，並提醒「bucket 上可能需要檢查 <dest>」 | 自動 |
| TC-036 | 裁決 6；裁決二 2 | 不在範圍 | 同 TC-033／TC-034／TC-032 的失敗情境 | 記下代理總共啟動過哪些 gcloud 命令 | 只有 cp（最多再加一次 describe）；沒有任何刪除 bucket 物件的命令（沒有 `rm`、`delete`）——中止只殺子程序 | 自動 |

## User Story 3 — 代理自己再檢查一次：目的地、檔案、大小、金鑰（優先度 P1；派工指令「代理側要再檢查一次」）

以下除特別說明外，每一條的共同預期：結果是被拒絕或失敗、**gcloud 一個字節都沒啟動**（假 gcloud 的建立次數為 0）、本機檔沒被動也沒被刪。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-037 | BB-08 | 例外 | 擁有者 alice，工作的 `dest` 是別人的前綴 `gs://lab-bucket/uploads/bob/reads.fq` | 代理處理 | 被拒絕（refused） | 自動 |
| TC-038 | BB-09 | 例外 | `dest` 是別的 bucket：`gs://other-bucket/uploads/alice/reads.fq` | 代理處理 | 被拒絕 | 自動 |
| TC-039 | BB-10 | 例外 | `dest` 逐一試：`gs://lab-bucket/work/x`、`gs://lab-bucket/uploads/reads.fq`、`gs://lab-bucket/uploads/alice`（沒有檔名）、`gs://lab-bucket/uploads/alice/` | 代理處理 | 每一個都被拒絕 | 自動 |
| TC-040 | BB-11 | 例外 | `dest` 逐一試：`gs://lab-bucket/uploads/alice/../bob/x`、`gs://lab-bucket/uploads/alice/%2e%2e`（照字面當一般名字，但因必須逐字等於預期值，仍被拒）、含控制字元、`s3://…`、`https://…`、前後多空白 | 代理處理 | 每一個都被拒絕 | 自動 |
| TC-041 | BB-12；裁決 3 | 例外 | `dest` 本身合法，但與 `owner`、`name` 算出的預期位置不同（name 是 `a.fq`、dest 結尾是 `b.fq`） | 代理處理 | 被拒絕，訊息為「目的地不在你自己的上傳前綴裡」的意思 | 自動 |
| TC-042 | BB-13 | 例外 | 環境逐一換成：不是 Google Batch 型、workDir 不是 `gs://`、workDir 的 bucket 名不合規則 | 代理處理 | 每一個都被拒絕 | 自動 |
| TC-043 | BB-14 | 例外 | `owner` 或 `name` 逐一壞成：含 `/`、含 `\`、含 `..`、含 NUL、空字串、256 字元、非字串 | 代理處理 | 每一個都被拒絕 | 自動 |
| TC-044 | BB-14；計畫 B-3 | 例外 | 同 TC-043，壞值裡放一個獨特標記字串 | 看被拒絕的訊息 | 訊息只說哪一項不對，不回顯工作裡的原文（找不到那個標記字串） | 自動 |
| TC-045 | BB-32；派工指令「代理側要再檢查一次」 | 例外 | 用平台的 `enqueue_put_upload` 正常排工作後，直接改資料庫 `args_json`，把 `dest` 改成 bob 的前綴 | `claim` → 代理處理 → `take_result` | 代理拒絕、平台記為 refused；假 gcloud 未建立（證明代理這道牆不靠平台） | 自動 |
| TC-046 | 跨使用者讀（專長守則 backend） | 例外 | 擁有者 alice，`name` 是 `../bob/reads.fq`，`uploads/bob/reads.fq` 真實存在 | 代理處理 | 被拒絕；bob 的檔從沒被開啟或讀取（沒有任何位元組送出）、沒被刪 | 自動 |
| TC-047 | BB-15 | 例外 | 代理的 `ABF_STATION_UPLOADS` 逐一是：沒設、相對路徑、不存在的路徑、一個檔案 | 代理處理 | 每一個都被拒絕，訊息含 `ABF_STATION_UPLOADS`（白話說這個代理沒有設定上傳資料夾） | 自動 |
| TC-048 | BB-16 | 例外 | 要傳的檔：不存在；或是一個資料夾 | 代理處理 | 兩者都被拒絕 | 自動 |
| TC-049 | BB-16（posix 專用） | 例外 | `uploads/alice/reads.fq` 是指向別處檔案的符號連結 | 代理處理 | 被拒絕；連結指向的檔沒被讀 | 自動 |
| TC-050 | BB-16（posix 專用） | 例外 | `uploads/alice` 本身是指向上傳資料夾以外某資料夾的捷徑 | 代理處理 | 被拒絕；捷徑另一頭的檔沒被讀 | 自動 |
| TC-051 | BB-17 | 例外 | 工作說 size＝100；實際檔 101 位元組（另試實際 99 位元組） | 代理處理 | 兩種都被拒絕，訊息含「重新上傳」 | 自動 |
| TC-052 | BB-18 | 例外 | 工作的 size 逐一是：0、-1、`True`、`"5"`、2_000_000_001 | 代理處理 | 每一個都被拒絕 | 自動 |
| TC-053 | BB-20 | 例外 | 電腦上找不到 gcloud（`shutil.which` 回 None） | 代理處理 | 結果是 error，訊息說「沒裝 gcloud」；假 gcloud 未建立 | 自動 |
| TC-054 | BB-21；計畫 B-3-7 | 例外 | 金鑰檔不存在；或指到的是資料夾 | 代理處理 | 結果是 error、`ok` 為假，訊息為「找不到金鑰檔（路徑不顯示內容）」的意思，且不顯示金鑰路徑；假 gcloud 未建立 | 自動 |
| TC-055 | BB-21；裁決 5 | 例外 | 金鑰檔存在，內容是無法解析的垃圾（含 canary） | 代理處理（走完成功路徑） | 金鑰檔從未被打開讀取（`open` 呼叫記錄中沒有它）；垃圾內容不影響結果，也不出現在任何輸出 | 自動 |
| TC-056 | 計畫 B-3 | 例外 | 任一條被拒絕的路徑（TC-037～TC-052 各取一） | 事後檢查本機 `uploads/` | 檔案仍在、位元組與修改時間不變（拒絕絕不刪檔） | 自動 |
| TC-057 | BB-22 | 例外 | 假 gcloud 回傳碼非 0，輸出含：一段 `〔私鑰BEGIN標頭，測試裡用拼接字串組出，文件不寫全文〕…〔私鑰END標頭，測試裡用拼接字串組出，文件不寫全文〕`、一個 40 字元的長字串、一條 `/home/alice/uploads/...` 路徑 | 代理處理 | 結果是 error、`ok` 為假；把整個結果轉成字串後，找不到那三樣原文；輸出片段最多 300 字元；訊息只用檔名、不出現本機 uploads 路徑 | 自動 |
| TC-058 | BB-22 | 例外 | 同 TC-057 | 看結果裡原本是金鑰區塊與長字串的位置 | 被換成 `[hidden]` | 自動 |

## User Story 4 — 不外洩、不亂啟動程式、不留日誌（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-059 | BB-28；派工指令「不記位元組、不記金鑰」 | 例外 | 檔案內容含 canary A；假金鑰檔含 canary B；分別跑成功路徑（TC-006）、傳到一半被改（TC-033）、gcloud 失敗並印出金鑰（TC-057）三種 | 檢查 stdout／stderr（capsys）與代理的日誌回呼（`ctx.site.log` 等） | 兩個 canary 都找不到；代理沒有寫任何日誌 | 自動 |
| TC-060 | BB-28 | 例外 | 同 TC-059 三種路徑 | 檢查代理回的結果 JSON，及 `jobs.clean_result("put_upload", result)` 的輸出 | 兩個 canary 都找不到 | 自動 |
| TC-061 | BB-28 | 例外 | 同 TC-059；用 `enqueue_put_upload` 排工作並經假平台 `take_result` 走完 | 把平台資料庫整份傾印後搜尋 | 兩個 canary 都找不到 | 自動 |
| TC-062 | BB-28 | 例外 | 同 TC-059 | 在 TC-059～TC-061 檢查過的所有位置搜 `private_key` | 都找不到 | 自動 |
| TC-063 | BB-29 | 功能 | 讀 `platform/abf_station/put_upload.py` 原始碼 | 掃描 | 不含 `print(`、`.log(`、`logging`、`subprocess`、`shell=True`、`os.system`、`while`、`Thread(`、`listen`、`bind`、`input(`、`daemon`、`google.cloud`；含 `# Nothing existing:`（≥15 字）；不含連續的字串 `storage cp` | 自動 |
| TC-064 | BB-30 | 功能 | 讀 `abf_station/` 全部原始碼 | 找哪些檔有 `import subprocess` | 只有 `site.py` 一個；`put_upload.py` 沒有；`test_station_static.py` 原封不動仍綠 | 自動 |
| TC-065 | 作法 A-2、A-3；TC-091 | 功能 | 讀 `site.py` | 掃描 `Fed` 與 `start_fed` 的程式碼，及檔內字樣 | `Fed` 與 `start_fed` 沒有 print、沒有日誌呼叫、沒有保留寫入過的位元組；沒有 `shell=True`；`shlex.quote` 與 `on_site.sh` 字樣仍在 | 自動 |
| TC-066 | 作法 A-1 | 例外 | `start_fed` 找不到程式或沒權限（丟 `OSError`） | 代理處理 | 結果是 error，白話訊息；沒有未處理例外；不露出堆疊或本機路徑 | 自動 |
| TC-067 | 作法 A-2 | 功能 | 一個 `Fed` 物件（真管道，posix） | `close_input()` 連叫兩次；`kill()` 連叫兩次 | 兩者重複呼叫都安全、不丟例外；`kill()` 後子程序已結束、暫存檔已關閉 | 自動 |
| TC-068 | 作法 A-2 | 功能 | 一個子程序輸出超過 2000 字元 | 呼叫 `wait(timeout)` | 回 `(回傳碼, 輸出文字)`，輸出文字最多前 2000 字元；逾時時丟 `TimeoutError` | 自動 |
| TC-069 | 計畫 A-3；範圍「不做」 | 功能 | 讀 `site.py` 與 `put_upload.py` 的 import | 檢查新增的 import | `site.py` 唯一新增的 import 是 `tempfile`（可有可無其他已存在的）；沒有任何雲端函式庫；既有的 TC-083／TC-114／TC-085 測試仍綠 | 自動 |

## User Story 5 — 範圍與維護者的決定寫進 ADR（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-070 | 範圍：檔案（裁決二 1） | 功能 | 實作完成 | 跑 `git diff --name-only <base>` | 只有 5 個檔：`platform/abf_station/put_upload.py`、`platform/abf_station/site.py`、`platform/abf_station/handlers.py`、`platform/tests/test_byte_channel_b.py`、`docs/adr/0010-chat-keys-byte-channel-studio-embedding.md`（`specs/byte-channel-b/` 內的 ledger 等工作記錄不算產品改動） | 手動（ledger 貼輸出，verifier 重跑） |
| TC-071 | 完成標準 | 功能 | 實作完成 | 看 `site.py` 的 `git diff` | 只有新增（`Fed`、`start_fed`、檔首說明）；`run_fixed`、`start_detached`、`Site.call` 逐行沒動 | 手動 |
| TC-072 | 完成標準；計畫 C | 功能 | 實作完成 | 看 `handlers.py` 的 `git diff` | 只有 import、`JOB_KINDS`、`ARG_KEYS`、一支 `put_upload` 分派（放在 `read_task_log` 之後）、檔首一句說明；其餘沒動 | 手動 |
| TC-073 | 「必須更新的既有斷言：沒有」 | 功能 | 實作完成 | 看 `git diff --stat <base>` 中的測試檔 | 沒有任何既有測試檔被改（斷言沒被放寬、沒被跳過、期望值沒被改成配合新輸出） | 手動 |
| TC-074 | 完成標準 | 功能 | 實作完成 | 跑既有的 `test_station_static.py`、`test_cloud_upload.py`、`test_scope.py`、`test_gcb_ce.py`、`test_gcb_launch.py`、`test_station_fakeplatform.py`、`test_byte_channel_a.py`、`test_run_diag_tools.py` | 全部原封不動仍綠 | 自動 |
| TC-075 | 裁決 C；裁決二 1 | 功能 | 實作完成 | 打開 `docs/adr/0010-…md` | 有新的一節，標題是「## 2026-10-25 修正」 | 手動 |
| TC-076 | 裁決 C | 功能 | 同 TC-075 | 讀那一節內容 | 明說兩點：①使用者按上傳就是確認；②允許先暫存在平台主機，傳完核對大小後刪除 | 手動 |
| TC-077 | 裁決 C；維護者原話 | 功能 | 同 TC-075 | 讀那一節內容 | 逐字引用維護者原話「1.會慢半天就不用 2.照你建議」 | 手動 |
| TC-078 | 裁決二 1「只新增一段」 | 功能 | 同 TC-075 | 看 ADR 檔的 `git diff` | 只有新增行，原有文字（包含 Decided 2 的逐字原文）一個字都沒改 | 手動 |
| TC-079 | 裁決二 7；專長守則（migration） | 功能 | 實作完成 | 看 diff 中有無 `abf_platform/`（含 `store.py`、`jobs.py`）、`gcb_preflight.py`、`agent.py`、`pyproject.toml`、`constraints.txt`、`hooks/*`、`tests/run_all.sh`、`.github/*`、`abf_launch/build.py`、`abf_station/launch.py` | 這些都沒動；因此沒有資料結構變動、不需要 migration（PR 說明或 ledger 寫明這個理由） | 手動 |
| TC-080 | 維護者「1.會慢半天就不用」；裁決 A | 不在範圍 | 代理收到一張五鍵齊全的 put_upload 工作 | 看代理的處理過程與工作形狀 | 沒有任何額外的確認步驟：工作鍵集合仍是五個（沒有 confirm 之類的鍵）、代理不等任何確認就處理；也沒有新的確認憑證種類 | 自動 |
| TC-081 | 裁決二 2「仍不做」 | 不在範圍 | 任一成功的傳輸 | 檢查 cp 與 describe 的所有命令 | 沒有 `--no-clobber`、沒有續傳選項、沒有 `-I`（多檔）、沒有校驗和／雜湊選項；代理也沒有計算任何雜湊 | 自動 |
| TC-082 | 「不做」：預檢加寫入探測 | 不在範圍 | 實作完成 | 看 `gcb_preflight.py` 的 diff 與既有預檢測試 | `gcb_preflight.py` 沒有改動（只被 import）；預檢仍只做讀取，沒有新增寫入探測；既有預檢測試仍綠 | 手動 |
| TC-083 | 完成標準；環境事實「查不到」 | 不在範圍 | PR 說明或 ledger | 讀其中關於真 bucket 的敘述 | 明寫「尚未用真 bucket 驗過」，並記下兩個未驗證項（2 GB 串流的記憶體與逾時行為；中途被殺後 bucket 是否留下殘缺物件）；網頁／MCP／HTTP 路由、把檔放進 `uploads/` 都不在本片 | 手動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-084 | Safety Net 第 1 條：絕不刪使用者的來源資料（裁決二 8 ②） | 例外 | 把 `uploads/alice/` 內唯一的檔傳完（成功且核對相符） | 看事後磁碟 | 被刪的只有那一個一般檔案；沒有刪資料夾；沒有碰 `uploads/` 以外任何路徑；`uploads/alice/` 資料夾還在 | 自動 |
| TC-085 | Safety Net 第 4 條（寫入工具要有人確認）與裁決二 8 ① | 例外 | 平台的一般排工作入口 `_enqueue` | 用一般入口直接排 kind＝`put_upload` 的工作 | 被拒絕（只能走 `enqueue_put_upload`，訊息提到上傳只能走專用入口） | 自動 |
| TC-086 | Safety Net 第 4 條與裁決二 8 ① | 例外 | 平台的 MCP 工具清單 | 列出所有工具名稱 | 沒有任何工具名稱含 `upload`（不分大小寫）——聊天或 PAT 沒辦法觸發上傳 | 自動 |
| TC-087 | 不變式：指令文字掃描（`test_cloud_upload.py` TC-099、TC-101） | 功能 | 實作完成 | 跑 `test_cloud_upload.py`，並看 `put_upload.py` | `test_cloud_upload.py` 沒被改且仍綠；連續字串 `storage cp` 只出現在 `cloud_store.py`；`put_upload.py` 用的是各自獨立的 argv 元素（與 `gcb_preflight.py` 既有做法同形） | 自動 |
| TC-088 | 專長守則 backend：錯誤訊息與日誌 | 例外 | 本檔所有被拒絕與失敗的路徑 | 逐一讀訊息 | 每一則都說明發生什麼事與該怎麼辦（例如「請重新上傳」「找不到金鑰檔」「沒裝 gcloud」）；沒有堆疊、SQL、金鑰檔路徑、本機 uploads 路徑 | 自動 |
| TC-089 | 專長守則 backend：確認管道（維護者已明示接受的偏離，裁決 A 與裁決二 8） | 功能 | 實作完成 | 讀 ledger 與 PR 說明 | 寫明為何不違反憲法：①憲法 I.2 承認的人工通道含「平台確認頁、同一個已登入的使用者」，使用者在頁面按上傳即那次確認，put_upload 只能經 `enqueue_put_upload` 排入（TC-085）、MCP 與 PAT 沒有上傳工具（TC-086）；②`uploads/` 內是傳輸用的暫存副本、不是來源資料，且雲端核對相符才刪（TC-023）。verifier 不因「每個寫入要確認」判 FAIL，但此判斷列入「需要人看的事」 | 手動 |
