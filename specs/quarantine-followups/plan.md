---
id: quarantine-followups
title: 隔離名單補強：記錄首次隔離日（防每 14 天續期）、測試的「今天」固定成一次、重跑給乾淨暫存目錄
tier: A
kinds: backend
lane: L9-tests
base: v3
after: platform-test-shards
source: PR #197（ci-quarantine）第二輪 /code-review 的三點；memory/dev-plans/ci-quarantine.md
---

# quarantine-followups

> 本檔由 developer-agent 助理草擬（2026-10-24）。**A 級**。行號一律是 `origin/v3` 合併 PR #197 之後的 `b086b6d`（用 SHA 讀：`MSYS_NO_PATHCONV=1 git -C <repo> show b086b6d:<path>`；本機實測 `origin/v3:tests/run_all.sh` 讀到的是合併前的舊檔，別用分支名讀）。**只動 `tests/` 與一份帳本，不碰產品程式碼。**
> **`after: platform-test-shards`**：兩個任務都改 `tests/run_all.sh`（後者改預設逾時，約第 46 行）。本任務等它合併後再派，派工時以函式名（`quarantine_check`、`q_find`、`retry_and_conclude`）定位，不要信下面的行號。

## 目標
隔離名單真的有 14 天上限、測試在 UTC 午夜前後不會偶發紅、重跑的測試檔看不到第一次留下的暫存。對使用者的意義：「暫時隔離」不能靠每兩週改一次日期變成永久；而且這套防隨機紅的機制自己不能隨機紅。

## 維護者原話（verifier 出題用）
本任務沒有新的維護者原話；依據是 `ci-quarantine` 已核可的原話（10-24 約 17:50「1-3按照你的建議」）與 PR #197 第二輪 /code-review 的三條意見。每句對應如下，verifier 據此出題：
- 「每條有 issue 與 ≤14 天到期」「名單到期自動變紅」（`memory/dev-plans/ci-quarantine.md` 第 20、22 行）→ 第 1 點：到期日只對「今天」檢查，可以每兩週改一次日期續期，原話的「≤14 天」被繞過；所以要記首次隔離日。
- 「沒有 RUN_ALL_TODAY 之類的後門」（`tests/run_all_retry_test.sh` 第 398 行 TC-090，該後門是刻意移除的）→ 第 2 點：不准用環境變數覆蓋今天。
- 「重跑才綠的檔不得悄悄併進 passed」「重跑只一次」→ 第 3 點：重跑要是乾淨的一次，不是沿用第一次留下的狀態，否則「重跑才綠」可能是假綠或假紅。

## 範圍：檔案（只准改這些，共 4 個）
修改：
- `tests/run_all.sh`（`quarantine_check` 第 126–183 行、`q_find` 第 185–192 行、`retry_and_conclude` 第 198–274 行、檔頭註解第 95–103 行、`usage` 第 65–70 行）
- `tests/quarantine.txt`（只改檔頭說明，第 1–13 行；仍然沒有任何有效條目）
- `tests/run_all_retry_test.sh`（既有斷言的固定資料改格式、日期改走固定時鐘、新增案例）
新增：
- `specs/quarantine-followups/ledger.md`（executor 進度帳本；證據貼這裡）

**不准動（硬規則）**：`hooks/*`、`.github/*`、`platform/*`；`tests/run_all_test.sh`、`tests/run_all_count_test.sh`（它們不讀名單，`git grep -i quarantine b086b6d` 在這兩檔無命中）；`scripts/utils/portable.sh`；閘門檔（`spec.md`、`test-case*.md`、憲法、`docs/ROADMAP.md`、`.claude-plugin/plugin.json`）。`.github/workflows/tests.yml` 第 26–28 行的註解寫「expiry <= 14 days」，加了 since 欄之後仍然正確（只是不完整），**不改**，記進「待 developer-agent 裁決」。

## 作法
全部是決定，不是程式碼。

