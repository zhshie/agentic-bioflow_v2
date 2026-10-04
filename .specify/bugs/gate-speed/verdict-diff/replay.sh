#!/bin/bash
# Verdict + timing diff of two hook trees (#34). Run in WSL/Linux:
#   bash capture.sh <baseline tree> <gate tests...>   records every payload the tests feed the hooks
#   bash replay.sh <baseline tree> <new tree>          builds the corpus, runs old and new, prints counts
# Both trees are copied to /tmp first. Build the baseline fresh, never from a
# leftover worktree:  git archive <baseline commit> | tar -x -C <dir>
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASRC="${1:?baseline tree}"; BSRC="${2:?new tree}"
rm -rf /tmp/abf34_A /tmp/abf34_B /tmp/abf34_res /tmp/abf34_ctx
mkdir -p /tmp/abf34_A /tmp/abf34_B
cp -r "$ASRC/." /tmp/abf34_A/ 2>/dev/null; rm -rf /tmp/abf34_A/.git
cp -r "$BSRC/." /tmp/abf34_B/ 2>/dev/null; rm -rf /tmp/abf34_B/.git
C=/tmp/abf34_ctx
mkdir -p "$C/work/analysis" "$C/home" "$C/state/in-use" "$C/bin_mingw" "$C/bin_nojq" "$C/bin_badjq"
: > "$C/state/in-use/s1"
for i in $(seq 1 200); do printf '{"type":"user","message":{"content":"hello %s"}}\n' "$i"; done > "$C/tr_plain.jsonl"
{ cat "$C/tr_plain.jsonl"
  printf '%s\n' '{"type":"user","message":{"content":"<command-name>/agentic-bioflow:launch</command-name>"}}'
  printf '%s\n' '{"type":"assistant","message":{"content":[{"type":"text","text":"ok"}]}}'
} > "$C/tr_slash.jsonl"
# a uname that says MINGW (D3 and the shared splitter answer then run), a PATH with no jq, a jq that fails
printf '#!/bin/bash\ncase "$1" in -s|"") echo MINGW64_NT-10.0;; *) exec /usr/bin/uname "$@";; esac\n' > "$C/bin_mingw/uname"
printf '#!/bin/bash\nexit 5\n' > "$C/bin_badjq/jq"
chmod +x "$C/bin_mingw/uname" "$C/bin_badjq/jq"
for f in /usr/bin/* /bin/*; do [ -x "$f" ] && [ "${f##*/}" != jq ] && ln -sf "$f" "$C/bin_nojq/${f##*/}" 2>/dev/null; done
bash "$HERE/corpus.sh"
python3 "$HERE/corpus2.py" /tmp/abf34_corpus
cd /tmp/abf34_corpus || exit 1
rm -f /tmp/abf34_jobs.txt
HOOKS="confirm_launch confirm_cleanup confirm_walkthrough guard_plugin_files"
for p in /tmp/abf34_corpus/*; do
  b=${p##*/}
  case "$b" in
    big*) ctxs="c1 mingw" ;;
    cap-*) ctxs="c0 c1 c2 c3 mingw" ;;
    *) ctxs="c1 c2 c3 mingw nojq badjq" ;;
  esac
  for h in $HOOKS; do for c in $ctxs; do echo "$p $c $h" >> /tmp/abf34_jobs.txt; done; done
done
echo "jobs: $(wc -l < /tmp/abf34_jobs.txt)"
xargs -P 6 -L 1 bash "$HERE/worker.sh" < /tmp/abf34_jobs.txt > /tmp/abf34_results.txt
echo "SAME $(grep -c '^SAME' /tmp/abf34_results.txt)  SLOW $(grep -c '^SLOW' /tmp/abf34_results.txt)  DIFF $(grep -c '^DIFF' /tmp/abf34_results.txt)"
grep -E '^(DIFF|SLOW)' /tmp/abf34_results.txt | head -60
