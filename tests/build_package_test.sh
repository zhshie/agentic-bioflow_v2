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
# Issue #5: commands/downstream.md step 3b presents analysis.md's fields as a
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
# Issue #12 part 2: the success line says "scaffold", and entries that are not
# accepted are listed (they still go into Results; nothing is refused).
mkp() {  # mkp <name>: a project whose analysis.md is read from stdin
  local d="$TMP/$1"
  mkdir -p "$d/runs/demo_20260101/results/pipeline_info" "$d/analysis/figures"
  cp "$P/runs/demo_20260101/results/pipeline_info/software_versions.yml" \
     "$d/runs/demo_20260101/results/pipeline_info/"
  echo '{}' > "$d/runs/demo_20260101/results/pipeline_info/params_2026-01-01_00-00-00.json"
  cat > "$d/analysis/analysis.md"
}
runp() { out=$(CITE_CURL=false bash "$S" "$TMP/$1" 2>&1); rc=$?; }
NA=' - still in Results; accept it in analysis.md or remove it before submitting'
chk() { grep -qF -- "$2" <<<"$out" && ok "$1" || no "$1" "missing <<$2>> in <<$out>>"; }
nochk() { grep -qF -- "$2" <<<"$out" && no "$1" "unexpected <<$2>>" || ok "$1"; }
HDR='| id | question | source | method | why | status |
|---|---|---|---|---|---|'

# TC-001, TC-005, TC-006, TC-018
mkp s1 <<MD
$HDR
| richness | Q1? | s | m | w | accepted |
| evenness | Q2? | s | m | w | accepted |
MD
runp s1
chk "TC-001 scaffold line with N=2" "wrote     submission/manuscript.qmd (scaffold: 2 Results section(s) and the Discussion still need prose)"
nochk "TC-018 all accepted: no not-accepted line" "not accepted"
R="$TMP/s1/submission/README.md"
l=$(grep -n 'scaffold' "$R" | head -1 | cut -d: -f1); h=$(grep -n '^## How to reproduce the runs' "$R" | cut -d: -f1)
{ [ -n "$l" ] && [ -n "$h" ] && [ "$l" -lt "$h" ] && sed -n "${l}p" "$R" | grep -qF '2 Results section(s)'; } \
  && ok "TC-005 README says scaffold before the reproduce heading" || no "TC-005 README says scaffold" "l=$l h=$h"
miss=""
for f in provenance.json methods.md manuscript.qmd README.md ro-crate-metadata.json figures scripts; do
  [ -e "$TMP/s1/submission/$f" ] || miss="$miss $f"; done
[ -z "$miss" ] && ok "TC-006 same files are written" || no "TC-006 same files are written" "missing:$miss"

