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

echo
[ "$fails" = 0 ] && echo "OK: invisible-package-gaps stays fixed" || { echo "$fails failed"; exit 1; }
