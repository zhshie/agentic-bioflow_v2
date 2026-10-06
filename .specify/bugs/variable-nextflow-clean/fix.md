# Fix: variable-nextflow-clean

- **Branch**: `fix/gates-audit2` (RED 298ac9b, GREEN 1cd7634)
- **Changed**: `hooks/confirm_cleanup.sh`; `tests/confirm_cleanup_test.sh` (SN2 section, 6 cases).

## What changed

A segment whose command word is a variable or substitution (`VARCMD`), not a dry run, is read like the nextflow check reads `nextflow`: the first word after the variable that is not an option is the subcommand; `clean` with `-f`/`-force`/`--force` adds the work/ hit, so it asks with the `nextflow clean -f` message and names the unknown command.

## Evidence (WSL)

| Command | Before | After |
|---|---|---|
| `N=nextflow; $N clean -f` | pass | ask |
| `N=nextflow; ${N} clean -f` | pass | ask |
| `N=nextflow; "$N" clean -f` | pass | ask |
| `N=nextflow; $N clean -n -f` | pass | pass |
| `N=nextflow; $N log` | pass | pass |
| `N=nextflow; $N clean` | pass | pass |

RED: 3 failures in `confirm_cleanup_test.sh` (and behind the here-doc). GREEN: all passed.

Note: any variable command with `clean -f` asks (`$MAKE clean -f Makefile` too): the guard cannot tell what the variable holds.
