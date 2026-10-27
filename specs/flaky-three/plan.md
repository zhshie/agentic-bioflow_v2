---
id: flaky-three
title: 前端任務全套測試的三支無關紅燈——confirm_launch 計時、jev TC-085 掃到 .pyc、platform 分片逾時——改成確定性（只收緊、不放寬、不跳過、不重試）
tier: A
kinds: backend
lane: L-tests
base: v3
source: memory/handoff/2026-10-27-frontend-speedup-study.md §1.3 與 §4(b) b1
---

# flaky-three

> 本檔由 developer-agent 助理草擬（2026-10-27）。**A 級**：讓測試變確定性只能更嚴，不能更鬆；verifier 通過＋CI 綠後由 developer-agent 自己合併。行號一律是 `origin/v3`（`946da8a`）的行號。**只改測試檔，不碰程式碼與包裝檔**；格式與精神沿用 `memory/dev-plans/flaky-tests.md`（#194，已合併），該件修過的（`test_r30_r36`、`scenario_life`、`test_nextflow_e2e` 固定睡眠、TC-002、tc087／tc071、TC-059）**不重做**。

## 目標
11 件前端任務的 56 次本機全套只有 15 次綠，紅的是與本件無關的 `tests/confirm_launch_test.sh`（31 次）、`tests/jev_test.sh`（31 次）、platform 四支包裝檔 FAIL／TIMEOUT（27 次）〔來源：handoff §1.3〕。本任務把其中**能用測試檔修掉的根因**各自改成「同樣條件永遠同樣結果」，並留下「改前會紅、改後穩定」證據。對使用者的意義：executor 每件省下 60～120 分鐘的「再跑一次全套看是不是又隨機紅」，主導者不必再分辨真紅假紅。

## 維護者原話（verifier 出題用）
- 「修掉或隔離那三支」（handoff §0 第 1 點，10-27 他核可的方向）→ 每支一條「改前紅」、一條「改後穩定」案例；修不掉的才隔離，且要說是哪支、為什麼。
- 「放寬『等待上限』而不是放寬斷言」（`dev-architecture-review-2026-10-24.md` 4(c) c1，flaky-tests 裁決 4 沿用）→ 可以加大「等到條件成立」的上限；不可以改比較值、不可刪斷言、不可加 skip／xfail／retry。
- 「讓測試變確定性只能更嚴」（flaky-tests 檔頭，10-24 定）→ 每處改動 verifier 要能指出「比原本多擋了什麼、少擋了什麼」；少擋任何東西的改動必須對應本檔「裁決」或「待裁決」的一條。
- 隔離規則（`tests/quarantine.txt` 表頭）：每條要 issue＋到期日＋起始日，單期 ≤14 天、總共 ≤28 天；`platform_test.sh`／`platform_shard_*_test.sh`／`platform_clock_test.sh` **不得列入**（`run_all.sh:167`）。issue 由 developer-agent 開，不是 executor。

## 範圍：檔案（只准改這些）
修改（全是測試檔）：
- `tests/confirm_launch_test.sh`（只動 `envbig` 函式第 946–972 行、它的 15 個呼叫行（21 個案例）973–979／988／1015–1023，以及在 1023 行之後新增的比例檢查；第 74 行與第 596–612 行一字不動）
- `tests/jev_test.sh`（只動第 487–488 行）
- `platform/tests/test_station_e2e.py`（只動 `test_tc014…` 第 414–423 行，與第 474、512、666、670、674、877 行的 `httpx.*(` 呼叫）
- `platform/tests/test_launch_e2e.py`（只動第 118、120、125、127、179 行的 `httpx.*(` 呼叫；加一個模組常數）
新增：
- `specs/flaky-three/ledger.md`（executor 進度帳本；每支的「改前紅」「改後穩定」證據與量測表貼這裡）

