# 測試案例：三支常誤報的測試改成確定性（flaky-three）

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
這個任務沒有 spec.md，只有 plan.md；「對應需求」欄引用 plan 的章節。
所有預期結果都來自 plan 寫明的內容，沒有另外發明行為。
-->

**規格**：`specs/flaky-three/plan.md`（無 spec.md）　**總覽**：`test-case-overview.md`

類型只有三種：

- **功能**：計畫說要做到的事，做到了。
- **例外**：出錯、重現不了、故意弄壞時，測試怎麼反應。
- **不在範圍**：計畫明講不做或禁止的事；確認它真的沒做。

名詞：

- **ledger**＝`specs/flaky-three/ledger.md`，執行者記錄每一步指令與輸出的檔案。
- **base**＝計畫所說的 `origin/v3`（`946da8a`）上的舊版測試檔。
- **忙迴圈**＝在背景跑一個空轉到底的 shell 迴圈把 CPU 吃滿，用來模擬機器很忙：`for i in $(seq 16); do ( while :; do :; done ) & done`，做完要 `kill` 掉。
- **比例檢查**＝計畫作法 1 新增的檢查：同一台機器上，1 MB 的指令花的時間除以 60 KB 的指令花的時間，必須 ≤ 40。機器忙時兩邊一起變慢，比值不變，所以它量的是「演算法是不是線性成本」，不是「這台機器快不快」。
- **`.pyc`**＝Python 編譯後的快取檔，在 `__pycache__` 資料夾，被 `.gitignore` 忽略，不是程式碼。
- **暫存副本**＝在 WSL 另 clone 的資料夾（計畫「環境事實」的 `~/abf-flaky3`），所有故意弄壞的實驗只在這裡做，不進 commit。
- **O(n)**＝成本和輸入大小成正比（大小變 16 倍、時間大約也變 16 倍）；平方成本則會變 256 倍。

## User Story 1 — confirm_launch：大輸入的時間預算改成確定性（優先度 P1）

