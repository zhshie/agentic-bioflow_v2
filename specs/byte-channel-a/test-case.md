# 測試案例：網頁上傳檔案到雲端（a：平台端工作種類 put_upload）

**規格**：`specs/byte-channel-a/plan.md`（含「裁決」「裁決（2026-10-25 維護者回覆）」「裁決二」；與上文衝突時以裁決二為準）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做。

名詞：**工作（job）**＝平台排給「代理」（站上替平台做事的程式）去做的一件事；**put_upload**＝本次新增的工作種類，意思是「把使用者上傳資料夾裡的某一個檔寫到他自己的雲端 bucket 前綴」；**前綴**＝`gs://<bucket>/uploads/<使用者名>/` 這一段位置；**遷移（migration）**＝舊資料庫升級到新結構時，原有資料一筆不丟。

**共同約定**：除非另寫，自動測試放在 `platform/tests/test_byte_channel_a.py`，用暫存資料夾當平台資料夾、假的檔案資訊（不真的造 2 GB 檔）、不連網、不啟動任何程式、不讀任何金鑰檔。凡「被拒絕」的 TC，都同時要求：丟出的是平台的拒絕（`JobRefused`）、**資料庫的工作數不變**（什麼都沒排）、訊息是白話。「種類清單」以 base（目前 v3）既有清單照原順序，末尾加 `put_upload`（目前 v3 為七種，加完八種；測試不得把「剛好幾個」寫死成與 base 不符的數字）。

維護者原話對照（出題依據，逐字）：
- 派工指令（2026-10-24）：「工作只帶 uploads/ 裡那份檔的參照，不把位元組放進工作的 JSON；大小上限 2 GB；只准寫 `gs://<workDir bucket>/uploads/<owner>/`；結果回報寫了幾個位元組與 gs:// 路徑；不得動 hooks/*、tests/run_all.sh、.github/*、actions/__init__.py、abf_launch/build.py、abf_station/launch.py；接到網頁／MCP 的線不在本任務（cloud-upload-wire）」→ TC-023～036、060～069、087～089、095。
- 10-18 裁示：「上傳 >2 GB 改給指令」→ TC-034、057、058。
- replan 第 16 點：「雲端上傳＝平台代傳到使用者自己的 bucket、不落地…大檔給 gsutil 指令」→ 目的地只能是呼叫者自己的前綴：TC-027、039～042。
- 憲法原則 2（TC-071）與 TC-061：TC-080、082、083、085。
- 維護者 2026-10-25：「1.會慢半天就不用 2.照你建議」→ 不加確認憑證種類（TC-004、090）；傳完刪本機檔與修 ADR 0010 屬 -b，本任務不做（TC-091、092）。