**不准動（硬規則）**：`hooks/confirm_launch.sh`、`scripts/jev.sh`、`platform/abf_platform/`、`platform/abf_station/` 底下任何檔案；`tests/platform_test.sh`、`tests/platform_shard_2_test.sh`、`tests/platform_shard_3_test.sh`、`tests/platform_clock_test.sh`、`tests/run_all.sh`、`tests/quarantine.txt`（隔離由 developer-agent 依待裁決決定，不在本任務寫）；閘門檔（`.github/`、`spec.md`、`test-case*.md`、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`.claude-plugin/plugin.json`、`platform/pyproject.toml`）；工作區檔 `memory/scripts/abf-fast-suite.sh`、`supervise.js`（見待裁決 3、4）；前端 session 擁有的 `platform/tests/test_web_*.py`。

## 作法
通則同 flaky-tests：每支「先證明會紅（強制條件）→ 改 → 同一條件下綠＋連跑穩定」。**不得**加 skip／xfail／重試裝飾器或迴圈；斷言的比較對象不得變鬆（可以更精確、可以更多）。

### 1. `tests/confirm_launch_test.sh` 的 `envbig`（原因：**已確認並重現**，是測試量了機器而不是量程式）
- 機制：`envbig()`（第 946–972 行）把 60 KB／70 KB／1 MB 的指令餵給 hook，用牆上時鐘（`date +%s%N`，第 962–963 行）量一次，第 967 行 `[ "$ms" -lt "$4" ]` 要求小於 500／1000／1500 ms（第 973–979、988、1015–1023 行）。本機日誌裡這支全部的紅都是 `FAIL: slow (1262～1583 ms)`，落在 TC-051 兩個 1 MB 案例與 TC-032 兩個 1 MB 案例〔來源：11 趟 supervise 的 agent 日誌；27/31 次集中在 10-25 09:51 起的一趟〕。在 `946da8a` 的 WSL 鏡像實測（桌機 16 邏輯核）：**閒置時 1 MB 已要 628～714 ms**（預算 1000 的 63～71%）；開 16 個忙迴圈後 2036～2869 ms，32 個 2701～4207 ms；60 KB 尾端型閒置 123～135 ms，負載下 438～823 ms（也超過 TC-048 的 500 預算）。CPU 時間（`TIMEFORMAT='%U %S'`）在負載下同樣從 ~650 漲到 1500～1700 ms（SMT 共用核心），所以「改量 CPU 時間」不是解。CI 10-24 `40103105713` 這支連紅兩次，原因無法從日誌取出，**只列疑似**（該分支正是新增這批 POL 案例的 relay-warning-polish）。
- 要測的性質其實是兩件事，計畫把它們分開寫、各自用不受負載影響的形式：
  (a) **成本 O(n)**（`relay-warning-hardening` 裁決五第 4 點：「成本 O(n)→TC-047、TC-048…TC-051」）：同一機器同一時刻量到的 1 MB 與 60 KB 時間之**比**，負載對分子分母同等放大。實測各條件下 `tail1m/tail60` 3.4～5.6、`spread1m/spread60` 5.6～11、`lookalike1m/tail60` 11～16；若演算法是平方，16.7 倍大小至少 50 倍以上。
  (b) **在 hook 逾時前答完**（註解 944–945 行「the hook must answer in time (its timeout lets a command through)」）：第 604–608 行已釘每個安全閘的 `timeout >= 30s`，所以「答得完」的硬上限是 30 s 的一部分，不是 1 s。
