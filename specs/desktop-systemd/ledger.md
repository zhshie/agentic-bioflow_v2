# desktop-systemd: ledger

## Automated (tests/desktop_systemd_test.sh, shape only)
TC-001..010, 014..017, 021..025, 027, 028, 031..034, 036..038, 040..056 (TC-044, TC-045, TC-054, TC-055 run the existing tests of the same name).
Skipped with a printed reason when the tool is missing: TC-017 (systemd-analyze), TC-037 (powershell.exe, run in default mode only).
Shared with other files: TC-032 also stands on TC-075..077 of tests/hosted_deploy_test.sh.

## Manual (docs/TESTING.md, "desktop-systemd")
TC-011, 012, 013, 018, 019, 020, 026, 029, 030, 035, 039. Not done: they need the maintainer's desktop.

## Could not verify
- That a systemd-started agent really uses the shared SSH socket under ~/.ssh/ with `NoNewPrivileges=true` (TC-020). ssh is not setuid, so it should; not run.
- That `systemd=true` is accepted by the maintainer's WSL version, and whether `loginctl enable-linger` asks for sudo there (TC-013).
- The Windows task itself: `-Apply` and `-Remove` were never run (the hard rule); only the default print-only mode, and only if powershell.exe was reachable.
- That `powershell.exe -File "$(wslpath -w ...)"` (a path under \wsl.localhost) runs the script without a prompt; the doc uses it for step 6.
- Exit status 3 in `RestartPreventExitStatus=2 3`: cli.py names only 2 (EXIT_REFUSED); 3 was in the lead's ruling P3 and is kept.
- The origin/v3 ref moved after the branch was cut; tests compare against the merge-base.

## Fix round after acceptance (rulings D1-D9, plan.md last section)
Each item has a check in tests/desktop_systemd_test.sh (RED commit first, then GREEN):
- D1 mkdir of both folders before the first cp; D2 the real switch-over order (`wsl --shutdown` already stopped them, `pgrep` lists, `pkill` only if something is left, no Ctrl+C advice); D3 "Going back to starting by hand"; D4 several agents (lab1 / gcb example, no hyphen, existing token file); D5 `scripts/preflight.sh` prints the line to paste, you type the OTP (`scripts/reset_master.sh` only closes a master, so it is not named as the way to open one); D6 env files from what the programs read (list below), the `~/.bashrc` comparison, `deploy/station.env.example` comments; D7 `cd <repository-folder>` before every `cp deploy/...`, TESTING TC-018 / TC-030 / TC-013 with exact commands and what to see; D8 no "hidden window" wording; D9 the task action is now `powershell.exe -NoProfile -WindowStyle Hidden -Command "& wsl.exe [-d <distro>] --exec /bin/sleep infinity"`, plus the execution-policy note and "minimise it, do not close it, report it".
- TC-004: changed by ruling D9 (the action is a hidden-window powershell that starts wsl.exe; what finally runs is unchanged). No other assertion was weakened. The TC-013 extraction in the test now reads 12 lines after the label instead of 3, because the manual steps grew.
- Environment variables found: platform services `ABF_PUBLIC_URL`, `ABF_PLATFORM_DB`, `ABF_PLATFORM_TOKENS`, `ABF_PLATFORM_STATE`, `ABF_PLATFORM_UPLOADS`, `ABF_PLATFORM_FIGURES`, `XDG_DATA_HOME` (deadline / clock variables are for tests only). Agent: `PATH`, `JAVA_HOME` (docs), `ABF_STATION_GCP_CREDENTIALS`, `ABF_STATION_UPLOADS`, `ABF_STATION_AWS_CREDENTIALS`, `ABF_STATION_AZURE_CREDENTIALS`, `ABF_STATION_KUBECONFIG`; tuning `ABF_STATION_MIN_REMAINING`, `ABF_STATION_PUT_TIMEOUT`, `ABF_STATION_GCB_SETTLE_SECONDS`, `ABF_STATION_MOUNTS_FILE` (tests). `LAB_SETTINGS_FILE` is not read by the platform services.
- Could not verify: the exact words of the port-in-use error of `abf-platform web` (TESTING says "an error that the address is already in use"); that `pgrep` shows the hand-started processes under their real command lines on the owner's machine; that WSL 0.67.6 is the first version accepting `systemd=true` (from memory); that the agent picks the site connection up without a restart after `scripts/preflight.sh` (inferred from how on_site.sh is called per job).
