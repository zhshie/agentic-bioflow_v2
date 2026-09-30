# Bug Assessment: the plugin-file guard denies reads when the path contains letters like "rm1"

- **Slug**: guard-word-boundary
- **Created**: 2026-09-30
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/40 (CI failed once, passed on rerun)
- **Verdict**: valid
- **Severity**: medium (a false deny, never a false allow; but it makes a safety-net test nondeterministic and can block ordinary reads for some users)

## 給維護者

1. 那支偶發失敗的測試不是亂跳：安全網在判斷「看不懂格式的 shell 工具」時，比對「寫入動作」的字沒有檢查字首，路徑裡只要有 `rm1`、`8ln3`、`Rm2`、`aren5` 這種片段，單純讀檔也會被擋。
2. 測試用的暫存資料夾名稱是隨機的，所以偶爾撞到才失敗。
3. 對使用者：如果帳號或資料夾名稱剛好長這樣（例如 `C:\Users\Arm1`），讀 plugin 的檔案會被擋。只會多擋、不會放行。
4. 修法：比對時加上「字的開頭」條件，並把隨機暫存名稱換成固定會撞到的名稱做成常駐測試。

## Reproduction (deterministic, WSL, main 0e83b31)

With `CLAUDE_PLUGIN_ROOT` set to an existing directory and a tool the guard does not know (`tool_name: SomeShellTool`, field `payload: "Get-Content <root>/hooks/x.sh"`):

| Root | Verdict |
|---|---|
| `/tmp/clean/plugin_root` | allow |
| `/tmp/arm1/plugin_root` | **DENY** |
| `/tmp/tmp.8ln3x/plugin_root` | **DENY** |
| `/tmp/tmp.q7Rm2/plugin_root` | **DENY** |
| `/tmp/tmp.aren5/plugin_root` | **DENY** |

`tests/guard_plugin_files_test.sh` builds its root under `mktemp -d`, whose random suffix sometimes contains such a fragment — hence one failure in CI and a pass on rerun.

## Root Cause (high confidence)

`hooks/guard_plugin_files.sh`, the branch for a shell tool whose input field it cannot read, matches the raw JSON payload with
`(sed -i|tee|cp|mv|rm|…|ln|…|del|…|ren)([^a-z-]|$)|>` (case-insensitive) — a trailing boundary but **no leading one**, so `rm` inside `arm1`, `ln` inside `8ln3`, `ren` inside `aren5` count as write verbs. The Bash and PowerShell branches below it use `(^|[[:space:]]|[;&|(])` as the leading boundary and are not affected.

## Proposed Remediation

- Add the leading boundary to that pattern: `(^|[^a-z0-9_.-])` before the verb group (the payload is JSON, so a verb may follow `"` or a space).
- In `tests/guard_plugin_files_test.sh`, add cases with fixed roots that contain `rm1`, `ln3`, `Rm2`, `ren5` (reads → allow, writes → still deny), so the outcome never depends on `mktemp`.
- Out of scope: the separate question in #15-era design of scanning raw payloads at all.

## Risks

A leading boundary must not let a real write through: `"payload":"rm <root>/x"` (verb after `"`) and `...;rm <root>/x` must still deny — both covered by the new cases.
