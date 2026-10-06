#!/bin/bash
# The methods paragraph a pipeline already wrote, with the gap it left filled.
#
# Nothing existing: nf-core's methods template and MultiQC already render the
# paragraph, but both leave the per-tool citation slot empty, and no
# maintained tool fills it from a run's versions file and the pipeline's
# CITATIONS.md. That slot is all this adds.
#
# Why it does not write a new methods paragraph: the pipeline's own
# assets/methods_description_template.yml already renders one into the
# quality report; this only fills the citation slot it leaves empty (below).
#
#   methods_text.py [--assets <dir>] [--cache-dir <dir>] [--out <file>] <results-dir> [...]
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
#
# Where CITATIONS.md and the template come from (issue #4). Pipelines here run
# through Seqera Platform, so nothing ever ran `nextflow pull` on this machine
# and ~/.nextflow/assets is empty on the first finish. Order: that directory
# (read only, never written), then the deployment's own cache (--cache-dir,
# <root>/cache/pipeline_files), then a fetch from the pipeline's GitHub
# repository at the revision the run's versions file records - the same
# raw.githubusercontent.com read scripts/prepare_launch.sh does for
# nextflow_schema.json, so it takes the same proxy where there is one. A fetch
# that cannot be done (no revision, not owner/repo, 404, offline) leaves the
# tools as CITATION NEEDED and the note says which of those it was.
# --fetcher <cmd> (or $ABF_PIPELINE_FETCHER; "off" disables) replaces the
# network read: `<cmd> <owner/repo> <revision> <path>` prints the file, exits
# 44 for "not found", anything else non-zero for "unreachable" with the reason
# on stderr. It exists so tests never touch the network.
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
import atexit
import re
import shutil
import subprocess
import sys
import tempfile

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

# nf-core's own methods template builds the DOI link as
# `https://doi.org/${doi_text}`, assuming doi_text is a bare id
# ("10.5281/..."). Some pipelines' nextflow.config sets manifest.doi to the
# already-complete URL instead, so the template's own render comes out
# doubled - "https://doi.org/https://doi.org/10.5281/..." - and a 404 link
# that reads fine is exactly the kind of error nobody notices at a glance.
# That happens in MultiQC's own rendering, upstream of anything this script
# reads (rendered_methods() relays the report's HTML verbatim by design, so
# it would otherwise carry the doubling straight through) - fixed here rather
# than upstream because this is the one place that puts the paragraph in
# front of a person.
DOI_DOUBLE_PREFIX_RE = re.compile(r"(https?://doi\.org/)(?:https?://doi\.org/)+", re.I)


def fix_doubled_doi(text):
    """Collapse a `https://doi.org/https://doi.org/<id>` link down to one prefix."""
    return DOI_DOUBLE_PREFIX_RE.sub(r"\1", text)


# invisible-package-gaps item 2: `re.sub(r"\$\{[^}]*\}", "", filled)` used to
# delete anything left unresolved with no trace - a sentence like "run for
# ${custom_reason}" came out reading "run for ." with nothing to say why.
# Invariant 9: a gap that cannot be resolved is written into the output,
# never silently dropped, so every survivor becomes a visible marker instead.
UNRESOLVED_PLACEHOLDER_RE = re.compile(r"\$\{([^}]*)\}")
# One pass over tags and placeholders together, so a marker written for a
# placeholder is never itself rescanned. #38 item 1: a placeholder inside a
# tag's attribute (`<div class="${x}">`, `<a href="${x}">`) used to be marked
# in place, and html_to_md then dropped the tag - or kept the marker only as a
# link target - so the gap never reached the reader. Inside a tag the
# placeholder becomes `#` and its marker is written as text just before the tag.
_TAG_OR_PLACEHOLDER_RE = re.compile(r"<[A-Za-z/!][^<>]*>|\$\{([^}]*)\}")


def _gap(name):
    return "[GAP: unresolved placeholder ${%s}]" % name


def mark_unresolved_placeholders(text):
    def one(m):
        if m.group(1) is not None:
            return _gap(m.group(1))
        tag = m.group(0)
        names = UNRESOLVED_PLACEHOLDER_RE.findall(tag)
        if not names:
            return tag
        # A trailing space keeps the marker from fusing with a following
        # `[text](url)` into a pandoc reference link.
        return ("".join(_gap(n) for n in names) + " "
                + UNRESOLVED_PLACEHOLDER_RE.sub("#", tag))
    return _TAG_OR_PLACEHOLDER_RE.sub(one, text)


