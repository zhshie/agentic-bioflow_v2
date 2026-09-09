#!/bin/bash
# Tests for scripts/positron_run.py, which runs a file in the console Positron
# already has open.
#
# Two things here are worth more than the rest.
#
# The first is the leak check. GET /sessions returns each kernel's entire
# environment, and on a real machine that holds real credentials - the first
# run of this script against a live Positron returned a GitHub PAT and several
# API keys. So the fixtures below carry a token-shaped string, and every case
# asserts it never reaches the output. That is the check that has to keep
# working when someone later adds a --verbose flag.
#
# The second is that these run with no Positron and no supervisor at all.
# Kallichore speaks HTTP over a named pipe or a Unix socket; standing one up in
# a test would test the harness. POSITRON_RUN_SUPERVISOR_DIR points the search
# at fixture files and POSITRON_RUN_FIXTURE supplies the responses, keyed by
# server pid so two supervisors can disagree - which is what having two
# Positron windows open looks like from here.
S="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/positron_run.py"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

# A token-shaped string that must never appear in output. Fake, but the same
# shape as the real thing that turned up in a live /sessions response.
SECRET="github_pat_11FAKEFAKEFAKEFAKE_notarealtokenatall"

# Pick an interpreter by running one, not by looking one up. On Windows,
# `python3` is on PATH as an App Execution Alias that resolves to a Microsoft
# Store stub: `command -v` finds it, and every invocation then exits 49 having
# printed nothing, which reads here as 21 identical unexplained failures.
PY=""
for candidate in python3 python py; do
    if "$candidate" -c 'pass' >/dev/null 2>&1; then PY="$candidate"; break; fi
done
if [ -z "$PY" ]; then echo "FAIL: no working python interpreter on PATH"; exit 1; fi

# --------------------------------------------------------------------------
# Fixture building
# --------------------------------------------------------------------------
supervisor() { # supervisor <pid> <transport-json-fragment>
  mkdir -p "$TMP/sup" "$TMP/fx/$1"
  cat > "$TMP/sup/kallichore-$1.json" <<JSON
{ "server_pid": $1, "bearer_token": "tok-$1-$SECRET", $2 }
JSON
}

session() { # session <pid> <session_id> <language> <status> <queue-len> <wd>
  local pid=$1 sid=$2 lang=$3 status=$4 qlen=$5 wd=$6
  local f="$TMP/fx/$pid/sessions.json"
  [ -f "$f" ] || echo '{"sessions":[]}' > "$f"
  "$PY" - "$f" "$sid" "$lang" "$status" "$qlen" "$wd" "$SECRET" <<'PY'
import json, sys
f, sid, lang, status, qlen, wd, secret = sys.argv[1:8]
d = json.load(open(f, encoding="utf-8"))
d["sessions"].append({
    "session_id": sid, "language": lang, "display_name": lang + " (fixture)",
    "status": status, "working_directory": wd,
    "execution_queue": {"length": int(qlen), "pending": []},
    # The field the whole leak check exists for.
    "initial_env": {"GITHUB_PAT": secret, "PATH": "/usr/bin"},
    "argv": ["kernel", "--token", secret],
})
json.dump(d, open(f, "w", encoding="utf-8"), indent=1)
PY
}

run() { # run <args...> -> sets $out and $rc
  out=$(POSITRON_RUN_SUPERVISOR_DIR="$TMP/sup" POSITRON_RUN_FIXTURE="$TMP/fx" \
        "$PY" "$S" "$@" 2>&1); rc=$?
}

t() { # t <label> <expect-rc> <expect-substring> -- <args...>
  local label="$1" want_rc="$2" want="$3"; shift 4
  printf '%-58s ' "$label"
  run "$@"
  if [ "$rc" != "$want_rc" ]; then
    echo "FAIL: rc $rc, wanted $want_rc  <<$out>>"; fails=$((fails+1)); return
  fi
  if [ -n "$want" ] && ! grep -qF -- "$want" <<<"$out"; then
    echo "FAIL: output lacks '$want'  <<$out>>"; fails=$((fails+1)); return
  fi
  # Every single case is also a leak case. Cheap, and the one assertion that
  # must not be possible to forget when adding a test below.
  if grep -qF -- "$SECRET" <<<"$out"; then
    echo "FAIL: LEAKED a credential from the fixture  <<$out>>"; fails=$((fails+1)); return
  fi
  echo "ok"
}

