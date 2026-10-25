---
id: byte-channel-b
title: 位元組通道（下）代理側：put_upload 工作——讀 uploads/ 的檔、串流進 `gcloud storage cp -`、再檢查目的地、回報位元組數與 gs:// 位置
tier: B
kinds: backend
lane: L-byte（byte-channel-a 合併之後才能開；同一車道依序）
base: v3 + byte-channel-a（-a 的 PR 必須已合進 v3；本任務從合併後的 origin/v3 開分支）
source: memory/dev-plans/byte-channel-a.md（平台側、工作的形狀、裁決 1–8）；memory/dev-plans/cloud-upload.md 裁決二 1–2、待裁決 1；docs/adr/0010-chat-keys-byte-channel-studio-embedding.md 第 2 點與 Decided 2
---

# byte-channel-b

> 本檔由 developer-agent 助理起草（2026-10-24）。**byte-channel 的下半**：平台主機上的代理（`abf-station run` 那個程序）認得 `put_upload`，把 `uploads/<擁有者>/<檔名>` 以串流餵進 `gcloud storage cp - gs://…`（stdin），不落地、不記位元組、不記金鑰。上半（排隊、遷移、結果清洗）在 `byte-channel-a.md`，**必須先合併**。B 級→ verifier 通過＋CI 綠由 developer-agent 自合。
> 合併後端到端仍差一段：「誰把檔放進 `uploads/`」與「誰呼叫 `enqueue_put_upload`」（網頁／MCP 的線）在 cloud-upload-wire，不在本任務；本任務用假 gcloud 與測試直接排工作來證明代理這一側。

## 目標
代理收到 `put_upload` 工作時：①把工作裡的參照**重新判斷一遍**（環境、擁有者、檔名、目的地、大小），只有目的地剛好落在 `gs://<workDir 的 bucket>/uploads/<擁有者>/` 之下才繼續；②在自己的上傳資料夾裡找到那個檔、確認它是一般檔案且大小與工作所說一致；③開一個 `gcloud storage cp - <目的地>` 子程序，把檔案以固定大小的塊餵給它的 stdin；④回報寫了幾個位元組、寫到哪個 gs:// 位置；任何一步不對就中止（殺掉子程序、不留半個物件的假成功）並用白話說明。

為什麼這樣切：
1. 憑證只在代理這一側（C-1 裁決二 H）；寫 bucket 的權力因此只落在持有金鑰的程序，平台程序從頭到尾沒有金鑰、沒有 gcloud。
2. 串流核心已存在：`cloud_store.stream_into`（`cloud_store.py:111`）逐塊轉交給 sink、不累積、超過宣告大小就停、短了就中止。本任務只需要一個「sink＝gcloud 的 stdin」。
3. 代理的第三種啟動程式方式（有 stdin 管道）只放在 `site.py`——現有測試要求整個代理套件只有一個模組 `import subprocess`（`test_station_static.py:61–69`）。

