# Plan 104: the cleanup gate closes the rest of the "unknown working folder" class

- **Slug**: 104-cleanup-cwd-rest
- **Branch**: `fix/104-cleanup-cwd-rest`, base **`main`** (v2 line: Safety Net tightening only)
- **Created**: 2026-10-17 by the developer-agent
- **Issue**: #104 (found by `/code-review` on #103, which fixed #78)
- **Tier**: A (tightening only; nothing that asks or denies today may pass afterwards)

## 給維護者

1. #78 讓「cd -、單獨 cd、popd 之後再刪檔」會先問你；這次把同一類剩下的漏洞補完。
2. 會多問的新情況：`cd ~/某處`、`cd $變數`、`cd $(...)` 之後的相對刪除；被括號或 `&`、`||` 包住的 cd 不再被當成「已知位置」；資料夾不明時用 `>` 覆寫檔案也會問。
3. 原本會擋的仍然擋、原本會問的仍然問；只有「原本放行」的會變成「問」。

## Facts (origin/main after #103, 2026-10-17)

- `hooks/confirm_cleanup.sh:411` `CWD_LOST=0`; `:413-419` `lost_rel` exempts `''|-*|/*|[A-Za-z]:*|'~'*|*'$'*|*'`'*`.
- `:1024` `''|-` sets `VCWD=""; CWD_LOST=1`. `:1025` `'~'*|*'$'*|*'`'*` sets `VCWD=""` only (no `CWD_LOST`).
- `:1026` an absolute target sets `CWD_LOST=0` unconditionally, whatever wraps the cd (subshell `( )`, `&`, `||`, a target that may not exist, `"$OLDPWD"`).
- `:1029` `[[ $SEG =~ $RE_QBS ]]` tests the whole segment, not the cd target.
- `:1043-1045` `popd` sets `CWD_LOST=1` and leaves `VCWD` stale. `:1046-1053` PowerShell location cmdlets: only `pop-location` sets `CWD_LOST`; `sl -`, bare `sl`, quoted backslash targets do not.
- Consumers of `lost_rel`: find roots `:1420` (only when `DESTRUCTIVE=1`), deletes / mv sources `:1552`. The truncate / overwrite branch `:1594-1599` (`TRUNCATE`, `RE_OVERWRITE`) never consults it.
- Pinned **pass** lines this plan flips to **ask** on purpose: `tests/confirm_cleanup_test.sh:831-833` (TC-041 `cd $d`, TC-042 `cd $(...)`; TC-043 alias — see Not in this PR), `:496` "#35 control: cd to a variable is unknown, as on main". Also flipped: `tests/confirm_cleanup_test.sh:855` (TC-078-24, `cd $d`) and `:856` (TC-078-27, `cd ~`), and `tests/confirm_cleanup_shapes.txt:32` (`cd @P/results; cd ~; …`). **This plan supersedes specs/078 TC-078-24 and TC-078-27 ("stays pass")**; every other TC-078-* stays unedited. Re-verify each, and any shapes line the measurement in step 6 finds.
- Must stay green and unedited: every deny and ask in `confirm_cleanup_test.sh`; `confirm_cleanup_behind_heredoc_test.sh`; `confirm_cleanup_candidates_timing_test.sh`; `confirm_cleanup_shapes_main.txt`; the #78 cases TC-078-* except TC-078-24 and TC-078-27 (flipped above); `gate_process_count_test.sh`; `jq_versions_test.sh`.

## Design decisions (developer-agent)