## User Story 1 — 資料庫放行新種類，並替舊資料庫遷移（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 A-1；BA-01 | 功能 | 全新的 `platform.db` | 直接插入一筆種類為 `put_upload`、不帶確認憑證（`confirmation_id` 空）的工作 | 插入成功 | 自動 |
| TC-002 | 作法 A-1；BA-01 | 例外 | 同上 | 分別插入種類為 `put`、`upload`、`put_uploads`、空字串的工作 | 四筆都被資料庫拒絕（`IntegrityError`），工作數不變 | 自動 |
| TC-003 | 作法 A-1；裁決二 1 | 功能 | 全新的 `platform.db` | 讀出 `jobs` 表 `kind` 的 CHECK 清單 | 清單＝base 既有種類照原順序（目前：preflight、list_site_files、launch_nextflow、cancel_run、fetch_run_records、read_task_log、clean_work），**最後一項**是 `put_upload`，沒有別的新增 | 自動 |
| TC-004 | 作法 A-1；裁決 4、維護者「1.會慢半天就不用」 | 例外 | 全新的 `platform.db` | 插入種類為 `launch_nextflow`、`cancel_run`、`clean_work`、**不帶**確認憑證的工作 | 三筆都被資料庫拒絕（需確認的規則沒被放寬） | 自動 |
| TC-005 | 作法 A-3、A-4；BA-03；裁決二 1 | 功能 | 舊資料庫：`jobs` 表的 CHECK 缺 `put_upload`（其餘種類都在），內有 3 筆工作（一筆帶確認憑證） | 用 `connect_state` 開啟 | 3 筆工作的每個欄位都與升級前逐欄相同，id 不變 | 自動 |
| TC-006 | 作法 A-3；BA-03 | 功能 | 同 TC-005 升級後 | 再新增一筆工作 | 新工作的 id 接在原最大 id 之後（原本最大 id 是 3 則新的是 4），自動編號計數有保留 | 自動 |
| TC-007 | 作法 A-3；BA-03 | 功能 | 同 TC-005 升級後 | 插入種類 `put_upload`、不帶確認憑證的工作 | 成功 | 自動 |
| TC-008 | 作法 A-3；BA-03 | 例外 | 同 TC-005 升級後 | 插入種類 `rm`、`launch`、空字串的工作 | 都被資料庫拒絕 | 自動 |
| TC-009 | 作法 A-3；BA-04 | 例外 | 同 TC-005 的舊資料庫；在遷移的「已複製」步驟（`store._migration_step`）丟出例外 | 用 `connect_state` 開啟 | 開啟失敗（例外照常往外丟）；舊的 `jobs` 表原樣還在，列數與內容不變 | 自動 |
| TC-010 | 作法 A-3；BA-04 | 功能 | 接續 TC-009，這次不丟例外 | 再用 `connect_state` 開啟 | 遷移成功，3 筆資料齊全，`put_upload` 可寫 | 自動 |
| TC-011 | 作法 A-3；BA-05 | 功能 | 已含全部種類（含 `put_upload`）的新資料庫 | `connect_state` 連開兩次 | 沒有重建：`sqlite_master` 裡 `jobs` 的 SQL 與各列的 rowid 兩次前後相同 | 自動 |
| TC-012 | 作法 A-3；BA-06 | 功能 | 更舊的資料庫（連 `read_task_log` 也沒有；即 `test_run_diag_tools.py` 的 `test_tc110_*` 造法） | `connect_state` 開啟 | 一次升到含 `put_upload` 的最新結構，舊 3 筆資料保留；`test_tc110_*` 原封不動仍綠 | 自動：`platform/tests/test_run_diag_tools.py`、本檔 |
| TC-013 | 作法 A-3；裁決二 1 | 功能 | 舊資料庫：CHECK **已有** `put_upload` 但**缺** `clean_work`（`test_cleanup_store.py` 的 `old_jobs()` 造法） | `connect_state` 開啟 | 照樣被遷移（判斷同時看 `read_task_log`、`clean_work`、`put_upload` 三者，缺任何一個都重建）；`test_cleanup_store.py` 的遷移測試仍綠 | 自動：`platform/tests/test_cleanup_store.py`、本檔 |
| TC-014 | 作法 A-4 | 功能 | 舊資料庫內 `confirmations`、`launches`、`compute_envs` 各有資料 | `connect_state` 開啟 | 這三張表的結構與資料升級前後完全相同（只重建了 `jobs`） | 自動 |

