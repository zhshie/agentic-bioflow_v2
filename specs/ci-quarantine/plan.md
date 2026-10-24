---
id: ci-quarantine
title: CI 的隨機紅隔離名單（tests/quarantine.txt）＋失敗檔只重跑一次（run_all.sh --retry-failed-once）
tier: C
kinds: backend
lane: L9-tests
base: v3
source: memory/reference/dev-architecture-review-2026-10-24.md 第 5.2 節第 2 項；維護者 2026-10-24 約 17:50「1-3按照你的建議」
---

# ci-quarantine

> 本檔由 developer-agent 助理草擬（2026-10-24）。**C 級**（維護者已在 10-24 約 17:50 點頭，方向題已答完；但改到 `.github/` 受保護路徑，須 `/code-review`）。行號一律是 `origin/v3`（`47701fb`）的行號。**只動 CI 與測試跑法，不碰任何產品程式碼。**

## 目標
讓 CI 對「偶發紅」有一個**看得見、會過期**的處理方式：失敗的測試檔自動只重跑一次；重跑就綠的叫 FLAKY，必須已登記在 `tests/quarantine.txt`（每條有 issue、最多 14 天到期），否則 CI 照樣紅。對使用者的意義：不再有人把「再跑一次就好」當成沒事而放著不修，也不再因為一支已知的偶發紅擋住無關的合併。

## 維護者原話（verifier 出題用）
取自審查報告第 5.2 節第 2 項（維護者 10-24 約 17:50 回「1-3按照你的建議」）：
- 「**隨機紅測試在修好之前用『隔離名單』（照常跑、紅照常顯示、每條有 issue 與 ≤14 天到期）**」→ 名單裡的檔案照常跑；紅的輸出照常印出；沒有 issue 或到期超過 14 天或已過期的條目讓 run_all 失敗。
- 「**＋『失敗的那幾支只重跑一次』（跟 CI 現行規則一樣）**」→ 只重跑第一輪失敗／逾時的檔，且只一次；兩次都紅＝真紅。
- 「建議：好，前提是 5.1 第 1 條同時進行，**名單到期自動變紅**」→ 過期不需要人記得，CI 自己變紅。
- 本任務補充的設計要求（派工訊息，維護者已核可方向）：重跑才綠的檔以 `FLAKY <名稱>` 單獨列出，**絕不悄悄併進 passed**；沒登記的 FLAKY 要失敗並說明「修掉或加一行隔離」；不帶旗標時行為與今天完全相同；本機 executor／verifier 的跑法（`memory/scripts/abf-fast-suite.sh`）**不改**，仍然單次嚴格。

## 範圍：檔案（只准改這些，共 5 個）
修改：
- `tests/run_all.sh`（加 `--retry-failed-once`、`--check-quarantine`、驗證 `tests/quarantine.txt`、重跑與結論）
- `.github/workflows/tests.yml`（**受保護路徑**；`CLAUDE.md` 第 227–229 行把 `.github/` 列為 executor「Never edit」。**派工訊息必須寫明：本任務授權 executor 只改這一個檔、只改下述作法 7 的內容**）
新增：
- `tests/quarantine.txt`（起始內容只有說明用註解，沒有任何有效條目；PR #194 剛修掉今天已知的隨機紅）
- `tests/run_all_retry_test.sh`（新測試，見「失敗先行測試」）
- `specs/ci-quarantine/ledger.md`（executor 進度帳本；證據貼這裡）

**不准動（硬規則）**：`hooks/*`、`platform/abf_station/launch.py`、`platform/tests/test_resume_edit_params_station.py`、`docs/TESTING.md`（皆為進行中任務持有）；`tests/run_all_test.sh`、`tests/run_all_count_test.sh`、`tests/jev_test.sh`、`tests/dev_workflow_test.sh`（既有測試一個斷言都不改，見「既有測試」）；`scripts/utils/portable.sh`；閘門檔（`spec.md`、`test-case*.md`、憲法、`docs/ROADMAP.md`、`.claude-plugin/plugin.json`）；`memory/scripts/abf-fast-suite.sh`（在工作區、不在 repo）。另：`flaky-tests` 計畫禁止動 `tests/run_all.sh`，本任務是唯一改它的人，兩者檔案不相交。

