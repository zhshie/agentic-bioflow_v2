# Bug Fix: guard-word-boundary

- **Fixed**: 2026-09-30 · **Assessment**: `assessment.md` (maintainer: 「#40 照修」)

| File | Change |
|---|---|
| `hooks/guard_plugin_files.sh` (unknown shell tool branch) | The write-verb pattern gained a leading boundary `(^|[^a-z0-9_.-])`, like the Bash and PowerShell branches already had |
| `tests/guard_plugin_files_test.sh` | Fixed roots under `arm1`, `tmp.8ln3x`, `tmp.q7Rm2`, `tmp.aren5`: a read is allowed, a write denied; plus `ls;rm <root>/…` denied |

Red before (4 reads denied), green after. WSL `tests/run_all.sh` 74/74.
