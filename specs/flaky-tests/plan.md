---
id: flaky-tests
title: 七支隨機紅或本身有誤的測試改成確定性（只收緊，不放寬、不跳過、不重試）
tier: A
kinds: backend
lane: L9-tests
base: v3
source: memory/reference/dev-architecture-review-2026-10-24.md 第 5.1 節第 1、2 項與 4(c) 的 c1
---

# flaky-tests

> 本檔由 developer-agent 助理草擬（2026-10-24）。**A 級**：讓測試變確定性只能更嚴，不能更鬆；verifier 通過＋CI 綠後由 developer-agent 自己合併。行號一律是 `origin/v3`（`73578cd`）的行號。**只改測試檔，不碰程式碼**；若發現測試隨機紅是產品本身的錯，寫進「待 developer-agent 裁決」，不在本任務修。

## 目標
把 10-24 在多套測試同時跑時隨機紅、或寫法本身就錯的 7 支測試，各自改成「同樣的條件永遠得到同樣的結果」，並且每支都留下「改前會紅、改後穩定」的證據。對使用者的意義：本機全套測試不再因為別的 session 正在跑而誤報，`ABF_SUITE_SLOTS` 可以放回 3，主導者不必再分辨「真紅還是又隨機紅」。

## 維護者原話（verifier 出題用）
取自審查報告 `memory/reference/dev-architecture-review-2026-10-24.md`（維護者 10-24 核可「現在就能做」清單）：
- 「**修 6 支隨機紅測試**：開一件 A 級任務 `flaky-tests-1`（≤6 檔）：`test_web_running.py::test_r30_r36`（`'f1'` 撞 token）、`test_station_e2e.py` tc001、`platform_clock_test.sh`、`constitution_scope_test.sh`、`test_station_static.py::tc087`、`test_scope.py::tc071`。先用 flakefinder／連跑 20 次證明會紅，修完再連跑 20 次證明不紅。」（第 5.1 節第 1 項）→ 每支一條「改前會紅」案例、一條「改後穩定」案例。
- 「**修 `hosted_deploy_test.sh` TC-059**（拿 `origin/v3` 比 diff，合併後必紅）；verifier 的 CONTRACT 規則加一句『測試不得以 base 分支當比較基準』。」（第 5.1 節第 2 項）→ TC-059 不得再出現 `origin/v3`、`git diff <分支>`。（CONTRACT 規則那半句不在本任務。）
- 「時序測試……用 flakefinder 連跑 20 次找出寬限值不夠的地方，**放寬『等待上限』而不是放寬斷言**。」（第 4(c) 的 c1）→ 可以加長等待上限；不可以改斷言的比較值、不可刪斷言。

## 範圍：檔案（只准改這些）
修改（全是測試檔）：
- `platform/tests/test_web_running.py`（**前端 session 擁有**；**developer-agent 派工前先通知前端 session**，並在派工訊息註明；只准動 `test_r30_r36_attention_card_uses_the_component` 一個函式，加一個新測試）
- `platform/tests/test_station_e2e.py`（只動 `scenario_life`，第 580–618 行）
- `platform/tests/test_nextflow_e2e.py`（只動 `platform_clock_test.sh` 所跑的那份檔裡以固定 `time.sleep` 代替事件的地方，見作法 3）
- `tests/constitution_scope_test.sh`
- `platform/tests/test_station_static.py`（只動 `test_tc087…`，第 83–87 行）
- `platform/tests/test_scope.py`（只動 `test_tc071…`，第 100–121 行；不改 `_all_platform_files` 的簽章，`test_station_static.py` 第 92 行 import 它）
- `tests/hosted_deploy_test.sh`（只動 TC-059，第 268–275 行）
新增：
- `specs/flaky-tests/ledger.md`（executor 進度帳本；每支測試的「改前紅」「改後穩定」證據貼這裡，格式見完成標準）

