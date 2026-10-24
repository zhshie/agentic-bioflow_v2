#!/bin/bash
# Tests for scripts/build_package.sh.
#
# Two properties matter more than the file list.
#
# The first is that a gap stays visible. A plan entry whose figure was never
# produced, and a figure no plan entry claims, both leave a visible
# `[GAP: ...]` line in the manuscript (an HTML comment until #32, which a
# rendered document drops). Silence there would produce a document that looks complete and
# is missing a result nobody asked about again.
#
# The second is that the .qmd carries no executable code. The figures are
# already files by the time this runs, so rendering needs Quarto and nothing
# else - no R, no knitr. That is what lets the document render on a machine
# with none of them, which is most of the machines involved.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/build_package.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
export ABF_PIPELINE_FETCHER=off   # no network in tests (#4); methods_text_fetch_test.sh covers fetching
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

# nf-prov's own crate (PITFALLS 32 shape, trimmed) - present for this run so
# the RO-Crate packaging step (scripts/package_crate.py) has something to
# nest and copy verbatim.
cat > "$P/runs/demo_20260101/results/pipeline_info/ro-crate-metadata.json" <<'JSON'
{"@context":"https://w3id.org/ro/crate/1.1/context","@graph":[
{"@id":"ro-crate-metadata.json","@type":"CreativeWork","about":{"@id":"./"},
 "conformsTo":[{"@id":"https://w3id.org/ro/crate/1.1"}]},
{"@id":"./","@type":"Dataset","datePublished":"2026-01-01",
 "conformsTo":[{"@id":"https://w3id.org/ro/wfrun/process/0.1"}],
 "hasPart":[{"@id":"main.nf"}]},
{"@id":"main.nf","@type":"File"}
]}
JSON

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

# The package describes itself as an RO-Crate too (proposal R5,
# scripts/package_crate.py) - a thin integration check; package_crate.py's
# own suite (tests/package_crate_test.sh) covers its behaviour in depth.
CRATE="$P/submission/ro-crate-metadata.json"
python3 -c "
import json
d = json.load(open('$CRATE'))
assert d['@context'] == 'https://w3id.org/ro/crate/1.1/context'
graph = {e['@id']: e for e in d['@graph']}
assert graph['./']['name']
assert {'@id': 'runs/demo_20260101/'} in graph['./']['hasPart']
assert 'license' not in graph['./']
" >/tmp/build_pkg_crate_err.$$ 2>&1 \
  && ok "the package itself is a valid RO-Crate that nests the run's crate" \
  || no "the package itself is a valid RO-Crate that nests the run's crate" "$(cat /tmp/build_pkg_crate_err.$$)"
rm -f /tmp/build_pkg_crate_err.$$

cmp -s "$P/runs/demo_20260101/results/pipeline_info/ro-crate-metadata.json" \
       "$P/submission/runs/demo_20260101/ro-crate-metadata.json" \
  && ok "nf-prov's run crate is carried into the package byte-identical" \
  || no "nf-prov's run crate is carried into the package byte-identical" "missing or differs"

grep -qi "no license is declared" "$P/submission/README.md" \
  && ok "README states the license gap" \
  || no "README states the license gap" "not found"

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

# No working Python on this machine - the Windows case (PITFALLS 20c). All
# three candidate names shadowed with stubs that fail, the shape of a Git
# Bash PATH whose only "python" is the unusable Microsoft Store stub.
# analysis.md was just deleted above to exercise the "no plan" refusal, so it
# has to come back first or this would hit that refusal instead.
cat > "$P/analysis/analysis.md" <<'MD'
- **richness**
  id: richness
  question: Does treatment change richness?
  status: accepted
MD
NOPY="$TMP/nopy_bin"; mkdir -p "$NOPY"
for name in python3 python py; do
    printf '#!/bin/bash\nexit 49\n' > "$NOPY/$name"
    chmod +x "$NOPY/$name"
done
out=$(PATH="$NOPY:$PATH" CITE_CURL=false bash "$S" "$P" 2>&1); rc=$?
[ "$rc" != 0 ] && ok "no working python: refuses rather than crashing partway" \
  || no "no working python: refuses rather than crashing partway" "rc=0 <<$out>>"
grep -qF "no working Python on this machine" <<<"$out" \
  && ok "...and says so in those words" \
  || no "...and says so in those words" "<<$out>>"
grep -qF "python3" <<<"$out" \
  && ok "...and names what it tried" \
  || no "...and names what it tried" "<<$out>>"
