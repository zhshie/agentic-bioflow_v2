# Plan 112: cleanup gate, writers that still pass after a lost folder (follow-up to #110 / #111)

- **Slug**: 112-cleanup-lost-writers
- **Branch**: `fix/112-cleanup-lost-writers`, base **main** (v2 line; the gate lives in `hooks/confirm_cleanup.sh`)
- **Tier**: A (tightening only). Protected path `hooks/`: built-in `/code-review` before merge.
- **Created**: 2026-10-17 by the developer-agent, from issue #112.

## 給維護者
1. 這是安全網補洞：資料夾「迷路」（`cd -` 之後不確定在哪）時，還有幾種寫檔方式沒被攔下來，這次全部改成先問你。
2. 只會讓關卡變嚴，不會放寬任何現在會問的指令。

## Rule (unchanged from #110)
After the shell's folder is lost, any command that may write to a relative path is asked (or denied where #110 denies), never passed. Unknown means ask (fail closed).

## Changes (each with a red probe first in the existing cleanup gate test file)
1. Redirect targets and writer file operands that start with `-` are file names, not flags (`echo x > -out`, `cat a >| -s1`).
2. Options end at `--`: `tee -- -a s1` writes `-a` and `s1`.
3. A quoted `"~/s1"` or `'~/s1'` is a relative folder named `~`; only an unquoted leading `~` is the home exemption.
4. New writers: `install`, `ln` (any form with a target), `shuf -o`, `split`, `curl -o/--output/-O`, `wget -O/--output-document` (and bare `wget`, which writes to the cwd), `perl -i/-pi`, `awk -i inplace` / `gawk -i inplace`.
5. Process substitution `>(...)` and `<(...)`: the inner command is scanned as a command of its own.
6. `cd /abs/path` clears the lost state only when that folder exists at check time; a missing absolute folder keeps the state lost.
7. Nested and wrapped writers are scanned: subshell `( ... )`, brace group `{ ...; }`, `if/then/else/fi`, `while/for ... do ... done` bodies; `xargs <writer>` and `find ... -exec/-execdir/-ok <writer>` are asked when lost.
8. Consolidate `lost_redirects_blind` and `lost_redirects` into one scanner; duplicate reasons are printed once.

## Not in this PR
- Item 7 of #112 (performance of the large-input filter): fail-closed already; left as is and noted in the ledger.

## Checks
- Every probe in #112 is a test that asks (red on main, green here).
- The #110 replay (`specs/110-cleanup-gate-rest/replay.tsv`) is run and shows 0 transitions from ask/deny to pass versus main. Any pass→ask is listed in the ledger.
- `bash tests/run_all.sh` green on WSL.

## Contract-review rulings (2026-10-17, developer-agent)
- Item 6 flips three existing pins, named here:
  - TC-110-66 (lost folder, then cd to a missing absolute folder, then a delete of `s1`) changes from pass to ask. This is the known gap being closed.
  - TC-078-19 and TC-104-19 (lost folder, then `cd $P`, then a delete) mean "an absolute cd to a real folder recovers". Their `$P` does not exist on the test machine, so the tests are rewritten to use a folder that exists (a `mktemp -d` path). The expectation stays pass. Old, new and reason go in the ledger.
- Item 6 only concerns a state that is already lost. When the folder is known, `cd` to a missing absolute path is unchanged; `confirm_cleanup_shapes.txt:237` stays pass.
- Probes that already ask on main (`echo x > >(tee s1)`, `cat <(tee s1)`, `( cp a s1 )`) are "must keep asking" cases; the ledger records them as "ask on main, ask here", not red to green.
- Absolute targets: `ln`, `split`, `curl -o`, `wget -O`, `install`, `shuf -o` are asked only when a target or output path is relative (the general rule). `wget -O -` and `curl` without `-o/-O` write to stdout and pass. Bare `wget` without `-O` writes into the cwd and is asked. `ln` with one operand creates a link in the cwd and is asked.
- `xargs <writer>` and `find ... -exec/-execdir/-ok <writer>` are asked when lost, even with absolute-looking literal operands, because the appended arguments are unknown (fail closed).
