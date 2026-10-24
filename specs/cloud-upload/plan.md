---
id: cloud-upload
title: 資料集可以放在雲端 bucket：登記 gs:// 位置、檢查歸屬、大檔給指令（位元組怎麼進 bucket 走站台代理，不在平台程序裡）
tier: B
kinds: backend
lane: L7-cloud（碰 `actions/datasets.py`，與 L6 的 012c-web 同一個檔，不可平行）
base: v3（C-1 `gcb-ce-type`、C-2 `gcb-launch` 已在 v3；本任務從 origin/v3 開分支）
source: memory/PLAN-abf-v3-replan-2026-10.md Milestone 3 的 C-6（拷問 10-21 第五輪第 16 點）；站台代理路線依據 memory/dev-plans/gcb-ce-type.md 裁決二 F–H、gcb-launch.md 裁決 4
---

# cloud-upload

> 本檔由 developer-agent 助理起草（2026-10-24）。**只處理 C-6 的平台側**：資料集（Dataset）的「目的地＝雲端 bucket」——怎麼命名位置、怎麼登記、怎麼拒絕不屬於你的位置、>2 GB 怎麼回指令、一個與傳輸方式無關的串流核心。**位元組真正從瀏覽器流到 bucket 的那條管道（ADR 0010 的位元組通道）v3 裡還不存在，不在本任務**；它需要的呼叫點都在被禁止動的檔案裡，列在「待 developer-agent 裁決」。B 級（後端行為改變）→ verifier 通過＋CI 綠由 developer-agent 自合。
> **與 replan 原文有兩處不同**：①原文寫「google-cloud-storage 客戶端，用平台主機的 SA 檔」——查證後不採（見裁決 1）；②原文寫「>2 GB 回 `gsutil cp`」——預設改 `gcloud storage cp`（見裁決 3）。

## 目標
使用者（或他的 AI）能把一份資料集登記成「檔案在我們實驗室自己的 Google Cloud bucket」：檔案位置是 `gs://<bucket>/uploads/<使用者名>/…`，bucket 必須就是某個 Google Batch 計算環境的 `workDir` 所在的 bucket；位置不屬於呼叫者、bucket 對不上、像憑證的值，一律白話拒絕；單檔超過 2 GB 時，回一行在使用者自己電腦上跑的指令。

為什麼這樣切：
1. 平台只記名字與位置、不讀不存檔案內容（`datasets.py` 檔首原則、ADR 0010）；雲端目的地只是把「位置」從本機資料夾換成 `gs://`。
2. gcb-launch 裁決 4 已定：送出時輸入檔必須是 `gs://` 且在該環境 `workDir` 的 bucket；本任務讓資料集能產生這樣的位置。
3. 憑證（服務帳號金鑰檔）只屬於站台代理那一側，平台程序從頭到尾不碰（C-1 裁決二 H）；本任務的程式碼與測試因此**沒有任何金鑰路徑的參數**。

## 維護者原話（verifier 出題用）
逐字取自 `memory/PLAN-abf-v3-replan-2026-10.md`：
- 「16. （10-21 拷問五）雲端上傳＝**平台代傳**到使用者自己的 bucket、不落地（ADR 0010 規則），大檔給 `gsutil` 指令；**跑完經本人確認刪中間檔（work），結果保留 30 天到期前提醒、不自動刪**；自訂 pipeline 分享只在實驗室內＋匯出 zip，不做公開庫；版本政策＝**新專案預設最新版**（仍釘住該版，不自動升）。」→ ①目的地是「使用者自己的 bucket」→ 位置只能落在呼叫者自己的前綴；②「不落地」→ 平台與本任務的程式都不得把位元組寫到本機磁碟；③「大檔給指令」→ >2 GB 回指令，不收；④刪 work、30 天提醒**不在本任務**。
- 「13. ……**雲端用戶不裝代理**——平台主機自己跑 Nextflow、雲端憑證放平台主機檔案（不進資料庫）→ C-1／C-2 改為平台內建的 `local` 執行器，不經站台。」（第 52 行；已被 C-1 裁決二 F–G 改成「平台主機上跑一個站台代理」，見 `gcb-ce-type.md`）→ 憑證不進資料庫；沿用 C-1／C-2 的代理做法。
- 「C-6 `cloud-upload`（B／backend）：012c 的上傳後端加「目的地＝雲端 bucket」：平台主機以串流寫入 `gs://…`（google-cloud-storage 客戶端，用平台主機的 SA 檔），不落地；>2 GB 回 `gsutil cp` 指令；資料集登記 bucket 路徑。files：`actions/datasets.py`、新 `platform/abf_platform/cloud_store.py`、`test_cloud_upload.py`。」（第 170 行）→ 資料集登記 bucket 路徑；>2 GB 回指令；不落地；檔案範圍照此。
- 「上傳 >2 GB 改給指令」（10-18 裁示，第 63 行引述 `memory/handoff/2026-10-18-web-012-014-answers.md`）→ 2 GB 上限（`WEB_UPLOAD_LIMIT`，十進位）對雲端目的地同樣適用，剛好 2,000,000,000 位元組仍收、多一個位元組就不收（沿用 012c 的 TC-024／TC-026）。
- 「**雲端第一個真實使用者＝他自己的自費帳號**」（10-21 拷問，第 50 行）→ 一切預設要在他自己一個人、一個 bucket 的情形下可用。

