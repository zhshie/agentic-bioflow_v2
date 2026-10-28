---
id: suite-speed
title: 把平台測試拆得更細：讓 tests/run_all.sh 每一個項目都在預設 300 秒內跑完（而不是調高上限）
tier: A
kinds: backend
lane: L13-tests
branch: test/suite-speed
base: v3（`origin/v3` @ d836c9c；查證日 2026-10-28；所有行號與名字都取自該版本）
source: developer-agent 派工訊息 2026-10-28（桌機 WSL 負載約 5 的實測：`tests/platform_shard_3_test.sh` 417 秒、`tests/platform_test.sh` 370 秒，兩支都過但超過 300 秒，executor 的完整套件被中途砍掉、誤判 BLOCKED）；前置任務 `platform-test-shards`（已合併，把一個項目拆成四個）
---

# suite-speed

> 本檔由 developer-agent 的計畫幫手草擬（2026-10-28），**A 級：只動測試基礎設施**。接續 `platform-test-shards`：那一片把「整份平台 pytest」拆成四個 `run_all.sh` 項目，但每個項目裡仍有一個巨大的「REST」分片（一個 pytest 行程塞約 30 個檔），四個項目在一台忙碌的機器上仍然 370～417 秒。本片把它再拆細、按**實測秒數**重新平衡，並讓以後新增的測試檔自動有歸屬。
> **不准碰**：`web*.py`、`static/`、`DESIGN.md`、`test_web_*`（另一個 session 的車道；本片只在分片清單裡**寫它們的檔名**，不改它們的內容）、`.github/`。
> 註：frontmatter 的 `kinds` 寫 `backend`（不加方括號），因為 `memory/scripts/build-dev-plans.py` 第 36～39 行用逗號切字串，方括號會被當成 kind 名的一部分。

## 目標
讓 `bash tests/run_all.sh`（預設每個項目 300 秒上限）在桌機 WSL 上**一個項目都不超時**，而且有餘裕：每個平台項目在那台機器上都 ≤ 200 秒。做法是把平台 pytest 從「3 份分片＋時鐘」改成「8 份分片＋時鐘」，每份只含少量檔、按實測秒數搭配；**不調高 `PER_TEST_TIMEOUT`**。

對使用者的意義：executor 跑完整套件不再因為上限被砍掉而回報 BLOCKED；300 秒的上限重新只負責抓卡死。

## 維護者原話（verifier 出題用）
來源是派工訊息與前置計畫，逐字：
- 「`tests/run_all.sh` 每支測試腳本預設 300 秒上限（`--timeout`）。10-28 在桌機 WSL（負載約 5）實測：`tests/platform_shard_3_test.sh` 417 秒、`tests/platform_test.sh` 370 秒，兩支都過了但超過上限，導致 executor 的完整套件被中途砍掉、誤判 BLOCKED。」→ 完成標準 1、SS-01…SS-14
- 「目標：每支測試腳本在預設 300 秒內跑完，而不是只把上限調大。」→ SS-12（上限仍是 300）、完成標準 1
- 「找出最慢的 pytest 檔（可讀分片清單推估；不要自己跑整套測試，太慢），提出把慢的分片再拆開或重新平衡的做法」→ 「現況與最慢處」「作法」
- 「在計畫裡寫可檢查的完成標準（例如 run_all 有新測試：每支 shard 的檔案清單不重疊、合起來等於全部 platform 測試檔；各 shard 單獨在 300 秒內）」→ SS-01…SS-04、完成標準 1～3
- 「不准碰：web*.py、static/、DESIGN.md、test_web_*、.github/」→ 「範圍：檔案」的不准動清單；完成標準 5

## 現況與最慢處（讀 `origin/v3` 的分片清單與前置任務的量測帳本推得；執行者要在作法 0 重量，不要照抄這裡的數字）
**分片怎麼切**（`tests/platform_test.sh`，`set_platform_parts` 第 56～89 行）：`SHARDS_1/2/3` 是人工點名的分片（每行一個 pytest 行程，共 11 行；點名的檔含時鐘 2 檔共 31 個）；其餘 89 個 `tests/test_*.py` 以 `LC_ALL=C sort` 排序後依 `k % 3` 輪流進 `REST_1/2/3`，**每份的 REST 是一個 pytest 行程**。每個 `run_all.sh` 項目＝同一份的全部分片一起平行跑，牆鐘時間＝最慢的那個分片。

