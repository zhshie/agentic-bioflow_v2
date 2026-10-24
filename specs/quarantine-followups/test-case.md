# 測試案例：隔離名單補強（首次隔離日、固定「今天」、重跑乾淨暫存）

**規格**：`specs/quarantine-followups/plan.md`（本任務沒有獨立的 spec.md，計畫即規格，維護者原話引用自計畫「維護者原話」一節）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：規格說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：規格明講這次不做的事；測試確認它真的沒做。

名詞（一句話）：
- **隔離名單**：`tests/quarantine.txt`，列出「偶發失敗、暫時先放行」的測試檔，每條是借來的時間，不是修好。
- **since**：新加的第四欄，「這個檔第一次被隔離的日期」。
- **墊片（shim）**：測試在自己的暫存沙盒裡放的一個假 `date` 程式，只讓被測的 runner 看到固定的「今天」；正式 CI 與本機跑的 runner 沒有任何覆蓋點。
- **runner**：`tests/run_all.sh`，跑全部測試的總程式。
- **重跑**：`--retry-failed-once`，第一輪失敗的測試檔再跑一次。
- 以下「今天」一律指測試啟動時固定的那一天（墊片提供）；「今天+N」「今天−N」是它前後 N 天。名單一行的寫法為 `tests/<檔名>.sh <issue> <到期> <since>`。
- 自動案例都寫在 `tests/run_all_retry_test.sh`，每條在測試裡以註解標出 TC 編號。

維護者原話（來自 `ci-quarantine` 已核可的「1-3按照你的建議」與計畫引用的 `memory/dev-plans/ci-quarantine.md`）與對應：
- 「每條有 issue 與 ≤14 天到期」「名單到期自動變紅」→ US1（TC-104～TC-110b）。
- 「沒有 RUN_ALL_TODAY 之類的後門」→ US2（TC-120）與既有 TC-090a／b／c。
- 「重跑才綠的檔不得悄悄併進 passed」「重跑只一次」→ US3（TC-130～TC-138）。

