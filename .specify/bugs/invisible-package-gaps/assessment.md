# Bug Assessment: Gaps in the paper package are invisible to the reader

- **Slug**: invisible-package-gaps
- **Created**: 2026-09-29
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/32 (constitution audit batch D)
- **Verdict**: valid
- **Severity**: high (item 1; item 2 medium, item 3 low)
- **Drafted by**: a read-only Sonnet reviewer; spot-checked by developer (build_package.sh:250, methods_text.py:319,342 confirmed on main 12dda0c)

## 給維護者

1. 論文包裡「這裡缺東西」的提示寫成網頁註解，轉成 Word 一定被濾掉，轉成網頁也只留在原始碼、畫面看不到——讀者永遠看不到缺口。
2. 沒填到的欄位會被默默刪掉，不留任何痕跡；方法段也沒寫出每句話是從哪個檔案來的（唯一寫出來源的說明也包在會消失的註解裡）。
3. 圖的編號比對有錯：`fig1` 可能誤抓到 `fig10.png`，而且不會提醒。
4. 現有測試只檢查原始碼裡有沒有那串字，從沒真的轉檔驗證過；本機和 CI 都沒有轉檔工具（pandoc/quarto），所以「會消失」是依 pandoc 公開行為推論的，修完要在有 quarto 的電腦（Positron 那台）手動轉一次確認。
5. 修法：統一改成畫面上看得見的 `[GAP: …]` 標記。

## Symptom

The package `/finish` produces (`submission/manuscript.qmd`, rendered by Quarto/Pandoc to docx and html) must make every unresolved gap visible (constitution invariant 9). Several gap markers are HTML comments, which the docx writer drops and the html writer keeps only in page source.

## Reproduction

1. `scripts/build_package.sh <project-dir>` on a project with a plan entry whose id has no figure, an unclaimed figure, a run with no MultiQC report, and figure ids `fig1`/`fig10`.
2. `submission/manuscript.qmd` contains the gap text wrapped in `<!-- -->`.
3. `quarto render manuscript.qmd --to docx` — [NEEDS CLARIFICATION: not executed; quarto/pandoc absent locally and in CI (`.github/workflows/tests.yml:23-30` installs only `jq`)]. Per Pandoc's documented docx writer, a markdown `<!-- -->` block becomes a `RawBlock "html"`, which has no docx representation and is dropped.
4. Item 3: `figures/` with `fig10.png`, `fig11.png` and no `fig1.png`; plan ids `fig1`, `fig10` → `fig1` silently claims `fig10.png`.

## Suspected Code Paths

- `scripts/build_package.sh:256` — `<!-- no figure file starting with '%s' in figures/ -->`
- `scripts/build_package.sh:261` — `<!-- figures/%s is in the package but no plan entry claims it -->`
- `scripts/build_package.sh:284-285` — Discussion placeholder as `<!-- Not drafted... -->`
- `scripts/methods_text.py:374-378` — the only block naming the sources of caveats is inside `<!-- assembled by scripts/methods_text.py ... -->`
- `scripts/methods_text.py:319`, `:342` — `re.sub(r"\$\{[^}]*\}", "", filled)` deletes any unresolved placeholder without trace
- `scripts/methods_text.py:368-372`, `:246-268` — "Why these parameters" never names `params.yaml`; the pointer lives only in the vanishing comment (`:344-348`)
- `scripts/build_package.sh:175`, `:250` — `startswith(fid)` with no boundary; `match[0]` taken with no multiple-match check
- `tests/principle_9_test.sh:16-19` — greps source text only; `:30-33` hardcode substrings that live inside the comments today
- `commands/finish.md:109-115` — tells the operator to look for "comments about figures" before rendering; nothing re-checks the rendered output

## Root Cause Hypothesis

High confidence. Both scripts used HTML comments as the "needs a human" idiom, natural for someone editing the `.qmd`, but the deliverable is the rendered docx/html. Tests only grepped the source, so "marker exists in source" was never compared with "marker survives to what the collaborator opens". Items 2 and 3 are independent defects in the same files.

## Proposed Remediation

**Preferred**: one visible-text convention, reusing what the code already trusts in body text (`[CITATION NEEDED: ...]` at `methods_text.py:364-365`, `[DOI not shown: ...]` at `:338-340`). Introduce `[GAP: <description>]` and replace every comment-wrapped gap with it, as ordinary text in the section it belongs to (Results body for figures, a visible "Notes" subsection for methods notes, plain italic text for the undrafted Discussion). Also: (a) route unknown `${...}` placeholders to `[GAP: unresolved placeholder ${name}]` before any catch-all; (b) name the source file (`<run_dir>/params.yaml`) under "Why these parameters"; (c) require a boundary after `fid` (`.`, `_`, or end) and emit `[GAP: id '<fid>' matches N files: …]` on ambiguity.

**Alternative (rejected)**: keep comments and re-inject them after rendering — more moving parts than not using comments.

**Files likely to change**: `scripts/build_package.sh`, `scripts/methods_text.py`, `tests/principle_9_test.sh`, `commands/finish.md`.

**Tests to add or update**: principle_9_test asserts the gap-emitting output contains no `<!--`; fixture for the fig1/fig10 match; `${unknown_key}` becomes a visible `[GAP: …]`; optional render round-trip, blocked on quarto in CI (future work, not a blocker).

## Risks & Considerations

- `scripts/cite.sh` and `tests/principle_9_test.sh` hardcode `CITATION NEEDED`; keep that string or change both together.
- `commands/finish.md` step 3 must be reworded to the new marker, or the operator searches for the wrong thing. It touches `commands/`, so the manual half of `docs/TESTING.md` applies.
- A manuscript with visible `[GAP: …]` lines looks less finished — that is the point of invariant 9, but the maintainer should see an example before merge.

## Open Questions

- Unify `[CITATION NEEDED: …]` / `[DOI not shown: …]` into `[GAP: …]`, or keep them and use `[GAP: …]` only for the new cases? (Recommendation: keep the existing two — they are more specific and already tested — and use `[GAP: …]` for the rest.)
- Confirm on a machine with quarto that docx drops and html hides `<!-- -->` (manual, Positron machine).

## Decisions (maintainer, 2026-09-30: 「D 也交給 Sonnet 修」, taken as approval of the recommendations)

- Keep the existing `[CITATION NEEDED: …]` and `[DOI not shown: …]` strings (specific, already tested); use `[GAP: …]` for every other gap.
- The render round-trip (docx drops / html hides `<!-- -->`) is confirmed by the maintainer by hand on a machine with quarto, after merge; not blocking.
