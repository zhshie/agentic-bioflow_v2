# 測試案例：分析失敗時，Jev 先幫忙指出是哪一類錯（選配）——v3 版（015）

**規格**：`specs/015-jev-triage/spec.md`（由 `origin/009-jev-triage` 搬來，並套入 `plan.md` 第 1 至 8 點修改後的版本）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

名詞：**Jev**＝TypeSafe 的雲端判斷服務（只回機率或 N 選 1）。**fixture**＝測試用的假回應檔，不上網。**`JEV_DRY_RUN`**＝設了這個變數，`scripts/jev.sh` 只讀假回應、完全不打網路。**假 curl**＝測試時放在 PATH 最前面的假 `curl`，被呼叫就記錄參數與標準輸入；在「不該上網」的測試裡被呼叫就算失敗。**門檻**＝`jev.min_confidence`，預設 0.80。**FAILED 流程**＝`skills/runs/SKILL.md` 裡「FAILED」那一段（v3 把舊的 `commands/runs.md` 搬到這裡）。**基底**＝`v3` 分支在 009a 合併後、本功能開始前的狀態，凡說「與基底相同」都比這個。**機器行**＝`scripts/jev.sh triage` 輸出的第 1 行 `JEV status=…`，給技能讀的，不是給使用者看的。

維護者的原話（出自 spec.md 的 Input 與「給維護者」，以及 plan.md 的「給維護者」）與對應 TC：

| 他的話 | 對應 TC |
|---|---|
| 「只要有價值就設計，若有風險未來考慮變成本地端」 | TC-043（`JEV_ENDPOINT` 可改指本地服務）、TC-054（ADR 記下理由）、TC-023 |
| 「使用者自備」 | TC-029、TC-030、TC-057、TC-083 |
| 「一致率 ≥ 90%」 | TC-064、TC-065 |
| 「只做除錯」 | TC-020 至 TC-024 |
| 「題庫我核可了」 | TC-058、TC-059、TC-060 |
| 給維護者 1（最後 200 行、8 類、有把握才帶路） | TC-001、TC-003、TC-005、TC-013、TC-019 |
| 給維護者 2（預設關、自備金鑰、第一次告知；關著時一切跟今天一模一樣） | TC-025、TC-027、TC-028、TC-045、TC-057、TC-078 |
| 給維護者 3（「Jev 未回應，改用原流程」） | TC-033、TC-074 |
| 給維護者 4（42 題、其中 37 題走到 Jev、≥ 90% 才寫「建議開啟」） | TC-059、TC-060、TC-062、TC-065 |
| plan 給維護者 1（「一個字都沒改你的決定」） | TC-059（題庫位元組不變）、TC-020 至 TC-024 |
| plan 給維護者 2（做在 `v3`、改的是 `skills/runs/SKILL.md`、不再發 2.18） | TC-002、TC-056、TC-086 |
| plan 給維護者 3（編號 015，不與 roadmap 的 009 混淆） | TC-088 |