**不准動（硬規則）**：`platform/abf_platform/` 與 `platform/abf_station/` 底下任何檔案；`tests/platform_clock_test.sh`、`tests/platform_test.sh`、`tests/run_all.sh`（它們不是隨機紅的原因，見作法 3；run_all 的逾時上限不得調）；閘門檔（`spec.md`、`test-case*.md`、`.specify/memory/constitution.md`、`docs/ROADMAP.md`、`.github/`、`.claude-plugin/plugin.json`、`platform/pyproject.toml`）；其他任務正在動的檔案：`platform/abf_platform/{pipeline_launch,module_sources,cli,store,receiver,cloud_cost,cloud_store}.py`、`actions/*`、`platform/abf_launch/*`、`platform/abf_station/launch.py`、`handlers.py`、`hooks/*`、`skills/launch/*`、`scripts/launch_recheck.sh`、`docs/TESTING.md`、`platform/tests/test_gcb_ce.py`。

## 作法
通則：每支都是「先證明會紅（強制條件或連跑）→ 改 → 同一個強制條件下變綠＋連跑穩定」。**不得**加 skip／xfail／重試裝飾器或迴圈；斷言的比較對象不得變鬆（可以更精確、可以更多）。

### 1. `test_r30_r36`（原因：已確認，是測試寫錯）
- 原因：第 152 行 `"f1" not in pane(c.get("/?run=" + b).text, "right")` 是對**整段 HTML**做兩字元子字串比對；頁面有 `secrets.token_hex(16)` 產生的 32 位十六進位 token（`platform/abf_platform/confirm.py` 第 44、90 行，按鈕表單用），`f1` 是合法十六進位，所以每次約 11%（`1-(255/256)^31`）撞到。測試自己的第 150 行註解承認「the buttons' hex tokens can hold it」，第 150 行當時只修了一處，第 152 行漏了。
- 改法：把「右欄沒有 f1 那個 run 的任何東西」改成**精確的禁止項**，全部對 `pane(..., "right")` 的結果做：
  (a) run 名稱 `f1` 只算獨立的詞：用 `(?<![0-9A-Za-z])f1(?![0-9A-Za-z])` 做 `re.search`（32 位 token 兩側是引號，不會被當成詞；`id-f1` 這種 run id 因為前面是 `-` 仍會被抓到，這正是要禁止的）；
  (b) f1 的獨有內容都不在：`seed` 給的 run id `id-f1`（`platform/tests/test_web_board.py` 第 32 行）、失敗原因 `samplesheet is missing the reverseReads column`、`FASTQC (sample2)`、`TRIMGALORE (sample3)`（`f1()` 見 `test_web_running.py` 第 44–49 行）。
  這比原斷言**更嚴**：原本只擋兩字元（還會誤報），現在擋 5 項具體標記且不誤報。保留前半 `len(notices(...)) == 1`。
- 第 14 行 `"l1"/"u1"/"s1" not in right`：`l`、`u`、`s` 不是十六進位字元，token 裡不可能出現，**不是**隨機紅來源，不改（改了也只是範圍膨脹）。executor 在 ledger 記一句為何不改。

