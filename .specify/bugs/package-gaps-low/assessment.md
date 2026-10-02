# Bug Assessment: Low-severity gaps left in the paper package after #32

- **Slug**: package-gaps-low
- **Created**: 2026-10-02
- **Source**: https://github.com/zhshie/agentic-bioflow_v2/issues/38 (follow-up to #32; see `.specify/bugs/invisible-package-gaps/fix.md`)
- **Verdict**: valid, all five reproduce on main 1a049f1
- **Severity**: low (each can only hide or misplace a gap, none corrupts data)

## 給維護者

1. 方法段落裡「沒填到的欄位」若出現在 HTML 屬性（例如 `<a href="${x}">`）裡，標記會跟著標籤一起消失，或只剩在連結目標裡，讀者看不到。已修：標記搬到可見文字。
2. 分析計畫表中沒有 id 的那一列被默默略過。已修：變成可見的 `[GAP: ...]`。
3. 方法段落、軟體清單沒有寫出資料來自哪個檔案（只有參數理由有）。已修：各加一行 `Source:`。
4. 一張圖存成兩種格式時只嵌入一種，另一種沒被提及。已修：圖下面加一行說明沒嵌入的檔案（要不要這行見 fix.md 的「需維護者決定」）。
5. 只有非圖片檔（如 `fig1.csv`）的 id 會被當成圖片嵌入。已修：改成可見的 `[GAP: ...]`。

## Items

### 1. `${...}` inside an HTML attribute

- **Repro**: a methods template (or the MultiQC-rendered paragraph) holding `<div class="${cls}">...` or `<a href="${site}">text</a>`, with no value for the placeholder. `methods_text.py <results>`.
- **Root cause**: `mark_unresolved_placeholders()` runs before `html_to_md()`. It rewrites the placeholder where it stands, which inside a tag is inside the attribute value. `html_to_md` then either strips the whole tag (`<div ...>` regex `</?(p|ul|div|...)[^>]*>`), taking the marker with it, or turns the `href` into the link target `[text]([GAP: ...])`, where it is not readable text.
- **Fix?** Yes. Treat placeholders inside a tag separately: replace them in the tag with `#` and emit the `[GAP: ...]` marker as text right after the tag, so it survives tag stripping and is part of the link text.
- **Test**: template with both a `class` and an `href` placeholder; assert both markers are present and none sits inside `](...)`.

### 2. A plan row with no id is skipped silently

- **Repro**: `analysis.md` table with a row whose `id` cell is empty (question and status filled). `parse_table()` drops it with `if row.get("id")`; the manuscript has no section and no trace.
- **Root cause**: the filter exists to ignore blank rows but also swallows rows that carry real content.
- **Fix?** Yes. A row with an empty id but some other non-empty cell becomes an entry with an empty id; the Results loop prints `[GAP: a plan row has no id (<question>) - no figure can be matched to it; add an id to analysis.md]`. Fully blank rows are still ignored. The kv-block form cannot be fixed the same way (a block without `id:` is indistinguishable from an ordinary heading), so it is left as is.
- **Test**: table with one good and one id-less row; assert a `[GAP:` line naming the row's question and saying "no id".

### 3. Methods paragraph and software list do not name their sources

- **Repro**: `methods_text.py` output; only "Why these parameters" has a `Source:` line.
- **Root cause**: #32 added the pointer for params only. The data for the others is already in the run (`quality_report`, `versions_file`) or computed in `render()` (template and CITATIONS.md paths).
- **Fix?** Yes. One `Source:` line after the methods paragraph (MultiQC report, else the template file, else "no template found" which is already a note) and one under "Software" (versions file and CITATIONS.md or its absence). Paths are relative to the run dir or shown as `<assets>/...`-relative file names, never absolute, so output stays portable.
- **Test**: template path (names `methods_description_template.yml`), software list (names `software_versions.yml` and `CITATIONS.md`), MultiQC path (names `multiqc_report.html`).

### 4. A figure saved in two formats: the other format is not mentioned

- **Repro**: `figures/fig1.png` and `figures/fig1.pdf`, plan id `fig1`. The manuscript embeds the png; the pdf appears nowhere (it is marked claimed, so not even an orphan gap).
- **Root cause**: formats are collapsed to one figure on purpose (#32 acceptance review), but the collapse also hides that a second file exists.
- **Fix?** Yes, minimal. A visible line under the figure: `Also in figures/, not embedded: fig1.pdf`. Not a `[GAP:]`, because nothing is missing, so the author does not have to clear it, but the reader can see it. **Needs maintainer decision** (could instead go in README, or be dropped).
- **Test**: the `fig1.png + fig1.pdf` fixture already in the test file; assert the line.

### 5. An id whose only match is a non-image file is embedded as an image

- **Repro**: `figures/fig1.csv` only, plan id `fig1`: `![...](figures/fig1.csv){#fig-fig1}`, which renders as a broken image or a render error.
- **Root cause**: `fig_matches()` matches by name only; extension is never checked.
- **Fix?** Yes. Embedding candidates are restricted to image extensions (png jpg jpeg svg pdf tif tiff gif webp). If an id matches files but none is an image: `[GAP: id 'fig1' has no image file in figures/ - only: fig1.csv]`, and those files count as claimed so they are not also reported as orphans. A non-image file beside an image of the same id is listed in the "Also in figures/" line from item 4.
- **Test**: csv-only fixture; assert no `](figures/fig1.csv)`, a `[GAP:` naming `fig1.csv` and "no image", and no orphan line for it.

## Files likely to change

`scripts/methods_text.py`, `scripts/build_package.sh`, `tests/package_gaps_test.sh`, `.specify/bugs/package-gaps-low/fix.md`.