### 一、首次隔離日（第四欄）
1. **格式**：每條有效行改成**四欄**：`tests/<name>.sh <issue> <expiry YYYY-MM-DD> <since YYYY-MM-DD>`（`tests/run_all.sh` 第 98 行現為三欄，第 149–151 行判欄數）。`since`＝這個檔**第一次**被隔離的日期。用裸日期欄，不加 `since=` 之類的關鍵字，跟既有欄位一樣以空白分隔；欄名只寫在檔頭說明。
2. **規則（`quarantine_check` 內，逐行，第一個不過的就報、`continue`）**，順序固定：
   1. 欄數：不是 4 欄（尾端 `# 註解` 仍可接在第 4 欄之後，改第 149 行的判斷為 `nf>4 && f[4]=#*`）。**三欄的舊格式要有專屬訊息**：`expected 4 columns (tests/<name>.sh <issue> <expiry> <since>), found 3 - add the date this file was first quarantined`。
   2. 路徑、重複、issue 的檢查不變（第 156–170 行）。
   3. `since` 要是真的日期（沿用 `q_parse_date`，第 107–124 行）。
   4. **`since` 在未來 → 拒絕**，訊息含 `in the future`。
   5. 到期日已過（第 174–175 行，不變）→ `expired`。
   6. 到期日 > 今天+14 → 拒絕（第 176–177 行，不變，訊息仍含 `14 days`）。
   7. **到期日 > since+28 → 拒絕**，訊息含 `28 days` 並印出 since 與「距今幾天」。
3. **為什麼上限是 since+28，不是 since+14（裁決 1，見下）**：每一期仍是「離今天最多 14 天」（規則 6 保留），但從 since 起算總共最多 28 天＝**最多續一次**。
4. **不再有獨立的「since 太舊」規則**：因為規則 5（到期日 ≥ 今天）加規則 7（到期日 ≤ since+28）已經推得 since ≥ 今天−28。獨立寫一條只會產生兩條打架的訊息。第二次續期的人會看到規則 7 的訊息，裡面有 since 日期和天數，夠他明白「該修了」。
5. **`QUAR` 的內容仍然是三欄 `path issue expiry`**（第 179 行），**不放 since**。原因：`retry_and_conclude` 用 `${QI##* }` 取最後一欄當日期（第 254 行）；若 QUAR 帶了 since，輸出的 `quarantined #12 until <日期>` 會悄悄變成印 since，是個沒有人會注意到的錯。要再加一條測試釘住（TC-111）。
6. **檔頭文件**：`tests/quarantine.txt` 第 4–13 行改寫，必須含 (a) 四欄格式一行、(b) `since` 的白話定義（「第一次隔離這個檔的日期；續期時不要改它」）、(c) 一句規則：「每期最多 14 天，從 since 起總共最多 28 天，只能續一次」、(d) 不再有「expiry at most 14 days from the day it is checked」那句（改成 per-term 說法）。`run_all.sh` 檔頭第 97–103 行與 `usage` 第 65–70 行同步（`usage` 的 `--retry-failed-once` 說明加 `first-quarantined date`；`unq` 的提示句第 266 行改為 `tests/<name>.sh <issue> <expiry YYYY-MM-DD> <since YYYY-MM-DD> (expiry at most 14 days out; since = today)`）。
7. **誠實的限制，寫進檔頭與 ledger**：`since` 是人填的，機器無法證明它沒被改；把 since 改成今天等於換一種續期。擋不住，但會出現在 PR diff 的同一行，審查者看得到。要真正防呆須讀 git 歷史（`git log -S`），在 CI 淺層 clone 不可靠，**本任務不做**。

### 二、固定「今天」（測試用，不動產品）
8. **現況**：`run_all.sh` 只在第 136 行讀一次 `date -u +%F`；測試在第 28–29 行用兩次**各自獨立**的 `date` 呼叫（`T0` 與 `TN`），之後每個案例啟動一個新的 runner 又各讀一次；第 411–413 行靠「結束時發現日期變了就整份重跑一次」補救，但重跑那一輪仍可能跨午夜，而且 `T0` 與 `TN` 本來就可能不同天。
9. **決定：測試在自己的 sandbox 放一個 `date` 外掛程式（PATH 墊片）**，只在被測的 runner 以 `date -u +%F` 問今天時回答測試啟動時抓的那一天；其他參數一律交給真的 `date`。`run_all.sh` **一個字都不為此改**：沒有環境變數、沒有旗標、沒有「測試模式」。
10. **為什麼不選另外兩條路**：
    - 「避開邊界案例」：邊界（今天、今天+14、since+28）正是這套規則要測的，避開＝不測。
    - 「環境變數／旗標傳日期」：正是 TC-090 刻意移除的後門（`tests/run_all_retry_test.sh` 第 398–406 行）；就算改名為「僅測試用」，生產環境一樣設得到。
    - 墊片只存在測試的暫存目錄、只被測試的子行程看到；正式 CI 與本機跑的是同一份不含任何覆蓋點的 runner。
