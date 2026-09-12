#!/bin/bash
# The methods paragraph a pipeline already wrote, with the gap it left filled.
#
#   methods_text.py [--assets <dir>] [--out <file>] <results-dir> [...]
#
# nf-core pipelines ship assets/methods_description_template.yml: a citable
# paragraph naming the pipeline, its DOI, Nextflow, Bioconda, Biocontainers,
# and the command that ran. The workflow interpolates it and puts the result in
# the quality report. So the paragraph is not ours to write - invariant 1 - and
# this does not write one.
#
# What it does is fill the slot the template leaves for the author. Two of its
# placeholders, ${tool_citations} and ${tool_bibliography}, came out EMPTY in
# every run measured here - the rendered paragraph reads "<p></p>" where the
# per-tool citations should be, so DADA2, QIIME2, STAR and Salmon go uncited.
# The template's own footnote says so in as many words:
#
#     You should also cite all software used within this run.
#
# That is the exercise this performs. It is not a second methods section; it is
# the one the pipeline asked the author to finish.
#
# Sources, in order of authority, and nothing outside them:
#   the run's versions file    which tools actually ran, and at which version
#   the pipeline's CITATIONS.md   what each of those is cited as
#   the run's own params.yaml   why the parameters have the values they have
#
# Anything a tool cannot be matched to becomes a visible CITATION NEEDED. A
# citation this program cannot find is not a citation it may invent.
''''true
HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
if [ -f "$HERE/require_python.sh" ]; then
    . "$HERE/require_python.sh"
    require_python || exit 1
fi
exec python3 "$0" "$@"
'''

import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s)\]\"'<>,;]+")

# The MultiQC-rendered Methods paragraph, and the one slot inside it that is
# reliably still empty. Measured against two real runs' multiqc_report.html
# (rnaseq_sclerotia_d5_20260902, ampliseq_sclerotia_d5_20260904): both render
# ${workflow.manifest.version}, ${doi_text} and ${workflow.commandLine}
# correctly - Nextflow fills those before MultiQC ever sees the template - and
# both leave ${tool_citations} as a bare "<p></p>" right before "References".
METHODS_SECTION_RE = re.compile(
    r"<h4>\s*Methods\s*</h4>.*?(?=<h4>\s*References\s*</h4>)", re.S | re.I)
EMPTY_P_RE = re.compile(r"<p>\s*</p>")
COMMAND_BLOCK_RE = re.compile(r"<pre><code>.*?</code></pre>", re.S)


def provenance(results_dirs):
    out = subprocess.run(
        [os.path.join(HERE, "collect_provenance.py"), "--json"] + list(results_dirs),
        capture_output=True, text=True)
    if out.returncode != 0:
        sys.stderr.write(out.stderr)
        return None
    return json.loads(out.stdout)["runs"]


def pipeline_name(run):
    """`nf-core/ampliseq` out of the Workflow block, whatever else is in it."""
    for key in (run.get("workflow") or {}):
        if "/" in key:
            return key
    return None


def assets_dir(base, pipeline):
    if not pipeline:
        return None
    d = os.path.join(base, pipeline)
    return d if os.path.isdir(d) else None


def parse_citations(path):
    """tool -> {"text": full citation, "doi": first DOI found}.

    The file's shape is regular across pipelines: `- [Tool](url)` followed by
    an indented `> citation`. Parsed rather than looked up, so a pipeline this
    has never seen works the same way.
    """
    entries, current = {}, None
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = re.match(r"^\s*[-*]?\s*\[([^\]]+)\]\((http[^)]+)\)", line)
                if m:
                    current = m.group(1).strip()
                    entries.setdefault(current, {"text": "", "doi": None})
                    continue
                if current and line.lstrip().startswith(">"):
                    body = line.lstrip()[1:].strip()
                    if body:
                        e = entries[current]
                        e["text"] = (e["text"] + " " + body).strip()
                        if not e["doi"]:
                            d = DOI_RE.search(body)
                            if d:
                                e["doi"] = d.group(0).rstrip(".")
    except OSError:
        return {}
    return entries