def provenance(results_dirs):
    # sys.executable, not the .py file's own path: Python's subprocess.run()
    # launches a file through raw CreateProcess on native Windows, which
    # bypasses shebang/file-association handling entirely (the OS itself
    # never gets a chance to see `#!/bin/bash` and re-exec through python3).
    # That crashed with `OSError: [WinError 193] %1 is not a valid Win32
    # application` - the interpreter that has to run this script is *this*
    # script's own interpreter, so ask for it by name instead of hoping the
    # OS can work it out from the file. Works identically on Linux/macOS/WSL.
    out = subprocess.run(
        [sys.executable, os.path.join(HERE, "collect_provenance.py"), "--json"] + list(results_dirs),
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


# --- fetching what a local `nextflow pull` would have left ------------------
GITHUB_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.-]+$")
REV_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/+-]*$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
NOT_FOUND = 44
CITATIONS_PATH = "CITATIONS.md"
TEMPLATE_PATH = "assets/methods_description_template.yml"
_SCRATCH = []


def _scratch_dir():
    """Where a fetched file goes when there is no cache to keep it in."""
    if not _SCRATCH:
        d = tempfile.mkdtemp(prefix="abf-pipeline-files-")
        _SCRATCH.append(d)
        atexit.register(shutil.rmtree, d, True)
    return _SCRATCH[0]


def curl_fetcher(repo, rev, path):
    """(text, None) or (None, reason). The read prepare_launch.sh does."""
    if not shutil.which("curl"):
        return None, "curl is not installed here"
    url = "https://raw.githubusercontent.com/%s/%s/%s" % (repo, rev, path)
    try:
        out = subprocess.run(
            ["curl", "-sS", "-L", "--connect-timeout", "10", "--max-time", "60",
             "-w", "\n%{http_code}", url], capture_output=True)
    except OSError as e:
        return None, "curl could not run: %s" % e
    if out.returncode != 0:
        err = out.stderr.decode("utf-8", "replace").strip().splitlines()
        return None, "network unreachable (curl exit %d: %s)" % (
            out.returncode, err[-1] if err else "no message")
    body, _, code = out.stdout.rpartition(b"\n")
    code = code.decode("ascii", "replace").strip()
    if code == "200":
        return body.decode("utf-8", "replace"), None
    if code == "404":
        return None, "not found"
    return None, "GitHub answered HTTP %s" % code


def command_fetcher(cmd):
    def fetch(repo, rev, path):
        try:
            out = subprocess.run([cmd, repo, rev, path], capture_output=True)
        except OSError as e:
            return None, "fetcher could not run: %s" % e
        if out.returncode == 0:
            return out.stdout.decode("utf-8", "replace"), None
        if out.returncode == NOT_FOUND:
            return None, "not found"
        err = out.stderr.decode("utf-8", "replace").strip()
        return None, "network unreachable (%s)" % (err or "exit %d" % out.returncode)
    return fetch


def disabled_fetcher(_repo, _rev, _path):
    return None, "fetching is switched off here"


def revision_candidates(rev):
    """The revision as recorded, then (tags only) its v-prefixed twin.

    A versions file says `3.14.0` where the tag is `3.14.0`, or `1.2.3` where
    it is `v1.2.3`. A commit SHA is exact and is never rewritten.
    """
    if SHA_RE.match(rev):
        return [rev]
    out = [rev]
    if rev[0].isdigit():
        out.append("v" + rev)
    elif rev[0] in "vV" and rev[1:2].isdigit():
        out.append(rev[1:])
    return out


IMMUTABLE_REV_RE = re.compile(r"^[vV]?[0-9]+(\.[0-9]+){0,3}$")
TEMPLATE_DATA_RE = re.compile(r"^data:\s*\|", re.M)


def is_immutable(rev):
    """A full commit SHA or a plain version tag never changes; a branch does."""
    return bool(SHA_RE.match(rev) or IMMUTABLE_REV_RE.match(rev))


def kind_of(path):
    return "CITATIONS.md" if path == CITATIONS_PATH else "methods template"


def not_usable(path, text):
    """Why this text is not the file it should be, or None when it is."""
    if not text.strip():
        return "it is empty"
    if path == CITATIONS_PATH:
        if not parse_citation_lines(text.splitlines()):
            return "it has no tool entries"
    elif not TEMPLATE_DATA_RE.search(text):
        return "it has no `data:` block"
    return None


def snippet(text):
    first = " ".join(text.split())[:50]
    return "starts: %r" % first


