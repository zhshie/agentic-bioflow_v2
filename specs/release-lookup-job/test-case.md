# 測試案例：站台代理讀管線公開檔（release-lookup-job）

**規格**：`specs/release-lookup-job/plan.md`（本任務沒有獨立 spec.md，計畫兼作規格；號碼大的裁決蓋小的）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；測試確認它真的沒做，或會明白說「不支援」而不是悄悄亂做。

名詞一句話：**站台代理**＝跑在使用者那台能上網的機器上、替平台跑腿的小程式；**平台**＝記帳與排工作的主程式，自己不連網；**工作（job）**＝平台排給代理的一張單；**釘死版本**＝用精確版本號（例 `2.18.0`）或 40 位的 commit 碼，不用 `main` 這種會變的分支名；**假的抓取函式（OPEN）**＝測試用來代替真正上網的替身，確保測試絕不連真的 GitHub。

驗證方式的「自動」＝executor 寫的測試檔（每條在註解寫 TC 編號）；「手動」＝閱卷者讀 diff／文件，或 `docs/TESTING.md` 裡的手動步驟。

## User Story 1 — 站台代理替平台去 GitHub 讀四類公開檔（優先度 P1）

維護者原話：「好，放寬」（2026-10-25；內容＝讓站台代理新增唯讀工作種類，讀公開 GitHub 檔——`nextflow_schema.json`、`assets/schema_input.json`、`docs/images`、最新 release tag）。放寬的範圍就是這四類，不多不少。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | S-01 | 功能 | 代理的工作種類清單 `JOB_KINDS` | 檢查清單 | `pipeline_files` 在清單中恰出現一次，而且排在最後（在 `put_upload` 之後，裁決四第 11 條）；原有各種類彼此的先後順序不變；測試不寫死種類總數 | 自動：`platform/tests/test_station_pipeline_files.py` |
| TC-002 | S-01 | 功能 | 代理的參數表 `ARG_KEYS` | 檢查 `pipeline_files` 的允許參數 | 恰為 `{"repo","revision","parts"}`；且 `JOB_KINDS` 與 `ARG_KEYS` 的種類集合完全相同 | 自動：同上 |
| TC-003 | S-01 | 例外 | 代理收到一個不認得的工作種類 | 呼叫 `handlers.handle` | 回「拒絕」，訊息的支援清單裡含 `pipeline_files` | 自動：同上 |
| TC-004 | S-02；原話「好，放寬」 | 功能 | 判斷網址能不能連的函式 `allowed(url)` | 餵 `https://github.com/…`、`https://raw.githubusercontent.com/…`、`https://api.github.com/…` | 三個都回 True | 自動：同上 |
| TC-005 | S-02；原話「好，放寬」（範圍不多不少）；裁決三第 6 條 | 例外 | 同上 | 餵 `http://`（非加密）、`https://github.com.evil.com/x`、`https://evil.com/github.com`、`https://raw.githubusercontent.com@evil.com/x`、`https://raw.githubusercontent.com:8443/x`、`ftp://…`、`https://nf-co.re/pipelines.json`、空字串 | 全部回 False（連 nf-co.re 也不行） | 自動：同上 |
| TC-006 | S-02 | 例外 | 假的抓取函式 OPEN 會記次數；給上一條那些不合格網址 | 讓代理跑 | OPEN 被呼叫 0 次（不合格的網址連請求都不發） | 自動：同上 |
| TC-007 | S-03 | 功能 | ampliseq `2.18.0`，要 schema＋schema_input＋diagram 三部分，OPEN 回計畫指定的 fixture（`platform/tests/fixtures/schema/ampliseq-2.18.0.nextflow_schema.json`、`tests/fixtures/schema_input/ampliseq-2.18.0.json`、四筆目錄清單） | 跑 `run_fetch` | 請求依序恰為三個：`https://raw.githubusercontent.com/nf-core/ampliseq/2.18.0/nextflow_schema.json`、`…/assets/schema_input.json`、`https://api.github.com/repos/nf-core/ampliseq/contents/docs/images?ref=2.18.0`，沒有第四個 | 自動：同上 |
| TC-008 | S-03 | 功能 | 同上 | 看結果 | 回 `("done", {"ok": True, …})`；`parts.schema.status == "ok"`，且 `text` 與 fixture 檔逐字相同 | 自動：同上 |
| TC-009 | S-03 | 功能 | 同上 | 看結果的 `parts` | 鍵剛好是被要求的三個；`parts.diagram == {"status":"ok","name":"ampliseq_workflow.png","type":"image/png","size":753702}`（四張圖裡選了這張） | 自動：同上 |
| TC-010 | S-04 | 功能 | 目錄清單的各種組合 | 挑流程圖 | 規則依序：名稱含 `metro` 的在前；其次 png 在 svg 前；其次名稱短的在前；最後字母序。例：有 metro 的 svg 與沒 metro 的 png → 選 metro 那張；同為 workflow → 選 png；同為 png → 選名稱短者 | 自動：同上 |
| TC-011 | S-04 | 功能 | 第一候選的 `size` 為 2,000,001、第二候選為 100；另一組候選沒有 `size` 欄 | 挑流程圖 | 前一組選第二個；沒有 `size` 的候選視為大小未知、照樣可選（交給讀取上限把關） | 自動：同上 |
| TC-012 | S-04 | 例外 | 有候選但每一張 `size` 都超過 2,000,000 | 挑流程圖 | `diagram` 狀態為 `too_large` | 自動：同上 |
| TC-013 | S-04 | 例外 | 沒有任何候選；或目錄清單回 404；或檔名含空白、`../`、`.gif` | 挑流程圖 | `diagram` 為 `{"status":"none"}`；名稱含空白、`../`、`.gif` 的不被當候選 | 自動：同上 |
| TC-014 | S-05 | 功能 | `parts=["image"]`，OPEN 對圖回 PNG 位元組（開頭是 PNG 魔術字） | 跑 `run_fetch` | 請求恰為「目錄清單」加 `https://raw.githubusercontent.com/nf-core/ampliseq/2.18.0/docs/images/ampliseq_workflow.png` | 自動：同上 |
| TC-015 | S-05 | 功能 | 同上 | 看結果 | `parts.image.data_b64` 解碼後與假回的位元組逐位元組相同；`type` 為 `image/png`；結果裡同時有 `diagram` | 自動：同上 |
| TC-016 | S-06 | 例外 | 圖的內容開頭不是 PNG 魔術字；或 SVG 前 4096 字內沒有 `<svg`；或 SVG 不是合法 UTF-8 | 跑 `run_fetch` | 該部分狀態 `bad_response` | 自動：同上 |
| TC-017 | S-06 | 例外 | 圖超過 2,000,000 位元組 | 跑 `run_fetch` | 該部分 `too_large`；OPEN 從沒被要求讀超過它的 `limit` | 自動：同上 |
| TC-018 | S-07 | 功能 | `parts=["tags"]`、`revision=None`，OPEN 回 git 公告（含服務行、flush、含 NUL 能力清單的 HEAD 行、`refs/heads/main`、`refs/pull/1/head`、`refs/tags/2.18.0`、`refs/tags/2.18.0^{}`、`refs/tags/3.0.0`、`refs/tags/3.0.0dev`） | 跑 `run_fetch` | 請求只有一個：`https://github.com/nf-core/ampliseq.git/info/refs?service=git-upload-pack` | 自動：同上 |
| TC-019 | S-07 | 功能 | 同上 | 看 `parts.tags.text` | 恰為 `<sha>\trefs/tags/2.18.0\n<sha>\trefs/tags/3.0.0\n<sha>\trefs/tags/3.0.0dev\n`（分支、pull、`^{}` 都濾掉、能力清單切掉）；`releases.parse_ls_remote(text)` 得 `["2.18.0","3.0.0","3.0.0dev"]`；`releases.pick_latest` 得 `"3.0.0"` | 自動：同上 |
| TC-020 | S-08 | 例外 | tag 公告：`Content-Type` 不對；或長度欄不是十六進位；或內容被截斷 | 跑 `run_fetch` | 三種都是 `bad_response` | 自動：同上 |
| TC-021 | S-08 | 例外 | tag 公告超過 4,000,000 位元組 | 跑 `run_fetch` | `too_large` | 自動：同上 |
| TC-022 | S-09 | 例外 | `assets/schema_input.json` 回 404，其餘 200 | 跑 `run_fetch` | 該部分 `not_found`、其餘 `ok`；整體仍 `done`、`ok True` | 自動：同上 |
| TC-023 | S-10 | 例外 | schema 回 1,000,001 位元組 | 跑 `run_fetch` | 該部分 `too_large`，且沒有 `text` 鍵 | 自動：同上 |
| TC-024 | S-11 | 例外 | 目錄 API 回 403 並帶 `X-RateLimit-Remaining: 0`；另一組回 429 | 跑 `run_fetch` | 兩組都是 `rate_limited` | 自動：同上 |
| TC-025 | S-11 | 例外 | 回 403 但 remaining 不是 0；另兩組分別回 500、301（轉址） | 跑 `run_fetch` | 三組都是 `bad_response`；301 不會被跟隨（沒有第二次請求） | 自動：同上 |
| TC-026 | S-11 | 例外 | 目錄 API 被限速，raw 的 schema、schema_input 正常 | 跑 `run_fetch` | raw 那兩部分仍 `ok`，只有 `diagram` 顯示 `rate_limited` | 自動：同上 |
| TC-027 | S-12；原話「好，放寬」（唯讀、不帶憑證） | 例外 | 成功路徑，記下每個請求的方法與標頭 | 檢查 | 全部是 `GET`；標頭裡沒有 `Authorization`、`Cookie`、任何 `X-` 開頭者 | 自動：同上 |
| TC-028 | S-12 | 功能 | 同上 | 看 `User-Agent` | 以 `abf-station/` 開頭 | 自動：同上 |
| TC-029 | S-12b；原話「Pin an exact pipeline revision, never a branch…」 | 例外 | `repo` 為 `""`、`../x`、`a/b/c`、`./x`、`x/.`、`nf core/x`、`nf-core/ampliseq?x=1`、`nf-core/ampliseq#a`、含換行、`%2e%2e/x`、`evil.com:80/x`、非字串 | 各送一次 | 每一筆都回 `("refused", {"ok": False, "message": …})`，OPEN 0 次 | 自動：同上 |
| TC-030 | S-12b；原話「Pin an exact pipeline revision, never a branch…」 | 例外 | `revision` 為 `master`、`main`、`dev`、`3.0.0dev`、`2.18.0/../x`、39 位十六進位、大寫 sha、`""` | 各送一次 | 每一筆都 `refused`（分支名一律不過），OPEN 0 次 | 自動：同上 |
| TC-031 | S-12b | 例外 | 要檔案部分但 `revision` 是 `None`；另一組 `parts` 只有 `["tags"]` 卻給 `revision="2.18.0"` | 各送一次 | 兩組都 `refused`，OPEN 0 次 | 自動：同上 |
| TC-032 | S-12b | 例外 | `parts` 為 `[]`、`["x"]`、重複的元素、非 list、字串 `"schema"` | 各送一次 | 每一筆都 `refused`，OPEN 0 次 | 自動：同上 |
| TC-033 | S-13 | 功能 | `revision` 為 `v3.0.0`、`3.0`、`1.2.3.4`、40 位小寫 sha | 各送一次 | 全部放行並發出請求 | 自動：同上 |
| TC-034 | S-14 | 例外 | 第一個請求就丟 `OSError`／`URLError`／逾時 | 跑 `run_fetch` | 回 `("error", {"ok": False, "error": "network", "message": …})`；OPEN 只被呼叫那一次，後面的部分不再試 | 自動：同上 |
| TC-035 | S-14 | 例外 | 第一個請求成功、第二個才失敗 | 跑 `run_fetch` | 同樣回 `network`；OPEN 次數＝失敗那一次的順位，之後不再有請求 | 自動：同上 |
| TC-036 | S-14；裁決三第 10 條 | 例外 | 任一種連線失敗 | 看 `message` | 不超過 300 字、中英並陳、不含 `Traceback` | 自動：同上 |
| TC-037 | S-15 | 例外 | 注入假時鐘 `CLOCK`，讓第 N 個請求前總時間已超過 45 秒 | 跑 `run_fetch` | 回 `network`（同 TC-034 形狀），其後沒有請求 | 自動：同上 |
| TC-038 | S-16 | 功能 | 成功結果 | 看結果的鍵 | 頂層只有 `ok`、`repo`、`revision`、`parts`、`message`；`parts` 內每一部分只有計畫第 2 節規定的欄位 | 自動：同上 |
| TC-039 | S-16 | 例外 | GitHub 回的是錯誤頁、帶一堆自己的標頭 | 看回給平台的內容 | 不含 GitHub 的原始標頭或錯誤頁內文，只有代理自己的短句與整理過的欄位 | 自動：同上 |
| TC-040 | 作法 2 | 功能 | OPEN 會記下每次收到的 `timeout`、`limit` | 各部分各跑一次 | 單次逾時不超過 10 秒；`limit` 依序為 schema／schema_input 1,000,000、目錄清單 1,000,000、圖 2,000,000、tag 公告 4,000,000（皆為「上限＋1 位元組」的讀法） | 自動：同上 |
| TC-041 | S-17；原話「平台不連網」 | 例外 | 掃 `platform/abf_station/*.py` 原始碼 | 找 `urllib.request` | 只出現在 `agent.py` 與 `pipeline_files.py` | 自動：同上 |
| TC-042 | S-17；原話「好，放寬」（不寫入、不帶憑證） | 例外 | 掃 `pipeline_files.py` 原始碼 | 找字樣 | 不含 `open(`、`.write(`、`os.remove`、`shutil`、`subprocess`、`socket`、`ctx.site`、`site.call`、`Authorization`、`sbatch`、`rm -rf` | 自動：同上 |
| TC-043 | S-18 | 例外 | 測試有「守門」：預設的 OPEN 被換成一呼叫就讓測試失敗的函式；另一條測試不注入就呼叫 `run_fetch` | 執行 | 守門生效：那次呼叫被抓成 `AssertionError`（`pytest.raises`），沒有任何測試連到真的 GitHub | 自動：同上 |
| TC-044 | S-19 | 例外 | 真的代理行程＋假平台（FakePlatform），送 `{"repo":"../x","revision":"2.18.0","parts":["schema"]}` | 代理領到工作 | 回 `refused`；代理行程仍活著；沒有連網（參數在發請求前就被擋） | 自動：同上 |
| TC-045 | S-19 | 例外 | 同上，送 `{"repo":"nf-core/x","revision":"2.18.0","parts":["schema"],"extra":1}` | 代理領到工作 | 回 `refused`（訊息為「不收這個參數」類）；代理仍活著 | 自動：同上 |
| TC-046 | 「不做」：代理不解析內容；裁決四第 14 條 | 不在範圍 | `schema` 的假回內容是壞掉的 JSON（`not json`） | 跑 `run_fetch` | 代理原樣回傳，`parts.schema.status == "ok"` 且 `text` 逐字相同（代理不解析、不報 `bad_json`；解析只在平台端） | 自動：同上 |
| TC-047 | 「不做」：不讀 README 或其他檔；原話「好，放寬」（只有四類） | 不在範圍 | `parts` 為 `["readme"]`、`["catalogue"]` | 各送一次 | 都 `refused`，OPEN 0 次（沒有「讀 README」或「讀 nf-core 全管線清單」的能力） | 自動：同上 |
| TC-048 | 原話「好，放寬」（四類公開檔，不多不少） | 功能 | 五種 `parts`（`schema`、`schema_input`、`diagram`、`image`、`tags`）各跑一次，記下所有請求網址 | 彙整 | 每個網址都屬於計畫第 2 節那五種形狀之一，主機只有 `github.com`、`raw.githubusercontent.com`、`api.github.com`，沒有其他路徑 | 自動：同上 |

