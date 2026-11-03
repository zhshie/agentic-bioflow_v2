# 測試案例：PITFALLS 條目補四行固定欄位＋PLATFORM.md 846 行 tier 字樣

**規格**：`specs/pitfalls-frontmatter/plan.md`（本任務沒有 spec.md，以計畫為準；維護者原話在計畫「維護者原話」四點）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做，或會明白說「這個不支援」而不是悄悄亂做。

**名詞**：「條目」＝ `docs/PITFALLS.md` 裡以粗體編號開頭的一個坑（例如 `**2b. ...**`）。「四行」＝ `Symptom:`、`Root cause:`、`Check:`、`Touches:`。
**條目數（驗證者在 v3 檔案上實數）**：共 **94** 條，不是計畫寫的 95。判別式 `^\*\*[0-9]+[a-z0-9]*\. `（點後有空格）只抓到 93 條，漏掉第 14 條（它的標題行是 `**14.** Before writing a check...`，點後接 `**`）；另有一行 `**3.3 s**`（約 695 行，在 16c 條內文中）長得像標題，其實是正文，不是條目。測試必須用能認得第 14 條、又不會在 `**3.3 s**` 處把 16c 切斷的判別式，例如 `^\*\*[0-9]+[a-z0-9]*\.( |\*\*)`。

## User Story 1 — 每個條目末尾都有四行固定欄位，可以 grep（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 計畫「檔首格式說明」；維護者原話 2「檔首有一段簡短的格式說明」；測試案例 1 | 功能 | `docs/PITFALLS.md` 已改好 | 執行 `bash tests/pitfalls_format_test.sh`，看 header 這一項 | 檔內有一行 `## How an entry is written`，位置在第一個 `## Setting up the agent` 之前；這一段（到下一個 `## ` 為止）文字裡出現 `Symptom:`、`Root cause:`、`Check:`、`Touches:` 四個標籤名；段內提到兩個 grep 範例（`grep -n '^Touches:.*prepare_launch' docs/PITFALLS.md` 與 `grep -n '^Check: none automated' docs/PITFALLS.md`），並說明「欄位是索引、正文是依據，兩者不一致以正文為準」。這一段只用英文，約 10 行 | 自動：`tests/pitfalls_format_test.sh` |
| TC-002 | 維護者原話 1「每條都有 symptom、root cause、check 三欄」；計畫「格式」；測試案例 2 | 功能 | 同上 | 執行測試，逐條掃描（條目＝從標題行到下一個標題行、下一個 `## `、或檔尾） | 94 個條目每一條都「恰好各有一行」以 `Symptom:`、`Root cause:`、`Check:`、`Touches:` 開頭（標籤前沒有任何符號，大小寫完全一致）、順序依此、標籤後有非空內容、每行單行不折行；四行在條目最後一行正文之後、緊接空行之前 | 自動：`tests/pitfalls_format_test.sh` |
| TC-003 | 計畫「不做」不刪條目；測試案例 3（驗證者更正數字） | 功能 | 同上 | 執行測試，看條目數那一項 | 條目標題行數「等於 94」（含第 14 條，不含 `**3.3 s**` 那行）；編號 1 到 58 每個整數至少出現一次；16c 條的內文沒有被 `**3.3 s**` 切成兩個條目（16c 自己恰有一組四行）。若測試的判別式漏掉第 14 條或把 `**3.3 s**` 算成條目，此項不通過 | 自動：`tests/pitfalls_format_test.sh` |
| TC-004 | 計畫「Check: 優先填條目自己或 repo 已有的測試／腳本」；測試案例 4 | 功能 | 同上 | 執行測試，看 Check 誠實那一項 | 每條的 `Check:` 內容要嘛含反引號包住的字串，要嘛以 `none automated:` 開頭；反引號內若是 repo 路徑（以 `tests/`、`platform/tests/`、`scripts/` 開頭），該檔相對 repo 根確實存在 | 自動：`tests/pitfalls_format_test.sh` |
| TC-005 | 計畫「Touches 讓 grep -n '^Touches:.*<名稱>' 可用」；測試案例 5 | 功能 | 同上 | 執行測試；再手動跑 `grep -c '^Touches:' docs/PITFALLS.md` 與 `grep -n '^Touches:.*prepare_launch' docs/PITFALLS.md` | 每條 `Touches:` 後至少一個項目（逗號分隔）；全檔以 `Touches:` 開頭的行數等於條目數 94（所以檔首說明段裡不可有任何一行以四個標籤之一開頭，範例要放在行中間或用反引號／項目符號帶開）；`prepare_league`以外的範例 `prepare_launch` 能 grep 到至少一條 | 自動：`tests/pitfalls_format_test.sh` |
| TC-006 | 計畫「Touches 用條目正文出現過的路徑與工具名」；裁決 3「欄位內容取自原文」 | 功能 | 同上 | 執行測試，看 Touches 來源那一項（對每條，把 `Touches:` 的每個項目拿去該條目原文比對） | 每個 Touches 項目（路徑或工具名，大小寫照原樣）都在該條目的原文裡出現過；沒有憑空多出的名稱 | 自動：`tests/pitfalls_format_test.sh` |
| TC-007 | 維護者原話 2「Convert existing entries without changing meaning」；計畫「完成標準」抽樣三條；裁決 3 | 功能 | 同上 | 閱卷時讀條目 2b、28、57 的原文與新增四行 | 四行的內容都能在該條原文找到依據（可濃縮、可用原有詞），沒有補寫原文沒講的事實；原文沒講根因的條目，`Root cause:` 寫的是 `not established in this entry`，不是猜的；`Check:` 沒有自動檢查的條目寫 `none automated: <條目裡已有的手動核對步驟>`。發現憑空補寫即不通過 | 手動：閱卷者逐條讀（`docs/TESTING.md` 沒有此步驟，計畫不准改該檔，見總覽「不確定的地方」） |
| TC-008 | 計畫測試案例 2「失敗訊息要印出缺欄位的條目編號」 | 例外 | 在未補欄位的 v3 原檔上（或刪掉某一條的 `Touches:` 行的檔案副本上）執行測試 | 執行 `bash tests/pitfalls_format_test.sh` | 測試失敗（紅），且訊息逐一印出缺欄位的條目編號與缺哪個欄位，不是只說「失敗」 | 自動：`tests/pitfalls_format_test.sh`（ledger 貼紅燈輸出） |
| TC-009 | 計畫「完成標準」第 1 點：測試「在未改文件前確實紅過」 | 功能 | 測試檔已寫好、`docs/PITFALLS.md` 與 `docs/PLATFORM.md` 尚未改 | 在尚未改文件的狀態下跑一次測試，把輸出貼進 `ledger.md`；改完文件後再跑一次 | 第一次輸出為紅（至少 TC-001、TC-002、TC-005、TC-014 對應項失敗）；第二次全綠 | 手動：閱卷者看 `ledger.md` 的紅燈與綠燈輸出，並自己執行一次測試檔 |