**在 `d836c9c` 上用 `git ls-tree` 加腳本自己的 `ABF_PLATFORM_LIST=1` 算出的每份內容（檔案位元組數，只是粗略代理）**：

| 項目 | 點名分片（檔案位元組） | REST 檔數／位元組 |
|---|---|---|
| 第 1 份 `platform_test.sh` | 5 K、10 K、11 K、61 K | 30 檔／約 736 K（最大） |
| 第 2 份 `platform_shard_2_test.sh` | 35 K、120 K、30 K、85 K | 30 檔／約 573 K |
| 第 3 份 `platform_shard_3_test.sh` | 111 K、77 K、122 K | 28 檔／約 446 K |

**前置任務的量測（`specs/platform-test-shards/ledger.md` 第 20～100 行，乾淨機器、暖快取、各項目單獨跑）**：第 1 份 170.5 秒（其中 REST 分片 169.5 秒，678 個測試）、第 2 份 122.2 秒（REST 121.2 秒）、第 3 份 123.5 秒（REST 122.4 秒）、時鐘 163.3 秒（`test_station_e2e.py` 64.9 秒＋`test_nextflow_e2e.py` 97.3 秒，一個接一個）。點名分片裡最慢的是 `test_launch_e2e.py`＋`test_station_fakeplatform.py`＋`test_station_channel.py` 那一行（100 個測試、124 秒），以及 `test_launch_nextflow.py`（6 個測試、43 秒，其中一個 setup 就 95 秒——那個 setup 是一次真的 Nextflow 執行，**不能再拆**，只能讓它獨佔一個分片）。

**所以最慢處是「REST」分片，不是某個單一檔**：每份 REST 把約 30 個檔塞進一個行程，而同一份裡其他分片早就跑完，牆鐘全由它決定。10-28 的 370／417 秒是同樣的程式在負載約 5 的機器上的結果（乾淨機器上 123～170 秒；放大約 2.2～3.4 倍）。因此只把 3 份 REST 各切成兩半不夠：要讓「負載約 5」的機器也 < 300 秒，乾淨機器上每個項目要降到約 85 秒以下，而四個項目總和約 580 秒，所以至少要 7～8 個項目（580 ÷ 8 ≈ 72 秒，留餘裕給分得不平均；實際以作法 0 的量測決定）。

## 範圍：檔案（只准改這些；另加 `specs/suite-speed/ledger.md` 為 executor 帳本）
修改：
- `tests/platform_test.sh`（`ABF_PLATFORM_PART` 的合法值與錯誤訊息、`set_platform_parts` 的分片表與輪流分配、`all` 的展開、註解）
- `tests/platform_clock_test.sh`（只改第 5～8 行註解，若它仍寫「four entries」）
- `tests/run_all.sh`（只改第 46 行與第 355～361 行的**註解**，把「four」改成不寫數字；**不改邏輯**：第 174 行與第 363～364 行的樣式 `platform_shard_*_test.sh`／`shard_[0-9]+` 本來就接受任何編號）
- `tests/quarantine.txt`（只改第 12 行註解）
- `tests/run_all_shard_test.sh`（只改 TC-002，第 31～37 行，見「受影響的既有斷言」）
- `tests/run_all_retry_test.sh`（只新增案例，不動既有斷言）
- `platform/tests/test_platform_parts.py`（見「受影響的既有斷言」）
- `docs/TESTING.md`（第 13、129、140、169 行）
- `docs/PLATFORM.md`（第 732～735 行那一段）
新增：
- `tests/platform_shard_4_test.sh` … `tests/platform_shard_8_test.sh`（五支，形狀同 `platform_shard_3_test.sh` 的三行有效碼）
- `specs/suite-speed/ledger.md`