## User Story 1 — 失敗原因被直接指出來（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | FR-001；US1 情境 1 | 功能 | Jev 已開、有金鑰，fixture 回「container、信心 0.93」；站台沒有拒絕紀錄、exit code 不是 137 | 執行 `scripts/jev.sh triage --err <檔> --exit 1` | 第 1 行為 `JEV status=ok category=container confidence=0.93 sent_chars=<n>`；第 2 行為「Jev 判斷：container（信心 0.93）」；exit 0 | 自動：`tests/jev_test.sh` |
| TC-002 | FR-001；plan 第 1 點 | 功能 | 讀 `skills/runs/SKILL.md` 與 `skills/operational/SKILL.md` | 檢查 FAILED 流程的順序 | Jev 步驟位在「No refusal lines up」分支內、「137, or killed」與「No `.command.log`」兩條規則之後、「Anything else」之前；步驟寫的是明確的腳本呼叫 `scripts/jev.sh triage --err … --exit …`；`skills/operational/SKILL.md` 的檢查順序（現有「先查站台出口紀錄再讀 Nextflow log」那行附近）同樣把它排在這個位置；FAILED 其他分支文字與基底相同 | 自動：`tests/jev_test.sh`（靜態順序檢查） |
| TC-003 | US1 情境 1、2 | 功能 | 真實失敗的 run、Jev 已開、高信心 | 照 `docs/TESTING.md` 開 Jev 版走一次 `/runs` | 先看到「Jev 判斷：<類別>（信心 0.xx）」那一行，之後 AI 只讀 `.command.err` 最後 200 行並照該類的說明走 | 手動：`docs/TESTING.md` |
| TC-004 | FR-002 | 功能 | 讀 `scripts/jev.sh` 與 `skills/runs/SKILL.md` | 比對類別清單 | 送給 Jev 的類別恰好 8 個：`memory`、`walltime`、`network`、`container`、`input`、`params`、`tool_bug`、`unknown`；除 `memory`（指向既有「Out of memory」段）與 `unknown`（走「Anything else」）外，其餘 6 類在 SKILL.md 各有一段，且每段都寫出「先看什麼、常見修法、何時要問使用者」 | 自動：`tests/jev_test.sh` |
| TC-005 | US1 情境 3；FR-012 | 功能 | fixture 回「container、信心 0.79」，門檻 0.80 | 執行 triage，再看 SKILL.md 規定的分流 | 結果為低信心；報告須註明「Jev 沒把握，照原流程」，走「Anything else」 | 自動 |
| TC-006 | US1 情境 3 | 功能 | fixture 回「unknown、信心 0.95」 | 同上 | 即使信心高，類別是 unknown 仍照原流程，並註明「Jev 沒把握，照原流程」 | 自動 |
| TC-007 | US1 情境 2（「信心 ≥ 門檻」）；FR-012 | 功能 | fixture 回「params、信心 0.80」，門檻 0.80 | 同上 | 剛好等於門檻算有把握，直接走 params 那一類 | 自動 |
| TC-008 | US1 情境 4 | 例外 | 讀 `skills/runs/SKILL.md` | 與基底比對：所有 ⏸（必須停下問使用者）的步驟 | 所有原有的 ⏸ 行與基底一字不差；新增的 Jev 步驟明寫「Jev 的判斷不讓任何需要使用者同意的事變成自動」；需改管線參數或放寬網路邊界的那幾類仍標 ⏸ | 自動 |
| TC-009 | US1 情境 5 | 例外 | 站台有拒絕紀錄對得上失敗時間 | 讀 SKILL.md 的順序 | 這條路徑走既有 egress 規則，Jev 步驟不在其中、不被呼叫 | 自動 |
| TC-010 | US1 情境 5 | 例外 | task exit code 137（題庫 T01、T03、T05、T43） | 讀 SKILL.md 的順序 | 走既有「Out of memory」，Jev 不被呼叫 | 自動 |
| TC-011 | US1 情境 5 | 例外 | 沒有 `.command.log` 也沒有 `.exitcode` | 讀 SKILL.md 的順序 | 照既有規則回報「工作目錄從計算端看不到」，Jev 不被呼叫 | 自動 |
| TC-012 | Edge「空的 .command.err」 | 例外 | `.command.err` 是空檔，Jev 已開 | 執行 triage | 第 1 行 `status=empty category=unknown`；不送任何請求（假 curl 沒被叫）；第 2 行說明；走原流程 | 自動 |
| TC-013 | Edge「超過 200 行／一行」 | 功能 | 一個 500 行的檔案、一個只有 1 行的檔案 | 執行 triage（假 curl 或 fixture 記錄送出內容） | 500 行檔只送最後 200 行（內容與檔案 `tail -n 200` 相同）；1 行檔整行送出；`sent_chars` 等於實際送出字數 | 自動 |
| TC-014 | Edge「非 UTF-8」 | 例外 | `.command.err` 含無效 UTF-8 位元組 | 執行 triage | 送出的請求本文是合法 UTF-8 的 JSON（可被 `jq` 解析）；不當掉 | 自動 |
| TC-015 | Edge「多個 task 失敗」 | 功能 | 讀 SKILL.md | 檢查 Jev 步驟的敘述 | 明寫只對找到的第一個失敗 task 呼叫一次 | 自動 |
| TC-016 | FR-003；plan 第 7(a) 點（沒有 exit code，如題庫 T11） | 例外 | 題庫 T11 那種沒有 exit code 的失敗；呼叫 `--exit none` | 執行 triage，並記錄送出的請求本文 | 不當掉，仍輸出合法的兩行；請求本文的 `state.exit_code` 為 JSON `null`（不是字串 "none"、不是 0） | 自動 |
| TC-017 | FR-003 | 功能 | 對 ok、disabled、no_key、failed、capped、empty 各跑一次 | 看輸出 | 第 1 行一定是 `JEV status=<六者之一> category=<key 或 -> confidence=<0.00 或 -> sent_chars=<n>`；除 disabled 外第 2 行給人看；每種情況 exit 0 | 自動 |
| TC-018 | FR-003；FR-005 | 例外 | fixture 回合法 JSON，但 `choice` 不是那 8 個之一（或信心缺漏、不在 0 到 1） | 執行 triage | `status=failed`，第 2 行說明原因，流程照舊；不把這個奇怪的類別當成答案 | 自動 |
| TC-019 | FR-007；「給維護者」1 | 功能 | 假 curl 記錄請求 | 執行一次 triage | 請求網址預設是 `https://api.typesafe.ai/v1/systemone`；`model` 是 `jev-latest`；`state` 只有 `exit_code` 與 `err_tail` 兩個欄位；`questions.category` 恰有那 8 個 criteria | 自動 |
| TC-020 | 不在範圍第 1 條（錯誤回報分類、逐樣本 QC、預選、hooks、verifier 閱卷前篩） | 不在範圍 | 看整個 repo | 搜尋對 `jev.sh` 的所有引用 | 只有 `skills/runs/SKILL.md`、`skills/operational/SKILL.md`、`scripts/dev/jev_replay.sh`、測試與文件引用；`hooks/`、`scripts/report.sh`、其他 `skills/*/SKILL.md`、`platform/` 都沒有 | 自動 |
| TC-021 | 不在範圍第 1 條（監看） | 不在範圍 | 與基底比對 | 比 `scripts/task_health.sh` 與 `scripts/report.sh` | 兩支與基底位元組相同 | 自動 |
| TC-022 | 不在範圍第 3 條（自動修復） | 不在範圍 | 讀 `scripts/jev.sh` | 搜尋它做的事 | 它只印出分診結果；沒有執行回應內容（無 `eval`／`bash -c` 作用於回應）、沒有啟動、取消、刪除任何東西（無 `tw`、`sbatch`、`scancel`、`rm`——自己的計數檔舊日清理除外，且只限狀態目錄內的 `jev-count-*`） | 自動 |
| TC-023 | 不在範圍第 2 條（本地模型、不退回其他 LLM）；FR-005 | 不在範圍 | 假 curl 記錄所有目的地；Jev 回 500 | 執行 triage | 唯一的目的地是 `JEV_ENDPOINT`（或預設網址）；失敗後沒有任何請求送往別的主機；repo 沒有附本地模型程式 | 自動 |
| TC-024 | 不在範圍第 1 條（管線／欄位預選、錯誤回報） | 不在範圍 | 與基底比對 | 比 `skills/` 下除 `runs/` 與 `operational/` 以外的檔案 | 全部與基底相同 | 自動 |

