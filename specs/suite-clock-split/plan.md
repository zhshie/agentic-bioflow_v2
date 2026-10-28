---
id: suite-clock-split
title: 把平台測試的「時鐘」項目拆成兩個（讓每個 run_all.sh 項目實測都 ≤ 180 秒），並更正 suite-speed 帳本一句拿分片秒數總和當牆鐘的話與 tests.yml 一行過期註解
tier: A
kinds: backend
lane: L13-tests
branch: test/suite-clock-split
base: v3（`origin/v3` @ 74e11ed，即 PR #255 suite-speed 合併後；查證日 2026-10-28；所有行號與名字都取自該版本）
source: suite-speed 的 verifier 報告（needs-human 第 2、4、5 點）：`tests/platform_clock_test.sh` 實測 205～213 秒，對 300 秒的單項上限只剩約 90 秒餘裕；帳本一句話把「各檔秒數總和」當牆鐘比較；`.github/workflows/tests.yml` 第 37 行註解過期
---

# suite-clock-split

> 本檔由 developer-agent 的計畫幫手草擬（2026-10-28），**A 級：只動測試基礎設施**。接續 `suite-speed`（PR #255，已合併進 v3）：它把平台 pytest 切成 8 份數字分片，但依裁決 D1 **刻意沒拆時鐘項目**，合併後它成了全套最慢的一項（205～213 秒），其餘八份最慢 126～160 秒。本片只處理三件小事：拆時鐘項目、更正一句帳本、更新一行 CI 註解（只准註解）。
> **不准碰**：`web*.py`、`static/`、`DESIGN.md`、`test_web_*`（另一個 session 的車道）、憲法文字（`.specify/memory/constitution.md`）。
> 註：frontmatter 的 `kinds` 寫 `backend`（不加方括號）。`memory/scripts/build-dev-plans.py` 用逗號切字串（第 36～39 行），方括號會被當成 kind 名的一部分、找不到 profile，專長守則段就貼不上。

## 目標
讓 `bash tests/run_all.sh` 的**每一個項目**（現有 9 個平台項目＋其他所有 `*.sh`）單獨實測都 ≤ 180 秒，對 300 秒單項上限留一半以上餘裕。作法：把「時鐘」項目（現在是 `test_station_e2e.py`、`test_nextflow_e2e.py` 兩個檔一個接一個）拆成兩個項目，**每個項目一個檔**；測試一個都不刪、不跳過、不弱化，整體跑的測試集合前後完全相同。另外順手把兩處已知的文字錯誤改對。

對使用者的意義：全套在忙碌的桌機上不再因為最慢的一項貼近上限而偶發 TIMEOUT；ledger 與 CI 註解不再給後人錯的數字。

## 維護者原話（verifier 出題用）
(A 級，無維護者原話；來源＝suite-speed verifier needs-human 第 2、4、5 點)
- needs-human 第 2 點：時鐘項目實測 205～213 秒，餘裕只剩約 90 秒（單項上限 300 秒）。→ SC-01…SC-09、完成標準 1、2
- needs-human 第 4 點：`specs/suite-speed/ledger.md` 把各檔秒數總和（3249 秒）當成牆鐘去比。→ SC-12、完成標準 4
- needs-human 第 5 點：`.github/workflows/tests.yml` 第 37 行註解過期。→ SC-13、完成標準 5
- 派工時加的限制：拆分後測試集合必須與拆分前完全相同（要有測試案例）；CI 設定改動需維護者核准，所以本片對 `.github/` 只准改註解，超出就 BLOCKED。→ SC-01、SC-02、SC-13、「不做」

## 現況（讀 `origin/v3` @ 74e11ed 與 `specs/suite-speed/ledger.md` 推得；執行者要在作法 0 重量，不要照抄這裡的數字）
**哪個項目超過**：`tests/platform_clock_test.sh`（把 `ABF_PLATFORM_PART=clock` 交給 `tests/platform_test.sh`）。`tests/platform_test.sh` 第 62 行 `LAST="tests/test_station_e2e.py tests/test_nextflow_e2e.py"`；第 133～134 行（`selected_shards` 內）對 `clock`／`all` 各印一行 `alone: <檔>`；第 409～415 行 `for f in $LAST` 把兩個檔**一個接一個**各自跑成一個 pytest 行程（為了看時鐘的測試不能和別的行程搶 CPU，第 376～383 行註解）。

