#!/bin/bash
# scripts/report.sh: privacy is a field whitelist, not redaction, and this
# is what proves the whitelist actually holds. Every scenario runs against a
# throwaway AGENTIC_BIOFLOW_REPORTS_DIR, so no run here touches a real
# settings file or a real $HOME, and every gh interaction goes through a
# stub on PATH - this file never files a real GitHub issue (2.8 plan, 五).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
R="$ROOT/scripts/report.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
fails=0

t() { printf '%-64s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: expected '$2' got '$3'"; fails=$((fails+1)); }; }
tgrep() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && echo ok || { echo "FAIL: lacks '$2' in <<$3>>"; fails=$((fails+1)); }; }
tnotgrep() { printf '%-64s ' "$1"; grep -qF -- "$2" <<<"$3" && { echo "FAIL: contains '$2'"; fails=$((fails+1)); } || echo ok; }

queue_count() { find "$1" -maxdepth 1 -type f -name '*.report' 2>/dev/null | wc -l | tr -d ' '; }

# A queue dir per scenario, isolated by env var (report.sh's own escape
# hatch for tests) so no scenario can see another's reports.
DIR1="$TMP/q1"; mkdir -p "$DIR1"

run() { AGENTIC_BIOFLOW_REPORTS_DIR="$DIR1" env -i PATH="$PATH" HOME="$TMP" \
        AGENTIC_BIOFLOW_REPORTS_DIR="$DIR1" bash "$R" "$@" 2>&1; }

# --- rejecting a path, a hostname, an email --------------------------------
# Fed into --step and into --script, both of which are meant to hold a short
# slug and nothing else.
for field in step script; do
  for bad in "/home/user/rawdata/sample.fastq" "t3.nchc.org.tw" "user@example.com"; do
    before=$(queue_count "$DIR1")
    if [ "$field" = step ]; then
      out=$(run add --category env --command none --step "$bad" 2>&1); rc=$?
    else
      out=$(run add --category env --command none --step ok-step --script "$bad" 2>&1); rc=$?
    fi
    after=$(queue_count "$DIR1")
    printf '%-64s ' "--$field '$bad' rejected (exit 2)"
    [ "$rc" = 2 ] && echo ok || { echo "FAIL: exit $rc <<$out>>"; fails=$((fails+1)); }
    printf '%-64s ' "--$field '$bad' queued nothing"
    [ "$before" = "$after" ] && echo ok || { echo "FAIL: queue went $before -> $after"; fails=$((fails+1)); }
  done
done

# Same rule for --category and --command via the enum check - a path/hostname
# there is rejected too, just by the enum rather than the slug rule.
out=$(run add --category "/etc/passwd" --command none --step ok 2>&1); rc=$?
t "--category outside the enum is rejected (exit 2)" 2 "$rc"
out=$(run add --category env --command "t3.nchc.org.tw" --step ok 2>&1); rc=$?
t "--command outside the enum is rejected (exit 2)" 2 "$rc"

t "queue is still empty after every rejection" 0 "$(queue_count "$DIR1")"

# --- a valid add: file exists, mode 600 ------------------------------------
out=$(run add --category pipeline --command runs --step probe1 --script probe.sh --exit 1 --outcome unresolved)
rc=$?
t "valid add exits 0" 0 "$rc"
t "exactly one report queued" 1 "$(queue_count "$DIR1")"
FIRST_FILE=$(find "$DIR1" -maxdepth 1 -type f -name '*.report' | head -1)
printf '%-64s ' "queued file is mode 600"
mode=$(stat -c %a "$FIRST_FILE" 2>/dev/null || stat -f %Lp "$FIRST_FILE" 2>/dev/null)
[ "$mode" = 600 ] && echo ok || { echo "FAIL: mode is '$mode'"; fails=$((fails+1)); }
tgrep "add prints the next-step procedure" "scripts/report.sh send" "$out"
tgrep "the report itself carries the signature" "signature" "$(cat "$FIRST_FILE")"

# --- list -------------------------------------------------------------------
out=$(run list)
tgrep "list shows the queued category" "category: pipeline" "$out"
tgrep "list shows the queued step" "step: probe1" "$out"

EMPTYDIR="$TMP/empty"; mkdir -p "$EMPTYDIR"
out=$(AGENTIC_BIOFLOW_REPORTS_DIR="$EMPTYDIR" env -i PATH="$PATH" HOME="$TMP" \
      AGENTIC_BIOFLOW_REPORTS_DIR="$EMPTYDIR" bash "$R" list)
