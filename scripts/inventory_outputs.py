#!/bin/bash
# What did this run actually produce, and what shape is each file?
#
#     inventory_outputs.py [--max-depth N] [--max-mb N] [--json] <results-dir>
#
# Written for the step after a run finishes: before anyone writes a line of
# plotting or stats code, they need the real column names, not remembered ones.
#
# It knows nothing about any pipeline, and must not learn. v1 of this plugin
# died of one spec file per pipeline - a curated list of "this tool writes
# report.tsv with these columns" that went stale on the next upstream release
# and left an unlisted pipeline unusable. So there is no filename table and no
# tool name here: it opens what it finds and reports what the bytes say.
# tests/no_per_pipeline_config.sh greps this file to keep that true.
#
# ---------------------------------------------------------------------------
# The header below is a shell/Python polyglot, and it is here for one reason:
# PITFALLS 16d. On this cluster /usr/bin/python3 is RHEL's own reserved
# interpreter, mode 750 root:root - present, on PATH, and unrunnable, so a
# plain `#!/usr/bin/env python3` dies with a bare `Permission denied` that
# reads like a broken install of this plugin. require_python.sh explains the
# fence and points at the module system, but a guard written in Python cannot
# run when Python is what is fenced. So the file is entered as a shell script,
# clears the guard, and only then hands itself to python3 - the same thing
# egress_ctl.sh and agent_ctl.sh do, moved inside the file because this script
# is invoked directly. Running it as `python3 inventory_outputs.py` still works;
# the shell block is then just a string.
''''true
HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
if [ -f "$HERE/require_python.sh" ]; then
    . "$HERE/require_python.sh"
    require_python || exit 1
fi
exec python3 "$0" "$@"
'''

import argparse
import csv
import json
import os
import sys

USAGE = "inventory_outputs.py [--max-depth N] [--max-mb N] [--json] <results-dir>"

# Extensions decide only which parser to *try*. What the file actually is comes
# from its bytes: a pipeline that writes TSV into a .txt is the normal case
# here, not the exception, and trusting the name is how a downstream reader ends
# up with one column called "everything".
TABULAR_EXT = {".tsv", ".csv", ".txt", ".tab", ".dat"}
JSON_EXT = {".json"}
YAML_EXT = {".yaml", ".yml"}
# Rendered output. Named and sized, never opened - a report is for a person, and
# there is nothing in it a plotting script can key off.
OPAQUE_EXT = {
    ".html", ".htm", ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".bmp", ".tif", ".tiff",
}

# Scratch, defined by shape rather than by who wrote it. A staging or work
# directory next to results holds a copy of everything, so walking it doubles
# the report and buries the part a person needs.
SCRATCH_DIRS = {"work", "tmp", "temp", "__pycache__", "node_modules", "cache"}
SCRATCH_SUFFIX = (".tmp", ".partial", ".swp", ".pyc", "~")

DELIMITERS = ("\t", ",", ";", "|")
SNIFF_ROWS = 6          # enough to catch an inconsistent split, cheap to hold
MAX_PREAMBLE = 500      # a comment banner longer than this is not a banner


# ------------------------------------------------------------------ utilities

def human(n):
    for unit, step in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if n >= step:
            return "%.1f %s" % (n / float(step), unit)
    return "%d B" % n


def looks_binary(path, probe=8192):
    """A NUL, or a lot of undecodable bytes, in the first few KB.

    Cheaper and more reliable than trusting the extension, which is the point:
    a .txt holding a compressed blob must not be handed to a delimiter sniffer.
    """
    try:
        with open(path, "rb") as fh:
            chunk = fh.read(probe)
    except OSError:
        return True
    if not chunk:
        return False
    if b"\x00" in chunk:
        return True
    try:
        chunk.decode("utf-8")
    except UnicodeDecodeError:
        # A multi-byte character straddling the probe boundary is not evidence
        # of a binary file; a high density of undecodable bytes is.
        bad = sum(1 for b in chunk if b < 9 or (13 < b < 32))
        return bad > len(chunk) * 0.05
    return False


# ------------------------------------------------------------ shape detection

def _fields(line, delim):
    return next(csv.reader([line], delimiter=delim))


def pick_delimiter(lines):
    """The delimiter that splits every sample line into the same >1 columns.

    Quoting is respected (csv, not str.split), because a comma inside a quoted
    note is the classic way a CSV is mis-read as having one extra column.
    Ties go to the earlier candidate, which puts tab ahead of comma - the right
    bias for a tree where most tables are tab-separated.
    """
    best, best_cols = None, 1
    for delim in DELIMITERS:
        counts = set()
        for line in lines:
            try:
                counts.add(len(_fields(line, delim)))
            except csv.Error:
                counts.add(0)
        if len(counts) == 1:
            cols = counts.pop()
            if cols > best_cols:
                best, best_cols = delim, cols
    return best, best_cols


