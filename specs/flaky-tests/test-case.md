# 測試案例：七支隨機紅或本身有誤的測試改成確定性（flaky-tests）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
Reader: the maintainer, who is not an engineer.
-->

**規格**：`specs/flaky-tests/plan.md`（A 級任務，沒有獨立的 spec.md；計畫的「目標」「作法 1–7」「失敗先行測試」「完成標準」「不做」「裁決」「裁決二」即為需求）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，做到了。
- **例外**：出錯、被模擬壞掉、或有人想放寬時，系統怎麼反應。
- **不在範圍**：計畫明講不做的事；確認它真的沒做。

這件事的特殊之處：沒有新功能，整件事是「測試本身要變穩，而且不能變鬆」。所以每支測試各有「改前會紅」與「改後穩定」兩種證據，另有「沒有放寬、沒有跳過、沒有動不該動的檔」的核對。

驗證方式說明：「自動」＝有測試檔會實際跑並用結果判定；「手動」＝閱卷者讀 diff，或重跑 `specs/flaky-tests/ledger.md` 裡貼的指令來核對（步驟即計畫的「失敗先行測試」與「完成標準」）。

維護者原話（取自計畫「維護者原話」，審查報告 2026-10-24）與對應 TC：

- 「修 6 支隨機紅測試……先用 flakefinder／連跑 20 次證明會紅，修完再連跑 20 次證明不紅。」→ 每支各一條「改前會紅」與「改後穩定」：TC-009／010、TC-017／018、TC-026／027、TC-034／035／036、TC-044～047／055／056。
- 「修 `hosted_deploy_test.sh` TC-059（拿 `origin/v3` 比 diff，合併後必紅）」→ TC-060、TC-065～068。
- 「放寬『等待上限』而不是放寬斷言」→ TC-015、TC-020～023、TC-082。

## US1 — test_r30_r36：頁面上的隨機十六進位字串不再誤判成 f1（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 1；失敗先行測試 | 功能 | 新增測試 `test_r30_r36_a_hex_token_holding_f1_cannot_trip_the_marker`。測試用 monkeypatch 把頁面實際用的按鈕隨機碼來源（`confirm.py` 的 `secrets.token_hex`）固定成含 f1 的字串，例如 `"f1" * 16` | 渲染 `?run=<l1>` 的右欄 | 測試確認「舊式 `"f1" not in 右欄`」在這個條件下是**假**（證明隨機碼真的被放進頁面、舊寫法必紅） | 自動：`platform/tests/test_web_running.py::test_r30_r36_a_hex_token_holding_f1_cannot_trip_the_marker` |
| TC-002 | 作法 1；失敗先行測試 | 功能 | 同 TC-001 的強制條件 | 同一個測試再跑新的精確禁止項檢查 | 新檢查為真（右欄沒有 f1 這個 run 的任何東西），整支測試綠，不因隨機碼含 f1 而紅 | 自動：同上 |
| TC-003 | 作法 1(a) | 功能 | `test_r30_r36_attention_card_uses_the_component` 改完 | 對 `pane(c.get("/?run=" + b).text, "right")` 用 `(?<![0-9A-Za-z])f1(?![0-9A-Za-z])` 做 `re.search` | 沒有符合；原本第 152 行對整頁做兩字元子字串比對的寫法已不存在 | 自動：`platform/tests/test_web_running.py::test_r30_r36_attention_card_uses_the_component` |
| TC-004 | 作法 1(b) | 功能 | 同上 | 對同一個右欄檢查四個 f1 獨有內容 | 右欄不含：`id-f1`、`samplesheet is missing the reverseReads column`、`FASTQC (sample2)`、`TRIMGALORE (sample3)`（四項各自被斷言） | 自動：同上 |
| TC-005 | 作法 1 | 功能 | 同上 | 看 `?run=<l1>` 的通知數 | 仍斷言 `len(notices(...)) == 1`（原本前半不刪） | 自動：同上 |
| TC-006 | 作法 1(a) | 例外 | 右欄真的出現 f1 這個 run 的內容，例如 run id `id-f1`（前面是 `-`） | 用 TC-003 的詞界正規式去找 | 仍會比對到（只有被英數字包住的才不算詞），也就是真正的洩漏仍會被抓到；ledger 貼一次直接驗證的指令與輸出 | 手動：閱卷者讀正規式並重跑 ledger 的驗證指令 |
| TC-007 | 作法 1 | 不在範圍 | 第 14 行 `"l1"/"u1"/"s1" not in right` | 比對 diff | 該行沒有改；ledger 有一句說明為什麼不改（l、u、s 不是十六進位字元，不可能出現在隨機碼裡） | 手動：閱卷者讀 diff 與 ledger |
| TC-008 | 範圍；裁決二 4 | 不在範圍 | `test_web_running.py` 由前端 session 擁有 | 看 `git diff` 這個檔 | 只動 `test_r30_r36_attention_card_uses_the_component` 一個函式並新增一支測試，其他函式一個字都沒改 | 手動：閱卷者讀 diff |
| TC-009 | 失敗先行測試；完成標準 1 | 功能 | 舊的斷言 | 在 TC-001 的強制條件下用舊式斷言跑 | ledger 有指令與輸出，證明舊寫法在這個條件下會紅（改前紅） | 手動：閱卷者重跑 ledger 指令 |
| TC-010 | 完成標準 2 | 功能 | 修好之後 | 逐次（不並行）連跑 20 次三支便宜測試的指令，其中含此測試 | 20 次全綠；ledger 貼次數與結果 | 手動：閱卷者重跑 `platform/tests/test_web_running.py::test_r30_r36_attention_card_uses_the_component` 並核對 ledger |