**不准動（硬規則）**：
- 車道外：`web*.py`、`platform/abf_platform/web*.py`、`static/`、`DESIGN.md`、`PRODUCT.md`、`platform/tests/test_web_*`（任何形式的修改；它們只會出現在分片清單的**字串**裡）、`.github/`。
- `hooks/*`、`platform/abf_*`、`platform/tests/` 底下除 `test_platform_parts.py` 以外的檔案（含 `test_wrapper*.py`、`test_scope.py`——它們靠 `platform_test.sh` 的字面，見「受影響的既有斷言」第 6 項）。
- `.specify/memory/constitution.md`（見「待 developer-agent 裁決」第 3 項）、`spec.md`、`test-case*.md`、`docs/ROADMAP.md`、`.claude-plugin/plugin.json`。
- 任何平台測試的**內容**：本片只搬「哪個檔在哪個分片」，不加速、不刪、不改個別測試。

## 作法
### 0. 先量（改任何檔之前；在 WSL／Linux，暖快取，從有 `.git` 的 clone 跑，記進 ledger）
1. 機器：`nproc`、`uptime`（前後各一次）、`git rev-parse HEAD`。
2. 現況每個項目的牆鐘與每個分片秒數（各項目單獨跑，循序）：
   ```
   for e in platform_test platform_shard_2_test platform_shard_3_test platform_clock_test; do
     ( time bash tests/$e.sh ) 2>&1 | grep -E '^real|===== pytest shard|passed|failed' ; done
   ```
3. **每個測試檔的秒數**（分配的依據）：
   ```
   ABF_PLATFORM_PART=all ABF_PYTEST_ARGS="--durations=0" bash tests/platform_test.sh > /tmp/dur.out 2>&1
   awk '/^[0-9.]+s (call|setup|teardown) /{split($3,a,"::"); t[a[1]]+=$1} END{for(f in t) printf "%.1f %s\n", t[f], f}' /tmp/dur.out | sort -rn > /tmp/per-file.txt
   ```
   把 `/tmp/per-file.txt` 全文貼進 ledger（這是「最慢的 pytest 檔」的正式答案；本計畫的位元組代理只供預估）。`--durations=0` 不顯示小於 5 毫秒的項目，可忽略。
4. **現況在忙碌機器上的對照**（重現 10-28 的症狀，一次即可）：`bash tests/run_all.sh --only platform_ 2>&1 | tail -20`，記下每個項目的 `ok  <n>s`／`TIMEOUT` 行。這是完成標準 1 的「改前」欄。

### 1. 新結構（決定）
- **8 份分片＋時鐘＝9 個平台項目**：`platform_test.sh`（第 1 份）、`platform_shard_2_test.sh` … `platform_shard_8_test.sh`（第 2～8 份）、`platform_clock_test.sh`（時鐘，不變）。
  - 為什麼是 8：總量約 580 秒（作法 0 會重量），要讓負載約 5 時 < 300 秒（放大約 3.4 倍）＝乾淨機器每份 ≤ 約 85 秒；580 ÷ 85 ≈ 7；取 8 留餘裕。**若作法 0 的量測總和與此差超過 30%，改用 `ceil(總和 ÷ 75)` 份（至少 6、至多 12），並在 ledger 說明；其餘規則不變。**
  - 為什麼不是「分更多平行行程」：前置計畫與 `platform_test.sh` 第 332～333 行已記錄，兩核的 CI runner 上更多平行行程會讓看時鐘的檔失敗；10-28 的桌機也是 CPU 搶用造成放大。把工作分到**更多循序項目**才真的縮短每個項目的牆鐘。
  - CI 影響：CI 是 `run_all.sh --shard I/4` 的矩陣（`tests.yml` 第 37 行註解），平台包裝檔權重 40，貪婪分給最輕的那份；9 個包裝檔會變成 3、2、2、2。每個 CI job 的平台工作量與現在接近（總量不變），**不需要**改 `.github/`（見「待 developer-agent 裁決」第 2 項）。
