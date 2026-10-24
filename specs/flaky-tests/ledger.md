# 修掉會隨機失敗的測試（不放寬斷言） progress ledger

環境：WSL Ubuntu，venv `~/.cache/abf-platform-venv`，實驗在 ext4 暫存複本 `~/ev`（`git clone --no-local` 本 worktree，不動真的 repo）。基準 = `a7ea26e`（本分支第一個實作前的 commit，內容等同計畫所說的 origin/v3 `73578cd` 加計畫與測試案例）。

- [x] 1. test_r30_r36
- [x] 2. scenario_life（platform_clock_test.sh 的一半）
- [x] 3. test_nextflow_e2e 固定睡眠（platform_clock_test.sh 的另一半）
- [x] 4. constitution_scope_test.sh
- [x] 5/6. tc087／tc071
- [x] 7. hosted_deploy TC-059（與刪除 TC-066）

## 與計畫不符的實測事實（以實測為準）

1. **按鈕 token 不是 `secrets.token_hex`。** `?run=` 頁面按鈕表單的 `csrf` 值來自 `platform/abf_platform/web.py` 第 181–182、116–117 行 `_mac(key, "csrf", sid, rid)`，是 HMAC-SHA256 的 `hexdigest()`（64 個十六進位字元，不是 32）。`confirm.py` 第 44、90 行的 `token_hex` 不在這個頁面。所以強制條件用 `monkeypatch` 把 `web._mac` 在 `parts[0] == "csrf"` 時回傳 `"f1" * 32`。隨機機率更高：1-(255/256)^63 約 22%（不是 11%）。結論不變（測試寫錯）。
2. **`scenario_life` 的釘點用「最後一次聯絡」（+0 秒），不是 +2 秒。** 照計畫 +2 秒、模擬子程序晚 4 秒起動時仍紅（`now_view` 變 offline）：2+4 加上真實啟動時間超過 6 秒上限。+0 秒時容許晚起動 6 秒（`3 * H`）。斷言本身（`status == "online"`、`offline` 的 `3 * H + 5`、`last_contact_at` 上下界）沒動，所以沒有放寬。
3. **`test_nextflow_e2e.py` 的 `time.sleep(0)` 沒能讓舊寫法變紅**（見第 3 節）：睡眠在這台機器上不是承重的；改成輪詢仍有效（只可能更穩），但「改前紅」這一條沒有重現，照實寫。
4. 右欄只顯示第一個失敗步驟（`FASTQC (sample2)`），`TRIMGALORE (sample3)` 不在 f1 自己的右欄；新測試對「別的 run」禁止四項全部，對 f1 自己的頁面只要求其中三項（run id、失敗原因、FASTQC）出現，證明偵測器抓得到真洩漏。

## 1. test_r30_r36（TC-001..010）

改前紅（TC-009）：強制 csrf token 含 f1，舊斷言 `"f1" not in pane(..., "right")`：

```
E       assert (1 == 1 and 'f1' not in '><p class="...body></html>'
E         'f1' is contained here:
E           f1f1f1f1f1f1"><button type="submit">重跑</button></form></div></article></div>...
```

RED commit `37fab89`（新測試 `test_r30_r36_a_hex_token_holding_f1_cannot_trip_the_marker` 與 `_f1_in` helper，在此條件下 `"f1" in right` 為真、精確標記為空），GREEN commit `5444a1a`（`test_r30_r36_attention_card_uses_the_component` 第 152 行換成 `_f1_in`：詞界正規式 `(?<![0-9A-Za-z])f1(?![0-9A-Za-z])` 加 `id-f1`、`samplesheet is missing the reverseReads column`、`FASTQC (sample2)`、`TRIMGALORE (sample3)`）。前半 `len(notices(...)) == 1` 原樣保留。
真洩漏仍抓得到（TC-006）：新測試最後對 `?run=id-f1`（f1 自己的頁面）的右欄跑 `_f1_in`，斷言 `id-f1`、失敗原因、`FASTQC (sample2)` 都被找到。
不改第 149 行 `"l1"/"u1"/"s1" not in right`（TC-007）：`l`、`u`、`s` 不是十六進位字元，不可能出現在 hex digest 裡，不是隨機紅來源。
`test_web_running.py` 只動 `test_r30_r36_attention_card_uses_the_component` 並新增一個測試與兩個模組層 helper（`_F1_MARKERS`、`_f1_in`，緊接在它後面；計畫「一個新測試」之外多這兩個 helper，供兩個測試共用）。

改後穩定（TC-010）：連跑 20 次（逐次、不並行），每次含本測試、新測試、tc071、tc087：20 次全是 `4 passed`（1.47–2.43 秒）。

## 2. scenario_life（TC-011..019）

改法見上「不符」第 2 點。`test_station_e2e.py` 只動 `scenario_life`：新增區域函式 `at_last_contact()`（讀 `last_seen_at`，回傳 `last - time.time()`），第一次檢視、`now_view`、重新連上後的檢視都改用 `ABF_PLATFORM_CLOCK_OFFSET=at_last_contact()`；重新連上的等待上限 15 改 60 秒（仍是輪詢）。`late_view`（`3 * H + 5`）、`POLL + 1` 的睡眠、所有斷言都沒改。