def read_table(path):
    """One streaming pass: preamble, a few sample lines, and a row count.

    Never holds the file. A published count matrix is hundreds of MB and the
    only thing wanted from it is the header and how many rows there are, so
    reading it into memory to call len() would be the whole cost of the script.
    """
    preamble, sample = [], []
    body = 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.rstrip("\r\n")
                if not sample and not body:
                    # Only a *leading* run of '#' lines is a preamble. Once real
                    # data has started, a '#' at the start of a line is data:
                    # metric names beginning with '#' are common in assembly
                    # reports, and treating them as comments deletes most of
                    # the file.
                    if s.startswith("#"):
                        if len(preamble) < MAX_PREAMBLE:
                            preamble.append(s)
                        continue
                    if not s.strip():
                        continue
                if not s.strip():
                    continue
                if len(sample) < SNIFF_ROWS:
                    sample.append(s)
                body += 1
    except OSError as exc:
        return {"kind": "unreadable", "note": str(exc)}

    # A file that is nothing but a comment banner is a real result - "no hits" -
    # and reporting it as an empty text file loses the only thing it says.
    if not sample:
        return {"kind": "text", "lines": 0, "preamble_lines": len(preamble)}

    delim, ncols = pick_delimiter(sample)
    if delim is None:
        return {"kind": "text", "lines": body, "preamble_lines": len(preamble)}

    # A preamble whose last line splits the same way the data does is a header
    # wearing a '#' - the shape nf-core's stats files ship in. Anything else in
    # the preamble is a banner and is reported as such, not as data.
    header_line, rows = sample[0], body - 1
    if preamble:
        candidate = preamble[-1].lstrip("#").lstrip()
        try:
            if len(_fields(candidate, delim)) == ncols:
                header_line, rows = candidate, body
        except csv.Error:
            pass

    columns = [c.strip() for c in _fields(header_line, delim)]
    return {
        "kind": "table",
        "delimiter": delim,
        "columns": columns,
        "rows": max(rows, 0),
        "preamble_lines": len(preamble),
    }


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            obj = json.load(fh)
    except (OSError, ValueError) as exc:
        return {"kind": "unreadable", "note": str(exc)}
    if isinstance(obj, dict):
        return {"kind": "json", "container": "object", "keys": list(obj.keys())}
    if isinstance(obj, list):
        shape = {"kind": "json", "container": "array", "length": len(obj)}
        if obj and isinstance(obj[0], dict):
            shape["item_keys"] = list(obj[0].keys())
        return shape
    return {"kind": "json", "container": type(obj).__name__}


def read_yaml(path):
    """Top-level keys only, by indentation.

    Deliberately not a YAML parser: the standard library has none, this must run
    under a bare python3, and the question being answered is only "what is in
    here". A block scalar containing an unindented 'x:' would be misread; that
    is the accepted cost of not vendoring a parser.
    """
    keys = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if len(keys) > 200:
                    break
                s = line.rstrip("\r\n")
                if not s.strip() or s[0] in " \t#-" or s.startswith("..."):
                    continue
                if ":" not in s:
                    continue
                key = s.split(":", 1)[0].strip().strip("'\"")
                if key and key not in keys:
                    keys.append(key)
    except OSError as exc:
        return {"kind": "unreadable", "note": str(exc)}
    return {"kind": "yaml", "keys": keys}


# -------------------------------------------------------------------- walking

def is_scratch_dir(name):
    return name.startswith(".") or name.lower() in SCRATCH_DIRS


def is_scratch_file(name):
    return name.startswith(".") or name.lower().endswith(SCRATCH_SUFFIX)


def inventory(root, max_depth, max_bytes):
    files, skipped = [], []
    total = 0

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1

        keep = []
        for d in sorted(dirnames):
            if is_scratch_dir(d):
                skipped.append({
                    "path": os.path.join(rel_dir, d) if rel_dir != "." else d,
                    "size": None, "reason": "scratch (directory, not walked)",
                })
            else:
                keep.append(d)
        # max_depth counts path components below the root, so files sitting in a
        # directory at the limit are still reported; only descending stops.
        dirnames[:] = [] if max_depth is not None and depth + 1 >= max_depth else keep

        for name in sorted(filenames):
            rel = name if rel_dir == "." else os.path.join(rel_dir, name)
            full = os.path.join(dirpath, name)
            if is_scratch_file(name):
                skipped.append({"path": rel, "size": None, "reason": "scratch"})
                continue
            try:
                size = os.stat(full).st_size
            except OSError as exc:
                skipped.append({"path": rel, "size": None,
                                "reason": "unreadable (%s)" % exc.strerror})
                continue
            total += size

            ext = os.path.splitext(name)[1].lower()
            entry = {"path": rel, "size": size}

            if ext in OPAQUE_EXT:
                entry.update(kind="opaque", format=ext.lstrip("."))
                files.append(entry)
                continue
            if ext not in TABULAR_EXT and ext not in JSON_EXT and ext not in YAML_EXT:
                entry.update(kind="other", format=ext.lstrip(".") or "none")
                files.append(entry)
                continue

            if size > max_bytes:
                skipped.append({"path": rel, "size": size,
                                "reason": "larger than --max-mb %g" % (max_bytes / 1048576.0)})
                continue
            if looks_binary(full):
                skipped.append({"path": rel, "size": size, "reason": "binary"})
                continue

            if ext in JSON_EXT:
                entry.update(read_json(full))
            elif ext in YAML_EXT:
                entry.update(read_yaml(full))
            else:
                entry.update(read_table(full))
            files.append(entry)

    return {"root": os.path.abspath(root), "files": files, "skipped": skipped,
            "bytes": total, "max_mb": max_bytes / 1048576.0,
            "max_depth": max_depth}