## User Story 2 — 平台只排工作、收文字：資料庫放行、遷移、排隊、清洗（優先度 P1）

維護者原話：「每個寫入要本人答應」（憲法 6／ADR 0006）→ 本工作唯讀，不需確認（裁決 1）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-049 | Q-01；裁決四第 11 條 | 功能 | 全新的 `platform.db` | 讀 `jobs` 表允許的種類清單 | `pipeline_files` 接在原有種類之後，是最後一項；原有各項順序不變 | 自動：`platform/tests/test_pipeline_files_queue.py` |
| TC-050 | Q-01 | 例外 | 同上 | 各插入種類為 `pipeline_file`、`pipeline_files `（尾巴空白）、`PIPELINE_FILES`、`tags`、`""` 的工作 | 每一筆都被資料庫拒絕（`IntegrityError`） | 自動：同上 |
| TC-051 | Q-02；原話「每個寫入要本人答應」 | 功能 | 同上 | 插入一筆不帶 `confirmation_id` 的 `pipeline_files` 工作 | 成功 | 自動：同上 |
| TC-052 | Q-02 | 例外 | 同上 | 不帶 `confirmation_id` 插入 `launch_nextflow`、`cancel_run`、`clean_work` | 三種仍然被拒絕（需確認的規則沒被放鬆） | 自動：同上 |
| TC-053 | Q-03 | 例外 | 讀 `jobs.CONFIRMED` | 比對 | 仍剛好是 `{"launch_nextflow":"launch","cancel_run":"cancel","clean_work":"clean_work"}`，沒有加 `pipeline_files` | 自動：同上 |
| TC-054 | Q-04（有資料結構變動，必須有 migration） | 功能 | 一個舊表（把新表定義裡的 `, 'pipeline_files'` 剪掉）含三筆舊資料與目前最大的 id | 開啟資料庫（`connect_state`） | 各欄位逐欄不變、id 不變、自動編號從原來的接續、能寫入新種類 | 自動：同上 |
| TC-055 | Q-04 | 例外 | 同上，遷移完成後 | 寫入種類 `rm`、`launch`、`""` | 仍被拒絕 | 自動：同上 |
| TC-056 | Q-04 | 功能 | 同上，遷移完成後再開一次 | 用遷移步驟計數器（`_migration_step`）數 | 第二次開啟不再重建 | 自動：同上 |
| TC-057 | Q-05 | 例外 | 舊表；遷移中途讓 `_migration_step` 丟例外 | 開啟資料庫 | 舊表原樣、列數不變（整個回滾） | 自動：同上 |
| TC-058 | Q-05 | 功能 | 上一條失敗後 | 再開一次 | 成功遷移 | 自動：同上 |
| TC-059 | Q-06 | 功能 | 更舊的表（連 `clean_work` 都沒有，用 `test_cleanup_store.py` 的 `old_jobs()`） | 開啟資料庫一次 | 直接升到最新（不多重建一次），新種類可寫 | 自動：同上 |
| TC-060 | Q-07 | 功能 | `jobs.KINDS` | 檢查 | `pipeline_files` 恰一次、排最後、其餘種類相對順序與現行相同；測試不寫死總數 | 自動：同上 |
| TC-061 | Q-08 | 功能 | 取 `deadline_seconds("pipeline_files")` | 不設環境變數；再設 `ABF_PLATFORM_DEADLINE_PIPELINE_FILES=7` | 預設 90；設 7 時為 7 | 自動：同上 |
| TC-062 | Q-08 | 例外 | 環境變數設成 `abc`、`0`、`-5` | 取期限 | 都回 90 | 自動：同上 |
| TC-063 | Q-08 | 功能 | 讀 `jobs.py` 常數 | 檢查 | `TAGS_CACHE_SECONDS == 86400`、`TAGS_CACHE_FILE == "release-tags.json"` | 自動：同上 |
| TC-064 | Q-09 | 功能 | alice 有一個在線的環境；呼叫 `enqueue_pipeline_files` | 看資料庫新增的那一列 | 回工作 id；該列 `kind='pipeline_files'`、`state='queued'`、`confirmation_id` 為空、`deadline_at = now+90` | 自動：同上 |
| TC-065 | Q-09 | 功能 | 同上 | 看該列的 `args_json` | 鍵集合剛好 `{repo, revision, parts}`，沒有 `ce` | 自動：同上 |
| TC-066 | Q-10 | 例外 | repo／revision／parts 各種壞值（同 TC-029～032 的子集） | 呼叫 `enqueue_pipeline_files` | 丟 `JobRefused`，資料庫沒有新列 | 自動：同上 |
| TC-067 | Q-10 | 例外 | `parts` 含 `tags` 但 `revision` 不是 `None` | 同上 | 丟 `JobRefused`，沒有新列 | 自動：同上 |
| TC-068 | Q-11 | 功能 | alice 有 `ce-a`（代理離線）、`ce-b`（在線、可用）、`ce-c`（在線、剛建立還沒預檢）、`ce-d`（停用）；bob 有在線的 `ce-x`；alice 沒指定環境 | 選環境 | 選到 `ce-b`（依名稱第一個通過者）；絕不選 `ce-x` | 自動：同上 |
| TC-069 | Q-11 | 功能 | 同上，把 `ce-b` 的代理弄成離線 | 再選一次 | 改選 `ce-c`（證明「剛建立、還沒預檢」的環境也能用） | 自動：同上 |
| TC-070 | Q-11 | 功能 | 呼叫者是本機終端機（`caller_user_id=None`） | 選環境 | 所有環境都算候選 | 自動：同上 |
| TC-071 | Q-11 | 例外 | 沒有任何環境通過 | 呼叫 | `JobRefused`，訊息同時含 `no online agent` 與中文「沒有在線的代理」，句中不含字面 `station`、`ssh` | 自動：同上 |
| TC-072 | Q-12；跨使用者 | 例外 | alice 指定 `compute_env="ce-x"`（bob 的） | 呼叫 | `JobRefused`，措辭與「環境不存在」完全相同（不洩漏有這個環境），沒有新列 | 自動：同上 |
| TC-073 | Q-13 | 功能 | 一個在線的 Google Batch 環境（雲端使用者） | 排 `pipeline_files` | 可以排 | 自動：同上 |
| TC-074 | Q-13 | 例外 | 同一個 Google Batch 環境 | 排 `list_site_files`、`fetch_run_records`、`read_task_log` | 仍被擋（既有 `test_gcb_ce.py`、`test_gcb_launch.py` 這部分不改且仍綠） | 自動：同上 |
| TC-075 | Q-14 | 功能 | 排好一筆 `pipeline_files` | 代理領取（`claim`） | 領到 `kind == "pipeline_files"`，沒有 `confirmation`、沒有 `run_token`；`remaining` 不超過 90；工作變 `claimed` | 自動：同上 |
| TC-076 | Q-14 | 例外 | 同上，另一個代理想領 | 領取 | 領不到 | 自動：同上 |
| TC-077 | Q-15 | 功能 | 正常的代理結果（`parts` 含各部分的合格欄位） | 平台清洗 `clean_result("pipeline_files", …)` | 原樣保留 | 自動：同上 |
| TC-078 | Q-15；原話「好，放寬」（代理無法讓平台存更多） | 例外 | 結果多帶 `headers`、`url`、`token`、`stdout`、`entries`、`private_key`，頂層還有 `text` | 清洗 | 這些鍵全部不在輸出裡 | 自動：同上 |
| TC-079 | Q-15 | 例外 | 某部分的 `status` 不在允許清單 | 清洗 | 該部分改成 `{"status":"bad_response"}` | 自動：同上 |
| TC-080 | Q-15 | 例外 | 某部分 `text` 有 1,000,001 字元 | 清洗 | 該部分改成 `{"status":"too_large"}`，且沒有 `text` | 自動：同上 |
| TC-081 | Q-15 | 例外 | `data_b64` 含非 base64 字元；另一組長度 2,800,001 字元 | 清洗 | 兩組該部分都改成 `bad_response` | 自動：同上 |
| TC-082 | Q-15 | 例外 | 圖的 `name` 為 `../x.png` | 清洗 | 該部分 `bad_response` | 自動：同上 |
| TC-083 | Q-15 | 例外 | 圖的 `type` 為 `text/html` | 清洗 | 丟掉整個圖的部分 | 自動：同上 |
| TC-084 | Q-15 | 例外 | `parts` 內有 `evil` 鍵 | 清洗 | `evil` 被丟掉；輸出沒有 `entries`（沒有落入原本給別種工作的最後 `else` 分支） | 自動：同上 |
| TC-085 | Q-16 | 功能 | 代理領取後以合格結果回報（`take_result`） | 看資料庫 | 工作變 `done`，`result_json` 存的是清洗後的結果 | 自動：同上 |
| TC-086 | Q-16 | 例外 | 同一個工作重複回報；另一個代理回報 | 回報 | 重複回 409；別的代理回 403 | 自動：同上 |
| TC-087 | Q-16 | 例外 | 逾期才回報 | 回報 | 回 `late`，工作變 `expired` | 自動：同上 |
| TC-088 | Q-17 | 功能 | 同一使用者有多筆工作 | `latest_pipeline_files` | 相同 `(repo, revision, parts)` 取最新那筆；`parts` 不同視為不同的工作 | 自動：同上 |
| TC-089 | Q-17；跨使用者（讀） | 例外 | bob 的環境上有工作 | alice 查 | 查不到（回 `None`），別人的工作永遠看不到 | 自動：同上 |
| TC-090 | Q-17 | 功能 | 沒有符合的工作 | 查 | 回 `None`；呼叫前後資料庫檔案位元組不變（唯讀） | 自動：同上 |
| TC-091 | Q-18；原話「平台不連網」 | 例外 | 看 `jobs.py`、`store.py` 的新增行 | 找小寫字樣 `station` | 無命中，也沒有拆字湊出來 | 自動：同上 |
| TC-092 | 作法 3 末（保留期不變） | 功能 | 一筆已完成超過 7 天的 `pipeline_files` 工作列 | 之後排任何新工作 | 該舊列被清掉（沿用既有 7 天保留規則） | 自動：同上 |

