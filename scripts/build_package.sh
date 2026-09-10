#!/bin/bash
# Assemble one project into something that can be sent somewhere.
#
#   build_package.sh [--render] <project-dir>
#
# A project holds the raw data, every run made from it, the analysis written on
# those runs, and this - the package built from the analysis. It is a build
# output: throwable away, rebuildable, and deliberately a sibling of analysis/
# rather than a child, because everything under analysis/ is undeletable by
# design (hooks/confirm_cleanup.sh) and a build directory that cannot be
# cleared is not one.
#
# What it assembles, and from where - nothing here is composed from memory:
#
#   provenance.json   scripts/collect_provenance.py over every run in the
#                     project. Versions, parameters, the command.
#   methods.md        scripts/methods_text.py. The pipeline's own methods
#                     paragraph with the citation slot it leaves for the
#                     author filled in.
#   references.bib    scripts/cite.sh over every DOI those two turned up.
#                     Resolved over the network, never recalled; anything
#                     unresolved stays in the file as CITATION NEEDED.
#   manuscript.qmd    methods.md, then one section per accepted entry in
#                     analysis.md, each with its figure and the question that
#                     entry says it answers.
#   figures/          what the analysis produced, plus anything the pipelines
#                     already drew that the plan chose to keep.
#   scripts/          the code that produced the figures.
#
# The .qmd carries NO executable chunks. The figures already exist as files by
# the time this runs, so rendering needs Quarto and nothing else - no R, no
# knitr, no Python. That is what lets the same document render on a machine
# that has none of them installed.
#
# --render is off by default and the reason is a machine boundary. Quarto ships
# inside Positron, so rendering happens where the IDE is; this cluster's login
# node has no quarto and no pandoc and cannot install them (no writable R or
# Python library, PITFALLS 16d). Everything before rendering works anywhere, so
# without --render this stops one step short and says which step and where -
# the same shape as PITFALLS 20i, where a tool that could not reach the IDE
# said so instead of blaming the user.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RENDER=0
PROJECT=""
while [ $# -gt 0 ]; do
    case "$1" in
        --render) RENDER=1; shift ;;
        -h|--help) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) echo "unknown option '$1'" >&2; exit 2 ;;
        *) PROJECT="$1"; shift ;;
    esac
done
[ -n "$PROJECT" ] || { echo "usage: build_package.sh [--render] <project-dir>" >&2; exit 2; }
[ -d "$PROJECT" ] || { echo "not a directory: $PROJECT" >&2; exit 2; }
PROJECT="$(cd "$PROJECT" && pwd)"

ANALYSIS="$PROJECT/analysis"
PLAN="$ANALYSIS/analysis.md"
OUT="$PROJECT/submission"

[ -f "$PLAN" ] || { printf '%s\n' \
    "no analysis plan at $PLAN." \
    "" \
    "The package is built from the plan: it is what says which figures were" \
    "accepted and what question each one answers, and those questions become" \
    "the captions. Run /downstream first - its step 3 agrees the plan and" \
    "writes it there." >&2; exit 2; }

RUNS=()
while IFS= read -r d; do RUNS+=("$d"); done < <(find -L "$PROJECT/runs" -maxdepth 2 -type d -name results 2>/dev/null | sort)
[ "${#RUNS[@]}" -gt 0 ] || { echo "no runs/*/results under $PROJECT - a package needs at least one run to describe." >&2; exit 2; }

mkdir -p "$OUT/figures" "$OUT/scripts" || exit 1

echo "project   $PROJECT"
echo "runs      ${#RUNS[@]}"

# --- what the runs can prove -------------------------------------------------
"$HERE/collect_provenance.py" --json "${RUNS[@]}" > "$OUT/provenance.json" || exit 1
echo "wrote     submission/provenance.json"

"$HERE/methods_text.py" --out "$OUT/methods.md" "${RUNS[@]}" || exit 1
echo "wrote     submission/methods.md"

# --- the bibliography --------------------------------------------------------
# Every DOI the runs recorded, plus every DOI the citation matching turned up.
# Deduplicated by cite.sh, which also leaves anything unresolved visible.
DOIS="$OUT/.dois.txt"
{
    python3 - "$OUT/provenance.json" <<'PY'
import json, sys
for run in json.load(open(sys.argv[1]))["runs"]:
    for c in run.get("citation_dois") or []:
        print("%s   # %s" % (c["doi"], c.get("tool") or ""))
PY
    grep -oE 'doi:10\.[0-9]{4,9}/[^ )]+' "$OUT/methods.md" 2>/dev/null | sed 's/^doi://'
} | sort -u > "$DOIS"

if [ -s "$DOIS" ]; then
    "$HERE/cite.sh" --out "$OUT/references.bib" "@$DOIS"
    rc=$?
    [ "$rc" = 3 ] && echo "note      some citations are unresolved and are marked in references.bib"
    echo "wrote     submission/references.bib ($(grep -c '^@' "$OUT/references.bib" 2>/dev/null || echo 0) entries)"
else
    echo "note      no DOIs found in any run - references.bib not written"
fi
rm -f "$DOIS"

