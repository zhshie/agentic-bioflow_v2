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

# ---------------------------------------------------------------------------
# R1 (confirmed bug, methods_text.py:244): `.replace("${doi_text}", "")` threw
# away the pipeline's own DOI, which MultiQC's report already renders
# correctly. Measured against a real run (rnaseq_sclerotia_d5_20260902):
# multiqc_report.html has "Data was processed using nf-core/rnaseq v3.14.0
# (doi: <a href='...zenodo.1400710'>...</a>) ..." while the local re-render
# blanked it. Fixed by reading MultiQC's own rendered paragraph (which already
# has the DOI right) and filling only the ${tool_citations} slot it leaves
# empty - not re-deriving the paragraph from the template with string
# replaces.
RUN2="$TMP/run2"
mkdir -p "$RUN2/results/multiqc/star_salmon" "$RUN2/results/pipeline_info"
cat > "$RUN2/results/pipeline_info/software_versions.yml" <<'YML'
FASTQC:
  fastqc: 0.12.1
DADA2_DENOISING:
  dada2: 1.38.0
Workflow:
  nf-core/demo: v2.0.0
  Nextflow: 25.10.4
YML
: > "$RUN2/results/pipeline_info/execution_report_2026-01-01_00-00-00.html"
echo '{}' > "$RUN2/results/pipeline_info/params_2026-01-01_00-00-00.json"
cat > "$RUN2/params.yaml" <<'Y'
pacbio: true
Y