**實測（全部取自 suite-speed 帳本）**：
| 項目 | 秒數 | 出處（帳本） |
|---|---|---|
| `platform_clock_test.sh` 單獨跑 | 213 | 「Single item walls」表（負載約 2.6～3.5） |
| 同上，完整 `run_all.sh` | 205 | 「Full suite at 0f9af82」與其輸出行（負載約 0.2） |
| 同上，完整 `run_all.sh`（另一趟） | 209 | 帳本 341 行（負載約 8） |
| `test_station_e2e.py` 單獨 | 約 68（`--durations` 加總 95、106） | 帳本 369 行；`--durations` 兩份清單 |
| `test_nextflow_e2e.py` 單獨 | 約 110（`--durations` 加總 145、151） | 同上 |
| 其餘八份數字分片 | 最慢 160（單項）；完整套件裡 70～126 | 帳本 369 行；完整套件輸出 |

**所以時鐘項目＝兩個檔的秒數相加**（約 68＋110＝178，加啟動共約 205～213）。兩個檔各自都遠低於 180 秒，分成兩個項目後最慢的應是 `test_nextflow_e2e.py` 那個（單獨約 110～150 秒，隨負載漂移）。**這是預期，不是已證；作法 0 重量**。

**拆開不會破壞「看時鐘」的保護**：這兩個檔本來就是一個接一個、各自一個 pytest 行程、前後沒有別的行程在跑；`run_all.sh` 一次只跑一個項目，所以拆成兩個項目後它們仍然各自獨佔機器。

## 範圍：檔案（只准改這些；另加 `specs/suite-clock-split/ledger.md` 為 executor 帳本）
修改：
- `tests/platform_test.sh`（`ABF_PLATFORM_PART` 合法值與錯誤訊息，第 46～53 行；`LAST` 的定義，第 62 行；`selected_shards` 內 `clock`／`all` 分支，第 118～134 行；執行迴圈第 404～415 行；註解第 376～389 行。**第 `SHARDS_1`…`SHARDS_8`、`REST_1`…`REST_8` 與輪流分配規則一個字都不改**）
- `tests/platform_clock_test.sh`（只改檔頭註解：第 1 行的「The fourth run_all.sh entry」已過期；說明它現在只選 `clock`＝`test_station_e2e.py`，另一個檔在 `platform_clock_2_test.sh`）
- `tests/run_all.sh`（第 174 行的隔離名單 `case` 與第 363～364 行兩條 awk 樣式，加入新包裝檔名；第 355 行附近註解若寫死個數就改成不寫個數）
- `tests/quarantine.txt`（只改第 12 行註解，保留現有字面 `platform_test.sh`、`platform_shard_2_test.sh`、`platform_shard_3_test.sh`、`platform_clock_test.sh` 與 `platform_shard_<n>_test.sh`，再加 `platform_clock_2_test.sh`——`run_all_retry_test.sh` 的 PS-24 逐字檢查這幾個字面，不能掉）
- `tests/run_all_shard_test.sh`（第 43、46 行的 grep 樣式、第 51 行的名單，把新包裝檔算進去；見「受影響的既有斷言」）
- `tests/run_all_retry_test.sh`（只新增案例；第 459 行那種逐一列名單的既有斷言只准**加名字**，不准刪斷言）
- `platform/tests/test_platform_parts.py`（見「受影響的既有斷言」）
- `docs/TESTING.md`（第 13、129、140、169 行的項目清單）
- `docs/PLATFORM.md`（第 766 行附近的指令清單與其註解）
- ~~`.github/workflows/tests.yml`~~（依裁決 2 移出範圍：不准改）
- `specs/suite-speed/ledger.md`（**只改第 26 行那一句**，見「作法 4」）
新增：
- `tests/platform_clock_2_test.sh`（形狀同 `tests/platform_clock_test.sh`：`export ABF_PLATFORM_PART=clock2`、`exec bash "$HERE/platform_test.sh" "$@"`）
- `specs/suite-clock-split/ledger.md`