tgrep "list on an empty queue says so" "No reports queued" "$out"

# --- send without --yes sends nothing --------------------------------------
STUBBIN="$TMP/stub_never"; mkdir -p "$STUBBIN"
cat > "$STUBBIN/gh" <<'EOF'
#!/bin/bash
echo "$@" >> "$GH_LOG"
exit 0
EOF
chmod +x "$STUBBIN/gh"
GH_LOG="$TMP/never.log"; : > "$GH_LOG"
before=$(queue_count "$DIR1")
out=$(GH_LOG="$GH_LOG" AGENTIC_BIOFLOW_REPORTS_DIR="$DIR1" env -i PATH="$STUBBIN:/usr/bin:/bin" HOME="$TMP" \
      GH_LOG="$GH_LOG" AGENTIC_BIOFLOW_REPORTS_DIR="$DIR1" bash "$R" send)
after=$(queue_count "$DIR1")
t "send without --yes leaves the queue untouched" "$before" "$after"
printf '%-64s ' "send without --yes never calls gh"
[ ! -s "$GH_LOG" ] && echo ok || { echo "FAIL: gh was called: $(cat "$GH_LOG")"; fails=$((fails+1)); }
tgrep "send without --yes says what would send it" "--yes" "$out"

# --- dedup: an existing issue gets a comment, not a new issue --------------
DIR2="$TMP/q2"; mkdir -p "$DIR2"
AGENTIC_BIOFLOW_REPORTS_DIR="$DIR2" env -i PATH="$PATH" HOME="$TMP" \
    AGENTIC_BIOFLOW_REPORTS_DIR="$DIR2" bash "$R" add --category egress --command launch \
    --step dedup-case >/dev/null

STUBDEDUP="$TMP/stub_dedup"; mkdir -p "$STUBDEDUP"
GH_LOG2="$TMP/dedup.log"; : > "$GH_LOG2"
cat > "$STUBDEDUP/gh" <<'EOF'
#!/bin/bash
echo "$*" >> "$GH_LOG2"
case "$*" in
  "api user --jq .login") echo "not-the-maintainer" ;;
  *"issue list "*)        echo 42 ;;
  *"issue comment "*)     exit 0 ;;
  *"issue create "*)      echo "should not be called" >&2; exit 1 ;;
esac
EOF
chmod +x "$STUBDEDUP/gh"

out=$(GH_LOG2="$GH_LOG2" AGENTIC_BIOFLOW_REPORTS_DIR="$DIR2" env -i PATH="$STUBDEDUP:/usr/bin:/bin" HOME="$TMP" \
      GH_LOG2="$GH_LOG2" AGENTIC_BIOFLOW_REPORTS_DIR="$DIR2" bash "$R" send --yes)
tgrep "dedup path comments on the found issue" "commented on existing issue #42" "$out"
tgrep "dedup path actually called issue comment" "issue comment 42" "$(cat "$GH_LOG2")"
tnotgrep "dedup path never calls issue create" "issue create" "$(cat "$GH_LOG2")"
t "dedup path removes the sent report from the queue" 0 "$(queue_count "$DIR2")"

# --- no gh on PATH: URL fallback, queue kept --------------------------------
DIR3="$TMP/q3"; mkdir -p "$DIR3"
AGENTIC_BIOFLOW_REPORTS_DIR="$DIR3" env -i PATH="$PATH" HOME="$TMP" \
    AGENTIC_BIOFLOW_REPORTS_DIR="$DIR3" bash "$R" add --category data --command downstream \
    --step no-gh-case >/dev/null

out=$(AGENTIC_BIOFLOW_REPORTS_DIR="$DIR3" env -i PATH="/usr/bin:/bin" HOME="$TMP" \
      AGENTIC_BIOFLOW_REPORTS_DIR="$DIR3" bash "$R" send --yes)
tgrep "no gh: prints an issues/new URL" "https://github.com/zhshie/agentic-bioflow_v2/issues/new" "$out"
tgrep "no gh: URL carries the off-design label" "labels=off-design" "$out"
t "no gh: report stays queued" 1 "$(queue_count "$DIR3")"

