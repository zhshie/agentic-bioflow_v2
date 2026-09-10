#!/bin/bash
# Tests for scripts/collect_provenance.py.
#
# The thing worth testing here is not that it reads a file - it is that it
# reads files whose names nobody agreed on. Measured across three real runs on
# one cluster, the versions file is called software_versions.yml,
# nf_core_<pipeline>_software_mqc_versions.yml, or collated_versions.yml; the
# quality report sits at the top of the tree in one and under the aligner's
# name in another. A lookup table would have been wrong twice and would go
# wrong again on the next template.
#
# The other one is the retry. A run that failed and resumed leaves the first
# attempt's report and a 154-byte trace beside the real ones. Sorted
# alphabetically the corpse comes first, and nothing about the output would
# look wrong.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/collect_provenance.py"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

ok() { printf '%-62s ok\n' "$1"; }
no() { printf '%-62s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }
has() { grep -qF -- "$2" <<<"$1"; }

# A run, built to order: <dir> <versions-filename> <qc-subpath>
mkrun() {
  local d="$1" vname="$2" qc="$3"
  mkdir -p "$d/results/pipeline_info" "$d/results/$(dirname "$qc")"
  cat > "$d/results/pipeline_info/$vname" <<YML
FASTQC:
  fastqc: 0.12.1
DADA2_DENOISING:
  R: 4.5.2
  dada2: 1.38.0
Workflow:
  nf-core/ampliseq: v2.18.0
  Nextflow: 25.10.4
YML
  echo '{"input":"samplesheet.csv","outdir":"results"}' \
      > "$d/results/pipeline_info/params_2026-09-04_11-35-50.json"
  : > "$d/results/pipeline_info/execution_report_2026-09-04_11-35-35.html"
  touch "$d/results/$qc"
  echo "# why these values" > "$d/params.yaml"
}

# --- the three names, one per run --------------------------------------------
for pair in "a:software_versions.yml" \
            "b:nf_core_ampliseq_software_mqc_versions.yml" \
            "c:collated_versions.yml"; do
  name="${pair%%:*}" vfile="${pair#*:}"
  mkrun "$TMP/$name" "$vfile" "multiqc/multiqc_report.html"
  out=$("$S" "$TMP/$name/results" 2>&1)
  if has "$out" "nf-core/ampliseq" && has "$out" "dada2 1.38.0"; then
    ok "versions file named $vfile is found"
  else no "versions file named $vfile is found" "<<$out>>"; fi
done

# --- the quality report, wherever it landed ----------------------------------
mkrun "$TMP/nested" "software_versions.yml" "multiqc/star_salmon/multiqc_report.html"
out=$("$S" "$TMP/nested/results" 2>&1)
has "$out" "star_salmon/multiqc_report.html" \
  && ok "a quality report nested under a tool name is still found" \
  || no "a quality report nested under a tool name is still found" "<<$out>>"

# --- the retry ---------------------------------------------------------------
# The older attempt is made newer-looking by name and older by mtime, which is
# the trap: sorted by name it wins, and it is the one that did not finish.
R="$TMP/retried/results/pipeline_info"
mkrun "$TMP/retried" "software_versions.yml" "multiqc/multiqc_report.html"
: > "$R/execution_trace_2026-09-04_11-25-59.txt"   # the aborted attempt
touch -d "2020-01-01" "$R/execution_trace_2026-09-04_11-25-59.txt"
: > "$R/execution_trace_2026-09-04_11-35-35.txt"   # the real one
out=$("$S" "$TMP/retried/results" 2>&1)
if has "$out" "execution_trace_2026-09-04_11-35-35.txt" && has "$out" "was retried"; then
  ok "a retried run uses the newest attempt and says so"
else no "a retried run uses the newest attempt and says so" "<<$out>>"; fi

# The note is not decoration: silence here reads as "there was one attempt".
out2=$("$S" "$TMP/a/results" 2>&1)
has "$out2" "was retried" \
  && no "a run that was not retried says nothing about retries" "<<$out2>>" \
  || ok "a run that was not retried says nothing about retries"

# --- nothing to read ---------------------------------------------------------
mkdir -p "$TMP/bare/results"
out=$("$S" "$TMP/bare/results" 2>&1)
has "$out" "nothing here can say what produced it" \
  && ok "a tree with no pipeline_info says so instead of crashing" \
  || no "a tree with no pipeline_info says so instead of crashing" "<<$out>>"

"$S" "$TMP/does-not-exist" >/dev/null 2>&1
[ "$?" = 2 ] && ok "a missing directory exits 2" || no "a missing directory exits 2" "wrong rc"

# --- several runs at once ----------------------------------------------------
out=$("$S" --json "$TMP/a/results" "$TMP/nested/results" 2>&1)
n=$(python3 -c 'import json,sys; print(len(json.load(sys.stdin)["runs"]))' <<<"$out" 2>/dev/null)
[ "$n" = 2 ] && ok "several runs come back as a list - a project spans them" \
             || no "several runs come back as a list - a project spans them" "got $n"

# --- what counts as citable --------------------------------------------------
out=$("$S" --json "$TMP/a/results")
cit=$(python3 -c 'import json,sys; print(",".join(json.load(sys.stdin)["runs"][0]["citable_tools"]))' <<<"$out")
[ "$cit" = "dada2,fastqc" ] \
  && ok "runtimes are excluded and real tools are kept" \
  || no "runtimes are excluded and real tools are kept" "got '$cit'"

# The exclusion list is the one thing here that looks like v1's per-pipeline
# table, so it is pinned against the list this project already uses to define
# what a pipeline tool IS - read from that file rather than retyped, because a
# copy is what goes stale. A pipeline tool appearing in NOT_CITED would mean a
# real citation silently vanishing from a manuscript.
printf '%-62s ' "no pipeline tool hides in the not-cited list"
TOOLS=$(sed -n "s/^ *TOOLS='\\(.*\\)'$/\\1/p" "$ROOT/tests/no_per_pipeline_config.sh" | head -1)
if [ -z "$TOOLS" ]; then
  echo "FAIL: could not read the tool list from no_per_pipeline_config.sh"; fails=$((fails+1))
else
  overlap=$(python3 - "$ROOT/scripts/collect_provenance.py" "$TOOLS" <<'PY'
import re, sys
src = open(sys.argv[1], encoding="utf-8").read()
block = re.search(r"NOT_CITED = \{(.*?)\}", src, re.S).group(1)
excluded = set(re.findall(r'"([^"]+)"', block))
tools = set(sys.argv[2].split("|"))
print(",".join(sorted(excluded & tools)))
PY
)
  if [ -z "$overlap" ]; then echo ok
  else echo "FAIL: these are pipeline tools and must not be excluded: $overlap"; fails=$((fails+1)); fi
fi

echo
[ "$fails" = 0 ] && echo "OK: collect_provenance.py" || { echo "$fails failed"; exit 1; }