# --- figures and the code that made them -------------------------------------
n_fig=0
if [ -d "$ANALYSIS/figures" ]; then
    for f in "$ANALYSIS/figures"/*; do
        [ -f "$f" ] || continue
        cp -p "$f" "$OUT/figures/" && n_fig=$((n_fig+1))
    done
fi
n_src=0
for f in "$ANALYSIS"/*.R "$ANALYSIS"/*.r "$ANALYSIS"/*.py; do
    [ -f "$f" ] || continue
    cp -p "$f" "$OUT/scripts/" && n_src=$((n_src+1))
done
cp -p "$PLAN" "$OUT/scripts/analysis.md" 2>/dev/null
echo "copied    $n_fig figure(s), $n_src script(s)"

# --- the manuscript ----------------------------------------------------------
QMD="$OUT/manuscript.qmd"
{
    echo '---'
    echo "title: \"$(basename "$PROJECT")\""
    echo 'bibliography: references.bib'
    echo 'format:'
    echo '  docx: default'
    echo '  html:'
    echo '    embed-resources: true'
    echo '---'
    echo
    cat "$OUT/methods.md"
    echo
    echo '## Results'
    echo
    # One section per figure the plan accepted, captioned with the question
    # that entry says it answers. The plan is the only record of why a figure
    # exists, so this is where that survives into the write-up.
    python3 - "$PLAN" "$OUT/figures" <<'PY'
import os, re, sys
plan, figdir = sys.argv[1], sys.argv[2]
text = open(plan, encoding="utf-8", errors="replace").read()
figs = sorted(os.listdir(figdir)) if os.path.isdir(figdir) else []
blocks = re.split(r"\n(?=#{1,3}\s|\s*[-*]\s+\*\*)", text)
emitted = set()
for block in blocks:
    ident = re.search(r"(?:^|\n)\s*(?:id|ID)\s*[:=]\s*`?([A-Za-z0-9_.-]+)", block)
    if not ident:
        continue
    fid = ident.group(1)
    q = re.search(r"(?:^|\n)\s*(?:question|問題)\s*[:=]\s*(.+)", block)
    match = [f for f in figs if f.startswith(fid)]
    print("### %s\n" % (q.group(1).strip() if q else fid))
    if match:
        print("![%s](figures/%s){#fig-%s}\n" % (q.group(1).strip() if q else fid, match[0], fid))
        emitted.add(match[0])
    else:
        print("<!-- no figure file starting with '%s' in figures/ -->\n" % fid)
    print("<!-- Describe what this shows, from the data. Every number here must "
          "trace to a file or to a script in scripts/. -->\n")
for f in figs:
    if f not in emitted:
        print("<!-- figures/%s is in the package but no plan entry claims it -->" % f)
PY
    echo
    echo '## Discussion'
    echo
    echo "<!-- Not drafted. The discussion is the authors' scientific judgement,"
    echo "     and this program has no basis for any of it. -->"
} > "$QMD"
echo "wrote     submission/manuscript.qmd"

# --- README: the reproducible reference --------------------------------------
{
    echo "# $(basename "$PROJECT")"
    echo
    echo "Built by scripts/build_package.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)."
    echo
    echo "## How to reproduce the runs"
    echo
    echo "The pipelines are not copied here. They are named, pinned and"
    echo "parameterised, which is what makes them re-runnable without carrying"
    echo "a second copy that can drift from upstream:"
    echo
    python3 - "$OUT/provenance.json" <<'PY'
import json, os, sys
for run in json.load(open(sys.argv[1]))["runs"]:
    wf = run.get("workflow") or {}
    name = next((k for k in wf if "/" in k), "unknown pipeline")
    print("- **%s** %s, Nextflow %s" % (name, wf.get(name, "?"), wf.get("Nextflow", "?")))
    if run.get("launch_params"):
        print("  parameters: `%s`" % os.path.basename(run["launch_params"]))
    for note in run.get("notes", []):
        print("  - note: %s" % note)
PY
    echo
    echo "## Contents"
    echo
    echo "- \`manuscript.qmd\` - methods and results; render with \`quarto render\`"
    echo "- \`methods.md\` - the methods section on its own"
    echo "- \`references.bib\` - every citation, resolved from its DOI"
    echo "- \`provenance.json\` - versions, parameters and commands for every run"
    echo "- \`figures/\`, \`scripts/\` - the figures and the code that made them"
} > "$OUT/README.md"
echo "wrote     submission/README.md"

# --- render, or say why not --------------------------------------------------
if [ "$RENDER" = 0 ]; then
    echo
    echo "Not rendered. Everything above is done; the remaining step is:"
    echo
    echo "    quarto render $QMD --to docx"
    echo "    quarto render $QMD --to html"
    echo
    echo "Run that where Positron is - it ships Quarto, and this machine has"
    echo "none. Each format is rendered separately on purpose: asking for"
    echo "several at once has a known failure when a figure needs converting."
    exit 0
fi

if ! command -v quarto >/dev/null 2>&1; then
    printf '%s\n' \
      "" \
      "--render was asked for and there is no quarto on this machine." \
      "" \
      "That is usually the machine, not a missing install: Quarto ships inside" \
      "Positron, so rendering happens where the IDE is. If Positron is on your" \
      "own desktop and this is running somewhere else, there is no route to it" \
      "from here - copy submission/ across, or run this there." \
      "" \
      "Everything before rendering is already written to $OUT." >&2
    exit 3
fi

rc=0
for fmt in docx html; do
    if quarto render "$QMD" --to "$fmt"; then echo "rendered  $fmt"
    else echo "FAILED to render $fmt" >&2; rc=1; fi
done
exit $rc