## 作法
行為事實（`tests/run_all.sh`，`47701fb`）：旗標在第 71–82 行 `case` 解析，未知旗標走第 80 行 `usage`；第一輪迴圈第 170–197 行已經依序（不並行）跑每個檔，把失敗與逾時的檔名收進 `FAILED_LIST`（第 192–195 行，逾時 `rc=124`）；第 199–212 行印「未通過檔案的輸出尾端 25 行」；第 214–221 行組並印摘要；第 227 行 `[ "$failed" = 0 ] && [ "$timedout" = 0 ] && [ "$total" = "$expected" ] || exit 1`，最後第 228 行印 `all green`。`FILES` 是 `tests/` 下的 basename（第 110–118 行）；`clocked`（`scripts/utils/portable.sh` 第 229–251 行）負責逾時並回 124。CI 在 `.github/workflows/tests.yml` 第 42–43 行跑 `bash tests/run_all.sh`；job id 是 `run_all`（第 34 行），repo ruleset 以此名為必要檢查（`developer-agent.md` 第 130 行），**job 與 step 名稱不得改**。

1. **旗標與預設不變**。第 71–82 行加兩個旗標：`--retry-failed-once`（`RETRY=1`）與 `--check-quarantine`（只驗名單後結束）。第 51–64 行 usage 加兩行說明。不帶旗標時，第 170–226 行與第 227–228 行**一個字元都不動**（第 227 行改成 `if [ "$RETRY" = 0 ]; then <原第 227 行>; else <新結論函式>; fi` 的形式，`RETRY=0` 走的是原字串）。**第 1–20 行的標頭註解不得出現 ≥10 的獨立整數**（`run_all_count_test.sh` 第 12 行 TC-001 會紅）；所有說明文字寫在第 42 行 `set` 之後或函式內。
2. **名單格式**（`tests/quarantine.txt`）：空行與以 `#` 開頭的整行是註解；每條有效行**恰好三欄**（空白分隔，容許行尾 `\r`）：`tests/<檔名>.sh <issue> <YYYY-MM-DD>`。
   - 路徑：必須是 `tests/<名稱>.sh`，且該檔存在於 `$ROOT/tests/`（防打錯字而名單形同虛設）；同一路徑不得出現兩次。
   - issue：`#<數字>` 或 `https://github.com/<owner>/<repo>/issues/<數字>`；其他一律拒絕。
   - 到期日：合法日曆日。規則**只用「檢查當天」，不查 git 歷史**：`到期日 < 今天` ＝ 已過期，失敗；`到期日 > 今天 + 14 天` ＝ 超過 14 天，失敗；等於今天仍有效（最後一天）。結果：要延期就得每次改這個日期，延期必然出現在 diff 裡，這是刻意的。
   - 「今天」＝環境變數 `RUN_ALL_TODAY`（只給測試用）否則系統日期 `date +%F`。日期加減**用純 bash 的日數換算**（civil-from-days 公式），不用 `date -d`（GNU 限定，`tests/portable_userland.sh` 第 36 行規則）也不依賴 python3（`--allow-msys` 會略過 python3 檢查，第 130–131 行）。
   - 檔案不存在視同空名單。空檔、只有註解的檔都合法。