- 改法：
  1. `envbig` 拿掉第 4 個參數 `<limit ms>` 與第 967 行；改成在函式上方定義 `BIG_CEIL_MS=10000`（註解寫明＝第 604–608 行 30 s 下限的三分之一），第 967 行換成 `[ "$ms" -lt "$BIG_CEIL_MS" ] || { ok=0; why="$why slow"; }`；量測與 `ok (NNN ms)` 的輸出照舊。每次量到的 `ms` 另存成 `eval "MS_${3}_${2}=$ms"`（`<kind>` 與變數名組成的純變數，不用關聯陣列）。15 個呼叫行各刪掉那一個數字參數，其餘引數（含 must-contain／must-not-contain）**一字不改**。
  2. 第 1023 行之後新增比例檢查（每行一個 `printf '%-58s '` 標籤＋ok／FAIL，與檔內格式一致；除以 0 時把分母當 1）：
     - 對 `V` 各一條 `TC-051 ${V#NF_RELAY_} O(n): 1 MB tail / 60 KB tail <= 40`：`MS_tail1m_V / MS_tail60_V`；
     - 對 `V` 各一條 `TC-051 ${V#NF_RELAY_} O(n): 1 MB spread / 60 KB spread <= 40`：`MS_spread1m_V / MS_spread60_V`；
     - 一條 `TC-032 O(n): 1 MB look-alikes / 60 KB tail <= 40`：`MS_lookalike1m_NF_RELAY_PEER_PREFIXES / MS_tail60_NF_RELAY_PEER_PREFIXES`。
     FAIL 訊息印出兩個 ms 與比值。
  3. 比原本**多擋**：平方成本（原本 1000 ms 預算在快機器上擋不住 60 KB 以下才明顯的平方）；hook 慢到接近逾時。**少擋**：絕對值 1000 ms 這個數字（改為 10000）——這是本檔唯一一處比較值變大，**必須經待裁決 1 核准才能派工**。
- 檔內沒有 `set -o pipefail`（`jev_test.sh` 才有），新增行照樣不得用 `grep -P`、`xargs -r`、`mapfile`、`declare -A`（`tests/portable_userland.sh:72–76` 掃 `tests/*.sh`）。

### 2. `tests/jev_test.sh` TC-085（原因：**已確認並重現**，測試掃到不屬於程式碼的檔案）
- 機制：第 487 行 `grep -rli jev "$ROOT/platform"` 遞迴掃**磁碟上所有**檔案，含被 `.gitignore` 忽略的 `__pycache__/*.pyc`（`.gitignore` 第 1–2 行）與二進位。`test_web_board.py`、`test_web_settings.py`、`test_web_running.py` 編譯出的 `.pyc` 位元組裡碰巧含 `jev`（大小寫不分），`grep -rli` 各算一個檔 → `got '1'/'2', wanted '0'`〔來源：agent 日誌 6 次同訊息；`946da8a` 鏡像重現：`py_compile` 三個檔後 `grep -rli jev platform` 列出 3 個 `.pyc`〕。`platform_test.sh:346` 自己有 `PYTHONDONTWRITEBYTECODE=1`，`.pyc` 來自同一鏡像裡並行的單檔 pytest（`abf-fast-suite.sh:39` 的 `--pytest` 路徑沒設該變數）；10-25 加的 `git clean -qfdx`（`abf-fast-suite.sh:24`）只清開跑前，清不到全套進行中寫入的。
- 改法：第 487 行改成只掃「會被提交的檔」，形式沿用同檔第 485 行 TC-020 已在用的寫法：
  `t "TC-085 nothing under platform/ mentions jev" "$(cd "$ROOT" && git ls-files -co --exclude-standard -- platform | xargs grep -lIi jev 2>/dev/null | sort | tr '\n' ' ')" ""`
  （`-c` 已追蹤＋`-o` 未追蹤、`--exclude-standard` 去掉被忽略的、`-I` 跳過二進位、`-i` 保留原本的大小寫不分；期望值由「數量 0」改成「清單為空」，失敗時直接列出違規檔名。）第 488 行 TC-075 同形改寫（`-- hooks`），讓兩行一致。`platform/` 底下沒有含空白的檔名（`git ls-tree -r origin/v3 platform` 查過 0 個），`xargs` 安全；`-- platform` 保證清單非空，不會讓 `grep` 讀 stdin。
- 比原本**多擋**：新增但尚未 `git add` 的 `.py` 一樣會被抓（`-o`），失敗訊息有檔名。**少擋**：被 `.gitignore` 忽略的檔與二進位——它們不是 `platform/` 的程式碼，spec 原文「搜尋 `platform/`」（`specs/015-jev-triage/test-case.md:128`）指的是程式碼；在 ledger 寫一句。
- 檔內有 `set -uo pipefail`（第 18 行）：新增行**不得**把管線接到 `grep -q`（`tests/no_pipefail_grep_q_test.sh` 會抓）；上面的寫法沒有 `-q`。

