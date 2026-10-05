# Bug Assessment: a jq that is present but broken can make the deletion guard fall silent

- **Slug**: jq-broken-cleanup
- **Created**: 2026-10-05
- **Source**: fresh audit against constitution 2.0.0, invariant 13 ("with jq missing or broken, the gates refuse what they cannot rule out from the raw text and name the fix")
- **Verdict**: valid
- **Severity**: high (a delete of results/ passes with nothing printed)

## 給維護者

1. 刪除關卡靠 jq 讀出「這次要執行的指令」。jq 不存在、或一執行就失敗時，關卡會改看原始文字、看起來像刪除就擋，並說出怎麼裝 jq——這部分有測試、也正常。
2. 但 jq「存在、會回答、答案卻是錯的」時就不一定了：例如 jq 對什麼都只印 `{}`、印一行亂碼、什麼都不印、或只有讀指令那一步失敗。實測有好幾種情況，`rm -rf …/results` 會被直接放行，或關卡印出一個沒有決定的 `{}`（等於放行）。
3. 另一個洞在「沒有 jq」那條退路本身：它只看原始文字裡有沒有 ` rm ` 這種字，但多行指令在原始 JSON 裡是 `\nrm`，前面黏著 `\n`，所以第二行以後的刪除完全看不到；`truncate`、`unlink` 也不在它的清單裡。
4. 修法：讓 jq 每次都順便答一個已知答案的小題目（答錯就當作 jq 壞了、走跟「沒有 jq」一樣的退路，並說是 jq 的答案不對）；讀不出指令、但原始輸入明明有指令時也一樣；關卡自己組出來的回覆如果不是它該有的樣子，就改印固定的「請確認」；退路的文字掃描改成也看得到第二行以後與 truncate／unlink。

## Reproduction (WSL, 29e7b98; a jq shim first on PATH; `<run>` = /w/lab_runs/x)

| jq on PATH | `rm -rf <run>/results` | the same on line 2 | `ls -la` |
|---|---|---|---|
| prints `{}` for everything | prints `{}` (no decision: proceeds) | pass | pass |
| prints a line of text | ask | pass | pass |
| prints nothing, exit 0 | ask | pass | pass |
| answers the one-call read with an empty command | pass | pass | pass |
| fails only when asked for the command field | pass | pass | pass |
| fails nothing, but `jq -n` prints `{}` | prints `{}` | prints `{}` | pass |
| exits 127 (covered today) | BLOCKED (exit 2) | pass | pass |
| none on PATH (covered today) | BLOCKED (exit 2) | pass | pass |

`truncate -s 0 <run>/results/x.tsv` and `unlink <run>/results/x.tsv` with no jq: pass.

## Root Cause (high confidence)

`hooks/confirm_cleanup.sh`:
1. The one-call read (`jq -js …`) is trusted whenever it printed anything; its fields are read up to `\037` and a missing separator is not noticed. The fallback probe (`printf '{}' | jq -e .`) only checks the exit status, so a jq that exits 0 passes it.
2. The per-field fallback ignores jq's exit status; a failed read of the command leaves `CMD=""`, and an empty command with `tool_name` Bash exits 0.
3. `abf_emit` accepts jq's output when it starts with `{`, so `{}` is printed as the verdict.
4. `looks_delete_shaped` folds JSON punctuation to spaces but not the `\n`/`\t`/`\r` escapes, so a verb after a line break is glued to `n`; its verb list lacks truncate and unlink (and the shapes added on this branch).

## Proposed Remediation

- The one-call read also prints a fixed token computed by jq; it is trusted only when the token, both separators and nothing else are there. The fallback probe asks jq for a computed string and compares it.
- A command that comes back empty while the raw input has a non-empty command field (or a per-field read that fails) means jq's answer cannot be trusted: the raw-text path, as with no jq, with a message saying jq answered wrongly.
- `abf_emit` prints jq's output only when it carries `hookSpecificOutput`, the event name and the decision it was asked for; otherwise the fixed minimal ask.
- The raw-text scan reads `\n`, `\t`, `\r` escapes as separators (and fails closed if its own tools are missing), and knows truncate, unlink, `nextflow … clean`, `git … clean`, `--remove-files`, `rclone`, and the code-delete names.
- Tests first in the "no jq" section of `tests/confirm_cleanup_test.sh` (the constitution's check for invariant 13): each shim above, a delete on line 1 and on line 2, and an unrelated command that must still pass.
- Out of scope: the other three gates (another branch owns them); a jq that answers a plausible but wrong command (only an adversary does that).