這一段對應計畫「作法 1」。要測的是 `tests/confirm_launch_test.sh` 的 `envbig`（21 個案例、15 個呼叫行）。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 失敗先行測試；作法 1 | 功能 | 還沒改 `tests/confirm_launch_test.sh`（base 版）；在 WSL 暫存副本 | 開 16 個忙迴圈（記下 PID），同時跑 `bash tests/confirm_launch_test.sh`，結束後 `kill` 全部忙迴圈 | ledger 貼出指令與輸出，輸出裡有 `FAIL: slow (… ms)`（1 MB 案例，大約 2.0～2.9 秒）；若沒有紅，ledger 要如實寫「重現不了」並回報，不得宣稱已重現 | 手動：閱卷者讀 ledger |
| TC-002 | 完成標準 2；作法 1 | 功能 | 改好之後；同 TC-001 的 16 個忙迴圈條件 | 跑 `bash tests/confirm_launch_test.sh` | 整檔結束碼 0、輸出沒有任何 `FAIL`；ledger 貼出結果 | 手動：閱卷者讀 ledger，並自己在忙迴圈下跑一次 |
| TC-003 | 完成標準 2；作法 1 | 功能 | 改好之後，機器閒置 | 跑 `bash tests/confirm_launch_test.sh` | 整檔結束碼 0、輸出沒有任何 `FAIL` | 自動：`tests/confirm_launch_test.sh` |
| TC-004 | 完成標準 2 | 功能 | 改好之後 | 負載下（16 忙迴圈）連跑 10 次、閒置連跑 10 次 | ledger 貼出 20 次每一次的結果：每次都全綠；並貼出每次的 `ok (NNN ms)` 行與比例檢查行；沒有任何一次紅 | 手動：閱卷者讀 ledger 並數次數 |
| TC-005 | 作法 1 改法 1；完成標準 5 | 功能 | 改好之後 | 執行 `grep -nE '^ *envbig ' tests/confirm_launch_test.sh`，再看 `envbig` 函式本體 | 列出 15 行；每一行的第 4 個引數都不再是純數字（原本的 500／1000／1500 都沒了）；函式註解與本體不再有 `<limit ms>` 參數，也不再有 `[ "$ms" -lt "$4" ]` 這一行 | 手動：閱卷者自己重跑 grep |
| TC-006 | 作法 1 改法 1；完成標準 5 | 功能 | 改好之後 | 看 `BIG_CEIL_MS` 的定義與使用 | 函式上方有 `BIG_CEIL_MS=10000`，旁邊註解寫明它等於第 604–608 行「hook timeout 下限 30 秒」的三分之一；`grep -c 'BIG_CEIL_MS' tests/confirm_launch_test.sh` ≥ 2；原第 967 行的比較改成 `[ "$ms" -lt "$BIG_CEIL_MS" ] \|\| { ok=0; why="$why slow"; }`；`ok (NNN ms)` 的輸出格式照舊 | 手動：閱卷者讀差異並重跑 grep |
| TC-007 | 作法 1 改法 1（15 個呼叫行、21 個案例） | 功能 | base 與改好版各在閒置下跑一次 | 比對兩次輸出裡 `envbig` 印出的案例標籤（`TC-048`、`TC-049`、`TC-050`、`TC-051`、`POL-4`、`POL-19`、`POL-20`、`POL-21`、`POL-22`、`POL-22b`、`POL-19b`、`POL-lk25`、`POL-lk25b`、`POL-lk25c` 各自的 EXTRA／PEER 版本） | base 印出的 21 個案例標籤改好版全部還在、每條都是 `ok`；其餘引數（must-contain／must-not-contain）在 15 個呼叫行裡一字不改，只少了那個數字 | 手動：閱卷者在兩個版本各跑一次並比對標籤清單，貼進驗收報告 |
| TC-008 | 作法 1 改法 1（其餘引數「一字不改」，不得因拿掉參數而失效） | 例外 | 在暫存副本的改好版，故意改壞三處（互不相干，各跑一次）：(a) 把某個 must-contain 期望字串改成不存在的 `ZZZ`；(b) 把某個 must-not-contain 改成輸出裡確實有的字串；(c) 把 `H` 換成一支永遠回 allow 的假 hook | 各跑一次 `bash tests/confirm_launch_test.sh` | (a) 該案例變紅，訊息含 `missing ZZZ`；(b) 該案例變紅，訊息含 `has`；(c) 所有 `envbig` 案例變紅，訊息含 `not ask`；這證明拿掉第 4 個參數後，內容斷言與閘門斷言仍然在咬 | 手動：閱卷者在暫存副本自己做，結果貼進驗收報告 |
| TC-009 | 作法 1 改法 2；維護者原話「成本 O(n)」 | 功能 | 改好之後，機器閒置 | 跑 `bash tests/confirm_launch_test.sh`，看兩行 `TC-051 EXTRA_DOMAINS O(n): 1 MB tail / 60 KB tail <= 40` 與 `TC-051 PEER_PREFIXES O(n): 1 MB tail / 60 KB tail <= 40` | 兩行都出現，都是 `ok`；比值用的是 `MS_tail1m_<V>` 除以 `MS_tail60_<V>`（同一個 V） | 自動：`tests/confirm_launch_test.sh` |
| TC-010 | 作法 1 改法 2 | 功能 | 同上 | 看 `TC-051 EXTRA_DOMAINS O(n): 1 MB spread / 60 KB spread <= 40` 與 `TC-051 PEER_PREFIXES O(n): 1 MB spread / 60 KB spread <= 40` | 兩行都出現，都是 `ok`；比值用的是 `MS_spread1m_<V>` 除以 `MS_spread60_<V>` | 自動：`tests/confirm_launch_test.sh` |
| TC-011 | 作法 1 改法 2 | 功能 | 同上 | 看 `TC-032 O(n): 1 MB look-alikes / 60 KB tail <= 40` | 出現且 `ok`；比值用的是 `MS_lookalike1m_NF_RELAY_PEER_PREFIXES` 除以 `MS_tail60_NF_RELAY_PEER_PREFIXES` | 自動：`tests/confirm_launch_test.sh` |
| TC-012 | 完成標準 5；作法 1 改法 2 | 功能 | 改好之後 | (a) 執行 `grep -c 'O(n)' tests/confirm_launch_test.sh`；(b) 跑整檔，數輸出裡含 `O(n)` 的行 | (a) 恰為 5；(b) 恰為 5 行；每行格式與檔內其他檢查一致（標籤、`ok` 或 `FAIL`）。因為原始碼要有 5 行，比例檢查須寫成 5 行獨立文字，檔內其他地方（含註解）不得再出現 `O(n)` | 手動：閱卷者自己重跑 grep 與整檔 |
| TC-013 | 失敗先行測試 反向條件 (i)；維護者原話「讓測試變確定性只能更嚴」 | 例外 | 在暫存副本把 `H` 換成一支包裝腳本：讀完 stdin 後，依位元組數的平方 `sleep`（60 KB 約 0.03 秒、1 MB 約 8.3 秒），再轉呼叫真 hook | 在閒置下跑改好版的 `bash tests/confirm_launch_test.sh` | 比例檢查必紅（比值約 60，大於 40），FAIL 訊息印出兩個 ms 與比值；但 10 秒絕對上限本身不紅（輸出裡沒有 `slow`）；ledger 貼出此次輸出。這證明新檢查擋得住平方成本，而舊的 1000 ms 預算在這種情況下反而是靠機器快才不擋 | 手動：閱卷者在暫存副本自己做 |
| TC-014 | 失敗先行測試 反向條件 (ii) | 例外 | 在暫存副本把 `H` 換成一支包裝腳本：固定 `sleep 11` 再轉呼叫真 hook | 在閒置下跑改好版 | 21 個 `envbig` 案例都變紅，訊息含 `slow`（超過 10 秒上限）；ledger 貼出此次輸出 | 手動：閱卷者在暫存副本自己做 |
| TC-015 | 作法 1 改法 2（除以 0 時把分母當 1） | 例外 | 改好之後 | 讀比例檢查的程式；再跑整檔並看標準錯誤輸出 | 程式裡有「分母為 0（或小於 1）時當 1」的處理；整檔跑完標準錯誤沒有 `division by 0` 之類的算術錯誤 | 手動：閱卷者讀程式並跑一次 |
| TC-016 | 裁決 5 待裁決 1；「不做」最後一條 | 功能 | 改好之後 | 看 `git diff` 對 `specs/relay-warning-hardening/` 的影響與 ledger | `specs/relay-warning-hardening/test-case.md` 沒被改（「都 < 1 秒」「< 0.5 秒」字句原樣）；ledger 有一句明寫「由 flaky-three 裁決 5（維護者 10-27 選『照建議改』）取代」 | 手動：閱卷者讀差異與 ledger |
| TC-017 | 範圍：檔案（第 74 行與第 596–612 行一字不動）；完成標準 8 | 功能 | 改好之後 | 看 `git diff origin/v3...HEAD -- tests/confirm_launch_test.sh` 的所有區塊位置，並看第 74 行與第 596–612 行 | 所有改動區塊都在第 940 行以後；第 74 行仍是原句（`docs/TESTING.md:520` 釘的那句）；第 596–612 行（`#29 every … entry has timeout >= 30s`）與 base 逐字相同 | 手動：閱卷者讀差異 |
| TC-018 | 作法 1 末段（不可攜寫法）；完成標準 8 | 功能 | 改好之後 | 看 `tests/confirm_launch_test.sh` 的新增行，並跑 `bash tests/portable_userland.sh` | 新增行沒有 `grep -P`、`xargs -r`、`mapfile`、`declare -A`；`MS_<kind>_<var>` 是用 `eval` 設的普通變數，不是關聯陣列；`portable_userland.sh` 結果綠 | 手動：閱卷者讀差異並跑該檔 |

