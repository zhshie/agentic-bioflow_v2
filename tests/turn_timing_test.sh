#!/bin/bash
# Tests for scripts/turn_timing.py: pure read of a transcript file, so this
# never touches the network, the cluster or a real settings file.
#
# The fixture below is built with python3 rather than typed as a heredoc of
# JSON: a transcript's timestamps have to be internally consistent (each
# record after the one it is measured against) and readable as a story - "a
# tool call that took 5s, then an ssh-shaped one that took 8s, then a
# question that waited 30s for a reply" - which is easier to get right, and
# to see is right, written as a small Python list of records than as elever
# hand-typed offsets.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/turn_timing.py"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0
ok() { printf '%-70s ok\n' "$1"; }
no() { printf '%-70s FAIL: %s\n' "$1" "$2"; fails=$((fails+1)); }
has() { grep -qF -- "$2" <<<"$1"; }
# hasre <text> <regex> - whitespace-tolerant: this file's own column widths
# are an implementation detail the tests should not have to reproduce
# character for character.
hasre() { grep -qE -- "$2" <<<"$1"; }

FIXTURE="$TMP/fixture.jsonl"
python3 - "$FIXTURE" <<'PY'
import json, sys

def rec(t, typ, content):
    return {"type": typ, "timestamp": t, "message": {"role": typ, "content": content}}

