# 測試案例：測試用假 Slurm 指令（sbatch／squeue／sacct）與 su.py 排程器終結狀態的 SU 測試資料

<!--
Written by the verifier (CONTRACT mode, rules in the `test-cases` skill) after the plan, before any code.
本任務是 tier C、risk M 的純測試輔助任務，沒有 spec.md；依據是 `specs/slurm-shim-su/plan.md`（其「維護者原話」四條即維護者的例子）。
-->

**規格**：`specs/slurm-shim-su/plan.md`（本任務無 spec.md）　**總覽**：`test-case-overview.md`

白話說明：「假 Slurm」是三支只存在於暫存資料夾的假程式（`sbatch` 送件、`squeue` 查隊列、`sacct` 查帳），測試時放在 PATH 最前面，讓所有碰 Slurm 輸出的測試用同一組資料，從頭到尾不碰真的 Slurm。「SU」是國網的計算點數，SU 費率換算（1 SU = 1 核心小時）**仍是推論、未確認**。`su.py` 的 SU 只看 task 的 cpus、realtime（毫秒）、分區，**完全不看 task 的 status**，本任務只釘住這個現況，不改它。

類型只有三種：

- **功能**：計畫說要做到的事，正常情況下做到了。
- **例外**：出錯、缺東西、使用者做了不該做的事時，系統怎麼反應（拒絕、提示、停下）。
- **不在範圍**：計畫明講這次不做的事；確認它真的沒做。

維護者原話（計畫「維護者原話」，逐條對應）：
1.「SU 費率只放一個設定值，且未確認」→ TC-019、TC-020、TC-021
2.「跟Seqera platform一樣的模式，不要自己定義」（不新增欄位、不新增狀態，只加測試資料）→ TC-022、TC-023
3.「never a guess and never 0」（缺 cpus／realtime／係數時 SU 一律 `None` 加原因）→ TC-015、TC-017
4.「Never run: anything that reaches the site or HPC」（假指令只在暫存目錄，測試不得呼叫真的 Slurm）→ TC-001、TC-008、TC-010、TC-011

## User Story 1 — 假 Slurm 指令放上 PATH，吐出各種排程器輸出（優先度 P1）

