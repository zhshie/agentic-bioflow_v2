#!/bin/bash
# Where a `launch` walk's wall-clock time actually goes (GitHub issue #13).
#
# Not a Claude Code built-in: there is no first-party report that turns a
# transcript's own timestamps into "model generation vs tool execution vs
# waiting for the user" - the `system`/`turn_duration` records the CLI
# already writes give one number for a whole turn (thinking through the next
# prompt), not the three-way split a latency investigation needs.
#
#   turn_timing.py <transcript.jsonl> [--top N]
#
# Reads a Claude Code transcript (the same `.jsonl` `transcript_path` in a
# hook's stdin JSON points at, and what hooks/confirm_walkthrough.sh already
# reads for other reasons) and, using only the `timestamp` field every
# `assistant`/`user` record already carries, buckets the time between them
# into three kinds of segment:
#
#   model      from the record right before an assistant reply (a tool
#              result, or a real human message) to the LAST of the one or
#              more consecutive `assistant` records that reply - a reply is
#              commonly several records (thinking, then tool_use, sometimes
#              text), each its own line with its own timestamp, so the whole
#              run is one segment, not one per record.
#   tool       from that last assistant record (the one carrying a
#              `tool_use` block) to the `user` record carrying the matching
#              `tool_result` - one segment per tool call, tagged `ssh` when
#              the command looks like it crossed the site adapter
#              (`scripts/on_site.sh`, `scripts/utils/wsl_ssh.sh`, or a bare
#              `ssh` invocation) and `tool` otherwise.
#   wait       from an assistant reply that ends the turn with no tool call
#              (asking the user something) to the next record that is
#              actually a human typing, not a tool result or an injected
#              system/hook record.
#
# What this cannot measure, and does not pretend to: a PreToolUse hook's own
# execution time is invisible here. Hooks run and exit inside the gap between
# a `tool_use` record and its `tool_result` record; the transcript carries no
# separate timestamp for where the hook ended and the tool itself started, so
# it is folded into `tool` - this file does not report a `hook` category,
# because docs/PRINCIPLES.md invariant 8 rules out inventing a number that was
# not measured. The measured hook figure this project already has (~0.17s/call
# on this cluster, already established as not the bottleneck - see this
# script's own commit) came from timing the hook script directly, a different
# method from anything a transcript alone can do.
#
# Entered as a shell script for the same reason scripts/positron_run.py is:
# on Windows, where this reads transcripts written by a Claude Code session
# running there, `python3` on PATH is commonly a Microsoft Store stub that
# `command -v` finds and running exits 49 having printed nothing (PITFALLS
# 20c). Pick an interpreter by running it, never by finding it.
''''true
for candidate in python3 python py; do
    if "$candidate" -c 'import sys' >/dev/null 2>&1; then
        exec "$candidate" "$0" "$@"
    fi
done
echo "turn_timing: no working Python interpreter found (tried python3, python, py)." >&2
echo "  On Windows, 'python3' may be the Microsoft Store alias - install Python or" >&2
echo "  use the interpreter Claude Code itself runs on." >&2
exit 2
'''

"""Split a Claude Code transcript into model/tool/wait segments and report
the slowest ones plus each category's total. Pure read of the transcript
file - no network, no cluster, nothing this touches can fail a dry test."""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

# Bash commands shaped like a site-adapter round trip (docs/SITE_ADAPTER.md,
# contract "reach"). Matched the same loose way
# tests/command_layer_is_site_neutral.sh already matches `ssh` as a forbidden
# term in the command layer - a substring check, not a parser, because a
# shell command is not something this needs to fully understand to tag it.
SSH_SHAPED = re.compile(
    r'on_site\.sh|wsl_ssh\.sh|(^|[^A-Za-z0-9_])ssh(\s|$)')

# Content blocks injected by the harness rather than typed by a person -
# hooks/confirm_walkthrough.sh already has to make exactly this distinction
# (its EV/awk pass) to tell a real reply from machinery wearing a user
# record; the marker list is copied from there rather than re-derived.
INJECTED = re.compile(
    r'<task-notification|<system-reminder|<command-name|<local-command'
    r'|This session is being continued')


def parse_ts(s):
    """`timestamp` is always `...Z` (UTC) in a Claude Code transcript -
    verified against a real session's transcript while writing this. Turned
    into a plain float (seconds) rather than kept as a datetime because every
    use below is a subtraction."""
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
        tzinfo=timezone.utc).timestamp()