## User Story 2 — jev_test.sh TC-085：不再被 `.pyc` 誤報（優先度 P1）

這一段對應計畫「作法 2」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 失敗先行測試；作法 2 | 功能 | base 版 `tests/jev_test.sh`；暫存副本 | 先執行計畫指定的 `python3 -c 'import py_compile; py_compile.compile("platform/tests/test_web_board.py", cfile="platform/tests/__pycache__/test_web_board.cpython-310.pyc", doraise=True)'`，再跑 `bash tests/jev_test.sh` | 輸出有 `TC-085 … FAIL: got '1', wanted '0'`；ledger 貼出指令與輸出 | 手動：閱卷者讀 ledger |
| TC-020 | 作法 2；維護者原話「修掉或隔離那三支」 | 功能 | 改好版；同 TC-019 的 `.pyc` 還在（不清掉） | 跑 `bash tests/jev_test.sh` | `TC-085` 那行是 `ok`，整檔沒有 `FAIL` | 自動：`tests/jev_test.sh` |
| TC-021 | 完成標準 3 | 功能 | 改好版；鏡像裡**先放進** 3 個含 `jev` 的 `.pyc`（對 `test_web_board.py`、`test_web_settings.py`、`test_web_running.py` 各 `py_compile`），不清掉 | 連跑 `bash tests/jev_test.sh` 20 次 | ledger 貼出 20 次結果，全部綠；沒有任何一次紅 | 手動：閱卷者讀 ledger |
| TC-022 | 失敗先行測試 正向控制；作法 2「失敗時直接列出違規檔名」 | 例外 | 改好版；在 `platform/` 底下新增一個**未追蹤、未被忽略**的 `platform/zz_probe.py`，內含 `jev` | 跑 `bash tests/jev_test.sh`，之後刪掉該檔再跑一次 | 有檔時 `TC-085` 變紅，失敗訊息列出 `platform/zz_probe.py` 這個檔名；刪掉後恢復綠；ledger 貼出兩次輸出 | 手動：閱卷者自己做一次 |
| TC-023 | 作法 2（`-i` 保留原本大小寫不分） | 例外 | 改好版；`platform/` 底下新增未追蹤的檔，內容只有 `JEV`（大寫） | 跑 `bash tests/jev_test.sh` | `TC-085` 變紅並列出該檔名（大小寫不分仍然成立）；刪檔後恢復綠 | 手動：閱卷者自己做一次 |
| TC-024 | 作法 2；完成標準 5 | 功能 | 改好之後 | 執行 `sed -n 487,488p tests/jev_test.sh \| grep -c 'git ls-files -co --exclude-standard'`，並 `grep -n 'grep -rli' tests/jev_test.sh` | 第一個指令結果為 2（第 487 行 `-- platform`、第 488 行 `-- hooks`，兩行同形）；第二個指令沒有輸出（整檔沒有 `grep -rli`）；改動只在第 487–488 行 | 手動：閱卷者重跑兩個指令並看差異 |
| TC-025 | 作法 2（期望值由數量 0 改成清單為空；不得接 `grep -q`） | 功能 | 改好之後 | 看第 487–488 行的比較值，並跑 `bash tests/no_pipefail_grep_q_test.sh` | 兩行的期望值是空字串 `""`（不是數字 0），實際值是違規檔名清單；新增行沒有把管線接到 `grep -q`；`no_pipefail_grep_q_test.sh` 綠 | 手動：閱卷者讀差異並跑該檔 |
| TC-026 | 作法 2（第 488 行 TC-075 同形改寫） | 例外 | 改好版；在 `hooks/` 底下新增一個內含 `jev` 的檔 | 跑 `bash tests/jev_test.sh` | `TC-075` 變紅，訊息列出該檔名；刪掉後恢復綠。這證明 hooks 那一行改寫後仍然擋得住 | 手動：閱卷者在暫存副本自己做 |
| TC-027 | 作法 2「少擋」須在 ledger 寫一句 | 功能 | 改好之後 | 讀 ledger | ledger 有一句寫明：少擋的是「被 `.gitignore` 忽略的檔與二進位」，理由是它們不是 `platform/` 的程式碼，並引用 `specs/015-jev-triage/test-case.md:128` 的「搜尋 `platform/`」 | 手動：閱卷者讀 ledger |