## US2 — test_station_e2e 的 `scenario_life`（platform_clock_test.sh 的一半）：時間邊界不再太窄（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-011 | 作法 2(d) | 功能 | agent 剛上線的第一次檢視（約第 590–596 行） | 先讀出最後一次聯絡時間 `last_seen_at`，再用 `ABF_PLATFORM_CLOCK_OFFSET` 把「現在」釘在最後一次聯絡後 2 秒去問 `list_agents` | 狀態仍是 `online`；對 `last_contact_at` 的上下界斷言原樣保留 | 自動：`platform/tests/test_station_e2e.py`（scenario_life） |
| TC-012 | 作法 2(a)(b) | 功能 | agent 被 SIGKILL 殺掉，睡完 `POLL + 1` 秒（這一睡保留） | 用 `plat.db_rows("SELECT last_seen_at FROM agents")` 讀出 `last`，再以 `ABF_PLATFORM_CLOCK_OFFSET=last + 2 - time.time()` 問 `list_agents` | 斷言仍是 `status == "online"`，訊息「offline is decided by the clock, not by a broken connection」保留；斷線不等於離線 | 自動：同上 |
| TC-013 | 作法 2(c) | 功能 | 同 TC-012 | 用 `3 * H + 5` 的偏移問 `list_agents` | 該檢視是 `offline`，且 `last_contact_at` 與 TC-012 看到的相同；這一段沒被改 | 自動：同上 |
| TC-014 | 作法 2(d) | 功能 | agent 以同名重新連上 | 重新連上後的檢視同樣先讀 `last_seen_at`、偏移釘在 +2 秒 | 仍是 1 個 agent、狀態 `online`，`last_contact_at` 比 `first_contact` 晚 | 自動：同上 |
| TC-015 | 作法 2(e)；維護者原話 c1 | 功能 | 等待 agent 重新連上的輪詢迴圈 | 看等待上限與結束條件 | 上限由 15 秒改為 60 秒；仍是輪詢到條件成立就結束（不是固定睡 60 秒）；條件 `last_seen_at > first_contact + 0.5` 原樣不變 | 手動：閱卷者讀 diff |
| TC-016 | 作法 2；範圍 | 不在範圍 | 比對 diff | 看 `test_station_e2e.py` 的改動範圍 | 只動 `scenario_life`（約第 580–618 行）；`H`、`POLL`、`FAST`、`POLL + 1` 那一睡、`3 * H + 5`、其他三個場景與 fixture 都沒改；沒有用「加大心跳或加長 sleep」代替 | 手動：閱卷者讀 diff |
| TC-017 | 失敗先行測試 | 功能 | 一個不提交的暫存副本，在 `now_view` 前插入 `time.sleep(4)`（模擬子程序啟動慢） | 舊寫法跑一次、新寫法跑一次 | 舊寫法紅（3＋4 超過 6 秒），新寫法仍綠；指令與結果貼在 ledger，插入的那行不進 commit | 手動：閱卷者重跑 ledger 指令 |
| TC-018 | 完成標準 3 | 功能 | 修好之後 | `test_station_e2e.py` 整檔逐次連跑 5 次（四個場景一起跑，不能只挑一個） | 5 次全綠；ledger 貼次數與結果 | 自動：`platform/tests/test_station_e2e.py` |
| TC-019 | 完成標準 3 | 功能 | 修好之後 | 同時開 4 份：`for k in 1 2 3 4; do pytest tests/test_station_e2e.py -q & done; wait` | 4 份全綠 | 自動：`platform/tests/test_station_e2e.py` |

