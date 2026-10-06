#!/bin/bash
# Bug fix: invisible-package-gaps (.specify/bugs/invisible-package-gaps/).
#
# scripts/build_package.sh and scripts/methods_text.py wrote every "something
# is missing" marker as an HTML comment. Pandoc's documented docx writer turns
# a markdown `<!-- -->` block into a RawBlock with no docx representation, so
# it is dropped on render; the html writer keeps it only in page source. A
# reader of the finished package never sees a gap written that way, which is
# exactly what constitution invariant 9 exists to prevent
# (tests/principle_9_test.sh checks the machinery exists; this checks a gap
# actually reaches the reader in visible text).
#
# Three adjacent defects lived in the same code and are checked here too:
# an unresolved `${...}` placeholder was deleted with no trace, a figure id
# was matched with a bare `startswith` (so `fig1` could silently claim
# `fig10.png`), and the parameter-rationale section never named the file its
# reasoning came from.
BP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/build_package.sh"
MT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/methods_text.py"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
export ABF_PIPELINE_FETCHER=off   # no network in tests (#4); methods_text_fetch_test.sh covers fetching
fails=0
ok() { printf '%-62s ok\n' "$1"; }
no() { printf '%-62s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

# =============================================================================
# (a) + (c): scripts/build_package.sh's manuscript.qmd / methods.md
# =============================================================================
P="$TMP/proj"
mkdir -p "$P/runs/demo_20260101/results/pipeline_info" "$P/analysis/figures"
cat > "$P/runs/demo_20260101/results/pipeline_info/software_versions.yml" <<'YML'
FASTQC:
  fastqc: 0.12.1
Workflow:
  nf-core/demo: v1.0.0
  Nextflow: 25.10.4
YML
echo '{}' > "$P/runs/demo_20260101/results/pipeline_info/params_2026-01-01_00-00-00.json"
echo "# because reads are long" > "$P/runs/demo_20260101/params.yaml"

# fig1/fig10 boundary (item c): only fig10.png and fig11.png exist, no
# fig1.png at all - a bare startswith("fig1") matches BOTH. figA has two
# files that share a boundary-safe prefix - the ambiguous-match case.
echo x > "$P/analysis/figures/fig10.png"
echo x > "$P/analysis/figures/fig11.png"
echo x > "$P/analysis/figures/figA_v1.png"
echo x > "$P/analysis/figures/figA_v2.png"

cat > "$P/analysis/analysis.md" <<'MD'
| id | question | status |
|---|---|---|
| fig1 | Does fig1 show anything? | accepted |
| fig10 | Does fig10 show anything? | accepted |
| figA | Ambiguous figure | accepted |
MD

out=$(CITE_CURL=false bash "$BP" "$P" 2>&1); rc=$?
[ "$rc" = 0 ] && ok "builds" || no "builds" "rc=$rc <<$out>>"

Q="$P/submission/manuscript.qmd"
M="$P/submission/methods.md"

# --- a plan figure with no file --------------------------------------------
grep -qF "[GAP: no figure file starting with 'fig1' in figures/]" "$Q" \
  && ok "fig1 has no file: a visible [GAP: ...], not a comment" \
  || no "fig1 has no file: a visible [GAP: ...], not a comment" "not found in: $(cat "$Q" 2>/dev/null)"

# --- the boundary fix: fig1 must not silently claim fig10.png --------------
grep -qF 'figures/fig10.png){#fig-fig1}' "$Q" \
  && no "fig1 must not silently claim fig10.png" "it did" \
  || ok "fig1 does not silently claim fig10.png"

grep -qF 'figures/fig10.png){#fig-fig10}' "$Q" \
  && ok "fig10 resolves to its own file" \
  || no "fig10 resolves to its own file" "not found"

# --- an id matching two files is a gap, not silently resolved --------------
grep -qF "[GAP: id 'figA' matches 2 files" "$Q" \
  && ok "an id matching two files is reported as a gap" \
  || no "an id matching two files is reported as a gap" "not found in: $(cat "$Q" 2>/dev/null)"

# --- a figure no plan claims -------------------------------------------------
grep -qF "[GAP: figures/fig11.png is in the package but no plan entry claims it]" "$Q" \
  && ok "a figure no plan claims: a visible [GAP: ...]" \
  || no "a figure no plan claims: a visible [GAP: ...]" "not found in: $(cat "$Q" 2>/dev/null)"

# --- the undrafted discussion ------------------------------------------------
grep -qF "[GAP: not drafted" "$Q" \
  && ok "the undrafted discussion is a visible [GAP: ...]" \
  || no "the undrafted discussion is a visible [GAP: ...]" "not found in: $(cat "$Q" 2>/dev/null)"

# --- the methods notes (no CITATIONS.md - default assets dir has none here) -
grep -qF "[GAP: no CITATIONS.md" "$M" \
  && ok "methods notes (no CITATIONS.md) are a visible [GAP: ...]" \
  || no "methods notes (no CITATIONS.md) are a visible [GAP: ...]" "not found in: $(cat "$M" 2>/dev/null)"

# --- none of the above still hides behind an HTML comment -------------------
for phrase in "no figure file starting with 'fig1'" \
              "figures/fig11.png is in the package but no plan entry claims it" \
              "not drafted"; do
  printf '%-62s ' "not wrapped in <!-- -->: $phrase"
  if grep -F -- "$phrase" "$Q" | grep -qF '<!--'; then
    echo "FAIL: still inside an HTML comment"; fails=$((fails+1))
  else echo ok; fi
done
printf '%-62s ' "methods.md's notes are no longer wrapped in <!-- assembled -->"
if grep -qF '<!-- assembled by scripts/methods_text.py' "$M"; then
  echo "FAIL: still a comment"; fails=$((fails+1))
else echo ok; fi

# --- acceptance review: prefix ids that coexist, and one figure in several
# formats. fig1 and fig1_b both planned and both present: fig1 must get
# fig1.png, not an "ambiguous" gap (main picked it correctly; the first fix
# did not). A figure saved as .png and .pdf is one figure, not two.
P2="$TMP/proj2"
mkdir -p "$P2/runs/demo_20260101/results/pipeline_info" "$P2/analysis/figures"
cp "$P/runs/demo_20260101/results/pipeline_info/"* "$P2/runs/demo_20260101/results/pipeline_info/"
cp "$P/runs/demo_20260101/params.yaml" "$P2/runs/demo_20260101/"
for f in fig1.png fig1.pdf fig1_b.png; do echo x > "$P2/analysis/figures/$f"; done
cat > "$P2/analysis/analysis.md" <<'MD'
| id | question | status |
|---|---|---|
| fig1 | First figure | accepted |
| fig1_b | Second figure | accepted |
MD
CITE_CURL=false bash "$BP" "$P2" >/dev/null 2>&1
Q2="$P2/submission/manuscript.qmd"
grep -qF 'figures/fig1.png){#fig-fig1}' "$Q2" \
  && ok "fig1 gets fig1.png while fig1_b is also planned" \
  || no "fig1 gets fig1.png while fig1_b is also planned" "$(grep -n 'fig1' "$Q2" | head -3)"
grep -qF 'figures/fig1_b.png){#fig-fig1_b}' "$Q2" \
  && ok "fig1_b gets fig1_b.png" || no "fig1_b gets fig1_b.png" "not found"
printf '%-62s ' "fig1.png + fig1.pdf is one figure, not an ambiguous gap"
if grep -qF "[GAP: id 'fig1' matches" "$Q2"; then
  echo "FAIL: $(grep -F "[GAP: id 'fig1'" "$Q2")"; fails=$((fails+1)); else echo ok; fi

# --- acceptance review: the run's own notes are written even when this
# script added none of its own (the `if notes:` guard dropped them all).
printf '%-62s ' "run notes are kept when there are no local notes"
got=$(cd "$(dirname "$BP")" && python3 - <<'PY' 2>&1
import os, sys, tempfile
sys.path.insert(0, ".")
import methods_text as m
d = tempfile.mkdtemp()
open(os.path.join(d, "CITATIONS.md"), "w").write("# Citations\n")
m.assets_dir = lambda base, name: d
m.rendered_methods = lambda q: "<p>Data was processed.</p>"
run = {"run_dir": d, "workflow": {}, "tools": {}, "citable_tools": [],
       "notes": ["no hand-written params.yaml beside results/"]}
print(m.render(run, d))
PY
)
if grep -qF "[GAP: no hand-written params.yaml beside results/]" <<<"$got"; then echo ok; else
  echo "FAIL: <<${got:0:200}>>"; fails=$((fails+1)); fi

# --- developer review: nothing in the manuscript is an HTML comment ---------
# The per-figure "describe what this shows" placeholder is step 4's to fill.
# Left as a comment, a figure step 4 skipped rendered with no description and
# no sign one was missing - the same invisible gap as the rest of #32.
printf '%-62s ' "manuscript.qmd holds no HTML comment at all"
if grep -qF '<!--' "$Q"; then
  echo "FAIL: $(grep -nF '<!--' "$Q" | head -1)"; fails=$((fails+1))
else echo ok; fi
printf '%-62s ' "each planned figure carries a visible 'not written yet' gap"
if grep -qF "[GAP: Results for 'fig10' not written yet" "$Q"; then echo ok; else
  echo "FAIL: no visible placeholder for fig10"; fails=$((fails+1)); fi

# --- ambiguous matches are not ALSO double-reported as unclaimed orphans ----
printf '%-62s ' "ambiguous figA files are not ALSO reported as unclaimed orphans"
if grep -qF "figA_v1.png is in the package but no plan entry claims it" "$Q" \
   || grep -qF "figA_v2.png is in the package but no plan entry claims it" "$Q"; then
  echo "FAIL: double-reported"; fails=$((fails+1))
else echo ok; fi

# =============================================================================
# (b): an unresolved ${unknown_key} becomes a visible gap, never an empty
# string
# =============================================================================
A="$TMP/assets/nf-core/demo2"
mkdir -p "$A/assets"
cat > "$A/CITATIONS.md" <<'MD'
# nf-core/demo2: Citations
## Pipeline tools
- [FastQC](https://example.org/fastqc)
  > Andrews S. FastQC. doi: 10.1000/fastqc.
MD
cat > "$A/assets/methods_description_template.yml" <<'YML'
id: "demo2-methods"
data: |
  <h4>Methods</h4>
  <p>Data was processed using nf-core/demo2 v${workflow.manifest.version}, run for ${custom_reason}.</p>
  <p>Executed with Nextflow v${workflow.nextflow.version}:</p>
  <pre><code>${workflow.commandLine}</code></pre>
  <p>${tool_citations}</p>
YML

RUN2="$TMP/run2"
mkdir -p "$RUN2/results/pipeline_info"
cat > "$RUN2/results/pipeline_info/software_versions.yml" <<'YML'
FASTQC:
  fastqc: 0.12.1
Workflow:
  nf-core/demo2: v1.0.0
  Nextflow: 25.10.4
YML
: > "$RUN2/results/pipeline_info/execution_report_2026-01-01_00-00-00.html"
echo '{}' > "$RUN2/results/pipeline_info/params_2026-01-01_00-00-00.json"
cat > "$RUN2/params.yaml" <<'Y'
# because the read depth needed a higher threshold
min_reads: 500
Y

out2=$("$MT" --assets "$TMP/assets" "$RUN2/results" 2>&1)

grep -qF '[GAP: unresolved placeholder ${custom_reason}]' <<<"$out2" \
  && ok 'an unresolved ${custom_reason} becomes a visible [GAP: ...]' \
  || no 'an unresolved ${custom_reason} becomes a visible [GAP: ...]' "<<$out2>>"

if grep -qF ', run for .' <<<"$out2"; then
  no "...and is not silently deleted to an empty string" "found the blanked-out sentence"
else ok "...and is not silently deleted to an empty string"
fi

# =============================================================================
# (d): the parameter-rationale section names its source file
# =============================================================================
if grep -A3 -F "Why these parameters" <<<"$out2" | grep -qF 'params.yaml'; then
  ok "the parameter-rationale section names its source file"
else no "the parameter-rationale section names its source file" "<<$out2>>"; fi


# =============================================================================
# #38 (package-gaps-low): the five low-severity gaps left after #32.
# .specify/bugs/package-gaps-low/. Each case below fails on the code as it
# stood at 1a049f1.
# =============================================================================

# --- item 1: a ${...} inside an HTML attribute is a visible gap, not lost ----
A3="$TMP/assets/nf-core/demo3"
mkdir -p "$A3/assets"
cp "$A/CITATIONS.md" "$A3/CITATIONS.md"
cat > "$A3/assets/methods_description_template.yml" <<'YML'
id: "demo3-methods"
data: |
  <h4>Methods</h4>
  <div class="${cls}"><p>Body text.</p></div>
  <p>See <a href="${site}">the project site</a> for details.</p>
YML
RUN3="$TMP/run3"
mkdir -p "$RUN3/results/pipeline_info"
sed 's#nf-core/demo2#nf-core/demo3#' "$RUN2/results/pipeline_info/software_versions.yml" \
  > "$RUN3/results/pipeline_info/software_versions.yml"
echo '{}' > "$RUN3/results/pipeline_info/params_2026-01-01_00-00-00.json"
out3=$("$MT" --assets "$TMP/assets" "$RUN3/results" 2>&1)

grep -qF '[GAP: unresolved placeholder ${cls}]' <<<"$out3" \
  && ok 'a ${cls} in a <div class="..."> attribute is not lost with the tag' \
  || no 'a ${cls} in a <div class="..."> attribute is not lost with the tag' "<<$out3>>"
grep -qF '[GAP: unresolved placeholder ${site}]' <<<"$out3" \
  && ok 'a ${site} in an <a href> shows as a gap' \
  || no 'a ${site} in an <a href> shows as a gap' "<<$out3>>"
printf '%-62s ' 'the ${site} gap is visible text, not only a link target'
if grep -qE '\]\([^)]*GAP' <<<"$out3"; then
  echo "FAIL: $(grep -E '\]\([^)]*GAP' <<<"$out3" | head -1)"; fails=$((fails+1)); else echo ok; fi

# --- item 3: the methods paragraph and the software list name their sources -
printf '%-62s ' "the methods paragraph names its template"
if grep -F "methods_description_template.yml" <<<"$out2" | grep -qF 'Source'; then echo ok; else
  echo "FAIL: <<${out2:0:300}>>"; fails=$((fails+1)); fi
printf '%-62s ' "the software list names versions file and CITATIONS.md"
sw=$(sed -n '/### Software/,/### Why/p' <<<"$out2")
if grep -qF 'software_versions.yml' <<<"$sw" && grep -qF 'CITATIONS.md' <<<"$sw"; then echo ok; else
  echo "FAIL: <<$sw>>"; fails=$((fails+1)); fi
RUN4="$TMP/run4"
cp -r "$RUN2" "$RUN4"
printf '<html><h4>Methods</h4><p>Rendered by MultiQC.</p><h4>References</h4></html>\n' \
  > "$RUN4/results/multiqc_report.html"
out4=$("$MT" --assets "$TMP/assets" "$RUN4/results" 2>&1)
printf '%-62s ' "a MultiQC-rendered paragraph names the report it came from"
if grep -F "multiqc_report.html" <<<"$out4" | grep -qF 'Source'; then echo ok; else
  echo "FAIL: <<${out4:0:300}>>"; fails=$((fails+1)); fi

# --- item 2: a plan row with no id is a visible gap, not skipped -------------
P5="$TMP/proj5"
mkdir -p "$P5/runs/demo_20260101/results/pipeline_info" "$P5/analysis/figures"
cp "$P/runs/demo_20260101/results/pipeline_info/"* "$P5/runs/demo_20260101/results/pipeline_info/"
cp "$P/runs/demo_20260101/params.yaml" "$P5/runs/demo_20260101/"
echo x > "$P5/analysis/figures/fig1.png"
cat > "$P5/analysis/analysis.md" <<'MD'
| id | question | status |
|---|---|---|
| fig1 | Has an id | accepted |
|  | Orphan question without an id | accepted |
MD
CITE_CURL=false bash "$BP" "$P5" >/dev/null 2>&1
Q5="$P5/submission/manuscript.qmd"
printf '%-62s ' "a plan row with no id is reported as a visible gap"
if grep -F "Orphan question without an id" "$Q5" | grep -F '[GAP:' | grep -qF 'no id'; then echo ok; else
  echo "FAIL: not found in: $(cat "$Q5" 2>/dev/null)"; fails=$((fails+1)); fi

# --- item 4: a figure saved in two formats mentions the one not embedded -----
printf '%-62s ' "fig1.pdf (not embedded) is named beside fig1.png"
if grep -qF "Also in figures/, not embedded: fig1.pdf" "$Q2"; then echo ok; else
  echo "FAIL: $(grep -n 'fig1' "$Q2" | head -4)"; fails=$((fails+1)); fi

# --- item 5: an id whose only match is not an image is not embedded ----------
P6="$TMP/proj6"
mkdir -p "$P6/runs/demo_20260101/results/pipeline_info" "$P6/analysis/figures"
cp "$P/runs/demo_20260101/results/pipeline_info/"* "$P6/runs/demo_20260101/results/pipeline_info/"
cp "$P/runs/demo_20260101/params.yaml" "$P6/runs/demo_20260101/"
echo x > "$P6/analysis/figures/fig1.csv"
cat > "$P6/analysis/analysis.md" <<'MD'
| id | question | status |
|---|---|---|
| fig1 | Only a table exists | accepted |
MD
CITE_CURL=false bash "$BP" "$P6" >/dev/null 2>&1
Q6="$P6/submission/manuscript.qmd"
printf '%-62s ' "fig1.csv is not embedded as an image"
if grep -qF 'figures/fig1.csv)' "$Q6"; then echo "FAIL: $(grep -F 'fig1.csv' "$Q6" | head -1)"; fails=$((fails+1)); else echo ok; fi
printf '%-62s ' "...and the missing image is a visible gap naming fig1.csv"
if grep -F "[GAP:" "$Q6" | grep -F "fig1.csv" | grep -qF "no image"; then echo ok; else
  echo "FAIL: $(cat "$Q6" 2>/dev/null | head -20)"; fails=$((fails+1)); fi
printf '%-62s ' "...and fig1.csv is not also reported as an unclaimed orphan"
if grep -qF "fig1.csv is in the package but no plan entry claims it" "$Q6"; then
  echo "FAIL: double-reported"; fails=$((fails+1)); else echo ok; fi


# --- #38 acceptance: every file in figures/ is named somewhere --------------
P7="$TMP/proj7"
mkdir -p "$P7/runs/demo_20260101/results/pipeline_info" "$P7/analysis/figures"
cp "$P/runs/demo_20260101/results/pipeline_info/"* "$P7/runs/demo_20260101/results/pipeline_info/"
cp "$P/runs/demo_20260101/params.yaml" "$P7/runs/demo_20260101/"
for f in fig1_a.png fig1_b.png fig1_c.csv; do echo x > "$P7/analysis/figures/$f"; done
cat > "$P7/analysis/analysis.md" <<'MD'
| id | question | status |
|---|---|---|
| fig1 | Ambiguous with a table | accepted |
MD
CITE_CURL=false bash "$BP" "$P7" >/dev/null 2>&1
Q7="$P7/submission/manuscript.qmd"
printf '%-62s ' "ambiguous id: the non-image file is still named"
if grep -F "[GAP:" "$Q7" | grep -F "fig1_a.png" | grep -F "fig1_b.png" | grep -qF "fig1_c.csv"; then echo ok; else
  echo "FAIL: $(grep -n 'fig1' "$Q7" | head -4)"; fails=$((fails+1)); fi

printf '%-62s ' "a gap marker is not glued to a following link"
if grep -qF '][' <<<"$(grep -F 'project site' <<<"$out3")"; then
  echo "FAIL: $(grep -F 'project site' <<<"$out3")"; fails=$((fails+1)); else echo ok; fi

FIN="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/commands/finish.md"
for phrase in "has no id" "no image file" "Also in figures/, not embedded"; do
  printf '%-62s ' "finish.md step 3 knows: $phrase"
  if sed -n '/^3\. \*\*Read what it produced/,/^4\. /p' "$FIN" | grep -qF "$phrase"; then echo ok; else
    echo "FAIL: not in step 3"; fails=$((fails+1)); fi
done

echo
[ "$fails" = 0 ] && echo "OK: invisible-package-gaps stays fixed" || { echo "$fails failed"; exit 1; }