## User Story 2 — 種類表、期限與上限常數（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 作法 B-1；BA-07；裁決二 1 | 功能 | 無 | 讀 `jobs.KINDS` | 順序＝base 既有種類，**末項**是 `put_upload` | 自動 |
| TC-016 | 作法 B-1；BA-07；裁決二 1 | 功能 | 無 | 讀 `jobs.CONFIRMED` | 與 base 完全相同（目前：launch_nextflow→launch、cancel_run→cancel、clean_work→clean_work），**不含** `put_upload` | 自動 |
| TC-017 | 作法 B-1；BA-08；裁決 8 | 功能 | 沒設環境變數 | 呼叫 `jobs.deadline_seconds("put_upload")` | 得 3600 | 自動 |
| TC-018 | 作法 B-1；BA-08 | 功能 | 環境變數 `ABF_PLATFORM_DEADLINE_PUT_UPLOAD=7` | 同上 | 得 7 | 自動 |
| TC-019 | 作法 B-1；BA-08 | 例外 | 該環境變數分別設 `abc`、`-1`、`0` | 同上，逐一 | 每一個都得 3600（壞值退回預設） | 自動 |
| TC-020 | 作法 C；BA-09；10-18 裁示 | 功能 | 無 | 讀 `cloud_store.UPLOAD_LIMIT` | 等於 2,000,000,000（十進位位元組） | 自動 |
| TC-021 | 作法 C；BA-09 | 功能 | 無 | 比較 `cloud_store.UPLOAD_LIMIT` 與 `actions.datasets.WEB_UPLOAD_LIMIT` | 兩者相等 | 自動 |
| TC-022 | 裁決二 4 | 例外 | 一個可用的 Google Batch 環境與其代理在線 | 用泛用排隊函式 `jobs._enqueue(...)` 直接要求種類 `put_upload` | 被拒絕，訊息指向只能走專用入口；工作數不變 | 自動 |

## User Story 3 — 排隊成功：工作只帶「檔案的參照」（優先度 P1）

共同前置：使用者 alice（有使用者編號）、她的可用（`available`）Google Batch 環境 `gcb1`（代理在線，`workDir` 的 bucket 為某個已知名字）、`<uploads>/alice/reads.fastq.gz` 以假的檔案資訊回報為一般檔案、500 位元組。入口一律是 `jobs.enqueue_put_upload`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-023 | 作法 B-3；BA-10 | 功能 | 共同前置 | alice 對 `gcb1` 排 `reads.fastq.gz` | 回傳工作 id；資料庫該列 `kind='put_upload'`、`state='queued'`、`confirmation_id` 為空 | 自動 |
| TC-024 | 作法 B-1；BA-10 | 功能 | 同上，時鐘固定為 now | 同上 | 該列 `deadline_at` ＝ now + 3600 | 自動 |
| TC-025 | 作法 B-3 第 6 點；派工指令；BA-10 | 功能 | 同上 | 讀該列 `args_json` | 鍵的集合**剛好**是 `ce`、`owner`、`name`、`size`、`dest`，不多不少（沒有位元組、本機路徑、雜湊、網址原文之類的鍵） | 自動 |
| TC-026 | 作法 B-3；BA-10 | 功能 | 同上 | 讀 `args_json` 的值 | `owner`＝alice、`name`＝reads.fastq.gz、`size`＝500 | 自動 |
| TC-027 | 派工指令「只准寫 gs://<workDir bucket>/uploads/<owner>/」；裁決 2；BA-10 | 功能 | 同上 | 讀 `args_json` 的 `dest` | 剛好等於 `gs://<該環境 workDir 的 bucket>/uploads/alice/reads.fastq.gz` | 自動 |
| TC-028 | 作法 B-3；BA-10 | 功能 | 同上 | 讀 `args_json` 的 `ce` | 與 `compute_envs.snapshot` 對該環境給的內容相同（含 `workDir`；沒有金鑰檔路徑） | 自動 |
| TC-029 | 裁決 1；BA-11；專長守則（密鑰） | 功能 | 同上 | 把該列整列轉成字串，搜尋 `uploads_dir` 的本機路徑、`gcp-sa`、`private_key`、`/home` | 四者都找不到 | 自動 |
| TC-030 | 作法 B-1；BA-12 | 功能 | 同上已排隊；代理名＝該環境的代理 | 呼叫 `jobs.claim` | 取得的工作 `kind=="put_upload"`；結果裡**沒有** `confirmation` 鍵、**沒有** `run_token` 鍵 | 自動 |
| TC-031 | 作法 B-1；BA-12 | 功能 | 同 TC-030 | 同上 | `remaining` ≤ 3600；資料庫該工作變 `claimed` | 自動 |
| TC-032 | 裁決 5；BA-22 | 功能 | 共同前置 | 對同一個檔連續排兩次 | 兩次都成功、得到兩個不同工作 id（覆寫同名物件允許；不做「進行中就拒」） | 自動 |
| TC-033 | 作法 B-3 第 4 點；BA-21 | 功能 | 假的檔案資訊回報大小 1 位元組 | alice 排該檔 | 成功 | 自動 |
| TC-034 | 10-18 裁示「>2 GB 改給指令」；BA-21 | 功能 | 假的檔案資訊回報大小 2,000,000,000 位元組 | alice 排該檔 | 成功（剛好 2 GB 仍收），`args_json` 的 `size` 為 2000000000 | 自動 |
| TC-035 | 裁決 6；作法 B-3 第 4 點 | 功能 | 共同前置，但磁碟上**沒有**這個檔，只有注入的假檔案資訊回報「一般檔案、500 位元組」 | alice 排該檔 | 成功：平台只靠 `lstat` 取資訊，沒有打開檔案、沒有讀內容（磁碟上檔案不存在也不影響；原始碼中新函式沒有讀內容的 `open(`、雜湊） | 自動 |
| TC-036 | 裁決 2；作法 B-3 第 3 點 | 例外 | 無 | 檢查 `enqueue_put_upload` 的參數表，並嘗試傳入名為 `dest` 或 `url` 的參數 | 沒有任何可由呼叫者傳入網址的參數；硬傳會出錯而不是被採用 | 自動 |

