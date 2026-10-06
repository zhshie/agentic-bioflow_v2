# Bug Assessment: `nextflow clean -f` through a variable passes the deletion guard

- **Slug**: variable-nextflow-clean
- **Created**: 2026-10-05
- **Source**: independent acceptance of `fix/gates-audit2` (item 2)
- **Verdict**: valid
- **Severity**: medium (a work/ delete without the confirmation the Safety Net requires; work/ is scratch, not source data)

## 給維護者

1. `N=nextflow; $N clean -f` 會刪掉一個 run 在 work/ 底下的暫存資料夾，跟直接打 `nextflow clean -f` 一樣，照規定要先問使用者。
2. 指令名稱放在變數裡時，關卡只在「後面的目標是受保護的資料夾」時才停下來問；`clean -f` 後面沒有路徑，所以直接放行。
3. 修法：指令名稱是變數、後面接 `clean` 加 `-f`（不是試跑）時，當成可能是 nextflow clean -f，一樣停下來問。

## Reproduction (WSL, 41d8f9b)

| Command | Verdict | Should be |
|---|---|---|
| `N=nextflow; $N clean -f` | pass | ask |
| `N=nextflow; ${N} clean -f` | pass | ask |
| `N=nextflow; "$N" clean -f` | pass | ask |
| `N=nextflow; $N clean -n -f` | pass | pass (dry run) |
| `N=nextflow; $N log` | pass | pass |

Constitution: Safety Net, "Deleting `work/` ... requires the user's explicit confirmation".

## Root Cause (high confidence)

`hooks/confirm_cleanup.sh`: the SN2 check reads the subcommand only after a word that is literally `nextflow`; a variable command word (`VARCMD=1`) is judged only by its targets, and only a target naming a guarded folder pauses. `clean -f` has none.

## Proposed Remediation

- With a variable command word, a segment whose first non-option word after it is `clean`, with `-f`/`-force`/`--force` and not a dry run, asks with the same work/ message as `nextflow clean -f`, naming the unknown command.
- Tests first in the SN2 section of `tests/confirm_cleanup_test.sh`: the five commands above.
- Out of scope: a command word built some other way (`eval`, an array) - the guard already cannot see through those.
