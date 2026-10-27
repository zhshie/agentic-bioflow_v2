# 測試案例：站台代理讀 nf-core 官網管線清單（nfcore-catalogue）

<!--
Written by the verifier (CONTRACT mode) from specs/nfcore-catalogue/plan.md. There is no spec.md in this task directory: the plan (with its "維護者原話" section) is the specification.
Every example below (ampliseq, abotyper, exoseq, cellpainting, the 6-entry fixture, the manual step 2 figures) is quoted from the plan. Nothing here is invented beyond the plan.
-->

**規格**：`specs/nfcore-catalogue/plan.md`（本任務沒有 spec.md，計畫即規格）　**總覽**：`test-case-overview.md`

白話說明：這個功能讓「引導式送出」的新管線步驟能搜尋全部 nf-core 管線。流程是這樣的。站台代理（裝在能上網的那台機器上的小程式）去讀 nf-core 官網的公開清單 `https://nf-co.re/pipelines.json`。平台自己不上網，只排工作、收結果、算出每條管線的最新版本。結果保留 24 小時，期間重複問不會再排新工作。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、不合格的輸入時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事，或「這些東西不能被動到」。測試確認它真的沒做，或原本的行為沒變。

「對應需求」欄的 CS／CQ／CA 編號是計畫「失敗先行測試」三張表裡的編號（CS＝站台代理、CQ＝平台排隊與清洗、CA＝動作層）。

## 一、站台代理讀清單（計畫 CS-01 至 CS-11）