def load_records(path):
    """Every `assistant`/`user` record that carries both a timestamp and a
    message - the only two types this needs, and the only two a real
    transcript ever times against each other. A line that fails to parse as
    JSON is skipped, not fatal: a transcript still being written can end
    mid-line, and a report that refuses over the last, incomplete line would
    be refusing over exactly the turn someone is most likely to be asking
    about."""
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") not in ("assistant", "user"):
                continue
            ts = d.get("timestamp")
            msg = d.get("message")
            if not ts or not isinstance(msg, dict):
                continue
            try:
                d["_ts"] = parse_ts(ts)
            except ValueError:
                continue
            out.append(d)
    return out


def content_blocks(rec):
    c = rec.get("message", {}).get("content")
    if isinstance(c, list):
        return [b for b in c if isinstance(b, dict)]
    return []


def is_human(rec):
    """A `user` record is someone typing, not a tool result or an injected
    marker riding in the same envelope - the same test
    hooks/confirm_walkthrough.sh's own transcript read already applies
    (PITFALLS 18/18b: text the user actually saw vs machinery shaped like a
    reply)."""
    msg = rec.get("message", {})
    c = msg.get("content")
    if isinstance(c, str):
        return not INJECTED.search(c)
    blocks = content_blocks(rec)
    if not blocks:
        return False
    if any(b.get("type") == "tool_result" for b in blocks):
        return False
    texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    if not texts:
        return False
    return not any(INJECTED.search(t) for t in texts)


def tool_uses(rec):
    return [b for b in content_blocks(rec) if b.get("type") == "tool_use"]


def tool_results(rec):
    return [b for b in content_blocks(rec) if b.get("type") == "tool_result"]


def is_ssh_shaped(block):
    if block.get("name") != "Bash":
        return False
    cmd = (block.get("input") or {}).get("command", "")
    return bool(SSH_SHAPED.search(cmd))


def label_tools(rec):
    """The tool name(s) an assistant record calls, for a model segment that
    ends in a tool call - "Bash", or "Bash, Read" for more than one."""
    names = [b.get("name") for b in tool_uses(rec) if b.get("name")]
    return ", ".join(names) if names else "(tool)"


def _clip(s, n):
    s = s.strip().replace("\n", " ")
    return s[:n] + ("…" if len(s) > n else "")


def label_text(rec):
    """A short description for a segment with no tool call - the assistant's
    own text if it wrote any (the thing that actually ends a turn and waits
    on the user), else a clip of its thinking, so the slowest-N table never
    prints a blank line for a real segment."""
    blocks = content_blocks(rec)
    texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    if texts:
        return _clip(" ".join(texts), 60)
    thinking = [b.get("thinking", "") for b in blocks if b.get("type") == "thinking"]
    if thinking:
        return "(thinking) " + _clip(" ".join(thinking), 50)
    return "(no text)"


