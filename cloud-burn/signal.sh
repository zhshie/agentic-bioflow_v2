#!/usr/bin/env bash
# cloud-burn control signal from the tracking issue (newest owner comment that is a control word wins).
# prints one line: GO | STOP | PAUSE | <plus> SKIP ids / SHARD X STOP lines; and the UTC time.
set -u
R=zhshie/agentic-bioflow_v2; ISSUE=${ISSUE:-317}; SHARD=${SHARD:-}
bodies=$(gh api --paginate "repos/$R/issues/$ISSUE/comments?per_page=100" --jq '.[] | select(.user.login=="zhshie") | .body' 2>/dev/null)
sig=GO
while IFS= read -r line; do
  case "$line" in
    STOP*) sig=STOP; break;;
    "SHARD $SHARD STOP"*) [ -n "$SHARD" ] && { sig=STOP; break; };;
    PAUSE*) sig=PAUSE; break;;
    RESUME*) sig=GO; break;;
  esac
done <<< "$(printf '%s\n' "$bodies" | grep -E '^(STOP|PAUSE|RESUME|SHARD [A-Z] STOP)' | tac)"
skips=$(printf '%s\n' "$bodies" | grep -oE '^SKIP [A-Za-z0-9]+' | cut -d' ' -f2 | sort -u | tr '\n' ' ')
echo "signal=$sig skip=[${skips% }] utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
