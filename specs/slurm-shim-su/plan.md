---
id: slurm-shim-su
title: 測試用假 Slurm 指令（sbatch／squeue／sacct）放上 PATH，並補齊 su.py 的 NODE_FAIL／TIMEOUT／OOM 測試資料
tier: C
kinds: [hpc]
risk: M
lane: L46-slurm-shim-su
branch: test/slurm-shim-su
base: v3
source: 維護者 10-21 起的 SU 估算線（specs/estimate-su）；su.py 已上線但只有「COMPLETED 的 task」有測試資料，排程器終結的狀態沒有；SU 費率換算仍是推論（memory/reference/nchc-pricing-2026-10-21.md）
---

# slurm-shim-su

> 本檔由 developer-agent 寫、`/supervise` 複製進 worktree 的 `specs/slurm-shim-su/plan.md`。**只處理本任務**。risk M：範圍不含 `platform/abf_station/`、`.github/`，是純測試輔助＋測試，不改產品行為。

## 目標
在 `platform/tests/` 新增一組「假 Slurm」輔助：把 `sbatch`／`squeue`／`sacct` 三支假指令寫進暫存目錄、放上測試的 PATH，可吐出 COMPLETED、FAILED、TIMEOUT、OUT_OF_MEMORY、NODE_FAIL、多列（`.batch`／`.extern`）與空輸出；並用這組資料補齊 `su.py` 缺的測試（task 以 FAILED／TIMEOUT／OOM／NODE_FAIL 結束時 SU 怎麼算）。意義：日後任何碰 Slurm 輸出的測試（SU、head 偵測、取消）都用同一組資料，測試從不呼叫真的 Slurm。**不寫新的估算器。**

## 維護者原話（verifier 出題用）
本任務沒有新的維護者裁示；沿用下列既有的（逐字出處）：
1. 「SU 費率只放一個設定值，且未確認」——developer-agent 派工單（11-04）。對應 `configs/sites/su_rates.json` 的 `assumption`：「1 SU = 1 core-hour is inferred … not stated by NCHC」；`memory/reference/nchc-pricing-2026-10-21.md` 第 3 點：「『1 SU＝1 核心小時』仍是推論，需用 `wallet` 前後比對」。→ 輸出與測試都要說「未確認」，且費率只能來自該檔（不新增第二個常數）。
2. 「跟Seqera platform一樣的模式，不要自己定義」（10-23 常設）→ 不新增欄位、不新增狀態；只加測試資料。
3. specs/estimate-su/plan.md E3／E4（維護者「都照你的建議」）：「never a guess and never 0」→ 缺 cpus／realtime／係數時 SU 一律 `None` 加原因，不補 0。
4. CLAUDE.md「Never run: anything that reaches the site or HPC」→ 假指令只在暫存目錄；測試不得呼叫真的 Slurm（含 PATH 上原有的 sbatch）。

## 範圍：檔案
只准改這些（全在 `platform/tests/`，另加本計畫的 specs；**不碰 `platform/abf_station/`、`.github/`、`platform/tests/station_harness.py`**）：
- 新增 `platform/tests/fake_slurm.py`：假 Slurm 輔助模組（非測試檔，不以 `test_` 開頭）。
- 新增 `platform/tests/test_fake_slurm_shim.py`：測假指令本身。
- 新增 `platform/tests/test_su_job_states.py`：`su.py` 的排程器終結狀態測試資料。
- 不改 `platform/abf_platform/su.py`、`actions/__init__.py`、`configs/sites/su_rates.json`（若發現必須改，停下來問，見「不做」與待決）。
- 被釘住的既有測試（只准增加、不刪不放寬）見下節「允許的斷言」。