11. **墊片行為（定死）**：
    - 參數恰為 `-u +%F` → 印固定日期（來自測試寫的檔 `$TMP/today`，內容就是 `T0`），結束碼 0。
    - 參數含 `+%F` 但沒有 `-u` → 印哨兵日期 `1999-12-31`。這讓 TC-055（TZ=UTC-14／UTC+12 的案例，第 313–320 行）從「碰運氣才偵測得到」變成**確定偵測**：runner 若忘了 `-u`，所有案例立刻變紅。
    - 含 `-d` 或 `--date*` → 寫標記檔 `$TMP/date-rel-called` 並結束碼 1（沿用第 339 行 TC-056 的行為，改為由這個全域墊片負責）。
    - 其他 → `exec` 真的 `date`（路徑在建墊片前以 `command -v date` 取得）。
12. **測試端取日期只抓一次**：`NOW=$(date -u +%s)` 之後 `TN=$((NOW/86400))`、`T0=$(n2d "$TN")`，不再另呼叫 `date -u +%F`。第 44 行「`n2d` 與 `date` 是否一致」的檢查會因此變成跟自己比，改為對兩個**固定已知值**自檢：`n2d 0` ＝ `1970-01-01`，`n2d 19723` ＝ `2024-01-01`。
13. **移除第 408–413 行「日期變了就重跑」的保護與第 12–14 行的說明**——它已經多餘。第 12–14 行改寫為：「今天由 sandbox 內的 date 墊片固定，runner 沒有任何覆蓋點」。
14. **全域接入**：`run()`（第 80–90 行）的 `PATH` 一律把墊片目錄放最前面（在 `EXTRAPATH` 之前）。第 337–343 行 TC-056 原本自己建的 date 墊片改為使用這個全域墊片，只保留 python3 墊片在 `EXTRAPATH`。
15. **不是被測的地方不用墊片**：第 300 行 TC-052（真實樹的 `--check-quarantine`）與第 134 行 `--list` 直接呼叫真的 runner；真實 `quarantine.txt` 沒有有效條目，沒有邊界問題，不改。

### 三、重跑給乾淨的暫存目錄
16. **現況（先講事實，因為任務題目的前提只對一半）**：`run_all.sh` 沒有「每個檔一個 TMPDIR」。只有一個 `LOGDIR`（第 368 行 `mktemp -d "${TMPDIR:-/tmp}/bioflow-tests.XXXXXX"`），第一輪日誌寫 `$LOGDIR/$b.log`（第 387、391 行），重跑日誌寫 `$LOGDIR/$b.retry.log`（第 213、217 行）——**日誌檔本來就分開**，沒有互相覆蓋。真正共用的是測試行程**繼承的環境變數 `TMPDIR`**：第一次與重跑用同一個，測試若把狀態留在 `$TMPDIR`（固定檔名），重跑會看到第一次的殘留。
17. **決定**：**只給重跑**一個全新的空目錄 `"$LOGDIR/tmp.$b.retry"`（`mkdir -p` 後以 `env TMPDIR=<該目錄>` 前綴傳給 `clocked … bash`；兩處：第 213 行 verbose 與第 217 行靜默）。第一輪**不改**（保持「不帶旗標時行為與今天完全相同」，ci-quarantine 的要求）。不刪第一次的殘留（它是失敗現場，要留著給人看）。
18. 目錄放在 `$LOGDIR` 之下：與日誌同壽命、同一個清理點，不需要新的 trap；`mkdir` 失敗就把這次重跑記為失敗（`failed2`），不要退回共用 `TMPDIR`（退回等於悄悄回到舊行為）。
19. 輸出文字不變：`retry <name> ... ok|FAIL|TIMEOUT` 這行不加路徑，既有的輸出比對（TC-001、TC-022、TC-023）不受影響。

## 失敗先行測試
全在 `tests/run_all_retry_test.sh`。新案例編號接在既有之後，從 TC-101 起。**共 26 條新案例（A 14、B 6、C 6），加上下節列出的既有斷言改動。** 先寫、現在必紅。