**不准動（硬規則）**：
- 車道外：`web*.py`、`platform/abf_platform/web*.py`、`static/`、`DESIGN.md`、`PRODUCT.md`、`platform/tests/test_web_*`（它們只會出現在清單的字串裡）。
- `.specify/memory/constitution.md`（憲法字面「四個入口」過期，另案，本片不碰）、`hooks/*`、`platform/abf_*`、`platform/tests/` 除 `test_platform_parts.py` 以外的檔案、`.claude-plugin/plugin.json`、`docs/ROADMAP.md`。
- `.github/` 底下除上列註解行之外的**任何**東西（含 `timeout-minutes`、矩陣份數、`--timeout`）。
- 任何平台測試的**內容**：本片只搬「哪個檔在哪個項目」，不加速、不刪、不改個別測試。

## 作法
### 0. 先量（改任何檔之前；在 WSL／Linux，暖快取，從有 `.git` 的 clone 跑，記進 ledger）
1. 機器：`nproc`、`/proc/loadavg`（前後各一次）、`git rev-parse HEAD`。
2. **集合基準**（SC-01 的「前」）：
   ```
   ABF_PLATFORM_PART=all ABF_PYTEST_ARGS="--collect-only -q" bash tests/platform_test.sh > /tmp/before-collect.out 2>&1
   grep -E '^platform/tests/|^tests/.*::|::' /tmp/before-collect.out | sort > /tmp/before-ids.txt ; wc -l /tmp/before-ids.txt ; sha256sum /tmp/before-ids.txt
   ```
   （節點 id 的格式以實際輸出為準，pytest 的 `-q` 會印 `<檔>::<測試>` 一行一個。）把行數與 sha256 貼進 ledger，節點 id 全文存 `/tmp/before-ids.txt` 備用。**沒有 Java 時這步仍可跑**（收集不執行測試），但 `tests/platform_test.sh` 會先檢查 Java；本機 `E2E SKIPPED` 時照 `SS-08` 的既有做法（沿用 `warm` fixture）。
3. **現況每項單獨牆鐘**，循序、各量一次：`for e in platform_clock_test platform_shard_5_test platform_test; do ( time bash tests/$e.sh ) 2>&1 | grep -E '^real|passed|failed'; done`；另量兩個檔各自的單獨秒數：`ABF_PLATFORM_PART=clock ABF_PYTEST_ARGS="--durations=5" bash tests/platform_test.sh | grep -E 'passed|^[0-9.]+s '`（`test_station_e2e.py` 與 `test_nextflow_e2e.py` 要分開量，各自跑一次）。把秒數與負載貼進 ledger。
4. **若兩個檔其中任何一個單獨量到 > 180 秒**（乾淨機器），**停止，BLOCKED 回報**：那表示光拆這兩個檔不夠，要動檔內容或別的做法，超出本片。

### 1. 新結構（決定）
- **時鐘一分為二，檔案各占一個項目，順序不變**：
  - `ABF_PLATFORM_PART=clock` → 只有 `tests/test_station_e2e.py`（原 `LAST` 的第一個）。
  - `ABF_PLATFORM_PART=clock2` → 只有 `tests/test_nextflow_e2e.py`（原 `LAST` 的第二個）。
  - `ABF_PLATFORM_PART=all` → 八份數字分片，然後 `clock`，然後 `clock2`（與現在「分片之後兩個檔一個接一個」的順序、獨佔方式完全相同）。
  - 為什麼 `clock` 保留舊名而新的叫 `clock2`、包裝檔叫 `platform_clock_2_test.sh`：`platform_clock_test.sh` 的名字被 `run_all_retry_test.sh`（TC-089、PS-22、PS-24）、`test_platform_parts.py`、`tests/quarantine.txt`、docs 逐字引用，改名會連動一大片；新增一個名字只需加不改。