grep -qF "this shell is unsupported" <<<"$out" \
  && no "...never blames the shell" "found the wrong phrase" \
  || ok "...never blames the shell"

# ---------------------------------------------------------------------------
# Issue #5: skills/downstream/SKILL.md step 3b presents analysis.md's fields as a
# column list, which reads naturally as a markdown table - and a
# table-formatted analysis.md matched zero entries against the old
# heading/bullet-block parser, with no error. The Results section came out
# looking complete and was silently empty. The parser now reads a table too,
# still reads the original block form, and hard-fails (rather than writing a
# blank Results section) when it reads neither.
P2="$TMP/proj_table"
mkdir -p "$P2/runs/demo_20260101/results/pipeline_info" "$P2/analysis/figures"
cp "$P/runs/demo_20260101/results/pipeline_info/software_versions.yml" \
   "$P2/runs/demo_20260101/results/pipeline_info/"
echo '{}' > "$P2/runs/demo_20260101/results/pipeline_info/params_2026-01-01_00-00-00.json"
echo "# because the reads are long" > "$P2/runs/demo_20260101/params.yaml"
echo x > "$P2/analysis/figures/richness.png"

# --- the table format downstream.md's own worked example reads like ----------
cat > "$P2/analysis/analysis.md" <<'MD'
| id | question | source | method | why | status |
|---|---|---|---|---|---|
| richness | Does treatment change richness? | demo_20260101/results/richness.tsv | Shannon index | the background section asks about diversity | accepted |
MD
out=$(CITE_CURL=false bash "$S" "$P2" 2>&1); rc=$?
Q2="$P2/submission/manuscript.qmd"
[ "$rc" = 0 ] && ok "table-formatted analysis.md: build succeeds" \
  || no "table-formatted analysis.md: build succeeds" "rc=$rc <<$out>>"
grep -qF "Does treatment change richness?" "$Q2" \
  && ok "table-formatted analysis.md: the question becomes the caption" \
  || no "table-formatted analysis.md: the question becomes the caption" "not in the qmd"
grep -qF "figures/richness.png" "$Q2" \
  && ok "table-formatted analysis.md: the figure is matched by id" \
  || no "table-formatted analysis.md: the figure is matched by id" "not in the qmd"

# --- neither format: a plan file that is neither a table nor id:/question: --
cat > "$P2/analysis/analysis.md" <<'MD'
We looked at richness and it seemed fine, no strong pattern either way.
MD
out=$(CITE_CURL=false bash "$S" "$P2" 2>&1); rc=$?
[ "$rc" != 0 ] && ok "unparseable analysis.md: hard fails rather than building" \
  || no "unparseable analysis.md: hard fails rather than building" "rc=0 <<$out>>"
grep -qF "matched 0 plan entries" <<<"$out" \
  && ok "...and says it matched 0 entries" \
  || no "...and says it matched 0 entries" "<<$out>>"
grep -qF "id/question/source/method/why/status" <<<"$out" \
  && ok "...and says what it expected" \
  || no "...and says what it expected" "<<$out>>"
printf '%-62s ' "...and does not leave a stale manuscript.qmd claiming success"
if grep -qF "wrote     submission/manuscript.qmd" <<<"$out"; then
  echo "FAIL: printed 'wrote' after failing to parse the plan"; fails=$((fails+1))
else echo ok; fi

# ---------------------------------------------------------------------------
# 013a: report.md, the facts report. Built from files only; a rebuild must not
# overwrite one the person has edited (R2: sha256 kept in .report.md.sha256).
P3="$TMP/proj_report"
for r in demo_20260101 demo_20260102; do
  mkdir -p "$P3/runs/$r/results/pipeline_info"
  printf 'Workflow:\n  nf-core/demo: v1.0.0\n  Nextflow: 25.10.4\n' \
    > "$P3/runs/$r/results/pipeline_info/software_versions.yml"
done
echo '{"input":"/data/lab/private/samples_v2.csv"}' \
  > "$P3/runs/demo_20260101/results/pipeline_info/params_2026-01-01_00-00-00.json"
echo '{}' > "$P3/runs/demo_20260102/results/pipeline_info/params_2026-01-02_00-00-00.json"
mkdir -p "$P3/runs/demo_20260101/results/multiqc" "$P3/analysis"
echo '<html></html>' > "$P3/runs/demo_20260101/results/multiqc/multiqc_report.html"
printf -- '- **richness**\n  id: richness\n  question: Q?\n  status: accepted\n' > "$P3/analysis/analysis.md"
SUB="$P3/submission"
sha() { sha256sum "$1" 2>/dev/null | cut -d' ' -f1; }