# --- maintainer identity: never sends ---------------------------------------
DIR4="$TMP/q4"; mkdir -p "$DIR4"
AGENTIC_BIOFLOW_REPORTS_DIR="$DIR4" env -i PATH="$PATH" HOME="$TMP" \
    AGENTIC_BIOFLOW_REPORTS_DIR="$DIR4" bash "$R" add --category scheduler --command setup \
    --step maint-case >/dev/null

STUBMAINT="$TMP/stub_maint"; mkdir -p "$STUBMAINT"
GH_LOG4="$TMP/maint.log"; : > "$GH_LOG4"
cat > "$STUBMAINT/gh" <<'EOF'
#!/bin/bash
echo "$*" >> "$GH_LOG4"
case "$*" in
  "api user --jq .login") echo "zhshie" ;;
  *) echo "should not be called" >&2; exit 1 ;;
esac
EOF
chmod +x "$STUBMAINT/gh"

out=$(GH_LOG4="$GH_LOG4" AGENTIC_BIOFLOW_REPORTS_DIR="$DIR4" env -i PATH="$STUBMAINT:/usr/bin:/bin" HOME="$TMP" \
      GH_LOG4="$GH_LOG4" AGENTIC_BIOFLOW_REPORTS_DIR="$DIR4" bash "$R" send --yes)
tgrep "maintainer identity: says design it in instead" "design this into the plugin instead" "$out"
tnotgrep "maintainer identity: never touches issue list/create/comment" "issue " "$(cat "$GH_LOG4")"
t "maintainer identity: report stays queued" 1 "$(queue_count "$DIR4")"

# --- dry-run prints the gh commands, sends nothing --------------------------
DIR5="$TMP/q5"; mkdir -p "$DIR5"
AGENTIC_BIOFLOW_REPORTS_DIR="$DIR5" env -i PATH="$PATH" HOME="$TMP" \
    AGENTIC_BIOFLOW_REPORTS_DIR="$DIR5" bash "$R" add --category request --command launch \
    --step dry-case >/dev/null

STUBDRY="$TMP/stub_dry"; mkdir -p "$STUBDRY"
GH_LOG5="$TMP/dry.log"; : > "$GH_LOG5"
cat > "$STUBDRY/gh" <<'EOF'
#!/bin/bash
echo "$*" >> "$GH_LOG5"
case "$*" in
  "api user --jq .login") echo "not-the-maintainer" ;;
  *"issue list "*|*"issue create "*|*"issue comment "*)
    echo "dry-run must never reach this" >&2; exit 1 ;;
esac
EOF
chmod +x "$STUBDRY/gh"

out=$(GH_LOG5="$GH_LOG5" AGENTIC_BIOFLOW_REPORTS_DIR="$DIR5" env -i PATH="$STUBDRY:/usr/bin:/bin" HOME="$TMP" \
      GH_LOG5="$GH_LOG5" AGENTIC_BIOFLOW_REPORTS_DIR="$DIR5" bash "$R" send --yes --dry-run)
tgrep "dry-run prints the gh issue list command" "gh issue list --repo" "$out"
tgrep "dry-run prints the gh issue create command" "gh issue create --repo" "$out"
tnotgrep "dry-run never actually calls issue list/create/comment" "issue " "$(cat "$GH_LOG5")"
t "dry-run: report stays queued" 1 "$(queue_count "$DIR5")"

# REPORT_DRY_RUN=1 must behave the same as --dry-run.
DIR6="$TMP/q6"; mkdir -p "$DIR6"
AGENTIC_BIOFLOW_REPORTS_DIR="$DIR6" env -i PATH="$PATH" HOME="$TMP" \
    AGENTIC_BIOFLOW_REPORTS_DIR="$DIR6" bash "$R" add --category host --command finish \
    --step dry-env-case >/dev/null
GH_LOG6="$TMP/dry_env.log"; : > "$GH_LOG6"
out=$(GH_LOG5="$GH_LOG6" AGENTIC_BIOFLOW_REPORTS_DIR="$DIR6" env -i PATH="$STUBDRY:/usr/bin:/bin" HOME="$TMP" \
      GH_LOG5="$GH_LOG6" REPORT_DRY_RUN=1 AGENTIC_BIOFLOW_REPORTS_DIR="$DIR6" bash "$R" send --yes)
tgrep "REPORT_DRY_RUN=1 behaves like --dry-run" "gh issue create --repo" "$out"
t "REPORT_DRY_RUN=1: report stays queued" 1 "$(queue_count "$DIR6")"

echo
[ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