- **`ABF_PLATFORM_PART` 的合法值**：`1`～`8`、`clock`、`clock2`、`all`。檢查式照現在的樣子，把 `clock|all` 擴成 `clock|clock2|all`；錯誤訊息改成 `FAIL: ABF_PLATFORM_PART must be 1 to $PLATFORM_PARTS, clock, clock2 or all, not '$PART'`。預設仍是 `1`。
- **`LAST` 變數**：保留名字與內容（兩個檔的聯集，`set_platform_parts` 第 104 行的 `listed=` 靠它判斷「已被點名」，**REST 的輪流分配因此完全不變**）；另設 `LAST_1="tests/test_station_e2e.py"`、`LAST_2="tests/test_nextflow_e2e.py"` 並在註解寫明 `LAST` ＝ 兩者合併。`selected_shards`（第 118～134 行）：`clock` 分支印 `alone: $LAST_1`、`clock2` 分支印 `alone: $LAST_2`、`all` 兩者依序都印。`ABF_PLATFORM_LIST=1` 的輸出格式（`shard: <檔…>`／`alone: <檔>`）、空的 REST 不印、`wait`／`$LOG.$n` 合併、摘要行 `platform tests: pytest exit …`、CI 不准 skipped 的規則——**全部不變**。
- **執行迴圈**（第 404～415 行）：`clock` 與 `clock2` 都不跑數字分片（原本只有 `clock` 跳過）；`clock` 跑 `LAST_1`，`clock2` 跑 `LAST_2`，`all` 兩者依序各自一個 pytest 行程。
- **新包裝檔** `tests/platform_clock_2_test.sh`：與 `tests/platform_clock_test.sh` 同形，檔頭註解說明「不是第二份拷貝，只選份數；檔名由 `tests/run_all.sh` 拒絕隔離的樣式固定」。
- **bootstrap 不動**：所有項目共用同一份 venv 與下載快取；不新增快取、不抽共用腳本。

### 2. `tests/run_all.sh` 的樣式（不是 CI；在車道內）
三處都要認得新名字，否則它會（a）可以被隔離（把「平台測試失敗放行」的保護洞開）、（b）在 `--shard I/N` 被當成權重 1 的普通檔而不是權重 40 的平台包裝檔，使 CI 分片不均：
- 第 174 行：`platform_test.sh|platform_clock_test.sh|platform_shard_*_test.sh` → 加上 `platform_clock_2_test.sh`。
- 第 363、364 行：`platform_(test|clock_test|shard_[0-9]+_test).sh` → `platform_(test|clock_test|clock_2_test|shard_[0-9]+_test).sh`（兩行要一致）。
- `tests/run_all_shard_test.sh` 第 43、46 行用同一個樣式數包裝檔，同步改。**不是弱化**：它釘死的是「哪些檔算平台包裝檔」，檔增加了。

### 3. `.github/workflows/tests.yml` 第 36～38 行註解（**只改註解**）
過期之處（讀 `origin/v3` 第 36～38 行）：
- 「**The four platform wrappers** … go one to each part」：suite-speed 之後平台包裝檔是 9 個，本片後是 10 個；CI 矩陣仍是 4 份，所以不是「一份一個」，而是每份 2～3 個（權重 40 的貪婪分配）。
- 括號裡的秒數「clock ~196 s, shard_3 ~176, test ~163, shard_2 ~111」是 PR #200 時代的量測，現在每個項目都短得多（見 suite-speed 帳本），已不是事實。
改寫成**不含個數也不含秒數**的說法（避免再過期），例如：
`#   - Split: bash tests/run_all.sh --shard I/4 (see the SHARD block in tests/run_all.sh). The platform wrappers (tests/platform_test.sh, platform_shard_<n>_test.sh, platform_clock_test.sh, platform_clock_2_test.sh) are the heavy files and are dealt out first, one at a time to the part with the least weight so far; the other test files fill the parts up evenly; before, one job ran everything in series.`
（第 38 行後半「~17-19 min」那句也是歷史量測，一併去掉或改成不含數字。第 39 行起的「Each part keeps --retry-failed-once…」不動。）
**硬限制**：`git diff -U0 origin/v3 -- .github/` 裡每一個被加或減的內容行（排除 `---`、`+++`、`@@`）都必須以 `#` 開頭。要動任何一個非註解字元（`timeout-minutes`、矩陣、job 名、`--timeout`）→ **BLOCKED**，回報，不要自己改。