### 2. `test_tc001_tc003_tc004…`（`scenario_life`；原因：時間邊界太窄，確定性可推導）
- 機制：agent 被判 offline 的條件是 `現在 - last_seen_at > 3 個心跳`（`platform/abf_platform/agents.py` 第 30–32 行；`common.py` 第 138–139 行 `offline_after_seconds`；本檔 `H = 2`，第 24 行，所以上限 6 秒）。第 604 行斷言「殺掉後仍 online」，但真正的「現在」是第 602 行起一個**新子程序**（`station_harness.py` 第 416–423 行 `mcp`／`mcp_json`）啟動後才讀的牆上時鐘。從最後一次心跳算起：最多 2 秒（上次心跳到 SIGKILL）＋第 601 行睡的 3 秒＋子程序啟動時間 ≤ 6 秒，所以子程序啟動慢過約 1 秒就紅。四個場景同時各起一組平台＋agent（第 763–770 行 autouse fixture），多個套件同時跑時啟動慢到 1 秒以上很常見。第 590–596 行、第 612–613 行有同樣的結構（寬限 6 秒，啟動慢到 5 秒才紅，機率較低但同型）。
- 改法（斷言的意思不變：「斷線不等於 offline，offline 由時鐘決定」）：
  a. 睡完 `POLL + 1` 秒（第 601 行，保留，它的用途是讓平台還握著的舊 poll 結束）後，用 `plat.db_rows("SELECT last_seen_at FROM agents")`（第 610 行已在用；`station_harness.py` 第 425–433 行）讀出 `last`；
  b. 第 602 行的 `now_view` 改成 `plat.mcp_json("list_agents", ABF_PLATFORM_CLOCK_OFFSET=last + 2 - time.time())`——用平台本來就有的時鐘偏移（`status.py` 第 20–21 行、`store.py` 第 841–842 行）把「現在」釘在最後一次聯絡後 2 秒，容許子程序啟動慢 4 秒而不是 1 秒；斷言仍是 `status == "online"`；
  c. 第 603 行 `late_view` 不變（`3 * H + 5` 的偏移只會讓它更晚，不會變隨機）；
  d. 第 590–596 行與第 612–613 行同法：先讀 `last_seen_at`，偏移釘在 +2 秒；第 596–597 行對 `last_contact_at` 的上下界不變；
  e. 第 609 行重新連上的等待上限 `15` 秒改 `60` 秒（輪詢到條件成立就結束，不是固定睡；這是「放寬等待上限，不放寬斷言」）。
- 為何不改成「更大的心跳／更長的 sleep」：那樣測試變慢但邊界不變。

### 3. `tests/platform_clock_test.sh`（原因：腳本本身只轉發；隨機紅在它跑的兩份檔裡）
- 該腳本只是設 `ABF_PLATFORM_PART=clock` 後交給 `platform_test.sh`（`platform_clock_test.sh` 第 9–11 行），`platform_test.sh` 在「全部分片跑完後」依序單獨跑 `test_station_e2e.py` 與 `test_nextflow_e2e.py`（`platform_test.sh` 第 53 行 `LAST`、第 360–365 行）。所以它的隨機紅＝上面作法 2（`test_station_e2e.py` 的 `scenario_life`）加上 `test_nextflow_e2e.py` 的固定睡眠。**不改這兩個 .sh**（行為正確，改了等於動關卡）。
- `test_nextflow_e2e.py` 裡用固定 `time.sleep` 代替「等某件事發生」的地方：第 62 行（三個 run 結束後睡 1.5 秒才去問 receiver）、第 153 行（`proc.wait` 後睡 1.5 秒才讀 `final["status"] == "succeeded"`）、第 189 行（睡 1.0 秒才讀 `env.recorder.of_kind("begin")`）、第 467 行（睡 1.0 秒才回傳 log）。改法：把睡眠換成 `wait_until(<下一行要讀的那個事實>, timeout=30)`（`wait_until` 在 `e2e_harness.py` 第 179 行，檔內已在第 137、409 行使用），斷言原樣保留：
  - 第 62 行 → 等三個 run 的狀態都已是最終狀態（`_runs_via_mcp` 看 `status`）；
  - 第 153 行 → 等 `status == "succeeded"`，之後第 155–156 行原斷言不動；
  - 第 189 行 → 等 `env.recorder.of_kind("begin")` 非空，第 191 行原斷言不動；
  - 第 467 行 → executor 先讀呼叫端（第 460–468 行之後誰用這份 log）；若呼叫端只讀 log 檔、不讀 receiver 狀態，則 `proc.wait` 之後檔案已完整，睡眠可直接移除，並在 ledger 寫明理由；若呼叫端讀 receiver 狀態，同上改成等該事實。
  - 第 414 行（SIGKILL 後睡 1.0 秒再讀 history）與第 411 行（睡 1.2 秒再殺）是**刻意的時間窗**（要讓進度訊息先進來、再殺），不是等待事件，不改。第 81 行、第 246–248 行、第 435 行的容差（`+2`、`_CLOCK_SLACK_SECONDS = 3`、`<= 1`）是斷言本身，不動。
