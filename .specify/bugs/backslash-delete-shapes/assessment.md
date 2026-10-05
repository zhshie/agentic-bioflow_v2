# Bug Assessment: a leading backslash hides the SN1/SN2 delete shapes from the deletion guard

- **Slug**: backslash-delete-shapes
- **Created**: 2026-10-05
- **Source**: independent acceptance of `fix/gates-audit2` (item 1)
- **Verdict**: valid
- **Severity**: high (a delete of results/ or rawdata/ passes with nothing printed)

## 給維護者

1. 在指令前面加一個反斜線（`\tar`、`\rclone`…）是 shell 裡「不要用別名」的寫法，指令照樣執行。
2. 刪除關卡對 `\rm`、`\mv` 早就認得，但這個分支新加的幾種「順便刪除」的指令（tar --remove-files、zip -m、rclone purge、ln -sfn、find -delete、rsync --delete、nextflow clean -f）前面加 `\` 就完全看不到，直接放行。
3. 修法：這些規則也接受開頭的 `\`，讀指令名稱的地方也先去掉 `\`；大輸入的預先過濾用的是同一組規則，所以一起修好。

## Reproduction (WSL, 41d8f9b, cwd a run folder)

| Command | Verdict | Without the `\` |
|---|---|---|
| `\nextflow clean -f` | pass | ask |
| `\tar --remove-files -cf a.tar results` | pass | deny |
| `\zip -m a.zip rawdata` | pass | deny |
| `\rclone purge results` | pass | deny |
| `\ln -sfn /tmp/x rawdata` | pass | deny |
| `\find /work/u/lab_runs/p -delete` | pass | deny |
| `\rsync -a --delete e/ results/` | pass | deny |

Constitution: Safety Net, "Never delete a user's source data"; "Deleting work/ requires the user's explicit confirmation".

## Root Cause (high confidence)

`hooks/confirm_cleanup.sh`:
- `RE_FIND_DEL`, `RE_RSYNC_DEL`, `RE_RSYNC_RSF`, `RE_NFCLEAN`, `RE_TAR_RM`, `RE_ZIP_MV`, `RE_RCLONE`, `RE_LN_F`, `RE_INSTALL_D` allow a directory before the name (`([^[:space:]]*/)?`) but not the backslash that `RE_DELVERB` and `RE_MV` allow (`\\?`).
- `past_word` (where the words after tar/zip/rclone/ln/install start) and the `nextflow` word search (`NFX=${NFX##*/}`) strip a directory but not a leading `\`, so even when the shape is found no target is judged.

## Proposed Remediation

- `\\?` before the name in each of those regexes, as in `RE_DELVERB`.
- `past_word` and the nextflow word search strip a leading `\`.
- The large-input filter (`RE_TRIGGER`) is built from the same variables, and the awk command word already drops the `\`, so it keeps these segments; `tests/confirm_cleanup_behind_heredoc_test.sh` reruns the new cases there.
- Tests first in the SN1/SN2 sections of `tests/confirm_cleanup_test.sh`: the seven commands above, each with the verdict of the same command without `\`.