### 4. 更正 `specs/suite-speed/ledger.md` 第 26 行那一句
現在的句子：「…this repeat sums to 3249.2 s over 120 files, within 12 percent of it and within 30 percent of the plan's 580 s wall (D4, D9), so 8 parts stands.」
錯在：3249.2 秒是 `--durations=0` 對 120 個檔的 `call`＋`setup`＋`teardown` 秒數**逐項加總**，而那趟是 16 個 pytest 行程同時跑，加總 ≠ 牆鐘；牆鐘是同一段指令的 `real`。帳本自己兩處記載：第一趟 `real 9m46s`（＝586 秒，加總 2908.3 秒），重複那趟 `real 12m38s`（＝758 秒，加總 3249.2 秒）。計畫的「580 秒」是各項目單獨牆鐘之和（170.5＋122.2＋123.5＋163.3），與逐檔加總本是兩個東西，不能互比。
改法：**只改這一句**，寫成大意「這趟逐檔秒數加總 3249.2 秒（第一趟 2908.3 秒，兩次差 12%）；這是 CPU 時間式的加總，不是牆鐘；同一段指令的牆鐘第一趟是 9m46s（586 秒）、這一趟是 12m38s（758 秒）；計畫的 580 秒是各項目單獨牆鐘之和，與牆鐘 586 秒相差 1%，所以 8 份的結論不變」。**不改任何其他句子、數字、表格**；原句裡的 `(D4, D9), so 8 parts stands` 保留意思。若執行者在該帳本找不到 586 或 9m46s 的來源，改以 ledger 現有字面為準，不自己編數字，並在新 ledger 註明。

### 5. 文件與註解
- `docs/TESTING.md` 第 13、129、140、169 行與 `docs/PLATFORM.md` 第 766 行附近：項目清單加入 `tests/platform_clock_2_test.sh`，說明「時鐘兩個檔各占一個項目」；不寫秒數、不寫個數。
- `tests/platform_test.sh` 第 46～48 行、第 376～389 行註解：改述 `clock` 與 `clock2`；不得出現 `/home/<名>/` 一類路徑（`test_scope.py` 掃這個），且必須保留 `PREFLIGHT_ONLY:-}" = "2"` 與 `${XDG_CACHE_HOME:-$HOME/.cache}` 兩個字面（`test_wrapper*.py` 讀 `platform_test.sh` 全文）。

### 6. 受影響的既有斷言（執行者先 `grep -nE 'clock|nine|九|== 9|-eq 9|"9"' ` 全部列進 ledger，逐條標「改（只因個數／名單變）」或「不改但仍綠」）
會改的（**不是弱化**——它們釘死的是「9 個項目」「clock 是兩個檔」，正是本片要改的）：
1. `platform/tests/test_platform_parts.py`：
   - 第 20 行 `PARTS = [*NUMBERS, "clock"]` → 加 `"clock2"`；docstring（第 2 行）「nine run_all.sh entries」→ 十個。
   - 第 57～63 行 `test_tcf3_05`：`listed(MAIN, ABF_PLATFORM_PART="clock") == [("alone", [CLOCK_FILES[0]]), ("alone", [CLOCK_FILES[1]])]` → `clock` 恰為 `[("alone",[CLOCK_FILES[0]])]`，`clock2` 恰為 `[("alone",[CLOCK_FILES[1]])]`，順序不變；「兩個檔不在任何數字份的任何分片」那段原樣保留。
   - 第 91 行：訊息子字串 `must be 1 to 8, clock or all` → `must be 1 to 8, clock, clock2 or all`；`PART=9`、`PART=0`、`PART=main` 照舊退出 1，另加 `PART=clock3`、`PART=clock_2`。
   - 第 220 行：檔名樣式（`platform_clock_test.sh` 或 `platform_shard_\d+_test.sh`）加 `platform_clock_2_test.sh`。
   - 第 263 行與 SS-07／SS-11 一類算「恰好 9 個包裝檔」的斷言：9 → 10。
2. `tests/run_all_shard_test.sh`：第 43、46 行樣式；第 51 行名單加 `platform_clock_2_test.sh`。TC-002 的「兩兩相差 ≤ 1 且總和等於磁碟上實際包裝檔數」本來就是相對判斷，新檔自動算進去；反例（全部堆同一份要判紅）原樣保留。
3. `tests/run_all_retry_test.sh` 第 459 行那種逐一列名單：只**加**新名字（對應 SC-06）。