**A. since 欄（對應作法一）**
- TC-101 三欄舊格式 `tests/ok_test.sh #12 <今天+3>`：exit 1；stderr 含 `quarantine: tests/quarantine.txt:1:` 與 `found 3`。
- TC-102 since 不是真日期（`2026-13-40`、`not-a-date` 各一條，共 2 條）：exit 1，訊息含行號。
- TC-103 since＝今天+1：exit 1，stderr 含 `in the future`。
- TC-104 since＝今天，到期＝今天+14：exit 0（新格式的基本有效案例）。
- TC-105 since＝今天−14，到期＝今天+14（＝since+28，上限當天）：exit 0。
- TC-106 since＝今天−15，到期＝今天+13（＝since+28）：exit 0。
- TC-107 since＝今天−15，到期＝今天+14（＝since+29）：exit 1，stderr 含 `28 days` 與 since 日期。
- TC-108 **續期繞道**：since＝今天−28，到期＝今天：exit 0（最後一天）；since＝今天−29，到期＝今天：exit 1，訊息含 `28 days`（共 2 條斷言，同一案例）。
- TC-109 到期日已過但 since 也很舊（since＝今天−40，到期＝今天−1）：exit 1，stderr 含 `expired`（先報 expired，不報 28 days）。
- TC-110 到期＝今天+15、since＝今天：exit 1，stderr 含 `14 days`（每期上限規則仍在，且先於 28 天規則）。
- TC-111 已登記的 FLAKY 行仍印 `quarantined #12 until <到期日>`，**不是 since**（四欄資料，到期與 since 故意取不同日）。
- TC-112 `--check-quarantine` 對四欄有效／無效名單：exit 0／1，且 sandbox 不跑任何測試（沿用 TC-050/051 的做法，各一條斷言）。
- TC-113 真實 `tests/quarantine.txt` 檔頭含 `since` 字樣與四欄格式行，且仍沒有有效條目（接在 TC-057 之後）。
- TC-114 `--help` 輸出含 `first-quarantined` 與 `--retry-failed-once`。

**B. 固定今天（對應作法二）**
- TC-120 `tests/run_all.sh` 裡 `date -u` 只出現一次，且全檔沒有 `RUN_ALL_TODAY`、`TODAY=` 之類的讀取（靜態 grep；與既有 TC-090 的行為測試互補）。
- TC-121 把墊片日期設成 `2030-02-28`：到期＝`2030-03-14`（+14）exit 0；`2030-03-15`（+15）exit 1，訊息含 `14 days`。證明墊片真的生效（跟真實今天無關）且跨月不出錯。
- TC-122 墊片日期 `2028-02-27`（閏年）：到期 `2028-03-12`（+14，經過 2/29）exit 0；`2028-03-13` exit 1。
- TC-123 墊片日期設成某個**午夜前一秒的日子**（`2026-12-31`）：since＝`2026-12-31`、到期＝`2027-01-14` exit 0（跨年）；`2027-01-15` exit 1。
- TC-124 不帶 `-u` 的哨兵：用一個臨時改過的 runner 副本（sandbox 內把第 136 行的 `date -u +%F` 換成 `date +%F`）跑一個有效名單 → exit 1，證明 TC-055 的 TZ 案例現在是確定會抓到的。
- TC-125 墊片收到 `-d` 時寫標記並失敗；TC-056 的「沒用相對日期」斷言改讀這個標記（既有案例，見下節；此條只驗墊片本身：直接呼叫墊片 `date -d tomorrow` 得到 exit 1 且標記存在）。

**C. 重跑的乾淨暫存（對應作法三）**
- TC-130 固定資料：測試檔第一次在 `$TMPDIR/leftover` 留檔後 exit 1；第二次若 `$TMPDIR/leftover` 存在就 exit 1，否則 exit 0。已登記為 FLAKY，帶 `--retry-failed-once`：exit 0，輸出含 `green after retry: 1`。**現在（共用 TMPDIR）會紅。**
- TC-131 該測試把 `$TMPDIR` 路徑記進計數檔：第一次＝sandbox 傳進來的 `$TMPD`；第二次≠`$TMPD`，且以 `<logs>/tmp.<name>.retry` 結尾。
- TC-132 第一輪留下的 `$TMPD/leftover` 在整個執行結束後**仍在**（只是重跑看不到，沒有被刪）。
- TC-133 `$LOGDIR/<name>.log` 與 `$LOGDIR/<name>.retry.log` 兩個檔都在，內容不同（從 `logs:` 行取 LOGDIR；`normalize` 會刪該行，所以此案例直接讀 `OUT`）。
- TC-134 不帶旗標、測試失敗：測試看到的 `$TMPDIR` 等於 `$TMPD`（第一輪沒有被換成每檔目錄；釘住「不帶旗標與今天完全相同」）。
- TC-135 `--verbose` 的重跑也走乾淨目錄（同 TC-130 的資料，加 `--verbose`）。