## User Story 2 — 沒開、沒金鑰、或 Jev 掛了，都不影響（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-025 | US2 情境 1；FR-004 | 功能 | `jev.enabled` 沒設；假 curl 一被叫就讓測試失敗 | 執行 triage | 假 curl 沒被叫；標準輸出第 1 行以 `JEV status=disabled` 開頭（plan 第 5 點：機器行照印）；第 1 行以外沒有任何字；exit 0 | 自動：`tests/jev_test.sh` |
| TC-026 | US2 情境 1 | 功能 | `jev.enabled=false`，即使環境裡有金鑰 | 執行 triage | 同 TC-025 | 自動 |
| TC-027 | US2 情境 1；SC-003；plan 第 5 點 | 功能 | 關閉狀態；FAILED 流程所用的既有腳本（`egress_ctl.sh`、`on_site.sh`、`task_health.sh`、`report.sh`） | 與基底各跑一次同樣輸入，比對標準輸出 | 逐字相同；這些腳本檔本身與基底位元組相同（Jev 沒有改動它們） | 自動（golden） |
| TC-028 | FR-004 | 功能 | 設定檔沒有任何 `jev.*` | 讀 `jev.enabled`、`jev.daily_cap`、`jev.min_confidence` | 依序為 false、500、0.80；設環境變數或設定檔時，環境變數優先 | 自動：`tests/settings_test.sh` 或 `tests/jev_test.sh` |
| TC-029 | US2 情境 2 | 例外 | `jev.enabled=true`，環境與金鑰檔都沒有金鑰 | 執行 triage | 第 1 行 `status=no_key`；第 2 行含「Jev 已開啟但找不到金鑰，改用原流程」；不送請求 | 自動 |
| TC-030 | FR-004 | 功能 | 金鑰同時存在於環境變數 `TYPESAFE_API_KEY` 與設定檔旁的 `.typesafe_key` | 執行 triage；再移除環境變數重跑 | 第一次用環境變數的值，第二次用檔案的值；`jev_key_file()` 的路徑規則與 `token_file()` 相同（同一個設定目錄，`scripts/settings.sh` 內並排） | 自動 |
| TC-031 | US2 情境 3 | 例外 | Jev 逾時（`__timeout__`；實機模式下 curl 帶 `--max-time 10`） | 執行 triage | `status=failed`；第 2 行「Jev 未回應，改用原流程（原因：timeout）」；流程照舊 | 自動 |
| TC-032 | US2 情境 3 | 例外 | Jev 回 401 或 400 | 執行 triage | `status=failed`，說出原因，不重試（只送 1 次請求） | 自動 |
| TC-033 | US2 情境 3；「給維護者」3 | 例外 | Jev 回 500（`__500__`） | 執行 triage | `status=failed`；第 2 行含「Jev 未回應，改用原流程」與原因 | 自動 |
| TC-034 | US2 情境 3 | 例外 | 第一次回 429，第二次成功（`__429_then_ok__`） | 執行 triage | 重試後 `status=ok`，結果正確 | 自動 |
| TC-035 | US2 情境 3 | 例外 | 一直回 429 或 529 | 執行 triage | 共 3 次請求（1 次加 2 次重試），重試前依序等 1 秒、3 秒；之後 `status=failed` 並說原因 | 自動 |
| TC-036 | US2 情境 3 | 例外 | Jev 回 200 但內容不是 JSON，或缺 `answers.category` | 執行 triage | `status=failed`，說明格式不對；不當掉 | 自動 |
| TC-037 | US2 情境 4 | 例外 | PATH 上沒有 `curl` | 執行 triage（Jev 已開、有金鑰） | 印出放行訊息，明說缺 `curl`；exit 0 | 自動 |
| TC-038 | US2 情境 4 | 例外 | PATH 上沒有 `jq` | 同上 | 印出放行訊息，明說缺 `jq`；exit 0 | 自動 |
| TC-039 | US2 情境 5 | 例外 | 今天的計數已等於上限 | 執行 triage | `status=capped`；第 2 行含「今天的 Jev 次數已用完，改用原流程」；不送請求 | 自動 |
| TC-040 | US2 情境 5；Assumptions | 功能 | `jev.daily_cap=2`；連叫三次；再把日期換成隔天 | 看三次結果與隔天結果 | 前兩次 ok、第三次 capped；隔天重新計數；前一天的計數檔被清掉 | 自動 |
| TC-041 | FR-006 | 功能 | `JEV_DRY_RUN=<目錄>`，Jev 已開、有金鑰；假 curl 一被叫就失敗 | 執行 triage | 不打網路；先找 `<目錄>/<err_tail 的 sha256>.json`，找不到才用 `default.json` | 自動 |
| TC-042 | FR-006 | 功能 | 看 `tests/jev_test.sh` 與 `tests/run_all.sh` | 搜尋 | `jev_test.sh` 所有呼叫都帶 `JEV_DRY_RUN`（或假 curl），沒有真網路呼叫；`run_all.sh` 會跑到它（`bash tests/run_all.sh --list` 列得出 `jev_test.sh`） | 自動 |
| TC-043 | FR-007；他的話「未來考慮變成本地端」 | 功能 | 設 `JEV_ENDPOINT=http://127.0.0.1:9/x`；假 curl 記錄網址 | 執行 triage | 請求送往該網址，其他部分（model、本文）不變；不需改任何程式碼 | 自動 |
| TC-044 | Edge「兩台機器」；FR-010 | 功能 | 跑完數次 triage | 看 repo 的 `git status` 與計數檔位置 | 計數檔在機器本地的狀態目錄（`${XDG_STATE_HOME:-$HOME/.local/state}/agentic-bioflow/`），repo 內沒有新增或變動的檔案 | 自動 |
| TC-078 | US2 情境 1；SC-003；plan 第 5 點 | 功能 | 讀 `skills/runs/SKILL.md` 的 Jev 步驟 | 檢查技能文字 | 明寫：機器行 `JEV status=…` 是給技能解析用的，不展示給使用者；當 `status=disabled` 時，使用者看到的回報沒有任何新增的 Jev 文字（沒有「Jev」字樣、沒有多一行）；`spec.md` US2 情境 1 的措辭與此一致（寫明「使用者看到的」逐字相同，而不是腳本標準輸出逐字相同） | 自動：`tests/jev_test.sh`（靜態檢查） |
| TC-079 | plan 第 7(c) 點；FR-012 | 功能 | 讀 `spec.md` 與 `docs/SETTINGS.md` | 找 `jev.min_confidence` | `spec.md` 有 FR-012，寫明 `jev.min_confidence`（預設 0.80；低於它或類別為 unknown 則走原流程）；`docs/SETTINGS.md` 的 Jev 段也寫到它；該條 FR 有對應 TC（TC-005、TC-007、TC-028） | 自動 |
| TC-081 | plan 第 7(d) 點 | 功能 | 計數歸零；`__429_then_ok__`（共 2 次 HTTP 請求）；另一次 fixture 為一直 429（共 3 次請求） | 各執行一次 triage，看計數檔 | 429 後成功的那次，計數恰好增加 1（不是 2）；一直 429 的那次，計數增加量不超過 1（絕不是 3） | 自動 |
| TC-082 | plan 第 7(b) 點 | 例外 | 金鑰檔 `.typesafe_key` 權限為 644（群組／其他人可讀），Jev 已開；假 curl 一被叫就失敗 | 執行 triage（在 Linux／WSL） | 印出一行說明（讀得出是金鑰檔權限過寬）；第 1 行 status 不是 `ok`；不送請求；exit 0；金鑰字串不出現在任何輸出 | 自動 |