不改但必須仍然通過（executor 在 ledger 貼出綠）：`tests/run_all_retry_test.sh` 的 TC-089、PS-22、PS-24（第 413～441 行）；`tests/run_all_count_test.sh`（TC-004 動態比對 `--list` 行數與實際 `*.sh` 數，新檔自動算）；`tests/constitution_scope_test.sh`（只要求憲法裡舊名字存在）；`platform/tests/test_wrapper.py`、`test_wrapper_nf2.py`、`test_scope.py`；`test_platform_parts.py` 裡所有談 REST 輪流分配、重檔、`ABF_PLATFORM_DIR` 沙盒新增空檔、`PER_TEST_TIMEOUT` 仍是 300 的案例（SS-05、SS-06、SS-12 等）。

## 失敗先行測試（現在都會紅；前綴 `SC-`，避免撞到 `SS-`／`PS-`／`TC-`）
「現在會紅」＝在未改動的 `origin/v3` 上，因為 `PART=clock2` 被拒、`platform_clock_2_test.sh` 不存在、或 `clock` 還是兩個檔而失敗。放在 `platform/tests/test_platform_parts.py`（SC-01…SC-09）、`tests/run_all_retry_test.sh`（SC-06）、`tests/run_all_shard_test.sh`（SC-07）。

### A. 測試集合前後相同（本片最重要的案例）
- SC-01 **收集集合不變**：以 `ABF_PYTEST_ARGS="--collect-only -q"` 分別執行十個項目（八份數字分片、`clock`、`clock2`；沿用 `warm` fixture，沒有 Java 時 skip，CI 上不准 skip），把各自收集到的節點 id 取聯集：（a）沒有任何節點 id 在兩個項目出現；（b）聯集等於對 `platform/tests` 整個目錄一次 `pytest --collect-only -q` 的節點 id 集合（同一環境同一 commit）；（c）每個項目收集到的**檔案**集合恰等於它的 `ABF_PLATFORM_LIST=1` 清單。這條案例用的是同一 commit 的兩種收集方式互相比對，抓得到「某個檔掉出所有項目」「某個檔跑兩次」。
- SC-02 **清單層級不變**：`clock` ∪ `clock2` 的檔案恰為 `{tests/test_station_e2e.py, tests/test_nextflow_e2e.py}`，且與八份數字分片兩兩不重疊；十份清單的聯集排序後恰等於 `platform/tests/test_*.py` 全部；`PART=all` 的聯集等於同一個集合；`PART=1`～`8` 各自的清單**與改前逐字相同**（改前的八份清單由 executor 在作法 0 用 `ABF_PLATFORM_LIST=1` 存進 ledger，測試不寫死檔名，閱卷者看 diff 確認 `SHARDS_n`／`REST_n` 的程式行零變動——依 README 通例）。
- SC-03 不設 `ABF_PLATFORM_PART` 仍等於 `PART=1`；清單裡每個路徑都在磁碟上存在。

### B. 時鐘分兩個
- SC-04 `PART=clock` 恰為 `[alone: test_station_e2e.py]`；`PART=clock2` 恰為 `[alone: test_nextflow_e2e.py]`；`PART=all` 的 `alone` 行依序為這兩個，且排在全部 `shard` 行之後；兩個檔都不在任何數字分片。
- SC-05 `PART=9`、`0`、`main`、`clock3`、`clock_2` 都退出 1，訊息含 `must be 1 to 8, clock, clock2 or all`；`tests/` 底下恰有 `platform_clock_test.sh` 與 `platform_clock_2_test.sh` 兩支時鐘包裝檔，後者內含且只含 `ABF_PLATFORM_PART=clock2`，前者內含且只含 `ABF_PLATFORM_PART=clock`。
- SC-06 `platform_clock_2_test.sh`（以及沙盒內造的同名檔）被拒絕隔離：`run_all.sh --retry-failed-once` 讀到 quarantine 含它時退出 1、訊息含 `may not be quarantined`（對照既有 TC-089 的寫法）；`tests/quarantine.txt` 第 12 行同時含 `platform_clock_2_test.sh` 與原有五個字面（PS-24 照舊綠）。
- SC-07 `run_all.sh --list --allow-msys` 含十個平台包裝檔（`platform_test.sh`、`platform_shard_2…8_test.sh`、`platform_clock_test.sh`、`platform_clock_2_test.sh`）；`--shard I/4` 的四份，包裝檔數兩兩相差 ≤ 1 且總和為十；在 `--shard` 的排序裡 `platform_clock_2_test.sh` 與其他包裝檔一樣是權重 40（用「在沙盒裡只留這 10 個包裝檔加 4 個普通檔」之類的情境驗：普通檔不會先於它被分配）。
- SC-08 CI 模式（`CI=true`）且 PATH 沒有 Java：十個項目全部退出非 0，輸出含 `FAIL (CI=true)`（沿用 SS-09）。
- SC-09 `PER_TEST_TIMEOUT` 仍是 300，`run_all.sh` 使用說明仍寫 `default 300`（沿用 SS-12，確認本片沒偷調上限）。