假網路測試，不連真網路。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | CS-01；裁決 1 | 不在範圍 | 讀現行程式 | 檢查代理的工作種類清單 `handlers.JOB_KINDS` 和 `ARG_KEYS["pipeline_files"]` | `JOB_KINDS` 逐字等於現行九種，沒有新增種類。`ARG_KEYS["pipeline_files"]` 仍恰為 `{"repo","revision","parts"}` | 自動：`platform/tests/test_nfcore_catalogue.py` |
| TC-002 | CS-01；作法 1 | 功能 | 同上 | 檢查 `pipeline_files.PARTS` 與 `jobs.PF_PARTS` | `PARTS[-1] == "catalogue"`。`PARTS[:5]` 逐字等於舊的五個：`schema`、`schema_input`、`diagram`、`image`、`tags`。`jobs.PF_PARTS == PARTS` | 自動：同上 |
| TC-003 | CS-02；維護者「都ok」 | 功能 | 無 | 呼叫 `allowed("https://nf-co.re/pipelines.json")`，並讀 `HOSTS` | 回 True。`HOSTS == ("github.com","raw.githubusercontent.com","api.github.com","nf-co.re")` | 自動：同上 |
| TC-004 | CS-02；維護者「都ok」（只放這一個主機） | 例外 | 假網路，記錄呼叫次數 | 對 `allowed()` 逐一餵：`http://nf-co.re/pipelines.json`、`https://nf-co.re.evil.com/pipelines.json`、`https://evil.com/nf-co.re/pipelines.json`、`https://nf-co.re@evil.com/x`、`https://nf-co.re:8443/pipelines.json`、`https://www.nf-co.re/pipelines.json` | 六個都回 False，假網路 `OPEN` 零次被呼叫 | 自動：同上 |
| TC-005 | CS-03；CS-10 | 功能 | 假 `OPEN` 回 fixture `pipelines-small.json`（200、`Content-Type: application/json`） | 對 `job(["catalogue"], repo=None, revision=None)` 執行 `run_fetch` | 請求恰一個。網址逐字 `https://nf-co.re/pipelines.json`，`limit == 8000000`，`Accept == "application/json"`，方法 GET。標頭沒有 `Authorization`，也沒有 `Cookie` | 自動：同上 |
| TC-006 | CS-03 | 功能 | 同 TC-005 | 看結果 | 結果是 `("done", {"ok": True, "repo": None, "revision": None, "parts": {"catalogue": {"status": "ok", "pipelines": [...]}}, "message": …})`。`pipelines` 恰 6 條，依 name 排序，每條的鍵恰為 `{"name","description","archived","tags"}` | 自動：同上 |
| TC-007 | CS-03（計畫的例子） | 功能 | 同 TC-005 | 看 `ampliseq` 與 `abotyper` 兩條 | `ampliseq` 的 `tags == ["3.0.0","2.18.0","dev"]`（與 fixture 順序相同），`description` 逐字等於 fixture（例如 "Amplicon sequencing analysis workflow using DADA2 and QIIME2"），`archived` 為 False。`abotyper.tags == ["dev"]` | 自動：同上 |
| TC-008 | CS-03（計畫的例子） | 功能 | 同 TC-005 | 看 `exoseq` 與 `cellpainting` 兩條 | `exoseq.archived` 為 True。`cellpainting.description == ""`（原檔是 null） | 自動：同上 |
| TC-009 | CS-03；不做第 7 條 | 功能 | 同 TC-005，fixture 內有 `stargazers_count`、`topics`、`html_url`、`releases[].tag_sha` | 把整個輸出 `json.dumps` 成字串，找這些名字與值 | 這些欄位的鍵與值都不在輸出的任何地方 | 自動：同上 |
| TC-010 | CS-04 | 例外 | fixture 另加兩條：`name: "../evil"`、`name: 5` | 執行 | 這兩條不在輸出，其他條目照常，整份不失敗 | 自動：同上 |
| TC-011 | CS-04 | 例外 | fixture 另加三條：一條沒有 `releases`、一條 `releases: "x"`、一條 `description: 7` | 執行 | 三條都在輸出。前兩條 `tags == []`，第三條 `description == ""` | 自動：同上 |
| TC-012 | CS-04；裁決 10 | 例外 | 分別餵：頂層 `{"remote_workflows": {}}`、`[]`、`"x"`、非 UTF-8 位元組、`{"remote_workflows": []}`、所有條目名稱都壞 | 各執行一次 | 六種都得到 `{"status":"bad_response","message":…}`。`message` 不超過 300 字，中英並陳。沒有新增任何狀態字樣 | 自動：同上 |
| TC-013 | CS-05 | 例外 | 假 `OPEN` 回 8,000,001 位元組的本文 | 執行 | 結果 `too_large`，沒有 `pipelines` 鍵。代理沒有被要求讀超過 `limit + 1` 位元組 | 自動：同上 |
| TC-014 | CS-05 | 例外 | 本文有 1001 條合格條目 | 執行 | 結果 `too_large`，沒有 `pipelines` 鍵 | 自動：同上 |
| TC-015 | CS-06 | 例外 | 假網路分別回 404、429、403 加 `X-RateLimit-Remaining: 0` | 各執行一次 | 依序得到 `not_found`、`rate_limited`、`rate_limited` | 自動：同上 |
| TC-016 | CS-06 | 例外 | 假網路分別回 500、301 | 各執行一次 | 兩者都是 `bad_response`；301 不被跟隨 | 自動：同上 |
| TC-017 | CS-07 | 例外 | 假網路丟 `OSError` | 執行 | 結果 `("error", {"ok": False, "error": "network", "message": …})`，`OPEN` 恰被呼叫 1 次 | 自動：同上 |
| TC-018 | CS-07 | 例外 | 注入 `CLOCK` 讓總預算（45 秒）一開始就用完 | 執行 | 同樣是 `("error", {"ok": False, "error": "network", …})`，`OPEN` 被呼叫 0 次 | 自動：同上 |
| TC-019 | CS-08 | 例外 | 假網路，記錄請求數 | 分別執行：`job(["catalogue"])`（repo／revision 用預設值）、`job(["catalogue"], repo=None)`（revision 仍是 2.18.0）、`job(["catalogue"], revision=None)`（repo 仍給） | 三筆都被拒絕（`refused`），`OPEN` 零次 | 自動：同上 |
| TC-020 | CS-08 | 例外 | 同上 | 分別執行：`job(["catalogue","schema"], repo=None, revision=None)`、`job(["catalogue","tags"], repo=None, revision=None)`、`job(["catalogue","catalogue"], repo=None, revision=None)` | 三筆都被拒絕，`OPEN` 零次 | 自動：同上 |
| TC-021 | CS-08 | 例外 | 同上 | 執行 `job(["schema"], repo=None, revision=None)` | 被拒絕，`OPEN` 零次（repo 為 None 只對 catalogue 合法） | 自動：同上 |
| TC-022 | CS-09；作法 1 | 不在範圍 | 既有五個 part 的工作（`schema`、`schema_input`、`diagram`、`image`、`tags`） | 執行 | 仍恰 5 個請求，網址都不在 `nf-co.re`。不帶 `catalogue` 就不會碰到 nf-co.re | 自動：同上 |
| TC-023 | CS-10；裁決 2；不做第 2 條 | 不在範圍 | 讀 `abf_station/pipeline_files.py` 原始碼 | 數 `"https://nf-co.re/pipelines.json"` 出現幾次，並找 `nf-co.re/` 的其他路徑 | 該網址字串恰出現一次，沒有 `nf-co.re/` 的其他路徑。網址是常數，沒有任何參數可以組出別的網址 | 自動：同上 |
| TC-024 | CS-11 | 例外 | 不注入假 `OPEN`（測試檔的 autouse 守門生效） | 直接執行 `run_fetch(job(["catalogue"], repo=None, revision=None), ctx)` | 丟 `AssertionError`。測試全程不連真網路 | 自動：同上 |
| TC-025 | 作法 2「代理不挑最新版」；不做第 4 條 | 不在範圍 | 假網路回 fixture | 看 `abotyper` 的輸出 | `abotyper.tags == ["dev"]`（`dev` 沒被濾掉）。每條的鍵集合裡沒有 `latest` | 自動：同上 |