# --------------------------------------------------------------------------
# Transports: the three shapes Kallichore uses, one per platform. Only the
# label is asserted - it is what proves the right branch was taken without a
# real socket, and it is also the only thing the tool ever prints about a
# supervisor.
# --------------------------------------------------------------------------
mkdir -p "$TMP/work"
supervisor 111 '"transport": "named-pipe", "named_pipe": "\\\\.\\pipe\\kallichore-111"'
session 111 r-aaa R idle 0 "$TMP/work"

t "named-pipe: reports its endpoint"      0 'named-pipe \\.\pipe\kallichore-111' -- --check
t "named-pipe: dry run picks the session" 0 "would run in r-aaa" \
    -- --lang r --code '1+1' --workspace "$TMP/work" --dry-run

rm -rf "$TMP/sup" "$TMP/fx"
supervisor 222 '"transport": "socket", "socket_path": "/var/folders/kc.sock"'
session 222 r-bbb R idle 0 "$TMP/work"
t "unix socket: reports its endpoint"     0 "socket /var/folders/kc.sock" -- --check

rm -rf "$TMP/sup" "$TMP/fx"
supervisor 333 '"transport": "tcp", "ip": "127.0.0.1", "port": 8182'
session 333 r-ccc R idle 0 "$TMP/work"
t "tcp: reports its endpoint"             0 "tcp 127.0.0.1:8182" -- --check

# --------------------------------------------------------------------------
# Two windows open. The sessions differ only by working directory, which is
# the one thing that can tell them apart.
# --------------------------------------------------------------------------
rm -rf "$TMP/sup" "$TMP/fx"
mkdir -p "$TMP/projA/analysis" "$TMP/projB"
supervisor 444 '"transport": "tcp", "port": 1'
supervisor 555 '"transport": "tcp", "port": 2'
session 444 r-projA R idle 0 "$TMP/projA"
session 555 r-projB R idle 0 "$TMP/projB"

t "two windows: picks the one holding the file" 0 "would run in r-projA" \
    -- --lang r --code '1+1' --workspace "$TMP/projA/analysis" --dry-run
t "two windows: and the other one, likewise"    0 "would run in r-projB" \
    -- --lang r --code '1+1' --workspace "$TMP/projB" --dry-run
t "--check lists both, no env either way"       0 "r-projA" -- --check
t "--session-id overrides the search"           0 "would run in r-projB" \
    -- --lang r --code '1+1' --session-id r-projB --workspace "$TMP/projA" --dry-run

# A console exists, but not for this workspace. Running it anyway would
# execute against a project the caller did not name.
t "unrelated workspace: refuses, names what it saw" 2 "but not one holding" \
    -- --lang r --code '1+1' --workspace "$TMP/nowhere-else" --dry-run

# --------------------------------------------------------------------------
# Nothing to attach to. This must never start a session.
# --------------------------------------------------------------------------
rm -rf "$TMP/sup" "$TMP/fx"; mkdir -p "$TMP/sup"
t "no console: exits 2 and says to open one" 2 "no R console is open" \
    -- --lang r --code '1+1' --workspace "$TMP/work" --dry-run
t "no console: --check says so plainly"      0 "no Positron sessions found" -- --check

# A supervisor file left behind by a Positron that has quit. Unreadable
# responses must be skipped, not crash the search.
supervisor 666 '"transport": "tcp", "port": 3'   # no fixture -> every GET 404s
t "stale supervisor file: skipped, not fatal" 2 "no R console is open" \
    -- --lang r --code '1+1' --workspace "$TMP/work" --dry-run

