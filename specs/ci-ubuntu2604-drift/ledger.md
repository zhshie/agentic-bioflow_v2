# CI drift on ubuntu-latest = Ubuntu 26.04 / python 3.14.4

Green on 2026-11-11 (ubuntu-24.04, python 3.12.3); red once the image became 26.04. Tests only; nothing under
`.github/`, `hooks/`, `platform/abf_station/`.

| # | Failing test | Cause | Change |
|---|---|---|---|
| 1 | `test_station_e2e.py::test_tc082_...` | python 3.14 `shutil` does `import _winapi` when `sys.platform == 'win32'` | the subprocess prelude pre-seeds a stub `_winapi` in `sys.modules` |
| 2 | `test_cli_snapshots.py::test_help_snapshots[cli_help_top]` | 3.14 argparse keeps the trailing `...` on the usage line | `assert_golden` compares after joining a line that is only `...` to the line before (`_unwrap_ellipsis`); every other difference still fails |
| 3 | `tests/init_workspace_test.sh` control case | Ubuntu 26.04 ships uutils coreutils; its `mkdir` error lacks GNU's "cannot create directory" | the case now expects the deployment's own `/proc/no-such-run-area` path (shows the unisolated call reached the deployment), not mkdir's wording |
| 4a | `test_azure_ce.py::test_a_missing_credential_file_says_where_to_put_it` | detail clipped at 300 chars; retry's temp base is longer, "chmod 600" falls off | test builds its fixture on a short fixed folder (`short_tmp` in `conftest.py`, helper `_make_ip`) |
| 4b | `test_station_e2e.py::test_tc045_tc046_tc087_...` | ssh ControlPath under the temp base exceeds the ~104-char socket limit | test uses `short_tmp` |

Reproduced: 1, 2 on uv python 3.14.8 venv (throwaway, /tmp/v314); 4 with `--basetemp` of ~150 chars; 3 in a real Ubuntu 26.04.1
rootfs imported into WSL (docker daemon was not running). Each passes after the change on 3.14 and on the default venv (3.10);
item 3 also on Ubuntu 22.04.

Unverified: the full suite on 26.04 (the PR's CI is the verdict); python 3.14.8 locally vs 3.14.4 on the runner.
