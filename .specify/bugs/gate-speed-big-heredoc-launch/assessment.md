# Bug Assessment: the launch gate, and the in-use check every gate runs first, are not linear on a big here-doc

- **Slug**: gate-speed-big-heredoc-launch
- **Created**: 2026-10-05
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/62 (found on the deletion guard; the launch gate has the same shape), audit `C:\Users\ACER\abf_audit2\t62.sh`
- **Verdict**: valid
- **Severity**: high (a PreToolUse hook that runs past its `timeout` lets the call PROCEED: a launch, or a delete the in-use check was still deciding about, goes through with no prompt; invariant 13, Safety Net 3)

## 給維護者

1. 一個 Bash 呼叫如果先帶一大段 here-doc（例如 300 KB 的 python 腳本），再接 `tw launch`，啟動關卡在原生 Git Bash 上要跑 7–60 秒；hooks.json 只給 30 秒，超時就等於放行。
2. 慢的地方有三個：(a) 關卡把 here-doc 的每一行都當成一段指令，在 shell 裡逐行讀（Git Bash 上這種逐行讀超過線性）；(b) 每支關卡最先問的「這個 session 有沒有在用 plugin」（`hooks/in_use.sh`），在沒有 marker 的 session 裡會對整段文字做幾種在 bash 裡是平方時間的字串操作——300 KB 的 here-doc 後面接一個刪除或送出、指到部署資料夾，連在 WSL 都要 36 秒；(c) 啟動關卡裡管 egress 白名單的那段，遇到很多 `*`、`[`、`.tsv` 的程式碼時逐行做重活。
3. 先前的 WIP 預先過濾（commit 490de98）讓速度好一些，但也弄丟了三種寫法：`s"b"atch`、`tw l"aun"ch`、`nextflow r"u"n`（引號拼字）在 c018c15 會問，WIP 之後不問。
4. 修法：大輸入時先用一次 awk 把「不可能有關」的行挑掉（條件與後面逐段判斷用的完全一致，只會多留、不會少留），引號拼字的預先過濾改看「去掉引號後」的文字；`in_use.sh` 改用一次正規表達式找路徑、大文字的正規化交給一次 `sed`；egress 那段先用便宜的條件跳過不可能相關的行。判斷結果不變。

## Reproduction

Native Git Bash, Windows 11, HEAD 490de98, `t62.sh` (marker present, cwd outside), one run each (the machine was shared with other agents; times scatter up to 2x):

| input | launch gate |
|---|---|
| 130 KB here-doc + `rm -rf .../results` | 15.6 s |
| 300 KB here-doc + `rm -rf .../results` | 16.8 s |
| 300 KB here-doc + `tw launch` | 6.9 s (ask) |

Profile of the 300 KB launch (native, micro-timed): `is_launch_command` 5.7 s, of which the shell `while read` over ~11 000 segments 3.5 s (30 KB: 0.1 s, so superlinear), the nested-shell regex over the whole command 0.4 s, the two awk passes 1.4 s. The D3 loop walks the same 11 000 segments again on MSYS when the command is not a launch.

The same cases in WSL (Linux bash), HEAD 490de98, `g2b_time.sh`:

| situation | 30 KB | 300 KB |
|---|---|---|
| marker, here-doc + `tw launch` | 0.7 s | 0.9 s |
| no marker, cwd under storage_root, here-doc + `tw launch` | 1.5 s | 5.4 s |
| no marker, cwd outside, here-doc + `rm -rf <storage_root>/p/results` | 1.1 s | **36.3 s** |
| marker, code-like here-doc (quotes, `[`, `*`, `.tsv`) + `tw launch` | 1.2 s | 10.8 s |

`abf_in_use` alone, native, no marker, 300 KB: 9-110 s.

Quote-spliced launch spellings, native, c018c15 vs HEAD: `s"b"atch job.sh`, `tw l"aun"ch x`, `nextflow r"u"n x` ask on c018c15 and pass silently on HEAD.

## Root Cause (high confidence, measured)

1. `hooks/launch_trigger.sh` `is_launch_command`: every segment of the split command goes through a `while read` loop in the shell; a kept here-doc body (`python3 - <<EOF`) is thousands of segments. Under Git Bash this loop is superlinear. `LAUNCH_NESTED_SHELL_RE` runs over the whole command even when no segment needs it. The WIP prefilter (`case "$S$V" in *launch*...`) reads the segment WITH its quotes, so a quote-spliced verb no longer reaches the checks that would have caught it.
2. `hooks/confirm_launch.sh`: D3 walks the same segments again in a `while read` loop; the egress-allowlist block (entered whenever the command mentions `.tsv`, or a glob/`$` and the word add/remove) does word loops and here-strings per segment; `EA_N` drops quotes with `${x//p/}` (quadratic in the number of quotes); `RELAY_OVR` uses `${CMD#*...}`.
3. `hooks/in_use.sh`: `_abf_has_path` uses `${t#*"$p"}` (bash tries every prefix: quadratic, 89 s at 100 KB); the text normalisation replaces `\n` with `${x//p/}` once per line (quadratic in the number of matches); the bare-`cd` check squeezes double spaces in a loop of global replacements.

## Scope / fix direction

- Big inputs only (over 16 KB of segments, or 8 KB of in-use text): one `awk`/`sed`/`tr` process does the linear part. Small commands keep the fork-free path (#34).
- The awk filters keep exactly the segments the per-segment checks could act on: for the launch check, a segment whose quote-free text or quote-dropped text holds `launch`, `sbatch`, `run` or `--confirm`, or the too-deep marker; for D3, a segment whose quote-free text holds a transport word; for the allowlist block, a segment that names `egr`/`ess`/`allow`, holds `$`, is a bare assignment, or holds a glob next to a `/` (or the cwd is a config or scripts folder).
- `in_use.sh`: `_abf_has_path` becomes one regex; the bare-`cd` check becomes two regexes; normalisation of a big text is one `sed`.
- Tests: `tests/confirm_launch_test.sh` (the three quote splices; every spelling re-run after a 20 KB here-doc with the same expected answer), `tests/gate_big_input_test.sh` (launch timing block: ratio 30 KB vs 300 KB and a 25 s bound; in use by cwd and by a named path with no marker).

## NOT changed

- What any gate decides on any command (the filters only skip segments the checks cannot act on).
- `hooks/confirm_cleanup.sh` (another branch); it gets the `in_use.sh` part of this fix for free.
- The 30 s timeouts in hooks.json.