3. **驗證時機**：只在 `--retry-failed-once` 或 `--check-quarantine` 時驗；放在工具檢查（第 159 行）之後、橫幅（第 161 行）之前，**任何測試開跑前**就失敗，退出碼 1，每個問題一行 `quarantine: tests/quarantine.txt:<行號>: <原因>`（stderr）。所以名單過期會讓 CI 紅，即使當輪沒有任何測試失敗（刻意：到期自動變紅）。`--check-quarantine` 驗完即 `exit 0/1`，不跑任何測試、不寫 log 目錄；順序在 MSYS 拒絕（第 86 行）**之後**。
4. **重跑**（只在 `RETRY=1`）：第一輪與其輸出（第 170–221 行）照舊全印，**紅照常顯示**。摘要後，若 `FAILED_LIST` 非空：印標題 `== retry: re-running <N> file(s) once ==`，依第一輪順序**逐一循序**重跑（同樣 `clocked "$PER_TEST_TIMEOUT" bash ... </dev/null`，log 存 `$LOGDIR/<b>.retry.log`），每檔一行 `retry <b> ... ok|FAIL|TIMEOUT`。**不改第一輪的計數**：`passed/failed/timedout` 與摘要字串維持第一輪的數字，重跑結果不併入 passed。
5. **結論**（`RETRY=1` 時取代第 227–228 行）：
   - 先看 `total != expected`（INCOMPLETE，第 215 行）：照舊 `exit 1`，重跑不能補救。
   - 兩次都沒過的檔：印 `== FAILED twice ==` 區塊，每檔 `FAILED <b>` 並印其 retry log 尾端 25 行；`exit 1`。即使它在名單裡也一樣（隔離只饒過「重跑會綠」，不饒過真紅）。
   - 重跑才過的檔：印獨立區塊 `== FLAKY (failed the first run, passed the retry) ==`，每檔一行，**行首固定 `FLAKY <b>`**（CI 用 `grep '^FLAKY '` 抓），後接 `  quarantined <issue> until <日期>` 或 `  NOT in tests/quarantine.txt`。
   - 有任何 FLAKY 不在名單：往 stderr 印 `FLAKY not quarantined: <名稱…>. Fix the test, or add one line per file to tests/quarantine.txt: tests/<name>.sh <issue> <YYYY-MM-DD> (at most 14 days out).`，`exit 1`。
   - 全部通過且無 FLAKY：照舊印 `all green`，`exit 0`。全部 FLAKY 都在名單、無其他問題：印 `green after retry: <N> quarantined flaky file(s)`（**刻意不含 `all green`**，免得被當成乾淨通過），`exit 0`。
   - 退出碼：沿用今天的 1（失敗）；環境問題 3 與用法錯誤 2 不變。
6. **本機跑法不變**：`memory/scripts/abf-fast-suite.sh` 第 52 行是 `exec bash tests/run_all.sh "$@"`，不帶旗標，**本任務不改它**；executor／verifier 的本機驗證仍是單次嚴格（人若手動傳旗標，行為如上，但派工訊息不要求）。
7. **CI**（`.github/workflows/tests.yml`，只改第 42–43 行那個 step，並在其後加一個 step；其餘含頂端說明註解的既有內容不動，註解末加兩行解釋新旗標）：
   - 第 42–43 行改成 `shell: bash`（GitHub 會用 `-eo pipefail`），指令 `bash tests/run_all.sh --retry-failed-once 2>&1 | tee "$RUNNER_TEMP/run_all.out"`。step 名稱改成 `bash tests/run_all.sh --retry-failed-once`（這是 step 名不是 job 名，不影響必要檢查）。
   - 新增 step，`if: always()`：若 `grep '^FLAKY ' "$RUNNER_TEMP/run_all.out"` 有輸出，往 `$GITHUB_STEP_SUMMARY` 追加 `### FLAKY tests` 標題與那些行（markdown 清單）；沒有就什麼都不寫。這個 step 自己不得讓 job 失敗（`|| true` 僅限 grep 無輸出那一支，tee 與測試的結果仍由前一個 step 決定）。
8. **受保護路徑審查**：本任務改 `.github/`，**developer-agent 在合併前必須對這個 PR 跑內建 `/code-review`**（`developer-agent.md` 第 130 行：改到受保護路徑另跑一次安全審查，只採高信心結果），把結論記進 PR 描述。並因 `.github/` 在 CLAUDE.md「Never edit」清單，此任務屬 C 級＋受保護路徑，不掛 `--auto`，由 developer-agent 在 CI 綠、`/code-review` 無高信心問題後手動合併。