## US3 — test_nextflow_e2e：用「等事件發生」取代固定睡眠（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-020 | 作法 3（第 62 行） | 功能 | 三個 run 結束後原本固定睡 1.5 秒才問 receiver | 改成 `wait_until`，等三個 run 的狀態（`_runs_via_mcp` 看 `status`）都已是最終狀態，上限 30 秒 | 固定睡眠已移除；後面的斷言一個字不改；測試綠 | 自動：`platform/tests/test_nextflow_e2e.py`（本機沒有 Java 與 Nextflow 時，交 CI 的 `tests/platform_clock_test.sh`） |
| TC-021 | 作法 3（第 153 行） | 功能 | `proc.wait` 後原本固定睡 1.5 秒才讀 `final["status"]` | 改成 `wait_until` 等 `status == "succeeded"`，上限 30 秒 | 睡眠移除；第 155–156 行原斷言不動；測試綠 | 自動：同上 |
| TC-022 | 作法 3（第 189 行） | 功能 | 原本固定睡 1.0 秒才讀 `env.recorder.of_kind("begin")` | 改成 `wait_until` 等該清單非空，上限 30 秒 | 睡眠移除；第 191 行原斷言不動；測試綠 | 自動：同上 |
| TC-023 | 作法 3（第 467 行） | 功能 | 原本固定睡 1.0 秒才回傳 log；executor 先讀呼叫端（第 460–468 行之後誰用這份 log） | 若呼叫端只讀 log 檔：睡眠直接移除；若讀 receiver 狀態：改成 `wait_until` 等該事實 | 兩種做法擇一，ledger 寫明是哪一種與理由；沒有留下固定睡眠；測試綠 | 自動：同 TC-020；理由由閱卷者讀 ledger |
| TC-024 | 作法 3 | 不在範圍 | 第 411 行（睡 1.2 秒再殺）、第 414 行（SIGKILL 後睡 1.0 秒）是刻意的時間窗；第 81 行、第 246–248 行、第 435 行的容差（`+2`、`_CLOCK_SLACK_SECONDS = 3`、`<= 1`）是斷言本身 | 比對 diff | 這些全部沒改 | 手動：閱卷者讀 diff |
| TC-025 | 作法 3；不做 | 不在範圍 | 比對 diff | 看 `tests/platform_clock_test.sh`、`tests/platform_test.sh`、`tests/run_all.sh` | 三個檔一個字都沒改（包含 `run_all.sh` 的逾時上限） | 手動：閱卷者讀 diff |
| TC-026 | 失敗先行測試 | 功能 | 暫存副本，把被改掉的那些 `time.sleep(n)` 改成 `time.sleep(0)` | 舊寫法跑、新寫法（`wait_until`）跑 | 舊寫法因為事件還沒到而紅（證明睡眠是承重的競態），新寫法仍綠；指令與結果貼 ledger | 手動：閱卷者重跑 ledger 指令（需要 Java 與 Nextflow，沒有則 ledger 註明交 CI） |
| TC-027 | 完成標準 3 | 功能 | 修好之後 | `test_nextflow_e2e.py` 整檔連跑 3 次；本機沒有 Java 與 Nextflow 時 ledger 寫明「本機沒有、交 CI」 | 3 次全綠；或有該句說明且 CI 的 `platform_clock_test.sh` 綠 | 自動：`platform/tests/test_nextflow_e2e.py` |
| TC-028 | 作法 3 末段 | 功能 | 修好之後 | 執行一次 `time bash tests/platform_clock_test.sh` | ledger 記下秒數 | 手動：閱卷者核對 ledger |
| TC-029 | 裁決二 2；待裁決 2 | 例外 | 上一條量到的秒數超過約 200 秒（若沒超過，此條不觸發，閱卷標「不適用」） | 看 executor 怎麼處理 | 不調高 `run_all.sh` 的逾時上限，回報 BLOCKED 交 developer-agent 另開拆分任務 | 手動：閱卷者核對 ledger 與 executor 回報 |

