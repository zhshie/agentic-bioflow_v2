# platform-autostart: ledger

Branch `fable/platform-autostart`, base `origin/v3`. Written by the executor.

## What was built

- [x] `deploy/wsl/abf-supervise.sh` (the supervisor), `deploy/wsl/processes.example`, `deploy/wsl/install-autostart.ps1` (UTF-8 with BOM; Windows PowerShell 5.1 reads Chinese text correctly)
- [x] `docs/OPERATIONS.md`: a `###` section 桌機（WSL）上自動啟動 inside section 3 (not a seventh `##`: `tests/operations_doc_test.sh` pins six)
- [x] `docs/TESTING.md`: section "桌機自動啟動 (platform-autostart)" with the eight manual cases TC-013, 014, 015, 034, 047, 055, 077, 114
- [x] `CHANGELOG.md`: one line, second bullet of 3.0.0-dev (the keep-submissions bullet stays first)
- [x] `tests/hosted_deploy_test.sh`: only the `want_list` of TC-069 got the three `deploy/wsl/` files (one line changed; the label still says "six")
- [x] `tests/platform_autostart_test.sh`: the automatic cases, each labelled with its TC id

## Knobs (environment variables, documented in the header of `abf-supervise.sh`)

| Name | Default | Meaning |
|---|---|---|
| `ABF_SUPERVISE_STATE` | `~/.local/state/abf-platform` | state folder (lock, pid, logs, per-process state) |
| `ABF_SUPERVISE_BASE` | 2 | first restart interval, seconds (doubles after each quick failure) |
| `ABF_SUPERVISE_MAX` | 60 | longest interval |
| `ABF_SUPERVISE_STABLE` | 30 | alive this long = healthy, the interval starts over |
| `ABF_SUPERVISE_WAIT` | 10 | on stop, wait this long before SIGKILL |
| `ABF_SUPERVISE_LOGMAX` | 10485760 | rotate a log above this many bytes |
| `ABF_SUPERVISE_TICK` | 5 | how often running logs are checked for rotation, seconds |

Decimals are accepted. The list path is `--list FILE`, default `~/.config/abf-platform/processes`.
Exit codes: 0 ok (also "already running"), 1 `--status` and not running, 2 refused, 129 stopped by SIGHUP (H6; non-zero on purpose). New switch `--stop` (H6). Interval knobs BASE, MAX and TICK must be greater than 0, all knobs must be numbers (H9).

## Design notes that a reviewer may ask about

- Each process has its own runner (a bash subshell with job control on, so the child is its own process group): a stop signal goes to the whole group (`kill -- -pgid`), so grandchildren are not left behind (TC-032). `setsid` is not used, so only `flock` is checked for (TC-012).
- Process logs are opened in append mode by the child; a log that grows while the process runs is rotated by copy-then-empty from the supervisor's tick (P8, TC-092). At start a log is moved aside (`.1`).
- `--status` decides "running" by trying the lock (`flock -n`) on the lock file, so a stale state file after `kill -9` cannot fake it (TC-045). A status probe and a starting supervisor can collide; since the fix round (H7) the starting supervisor waits up to 2 s for the lock before it says "already running".
- Needs bash 5; the script says so and exits 2 otherwise. Durations are measured on `/proc/uptime` (monotonic), not on the wall clock (H9).
- SIGHUP (the window was closed) stops everything cleanly like SIGTERM but exits 129, so the logon task's failure retry brings it back (H6, replaces the earlier "treated like SIGTERM, exit 0").
- The supervisor passes its own environment to the children unchanged and prints none of it (TC-073).
- A supervisor started as a background job from a shell without job control inherits "ignore SIGINT" from that shell and cannot trap it; the Windows task and a terminal do not have that problem. The test starts it with `set -m`.

## Not verified / limits (read before merge)