### C. 文字更正（依 README 通例，由閱卷者看 ledger／diff／grep；executor 把證據貼進 ledger）
- SC-12 `specs/suite-speed/ledger.md`：不再含 `within 30 percent of the plan's 580 s wall`；含 `586`；同一句明說逐檔加總不是牆鐘；`git diff --stat origin/v3 -- specs/suite-speed/ledger.md` 顯示只改 1 行（`1 insertion, 1 deletion`）。
- SC-13 `.github/workflows/tests.yml`：`git diff -U0 origin/v3 -- .github/ | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | grep -vE '^[+-]#'` 輸出為空（每個變動行都是註解）；新註解不含 `four`、不含 `~` 加數字加 `s` 的秒數、含 `platform_clock_2_test.sh`。
- SC-14 `docs/TESTING.md` 與 `docs/PLATFORM.md` 都提到 `platform_clock_2_test.sh`；`tests/platform_clock_test.sh` 檔頭不再含 `fourth`；`tests/` 與 `docs/` 不再含 `four platform entries`。

## 完成標準（done when）
1. **每一項實測 ≤ 180 秒**：在桌機 WSL 單獨量每個平台項目（十個）與完整 `bash tests/run_all.sh`（**不帶 `--timeout`**，預設 300 秒）：輸出沒有任何 `TIMEOUT` 行，且十個平台項目的 `ok  <n>s` 都 ≤ 180 秒。依 suite-speed 的裁決 D5 精神：機器負載不歸 executor 控制——`uptime` 1 分鐘負載 ≤ 3 時 ≤ 180 秒是硬條件；負載 > 3 時只記錄數字（連同負載），**沒有 TIMEOUT 行**才是硬條件。把改前（作法 0 第 3 點）與改後的這些行及 `nproc`、`/proc/loadavg` 貼進 ledger；閱卷者自己在 WSL 重跑核對。
2. **兩個時鐘項目都有餘裕**：`platform_clock_test.sh`（`test_station_e2e.py`）與 `platform_clock_2_test.sh`（`test_nextflow_e2e.py`）各自單獨牆鐘都 ≤ 180 秒，且兩者秒數之和不比改前的 `platform_clock_test.sh` 多 20% 以上（拆分只多一次 bootstrap 預檢，約 0.5 秒）。
3. **測試集合不變**：SC-01～SC-03 全綠；ledger 貼出作法 0 第 2 點的「前」行數與 sha256，以及改後同一指令的「後」行數與 sha256，兩者相同（逐檔收集 id 的排序後文字完全一致）。
4. **更正帳本**：SC-12 成立（只動第 26 行那一句）。
5. **CI 註解**：SC-13 成立；`git diff --stat origin/v3 -- .github/` 只有 `.github/workflows/tests.yml` 一個檔且只有註解行。
6. SC-01…SC-14 全綠；「受影響的既有斷言」第 6 節的「不改但必須仍然通過」在 ledger 貼出綠的輸出；`bash tests/run_all.sh --only platform_` 全綠；`bash tests/run_all.sh` 全綠（同標準 1 那一趟）。
7. **範圍**：`git diff --stat origin/v3` 貼進 ledger，只含「範圍：檔案」列的檔；`web*.py`、`static/`、`DESIGN.md`、`platform/tests/test_web_*`、憲法、`hooks/*`、`platform/abf_*` 零變動。
8. `bash tests/run_all.sh --list --allow-msys` 的行數比改前多 1。

