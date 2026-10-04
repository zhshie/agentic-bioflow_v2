#!/bin/bash
# Verdict diff of two hook trees (#34). Run in WSL/Linux, in this order:
#   bash capture.sh <gate tests...>   (baseline tree: records every payload the tests feed the hooks)
#   bash replay.sh                    (builds the corpus, runs old and new hooks, prints SAME/DIFF counts)
# SRC below is the folder holding the worktrees wt-34 (new) and wt-34-base (baseline).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# abf_34_replay.sh  - copy baseline (A) and current (B) trees, build contexts, replay corpus.
SRC=/mnt/c/Users/ACER/Desktop/agentic-bioflow
rm -rf /tmp/abf34_A /tmp/abf34_B /tmp/abf34_res /tmp/abf34_ctx
mkdir -p /tmp/abf34_A /tmp/abf34_B
cp -r "$SRC/wt-34-base/." /tmp/abf34_A/ 2>/dev/null; rm -rf /tmp/abf34_A/.git
cp -r "$SRC/wt-34/." /tmp/abf34_B/ 2>/dev/null; rm -rf /tmp/abf34_B/.git
# the base copy carries my uncommitted test copy only; make sure its hooks are pristine
( cd "$SRC/wt-34-base" && git status --short hooks )
C=/tmp/abf34_ctx
mkdir -p "$C/work" "$C/home" "$C/state/in-use"
: > "$C/state/in-use/s1"
for i in $(seq 1 200); do printf '{"type":"user","message":{"content":"hello %s"}}\n' "$i"; done > "$C/tr_plain.jsonl"
{ cat "$C/tr_plain.jsonl"
  printf '%s\n' '{"type":"user","message":{"content":"<command-name>/agentic-bioflow:launch</command-name>"}}'
  printf '%s\n' '{"type":"assistant","message":{"content":[{"type":"text","text":"ok"}]}}'
} > "$C/tr_slash.jsonl"
export PATH="$PATH"
bash "$HERE/corpus.sh"
cd /tmp/abf34_corpus || exit 1
rm -f /tmp/abf34_jobs.txt
for p in /tmp/abf34_corpus/*; do
  for h in confirm_launch confirm_cleanup confirm_walkthrough guard_plugin_files; do
    for c in c1 c2 c3; do echo "$p $c $h" >> /tmp/abf34_jobs.txt; done
    case "$p" in *cap-*) echo "$p c0 $h" >> /tmp/abf34_jobs.txt ;; esac
  done
done
wc -l < /tmp/abf34_jobs.txt
xargs -P 6 -L 1 bash "$HERE/worker.sh" < /tmp/abf34_jobs.txt > /tmp/abf34_results.txt
grep -c '^SAME' /tmp/abf34_results.txt
grep -c '^DIFF' /tmp/abf34_results.txt
grep '^DIFF' /tmp/abf34_results.txt | head -60