recs = [
    rec("2026-09-18T00:00:00.000Z", "user", "please run the pipeline"),
    rec("2026-09-18T00:00:01.000Z", "assistant", [{"type": "thinking", "thinking": "let's look"}]),
    rec("2026-09-18T00:00:02.000Z", "assistant",
        [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls foo"}}]),
    # tool executes for 5s - not ssh-shaped
    rec("2026-09-18T00:00:07.000Z", "user",
        [{"type": "tool_result", "tool_use_id": "t1", "content": "foo.txt"}]),
    # generation 1s, then an ssh-shaped call that takes 8s
    rec("2026-09-18T00:00:08.000Z", "assistant",
        [{"type": "tool_use", "id": "t2", "name": "Bash",
          "input": {"command": "scripts/on_site.sh --check-reach"}}]),
    rec("2026-09-18T00:00:16.000Z", "user",
        [{"type": "tool_result", "tool_use_id": "t2", "content": "ok"}]),
    # generation 1s, then a question - waits 30s for the human to answer
    rec("2026-09-18T00:00:17.000Z", "assistant",
        [{"type": "text", "text": "Which project should this run belong to?"}]),
    rec("2026-09-18T00:00:47.000Z", "user", "project-alpha"),
    # generation 0.5s, then a quick tool call (0.2s, not ssh-shaped)
    rec("2026-09-18T00:00:47.500Z", "assistant",
        [{"type": "tool_use", "id": "t3", "name": "Read", "input": {"file_path": "x"}}]),
    rec("2026-09-18T00:00:47.700Z", "user",
        [{"type": "tool_result", "tool_use_id": "t3", "content": "contents"}]),
    # a final reply with no tool call and no reply after it - open, not counted
    rec("2026-09-18T00:00:48.000Z", "assistant", [{"type": "text", "text": "Done."}]),
]
with open(sys.argv[1], "w") as f:
    for r in recs:
        f.write(json.dumps(r) + "\n")
PY

out=$("$S" "$FIXTURE" 2>&1); rc=$?
[ "$rc" = 0 ] && ok "exits 0 on a well-formed fixture" \
              || no "exits 0 on a well-formed fixture" "rc=$rc <<$out>>"

# --- the three categories, with the numbers this fixture was built for -----
hasre "$out" 'model[[:space:]]+4\.80s[[:space:]]+\(5 turns\)' \
  && ok "model generation totals 4.80s across 5 turns" \
  || no "model generation totals 4.80s across 5 turns" "<<$out>>"

hasre "$out" 'tool[[:space:]]+13\.20s[[:space:]]+\(3 calls\)' \
  && ok "tool execution totals 13.20s across 3 calls" \
  || no "tool execution totals 13.20s across 3 calls" "<<$out>>"

hasre "$out" 'wait[[:space:]]+30\.00s[[:space:]]+\(1 wait\)' \
  && ok "waiting for the user totals 30.00s across 1 wait" \
  || no "waiting for the user totals 30.00s across 1 wait" "<<$out>>"

# --- the ssh sub-split inside 'tool' ----------------------------------------
hasre "$out" 'ssh[[:space:]]+8\.00s[[:space:]]+\(1 call\)' \
  && ok "the on_site.sh call is tagged and totalled as ssh" \
  || no "the on_site.sh call is tagged and totalled as ssh" "<<$out>>"

hasre "$out" 'other[[:space:]]+5\.20s[[:space:]]+\(2 calls\)' \
  && ok "the two non-ssh calls (5s + 0.2s) total 5.20s" \
  || no "the two non-ssh calls (5s + 0.2s) total 5.20s" "<<$out>>"

# It must NOT invent a per-call hook figure - docs/PRINCIPLES.md invariant 8.
has "$out" "hook time is not separately measurable" \
  && ok "says plainly that hook time is not broken out, rather than guessing" \
  || no "says plainly that hook time is not broken out, rather than guessing" "<<$out>>"

# --- the slowest-N table -----------------------------------------------------
first_line=$(sed -n '2p' <<<"$out")
has "$first_line" "30.00s" && has "$first_line" "wait" \
  && ok "the single slowest segment (the 30s wait) is listed first" \
  || no "the single slowest segment (the 30s wait) is listed first" "<<$first_line>>"

has "$out" "8.00s  tool(ssh)" \
  && ok "the ssh call is labelled tool(ssh) in the slowest-N table" \
  || no "the ssh call is labelled tool(ssh) in the slowest-N table" "<<$out>>"

# --- the open final segment is not counted -----------------------------------
# 9 real segments total: 5 model + 3 tool + 1 wait. A 10th (a wait after
# "Done.") would exist only if the transcript kept going.
n=$(has "$out" "slowest 9 segment" && echo yes || echo no)
[ "$n" = yes ] \
  && ok "an open trailing turn with no reply after it is not counted" \
  || no "an open trailing turn with no reply after it is not counted" "<<$out>>"

# --- --top limits the table, not the totals ----------------------------------
out3=$("$S" --top 3 "$FIXTURE" 2>&1)
n_rows=$(sed -n '/^slowest/,/^$/p' <<<"$out3" | grep -cE '^\s+[0-9]')
[ "$n_rows" = 3 ] \
  && ok "--top 3 lists exactly 3 segments" \
  || no "--top 3 lists exactly 3 segments" "got $n_rows rows <<$out3>>"
hasre "$out3" 'wait[[:space:]]+30\.00s[[:space:]]+\(1 wait\)' \
  && ok "--top 3 does not change the totals" \
  || no "--top 3 does not change the totals" "<<$out3>>"

# --- --json carries every segment, machine-readably --------------------------
outj=$("$S" --json "$FIXTURE" 2>&1)
count=$(python3 -c 'import json,sys; print(len(json.load(sys.stdin)["segments"]))' <<<"$outj" 2>/dev/null)
[ "$count" = 9 ] \
  && ok "--json carries all 9 segments" \
  || no "--json carries all 9 segments" "got '$count'"

ssh_dur=$(python3 -c '
import json, sys
segs = json.load(sys.stdin)["segments"]
print([s["dur"] for s in segs if s.get("tag") == "ssh"][0])
' <<<"$outj" 2>/dev/null)
[ "$ssh_dur" = "8.0" ] \
  && ok "--json tags the on_site.sh call ssh with its own duration" \
  || no "--json tags the on_site.sh call ssh with its own duration" "got '$ssh_dur'"

# --- a garbage/partial line does not crash the whole report ------------------
GARBLED="$TMP/garbled.jsonl"
{ cat "$FIXTURE"; printf 'not json at all\n'; printf '{"type": "assistant", "timestamp": "2026-09-18T00:00:49.000Z"'; } > "$GARBLED"
out=$("$S" "$GARBLED" 2>&1); rc=$?
[ "$rc" = 0 ] \
  && ok "a garbled trailing line (transcript still being written) does not crash it" \
  || no "a garbled trailing line (transcript still being written) does not crash it" "rc=$rc <<$out>>"

# --- a missing file is a clean error, not a traceback -------------------------
out=$("$S" "$TMP/does-not-exist.jsonl" 2>&1); rc=$?
[ "$rc" = 2 ] \
  && ok "a missing transcript file exits 2" \
  || no "a missing transcript file exits 2" "rc=$rc"
has "$out" "Traceback" \
  && no "a missing transcript file reports cleanly, not a Python traceback" "<<$out>>" \
  || ok "a missing transcript file reports cleanly, not a Python traceback"

echo
[ "$fails" = 0 ] && echo "OK: turn_timing.py" || { echo "$fails failed"; exit 1; }