改前紅（TC-017）：基準 `a7ea26e` 的檔案，在 `now_view =` 前插入 `time.sleep(4)`（只在暫存副本）：

```
E           AssertionError: offline is decided by the clock, not by a broken connection
E           assert 'offline' == 'online'
1 failed, 84 passed in 70.91s
```

改後（同一個模擬：在 `at_last_contact()` 算完偏移後睡 4 秒，所有用到的地方都晚 4 秒）：`85 passed in 69.80s`。原樣：`85 passed in 83.08s`。
連跑整檔 5 次（TC-018）：`85 passed` x5（67.6–68.4 秒）。同時開 4 份（TC-019）：4 份都是 `85 passed`（79.5–80.3 秒）。

## 3. test_nextflow_e2e 固定睡眠（TC-020..029）

改動（皆只動睡眠，後面的斷言原樣）：
- 第 62 行（fixture）改為 `wait_until(三個 run 都在、狀態都是 succeeded 或 failed, timeout=30)`；
- 第 153 行改為 `wait_until(有 status == "succeeded" 的 run, timeout=30)`；
- 第 189 行改為 `wait_until(env.recorder.of_kind("begin"), timeout=30)`；
- 第 467 行（`_aborted_log`）直接移除。理由（TC-023）：唯一呼叫端是 `test_abort_tc010`／`tc011`，只讀 `launch/.nextflow.log` 這個檔，不讀 receiver 狀態；`proc.wait()` 回來時 Nextflow 已結束（`nextflow` 啟動器直接 exec JVM），log 檔已完整。
- 第 411、414 行（刻意的時間窗）、第 81、246–248、435 行（容差）沒動（TC-024）。`platform_clock_test.sh`、`platform_test.sh`、`run_all.sh` 沒動（TC-025）。

改前紅（TC-026）：**沒有重現。** 基準檔把 62、153、189、467 行的睡眠改成 `time.sleep(0)`，用 `ABF_PYTEST_TARGETS=tests/test_nextflow_e2e.py bash tests/platform_test.sh`（本機有 Java 與已快取的 Nextflow）：
- 一般負載：`23 passed in 114.19s`；
- 16 顆 CPU 全部被空迴圈佔滿：`23 passed in 224.18s`。
所以在本機這兩次，睡眠不是承重的。改成輪詢是計畫指定的做法（只會更穩、不會更鬆），但「睡眠是承重競態」這個說法沒有被證明；請閱卷者與 CI 的紀錄一起看。

改後（TC-027）：整檔連跑 3 次：`23 passed in 125.81s`、`23 passed in 205.08s`（當時機器上別的 session 在跑）、`23 passed in 142.61s`。

`time bash tests/platform_clock_test.sh`（TC-028）：**186.06 秒**，exit 0（兩份檔都跑，`pytest exit 0, 0 skipped`）。低於計畫的 200 秒門檻，TC-029 不觸發（但離門檻只剩 14 秒，且那次機器有別的負載；`run_all.sh` 的逾時沒動）。

## 4. constitution_scope_test.sh（TC-030..038）

改法：`mkclone` 在 clone 後把 `CLAUDE.md`、`README.md` 與 `docs/`、`hooks/`、`.specify/`（先刪複本的、再 `cp -R` 工作樹的）蓋進複本（`$C`、`CONTEXT.md` 本來就蓋）；`git clone` 的 stderr 存 `$SCR/clone.err`，三個 `mkclone` 呼叫端失敗時把前 400 字放進 `bad` 訊息。TC-002 的斷言、`PINNED_SN_SHA256`、所有 `has`／`hasnt` 字串、TC-003/004/006/007/008/009 一個字沒動。重現步驟只貼在這裡，沒有進腳本。

重現（TC-034）：暫存複本，提交一個把 `docs/SITE_ADAPTER.md` 的 `Constitution 2.0.0` 改掉的 commit，再把工作樹那份還原不提交（`git status`：` M docs/SITE_ADAPTER.md`）：

```
--- OLD (a7ea26e 的腳本)
TC-002: unchanged, no main: the fingerprint line runs and is ok     FAIL: rc=1
old exit=1
--- NEW
new exit=0   (沒有任何 FAIL)
```

改後穩定（TC-036）：連跑 5 次：5 次 exit 0、FAIL 行數 0。

## 5/6. tc087／tc071（TC-040..056）

改法：
- 兩支都檢查 `git ls-files` 回傳碼為 0 且清單非空，否則失敗並印 stderr；
- 失敗訊息只列違規路徑，附 `git status --porcelain` 前 20 行；
- tc071 的磁碟旁檔掃描改為「重掃到空為止，最多 15 秒（每 0.3 秒）」，到期仍有檔案才失敗並列檔名。
- tc071 前半的禁止樣式清單與原始碼掃描、tc087 最後一行 `hits(...)` 沒動；`_all_platform_files` 簽章沒動。

實測（暫存複本）：