## User Story 1 — 名單每條記「首次隔離日」，續期最多一次（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-101 | 作法一規則 1 | 例外 | 名單一行是舊的三欄格式：`tests/ok_test.sh #12 <今天+3>` | 執行 `--check-quarantine` | 結束碼 1；錯誤訊息含 `quarantine: tests/quarantine.txt:1:`、`found 3`，以及 `add the date this file was first quarantined`（舊格式有專屬提示，不是靜默放行） | 自動：`tests/run_all_retry_test.sh` |
| TC-102a | 作法一規則 3 | 例外 | 四欄，since 寫成 `2026-13-40`（不存在的日期） | 執行 `--check-quarantine` | 結束碼 1；訊息含該行行號 | 自動 |
| TC-102b | 作法一規則 3 | 例外 | 四欄，since 寫成 `not-a-date` | 執行 `--check-quarantine` | 結束碼 1；訊息含該行行號 | 自動 |
| TC-103 | 作法一規則 4 | 例外 | since＝今天+1，到期＝今天+3 | 執行 `--check-quarantine` | 結束碼 1；訊息含 `in the future` | 自動 |
| TC-104 | 作法一規則 2.1～2.7 | 功能 | since＝今天，到期＝今天+14（新格式的基本有效案例） | 執行 `--check-quarantine` | 結束碼 0 | 自動 |
| TC-105 | 作法一規則 7（上限當天） | 功能 | since＝今天−14，到期＝今天+14（剛好 since+28） | 執行 `--check-quarantine` | 結束碼 0 | 自動 |
| TC-106 | 作法一規則 7 | 功能 | since＝今天−15，到期＝今天+13（剛好 since+28） | 執行 `--check-quarantine` | 結束碼 0 | 自動 |
| TC-107 | 作法一規則 7 | 例外 | since＝今天−15，到期＝今天+14（since+29，多一天） | 執行 `--check-quarantine` | 結束碼 1；訊息含 `28 days` 與那個 since 日期 | 自動 |
| TC-107b | 作法一規則 7（印出距今幾天） | 例外 | 同 TC-107（since＝今天−15） | 執行 `--check-quarantine` | 訊息裡除了 since 日期，還印出「距今」天數 15 | 自動 |
| TC-108a | 作法一規則 5、7（續期繞道，最後一天） | 功能 | since＝今天−28，到期＝今天 | 執行 `--check-quarantine` | 結束碼 0 | 自動 |
| TC-108b | 作法一規則 7（續期繞道） | 例外 | since＝今天−29，到期＝今天 | 執行 `--check-quarantine` | 結束碼 1；訊息含 `28 days`（每兩週改一次到期日就永久隔離的做法被擋下） | 自動 |
| TC-109 | 作法一規則順序（5 先於 7） | 例外 | since＝今天−40，到期＝今天−1（已過期，since 又很舊） | 執行 `--check-quarantine` | 結束碼 1；訊息含 `expired`，且不含 `28 days`（先報過期） | 自動 |
| TC-110 | 作法一規則 6（先於規則 7） | 例外 | since＝今天，到期＝今天+15 | 執行 `--check-quarantine` | 結束碼 1；訊息含 `14 days` | 自動 |
| TC-110b | 不做：不調整 14 天每期上限 | 不在範圍 | since＝今天−10，到期＝今天+15（since+28 本來允許，但離今天超過 14 天） | 執行 `--check-quarantine` | 結束碼 1；訊息含 `14 days`（每期上限 14 天沒有被放寬或取代） | 自動 |
| TC-111 | 作法一第 5 點（QUAR 仍是三欄） | 功能 | 一條有效的四欄行，已登記的測試檔第一輪失敗、重跑才綠；到期與 since 故意取不同日（例：到期＝今天+9，since＝今天−5） | 以 `--retry-failed-once` 執行 | 輸出的 FLAKY 行是 `quarantined #12 until <到期日>`，印的是到期日，不是 since | 自動 |
| TC-112a | 作法一、既有 TC-050 的做法 | 功能 | 四欄的有效名單 | 執行 `--check-quarantine` | 結束碼 0，沙盒內沒有執行任何測試檔 | 自動 |
| TC-112b | 作法一、既有 TC-051 的做法 | 例外 | 四欄但無效的名單 | 執行 `--check-quarantine` | 結束碼 1，沙盒內沒有執行任何測試檔 | 自動 |
| TC-113 | 作法一第 6 點(a) | 功能 | 真實的 `tests/quarantine.txt` | 讀檔頭 | 檔頭含 `since` 字樣與四欄格式那一行（`tests/<name>.sh <issue> <expiry YYYY-MM-DD> <since YYYY-MM-DD>`）；且仍然沒有任何有效條目（接在既有 TC-057 之後） | 自動 |
| TC-113b | 作法一第 6 點(b) | 功能 | 同上 | 讀檔頭 | 有 since 的白話定義，含「第一次隔離這個檔的日期；續期時不要改它」的意思 | 自動 |
| TC-113c | 作法一第 6 點(c) | 功能 | 同上 | 讀檔頭 | 有一句規則：每期最多 14 天、從 since 起總共最多 28 天、只能續一次 | 自動 |
| TC-113d | 作法一第 6 點(d) | 功能 | 同上 | 讀檔頭 | 不再出現舊句 `expiry at most 14 days from the day it is checked` | 自動 |
| TC-113e | 作法一第 7 點（誠實的限制） | 功能 | 同上 | 讀檔頭 | 檔頭明說 since 是人填的、機器無法證明它沒被改，改成今天等於換一種續期 | 自動 |
| TC-114a | 作法一第 6 點（usage 同步） | 功能 | 真實 runner | 執行 `--help` | 輸出含 `first-quarantined` | 自動 |
| TC-114b | 作法一第 6 點（usage 同步） | 功能 | 真實 runner | 執行 `--help` | 輸出含 `--retry-failed-once` | 自動 |
| TC-115 | 不做：不從 git 歷史驗證 since | 不在範圍 | 沙盒 `PATH` 上放一個假 `git`（被呼叫就寫標記檔），名單為有效四欄 | 執行 `--check-quarantine` | 結束碼 0，且假 `git` 的標記檔不存在（runner 沒有去查 git 歷史） | 自動 |