## US4 — constitution_scope_test.sh：外層與內層讀同一份輸入（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-030 | 作法 4(a) | 功能 | 工作樹有「尚未提交的文件或 hook 修改」 | `mkclone` 建出暫存複本後 | 外層讀過的 `docs/`、`hooks/`、`.specify/`、`CLAUDE.md`、`README.md`、`CONTEXT.md` 都從工作樹蓋進複本，內層 TC-002 與外層讀同一份輸入，不再因未提交修改而 `rc=1` | 自動：`tests/constitution_scope_test.sh` |
| TC-031 | 作法 4(a) | 功能 | 看 `mkclone` 的寫法 | 找複製檔案的指令 | 用 `cp -R`，不依賴 rsync | 手動：閱卷者讀 diff |
| TC-032 | 作法 4(b) | 功能 | `git clone` 那一行 | 看 stderr 的去向 | stderr 存到 `$SCR/clone.err`，不再 `>/dev/null 2>&1` 吞掉 | 手動：閱卷者讀 diff |
| TC-033 | 作法 4(b) | 例外 | 暫存複本的 `git clone` 失敗 | 看失敗訊息 | 訊息（`bad`）帶出 `clone.err` 的內容，不再只剩一行沒原因的 `scratch shallow clone` | 手動：閱卷者讀 diff；可用讓 clone 失敗的方式在暫存副本驗證 |
| TC-034 | 失敗先行測試；作法 4 | 功能 | 暫存複本（`git clone --no-local file://<repo>`）：提交一個把 `docs/SITE_ADAPTER.md` 的 `Constitution 2.0.0` 拿掉的 commit，再把工作樹那份還原不提交 | 跑**舊**腳本 | 外層全綠，內層出現 `TC-002 … FAIL: rc=1`（改前紅）；指令與輸出貼 ledger | 手動：閱卷者重跑 ledger 指令 |
| TC-035 | 失敗先行測試；作法 4 | 功能 | 同 TC-034 的暫存複本 | 跑**新**腳本 | 全綠，沒有任何 FAIL | 自動：`tests/constitution_scope_test.sh` |
| TC-036 | 完成標準 3 | 功能 | 修好之後 | `bash tests/constitution_scope_test.sh` 逐次連跑 5 次 | 5 次全綠；ledger 貼次數與結果 | 自動：`tests/constitution_scope_test.sh` |
| TC-037 | 作法 4(c)(d) | 不在範圍 | 比對 diff | 看其餘斷言 | TC-002 的「fingerprint 那行是 ok」「沒有 skip 字樣」，以及 TC-003／004／006／007／008／009、`PINNED_SN_SHA256`、所有 `has`／`hasnt` 的檢查字串，一個字都沒改 | 手動：閱卷者讀 diff |
| TC-038 | 失敗先行測試 | 不在範圍 | 重現步驟（提交拿掉字串的 commit） | 看腳本 | 重現步驟只貼在 ledger，沒有被新增進 `tests/constitution_scope_test.sh` | 手動：閱卷者讀 diff |

