#!/usr/bin/env bash
# cloud-burn dynamic HOT list (REST only; GraphQL is blocked in cloud VMs). Writes /tmp/cb/hot_dynamic.txt and prints it.
# Sources: files of open PRs whose head branch is not a cloud-burn branch; files changed on origin branches
# (not cb, not v3/main/cloud/*) committed in the last 48 h; `HOT <path>` comments by zhshie on the tracking issue.
set -u
R=zhshie/agentic-bioflow_v2; ISSUE=${ISSUE:-317}; mkdir -p /tmp/cb; out=/tmp/cb/hot_dynamic.txt
git fetch origin --prune -q
{
  for n in $(gh api "repos/$R/pulls?state=open&per_page=100" --jq '.[] | select(.head.ref | test("/cb-|^cloud/") | not) | .number'); do
    gh api "repos/$R/pulls/$n/files?per_page=100" --jq '.[].filename'
  done
  now=$(date +%s)
  for b in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin | grep -v -e '/cb-' -e '^origin/cloud/' -e '^origin/v3$' -e '^origin/main$' -e '^origin/HEAD$'); do
    [ "$(git log -1 --format=%ct "$b")" -gt $(( now - 172800 )) ] && git diff --name-only origin/v3..."$b"
  done
  gh api --paginate "repos/$R/issues/$ISSUE/comments?per_page=100" --jq '.[] | select(.user.login=="zhshie") | .body' | grep -oE '^HOT [^ ]+' | cut -d' ' -f2
} 2>/dev/null | sed '/^$/d' | sort -u > "$out"
cat "$out"
