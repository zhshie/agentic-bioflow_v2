# 測試案例：docs/PLATFORM.md「平台存了什麼、存在哪、存多久」（issue #119 項目 1）

**規格**：`specs/platform-doc-storage/plan.md`（此功能沒有 spec.md；來源是 plan 的項目 1–3 與 P1–P3 裁定，沒有維護者逐字引用的例子）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：plan 說要做到的事，正常情況下做到了。
- **例外**：缺資料、規則不存在、文件與程式不一致時，測試要抓得到或文件要誠實說出來。
- **不在範圍**：plan 明講這次不做的事；確認真的沒做。

測試檔：`tests/platform_storage_doc_test.sh`（plan 規定先寫）。它在 `tests/*.sh`，會被 `tests/run_all.sh` 自動收進去。下列「自動」都指這支檔，或指現有的測試。

## User Story 1 — 表格：平台存了什麼、存在哪、存多久（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | plan 項目 1；P3 | 功能 | `docs/PLATFORM.md` 已改好 | 在檔內找標題 | 有且只有一個標題，內容恰好是 `## What the platform stores` | 自動：`tests/platform_storage_doc_test.sh` |
| TC-002 | plan 項目 1；P3 | 功能 | 同上 | 看該標題下的表格表頭 | 欄位依序是 `What`／`Where`／`How long`，三欄，不多不少 | 自動 |
| TC-003 | plan 項目 1（e.g. 清單） | 功能 | 同上 | 逐一找表格的列 | 每一種資料各有一列：run index（執行索引）、已確認送出的 bundle 與畫面文字、job rows（工作列）、tokens／users／OAuth、web sessions（網頁登入）、uploads（上傳檔）、fetched records（取回的 Nextflow 紀錄）。七種缺任何一種都算失敗 | 自動 |
| TC-004 | plan 項目 1；plan 測試第 2 點 | 功能 | 同上 | 取出每一列 Where 欄裡用反引號標出的檔名或表名 | 每個名稱都能在 `platform/` 的原始碼裡找到（例：`index.db`、`tokens.db`、`platform.db`、`confirmations`、`jobs`、`web_sessions`、`uploads`、`records`）；找不到的名稱 = 失敗 | 自動 |
| TC-005 | plan 項目 1（「docs/OPERATIONS.md section 4 lists files」） | 功能 | 同上 | 對照 `docs/OPERATIONS.md` 第 4 節的六項 | `index.db`、`tokens.db`、`platform.db`、`web_signing.key`、`uploads/`、`records/` 六項都在表格的 Where 欄出現至少一次 | 自動 |
| TC-006 | plan 項目 1（run index (rebuildable)） | 功能 | 同上 | 讀 run index 那一列 | How long 欄說它可以重建（rebuildable），並指向 `abf-platform rebuild`；沒有寫成「保存多久後刪除」之類的期限 | 自動 |
| TC-007 | plan 項目 1（keep-submissions） | 功能 | 同上 | 讀「bundle 與畫面文字」那一列 | How long 欄說「保留到擁有者自己忘掉它」，並提到 `abf-platform forget`，且沒有說有計時器自動清掉已確認的 | 自動 |
| TC-008 | plan 項目 1（job rows pruned 7 days after the job ends） | 功能 | 同上 | 讀 job rows 那一列 | How long 欄寫「工作結束後 7 天清掉」，數字 7 與 `platform/abf_platform/jobs.py` 的 `PRUNE_AFTER_SECONDS = 7 * 86400` 一致 | 自動 |
| TC-009 | plan 項目 1（「Every 'how long' must come from code or existing docs」） | 功能 | 同上 | 取出 How long 欄裡所有「N 天／N 小時」的數字 | 每一個期間都能在 `platform/abf_platform/*.py` 的常數換算後找到同值（例：7 天、12 小時的 web session、14 天的 run token、1 小時／30 天的 OAuth）。找不到出處的期間 = 失敗 | 自動 |
| TC-010 | plan 項目 1（「if the code has no rule, write 'no automatic deletion'」） | 例外 | 程式碼對 uploads 與 fetched records 沒有任何自動刪除（`platform/abf_platform` 內除了 web_sessions／jobs／confirmations／OAuth 外沒有 rmtree／unlink 這些資料夾的規則） | 讀 uploads 與 fetched records 兩列 | How long 欄逐字寫 `no automatic deletion` | 自動 |
| TC-011 | plan 項目 1（「never invent a period」） | 例外 | 同上 | 掃每一列的 How long 欄 | 沒有空白、沒有 `TBD`／`unknown`／`?` 之類的佔位；沒有「約」「大概」「通常」這種憑感覺的期限；每一格不是有出處的期間，就是「until …」，就是 `no automatic deletion` | 自動 |
| TC-012 | plan 測試第 2 點（測試要能失敗） | 例外 | 複製一份 PLATFORM.md，把某列 Where 欄的名稱改成程式碼裡不存在的名字（例 `ghost.db`） | 對那份複本跑 TC-004 的檢查 | 測試失敗並指出 `ghost.db`；還原後通過 | 自動 |