## User Story 3 — 使用者知道送了什麼，金鑰不外洩（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-045 | US3 情境 1；「給維護者」2 | 功能 | 這台機器第一次呼叫（沒有標記檔），Jev 已開、有金鑰 | 執行 triage | 先印出告知，內容含：送出 `.command.err` 最後 200 行與 exit code、送到 `api.typesafe.ai`、內容可能含路徑與樣本名、TypeSafe 只對企業客戶提供不保留資料、如何關閉 | 自動 |
| TC-046 | US3 情境 1 | 功能 | 已有標記檔 | 再執行一次 | 不再印告知 | 自動 |
| TC-047 | US3 情境 1 | 功能 | 第一次呼叫，用假 curl 記錄時間順序 | 執行 triage | 告知先出現，之後才送出請求 | 自動 |
| TC-048 | US3 情境 1 | 例外 | 第一次呼叫但 Jev 沒開，或沒有金鑰 | 執行 triage | 不印「會送出什麼」的告知（什麼都沒送），也不建立標記檔 | 自動 |
| TC-049 | US3 情境 2；Safety Net 憑證條 | 例外 | 放一個可辨認的假金鑰（如 `FAKEKEY-9f3a`） | 對 ok、failed、capped、no_key、disabled、empty 各跑一次，收集 stdout、stderr | 假金鑰字串完全不出現 | 自動 |
| TC-050 | US3 情境 2；plan 第 7(e) 點 | 例外 | 假 curl 記錄完整參數列 | 執行 triage（有金鑰） | 假金鑰不在 curl 的參數列上（別人用 `ps` 看不到）；授權標頭不經由命令列傳遞 | 自動 |
| TC-051 | US3 情境 2；FR-004 | 例外 | 看 `.gitignore` 與 `tests/credentials_stay_in_settings_test.sh` | 跑該測試 | `.gitignore` 列出 `.typesafe_key`；該測試的靜態檢查涵蓋 `TYPESAFE_API_KEY`／`.typesafe_key`（在 `scripts/` 裡 echo 或 printf 它會讓測試轉紅，自我測試證明）；現況全綠 | 自動：`tests/credentials_stay_in_settings_test.sh` |
| TC-052 | US3 情境 2 | 例外 | 假金鑰；跑完一次完整流程（含 failed 與 ok） | 在測試用的暫存工作區、狀態目錄、log 中搜尋 | 假金鑰不出現在 params、log、trace、report、計數檔、標記檔 | 自動 |
| TC-053 | US3 情境 3 | 功能 | 讀 `docs/SETTINGS.md` | 找 Jev 段落 | 寫出：開關名稱（`jev.enabled`）、金鑰放哪（環境變數與 `.typesafe_key` 的路徑）、送出哪些欄位、每日上限與計數檔位置、`jev.min_confidence`、`JEV_ENDPOINT` | 自動（內容檢查） |
| TC-054 | FR-008；他的話（四句）；plan 第 3 點 | 功能 | 讀 `docs/adr/0007-jev-optional-triage.md`、`docs/POSITIONING.md`，並與基底比 `docs/adr/0006-*` | 檢查內容 | ADR 0007 存在，引用維護者 10-16 原話（含「只要有價值就設計，若有風險未來考慮變成本地端」「使用者自備」「只做除錯」）與官方網址；POSITIONING 原本「❌ Jev」那一行（第 91 行）已改成「選配、預設關、自備金鑰、外送已揭露」並連到 ADR；文件裡不再留「❌ Jev」；`docs/adr/0006-*` 與基底相同、沒有新增第二個 0007 | 自動 |
| TC-055 | FR-011 | 功能 | 讀 `docs/TESTING.md` 手動段 | 照步驟走 | 有「開 Jev、關 Jev 各跑一次失敗 run」的具體步驟，沒有工程背景的人也能照著做 | 手動：`docs/TESTING.md` |
| TC-056 | FR-011；plan 第 2 點 | 功能 | 與基底比 `.claude-plugin/plugin.json` 與 `CHANGELOG.md` | 看版本與 CHANGELOG | `plugin.json` 與基底位元組相同（版本仍是 `3.0.0-dev`）；`CHANGELOG.md` 在「3.0.0-dev (unreleased…)」那一節下恰好新增一行提到 Jev 分診，其餘行不變；`spec.md` 的 FR-011 與 `tasks.md` 的 T013 寫的也是 CHANGELOG 而不是 plugin.json 升版 | 自動 |
| TC-057 | 他的話「使用者自備」；「給維護者」2 | 功能 | 搜尋整個 repo 與預設設定範本 | 找金鑰與開關 | repo 內沒有任何 TypeSafe 金鑰；任何隨附的預設設定都沒有把 `jev.enabled` 設成 true | 自動 |
| TC-083 | 他的話「使用者自備」；plan 第 7(b) 點 | 功能 | 讀 `docs/SETTINGS.md` 的金鑰說明 | 抽出文件給的建立指令（`umask 077; printf '%s' "$KEY" > <設定目錄>/.typesafe_key`），在暫存設定目錄實際執行（Linux／WSL） | 文件確實有這行指令；執行後 `.typesafe_key` 的權限是 600；內容為金鑰本身；`scripts/jev.sh` 自己不建立金鑰檔 | 自動 |
| TC-084 | US3 情境 2；plan 第 7(e) 點 | 例外 | 假 curl 同時記錄參數列與標準輸入；有假金鑰 | 執行 triage | 參數列含 `--config` 且接 `-`；標準輸入含一行 `header = "Authorization: Bearer <假金鑰>"`；假金鑰不在參數列任何位置 | 自動 |