## User Story 2 — 測試的「今天」固定成一次，runner 沒有覆蓋點（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-120 | 作法二第 9、10 點；維護者原話「沒有 RUN_ALL_TODAY 之類的後門」 | 不在範圍 | `tests/run_all.sh` 原始檔 | 靜態檢查 | `date -u` 在全檔只出現一次；全檔沒有 `RUN_ALL_TODAY`，也沒有以 `TODAY=` 賦值的讀取（沒有任何環境變數、旗標、隱藏參數可以覆蓋今天） | 自動 |
| TC-121a | 作法二（墊片生效、跨月） | 功能 | 墊片日期設為 `2030-02-28`；到期＝`2030-03-14`（+14），since＝`2030-02-28` | 執行 `--check-quarantine` | 結束碼 0（結果與真實今天無關） | 自動 |
| TC-121b | 作法二（墊片生效、跨月） | 例外 | 墊片日期 `2030-02-28`；到期＝`2030-03-15`（+15） | 執行 `--check-quarantine` | 結束碼 1；訊息含 `14 days` | 自動 |
| TC-122a | 作法二（閏年） | 功能 | 墊片日期 `2028-02-27`；到期＝`2028-03-12`（+14，中間經過 2/29） | 執行 `--check-quarantine` | 結束碼 0 | 自動 |
| TC-122b | 作法二（閏年） | 例外 | 墊片日期 `2028-02-27`；到期＝`2028-03-13`（+15） | 執行 `--check-quarantine` | 結束碼 1 | 自動 |
| TC-123a | 作法二（午夜前一天、跨年） | 功能 | 墊片日期 `2026-12-31`；since＝`2026-12-31`，到期＝`2027-01-14` | 執行 `--check-quarantine` | 結束碼 0 | 自動 |
| TC-123b | 作法二（跨年） | 例外 | 墊片日期 `2026-12-31`；since＝`2026-12-31`，到期＝`2027-01-15` | 執行 `--check-quarantine` | 結束碼 1 | 自動 |
| TC-124 | 作法二第 11 點（哨兵）；既有 TC-055 | 例外 | 沙盒內的 runner 副本，把 `quarantine_check` 裡的 `date -u +%F` 換成 `date +%F`；名單為有效四欄 | 執行 `--check-quarantine` | 結束碼 1（runner 一旦忘了 `-u` 就確定變紅，不是碰運氣） | 自動 |
| TC-125 | 作法二第 11 點（`-d`） | 例外 | 墊片已安裝 | 直接呼叫墊片 `date -d tomorrow` | 結束碼 1，且標記檔 `$TMP/date-rel-called` 存在 | 自動 |
| TC-126 | 作法二第 12 點 | 功能 | 測試檔的日期輔助函式 `n2d` | 測試檔啟動時自檢 | 對固定已知值：`n2d 0` ＝ `1970-01-01`，`n2d 19723` ＝ `2024-01-01`；不再拿 `n2d` 跟另一次 `date` 呼叫比 | 自動 |
| TC-127 | 作法二第 11 點 | 功能 | 墊片已安裝，固定日為 `$TMP/today` 的內容 | 呼叫墊片 `date -u +%F` | 印出固定日期，結束碼 0 | 自動 |
| TC-128 | 作法二第 11 點 | 功能 | 墊片已安裝 | 呼叫墊片 `date +%F`（沒有 `-u`） | 印出哨兵日期 `1999-12-31` | 自動 |
| TC-129 | 作法二第 11 點 | 功能 | 墊片已安裝 | 呼叫墊片 `date -u +%s`（其他參數） | 交給真的 `date`，印出數字時間戳 | 自動 |
| TC-136 | 作法二第 13 點 | 功能 | 測試檔改動後的 diff | 閱卷看 diff | 「結束時發現日期變了就整份重跑」的保護與檔頭第 12–14 行的舊說明已刪除，改為「今天由 sandbox 內的 date 墊片固定，runner 沒有任何覆蓋點」 | 手動：閱卷看 `git diff`（見總覽「不確定」第 1 條） |
| TC-139 | 完成標準 3（午夜前後結果一致） | 功能 | 墊片日期固定為 `2026-12-31` | 整份 `bash tests/run_all_retry_test.sh` 分別在 `TZ=UTC-14` 與 `TZ=UTC+12` 下各跑一次 | 兩次都全綠，輸出的 ok／FAIL 行完全一致 | 自動：執行該測試檔，證據貼 ledger |

