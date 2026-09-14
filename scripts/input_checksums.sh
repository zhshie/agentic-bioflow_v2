#!/bin/bash
# Reuse or compute a SHA-256 for every input file a samplesheet names.
#
# Not nf-prov's own checksums: whether nf-prov already records these on this
# cluster is unmeasured (plan M1), so this still computes or reuses them.
#
#   input_checksums.sh --samplesheet <csv> --out <file>
#                       [--known <sha256sum-format list>] [--force]
#
# Proposal R4 (docs/LAB_AGENTS.md section A3, row R4): prefer whatever
# checksum a lab's own intake process already recorded over spending a login
# node's CPU re-hashing a file that can run tens of gigabytes. A value found
# in --known is copied out verbatim; the file itself is never touched by a
# hashing tool in that case.
#
# Pipeline-agnostic: no pipeline's column names are known here. A cell
# qualifies as a file if it is a path that exists - resolved against the
# samplesheet's OWN directory, the same convention `sha256sum -c` itself
# uses - or if its text ends in one of .fastq.gz/.fq.gz/.fastq/.fq/.bam/.cram,
# which is what lets a reference to a file that SHOULD be there but is not
# still get reported as `missing` rather than silently skipped like an
# ordinary non-file cell (a sample name, "auto", a numeric field). A cell that
# looks like a URL (any `scheme://`) is reported `not-local` instead -
# s3://, https:// and similar are not this script's to reach across: it makes
# no network call anywhere in it.
#
# Two files come out, because a per-file source note has no home inside the
# `sha256sum` format itself:
#   <out>              pure `sha256sum` format - `sha256sum -c` run from the
#                       samplesheet's own directory verifies it directly
#   <out>.sources.tsv  path<TAB>size_bytes<TAB>source, source one of
#                       known|known-by-name|computed|not-local|missing. size_bytes is `-`
#                       for not-local and missing rows, where there is no
#                       local size to report.
#
# --known: a standard `sha256sum`-format list (<hex>  <path>, one entry per
# line - the exact format this script's own <out> is written in, so a lab's
# manifest and this script's own prior output both read back in). It carries
# no size field, so the "prefer an existing value" match is tried two ways
# and the second is flagged rather than silently trusted: first by absolute
# path (a known entry's path, resolved against --known's own directory when
# it is relative, symlinks resolved the same way a candidate file's path is);
# failing that, by basename alone - recorded as source `known-by-name` in
# sources.tsv (and noted on stderr) because a basename match says nothing about
# which directory the value came from, and sequencing files share names across
# sample directories all the time.
#
# Meant to run where the data is - through `scripts/on_site.sh --script
# input_checksums.sh ...` with ON_SITE_TIMEOUT=0 for a large samplesheet, so a
# genuinely long hash is never raced against the usual clock. This script
# itself makes no ssh call anywhere in it; on_site.sh is what carries it
# there when the data is not local to begin with.
#
# Exit: 0 clean. 1 - at least one referenced file is missing; both output
# files are still written in full first. 2 - bad usage, an unreadable input,
# an existing --out or --out.sources.tsv without --force, or no sha256sum/
# shasum on PATH at all when one is actually needed to compute a value (a
# file already covered by --known never triggers this).
#
# Not sha256deep/hashdeep: neither ships in this repo's containers or on a
# stock login node, and the one thing this script needs beyond a plain
# checksum - "did a lab already know this one" - is not something either
# tool answers.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/utils/portable.sh"

die() { local rc="$1"; shift; printf '%s\n' "$@" >&2; exit "$rc"; }
usage() {
    die 2 "usage: input_checksums.sh --samplesheet <csv> --out <file> [--known <sha256-list>] [--force]"
}

SAMPLESHEET="" OUT="" KNOWN="" FORCE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --samplesheet) [ $# -ge 2 ] || usage; SAMPLESHEET="$2"; shift 2 ;;
        --out)         [ $# -ge 2 ] || usage; OUT="$2"; shift 2 ;;
        --known)       [ $# -ge 2 ] || usage; KNOWN="$2"; shift 2 ;;
        --force)       FORCE=1; shift ;;
        -h|--help)     usage ;;
        *)             usage ;;
    esac
done
[ -n "$SAMPLESHEET" ] && [ -n "$OUT" ] || usage
[ -r "$SAMPLESHEET" ] || die 2 "samplesheet not readable: $SAMPLESHEET"
[ -z "$KNOWN" ] || [ -r "$KNOWN" ] || die 2 "--known list not readable: $KNOWN"
command -v python3 >/dev/null 2>&1 \
    || die 2 "python3 not found - needed to read the samplesheet as CSV."

if [ "$FORCE" != 1 ]; then
    [ -e "$OUT" ] && die 2 "refusing to overwrite existing '$OUT' without --force."
    [ -e "${OUT}.sources.tsv" ] \
        && die 2 "refusing to overwrite existing '${OUT}.sources.tsv' without --force."
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

SHEET_DIR="$(cd "$(dirname "$SAMPLESHEET")" && pwd)"

