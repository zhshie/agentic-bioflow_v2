#!/bin/bash
# Invariants 1 and 6: build only what nf-core already provides, and any pipeline
# must run with no configuration.
#
# v1 died of the opposite. It carried one spec file per pipeline - a manual, a
# curated parameter list, a list of optional tools - and paid twice: a pipeline
# nobody had written a file for could not be run at all, and every file that did
# exist went stale on the next upstream release.
#
# v2's replacement is that everything the user is shown or asked comes from the
# pipeline at the pinned revision. This guards both halves: that no per-pipeline
# file has crept back, and that the command layer still says to read the
# pipeline rather than a copy of it.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
fail=0

# 1. No per-pipeline directory, whatever it is called underneath.
found=$(find "$ROOT" -path "$ROOT/.git" -prune -o -type d -name pipelines -print 2>/dev/null)
if [ -n "$found" ]; then
    echo "FAIL: a pipelines/ directory is back:"
    printf '  %s\n' $found
    fail=1
fi

# 2. configs/ holds site adapters and nothing else. A configs/pipelines/ or a
#    configs/rnaseq.config is the same regression wearing a different hat.
for d in "$ROOT"/configs/*; do
    [ -e "$d" ] || continue
    case "$(basename "$d")" in
        sites) ;;
        *) echo "FAIL: configs/$(basename "$d") — configs/ holds site adapters only"; fail=1 ;;
    esac
done

# 3. The command layer still derives from the pipeline itself. If these
#    references disappear, the answers they used to fetch are being carried
#    somewhere instead - which is the regression, whether or not a file named
#    after a pipeline ever appears.
for want in 'nextflow_schema.json' 'assets/schema_input.json' 'docs/images/'; do
    grep -qF "$want" "$ROOT/commands/launch.md" || {
        echo "FAIL: commands/launch.md no longer mentions $want"
        fail=1
    }
done

# 4. scripts/inventory_outputs.py reports what a results tree contains. The
#    tempting shortcut is a lookup table - "this tool writes report.tsv, its
#    columns are these" - which is v1's spec file reborn one entry at a time,
#    and which goes wrong silently: the tree still gets inventoried, just with
#    the columns the table remembers rather than the ones on disk. There is no
#    honest reason for a tool name to appear in a script that opens files and
#    reads their headers, so the absence of one is the guardrail.
INV="$ROOT/scripts/inventory_outputs.py"
if [ -f "$INV" ]; then
    TOOLS='quast|busco|prokka|multiqc|fastqc|salmon|star|kraken|bracken|dada2|qiime|spades|flye|medaka|porechop|nanoplot|samtools|bwa|bowtie|hisat|kallisto|deseq2|featurecounts|trimgalore|cutadapt|picard|gatk|bcftools|vcftools|megahit|checkm|gtdbtk|abricate|amrfinder'
    if hits=$(grep -inE "\\b($TOOLS)\\b" "$INV"); then
        echo "FAIL: scripts/inventory_outputs.py names a pipeline tool:"
        printf '  %s\n' "$hits"
        echo "  It must report what it finds on disk, not what it remembers a tool writes."
        fail=1
    fi
fi

# 5. commands/downstream.md is the same guardrail wearing a different hat: it
#    must learn from the inventory in front of it, never from a remembered
#    list of what one pipeline's tool writes. A tool name or a specific output
#    filename here is v1's per-pipeline table growing back one line of prose
#    at a time - see the guardrail note inside the file itself.
DS="$ROOT/commands/downstream.md"
if [ -f "$DS" ]; then
    DS_LITERALS='report\.tsv|short_summary'
    if hits=$(grep -inE "\\b($TOOLS|$DS_LITERALS)\\b" "$DS"); then
        echo "FAIL: commands/downstream.md names a pipeline tool or output file:"
        printf '  %s\n' "$hits"
        echo "  It must read the results tree at run time, not remember what one pipeline wrote."
        fail=1
    fi
fi

[ "$fail" = 0 ] && echo "OK: nothing is configured per pipeline; launch.md still reads the pipeline"
exit $fail
