#!/bin/bash
# Tests for scripts/methods_text.py.
#
# The one thing this program exists to do is fill a slot the pipeline left
# empty. nf-core's methods template has ${tool_citations}, and in every run
# measured here it rendered as "<p></p>" - so DADA2, STAR and Salmon went
# uncited in a paragraph that otherwise looks complete. The first case below is
# that slot, and it is the case that must never quietly start passing for the
# wrong reason.
#
# The second thing is what happens at the edge of what it knows. A tool it
# cannot match must become a visible gap, and a tool it can ALMOST match must
# become a visible gap with a candidate attached - never a citation. Measured:
# the versions file says `stringtie`, the citation list says `StringTie2`. A
# rule joining those would just as happily cite Bowtie's paper for Bowtie 2.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/methods_text.py"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
ok() { printf '%-62s ok\n' "$1"; }
no() { printf '%-62s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

RUN="$TMP/run"
mkdir -p "$RUN/results/pipeline_info" "$RUN/results/multiqc"
cat > "$RUN/results/pipeline_info/software_versions.yml" <<'YML'
FASTQC:
  fastqc: 0.12.1
DADA2_DENOISING:
  dada2: 1.38.0
STRINGTIE_MERGE:
  stringtie: 2.2.1
NOVEL_STEP:
  neverheardofit: 1.0
Workflow:
  nf-core/demo: v1.2.3
  Nextflow: 25.10.4
YML
: > "$RUN/results/pipeline_info/execution_report_2026-01-01_00-00-00.html"
echo '{}' > "$RUN/results/pipeline_info/params_2026-01-01_00-00-00.json"
touch "$RUN/results/multiqc/multiqc_report.html"
cat > "$RUN/params.yaml" <<'Y'
# Full-length reads, so the error model differs from the paired default.
pacbio: true
Y

A="$TMP/assets/nf-core/demo"
mkdir -p "$A/assets"
cat > "$A/CITATIONS.md" <<'MD'
# nf-core/demo: Citations
## Pipeline tools
- [FastQC](https://example.org/fastqc)
  > Andrews S. FastQC. doi: 10.1000/fastqc.
- [DADA2](https://example.org/dada2)
  > Callahan BJ et al. DADA2. doi: 10.1038/nmeth.3869.
- [StringTie2](https://example.org/stringtie2)
  > Kovaka S et al. StringTie2. doi: 10.1186/s13059-019-1910-1.
MD
cat > "$A/assets/methods_description_template.yml" <<'YML'
id: "demo-methods"
data: |
  <h4>Methods</h4>
  <p>Data was processed using nf-core/demo v${workflow.manifest.version}.</p>
  <p>Executed with Nextflow v${workflow.nextflow.version}:</p>
  <pre><code>${workflow.commandLine}</code></pre>
  <p>${tool_citations}</p>
YML

out=$("$S" --assets "$TMP/assets" "$RUN/results" 2>&1)

# THE case. An empty slot here is the defect this program was written for.
if grep -qF "Tools used within the workflow:" <<<"$out" \
   && grep -qF "DADA2" <<<"$out" && grep -qF "FastQC" <<<"$out"; then
  ok "the empty tool-citations slot comes back filled"
else no "the empty tool-citations slot comes back filled" "<<$out>>"; fi

grep -qF "nf-core/demo v1.2.3" <<<"$out" \
  && ok "the pipeline's own wording is reused, not rewritten" \
  || no "the pipeline's own wording is reused, not rewritten" "<<$out>>"

# A tool no citation file mentions.
grep -qF 'CITATION NEEDED: neverheardofit' <<<"$out" \
  && ok "an unciteable tool becomes a visible gap" \
  || no "an unciteable tool becomes a visible gap" "<<$out>>"

# A near miss: candidate shown, citation NOT made.
if grep -qF 'CITATION NEEDED: stringtie' <<<"$out" \
   && grep -qF 'StringTie2' <<<"$out" \
   && ! grep -qE '^- \*\*stringtie\*\*.*\(cited as' <<<"$out"; then
  ok "a near miss offers a candidate and cites nothing"
else no "a near miss offers a candidate and cites nothing" "<<$out>>"; fi

# The reconstructed command, and the admission that it is reconstructed.
if grep -qF "params-file params.yaml" <<<"$out" \
   && grep -qF "reconstructed" <<<"$out"; then
  ok "the command is rebuilt against the run's own params, and says so"
else no "the command is rebuilt against the run's own params, and says so" "<<$out>>"; fi

grep -qF "error model differs" <<<"$out" \
  && ok "the reasoning from params.yaml is carried into the methods" \
  || no "the reasoning from params.yaml is carried into the methods" "<<$out>>"

# No citation file at all must not produce a clean-looking methods section.
out2=$("$S" --assets "$TMP/nowhere" "$RUN/results" 2>&1)
if grep -qF "CITATION NEEDED: dada2" <<<"$out2" && grep -qF "no CITATIONS.md" <<<"$out2"; then
  ok "with no citation file every tool is a gap, and it says why"
else no "with no citation file every tool is a gap, and it says why" "<<$out2>>"; fi

echo
[ "$fails" = 0 ] && echo "OK: methods_text.py" || { echo "$fails failed"; exit 1; }
