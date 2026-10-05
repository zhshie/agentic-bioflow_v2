# Bug Assessment: a jq that answers wrongly turns the gates and the overview hook silently permissive

- **Slug**: jq-broken-gates
- **Created**: 2026-10-05
- **Source**: fresh audit against constitution 2.0.0, invariant 13 ("with `jq` missing or broken, the gates refuse what they cannot rule out from the raw text and name the fix")
- **Verdict**: valid
- **Severity**: high for the `{}` case (a launch the gate recognised goes through: the gate prints `{}`, an empty verdict), medium otherwise

## 給維護者

1. 關卡最依賴的工具是 `jq`。jq「不存在」或「一跑就失敗」時，關卡會改用純文字的保守判斷：看起來像送出／刪除／寫入 plugin 的就擋下並說明怎麼裝 jq，其餘放行——這部分本來就有測試。
2. 沒處理到的是 jq「在、會回 0、但答錯」：例如回一個空的 `{}`、或回一段亂碼。今天：
   - 啟動關卡收到 `{}` 會把 `{}` 當成自己的判決印出去——等於沒有判決，`tw launch` 直接放行；收到亂碼則印出固定的「請人工確認」，但沒說是 jq 壞了。
   - 外掛檔守衛、導覽關卡收到 `{}` 或亂碼會直接放行，不出聲。
   - `plugin_intro.sh` 的「jq 能不能用」檢查只看 jq 有沒有回 0，所以不會警告；它還會把 jq 的亂碼當成輸出送給 Claude Code。
3. 修法：讀 jq 的回答時檢查形狀（每個欄位後面都要有分隔字元），對不上就當成 jq 不能用；「jq 能不能用」的檢查改成要它真的算對一個小題目（容忍 Windows jq.exe 的 CRLF）。之後走既有的「沒有 jq」路線：擋下看得出來的、說明怎麼修。

## Reproduction (WSL, HEAD ed6fdfd; a `jq` first on PATH that prints `{}` and exits 0)

| hook | call | Today | Should be |
|---|---|---|---|
| confirm_launch.sh | `tw launch nf-core/rnaseq` | prints `{}`, exit 0 (proceeds) | exit 2, BLOCKED, install line |
| confirm_walkthrough.sh | Write `/r/samplesheet.csv` | silent, exit 0 | exit 2, BLOCKED |
| guard_plugin_files.sh | Write into `$CLAUDE_PLUGIN_ROOT/hooks/` | silent, exit 0 | exit 2, BLOCKED |
| plugin_intro.sh | `/agentic-bioflow:setup` | `{}` (no warning) | the jq warning, marker written |

With a jq that prints text and exits 0 the launch gate prints its fixed "could not build its message" ask instead of the jq refusal; the other three are as above. With a jq that exits non-zero on everything the gates already refuse (tests exist); `plugin_intro.sh` warns.

## Root Cause (high confidence)

- `confirm_launch.sh`, `confirm_walkthrough.sh`, `guard_plugin_files.sh`: the one-call fast path (#34) is trusted whenever jq exits 0 with non-empty output; the fields are then read with `read -d $'\037'` without checking that the separators were there, so `{}` becomes the tool name and the command is empty.
- All four: the "can jq run" probe is `printf '{}' | jq -e .`, which a jq answering `{}` (or anything, exit 0) passes.

## Scope / fix direction

- Fast path: trusted only when every field's separator was read; otherwise the probe decides, as for a jq that failed.
- The probe asks jq to compute something with a known answer (`.a` of `{"a":[1]}` is `[1]`, a trailing CR from jq.exe allowed); wrong answer = jq cannot be used = the existing no-jq path.
- `plugin_intro.sh`: the same probe before the overview; the no-jq branch already marks the session and warns.
- Tests: `tests/gate_output_failclosed_test.sh`, a separate block: three broken jqs (fails, answers `{}`, answers text) x the four hooks, a guarded call (refused, the fix named; for plugin_intro.sh the warning and the marker) and a call each does not guard (quiet).

## NOT changed

- `hooks/confirm_cleanup.sh` (other branch) has the same fast-path shape; reported, not edited here.
- A jq that answers the probe right and the real question wrong (implausible); the c018c15 minimal ask still covers a jq that cannot build the output.