## 作法
1. **為什麼獨立模組、不改 `station_harness.py`**：`FakeSite._fakes` 已有假 sbatch／squeue／scancel，`fix/head-nodefail-detect` 分支（PR 進行中）又在同檔加了假 `sacct`（`state/sacct_<id>`、`sacct_fail`）與 `FAKE_TOOLS`。本任務不動那個檔，避免與該分支衝突，也不複製它的 NODE_FAIL 測試（`test_head_nodefail.py`、`test_station_head_state.py` 已有）。`fake_slurm.py` 是獨立、小型、不依賴 `FakeSite` 的版本，給不需要整個假站台的測試用。
2. **`fake_slurm.py` 介面**（決定，不是程式碼）：
   - `STATES`：具名資料表 `COMPLETED, FAILED, TIMEOUT, OUT_OF_MEMORY, NODE_FAIL, CANCELLED`（CANCELLED 含 `CANCELLED by 1234` 尾巴一例），每個狀態有對應 `ExitCode`（例 OOM `0:125`、TIMEOUT `0:0`、FAILED `1:0`）。
   - `sacct_rows(job_id, state, elapsed="01:00:00", ncpus=4, partition="ct56", steps=True)`：回 `sacct -n -P` 格式文字（欄位以 `|` 分隔：`JobID|State|ExitCode|Elapsed|AllocCPUS|Partition`）。`steps=True` 時多出 `<id>.batch`、`<id>.extern` 兩列（子步驟的 State 可與主列不同，例如主列 NODE_FAIL、`.batch` CANCELLED，用來證明「只取主列」）。
   - `install(tmp_path, monkeypatch, *, jobs)`：在 `tmp_path/fakeslurm-bin` 寫三支可執行 shell 腳本，`monkeypatch.setenv("PATH", bin + os.pathsep + <原 PATH 只保留 coreutils 用>)`。**PATH 前置之外，另外用 `ABF_FAKE_SLURM_DIR` 環境變數讓腳本找狀態檔**，沒有該變數時假腳本一律 `exit 99` 並印 `fake slurm: not configured`（防止被誤用成真的）。回傳物件含 `.calls()`（讀 `calls.log`，逐行 `<prog> <args>`）與 `.set(job_id, state_or_none, source)`。
   - 假 `sbatch`：印 `Submitted batch job <id>`（id 取自狀態檔，預設 4242），記錄呼叫；`sbatch_fail` 狀態檔存在則 `exit 1`。
   - 假 `squeue -h -j <id> -o %T`：該 job 仍活著（PENDING／RUNNING）才印狀態，否則印空字串、`exit 0`（真 Slurm 對已結束的 job 回「Invalid job id」且 rc=1，另設 `squeue_invalid` 狀態檔重現這一種）。
   - 假 `sacct -n -P -X -j <id> -o State` 與 `-o JobID,State,ExitCode,Elapsed,AllocCPUS,Partition`（無 `-X` 時含子步驟）：吐上面的 `sacct_rows`；**空輸出**（job 不在 accounting，rc=0 空字串）與 `sacct_fail`（rc=1）各一種。
   - 腳本只用 POSIX shell＋`cat`，不得 `eval` 輸入、不得寫入 `tmp_path` 以外。工作編號參數若不是純數字，假指令 `exit 2`（與站台驗證一致，防注入測試用）。
3. **SU 測試資料（`test_su_job_states.py`）——不改 su.py，釘住它現在的行為**：
   `su.py` 只吃 `task_usage` 的 `cpus`、`realtime`（毫秒）、`queue`，**完全不看 task 的 `status`**。所以 Slurm 終結狀態對 SU 的影響只有「該 task 有沒有 realtime」。測試以 `fake_slurm.sacct_rows(...)` 的 Elapsed 轉成毫秒餵 `su_of_tasks`（轉換函式只放在測試裡，**不是估算器**，不進 `abf_platform`）：
   - COMPLETED、FAILED：有 cpus＋realtime → 照常計（FAILED 的 task 也要付費，Slurm 照計時）。
   - TIMEOUT：realtime＝時限（例 `02:00:00`＝7,200,000 ms）→ 照常計，SU＝cpus×2×係數。
   - OUT_OF_MEMORY：realtime 很短但有值 → 照常計，不得被當 0 略過。
   - NODE_FAIL：Nextflow 沒收到 trace，`realtime=None` → 總數 `None`，原因含「缺 realtime」；不得補 0、不得猜。
   - 多列：`.batch`／`.extern` 列**不可**重複加進 task（測試用假資料證明只有主列 Elapsed 被轉成 task，子步驟列被輔助函式忽略）。
   - 空輸出：沒有任何 task → 走 `run_su` 的 `NOT_STORED` 原因，SU 為 `None`，不是 0。
   - 對每個狀態再用一次 `run_su` 走 `task_usage` 表（仿 `test_su_in_get_run.py::_world`／`TWO`）確認 `FAILED`／`ABORTED` 的 task 列同樣被計入。
