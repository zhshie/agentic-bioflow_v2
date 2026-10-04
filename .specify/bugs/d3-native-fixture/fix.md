# Fix: d3-native-fixture (#44)

- **Branch**: `fix/44-d3-native` (stacked on `fix/53-scope-shapes`)
- **Changed**: `tests/confirm_launch_test.sh` only. No hook changed.
- **Root cause**: D3 (bare ssh asks) is MSYS-only and reads the real `uname -s`. The test file had a fake `uname` that says MSYS, and no way to say "not MSYS", so natively in Git Bash two cases saw D3 fire: `#29d ssh running a read-only grep of the words` and `the same bare ssh call, but NOT on MSYS`.
- **Change**: at the top of the file a `uname` shim that answers `Linux` for `-s` (and passes everything else to `/usr/bin/uname`) is put first on PATH. The MSYS cases already put their own MSYS shim in front of it, so they are unaffected. A new assertion, `#44 fixture: the default uname -s is not MSYS`, pins the shim.
- **Red -> green (native Git Bash, MINGW64_NT-10.0-26200)**:
  - Before (main + #53 file, `bash tests/confirm_launch_test.sh`, 5m25s): 2 failed, exactly the two in the issue.
  - After: `all passed`, 5m11s. The fixture assertion is red on the commit before the shim (`ce34a0c`) and green after.
  - WSL: `all passed` before and after.
- **Not changed**: the hook; other test files (none contains a bare-ssh case that expects silence).
- **Needs maintainer decision**: none. The native run takes about 5 minutes; `docs/TESTING.md` still sends Windows to WSL for the full suite.
