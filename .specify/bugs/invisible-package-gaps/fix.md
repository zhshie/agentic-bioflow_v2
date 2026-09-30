# Bug Fix: Gaps in the paper package are invisible to the reader

- **Slug**: invisible-package-gaps
- **Fixed**: 2026-09-30
- **Assessment**: ./assessment.md
- **Status**: applied

## Summary

Every gap marker `build_package.sh` and `methods_text.py` wrote as an HTML
comment (`<!-- ... -->`) is now ordinary visible text of the form
`[GAP: ...]`, so it survives a docx/html render instead of vanishing. Two
adjacent defects in the same code were fixed alongside it: an unresolved
`${...}` placeholder is now a visible gap instead of a silent deletion, and
figure-id matching now requires a name boundary and reports an ambiguous
match instead of silently taking the first hit.

## Changes

| File | Change | Notes |
|------|--------|-------|
| `scripts/build_package.sh` | modified | "no figure file starting with" and "no plan entry claims it" now print as `[GAP: ...]`, not `<!-- ... -->` |
| `scripts/build_package.sh` | modified | added `fig_matches()`: boundary-checked match (`.`/`_`/end) instead of bare `startswith`; a fid matching >1 file prints `[GAP: id '<fid>' matches N files: ...]` instead of silently taking `match[0]` |
| `scripts/build_package.sh` | modified | Discussion placeholder is now `*[GAP: not drafted - ...]*` instead of an HTML comment |
| `scripts/methods_text.py` | modified | added `mark_unresolved_placeholders()`; both `re.sub(r"\$\{[^}]*\}", "", filled)` catch-alls replaced with it, so an unmatched `${name}` becomes `[GAP: unresolved placeholder ${name}]` instead of an empty string |
| `scripts/methods_text.py` | modified | the notes block (reconstructed-command-line note, no-CITATIONS.md note, etc.) is now a visible `### Notes` section with one `- [GAP: ...]` line each, not an HTML comment |
| `scripts/methods_text.py` | modified | "Why these parameters" now opens with `Source: \`<relpath to params file>\`` so the rationale names the file it came from |
| `commands/finish.md` | modified | "The Discussion heading is left in place with a comment saying so" → "...with a visible `[GAP: ...]` marker saying so"; step 3's "comments about figures" → "`[GAP: ...]` lines that flag figures" |
| `tests/package_gaps_test.sh` | added | see below |

`docs/FINISH.md` was checked and needs no change — its one "comments" mention
(line 112) is about the `#` rationale comments inside a run's own
`params.yaml`, an unrelated and still-accurate usage.

## Diff Highlights

```python
# build_package.sh — boundary-checked match, ambiguity reported as a gap
def fig_matches(fid, figs):
    boundary = re.compile(r"^" + re.escape(fid) + r"([._]|$)")
    return [f for f in figs if boundary.match(f)]
...
match = fig_matches(fid, figs)
if len(match) == 1:
    print("![%s](figures/%s){#fig-%s}\n" % (qtext, match[0], fid))
    emitted.add(match[0])
elif len(match) > 1:
    print("[GAP: id '%s' matches %d files in figures/: %s]\n"
          % (fid, len(match), ", ".join(match)))
    emitted.update(match)
else:
    print("[GAP: no figure file starting with '%s' in figures/]\n" % fid)
```

```python
# methods_text.py — unresolved placeholders become visible, not deleted
UNRESOLVED_PLACEHOLDER_RE = re.compile(r"\$\{([^}]*)\}")

def mark_unresolved_placeholders(text):
    return UNRESOLVED_PLACEHOLDER_RE.sub(
        lambda m: "[GAP: unresolved placeholder ${%s}]" % m.group(1), text)
```

## Tests Added or Updated

- `tests/package_gaps_test.sh` (new, 16 cases) — covers all four required
  scenarios plus the boundary/ambiguity fix:
  - a plan figure with no file → visible `[GAP: no figure file starting with '<id>' in figures/]`
  - a figure no plan claims → visible `[GAP: figures/<f> is in the package but no plan entry claims it]`
  - the undrafted Discussion → visible `[GAP: not drafted ...]`
  - the methods notes (no CITATIONS.md) → visible `[GAP: ...]` inside `methods.md`
  - none of the above is still wrapped in `<!-- -->`
  - `fig1`/`fig10` with only `fig10.png`/`fig11.png`: `fig1` no longer
    silently claims `fig10.png`; `fig10` resolves to its own file
  - an id matching two files (`figA` → `figA_v1.png`, `figA_v2.png`) is
    reported as a gap, not silently resolved, and not double-reported as an
    orphan
  - an unresolved `${custom_reason}` becomes `[GAP: unresolved placeholder ${custom_reason}]`, not an empty string
  - the "Why these parameters" section names its source file (`params.yaml`)