# Shaped exactly like the real report: a Methods heading, the paragraph
# MultiQC already filled in full (DOI included), the raw non-reproducible
# command line, then the still-empty ${tool_citations} slot as a bare <p></p>,
# then References. Trimmed of everything this test does not check.
cat > "$RUN2/results/multiqc/star_salmon/multiqc_report.html" <<'HTML'
<div class="mqc-section mqc-section-nf-core-demo-methods-description">
<h4>Methods</h4>
<p>Data was processed using nf-core/demo v2.0.0 (doi: <a href='https://doi.org/10.5281/zenodo.9999999'>https://doi.org/10.5281/zenodo.9999999</a>) of the nf-core collection of workflows.</p>
<p>The pipeline was executed with Nextflow v25.10.4 with the following command:</p>
<pre><code>nextflow run 'https://github.com/nf-core/demo' -params-file 'https://api.cloud.seqera.io/ephemeral/A2H4yoZPhIZJIgmV-Pow_w.yaml' -r 2.0.0</code></pre>
<p></p>
<h4>References</h4>
<ul></ul>
</div>
HTML

out3=$("$S" --assets "$TMP/assets" "$RUN2/results" 2>&1)

grep -qF "zenodo.9999999" <<<"$out3" \
  && ok "R1: the pipeline's own DOI survives into the methods paragraph" \
  || no "R1: the pipeline's own DOI survives into the methods paragraph" "<<$out3>>"

if grep -qF "Tools used within the workflow:" <<<"$out3" && grep -qF "DADA2" <<<"$out3"; then
  ok "R1: the tool-citations gap in the RENDERED report is still filled"
else no "R1: the tool-citations gap in the RENDERED report is still filled" "<<$out3>>"; fi

# The prose note is allowed to say "ephemeral URL" (same as the existing
# template-render path above) - what must not survive is the URL itself.
grep -qF "api.cloud.seqera.io" <<<"$out3" \
  && no "R1: the ephemeral launch URL is not left in as the command" "<<$out3>>" \
  || ok "R1: the ephemeral launch URL is not left in as the command"

grep -qF "params-file params.yaml" <<<"$out3" \
  && ok "R1: the command is still reconstructed against the run's own params" \
  || no "R1: the command is still reconstructed against the run's own params" "<<$out3>>"

# ---------------------------------------------------------------------------
# Issue #3: nf-core's own template builds `https://doi.org/${doi_text}`
# assuming doi_text is a bare id, but some pipelines' manifest.doi is already
# the full URL, so MultiQC's own render comes out doubled -
# "https://doi.org/https://doi.org/10.xxxx/..." - a link that reads fine and
# 404s. Shaped exactly like RUN2 above, except the href MultiQC rendered
# already carries the doubled prefix; the anchor TEXT does not, which is the
# real shape measured in the bug report (only the href is doubled).
RUN3="$TMP/run3"
mkdir -p "$RUN3/results/multiqc/star_salmon" "$RUN3/results/pipeline_info"
cat > "$RUN3/results/pipeline_info/software_versions.yml" <<'YML'
FASTQC:
  fastqc: 0.12.1
Workflow:
  nf-core/rnaseq: v3.14.0
  Nextflow: 25.10.4
YML
: > "$RUN3/results/pipeline_info/execution_report_2026-01-01_00-00-00.html"
echo '{}' > "$RUN3/results/pipeline_info/params_2026-01-01_00-00-00.json"
cat > "$RUN3/params.yaml" <<'Y'
pacbio: true
Y
cat > "$RUN3/results/multiqc/star_salmon/multiqc_report.html" <<'HTML'
<div class="mqc-section mqc-section-nf-core-rnaseq-methods-description">
<h4>Methods</h4>
<p>Data was processed using nf-core/rnaseq v3.14.0 (doi: <a href='https://doi.org/https://doi.org/10.5281/zenodo.1400710'>https://doi.org/10.5281/zenodo.1400710</a>) of the nf-core collection of workflows.</p>
<p>The pipeline was executed with Nextflow v25.10.4 with the following command:</p>
<pre><code>nextflow run 'https://github.com/nf-core/rnaseq' -params-file 'https://api.cloud.seqera.io/ephemeral/A2H4yoZPhIZJIgmV-Pow_w.yaml' -r 3.14.0</code></pre>
<p></p>
<h4>References</h4>
<ul></ul>
</div>
HTML

out4=$("$S" --assets "$TMP/assets" "$RUN3/results" 2>&1)

if grep -qF "doi.org/10.5281/zenodo.1400710" <<<"$out4" \
   && ! grep -qF "doi.org/https://doi.org" <<<"$out4"; then
  ok "the pipeline's own DOI link is not double-prefixed with https://doi.org/"
else no "the pipeline's own DOI link is not double-prefixed with https://doi.org/" "<<$out4>>"; fi

# ---------------------------------------------------------------------------
# Issue #2 (confirmed on native Windows Python, WinError 193 - "%1 is not a
# valid Win32 application"): provenance() used to exec collect_provenance.py
# by its own path. subprocess.run()'s CreateProcess call bypasses shebang/
# file-association handling entirely on native Windows, so the OS never gets
# a chance to see `#!/bin/bash` and hand the file to python3 - it only works
# at all today because every test above runs on a POSIX shebang-aware OS.
# sys.executable sidesteps the whole question by naming the interpreter
# directly. Portable proxy for the same shape of failure - "a script the OS
# will not run directly by its own path, but the right interpreter reads
# fine" - stripping the executable bit from a copy of collect_provenance.py
# and asking methods_text.py to use it: with the fix this needs only read
# access, because sys.executable never asks the OS to exec the file itself.
COPY="$TMP/copy"; mkdir -p "$COPY"
cp "$(dirname "$S")/collect_provenance.py" "$COPY/collect_provenance.py"
cp "$S" "$COPY/methods_text.py"
chmod -x "$COPY/collect_provenance.py"
chmod +x "$COPY/methods_text.py"
out5=$("$COPY/methods_text.py" --assets "$TMP/assets" "$RUN/results" 2>&1); rc5=$?
if [ "$rc5" = 0 ] && grep -qF "Tools used within the workflow:" <<<"$out5"; then
  ok "collect_provenance.py needs no execute bit - invoked via sys.executable"
else no "collect_provenance.py needs no execute bit - invoked via sys.executable" "rc=$rc5 <<$out5>>"; fi

echo
[ "$fails" = 0 ] && echo "OK: methods_text.py" || { echo "$fails failed"; exit 1; }