測試檔：`platform/tests/test_fake_slurm_shim.py`，輔助模組：`platform/tests/fake_slurm.py`。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-001 | 作法 2「install」；作法 5 PATH 安全；維護者原話 4；`test_shim_is_first_on_path`、`test_tests_never_call_real_slurm` | 功能 | 測試用暫存資料夾；已呼叫 `fake_slurm.install` | 問 `shutil.which("sbatch")`、`which("squeue")`、`which("sacct")`；跑完 SU 案例後讀 `.calls()`；測試結束後看 PATH | 三支指令的位置都在暫存資料夾之下，不是系統上原有的；`.calls()` 裡只有假腳本的呼叫；測試結束後 PATH 已還原（用 monkeypatch，不是手動改環境變數） | 自動：`platform/tests/test_fake_slurm_shim.py`、`platform/tests/test_su_job_states.py` |
| TC-002 | 作法 2「假 sbatch」；`test_sbatch_prints_job_id_and_logs_call` | 功能 | 已 install，未指定工作編號 | 執行假 `sbatch` 帶任意參數 | 印出 `Submitted batch job 4242`；`.calls()` 多一行以 `sbatch ` 開頭並含所帶參數 | 自動：`platform/tests/test_fake_slurm_shim.py` |
| TC-003 | 作法 2「假 sacct」；`test_sacct_state[...]` | 功能 | 已 install；工作 4242 依序設為 COMPLETED、FAILED、TIMEOUT、OUT_OF_MEMORY、NODE_FAIL | 執行 `sacct -n -P -X -j 4242 -o State` | 每個狀態都只吐一列，內容恰為該狀態名稱 | 自動：`platform/tests/test_fake_slurm_shim.py` |
| TC-004 | 作法 2「STATES」「sacct_rows」；裁決 7（PITFALLS）、裁決 9；`test_sacct_cancelled_has_by_uid_tail` | 功能 | 已 install；呼叫 `sacct_rows` 與 `STATES` | 取 `sacct -n -P -j 4242 -o JobID,State,ExitCode,Elapsed,AllocCPUS,Partition` 的輸出；另設 CANCELLED | 每列欄位以 `|` 分隔，順序為 `JobID|State|ExitCode|Elapsed|AllocCPUS|Partition`；`STATES` 含 COMPLETED、FAILED、TIMEOUT、OUT_OF_MEMORY、NODE_FAIL、CANCELLED 且每個都有 ExitCode；OOM 為 `0:125`、TIMEOUT 為 `0:0`、FAILED 為 `1:0`；另有一個 FAILED 範例是 ExitCode `1:0` 且標明「沒有 trace」；CANCELLED 有一例輸出 `CANCELLED by 1234` | 自動：`platform/tests/test_fake_slurm_shim.py` |
| TC-005 | 作法 2「steps=True」；`test_sacct_multistep_rows` | 功能 | 已 install；工作 4242 主列 NODE_FAIL、`.batch` 為 CANCELLED | 各執行一次不帶 `-X` 與帶 `-X` 的 `sacct` | 不帶 `-X`：三列 `4242`、`4242.batch`、`4242.extern`，子步驟狀態可與主列不同；帶 `-X`：只有主列 `4242` | 自動：`platform/tests/test_fake_slurm_shim.py` |
| TC-006 | 作法 2「假 squeue」；`test_squeue_gone_job_prints_nothing` | 功能 | 已 install；一個工作設為 PENDING／RUNNING，另一個已結束 | 執行 `squeue -h -j <id> -o %T` | 還活著的工作印出其狀態；已結束的工作印空字串，且 rc=0 | 自動：`platform/tests/test_fake_slurm_shim.py` |
| TC-007 | 作法 2「空輸出」；`test_sacct_empty_output_is_rc0` | 例外 | 已 install；工作不在 accounting 裡 | 執行 `sacct -n -P -X -j 4242 -o State` | rc=0 且標準輸出是空的（不是錯誤、不是 0 列的假資料） | 自動：`platform/tests/test_fake_slurm_shim.py` |
| TC-008 | 作法 2「sacct_fail」「squeue_invalid」「sbatch_fail」；`test_sacct_fail_is_rc1`、`test_squeue_invalid_job_is_rc1` | 例外 | 已 install；分別設定 `sacct_fail`、`squeue_invalid`、`sbatch_fail` 狀態 | 分別執行 `sacct`、`squeue`、`sbatch` | 三者各自 rc=1（`squeue_invalid` 重現真 Slurm 對已結束工作回「Invalid job id」且 rc=1 的情形；`sbatch_fail` 則 `exit 1`） | 自動：`platform/tests/test_fake_slurm_shim.py` |
| TC-009 | 作法 2「ABF_FAKE_SLURM_DIR」；`test_unconfigured_shim_refuses` | 例外 | 已 install，但移除環境變數 `ABF_FAKE_SLURM_DIR` | 分別執行假 `sbatch`、`squeue`、`sacct` | 三支都 rc=99，並印出 `fake slurm: not configured`，不會被誤當成真的 Slurm | 自動：`platform/tests/test_fake_slurm_shim.py` |
| TC-010 | 作法 2「工作編號必須純數字」；`test_job_id_must_be_digits` | 例外 | 已 install | 執行 `sacct -j "1; rm -x"` | rc=2；`.calls()` 有記錄這次呼叫，但沒有執行引數裡的任何東西，暫存資料夾沒有新增檔案 | 自動：`platform/tests/test_fake_slurm_shim.py` |
| TC-011 | 作法 2「不得寫入 tmp_path 以外」；`test_shim_never_writes_outside_tmp` | 例外 | 已 install；先對暫存資料夾以外的目錄拍快照（不 import `station_harness`） | 依序呼叫三支假指令（含成功、失敗、非法編號各情形） | 呼叫前後暫存資料夾以外的快照完全相同 | 自動：`platform/tests/test_fake_slurm_shim.py` |

## User Story 2 — 排程器終結狀態下 su.py 怎麼算 SU（優先度 P1）

