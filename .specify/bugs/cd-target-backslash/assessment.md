# Bug Assessment: the cleanup gate does not follow a directory change written with a backslash, or by PowerShell's Set-Location

- **Slug**: cd-target-backslash
- **Created**: 2026-10-10
- **Source**: issues #76 (security review of PR #74) and #75 (found while fixing #66)
- **Verdict**: valid
- **Severity**: high (a delete inside results/ or rawdata/ passes silently)

## 給維護者

1. 刪除關卡會記住「現在切到哪個資料夾」，再判斷後面的相對路徑刪除。
2. 兩種切換它跟丟了：資料夾名字中間夾反斜線（`cd res\ults`，shell 會拿掉反斜線、真的切進 results），以及 PowerShell 的 `Set-Location`／`sl`／`Push-Location`。
3. 跟丟之後，`rm -rf x` 就被當成刪一個無關的地方，直接放行。
4. 修法：關卡同時記兩個「目前資料夾」（照原樣讀、去掉反斜線讀），兩個都判，取比較嚴的；PowerShell 的切換指令當成 `cd` 處理。

## Reproduction (WSL, main c4a7327, jq 1.7.1, session cwd /tmp, R=/work/u9613010/lab_runs/x)

| Command | Tool | Verdict | Same command without the trick |
|---|---|---|---|
| `cd R; cd res\ults; rm -rf x` | Bash | pass | deny |
| `cd R; cd raw\data; rm -rf x` | Bash | pass | deny |
| `cd R; cd wo\rk; rm -rf x` | Bash | pass | ask |
| `pushd R/.nextflow/plug\ins; rm -rf x` | Bash | pass | deny |
| `cd R/res\ults; rm -rf .` | Bash | pass | deny |
| `Set-Location R/results; Remove-Item -Recurse x` | PowerShell | pass | deny (`cd`) |
| `sl R/results; Remove-Item -Recurse x` | PowerShell | pass | deny |
| `Push-Location R/results; Remove-Item -Recurse x` | PowerShell | pass | deny |
| `Set-Location R/results; rm -rf x` | Bash (pwsh-style text) | pass | deny |

Corrected by the verifier (CONTRACT, 2026-10-10): issue #76 item 2 DOES reproduce in the relative form. `Get-ChildItem res\ults | Move-Item -Destination x` (session cwd /tmp or R), `raw\data`, `gci res\ults`, `ls res\ults` pass on main, while the plain `Get-ChildItem results | Move-Item ...` asks. Only the absolute form `Get-ChildItem R/res\ults | ...` already asks. Cause: #74 restores LISTER_OK after the dropped-backslash copy, so the copy (which reads the protected `results`) can never make the lister verdict stricter.

Constitution: Safety Net, "Never delete a user's source data"; "Deleting work/ requires the user's explicit confirmation".

## Root Cause

`hooks/confirm_cleanup.sh` keeps one working directory (VCWD) across segments. Its `cd`/`pushd` handler reads the target as written (a backslash becomes `/`), and PR #74 deliberately stops the dropped-backslash copy from changing VCWD (so the copy cannot loosen anything). So the directory the shell really enters (`results`) is never tracked. Separately, PowerShell's location cmdlets are not recognised as directory changes at all.