### 3. platform 四支包裝檔（原因：**三個來源，分開處理**）
- 3a. **CI 的 `platform_test.sh TIMEOUT 300s`（6 次）全部在 10-24 14:00Z 之前**，即 PR #200 把平台測試拆成四個項目之前〔來源：`gh run list` 30 筆失敗逐一看 `--log-failed`；#200 `mergedAt` 2026-10-24T14:00:14Z〕。拆分後最近一次綠的 v3（`40442460318`）四支分別 163／111／176／196 s。**已修，本任務不做**。
- 3b. **`test_station_e2e.py::test_tc014_idle_polls_end_quietly_and_keep_the_last_contact_moving`**（CI 兩次：`39742927299` 10-22、`40232150460` 10-25，兩次都讓 `platform_clock_test.sh` 變 FLAKY 而它不得隔離）——原因由讀碼推得：第 416–420 行在**固定 4.5 秒**窗內每 0.25 s 讀 `agents.last_seen_at`，第 421 行要求看到 ≥3 個不同值；心跳 `H=2`、長輪詢 `POLL=2`（第 24–25 行），4.5 秒理論上只容得下 2～3 次聯絡，任何一次 poll 晚個幾百毫秒就只剩 2 個值。
  改法（斷言不變，窗變成上限）：迴圈條件改為「跑到**至少 4.5 秒**且 `len(seen) >= 3` 就停；最晚 30 秒」，即保留原本 4.5 秒的最短觀察（第 422–423 行對代理輸出「沒有 Traceback／cannot reach／stopped:／will not start」的檢查因此覆蓋的時間只會更長不會更短），再加 `deadline = time.time() + 30`；第 421 行 `assert len(seen) >= 3` 與訊息原樣。這是「等待上限放寬，斷言不動」。
- 3c. **`httpx` 預設 5 秒逾時**：CI `40099957808`（10-24，拆分前的重負載）`test_launch_e2e.py::test_tc020… httpx.ReadTimeout: timed out`。`test_launch_e2e.py` 第 118、120、125、127、179 行與 `test_station_e2e.py` 第 474、512、666、670、674、877 行都是不帶 `timeout=` 的頂層 `httpx.post/put/get/request`，venv 裡 `httpx 0.28.1` 的 `DEFAULT_TIMEOUT_CONFIG = Timeout(timeout=5.0)`。
  改法：兩檔各加模組常數 `HTTP_TIMEOUT = 60  # seconds; httpx defaults to 5 s, which a loaded runner exceeded (CI run 40099957808)`，上述 11 個呼叫全部帶 `timeout=HTTP_TIMEOUT`（跨行的呼叫也要）。狀態碼與回傳內容的斷言一字不改。其他檔的同型呼叫（`test_cli.py` 4、`test_pat.py` 5、`test_station_envs.py` 2、`test_oauth_mcp.py` 2、`test_confirm_page.py` 2、`oauth_harness.py` 2、`test_human_channel.py`／`test_oauth.py`／`test_review_fixes.py`／`test_web_login.py` 各 1）**沒有紅的證據，不在本任務**，見待裁決 2。
- 3d. **本機 900 s TIMEOUT（4 次，其中 2 次在拆分後的 10-25）與 573～893 s 的紅／險綠**：兩套全套並跑時每支平台項目各開 4～5 個 pytest 行程再各起 Nextflow JVM，是**容量**問題（同一套在 CI 單跑 163 s）。不是任何一條測試寫錯，測試檔修不掉；量測交 executor（下節），決定交待裁決 3。