1. **A cd the gate cannot name sets `CWD_LOST`.** `'~'*`, `*'$'*`, `*'`'*` targets (and `$(...)`) set `CWD_LOST=1` as well as `VCWD=""`.
2. **Only an unconditional main-shell absolute cd clears it.** `CWD_LOST=0` only when the segment is a plain `cd`/`pushd`/`Set-Location` at top level: not inside `( )`, not backgrounded with `&`, not on the right of `||`, not inside `if`/`while`/`case`, and the target is not a variable. `cd /abs && …` at top level DOES clear (what follows runs only after a successful cd). **Ruling 2026-10-17 after acceptance round 1:** `{ cd /abs; }` does NOT clear — clearing there turned main's ask into pass (`cd -; { cd /tmp; }; rm -rf s1`, and with `false &&` in front), which this tier forbids; TC-104-18's brace half is superseded. Where the gate already tracks subshell / condition context, reuse it; where it does not, the safe default is: do not clear. Never add a new process.
3. **`lost_rel` covers writers too.** The truncate / overwrite branch asks for a relative target when `lost_rel` is true, same UNRESOLVED wording family. Today `RE_TRUNC` only matches an absolute `> /…` target and `RE_OVERWRITE` only `rawdata`/`results` (`:610-611`), so add recognition of a relative truncating `>` target from any writer (`: > s1`, `echo hi > s1`) and ask for it only under `lost_rel`; a relative `>` with a known folder keeps today's verdict. `tar --remove-files`, `zip -m`, `rclone` relative sources: ask under `lost_rel` if the gate already resolves their paths; otherwise list in the ledger as a known gap (do not invent new parsing).
4. **Tilde.** `lost_rel` exempts only `~` and `~/...`; any other `~word` (e.g. `~s1`, `~user/x`) is treated as relative under `lost_rel`.
5. **Quoted backslash on the target only.** Test the cd target's raw form, not the whole segment. PowerShell (tool `PowerShell`) `sl -`, bare `sl`/`Set-Location`, and a quoted backslash target set `CWD_LOST=1`. Under Bash `sl` is not a built-in and changes nothing.
6. **popd keeps `VCWD` stale but harmless.** Leave `VCWD` as is (clearing it would make some consumers skip judging = pass); decision 3 makes the remaining consumer ask.
7. **One helper.** A single `lost_ask <context> <word>` builds the UNRESOLVED entry for every consumer; the find-root check asks for any find that removes or moves (`-delete`, `-exec rm|mv`, `-execdir`), not only `DESTRUCTIVE=1`.

## Changes, in order (red first)

1. Red: in `tests/confirm_cleanup_test.sh` after the TC-078 block, add cases expecting **ask** (cwd `/tmp`): `cd $P/rawdata; cd ~/x; rm -rf s1`; `cd $HOME/rawdata; rm -rf s1`; `cd $(echo /tmp); rm -rf s1`; `cd $P/rawdata; cd -; (cd /tmp); rm -rf s1`; `cd -; cd /tmp & rm -rf s1`; `cd -; true || cd /tmp; rm -rf s1`; `cd $P/rawdata; cd -; : > s1`; `cd $P/rawdata; cd -; rm -rf ~s1`; `cd $P; sl -; Remove-Item -Recurse x` (PowerShell). The find `-exec mv` shape already asks on main via the mv-source check: keep it as a control, and the ledger says honestly that Design 7 flips no shape today (a refactor guarding against drift). Controls staying **pass**: `cd -; cd /tmp; rm -rf s1`; `cd -; cd /tmp && rm -rf s1`; `echo hi > s1` with a known folder (as main); `cd ~; rm -rf /tmp/s1`; a cd with a later unrelated quoted backslash token (`cd tmp; echo "a\b"; rm -rf x`) stays as main. Run → reds fail; record in the ledger.
2. Implement decisions 1–7 in `hooks/confirm_cleanup.sh`.
3. Flip the pinned pass lines under Facts to ask with the reason "lost cwd now asks (#104)"; change no deny or ask line.
4. Add shapes rows to `tests/confirm_cleanup_shapes.txt` for each new shape.
5. WSL `bash tests/run_all.sh` green with jq 1.6 and 1.7.1 first on PATH; timing test main vs branch ms recorded in the ledger.
6. Measure pass→ask over `confirm_cleanup_shapes.txt` and `confirm_cleanup_shapes_main.txt` (no transcripts); every changed line must be one of the shapes above; count in the ledger.

## Not in this PR

- Aliases (`alias go=cd; go x`, TC-043) stay pass: no alias model.
- No directory-stack model for pushd/popd; no change to `confirm_launch.sh`, `hooks.json`, the jq fast path, the deadline or any deny rule.
- No new parsing for archive tools (`tar --remove-files`, `zip -m`, `rclone`): they pass after `cd -` on main and stay so; the ledger lists them as a known gap for a follow-up issue.

## Constitution Check

- Safety Net: tightens only (pass → ask); no deny or ask weakened; output still `abf_emit`.
- No new process; 20 s deadline and 30 s hook timeout untouched; timing test is the guard.
- Tests red first; flipped pass expectations listed with reasons.
- Protected path (`hooks/`): the developer-agent runs `/code-review` before merge.
