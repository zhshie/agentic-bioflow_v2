# Bug Assessment: the in-use check misses several spellings of a path under the deployment

- **Slug**: in-use-path-spellings
- **Created**: 2026-10-05
- **Source**: fresh audit against constitution 2.0.0 (`C:\Users\ACER\abf_audit2\scope.sh`), Safety Net scope condition 3 ("names a path under the deployment, in any spelling")
- **Verdict**: valid
- **Severity**: medium (in a session with no marker and a cwd outside the deployment, a delete of `results/` or a launch that names the run area this way gets no gate at all)

## 給維護者

1. 「這個 session 有沒有在用 plugin」的第 3 個條件是：這次呼叫用**任何寫法**指到部署底下的路徑。今天有幾種寫法認不出來，整個安全網就當作「沒在用」而不出聲：
   - `"$LAB_RUNS_DIR/p/results"`：這個變數就是部署的 run 區（`storage_root` 匯出成 `LAB_RUNS_DIR`），但 hook 只比對寫出來的字；
   - 相對路徑：工作資料夾在家目錄、storage_root 是 `~/runs3` 時的 `rm -rf runs3/p/results`、`cd runs3/p && rm -rf results`，以及從旁邊資料夾的 `../runs3/p/results`；
   - 同一類的小洞：PowerShell 的 `$env:USERPROFILE\runs3\...`、`x=~/runs3/...`（`=` 後面的 `~`）。
2. 修法往「寧可判成在用」的方向：`$LAB_RUNS_DIR` 換成 hook 看到的值（沒有就用部署自己的 storage_root）再比；從目前資料夾算出到 storage_root／部署根目錄的相對寫法（`runs3`、`../runs3`）也拿來比；`$env:USERPROFILE`、`%USERPROFILE%` 當作家目錄，`=`、`:` 後面的 `~/` 也展開。
3. 沒在用時的成本不變：這些比對只在「已經有部署、又還沒判定在用」時才做，而且不開新程序；`tests/in_use_speed_test.sh` 要維持在基準的 1.1 倍以內。

## Reproduction (WSL, HEAD 490de98, `scope.sh`: no marker, storage_root `$HOME/runs3`)

| cwd | command (hook env) | Today | Should be |
|---|---|---|---|
| `$HOME` | `rm -rf "$LAB_RUNS_DIR/p/results"` | pass | deny |
| `$HOME` | same, `LAB_RUNS_DIR=$HOME/runs3` | pass | deny |
| `$HOME` | `rm -rf runs3/p/results` | pass | deny |
| `$HOME` | `cd runs3/p && rm -rf results` | pass | deny |
| `$HOME/other` | `rm -rf ../runs3/p/results` | pass | deny |
| `$HOME` | PowerShell `Remove-Item -Recurse -Force $env:USERPROFILE\runs3\p\results` | pass | deny |
| `$HOME` | `x=~/runs3/p/results; rm -rf $x` | pass | deny |
| `$HOME/runs3` | `rm -rf p/results` | deny | deny |

## Root Cause (high confidence)

`hooks/in_use.sh` `_abf_in_use_inner` compares the call's text with the bases (deployment root, storage_root, `LAB_RUNS_DIR`) only as absolute paths, with `~`, `$HOME` and `${HOME}` expanded (the `~` only after a blank). It never expands `$LAB_RUNS_DIR`, never resolves a relative path against the session's cwd, and does not know PowerShell's name for the home directory.

## Scope / fix direction

- Section 4 of `_abf_in_use_inner` (a deployment exists): `$LAB_RUNS_DIR`, `${LAB_RUNS_DIR}`, `$env:LAB_RUNS_DIR`, `%LAB_RUNS_DIR%` become the hook's `LAB_RUNS_DIR` or, when unset, storage_root; any other `${LAB_RUNS_DIR...}` form counts as naming it.
- For each cwd form and each base, the relative path from one to the other (`runs3`, `../runs3`, `home/runs3`) is looked for at the start of a word, optionally after `./`. A single name under 4 characters is ignored (short names prove nothing, as for absolute paths).
- Home spellings: `$env:USERPROFILE`, `${env:USERPROFILE}`, `%USERPROFILE%`, `$env:HOME`; `~/` after `=`, `:`, `"` or the start of the text as well as after a blank.
- Tests: `tests/in_use_test.sh`, every shape with a control that differs in the one folder name.

## NOT changed

- `~otheruser/...`, a relative path that walks through `..` in the middle (`a/../runs3`), and paths assembled at run time.
- What any gate decides once the session is in use.