## 二、平台排隊與清洗（計畫 CQ-01 至 CQ-08）

資料庫用暫時的 `platform.db`，不連網。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-026 | CQ-01；裁決 1；作法 8 | 不在範圍 | 新建 `platform.db` | 讀 `jobs` 表的 CHECK 清單，並讀 `jobs.KINDS` | 逐字與 base 相同：`pipeline_files` 仍最後，沒有新字樣（沒有新工作種類） | 自動：`platform/tests/test_nfcore_catalogue.py` |
| TC-027 | CQ-01；作法 8（不需要 migration） | 不在範圍 | 同上 | 對同一個資料庫開兩次 | 不重建，`_migration_step` 零次被呼叫。沒有 migration | 自動：同上 |
| TC-028 | CQ-02；裁決 7 | 功能 | alice 有在線環境 | 檢查 `jobs.CONFIRMED`；不帶 `confirmation_id` 排一筆 `catalogue` 工作 | `CONFIRMED` 仍剛好三項。排隊成功（唯讀，不需確認） | 自動：同上 |
| TC-029 | CQ-03 | 功能 | 無 | 呼叫 `pf_arguments(None, None, ["catalogue"])` | 回 `(None, None, ["catalogue"])` | 自動：同上 |
| TC-030 | CQ-04 | 例外 | 無 | 分別餵 `("nf-core/ampliseq", None, ["catalogue"])`、`(None, "2.18.0", ["catalogue"])`、`(None, None, ["catalogue","schema"])`、`(None, None, ["tags","catalogue"])`、`(None, None, ["schema"])`、`(None, None, ["tags"])`、`(None, None, ["catalogue","catalogue"])` | 七筆都丟 `JobRefused` | 自動：同上 |
| TC-031 | CQ-04；作法 3 最後一條 | 例外 | 同 TC-030 | 看這七個拒絕訊息的文字 | 每則都中英並陳，且都不含字面 `station` | 自動：同上 |
| TC-032 | CQ-05 | 功能 | alice 有在線環境，假時鐘 | `enqueue_pipeline_files(db, None, None, ["catalogue"], clock=clock, caller_user_id=1)` | 回一個 id。該列 `kind='pipeline_files'`，`confirmation_id IS NULL`，`deadline_at == now + 90`，`args_json == {"repo": null, "revision": null, "parts": ["catalogue"]}` | 自動：同上 |
| TC-033 | CQ-05 | 功能 | 接 TC-032 | 用 `latest_pipeline_files` 查三種條件 | `(db, None, None, ["catalogue"], 1)` 找得到那筆。`(db, None, None, ["tags"], 1)` 與 `(db, "nf-core/ampliseq", None, ["tags"], 1)` 找不到 | 自動：同上 |
| TC-034 | CQ-05；專長守則（擁有者規則） | 例外 | 接 TC-032，bob（`caller_user_id=2`）是另一位使用者 | bob 用 `latest_pipeline_files(db, None, None, ["catalogue"], 2)` 查 | 找不到 alice 的那筆 | 自動：同上 |
| TC-035 | CQ-06 | 功能 | 一個合格的 6 條 catalogue 結果 | 經 `clean_result("pipeline_files", …)` | 原樣通過（6 條，內容不變） | 自動：同上 |
| TC-036 | CQ-06；作法 4 | 例外 | 每條多給 `html_url`、`topics`、`stargazers_count`、`token` | 清洗 | 這四個鍵都不在輸出，每條只剩 `name`、`description`、`archived`、`tags` | 自動：同上 |
| TC-037 | CQ-06 | 例外 | 條目的 `name` 分別是 `"../x"`、`5`、缺少 | 清洗 | 這三條各自被丟掉，其他條目留著 | 自動：同上 |
| TC-038 | CQ-06 | 例外 | `description` 一條 401 字、一條不是字串 | 清洗 | 401 字的被切成 400 字。非字串的變成 `""` | 自動：同上 |
| TC-039 | CQ-06 | 例外 | `archived` 為 `"yes"` | 清洗 | 變成 False | 自動：同上 |
| TC-040 | CQ-06 | 例外 | `tags` 含非字串、含 `"../x"`，另一條有 501 個合格 tag | 清洗 | 壞的被丟掉。合格 tag 最多留 500 個 | 自動：同上 |
| TC-041 | CQ-06 | 例外 | `pipelines` 有 1001 條 | 清洗 | 只留前 1000 條 | 自動：同上 |
| TC-042 | CQ-06 | 例外 | `pipelines` 不是 list；另一筆是清洗後 0 條 | 清洗 | 兩種都得到 `{"status":"bad_response"}` | 自動：同上 |
| TC-043 | CQ-06；作法 4 | 例外 | `status` 為 `too_large`，但結果還夾帶 `pipelines` | 清洗 | 只留 `status` 與 `message`（不超過 300 字）。不產生 `entries`（`clean_result` 最後的 `else` 沒被碰到） | 自動：同上 |
| TC-044 | CQ-07 | 功能 | 一筆 catalogue 工作，代理領取後回合格的 catalogue 結果 | 走一遍 `take_result` | 存進去的 `result_json` 是清洗後的。給代理的 `claim` 中 `out["args"] == {"repo": None, "revision": None, "parts": ["catalogue"]}`，沒有 `confirmation`，也沒有 `run_token` | 自動：同上 |
| TC-045 | CQ-08；作法 4 | 功能 | 無 | 讀 `jobs.py` 的新常數 | `CATALOGUE_CACHE_SECONDS == 86400`，`PF_CATALOGUE_ENTRIES == 1000`，`PF_CATALOGUE_TAGS == 500`，`PF_DESCRIPTION_LIMIT == 400` | 自動：同上 |
| TC-046 | CQ-08 | 功能 | 無 | 用 `PF_PIPELINE_NAME.match` 試名字；比較 `PF_TAG_NAME` 與站台的 `_TAG_NAME` | `"ampliseq"`、`"Ampliseq_2"`、`"a.b"` 為真。`"../x"`、`"."`、`""`、`"a b"`、`"a/b"` 為假。`PF_TAG_NAME` 的 pattern 逐字等於站台 `_TAG_NAME.pattern` | 自動：同上 |