## User Story 4 — 用核可題庫量準度（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-058 | US4 情境 1 | 功能 | `specs/015-jev-triage/labels.json` 與每題一份 fixture；`JEV_DRY_RUN` | 把 42 題的 `err_tail` 與 `exit_code` 逐題丟給 `jev.sh triage` | 每題都走完，第 1 行 `status=ok`，類別是 8 類之一，信心是 0 到 1 的數字；T11 的 `exit_code` 為 null 也能走完 | 自動：`tests/jev_test.sh` |
| TC-059 | 他的話「題庫我核可了」；「給維護者」4；plan「Carry over」 | 功能 | `specs/015-jev-triage/labels.json` | 計數並算雜湊 | 恰好 42 題；id 為 T01 至 T28、T30 至 T40、T42、T43、T44（沒有 T29、T41）；檔案 sha256 為 `dd1b455b2f4ef0c7cf0c3d6940a5e092d44abb6d3b1592f8e94528260fc83e57`（與 `origin/009-jev-triage` 上的檔案相同），實作期間不得變動（要改須回維護者再核可） | 自動 |
| TC-060 | US4 情境 2 | 功能 | `labels.json` 與 `skills/runs/SKILL.md` | 檢查 T01、T03、T05、T43、T14 | 前四題 exit code 是 137，T14 的 err 含 relay 的 `DENY-DOMAIN` 行；它們都會被 SKILL.md 裡排在 Jev 步驟之前的規則接走；其餘 37 題沒有這兩種情況 | 自動 |
| TC-061 | US4 情境 2；tasks T012 | 例外 | 沒有金鑰、也沒有設 `JEV_DRY_RUN` | 執行 `scripts/dev/jev_replay.sh` | 拒絕執行並說明需要金鑰；exit 非 0；不寫出 `replay-report.md` | 自動 |
| TC-062 | US4 情境 2；SC-001 | 功能 | 真金鑰、Jev 已開 | 維護者手動跑 `scripts/dev/jev_replay.sh` | 只對 37 題計分；`specs/015-jev-triage/replay-report.md` 含：整體答對率、各類答對率、信心門檻建議、總 token、延遲、答錯題號 | 手動：`docs/TESTING.md` |
| TC-063 | US4 情境 2 | 功能 | 同上 | 看報告 | 報告記載那 5 題（T01、T03、T05、T14、T43）確實沒有呼叫 Jev | 手動：`docs/TESTING.md` |
| TC-064 | US4 情境 3；plan 第 6 點；他的話「一致率 ≥ 90%」 | 例外 | `JEV_DRY_RUN` 加假金鑰，fixture 刻意讓 5 題答錯（答對率 32/37 = 86%） | 跑 `scripts/dev/jev_replay.sh`（離線） | 腳本在離線模式下能跑完；報告內容列出答錯的 5 個題號、答對率 32/37；`docs/SETTINGS.md` 沒有「建議開啟」字樣 | 自動：`tests/jev_test.sh` |
| TC-065 | SC-001；他的話「一致率 ≥ 90%」 | 功能 | repo 現況 | 搜尋「建議開啟」 | 只有在 `replay-report.md` 存在且記載答對 ≥ 34/37（≥ 90%；33/37 只有 89.2%，不算）時，文件才可以出現「建議開啟」；否則一個字都不能有 | 自動 |
| TC-066 | SC-002 | 功能 | 真金鑰 | 看 `replay-report.md` | 有「高信心時 AI 讀進的錯誤訊息字數 vs 原本」的前後對比 | 手動：`docs/TESTING.md` |
| TC-067 | SC-004 | 功能 | `tests/fixtures/jev/` | 列出 fixture | 涵蓋：高信心、低信心、unknown、500、逾時、429 後成功、缺 jq、無金鑰、達上限；`tests/jev_test.sh` 各有對應案例 | 自動 |
| TC-080 | SC-002；plan 第 4 點 | 功能 | `JEV_DRY_RUN` 加假金鑰，fixture 讓 37 題都是高信心 | 跑 `scripts/dev/jev_replay.sh`（離線），讀報告表格 | 報告對每個被計分的題目有兩欄：「有 Jev 時 AI 讀的字數」（`err_tail` 最後 200 行的字數）與「沒有 Jev 時」（fixture 中整份 `.command.err` 的字數），並有兩欄的總計；任一題「有 Jev」字數不大於 200 行對應的字數，也不大於「沒有 Jev」字數；字數是從題庫實際算出，不是固定常數 | 自動：`tests/jev_test.sh` |

