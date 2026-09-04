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

[ "$fail" = 0 ] && echo "OK: nothing is configured per pipeline; launch.md still reads the pipeline"
exit $fail