## User Story 3 — test_station_e2e.py tc014：等待窗只放寬上限（優先度 P1）

這一段對應計畫「3b」。`test_tc014_idle_polls_end_quietly_and_keep_the_last_contact_moving`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-028 | 失敗先行測試（tc014）；3b | 功能 | 暫存副本，**舊寫法**；在「算出 4.5 秒結束時間那一行之後、進 `while` 迴圈之前」插入 `time.sleep(3)`（讓舊的 4.5 秒窗只剩 1.5 秒；插在算結束時間之前不會有效果） | 跑這一個測試 | 舊寫法變紅，訊息為 `the last contact did not move with each poll: …`；同樣的插入放進**改好版**（插在算出最短結束時間之後、迴圈之前）則仍然綠；ledger 貼出兩次輸出，並說明插入只存在於暫存副本 | 手動：閱卷者在暫存副本自己做 |
| TC-029 | 3b 改法；維護者原話「放寬等待上限而不是放寬斷言」 | 功能 | 改好之後 | 讀 `test_tc014…` 的程式 | 迴圈改成「至少跑 4.5 秒、且 `len(seen) >= 3` 才停；最晚 `deadline = time.time() + 30`」；`assert len(seen) >= 3, "the last contact did not move with each poll: %r" % sorted(seen)` 與訊息原樣；對代理輸出「沒有 Traceback／cannot reach／stopped:／will not start」的檢查原樣 | 手動：閱卷者讀差異 |
| TC-030 | 3b（保留原本 4.5 秒的最短觀察） | 功能 | 改好之後，正常機器 | 用 `pytest -k tc014 --durations=5` 跑，看這個測試花的時間 | 耗時不少於 4.5 秒（不會因為提早看到 3 個值就在 4.5 秒前停下，以免「安靜結束」的檢查覆蓋時間變短）；ledger 貼出耗時 | 手動：閱卷者自己跑一次並讀耗時 |
| TC-031 | 完成標準 4 | 功能 | 改好之後 | 在 `platform/` 的 venv 跑整檔 `pytest tests/test_station_e2e.py -q -p no:cacheprovider`（`side` fixture 四個場景一起起，不能只挑一個） | 全綠；ledger 貼出連跑 5 次的結果 | 自動：`platform/tests/test_station_e2e.py` |
| TC-032 | 完成標準 4 | 功能 | 改好之後 | 同時開 4 份：`for k in 1 2 3 4; do pytest tests/test_station_e2e.py -q -p no:cacheprovider & done; wait` | 4 份全部綠；ledger 貼出指令與四份各自的結果 | 手動：閱卷者讀 ledger |
| TC-033 | 3b（「最晚 30 秒」是真的上限，不是無窮等待） | 例外 | 暫存副本的改好版，讓 `agents_rows` 永遠回傳同一個值（接觸時間永遠不動） | 跑這一個測試 | 測試以同一句 `the last contact did not move with each poll: …` 失敗，約在 30 秒左右（不是 4.5 秒就結束，也不是卡住不結束）；ledger 貼出耗時與訊息 | 手動：閱卷者在暫存副本自己做 |

