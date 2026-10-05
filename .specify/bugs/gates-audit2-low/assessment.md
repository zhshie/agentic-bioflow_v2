# Bug Assessment: low items from the acceptance of `fix/gates-audit2`

- **Slug**: gates-audit2-low
- **Created**: 2026-10-05
- **Source**: independent acceptance of `fix/gates-audit2` (item 5)
- **Verdict**: valid
- **Severity**: low (a missing test and a stale comment; no wrong verdict today)

## 給維護者

1. `srun tar --remove-files … results` 接在一大段 here-doc 後面時，判斷只靠大輸入的預先過濾規則（RE_TRIGGER）保住：`srun` 不在指令名稱清單裡。現在結果正確，但沒有測試，改壞了不會有人知道。補一個測試。
2. `tests/gate_output_failclosed_test.sh` 開頭的註解指向一個不存在的檔案 `gate_jq_failing_test.sh`，改成真正的位置。
3. 選做：`tw l\aunch`、`s\batch` 這種把反斜線塞在字中間的寫法（shell 照樣執行）。見 fix.md 的結論。

## Reproduction (WSL, 41d8f9b)

- `srun tar --remove-files -cf /tmp/r.tar <run>/results` after a 40 KB here-doc: deny (correct). With `($RE_TAR_RM)` removed from `RE_TRIGGER`: pass, and no test fails.
- `tests/gate_output_failclosed_test.sh:14`: "covered by tests/gate_jq_failing_test.sh" - no such file.
- `tw l\aunch nf-core/rnaseq`, `s\batch job.sh`: pass through confirm_launch and confirm_walkthrough (`\sbatch`, `\tw launch` already ask). The shell drops the backslash and runs the launcher.

## Proposed Remediation

- A case in `tests/confirm_cleanup_behind_heredoc_test.sh` with `srun` before the tar, checked to fail with the trigger removed.
- The comment names the "no jq" sections of the gate tests and this file's jq-broken-gates section.
- `hooks/launch_trigger.sh`: a segment holding a backslash is judged a second time with its backslashes dropped (an added copy, so a Windows path is still judged as written). Tests in the launch-shapes section of `tests/confirm_launch_test.sh`, which its #62 section reruns behind a big here-doc.