## 既有斷言的改動（逐條點名）
`tests/run_all_retry_test.sh`。「**只換資料格式**」＝斷言本身一字不改，只是名單那一行多帶 since 欄（用新輔助函式 `qline <檔名> <issue> <到期>` 產生 `tests/<檔名> <issue> <到期> <今天>`）。
- **只換資料格式（斷言不變）**：TC-016、TC-017、TC-018、TC-019、TC-020、TC-021（第 161 行同一組）；TC-025（第 193 行）；TC-027（第 203 行）；TC-029（第 213 行）；TC-030（第 218 行）；TC-031（第 221 行）；TC-034／TC-047（第 265 行）；TC-036、TC-037、TC-038、TC-040、TC-041、TC-042、TC-043、TC-044（第 277–287 行，經 `chk_valid`／`chk_bad`）；TC-046（第 289 行）；TC-050、TC-051（第 292、296 行）；TC-053（第 303 行）；TC-054（第 308 行）；TC-055（第 317 行）；TC-079（第 237 行）；TC-080、TC-081（第 244、247 行）；TC-082（第 254 行）；TC-086、TC-087、TC-088（第 364–387 行）；TC-089（第 393 行）；TC-091 與 TC-056 shimmed 的兩個 `sweep`（第 325–343 行）。
- **斷言本身要改**：
  - **TC-015「format hint」**（第 157 行）：期望字串由 `tests/<name>.sh <issue> <YYYY-MM-DD> (at most 14 days out)` 改為 `tests/<name>.sh <issue> <expiry YYYY-MM-DD> <since YYYY-MM-DD>`（對應作法一第 6 點）。
  - **TC-039**（第 280 行，缺 issue 欄）：資料改成缺 issue 的四欄形式 `tests/ok_test.sh <到期> <今天>`；斷言（exit 1、含行號前綴）不變。
  - **TC-045「fourth column rejected」**（第 288 行）：語意改成「**第五欄**被拒」：資料 `tests/ok_test.sh #12 <到期> <since> extra`，改名 `TC-045 fifth column rejected`。
  - **TC-084「trailing comment」**（第 349–354 行）：尾端 `# 註解` 現在接在第 4 欄之後；兩行資料與單行資料都換成四欄加註解，斷言不變。
  - **TC-090a／b／c**（第 399–405 行，`RUN_ALL_TODAY` 不是後門）：資料換成四欄。**TC-090b** 的名單行 `tests/ok_test.sh #12 2000-01-05` 需要 since，用 `2000-01-01`；它仍應 exit 1 且含 `expired`（規則 5 先於規則 7，正好驗證 TC-109 的順序）。
  - **TC-052**（第 300 行）：不改。
  - **TC-056「neither python3 nor a relative date was used」**（第 343 行）：標記檔路徑不變（`$TMP/date-rel-called`），但墊片來源由局部改為全域；斷言不變。
  - **TC-055**（第 314–320 行）：斷言不變；因為 `date` 現在由墊片提供，不帶 `-u` 的呼叫回哨兵日期而不是靠真實時區碰運氣。
- **刪除（非斷言）**：第 44 行的一致性自檢改為對固定已知值自檢（作法二第 12 點）；第 408–413 行的「日期變了就重跑」保護刪除（作法二第 13 點）。

## 完成標準（done when）
1. 新案例 TC-101～TC-135 全綠；「既有斷言的改動」列出的每一條改完後全綠。
2. 先寫的案例在實作前確實紅：至少 TC-101、TC-103、TC-107、TC-121、TC-130、TC-131 在未改 `run_all.sh` 時為紅（貼進 ledger.md）。
3. `bash tests/run_all_retry_test.sh` 在 UTC 午夜前後各跑一次的結果一致——用墊片後不再依賴真實時鐘；executor 以 `TZ` 與強制把墊片日期設在 `2026-12-31` 取代真的等到午夜（貼 TC-123 的輸出）。
4. `bash tests/run_all.sh --check-quarantine`（真實樹）exit 0；`git diff --stat` 只列範圍內 4 個檔（通例：閱卷看 diff，證據貼 ledger）。
5. 不帶旗標的輸出與今天相同：`tests/run_all_test.sh`、`tests/run_all_count_test.sh` 一個斷言都沒動且全綠。
6. 整套 `bash tests/run_all.sh --retry-failed-once` 綠（在 WSL／登入節點；原生 Git Bash 需 `--allow-msys`，其紅是已知缺口）。