```
== NEW, git 永遠 exit 1:        2 failed  "git ls-files gave nothing (rc=1): "
== OLD, git 永遠 exit 1:        2 passed  （空洞通過，TC-042/043 的改前）
== OLD, git add x.service x.db: 訊息是整份 tracked 清單 ['.claude-plugin/marketplace.json', ...
== NEW, git add x.service x.db: tracked files that keep a process alive: ['x.service']
                                 git status --porcelain (first 20 lines): A  x.db / A  x.service
                                 database files are committed: ['x.db']  (同樣附 status)
== NEW, rm + git reset:         2 passed
== NEW, platform/x.sqlite-wal 永久存在: 紅，15.47 秒後，訊息 database files on disk in platform/: ['x.sqlite-wal']
== NEW, 旁檔 4 秒後被刪:        2 passed in 4.04s
```

改後穩定（TC-055/056）：與第 1 節同一個 20 次迴圈，tc087、tc071 各 20/20 綠。

抓原因（TC-051）：見檔尾「tc087／tc071 觀察」。

## 7. hosted_deploy TC-059（TC-060..071）

改法：TC-059 改成讀 `docs/INSTALL.md` 現況：含 `Hosting one lab` 的行至少 1、至多 6 行、不以 `#` 開頭、反引號內沒有 snake_case；「剛好 6 個 `## `」保留；沒有 `skip` 分支。TC-066 整段（含 skip 分支）依裁決二 1 刪除。

刪除理由與實測（TC-069）：TC-066 用 `origin/v3` 當範圍基準，合併後必紅、CI 淺層 clone 是 skip，不是安全網。實測（暫存複本，`origin/v3` = HEAD 模擬合併後）：`TC-066 gate files touched  FAIL: platform/abf_platform/web_board.py`。範圍證據改由本檔下面的 `git diff --stat` 供閱卷核對。

```
--- OLD, origin/v3 = HEAD（合併後）
TC-059 INSTALL.md pointer   FAIL: added 0 lines
TC-066 gate files touched   FAIL: platform/abf_platform/web_board.py
--- NEW, 同上
TC-059 INSTALL.md: a short pointer, no new ##, no snake_case terms   ok
TC-059 INSTALL.md still has six ## headings                           ok
--- OLD, 沒有 origin/v3（CI 淺層）: 兩個都是 skip
--- NEW, 沒有 origin/v3:             兩行都是 ok
```

`sed -n '/TC-059/,/TC-062/p' tests/hosted_deploy_test.sh | grep -nE 'git|origin/|skip'` 無輸出（TC-060）。
連跑 20 次：TC-059 兩行 20/20 `ok`（TC-068）。
本機 Git Bash 上 TC-034／035／036／041／042／085 的 FAIL 是環境（`rc=49`：沒有 python3），與本任務無關，WSL 上不出現。

## 範圍與禁止項（TC-080..094）

`git diff --stat a7ea26e HEAD`（不含本檔）：

```
 platform/tests/test_nextflow_e2e.py   | 13 ++++++++-----
 platform/tests/test_scope.py          | 20 +++++++++++++++-----
 platform/tests/test_station_e2e.py    | 14 ++++++++++----
 platform/tests/test_station_static.py |  7 +++++--
 platform/tests/test_web_running.py    | 32 +++++++++++++++++++++++++++++++-
 tests/constitution_scope_test.sh      | 11 +++++++----
 tests/hosted_deploy_test.sh           | 23 ++++++-----------------
 7 files changed, 82 insertions(+), 38 deletions(-)
```

`platform/abf_platform/`、`platform/abf_station/`、`platform_clock_test.sh`、`platform_test.sh`、`run_all.sh`、閘門檔都沒動。
`git diff a7ea26e HEAD | grep -nE '^\+.*(skip|xfail|flaky|retry|rerun)'` 無輸出。

## tc087／tc071 觀察（TC-051，作法 5a）

在暫存複本 `~/ev` 開 `ABF_PLATFORM_PART=main bash tests/platform_test.sh`（12 個分片並行），同時：
- 每 0.2 秒執行 `find platform -name '*-wal' -o -name '*-shm' -o -name '*-journal' -o -name '*.sqlite*'`；
- 連續重複跑 tc071 與 tc087（逐次）直到那份平台測試結束。

結果：`main part exit=0`；tc071＋tc087 共跑 857 次，**0 次失敗**；0.2 秒觀察迴圈 **0 筆**旁檔紀錄（`platform/` 底下從未出現 `-wal`／`-shm`／`-journal`／`*.sqlite*`）。

結論：**查不到原因**（待裁決 3）：沒有抓到任何隨機紅，也沒有抓到把檔案寫進 `platform/` 的測試（TC-052 不適用）、沒有抓到別的程序 `git add` 進同一棵樹（TC-053 不適用）。交付的是計畫的有界修法（git 回傳碼與非空檢查、只列違規路徑、旁檔重掃最多 15 秒）。要找真正原因需要在 10-24 那種多 session 同時跑的環境重現；建議留意下次它紅時的訊息（現在會列出違規路徑與 `git status`）。