- 另有一個**不改、只量測**的疑點：`platform_test.sh` 第 335–338 行寫明 clock 這一份在 CI 上接近 `run_all.sh` 的 300 秒逾時；若逾時才是「隨機紅」的原因，修法是拆分或加速，不是調上限——見待裁決 2。executor 在 ledger 記一次 `time bash tests/platform_clock_test.sh` 的秒數。

### 4. `tests/constitution_scope_test.sh` TC-002（原因：已重現，是測試讀了兩份不同的輸入）
- 機制：外層檢查讀**工作樹**的 `CLAUDE.md`、`docs/*.md`、`hooks/*.sh`（第 61–76 行）；內層 TC-002（第 183–185 行）在 `git clone --depth 1` 出來的暫存複本裡再跑一次本腳本，但 `mkclone`（第 156–168 行）只把工作樹的 `$C`（constitution）與 `CONTEXT.md` 蓋進複本（第 165 行），其餘檔案是複本 **HEAD 已提交**的版本。所以只要工作樹有「尚未提交的文件／hook 修改」（多個 session 各在自己的工作樹改檔時很常見），外層綠、內層 `rc=1`，只有 `TC-002: unchanged, no main…` 這一行紅。已在 `73578cd` 的暫存複本上重現：提交一個把 `docs/SITE_ADAPTER.md` 的 `Constitution 2.0.0` 拿掉的 commit，再把工作樹那份還原不提交 → 外層全綠、內層 TC-002 `FAIL: rc=1`。另外第 158 行 `git clone` 的錯誤被 `>/dev/null 2>&1` 吞掉，clone 偶發失敗時只看到一行沒原因的 `scratch shallow clone`。
- 改法：
  a. `mkclone` 在 clone 之後，把外層讀過的所有檔案從工作樹蓋進複本：`docs/`、`hooks/`、`.specify/`（`$C` 已在內）、`CLAUDE.md`、`README.md`、`CONTEXT.md`（用 `cp -R`，不依賴 rsync）。蓋完之後內層與外層讀的是同一份輸入；
  b. `git clone` 的 stderr 存到 `$SCR/clone.err`，失敗時放進 `bad` 訊息；
  c. 其餘斷言（TC-002 的「fingerprint 那行是 ok」「沒有 skip 字樣」、TC-003／004／006／007／008／009）一個字都不改；
  d. 不改 `PINNED_SN_SHA256`、不改任何 `has`／`hasnt` 的檢查字串。
- 這比原本**更嚴**：內層現在檢查的就是外層檢查的東西，而且 clone 失敗會說原因。