## 失敗先行測試
新檔 `tests/run_all_retry_test.sh`（現在會紅：旗標不存在，第 80 行會 `unknown option`）。架構照 `tests/run_all_test.sh`：
- 在 `mktemp -d` 建沙盒根 `SR/{tests,scripts/utils}`，複製 `tests/run_all.sh` 與 `scripts/utils/portable.sh`（`run_all_test.sh` 第 83、165 行同法），沙盒內只放小型假測試檔；**絕不跑真套件**（會遞迴）。
- 用 `run_all_test.sh` 第 21–25 行的 `mkuname` 手法在 PATH 前放一個回答 `Linux` 的假 `uname`，所有執行都帶 `--allow-missing-tools`，使本檔在 Git Bash 也能跑。
- 假檔：`ok_test.sh`（`exit 0`）；`flaky_test.sh`（用計數檔 `$TMP/c.flaky`，第一次 `exit 1`、第二次 `exit 0`，並把次數累加進計數檔）；`bad_test.sh`（永遠 `exit 1`，也累計次數，第二次輸出含標記字串 `second-run-marker`）；`slow_test.sh`（第一次 `sleep 3` 配 `--timeout 1`，第二次立即過）。
- 日期一律用 `RUN_ALL_TODAY` 固定（基準 `2026-10-24`）。

案例（共 38 條，編號 R01–R38；斷言一律對退出碼與輸出內容，不寫「執行過」這類空話）：

**A. 不帶旗標＝今天的行為（對固定 fixture，不對 origin/v3）**
- R01 兩個 `ok_test.sh` 類檔、不帶旗標：退出 0；輸出經正規化（刪 `logs:` 行、`root:` 行換成 `root: X`、去掉各行尾 `<n>s`）後**逐字等於**測試內嵌的期望文字（橫幅、兩行 `ok`、`2/2 passed`、`all green`）。
- R02 不帶旗標、含 `bad_test.sh`：退出 1；摘要為 `1/2 passed, 1 failed`；`bad_test.sh` 計數檔＝1（只跑一次）；輸出不含 `FLAKY`、`retry`。
- R03 不帶旗標、含 `flaky_test.sh`（第一次紅）：退出 1、計數＝1（今天就是嚴格單次）。
- R04 不帶旗標、沙盒名單寫了亂碼：退出 0，名單根本不被讀。
- R05 `--help` 的用法文字含 `--retry-failed-once` 與 `--check-quarantine`。

**B. 帶旗標、沒有失敗**
- R06 全綠＋旗標：退出 0、輸出含 `all green`、不含 `FLAKY`、不含 `== retry`；每個檔計數＝1。
- R07 名單是空檔：同 R06 結果。
- R08 名單不存在：同 R06 結果。

**C. 重跑與 FLAKY**
- R09 `flaky_test.sh` 不在名單：退出 1；輸出有一行以 `FLAKY flaky_test.sh` 開頭；stderr 含 `tests/quarantine.txt` 與 `Fix the test`。
- R10 `flaky_test.sh` 在名單且有效：退出 0；仍有 `FLAKY flaky_test.sh` 行且含 issue 號；最後一行含 `green after retry: 1` 且**不含** `all green`。
- R11 FLAKY 不併進 passed：R10 的摘要行仍是第一輪數字（`2/3 passed, 1 failed`）。
- R12 `FLAKY` 行出現在摘要行**之後**，且在 `== FLAKY` 標題底下。
- R13 紅照常顯示：R10 輸出仍含 `== output of what did not pass ==` 與 `--- flaky_test.sh ---`。
- R14 只重跑失敗的檔：`ok_test.sh` 計數＝1，`flaky_test.sh` 計數＝2，且重跑是循序（兩個 flaky 檔時，重跑行順序＝第一輪順序）。
- R15 `bad_test.sh`（兩次都紅）＋旗標：退出 1；計數＝2；輸出含 `FAILED bad_test.sh`；**不含** `FLAKY bad_test.sh`；含 `second-run-marker`（印的是重跑 log 尾端）。
- R16 `bad_test.sh` 在名單：仍退出 1（隔離不饒真紅）。
- R17 逾時檔：`slow_test.sh` 第一次逾時（`--timeout 1`）、第二次過：被視為 FLAKY，不在名單則退出 1，在名單則退出 0。
- R18 一個 FLAKY 在名單、另一個不在：退出 1；錯誤訊息只點名不在名單的那個。
- R19 在名單的 FLAKY＋另一個真紅：退出 1。
- R20 `--retry-failed-once --only flaky`：只跑與重跑符合的檔；`ok_test.sh` 計數＝0。
- R21 `--retry-failed-once --list`：輸出與不帶旗標的 `--list` 逐字相同，退出 0。