## User Story 4 — httpx 預設 5 秒逾時：全部帶上 60 秒（優先度 P1）

這一段對應計畫「3c」。涉及 `platform/tests/test_launch_e2e.py` 5 個呼叫、`platform/tests/test_station_e2e.py` 6 個呼叫，共 11 個。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-034 | 3c；完成標準 5 | 功能 | 改好之後 | 執行 `grep -nE 'httpx\.(get\|post\|put\|delete\|patch\|request)\(' platform/tests/test_launch_e2e.py platform/tests/test_station_e2e.py`，逐處看該呼叫及其後兩行 | 列出的 11 處（launch 5、station 6）每一處（跨行的呼叫也要）都含 `timeout=HTTP_TIMEOUT` | 手動：閱卷者自己重跑 grep 並逐處核對 |
| TC-035 | 3c | 功能 | 改好之後 | 看兩個檔的模組開頭 | 各自有 `HTTP_TIMEOUT = 60`，旁邊註解寫明 httpx 預設是 5 秒、跑在負載下的 runner 超過過（CI run 40099957808）；兩檔數值同為 60 | 手動：閱卷者讀差異 |
| TC-036 | 失敗先行測試（httpx，日誌證據）；裁決 3 | 功能 | 改好之後 | 讀 ledger | ledger 貼出 CI run `40099957808` 日誌裡 `test_tc020… httpx.ReadTimeout: timed out` 的原文，以及 venv 內 `python -c 'import httpx; print(httpx.__version__, httpx._config.DEFAULT_TIMEOUT_CONFIG)'` 的輸出（0.28.1、預設逾時 5.0）；ledger 明寫這條是「日誌證據，不是強制重現」 | 手動：閱卷者讀 ledger |
| TC-037 | 3c（狀態碼與回傳內容的斷言一字不改） | 功能 | 改好之後 | 看這兩個檔的 `git diff` | 被刪的每一行都有一行對應的新增行，兩者只差 `timeout=HTTP_TIMEOUT`（與換行排版）；沒有任何 `assert` 被刪、被改、被放寬 | 手動：閱卷者逐行對照差異 |
| TC-038 | 完成標準 4 | 功能 | 改好之後；本機有 Java 與 Nextflow | `test_launch_e2e.py` 整檔連跑 3 次 | 全綠，ledger 貼 3 次結果；若本機沒有 Java／Nextflow，ledger 明寫「本機沒有、交 CI」，且 CI 該項為綠 | 手動：閱卷者讀 ledger 與 CI |
| TC-039 | 範圍：檔案 | 功能 | 改好之後 | 看 `test_station_e2e.py` 與 `test_launch_e2e.py` 的 `git diff` 區塊位置 | `test_station_e2e.py` 只有 tc014 第 414–423 行附近與第 474、512、666、670、674、877 行的 `httpx` 呼叫（加模組常數例外）；`test_launch_e2e.py` 只有第 118、120、125、127、179 行與模組常數；其餘行沒有變動 | 手動：閱卷者讀差異 |

