# Plan 012: build_package.sh says "scaffold, not finished" and names entries it left out

- **Slug**: 012-finish-honest-output
- **Branch**: `fix/012-finish-honest-output`, base **`main`**
- **Created**: 2026-10-17 by the developer-agent
- **Issue**: #12 (part 2 of its suggested fix only; see Not in this PR)
- **Tier**: A (bug fix: the tool's own output misreports a scaffold as finished; the build's behaviour and files are unchanged, only what it prints)

## 給維護者
1. `finish` 組好投稿包時，以前只印「wrote manuscript.qmd」，看起來像完成了；以後會寫明「還有 N 段結果和討論要人來寫，這是草稿骨架」。
2. 分析計畫裡還沒被你接受的項目，現在其實也會被放進結果；以後會逐項列出「這些還沒接受，送出前要接受或拿掉」。
3. 不會因此擋下打包（要不要擋，是另一個問題，之後再問你）。

## Facts (origin/main)
- **Corrected after contract review (2026-10-17):** the comments at `:26`, `:71`, `:164` say "one section per accepted entry", but the embedded Python does **not** filter on `status`: every entry, accepted or not, gets a Results section. Filtering would change the deliverable (and could trip the zero-entry stop), so it is not done here; it is the tier-B question already listed under Not in this PR.
- `scripts/build_package.sh:164-176`: Results sections are built from `analysis.md` entries; the entries are parsed by an embedded Python (`FIELDS = ("id","question","source","method","why","status")`, `:183`). A zero-entry read already stops the build (issue #5).
- `:355-363`: each Results section is a placeholder comment (`<!-- Describe what this shows, from the data. ... -->`) and the Discussion is a `[GAP: not drafted …]` line.
- `:364`: prints `wrote     submission/manuscript.qmd` with no hint that it is a scaffold.
- Tests: `tests/build_package_test.sh`.

## Design decisions (developer-agent)
1. The success line becomes `wrote     submission/manuscript.qmd (scaffold: N Results section(s) and the Discussion still need prose)`, N counted from the placeholders actually written. When N is 0 and no GAP remains (not possible today, but keep it honest) it prints the plain line.
2. After the manuscript line, for each entry whose `status` (trimmed, case-insensitive) is not `accepted` — `proposed`, `revised`, `rejected`, or empty — print one line: `not accepted <id>: status <status or "(none)"> - still in Results; accept it in analysis.md or remove it before submitting`. This is what the build really does today (it includes them); the line makes it visible.
3. The README the script writes gets the same scaffold sentence, with N, before its `## How to reproduce the runs` heading. (So README.md's text changes; which files are written does not.)
4. N counts only the Results placeholders (one per entry section); a plan row without an id (its own GAP) is not counted.
5. The three source comments that claim "accepted only" (`:26`, `:71`, `:164`) are corrected to say every parsed entry gets a section.
6. No exit-code change, no refusal, no new hook, no change to which entries go in.
7. zh-TW / en intro texts (`scripts/intro/*/finish.txt`) unchanged unless they quote the old line.

**Round 3 rulings (2026-10-17, after contract review):**
- Facts correction: the per-entry Results placeholder on main is the visible line `[GAP: Results for '<id>' not written yet - …]` (~`:300-302`, after #32), not an HTML comment. N counts those lines.
- The older block format (`parse_kv_blocks`, ~`:150-160`) does not return `status` today. It is extended to also return `status` when a block has a `status:` line — the only parser change; which entries are parsed and which sections are written stay the same. Without it, an older-format plan with `status: accepted` would be falsely reported as `not accepted … (none)`. Add a test with the older format + `status: accepted` (no `not accepted` line) and + `status: proposed` (listed).
- N = 0 with entries present (only id-less rows) prints `scaffold: 0 Results section(s) and the Discussion still need prose`.
- Rows without an id get no `not accepted` line (they already have their own GAP).
- The status is printed as written (trimmed); the accepted test is case-insensitive.

## Changes, in order (red first)
1. Red: in `tests/build_package_test.sh` add cases: (a) two accepted entries → output contains `scaffold: 2 Results section(s) and the Discussion still need prose`; (b) one accepted + one `proposed` + one `rejected` + one with no status → output has a `not accepted` line for the three (the empty one shows `(none)`), Results still has four sections, N is 4; (b2) `Accepted` / ` accepted ` count as accepted; (c) all accepted → no `not accepted` line; (d) README mentions scaffold. Run → red; record in the ledger.
2. Implement in `scripts/build_package.sh`.
3. Update `commands/finish.md` / `docs/FINISH.md` only where they quote the old output line.
4. WSL `bash tests/run_all.sh` green.

## Not in this PR
- Refusing to build, or a `confirm_finish.sh` hook, when entries are unaccepted (issue #12 part 1): that changes what `finish` lets a person do — tier B, asked separately.
- No change to analysis.md parsing, the zero-entry stop, or which files are written.

## Constitution Check
- Safety Net untouched (no gate loosened or added). Honest-output principle served.
- Tests red first; no existing expectation edited except where the old output line is asserted verbatim (list each in the ledger).
