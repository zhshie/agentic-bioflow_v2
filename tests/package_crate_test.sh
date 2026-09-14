#!/bin/bash
# Tests for scripts/package_crate.py - the package described as an RO-Crate
# 1.1 in its own right (proposal R5, docs/LAB_AGENTS.md row R5).
#
# Two things matter more than the file list: nothing in the crate is invented
# (docs/PRINCIPLES.md invariant 9 - license and author are simply absent, and
# the gap is written into README.md instead of guessed), and nf-prov's own
# run crate (PITFALLS 32) is carried verbatim, never rewritten, never
# fabricated for a run that has none.
#
# Run standalone, the same way every script under scripts/ is meant to stay
# runnable (invariant 5) - this does not go through build_package.sh at all.
set -uo pipefail
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/package_crate.py"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
ok() { printf '%-68s ok\n' "$1"; }
no() { printf '%-68s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

py() { python3 -c "$1"; }

# --- fixture: a project with two runs, one with an nf-prov crate, one without
P="$TMP/proj"
mkdir -p "$P/runs/withprov_20260101/results/pipeline_info"
mkdir -p "$P/runs/noprov_20260102/results/pipeline_info"

NESTED="$P/runs/withprov_20260101/results/pipeline_info/ro-crate-metadata.json"
cat > "$NESTED" <<'JSON'
{
  "@context": "https://w3id.org/ro/crate/1.1/context",
  "@graph": [
    {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
     "about": {"@id": "./"},
     "conformsTo": [{"@id": "https://w3id.org/ro/crate/1.1"},
                     {"@id": "https://w3id.org/workflowhub/workflow-ro-crate/1.0"}]},
    {"@id": "./", "@type": "Dataset", "datePublished": "2026-09-14",
     "name": "Workflow run of nf-core/demo",
     "conformsTo": [{"@id": "https://w3id.org/ro/wfrun/process/0.1"},
                     {"@id": "https://w3id.org/workflowhub/workflow-ro-crate/1.0"}],
     "hasPart": [{"@id": "main.nf"}]},
    {"@id": "main.nf", "@type": "File"},
    {"@id": "file:///work/u9613010/lab_runs/some/absolute/path/input.fastq.gz",
     "@type": "File"}
  ]
}
JSON

# --- a submission/ directory as build_package.sh would have left it, minus
# references.bib (which is optional and legitimately sometimes absent)
OUT="$P/submission"
mkdir -p "$OUT/figures" "$OUT/scripts"
echo "methods"      > "$OUT/methods.md"
echo '{"runs":[]}'  > "$OUT/provenance.json"
echo "---"          > "$OUT/manuscript.qmd"
echo "x"            > "$OUT/figures/richness.png"
echo "x <- 1"       > "$OUT/scripts/plot.R"
{
  echo "# proj"
  echo
  echo "## Contents"
  echo
  echo "- some existing content build_package.sh already wrote"
} > "$OUT/README.md"

out=$(python3 "$S" "$P" "$OUT" \
        "$P/runs/withprov_20260101/results" "$P/runs/noprov_20260102/results" 2>&1)
rc=$?
[ "$rc" = 0 ] && ok "runs cleanly over a run with a crate and one without" \
  || no "runs cleanly over a run with a crate and one without" "rc=$rc <<$out>>"

CRATE="$OUT/ro-crate-metadata.json"
[ -s "$CRATE" ] || { echo "FATAL: no crate written, cannot continue"; exit 1; }

# 1. Valid JSON, correct @context, descriptor entity, root Dataset.
py "
import json, sys
d = json.load(open('$CRATE'))
assert d['@context'] == 'https://w3id.org/ro/crate/1.1/context', d.get('@context')
graph = {e['@id']: e for e in d['@graph']}
desc = graph['ro-crate-metadata.json']
assert desc['@type'] == 'CreativeWork'
assert desc['conformsTo'] == {'@id': 'https://w3id.org/ro/crate/1.1'}
assert desc['about'] == {'@id': './'}
root = graph['./']
assert root['@type'] == 'Dataset'
assert root['name'] == 'proj'
assert root['datePublished']
assert isinstance(root['hasPart'], list) and root['hasPart']
" 2>/tmp/pkgcrate_err_$$ \
  && ok "valid JSON: @context, descriptor entity, root Dataset with name/datePublished/hasPart" \
  || no "valid JSON: @context, descriptor entity, root Dataset with name/datePublished/hasPart" \
        "$(cat /tmp/pkgcrate_err_$$)"; rm -f /tmp/pkgcrate_err_$$

# 2. Every payload file in submission/ has a File entity with a relative @id
#    that exists on disk, and vice versa for every File entity found.
py "
import json, os
d = json.load(open('$CRATE'))
graph = {e['@id']: e for e in d['@graph']}
on_disk = set()
for root, _dirs, files in os.walk('$OUT'):
    relr = os.path.relpath(root, '$OUT')
    for f in files:
        rel = f if relr == '.' else os.path.join(relr, f)
        rel = rel.replace(os.sep, '/')
        if rel != 'ro-crate-metadata.json':
            on_disk.add(rel)
file_ids = {i for i, e in graph.items() if e.get('@type') == 'File'}
missing_entity = on_disk - file_ids
missing_on_disk = set()
for fid in file_ids:
    p = os.path.join('$OUT', fid)
    if not os.path.isfile(p):
        missing_on_disk.add(fid)
assert not missing_entity, 'no File entity for: %r' % missing_entity
assert not missing_on_disk, 'File entity points at nothing on disk: %r' % missing_on_disk
" 2>/tmp/pkgcrate_err_$$ \
  && ok "every payload file has a File entity, and every File entity's @id exists" \
  || no "every payload file has a File entity, and every File entity's @id exists" \
        "$(cat /tmp/pkgcrate_err_$$)"; rm -f /tmp/pkgcrate_err_$$

# 3. No absolute path in the PACKAGE's own crate (the nested nf-prov crate is
#    allowed to carry one - PITFALLS 32 - and is checked separately below).
if grep -oE '"@id"[[:space:]]*:[[:space:]]*"[^"]*"' "$CRATE" | grep -E '"(/|file://)' >/dev/null; then
  no "no absolute path in the package's own crate" "found one - see grep above"
else
  ok "no absolute path in the package's own crate"
fi

# 4a. A run with a crate: copied byte-identical, referenced as a nested
#     Dataset with conformsTo copied verbatim.
DEST="$OUT/runs/withprov_20260101/ro-crate-metadata.json"
if [ -f "$DEST" ] && cmp -s "$NESTED" "$DEST"; then
  ok "a run's nf-prov crate is copied byte-identical into runs/<name>/"
else
  no "a run's nf-prov crate is copied byte-identical into runs/<name>/" "missing or differs"
fi

py "
import json
d = json.load(open('$CRATE'))
graph = {e['@id']: e for e in d['@graph']}
root = graph['./']
assert {'@id': 'runs/withprov_20260101/'} in root['hasPart']
ds = graph['runs/withprov_20260101/']
assert ds['@type'] == 'Dataset'
assert {'@id': 'runs/withprov_20260101/ro-crate-metadata.json'} in ds['hasPart']
nested = json.load(open('$NESTED'))
nested_root = [e for e in nested['@graph'] if e['@id'] == './'][0]
assert ds['conformsTo'] == nested_root['conformsTo'], (ds['conformsTo'], nested_root['conformsTo'])
" 2>/tmp/pkgcrate_err_$$ \
  && ok "the nested Dataset's conformsTo is copied from the run crate's own root" \
  || no "the nested Dataset's conformsTo is copied from the run crate's own root" \
        "$(cat /tmp/pkgcrate_err_$$)"; rm -f /tmp/pkgcrate_err_$$

# 4b. A run with no crate: no runs/<name> entry anywhere, and no error (this
#     already passed via rc=0 above; here we check it left no trace).
if [ -e "$OUT/runs/noprov_20260102" ]; then
  no "a run with no crate leaves no runs/<name> entry" "runs/noprov_20260102 exists"
else
  ok "a run with no crate leaves no runs/<name> entry"
fi
py "
import json
d = json.load(open('$CRATE'))
ids = {e['@id'] for e in d['@graph']}
assert not any('noprov' in i for i in ids)
" 2>/tmp/pkgcrate_err_$$ \
  && ok "...and nothing in the crate itself names that run" \
  || no "...and nothing in the crate itself names that run" "$(cat /tmp/pkgcrate_err_$$)"
rm -f /tmp/pkgcrate_err_$$

# 5. License absent, and README carries both gaps (a nested crate WAS copied
#    in this fixture, so both bullets are expected).
if grep -q '"license"' "$CRATE"; then
  no "license absent from the crate" "found a license key"
else
  ok "license absent from the crate"
fi
grep -qi "no license is declared" "$OUT/README.md" \
  && ok "README.md states the license gap" \
  || no "README.md states the license gap" "not found"
grep -qi "absolute" "$OUT/README.md" && grep -qi "outside the lab" "$OUT/README.md" \
  && ok "README.md warns about cluster paths when a run crate was copied" \
  || no "README.md warns about cluster paths when a run crate was copied" "not found"

# --- a second fixture: no run has a crate at all, so the cluster-path warning
#     must NOT appear, while the license gap still must.
P2="$TMP/proj2"
mkdir -p "$P2/runs/onlyrun_20260101/results/pipeline_info" "$P2/submission"
echo "x" > "$P2/submission/methods.md"
{ echo "# proj2"; echo; echo "## Contents"; } > "$P2/submission/README.md"
out2=$(python3 "$S" "$P2" "$P2/submission" "$P2/runs/onlyrun_20260101/results" 2>&1); rc2=$?
[ "$rc2" = 0 ] || no "second fixture (no run crates) still runs cleanly" "rc=$rc2 <<$out2>>"
if [ ! -d "$P2/submission/runs" ]; then
  ok "no nested crates at all: submission/runs/ is never created"
else
  no "no nested crates at all: submission/runs/ is never created" "runs/ exists"
fi
if grep -qi "no license is declared" "$P2/submission/README.md" \
   && ! grep -qi "absolute" "$P2/submission/README.md"; then
  ok "README warns about cluster paths ONLY when a nested crate was copied"
else
  no "README warns about cluster paths ONLY when a nested crate was copied" \
     "$(tail -10 "$P2/submission/README.md")"
fi

echo
[ "$fails" = 0 ] && echo "OK: package_crate.py" || { echo "$fails failed"; exit 1; }