## User Story 2 — 第一次使用的揭露段落（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-013 | plan 項目 2；P3（一段、最多 3 句） | 功能 | PLATFORM.md 已改好 | 找 `## What the platform stores` 章節內的 first-use disclosure 段落 | 有一段（只有一段，不是兩段），句子數 ≤ 3，位在該章節內 | 自動 |
| TC-014 | plan 項目 2 | 功能 | 同上 | 讀該段 | 說明平台留著什麼（送出的 bundle 與畫面文字），並明說可用 `abf-platform forget` 把一次送出忘掉；`forget` 這個子命令真的存在於 `platform/abf_platform/cli.py` | 自動 |
| TC-015 | plan 項目 2（「Mark that showing it in the web/clients is not built yet」） | 功能 | 同上 | 讀該段 | 明白標示「在網頁／各 client 裡顯示這段話還沒做」，不能讀起來像已經會自動顯示 | 自動 |

## User Story 3 — ask 清單與過時的工具清單（優先度 P3）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-016 | plan 項目 3；P1 | 功能 | 約第 411 行的句子（"The Claude Code kit adds a permission `ask` rule for ..."） | 把句子裡的 `mcp__abf-platform__*` 名稱集合，和 `extensions/claude-code-kit/settings.json` 的 `permissions.ask` 集合比對 | 兩邊完全相同（目前是 launch、cancel、resume、relaunch、forget 五個），句子多一個或少一個都失敗 | 自動 |
| TC-017 | plan 項目 3（測試要釘住以免再漂移）；P1 | 例外 | 複製 settings.json，加入第六個 `mcp__abf-platform__foo`，或拿掉 `forget` | 對複本跑 TC-016 的檢查 | 測試失敗並指出差的那個名稱；證明測試是即時讀 settings.json，而不是寫死五個名字 | 自動 |
| TC-018 | P2（約第 6 行） | 功能 | PLATFORM.md 開頭第 2 點 | 讀 "Two more tools, `launch` and `cancel`, only ask..." 這一句 | 這句不再說 "Two more tools"，改成把五個寫入工具 `launch`、`cancel`、`resume`、`relaunch`、`forget` 都點名；仍寫「六個唯讀工具」 | 自動 |
| TC-019 | P2（約第 460 行的 Action layer） | 功能 | 「## Action layer」段 | 讀「一個動作一個函式」的清單與其後說明 | 清單與說明點名目前的寫入動作 launch、cancel、resume、relaunch、forget，與約第 274 行、第 466 行的說法一致，不再只剩 launch、cancel | 自動 |
| TC-020 | P2（「The test checks these lists against mcp_server.py's write tools」） | 功能 | `platform/abf_platform/mcp_server.py` 的寫入工具（標 `_WRITES` 或 `_STOPS` 的）集合 | 對 PLATFORM.md 內所有列舉寫入工具的句子（約第 6、274、411、460、466 行）逐句比對 | 每一句列出的寫入工具集合都等於 mcp_server.py 的寫入工具集合；任何一句漏掉或多出一個都失敗 | 自動 |
| TC-021 | P1（「Do NOT change lines ~417-422」） | 不在範圍 | 「The limits of the confirmation」與「Two more limits that are accepted」兩節 | 檢查這兩節 | 內容沒被改成五個工具；仍在講終端機指令 `abf-platform launch|cancel`（至少三處 "`abf-platform launch|cancel`" 字樣仍在，約第 417、421、422 行），不被誤改成 MCP ask 清單 | 自動 |