**D. 名單驗證（旗標才驗；任何測試開跑前失敗，計數檔不存在）**
- R22 到期日＝昨天：退出 1；訊息含 `quarantine: tests/quarantine.txt:<行號>:` 與 `expired`；沒有任何測試被執行。
- R23 到期日＝今天：有效。
- R24 到期日＝今天+14：有效；今天+15：退出 1，訊息含 `14 days`。
- R25 少了 issue 欄（只有兩欄）：退出 1。
- R26 issue 寫法：`#12`、`https://github.com/zhshie/agentic-bioflow/issues/12` 有效；`12`、`#`、`https://example.com/x` 無效（逐一檢查）。
- R27 日期不合法：`2026-13-40`、`2026-2-3`、`not-a-date` 都退出 1。
- R28 路徑不存在於沙盒 `tests/`、或不是 `tests/*.sh` 形式（如 `../x.sh`、`tests/a.txt`）：退出 1。
- R29 同一路徑兩行：退出 1。
- R30 多出第四欄：退出 1。
- R31 註解行、空行、行尾 `\r`（CRLF）都被容忍：有效名單退出 0。
- R32 名單有一行已過期、但這輪所有測試都綠：仍退出 1（到期自動變紅）。
- R33 邊界：`RUN_ALL_TODAY=2028-02-20`（閏年）→ 到期日 `2028-03-05` 有效、`2028-03-06` 無效；`RUN_ALL_TODAY=2026-12-25` → `2027-01-08` 有效、`2027-01-09` 無效。
- R34 `--check-quarantine`：有效名單退出 0 且不執行任何測試、不建立 log 目錄；無效名單退出 1。

**E. 真實 repo**
- R35 對**真實** `$ROOT/tests/run_all.sh --check-quarantine`（不是沙盒）：退出 0（真實名單合法；日後有人加壞行，這條在 CI 就紅）。這條不執行任何測試，不會遞迴。
- R36 `.github/workflows/tests.yml` 靜態檢查：含 `--retry-failed-once`、`GITHUB_STEP_SUMMARY`、`grep '^FLAKY '`；仍含 `Install jq` 與 job 名 `run_all:`；不再有獨立一行 `run: bash tests/run_all.sh`（舊寫法）。
- R37 `tests/run_all.sh` 第 1–20 行沒有 ≥10 的獨立整數、且仍含 `run time`（對應既有 `run_all_count_test.sh` 的 TC-001／TC-002，這裡只是提早在新檔也釘一次，避免兩個檔互相踩）。
- R38 `bash tests/run_all.sh --list` 的檔數＝`ls tests/*.sh` 減 `run_all.sh`，且列表含 `run_all_retry_test.sh`（新檔自己有被收進去）。