### 5. `test_tc087`（第 83–87 行）與 6. `test_tc071`（第 100–121 行）（原因：**查不到單一確定原因**，給有界修法）
- 已知事實：兩者都用 `subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, …).stdout.split()`（`test_station_static.py` 第 85 行；`test_scope.py` 第 117 行），**不檢查回傳碼**——git 失敗時 `tracked` 變空、斷言空洞通過（這是弱點，不是隨機紅的原因）；`git ls-files` 讀的是**索引**，所以另一個程序在同一棵樹裡 `git add` 了符合 `\.(service|timer)$|(^|/)crontab$` 的檔案（`test_tc087` 第 86 行）或資料庫檔（`test_tc071` 第 118 行）就會紅，離開那個狀態就綠。另外 `test_tc071` 第 120–121 行掃描 `platform/` 底下磁碟上的 `*.sqlite*`、`-wal`、`-shm`、`-journal`（`_all_platform_files`，第 27–32 行），分片並行時若別的程序在 `platform/` 內短暫開著 SQLite 連線就會有 `-wal`／`-journal` 旁檔。**這兩種機制我沒有在 `origin/v3` 上實際重現**（沒有可跑的 Python 環境），所以 executor 的第一步是抓證據。
- 步驟：
  a. 抓：在一個暫存複本裡，開 `ABF_PLATFORM_PART=main` 的整份平台測試同時，另開一個迴圈每 0.2 秒執行 `find platform -name '*-wal' -o -name '*-shm' -o -name '*-journal' -o -name '*.sqlite*'` 並記錄時間與檔名；同時連跑這兩支測試 20 次，把每次失敗訊息貼進 ledger；
  b. 無論抓到什麼，先做這些**只收緊**的修改：`git ls-files` 的回傳碼必須是 0 且清單非空（否則斷言失敗並印 stderr）；失敗訊息改成只印違規的那幾個路徑（`test_tc087` 第 86 行目前把整份 `tracked` 清單當訊息）並附 `git status --porcelain` 的前 20 行；
  c. `test_tc071` 的磁碟旁檔掃描改成「重掃到空為止，最多 15 秒」：`deadline = time.time() + 15`，每 0.3 秒重掃，空了就過；到期仍有檔案才失敗，訊息列出檔名。這不是放寬——永久遺留的檔案 15 秒後照樣紅；短暫的 SQLite 旁檔會在連線關閉後消失；
  d. 若 a 抓到某個測試把檔案寫進 `platform/`（不是 `tmp_path`），那是另一支測試的隔離錯誤：**不在本任務改**，寫進待裁決 3；
  e. 若 a 抓到的是「別的程序把 `.service`／`.timer` `git add` 進同一棵樹」（例如 hosted-deploy 的 worktree 在改名前，見該計畫裁決四），那是**測試正確地反應了索引狀態**，不是 bug：不改行為，只做 b 的訊息改善，並在 ledger 寫明；
  f. 若 a 完全抓不到，ledger 明講「查不到原因」，保留 b、c 的修改，並在待裁決 3 說明。

### 7. `tests/hosted_deploy_test.sh` TC-059（原因：已重現，寫法本身錯）
- 機制：第 269–275 行用 `git diff origin/v3 -- docs/INSTALL.md` 取得「這個分支新增的行」當基準。分支合進 `v3` 之後 `origin/v3` 已含這些行，`add` 變空，`nadd = 0` 且找不到 `Hosting one lab`，於是 `FAIL: added 0 lines`；CI 的淺層 clone 沒有 `origin/v3`，走第 275 行的 `skip`，於是測試在 CI 是空轉、在本機是必紅。已在 `73578cd` 上重現：`TC-059 INSTALL.md pointer FAIL: added 0 lines`。
- 改法：改成檢查 **INSTALL.md 現況的穩定性質**，不用任何 git 基準（整個 TC-059 區塊不得再出現 `git`、`origin/`）：
  - 取出 `docs/INSTALL.md` 中含 `Hosting one lab` 的行（`origin/v3` 上是第 13 行與第 53 行），斷言：至少 1 行、至多 6 行（原斷言 `nadd <= 6`）；
  - 這些行本身不以 `#` 開頭（原斷言「沒有新 `##`」）；
  - 這些行裡反引號包住的詞沒有 snake_case（沿用第 272 行的樣式 `` `[^`]*` `` 與 `[a-z]+_[a-z_]+`）；
  - 第 274 行「剛好 6 個 `## ` 標題」保留（`origin/v3` 上是第 9、23、43、66、73、81 行，已涵蓋「不得新增 `##`」）；
  - 區塊不再有 `skip` 分支：沒有 `origin/v3` 時照樣檢查。