## US5 — test_tc087 與 test_tc071：只收緊，查不到原因就照實說（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 作法 5b | 功能 | `test_tc087_nothing_keeps_a_process_alive_or_reopens_a_connection` | 看 `git ls-files` 的結果處理 | 回傳碼必須是 0 且清單非空，否則斷言失敗並印出 stderr | 自動：`platform/tests/test_station_static.py::test_tc087_nothing_keeps_a_process_alive_or_reopens_a_connection` |
| TC-041 | 作法 5b | 功能 | `test_tc071_no_submission_no_resident_loop_no_committed_database` | 看 `git ls-files` 的結果處理 | 同 TC-040：回傳碼 0 且清單非空，否則失敗並印 stderr | 自動：`platform/tests/test_scope.py::test_tc071_no_submission_no_resident_loop_no_committed_database` |
| TC-042 | 作法 5b；失敗先行測試 | 例外 | 暫存副本的 `PATH` 裡放一個永遠 exit 1 的 `git` | 跑 tc087 | 變紅（舊寫法會空洞通過） | 手動：閱卷者重跑 ledger 指令 |
| TC-043 | 作法 5b；失敗先行測試 | 例外 | 同 TC-042 | 跑 tc071 | 變紅（舊寫法會空洞通過） | 手動：閱卷者重跑 ledger 指令 |
| TC-044 | 作法 5b；失敗先行測試 | 功能 | 暫存複本 `git add` 一個空的 `x.service` | 跑 tc087 | 紅；失敗訊息只列違規路徑（`x.service`）加 `git status --porcelain` 的前 20 行，不再把整份 tracked 清單當訊息 | 手動：閱卷者重跑 ledger 指令 |
| TC-045 | 失敗先行測試 | 功能 | 上一條之後 `rm x.service` 並 `git reset` | 跑 tc087 | 綠 | 手動：閱卷者重跑 ledger 指令 |
| TC-046 | 作法 5b；失敗先行測試 | 功能 | 暫存複本 `git add` 一個空的 `x.db` | 跑 tc071 | 紅；失敗訊息只列違規路徑（`x.db`）加 `git status --porcelain` 的前 20 行 | 手動：閱卷者重跑 ledger 指令 |
| TC-047 | 失敗先行測試 | 功能 | 上一條之後 `rm x.db` 並 `git reset` | 跑 tc071 | 綠 | 手動：閱卷者重跑 ledger 指令 |
| TC-048 | 作法 5c | 功能 | tc071 掃描 `platform/` 底下磁碟上的 sqlite／-wal／-shm／-journal 檔 | 看掃描迴圈 | 改成重掃到空為止：`deadline = time.time() + 15`、每 0.3 秒重掃，空了就過 | 自動：`platform/tests/test_scope.py::test_tc071_no_submission_no_resident_loop_no_committed_database` |
| TC-049 | 作法 5c | 例外 | `platform/` 裡有一個永久遺留的旁檔（例如 `x.sqlite-wal`）不會消失 | 跑 tc071 | 約 15 秒後仍紅，訊息列出該檔名（不是放寬：永久遺留的檔照樣紅） | 手動：閱卷者重跑 ledger 指令 |
| TC-050 | 作法 5c | 功能 | 旁檔在測試執行期間的幾秒內被刪掉（模擬短暫的連線旁檔） | 跑 tc071 | 通過，不誤報 | 手動：閱卷者重跑 ledger 指令 |
| TC-051 | 作法 5a、5f；裁決 5 | 功能 | ledger | 看抓證據的紀錄 | 有「每 0.2 秒掃旁檔」的觀察迴圈輸出與連跑 20 次的每次失敗訊息；若完全抓不到，ledger 明講「查不到原因」並指向待裁決 3；不要求猜一個原因 | 手動：閱卷者核對 ledger |
| TC-052 | 作法 5d；裁決二 3 | 不在範圍 | 抓到某個測試把檔案寫進 `platform/`（不是 `tmp_path`） | 看 diff | 沒有去修那支測試的隔離問題；只記在 ledger／待裁決 3 另案（沒抓到則此條標「不適用」） | 手動：閱卷者讀 diff 與 ledger |
| TC-053 | 作法 5e | 不在範圍 | 抓到的是別的程序把 `.service`／`.timer` `git add` 進同一棵樹 | 看 diff | 不改行為，只做訊息改善，ledger 寫明「測試正確反應索引狀態」（沒抓到則標「不適用」） | 手動：閱卷者讀 diff 與 ledger |
| TC-054 | 範圍；不做 | 不在範圍 | `_all_platform_files`（`test_scope.py`） | 看簽章與 `test_station_static.py` 第 92 行的 import | 簽章沒變，import 仍可用 | 自動：`platform/tests/test_station_static.py` 與 `platform/tests/test_scope.py` 整檔可載入並通過 |
| TC-055 | 完成標準 2 | 功能 | 修好之後 | 逐次連跑 20 次三支便宜測試的指令 | tc087 在 20 次中全綠；ledger 貼次數與結果 | 自動：`platform/tests/test_station_static.py::test_tc087_nothing_keeps_a_process_alive_or_reopens_a_connection` |
| TC-056 | 完成標準 2 | 功能 | 同上 | 同一個 20 次迴圈 | tc071 在 20 次中全綠；ledger 貼次數與結果 | 自動：`platform/tests/test_scope.py::test_tc071_no_submission_no_resident_loop_no_committed_database` |