## User Story 3 — 動作層 `actions.pipeline_files`：引導式送出頁拿參數表、樣本表欄位、流程圖（優先度 P1）

維護者原話：「Pin an exact pipeline revision, never a branch, when launching or reading a pipeline's schema/README/diagrams — those are all read live from the pipeline's repo at that revision, never cached here」（repo `CLAUDE.md`）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-093 | A-01 | 功能 | 動作層 | 看 `pipeline_files`、`latest_release` | 兩個都是一般函式（不是 `async`，`inspect.iscoroutinefunction` 為 False），第一個參數是 `platform_path` | 自動：`platform/tests/test_pipeline_files_action.py` |
| TC-094 | A-01 | 功能 | 同上 | 看參數順序 | `pipeline_files` 為 `(platform_path, pipeline, revision, *, parts, compute_env, caller, enqueue)`；`latest_release` 同理但沒有 `revision`、`parts` | 自動：同上 |
| TC-095 | A-03 | 例外 | pipeline 為 `""`、`"../x"`、`"a/b/c"`、`None`、`123` | 呼叫 | 都回 `state:"error"`、`error:"bad_input"` | 自動：同上 |
| TC-096 | A-03；原話「Pin an exact pipeline revision, never a branch…」 | 例外 | revision 為 `"master"`、`None`、`""`、`"3.0.0dev"` | 呼叫 | 都回 `state:"error"`、`error:"bad_input"`（分支名不收） | 自動：同上 |
| TC-097 | A-03 | 例外 | parts 為 `["tags"]`、`[]`、`["x"]`、重複元素 | 呼叫 | 都回 `bad_input`（`tags` 在這個函式不收） | 自動：同上 |
| TC-098 | A-03；「失敗形狀範例」 | 例外 | pipeline 為 `"../x"` | 呼叫並看資料庫 | `reason` 中英並陳（以「pipeline 名稱不合格」起頭）；回傳的鍵齊全，各部分為 `None`；`jobs` 表零新列 | 自動：同上 |
| TC-099 | A-04 | 功能 | alice 有在線環境，從沒問過 | 第一次呼叫 `pipeline_files(…, "nf-core/ampliseq", "2.18.0")` | `state:"loading"`、`parts` 預設為 `["schema","schema_input","diagram"]`、四個部分（schema、schema_input、diagram、image）全是 `None`、`checked_at` 是 `None` | 自動：同上 |
| TC-100 | A-04 | 功能 | 同上 | 看資料庫 | 恰新增一筆工作，`args` 為 `{"repo":"nf-core/ampliseq","revision":"2.18.0","parts":["schema","schema_input","diagram"]}` | 自動：同上 |
| TC-101 | A-04 | 功能 | 同上 | 第二次呼叫 | 仍是 `loading`，資料庫仍只有一筆（不重複排） | 自動：同上 |
| TC-102 | 作法 5 步驟 4 | 功能 | 工作已被代理領走（`claimed`）但還沒答覆、沒超過期限 | 呼叫 | `loading`，沒有新工作 | 自動：同上 |
| TC-103 | A-05 | 功能 | 代理答覆了含 ampliseq fixture 的結果 | 再呼叫 | `state:"ready"`；`schema.groups` 等於「把 fixture 讀進來再分組」的結果（16 組）；`schema.required_without_default == ["outdir"]` | 自動：同上 |
| TC-104 | A-05 | 功能 | 同上 | 看 `schema_input` | `columns` 等於 `schema.samplesheet_columns(schema.load(fixture))` | 自動：同上 |
| TC-105 | A-05 | 功能 | 同上 | 看 `diagram` 與 `checked_at` | `diagram` 與代理答覆相同；`checked_at` 等於該工作的 `finished_at` | 自動：同上 |
| TC-106 | A-05；作法 6 | 功能 | 同上 | 看整個回傳 | `json.dumps` 得過；鍵集合恰為作法 6 列的那些（`state`、`pipeline`、`revision`、`parts`、`checked_at`、`error`、`reason`、`schema`、`schema_input`、`diagram`、`image`） | 自動：同上 |
| TC-107 | A-06；「失敗形狀範例」 | 例外 | `schema_input` 部分是 `not_found` | 呼叫 | `state:"ready"`（部分失敗不擋）；該部分 `{"status":"not_found","message":"這個版本沒有 assets/schema_input.json (this revision has no assets/schema_input.json)"}`；其他部分照常 | 自動：同上 |
| TC-108 | A-07 | 例外 | `schema` 部分的 `text` 是 `"not json"` | 呼叫 | 該部分 `{"status":"bad_json","message":…}`，不丟例外；其他部分照常 | 自動：同上 |
| TC-109 | A-08；裁決三第 8 條 | 例外 | 被要求的部分全是 `not_found` | 呼叫 | `state:"error"`、`error:"not_found"`、各部分 `None`、`reason` 是白話 | 自動：同上 |
| TC-110 | A-08 | 例外 | 部分狀態混合（例如 `schema` 為 `rate_limited`、`schema_input` 為 `too_large`、`diagram` 為 `not_found`） | 呼叫 | `state:"error"`，`error` 取依 `parts` 順序第一個的狀態（`rate_limited`），各部分 `None` | 自動：同上 |
| TC-111 | 裁決三第 8 條 | 例外 | 一筆「全部部分都失敗」的已完成工作，完成不到 60 秒 | 再呼叫 | 仍回同一個錯誤，不排新工作 | 自動：同上 |
| TC-112 | 裁決三第 8 條 | 例外 | 同上，已過 60 秒 | 再呼叫 | `loading`，並新增一筆工作 | 自動：同上 |
| TC-113 | 裁決三第 8 條 | 功能 | 一筆已完成、只有「確定性」失敗（`not_found`、`too_large`、`bad_json`）的工作，在 7 天保留期內 | 用相同參數再呼叫兩次 | 都回同一筆的結果（`ready`），不新增工作 | 自動：同上 |
| TC-114 | 裁決四第 13 條 | 例外 | 一筆已完成、含暫時性失敗部分（`network`／`rate_limited`／`bad_response`）的工作，完成後 60 秒內 | 再呼叫 | 回同一筆的結果（各部分的錯誤照列），不排新工作 | 自動：同上 |
| TC-115 | 裁決四第 13 條 | 例外 | 同上，超過 60 秒 | 再呼叫 | 新排一筆工作、回 `loading` | 自動：同上 |
| TC-116 | A-09；「失敗形狀範例」逐字 | 例外 | 代理回整體 `error`／`network` | 呼叫 | `{"state":"error","pipeline":"nf-core/ampliseq","revision":"2.18.0","parts":["schema","schema_input","diagram"],"checked_at":<finished_at>,"error":"network","reason":"代理連不到 GitHub，請檢查那台機器的網路 (the agent could not reach GitHub; check that machine's network)","schema":None,"schema_input":None,"diagram":None,"image":None}` | 自動：同上 |
| TC-117 | A-09 | 例外 | 上一條失敗後 60 秒內 | 再呼叫 | 仍是這個錯誤，不排新工作 | 自動：同上 |
| TC-118 | A-09 | 例外 | 時間推進 61 秒 | 再呼叫 | `loading`，並新增一筆工作 | 自動：同上 |
| TC-119 | A-10 | 例外 | 代理（舊版）對新種類回 `refused`（「不支援」） | 呼叫 | `error:"refused"`；`reason` 提到要更新 abf-station | 自動：同上 |
| TC-120 | A-11 | 例外 | 工作一直 `queued` 沒人領，超過 `deadline_at` | 呼叫 | `error:"no_answer"` | 自動：同上 |
| TC-121 | A-11 | 例外 | 同上，再過 60 秒 | 呼叫 | 重新排一筆新工作 | 自動：同上 |
| TC-122 | A-12 | 例外 | 使用者沒有任何在線代理 | 呼叫 | `state:"error"`、`error:"no_agent"`，資料庫零新列 | 自動：同上 |
| TC-123 | A-12 | 例外 | 同上，且 `enqueue=False`（只看不排） | 呼叫 | `state:"loading"`，零新列 | 自動：同上 |
| TC-124 | A-13；專長守則（跨使用者，讀） | 例外 | alice 的工作已完成；bob（自己有在線環境）用相同參數呼叫 | bob 呼叫 | bob 看到 `loading`（排自己的工作），看不到 alice 的結果 | 自動：同上 |
| TC-125 | A-13 | 例外 | bob 沒有任何環境 | bob 呼叫 | `no_agent` | 自動：同上 |
| TC-126 | A-13；專長守則（跨使用者，寫） | 例外 | bob 的 `compute_env` 指向 alice 的環境 | bob 呼叫 | 措辭與「找不到這個環境」相同，資料庫沒有新工作 | 自動：同上 |
| TC-127 | A-14；原話「…never cached here」 | 例外 | 工作完成後 | 比對 `platform.db` 同資料夾前後的檔案清單（此測試不呼叫 `latest_release`，`release-tags.json` 除外） | 沒有新增任何檔案（平台不另存檔案內容的快取檔） | 自動：同上 |
| TC-128 | A-14；作法 5 | 功能 | 同上 | 相同參數再呼叫兩次 | 仍是同一筆工作，不新增 | 自動：同上 |
| TC-129 | A-14 | 功能 | 把工作列刪掉（模擬 7 天清除） | 再呼叫 | `loading`，並新增一筆工作 | 自動：同上 |
| TC-130 | A-15 | 功能 | `parts=("image",)`，代理答覆含 `image.data_b64` | 呼叫 | `image == {"status":"ok","name":…,"type":"image/png","size":…,"data_b64":…}` | 自動：同上 |
| TC-131 | A-15 | 功能 | 預設 `parts`（不含 image） | 呼叫 | 整個回傳的文字裡不含 `data_b64` 字樣 | 自動：同上 |
| TC-132 | A-21；專長守則（錯誤訊息） | 例外 | 本檔所有回傳形狀（loading、ready、各種 error） | `json.dumps` 並掃 `reason`／`why`／`message` | 都得過；不含 `Traceback`、`sqlite`、`args_json`、`deadline_at`、`result_json`、`SELECT`；每個 `state:"error"` 的 `reason` 都有白話說明 | 自動：同上 |
| TC-133 | A-22 | 例外 | 掃 `actions/__init__.py` 的新增行 | 找字樣 | 不含 `urllib`、`socket`、`subprocess`、`open(`（動作層不碰網路與檔案） | 自動：同上 |
| TC-134 | A-02；專長守則（對等性） | 功能 | `test_web_parity.py` | 執行 | 兩個新名稱在 `WEB_ONLY` 表；「動作層公開名稱＝網頁／工具／待辦／內部名單的聯集」檢查為綠；新增的公開名稱只有 `pipeline_files`、`latest_release`（輔助函式都以底線開頭） | 自動：`platform/tests/test_web_parity.py` |
| TC-135 | A-02 | 功能 | MCP 伺服器的工具名單 | 建伺服器並列工具 | 不含 `pipeline_files`、`latest_release`；工具數與基底相同 | 自動：同上 |

