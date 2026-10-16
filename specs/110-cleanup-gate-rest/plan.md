# Plan 110: the cleanup gate's remaining lost-folder bypasses, and its spurious asks

- **Slug**: 110-cleanup-gate-rest
- **Branch**: `fix/110-cleanup-gate-rest`, base **`main`** (after #109)
- **Created**: 2026-10-17 by the developer-agent
- **Issue**: #110 (from `/code-review` on #109)
- **Tier**: A. Part 1 only tightens. Part 2 corrects asks #109 introduced for commands that neither delete nor overwrite anything (a bug fix of a false alarm, named shape by shape below); nothing that asked or denied on main **before #104** (`94a1c30`) may pass, and no delete or overwrite may pass that asks today.

## 給維護者
1. 補完「不知道在哪個資料夾」時仍會被直接放行的幾種寫法（例如 `false && cd /tmp` 之後刪檔、`tee` 覆寫檔案）。
2. 修掉 #104 帶來的幾種「沒必要的詢問」：引號裡的 `>`、`awk '$1>3'` 這類根本沒寫檔的指令不再跳出來問你。
3. 真正會刪或覆寫的，照樣問或擋。

## Facts (origin/main after #109)
- `hooks/confirm_cleanup.sh:953-966` `cd_uncond` tests every physical line holding the cd with `RE_CD_COND` (`:957`: `[&|(`]` or a keyword `if|while|until|case|for|select|eval|ssh|-c`). `&&` is stripped before the test, so `false && cd /tmp` clears; the whole line is tested, so comments and quoted text count.
- `:1053` an absolute cd clears `CWD_LOST` when `cd_uncond` is true.
- `:968` `RE_REDIR_REL` matches only `>` / `N>`; `:1170` `SEG_NR` keeps quoted text; `:1174-1181` the redirect check runs on `SEG_NR` only when `CWD_LOST=1`.
- `lost_rel` (`:413` area) exempts words with `$`.
- #109 measurement (ledger of specs/104): 95 pass→ask over 1049 inputs, 0 loosened.

## Design decisions (developer-agent)
**Part 1 — tighten (pass → ask only):**
1. **`&&` no longer clears.** A cd clears only when it starts its own top-level command (nothing joined before it by `&&`); `cd /abs && rm …` (cd first) still clears.
2. **Multi-line.** If the command holds a newline and any of `if|for|while|until|case|select`, `()`/`function` definitions, `{` or a heredoc `<<` appears before the cd, the cd does not clear.
3. **Prefixed cd.** `builtin cd`, `command cd`, `VAR=x cd` do not clear (`cd` to a missing absolute folder stays a known gap: the gate cannot test existence without a process).
4. **More redirect forms** under `lost_rel`: `>|`, `>&file`, `>& file` (a file name, not a digit), and a target written with `$`/`$(…)`/backticks (`> "$F"`, `> $(…)`) — the latter always asks when the folder is lost.
5. **More relative writers** under `lost_rel`: `tee FILE…` (without `-a`), `sort -o FILE`, `cp … DEST` (destination), `sed -i … FILE`, `dd of=FILE`.
**Part 2 — false alarms #109 introduced (ask → pass, only these):**
6. The redirect check reads the quote-free copy (the one the TRUNCATE test already uses), so a `>` inside quotes is text: `echo "x>y"`, `awk '$1>3'`, `git log --format='a->b'`.
7. `[[ a > b ]]` / `[ a \> b ]` comparisons are not redirects.
8. `RE_CD_COND` ignores text after an unquoted `#` comment and inside quotes: `cd /tmp # a | b` and `cd /tmp; echo "a&b"` clear as a plain cd would.
**Ruling 2026-10-17 after acceptance round 1:** decision 6's relief applies only when the segment's command word is text-only (`echo`, `printf`, `git`, `grep`/`egrep`/`fgrep`/`rg`, `jq`); interpreters that can write (`awk`, `perl`, `python`, `sed`, `sh -c`, …) keep asking on a quoted `>` (so `awk '$1>3'` still asks — accepted). Decision 7 covers only `[[ … ]]` and an escaped `\>`; a bare `[ a > s1 ]` is a redirect and asks.
**Not changed:** `cd "$dir"` / `cd $(…)` still set the lost state (#104, deliberate); a relative delete through a variable (`d=s1; rm -rf $d`) stays as today (listed as a known gap).

## Changes, in order (red first)
1. Red: add cases in `tests/confirm_cleanup_test.sh` after the #104 block — Part 1 expecting **ask**: `cd $P; cd -; false && cd /tmp; rm -rf s1`; `cd -; [ -d x ] && cd /tmp; rm -rf s1`; multi-line `cd -⏎if true⏎then⏎cd /tmp⏎fi⏎rm -rf s1`; `cd -⏎for i in; do⏎cd /tmp⏎done⏎rm -rf s1`; `cd -; builtin cd /tmp; rm -rf s1`; `cd -; ls >| s1`; `cd -; ls >&s1`; `cd -; echo x > "$F"`; `cd -; echo x | tee s1`; `cd -; sort -o s1 s1`; `cd -; cp /tmp/a s1`; `cd -; sed -i s/a/b/ s1`; `cd -; dd if=/dev/zero of=s1 count=1`. Part 2 expecting **pass** (each asks on main today — record it): `cd -; echo "x>y"`; `cd -; awk '$1>3' /tmp/f`; `cd -; [[ a > b ]]`; `cd -; git log --format='a->b'`; `cd /tmp # a | b⏎rm -rf s1` with cwd known; `cd -; cd /tmp; echo "a&b"; rm -rf s1`. Controls: `cd -; tee -a s1` stays as today; `ls > s1` with a known folder stays pass; `cd /tmp && rm -rf s1` stays pass.
2. Implement 1–8.
3. Replay every input of the test file and both shapes files through `94a1c30` (pre-#104 main), through current `origin/main`, and through the branch. Allowed changes versus current main: pass→ask (Part 1), and ask→pass **only** for inputs that neither delete nor overwrite (Part 2), each listed. Versus `94a1c30`: zero ask→pass and zero deny weakened. Table in the ledger.
4. Note in `specs/104-cleanup-cwd-rest/test-case.md` under TC-104-18: "brace half superseded by the 2026-10-17 ruling (plan Design 2)" — a note only, no expectation edited.
5. WSL `bash tests/run_all.sh` green with jq 1.6 and 1.7.1 first on PATH.

## Not in this PR
- No existence check of a cd target, no alias model, no new process, no change to deadline / jq fast path / other hooks / any deny rule. Archive tools (`tar --remove-files`, `zip -m`, `rclone`) stay a known gap.

## Constitution Check
- Safety Net: Part 1 tightens; Part 2 removes asks only for commands that neither delete nor overwrite, introduced by #109 (shown against pre-#104 main); no deny weakened.
- No new process; timing and process-count tests are the guard.
- Protected path `hooks/`: `/code-review` before merge.