## User Story 3 — 重跑看不到第一次留下的暫存（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-130 | 作法三第 17 點；維護者原話「重跑要是乾淨的一次」 | 功能 | 測試檔：第一次在 `$TMPDIR/leftover` 留檔後 exit 1；第二次若 `$TMPDIR/leftover` 存在就 exit 1，否則 exit 0；已登記為 FLAKY | 以 `--retry-failed-once` 執行 | 結束碼 0；輸出含 `green after retry: 1` | 自動 |
| TC-131a | 作法三第 17 點 | 功能 | 測試檔把自己看到的 `$TMPDIR` 路徑記進計數檔 | 以 `--retry-failed-once` 執行 | 第一次記下的路徑＝沙盒傳進來的 `$TMPD` | 自動 |
| TC-131b | 作法三第 17 點 | 功能 | 同 TC-131a | 以 `--retry-failed-once` 執行 | 第二次記下的路徑≠`$TMPD`，且以 `<logs>/tmp.<檔名>.retry` 結尾 | 自動 |
| TC-132 | 作法三第 17 點（不刪失敗現場） | 功能 | 同 TC-130 的資料 | 執行結束後檢查 | 第一輪留下的 `$TMPD/leftover` 仍然存在（只是重跑看不到，沒有被刪） | 自動 |
| TC-133 | 作法三第 16 點（日誌本來就分開） | 功能 | 同 TC-130 的資料 | 執行結束後從輸出的 `logs:` 行取日誌目錄（直接讀原始輸出，因為 `normalize` 會刪該行） | `<檔名>.log` 與 `<檔名>.retry.log` 兩個檔都在，且內容不同 | 自動 |
| TC-134 | 不做：不改第一輪的 TMPDIR | 不在範圍 | 不帶 `--retry-failed-once`，測試檔失敗，且記下自己看到的 `$TMPDIR` | 執行 runner | 測試看到的 `$TMPDIR` 等於 `$TMPD`（第一輪沒有被換成每檔專用目錄，行為與今天相同） | 自動 |
| TC-135 | 作法三第 17 點（兩處：verbose 與靜默） | 功能 | 同 TC-130 的資料 | 加 `--verbose` 與 `--retry-failed-once` 執行 | 結束碼 0；輸出含 `green after retry: 1`（verbose 的重跑也走乾淨目錄） | 自動 |
| TC-137 | 作法三第 18 點 | 例外 | 沙盒讓重跑用的目錄 `tmp.<檔名>.retry` 建立失敗（例如 `PATH` 上放會失敗的假 `mkdir`） | 以 `--retry-failed-once` 執行 | 這次重跑記為失敗：結束碼非 0，輸出不含 `green after retry`；測試檔沒有改用共用的 `$TMPD` 重跑 | 自動 |
| TC-138 | 作法三第 19 點 | 功能 | 同 TC-130 的資料 | 以 `--retry-failed-once` 執行 | `retry <檔名> ... ok` 那一行文字不變、不含任何暫存目錄路徑 | 自動 |

## User Story 4 — 既有案例的改動（優先度 P1）

