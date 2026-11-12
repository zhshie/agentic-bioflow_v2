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
