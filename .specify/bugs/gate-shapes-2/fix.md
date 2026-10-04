# Fix: gate-shapes-2 (#35, with the asks-too-often items from the #33 comment)

- **Branch**: `fix/35-gate-shapes` (stacked on `fix/44-d3-native`)
- **Changed**: `hooks/split_segments.awk`, `hooks/strip_heredocs.awk`, `hooks/launch_trigger.sh`, `hooks/confirm_cleanup.sh`; tests in `tests/confirm_cleanup_test.sh` and `tests/confirm_launch_test.sh` (section "#35", 70 new red cases, 8 controls among the ~125 new assertions)
- **What changed**
  - Splitter (`split_segments.awk`): re-reads the quoted strings of `flock|su|runuser|sg ... -c`, `tmux`, `screen`, `R -e`; reads the inside of an array assignment `a=(...)` as a command; a pipe now counts as handing its input to a runner when, after any wrappers with options (`sudo -u x`, `srun --pty`, `env`, `timeout 60`, `nice -n`), a shell or interpreter (bash, sh, ssh, python, perl, R, ...) follows (`pipes_into_runner`, same two functions in `strip_heredocs.awk` so a here-doc body piped into such a runner is kept).
  - `launch_trigger.sh`: `Start-Process <prog> -ArgumentList ...` is read as the command line it makes (parameter names and commas dropped).
  - `confirm_cleanup.sh`: `cmd /c rd|rmdir|del|erase|ri`; `git clean -f` (ask; deny when it names or runs in a protected folder; `-n`/`--dry-run` quiet); `remove_tree`; a backslash in a name is also read as an escape (`re\sults`); relative targets resolved against the hook input's `cwd` and any earlier `cd` (in-shell, no process); `rsync --dry-run`/`-n` no longer a delete or a move; `{}` placeholders ask instead of reading as the filesystem root; `mv -t DIR` excludes DIR from the sources; a pipeline-fed `Move-Item` is quiet when the lister before it names an explicit unprotected path (through `Where/Select/Sort/Measure-Object` filters).
- **Red -> green** (WSL): 70 failing assertions before (54 in the cleanup file, 16 in the launch file), 0 after; each has a control that differs in one fact. Also green: confirm_walkthrough, in_use, in_use_speed, constitution_scope, guard_plugin_files, next_step, plugin_intro, init_workspace, principle_12/13.
- **Compared with main** on 81 shapes (cleanup and launch hooks side by side): every row where main denied/asked and the branch passes is one the issue calls a false alarm: `rsync --dry-run/-n` (x3), `mv -t results` (x2), pipeline-fed `Move-Item` with an explicit lister (x3). Deny-to-ask only for `xargs -I{} rm -rf {}` (x2) and `find ... -exec rm {}` outside results/ (the old deny was `{}` read as `/`).
- **Item M3** (`rsync --remove-source-files`) was already fixed by #29e/#33 on main (asks); pinned as a control.
- **Not fixed / kept**
  - F4 `mv x.txt results/{a,b}.txt` keeps asking: bash expands it to `mv x.txt results/a.txt results/b.txt`, whose source `results/a.txt` really is moved out. Not a false alarm.
  - `cmd /c` verbs are matched only right after `/c`; `cmd /c "echo x & rd ..."` splits on `&` and the second part is a plain `rd`, quiet under the Bash tool (same as main).
  - Writing a python/R body that is piped in is judged by what it calls (`rmtree`, `unlink`, `remove_tree`), not by what it deletes: ask, as for `python -c`.
- **Needs maintainer decision** (safer option taken in each)
  1. Relative targets are judged by the session's `cwd`: in a session in use, `rm x` with the session sitting in any folder called `analysis/`, `results/` or `rawdata/` is now denied, the same as `rm analysis/x` already was. A `cd` is assumed to last for the rest of the command (subshell `cd` over-applied).
  2. `echo 'rm -rf x' | python3` (shell text into python) is denied like a shell pipe: the splitter cannot tell code from commands.
  3. `find /tmp/x -exec rm {} \;` and `xargs -I{} rm {}` ask (they used to deny by accident); say if you want a plain pass for unprotected find paths.
  4. A dry run (`rsync -n`, `--dry-run`) is believed even with `--delete`/`--remove-source-files`.

## After independent acceptance

Findings fixed here (branch `fix/35-gate-shapes`, tests in `tests/confirm_cleanup_test.sh` and `tests/confirm_launch_test.sh`, labelled `#35b`).

1. **HIGH regression: a wrapper's `-n` was read as rsync's dry run.** `hooks/confirm_cleanup.sh` treated ANY `-n` in the segment as a dry run, so `nice -n 10 rsync -a --delete src/ .../results/`, `srun -n 1 rsync ...`, `ssh -n t3 rsync ...` (unquoted), `sudo -n rsync ...`, `timeout -n 5 rsync ...` (all deny on main) and `ionice -n 7 rsync --remove-source-files .../rawdata/ /backup/`, `nice -n 19 rsync --remove-source-files ...` (ask on main), and `nice -n 10 git clean -fdx .../results` went silent. Fix: a new `is_dry_run` reads only the option words AFTER the `rsync` word (or after `clean` for `git clean`); `--dry-run` and an n among the short options count only there.
   - Red: 8 cases (5 deny, 2 ask, 1 git clean) failed before. Green after. Controls that stay quiet: `nice -n 10 rsync -avn --delete`, `rsync -a --delete -n`, `--dry-run` behind a wrapper, `nice -n 10 git clean -n -fd`.
   - Not covered: `rsync -e 'ssh -n' ...` (the quote characters are dropped before the check, so the nested `-n` is read as rsync's).
2. **LOW false alarms: data piped into a runner that has its own script or remote command.** `echo 'rm -rf .../results' | python3 count_words.py` (deny) and `echo 'tw launch x' | ssh t3 'cat >> notes.md'` (gate) were judged as commands. Fix in `hooks/split_segments.awk` and the twin in `hooks/strip_heredocs.awk` (new `reads_code`): a shell always reads its stdin as code; an interpreter does unless a script file argument is present (a lone `-`, or `-c`/`-e`, keeps it code); `ssh` does unless a remote command is present, and a remote command that is itself a shell or interpreter is judged the same way (`ssh h bash`, `ssh h 'bash -s'`, `ssh h python3 -` stay code).
   - Red: 4 cleanup cases + 2 launch cases failed before. Green after. Controls stay judged: `| python3 -`, `| python3`, `| python3 -u -`, `| bash`, `| sh`, `| ssh host`, `| ssh h bash`.