- 這比原本**更嚴**：原本在 CI 是 skip、合併後是必紅；現在每個環境都真的檢查，且對任何時間點都給同一個答案。
- **同型問題 TC-066（第 284–292 行）**：`base66=origin/v3` 與 `git diff --name-only "$base66"...HEAD` 在合併後的 `v3` 上也必紅（在 `73578cd` 上實測 `TC-066 gate files touched FAIL: platform/abf_platform/web_board.py`，那是別的 PR 的檔），CI 淺層 clone 同樣 skip。它沒有被點名，但跟 TC-059 同一個錯。本任務**不動 TC-066**，由待裁決 1 決定怎麼處理；executor 把實測結果寫進 ledger。

## 失敗先行測試
這件事的「失敗先行」不是新功能的紅燈，而是**先證明舊寫法會紅**。每支一條，寫在 ledger 並盡量留成可重跑的測試：
- `test_web_running.py` 新增 `test_r30_r36_a_hex_token_holding_f1_cannot_trip_the_marker`：把產生 token 的來源（先確認頁面上實際用的是 `confirm.py` 第 44 或 90 行的 `secrets.token_hex`）用 `monkeypatch` 固定成含 `f1` 的字串（例如 `"f1" * 16`），渲染 `?run=<l1>` 的右欄，斷言：舊式 `"f1" not in 右欄` **為假**（證明強制條件確實把 token 放進頁面），同時新的精確禁止項檢查為真。改前（用舊斷言）這個條件下必紅，改後必綠。
- `scenario_life`：在一個**不提交**的暫存副本把第 602 行前插入 `time.sleep(4)`（模擬子程序啟動慢）→ 舊寫法必紅（3＋4 > 6）；新寫法（偏移釘在 `last + 2`）仍綠。這段插入只存在於暫存副本，貼進 ledger 的是指令與結果，不進 commit。
- `test_nextflow_e2e.py`：在暫存副本把被改掉的那些 `time.sleep(n)` 改成 `time.sleep(0)`：舊寫法下測試因為事件還沒到而紅（證明睡眠是承重的競態）；新寫法（`wait_until`）下仍綠。
- `constitution_scope_test.sh`：照「作法 4」的重現步驟（提交一個拿掉字串的 commit、工作樹還原不提交）→ 舊腳本 `TC-002 … FAIL: rc=1`，新腳本全綠。這個重現步驟貼進 ledger；**不**新增進腳本（避免測試變得更長更脆）。
- `tc087`／`tc071`：在暫存複本 `git add` 一個空的 `x.service`／`x.db` → 兩支必紅且訊息只列出違規路徑；`rm` 並 `git reset` 後綠。另外在暫存副本模擬 `git` 失敗（`PATH` 裡放一個永遠 exit 1 的 `git`）→ 新寫法紅（舊寫法空洞通過）。
- `hosted_deploy_test.sh`：在 `73578cd` 上舊腳本 `TC-059 … FAIL: added 0 lines`；新腳本 `ok`；再模擬「淺層、沒有 `origin/v3`」（暫存複本 `git branch -rd origin/v3` 或 `--depth 1` clone）→ 新腳本仍 `ok`（舊腳本是 `skip`）。

## 完成標準（done when）
1. 上節每一條「改前紅」都在 `specs/flaky-tests/ledger.md` 有指令與輸出；每一條「改後綠」同樣有。
2. 便宜的測試連跑 N=20（逐次、不並行），20 次全綠，貼次數與結果：
   - `for i in $(seq 20); do (cd platform && python -m pytest -q -p no:cacheprovider tests/test_web_running.py::test_r30_r36_attention_card_uses_the_component tests/test_scope.py::test_tc071_no_submission_no_resident_loop_no_committed_database tests/test_station_static.py::test_tc087_nothing_keeps_a_process_alive_or_reopens_a_connection) || exit 1; done`
   - `for i in $(seq 20); do bash tests/hosted_deploy_test.sh | grep -E 'TC-059|TC-066' ; done`（TC-059 兩行 20 次都 `ok`）
