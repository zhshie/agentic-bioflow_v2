# Bug Assessment: medium/low gate shapes left after #29 (and the asks-too-often items from #33's review)

- **Slug**: gate-shapes-2
- **Created**: 2026-10-02
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/35 (details: `.specify/bugs/safety-net-bypass/test.md`)
- **Verdict**: valid; every item behaves the same on `main` (1a049f1), reproduced in WSL with the hooks' own input shape
- **Severity**: medium (a delete or a launch reaches the shell with nothing printed) and low (a false alarm, or a rare shape)

## 給維護者

1. 刪除關卡與啟動關卡各漏掉幾種「把指令交給另一層殼」的寫法：`flock -c`、`su -c`、`tmux`、`screen`、`cmd /c`、`cat <<EOF | sudo -u x bash`、`| srun bash`、`| python3`、`R -e`、`git clean -fdx`、`perl remove_tree`、`a=(rm …)`、`Start-Process nextflow`，以及相對路徑（`cd results && rm -rf x`）。
2. 另有幾個「誤報」：`rsync --dry-run --delete`、`xargs -I{} rm`、`mv -t results`、管線餵給 `Move-Item`。
3. 修法跟 #29 一樣：共用的切割器多認這幾種殼，相對路徑用 hook 輸入裡的 `cwd` 加上前面的 `cd` 解開。每一條都先寫失敗的測試（70 個失敗）。
4. 需要你決定的：下面「Decisions」那幾條。我都選了比較安全的那邊。

## Items and test cases

Tests: `tests/confirm_cleanup_test.sh` and `tests/confirm_launch_test.sh`, section "#35". A label starting `#35 control:` differs from its pair in one fact and already passed on main.

| # | Item | Today (main) | Wanted | Where |
|---|---|---|---|---|
| M1 | `flock /tmp/l -c 'rm -rf analysis'`, `su - lab -c '…'`, `tmux new -d '…'`, `tmux send-keys '…'`, `screen -X stuff '…'` outside a nested shell | pass | deny / ask / launch gate as if the string were typed | `split_segments.awk` re-reads their quoted strings |
| M2 | `cmd /c rd /s /q results`, `cmd.exe /c del …` under the Bash tool | pass | deny (ask for work/) | cleanup |
| M3 | `rsync -a --remove-source-files rawdata/ /backup/` | already asks (#29e/#33) | ask | pinned as a control only |
| M4 | `cat <<EOF \| sudo -u x bash`, `\| srun bash`, `\| srun --pty bash`, `\| ssh h bash`, `\| sudo -E bash -s`, `\| python3` | pass | judged as the piped-in command | `split_segments.awk` (and the here-doc stripper) |
| M5 | `R -e 'unlink("results", recursive=TRUE)'` | pass | ask | interpreter list |
| M6 | `cd …/results && rm -rf fastqc`, cwd inside results/, `../x`, `cd work && rm …` | pass | deny / ask | cleanup: cwd from the hook input plus `cd` tracking |
| L1 | `perl -MFile::Path=remove_tree -e …` | pass | ask | `RE_CODE_DEL` |
| L2 | `git clean -fdx` (also inside results/, or naming results/) | pass | ask / deny | cleanup |
| L3 | `Start-Process nextflow -ArgumentList 'run x'` (also `-FilePath`, comma list, `tw`) | pass | launch gate | `launch_trigger.sh` |
| L4 | `a=(rm -rf results); "${a[@]}"` | pass | deny | splitter: array assignment contents are commands |
| L5 | `rm -rf re\sults`, `r\esults/x` | pass | deny | cleanup: backslash read as an escape as well as a path separator |
| F1 | `rsync -av --dry-run --delete results/ bk/` (also `-avn`, `--dry-run --remove-source-files`) | deny / ask | pass | cleanup: a dry run deletes nothing |
| F2 | `xargs -I{} rm -rf {} < dirs.txt`, `… \| xargs -I{} rm -rf {}` | deny (`{}` was read as the filesystem root) | ask | cleanup |
| F3 | `mv -t results a b`, `mv -t results/sub a b` | ask | pass (writing INTO results/) | cleanup |
| F4 | `mv x.txt results/{a,b}.txt` | ask | **kept** (see Decisions) | none |
| F5 | pipeline-fed `Move-Item` with nothing protected | ask | pass when the pipeline's lister names an explicit, unprotected path | cleanup |

## Root cause (per family)

- M1/M4/L3/L4: the splitter re-reads quoted strings only for a fixed list of runners (`bash -c`, `eval`, `ssh`, `on_site.sh`, powershell, python/perl/ruby/node/Rscript `-c/-e`) and only a plain shell after a pipe. Anything else that hands text to a shell is invisible, and a pipe target with its own arguments is not a plain shell.
- M2: `rd`, `del`, `erase`, `ri` count as delete verbs only for non-Bash tools (they are ordinary words in a Bash command), and `cmd /c` was not recognised as the thing that makes them verbs.
- M5/L1: the interpreter list and `RE_CODE_DEL` do not know `R`/`remove_tree`.
- M6: targets are judged as written; the hook input's `cwd` and a preceding `cd` were never used.
- L5: every backslash was turned into a slash (for Windows paths), so an escape reads as a path separator.
- F1-F5: dry-run is not looked at; `{}` is munged into `//` and matches the "filesystem root" rule; `-t DIR` leaves DIR in the list of sources; a pipeline-fed `Move-Item` has no source on its own line.

## Decisions (safer option taken; listed again in fix.md)

- F4 kept as ask. Bash expands `mv x.txt results/{a,b}.txt` to `mv x.txt results/a.txt results/b.txt`: `results/a.txt` is then a source moved into the directory `results/b.txt`. That is a real move out of results/, not a false alarm. Moving INTO results/ with a single destination stays quiet.
- M6 resolves a relative target even when the session's cwd is simply a folder named `analysis/`, `results/` or `rawdata/` (any component): the same rule as the absolute spelling, which main already denies. A `cd` is assumed to persist for the rest of the command (a subshell's `cd` is over-applied, the safe direction); a `cd` to something that cannot be resolved (variable, `~`, `-`) makes later relative targets unknown, as on main.
- F2: `{}` placeholders ask (not pass): the real targets come from a command this hook cannot see. `find /tmp/x … -exec rm {} \;` therefore asks instead of the accidental "filesystem root" deny.
- F5: only when the lister before the pipe names an explicit path with no protected name, variable or glob. A bare `ls | Move-Item`, a variable path, and anything passing through `ForEach-Object` keep asking.
- F1: a dry run is believed (`--dry-run`, or `n` in a short-option cluster).

## NOT changed

- No gate went quieter than main except F1 (dry runs), F3 (writing into) and F5 (provably unprotected lister), which the issue and its comment call false alarms.
- The three launch-gate rules, `confirm_walkthrough.sh`, the in-use scope, timeouts.
- Performance is #34.