## 計畫的「不在範圍」

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | plan「Out of scope: code」 | 不在範圍 | 實作完成的分支 | 驗收者執行 `git diff --name-only main...HEAD` | 沒有任何檔案在 `platform/`、`hooks/`、`extensions/`、`skills/`、`scripts/` 之下 | 手動：驗收時以 git diff 核對（不加 TESTING.md 步驟，因為 plan 禁止改其他文件） |
| TC-023 | plan「Out of scope: CHANGELOG.md, other docs」 | 不在範圍 | 同上 | 同上 | 變動的檔案只有 `docs/PLATFORM.md`、`tests/platform_storage_doc_test.sh`，加上 `specs/platform-doc-storage/` 之下的檔案；`CHANGELOG.md`、`docs/OPERATIONS.md`、`docs/TESTING.md`、`README.md` 等都沒動 | 手動：同上 |
| TC-024 | plan 項目 2（顯示這段話「not built yet」） | 不在範圍 | 同上 | 驗收者查 diff，並在 `platform/` 搜這段揭露文字 | 網頁（`web.py`）、MCP 伺服器（`mcp_server.py`）、命令列都沒有新增顯示這段話的程式；揭露文字只出現在 PLATFORM.md | 手動：同上 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | 第 2 條（不留第二份 run 狀態；run index 只是索引） | 功能 | 新章節已寫好 | 讀 run index 那一列與其前後說明 | 文件仍把 index 說成「索引、可重建、真相在 Nextflow 自己的紀錄」，沒有把它說成權威資料；與第 5 節 "Rebuild the index" 不矛盾 | 自動（同 TC-006 的檢查，加上不得出現 "source of truth" 指向 index 的句子）；驗收者另讀文字確認 |
| TC-026 | 安全網「憑證不外洩」；第 3 條（不寫個人路徑、叢集路徑） | 功能 | 新章節已寫好 | 讀 tokens／users／OAuth／web sessions 列；執行 `bash tests/no_hardcoded_paths.sh` | 這些列只說存的是雜湊（hash）或簽章，沒有任何真實 token、密碼、個人家目錄路徑或叢集路徑；`no_hardcoded_paths.sh` 通過 | 自動：`tests/platform_storage_doc_test.sh`、`tests/no_hardcoded_paths.sh` |
| TC-027 | 開發流程「綠燈」：現有釘住 PLATFORM.md 文字的測試不變 | 功能 | 改完 PLATFORM.md | 跑 `platform/tests` 中引用 PLATFORM.md 的測試檔（`test_actions_layer.py`、`test_keep_submissions.py`、`test_launch_docs.py`、`test_owner_binding.py`、`test_scope.py`、`test_station_docs.py`、`test_station_envs.py`、`test_station_platform.py`）以及 `tests/platform_direction_docs_test.sh`、`tests/install_doc_test.sh` | 全部原樣通過；diff 中沒有任何一支現有測試檔被改動或放寬 | 自動：`bash tests/platform_test.sh` 與上述 `tests/*.sh`（WSL 或 CI） |
| TC-028 | 開發流程「先寫測試」 | 功能 | 實作開始前 | 查 git 歷史 | `tests/platform_storage_doc_test.sh` 的提交早於 `docs/PLATFORM.md` 的修改（或同一個提交裡測試先在舊文件上失敗）；`bash tests/run_all.sh --only platform_storage` 會列出並執行它 | 自動：`bash tests/run_all.sh --list` 內有此檔 |

<!--
Rules followed:
- 沒有 spec.md；每個 TC 的「對應需求」欄寫 plan 的項目編號或 P1–P3 裁定。
- IDs 核可後不再重編。
-->