## 既有測試：哪些斷言受影響（已逐一核對 `origin/v3`）
- `tests/run_all_count_test.sh`：第 12–13 行 TC-001（標頭前 20 行不得有 ≥10 的獨立整數）**斷言不改**，但作法 1 要求不把這類數字寫進標頭；第 16 行 TC-002（標頭有 `run time`）不變；第 19–23 行 TC-004／TC-005 比對 `--list` 行數與 `ls tests/*.sh` 的檔數——新增 `run_all_retry_test.sh` 兩邊同時 +1，自動成立；`quarantine.txt` 不是 `*.sh`，不計入。**零斷言需要修改。**
- `tests/run_all_test.sh`：第 59 行只 grep 用法含 `--allow-msys`；第 168 行 TC-033 對「`exit 1` 的測試、不帶旗標」要求退出 1、含 `failed`、不含 `all green`，不帶旗標路徑不變。**零斷言需要修改。**
- `tests/jev_test.sh` 第 334 行 TC-042（`--list` 含 `jev_test.sh`）、`tests/dev_workflow_test.sh` 第 48 行（`CLAUDE.md` 含 `bash tests/run_all.sh`，未動 CLAUDE.md）、`tests/guard_plugin_files_test.sh` 第 128–146 行（對 `bash <root>/tests/run_all.sh` 這條命令的閘門放行判斷，與旗標無關）：不受影響。
- `tests/portable_userland.sh`：第 72–85 行掃 `tests/*.sh` 的 `grep -P`；新檔與 `run_all.sh` 不得使用（作法已避開）。
- 沒有任何既有測試讀 `.github/workflows/tests.yml`（`grep` 全 `tests/` 無命中），故 workflow 的修改不影響既有斷言；R36 是新增。
- 結論：**要修改的既有斷言為 0 條**；executor 若發現必須改任何既有斷言，視為設計出錯，回報 BLOCKED。

## 完成標準（done when）
- `bash tests/run_all_retry_test.sh` 全綠（38 條）；在這之前先在未改 `run_all.sh` 的狀態下跑一次並把「紅」貼進 ledger。
- 在 WSL 或 Linux 全套 `bash tests/run_all.sh` 綠（含 `run_all_count_test.sh`、`run_all_test.sh` 原樣通過）。
- ledger 貼：`git diff --stat`（只有範圍列出的 5 個檔）；作法 1「不帶旗標一字不動」的證據——同一個假 fixture 目錄，在 `origin/v3` 的 `run_all.sh` 與新 `run_all.sh` 各跑一次（不帶旗標），正規化後 `diff` 為空（通例：閱卷看 diff）；真實 repo 上 `--retry-failed-once` 全綠與 `--check-quarantine` 的輸出。
- PR 開出後 CI 的 `run_all` job 綠，且 `$GITHUB_STEP_SUMMARY` 在無 FLAKY 時沒有多出任何段落。
- developer-agent 的 `/code-review` 對此 PR 無高信心問題。

## 環境事實
- 全套測試只能在 Linux／WSL 跑（`tests/run_all.sh` 第 24–32、84–107 行：native Git Bash 拒絕並退出 3）；`run_all_retry_test.sh` 用假 `uname` 讓沙盒版在 Git Bash 也能跑，但完成標準的全套跑要在 WSL。
- 同一份工作樹不得同時跑兩次套件（`CLAUDE.md` 第 224–225 行）。
- CI：`ubuntu-latest`、先裝 jq（`tests.yml` 第 39–40 行）；`on` 是所有 PR 與 `main`／`v3` 的 push（第 28–31 行）；必要檢查名稱 `run_all`。
- 平台測試是兩個 `run_all` 項目共用一個檔（`platform_test.sh`、`platform_clock_test.sh`，見 `platform_test.sh` 第 335–338 行），所以**隔離的粒度是 `tests/*.sh` 整個檔**：一條名單行會讓該檔內任何失敗只要重跑能過就被饒過（見待裁決 2）。
- `memory/scripts/abf-fast-suite.sh` 在謝馬爾工作區，不在 repo。