「斷言本身一字不改、只換資料格式」的案例（計畫逐條點名者）併為 TC-150。斷言有改的逐條列在下面。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-015 | 既有斷言改動：format hint | 功能 | 觸發「未登記的 FLAKY」提示 | 讀提示句 | 含 `tests/<name>.sh <issue> <expiry YYYY-MM-DD> <since YYYY-MM-DD>`（舊的 `(at most 14 days out)` 說法已換掉） | 自動 |
| TC-039 | 既有斷言改動：缺 issue 欄 | 例外 | 資料改為缺 issue 的四欄形式 `tests/ok_test.sh <到期> <今天>` | 執行 `--check-quarantine` | 結束碼 1，訊息帶行號前綴（斷言與舊版相同） | 自動 |
| TC-045 | 既有斷言改動：改名為 `TC-045 fifth column rejected` | 例外 | 資料 `tests/ok_test.sh #12 <到期> <since> extra`（第五欄） | 執行 `--check-quarantine` | 被拒（結束碼 1，帶行號） | 自動 |
| TC-084 | 既有斷言改動：尾端註解 | 功能 | 尾端 `# 註解` 接在第 4 欄之後（兩行資料與單行資料各一） | 執行 `--check-quarantine` | 與舊版斷言相同：註解被接受，名單有效 | 自動 |
| TC-055 | 既有案例：TZ 案例變確定 | 功能 | `TZ=UTC-14`、`TZ=UTC+12` 各一次，名單有效 | 執行 `--check-quarantine` | 斷言不變、全綠（不再靠真實時區碰運氣） | 自動 |
| TC-056 | 既有案例：墊片改為全域 | 功能 | 沒有 python3、相對日期呼叫會失敗，`PATH` 墊片目錄在 `EXTRAPATH` 之前 | 執行含 `sweep` 的案例 | 斷言不變：`neither python3 nor a relative date was used`；標記檔仍是 `$TMP/date-rel-called` | 自動 |
| TC-090a | 既有案例：`RUN_ALL_TODAY` 不是後門 | 不在範圍 | 環境設 `RUN_ALL_TODAY=2000-01-01`，名單換成四欄，到期今天+3 | 執行 `--check-quarantine` | 結束碼 0（該環境變數被完全忽略） | 自動 |
| TC-090b | 既有案例：同上 | 不在範圍 | `RUN_ALL_TODAY` 設定同上，名單 `tests/ok_test.sh #12 2000-01-05 2000-01-01` | 執行 `--check-quarantine` | 結束碼 1，訊息含 `expired`（驗證過期規則先於 28 天規則） | 自動 |
| TC-090c | 既有案例：同上 | 不在範圍 | 環境設 `RUN_ALL_TODAY=2099-01-01`，名單四欄，到期今天+3 | 執行 `--check-quarantine` | 結束碼 0 | 自動 |
| TC-150 | 既有斷言改動：只換資料格式 | 功能 | 計畫點名的案例（TC-016～021、025、027、029、030、031、034、036～038、040～044、046、047、050、051、053、054、079～082、086～089、091，與 TC-056 的兩個 `sweep`）名單行改用 `qline` 輔助函式帶 since 欄 | 閱卷比對與 base 的 diff，並執行整份測試檔 | 這些案例的斷言文字與 base 一字不差，只有資料格式不同；整份測試檔全部 ok | 自動：執行該測試檔；斷言比對由閱卷看 `git diff` |
| TC-151 | 作法二第 15 點；完成標準 4 | 功能 | 真實樹，既有 TC-052 不改 | 執行 `bash tests/run_all.sh --check-quarantine` | 結束碼 0（真實名單仍沒有有效條目） | 自動 |
| TC-152 | 完成標準 5 | 功能 | `tests/run_all_test.sh` 與 `tests/run_all_count_test.sh` | 閱卷看 diff 並各自執行 | 兩檔沒有任何改動，且全綠（不帶旗標的輸出與今天相同） | 自動：`tests/run_all_test.sh`、`tests/run_all_count_test.sh` |

## User Story 5 — 交付與範圍（優先度 P1）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-153 | 完成標準 2（先紅後綠） | 功能 | `specs/quarantine-followups/ledger.md` | 閱卷讀 ledger | 貼有 TC-101、TC-103、TC-107、TC-121、TC-130、TC-131 在未改 `run_all.sh` 時為紅的輸出，以及 TC-123 的輸出；這些案例現在轉綠 | 手動：閱卷讀 ledger（見總覽「不確定」第 1 條） |
| TC-154 | 範圍「不准動」與「不做」 | 不在範圍 | 本任務的完整 diff | 閱卷看 `git diff --stat` 對 base | 只列 4 個檔：`tests/run_all.sh`、`tests/quarantine.txt`、`tests/run_all_retry_test.sh`、`specs/quarantine-followups/ledger.md`；沒有動 `hooks/*`、`.github/*`（含 `tests.yml` 註解）、`platform/*`、`scripts/utils/portable.sh`、`docs/TESTING.md`、`memory/scripts/abf-fast-suite.sh`、閘門檔；`run_all.sh` 沒有為了固定今天而改任何一個字以外的覆蓋點 | 手動：閱卷看 `git diff --stat`（完成標準 4 指定） |
| TC-155 | 完成標準 6 | 功能 | 在 WSL 或 Linux | 執行 `bash tests/run_all.sh --retry-failed-once` | 整套綠 | 自動：`tests/run_all.sh` |
| TC-156 | 作法一第 7 點；待裁決第 3 點 | 功能 | `specs/quarantine-followups/ledger.md` | 閱卷讀 ledger | 寫明「since 是人填的、機器無法證明它沒被改，擋不住但會出現在 PR diff 同一行」的限制；若有任何測試檔因新的重跑 `TMPDIR` 變紅，記為 BLOCKED，而不是退回共用 `TMPDIR` | 手動：閱卷讀 ledger |

## 憲法與安全網

本任務只動測試與隔離名單，不碰 `hooks/*`、閘門與產品程式碼，沒有觸及憲法第 1–13 條或安全網規則，本節無案例。