# --------------------------------------------------------------------------
# A busy console. Queuing behind whatever is running would execute this at a
# time nobody chose.
# --------------------------------------------------------------------------
rm -rf "$TMP/sup" "$TMP/fx"
supervisor 777 '"transport": "tcp", "port": 4'
session 777 r-busy R busy 0 "$TMP/work"
t "busy console: refuses with exit 3" 3 "is not free" \
    -- --lang r --code '1+1' --workspace "$TMP/work" --dry-run

rm -rf "$TMP/sup" "$TMP/fx"
supervisor 888 '"transport": "tcp", "port": 5'
session 888 r-queued R idle 2 "$TMP/work"
t "queued console: also refuses"      3 "already queued" \
    -- --lang r --code '1+1' --workspace "$TMP/work" --dry-run

# --------------------------------------------------------------------------
# Language selection, and the code each language gets sent.
# --------------------------------------------------------------------------
rm -rf "$TMP/sup" "$TMP/fx"
supervisor 999 '"transport": "tcp", "port": 6'
session 999 r-both   R      idle 0 "$TMP/work"
session 999 py-both  Python idle 0 "$TMP/work"
printf 'x <- 1\n' > "$TMP/work/s.R"
printf 'x = 1\n'  > "$TMP/work/s.py"

t "--lang r sources the file"        0 'source("' -- --lang r      --file "$TMP/work/s.R"  --dry-run
t "--lang r targets the R session"   0 "would run in r-both"  -- --lang r      --file "$TMP/work/s.R"  --dry-run
t "--lang python uses %run"          0 '%run "'   -- --lang python --file "$TMP/work/s.py" --dry-run
t "--lang python targets Python"     0 "would run in py-both" -- --lang python --file "$TMP/work/s.py" --dry-run
t "missing file is caught here"      2 "no such file" -- --lang r --file "$TMP/work/absent.R" --dry-run
t "--file and --code are exclusive"  2 "exactly one"  -- --lang r --file "$TMP/work/s.R" --code '1' --dry-run
t "--lang required without --check"  2 "--lang is required" -- --file "$TMP/work/s.R" --dry-run

# --------------------------------------------------------------------------
# The leak check, stated once as its own case rather than only as a side
# condition of the others.
# --------------------------------------------------------------------------
printf '%-58s ' "no fixture credential anywhere in --check"
run --check
if grep -qF -- "$SECRET" <<<"$out"; then
  echo "FAIL: credential in output"; fails=$((fails+1))
elif grep -qiE 'initial_env|bearer|"argv"' <<<"$out"; then
  echo "FAIL: raw API fields in output  <<$out>>"; fails=$((fails+1))
else
  echo "ok"
fi

# --------------------------------------------------------------------------
# Passing the script its own arguments. A live console's
# commandArgs(trailingOnly = TRUE) is empty, so without this a script's
# --outdir was reachable from Rscript and not from here - and two scripts in
# one analysis/ directory defaulting to the same figures/ meant running one
# live destroyed the other's output with no flag available to prevent it.
# --------------------------------------------------------------------------
# Match the tail only: $TMP is an MSYS path here and the tool prints the
# native one, so the leading directory is not the same string on Windows.
t "python --args become sys.argv"    0 's.py" "--outdir" "figs"' \
    -- --lang python --file "$TMP/work/s.py" --dry-run --args --outdir figs
t "R --args shadow commandArgs"      0 "assign('commandArgs'" \
    -- --lang r --file "$TMP/work/s.R" --dry-run --args --outdir figs
t "R --args are quoted as R strings" 0 'c("--outdir", "figs")' \
    -- --lang r --file "$TMP/work/s.R" --dry-run --args --outdir figs
t "R restores commandArgs on error"  0 "on.exit(" \
    -- --lang r --file "$TMP/work/s.R" --dry-run --args --outdir figs
t "no --args leaves the call plain"  0 'source("' \
    -- --lang r --file "$TMP/work/s.R" --dry-run
t "--args without --file is refused" 2 "--args needs --file" \
    -- --lang r --code '1+1' --dry-run --args --outdir figs

