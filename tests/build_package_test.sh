#!/bin/bash
# Tests for scripts/build_package.sh.
#
# Two properties matter more than the file list.
#
# The first is that a gap stays visible. A plan entry whose figure was never
# produced, and a figure no plan entry claims, both leave a comment in the
# manuscript. Silence there would produce a document that looks complete and
# is missing a result nobody asked about again.
#
# The second is that the .qmd carries no executable code. The figures are
# already files by the time this runs, so rendering needs Quarto and nothing
# else - no R, no knitr. That is what lets the document render on a machine
# with none of them, which is most of the machines involved.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/build_package.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
ok() { printf '%-62s ok\n' "$1"; }
no() { printf '%-62s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

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
echo "# because the reads are long" > "$P/runs/demo_20260101/params.yaml"

# A plan with two entries; only one of them has a figure. And one stray figure
# that no entry claims.
cat > "$P/analysis/analysis.md" <<'MD'
- **richness**
  id: richness
  question: Does treatment change richness?
  status: accepted
- **evenness**
  id: evenness
  question: Is evenness affected too?
  status: accepted
MD
echo x > "$P/analysis/figures/richness.png"
echo x > "$P/analysis/figures/orphan.png"
echo 'x <- 1' > "$P/analysis/plot_richness.R"

# No network in the test: cite.sh caches, and an empty cache plus a failing
# fetcher is the offline state. It must not stop the build.
out=$(CITE_CURL=false bash "$S" "$P" 2>&1); rc=$?
[ "$rc" = 0 ] && ok "builds without a network" || no "builds without a network" "rc=$rc <<$out>>"

Q="$P/submission/manuscript.qmd"
for f in manuscript.qmd methods.md provenance.json README.md; do
  [ -s "$P/submission/$f" ] && ok "wrote $f" || no "wrote $f" "missing or empty"
done
[ -s "$P/submission/figures/richness.png" ] && ok "figures are copied into the package" \
  || no "figures are copied into the package" "missing"
[ -s "$P/submission/scripts/plot_richness.R" ] && ok "the code that made them travels too" \
  || no "the code that made them travels too" "missing"
[ -s "$P/submission/scripts/analysis.md" ] && ok "the plan travels with the package" \
  || no "the plan travels with the package" "missing"

grep -qF "Does treatment change richness?" "$Q" \
  && ok "a plan entry's question becomes the caption" \
  || no "a plan entry's question becomes the caption" "not in the qmd"

grep -qF "no figure file starting with 'evenness'" "$Q" \
  && ok "a planned figure that was never made is called out" \
  || no "a planned figure that was never made is called out" "silent"

grep -qF "orphan.png is in the package but no plan entry claims it" "$Q" \
  && ok "a figure nobody planned is called out too" \
  || no "a figure nobody planned is called out too" "silent"

grep -q '```{' "$Q" \
  && no "the manuscript carries no executable chunks" "found a code chunk" \
  || ok "the manuscript carries no executable chunks"

grep -qF "Discussion" "$Q" && ! grep -qiE '^(In conclusion|These results (show|suggest|demonstrate))' "$Q" \
  && ok "the discussion is left to the authors" \
  || no "the discussion is left to the authors" "something was drafted"

# --render on a machine with no quarto: refuse, name the boundary, and leave
# everything that WAS possible in place. PITFALLS 20i's shape.
# Not by hiding quarto behind a trimmed PATH: doing that also hides the only
# runnable python3 on this cluster and the failure becomes PITFALLS 16d
# instead of the one under test. This machine has no quarto, and a machine
# that does takes the branch above.
out=$(CITE_CURL=false bash "$S" --render "$P" 2>&1); rc=$?
if command -v quarto >/dev/null 2>&1; then
  ok "(quarto present here - render path not exercised)"
elif [ "$rc" = 3 ] && grep -qF "Positron" <<<"$out" && [ -s "$Q" ]; then
  ok "--render without quarto names the machine, keeps the files"
else no "--render without quarto names the machine, keeps the files" "rc=$rc <<$out>>"; fi

# The two refusals that point somewhere.
rm "$P/analysis/analysis.md"
out=$(bash "$S" "$P" 2>&1); rc=$?
[ "$rc" = 2 ] && grep -qF "/downstream" <<<"$out" \
  && ok "no plan: refuses and says which step writes one" \
  || no "no plan: refuses and says which step writes one" "rc=$rc <<$out>>"

mkdir -p "$TMP/empty/analysis"; echo "-" > "$TMP/empty/analysis/analysis.md"
out=$(bash "$S" "$TMP/empty" 2>&1); rc=$?
[ "$rc" = 2 ] && grep -qF "at least one run" <<<"$out" \
  && ok "no runs: refuses and says why" \
  || no "no runs: refuses and says why" "rc=$rc <<$out>>"

echo
[ "$fails" = 0 ] && echo "OK: build_package.sh" || { echo "$fails failed"; exit 1; }
