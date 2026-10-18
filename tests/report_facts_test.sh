#!/bin/bash
# Tests for scripts/report_facts.py (013a): the facts report, filled only from
# files. TC ids refer to specs/013a-report-facts/test-case.md.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
S="$ROOT/scripts/report_facts.py"
B="$ROOT/scripts/build_package.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
export ABF_PIPELINE_FETCHER=off CITE_CURL=false
fails=0
ok() { printf '%-62s ok\n' "$1"; }
no() { printf '%-62s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }
section() { # file heading -> body of that "## heading" section
  awk -v h="## $2" '$0==h{on=1;next} /^## /{on=0} on' "$1"
}

# --- standard fixture --------------------------------------------------------
P="$TMP/proj"
for r in demo_20260101 demo_20260102; do
  mkdir -p "$P/runs/$r/results/pipeline_info"
  printf 'Workflow:\n  nf-core/demo: v1.0.0\n  Nextflow: 25.10.4\n' \
    > "$P/runs/$r/results/pipeline_info/software_versions.yml"
done
echo '{"input":"/data/lab/private/samples_v2.csv"}' \
  > "$P/runs/demo_20260101/results/pipeline_info/params_2026-01-01_00-00-00.json"
echo '{}' > "$P/runs/demo_20260102/results/pipeline_info/params_2026-01-02_00-00-00.json"
mkdir -p "$P/runs/demo_20260101/results/multiqc"
echo '<html></html>' > "$P/runs/demo_20260101/results/multiqc/multiqc_report.html"
mkdir -p "$P/analysis"
printf -- '- **richness**\n  id: richness\n  question: Q?\n  status: accepted\n' > "$P/analysis/analysis.md"
# a file shaped like an input_checksums output (TC-021)
printf '%s  samples_v2.csv\n' "$(printf 'a%.0s' $(seq 1 64))" > "$P/input_checksums.txt"
bash "$B" "$P" >/dev/null 2>&1
R="$P/submission/report.md"
PJ="$P/submission/provenance.json"
[ -s "$R" ] || { no "fixture builds report.md" "missing: $R"; echo "$fails failed"; exit 1; }

# TC-001
heads=$(grep -E '^#{1,2} ' "$R" | tr '\n' '|')
[ "$heads" = "## Runs|## Inputs|## Methods|## Quality control|## Interpretation|" ] \
  && ok "TC-001 five headings, in order, nothing else" || no "TC-001 headings" "$heads"

# TC-002
runs=$(section "$R" Runs)
if grep -q "run name: demo_20260101" <<<"$runs" && grep -q "run name: demo_20260102" <<<"$runs" &&
   [ "$(grep -c "pipeline: nf-core/demo" <<<"$runs")" = 2 ] && [ "$(grep -c "version: v1.0.0" <<<"$runs")" = 2 ] &&
   [ "$(grep -n "demo_20260101" <<<"$runs" | head -1 | cut -d: -f1)" -lt "$(grep -n "demo_20260102" <<<"$runs" | head -1 | cut -d: -f1)" ]
then ok "TC-002 both runs, nf-core/demo v1.0.0"; else no "TC-002" "$runs"; fi

# TC-003
H="$TMP/hand"; mkdir -p "$H/runs/r1/results" "$H/sub"
echo "METHODS-X" > "$H/methods.md"
cat > "$H/p.json" <<JSON
{"runs":[{"run_dir":"$H/runs/r1","results":"$H/runs/r1/results","platform_run_id":"abc123","workflow":{"nf-core/foo":"v9","Nextflow":"1"}}]}
JSON
python3 "$S" --provenance "$H/p.json" --methods "$H/methods.md" --out "$H/sub/report.md" 2>"$TMP/err"
grep -q "run id: abc123" "$H/sub/report.md" 2>/dev/null && ok "TC-003 run id shown" || no "TC-003" "$(cat "$TMP/err")"

# TC-004
[ "$(grep -c 'run id: not recorded' <<<"$runs")" = 2 ] && ok "TC-004 run id not recorded" || no "TC-004" "$runs"

# TC-005
bad=0
for k in start end status; do
  [ "$(grep -ciE "^[-* ]*$k:? " <<<"$runs")" = 2 ] || bad=1
  if grep -iE "^[-* ]*$k" <<<"$runs" | grep -qv 'not recorded'; then bad=1; fi
done
[ "$bad" = 0 ] && ok "TC-005 start/end/status not recorded" || no "TC-005" "$runs"

# TC-006
cat > "$H/p6.json" <<JSON
{"runs":[{"run_dir":"$H/runs/r1","results":"$H/runs/r1/results"}]}
JSON
python3 "$S" --provenance "$H/p6.json" --methods "$H/methods.md" --out "$H/sub/r6.md" 2>/dev/null
if grep -q 'pipeline: not recorded' "$H/sub/r6.md" && grep -q 'version: not recorded' "$H/sub/r6.md" \
   && ! grep -qi unknown "$H/sub/r6.md"; then ok "TC-006 no workflow -> not recorded"; else no "TC-006" "bad"; fi

# TC-007 / TC-008
inp=$(section "$R" Inputs)
if grep -q 'demo_20260101.*samples_v2.csv' <<<"$inp" && ! grep -q '/' <<<"$inp" && ! grep -q '/data/lab/private' "$R"
then ok "TC-007 input is a bare file name"; else no "TC-007" "$inp"; fi
grep -q 'demo_20260102.*not recorded' <<<"$inp" && ok "TC-008 missing input" || no "TC-008" "$inp"

# TC-009 / TC-010: strip blank edges of the section, compare with methods.md
meth=$(section "$R" Methods)
exp=$(cat "$P/submission/methods.md")
[ "$(printf '%s' "$meth" | sed '/./,$!d')" = "$exp" ] && ok "TC-009 methods verbatim" || no "TC-009" "differs"
"$ROOT/scripts/methods_text.py" --out "$TMP/mt.md" "$P"/runs/*/results >/dev/null 2>&1
if cmp -s "$TMP/mt.md" "$P/submission/methods.md" && [ "$(printf '%s' "$meth" | sed '/./,$!d')" = "$(cat "$TMP/mt.md")" ]
then ok "TC-010 methods equals methods_text.py output"; else no "TC-010" "differs"; fi

# TC-011 / TC-012
qc=$(section "$R" "Quality control")
l1=$(grep demo_20260101 <<<"$qc"); l2=$(grep demo_20260102 <<<"$qc")
if grep -qF '(../runs/demo_20260101/results/multiqc/multiqc_report.html) (outside this package)' <<<"$l1" \
   && [ -f "$P/submission/../runs/demo_20260101/results/multiqc/multiqc_report.html" ]
then ok "TC-011 relative MultiQC link"; else no "TC-011" "$l1"; fi
if grep -q 'MultiQC report not found' <<<"$l2" && ! grep -q '](' <<<"$l2"
then ok "TC-012 no MultiQC -> not found"; else no "TC-012" "$l2"; fi

# TC-013
cat > "$H/p13.json" <<JSON
{"runs":[{"run_dir":"$H/runs/r1","results":"$H/runs/r1/results","quality_report":"$H/gone/multiqc_report.html"}]}
JSON
python3 "$S" --provenance "$H/p13.json" --methods "$H/methods.md" --out "$H/sub/r13.md" 2>/dev/null
if grep -q 'MultiQC report not found' "$H/sub/r13.md" && ! grep -q '](' "$H/sub/r13.md"
then ok "TC-013 deleted report -> not found"; else no "TC-013" "bad"; fi

# TC-014
mkdir -p "$H/runs/r1/results/deep"; echo x > "$H/runs/r1/results/deep/multiqc_report.html"
python3 "$S" --provenance "$H/p6.json" --methods "$H/methods.md" --out "$H/sub/r14.md" 2>/dev/null
grep -qF '](../runs/r1/results/deep/multiqc_report.html) (outside this package)' "$H/sub/r14.md" \
  && ok "TC-014 finds report itself" || no "TC-014" "bad"

# TC-015
interp=$(section "$R" Interpretation | grep -v '^[[:space:]]*$')
[ "$(wc -l <<<"$interp")" = 1 ] && grep -qi 'you' <<<"$interp" && ok "TC-015 one-line note only" || no "TC-015" "$interp"

# TC-016
python3 "$S" --provenance "$PJ" --methods "$P/submission/methods.md" --out "$TMP/a.md" 2>/dev/null
python3 "$S" --provenance "$PJ" --methods "$P/submission/methods.md" --out "$TMP/b.md" 2>/dev/null
if [ -s "$TMP/a.md" ] && cmp -s "$TMP/a.md" "$TMP/b.md" && ! grep -qE '[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:' "$TMP/a.md" \
   && ! grep -qF "$(hostname)" "$TMP/a.md"
then ok "TC-016 deterministic"; else no "TC-016" "differs"; fi

# TC-017
if grep -qF "$TMP" "$R" || grep -qF "$HOME" "$R"; then no "TC-017 no absolute paths" "found"; else ok "TC-017 no absolute paths"; fi

# TC-018
echo "HAND-WRITTEN-MARKER-7" > "$H/m18.md"
python3 "$S" --provenance "$H/p.json" --methods "$H/m18.md" --out "$H/sub/r18.md" 2>/dev/null
if section "$H/sub/r18.md" Methods | grep -q HAND-WRITTEN-MARKER-7 && grep -q 'pipeline: nf-core/foo' "$H/sub/r18.md" \
   && grep -q 'version: v9' "$H/sub/r18.md"; then ok "TC-018 reads the given files"; else no "TC-018" "bad"; fi

# TC-019
echo "{\"runs\":[{\"results\":\"$H/runs/r1/results\",\"run_dir\":\"$H/runs/r1\"}]}" > "$H/p19.json"
python3 "$S" --provenance "$H/p19.json" --methods "$H/methods.md" --out "$H/sub/r19.md" 2>"$TMP/e19"; rc=$?
if [ "$rc" = 0 ] && ! grep -q Traceback "$TMP/e19" && grep -q 'run name: r1' "$H/sub/r19.md" \
   && ! { grep -E '^- (pipeline|version|run id|start|end|status):' "$H/sub/r19.md" | grep -qv 'not recorded'; }
then ok "TC-019 sparse run"; else no "TC-019" "rc=$rc"; fi

# TC-020
if grep -qiE 'urllib|http\.client|socket|requests|anthropic|openai|subprocess' "$S" 2>/dev/null; then
  no "TC-020 no network/model" "found"
else
  imps=$(grep -E '^(import|from) ' "$S" 2>/dev/null | awk '{print $2}' | sort -u | tr '\n' ' ')
  [ "$imps" = "argparse json os sys " ] && ok "TC-020 stdlib only, no network" || no "TC-020" "$imps"
fi

# TC-021
if grep -qE '[0-9a-f]{64}' "$R" || grep -qiE 'checksum|sha256' <<<"$inp"; then no "TC-021 no checksums" "found"; else ok "TC-021 no checksums"; fi

# TC-C06
if head -30 "$S" 2>/dev/null | grep -q 'require_python.sh' && head -30 "$S" | grep -q 'require_python ||'
then ok "TC-C06 require_python used"; else no "TC-C06" "missing"; fi

# TC-030 / TC-C08: build_package.sh runs report_facts.py directly, so git must
# record it as executable (a 100644 file fails with Permission denied on Linux/CI)
mode=$(git -C "$ROOT" ls-files -s -- scripts/report_facts.py 2>/dev/null | awk '{print $1}')
if [ -z "$mode" ]; then ok "TC-030 exec bit (not a git checkout, skipped)"
elif [ "$mode" = 100755 ]; then ok "TC-030 report_facts.py is executable in git"
else no "TC-030 report_facts.py git mode" "$mode"; fi

echo
[ "$fails" = 0 ] && echo "OK: report_facts.py" || { echo "$fails failed"; exit 1; }