def normalise(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def match_tools(citable, citations):
    """Pair each tool that ran with how the pipeline says to cite it.

    Matching is on a squashed name because the two files disagree about
    punctuation and prefixes - a versions file says `bioconductor-deseq2`
    where the citation list says `DESeq2`.
    """
    index = {}
    for name, entry in citations.items():
        index.setdefault(normalise(name), (name, entry))
        for word in re.split(r"[\s/(),-]+", name):
            if len(word) > 2:
                index.setdefault(normalise(word), (name, entry))

    matched, missing = [], []
    for tool in citable:
        key = normalise(tool)
        hit = index.get(key)
        if hit is None:
            for suffix in ("bioconductor", "r", "python", "perl"):
                if key.startswith(suffix):
                    hit = index.get(key[len(suffix):])
                    if hit:
                        break
        if hit:
            matched.append((tool, hit[0], hit[1]))
        else:
            # A near miss is reported as a near miss, never resolved silently.
            # Measured: the versions file says `stringtie` and the citation
            # list says `StringTie2`, so a rule that stripped trailing digits
            # would join them - and would just as happily cite Bowtie's paper
            # for Bowtie 2, which is a wrong citation rather than a missing
            # one. Wrong is worse, because a gap is visible and an error is
            # not. So the candidate is surfaced for a person to confirm.
            near = sorted({name for k, (name, _e) in index.items()
                           if len(key) > 3 and (k.startswith(key) or key.startswith(k))})
            missing.append((tool, near))
    return matched, missing


def html_to_md(text):
    """The template's paragraph is HTML in a YAML block; this is the whole of it."""
    text = re.sub(r"<h4>(.*?)</h4>", r"\n### \1\n", text, flags=re.S)
    text = re.sub(r"<pre><code>(.*?)</code></pre>", r"\n```\n\1\n```\n", text, flags=re.S)
    text = re.sub(r'<a href="([^"]+)">(.*?)</a>', r"[\2](\1)", text, flags=re.S)
    text = re.sub(r"<a href='([^']+)'>(.*?)</a>", r"[\2](\1)", text, flags=re.S)
    text = re.sub(r"<li>(.*?)</li>", r"- \1", text, flags=re.S)
    text = re.sub(r"</?(p|ul|div|em|strong|h5)[^>]*>", "", text)
    text = re.sub(r'<div class="[^"]*">', "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def rendered_methods(quality_report):
    """The Methods paragraph as MultiQC already rendered it, DOI and all.

    Invariant 1: MultiQC (through nf-core's own pipeline code) already renders
    methods_description_template.yml, substituting ${workflow.manifest.version},
    ${doi_text} and ${workflow.commandLine} with values only Nextflow has at
    run time. Re-deriving that by string-replacing the template a second time
    is where the DOI bug lived - ${doi_text} was blanked instead of read. So
    this reads the report's own rendered text instead of the template file.

    Returns the raw HTML of that section, or None if the report has no such
    section (MultiQC not run yet, or a customised template without one) - the
    caller falls back to the template-based render in that case.
    """
    if not quality_report:
        return None
    try:
        with open(quality_report, encoding="utf-8", errors="replace") as fh:
            html = fh.read()
    except OSError:
        return None
    m = METHODS_SECTION_RE.search(html)
    return m.group(0) if m else None


def template_body(path):
    """The `data: |` block, dedented. Not a YAML parser - see collect_provenance."""
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return None
    body, taking = [], False
    for line in lines:
        if not taking:
            if re.match(r"^data:\s*\|", line):
                taking = True
            continue
        if line and not line[0].isspace():
            break
        body.append(line[2:] if line.startswith("  ") else line)
    return "\n".join(body) if body else None


def rationale(path):
    """The comment blocks from the run's own params.yaml, kept with their key.

    This is the only place on the tree that says WHY a value was chosen. A
    methods section without it can say what ran and never why, which is the
    half a reader needs to judge the work.
    """
    out, pending = [], []
    try:
        for line in open(path, encoding="utf-8", errors="replace"):
            st = line.strip()
            if st.startswith("#"):
                pending.append(st.lstrip("#").strip())
            elif st and ":" in st:
                key = st.split(":", 1)[0].strip()
                if pending:
                    out.append((key, " ".join(pending)))
                pending = []
            elif not st:
                pending = []
    except OSError:
        return []
    return out


def render(run, assets_base):
    name = pipeline_name(run)
    wf = run.get("workflow") or {}
    tools = run.get("tools") or {}
    citable = run.get("citable_tools") or []
    lines, notes = [], []

    adir = assets_dir(assets_base, name)
    tmpl = os.path.join(adir, "assets", "methods_description_template.yml") if adir else None
    cits = os.path.join(adir, "CITATIONS.md") if adir else None

    body = template_body(tmpl) if tmpl and os.path.isfile(tmpl) else None
    matched, missing = ([], [(t, []) for t in citable])
    if cits and os.path.isfile(cits):
        matched, missing = match_tools(citable, parse_citations(cits))
    else:
        notes.append("no CITATIONS.md for %s under %s - every tool below is "
                     "unmatched for that reason alone, not because it is uncitable"
                     % (name, assets_base))

    tool_citations = ""
    if matched:
        tool_citations = ("Tools used within the workflow: "
                          + ", ".join(sorted({m[1] for m in matched})) + ".")
    tool_bibliography = ""
    if matched:
        tool_bibliography = "".join(
            "<li>%s%s</li>" % (entry["text"] or cited_as,
                               (" doi: " + entry["doi"]) if entry.get("doi") else "")
            for _tool, cited_as, entry in sorted(matched, key=lambda m: m[0].lower()))

    # The command the report records is not reproducible: launching through
    # the Platform puts an ephemeral URL where the parameters were. Point at
    # the file kept beside the run instead, and say that is what happened.
    cmd = "nextflow run %s -r %s -params-file %s" % (
        name, wf.get(name, "<revision>"),
        os.path.relpath(run["launch_params"], run["run_dir"])
        if run.get("launch_params") else "params.yaml")

    rendered = rendered_methods(run.get("quality_report"))
    if rendered:
        # Fill only the gap MultiQC's own tool-citation matcher leaves empty -
        # never overwrite a slot the report already filled, because our own
        # match is not more authoritative than the report's own render.
        filled, n = EMPTY_P_RE.subn("<p>%s</p>" % tool_citations, rendered, count=1)
        if n == 0:
            filled = rendered
        filled, n = COMMAND_BLOCK_RE.subn("<pre><code>%s</code></pre>" % cmd, filled, count=1)
        filled = re.sub(r"\$\{[^}]*\}", "", filled)
        lines.append(html_to_md(filled))
        if n:
            notes.append("the command line shown is reconstructed against the run's "
                         "own params file; the one the report records points at an "
                         "ephemeral URL and cannot be re-run")
    elif body:
        filled = (body
                  .replace("${workflow.manifest.version}", str(wf.get(name, "")).lstrip("v"))
                  .replace("${workflow.nextflow.version}", str(wf.get("Nextflow", "")))
                  .replace("${workflow.commandLine}", cmd)
                  .replace("${tool_citations}", tool_citations)
                  .replace("${tool_bibliography}", tool_bibliography)
                  # No rendered report to read the real ${doi_text}/${nodoi_text}
                  # from (Nextflow fills those, not this script - see
                  # rendered_methods()). Invariant 9: a gap that cannot be
                  # resolved is written into the output, never silently
                  # dropped, so this is a visible marker, not a blank.
                  .replace("${doi_text}",
                           "[DOI not shown: no rendered MultiQC report was "
                           "found to read it from]")
                  .replace("${nodoi_text}", ""))
        filled = re.sub(r"\$\{[^}]*\}", "", filled)
        lines.append(html_to_md(filled))
        notes.append("the command line shown is reconstructed against the run's "
                     "own params file; the one the report records points at an "
                     "ephemeral URL and cannot be re-run")
        notes.append("no rendered quality report was found, so the pipeline's DOI "
                     "could not be read from it - see the [DOI not shown] marker above")
    else:
        notes.append("no methods template for %s - the paragraph below is only "
                     "the tool list, not the pipeline's own wording" % name)
        lines.append("### Methods\n\nData was processed using %s %s with Nextflow %s."
                     % (name, wf.get(name, ""), wf.get("Nextflow", "")))

    lines.append("\n### Software\n")
    for tool, cited_as, entry in sorted(matched, key=lambda m: m[0].lower()):
        doi = (" doi:" + entry["doi"]) if entry.get("doi") else ""
        lines.append("- **%s** %s (cited as %s%s)" % (tool, tools.get(tool, ""), cited_as, doi))
    for tool, near in sorted(missing, key=lambda m: m[0].lower()):
        hint = ""
        if near:
            hint = (" — closest in CITATIONS.md: %s. Confirm it is the same tool "
                    "before using it." % ", ".join("`%s`" % n for n in near[:3]))
        lines.append("- **%s** %s — `[CITATION NEEDED: %s]`%s"
                     % (tool, tools.get(tool, ""), tool, hint))

    if run.get("launch_params"):
        why = rationale(run["launch_params"])
        if why:
            lines.append("\n### Why these parameters\n")
            for key, text in why:
                lines.append("- `%s` — %s" % (key, text))

    if notes:
        lines.append("\n<!-- assembled by scripts/methods_text.py")
        for n in notes + run.get("notes", []):
            lines.append("     - " + n)
        lines.append("-->")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(prog="methods_text.py")
    p.add_argument("results", nargs="+")
    p.add_argument("--assets", default=os.path.expanduser("~/.nextflow/assets"),
                   help="where pipeline sources are cached (default ~/.nextflow/assets)")
    p.add_argument("--out")
    args = p.parse_args(argv)

    runs = provenance(args.results)
    if runs is None:
        return 2
    text = "\n\n".join(render(r, args.assets) for r in runs)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