## 三、動作層 `nfcore_catalogue`（計畫 CA-01 至 CA-17）

用資料庫＋假時鐘，由測試代替代理答覆。「代理答覆 6 條」指跟 TC-005 同一份 fixture 的內容。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-047 | CA-01 | 功能 | 無 | 檢查 `actions.nfcore_catalogue` 的簽章 | 是一般函式（不是 coroutine）。參數依序為 `platform_path`、`compute_env`、`caller`、`enqueue`。第一個可位置也可關鍵字，其餘只能關鍵字。預設值為 `None`、`None`、`True` | 自動：`platform/tests/test_nfcore_catalogue.py` |
| TC-048 | CA-02；專長守則（對等性） | 功能 | 無 | 跑 `test_web_parity` | `"nfcore_catalogue"` 在 `WEB_ONLY` 清單裡，聯集檢查通過 | 自動：`platform/tests/test_web_parity.py` |
| TC-049 | CA-02；不做第 1 條 | 不在範圍 | 無 | 看 `mcp_server.build_server` 的工具名單 | 名單不含 `nfcore_catalogue`，工具數與 base 相同。沒有新增網頁路由 | 自動：`platform/tests/test_nfcore_catalogue.py` |
| TC-050 | CA-03 | 功能 | alice 有在線環境，還沒有任何工作 | 第一次呼叫 `nfcore_catalogue` | 回 `{"state":"loading","checked_at":None,"count":None,"error":None,"reason":None,"pipelines":None}`。資料庫恰一筆 `pipeline_files` 工作，`args == {"repo": None, "revision": None, "parts": ["catalogue"]}` | 自動：同上 |
| TC-051 | CA-03 | 功能 | 接 TC-050 | 再呼叫一次 | 仍是 `loading`，資料庫仍只有一筆 | 自動：同上 |
| TC-052 | CA-04 | 功能 | 代理答覆 6 條 | 再呼叫 | `state == "ready"`，`count == 6`，`checked_at == finished_at`。`pipelines` 依 name 排序，每條的鍵恰為 `{"name","repo","description","archived","latest"}` | 自動：同上 |
| TC-053 | CA-04（計畫的例子） | 功能 | 同 TC-052 | 看 `ampliseq` 與 `abotyper` | `ampliseq.repo == "nf-core/ampliseq"`，`ampliseq.latest == "3.0.0"`。`abotyper.latest is None`（只有 `dev`） | 自動：同上 |
| TC-054 | CA-04（計畫的例子） | 功能 | 同 TC-052 | 看 `exoseq` 與 `cellpainting` | `exoseq.archived is True`。`cellpainting.description == ""` | 自動：同上 |
| TC-055 | CA-04 | 功能 | 同 TC-052 | 把回傳 `json.dumps` | 得過。回傳裡沒有 `tags` 字樣 | 自動：同上 |
| TC-056 | CA-05 | 功能 | 代理答覆某條的 `tags == ["dev","3.0.0dev","1.0.0-rc1","v2.0.0","2.0.0","1.9.0"]` | 呼叫 | 該條 `latest == "2.0.0"`（純數字版本才算；同一版本不帶 v 的優先） | 自動：同上 |
| TC-057 | CA-05 | 功能 | 代理答覆某條的 `tags == ["dev"]` | 呼叫 | 該條 `latest is None` | 自動：同上 |
| TC-058 | CA-06 | 例外 | 用 monkeypatch 讓 `releases.repo_of` 對名字 `"x"` 丟 `ValueError` | 代理答覆含 `x` 的清單後呼叫 | `x` 那條不在清單，其餘照常，`count` 跟著減少 | 自動：同上 |
| TC-059 | CA-07 | 例外 | 代理回 catalogue 部分失敗，分別是 `too_large`、`bad_response`、`rate_limited`、`not_found` | 各呼叫一次 | `state == "error"`，`error` 依序為 `too_large`、`bad_response`、`rate_limited`、`not_found`。`pipelines is None`，`count is None` | 自動：同上 |
| TC-060 | CA-07；作法 6 失敗範例 | 例外 | 代理回整體 `network` 失敗 | 呼叫 | `state == "error"`，`error == "network"`。`reason` 逐字為「代理連不到 nf-co.re，請檢查那台機器的網路 (the agent could not reach nf-co.re; check that machine's network)」。`checked_at` 等於該工作的 `finished_at` | 自動：同上 |
| TC-061 | CA-07 | 例外 | 代理回 `refused` | 呼叫 | `error == "refused"`，`reason` 提到要更新代理 | 自動：同上 |
| TC-062 | CA-07 | 例外 | 工作排了但過了期限沒人領 | 呼叫 | `error == "no_answer"` | 自動：同上 |
| TC-063 | CA-07 | 例外 | 上面 `too_large`／`bad_response`／`rate_limited`／`not_found`／`network` 五種失敗 | 看 `reason` | 每則都中英並陳、含 `nf-co.re`、不含 `GitHub` | 自動：同上 |
| TC-064 | CA-08 | 例外 | 一筆失敗的工作，60 秒內 | 再呼叫 | 回同樣的錯誤，資料庫沒有新工作 | 自動：同上 |
| TC-065 | CA-08 | 功能 | 同上，時間推進 61 秒 | 再呼叫 | 回 `loading`，資料庫新增一筆工作 | 自動：同上 |
| TC-066 | CA-09 | 功能 | 已經是 `ready` | 時間推進 3600 秒再呼叫 | 仍 `ready`，`checked_at` 不變，資料庫沒有新工作 | 自動：同上 |
| TC-067 | CA-09 | 功能 | 已經是 `ready` | 時間推進到 `finished_at + 86400` 整（含）再呼叫 | 回 `loading`，資料庫新增一筆工作（剛好 86400 秒就算過期） | 自動：同上 |
| TC-068 | CA-09 | 功能 | 接 TC-067，新工作被答覆 | 再呼叫 | `ready`，`checked_at` 換成新的 | 自動：同上 |
| TC-069 | CA-10；裁決 5；不做第 5 條 | 不在範圍 | 清單已過 24 小時，新工作失敗（`network`） | 呼叫 | `state == "error"`，`error == "network"`。不會退回顯示舊清單（沒有 stale 退路） | 自動：同上 |
| TC-070 | CA-10 | 功能 | 接 TC-069，60 秒後 | 再呼叫 | 回 `loading` | 自動：同上 |
| TC-071 | CA-11 | 例外 | 呼叫者沒有任何在線代理 | 呼叫 | `error == "no_agent"`，`reason` 含「沒有在線的代理」，資料庫零新列 | 自動：同上 |
| TC-072 | CA-11 | 例外 | 同 TC-071 | 呼叫時帶 `enqueue=False` | 回 `loading`，資料庫零新列 | 自動：同上 |
| TC-073 | CA-12；專長守則（跨使用者） | 例外 | alice 的 catalogue 工作已 `ready`，bob 自己有在線環境 | bob 呼叫 | bob 得到 `loading`，並排自己的一筆。看不到 alice 的清單 | 自動：同上 |
| TC-074 | CA-12 | 例外 | bob 沒有在線環境 | bob 呼叫 | `error == "no_agent"` | 自動：同上 |
| TC-075 | CA-12 | 例外 | bob 的 `compute_env` 指向 alice 的環境 | bob 呼叫 | 措辭與「找不到這個環境」相同，不洩漏那是別人的環境 | 自動：同上 |
| TC-076 | CA-13；裁決 5；不做第 3 條 | 不在範圍 | 記下 `platform.db` 同資料夾的檔案清單 | `ready` 前後各列一次 | 清單完全相同，沒有新檔案（沒有 `nfcore-catalogue.json`，`release-tags.json` 也沒出現） | 自動：同上 |
| TC-077 | CA-14 | 功能 | 讀 `actions/__init__.py` | 找 marker | 有 `# ---- nfcore-catalogue: begin` 與 `end` 區塊。區塊內不含 `urllib`、`socket`、`subprocess`、`open(`、`station`。release-lookup-job 區塊（TC-133）仍存在且超過 80 行 | 自動：同上 |
| TC-078 | CA-14 | 功能 | 同上 | 數新區塊內名字不以 `_` 開頭的 `def` | 只有 `nfcore_catalogue` 一個 | 自動：同上 |
| TC-079 | CA-15；專長守則（錯誤訊息） | 例外 | 跑過上面所有情境 | 檢查每一次的回傳 | 每個回傳都能 `json.dumps`。`reason` 不含 `Traceback`、`sqlite`、`args_json`、`deadline_at`、`result_json`、`SELECT` | 自動：同上 |
| TC-080 | CA-15 | 功能 | 同上 | 檢查每一次的回傳 | 鍵集合永遠恰為 `{"state","checked_at","count","error","reason","pipelines"}`。`state == "error"` 時 `reason` 非空 | 自動：同上 |
| TC-081 | CA-16；作法 5；不做最後一條 | 不在範圍 | 有 `world` 夾具 | 呼叫 `pipeline_files(world, parts=["catalogue"])` 與 `parts=["schema","catalogue"]` | 兩者都回 `bad_input`（清單只能走 `nfcore_catalogue`），資料庫零新列 | 自動：同上 |
| TC-082 | CA-17；專長守則（確認管道） | 不在範圍 | 記下 `confirmations`、`launches`、`compute_envs`、`agents` 的列數 | 呼叫 `nfcore_catalogue`（含排隊與答覆） | 四張表列數不變。`SELECT DISTINCT kind FROM jobs` 只有 `pipeline_files`。這個動作只寫 `jobs` | 自動：同上 |
| TC-083 | 不做第 1 條；裁決 6 | 不在範圍 | 讀簽章與回傳 | 檢查有沒有 `query`／`limit` 參數，並呼叫一次 | 簽章沒有 `query`、`limit`。回傳是全部條目（6 條全回），平台沒做篩選或排名 | 自動：同上 |

## 四、既有測試的更新、範圍與文件

「改斷言」那幾條：只准改計畫表格列出的斷言，其餘不動。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-084 | 計畫「會改斷言」表第 1 列（TC-004） | 功能 | 看 `test_station_pipeline_files.py` | 讀 `the_four_hosts_are_allowed` | 測試改名為 `the_four_hosts_are_allowed`，迴圈多一個 `https://nf-co.re/pipelines.json`，原來的三個網址仍在 | 自動：`platform/tests/test_station_pipeline_files.py` |
| TC-085 | 同表第 2 列（`BAD_URLS`） | 功能 | 同上 | 讀 `BAD_URLS` | 刪掉 `https://nf-co.re/pipelines.json`。加入 `http://nf-co.re/pipelines.json`、`https://nf-co.re.evil.com/pipelines.json`、`https://www.nf-co.re/pipelines.json`。其餘項目沒少 | 自動：同上 |
| TC-086 | 同表第 3 列（TC-047） | 功能 | 同上 | 讀 `there_is_no_way_to_read_other_files` | `readme` 兩行不動。`job(["catalogue"])` 那行加註解「catalogue takes no repo／revision (CS-08)」。新增 `refused(ctx, net, job(["schema", "catalogue"], repo=None, revision=None))` | 自動：同上 |
| TC-087 | 同表第 4 列（檔首 docstring） | 功能 | 同上 | 讀第 2 行 | 文字改為「five kinds of public file（the fifth is nf-core's own pipeline list, test_nfcore_catalogue.py）」 | 手動：閱卷時讀該檔第 2 行 |
| TC-088 | 同表第 5 列（`BAD_ARGS`） | 功能 | 看 `test_pipeline_files_queue.py` | 讀 `BAD_ARGS` | 原 19 筆全在（只加不刪）。新增 `(None, None, ["schema"])`、`("nf-core/ampliseq", None, ["catalogue"])`、`(None, "2.18.0", ["catalogue"])`、`(None, None, ["catalogue", "schema"])` | 自動：`platform/tests/test_pipeline_files_queue.py` |
| TC-089 | 同表第 6 列（TC-159） | 功能 | 看 `test_pipeline_files_action.py` | 讀翻轉後的測試 | 改名 `the_catalogue_is_its_own_action`。斷言 `callable(actions.nfcore_catalogue)`。`pipeline_files` 簽章仍沒有 `catalogue` 參數。`pf(world, parts=["catalogue"])["error"] == "bad_input"` | 自動：`platform/tests/test_pipeline_files_action.py` |
| TC-090 | 同表第 7 列（TC-135） | 功能 | 同上 | 讀 `no_mcp_tool_for_the_...` | 名字從「two」改「three」，集合加 `"nfcore_catalogue"`，其他不動 | 自動：同上 |
| TC-091 | 同表第 8 列（`WEB_ONLY`） | 功能 | 看 `test_web_parity.py` | 讀 `WEB_ONLY` | 新增 `"nfcore_catalogue"` 一列，理由文字如計畫所寫，原兩列不動 | 自動：`platform/tests/test_web_parity.py` |
| TC-092 | 完成標準「上表以外零改動」 | 不在範圍 | 對 base 做 `git diff` | 檢查所有被動到的既有測試檔 | 除 TC-084 至 TC-091 列出的之外，沒有任何既有測試被改。沒有被移除、放寬或跳過的斷言。這四個檔只有表內的改動 | 手動：閱卷時讀 `git diff <base>...HEAD` |
| TC-093 | 完成標準；範圍「不准動」 | 不在範圍 | 對 base 做 `git diff --name-only` | 看檔案清單 | 只有計畫「範圍：檔案」所列的檔案。`store.py`、`schema.py`、`releases.py`、`mcp_server.py`、`web*.py`、`guidance.py`、`chat_tools.py`、其他站台檔、`pyproject.toml`、`tests/*.sh` 都沒有被改 | 手動：閱卷時讀 `git diff --name-only` |
| TC-094 | 不做倒數第 2 條；確認沒有牽動 | 不在範圍 | 既有測試（未改） | 跑 `test_pipeline_files_action.py` 的 TC-093、TC-097、TC-132、TC-133、TC-180 | 全綠，`pipeline_files` 與 `latest_release` 的簽章與回傳形狀沒變 | 自動：`platform/tests/test_pipeline_files_action.py` |
| TC-095 | 不做倒數第 3 條 | 不在範圍 | 既有測試（未改） | 跑 `test_station_pipeline_files.py` 的 TC-029 至 TC-032、TC-038、TC-040、TC-046、TC-048 | 全綠，既有五個 part 的行為、訊息、上限都沒變 | 自動：`platform/tests/test_station_pipeline_files.py` |
| TC-096 | 作法 7 | 功能 | 讀 `docs/PLATFORM.md` | 找三處 | `pipeline_files` 條目改為 five kinds，加入 nf-core 全部管線清單的說明，並提到 `actions.nfcore_catalogue`。三主機那句加入 `nf-co.re`（one fixed address）。Action layer 那段改為 Three actions，補一句 `actions.nfcore_catalogue(...)`。「What the platform stores」表沒有新增列 | 自動：`platform/tests/test_nfcore_catalogue.py` |
| TC-097 | 完成標準（文件） | 功能 | 讀 `docs/TESTING.md` | 找新一節 | 有「nfcore-catalogue：真的讀一次 nf-co.re (read nf-co.re for real, once)」一節，接在 release-lookup-job 手動節之後，含計畫手動步驟 1 至 5 | 自動：同上 |
| TC-098 | 完成標準（文件） | 功能 | 讀程式碼說明句 | 看 `handlers.py:7`、`pipeline_files.py` 的 1、5、7、57 行附近 | 「四種／三個主機」都改成「五種／四個主機」（handlers 那句是 "five kinds, the fifth being nf-core's own list of pipelines"） | 手動：閱卷時讀這幾行 |
| TC-099 | 完成標準；作法 5 後半 | 功能 | 讀 `specs/nfcore-catalogue/ledger.md` | 檢查內容 | 計畫「會改斷言」表八列的「舊→新＋理由」都有逐條記載。有 `git diff --stat` 貼上 | 手動：閱卷時讀 ledger |
| TC-100 | 範圍：檔案；環境事實「fixture 內容」 | 功能 | 讀 `platform/tests/fixtures/catalogue/pipelines-small.json` 與新測試檔頭 | 載入 fixture、讀檔頭第一行 | fixture 恰 6 條：`abotyper`（只有 `dev`）、`airrflow`、`ampliseq`（`3.0.0`、`2.18.0`、`dev`）、`cellpainting`（`description` 為 null）、`exoseq`（`archived` 為 true）、`rnaseq`。保留 `html_url`、`topics`、`stargazers_count`、`tag_sha` 等多餘鍵。檔案 60 KB 以內。測試檔頭有 `# Nothing existing: …` 且至少 15 字 | 自動：`platform/tests/test_nfcore_catalogue.py` |
| TC-101 | 失敗先行測試章節 | 功能 | 讀 ledger | 找最初的紅輸出 | ledger 貼有實作前跑新測試檔的紅色輸出（`PARTS` 沒有 `catalogue`、`actions.nfcore_catalogue` 不存在等） | 手動：閱卷時讀 ledger |
| TC-102 | 完成標準（自動） | 功能 | 執行者完成記號為 GREEN | 在 WSL 跑 `bash tests/run_all.sh` 的結果 | 全綠，含 `test_scope.py` 的 TC-061、TC-070、TC-071，`tests/platform_storage_doc_test.sh`、`tests/no_second_run_state_test.sh`、`tests/credentials_stay_in_settings_test.sh`。已知環境紅 `test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 視同綠 | 自動：`tests/run_all.sh`（WSL） |

## 五、手動：真的連 nf-co.re 讀一次

executor 不執行這一節。合併後由 developer-agent 或維護者在有網路的機器上做。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-103 | 手動步驟 1、2 | 功能 | 一個平台、一個代理、一個指向它的環境（同 release-lookup-job 手動步驟 1） | 用一行 Python 呼叫 `actions.nfcore_catalogue(<platform.db 路徑>)`，每 5 秒再呼叫直到不是 `loading`（最多約 1 分鐘） | `state == "ready"`，`count >= 150`（2026-10-26 實抓為 159）。`ampliseq` 的 `repo == "nf-core/ampliseq"`，`latest` 是最新純數字 tag（2026-10-26 是 `3.0.0`，以當天為準），`archived` 為 False。`exoseq.archived` 為 True。`abotyper.latest` 為 None。清單依 name 排序。`platform.db` 旁沒有新檔案 | 手動：`docs/TESTING.md` 新一節 |
| TC-104 | 手動步驟 3 | 功能 | 接 TC-103 | 立刻再呼叫一次 | `checked_at` 與上一次相同，`jobs` 表沒有新的 `pipeline_files` 列 | 手動：同上 |
| TC-105 | 手動步驟 4 | 例外 | 拔掉代理機器的網路，並把那筆工作列刪掉（或等 24 小時） | 再呼叫 | 約 1 分鐘內 `state == "error"`，`error == "network"`，`reason` 提到 nf-co.re 與檢查網路 | 手動：同上 |
| TC-106 | 手動步驟 5 | 功能 | 做完上面三步 | 讀 `specs/nfcore-catalogue/ledger.md` | 上面三步的輸出已貼進 ledger | 手動：閱卷時讀 ledger（合併後補） |

## 憲法與安全網

下面三條是計畫自己點名的：平台不連網（憲法原則 2＋`test_scope.py` TC-061，依計畫引用）、站台只讀（站台 TC-042）、連網只在兩個檔（站台 TC-041）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-107 | 平台自己不連網（計畫「憲法原則 2＋TC-061」；作法 8） | 例外 | 本次新增的平台程式 | 跑 `test_scope.py` 的 TC-061、TC-071 與新測試檔的掃描；看 `jobs.py`、`store.py` 整檔 | 新增的平台行沒有字面 `station`、`ssh`、`sbatch`、`urllib.request`、`import socket`、`socket.`、`subprocess`、`threading`、`while True`。`jobs.py`、`store.py` 整檔無 `station` | 自動：`platform/tests/test_scope.py` 與 `platform/tests/test_nfcore_catalogue.py` |
| TC-108 | 站台只讀、不帶憑證（計畫作法 8；站台 TC-042） | 例外 | 本次新增的站台程式 | 跑站台 TC-042 對整個 `pipeline_files.py` 的掃描 | 沒有 `open(`、`.write(`、`os.remove`、`shutil`、`subprocess`、`socket`、`ctx.site`、`site.call`、`Authorization`、`sbatch`、`rm -rf` | 自動：`platform/tests/test_station_pipeline_files.py` 與 `platform/tests/test_nfcore_catalogue.py` |
| TC-109 | 連網只在兩個檔（站台 TC-041） | 例外 | 本次新增的站台程式 | 跑站台 TC-041 | `abf_station/` 內含 `urllib.request` 的檔仍只有 `agent.py` 和 `pipeline_files.py` | 自動：`platform/tests/test_station_pipeline_files.py` |
