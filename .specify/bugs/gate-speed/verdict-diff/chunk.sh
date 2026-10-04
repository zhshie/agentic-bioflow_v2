#!/bin/bash
# chunk.sh <from> <to>: run job lines <from>..<to> of /tmp/abf34_jobs.txt (see replay.sh, PREP_ONLY=1)
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sed -n "${1},${2}p" /tmp/abf34_jobs.txt | xargs -P 6 -L 1 bash "$HERE/worker.sh" >> /tmp/abf34_results.txt
echo "results so far: $(wc -l < /tmp/abf34_results.txt) of $(wc -l < /tmp/abf34_jobs.txt)"