3. 貴的測試連跑 N=5（每次約 1～2 分鐘）：`tests/constitution_scope_test.sh`（約 20 秒／次，N=5）；`test_station_e2e.py` 整檔（`side` fixture 一啟動就跑四個場景，不能只挑一個，N=5）；`test_nextflow_e2e.py` 整檔（N=3，需要 Java 與 Nextflow；沒有就在 ledger 寫明「本機沒有、交 CI」並由 CI 的 `platform_clock_test.sh` 當證據）。**另外**用「同時開 4 份」壓測一次：`for k in 1 2 3 4; do pytest tests/test_station_e2e.py -q & done; wait`，全綠。
4. `test_tc087`／`test_tc071` 的失敗訊息只列違規路徑；`git` 失敗時變紅（作法 5b 的模擬）。
5. `TC-059` 區塊不含 `git`、`origin/`、`skip`（`sed -n '/TC-059/,/TC-062/p' tests/hosted_deploy_test.sh | grep -nE 'git|origin/|skip'` 無輸出）。
6. 改動範圍證據：`git diff --stat` 只列「範圍：檔案」那些檔，貼進 ledger（依 README 通例由 verifier 自己重跑核對）；沒有任何 `skip`／`xfail`／`flaky`／retry 字樣新增（`git diff | grep -nE '^\+.*(skip|xfail|flaky|retry|rerun)'` 無輸出，英文註解裡的敘述性用法除外並在 ledger 說明）。
7. 全套測試綠（本機 `bash tests/run_all.sh`；CI 綠）。

## 環境事實
（行號為 2026-10-24 讀 `origin/v3`，`73578cd`）
- 平台測試分片並行、cwd 是 `platform/`，`LAST` 兩份（`test_station_e2e.py`、`test_nextflow_e2e.py`）在全部分片結束後單獨依序跑：`tests/platform_test.sh` 第 53、322、340–366 行。起 pytest 的包裝在第 349 行。
- `scenario_life` 在 `Side` 的 4 執行緒池裡與其他三個場景同時跑，每個場景起一個真平台程序與一個真 agent 程序：`test_station_e2e.py` 第 751–770 行。
- agent 離線判定與時鐘偏移：`agents.py` 第 30–32 行、`common.py` 第 138–139 行、`status.py` 第 20–21 行、`store.py` 第 841–842 行；既有測試已用 `ABF_PLATFORM_CLOCK_OFFSET`（例如 `test_station_e2e.py` 第 603 行、`test_mcp.py` 第 112 行）。
- `wait_until(fn, timeout=60, step=0.2, what=…)`：`platform/tests/e2e_harness.py` 第 179 行。
- 暫存複本重現用法（不要在真的 repo 動）：`git clone --no-local file://<repo> <暫存>`，再 `git fetch origin +refs/remotes/origin/v3:refs/remotes/origin/v3` 取得 `origin/v3`；本機的 `v3` 分支落後，別拿它當基準。
- 本機（Windows Git Bash）跑 `tests/hosted_deploy_test.sh` 時備份相關的 TC-034／035／036／041／042 會因環境（沒有 POSIX 權限、沒有 python3／sqlite3）紅，與本任務無關；`run_all.sh` 拒絕原生 Git Bash，正式驗證在 WSL／Linux 或 CI。
- 本草擬者沒有可跑的 Python 環境，所以作法 1、2、3、5、6 的原因是**讀碼推得**，作法 4、7 是**實際重現**；每條都在上面標明，executor 以 ledger 的重現結果為準，若重現結果與本文不符，以實測為準並回報。