## 環境事實
- `tests/run_all.sh` 只在第 136 行讀一次今天（`date -u +%F`）；日期算術全是純 bash（第 95–103 行說明、第 107–124 行 `q_parse_date`），**不用 `date -d`、不用 python3**（TC-056 守著）。
- `LOGDIR` 單一（第 368 行）；第一輪日誌 `$b.log`（第 387、391 行）、重跑日誌 `$b.retry.log`（第 213、217 行）；測試行程沒有被設定每檔 `TMPDIR`，沿用 runner 的環境。
- `clocked`（`scripts/utils/portable.sh` 第 229–256 行）把 `"$@"` 當命令執行，所以 `clocked N env TMPDIR=… bash file` 可行，`timeout` 與純 shell watchdog 兩種路徑都適用。
- 測試檔 sandbox：`reset()`（第 57–63 行）複製 `run_all.sh` 與 `portable.sh` 進 `$SR`，假的 `uname` 讓它在 Git Bash 也能跑（第 22–25 行）；`run()` 組 `PATH`（第 83–84 行）。
- `tests/run_all_retry_test.sh` 目前有 TC-001～TC-091 的案例；既有案例編號本計畫不重排。
- `.github/workflows/tests.yml` 第 47–57 行用 `--retry-failed-once --timeout 900` 並以 `grep -E '^FLAKY [^ ]+.sh  '` 取 FLAKY 行；本任務不改輸出行格式，所以那段不受影響。
- `hooks/*`、`.github/*`、`platform/*` 不碰；`platform-test-shards` 進行中會改 `tests/run_all.sh` 預設逾時，故 `after:`。

## 不做
- 不從 git 歷史驗證 `since`（淺層 clone 不可靠；限制已寫進檔頭）。
- 不加任何讓測試以外的人覆蓋「今天」的環境變數、旗標或隱藏參數。
- 不改第一輪的 `TMPDIR`、不為每個檔常駐一個臨時目錄。
- 不改 `.github/workflows/tests.yml` 的註解、不改 `docs/TESTING.md`、不動 `memory/scripts/abf-fast-suite.sh`。
- 不調整 14 天每期上限本身（維護者已核可）。
- 不處理 `platform_test.sh` 逾時（`platform-test-shards`）。

## 裁決
1. A 級；專長守則用 `backend`；verifier 通過＋CI 綠後由 developer-agent 自己合併。
2. **總上限選 since+28（最多續一次），不選 since+14（零續期）**：零續期在機器上其實擋不住（since 是人填的，改日期一樣能繞，見作法一第 7 點），卻會讓真的需要第二個迭代才修好的案例被迫偽造 since；28 天上限讓正當的一次續期不必說謊，而第二次續期立刻看到訊息。維護者若要零續期，只需把規則 7 的 28 改 14（TC-105、TC-106、TC-108 的邊界隨之改），其餘不變。
3. **since 用裸日期第四欄**，不用 `since=` 關鍵字；三欄舊行用專屬訊息拒絕，不靜默相容（靜默相容＝舊行永遠不受 since 規則約束）。
4. **今天用 PATH 墊片固定，不用任何 runner 內建的覆蓋點。**
5. **第 3 點的前提只對一半（日誌本來就分開，共用的只有繼承的 `TMPDIR`）**；決定只給重跑一個乾淨目錄，第一輪不動。

## 待 developer-agent 裁決
1. 28 天（一次續期）還是 14 天（零續期）？上方裁決 2 是我的建議，維護者可改。
2. `.github/workflows/tests.yml` 第 28 行註解「expiry <= 14 days」要不要補一句 since？它不是錯，只是不完整；改它要 /code-review（受保護路徑），不值得為一個註解開任務。建議不改。
3. 第 3 點若 executor 發現某個測試檔在 `TMPDIR` 變更後（路徑較長、不在 `/tmp` 底下）而變紅：回報 BLOCKED 記進 ledger，不要為了讓它綠而回頭共用 `TMPDIR`。

## 裁決二（2026-10-24 20:50 developer-agent）
1. 上限：總共 28 天（可續期一次），照計畫。
2. tests.yml 註解不動。
3. 新的重跑 TMPDIR 讓某支測試變紅 → 回報 BLOCKED，不退回共用 TMPDIR。
4. 讀程式一律以 SHA 為準；platform-test-shards 合併後以函式名定位。

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