- **Registering the logon task was never run.** Only the dry run of the installer (no `-Apply`) and a read-only `Get-ScheduledTask` query ran here (powershell.exe was reachable). Whether a normal (non-administrator) account may register a logon-trigger task on the maintainer's machine is unverified; the installer has a 權限不足 branch that stops without elevating (exit 3). The live `-Remove` was not run (it would delete the real task if it exists); only its text and its "本來就沒有這個工作, exit 0" branch are checked statically.
- **TC-015 (no black window).** `wsl.exe` is a console program; the task is registered with the `Hidden` setting, which hides the task in the scheduler but may not hide a console window for a task that runs while the user is logged on. Unverified; TESTING.md step 4 says to report it. Possible follow-ups if a window shows: run the task as a non-interactive principal, or start through a hidden launcher.
- TC-013, 014, 015, 034, 047, 055, 077, 114 are manual (docs/TESTING.md); none was run.
- A `kill -9` of the supervisor no longer leaves a second set (H1; this replaces the earlier P9 "documented only"): a guardian process notices that the supervisor is gone and tells the runners to stop their processes, each runner also checks that the supervisor exists before every restart, and the lock stays held by the runners until the last one is gone. So after a kill -9 the platform is down for a few seconds and a new supervisor started in that window waits (up to 2 s) or says "already running"; the logon task's retry (one minute) then starts it.
- A process that `setsid`-detaches itself, and `wsl --shutdown`, are outside the fix round (the plan says so).
- The default PATH of a login task is short: list lines should use absolute paths (documented; `--check` reports a program it cannot find).
- TC-111, 112 and 123 compare against `origin/v3` and only run on the branch `fable/platform-autostart` (they would go red on any later work on `v3`); elsewhere they print `skip`.
- Constitution I.2 (P1): the lead's reading is that the supervisor is not a "monitoring daemon" (it watches only the processes it started; no run state, no `tw`, no Nextflow). The maintainer is asked to confirm in the morning note; if he disagrees this case stops and goes through the amendment procedure.

## Fix round (the lead's rulings H1-H10 after acceptance and the adversarial review)

Each item was written as a failing test first (commit `RED:`), then fixed (`GREEN:`). Labels are in `tests/platform_autostart_test.sh`; TC ids of the contract were not reused. The acceptance notes: TC-062 now has its own test (`case_t062`); TC-111, 112 and 123 are marked above as valid before merge only; the label text of `hosted_deploy_test.sh` TC-069 was changed by the lead's note to the real number of files (see the diff of that file, not touched again here).

| Ruling | Test label(s) | Where in `deploy/wsl/abf-supervise.sh` |
|---|---|---|
| H1 kill -9 leaves no second set | `H1` (cases h1a, h1b) | `start_guardian`, `runner` (checks `sup_alive` before each start; keeps fd 9, closes it only for the process), lock held until the last runner is gone |
| H2 closed stdout | `H2` | the start-up message is printed before any runner starts, under `trap '' PIPE` |
| H3 token shapes, no echo | `H3` (h3, h3ok, h3msg) | `secret_line`, `secret_cmd`, messages in `load_list` |
| H4 `VAR=value`, one program | `H4` | `split_words`, `program_of`, `load_list`; `runner` runs `exec /usr/bin/env <line>` for a leading assignment |
| H5 stop races | `H5` (h5a, h5b; deterministic: a fake `stat` / `mv` on PATH sends the TERM at the exact moment) | `runner`: `stopping` re-checked after the process start and before/after the sleep; `on_term` also kills the sleep |
| H6 SIGHUP, `--stop` | `H6` | `on_hup` (exit 129), `--stop` mode |
| H7 status probe | `H7` (h7, h7b) | `flock -w 2` |
| H8 child environment | `H8` | `( cd "$HOME"; umask "$ORIG_UMASK"; exec bash -l -c ... )` |
| H9 BOM, /mnt, dead runner, clock, knobs, rotation, installer | `H9` (h9bom, h9mnt, h9runner, h9clock, h9knobs, h9cp), static check of `install-autostart.ps1` | `on_windows_fs`, `pid_alive` + take-over in the main loop, `now_us` on `/proc/uptime`, `fmt_us`, knob loop, `rotate_live`; `Invoke-Apply` runs `wsl.exe ... --exec test -x` first |
| H10 crash loop visible | `H10` | `fails` in the state file, the 警告 line at every 5th failure, `--status` |
| (docs) | `H4/H6/H8/H9/H10 the section says...`, `H6/H8 docs/TESTING.md` | `docs/OPERATIONS.md`, `docs/TESTING.md` |