## 不做
- 不改 `memory/scripts/abf-fast-suite.sh` 與任何本機 executor／verifier 的跑法（仍單次嚴格）。
- 不改逾時（`PER_TEST_TIMEOUT=300`，第 46 行）、不改任何現有測試檔、不加 skip／xfail。
- 不做「查 `git log` 這條名單行是哪天加的」——只用檢查當天比對到期日。
- 不做 pytest 單一測試層級的隔離（只到 `tests/*.sh` 檔層級）。
- 不做 CI 對 FLAKY 自動開 issue。
- 不改 `docs/TESTING.md`、repo 的 `CLAUDE.md`（見待裁決 1）。
- 不改 `strict_required_status_checks_policy`（審查報告 5.2 第 1 項，另案）。

## 待 developer-agent 裁決
1. **文件落差**：`docs/TESTING.md`（第 10、47、133 行提到 `bash tests/run_all.sh`；該檔由進行中任務持有，本任務不碰）與 repo `CLAUDE.md` 第 130–131 行（寫 CI 跑 `bash tests/run_all.sh`）在本任務合併後會過時一小處。建議：等持有 `docs/TESTING.md` 的任務合併後，另開一個 A 級小任務各補一句「CI 帶 `--retry-failed-once`；FLAKY 要登記到 `tests/quarantine.txt`」；`docs/PITFALLS.md` 不需要加。
2. **粒度**：因 `platform_test.sh` 把整個平台分片都包在一個檔裡，登記它等於隔離整個平台套件。要不要在名單格式加選用的第四欄「測試識別」？本計畫**不加**（超出範圍、也沒有 pytest 單測重跑機制），預設答案：登記整檔但 issue 裡要寫明是哪個測試，到期 14 天內修掉。
3. **`/code-review` 的記錄位置**：預設寫進 PR 描述；若你要另存 ledger，派工訊息請註明。

## 裁決（2026-10-24，developer-agent 助理草擬；與上文衝突時以本段為準）
1. **到期規則用「檢查當天 ≤ 今天+14」，不查 git 歷史**：可由任何人在任何機器上重現，且延期必須改日期、必然進 diff。代價：名單行寫了超過 14 天會當場被拒，不是「到期那天才紅」——這比較嚴，符合維護者「≤14 天」。
2. **名單驗證只在帶旗標時做**，滿足「不帶旗標時與今天完全相同」。CI 帶旗標，所以過期照樣會讓 CI 變紅；本機 `--check-quarantine` 可預檢。
3. **FLAKY 的結論行不含 `all green`**，退出碼 0，以免「過了但有隔離」被讀成「乾淨通過」。
4. **起始名單沒有有效條目**：PR #194 已修掉今天已知的隨機紅，名單從空開始；之後每加一條都要附 issue。
5. **`--check-quarantine` 是新增的第二個旗標**，理由：R35 要在真實 repo 驗名單合法，又不能跑整套（會遞迴）。這是為測試性加的最小介面，維護者的設計描述未列，已於待裁決外明列於此。
6. **`.github/` 修改須經授權**：`CLAUDE.md` 第 227–229 行禁止 executor 改 `.github/`；本任務屬維護者 10-24 核可的 CI 變更，派工訊息明寫「僅授權改 `.github/workflows/tests.yml`」，且 developer-agent 合併前跑 `/code-review`（作法 8）。

## 裁決二（2026-10-24 18:10 developer-agent；以本段為準）
1. `.github/workflows/tests.yml` 不給 executor 改（repo 規則 Never edit）。executor 只做 run_all.sh、quarantine.txt、新測試；verifier PASS 後由 developer-agent 自己在同一分支改 tests.yml（照計畫寫的那幾行），跑 /code-review，再合併。合約裡關於 tests.yml 的案例改由閱卷 diff 驗（README 通例），executor 不寫。
2. `tests/platform_test.sh` 不准進隔離名單：它包著整套 platform pytest，隔離它等於放過任何一個 platform 測試。quarantine 驗證遇到這一行要拒絕並說明；加一條測試。
3. `--check-quarantine` 接受。
4. docs/TESTING.md 與 repo CLAUDE.md 的過時句子另開小任務。車道 L9-tests。

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