## User Story 2 — 既有文字一行不刪不改，被別處釘住的東西還在（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-010 | 計畫「被釘住的既有檢查」；測試案例 6 | 功能 | `docs/PITFALLS.md` 已改好 | 執行測試，看被釘住字串那一項 | 檔內仍有：`--relative-paths`、`auto mode classifier`、`UNVERIFIED`、`maxParallel`、`NXF_SINGULARITY_LIBRARYDIR`、`NXF_SINGULARITY_CACHEDIR`、「GatewayPorts off on NCHC: reverse forward is loopback-only (measured 2026-10-11)」、「Seqera launcher scripts hold the token in a 755 file」；且恰有一行符合 `^\*\*52\. .*read-only.*\*\*`、恰有一行符合 `^\*\*53\. .*-r.*\*\*`（標題行未被動過） | 自動：`tests/pitfalls_format_test.sh` |
| TC-011 | 計畫「完成標準」第 2 點 | 功能 | 同上 | 各別執行 `bash tests/pitfalls_supervise_test.sh`、`bash tests/docs_nano4_keys.sh`、`bash tests/column_output_relay_rule.sh`、`bash tests/daemon_cwd_test.sh`，以及 `platform/tests/test_launch_docs.py` | 全部通過；`scripts/agent_ctl.sh`、`scripts/egress_ctl.sh` 仍含字串 `PITFALLS 36`，且 PITFALLS 第 36 條仍在（編號與順序未動）。（完整套件 `tests/run_all.sh` 綠由完成記號 GATE 把關） | 自動：上列既有測試檔（執行時以各檔實際結果為準） |
| TC-012 | 維護者原話 2「既有文字一行不刪不改（diff 只有新增行）」；計畫「作法」末段 | 功能 | 分支相對 `origin/v3` 已有變更 | 閱卷者執行 `git diff --numstat origin/v3 -- docs/PITFALLS.md` | 刪除欄為 0（只有新增行）；新增行數約為 94×4 加檔首說明段；行尾 CRLF／LF 維持原樣，沒有整檔轉換 | 手動：閱卷者執行該 git 指令（證據也貼在 `ledger.md`） |
| TC-013 | 計畫測試案例 8；憲法第 V 原則精神（不留 token） | 例外 | 同上 | 執行測試，看秘密字串那一項 | 新增的欄位文字不含 `abf_pat_`，也不符合 `abf_pat_\|mst1\d{5}\|u9\d{7}` 樣式；若有人放進去，測試失敗並指出所在條目 | 自動：`tests/pitfalls_format_test.sh` |