## User Story 4 — 動作層 `actions.latest_release`：新專案預填「最新版並寫死成版本號」（優先度 P2）

維護者原話：「新專案預設最新版並釘住」「launch 表單與 MCP 預填＝該 pipeline 最新 release tag」（replan 第 28、172 行，引自 `release-tag-pick.md`）→ 回的必須是具體版本號，不是 `latest` 或分支名。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-136 | A-16；原話「新專案預設最新版並釘住」 | 功能 | 快取檔不存在、沒有工作；alice 有在線環境 | 呼叫 `latest_release("ampliseq", …)` | `pipeline:"nf-core/ampliseq"`（已正規化）、`state:"loading"`、`revision` 為 `None`、`source:"none"` | 自動：`platform/tests/test_pipeline_files_action.py` |
| TC-137 | A-16 | 功能 | 同上 | 看資料庫 | 新增一筆工作，`args == {"repo":"nf-core/ampliseq","revision":None,"parts":["tags"]}` | 自動：同上 |
| TC-138 | A-17 | 功能 | 代理答覆 tags 文字（含 `2.18.0`、`3.0.0`、`3.0.0dev`、`dev` 四種 ref） | 再呼叫 | `state:"ready"`、`revision:"3.0.0"`、`source:"fetched"`、`checked_at` 為假時鐘的時間 | 自動：同上 |
| TC-139 | A-17 | 功能 | 同上 | 看 `platform.db` 旁的 `release-tags.json` | 是合法 JSON，內容 `{"nf-core/ampliseq": {"revision":"3.0.0","checked_at":…}}` | 自動：同上 |
| TC-140 | A-17；原話「新專案預設最新版並釘住」 | 功能 | 同上 | 檢查 `revision` | 通過 `^(v?[0-9]+(\.[0-9]+){1,3}\|[0-9a-f]{40})\Z`（能直接送去啟動；不是 `dev`、`3.0.0dev`、`latest`） | 自動：同上 |
| TC-141 | A-18 | 功能 | 上述快取已寫入，3600 秒後 | 再呼叫 | `source:"cache"`，資料庫沒有新工作 | 自動：同上 |
| TC-142 | A-18；裁決三第 7 條 | 功能 | 剛好 86400 秒後 | 再呼叫 | 快取過期（邊界＝過期）：`loading`，並新增一筆工作（已完成的舊工作也不再被重用） | 自動：同上 |
| TC-143 | A-19 | 例外 | 先有 `2.18.0` 的快取，過期後問，代理回 `network` | 呼叫 | `state:"ready"`、`revision:"2.18.0"`、`source:"stale-cache"`、`why` 不為空 | 自動：同上 |
| TC-144 | A-19 | 例外 | 同上 | 看快取檔 | 內容未變（失敗不寫快取） | 自動：同上 |
| TC-145 | A-19 | 例外 | 沒有舊快取，代理回 `network` | 呼叫 | `state:"error"`、`error:"network"`、`revision` 為 `None`、`source:"none"` | 自動：同上 |
| TC-146 | A-19 | 例外 | 同上，之後代理恢復 | 超過 60 秒後再問 | 會再試（排新工作），失敗沒被快取 | 自動：同上 |
| TC-147 | A-20 | 例外 | 代理答覆的 tags 全不可用（只有 `dev`、`3.0.0dev`） | 呼叫 | `error:"no_release"`，`why` 點名「沒有可用的 release tag」 | 自動：同上 |
| TC-148 | A-20 | 例外 | 同上 | 看 `platform.db` 旁 | 沒有寫入 `release-tags.json` | 自動：同上 |
| TC-149 | 作法 5 `latest_release` 步驟 1、5 | 例外 | pipeline 為 `"../x"` | 呼叫 | `state:"error"`、`error:"bad_input"`、`pipeline` 為原輸入字串；資料庫零新列 | 自動：同上 |
| TC-150 | 作法 5 `latest_release` | 例外 | 使用者沒有在線代理、沒有快取 | 呼叫 | `state:"error"`、`error:"no_agent"`；零新列 | 自動：同上 |
| TC-151 | 作法 6 `latest_release` | 功能 | loading、ready、error 各一例 | 看回傳 | 鍵永遠齊全：`state`、`pipeline`、`revision`、`source`、`checked_at`、`why`、`error`；`json.dumps` 得過；`error` 值都在計畫列的清單內 | 自動：同上 |