## US6 — hosted_deploy_test.sh TC-059：不再拿 base 分支當基準（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 作法 7；完成標準 5 | 功能 | 修好的 `tests/hosted_deploy_test.sh` | `sed -n '/TC-059/,/TC-062/p' tests/hosted_deploy_test.sh \| grep -nE 'git\|origin/\|skip'` | 沒有任何輸出（TC-059 區塊不含 `git`、`origin/`、`skip`） | 手動：閱卷者重跑該指令 |
| TC-061 | 作法 7 | 功能 | `docs/INSTALL.md` 現況 | 取出含 `Hosting one lab` 的行 | 斷言至少 1 行、至多 6 行（原斷言 `nadd <= 6` 的 6 不變） | 自動：`tests/hosted_deploy_test.sh` |
| TC-062 | 作法 7 | 功能 | 同上 | 檢查這些行 | 沒有任何一行以 `#` 開頭（原斷言「沒有新 `##`」） | 自動：`tests/hosted_deploy_test.sh` |
| TC-063 | 作法 7 | 功能 | 同上 | 檢查這些行裡反引號包住的詞 | 沒有 snake_case（沿用原樣式 `` `[^`]*` `` 與 `[a-z]+_[a-z_]+`） | 自動：`tests/hosted_deploy_test.sh` |
| TC-064 | 作法 7 | 功能 | `docs/INSTALL.md` | 數 `## ` 標題 | 仍斷言剛好 6 個，該斷言保留 | 自動：`tests/hosted_deploy_test.sh` |
| TC-065 | 失敗先行測試 | 功能 | `73578cd` 上的**舊**腳本 | 執行 | 出現 `TC-059 INSTALL.md pointer FAIL: added 0 lines`（改前紅）；ledger 貼指令與輸出 | 手動：閱卷者重跑 ledger 指令 |
| TC-066 | 失敗先行測試 | 功能 | 同一個 commit 上的**新**腳本 | 執行 | TC-059 的兩行輸出都是 `ok` | 自動：`tests/hosted_deploy_test.sh` |
| TC-067 | 失敗先行測試；作法 7 | 功能 | 暫存複本模擬淺層、沒有 `origin/v3`（`git branch -rd origin/v3` 或 `--depth 1` clone） | 跑新腳本 | TC-059 的兩行仍是 `ok`（舊腳本在這裡是 `skip`） | 手動：閱卷者重跑 ledger 指令 |
| TC-068 | 完成標準 2 | 功能 | 修好之後 | 逐次連跑 20 次 `bash tests/hosted_deploy_test.sh \| grep -E 'TC-059'` | 20 次的兩行 TC-059 都是 `ok`；ledger 貼次數與結果 | 自動：`tests/hosted_deploy_test.sh` |
| TC-069 | 裁決二 1；待裁決 1 | 功能 | `tests/hosted_deploy_test.sh` | 搜尋 `TC-066` | 整個 TC-066 區塊（約第 284–292 行，含 skip 分支）已移除；ledger 與 PR 說明寫有刪除理由與實測結果（在 `73578cd` 上 `TC-066 gate files touched FAIL: platform/abf_platform/web_board.py`）；範圍證據改由 ledger 的 `git diff --stat` 供閱卷核對 | 手動：閱卷者 `grep -n 'TC-066' tests/hosted_deploy_test.sh`（無輸出）並讀 ledger |
| TC-070 | 作法 7；不做 | 不在範圍 | 比對 diff | 看 verifier CONTRACT 規則相關檔案 | 本任務沒有修改任何 verifier 規則（「測試不得以 base 分支當比較基準」那半句不在本任務） | 手動：閱卷者讀 diff |
| TC-071 | 環境事實 | 不在範圍 | 本機 Windows Git Bash 上 TC-034／035／036／041／042 會因環境而紅 | 比對 diff | 這些 TC 與 `hosted_deploy_test.sh` 其他部分都沒被改（只動 TC-059 與刪 TC-066） | 手動：閱卷者讀 diff |

