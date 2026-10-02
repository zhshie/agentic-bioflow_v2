# Bug Assessment: confirm_launch_test.sh fails 2 D3 assertions when run natively in Git Bash

- **Slug**: d3-native-fixture
- **Created**: 2026-10-02
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/44
- **Verdict**: valid, a test-fixture defect (the hook is right)
- **Severity**: low (WSL/CI are green), but the native run is the only check of the D3 rule from the platform it targets

## 給維護者

1. 兩個失敗不是 hook 的錯，是測試的前提不成立：D3（直接 ssh 的提醒）只在 MSYS（Git Bash）上啟用，hook 靠真正的 `uname -s` 判斷。
2. 測試檔在 Git Bash 裡跑時，真的 `uname -s` 就是 MSYS，所以「不在 MSYS 上」那一格、以及「ssh 去 grep 這幾個字」那一格，hook 都照規矩問了。
3. 修法只動測試：檔案開頭放一支假的 `uname`（回 Linux）到 PATH 最前面；要測 MSYS 的案例本來就會自己再放一支假的 MSYS `uname` 蓋過去。Hook 完全不動。

## Reproduction (native Git Bash, `bash tests/confirm_launch_test.sh`, ~25 min on this laptop)

```
#29d ssh running a read-only grep of the words           FAIL: expected pass, got gate
the same bare ssh call, but NOT on MSYS: not flagged (D3 is MSYS-only) FAIL: D3 fired off MSYS <<{
```

`uname -s` here prints `MINGW64_NT-10.0-26200`. `hooks/confirm_launch.sh` D3 branch: `case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*)`.

## Root cause (confirmed)

Both failing cases invoke the hook with the real PATH. The only fake `uname` in the file (MSYSBIN) makes the hook *think it is on MSYS*; nothing makes it think it is *not*. On Linux/macOS the real `uname` supplies that for free, in Git Bash it supplies the opposite. Case 1 (`ssh h 'grep ...'`, expected pass) and case 2 (the explicit NOT-on-MSYS case) are the only two with a bare `ssh` and no MSYS stub that expect no ask.

## Fix direction / scope

- `tests/confirm_launch_test.sh`: a `Linux` `uname -s` shim exported on PATH at the top; a self-check assertion that the default `uname -s` is not MSYS (red natively before the shim, so removing the shim later cannot go unnoticed).
- NOT changed: any hook. D3's MSYS-only rule is as designed.
- Other test files that run hooks without a fake `uname` may have the same shape natively; not checked here (they do not contain a bare-ssh case expecting silence).

## Test cases

1. `#29d ssh running a read-only grep of the words` passes natively.
2. `the same bare ssh call, but NOT on MSYS` passes natively.
3. New: `#44 fixture: the default uname -s is not MSYS` (fails natively without the shim; passes on Linux either way).