# TC-002, 010-016, 030
mkp s2 <<MD
$HDR
| acc | Qa? | s | m | w | accepted |
| prop | Qp? | s | m | w | proposed |
| rej | Qr? | s | m | w | rejected |
| none | Qn? | s | m | w |  |
MD
runp s2
chk "TC-002 N=4" "scaffold: 4 Results section(s) and the Discussion still need prose"
[ "$(grep -c "^\[GAP: Results for '" "$TMP/s2/submission/manuscript.qmd")" = 4 ] \
  && ok "TC-002/016 four Results placeholders, none dropped" || no "TC-016" "count differs"
chk "TC-010 proposed" "not accepted prop: status proposed$NA"
chk "TC-011 rejected" "not accepted rej: status rejected$NA"
chk "TC-012 empty shows (none)" "not accepted none: status (none)$NA"
nochk "TC-014 accepted entry not listed" "not accepted acc"
[ "$(grep -c '^not accepted' <<<"$out")" = 3 ] && ok "TC-014 exactly three lines" || no "TC-014" "count"
w=$(grep -n 'wrote     submission/manuscript.qmd' <<<"$out" | head -1 | cut -d: -f1)
f=$(grep -n '^not accepted' <<<"$out" | head -1 | cut -d: -f1)
[ -n "$w" ] && [ -n "$f" ] && [ "$w" -lt "$f" ] && ok "TC-015 listed after the manuscript line" || no "TC-015" "w=$w f=$f"
for i in acc prop rej none; do
  grep -qF "[GAP: Results for '$i' not written yet" "$TMP/s2/submission/manuscript.qmd" \
    && ok "TC-016 $i still in Results" || no "TC-016 $i still in Results" "gone"; done
[ "$rc" = 0 ] && [ -s "$TMP/s2/submission/manuscript.qmd" ] && [ -s "$TMP/s2/submission/README.md" ] \
  && ok "TC-030 unaccepted entries do not stop the build" || no "TC-030" "rc=$rc"

# TC-013
mkp s3 <<MD
$HDR
| rev | Qv? | s | m | w | revised |
MD
runp s3; chk "TC-013 revised" "not accepted rev: status revised$NA"

# TC-017
mkp s4 <<MD
$HDR
| a1 | Q? | s | m | w | Accepted |
| a2 | Q? | s | m | w |  accepted  |
MD
runp s4; nochk "TC-017 Accepted / ' accepted ' count as accepted" "not accepted"

# TC-019
mkp s5 <<MD
$HDR
| cap | Q? | s | m | w |  Proposed  |
MD
runp s5; chk "TC-019 status printed as written, trimmed" "not accepted cap: status Proposed - still in Results;"

# TC-003, TC-020
mkp s6 <<MD
$HDR
| one | Q1? | s | m | w | accepted |
|  | idless question | s | m | w | proposed |
| two | Q2? | s | m | w | accepted |
MD
runp s6
chk "TC-003 id-less row not counted" "scaffold: 2 Results section(s)"
grep -qF "[GAP: a plan row has no id" "$TMP/s6/submission/manuscript.qmd" \
  && ok "TC-003 id-less GAP still there" || no "TC-003" "GAP gone"
nochk "TC-020 id-less row gets no not-accepted line" "not accepted"

# TC-004
mkp s7 <<MD
$HDR
|  | only a question | s | m | w | accepted |
MD
runp s7
chk "TC-004 N=0 still says scaffold" "wrote     submission/manuscript.qmd (scaffold: 0 Results section(s) and the Discussion still need prose)"

# TC-021, TC-022, TC-034 (older block format)
mkp o1 <<'MD'
- **x**
  id: x
  question: Qx?
  status: accepted
- **y**
  id: y
  question: Qy?
  status: Accepted
MD
runp o1
nochk "TC-021 older format, accepted: no not-accepted line" "not accepted"
chk "TC-021 older format N=2" "scaffold: 2 Results section(s)"
mkp o2 <<'MD'
- **old1**
  id: old1
  question: Qo?
  status: proposed
MD
runp o2; chk "TC-022 older format proposed listed" "not accepted old1: status proposed$NA"
mkp o3 <<'MD'
- **nostat**
  id: nostat
  question: No status here?
MD
runp o3
[ "$rc" = 0 ] && grep -qF "No status here?" "$TMP/o3/submission/manuscript.qmd" \
  && ok "TC-034 older format without status still parses" || no "TC-034 no status" "rc=$rc"
mkp t1 <<'MD'
| extra | 問題 | status | id |
|---|---|---|---|
| zz | Shuffled question? | accepted | shuf |
MD
runp t1
[ "$rc" = 0 ] && grep -qF "Shuffled question?" "$TMP/t1/submission/manuscript.qmd" \
  && ok "TC-034 shuffled/aliased table parses" || no "TC-034 table" "rc=$rc"

# TC-040
mkp s8 <<MD
$HDR
| p1 | Q? | s | m | w | proposed |
| p2 | Q? | s | m | w | rejected |
MD
runp s8
[ "$rc" = 0 ] && [ "$(grep -c '^not accepted' <<<"$out")" = 2 ] \
  && ok "TC-040 nothing accepted still builds, both listed" || no "TC-040" "rc=$rc <<$out>>"

# TC-031 (extra): unparseable plan prints no scaffold / not accepted
mkp u1 <<'MD'
We looked at richness and it seemed fine.
MD
runp u1
[ "$rc" != 0 ] && ! grep -qE 'scaffold|not accepted' <<<"$out" \
  && ok "TC-031 unparseable plan: no scaffold or not-accepted output" || no "TC-031" "rc=$rc <<$out>>"

# TC-032 is covered by the existing --render test above.

# TC-033
if grep -qE 'one section per accepted entry|One section per figure the plan accepted' "$S"; then
  no "TC-033 old 'accepted only' claims are gone" "still in build_package.sh"
else ok "TC-033 old 'accepted only' claims are gone"; fi

# TC-041
HK="$(dirname "$S")/../hooks"
{ [ ! -e "$HK/confirm_finish.sh" ] && ! grep -qiE 'build_package|finish' "$HK/hooks.json"; } \
  && ok "TC-041 no finish hook added" || no "TC-041" "hook present"

# TC-042
bad=$(grep -rlF 'wrote     submission/manuscript.qmd' "$(dirname "$S")/../commands" "$(dirname "$S")/../docs" "$(dirname "$S")/intro" 2>/dev/null \
  | xargs -r grep -LF '(scaffold:')
[ -z "$bad" ] && ok "TC-042 docs quoting the old line carry the new one" || no "TC-042" "$bad"
echo
[ "$fails" = 0 ] && echo "OK: build_package.sh" || { echo "$fails failed"; exit 1; }