class PipelineFiles:
    """Resolve one file of a pipeline's repository to a path on this machine."""

    def __init__(self, cache_dir=None, fetcher=None):
        self.cache_dir = cache_dir
        self.fetcher = fetcher or disabled_fetcher

    def get(self, name, rev, path, assets_base):
        """-> (file path or None, where it came from, reason it is missing, warning).

        A file is only ever returned after it has been checked to be the kind
        of file it should be: a captive portal's HTML page answers 200 too.
        """
        kind = kind_of(path)
        local = os.path.join(assets_base, name, *path.split("/")) if name else None
        if local and os.path.isfile(local):
            src = os.path.relpath(local, assets_base)
            with open(local, encoding="utf-8", errors="replace") as fh:
                bad = not_usable(path, fh.read())
            if bad:
                return None, None, "%s is not a %s (%s)" % (src, kind, bad), None
            return local, src, None, None
        if not name:
            return None, None, "the run records no pipeline name", None
        if not GITHUB_NAME_RE.match(name) or ".." in name:
            return None, None, ("%s is not a GitHub owner/repo, so there is nowhere "
                                "to fetch it from" % name), None
        rev = "" if rev is None else str(rev).strip()
        if not rev or rev.lower() in ("none", "null", "~"):
            return None, None, ("the run's versions file records no revision for %s, "
                                "so there is no version to fetch" % name), None
        if not REV_RE.match(rev) or ".." in rev:
            return None, None, ("the recorded revision %r is not one GitHub can serve"
                                % rev), None
        origin = "github.com/%s@%s %s" % (name, rev, path)
        cached = self._cache_path(name, rev, path)
        stale = None
        if cached and os.path.isfile(cached):
            with open(cached, encoding="utf-8", errors="replace") as fh:
                good = not_usable(path, fh.read()) is None
            if good and is_immutable(rev):
                return cached, origin, None, None
            if good:
                stale = cached   # a branch moves: fetch again, keep this as the fallback

        reason, bad = None, None
        for cand in revision_candidates(rev):
            text, reason = self.fetcher(name, cand, path)
            if text is not None:
                why = not_usable(path, text)
                if why is None:
                    f, warn = self._keep(cached, text)
                    return f, origin, None, warn
                bad = ("the file fetched from github.com/%s@%s is not a %s (%s; %s)"
                       % (name, cand, kind, why, snippet(text)))
                break
            if reason != "not found":
                break
        if bad:
            reason = bad
        elif reason == "not found":
            reason = "%s not found in %s at %s (HTTP 404)" % (
                path, name, " or ".join(revision_candidates(rev)))
        else:
            reason = "%s could not be fetched from %s@%s: %s" % (path, name, rev, reason)
        if stale:
            return stale, origin, None, (
                "%s was not refreshed (%s); the copy cached by an earlier build is "
                "used and may be out of date" % (path, reason))
        return None, None, reason, None

    def _cache_path(self, name, rev, path):
        if not self.cache_dir:
            return None
        return os.path.join(self.cache_dir, name, rev.replace("/", "_"), *path.split("/"))

    def _keep(self, dest, text):
        """Write atomically into the cache; fall back to scratch space.

        -> (path, warning or None)
        """
        warn = None
        if dest:
            try:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                tmp = dest + ".part%d" % os.getpid()
                with open(tmp, "w", encoding="utf-8") as fh:
                    fh.write(text)
                os.replace(tmp, dest)
                return dest, None
            except OSError as e:
                warn = ("the cache at %s could not be written (%s); the fetched file "
                        "was not kept and will be fetched again on the next build" % (dest, e))
        else:
            warn = ("no deployment root is known here, so the fetched file was not "
                    "kept and will be fetched again on every build")
        scratch = tempfile.mkdtemp(dir=_scratch_dir())
        f = os.path.join(scratch, os.path.basename(dest or "file"))
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(text)
        return f, warn