## 失敗先行測試
這件事的「失敗先行」是**先證明舊寫法會紅**，每支一條，指令與輸出貼進 ledger，不進 commit：
- `confirm_launch_test.sh`：強制條件＝負載。在鏡像裡 `for i in $(seq 16); do ( while :; do :; done ) & done`（記下 PID，結束後 `kill`），同時跑 `bash tests/confirm_launch_test.sh`：舊檔應出現 `FAIL: slow (…ms)`（10-27 實測 1 MB 在此條件下 2.0～2.9 s，100% 超過 1000）；新檔同條件全綠。另外兩個**反向**強制條件證明新檢查有牙：在暫存副本把 `H` 換成一支包裝腳本——(i) 讀完 stdin 後 `sleep` 與位元組數平方成正比（60 KB 約 0.03 s、1 MB 約 8.3 s）再轉呼叫真 hook → 新檔的比例檢查必紅（比值約 60 > 40）而 10 s 上限仍過；(ii) 固定 `sleep 11` → 新檔的 `slow` 必紅。
- `jev_test.sh`：在暫存副本（或鏡像）執行 `python3 -c 'import py_compile; py_compile.compile("platform/tests/test_web_board.py", cfile="platform/tests/__pycache__/test_web_board.cpython-310.pyc", doraise=True)'` → 舊檔 `TC-085 … FAIL: got '1', wanted '0'`；新檔 `ok`。**正向控制**：放一個未追蹤、未忽略的 `platform/zz_probe.py` 內含 `jev` → 新檔必紅且訊息列出 `platform/zz_probe.py`；刪掉後綠。
- `tc014`：在暫存副本於第 416 行迴圈前插入 `time.sleep(3)`（模擬第一次 poll 晚到）→ 舊寫法只剩 1.5 秒窗、必紅；新寫法（上限 30 s）仍綠。這段插入只存在於暫存副本。
- `httpx` 逾時：「改前紅」以 CI 日誌 `40099957808` 的 `httpx.ReadTimeout` 原文＋venv 內 `python -c 'import httpx; print(httpx.__version__, httpx._config.DEFAULT_TIMEOUT_CONFIG)'` 的輸出為證（無法在不改產品的情況下強制伺服器慢 5 秒）；「改後」以完成標準 5 的 grep 規則與連跑為證。ledger 明寫這條是「日誌證據，不是強制重現」。

## 完成標準（done when）
1. 上節每一條「改前紅」「改後綠」都在 `specs/flaky-three/ledger.md` 有指令與輸出。
2. `confirm_launch_test.sh`：負載下（16 忙迴圈）連跑 N=10 全綠、閒置連跑 N=10 全綠，貼每次的 `ok (NNN ms)` 行與比例檢查行；兩個反向強制條件各一次紅。
3. `jev_test.sh`：鏡像裡**先放進** 3 個含 `jev` 的 `.pyc`（作法 2 的 `py_compile`，三個檔），不清掉，連跑 N=20 全綠；正向控制一次紅。
4. `tc014`：`test_station_e2e.py` 整檔 N=5（`side` fixture 四場景一起起，不能只挑一個）；再「同時開 4 份」壓測一次：`for k in 1 2 3 4; do pytest tests/test_station_e2e.py -q -p no:cacheprovider & done; wait` 全綠。`test_launch_e2e.py` 整檔 N=3（需要 Java 與 Nextflow；沒有就在 ledger 寫明「本機沒有、交 CI」）。
5. 可機械檢查的規則：
   - `grep -nE '^ *envbig ' tests/confirm_launch_test.sh` 列出 15 行，每行的第 4 個引數都不再是純數字；`grep -c 'BIG_CEIL_MS' tests/confirm_launch_test.sh` ≥ 2；比例檢查 5 行存在（`grep -c 'O(n)' tests/confirm_launch_test.sh` = 5）。
   - `sed -n 487,488p tests/jev_test.sh | grep -c 'git ls-files -co --exclude-standard'` = 2；整檔沒有 `grep -rli`。
   - `grep -nE 'httpx\.(get|post|put|delete|patch|request)\(' platform/tests/test_launch_e2e.py platform/tests/test_station_e2e.py` 列出的每一處（含其後兩行）都含 `timeout=HTTP_TIMEOUT`。
   - `git diff | grep -nE '^\+.*(skip|xfail|flaky|retry|rerun)'` 無輸出（英文註解裡的敘述性用法除外，ledger 說明）。