## User Story 5 — platform 四支包裝檔：只交付量測與說明（優先度 P2）

這一段對應計畫「3a、3d」與完成標準 6。測試檔修不掉的部分，本任務不修、也不隔離，只留下證據。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-040 | 3a | 功能 | 改好之後 | 讀 ledger | ledger 有一段說明 CI 的 `platform_test.sh TIMEOUT 300s`（6 次）全在 PR #200 合併（2026-10-24T14:00:14Z）之前，已被拆分修掉，本任務沒有再做任何事 | 手動：閱卷者讀 ledger |
| TC-041 | 完成標準 6；裁決 5 待裁決 3 | 功能 | 鏡像裡，單獨跑 | 分別跑 `ABF_PLATFORM_PART=1 bash tests/platform_test.sh`、`…=2`、`…=3`，並用 `ABF_PLATFORM_LIST=1` 列出各 shard 檔名清單 | ledger 有一張表：三個 shard 各一列，含每個 shard 輸出最後的 `N passed in X s` 行與 shard 檔名清單；三列都有數字，不是空欄 | 手動：閱卷者讀 ledger |
| TC-042 | 維護者原話「修不掉的才隔離，且要說是哪支、為什麼」；3d | 功能 | 改好之後 | 讀 ledger | ledger 寫明：本機 900 秒 TIMEOUT 與 573～893 秒險綠屬「兩套全套並跑的容量問題」、測試檔修不掉；點名是 platform 四支包裝檔（不得隔離）；結論交 developer-agent 看量測表決定（待裁決 3），本任務沒有修也沒有隔離 | 手動：閱卷者讀 ledger |

## User Story 6 — 只更嚴、不更鬆、範圍不外溢（優先度 P1）