4. **費率只有一個設定值，且說「未確認」**：
   - 測試一律從 `su.load_rates()`（即 `configs/sites/su_rates.json`）取 `nstc_twd_per_su`，**測試檔內不得再寫 `0.08` 之類的費率字面值當預期值**（假資料自己的 `rates()` 小表例外，沿用 `test_estimate_su.py` 的寫法，但要標註為「假費率」）。
   - 加一條測試：`su_rates.json` 的 `assumption` 含 `inferred`，且 `fake_slurm.py` 與兩個新測試檔的模組說明都含 `UNCONFIRMED`（大寫）；`test_su_job_states.py` 每個以真實費率檔算出金額的案例，在 assert 訊息裡帶 `UNCONFIRMED`，讓失敗輸出也看得到。
   - 若維護者要求「`get_run`／MCP 的實際輸出」也帶未確認字樣，那要改 `actions/__init__.py`／`su.py`，**超出本片**，見待決 1。
5. **PATH 安全**：`install` 之後測試要斷言 `shutil.which("sbatch")` 位於 `tmp_path` 之下；所有案例在 `finally`／fixture 結束時還原 PATH（用 `monkeypatch`，不手動改 `os.environ`）。

## 失敗先行測試
先寫、現在會紅（模組與資料都還不存在）。
**`test_fake_slurm_shim.py`**
- `test_shim_is_first_on_path`：`install` 後 `which sbatch/squeue/sacct` 都在 `tmp_path` 下，不是系統的。
- `test_unconfigured_shim_refuses`：沒有 `ABF_FAKE_SLURM_DIR` → 三支都 rc=99、訊息 `fake slurm: not configured`。
- `test_sbatch_prints_job_id_and_logs_call`：輸出 `Submitted batch job 4242`，`.calls()` 有一行 `sbatch ...`。
- 參數化 `test_sacct_state[COMPLETED|FAILED|TIMEOUT|OUT_OF_MEMORY|NODE_FAIL]`：`sacct -n -P -X -j 4242 -o State` 只吐一列、State 正確。
- `test_sacct_cancelled_has_by_uid_tail`：輸出 `CANCELLED by 1234`。
- `test_sacct_multistep_rows`：不帶 `-X` 時有 `4242`、`4242.batch`、`4242.extern` 三列；帶 `-X` 時只有主列。
- `test_sacct_empty_output_is_rc0`：job 不在 accounting → rc=0、stdout 空。
- `test_sacct_fail_is_rc1`、`test_squeue_invalid_job_is_rc1`、`test_squeue_gone_job_prints_nothing`。
- `test_job_id_must_be_digits`：`sacct -j "1; rm -x"` → rc=2，`.calls()` 記錄但未執行任何東西，`tmp_path` 無新檔。
- `test_shim_never_writes_outside_tmp`：呼叫前後，`tmp_path` 以外的 `snapshot` 不變（可用 `station_harness.snapshot` 的做法，但**不 import** station_harness 以免耦合）。
**`test_su_job_states.py`**
- `test_completed_and_failed_tasks_are_charged`、`test_timeout_task_is_charged_its_full_walltime`、`test_oom_task_with_short_realtime_is_still_charged`。
- `test_nodefail_task_without_realtime_makes_total_unknown`：`su is None`，原因含 `realtime`，且 `twd_nstc is None`（不是 0）。
- `test_batch_and_extern_rows_are_not_extra_tasks`。
- `test_empty_sacct_gives_unknown_not_zero`：走 `run_su` → `NOT_STORED`。
- `test_failed_and_aborted_rows_in_task_usage_are_counted`：`run_tasks` 讀回 status 並計入。
- `test_rate_comes_from_the_one_config_value`：把 `nstc_twd_per_su` 改成 0.5（複製檔到 tmp、`load_rates(path)`）→ 金額跟著變，證明測試沒寫死費率。
- `test_unconfirmed_is_stated`：同作法 4。
- `test_tests_never_call_real_slurm`：`shutil.which("sbatch")` 在 tmp 下；`.calls()` 只含假腳本。