def segments(records):
    """Walk the transcript once, in file order (already chronological - a
    Claude Code transcript is append-only), and yield one dict per timed
    segment: {kind, tag, start, end, dur, label}.

    kind is 'model' | 'tool' | 'wait'. tag further splits 'tool' into 'ssh'
    vs 'tool'; it is None for the other two kinds.
    """
    i = 0
    n = len(records)
    # boundary_ts: the timestamp a segment about to be found should start
    # from - the end of whatever closed the previous one. Seeded from the
    # first record so the very first assistant run is timed from something
    # real rather than from zero.
    boundary_ts = records[0]["_ts"] if records else None

    while i < n:
        rec = records[i]
        if rec["type"] != "assistant":
            i += 1
            continue

        # One reply: every consecutive 'assistant' record from here.
        run_start = i
        while i < n and records[i]["type"] == "assistant":
            i += 1
        run_end = i - 1
        last = records[run_end]

        if boundary_ts is not None:
            dur = last["_ts"] - boundary_ts
            if dur >= 0:
                yield {"kind": "model", "tag": None,
                       "start": boundary_ts, "end": last["_ts"], "dur": dur,
                       "label": label_tools(last) if tool_uses(last)
                                else label_text(last)}

        uses = tool_uses(last)
        if uses:
            # One or more tool calls from this reply. They may all land in
            # one following `user` record (parallel/batched) or be spread
            # across several consecutive ones (sequential) - either way,
            # collect every tool_result until every tool_use id from `last`
            # is accounted for, or a non-matching record breaks the run.
            pending = {b.get("id"): b for b in uses if b.get("id")}
            j = i
            last_result_ts = None
            while j < n and pending:
                rj = records[j]
                if rj["type"] != "user":
                    break
                found_here = False
                for tr in tool_results(rj):
                    tid = tr.get("tool_use_id")
                    if tid in pending:
                        use_block = pending.pop(tid)
                        yield {"kind": "tool",
                               "tag": "ssh" if is_ssh_shaped(use_block) else "tool",
                               "start": last["_ts"], "end": rj["_ts"],
                               "dur": rj["_ts"] - last["_ts"],
                               "label": use_block.get("name", "?")}
                        found_here = True
                        last_result_ts = rj["_ts"]
                if not found_here:
                    break
                j += 1
            if last_result_ts is not None:
                boundary_ts = last_result_ts
                i = j
                continue
            # A tool_use with no matching tool_result anywhere later - the
            # transcript ends mid-call. Nothing to time; leave boundary_ts
            # where it is and stop, there is no more to segment.
            boundary_ts = None
            break

        # No tool call: this reply ends the turn and waits for the user.
        k = i
        while k < n and not (records[k]["type"] == "user" and is_human(records[k])):
            k += 1
        if k < n:
            yield {"kind": "wait", "tag": None,
                   "start": last["_ts"], "end": records[k]["_ts"],
                   "dur": records[k]["_ts"] - last["_ts"],
                   "label": label_text(last)}
            boundary_ts = records[k]["_ts"]
            i = k + 1
        else:
            # Transcript ends waiting on the user - open, nothing to sum.
            boundary_ts = None
            break


def render(segs, top_n):
    segs = list(segs)
    if not segs:
        print("no timed segments found in this transcript")
        return

    by_kind = {"model": [], "tool": [], "wait": []}
    for s in segs:
        by_kind[s["kind"]].append(s)

    ranked = sorted(segs, key=lambda s: s["dur"], reverse=True)[:top_n]
    print("slowest %d segment(s):" % len(ranked))
    for s in ranked:
        kind = s["kind"] if not s["tag"] else "%s(%s)" % (s["kind"], s["tag"])
        print("  %7.2fs  %-11s %s" % (s["dur"], kind, s["label"]))

    print()
    print("totals:")
    m = by_kind["model"]
    print("  %-11s %8.2fs  (%d turn%s)" %
          ("model", sum(s["dur"] for s in m), len(m), "" if len(m) == 1 else "s"))

    t = by_kind["tool"]
    ssh = [s for s in t if s["tag"] == "ssh"]
    plain = [s for s in t if s["tag"] != "ssh"]
    print("  %-11s %8.2fs  (%d call%s)" %
          ("tool", sum(s["dur"] for s in t), len(t), "" if len(t) == 1 else "s"))
    print("    %-9s %8.2fs  (%d call%s)" %
          ("ssh", sum(s["dur"] for s in ssh), len(ssh), "" if len(ssh) == 1 else "s"))
    print("    %-9s %8.2fs  (%d call%s)" %
          ("other", sum(s["dur"] for s in plain), len(plain), "" if len(plain) == 1 else "s"))
    print("    hook time is not separately measurable from a transcript alone -")
    print("    it is inside 'tool' above, not broken out (see this script's own header)")

    w = by_kind["wait"]
    print("  %-11s %8.2fs  (%d wait%s)" %
          ("wait", sum(s["dur"] for s in w), len(w), "" if len(w) == 1 else "s"))


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="turn_timing.py",
        description="Where a session's wall-clock time went: model "
                     "generation, tool execution (ssh round trips broken "
                     "out), or waiting for the user.")
    p.add_argument("transcript", help="path to a Claude Code .jsonl transcript")
    p.add_argument("--top", type=int, default=10,
                    help="how many of the slowest segments to list (default 10)")
    p.add_argument("--json", action="store_true", dest="as_json",
                    help="emit every segment machine-readably instead of the report")
    args = p.parse_args(argv)

    try:
        records = load_records(args.transcript)
    except OSError as exc:
        print("turn_timing: %s" % exc, file=sys.stderr)
        return 2

    segs = list(segments(records))
    if args.as_json:
        json.dump({"segments": segs}, sys.stdout, indent=1)
        print()
    else:
        render(segs, args.top)
    return 0


if __name__ == "__main__":
    sys.exit(main())