# TC-030
out=$(CITE_CURL=false bash "$S" "$P3" 2>&1); rc=$?
if [ "$rc" = 0 ] && [ -s "$SUB/report.md" ] && [ "$(grep -cE '^## (Runs|Inputs|Methods|Quality control|Interpretation)$' "$SUB/report.md")" = 5 ]
then ok "TC-030 report.md is in the package"; else no "TC-030 report.md is in the package" "rc=$rc <<$out>>"; fi

# TC-031
[ "$(tr -d ' \n' < "$SUB/.report.md.sha256" 2>/dev/null | head -c 64)" = "$(sha "$SUB/report.md")" ] \
  && ok "TC-031 .report.md.sha256 holds the hash of report.md" || no "TC-031 hash file" "missing or wrong"

# TC-032
cp "$SUB/report.md" "$TMP/report.first"
err=$(CITE_CURL=false bash "$S" "$P3" 2>&1 >/dev/null)
if cmp -s "$TMP/report.first" "$SUB/report.md" && [ ! -e "$SUB/report.facts.md" ] && ! grep -qF "report.facts.md" <<<"$err"
then ok "TC-032 untouched report.md is rewritten in place, no report.facts.md"; else no "TC-032" "differs or report.facts.md present"; fi

# TC-033
echo '{"input":"/data/lab/private/samples_v3.csv"}' \
  > "$P3/runs/demo_20260101/results/pipeline_info/params_2026-01-01_00-00-00.json"
CITE_CURL=false bash "$S" "$P3" >/dev/null 2>&1
if grep -q 'samples_v3.csv' "$SUB/report.md" && [ ! -e "$SUB/report.facts.md" ] \
   && [ "$(tr -d ' \n' < "$SUB/.report.md.sha256" | head -c 64)" = "$(sha "$SUB/report.md")" ]
then ok "TC-033 unedited report.md follows the data; hash refreshed"; else no "TC-033" "not updated"; fi

# TC-034
rm "$SUB/report.md"
CITE_CURL=false bash "$S" "$P3" >/dev/null 2>&1
[ -s "$SUB/report.md" ] && [ ! -e "$SUB/report.facts.md" ] \
  && ok "TC-034 a missing report.md is written again" || no "TC-034" "not rewritten"

# TC-035..037, TC-041: edited report.md
printf 'Sample A has higher richness.\n' >> "$SUB/report.md"
cp "$SUB/report.md" "$TMP/report.edited"
echo '{"input":"/data/lab/private/samples_v4.csv"}' \
  > "$P3/runs/demo_20260101/results/pipeline_info/params_2026-01-01_00-00-00.json"
err=$(CITE_CURL=false bash "$S" "$P3" 2>&1 >/dev/null)
cmp -s "$TMP/report.edited" "$SUB/report.md" && grep -q 'Sample A has higher richness' "$SUB/report.md" \
  && ok "TC-035 an edited report.md is kept byte for byte" || no "TC-035" "edited report.md changed"
if [ -s "$SUB/report.facts.md" ] && grep -q 'samples_v4.csv' "$SUB/report.facts.md" \
   && ! grep -q 'Sample A has higher richness' "$SUB/report.facts.md"
then ok "TC-036 the fresh report goes to report.facts.md"; else no "TC-036" "report.facts.md missing or stale"; fi
lines=$(grep -F "report.facts.md" <<<"$err")
if [ "$(wc -l <<<"$lines")" = 1 ] && grep -qF "report.md" <<<"$lines" && grep -qF "report.facts.md" <<<"$lines"
then ok "TC-037 exactly one stderr line names both files"; else no "TC-037" "<<$err>>"; fi

# TC-041: MultiQC is linked, never copied
if [ -z "$(find "$SUB" -name 'multiqc_report.html' 2>/dev/null)" ] && grep -qF '(outside this package)' "$SUB/report.md"
then ok "TC-041 MultiQC is not copied into the package"; else no "TC-041" "copied or not marked"; fi

# TC-039: an old report.facts.md is replaced, not accumulated
echo OLD > "$SUB/report.facts.md"
CITE_CURL=false bash "$S" "$P3" >/dev/null 2>&1
if ! grep -q OLD "$SUB/report.facts.md" && [ -z "$(ls "$SUB" | grep -E '^report\.facts\.md\.')" ]
then ok "TC-039 old report.facts.md is overwritten"; else no "TC-039" "OLD kept or extras"; fi

