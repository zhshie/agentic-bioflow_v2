# Fix: in-use-path-spellings

- **Branch**: `fix/gates-audit2-launch` (RED 1ac6ecd, GREEN: the commit carrying this file)
- **Changed**: `hooks/in_use.sh` (two helpers `_abf_rel`, `_abf_text_has_rel`; home spellings in the text normalisation; `$LAB_RUNS_DIR` and relative paths in section 4), `tests/in_use_test.sh` (12 cases, each with a control)
- **Approach** (only widens "in use"; no process added):
  - `$LAB_RUNS_DIR`, `${LAB_RUNS_DIR}`, `$env:LAB_RUNS_DIR`, `%LAB_RUNS_DIR%` are replaced by the hook's `LAB_RUNS_DIR`, or by the deployment's storage_root when the hook has none, and then compared like any path; any other `${LAB_RUNS_DIR...}` form (a default, a trim) counts as naming it. Only when a deployment exists, as before.
  - For each form of the cwd (as given, physical) and each base (root, storage_root, `LAB_RUNS_DIR`, each as named and physical) the relative path between them (`runs3`, `../runs3`, `home/runs3`) is looked for at the start of a word, also after `./`, as a whole path. A single name under 4 characters is ignored, as short absolute paths already were.
  - Home spellings: `$env:USERPROFILE`, `${env:USERPROFILE}`, `%USERPROFILE%`, `$env:HOME`; `~/` at the start of the text or after `=`, `:` or a quote (it was only after a blank); `~<this user>/` (`$USER`, `$LOGNAME` or `$USERNAME`).
- **Red -> green**: 10 cases red on 53853d5 (`$LAB_RUNS_DIR` x3, relative x5, `$env:USERPROFILE`, `x=~/`); two `~<this user>/` cases added with the fix (red on 53853d5 by `scope.sh`: `rm -rf ~acer/runs3/p/results` passed). All 12 green, all 10 controls silent. `x=~/runs3/p/results; rm -rf $x` now reaches the deletion guard, which asks (the target is a variable), not silent.
- **scope.sh** (WSL): every line now deny except `rm -rf --dir=~/runs3/p/results` (in use now; the deletion guard does not read `--dir=` as a target - its business, another branch) and `x=~/...; rm -rf $x` (ask).
- **Cost**: `tests/in_use_speed_test.sh` green (20 not-in-use calls: 0.27-0.57 s vs 1.36-1.46 s baseline); the new work runs only when a deployment exists and nothing earlier decided, and is string matching only.
- **Not changed**: `~otheruser/`, `a/../runs3`, paths assembled at run time.
