# Bug Assessment: the safety net can be bypassed (quoted paths, heredocs, relaunch, other shapes)

- **Slug**: safety-net-bypass
- **Created**: 2026-09-29
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/29 (allowlisted host; constitution audit batch A)
- **Verdict**: valid
- **Severity**: critical

## 給維護者

1. 安全網有三個確定的漏洞，都已實測重現：刪除路徑加引號就放行；用 heredoc（在指令裡直接塞一段多行腳本）包起來的送出和刪除都看不到；「重新送出」的腳本不經確認。
2. 另有幾種寫法可能繞過（讀比對規則推論出來的）：PowerShell 的刪除指令、`tw` 把設定參數放在前面、把指令用管線丟給 bash 執行、Seqera 的 MCP 工具直接送出。
3. 修法方向：刪除和送出的判斷改成「看得懂引號」，而不是把引號裡的東西整段丟掉；包 heredoc 的如果是 shell 或 ssh，就照樣檢查裡面的內容；把漏掉的寫法補進比對規則。
4. 會多攔一些原本不攔的指令（例如用變數當刪除路徑時，會從「提醒」升級成「停下來問你」）。代價是偶爾多問一次，換來不會默默刪掉資料。
5. 請你決定下方「待你決定」的兩題，然後我才動手修。

## Report (summarized)

Constitution audit 2026-09-29, batch A: the Safety Net ("never delete rawdata/, results/, analysis/…"; "a launch command is shown in full and waits for explicit confirmation") and invariant 13 ("never silently permissive") are violated by several command shapes the two gates cannot see.

## Symptom

A delete of `results/` or a launch that is expressed in certain ordinary shell shapes passes `hooks/confirm_cleanup.sh` / `hooks/confirm_launch.sh` with no deny, no ask and no warning (exit 0, empty output). Expected: the same verdict as the plain, unquoted form.

## Reproduction (run on `main` 12dda0c, Git Bash, jq present)

1. `rm -rf "/x/proj/results"` → confirm_cleanup: rc 0, no output. The unquoted `rm -rf /x/proj/results` → deny. **Reproduced.**
2. `ssh host bash -s <<'EOF'` / `rm -rf /x/proj/results` / `EOF` → confirm_cleanup: rc 0, no output. **Reproduced.**
3. `bash -s <<'EOF'` / `tw launch foo` / `EOF` → confirm_launch: rc 0, no `ask`. **Reproduced.**
4. `scripts/relaunch_with_override.sh --confirm <run> <proc> <cpus> <mem>` runs `tw runs cancel` + `tw runs relaunch` (`scripts/relaunch_with_override.sh:259,272`); `LAUNCH_TRIGGER_RE` (`hooks/launch_trigger.sh:33`) has no term for it, and `commands/runs.md:191` says it "proceeds without asking first". **Read-verified.**
5. Inferred from the regexes, not yet run: `tw -o json launch …`, `nextflow -bg run …`, `echo 'tw launch …' | bash`, PowerShell `Remove-Item -Recurse …/results`, `rd /s`, `del`, a Seqera MCP launch tool (`hooks/hooks.json:5` matches no `mcp__*` name). The fix's tests will turn each into a reproduction first.

## Suspected Code Paths

- `hooks/confirm_cleanup.sh:194` — `SEGSRC` deletes every quoted string before segmenting; arguments are then taken from `SEGSRC`, so a quoted target disappears. Line 253 already strips one layer of quotes from each argument, showing arguments were meant to keep their quoted content.
- `hooks/strip_heredocs.awk:47` — drops every heredoc body. Its header (lines 21-23) accepts that `bash <<'EOF'` is hidden "because this plugin never launches runs that way"; the model is not bound by that.
- `hooks/launch_trigger.sh:33` — `tw[[:space:]]+launch` requires `launch` right after `tw`; `nextflow[[:space:]]+run` likewise; no `relaunch_with_override.sh`.
- `hooks/launch_trigger.sh:44` — `LAUNCH_NESTED_SHELL_RE` knows `bash -c`, `eval`, `ssh`, `on_site.sh`, but not a pipe into a shell, so `echo '…' | bash` has its quoted command stripped (`:68-69`).
- `hooks/confirm_cleanup.sh:226-228` — delete verbs are only `rm`, `rmdir`, `find -delete`, `rsync --delete`, `shred`; `hooks/hooks.json` sends PowerShell tools here, but no PowerShell delete verb is recognised.
- `hooks/confirm_cleanup.sh:260-261,375` — a delete whose target is a variable only `warn`s (additionalContext); nothing pauses.
- `hooks/hooks.json:5` — PreToolUse matchers cover shell-like tool names only.

## Root Cause Hypothesis

Both gates solved false positives ("a quoted regex or a document that mentions rm/tw launch is not a command") by throwing text away — quoted strings, heredoc bodies — instead of by knowing where that text sits. Whatever was thrown away can carry a real command. Confidence: high (three shapes reproduced, the mechanism is visible in the code).