## User Story 5 — 範圍、文件與真的連 GitHub 的手動驗收（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-152 | 完成標準；範圍：檔案 | 例外 | 實作完成 | 閱卷者讀 `git diff <base>...HEAD --name-only` | 只有「範圍：檔案」所列的檔案，加上裁決五追認的 `platform/tests/test_byte_channel_b.py`（只限 TC-001 的 JOB_KINDS 尾端加 `pipeline_files`），以及裁決四第 12 條准改的 `test_http_site_samplesheet.py`、`test_byte_channel_a.py` | 手動：閱卷者讀 diff |
| TC-153 | 完成標準；「會改斷言的既有測試」 | 例外 | 同上 | 比對每個被動到的既有測試檔 | 只有計畫表列的那些斷言被改；表外的既有測試零改動 | 手動：閱卷者讀 diff |
| TC-154 | 閱卷規則（不得放水）；「會改斷言」通則 | 例外 | 同上 | 看每條被改的斷言 | 都只是在尾端加 `pipeline_files`；沒有任何斷言被刪除、放寬成不檢查順序、跳過，或把預期值改成配合新輸出 | 手動：閱卷者讀 diff |
| TC-155 | 裁決四第 12 條 | 例外 | 同上 | 看 `test_http_site_samplesheet.py` 與 `test_byte_channel_a.py` | 前者只換 `SCHEMA_SHA256` 一個值（ledger 記新舊值與算法）；後者只改 `put_upload` 在 `pipeline_files` 之前、`pipeline_files` 最後的相關斷言，其餘逐字比對不變 | 手動：閱卷者讀 diff |
| TC-156 | 完成標準；裁決四第 15 條 | 例外 | 同上 | 讀 `specs/release-lookup-job/ledger.md` | 每一條既有測試改動都有「舊→新＋理由」；貼了 `git diff --stat`；標題不再有「nf-core 清單」 | 手動：閱卷者讀 ledger |
| TC-157 | 憲法（實作期間不得改規格） | 例外 | 同上 | 看 diff | `plan.md`、`test-case.md`、`test-case-overview.md`、憲法在實作期間沒有被改 | 手動：閱卷者讀 diff |
| TC-158 | 「不做」：不改純模組與其他檔 | 不在範圍 | 同上 | 看 diff | `schema.py`、`releases.py`、`mcp_server.py`、`guidance.py`、`chat_tools.py`、`web*.py`、`cli.py`、`confirm.py`、`compute_envs.py`、`receiver.py`、`abf_station/{launch,cancel,clean,fetch,readlog,site,rules,agent,cli}.py`、`station_harness.py`、`pyproject.toml` 全無改動 | 手動：閱卷者讀 diff |
| TC-159 | 「不做」：不加 MCP 工具、不加網頁路由、不做 nf-core 全管線搜尋；裁決三第 6 條 | 不在範圍 | 動作層與路由名單 | 查 | 動作層沒有 `nfcore_catalogue`，沒有 `catalogue` 部分；MCP 工具名單、網頁路由名單不變（由 TC-134、TC-135 與既有 `test_actions_layer.py`、`test_pat.py`、`test_oauth_mcp.py` 的工具數斷言守住） | 自動：`platform/tests/test_web_parity.py` |
| TC-160 | 「不做」：不接線版本預填（release-tag-pick 裁決 2） | 不在範圍 | 同上 | 看 diff | `request_launch`、`launch_prefill`、啟動表單的版本預填沒有被改 | 手動：閱卷者讀 diff |
| TC-161 | 「不做」：不加資料表、不加欄位 | 不在範圍 | 新建的 `platform.db` | 比對所有表與欄位 | 與基底相比，只有 `jobs` 的種類限制多了 `pipeline_files`，其他表與欄位不變（`test_http_site_samplesheet.py` 的 TC-057 結構雜湊檢查，雜湊值依計畫重算） | 自動：`platform/tests/test_http_site_samplesheet.py` |
| TC-162 | 「不做」：不改 `confirmations`、不新增確認種類 | 不在範圍 | 同上 | 看 diff 與 `confirmations` 的定義 | `confirmations` 表與其種類限制沒有改動 | 手動：閱卷者讀 diff |
| TC-163 | 「不做」：不新增設定鍵；裁決 8（版本號不動） | 不在範圍 | 同上 | 看 diff | 新增的環境設定只有 `ABF_PLATFORM_DEADLINE_PIPELINE_FILES`；`abf_station.__version__` 沒變 | 手動：閱卷者讀 diff |
| TC-164 | 「不做」：不加背景執行緒、迴圈、重試 | 不在範圍 | 掃 `abf_platform/` 與 `abf_station/` 新增程式 | 跑 `test_scope.py` 的 TC-071 | 沒有 `threading`、`subprocess`、`while True` | 自動：`platform/tests/test_scope.py` |
| TC-165 | 作法 8 文件①④ | 功能 | `docs/PLATFORM.md` | 閱卷者讀 diff | 第 6 節「三件唯讀的事」清單補了 `pipeline_files`；「The agent never opens a connection of its own」限定為「toward the site」，並說明這是代理唯一連網際網路的工作、只問 `github.com`、`raw.githubusercontent.com`、`api.github.com` 三個主機的公開檔、不帶憑證、不寫入、不跟隨轉址；「Action layer」節補了 `pipeline_files`、`latest_release` 各一句 | 手動：閱卷者讀 diff |
| TC-166 | 作法 8 文件② | 功能 | 「What the platform stores」表 | 跑 `tests/platform_storage_doc_test.sh` | 新增一列「Newest release of a pipeline \| release-tags.json (next to platform.db) \| 24 hours」，TC-004（名字出現在程式碼）與 TC-009（`24 hours` 對得上 `jobs.py` 頂層的 `TAGS_CACHE_SECONDS = 24 * 3600`）通過 | 自動：`tests/platform_storage_doc_test.sh` |
| TC-167 | 作法 8 文件③ | 功能 | `docs/PLATFORM.md` 設定一節 | 閱卷者讀 diff | 補了 `ABF_PLATFORM_DEADLINE_PIPELINE_FILES`（預設 90） | 手動：閱卷者讀 diff |
| TC-168 | 完成標準（手動） | 功能 | `docs/TESTING.md` | 閱卷者讀 | 新增一節「release-lookup-job：真的連 GitHub 讀一次」，含下面 TC-169～172 的步驟，具體到非工程師能照做 | 手動：`docs/TESTING.md` |
| TC-169 | 完成標準手動 2；原話「好，放寬」 | 功能 | 有網路的機器，已啟動平台與一個代理，建好該代理的環境（不必預檢） | 用一行 Python 呼叫 `actions.pipeline_files(<platform.db 路徑>, "nf-core/ampliseq", "2.18.0")`，每 5 秒再呼叫到不是 `loading`（最多約 1 分鐘） | `state "ready"`；`schema.groups` 16 組、參數共 170 個；`schema.required_without_default == ["outdir"]`；`schema_input.columns` 首欄 `sampleID`；`diagram.name == "ampliseq_workflow.png"`、`size == 753702` | 手動：`docs/TESTING.md`（由 developer-agent／維護者做，executor 不執行） |
| TC-170 | 完成標準手動 2 | 功能 | 同上 | 以 `parts=("image",)` 呼叫 | `len(base64.b64decode(data_b64)) == 753702`，開頭是 PNG 魔術字 | 手動：`docs/TESTING.md` |
| TC-171 | 完成標準手動 3；原話「新專案預設最新版並釘住」 | 功能 | 同上 | 呼叫 `actions.latest_release(<路徑>, "nf-core/ampliseq")` 輪詢到不是 `loading`；立刻再呼叫一次 | 第一次回最新的純數字 tag（2026-10-25 實測是 `3.0.0`，以當時 GitHub 為準）、`source "fetched"`，`release-tags.json` 出現在 `platform.db` 旁；第二次 `source "cache"` 且資料庫沒有新工作 | 手動：`docs/TESTING.md` |
| TC-172 | 完成標準手動 4 | 例外 | 拔掉網路（或把代理的網路關掉） | 呼叫一個沒問過的 `("nf-core/rnaseq","3.27.0")` | 約 1 分鐘內 `state "error"`、`error "network"`、`reason` 是白話 | 手動：`docs/TESTING.md` |
| TC-173 | 完成標準（自動） | 功能 | executor 完成 | 在 WSL 跑 `bash tests/run_all.sh` | 全綠（含 `platform_test.sh`、`no_second_run_state_test.sh`（`LAUNCH_ALLOW` 仍一筆）、`credentials_stay_in_settings_test.sh`、`platform_storage_doc_test.sh`、`test_scope.py`）；全程沒有連真網路（TC-043 守門）；已知環境紅 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 在計畫指定條件下視同綠 | 自動：`tests/run_all.sh` |

