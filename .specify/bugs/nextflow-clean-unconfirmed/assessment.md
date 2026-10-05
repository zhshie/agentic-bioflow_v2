# Bug Assessment: deletes of work/ that run without the confirmation Safety Net 2 requires

- **Slug**: nextflow-clean-unconfirmed
- **Created**: 2026-10-05
- **Source**: fresh audit against constitution 2.0.0 (`C:\Users\ACER\abf_audit2\probes.txt`, `probes2.txt`); the second shape found while reproducing the first
- **Verdict**: valid
- **Severity**: medium (work/ is recreatable, but losing it costs the user -resume and a full rerun, which is why SN2 asks first)

## 給維護者

1. 安全網第 2 條：刪 work/ 或 .nextflow/cache/ 之前要使用者明確確認。`rm -rf work` 會被擋下來問，但 Nextflow 自己的清除指令 `nextflow clean -f`（以及 `-f -k last`、`-f -q`、`-f <run 名稱>`、`-but <run>`）做的是同一件事——刪掉那次 run 在 work/ 裡的任務資料夾——卻完全不出聲就放行。
2. 第二個洞：刪 work/ 的指令只要「同時」碰到另一個只需提醒的情況（目標檔名像定序檔，例如 `rm -f work/ab/cd/x.bam`；或同一行還寫了 results/ 裡的檔案），關卡就只給提醒、不再要求確認，因為提醒的判斷排在確認之前，先結束了。
3. 修法：`nextflow clean` 帶 `-f`／`-force` 而沒有 `-n`／`-dry-run` 時，跟刪 work/ 一樣要求確認；`-n` 或什麼旗標都沒有（Nextflow 自己會拒絕）時照舊不出聲。刪 work/ 的確認改排在所有提醒之前，提醒的文字併進確認訊息裡。

## Reproduction (WSL, 935328a, `probe.sh` against this worktree)

| Command | Verdict | Should be |
|---|---|---|
| `nextflow clean -f` | pass | ask |
| `nextflow clean -f -k last` / `-f -q` / `-f happy_euler` / `-f -but happy_euler` | pass | ask |
| `nextflow clean -force -before happy_euler`, `nextflow -log x clean -f`, `srun nextflow clean -f` | pass | ask |
| `rm -f <run>/work/ab/cdef/x.bam` | warn | ask |
| `rm -rf <run>/work && echo x > <run>/results/notes.txt` | warn | ask |
| `rm -rf <run>/work/*.fastq.gz` | warn | ask |
| `nextflow clean -n`, `clean -n -f`, `clean -dry-run`, `clean`, `clean -but x`, `nextflow log` | pass | pass |

## Root Cause (high confidence)

1. `hooks/confirm_cleanup.sh` knows the delete verbs (rm, find -delete, rsync --delete, git clean, ...) but has no rule for `nextflow clean`, whose `-f` deletes the task directories under work/ (and their cache entries) of the named run, or of the last run.
2. The verdicts are printed in a fixed order and the first one ends the hook: the warnings for an overwrite under rawdata/results (`HIT_OVERWRITE`) and for sequencing-file names (`HIT_SEQFILE`) come before the work/ ask (`HIT_WORK`), so either one turns a confirmation into a note the model may proceed past.

## Proposed Remediation

- A segment whose command is `nextflow` (behind any wrapper, after global options such as `-log x`) with `clean` as its subcommand, `-f`/`-force`/`--force` among its options and no `-n`/`-dry-run`/`--dry-run`, is a work/ delete: the same ask as `rm -rf work/`. Its other words are run names, not paths, and are not judged as paths.
- The work/ ask moves ahead of the two warnings; their text is appended to it, so nothing is lost.
- Tests first in `tests/confirm_cleanup_test.sh`: the shapes above, plus controls (`clean -n`, `clean -n -f`, `clean`, `clean -but x`, `nextflow run ... -profile clean`, `make clean -f Makefile`).
- Out of scope: `nextflow drop` (deletes a downloaded pipeline under ~/.nextflow/assets, not a protected folder).
