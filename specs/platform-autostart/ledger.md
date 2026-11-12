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
Exit codes: 0 ok (also "already running"), 1 `--status` and not running, 2 refused.

## Design notes that a reviewer may ask about

- Each process has its own runner (a bash subshell with job control on, so the child is its own process group): a stop signal goes to the whole group (`kill -- -pgid`), so grandchildren are not left behind (TC-032). `setsid` is not used, so only `flock` is checked for (TC-012).
- Process logs are opened in append mode by the child; a log that grows while the process runs is rotated by copy-then-empty from the supervisor's tick (P8, TC-092). At start a log is moved aside (`.1`).
- `--status` decides "running" by trying the lock (`flock -n`) on the lock file, so a stale state file after `kill -9` cannot fake it (TC-045). A status probe and a starting supervisor could in theory collide for a few microseconds; the supervisor's real second-copy refusal is unaffected.
- Needs bash 5 (`EPOCHREALTIME`); the script says so and exits 2 otherwise.
- SIGHUP is treated like SIGTERM and SIGINT (closing the terminal of a manual run stops it cleanly).
- The supervisor passes its own environment to the children unchanged and prints none of it (TC-073).
- A supervisor started as a background job from a shell without job control inherits "ignore SIGINT" from that shell and cannot trap it; the Windows task and a terminal do not have that problem. The test starts it with `set -m`.

## Not verified / limits (read before merge)

- **Registering the logon task was never run.** Only the dry run of the installer (no `-Apply`) and a read-only `Get-ScheduledTask` query ran here (powershell.exe was reachable). Whether a normal (non-administrator) account may register a logon-trigger task on the maintainer's machine is unverified; the installer has a 權限不足 branch that stops without elevating (exit 3). The live `-Remove` was not run (it would delete the real task if it exists); only its text and its "本來就沒有這個工作, exit 0" branch are checked statically.
- **TC-015 (no black window).** `wsl.exe` is a console program; the task is registered with the `Hidden` setting, which hides the task in the scheduler but may not hide a console window for a task that runs while the user is logged on. Unverified; TESTING.md step 4 says to report it. Possible follow-ups if a window shows: run the task as a non-interactive principal, or start through a hidden launcher.
- TC-013, 014, 015, 034, 047, 055, 077, 114 are manual (docs/TESTING.md); none was run.
- A `kill -9` of the supervisor leaves its children running (P9); documented, no extra mechanism.
- The default PATH of a login task is short: list lines should use absolute paths (documented; `--check` reports a program it cannot find).
- TC-111, 112 and 123 compare against `origin/v3` and only run on the branch `fable/platform-autostart` (they would go red on any later work on `v3`); elsewhere they print `skip`.
- Constitution I.2 (P1): the lead's reading is that the supervisor is not a "monitoring daemon" (it watches only the processes it started; no run state, no `tw`, no Nextflow). The maintainer is asked to confirm in the morning note; if he disagrees this case stops and goes through the amendment procedure.

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