## 憲法與安全網

本任務動到：原則 1（新檔頭）、原則 2（平台不連網、不得另開第二條送出路徑）、原則 3（不寫死路徑）、原則 6（樣本表欄位來自管線自己的檔）、憑證規則、「每個寫入要本人答應」。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-174 | 原則 1：新檔頭寫明「為什麼不用現成的」 | 例外 | 新增的 `pipeline_files.py` 與三個新測試檔 | 跑 `test_scope.py` TC-070 | 每個檔首行都有 `# Nothing existing: …` 且不少於 15 字，缺一個就紅（`abf_station/` 也受檢） | 自動：`platform/tests/test_scope.py` |
| TC-175 | 原則 2：平台不連網（原話「平台不連網」；`test_scope.py` TC-061） | 例外 | 掃整個 `platform/abf_platform/` | 跑 TC-061 | 沒有 `urllib.request`、`import socket`、`socket.`、`ssh`、`sbatch`、字面 `station` 等；也沒有 `watchdog`、`POLICY`（`test_cloud_cost.py`）；連網只在 `abf_station/pipeline_files.py` | 自動：`platform/tests/test_scope.py`、`platform/tests/test_cloud_cost.py` |
| TC-176 | 原則 2：只有一條送出路徑 | 例外 | 掃 `scripts/` 與 `platform/` | 跑 `tests/no_second_run_state_test.sh` | `LAUNCH_ALLOW` 仍只有一筆；`pipeline_files.py` 沒有 `sbatch`／`srun`／`nextflow run` 開頭字串（沒有第二條送出路徑、沒有第二份執行狀態） | 自動：`tests/no_second_run_state_test.sh` |
| TC-177 | 原則 3：不寫死路徑 | 例外 | 掃新增程式 | 跑 `tests/no_hardcoded_paths.sh` | 沒有 `/home/…/`、`/work/…/` 形的路徑；快取檔位置由 `platform.db` 所在資料夾推導，不寫死 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-178 | 原則 6：樣本表欄位必須來自管線自己的 `assets/schema_input.json`，參數來自 `nextflow_schema.json` | 例外 | 掃新增程式 | 跑 `tests/no_per_pipeline_config.sh`；看 TC-103、TC-104 | 沒有逐管線的設定檔或寫死的管線欄位表；欄位只由讀到的檔案經 `schema.py` 解析而來 | 自動：`tests/no_per_pipeline_config.sh` |
| TC-179 | 安全網：憑證不外流；專長守則（日誌與回應不含密鑰） | 例外 | 掃新增程式與清洗後的結果 | 跑 `tests/credentials_stay_in_settings_test.sh`；看 TC-027、TC-078 | 請求不帶憑證、結果中的 `token`／`private_key` 之類鍵被丟掉、`reason` 不含內部字樣 | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-180 | 原則 2／ADR 0006：寫入要本人答應（原話「每個寫入要本人答應」）；專長守則（確認管道） | 例外 | 一個沒有確認的使用者 | 呼叫 `pipeline_files`／`latest_release` 並看 `confirmations` 表與 `jobs` 表 | 唯一的資料變動是 `jobs` 表多一筆 `pipeline_files` 工作；`confirmations` 表沒有新列；不碰站台、不寫使用者資料 | 自動：`platform/tests/test_pipeline_files_queue.py` |