- **`ABF_PLATFORM_PART` 的合法值改為 `1`～`8`、`clock`、`all`**，預設仍是 `1`。檢查寫成「上限由一個變數 `PLATFORM_PARTS=8` 決定」，不要在 `case` 裡列 `1|2|3|…|8`：錯誤訊息改成 `FAIL: ABF_PLATFORM_PART must be 1 to 8, clock or all, not '$PART'`（8 從變數帶入）。`all`＝全部數字份分片之後再跑時鐘（等同現行 `all` 的語意）。
- 新增五支包裝檔，與 `platform_shard_3_test.sh` 同形：`export ABF_PLATFORM_PART=<n>`、`exec bash "$HERE/platform_test.sh" "$@"`；檔頭註解說明「不是第二份拷貝，只選份數；檔名由 `tests/run_all.sh` 拒絕隔離的樣式固定」。
- **分片表改寫（`set_platform_parts`）**：
  1. 點名分片只保留**重的檔**：作法 0 第 3 點量出的每檔秒數 ≥ 20 秒者，**每檔一行、獨佔一個 pytest 行程**（`test_launch_nextflow.py` 的 95 秒 setup 因此獨佔；`test_launch_e2e.py`、`test_station_fakeplatform.py`、`test_station_channel.py` 那個 124 秒的組合行要拆開）。已有的多檔點名行若合計 > 30 秒，也拆開。
  2. 這些重檔用**最長者先分配**法放進 8 份：由大到小排序，每個放進目前總秒數最小的份（同分取編號小者）。每份點名分片 ≤ 3 個。
  3. 其餘所有檔（沒被點名、不在時鐘）維持**輪流分配**，但 `% 3` 改為 `% 8`（用 `PLATFORM_PARTS`）；REST 因此變成每份約 11 檔、一個行程。新增的測試檔自動有歸屬，不必改清單。
  4. 依作法 0 的秒數估算每份「點名秒數＋REST 估計（全部 REST 檔秒數 ÷ 8）」，最大／最小 ≤ 1.4；做不到時**只准整行搬移**（不拆行、不調輪流規則），一次調整後依實測定案，不反覆調。
  5. 時鐘兩檔（`LAST`）完全不動。
- **介面不變的部分**：`ABF_PLATFORM_LIST=1` 的輸出格式（`shard: <檔…>`／`alone: <檔>`）、`selected_shards` 的函式形狀、空的 REST 不印、`wait`／`$LOG.$n` 合併、摘要行 `platform tests: pytest exit …`、CI 不准 skipped 的規則——因為 `test_platform_parts.py` 與 `run_all.sh` 都靠它們。
- **bootstrap 不動**：九個項目共用同一份 venv 與下載快取（暖預檢 0.5 秒，前置計畫已量）；不新增快取機制、不抽共用腳本。

### 2. 隔離名單
`tests/run_all.sh` 第 174 行的樣式 `platform_shard_*_test.sh` 已涵蓋 `platform_shard_4`…`8`，**不需要改邏輯**；本片只加案例證明（SS-10）並把 `tests/quarantine.txt` 第 12 行的註解改成不寫「四個」、改述「`platform_test.sh`、`platform_clock_test.sh` 與所有 `platform_shard_<n>_test.sh`」。

### 3. 文件與註解
- `docs/TESTING.md` 第 13、129、140、169 行：「the four platform entries (…)」→ 「the platform entries (`tests/platform_test.sh`, `tests/platform_shard_<n>_test.sh` for n = 2 to 8, and `tests/platform_clock_test.sh`)」，不寫秒數、不寫「four」。
- `docs/PLATFORM.md` 第 732～735 行：指令清單改為 `platform_test.sh`（第 1 份）、`platform_shard_<n>_test.sh`（第 n 份，n = 2…8）、`platform_clock_test.sh`；註解的「one of four entries」改為不寫數字。
- `tests/platform_test.sh` 第 46～51、75～77、361～363 行等註解改述新結構（八份加時鐘）。
- `tests/run_all.sh` 第 46、355～361 行的註解：46 行改成 `PER_TEST_TIMEOUT=300   # every entry, the platform ones included, should finish well inside this; it only catches a hang`（**必須保留「only catches a hang」，不得含 `~30s`**，`test_tcf3_04` 靠它）；355～361 行把「the four platform_*_test.sh wrappers」與「N=4 each part gets one platform wrapper」改成不寫個數的說法。