## User Story 3 — PLATFORM.md 846 行改成 tier C（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-014 | 維護者原話 4「docs/PLATFORM.md:846『one tier A PR』依 11-03 A／C 對調改成 tier C」；測試案例 7 | 功能 | `docs/PLATFORM.md` 已改好 | 執行測試，看 platform tier 那一項 | `docs/PLATFORM.md` 不含 `one tier A PR`，且含完整句 `A new snapshot is one tier C PR: the changed file, plus the new sha here and in the test.`（前面的「- 」清單符號照舊）；同時 `platform/tests/test_catalogue.py` 第 419 行的正規式須接受 `tier C`（只准改那一處，改成 `tier A|tier C|A-tier|A 級|A級`），且該測試仍綠 | 自動：`tests/pitfalls_format_test.sh` |
| TC-015 | 維護者原話 4「不波及其他句子」；計畫「PLATFORM.md 846 行」 | 功能 | 同上 | 閱卷者執行 `git diff origin/v3 -- docs/PLATFORM.md`；並跑 `platform/tests/test_launch_docs.py` | diff 只有 846 行那一行：一行刪、一行增，差別只有 `A` 變 `C`；沒有加註解、沒有擴寫；`test_launch_docs.py` 仍綠。`ledger.md` 有記：constitution 6.2.0 只寫「開發主導者自行合併」、沒有出現 A／B／C 字母，所以executor 無從用它確認「C＝自行合併」，改依維護者原話（backlog 項 4）執行，並貼出實際讀到的原文 | 手動：閱卷者執行該 git 指令並讀 `ledger.md` |
| TC-016 | 計畫「同檔 746 行另有 Tier A…本任務不動」 | 不在範圍 | 同上 | 閱卷者看 `git diff origin/v3 -- docs/PLATFORM.md` 與 `ledger.md` | 746 行「*(Tier A: OAuth only adds another way ...」一字未動；`ledger.md` 有一行說明「746 行仍為 Tier A，是否也要隨 A／C 對調改，請 developer-agent 判斷」 | 手動：閱卷者執行該 git 指令並讀 `ledger.md` |

## User Story 4 — 範圍邊界：只動三個檔、不重做條目（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-017 | 維護者原話 3「Docs only」；計畫「不得動」與「不做」最後兩項 | 不在範圍 | 分支相對 `origin/v3` 已有變更 | 閱卷者執行 `git diff --stat origin/v3...HEAD` | 變更檔只有 `docs/PITFALLS.md`、`docs/PLATFORM.md`、`tests/pitfalls_format_test.sh`，加上本任務自己的 `specs/pitfalls-frontmatter/` 文件；沒有 `.specify/memory/constitution.md`、`.github/`、`hooks/`、`plugin.json`、`platform/abf_station/`、任何 `scripts/`；也沒有任何「讓 dev-planner 自動讀這些欄位」的程式 | 手動：閱卷者執行該 git 指令 |
| TC-018 | 計畫「不做」：不改原文／編號／順序、不合併拆分刪除、不新增條目、不拆檔、不改 YAML | 不在範圍 | 同上 | 閱卷者比對 `git show origin/v3:docs/PITFALLS.md` 與新檔的標題行清單，以及 `^## ` 章節清單 | 條目標題行的編號、順序、文字與 v3 完全相同（共 94 條，沒有新增、合併、拆分、刪除或搬動）；原有 7 個 `##` 章節（Setting up the agent、Resources、Launching、Do not rebuild what nf-core already does、Driving the site from a laptop、Driving the IDE from a terminal、Lab agents）順序不變，唯一多出的 `##` 是 `## How an entry is written`；PITFALLS 仍是單一 markdown 檔，沒有 YAML frontmatter | 手動：閱卷者比對 |
| TC-019 | 計畫範圍：新測試「不要為此改 run_all.sh」 | 不在範圍 | 同上 | 閱卷者確認 `git diff origin/v3 -- tests/run_all.sh` 為空；在 WSL 執行 `bash tests/run_all.sh --list`（或 `--only pitfalls_format`） | `tests/run_all.sh` 沒有被改；`tests/pitfalls_format_test.sh` 仍被 run_all 自動列入（run_all 吃所有 `*.sh`）。若環境無法執行 run_all，改在 `ledger.md` 以讀 `tests/run_all.sh` 開頭註解（「files are every *.sh in this directory except run_all.sh」）為證 | 手動：閱卷者執行或讀 `ledger.md` |