## 允許的斷言（既有測試）
以下釘住 `su.py`、費率檔與 SU 輸出的常數或句子；**只准新增、不刪不放寬**。開工前用 `git -C <repo> grep -n "<字串>" origin/v3 -- platform/tests tests` 逐條重核行號：
- `platform/tests/test_estimate_su.py`：TC-001～TC-013（公式、毫秒單位、unknown 原因字串「費率檔」「缺 cpus」「缺 realtime」）；253 行 `not_used` 與 `assumption` 含 `1 SU = 1 core-hour`（費率檔 `assumption` 句子**不可改**）；`RATES_FILE`、`LEDGER` 路徑。
- `platform/tests/test_su_in_get_run.py`：`_world`／`TWO` 與 `_LEAKS` 正則（回應不得含 sqlite、task_usage、traceback）；222～231 行（沒有 `task_usage` 表時不建表、唯讀）。
- `platform/tests/test_su_usd.py`、`test_su_packaged.py`（費率檔被複製進 wheel、`setup.py` 第 36～41 行）：本任務不新增 `configs/` 檔，也不改 `setup.py`。
- `platform/tests/test_cloud_cost.py`：214、314～322、676～703（`task_usage` 欄位與唯讀）——只讀，不改。
- `platform/tests/test_web_parity.py`、`test_owner_guard.py`、`tests/platform_direction_docs_test.sh`（含 `estimate_su`／`su_rates` 字樣）：本任務不新增動作、不改文件。
- 檢查：新增的兩個測試檔與 `fake_slurm.py` 不能被 `tests/` 底下「列舉所有 `platform/tests/*.py`」的檢查誤判（例如要求每個檔都有 `# Nothing existing:` 首行的檢查——grep `Nothing existing` 於 `tests/*.sh` 確認；新檔照此格式寫第一行）。
- `fix/head-nodefail-detect` 分支新增的 `FAKE_TOOLS`／`state/sacct_<id>` 約定：不重用、不改名，也不與其檔名撞（`test_head_nodefail.py`、`test_station_head_state.py` 不碰）。

## 完成標準（done when）
- 上面每條失敗先行測試綠；`tests/run_all.sh` 全綠（環境紅依 README 通例）。
- `git diff --stat` 只含 `platform/tests/fake_slurm.py`、`test_fake_slurm_shim.py`、`test_su_job_states.py`（加 `specs/slurm-shim-su/*`）；`su.py`、`su_rates.json`、`station_harness.py`、`platform/abf_station/`、`.github/` 零變動（貼進 ledger）。
- `git grep -n "subprocess" platform/tests/fake_slurm.py` 的唯一用途是執行**假腳本**；`shutil.which` 證明沒有碰真的 Slurm。
- 輸出（pytest 失敗訊息／模組說明）看得到 `UNCONFIRMED`；費率值只出現在 `su_rates.json`。
- ledger 記：新增的狀態表與「su.py 不看 task status」這個既有行為（已被測試釘住）。

## 環境事實
- `su.py`（`platform/abf_platform/su.py`）：`su_of_tasks(tasks, site, rates)`＝Σ cpus × realtime(ms)/3,600,000 × 分區係數；缺任一項整體 `None`＋原因；`run_tasks` 從 `task_usage`（`name,status,cpus,realtime_ms,queue`）讀；`run_su`、`month_total` 已有。**沒有任何地方呼叫 sacct**——SU 來自 Nextflow trace，不是 Slurm accounting。
- 費率檔 `configs/sites/su_rates.json`：`taiwania3` 各分區係數 1；`nchc` 的 ngs 分區 `null`；`nano4` 有 `twd_per_su`＋`ngs*` 係數；`nstc_twd_per_su` 0.08、`su_plan_type: nstc`。`assumption` 明寫「1 SU = 1 core-hour is inferred」。
- 國網價格背景：`memory/reference/nchc-pricing-2026-10-21.md`（SU 定義官方未寫；需用 `wallet` 前後比對；GP1 兩頁價差未解釋）。executor 不必讀它，也不碰國網。
- 既有假 Slurm：`platform/tests/station_harness.py::FakeSite._fakes`（假 sbatch／squeue／sinfo／scancel，狀態檔驅動，`FAKE_TOOLS` 列表）；v3 上**沒有**假 sacct，`fix/head-nodefail-detect` 分支才加。
- 測試輔助慣例：`platform/tests/helpers.py`（`PLATFORM_DIR`、`REPO_ROOT`、`own_runs`）、`test_su_in_get_run.py::_world` 造 index＋platform.db。
- 測試專案首行要寫 `# Nothing existing: <理由>`（見 test_estimate_su.py 第 1 行）。
- 工具：Git Bash 下 POSIX 腳本可跑；完整套件要在 WSL（CLAUDE.md「For the executor and verifier」）；repo 必須在本機磁碟。