## Proposed Remediation

**Preferred**:

1. *Quote-aware segmentation (cleanup).* Split segments only on separators outside quotes (mask `;&|` inside quotes instead of deleting the quoted text). Detect the delete verb on a copy with quoted content removed (keeps `grep 'A\|rm '` harmless, the original false positive), but take the arguments from the masked original, so `"…/results"` stays an argument. Same helper used by `launch_trigger.sh` so the two gates cannot drift.
2. *Heredocs.* Keep the body when the heredoc feeds a command interpreter — the text before `<<` has `bash|sh|zsh|dash|ksh|ssh|on_site.sh` (optionally via `sudo`/a path) as its command word; still drop it for `cat > file <<EOF` and similar writers. For `python`/`Rscript`/`perl`/`node` bodies, scan the raw body for delete calls (`rmtree`, `os.remove`, `unlink`, `file.remove`, `unlink(`) and launch verbs, and `ask` on a hit.
3. *Launch shapes.* `tw` followed by any options then `launch` or `runs relaunch`; `nextflow` followed by options then `run`; a pipe into `bash|sh|zsh` counts as a nested shell; `relaunch_with_override.sh … --confirm` is a launch.
4. *PowerShell deletes.* `Remove-Item`, `ri`, `rm`/`del`/`erase`/`rd`/`rmdir` (incl. `/s`) as command words, arguments judged by the same protected-path rules.
5. *MCP.* A PreToolUse entry for `mcp__.*` → `confirm_launch.sh`; for a non-Bash tool whose **name** contains `launch|relaunch|submit`, `ask` with the full call shown.
6. *Unresolved targets.* A delete whose target is a variable becomes `ask` (pause) instead of `warn`, keeping the "expand it and show me" text.
7. *Docs.* `commands/runs.md:191` → the numbers need no question, the relaunch still waits for confirmation; `strip_heredocs.awk` header rewritten to match the new rule.

**Alternatives**:
- Parse the command with a real shell parser (e.g. `bash -n` + `shfmt --to-json`): exact, but adds a dependency to a gate that must never vanish when a helper is missing (the file's own rule, `confirm_cleanup.sh:49-54`). Not preferred.
- Fail closed on any quoted delete target: simplest, but reintroduces the "cries wolf" problem the quote stripping was added to fix.

**Files likely to change**: `hooks/confirm_cleanup.sh`, `hooks/launch_trigger.sh`, `hooks/strip_heredocs.awk`, `hooks/hooks.json`, `hooks/confirm_launch.sh` (tool-name rule), `commands/runs.md`, plus `docs/PITFALLS.md` (new entry: the bypasses and why).

**Tests to add or update**: in `tests/confirm_cleanup_test.sh` — quoted protected target (single, double, with spaces), quoted work/ target → ask, heredoc into `bash`/`ssh` with a protected delete → deny, `cat > f <<EOF` containing `rm -rf results` → allowed (regression for the original false positive), `grep 'A\|rm ' f` → allowed, PowerShell verbs, variable target → ask, python heredoc with `shutil.rmtree` → ask. In `tests/confirm_launch_test.sh` — `tw -o json launch`, `tw --url=x runs relaunch`, `nextflow -bg run`, `echo 'tw launch x' | bash`, heredoc into `bash` with `tw launch`, `relaunch_with_override.sh --confirm`, an `mcp__seqera__launch_*` tool, and the read-only regressions (`grep 'sbatch' f`, `cat > doc <<EOF` mentioning `tw launch`). Each new case is written first and must fail on `main`.

## Risks & Considerations

- More asks: the variable-target change and heredoc bodies will pause some commands that passed before. That is the intended trade (principle 13), but the plugin's own command files must not start tripping it on routine steps — run the manual half of `docs/TESTING.md` after the fix.
- The gates run on every shell call with 5-10 s timeouts (`hooks/hooks.json`); the quote-aware splitter must stay in awk/sed, no new interpreter.
- A heuristic gate is still not a sandbox (`confirm_cleanup.sh:49-50`). The fix closes the known shapes; it does not claim completeness, and PITFALLS says so.
- No behaviour of the plugin's normal flow should change, so no version bump beyond a PATCH.

## Decisions (maintainer, 2026-09-29: 「照建議」)

- Q1 → yes: a delete whose target is a variable becomes `ask`.
- Q2 → not in this fix; moving protected directories goes to batch E (#33).

## Open Questions（已決定，見上）

- **Q1 用變數當刪除路徑時（例如 `rm -rf "$RUN_DIR/work"`），要從「提醒」升級成「停下來問你」嗎？** 建議：要。只提醒的話，模型可以讀完提醒後照樣刪；停下來問，最後是你按確認。代價是清理 work/ 時會多問一次，但那本來就要你說「確認刪除」。
- **Q2 搬走 `results/`、`rawdata/`、`analysis/`（mv）要不要也停下來問？** 建議：這次不做。搬移不是刪除，憲法也沒規定；它排進 E 批，跟其他小修一起處理。