### 4. 受影響的既有斷言（已逐一核對 `origin/v3`）
會改（同一個提交內改好；**不是弱化**——它們釘死的是「三份」「四個項目」的個數，而個數正是本片要改的）：
1. `platform/tests/test_platform_parts.py`：
   - 檔頭 docstring 與常數（第 1～16 行）：`ENTRIES`／`PARTS`／`SHARD2`／`SHARD3` 改成由 `PLATFORM_PARTS = 8` 與 `tests/platform_shard_<n>_test.sh` 產生；`PARTS` 變成 `["1",…,"8","clock"]`。
   - `test_tcf3_02`（第 27～33 行）、`test_ps03`（第 36～40 行）、`test_tcf3_05`（第 43～57 行裡的 `for part in "123"`）、`test_ps05`（第 60～64 行）：「三份」→ 「八份」。
   - `test_ps08`（第 84～93 行附近）：舊的「`PART=4` 被拒」不再成立；改成 `PART=9`、`PART=0`、`PART=main` 都退出 1 且訊息含 `must be 1 to 8, clock or all`。
   - `test_ps09_ps32`、`test_ps32`（第 113～142 行附近）：`% 3` → `% 8`、「七個新檔散到三份」→ 「十六個新檔每份恰兩個、REST 檔數兩兩相差 ≤ 1」。
   - `test_ps34_ps35`、`test_tcf3_06`、`test_ps13_ps14`、`test_ps15_ps16`、`test_tcf3_03`：迴圈改為涵蓋全部九個項目（`SHARD2`／`SHARD3` 常數 → 產生的清單）。
   - `test_ps61`（第 153～155 行）：「恰好兩支分片腳本」→ 「恰好是 `platform_shard_2_test.sh`…`platform_shard_8_test.sh` 七支」。
   - `test_ps27_to_ps30_…`、`test_ps31`（第 167～190 行）：文件與註解斷言改成「列出全部項目名、不再說『four』」。
2. `tests/run_all_shard_test.sh` TC-002（第 31～37 行）：現在斷言「N=4 時每份恰好一個平台包裝檔（`1 1 1 1`）」；9 個包裝檔時不可能。改成「每份的包裝檔數兩兩相差 ≤ 1，且總和等於 `tests/` 底下實際的平台包裝檔數」。閱卷者要確認新斷言仍抓得到「全部包裝檔堆在同一份」的壞情形（SS-11 的反例）。

不改但必須仍然通過（executor 在 ledger 貼出綠）：
3. `tests/run_all_count_test.sh`：TC-001 只看 `run_all.sh` 前 20 行（本片不碰）；TC-004 是動態比對 `--list` 行數與實際 `*.sh` 數，新增五支自動算進去。
4. `tests/constitution_scope_test.sh` 第 267～276 行：只要求憲法裡**有**四個舊名字且檔案存在；多出的包裝檔不影響。
5. `tests/run_all_retry_test.sh` 既有 TC-053、TC-089、PS-18、PS-19、PS-22、PS-24（第 413～441 行）原樣通過。
6. `platform/tests/test_wrapper.py`、`test_wrapper_nf2.py`（讀 `platform_test.sh` 全文確認第二組 Nextflow 的設定）、`test_scope.py`（掃檔內有沒有硬編路徑）、`test_launch_static.py`：必須保留的字面——`platform_test.sh` 內的 `PREFLIGHT_ONLY:-}" = "2"`、`${XDG_CACHE_HOME:-$HOME/.cache}`，並且新增的註解不得出現 `/home/<名>/` 這類路徑。
7. `tests/platform_direction_docs_test.sh`、`tests/platform_storage_doc_test.sh`：只讀文件，仍可被隔離，不受影響。

## 失敗先行測試（現在都會紅；在 `platform/tests/test_platform_parts.py`、`tests/run_all_retry_test.sh`、`tests/run_all_shard_test.sh`）
「現在會紅」＝在未改動的 `origin/v3` 上，因為 `PART=4…8` 被拒、`platform_shard_4…8_test.sh` 不存在而失敗。編號前綴 `SS-`（suite-speed），避免撞到其他任務的 `TC-0xx`／`PS-xx`。