這一段對應計畫「作法」通則、完成標準 5、7、8、9 與維護者原話「讓測試變確定性只能更嚴」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-043 | 完成標準 7；範圍：檔案 | 功能 | 改好之後 | 執行 `git diff --stat origin/v3...HEAD`（含未提交的 `git diff`） | 只列四個測試檔（`tests/confirm_launch_test.sh`、`tests/jev_test.sh`、`platform/tests/test_station_e2e.py`、`platform/tests/test_launch_e2e.py`）與 `specs/flaky-three/` 底下的檔；沒有其他路徑 | 手動：閱卷者自己重跑 |
| TC-044 | 完成標準 5 最後一條；作法通則；裁決 2 | 功能 | 改好之後 | 對**四個測試檔**的差異（`git diff -- tests platform/tests`）執行 `grep -nE '^\+.*(skip\|xfail\|flaky\|retry\|rerun)'` | 無輸出（英文註解裡的敘述性用法除外，須在 ledger 說明）；沒有 skip／xfail／重試裝飾器或迴圈 | 手動：閱卷者自己重跑 |
| TC-045 | 作法通則；維護者原話「放寬等待上限而不是放寬斷言」 | 功能 | 改好之後 | 逐一比對四個測試檔的差異，看被刪或被改的比較與斷言 | 沒有任何斷言被刪；沒有比較值被改鬆（唯一比較值變大的是 `envbig` 的 500／1000／1500 → `BIG_CEIL_MS=10000`，對應裁決 5 待裁決 1）；沒有預期值改成配合新輸出；`tc014` 的 `assert len(seen) >= 3` 原樣 | 手動：閱卷者讀差異 |
| TC-046 | 維護者原話「讓測試變確定性只能更嚴」 | 功能 | 改好之後 | 讀 ledger | ledger 對每一處改動（envbig、TC-085／TC-075、tc014、httpx 逾時）各寫一句「比原本多擋了什麼、少擋了什麼」；任何「少擋」都標明對應的裁決條文 | 手動：閱卷者讀 ledger |
| TC-047 | 完成標準 8 | 功能 | 改好之後 | 逐一跑 `tests/no_pipefail_grep_q_test.sh`、`tests/portable_userland.sh`、`tests/run_all_count_test.sh`、`tests/constitution_scope_test.sh`（第 274 行四支名單不動）、`tests/hooks_fail_closed_test.sh`、`tests/gates_without_jq_test.sh` | 六支都綠；ledger 逐支點名；`constitution_scope_test.sh` 第 274 行的名單與 base 相同 | 自動：上列六個測試檔 |
| TC-048 | 完成標準 8 | 功能 | 改好之後 | 跑 `bash tests/jev_test.sh`，看 `TC-020`（第 485 行）與 `TC-044`（第 397 行） | 兩行都是 `ok` 且寫法沒被動到；ledger 點名 | 自動：`tests/jev_test.sh` |
| TC-049 | 完成標準 8 | 功能 | 改好之後 | 在 `platform/` 的 venv 跑 `pytest tests/test_scope.py -k tc072` | 綠：新增的行裡沒有個人路徑或叢集路徑；ledger 點名 | 自動：`platform/tests/test_scope.py` |
| TC-050 | 完成標準 9；專案事實的完成記號 | 功能 | 改好之後，已提交，工作樹乾淨 | 在 WSL 跑 `bash tests/run_all.sh`；看 `executor-status` 與 CI | 全套綠；`executor-status` 為 `GREEN <HEAD sha>`；CI 綠 | 自動：`tests/run_all.sh` |

## User Story 7 — 不在範圍（優先度 P1）

這一段對應計畫「不做」「不准動」「待裁決 2、3、4」。每一條都是「確認它真的沒做」。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-051 | 不做：其餘 `httpx` 呼叫；裁決 5 待裁決 2 | 不在範圍 | 改好之後 | 看 `test_cli.py`、`test_pat.py`、`test_station_envs.py`、`test_oauth_mcp.py`、`test_confirm_page.py`、`oauth_harness.py`、`test_human_channel.py`、`test_oauth.py`、`test_review_fixes.py`、`test_web_login.py` 的差異 | 全部沒有任何變動；這 11 個檔的不帶 `timeout=` 的 `httpx` 呼叫維持原樣 | 手動：閱卷者看 `git diff --stat` 與這幾個檔 |
| TC-052 | 不做：不寫隔離；隔離規則 | 不在範圍 | 改好之後 | 看 `tests/quarantine.txt` 的差異 | 沒有變動；整個差異沒有新增任何 skip／xfail／flaky 標記 | 手動：閱卷者看差異 |
| TC-053 | 不做：不改分片與逾時；裁決 5 待裁決 3、4 | 不在範圍 | 改好之後 | 看 `tests/platform_test.sh`、`tests/platform_shard_2_test.sh`、`tests/platform_shard_3_test.sh`、`tests/platform_clock_test.sh`、`tests/run_all.sh` 的差異，並看工作區檔 `memory/scripts/abf-fast-suite.sh`、`supervise.js` | 全部沒有變動；沒有新增 `run_all` 項目；逾時與同時跑的套數（slot）沒被調 | 手動：閱卷者看 `git diff --stat` |
| TC-054 | 不做：不改程式碼 | 不在範圍 | 改好之後 | 看 `hooks/confirm_launch.sh`、`scripts/jev.sh`、`platform/abf_platform/`、`platform/abf_station/` 底下的差異 | 全部沒有變動 | 手動：閱卷者看 `git diff --stat` |
| TC-055 | 不做：前端 session 的檔與 flaky-tests 已修的七處 | 不在範圍 | 改好之後 | 看 `platform/tests/test_web_*.py` 的差異；並看 `test_r30_r36`、`scenario_life`、`test_nextflow_e2e` 的固定睡眠、TC-002、tc087／tc071、TC-059 這些位置 | `test_web_*.py` 沒有變動；上述已修的位置沒有被碰 | 手動：閱卷者看差異 |
| TC-056 | 不做：不改規格字句與閘門檔 | 不在範圍 | 改好之後 | 看 `specs/*/test-case*.md`（含 `relay-warning-hardening`）、`spec.md`、`.github/`、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`.claude-plugin/plugin.json`、`platform/pyproject.toml` 的差異；並看 `specs/flaky-three/test-case*.md` 在實作期間的差異 | 全部沒有變動（`specs/flaky-three/plan.md` 是派工前就提交的，不算） | 手動：閱卷者看 `git diff` |
| TC-057 | 裁決 4（不做工具化） | 不在範圍 | 改好之後 | 看差異與 ledger | 沒有新增 flakefinder 之類的工具或腳本；連跑都是 shell 迴圈 | 手動：閱卷者看 `git diff --stat` 與 ledger |