測試檔：`platform/tests/test_su_job_states.py`。不改 `su.py`，只用假資料釘住它現在的行為；Elapsed 轉毫秒的函式只放在測試裡。

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-012 | 作法 3「COMPLETED、FAILED」；`test_completed_and_failed_tasks_are_charged` | 功能 | task 有 cpus 與 realtime（毫秒，由 `sacct_rows` 的 Elapsed 轉來），狀態分別為 COMPLETED、FAILED（FAILED 有 trace） | 對每個 task 呼叫 `su_of_tasks` | 兩者都照常計：SU = cpus × realtime 小時 × 分區係數；FAILED 的 task 也要付費，不得因失敗而被略過 | 自動：`platform/tests/test_su_job_states.py` |
| TC-013 | 作法 3「TIMEOUT」；`test_timeout_task_is_charged_its_full_walltime` | 功能 | TIMEOUT 的 task，Elapsed `02:00:00`（= 7,200,000 毫秒） | 呼叫 `su_of_tasks` | SU = cpus × 2 × 係數（整個時限都算） | 自動：`platform/tests/test_su_job_states.py` |
| TC-014 | 作法 3「OUT_OF_MEMORY」；`test_oom_task_with_short_realtime_is_still_charged` | 功能 | OUT_OF_MEMORY 的 task，realtime 很短但有值 | 呼叫 `su_of_tasks` | SU 為正數、照 realtime 計算，不得被當成 0 或略過 | 自動：`platform/tests/test_su_job_states.py` |
| TC-015 | 作法 3「NODE_FAIL」；裁決 7（PITFALLS 約 665 行：任務啟動前失敗只有 bare exit 1）；維護者原話 3；`test_nodefail_task_without_realtime_makes_total_unknown` | 例外 | 兩種 task：NODE_FAIL（Nextflow 沒收到 trace，`realtime=None`）；FAILED 且 ExitCode `1:0` 但沒有 trace（`realtime=None`） | 對每種呼叫 `su_of_tasks` | `su` 是 `None`、`twd_nstc` 是 `None`（不是 0）；`unknown_reasons` 含「缺 realtime」；不補 0、不猜 | 自動：`platform/tests/test_su_job_states.py` |
| TC-016 | 作法 3「多列」；`test_batch_and_extern_rows_are_not_extra_tasks` | 功能 | 一個工作的 `sacct_rows(steps=True)` 輸出，含 `4242`、`4242.batch`、`4242.extern` 三列 | 用測試內的轉換函式把輸出變成 task 清單，再算 SU | 只有主列的 Elapsed 變成一個 task；`.batch`、`.extern` 列被忽略，SU 不會因子步驟而重複加總 | 自動：`platform/tests/test_su_job_states.py` |
| TC-017 | 作法 3「空輸出」；維護者原話 3；`test_empty_sacct_gives_unknown_not_zero` | 例外 | 假 `sacct` 空輸出，因此沒有任何 task（`tasks_of` 回 `None`） | 呼叫 `run_su` | 結果的原因是 `NOT_STORED`，`su` 是 `None`，不是 0 | 自動：`platform/tests/test_su_job_states.py` |
| TC-018 | 作法 3 最後一條；`test_failed_and_aborted_rows_in_task_usage_are_counted` | 功能 | 仿 `test_su_in_get_run.py::_world`／`TWO`，`task_usage` 表有狀態為 FAILED 與 ABORTED 的列（各有 cpus、realtime） | 呼叫 `run_su`（經 `run_tasks` 讀表） | `run_tasks` 讀回的每列帶著 status，且這些列都被計入 SU 總數 | 自動：`platform/tests/test_su_job_states.py` |

## User Story 3 — 費率只有一個設定值，且明說「未確認」（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-019 | 作法 4；維護者原話 1；`test_rate_comes_from_the_one_config_value` | 功能 | 把 `configs/sites/su_rates.json` 複製到暫存資料夾，把 `nstc_twd_per_su` 改成 0.5，用 `load_rates(path)` 讀 | 對同一組 task 以原費率檔與改過的費率檔各算一次 | 金額隨設定值改變（改過的結果按 0.5 算）；兩個新測試檔內沒有 `0.08` 這類費率字面值當預期值（假資料自己的 `rates()` 小表可例外，但要標註「假費率」）；沒有新增第二個費率常數 | 自動：`platform/tests/test_su_job_states.py` |
| TC-020 | 作法 4「UNCONFIRMED」；維護者原話 1；`test_unconfirmed_is_stated` | 功能 | 讀真正的 `configs/sites/su_rates.json` 與三個新檔的模組說明 | 檢查費率檔 `assumption`、`fake_slurm.py`／`test_fake_slurm_shim.py`／`test_su_job_states.py` 的模組說明，以及 `test_su_job_states.py` 以真實費率檔算出金額的案例 | `assumption` 含 `inferred`；三個檔的模組說明都含大寫 `UNCONFIRMED`；每個以真實費率檔算金額的案例，assert 訊息裡帶 `UNCONFIRMED`；沒有任何地方宣稱「1 SU = 1 核心小時」已確認 | 自動：`platform/tests/test_su_job_states.py` |
| TC-021 | 裁決 7（PITFALLS 第 42 條）、裁決 9 | 功能 | 讀 `fake_slurm.py` 與 `test_su_job_states.py` 的模組說明 | 檢查說明文字 | 明寫「欄位順序為假設，未經 nano4 實測」；明寫假指令只證明我們自己的解析、不證明真 Slurm 行為；沒有宣稱「已驗證 Slurm」；欄位名只用 `JobID,State,ExitCode,Elapsed,AllocCPUS,Partition`，沒有自創欄位 | 自動：`platform/tests/test_fake_slurm_shim.py` |