printf '%-58s ' "R --args survive a quote in the value"
run --lang r --file "$TMP/work/s.R" --dry-run --args --title 'a "quoted" word'
if grep -qF -- '\"quoted\"' <<<"$out"; then echo "ok"
else echo "FAIL: quote not escaped for R  <<$out>>"; fails=$((fails+1)); fi

# --------------------------------------------------------------------------
# No console, and the refusal has to be usable. This is the one step the tool
# will not do for the person, so "no session found" is not an acceptable
# message - it has to say what to do, and offer to hold the step open.
# --------------------------------------------------------------------------
rm -rf "$TMP/sup" "$TMP/fx"; mkdir -p "$TMP/sup"
printf '%-58s ' "no console: the refusal is a set of instructions"
run --lang r --code '1+1' --workspace "$TMP/work" --dry-run
ok=1
for phrase in "Nothing can run until one exists" "session picker" "--wait" "--check"; do
  grep -qF -- "$phrase" <<<"$out" || { echo "FAIL: guidance lacks '$phrase'  <<$out>>"; ok=0; break; }
done
[ "$rc" = 2 ] || { echo "FAIL: rc $rc, wanted 2"; ok=0; }
[ "$ok" = 1 ] && echo "ok" || fails=$((fails+1))

printf '%-58s ' "--wait holds, then gives up without running"
start=$(date +%s)
run --lang r --code '1+1' --workspace "$TMP/work" --dry-run --wait 3
waited=$(( $(date +%s) - start ))
if [ "$rc" != 2 ]; then echo "FAIL: rc $rc, wanted 2"; fails=$((fails+1))
elif [ "$waited" -lt 2 ]; then echo "FAIL: returned after ${waited}s, did not wait"; fails=$((fails+1))
elif ! grep -qF -- "no R console appeared" <<<"$out"; then
  echo "FAIL: no timeout message  <<$out>>"; fails=$((fails+1))
elif ! grep -qF -- "still waiting" <<<"$out"; then
  echo "FAIL: waited silently  <<$out>>"; fails=$((fails+1))
else echo "ok"; fi

# --wait must not paper over a console that is there but busy: that is a
# different problem with a different answer, and exit 3 is what says so.
rm -rf "$TMP/sup" "$TMP/fx"
supervisor 1010 '"transport": "tcp", "port": 7'
session 1010 r-busy2 R busy 0 "$TMP/work"
t "--wait does not swallow a busy console" 3 "is not free" \
    -- --lang r --code '1+1' --workspace "$TMP/work" --dry-run --wait 3

rm -rf "$TMP/sup" "$TMP/fx"
supervisor 999 '"transport": "tcp", "port": 6'
session 999 r-both   R      idle 0 "$TMP/work"
session 999 py-both  Python idle 0 "$TMP/work"