## 憲法與安全網

`tests/confirm_launch_test.sh` 測的是安全網裡的確認閘門（`hooks/confirm_launch.sh`）。改這支測試最怕的是：測試變鬆，閘門被改窄卻沒人發現（本專案的校準案例 1、#29）。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-058 | 安全網：確認閘門對大輸入仍要問；校準案例 1 | 功能 | base 與改好版各在閒置下跑 `confirm_launch_test.sh`；`hooks/confirm_launch.sh` 沒動 | 比對兩個版本裡 `envbig` 案例的「有標頭」「閘門 ask」兩項斷言是否都還在，並做 TC-008(c) 的假 hook | 21 個案例的 `no header`／`not ask` 判斷在改好版一條不少；換成永遠 allow 的假 hook 時全部變紅；因此閘門的覆蓋面與 base 相同 | 手動：閱卷者在兩個版本各跑一次並比對 |
| TC-059 | 安全網 #29：每個安全閘的 hook timeout ≥ 30 秒 | 功能 | 改好之後 | 跑 `bash tests/confirm_launch_test.sh`，看四行 `#29 every … entry has timeout >= 30s` | 四行都 `ok`；`BIG_CEIL_MS`（10000）確實小於這個 30 秒下限（註解所說的三分之一） | 自動：`tests/confirm_launch_test.sh` |

## 專長守則（backend）

計畫帶有「專長守則（backend）」。本任務只改測試檔，不新增網頁、API 或聊天動作，也不碰資料表。適用的兩條各對應一個 TC；動作層對等性、跨使用者讀寫、人工確認管道、錯誤訊息用詞這四條在本任務**不適用**（沒有任何動作、紀錄、寫入路徑被新增或修改），不另出題。

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-060 | 專長守則：密鑰、token、密碼不得出現在日誌或回應中 | 功能 | 改好之後 | 搜尋 ledger 與四個測試檔新增行裡有沒有 token、`Authorization` 標頭值、passphrase、金鑰內容；看 `httpx` 呼叫只多了 `timeout=` | 沒有任何密鑰出現；ledger 貼的輸出不含實際 token；`timeout=HTTP_TIMEOUT` 沒有改變任何標頭或內容 | 手動：閱卷者搜尋並讀差異 |
| TC-061 | 專長守則：資料結構變動須附 migration 或寫明不需要 | 功能 | 改好之後 | 看 `git diff --stat`，並看 ledger 或總覽 | 沒有任何資料庫結構、資料內容或 `platform/abf_platform/` 底下的檔被改；ledger 寫明「不需要 migration：只改測試檔」 | 手動：閱卷者看差異與 ledger |