## User Story 4 — 不碰產品碼、不重複既有工作（優先度 P2）

| 編號 | 對應需求 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-022 | 計畫「不做」第 1、2、4、5、6 條；維護者原話 2；「允許的斷言」 | 不在範圍 | 任務完成後的分支，對 base（v3）比較 | 驗收者執行 `git diff --stat <base>...HEAD`，並對照被釘住的既有測試（`test_estimate_su.py`、`test_su_in_get_run.py`、`test_su_usd.py`、`test_su_packaged.py`、`test_cloud_cost.py`）的 diff | 只有 `platform/tests/fake_slurm.py`、`test_fake_slurm_shim.py`、`test_su_job_states.py` 與 `specs/slurm-shim-su/*` 有變動；`su.py`、`actions/__init__.py`、`su_rates.json`、`setup.py`、`docs/`、`station_harness.py`、`platform/abf_station/`、`.github/` 零變動；沒有新增 `configs/` 檔、migration、SU 估算器；既有被釘住的測試只增不刪不放寬；`get_run`／MCP／網頁的 SU 輸出文字沒變，`su_of_tasks` 回傳欄位與狀態沒有新增 | 手動：驗收者以 `git diff --stat` 核對（docs/ 在範圍外，不另增 `docs/TESTING.md` 步驟） |
| TC-023 | 計畫「不做」第 3、4 條；作法 1；允許的斷言最後一條 | 不在範圍 | 同上 | 驗收者搜尋三個新檔 | 沒有 import `station_harness`；沒有定義 `FAKE_TOOLS` 或 `state/sacct_<id>` 約定；沒有複製 NODE_FAIL 的 head 偵測測試（`test_head_nodefail.py`、`test_station_head_state.py` 不碰、檔名不撞）；`FakeSite` 沒被併入；`subprocess` 只用來執行假腳本，不呼叫國網／ssh | 手動：驗收者以 `git grep -n` 核對（同上） |

## 憲法與安全網

| 編號 | 憲法條目 | 類型 | 前置條件 | 步驟 | 預期結果 | 驗證方式 |
|---|---|---|---|---|---|---|
| TC-024 | 第 1 條（新檔須在首行說明為何不用既有工具：`# Nothing existing: <理由>`；`test_estimate_su.py` 第 1 行為例） | 功能 | 三個新檔 | 看各檔第一行（`head -1`） | 三個檔的第一行都是 `# Nothing existing: <理由>`，理由不是空的；且 `tests/` 下列舉 `platform/tests/*.py` 的檢查沒有因新檔而變紅 | 手動：驗收者以 `head -1` 核對（`tests/*.sh` 的檢查在 `tests/run_all.sh` 中一併跑） |
| TC-025 | 第 2 條（SU 的依據是 Nextflow 的 trace，不是排程器帳務）；作法 3 前言 | 功能 | 兩組 task，cpus、realtime、queue 完全相同，只有 status 不同（COMPLETED、FAILED、ABORTED、TIMEOUT、OUT_OF_MEMORY、NODE_FAIL 各一） | 對每組呼叫 `su_of_tasks` | 只要 cpus、realtime、queue 相同，SU 就相同，與 status 無關（釘住「su.py 不看 task status」）；`su.py` 中沒有呼叫 `sacct` | 自動：`platform/tests/test_su_job_states.py` |