### Assertions changed by a ruling (everything else in the file is as the contract pinned it)

- **changed by ruling H3:** `TOKV` (the fake token that TC-063, 066, 067 use) is now `abf_` + 43 characters instead of + 30, the real shape (the old shape `abf_` + 20 letters or digits is no longer what the check looks for).
- **changed by ruling H7:** TC-054 no longer sleeps 1 s and then expects one copy to be gone: it waits (up to 8 s) until the loser has printed "already running", because the loser now waits up to 2 s for the lock.
- **changed by ruling H10:** TC-121 expects the state-file keys `fails last_rc pid restarts running started` (a `fails` key was added).
- **changed by the lead's acceptance note:** the label of `hosted_deploy_test.sh` TC-069 says `ten` planned files (it said `six`; it lists 10 files with the three of `deploy/wsl/`), and the TC-123 check of this file accepts exactly that second changed line (2 removed / 2 added lines instead of 1 / 1, the added ones being the list and the label).
- No test was deleted, skipped or loosened otherwise. The SIGHUP exit code was not pinned by any existing assertion.
- Not an assertion, but a decision for the lead: the whole-script TC-043 bound (`count_procs ... -le 12`) was kept as it was; a first design with one watcher per runner went over it and was replaced by a single guardian.

### Limits of the fix round (not verified, or verified only partly)

- **A clock stepping backwards** cannot be provoked here without root: it is covered by a unit check of `fmt_us` (a negative duration prints `0`) and a static check that durations use `/proc/uptime`; the live step was not run.
- **`install-autostart.ps1 -Apply` check** (the script must exist and be executable in the distro) is checked statically only; `-Apply` was never run here (it would register a real task).
- **The `/mnt/` refusal** is tested only when a writable folder under `/mnt/c` exists (it does in this WSL; on CI the case prints `skip`). Refusal is by filesystem type (9p/drvfs/ntfs/vfat/...), so an ext4 mount under `/mnt/` is not refused.
- The login shell (H8) makes a process start through `bash -l`; a `~/.profile` that prints or waits for input would slow or break a start. Nothing was measured on the maintainer's real profile.
- After a `kill -9` the stop of every process takes up to about one second plus the process's own stop time; a supervisor started inside that window waits at most 2 s and otherwise says "already running" (exit 0) - then the logon task's retry (not an exit code) is not triggered. Recovery in that case is the next logon or a manual start.
- **CI.** The first CI run of this branch (before the fix round) already ended with `TIMEOUT platform_autostart_test.sh` (run_all.sh's 300 s limit) although the file takes 15-60 s here, so something hangs on the GitHub runner that does not here (the cause was not known when this was written). `case_*` functions now run under a per-case limit (`PA_CASE_TIMEOUT`, default 120 s): a case that does not finish fails by name and prints DIAG lines (its leftover processes and the tail of its `supervise.log`) instead of hanging the file.
- Pid reuse: a runner that died and was replaced stops the old process group only when the pid in its state file is still a live group leader; nothing else is signalled.

## Manual results (to be filled in by the maintainer)

| TC | date | pass / fail | note |
|---|---|---|---|
| TC-114 | | | |
| TC-014 | | | |
| TC-013 | | | |
| TC-015 | | | |
| TC-034 | | | |
| TC-047 | | | |
| TC-055 | | | |
| TC-077 | | | |