# ------------------------------------------------------------------ rendering

def names(cols):
    """Column names, quoted where one contains the separator between them.

    Headerless tables are common, so the first data row often lands here - and a
    free-text field with a comma in it then reads as two columns, which is
    exactly the miscount this script exists to prevent.
    """
    return ", ".join('"%s"' % c if ("," in c or not c) else c for c in cols)


def describe(f):
    """The one-line shape, and an optional continuation line of names."""
    kind = f.get("kind")
    if kind == "table":
        d = {"\t": "tsv", ",": "csv", ";": "ssv", "|": "psv"}.get(f["delimiter"], "delimited")
        head = "%s, %d cols x %d rows" % (d, len(f["columns"]), f["rows"])
        if f.get("preamble_lines"):
            head += " (after %d comment line%s)" % (
                f["preamble_lines"], "" if f["preamble_lines"] == 1 else "s")
        return head, names(f["columns"])
    if kind == "text":
        head = "text, %d lines, no delimiter found" % f.get("lines", 0)
        if f.get("preamble_lines"):
            head += " (+ %d comment line%s)" % (
                f["preamble_lines"], "" if f["preamble_lines"] == 1 else "s")
        return head, None
    if kind == "json":
        if f.get("container") == "object":
            return "json object, %d keys" % len(f["keys"]), names(f["keys"])
        if f.get("container") == "array":
            head = "json array, %d items" % f["length"]
            if "item_keys" in f:
                return head, "item keys: " + names(f["item_keys"])
            return head, None
        return "json %s" % f.get("container", "scalar"), None
    if kind == "yaml":
        return "yaml, %d top-level keys" % len(f["keys"]), names(f["keys"])
    if kind == "opaque":
        return "%s (not parsed)" % f.get("format", "rendered"), None
    if kind == "unreadable":
        return "unreadable: %s" % f.get("note", ""), None
    return None, None


def render(inv, out):
    files, skipped = inv["files"], inv["skipped"]
    described = [f for f in files if f.get("kind") != "other"]
    print("inventory of %s" % inv["root"], file=out)
    print("  %d files, %s, %d described / %d not structured; parsed up to --max-mb %g"
          % (len(files), human(inv["bytes"]), len(described),
             len(files) - len(described), inv["max_mb"]), file=out)
    if inv["max_depth"] is not None:
        print("  --max-depth %d, so anything deeper is not listed" % inv["max_depth"], file=out)

    by_dir = {}
    for f in files:
        by_dir.setdefault(os.path.dirname(f["path"]) or ".", []).append(f)

    for d in sorted(by_dir):
        print("", file=out)
        print("%s/" % ("." if d == "." else d), file=out)
        others = {}
        for f in sorted(by_dir[d], key=lambda x: x["path"]):
            if f.get("kind") == "other":
                fmt = f.get("format", "none")
                n, b = others.get(fmt, (0, 0))
                others[fmt] = (n + 1, b + f["size"])
                continue
            head, cont = describe(f)
            print("  %-46s %10s  %s"
                  % (os.path.basename(f["path"]), human(f["size"]), head), file=out)
            if cont:
                print("      %s" % cont, file=out)
        if others:
            parts = ["." + k if k != "none" else "no extension" for k in sorted(others)]
            parts = ["%s %d (%s)" % (p, others[k][0], human(others[k][1]))
                     for p, k in zip(parts, sorted(others))]
            print("  + %d other file(s): %s"
                  % (sum(v[0] for v in others.values()), ", ".join(parts)), file=out)

    if skipped:
        print("", file=out)
        print("skipped (%d)" % len(skipped), file=out)
        for s in sorted(skipped, key=lambda x: x["path"]):
            size = human(s["size"]) if s["size"] is not None else ""
            print("  %-46s %10s  %s" % (s["path"], size, s["reason"]), file=out)


def main(argv):
    ap = argparse.ArgumentParser(
        prog="inventory_outputs.py",
        description="Report what a finished results tree contains and what shape "
                    "each structured file is. Knows nothing about any pipeline.")
    ap.add_argument("results_dir")
    ap.add_argument("--max-depth", type=int, default=None,
                    help="stop descending this many components below the root")
    ap.add_argument("--max-mb", type=float, default=20.0,
                    help="do not open a file larger than this (default 20)")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="emit the same report machine-readably")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.results_dir):
        print("not a directory: %s\n\n    %s" % (args.results_dir, USAGE), file=sys.stderr)
        return 2

    inv = inventory(args.results_dir, args.max_depth, int(args.max_mb * 1048576))
    if args.as_json:
        json.dump(inv, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        render(inv, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