### A. 覆蓋（以 `ABF_PLATFORM_LIST=1` 解析清單，沿用該檔的 `listed()`）
- SS-01 `PART=1`…`PART=8` 與 `clock` 九份清單的聯集，排序後恰等於 `platform/tests/test_*.py` 全部（`tests/` 前綴）；合併後沒有重複檔。
- SS-02 `PART=all` 的聯集等於全部檔，也等於九份的聯集；八份數字份各自非空，且每一行的種類都是 `shard`；時鐘兩檔不在任何數字份的任何分片，`PART=clock` 恰為兩個 `alone`（順序不變）。
- SS-03 清單裡每個路徑都在磁碟上存在（點名的檔被刪或改名會紅，而不是到 pytest 才報 not found）；不設 `ABF_PLATFORM_PART` 等於 `PART=1`。
- SS-04 `PART=9`、`PART=0`、`PART=main` 都退出 1，訊息含 `must be 1 to 8, clock or all`。
- SS-05（守「REST 不再膨脹」）八份裡**每一個分片（一行）至多 10 個檔**，且每份至多 4 個分片（含 REST）；每個點名的重檔行至多 3 個檔。這條抓的是「新檔全擠進一個行程」這個本片要解的病根——以前沒有任何測試擋它。
- SS-06 把 `platform/` 複製到暫存目錄（`ABF_PLATFORM_DIR`），多放 16 個空的 `tests/test_zz_new_<i>.py`：每份恰得到其中兩個，且八份的 REST 檔數兩兩相差 ≤ 1。
- SS-07 每個包裝檔選的份數與檔名一致：`platform_shard_<n>_test.sh` 內含且只含 `ABF_PLATFORM_PART=<n>`；`tests/` 底下恰好有 `platform_shard_2…8` 七支，沒有 `platform_shard_1`、沒有 `platform_shard_9`。
- SS-08 九個項目各以 `ABF_PYTEST_ARGS="--collect-only -q"` 執行（沿用 `warm` fixture；沒有 Java 時 skip，CI 上不准 skip）：各退出 0、輸出含 `platform tests: pytest exit 0`；各項目收集到的檔案集合恰等於它的清單，九個項目的聯集恰等於全部檔、無重複。
- SS-09 CI 模式（`CI=true`）且 PATH 沒有 Java：九個項目全部退出非 0，輸出含 `FAIL (CI=true)`。

### B. 隔離與分片（`tests/run_all_retry_test.sh`、`tests/run_all_shard_test.sh`）
- SS-10 `platform_shard_8_test.sh` 與沙盒內造的 `platform_shard_12_test.sh` 被拒隔離（退出 1，訊息含 `may not be quarantined`）；`platform_storage_doc_test.sh`、`platform_direction_docs_test.sh` 仍可隔離（退出 0）。
- SS-11 `run_all.sh --list --allow-msys` 含九個平台包裝檔；`--shard I/4` 的四份，包裝檔數兩兩相差 ≤ 1 且總和為九；並加一個**反例**：在沙盒造一個把全部包裝檔排在同一份的假清單，新斷言要判紅（證明新版 TC-002 沒有被弱化成永遠為真）。
- SS-12 `PER_TEST_TIMEOUT` 仍是 300，註解含 `only catches a hang`，不含 `~30s`，且 `run_all.sh` 的使用說明仍寫 `default 300`。

### C. 文件
- SS-13 `docs/TESTING.md` 與 `docs/PLATFORM.md` 提到 `platform_shard_`，且不再含 `four platform entries`、`one of four entries`、`The machine part is the four`；`docs/TESTING.md` 仍含 `default 300`。
- SS-14 `tests/platform_test.sh`、`platform_clock_test.sh` 與各包裝檔的註解不再出現 `Two run_all.sh entries`、`about half`、`four entries`。