## User Story 4 — 排隊被擋：自己的環境、自己的前綴、合格的檔（優先度 P1）

凡被擋，皆要求：工作數不變、訊息白話、**訊息不含使用者傳入的原文**（檔名、路徑）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-037 | 作法 B-3 第 1 點；BA-13 | 例外 | 共同前置 | `caller_user_id=None`（終端機，沒有使用者）排工作 | 被拒（沒有使用者就沒有「他自己的前綴」） | 自動 |
| TC-038 | 作法 B-3 第 1 點 | 例外 | 共同前置 | `caller_user_id` 傳字串 `"1"`（不是整數） | 被拒 | 自動 |
| TC-039 | 作法 B-3 第 2 點；replan 16；BA-14 | 例外 | alice 與 bob 都有使用者編號 | 用 alice 的編號、但 `owner_name` 填 `bob`（想寫進 bob 的前綴） | 被拒，訊息與「找不到計算環境」那一句**字面相同**（不說「名字不符」） | 自動 |
| TC-040 | 擁有者規則；BA-15 | 例外 | bob 有自己的環境 `bobenv` | alice 對 `bobenv` 排工作 | 被拒，訊息是「找不到計算環境」那一句 | 自動 |
| TC-041 | 擁有者規則；BA-15 | 例外 | 無 | alice 對根本不存在的環境排工作 | 被拒，訊息與 TC-040 字面相同（不透露別人的環境是否存在） | 自動 |
| TC-042 | 裁決二 5 | 例外 | bob 的環境 `bobenv`；一次「檔案存在」、一次「檔案不存在」 | alice 各排一次 | 兩次的拒絕訊息**字面相同**（都是「找不到」），不透露檔案是否存在；對不存在的環境同理 | 自動 |
| TC-043 | 作法 B-2；BA-16 | 例外 | alice 的環境是 Slurm 型（非 Google Batch） | 排工作 | 被拒，訊息含「Google Batch」 | 自動 |
| TC-044 | 作法 B-2；BA-17 | 例外 | alice 的 Google Batch 環境狀態為 `unsupported` | 排工作 | 被拒 | 自動 |
| TC-045 | 作法 B-2；BA-17 | 例外 | 狀態為 `disabled` | 排工作 | 被拒 | 自動 |
| TC-046 | 作法 B-2；BA-17 | 例外 | 狀態為 `unchecked`（尚未預檢） | 排工作 | 被拒，訊息說明要先預檢（含 `abf-platform ce preflight` 的提示） | 自動 |
| TC-047 | 作法 B-2；BA-17 | 例外 | 狀態為 `unavailable`，**用同一個環境逐一切換狀態**測 | 排工作 | 被拒，訊息含 "store a file"（`put_upload` 專用字樣） | 自動 |
| TC-048 | 作法 B-2；BA-17 | 功能 | 同一環境狀態切回 `available` | 排工作 | 成功（只有 `available` 才過） | 自動 |
| TC-049 | 作法 B-3 第 5 點；BA-18 | 例外 | 代理最後一次出現的時間超過 `offline_after` | 排工作 | 被拒，訊息含代理名並說明沒排進去 | 自動 |
| TC-050 | 作法 B-3 第 3 點；BA-19 | 例外 | 共同前置 | 檔名分別為 `""`、`"a/b"`、`"a\\b"`、`".."`、`"."`、含 NUL 字元、256 個字元、含換行 | 八種都被拒 | 自動 |
| TC-051 | 作法 B-3 第 3 點；BA-19 | 例外 | 同 TC-050 | 讀每個拒絕訊息 | 訊息不回顯檔名原文 | 自動 |
| TC-052 | 作法 B-3 第 4 點；BA-20 | 例外 | 檔案資訊回報「不存在」 | 排工作 | 被拒 | 自動 |
| TC-053 | 作法 B-3 第 4 點；BA-20 | 例外 | 檔案資訊回報是資料夾 | 排工作 | 被拒 | 自動 |
| TC-054 | 作法 B-3 第 4 點；BA-20 | 例外 | 檔案資訊回報是符號連結（捷徑；Windows 用注入的模式代替） | 排工作 | 被拒（不跟隨連結） | 自動 |
| TC-055 | 作法 B-3 第 4 點；BA-20 | 例外 | 檔案的真實位置（`realpath`）跑出 `uploads/alice` 之外 | 排工作 | 被拒 | 自動 |
| TC-056 | 作法 B-3 第 4 點；BA-21 | 例外 | 檔案大小 0 位元組 | 排工作 | 被拒，訊息說「空檔案，沒有東西可存」 | 自動 |
| TC-057 | 10-18 裁示；replan 16；BA-21 | 例外 | 檔案大小 2,000,000,001 位元組（多一個位元組） | 排工作 | 被拒（超過 2 GB 不收） | 自動 |
| TC-058 | 10-18 裁示「改給指令」；BA-21 | 例外 | 同 TC-057 | 讀拒絕訊息 | 訊息含 `cloud_store.big_file_command(...)` 給的那一行，即 `gcloud storage cp <你電腦上的資料夾>/* gs://<bucket>/uploads/alice/rawdata/` | 自動 |
| TC-059 | 專長守則（錯誤訊息） | 例外 | 把 TC-037～057 每一種拒絕的訊息收集起來 | 逐一檢查 | 每則都說明發生了什麼事；不含本機上傳資料夾路徑、SQL 語句、堆疊追蹤文字 | 自動 |

