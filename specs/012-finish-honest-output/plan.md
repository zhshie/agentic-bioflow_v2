# Plan 012: build_package.sh says "scaffold, not finished" and names entries it left out

- **Slug**: 012-finish-honest-output
- **Branch**: `fix/012-finish-honest-output`, base **`main`**
- **Created**: 2026-10-17 by the developer-agent
- **Issue**: #12 (part 2 of its suggested fix only; see Not in this PR)
- **Tier**: A (bug fix: the tool's own output misreports a scaffold as finished; the build's behaviour and files are unchanged, only what it prints)

## 給維護者
1. `finish` 組好投稿包時，以前只印「wrote manuscript.qmd」，看起來像完成了；以後會寫明「還有 N 段結果和討論要人來寫，這是草稿骨架」。
2. 分析計畫裡還沒被你接受的項目，會被列出來說「這些沒放進去」，不再默默略過。
3. 不會因此擋下打包（要不要擋，是另一個問題，之後再問你）。

## Facts (origin/main)
- `scripts/build_package.sh:164-176`: Results has one section per *accepted* entry of `analysis.md`; the entries are parsed by an embedded Python (`FIELDS = ("id","question","source","method","why","status")`, `:183`). A zero-entry read already stops the build (issue #5).
- `:355-363`: each Results section is a placeholder comment (`<!-- Describe what this shows, from the data. ... -->`) and the Discussion is a `[GAP: not drafted …]` line.
- `:364`: prints `wrote     submission/manuscript.qmd` with no hint that it is a scaffold.
- Tests: `tests/build_package_test.sh`.

## Design decisions (developer-agent)
1. The success line becomes `wrote     submission/manuscript.qmd (scaffold: N Results section(s) and the Discussion still need prose)`, N counted from the placeholders actually written. When N is 0 and no GAP remains (not possible today, but keep it honest) it prints the plain line.
2. After the manuscript line, if `analysis.md` holds entries whose `status` is not `accepted` (e.g. `proposed`, `revised`, `rejected`, empty), print one line per entry: `left out   <id>: status <status> (not accepted, so not in Results)`. Rejected entries are listed too (the person sees exactly what is out).
3. The README the script writes gets the same "scaffold" sentence near its top.
4. No exit-code change, no refusal, no new hook, no change to which entries go in.
5. zh-TW / en intro texts (`scripts/intro/*/finish.txt`) unchanged unless they quote the old line.

## Changes, in order (red first)
1. Red: in `tests/build_package_test.sh` add cases: (a) two accepted entries → output contains `scaffold: 2 Results section(s) and the Discussion still need prose`; (b) one accepted + one `proposed` + one `rejected` → output lists `left out` for the two with their statuses, Results has exactly one section; (c) all accepted → no `left out` line; (d) README mentions scaffold. Run → red; record in the ledger.
2. Implement in `scripts/build_package.sh`.
3. Update `commands/finish.md` / `docs/FINISH.md` only where they quote the old output line.
4. WSL `bash tests/run_all.sh` green.

## Not in this PR
- Refusing to build, or a `confirm_finish.sh` hook, when entries are unaccepted (issue #12 part 1): that changes what `finish` lets a person do — tier B, asked separately.
- No change to analysis.md parsing, the zero-entry stop, or which files are written.

## Constitution Check
- Safety Net untouched (no gate loosened or added). Honest-output principle served.
- Tests red first; no existing expectation edited except where the old output line is asserted verbatim (list each in the ledger).
