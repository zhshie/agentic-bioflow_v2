#!/bin/bash
# PITFALLS 36: a long-lived daemon must not inherit a caller's temporary
# working directory.
#
# scripts/on_site.sh --script copies this repo's scripts into a `mktemp -d` on
# the site and runs them there, so anything a script backgrounds inherits that
# directory - which is deleted the moment the round trip ends. The process
# survives; its cwd does not.
#
# For scripts/agent_ctl.sh that is not cosmetic. The agent answers Platform by
# running `sh -c <command>` with redirectErrorStream(true) and no working
# directory set on the ProcessBuilder (measured from tw-agent v0.5.6's own
# bytecode). With a deleted cwd every such shell writes a `shell-init:
# ... getcwd` line to stderr, which is folded into stdout, so every response
# Platform reads carries shell noise where its first line of content should
# be. The agent still reports ONLINE and still heartbeats; the run's report
# manifest simply stops parsing, and every run's outputs read as absent.
#
# Two halves, because the structural check alone would be a rule nobody could
# justify a year from now:
#   1. the mechanism, reproduced - so the reason the `cd` exists is pinned
#   2. the scripts actually anchor themselves before backgrounding anything
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fails=0
ok()   { printf '%-64s ok\n' "$1"; }
bad()  { printf '%-64s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

# --- 1. the mechanism -------------------------------------------------------
# A shell started from a deleted directory still runs, and still produces the
# right answer - it just prepends a diagnostic. That is exactly what makes it
# so hard to see: nothing fails.
mkdir -p "$TMP/doomed"
OUT=$( cd "$TMP/doomed" && rmdir "$TMP/doomed" && sh -c 'echo CONTENT' 2>&1 )
if grep -q 'CONTENT' <<<"$OUT"; then
    ok "a shell from a deleted cwd still produces its output"
else
    bad "a shell from a deleted cwd still produces its output" "<<$OUT>>"
fi
if grep -qi 'getcwd\|current directory' <<<"$OUT"; then
    ok "...but prepends a getcwd diagnostic that merges into stdout"
    FIRST=$(head -1 <<<"$OUT")
    if [ "$FIRST" = "CONTENT" ]; then
        bad "...and the diagnostic lands on line 1, not the content" "content was still first"
    else
        ok "...and the diagnostic lands on line 1, not the content"
    fi
else
    # Not every libc/shell spells this the same way. If a platform does not
    # produce it, the structural half below still holds - say so rather than
    # failing a check this platform cannot observe.
    ok "...(this shell prints no getcwd diagnostic; structural check still applies)"
fi

# --- 2. the scripts anchor themselves --------------------------------------
# Every `nohup` that backgrounds a daemon must have a `cd` ahead of it in the
# same script. Checked by reading the source rather than by starting a real
# agent: starting one needs a token, a connection id Platform has issued, and
# a login node that other people share.
for s in agent_ctl.sh egress_ctl.sh; do
    f="$ROOT/scripts/$s"
    if [ ! -r "$f" ]; then bad "$s is readable" "missing"; continue; fi
    # The comment filter has to run against the line's own text, not against
    # grep -n's "N:line" output - both scripts mention nohup in a comment
    # before they reach the real one.
    NLINE=$(grep -n 'nohup' "$f" | grep -vE '^[0-9]+:[[:space:]]*#' | head -1 | cut -d: -f1)
    if [ -z "$NLINE" ]; then
        ok "$s has no backgrounded daemon to anchor"
        continue
    fi
    # The nearest preceding `cd` must be within a handful of lines - far
    # enough back to allow a comment block, close enough that it is plainly
    # guarding this launch and not something unrelated earlier in the file.
    CDLINE=$(awk -v n="$NLINE" 'NR<n && /^[[:space:]]*cd /{last=NR} END{print last+0}' "$f")
    if [ "$CDLINE" = 0 ]; then
        bad "$s cds before backgrounding its daemon" "no cd anywhere before line $NLINE"
    elif [ $((NLINE - CDLINE)) -gt 8 ]; then
        bad "$s cds before backgrounding its daemon" \
            "nearest cd is line $CDLINE, $((NLINE - CDLINE)) lines before the nohup at $NLINE"
    else
        ok "$s cds before backgrounding its daemon"
    fi
done

# The comment has to name the pitfall, so the next person to read a bare `cd`
# in front of a nohup can find out why it is load-bearing.
for s in agent_ctl.sh egress_ctl.sh; do
    if grep -q 'PITFALLS 36' "$ROOT/scripts/$s"; then
        ok "$s says why it cds (names PITFALLS 36)"
    else
        bad "$s says why it cds (names PITFALLS 36)" "no reference to the pitfall"
    fi
done

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