## User Story 5 — 代理回報的結果只收「寫了幾個位元組、寫到哪裡」（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 作法 B-4；派工指令「結果回報寫了幾個位元組與 gs:// 路徑」；BA-23 | 功能 | 無 | `clean_result("put_upload", {"ok": True, "bytes": 500, "path": "gs://b/uploads/alice/x"})` | 輸出剛好這三個鍵、值原樣 | 自動 |
| TC-061 | 作法 B-4；BA-23 | 功能 | 同上，另外多給 `stdout`、`key`、`text`、`entries`、`private_key` | 同上 | 這五個鍵都不在輸出裡 | 自動 |
| TC-062 | 作法 B-4；BA-24 | 例外 | `ok: True` 但**沒有** `bytes` | 同上 | 輸出 `ok` 為 `False` | 自動 |
| TC-063 | 作法 B-4；BA-24 | 例外 | `ok: True`，`bytes` 分別為 `True`、`-1`、`"500"`、`2_000_000_001` | 逐一清洗 | 每一個輸出的 `ok` 都為 `False`，且輸出沒有 `bytes` 鍵 | 自動 |
| TC-064 | 作法 B-4；BA-24 | 例外 | `ok: True`，`bytes` 合格，`path` 不是字串（如數字） | 同上 | 輸出 `ok` 為 `False` | 自動 |
| TC-065 | 作法 B-4；BA-24 | 例外 | `ok: True`，`bytes` 合格，**沒有** `path` | 同上 | 輸出 `ok` 為 `False` | 自動 |
| TC-066 | 作法 B-4；BA-25 | 功能 | `path` 為 1200 字的字串 | 同上 | 輸出的 `path` 被截到 1100 字以內 | 自動 |
| TC-067 | 作法 B-4；BA-25 | 功能 | `message` 為 5000 字 | 同上 | 輸出的 `message` 被截到 2000 字以內 | 自動 |
| TC-068 | 作法 B-4；BA-25 | 功能 | `error`、`note` 各 1000 字 | 同上 | 兩者都被截到 300 字以內 | 自動 |
| TC-069 | 作法 B-4 | 功能 | `ok: False`，帶 `message`，不帶 `bytes`／`path` | 同上 | 輸出 `ok` 為 `False`，`message` 保留（失敗的回報不因缺數字而丟失原因） | 自動 |
| TC-070 | 作法 B-4；BA-26 | 功能 | 一個 `claimed` 的 `put_upload` 工作 | 該環境的代理回 `done`＋合格結果（另夾帶 `stdout`） | 資料庫 `result_json` 是清洗後的內容，沒有 `stdout` | 自動 |
| TC-071 | 作法 B-5；BA-26 | 例外 | 同 TC-070 已回報過一次 | 同一代理再回一次 | 回 409，原結果不變 | 自動 |
| TC-072 | 作法 B-5；BA-26 | 例外 | 一個 `claimed` 的 `put_upload` 工作 | **別的**代理回報 | 回 403，工作狀態與結果不變 | 自動 |
| TC-073 | 作法 B-5；BA-26 | 例外 | 一個 `claimed` 的 `put_upload` 工作，已過期限 | 代理回報 | 回應是 `late`，工作變 `expired`（與其他種類一致） | 自動 |
| TC-074 | 作法 B-4 | 功能 | 無 | `clean_result` 分別給 `bytes: 0` 與 `bytes: 2_000_000_000`（`ok: True`、`path` 合格） | 兩者的 `bytes` 都保留、`ok` 仍為 `True`（邊界值合格） | 自動 |

