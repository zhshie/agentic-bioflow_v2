# Bug Assessment: the safety gates take seconds per shell call on Windows Git Bash

- **Slug**: gate-speed
- **Created**: 2026-10-04
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/34
- **Verdict**: valid
- **Severity**: high (not the wait itself - a PreToolUse hook that runs past its `timeout` is cancelled and the tool call PROCEEDS, so speed is safety; invariant 13, constitution 2.0.0. #29 raised the timeouts to 30 s; this is what keeps the gates far from them)

## 給維護者

1. 每一次 Bash 呼叫，四道關卡（發射、刪除、導覽、外掛檔案保護）會同時各跑一遍，每一道要 0.5～3.6 秒，最壞的一道（導覽關卡遇到發射指令）11 秒。
2. 原因不是判斷複雜，而是在 Windows 的 Git Bash 上「啟動一個外部程式」很貴（約 0.1 秒），而關卡每次啟動 8～33 個（`cat`、`jq` 三到六次、`dirname`、`grep`、`sed`、`awk`、`uname`、`tail`）。
3. 修法：外部程式的數量降到「`jq` 一次＋`awk` 一次（切割指令）」，其餘全在 bash 內建完成；判斷結果不能有任何差異（逐字比對舊版與新版）。
4. 驗收看的是「啟動的程式數」（與機器無關），牆鐘時間另外量。

## Measured baseline (native Git Bash, Windows 11, `c440785`)

`measure.sh` in this folder: 10 calls per case on an in-use session (marker present, a 200-line transcript), median wall time; the process count is a separate run with a logging shim in front of every external program.

| Hook | `grep -rn x results/` | multi-segment | 30-line script | launch |
|---|---|---|---|---|
| confirm_launch | 1721 ms / 15 procs | 3610 / 15 | 1558 / 15 | 1257 / 16 |
| confirm_cleanup | 673 / 8 | 967 / 8 | 1606 / 8 | 1441 / 8 |
| confirm_walkthrough | 1353 / 19 | 2908 / 19 | 2285 / 19 | 11011 / 33 |
| guard_plugin_files | 535 / 6 | 594 / 6 | 1520 / 6 | 1828 / 6 |

(The wall times scatter by a factor of two between runs on this machine - antivirus and other work - which is why the process count is the thing a test can pin.)

Which programs, on an ordinary command (`ls -la`): launch `cat jq jq jq dirname dirname grep grep awk awk uname dirname awk dirname awk`; cleanup `cat jq jq jq dirname awk dirname awk`; walkthrough `cat jq*6 dirname awk grep sed head sed dirname dirname awk awk tail grep`; guard `cat sort uname jq jq jq`.

## Root causes

1. **Stdin read by `cat`** - one process per hook, where `read` is a builtin.
2. **jq started 3-6 times per call**: a "can jq run" probe, then one `jq -r` per field (tool, command, file, content, transcript path).
3. **`dirname "$0"` in command substitutions**, once per use (2-4 per hook; `launch_trigger.sh` did `cd`, `dirname` and a subshell to find its own folder).
4. **`printf '%s\n' "$CMD" | awk`** where a here-string does the same; the here-doc stripper started even for commands that contain no `<<`, which is the normal case.
5. **`echo | grep` / `grep | sed | head` for yes/no questions** a `[[ =~ ]]` answers (the relay-restart and `tw launch` checks, the walkthrough's analysis/ candidate even when "analysis/" is nowhere in the command).
6. **`uname -s`** (launch D3 and the plugin-file guard) asked on every call, though its answer matters only for a command that names ssh/scp/rsync/sftp.
7. **`tail | grep -q` on the transcript** (walkthrough G6): two processes where one `tail` into a variable does it.
8. Guard: `sort -u` over the root spellings, `uname`, three `jq`, and a `grep`/`sed` per segment.

The classification itself (per segment, per argument) is already in-shell since #29 round 3 - the cost left is the fixed overhead above, paid by every call whether or not a gate has anything to say.

## Proposed remediation

- jq once for the input (a record separator between fields; anything unusual - not JSON, an object-valued field, two documents - falls back to the old probe-then-per-field path, so odd inputs behave as before).
- `read` for stdin, `$HD` for the hook folder, here-strings into awk, bash regex in place of one-line greps (taking care that `[[:space:]]` and `^` mean different things across a newline in bash than in grep).
- The two awk passes (strip here-docs, split segments) only when needed; at most one for an ordinary command.
- Budget pinned in `tests/gate_process_count_test.sh`; behaviour pinned by the existing gate tests plus a verdict diff of old vs new hooks over every command string those tests use and 50 everyday commands.
- Out of scope: the cost of `scripts/settings.sh` / `egress_ctl.sh` that a real launch ask runs on purpose.