# TC-038: report.md with no hash file counts as edited
rm -f "$SUB/.report.md.sha256" "$SUB/report.facts.md"
echo "mine" > "$SUB/report.md"
err=$(CITE_CURL=false bash "$S" "$P3" 2>&1 >/dev/null)
if [ "$(cat "$SUB/report.md")" = "mine" ] && [ -s "$SUB/report.facts.md" ] \
   && [ "$(grep -cF report.facts.md <<<"$err")" = 1 ]
then ok "TC-038 report.md without a hash file is treated as edited"; else no "TC-038" "<<$err>>"; fi

# TC-040
sed -n '1,45p' "$S" | grep -E '^#   report\.md.*report_facts\.py' >/dev/null \
  && ok "TC-040 header comment lists report.md" || no "TC-040" "header does not list report.md"

# ---------------------------------------------------------------------------
# Issue #12 (finish-accept-gate): only entries the user accepted are packaged.
# TC-G01..G28 in specs/finish-accept-gate/test-case.md.
# gate_proj <name> : a minimal project with one run, no analysis.md yet.
gate_proj() {
    local d="$TMP/gate_$1"
    mkdir -p "$d/runs/demo_20260101/results/pipeline_info" "$d/analysis"
    cp "$P/runs/demo_20260101/results/pipeline_info/software_versions.yml" \
       "$P/runs/demo_20260101/results/pipeline_info/params_2026-01-01_00-00-00.json" \
       "$d/runs/demo_20260101/results/pipeline_info/"
    echo "$d"
}
blk() { printf -- '- **%s**\n  id: %s\n  question: Q-%s?\n  status: %s\n' "$1" "$1" "$1" "$2"; }
run_gate() { out=$(CITE_CURL=false bash "$S" "$@" 2>&1 >/dev/null); rc=$?; }

# TC-G01a-e
G=$(gate_proj g01); blk richness proposed > "$G/analysis/analysis.md"
run_gate "$G"
[ "$rc" = 2 ] && ok "TC-G01a proposed entry: exit 2" || no "TC-G01a" "rc=$rc <<$out>>"
{ grep -qF "refusing to build" <<<"$out" && grep -qF "not accepted" <<<"$out" \
  && grep -qF richness <<<"$out" && grep -qF "status: proposed" <<<"$out"; } \
  && ok "TC-G01b fixed substrings" || no "TC-G01b" "<<$out>>"
[ "$(sed -n 1p <<<"$out")" = "build_package.sh: refusing to build - 1 of 1 entries in $G/analysis/analysis.md are not accepted:" ] \
  && [ "$(sed -n 2p <<<"$out")" = "  richness   status: proposed" ] \
  && ok "TC-G01c first two lines verbatim" || no "TC-G01c" "<<$out>>"
{ grep -qF "Moving on to" <<<"$out" && grep -qF "status: accepted" <<<"$out"; } \
  && ok "TC-G01d says what to do" || no "TC-G01d" "<<$out>>"
{ grep -qF "Nothing was written to" <<<"$out" && [ ! -e "$G/submission" ]; } \
  && ok "TC-G01e nothing written, submission/ absent" || no "TC-G01e" "<<$out>>"

# TC-G16: the issue's own scene - four entries, none accepted
G=$(gate_proj g16); for i in richness evenness beta pcoa; do blk $i proposed; done > "$G/analysis/analysis.md"
run_gate "$G"
all4=1; for i in richness evenness beta pcoa; do grep -qF "$i" <<<"$out" || all4=0; done
{ [ "$rc" = 2 ] && sed -n 1p <<<"$out" | grep -qF "4 of 4 entries" && [ ! -e "$G/submission" ] \
  && [ "$(grep -cF 'status: proposed' <<<"$out")" -ge 4 ] && [ "$all4" = 1 ]; } \
  && ok "TC-G16 four unaccepted entries all listed" || no "TC-G16" "rc=$rc <<$out>>"

# TC-G02a-c
G=$(gate_proj g02); { blk richness accepted; blk evenness revised; } > "$G/analysis/analysis.md"
run_gate "$G"
{ [ "$rc" = 2 ] && sed -n 1p <<<"$out" | grep -qF "1 of 2 entries" \
  && grep -qF evenness <<<"$out" && grep -qF "status: revised" <<<"$out"; } \
  && ok "TC-G02a one of two refused" || no "TC-G02a" "rc=$rc <<$out>>"
