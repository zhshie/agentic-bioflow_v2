#!/bin/bash
# DOIs in, BibTeX out. Nothing here is written from memory.
#
#   cite.sh [--cache <dir>] [--out <file>] <doi|@file> ...
#
# A citation a language model recalls is a citation that may not exist, and a
# fabricated reference in a methods section is worse than a missing one:
# missing is visible. So every entry this produces came back from a resolver
# over the network, and every one that did not is left in the output as a
# marker a reader cannot miss.
#
# The resolver is DOI content negotiation, which is the registrars' own
# service and needs no key:
#
#     curl -LH 'Accept: application/x-bibtex' https://doi.org/<doi>
#
# Measured from this cluster's login node 2026-09-10: returns a complete entry
# with authors, journal, year and DOI.
#
# @file reads DOIs from a file, one per line, in the shape a quality report
# records them - `10.xxxx/yyy   # toolname` - so the report's own citation
# list can be piped straight in.
#
# Cached by DOI under --cache, because re-rendering a manuscript should not
# re-ask the network for the same twenty references, and because a cache is
# what lets this be tested without one.
set -uo pipefail

CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/agentic-bioflow/cite"
OUT=""
CURL="${CITE_CURL:-curl}"     # the seam: tests point this at something that fails
ARGS=()

while [ $# -gt 0 ]; do
    case "$1" in
        --cache) CACHE="${2:?--cache needs a value}"; shift 2 ;;
        --out)   OUT="${2:?--out needs a value}"; shift 2 ;;
        -h|--help)
            sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) ARGS+=("$1"); shift ;;
    esac
done

[ "${#ARGS[@]}" -gt 0 ] || { echo "usage: cite.sh [--cache <dir>] [--out <file>] <doi|@file> ..." >&2; exit 2; }
mkdir -p "$CACHE" || { echo "cite.sh: cannot use cache dir $CACHE" >&2; exit 1; }

# One flat list of doi<TAB>label. The label is only ever used to say what is
# missing; it never reaches the BibTeX.
entries=()
for a in "${ARGS[@]}"; do
    case "$a" in
        @*)
            f="${a#@}"
            [ -r "$f" ] || { echo "cite.sh: cannot read $f" >&2; exit 2; }
            while IFS= read -r line; do
                doi=$(sed -nE 's/^[[:space:]]*(10\.[0-9]{4,9}\/[^[:space:]]+).*/\1/p' <<<"$line")
                [ -n "$doi" ] || continue
                label=$(sed -nE 's/^[^#]*#[[:space:]]*(.*)$/\1/p' <<<"$line")
                entries+=("$doi	${label:-$doi}")
            done < "$f" ;;
        10.*) entries+=("$a	$a") ;;
        *) echo "cite.sh: '$a' is not a DOI and not @file" >&2; exit 2 ;;
    esac
done

emit() { if [ -n "$OUT" ]; then printf '%s\n' "$1" >> "$OUT"; else printf '%s\n' "$1"; fi; }
[ -n "$OUT" ] && : > "$OUT"

missing=0
seen=""
for e in "${entries[@]}"; do
    doi="${e%%	*}"; label="${e#*	}"
    case " $seen " in *" $doi "*) continue ;; esac
    seen="$seen $doi"

    key=$(printf '%s' "$doi" | tr '/' '_' | tr -cd 'A-Za-z0-9._-')
    hit="$CACHE/$key.bib"
    if [ ! -s "$hit" ]; then
        body=$("$CURL" -sLH 'Accept: application/x-bibtex' \
               --max-time 20 "https://doi.org/$doi" 2>/dev/null)
        # A resolver that does not know the DOI answers with prose, not an
        # entry. Requiring the @ sigil is what stops an error page being
        # cached and cited - but the real service answers with a leading
        # space before it, so an anchored match on `@` rejects every genuine
        # reply. Measured, after this refused two DOIs that resolve fine by
        # hand: trim first, then check.
        body=$(printf '%s' "$body" | sed -e 's/^[[:space:]]*//')
        case "$body" in
            @*) printf '%s\n' "$body" > "$hit" ;;
            *)  : ;;
        esac
    fi

    if [ -s "$hit" ]; then
        emit "$(cat "$hit")"
        emit ""
    else
        # Loud on purpose, and in the file rather than only on the terminal:
        # a reference that quietly disappears is how a methods section comes
        # to look complete while under-citing the work it used.
        emit "% CITATION NEEDED: $label (doi $doi could not be resolved)"
        emit ""
        echo "cite.sh: could not resolve $doi ($label)" >&2
        missing=$((missing+1))
    fi
done

if [ "$missing" -gt 0 ]; then
    echo "cite.sh: $missing citation(s) unresolved - they are marked CITATION NEEDED in the output, not dropped." >&2
    exit 3
fi
exit 0
