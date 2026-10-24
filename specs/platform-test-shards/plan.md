---
id: platform-test-shards
title: 把平台 pytest 拆成四個 run_all 項目（三份分片＋時鐘），量出最慢的測試，讓 CI 回到預設 300 秒
tier: A
kinds: backend
lane: L9-tests
base: v3
source: dev-queue.json 的 platform-test-shards；developer-agent 派工訊息 2026-10-24（CI log 2026-10-24 `platform_test.sh TIMEOUT 300s`；PR #198 為權宜之計把 CI 改成 `--timeout 900`）
---

# platform-test-shards

> 本檔由 developer-agent 助理草擬（2026-10-24）。**A 級**。行號一律是 `origin/v3`（`b086b6d`）的行號。**只動測試跑法與文件，不碰 `hooks/*`、`.github/*`、`platform/abf_*` 任何檔。** 前置：`ci-quarantine` 已完成（`tests/run_all.sh` 的隔離名單規則在第 160–161 行）。

## 目標
把「整份平台 pytest 塞在一個 `run_all.sh` 項目、在 CI 上超過 300 秒」改成四個各自遠低於 300 秒的項目，並證明每個 `platform/tests/test_*.py` 恰好被一個項目跑到。意義：CI 可以拿掉 `--timeout 900`，300 秒的上限重新只負責抓卡死；同時也量出哪些測試最慢，之後有依據再加速。