! grep -qF richness <<<"$out" && ok "TC-G02b accepted entry not listed" || no "TC-G02b" "<<$out>>"
[ ! -e "$G/submission" ] && ok "TC-G02c no submission/" || no "TC-G02c" "exists"

# TC-G03: block with no status line
G=$(gate_proj g03); printf -- '- **richness**\n  id: richness\n  question: Q?\n' > "$G/analysis/analysis.md"
run_gate "$G"
{ [ "$rc" = 2 ] && grep -qF "status: (none)" <<<"$out"; } && ok "TC-G03 missing status line" || no "TC-G03" "rc=$rc <<$out>>"

# TC-G04: table without a status column
G=$(gate_proj g04); printf '| id | question |\n|---|---|\n| fig1 | Q? |\n' > "$G/analysis/analysis.md"
run_gate "$G"
{ [ "$rc" = 2 ] && grep -qF fig1 <<<"$out" && grep -qF "status: (none)" <<<"$out"; } \
  && ok "TC-G04 table without status column" || no "TC-G04" "rc=$rc <<$out>>"

# TC-G05 / G08 / G17: values that are not exactly accepted/done
for pair in "G05:approved" "G08:accepted-ish" "G17:not accepted"; do
    tc=${pair%%:*}; val=${pair#*:}
    G=$(gate_proj "g_$tc"); blk richness "$val" > "$G/analysis/analysis.md"
    run_gate "$G"
    { [ "$rc" = 2 ] && grep -qF "status: $val" <<<"$out" && [ ! -e "$G/submission" ]; } \
      && ok "TC-$tc status '$val' is not accepted" || no "TC-$tc" "rc=$rc <<$out>>"
done
# TC-G18: empty status
G=$(gate_proj g18); printf -- '- **richness**\n  id: richness\n  question: Q?\n  status:\n' > "$G/analysis/analysis.md"
run_gate "$G"
{ [ "$rc" = 2 ] && grep -qF richness <<<"$out" && grep -qF "not accepted" <<<"$out" && [ ! -e "$G/submission" ]; } \
  && ok "TC-G18 empty status" || no "TC-G18" "rc=$rc <<$out>>"

# TC-G11: row without an id
G=$(gate_proj g11)
printf '| id | question | status |\n|---|---|---|\n|  | Orphan question | proposed |\n| fig1 | Q? | accepted |\n' > "$G/analysis/analysis.md"
run_gate "$G"
{ [ "$rc" = 2 ] && grep -qF "(no id)" <<<"$out"; } && ok "TC-G11 row without id" || no "TC-G11" "rc=$rc <<$out>>"

# TC-G06a/b: accepted + done build
G=$(gate_proj g06); { blk richness accepted; blk evenness done; } > "$G/analysis/analysis.md"
out=$(CITE_CURL=false bash "$S" "$G" 2>/dev/null); rc=$?
{ [ "$rc" = 0 ] && grep -qF "wrote     submission/manuscript.qmd" <<<"$out" && [ -f "$G/submission/manuscript.qmd" ]; } \
  && ok "TC-G06a accepted+done build" || no "TC-G06a" "rc=$rc"
{ grep -qF "Q-richness?" "$G/submission/manuscript.qmd" && grep -qF "Q-evenness?" "$G/submission/manuscript.qmd"; } \
  && ok "TC-G06b both questions in the qmd" || no "TC-G06b" "missing"
# TC-G23: no 'ready vs assembled' wording (the issue's second suggestion is out of scope)
grep -qE 'still need prose|not yet a finished document|placeholder\(s\)' <<<"$out" \
  && no "TC-G23" "new wording appeared" || ok "TC-G23 success message unchanged"

# TC-G07: case and whitespace
G=$(gate_proj g07); printf -- '- **richness**\n  id: richness\n  question: Q?\n  status:  Accepted  \n' > "$G/analysis/analysis.md"
run_gate "$G"
{ [ "$rc" = 0 ] && [ -f "$G/submission/manuscript.qmd" ]; } && ok "TC-G07 'Accepted ' passes" || no "TC-G07" "rc=$rc <<$out>>"

# TC-G09a-c: a refused rerun leaves the earlier package untouched
G=$(gate_proj g09); { blk richness accepted; blk evenness accepted; } > "$G/analysis/analysis.md"
CITE_CURL=false bash "$S" "$G" >/dev/null 2>&1
mkdir -p "$TMP/g09_keep"; cp "$G/submission/manuscript.qmd" "$G/submission/report.md" "$G/submission/provenance.json" "$TMP/g09_keep/"
rm -f "$G/submission/report.facts.md"
{ blk richness accepted; blk evenness proposed; } > "$G/analysis/analysis.md"
run_gate "$G"
[ "$rc" = 2 ] && ok "TC-G09a rerun with a proposed entry: exit 2" || no "TC-G09a" "rc=$rc <<$out>>"
{ cmp -s "$G/submission/manuscript.qmd" "$TMP/g09_keep/manuscript.qmd" \
  && cmp -s "$G/submission/report.md" "$TMP/g09_keep/report.md" \
  && cmp -s "$G/submission/provenance.json" "$TMP/g09_keep/provenance.json"; } \
  && ok "TC-G09b earlier files byte-identical" || no "TC-G09b" "changed"
[ ! -e "$G/submission/report.facts.md" ] && ok "TC-G09c no new report.facts.md" || no "TC-G09c" "appeared"

# TC-G10a/b: --render passes the gate first
G=$(gate_proj g10); blk richness proposed > "$G/analysis/analysis.md"
run_gate --render "$G"
[ "$rc" = 2 ] && ok "TC-G10a --render refused with 2, not 3" || no "TC-G10a" "rc=$rc"
{ grep -qF "refusing to build" <<<"$out" && ! grep -qF Positron <<<"$out"; } \
  && ok "TC-G10b refusal message, not the quarto one" || no "TC-G10b" "<<$out>>"

# TC-G12: the existing runs check still comes first
G="$TMP/gate_g12"; mkdir -p "$G/runs" "$G/analysis"; echo "-" > "$G/runs/x"; blk richness proposed > "$G/analysis/analysis.md"
run_gate "$G"
{ [ "$rc" = 2 ] && grep -qF "at least one run" <<<"$out" && ! grep -qF "refusing to build" <<<"$out"; } \
  && ok "TC-G12 no runs wins over the gate" || no "TC-G12" "rc=$rc <<$out>>"

# TC-G13: python lookup still reports itself the same way
G=$(gate_proj g13); blk richness proposed > "$G/analysis/analysis.md"
out=$(PATH="$NOPY:$PATH" CITE_CURL=false bash "$S" "$G" 2>&1); rc=$?
{ [ "$rc" != 0 ] && grep -qF "no working Python on this machine" <<<"$out"; } \
  && ok "TC-G13 no python message unchanged" || no "TC-G13" "rc=$rc <<$out>>"

# TC-G14a/b: nothing parseable is still issue #5's exit 1, not a gate refusal
G=$(gate_proj g14); echo "We looked at richness and it seemed fine." > "$G/analysis/analysis.md"
run_gate "$G"
{ [ "$rc" = 1 ] && grep -qF "matched 0 plan entries" <<<"$out"; } && ok "TC-G14a exit 1 for 0 entries" || no "TC-G14a" "rc=$rc <<$out>>"
{ ! grep -qF "not accepted" <<<"$out" && ! grep -qF "0 of 0" <<<"$out"; } && ok "TC-G14b no gate wording" || no "TC-G14b" "<<$out>>"

# TC-G25/G26: no bypass flag
G=$(gate_proj g25); blk richness proposed > "$G/analysis/analysis.md"
for f in --force --allow-unaccepted; do
    run_gate "$f" "$G"
    { [ "$rc" = 2 ] && grep -qF "unknown option" <<<"$out" && [ ! -e "$G/submission" ]; } \
      && ok "TC-G25/26 $f is not a flag" || no "TC-G25/26 $f" "rc=$rc <<$out>>"
done

# TC-G27: a missing figure is the gap mechanism's business, not the gate's
G=$(gate_proj g27); blk richness accepted > "$G/analysis/analysis.md"
run_gate "$G"
{ ! grep -qF "refusing to build" <<<"$out" && ! grep -qF "not accepted" <<<"$out"; } \
  && ok "TC-G27 accepted entry without a figure is not gated" || no "TC-G27" "<<$out>>"

# TC-G15a/b: the instructions say what to set
grep -qF 'status: accepted' "$(dirname "$S")/../skills/finish/SKILL.md" \
  && ok "TC-G15a finish SKILL.md names status: accepted" || no "TC-G15a" "missing"
grep -qF 'status: accepted' "$(dirname "$S")/../docs/FINISH.md" \
  && ok "TC-G15b docs/FINISH.md names status: accepted" || no "TC-G15b" "missing"

echo
[ "$fails" = 0 ] && echo "OK: build_package.sh" || { echo "$fails failed"; exit 1; }