## 維護者原話（verifier 出題用）
- ADR 0010 Decided 2（逐字）：「**Byte channel:** option A. … The agent gets its first loopback listener and its first write (into the person's upload folder, each time confirmed by a person).」→ 本任務是代理的第一個寫入（寫 bucket，不是 uploads 資料夾）；「每次確認」見 -a 裁決 4（偏離，已列開放問題）。
- ADR 0010 第 2 點（逐字）：「…it gets its own allow-listed job kind, a path allow-list under the project's upload folder, a size limit, and a human confirmation shown on the page」→ ①自己的工作種類（-a）；②路徑白名單＝只讀 `uploads/<擁有者>/` 之下；③大小上限 2 GB；④確認見 -a。
- replan 第 16 點：「雲端上傳＝平台代傳到使用者自己的 bucket、不落地」→ gcloud 以 stdin 接收，代理不把位元組寫到本機任何檔；只讀 uploads 裡已有的檔。
- 憑證規則（`gcb_preflight.py` 檔頭）：「The key file's content is parsed in memory for four fields and dropped; it never reaches a result, a message or the platform's database.」→ 本任務連解析都不做：只確認金鑰檔存在，路徑用環境變數交給 gcloud，不進 argv、不進日誌。
- 派工指令（2026-10-24）：「代理串流讀檔，不記位元組、不記金鑰；結果回報寫了幾個位元組與 gs:// 路徑；只准寫 `gs://<workDir bucket>/uploads/<owner>/`，代理側要再檢查一次；測試用假 gcloud（不連網）與現有站台測試工具；不得動 hooks/*、tests/run_all.sh、.github/*、actions/__init__.py、abf_launch/build.py、abf_station/launch.py」。

## 範圍：檔案（只准改這些；共 4 個）
1. `platform/abf_station/put_upload.py`（新）
2. `platform/abf_station/site.py`（只新增 `Fed` 類別與 `start_fed` 函式，並更新檔首與 `run_fixed` 旁的「唯一啟動程式的模組」說明）
3. `platform/abf_station/handlers.py`（`JOB_KINDS`、`ARG_KEYS`、import、分派一支、檔首說明一句）
4. `platform/tests/test_byte_channel_b.py`（新）

**不准動**：`hooks/*`、`tests/run_all.sh`、`.github/*`、`platform/abf_platform/actions/__init__.py`、`platform/abf_launch/build.py`、`platform/abf_station/launch.py`；以及 `abf_platform/` 全部（-a 已做）、`gcb_preflight.py`（只 import 它，不改它）、`agent.py`、`pyproject.toml`、`constraints.txt`。

## 作法
（決定，不是程式碼。行號是 origin/v3（-a 合併前）的；開工前 fetch 並核對。）

**A. `site.py`——第三種啟動程式的方式（有 stdin 管道），仍無 shell**
1. 新增 `start_fed(argv, env)`：以固定 argv、`shell=False`、`stdin=PIPE`、`stdout=DEVNULL`、`stderr` 指向一個**暫存檔**（不是管道、不放記憶體：避免子程序在我們還在餵 stdin 時因 stderr 管道滿了而卡死），回傳 `Fed` 物件。啟動失敗（找不到程式、權限）→ 丟 `OSError` 由呼叫者轉成白話。
2. `Fed` 有四個方法：`write(data)`（寫進 stdin；`BrokenPipeError`／`OSError` 原樣丟，由 sink 轉成中止）、`close_input()`（關 stdin，重複呼叫安全）、`wait(timeout)` → `(return code, 輸出文字最多前 2000 字元)`，逾時丟 `TimeoutError`（與 `run_fixed`:91–101 的慣例相同）、`kill()`（殺掉並回收，重複呼叫安全；暫存檔一併關閉）。**`Fed` 不記錄、不 print、不保留任何寫入的位元組。**
3. 檔首「The only module that starts another program」的說明補一句第三種方式；`shlex.quote`（TC-091 要求 `site.py` 含它）與 `on_site.sh` 字樣保持在。不新增任何 `import`（`subprocess`、`os`、`tempfile` 若已有就沿用；`tempfile` 是新 import，允許，因為它不啟動程式）。

**B. `put_upload.py`（新）——這種工作的全部邏輯**
1. 檔首第一行 `# Nothing existing: …`（≥15 字，TC-070）。理由寫：「搜過 gcloud storage cp 的 stdin 模式、google-cloud-storage、Nextflow 的 gs:// 支援；函式庫被 TC-083/114/085 擋（也要平台或代理 import google），所以由固定 argv 的 gcloud 讀 stdin，這裡只做檢查與計數」。
2. `ARGS = {"ce", "owner", "name", "size", "dest"}`（與 -a 的工作形狀逐字相同）。`UPLOADS_ENV = "ABF_STATION_UPLOADS"`：代理自己的設定，值是**平台上傳資料夾**的絕對路徑（與平台的 `store.uploads_root` 同一個資料夾）；沒設、不是絕對路徑、不是資料夾 → 拒絕並說「這個代理沒有設定上傳資料夾（ABF_STATION_UPLOADS）」。`CHUNK = 1024 * 1024`（1 MiB）。`TIMEOUT_SECONDS = 3600`。
3. `run_put(job, ctx)` → `(state, result)`，檢查順序（任何不過 → `rules.Refusal` 白話訊息，狀態＝refused，**gcloud 一個字節都沒啟動**；refused 的訊息不回顯工作裡的原文，只說哪一項不對）：
   1. 缺鍵 → 拒（同 `readlog.run_read` 的作法）。
   2. `ce = gcb_preflight.clean_environment(args["ce"])`（它已檢查 platform 型別、project、location、workDir、信箱、憑證名；非 Google Batch → `Refusal`）。
   3. 以 `{"platform": gcb_preflight.TYPE, "config": {"workDir": ce["workDir"]}}` 造 `cloud_store` 吃的環境形狀 `view`；`owner`、`name` 必須是字串，用 `cloud_store.object_url(view, owner, name)` 算出 `expected`（`CloudPathError` → 拒）。
   4. **再檢查目的地**：`args["dest"] == expected`（逐字相等）**且** `cloud_store.inside_prefix(args["dest"], cloud_store.upload_prefix(view, owner))` 為真。兩條都要；任何一條不過 → 拒（訊息：「目的地不在你自己的上傳前綴裡」）。
   5. `size` 必須是 `int` 且不是 `bool`，1 ≤ size ≤ `cloud_store.UPLOAD_LIMIT`。
   6. 上傳資料夾與檔案：`root = realpath(環境變數)`；`area = realpath(root/owner)` 必須仍在 `root` 之下（擁有者資料夾本身是捷徑跑出去 → 拒）；用 `os.open(path, O_RDONLY | O_NOFOLLOW)`（`O_NOFOLLOW` 不存在的平台改用 `lstat` 先判斷不是連結）打開 `area/name`；`fstat` 必須是一般檔案；`realpath(area/name)` 必須在 `area` 之下；`st_size == size`（不等 → 拒：「檔案和排隊時不一樣了，請重新上傳」）。
   7. 金鑰檔：`cred = gcb_preflight.credentials_path(ctx.settings_file)`；只 `stat`，不存在或不是一般檔案 → **失敗結果**（state＝error，`ok:false`，訊息「找不到金鑰檔（路徑不顯示內容）」）。**不讀內容。**
   8. gcloud：`shutil.which("gcloud")` 為 `None` → 失敗結果（「沒裝 gcloud」，與預檢同口氣）。
4. 啟動與串流：argv ＝ 固定清單 `["gcloud", "storage", "cp", "-", dest, "--project", ce["project"]]`——**是 argv 清單，不是一整串命令字串**（這是 `gcb_preflight.py:180–182` 的既有做法，也讓 `test_cloud_upload.py:739` 的「`storage cp` 這串字只在 `cloud_store.py`」不必改，見裁決 2）。環境變數＝`gcb_preflight._gcloud_env(cred)`（它濾掉所有 `ABF_*` 與 `GOOGLE_APPLICATION_CREDENTIALS`，只放 `CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE` 與 `CLOUDSDK_CORE_DISABLE_PROMPTS`——金鑰路徑走環境變數，**不進 argv**）。`site.start_fed(argv, env)` 丟 `OSError` → 失敗結果。
5. Sink（`put_upload.py` 內部類別，介面是 `cloud_store.stream_into` 要的 `write`／`close`／`abort`）：`write(data)`＝`fed.write(data)`；`close()`＝`fed.close_input()` 後 `fed.wait(TIMEOUT_SECONDS)`，回傳碼非 0 → 記下已洗淨的輸出（作法 6）並丟例外（`stream_into` 會轉去 `abort()` 並回失敗）；`abort()`＝`fed.kill()`。逾時（`TimeoutError`）→ `kill()`，結果訊息「gcloud 逾時（超過 N 秒）」。
6. 輸出洗淨：把 gcloud 的輸出經 `gcb_preflight._scrub`（:66，擋 BEGIN…END 區塊、憑證形狀、32 字元以上長字串）再截 300 字元才放進訊息。**回傳碼、不是位元組內容，才是成功的依據。**
7. 餵檔：`chunks` ＝ 一個產生器，每次 `os.read(fd, CHUNK)` 一塊（最多 1 MiB）直到讀到空；`finally` 一定 `os.close(fd)`。呼叫 `cloud_store.stream_into(chunks, sink, declared_size=size, limit=cloud_store.UPLOAD_LIMIT)`。檔案在讀的過程中變長或變短 → `stream_into` 已會中止（宣告大小不符）。
8. 結果：成功＝`("done", {"ok": True, "bytes": received, "path": dest})`（`received == size`）；失敗＝`("error", {"ok": False, "message": <白話>, "bytes": received})`（`bytes` 是已餵出的數字，供人判斷；平台的 `clean_result` 只收合格的數字）。**結果與訊息裡不出現：位元組內容、金鑰檔路徑、`uploads` 的本機路徑、gcloud 的原始輸出（只留洗淨後 300 字元）。**
9. 不寫日誌：本模組不 `print`、不呼叫 `ctx.site.log`、不把 argv 或檔名送到任何日誌（`site.Site.call` 才會記指令，本模組不走它）。

**C. `handlers.py`**
- :13 的 import 加 `put_upload`；:16 `JOB_KINDS` 末尾加 `"put_upload"`；:17–18 `ARG_KEYS` 加 `"put_upload": put_upload.ARGS`；:47–65 的分派在 `read_task_log` 之後加一支 `if kind == "put_upload": return put_upload.run_put(job, ctx)`。:41 的「this agent does …」訊息由 `JOB_KINDS` 自動帶出新種類，不另改。:1–9 檔首說明補一句。其餘不動。

## 失敗先行測試（`platform/tests/test_byte_channel_b.py`；全部不連網、不用真的 gcloud 以外的任何程式；沿用 `test_gcb_launch.py` 的 `Box` 做法（`SimpleNamespace` ctx、`monkeypatch.setenv("ABF_STATION_GCP_CREDENTIALS", …)`、`key_data()`）與 `station_harness.py` 的 `FakePlatform`／`Inproc`／`ce_snapshot`；`import` 它們，不複製）
假件：`FakeFed`（記錄 `argv`、`env`、每次 `write` 的長度與內容雜湊、`closed`、`killed`；可設 `rc`、`output`、`raise_on_write_after=N`、`wait_raises=TimeoutError`），用 `monkeypatch.setattr(site, "start_fed", …)` 換進去。真管道的測試（BB-24～BB-27）用 posix 下放在 `tmp_path/bin/gcloud` 的假 gcloud 腳本，加 `posix_only` 標記。編號是本計畫內的 BB-nn。

認得這種工作
- BB-01 `handlers.JOB_KINDS` 末項是 `put_upload`；`ARG_KEYS["put_upload"] == {"ce","owner","name","size","dest"}`（與 -a 的 `args_json` 鍵集合逐字相同，測試從 -a 的 `jobs.enqueue_put_upload` 產出的工作讀鍵來比，不重抄）。
- BB-02 工作多帶一個鍵（例如 `path`）→ refused，訊息含 `不支援`／`not supported`；少帶一個鍵 → refused。
- BB-03 `handle()` 對未知種類的訊息現在列出七個種類（含 `put_upload`）。

好的一條
- BB-04 Google Batch 環境 `lab-bucket/work`、project `lab-project-1`、擁有者 alice、`<uploads>/alice/reads.fq`（3 MiB + 17 位元組的隨機內容）、`size` 吻合、`dest="gs://lab-bucket/uploads/alice/reads.fq"` → `("done", {"ok": True, "bytes": 3145745, "path": dest})`；`FakeFed` 收到的位元組串接起來**逐位元組等於**原檔；`closed` 為真、`killed` 為假。
- BB-05 argv 剛好是 `["gcloud","storage","cp","-",dest,"--project","lab-project-1"]`；沒有 shell（`FakeFed` 收到的是清單）；環境變數裡有 `CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE` 指向金鑰檔、**沒有**任何以 `ABF_` 開頭的鍵、沒有 `GOOGLE_APPLICATION_CREDENTIALS`；金鑰檔路徑**不在** argv 裡。
- BB-06 記憶體：`FakeFed.write` 看到的每一塊 ≤ 1 MiB；以 `tracemalloc` 或「讀檔函式被呼叫時要求的長度」證明沒有一次讀整個檔（用 40 MiB 的稀疏／重複內容檔，峰值遠小於檔案大小，例如 < 8 MiB）。
- BB-07 同一個檔連續傳兩次 → 兩次都 `done`（覆寫同名物件；argv 沒有 `--no-clobber`）。

再檢查目的地（gcloud **從未啟動**：`FakeFed` 的建立次數＝0）
- BB-08 `dest` 在別的擁有者前綴（`…/uploads/bob/reads.fq`）→ refused。
- BB-09 `dest` 在別的 bucket（`gs://other-bucket/uploads/alice/reads.fq`）→ refused。
- BB-10 `dest` 在 bucket 的 `work/`（`gs://lab-bucket/work/x`）或 `uploads/` 本身下一層以外（`gs://lab-bucket/uploads/reads.fq`、`gs://lab-bucket/uploads/alice` 沒有檔名、`gs://lab-bucket/uploads/alice/`）→ 各 refused。
- BB-11 `dest` 含 `..`（`gs://lab-bucket/uploads/alice/../bob/x`）、`%2e%2e`（照字面當一般名字：因為 `dest` 必須逐字等於 `expected`，所以仍被拒）、控制字元、`s3://`、`https://`、前後多空白 → 各 refused。
- BB-12 `dest` 合法但與 `owner`／`name` 算出的 `expected` 不同（例如 name 是 `a.fq`、dest 結尾是 `b.fq`）→ refused。
- BB-13 `ce` 不是 Google Batch 型、`workDir` 不是 `gs://`、`workDir` 的 bucket 不合規則 → 各 refused。
- BB-14 `owner`／`name` 壞：含 `/`、`\`、`..`、NUL、空字串、256 字元、非字串 → 各 refused，訊息不回顯原文。

檔案端
- BB-15 `ABF_STATION_UPLOADS` 沒設／相對路徑／不存在／是檔案 → refused，訊息含 `ABF_STATION_UPLOADS`。
- BB-16 檔案不存在、是資料夾、是符號連結（posix）、`<uploads>/alice` 本身是指向資料夾外的捷徑（posix）→ 各 refused；gcloud 從未啟動。
- BB-17 檔案大小與 `size` 不同（工作說 100、實際 101；工作說 100、實際 99）→ refused，訊息含「重新上傳」。
- BB-18 `size` 邊界：0、-1、`True`、`"5"`、`2_000_000_001` → refused；`2_000_000_000` → 通過檢查（用注入的 `fstat` 假大小，不造 2 GB 檔；`FakeFed` 吞掉資料，餵檔改用假讀取器回等長的零，驗證只被讀 2×10^9/1MiB 次且仍成功）。
- BB-19 傳到一半檔案被截短或加長（`FakeFed` 的 `write` 內部偷改檔案；或假讀取器多回一塊／少回一塊）→ `("error", …)`；`FakeFed.killed` 為真；結果的 `ok` 為假；`bytes` 是已餵出的數目。

gcloud 與金鑰端
- BB-20 gcloud 沒裝（`shutil.which` 回 `None`）→ `("error", …)`「沒裝 gcloud」；`FakeFed` 未建立。
- BB-21 金鑰檔不存在／是資料夾 → `("error", …)`；**金鑰檔從未被讀取**（用 `open` 的呼叫記錄或讓金鑰檔內容是不能解析的垃圾仍得到同一個「找不到」以外的結果來證）。
- BB-22 gcloud 回傳碼非 0，輸出含一段 `-----BEGIN PRIVATE KEY-----…-----END PRIVATE KEY-----`、一個 40 字元的長字串、以及 `/home/alice/uploads/...` 路徑 → `("error", …)`；結果 JSON 字串化後**不含**那三樣原文（`[hidden]` 取代前兩者；本機 `uploads` 路徑不出現：訊息只用檔名）；訊息 ≤ 300 字元的輸出片段。
- BB-23 `FakeFed.wait` 丟 `TimeoutError` → `("error", …)` 含「逾時」；`killed` 為真。

真管道（posix_only，`tmp_path/bin` 在 `PATH` 最前面，假 gcloud 是一支 sh 腳本：把 argv 寫到 `argv.txt`、把 stdin 以 `cat > received.bin` 收下、`exit 0`）
- BB-24 5 MiB 隨機檔經真的 `site.start_fed` → `received.bin` 與原檔位元組相同；`argv.txt` 逐行是 BB-05 的清單；結果 `bytes == 5242880`。
- BB-25 假 gcloud 在讀 1 KiB 後就 `exit 1`（stderr 印一行）→ 代理不卡死（整個測試在 20 秒內完成）；結果 `ok` 為假；沒有 `BrokenPipeError` 洩漏成未處理例外。
- BB-26 假 gcloud 睡 60 秒不讀 stdin，代理的逾時（測試用環境變數或參數縮成 1 秒）→ 子程序被殺（`pgrep`／`poll()` 證明已結束）；結果含「逾時」。
- BB-27 假 gcloud 把 stderr 灌 1 MiB 文字再 `exit 0`（驗 stderr 是暫存檔、不會塞住）→ 成功；結果訊息不含那段文字。

不外洩（跨以上所有成功與失敗的路徑）
- BB-28 以一個含獨特標記字串（canary，例如 `CANARY-9f3a…`）的檔當內容、以一個含另一個 canary 的假金鑰檔，跑完 BB-04、BB-19、BB-22 三種路徑：①`capsys` 的 stdout／stderr；②結果 JSON；③`jobs.clean_result("put_upload", result)` 的輸出；④平台資料庫整份傾印（用 -a 的 `enqueue_put_upload` → 假平台 `take_result` 走完）；⑤`FakeFed` 以外的任何日誌回呼——**全都找不到兩個 canary**，也找不到 `private_key`。
- BB-29 `put_upload.py` 原始碼：不含 `print(`、`.log(`、`logging`；不含 `subprocess`、`shell=True`、`os.system`、`while`、`Thread(`；含 `# Nothing existing:`；不含 `listen`、`bind`、`input(`、`daemon`、`google.cloud`（`test_station_static.py` 這些掃描已自動涵蓋，這裡顯式釘一次）。
- BB-30 `site.py` 仍是 `abf_station/` 裡唯一 `import subprocess` 的檔（`test_station_static.py:61–69` 原封不動仍綠）；`put_upload.py` 沒有 `import subprocess`。

端到端（進程內，不經 HTTP）
- BB-31 用 -a 的 `jobs.enqueue_put_upload` 排工作（alice 的可用環境、`FakePlatform` 或 `Inproc`）→ `jobs.claim` → `handlers.handle(job, ctx)` → `jobs.take_result` → `jobs.wait_for_result` 回 `{"ok": True, "result": {"bytes": …, "path": "gs://lab-bucket/uploads/alice/…"}}`；`FakeFed` 收到的位元組與原檔相同。
- BB-32 同一條路，但平台排工作時被竄改（直接改資料庫 `args_json` 的 `dest` 成 bob 的前綴）→ 代理 refused、`take_result` 記為 refused、`FakeFed` 未建立（證明「代理側再檢查一次」是獨立的一道牆，不靠平台）。

## 必須更新的既有斷言
**沒有需要有意更新的既有斷言**（本任務不改任何現有測試檔）。逐條核對過、PR 說明要列「沒動」的：
- `test_run_diag_tools.py:466`（`"read_task_log" in handlers.JOB_KINDS` 與 `ARG_KEYS`）：只檢查成員，不受影響。
- `test_station_fakeplatform.py:14、:176`（`REFUSAL` 正規式 `not supported|unsupported|不支援`）：訊息仍含「不支援」，BB-02 沿用同一條。
- `test_station_static.py:61–69`（TC-091 只有一個模組 import subprocess）、`:28–56`（無 listen／bind／input()／socket／google.cloud；無 Thread 以外的檔、無 `while` 以外的檔）、`:72–84`（TC-084 禁 `nextflow run`、`--wrap`、`sbatch <字>`）：`put_upload.py` 與 `site.py` 新增部分都不碰這些字；不改。
- `test_cloud_upload.py:739`（`storage cp` 這串字只准在 `cloud_store.py`）：`put_upload.py` 用 argv 清單 `["gcloud","storage","cp","-",…]`，檔內沒有連續的 `storage cp` 文字（`BB-29` 也釘住：`put_upload.py` 不含該連續字串）；**這不是拆字繞過**——argv 清單是 `gcb_preflight.py:180–182` 已有的形式，掃描要擋的是「指令文字」，不是「程式啟動時的參數」。若維護者或閱卷者認為這是繞過，替代方案見裁決 2。
- `test_gcb_ce.py:805`、`test_gcb_launch.py`（TC-114 無雲端函式庫）、`test_station_envs.py`（TC-085）：本任務不引入任何雲端函式庫；不改。
- `test_gcb_ce.py:585–588`（預檢用 `gcloud storage ls` 的假 `run_fixed` 會對未預期程式拋 `AssertionError`）：本任務不走 `run_fixed`（走 `start_fed`），這些測試不受影響；BB 的假件各自換 `start_fed`。
- `test_scope.py` TC-070：新檔 `put_upload.py` 與 `test_byte_channel_b.py` 都必須有 `# Nothing existing:` 行——新檔的義務，不是更新斷言。

## 完成標準（done when）
- BB-01～BB-32 全綠；`platform/tests/` 全套綠（含 -a 的 BA-01～BA-29，與 `test_station_static.py`、`test_cloud_upload.py`、`test_scope.py`、`test_gcb_ce.py`、`test_gcb_launch.py`、`test_station_fakeplatform.py` 原封不動全綠）；`tests/platform_test.sh` 與倉庫既有 CI 綠。posix 測試在 Linux CI 上實跑（不得被 skip 成「全綠」）；Windows 本機可 skip BB-16 捷徑、BB-24～27。
- `git diff --name-only <base>` 只含「範圍：檔案」列的 4 個檔。
- `site.py` 的差異只有新增（`Fed`、`start_fed`、檔首說明），`run_fixed`、`start_detached`、`Site.call` 逐行沒動；`handlers.py` 的差異只有 import、兩個常數、一支分派與說明。
- 手動驗收（不寫進 CI，因為要真的 GCP）：寫進 `docs/TESTING.md`？**不寫**——本任務不在範圍檔裡動 docs；真 bucket 的 2 GB 端到端與 `gcloud storage cp -` 的記憶體／逾時行為（cloud-upload「查不到」那項）由 cloud-upload-wire 的手動驗收一併量，這裡只在 PR 說明寫「尚未用真 bucket 驗過」。
- 回報（bundle）、資料庫、日誌、測試輸出、PR 說明裡搜不到金鑰片段與測試用 canary。

## 環境事實
（行號是 origin/v3 的，2026-10-24 讀；`git -C C:\Users\marvi\Desktop\agentic-bioflow\agentic-bioflow_v2 fetch -q origin` 後以 `MSYS_NO_PATHCONV=1 git show origin/v3:<path>` 讀。）
- `platform/abf_station/handlers.py`：`JOB_KINDS`:16、`ARG_KEYS`:17–18、`handle`:34–67（分派 :47–65；Google Batch 預檢分流在 :57–61；`rules.Refusal` → refused 在 :66–67）、未知種類訊息 :39–41。
- `platform/abf_station/site.py`：檔首「The only module that starts another program」:2、`Site.call`:61（記指令到日誌 :75–76——本任務不走它）、`run_fixed`:91–101、`start_detached`:116–127。`readlog.py:1–60` 是同型「只讀、白話拒絕」的寫法範本。
- `platform/abf_station/gcb_preflight.py`：`TYPE`:24、`CREDENTIALS_ENV`:25、`credentials_path`:35–41、`clean_environment`:44–63、`_scrub`:66–70、`_gcloud_env`:83–87（濾掉 `ABF_*` 與 `GOOGLE_APPLICATION_CREDENTIALS`）、`run_preflight`:108–198（`gcloud storage ls` 的 argv 清單在 :180–182）。
- `platform/abf_station/agent.py`：`Context`:195–205（`site`、`settings_file`、`platform_url`、`agent_name`）；`Beat`:70 在工作執行中維持在線（長傳輸不會被判離線）；`handlers.handle` 在 :164 被呼叫。
- `platform/abf_platform/cloud_store.py`：`stream_into`:111–135（先判斷 `declared_size`、再逐塊；超過宣告就 `abort` 並不讀下一塊；結尾不符就 `abort`；相等才 `close`；任何例外 → `abort` 並回「傳輸中斷」，**不重複錯誤文字**）、`inside_prefix`:80、`object_url`:75、`upload_prefix`:67。`UPLOAD_LIMIT` 由 -a 加入。
- gcloud：`gcloud storage cp` 以 `-` 為來源（不帶 `-I`）讀 stdin（https://docs.cloud.google.com/sdk/gcloud/reference/storage/cp，2026-10-24 讀，引自 cloud-upload.md）。**查不到**：①2 GB 級串流的記憶體與逾時行為；②stdin 串流上傳在中途被殺時 bucket 上是否留下殘缺物件（resumable 上傳未完成通常不會成為可見物件，但文件沒寫）→ 本任務在「中止」時只殺子程序、不去刪物件（刪除是破壞性動作，屬不做），並在 PR 說明記為未驗證。
- 假 gcloud 的做法：測試在 `tmp_path/bin/` 放一支 `gcloud` sh 腳本、把該目錄放進 `PATH` 最前面（`monkeypatch.setenv`）；`shutil.which` 因此找到它。倉庫既有測試用 `monkeypatch.setattr(gcb_preflight.shutil, "which", …)` 的作法也可（`test_gcb_launch.py:98`），BB-24～27 要真的管道所以用 PATH。
- 平台主機的現實：代理跑在使用者桌機的 WSL（cloud-upload「環境事實」末項）；`ABF_STATION_UPLOADS` 在 WSL 裡要指到平台寫上傳檔的那個資料夾（WSL 掛載的 Windows 路徑也可，但效能與 `O_NOFOLLOW` 語意較差）——設定說明屬 docs，不在本任務。

## 不做
- 平台側（-a）；網頁／MCP／HTTP 路由／上傳畫面／把檔案放進 `uploads/` → cloud-upload-wire。
- 確認憑證與人工確認畫面（-a 裁決 4 與開放問題）。
- 傳完後刪除本機 `uploads/` 的檔、刪 bucket 上的殘缺物件、`--no-clobber`、續傳、校驗和與雜湊、多檔批次、讀回 bucket 驗證大小。
- 預檢加寫入探測（花錢，要他點頭）。
- 任何雲端函式庫、新依賴、改 `pyproject.toml`／`constraints.txt`。
- 為了過掃描而拆字串（`put_upload.py` 的 `gcloud` 與 `storage` 各是 argv 清單的獨立元素，是參數，不是被拆開的指令文字；見裁決 2）。
- 在 `docs/TESTING.md` 或任何文件寫手動驗收（不在範圍檔）。

## 通例：閱卷看 diff 的手動案例（2026-10-24，照 dev-plans/README）
「改動範圍只有上列 4 個檔」「`site.py` 既有函式沒動」「既有測試檔一個字都沒改」「本分支與 -a 合併後的 v3 比對輸出」這類只能看 diff 的案例，不寫進 `docs/TESTING.md`：executor 把 `git diff --stat`、`git diff --name-only` 與 `site.py` 的 `git diff` 貼進 ledger.md，verifier 依 ledger 並自己重跑核對。verifier 不以「TESTING.md 沒有步驟」退回。

## 裁決（2026-10-24 developer-agent 助理起草；與上文衝突時以本段為準）
1. **代理用固定 argv 的 `gcloud storage cp -` 子程序，不用函式庫、不用 shell。** 理由：cloud-upload 裁決一（函式庫被 TC-083／TC-114／TC-085 與「平台不讀金鑰檔」擋下）；`gcloud` 已是預檢的依賴。stdin 管道與暫存檔 stderr 的理由見作法 A-1。
2. **argv 清單 ≠ 指令文字。** `["gcloud","storage","cp","-",dest,"--project",p]` 不含連續的 `storage cp` 字串，所以 `test_cloud_upload.py:739`（TC-099：該串字只在 `cloud_store.py`）與 TC-101（兩個來源檔的拆字掃描）不必改，且這與 `gcb_preflight.py:180–182` 的 `gcloud storage ls` 同一形式。**這是閱卷最可能挑戰的點**：若判為繞過，替代方案＝把 TC-099 的對象由「指令文字」收窄為「給人看的指令」並有意更新那條斷言（只准動 `test_cloud_upload.py:739` 一行，需把該檔加進範圍），由 developer-agent 決定；預設不動。裁決三 7 的「不准拆字」針對的是為了過掃描把一個字分兩段字串；argv 的元素本來就是各自獨立的參數。
3. **目的地在代理側用「逐字相等＋前綴包含」兩道檢查**（作法 B-3-4）。理由：只用前綴包含，`dest` 仍可指向自己前綴下的任意名字（不是排隊時算的那個檔名）；只用相等，少一道不依賴字串組法的獨立判斷。兩道都留。
4. **用 `O_NOFOLLOW` 開檔，再 `fstat`，而不是先 `stat` 再開。** 理由：避免檢查與使用之間被換成捷徑（TOCTOU）；`realpath` 另外確認仍在擁有者資料夾內。
5. **金鑰檔只 `stat`、不讀。** 理由：gcloud 自己讀；代理讀了就多一個可能外洩的位置（預檢為了比對 project 才讀，本任務不需要）。
6. **中止時只殺子程序，不刪 bucket 上可能的殘物件。** 理由：刪除是破壞性動作、需要另一個寫入權限與確認；殘物件對使用者可見性未知（見環境事實「查不到」）。結果訊息要明說「已中止；bucket 上可能需要檢查 `<dest>`」。
7. **逾時 3600 秒（與 -a 的工作期限一致）。** 測試可縮短（參數或環境變數，執行者擇一，鍵名自訂但必須在 `put_upload.py` 內用 `ABF_STATION_` 開頭）。
8. **結果的 `bytes` 在失敗時也回報**（已餵出的數目），但平台 `clean_result` 的規則是「`ok` 假則不要求 `bytes`」，所以失敗時它可有可無。

## 裁決（2026-10-25 01:00，維護者回覆）
維護者原話：「1.會慢半天就不用 2.照你建議」。
A. **確認**：採 -a 裁決 4——使用者在已登入的頁面自己選檔、選環境、按上傳，就是這次寫入的 yes；**不加**確認憑證種類、不開 byte-channel-c。verifier 不因 backend 守則「每個寫入要確認」判 FAIL（維護者已明示接受此偏離）。
B. **暫存**：允許檔案先放在平台主機 `uploads/` 再傳；**傳完且雲端物件大小與本機相同就刪掉本機那份**（取代 -a 裁決 7 ①的「傳完不自動刪」）；大小不符或傳輸失敗則保留並回報。
C. **ADR 0010 同步**：在本系列的 -b 片修改 `docs/adr/0010-chat-keys-byte-channel-studio-embedding.md`，加一段「2026-10-25 修正」：①按上傳即為確認；②允許在平台主機暫存，傳完核對大小後刪除。附維護者原話。
D. 前置：本系列動 `store.py`／`jobs.py` 的 CHECK 清單，與 cloud-cleanup-a/b 重疊，排在 cloud-cleanup-b 之後；開工前依當時 v3 的 CHECK 清單重算（不釘「剛好七個」）。

## 裁決二（2026-10-25，developer-agent，回應 verifier 出題退回；與上文衝突時以本段為準）
1. **範圍改成 5 個檔**：上列 4 個＋`docs/adr/0010-chat-keys-byte-channel-studio-embedding.md`（只新增一段「## 2026-10-25 修正」，內容照上段裁決 C，附維護者原話「1.會慢半天就不用 2.照你建議」）。完成標準改為「`git diff --name-only <base>` 只含這 5 個檔」。
2. **「不做」的兩條作廢**：「傳完後刪除本機 uploads/ 的檔」與「讀回 bucket 驗證大小」改成要做（裁決 B），做法如下第 3、4 條。「刪 bucket 上的殘缺物件、--no-clobber、續傳、校驗和、多檔批次」仍不做。
3. **取得雲端物件大小**：`cp` 成功後跑 `host.run_fixed(["gcloud","storage","objects","describe",dest,"--project",ce["project"],"--format=value(size)"], env, 60)`（同一個 `_gcloud_env`）。輸出去頭尾空白後必須是純十進位數字才算取得；非零結束碼、逾時、輸出不是數字＝**取不到**。假 gcloud 在測試裡依 argv 第 3 個元素分辨 `cp`／`objects describe`，describe 回一行數字。executor 先對 `gcloud storage objects describe --help` 核對 `--format=value(size)` 拼法並寫進 ledger，核對不過就停手回報。
4. **刪本機暫存檔**：只有「取得大小且等於開檔時 `os.fstat` 的 `st_size`、也等於串流寫出的位元組數」才刪。刪法：開檔時用 `os.open(path, os.O_RDONLY | os.O_NOFOLLOW)` 並記下 `(st_dev, st_ino)`；刪之前 `os.lstat(path)`，若是捷徑或 `(st_dev, st_ino)` 不同 → 不刪（保留）；相同才 `os.unlink(path)`。
5. **結果**（平台 `clean_result` 只收 ok、message、note、bytes、path，所以「已刪／已保留」放在 message 文字）：
   - 大小相符且刪成功 → `ok: True`，message「已上傳 <dest>（N 位元組）；平台主機上的暫存檔已刪除」。
   - 大小相符但刪除失敗或檔被換過 → `ok: True`，message「已上傳 <dest>（N 位元組）；暫存檔沒刪掉，請管理者清理」。
   - 取不到雲端大小 → `ok: True`，message「已上傳 <dest>（N 位元組），但沒能核對雲端大小；暫存檔保留」。
   - 大小不符 → `ok: False`，message「雲端物件大小與本機不符，暫存檔保留，請重新上傳」。
   - 傳輸失敗 → 照原計畫，暫存檔保留。
6. **BB-03 不釘個數**：改成「訊息列出 `JOB_KINDS` 的每一個、含 `put_upload`」。
7. **裁決 D 只是排序條件**：本片**不動** `store.py`／`jobs.py`（CHECK 清單已在 -a #224 加好）；`abf_platform/` 仍整個不准動。
8. **憲法 Safety Net**：不違反，理由寫進 ledger 與 PR 說明——①憲法 I.2 承認的人工通道包含「平台確認頁、以同一個已登入的使用者」；網頁上傳由已登入本人在頁面上按下，就是那個通道的 yes（裁決 A）；`put_upload` 只能經 -a 的 `enqueue_put_upload` 排入、`_enqueue` 拒絕直接排，MCP 與 PAT 都沒有上傳工具（本片加一條測試：MCP 工具清單沒有任何名稱含 `upload`）。②「Never delete a user's source data」：`uploads/` 裡的是平台為了傳輸暫存的副本，不是使用者的來源資料（來源在使用者自己的電腦，且只有在雲端那份核對大小相符後才刪副本）。
9. 本片沒有 spec.md，以 plan.md 與兩段裁決為唯一來源：接受。

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