## 維護者原話（verifier 出題用）
來源是派工訊息，逐字：
- 「`tests/platform_test.sh` runs the whole platform pytest suite in one run_all.sh entry and now takes >300 s on GitHub runners (CI log 2026-10-24: `platform_test.sh TIMEOUT 300s`; PR #198 raised CI to `--timeout 900` as a stopgap).」→ PS-01…PS-12、PS-31
- 「measure the slowest platform test files/tests (`pytest --durations=30` in the plan's done-when, recorded in ledger)」→ 完成標準第 1 條（閱卷看 ledger，見 README 通例）
- 「split platform_test.sh into 3–4 run_all entries … so each finishes well under 300 s on CI, with a test that every platform/tests/test_*.py is covered by exactly one shard (no file dropped, none twice)」→ PS-01…PS-09、PS-14
- 「keep the venv/Nextflow bootstrap shared or cached so shards don't each pay it」→ PS-15、PS-16
- 「after this, CI can go back to the default per-test timeout — list the tests.yml change under `## 待 developer-agent 裁決`」→ 見該段（本任務不改 `.github/`）
- 「fix docs claims made stale (`tests/run_all.sh` comment about ~30 s max, docs/TESTING.md "About 100 seconds"/"default 300")」→ PS-26…PS-30
- 「the new shard names must be rejected [from quarantine] the same way」→ PS-17…PS-25

## 範圍：檔案（只准改這些，共 10 個；另加 `specs/platform-test-shards/ledger.md` 為 executor 帳本）
修改：
- `tests/platform_test.sh`（分片表、`ABF_PLATFORM_PART` 的值、迴圈、註解）
- `tests/platform_clock_test.sh`（只改第 7–8 行註解）
- `tests/run_all.sh`（只改第 46 行註解與第 160–161 行隔離規則）
- `tests/quarantine.txt`（只改第 12 行註解）
- `tests/run_all_retry_test.sh`（只新增案例，不動既有斷言）
- `platform/tests/test_platform_parts.py`（改寫既有斷言，見「受影響的既有斷言」）
- `docs/TESTING.md`（第 13、129、140、169 行）
- `docs/PLATFORM.md`（第 648–649 行）
新增：
- `tests/platform_shard_2_test.sh`
- `tests/platform_shard_3_test.sh`

**不准動**：`hooks/*`、`.github/*`、`platform/abf_*`、`platform/tests/` 底下除 `test_platform_parts.py` 以外的檔案（`flaky-tests` 任務正在動 `test_station_e2e.py`、`test_nextflow_e2e.py` 等，同車道循序，不在本任務碰）、`tests/run_all.sh` 第 1–20 行（`run_all_count_test.sh` 第 12 行檢查那段不得有 2 位數以上的數字）。

## 作法

### 0. 先量（改任何檔之前）
在 WSL／Linux 跑並把輸出貼進 ledger：
```
ABF_PLATFORM_PART=all ABF_PYTEST_ARGS="--durations=30" bash tests/platform_test.sh 2>&1 | tee /tmp/before.out
grep -E '^[0-9.]+s (call|setup|teardown) ' /tmp/before.out | sort -rn | head -30
grep -E '===== pytest shard|=+ .* in [0-9.]+s' /tmp/before.out
```
以及 `time bash tests/platform_test.sh`、`time bash tests/platform_clock_test.sh` 各一次（現況兩項目的牆鐘時間）。每個分片的 pytest 都會印自己的 `--durations`，所以第二行是跨分片合併後的前 30 慢測試；第三行給每個分片自己的秒數。依這份數字做下面第 2 點的分配。

### 1. 現況（`origin/v3`，供對照）
- `tests/platform_test.sh` 已在**一個項目內**用多個 pytest 行程平行跑：固定清單 `SHARDS`（第 54–66 行，11 行）加一個吃掉其餘檔案的 `REST`（第 67–72 行），第 344–351 行 `start_shard` 以 `&` 啟動，第 358 行等待；兩個看時鐘的檔 `LAST`（第 53 行）在第 360–366 行於分片之後逐個單獨跑。
- `ABF_PLATFORM_PART` 現在只有 `main|clock|all`（第 47–48 行）；`tests/platform_clock_test.sh` 第 10–11 行只是設 `clock` 後 `exec` 回 `platform_test.sh`。
- 所以「拆成 3–4 個項目」＝把現有分片**分組到不同項目**，不是新發明平行化；注意項目之間由 `run_all.sh` 循序執行（第 382–404 行），拆分降低的是每個項目的牆鐘時間，不是總 CPU。

### 2. 新結構（決定）
- 四個項目：`tests/platform_test.sh`（第 1 份）、`tests/platform_shard_2_test.sh`（第 2 份）、`tests/platform_shard_3_test.sh`（第 3 份）、`tests/platform_clock_test.sh`（時鐘，不變）。
- `ABF_PLATFORM_PART` 的值改為 `1|2|3|clock|all`，**預設 `1`**（`platform_test.sh` 直接跑＝第 1 份）。`main` 這個舊值**不再接受**（目前全 repo 沒有人設它：`grep` 只在 `platform_test.sh` 第 47、336–338 行出現）。第 48 行的訊息改成 `FAIL: ABF_PLATFORM_PART must be 1, 2, 3, clock or all, not '$PART'`。`all` ＝ 第 1、2、3 份加時鐘，行為等同現在的 `all`（舊檔 once did）。
- 兩支新腳本與 `platform_clock_test.sh` 同一個形狀（三行有效碼）：`HERE=…`、`export ABF_PLATFORM_PART=2`（或 `3`）、`exec bash "$HERE/platform_test.sh" "$@"`；檔頭註解說明「不是第二份拷貝，只選份數」。
- `set_platform_parts`（第 52–73 行）改成定義 `SHARDS_1`、`SHARDS_2`、`SHARDS_3`（每行一個分片，沿用現有格式），`LAST` 不變。**初始分配**（把現有 11 行依序分組，之後依第 0 步的量測調整）：
  - 第 1 份：現行第 55–58 行（`test_wrapper_nf2.py`；`test_wrapper.py`；`test_launch_nextflow.py`；`test_launch_e2e.py`＋`test_station_fakeplatform.py`＋`test_station_channel.py`）
  - 第 2 份：現行第 59–62 行（`test_station_cancel.py`＋`test_launch_cli.py`；`test_station_launch.py`＋`test_relay_loopback.py`＋`test_station_envs.py`；`test_station_resume.py`；五個 `test_resume_*.py`）
  - 第 3 份：現行第 63–65 行（`test_owner_binding.py`＋`test_pat.py`＋`test_human_channel.py`；`test_confirm_page.py`＋`test_owner_gaps.py`＋`test_launch_followup.py`＋`test_web_login.py`；五個 oauth／`test_keep_submissions.py`）
- **「其餘檔案」不再全進最後一個分片**：把沒被點名也不在 `LAST` 的 `tests/test_*.py` 以 `LC_ALL=C sort` 排序，第 i 個（從 0 起）進第 `(i mod 3)+1` 份的各自一個 `REST_n` 分片。這樣新增的測試檔自動有歸屬、且把目前塞在單一行程裡的大批檔案（`origin/v3` 有80 多個 `test_*.py`，被點名的分片檔加時鐘檔共 31 個）攤到三份。
- **調整規則（量測後）**：依第 0 步每個分片的秒數，整行搬移（不拆行）使三份各自的牆鐘時間（各項目單獨以 `time` 量）最大／最小 ≤ 1.5。若做不到，記進 ledger，不再硬調。
- `PART` 與要跑的內容：`1|2|3` 只跑該份的 `SHARDS_n`＋`REST_n`；`clock` 只跑 `LAST`；`all` 跑三份再跑 `LAST`。第 79、83、353、360 行的條件相應改寫；第 354–357 行的 `while` 與 `start_shard "$REST"` 合併成「對選到的分片逐個 `start_shard`」。
- `ABF_PLATFORM_LIST=1` 的輸出格式**不變**（`shard: <檔…>`、`alone: <檔>`，第 80–85 行），因為 `test_platform_parts.py` 第 15–24 行解析它。第 81 行的 `echo "shard:$REST"` 併入逐分片輸出（空的 `REST_n` 不印）。
- 摘要行 `platform tests: pytest exit …`（第 388 行）、`failing tests:`（第 383–387 行）、CI 不准有 skipped 的規則（第 389–392 行）照舊，四個項目共用同一段程式。
- `wait` 的退出碼蒐集（第 358、364 行）與 `$LOG.$n` 的合併（第 367–373 行）不變。

### 3. 共用／快取 bootstrap（決定：不新增機制）
- 現況：venv 在 `${XDG_CACHE_HOME:-$HOME/.cache}/abf-platform-venv`、下載與解壓在 `…/abf-platform`（第 40–42 行）。venv 以戳記 `.abf-stamp` 判斷是否重裝（第 196–204 行）；下載檔存在就只驗 sha256（第 133–136 行）；外掛已解壓且 `.abf-sha256` 相符就跳過（第 234、284 行）。
- 所以同一個 CI job 內，第一個項目付下載與 `pip install`，後面三個命中同一份快取，只剩對 6 個快取檔重算 sha256 與 `java -version`（第 208–212 行）。這就是「共用」，**本任務不再加快取機制，也不把 bootstrap 抽成另一支腳本**（會多一個要維護的接縫，而 `test_wrapper_nf2.py` 第 28–48 行靠讀 `platform_test.sh` 全文確認第二組 Nextflow 的設定，抽出去會弄壞它）。
- 要量：`time ABF_PLATFORM_PREFLIGHT_ONLY=2 bash tests/platform_test.sh`（快取暖的）寫進 ledger。**≤ 20 秒就接受**；超過就不優化、只記進 ledger 並列入「待 developer-agent 裁決」第 3 項。
- 必須保留的字面：`platform_test.sh` 第 307 行 `PREFLIGHT_ONLY:-}" = "2"`（`test_wrapper_nf2.py` 第 30 行靠它）、第 40 行 `${XDG_CACHE_HOME:-$HOME/.cache}`（`test_scope.py` 第 159 行靠它）。新增的註解不得出現 `/home/<名>/` 這類路徑（`test_scope.py` 第 146–148 行掃整個檔）。

### 4. 隔離名單規則（決定）
- `tests/run_all.sh` 第 160 行改成依 basename 的 `case`：`platform_test.sh|platform_clock_test.sh|platform_shard_*_test.sh` 一律拒絕，訊息沿用第 161 行的句型（`<base> may not be quarantined: it wraps the platform pytest suite, so quarantining it would let any platform test failure through`），退出路徑與其他拒絕相同（`bad=1; continue`）。
- **不用 `platform_*_test.sh`**：`tests/platform_direction_docs_test.sh` 與 `tests/platform_storage_doc_test.sh` 是只讀文件的檢查（檔頭自述 document checks only），不包平台 pytest，必須仍可被隔離。分片腳本因此固定命名為 `platform_shard_<n>_test.sh`。
- 防止日後有人加了分片卻忘了改規則：`test_platform_parts.py` 新增一條，掃 `tests/*.sh` 中含 `ABF_PLATFORM_PART=` 字樣的檔（現在是時鐘與兩支分片腳本），每個的 basename 必須符合 `platform_clock_test.sh` 或 `platform_shard_<n>_test.sh`，且 `run_all.sh` 的規則文字含 `platform_shard_*_test.sh`。
- `tests/quarantine.txt` 第 12 行註解改成列出四個名字（並說明只有這四支包平台 pytest）。

### 5. 文件與註解（逐行）
- `tests/run_all.sh` 第 46 行：`PER_TEST_TIMEOUT=300   # no test measured above ~30s; this only catches a hang` → `PER_TEST_TIMEOUT=300   # every entry, the four platform ones included, should finish well inside this; it only catches a hang`。**必須保留「only catches a hang」**（`test_platform_parts.py` 第 56–57 行的正則要它）。不寫任何秒數（避免再過期，同 `run_all_count_test.sh` 的原則）。
- `docs/TESTING.md` 第 13 行 `About 100 seconds, one verdict and a non-zero exit if anything fails.` → `Several minutes, mostly the four platform entries (`tests/platform_test.sh`, `tests/platform_shard_2_test.sh`, `tests/platform_shard_3_test.sh`, `tests/platform_clock_test.sh`); one verdict and a non-zero exit if anything fails.`
- `docs/TESTING.md` 第 16 行 `(default 300, only there to catch a hang)`：**內容仍然正確，不改**；PS-28 確認它還在。
- `docs/TESTING.md` 第 129、140、169 行的「The machine part is `tests/platform_test.sh` …」→ 「The machine part is the four platform entries (`tests/platform_test.sh`, `tests/platform_shard_2_test.sh`, `tests/platform_shard_3_test.sh`, `tests/platform_clock_test.sh`)」，其後的句子保留。第 133、137、159、161、177 行是各自功能的歷史驗收步驟，不動。
- `docs/PLATFORM.md` 第 648–649 行的兩行指令與註解改成四行（第 1、2、3 份、時鐘），註解不再說「every test file but two」；第 652 行說明段保留，加一句「`ABF_PLATFORM_PART=all` 在同一個項目跑全部」。
- `tests/platform_test.sh` 第 46 行、50–51 行、75 行與 328–339 行的註解改寫成新結構（四個項目、`REST` 輪流分到三份）；`tests/platform_clock_test.sh` 第 7–8 行（「Each entry now takes about half」）改成「四個項目中的一個」。
- 不改 `.github/workflows/tests.yml`（見「待 developer-agent 裁決」）。

### 受影響的既有斷言（已逐一核對 `origin/v3`）
會改：
1. `platform/tests/test_platform_parts.py::test_tcf3_02_every_test_file_is_in_exactly_one_entry`（第 27–33 行）：現在是 `main + clock`，改成四個項目的聯集等於所有檔、兩兩不相交。
2. 同檔 `test_tcf3_06_…`（第 44–50 行）：要多斷言兩支新腳本出現在 `run_all.sh --list`。
3. 同檔 `test_tcf3_03_…`（第 60–65 行）：迴圈 `for script in (MAIN, CLOCK)` 加入兩支分片腳本。
4. 同檔第 1–2 行檔頭與 docstring：改成描述四個項目。
不改但必須仍然通過（executor 要在 ledger 貼出綠）：
5. `test_tcf3_05_…`（第 36–41 行）：第 1 份全是 `shard`、不含時鐘檔；時鐘清單是 `alone` ×2。
6. `test_tcf3_04_…`（第 53–57 行）：上限 ≤ 300 且註解含 `only catches a hang`。
7. `tests/run_all_count_test.sh`：**不用改**。TC-001（第 12 行）只看 `run_all.sh` 前 20 行；TC-004（第 19–22 行）是動態比對 `--list` 行數與實際 `*.sh` 數，新增兩支腳本自動算進去。
8. `tests/run_all_retry_test.sh`：TC-053（第 303–306 行）與 TC-089（第 392–396 行）原樣通過；本任務只在檔尾（第 396 行之後、TC-090 之前或檔尾 `echo` 之前）**新增**案例，編號用 `PS-` 前綴避免撞到其他任務新增的 `TC-0xx`。
9. `platform/tests/test_wrapper.py`（`WRAPPER = …/platform_test.sh`，第 13 行）、`test_wrapper_nf2.py`（第 28–48 行）、`test_scope.py`（第 148、158、171 行）、`test_launch_static.py`（第 72 行）：只讀 `platform_test.sh` 的文字或以預檢模式執行，不受分片影響，只需保持上述字面（作法 3）。
10. `tests/run_all_test.sh`：`grep` 沒有任何 platform 字樣，不受影響。

## 失敗先行測試
「現在會紅」是指：在未改動的 `origin/v3` 上，這些測試因為旗標值／檔案不存在而失敗。

### A. 覆蓋（`platform/tests/test_platform_parts.py`，以 `ABF_PLATFORM_LIST=1` 解析清單，沿用該檔 `listed()`）
- PS-01 `ABF_PLATFORM_PART` 為 `1`、`2`、`3`、`clock` 四份清單的聯集，排序後恰等於 `platform/tests/test_*.py` 全部（`tests/` 前綴）。
- PS-02 四份清單合併後沒有重複檔（`len(set) == len`）。
- PS-03 `PART=all` 的清單聯集等於四份聯集，也等於全部檔。
- PS-04 時鐘兩檔不在第 1、2、3 份的任何分片；`PART=clock` 的清單恰為 `[("alone", ["tests/test_station_e2e.py"]), ("alone", ["tests/test_nextflow_e2e.py"])]`（順序不變）。
- PS-05 第 1、2、3 份各自非空，且每一行的種類都是 `shard`。
- PS-06 清單裡每個路徑都是磁碟上存在的檔（點名的檔被刪或改名會紅，而不是到 pytest 才報 not found）。
- PS-07 不設 `ABF_PLATFORM_PART` 的清單等於 `PART=1` 的清單。
- PS-08 `PART=main` 與 `PART=4` 都退出 1，訊息含 `must be 1, 2, 3, clock or all`。
- PS-09 把 `platform/` 複製到暫存目錄（`ABF_PLATFORM_DIR` 指過去，第 39、77 行），多放 7 個空的 `tests/test_zz_new_<i>.py`：這 7 個檔在三份中各恰出現一次，且三份的 `REST` 檔數兩兩相差 ≤ 1。
- PS-10 每個點名的分片行都不含時鐘檔（防止有人把 `LAST` 的檔又寫進分片）。
- PS-11 `tests/*.sh` 中含 `ABF_PLATFORM_PART=` 的檔，basename 必為 `platform_clock_test.sh` 或符合 `platform_shard_<n>_test.sh`；且 `run_all.sh` 全文含 `platform_shard_*_test.sh`。
- PS-12 `run_all.sh --list --allow-msys` 含 `platform_test.sh`、`platform_shard_2_test.sh`、`platform_shard_3_test.sh`、`platform_clock_test.sh`，不含 `run_all.sh`；四者都以 `_test.sh` 結尾。

### B. 真的跑得到（需暖快取與 Java，同 `test_wrapper.py` 的 `warm` fixture，第 36–43 行；沒有 Java 時該 fixture 會 skip，CI 上不准 skip 的規則照舊）
- PS-13 四個項目各以 `ABF_PYTEST_ARGS="--collect-only -q"` 執行：退出 0，輸出含 `platform tests: pytest exit 0`；各項目收集到的測試檔集合恰等於它的清單。
- PS-14 PS-13 四個項目收集到的檔案聯集恰等於 `platform/tests/test_*.py` 全部，且沒有檔出現在兩個項目（這是「實際跑」層級的覆蓋，PS-01 是清單層級）。
- PS-15 暖快取下連跑兩次預檢（`ABF_PLATFORM_PREFLIGHT_ONLY=2`，一次 `platform_test.sh`、一次 `platform_shard_2_test.sh`），第二次的輸出不含 `installing platform test dependencies`。
- PS-16 同上第二次，PATH 前面放一支記錄呼叫的假 `curl`：記錄檔為空（命中快取，沒有重新下載）。
- PS-17 CI 模式（`CI=true`）且 PATH 沒有 Java：四個項目全部退出非 0，輸出含 `FAIL (CI=true)`（改寫 `test_tcf3_03`）。

### C. 隔離名單（`tests/run_all_retry_test.sh` 新增，沿用該檔 `reset`／`mk_ok`／`setq`／`run $F`／`t`／`rc_is`／`err_has`，第 303–306 行為樣板）
- PS-18 `tests/platform_shard_2_test.sh #12 $D3`：退出 1；訊息含 `quarantine: tests/quarantine.txt:1:` 與 `platform_shard_2_test.sh`。
- PS-19 `platform_shard_3_test.sh`：同 PS-18。
- PS-20 假想的 `platform_shard_9_test.sh`（沙盒內建出來）：同樣被拒（規則是樣式，不是兩個名字）。
- PS-21 `platform_storage_doc_test.sh` 與 `platform_direction_docs_test.sh`（沙盒內建出來）仍可隔離：退出 0。
- PS-22 `platform_test.sh` 與 `platform_clock_test.sh` 仍被拒（既有 TC-053、TC-089 原樣綠，不改）。
- PS-23 真實樹 `bash tests/run_all.sh --check-quarantine` 退出 0（既有 TC-052 原樣綠）。
- PS-24 隔離名單檔 `tests/quarantine.txt` 第 12 行註解列出四個名字（`grep -F` 四次）。
- PS-25 `run_all.sh` 第 160 行規則仍是依 basename（不是依內容）：沙盒內檔名為 `platform_x_test.sh` 且內容含 `ABF_PLATFORM_PART=` 者，**不**被拒（鎖定「命名規則＋PS-11 守門」這個設計，不讓它悄悄變成內容掃描）。

### D. 上限與文件（`test_platform_parts.py`）
- PS-26 `run_all.sh` 的 `PER_TEST_TIMEOUT` 仍是 300，註解含 `only catches a hang`，且**不含** `~30s`（既有 `test_tcf3_04` 加一條）。
- PS-27 `docs/TESTING.md` 不含 `About 100 seconds`，含四個項目的檔名。
- PS-28 `docs/TESTING.md` 仍含 `default 300`（第 16 行沒被誤刪）。
- PS-29 `docs/TESTING.md` 不再有 `The machine part is `tests/platform_test.sh``（第 129、140、169 行已改）。
- PS-30 `docs/PLATFORM.md` 含四個項目的檔名，不含 `every test file but two`。
- PS-31 `tests/platform_test.sh` 與兩支分片腳本、時鐘腳本的註解不再出現「Two run_all.sh entries」與「about half」。

## 完成標準（done when）
1. **量測帳本**：`specs/platform-test-shards/ledger.md` 貼上改前的第 0 步輸出（前 30 慢測試、每分片秒數、兩個項目現況牆鐘時間），與改後四個項目各自 `time` 的牆鐘時間（WSL／Linux，暖快取），以及 `ABF_PLATFORM_PREFLIGHT_ONLY=2` 暖預檢秒數。閱卷者依 README 通例看 ledger 並自己重跑核對。
2. 改後四個項目中最慢的牆鐘時間 ≤ 改前 `platform_test.sh` 牆鐘時間的 45%；三份的最大／最小 ≤ 1.5（做不到要在 ledger 寫明原因與測得的數字）。
3. 本計畫所有案例（PS-01…PS-31）綠；`bash tests/run_all.sh --only platform` 與 `bash tests/run_all.sh` 全綠。
4. 「受影響的既有斷言」第 5–10 項在 ledger 貼出綠的輸出。
5. `git diff --stat` 貼進 ledger，且只含「範圍：檔案」列的 10 個檔（`hooks/*`、`.github/*`、`platform/abf_*` 無任何變動；依 README 通例由閱卷者看 diff 確認）。
6. 本機 `bash tests/run_all.sh --list --allow-msys` 的行數比改前多 2。
7. **CI 上的結果不在本任務完成標準內**（要等合併後才有），列在「待 developer-agent 裁決」第 2 項。

## 環境事實
- 只能在 Linux／WSL 跑（`tests/run_all.sh` 第 283–306 行：原生 Git Bash 會拒絕，`--allow-msys` 才硬跑）；平台測試要 Python ≥ 3.10、Java ≥ 17、可連網下載 Nextflow（第 171–178、206–219 行）；沒有 Java 時本機會 `E2E SKIPPED`、CI 上直接紅（第 104–111 行）。
- `run_all.sh` 一次只跑一個項目、循序（第 382–404 行），所以時鐘項目仍然單獨執行；CI 是單一 job（`.github/workflows/tests.yml` 第 38–50 行，`timeout-minutes: 60`），四個項目共用同一個 `$HOME` 快取。
- CI runner 只有兩核，所以項目內平行的分片數不是越多越快；這也是用「分組到不同項目」而不是「加更多平行行程」的原因（`platform_test.sh` 第 332–333 行已記一次兩核上時鐘檔因分片忙碌而失敗）。
- `--retry-failed-once` 只重跑失敗的整個檔、逾時的不重跑（`run_all.sh` 第 231–237 行）；拆成四個項目後，重跑的單位變小，平台項目偶發紅時的重跑成本也跟著降低。
- 同車道的 `flaky-tests` 會動 `test_station_e2e.py`／`test_nextflow_e2e.py`（時鐘項目跑的檔）；兩任務檔案不相交，但時鐘項目的秒數會因它改變，所以本任務的量測在 ledger 註明量測時的 `v3` commit。

## 不做
- 不改 `.github/workflows/tests.yml`、`hooks/*`、`platform/abf_*`。
- 不改任何平台測試的內容、不加速個別慢測試（先量，之後有依據再開任務）。
- 不做 `pytest-xdist` 或其他平行化外掛：現有的「每個分片一個 pytest 行程」已是平行，且本任務的目標是降低每個項目的牆鐘，不是總 CPU；要不要引入 xdist 另案（搜尋與選型不在本任務）。
- 不抽出共用 bootstrap 腳本、不加新的快取機制（作法 3）。
- 不調高 `PER_TEST_TIMEOUT`，也不把平台項目加進隔離名單的可隔離範圍。
- 不新增第四份分片（若量測顯示需要，見「待 developer-agent 裁決」第 2 項）。

## 待 developer-agent 裁決
1. **`.github/workflows/tests.yml` 的改動（你自己改，本任務不碰）**：
   - 第 50 行 `run: bash tests/run_all.sh --retry-failed-once --timeout 900 2>&1 | tee "$RUNNER_TEMP/run_all.out"` → 去掉 `--timeout 900`，成為 `bash tests/run_all.sh --retry-failed-once 2>&1 | tee "$RUNNER_TEMP/run_all.out"`（預設 300 秒，`run_all.sh` 第 46 行）。
   - 第 28–29 行註解 `--timeout 900 matches the local runner (memory/scripts/abf-fast-suite.sh); platform_test.sh grew past 300 s on CI runners.` 改成「the platform tests run as four entries so each fits the default per-test limit」之類，並把第 29 行改成不再提 900。
   - 時機：本任務合併後、你確認 CI 上四個項目各自秒數（`run_all.out` 的 `ok  <n>s` 行）才改；改的 PR 屬 `.github/` 受保護路徑，需 `/code-review`。
2. **合併後的 CI 門檻**：四個平台項目在 CI 上各自 ≤ 150 秒才算「遠低於 300」。若任何一個 > 200 秒，需要你決定再加第 4 份（新增 `platform_shard_4_test.sh`＋第 160 行規則已涵蓋＋清單函式的 `% 3` 改 `% 4`），**不是**調高上限。
3. **要不要在 CI 加 `actions/cache`**（快取 `~/.cache/abf-platform*`，key 用 `hashFiles('platform/tests/pins.env','platform/constraints.txt')`）：能省第一個項目的下載與 `pip install`，但屬 `.github/` 改動；若暖預檢（作法 3）> 20 秒也一併考慮。這是選配，不影響本任務完成。
4. **`memory/scripts/abf-fast-suite.sh`（工作區，非 repo）** 若仍帶 `--timeout 900`，拆分後可一起拿掉，由你決定。
5. **TESTING.md 同時被其他任務動**：`flaky-tests` 的不准動清單把 `docs/TESTING.md` 列為別的任務正在動的檔；本任務只改第 13、129、140、169 行，若合併時衝突，由你協調順序。

## 裁決
1. A 級；專長守則用 `backend`；verifier 通過＋CI 綠後由 developer-agent 自己合併。
2. 項目數定為四個（三份分片＋時鐘）；不是五個。若合併後 CI 實測不夠，走「待 developer-agent 裁決」第 2 項。
3. 命名定為 `platform_shard_<n>_test.sh`，隔離規則用 basename 樣式 `platform_shard_*_test.sh` 加兩個既有名字；**不用** `platform_*_test.sh`（會誤傷兩支文件檢查）。
4. `ABF_PLATFORM_PART` 預設 `1`，舊值 `main` 不再接受（沒有任何呼叫者）。
5. 其餘檔案（`REST`）以排序後輪流分到三份，不再全進最後一個分片；新增的測試檔自動有歸屬，不必改清單。
6. 重新分配分片只准整行搬移，不拆行；依量測結果做一次，不反覆調。
7. 不新增 bootstrap 快取機制；暖預檢 > 20 秒只記錄、不優化。
8. 註解與文件一律不寫秒數（避免再過期）；`PER_TEST_TIMEOUT` 註解必須保留 `only catches a hang`。

## 裁決二（2026-10-24 21:00 developer-agent）
1. tests.yml 的 `--timeout 900` 等合併後 CI 實測每支 ≤150 秒再由 developer-agent 拿掉；超過 200 秒就加第 4 份，不調高上限。
2. CI cache、abf-fast-suite 的 `--timeout 900` 不在本任務；fast-suite 的值由 developer-agent 之後一起調。
3. 用 `PS-` 前綴編號接受；以 SHA 定位；docs/TESTING.md 衝突合併時兩邊都留。

## 裁決三（2026-10-24 21:10 developer-agent，回應出題退回；以本段為準）
1. PS-11 只掃「行首（可有空白）`export ABF_PLATFORM_PART=` 或 `ABF_PLATFORM_PART=` 開頭的賦值行」，且明確排除 `tests/run_all_retry_test.sh`（它的沙盒會造假檔）與 `tests/platform_test.sh` 本身（被包裝的那支）。註解行不算。
2. 完成標準第 2 條改成：**三支分片（part 1、2、3）各自的牆鐘時間 ≤ 改前 platform_test.sh（main 部分）牆鐘時間的 45%；時鐘項目不變、不得比改前慢超過 10%**。CI 目標另寫：合併後每支 ≤150 秒（量測記進 ledger，由 developer-agent 看 CI 判定）。
3. 憲法條文提到「由 tests/platform_test.sh 跑」的字面不精確，本任務不改憲法；PS-77 證明檔案沒掉，developer-agent 記一筆之後另案修條文。
4. 手動驗證照通例（看 diff／ledger／自己在 WSL 重跑）。

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
