# Bug Assessment: the deletion guard can run past its timeout on a large here-doc, and the call then proceeds

- **Slug**: gate-speed-big-heredoc
- **Created**: 2026-10-05
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/62 (found by the acceptance of #34)
- **Verdict**: valid
- **Severity**: high (a delete of results/ after a large script can go through with no prompt on a busy Windows machine)

## 給維護者

1. 一個 Bash 呼叫如果先用 here-doc 跑一段很長的 python（例如 300 KB），最後再刪 results/，刪除關卡在 Windows 原生 Git Bash 上要跑 23 秒到 115 秒。
2. hooks.json 給每個關卡 30 秒；超過就被 Claude Code 取消，而被取消的 PreToolUse hook 等於「放行」。所以機器一忙，這個刪除就會在沒人被問的情況下執行（違反不變式 13：安全網做不到時必須說出來）。
3. 原因：here-doc 的每一行都被當成一個指令，逐行做二十幾個判斷；而 Git Bash 的 bash 一旦手上握著幾個大字串，每個小動作都會慢 18–30 倍（實測），所以總時間不是線性的。
4. 修法：大輸入先用一個 awk 把「不可能是刪除」的行整批濾掉（判斷條件就是後面各條規則自己的正規式，不是另一份手寫清單），bash 只看剩下的幾行；另外加一個 20 秒的自我期限，萬一還是來不及，就改成「請使用者確認」而不是被取消後放行。

## Reproduction (native Git Bash, Windows 11, this machine, c018c15)

`C:\Users\ACER\abf_audit2\t62.sh` / `gen62.py`: `python3 - <<'EOF'` + N KB of `xN = N  # filler line` + `EOF` + `rm -rf /work/u/lab_runs/x/results`.

| input | total | of which the segment loop |
|---|---|---|
| 30 KB (about 1,100 segments) | 1.6 s | 0.9 s |
| 100 KB (3,700) | 50 s | 46 s |
| 300 KB (11,000) | 116 s | most of it |

490de98 (the WIP pre-filter) brought 300 KB to 3-17 s; the loop alone still took 1.7-16.7 s from run to run.

## Root Cause (high confidence, measured)

Stage timings at 300 KB (profiling copy of the hook): read 2 ms, in_use 30 ms, jq 0.6-1.0 s, strip_heredocs.awk 0.1-0.7 s, split_segments.awk 0.45 s, segment loop 1.7-117 s.

1. The loop does the whole judgement for every segment, and the body of a here-doc fed to python is kept on purpose (#29), so 300 KB is 11,000 segments.
2. Per segment the cost is not constant. Bisecting the loop body at 100 KB: an empty body 0.3 s, five of the regex tests 0.5 s, `is_dry_run` alone 22 s. `is_dry_run` starts a here-string per call. With the here-string replaced, 100 KB fell to 2 s, but 300 KB still took 74 s.
3. On MSYS bash every operation slows down once the shell holds a few large strings (here `INPUT`, `JQ_OUT`, `CMD`, `STRIPPED`, `SEGMENTS`): a bare `read` loop over 11,000 lines went from 0.6 s to 18 s, and 11,000 calls of a small function from 0.4 s to 6.7 s, after five 300 KB strings were created. So any per-segment loop over a large input is slow there, however cheap its body.
4. The WIP pre-filter (490de98) skips a segment by a hand-kept list of stems, so its correctness depends on that list matching every rule after it; it already misses the shapes added on this branch (`nextflow clean`, rclone, tar, zip, ...).

## Proposed Remediation

- When the segment list is large (over 8 KB), filter it with one awk pass before the loop. A segment is kept when its command word is one the loop handles (including `cd` and the PowerShell listers, which carry state) or its quote-free text matches one of the loop's own trigger regexes, passed to awk unchanged; each run of dropped segments becomes one marker line, which resets the lister state exactly as any other command does. The trigger list is built from the same variables the rules use, and `tests/confirm_cleanup_test.sh` is also run with every case behind a large here-doc, so a rule the filter does not reach fails a test.
- Small inputs keep the current path (no extra process: `tests/gate_process_count_test.sh` budget), and the WIP stem list is removed.
- No here-string in the per-segment path (`is_dry_run`, the target words).
- A deadline: past 20 s of the hook's own time the loop stops and the hook asks, saying the command was too large to check in time (invariant 13), instead of being cancelled at 30 s.
- Tests: a 30 KB vs 300 KB timing case in `tests/gate_big_input_test.sh` (ratio, generous bound); the deadline case; every case of `tests/confirm_cleanup_test.sh` behind a large here-doc.
- Out of scope: the launch, walkthrough and plugin-file gates (another branch owns them).

## Found while fixing: a here-doc of pipelines (added 2026-10-05)

A shell script fed to bash (`bash <<'EOF'`, every line `cat f | grep x | sort`) took 1 s at 30 KB and 39 s at 100 KB in `hooks/split_segments.awk` alone (native Git Bash), and 62 s for the whole hook; in WSL 300 KB ran past 30 s. Two causes:
1. `pipes_into_runner` (in both `split_segments.awk` and `strip_heredocs.awk`) copies the rest of the string at every pipe (`substr(t, …)`, then a regex over that copy): quadratic in the number of pipes. The backtick scan (`index(substr(str, i + 1), "`")`) has the same shape.
2. The large-input filter keeps every segment whose command word carries PowerShell lister state, and `sort`, `ls`, `dir`, `select`, `where` are among them: every line of such a script is kept.

Remedy: split once on the pipes (each piece is the text between two pipes, so the work is linear) and scan forward for the closing backtick; in the filter, hold a run of listers and pipeline filters back and keep it only when a PowerShell move follows it (the only rule that reads that state). The splitter is shared with the launch gate (`hooks/launch_trigger.sh`); the change is meaning-preserving, and both copies of `pipes_into_runner` stay identical. Test: a third body ("pipes") in the #62 block of `tests/gate_big_input_test.sh`.