## 環境事實
- 完整套件只能在 Linux／WSL 跑（`tests/run_all.sh` 拒絕原生 Git Bash）；從 Git Bash 用 `cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree> && bash tests/run_all.sh'`（根 `CLAUDE.md`「For the executor and verifier」）。worktree 必須在本機磁碟，**同一個 checkout 同時跑兩次會互相弄壞暫存副本**——量測一律循序。
- 平台測試要 Python ≥ 3.10、Java ≥ 17、可連網下載 Nextflow；沒有 Java 時本機 `E2E SKIPPED`，CI 上直接紅。
- 這兩個「時鐘」檔看心跳（兩秒一次）與重建的結束時間（誤差須在一秒內），在只有兩核且別的行程忙碌時會失敗（`tests/platform_test.sh` 第 376～383 行註解）；所以它們必須各自獨佔，**不准改成與任何其他 pytest 行程同時跑**。`run_all.sh` 一次只跑一個項目，因此拆成兩個項目仍然獨佔。
- 機器：桌機 WSL，nproc=16（suite-speed 帳本），常有別的車道同時在跑完整套件，負載 2～20 都出現過；單項秒數會隨負載漂移 20～30%，所以完成標準 1 有負載條件。
- 已知環境紅：`test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 在 `onboarding-test-pinned-base` 合併前，完整 clone 上一定紅；若只剩這一條紅視同綠（README 通例，2026-10-25）。
- 憲法第 46、614 行寫「四個入口」的字面早已過期（suite-speed 後是九個、本片後是十個）；`constitution_scope_test.sh` 只檢查舊四個名字仍存在，不會紅。**本片不改憲法**，由 developer-agent 另案處理。
- 其他車道：web 車道可能同時新增 `test_web_*.py`；它們會被輪流分配自動接住，不影響本片，但 ledger 要註明量測時的 `v3` commit。

## 不做
- 不調高 `PER_TEST_TIMEOUT`、不在 CI 或 `memory/scripts/abf-fast-suite.sh` 加 `--timeout`。
- 不刪、不跳過、不弱化、不加速任何測試；不拆更細（一個檔的內部不拆；兩個時鐘檔本來就各自是單檔項目）；不碰 `test_web_*`。
- 不動八份數字分片的內容、輪流分配規則、`PLATFORM_PARTS=8`。
- 不引入 `pytest-xdist` 或按歷史秒數自動切分的外掛。
- 不改 `.github/` 的任何非註解行（`timeout-minutes`、矩陣份數、job 名、`--timeout`），需要就 BLOCKED。
- 不改憲法文字、不改 web 相關檔。
- 不把秒數或個數寫進註解、文件（避免再過期）。

## 待 developer-agent 裁決
1. **名字**：計畫預設新包裝檔叫 `platform_clock_2_test.sh`、份數值叫 `clock2`。若你偏好別的名字（例如 `platform_clock_nf_test.sh`），請在裁決段寫明；改名要連動 `run_all.sh` 三處樣式與所有 SC 案例。
2. **CI 矩陣**：包裝檔增至 10 個、CI 仍 4 份（每份 2～3 個包裝檔）。本片不碰 CI 設定；合併後看 CI 各份秒數再決定是否調整，屬需維護者核准的事。
3. **憲法**：同 suite-speed D3，字面過期另案。

## 裁決
1. **名字**：照預設 `platform_clock_2_test.sh`／`clock2`。
2. **tests.yml 移出範圍**（覆寫「範圍」第 58 行、作法 3、SC-13、完成標準 5）：本專案「改 CI 設定」要先問維護者，連註解也不碰。`git diff origin/v3 -- .github/` 必須為空；SC-13 與完成標準 5 改判為「.github 無變動」。過期註解列進每日清單另案。
3. **CI 矩陣、憲法**：照「待裁決」2、3，本片不碰。
4. **帳本更正**：只改 suite-speed ledger 第 26 行那一句，把 3249.2 秒正名為「各檔秒數總和」，牆鐘用同一次量測的 `real` 值；不新增量測、不改其他句。
5. **`kinds`**：維持 `kinds: backend`（無括號），助手說明正確。

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