- Picked up automatically by `tests/run_all.sh` (globs `tests/*.sh`).

## Local Verification

- RED (before the fix, current code): `MSYS_NO_PATHCONV=1 wsl.exe bash /mnt/c/Users/ACER/run_pkg_gaps_test.sh` → `12 failed`, each failure the exact defect described (e.g. `fig1` resolved to `figures/fig10.png`; `run for .` with the placeholder silently deleted; notes/discussion/figure gaps still inside `<!-- -->`).
- GREEN (after the fix): same command → all 16 cases `ok`.
- `bash tests/build_package_test.sh` → OK (29/29), unchanged behaviour for the existing fixtures.
- `bash tests/methods_text_test.sh` → OK (13/13), unchanged behaviour.
- `bash tests/principle_9_test.sh` → OK — the structural strings it greps for in source (`no figure file starting with`, `no plan entry claims it`) are still present verbatim inside the new `[GAP: ...]` literals.
- `bash tests/portable_userland.sh` → all passed (no new unportable spellings).
- `bash tests/no_hardcoded_paths.sh` → OK.
- `bash tests/run_all.sh` (full suite, 74 files) → **74/74 passed, all green**, `FINAL_EXIT=0`.
- All runs were in WSL (`wsl.exe bash /mnt/c/Users/ACER/...`), never native Git Bash, per the suite's own MSYS refusal.
- Not run: an actual `quarto render --to docx` round-trip (no quarto/pandoc on this machine) — per the assessment's own Decisions section, this is confirmed by the maintainer by hand on a machine with quarto, not blocking.

## Deviations from Assessment

None. The `[CITATION NEEDED: ...]` and `[DOI not shown: ...]` strings were
left untouched, as decided.

## Follow-ups

- Maintainer to manually confirm on a machine with quarto that the old
  `<!-- -->` markers were in fact dropped/hidden on render, and spot-check
  that the new `[GAP: ...]` lines survive a `quarto render --to docx`
  round-trip (assessment's Open Questions / Decisions, not blocking).
- The instructional `<!-- Describe what this shows, from the data. ... -->`
  placeholder in `build_package.sh`'s per-entry Results section was left
  unchanged: it is not a "something could not be found" gap but a
  to-be-replaced authoring instruction for the `/finish` step-4 write-up, and
  it was not named in the assessment's suspected code paths.

## Developer review (2026-09-30)

The implementer left the per-figure `<!-- Describe what this shows… -->` placeholder as an HTML comment, reading it as an authoring instruction rather than a gap. Changed: step 4 of `commands/finish.md` fills it, and a figure step 4 skips would render with no description and no sign one is missing — the same invisible gap. It is now `[GAP: Results for '<id>' not written yet - …]`; `commands/finish.md` step 4 says to replace it and that one left in place stays visible on purpose; step 3 says these are step 4's to fill, not decisions. `tests/package_gaps_test.sh` now asserts the manuscript holds no HTML comment at all and that each planned figure carries the visible placeholder (both red on 40f6525, green now). WSL `tests/run_all.sh` 74/74.

## After independent acceptance (2026-09-30)

The reviewer failed one item and found one silent drop in the rewritten block; both fixed test-first (3 new cases, red on 602c002):

- Regression from the first fix: with `fig1` and `fig1_b` both planned (and `fig1.pdf` beside `fig1.png`), `fig1` was reported ambiguous and its figure dropped, where main had picked it. Now a file claimed by a longer planned id belongs to that id, and one figure in several formats is one figure (exact-name file, preferred format png > jpg > svg > pdf > tif).
- `methods_text.py`: the run's own notes (`collect_provenance`) were dropped whenever the script added none of its own (`if notes:` guard). They are now always written.
- `commands/finish.md` step 3 now names every kind of `[GAP:]` (manuscript and methods.md, incl. Notes and unresolved placeholders); `tests/build_package_test.sh` header no longer says "comment".

Not changed (reviewer: rare, low): a `${…}` inside an HTML attribute of a MultiQC template can still vanish with the tag or land only in a link target; a plan row with no id is skipped (pre-existing, outside this assessment); only `params.yaml` names its source file — the methods paragraph and software list still do not name theirs. → follow-up.

WSL `tests/run_all.sh` 74/74.