6. 量測（不是修改）：在鏡像單獨跑一次 `ABF_PLATFORM_PART=1 bash tests/platform_test.sh`、`…=2`、`…=3`，把每個 shard 輸出最後的 `N passed in X s` 行整理成表（shard 檔名清單可由 `ABF_PLATFORM_LIST=1` 列出）貼進 ledger，供待裁決 3 使用。
7. 改動範圍證據：`git diff --stat` 只列「範圍：檔案」那些檔（verifier 依 README 通例自己重跑核對）。
8. 下列既有守門測試仍綠並在 ledger 點名（PRECHECK 第 3 條）：`tests/no_pipefail_grep_q_test.sh`、`tests/portable_userland.sh`、`tests/run_all_count_test.sh`、`tests/constitution_scope_test.sh`（第 274 行四支名單不動）、`tests/hooks_fail_closed_test.sh`／`tests/gates_without_jq_test.sh`（hook 沒動）、`jev_test.sh` 自己的 TC-020（第 485 行）與 TC-044（第 397 行）、`platform/tests/test_scope.py::test_tc072`（新增行沒有個人／叢集路徑）。`docs/TESTING.md:520` 釘的 `tests/confirm_launch_test.sh:74` 不受影響（改動都在第 940 行以後），verifier 看一眼第 74 行仍是原句。
9. 全套測試綠（鏡像 `bash tests/run_all.sh`；CI 綠）。

## 環境事實
（行號為 2026-10-27 讀 `origin/v3`，`946da8a`）
- `run_all.sh` 逐檔序跑（第 404–431 行），每檔上限 `PER_TEST_TIMEOUT=300`（第 46 行）；CI 用 `--retry-failed-once`（`.github/workflows/tests.yml:51`），本機 `abf-fast-suite.sh:57` 不帶 retry、`:42` 設 `--timeout 900`、`:46` 最多 2 套同時。
- 平台四支：`platform_test.sh` 第 49 行 `PART`、第 57–88 行 `set_platform_parts`（SHARDS_1 四行＋REST_1 28 檔）、第 370–391 行每 shard 一個 pytest 行程同時起、`LAST` 兩檔只在 `clock` 部分逐一單跑。第 346 行 `PYTHONDONTWRITEBYTECODE=1`。
- hook 逾時下限 30 s 的既有檢查：`confirm_launch_test.sh:604–608`（`#29 every … entry has timeout >= 30s`）。
- `tests/portable_userland.sh:72–76` 對 `tests/*.sh` 只掃 `grep -P`；其 RULES 表（第 28–45 行）列出的其他 GNU 專用寫法（`xargs -r`、`mapfile`、`declare -A`、`timeout`…）雖不掃 tests/，本任務新增行一律避開。
- 暫存複本重現用法：WSL 內 `git clone -q /mnt/c/Users/marvi/Desktop/agentic-bioflow/agentic-bioflow_v2 ~/abf-flaky3 && cd ~/abf-flaky3 && git checkout -q -f --detach origin/v3`（草擬時已建，可直接用；不要在真 repo 或別人的 `~/abf-mirror/*` 動）。鏡像跑法：`~/.local/bin/abf-fast-suite <worktree> --only confirm_launch`。
- 草擬者實測過：作法 1 的計時（三種負載）、作法 2 的 `.pyc` 命中與 `git ls-files` 結果、`confirm_launch_test.sh` 閒置整檔 40 s 全綠；作法 3b、3c 的機制是**讀碼推得**，症狀有 CI 日誌；3d 只有時長數據。若 executor 的重現與本文不符，以實測為準並回報。

## 不做
- 不加 `skip`／`xfail`／`flaky`／重試；不寫 `tests/quarantine.txt`（隔離由 developer-agent 依待裁決 1 決定並開 issue）。
- 不改 `hooks/confirm_launch.sh`、`scripts/jev.sh`、任何 `platform/abf_*/` 程式碼。
- 不改 `platform_test.sh` 的分片、不加新的 run_all 項目、不調 `run_all.sh` 與 `abf-fast-suite.sh` 的逾時或 slot（待裁決 3、4）。
- 不動 `test_web_*.py`（前端 session 擁有）；不動 flaky-tests 已修的七處。
- 不處理 3c 列出的其他檔同型 `httpx` 呼叫（待裁決 2）。
- 不改 `specs/*/test-case*.md` 的字句，包括 `relay-warning-hardening` 的「都 < 1 秒」（待裁決 1 決定如何對應）。