## US7 — 整體界線：只更嚴、不放寬、只動範圍內的檔（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-080 | 完成標準 6；範圍：檔案 | 功能 | 修好之後 | 閱卷者自己重跑 `git diff --stat <base>...HEAD` | 只列計畫「範圍：檔案」的 7 個測試檔加 `specs/flaky-tests/ledger.md`；ledger 內也貼有這份輸出 | 手動：閱卷者重跑 |
| TC-081 | 完成標準 6；不做 | 例外 | 修好之後 | `git diff \| grep -nE '^\+.*(skip\|xfail\|flaky\|retry\|rerun)'` | 無輸出；若有英文註解的敘述性用法，ledger 逐一說明。沒有新增 skip／xfail／重試迴圈 | 手動：閱卷者重跑 |
| TC-082 | 通則；維護者原話 c1 | 例外 | 每個被動到的測試檔與 base 逐一比對 | 看斷言的比較對象 | 沒有任何斷言的比較值變鬆（可以更精確、更多）；唯一允許變動的是等待上限（TC-015、TC-020～023）；沒有把預期值改成配合新輸出 | 手動：閱卷者讀 diff |
| TC-083 | 通則；不做 | 例外 | 同上 | 看有沒有斷言被刪、被縮小檢查範圍 | 沒有刪除斷言、沒有縮小被檢查的範圍；唯一例外是裁決二 1 明列的 TC-066 區塊 | 手動：閱卷者讀 diff |
| TC-084 | 不做 | 不在範圍 | 比對 diff | 看 `ABF_SUITE_SLOTS`、`run_all.sh` 逾時 | 兩者都沒調（修完後由 developer-agent 自己放回 3） | 手動：閱卷者讀 diff |
| TC-085 | 不做；裁決 3 | 不在範圍 | 比對 diff | 看有沒有新工具或標記 | 沒有 `@pytest.mark.quarantine`，也沒有 flakefinder 之類的工具化；連跑只用 shell 迴圈 | 手動：閱卷者讀 diff |
| TC-086 | 完成標準 7 | 功能 | 修好之後 | 在 WSL／Linux 跑 `bash tests/run_all.sh`；並查完成記號 | 全套綠，且完成記號 `GREEN <HEAD sha>` 與 HEAD 相符、工作樹乾淨 | 自動：`tests/run_all.sh` |
| TC-087 | 完成標準 1 | 功能 | `specs/flaky-tests/ledger.md` | 對七項（test_r30_r36、scenario_life／platform_clock_test.sh、constitution_scope_test.sh、tc087、tc071、TC-059、並含 nextflow 睡眠）逐項查 | 每一項都有「改前紅」的指令與輸出、以及「改後穩定」的指令與輸出 | 手動：閱卷者讀 ledger 並抽重跑 |
| TC-088 | 範圍：不准動 | 不在範圍 | 比對 diff | 看禁區檔案 | 閘門檔（`spec.md`、`test-case*.md`、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`、`platform/pyproject.toml`）與其他任務正在動的檔案（`pipeline_launch.py` 等、`actions/*`、`platform/abf_launch/*`、`launch.py`、`handlers.py`、`hooks/*`、`skills/launch/*`、`scripts/launch_recheck.sh`、`docs/TESTING.md`、`test_gcb_ce.py`）一個字都沒改 | 手動：閱卷者讀 diff |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-090 | 專長守則（backend）：動作層、確認管道、擁有者規則、錯誤訊息、密鑰；計畫「不做」 | 不在範圍 | 比對 diff | 看 `platform/abf_platform/` 與 `platform/abf_station/` | 底下任何檔案都沒改，所以沒有新的寫入路徑、沒有繞過確認、沒有跨使用者讀寫、沒有新的錯誤訊息或日誌輸出 | 手動：閱卷者讀 diff |
| TC-091 | 專長守則（backend）：migration | 不在範圍 | 比對 diff | 看是否有資料結構、schema 或 migration 檔 | 沒有任何資料結構或資料內容變動，因此不需要 migration | 手動：閱卷者讀 diff |
| TC-092 | 安全網（指紋固定值）；不做 | 不在範圍 | 比對 diff | 看 `PINNED_SN_SHA256` 與憲法檔 | `PINNED_SN_SHA256` 與 `.specify/memory/constitution.md` 都沒改，安全網的指紋檢查沒被動過 | 手動：閱卷者讀 diff；`tests/constitution_scope_test.sh` 仍綠 |
| TC-093 | 原則 2（沒有提交、沒有常駐迴圈、沒有已提交的資料庫），檢查名 tc071 | 不在範圍 | `test_tc071…` 前半的禁止樣式清單與原始碼掃描 | 比對 diff | 前半（`nextflow run`、`sbatch`、`while True`、threading、subprocess 等五組樣式的掃描）一個字沒改，沒有被縮小 | 手動：閱卷者讀 diff |
| TC-094 | 靜態檢查名 tc087（沒有常駐程序、沒有重開連線） | 不在範圍 | `test_tc087…` 最後一行 `hits(station_sources(), [ControlMaster, ControlPersist, ssh -, ssh_control])` | 比對 diff | 這一行沒改，檢查範圍沒縮小 | 手動：閱卷者讀 diff |

<!--
Rules for the writer:
- Every requirement and example in the plan maps to at least one TC. IDs are never renumbered after approval.
-->
