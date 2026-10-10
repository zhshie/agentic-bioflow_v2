# Bug Assessment: a backslash inside a delete command word hides it from the cleanup gate

- **Slug**: backslash-inside-delete-word
- **Created**: 2026-10-10
- **Source**: issue #66 (round-3 acceptance of #65)
- **Verdict**: valid
- **Severity**: high (a delete of results/ passes with nothing printed)

## 給維護者

1. 在指令名字中間夾一個反斜線（`r\m`、`t\ar`、`cl\ean`），shell 會把反斜線拿掉、照樣執行刪除。
2. 刪除關卡只認得「開頭」的反斜線（`\rm`，#65 修好），夾在中間的完全看不到，直接放行。
3. 修法：照搬送分析關卡已經在用的做法——有反斜線的片段，去掉反斜線再判一次（原樣那份也照判）。

## Reproduction (WSL, main bec2ea5, jq 1.7.1, cwd a run folder with results/)

| Command | Verdict | Without the `\` |
|---|---|---|
| `r\m -rf results` | pass | deny |
| `t\ar --remove-files -cf a.tar results` | pass | deny |
| `tar --remo\ve-files -cf a.tar results` | pass | deny |
| `nextflow cl\ean -f` | pass | ask |

Controls that must stay pass: `printf 'a\nb'`, `grep -E "a\sb" file`.

Constitution: Safety Net, "Never delete a user's source data"; "Deleting work/ requires the user's explicit confirmation".

## Root Cause

`hooks/confirm_cleanup.sh` matches command words and options as written. `hooks/launch_trigger.sh:135-145` (gates-audit2-low, #65) already judges every segment holding a backslash a second time with its backslashes dropped, as an added copy; the cleanup gate has no equivalent. Not a regression (present before #65).