# --------------------------------------------------------------------------
# Response parsing.
#
# Every case above goes through the fixture seam, which returns a parsed
# object and never touches a socket - so until this block existed, the code
# that reads bytes off the wire had no test at all, and a leak or a parse bug
# introduced there would have passed the whole suite. It is also where the one
# real bug an adversarial read turned up was hiding: the chunked branch tested
# for a capitalised `Transfer-Encoding`, and kcserver sends every header
# lowercase (measured against a live supervisor: `content-length: 18630`), so
# that branch could not fire.
printf '%-58s ' "response parsing: headers, framing, no body in errors"
parse_out=$("$PY" - "$S" "$SECRET" <<'PY' 2>&1
import importlib.util, sys
spec = importlib.util.spec_from_file_location("pr", sys.argv[1])
pr = importlib.util.module_from_spec(spec); spec.loader.exec_module(pr)
secret = sys.argv[2]
bad = []

def check(label, cond):
    if not cond: bad.append(label)

body = b'{"ok":1}'
chunked = b"8\r\n" + body + b"\r\n0\r\n\r\n"

# The header case that actually ships. This is the regression test.
check("lowercase chunked", pr._parse_response(
    b"HTTP/1.1 200 OK\r\ntransfer-encoding: chunked\r\n\r\n" + chunked, "/s") == {"ok": 1})
# And the RFC's spelling, so neither case is the only one that works.
check("capitalised chunked", pr._parse_response(
    b"HTTP/1.1 200 OK\r\nTransfer-Encoding: Chunked\r\n\r\n" + chunked, "/s") == {"ok": 1})
# Content-Length wins over "everything that arrived".
check("content-length truncates", pr._parse_response(
    b"HTTP/1.1 200 OK\r\ncontent-length: 8\r\n\r\n" + body + b"TRAILING JUNK", "/s") == {"ok": 1})
check("no length, read to EOF", pr._parse_response(
    b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\n\r\n" + body, "/s") == {"ok": 1})

# An error response body can carry initial_env. The raised message must
# describe the status and nothing else.
try:
    pr._parse_response(
        b"HTTP/1.1 500 Internal Server Error\r\ncontent-length: 60\r\n\r\n"
        + ('{"error":"env had ' + secret + '"}').encode(), "/sessions")
    bad.append("500 did not raise")
except RuntimeError as e:
    check("500 message names the status", "500" in str(e))
    check("500 message withholds the body", secret not in str(e))

try:
    pr._parse_response(b"", "/s"); bad.append("empty did not raise")
except RuntimeError as e:
    check("empty response explained", "without replying" in str(e))

print("BAD:" + ",".join(bad) if bad else "ALLOK")
PY
)
if [ "$parse_out" != "ALLOK" ]; then
  echo "FAIL: $parse_out"; fails=$((fails+1))
elif grep -qF -- "$SECRET" <<<"$parse_out"; then
  echo "FAIL: credential in output"; fails=$((fails+1))
else
  echo "ok"
fi

# --------------------------------------------------------------------------
# Workspace containment. Two paths naming one directory in different letter
# case are the same directory on Windows and macOS; treating them as different
# reports "no console is open" for a console that is open.
printf '%-58s ' "workspace match survives a differently-cased path"
case_out=$("$PY" - "$S" "$TMP" <<'PY' 2>&1
import importlib.util, os, sys
spec = importlib.util.spec_from_file_location("pr", sys.argv[1])
pr = importlib.util.module_from_spec(spec); spec.loader.exec_module(pr)
root = sys.argv[2]
parent = os.path.join(root, "CaseTest"); child = os.path.join(parent, "inner")
os.makedirs(child, exist_ok=True)
bad = []
if not pr._under(child, parent): bad.append("exact path did not match")
if pr._under(parent, child): bad.append("parent matched inside its own child")
if pr._under(root, os.path.join(root, "no-such-dir")): bad.append("matched a missing parent")
# Only meaningful where the filesystem is case-insensitive; where it is not,
# the two names are genuinely different directories and False is correct.
folded = os.path.join(root, "casetest")
if os.path.isdir(folded) and not pr._under(child, folded):
    bad.append("case-insensitive fs, but a lowercased parent did not match")
print("BAD:" + ",".join(bad) if bad else "ALLOK")
PY
)
if [ "$case_out" != "ALLOK" ]; then echo "FAIL: $case_out"; fails=$((fails+1)); else echo "ok"; fi

# --------------------------------------------------------------------------
# A failed run has to say why. ark sends an iopub error whose `traceback` is
# an empty list, so joining it printed one blank line to stderr and left the
# reason visible only inside the IDE - the exact "did it work?" blindness this
# tool was written to remove.
printf '%-58s ' "a failure explains itself, whatever field carries it"
err_out=$("$PY" - "$S" <<'PY' 2>&1
import importlib.util, sys
spec = importlib.util.spec_from_file_location("pr", sys.argv[1])
pr = importlib.util.module_from_spec(spec); spec.loader.exec_module(pr)
bad = []
if pr.error_text({"traceback": ["Error:", "! boom"]}) != "Error:\n! boom":
    bad.append("traceback not used when present")
# What ark actually sends for stop("boom").
if pr.error_text({"traceback": [], "ename": "Error", "evalue": "boom"}) != "Error: boom":
    bad.append("empty traceback did not fall back to ename/evalue")
if not pr.error_text({}).strip():
    bad.append("an empty payload printed nothing at all")
print("BAD:" + ",".join(bad) if bad else "ALLOK")
PY
)
if [ "$err_out" != "ALLOK" ]; then echo "FAIL: $err_out"; fails=$((fails+1)); else echo "ok"; fi

# --------------------------------------------------------------------------
# The whitelist, tested where it acts rather than where it shows.
#
# Every case above also greps the rendered output for $SECRET, which reads like
# a leak check and is not one: report() prints six named fields, so the
# credential cannot reach stdout whether the whitelist is there or not. Deleting
# SESSION_FIELDS outright and returning dict(raw) passed all of them. The point
# of narrowing at parse time is that a print site added later cannot leak what
# was never carried - so the assertion belongs on the object, not the render.
# --------------------------------------------------------------------------
printf '%-58s ' "the parsed session carries no credential-bearing field"
wl_out=$(POSITRON_RUN_SUPERVISOR_DIR="$TMP/sup" POSITRON_RUN_FIXTURE="$TMP/fx" \
  "$PY" - "$(dirname "$S")" "$SECRET" <<'PY'
import sys, os
sys.path.insert(0, sys.argv[1])
import positron_run as pr
secret, bad = sys.argv[2], []
pairs = pr.find_sessions()
if not pairs:
    bad.append("no sessions parsed - the fixture stopped reaching this code")
for _sup, session in pairs:
    for dropped in ("initial_env", "argv"):
        if dropped in session:
            bad.append(f"{dropped} survived parsing")
    if secret in repr(session):
        bad.append("the credential is inside the parsed session")
print("BAD:" + ",".join(sorted(set(bad))) if bad else "ALLOK")
PY
)
if [ "$wl_out" != "ALLOK" ]; then echo "FAIL: $wl_out"; fails=$((fails+1)); else echo "ok"; fi

# --------------------------------------------------------------------------
# The invocation commands/downstream.md actually tells a person to type.
# Every case above runs "$PY" "$S", which is not that line and cannot fail the
# way that line fails: a file without its executable bit, or a shebang naming
# an interpreter that is a Microsoft Store stub on the machine this tool is for
# (PITFALLS 20c, documented in the same change that shipped the bare-path
# instruction).
# --------------------------------------------------------------------------
printf '%-58s ' "the documented bare-path invocation runs"
bp_out=$(POSITRON_RUN_SUPERVISOR_DIR="$TMP/sup" POSITRON_RUN_FIXTURE="$TMP/fx" \
         "$S" --check 2>&1); bp_rc=$?
if [ "$bp_rc" = 0 ]; then echo ok
else echo "FAIL: rc=$bp_rc <<$bp_out>>"; fails=$((fails+1)); fi

# The case above passes off the filesystem, and git is what ships this file: a
# `git stash` round-trip silently reverted the index mode to 100644 while the
# working copy stayed +x, so the bare-path case still passed and the broken
# file would have been the one committed. Assert on what gets distributed.
printf '%-58s ' "and git ships it executable, not just this checkout"
if git -C "$(dirname "$S")" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  mode=$(git -C "$(dirname "$S")" ls-files -s -- "$(basename "$S")" | awk '{print $1}')
  if [ "$mode" = 100755 ]; then echo ok
  else echo "FAIL: index mode $mode, wanted 100755"; fails=$((fails+1)); fi
else
  echo "ok (not a git checkout)"
fi

printf '%-58s ' "and it picks an interpreter by running one"
# A bare `#!/usr/bin/env python3` is exactly what 20c says cannot be trusted
# here, and 16d says the same for this cluster's fenced /usr/bin/python3. One
# probe loop answers both; asserting on its shape is the honest limit, because
# neither machine is this one.
if grep -qE 'for [a-z]+ in python3 python py' "$S"; then echo ok
else echo "FAIL: no interpreter probe in $S"; fails=$((fails+1)); fi

echo
if [ "$fails" -gt 0 ]; then echo "FAIL: $fails case(s)"; exit 1; fi
echo "OK: positron_run.py"