## 計畫的搬家與收尾要求（015）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-085 | plan 第 8 點 | 功能 | 讀 `specs/015-jev-triage/plan.md` 的 Constitution Check，並搜尋 `platform/` | 檢查內容 | Constitution Check 寫明：Jev 是 runs 技能內的一步、由一支腳本支撐；之後 issue #93 第 6 步改寫 runs 技能去呼叫平台動作時，Jev 步驟仍是技能裡的一個腳本呼叫，不是 MCP 工具、不屬於動作層（它不改任何狀態、不需要關卡）；`platform/` 沒有任何 `jev` 字樣 | 自動 |
| TC-086 | plan 第 1 點；「Not in this PR」 | 功能 | 與基底比 `tests/` 與其他既有檔案 | 看這個分支改了哪些既有測試檔 | 既有測試檔裡只有 `tests/credentials_stay_in_settings_test.sh` 被改，且只有新增（沒有刪除或放寬任何斷言、沒有跳過案例）；`tests/off_design_single_path.sh`、`tests/flow_skills_layout_test.sh`、`tests/runs_report_format_test.sh`、`tests/egress_allow_test.sh`、`tests/works_without_host_test.sh` 與基底位元組相同，且在新技能文字下仍綠；`origin/009-jev-triage` 分支未被動過 | 自動 |
| TC-087 | plan「Order」 | 功能 | 分支完成 | 在 WSL 跑 `bash tests/run_all.sh`；在 repo 根目錄跑 `claude plugin validate .` | 兩者都通過（CI 同樣綠） | 自動：CI；`tests/run_all.sh` |
| TC-088 | plan 第 1 點、編號說明 | 功能 | 讀 `specs/015-jev-triage/` 下的 `spec.md`、`plan.md`、`tasks.md` | 搜尋舊 slug 與舊路徑 | 除了 `plan.md` 開頭說明「原名 009-jev-triage」的那一句外，沒有 `specs/009-jev-triage`；沒有指向舊的 `commands/runs.md` 的引用（FR-001、Project Structure、tasks T008 都改成 `skills/runs/SKILL.md`）；`specs/009-jev-triage/` 目錄在此分支不存在 | 自動 |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-068 | I-1（先查現成工具） | 功能 | `scripts/jev.sh`、`scripts/dev/jev_replay.sh` | 讀檔頭並跑檢查 | 兩支檔頭都有 `# Nothing existing: <理由>` 或 `# Not <tool>: <理由>`（FR-009）；`tests/scripts_name_their_alternative.sh` 綠 | 自動：`tests/scripts_name_their_alternative.sh` |
| TC-069 | I-2（不留第二份執行狀態）；FR-010 | 功能 | 計數檔與標記檔 | 跑檢查並看內容 | `tests/no_second_run_state_test.sh` 綠；若為此新增白名單，須附理由；兩個檔只含一個整數或空標記，沒有 run id、task、狀態 | 自動：`tests/no_second_run_state_test.sh` |
| TC-070 | I-2；「分診結果只印出，不存檔」 | 功能 | 跑一次 triage 前後各列檔案 | 比對 | 除計數檔與標記檔外，沒有新檔（沒有存分診結果、沒有存 `err_tail`） | 自動 |
| TC-071 | II-3（無個人／叢集路徑） | 功能 | 本次新增與改動的檔案 | 跑檢查 | `tests/no_hardcoded_paths.sh` 綠；網址只由 `JEV_ENDPOINT` 預設，路徑由設定推導 | 自動：`tests/no_hardcoded_paths.sh` |
| TC-072 | II-4（指令層不點名排程器） | 功能 | `skills/runs/SKILL.md` 新增文字 | 跑檢查 | `tests/command_layer_is_site_neutral.sh` 綠（`walltime` 那段不得寫出特定排程器、分區名稱） | 自動：`tests/command_layer_is_site_neutral.sh` |
| TC-073 | II-5（判斷與程序寫在可讀可跑的檔案） | 功能 | 拿掉 `hooks/` 與 `.claude-plugin/` | 跑檢查 | `tests/works_without_host_test.sh` 與 `tests/commands_resolve_their_own_paths.sh` 綠；`jev.sh` 單靠 `scripts/` 就能執行，SKILL.md 用外掛根目錄路徑呼叫它 | 自動 |
| TC-074 | VI-13（出事要說出來） | 例外 | 對 no_key、failed、capped、empty、缺 curl、缺 jq 各跑一次 | 看第 2 行 | 每一種都有一句人看得懂的話，說明發生什麼與接下來走原流程；沒有任何一種是安靜放行，也沒有任何一種被當成「高信心」往下走 | 自動 |
| TC-075 | Safety Net（不放寬） | 功能 | 與基底比對 | 比 `hooks/` | `hooks/` 與基底相同；`tests/in_use_test.sh`、`tests/confirm_launch_test.sh`、`tests/confirm_cleanup_test.sh` 綠 | 自動 |
| TC-076 | Safety Net（啟動需確認、刪除需確認） | 例外 | Jev 回傳要「放寬網路邊界」或「改參數」那類 | 依 SKILL.md 走到該類 | 流程停下問使用者；沒有任何自動啟動、自動刪 `work/`、自動加白名單 | 自動（靜態檢查 SKILL.md） |
| TC-077 | 開發流程（每階段全綠）；SC-004 | 功能 | 實作完成 | 在 WSL 跑 `bash tests/run_all.sh` | 全綠，CI 綠；`spec.md`、`test-case.md`、`test-case-overview.md`、`labels.json` 在「合約已確認」之後沒被改過（git 歷史可查） | 自動：`tests/run_all.sh` |
| TC-089 | 開發流程（測試案例由獨立審查者出、實作者不得改規格） | 功能 | 看這個分支的 git 歷史 | 找出「合約已確認」的 commit，比對之後對 `spec.md`、`test-case*.md`、`labels.json` 的變更 | 之後沒有任何變更；plan 第 1、2、5、7(c) 點對 `spec.md` 的修改（路徑、FR-011、US2 情境 1、FR-012）全部發生在合約確認之前 | 自動（驗收時查 git 歷史） |