# --- every distinct, non-empty cell in the sheet, in first-seen order -------
# A real CSV parser, not an IFS=, split: nf-core samplesheets are ordinary
# CSV, and a hand-rolled split breaks the moment a value is quoted.
CANDS="$WORK/candidates.txt"
python3 - "$SAMPLESHEET" > "$CANDS" <<'PY'
import csv, sys
seen = []
seenset = set()
with open(sys.argv[1], newline='') as f:
    for row in csv.reader(f):
        for cell in row:
            c = cell.strip()
            if c and c not in seenset:
                seenset.add(c)
                seen.append(c)
for c in seen:
    print(c)
PY

# --- --known, normalised once ------------------------------------------------
# abspath<TAB>hex and basename<TAB>hex, built once rather than re-reading
# --known for every cell in the sheet.
KNOWN_BY_PATH="$WORK/known_by_path.tsv"
KNOWN_BY_NAME="$WORK/known_by_name.tsv"
: > "$KNOWN_BY_PATH"; : > "$KNOWN_BY_NAME"
if [ -n "$KNOWN" ]; then
    KNOWN_DIR="$(cd "$(dirname "$KNOWN")" && pwd)"
    while IFS= read -r kline || [ -n "$kline" ]; do
        [ -n "$kline" ] || continue
        case "$kline" in \#*) continue ;; esac
        # sha256sum format: <64 hex><space><mode-char><path>, mode is ' ' or
        # '*'. [[:space:]]+ swallows both characters when mode is a plain
        # space (the common case), leaving only the '*' branch to strip.
        if [[ "$kline" =~ ^([0-9a-fA-F]{64})[[:space:]]+(.*)$ ]]; then
            khex="$(printf '%s' "${BASH_REMATCH[1]}" | tr 'A-F' 'a-f')"
            kpath="${BASH_REMATCH[2]}"
            case "$kpath" in \**) kpath="${kpath#\*}" ;; esac
            case "$kpath" in
                /*) kabs="$kpath" ;;
                *)  kabs="$KNOWN_DIR/$kpath" ;;
            esac
            kabs_resolved="$(resolve_link "$kabs" 2>/dev/null)"
            [ -n "$kabs_resolved" ] && kabs="$kabs_resolved"
            printf '%s\t%s\n' "$kabs" "$khex" >> "$KNOWN_BY_PATH"
            printf '%s\t%s\n' "$(basename "$kpath")" "$khex" >> "$KNOWN_BY_NAME"
        fi
    done < "$KNOWN"
fi

hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum -- "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 -- "$1" | awk '{print $1}'
    else
        return 3
    fi
}

OUT_TMP="$WORK/out.sha256"
SRC_TMP="$WORK/sources.tsv"
: > "$OUT_TMP"
printf '# path\tsize_bytes\tsource\n' > "$SRC_TMP"

URL_RE='^[A-Za-z][A-Za-z0-9+.-]*://'
EXT_RE='\.(fastq\.gz|fq\.gz|fastq|fq|bam|cram)$'
missing_any=0

while IFS= read -r cell || [ -n "$cell" ]; do
    [ -n "$cell" ] || continue

    if [[ "$cell" =~ $URL_RE ]]; then
        printf '%s\t-\tnot-local\n' "$cell" >> "$SRC_TMP"
        continue
    fi

    case "$cell" in
        /*) test_path="$cell" ;;
        *)  test_path="$SHEET_DIR/$cell" ;;
    esac

    looks_like_a_read=0
    [[ "$cell" =~ $EXT_RE ]] && looks_like_a_read=1

    if [ -f "$test_path" ]; then
        : # a real, existing candidate - fall through to hashing below
    elif [ "$looks_like_a_read" = 1 ]; then
        printf '%s\t-\tmissing\n' "$cell" >> "$SRC_TMP"
        missing_any=1
        continue
    else
        continue   # not file-shaped at all - a sample name, a flag, ...
    fi

    size="$(stat_size "$test_path" 2>/dev/null)"
    [ -n "$size" ] || size="-"

    cand_abs="$(resolve_link "$test_path" 2>/dev/null)"
    [ -n "$cand_abs" ] || cand_abs="$test_path"

    hex=""; src="known"
    if [ -s "$KNOWN_BY_PATH" ]; then
        hex="$(awk -F'\t' -v want="$cand_abs" '$1==want{print $2; exit}' "$KNOWN_BY_PATH")"
    fi
    if [ -z "$hex" ] && [ -s "$KNOWN_BY_NAME" ]; then
        bn="$(basename "$cell")"
        hex="$(awk -F'\t' -v want="$bn" '$1==want{print $2; exit}' "$KNOWN_BY_NAME")"
        if [ -n "$hex" ]; then
            echo "input_checksums: matched-by-name (no path match in --known): $cell" >&2
            src="known-by-name"
        fi
    fi

    if [ -z "$hex" ]; then
        hex="$(hash_file "$test_path")" \
            || die 2 "no sha256sum or shasum on PATH - cannot hash '$cell'."
        src="computed"
    fi

    printf '%s  %s\n' "$hex" "$cell" >> "$OUT_TMP"
    printf '%s\t%s\t%s\n' "$cell" "$size" "$src" >> "$SRC_TMP"
done < "$CANDS"

mv "$OUT_TMP" "$OUT"
mv "$SRC_TMP" "${OUT}.sources.tsv"

if [ "$missing_any" = 1 ]; then
    echo "input_checksums: one or more referenced files are missing - see ${OUT}.sources.tsv" >&2
    exit 1
fi
exit 0
