# Fix: jq-missing-tests (issue #70)

- **Branch**: `fix/70-jq-missing-tests` (plan 9ce250f, gates test b4e893c, RED cc8d1a9, GREEN see `git log`)
- **Changed**: `tests/run_all.sh`; `tests/run_all_test.sh`; new `tests/gates_without_jq_test.sh`; `docs/TESTING.md`; `docs/PITFALLS.md` (38). No file under `hooks/`.

## What changed

- `run_all.sh` probes jq (`jq -c .a` on `{"a":[1]}` gives `[1]`, trailing CR allowed) and python3 (`print(1)`) after file selection and `--list`, before the log directory. A failing tool: one message, exit 3, nothing run. `--allow-missing-tools` runs anyway and the verdict line names the tool. `--allow-msys` skips the python3 probe, not jq. Selecting only `gates_without_jq_test.sh` skips the probe.
- `gates_without_jq_test.sh`: hides jq with `nojq_path` (fails, not skips, if it cannot), builds every input with `printf`, 11 rows from the assessment table.
- `run_all_test.sh`: existing cases that run a file got `--allow-missing-tools`; new cases (TC-015..030, 033, 038) run the stop in a throwaway root of two stub test files, so a regression cannot start the real suite from inside the test.

## Evidence (WSL Ubuntu, no jq)

| Check | Result |
|---|---|
| `run_all_test.sh` at RED (cc8d1a9) | 17 failed (tool check and option absent) |
| `run_all_test.sh` at GREEN | all passed |
| `gates_without_jq_test.sh` on main behaviour | 11/11 pass (the gates hold; intended) |

## Mutation check (TC-014), local, reverted, never committed

`hooks/guard_plugin_files.sh`: the `exit 2` ending `refuse_without_jq` changed to `exit 0`. `bash tests/gates_without_jq_test.sh` then: **2 failed** (TC-010 Edit under the plugin root, TC-011 `sed -i` under it); the other 9 rows stayed ok. After `git checkout hooks` it is 11/11 again and `git diff main -- hooks` is empty.

## Not verified here

WSL has no jq, so the with-jq paths (TC-012 hiding a real jq, TC-032 the four "no jq" sections, the 22 files green) rely on CI.
