# Bug Assessment: the launch gate fails OPEN when its own message is too large to build

- **Slug**: gate-fail-open-big-output
- **Created**: 2026-10-05
- **Source**: fresh audit against constitution 2.0.0 (`C:\Users\ACER\abf_audit2\`, tcat.sh), invariant 13 and Safety Net 3
- **Verdict**: valid
- **Severity**: high (a launch the gate recognised goes through with no prompt)

## 給維護者

1. 關卡認出「這是一次送出分析」之後，要把整條指令放進給使用者看的確認訊息；組訊息用 `jq --arg`，而 `--arg` 把整條指令塞進程序的命令列參數。
2. 命令列參數有上限（Windows 約 32 KB、Linux 單一參數 128 KiB）。超過時 jq 失敗、什麼都不印，而 hook 接著 `exit 0`，等於「放行」。所以一條夠長的指令（例如先用 here-doc 寫一個大檔、再 `tw launch`）會直接送出，沒人被問。
3. 同樣的寫法在其他三道關卡（刪除、導覽、外掛檔守衛）的 deny／warn／ask 也有：訊息建不出來就靜靜放行。
4. 修法：顯示的文字有上限（頭尾各留一段，中間註明「省略 N 字」；判斷本身仍看完整指令），並且訊息建不出來時改印一個固定的最小 ask，而不是什麼都不印。

## Reproduction

`tests/gate_big_input_test.sh` case "128 KB here-doc then tw launch (launch gate)": want `ask`, got none, at 32 KB on native Git Bash (jq argv limit) and at 128 KB on Linux. Before this fix the test skipped the assertion.

## Root Cause (high confidence)

`ask()` in hooks/confirm_launch.sh (`jq -n --arg r "$2"` then `exit 0` without looking at jq's status); `deny()`/`warn()`/`ask()` in confirm_cleanup.sh, confirm_walkthrough.sh and guard_plugin_files.sh have the same shape. The messages carry the command (launch REASON = the whole command; MCP ask = the whole $INPUT; direct-ssh ask).

## Other hooks checked

- next_step.sh (Stop hook, advisory): jq args are a command word and a short flow list; not a safety gate; unchanged.
- session_start.sh, plugin_intro.sh: context text of bounded, plugin-owned size; unchanged.