## 完成標準（done when）
1. **預設上限下全套不超時**：在桌機 WSL 跑 `bash tests/run_all.sh`（**不帶 `--timeout`**，即預設 300 秒），輸出裡**沒有任何 `TIMEOUT` 行**，且每個平台項目（九個）的 `ok  <n>s` 都 ≤ 200 秒（留 1.5 倍餘裕）。在 ledger 貼出改前（作法 0 第 4 點）與改後的這些行，以及當時的 `uptime`、`nproc`。這是本片唯一直接對應症狀的標準，閱卷者依 README 通例看 ledger 並**自己在 WSL 重跑核對**。
2. **各項目單獨量（乾淨機器）**：九個項目各自 `time` 的牆鐘 ≤ 100 秒（時鐘除外，它不變、不得比改前慢超過 10%）；八份數字份的最大／最小 ≤ 1.5。做不到要在 ledger 寫明原因與測得的數字（例如某個 95 秒 setup 的檔獨佔一份）。
3. **清單層級的覆蓋**（可由測試檢查）：SS-01、SS-02：九個項目的檔案清單兩兩不重疊，合起來等於 `platform/tests/test_*.py` 全部；SS-08：實際收集到的也是這樣。
4. SS-01…SS-14 全綠；「受影響的既有斷言」第 3～7 項在 ledger 貼出綠的輸出；`bash tests/run_all.sh --only platform_` 全綠；`bash tests/run_all.sh` 全綠（同標準 1 那一趟）。
5. **範圍**：`git diff --stat origin/v3` 貼進 ledger，只含「範圍：檔案」列的檔；`web*.py`、`static/`、`DESIGN.md`、`platform/tests/test_web_*`、`.github/`、`hooks/*`、`platform/abf_*` 零變動（依 README 通例由閱卷者看 diff 確認）。`ABF_PLATFORM_LIST=1` 裡出現 `test_web_*` 的**檔名**不算違規。
6. `bash tests/run_all.sh --list --allow-msys` 的行數比改前多 5。

## 環境事實
- 完整套件只能在 Linux／WSL 跑（`tests/run_all.sh` 拒絕原生 Git Bash）；從 Git Bash 用 `cd ~ && wsl.exe -d Ubuntu -- bash -c 'cd /mnt/c/<worktree> && bash tests/run_all.sh'`（根 `CLAUDE.md`「For the executor and verifier」）。worktree 必須在本機磁碟，**同一個 checkout 同時跑兩次會互相弄壞暫存副本**——所以量測一律循序，不要用「同時跑兩個項目」來模擬負載。
- 平台測試要 Python ≥ 3.10、Java ≥ 17、可連網下載 Nextflow；沒有 Java 時本機 `E2E SKIPPED`，CI 上直接紅。
- 每個項目是循序跑（`run_all.sh` 一次一個），所以拆更多項目縮短的是每個項目的牆鐘，不是總 CPU；總時間不變，甚至多幾秒的啟動成本。這是設計：目標是不超時。
- `--retry-failed-once` 只重跑失敗的整個檔、逾時的不重跑；項目越小，偶發紅的重跑成本越低。
- 前置任務 `platform-test-shards` 的量測是「乾淨機器」；10-28 的 370／417 秒是負載約 5 的機器。兩者不可直接比，所以完成標準 1 用**同一種使用情境**（整套 `run_all.sh`）驗證，標準 2 才用乾淨機器的單項目時間。
- 已知環境紅：`test_onboarding_doc.py::test_tc047_tc051_other_docs_untouched` 在 `onboarding-test-pinned-base` 合併前完整 clone 上一定紅；若只剩這一條紅視同綠（README 通例，2026-10-25）。
- 其他車道：web 車道（另一個 session）可能同時新增 `test_web_*.py`；它們會被輪流分配自動接住，不衝突，**但**量測帳本要註明量測時的 `v3` commit，因為新檔會讓 REST 秒數漂移。

## 不做
- 不調高 `PER_TEST_TIMEOUT`、不在 CI 或 `memory/scripts/abf-fast-suite.sh` 加 `--timeout`。
- 不加速、不刪、不改任何個別平台測試的內容；不碰 `test_web_*`。
- 不引入 `pytest-xdist`（前置計畫已排除：目標是降低每個項目的牆鐘，且兩核 CI 上更多平行行程會讓看時鐘的檔失敗）；也不引入按歷史秒數自動切分的外掛（需要新增依賴與要維護的秒數檔，超出 A 級「只動測試基礎設施」的最小改動——如要採用，另案搜尋與選型）。
- 不拆時鐘項目（見「待 developer-agent 裁決」第 1 項的條件）。
- 不把秒數寫進註解或文件（避免再過期，同前置計畫的原則）。
- 不改 `.github/`、憲法、`hooks/*`、`platform/abf_*`。

