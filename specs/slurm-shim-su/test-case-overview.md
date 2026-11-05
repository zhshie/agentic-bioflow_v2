# 測試案例總覽：測試用假 Slurm 指令（sbatch／squeue／sacct）與 su.py 排程器終結狀態的 SU 測試資料

狀態：合約已確認（2026-11-04，verifier）

**規格**：`specs/slurm-shim-su/plan.md`（tier C、risk M，無 spec.md）　**明細**：`test-case.md`

## 一眼看完

| User Story | 功能 | 例外 | 不在範圍 | 合計 |
|---|---|---|---|---|
| US1 — 假 Slurm 指令放上 PATH，吐出各種排程器輸出 | 6 | 5 | 0 | 11 |
| US2 — 排程器終結狀態下 su.py 怎麼算 SU | 5 | 2 | 0 | 7 |
| US3 — 費率只有一個設定值，且明說「未確認」 | 3 | 0 | 0 | 3 |
| US4 — 不碰產品碼、不重複既有工作 | 0 | 0 | 2 | 2 |
| 憲法與安全網 | 2 | 0 | 0 | 2 |
| **合計** | 16 | 7 | 2 | 25 |

自動驗證 22 條、手動驗證 3 條（TC-022、TC-023、TC-024；皆為「檔案有沒有被動到」類，由驗收者以 `git diff`／`git grep`／`head -1` 核對）。

## 請你判斷的三件事

1. **每條是不是你要的？** 有沒有哪條的「預期結果」跟你想的不一樣。
2. **有沒有漏掉的出錯情況？** 想像實驗室成員會怎麼用錯它。
3. **「不在範圍」對嗎？** 這次不做的事，有沒有其實這次就該做的。

## 覆蓋檢查

- 計畫沒有 FR 編號；以「作法 1～5」「失敗先行測試」「完成標準」「裁決 6、7、9」逐條對照：shim 檔的 12 個具名測試（`test_shim_is_first_on_path`、`test_unconfigured_shim_refuses`、`test_sbatch_prints_job_id_and_logs_call`、`test_sacct_state`、`test_sacct_cancelled_has_by_uid_tail`、`test_sacct_multistep_rows`、`test_sacct_empty_output_is_rc0`、`test_sacct_fail_is_rc1`、`test_squeue_invalid_job_is_rc1`、`test_squeue_gone_job_prints_nothing`、`test_job_id_must_be_digits`、`test_shim_never_writes_outside_tmp`）對應 TC-001～011；SU 檔的 10 個具名測試（含 `test_completed_and_failed_tasks_are_charged`、`test_timeout_task_is_charged_its_full_walltime`、`test_oom_task_with_short_realtime_is_still_charged` 三個）對應 TC-012～020 與 TC-001；全部都有測試案例：是（缺：無）
- 維護者原話 4 條：全部都有測試案例：是（1→TC-019/020/021；2→TC-022/023；3→TC-015/017；4→TC-001/008/010/011）
- 驗收情境：計畫「完成標準」6 條（失敗先行測試全綠、diff 範圍、`subprocess` 只跑假腳本、`UNCONFIRMED` 可見、ledger 記載、`run_all.sh` 全綠）。前四條對應 TC-001～025；ledger 記載與 `run_all.sh` 全綠由 gate marker 與 CI 負責，不是獨立 TC。全部都有測試案例：是
- 計畫「不做」共 7 條（不寫估算器／不改 su.py 等、不改輸出文字、不改 station_harness／不併入 FakeSite、不複製 head 偵測測試、不呼叫真 Slurm／不新增 migration／不碰 abf_station 與 .github、不確認 1 SU = 1 核心小時、後續切片三項）：全部都有「不在範圍」或對應的測試案例：是（TC-022、TC-023；不確認 1 SU = 1 核心小時由 TC-020 的「沒有宣稱已確認」守住；不呼叫真 Slurm 由 TC-001、TC-023 守住）
- 計畫「裁決 7」的 PITFALLS 三項（第 42 條不宣稱已驗證 Slurm、約 665 行 ExitCode 1:0 無 trace 範例、欄位名不自創）：是（TC-021、TC-004、TC-015）

## 我（撰寫者）不確定的地方

以下都不改變要檢查的內容：

1. TC-022、TC-023、TC-024 是手動，但計畫禁止改 `docs/`，所以 `docs/TESTING.md` 不會有對應步驟，由驗收者用 `git diff` 核對。這樣可以嗎？
2. 計畫只指定 OOM `0:125`、TIMEOUT `0:0`、FAILED `1:0` 三個 ExitCode；COMPLETED、NODE_FAIL、CANCELLED 的值計畫沒給，TC-004 只要求「有值」。這樣可以嗎？
3. `fake_slurm.set(job_id, state_or_none, source)` 的第三個參數與 `install(..., jobs=)` 的資料形狀計畫沒說明，合約只驗證可觀察行為（輸出、rc、calls.log），不驗簽名。這樣可以嗎？
4. 條數上限 25（計畫「裁決 2」）使部分列合併了同類預期（TC-008、TC-022）；實際測試仍可以參數化分別驗證。

## 核可紀錄

（無；本合約由 verifier 確認，未經維護者逐條核可。）
