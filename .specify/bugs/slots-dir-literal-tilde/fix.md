# Fix: slots-dir-literal-tilde (#25)

- **Branch**: `fix/user-folder-audit2`
- **Changed**: `scripts/on_site.sh` (`SLOTS_DIR`), `tests/on_site_parallel_test.sh` (2 cases)
- **Approach**: `SLOTS_DIR` is built from `CP` with a leading `~/` swapped for this shell's `$HOME`. `CP` (handed to ssh / WSL) is unchanged, so PITFALLS 16b still holds.
- **Red -> green**: both new cases failed first (a `~` directory appeared in the caller's cwd; no slot under `$HOME/.ssh`), pass after.
- **Not done**: the stray `~/.ssh/cm-%r-%h-%p.slots/` in the main checkout's root (2026-09-30) is left for the maintainer to delete.
