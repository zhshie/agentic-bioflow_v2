#!/bin/bash
# settings.sh --migrate also carries the pre-T30 queue of unsent off-design
# reports (<old settings dir>/reports/*.report) to <root>/config/reports/.
# Covers TC-001..TC-021 of specs/migrate-reports-queue/test-case.md.
D="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
S="$D/scripts/settings.sh"; R="$D/scripts/report.sh"
fails=0
t() { printf '%-60s ' "$1"; [ "$2" = "$3" ] && echo ok || { echo "FAIL: got '$2', wanted '$3'"; fails=$((fails+1)); }; }

# Fresh sandbox: sets TMP, OLD (old config dir), ROOT. HOME is always a temp dir.
setup() {
  TMP=$(mktemp -d); TMPS="$TMPS $TMP"
  export HOME="$TMP/home" XDG_CONFIG_HOME="$TMP/home/.config"
  unset LAB_RUNS_DIR LAB_SETTINGS_FILE AGENTIC_BIOFLOW_REPORTS_DIR AGENTIC_BIOFLOW_ROOT
  OLD="$HOME/.config/agentic-bioflow"; mkdir -p "$OLD"
  printf 'workspace_id: 1\n' > "$OLD/env.yaml"; chmod 600 "$OLD/env.yaml"
  ROOT="$TMP/root"
}
two() { mkdir -p "$1"; printf 'one\n' > "$1/100-1-aaa.report"; printf 'two\n' > "$1/200-2-bbb.report"; }
trap 'rm -rf $TMPS' EXIT
mig() { OUT="$(bash "$S" --migrate "$ROOT" 2>&1)"; }

# TC-001..009, TC-011
setup; two "$OLD/reports"; mig
Q="$ROOT/config/reports"
t "TC-001 first report identical" "$(cmp "$OLD/reports/100-1-aaa.report" "$Q/100-1-aaa.report" && echo same)" "same"
t "TC-001 second report identical" "$(cmp "$OLD/reports/200-2-bbb.report" "$Q/200-2-bbb.report" && echo same)" "same"
t "TC-002 report.sh --dir points at new queue" "$(bash "$R" --dir 2>/dev/null)" "$Q"
LST="$(bash "$R" list 2>&1)"
t "TC-003 report.sh list shows both" "$(echo "$LST" | grep -c -e 100-1-aaa -e 200-2-bbb)" "2"
t "TC-004 old dir stays" "$([ -d "$OLD/reports" ] && echo y)" "y"
t "TC-005 old files stay" "$(ls "$OLD/reports" | wc -l | tr -d ' ')" "2"
t "TC-005 old content intact" "$(cat "$OLD/reports/100-1-aaa.report")" "one"
t "TC-006 file mode 600" "$(stat -c %a "$Q"/*.report | sort -u)" "600"
t "TC-007 dir mode 700" "$(stat -c %a "$Q")" "700"
t "TC-008 count line" "$(echo "$OUT" | grep -cF "2 queued report(s) copied to $Q")" "1"
t "TC-008 only one queued line" "$(echo "$OUT" | grep -c 'queued report')" "1"
t "TC-009 old dir in deletable list" "$(echo "$OUT" | sed -n '/^Done/,$p' | grep -cF "$OLD/reports")" "1"
t "TC-011 settings line unchanged" "$(echo "$OUT" | grep -c '1 setting(s) into config/env.yaml')" "1"

# TC-010: legacy location under LAB_RUNS_DIR
setup; export LAB_RUNS_DIR="$TMP/lab"; rm -rf "$OLD"; mkdir -p "$LAB_RUNS_DIR/_personal"
printf 'workspace_id: 1\n' > "$LAB_RUNS_DIR/_personal/env.yaml"; two "$LAB_RUNS_DIR/_personal/reports"; mig
t "TC-010 LAB_RUNS_DIR queue copied" "$(ls "$ROOT/config/reports" 2>/dev/null | wc -l | tr -d ' ')" "2"
t "TC-010 identical" "$(cmp "$LAB_RUNS_DIR/_personal/reports/200-2-bbb.report" "$ROOT/config/reports/200-2-bbb.report" && echo same)" "same"

# TC-012/013/014: token, local_root, no secret in output
setup; two "$OLD/reports"; printf 'SECRETTOKEN123\n' > "$OLD/.seqera_token"; printf 'local_root: /some/where\n' >> "$OLD/env.yaml"; mig
t "TC-012 token copied message" "$(echo "$OUT" | grep -cF "token copied to $ROOT/config/.seqera_token")" "1"
t "TC-013 local_root message" "$(echo "$OUT" | grep -cF 'local_root (/some/where) is superseded by the root itself - not carried over')" "1"
t "TC-014 token not in output" "$(echo "$OUT" | grep -c SECRETTOKEN123)" "0"

# TC-015/016: never overwrite
setup; two "$OLD/reports"; mkdir -p "$ROOT/config/reports"; printf 'mine\n' > "$ROOT/config/reports/100-1-aaa.report"; mig
t "TC-015 existing not overwritten" "$(cat "$ROOT/config/reports/100-1-aaa.report")" "mine"
t "TC-015 other one copied" "$(cat "$ROOT/config/reports/200-2-bbb.report")" "two"
t "TC-016 already-there line" "$(echo "$OUT" | grep -c '1 already there - left alone')" "1"

# TC-017/018: no old queue
setup; mig
t "TC-017 no new queue dir" "$([ -e "$ROOT/config/reports" ] && echo made || echo none)" "none"
t "TC-018 no queued text" "$(echo "$OUT" | grep -c 'queued report')" "0"

# TC-019/020: only *.report files
setup; two "$OLD/reports"; echo x > "$OLD/reports/notes.txt"; mkdir -p "$OLD/reports/sub"; echo y > "$OLD/reports/sub/z.report"; mig
t "TC-019 notes.txt not copied" "$([ -e "$ROOT/config/reports/notes.txt" ] && echo y || echo n)" "n"
t "TC-020 subdir not copied" "$([ -e "$ROOT/config/reports/sub" ] && echo y || echo n)" "n"

# TC-021: XDG state queue is not migrated
setup; two "$HOME/.local/state/agentic-bioflow/reports"; mig
t "TC-021 state queue not copied" "$([ -e "$ROOT/config/reports" ] && echo y || echo n)" "n"
t "TC-021 state queue intact" "$(ls "$HOME/.local/state/agentic-bioflow/reports" | wc -l | tr -d ' ')" "2"

echo; [ "$fails" = 0 ] && echo "all passed" || { echo "$fails failed"; exit 1; }