## User Story 6 — 既有行為不被弄壞（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-075 | BA-27 | 功能 | Google Batch 環境 | 排 `list_site_files`、`fetch_run_records`、`read_task_log` | 三者仍被「尚未支援」擋下；`test_gcb_ce.py:718–735`、`test_gcb_launch.py:972–986` 原封不動仍綠 | 自動：`platform/tests/test_gcb_ce.py`、`test_gcb_launch.py` |
| TC-076 | BA-28 | 功能 | Slurm 環境、狀態不可用 | 排 `launch_nextflow` | 拒絕訊息仍含 "run an analysis"（原字不變） | 自動 |
| TC-077 | BA-28 | 功能 | 同上 | 排 `list_site_files` | 拒絕訊息仍含 "list files"（原字不變） | 自動 |
| TC-078 | 裁決二 2 | 功能 | Google Batch 環境 | 跑 `clean_work` 相關既有測試 | `clean_work` 仍對 Google Batch 環境放行、確認憑證仍是三種；`test_cleanup_confirm.py`、`test_cleanup_store.py` 除種類清單末尾補 `put_upload` 外**原封不動**，全綠 | 自動：`platform/tests/test_cleanup_confirm.py`、`test_cleanup_store.py` |
| TC-079 | 完成標準 | 功能 | 完成實作 | 跑 `platform/tests/` 全套與 `tests/platform_test.sh` | 全綠（裁決二 7：若 #218 尚未合併，只剩 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 紅，視同綠） | 自動：`tests/platform_test.sh` |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | 原則 2（平台程序不啟動任何程式、不處理位元組；`test_scope.py` TC-071） | 功能 | 實作完成 | 掃描 `jobs.py`、`store.py` 全文 | 不含 `gcloud`、`subprocess`；`test_scope.py` TC-071 綠 | 自動 |
| TC-081 | 原則 1（新檔要寫明為何自己做；`test_scope.py` TC-070） | 功能 | 新檔 `test_byte_channel_a.py` | 看檔案前 40 行 | 有 `# Nothing existing:` 一行且說明至少 15 字；`test_scope.py` TC-070 綠 | 自動：`platform/tests/test_scope.py` |
| TC-082 | `test_scope.py` TC-061（平台來源不得出現「station」） | 功能 | 實作完成 | 跑 `test_scope.py` | TC-061 綠（整個平台來源目錄） | 自動：`platform/tests/test_scope.py` |
| TC-083 | 同上；計畫「不要學拆字」 | 功能 | 實作完成 | `git diff <base>...HEAD -- platform/abf_platform/jobs.py` 看新增（`+`）行 | 新增行不含小寫 `station`、也沒有用拆成兩段字串來繞過；既有第 36 行的歷史拆字沒被動 | 手動：ledger.md 貼 diff，verifier 重跑核對 |
| TC-084 | 原則 3（不寫死個人路徑；`tests/no_hardcoded_paths.sh`） | 功能 | 實作完成 | 跑該檢查 | 通過；新程式碼沒有 `/home` 之類固定路徑 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-085 | 原則 2（只有一條送出路徑；`tests/no_second_run_state_test.sh`） | 功能 | 實作完成 | 跑該檢查 | 通過；除 `abf_station/launch.py` 外沒有新檔含送出字樣，也沒有新增第二份執行狀態 | 自動：`tests/no_second_run_state_test.sh` |
| TC-086 | 專長守則（密鑰不外洩）；完成標準 | 功能 | 實作完成 | 在回報（bundle）、資料庫、日誌、測試輸出、PR 說明中搜尋 `private_key` 與站台金鑰檔名（測試原始碼中為了斷言而寫的字串不算） | 搜不到金鑰片段 | 手動：ledger.md 貼指令與輸出，verifier 重跑 |