## 不做
- 不寫新的 SU 估算器；不改 `su.py`、`actions`、`su_rates.json`、`setup.py`、`docs/`。
- 不改 `get_run`／MCP／網頁的 SU 輸出文字（「輸出也要說未確認」若要落到產品輸出，是後續切片，需維護者同意；見待決 1）。
- 不改 `station_harness.py`、不並入 `FakeSite`（等 head-nodefail-detect 合併後，另案把 `fake_slurm.py` 與 `FakeSite` 的 sacct 合一）。
- 不複製 NODE_FAIL 的 head 偵測測試（已在 head-nodefail-detect）。
- 不呼叫真的 Slurm／國網／ssh；不新增 migration；不碰 `platform/abf_station/`、`.github/`。
- 不確認「1 SU = 1 核心小時」：這要帳號持有者用 `wallet` 前後比對，維護者／操作員事。
- 後續切片：①產品輸出加「未確認」標記（`su.py` 回傳加 `rate_confirmed: false` 或說明字串）；②`FakeSite` 與 `fake_slurm.py` 合併；③以 sacct 的 `Elapsed`／`AllocCPUS` 對 trace 的 `realtime` 做交叉檢查（會是新功能）。

## 裁決
1. 整套測試一律 `run_in_background`＋等待迴圈跑 `tests/run_all.sh --timeout 900`。
2. 合約規則：計畫未明寫的細節由 verifier 依專長守則與既有慣例自訂預期值，不以「計畫未寫」退回；test-case.md 全文放進回傳值，條數 ≤ 25。
3. 本任務不碰 `platform/abf_station/`，risk M；請把 `risk: M` 抄進佇列任務物件。
4. 與其他車道：`fix/head-nodefail-detect`（改 `station_harness.py`、`fetch.py`、`test_head_nodefail.py`）——本任務與它檔案不相交；落地前 `git merge origin/v3`。
5. worktree 用 Windows git 建，WSL 裡 `constitution_scope_test.sh` 紅＝環境問題，以 CI 為準，ledger 註明。
6. 費率：只信 `su_rates.json`；PR 與 ledger 一律稱「SU 費率未確認（UNCONFIRMED，1 SU = 1 core-hour 為推論）」。
7. PITFALLS 已查：`docs/PITFALLS.md` 第 42 條（Slurm 以 submitter umask 開輸出檔；「離線測試用假 sbatch，真 Slurm 是否相同未證實」）→ 假指令只證明我們的解析，不證明真 Slurm 行為，ledger 與模組說明要寫這句，不可宣稱「已驗證 Slurm」；約 665 行（`sacct` 對任務啟動前失敗只給 bare exit 1，無 `.command.log`／`.exitcode`）→ `sacct_rows` 需含「ExitCode 1:0 但沒有 trace」的 FAILED 範例（即 NODE_FAIL／FAILED 且 `realtime=None`）；約 439～451、553～582 行（`sacctmgr`／`sacct --format=...ReqMem` 類）→ 欄位名以這些條目已出現的 `JobID,State,ExitCode,AllocCPUS,Partition` 為準，不自創欄位。`docs/solutions/` 不存在。

8. 待決 1 裁決（11-04）：同意。本任務只做測試與輔助模組的 UNCONFIRMED 標記；get_run／MCP／網頁的 SU 標記另開後續切片，不在本任務。
9. 待決 2 裁決（11-04）：不先等真 sacct 輸出。照現有欄位擬，fixture 與模組說明明寫「欄位順序為假設，未經 nano4 實測」；真實格式列入 nano4 驗收待辦（需 2FA）。

## 待決（已全數裁決，見上 8、9）
1. 「輸出必須說未確認」：本計畫只做到測試與輔助模組輸出（`UNCONFIRMED`）及釘住費率檔的 `assumption`。若要 `get_run`／MCP／網頁的 SU 也帶標記，需改產品碼，另開切片——是否同意？
2. `fake_slurm.py` 的欄位順序（`JobID|State|ExitCode|Elapsed|AllocCPUS|Partition`）是我依 PITFALLS 已出現的欄位名擬的，非從 nano4 實測；是否需要先請操作員貼一份真 `sacct -P` 輸出當參考（目前不要求）？

## 專長守則（[hpc]）

（工作區沒有 `.claude/dev-profiles/[hpc].md`；本任務無專長守則。）