def parse_citations(path):
    """tool -> {"text": full citation, "doi": first DOI found}.

    The file's shape is regular across pipelines: `- [Tool](url)` followed by
    an indented `> citation`. Parsed rather than looked up, so a pipeline this
    has never seen works the same way.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return parse_citation_lines(fh)
    except OSError:
        return {}


def parse_citation_lines(lines):
    entries, current = {}, None
    for line in lines:
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


def render(run, assets_base, files=None):
    name = pipeline_name(run)
    wf = run.get("workflow") or {}
    tools = run.get("tools") or {}
    citable = run.get("citable_tools") or []
    lines, notes = [], []

    files = files or PipelineFiles()
    rev = wf.get(name) if name else None

    cits, cits_src, cits_why, cits_warn = files.get(name, rev, CITATIONS_PATH, assets_base)
    if cits_warn:
        notes.append(cits_warn)
    matched, missing = ([], [(t, []) for t in citable])
    if cits:
        matched, missing = match_tools(citable, parse_citations(cits))
    else:
        notes.append("no CITATIONS.md for %s: %s - every tool below is "
                     "unmatched for that reason alone, not because it is uncitable"
                     % (name, cits_why))

    # The template is only needed when the quality report has no rendered
    # paragraph to read, so it is only fetched then.
    rendered = rendered_methods(run.get("quality_report"))
    tmpl_src, tmpl_why, body = None, None, None
    if not rendered:
        tmpl, tmpl_src, tmpl_why, tmpl_warn = files.get(name, rev, TEMPLATE_PATH, assets_base)
        if tmpl_warn:
            notes.append(tmpl_warn)
        body = template_body(tmpl) if tmpl else None

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

    if rendered:
        # Fill only the gap MultiQC's own tool-citation matcher leaves empty -
        # never overwrite a slot the report already filled, because our own
        # match is not more authoritative than the report's own render.
        filled, n = EMPTY_P_RE.subn("<p>%s</p>" % tool_citations, rendered, count=1)
        if n == 0:
            filled = rendered
        filled, n = COMMAND_BLOCK_RE.subn("<pre><code>%s</code></pre>" % cmd, filled, count=1)
        filled = mark_unresolved_placeholders(filled)
        filled = fix_doubled_doi(filled)
        lines.append(html_to_md(filled))
        if run.get("quality_report"):
            lines.append("\nSource: `%s` (the report's own rendering of the pipeline's "
                         "methods template)"
                         % os.path.relpath(run["quality_report"], run["run_dir"]))
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
        filled = mark_unresolved_placeholders(filled)
        lines.append(html_to_md(filled))
        lines.append("\nSource: `%s` (the pipeline's methods template, filled here)"
                     % tmpl_src)
        notes.append("the command line shown is reconstructed against the run's "
                     "own params file; the one the report records points at an "
                     "ephemeral URL and cannot be re-run")
        notes.append("no rendered quality report was found, so the pipeline's DOI "
                     "could not be read from it - see the [DOI not shown] marker above")
    else:
        notes.append("no methods template for %s: %s - the paragraph below is only "
                     "the tool list, not the pipeline's own wording"
                     % (name, tmpl_why or "the file has no `data:` block"))
        lines.append("### Methods\n\nData was processed using %s %s with Nextflow %s."
                     % (name, wf.get(name, ""), wf.get("Nextflow", "")))

    lines.append("\n### Software\n")
    # #38 item 3: name where the list came from, as "Why these parameters" does.
    vsrc = (os.path.relpath(run["versions_file"], run["run_dir"])
            if run.get("versions_file") else "no versions file")
    csrc = cits_src if cits else "no CITATIONS.md"
    lines.append("Source: versions `%s`; citations `%s`\n" % (vsrc, csrc))
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
            # invariant 9: the source a piece of reasoning came from must be
            # named, not just the reasoning itself - the pointer used to live
            # only inside the comment block below, which vanishes on render.
            src = os.path.relpath(run["launch_params"], run["run_dir"])
            lines.append("\n### Why these parameters\n")
            lines.append("Source: `%s`\n" % src)
            for key, text in why:
                lines.append("- `%s` — %s" % (key, text))

    # The run's own notes (collect_provenance) count even when this script
    # added none - the guard used to be `if notes:` and dropped them silently
    # (acceptance review of #32).
    notes = notes + run.get("notes", [])
    if notes:
        # invisible-package-gaps item 1: these used to be wrapped in an HTML
        # comment, which a docx render drops and an html render only keeps in
        # page source - a reader never saw them. Written as ordinary visible
        # text instead, each one a [GAP: ...] so it reads as a gap rather
        # than as settled prose.
        lines.append("\n### Notes\n")
        for n in notes:
            lines.append("- [GAP: %s]" % n)
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(prog="methods_text.py")
    p.add_argument("results", nargs="+")
    p.add_argument("--assets", default=os.path.expanduser("~/.nextflow/assets"),
                   help="where pipeline sources are cached (default ~/.nextflow/assets)")
    p.add_argument("--cache-dir", default=os.environ.get("ABF_CACHE_DIR") or None,
                   help="where fetched pipeline files are kept (the deployment's own "
                        "cache; without it they are fetched again every run)")
    p.add_argument("--fetcher", default=os.environ.get("ABF_PIPELINE_FETCHER") or None,
                   help="command replacing the GitHub read (tests); 'off' disables it")
    p.add_argument("--out")
    args = p.parse_args(argv)
    if args.fetcher == "off":
        fetch = disabled_fetcher
    elif args.fetcher:
        fetch = command_fetcher(args.fetcher)
    else:
        fetch = curl_fetcher
    files = PipelineFiles(args.cache_dir, fetch)

    runs = provenance(args.results)
    if runs is None:
        return 2
    text = "\n\n".join(render(r, args.assets, files) for r in runs)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