## User Story 7 — 不在範圍與改動範圍

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-087 | 不做：代理端的事（byte-channel-b） | 不在範圍 | 實作完成 | `git diff --name-only <base>` | 整個 `abf_station/`（含 `handlers.py`）沒有任何改動；平台端沒有任何讀檔、呼叫 gcloud、再檢查、回報的程式（代理端仍會對這種工作回「不支援」） | 手動：ledger.md 貼 `git diff --stat`／`--name-only`，verifier 重跑 |
| TC-088 | 不做：接網頁／MCP／HTTP 路由／上傳畫面（cloud-upload-wire） | 不在範圍 | 實作完成 | `git diff --name-only <base>` | `receiver.py`、`web.py`、`mcp_server.py`、`confirm.py`、`actions/__init__.py`、`actions/datasets.py` 都沒有改動 | 手動：同 TC-087 |
| TC-089 | 同上 | 不在範圍 | 實作完成 | 跑 MCP／網頁工具清單相關既有測試（`test_actions_layer.py`、`test_mcp.py`、`test_chat_tools.py`、`test_guidance.py` 等） | 工具數量與名單與 base 相同，沒有新增上傳相關工具或路由；這些測試**未被修改**且全綠 | 自動：既有測試 |
| TC-090 | 不做：第三種確認憑證、`confirmations` 表遷移、`confirm.py` 改動；維護者「1.會慢半天就不用」 | 不在範圍 | 實作完成 | 讀 `confirm.JOB_KIND` 與 `store.STATE_SCHEMA` 的 `confirmations` CHECK | 與 base 相同（目前：launch、cancel、clean_work 三種），沒有新增 `put_upload`；`test_keep_submissions.py:773–774`、`test_resume_scope.py` 的 `test_tc161`、`test_cloud_cost.py:748` 的「確認憑證種類」斷言未動且綠 | 自動：既有測試 |
| TC-091 | 不做：傳完把本機檔刪掉或搬走（維護者「2.照你建議」之傳完刪檔屬 -b） | 不在範圍 | 共同前置，檔案真的放在暫存資料夾 | 排工作成功後檢查該檔 | 檔案仍在原位、內容未變（-a 不刪、不搬、不改本機檔） | 自動 |
| TC-092 | 不做：修改 ADR 0010（維護者裁決 C 指定在 -b 片） | 不在範圍 | 實作完成 | `git diff --name-only <base>` | `docs/adr/0010-chat-keys-byte-channel-studio-embedding.md` 沒有改動 | 手動：同 TC-087 |
| TC-093 | 不做：校驗和、完整性雜湊、續傳、多檔批次 | 不在範圍 | 共同前置 | 對一個檔名呼叫一次排隊 | 資料庫恰好多一個工作；`args_json` 沒有雜湊、校驗和、位移、檔案清單之類的鍵（鍵集合維持 TC-025 的五個） | 自動 |
| TC-094 | 不做：預檢加「寫入探測」 | 不在範圍 | 可用的 Google Batch 環境 | 排 `preflight` 並讀該工作 | 工作內容仍只有 `{"ce": <snapshot>}`，沒有新增任何探測相關的鍵；預檢既有測試未動且綠 | 自動 |
| TC-095 | 派工指令的禁區 | 不在範圍 | 實作完成 | `git diff --name-only <base>` | `hooks/*`、`tests/run_all.sh`、`.github/*`、`platform/abf_platform/actions/__init__.py`、`platform/abf_launch/build.py`、`platform/abf_station/launch.py` 都沒有改動 | 手動：同 TC-087 |
| TC-096 | 不做：新依賴 | 不在範圍 | 實作完成 | `git diff <base> -- pyproject.toml constraints.txt` | 無差異 | 手動：同 TC-087 |
| TC-097 | 完成標準；裁決二 2 | 不在範圍 | 實作完成 | `git diff --name-only <base>` | 除 `specs/byte-channel-a/` 底下的文件（計畫、ledger）外，只含這十個檔：`platform/abf_platform/jobs.py`、`store.py`、`cloud_store.py`，`platform/tests/test_byte_channel_a.py`（新）、`test_launch_platform.py`、`test_resume_scope.py`、`test_station_platform.py`、`test_cloud_cost.py`、`test_cleanup_confirm.py`、`test_cleanup_store.py` | 手動：同 TC-087 |
| TC-098 | 「必須更新的既有斷言」＋裁決二 2（其他一律不准動） | 不在範圍 | 實作完成 | 逐一比對上列六個既有測試檔在 base 與現在的差異 | 每處改動都只是「種類清單末尾補一項 `put_upload`」（含註解與插入迴圈補 `("put_upload", None)`）；沒有刪除或放寬任何斷言、沒有跳過案例、拒絕清單（如 `rm`、`launch`）未動；`test_keep_submissions.py` 全檔未動 | 手動：同 TC-087，verifier 逐檔 `git diff` 核對 |
| TC-099 | 完成標準（既有函式沒被順手改）；作法 C | 不在範圍 | 實作完成 | 看 `store.py`、`jobs.py`、`cloud_store.py` 的 diff | `store.py` 只動 `_JOBS_TABLE` 的一行 CHECK、種類數註解、遷移的「已是最新」判斷；`jobs.py` 的既有函式只動 `_target`、`_enqueue`（加拒絕）、`clean_result` 與三個常數表，其餘為新增；`cloud_store.py` 只多一個常數 `UPLOAD_LIMIT`，`stream_into` 等函式未動、檔首 `# Nothing existing:` 行未動 | 手動：同 TC-087 |
| TC-100 | 完成標準（PR 說明） | 功能 | PR 已開 | 讀 PR 說明 | 含：需要 migration 的理由與範圍（只重建 `jobs` 表）、沒動的既有斷言清單、與 ADR 0010 的差別、不加確認憑證的決定與維護者 2026-10-25 的回覆 | 手動：verifier 讀 PR 說明（無 PR 時回報 UNVERIFIED） |
