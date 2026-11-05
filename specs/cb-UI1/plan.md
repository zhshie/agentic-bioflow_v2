# cb-UI1: ui_check.py can use a Chrome that is already installed

Source: cloud-burn tasks.json UI1

## Goal
`scripts/dev/ui_check.py` calls `p.chromium.launch()`, which needs a Playwright-downloaded Chromium.
Cloud VMs and other offline boxes have Chrome at `$CHROME_PATH` but cannot reach the Playwright CDN.
Add `--chromium-path` (default `$CHROME_PATH` when set), passed to Playwright as `executable_path`.
Exit code 3 ("nothing was checked: playwright / axe / Chromium missing") is unchanged when nothing usable exists.

## Files
- `scripts/dev/ui_check.py`
- `tests/ui_check_script_test.sh`

## Approach
- New option `--chromium-path`; default `os.environ.get("CHROME_PATH")` (empty string counts as unset).
- `run_checks`: `launch(executable_path=path)` only when a path is set; with none, `launch()` exactly as before.
- A path that is not a file: one line on stdout and exit 3 (nothing usable), before Playwright is started.
- Header docstring documents the flag.

## RED tests (no browser needed)
The test puts a stub `playwright` / `axe_playwright_python` package on PYTHONPATH whose
`chromium.launch(**kw)` records its kwargs to a file and raises. Cases:
1. `--help` lists `--chromium-path`.
2. `--chromium-path <file>` reaches launch as `executable_path`.
3. `$CHROME_PATH` is the default.
4. The flag beats `$CHROME_PATH`.
5. No flag and no env: launch gets no `executable_path` (behaviour unchanged).
6. A path that does not exist exits 3, one line, launch never called.
7. A launch failure still exits 3.

## Done criteria
New test cases fail on base, pass after; `check_scope.sh` clean; full `tests/run_all.sh` green.

## Environment facts
Playwright is not installed here; the stub stands in. `$CHROME_PATH=/usr/bin/google-chrome` on the cloud VM.

## Not doing
No real browser run, no change to pages/widths/axe logic, no other files.