## 裁決
1. A 級；專長守則用 `backend`；verifier 通過＋CI 綠後由 developer-agent 自己合併。
2. 「放寬等待上限，不放寬斷言」是唯一允許的時序修法；3b、3c 都屬此類。
3. 證據以「強制條件」優先、「連跑 N 次」其次；3c 只有日誌證據，接受並在 ledger 標明。
4. 本任務不做工具化（flakefinder 等），用 shell 迴圈連跑。

5. **（10-27 developer-agent，待裁決 1～4 結案）**
   - 待裁決 1 → **(A) 核准**：維護者 10-27 親自選「照建議改」（O(n) 比例檢查＋`BIG_CEIL_MS=10000` 硬上限，hook 逾時 30 s 的三分之一）。作法 1 照做；`relay-warning-hardening` 的「都 < 1 秒」不改字句，在 ledger 寫明由本裁決取代。
   - 待裁決 2 → **不擴大**：其他 11 檔的 `httpx` 呼叫不在本任務，等真的紅再說（避開其他車道在動的檔）。
   - 待裁決 3 → **本任務只交付量測表**（完成標準 6），工作區怎麼調由 developer-agent 看表後決定。
   - 待裁決 4 → developer-agent 已在工作區處理（`PYTHONDONTWRITEBYTECODE=1`、本機全套帶 `--retry-failed-once`），executor 不必管。

## 待 developer-agent 裁決
1. **作法 1 的 1000→10000 ms**：比例檢查是新增、只會多擋，但 `BIG_CEIL_MS=10000` 把 21 個案例的絕對預算從 500／1000／1500 放大到 10000，而 `relay-warning-hardening` 出題時寫的是「都 < 1 秒」。三個選項：(A) 核准本檔作法（量 O(n) 比例＋hook 逾時三分之一的硬上限；10-27 實測證明絕對值在閒置桌機已吃掉 63～71% 預算、負載下必超）；(B) 不核准，`confirm_launch_test.sh` 進 `tests/quarantine.txt`（它不是平台包裝檔，可列）＋開 issue，接受本機不帶 retry 的全套仍會紅；(C) 單純把預算放大到某個數（仍與負載相關，不建議）。**不核准 (A) 就把作法 1 整段從本任務拿掉**，不要讓 executor 自己選。
2. 3c 其餘 11 個檔共 23 個不帶 `timeout=` 的頂層 `httpx` 呼叫是否一併改成 `timeout=HTTP_TIMEOUT`？同型、無紅的證據；改了會碰到其他車道可能在動的 `test_pat.py`、`test_confirm_page.py`。建議另開一件小任務，或等它們真的紅。
3. **本機平台項目的 900 s 逾時**：測試檔修不掉。選項：(A) 工作區 `abf-fast-suite.sh:42` 的 `--timeout 900` 對平台四支放到 1800（等待上限，政策允許；但 run_all 的 `--timeout` 是全檔共用的一個數）；(B) 在 `platform_test.sh` 加一個預設不變的環境變數限制同時起的 shard 數，由工作區 runner 設定（要先看完成標準 6 的量測表才知道有沒有用）；(C) 照 handoff b1.3 把全套改成「每件只跑一次、背景跑」，從需求端減少同時跑的套數。本任務只交付量測表。
4. 工作區跟進（不是 executor 的事）：`abf-fast-suite.sh:39` 的 `--pytest` 路徑補 `PYTHONDONTWRITEBYTECODE=1`，讓鏡像不再被單檔 pytest 寫進 `.pyc`（作法 2 修完後 TC-085 已不受影響，這條只是衛生）；`abf-fast-suite.sh:57` 本機全套是否也帶 `--retry-failed-once`（handoff b1.2），讓本機與 CI 同一套判準。

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