## 不做
- 不加 `skip`／`xfail`／`flaky` 標記／重試迴圈；不加 `@pytest.mark.quarantine`（c2 隔離規則是另一件要維護者點頭的事）。
- 不調 `run_all.sh` 的逾時上限、不調 `ABF_SUITE_SLOTS`（修完後由 developer-agent 自己放回 3）。
- 不改任何程式碼（`platform/abf_platform/`、`platform/abf_station/`）；不改 `platform_clock_test.sh`／`platform_test.sh`。
- 不放寬任何斷言的比較值、不刪斷言、不縮小被檢查的範圍。
- 不改 `test_web_running.py` 其他函式、不改 `_all_platform_files` 的簽章。
- 不處理 TC-066（見待裁決 1）、不處理 verifier 的 CONTRACT 規則（審查報告另有項目）。
- 不改別支測試的隔離問題（若抓到，寫待裁決 3）。

## 裁決
1. A 級；專長守則用 `backend`；verifier 通過＋CI 綠後由 developer-agent 自己合併。
2. `test_web_running.py` 為前端 session 擁有：**派工前 developer-agent 先通知前端 session**，並要求 executor 只動 `test_r30_r36…` 一個函式與新增一個測試。
3. 本任務不做 flakefinder 工具化；用 shell 迴圈連跑（工具搜尋與選型在審查報告第 3 節已做）。
4. 「放寬等待上限，不放寬斷言」是唯一允許的時序修法（審查報告 4(c) c1）；用輪詢到條件成立，不用加長固定睡眠。
5. 作法 5／6 若抓不到原因，接受「查不到＋有界修法（只收緊與輪詢）」作為本任務的交付，不要求猜一個原因。

## 待 developer-agent 裁決
1. **TC-066（`hosted_deploy_test.sh` 第 284–292 行）怎麼辦？** 它用 `origin/v3` 當範圍基準，在合併後的 `v3` 上實測必紅，在 CI 淺層 clone 是 skip。沒有一個「歷史不完整也成立」的靜態性質能代替「這個 PR 沒碰程式碼」。建議：依 `memory/dev-plans/README.md` 通例，這是「只能看 diff 確認」的案例，移到 verifier 的閱卷核對（ledger 貼 `git diff --stat`），並從測試檔移除該區塊。**移除斷言屬放寬，必須你點頭**；不點頭就保持現狀（本機必紅、CI skip），本任務不動。
2. **`platform_clock_test.sh` 若是逾時紅而不是競態紅？** `platform_test.sh` 第 335–338 行承認整份平台測試曾用掉 300 秒中的 298 秒。executor 會量 `time bash tests/platform_clock_test.sh`；若超過約 200 秒，需要你決定拆分（再多一個 `run_all.sh` 項目）或加速，**不是**調高上限。
3. **作法 5／6 若抓到產品或其他測試的問題**（某測試把 SQLite 檔寫進 `platform/`、或 `git ls-files` 的索引被別的流程污染的規則該怎麼訂）：列在這裡，另開任務；本任務只交付訊息改善與輪詢修法。
4. **前端 session 的 `test_web_running.py`**：若前端 session 同時在改同一個函式，請你協調順序（本任務改動只有 `test_r30_r36…` 一處，衝突面很小）。

## 裁決二（2026-10-24 developer-agent）
1. hosted_deploy TC-066：這條是 10-24 本任務流程新寫、以 origin/v3 當基準的檢查，在 v3 上必紅、CI 又跳過，不是安全網。刪除該段，改成 README「閱卷看 diff」通例（verifier 看 ledger 的 diff 證據）；刪除理由寫進 ledger 與 PR 說明。TC-059 照計畫改寫。
2. platform_clock_test 若是 300 秒上限造成：不准調高上限，回報 BLOCKED，由 developer-agent 另開拆分任務。
3. tc087/tc071 抓到的真正原因若屬別的測試或別的 session，記進 ledger、另案。
4. 已通知前端 session：test_web_running.py 只動計畫列的那一個函式加一支新測試。

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