## 範圍：檔案（只准改這些）
- `platform/abf_platform/actions/datasets.py`（`draft_samplesheet`、`check_web_upload`、`register_dataset` 各加一個關鍵字參數 `destination=None`；**不新增公開函式**，見「必須更新的既有斷言」）
- `platform/abf_platform/cloud_store.py`（新；純 Python、無 I/O 函式庫、無網路）
- `platform/tests/test_cloud_upload.py`（新）
- `docs/TESTING.md`（只加「cloud-upload」一小節：手動驗收步驟；仿 gcb-ce-type 裁決 A）
- **不准動**：`platform/abf_platform/actions/__init__.py`、`pipeline_launch.py`、`cli.py`、`store.py`、`receiver.py`、`platform/abf_launch/build.py`、`platform/abf_station/launch.py`、`deploy/`、`configs/sites/*`、`docs/OPERATIONS.md`、`docs/INSTALL.md`（其他任務在動）。`platform/pyproject.toml`、`platform/constraints.txt` 也不動（見裁決 1）。

## 作法
（全部是決定，不是程式碼。行號與函式名是 origin/v3 的；開工前 `git fetch -q origin` 再核對。）

**A. `cloud_store.py`（新）——位置語言與串流核心，全程不打開檔案、不連網、不啟動程式**
1. 檔首第一行 `# Nothing existing: …`（≥15 字，TC-070），理由寫：「搜過 google-cloud-storage、gcloud/gsutil、Nextflow 的 gs:// 支援；它們都會在平台程序裡連網或啟動程式，被憲法原則 2 與 TC-061/071 擋掉，所以這裡只做位置的判斷與位元組計數，真正寫入由注入的 sink 做」。
2. `parse_gs(url)` → `(bucket, object_name)` 或丟 `CloudPathError(白話訊息)`。bucket 規則：3～63 字元，小寫英數與 `-`、`_`、`.`，頭尾是英數；物件名：不得為空、不得含 `..` 片段、不得含控制字元（含 NUL）、UTF-8 長度 ≤ 1024、不得以 `/` 開頭。其他方案（`s3://`、`https://`、`file://`）一律拒絕並說「只收 gs://」。
3. `workdir_bucket(ce)` → 該環境 `config["workDir"]` 的 bucket；`ce["platform"]` 不是 `googlebatch-platform` 或沒有 `workDir` → `CloudPathError`。（platform 型別用 `compute_envs.PLATFORM_HOST_TYPES` 判斷，不寫死字串兩次。）
4. `upload_prefix(ce, owner_name)` → `gs://<bucket>/uploads/<owner_name>/`；`owner_name=None`（終端機）→ `gs://<bucket>/uploads/`。`object_url(ce, owner_name, filename)` → `upload_prefix + filename`；`filename` 只能是單層檔名（不含 `/`、`\`、`..`、NUL；長度 1～255；通過 012c 既有的 FASTQ 副檔名不在這裡判斷）。
5. `inside_prefix(url, prefix)`：`url` 與 `prefix` 都經 `parse_gs`，bucket 相同且物件名以 prefix 的物件名開頭**且至少再多一個字元**（前綴本身不算檔案）；比較前不做 URL 解碼（`%2e%2e` 不會被當成 `..`，也不會被當成 `/`——一律照字面）。
6. `big_file_command(ce, owner_name)` → 一行字串：`gcloud storage cp <你電腦上的資料夾>/* <upload_prefix>rawdata/`（見裁決 3；`<…>` 是留給人填的佔位字，仿既有 `bash scripts/push.sh <你電腦上的資料夾> …`）。指令裡**只有 bucket 前綴**，沒有專案名、沒有金鑰路徑。
7. `stream_into(chunks, sink, *, declared_size, limit)`：`chunks` 是產生 `bytes` 的可迭代物件；`sink` 是有 `write(data)`、`close()`、`abort()` 三個方法的物件（協定由呼叫者實作；本任務只在測試裡用假 sink）。規則：①每塊只轉交給 `sink.write`，函式內**不累積**所有位元組（記憶體只持有目前這一塊）；②累計位元組超過 `declared_size` 或 `limit` 的瞬間：停止讀下一塊、呼叫 `sink.abort()`、回 `{"ok": False, "message": …, "received": n}`；③迭代結束時 `received != declared_size` → `abort()`、回失敗（「短了／長了」）；④恰好相等 → `close()`、回 `{"ok": True, "received": n}`；⑤`chunks` 迭代中丟例外或 `sink.write` 丟例外 → 先 `abort()` 再回失敗，**例外訊息不原樣放進回覆**（可能含路徑或權杖），只回「傳輸中斷」；⑥不算雜湊（分塊校驗屬位元組通道，見 ADR 0010 路徑 B）。
8. 所有函式都不接受、不回傳、不記錄憑證路徑或內容；任何出現在回覆裡的字串經 `compute_envs.looks_like_credential` 檢查的輸入值不得原樣回顯。

**B. `datasets.py` 的三處關鍵字參數 `destination`**
- 值是**計算環境的名字**（字串）或 `None`。`None` ＝ 今天的行為，位元組級不變（既有測試全部沿用）。
- 三個函式的雲端分支共用一個私有解析器 `_cloud_target(platform_path, caller, destination)`（底線開頭，不增加公開函式）：用 `compute_envs.get(platform_path, destination, owner=<caller.user_id 或 None>)` 取環境（別人的或不存在 → 同一句「找不到計算環境」，與 `_not_found` 同口氣，不洩漏存在與否）；再用 `cloud_store.workdir_bucket`；回 `(ce, owner_name)`。**不要求環境狀態是 `available`**（登記只存位置；能不能真的傳是位元組通道的事）。
- `check_web_upload(…, destination=ce)`：規則同今天（逐檔、`sizes` 驗證不變、超過 `WEB_UPLOAD_LIMIT` 才列入 `over`）；超過時 `command` 換成 `cloud_store.big_file_command(…)`，`message` 第二句（「如果檔案已經在國網上」那句）換成「如果檔案已經在這個 bucket 裡，就把它們放進同一個前綴：<upload_prefix>」。`ok:false` 的形狀不變：`over`、`command`、`accepted` 都在。
- `draft_samplesheet(…, destination=ce)`：每個名字可以是 `gs://` 位置或單層檔名（單層檔名 ＝ `object_url(…)`）；必須 `inside_prefix`；其餘與今天同（不寫入、配對規則不變；`pair_fastq` 用 `os.path.split`，對 `gs://` 字串可用，測試要證實）。
- `register_dataset(…, destination=ce)`：`files` 的每個 `path` 必須 `inside_prefix`；`size_bytes` 規則不變；**一份資料集不得混雜本機路徑與 `gs://`**（任一檔不是 `gs://` → 拒）；樣本表儲存格允許 `gs://` 值，但該值必須是登記檔案之一（沿用「樣本表裡有檔案不在登記的檔案內」那條拒絕）；非 `gs://` 的任何網址（`https://` 等）仍照今天的「樣本表含網址，不收」拒絕。`files_json` 的每個項目仍然只有 `path`（與選填 `size_bytes`）——**不新增欄位、不加資料表欄位**，雲端與否由 `path` 以 `gs://` 開頭決定。
- 擁有者規則不變：表的 `owner_user_id` 照舊；`list_datasets`／`get_dataset` 不改。
- **資料結構沒有變動 → 不需要 migration**（理由寫進 PR 說明：`datasets` 表欄位全不動，雲端位置存在既有 `files_json` 的 `path` 裡）。
- 檔首 docstring 更新「the bytes go straight to the person's own folder on the cluster」那句，補一句「or, for a cloud destination, into the person's own prefix of the lab's bucket (written by the agent on the platform host, never by this module)」——注意**整個 `datasets.py` 原始碼不得出現**既有測試禁用的字（見下節 TC-059/061/078/085 的清單）。

**C. 為什麼位元組走站台代理而不是平台程序裡的函式庫（含查證）**
- 三個現有測試明文擋下雲端函式庫：`test_gcb_ce.py` TC-083（pyproject 不含 `google-cloud`，且 `abf_platform`／`abf_station` 不得 `import google`）、`test_gcb_launch.py` TC-114（同，另掃 `abf_launch`）、`test_station_envs.py` TC-085（pyproject 不含 `boto3`／`botocore`／`azure`／`google-cloud`／`kubernetes`，且不得 import）。`test_guidance.py:460` 還逐字斷言 `dependencies = ["mcp>=2.3,<3"]`。要加 `google-cloud-storage` 就是改四個測試＋`pyproject.toml`＋釘版檔 `platform/constraints.txt`（`tests/platform_test.sh` 照它裝；目前一個 google 套件都沒有）＋至少一個憲法層級的決定。
- 更根本的是：函式庫要在**平台程序**裡讀服務帳號金鑰檔——C-1 裁決二 H 才剛把它改成「平台不讀金鑰檔」。這等於把金鑰放進一個對外開 HTTP 的程序的記憶體，並讓平台程序主動連出 Google；TC-061 的檔名是「no outgoing connection in the source」，函式庫繞過的是字面掃描、不是原則。
- 站台代理本來就在平台主機、本來就持有那個金鑰檔（`ABF_STATION_GCP_CREDENTIALS`）、本來就用 `gcloud`（`abf_station/gcb_preflight.py`，`site.py` 是唯一 `subprocess` 的地方）。`gcloud storage cp` 的說明寫「To copy the contents of one file directly from stdin, use "-" as the source argument without the "-I" flag」（https://docs.cloud.google.com/sdk/gcloud/reference/storage/cp，2026-10-24 讀），所以代理可以把收到的塊餵進 `gcloud storage cp - gs://…`，不落地。→ **採代理路線**；它也讓「憑證只有代理那一側持有」這個 C-1／C-2 的不變量繼續成立。
- 代價（要老實說）：代理路線需要位元組通道（瀏覽器→代理）才有端到端；v3 還沒有（ADR 0010 第 2 點，路徑 A 回送介面／路徑 B 平台記憶體轉送，都未實作；現有代理協定只傳 JSON，`fetch-records` 上限 20 MB）。所以本任務交付的是**平台側的一半**，加上與傳輸方式無關的串流核心；另一半見「待 developer-agent 裁決」第 1、2 項。

## 失敗先行測試（`platform/tests/test_cloud_upload.py`，現在都會紅；全部用 `tmp_path` 當平台資料夾、假 sink、假 chunk；不碰網路、不啟動程式、不讀任何金鑰檔）
檔首 `# Nothing existing: …`（TC-070）。建環境的輔助函式照 `test_gcb_ce.py` 的 `flat_env`／`create`（讀它，別憑記憶）；呼叫者與資料夾照 `test_datasets.py` 的 `Duo`／`World`（`d.a`、`d.b` 兩個使用者）。環境 `gcb1` 屬於 `d.a`，`workDir` ＝ `gs://lab-bucket/work`；`d.b` 另有 `gcb2`，`workDir` ＝ `gs://other-bucket/work`。

位置語言（純函式，`cloud_store`）：
1. `test_parse_gs_accepts_a_plain_location`：`gs://lab-bucket/uploads/alice/a_R1.fastq.gz` → `("lab-bucket", "uploads/alice/a_R1.fastq.gz")`。
2. `test_parse_gs_refuses_the_bent_ones`（參數化）：`s3://b/x`、`https://b/x`、`gs://B/x`（大寫 bucket）、`gs://ab/x`（太短）、`gs://b-ok/../x`、`gs://b-ok/a/../../x`、`gs://b-ok/`（空物件）、`gs://b-ok//x` 的 `/` 開頭情形、含 NUL 或換行、物件名 1025 位元組 → 都丟 `CloudPathError`，且訊息是白話、不含堆疊。
3. `test_encoded_dots_are_literal`：`gs://lab-bucket/uploads/alice/%2e%2e/bob/x` 不被當作離開 alice 前綴（它仍在 alice 前綴內，物件名保留字面 `%2e%2e`）——證明沒有 URL 解碼。
4. `test_inside_prefix_needs_the_same_bucket_and_something_after_the_prefix`：前綴本身、同前綴不同 bucket、`uploads/alicex/…`（只是字首相同的別人）都不算在內；`uploads/alice/x` 算在內。
5. `test_workdir_bucket_needs_a_google_batch_environment`：Slurm 環境、沒有 `workDir` 的環境 → `CloudPathError`。
6. `test_big_file_command_is_one_line_with_only_the_bucket_prefix`：一行、以 `gcloud storage cp ` 開頭、含 `gs://lab-bucket/uploads/alice/rawdata/`、不含專案名、不含 `gcp-sa`、不含 `.json`。

串流核心：
7. `test_stream_into_hands_every_chunk_to_the_sink_and_closes`：5 塊共 1000 位元組、`declared_size=1000` → `ok`、`received==1000`、sink 依序收到 5 塊、`close` 一次、`abort` 零次。
8. `test_stream_into_stops_at_the_first_byte_over_the_declared_size`：宣告 1000、送 1001 → `ok:false`、`abort` 一次、`close` 零次、**第 N+1 塊沒有被讀**（用會記錄「被取用幾次」的產生器證明）。
9. `test_stream_into_stops_at_the_limit`：`limit=2_000_000_000`，用假的「會謊稱大小」的塊（不真的配置 2 GB——用 `declared_size=limit+1` 搭配 `limit`，只送兩小塊即可觸發前置檢查）→ 在 `declared_size > limit` 時**一塊都不讀**就失敗（不呼叫 `write`，`abort` 可呼叫一次或零次，由實作定，測試只斷言 `write` 零次與 `ok:false`）。
10. `test_stream_into_short_is_an_error`：宣告 1000、只送 999 → `abort`、`ok:false`。
11. `test_a_failing_chunk_source_or_sink_aborts_and_hides_the_exception_text`：產生器丟 `RuntimeError("token=abc123 /home/x/gcp-sa.json")`；另一個情形是 sink.write 丟同樣例外 → 回覆 `ok:false`、`abort` 一次，且回覆的 JSON 字串**不含** `abc123`、`gcp-sa`、`/home`。
12. `test_stream_into_never_holds_more_than_one_chunk`：產生器產出 200 塊各 1 MiB 的**同一個** bytes 物件、sink 立即丟棄；用 `tracemalloc`（或對塊的 `weakref`）證明 `stream_into` 沒有 list／bytearray 累積（做法由 executor 選，驗收看「不累積」的證據，不看速度）。

資料集（`datasets`，雲端分支）：
13. `test_register_a_cloud_dataset`：`d.a` 以 `destination="gcb1"` 登記兩個 `gs://lab-bucket/uploads/<a 的名字>/…_R1/_R2` 檔與對應樣本表 → `ok`；`get_dataset` 的 `files` 每項只有 `path`（與選填 `size_bytes`）；`datasets` 表欄位清單與基準 commit 相同（證明沒有 migration）。
14. `test_a_cloud_dataset_cannot_name_somebody_elses_prefix`：路徑在 `uploads/<b 的名字>/…` → 拒；訊息點名 **a 自己的**前綴、不點名 b 的任何東西。
15. `test_a_cloud_dataset_cannot_leave_the_environments_bucket`：路徑是 `gs://other-bucket/uploads/<a>/…` → 拒；訊息說明 bucket 必須是該環境 `workDir` 的 bucket。
16. `test_someone_elses_environment_answers_like_a_missing_one`：`d.b` 以 `destination="gcb1"`（a 的環境）呼叫三個函式 → 與 `destination="no-such-env"` 的回覆**逐字相同**（把環境名換成 `<name>` 後比較，仿 `test_datasets.py` 的 `words()`）。
17. `test_local_and_cloud_paths_cannot_be_mixed`：一個 `gs://`、一個本機路徑 → 拒。
18. `test_other_urls_in_a_cloud_samplesheet_are_still_refused`：儲存格是 `https://example.org/x_R1.fastq.gz` → 拒，訊息含「網址」（與 TC-052 同）；儲存格是 `gs://` 但不在登記檔案內 → 拒（同 TC-045）。
19. `test_a_credential_shaped_value_is_refused_and_never_reaches_the_database`：`gs://lab-bucket/uploads/<a>/` 之後帶 `abf_pat_` 加 30 字元（用字串拼接，仿 `test_datasets.py` 的 `TOKEN`）→ 拒，資料表仍空（仿 TC-054／TC-083）。
20. `test_check_web_upload_for_a_cloud_destination`：恰好 2,000,000,000 位元組 → `accepted`；2,000,000,001 → `ok:false`、`over` 有它、`command` 以 `gcloud storage cp ` 開頭並含 a 的前綴、不含 b 的前綴；多個檔只有大的被列入（同 TC-029）。
21. `test_draft_samplesheet_for_a_cloud_destination`：四個 `gs://` 檔名配成兩對、`unpaired` 空；其中一個在別人的前綴 → 整個草稿被拒；不寫入任何東西（資料夾列表前後相同，仿 TC-060）。
22. `test_the_default_behaviour_is_byte_for_byte_unchanged`：不傳 `destination` 時，回覆與基準相同——直接重跑 `test_datasets.py` 的全部測試即可（本測試只斷言 `destination` 的預設值是 `None` 與三個簽章的位置參數順序沒變）。

原始碼掃描（仿既有慣例）：
23. `test_cloud_store_has_no_io_network_or_process_words`：`cloud_store.py` 原始碼不含 `open(`、`subprocess`、`os.system`、`socket`、`urllib`、`httpx`、`requests`、`import google`、`boto3`、`azure`。指令字串 `gcloud storage cp` 直接寫（它不在 TC-071 的禁字清單，不必拆字）。
24. `test_the_word_station_appears_nowhere_in_the_new_or_changed_platform_sources`：掃 `cloud_store.py`、`datasets.py`，不含 `station`（TC-061）；**註解與 docstring 一律寫「the agent on the platform host」，不寫那個字，也不拆字。**
25. `test_no_new_dependency_and_no_cloud_import`：`pyproject.toml` 與 `constraints.txt` 不含 `google`；`git diff --name-only <base>` 不含 `pyproject.toml`、`constraints.txt`。
26. `test_no_key_file_word_in_the_new_sources`：兩個來源檔不含 `gcp-sa`、`GOOGLE_APPLICATION_CREDENTIALS`、`CLOUDSDK`、`.json`（金鑰檔的事只屬代理）。
27. `test_the_cloud_code_adds_no_public_function_to_datasets`：重跑 `test_datasets.py::test_tc063_no_delete_share_or_edit` 的同一份清單（見下節）。

## 必須更新的既有斷言（有意的更新；其他一律不准動；PR 說明逐條寫「以前／以後／理由」）
**本任務不新增 MCP 工具、不新增 HTTP 路由、不新增工作種類、不改任何資料表，所以下面這些都「不變」，且 PR 說明要明寫「沒動」：**
- `platform/tests/test_actions_layer.py` 的唯讀工具基準（BASELINE，逐位元組）與 `READ_TOOLS`——不變（資料集函式本來就沒接上 `actions/__init__.py`／`mcp_server.py`；若將來接上，是另一個任務的有意更新）。
- 各測試裡的工具個數、`UNSUPPORTED` 長度（12）、`jobs.kind` 的 CHECK 清單、`launches`／`jobs`／`compute_envs` 欄位清單（`test_gcb_launch.py` 附近的欄位斷言）——不變。
- `test_datasets.py` 的 TC-063（公開函式清單必須剛好是 `check_web_upload, draft_samplesheet, get_dataset, list_datasets, pair_fastq, register_dataset`）——**不變**，所以雲端分支不得新增公開函式。
- `test_datasets.py` 的 TC-059（來源不得含 `open(`、`os.stat`、`.stat(`）、TC-061（小寫後不得出現 `hashlib`、`md5`、符合 `\bsha\d*` 的字——注意 `share`、`shape` 這類以 `sha` 起頭的字也會中）、TC-078（不得含 `subprocess`、`os.system`、`sbatch`、`srun`、`qsub`、`jobs`、`confirm`、`queue`、`submit`）、TC-085（不得含刪改檔案的字）、TC-081（不得有寫死路徑）——**不變，而且對新增的程式碼同樣生效**；寫註解與訊息時避開這些字。
- `test_datasets.py` 的 TC-052／053（網址仍被拒）、TC-045（樣本表檔案不在登記內仍被拒）、TC-062（檔案項目只有 `path`、`size_bytes`）、TC-065（`WEB_UPLOAD_LIMIT == 2000000000`）——**不變**。
- `test_datasets.py` 的 TC-064（`actions/__init__.py`、`mcp_server.py`、`web.py`、`web_board.py`、`store.py` 不得出現資料集函式名）——不變；本任務不動那些檔，所以自然成立。
- `test_gcb_ce.py` TC-083、`test_gcb_launch.py` TC-114、`test_station_envs.py` TC-085（不得有雲端函式庫）、`test_guidance.py:460`（依賴清單逐字）——**不變**，且是本任務選代理路線的理由。
- 唯一可能需要有意更新的：`test_scope.py` 的 TC-070 會自動納入兩個新 `.py` 檔（要求檔首 `# Nothing existing:` ≥15 字）——不是更新斷言，是新檔必須符合；TC-061／TC-071 的掃描也會自動涵蓋 `cloud_store.py`。

## 完成標準（done when）
- 上節測試 1～27 全綠；`platform/tests/` 全套綠（含 `test_datasets.py` 原封不動全綠、`test_scope.py` 全綠）；`tests/platform_test.sh` 與倉庫既有的 CI 綠。
- `git diff --name-only <base>` 只含「範圍：檔案」列的四個檔。
- `datasets` 表欄位、`files_json` 項目形狀、`pyproject.toml`、`constraints.txt` 與基準相同（測試 13、25）。
- 不傳 `destination` 時 `datasets.py` 的行為與基準完全相同（測試 22 與 `test_datasets.py` 全綠）。
- `docs/TESTING.md` 有「cloud-upload」小節，且手動驗收步驟寫明：**端到端（真的把檔案傳進 bucket）要等位元組通道任務，目前只能驗到登記與拒絕**。
- 回報內容包（bundle）、資料庫、日誌、測試輸出、PR 說明裡搜不到任何金鑰片段（`grep -r` 站台金鑰檔名、`private_key`）。

## 環境事實
（行號為 origin/v3 的內容，2026-10-24 讀；`git -C <repo> fetch -q origin` 後以 `git show origin/v3:<path>` 讀。）
- `platform/abf_platform/actions/datasets.py`：`WEB_UPLOAD_LIMIT`=2_000_000_000、`_SCHEME` 擋所有 `scheme://`、`_within`（只准呼叫者自己的上傳資料夾）、`draft_samplesheet`:132、`check_web_upload`:149（`over` 時回 `bash scripts/push.sh …`）、`register_dataset`:193（`UNIQUE (owner_user_id, name, version)`）、`list_datasets`、`get_dataset`。這些函式**尚未接到** `actions/__init__.py`／`mcp_server.py`／`web.py`（`test_datasets.py` TC-064 保證）。
- `platform/abf_platform/compute_envs.py`：`PLATFORM_HOST_TYPES = ("googlebatch-platform",)`:35、`get(state_path, name, owner=None)`:481（別人的環境回 `None`，與不存在相同）、`view()`:463（`config` 已解析成 dict，含 `workDir`）、`looks_like_credential`。
- `platform/abf_station/gcb_preflight.py`：金鑰檔由 `ABF_STATION_GCP_CREDENTIALS` 或 `<部署資料夾>/_personal/gcp-sa.json` 決定；呼叫 gcloud 的環境變數用 `CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE`（路徑不進 argv）；唯一 `subprocess` 在 `abf_station/site.py`。
- 憲法掃描：`platform/tests/test_scope.py` TC-061（`abf_platform/` 與 `abf_station/` 以外的來源不得含 `station` 字樣、`ssh`、`sbatch`、`import requests`、`urllib.request`、`import httpx`、`socket.` 等）、TC-071（不得含 `nextflow run`、`subprocess`、`threading`、`nohup`、`setsid`、`while True` 等）、TC-070（新 `.py` 檔前 40 行要有 `# Nothing existing: …`）。`jobs.py:35` 為了避開 TC-061 把該字拆成兩段字串；**本任務不用那招，直接寫「the agent on the platform host」**。
- `jobs.kind` 的 CHECK 只列六種（`preflight`、`list_site_files`、`fetch_run_records`、`read_task_log`、`launch_nextflow`、`cancel_run`）；`store.py` 與 `receiver.py` 在本任務禁區。
- ADR 0010（`docs/adr/0010-chat-keys-byte-channel-studio-embedding.md`）第 2 點：代理只講 JSON 長輪詢、不收連線；路徑 A（瀏覽器與代理同一台，代理開回送介面、一次性權杖）／路徑 B（平台記憶體轉送 8 MiB 塊、不落地、代理往外拉）；「上傳的寫入需要自己的工作種類、路徑白名單、大小上限、頁面上的人工確認」。**這些在 v3 都還沒有程式。**
- Google 文件（2026-10-24 讀）：「The gsutil tool is a legacy Cloud Storage CLI and minimally maintained」「gsutil is not the recommended CLI for Cloud Storage」（https://docs.cloud.google.com/storage/docs/gsutil）；`gcloud storage cp` 以 `-` 為來源時讀 stdin（https://docs.cloud.google.com/sdk/gcloud/reference/storage/cp）。**查不到**：`gcloud storage cp -` 對 2 GB 級串流的記憶體／逾時行為（文件沒寫）——列為手動驗收，位元組通道任務時量。
- 平台主機現實：首位使用者的平台主機是他自己的桌機，代理跑在 WSL；使用者電腦要跑 `gcloud storage cp` 需要先對該實驗室的 GCP 專案有權限並登入（`gcloud auth login`）——**這是 >2 GB 指令能不能用的前提，見待裁決第 5 項**。

## 不做
- 位元組通道本身（瀏覽器→平台→代理）、代理端 `gcloud storage cp -` 的包裝、新工作種類、`jobs.kind` CHECK 的 migration、上傳 HTTP 路由、上傳畫面（012c-web）、MCP／動作層接線。
- 刪除中間檔（work）、結果保留 30 天提醒（拷問五第 16 點後半）。
- 把資料集的 `gs://` 位置帶進送出流程（`request_launch`／`prepare_launch` 如何用資料集的樣本表）——另一個任務；本任務只讓資料集「能被登記成雲端位置」。
- AWS S3／Azure Blob（C-4／C-5 複製此做法）。
- 新增 Python 依賴；改 `pyproject.toml`／`constraints.txt`；改任何現有測試的斷言。
- 校驗和、完整性雜湊（屬位元組通道）。
- 為了過 TC-061 而拆字；**平台來源裡不出現那個字，用不到拆字**。

## 裁決（2026-10-24，developer-agent 助理起草；與上文衝突時以本段為準）
1. **位元組走站台代理（`gcloud storage cp -`），不用 `google-cloud-storage` 函式庫。** 理由：①四個現有測試與一條逐字依賴斷言明文擋函式庫（見作法 C），採用等於改四個測試＋兩個設定檔＋憲法層級決定；②函式庫需要平台程序讀金鑰檔，推翻 C-1 裁決二 H（平台不讀金鑰檔）；③站台代理本來就在平台主機、持有金鑰、有 gcloud，與 C-1／C-2 完全同一個模式，不變量（憑證只在代理那側）不用重新論證。**另一選項**：把函式庫放進**代理**（不是平台）——仍然要改同樣四個測試（它們也掃 `abf_station/`）與 `pyproject.toml`，只贏在不用 `gcloud` 子程序，不值得。**預設採此做法；需要他知道的後果：端到端要等位元組通道（待裁決 1）。**
2. **本任務只交付平台側，不交付「能傳」。** 理由：沒有位元組通道，任何「上傳」都是空話；而通道的呼叫點（新工作種類 → `store.py` 的 CHECK／migration、`jobs.py`、`receiver.py`、`web.py` 路由）有的在禁區、有的是一個比本任務大的設計（ADR 0010 的兩條路徑）。把串流核心做成「與傳輸無關、sink 注入」，是為了通道任務一接上就能用、且在那之前能完整測試。**預設採此做法。**
3. **>2 GB 的指令預設 `gcloud storage cp`，不是 `gsutil cp`（維護者原話與 replan 原文都寫 gsutil）。** 理由：Google 自己寫 gsutil 是 legacy、minimally maintained、不是建議的 CLI；C-1 的預檢已經要求 gcloud，使用者端少裝一個工具。**這是對維護者字面的偏離，所以列出來：**另一選項是照字面回 `gsutil cp`（舊工具仍可用），測試 6 與 20 把前綴字串換掉即可。**預設：gcloud storage cp；他若要字面，一行改。**
4. **雲端位置固定在 `gs://<workDir 的 bucket>/uploads/<使用者名>/`，與 `workDir` 同 bucket、不同前綴。** 理由：gcb-launch 裁決 4（輸入必須在 workDir 的 bucket）；金鑰與預檢只驗證過那個 bucket；`uploads/` 與 `work/` 分開，之後「刪 work」不會誤刪上傳的原始資料。**預設採此做法。**
5. **不要求環境是 `available` 才能登記。** 理由：登記只寫名字與位置、不碰雲端；要求 `available` 會讓「預檢暫時失敗」擋住使用者先把資料集整理好。傳輸時才檢查（通道任務）。**預設採此做法。**
6. **雲端與否由 `path` 是否以 `gs://` 開頭決定，不新增資料表欄位。** 理由：`datasets` 表在 `datasets.py` 內建立（`_TABLE`），改欄位要 migration 與 `store.py` 的同步檢查；TC-062 也限定檔案項目只有 `path`、`size_bytes`。**另一選項**：加 `destination` 欄；需要 migration 與改 TC-062。**預設：不加。**
7. **雲端分支不新增公開函式，三個函式各加關鍵字參數。** 理由：TC-063 逐字斷言公開函式清單；加一個函式就要改那條測試，而關鍵字參數預設 `None` 對所有現有呼叫者零影響。**預設採此做法。**
8. **新檔標頭**：`cloud_store.py`、`test_cloud_upload.py` 前 40 行要有 `# Nothing existing: …`（TC-070）。
9. **派工順序**：不可與 L6 的 012c-web（同改 `datasets.py` 的呼叫端）、也不可與任何改 `actions/datasets.py` 的任務平行；與 C-3（L7）檔案不相交，可平行。

## 待 developer-agent 裁決
（以下每一項的呼叫點都在被禁止動的檔案裡，或需要比本任務更大的設計；**本任務不猜、不先做**。）
1. **位元組通道要不要先成為獨立任務？**（建議：要，叫 `byte-channel`，B 級，依 ADR 0010 第 2 點）。它需要：新工作種類（例如 `put_object`）→ `store.py` 的 `jobs.kind` CHECK 與 migration、`jobs.py` 的 `KINDS`／`DEADLINE_SECONDS`／`_target`／`clean_result`、`receiver.py` 的塊接收端點、`abf_station/handlers.py` 的 `JOB_KINDS`、代理端的包裝（`gcloud storage cp - gs://…`，餵塊進 stdin，`site.py` 是唯一能 `subprocess` 的地方）、人工確認（ADR 0010：頁面上的人本人確認，寫入類）。本任務的 `stream_into` 與 `inside_prefix` 是它的零件。**C-6 的「端到端」驗收在這項完成之前做不到。**
2. **誰來把 `destination` 接進動作層／MCP／HTTP？**（`actions/__init__.py`、`mcp_server.py`、`web.py`；其中前兩者在禁區。）建議併入第 1 項或 012c-web；接上時才會有工具個數、`READ_TOOLS`、BASELINE 的有意更新（那時由該任務逐條列）。
3. **`jobs.kind` 若要新增 `put_object`，要不要順便讓代理回報「目前能不能寫 bucket」？**（`hello` 回「有／無」那句 C-1 已取消；預檢的 `bucket` 項是唯讀 `ls`，不證明可寫。）可能需要預檢加一項寫入探測——會寫一個物件到 bucket，**花錢極微但不是零**，要他點頭。（`gcb_preflight.py` 與 `compute_envs.py` 不在禁區，但屬 C-1 的檔，另開任務。）
4. **使用者電腦上的 `gcloud storage cp` 指令，帳號從哪來？** 使用者要對該專案有權限並已 `gcloud auth login`。是否由管理者開帳號時一併給 bucket 的寫入權限（只限 `uploads/<他的名字>/` 前綴要靠 IAM 條件，查不到這個專案是否已設）？這是 `docs/INSTALL.md`／`docs/OPERATIONS.md` 的內容（禁區），建議由 L3 docs 任務補一小節，並在 `docs/TESTING.md` 手動驗收寫明前提。
5. **`gs://` 位置如何進送出流程？** `request_launch`／`prepare_launch`（`actions/__init__.py`、`abf_launch/build.py` 在禁區）目前要求樣本表是「呼叫者自己上傳資料夾裡的本機檔」；雲端資料集的樣本表文字存在資料庫、不是檔案。需要在送出路徑加「用資料集名稱＋版本當輸入」的入口，並重用 `gcb-launch` 裁決 4 的 bucket 檢查。建議開 `dataset-to-launch` 任務。
6. **刪除 `work`、30 天提醒**（拷問五第 16 點後半）不在 C-6；是否已有任務？（C-3 的 cap／watchdog 附近？）
7. **維護者原話寫 `gsutil`**——裁決 3 偏離它；是否要他親自點頭，由 developer-agent 判斷（我建議不用，列進每日清單即可）。

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
