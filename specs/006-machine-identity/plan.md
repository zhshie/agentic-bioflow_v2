# Implementation Plan: machine identity (006, #49)

**Branch**: `006-machine-identity` | **Spec**: `spec.md` | **Test cases**: `test-case.md`, approved on 2026-10-02

## Design (all in `scripts/settings.sh`)

- `MACHINE_ID_FILE="${XDG_CONFIG_HOME:-${HOME:-}/.config}/agentic-bioflow/machine-id"`, beside `ROOT_POINTER`.
- `legacy_machine_id()` is today's `machine_id()` body, renamed: hostname plus `uname -s`, sanitised.
- `stored_machine_id()` reads the first line of the ID file. It returns the value only if it matches `^[A-Za-z0-9._-]{1,64}$`; otherwise nothing (FR-005).
- `machine_id()` returns the stored id if there is one, else `legacy_machine_id`. This is read-only and never creates anything (FR-002).
- `legacy_machine_file <machines-dir>`:
  - Prefer an exact `<legacy_machine_id>.yaml`.
  - Otherwise, only when `uname -s` is `MINGW*`, `MSYS*` or `CYGWIN*`, use the newest `<host>-<prefix>_NT-*.yaml`, where `<prefix>` is the part of `uname -s` before `_NT` (FR-003). Pick "newest" with `ls -t`, already used in this repo; check that `tests/portable_userland.sh` allows it.
- Resolving `MACHINE_SETTINGS_FILE` (the two places at lines ~98 and ~112, and `migrate_legacy` ~767):
  - If there is a stored id, use `machines/<id>.yaml`.
  - Otherwise use `legacy_machine_file` if one exists, or `machines/<legacy_machine_id>.yaml` as a not-yet-existing path.
- `ensure_machine_id`:
  - Called by `set_setting` before it writes a machine key, and by `migrate_legacy`.
  - If there is no valid stored id, generate `<sanitised hostname>-<8 hex>`. The hex comes from `od -An -tx1 -N4 /dev/urandom | tr -d ' \n'`, falling back to `printf '%04x%04x' $RANDOM $RANDOM`.
  - It writes the file with `mkdir -p`, failing loudly if it cannot (FR-005, TC-012).
  - It renames the legacy machine file found above to `<id>.yaml` if one exists (FR-004).
  - It re-points `MACHINE_SETTINGS_FILE`.
  - If the stored id was invalid, it says so on stderr.
- `setup_proof.sh`: no change. It uses `MACHINE_SETTINGS_FILE` and `set_setting`. TC-010 proves two HOMEs end up in two files.
- `docs/SETTINGS.md`: identity section and migration note. Also check `where.sh` and `--summary`, which print `MACHINE_SETTINGS_FILE` (TC-013).

## Tests

New `tests/machine_identity_test.sh`, TC-001 to TC-012. A fake `uname` on PATH prints the `-n`/`-s` values from env vars. Isolate with `env -u XDG_CONFIG_HOME`, as the other settings tests do. TC-013 is a doc grep plus a `where.sh` check. TC-014 is the full suite.

## Complexity and risk

- **Small to medium.** Only one file, but every script sources it.
- **Risk: a mistake in resolving the path hides every machine key**, including `tw_bin`, on real machines. Mitigations: the legacy fallback is read-only, the existing tests for `tw_bin`/`site_bridge` routing keep running, and acceptance probes the upgrade path from today's layout.
- **Risk: the rename on first write.** If the machine dies mid-rename, a single `mv` is atomic on one filesystem.