## 待 developer-agent 裁決
1. **時鐘項目是否也要拆**：它乾淨機器上 163 秒（兩個檔一個接一個），10-28 沒超時。作法 0 第 4 點與完成標準 1 會量它在忙碌機器上的秒數：若改後 `platform_clock_test.sh` > 200 秒，請另開一片把它拆成 `clock`／`clock2` 兩個項目（要動 `run_all.sh` 第 174 行與 363～364 行的樣式，所以不放進本片）。
2. **`.github/workflows/tests.yml` 第 37 行的註解**（「clock ~196 s, shard_3 ~176, test ~163, shard_2 ~111 … one to each part」）合併後會過期，且 CI 矩陣變成每份 2～3 個包裝檔；是否更新註解／是否改矩陣份數由你決定（本片不碰 `.github/`）。CI 的 `--timeout 900` 是否拿掉，等合併後看 CI 各項目秒數再說。
3. **憲法**（`.specify/memory/constitution.md` 第 46、614 行）寫「四個入口／四份」，合併後字面過期；`constitution_scope_test.sh` 只檢查舊四個名字仍在，所以不會紅。同前置計畫的做法：本片不改憲法，由你記一筆之後另案修條文。
4. **份數**：計畫預設 8 份。若作法 0 的量測總和與預估差超過 30%，executor 依「為什麼是 8」那一段改用 `ceil(總和 ÷ 75)` 份（6～12）並記進 ledger；若你要固定份數，請在裁決段寫明。

## 裁決
（2026-10-28 13:50，developer-agent）
D1. 時鐘項目本片不拆；改後在忙碌機器上 > 200 秒就照待裁決第 1 項另開一片，本片不擋。
D2. `.github/` 一律不碰（改 CI 屬先問的事）；過期的第 37 行註解由我列進每日清單另案處理。
D3. 憲法不改；字面過期由我記一筆另案修。
D4. 份數照計畫：預設 8，作法 0 實測差 > 30% 才改 `ceil(總和 ÷ 75)`，並記進 ledger。
D5. 機器負載不歸 executor 控制（同一台機器上常有別條車道在跑完整套件）。完成標準 1 的硬條件是「預設 300 秒下沒有任何 TIMEOUT 行」；「每項 ≤ 200 秒」在 `uptime` 的 1 分鐘負載 ≤ 3 時才是硬條件，負載 > 3 時只記錄數字、不判 FAIL。完成標準 2 同理：負載 ≤ 2 時量才算數，量不到乾淨時段就在 ledger 寫明負載與數字，閱卷者依最大／最小比值（≤ 1.5）判斷平衡，不依絕對秒數。
D7.（14:10，回應合約階段阻擋 1）SS-05 的「每個分片至多 10 個檔」作廢。改為：每一份 REST 分片的檔數 ≤ `ceil(REST 檔總數 ÷ 份數) + 1`（輪流分配的自然上限），測試用當下實際收集到的檔數計算，不寫死總檔數或 10。
D8.（回應阻擋 2）`tests/quarantine.txt` 第 12 行保留 `platform_shard_2_test.sh` 與 `platform_shard_3_test.sh` 兩個字面，再加一句總述涵蓋所有 `platform_shard_<n>_test.sh`；PS-24 原樣不改、必須照舊通過。
D9.（非阻擋各點）以實際 HEAD 量測，不照抄計畫數字，測試不寫死檔案總數；實測後若要改份數（不是 8），executor 停下回報 BLOCKED，由我重開合約；「手動：閱卷者看 ledger／diff／在 WSL 重跑」的寫法可接受；SS-12～14 放在三支測試檔任一支、註解標 TC 編號即可。
D6. 車道名改為 `L13-tests`（避免和既有車道 `L9-web-cost`、`L11-onboarding` 撞號）。

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
